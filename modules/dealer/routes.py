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
from modules.wallet.models import AssetCode
from modules.pricing.calculator import calculate_bar_price
from modules.pricing.service import get_end_customer_wage, get_dealer_margin, get_price_value, get_product_pricing, is_price_fresh
from modules.pricing.models import GOLD_18K
from modules.inventory.models import Bar, BarStatus
from modules.dealer.models import DealerSale, BuybackRequest, BuybackStatus

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
    irr_balance = wallet_service.get_balance(db, dealer.id, asset_code=AssetCode.IRR)
    gold_balance = wallet_service.get_balance(db, dealer.id, asset_code=AssetCode.XAU_MG)

    # Analytics data
    daily_sales = dealer_service.get_daily_sales_data(db, dealer.id, days=30)
    metal_breakdown = dealer_service.get_metal_profit_breakdown(db, dealer.id)
    period_comparison = dealer_service.get_period_comparison(db, dealer.id)
    inventory_value = dealer_service.get_inventory_value(db, dealer.id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/dashboard.html", {
        "request": request,
        "dealer": dealer,
        "stats": stats,
        "available_bars_count": len(available_bars),
        "irr_balance": irr_balance,
        "gold_balance": gold_balance,
        "daily_sales": daily_sales,
        "metal_breakdown": metal_breakdown,
        "period_comparison": period_comparison,
        "inventory_value": inventory_value,
        "active_page": "dashboard",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# POS Sale
# ==========================================

def _calc_bar_prices(db: Session, bars, dealer):
    """Calculate system price + dealer margin for each bar (per-product metal pricing)."""
    if not bars:
        return {}
    from common.templating import get_setting_from_db
    tax_percent = float(get_setting_from_db(db, "tax_percent", "10"))

    prices = {}
    for bar in bars:
        p = bar.product
        if not p:
            continue
        p_price, p_bp, _ = get_product_pricing(db, p)
        ec_wage, dealer_wage_pct, margin_pct = get_dealer_margin(db, p, dealer)

        info = calculate_bar_price(
            weight=p.weight, purity=p.purity,
            wage_percent=ec_wage,
            base_metal_price=p_price,
            tax_percent=tax_percent,
            base_purity=p_bp,
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
            "gold_price": p_price,
            "base_purity": p_bp,
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
# Sub-dealers (Read-only view)
# ==========================================

@router.get("/sub-dealers", response_class=HTMLResponse)
async def dealer_sub_dealers(
    request: Request,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    parent_rel = dealer_service.get_parent_relation(db, dealer.id)
    sub_rels = dealer_service.get_sub_dealers(db, dealer.id)
    commission_stats = dealer_service.get_sub_dealer_commission_stats(db, dealer.id)

    response = templates.TemplateResponse("dealer/sub_dealers.html", {
        "request": request,
        "dealer": dealer,
        "parent_rel": parent_rel,
        "sub_rels": sub_rels,
        "commission_stats": commission_stats,
        "active_page": "sub_dealers",
    })
    return response


# ==========================================
# Physical Inventory
# ==========================================

@router.get("/inventory", response_class=HTMLResponse)
async def dealer_inventory(
    request: Request,
    metal_type: str = "",
    status: str = "",
    page: int = 1,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    bars, total, inv_stats = dealer_service.get_inventory_at_location(
        db, dealer.id, metal_type=metal_type, status_filter=status, page=page,
    )
    total_pages = (total + 29) // 30

    response = templates.TemplateResponse("dealer/inventory.html", {
        "request": request,
        "dealer": dealer,
        "bars": bars,
        "total": total,
        "inv_stats": inv_stats,
        "page": page,
        "total_pages": total_pages,
        "metal_type": metal_type,
        "status_filter": status,
        "active_page": "inventory",
    })
    return response


# ==========================================
# Scanner Lookup (Dealer)
# ==========================================

@router.get("/scan/lookup")
async def dealer_scan_lookup(
    serial: str = Query(...),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    """JSON lookup for dealer scanner — returns bar info + at_my_location flag."""
    bar = db.query(Bar).filter(Bar.serial_code == serial.strip().upper()).first()
    if not bar:
        return JSONResponse({"error": "شمش با این سریال یافت نشد"})

    return JSONResponse({
        "bar_id": bar.id,
        "serial": bar.serial_code,
        "status": bar.status,
        "status_label": bar.status_label,
        "status_color": bar.status_color,
        "product_name": bar.product.name if bar.product else None,
        "at_my_location": bar.dealer_id == dealer.id,
    })


# ==========================================
# Reconciliation (Dealer)
# ==========================================

@router.get("/reconciliation", response_class=HTMLResponse)
async def dealer_reconciliation_list(
    request: Request,
    page: int = 1,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    from modules.inventory.service import inventory_service
    sessions, total = inventory_service.list_reconciliation_sessions(db, dealer_id=dealer.id, page=page)
    total_pages = (total + 19) // 20

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/reconciliation.html", {
        "request": request,
        "dealer": dealer,
        "sessions": sessions,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "csrf_token": csrf,
        "active_page": "reconciliation",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/reconciliation/start")
async def dealer_reconciliation_start(
    request: Request,
    csrf_token: str = Form(None),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    from modules.inventory.service import inventory_service
    try:
        session = inventory_service.start_reconciliation(db, dealer.id, dealer.full_name)
        db.commit()
        return RedirectResponse(f"/dealer/reconciliation/{session.id}", status_code=303)
    except ValueError as e:
        import urllib.parse as _up
        return RedirectResponse(f"/dealer/reconciliation?error={_up.quote(str(e))}", status_code=303)


@router.get("/reconciliation/{session_id}", response_class=HTMLResponse)
async def dealer_reconciliation_detail(
    request: Request,
    session_id: int,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    from modules.inventory.service import inventory_service
    recon = inventory_service.get_reconciliation_session(db, session_id, dealer_id=dealer.id)
    if not recon:
        return RedirectResponse("/dealer/reconciliation", status_code=303)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/reconciliation_detail.html", {
        "request": request,
        "dealer": dealer,
        "recon": recon,
        "csrf_token": csrf,
        "active_page": "reconciliation",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/reconciliation/{session_id}/scan")
async def dealer_reconciliation_scan(
    request: Request,
    session_id: int,
    serial: str = Form(...),
    csrf_token: str = Form(None),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    from modules.inventory.service import inventory_service
    result = inventory_service.scan_for_reconciliation(db, session_id, serial, dealer.id)
    db.commit()
    return JSONResponse(result)


@router.post("/reconciliation/{session_id}/finalize")
async def dealer_reconciliation_finalize(
    request: Request,
    session_id: int,
    notes: str = Form(None),
    csrf_token: str = Form(None),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    from modules.inventory.service import inventory_service
    try:
        inventory_service.finalize_reconciliation(db, session_id, dealer.id, notes=notes)
        db.commit()
        return RedirectResponse(f"/dealer/reconciliation/{session_id}", status_code=303)
    except ValueError:
        return RedirectResponse("/dealer/reconciliation", status_code=303)


@router.post("/reconciliation/{session_id}/cancel")
async def dealer_reconciliation_cancel(
    request: Request,
    session_id: int,
    csrf_token: str = Form(None),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    from modules.inventory.service import inventory_service
    try:
        inventory_service.cancel_reconciliation(db, session_id, dealer.id)
        db.commit()
    except ValueError:
        pass
    return RedirectResponse("/dealer/reconciliation", status_code=303)


# ==========================================
# B2B Bulk Orders (Dealer)
# ==========================================

@router.get("/b2b-orders", response_class=HTMLResponse)
async def b2b_order_list(
    request: Request,
    page: int = 1,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    orders, total = dealer_service.get_b2b_orders(db, dealer.id, page=page)
    total_pages = (total + 19) // 20

    response = templates.TemplateResponse("dealer/b2b_orders.html", {
        "request": request,
        "dealer": dealer,
        "orders": orders,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "active_page": "b2b_orders",
    })
    return response


@router.get("/b2b-orders/new", response_class=HTMLResponse)
async def b2b_order_new(
    request: Request,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    catalog = dealer_service.get_b2b_catalog_for_dealer(db, dealer.id)
    irr_balance = wallet_service.get_balance(db, dealer.id, asset_code=AssetCode.IRR)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/b2b_order_new.html", {
        "request": request,
        "dealer": dealer,
        "catalog": catalog,
        "irr_balance": irr_balance,
        "csrf_token": csrf,
        "active_page": "b2b_orders",
        "error": None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/b2b-orders/new")
async def b2b_order_submit(
    request: Request,
    csrf_token: str = Form(""),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    form = await request.form()

    # Collect items from form: qty_{product_id} fields
    items_data = []
    for key, val in form.items():
        if key.startswith("qty_") and val and val.strip().isdigit() and int(val.strip()) > 0:
            product_id = int(key.replace("qty_", ""))
            items_data.append({"product_id": product_id, "quantity": int(val.strip())})

    result = dealer_service.create_b2b_order(db, dealer.id, items_data)

    if result["success"]:
        db.commit()
        return RedirectResponse(
            f"/dealer/b2b-orders/{result['order'].id}",
            status_code=302,
        )
    else:
        db.rollback()
        # Re-render form with error
        catalog = dealer_service.get_b2b_catalog_for_dealer(db, dealer.id)
        irr_balance = wallet_service.get_balance(db, dealer.id, asset_code=AssetCode.IRR)
        csrf = new_csrf_token()
        response = templates.TemplateResponse("dealer/b2b_order_new.html", {
            "request": request,
            "dealer": dealer,
            "catalog": catalog,
            "irr_balance": irr_balance,
            "csrf_token": csrf,
            "active_page": "b2b_orders",
            "error": result["message"],
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response


@router.get("/b2b-orders/{order_id}", response_class=HTMLResponse)
async def b2b_order_detail(
    request: Request,
    order_id: int,
    msg: str = "",
    error: str = "",
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    order = dealer_service.get_b2b_order(db, order_id, dealer_id=dealer.id)
    if not order:
        return RedirectResponse("/dealer/b2b-orders", status_code=302)

    irr_balance = wallet_service.get_balance(db, dealer.id, asset_code=AssetCode.IRR)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/b2b_order_detail.html", {
        "request": request,
        "dealer": dealer,
        "order": order,
        "irr_balance": irr_balance,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "active_page": "b2b_orders",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/b2b-orders/{order_id}/pay")
async def b2b_order_pay(
    request: Request,
    order_id: int,
    csrf_token: str = Form(""),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = dealer_service.pay_b2b_order(db, order_id, dealer.id)

    if result["success"]:
        db.commit()
        return RedirectResponse(
            f"/dealer/b2b-orders/{order_id}?msg={result['message']}",
            status_code=302,
        )
    else:
        db.rollback()
        return RedirectResponse(
            f"/dealer/b2b-orders/{order_id}?msg={result['message']}&error=1",
            status_code=302,
        )


@router.post("/b2b-orders/{order_id}/cancel")
async def b2b_order_cancel(
    request: Request,
    order_id: int,
    csrf_token: str = Form(""),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = dealer_service.cancel_b2b_order(db, order_id, dealer.id)

    if result["success"]:
        db.commit()
        return RedirectResponse(
            f"/dealer/b2b-orders/{order_id}?msg={result['message']}",
            status_code=302,
        )
    else:
        db.rollback()
        return RedirectResponse(
            f"/dealer/b2b-orders/{order_id}?msg={result['message']}&error=1",
            status_code=302,
        )


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

    # Check if a buyback request already exists for this bar
    existing_buyback = db.query(BuybackRequest).filter(
        BuybackRequest.bar_id == bar.id,
        BuybackRequest.status != BuybackStatus.REJECTED,
    ).first()
    if existing_buyback:
        return JSONResponse({"found": False, "error": "برای این شمش قبلاً درخواست بازخرید ثبت شده است"})

    product = bar.product
    if not product:
        return JSONResponse({"found": False, "error": "محصول مرتبط یافت نشد"})

    # --- Find original sale price (at time of purchase) ---
    from common.templating import get_setting_from_db
    from modules.order.models import OrderItem, Order

    original_metal_price = None

    # Check DealerSale (POS sale)
    dealer_sale = db.query(DealerSale).filter(DealerSale.bar_id == bar.id).first()
    if dealer_sale and dealer_sale.applied_metal_price:
        original_metal_price = int(dealer_sale.applied_metal_price)

    # Check OrderItem (online order) if not found in POS
    if not original_metal_price:
        order_item = (
            db.query(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(OrderItem.bar_id == bar.id, Order.status == "Paid")
            .first()
        )
        if order_item and order_item.applied_metal_price:
            original_metal_price = int(order_item.applied_metal_price)

    # Use original sale price; fallback to current if no sale record
    _, p_bp, _ = get_product_pricing(db, product)
    if original_metal_price:
        p_price = original_metal_price
    else:
        p_price, p_bp, _ = get_product_pricing(db, product)

    info = calculate_bar_price(
        weight=product.weight, purity=product.purity,
        wage_percent=0,
        base_metal_price=p_price, tax_percent=0,
        base_purity=p_bp,
    )
    raw_gold_toman = info.get("total", 0) // 10

    # Full retail price for reference (using original sale price)
    tax_percent = float(get_setting_from_db(db, "tax_percent", "10"))
    ec_wage = get_end_customer_wage(db, product)
    full_info = calculate_bar_price(
        weight=product.weight, purity=product.purity,
        wage_percent=ec_wage,
        base_metal_price=p_price, tax_percent=tax_percent,
        base_purity=p_bp,
    )
    retail_toman = full_info.get("total", 0) // 10

    # Buyback wage uses separate buyback_wage_percent (no tax) — original sale price
    buyback_pct = float(product.buyback_wage_percent or 0)
    wage_toman = 0
    if buyback_pct > 0:
        bb_info = calculate_bar_price(
            weight=product.weight, purity=product.purity,
            wage_percent=buyback_pct,
            base_metal_price=p_price, tax_percent=0,
            base_purity=p_bp,
        )
        wage_toman = bb_info.get("wage", 0) // 10

    return JSONResponse({
        "found": True,
        "serial_code": bar.serial_code,
        "product_name": product.name,
        "weight": str(product.weight),
        "purity": float(product.purity),
        "raw_gold_toman": raw_gold_toman,
        "wage_toman": wage_toman,
        "retail_toman": retail_toman,
        "owner_name": bar.customer.full_name if bar.customer_id and bar.customer else "نامشخص",
    })


# ==========================================
# Custodial Deliveries (Dealer)
# ==========================================

@router.get("/deliveries", response_class=HTMLResponse)
async def dealer_deliveries(
    request: Request,
    status_filter: str = "",
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    from modules.ownership.service import ownership_service
    requests = ownership_service.get_dealer_delivery_requests(
        db, dealer.id, status_filter=status_filter or None,
    )

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/deliveries.html", {
        "request": request,
        "dealer": dealer,
        "delivery_requests": requests,
        "status_filter": status_filter,
        "csrf_token": csrf,
        "active_page": "deliveries",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.get("/deliveries/{req_id}", response_class=HTMLResponse)
async def dealer_delivery_detail(
    request: Request,
    req_id: int,
    error: str = None,
    msg: str = None,
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    from modules.ownership.service import ownership_service
    req = ownership_service.get_delivery_request(db, req_id)
    if not req or req.dealer_id != dealer.id:
        return RedirectResponse("/dealer/deliveries", status_code=303)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("dealer/delivery_confirm.html", {
        "request": request,
        "dealer": dealer,
        "delivery_req": req,
        "csrf_token": csrf,
        "error": error,
        "msg": msg,
        "active_page": "deliveries",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/deliveries/{req_id}/confirm")
async def dealer_delivery_confirm(
    request: Request,
    req_id: int,
    otp_code: str = Form(...),
    serial_code: str = Form(...),
    csrf_token: str = Form(None),
    dealer=Depends(require_dealer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    from modules.ownership.service import ownership_service
    try:
        ownership_service.confirm_delivery(db, req_id, dealer.id, otp_code, serial_code)
        db.commit()
        import urllib.parse
        msg = urllib.parse.quote("تحویل با موفقیت ثبت شد")
        return RedirectResponse(f"/dealer/deliveries/{req_id}?msg={msg}", status_code=303)
    except ValueError as e:
        db.rollback()
        import urllib.parse
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/dealer/deliveries/{req_id}?error={error}", status_code=303)
