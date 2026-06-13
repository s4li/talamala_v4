"""
Pay Link — public routes (no login required — token is the access key)
  GET  /pay/{token}           — show payment page, auto-initiates if active
  POST /pay/{token}/initiate  — redirect to gateway
  POST /pay/callback/sepehr   — Sepehr callback
  GET  /pay/callback/zibal    — Zibal callback
  GET  /pay/callback/top      — Top callback
  POST /pay/callback/parsian  — Parsian callback
  GET  /pay/{token}/receipt   — receipt page
"""

import urllib.parse
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.security import csrf_check, new_csrf_token
from common.templating import templates
from modules.auth.deps import get_current_active_user
from modules.pay_link.service import pay_link_service

router = APIRouter(prefix="/pay", tags=["pay_link"])


# ── Payment page (no login needed) ──────────────────────────────────────────

@router.get("/{token}")
async def pay_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
    me=Depends(get_current_active_user),
):
    link = pay_link_service.get_by_token(db, token)
    if not link:
        return RedirectResponse("/", status_code=303)

    if link.is_paid:
        return RedirectResponse(f"/pay/{token}/receipt", status_code=303)

    csrf = new_csrf_token()
    resp = templates.TemplateResponse("pay_link/pay.html", {
        "request": request,
        "user": me,
        "cart_count": 0,
        "gold_price": None,
        "link": link,
        "csrf_token": csrf,
    })
    resp.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return resp


# ── Initiate payment (no login needed) ──────────────────────────────────────

@router.post("/{token}/initiate")
async def initiate_payment(
    request: Request,
    token: str,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    link = pay_link_service.get_by_token(db, token)
    if not link:
        return RedirectResponse("/", status_code=303)

    if not link.is_active:
        error = urllib.parse.quote(f"این لینک {link.status_label} است")
        return RedirectResponse(f"/pay/{token}?error={error}", status_code=303)

    result = pay_link_service.initiate(db, link)
    if result["success"]:
        db.commit()
        return RedirectResponse(result["redirect_url"], status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result["error"])
        return RedirectResponse(f"/pay/{token}?error={error}", status_code=303)


# ── Receipt page (no login needed) ──────────────────────────────────────────

@router.get("/{token}/receipt")
async def receipt_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
    me=Depends(get_current_active_user),
):
    link = pay_link_service.get_by_token(db, token)
    if not link:
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse("pay_link/receipt.html", {
        "request": request,
        "user": me,
        "cart_count": 0,
        "gold_price": None,
        "link": link,
    })


# ── Sepehr callback (POST) ───────────────────────────────────────────────────

@router.post("/callback/sepehr")
async def sepehr_callback(
    request: Request,
    link_token: str = Query(""),
    respcode: int = Form(...),
    respmsg: str = Form(None),
    invoiceid: str = Form(...),
    amount: int = Form(...),
    digitalreceipt: str = Form(None),
    db: Session = Depends(get_db),
):
    token = link_token or invoiceid

    if not token:
        return RedirectResponse("/", status_code=303)

    if respcode != 0:
        error = urllib.parse.quote(f"پرداخت ناموفق: {respmsg or 'خطای بانکی'}")
        return RedirectResponse(f"/pay/{token}?error={error}", status_code=303)

    if not digitalreceipt:
        error = urllib.parse.quote("کد پیگیری دریافت نشد")
        return RedirectResponse(f"/pay/{token}?error={error}", status_code=303)

    result = pay_link_service.verify(db, "sepehr", {
        "digitalreceipt": digitalreceipt,
        "expected_amount": amount,
    }, token)

    if result.get("success"):
        db.commit()
        return RedirectResponse(f"/pay/{token}/receipt", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("error", "پرداخت ناموفق"))
        return RedirectResponse(f"/pay/{token}?error={error}", status_code=303)


# ── Zibal callback (GET) ─────────────────────────────────────────────────────

@router.get("/callback/zibal")
async def zibal_callback(
    request: Request,
    link_token: str = Query(""),
    trackId: str = Query(""),
    success: str = Query(""),
    db: Session = Depends(get_db),
):
    if not link_token or not trackId:
        return RedirectResponse("/", status_code=303)

    if success == "0":
        error = urllib.parse.quote("پرداخت توسط کاربر لغو شد")
        return RedirectResponse(f"/pay/{link_token}?error={error}", status_code=303)

    result = pay_link_service.verify(db, "zibal", {"trackId": trackId}, link_token)

    if result.get("success"):
        db.commit()
        return RedirectResponse(f"/pay/{link_token}/receipt", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("error", "پرداخت ناموفق"))
        return RedirectResponse(f"/pay/{link_token}?error={error}", status_code=303)


# ── Top callback (GET) ───────────────────────────────────────────────────────

@router.get("/callback/top")
async def top_callback(
    request: Request,
    link_token: str = Query(""),
    token: str | list[str] = Query(None, alias="token"),
    status: int = Query(None),
    MerchantOrderId: str = Query(None),
    db: Session = Depends(get_db),
):
    if not link_token or not token:
        return RedirectResponse("/", status_code=303)

    if isinstance(token, list):
        token = token[0]

    result = pay_link_service.verify(db, "top", {
        "token": token,
        "MerchantOrderId": MerchantOrderId or link_token,
    }, link_token)

    if result.get("success"):
        db.commit()
        return RedirectResponse(f"/pay/{link_token}/receipt", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("error", "پرداخت ناموفق"))
        return RedirectResponse(f"/pay/{link_token}?error={error}", status_code=303)


# ── Parsian callback (POST) ──────────────────────────────────────────────────

@router.post("/callback/parsian")
async def parsian_callback(
    request: Request,
    link_token: str = Query(""),
    Token: str = Form(None),
    status: int = Form(None),
    RRN: int = Form(None),
    db: Session = Depends(get_db),
):
    if not link_token:
        return RedirectResponse("/", status_code=303)

    if status is not None and status != 0:
        error = urllib.parse.quote("پرداخت ناموفق یا لغو شد")
        return RedirectResponse(f"/pay/{link_token}?error={error}", status_code=303)

    result = pay_link_service.verify(db, "parsian", {
        "Token": str(Token) if Token else "",
        "status": status,
        "RRN": str(RRN) if RRN else "",
    }, link_token)

    if result.get("success"):
        db.commit()
        return RedirectResponse(f"/pay/{link_token}/receipt", status_code=303)
    else:
        db.rollback()
        error = urllib.parse.quote(result.get("error", "پرداخت ناموفق"))
        return RedirectResponse(f"/pay/{link_token}?error={error}", status_code=303)
