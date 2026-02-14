"""
Catalog Module - Admin Routes
===============================
CRUD for Products, CardDesigns, PackageTypes, Batches.
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
from modules.auth.deps import require_super_admin, require_operator_or_admin
from modules.catalog.service import (
    product_service, design_service, package_service, batch_service,
    images, ProductImage, CardDesignImage, PackageTypeImage, BatchImage,
)
from modules.catalog.models import ProductCategory, CardDesign, PackageType

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
async def list_products(request: Request, db: Session = Depends(get_db), user=Depends(require_super_admin)):
    products = product_service.list_all(db)
    categories = db.query(ProductCategory).order_by(ProductCategory.sort_order).all()
    designs = db.query(CardDesign).all()
    packages = db.query(PackageType).all()
    data, csrf = ctx(request, user, products=products, categories=categories, designs=designs, packages=packages)
    response = templates.TemplateResponse("admin/catalog/products.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/products/add")
async def add_product(
    request: Request,
    name: str = Form(...), weight: str = Form(...), purity: str = Form("750"),
    category_id: str = Form(""), design: str = Form(None),
    card_design_id: str = Form(""), package_type_id: str = Form(""),
    wage: str = Form("0"), is_wage_percent: bool = Form(False),
    profit_percent: str = Form("7"), commission_percent: str = Form("0"),
    stone_price: str = Form("0"), accessory_cost: str = Form("0"),
    accessory_profit_percent: str = Form("15"), is_active: bool = Form(True),
    files: List[UploadFile] = File(None),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_super_admin),
):
    csrf_check(request, csrf_token)
    cat_id = int(category_id) if category_id.strip().isdigit() else None
    cd_id = int(card_design_id) if card_design_id.strip().isdigit() else None
    pt_id = int(package_type_id) if package_type_id.strip().isdigit() else None
    product_service.create(db, {
        "name": name, "weight": weight, "purity": purity, "design": design,
        "category_id": cat_id, "card_design_id": cd_id, "package_type_id": pt_id,
        "wage": wage, "is_wage_percent": is_wage_percent,
        "profit_percent": profit_percent, "commission_percent": commission_percent,
        "stone_price": stone_price, "accessory_cost": accessory_cost,
        "accessory_profit_percent": accessory_profit_percent, "is_active": is_active,
    }, files)
    return RedirectResponse("/admin/products", status_code=303)


@router.get("/admin/products/edit/{p_id}", response_class=HTMLResponse)
async def edit_product_form(request: Request, p_id: int, db: Session = Depends(get_db), user=Depends(require_super_admin)):
    p = product_service.get_by_id(db, p_id)
    if not p:
        raise HTTPException(404)
    categories = db.query(ProductCategory).order_by(ProductCategory.sort_order).all()
    designs = db.query(CardDesign).all()
    packages = db.query(PackageType).all()
    data, csrf = ctx(request, user, p=p, categories=categories, designs=designs, packages=packages)
    response = templates.TemplateResponse("admin/catalog/edit_product.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/products/update/{p_id}")
async def update_product(
    request: Request, p_id: int,
    name: str = Form(...), weight: str = Form(...), purity: str = Form(...),
    category_id: str = Form(""), design: str = Form(None),
    card_design_id: str = Form(""), package_type_id: str = Form(""),
    wage: str = Form(...), is_wage_percent: bool = Form(False),
    profit_percent: str = Form(...), commission_percent: str = Form(...),
    stone_price: str = Form(...), accessory_cost: str = Form(...),
    accessory_profit_percent: str = Form(...), is_active: bool = Form(False),
    new_files: List[UploadFile] = File(None),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_super_admin),
):
    csrf_check(request, csrf_token)
    cat_id = int(category_id) if category_id.strip().isdigit() else None
    cd_id = int(card_design_id) if card_design_id.strip().isdigit() else None
    pt_id = int(package_type_id) if package_type_id.strip().isdigit() else None
    product_service.update(db, p_id, {
        "name": name, "weight": weight, "purity": purity, "design": design,
        "category_id": cat_id, "card_design_id": cd_id, "package_type_id": pt_id,
        "wage": wage, "is_wage_percent": is_wage_percent,
        "profit_percent": profit_percent, "commission_percent": commission_percent,
        "stone_price": stone_price, "accessory_cost": accessory_cost,
        "accessory_profit_percent": accessory_profit_percent, "is_active": is_active,
    }, new_files)
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/admin/products/delete_image/{img_id}")
async def delete_product_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    pid = images.delete_image(db, ProductImage, img_id)
    return RedirectResponse(f"/admin/products/edit/{pid}" if pid else "/admin/products", status_code=303)


@router.post("/admin/products/set_default/{img_id}")
async def set_product_default(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                               db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    pid = images.set_default(db, ProductImage, img_id, "product_id")
    return RedirectResponse(f"/admin/products/edit/{pid}" if pid else "/admin/products", status_code=303)


# ==========================================
# 🎨 Card Designs
# ==========================================

@router.get("/admin/designs", response_class=HTMLResponse)
async def list_designs(request: Request, db: Session = Depends(get_db), user=Depends(require_super_admin)):
    items = design_service.list_all(db)
    data, csrf = ctx(request, user, designs=items)
    response = templates.TemplateResponse("admin/catalog/designs.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/designs/add")
async def add_design(request: Request, name: str = Form(...), files: List[UploadFile] = File(None),
                      csrf_token: Optional[str] = Form(None), db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    design_service.create(db, name, files)
    return RedirectResponse("/admin/designs", status_code=303)


@router.post("/admin/designs/update/{item_id}")
async def update_design(request: Request, item_id: int, name: str = Form(...), files: List[UploadFile] = File(None),
                          csrf_token: Optional[str] = Form(None), db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    design_service.update(db, item_id, name, files)
    return RedirectResponse("/admin/designs", status_code=303)


@router.post("/admin/designs/delete/{item_id}")
async def delete_design(request: Request, item_id: int, csrf_token: Optional[str] = Form(None),
                          db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    design_service.delete(db, item_id)
    return RedirectResponse("/admin/designs", status_code=303)


@router.post("/admin/designs/image/delete/{img_id}")
async def delete_design_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    images.delete_image(db, CardDesignImage, img_id)
    return RedirectResponse("/admin/designs", status_code=303)


@router.post("/admin/designs/image/default/{img_id}")
async def set_default_design_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                     db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    images.set_default(db, CardDesignImage, img_id, "design_id")
    return RedirectResponse("/admin/designs", status_code=303)


# ==========================================
# 📦 Package Types
# ==========================================

@router.get("/admin/packages", response_class=HTMLResponse)
async def list_packages(request: Request, db: Session = Depends(get_db), user=Depends(require_super_admin)):
    items = package_service.list_all(db)
    data, csrf = ctx(request, user, packages=items)
    response = templates.TemplateResponse("admin/catalog/packages.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/packages/add")
async def add_package(request: Request, name: str = Form(...), files: List[UploadFile] = File(None),
                       csrf_token: Optional[str] = Form(None), db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    package_service.create(db, name, files)
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/admin/packages/update/{item_id}")
async def update_package(request: Request, item_id: int, name: str = Form(...), files: List[UploadFile] = File(None),
                           csrf_token: Optional[str] = Form(None), db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    package_service.update(db, item_id, name, files)
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/admin/packages/delete/{item_id}")
async def delete_package(request: Request, item_id: int, csrf_token: Optional[str] = Form(None),
                           db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    package_service.delete(db, item_id)
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/admin/packages/image/delete/{img_id}")
async def delete_package_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                 db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    images.delete_image(db, PackageTypeImage, img_id)
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/admin/packages/image/default/{img_id}")
async def set_default_package_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                      db: Session = Depends(get_db), user=Depends(require_super_admin)):
    csrf_check(request, csrf_token)
    images.set_default(db, PackageTypeImage, img_id, "package_id")
    return RedirectResponse("/admin/packages", status_code=303)


# ==========================================
# 🔥 Batches
# ==========================================

@router.get("/admin/batches", response_class=HTMLResponse)
async def list_batches(request: Request, db: Session = Depends(get_db), user=Depends(require_operator_or_admin)):
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
    db: Session = Depends(get_db), user=Depends(require_operator_or_admin),
):
    csrf_check(request, csrf_token)
    try:
        batch_service.create(db, {
            "batch_number": batch_number, "melt_number": melt_number,
            "operator": operator, "purity": purity,
        }, files)
    except IntegrityError:
        db.rollback()
    return RedirectResponse("/admin/batches", status_code=303)


@router.get("/admin/batches/edit/{batch_id}", response_class=HTMLResponse)
async def edit_batch_form(request: Request, batch_id: int, db: Session = Depends(get_db), user=Depends(require_operator_or_admin)):
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
    db: Session = Depends(get_db), user=Depends(require_operator_or_admin),
):
    csrf_check(request, csrf_token)
    batch_service.update(db, batch_id, {
        "batch_number": batch_number, "melt_number": melt_number,
        "operator": operator, "purity": purity,
    }, new_files)
    return RedirectResponse(f"/admin/batches/edit/{batch_id}", status_code=303)


@router.post("/admin/batches/delete/{item_id}")
async def delete_batch(request: Request, item_id: int, csrf_token: Optional[str] = Form(None),
                         db: Session = Depends(get_db), user=Depends(require_operator_or_admin)):
    csrf_check(request, csrf_token)
    batch_service.delete(db, item_id)
    return RedirectResponse("/admin/batches", status_code=303)


@router.post("/admin/batches/image/delete/{img_id}")
async def delete_batch_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                               db: Session = Depends(get_db), user=Depends(require_operator_or_admin)):
    csrf_check(request, csrf_token)
    bid = images.delete_image(db, BatchImage, img_id)
    return RedirectResponse(f"/admin/batches/edit/{bid}" if bid else "/admin/batches", status_code=303)


@router.post("/admin/batches/image/default/{img_id}")
async def set_batch_default_image(request: Request, img_id: int, csrf_token: Optional[str] = Form(None),
                                    db: Session = Depends(get_db), user=Depends(require_operator_or_admin)):
    csrf_check(request, csrf_token)
    bid = images.set_default(db, BatchImage, img_id, "batch_id")
    return RedirectResponse(f"/admin/batches/edit/{bid}" if bid else "/admin/batches", status_code=303)


# ==========================================
# 🗂️ Product Categories
# ==========================================

@router.get("/admin/categories", response_class=HTMLResponse)
async def list_categories(request: Request, db: Session = Depends(get_db), user=Depends(require_super_admin)):
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
    db: Session = Depends(get_db), user=Depends(require_super_admin),
):
    csrf_check(request, csrf_token)
    cat = ProductCategory(name=name.strip(), slug=slug.strip().lower(), sort_order=sort_order, is_active=is_active)
    db.add(cat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return RedirectResponse("/admin/categories", status_code=303)


@router.post("/admin/categories/edit/{cat_id}")
async def edit_category(
    request: Request, cat_id: int,
    name: str = Form(...), slug: str = Form(...),
    sort_order: int = Form(0), is_active: bool = Form(True),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db), user=Depends(require_super_admin),
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
    db: Session = Depends(get_db), user=Depends(require_super_admin),
):
    csrf_check(request, csrf_token)
    cat = db.query(ProductCategory).filter(ProductCategory.id == cat_id).first()
    if cat:
        db.delete(cat)
        db.commit()
    return RedirectResponse("/admin/categories", status_code=303)
