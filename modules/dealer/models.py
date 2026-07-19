"""
Dealer Module - Models
========================
Dealer tiers, POS sales, and buyback requests.

Models:
  - DealerTier: Dealer level (پخش, بنکدار, فروشگاه, مشتری نهایی)
  - DealerSale: POS sale record (walk-in customer purchase via dealer)
  - BuybackRequest: Customer wants to sell back a bar (dealer initiates)

Note: The Dealer class has been removed. Dealer data is now part of the
unified User model (modules/user/models.py) with is_dealer=True.
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean,
    BigInteger, Text, Numeric, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# Enums
# ==========================================

class BuybackStatus(str, enum.Enum):
    PENDING = "Pending"       # OTP ارسال شده — در انتظار تأیید فروشنده
    COMPLETED = "Completed"   # تسویه شده — وجه به کیف پول واریز شد
    REJECTED = "Rejected"     # رد شده / لغو شده / منقضی شده



# ==========================================
# Dealer Tier (سطوح نمایندگان)
# ==========================================

class DealerTier(Base):
    __tablename__ = "dealer_tiers"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)        # "پخش", "بنکدار", "فروشگاه", "مشتری نهایی"
    slug = Column(String, unique=True, nullable=False)        # "distributor", "wholesaler", "store", "end_customer"
    sort_order = Column(Integer, default=0)
    is_end_customer = Column(Boolean, default=False)          # فلگ ویژه: بالاترین اجرت
    is_active = Column(Boolean, default=True)
    default_credit_limit_mg = Column(BigInteger, default=0, nullable=False, server_default="0")  # سقف اعتبار پیش‌فرض (mg)

    def __repr__(self):
        return f"<DealerTier {self.name} (ec={self.is_end_customer})>"


# ==========================================
# Dealer Sale (POS)
# ==========================================

class DealerSale(Base):
    __tablename__ = "dealer_sales"

    id = Column(Integer, primary_key=True)
    dealer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String, nullable=True)
    customer_mobile = Column(String(15), nullable=True)
    customer_national_id = Column(String, nullable=True)
    sale_price = Column(BigInteger, nullable=False)           # ریال
    applied_metal_price = Column(BigInteger, nullable=True)  # قیمت فلز پایه در لحظه فروش (ریال/گرم)
    commission_amount = Column(BigInteger, default=0, nullable=False)  # ریال (legacy)
    metal_profit_mg = Column(BigInteger, default=0, nullable=False)   # سود فلزی (میلی‌گرم)
    metal_type = Column(String(20), default="gold", nullable=False)   # "gold", "silver" — maps to PRECIOUS_METALS
    discount_wage_percent = Column(Numeric(5, 2), default=0, nullable=False)  # تخفیف اجرت از سهم نماینده (درصد)
    description = Column(Text, nullable=True)
    # --- Product snapshot (immutable at sale time) ---
    # bar_id/product_id are SET NULL on delete, so the live join can vanish.
    # These columns keep the report correct after a bar or product is removed.
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name = Column(String, nullable=True)                      # نام محصول در لحظه فروش
    product_weight = Column(Numeric(10, 3), nullable=True)            # وزن (گرم)
    product_purity = Column(Numeric(6, 1), nullable=True)             # عیار (در هزار)
    applied_wage_percent = Column(Numeric(5, 2), nullable=True)       # اجرت مشتری نهایی در لحظه فروش (درصد)
    serial_code = Column(String, nullable=True, index=True)           # سریال شمش در لحظه فروش
    # Sub-dealer commission split tracking
    parent_dealer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_commission_mg = Column(BigInteger, default=0, nullable=False)  # parent's share (milligrams)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dealer = relationship("User", foreign_keys=[dealer_id])
    parent_dealer = relationship("User", foreign_keys=[parent_dealer_id])
    bar = relationship("Bar", foreign_keys=[bar_id])
    product = relationship("Product", foreign_keys=[product_id])

    # --- Display helpers: snapshot first, live join only as fallback ---

    @property
    def display_product_name(self) -> str:
        if self.product_name:
            return self.product_name
        if self.bar and self.bar.product:
            return self.bar.product.name
        return "—"

    @property
    def display_serial(self) -> str:
        if self.serial_code:
            return self.serial_code
        if self.bar:
            return self.bar.serial_code
        return "—"

    @property
    def display_weight(self):
        """Weight in grams (Decimal) or None."""
        if self.product_weight is not None:
            return self.product_weight
        if self.bar and self.bar.product:
            return self.bar.product.weight
        return None

    @property
    def weight_mg(self) -> int:
        w = self.display_weight
        return int(float(w) * 1000) if w else 0

    @property
    def wage_mg(self) -> int:
        """Total wage in milligrams of metal — the pool split between us and the dealer.

        Mirrors how metal_profit_mg is computed at sale time (gross weight × percent),
        so `wage_mg - metal_profit_mg` is a like-for-like figure.
        """
        w = self.display_weight
        pct = self.applied_wage_percent
        if pct is None and self.bar and self.bar.product:
            pct = self.bar.product.wage
        if not w or pct is None:
            return 0
        return int(float(w) * float(pct) / 100 * 1000)

    @property
    def our_profit_mg(self) -> int:
        """Our share of the wage after the dealer's cut."""
        return max(0, self.wage_mg - (self.metal_profit_mg or 0))


# ==========================================
# Buyback Request
# ==========================================

class BuybackRequest(Base):
    __tablename__ = "buyback_requests"

    id = Column(Integer, primary_key=True)
    dealer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String, nullable=True)              # نام فروشنده
    customer_mobile = Column(String(15), nullable=True)        # موبایل فروشنده
    seller_national_id = Column(String, nullable=True)         # کد ملی فروشنده
    seller_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # کاربر فروشنده (بعد از verify)
    is_owner = Column(Boolean, default=False, nullable=False)  # آیا فروشنده همون مالک اصلیه؟
    buyback_price = Column(BigInteger, nullable=False)         # ریال — ارزش طلای خام
    wage_refund_amount = Column(BigInteger, default=0, nullable=False)      # اجرت بازخرید (ریال) — فقط وقتی is_owner=True
    wage_refund_customer_id = Column(Integer, nullable=True)                 # user_id دریافت‌کننده وجه
    status = Column(String, default=BuybackStatus.PENDING, nullable=False)
    otp_hash = Column(String, nullable=True)                   # HMAC hash of OTP
    otp_expiry = Column(DateTime(timezone=True), nullable=True)
    admin_note = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dealer = relationship("User", foreign_keys=[dealer_id])
    seller = relationship("User", foreign_keys=[seller_user_id])
    bar = relationship("Bar", foreign_keys=[bar_id])

    @property
    def status_label(self) -> str:
        labels = {
            BuybackStatus.PENDING: "در انتظار تأیید OTP",
            BuybackStatus.COMPLETED: "تسویه شده",
            BuybackStatus.REJECTED: "لغو شده",
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        colors = {
            BuybackStatus.PENDING: "warning",
            BuybackStatus.COMPLETED: "success",
            BuybackStatus.REJECTED: "danger",
        }
        return colors.get(self.status, "secondary")


# ==========================================
# Sub-Dealer Relation (شبکه زیرمجموعه)
# ==========================================

class SubDealerRelation(Base):
    __tablename__ = "sub_dealer_relations"

    id = Column(Integer, primary_key=True)
    parent_dealer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    child_dealer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    commission_split_percent = Column(Numeric(5, 2), default=20.0, nullable=False)  # % of child's profit → parent
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    admin_note = Column(Text, nullable=True)

    parent_dealer = relationship("User", foreign_keys=[parent_dealer_id])
    child_dealer = relationship("User", foreign_keys=[child_dealer_id])

    __table_args__ = (
        UniqueConstraint("parent_dealer_id", "child_dealer_id", name="uq_sub_dealer_relation"),
        CheckConstraint("commission_split_percent >= 0 AND commission_split_percent <= 100",
                        name="ck_commission_split_range"),
        CheckConstraint("parent_dealer_id != child_dealer_id",
                        name="ck_no_self_reference"),
    )

    @property
    def status_label(self) -> str:
        return "فعال" if self.is_active else "غیرفعال"

    @property
    def status_color(self) -> str:
        return "success" if self.is_active else "secondary"
