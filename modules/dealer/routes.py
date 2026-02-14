"""
Dealer Module - Routes (Dealer Panel)
=========================================
Dashboard, POS sale, buyback, sales history for dealers.
"""

from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token, csrf_check
from modules.auth.deps import require_dealer
from modules.dealer.service import dealer_service
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode, OwnerType

router = APIRouter(prefix="/dealer", tags=["dealer"])


# ==========================================
# Dashboard
# ==========================================

@router.get("/dashboard", response_class=HTMLResponse)
async def dealer_dashboard(
    request: Request,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    stats = dealer_service.get_dealer_stats(db, dealer.id)
    available_bars = dealer_service.get_available_bars(db, dealer.location_id) if dealer.location_id else []

    # Wallet balances
    irr_balance = wallet_service.get_balance(db, dealer.id, asset_code=AssetCode.IRR, owner_type=OwnerType.DEALER)
    gold_balance = wallet_service.get_balance(db, dealer.id, asset_code=AssetCode.XAU_MG, owner_type=OwnerType.DEALER)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/dashboard.html", {
        "request": request,
        "dealer": dealer,
        "stats": stats,
        "available_bars_count": len(available_bars),
        "irr_balance": irr_balance,
        "gold_balance": gold_balance,
        "active_page": "dashboard",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# POS Sale
# ==========================================

@router.get("/pos", response_class=HTMLResponse)
async def pos_page(
    request: Request,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    bars = dealer_service.get_available_bars(db, dealer.location_id) if dealer.location_id else []

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/pos.html", {
        "request": request,
        "dealer": dealer,
        "bars": bars,
        "csrf_token": csrf,
        "active_page": "pos",
        "error": None,
        "success": None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/pos")
async def pos_submit(
    request: Request,
    bar_id: int = Form(...),
    sale_price: int = Form(...),
    customer_name: str = Form(""),
    customer_mobile: str = Form(""),
    customer_national_id: str = Form(""),
    description: str = Form(""),
    csrf_token: str = Form(""),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    # sale_price from form is in toman, convert to rial
    sale_price_rial = sale_price * 10

    result = dealer_service.create_pos_sale(
        db, dealer.id, bar_id, sale_price_rial,
        customer_name=customer_name,
        customer_mobile=customer_mobile,
        customer_national_id=customer_national_id,
        description=description,
    )

    if result["success"]:
        db.commit()
    else:
        db.rollback()

    bars = dealer_service.get_available_bars(db, dealer.location_id) if dealer.location_id else []

    # Build success message with claim code for POS receipt
    success_msg = None
    if result["success"]:
        claim_code = result.get("claim_code", "")
        success_msg = result["message"]
        if claim_code:
            success_msg += f" | کد ثبت مالکیت: {claim_code}"

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/pos.html", {
        "request": request,
        "dealer": dealer,
        "bars": bars,
        "csrf_token": csrf,
        "active_page": "pos",
        "error": None if result["success"] else result["message"],
        "success": success_msg,
        "claim_code": result.get("claim_code") if result["success"] else None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Buyback
# ==========================================

@router.get("/buyback", response_class=HTMLResponse)
async def buyback_page(
    request: Request,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/buyback.html", {
        "request": request,
        "dealer": dealer,
        "csrf_token": csrf,
        "active_page": "buyback",
        "error": None,
        "success": None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/buyback")
async def buyback_submit(
    request: Request,
    serial_code: str = Form(...),
    buyback_price: int = Form(...),
    customer_name: str = Form(""),
    customer_mobile: str = Form(""),
    description: str = Form(""),
    csrf_token: str = Form(""),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    # buyback_price from form is in toman, convert to rial
    buyback_price_rial = buyback_price * 10

    result = dealer_service.create_buyback(
        db, dealer.id, serial_code, buyback_price_rial,
        customer_name=customer_name,
        customer_mobile=customer_mobile,
        description=description,
    )

    if result["success"]:
        db.commit()
    else:
        db.rollback()

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/buyback.html", {
        "request": request,
        "dealer": dealer,
        "csrf_token": csrf,
        "active_page": "buyback",
        "error": None if result["success"] else result["message"],
        "success": result["message"] if result["success"] else None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Sales History
# ==========================================

@router.get("/sales", response_class=HTMLResponse)
async def sales_list(
    request: Request,
    page: int = 1,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    sales, total = dealer_service.get_dealer_sales(db, dealer.id, page=page)
    total_pages = (total + 19) // 20

    response = templates.TemplateResponse("dealer/sales.html", {
        "request": request,
        "dealer": dealer,
        "sales": sales,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "active_page": "sales",
    })
    return response


# ==========================================
# Buyback History
# ==========================================

@router.get("/buybacks", response_class=HTMLResponse)
async def buyback_list(
    request: Request,
    page: int = 1,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    buybacks, total = dealer_service.get_dealer_buybacks(db, dealer.id, page=page)
    total_pages = (total + 19) // 20

    response = templates.TemplateResponse("dealer/buybacks.html", {
        "request": request,
        "dealer": dealer,
        "buybacks": buybacks,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "active_page": "buybacks",
    })
    return response
