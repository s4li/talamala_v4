"""
Inventory Module - Models
==========================
Bar: Physical gold bar with serial code and lifecycle status.
BarImage: Photos of each bar.
OwnershipHistory: Tracks ownership changes over time.
Location: Physical places where bars are stored/sold.
LocationTransfer: History of bar movements between locations.
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# Location
# ==========================================

class LocationType(str, enum.Enum):
    FACTORY = "Factory"            # کارخانه
    WAREHOUSE = "Warehouse"        # انبار مرکزی
    BRANCH = "Branch"              # نمایندگی / شعبه
    IN_TRANSIT = "InTransit"       # در حال انتقال
    ONLINE_PLATFORM = "OnlinePlatform"  # انبار دیجیکالا / پلتفرم آنلاین


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)                    # مثل: نمایندگی اصفهان
    location_type = Column(String, default=LocationType.WAREHOUSE, nullable=False)
    province = Column(String, nullable=True)                 # استان
    city = Column(String, nullable=True)                     # شهر
    address = Column(Text, nullable=True)                    # آدرس کامل
    phone = Column(String, nullable=True)                    # تلفن تماس
    is_active = Column(Boolean, default=True, nullable=False)
    is_postal_hub = Column(Boolean, default=False, nullable=False)  # انبار مخصوص ارسال پستی
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def type_label(self) -> str:
        labels = {
            LocationType.FACTORY: "کارخانه",
            LocationType.WAREHOUSE: "انبار مرکزی",
            LocationType.BRANCH: "نمایندگی",
            LocationType.IN_TRANSIT: "در حال انتقال",
            LocationType.ONLINE_PLATFORM: "پلتفرم آنلاین",
        }
        return labels.get(self.location_type, self.location_type)

    @property
    def type_icon(self) -> str:
        icons = {
            LocationType.FACTORY: "bi-building",
            LocationType.WAREHOUSE: "bi-box-seam",
            LocationType.BRANCH: "bi-shop",
            LocationType.IN_TRANSIT: "bi-truck",
            LocationType.ONLINE_PLATFORM: "bi-globe",
        }
        return icons.get(self.location_type, "bi-geo-alt")

    @property
    def type_color(self) -> str:
        colors = {
            LocationType.FACTORY: "dark",
            LocationType.WAREHOUSE: "primary",
            LocationType.BRANCH: "success",
            LocationType.IN_TRANSIT: "warning",
            LocationType.ONLINE_PLATFORM: "info",
        }
        return colors.get(self.location_type, "secondary")

    @property
    def display_name(self) -> str:
        """Full display: نمایندگی اصفهان - اصفهان"""
        parts = [self.name]
        if self.city:
            parts.append(f"- {self.city}")
        if self.province and self.province != self.city:
            parts.append(f"({self.province})")
        return " ".join(parts)

    def __repr__(self):
        return f"<Location {self.name} ({self.location_type})>"


# ==========================================
# Bar Status
# ==========================================

class BarStatus(str, enum.Enum):
    RAW = "Raw"            # خام - فقط سریال دارد
    ASSIGNED = "Assigned"  # اختصاص - محصول تخصیص داده شده
    RESERVED = "Reserved"  # رزرو - در سبد خرید مشتری
    SOLD = "Sold"          # فروخته شده


# ==========================================
# Bar
# ==========================================

class Bar(Base):
    __tablename__ = "bars"

    id = Column(Integer, primary_key=True, index=True)
    serial_code = Column(String(8), unique=True, index=True, nullable=False)
    status = Column(String, default=BarStatus.RAW, nullable=False)

    # Foreign keys to catalog + customer
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="SET NULL"), nullable=True)

    # Location tracking
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    # Claim code (for POS sales and gift orders)
    claim_code = Column(String(8), unique=True, nullable=True, index=True)

    # Reservation fields
    reserved_customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    reserved_until = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    batch = relationship("Batch", foreign_keys=[batch_id])
    location = relationship("Location", foreign_keys=[location_id])

    images = relationship("BarImage", back_populates="bar", cascade="all, delete-orphan")
    history = relationship("OwnershipHistory", back_populates="bar", cascade="all, delete-orphan",
                          order_by="OwnershipHistory.transfer_date.desc()")
    transfers = relationship("LocationTransfer", back_populates="bar", cascade="all, delete-orphan",
                            order_by="LocationTransfer.transferred_at.desc()")

    @property
    def first_image(self):
        return self.images[0].file_path if self.images else None

    @property
    def status_label(self) -> str:
        labels = {
            BarStatus.RAW: "خام",
            BarStatus.ASSIGNED: "اختصاص",
            BarStatus.RESERVED: "رزرو",
            BarStatus.SOLD: "فروخته",
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        colors = {
            BarStatus.RAW: "secondary",
            BarStatus.ASSIGNED: "info",
            BarStatus.RESERVED: "warning",
            BarStatus.SOLD: "success",
        }
        return colors.get(self.status, "secondary")

    def __repr__(self):
        return f"<Bar {self.serial_code} ({self.status})>"


# ==========================================
# Bar Image
# ==========================================

class BarImage(Base):
    __tablename__ = "bar_images"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)

    bar = relationship("Bar", back_populates="images")


# ==========================================
# Ownership History
# ==========================================

class OwnershipHistory(Base):
    __tablename__ = "ownership_history"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    previous_owner_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    new_owner_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    transfer_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    description = Column(String, nullable=True)

    bar = relationship("Bar", back_populates="history")
    previous_owner = relationship("Customer", foreign_keys=[previous_owner_id])
    new_owner = relationship("Customer", foreign_keys=[new_owner_id])


# ==========================================
# Location Transfer History
# ==========================================

class LocationTransfer(Base):
    __tablename__ = "location_transfers"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    from_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    to_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    transferred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    transferred_by = Column(String, nullable=True)   # نام اپراتور / سیستم
    description = Column(String, nullable=True)       # توضیح: "ارسال با پست پیشتاز"

    bar = relationship("Bar", back_populates="transfers")
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])


# ==========================================
# Bar Transfer (Ownership Transfer Request)
# ==========================================

class TransferStatus(str, enum.Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    EXPIRED = "Expired"


class BarTransfer(Base):
    __tablename__ = "bar_transfers"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    from_customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    to_mobile = Column(String(11), nullable=False)
    otp_hash = Column(String, nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default=TransferStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bar = relationship("Bar")
    from_customer = relationship("Customer", foreign_keys=[from_customer_id])
