"""
Dealer Module - Routes (Dealer Panel)
=========================================
Dashboard, POS sale, buyback, sales history for dealers.
"""

import json

from fastapi import APIRouter, Request, Depends, Form, Response, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token, csrf_check
from modules.auth.deps import require_dealer
from modules.dealer.service import dealer_service
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode, OwnerType
from modules.admin.models import SystemSetting
from modules.pricing.calculator import calculate_bar_price
from modules.pricing.service import get_end_customer_wage
from modules.inventory.models import Bar, BarStatus

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
    available_bars = dealer_service.get_available_bars(db, dealer.id)

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

def _calc_bar_prices(db: Session, bars, dealer):
    """Calculate system price + dealer margin for each bar."""
    if not bars:
        return {}
    gold_setting = db.query(SystemSetting).filter(SystemSetting.key == "gold_price").first()
    tax_setting = db.query(SystemSetting).filter(SystemSetting.key == "tax_percent").first()
    gold_price = int(gold_setting.value) if gold_setting else 0
    tax_percent = float(tax_setting.value) if tax_setting else 10.0

    from modules.catalog.models import ProductTierWage
    dealer_tier_id = dealer.tier_id

    prices = {}
    for bar in bars:
        p = bar.product
        if not p:
            continue
        ec_wage = get_end_customer_wage(db, p)

        # Dealer's own wage for this product
        dealer_wage_pct = 0.0
        if dealer_tier_id:
            dw_row = db.query(ProductTierWage).filter(
                ProductTierWage.product_id == p.id,
                ProductTierWage.tier_id == dealer_tier_id,
            ).first()
            dealer_wage_pct = float(dw_row.wage_percent) if dw_row else 0
        margin_pct = round(ec_wage - dealer_wage_pct, 2)

        info = calculate_bar_price(
            weight=p.weight, purity=p.purity,
            wage_percent=ec_wage,
            base_gold_price_18k=gold_price,
            tax_percent=tax_percent,
        )
        prices[bar.id] = {
            "total_toman": info.get("total", 0) // 10,
            "raw_gold_toman": info.get("raw_gold", 0) // 10,
            "wage_toman": info.get("wage", 0) // 10,
            "tax_toman": info.get("tax", 0) // 10,
            # Margin data for discount UI
            "ec_wage_pct": ec_wage,
            "dealer_wage_pct": dealer_wage_pct,
            "margin_pct": margin_pct,
            "weight": str(p.weight),
            "purity": int(p.purity),
            "gold_price": gold_price,
            "tax_percent": tax_percent,
        }
    return prices


@router.get("/pos", response_class=HTMLResponse)
async def pos_page(
    request: Request,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    bars = dealer_service.get_available_bars(db, dealer.id)
    bar_prices = _calc_bar_prices(db, bars, dealer)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/pos.html", {
        "request": request,
        "dealer": dealer,
        "bars": bars,
        "bar_prices_json": json.dumps(bar_prices),
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
    discount_wage_percent: str = Form("0"),
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

    # Parse discount
    try:
        disc_pct = float(discount_wage_percent)
    except (ValueError, TypeError):
        disc_pct = 0.0

    result = dealer_service.create_pos_sale(
        db, dealer.id, bar_id, sale_price_rial,
        customer_name=customer_name,
        customer_mobile=customer_mobile,
        customer_national_id=customer_national_id,
        description=description,
        discount_wage_percent=disc_pct,
    )

    if result["success"]:
        db.commit()
    else:
        db.rollback()

    bars = dealer_service.get_available_bars(db, dealer.id)
    bar_prices = _calc_bar_prices(db, bars, dealer)

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
        "bar_prices_json": json.dumps(bar_prices),
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


# ==========================================
# Buyback Bar Lookup (AJAX)
# ==========================================

@router.get("/buyback/lookup")
async def buyback_lookup(
    serial: str = Query(""),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    """AJAX: look up bar by serial → return bar info + system buyback price."""
    if not serial or len(serial.strip()) < 3:
        return JSONResponse({"found": False})

    bar = db.query(Bar).filter(Bar.serial_code == serial.strip().upper()).first()
    if not bar:
        return JSONResponse({"found": False, "error": "شمش با این سریال یافت نشد"})
    if bar.status != BarStatus.SOLD:
        return JSONResponse({"found": False, "error": "فقط شمش‌های فروخته‌شده قابل بازخرید هستند"})

    product = bar.product
    if not product:
        return JSONResponse({"found": False, "error": "محصول مرتبط یافت نشد"})

    # Calculate raw gold value (buyback = gold value without wage/profit/tax)
    gold_setting = db.query(SystemSetting).filter(SystemSetting.key == "gold_price").first()
    gold_price = int(gold_setting.value) if gold_setting else 0

    info = calculate_bar_price(
        weight=product.weight, purity=product.purity,
        wage_percent=0,
        base_gold_price_18k=gold_price, tax_percent=0,
    )
    raw_gold_toman = info.get("total", 0) // 10

    # Also calc full retail price for reference
    tax_setting = db.query(SystemSetting).filter(SystemSetting.key == "tax_percent").first()
    tax_percent = float(tax_setting.value) if tax_setting else 10.0
    ec_wage = get_end_customer_wage(db, product)
    full_info = calculate_bar_price(
        weight=product.weight, purity=product.purity,
        wage_percent=ec_wage,
        base_gold_price_18k=gold_price, tax_percent=tax_percent,
    )
    retail_toman = full_info.get("total", 0) // 10

    return JSONResponse({
        "found": True,
        "serial_code": bar.serial_code,
        "product_name": product.name,
        "weight": str(product.weight),
        "purity": float(product.purity),
        "raw_gold_toman": raw_gold_toman,
        "retail_toman": retail_toman,
        "owner_name": bar.customer.full_name if bar.customer_id and bar.customer else "نامشخص",
    })
