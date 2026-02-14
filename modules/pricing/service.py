"""
Pricing Module - Shared Service
==================================
Shared pricing helpers used across shop, cart, order, and dealer modules.
"""

from sqlalchemy.orm import Session


def get_end_customer_wage(db: Session, product) -> float:
    """
    Get end-customer wage% for a product.
    Product.wage IS the end-customer wage (auto-synced).
    """
    return float(product.wage)
