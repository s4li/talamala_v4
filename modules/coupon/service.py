"""
Coupon Service
================
Validate, calculate, apply, and settle coupons.

Validation chain:
  1. Code exists & is ACTIVE
  2. Date range check (starts_at / expires_at)
  3. Total usage limit
  4. Per-customer usage limit
  5. Mobile whitelist (if any)
  6. First-purchase-only check
  7. Min order amount / min quantity
  8. Scope check (global / product / category)
  9. Calculate discount amount with caps
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func, desc

from modules.coupon.models import (
    Coupon, CouponMobile, CouponUsage, CouponCategory,
    CouponType, DiscountMode, CouponScope, CouponStatus,
)
from modules.order.models import Order, OrderStatus
from modules.user.models import User
from common.helpers import now_utc


class CouponValidationError(Exception):
    """Raised when coupon validation fails."""
    pass


class CouponService:

    # ------------------------------------------
    # Validate coupon (raises CouponValidationError)
    # ------------------------------------------

    def validate(
        self,
        db: Session,
        code: str,
        customer_id: int,
        order_amount: int,
        item_count: int = 1,
        product_ids: List[int] = None,
        category_ids: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Full validation chain. Returns coupon info + calculated discount.
        Raises CouponValidationError on failure.
        """
        code = code.strip().upper()

        # 1. Exists & active
        coupon = (
            db.query(Coupon)
            .options(joinedload(Coupon.allowed_mobiles), joinedload(Coupon.categories))
            .filter(Coupon.code == code)
            .first()
        )
        if not coupon:
            raise CouponValidationError("کد تخفیف نامعتبر است")

        if coupon.status != CouponStatus.ACTIVE:
            raise CouponValidationError("این کد تخفیف غیرفعال است")

        now = now_utc()

        # 2. Date range
        if coupon.starts_at and now < coupon.starts_at:
            raise CouponValidationError("این کد تخفیف هنوز فعال نشده است")
        if coupon.expires_at and now > coupon.expires_at:
            raise CouponValidationError("این کد تخفیف منقضی شده است")

        # 3. Total usage limit
        if coupon.max_total_uses and coupon.current_uses >= coupon.max_total_uses:
            raise CouponValidationError("ظرفیت استفاده از این کد تمام شده است")

        # 4. Per-customer usage limit
        customer_uses = (
            db.query(CouponUsage)
            .filter(CouponUsage.coupon_id == coupon.id, CouponUsage.user_id == customer_id)
            .count()
        )
        if customer_uses >= coupon.max_per_customer:
            raise CouponValidationError("شما قبلاً از این کد استفاده کرده‌اید")

        # 5. Mobile whitelist
        if coupon.allowed_mobiles:
            customer = db.query(User).filter(User.id == customer_id).first()
            if not customer:
                raise CouponValidationError("مشتری یافت نشد")
            allowed = {m.mobile for m in coupon.allowed_mobiles}
            if customer.mobile not in allowed:
                raise CouponValidationError("این کد تخفیف برای شماره موبایل شما مجاز نیست")

        # 6. First purchase only
        if coupon.first_purchase_only:
            prior_orders = (
                db.query(Order)
                .filter(
                    Order.customer_id == customer_id,
                    Order.status == OrderStatus.PAID,
                )
                .count()
            )
            if prior_orders > 0:
                raise CouponValidationError("این کد تخفیف فقط برای اولین خرید شما معتبر است")

        # 7. Min order amount
        if coupon.min_order_amount and order_amount < coupon.min_order_amount:
            min_toman = coupon.min_order_amount // 10
            raise CouponValidationError(f"حداقل مبلغ سفارش برای استفاده: {min_toman:,} تومان")

        # Max order amount
        if coupon.max_order_amount and order_amount > coupon.max_order_amount:
            max_toman = coupon.max_order_amount // 10
            raise CouponValidationError(f"حداکثر مبلغ سفارش برای استفاده: {max_toman:,} تومان")

        # Min quantity
        if coupon.min_quantity and item_count < coupon.min_quantity:
            raise CouponValidationError(f"حداقل {coupon.min_quantity} قلم کالا برای استفاده لازم است")

        # 8. Scope check
        applicable_amount = order_amount
        if coupon.scope == CouponScope.PRODUCT:
            if product_ids and coupon.scope_product_id:
                if coupon.scope_product_id not in product_ids:
                    raise CouponValidationError("این کد فقط برای محصول خاصی معتبر است")
                # Applicable amount could be filtered to just that product
                # For simplicity, apply to full order (admin decides scope)

        elif coupon.scope == CouponScope.CATEGORY:
            coupon_cat_ids = {cc.category_id for cc in coupon.categories}
            if coupon_cat_ids:
                cart_cat_ids = set(category_ids or [])
                if not coupon_cat_ids.intersection(cart_cat_ids):
                    raise CouponValidationError("این کد فقط برای دسته‌بندی خاصی معتبر است")

        # 9. Calculate discount
        discount_amount = self._calculate_discount(coupon, applicable_amount)

        return {
            "coupon_id": coupon.id,
            "code": coupon.code,
            "title": coupon.title,
            "coupon_type": coupon.coupon_type,
            "coupon_type_label": coupon.coupon_type_label,
            "discount_mode": coupon.discount_mode,
            "discount_value": coupon.discount_value,
            "discount_amount": discount_amount,
            "discount_display": coupon.discount_display,
            "discount_toman": discount_amount // 10,
            "is_cashback": coupon.coupon_type == CouponType.CASHBACK,
        }

    # ------------------------------------------
    # Calculate discount amount
    # ------------------------------------------

    def _calculate_discount(self, coupon: Coupon, order_amount: int) -> int:
        """Calculate actual discount in Rial."""
        if coupon.discount_mode == DiscountMode.PERCENT:
            raw = (order_amount * coupon.discount_value) // 100
            # Apply cap
            if coupon.max_discount_amount:
                raw = min(raw, coupon.max_discount_amount)
            return raw
        else:
            # Fixed amount - can't exceed order
            return min(coupon.discount_value, order_amount)

    # ------------------------------------------
    # Apply coupon to order (record usage)
    # ------------------------------------------

    def apply_to_order(
        self,
        db: Session,
        coupon_code: str,
        customer_id: int,
        order_id: int,
        order_amount: int,
        item_count: int = 1,
        product_ids: List[int] = None,
        category_ids: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Validate + record usage + return discount info.
        Called during checkout finalization.
        """
        result = self.validate(
            db, coupon_code, customer_id, order_amount,
            item_count, product_ids, category_ids,
        )

        coupon = db.query(Coupon).filter(Coupon.id == result["coupon_id"]).with_for_update().first()

        # Record usage
        usage = CouponUsage(
            coupon_id=coupon.id,
            user_id=customer_id,
            order_id=order_id,
            discount_amount=result["discount_amount"],
            cashback_settled=False,
        )
        db.add(usage)

        # Increment counter
        coupon.current_uses = (coupon.current_uses or 0) + 1
        db.flush()

        return result

    # ------------------------------------------
    # Settle cashback (called after delivery)
    # ------------------------------------------

    def settle_cashback(self, db: Session, order_id: int) -> Optional[int]:
        """
        After successful delivery, credit cashback to customer wallet.
        Returns cashback amount or None.
        """
        from modules.wallet.service import wallet_service

        usage = (
            db.query(CouponUsage)
            .join(Coupon)
            .filter(
                CouponUsage.order_id == order_id,
                Coupon.coupon_type == CouponType.CASHBACK,
                CouponUsage.cashback_settled == False,
            )
            .first()
        )
        if not usage:
            return None

        # Credit wallet
        wallet_service.deposit(
            db, usage.user_id, usage.discount_amount,
            reference_type="cashback",
            reference_id=str(order_id),
            description=f"کشبک سفارش #{order_id} — کد {usage.coupon.code}",
            idempotency_key=f"cashback:{order_id}:{usage.coupon_id}",
        )

        usage.cashback_settled = True

        # Also mark order
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.cashback_settled = True

        db.flush()
        return usage.discount_amount

    # ------------------------------------------
    # Quick check (AJAX, no side effects)
    # ------------------------------------------

    def quick_check(
        self,
        db: Session,
        code: str,
        customer_id: int,
        order_amount: int,
        item_count: int = 1,
        product_ids: List[int] = None,
        category_ids: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Same as validate but returns error dict on failure (for AJAX).
        """
        try:
            result = self.validate(
                db, code, customer_id, order_amount,
                item_count, product_ids, category_ids,
            )
            return {"valid": True, **result}
        except CouponValidationError as e:
            return {"valid": False, "error": str(e)}

    # ------------------------------------------
    # Admin: CRUD
    # ------------------------------------------

    def get_all_coupons(
        self, db: Session, page: int = 1, per_page: int = 30,
        status_filter: str = None, search: str = None,
    ) -> Tuple[List[Coupon], int]:
        q = db.query(Coupon)
        if status_filter:
            q = q.filter(Coupon.status == status_filter)
        if search:
            q = q.filter(
                (Coupon.code.ilike(f"%{search}%")) | (Coupon.title.ilike(f"%{search}%"))
            )
        total = q.count()
        coupons = (
            q.order_by(desc(Coupon.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return coupons, total

    def get_coupon_by_id(self, db: Session, coupon_id: int) -> Optional[Coupon]:
        return (
            db.query(Coupon)
            .options(joinedload(Coupon.allowed_mobiles), joinedload(Coupon.usages), joinedload(Coupon.categories))
            .filter(Coupon.id == coupon_id)
            .first()
        )

    def get_coupon_usages(
        self, db: Session, coupon_id: int, page: int = 1, per_page: int = 30
    ) -> Tuple[List[CouponUsage], int]:
        q = db.query(CouponUsage).filter(CouponUsage.coupon_id == coupon_id)
        total = q.count()
        usages = (
            q.order_by(desc(CouponUsage.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return usages, total

    def create_coupon(self, db: Session, data: dict) -> Coupon:
        coupon = Coupon(
            code=data["code"].strip().upper(),
            title=data["title"],
            description=data.get("description", ""),
            coupon_type=data.get("coupon_type", CouponType.DISCOUNT),
            discount_mode=data.get("discount_mode", DiscountMode.PERCENT),
            discount_value=int(data["discount_value"]),
            max_discount_amount=int(data["max_discount_amount"]) if data.get("max_discount_amount") else None,
            scope=data.get("scope", CouponScope.GLOBAL),
            scope_product_id=int(data["scope_product_id"]) if data.get("scope_product_id") else None,
            scope_category=data.get("scope_category") or None,
            min_order_amount=int(data.get("min_order_amount", 0)),
            max_order_amount=int(data["max_order_amount"]) if data.get("max_order_amount") else None,
            min_quantity=int(data.get("min_quantity", 0)),
            max_total_uses=int(data["max_total_uses"]) if data.get("max_total_uses") else None,
            max_per_customer=int(data.get("max_per_customer", 1)),
            starts_at=data.get("starts_at") or None,
            expires_at=data.get("expires_at") or None,
            first_purchase_only=bool(data.get("first_purchase_only")),
            is_combinable=bool(data.get("is_combinable")),
            is_private=bool(data.get("is_private")),
            referrer_user_id=int(data["referrer_user_id"]) if data.get("referrer_user_id") else None,
            status=data.get("status", CouponStatus.ACTIVE),
        )
        db.add(coupon)
        db.flush()

        # M2M categories
        category_ids = data.get("category_ids") or []
        for cat_id in category_ids:
            db.add(CouponCategory(coupon_id=coupon.id, category_id=int(cat_id)))
        db.flush()

        return coupon

    def update_coupon(self, db: Session, coupon_id: int, data: dict) -> Coupon:
        coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if not coupon:
            raise ValueError("کوپن یافت نشد")

        for key in [
            "title", "description", "coupon_type", "discount_mode",
            "scope", "scope_category", "status",
        ]:
            if key in data and data[key] is not None:
                setattr(coupon, key, data[key])

        for key in [
            "discount_value", "max_discount_amount", "min_order_amount",
            "max_order_amount", "min_quantity", "max_total_uses",
            "max_per_customer", "scope_product_id", "referrer_user_id",
        ]:
            if key in data:
                val = data[key]
                setattr(coupon, key, int(val) if val else None)

        for key in ["starts_at", "expires_at"]:
            if key in data:
                setattr(coupon, key, data[key] or None)

        for key in ["first_purchase_only", "is_combinable", "is_private"]:
            if key in data:
                setattr(coupon, key, bool(data[key]))

        # Sync M2M categories
        if "category_ids" in data:
            db.query(CouponCategory).filter(CouponCategory.coupon_id == coupon.id).delete()
            for cat_id in (data["category_ids"] or []):
                db.add(CouponCategory(coupon_id=coupon.id, category_id=int(cat_id)))

        db.flush()
        return coupon

    def delete_coupon(self, db: Session, coupon_id: int) -> bool:
        coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if not coupon:
            return False
        if coupon.current_uses > 0:
            raise ValueError("این کوپن قبلاً استفاده شده و قابل حذف نیست. غیرفعال کنید.")
        db.delete(coupon)
        db.flush()
        return True

    # ------------------------------------------
    # Mobile whitelist management
    # ------------------------------------------

    def add_mobile(self, db: Session, coupon_id: int, mobile: str, note: str = "") -> CouponMobile:
        mobile = mobile.strip()
        # Prevent duplicate
        existing = (
            db.query(CouponMobile)
            .filter(CouponMobile.coupon_id == coupon_id, CouponMobile.mobile == mobile)
            .first()
        )
        if existing:
            raise ValueError(f"شماره {mobile} قبلاً اضافه شده")
        cm = CouponMobile(coupon_id=coupon_id, mobile=mobile, note=note)
        db.add(cm)
        db.flush()
        return cm

    def add_mobiles_bulk(self, db: Session, coupon_id: int, mobiles_text: str) -> int:
        """Add multiple mobiles from textarea (one per line or comma-separated)."""
        raw = mobiles_text.replace(",", "\n").replace("،", "\n")
        lines = [m.strip() for m in raw.split("\n") if m.strip()]
        count = 0
        for mobile in lines:
            # Normalize
            mobile = mobile.replace(" ", "").replace("-", "")
            if mobile.startswith("+98"):
                mobile = "0" + mobile[3:]
            if not mobile.startswith("09") or len(mobile) != 11:
                continue
            try:
                self.add_mobile(db, coupon_id, mobile)
                count += 1
            except ValueError:
                pass  # duplicate
        db.flush()
        return count

    def remove_mobile(self, db: Session, mobile_id: int) -> bool:
        cm = db.query(CouponMobile).filter(CouponMobile.id == mobile_id).first()
        if cm:
            db.delete(cm)
            db.flush()
            return True
        return False

    # ------------------------------------------
    # Stats
    # ------------------------------------------

    def get_stats(self, db: Session) -> Dict[str, Any]:
        total = db.query(Coupon).count()
        active = db.query(Coupon).filter(Coupon.status == CouponStatus.ACTIVE).count()
        total_usages = db.query(CouponUsage).count()
        total_discount = (
            db.query(sa_func.coalesce(sa_func.sum(CouponUsage.discount_amount), 0))
            .scalar()
        )
        return {
            "total_coupons": total,
            "active_coupons": active,
            "total_usages": total_usages,
            "total_discount": total_discount,
        }


# Singleton
coupon_service = CouponService()
