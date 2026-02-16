"""
Cart Module - Models
=====================
Shopping cart with per-customer uniqueness and quantity constraints.
"""

from sqlalchemy import (
    Column, Integer, ForeignKey, DateTime,
    UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    customer = relationship("Customer", foreign_keys=[customer_id])
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    package_type_id = Column(Integer, ForeignKey("package_types.id", ondelete="SET NULL"), nullable=True)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
    package_type = relationship("PackageType")

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
        CheckConstraint("quantity >= 1", name="ck_cart_qty"),
    )
