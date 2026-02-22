"""
Wallet Routes — Unified for All User Types
=============================================
Balance view, topup (via active gateway), withdrawal, transaction history,
generic precious metal buy/sell with dynamic role-based commission.
"""

import logging

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from config.settings import BASE_URL
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from common.flash import flash
from modules.auth.deps import require_login
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode, WithdrawalStatus, WithdrawalRequest, WalletTopup, PRECIOUS_METALS
from modules.payment.gateways import get_gateway, GatewayPaymentRequest

logger = logging.getLogger("talamala.wallet")

router = APIRouter(prefix="/wallet", tags=["wallet"])


def _get_enabled_gateways(db: Session) -> list:
    """Read enabled gateways from SystemSetting."""
    from modules.admin.models import SystemSetting
    setting = db.query(SystemSetting).filter(SystemSetting.key == "enabled_gateways").first()
    raw = setting.value if setting else "sepehr,top,parsian"
    return [g.strip() for g in raw.split(",") if g.strip()]


# ==========================================
# 💰 Wallet Dashboard
# ==========================================

@router.get("", response_class=HTMLResponse)
async def wallet_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    balance = wallet_service.get_balance(db, me.id)
    entries, total = wallet_service.get_transactions(db, me.id, per_page=10)

    # Pending withdrawals
    pending_wr = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.user_id == me.id, WithdrawalRequest.status == WithdrawalStatus.PENDING)
        .all()
    )

    # Enabled gateways for topup selector
    enabled_gateways = _get_enabled_gateways(db)

    # Build metals list with balances, rates, fees
    metals = []
    for key, meta in PRECIOUS_METALS.items():
        fee = wallet_service.get_fee_for_user(db, me, asset_type=key)
        rates = wallet_service.get_metal_rates(db, asset_type=key, fee_percent=fee)
        metal_balance = wallet_service.get_balance(db, me.id, asset_code=meta["asset_code"])
        metals.append({
            "key": key,
            **meta,
            "balance": metal_balance,
            "rates": rates,
            "fee_percent": fee,
        })

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/wallet.html", {
        "request": request,
        "user": me,
        "balance": balance,
        "metals": metals,
        "entries": entries,
        "pending_withdrawals": pending_wr,
        "cart_count": 0,
        "csrf_token": csrf,
        "enabled_gateways": enabled_gateways,
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
    asset: str = "",
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    per_page = 25
    asset_code = None
    if asset == "gold":
        asset_code = AssetCode.XAU_MG
    elif asset == "silver":
        asset_code = AssetCode.XAG_MG
    elif asset == "irr":
        asset_code = AssetCode.IRR

    entries, total = wallet_service.get_transactions(
        db, me.id, page=page, per_page=per_page, asset_code=asset_code,
    )
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
        "asset_filter": asset,
        "cart_count": 0,
    })


# ==========================================
# 💳 Topup (charge wallet via active gateway)
# ==========================================

@router.post("/topup")
async def wallet_topup(
    request: Request,
    amount_toman: int = Form(...),
    gateway: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    amount_irr = amount_toman * 10

    # Validate customer-selected gateway
    enabled = _get_enabled_gateways(db)
    if not gateway or gateway not in enabled:
        flash(request, "لطفاً یک درگاه پرداخت انتخاب کنید", "danger")
        return RedirectResponse("/wallet", status_code=302)

    try:
        topup = wallet_service.create_topup(db, me.id, amount_irr)
        db.flush()

        gateway_name = gateway
        gw = get_gateway(gateway_name)
        if not gw:
            wallet_service.fail_topup(db, topup.id)
            db.commit()
            flash(request, f"درگاه {gateway_name} در دسترس نیست", "danger")
            return RedirectResponse("/wallet", status_code=302)

        callback_url = f"{BASE_URL}/wallet/topup/{gateway_name}/callback?topup_id={topup.id}"
        result = gw.create_payment(GatewayPaymentRequest(
            amount_irr=amount_irr,
            callback_url=callback_url,
            description=f"شارژ کیف پول - {amount_toman:,} تومان",
            order_ref=str(topup.id),
        ))

        if result.success:
            topup.track_id = result.track_id
            topup.gateway = gateway_name
            db.commit()
            return RedirectResponse(result.redirect_url, status_code=303)
        else:
            wallet_service.fail_topup(db, topup.id)
            db.commit()
            flash(request, f"خطا در درگاه: {result.error_message}", "danger")
            return RedirectResponse("/wallet", status_code=302)

    except ValueError as e:
        db.rollback()
        flash(request, str(e), "danger")
        return RedirectResponse("/wallet", status_code=302)
    except Exception as e:
        db.rollback()
        logger.error(f"Wallet topup failed: {e}")
        flash(request, "خطا در اتصال به درگاه پرداخت", "danger")
        return RedirectResponse("/wallet", status_code=302)


# ==========================================
# 💳 Topup Callbacks (per gateway)
# ==========================================

def _verify_topup(request: Request, db: Session, topup: WalletTopup, params: dict, gateway_name: str):
    """Common topup verification logic for all gateways."""
    # Already processed (double callback protection)
    if topup.status == "PAID":
        flash(request, "کیف پول قبلاً شارژ شده است", "info")
        return RedirectResponse("/wallet", status_code=302)

    gw = get_gateway(gateway_name)
    if not gw:
        flash(request, f"درگاه {gateway_name} شناسایی نشد", "danger")
        return RedirectResponse("/wallet", status_code=302)

    # For Sepehr, inject expected_amount
    if gateway_name == "sepehr":
        params["expected_amount"] = topup.amount_irr

    result = gw.verify_payment(params)

    if result.success:
        wallet_service.confirm_topup(db, topup.id, ref_number=result.ref_number)
        db.commit()
        amount_toman = topup.amount_irr // 10
        flash(request, f"کیف پول با موفقیت شارژ شد ({amount_toman:,} تومان)", "success")
    else:
        wallet_service.fail_topup(db, topup.id)
        db.commit()
        flash(request, f"تراکنش ناموفق — {result.error_message}", "danger")

    return RedirectResponse("/wallet", status_code=302)


def _get_topup_or_redirect(request: Request, db: Session, topup_id: int):
    """Lookup topup by ID, return it or redirect on error."""
    if not topup_id:
        flash(request, "پارامترهای نامعتبر", "danger")
        return None
    topup = db.query(WalletTopup).filter(WalletTopup.id == topup_id).first()
    if not topup:
        flash(request, "تراکنش یافت نشد", "danger")
        return None
    return topup


# Backward-compatible Zibal callback (old URL without gateway prefix)
@router.get("/topup/callback")
async def wallet_topup_callback_legacy(
    request: Request,
    trackId: str = "",
    success: str = "",
    topup_id: int = 0,
    db: Session = Depends(get_db),
):
    """Legacy Zibal topup callback (backward compatibility)."""
    topup = _get_topup_or_redirect(request, db, topup_id)
    if not topup:
        return RedirectResponse("/wallet", status_code=302)

    if success == "0":
        wallet_service.fail_topup(db, topup.id)
        db.commit()
        flash(request, "پرداخت توسط کاربر لغو شد.", "danger")
        return RedirectResponse("/wallet", status_code=302)

    return _verify_topup(request, db, topup, {"trackId": trackId}, "zibal")


@router.get("/topup/zibal/callback")
async def wallet_topup_zibal_callback(
    request: Request,
    trackId: str = "",
    success: str = "",
    topup_id: int = 0,
    db: Session = Depends(get_db),
):
    """Zibal topup callback."""
    topup = _get_topup_or_redirect(request, db, topup_id)
    if not topup:
        return RedirectResponse("/wallet", status_code=302)

    if success == "0":
        wallet_service.fail_topup(db, topup.id)
        db.commit()
        flash(request, "پرداخت توسط کاربر لغو شد.", "danger")
        return RedirectResponse("/wallet", status_code=302)

    return _verify_topup(request, db, topup, {"trackId": trackId}, "zibal")


@router.post("/topup/sepehr/callback")
async def wallet_topup_sepehr_callback(
    request: Request,
    respcode: int = Form(...),
    respmsg: str = Form(None),
    invoiceid: str = Form(...),
    amount: int = Form(...),
    digitalreceipt: str = Form(None),
    topup_id: int = Query(0),
    db: Session = Depends(get_db),
):
    """Sepehr topup callback (POST with form data, topup_id in URL query)."""
    topup = _get_topup_or_redirect(request, db, topup_id)
    if not topup:
        return RedirectResponse("/wallet", status_code=302)

    if respcode != 0:
        wallet_service.fail_topup(db, topup.id)
        db.commit()
        flash(request, f"پرداخت ناموفق: {respmsg or 'خطای بانکی'}", "danger")
        return RedirectResponse("/wallet", status_code=302)

    if not digitalreceipt:
        wallet_service.fail_topup(db, topup.id)
        db.commit()
        flash(request, "کد پیگیری دریافت نشد.", "danger")
        return RedirectResponse("/wallet", status_code=302)

    return _verify_topup(request, db, topup, {"digitalreceipt": digitalreceipt, "expected_amount": amount}, "sepehr")


@router.get("/topup/top/callback")
async def wallet_topup_top_callback(
    request: Request,
    token: str | list[str] = Query(None, alias="token"),
    status: int = Query(None, alias="status"),
    MerchantOrderId: int = Query(None, alias="MerchantOrderId"),
    topup_id: int = Query(0),
    db: Session = Depends(get_db),
):
    """Top topup callback."""
    topup = _get_topup_or_redirect(request, db, topup_id)
    if not topup:
        return RedirectResponse("/wallet", status_code=302)

    if not token:
        wallet_service.fail_topup(db, topup.id)
        db.commit()
        flash(request, "پارامترهای نامعتبر", "danger")
        return RedirectResponse("/wallet", status_code=302)

    if isinstance(token, list):
        token = token[0]
    return _verify_topup(request, db, topup, {"token": token, "MerchantOrderId": str(topup_id)}, "top")


@router.post("/topup/parsian/callback")
async def wallet_topup_parsian_callback(
    request: Request,
    Token: str = Form(None),
    status: int = Form(None),
    RRN: int = Form(None),
    topup_id: int = Query(0),
    db: Session = Depends(get_db),
):
    """Parsian topup callback (POST with form data, topup_id in URL query)."""
    topup = _get_topup_or_redirect(request, db, topup_id)
    if not topup:
        return RedirectResponse("/wallet", status_code=302)

    # Bank reports failure
    if status is not None and status != 0:
        wallet_service.fail_topup(db, topup.id)
        db.commit()
        flash(request, "پرداخت توسط کاربر لغو شد یا ناموفق بود.", "danger")
        return RedirectResponse("/wallet", status_code=302)

    return _verify_topup(
        request, db, topup,
        {"Token": str(Token) if Token else "", "status": status, "RRN": str(RRN) if RRN else ""},
        "parsian",
    )


# ==========================================
# 🏦 Withdrawal
# ==========================================

@router.get("/withdraw", response_class=HTMLResponse)
async def wallet_withdraw_form(
    request: Request,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    balance = wallet_service.get_balance(db, me.id)
    withdrawals = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.user_id == me.id)
        .order_by(WithdrawalRequest.created_at.desc())
        .limit(20)
        .all()
    )
    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/wallet_withdraw.html", {
        "request": request,
        "user": me,
        "balance": balance,
        "withdrawals": withdrawals,
        "csrf_token": csrf,
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
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    amount_irr = amount_toman * 10

    try:
        wr = wallet_service.create_withdrawal(db, me.id, amount_irr, shaba_number, account_holder)
        db.commit()
        flash(request, f"درخواست برداشت #{wr.id} ثبت شد. پس از تأیید مدیر به حساب شما واریز خواهد شد.", "success")
        return RedirectResponse("/wallet", status_code=302)
    except ValueError as e:
        db.rollback()
        flash(request, str(e), "danger")
        return RedirectResponse("/wallet/withdraw", status_code=302)


# ==========================================
# 🪙 Precious Metal Buy / Sell (generic, all users, dynamic fee)
# ==========================================

@router.get("/{asset_type}", response_class=HTMLResponse)
async def wallet_metal_page(
    request: Request,
    asset_type: str,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    """Precious metal buy/sell page — all users with role-based commission."""
    metal = PRECIOUS_METALS.get(asset_type)
    if not metal:
        flash(request, "نوع دارایی شناسایی نشد", "danger")
        return RedirectResponse("/wallet", status_code=302)

    from modules.pricing.trade_guard import is_trade_enabled
    balance = wallet_service.get_balance(db, me.id)
    metal_balance = wallet_service.get_balance(db, me.id, asset_code=metal["asset_code"])
    fee_percent = wallet_service.get_fee_for_user(db, me, asset_type=asset_type)
    rates = wallet_service.get_metal_rates(db, asset_type=asset_type, fee_percent=fee_percent)
    buy_enabled = is_trade_enabled(db, asset_type, "wallet_buy")
    sell_enabled = is_trade_enabled(db, asset_type, "wallet_sell")

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/wallet_trade.html", {
        "request": request,
        "user": me,
        "balance": balance,
        "metal_balance": metal_balance,
        "rates": rates,
        "fee_percent": fee_percent,
        "csrf_token": csrf,
        "cart_count": 0,
        "metal": metal,
        "asset_type": asset_type,
        "buy_enabled": buy_enabled,
        "sell_enabled": sell_enabled,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/{asset_type}/buy")
async def wallet_metal_buy(
    request: Request,
    asset_type: str,
    amount_toman: int = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    """Buy precious metal with rials — dynamic fee based on user role."""
    csrf_check(request, csrf_token)
    metal = PRECIOUS_METALS.get(asset_type)
    if not metal:
        flash(request, "نوع دارایی شناسایی نشد", "danger")
        return RedirectResponse("/wallet", status_code=302)

    amount_irr = amount_toman * 10
    fee_percent = wallet_service.get_fee_for_user(db, me, asset_type=asset_type)

    try:
        result = wallet_service.buy_metal(db, me.id, amount_irr, asset_type=asset_type, fee_percent=fee_percent)
        db.commit()
        mg = result["metal_mg"]
        flash(request, f"خرید {mg / 1000:.3f} گرم {metal['label']} با موفقیت انجام شد", "success")
        return RedirectResponse(f"/wallet/{asset_type}", status_code=302)
    except ValueError as e:
        db.rollback()
        flash(request, str(e), "danger")
        return RedirectResponse(f"/wallet/{asset_type}", status_code=302)


@router.post("/{asset_type}/sell")
async def wallet_metal_sell(
    request: Request,
    asset_type: str,
    metal_grams: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    """Sell precious metal for rials — dynamic fee based on user role."""
    csrf_check(request, csrf_token)
    metal = PRECIOUS_METALS.get(asset_type)
    if not metal:
        flash(request, "نوع دارایی شناسایی نشد", "danger")
        return RedirectResponse("/wallet", status_code=302)

    fee_percent = wallet_service.get_fee_for_user(db, me, asset_type=asset_type)

    try:
        mg = int(float(metal_grams) * 1000)
        if mg <= 0:
            raise ValueError(f"مقدار {metal['label']} باید بیشتر از صفر باشد")
        result = wallet_service.sell_metal(db, me.id, mg, asset_type=asset_type, fee_percent=fee_percent)
        db.commit()
        rial = result["amount_irr"]
        flash(request, f"فروش {mg / 1000:.3f} گرم {metal['label']} — {rial // 10:,} تومان واریز شد", "success")
        return RedirectResponse(f"/wallet/{asset_type}", status_code=302)
    except ValueError as e:
        db.rollback()
        flash(request, str(e), "danger")
        return RedirectResponse(f"/wallet/{asset_type}", status_code=302)
