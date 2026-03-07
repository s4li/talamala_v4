"""
Catalog Module - Admin Routes
===============================
CRUD for Products, PackageTypes, GiftBoxes, Batches.
All routes require staff authentication.
"""

from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from common.flash import flash
from modules.auth.deps import require_permission
from modules.catalog.service import (
    product_service, package_service, gift_box_service, batch_service,
    images, ProductImage, PackageTypeImage, GiftBoxImage, BatchImage,
)
from modules.catalog.models import ProductCategory, PackageType, GiftBox

router = APIRouter(tags=["catalog-admin"])


# ==========================================
# Helper: template context
# ==========================================

def ctx(request, user, **extra):
    csrf = new_csrf_token()
    data = {"request": request, "user": user, "csrf_token": csrf, **extra}
    return data, csrf


# ==========================================
# 📦 Products
# ==========================================

@router.get("/admin/products", response_class=HTMLResponse)
async def list_products(request: Request, db: Session = Depends(get_db), user=Depends(require_permission("products"))):
    products = product_service.list_all(db)
    categories = db.query(ProductCategory).order_by(ProductCategory.sort_order).all()
    packages = db.query(PackageType).all()
    data, csrf = ctx(request, user, products=products, categories=categories, packages=packages)
    response = templates.TemplateResponse("admin/catalog/products.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/products/add")
async def add_product(
    request: Request,
    name: str = Form(...), weight: str = Form(...), purity: str = Form("995"),
    package_type_id: str = Form(""),
    wage: str = Form("0"),
    is_active: bool = Form(True),
    files: List[UploadFile] = File(None),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_permission("products", level="create")),
):
    csrf_check(request, csrf_token)
    form = await request.form()
    category_ids = [int(v) for v in form.getlist("category_ids") if str(v).isdigit()]
    pt_id = int(package_type_id) if package_type_id.strip().isdigit() else None
    product_service.create(db, {
        "name": name, "weight": weight, "purity": purity,
        "category_ids": category_ids, "package_type_id": pt_id,
        "wage": wage,
        "is_active": is_active,
    }, files)
    db.commit()
    return RedirectResponse("/admin/products", status_code=303)


@router.get("/admin/products/edit/{p_id}", response_class=HTMLResponse)
async def edit_product_form(request: Request, p_id: int, db: Session = Depends(get_db), user=Depends(require_permission("products"))):
    p = product_service.get_by_id(db, p_id)
    if not p:
        raise HTTPException(404)
    categories = db.query(ProductCategory).order_by(ProductCategory.sort_order).all()
    packages = db.query(PackageType).all()
    data, csrf = ctx(request, user, p=p, categories=categories, packages=packages)
    response = templates.TemplateResponse("admin/catalog/edit_product.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/products/update/{p_id}")
async def update_product(
    request: Request, p_id: int,
    name: str = Form(...), weight: str = Form(...), purity: str = Form(...),
    package_type_id: str = Form(""),
    wage: str = Form(...),
    is_active: bool = Form(False),
    new_files: List[UploadFile] = File(None),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_permission("products", level="edit")),
):
    csrf_check(request, csrf_token)
    form = await request.form()
    description = form.get("description", "")
    buyback_wage_percent = str(form.get("buyback_wage_percent", "0")).strip()
    category_ids = [int(v) for v in form.getlist("category_ids") if str(v).isdigit()]
    pt_id = int(package_type_id) if package_type_id.strip().isdigit() else None

    product_service.update(db, p_id, {
        "name": name, "weight": weight, "purity": purity,
        "description": description,
        "category_ids": category_ids, "package_type_id": pt_id,
        "wage": wage,
        "buyback_wage_percent": buyback_wage_percent,
        "is_active": is_active,
    }, new_files)
    db.commit()

    return RedirectResponse("/admin/products", status_code=303)


@router.post("/admin/products/delete_image/{img_id}")
async def delete_product_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                db: Session = Depends(get_db), user=Depends(require_permission("products", level="edit"))):
    csrf_check(request, csrf_token)
    pid = images.delete_image(db, ProductImage, img_id)
    db.commit()
    return RedirectResponse(f"/admin/products/edit/{pid}" if pid else "/admin/products", status_code=303)


@router.post("/admin/products/set_default/{img_id}")
async def set_product_default(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                               db: Session = Depends(get_db), user=Depends(require_permission("products", level="edit"))):
    csrf_check(request, csrf_token)
    pid = images.set_default(db, ProductImage, img_id, "product_id")
    db.commit()
    return RedirectResponse(f"/admin/products/edit/{pid}" if pid else "/admin/products", status_code=303)


# ==========================================
# 📦 Package Types (کارت محصول)
# ==========================================

@router.get("/admin/packages", response_class=HTMLResponse)
async def list_packages(request: Request, db: Session = Depends(get_db), user=Depends(require_permission("products"))):
    items = package_service.list_all(db)
    data, csrf = ctx(request, user, packages=items)
    response = templates.TemplateResponse("admin/catalog/packages.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/packages/add")
async def add_package(request: Request, name: str = Form(...), price: str = Form("0"),
                       is_active: str = Form("on"), files: List[UploadFile] = File(None),
                       csrf_token: Optional[str] = Form(None), db: Session = Depends(get_db), user=Depends(require_permission("products", level="create"))):
    csrf_check(request, csrf_token)
    price_rial = int(price) * 10 if price.strip().isdigit() else 0
    package_service.create(db, name, price=price_rial, is_active=(is_active == "on"), files=files)
    db.commit()
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/admin/packages/update/{item_id}")
async def update_package(request: Request, item_id: int, name: str = Form(...), price: str = Form("0"),
                           is_active: str = Form(None), files: List[UploadFile] = File(None),
                           csrf_token: Optional[str] = Form(None), db: Session = Depends(get_db), user=Depends(require_permission("products", level="edit"))):
    csrf_check(request, csrf_token)
    price_rial = int(price) * 10 if price.strip().isdigit() else 0
    package_service.update(db, item_id, name, price=price_rial, is_active=(is_active == "on"), files=files)
    db.commit()
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/admin/packages/delete/{item_id}")
async def delete_package(request: Request, item_id: int, csrf_token: Optional[str] = Form(None),
                           db: Session = Depends(get_db), user=Depends(require_permission("products", level="full"))):
    csrf_check(request, csrf_token)
    package_service.delete(db, item_id)
    db.commit()
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/admin/packages/image/delete/{img_id}")
async def delete_package_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                 db: Session = Depends(get_db), user=Depends(require_permission("products", level="edit"))):
    csrf_check(request, csrf_token)
    images.delete_image(db, PackageTypeImage, img_id)
    db.commit()
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/admin/packages/image/default/{img_id}")
async def set_default_package_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                      db: Session = Depends(get_db), user=Depends(require_permission("products", level="edit"))):
    csrf_check(request, csrf_token)
    images.set_default(db, PackageTypeImage, img_id, "package_id")
    db.commit()
    return RedirectResponse("/admin/packages", status_code=303)


# ==========================================
# 🎁 Gift Boxes (جعبه کادو)
# ==========================================

@router.get("/admin/gift-boxes", response_class=HTMLResponse)
async def list_gift_boxes(request: Request, db: Session = Depends(get_db), user=Depends(require_permission("products"))):
    items = gift_box_service.list_all(db)
    data, csrf = ctx(request, user, gift_boxes=items)
    response = templates.TemplateResponse("admin/catalog/gift_boxes.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/gift-boxes/add")
async def add_gift_box(request: Request, name: str = Form(...), price: str = Form("0"),
                       description: str = Form(""), sort_order: str = Form("0"),
                       is_active: str = Form("on"), files: List[UploadFile] = File(None),
                       csrf_token: Optional[str] = Form(None), db: Session = Depends(get_db),
                       user=Depends(require_permission("products", level="create"))):
    csrf_check(request, csrf_token)
    price_rial = int(price) * 10 if price.strip().isdigit() else 0
    so = int(sort_order) if sort_order.strip().isdigit() else 0
    gift_box_service.create(db, name, description=description or None, price=price_rial,
                            is_active=(is_active == "on"), sort_order=so, files=files)
    db.commit()
    return RedirectResponse("/admin/gift-boxes", status_code=303)


@router.post("/admin/gift-boxes/update/{item_id}")
async def update_gift_box(request: Request, item_id: int, name: str = Form(...), price: str = Form("0"),
                          description: str = Form(""), sort_order: str = Form("0"),
                          is_active: str = Form(None), files: List[UploadFile] = File(None),
                          csrf_token: Optional[str] = Form(None), db: Session = Depends(get_db),
                          user=Depends(require_permission("products", level="edit"))):
    csrf_check(request, csrf_token)
    price_rial = int(price) * 10 if price.strip().isdigit() else 0
    so = int(sort_order) if sort_order.strip().isdigit() else 0
    gift_box_service.update(db, item_id, name, description=description or None, price=price_rial,
                            is_active=(is_active == "on"), sort_order=so, files=files)
    db.commit()
    return RedirectResponse("/admin/gift-boxes", status_code=303)


@router.post("/admin/gift-boxes/delete/{item_id}")
async def delete_gift_box(request: Request, item_id: int, csrf_token: Optional[str] = Form(None),
                          db: Session = Depends(get_db), user=Depends(require_permission("products", level="full"))):
    csrf_check(request, csrf_token)
    gift_box_service.delete(db, item_id)
    db.commit()
    return RedirectResponse("/admin/gift-boxes", status_code=303)


@router.post("/admin/gift-boxes/image/delete/{img_id}")
async def delete_gift_box_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                db: Session = Depends(get_db), user=Depends(require_permission("products", level="edit"))):
    csrf_check(request, csrf_token)
    images.delete_image(db, GiftBoxImage, img_id)
    db.commit()
    return RedirectResponse("/admin/gift-boxes", status_code=303)


@router.post("/admin/gift-boxes/image/default/{img_id}")
async def set_default_gift_box_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                     db: Session = Depends(get_db), user=Depends(require_permission("products", level="edit"))):
    csrf_check(request, csrf_token)
    images.set_default(db, GiftBoxImage, img_id, "gift_box_id")
    db.commit()
    return RedirectResponse("/admin/gift-boxes", status_code=303)


# ==========================================
# 🔥 Batches
# ==========================================

@router.get("/admin/batches", response_class=HTMLResponse)
async def list_batches(request: Request, db: Session = Depends(get_db), user=Depends(require_permission("batches"))):
    items = batch_service.list_all(db)
    data, csrf = ctx(request, user, batches=items)
    response = templates.TemplateResponse("admin/catalog/batches.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/batches/add")
async def add_batch(
    request: Request, batch_number: str = Form(...), melt_number: str = Form(None),
    operator: str = Form(None), purity: str = Form(None),
    files: List[UploadFile] = File(None), csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_permission("batches", level="create")),
):
    csrf_check(request, csrf_token)
    try:
        batch_service.create(db, {
            "batch_number": batch_number, "melt_number": melt_number,
            "operator": operator, "purity": purity,
        }, files)
        db.commit()
    except IntegrityError:
        db.rollback()
        flash(request, "شماره بچ تکراری است. لطفاً شماره متفاوتی وارد کنید.", "danger")
    return RedirectResponse("/admin/batches", status_code=303)


@router.get("/admin/batches/edit/{batch_id}", response_class=HTMLResponse)
async def edit_batch_form(request: Request, batch_id: int, db: Session = Depends(get_db), user=Depends(require_permission("batches"))):
    batch = batch_service.get_by_id(db, batch_id)
    if not batch:
        raise HTTPException(404)
    data, csrf = ctx(request, user, batch=batch)
    response = templates.TemplateResponse("admin/catalog/edit_batch.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/batches/update/{batch_id}")
async def update_batch(
    request: Request, batch_id: int,
    batch_number: str = Form(...), melt_number: str = Form(None),
    operator: str = Form(None), purity: str = Form(None),
    new_files: List[UploadFile] = File(None), csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_permission("batches", level="edit")),
):
    csrf_check(request, csrf_token)
    batch_service.update(db, batch_id, {
        "batch_number": batch_number, "melt_number": melt_number,
        "operator": operator, "purity": purity,
    }, new_files)
    db.commit()
    return RedirectResponse(f"/admin/batches/edit/{batch_id}", status_code=303)


@router.post("/admin/batches/delete/{item_id}")
async def delete_batch(request: Request, item_id: int, csrf_token: Optional[str] = Form(None),
                         db: Session = Depends(get_db), user=Depends(require_permission("batches", level="full"))):
    csrf_check(request, csrf_token)
    batch_service.delete(db, item_id)
    db.commit()
    return RedirectResponse("/admin/batches", status_code=303)


@router.post("/admin/batches/image/delete/{img_id}")
async def delete_batch_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                               db: Session = Depends(get_db), user=Depends(require_permission("batches", level="edit"))):
    csrf_check(request, csrf_token)
    bid = images.delete_image(db, BatchImage, img_id)
    db.commit()
    return RedirectResponse(f"/admin/batches/edit/{bid}" if bid else "/admin/batches", status_code=303)


@router.post("/admin/batches/image/default/{img_id}")
async def set_batch_default_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                    db: Session = Depends(get_db), user=Depends(require_permission("batches", level="edit"))):
    csrf_check(request, csrf_token)
    bid = images.set_default(db, BatchImage, img_id, "batch_id")
    db.commit()
    return RedirectResponse(f"/admin/batches/edit/{bid}" if bid else "/admin/batches", status_code=303)


# ==========================================
# 🗂️ Product Categories
# ==========================================

@router.get("/admin/categories", response_class=HTMLResponse)
async def list_categories(request: Request, db: Session = Depends(get_db), user=Depends(require_permission("products"))):
    categories = db.query(ProductCategory).order_by(ProductCategory.sort_order, ProductCategory.id).all()
    data, csrf = ctx(request, user, categories=categories)
    response = templates.TemplateResponse("admin/catalog/categories.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/categories/add")
async def add_category(
    request: Request,
    name: str = Form(...), slug: str = Form(...),
    sort_order: int = Form(0), is_active: bool = Form(True),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_permission("products", level="create")),
):
    csrf_check(request, csrf_token)
    cat = ProductCategory(name=name.strip(), slug=slug.strip().lower(), sort_order=sort_order, is_active=is_active)
    db.add(cat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        flash(request, "نام یا اسلاگ دسته‌بندی تکراری است.", "danger")
    return RedirectResponse("/admin/categories", status_code=303)


@router.post("/admin/categories/edit/{cat_id}")
async def edit_category(
    request: Request, cat_id: int,
    name: str = Form(...), slug: str = Form(...),
    sort_order: int = Form(0), is_active: bool = Form(True),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_permission("products", level="edit")),
):
    csrf_check(request, csrf_token)
    cat = db.query(ProductCategory).filter(ProductCategory.id == cat_id).first()
    if cat:
        cat.name = name.strip()
        cat.slug = slug.strip().lower()
        cat.sort_order = sort_order
        cat.is_active = is_active
        db.commit()
    return RedirectResponse("/admin/categories", status_code=303)


@router.post("/admin/categories/delete/{cat_id}")
async def delete_category(
    request: Request, cat_id: int,
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_permission("products", level="full")),
):
    csrf_check(request, csrf_token)
    cat = db.query(ProductCategory).filter(ProductCategory.id == cat_id).first()
    if cat:
        db.delete(cat)
        db.commit()
    return RedirectResponse("/admin/categories", status_code=303)
