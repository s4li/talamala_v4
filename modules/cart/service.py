"""
Cart Module - Service Layer
==============================
Cart management: get/create, add/remove items, calculate totals.
"""

from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from modules.cart.models import Cart, CartItem
from modules.catalog.models import Product
from modules.inventory.models import Bar, BarStatus
from modules.pricing.calculator import calculate_bar_price, calculate_gold_cost
from modules.pricing.service import get_end_customer_wage, get_product_pricing
from common.templating import get_setting_from_db


class CartService:

    def get_or_create_cart(self, db: Session, customer_id: int) -> Cart:
        """Get existing cart or create new one for customer."""
        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if not cart:
            cart = Cart(customer_id=customer_id)
            db.add(cart)
            db.flush()
        return cart

    def get_available_inventory(self, db: Session, product_id: int) -> int:
        """Count available (non-reserved) bars for a product."""
        return db.query(Bar).filter(
            Bar.product_id == product_id,
            Bar.status == BarStatus.ASSIGNED,
            Bar.customer_id.is_(None),
            Bar.reserved_customer_id.is_(None),
        ).count()

    def update_item(self, db: Session, customer_id: int, product_id: int, change: int,
                    gift_box_id: int = None) -> Tuple[int, int]:
        """
        Update cart item quantity by `change` (+1 or -1).
        If gift_box_id is provided on first add, it's set on the CartItem.
        Returns: (new_quantity, total_cart_count)
        """
        cart = self.get_or_create_cart(db, customer_id)
        inventory = self.get_available_inventory(db, product_id)

        item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id,
        ).first()

        new_qty = 0
        if item:
            new_qty = item.quantity + change
            if new_qty > inventory:
                new_qty = inventory
            if new_qty <= 0:
                db.delete(item)
                new_qty = 0
            else:
                item.quantity = new_qty
                if gift_box_id is not None and change > 0:
                    item.gift_box_id = gift_box_id
        elif change > 0:
            if inventory < 1:
                return 0, self._cart_count(db, cart.id)
            item = CartItem(cart_id=cart.id, product_id=product_id, quantity=1,
                           gift_box_id=gift_box_id)
            db.add(item)
            new_qty = 1

        db.flush()
        total = self._cart_count(db, cart.id)
        return new_qty, total

    def set_gift_box(self, db: Session, customer_id: int, product_id: int,
                     gift_box_id: int = None) -> bool:
        """Set or clear the gift box for a cart item. Returns True if found."""
        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if not cart:
            return False
        item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id,
        ).first()
        if not item:
            return False
        item.gift_box_id = gift_box_id
        db.flush()
        return True

    def get_cart_items_with_pricing(self, db: Session, customer_id: int,
                                    dealer=None) -> Tuple[List[dict], int]:
        """
        Get all cart items with calculated prices and inventory.
        If dealer is provided (User with is_dealer=True), uses dealer's tier wage
        from ProductTierWage instead of end-customer wage.
        Returns: (items_data, total_cart_price)
        """
        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if not cart or not cart.items:
            return [], 0

        tax_percent_str = self._tax_percent(db)

        # Batch inventory lookup
        product_ids = [it.product_id for it in cart.items]
        inv_rows = db.query(Bar.product_id, func.count(Bar.id)).filter(
            Bar.product_id.in_(product_ids),
            Bar.status == BarStatus.ASSIGNED,
            Bar.customer_id.is_(None),
            Bar.reserved_customer_id.is_(None),
        ).group_by(Bar.product_id).all()
        inv_map = {pid: cnt for pid, cnt in inv_rows}

        # Batch dealer tier wages (if dealer)
        dealer_wage_map = {}
        if dealer and dealer.tier_id:
            from modules.catalog.models import ProductTierWage
            tier_wages = db.query(ProductTierWage).filter(
                ProductTierWage.product_id.in_(product_ids),
                ProductTierWage.tier_id == dealer.tier_id,
            ).all()
            dealer_wage_map = {tw.product_id: float(tw.wage_percent) for tw in tier_wages}

        items_data = []
        total_price = 0

        for item in cart.items:
            # Per-product metal pricing
            p_price, p_bp, _ = get_product_pricing(db, item.product)

            # Use dealer tier wage if available, otherwise end-customer wage
            if dealer and dealer.tier_id:
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
            unit_total = int(price_info.get("total", 0))

            # Gift box price (per bar)
            gift_box_price = 0
            if item.gift_box_id and item.gift_box:
                gift_box_price = int(item.gift_box.price or 0)

            line_total = (unit_total + gift_box_price) * item.quantity
            total_price += line_total

            item_data = {
                "product": item.product,
                "quantity": item.quantity,
                "unit_price": unit_total,
                "gift_box": item.gift_box,
                "gift_box_price": gift_box_price,
                "line_total": line_total,
                "inventory": inv_map.get(item.product_id, 0),
                "details": price_info,
                "db_item_id": item.id,
            }
            if dealer:
                item_data["dealer_wage_percent"] = wage

            items_data.append(item_data)

        return items_data, total_price

    def get_cart_items_with_gold_pricing(
        self, db: Session, customer_id: int, dealer
    ) -> Tuple[List[dict], int]:
        """
        Get cart items with gold-for-gold pricing for dealers.
        Uses dealer's tier wage from ProductTierWage. Gift box ignored.
        Returns: (items_data, total_gold_mg)
        """
        from modules.catalog.models import ProductTierWage

        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if not cart or not cart.items:
            return [], 0

        # Batch inventory lookup
        product_ids = [it.product_id for it in cart.items]
        inv_rows = db.query(Bar.product_id, func.count(Bar.id)).filter(
            Bar.product_id.in_(product_ids),
            Bar.status == BarStatus.ASSIGNED,
            Bar.customer_id.is_(None),
            Bar.reserved_customer_id.is_(None),
        ).group_by(Bar.product_id).all()
        inv_map = {pid: cnt for pid, cnt in inv_rows}

        items_data = []
        total_gold_mg = 0

        for item in cart.items:
            # Dealer tier wage
            tw = None
            if dealer.tier_id:
                tw = db.query(ProductTierWage).filter(
                    ProductTierWage.product_id == item.product_id,
                    ProductTierWage.tier_id == dealer.tier_id,
                ).first()
            dealer_wage = float(tw.wage_percent) if tw else float(item.product.wage)

            gold_info = calculate_gold_cost(
                weight=item.product.weight,
                purity=item.product.purity,
                wage_percent=dealer_wage,
            )
            item_gold_mg = gold_info.get("total_mg", 0) * item.quantity
            total_gold_mg += item_gold_mg

            items_data.append({
                "product": item.product,
                "quantity": item.quantity,
                "gold_cost_info": gold_info,
                "item_gold_mg": item_gold_mg,
                "dealer_wage_percent": dealer_wage,
                "inventory": inv_map.get(item.product_id, 0),
                "db_item_id": item.id,
            })

        return items_data, total_gold_mg

    def get_cart_map(self, db: Session, customer_id: int) -> Tuple[dict, int]:
        """Get {product_id: quantity} map and total count for shop pages."""
        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if not cart or not cart.items:
            return {}, 0
        cart_map = {item.product_id: item.quantity for item in cart.items}
        return cart_map, sum(cart_map.values())

    def clear_cart(self, db: Session, customer_id: int):
        """Remove all items from customer's cart."""
        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if cart:
            db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
            db.flush()

    # ==========================================
    # Private helpers
    # ==========================================

    def _cart_count(self, db: Session, cart_id: int) -> int:
        return db.query(
            func.coalesce(func.sum(CartItem.quantity), 0)
        ).filter(CartItem.cart_id == cart_id).scalar() or 0

    def _gold_price(self, db: Session) -> int:
        from modules.pricing.service import get_price_value
        from modules.pricing.models import GOLD_18K
        return get_price_value(db, GOLD_18K)

    def _tax_percent(self, db: Session) -> str:
        return get_setting_from_db(db, "tax_percent", "9")


# Singleton
cart_service = CartService()
