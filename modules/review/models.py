"""
Review Module - Models
========================
Product reviews (star ratings from buyers) and product comments/Q&A.

Models:
  - Review: Star rating (1-5) from buyer, linked to order_item
  - ReviewImage: Image attached to a review
  - ProductComment: General comment or Q&A on a product (all users)
  - CommentImage: Image attached to a comment (only buyers)
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# Enums
# ==========================================

class CommentSenderType(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


# ==========================================
# Review (buyer star ratings)
# ==========================================

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False, unique=True)

    rating = Column(Integer, nullable=False)  # 1-5
    body = Column(Text, nullable=False)

    admin_reply = Column(Text, nullable=True)
    admin_reply_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    customer = relationship("Customer", foreign_keys=[customer_id])
    order_item = relationship("OrderItem", foreign_keys=[order_item_id])
    images = relationship(
        "ReviewImage", back_populates="review",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
        Index("ix_review_product", "product_id"),
        Index("ix_review_customer", "customer_id"),
    )

    @property
    def stars_range(self):
        return range(1, 6)

    def __repr__(self):
        return f"<Review #{self.id} product={self.product_id} rating={self.rating}>"


# ==========================================
# Review Image
# ==========================================

class ReviewImage(Base):
    __tablename__ = "review_images"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=False)

    review = relationship("Review", back_populates="images")

    __table_args__ = (
        Index("ix_review_image_review", "review_id"),
    )


# ==========================================
# Product Comment (comments + Q&A)
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
    parent = relationship("ProductComment", remote_side="ProductComment.id", backref="replies")
    images = relationship(
        "CommentImage", back_populates="comment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_comment_product", "product_id"),
        Index("ix_comment_parent", "parent_id"),
    )

    @property
    def is_admin(self) -> bool:
        return self.sender_type == CommentSenderType.ADMIN

    @property
    def sender_badge_color(self) -> str:
        return "success" if self.is_admin else "info"

    @property
    def sender_type_label(self) -> str:
        return "پشتیبانی طلاملا" if self.is_admin else "مشتری"

    def __repr__(self):
        return f"<ProductComment #{self.id} product={self.product_id}>"


# ==========================================
# Comment Image
# ==========================================

class CommentImage(Base):
    __tablename__ = "comment_images"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("product_comments.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String, nullable=False)

    comment = relationship("ProductComment", back_populates="images")

    __table_args__ = (
        Index("ix_comment_image_comment", "comment_id"),
    )
