"""
Wallet Routes - Customer Facing
=================================
Balance view, topup (via Zibal gateway), withdrawal, transaction history.
"""

import logging
import urllib.parse
import httpx

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.settings import ZIBAL_MERCHANT, BASE_URL
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_customer
from modules.wallet.service import wallet_service
from modules.wallet.models import WithdrawalStatus, WithdrawalRequest, WalletTopup

logger = logging.getLogger("talamala.wallet")

ZIBAL_REQUEST_URL = "https://gateway.zibal.ir/v1/request"
ZIBAL_VERIFY_URL = "https://gateway.zibal.ir/v1/verify"
ZIBAL_START_URL = "https://gateway.zibal.ir/start/{trackId}"

router = APIRouter(prefix="/wallet", tags=["wallet"])


# ==========================================
# 💰 Wallet Dashboard
# ==========================================

@router.get("", response_class=HTMLResponse)
async def wallet_dashboard(
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    balance = wallet_service.get_balance(db, me.id)
    entries, total = wallet_service.get_transactions(db, me.id, per_page=10)

    # Pending withdrawals
    pending_wr = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.customer_id == me.id, WithdrawalRequest.status == WithdrawalStatus.PENDING)
        .all()
    )

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/wallet.html", {
        "request": request,
        "user": me,
        "balance": balance,
        "entries": entries,
        "pending_withdrawals": pending_wr,
        "cart_count": 0,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# 📜 Transaction History
# ==========================================

@router.get("/transactions", response_class=HTMLResponse)
async def wallet_transactions(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    per_page = 25
    entries, total = wallet_service.get_transactions(db, me.id, page=page, per_page=per_page)
    balance = wallet_service.get_balance(db, me.id)
    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse("shop/wallet_transactions.html", {
        "request": request,
        "user": me,
        "balance": balance,
        "entries": entries,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "cart_count": 0,
    })


# ==========================================
# 💳 Topup (charge wallet)
# ==========================================

@router.post("/topup")
async def wallet_topup(
    request: Request,
    amount_toman: int = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    csrf_check(request, csrf_token)
    amount_irr = amount_toman * 10

    try:
        topup = wallet_service.create_topup(db, me.id, amount_irr)
        db.flush()

        # Create Zibal payment request
        callback_url = f"{BASE_URL}/wallet/topup/callback?topup_id={topup.id}"
        resp = httpx.post(ZIBAL_REQUEST_URL, json={
            "merchant": ZIBAL_MERCHANT,
            "amount": amount_irr,
            "callbackUrl": callback_url,
            "description": f"شارژ کیف پول - {amount_toman:,} تومان",
        }, timeout=15)
        data = resp.json()
        logger.info(f"Zibal topup request #{topup.id}: {data}")

        if data.get("result") == 100:
            track_id = data["trackId"]
            topup.track_id = str(track_id)
            db.commit()
            return RedirectResponse(
                ZIBAL_START_URL.format(trackId=track_id), status_code=303
            )
        else:
            msg = data.get("message", f"کد خطا: {data.get('result')}")
            wallet_service.fail_topup(db, topup.id)
            db.commit()
            error = urllib.parse.quote(f"خطا در درگاه: {msg}")
            return RedirectResponse(f"/wallet?error={error}", status_code=302)

    except httpx.TimeoutException:
        db.rollback()
        error = urllib.parse.quote("درگاه پاسخ نداد. دوباره تلاش کنید.")
        return RedirectResponse(f"/wallet?error={error}", status_code=302)
    except ValueError as e:
        db.rollback()
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/wallet?error={error}", status_code=302)
    except Exception as e:
        db.rollback()
        logger.error(f"Wallet topup failed: {e}")
        error = urllib.parse.quote("خطا در اتصال به درگاه پرداخت")
        return RedirectResponse(f"/wallet?error={error}", status_code=302)


@router.get("/topup/callback")
async def wallet_topup_callback(
    request: Request,
    trackId: str = "",
    success: str = "",
    status: str = "",
    topup_id: int = 0,
    db: Session = Depends(get_db),
):
    """Zibal redirects user here after topup payment attempt."""
    if not trackId or not topup_id:
        return RedirectResponse("/wallet?error=پارامترهای+نامعتبر", status_code=302)

    # Validate trackId is numeric
    try:
        track_id_int = int(trackId)
    except (ValueError, TypeError):
        return RedirectResponse("/wallet?error=پارامترهای+نامعتبر", status_code=302)

    topup = db.query(WalletTopup).filter(WalletTopup.id == topup_id).first()
    if not topup:
        return RedirectResponse("/wallet?error=تراکنش+یافت+نشد", status_code=302)

    # Verify trackId matches stored value (defense-in-depth)
    if topup.track_id and topup.track_id != str(track_id_int):
        return RedirectResponse("/wallet?error=پارامترهای+نامعتبر", status_code=302)

    # Already processed (double callback protection)
    if topup.status == "PAID":
        msg = urllib.parse.quote("کیف پول قبلاً شارژ شده است")
        return RedirectResponse(f"/wallet?msg={msg}", status_code=302)

    # User cancelled on gateway
    if success == "0":
        wallet_service.fail_topup(db, topup.id)
        db.commit()
        error = urllib.parse.quote("پرداخت توسط کاربر لغو شد.")
        return RedirectResponse(f"/wallet?error={error}", status_code=302)

    # Verify with Zibal
    try:
        resp = httpx.post(ZIBAL_VERIFY_URL, json={
            "merchant": ZIBAL_MERCHANT,
            "trackId": track_id_int,
        }, timeout=15)
        data = resp.json()
        logger.info(f"Zibal topup verify #{topup.id}: {data}")

        if data.get("result") == 100:
            ref_number = str(data.get("refNumber", trackId))
            wallet_service.confirm_topup(db, topup.id, ref_number=ref_number)
            db.commit()
            amount_toman = topup.amount_irr // 10
            msg = urllib.parse.quote(f"کیف پول با موفقیت شارژ شد ({amount_toman:,} تومان)")
            return RedirectResponse(f"/wallet?msg={msg}", status_code=302)
        else:
            wallet_service.fail_topup(db, topup.id)
            db.commit()
            msg = data.get("message", f"کد: {data.get('result')}")
            error = urllib.parse.quote(f"تراکنش ناموفق — {msg}")
            return RedirectResponse(f"/wallet?error={error}", status_code=302)

    except Exception as e:
        db.rollback()
        logger.error(f"Zibal topup verify failed: {e}")
        error = urllib.parse.quote("خطا در تأیید تراکنش")
        return RedirectResponse(f"/wallet?error={error}", status_code=302)


# ==========================================
# 🏦 Withdrawal
# ==========================================

@router.get("/withdraw", response_class=HTMLResponse)
async def wallet_withdraw_form(
    request: Request,
    error: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    balance = wallet_service.get_balance(db, me.id)
    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/wallet_withdraw.html", {
        "request": request,
        "user": me,
        "balance": balance,
        "csrf_token": csrf,
        "error": error,
        "cart_count": 0,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/withdraw")
async def wallet_withdraw_submit(
    request: Request,
    amount_toman: int = Form(...),
    shaba_number: str = Form(...),
    account_holder: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    csrf_check(request, csrf_token)
    amount_irr = amount_toman * 10

    try:
        wr = wallet_service.create_withdrawal(db, me.id, amount_irr, shaba_number, account_holder)
        db.commit()
        return RedirectResponse(
            f"/wallet?msg=درخواست+برداشت+%23{wr.id}+ثبت+شد.+پس+از+تأیید+مدیر+به+حساب+شما+واریز+خواهد+شد.",
            status_code=302,
        )
    except ValueError as e:
        db.rollback()
        return RedirectResponse(f"/wallet/withdraw?error={str(e)}", status_code=302)


