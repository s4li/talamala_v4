"""
PaymentLink — admin-generated payment links for specific users.
"""

import uuid
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from config.database import Base
from common.helpers import now_utc


class PaymentLink(Base):
    __tablename__ = "payment_links"

    id = Column(Integer, primary_key=True)
    token = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount_irr = Column(BigInteger, nullable=False)
    description = Column(String(500), nullable=False)
    gateway = Column(String(50), default="sepehr")
    # pending / paid / expired / cancelled
    status = Column(String(20), default="pending")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    ref_number = Column(String(100), nullable=True)
    track_id = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])

    @property
    def is_paid(self):
        return self.status == "paid"

    @property
    def is_expired(self):
        if self.status == "expired":
            return True
        if self.expires_at and now_utc() > self.expires_at:
            return True
        return False

    @property
    def is_active(self):
        return self.status == "pending" and not self.is_expired

    @property
    def status_label(self):
        return {
            "pending": "در انتظار پرداخت",
            "paid": "پرداخت شده",
            "expired": "منقضی شده",
            "cancelled": "لغو شده",
        }.get(self.status, self.status)

    @property
    def status_color(self):
        return {
            "pending": "warning",
            "paid": "success",
            "expired": "secondary",
            "cancelled": "danger",
        }.get(self.status, "secondary")

    @property
    def gateway_label(self):
        return {
            "sepehr": "سپهر",
            "zibal": "زیبال",
            "top": "تاپ",
            "parsian": "پارسیان",
        }.get(self.gateway, self.gateway)
