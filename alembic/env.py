"""
Alembic Environment Configuration
===================================
Reads DATABASE_URL from config.settings (not from alembic.ini).
Imports all models so autogenerate works correctly.
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DATABASE_URL
from config.database import Base

# ==========================================
# Import ALL models here for autogenerate
# ==========================================
from modules.user.models import User  # noqa: F401
from modules.admin.models import SystemSetting, RequestLog  # noqa: F401
from modules.customer.address_models import GeoProvince, GeoCity, GeoDistrict, CustomerAddress  # noqa: F401
from modules.catalog.models import (  # noqa: F401
    ProductCategory, ProductCategoryLink, Product, ProductImage, CardDesign, CardDesignImage,
    PackageType, PackageTypeImage, Batch, BatchImage, ProductTierWage,
)
from modules.inventory.models import Bar, BarImage, OwnershipHistory, DealerTransfer, BarTransfer  # noqa: F401
from modules.cart.models import Cart, CartItem  # noqa: F401
from modules.order.models import Order, OrderItem, OrderStatusLog  # noqa: F401
from modules.wallet.models import Account, LedgerEntry, WalletTopup, WithdrawalRequest  # noqa: F401
from modules.coupon.models import Coupon, CouponMobile, CouponUsage, CouponCategory  # noqa: F401
from modules.dealer.models import DealerTier, DealerSale, BuybackRequest  # noqa: F401
from modules.ticket.models import Ticket, TicketMessage, TicketAttachment  # noqa: F401
from modules.review.models import Review, ReviewImage, ProductComment, CommentImage, CommentLike  # noqa: F401
from modules.dealer_request.models import DealerRequest, DealerRequestAttachment  # noqa: F401
from modules.pricing.models import Asset  # noqa: F401

# Alembic Config
config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
