"""
Cart & Order Routes
=====================
Cart view, item update (form + API), checkout, order list, invoice.
"""

import urllib.parse
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_login, get_current_active_user
from modules.cart.service import cart_service
from modules.order.service import order_service
from modules.pricing.service import is_price_fresh
from modules.pricing.models import GOLD_18K
from modules.pricing.trade_guard import is_trade_enabled, require_trade_enabled
from common.templating import get_setting_from_db

router = APIRouter(tags=["cart"])


# ==========================================
# 🛒 View Cart
# ==========================================

@router.get("/cart", response_class=HTMLResponse)
async def view_cart(
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    items, total_price = cart_service.get_cart_items_with_pricing(db, me.id)

    # Get active gift boxes for selection dropdown
    from modules.catalog.models import GiftBox
    gift_boxes = db.query(GiftBox).filter(GiftBox.is_active == True).order_by(GiftBox.sort_order, GiftBox.id).all()

    shop_gold_enabled = is_trade_enabled(db, "gold", "shop")
    shop_silver_enabled = is_trade_enabled(db, "silver", "shop")
    shop_closed_message = get_setting_from_db(db, "shop_closed_message", "")
    # Check if any item in cart has a disabled metal
    has_disabled_items = any(
        not (shop_gold_enabled if (it["product"].metal_type or "gold") == "gold" else shop_silver_enabled)
        for it in items
    )

    csrf = new_csrf_token(request)
    response = templates.TemplateResponse("shop/cart.html", {
        "request": request,
        "user": me,
        "items": items,
        "total_price": total_price,
        "cart_count": sum(it["quantity"] for it in items),
        "gold_price": cart_service._gold_price(db),
        "price_stale": not is_price_fresh(db, GOLD_18K),
        "shop_disabled": not shop_gold_enabled or not shop_silver_enabled,
        "shop_closed_message": shop_closed_message,
        "shop_gold_enabled": shop_gold_enabled,
        "shop_silver_enabled": shop_silver_enabled,
        "has_disabled_items": has_disabled_items,
        "gift_boxes": gift_boxes,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# ➕➖ Update Cart (Form-based, from shop pages)
# ==========================================

@router.post("/cart/update")
async def update_cart_form(
    request: Request,
    product_id: int = Form(...),
    action: str = Form(...),
    gift_box_id: str = Form(""),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    referer = request.headers.get("referer", "/")

    # Trade guard check (only for add/increase, not remove)
    if action != "remove":
        from modules.catalog.models import Product
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            try:
                require_trade_enabled(db, product.metal_type or "gold", "shop")
            except ValueError as e:
                from common.flash import flash
                flash(request, str(e), "danger")
                return RedirectResponse(referer, status_code=303)

    gb_id = int(gift_box_id) if gift_box_id.strip().isdigit() else None
    if action == "remove":
        cart_service.update_item(db, me.id, product_id, -9999)
    else:
        change = 1 if action == "increase" else -1
        cart_service.update_item(db, me.id, product_id, change, gift_box_id=gb_id)
    db.commit()

    return RedirectResponse(referer, status_code=303)


# ==========================================
# ➕➖ Update Cart (API, for AJAX)
# ==========================================

@router.post("/api/cart/update")
async def api_update_cart(
    data: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_token = request.headers.get("X-CSRF-Token")
    csrf_check(request, csrf_token)

    try:
        product_id = int(data.get("product_id"))
        change = int(data.get("change"))
    except (TypeError, ValueError):
        return JSONResponse({"status": "error", "message": "پارامترهای نامعتبر"}, status_code=400)

    # Trade guard check (only for adding, not removing)
    if change > 0:
        from modules.catalog.models import Product
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            try:
                require_trade_enabled(db, product.metal_type or "gold", "shop")
            except ValueError as e:
                return JSONResponse({"status": "error", "message": str(e)}, status_code=403)

    gb_id = data.get("gift_box_id")
    if gb_id is not None:
        try:
            gb_id = int(gb_id)
        except (TypeError, ValueError):
            gb_id = None

    new_qty, cart_count = cart_service.update_item(db, me.id, product_id, change,
                                                   gift_box_id=gb_id)
    db.commit()
    return JSONResponse({
        "status": "success",
        "new_quantity": new_qty,
        "cart_count": cart_count,
    })


# ==========================================
# 🎁 Set Cart Gift Box (Form-based)
# ==========================================

@router.post("/cart/set-gift-box")
async def set_cart_gift_box(
    request: Request,
    product_id: int = Form(...),
    gift_box_id: str = Form(""),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    gb_id = int(gift_box_id) if gift_box_id.strip().isdigit() else None
    cart_service.set_gift_box(db, me.id, product_id, gb_id)
    db.commit()
    referer = request.headers.get("referer", "/cart")
    return RedirectResponse(referer, status_code=303)


# ==========================================
# ✅ Checkout - Step 1: Delivery Selection Page
# ==========================================

@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(
    request: Request,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    from modules.order.delivery_service import delivery_service
    from common.templating import get_setting_from_db

    # Profile completion check
    if not me.is_profile_complete:
        error = urllib.parse.quote("لطفاً ابتدا پروفایل خود را تکمیل کنید تا بتوانید سفارش ثبت کنید.")
        return RedirectResponse(f"/profile?error={error}&return_to=/cart", status_code=302)

    # Shahkar verification check
    if get_setting_from_db(db, "shahkar_enabled", "false") == "true" and not me.shahkar_verified:
        error = urllib.parse.quote("لطفاً ابتدا احراز هویت شاهکار را از صفحه پروفایل انجام دهید.")
        return RedirectResponse(f"/profile?error={error}&return_to=/cart", status_code=302)

    items, total_price = cart_service.get_cart_items_with_pricing(db, me.id)
    if not items:
        return RedirectResponse("/cart", status_code=302)

    product_ids = [it["product"].id for it in items]

    # Get provinces with available branches
    provinces = delivery_service.get_provinces_with_branches(db)

    # Postal availability
    postal_info = delivery_service.calculate_shipping(db, total_price)
    postal_hub = delivery_service.get_postal_hub(db)
    postal_stock = delivery_service.get_postal_hub_stock(db, product_ids) if postal_hub else 0

    # Customer saved addresses (for postal delivery)
    from modules.customer.address_models import CustomerAddress
    customer_addresses = db.query(CustomerAddress).filter(
        CustomerAddress.user_id == me.id
    ).order_by(CustomerAddress.is_default.desc(), CustomerAddress.id.desc()).all()

    shop_gold_enabled = is_trade_enabled(db, "gold", "shop")
    shop_silver_enabled = is_trade_enabled(db, "silver", "shop")
    shop_closed_message = get_setting_from_db(db, "shop_closed_message", "")
    has_disabled_items = any(
        not (shop_gold_enabled if (it["product"].metal_type or "gold") == "gold" else shop_silver_enabled)
        for it in items
    )

    csrf = new_csrf_token(request)
    response = templates.TemplateResponse("shop/checkout.html", {
        "request": request,
        "user": me,
        "items": items,
        "total_price": total_price,
        "cart_count": sum(it["quantity"] for it in items),
        "provinces": provinces,
        "postal_info": postal_info,
        "postal_stock": postal_stock,
        "customer_addresses": customer_addresses,
        "gold_price": cart_service._gold_price(db),
        "price_stale": not is_price_fresh(db, GOLD_18K),
        "shop_disabled": not shop_gold_enabled or not shop_silver_enabled,
        "shop_closed_message": shop_closed_message,
        "has_disabled_items": has_disabled_items,
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# 🔍 API: Filter locations by province/city (AJAX)
# ==========================================

@router.get("/api/delivery/locations")
async def api_delivery_locations(
    request: Request,
    province: str = None,
    city: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    from modules.order.delivery_service import delivery_service

    if not province:
        return JSONResponse({"locations": [], "cities": []})

    # Get cities for province
    cities = delivery_service.get_cities_in_province(db, province)

    # Get cart product_ids for stock check
    cart_map, _ = cart_service.get_cart_map(db, me.id)
    product_ids = list(cart_map.keys())

    # Get dealers with stock info
    dealers = delivery_service.get_pickup_dealers(
        db, province=province, city=city, product_ids=product_ids,
    )

    return JSONResponse({
        "cities": cities,
        "locations": dealers,
    })


# ==========================================
# ✅ Checkout - Step 2: Process Order
# ==========================================

@router.post("/cart/checkout")
async def checkout(
    request: Request,
    delivery_method: str = Form(...),
    pickup_dealer_id: str = Form(""),
    shipping_province: str = Form(""),
    shipping_city: str = Form(""),
    shipping_address: str = Form(""),
    shipping_postal_code: str = Form(""),
    coupon_code: str = Form(""),
    is_gift: str = Form("0"),
    commitment: str = Form(None),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    from common.templating import get_setting_from_db

    # Profile completion check
    if not me.is_profile_complete:
        error = urllib.parse.quote("لطفاً ابتدا پروفایل خود را تکمیل کنید.")
        return RedirectResponse(f"/profile?error={error}", status_code=303)

    # Shahkar verification check
    if get_setting_from_db(db, "shahkar_enabled", "false") == "true" and not me.shahkar_verified:
        error = urllib.parse.quote("لطفاً ابتدا احراز هویت شاهکار را از صفحه پروفایل انجام دهید.")
        return RedirectResponse(f"/profile?error={error}", status_code=303)

    # Validate
    pickup_loc_id = int(pickup_dealer_id) if pickup_dealer_id.strip().isdigit() else None
    if delivery_method == "Pickup":
        if not pickup_loc_id:
            error = urllib.parse.quote("لطفاً نمایندگی تحویل را انتخاب کنید.")
            return RedirectResponse(f"/checkout?error={error}", status_code=303)
        # Server-side: verify dealer exists and is active
        from modules.user.models import User
        dlr = db.query(User).filter(User.id == pickup_loc_id, User.is_dealer == True).first()
        if not dlr or not dlr.is_active:
            error = urllib.parse.quote("نمایندگی انتخابی نامعتبر است.")
            return RedirectResponse(f"/checkout?error={error}", status_code=303)
        if not commitment:
            error = urllib.parse.quote("تأیید تعهد تحویل حضوری الزامی است.")
            return RedirectResponse(f"/checkout?error={error}", status_code=303)
    elif delivery_method == "Postal":
        if not shipping_address or not shipping_city:
            error = urllib.parse.quote("آدرس و شهر الزامی است.")
            return RedirectResponse(f"/checkout?error={error}", status_code=303)
    else:
        error = urllib.parse.quote("روش تحویل نامعتبر.")
        return RedirectResponse(f"/checkout?error={error}", status_code=303)

    try:
        order = order_service.checkout(db, me.id, {
            "delivery_method": delivery_method,
            "pickup_dealer_id": pickup_loc_id,
            "shipping_province": shipping_province,
            "shipping_city": shipping_city,
            "shipping_address": shipping_address,
            "shipping_postal_code": shipping_postal_code,
            "coupon_code": coupon_code.strip() if coupon_code else "",
            "is_gift": is_gift == "1",
        })
        db.commit()

        # Get plain delivery code (transient) for display
        plain_code = getattr(order, "_plain_delivery_code", None)

        if delivery_method == "Pickup" and plain_code:
            msg = urllib.parse.quote(
                f"سفارش #{order.id} ثبت شد. کد تحویل: {plain_code}"
            )
        else:
            msg = urllib.parse.quote(f"سفارش #{order.id} ثبت شد. لطفاً پرداخت کنید.")

        return RedirectResponse(f"/orders/{order.id}?msg={msg}", status_code=303)

    except ValueError as e:
        error = urllib.parse.quote(str(e))
        return RedirectResponse(f"/checkout?error={error}", status_code=303)


# ==========================================
# 📋 My Orders
# ==========================================

@router.get("/orders", response_class=HTMLResponse)
async def my_orders(
    request: Request,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    orders = order_service.get_customer_orders(db, me.id)
    cart_map, cart_count = cart_service.get_cart_map(db, me.id)

    csrf = new_csrf_token(request)
    response = templates.TemplateResponse("shop/orders.html", {
        "request": request,
        "user": me,
        "orders": orders,
        "cart_count": cart_count,
        "gold_price": cart_service._gold_price(db),
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# 🧾 Order Detail / Invoice
# ==========================================

@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail(
    request: Request,
    order_id: int,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    order = order_service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(404)

    # Security: customer can only see own orders, staff can see all
    is_staff = getattr(user, "is_staff", False)
    if not is_staff and order.customer_id != user.id:
        raise HTTPException(403)

    cart_map, cart_count = {}, 0
    wallet_balance = None
    if not is_staff:
        cart_map, cart_count = cart_service.get_cart_map(db, user.id)
        # Get wallet balance for payment
        from modules.wallet.service import wallet_service
        wallet_balance = wallet_service.get_balance(db, user.id)

    # Get existing reviews for order items (to show/hide review form)
    from modules.review.service import review_service
    order_item_ids = [item.id for item in order.items]
    item_reviews = review_service.get_reviews_for_order_items(db, order_item_ids)

    # Get enabled gateways for payment selector
    from modules.payment.service import payment_service
    enabled_gateways = payment_service.get_enabled_gateways(db)

    csrf = new_csrf_token(request)
    response = templates.TemplateResponse("shop/order_detail.html", {
        "request": request,
        "user": user,
        "order": order,
        "cart_count": cart_count,
        "gold_price": cart_service._gold_price(db),
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "wallet_balance": wallet_balance,
        "item_reviews": item_reviews,
        "enabled_gateways": enabled_gateways,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# ❌ Cancel Order
# ==========================================

@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    request: Request,
    order_id: int,
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    order = order_service.get_order_by_id(db, order_id)
    if not order or order.customer_id != me.id:
        raise HTTPException(404)

    result = order_service.cancel_order(db, order_id, reason="لغو توسط مشتری", changed_by="customer")
    db.commit()
    if result:
        msg = urllib.parse.quote("سفارش لغو و شمش‌ها آزاد شدند.")
    else:
        msg = urllib.parse.quote("امکان لغو این سفارش وجود ندارد.")
    return RedirectResponse(f"/orders?msg={msg}", status_code=303)
