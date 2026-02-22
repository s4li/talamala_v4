"""
Inventory Module - Service Layer
==================================
Bar generation, CRUD, bulk operations, and reservation management.
"""

import math
import secrets
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from common.helpers import safe_int, now_utc
from common.upload import save_upload_file, delete_file
from modules.inventory.models import (
    Bar, BarImage, BarStatus, OwnershipHistory, DealerTransfer, TransferType,
    ReconciliationSession, ReconciliationItem, ReconciliationStatus, ReconciliationItemStatus,
)

# Characters for serial codes (no ambiguous: 0, O, I, 1)
SAFE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_serial(length: int = 8) -> str:
    """Generate a random serial code using safe characters."""
    return "".join(secrets.choice(SAFE_CHARS) for _ in range(length))


class InventoryService:

    # ==========================================
    # Query
    # ==========================================

    def list_bars(
        self,
        db: Session,
        page: int = 1,
        per_page: int = 50,
        search: str = None,
        customer_id: int = None,
        status: str = None,
        product_id: int = None,
        dealer_id: int = None,
    ) -> Tuple[List[Bar], int, int]:
        """
        List bars with pagination, search, and filters.
        Returns: (bars, total_count, total_pages)
        """
        query = db.query(Bar).options(
            joinedload(Bar.product),
            joinedload(Bar.customer),
            joinedload(Bar.batch),
            joinedload(Bar.dealer_location),
        ).order_by(Bar.id.desc())

        if search:
            query = query.filter(Bar.serial_code.ilike(f"%{search}%"))
        if customer_id:
            query = query.filter(Bar.customer_id == customer_id)
        if status:
            query = query.filter(Bar.status == status)
        if product_id:
            query = query.filter(Bar.product_id == product_id)
        if dealer_id:
            query = query.filter(Bar.dealer_id == dealer_id)

        total = query.count()
        total_pages = math.ceil(total / per_page) if total else 1
        bars = query.offset((page - 1) * per_page).limit(per_page).all()

        return bars, total, total_pages

    def get_by_id(self, db: Session, bar_id: int) -> Optional[Bar]:
        return db.query(Bar).filter(Bar.id == bar_id).first()

    def get_by_serial(self, db: Session, serial: str) -> Optional[Bar]:
        return db.query(Bar).filter(Bar.serial_code == serial).first()

    # ==========================================
    # Generate
    # ==========================================

    def generate_bars(self, db: Session, count: int) -> int:
        """Generate N new raw bars with unique serial codes + QR images. Returns count created."""
        created = 0
        for _ in range(count):
            for attempt in range(5):
                try:
                    bar = Bar(serial_code=generate_serial(), status=BarStatus.RAW)
                    db.add(bar)
                    db.commit()
                    # Generate QR code file for laser printing
                    self._generate_qr_for_bar(bar.serial_code)
                    created += 1
                    break
                except IntegrityError:
                    db.rollback()
                    if attempt == 4:
                        raise
        return created

    def _generate_qr_for_bar(self, serial_code: str):
        """Generate and save high-res QR code PNG to static/uploads/qrcodes/."""
        try:
            from modules.verification.service import verification_service
            verification_service.ensure_qr_exists(serial_code)
        except Exception:
            pass  # Never block bar creation if QR generation fails

    def regenerate_all_qr_codes(self, db: Session) -> int:
        """Regenerate QR codes for all existing bars. Returns count."""
        import os
        from modules.verification.service import verification_service, QR_OUTPUT_DIR
        os.makedirs(QR_OUTPUT_DIR, exist_ok=True)
        bars = db.query(Bar).all()
        count = 0
        for bar in bars:
            path = verification_service.get_qr_path(bar.serial_code)
            # Force regenerate (delete existing first)
            if os.path.exists(path):
                os.remove(path)
            verification_service.generate_qr_for_print(bar.serial_code, save_path=path)
            count += 1
        return count

    # ==========================================
    # Update
    # ==========================================

    def update_bar(
        self,
        db: Session,
        bar_id: int,
        data: dict,
        files: List[UploadFile] = None,
        updated_by: str = "System",
    ) -> Optional[Bar]:
        """Update a single bar's fields. Tracks ownership changes."""
        bar = self.get_by_id(db, bar_id)
        if not bar:
            return None

        new_cust = safe_int(data.get("customer_id")) if data.get("customer_id") != "0" else None
        new_prod = safe_int(data.get("product_id")) if data.get("product_id") != "0" else None

        # Track ownership change
        if bar.customer_id != new_cust:
            db.add(OwnershipHistory(
                bar_id=bar.id,
                previous_owner_id=bar.customer_id,
                new_owner_id=new_cust,
                description=f"Admin Update (by {updated_by})",
            ))

        # Update fields
        bar.status = data.get("status", bar.status)
        bar.product_id = new_prod
        bar.customer_id = new_cust
        bar.batch_id = safe_int(data.get("batch_id")) if data.get("batch_id") != "0" else None

        # Track dealer (location) change
        new_dealer = safe_int(data.get("dealer_id")) if data.get("dealer_id") != "0" else None
        if bar.dealer_id != new_dealer:
            db.add(DealerTransfer(
                bar_id=bar.id,
                from_dealer_id=bar.dealer_id,
                to_dealer_id=new_dealer,
                transferred_by=updated_by,
                description=data.get("transfer_note", ""),
                transfer_type=TransferType.ADMIN_TRANSFER,
            ))
            bar.dealer_id = new_dealer

            # Rasis POS: add bar to new dealer's POS if assigned
            if new_dealer and data.get("status") == BarStatus.ASSIGNED:
                try:
                    from modules.rasis.service import rasis_service
                    from modules.user.models import User
                    dealer_obj = db.query(User).get(new_dealer)
                    if dealer_obj and dealer_obj.rasis_sharepoint:
                        rasis_service.add_bar_to_pos(db, bar, dealer_obj)
                except Exception:
                    pass  # Never block admin operations

        # Clear reservation if no longer reserved or if owner assigned
        if bar.status != BarStatus.RESERVED or new_cust is not None:
            bar.reserved_customer_id = None
            bar.reserved_until = None

        # Save new images
        if files:
            for f in files:
                if not f or not f.filename:
                    continue
                path = save_upload_file(f, subfolder="bars")
                if path:
                    db.add(BarImage(file_path=path, bar_id=bar.id))

        db.flush()
        return bar

    # ==========================================
    # Bulk Actions
    # ==========================================

    def bulk_update(self, db: Session, ids: List[int], data: dict) -> int:
        """Bulk update bars. Returns count of affected rows."""
        if not ids:
            return 0

        update_data = {}

        # Product assignment
        if data.get("target_product_id") not in (None, ""):
            prod_id = safe_int(data["target_product_id"]) if data["target_product_id"] != "0" else None
            update_data[Bar.product_id] = prod_id
            update_data[Bar.status] = BarStatus.ASSIGNED if prod_id else BarStatus.RAW

        # Customer assignment
        if data.get("target_customer_id") not in (None, ""):
            cust_id = safe_int(data["target_customer_id"]) if data["target_customer_id"] != "0" else None
            update_data[Bar.customer_id] = cust_id
            update_data[Bar.status] = BarStatus.SOLD if cust_id else BarStatus.ASSIGNED

        # Other fields
        if data.get("target_batch_id") not in (None, ""):
            update_data[Bar.batch_id] = safe_int(data["target_batch_id"]) if data["target_batch_id"] != "0" else None
        if data.get("target_dealer_id") not in (None, ""):
            update_data[Bar.dealer_id] = safe_int(data["target_dealer_id"]) if data["target_dealer_id"] != "0" else None

        if update_data:
            # Always clear reservation on bulk update
            update_data[Bar.reserved_customer_id] = None
            update_data[Bar.reserved_until] = None
            count = db.query(Bar).filter(Bar.id.in_(ids)).update(update_data, synchronize_session=False)
            db.flush()
            return count

        return 0

    def bulk_delete(self, db: Session, ids: List[int]) -> int:
        """Delete bars by IDs. Returns count deleted."""
        count = db.query(Bar).filter(Bar.id.in_(ids)).delete(synchronize_session=False)
        db.flush()
        return count

    # ==========================================
    # Image Management
    # ==========================================

    def delete_image(self, db: Session, img_id: int) -> Optional[int]:
        """Delete a bar image. Returns bar_id or None."""
        img = db.query(BarImage).filter(BarImage.id == img_id).first()
        if not img:
            return None
        delete_file(img.file_path)
        bar_id = img.bar_id
        db.delete(img)
        db.flush()
        return bar_id

    # ==========================================
    # Reservation (used by cart module later)
    # ==========================================

    def reserve_bars(
        self,
        db: Session,
        product_id: int,
        customer_id: int,
        quantity: int,
        expire_minutes: int = 15,
    ) -> List[Bar]:
        """
        Reserve N available bars for a customer.
        Uses SELECT FOR UPDATE to prevent race conditions.
        """
        from datetime import timedelta

        available = (
            db.query(Bar)
            .filter(
                Bar.product_id == product_id,
                Bar.status == BarStatus.ASSIGNED,
                Bar.customer_id.is_(None),
            )
            .with_for_update(skip_locked=True)
            .limit(quantity)
            .all()
        )

        if len(available) < quantity:
            return []

        now = now_utc()
        expire_at = now + timedelta(minutes=expire_minutes)

        for bar in available:
            bar.status = BarStatus.RESERVED
            bar.reserved_customer_id = customer_id
            bar.reserved_until = expire_at

        db.flush()
        return available

    def release_bars(self, db: Session, bar_ids: List[int]):
        """Release reserved bars back to Assigned status."""
        db.query(Bar).filter(Bar.id.in_(bar_ids)).update({
            Bar.status: BarStatus.ASSIGNED,
            Bar.reserved_customer_id: None,
            Bar.reserved_until: None,
        }, synchronize_session=False)
        db.flush()

    def release_expired_reservations(self, db: Session) -> int:
        """Release all bars whose reservation has expired. Returns count released."""
        now = now_utc()
        count = db.query(Bar).filter(
            Bar.status == BarStatus.RESERVED,
            Bar.reserved_until.isnot(None),
            Bar.reserved_until < now,
        ).update({
            Bar.status: BarStatus.ASSIGNED,
            Bar.reserved_customer_id: None,
            Bar.reserved_until: None,
        }, synchronize_session=False)
        db.flush()
        return count

    # ==========================================
    # Dealer Transfer History
    # ==========================================

    def get_bar_count_by_dealer(self, db: Session) -> dict:
        """Returns {dealer_id: count} for inventory dashboard."""
        from sqlalchemy import func
        rows = db.query(Bar.dealer_id, func.count(Bar.id)).filter(
            Bar.dealer_id.isnot(None),
        ).group_by(Bar.dealer_id).all()
        return {dealer_id: cnt for dealer_id, cnt in rows}

    def transfer_bar_to_dealer(
        self,
        db: Session,
        bar_id: int,
        to_dealer_id: int,
        transferred_by: str = "System",
        description: str = "",
        transfer_type=TransferType.MANUAL,
        reference_type: str = None,
        reference_id: int = None,
    ) -> Optional[Bar]:
        """Move a bar to a new dealer/warehouse with history tracking."""
        bar = db.query(Bar).filter(Bar.id == bar_id).first()
        if not bar:
            return None

        from_id = bar.dealer_id
        if from_id == to_dealer_id:
            return bar  # No change

        db.add(DealerTransfer(
            bar_id=bar.id,
            from_dealer_id=from_id,
            to_dealer_id=to_dealer_id if to_dealer_id else None,
            transferred_by=transferred_by,
            description=description,
            transfer_type=transfer_type,
            reference_type=reference_type,
            reference_id=reference_id,
        ))
        bar.dealer_id = to_dealer_id if to_dealer_id else None
        db.flush()
        return bar

    def get_transfers_for_bar(self, db: Session, bar_id: int) -> List[DealerTransfer]:
        return db.query(DealerTransfer).filter(
            DealerTransfer.bar_id == bar_id,
        ).order_by(DealerTransfer.transferred_at.desc()).all()

    # ==========================================
    # Reconciliation (انبارگردانی)
    # ==========================================

    def start_reconciliation(self, db: Session, dealer_id: int, initiated_by: str) -> ReconciliationSession:
        """Start a new reconciliation session for a dealer. Blocks if active session exists."""
        active = db.query(ReconciliationSession).filter(
            ReconciliationSession.dealer_id == dealer_id,
            ReconciliationSession.status == ReconciliationStatus.IN_PROGRESS,
        ).first()
        if active:
            raise ValueError("یک جلسه انبارگردانی فعال برای این نمایندگی وجود دارد")

        expected = db.query(Bar).filter(
            Bar.dealer_id == dealer_id,
            Bar.status.in_([BarStatus.ASSIGNED, BarStatus.RESERVED]),
        ).count()

        session = ReconciliationSession(
            dealer_id=dealer_id,
            initiated_by=initiated_by,
            status=ReconciliationStatus.IN_PROGRESS,
            total_expected=expected,
        )
        db.add(session)
        db.flush()
        return session

    def scan_for_reconciliation(
        self, db: Session, session_id: int, serial_code: str, dealer_id: int,
    ) -> dict:
        """Record a scanned bar in a reconciliation session. Returns result dict."""
        session = db.query(ReconciliationSession).filter(
            ReconciliationSession.id == session_id,
            ReconciliationSession.dealer_id == dealer_id,
            ReconciliationSession.status == ReconciliationStatus.IN_PROGRESS,
        ).first()
        if not session:
            return {"error": "جلسه انبارگردانی فعال یافت نشد"}

        serial_code = serial_code.strip().upper()

        # Check for duplicate scan
        existing = db.query(ReconciliationItem).filter(
            ReconciliationItem.session_id == session_id,
            ReconciliationItem.serial_code == serial_code,
        ).first()
        if existing:
            return {"error": "این سریال قبلاً اسکن شده", "duplicate": True}

        bar = db.query(Bar).filter(Bar.serial_code == serial_code).first()

        if bar and bar.dealer_id == dealer_id:
            # Matched — bar is at this location
            item = ReconciliationItem(
                session_id=session_id,
                bar_id=bar.id,
                serial_code=serial_code,
                item_status=ReconciliationItemStatus.MATCHED,
                expected_status=bar.status,
                expected_product=bar.product.name if bar.product else None,
            )
            status = "matched"
        else:
            # Unexpected — bar not at this location (or doesn't exist)
            item = ReconciliationItem(
                session_id=session_id,
                bar_id=bar.id if bar else None,
                serial_code=serial_code,
                item_status=ReconciliationItemStatus.UNEXPECTED,
                expected_status=bar.status if bar else None,
                expected_product=bar.product.name if bar and bar.product else None,
            )
            status = "unexpected"

        db.add(item)
        session.total_scanned = (session.total_scanned or 0) + 1
        db.flush()

        return {
            "status": status,
            "serial": serial_code,
            "product": item.expected_product or "—",
            "bar_status": item.expected_status or "—",
            "item_id": item.id,
        }

    def finalize_reconciliation(
        self, db: Session, session_id: int, dealer_id: int, notes: str = None,
    ) -> ReconciliationSession:
        """Finalize: generate Missing items, compute summary stats."""
        session = db.query(ReconciliationSession).filter(
            ReconciliationSession.id == session_id,
            ReconciliationSession.dealer_id == dealer_id,
            ReconciliationSession.status == ReconciliationStatus.IN_PROGRESS,
        ).first()
        if not session:
            raise ValueError("جلسه انبارگردانی فعال یافت نشد")

        # Find bars that should be at this dealer but weren't scanned
        scanned_bar_ids = {
            item.bar_id for item in session.items if item.bar_id
        }
        expected_bars = db.query(Bar).filter(
            Bar.dealer_id == dealer_id,
            Bar.status.in_([BarStatus.ASSIGNED, BarStatus.RESERVED]),
        ).all()

        for bar in expected_bars:
            if bar.id not in scanned_bar_ids:
                db.add(ReconciliationItem(
                    session_id=session_id,
                    bar_id=bar.id,
                    serial_code=bar.serial_code,
                    item_status=ReconciliationItemStatus.MISSING,
                    scanned_at=None,
                    expected_status=bar.status,
                    expected_product=bar.product.name if bar.product else None,
                ))

        # Compute summary stats
        matched = sum(1 for i in session.items if i.item_status == ReconciliationItemStatus.MATCHED)
        unexpected = sum(1 for i in session.items if i.item_status == ReconciliationItemStatus.UNEXPECTED)
        missing = len(expected_bars) - len(scanned_bar_ids & {b.id for b in expected_bars})

        session.total_matched = matched
        session.total_unexpected = unexpected
        session.total_missing = missing
        session.notes = notes
        session.status = ReconciliationStatus.COMPLETED
        session.completed_at = now_utc()

        db.flush()
        return session

    def cancel_reconciliation(self, db: Session, session_id: int, dealer_id: int) -> ReconciliationSession:
        """Cancel an in-progress reconciliation session."""
        session = db.query(ReconciliationSession).filter(
            ReconciliationSession.id == session_id,
            ReconciliationSession.dealer_id == dealer_id,
            ReconciliationSession.status == ReconciliationStatus.IN_PROGRESS,
        ).first()
        if not session:
            raise ValueError("جلسه انبارگردانی فعال یافت نشد")

        session.status = ReconciliationStatus.CANCELLED
        session.completed_at = now_utc()
        db.flush()
        return session

    def list_reconciliation_sessions(
        self, db: Session, dealer_id: int = None, page: int = 1, per_page: int = 20,
    ) -> Tuple[list, int]:
        """List reconciliation sessions. Optional dealer filter. Returns (sessions, total)."""
        from sqlalchemy.orm import joinedload
        query = db.query(ReconciliationSession).options(
            joinedload(ReconciliationSession.dealer),
        ).order_by(ReconciliationSession.started_at.desc())

        if dealer_id:
            query = query.filter(ReconciliationSession.dealer_id == dealer_id)

        total = query.count()
        sessions = query.offset((page - 1) * per_page).limit(per_page).all()
        return sessions, total

    def get_reconciliation_session(
        self, db: Session, session_id: int, dealer_id: int = None,
    ) -> Optional[ReconciliationSession]:
        """Get a single reconciliation session with items."""
        from sqlalchemy.orm import joinedload
        query = db.query(ReconciliationSession).options(
            joinedload(ReconciliationSession.items),
            joinedload(ReconciliationSession.dealer),
        ).filter(ReconciliationSession.id == session_id)

        if dealer_id:
            query = query.filter(ReconciliationSession.dealer_id == dealer_id)

        return query.first()


# Singleton
inventory_service = InventoryService()
