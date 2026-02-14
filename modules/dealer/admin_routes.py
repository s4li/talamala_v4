"""
Dealer Module - Admin Routes
================================
Admin management of dealers, buyback approvals, and stats.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token, csrf_check
from modules.auth.deps import require_operator_or_admin
from modules.dealer.service import dealer_service
from modules.dealer.models import DealerTier
from modules.catalog.models import Product, ProductTierWage
from modules.inventory.models import Location, LocationType

router = APIRouter(prefix="/admin/dealers", tags=["admin-dealer"])


# ==========================================
# Dealer List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def dealer_list(
    request: Request,
    page: int = 1,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    dealers, total = dealer_service.list_dealers(db, page=page)
    total_pages = (total + 29) // 30
    admin_stats = dealer_service.get_admin_stats(db)

    response = templates.TemplateResponse("admin/dealers/list.html", {
        "request": request,
        "user": user,
        "dealers": dealers,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "stats": admin_stats,
        "active_page": "dealers",
    })
    return response


# ==========================================
# Create Dealer
# ==========================================

@router.get("/create", response_class=HTMLResponse)
async def dealer_create_form(
    request: Request,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    locations = db.query(Location).filter(
        Location.is_active == True,
        Location.location_type == LocationType.BRANCH,
    ).order_by(Location.name).all()
    tiers = db.query(DealerTier).filter(DealerTier.is_active == True).order_by(DealerTier.sort_order).all()

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/form.html", {
        "request": request,
        "user": user,
        "dealer": None,
        "locations": locations,
        "tiers": tiers,
        "csrf_token": csrf,
        "active_page": "dealers",
        "error": None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/create")
async def dealer_create_submit(
    request: Request,
    mobile: str = Form(...),
    full_name: str = Form(...),
    national_id: str = Form(""),
    location_id: str = Form(""),
    tier_id: str = Form(""),
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    # Check duplicate mobile
    existing = dealer_service.get_dealer_by_mobile(db, mobile.strip())
    if existing:
        locations = db.query(Location).filter(
            Location.is_active == True,
            Location.location_type == LocationType.BRANCH,
        ).order_by(Location.name).all()
        tiers = db.query(DealerTier).filter(DealerTier.is_active == True).order_by(DealerTier.sort_order).all()

        csrf = new_csrf_token()
        response = templates.TemplateResponse("admin/dealers/form.html", {
            "request": request,
            "user": user,
            "dealer": None,
            "locations": locations,
            "tiers": tiers,
            "csrf_token": csrf,
            "active_page": "dealers",
            "error": "این شماره موبایل قبلا ثبت شده است",
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response

    loc_id = int(location_id) if location_id.strip() else None
    t_id = int(tier_id) if tier_id.strip() else None
    dealer = dealer_service.create_dealer(
        db, mobile.strip(), full_name.strip(),
        national_id=national_id.strip(),
        location_id=loc_id,
        tier_id=t_id,
    )
    db.commit()

    return RedirectResponse("/admin/dealers", status_code=302)


# ==========================================
# Edit Dealer
# ==========================================

@router.get("/{dealer_id}/edit", response_class=HTMLResponse)
async def dealer_edit_form(
    dealer_id: int,
    request: Request,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    dealer = dealer_service.get_dealer(db, dealer_id)
    if not dealer:
        return RedirectResponse("/admin/dealers", status_code=302)

    locations = db.query(Location).filter(
        Location.is_active == True,
        Location.location_type == LocationType.BRANCH,
    ).order_by(Location.name).all()
    tiers = db.query(DealerTier).filter(DealerTier.is_active == True).order_by(DealerTier.sort_order).all()

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/form.html", {
        "request": request,
        "user": user,
        "dealer": dealer,
        "locations": locations,
        "tiers": tiers,
        "csrf_token": csrf,
        "active_page": "dealers",
        "error": None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/{dealer_id}/edit")
async def dealer_edit_submit(
    dealer_id: int,
    request: Request,
    full_name: str = Form(...),
    location_id: str = Form(""),
    tier_id: str = Form(""),
    is_active: str = Form("off"),
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    loc_id = int(location_id) if location_id.strip() else None
    t_id = int(tier_id) if tier_id.strip() else None
    dealer = dealer_service.update_dealer(
        db, dealer_id,
        full_name=full_name.strip(),
        location_id=loc_id,
        tier_id=t_id,
        is_active=(is_active == "on"),
    )
    db.commit()

    return RedirectResponse("/admin/dealers", status_code=302)


# ==========================================
# API Key Management (for POS devices)
# ==========================================

@router.post("/{dealer_id}/generate-api-key")
async def generate_api_key(
    dealer_id: int,
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    key = dealer_service.generate_api_key(db, dealer_id)
    if key:
        db.commit()
    return RedirectResponse(f"/admin/dealers/{dealer_id}/edit", status_code=302)


@router.post("/{dealer_id}/revoke-api-key")
async def revoke_api_key(
    dealer_id: int,
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    dealer_service.revoke_api_key(db, dealer_id)
    db.commit()
    return RedirectResponse(f"/admin/dealers/{dealer_id}/edit", status_code=302)


# ==========================================
# Buyback Management
# ==========================================

@router.get("/buybacks", response_class=HTMLResponse)
async def buyback_management(
    request: Request,
    page: int = 1,
    status_filter: str = "",
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    from modules.dealer.models import BuybackRequest, BuybackStatus

    q = db.query(BuybackRequest)
    if status_filter:
        q = q.filter(BuybackRequest.status == status_filter)
    total = q.count()
    buybacks = q.order_by(BuybackRequest.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    total_pages = (total + 19) // 20

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/buybacks.html", {
        "request": request,
        "user": user,
        "buybacks": buybacks,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "status_filter": status_filter,
        "csrf_token": csrf,
        "active_page": "dealer_buybacks",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/buybacks/{buyback_id}/approve")
async def approve_buyback(
    buyback_id: int,
    request: Request,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = dealer_service.approve_buyback(db, buyback_id, admin_note=admin_note)
    if result["success"]:
        db.commit()
    return RedirectResponse("/admin/dealers/buybacks", status_code=302)


@router.post("/buybacks/{buyback_id}/reject")
async def reject_buyback(
    buyback_id: int,
    request: Request,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = dealer_service.reject_buyback(db, buyback_id, admin_note=admin_note)
    if result["success"]:
        db.commit()
    return RedirectResponse("/admin/dealers/buybacks", status_code=302)


# ==========================================
# Dealer Stats (AJAX)
# ==========================================

@router.get("/{dealer_id}/stats")
async def dealer_stats_api(
    dealer_id: int,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    stats = dealer_service.get_dealer_stats(db, dealer_id)
    return stats


# ==========================================
# Dealer Tiers CRUD
# ==========================================

@router.get("/tiers/list", response_class=HTMLResponse)
async def tier_list(
    request: Request,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    tiers = db.query(DealerTier).order_by(DealerTier.sort_order).all()
    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/tiers.html", {
        "request": request,
        "user": user,
        "tiers": tiers,
        "csrf_token": csrf,
        "active_page": "dealer_tiers",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.get("/tiers/new", response_class=HTMLResponse)
async def tier_create_form(
    request: Request,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/tier_form.html", {
        "request": request,
        "user": user,
        "tier": None,
        "csrf_token": csrf,
        "active_page": "dealer_tiers",
        "error": None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/tiers/new")
async def tier_create_submit(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    sort_order: int = Form(0),
    is_end_customer: str = Form("off"),
    is_active: str = Form("on"),
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    tier = DealerTier(
        name=name.strip(),
        slug=slug.strip(),
        sort_order=sort_order,
        is_end_customer=(is_end_customer == "on"),
        is_active=(is_active == "on"),
    )
    db.add(tier)
    db.commit()
    return RedirectResponse("/admin/dealers/tiers/list", status_code=302)


@router.get("/tiers/{tier_id}/edit", response_class=HTMLResponse)
async def tier_edit_form(
    tier_id: int,
    request: Request,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    tier = db.query(DealerTier).filter(DealerTier.id == tier_id).first()
    if not tier:
        return RedirectResponse("/admin/dealers/tiers/list", status_code=302)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/tier_form.html", {
        "request": request,
        "user": user,
        "tier": tier,
        "csrf_token": csrf,
        "active_page": "dealer_tiers",
        "error": None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/tiers/{tier_id}/edit")
async def tier_edit_submit(
    tier_id: int,
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    sort_order: int = Form(0),
    is_end_customer: str = Form("off"),
    is_active: str = Form("on"),
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    tier = db.query(DealerTier).filter(DealerTier.id == tier_id).first()
    if not tier:
        return RedirectResponse("/admin/dealers/tiers/list", status_code=302)

    tier.name = name.strip()
    tier.slug = slug.strip()
    tier.sort_order = sort_order
    tier.is_end_customer = (is_end_customer == "on")
    tier.is_active = (is_active == "on")
    db.commit()
    return RedirectResponse("/admin/dealers/tiers/list", status_code=302)


# ==========================================
# Product Tier Wages (admin)
# ==========================================

@router.get("/tier-wages/{product_id}", response_class=HTMLResponse)
async def tier_wages_form(
    product_id: int,
    request: Request,
    msg: str = None,
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return RedirectResponse("/admin/products", status_code=302)

    tiers = db.query(DealerTier).filter(DealerTier.is_active == True).order_by(DealerTier.sort_order).all()
    existing = {tw.tier_id: tw for tw in product.tier_wages}

    tier_data = []
    for t in tiers:
        tw = existing.get(t.id)
        tier_data.append({
            "tier": t,
            "wage_percent": float(tw.wage_percent) if tw else "",
        })

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/tier_wages.html", {
        "request": request,
        "user": user,
        "product": product,
        "tier_data": tier_data,
        "csrf_token": csrf,
        "msg": msg,
        "active_page": "products",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/tier-wages/{product_id}")
async def tier_wages_save(
    product_id: int,
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(require_operator_or_admin),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    form = await request.form()

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return RedirectResponse("/admin/products", status_code=302)

    tiers = db.query(DealerTier).filter(DealerTier.is_active == True).all()
    for t in tiers:
        wage_val = form.get(f"wage_{t.id}", "").strip()
        existing = db.query(ProductTierWage).filter(
            ProductTierWage.product_id == product_id,
            ProductTierWage.tier_id == t.id,
        ).first()

        if wage_val:
            wage_pct = float(wage_val)
            if existing:
                existing.wage_percent = wage_pct
            else:
                db.add(ProductTierWage(
                    product_id=product_id,
                    tier_id=t.id,
                    wage_percent=wage_pct,
                ))
        elif existing:
            db.delete(existing)

    db.commit()
    return RedirectResponse(
        f"/admin/dealers/tier-wages/{product_id}?msg=اجرت+پلکانی+ذخیره+شد",
        status_code=302,
    )
