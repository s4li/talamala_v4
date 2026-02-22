"""
Ownership Module - Routes
============================
Customer-facing routes: my bars, claim bar, transfer ownership.
"""

from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from common.sms import sms_sender
from modules.auth.deps import require_login
from modules.cart.service import cart_service
from modules.ownership.service import ownership_service

router = APIRouter(tags=["ownership"])


# ==========================================
# My Bars
# ==========================================

@router.get("/my-bars", response_class=HTMLResponse)
async def my_bars(
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    bars = ownership_service.get_customer_bars(db, me.id)
    cart_map, cart_count = cart_service.get_cart_map(db, me.id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/my_bars.html", {
        "request": request,
        "user": me,
        "bars": bars,
        "cart_count": cart_count,
        "gold_price": cart_service._gold_price(db),
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Claim Bar
# ==========================================

@router.get("/claim-bar", response_class=HTMLResponse)
async def claim_bar_page(
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    cart_map, cart_count = cart_service.get_cart_map(db, me.id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/claim_bar.html", {
        "request": request,
        "user": me,
        "cart_count": cart_count,
        "gold_price": cart_service._gold_price(db),
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/claim-bar")
async def claim_bar_submit(
    request: Request,
    serial_code: str = Form(...),
    claim_code: str = Form(...),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)

    try:
        bar = ownership_service.claim_bar(db, me.id, serial_code, claim_code)
        db.commit()
        import urllib.parse
        msg = urllib.parse.quote(f"شمش {bar.serial_code} با موفقیت به نام شما ثبت شد!")
        return RedirectResponse(f"/my-bars?msg={msg}", status_code=303)
    except ValueError as e:
        db.rollback()
        import urllib.parse
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/claim-bar?error={error}", status_code=303)


# ==========================================
# Transfer Ownership - Step 1: Enter recipient mobile
# ==========================================

@router.get("/my-bars/{bar_id}/transfer", response_class=HTMLResponse)
async def transfer_page(
    request: Request,
    bar_id: int,
    error: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    from modules.inventory.models import Bar, BarStatus
    bar = db.query(Bar).filter(Bar.id == bar_id, Bar.customer_id == me.id, Bar.status == BarStatus.SOLD).first()
    if not bar:
        return RedirectResponse("/my-bars?error=شمش+یافت+نشد", status_code=303)

    cart_map, cart_count = cart_service.get_cart_map(db, me.id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/transfer_bar.html", {
        "request": request,
        "user": me,
        "bar": bar,
        "cart_count": cart_count,
        "gold_price": cart_service._gold_price(db),
        "csrf_token": csrf,
        "step": "mobile",
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Transfer Ownership - Step 2: Send OTP to owner
# ==========================================

@router.post("/my-bars/{bar_id}/transfer")
async def transfer_send_otp(
    request: Request,
    bar_id: int,
    to_mobile: str = Form(...),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)

    try:
        result = ownership_service.initiate_transfer(db, bar_id, me.id, to_mobile)
        db.commit()

        # Send OTP to owner's mobile
        sms_sender.send_otp_lookup(
            receptor=result["owner_mobile"],
            token=me.full_name.replace(" ", "_"),
            token2=result["otp_raw"],
            template_name="OTP",
        )

        # Re-render with OTP step
        from modules.inventory.models import Bar
        bar = db.query(Bar).filter(Bar.id == bar_id).first()
        cart_map, cart_count = cart_service.get_cart_map(db, me.id)

        csrf = new_csrf_token()
        response = templates.TemplateResponse("shop/transfer_bar.html", {
            "request": request,
            "user": me,
            "bar": bar,
            "cart_count": cart_count,
            "gold_price": cart_service._gold_price(db),
            "csrf_token": csrf,
            "step": "otp",
            "transfer_id": result["transfer_id"],
            "to_mobile": to_mobile,
            "error": None,
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response

    except ValueError as e:
        db.rollback()
        import urllib.parse
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/my-bars/{bar_id}/transfer?error={error}", status_code=303)


# ==========================================
# Transfer Ownership - Step 3: Confirm with OTP
# ==========================================

@router.post("/my-bars/{bar_id}/transfer/confirm")
async def transfer_confirm(
    request: Request,
    bar_id: int,
    transfer_id: int = Form(...),
    otp_code: str = Form(...),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)

    try:
        bar = ownership_service.confirm_transfer(db, transfer_id, me.id, otp_code)
        db.commit()

        import urllib.parse
        if bar.claim_code:
            # Recipient has no account
            msg = urllib.parse.quote(
                f"شمش {bar.serial_code} منتقل شد. گیرنده هنوز حساب کاربری ندارد — کد ثبت: {bar.claim_code}"
            )
        else:
            msg = urllib.parse.quote(f"شمش {bar.serial_code} با موفقیت منتقل شد!")
        return RedirectResponse(f"/my-bars?msg={msg}", status_code=303)

    except ValueError as e:
        db.rollback()
        # Re-render OTP step with error
        from modules.inventory.models import Bar
        bar = db.query(Bar).filter(Bar.id == bar_id).first()
        transfer = ownership_service.get_pending_transfer(db, transfer_id, me.id)
        cart_map, cart_count = cart_service.get_cart_map(db, me.id)

        csrf = new_csrf_token()
        response = templates.TemplateResponse("shop/transfer_bar.html", {
            "request": request,
            "user": me,
            "bar": bar,
            "cart_count": cart_count,
            "gold_price": cart_service._gold_price(db),
            "csrf_token": csrf,
            "step": "otp",
            "transfer_id": transfer_id,
            "to_mobile": transfer.to_mobile if transfer else "",
            "error": str(e),
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response


# ==========================================
# Custodial Delivery (درخواست تحویل امانی)
# ==========================================

@router.get("/my-bars/{bar_id}/delivery", response_class=HTMLResponse)
async def delivery_request_page(
    request: Request,
    bar_id: int,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    from modules.inventory.models import Bar, BarStatus, CustodialDeliveryRequest, CustodialDeliveryStatus
    from modules.customer.address_models import GeoProvince

    bar = db.query(Bar).filter(
        Bar.id == bar_id, Bar.customer_id == me.id,
        Bar.status == BarStatus.SOLD, Bar.delivered_at.is_(None),
    ).first()
    if not bar:
        return RedirectResponse("/my-bars?error=شمش+یافت+نشد", status_code=303)

    # Check for existing pending request
    existing_req = db.query(CustodialDeliveryRequest).filter(
        CustodialDeliveryRequest.bar_id == bar_id,
        CustodialDeliveryRequest.status == CustodialDeliveryStatus.PENDING,
    ).first()

    provinces = db.query(GeoProvince).order_by(GeoProvince.sort_order, GeoProvince.name).all()
    cart_map, cart_count = cart_service.get_cart_map(db, me.id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/custodial_delivery.html", {
        "request": request,
        "user": me,
        "bar": bar,
        "existing_req": existing_req,
        "provinces": provinces,
        "cart_count": cart_count,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/my-bars/{bar_id}/delivery")
async def delivery_request_submit(
    request: Request,
    bar_id: int,
    dealer_id: int = Form(...),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    try:
        req = ownership_service.create_delivery_request(db, me.id, bar_id, dealer_id)
        db.commit()
        import urllib.parse
        msg = urllib.parse.quote("درخواست تحویل ثبت شد")
        return RedirectResponse(f"/my-bars/{bar_id}/delivery?msg={msg}", status_code=303)
    except ValueError as e:
        db.rollback()
        import urllib.parse
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/my-bars/{bar_id}/delivery?error={error}", status_code=303)


@router.post("/my-bars/{bar_id}/delivery/{req_id}/send-otp")
async def delivery_send_otp(
    request: Request,
    bar_id: int,
    req_id: int,
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    try:
        result = ownership_service.send_delivery_otp(db, req_id, me.id)
        db.commit()

        # Send SMS
        sms_sender.send_otp_lookup(
            receptor=result["customer_mobile"],
            token=result["otp_raw"],
            token2="تحویل شمش",
            template_name="OTP",
        )

        import urllib.parse
        msg = urllib.parse.quote("کد تأیید ارسال شد")
        return RedirectResponse(f"/my-bars/{bar_id}/delivery?msg={msg}", status_code=303)
    except ValueError as e:
        db.rollback()
        import urllib.parse
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/my-bars/{bar_id}/delivery?error={error}", status_code=303)


@router.post("/my-bars/{bar_id}/delivery/{req_id}/cancel")
async def delivery_cancel(
    request: Request,
    bar_id: int,
    req_id: int,
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    try:
        ownership_service.cancel_delivery_request(db, req_id, me.id, reason="لغو توسط مشتری")
        db.commit()
        import urllib.parse
        msg = urllib.parse.quote("درخواست لغو شد")
        return RedirectResponse(f"/my-bars?msg={msg}", status_code=303)
    except ValueError as e:
        db.rollback()
        import urllib.parse
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/my-bars/{bar_id}/delivery?error={error}", status_code=303)
