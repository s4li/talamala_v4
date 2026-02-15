"""
Inventory Module - Models
==========================
Bar: Physical gold bar with serial code and lifecycle status.
BarImage: Photos of each bar.
OwnershipHistory: Tracks ownership changes over time.
DealerTransfer: History of bar movements between dealers/warehouses.
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


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

    # Dealer/warehouse tracking (dealer IS the location)
    dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="SET NULL"), nullable=True)

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
    dealer_location = relationship("Dealer", foreign_keys=[dealer_id])

    images = relationship("BarImage", back_populates="bar", cascade="all, delete-orphan")
    history = relationship("OwnershipHistory", back_populates="bar", cascade="all, delete-orphan",
                          order_by="OwnershipHistory.transfer_date.desc()")
    transfers = relationship("DealerTransfer", back_populates="bar", cascade="all, delete-orphan",
                            order_by="DealerTransfer.transferred_at.desc()")

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
# Dealer Transfer History (bar movement between dealers/warehouses)
# ==========================================

class DealerTransfer(Base):
    __tablename__ = "dealer_location_transfers"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False)
    from_dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="SET NULL"), nullable=True)
    to_dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="SET NULL"), nullable=True)
    transferred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    transferred_by = Column(String, nullable=True)   # نام اپراتور / سیستم
    description = Column(String, nullable=True)       # توضیح: "ارسال با پست پیشتاز"

    bar = relationship("Bar", back_populates="transfers")
    from_dealer = relationship("Dealer", foreign_keys=[from_dealer_id])
    to_dealer = relationship("Dealer", foreign_keys=[to_dealer_id])


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
