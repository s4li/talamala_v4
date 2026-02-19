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
from modules.order.models import Order, OrderItem, OrderStatus, DeliveryMethod, DeliveryStatus
from modules.cart.models import Cart, CartItem
from modules.catalog.models import Product
from modules.inventory.models import Bar, BarStatus, OwnershipHistory
from modules.pricing.calculator import calculate_bar_price
from modules.pricing.service import get_end_customer_wage

logger = logging.getLogger("talamala.order")


def build_order_item(product, bar, invoice: dict, gold_price_rial: int, tax_percent_str: str,
                     package_type_id: int = None, package_price: int = 0) -> OrderItem:
    """Create an OrderItem with full price snapshot (including package)."""
    audit = invoice.get("audit", {})
    gold_total = int(invoice.get("total", 0))
    return OrderItem(
        product_id=product.id,
        bar_id=bar.id,
        applied_gold_price=int(gold_price_rial),
        applied_unit_price=int(audit.get("unit_price_used", 0)),
        applied_weight=audit.get("weight_used") or product.weight,
        applied_purity=product.purity,
        applied_wage_percent=product.wage,
        applied_tax_percent=tax_percent_str,
        final_gold_amount=int(invoice.get("raw_gold", 0)),
        final_wage_amount=int(invoice.get("wage", 0)),
        final_tax_amount=int(invoice.get("tax", 0)),
        package_type_id=package_type_id,
        applied_package_price=package_price,
        line_total=gold_total + package_price,
    )


class OrderService:

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

        delivery_data keys:
            delivery_method: "Pickup" or "Postal"
            pickup_dealer_id: int (for Pickup)
            shipping_province, shipping_city, shipping_address,
            shipping_postal_code: str (for Postal)

        Raises ValueError if insufficient inventory.
        """
        from modules.order.delivery_service import generate_delivery_code, delivery_service

        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if not cart or not cart.items:
            raise ValueError("سبد خرید خالی است")

        gold_price_rial = self._gold_price(db)
        tax_percent_str = self._tax_percent(db)
        reservation_minutes = int(get_setting_from_db(db, "reservation_minutes", "15"))

        if not gold_price_rial:
            raise ValueError("قیمت طلا تنظیم نشده است")

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

        order_items = []
        cart_raw_total = 0
        expire_at = now_utc() + timedelta(minutes=reservation_minutes)

        for item in cart.items:
            # Calculate price for this product (always use end-customer tier wage)
            ec_wage = get_end_customer_wage(db, item.product)
            price_info = calculate_bar_price(
                weight=item.product.weight,
                purity=item.product.purity,
                wage_percent=ec_wage,
                base_gold_price_18k=gold_price_rial,
                tax_percent=Decimal(tax_percent_str) if tax_percent_str else 0,
            )

            # Package price snapshot
            pkg_type_id = item.package_type_id
            pkg_price = 0
            if pkg_type_id and item.package_type:
                pkg_price = int(item.package_type.price or 0)

            required_qty = item.quantity

            # Lock and reserve bars - filter by location for delivery method
            bar_filter = db.query(Bar).filter(
                Bar.product_id == item.product_id,
                Bar.status == BarStatus.ASSIGNED,
                Bar.customer_id.is_(None),
                Bar.reserved_customer_id.is_(None),
            )

            # Dealer-aware reservation
            if delivery_method == DeliveryMethod.PICKUP and new_order.pickup_dealer_id:
                bar_filter = bar_filter.filter(Bar.dealer_id == new_order.pickup_dealer_id)
            elif delivery_method == DeliveryMethod.POSTAL:
                postal_hub = delivery_service.get_postal_hub(db)
                if postal_hub:
                    bar_filter = bar_filter.filter(Bar.dealer_id == postal_hub.id)

            available_bars = (
                bar_filter
                .with_for_update(skip_locked=True)
                .limit(required_qty)
                .all()
            )

            if len(available_bars) < required_qty:
                # Build helpful error message
                location_name = ""
                if delivery_method == DeliveryMethod.PICKUP and new_order.pickup_dealer_id:
                    from modules.dealer.models import Dealer
                    dlr = db.query(Dealer).filter(Dealer.id == new_order.pickup_dealer_id).first()
                    location_name = f" در {dlr.full_name}" if dlr else ""
                elif delivery_method == DeliveryMethod.POSTAL:
                    location_name = " در انبار ارسال پستی"
                db.rollback()
                raise ValueError(f"موجودی «{item.product.name}»{location_name} کافی نیست (نیاز: {required_qty}, موجود: {len(available_bars)})")

            for bar in available_bars:
                bar.status = BarStatus.RESERVED
                bar.reserved_customer_id = customer_id
                bar.reserved_until = expire_at

                oi = build_order_item(item.product, bar, price_info, gold_price_rial, tax_percent_str,
                                     package_type_id=pkg_type_id, package_price=pkg_price)
                oi.order_id = new_order.id
                order_items.append(oi)
                cart_raw_total += int(price_info.get("total", 0)) + pkg_price

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
    # Finalize (mark as Paid)
    # ==========================================

    def finalize_order(self, db: Session, order_id: int) -> Optional[Order]:
        """
        Mark order as Paid and transfer bar ownership.
        Called after successful payment (wallet or gateway callback).
        """
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order or order.status != OrderStatus.PENDING:
            return None

        for oi in order.items:
            if oi.bar_id:
                bar = db.query(Bar).filter(Bar.id == oi.bar_id).first()
                if bar:
                    bar.status = BarStatus.SOLD
                    bar.reserved_customer_id = None
                    bar.reserved_until = None

                    if order.is_gift:
                        # Gift: don't assign to buyer, generate claim code
                        bar.customer_id = None
                        bar.claim_code = generate_unique_claim_code(db)
                        db.add(OwnershipHistory(
                            bar_id=bar.id,
                            previous_owner_id=None,
                            new_owner_id=None,
                            description=f"خرید هدیه — سفارش #{order.id}",
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

        order.status = OrderStatus.PAID

        # Process referral reward on first purchase (not registration)
        self._process_referral_reward_on_first_purchase(db, order.customer_id)

        db.flush()
        return order

    def _process_referral_reward_on_first_purchase(self, db: Session, customer_id: int):
        """Credit referrer's wallet when referred customer makes their first purchase."""
        from modules.customer.models import Customer
        from modules.wallet.service import wallet_service

        REFERRAL_REWARD_RIAL = 500_000  # 50,000 toman

        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer or customer.referral_rewarded:
            return
        if not customer.referred_by:
            return

        referrer = db.query(Customer).filter(Customer.id == customer.referred_by).first()
        if not referrer:
            return

        try:
            wallet_service.deposit(
                db,
                owner_id=referrer.id,
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

    def cancel_order(self, db: Session, order_id: int, reason: str = "") -> Optional[Order]:
        """Cancel order and release reserved bars."""
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order or order.status != OrderStatus.PENDING:
            return None

        self._release_order_bars(db, order)
        order.status = OrderStatus.CANCELLED
        order.cancellation_reason = reason or None
        order.cancelled_at = now_utc()
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
            order.status = OrderStatus.CANCELLED
            order.cancellation_reason = f"عدم پرداخت در مهلت مقرر ({reservation_minutes} دقیقه)"
            order.cancelled_at = now_ts
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
        """Determine metal type from product categories (slug prefix)."""
        if product and hasattr(product, 'categories'):
            for cat in product.categories:
                if cat.slug and cat.slug.startswith("silver"):
                    return "silver"
        return "gold"

    def get_pending_delivery_stats(self, db: Session):
        """Get separate gold/silver stats for paid pickup orders not yet delivered."""
        from sqlalchemy.orm import joinedload
        orders = (
            db.query(Order)
            .options(joinedload(Order.items), joinedload(Order.customer))
            .filter(
                Order.status == OrderStatus.PAID,
                Order.delivery_method == DeliveryMethod.PICKUP,
                Order.delivery_status.notin_([DeliveryStatus.DELIVERED, DeliveryStatus.RETURNED]),
            )
            .order_by(desc(Order.id))
            .all()
        )

        gold_weight = Decimal("0")
        silver_weight = Decimal("0")
        gold_bars = []
        silver_bars = []
        gold_order_ids = set()
        silver_order_ids = set()

        for order in orders:
            for oi in order.items:
                weight = oi.applied_weight or Decimal("0")
                metal = self._get_metal_type(oi.product)
                bar_info = {
                    "order_id": order.id,
                    "customer_name": order.customer.full_name if order.customer else "—",
                    "customer_mobile": order.customer.mobile if order.customer else "",
                    "serial_code": oi.bar.serial_code if oi.bar else "—",
                    "product_name": oi.product.name if oi.product else "—",
                    "weight": float(weight),
                    "delivery_status": order.delivery_status_label if order.delivery_status else "—",
                    "order_date": order.created_at,
                }
                if metal == "silver":
                    silver_weight += weight
                    silver_bars.append(bar_info)
                    silver_order_ids.add(order.id)
                else:
                    gold_weight += weight
                    gold_bars.append(bar_info)
                    gold_order_ids.add(order.id)

        return {
            "gold": {
                "total_weight": float(gold_weight),
                "total_bars": len(gold_bars),
                "total_orders": len(gold_order_ids),
                "bars": gold_bars,
            },
            "silver": {
                "total_weight": float(silver_weight),
                "total_bars": len(silver_bars),
                "total_orders": len(silver_order_ids),
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
            from modules.customer.models import Customer
            term = f"%{search.strip()}%"
            q = q.join(Order.customer).filter(
                or_(Customer.first_name.ilike(term),
                    Customer.last_name.ilike(term),
                    Customer.mobile.ilike(term))
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
        val = get_setting_from_db(db, "gold_price", "0")
        return int(val) if val.isdigit() else 0

    def _tax_percent(self, db: Session) -> str:
        return get_setting_from_db(db, "tax_percent", "9")


# Singleton
order_service = OrderService()
