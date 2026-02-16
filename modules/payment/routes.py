"""
Payment Routes
================
Wallet pay, Zibal gateway redirect/callback, admin refund.
"""

import urllib.parse
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_customer, require_permission
from modules.payment.service import payment_service

router = APIRouter(prefix="/payment", tags=["payment"])


# ==========================================
# 💰 Pay from Wallet
# ==========================================

@router.post("/{order_id}/wallet")
async def pay_wallet(
    request: Request,
    order_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    csrf_check(request, csrf_token)
    result = payment_service.pay_from_wallet(db, order_id, me.id)

    if result["success"]:
        db.commit()
        msg = urllib.parse.quote(result["message"])
        return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result["message"])
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)


# ==========================================
# 🏦 Zibal: Redirect to Gateway
# ==========================================

@router.post("/{order_id}/zibal")
async def pay_zibal(
    request: Request,
    order_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    csrf_check(request, csrf_token)
    result = payment_service.create_zibal_payment(db, order_id, me.id)

    if result.get("success") and result.get("redirect_url"):
        db.commit()
        return RedirectResponse(result["redirect_url"], status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("message", "خطا"))
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)


# ==========================================
# 🏦 Zibal: Callback (user returns here)
# ==========================================

@router.get("/zibal/callback")
async def zibal_callback(
    request: Request,
    trackId: str = "",
    success: str = "",
    status: str = "",
    order_id: int = 0,
    db: Session = Depends(get_db),
):
    """
    Zibal redirects user here after payment attempt.
    Query params: trackId, success (1/0), status, orderId
    """
    if not trackId or not order_id:
        return RedirectResponse("/orders?error=پارامترهای+نامعتبر", status_code=303)

    # If user cancelled on gateway page
    if success == "0":
        error = urllib.parse.quote("پرداخت توسط کاربر لغو شد.")
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)

    result = payment_service.verify_zibal_callback(db, trackId, order_id)

    if result.get("success"):
        db.commit()
        msg = urllib.parse.quote(result["message"])
        return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("message", "پرداخت ناموفق"))
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)


# ==========================================
# 🔄 Admin: Refund
# ==========================================

@router.post("/{order_id}/refund")
async def refund_order(
    request: Request,
    order_id: int,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("orders")),
):
    csrf_check(request, csrf_token)
    result = payment_service.refund_order(db, order_id, admin_note)

    if result["success"]:
        db.commit()
        msg = urllib.parse.quote(result["message"])
        return RedirectResponse(f"/admin/orders?msg={msg}", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result["message"])
        return RedirectResponse(f"/admin/orders?error={error}", status_code=303)
