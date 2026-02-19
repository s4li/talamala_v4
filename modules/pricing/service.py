"""
Pricing Module - Shared Service
==================================
Shared pricing helpers used across shop, cart, order, and dealer modules.
"""

from typing import Tuple

from sqlalchemy.orm import Session


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
