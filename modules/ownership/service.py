"""
Ownership Module - Service Layer
===================================
Bar claim (POS receipt / gift card) and ownership transfer logic.
"""

from datetime import timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from common.helpers import now_utc, generate_unique_claim_code
from common.security import generate_otp, hash_otp
from modules.inventory.models import (
    Bar, BarStatus, OwnershipHistory, BarTransfer, TransferStatus,
    CustodialDeliveryRequest, CustodialDeliveryStatus,
    DealerTransfer, TransferType,
)
from modules.user.models import User


class OwnershipService:

    # ------------------------------------------
    # My Bars
    # ------------------------------------------

    def get_customer_bars(self, db: Session, customer_id: int) -> List[Bar]:
        """Get all bars owned by a customer, enriched with delivery status."""
        from modules.order.models import OrderItem, Order, OrderStatus, DeliveryStatus, DeliveryMethod

        bars = (
            db.query(Bar)
            .filter(Bar.customer_id == customer_id, Bar.status == BarStatus.SOLD)
            .order_by(Bar.id.desc())
            .all()
        )

        # Fetch delivery info for all bars in one query
        bar_ids = [b.id for b in bars]
        delivery_map = {}
        if bar_ids:
            rows = (
                db.query(
                    OrderItem.bar_id,
                    Order.delivery_status,
                    Order.delivery_method,
                )
                .join(Order, OrderItem.order_id == Order.id)
                .filter(
                    OrderItem.bar_id.in_(bar_ids),
                    Order.status == OrderStatus.PAID,
                )
                .all()
            )
            delivery_map = {r.bar_id: r for r in rows}

        # Delivery label/color mapping
        label_map = {
            DeliveryStatus.WAITING: ("در انتظار تحویل", "warning"),
            DeliveryStatus.PREPARING: ("در حال آماده‌سازی", "info"),
            DeliveryStatus.SHIPPED: ("ارسال شده", "primary"),
            DeliveryStatus.DELIVERED: ("تحویل شده", "success"),
            DeliveryStatus.RETURNED: ("مرجوعی", "danger"),
        }

        # Exclude bars with active buyback (non-rejected)
        from modules.dealer.models import BuybackRequest, BuybackStatus
        buyback_bar_ids = set()
        if bar_ids:
            bb_rows = (
                db.query(BuybackRequest.bar_id)
                .filter(
                    BuybackRequest.bar_id.in_(bar_ids),
                    BuybackRequest.status != BuybackStatus.REJECTED,
                )
                .all()
            )
            buyback_bar_ids = {r.bar_id for r in bb_rows}

        # Filter out buyback bars
        bars = [b for b in bars if b.id not in buyback_bar_ids]

        for bar in bars:
            bar._has_buyback = False
            di = delivery_map.get(bar.id)
            if di and di.delivery_status:
                lbl, clr = label_map.get(di.delivery_status, ("نامشخص", "secondary"))
                # Pickup-specific label for WAITING
                if di.delivery_status == DeliveryStatus.WAITING and di.delivery_method == DeliveryMethod.PICKUP:
                    lbl = "منتظر مراجعه"
                bar._delivery_label = lbl
                bar._delivery_color = clr
            else:
                # POS / claim / transfer — already in customer's hands
                bar._delivery_label = "تحویل شده"
                bar._delivery_color = "success"

        return bars

    # ------------------------------------------
    # Claim Bar
    # ------------------------------------------

    def claim_bar(
        self, db: Session, customer_id: int, serial_code: str, claim_code: str
    ) -> Bar:
        """
        Claim a bar using serial_code + claim_code.
        Assigns the bar to the customer and invalidates the claim code.
        """
        serial_code = serial_code.strip().upper()
        claim_code = claim_code.strip().upper()

        if not serial_code or not claim_code:
            raise ValueError("سریال و کد ثبت الزامی است")

        bar = (
            db.query(Bar)
            .filter(
                Bar.serial_code == serial_code,
                Bar.claim_code == claim_code,
                Bar.status == BarStatus.SOLD,
            )
            .first()
        )

        if not bar:
            raise ValueError("کد نامعتبر است یا شمش قبلاً ثبت شده")

        if bar.customer_id is not None:
            raise ValueError("این شمش قبلاً به نام شخص دیگری ثبت شده است")

        # Assign to customer
        bar.customer_id = customer_id
        bar.claim_code = None  # Invalidate

        # Ownership history
        db.add(OwnershipHistory(
            bar_id=bar.id,
            previous_owner_id=None,
            new_owner_id=customer_id,
            description="ثبت مالکیت با کد ثبت",
        ))

        db.flush()
        return bar

    # ------------------------------------------
    # Ownership Transfer
    # ------------------------------------------

    def initiate_transfer(
        self, db: Session, bar_id: int, from_customer_id: int, to_mobile: str
    ) -> Dict[str, Any]:
        """
        Start ownership transfer: validate bar, generate OTP, return raw OTP for SMS.
        OTP is sent to the CURRENT OWNER's mobile (authorization confirmation).
        """
        to_mobile = to_mobile.strip()
        if not to_mobile or len(to_mobile) != 11 or not to_mobile.startswith("09"):
            raise ValueError("شماره موبایل گیرنده نامعتبر است")

        bar = db.query(Bar).filter(Bar.id == bar_id).with_for_update().first()
        if not bar:
            raise ValueError("شمش یافت نشد")
        if bar.customer_id != from_customer_id:
            raise ValueError("شما مالک این شمش نیستید")
        if bar.status != BarStatus.SOLD:
            raise ValueError("فقط شمش‌های فروخته‌شده قابل انتقال هستند")

        # Get owner's mobile for OTP
        owner = db.query(User).filter(User.id == from_customer_id).first()
        if not owner:
            raise ValueError("مالک یافت نشد")

        # Check owner isn't transferring to themselves
        if to_mobile == owner.mobile:
            raise ValueError("نمی‌توانید شمش را به خودتان انتقال دهید")

        # Cancel any existing pending transfer for this bar
        db.query(BarTransfer).filter(
            BarTransfer.bar_id == bar_id,
            BarTransfer.status == TransferStatus.PENDING,
        ).update({"status": TransferStatus.CANCELLED})

        # Generate OTP
        otp_raw = generate_otp()
        otp_hashed = hash_otp(owner.mobile, otp_raw)

        # Create transfer request
        transfer = BarTransfer(
            bar_id=bar_id,
            from_customer_id=from_customer_id,
            to_mobile=to_mobile,
            otp_hash=otp_hashed,
            otp_expiry=now_utc() + timedelta(minutes=5),
            status=TransferStatus.PENDING,
        )
        db.add(transfer)
        db.flush()

        return {
            "transfer_id": transfer.id,
            "otp_raw": otp_raw,
            "owner_mobile": owner.mobile,
        }

    def confirm_transfer(
        self, db: Session, transfer_id: int, from_customer_id: int, otp_code: str
    ) -> Bar:
        """
        Confirm transfer with OTP. Transfers ownership to recipient.
        If recipient has no account, generates a claim_code instead.
        """
        transfer = (
            db.query(BarTransfer)
            .filter(
                BarTransfer.id == transfer_id,
                BarTransfer.from_customer_id == from_customer_id,
                BarTransfer.status == TransferStatus.PENDING,
            )
            .first()
        )

        if not transfer:
            raise ValueError("درخواست انتقال یافت نشد یا منقضی شده")

        # Check expiry
        if transfer.otp_expiry and transfer.otp_expiry < now_utc():
            transfer.status = TransferStatus.EXPIRED
            db.flush()
            raise ValueError("کد تأیید منقضی شده است. لطفاً دوباره تلاش کنید")

        # Verify OTP
        owner = db.query(User).filter(User.id == from_customer_id).first()
        expected_hash = hash_otp(owner.mobile, otp_code.strip())
        if expected_hash != transfer.otp_hash:
            raise ValueError("کد تأیید اشتباه است")

        bar = db.query(Bar).filter(Bar.id == transfer.bar_id).with_for_update().first()
        if not bar or bar.customer_id != from_customer_id:
            raise ValueError("شمش قابل انتقال نیست")

        # Find recipient
        recipient = db.query(User).filter(User.mobile == transfer.to_mobile).first()

        if recipient:
            # Recipient has account → direct transfer
            bar.customer_id = recipient.id
            bar.claim_code = None
            new_owner_id = recipient.id
            desc = f"انتقال مالکیت به {recipient.full_name} ({transfer.to_mobile})"
        else:
            # Recipient has no account → generate claim_code
            bar.customer_id = None
            bar.claim_code = generate_unique_claim_code(db)
            new_owner_id = None
            desc = f"انتقال مالکیت به {transfer.to_mobile} (حساب کاربری ندارد — کد ثبت: {bar.claim_code})"

        # Ownership history
        db.add(OwnershipHistory(
            bar_id=bar.id,
            previous_owner_id=from_customer_id,
            new_owner_id=new_owner_id,
            description=desc,
        ))

        transfer.status = TransferStatus.COMPLETED
        db.flush()

        return bar

    def get_pending_transfer(self, db: Session, transfer_id: int, from_customer_id: int):
        """Get a pending transfer request."""
        return (
            db.query(BarTransfer)
            .filter(
                BarTransfer.id == transfer_id,
                BarTransfer.from_customer_id == from_customer_id,
                BarTransfer.status == TransferStatus.PENDING,
            )
            .first()
        )

    # ------------------------------------------
    # Custodial Delivery (تحویل امانی)
    # ------------------------------------------

    def create_delivery_request(
        self, db: Session, customer_id: int, bar_id: int, dealer_id: int,
    ) -> CustodialDeliveryRequest:
        """Create a custodial delivery request. Validates bar is custodial and undelivered."""
        bar = db.query(Bar).filter(Bar.id == bar_id).first()
        if not bar:
            raise ValueError("شمش یافت نشد")
        if bar.customer_id != customer_id:
            raise ValueError("شما مالک این شمش نیستید")
        if bar.status != BarStatus.SOLD:
            raise ValueError("فقط شمش‌های فروخته‌شده قابل درخواست تحویل هستند")
        if bar.delivered_at is not None:
            raise ValueError("این شمش قبلاً تحویل داده شده است")

        # Check no active request exists
        existing = db.query(CustodialDeliveryRequest).filter(
            CustodialDeliveryRequest.bar_id == bar_id,
            CustodialDeliveryRequest.status == CustodialDeliveryStatus.PENDING,
        ).first()
        if existing:
            raise ValueError("یک درخواست تحویل فعال برای این شمش وجود دارد")

        # Validate dealer
        dealer = db.query(User).filter(User.id == dealer_id, User.is_dealer == True, User.is_active == True).first()
        if not dealer:
            raise ValueError("نمایندگی انتخاب‌شده معتبر نیست")

        req = CustodialDeliveryRequest(
            customer_id=customer_id,
            bar_id=bar_id,
            dealer_id=dealer_id,
            status=CustodialDeliveryStatus.PENDING,
        )
        db.add(req)
        db.flush()
        return req

    def send_delivery_otp(self, db: Session, request_id: int, customer_id: int) -> Dict[str, Any]:
        """Generate and return OTP for delivery confirmation. OTP sent to customer mobile."""
        req = db.query(CustodialDeliveryRequest).filter(
            CustodialDeliveryRequest.id == request_id,
            CustodialDeliveryRequest.customer_id == customer_id,
            CustodialDeliveryRequest.status == CustodialDeliveryStatus.PENDING,
        ).first()
        if not req:
            raise ValueError("درخواست تحویل یافت نشد")

        customer = db.query(User).filter(User.id == customer_id).first()
        if not customer:
            raise ValueError("مشتری یافت نشد")

        otp_raw = generate_otp()
        otp_hashed = hash_otp(customer.mobile, otp_raw)

        req.otp_hash = otp_hashed
        req.otp_expiry = now_utc() + timedelta(minutes=10)
        db.flush()

        return {
            "request_id": req.id,
            "otp_raw": otp_raw,
            "customer_mobile": customer.mobile,
        }

    def confirm_delivery(
        self, db: Session, request_id: int, dealer_id: int, otp_code: str, serial_code: str,
    ) -> CustodialDeliveryRequest:
        """Dealer confirms delivery: verify OTP + serial, mark delivered."""
        req = db.query(CustodialDeliveryRequest).filter(
            CustodialDeliveryRequest.id == request_id,
            CustodialDeliveryRequest.dealer_id == dealer_id,
            CustodialDeliveryRequest.status == CustodialDeliveryStatus.PENDING,
        ).first()
        if not req:
            raise ValueError("درخواست تحویل یافت نشد")

        # Check expiry
        if not req.otp_hash or not req.otp_expiry:
            raise ValueError("ابتدا کد تأیید باید ارسال شود")
        if req.otp_expiry < now_utc():
            raise ValueError("کد تأیید منقضی شده است")

        # Verify serial
        bar = db.query(Bar).filter(Bar.id == req.bar_id).first()
        if not bar or bar.serial_code != serial_code.strip().upper():
            raise ValueError("سریال شمش مطابقت ندارد")

        # Verify OTP
        customer = db.query(User).filter(User.id == req.customer_id).first()
        expected_hash = hash_otp(customer.mobile, otp_code.strip())
        if expected_hash != req.otp_hash:
            raise ValueError("کد تأیید اشتباه است")

        # Mark delivered
        bar.delivered_at = now_utc()
        req.status = CustodialDeliveryStatus.COMPLETED
        req.completed_at = now_utc()
        req.completed_by = f"dealer:{dealer_id}"

        # Ownership history
        db.add(OwnershipHistory(
            bar_id=bar.id,
            previous_owner_id=bar.customer_id,
            new_owner_id=bar.customer_id,
            description="تحویل فیزیکی امانی (تأیید با OTP)",
        ))

        # Dealer transfer record
        db.add(DealerTransfer(
            bar_id=bar.id,
            from_dealer_id=bar.dealer_id,
            to_dealer_id=None,
            transferred_by=f"dealer:{dealer_id}",
            description=f"تحویل امانی به مشتری (درخواست #{req.id})",
            transfer_type=TransferType.CUSTODIAL_DELIVERY,
            reference_type="custodial_delivery",
            reference_id=req.id,
        ))

        db.flush()
        return req

    def cancel_delivery_request(
        self, db: Session, request_id: int, customer_id: int, reason: str = None,
    ) -> CustodialDeliveryRequest:
        """Customer cancels a pending delivery request."""
        req = db.query(CustodialDeliveryRequest).filter(
            CustodialDeliveryRequest.id == request_id,
            CustodialDeliveryRequest.customer_id == customer_id,
            CustodialDeliveryRequest.status == CustodialDeliveryStatus.PENDING,
        ).first()
        if not req:
            raise ValueError("درخواست تحویل یافت نشد")

        req.status = CustodialDeliveryStatus.CANCELLED
        req.cancelled_at = now_utc()
        req.cancel_reason = reason
        db.flush()
        return req

    def get_customer_delivery_requests(self, db: Session, customer_id: int) -> List:
        """List delivery requests for a customer."""
        return db.query(CustodialDeliveryRequest).filter(
            CustodialDeliveryRequest.customer_id == customer_id,
        ).order_by(CustodialDeliveryRequest.created_at.desc()).all()

    def get_dealer_delivery_requests(
        self, db: Session, dealer_id: int, status_filter: str = None,
    ) -> List:
        """List delivery requests assigned to a dealer."""
        query = db.query(CustodialDeliveryRequest).filter(
            CustodialDeliveryRequest.dealer_id == dealer_id,
        )
        if status_filter:
            query = query.filter(CustodialDeliveryRequest.status == status_filter)
        return query.order_by(CustodialDeliveryRequest.created_at.desc()).all()

    def get_delivery_request(self, db: Session, request_id: int) -> Optional[CustodialDeliveryRequest]:
        """Get a single delivery request with relationships."""
        return db.query(CustodialDeliveryRequest).filter(
            CustodialDeliveryRequest.id == request_id,
        ).first()


ownership_service = OwnershipService()
