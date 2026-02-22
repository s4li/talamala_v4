"""
Coupon Routes - Customer Facing
==================================
AJAX coupon validation for checkout page.
"""

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from modules.auth.deps import require_login
from modules.coupon.service import coupon_service
from modules.cart.service import cart_service

router = APIRouter(prefix="/api/coupon", tags=["coupon"])


@router.get("/check")
async def check_coupon(
    request: Request,
    code: str = Query(""),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    """AJAX: Validate coupon code against current cart."""
    if not code.strip():
        return JSONResponse({"valid": False, "error": "لطفاً کد تخفیف را وارد کنید"})

    # Get cart totals
    items, total_price = cart_service.get_cart_items_with_pricing(db, me.id)
    if not items:
        return JSONResponse({"valid": False, "error": "سبد خرید خالی است"})

    item_count = sum(it["quantity"] for it in items)
    product_ids = [it["product"].id for it in items]
    category_ids = list({cid for it in items for cid in it["product"].category_ids})

    result = coupon_service.quick_check(
        db, code.strip(), me.id, total_price,
        item_count=item_count,
        product_ids=product_ids,
        category_ids=category_ids,
    )
    return JSONResponse(result)
