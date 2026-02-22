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
from modules.auth.deps import require_permission
from modules.dealer.service import dealer_service
from modules.dealer.models import DealerTier
from modules.catalog.models import Product, ProductTierWage
from modules.customer.address_models import GeoProvince, GeoCity, GeoDistrict

router = APIRouter(prefix="/admin/dealers", tags=["admin-dealer"])


# ==========================================
# Dealer Sales (Admin view of ALL POS sales)
# ==========================================

@router.get("/sales", response_class=HTMLResponse)
async def dealer_sales_admin(
    request: Request,
    page: int = 1,
    dealer_id: str = "",
    search: str = "",
    date_from: str = "",
    date_to: str = "",
    has_discount: str = "",
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    from modules.user.models import User

    # Parse dealer_id filter
    did = None
    if dealer_id and dealer_id.strip().isdigit():
        did = int(dealer_id.strip())

    sales, total, stats = dealer_service.list_all_sales_admin(
        db, page=page, per_page=30,
        dealer_id=did, search=search.strip(),
        date_from=date_from.strip(), date_to=date_to.strip(),
        has_discount=has_discount.strip(),
    )
    total_pages = (total + 29) // 30

    # Load dealer list for dropdown filter
    dealers = db.query(User).filter(User.is_dealer == True, User.is_active == True).order_by(User.first_name).all()

    response = templates.TemplateResponse("admin/dealers/sales.html", {
        "request": request,
        "user": user,
        "sales": sales,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "stats": stats,
        "dealers": dealers,
        "filter_dealer_id": dealer_id,
        "filter_search": search,
        "filter_date_from": date_from,
        "filter_date_to": date_to,
        "filter_has_discount": has_discount,
        "active_page": "dealer_sales",
    })
    return response


# ==========================================
# Dealer List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def dealer_list(
    request: Request,
    page: int = 1,
    user=Depends(require_permission("dealers")),
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

def _load_form_context(db: Session):
    """Load provinces and tiers for dealer form."""
    provinces = db.query(GeoProvince).order_by(GeoProvince.sort_order, GeoProvince.name).all()
    tiers = db.query(DealerTier).filter(DealerTier.is_active == True).order_by(DealerTier.sort_order).all()
    return provinces, tiers


def _load_edit_geo(db: Session, dealer):
    """Load cities/districts for pre-populating edit form cascades."""
    cities = []
    districts = []
    if dealer.province_id:
        cities = db.query(GeoCity).filter(
            GeoCity.province_id == dealer.province_id
        ).order_by(GeoCity.sort_order, GeoCity.name).all()
    if dealer.city_id:
        districts = db.query(GeoDistrict).filter(
            GeoDistrict.city_id == dealer.city_id
        ).order_by(GeoDistrict.name).all()
    return cities, districts


def _parse_int(val: str) -> int | None:
    """Parse string to int, return None if empty."""
    return int(val) if val and val.strip().isdigit() else None


@router.get("/create", response_class=HTMLResponse)
async def dealer_create_form(
    request: Request,
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    provinces, tiers = _load_form_context(db)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/form.html", {
        "request": request,
        "user": user,
        "dealer": None,
        "provinces": provinces,
        "cities": [],
        "districts": [],
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
    tier_id: str = Form(""),
    province_id: str = Form(""),
    city_id: str = Form(""),
    district_id: str = Form(""),
    address: str = Form(""),
    postal_code: str = Form(""),
    landline_phone: str = Form(""),
    is_warehouse: str = Form("off"),
    is_postal_hub: str = Form("off"),
    can_distribute: str = Form("off"),
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers", level="create")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    # Check duplicate mobile
    existing = dealer_service.get_dealer_by_mobile(db, mobile.strip())
    if existing:
        provinces, tiers = _load_form_context(db)
        csrf = new_csrf_token()
        response = templates.TemplateResponse("admin/dealers/form.html", {
            "request": request,
            "user": user,
            "dealer": None,
            "provinces": provinces,
            "cities": [],
            "districts": [],
            "tiers": tiers,
            "csrf_token": csrf,
            "active_page": "dealers",
            "error": "این شماره موبایل قبلا ثبت شده است",
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response

    dealer = dealer_service.create_dealer(
        db, mobile.strip(), full_name.strip(),
        national_id=national_id.strip(),
        tier_id=_parse_int(tier_id),
        province_id=_parse_int(province_id),
        city_id=_parse_int(city_id),
        district_id=_parse_int(district_id),
        address=address.strip(),
        postal_code=postal_code.strip(),
        landline_phone=landline_phone.strip(),
        is_warehouse=(is_warehouse == "on"),
        is_postal_hub=(is_postal_hub == "on"),
        can_distribute=(can_distribute == "on"),
    )
    db.commit()

    # Rasis POS: auto-register dealer as branch
    try:
        from modules.rasis.service import rasis_service
        from common.templating import get_setting_from_db
        if get_setting_from_db(db, "rasis_pos_enabled", "false") == "true":
            rasis_service.register_branch(db, dealer)
            db.commit()
    except Exception:
        pass  # Never block dealer creation

    return RedirectResponse("/admin/dealers", status_code=302)


# ==========================================
# Edit Dealer
# ==========================================

@router.get("/{dealer_id}/edit", response_class=HTMLResponse)
async def dealer_edit_form(
    dealer_id: int,
    request: Request,
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    dealer = dealer_service.get_dealer(db, dealer_id)
    if not dealer:
        return RedirectResponse("/admin/dealers", status_code=302)

    provinces, tiers = _load_form_context(db)
    cities, districts = _load_edit_geo(db, dealer)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/form.html", {
        "request": request,
        "user": user,
        "dealer": dealer,
        "provinces": provinces,
        "cities": cities,
        "districts": districts,
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
    tier_id: str = Form(""),
    province_id: str = Form(""),
    city_id: str = Form(""),
    district_id: str = Form(""),
    address: str = Form(""),
    postal_code: str = Form(""),
    landline_phone: str = Form(""),
    is_active: str = Form("off"),
    is_warehouse: str = Form("off"),
    is_postal_hub: str = Form("off"),
    can_distribute: str = Form("off"),
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers", level="edit")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    dealer = dealer_service.update_dealer(
        db, dealer_id,
        full_name=full_name.strip(),
        tier_id=_parse_int(tier_id),
        province_id=_parse_int(province_id),
        city_id=_parse_int(city_id),
        district_id=_parse_int(district_id),
        address=address.strip(),
        postal_code=postal_code.strip(),
        landline_phone=landline_phone.strip(),
        is_active=(is_active == "on"),
        is_warehouse=(is_warehouse == "on"),
        is_postal_hub=(is_postal_hub == "on"),
        can_distribute=(can_distribute == "on"),
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
    user=Depends(require_permission("dealers", level="full")),
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
    user=Depends(require_permission("dealers", level="full")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    dealer_service.revoke_api_key(db, dealer_id)
    db.commit()
    return RedirectResponse(f"/admin/dealers/{dealer_id}/edit", status_code=302)


@router.post("/{dealer_id}/rasis-sync")
async def rasis_sync_dealer(
    dealer_id: int,
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers", level="edit")),
    db: Session = Depends(get_db),
):
    """Manual full sync of dealer's inventory with Rasis POS."""
    csrf_check(request, csrf_token)
    from modules.rasis.service import rasis_service
    dealer = dealer_service.get_dealer(db, dealer_id)
    if not dealer:
        return RedirectResponse("/admin/dealers", status_code=302)

    result = rasis_service.sync_dealer_inventory(db, dealer)
    db.commit()
    return RedirectResponse(f"/admin/dealers/{dealer_id}/edit", status_code=302)


# ==========================================
# Buyback Management
# ==========================================

@router.get("/buybacks", response_class=HTMLResponse)
async def buyback_management(
    request: Request,
    page: int = 1,
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    from modules.dealer.models import BuybackRequest

    q = db.query(BuybackRequest)
    total = q.count()
    buybacks = q.order_by(BuybackRequest.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    total_pages = (total + 19) // 20

    return templates.TemplateResponse("admin/dealers/buybacks.html", {
        "request": request,
        "user": user,
        "buybacks": buybacks,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "active_page": "dealer_buybacks",
    })


# approve_buyback / reject_buyback routes removed — buyback is now instant


# ==========================================
# Dealer Stats (AJAX)
# ==========================================

@router.get("/{dealer_id}/stats")
async def dealer_stats_api(
    dealer_id: int,
    user=Depends(require_permission("dealers")),
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
    user=Depends(require_permission("dealers")),
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
    user=Depends(require_permission("dealers")),
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
    user=Depends(require_permission("dealers", level="create")),
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
    user=Depends(require_permission("dealers")),
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
    user=Depends(require_permission("dealers", level="edit")),
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
    user=Depends(require_permission("dealers")),
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
    user=Depends(require_permission("dealers", level="edit")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    form = await request.form()

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return RedirectResponse("/admin/products", status_code=302)

    max_wage = float(product.wage)

    tiers = db.query(DealerTier).filter(DealerTier.is_active == True).all()
    for t in tiers:
        if t.is_end_customer:
            continue  # end_customer wage is auto-synced from product.wage

        wage_val = form.get(f"wage_{t.id}", "").strip()
        existing = db.query(ProductTierWage).filter(
            ProductTierWage.product_id == product_id,
            ProductTierWage.tier_id == t.id,
        ).first()

        if wage_val:
            wage_pct = float(wage_val)
            if wage_pct > max_wage:
                return RedirectResponse(
                    f"/admin/dealers/tier-wages/{product_id}?msg=اجرت+سطح+{t.name}+نمی‌تواند+بیشتر+از+اجرت+محصول+({max_wage}%)+باشد&error=1",
                    status_code=302,
                )
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


# ==========================================
# Sub-dealer Relations (Admin)
# ==========================================

@router.get("/{dealer_id}/sub-dealers", response_class=HTMLResponse)
async def admin_sub_dealers(
    request: Request,
    dealer_id: int,
    msg: str = "",
    error: str = "",
    admin=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    from modules.user.models import User
    dealer = db.query(User).filter(User.id == dealer_id, User.is_dealer == True).first()
    if not dealer:
        return RedirectResponse("/admin/dealers?msg=نماینده+یافت+نشد&error=1", status_code=302)

    # This dealer's sub-dealers (where they are parent)
    sub_rels = dealer_service.get_sub_dealers(db, dealer_id)
    # This dealer's parent (where they are child)
    parent_rel = dealer_service.get_parent_relation(db, dealer_id)
    # Commission earned from sub-dealers
    commission_stats = dealer_service.get_sub_dealer_commission_stats(db, dealer_id)
    # All dealers for the add form dropdown
    all_dealers = db.query(User).filter(User.is_dealer == True, User.is_active == True, User.id != dealer_id).order_by(User.first_name).all()

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/sub_dealers.html", {
        "request": request,
        "admin": admin,
        "dealer": dealer,
        "sub_rels": sub_rels,
        "parent_rel": parent_rel,
        "commission_stats": commission_stats,
        "all_dealers": all_dealers,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "active_page": "dealers",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/{dealer_id}/sub-dealers/add")
async def admin_add_sub_dealer(
    request: Request,
    dealer_id: int,
    child_dealer_id: int = Form(...),
    commission_split_percent: str = Form("20"),
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    admin=Depends(require_permission("dealers", level="create")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    try:
        split_pct = float(commission_split_percent)
    except (ValueError, TypeError):
        split_pct = 20.0

    result = dealer_service.create_sub_dealer_relation(
        db, parent_id=dealer_id, child_id=child_dealer_id,
        commission_split_percent=split_pct, admin_note=admin_note,
    )

    if result["success"]:
        db.commit()
        return RedirectResponse(
            f"/admin/dealers/{dealer_id}/sub-dealers?msg={result['message']}",
            status_code=302,
        )
    else:
        db.rollback()
        return RedirectResponse(
            f"/admin/dealers/{dealer_id}/sub-dealers?msg={result['message']}&error=1",
            status_code=302,
        )


@router.post("/sub-dealers/{relation_id}/deactivate")
async def admin_deactivate_sub_dealer(
    request: Request,
    relation_id: int,
    csrf_token: str = Form(""),
    admin=Depends(require_permission("dealers", level="full")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    from modules.dealer.models import SubDealerRelation
    rel = db.query(SubDealerRelation).filter(SubDealerRelation.id == relation_id).first()
    if not rel:
        return RedirectResponse("/admin/dealers?msg=ارتباط+یافت+نشد&error=1", status_code=302)

    parent_id = rel.parent_dealer_id
    result = dealer_service.deactivate_sub_dealer_relation(db, relation_id)
    if result["success"]:
        db.commit()
    else:
        db.rollback()

    return RedirectResponse(
        f"/admin/dealers/{parent_id}/sub-dealers?msg={result['message']}{'&error=1' if not result['success'] else ''}",
        status_code=302,
    )


# ==========================================
# B2B Bulk Orders (Admin)
# ==========================================

@router.get("/b2b-orders", response_class=HTMLResponse)
async def admin_b2b_orders(
    request: Request,
    page: int = 1,
    status: str = "",
    dealer_id: str = "",
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    from modules.user.models import User

    did = None
    if dealer_id and dealer_id.strip().isdigit():
        did = int(dealer_id.strip())

    orders, total = dealer_service.list_all_b2b_orders_admin(
        db, status_filter=status, dealer_id=did, page=page,
    )
    total_pages = (total + 29) // 30

    dealers = db.query(User).filter(User.is_dealer == True, User.is_active == True).order_by(User.first_name).all()

    response = templates.TemplateResponse("admin/dealers/b2b_orders.html", {
        "request": request,
        "user": user,
        "orders": orders,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "dealers": dealers,
        "filter_status": status,
        "filter_dealer_id": dealer_id,
        "active_page": "b2b_orders",
    })
    return response


@router.get("/b2b-orders/{order_id}", response_class=HTMLResponse)
async def admin_b2b_order_detail(
    request: Request,
    order_id: int,
    msg: str = "",
    error: str = "",
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    order = dealer_service.get_b2b_order(db, order_id)
    if not order:
        return RedirectResponse("/admin/dealers/b2b-orders", status_code=302)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealers/b2b_order_detail.html", {
        "request": request,
        "user": user,
        "order": order,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "active_page": "b2b_orders",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/b2b-orders/{order_id}/approve")
async def admin_b2b_approve(
    request: Request,
    order_id: int,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers", level="full")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = dealer_service.approve_b2b_order(db, order_id, user.id, admin_note)

    if result["success"]:
        db.commit()
    else:
        db.rollback()

    return RedirectResponse(
        f"/admin/dealers/b2b-orders/{order_id}?msg={result['message']}{'&error=1' if not result['success'] else ''}",
        status_code=302,
    )


@router.post("/b2b-orders/{order_id}/reject")
async def admin_b2b_reject(
    request: Request,
    order_id: int,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers", level="full")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = dealer_service.reject_b2b_order(db, order_id, user.id, admin_note)

    if result["success"]:
        db.commit()
    else:
        db.rollback()

    return RedirectResponse(
        f"/admin/dealers/b2b-orders/{order_id}?msg={result['message']}{'&error=1' if not result['success'] else ''}",
        status_code=302,
    )


@router.post("/b2b-orders/{order_id}/fulfill")
async def admin_b2b_fulfill(
    request: Request,
    order_id: int,
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers", level="full")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    result = dealer_service.fulfill_b2b_order(db, order_id, user.id)

    if result["success"]:
        db.commit()
    else:
        db.rollback()

    return RedirectResponse(
        f"/admin/dealers/b2b-orders/{order_id}?msg={result['message']}{'&error=1' if not result['success'] else ''}",
        status_code=302,
    )
