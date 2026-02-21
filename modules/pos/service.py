"""
POS Module - Service
=====================
Business logic for customer-facing POS sales at dealer locations.
Reserve -> Confirm/Cancel pattern for safe card payment flow.
"""

from datetime import timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func

from modules.catalog.models import (
    Product, ProductCategory, ProductCategoryLink, ProductImage, ProductTierWage,
)
from modules.inventory.models import Bar, BarStatus, OwnershipHistory
from modules.user.models import User
from modules.dealer.models import DealerSale
from modules.pricing.calculator import calculate_bar_price
from modules.pricing.service import get_price_value, require_fresh_price
from modules.pricing.models import GOLD_18K
from modules.pricing.service import get_end_customer_wage
from common.helpers import now_utc, generate_unique_claim_code


POS_RESERVE_MINUTES = 2


class PosService:

    # ------------------------------------------
    # Categories
    # ------------------------------------------

    def get_categories_for_dealer(self, db: Session, dealer_id: int) -> List[Dict[str, Any]]:
        """Active categories that have available stock at this dealer."""
        available_product_ids = (
            db.query(Bar.product_id)
            .filter(
                Bar.dealer_id == dealer_id,
                Bar.status == BarStatus.ASSIGNED,
                Bar.product_id.isnot(None),
            )
            .distinct()
            .subquery()
        )

        categories = (
            db.query(
                ProductCategory.id,
                ProductCategory.name,
                ProductCategory.slug,
                ProductCategory.sort_order,
                sa_func.count(ProductCategoryLink.product_id.distinct()).label("product_count"),
            )
            .join(ProductCategoryLink, ProductCategoryLink.category_id == ProductCategory.id)
            .filter(
                ProductCategory.is_active == True,
                ProductCategoryLink.product_id.in_(available_product_ids),
            )
            .group_by(ProductCategory.id)
            .order_by(ProductCategory.sort_order, ProductCategory.name)
            .all()
        )

        return [
            {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "product_count": cat.product_count,
            }
            for cat in categories
        ]

    # ------------------------------------------
    # Products
    # ------------------------------------------

    def get_products_for_pos(
        self, db: Session, dealer_id: int, category_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Products with live pricing + stock count for POS display."""
        dealer = db.query(User).filter(User.id == dealer_id, User.is_dealer == True).first()
        if not dealer:
            return {"products": [], "gold_price_18k": 0, "tax_percent": "10"}

        gold_price, tax_percent = self._get_price_settings(db)

        # Count available bars per product at this dealer
        stock_query = (
            db.query(Bar.product_id, sa_func.count(Bar.id).label("cnt"))
            .filter(
                Bar.dealer_id == dealer_id,
                Bar.status == BarStatus.ASSIGNED,
                Bar.product_id.isnot(None),
            )
            .group_by(Bar.product_id)
        )
        stock_map = {row.product_id: row.cnt for row in stock_query.all()}

        if not stock_map:
            return {"products": [], "gold_price_18k": gold_price, "tax_percent": str(tax_percent)}

        products_query = (
            db.query(Product)
            .filter(Product.id.in_(stock_map.keys()), Product.is_active == True)
        )
        if category_id:
            products_query = products_query.join(ProductCategoryLink).filter(
                ProductCategoryLink.category_id == category_id
            )

        products = products_query.all()

        result = []
        for p in products:
            ec_wage = get_end_customer_wage(db, p)
            price_info = calculate_bar_price(
                weight=p.weight, purity=p.purity,
                wage_percent=ec_wage,
                base_gold_price_18k=gold_price,
                tax_percent=tax_percent,
            )

            img = (
                db.query(ProductImage)
                .filter(ProductImage.product_id == p.id, ProductImage.is_default == True)
                .first()
            ) or (
                db.query(ProductImage)
                .filter(ProductImage.product_id == p.id)
                .first()
            )

            result.append({
                "product_id": p.id,
                "name": p.name,
                "weight": str(p.weight),
                "purity": float(p.purity),
                "wage_percent": float(ec_wage),
                "price": {
                    "raw_gold": price_info.get("raw_gold", 0),
                    "wage": price_info.get("wage", 0),
                    "tax": price_info.get("tax", 0),
                    "total": price_info.get("total", 0),
                },
                "stock": stock_map.get(p.id, 0),
                "image": img.file_path if img else None,
                "categories": [c.name for c in p.categories],
            })

        return {
            "gold_price_18k": gold_price,
            "tax_percent": str(tax_percent),
            "products": sorted(result, key=lambda x: float(x["weight"])),
        }

    # ------------------------------------------
    # Reserve
    # ------------------------------------------

    def reserve_bar(self, db: Session, dealer_id: int, product_id: int) -> Dict[str, Any]:
        """Reserve an available bar for POS payment (2-minute hold)."""
        # Staleness guard
        try:
            require_fresh_price(db, GOLD_18K)
        except ValueError as e:
            return {"success": False, "message": str(e)}

        bar = (
            db.query(Bar)
            .filter(
                Bar.dealer_id == dealer_id,
                Bar.product_id == product_id,
                Bar.status == BarStatus.ASSIGNED,
            )
            .with_for_update(skip_locked=True)
            .first()
        )
        if not bar:
            return {"success": False, "message": "موجودی برای این محصول تمام شده است"}

        product = bar.product
        gold_price, tax_percent = self._get_price_settings(db)
        ec_wage = get_end_customer_wage(db, product)
        price_info = calculate_bar_price(
            weight=product.weight, purity=product.purity,
            wage_percent=ec_wage,
            base_gold_price_18k=gold_price,
            tax_percent=tax_percent,
        )

        bar.status = BarStatus.RESERVED
        bar.reserved_until = now_utc() + timedelta(minutes=POS_RESERVE_MINUTES)
        db.flush()

        return {
            "success": True,
            "reservation": {
                "bar_id": bar.id,
                "serial_code": bar.serial_code,
                "product_name": product.name,
                "weight": str(product.weight),
                "purity": float(product.purity),
                "price": {
                    "raw_gold": price_info.get("raw_gold", 0),
                    "wage": price_info.get("wage", 0),
                    "tax": price_info.get("tax", 0),
                    "total": price_info.get("total", 0),
                },
                "expires_at": bar.reserved_until.isoformat(),
            },
        }

    # ------------------------------------------
    # Confirm Sale
    # ------------------------------------------

    def confirm_sale(
        self, db: Session, dealer_id: int, bar_id: int,
        payment_ref: str = "", payment_amount: int = 0,
        customer_name: str = "", customer_mobile: str = "",
        customer_national_id: str = "",
    ) -> Dict[str, Any]:
        """Confirm POS sale after successful card payment."""
        # Staleness guard
        try:
            require_fresh_price(db, GOLD_18K)
        except ValueError as e:
            return {"success": False, "message": str(e)}

        bar = db.query(Bar).filter(Bar.id == bar_id).with_for_update().first()
        if not bar:
            return {"success": False, "message": "شمش یافت نشد"}
        if bar.status != BarStatus.RESERVED:
            return {"success": False, "message": "رزرو منقضی شده یا شمش قابل فروش نیست"}
        if bar.dealer_id != dealer_id:
            return {"success": False, "message": "این شمش در محل نمایندگی شما نیست"}

        if bar.reserved_until and bar.reserved_until < now_utc():
            bar.status = BarStatus.ASSIGNED
            bar.reserved_until = None
            db.flush()
            return {"success": False, "message": "زمان رزرو منقضی شده، لطفا دوباره تلاش کنید"}

        dealer = db.query(User).filter(User.id == dealer_id, User.is_dealer == True).first()
        product = bar.product

        gold_price, tax_percent = self._get_price_settings(db)
        ec_wage = get_end_customer_wage(db, product) if product else 0
        price_info = calculate_bar_price(
            weight=product.weight, purity=product.purity,
            wage_percent=ec_wage,
            base_gold_price_18k=gold_price,
            tax_percent=tax_percent,
        ) if product else {}

        expected_price = price_info.get("total", 0)
        sale_price = payment_amount or expected_price

        # Server-side price validation: reject if payment deviates > 10 rial
        if payment_amount and expected_price and abs(payment_amount - expected_price) > 10:
            bar.status = BarStatus.ASSIGNED
            bar.reserved_until = None
            db.flush()
            return {"success": False, "message": "مبلغ پرداخت با قیمت محاسباتی مطابقت ندارد"}

        # Rasis POS: remove bar from dealer's POS before marking sold
        try:
            from modules.rasis.service import rasis_service
            if dealer.rasis_sharepoint:
                rasis_service.remove_bar_from_pos(db, bar, dealer)
        except Exception:
            pass  # Never block POS sales

        # Mark sold
        bar.status = BarStatus.SOLD
        bar.reserved_until = None
        bar.reserved_customer_id = None
        bar.claim_code = generate_unique_claim_code(db)
        bar.delivered_at = now_utc()  # POS = in-person, already delivered

        # Link customer
        customer = None
        if customer_mobile:
            customer = db.query(User).filter(User.mobile == customer_mobile).first()
            if customer:
                bar.customer_id = customer.id

        # Ownership history
        db.add(OwnershipHistory(
            bar_id=bar.id,
            previous_owner_id=None,
            new_owner_id=customer.id if customer else None,
            description=f"فروش حضوری POS - نماینده {dealer.full_name}"
                        + (f" - رسید: {payment_ref}" if payment_ref else ""),
        ))

        # Gold profit calculation
        dealer_wage_pct = 0.0
        margin_pct = 0.0
        if product and dealer.tier_id:
            row = db.query(ProductTierWage).filter(
                ProductTierWage.product_id == product.id,
                ProductTierWage.tier_id == dealer.tier_id,
            ).first()
            dealer_wage_pct = float(row.wage_percent) if row else 0
            margin_pct = ec_wage - dealer_wage_pct

        gold_profit_mg = 0
        if product and margin_pct > 0:
            gold_profit_mg = int(float(product.weight) * margin_pct / 100 * 1000)

        # Sale record
        desc = "فروش POS دستگاه"
        if payment_ref:
            desc = f"[POS Ref: {payment_ref}] {desc}"

        sale = DealerSale(
            dealer_id=dealer_id, bar_id=bar.id,
            customer_name=customer_name, customer_mobile=customer_mobile,
            customer_national_id=customer_national_id,
            sale_price=sale_price, commission_amount=0,
            gold_profit_mg=gold_profit_mg, discount_wage_percent=0,
            description=desc,
        )
        db.add(sale)
        db.flush()

        # Gold settlement
        if gold_profit_mg > 0:
            from modules.wallet.service import wallet_service
            from modules.wallet.models import AssetCode
            wallet_service.deposit(
                db, dealer_id, gold_profit_mg,
                reference_type="pos_gold_profit",
                reference_id=str(sale.id),
                description=f"سود طلایی فروش POS شمش {bar.serial_code} ({gold_profit_mg / 1000:.3f} گرم)",
                asset_code=AssetCode.XAU_MG,
            )

        return {
            "success": True,
            "sale": {
                "sale_id": sale.id,
                "serial_code": bar.serial_code,
                "claim_code": bar.claim_code,
                "product_name": product.name if product else "",
                "weight": str(product.weight) if product else "",
                "purity": float(product.purity) if product else 0,
                "sale_price": sale_price,
                "price_breakdown": price_info,
                "gold_profit_mg": gold_profit_mg,
                "payment_ref": payment_ref,
                "customer_name": customer_name,
                "customer_mobile": customer_mobile,
                "dealer_name": dealer.full_name,
                "created_at": sale.created_at.isoformat() if sale.created_at else now_utc().isoformat(),
            },
        }

    # ------------------------------------------
    # Cancel Reservation
    # ------------------------------------------

    def cancel_reservation(self, db: Session, dealer_id: int, bar_id: int) -> Dict[str, Any]:
        """Cancel a POS bar reservation (payment failed/cancelled)."""
        bar = db.query(Bar).filter(Bar.id == bar_id).with_for_update().first()
        if not bar:
            return {"success": False, "message": "شمش یافت نشد"}
        if bar.dealer_id != dealer_id:
            return {"success": False, "message": "این شمش متعلق به نمایندگی شما نیست"}
        if bar.status != BarStatus.RESERVED:
            return {"success": True, "message": "رزرو قبلا لغو شده"}

        bar.status = BarStatus.ASSIGNED
        bar.reserved_until = None
        bar.reserved_customer_id = None
        db.flush()

        return {"success": True, "message": "رزرو لغو شد"}

    # ------------------------------------------
    # Receipt
    # ------------------------------------------

    def get_receipt(self, db: Session, dealer_id: int, sale_id: int) -> Dict[str, Any]:
        """Get receipt data for a completed POS sale."""
        sale = (
            db.query(DealerSale)
            .options(joinedload(DealerSale.bar))
            .filter(DealerSale.id == sale_id, DealerSale.dealer_id == dealer_id)
            .first()
        )
        if not sale:
            return {"success": False, "message": "فروش یافت نشد"}

        dealer = db.query(User).filter(User.id == dealer_id, User.is_dealer == True).first()
        bar = sale.bar
        product = bar.product if bar else None

        return {
            "success": True,
            "receipt": {
                "sale_id": sale.id,
                "serial_code": bar.serial_code if bar else "",
                "claim_code": bar.claim_code if bar else "",
                "product_name": product.name if product else "",
                "weight": str(product.weight) if product else "",
                "purity": float(product.purity) if product else 0,
                "sale_price": sale.sale_price,
                "customer_name": sale.customer_name or "",
                "customer_mobile": sale.customer_mobile or "",
                "dealer_name": dealer.full_name if dealer else "",
                "dealer_address": (dealer.dealer_address or dealer.address or "") if dealer else "",
                "created_at": sale.created_at.isoformat() if sale.created_at else "",
            },
        }

    # ------------------------------------------
    # Helpers
    # ------------------------------------------

    def _get_price_settings(self, db: Session):
        from common.templating import get_setting_from_db
        gold_price = get_price_value(db, GOLD_18K)
        tax_percent = float(get_setting_from_db(db, "tax_percent", "10"))
        return gold_price, tax_percent


pos_service = PosService()
