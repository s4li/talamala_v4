"""
Hedging / Position Management Models
======================================
Tracks the company's net metal exposure (gold, silver) across all channels.
MetalPosition holds the current running balance per metal.
PositionLedger is the immutable audit trail of every change.
"""

import enum

from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.database import Base


# ==========================================
# Enums
# ==========================================

class PositionDirection(str, enum.Enum):
    OUT = "OUT"        # We give metal to customer (balance decreases)
    IN = "IN"          # We receive metal from customer (balance increases)
    HEDGE = "HEDGE"    # Admin records physical market trade
    ADJUST = "ADJUST"  # Manual admin adjustment (initial balance, correction)


# ==========================================
# MetalPosition — Current net position (one row per metal)
# ==========================================

class MetalPosition(Base):
    __tablename__ = "metal_positions"

    id = Column(Integer, primary_key=True)
    metal_type = Column(String(20), nullable=False, unique=True)  # "gold", "silver"
    balance_mg = Column(BigInteger, nullable=False, default=0)     # Signed: negative=short, positive=long
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def balance_grams(self) -> float:
        return (self.balance_mg or 0) / 1000.0

    @property
    def status(self) -> str:
        b = self.balance_mg or 0
        if b < 0:
            return "short"
        elif b > 0:
            return "long"
        return "hedged"

    @property
    def status_label(self) -> str:
        return {
            "short": "کمبود — نیاز به خرید از بازار",
            "long": "مازاد — نیاز به فروش در بازار",
            "hedged": "پوشش کامل",
        }.get(self.status, "")

    @property
    def status_color(self) -> str:
        return {"short": "danger", "long": "info", "hedged": "success"}.get(self.status, "secondary")

    @property
    def metal_label(self) -> str:
        return {"gold": "طلا", "silver": "نقره"}.get(self.metal_type, self.metal_type)


# ==========================================
# PositionLedger — Immutable audit trail
# ==========================================

class PositionLedger(Base):
    __tablename__ = "position_ledger"

    id = Column(Integer, primary_key=True)
    metal_type = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)          # OUT, IN, HEDGE, ADJUST
    amount_mg = Column(BigInteger, nullable=False)           # Always positive (absolute)
    balance_after_mg = Column(BigInteger, nullable=False)    # Signed running balance after this entry
    source_type = Column(String(50), nullable=False)         # order, pos_sale, wallet_buy, wallet_sell, buyback, hedge, admin_adjust
    source_id = Column(String(50), nullable=True)
    description = Column(String(500), nullable=True)
    metal_price_per_gram = Column(BigInteger, nullable=True) # Spot price at time (for hedge records, rial)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    involved_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Customer/dealer involved in this operation
    idempotency_key = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    recorder = relationship("User", foreign_keys=[recorded_by])
    involved_user = relationship("User", foreign_keys=[involved_user_id])

    __table_args__ = (
        Index("ix_pos_ledger_metal_created", "metal_type", "created_at"),
        Index("ix_pos_ledger_source", "source_type", "source_id"),
    )

    @property
    def direction_label(self) -> str:
        return {
            "OUT": "خروج (فروش به مشتری)",
            "IN": "ورود (خرید از مشتری)",
            "HEDGE": "هج (معامله بازار)",
            "ADJUST": "تعدیل دستی",
        }.get(self.direction, self.direction)

    @property
    def direction_color(self) -> str:
        return {
            "OUT": "danger",
            "IN": "success",
            "HEDGE": "primary",
            "ADJUST": "warning",
        }.get(self.direction, "secondary")

    @property
    def source_label(self) -> str:
        return {
            "order": "سفارش فروشگاه",
            "pos_sale": "فروش پوز",
            "wallet_buy": "خرید کیف پول",
            "wallet_sell": "فروش کیف پول",
            "buyback": "بازخرید",
            "hedge": "معامله بازار",
            "admin_adjust": "تعدیل ادمین",
        }.get(self.source_type, self.source_type)

    @property
    def amount_grams(self) -> float:
        return (self.amount_mg or 0) / 1000.0

    @property
    def balance_after_grams(self) -> float:
        return (self.balance_after_mg or 0) / 1000.0

    @property
    def metal_label(self) -> str:
        return {"gold": "طلا", "silver": "نقره"}.get(self.metal_type, self.metal_type)
