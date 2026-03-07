"""
Order Module - Admin Routes
==============================
Order management for admin: list, approve (finalize), cancel.
"""

import logging
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.order.service import order_service
from modules.order.models import OrderStatus, DeliveryStatus, DeliveryMethod

logger = logging.getLogger("talamala.order.admin")

router = APIRouter(tags=["order-admin"])


@router.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(
    request: Request,
    status: str = Query(None),
    delivery: str = Query(None),
    search: str = Query(None),
    msg: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("orders")),
):
    orders = order_service.get_all_orders(db, status=status, delivery=delivery, search=search)
    pending_stats = order_service.get_pending_delivery_stats(db)

    csrf = new_csrf_token(request)
    response = templates.TemplateResponse("admin/orders/list.html", {
        "request": request,
        "user": user,
        "orders": orders,
        "pending_stats": pending_stats,
        "status_filter": status or "",
        "delivery_filter": delivery or "",
        "search_query": search or "",
        "order_statuses": OrderStatus,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/orders/{order_id}/approve")
async def approve_order(
    request: Request,
    order_id: int,
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("orders", level="full")),
):
    """Admin approves/finalizes a pending order (marks as Paid, transfers bars)."""
    csrf_check(request, csrf_token)
    result = order_service.finalize_order(db, order_id)
    db.commit()
    if result:
        msg = urllib.parse.quote(f"سفارش #{order_id} تأیید و شمش‌ها منتقل شد.")
    else:
        msg = urllib.parse.quote("فقط سفارشات در انتظار قابل تأیید هستند.")
    return RedirectResponse(f"/admin/orders?msg={msg}", status_code=303)


@router.post("/admin/orders/{order_id}/cancel")
async def cancel_order_admin(
    request: Request,
    order_id: int,
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("orders", level="full")),
):
    """Admin cancels a pending order and releases bars."""
    csrf_check(request, csrf_token)
    result = order_service.cancel_order(db, order_id, reason="لغو توسط مدیر سیستم", changed_by=user.full_name)
    db.commit()
    if result:
        msg = urllib.parse.quote(f"سفارش #{order_id} لغو و شمش‌ها آزاد شد.")
    else:
        msg = urllib.parse.quote("فقط سفارشات در انتظار قابل لغو هستند.")
    return RedirectResponse(f"/admin/orders?msg={msg}", status_code=303)


# ==========================================
# 🚚 Delivery Management
# ==========================================

@router.post("/admin/orders/{order_id}/delivery-status")
async def update_delivery_status(
    request: Request,
    order_id: int,
    delivery_status: str = Form(...),
    postal_tracking_code: str = Form(""),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("orders", level="edit")),
):
    """Update delivery status and optionally add postal tracking code."""
    csrf_check(request, csrf_token)
    from modules.order.models import Order
    from common.helpers import now_utc

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.status != OrderStatus.PAID:
        msg = urllib.parse.quote("فقط سفارشات پرداخت‌شده قابل بروزرسانی هستند.")
        return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)

    old_delivery = order.delivery_status
    order.delivery_status = delivery_status

    order_service.log_status_change(
        db, order_id, "delivery_status",
        old_value=old_delivery, new_value=delivery_status,
        changed_by=user.full_name, description="بروزرسانی وضعیت تحویل",
    )

    if postal_tracking_code:
        order.postal_tracking_code = postal_tracking_code

    if delivery_status == DeliveryStatus.DELIVERED:
        order.delivered_at = now_utc()

        # Mark all bars in this order as physically delivered
        from modules.order.models import OrderItem
        from modules.inventory.models import Bar
        bar_ids = [oi.bar_id for oi in db.query(OrderItem.bar_id).filter(OrderItem.order_id == order.id).all() if oi.bar_id]
        if bar_ids:
            db.query(Bar).filter(Bar.id.in_(bar_ids)).update({"delivered_at": now_utc()}, synchronize_session=False)

        # Settle cashback coupon if applicable
        if order.promo_choice == "CASHBACK" and order.promo_amount and not order.cashback_settled:
            try:
                from modules.wallet.service import wallet_service
                wallet_service.deposit(
                    db, order.customer_id, order.promo_amount,
                    reference_type="cashback",
                    reference_id=str(order.id),
                    description=f"کشبک سفارش #{order.id}" + (f" (کد: {order.coupon_code})" if order.coupon_code else ""),
                    idempotency_key=f"cashback:order:{order.id}",
                )
                order.cashback_settled = True
            except Exception as e:
                logger.error(f"Cashback settlement failed for order #{order.id}: {e}")

    try:
        from modules.notification.service import notification_service
        from modules.notification.models import NotificationType
        delivery_labels = {
            "Preparing": "در حال آماده‌سازی",
            "Shipped": "ارسال شده",
            "Delivered": "تحویل داده شده",
        }
        label = delivery_labels.get(delivery_status, delivery_status)
        sms = f"طلاملا: سفارش #{order_id} — {label}"
        if postal_tracking_code:
            sms += f" کد رهگیری: {postal_tracking_code}"
        notification_service.send(
            db, order.customer_id,
            notification_type=NotificationType.ORDER_DELIVERY,
            title=f"بروزرسانی ارسال سفارش #{order_id}",
            body=f"وضعیت تحویل سفارش #{order_id}: {label}",
            link=f"/orders/{order_id}",
            sms_text=sms,
            reference_type="delivery", reference_id=f"{order_id}:{delivery_status}",
        )
    except Exception:
        pass

    db.commit()
    msg = urllib.parse.quote("وضعیت تحویل بروزرسانی شد.")
    return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)


@router.post("/admin/orders/{order_id}/confirm-pickup")
async def confirm_pickup_delivery(
    request: Request,
    order_id: int,
    delivery_code: str = Form(...),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("orders", level="edit")),
):
    """Confirm in-person pickup by verifying the delivery code."""
    csrf_check(request, csrf_token)
    from modules.order.models import Order
    from modules.order.delivery_service import verify_delivery_code
    from common.helpers import now_utc

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.status != OrderStatus.PAID:
        msg = urllib.parse.quote("سفارش قابل تحویل نیست.")
        return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)

    if order.delivery_method != DeliveryMethod.PICKUP:
        msg = urllib.parse.quote("این سفارش ارسال پستی است.")
        return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)

    if not order.delivery_code_hash:
        msg = urllib.parse.quote("کد تحویل برای این سفارش ثبت نشده.")
        return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)

    if not verify_delivery_code(delivery_code.strip(), order.delivery_code_hash):
        msg = urllib.parse.quote("❌ کد تحویل نادرست است!")
        return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)

    old_delivery = order.delivery_status
    order.delivery_status = DeliveryStatus.DELIVERED
    order.delivered_at = now_utc()

    # Mark all bars in this order as physically delivered
    from modules.order.models import OrderItem
    from modules.inventory.models import Bar
    bar_ids = [oi.bar_id for oi in db.query(OrderItem.bar_id).filter(OrderItem.order_id == order.id).all() if oi.bar_id]
    if bar_ids:
        db.query(Bar).filter(Bar.id.in_(bar_ids)).update({"delivered_at": now_utc()}, synchronize_session=False)

    order_service.log_status_change(
        db, order_id, "delivery_status",
        old_value=old_delivery, new_value=DeliveryStatus.DELIVERED,
        changed_by=user.full_name, description="تأیید تحویل حضوری با کد تحویل",
    )

    # Settle cashback coupon if applicable
    if order.promo_choice == "CASHBACK" and order.promo_amount and not order.cashback_settled:
        try:
            from modules.wallet.service import wallet_service
            wallet_service.deposit(
                db, order.customer_id, order.promo_amount,
                reference_type="cashback",
                reference_id=str(order.id),
                description=f"کشبک سفارش #{order.id}" + (f" (کد: {order.coupon_code})" if order.coupon_code else ""),
                idempotency_key=f"cashback:order:{order.id}",
            )
            order.cashback_settled = True
        except Exception as e:
            logger.error(f"Cashback settlement failed for order #{order.id}: {e}")

    db.commit()

    msg = urllib.parse.quote("✅ تحویل تأیید شد. کد تحویل صحیح بود.")
    return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)
