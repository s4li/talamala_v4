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
from modules.inventory.models import Bar, BarStatus, OwnershipHistory, BarTransfer, TransferStatus
from modules.customer.models import Customer


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

        for bar in bars:
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
        owner = db.query(Customer).filter(Customer.id == from_customer_id).first()
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
        owner = db.query(Customer).filter(Customer.id == from_customer_id).first()
        expected_hash = hash_otp(owner.mobile, otp_code.strip())
        if expected_hash != transfer.otp_hash:
            raise ValueError("کد تأیید اشتباه است")

        bar = db.query(Bar).filter(Bar.id == transfer.bar_id).with_for_update().first()
        if not bar or bar.customer_id != from_customer_id:
            raise ValueError("شمش قابل انتقال نیست")

        # Find recipient
        recipient = db.query(Customer).filter(Customer.mobile == transfer.to_mobile).first()

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


ownership_service = OwnershipService()
