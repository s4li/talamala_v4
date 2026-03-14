"""
Order Module - Service Layer
===============================
Checkout, order creation, inventory reservation, expiration cleanup.
"""

import logging
from decimal import Decimal
from datetime import timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from common.helpers import now_utc, generate_unique_claim_code
from common.templating import get_setting_from_db
from modules.order.models import Order, OrderItem, OrderStatus, OrderStatusLog, DeliveryMethod, DeliveryStatus
from modules.cart.models import Cart, CartItem
from modules.catalog.models import Product
from modules.inventory.models import Bar, BarStatus, OwnershipHistory
from modules.pricing.calculator import calculate_bar_price, calculate_gold_cost
from modules.pricing.service import get_end_customer_wage, get_product_pricing

logger = logging.getLogger("talamala.order")


def build_order_item(product, bar, invoice: dict, metal_price_rial: int, tax_percent_str: str,
                     gift_box_id: int = None, gift_box_price: int = 0) -> OrderItem:
    """Create an OrderItem with full price snapshot (including gift box)."""
    audit = invoice.get("audit", {})
    metal_total = int(invoice.get("total", 0))
    return OrderItem(
        product_id=product.id,
        bar_id=bar.id,
        applied_metal_price=int(metal_price_rial),
        applied_unit_price=int(audit.get("unit_price_used", 0)),
        applied_weight=audit.get("weight_used") or product.weight,
        applied_purity=product.purity,
        applied_wage_percent=product.wage,
        applied_tax_percent=tax_percent_str,
        final_gold_amount=int(invoice.get("raw_gold", 0)),
        final_wage_amount=int(invoice.get("wage", 0)),
        final_tax_amount=int(invoice.get("tax", 0)),
        gift_box_id=gift_box_id,
        applied_gift_box_price=gift_box_price,
        line_total=metal_total + gift_box_price,
    )


class OrderService:

    # ==========================================
    # Status Change Logging
    # ==========================================

    def log_status_change(
        self, db: Session, order_id: int, field: str,
        old_value: str = None, new_value: str = "",
        changed_by: str = None, description: str = None,
    ):
        """Record a status or delivery_status change in the audit log."""
        log = OrderStatusLog(
            order_id=order_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            description=description,
        )
        db.add(log)

    # ==========================================
    # Checkout
    # ==========================================

    def checkout(self, db: Session, customer_id: int, delivery_data: dict = None) -> Order:
        """
        Create an order from the customer's cart:
        1. Calculate prices at current gold rate
        2. Reserve bars (SELECT FOR UPDATE, skip_locked)
        3. Build order items with full price snapshot
        4. Set delivery info
        5. Clear cart
        6. Return Pending order (payment handled separately)

        If the user is a dealer, their tier wage is used instead of end-customer wage.

        delivery_data keys:
            delivery_method: "Pickup" or "Postal"
            pickup_dealer_id: int (for Pickup)
            shipping_province, shipping_city, shipping_address,
            shipping_postal_code: str (for Postal)

        Raises ValueError if insufficient inventory.
        """
        from modules.order.delivery_service import generate_delivery_code, delivery_service
        from modules.user.models import User

        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if not cart or not cart.items:
            raise ValueError("سبد خرید خالی است")

        # Detect dealer for tier wage pricing
        user = db.query(User).filter(User.id == customer_id).first()
        is_dealer = user and user.is_dealer
        dealer_wage_map = {}
        if is_dealer and user.tier_id:
            from modules.catalog.models import ProductTierWage
            pids = [it.product_id for it in cart.items]
            tier_wages = db.query(ProductTierWage).filter(
                ProductTierWage.product_id.in_(pids),
                ProductTierWage.tier_id == user.tier_id,
            ).all()
            dealer_wage_map = {tw.product_id: float(tw.wage_percent) for tw in tier_wages}

        tax_percent_str = self._tax_percent(db)
        reservation_minutes = int(get_setting_from_db(db, "reservation_minutes", "15"))

        # Staleness + trade toggle guard: check ALL unique metals in cart
        from modules.pricing.service import require_fresh_price
        from modules.pricing.trade_guard import require_trade_enabled
        checked_metals = set()
        for item in cart.items:
            _, _, m_info = get_product_pricing(db, item.product)
            pc = m_info["pricing_code"]
            mt = item.product.metal_type or "gold"
            if pc not in checked_metals:
                require_fresh_price(db, pc)
                require_trade_enabled(db, mt, "shop")
                checked_metals.add(pc)

        delivery_data = delivery_data or {}
        delivery_method = delivery_data.get("delivery_method")

        # Create order (Pending)
        new_order = Order(
            customer_id=customer_id,
            total_amount=0,
            status=OrderStatus.PENDING,
            delivery_method=delivery_method,
            delivery_status=DeliveryStatus.WAITING,
            is_gift=bool(delivery_data.get("is_gift", False)),
        )

        # Delivery: Pickup
        if delivery_method == DeliveryMethod.PICKUP:
            pickup_loc_id = delivery_data.get("pickup_dealer_id")
            if not pickup_loc_id:
                raise ValueError("لطفاً نمایندگی تحویل را انتخاب کنید")
            new_order.pickup_dealer_id = int(pickup_loc_id)
            # Generate delivery code
            plain_code, hashed_code = generate_delivery_code()
            new_order.delivery_code_hash = hashed_code
            new_order._plain_delivery_code = plain_code  # Transient, for SMS

        # Delivery: Postal
        elif delivery_method == DeliveryMethod.POSTAL:
            new_order.shipping_province = delivery_data.get("shipping_province", "")
            new_order.shipping_city = delivery_data.get("shipping_city", "")
            new_order.shipping_address = delivery_data.get("shipping_address", "")
            new_order.shipping_postal_code = delivery_data.get("shipping_postal_code", "")

        db.add(new_order)
        db.flush()  # get order.id

        self.log_status_change(
            db, new_order.id, "status",
            old_value=None, new_value=OrderStatus.PENDING,
            changed_by="system", description="ثبت سفارش جدید",
        )

        order_items = []
        cart_raw_total = 0
        expire_at = now_utc() + timedelta(minutes=reservation_minutes)

        for item in cart.items:
            # Per-product metal pricing
            p_price, p_bp, _ = get_product_pricing(db, item.product)

            # Use dealer tier wage if available, otherwise end-customer wage
            if is_dealer and user.tier_id:
                wage = dealer_wage_map.get(item.product_id, float(item.product.wage))
            else:
                wage = get_end_customer_wage(db, item.product)

            price_info = calculate_bar_price(
                weight=item.product.weight,
                purity=item.product.purity,
                wage_percent=wage,
                base_metal_price=p_price,
                tax_percent=Decimal(tax_percent_str) if tax_percent_str else 0,
                base_purity=p_bp,
            )

            # Gift box price snapshot
            gb_id = item.gift_box_id
            gb_price = 0
            if gb_id and item.gift_box:
                gb_price = int(item.gift_box.price or 0)

            required_qty = item.quantity

            # Lock and reserve bars - filter by location for delivery method
            bar_filter = db.query(Bar).filter(
                Bar.product_id == item.product_id,
                Bar.status == BarStatus.ASSIGNED,
                Bar.customer_id.is_(None),
                Bar.reserved_customer_id.is_(None),
            )

            # Dealer-aware reservation (with central warehouse fallback)
            cw_ids = delivery_service.get_central_warehouse_ids(db)

            if delivery_method == DeliveryMethod.PICKUP and new_order.pickup_dealer_id:
                # Pickup: dealer's own stock + central warehouse preorder
                allowed_ids = [new_order.pickup_dealer_id] + cw_ids
                bar_filter = bar_filter.filter(Bar.dealer_id.in_(allowed_ids))
            elif delivery_method == DeliveryMethod.POSTAL:
                postal_hub = delivery_service.get_postal_hub(db)
                if not postal_hub:
                    db.rollback()
                    raise ValueError("انبار ارسال پستی تنظیم نشده است. لطفاً با پشتیبانی تماس بگیرید.")
                # Postal: postal hub stock + central warehouse preorder
                allowed_ids = [postal_hub.id] + cw_ids
                bar_filter = bar_filter.filter(Bar.dealer_id.in_(allowed_ids))

            available_bars = (
                bar_filter
                .order_by(Bar.is_preorder.asc())  # Real bars first, preorder as fallback
                .with_for_update(skip_locked=True)
                .limit(required_qty)
                .all()
            )

            if len(available_bars) < required_qty:
                # Build helpful error message
                location_name = ""
                if delivery_method == DeliveryMethod.PICKUP and new_order.pickup_dealer_id:
                    dlr = db.query(User).filter(User.id == new_order.pickup_dealer_id).first()
                    location_name = f" در {dlr.full_name}" if dlr else ""
                elif delivery_method == DeliveryMethod.POSTAL:
                    location_name = " در انبار ارسال پستی"
                db.rollback()
                raise ValueError(f"موجودی «{item.product.name}»{location_name} کافی نیست (نیاز: {required_qty}, موجود: {len(available_bars)})")

            for bar in available_bars:
                bar.status = BarStatus.RESERVED
                bar.reserved_customer_id = customer_id
                bar.reserved_until = expire_at

                oi = build_order_item(item.product, bar, price_info, p_price, tax_percent_str,
                                     gift_box_id=gb_id, gift_box_price=gb_price)
                oi.order_id = new_order.id
                # Store dealer wage on OrderItem if applicable
                if is_dealer:
                    oi.applied_dealer_wage_percent = wage
                order_items.append(oi)
                cart_raw_total += int(price_info.get("total", 0)) + gb_price

        new_order.total_amount = cart_raw_total

        # Add shipping + insurance for postal delivery
        if delivery_method == DeliveryMethod.POSTAL:
            shipping_info = delivery_service.calculate_shipping(db, cart_raw_total)
            if not shipping_info["is_available"]:
                db.rollback()
                raise ValueError(shipping_info["unavailable_reason"])
            new_order.shipping_cost = shipping_info["shipping_cost"]
            new_order.insurance_cost = shipping_info["insurance_cost"]

        # Add all order items
        for oi in order_items:
            db.add(oi)

        # ==========================================
        # Apply coupon (if provided)
        # ==========================================
        coupon_code = delivery_data.get("coupon_code", "").strip()
        if coupon_code:
            try:
                from modules.coupon.service import coupon_service, CouponValidationError
                product_ids_list = [oi.product_id for oi in order_items]
                category_ids_list = list({cid for item in cart.items for cid in item.product.category_ids})

                coupon_result = coupon_service.apply_to_order(
                    db,
                    coupon_code=coupon_code,
                    customer_id=customer_id,
                    order_id=new_order.id,
                    order_amount=cart_raw_total,
                    item_count=len(order_items),
                    product_ids=product_ids_list,
                    category_ids=category_ids_list,
                )

                new_order.coupon_code = coupon_result["code"]
                if coupon_result["is_cashback"]:
                    new_order.promo_choice = "CASHBACK"
                    new_order.promo_amount = coupon_result["discount_amount"]
                    new_order.cashback_settled = False
                else:
                    new_order.promo_choice = "DISCOUNT"
                    new_order.promo_amount = coupon_result["discount_amount"]
            except CouponValidationError:
                pass  # Skip invalid coupon at checkout
            except Exception as e:
                logger.warning(f"Coupon apply error for order #{new_order.id}: {e}")

        # Clear cart
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

        db.flush()
        return new_order

    # ==========================================
    # Dealer Gold-for-Gold Checkout
    # ==========================================

    def checkout_dealer(self, db: Session, dealer_id: int,
                        delivery_data: dict = None) -> Order:
        """
        Gold-for-Gold checkout for dealers:
        1. Calculate gold cost using dealer's tier wage (no tax)
        2. Reserve bars based on delivery method (warehouse default, or pickup/postal)
        3. Apply coupon (CASHBACK only — DISCOUNT ignored for gold orders)
        4. Auto-pay from XAU_MG wallet (supports negative balance via credit_limit)
        5. Finalize order immediately

        delivery_data keys:
            delivery_method: "Pickup" or "Postal" (default: Pickup from warehouse)
            pickup_dealer_id: int (default: first warehouse dealer)
            shipping_province/city/address/postal_code: str (for Postal)
            coupon_code: str (optional)
            is_gift: bool (optional)
        """
        from modules.catalog.models import ProductTierWage
        from modules.wallet.service import wallet_service
        from modules.wallet.models import AssetCode
        from modules.user.models import User
        from modules.order.delivery_service import generate_delivery_code, delivery_service

        dealer = db.query(User).filter(User.id == dealer_id).first()
        if not dealer or not dealer.is_dealer:
            raise ValueError("فقط نمایندگان مجاز به خرید طلایی هستند")

        cart = db.query(Cart).filter(Cart.customer_id == dealer_id).first()
        if not cart or not cart.items:
            raise ValueError("سبد خرید خالی است")

        # Staleness + trade toggle guard
        from modules.pricing.service import require_fresh_price
        from modules.pricing.trade_guard import require_trade_enabled
        checked_metals = set()
        for item in cart.items:
            _, _, m_info = get_product_pricing(db, item.product)
            pc = m_info["pricing_code"]
            mt = item.product.metal_type or "gold"
            if pc not in checked_metals:
                require_fresh_price(db, pc)
                require_trade_enabled(db, mt, "shop")
                checked_metals.add(pc)

        reservation_minutes = int(get_setting_from_db(db, "reservation_minutes", "15"))
        expire_at = now_utc() + timedelta(minutes=reservation_minutes)

        delivery_data = delivery_data or {}
        delivery_method = delivery_data.get("delivery_method", DeliveryMethod.PICKUP)

        # Warehouse IDs (central source for dealer orders)
        warehouse_ids = [
            u.id for u in db.query(User).filter(
                User.is_dealer == True, User.is_warehouse == True, User.is_active == True
            ).all()
        ]
        if not warehouse_ids:
            raise ValueError("انبار مرکزی تعریف نشده است")

        # Create order
        new_order = Order(
            customer_id=dealer_id,
            total_amount=0,
            status=OrderStatus.PENDING,
            delivery_method=delivery_method,
            delivery_status=DeliveryStatus.WAITING,
            payment_asset_code="XAU_MG",
            is_gift=bool(delivery_data.get("is_gift", False)),
        )

        # Delivery: Pickup
        if delivery_method == DeliveryMethod.PICKUP:
            pickup_loc_id = delivery_data.get("pickup_dealer_id")
            if not pickup_loc_id:
                # Default: first warehouse dealer
                pickup_loc_id = warehouse_ids[0]
            new_order.pickup_dealer_id = int(pickup_loc_id)
            plain_code, hashed_code = generate_delivery_code()
            new_order.delivery_code_hash = hashed_code
            new_order._plain_delivery_code = plain_code

        # Delivery: Postal
        elif delivery_method == DeliveryMethod.POSTAL:
            new_order.shipping_province = delivery_data.get("shipping_province", "")
            new_order.shipping_city = delivery_data.get("shipping_city", "")
            new_order.shipping_address = delivery_data.get("shipping_address", "")
            new_order.shipping_postal_code = delivery_data.get("shipping_postal_code", "")

        db.add(new_order)
        db.flush()

        self.log_status_change(
            db, new_order.id, "status",
            old_value=None, new_value=OrderStatus.PENDING,
            changed_by="system", description="ثبت سفارش طلایی نماینده",
        )

        # Batch dealer tier wages
        dealer_wage_map = {}
        if dealer.tier_id:
            pids = [it.product_id for it in cart.items]
            tier_wages = db.query(ProductTierWage).filter(
                ProductTierWage.product_id.in_(pids),
                ProductTierWage.tier_id == dealer.tier_id,
            ).all()
            dealer_wage_map = {tw.product_id: float(tw.wage_percent) for tw in tier_wages}

        order_items = []
        total_gold_mg = 0

        for item in cart.items:
            dealer_wage = dealer_wage_map.get(item.product_id, float(item.product.wage))

            # Gold cost calculation
            gold_info = calculate_gold_cost(
                weight=item.product.weight,
                purity=item.product.purity,
                wage_percent=dealer_wage,
            )
            if gold_info.get("error"):
                raise ValueError(f"خطا در محاسبه قیمت {item.product.name}: {gold_info['error']}")

            unit_gold_mg = gold_info["total_mg"]

            # Rial price for reference (stored in total_amount for backward compat)
            p_price, p_bp, _ = get_product_pricing(db, item.product)
            rial_info = calculate_bar_price(
                weight=item.product.weight, purity=item.product.purity,
                wage_percent=dealer_wage, base_metal_price=p_price,
                tax_percent=0, base_purity=p_bp,
            )

            required_qty = item.quantity

            # Reserve bars based on delivery method
            bar_filter = db.query(Bar).filter(
                Bar.product_id == item.product_id,
                Bar.status == BarStatus.ASSIGNED,
                Bar.customer_id.is_(None),
                Bar.reserved_customer_id.is_(None),
            )

            cw_ids = delivery_service.get_central_warehouse_ids(db)

            if delivery_method == DeliveryMethod.PICKUP and new_order.pickup_dealer_id:
                allowed_ids = [new_order.pickup_dealer_id] + cw_ids
                bar_filter = bar_filter.filter(Bar.dealer_id.in_(allowed_ids))
            elif delivery_method == DeliveryMethod.POSTAL:
                postal_hub = delivery_service.get_postal_hub(db)
                if not postal_hub:
                    db.rollback()
                    raise ValueError("انبار ارسال پستی تنظیم نشده است.")
                allowed_ids = [postal_hub.id] + cw_ids
                bar_filter = bar_filter.filter(Bar.dealer_id.in_(allowed_ids))
            else:
                # Default: warehouse only
                bar_filter = bar_filter.filter(Bar.dealer_id.in_(warehouse_ids))

            available_bars = (
                bar_filter
                .order_by(Bar.is_preorder.asc())
                .with_for_update(skip_locked=True)
                .limit(required_qty)
                .all()
            )

            if len(available_bars) < required_qty:
                db.rollback()
                raise ValueError(
                    f"موجودی «{item.product.name}» کافی نیست "
                    f"(نیاز: {required_qty}, موجود: {len(available_bars)})"
                )

            for bar in available_bars:
                bar.status = BarStatus.RESERVED
                bar.reserved_customer_id = dealer_id
                bar.reserved_until = expire_at

                oi = OrderItem(
                    order_id=new_order.id,
                    product_id=item.product_id,
                    bar_id=bar.id,
                    applied_metal_price=int(p_price),
                    applied_unit_price=int(rial_info.get("audit", {}).get("unit_price_used", 0)),
                    applied_weight=item.product.weight,
                    applied_purity=item.product.purity,
                    applied_wage_percent=item.product.wage,  # end-customer wage (reference)
                    applied_tax_percent=0,
                    final_gold_amount=int(rial_info.get("raw_gold", 0)),
                    final_wage_amount=int(rial_info.get("wage", 0)),
                    final_tax_amount=0,
                    line_total=int(rial_info.get("total", 0)),
                    gold_cost_mg=unit_gold_mg,
                    applied_dealer_wage_percent=dealer_wage,
                )
                order_items.append(oi)
                total_gold_mg += unit_gold_mg

        new_order.total_amount = sum(oi.line_total for oi in order_items)
        new_order.gold_total_mg = total_gold_mg

        for oi in order_items:
            db.add(oi)

        # Shipping costs for postal
        if delivery_method == DeliveryMethod.POSTAL:
            shipping_info = delivery_service.calculate_shipping(db, new_order.total_amount)
            if not shipping_info["is_available"]:
                db.rollback()
                raise ValueError(shipping_info["unavailable_reason"])
            new_order.shipping_cost = shipping_info["shipping_cost"]
            new_order.insurance_cost = shipping_info["insurance_cost"]

        # Apply coupon (CASHBACK only for gold orders — DISCOUNT ignored)
        coupon_code = delivery_data.get("coupon_code", "").strip()
        if coupon_code:
            try:
                from modules.coupon.service import coupon_service, CouponValidationError
                product_ids_list = [oi.product_id for oi in order_items]
                category_ids_list = list({cid for item in cart.items for cid in item.product.category_ids})

                coupon_result = coupon_service.apply_to_order(
                    db,
                    coupon_code=coupon_code,
                    customer_id=dealer_id,
                    order_id=new_order.id,
                    order_amount=new_order.total_amount,
                    item_count=len(order_items),
                    product_ids=product_ids_list,
                    category_ids=category_ids_list,
                )

                # Gold orders: only accept CASHBACK coupons
                if coupon_result["is_cashback"]:
                    new_order.coupon_code = coupon_result["code"]
                    new_order.promo_choice = "CASHBACK"
                    new_order.promo_amount = coupon_result["discount_amount"]
                    new_order.cashback_settled = False
                # DISCOUNT coupons ignored for gold orders (no rial deduction)
            except (CouponValidationError, Exception) as e:
                logger.warning(f"Coupon apply error for gold order #{new_order.id}: {e}")

        # Clear cart
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

        # Auto-pay from XAU_MG wallet
        wallet_service.withdraw(
            db, dealer_id, total_gold_mg,
            reference_type="gold_order", reference_id=str(new_order.id),
            description=f"پرداخت سفارش طلایی #{new_order.id} ({total_gold_mg / 1000:.3f}g)",
            asset_code=AssetCode.XAU_MG,
        )

        # Finalize immediately
        self.finalize_order(db, new_order.id)

        db.flush()
        return new_order

    # ==========================================
    # Finalize (mark as Paid)
    # ==========================================

    def finalize_order(self, db: Session, order_id: int) -> Optional[Order]:
        """
        Mark order as Paid and transfer bar ownership.
        Called after successful payment (wallet or gateway callback).

        Dealer orders always generate claim_code (like gift orders) —
        dealers buy for resale, not for themselves.
        """
        from modules.user.models import User as UserModel

        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order or order.status != OrderStatus.PENDING:
            return None

        # Dealer orders = always claim_code (dealer buys for resale)
        buyer = db.query(UserModel).filter(UserModel.id == order.customer_id).first()
        is_dealer_order = buyer and buyer.is_dealer
        needs_claim_code = order.is_gift or is_dealer_order

        for oi in order.items:
            if oi.bar_id:
                bar = db.query(Bar).filter(Bar.id == oi.bar_id).first()
                if bar:
                    bar.status = BarStatus.SOLD
                    bar.reserved_customer_id = None
                    bar.reserved_until = None

                    if needs_claim_code:
                        # Gift or dealer order: generate claim code, no ownership
                        bar.customer_id = None
                        bar.claim_code = generate_unique_claim_code(db)
                        desc = f"خرید نمایندگی — سفارش #{order.id}" if is_dealer_order else f"خرید هدیه — سفارش #{order.id}"
                        db.add(OwnershipHistory(
                            bar_id=bar.id,
                            previous_owner_id=None,
                            new_owner_id=None,
                            description=desc,
                        ))
                    else:
                        # Self-purchase: assign to buyer
                        bar.customer_id = order.customer_id
                        db.add(OwnershipHistory(
                            bar_id=bar.id,
                            previous_owner_id=None,
                            new_owner_id=order.customer_id,
                            description=f"سفارش #{order.id}",
                        ))

                    # Rasis POS: remove bar from dealer's POS
                    try:
                        from modules.rasis.service import rasis_service
                        if bar.dealer_id:
                            from modules.user.models import User as UserModel
                            dealer = db.query(UserModel).get(bar.dealer_id)
                            if dealer and dealer.rasis_sharepoint:
                                rasis_service.remove_bar_from_pos(db, bar, dealer)
                    except Exception:
                        pass  # Never block order finalization

        order.status = OrderStatus.PAID
        if not order.paid_at:
            order.paid_at = now_utc()
        self.log_status_change(
            db, order.id, "status",
            old_value=OrderStatus.PENDING, new_value=OrderStatus.PAID,
            changed_by="system", description="پرداخت موفق و انتقال مالکیت شمش‌ها",
        )

        # Process referral reward on first purchase (not registration)
        self._process_referral_reward_on_first_purchase(db, order.customer_id)

        # Hedging: record OUT — ONLY for Rial orders (Guardrail 2: gold-for-gold excluded)
        if not order.is_gold_order:
            try:
                from modules.hedging.service import hedging_service
                for oi in order.items:
                    if oi.bar_id and oi.applied_weight:
                        from modules.catalog.models import Product
                        prod = db.query(Product).filter(Product.id == oi.product_id).first()
                        metal = (prod.metal_type if prod else None) or "gold"
                        weight_mg = int(float(oi.applied_weight) * 1000)
                        hedging_service.record_out(
                            db, metal, weight_mg,
                            source_type="order", source_id=str(order.id),
                            description=f"Order #{order.id}",
                            involved_user_id=order.customer_id,
                        )
            except Exception:
                pass  # Never block order finalization

        # Send notification + admin alert
        try:
            from modules.notification.service import notification_service
            from modules.notification.models import NotificationType

            # Build admin alert
            from modules.payment.service import _build_order_admin_alert
            admin_text = _build_order_admin_alert(db, order)

            if order.is_gold_order:
                body = f"سفارش طلایی #{order.id} ثبت و پرداخت شد ({order.gold_total_mg / 1000:.3f}g)"
                sms_text = f"طلاملا: سفارش طلایی #{order.id} پرداخت شد."
            else:
                body = f"سفارش #{order.id} با موفقیت پرداخت شد."
                sms_text = f"طلاملا: سفارش #{order.id} پرداخت شد. talamala.com/orders/{order.id}"

            notification_service.send(
                db, order.customer_id,
                notification_type=NotificationType.PAYMENT_SUCCESS,
                title=f"پرداخت سفارش #{order.id}",
                body=body,
                link=f"/orders/{order.id}",
                sms_text=sms_text,
                reference_type="order_paid", reference_id=str(order.id),
                admin_alert_text=admin_text,
            )
        except Exception:
            pass  # Never block order finalization

        db.flush()
        return order

    def _process_referral_reward_on_first_purchase(self, db: Session, customer_id: int):
        """Credit referrer's wallet when referred customer makes their first purchase."""
        from modules.user.models import User
        from modules.wallet.service import wallet_service

        REFERRAL_REWARD_RIAL = 500_000  # 50,000 toman

        customer = db.query(User).filter(User.id == customer_id).first()
        if not customer or customer.referral_rewarded:
            return
        if not customer.referred_by:
            return

        referrer = db.query(User).filter(User.id == customer.referred_by).first()
        if not referrer:
            return

        try:
            wallet_service.deposit(
                db,
                referrer.id,
                amount=REFERRAL_REWARD_RIAL,
                reference_type="referral",
                reference_id=str(customer.id),
                description=f"پاداش معرفی کاربر جدید ({customer.full_name})",
                idempotency_key=f"referral_reward:{customer.id}",
            )
            customer.referral_rewarded = True
        except Exception as e:
            logger.warning(f"Failed to process referral reward for customer {customer_id}: {e}")

    # ==========================================
    # Cancel
    # ==========================================

    def cancel_order(self, db: Session, order_id: int, reason: str = "", changed_by: str = "system") -> Optional[Order]:
        """Cancel order and release reserved bars."""
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order or order.status != OrderStatus.PENDING:
            return None

        self._release_order_bars(db, order)
        order.status = OrderStatus.CANCELLED
        order.cancellation_reason = reason or None
        order.cancelled_at = now_utc()
        self.log_status_change(
            db, order.id, "status",
            old_value=OrderStatus.PENDING, new_value=OrderStatus.CANCELLED,
            changed_by=changed_by, description=reason or "لغو سفارش",
        )

        try:
            from modules.notification.service import notification_service
            from modules.notification.models import NotificationType
            notification_service.send(
                db, order.customer_id,
                notification_type=NotificationType.ORDER_STATUS,
                title=f"لغو سفارش #{order.id}",
                body=f"سفارش #{order.id} لغو شد. {reason or ''}".strip(),
                link=f"/orders/{order.id}",
                sms_text=f"طلاملا: سفارش #{order.id} لغو شد.",
                reference_type="order_cancel", reference_id=str(order.id),
            )
        except Exception:
            pass

        db.flush()
        return order

    # ==========================================
    # Expiration Cleanup
    # ==========================================

    def release_expired_orders(self, db: Session) -> int:
        """Cancel all expired pending orders and release their bars."""
        now = now_utc()
        reservation_minutes = int(get_setting_from_db(db, "reservation_minutes", "15"))
        limit_time = now - timedelta(minutes=reservation_minutes)

        expired = (
            db.query(Order)
            .filter(
                Order.status == OrderStatus.PENDING,
                Order.created_at < limit_time,
            )
            .all()
        )

        count = 0
        now_ts = now_utc()
        for order in expired:
            self._release_order_bars(db, order)
            reason = f"عدم پرداخت در مهلت مقرر ({reservation_minutes} دقیقه)"
            order.status = OrderStatus.CANCELLED
            order.cancellation_reason = reason
            order.cancelled_at = now_ts
            self.log_status_change(
                db, order.id, "status",
                old_value=OrderStatus.PENDING, new_value=OrderStatus.CANCELLED,
                changed_by="system", description=reason,
            )
            count += 1

        if count:
            db.commit()
            logger.info(f"Released {count} expired orders")

        return count

    # ==========================================
    # Query
    # ==========================================

    def get_customer_orders(self, db: Session, customer_id: int) -> List[Order]:
        return db.query(Order).filter(
            Order.customer_id == customer_id,
        ).order_by(desc(Order.created_at)).all()

    def get_order_by_id(self, db: Session, order_id: int) -> Optional[Order]:
        return db.query(Order).filter(Order.id == order_id).first()

    def _get_metal_type(self, product) -> str:
        """Determine metal type from product.metal_type field."""
        return getattr(product, "metal_type", "gold") or "gold"

    def get_pending_delivery_stats(self, db: Session):
        """Get custodial gold/silver: SOLD bars not yet physically delivered."""
        from sqlalchemy.orm import joinedload
        from modules.user.models import User

        # Bar-based query: SOLD bars with delivered_at IS NULL
        bars = (
            db.query(Bar)
            .options(joinedload(Bar.product), joinedload(Bar.customer))
            .filter(
                Bar.status == BarStatus.SOLD,
                Bar.delivered_at == None,  # noqa: E711 — not physically delivered
            )
            .order_by(desc(Bar.id))
            .all()
        )

        # Get order context for each bar (if any)
        bar_ids = [b.id for b in bars]
        order_map = {}
        buyer_map = {}  # order customer_id → Customer name/mobile
        if bar_ids:
            rows = (
                db.query(OrderItem.bar_id, Order.id, Order.delivery_status, Order.delivery_method, Order.created_at, Order.customer_id)
                .join(Order, OrderItem.order_id == Order.id)
                .filter(OrderItem.bar_id.in_(bar_ids), Order.status == OrderStatus.PAID)
                .all()
            )
            order_map = {r.bar_id: r for r in rows}

            # Fetch original buyer names
            buyer_ids = {r.customer_id for r in rows if r.customer_id}
            if buyer_ids:
                buyers = db.query(User).filter(User.id.in_(buyer_ids)).all()
                buyer_map = {c.id: c for c in buyers}

        gold_weight = Decimal("0")
        silver_weight = Decimal("0")
        gold_bars = []
        silver_bars = []

        for bar in bars:
            product = bar.product
            if not product:
                continue
            weight = Decimal(str(product.weight)) if product.weight else Decimal("0")
            metal = self._get_metal_type(product)

            oi = order_map.get(bar.id)
            # Delivery status label
            if oi and oi.delivery_status:
                ds_label_map = {
                    DeliveryStatus.WAITING: "منتظر مراجعه" if oi.delivery_method == DeliveryMethod.PICKUP else "در حال آماده‌سازی",
                    DeliveryStatus.PREPARING: "در حال بسته‌بندی",
                    DeliveryStatus.SHIPPED: "ارسال شده",
                }
                delivery_label = ds_label_map.get(oi.delivery_status, str(oi.delivery_status))
            else:
                delivery_label = "منتظر مراجعه"

            # Original buyer (from order) vs current owner (from bar)
            buyer = buyer_map.get(oi.customer_id) if oi and oi.customer_id else None
            owner = bar.customer
            transferred = (owner and buyer and owner.id != buyer.id)

            bar_info = {
                "order_id": oi.id if oi else None,
                "buyer_name": buyer.full_name if buyer else "—",
                "buyer_mobile": buyer.mobile if buyer else "",
                "owner_name": owner.full_name if owner else "—",
                "owner_mobile": owner.mobile if owner else "",
                "ownership_transferred": transferred,
                "serial_code": bar.serial_code,
                "product_name": product.name,
                "weight": float(weight),
                "delivery_status": delivery_label,
                "order_date": oi.created_at if oi else bar.created_at,
            }
            if metal == "silver":
                silver_weight += weight
                silver_bars.append(bar_info)
            else:
                gold_weight += weight
                gold_bars.append(bar_info)

        return {
            "gold": {
                "total_weight": float(gold_weight),
                "total_bars": len(gold_bars),
                "total_orders": len({b["order_id"] for b in gold_bars if b["order_id"]}),
                "bars": gold_bars,
            },
            "silver": {
                "total_weight": float(silver_weight),
                "total_bars": len(silver_bars),
                "total_orders": len({b["order_id"] for b in silver_bars if b["order_id"]}),
                "bars": silver_bars,
            },
        }

    def get_all_orders(self, db: Session, status: str = None, delivery: str = None, search: str = None) -> List[Order]:
        q = db.query(Order).order_by(desc(Order.id))
        if status:
            q = q.filter(Order.status == status)
        if delivery:
            q = q.filter(Order.delivery_method == delivery)
        if search:
            from modules.user.models import User
            term = f"%{search.strip()}%"
            q = q.join(Order.customer).filter(
                or_(User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.mobile.ilike(term))
            )
        return q.all()

    # ==========================================
    # Private Helpers
    # ==========================================

    def _release_order_bars(self, db: Session, order: Order):
        """Release all reserved bars for an order."""
        for item in order.items:
            if item.bar_id:
                bar = db.query(Bar).filter(Bar.id == item.bar_id).first()
                if bar and bar.status == BarStatus.RESERVED:
                    bar.status = BarStatus.ASSIGNED
                    bar.reserved_customer_id = None
                    bar.reserved_until = None

    def _gold_price(self, db: Session) -> int:
        from modules.pricing.service import get_price_value
        from modules.pricing.models import GOLD_18K
        return get_price_value(db, GOLD_18K)

    def _tax_percent(self, db: Session) -> str:
        return get_setting_from_db(db, "tax_percent", "9")


# Singleton
order_service = OrderService()
