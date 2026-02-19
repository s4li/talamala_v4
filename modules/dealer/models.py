"""
Dealer Module - Models
========================
Dealer representatives, POS sales, buyback requests, and dealer tiers.

Models:
  - DealerTier: Dealer level (پخش, بنکدار, فروشگاه, مشتری نهایی)
  - Dealer: Representative who sells bars at a branch location (dealer IS the warehouse)
  - DealerSale: POS sale record (walk-in customer purchase via dealer)
  - BuybackRequest: Customer wants to sell back a bar (dealer initiates)
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean,
    BigInteger, Text, Numeric,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# Enums
# ==========================================

class BuybackStatus(str, enum.Enum):
    PENDING = "Pending"       # در انتظار تایید ادمین
    APPROVED = "Approved"     # تایید شده - آماده تسویه
    COMPLETED = "Completed"   # تسویه شده - وجه واریز شد
    REJECTED = "Rejected"     # رد شده


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

    dealers = relationship("Dealer", back_populates="tier")

    def __repr__(self):
        return f"<DealerTier {self.name} (ec={self.is_end_customer})>"


# ==========================================
# Dealer (نماینده = انبار/مکان فیزیکی)
# ==========================================

class Dealer(Base):
    __tablename__ = "dealers"

    id = Column(Integer, primary_key=True)
    mobile = Column(String(11), unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    national_id = Column(String, nullable=True)
    tier_id = Column(Integer, ForeignKey("dealer_tiers.id", ondelete="SET NULL"), nullable=True, index=True)
    commission_percent = Column(Numeric(5, 2), default=2.0, nullable=False)  # legacy
    is_active = Column(Boolean, default=True, nullable=False)

    # Warehouse / Postal flags
    is_warehouse = Column(Boolean, default=False, nullable=False)     # انبار مرکزی (بدون فروش POS)
    is_postal_hub = Column(Boolean, default=False, nullable=False)    # انبار ارسال پستی

    # Address fields
    province_id = Column(Integer, ForeignKey("geo_provinces.id", ondelete="SET NULL"), nullable=True, index=True)
    city_id = Column(Integer, ForeignKey("geo_cities.id", ondelete="SET NULL"), nullable=True, index=True)
    district_id = Column(Integer, ForeignKey("geo_districts.id", ondelete="SET NULL"), nullable=True, index=True)
    address = Column(Text, nullable=True)
    postal_code = Column(String(10), nullable=True)
    landline_phone = Column(String(15), nullable=True)

    # API Key for POS device authentication
    api_key = Column(String(64), unique=True, nullable=True, index=True)

    # OTP fields (for login)
    otp_code = Column(String, nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tier = relationship("DealerTier", back_populates="dealers")
    province = relationship("GeoProvince", foreign_keys=[province_id])
    city = relationship("GeoCity", foreign_keys=[city_id])
    district = relationship("GeoDistrict", foreign_keys=[district_id])
    sales = relationship("DealerSale", back_populates="dealer", cascade="all, delete-orphan")
    buybacks = relationship("BuybackRequest", back_populates="dealer", cascade="all, delete-orphan")

    @property
    def tier_name(self) -> str:
        return self.tier.name if self.tier else "—"

    @property
    def province_name(self) -> str:
        return self.province.name if self.province else "—"

    @property
    def city_name(self) -> str:
        return self.city.name if self.city else "—"

    @property
    def district_name(self) -> str:
        return self.district.name if self.district else "—"

    @property
    def full_address(self) -> str:
        parts = []
        if self.province:
            parts.append(self.province.name)
        if self.city:
            parts.append(self.city.name)
        if self.district:
            parts.append(self.district.name)
        if self.address:
            parts.append(self.address)
        return "، ".join(parts) if parts else "—"

    @property
    def display_name(self) -> str:
        """Full display: نمایندگی اصفهان - اصفهان"""
        parts = [self.full_name]
        if self.city:
            city_name = self.city.name
            parts.append(f"- {city_name}")
            if self.province and self.province.name != city_name:
                parts.append(f"({self.province.name})")
        return " ".join(parts)

    @property
    def type_label(self) -> str:
        if self.is_warehouse:
            return "انبار مرکزی"
        return self.tier_name

    @property
    def type_icon(self) -> str:
        if self.is_warehouse:
            return "bi-box-seam"
        return "bi-shop"

    @property
    def type_color(self) -> str:
        if self.is_warehouse:
            return "primary"
        return "success"

    def __repr__(self):
        return f"<Dealer {self.full_name} ({self.mobile})>"


# ==========================================
# Dealer Sale (POS)
# ==========================================

class DealerSale(Base):
    __tablename__ = "dealer_sales"

    id = Column(Integer, primary_key=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="CASCADE"), nullable=False, index=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String, nullable=True)
    customer_mobile = Column(String(15), nullable=True)
    customer_national_id = Column(String, nullable=True)
    sale_price = Column(BigInteger, nullable=False)           # ریال
    commission_amount = Column(BigInteger, default=0, nullable=False)  # ریال (legacy)
    gold_profit_mg = Column(BigInteger, default=0, nullable=False)    # سود طلایی (میلی‌گرم)
    discount_wage_percent = Column(Numeric(5, 2), default=0, nullable=False)  # تخفیف اجرت از سهم نماینده (درصد)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dealer = relationship("Dealer", back_populates="sales")
    bar = relationship("Bar", foreign_keys=[bar_id])


# ==========================================
# Buyback Request
# ==========================================

class BuybackRequest(Base):
    __tablename__ = "buyback_requests"

    id = Column(Integer, primary_key=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="CASCADE"), nullable=False, index=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String, nullable=True)
    customer_mobile = Column(String(15), nullable=True)
    buyback_price = Column(BigInteger, nullable=False)        # ریال - مبلغ پیشنهادی بازخرید
    status = Column(String, default=BuybackStatus.PENDING, nullable=False)
    admin_note = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    wage_refund_amount = Column(BigInteger, default=0, nullable=False)      # اعتبار اجرت واریزشده (ریال)
    wage_refund_customer_id = Column(Integer, nullable=True)                 # مشتری دریافت‌کننده اعتبار
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    dealer = relationship("Dealer", back_populates="buybacks")
    bar = relationship("Bar", foreign_keys=[bar_id])

    @property
    def status_label(self) -> str:
        labels = {
            BuybackStatus.PENDING: "در انتظار بررسی",
            BuybackStatus.APPROVED: "تایید شده",
            BuybackStatus.COMPLETED: "تسویه شده",
            BuybackStatus.REJECTED: "رد شده",
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        colors = {
            BuybackStatus.PENDING: "warning",
            BuybackStatus.APPROVED: "info",
            BuybackStatus.COMPLETED: "success",
            BuybackStatus.REJECTED: "danger",
        }
        return colors.get(self.status, "secondary")
