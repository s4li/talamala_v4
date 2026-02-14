"""
Shop Module - Routes
======================
Public storefront: product listing and product detail pages.
"""

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token
from modules.auth.deps import get_current_active_user
from modules.shop.service import shop_service
from modules.cart.service import cart_service

router = APIRouter(tags=["shop"])


def _get_cart_info(db: Session, user) -> tuple:
    """Get cart map and count for the current customer (if logged in)."""
    if user and not getattr(user, "is_staff", False):
        return cart_service.get_cart_map(db, user.id)
    return {}, 0


@router.get("/", response_class=HTMLResponse)
async def home_page(
    request: Request,
    sort: str = Query("weight_asc"),
    category: str = Query(""),
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """Shop home page - list all active products with prices."""
    products, gold_price_rial, tax_percent_str = shop_service.list_products_with_pricing(db, sort=sort)

    # Category filter
    from modules.catalog.models import ProductCategory
    categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).order_by(ProductCategory.sort_order).all()
    if category:
        cat_id = int(category) if category.isdigit() else None
        if cat_id:
            products = [p for p in products if p.category_id == cat_id]

    cart_map, cart_count = _get_cart_info(db, user)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/home.html", {
        "request": request,
        "products": products,
        "user": user,
        "gold_price": gold_price_rial,
        "cart_map": cart_map,
        "cart_count": cart_count,
        "current_sort": sort,
        "current_category": category,
        "categories": categories,
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """Product detail page with full price breakdown."""
    result = shop_service.get_product_detail(db, product_id)

    if not result:
        return templates.TemplateResponse("shop/404.html", {
            "request": request, "user": user,
        }, status_code=404)

    product, invoice, inventory, gold_price, tax_percent, location_inventory = result
    cart_map, cart_count = _get_cart_info(db, user)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/product_detail.html", {
        "request": request,
        "p": product,
        "user": user,
        "gold_price": gold_price,
        "invoice": invoice,
        "tax_percent": tax_percent,
        "inventory": inventory,
        "location_inventory": location_inventory,
        "cart_map": cart_map,
        "cart_count": cart_count,
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response
