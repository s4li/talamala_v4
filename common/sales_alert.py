"""
TalaMala v4 - Sales SMS Alerts (fixed numbers)
================================================
پیامک اطلاع‌رسانی هر فروش (سفارش آنلاین + فروش POS) به شماره‌های ثابت.

اصول:
- متن **همگام** در همان سشن ساخته می‌شود (بعد از commit کالر، آبجکت‌های ORM
  expire می‌شوند و ترد پس‌زمینه دیگر نمی‌تواند آن‌ها را بخواند).
- ارسال در یک **ترد دیمن** انجام می‌شود تا هیچ‌وقت درخواست را بلاک نکند.
- هیچ استثنایی نباید عملیات مالی را fail کند.
"""

import logging
import threading

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger("talamala.sales_alert")

# شماره‌های ثابت دریافت‌کننده پیامک فروش (هارد‌کد به درخواست کارفرما)
SALES_ALERT_MOBILES = ["09121023589", "09120725564"]


# ----------------------------------------------------------------------
# ارسال
# ----------------------------------------------------------------------

def _send(text: str):
    """ارسال به همه شماره‌ها. داخل ترد دیمن اجرا می‌شود (بدون سشن DB)."""
    from common.sms import sms_sender
    for mobile in SALES_ALERT_MOBILES:
        try:
            sms_sender.send_plain_text(mobile, text)
        except Exception as e:
            logger.error(f"Sales alert SMS failed to {mobile}: {e}")


def send_async(text: str):
    """سپردن ارسال به ترد دیمن (غیر بلاکینگ)."""
    if not text:
        return
    threading.Thread(target=_send, args=(text,), daemon=True).start()


def send_after_commit(db: Session, text: str):
    """
    ارسال فقط بعد از commit موفق تراکنش.

    اگر همان‌جا بفرستیم و بعد پرداخت/سفارش rollback شود، پیامکِ فروشی رفته
    که هرگز ثبت نشده. با هوکِ after_commit، ترد فقط وقتی استارت می‌شود که
    تراکنش واقعاً کامیت شده باشد.

    نکته: هوکِ rollback هم لازم است. بدون آن، لیسنرِ یک تراکنشِ rollback‌شده
    روی سشن باقی می‌ماند و با **کامیت بعدیِ همان سشن** شلیک می‌کند — یعنی
    پیامک فروشی که کنسل شده، همراه فروش بعدی ارسال می‌شود.
    """
    if not text:
        return

    state = {"done": False}

    def _on_commit(_session):
        if state["done"]:
            return
        state["done"] = True
        send_async(text)

    def _on_rollback(_session, _previous_transaction):
        state["done"] = True  # تراکنش برنگشت → پیامک نباید برود

    event.listen(db, "after_commit", _on_commit)
    event.listen(db, "after_soft_rollback", _on_rollback)


# ----------------------------------------------------------------------
# سفارش آنلاین
# ----------------------------------------------------------------------

def build_order_alert_text(db: Session, order) -> str:
    """متن پیامک سفارش فروشگاه اینترنتی."""
    from modules.user.models import User
    from modules.catalog.models import Product
    from modules.order.models import DeliveryMethod

    buyer = db.query(User).filter(User.id == order.customer_id).first()
    buyer_name = (buyer.full_name if buyer else "") or "نامشخص"
    buyer_mobile = buyer.mobile if buyer else "-"

    lines = [f"طلاملا | سفارش جدید #{order.id}"]
    lines.append(f"خریدار: {buyer_name} - {buyer_mobile}")

    for oi in order.items:
        product = db.query(Product).filter(Product.id == oi.product_id).first()
        name = product.name if product else f"محصول #{oi.product_id}"
        serial = oi.bar.serial_code if oi.bar else "-"
        lines.append(f"- {name} | سریال: {serial}")

    if order.is_gold_order:
        lines.append(f"مبلغ: {(order.gold_total_mg or 0) / 1000:.3f} گرم طلا")
    else:
        lines.append(f"مبلغ: {int(order.payable_total or 0) // 10:,} تومان")

    if order.delivery_method == DeliveryMethod.PICKUP:
        dealer = order.pickup_dealer
        where = dealer.display_name if dealer else "نامشخص"
        lines.append(f"تحویل: حضوری - {where}")
    else:
        city = order.shipping_city or ""
        province = order.shipping_province or ""
        lines.append(f"تحویل: پستی - {province} {city}".strip())

    return "\n".join(lines)


def notify_order_async(db: Session, order):
    """متن سفارش را همگام می‌سازد و ارسال را به ترد پس‌زمینه می‌سپارد."""
    try:
        text = build_order_alert_text(db, order)
    except Exception as e:
        logger.error(f"Building order alert text failed for order #{order.id}: {e}")
        return
    send_after_commit(db, text)


# ----------------------------------------------------------------------
# فروش POS (نماینده / دستگاه مشتری / راسیس)
# ----------------------------------------------------------------------

def build_sale_alert_text(db: Session, sale, source_label: str) -> str:
    """
    متن پیامک فروش POS.

    Args:
        sale: آبجکت DealerSale (باید flush شده باشد تا id داشته باشد)
        source_label: منبع فروش، مثلاً «پوز نماینده» / «پوز مشتری» / «دستگاه راسیس»
    """
    from modules.user.models import User
    from modules.catalog.models import Product

    dealer = db.query(User).filter(User.id == sale.dealer_id).first()
    dealer_name = (dealer.display_name if dealer else "") or "نامشخص"

    bar = sale.bar
    serial = bar.serial_code if bar else "-"
    product = None
    if bar and bar.product_id:
        product = db.query(Product).filter(Product.id == bar.product_id).first()
    product_name = product.name if product else "نامشخص"

    metal_label = "نقره" if (sale.metal_type or "gold") == "silver" else "طلا"

    lines = [f"طلاملا | فروش {source_label} #{sale.id}"]
    lines.append(f"نماینده: {dealer_name}")
    lines.append(f"- {product_name} ({metal_label}) | سریال: {serial}")
    lines.append(f"مبلغ: {int(sale.sale_price or 0) // 10:,} تومان")

    customer_name = sale.customer_name or "نامشخص"
    customer_mobile = sale.customer_mobile or "-"
    lines.append(f"خریدار: {customer_name} - {customer_mobile}")

    return "\n".join(lines)


def notify_sale_async(db: Session, sale, source_label: str):
    """متن فروش POS را همگام می‌سازد و ارسال را به ترد پس‌زمینه می‌سپارد."""
    try:
        text = build_sale_alert_text(db, sale, source_label)
    except Exception as e:
        logger.error(f"Building sale alert text failed for sale #{getattr(sale, 'id', '?')}: {e}")
        return
    send_after_commit(db, text)
