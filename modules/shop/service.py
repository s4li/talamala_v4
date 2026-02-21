"""
Shop Module - Service Layer
==============================
Product listing with real-time pricing and inventory counts.
"""

from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc

from modules.catalog.models import Product, ProductCategoryLink
from modules.inventory.models import Bar, BarStatus
from modules.pricing.calculator import calculate_bar_price
from modules.pricing.service import get_end_customer_wage, get_price_value, is_price_fresh
from modules.pricing.models import GOLD_18K
from common.templating import get_setting_from_db


class ShopService:

    def get_gold_price(self, db: Session) -> int:
        """Get current gold price (18K per gram in Rials) from Asset table."""
        return get_price_value(db, GOLD_18K)

    def get_tax_percent(self, db: Session) -> str:
        """Get current tax percentage from system settings."""
        return get_setting_from_db(db, "tax_percent", "9")

    def is_gold_price_fresh(self, db: Session) -> bool:
        """Check if gold price is within staleness threshold."""
        return is_price_fresh(db, GOLD_18K)

    def list_products_with_pricing(
        self,
        db: Session,
        sort: str = "weight_asc",
        category_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 12,
    ) -> Tuple[List[dict], int, int, str]:
        """
        Get paginated active products with:
        - Real-time calculated price
        - Available inventory count
        - Optional category filter (at DB level)

        Returns:
            (products_with_pricing, total_count, gold_price_rial, tax_percent_str)
        """
        gold_price_rial = self.get_gold_price(db)
        tax_percent_str = self.get_tax_percent(db)

        # Query products with inventory count
        query = db.query(
            Product,
            func.count(Bar.id).label("inv"),
        ).outerjoin(
            Bar,
            (Bar.product_id == Product.id)
            & (Bar.status == BarStatus.ASSIGNED)
            & (Bar.customer_id.is_(None)),
        ).filter(
            Product.is_active == True,
        )

        # Category filter at DB level
        if category_id:
            query = query.join(
                ProductCategoryLink,
                ProductCategoryLink.product_id == Product.id,
            ).filter(ProductCategoryLink.category_id == category_id)

        query = query.group_by(Product.id).options(
            joinedload(Product.images),
        )

        # Total count (before pagination)
        total = query.count()

        # Sorting
        if sort == "weight_desc":
            query = query.order_by(desc(Product.weight))
        elif sort == "newest":
            query = query.order_by(desc(Product.id))
        elif sort == "price_asc":
            query = query.order_by(asc(Product.weight))
        elif sort == "price_desc":
            query = query.order_by(desc(Product.weight))
        else:
            query = query.order_by(asc(Product.weight))

        # Pagination
        offset = (page - 1) * per_page
        results = query.offset(offset).limit(per_page).all()

        # Calculate price for each product
        products = []
        for product, inv_count in results:
            ec_wage = get_end_customer_wage(db,product)
            price_info = calculate_bar_price(
                weight=product.weight,
                purity=product.purity,
                wage_percent=ec_wage,
                base_gold_price_18k=gold_price_rial,
                tax_percent=Decimal(tax_percent_str) if tax_percent_str else 0,
            )
            # Attach dynamic attributes
            product.inventory = inv_count
            product.final_price = price_info.get("total", 0)
            product.price_info = price_info
            products.append(product)

        return products, total, gold_price_rial, tax_percent_str

    def get_product_detail(
        self, db: Session, product_id: int
    ) -> Optional[Tuple]:
        """
        Get single product with full price invoice and inventory.
        Returns: (product, invoice, inventory_count, gold_price, tax_percent) or None
        """
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.is_active == True,
        ).first()

        if not product:
            return None

        gold_price_rial = self.get_gold_price(db)
        tax_percent_str = self.get_tax_percent(db)

        # Count available bars
        inventory = db.query(Bar).filter(
            Bar.product_id == product_id,
            Bar.status == BarStatus.ASSIGNED,
            Bar.customer_id.is_(None),
        ).count()

        # Dealer breakdown for customer display (dealer = location)
        from modules.user.models import User
        from modules.customer.address_models import GeoCity
        from sqlalchemy import func as sqlfunc
        loc_rows = db.query(
            User, GeoCity.name, sqlfunc.count(Bar.id)
        ).join(
            Bar, Bar.dealer_id == User.id
        ).outerjoin(
            GeoCity, User.city_id == GeoCity.id
        ).filter(
            Bar.product_id == product_id,
            Bar.status == BarStatus.ASSIGNED,
            Bar.customer_id.is_(None),
            User.is_dealer == True,
            User.is_active == True,
        ).group_by(User.id, GeoCity.name).all()

        location_inventory = [
            {"name": dlr.full_name, "city": city or "", "type": dlr.type_label, "count": cnt}
            for dlr, city, cnt in loc_rows
        ]

        # Full invoice — always use end-customer tier wage
        ec_wage = get_end_customer_wage(db,product)
        invoice = calculate_bar_price(
            weight=product.weight,
            purity=product.purity,
            wage_percent=ec_wage,
            base_gold_price_18k=gold_price_rial,
            tax_percent=Decimal(tax_percent_str) if tax_percent_str else 0,
        )

        return product, invoice, inventory, gold_price_rial, tax_percent_str, location_inventory


# Singleton
shop_service = ShopService()
