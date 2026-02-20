"""
Wallet Module - Models
========================
Double-entry ledger system for customer & dealer wallets.

Models:
  - Account: Per-owner balance (IRR or XAU_MG) — polymorphic (customer/dealer)
  - LedgerEntry: Immutable audit trail (every balance change)
  - WalletTopup: Online charge requests (linked to payment gateways)
  - WithdrawalRequest: Customer cash-out requests (admin approval)

Enums:
  - OwnerType: customer / dealer
  - AssetCode: IRR (ریال), XAU_MG (طلا میلی‌گرم)
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

class OwnerType(str, enum.Enum):
    CUSTOMER = "customer"
    DEALER = "dealer"


class AssetCode(str, enum.Enum):
    IRR = "IRR"         # ریال (نمایش تومانی)
    XAU_MG = "XAU_MG"  # طلا به میلی‌گرم


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
# Account (balance per owner per asset)
# ==========================================

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    owner_type = Column(String, nullable=False, default=OwnerType.CUSTOMER)
    owner_id = Column(Integer, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True)  # backward compat
    asset_code = Column(String, nullable=False)
    balance = Column(BigInteger, default=0, nullable=False)
    locked_balance = Column(BigInteger, default=0, nullable=False)
    credit_balance = Column(BigInteger, default=0, nullable=False)  # اعتبار غیرقابل برداشت
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer")
    entries = relationship("LedgerEntry", back_populates="account", order_by="LedgerEntry.created_at.desc()")

    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", "asset_code", name="uq_account_owner_asset"),
        CheckConstraint("balance >= 0", name="ck_account_balance_nonneg"),
        CheckConstraint("locked_balance >= 0", name="ck_account_locked_nonneg"),
        CheckConstraint("credit_balance >= 0", name="ck_account_credit_nonneg"),
        Index("ix_account_owner", "owner_type", "owner_id", "asset_code"),
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
        if self.owner_type == OwnerType.CUSTOMER:
            return f"مشتری #{self.owner_id}"
        return f"نماینده #{self.owner_id}"


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
    def txn_type_label(self) -> str:
        # Context-aware labels based on reference_type
        ref = self.reference_type or ""
        if ref == "pos_gold_profit":
            return "واریز سود"
        if ref == "gold_buy":
            return "خرید طلا"
        if ref == "gold_sell":
            if self.txn_type == TransactionType.DEPOSIT:
                return "واریز"
            return "فروش طلا"
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
        if ref == "gold_buy":
            return "warning"
        if ref == "gold_sell":
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
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_irr = Column(BigInteger, nullable=False)
    track_id = Column(String, unique=True, nullable=True)
    ref_number = Column(String, nullable=True)
    status = Column(String, default="PENDING", nullable=False)  # PENDING/PAID/FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    customer = relationship("Customer")


# ==========================================
# WithdrawalRequest (customer → admin → bank)
# ==========================================

class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True)
    owner_type = Column(String, default=OwnerType.CUSTOMER, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="CASCADE"), nullable=True, index=True)
    amount_irr = Column(BigInteger, nullable=False)
    shaba_number = Column(String, nullable=False)
    account_holder = Column(String, nullable=True)
    status = Column(String, default=WithdrawalStatus.PENDING.value, nullable=False)
    admin_note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer")
    dealer = relationship("Dealer")

    @property
    def owner_id(self) -> int:
        if self.owner_type == OwnerType.DEALER:
            return self.dealer_id
        return self.customer_id

    @property
    def owner_name(self) -> str:
        if self.owner_type == OwnerType.DEALER and self.dealer:
            return self.dealer.full_name
        if self.customer:
            return self.customer.full_name or self.customer.mobile
        return "---"

    @property
    def owner_mobile(self) -> str:
        if self.owner_type == OwnerType.DEALER and self.dealer:
            return self.dealer.mobile
        if self.customer:
            return self.customer.mobile
        return ""

    @property
    def owner_type_label(self) -> str:
        if self.owner_type == OwnerType.DEALER:
            return "نماینده"
        return "مشتری"

    @property
    def owner_type_color(self) -> str:
        if self.owner_type == OwnerType.DEALER:
            return "info"
        return "secondary"

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
