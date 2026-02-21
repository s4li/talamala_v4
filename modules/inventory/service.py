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
    Bar, BarImage, BarStatus, OwnershipHistory, DealerTransfer,
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
        """Generate N new raw bars with unique serial codes. Returns count created."""
        created = 0
        for _ in range(count):
            for attempt in range(5):
                try:
                    bar = Bar(serial_code=generate_serial(), status=BarStatus.RAW)
                    db.add(bar)
                    db.commit()
                    created += 1
                    break
                except IntegrityError:
                    db.rollback()
                    if attempt == 4:
                        raise
        return created

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
        ))
        bar.dealer_id = to_dealer_id if to_dealer_id else None
        db.flush()
        return bar

    def get_transfers_for_bar(self, db: Session, bar_id: int) -> List[DealerTransfer]:
        return db.query(DealerTransfer).filter(
            DealerTransfer.bar_id == bar_id,
        ).order_by(DealerTransfer.transferred_at.desc()).all()


# Singleton
inventory_service = InventoryService()
