"""
Payment Service
=================
Wallet payment + Zibal gateway (sandbox/production).

Zibal Sandbox: merchant = "zibal" → all payments auto-succeed.
Zibal Production: set ZIBAL_MERCHANT env to real merchant ID.
"""

import logging
import httpx
from typing import Dict, Any
from sqlalchemy.orm import Session

from modules.order.models import Order, OrderStatus
from modules.order.service import order_service
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode
from common.helpers import now_utc
from config.settings import ZIBAL_MERCHANT, BASE_URL

logger = logging.getLogger("talamala.payment")

ZIBAL_REQUEST_URL = "https://gateway.zibal.ir/v1/request"
ZIBAL_VERIFY_URL = "https://gateway.zibal.ir/v1/verify"
ZIBAL_START_URL = "https://gateway.zibal.ir/start/{trackId}"


class PaymentService:

    # ==========================================
    # 💰 Pay from Wallet
    # ==========================================

    def pay_from_wallet(self, db: Session, order_id: int, customer_id: int) -> Dict[str, Any]:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"success": False, "message": "سفارش یافت نشد"}
        if order.customer_id != customer_id:
            return {"success": False, "message": "این سفارش متعلق به شما نیست"}
        if order.status != OrderStatus.PENDING:
            return {"success": False, "message": "این سفارش قابل پرداخت نیست"}

        amount = order.grand_total
        if amount < 0:
            return {"success": False, "message": "مبلغ سفارش نامعتبر است"}

        # Zero-amount order (100% discount) — no wallet deduction needed
        if amount > 0:
            balance = wallet_service.get_balance(db, customer_id, AssetCode.IRR)
            if balance["available"] < amount:
                deficit = amount - balance["available"]
                return {
                    "success": False,
                    "message": f"موجودی کیف پول کافی نیست. کسری: {deficit // 10:,} تومان",
                }

            try:
                wallet_service.withdraw(
                    db, customer_id, amount,
                    reference_type="order",
                    reference_id=str(order_id),
                    description=f"پرداخت سفارش #{order_id}",
                    consume_credit=True,
                )
            except ValueError as e:
                return {"success": False, "message": f"خطا در کسر از کیف پول: {e}"}

        order.payment_method = "coupon_free" if amount == 0 else "wallet"
        order.payment_ref = f"COUPON-FREE-{order_id}" if amount == 0 else f"WALLET-{customer_id}-{order_id}"
        order.paid_at = now_utc()
        result = order_service.finalize_order(db, order_id)

        if not result:
            if amount > 0:
                try:
                    wallet_service.deposit(
                        db, customer_id, amount,
                        reference_type="refund",
                        reference_id=str(order_id),
                        description=f"بازگشت وجه سفارش #{order_id} (خطا)",
                        idempotency_key=f"refund:finalize_fail:{order_id}",
                    )
                except Exception as e:
                    logger.error(f"Failed to refund wallet after finalize failure for order #{order_id}: {e}")
            return {"success": False, "message": "خطا در نهایی‌سازی سفارش"}

        logger.info(f"Order #{order_id} paid from wallet by customer #{customer_id}")
        return {
            "success": True,
            "message": f"سفارش #{order_id} با موفقیت از کیف پول پرداخت شد",
            "order": result,
        }

    # ==========================================
    # 🏦 Zibal Gateway
    # ==========================================

    def create_zibal_payment(self, db: Session, order_id: int, customer_id: int) -> Dict[str, Any]:
        """Create Zibal payment → redirect URL."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.customer_id != customer_id or order.status != OrderStatus.PENDING:
            return {"success": False, "message": "سفارش نامعتبر"}

        amount = order.grand_total
        callback_url = f"{BASE_URL}/payment/zibal/callback?order_id={order_id}"

        try:
            resp = httpx.post(ZIBAL_REQUEST_URL, json={
                "merchant": ZIBAL_MERCHANT,
                "amount": amount,
                "callbackUrl": callback_url,
                "description": f"سفارش #{order_id} طلاملا",
                "orderId": str(order_id),
            }, timeout=15)
            data = resp.json()
            logger.info(f"Zibal request order #{order_id}: {data}")

            if data.get("result") == 100:
                track_id = data["trackId"]
                order.track_id = str(track_id)
                db.flush()
                return {"success": True, "redirect_url": ZIBAL_START_URL.format(trackId=track_id)}
            else:
                msg = data.get("message", f"کد خطا: {data.get('result')}")
                return {"success": False, "message": f"خطا در درگاه: {msg}"}

        except httpx.TimeoutException:
            return {"success": False, "message": "درگاه پاسخ نداد. دوباره تلاش کنید."}
        except Exception as e:
            logger.error(f"Zibal request failed: {e}")
            return {"success": False, "message": f"خطا در اتصال به درگاه: {e}"}

    def verify_zibal_callback(self, db: Session, track_id: str, order_id: int) -> Dict[str, Any]:
        """Verify Zibal callback after user returns from gateway."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"success": False, "message": "سفارش یافت نشد"}
        if order.status != OrderStatus.PENDING:
            # Already processed (double callback protection)
            if order.status == OrderStatus.PAID:
                return {"success": True, "message": "این سفارش قبلاً پرداخت شده"}
            return {"success": False, "message": "سفارش لغو شده"}

        try:
            resp = httpx.post(ZIBAL_VERIFY_URL, json={
                "merchant": ZIBAL_MERCHANT,
                "trackId": int(track_id),
            }, timeout=15)
            data = resp.json()
            logger.info(f"Zibal verify order #{order_id}: {data}")

            if data.get("result") == 100:
                ref_number = data.get("refNumber", track_id)
                order.payment_method = "gateway_zibal"
                order.payment_ref = str(ref_number)
                order.paid_at = now_utc()

                result = order_service.finalize_order(db, order_id)
                if result:
                    return {"success": True, "message": f"پرداخت موفق! مرجع: {ref_number}"}
                return {"success": False, "message": "خطا در نهایی‌سازی سفارش"}
            else:
                msg = data.get("message", f"کد: {data.get('result')}")
                return {"success": False, "message": f"تراکنش ناموفق — {msg}"}

        except Exception as e:
            logger.error(f"Zibal verify failed: {e}")
            return {"success": False, "message": f"خطا در تأیید: {e}"}

    # ==========================================
    # 🔄 Refund to Wallet
    # ==========================================

    def refund_order(self, db: Session, order_id: int, admin_note: str = "") -> Dict[str, Any]:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"success": False, "message": "سفارش یافت نشد"}
        if order.status != OrderStatus.PAID:
            return {"success": False, "message": "فقط سفارشات پرداخت‌شده قابل استرداد هستند"}

        amount = order.grand_total
        try:
            wallet_service.deposit(
                db, order.customer_id, amount,
                reference_type="refund",
                reference_id=str(order_id),
                description=f"استرداد سفارش #{order_id}" + (f" — {admin_note}" if admin_note else ""),
                idempotency_key=f"refund:order:{order_id}",
            )
            order_service._release_order_bars(db, order)
            order.status = OrderStatus.CANCELLED
            reason = "استرداد وجه توسط مدیر" + (f" — {admin_note}" if admin_note else "")
            order.cancellation_reason = reason
            from common.helpers import now_utc
            order.cancelled_at = now_utc()
            order_service.log_status_change(
                db, order.id, "status",
                old_value=OrderStatus.PAID, new_value=OrderStatus.CANCELLED,
                changed_by="admin", description=reason,
            )
            db.flush()
            logger.info(f"Order #{order_id} refunded: {amount} IRR")
            return {
                "success": True,
                "message": f"سفارش #{order_id} استرداد شد. {amount // 10:,} تومان به کیف پول واریز شد.",
            }
        except Exception as e:
            return {"success": False, "message": f"خطا: {e}"}


payment_service = PaymentService()
