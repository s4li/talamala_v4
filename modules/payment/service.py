"""
Payment Service
=================
Wallet payment + Multi-gateway support (Zibal, Sepehr, Top, Parsian).
Active gateway is selected via SystemSetting("active_gateway").
"""

import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from modules.order.models import Order, OrderStatus
from modules.order.service import order_service
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode
from modules.admin.models import SystemSetting
from common.helpers import now_utc
from config.settings import BASE_URL

# Import gateway modules to trigger register_gateway() calls
from modules.payment.gateways import get_gateway, GatewayPaymentRequest  # noqa: F401
import modules.payment.gateways.zibal     # noqa: F401
import modules.payment.gateways.sepehr    # noqa: F401
import modules.payment.gateways.top       # noqa: F401
import modules.payment.gateways.parsian   # noqa: F401

logger = logging.getLogger("talamala.payment")

DEFAULT_GATEWAYS = "sepehr,top,parsian"


def _build_order_admin_alert(db: Session, order) -> str:
    """Build admin alert text from order items: weight + metal type per item."""
    from modules.order.models import OrderItem
    from modules.catalog.models import Product

    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    parts = []
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            metal_label = "طلا" if product.metal_type == "gold" else "نقره"
            parts.append(f"{product.weight}g {metal_label}")

    if parts:
        return "[هشدار] فروش شمش " + " + ".join(parts)
    return f"[هشدار] فروش سفارش #{order.id}"


class PaymentService:

    # ==========================================
    # 🔧 Gateway Selection
    # ==========================================

    def get_enabled_gateways(self, db: Session) -> list:
        """Read enabled gateways from SystemSetting, returns list of names."""
        setting = db.query(SystemSetting).filter(SystemSetting.key == "enabled_gateways").first()
        raw = setting.value if setting else DEFAULT_GATEWAYS
        return [g.strip() for g in raw.split(",") if g.strip()]

    # ==========================================
    # 💰 Pay from Wallet
    # ==========================================

    def pay_from_wallet(self, db: Session, order_id: int, customer_id: int) -> Dict[str, Any]:
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
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

        try:
            from modules.notification.service import notification_service
            from modules.notification.models import NotificationType

            # Build admin alert text with weight info
            admin_text = _build_order_admin_alert(db, order)

            notification_service.send(
                db, customer_id,
                notification_type=NotificationType.PAYMENT_SUCCESS,
                title=f"پرداخت سفارش #{order_id}",
                body=f"سفارش #{order_id} با موفقیت از کیف پول پرداخت شد.",
                link=f"/orders/{order_id}",
                sms_text=f"طلاملا: سفارش #{order_id} پرداخت شد. talamala.com/orders/{order_id}",
                reference_type="order_paid", reference_id=str(order_id),
                admin_alert_text=admin_text,
            )
        except Exception:
            pass

        return {
            "success": True,
            "message": f"سفارش #{order_id} با موفقیت از کیف پول پرداخت شد",
            "order": result,
        }

    # ==========================================
    # 🏦 Gateway Payment (generic)
    # ==========================================

    def create_gateway_payment(
        self, db: Session, order_id: int, customer_id: int, gateway_name: str = ""
    ) -> Dict[str, Any]:
        """Create payment via the customer-selected gateway."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.customer_id != customer_id or order.status != OrderStatus.PENDING:
            return {"success": False, "message": "سفارش نامعتبر"}

        # Validate gateway is enabled
        enabled = self.get_enabled_gateways(db)
        if not gateway_name or gateway_name not in enabled:
            return {"success": False, "message": "لطفاً یک درگاه پرداخت معتبر انتخاب کنید"}

        gw = get_gateway(gateway_name)
        if not gw:
            return {"success": False, "message": f"درگاه {gateway_name} در دسترس نیست"}

        amount = order.grand_total
        callback_url = f"{BASE_URL}/payment/{gateway_name}/callback?order_id={order_id}"

        result = gw.create_payment(GatewayPaymentRequest(
            amount_irr=amount,
            callback_url=callback_url,
            description=f"سفارش #{order_id} طلاملا",
            order_ref=str(order_id),
        ))
        if result.success:
            order.track_id = result.track_id
            
            db.flush()
            return {
                "success": True,
                "redirect_url": result.redirect_url,
                "gateway": gateway_name,
            }
        else:
            return {"success": False, "message": result.error_message}

    def verify_gateway_callback(
        self, db: Session, gateway_name: str, params: Dict[str, Any], order_id: int
    ) -> Dict[str, Any]:
        """Verify callback from any gateway."""
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order:
            return {"success": False, "message": "سفارش یافت نشد"}
        if order.status != OrderStatus.PENDING:
            # Already processed (double callback protection)
            if order.status == OrderStatus.PAID:
                return {"success": True, "message": "این سفارش قبلاً پرداخت شده"}
            return {"success": False, "message": "سفارش لغو شده"}

        gw = get_gateway(gateway_name)
        if not gw:
            return {"success": False, "message": f"درگاه {gateway_name} شناسایی نشد"}

        # For Sepehr, inject expected_amount for verification
        if gateway_name == "sepehr":
            params["expected_amount"] = order.grand_total

        result = gw.verify_payment(params)

        if result.success:
            order.payment_method = f"gateway_{gateway_name}"
            order.payment_ref = result.ref_number
            order.paid_at = now_utc()

            finalized = order_service.finalize_order(db, order_id)
            if finalized:
                try:
                    from modules.notification.service import notification_service
                    from modules.notification.models import NotificationType

                    admin_text = _build_order_admin_alert(db, order)

                    notification_service.send(
                        db, order.customer_id,
                        notification_type=NotificationType.PAYMENT_SUCCESS,
                        title=f"پرداخت سفارش #{order_id}",
                        body=f"سفارش #{order_id} با موفقیت پرداخت شد. مرجع: {result.ref_number}",
                        link=f"/orders/{order_id}",
                        sms_text=f"طلاملا: سفارش #{order_id} پرداخت شد. talamala.com/orders/{order_id}",
                        reference_type="order_paid", reference_id=str(order_id),
                        admin_alert_text=admin_text,
                    )
                except Exception:
                    pass
                return {"success": True, "message": f"پرداخت موفق! مرجع: {result.ref_number}"}
            return {"success": False, "message": "خطا در نهایی‌سازی سفارش"}
        else:
            try:
                from modules.notification.service import notification_service
                from modules.notification.models import NotificationType
                notification_service.send(
                    db, order.customer_id,
                    notification_type=NotificationType.PAYMENT_FAILED,
                    title=f"پرداخت ناموفق سفارش #{order_id}",
                    body=f"پرداخت سفارش #{order_id} ناموفق بود. {result.error_message}",
                    link=f"/orders/{order_id}",
                    reference_type="order_payment_failed", reference_id=str(order_id),
                )
            except Exception:
                pass
            return {"success": False, "message": result.error_message}

    # ==========================================
    # 🔄 Refund to Wallet
    # ==========================================

    def refund_order(self, db: Session, order_id: int, admin_note: str = "") -> Dict[str, Any]:
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
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
