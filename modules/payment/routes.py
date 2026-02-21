"""
Payment Routes
================
Wallet pay, multi-gateway redirect/callback, admin refund.
"""

import urllib.parse
from fastapi import APIRouter, Request, Depends, Form, Query
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
# 🏦 Gateway: Unified Redirect
# ==========================================

@router.post("/{order_id}/gateway")
async def pay_gateway(
    request: Request,
    order_id: int,
    csrf_token: str = Form(""),
    gateway: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    """Redirect to the customer-selected gateway."""
    csrf_check(request, csrf_token)
    result = payment_service.create_gateway_payment(db, order_id, me.id, gateway_name=gateway)

    if result.get("success") and result.get("redirect_url"):
        db.commit()
        return RedirectResponse(result["redirect_url"], status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("message", "خطا"))
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)


# ==========================================
# 🏦 Zibal: Callback (GET — backward compatible)
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
    """Zibal redirects user here after payment attempt (GET with query params)."""
    if not trackId or not order_id:
        return RedirectResponse("/orders?error=پارامترهای+نامعتبر", status_code=303)

    # User cancelled on gateway page
    if success == "0":
        error = urllib.parse.quote("پرداخت توسط کاربر لغو شد.")
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)

    result = payment_service.verify_gateway_callback(db, "zibal", {"trackId": trackId}, order_id)

    if result.get("success"):
        db.commit()
        msg = urllib.parse.quote(result["message"])
        return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("message", "پرداخت ناموفق"))
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)


# ==========================================
# 🏦 Sepehr: Callback (POST — bank sends form data)
# ==========================================

@router.post("/sepehr/callback")
async def sepehr_callback(
    request: Request,
    respcode: int = Form(...),
    respmsg: str = Form(None),
    invoiceid: str = Form(...),
    amount: int = Form(...),
    digitalreceipt: str = Form(None),
    db: Session = Depends(get_db),
):
    """
    Sepehr bank callback (POST with form data).
    invoiceid = order_id, digitalreceipt = track for Advice verify.
    """
    try:
        order_id = int(invoiceid)
    except (ValueError, TypeError):
        return RedirectResponse("/orders?error=پارامترهای+نامعتبر", status_code=303)

    # Bank reports error
    if respcode != 0:
        error = urllib.parse.quote(f"پرداخت ناموفق: {respmsg or 'خطای بانکی'}")
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)

    # No receipt
    if not digitalreceipt:
        error = urllib.parse.quote("کد پیگیری دریافت نشد.")
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)

    result = payment_service.verify_gateway_callback(
        db, "sepehr",
        {"digitalreceipt": digitalreceipt, "expected_amount": amount},
        order_id,
    )

    if result.get("success"):
        db.commit()
        msg = urllib.parse.quote(result["message"])
        return RedirectResponse(f"/orders/{order_id}?msg={msg}", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("message", "پرداخت ناموفق"))
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)


# ==========================================
# 🏦 Top: Callback (GET — gateway sends query params)
# ==========================================

@router.get("/top/callback")
async def top_callback(
    request: Request,
    token: str | list[str] = Query(None, alias="token"),
    status: int = Query(None, alias="status"),
    MerchantOrderId: int = Query(None, alias="MerchantOrderId"),
    order_id: int = Query(0),
    db: Session = Depends(get_db),
):
    """
    Top gateway callback (GET with query params).
    token + MerchantOrderId used for verification.
    order_id passed in callback URL by us.
    """
    # Resolve order_id from our callback param or MerchantOrderId
    final_order_id = order_id or MerchantOrderId
    if not final_order_id or not token:
        return RedirectResponse("/orders?error=پارامترهای+نامعتبر", status_code=303)

    if isinstance(token, list):
        token = token[0]
    result = payment_service.verify_gateway_callback(
        db, "top",
        {"token": token, "MerchantOrderId": str(final_order_id)},
        final_order_id,
    )

    if result.get("success"):
        db.commit()
        msg = urllib.parse.quote(result["message"])
        return RedirectResponse(f"/orders/{final_order_id}?msg={msg}", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("message", "پرداخت ناموفق"))
        return RedirectResponse(f"/orders/{final_order_id}?error={error}", status_code=303)


# ==========================================
# 🏦 Parsian: Callback (POST — bank sends form data)
# ==========================================

@router.post("/parsian/callback")
async def parsian_callback(
    request: Request,
    Token: str = Form(None),
    status: int = Form(None),
    RRN: int = Form(None),
    order_id: int = Form(0),
    db: Session = Depends(get_db),
):
    """
    Parsian bank callback (POST with form data).
    Token + status + RRN from bank. order_id passed in callback URL by us.
    """
    # Resolve order_id: either from form data or find order by track_id (Token)
    if not order_id and Token:
        from modules.order.models import Order
        order = db.query(Order).filter(Order.track_id == str(Token)).first()
        if order:
            order_id = order.id

    if not order_id:
        return RedirectResponse("/orders?error=پارامترهای+نامعتبر", status_code=303)

    # Bank reports failure
    if status is not None and status != 0:
        error = urllib.parse.quote("پرداخت توسط کاربر لغو شد یا ناموفق بود.")
        return RedirectResponse(f"/orders/{order_id}?error={error}", status_code=303)

    result = payment_service.verify_gateway_callback(
        db, "parsian",
        {"Token": str(Token) if Token else "", "status": status, "RRN": str(RRN) if RRN else ""},
        order_id,
    )

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
