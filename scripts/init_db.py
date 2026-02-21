"""
TalaMala v4 - Database Initialization
=======================================
Creates all tables if they don't exist.
Safe to run multiple times (CREATE IF NOT EXISTS).

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --drop   # Drop and recreate all tables
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import Base, engine

# Import ALL models so Base.metadata knows about them
from modules.user.models import User  # noqa
from modules.admin.models import SystemSetting  # noqa
from modules.customer.address_models import GeoProvince, GeoCity, GeoDistrict, CustomerAddress  # noqa
from modules.catalog.models import (  # noqa
    Product, ProductCategory, ProductImage, ProductTierWage,
    CardDesign, CardDesignImage,
    PackageType, PackageTypeImage, Batch, BatchImage,
)
from modules.inventory.models import (  # noqa
    Bar, BarImage, OwnershipHistory, DealerTransfer, BarTransfer,
)
from modules.cart.models import Cart, CartItem  # noqa
from modules.order.models import Order, OrderItem  # noqa
from modules.wallet.models import Account, LedgerEntry, WalletTopup, WithdrawalRequest  # noqa
from modules.coupon.models import Coupon, CouponMobile, CouponUsage, CouponCategory  # noqa
from modules.dealer.models import DealerTier, DealerSale, BuybackRequest  # noqa
from modules.ticket.models import Ticket, TicketMessage, TicketAttachment  # noqa


def init_db(drop_first=False):
    if drop_first:
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("Done.")

    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)

    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nTables in database ({len(tables)}):")
    for t in sorted(tables):
        print(f"  - {t}")
    print("\nDatabase initialized successfully!")


if __name__ == "__main__":
    drop = "--drop" in sys.argv
    if drop:
        confirm = input("This will DROP all tables. Type 'yes': ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    init_db(drop_first=drop)
