"""
Wallet Module - Models
========================
Double-entry ledger system for user wallets.

Models:
  - Account: Per-user balance (IRR, XAU_MG, XAG_MG)
  - LedgerEntry: Immutable audit trail (every balance change)
  - WalletTopup: Online charge requests (linked to payment gateways)
  - WithdrawalRequest: User cash-out requests (admin approval)

Enums:
  - AssetCode: IRR (ریال), XAU_MG (طلا میلی‌گرم), XAG_MG (نقره میلی‌گرم)
  - TransactionType: Deposit/Withdraw/Payment/Refund/Hold/Release/Commit
  - WithdrawalStatus: Pending/Paid/Rejected
"""

import enum
from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, Index, text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# Enums
# ==========================================

class AssetCode(str, enum.Enum):
    IRR = "IRR"         # ریال (نمایش تومانی)
    XAU_MG = "XAU_MG"  # طلا به میلی‌گرم
    XAG_MG = "XAG_MG"  # نقره به میلی‌گرم


# ==========================================
# Precious Metals Registry (generic metadata)
# ==========================================

PRECIOUS_METALS = {
    "gold": {
        "asset_code": "XAU_MG",
        "pricing_code": "gold_18k",
        "label": "طلا",
        "label_en": "gold",
        "unit": "گرم",
        "color": "warning",
        "icon": "bi-gem",
        "fee_setting_prefix": "gold",
    },
    "silver": {
        "asset_code": "XAG_MG",
        "pricing_code": "silver",
        "label": "نقره",
        "label_en": "silver",
        "unit": "گرم",
        "color": "secondary",
        "icon": "bi-diamond",
        "fee_setting_prefix": "silver",
    },
}


class TransactionType(str, enum.Enum):
    DEPOSIT = "Deposit"     # شارژ
    WITHDRAW = "Withdraw"   # برداشت
    PAYMENT = "Payment"     # خرید
    REFUND = "Refund"       # برگشت پول
    HOLD = "Hold"           # بلوکه
    RELEASE = "Release"     # آزاد
    COMMIT = "Commit"       # نهایی
    CREDIT = "Credit"       # اعتبار بازخرید اجرت


class WithdrawalStatus(str, enum.Enum):
    PENDING = "Pending"     # در انتظار بررسی
    PAID = "Paid"           # پرداخت شده
    REJECTED = "Rejected"   # رد شده


# ==========================================
# Account (balance per user per asset)
# ==========================================

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_code = Column(String, nullable=False)
    balance = Column(BigInteger, default=0, nullable=False)
    locked_balance = Column(BigInteger, default=0, nullable=False)
    credit_balance = Column(BigInteger, default=0, nullable=False)  # اعتبار غیرقابل برداشت
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    entries = relationship("LedgerEntry", back_populates="account", order_by="LedgerEntry.created_at.desc()")

    __table_args__ = (
        UniqueConstraint("user_id", "asset_code", name="uq_account_user_asset"),
        CheckConstraint("balance >= 0", name="ck_account_balance_nonneg"),
        CheckConstraint("locked_balance >= 0", name="ck_account_locked_nonneg"),
        CheckConstraint("credit_balance >= 0", name="ck_account_credit_nonneg"),
        Index("ix_account_user_asset", "user_id", "asset_code"),
    )

    @property
    def available_balance(self) -> int:
        """Balance minus locked."""
        return max(0, self.balance - self.locked_balance)

    @property
    def withdrawable_balance(self) -> int:
        """Balance minus locked minus non-withdrawable credit."""
        return max(0, self.balance - self.locked_balance - self.credit_balance)

    @property
    def owner_label(self) -> str:
        if self.user:
            return self.user.display_name
        return f"کاربر #{self.user_id}"


# ==========================================
# LedgerEntry (immutable audit trail)
# ==========================================

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    txn_type = Column(String, nullable=False)
    delta_balance = Column(BigInteger, default=0, nullable=False)
    delta_locked = Column(BigInteger, default=0, nullable=False)
    delta_credit = Column(BigInteger, default=0, nullable=False)
    balance_after = Column(BigInteger, nullable=False)
    locked_after = Column(BigInteger, nullable=False)
    credit_after = Column(BigInteger, default=0, nullable=False)
    idempotency_key = Column(String, nullable=False, unique=True)
    reference_type = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    account = relationship("Account", back_populates="entries")

    __table_args__ = (
        Index("ix_ledger_account_created", "account_id", "created_at"),
    )

    @property
    def asset(self) -> str:
        """Asset code from parent account (IRR or XAU_MG)."""
        return self.account.asset_code if self.account else AssetCode.IRR

    @property
    def is_gold(self) -> bool:
        return self.asset == AssetCode.XAU_MG

    @property
    def is_silver(self) -> bool:
        return self.asset == AssetCode.XAG_MG

    @property
    def is_precious_metal(self) -> bool:
        return self.asset in (AssetCode.XAU_MG, AssetCode.XAG_MG)

    @property
    def txn_type_label(self) -> str:
        # Context-aware labels based on reference_type
        ref = self.reference_type or ""
        if ref == "pos_gold_profit":
            return "واریز سود"
        # Generic metal buy/sell labels (gold_buy, silver_buy, etc.)
        if ref.endswith("_buy"):
            metal_key = ref.rsplit("_buy", 1)[0]
            metal = PRECIOUS_METALS.get(metal_key)
            return f"خرید {metal['label']}" if metal else "خرید"
        if ref.endswith("_sell"):
            if self.txn_type == TransactionType.DEPOSIT:
                return "واریز"
            metal_key = ref.rsplit("_sell", 1)[0]
            metal = PRECIOUS_METALS.get(metal_key)
            return f"فروش {metal['label']}" if metal else "فروش"
        if ref == "topup":
            return "شارژ کیف پول"
        # Fallback to generic labels
        labels = {
            TransactionType.DEPOSIT: "واریز",
            TransactionType.WITHDRAW: "برداشت",
            TransactionType.PAYMENT: "پرداخت سفارش",
            TransactionType.REFUND: "بازگشت وجه",
            TransactionType.HOLD: "بلوکه",
            TransactionType.RELEASE: "آزادسازی",
            TransactionType.COMMIT: "تسویه",
            TransactionType.CREDIT: "اعتبار اجرت",
        }
        return labels.get(self.txn_type, self.txn_type)

    @property
    def txn_type_color(self) -> str:
        ref = self.reference_type or ""
        if ref == "pos_gold_profit":
            return "success"
        if ref.endswith("_buy"):
            return "warning"
        if ref.endswith("_sell"):
            if self.txn_type == TransactionType.DEPOSIT:
                return "success"
            return "info"
        colors = {
            TransactionType.DEPOSIT: "success",
            TransactionType.WITHDRAW: "danger",
            TransactionType.PAYMENT: "warning",
            TransactionType.REFUND: "info",
            TransactionType.HOLD: "secondary",
            TransactionType.RELEASE: "primary",
            TransactionType.COMMIT: "dark",
            TransactionType.CREDIT: "info",
        }
        return colors.get(self.txn_type, "secondary")


# ==========================================
# WalletTopup (online charge via gateway)
# ==========================================

class WalletTopup(Base):
    __tablename__ = "wallet_topups"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_irr = Column(BigInteger, nullable=False)
    track_id = Column(String, unique=True, nullable=True)
    ref_number = Column(String, nullable=True)
    gateway = Column(String, nullable=True)  # zibal/sepehr/top/parsian
    status = Column(String, default="PENDING", nullable=False)  # PENDING/PAID/FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")


# ==========================================
# WithdrawalRequest (user → admin → bank)
# ==========================================

class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_irr = Column(BigInteger, nullable=False)
    shaba_number = Column(String, nullable=False)
    account_holder = Column(String, nullable=True)
    status = Column(String, default=WithdrawalStatus.PENDING.value, nullable=False)
    admin_note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")

    @property
    def owner_name(self) -> str:
        if self.user:
            return self.user.full_name or self.user.mobile
        return "---"

    @property
    def owner_mobile(self) -> str:
        if self.user:
            return self.user.mobile
        return ""

    @property
    def status_label(self) -> str:
        labels = {
            WithdrawalStatus.PENDING: "در انتظار بررسی",
            WithdrawalStatus.PAID: "پرداخت شده",
            WithdrawalStatus.REJECTED: "رد شده",
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        colors = {
            WithdrawalStatus.PENDING: "warning",
            WithdrawalStatus.PAID: "success",
            WithdrawalStatus.REJECTED: "danger",
        }
        return colors.get(self.status, "secondary")
