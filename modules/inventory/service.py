"""
Inventory Module - Service Layer
==================================
Bar generation, CRUD, bulk operations, and reservation management.
"""

import math
import secrets
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import IntegrityError

from common.helpers import safe_int, now_utc
from common.upload import save_upload_file, delete_file
from modules.inventory.models import (
    Bar, BarImage, BarBatchLink, BarStatus, OwnershipHistory, DealerTransfer, TransferType,
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
        dealer_tier_id: int = None,
        is_sellable: bool = None,
    ) -> Tuple[List[Bar], int, int]:
        """
        List bars with pagination, search, and filters.
        Returns: (bars, total_count, total_pages)
        """
        query = db.query(Bar).options(
            joinedload(Bar.product),
            joinedload(Bar.customer),
            selectinload(Bar.batch_links).joinedload(BarBatchLink.batch),
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
        if dealer_tier_id:
            # Bars whose physical location is a dealer of this tier
            from modules.user.models import User
            query = query.filter(Bar.dealer_id.in_(
                db.query(User.id).filter(User.tier_id == dealer_tier_id)
            ))
        if is_sellable is not None:
            query = query.filter(Bar.is_sellable == is_sellable)

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

    def generate_preorder_bars(self, db: Session, product_id: int, central_warehouse_id: int, count: int) -> int:
        """Generate N preorder bars: ASSIGNED to central warehouse with is_preorder=True."""
        created = 0
        for _ in range(count):
            for attempt in range(5):
                try:
                    bar = Bar(
                        serial_code=generate_serial(),
                        status=BarStatus.ASSIGNED,
                        product_id=product_id,
                        dealer_id=central_warehouse_id,
                        is_preorder=True,
                    )
                    db.add(bar)
                    db.flush()
                    db.add(OwnershipHistory(
                        bar_id=bar.id,
                        previous_owner_id=None,
                        new_owner_id=None,
                        description=f"تولید پیش‌سفارش — انبار مرکزی",
                    ))
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
        new_status = data.get("status", bar.status)
        new_dealer = safe_int(data.get("dealer_id")) if data.get("dealer_id") != "0" else None

        # Validation: bar with product must have a dealer (physical location)
        if new_prod and not new_dealer:
            raise ValueError("شمش دارای محصول باید مکان (نماینده) داشته باشد.")
        if new_status in (BarStatus.ASSIGNED, BarStatus.RESERVED, BarStatus.SOLD) and not new_dealer:
            raise ValueError("شمش با وضعیت اختصاص‌یافته/رزرو/فروخته‌شده باید مکان (نماینده) داشته باشد.")

        bar.status = new_status
        bar.product_id = new_prod
        bar.customer_id = new_cust
        bar.is_preorder = bool(data.get("is_preorder"))

        if "batch_ids" in data:
            self.set_batches(db, bar, data.get("batch_ids") or [])

        # Sellability change: mirror onto the Rasis POS device if this dealer has one
        new_sellable = bool(data.get("is_sellable"))
        sellable_changed = bar.is_sellable != new_sellable
        bar.is_sellable = new_sellable

        # Track dealer (location) change
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

            # Rasis POS: add bar to new dealer's POS if assigned and sellable
            if new_dealer and data.get("status") == BarStatus.ASSIGNED and new_sellable:
                try:
                    from modules.rasis.service import rasis_service
                    from modules.user.models import User
                    dealer_obj = db.query(User).get(new_dealer)
                    if dealer_obj and dealer_obj.rasis_sharepoint:
                        rasis_service.add_bar_to_pos(db, bar, dealer_obj)
                except Exception:
                    pass  # Never block admin operations

        elif sellable_changed and bar.dealer_id:
            # Location unchanged but sellability flipped — push/pull on the POS device
            self._sync_sellable_to_rasis(db, [bar], new_sellable)

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
    # Batches (M2M)
    # ==========================================

    def _valid_batch_ids(self, db: Session, batch_ids) -> List[int]:
        """Keep only ids that exist, de-duplicated, order preserved."""
        from modules.catalog.models import Batch
        wanted = list(dict.fromkeys(i for i in (safe_int(b) for b in batch_ids or []) if i))
        if not wanted:
            return []
        existing = {b.id for b in db.query(Batch.id).filter(Batch.id.in_(wanted)).all()}
        return [i for i in wanted if i in existing]

    def set_batches(self, db: Session, bar: Bar, batch_ids) -> List[int]:
        """Replace a bar's batch set. Returns the ids actually linked."""
        wanted = self._valid_batch_ids(db, batch_ids)
        current = {link.batch_id: link for link in bar.batch_links}

        for batch_id, link in current.items():
            if batch_id not in wanted:
                bar.batch_links.remove(link)  # delete-orphan cascade removes the row
        for batch_id in wanted:
            if batch_id not in current:
                bar.batch_links.append(BarBatchLink(batch_id=batch_id))

        db.flush()
        return wanted

    def bulk_set_batches(self, db: Session, bar_ids: List[int], batch_ids) -> int:
        """Replace the batch set of many bars at once. Returns bars touched."""
        if not bar_ids:
            return 0
        wanted = self._valid_batch_ids(db, batch_ids)

        db.query(BarBatchLink).filter(BarBatchLink.bar_id.in_(bar_ids)).delete(synchronize_session=False)
        db.flush()
        if wanted:
            db.bulk_save_objects([
                BarBatchLink(bar_id=bar_id, batch_id=batch_id)
                for bar_id in bar_ids for batch_id in wanted
            ])
            db.flush()
        return len(bar_ids)

    # ==========================================
    # Bulk Actions
    # ==========================================

    # Statuses an admin may set from the bulk action.
    # RESERVED is excluded on purpose: a reservation is created by the cart/POS
    # flow together with reserved_customer_id + reserved_until. Bulk-setting it
    # here would leave a bar Reserved with no holder and no expiry, which
    # release_expired_reservations() never picks up — i.e. stuck out of stock
    # forever. Use the single-bar edit form if you really need it.
    BULK_STATUSES = (BarStatus.RAW, BarStatus.ASSIGNED, BarStatus.SOLD)

    def bulk_update(self, db: Session, ids: List[int], data: dict) -> int:
        """Bulk update bars. Returns count of affected rows."""
        if not ids:
            return 0

        update_data = {}

        # Resolve target values first
        has_dealer = data.get("target_dealer_id") not in (None, "")
        target_dealer = safe_int(data["target_dealer_id"]) if has_dealer and data["target_dealer_id"] != "0" else None

        # Explicit status wins over the status implied by product/customer below
        explicit_status = (data.get("target_status") or "").strip() or None
        if explicit_status and explicit_status not in self.BULK_STATUSES:
            if explicit_status == BarStatus.RESERVED:
                raise ValueError(
                    "وضعیت «رزرو» از عملیات گروهی قابل تنظیم نیست — "
                    "رزرو توسط سبد خرید یا POS ایجاد می‌شود."
                )
            raise ValueError("وضعیت انتخاب‌شده نامعتبر است.")

        # Product assignment
        has_product = data.get("target_product_id") not in (None, "")
        prod_id = None
        if has_product:
            prod_id = safe_int(data["target_product_id"]) if data["target_product_id"] != "0" else None
            # Validation: bar with product must have dealer (physical location)
            if prod_id and not target_dealer:
                orphan_count = db.query(Bar).filter(Bar.id.in_(ids), Bar.dealer_id.is_(None)).count()
                if orphan_count > 0 and not has_dealer:
                    raise ValueError("شمش دارای محصول باید مکان (نماینده) داشته باشد.")
            update_data[Bar.product_id] = prod_id
            if not explicit_status:
                update_data[Bar.status] = BarStatus.ASSIGNED if prod_id else BarStatus.RAW

        # Customer assignment
        has_customer = data.get("target_customer_id") not in (None, "")
        cust_id = None
        if has_customer:
            cust_id = safe_int(data["target_customer_id"]) if data["target_customer_id"] != "0" else None
            if not target_dealer:
                orphan_count = db.query(Bar).filter(Bar.id.in_(ids), Bar.dealer_id.is_(None)).count()
                if orphan_count > 0 and not has_dealer:
                    raise ValueError("برای تغییر مالکیت، انتخاب نماینده (مکان) الزامی است.")
            update_data[Bar.customer_id] = cust_id
            if not explicit_status:
                update_data[Bar.status] = BarStatus.SOLD if cust_id else BarStatus.ASSIGNED

        # Batches (M2M): "" = leave alone, "0" = clear, otherwise replace with the given set
        raw_batches = data.get("target_batch_ids")
        if isinstance(raw_batches, str):
            raw_batches = [b for b in raw_batches.split(",") if b.strip()]
        batch_change = raw_batches not in (None, [])
        # "0" anywhere in the selection means "clear all batches"
        new_batches = [] if any(str(b).strip() == "0" for b in (raw_batches or [])) else (raw_batches or [])

        if has_dealer:
            update_data[Bar.dealer_id] = target_dealer

        # Explicit status: validate the state each bar actually ends up in
        if explicit_status:
            self._validate_bulk_status(
                db, ids, explicit_status,
                prod_id if has_product else "keep",
                cust_id if has_customer else "keep",
                target_dealer if has_dealer else "keep",
            )
            update_data[Bar.status] = explicit_status

        count = 0
        if update_data:
            # Always clear reservation on bulk update
            update_data[Bar.reserved_customer_id] = None
            update_data[Bar.reserved_until] = None
            count = db.query(Bar).filter(Bar.id.in_(ids)).update(update_data, synchronize_session=False)
            db.flush()

        if batch_change:
            count = max(count, self.bulk_set_batches(db, ids, new_batches))

        return count

    def _validate_bulk_status(self, db: Session, ids: List[int], status: str,
                              product, customer, dealer) -> None:
        """
        Reject a bulk status change that would leave bars in an incoherent state.

        product/customer/dealer are the bulk target values, or the sentinel
        "keep" when that field is not being changed (each bar keeps its own).
        """
        bars = db.query(Bar).filter(Bar.id.in_(ids)).all()

        missing_dealer, missing_product, missing_customer = 0, 0, 0
        has_product, has_customer = 0, 0

        for bar in bars:
            final_product = bar.product_id if product == "keep" else product
            final_customer = bar.customer_id if customer == "keep" else customer
            final_dealer = bar.dealer_id if dealer == "keep" else dealer

            if not final_dealer:
                missing_dealer += 1
            if not final_product:
                missing_product += 1
            if not final_customer:
                missing_customer += 1
            if final_product:
                has_product += 1
            if final_customer:
                has_customer += 1

        if status == BarStatus.RAW:
            # A raw bar is a bare serial: no product, no owner.
            if has_product:
                raise ValueError(
                    f"{has_product} شمش هنوز محصول دارد. برای تبدیل به «خام»، "
                    "گزینه «حذف محصول» را هم انتخاب کنید."
                )
            if has_customer:
                raise ValueError(
                    f"{has_customer} شمش هنوز مالک دارد. برای تبدیل به «خام»، "
                    "گزینه «حذف مالک» را هم انتخاب کنید."
                )
            return

        # ASSIGNED / SOLD both need a physical location and a product
        if missing_dealer:
            raise ValueError(
                f"{missing_dealer} شمش نمایندگی (مکان) ندارد. "
                "برای این وضعیت انتخاب نمایندگی الزامی است."
            )
        if missing_product:
            raise ValueError(
                f"{missing_product} شمش محصول ندارد. "
                "برای این وضعیت تخصیص محصول الزامی است."
            )
        if status == BarStatus.SOLD and missing_customer:
            raise ValueError(
                f"{missing_customer} شمش مالک ندارد. "
                "برای وضعیت «فروخته» انتخاب مالک الزامی است."
            )

    def _sync_sellable_to_rasis(self, db: Session, bars: List[Bar], sellable: bool) -> None:
        """Mirror a sellability change onto Rasis POS devices. Never raises."""
        try:
            from modules.rasis.service import rasis_service
            from modules.user.models import User

            dealer_cache = {}
            for bar in bars:
                if not bar.dealer_id or bar.status != BarStatus.ASSIGNED or not bar.product_id:
                    continue
                if bar.dealer_id not in dealer_cache:
                    dealer_cache[bar.dealer_id] = db.query(User).get(bar.dealer_id)
                dealer_obj = dealer_cache[bar.dealer_id]
                if not dealer_obj or not dealer_obj.rasis_sharepoint:
                    continue
                if sellable:
                    rasis_service.add_bar_to_pos(db, bar, dealer_obj)
                else:
                    rasis_service.remove_bar_from_pos(db, bar, dealer_obj)
        except Exception:
            pass  # Rasis is best-effort; never block an admin operation

    def bulk_set_sellable(self, db: Session, ids: List[int], sellable: bool) -> int:
        """
        Bulk enable/disable sellability. Returns count of affected rows.

        Deliberately separate from bulk_update: that method clears reservations on
        every write, which would orphan an in-flight reservation here.
        """
        if not ids:
            return 0

        bars = db.query(Bar).filter(Bar.id.in_(ids), Bar.is_sellable != sellable).all()
        if not bars:
            return 0

        for bar in bars:
            bar.is_sellable = sellable
        db.flush()

        self._sync_sellable_to_rasis(db, bars, sellable)
        return len(bars)

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
                Bar.is_sellable == True,
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
        db.add(OwnershipHistory(
            bar_id=bar.id,
            previous_owner_id=bar.customer_id,
            new_owner_id=bar.customer_id,
            description=f"انتقال مکان — {description}" if description else f"انتقال مکان توسط {transferred_by}",
        ))
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
            Bar.is_preorder == False,  # Preorder bars don't physically exist
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
        if status == "matched":
            session.total_matched = (session.total_matched or 0) + 1
        elif status == "unexpected":
            session.total_unexpected = (session.total_unexpected or 0) + 1
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
            Bar.is_preorder == False,  # Preorder bars don't physically exist
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
