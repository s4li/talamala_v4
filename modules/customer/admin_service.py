"""
Customer Admin Service
========================
Queries for admin customer management: list, search, stats, detail aggregation.
"""

from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, or_

from modules.customer.models import Customer
from modules.order.models import Order
from modules.wallet.models import Account, WithdrawalRequest, OwnerType, AssetCode
from modules.inventory.models import Bar, BarStatus
from common.helpers import now_utc
from datetime import timedelta


class CustomerAdminService:

    def list_customers(
        self,
        db: Session,
        page: int = 1,
        per_page: int = 30,
        search: str = None,
        status: str = None,
    ) -> Tuple[List[Customer], int]:
        q = db.query(Customer)
        if search:
            term = f"%{search}%"
            q = q.filter(
                or_(
                    Customer.mobile.ilike(term),
                    Customer.national_id.ilike(term),
                    Customer.first_name.ilike(term),
                    Customer.last_name.ilike(term),
                )
            )
        if status == "active":
            q = q.filter(Customer.is_active == True)
        elif status == "inactive":
            q = q.filter(Customer.is_active == False)

        total = q.count()
        customers = (
            q.order_by(Customer.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return customers, total

    def get_customer_stats(self, db: Session) -> Dict[str, Any]:
        now = now_utc()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total = db.query(sa_func.count(Customer.id)).scalar() or 0
        active = (
            db.query(sa_func.count(Customer.id))
            .filter(Customer.is_active == True)
            .scalar()
            or 0
        )
        today_registered = (
            db.query(sa_func.count(Customer.id))
            .filter(Customer.created_at >= today_start)
            .scalar()
            or 0
        )
        with_orders = (
            db.query(sa_func.count(sa_func.distinct(Order.customer_id)))
            .filter(Order.status == "Paid")
            .scalar()
            or 0
        )

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "today_registered": today_registered,
            "with_orders": with_orders,
        }

    def get_customer_detail(self, db: Session, customer_id: int) -> Optional[Customer]:
        return db.query(Customer).filter(Customer.id == customer_id).first()

    def get_customer_summary(self, db: Session, customer_id: int) -> Dict[str, Any]:
        # Orders
        order_count = (
            db.query(sa_func.count(Order.id))
            .filter(Order.customer_id == customer_id)
            .scalar()
            or 0
        )
        total_spent = (
            db.query(sa_func.coalesce(sa_func.sum(Order.total_amount), 0))
            .filter(Order.customer_id == customer_id, Order.status == "Paid")
            .scalar()
        )

        # Wallet IRR
        irr_acct = (
            db.query(Account)
            .filter(
                Account.owner_type == OwnerType.CUSTOMER,
                Account.owner_id == customer_id,
                Account.asset_code == AssetCode.IRR,
            )
            .first()
        )
        irr_balance = irr_acct.balance if irr_acct else 0

        # Wallet XAU_MG
        gold_acct = (
            db.query(Account)
            .filter(
                Account.owner_type == OwnerType.CUSTOMER,
                Account.owner_id == customer_id,
                Account.asset_code == AssetCode.XAU_MG,
            )
            .first()
        )
        gold_balance_mg = gold_acct.balance if gold_acct else 0

        # Bars owned
        bars_owned = (
            db.query(sa_func.count(Bar.id))
            .filter(Bar.customer_id == customer_id, Bar.status == BarStatus.SOLD)
            .scalar()
            or 0
        )

        # Withdrawal requests
        withdrawal_count = (
            db.query(sa_func.count(WithdrawalRequest.id))
            .filter(WithdrawalRequest.customer_id == customer_id)
            .scalar()
            or 0
        )

        return {
            "order_count": order_count,
            "total_spent": total_spent,
            "irr_balance": irr_balance,
            "gold_balance_mg": gold_balance_mg,
            "bars_owned": bars_owned,
            "withdrawal_count": withdrawal_count,
        }

    def get_customer_orders(
        self,
        db: Session,
        customer_id: int,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[Order], int]:
        q = db.query(Order).filter(Order.customer_id == customer_id)
        total = q.count()
        orders = (
            q.order_by(Order.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return orders, total

    def get_customer_withdrawals(
        self,
        db: Session,
        customer_id: int,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[WithdrawalRequest], int]:
        q = db.query(WithdrawalRequest).filter(
            WithdrawalRequest.customer_id == customer_id
        )
        total = q.count()
        items = (
            q.order_by(WithdrawalRequest.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total


    def update_customer(
        self,
        db: Session,
        customer_id: int,
        first_name: str = None,
        last_name: str = None,
        national_id: str = None,
        mobile: str = None,
        birth_date: str = None,
        customer_type: str = None,
        company_name: str = None,
        economic_code: str = None,
        postal_code: str = None,
        address: str = None,
        phone: str = None,
        is_active: bool = None,
    ) -> Dict[str, Any]:
        customer = self.get_customer_detail(db, customer_id)
        if not customer:
            return {"success": False, "error": "مشتری یافت نشد"}

        # Uniqueness: mobile
        if mobile and mobile != customer.mobile:
            dup = db.query(Customer).filter(
                Customer.mobile == mobile, Customer.id != customer_id
            ).first()
            if dup:
                return {"success": False, "error": "این شماره موبایل قبلا ثبت شده است"}

        # Uniqueness: national_id
        if national_id and national_id != (customer.national_id or ""):
            dup = db.query(Customer).filter(
                Customer.national_id == national_id, Customer.id != customer_id
            ).first()
            if dup:
                return {"success": False, "error": "این کد ملی قبلا ثبت شده است"}

        # Apply updates
        if first_name is not None:
            customer.first_name = first_name or None
        if last_name is not None:
            customer.last_name = last_name or None
        if national_id is not None:
            customer.national_id = national_id or customer.national_id
        if mobile is not None:
            customer.mobile = mobile or customer.mobile
        if birth_date is not None:
            customer.birth_date = birth_date or None
        if customer_type and customer_type in ("real", "legal"):
            customer.customer_type = customer_type
            if customer_type == "legal":
                customer.company_name = (company_name or "").strip() or None
                customer.economic_code = (economic_code or "").strip() or None
            else:
                customer.company_name = None
                customer.economic_code = None
        if postal_code is not None:
            customer.postal_code = postal_code or None
        if address is not None:
            customer.address = address or None
        if phone is not None:
            customer.phone = phone or None
        if is_active is not None:
            customer.is_active = is_active

        db.flush()
        return {"success": True, "customer": customer}


customer_admin_service = CustomerAdminService()
