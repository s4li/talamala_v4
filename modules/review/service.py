"""
Review Service - Business Logic
==================================
Create, list, and manage product reviews and comments.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func

from modules.review.models import (
    Review, ReviewImage, ProductComment, CommentImage, CommentSenderType,
)
from modules.order.models import Order, OrderItem
from modules.customer.models import Customer
from modules.catalog.models import Product
from common.upload import save_upload_file
from common.helpers import now_utc

logger = logging.getLogger("talamala.review")


class ReviewService:

    def customer_has_purchased(self, db: Session, customer_id: int, product_id: int) -> bool:
        return db.query(OrderItem).join(Order).filter(
            Order.customer_id == customer_id,
            Order.status == "Paid",
            OrderItem.product_id == product_id,
        ).first() is not None

    def _save_review_images(self, db: Session, review_id: int, files: List[UploadFile]):
        for f in files:
            if not f or not f.filename:
                continue
            path = save_upload_file(f, subfolder="reviews")
            if path:
                db.add(ReviewImage(review_id=review_id, file_path=path))
        db.flush()

    def _save_comment_images(self, db: Session, comment_id: int, files: List[UploadFile]):
        for f in files:
            if not f or not f.filename:
                continue
            path = save_upload_file(f, subfolder="comments")
            if path:
                db.add(CommentImage(comment_id=comment_id, file_path=path))
        db.flush()

    # ------------------------------------------
    # Create Review (from order page)
    # ------------------------------------------

    def create_review(self, db, customer_id, order_item_id, product_id, rating, body, files=None):
        if not body or not body.strip():
            return {"success": False, "message": "متن نظر نمی‌تواند خالی باشد"}
        if rating < 1 or rating > 5:
            return {"success": False, "message": "امتیاز باید بین ۱ تا ۵ باشد"}

        existing = db.query(Review).filter(Review.order_item_id == order_item_id).first()
        if existing:
            return {"success": False, "message": "شما قبلاً برای این محصول نظر ثبت کرده‌اید"}

        item = db.query(OrderItem).join(Order).filter(
            OrderItem.id == order_item_id,
            Order.customer_id == customer_id,
            Order.status == "Paid",
        ).first()
        if not item:
            return {"success": False, "message": "آیتم سفارش معتبر نیست"}

        review = Review(
            product_id=product_id, customer_id=customer_id,
            order_item_id=order_item_id, rating=rating, body=body.strip(),
        )
        db.add(review)
        db.flush()

        if files:
            self._save_review_images(db, review.id, files)

        return {"success": True, "review": review}

    # ------------------------------------------
    # Add Comment (from product page)
    # ------------------------------------------

    def add_comment(self, db, product_id, customer_id, sender_name, body,
                    sender_type=CommentSenderType.CUSTOMER, parent_id=None, files=None):
        if not body or not body.strip():
            return {"success": False, "message": "متن نظر نمی‌تواند خالی باشد"}

        if parent_id:
            parent = db.query(ProductComment).filter(ProductComment.id == parent_id).first()
            if not parent or parent.product_id != product_id:
                return {"success": False, "message": "نظر والد معتبر نیست"}

        comment = ProductComment(
            product_id=product_id, customer_id=customer_id,
            parent_id=parent_id, body=body.strip(),
            sender_type=sender_type, sender_name=sender_name,
        )
        db.add(comment)
        db.flush()

        if files:
            self._save_comment_images(db, comment.id, files)

        return {"success": True, "comment": comment}

    # ------------------------------------------
    # Query methods
    # ------------------------------------------

    def get_product_reviews(self, db, product_id):
        return (
            db.query(Review)
            .options(joinedload(Review.images), joinedload(Review.customer))
            .filter(Review.product_id == product_id)
            .order_by(Review.created_at.desc())
            .all()
        )

    def get_product_review_stats(self, db, product_id):
        result = db.query(
            sa_func.count(Review.id), sa_func.avg(Review.rating),
        ).filter(Review.product_id == product_id).first()
        count = result[0] or 0
        avg = round(float(result[1]), 1) if result[1] else 0
        return {"count": count, "avg": avg}

    def get_product_comments(self, db, product_id):
        return (
            db.query(ProductComment)
            .options(joinedload(ProductComment.images), joinedload(ProductComment.customer))
            .filter(ProductComment.product_id == product_id, ProductComment.parent_id == None)
            .order_by(ProductComment.created_at.desc())
            .all()
        )

    def get_reviews_for_order_items(self, db, order_item_ids):
        if not order_item_ids:
            return {}
        reviews = (
            db.query(Review).options(joinedload(Review.images))
            .filter(Review.order_item_id.in_(order_item_ids)).all()
        )
        return {r.order_item_id: r for r in reviews}

    # ------------------------------------------
    # Admin methods
    # ------------------------------------------

    def admin_reply_review(self, db, review_id, reply_text):
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return {"success": False, "message": "نظر یافت نشد"}
        review.admin_reply = reply_text.strip()
        review.admin_reply_at = now_utc()
        db.flush()
        return {"success": True}

    def delete_review(self, db, review_id):
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return {"success": False, "message": "نظر یافت نشد"}
        db.delete(review)
        db.flush()
        return {"success": True}

    def delete_comment(self, db, comment_id):
        comment = db.query(ProductComment).filter(ProductComment.id == comment_id).first()
        if not comment:
            return {"success": False, "message": "نظر یافت نشد"}
        db.delete(comment)
        db.flush()
        return {"success": True}

    def list_reviews_admin(self, db, page=1, per_page=30, search=None):
        q = db.query(Review).options(
            joinedload(Review.product), joinedload(Review.customer), joinedload(Review.images),
        )
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.join(Product, Review.product_id == Product.id)
            q = q.outerjoin(Customer, Review.customer_id == Customer.id)
            q = q.filter(Product.name.ilike(term) | Customer.mobile.ilike(term) | Review.body.ilike(term))
        total = q.count()
        reviews = q.order_by(Review.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return reviews, total

    def list_comments_admin(self, db, page=1, per_page=30, search=None):
        q = db.query(ProductComment).options(
            joinedload(ProductComment.product), joinedload(ProductComment.customer), joinedload(ProductComment.images),
        ).filter(ProductComment.parent_id == None)
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.join(Product, ProductComment.product_id == Product.id)
            q = q.filter(Product.name.ilike(term) | ProductComment.body.ilike(term) | ProductComment.sender_name.ilike(term))
        total = q.count()
        comments = q.order_by(ProductComment.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return comments, total

    def get_review(self, db, review_id):
        return db.query(Review).options(
            joinedload(Review.product), joinedload(Review.customer), joinedload(Review.images),
        ).filter(Review.id == review_id).first()

    def get_comment(self, db, comment_id):
        return db.query(ProductComment).options(
            joinedload(ProductComment.product), joinedload(ProductComment.customer), joinedload(ProductComment.images),
        ).filter(ProductComment.id == comment_id).first()


review_service = ReviewService()
