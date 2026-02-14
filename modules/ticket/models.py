"""
Ticket Module - Models
========================
Support ticketing system with conversation threads.

Models:
  - Ticket: A support request from a Customer or Dealer
  - TicketMessage: A message in the conversation thread
  - TicketAttachment: File attached to a message

Enums:
  - TicketStatus: Open / InProgress / Answered / Closed
  - TicketPriority: Low / Medium / High
  - SenderType: CUSTOMER / DEALER / STAFF
  - TicketCategory: Financial / Technical / Sales / Complaints / Other
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Index, Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# Enums
# ==========================================

class TicketStatus(str, enum.Enum):
    OPEN = "Open"                # باز - جدید
    IN_PROGRESS = "InProgress"   # در حال بررسی
    ANSWERED = "Answered"        # پاسخ داده شده
    CLOSED = "Closed"            # بسته شده


class TicketPriority(str, enum.Enum):
    LOW = "Low"         # کم
    MEDIUM = "Medium"   # متوسط
    HIGH = "High"       # بالا


class SenderType(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    DEALER = "DEALER"
    STAFF = "STAFF"


class TicketCategory(str, enum.Enum):
    FINANCIAL = "Financial"       # مالی
    TECHNICAL = "Technical"       # فنی
    SALES = "Sales"               # فروش
    COMPLAINTS = "Complaints"     # شکایات
    OTHER = "Other"               # سایر


# ==========================================
# Ticket
# ==========================================

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    subject = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String, default=TicketCategory.OTHER, nullable=False)

    status = Column(String, default=TicketStatus.OPEN, nullable=False)
    priority = Column(String, default=TicketPriority.MEDIUM, nullable=False)

    # Sender: either a customer or a dealer (exactly one should be set)
    sender_type = Column(String, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="SET NULL"), nullable=True)

    # Assignment to staff
    assigned_to = Column(Integer, ForeignKey("system_users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id])
    dealer = relationship("Dealer", foreign_keys=[dealer_id])
    assigned_staff = relationship("SystemUser", foreign_keys=[assigned_to])
    messages = relationship(
        "TicketMessage", back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketMessage.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_ticket_status_sender", "status", "sender_type"),
        Index("ix_ticket_customer", "customer_id"),
        Index("ix_ticket_dealer", "dealer_id"),
    )

    # --- Display properties ---

    @property
    def sender_name(self) -> str:
        if self.sender_type == SenderType.CUSTOMER and self.customer:
            return self.customer.full_name or "مشتری"
        elif self.sender_type == SenderType.DEALER and self.dealer:
            return self.dealer.full_name
        return "ناشناس"

    @property
    def sender_mobile(self) -> str:
        if self.sender_type == SenderType.CUSTOMER and self.customer:
            return self.customer.mobile
        elif self.sender_type == SenderType.DEALER and self.dealer:
            return self.dealer.mobile
        return ""

    @property
    def status_label(self) -> str:
        return {
            TicketStatus.OPEN: "باز",
            TicketStatus.IN_PROGRESS: "در حال بررسی",
            TicketStatus.ANSWERED: "پاسخ داده شده",
            TicketStatus.CLOSED: "بسته شده",
        }.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        return {
            TicketStatus.OPEN: "primary",
            TicketStatus.IN_PROGRESS: "warning",
            TicketStatus.ANSWERED: "success",
            TicketStatus.CLOSED: "secondary",
        }.get(self.status, "secondary")

    @property
    def priority_label(self) -> str:
        return {
            TicketPriority.LOW: "کم",
            TicketPriority.MEDIUM: "متوسط",
            TicketPriority.HIGH: "بالا",
        }.get(self.priority, self.priority)

    @property
    def priority_color(self) -> str:
        return {
            TicketPriority.LOW: "info",
            TicketPriority.MEDIUM: "warning",
            TicketPriority.HIGH: "danger",
        }.get(self.priority, "secondary")

    @property
    def sender_type_label(self) -> str:
        return {"CUSTOMER": "مشتری", "DEALER": "نماینده"}.get(self.sender_type, self.sender_type)

    @property
    def sender_type_color(self) -> str:
        return {"CUSTOMER": "info", "DEALER": "purple"}.get(self.sender_type, "secondary")

    @property
    def category_label(self) -> str:
        return {
            TicketCategory.FINANCIAL: "مالی",
            TicketCategory.TECHNICAL: "فنی",
            TicketCategory.SALES: "فروش",
            TicketCategory.COMPLAINTS: "شکایات",
            TicketCategory.OTHER: "سایر",
        }.get(self.category, self.category)

    @property
    def category_color(self) -> str:
        return {
            TicketCategory.FINANCIAL: "warning",
            TicketCategory.TECHNICAL: "info",
            TicketCategory.SALES: "success",
            TicketCategory.COMPLAINTS: "danger",
            TicketCategory.OTHER: "secondary",
        }.get(self.category, "secondary")

    @property
    def message_count(self) -> int:
        return len(self.messages) if self.messages else 0

    @property
    def public_message_count(self) -> int:
        """Count of messages visible to customer/dealer (excludes internal notes)."""
        if not self.messages:
            return 0
        return sum(1 for m in self.messages if not m.is_internal)

    def __repr__(self):
        return f"<Ticket #{self.id} [{self.status}] {self.subject[:30]}>"


# ==========================================
# Ticket Message (conversation thread)
# ==========================================

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)

    sender_type = Column(String, nullable=False)       # CUSTOMER / DEALER / STAFF
    sender_name = Column(String(200), nullable=False)  # Denormalized name snapshot
    body = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False, nullable=False)  # یادداشت داخلی (فقط کارکنان)
    is_initial = Column(Boolean, default=False, nullable=False)   # پیام اولیه تیکت (برای پیوست‌ها)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="messages")
    attachments = relationship(
        "TicketAttachment", back_populates="message",
        cascade="all, delete-orphan",
        order_by="TicketAttachment.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_ticket_msg_ticket", "ticket_id"),
    )

    @property
    def sender_type_label(self) -> str:
        return {
            "CUSTOMER": "مشتری",
            "DEALER": "نماینده",
            "STAFF": "پشتیبانی",
        }.get(self.sender_type, self.sender_type)

    @property
    def sender_badge_color(self) -> str:
        return {
            "CUSTOMER": "info",
            "DEALER": "purple",
            "STAFF": "success",
        }.get(self.sender_type, "secondary")

    @property
    def is_staff_message(self) -> bool:
        return self.sender_type == SenderType.STAFF


# ==========================================
# Ticket Attachment (file uploads)
# ==========================================

class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("ticket_messages.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    message = relationship("TicketMessage", back_populates="attachments")

    __table_args__ = (
        Index("ix_ticket_attachment_message", "message_id"),
    )
