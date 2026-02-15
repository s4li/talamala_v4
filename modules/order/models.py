"""
Order Module - Models
======================
Order with full price snapshot per item for audit trail.
"""

import enum
from sqlalchemy import (
    Column, Integer, String, BigInteger, Numeric, Boolean, Text,
    ForeignKey, DateTime, text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class DeliveryMethod(str, enum.Enum):
    PICKUP = "Pickup"      # تحویل حضوری
    POSTAL = "Postal"      # ارسال پستی


class OrderStatus(str, enum.Enum):
    PENDING = "Pending"
    PAID = "Paid"
    CANCELLED = "Cancelled"


class DeliveryStatus(str, enum.Enum):
    WAITING = "Waiting"                # منتظر مراجعه / آماده‌سازی
    PREPARING = "Preparing"            # در حال بسته‌بندی
    SHIPPED = "Shipped"                # ارسال شده (پستی)
    DELIVERED = "Delivered"            # تحویل داده شده
    RETURNED = "Returned"             # مرجوعی


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    total_amount = Column(BigInteger, nullable=False)
    status = Column(String, default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    track_id = Column(String, unique=True, nullable=True)

    # Delivery
    delivery_method = Column(String, nullable=True)                   # Pickup / Postal
    delivery_status = Column(String, default=DeliveryStatus.WAITING, nullable=True)

    # Pickup delivery
    pickup_dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="SET NULL"), nullable=True)
    delivery_code_hash = Column(String, nullable=True)                # Hashed 6-digit code
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Postal delivery
    shipping_province = Column(String, nullable=True)
    shipping_city = Column(String, nullable=True)
    shipping_address = Column(Text, nullable=True)
    shipping_postal_code = Column(String, nullable=True)
    shipping_cost = Column(BigInteger, default=0, nullable=False)     # هزینه پست
    insurance_cost = Column(BigInteger, default=0, nullable=False)    # هزینه بیمه
    postal_tracking_code = Column(String, nullable=True)              # کد رهگیری پست

    # Promo / Coupon (Phase 8)
    promo_choice = Column(String, nullable=True)
    promo_amount = Column(BigInteger, server_default=text("0"), default=0, nullable=False)
    cashback_settled = Column(Boolean, server_default=text("false"), default=False, nullable=False)
    coupon_code = Column(String, nullable=True)

    # Gift order
    is_gift = Column(Boolean, server_default=text("false"), default=False, nullable=False)

    # Cancellation
    cancellation_reason = Column(String, nullable=True)   # دلیل لغو سفارش
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Payment (Phase 9)
    payment_method = Column(String, nullable=True)    # wallet / gateway_zibal / gateway_sepehr
    payment_ref = Column(String, nullable=True)        # شماره مرجع / ref_number
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id])
    pickup_dealer = relationship("Dealer", foreign_keys=[pickup_dealer_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    @property
    def status_label(self) -> str:
        labels = {
            OrderStatus.PENDING: "در انتظار پرداخت",
            OrderStatus.PAID: "پرداخت شده",
            OrderStatus.CANCELLED: "لغو شده",
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        colors = {
            OrderStatus.PENDING: "warning",
            OrderStatus.PAID: "success",
            OrderStatus.CANCELLED: "danger",
        }
        return colors.get(self.status, "secondary")

    @property
    def delivery_method_label(self) -> str:
        labels = {
            DeliveryMethod.PICKUP: "تحویل حضوری",
            DeliveryMethod.POSTAL: "ارسال پستی",
        }
        return labels.get(self.delivery_method, "—")

    @property
    def delivery_status_label(self) -> str:
        labels = {
            DeliveryStatus.WAITING: "منتظر مراجعه" if self.delivery_method == DeliveryMethod.PICKUP else "در حال آماده‌سازی",
            DeliveryStatus.PREPARING: "در حال بسته‌بندی",
            DeliveryStatus.SHIPPED: "ارسال شده",
            DeliveryStatus.DELIVERED: "تحویل داده شده",
            DeliveryStatus.RETURNED: "مرجوعی",
        }
        return labels.get(self.delivery_status, "—")

    @property
    def delivery_status_color(self) -> str:
        colors = {
            DeliveryStatus.WAITING: "warning",
            DeliveryStatus.PREPARING: "info",
            DeliveryStatus.SHIPPED: "primary",
            DeliveryStatus.DELIVERED: "success",
            DeliveryStatus.RETURNED: "danger",
        }
        return colors.get(self.delivery_status, "secondary")

    @property
    def grand_total(self) -> int:
        """Total including shipping + insurance − discount (cashback doesn't reduce)."""
        base = self.total_amount + (self.shipping_cost or 0) + (self.insurance_cost or 0)
        if self.promo_choice == "DISCOUNT" and self.promo_amount:
            base = max(0, base - self.promo_amount)
        return base


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="SET NULL"), nullable=True)

    # Price snapshot at time of purchase
    applied_gold_price = Column(BigInteger, nullable=False)
    applied_unit_price = Column(BigInteger, nullable=False)
    applied_weight = Column(Numeric(10, 3), nullable=False)
    applied_purity = Column(Numeric(4, 1), nullable=False)
    applied_wage_percent = Column(Numeric(5, 2), nullable=False)
    applied_tax_percent = Column(Numeric(5, 2), nullable=False)

    # Calculated amounts
    final_gold_amount = Column(BigInteger, nullable=False)
    final_wage_amount = Column(BigInteger, nullable=False)
    final_tax_amount = Column(BigInteger, default=0, nullable=False)
    line_total = Column(BigInteger, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    bar = relationship("Bar")
