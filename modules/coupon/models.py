"""
Coupon Module - Models
========================
Comprehensive discount/cashback coupon system.

Features:
  - Discount (instant) or Cashback (wallet credit after delivery)
  - Percentage or Fixed amount
  - Per-product / per-category / global scope
  - Per-customer (mobile whitelist) or public
  - Usage limits (total + per-customer)
  - Date range (start_at / expires_at)
  - Min/Max order constraints
  - First-purchase-only flag
  - Combinable flag (stack with other coupons)
  - Referral tracking (referrer_customer_id)
"""

import enum
from sqlalchemy import (
    Column, Integer, String, BigInteger, Boolean, Text,
    DateTime, ForeignKey, Numeric, Index, text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# Enums
# ==========================================

class CouponType(str, enum.Enum):
    DISCOUNT = "DISCOUNT"    # تخفیف مستقیم
    CASHBACK = "CASHBACK"    # کشبک (واریز به کیف پول)


class DiscountMode(str, enum.Enum):
    PERCENT = "PERCENT"      # درصدی
    FIXED = "FIXED"          # مبلغ ثابت (ریال)


class CouponScope(str, enum.Enum):
    GLOBAL = "GLOBAL"        # کل سفارش
    PRODUCT = "PRODUCT"      # محصول خاص
    CATEGORY = "CATEGORY"    # دسته‌بندی (product_type)


class CouponStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"


# ==========================================
# Coupon
# ==========================================

class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Type & Mode
    coupon_type = Column(String, default=CouponType.DISCOUNT, nullable=False)
    discount_mode = Column(String, default=DiscountMode.PERCENT, nullable=False)
    discount_value = Column(BigInteger, nullable=False)  # percent (e.g. 10) or fixed in Rial

    # Caps
    max_discount_amount = Column(BigInteger, nullable=True)  # سقف تخفیف (ریال) for percent mode

    # Scope
    scope = Column(String, default=CouponScope.GLOBAL, nullable=False)
    scope_product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    scope_category = Column(String, nullable=True)  # legacy (use coupon_categories M2M)

    # Constraints
    min_order_amount = Column(BigInteger, default=0, nullable=False)  # حداقل مبلغ سفارش
    max_order_amount = Column(BigInteger, nullable=True)  # حداکثر مبلغ سفارش
    min_quantity = Column(Integer, default=0, nullable=False)  # حداقل تعداد اقلام

    # Usage limits
    max_total_uses = Column(Integer, nullable=True)  # سقف کل استفاده
    max_per_customer = Column(Integer, default=1, nullable=False)  # سقف استفاده هر مشتری
    current_uses = Column(Integer, default=0, nullable=False)

    # Date range
    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Special flags
    first_purchase_only = Column(Boolean, default=False, nullable=False)  # فقط اولین خرید
    is_combinable = Column(Boolean, default=False, nullable=False)  # قابل ترکیب
    is_private = Column(Boolean, default=False, nullable=False)  # فقط با کد (نه در لیست عمومی)

    # Referral
    referrer_customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)

    # Status
    status = Column(String, default=CouponStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    scope_product = relationship("Product", foreign_keys=[scope_product_id])
    referrer = relationship("Customer", foreign_keys=[referrer_customer_id])
    allowed_mobiles = relationship("CouponMobile", back_populates="coupon", cascade="all, delete-orphan")
    usages = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan")
    categories = relationship("CouponCategory", back_populates="coupon", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_coupon_code_status", "code", "status"),
    )

    @property
    def coupon_type_label(self) -> str:
        return {"DISCOUNT": "تخفیف", "CASHBACK": "کشبک"}.get(self.coupon_type, self.coupon_type)

    @property
    def discount_mode_label(self) -> str:
        return {"PERCENT": "درصدی", "FIXED": "مبلغ ثابت"}.get(self.discount_mode, self.discount_mode)

    @property
    def scope_label(self) -> str:
        return {"GLOBAL": "کل سفارش", "PRODUCT": "محصول خاص", "CATEGORY": "دسته‌بندی"}.get(self.scope, self.scope)

    @property
    def status_label(self) -> str:
        return {"ACTIVE": "فعال", "INACTIVE": "غیرفعال", "EXPIRED": "منقضی"}.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        return {"ACTIVE": "success", "INACTIVE": "secondary", "EXPIRED": "danger"}.get(self.status, "secondary")

    @property
    def discount_display(self) -> str:
        """Human-readable discount value."""
        if self.discount_mode == DiscountMode.PERCENT:
            s = f"{self.discount_value}٪"
            if self.max_discount_amount:
                cap_toman = self.max_discount_amount // 10
                s += f" (سقف {cap_toman:,} تومان)"
            return s
        else:
            val_toman = self.discount_value // 10
            return f"{val_toman:,} تومان"

    @property
    def is_mobile_restricted(self) -> bool:
        """Check if coupon is restricted to specific mobile numbers."""
        return len(self.allowed_mobiles) > 0


# ==========================================
# CouponMobile (whitelist per coupon)
# ==========================================

class CouponMobile(Base):
    __tablename__ = "coupon_mobiles"

    id = Column(Integer, primary_key=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    mobile = Column(String(15), nullable=False)
    note = Column(String(200), nullable=True)  # یادداشت اختیاری
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    coupon = relationship("Coupon", back_populates="allowed_mobiles")

    __table_args__ = (
        Index("ix_coupon_mobile_unique", "coupon_id", "mobile", unique=True),
    )


# ==========================================
# CouponUsage (audit trail)
# ==========================================

class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    id = Column(Integer, primary_key=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    discount_amount = Column(BigInteger, nullable=False)  # مبلغ تخفیف / کشبک اعمال شده
    cashback_settled = Column(Boolean, default=False, nullable=False)  # آیا کشبک واریز شده؟
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    coupon = relationship("Coupon", back_populates="usages")
    customer = relationship("Customer")
    order = relationship("Order")

    __table_args__ = (
        Index("ix_usage_coupon_customer", "coupon_id", "customer_id"),
    )


# ==========================================
# CouponCategory (M2M: coupon ↔ product_categories)
# ==========================================

class CouponCategory(Base):
    __tablename__ = "coupon_categories"

    id = Column(Integer, primary_key=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("product_categories.id", ondelete="CASCADE"), nullable=False)

    coupon = relationship("Coupon", back_populates="categories")
    category = relationship("ProductCategory")

    __table_args__ = (
        Index("ix_coupon_category_unique", "coupon_id", "category_id", unique=True),
    )
