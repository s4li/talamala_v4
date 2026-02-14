"""
Pricing Module - Shared Service
==================================
Shared pricing helpers used across shop, cart, order, and dealer modules.
"""

from sqlalchemy.orm import Session

from modules.dealer.models import DealerTier
from modules.catalog.models import ProductTierWage


def get_end_customer_wage(db: Session, product) -> float:
    """
    Get end-customer tier wage% for a product.
    Fallback to product.wage (if percent) or default 7%.
    """
    ec_tier = db.query(DealerTier).filter(
        DealerTier.is_end_customer == True,
        DealerTier.is_active == True,
    ).first()
    if ec_tier:
        ptw = db.query(ProductTierWage).filter(
            ProductTierWage.product_id == product.id,
            ProductTierWage.tier_id == ec_tier.id,
        ).first()
        if ptw:
            return float(ptw.wage_percent)
    return float(product.wage) if product.is_wage_percent else 7.0
