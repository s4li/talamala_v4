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
from modules.pricing.calculator import calculate_bar_price
from modules.pricing.service import get_end_customer_wage
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

    def update_item(self, db: Session, customer_id: int, product_id: int, change: int) -> Tuple[int, int]:
        """
        Update cart item quantity by `change` (+1 or -1).
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
        elif change > 0:
            if inventory < 1:
                return 0, self._cart_count(db, cart.id)
            item = CartItem(cart_id=cart.id, product_id=product_id, quantity=1)
            db.add(item)
            new_qty = 1

        db.flush()
        total = self._cart_count(db, cart.id)
        return new_qty, total

    def get_cart_items_with_pricing(self, db: Session, customer_id: int) -> Tuple[List[dict], int]:
        """
        Get all cart items with calculated prices and inventory.
        Returns: (items_data, total_cart_price)
        """
        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if not cart or not cart.items:
            return [], 0

        gold_price_rial = self._gold_price(db)
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

        items_data = []
        total_price = 0

        for item in cart.items:
            ec_wage = get_end_customer_wage(db, item.product)
            price_info = calculate_bar_price(
                weight=item.product.weight,
                purity=item.product.purity,
                wage_percent=ec_wage,
                base_gold_price_18k=gold_price_rial,
                tax_percent=Decimal(tax_percent_str) if tax_percent_str else 0,
            )
            unit_total = int(price_info.get("total", 0))
            line_total = unit_total * item.quantity
            total_price += line_total

            items_data.append({
                "product": item.product,
                "quantity": item.quantity,
                "unit_price": unit_total,
                "line_total": line_total,
                "inventory": inv_map.get(item.product_id, 0),
                "details": price_info,
                "db_item_id": item.id,
            })

        return items_data, total_price

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
        val = get_setting_from_db(db, "gold_price", "0")
        return int(val) if val.isdigit() else 0

    def _tax_percent(self, db: Session) -> str:
        return get_setting_from_db(db, "tax_percent", "9")


# Singleton
cart_service = CartService()
