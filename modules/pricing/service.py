"""
Pricing Module - Shared Service
==================================
Shared pricing helpers used across shop, cart, order, and dealer modules.
Includes asset price management with staleness guard.
"""

from typing import Tuple

from sqlalchemy.orm import Session

from common.helpers import now_utc
from modules.pricing.models import Asset, GOLD_18K, SILVER


# ==========================================
# Asset Price Helpers
# ==========================================

def get_asset(db: Session, asset_code: str) -> Asset:
    """Get Asset object by code. Raises ValueError if not found."""
    asset = db.query(Asset).filter(Asset.asset_code == asset_code).first()
    if not asset:
        raise ValueError(f"دارایی '{asset_code}' در سیستم تعریف نشده است")
    return asset


def get_price_value(db: Session, asset_code: str) -> int:
    """Get price_per_gram as int. Returns 0 if asset not found."""
    asset = db.query(Asset).filter(Asset.asset_code == asset_code).first()
    return int(asset.price_per_gram) if asset else 0


def is_price_fresh(db: Session, asset_code: str) -> bool:
    """True if asset price is within its staleness threshold."""
    asset = db.query(Asset).filter(Asset.asset_code == asset_code).first()
    if not asset:
        return False
    return asset.is_fresh


def require_fresh_price(db: Session, asset_code: str):
    """Raise ValueError if asset price is stale or missing."""
    asset = db.query(Asset).filter(Asset.asset_code == asset_code).first()
    if not asset:
        raise ValueError(f"قیمت دارایی '{asset_code}' تنظیم نشده است")
    if not asset.is_fresh:
        mins = int(asset.minutes_since_update)
        raise ValueError(
            f"قیمت {asset.asset_label} منقضی شده است "
            f"(آخرین بروزرسانی: {mins} دقیقه پیش). "
            f"لطفاً بعداً تلاش کنید."
        )


def update_asset_price(db: Session, asset_code: str, new_price: int, updated_by: str):
    """Update price + set updated_at to now. Caller must commit."""
    asset = db.query(Asset).filter(Asset.asset_code == asset_code).first()
    if not asset:
        raise ValueError(f"دارایی '{asset_code}' یافت نشد")
    asset.price_per_gram = new_price
    asset.updated_at = now_utc()
    asset.updated_by = updated_by


# ==========================================
# Product Wage Helpers
# ==========================================

def get_product_pricing(db: Session, product):
    """
    Get pricing parameters for a product based on its metal_type.

    Returns:
        (metal_price_per_gram, base_purity, metal_info_dict)
    """
    from modules.wallet.models import PRECIOUS_METALS
    metal_type = getattr(product, "metal_type", "gold") or "gold"
    metal_info = PRECIOUS_METALS.get(metal_type, PRECIOUS_METALS["gold"])
    price = get_price_value(db, metal_info["pricing_code"])
    base_purity = metal_info["base_purity"]
    return price, base_purity, metal_info


def get_end_customer_wage(db: Session, product) -> float:
    """
    Get end-customer wage% for a product.
    Product.wage IS the end-customer wage (auto-synced).
    """
    return float(product.wage)


def get_dealer_margin(db: Session, product, dealer) -> Tuple[float, float, float]:
    """
    Calculate dealer margin for a product.

    Returns:
        (ec_wage_pct, dealer_wage_pct, margin_pct)
    """
    from modules.catalog.models import ProductTierWage

    ec_wage_pct = get_end_customer_wage(db, product)
    dealer_wage_pct = 0.0

    if dealer.tier_id:
        dw_row = db.query(ProductTierWage).filter(
            ProductTierWage.product_id == product.id,
            ProductTierWage.tier_id == dealer.tier_id,
        ).first()
        if dw_row:
            dealer_wage_pct = float(dw_row.wage_percent)

    margin_pct = round(ec_wage_pct - dealer_wage_pct, 2)
    return ec_wage_pct, dealer_wage_pct, margin_pct
