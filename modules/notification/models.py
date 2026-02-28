"""
TalaMala v4 - Notification Models
===================================
In-app notification center + user preferences.
"""

import enum

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NotificationType(str, enum.Enum):
    ORDER_STATUS = "ORDER_STATUS"
    ORDER_DELIVERY = "ORDER_DELIVERY"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    WALLET_TOPUP = "WALLET_TOPUP"
    WALLET_WITHDRAW = "WALLET_WITHDRAW"
    WALLET_TRADE = "WALLET_TRADE"
    OWNERSHIP_TRANSFER = "OWNERSHIP_TRANSFER"
    CUSTODIAL_DELIVERY = "CUSTODIAL_DELIVERY"
    TICKET_UPDATE = "TICKET_UPDATE"
    DEALER_SALE = "DEALER_SALE"
    DEALER_BUYBACK = "DEALER_BUYBACK"
    B2B_ORDER = "B2B_ORDER"
    DEALER_REQUEST = "DEALER_REQUEST"
    REVIEW_REPLY = "REVIEW_REPLY"
    SYSTEM = "SYSTEM"


class NotificationChannel(str, enum.Enum):
    SMS = "SMS"
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


# Persian labels for each type (used in settings page)
NOTIFICATION_TYPE_LABELS = {
    NotificationType.ORDER_STATUS: "وضعیت سفارش",
    NotificationType.ORDER_DELIVERY: "ارسال و تحویل",
    NotificationType.PAYMENT_SUCCESS: "پرداخت موفق",
    NotificationType.PAYMENT_FAILED: "پرداخت ناموفق",
    NotificationType.WALLET_TOPUP: "شارژ کیف پول",
    NotificationType.WALLET_WITHDRAW: "درخواست برداشت",
    NotificationType.WALLET_TRADE: "خرید/فروش فلز",
    NotificationType.OWNERSHIP_TRANSFER: "انتقال مالکیت",
    NotificationType.CUSTODIAL_DELIVERY: "تحویل امانی",
    NotificationType.TICKET_UPDATE: "بروزرسانی تیکت",
    NotificationType.DEALER_SALE: "فروش نماینده",
    NotificationType.DEALER_BUYBACK: "بازخرید",
    NotificationType.B2B_ORDER: "سفارش عمده",
    NotificationType.DEALER_REQUEST: "درخواست نمایندگی",
    NotificationType.REVIEW_REPLY: "پاسخ به نظر",
    NotificationType.SYSTEM: "سیستمی",
}

# Bootstrap icon per type
NOTIFICATION_TYPE_ICONS = {
    NotificationType.ORDER_STATUS: "bi-bag-check",
    NotificationType.ORDER_DELIVERY: "bi-truck",
    NotificationType.PAYMENT_SUCCESS: "bi-check-circle",
    NotificationType.PAYMENT_FAILED: "bi-x-circle",
    NotificationType.WALLET_TOPUP: "bi-wallet2",
    NotificationType.WALLET_WITHDRAW: "bi-bank",
    NotificationType.WALLET_TRADE: "bi-arrow-left-right",
    NotificationType.OWNERSHIP_TRANSFER: "bi-arrow-repeat",
    NotificationType.CUSTODIAL_DELIVERY: "bi-box-arrow-in-down",
    NotificationType.TICKET_UPDATE: "bi-headset",
    NotificationType.DEALER_SALE: "bi-receipt",
    NotificationType.DEALER_BUYBACK: "bi-arrow-return-left",
    NotificationType.B2B_ORDER: "bi-cart4",
    NotificationType.DEALER_REQUEST: "bi-person-plus",
    NotificationType.REVIEW_REPLY: "bi-chat-dots",
    NotificationType.SYSTEM: "bi-megaphone",
}

# Badge color per type
NOTIFICATION_TYPE_COLORS = {
    NotificationType.PAYMENT_SUCCESS: "success",
    NotificationType.PAYMENT_FAILED: "danger",
    NotificationType.ORDER_STATUS: "primary",
    NotificationType.ORDER_DELIVERY: "info",
    NotificationType.WALLET_TOPUP: "success",
    NotificationType.WALLET_WITHDRAW: "warning",
    NotificationType.TICKET_UPDATE: "info",
    NotificationType.SYSTEM: "secondary",
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    link = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False, server_default="false", nullable=False)
    channel = Column(String(20), default=NotificationChannel.IN_APP, server_default="IN_APP", nullable=False)
    reference_type = Column(String(100), nullable=True)
    reference_id = Column(String(100), nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_notification_user_unread", "user_id", "is_read"),
        Index("ix_notification_user_created", "user_id", "created_at"),
        Index("ix_notification_ref", "reference_type", "reference_id"),
    )

    @property
    def type_label(self) -> str:
        try:
            return NOTIFICATION_TYPE_LABELS.get(NotificationType(self.notification_type), self.notification_type)
        except ValueError:
            return self.notification_type

    @property
    def type_icon(self) -> str:
        try:
            return NOTIFICATION_TYPE_ICONS.get(NotificationType(self.notification_type), "bi-bell")
        except ValueError:
            return "bi-bell"

    @property
    def type_color(self) -> str:
        try:
            return NOTIFICATION_TYPE_COLORS.get(NotificationType(self.notification_type), "primary")
        except ValueError:
            return "primary"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notification_type = Column(String(50), nullable=False)
    sms_enabled = Column(Boolean, default=True, server_default="true", nullable=False)
    in_app_enabled = Column(Boolean, default=True, server_default="true", nullable=False)
    email_enabled = Column(Boolean, default=False, server_default="false", nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "notification_type", name="uq_notif_pref_user_type"),
        Index("ix_notif_pref_user", "user_id"),
    )
