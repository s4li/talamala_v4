"""
Dealer Service - Business Logic
==================================
POS sales, buyback processing, gold profit calculations.
"""

import secrets
from typing import List, Tuple, Dict, Any, Optional
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func, or_

from modules.dealer.models import Dealer, DealerSale, BuybackRequest, BuybackStatus
from modules.inventory.models import Bar, BarStatus, OwnershipHistory
from modules.catalog.models import ProductTierWage
from modules.customer.models import Customer
from modules.pricing.service import get_end_customer_wage, get_dealer_margin
from common.helpers import now_utc, generate_unique_claim_code


class DealerService:

    # ------------------------------------------
    # Dealer CRUD
    # ------------------------------------------

    def get_dealer(self, db: Session, dealer_id: int) -> Optional[Dealer]:
        return db.query(Dealer).filter(Dealer.id == dealer_id).first()

    def get_dealer_by_mobile(self, db: Session, mobile: str) -> Optional[Dealer]:
        return db.query(Dealer).filter(Dealer.mobile == mobile).first()

    def get_dealer_by_api_key(self, db: Session, api_key: str) -> Optional[Dealer]:
        """Lookup dealer by API key (for POS device auth)."""
        if not api_key:
            return None
        return db.query(Dealer).filter(
            Dealer.api_key == api_key,
            Dealer.is_active == True,
        ).first()

    def generate_api_key(self, db: Session, dealer_id: int) -> Optional[str]:
        """Generate a new 64-char hex API key for a dealer."""
        dealer = self.get_dealer(db, dealer_id)
        if not dealer:
            return None
        dealer.api_key = secrets.token_hex(32)
        db.flush()
        return dealer.api_key

    def revoke_api_key(self, db: Session, dealer_id: int) -> bool:
        """Remove API key from a dealer."""
        dealer = self.get_dealer(db, dealer_id)
        if not dealer:
            return False
        dealer.api_key = None
        db.flush()
        return True

    def list_dealers(self, db: Session, page: int = 1, per_page: int = 30) -> Tuple[List[Dealer], int]:
        q = db.query(Dealer).order_by(Dealer.created_at.desc())
        total = q.count()
        dealers = q.offset((page - 1) * per_page).limit(per_page).all()
        return dealers, total

    def create_dealer(
        self, db: Session, mobile: str, full_name: str,
        national_id: str = "",
        tier_id: int = None,
        province_id: int = None, city_id: int = None,
        district_id: int = None, address: str = "",
        postal_code: str = "", landline_phone: str = "",
        is_warehouse: bool = False, is_postal_hub: bool = False,
    ) -> Dealer:
        dealer = Dealer(
            mobile=mobile,
            full_name=full_name,
            national_id=national_id or None,
            tier_id=tier_id,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            address=address or None,
            postal_code=postal_code or None,
            landline_phone=landline_phone or None,
            is_warehouse=is_warehouse,
            is_postal_hub=is_postal_hub,
        )
        db.add(dealer)
        db.flush()
        return dealer

    def update_dealer(
        self, db: Session, dealer_id: int,
        full_name: str = None,
        tier_id: int = None, is_active: bool = None,
        province_id: int = None, city_id: int = None,
        district_id: int = None, address: str = None,
        postal_code: str = None, landline_phone: str = None,
        is_warehouse: bool = None, is_postal_hub: bool = None,
    ) -> Optional[Dealer]:
        dealer = self.get_dealer(db, dealer_id)
        if not dealer:
            return None
        if full_name is not None:
            dealer.full_name = full_name
        if tier_id is not None:
            dealer.tier_id = tier_id
        if is_active is not None:
            dealer.is_active = is_active
        if province_id is not None:
            dealer.province_id = province_id
        if city_id is not None:
            dealer.city_id = city_id
        if district_id is not None:
            dealer.district_id = district_id
        if address is not None:
            dealer.address = address or None
        if postal_code is not None:
            dealer.postal_code = postal_code or None
        if landline_phone is not None:
            dealer.landline_phone = landline_phone or None
        if is_warehouse is not None:
            dealer.is_warehouse = is_warehouse
        if is_postal_hub is not None:
            dealer.is_postal_hub = is_postal_hub
        db.flush()
        return dealer

    # ------------------------------------------
    # Available Bars at Dealer's Location
    # ------------------------------------------

    def get_available_bars(self, db: Session, dealer_id: int) -> List[Bar]:
        """Get bars at this dealer's location that are available for sale."""
        return (
            db.query(Bar)
            .filter(
                Bar.dealer_id == dealer_id,
                Bar.status == BarStatus.ASSIGNED,
            )
            .order_by(Bar.serial_code)
            .all()
        )

    # ------------------------------------------
    # POS Sale
    # ------------------------------------------

    def create_pos_sale(
        self, db: Session, dealer_id: int, bar_id: int,
        sale_price: int, customer_name: str = "",
        customer_mobile: str = "", customer_national_id: str = "",
        description: str = "",
        discount_wage_percent: float = 0.0,
    ) -> Dict[str, Any]:
        """Process a POS sale: dealer sells a bar to a walk-in customer."""
        # Staleness guard: block sale if gold price is expired
        from modules.pricing.service import require_fresh_price
        from modules.pricing.models import GOLD_18K
        try:
            require_fresh_price(db, GOLD_18K)
        except ValueError as e:
            return {"success": False, "message": str(e)}

        dealer = self.get_dealer(db, dealer_id)
        if not dealer or not dealer.is_active:
            return {"success": False, "message": "نماینده غیرفعال یا نامعتبر"}

        bar = db.query(Bar).filter(Bar.id == bar_id).with_for_update().first()
        if not bar:
            return {"success": False, "message": "شمش یافت نشد"}
        if bar.status != BarStatus.ASSIGNED:
            return {"success": False, "message": "این شمش قابل فروش نیست"}
        if bar.dealer_id != dealer.id:
            return {"success": False, "message": "این شمش در محل نمایندگی شما نیست"}

        # --- Resolve wage tiers for discount validation & gold profit ---
        product = bar.product
        ec_wage_pct = 0.0
        dealer_wage_pct = 0.0
        margin_pct = 0.0
        if product:
            ec_wage_pct, dealer_wage_pct, margin_pct = get_dealer_margin(db, product, dealer)

        # Validate discount range
        if discount_wage_percent < 0:
            return {"success": False, "message": "تخفیف نمی‌تواند منفی باشد"}
        if margin_pct > 0 and discount_wage_percent > margin_pct + 0.001:
            return {"success": False, "message": f"حداکثر تخفیف مجاز {margin_pct:.2f}% اجرت است"}
        if margin_pct <= 0:
            discount_wage_percent = 0.0  # no margin = no discount possible

        # Server-side price verification
        if product and discount_wage_percent > 0:
            from modules.pricing.calculator import calculate_bar_price
            from modules.pricing.service import get_price_value
            from common.templating import get_setting_from_db
            gold_price = get_price_value(db, GOLD_18K)
            tax_pct = float(get_setting_from_db(db, "tax_percent", "10"))
            effective_wage = ec_wage_pct - discount_wage_percent
            expected = calculate_bar_price(
                weight=product.weight, purity=product.purity,
                wage_percent=effective_wage,
                base_gold_price_18k=gold_price, tax_percent=tax_pct,
            )
            expected_total = expected.get("total", 0)
            if abs(sale_price - expected_total) > 10:
                return {"success": False, "message": "مبلغ فروش با قیمت محاسباتی مطابقت ندارد"}

        # Mark bar as sold + generate claim code for POS receipt
        bar.status = BarStatus.SOLD
        bar.claim_code = generate_unique_claim_code(db)
        bar.delivered_at = now_utc()  # POS = in-person, already delivered

        # Link to customer if mobile provided
        customer = None
        if customer_mobile:
            customer = db.query(Customer).filter(Customer.mobile == customer_mobile).first()
            if customer:
                bar.customer_id = customer.id

        # Ownership history
        history = OwnershipHistory(
            bar_id=bar.id,
            previous_owner_id=None,
            new_owner_id=customer.id if customer else None,
            description=f"فروش حضوری توسط نماینده {dealer.full_name}",
        )
        db.add(history)

        # Sale record
        sale = DealerSale(
            dealer_id=dealer_id,
            bar_id=bar.id,
            customer_name=customer_name,
            customer_mobile=customer_mobile,
            customer_national_id=customer_national_id,
            sale_price=sale_price,
            commission_amount=0,
            discount_wage_percent=discount_wage_percent,
            description=description,
        )
        db.add(sale)
        db.flush()

        # --- Gold settlement: auto-credit gold profit to dealer wallet ---
        gold_profit_mg = 0
        if product and margin_pct > 0:
            effective_margin = margin_pct - discount_wage_percent
            if effective_margin > 0:
                gold_profit_grams = float(product.weight) * effective_margin / 100
                gold_profit_mg = int(gold_profit_grams * 1000)

        sale.gold_profit_mg = gold_profit_mg

        if gold_profit_mg > 0:
            from modules.wallet.service import wallet_service
            from modules.wallet.models import OwnerType, AssetCode
            wallet_service.deposit(
                db, dealer_id, gold_profit_mg,
                reference_type="pos_gold_profit",
                reference_id=str(sale.id),
                description=f"سود طلایی فروش شمش {bar.serial_code} ({gold_profit_mg / 1000:.3f} گرم)",
                asset_code=AssetCode.XAU_MG,
                owner_type=OwnerType.DEALER,
            )

        return {
            "success": True,
            "message": f"فروش شمش {bar.serial_code} ثبت شد",
            "sale": sale,
            "gold_profit_mg": gold_profit_mg,
            "claim_code": bar.claim_code,
        }

    # ------------------------------------------
    # Buyback
    # ------------------------------------------

    def create_buyback(
        self, db: Session, dealer_id: int, serial_code: str,
        buyback_price: int, customer_name: str = "",
        customer_mobile: str = "", description: str = "",
    ) -> Dict[str, Any]:
        """Dealer initiates a buyback request for a bar."""
        dealer = self.get_dealer(db, dealer_id)
        if not dealer or not dealer.is_active:
            return {"success": False, "message": "نماینده غیرفعال"}

        bar = db.query(Bar).filter(Bar.serial_code == serial_code.upper()).first()
        if not bar:
            return {"success": False, "message": "شمش با این سریال یافت نشد"}
        if bar.status != BarStatus.SOLD:
            return {"success": False, "message": "فقط شمش‌های فروخته‌شده قابل بازخرید هستند"}

        buyback = BuybackRequest(
            dealer_id=dealer_id,
            bar_id=bar.id,
            customer_name=customer_name,
            customer_mobile=customer_mobile,
            buyback_price=buyback_price,
            description=description,
        )
        db.add(buyback)
        db.flush()

        return {
            "success": True,
            "message": f"درخواست بازخرید شمش {bar.serial_code} ثبت شد",
            "buyback": buyback,
        }

    def approve_buyback(self, db: Session, buyback_id: int, admin_note: str = "") -> Dict[str, Any]:
        """Admin approves a buyback — bar goes back to ASSIGNED, wage refunded as credit."""
        from modules.order.models import OrderItem
        from modules.wallet.service import wallet_service

        bb = db.query(BuybackRequest).filter(BuybackRequest.id == buyback_id).first()
        if not bb:
            return {"success": False, "message": "درخواست یافت نشد"}
        if bb.status != BuybackStatus.PENDING:
            return {"success": False, "message": "درخواست قبلا پردازش شده"}

        bb.status = BuybackStatus.APPROVED
        bb.admin_note = admin_note

        wage_refunded = 0

        # Return bar to dealer's location
        if bb.bar:
            # Save customer_id BEFORE clearing (fix: was lost before OwnershipHistory)
            original_customer_id = bb.bar.customer_id

            bb.bar.status = BarStatus.ASSIGNED
            bb.bar.customer_id = None

            history = OwnershipHistory(
                bar_id=bb.bar.id,
                previous_owner_id=original_customer_id,
                new_owner_id=None,
                description=f"بازخرید - تایید توسط مدیر (نماینده: {bb.dealer.full_name})",
            )
            db.add(history)

            # Wage refund: credit original wage as non-withdrawable store credit
            if original_customer_id:
                order_item = (
                    db.query(OrderItem)
                    .filter(OrderItem.bar_id == bb.bar.id)
                    .order_by(OrderItem.id.desc())
                    .first()
                )
                if order_item and order_item.final_wage_amount and order_item.final_wage_amount > 0:
                    wage_amount = int(order_item.final_wage_amount)
                    wallet_service.deposit_credit(
                        db, original_customer_id, wage_amount,
                        reference_type="buyback_wage_refund",
                        reference_id=str(bb.id),
                        description=f"اعتبار بازگشت اجرت بازخرید شمش {bb.bar.serial_code}",
                        idempotency_key=f"buyback_wage:{bb.id}",
                    )
                    wage_refunded = wage_amount
                    bb.wage_refund_amount = wage_refunded
                    bb.wage_refund_customer_id = original_customer_id

        db.flush()
        msg = f"بازخرید #{bb.id} تایید شد"
        if wage_refunded:
            msg += f" — اعتبار اجرت {wage_refunded // 10:,} تومان به کیف پول مشتری واریز شد"
        return {"success": True, "message": msg, "wage_refunded": wage_refunded}

    def reject_buyback(self, db: Session, buyback_id: int, admin_note: str = "") -> Dict[str, Any]:
        bb = db.query(BuybackRequest).filter(BuybackRequest.id == buyback_id).first()
        if not bb:
            return {"success": False, "message": "درخواست یافت نشد"}
        if bb.status != BuybackStatus.PENDING:
            return {"success": False, "message": "درخواست قبلا پردازش شده"}

        bb.status = BuybackStatus.REJECTED
        bb.admin_note = admin_note
        db.flush()
        return {"success": True, "message": f"بازخرید #{bb.id} رد شد"}

    # ------------------------------------------
    # Reports & Stats
    # ------------------------------------------

    def get_dealer_sales(
        self, db: Session, dealer_id: int, page: int = 1, per_page: int = 20
    ) -> Tuple[List[DealerSale], int]:
        q = db.query(DealerSale).filter(DealerSale.dealer_id == dealer_id)
        total = q.count()
        sales = q.order_by(DealerSale.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return sales, total

    def get_dealer_buybacks(
        self, db: Session, dealer_id: int, page: int = 1, per_page: int = 20
    ) -> Tuple[List[BuybackRequest], int]:
        q = db.query(BuybackRequest).filter(BuybackRequest.dealer_id == dealer_id)
        total = q.count()
        items = q.order_by(BuybackRequest.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    def get_dealer_stats(self, db: Session, dealer_id: int) -> Dict[str, Any]:
        """Dashboard stats for a dealer."""
        total_sales = db.query(DealerSale).filter(DealerSale.dealer_id == dealer_id).count()
        total_revenue = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.sale_price), 0))
            .filter(DealerSale.dealer_id == dealer_id)
            .scalar()
        )
        total_gold_profit_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.gold_profit_mg), 0))
            .filter(DealerSale.dealer_id == dealer_id)
            .scalar()
        )
        pending_buybacks = (
            db.query(BuybackRequest)
            .filter(BuybackRequest.dealer_id == dealer_id, BuybackRequest.status == BuybackStatus.PENDING)
            .count()
        )
        return {
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "total_gold_profit_mg": total_gold_profit_mg,
            "pending_buybacks": pending_buybacks,
        }

    # ------------------------------------------
    # POS API: Products + Sale by Serial
    # ------------------------------------------

    def get_products_for_dealer(self, db: Session, dealer_id: int) -> Dict[str, Any]:
        """Get products with pricing + available bar serials for a dealer's location (JSON-ready)."""
        from modules.catalog.models import Product, ProductImage
        from modules.pricing.calculator import calculate_bar_price

        dealer = self.get_dealer(db, dealer_id)
        if not dealer:
            return {"products": [], "gold_price_18k": 0, "tax_percent": "0"}

        # Get gold price + tax
        from modules.pricing.service import get_price_value
        from common.templating import get_setting_from_db
        gold_price = get_price_value(db, GOLD_18K)
        tax_percent = get_setting_from_db(db, "tax_percent", "10")

        # Get available bars at dealer, grouped by product
        bars = (
            db.query(Bar)
            .filter(
                Bar.dealer_id == dealer.id,
                Bar.status == BarStatus.ASSIGNED,
            )
            .order_by(Bar.product_id, Bar.serial_code)
            .all()
        )

        # Group bars by product_id
        bars_by_product: Dict[int, list] = {}
        for bar in bars:
            bars_by_product.setdefault(bar.product_id, []).append(bar)

        if not bars_by_product:
            return {"products": [], "gold_price_18k": gold_price, "tax_percent": tax_percent}

        # Get products that have bars
        product_ids = list(bars_by_product.keys())
        products = (
            db.query(Product)
            .filter(Product.id.in_(product_ids), Product.is_active == True)
            .all()
        )

        # Batch: default images for all products (avoid N+1)
        default_images = db.query(ProductImage).filter(
            ProductImage.product_id.in_(product_ids),
            ProductImage.is_default == True,
        ).all()
        img_map = {img.product_id: img.file_path for img in default_images}

        # Batch: dealer tier wages for all products (avoid N+1)
        dealer_wage_map: Dict[int, float] = {}
        if dealer.tier_id:
            dealer_wages = db.query(ProductTierWage).filter(
                ProductTierWage.product_id.in_(product_ids),
                ProductTierWage.tier_id == dealer.tier_id,
            ).all()
            dealer_wage_map = {dw.product_id: float(dw.wage_percent) for dw in dealer_wages}

        result_products = []
        for p in products:
            ec_wage = get_end_customer_wage(db, p)
            price_info = calculate_bar_price(
                weight=p.weight, purity=p.purity,
                wage_percent=ec_wage,
                base_gold_price_18k=gold_price,
                tax_percent=float(tax_percent),
            )

            # Dealer's tier wage from batch map
            dealer_wage_pct = dealer_wage_map.get(p.id, 0.0)
            margin_pct = round(ec_wage - dealer_wage_pct, 2)

            # Default image from batch map
            img_path = img_map.get(p.id)

            product_bars = bars_by_product.get(p.id, [])
            result_products.append({
                "product_id": p.id,
                "name": p.name,
                "weight": str(p.weight),
                "purity": float(p.purity),
                "categories": [c.name for c in p.categories],
                "final_price": price_info.get("total", 0),
                "price_breakdown": {
                    "raw_gold": price_info.get("raw_gold", 0),
                    "wage": price_info.get("wage", 0),
                    "tax": price_info.get("tax", 0),
                    "total": price_info.get("total", 0),
                },
                "ec_wage_pct": ec_wage,
                "dealer_wage_pct": dealer_wage_pct,
                "margin_pct": margin_pct,
                "available_bars": [
                    {"bar_id": b.id, "serial_code": b.serial_code}
                    for b in product_bars
                ],
                "stock_count": len(product_bars),
                "default_image": img_path,
            })

        return {
            "gold_price_18k": gold_price,
            "tax_percent": tax_percent,
            "products": result_products,
        }

    def create_pos_sale_by_serial(
        self, db: Session, dealer_id: int, serial_code: str,
        sale_price: int, customer_name: str = "",
        customer_mobile: str = "", customer_national_id: str = "",
        payment_ref: str = "", description: str = "",
        discount_wage_percent: float = 0.0,
    ) -> Dict[str, Any]:
        """Resolve serial_code to bar_id, then delegate to create_pos_sale."""
        bar = db.query(Bar).filter(Bar.serial_code == serial_code.upper()).first()
        if not bar:
            return {"success": False, "message": "شمش با این سریال‌کد یافت نشد"}

        desc = description
        if payment_ref:
            desc = f"[POS Ref: {payment_ref}] {desc}".strip()

        result = self.create_pos_sale(
            db=db, dealer_id=dealer_id, bar_id=bar.id,
            sale_price=sale_price, customer_name=customer_name,
            customer_mobile=customer_mobile,
            customer_national_id=customer_national_id,
            description=desc,
            discount_wage_percent=discount_wage_percent,
        )
        return result

    def get_admin_stats(self, db: Session) -> Dict[str, Any]:
        """Global stats for admin dashboard."""
        total_dealers = db.query(Dealer).count()
        active_dealers = db.query(Dealer).filter(Dealer.is_active == True).count()
        total_sales = db.query(DealerSale).count()
        total_revenue = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.sale_price), 0)).scalar()
        )
        total_gold_profit_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.gold_profit_mg), 0)).scalar()
        )
        pending_buybacks = (
            db.query(BuybackRequest).filter(BuybackRequest.status == BuybackStatus.PENDING).count()
        )
        return {
            "total_dealers": total_dealers,
            "active_dealers": active_dealers,
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "total_gold_profit_mg": total_gold_profit_mg,
            "pending_buybacks": pending_buybacks,
        }

    # ------------------------------------------
    # Admin: All Dealer Sales (with filters)
    # ------------------------------------------

    def list_all_sales_admin(
        self, db: Session,
        page: int = 1, per_page: int = 30,
        dealer_id: int = None,
        search: str = "",
        date_from: str = "",
        date_to: str = "",
        has_discount: str = "",
    ) -> Tuple[List[DealerSale], int, Dict[str, Any]]:
        """List all dealer sales with filters + aggregate stats for the filtered set."""
        from modules.inventory.models import Bar

        q = db.query(DealerSale).options(
            joinedload(DealerSale.dealer),
            joinedload(DealerSale.bar),
        )

        # --- Filters ---
        if dealer_id:
            q = q.filter(DealerSale.dealer_id == dealer_id)

        if search:
            search_term = f"%{search.strip()}%"
            q = q.outerjoin(Bar, DealerSale.bar_id == Bar.id).filter(
                or_(
                    DealerSale.customer_name.ilike(search_term),
                    DealerSale.customer_mobile.ilike(search_term),
                    DealerSale.customer_national_id.ilike(search_term),
                    Bar.serial_code.ilike(search_term),
                    DealerSale.description.ilike(search_term),
                )
            )

        if date_from:
            try:
                from datetime import datetime
                dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                q = q.filter(DealerSale.created_at >= dt_from)
            except ValueError:
                pass

        if date_to:
            try:
                from datetime import datetime, timedelta
                dt_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                q = q.filter(DealerSale.created_at < dt_to)
            except ValueError:
                pass

        if has_discount == "yes":
            q = q.filter(DealerSale.discount_wage_percent > 0)
        elif has_discount == "no":
            q = q.filter(DealerSale.discount_wage_percent == 0)

        # --- Aggregates on filtered set ---
        # Build a clean filter-only query (no joinedload) for aggregates
        ids_subq = q.with_entities(DealerSale.id).subquery()
        total = q.count()

        if total > 0:
            filtered_revenue = (
                db.query(sa_func.coalesce(sa_func.sum(DealerSale.sale_price), 0))
                .filter(DealerSale.id.in_(db.query(ids_subq.c.id)))
                .scalar()
            )
            filtered_gold_profit = (
                db.query(sa_func.coalesce(sa_func.sum(DealerSale.gold_profit_mg), 0))
                .filter(DealerSale.id.in_(db.query(ids_subq.c.id)))
                .scalar()
            )
            filtered_discount_count = (
                db.query(sa_func.count(DealerSale.id))
                .filter(
                    DealerSale.id.in_(db.query(ids_subq.c.id)),
                    DealerSale.discount_wage_percent > 0,
                )
                .scalar()
            )
        else:
            filtered_revenue = 0
            filtered_gold_profit = 0
            filtered_discount_count = 0

        stats = {
            "total": total,
            "total_revenue": filtered_revenue,
            "total_gold_profit_mg": filtered_gold_profit,
            "discount_count": filtered_discount_count,
        }

        # --- Paginate ---
        sales = (
            q.order_by(DealerSale.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return sales, total, stats


dealer_service = DealerService()
