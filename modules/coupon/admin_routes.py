"""
Coupon Admin Routes
=====================
CRUD for coupons, mobile whitelist management, usage history.
"""

from datetime import datetime
from typing import List as TypingList
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.coupon.service import coupon_service
from modules.coupon.models import CouponStatus, CouponType, DiscountMode, CouponScope
from modules.catalog.models import Product, ProductCategory

router = APIRouter(prefix="/admin/coupons", tags=["admin-coupon"])


def _parse_datetime(val: str):
    """Parse datetime from form input."""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


# ==========================================
# 📋 Coupon List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def coupon_list(
    request: Request,
    page: int = 1,
    status: str = None,
    search: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons")),
):
    per_page = 30
    coupons, total = coupon_service.get_all_coupons(
        db, page=page, per_page=per_page,
        status_filter=status, search=search,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)
    stats = coupon_service.get_stats(db)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/coupon/list.html", {
        "request": request,
        "user": user,
        "coupons": coupons,
        "stats": stats,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "status_filter": status,
        "search": search or "",
        "csrf_token": csrf,
        "active_page": "coupons",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# ➕ Create Coupon
# ==========================================

@router.get("/new", response_class=HTMLResponse)
async def coupon_new_form(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons")),
):
    products = db.query(Product).filter(Product.is_active == True).all()
    product_categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).order_by(ProductCategory.sort_order).all()
    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/coupon/form.html", {
        "request": request,
        "user": user,
        "coupon": None,
        "products": products,
        "product_categories": product_categories,
        "csrf_token": csrf,
        "active_page": "coupons",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/new")
async def coupon_create(
    request: Request,
    code: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    coupon_type: str = Form("DISCOUNT"),
    discount_mode: str = Form("PERCENT"),
    discount_value: str = Form(...),
    max_discount_amount: str = Form(""),
    scope: str = Form("GLOBAL"),
    scope_product_id: str = Form(""),
    min_order_amount: str = Form("0"),
    max_order_amount: str = Form(""),
    min_quantity: str = Form("0"),
    max_total_uses: str = Form(""),
    max_per_customer: str = Form("1"),
    starts_at: str = Form(""),
    expires_at: str = Form(""),
    first_purchase_only: str = Form(None),
    is_combinable: str = Form(None),
    is_private: str = Form(None),
    status: str = Form("ACTIVE"),
    mobiles_text: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons", level="create")),
):
    csrf_check(request, csrf_token)

    # Extract category_ids from form (multi-select checkboxes)
    form_data = await request.form()
    category_ids = form_data.getlist("category_ids")

    # Convert toman inputs to rial where needed
    def toman_to_rial(val):
        if not val:
            return None
        try:
            return int(val) * 10
        except (ValueError, TypeError):
            return None

    data = {
        "code": code,
        "title": title,
        "description": description,
        "coupon_type": coupon_type,
        "discount_mode": discount_mode,
        "discount_value": int(discount_value) if discount_mode == "PERCENT" else toman_to_rial(discount_value),
        "max_discount_amount": toman_to_rial(max_discount_amount),
        "scope": scope,
        "scope_product_id": scope_product_id or None,
        "category_ids": [int(c) for c in category_ids if c],
        "min_order_amount": toman_to_rial(min_order_amount) or 0,
        "max_order_amount": toman_to_rial(max_order_amount),
        "min_quantity": min_quantity or 0,
        "max_total_uses": max_total_uses or None,
        "max_per_customer": max_per_customer or 1,
        "starts_at": _parse_datetime(starts_at),
        "expires_at": _parse_datetime(expires_at),
        "first_purchase_only": first_purchase_only,
        "is_combinable": is_combinable,
        "is_private": is_private,
        "status": status,
    }

    try:
        coupon = coupon_service.create_coupon(db, data)

        # Add mobiles if provided
        if mobiles_text.strip():
            coupon_service.add_mobiles_bulk(db, coupon.id, mobiles_text)

        db.commit()
        return RedirectResponse(
            f"/admin/coupons/{coupon.id}?msg=کوپن+با+موفقیت+ایجاد+شد",
            status_code=302,
        )
    except Exception as e:
        db.rollback()
        return RedirectResponse(f"/admin/coupons/new?error={str(e)}", status_code=302)


# ==========================================
# 👁️ Coupon Detail
# ==========================================

@router.get("/{coupon_id}", response_class=HTMLResponse)
async def coupon_detail(
    request: Request,
    coupon_id: int,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons")),
):
    coupon = coupon_service.get_coupon_by_id(db, coupon_id)
    if not coupon:
        raise HTTPException(404, "کوپن یافت نشد")

    usages, usage_total = coupon_service.get_coupon_usages(db, coupon_id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/coupon/detail.html", {
        "request": request,
        "user": user,
        "coupon": coupon,
        "usages": usages,
        "usage_total": usage_total,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "active_page": "coupons",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# ✏️ Edit Coupon
# ==========================================

@router.get("/{coupon_id}/edit", response_class=HTMLResponse)
async def coupon_edit_form(
    request: Request,
    coupon_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons")),
):
    coupon = coupon_service.get_coupon_by_id(db, coupon_id)
    if not coupon:
        raise HTTPException(404, "کوپن یافت نشد")

    products = db.query(Product).filter(Product.is_active == True).all()
    product_categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).order_by(ProductCategory.sort_order).all()
    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/coupon/form.html", {
        "request": request,
        "user": user,
        "coupon": coupon,
        "products": products,
        "product_categories": product_categories,
        "csrf_token": csrf,
        "active_page": "coupons",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/{coupon_id}/edit")
async def coupon_edit(
    request: Request,
    coupon_id: int,
    title: str = Form(...),
    description: str = Form(""),
    coupon_type: str = Form("DISCOUNT"),
    discount_mode: str = Form("PERCENT"),
    discount_value: str = Form(...),
    max_discount_amount: str = Form(""),
    scope: str = Form("GLOBAL"),
    scope_product_id: str = Form(""),
    min_order_amount: str = Form("0"),
    max_order_amount: str = Form(""),
    min_quantity: str = Form("0"),
    max_total_uses: str = Form(""),
    max_per_customer: str = Form("1"),
    starts_at: str = Form(""),
    expires_at: str = Form(""),
    first_purchase_only: str = Form(None),
    is_combinable: str = Form(None),
    is_private: str = Form(None),
    status: str = Form("ACTIVE"),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons", level="edit")),
):
    csrf_check(request, csrf_token)

    # Extract category_ids from form (multi-select checkboxes)
    form_data = await request.form()
    category_ids = form_data.getlist("category_ids")

    def toman_to_rial(val):
        if not val:
            return None
        try:
            return int(val) * 10
        except (ValueError, TypeError):
            return None

    data = {
        "title": title,
        "description": description,
        "coupon_type": coupon_type,
        "discount_mode": discount_mode,
        "discount_value": int(discount_value) if discount_mode == "PERCENT" else toman_to_rial(discount_value),
        "max_discount_amount": toman_to_rial(max_discount_amount),
        "scope": scope,
        "scope_product_id": scope_product_id or None,
        "category_ids": [int(c) for c in category_ids if c],
        "min_order_amount": toman_to_rial(min_order_amount) or 0,
        "max_order_amount": toman_to_rial(max_order_amount),
        "min_quantity": min_quantity or 0,
        "max_total_uses": max_total_uses or None,
        "max_per_customer": max_per_customer or 1,
        "starts_at": _parse_datetime(starts_at),
        "expires_at": _parse_datetime(expires_at),
        "first_purchase_only": first_purchase_only,
        "is_combinable": is_combinable,
        "is_private": is_private,
        "status": status,
    }

    try:
        coupon_service.update_coupon(db, coupon_id, data)
        db.commit()
        return RedirectResponse(
            f"/admin/coupons/{coupon_id}?msg=کوپن+با+موفقیت+بروزرسانی+شد",
            status_code=302,
        )
    except ValueError as e:
        db.rollback()
        return RedirectResponse(
            f"/admin/coupons/{coupon_id}/edit?error={str(e)}",
            status_code=302,
        )


# ==========================================
# 🗑️ Delete Coupon
# ==========================================

@router.post("/{coupon_id}/delete")
async def coupon_delete(
    request: Request,
    coupon_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons", level="full")),
):
    csrf_check(request, csrf_token)
    try:
        coupon_service.delete_coupon(db, coupon_id)
        db.commit()
        return RedirectResponse("/admin/coupons?msg=کوپن+حذف+شد", status_code=302)
    except ValueError as e:
        db.rollback()
        return RedirectResponse(f"/admin/coupons/{coupon_id}?error={str(e)}", status_code=302)


# ==========================================
# 🔄 Toggle Coupon Status
# ==========================================

@router.post("/{coupon_id}/toggle")
async def coupon_toggle(
    request: Request,
    coupon_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons", level="edit")),
):
    csrf_check(request, csrf_token)
    coupon = coupon_service.get_coupon_by_id(db, coupon_id)
    if not coupon:
        return RedirectResponse("/admin/coupons?error=کوپن+یافت+نشد", status_code=302)

    new_status = CouponStatus.INACTIVE if coupon.status == CouponStatus.ACTIVE else CouponStatus.ACTIVE
    coupon_service.update_coupon(db, coupon_id, {"status": new_status})
    db.commit()

    label = "فعال" if new_status == CouponStatus.ACTIVE else "غیرفعال"
    return RedirectResponse(f"/admin/coupons?msg=کوپن+{label}+شد", status_code=302)


# ==========================================
# 📱 Mobile Whitelist
# ==========================================

@router.post("/{coupon_id}/mobiles/add")
async def coupon_add_mobiles(
    request: Request,
    coupon_id: int,
    mobiles_text: str = Form(""),
    single_mobile: str = Form(""),
    note: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons", level="edit")),
):
    csrf_check(request, csrf_token)
    count = 0
    try:
        if mobiles_text.strip():
            count = coupon_service.add_mobiles_bulk(db, coupon_id, mobiles_text)
        elif single_mobile.strip():
            coupon_service.add_mobile(db, coupon_id, single_mobile.strip(), note)
            count = 1
        db.commit()
        return RedirectResponse(
            f"/admin/coupons/{coupon_id}?msg={count}+شماره+اضافه+شد",
            status_code=302,
        )
    except ValueError as e:
        db.rollback()
        return RedirectResponse(f"/admin/coupons/{coupon_id}?error={str(e)}", status_code=302)


@router.post("/{coupon_id}/mobiles/{mobile_id}/remove")
async def coupon_remove_mobile(
    request: Request,
    coupon_id: int,
    mobile_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("coupons", level="edit")),
):
    csrf_check(request, csrf_token)
    coupon_service.remove_mobile(db, mobile_id)
    db.commit()
    return RedirectResponse(f"/admin/coupons/{coupon_id}?msg=شماره+حذف+شد", status_code=302)
