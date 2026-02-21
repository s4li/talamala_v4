"""
Inventory Module - Admin Routes
=================================
Bar management: list, generate, edit, update, bulk actions, image management.
"""

import urllib.parse
from typing import List, Optional

from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from common.helpers import safe_int
from modules.auth.deps import require_permission
from modules.inventory.models import BarStatus
from modules.inventory.service import inventory_service
from modules.catalog.models import Product, Batch
from modules.user.models import User
from modules.customer.address_models import GeoProvince

router = APIRouter(tags=["inventory-admin"])


def ctx(request, user, **extra):
    csrf = new_csrf_token()
    return {"request": request, "user": user, "csrf_token": csrf, **extra}, csrf


# ==========================================
# 📊 Bar List
# ==========================================

@router.get("/admin/bars", response_class=HTMLResponse)
async def list_bars(
    request: Request,
    page: int = 1,
    search: str = Query(None),
    customer_id: str = Query(None),
    status: str = Query(None),
    product_id: str = Query(None),
    dealer_id: str = Query(None),
    msg: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory")),
):
    _customer_id = safe_int(customer_id)
    _product_id = safe_int(product_id)
    _dealer_id = safe_int(dealer_id)
    _status = status if status else None

    bars, total, total_pages = inventory_service.list_bars(
        db, page=page, search=search or None, customer_id=_customer_id,
        status=_status, product_id=_product_id, dealer_id=_dealer_id,
    )

    filter_customer = None
    if _customer_id:
        filter_customer = db.query(User).filter(User.id == _customer_id).first()

    all_dealers = db.query(User).filter(User.is_dealer == True, User.is_active == True).order_by(User.first_name, User.last_name).all()
    all_provinces = db.query(GeoProvince).order_by(GeoProvince.sort_order, GeoProvince.name).all()

    data, csrf = ctx(
        request, user,
        bars=bars,
        page=page,
        total=total,
        total_pages=total_pages,
        search=search or "",
        filter_customer=filter_customer,
        status_filter=status or "",
        product_filter=product_id or "",
        dealer_filter=dealer_id or "",
        all_products=db.query(Product).all(),
        all_customers=db.query(User).filter(User.is_customer == True).all(),
        all_batches=db.query(Batch).all(),
        all_dealers=all_dealers,
        all_provinces=all_provinces,
        bar_statuses=BarStatus,
        msg=msg,
        error=error,
    )
    response = templates.TemplateResponse("admin/inventory/bars.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# ➕ Generate
# ==========================================

@router.post("/admin/bars/generate")
async def generate_bars(
    request: Request,
    count: int = Form(...),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory")),
):
    csrf_check(request, csrf_token)
    count = min(count, 500)  # Safety limit
    created = inventory_service.generate_bars(db, count)
    msg = urllib.parse.quote(f"{created} شمش جدید ایجاد شد")
    return RedirectResponse(f"/admin/bars?msg={msg}", status_code=303)


# ==========================================
# ✏️ Edit
# ==========================================

@router.get("/admin/bars/edit/{bar_id}", response_class=HTMLResponse)
async def edit_bar_form(
    request: Request, bar_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory")),
):
    bar = inventory_service.get_by_id(db, bar_id)
    if not bar:
        raise HTTPException(404)

    data, csrf = ctx(
        request, user,
        bar=bar,
        products=db.query(Product).all(),
        batches=db.query(Batch).all(),
        customers=db.query(User).filter(User.is_customer == True).all(),
        dealers=db.query(User).filter(User.is_dealer == True, User.is_active == True).order_by(User.first_name, User.last_name).all(),
        provinces=db.query(GeoProvince).order_by(GeoProvince.sort_order, GeoProvince.name).all(),
        bar_statuses=BarStatus,
    )
    response = templates.TemplateResponse("admin/inventory/edit_bar.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/bars/update/{bar_id}")
async def update_bar(
    request: Request, bar_id: int,
    status: str = Form(...),
    product_id: str = Form(None),
    customer_id: str = Form(None),
    batch_id: str = Form(None),
    dealer_id: str = Form(None),
    transfer_note: str = Form(""),
    new_files: List[UploadFile] = File(None),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory")),
):
    csrf_check(request, csrf_token)
    inventory_service.update_bar(db, bar_id, {
        "status": status,
        "product_id": product_id,
        "customer_id": customer_id,
        "batch_id": batch_id,
        "dealer_id": dealer_id,
        "transfer_note": transfer_note,
    }, new_files, updated_by=user.full_name)
    db.commit()
    return RedirectResponse("/admin/bars", status_code=303)


# ==========================================
# 🔄 Bulk Actions
# ==========================================

@router.post("/admin/bars/bulk_action")
async def bulk_action(
    request: Request,
    action: str = Form(...),
    selected_ids: str = Form(...),
    target_product_id: str = Form(None),
    target_customer_id: str = Form(None),
    target_batch_id: str = Form(None),
    target_dealer_id: str = Form(None),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory")),
):
    csrf_check(request, csrf_token)

    try:
        ids = [int(i) for i in selected_ids.split(",") if i.strip().isdigit()]
    except Exception:
        ids = []

    if not ids:
        msg = urllib.parse.quote("هیچ موردی انتخاب نشده")
        return RedirectResponse(f"/admin/bars?error={msg}", status_code=303)

    if action == "delete":
        # Only admin can delete
        if getattr(user, "role", "") != "admin":
            return HTMLResponse("⛔ فقط مدیر سیستم می‌تواند حذف کند.", status_code=403)
        count = inventory_service.bulk_delete(db, ids)
        msg = urllib.parse.quote(f"{count} شمش حذف شد")

    elif action == "update":
        count = inventory_service.bulk_update(db, ids, {
            "target_product_id": target_product_id,
            "target_customer_id": target_customer_id,
            "target_batch_id": target_batch_id,
            "target_dealer_id": target_dealer_id,
        })
        msg = urllib.parse.quote(f"{count} شمش بروزرسانی شد")
    else:
        msg = urllib.parse.quote("عملیات نامعتبر")

    db.commit()
    return RedirectResponse(f"/admin/bars?msg={msg}", status_code=303)


# ==========================================
# 🖼️ Image Management
# ==========================================

@router.post("/admin/bars/delete_image/{img_id}")
async def delete_bar_image(
    request: Request, img_id: int,
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory")),
):
    csrf_check(request, csrf_token)
    bar_id = inventory_service.delete_image(db, img_id)
    db.commit()
    if bar_id:
        return RedirectResponse(f"/admin/bars/edit/{bar_id}", status_code=303)
    return RedirectResponse("/admin/bars", status_code=303)

