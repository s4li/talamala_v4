"""
Admin Dashboard Service
=========================
Aggregated statistics for the admin dashboard.
"""

from datetime import timedelta
from typing import Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, cast, Date

from modules.order.models import Order, OrderItem
from modules.inventory.models import Bar, BarStatus
from modules.user.models import User
from modules.catalog.models import Product
from modules.wallet.models import Account, WithdrawalRequest, WithdrawalStatus
from modules.dealer.models import DealerSale, BuybackRequest, BuybackStatus
from modules.admin.models import SystemSetting
from common.helpers import now_utc


class DashboardService:

    def get_overview_stats(self, db: Session) -> Dict[str, Any]:
        """Key business metrics."""
        now = now_utc()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today_start - timedelta(days=7)
        month_ago = today_start - timedelta(days=30)

        # Orders
        total_orders = db.query(Order).count()
        paid_orders = db.query(Order).filter(Order.status == "Paid").count()
        pending_orders = db.query(Order).filter(Order.status == "Pending").count()
        today_orders = db.query(Order).filter(Order.created_at >= today_start).count()

        # Revenue (from paid orders)
        total_revenue = (
            db.query(sa_func.coalesce(sa_func.sum(Order.total_amount), 0))
            .filter(Order.paid_at.isnot(None))
            .scalar()
        )
        today_revenue = (
            db.query(sa_func.coalesce(sa_func.sum(Order.total_amount), 0))
            .filter(Order.paid_at.isnot(None), Order.paid_at >= today_start)
            .scalar()
        )
        month_revenue = (
            db.query(sa_func.coalesce(sa_func.sum(Order.total_amount), 0))
            .filter(Order.paid_at.isnot(None), Order.paid_at >= month_ago)
            .scalar()
        )

        # Inventory
        total_bars = db.query(Bar).count()
        available_bars = db.query(Bar).filter(Bar.status == BarStatus.ASSIGNED).count()
        sold_bars = db.query(Bar).filter(Bar.status == BarStatus.SOLD).count()
        reserved_bars = db.query(Bar).filter(Bar.status == BarStatus.RESERVED).count()

        # Customers
        total_customers = db.query(User).filter(User.is_dealer == False, User.is_admin == False).count()

        # Products
        total_products = db.query(Product).filter(Product.is_active == True).count()

        # Wallets
        total_wallet_balance = (
            db.query(sa_func.coalesce(sa_func.sum(Account.balance), 0)).scalar()
        )
        pending_withdrawals = (
            db.query(WithdrawalRequest)
            .filter(WithdrawalRequest.status == WithdrawalStatus.PENDING)
            .count()
        )

        # Dealers
        total_dealers = db.query(User).filter(User.is_dealer == True).count()
        active_dealers = db.query(User).filter(User.is_dealer == True, User.is_active == True).count()
        dealer_total_sales = db.query(DealerSale).count()
        pending_buybacks = (
            db.query(BuybackRequest)
            .filter(BuybackRequest.status == BuybackStatus.PENDING)
            .count()
        )

        # Gold price (from Asset table — display only, no staleness block)
        from modules.pricing.service import get_price_value, is_price_fresh
        from modules.pricing.models import GOLD_18K
        gold_price = get_price_value(db, GOLD_18K)
        gold_price_fresh = is_price_fresh(db, GOLD_18K)

        return {
            # Orders
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "pending_orders": pending_orders,
            "today_orders": today_orders,
            # Revenue
            "total_revenue": total_revenue,
            "today_revenue": today_revenue,
            "month_revenue": month_revenue,
            # Inventory
            "total_bars": total_bars,
            "available_bars": available_bars,
            "sold_bars": sold_bars,
            "reserved_bars": reserved_bars,
            # Customers
            "total_customers": total_customers,
            # Products
            "total_products": total_products,
            # Wallet
            "total_wallet_balance": total_wallet_balance,
            "pending_withdrawals": pending_withdrawals,
            # Dealers
            "total_dealers": total_dealers,
            "active_dealers": active_dealers,
            "dealer_total_sales": dealer_total_sales,
            "pending_buybacks": pending_buybacks,
            # Gold
            "gold_price": gold_price,
            "gold_price_fresh": gold_price_fresh,
        }

    def get_recent_orders(self, db: Session, limit: int = 10) -> List[Order]:
        """Most recent orders for dashboard feed."""
        return (
            db.query(Order)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_daily_revenue(self, db: Session, days: int = 30) -> List[Dict[str, Any]]:
        """Daily revenue for the chart (last N days)."""
        now = now_utc()
        start = now - timedelta(days=days)

        rows = (
            db.query(
                cast(Order.paid_at, Date).label("day"),
                sa_func.count(Order.id).label("count"),
                sa_func.coalesce(sa_func.sum(Order.total_amount), 0).label("revenue"),
            )
            .filter(Order.paid_at.isnot(None), Order.paid_at >= start)
            .group_by(cast(Order.paid_at, Date))
            .order_by(cast(Order.paid_at, Date))
            .all()
        )

        return [
            {"date": str(r.day), "count": r.count, "revenue": int(r.revenue)}
            for r in rows
        ]

    def get_inventory_by_status(self, db: Session) -> Dict[str, int]:
        """Bar counts grouped by status for pie chart."""
        rows = (
            db.query(Bar.status, sa_func.count(Bar.id))
            .group_by(Bar.status)
            .all()
        )
        return {str(status): count for status, count in rows}


dashboard_service = DashboardService()
