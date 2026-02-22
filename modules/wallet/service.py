"""
Wallet Service - Double-Entry Ledger
======================================
Thread-safe, idempotent balance operations.
Supports multi-asset (IRR/XAU_MG/XAG_MG) with unified User model.
Generic precious metal trading via PRECIOUS_METALS registry.

Usage:
    wallet_service.deposit(db, user_id=1, amount=5_000_000, reference_type="topup", reference_id="123")
    wallet_service.deposit(db, 5, 100, asset_code=AssetCode.XAU_MG)
    wallet_service.buy_metal(db, user_id=1, amount_irr=1_000_000, asset_type="gold", fee_percent=2.0)
    wallet_service.buy_metal(db, user_id=1, amount_irr=500_000, asset_type="silver", fee_percent=1.5)
"""

import uuid
from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func

from modules.wallet.models import (
    Account, LedgerEntry, WalletTopup, WithdrawalRequest,
    AssetCode, TransactionType, WithdrawalStatus, PRECIOUS_METALS,
)
from modules.user.models import User
from common.helpers import now_utc


class WalletService:
    """Stateless service — call methods with db session."""

    # ------------------------------------------
    # Account helpers
    # ------------------------------------------

    def get_or_create_account(
        self, db: Session, user_id: int,
        asset_code: str = AssetCode.IRR,
    ) -> Account:
        """Get existing account or create with zero balance."""
        acct = (
            db.query(Account)
            .filter(
                Account.user_id == user_id,
                Account.asset_code == asset_code,
            )
            .with_for_update()
            .first()
        )
        if not acct:
            acct = Account(
                user_id=user_id,
                asset_code=asset_code,
                balance=0,
                locked_balance=0,
            )
            db.add(acct)
            db.flush()
        return acct

    def get_account(
        self, db: Session, user_id: int,
        asset_code: str = AssetCode.IRR,
    ) -> Optional[Account]:
        """Get account without creating."""
        return (
            db.query(Account)
            .filter(
                Account.user_id == user_id,
                Account.asset_code == asset_code,
            )
            .first()
        )

    def get_balance(
        self, db: Session, user_id: int,
        asset_code: str = AssetCode.IRR,
    ) -> Dict[str, int]:
        """Return balance summary."""
        acct = self.get_account(db, user_id, asset_code)
        if not acct:
            return {"balance": 0, "locked": 0, "available": 0, "credit": 0, "withdrawable": 0}
        return {
            "balance": acct.balance,
            "locked": acct.locked_balance,
            "available": acct.available_balance,
            "credit": acct.credit_balance,
            "withdrawable": acct.withdrawable_balance,
        }

    # ------------------------------------------
    # Core ledger writer
    # ------------------------------------------

    def _write_entry(
        self,
        db: Session,
        account: Account,
        txn_type: str,
        delta_balance: int,
        delta_locked: int,
        idempotency_key: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
        delta_credit: int = 0,
    ) -> LedgerEntry:
        """Create immutable ledger entry and update account atomically."""
        # Idempotency check
        existing = db.query(LedgerEntry).filter(LedgerEntry.idempotency_key == idempotency_key).first()
        if existing:
            return existing

        # Apply deltas
        account.balance += delta_balance
        account.locked_balance += delta_locked
        account.credit_balance += delta_credit

        # Safety checks
        if account.balance < 0:
            raise ValueError(f"موجودی کافی نیست (balance would be {account.balance})")
        if account.locked_balance < 0:
            raise ValueError(f"بلوکه منفی (locked would be {account.locked_balance})")
        if account.credit_balance < 0:
            raise ValueError(f"اعتبار منفی (credit would be {account.credit_balance})")
        # Credit cannot exceed total balance
        if account.credit_balance > account.balance:
            account.credit_balance = account.balance

        entry = LedgerEntry(
            account_id=account.id,
            txn_type=txn_type,
            delta_balance=delta_balance,
            delta_locked=delta_locked,
            delta_credit=delta_credit,
            balance_after=account.balance,
            locked_after=account.locked_balance,
            credit_after=account.credit_balance,
            idempotency_key=idempotency_key,
            reference_type=reference_type,
            reference_id=str(reference_id) if reference_id else None,
            description=description,
        )
        db.add(entry)
        db.flush()
        return entry

    def _gen_key(self, prefix: str, ref_type: str = "", ref_id: str = "") -> str:
        """Generate idempotency key."""
        if ref_type and ref_id:
            return f"{prefix}:{ref_type}:{ref_id}"
        return f"{prefix}:{uuid.uuid4().hex[:12]}"

    # ------------------------------------------
    # Public operations
    # ------------------------------------------

    def deposit(
        self,
        db: Session,
        user_id: int,
        amount: int,
        reference_type: str = "manual",
        reference_id: str = "",
        description: str = "واریز",
        asset_code: str = AssetCode.IRR,
        idempotency_key: Optional[str] = None,
    ) -> LedgerEntry:
        """Add funds to user balance."""
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد")
        acct = self.get_or_create_account(db, user_id, asset_code)
        key = idempotency_key or self._gen_key("deposit", reference_type, reference_id)
        return self._write_entry(
            db, acct, TransactionType.DEPOSIT,
            delta_balance=amount, delta_locked=0,
            idempotency_key=key,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )

    def hold(
        self,
        db: Session,
        user_id: int,
        amount: int,
        reference_type: str = "order",
        reference_id: str = "",
        description: str = "بلوکه برای سفارش",
        asset_code: str = AssetCode.IRR,
    ) -> LedgerEntry:
        """Lock funds (available -> locked). For order reservations."""
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد")
        acct = self.get_or_create_account(db, user_id, asset_code)
        if acct.withdrawable_balance < amount:
            raise ValueError(f"موجودی قابل برداشت کافی نیست (withdrawable={acct.withdrawable_balance}, need={amount})")
        key = self._gen_key("hold", reference_type, reference_id)
        return self._write_entry(
            db, acct, TransactionType.HOLD,
            delta_balance=0, delta_locked=amount,
            idempotency_key=key,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )

    def commit(
        self,
        db: Session,
        user_id: int,
        amount: int,
        reference_type: str = "order",
        reference_id: str = "",
        description: str = "تسویه سفارش",
        asset_code: str = AssetCode.IRR,
    ) -> LedgerEntry:
        """Finalize held funds (deduct from both balance & locked)."""
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد")
        acct = self.get_or_create_account(db, user_id, asset_code)
        key = self._gen_key("commit", reference_type, reference_id)
        return self._write_entry(
            db, acct, TransactionType.COMMIT,
            delta_balance=-amount, delta_locked=-amount,
            idempotency_key=key,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )

    def release(
        self,
        db: Session,
        user_id: int,
        amount: int,
        reference_type: str = "order",
        reference_id: str = "",
        description: str = "آزادسازی بلوکه",
        asset_code: str = AssetCode.IRR,
    ) -> LedgerEntry:
        """Release held funds back to available."""
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد")
        acct = self.get_or_create_account(db, user_id, asset_code)
        key = self._gen_key("release", reference_type, reference_id)
        return self._write_entry(
            db, acct, TransactionType.RELEASE,
            delta_balance=0, delta_locked=-amount,
            idempotency_key=key,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )

    def withdraw(
        self,
        db: Session,
        user_id: int,
        amount: int,
        reference_type: str = "withdrawal",
        reference_id: str = "",
        description: str = "برداشت",
        asset_code: str = AssetCode.IRR,
        idempotency_key: Optional[str] = None,
        consume_credit: bool = True,
    ) -> LedgerEntry:
        """Deduct from available balance.

        consume_credit=True: can spend credit (for purchases). Regular money first, then credit.
        consume_credit=False: cannot touch credit (for bank withdrawals).
        """
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد")
        acct = self.get_or_create_account(db, user_id, asset_code)

        if consume_credit:
            # Can spend entire available_balance (including credit)
            if acct.available_balance < amount:
                raise ValueError("موجودی آزاد کافی نیست")
            # Calculate credit consumption: regular money used first
            regular_available = max(0, acct.available_balance - acct.credit_balance)
            credit_consumed = max(0, amount - regular_available)
            credit_consumed = min(credit_consumed, acct.credit_balance)
        else:
            # Bank withdrawal: cannot touch credit
            if acct.withdrawable_balance < amount:
                raise ValueError("موجودی قابل برداشت کافی نیست")
            credit_consumed = 0

        key = idempotency_key or self._gen_key("withdraw", reference_type, reference_id)
        return self._write_entry(
            db, acct, TransactionType.WITHDRAW,
            delta_balance=-amount, delta_locked=0,
            idempotency_key=key,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
            delta_credit=-credit_consumed,
        )

    def refund(
        self,
        db: Session,
        user_id: int,
        amount: int,
        reference_type: str = "order",
        reference_id: str = "",
        description: str = "بازگشت وجه",
        asset_code: str = AssetCode.IRR,
        idempotency_key: Optional[str] = None,
    ) -> LedgerEntry:
        """Refund funds back to user balance."""
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد")
        acct = self.get_or_create_account(db, user_id, asset_code)
        key = idempotency_key or self._gen_key("refund", reference_type, reference_id)
        return self._write_entry(
            db, acct, TransactionType.REFUND,
            delta_balance=amount, delta_locked=0,
            idempotency_key=key,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )

    def deposit_credit(
        self,
        db: Session,
        user_id: int,
        amount: int,
        reference_type: str = "buyback_wage_refund",
        reference_id: str = "",
        description: str = "اعتبار بازگشت اجرت بازخرید",
        asset_code: str = AssetCode.IRR,
        idempotency_key: Optional[str] = None,
    ) -> LedgerEntry:
        """Deposit non-withdrawable credit (increases both balance and credit_balance)."""
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد")
        acct = self.get_or_create_account(db, user_id, asset_code)
        key = idempotency_key or self._gen_key("credit", reference_type, reference_id)
        return self._write_entry(
            db, acct, TransactionType.CREDIT,
            delta_balance=amount, delta_locked=0,
            idempotency_key=key,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
            delta_credit=amount,
        )

    # ------------------------------------------
    # Generic precious metal trading
    # ------------------------------------------

    def _get_metal_price_per_mg(self, db: Session, pricing_code: str) -> float:
        """Metal price per milligram (rial). From Asset table / 1000."""
        from modules.pricing.service import get_price_value, require_fresh_price
        require_fresh_price(db, pricing_code)
        price = get_price_value(db, pricing_code)
        if price <= 0:
            raise ValueError("قیمت فلز گرانبها در تنظیمات سیستم ثبت نشده")
        return price / 1000.0

    def get_fee_for_user(self, db: Session, user, asset_type: str = "gold") -> float:
        """Dynamic trade fee based on user role and asset type.
        Reads {prefix}_fee_dealer_percent / {prefix}_fee_customer_percent from SystemSetting."""
        from modules.admin.models import SystemSetting
        metal = PRECIOUS_METALS.get(asset_type)
        if not metal:
            return 2.0
        prefix = metal["fee_setting_prefix"]
        defaults = {"gold": (2.0, 0.5), "silver": (1.5, 0.3)}
        default_customer, default_dealer = defaults.get(asset_type, (2.0, 0.5))
        if user.is_dealer:
            s = db.query(SystemSetting).filter(SystemSetting.key == f"{prefix}_fee_dealer_percent").first()
            return float(s.value) if s else default_dealer
        else:
            s = db.query(SystemSetting).filter(SystemSetting.key == f"{prefix}_fee_customer_percent").first()
            return float(s.value) if s else default_customer

    def buy_metal(
        self, db: Session, user_id: int, amount_irr: int,
        asset_type: str = "gold", fee_percent: float = 2.0,
    ) -> Dict[str, Any]:
        """Buy precious metal: deduct IRR, credit metal account."""
        from modules.pricing.trade_guard import require_trade_enabled
        metal = PRECIOUS_METALS.get(asset_type)
        if not metal:
            raise ValueError(f"نوع فلز '{asset_type}' شناسایی نشد")
        require_trade_enabled(db, asset_type, "wallet_buy")
        if amount_irr <= 0:
            raise ValueError("مبلغ باید مثبت باشد")

        price_mg = self._get_metal_price_per_mg(db, metal["pricing_code"])
        buy_price = price_mg * (1 + fee_percent / 100)
        metal_mg = int(amount_irr / buy_price)
        if metal_mg <= 0:
            raise ValueError(f"مبلغ وارد شده برای خرید {metal['label']} کافی نیست")
        actual_cost = int(metal_mg * buy_price)

        ref_type = f"{asset_type}_buy"
        desc = f"خرید {metal['label']} ({metal_mg / 1000:.3f} گرم)"
        self.withdraw(
            db, user_id, actual_cost,
            reference_type=ref_type, reference_id="",
            description=desc, consume_credit=True,
        )
        self.deposit(
            db, user_id, metal_mg,
            reference_type=ref_type, reference_id="",
            description=desc, asset_code=metal["asset_code"],
        )
        return {
            "metal_mg": metal_mg,
            "cost_irr": actual_cost,
            "rate_per_mg": buy_price,
            "rate_per_gram": buy_price * 1000,
        }

    def sell_metal(
        self, db: Session, user_id: int, metal_mg: int,
        asset_type: str = "gold", fee_percent: float = 2.0,
    ) -> Dict[str, Any]:
        """Sell precious metal: deduct metal account, credit IRR."""
        from modules.pricing.trade_guard import require_trade_enabled
        metal = PRECIOUS_METALS.get(asset_type)
        if not metal:
            raise ValueError(f"نوع فلز '{asset_type}' شناسایی نشد")
        require_trade_enabled(db, asset_type, "wallet_sell")
        if metal_mg <= 0:
            raise ValueError(f"مقدار {metal['label']} باید مثبت باشد")

        price_mg = self._get_metal_price_per_mg(db, metal["pricing_code"])
        sell_price = price_mg * (1 - fee_percent / 100)
        amount_irr = int(metal_mg * sell_price)
        if amount_irr <= 0:
            raise ValueError(f"مقدار {metal['label']} برای فروش کافی نیست")

        ref_type = f"{asset_type}_sell"
        desc = f"فروش {metal['label']} ({metal_mg / 1000:.3f} گرم)"
        self.withdraw(
            db, user_id, metal_mg,
            reference_type=ref_type, reference_id="",
            description=desc, asset_code=metal["asset_code"],
        )
        self.deposit(
            db, user_id, amount_irr,
            reference_type=ref_type, reference_id="",
            description=desc,
        )
        return {
            "metal_mg": metal_mg,
            "amount_irr": amount_irr,
            "rate_per_mg": sell_price,
            "rate_per_gram": sell_price * 1000,
        }

    def get_metal_rates(self, db: Session, asset_type: str = "gold", fee_percent: float = 2.0) -> Dict[str, Any]:
        """Get current buy/sell rates for a precious metal (per gram)."""
        metal = PRECIOUS_METALS.get(asset_type)
        if not metal:
            return {"buy_per_gram": 0, "sell_per_gram": 0, "fee_percent": 0}
        try:
            price_mg = self._get_metal_price_per_mg(db, metal["pricing_code"])
        except ValueError:
            return {"buy_per_gram": 0, "sell_per_gram": 0, "fee_percent": 0}
        buy_per_gram = int(price_mg * (1 + fee_percent / 100) * 1000)
        sell_per_gram = int(price_mg * (1 - fee_percent / 100) * 1000)
        return {
            "buy_per_gram": buy_per_gram,
            "sell_per_gram": sell_per_gram,
            "fee_percent": fee_percent,
        }

    # ------------------------------------------
    # Transaction history
    # ------------------------------------------

    def get_transactions(
        self,
        db: Session,
        user_id: int,
        asset_code: str = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[LedgerEntry], int]:
        """Get paginated ledger entries. If asset_code is None, returns all assets."""
        if asset_code:
            acct = self.get_account(db, user_id, asset_code)
            if not acct:
                return [], 0
            q = db.query(LedgerEntry).filter(LedgerEntry.account_id == acct.id)
        else:
            # All accounts for this user
            acct_ids = [
                a.id for a in db.query(Account).filter(
                    Account.user_id == user_id,
                ).all()
            ]
            if not acct_ids:
                return [], 0
            q = db.query(LedgerEntry).filter(LedgerEntry.account_id.in_(acct_ids))

        total = q.count()
        entries = (
            q.options(joinedload(LedgerEntry.account))
            .order_by(LedgerEntry.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return entries, total

    # ------------------------------------------
    # Topup management
    # ------------------------------------------

    def create_topup(
        self, db: Session, user_id: int, amount_irr: int
    ) -> WalletTopup:
        """Create a pending topup request."""
        if amount_irr < 100_000:  # min 10,000 toman
            raise ValueError("حداقل مبلغ شارژ ۱۰,۰۰۰ تومان می‌باشد")
        topup = WalletTopup(
            user_id=user_id,
            amount_irr=amount_irr,
            status="PENDING",
        )
        db.add(topup)
        db.flush()
        return topup

    def confirm_topup(self, db: Session, topup_id: int, ref_number: str) -> WalletTopup:
        """Confirm a successful payment -> credit wallet."""
        topup = db.query(WalletTopup).filter(WalletTopup.id == topup_id).with_for_update().first()
        if not topup:
            raise ValueError("تراکنش شارژ یافت نشد")
        if topup.status != "PENDING":
            raise ValueError("تراکنش قبلاً پردازش شده")

        topup.status = "PAID"
        topup.ref_number = ref_number

        self.deposit(
            db, topup.user_id, topup.amount_irr,
            reference_type="topup", reference_id=str(topup.id),
            description=f"شارژ آنلاین - کد پیگیری {ref_number}",
            idempotency_key=f"topup_confirm:{topup.id}",
        )
        db.flush()
        return topup

    def fail_topup(self, db: Session, topup_id: int) -> WalletTopup:
        """Mark topup as failed."""
        topup = db.query(WalletTopup).filter(WalletTopup.id == topup_id).first()
        if topup and topup.status == "PENDING":
            topup.status = "FAILED"
            db.flush()
        return topup

    # ------------------------------------------
    # Withdrawal management
    # ------------------------------------------

    def create_withdrawal(
        self,
        db: Session,
        user_id: int,
        amount_irr: int,
        shaba_number: str,
        account_holder: str = "",
    ) -> WithdrawalRequest:
        """Create withdrawal request (holds funds immediately)."""
        if amount_irr < 1_000_000:  # min 100,000 toman
            raise ValueError("حداقل مبلغ برداشت ۱۰۰,۰۰۰ تومان می‌باشد")

        # Validate shaba
        shaba_clean = shaba_number.replace(" ", "").strip()
        if not shaba_clean.startswith("IR") or len(shaba_clean) != 26:
            raise ValueError("شماره شبا نامعتبر است (فرمت: IR + ۲۴ رقم)")

        # Check withdrawable balance (excludes non-withdrawable credit)
        bal = self.get_balance(db, user_id)
        if bal["withdrawable"] < amount_irr:
            raise ValueError("موجودی قابل برداشت کافی نیست")

        wr = WithdrawalRequest(
            user_id=user_id,
            amount_irr=amount_irr,
            shaba_number=shaba_clean,
            account_holder=account_holder,
            status=WithdrawalStatus.PENDING,
        )
        db.add(wr)
        db.flush()

        # Hold funds immediately
        self.hold(
            db, user_id, amount_irr,
            reference_type="withdrawal", reference_id=str(wr.id),
            description=f"بلوکه برای درخواست برداشت #{wr.id}",
        )
        return wr

    def approve_withdrawal(self, db: Session, withdrawal_id: int, admin_note: str = "") -> WithdrawalRequest:
        """Admin approves -> deduct held funds."""
        wr = db.query(WithdrawalRequest).filter(WithdrawalRequest.id == withdrawal_id).first()
        if not wr:
            raise ValueError("درخواست برداشت یافت نشد")
        if wr.status != WithdrawalStatus.PENDING:
            raise ValueError("درخواست قبلاً پردازش شده")

        wr.status = WithdrawalStatus.PAID
        wr.admin_note = admin_note

        # Commit the held funds (deduct balance + locked)
        self.commit(
            db, wr.user_id, wr.amount_irr,
            reference_type="withdrawal", reference_id=str(wr.id),
            description=f"تسویه برداشت #{wr.id} به شبا {wr.shaba_number}",
        )
        db.flush()
        return wr

    def reject_withdrawal(self, db: Session, withdrawal_id: int, admin_note: str = "") -> WithdrawalRequest:
        """Admin rejects -> release held funds."""
        wr = db.query(WithdrawalRequest).filter(WithdrawalRequest.id == withdrawal_id).first()
        if not wr:
            raise ValueError("درخواست برداشت یافت نشد")
        if wr.status != WithdrawalStatus.PENDING:
            raise ValueError("درخواست قبلاً پردازش شده")

        wr.status = WithdrawalStatus.REJECTED
        wr.admin_note = admin_note

        # Release held funds
        self.release(
            db, wr.user_id, wr.amount_irr,
            reference_type="withdrawal", reference_id=str(wr.id),
            description=f"آزادسازی بلوکه - رد درخواست برداشت #{wr.id}",
        )
        db.flush()
        return wr

    # ------------------------------------------
    # Admin helpers
    # ------------------------------------------

    def get_all_accounts(
        self, db: Session,
        asset_code: str = AssetCode.IRR,
        page: int = 1,
        per_page: int = 30,
    ) -> Tuple[List[Account], int]:
        """Get all accounts with pagination."""
        q = db.query(Account).filter(Account.asset_code == asset_code)
        total = q.count()
        accounts = (
            q.order_by(Account.balance.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return accounts, total

    def get_pending_withdrawals(self, db: Session) -> List[WithdrawalRequest]:
        """Get all pending withdrawal requests."""
        return (
            db.query(WithdrawalRequest)
            .filter(WithdrawalRequest.status == WithdrawalStatus.PENDING)
            .order_by(WithdrawalRequest.created_at.asc())
            .all()
        )

    def get_all_withdrawals(
        self, db: Session, page: int = 1, per_page: int = 30,
    ) -> Tuple[List[WithdrawalRequest], int]:
        """Get all withdrawal requests with pagination."""
        q = db.query(WithdrawalRequest)
        total = q.count()
        items = (
            q.order_by(WithdrawalRequest.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def admin_adjust(
        self,
        db: Session,
        user_id: int,
        amount: int,
        direction: str,
        description: str = "",
        admin_id: int = 0,
        asset_code: str = AssetCode.IRR,
    ) -> LedgerEntry:
        """Manual admin adjustment (deposit or withdraw)."""
        desc = description or ("واریز دستی مدیر" if direction == "deposit" else "برداشت دستی مدیر")
        ref_id = str(admin_id) if admin_id else ""
        unique_key = f"admin_adjust:{direction}:{user_id}:{uuid.uuid4().hex[:12]}"
        if direction == "deposit":
            return self.deposit(
                db, user_id, amount, "admin_adjust", ref_id, desc,
                asset_code=asset_code,
                idempotency_key=unique_key,
            )
        elif direction == "withdraw":
            return self.withdraw(
                db, user_id, amount, "admin_adjust", ref_id, desc,
                asset_code=asset_code, idempotency_key=unique_key,
            )
        else:
            raise ValueError("نوع عملیات نامعتبر")

    # ------------------------------------------
    # Stats
    # ------------------------------------------

    def get_stats(self, db: Session) -> Dict[str, Any]:
        """Summary stats for admin dashboard."""
        total_accounts = db.query(Account).filter(Account.asset_code == AssetCode.IRR).count()
        total_balance = (
            db.query(sa_func.coalesce(sa_func.sum(Account.balance), 0))
            .filter(Account.asset_code == AssetCode.IRR)
            .scalar()
        )
        total_locked = (
            db.query(sa_func.coalesce(sa_func.sum(Account.locked_balance), 0))
            .filter(Account.asset_code == AssetCode.IRR)
            .scalar()
        )
        pending_withdrawals = (
            db.query(WithdrawalRequest)
            .filter(WithdrawalRequest.status == WithdrawalStatus.PENDING)
            .count()
        )
        gold_accounts = db.query(Account).filter(Account.asset_code == AssetCode.XAU_MG).count()
        gold_balance_mg = (
            db.query(sa_func.coalesce(sa_func.sum(Account.balance), 0))
            .filter(Account.asset_code == AssetCode.XAU_MG)
            .scalar()
        )
        silver_accounts = db.query(Account).filter(Account.asset_code == AssetCode.XAG_MG).count()
        silver_balance_mg = (
            db.query(sa_func.coalesce(sa_func.sum(Account.balance), 0))
            .filter(Account.asset_code == AssetCode.XAG_MG)
            .scalar()
        )
        return {
            "total_accounts": total_accounts,
            "total_balance": total_balance,
            "total_locked": total_locked,
            "pending_withdrawals": pending_withdrawals,
            "gold_accounts": gold_accounts,
            "gold_balance_mg": gold_balance_mg,
            "silver_accounts": silver_accounts,
            "silver_balance_mg": silver_balance_mg,
        }


# Singleton
wallet_service = WalletService()
