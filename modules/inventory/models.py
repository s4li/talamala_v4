"""
Inventory Module - Models
==========================
Bar: Physical gold bar with serial code and lifecycle status.
BarImage: Photos of each bar.
OwnershipHistory: Tracks ownership changes over time.
DealerTransfer: History of bar movements between dealers/warehouses.
ReconciliationSession / ReconciliationItem: Inventory count & mismatch detection.
CustodialDeliveryRequest: Customer-initiated physical delivery of custodial bars.
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Numeric,
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
# Transfer Type (reason for physical bar movement)
# ==========================================

class TransferType(str, enum.Enum):
    MANUAL = "Manual"                         # دستی (ادمین)
    B2B_FULFILLMENT = "B2BFulfillment"        # تحویل سفارش عمده
    ADMIN_TRANSFER = "AdminTransfer"          # انتقال ادمین
    RECONCILIATION = "Reconciliation"         # تعدیل انبارگردانی
    CUSTODIAL_DELIVERY = "CustodialDelivery"  # تحویل امانی به مشتری
    RETURN = "Return"                         # بازگشت به انبار


# ==========================================
# Bar
# ==========================================

class Bar(Base):
    __tablename__ = "bars"

    id = Column(Integer, primary_key=True, index=True)
    serial_code = Column(String(8), unique=True, index=True, nullable=False)
    status = Column(String, default=BarStatus.RAW, nullable=False)

    # Foreign keys to catalog + user
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True)

    # Dealer/warehouse tracking (dealer IS the location)
    dealer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Claim code (for POS sales and gift orders)
    claim_code = Column(String(8), unique=True, nullable=True, index=True)

    # Reservation fields
    reserved_customer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reserved_until = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Physical delivery timestamp (NULL = not yet delivered = "امانی")
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    customer = relationship("User", foreign_keys=[customer_id])
    batch = relationship("Batch", foreign_keys=[batch_id])
    dealer_location = relationship("User", foreign_keys=[dealer_id])

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
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False, index=True)

    bar = relationship("Bar", back_populates="images")


# ==========================================
# Ownership History
# ==========================================

class OwnershipHistory(Base):
    __tablename__ = "ownership_history"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    new_owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    transfer_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    description = Column(String, nullable=True)

    bar = relationship("Bar", back_populates="history")
    previous_owner = relationship("User", foreign_keys=[previous_owner_id])
    new_owner = relationship("User", foreign_keys=[new_owner_id])


# ==========================================
# Dealer Transfer History (bar movement between dealers/warehouses)
# ==========================================

class DealerTransfer(Base):
    __tablename__ = "dealer_location_transfers"

    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False, index=True)
    from_dealer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    to_dealer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    transferred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    transferred_by = Column(String, nullable=True)   # نام اپراتور / سیستم
    description = Column(String, nullable=True)       # توضیح: "ارسال با پست پیشتاز"

    # Phase 22: structured transfer audit
    transfer_type = Column(String(30), default=TransferType.MANUAL, nullable=False)
    reference_type = Column(String(50), nullable=True)   # e.g. "b2b_order", "reconciliation_session"
    reference_id = Column(Integer, nullable=True)         # ID of the referenced entity

    bar = relationship("Bar", back_populates="transfers")
    from_dealer = relationship("User", foreign_keys=[from_dealer_id])
    to_dealer = relationship("User", foreign_keys=[to_dealer_id])

    @property
    def transfer_type_label(self) -> str:
        labels = {
            TransferType.MANUAL: "دستی",
            TransferType.B2B_FULFILLMENT: "تحویل سفارش عمده",
            TransferType.ADMIN_TRANSFER: "انتقال ادمین",
            TransferType.RECONCILIATION: "تعدیل انبارگردانی",
            TransferType.CUSTODIAL_DELIVERY: "تحویل امانی",
            TransferType.RETURN: "بازگشت به انبار",
        }
        return labels.get(self.transfer_type, str(self.transfer_type))

    @property
    def transfer_type_color(self) -> str:
        colors = {
            TransferType.MANUAL: "secondary",
            TransferType.B2B_FULFILLMENT: "primary",
            TransferType.ADMIN_TRANSFER: "info",
            TransferType.RECONCILIATION: "warning",
            TransferType.CUSTODIAL_DELIVERY: "success",
            TransferType.RETURN: "danger",
        }
        return colors.get(self.transfer_type, "secondary")


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
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False, index=True)
    from_customer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    to_mobile = Column(String(11), nullable=False)
    otp_hash = Column(String, nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default=TransferStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bar = relationship("Bar")
    from_customer = relationship("User", foreign_keys=[from_customer_id])


# ==========================================
# Reconciliation (انبارگردانی)
# ==========================================

class ReconciliationStatus(str, enum.Enum):
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class ReconciliationItemStatus(str, enum.Enum):
    MATCHED = "Matched"        # اسکن شده و تطابق دارد
    MISSING = "Missing"        # در سیستم هست ولی اسکن نشده
    UNEXPECTED = "Unexpected"  # اسکن شده ولی در سیستم این لوکیشن نیست


class ReconciliationSession(Base):
    __tablename__ = "reconciliation_sessions"

    id = Column(Integer, primary_key=True)
    dealer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    initiated_by = Column(String, nullable=False)
    status = Column(String, default=ReconciliationStatus.IN_PROGRESS, nullable=False)

    # Summary stats (computed on finalize)
    total_expected = Column(Integer, default=0)
    total_scanned = Column(Integer, default=0)
    total_matched = Column(Integer, default=0)
    total_missing = Column(Integer, default=0)
    total_unexpected = Column(Integer, default=0)

    notes = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    dealer = relationship("User", foreign_keys=[dealer_id])
    items = relationship("ReconciliationItem", back_populates="session",
                         cascade="all, delete-orphan",
                         order_by="ReconciliationItem.id.desc()")

    @property
    def status_label(self) -> str:
        labels = {
            ReconciliationStatus.IN_PROGRESS: "در حال انجام",
            ReconciliationStatus.COMPLETED: "تکمیل‌شده",
            ReconciliationStatus.CANCELLED: "لغو‌شده",
        }
        return labels.get(self.status, str(self.status))

    @property
    def status_color(self) -> str:
        colors = {
            ReconciliationStatus.IN_PROGRESS: "warning",
            ReconciliationStatus.COMPLETED: "success",
            ReconciliationStatus.CANCELLED: "secondary",
        }
        return colors.get(self.status, "secondary")

    @property
    def has_mismatches(self) -> bool:
        return (self.total_missing or 0) > 0 or (self.total_unexpected or 0) > 0


class ReconciliationItem(Base):
    __tablename__ = "reconciliation_items"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("reconciliation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="SET NULL"), nullable=True, index=True)
    serial_code = Column(String(12), nullable=False)
    item_status = Column(String(20), nullable=False)
    scanned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    # Snapshot of bar state at scan time
    expected_status = Column(String, nullable=True)
    expected_product = Column(String, nullable=True)

    session = relationship("ReconciliationSession", back_populates="items")
    bar = relationship("Bar")

    @property
    def item_status_label(self) -> str:
        labels = {
            ReconciliationItemStatus.MATCHED: "تطابق",
            ReconciliationItemStatus.MISSING: "مفقود",
            ReconciliationItemStatus.UNEXPECTED: "اضافی",
        }
        return labels.get(self.item_status, str(self.item_status))

    @property
    def item_status_color(self) -> str:
        colors = {
            ReconciliationItemStatus.MATCHED: "success",
            ReconciliationItemStatus.MISSING: "danger",
            ReconciliationItemStatus.UNEXPECTED: "warning",
        }
        return colors.get(self.item_status, "secondary")


# ==========================================
# Custodial Delivery Request (تحویل امانی)
# ==========================================

class CustodialDeliveryStatus(str, enum.Enum):
    PENDING = "Pending"       # درخواست ثبت شده
    COMPLETED = "Completed"   # تحویل شد (OTP تایید)
    CANCELLED = "Cancelled"   # لغو شده
    EXPIRED = "Expired"       # منقضی شده


class CustodialDeliveryRequest(Base):
    __tablename__ = "custodial_delivery_requests"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="CASCADE"), nullable=False, index=True)
    dealer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String, default=CustodialDeliveryStatus.PENDING, nullable=False)

    # OTP for handoff verification (sent to customer mobile)
    otp_hash = Column(String, nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True)

    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(String, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    customer = relationship("User", foreign_keys=[customer_id])
    bar = relationship("Bar")
    dealer = relationship("User", foreign_keys=[dealer_id])

    @property
    def status_label(self) -> str:
        labels = {
            CustodialDeliveryStatus.PENDING: "در انتظار تحویل",
            CustodialDeliveryStatus.COMPLETED: "تحویل داده شده",
            CustodialDeliveryStatus.CANCELLED: "لغو شده",
            CustodialDeliveryStatus.EXPIRED: "منقضی شده",
        }
        return labels.get(self.status, str(self.status))

    @property
    def status_color(self) -> str:
        colors = {
            CustodialDeliveryStatus.PENDING: "warning",
            CustodialDeliveryStatus.COMPLETED: "success",
            CustodialDeliveryStatus.CANCELLED: "secondary",
            CustodialDeliveryStatus.EXPIRED: "danger",
        }
        return colors.get(self.status, "secondary")
