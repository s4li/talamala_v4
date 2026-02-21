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
from modules.pricing.service import is_price_fresh, get_product_pricing
from modules.pricing.models import GOLD_18K
from modules.pricing.calculator import calculate_bar_price

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
    page: int = Query(1),
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """Shop home page - list all active products with prices."""
    per_page = 12

    # Category list for filter pills
    from modules.catalog.models import ProductCategory
    categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).order_by(ProductCategory.sort_order).all()

    # Default to first category when no category specified
    if not category and categories:
        category = str(categories[0].id)

    # Category filter (DB-level) — "all" means no filter
    cat_id = int(category) if category and category.isdigit() else None

    products, total, gold_price_rial, tax_percent_str = shop_service.list_products_with_pricing(
        db, sort=sort, category_id=cat_id, page=max(1, page), per_page=per_page,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(1, page), total_pages)

    cart_map, cart_count = _get_cart_info(db, user)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/home.html", {
        "request": request,
        "products": products,
        "user": user,
        "gold_price": gold_price_rial,
        "price_stale": not is_price_fresh(db, GOLD_18K),
        "cart_map": cart_map,
        "cart_count": cart_count,
        "current_sort": sort,
        "current_category": category,
        "categories": categories,
        "page": page,
        "total_pages": total_pages,
        "total_products": total,
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

    # Calculate buyback amount using separate buyback_wage_percent
    buyback_amount = 0
    buyback_pct = float(product.buyback_wage_percent or 0)
    if buyback_pct > 0:
        p_price, p_bp, _ = get_product_pricing(db, product)
        bb_info = calculate_bar_price(
            weight=product.weight, purity=product.purity,
            wage_percent=buyback_pct,
            base_metal_price=p_price, tax_percent=0,
            base_purity=p_bp,
        )
        buyback_amount = bb_info.get("wage", 0)

    # Get active packages for selection
    from modules.catalog.models import PackageType
    packages = db.query(PackageType).filter(PackageType.is_active == True).order_by(PackageType.id).all()

    # Reviews & Comments
    from modules.review.service import review_service
    reviews = review_service.get_product_reviews(db, product_id)
    review_stats = review_service.get_product_review_stats(db, product_id)
    product_comments = review_service.get_product_comments(db, product_id)
    has_purchased = False
    customer_id = None
    if user and not getattr(user, "is_staff", False):
        has_purchased = review_service.customer_has_purchased(db, user.id, product_id)
        customer_id = user.id

    # Collect all comment IDs (parents + replies) for like counts
    all_comment_ids = []
    for c in product_comments:
        all_comment_ids.append(c.id)
        for r in (c.replies or []):
            all_comment_ids.append(r.id)
    comment_likes = review_service.get_comment_likes_map(db, all_comment_ids, customer_id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/product_detail.html", {
        "request": request,
        "p": product,
        "user": user,
        "gold_price": gold_price,
        "price_stale": not is_price_fresh(db, GOLD_18K),
        "invoice": invoice,
        "buyback_amount": buyback_amount,
        "tax_percent": tax_percent,
        "inventory": inventory,
        "location_inventory": location_inventory,
        "cart_map": cart_map,
        "cart_count": cart_count,
        "packages": packages,
        "reviews": reviews,
        "review_stats": review_stats,
        "product_comments": product_comments,
        "has_purchased": has_purchased,
        "comment_likes": comment_likes,
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response
