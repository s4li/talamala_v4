"""
Dealer Wallet Routes
=======================
Wallet dashboard, transaction history, gold buy/sell for dealers.
"""

import urllib.parse

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_dealer
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode, OwnerType

router = APIRouter(prefix="/dealer/wallet", tags=["dealer-wallet"])


# ==========================================
# Dashboard
# ==========================================

@router.get("", response_class=HTMLResponse)
async def dealer_wallet_dashboard(
    request: Request,
    msg: str = None,
    error: str = None,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    irr_balance = wallet_service.get_balance(
        db, dealer.id, asset_code=AssetCode.IRR, owner_type=OwnerType.DEALER
    )
    gold_balance = wallet_service.get_balance(
        db, dealer.id, asset_code=AssetCode.XAU_MG, owner_type=OwnerType.DEALER
    )
    entries, total = wallet_service.get_transactions(
        db, dealer.id, owner_type=OwnerType.DEALER, per_page=10
    )

    csrf = new_csrf_token()
    resp = templates.TemplateResponse("dealer/wallet.html", {
        "request": request,
        "dealer": dealer,
        "irr_balance": irr_balance,
        "gold_balance": gold_balance,
        "entries": entries,
        "active_page": "wallet",
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
    })
    resp.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return resp


# ==========================================
# Transaction History
# ==========================================

@router.get("/transactions", response_class=HTMLResponse)
async def dealer_wallet_transactions(
    request: Request,
    page: int = 1,
    asset: str = "",
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    per_page = 25
    asset_code = AssetCode.XAU_MG if asset == "gold" else (AssetCode.IRR if asset == "irr" else None)
    entries, total = wallet_service.get_transactions(
        db, dealer.id, owner_type=OwnerType.DEALER,
        page=page, per_page=per_page, asset_code=asset_code,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse("dealer/wallet_transactions.html", {
        "request": request,
        "dealer": dealer,
        "entries": entries,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "asset_filter": asset,
        "active_page": "wallet",
    })


# ==========================================
# Gold Buy / Sell
# ==========================================

@router.post("/gold/buy")
async def dealer_gold_buy(
    request: Request,
    amount_toman: int = Form(...),
    csrf_token: str = Form(""),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    """Dealer buys gold with rials."""
    csrf_check(request, csrf_token)
    amount_irr = amount_toman * 10

    try:
        result = wallet_service.convert_rial_to_gold(
            db, dealer.id, amount_irr, owner_type=OwnerType.DEALER
        )
        db.commit()
        gold_mg = result["gold_mg"]
        msg = urllib.parse.quote(f"خرید {gold_mg / 1000:.3f} گرم طلا با موفقیت انجام شد")
        return RedirectResponse(f"/dealer/wallet?msg={msg}", status_code=302)
    except ValueError as e:
        db.rollback()
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/dealer/wallet?error={error}", status_code=302)


@router.post("/gold/sell")
async def dealer_gold_sell(
    request: Request,
    gold_grams: str = Form(...),
    csrf_token: str = Form(""),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    """Dealer sells gold for rials."""
    csrf_check(request, csrf_token)

    try:
        gold_mg = int(float(gold_grams) * 1000)
        if gold_mg <= 0:
            raise ValueError("مقدار طلا باید بیشتر از صفر باشد")
        result = wallet_service.convert_gold_to_rial(
            db, dealer.id, gold_mg, owner_type=OwnerType.DEALER
        )
        db.commit()
        rial = result["amount_irr"]
        msg = urllib.parse.quote(f"فروش {gold_mg / 1000:.3f} گرم طلا — {rial // 10:,} تومان واریز شد")
        return RedirectResponse(f"/dealer/wallet?msg={msg}", status_code=302)
    except ValueError as e:
        db.rollback()
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/dealer/wallet?error={error}", status_code=302)
