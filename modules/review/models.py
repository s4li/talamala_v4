"""
Review Module - Models
========================
Product reviews (star rating from order page) and comments/Q&A (from product page).
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class CommentSenderType(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


# ==========================================
# Review (star rating — submitted from order page)
# ==========================================

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id", ondelete="SET NULL"), nullable=True, unique=True)
    rating = Column(Integer, nullable=False)  # 1-5
    body = Column(Text, nullable=False)
    admin_reply = Column(Text, nullable=True)
    admin_reply_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    order_item = relationship("OrderItem", foreign_keys=[order_item_id])
    images = relationship("ReviewImage", back_populates="review", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_review_product", "product_id"),
        Index("ix_review_customer", "customer_id"),
    )


class ReviewImage(Base):
    __tablename__ = "review_images"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=False)

    review = relationship("Review", back_populates="images")


# ==========================================
# Product Comment / Q&A (submitted from product page)
# ==========================================

class ProductComment(Base):
    __tablename__ = "product_comments"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    parent_id = Column(Integer, ForeignKey("product_comments.id", ondelete="CASCADE"), nullable=True)
    body = Column(Text, nullable=False)
    sender_type = Column(String, default=CommentSenderType.CUSTOMER, nullable=False)
    sender_name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    parent = relationship("ProductComment", remote_side=[id], backref="replies")
    images = relationship("CommentImage", back_populates="comment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_comment_product", "product_id"),
        Index("ix_comment_parent", "parent_id"),
    )

    @property
    def is_admin(self) -> bool:
        return self.sender_type == CommentSenderType.ADMIN

    @property
    def has_admin_reply(self) -> bool:
        for r in (self.replies or []):
            if r.sender_type == CommentSenderType.ADMIN:
                return True
        return False

    @property
    def sender_badge_color(self) -> str:
        return "success" if self.is_admin else "info"

    @property
    def sender_type_label(self) -> str:
        return "پشتیبانی" if self.is_admin else "مشتری"


class CommentImage(Base):
    __tablename__ = "comment_images"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("product_comments.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=False)

    comment = relationship("ProductComment", back_populates="images")


# ==========================================
# Comment Like
# ==========================================

class CommentLike(Base):
    __tablename__ = "comment_likes"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("product_comments.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("comment_id", "customer_id", name="uq_comment_like"),
    )
