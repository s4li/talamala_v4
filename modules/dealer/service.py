"""
Dealer Service - Business Logic
==================================
POS sales, buyback processing, gold profit calculations.
"""

import secrets
from typing import List, Tuple, Dict, Any, Optional
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func, or_, case as sa_case

from modules.user.models import User
from modules.dealer.models import (
    DealerSale, BuybackRequest, BuybackStatus, SubDealerRelation,
    B2BOrder, B2BOrderItem, B2BOrderStatus,
)
from modules.inventory.models import Bar, BarStatus, OwnershipHistory
from modules.catalog.models import ProductTierWage
from modules.pricing.service import get_end_customer_wage, get_dealer_margin, get_product_pricing, get_price_value
from common.helpers import now_utc, generate_unique_claim_code


class DealerService:

    # ------------------------------------------
    # Dealer CRUD
    # ------------------------------------------

    def get_dealer(self, db: Session, dealer_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == dealer_id, User.is_dealer == True).first()

    def get_dealer_by_mobile(self, db: Session, mobile: str) -> Optional[User]:
        return db.query(User).filter(User.mobile == mobile, User.is_dealer == True).first()

    def get_dealer_by_api_key(self, db: Session, api_key: str) -> Optional[User]:
        """Lookup dealer by API key (for POS device auth)."""
        if not api_key:
            return None
        return db.query(User).filter(
            User.api_key == api_key,
            User.is_dealer == True,
            User.is_active == True,
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

    def list_dealers(self, db: Session, page: int = 1, per_page: int = 30) -> Tuple[List[User], int]:
        q = db.query(User).filter(User.is_dealer == True).order_by(User.created_at.desc())
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
        can_distribute: bool = False,
    ) -> User:
        # Check if user with this mobile already exists
        existing = db.query(User).filter(User.mobile == mobile).first()
        if existing:
            # Promote existing user to dealer
            existing.is_dealer = True
            name_parts = full_name.split(" ", 1) if full_name else ["", ""]
            existing.first_name = existing.first_name or name_parts[0]
            existing.last_name = existing.last_name or (name_parts[1] if len(name_parts) > 1 else "")
            existing.national_id = existing.national_id or national_id or None
            existing.tier_id = tier_id
            existing.province_id = province_id
            existing.city_id = city_id
            existing.district_id = district_id
            existing.dealer_address = address or None
            existing.dealer_postal_code = postal_code or None
            existing.landline_phone = landline_phone or None
            existing.is_warehouse = is_warehouse
            existing.is_postal_hub = is_postal_hub
            existing.can_distribute = can_distribute
            db.flush()
            return existing

        name_parts = full_name.split(" ", 1) if full_name else ["", ""]
        dealer = User(
            mobile=mobile,
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else "",
            national_id=national_id or None,
            is_dealer=True,
            tier_id=tier_id,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            dealer_address=address or None,
            dealer_postal_code=postal_code or None,
            landline_phone=landline_phone or None,
            is_warehouse=is_warehouse,
            is_postal_hub=is_postal_hub,
            can_distribute=can_distribute,
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
        can_distribute: bool = None,
    ) -> Optional[User]:
        dealer = self.get_dealer(db, dealer_id)
        if not dealer:
            return None
        if full_name is not None:
            name_parts = full_name.split(" ", 1) if full_name else ["", ""]
            dealer.first_name = name_parts[0]
            dealer.last_name = name_parts[1] if len(name_parts) > 1 else ""
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
            dealer.dealer_address = address or None
        if postal_code is not None:
            dealer.dealer_postal_code = postal_code or None
        if landline_phone is not None:
            dealer.landline_phone = landline_phone or None
        if is_warehouse is not None:
            dealer.is_warehouse = is_warehouse
        if is_postal_hub is not None:
            dealer.is_postal_hub = is_postal_hub
        if can_distribute is not None:
            dealer.can_distribute = can_distribute
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
        from modules.pricing.service import require_fresh_price

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

        # --- Resolve metal type + pricing ---
        product = bar.product
        metal_type = (product.metal_type if product else "gold") or "gold"
        metal_price, base_purity, metal_info = get_product_pricing(db, product) if product else (0, 750, {})

        # Staleness + trade toggle guard
        if product:
            try:
                require_fresh_price(db, metal_info["pricing_code"])
            except ValueError as e:
                return {"success": False, "message": str(e)}
            try:
                from modules.pricing.trade_guard import require_trade_enabled
                require_trade_enabled(db, metal_type, "dealer_pos")
            except ValueError as e:
                return {"success": False, "message": str(e)}

        # --- Resolve wage tiers for discount validation & metal profit ---
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

        # Server-side authoritative price calculation
        # When discount is applied, recalculate on server to avoid JS float rounding
        # and metal price change between page load and submission
        if product:
            from modules.pricing.calculator import calculate_bar_price
            from common.templating import get_setting_from_db
            from decimal import Decimal, ROUND_FLOOR
            tax_pct = float(get_setting_from_db(db, "tax_percent", "10"))
            full_price = calculate_bar_price(
                weight=product.weight, purity=product.purity,
                wage_percent=ec_wage_pct,
                base_metal_price=metal_price, tax_percent=tax_pct,
                base_purity=base_purity,
            )
            if discount_wage_percent > 0:
                raw_gold = full_price.get("raw_gold", 0)
                discount_rial = int(
                    (Decimal(str(raw_gold)) * Decimal(str(discount_wage_percent))
                     / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_FLOOR)
                )
                sale_price = full_price.get("total", 0) - discount_rial
            else:
                sale_price = full_price.get("total", 0)

        # Mark bar as sold + generate claim code for POS receipt
        # Rasis POS: remove bar from dealer's POS before marking sold
        try:
            from modules.rasis.service import rasis_service
            if dealer.rasis_sharepoint:
                rasis_service.remove_bar_from_pos(db, bar, dealer)
        except Exception:
            pass  # Never block POS sales

        bar.status = BarStatus.SOLD
        bar.claim_code = generate_unique_claim_code(db)
        bar.delivered_at = now_utc()  # POS = in-person, already delivered

        # Link to customer if mobile provided
        customer = None
        if customer_mobile:
            customer = db.query(User).filter(User.mobile == customer_mobile).first()
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
            applied_metal_price=metal_price,
            metal_type=metal_type,
            commission_amount=0,
            discount_wage_percent=discount_wage_percent,
            description=description,
        )
        db.add(sale)
        db.flush()

        # --- Metal settlement: auto-credit profit to dealer wallet ---
        metal_profit_mg = 0
        if product and margin_pct > 0:
            effective_margin = margin_pct - discount_wage_percent
            if effective_margin > 0:
                profit_grams = float(product.weight) * effective_margin / 100
                metal_profit_mg = int(profit_grams * 1000)

        sale.metal_profit_mg = metal_profit_mg

        if metal_profit_mg > 0 and metal_info:
            from modules.wallet.service import wallet_service
            from modules.wallet.models import AssetCode
            asset_code = AssetCode(metal_info["asset_code"])
            metal_label = metal_info.get("label", "فلز")

            # --- Sub-dealer commission split ---
            parent_rel = (
                db.query(SubDealerRelation)
                .filter(
                    SubDealerRelation.child_dealer_id == dealer_id,
                    SubDealerRelation.is_active == True,
                )
                .first()
            )
            parent_active = (
                parent_rel
                and parent_rel.parent_dealer
                and parent_rel.parent_dealer.is_active
                and float(parent_rel.commission_split_percent) > 0
            ) if parent_rel else False

            if parent_active:
                split_pct = float(parent_rel.commission_split_percent)
                parent_share_mg = int(metal_profit_mg * split_pct / 100)
                child_share_mg = metal_profit_mg - parent_share_mg

                # Record split on sale
                sale.parent_dealer_id = parent_rel.parent_dealer_id
                sale.parent_commission_mg = parent_share_mg

                # Deposit child's share
                if child_share_mg > 0:
                    wallet_service.deposit(
                        db, dealer_id, child_share_mg,
                        reference_type=f"pos_{metal_type}_profit",
                        reference_id=str(sale.id),
                        description=f"سود {metal_label}ی فروش شمش {bar.serial_code} ({child_share_mg / 1000:.3f} گرم)",
                        asset_code=asset_code,
                    )
                # Deposit parent's share
                if parent_share_mg > 0:
                    wallet_service.deposit(
                        db, parent_rel.parent_dealer_id, parent_share_mg,
                        reference_type=f"sub_dealer_{metal_type}_commission",
                        reference_id=str(sale.id),
                        description=f"کمیسیون زیرمجموعه — فروش {bar.serial_code} ({parent_share_mg / 1000:.3f} گرم)",
                        asset_code=asset_code,
                    )
            else:
                # No parent → full profit to dealer
                wallet_service.deposit(
                    db, dealer_id, metal_profit_mg,
                    reference_type=f"pos_{metal_type}_profit",
                    reference_id=str(sale.id),
                    description=f"سود {metal_label}ی فروش شمش {bar.serial_code} ({metal_profit_mg / 1000:.3f} گرم)",
                    asset_code=asset_code,
                )

        return {
            "success": True,
            "message": f"فروش شمش {bar.serial_code} ثبت شد",
            "sale": sale,
            "metal_profit_mg": metal_profit_mg,
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
        """
        Dealer initiates a buyback — instant process:
        1. Recalculate raw metal value + wage server-side
        2. Deposit raw metal value to owner's wallet (transaction 1)
        3. Deposit wage amount to owner's wallet (transaction 2)
        4. Set buyback status to COMPLETED
        """
        from modules.wallet.service import wallet_service
        from modules.pricing.calculator import calculate_bar_price
        from common.templating import get_setting_from_db

        dealer = self.get_dealer(db, dealer_id)
        if not dealer or not dealer.is_active:
            return {"success": False, "message": "نماینده غیرفعال"}

        bar = db.query(Bar).filter(Bar.serial_code == serial_code.upper()).first()
        if not bar:
            return {"success": False, "message": "شمش با این سریال یافت نشد"}
        if bar.status != BarStatus.SOLD:
            return {"success": False, "message": "فقط شمش‌های فروخته‌شده قابل بازخرید هستند"}

        # Trade toggle guard
        product = bar.product
        bb_metal = (product.metal_type if product else "gold") or "gold"
        try:
            from modules.pricing.trade_guard import require_trade_enabled
            require_trade_enabled(db, bb_metal, "buyback")
        except ValueError as e:
            return {"success": False, "message": str(e)}

        # Prevent duplicate buyback for same bar
        existing = (
            db.query(BuybackRequest)
            .filter(
                BuybackRequest.bar_id == bar.id,
                BuybackRequest.status != BuybackStatus.REJECTED,
            )
            .first()
        )
        if existing:
            return {"success": False, "message": "برای این شمش قبلاً درخواست بازخرید ثبت شده است"}

        if not bar.customer_id:
            return {"success": False, "message": "مالک شمش مشخص نیست"}

        product = bar.product
        if not product:
            return {"success": False, "message": "محصول مرتبط یافت نشد"}

        owner_id = bar.customer_id

        # --- Find the original sale price (at time of purchase) ---
        from modules.order.models import OrderItem, Order

        original_metal_price = None

        # Check DealerSale (POS sale)
        dealer_sale = db.query(DealerSale).filter(DealerSale.bar_id == bar.id).first()
        if dealer_sale and dealer_sale.applied_metal_price:
            original_metal_price = int(dealer_sale.applied_metal_price)

        # Check OrderItem (online order) if not found in POS
        if not original_metal_price:
            order_item = (
                db.query(OrderItem)
                .join(Order, Order.id == OrderItem.order_id)
                .filter(OrderItem.bar_id == bar.id, Order.status == "Paid")
                .first()
            )
            if order_item and order_item.applied_metal_price:
                original_metal_price = int(order_item.applied_metal_price)

        # Fallback to current price only if no sale record found
        _, p_bp, _ = get_product_pricing(db, product)
        if original_metal_price:
            p_price = original_metal_price
        else:
            p_price, p_bp, _ = get_product_pricing(db, product)

        # Raw metal value (no wage, no tax) — based on ORIGINAL sale price
        raw_info = calculate_bar_price(
            weight=product.weight, purity=product.purity,
            wage_percent=0, base_metal_price=p_price,
            tax_percent=0, base_purity=p_bp,
        )
        raw_metal_rial = raw_info.get("total", 0)

        # Buyback wage uses separate buyback_wage_percent (no tax) — based on ORIGINAL sale price
        buyback_pct = float(product.buyback_wage_percent or 0)
        wage_rial = 0
        if buyback_pct > 0:
            bb_info = calculate_bar_price(
                weight=product.weight, purity=product.purity,
                wage_percent=buyback_pct, base_metal_price=p_price,
                tax_percent=0, base_purity=p_bp,
            )
            wage_rial = bb_info.get("wage", 0)

        total_deposit = raw_metal_rial + wage_rial

        buyback = BuybackRequest(
            dealer_id=dealer_id,
            bar_id=bar.id,
            customer_name=customer_name,
            customer_mobile=customer_mobile,
            buyback_price=raw_metal_rial,
            wage_refund_amount=wage_rial,
            wage_refund_customer_id=owner_id,
            description=description,
            status=BuybackStatus.COMPLETED,
        )
        db.add(buyback)
        db.flush()

        # Transaction 1: Raw metal value
        wallet_service.deposit(
            db, owner_id, raw_metal_rial,
            reference_type="buyback",
            reference_id=str(buyback.id),
            description=f"واریز ارزش طلای خام شمش {bar.serial_code}",
            idempotency_key=f"buyback_raw:{buyback.id}",
        )

        # Transaction 2: Wage refund
        if wage_rial > 0:
            wallet_service.deposit(
                db, owner_id, wage_rial,
                reference_type="buyback_wage",
                reference_id=str(buyback.id),
                description=f"واریز مبلغ بازخرید (اجرت) شمش {bar.serial_code}",
                idempotency_key=f"buyback_wage:{buyback.id}",
            )

        # Ownership history
        db.add(OwnershipHistory(
            bar_id=bar.id,
            previous_owner_id=owner_id,
            new_owner_id=owner_id,
            description=f"بازخرید توسط نماینده {dealer.full_name} — مبلغ {total_deposit // 10:,} تومان به کیف پول واریز شد",
        ))

        db.flush()

        return {
            "success": True,
            "message": f"بازخرید شمش {bar.serial_code} انجام شد — مبلغ {raw_metal_rial // 10:,} تومان (طلای خام) + {wage_rial // 10:,} تومان (اجرت) به کیف پول مالک واریز شد",
            "buyback": buyback,
        }

    # approve_buyback / reject_buyback removed — buyback is now instant (no admin approval)

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
        gold_profit_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.metal_profit_mg), 0))
            .filter(DealerSale.dealer_id == dealer_id, DealerSale.metal_type == "gold")
            .scalar()
        )
        silver_profit_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.metal_profit_mg), 0))
            .filter(DealerSale.dealer_id == dealer_id, DealerSale.metal_type == "silver")
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
            "total_gold_profit_mg": gold_profit_mg,
            "total_silver_profit_mg": silver_profit_mg,
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

        # Get tax (metal prices are resolved per-product below)
        from common.templating import get_setting_from_db
        from modules.pricing.models import GOLD_18K
        gold_price = get_price_value(db, GOLD_18K)  # default display price
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
            # Per-product metal pricing
            p_price, p_bp, _ = get_product_pricing(db, p)
            ec_wage = get_end_customer_wage(db, p)
            price_info = calculate_bar_price(
                weight=p.weight, purity=p.purity,
                wage_percent=ec_wage,
                base_metal_price=p_price,
                tax_percent=float(tax_percent),
                base_purity=p_bp,
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
        total_dealers = db.query(User).filter(User.is_dealer == True).count()
        active_dealers = db.query(User).filter(User.is_dealer == True, User.is_active == True).count()
        total_sales = db.query(DealerSale).count()
        total_revenue = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.sale_price), 0)).scalar()
        )
        gold_profit_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.metal_profit_mg), 0))
            .filter(DealerSale.metal_type == "gold")
            .scalar()
        )
        silver_profit_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.metal_profit_mg), 0))
            .filter(DealerSale.metal_type == "silver")
            .scalar()
        )
        pending_buybacks = (
            db.query(BuybackRequest).filter(BuybackRequest.status == BuybackStatus.PENDING).count()
        )
        return {
            "total_dealers": total_dealers,
            "active_dealers": active_dealers,
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "total_gold_profit_mg": gold_profit_mg,
            "total_silver_profit_mg": silver_profit_mg,
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
        from modules.catalog.models import Product

        q = db.query(DealerSale).options(
            joinedload(DealerSale.dealer),
            joinedload(DealerSale.bar).joinedload(Bar.product),
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
        ids_subq = q.with_entities(DealerSale.id).subquery()
        total = q.count()

        if total > 0:
            filtered_ids = db.query(ids_subq.c.id)
            filtered_revenue = (
                db.query(sa_func.coalesce(sa_func.sum(DealerSale.sale_price), 0))
                .filter(DealerSale.id.in_(filtered_ids))
                .scalar()
            )
            filtered_discount_count = (
                db.query(sa_func.count(DealerSale.id))
                .filter(
                    DealerSale.id.in_(filtered_ids),
                    DealerSale.discount_wage_percent > 0,
                )
                .scalar()
            )

            # --- Metal-specific stats using DealerSale.metal_type ---
            def _metal_agg(metal_key: str):
                """Calculate weight, wage_mg, dealer_profit_mg for a metal type."""
                base_filters = [
                    DealerSale.id.in_(filtered_ids),
                    DealerSale.metal_type == metal_key,
                ]
                weight = (
                    db.query(sa_func.coalesce(sa_func.sum(Product.weight), 0))
                    .join(Bar, Bar.product_id == Product.id)
                    .join(DealerSale, DealerSale.bar_id == Bar.id)
                    .filter(*base_filters)
                    .scalar()
                )
                wage_mg = (
                    db.query(sa_func.coalesce(
                        sa_func.sum(Product.weight * Product.wage / 100 * 1000), 0
                    ))
                    .join(Bar, Bar.product_id == Product.id)
                    .join(DealerSale, DealerSale.bar_id == Bar.id)
                    .filter(*base_filters)
                    .scalar()
                )
                dealer_profit = (
                    db.query(sa_func.coalesce(sa_func.sum(DealerSale.metal_profit_mg), 0))
                    .filter(*base_filters)
                    .scalar()
                )
                our = int(wage_mg) - int(dealer_profit)
                return int(float(weight) * 1000), our, int(dealer_profit)

            gold_weight_mg, gold_our_mg, gold_dealer_mg = _metal_agg("gold")
            silver_weight_mg, silver_our_mg, silver_dealer_mg = _metal_agg("silver")
        else:
            filtered_revenue = 0
            filtered_discount_count = 0
            gold_weight_mg = silver_weight_mg = 0
            gold_our_mg = silver_our_mg = 0
            gold_dealer_mg = silver_dealer_mg = 0

        stats = {
            "total": total,
            "total_revenue": filtered_revenue,
            "discount_count": filtered_discount_count,
            # Gold
            "gold_weight_mg": gold_weight_mg,
            "gold_our_profit_mg": gold_our_mg,
            "gold_dealer_profit_mg": gold_dealer_mg,
            # Silver
            "silver_weight_mg": silver_weight_mg,
            "silver_our_profit_mg": silver_our_mg,
            "silver_dealer_profit_mg": silver_dealer_mg,
        }

        # --- Paginate ---
        sales = (
            q.order_by(DealerSale.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return sales, total, stats


    # ------------------------------------------
    # Sub-dealer Management
    # ------------------------------------------

    def get_parent_dealer(self, db: Session, dealer_id: int) -> Optional[User]:
        """Get the parent dealer for a given dealer (if any active relation)."""
        rel = (
            db.query(SubDealerRelation)
            .filter(SubDealerRelation.child_dealer_id == dealer_id, SubDealerRelation.is_active == True)
            .first()
        )
        return rel.parent_dealer if rel else None

    def get_parent_relation(self, db: Session, dealer_id: int) -> Optional[SubDealerRelation]:
        """Get the active parent relation for a dealer."""
        return (
            db.query(SubDealerRelation)
            .filter(SubDealerRelation.child_dealer_id == dealer_id, SubDealerRelation.is_active == True)
            .first()
        )

    def get_sub_dealers(self, db: Session, dealer_id: int) -> List[SubDealerRelation]:
        """Get all active sub-dealer relations for a parent dealer."""
        return (
            db.query(SubDealerRelation)
            .filter(SubDealerRelation.parent_dealer_id == dealer_id, SubDealerRelation.is_active == True)
            .order_by(SubDealerRelation.created_at.desc())
            .all()
        )

    def get_all_sub_dealer_relations(self, db: Session, dealer_id: int = None) -> List[SubDealerRelation]:
        """Admin: list all relations, optionally filtered by parent dealer."""
        q = db.query(SubDealerRelation).order_by(SubDealerRelation.created_at.desc())
        if dealer_id:
            q = q.filter(SubDealerRelation.parent_dealer_id == dealer_id)
        return q.all()

    def create_sub_dealer_relation(
        self, db: Session, parent_id: int, child_id: int,
        commission_split_percent: float = 20.0, admin_note: str = "",
    ) -> Dict[str, Any]:
        """Create parent-child dealer relationship."""
        if parent_id == child_id:
            return {"success": False, "message": "نماینده نمی‌تواند زیرمجموعه خودش باشد"}

        parent = self.get_dealer(db, parent_id)
        if not parent or not parent.is_active:
            return {"success": False, "message": "نماینده بالاسری نامعتبر یا غیرفعال"}

        child = self.get_dealer(db, child_id)
        if not child or not child.is_active:
            return {"success": False, "message": "نماینده زیرمجموعه نامعتبر یا غیرفعال"}

        # Check child doesn't already have an active parent
        existing = (
            db.query(SubDealerRelation)
            .filter(SubDealerRelation.child_dealer_id == child_id, SubDealerRelation.is_active == True)
            .first()
        )
        if existing:
            return {"success": False, "message": f"این نماینده قبلاً زیرمجموعه «{existing.parent_dealer.full_name}» است"}

        # Prevent circular: parent cannot be child's sub-dealer
        reverse = (
            db.query(SubDealerRelation)
            .filter(
                SubDealerRelation.child_dealer_id == parent_id,
                SubDealerRelation.parent_dealer_id == child_id,
                SubDealerRelation.is_active == True,
            )
            .first()
        )
        if reverse:
            return {"success": False, "message": "ارجاع دوری: نماینده بالاسری خودش زیرمجموعه این نماینده است"}

        if not (0 <= commission_split_percent <= 100):
            return {"success": False, "message": "درصد تقسیم سود باید بین ۰ تا ۱۰۰ باشد"}

        rel = SubDealerRelation(
            parent_dealer_id=parent_id,
            child_dealer_id=child_id,
            commission_split_percent=commission_split_percent,
            admin_note=admin_note or None,
        )
        db.add(rel)
        db.flush()
        return {"success": True, "message": "ارتباط زیرمجموعه ایجاد شد", "relation": rel}

    def deactivate_sub_dealer_relation(self, db: Session, relation_id: int) -> Dict[str, Any]:
        """Soft-deactivate a sub-dealer relationship."""
        rel = db.query(SubDealerRelation).filter(SubDealerRelation.id == relation_id).first()
        if not rel:
            return {"success": False, "message": "ارتباط یافت نشد"}
        if not rel.is_active:
            return {"success": False, "message": "این ارتباط قبلاً غیرفعال شده"}

        rel.is_active = False
        rel.deactivated_at = now_utc()
        db.flush()
        return {"success": True, "message": "ارتباط زیرمجموعه غیرفعال شد"}

    def get_sub_dealer_commission_stats(self, db: Session, parent_id: int) -> Dict[str, Any]:
        """Aggregate commission earned from all sub-dealers."""
        total_gold_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.parent_commission_mg), 0))
            .filter(DealerSale.parent_dealer_id == parent_id, DealerSale.metal_type == "gold")
            .scalar()
        )
        total_silver_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.parent_commission_mg), 0))
            .filter(DealerSale.parent_dealer_id == parent_id, DealerSale.metal_type == "silver")
            .scalar()
        )
        sale_count = (
            db.query(DealerSale)
            .filter(DealerSale.parent_dealer_id == parent_id)
            .count()
        )
        return {
            "total_gold_commission_mg": int(total_gold_mg),
            "total_silver_commission_mg": int(total_silver_mg),
            "total_sales_from_subs": sale_count,
        }

    # ------------------------------------------
    # Dealer Analytics
    # ------------------------------------------

    def get_daily_sales_data(self, db: Session, dealer_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily sales count + revenue for the last N days."""
        from datetime import timedelta
        cutoff = now_utc() - timedelta(days=days)

        rows = (
            db.query(
                sa_func.cast(DealerSale.created_at, sa_func.DATE if hasattr(sa_func, 'DATE') else None).label("dt")
                if False else  # PostgreSQL specific cast
                sa_func.date(DealerSale.created_at).label("dt"),
                sa_func.count(DealerSale.id).label("cnt"),
                sa_func.coalesce(sa_func.sum(DealerSale.sale_price), 0).label("rev"),
                sa_func.coalesce(
                    sa_func.sum(
                        sa_case(
                            (DealerSale.metal_type == "gold", DealerSale.metal_profit_mg),
                            else_=0,
                        )
                    ), 0
                ).label("gold_mg"),
                sa_func.coalesce(
                    sa_func.sum(
                        sa_case(
                            (DealerSale.metal_type == "silver", DealerSale.metal_profit_mg),
                            else_=0,
                        )
                    ), 0
                ).label("silver_mg"),
            )
            .filter(DealerSale.dealer_id == dealer_id, DealerSale.created_at >= cutoff)
            .group_by("dt")
            .order_by("dt")
            .all()
        )

        result = []
        for r in rows:
            dt_str = str(r.dt) if r.dt else ""
            result.append({
                "date": dt_str,
                "count": int(r.cnt),
                "revenue": int(r.rev),
                "gold_profit_mg": int(r.gold_mg),
                "silver_profit_mg": int(r.silver_mg),
            })
        return result

    def get_metal_profit_breakdown(self, db: Session, dealer_id: int) -> Dict[str, Any]:
        """Gold vs silver profit aggregate."""
        gold_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.metal_profit_mg), 0))
            .filter(DealerSale.dealer_id == dealer_id, DealerSale.metal_type == "gold")
            .scalar()
        )
        silver_mg = (
            db.query(sa_func.coalesce(sa_func.sum(DealerSale.metal_profit_mg), 0))
            .filter(DealerSale.dealer_id == dealer_id, DealerSale.metal_type == "silver")
            .scalar()
        )
        gold_count = (
            db.query(DealerSale)
            .filter(DealerSale.dealer_id == dealer_id, DealerSale.metal_type == "gold")
            .count()
        )
        silver_count = (
            db.query(DealerSale)
            .filter(DealerSale.dealer_id == dealer_id, DealerSale.metal_type == "silver")
            .count()
        )
        return {
            "gold_mg": int(gold_mg),
            "silver_mg": int(silver_mg),
            "gold_count": gold_count,
            "silver_count": silver_count,
        }

    def get_period_comparison(self, db: Session, dealer_id: int) -> Dict[str, Any]:
        """This month vs last month stats."""
        from datetime import timedelta
        today = now_utc()
        # First day of current month
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # First day of last month
        if month_start.month == 1:
            last_month_start = month_start.replace(year=month_start.year - 1, month=12)
        else:
            last_month_start = month_start.replace(month=month_start.month - 1)

        def _period_stats(start, end):
            q = db.query(
                sa_func.count(DealerSale.id),
                sa_func.coalesce(sa_func.sum(DealerSale.sale_price), 0),
                sa_func.coalesce(sa_func.sum(DealerSale.metal_profit_mg), 0),
            ).filter(
                DealerSale.dealer_id == dealer_id,
                DealerSale.created_at >= start,
                DealerSale.created_at < end,
            )
            row = q.one()
            return {"sales": int(row[0]), "revenue": int(row[1]), "profit_mg": int(row[2])}

        this_m = _period_stats(month_start, today)
        last_m = _period_stats(last_month_start, month_start)

        # Calculate percentage change
        change = {}
        for key in ("sales", "revenue", "profit_mg"):
            if last_m[key] > 0:
                change[key] = round((this_m[key] - last_m[key]) / last_m[key] * 100, 1)
            else:
                change[key] = 100.0 if this_m[key] > 0 else 0.0

        return {"this_month": this_m, "last_month": last_m, "change_pct": change}

    def get_inventory_value(self, db: Session, dealer_id: int) -> Dict[str, Any]:
        """Current inventory value at spot prices."""
        from modules.catalog.models import Product
        from modules.pricing.models import GOLD_18K, SILVER

        gold_price = get_price_value(db, GOLD_18K)
        silver_price = get_price_value(db, SILVER)

        bars = (
            db.query(Bar)
            .filter(Bar.dealer_id == dealer_id, Bar.status == BarStatus.ASSIGNED)
            .all()
        )

        gold_val = 0
        silver_val = 0
        for bar in bars:
            p = bar.product
            if not p:
                continue
            w = float(p.weight) if p.weight else 0
            purity = float(p.purity) if p.purity else 750
            mt = getattr(p, "metal_type", "gold") or "gold"
            if mt == "silver":
                unit = (silver_price / 999) * purity if silver_price else 0
                silver_val += int(w * unit)
            else:
                unit = (gold_price / 750) * purity if gold_price else 0
                gold_val += int(w * unit)

        return {
            "gold_value_rial": gold_val,
            "silver_value_rial": silver_val,
            "total_value_rial": gold_val + silver_val,
        }

    # ------------------------------------------
    # Dealer Physical Inventory
    # ------------------------------------------

    def get_inventory_at_location(
        self, db: Session, dealer_id: int,
        metal_type: str = "", status_filter: str = "",
        page: int = 1, per_page: int = 30,
    ) -> Tuple[List[Bar], int, Dict[str, Any]]:
        """Get all bars at dealer's location with optional filters + summary stats."""
        from modules.catalog.models import Product

        q = db.query(Bar).filter(Bar.dealer_id == dealer_id)

        if metal_type:
            q = q.join(Product, Bar.product_id == Product.id).filter(Product.metal_type == metal_type)
        if status_filter:
            q = q.filter(Bar.status == status_filter)

        total = q.count()
        bars = (
            q.order_by(Bar.status, Bar.serial_code)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        stats = self._calc_inventory_stats(db, dealer_id)
        return bars, total, stats

    def _calc_inventory_stats(self, db: Session, dealer_id: int) -> Dict[str, Any]:
        """Aggregate inventory statistics for a dealer location."""
        from modules.catalog.models import Product

        all_bars = (
            db.query(Bar)
            .filter(Bar.dealer_id == dealer_id)
            .all()
        )

        total_bars = len(all_bars)
        gold_weight_g = 0.0
        silver_weight_g = 0.0
        gold_bars = 0
        silver_bars = 0
        by_status: Dict[str, int] = {}

        for bar in all_bars:
            # Count by status
            st = bar.status if isinstance(bar.status, str) else bar.status.value
            by_status[st] = by_status.get(st, 0) + 1

            p = bar.product
            if not p:
                continue
            w = float(p.weight) if p.weight else 0
            mt = getattr(p, "metal_type", "gold") or "gold"
            if mt == "silver":
                silver_bars += 1
                silver_weight_g += w
            else:
                gold_bars += 1
                gold_weight_g += w

        return {
            "total_bars": total_bars,
            "gold_bars": gold_bars,
            "silver_bars": silver_bars,
            "gold_weight_g": round(gold_weight_g, 3),
            "silver_weight_g": round(silver_weight_g, 3),
            "by_status": by_status,
            "assigned_count": by_status.get("Assigned", 0),
            "reserved_count": by_status.get("Reserved", 0),
            "sold_count": by_status.get("Sold", 0),
        }


    # ------------------------------------------
    # B2B Bulk Orders
    # ------------------------------------------

    def get_b2b_catalog_for_dealer(self, db: Session, dealer_id: int) -> List[Dict[str, Any]]:
        """Get products with dealer tier pricing for B2B order page."""
        from modules.catalog.models import Product, ProductImage
        from modules.pricing.calculator import calculate_bar_price
        from common.templating import get_setting_from_db

        dealer = self.get_dealer(db, dealer_id)
        if not dealer:
            return []

        tax_percent = float(get_setting_from_db(db, "tax_percent", "10"))

        # Get all active products
        products = (
            db.query(Product)
            .filter(Product.is_active == True)
            .order_by(Product.name)
            .all()
        )

        if not products:
            return []

        product_ids = [p.id for p in products]

        # Batch: default images
        default_images = db.query(ProductImage).filter(
            ProductImage.product_id.in_(product_ids),
            ProductImage.is_default == True,
        ).all()
        img_map = {img.product_id: img.file_path for img in default_images}

        # Batch: dealer tier wages
        dealer_wage_map: Dict[int, float] = {}
        if dealer.tier_id:
            from modules.catalog.models import ProductTierWage
            dealer_wages = db.query(ProductTierWage).filter(
                ProductTierWage.product_id.in_(product_ids),
                ProductTierWage.tier_id == dealer.tier_id,
            ).all()
            dealer_wage_map = {dw.product_id: float(dw.wage_percent) for dw in dealer_wages}

        # Batch: warehouse stock count per product (ASSIGNED bars at warehouse locations)
        warehouse_stock: Dict[int, int] = {}
        wh_rows = (
            db.query(Bar.product_id, sa_func.count(Bar.id))
            .join(User, Bar.dealer_id == User.id)
            .filter(
                Bar.status == BarStatus.ASSIGNED,
                Bar.product_id.in_(product_ids),
                User.is_warehouse == True,
            )
            .group_by(Bar.product_id)
            .all()
        )
        for pid, cnt in wh_rows:
            warehouse_stock[pid] = cnt

        result = []
        for p in products:
            p_price, p_bp, _ = get_product_pricing(db, p)
            dealer_wage_pct = dealer_wage_map.get(p.id, 0.0)

            # Calculate dealer price (using dealer's tier wage)
            if dealer_wage_pct > 0:
                price_info = calculate_bar_price(
                    weight=p.weight, purity=p.purity,
                    wage_percent=dealer_wage_pct,
                    base_metal_price=p_price,
                    tax_percent=tax_percent,
                    base_purity=p_bp,
                )
            else:
                # Fallback to product's default wage if no tier wage set
                price_info = calculate_bar_price(
                    weight=p.weight, purity=p.purity,
                    wage_percent=float(p.wage),
                    base_metal_price=p_price,
                    tax_percent=tax_percent,
                    base_purity=p_bp,
                )

            stock = warehouse_stock.get(p.id, 0)
            if stock == 0:
                continue  # Skip products with no warehouse stock

            result.append({
                "product": p,
                "unit_price": price_info.get("total", 0),
                "price_breakdown": price_info,
                "dealer_wage_pct": dealer_wage_pct or float(p.wage),
                "metal_price": p_price,
                "base_purity": p_bp,
                "tax_percent": tax_percent,
                "stock": stock,
                "image": img_map.get(p.id),
            })

        return result

    def create_b2b_order(
        self, db: Session, dealer_id: int,
        items_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create a B2B order with items, pricing locked at creation time.

        items_data: [{"product_id": int, "quantity": int}, ...]
        """
        from modules.catalog.models import Product
        from modules.pricing.calculator import calculate_bar_price
        from common.templating import get_setting_from_db

        dealer = self.get_dealer(db, dealer_id)
        if not dealer or not dealer.is_active:
            return {"success": False, "message": "نماینده غیرفعال یا نامعتبر"}

        if not items_data:
            return {"success": False, "message": "حداقل یک محصول انتخاب کنید"}

        tax_percent = float(get_setting_from_db(db, "tax_percent", "10"))

        # Ensure metal prices are fresh + trade toggle enabled
        from modules.pricing.service import require_fresh_price
        from modules.pricing.trade_guard import require_trade_enabled
        from modules.pricing.models import GOLD_18K
        try:
            require_fresh_price(db, GOLD_18K)
        except ValueError as e:
            return {"success": False, "message": str(e)}

        # Trade toggle guard: check each product's metal type
        checked_b2b_metals = set()
        for it in items_data:
            prod = db.query(Product).get(it["product_id"])
            if prod:
                mt = prod.metal_type or "gold"
                if mt not in checked_b2b_metals:
                    try:
                        require_trade_enabled(db, mt, "b2b_order")
                    except ValueError as e:
                        return {"success": False, "message": str(e)}
                    checked_b2b_metals.add(mt)

        # Get dealer's tier wage map
        dealer_wage_map: Dict[int, float] = {}
        if dealer.tier_id:
            from modules.catalog.models import ProductTierWage
            pids = [it["product_id"] for it in items_data]
            dealer_wages = db.query(ProductTierWage).filter(
                ProductTierWage.product_id.in_(pids),
                ProductTierWage.tier_id == dealer.tier_id,
            ).all()
            dealer_wage_map = {dw.product_id: float(dw.wage_percent) for dw in dealer_wages}

        order = B2BOrder(
            dealer_id=dealer_id,
            status=B2BOrderStatus.SUBMITTED,
            applied_tax_percent=tax_percent,
        )
        db.add(order)
        db.flush()

        total_amount = 0
        for item_data in items_data:
            product = db.query(Product).filter(Product.id == item_data["product_id"]).first()
            if not product or not product.is_active:
                db.rollback()
                return {"success": False, "message": f"محصول با شناسه {item_data['product_id']} نامعتبر است"}

            qty = int(item_data["quantity"])
            if qty <= 0:
                continue

            # Check warehouse stock
            wh_stock = (
                db.query(sa_func.count(Bar.id))
                .join(User, Bar.dealer_id == User.id)
                .filter(
                    Bar.product_id == product.id,
                    Bar.status == BarStatus.ASSIGNED,
                    User.is_warehouse == True,
                )
                .scalar()
            )
            if wh_stock < qty:
                db.rollback()
                return {"success": False, "message": f"موجودی انبار {product.name} کافی نیست (موجود: {wh_stock}, درخواست: {qty})"}

            # Calculate dealer price
            p_price, p_bp, _ = get_product_pricing(db, product)
            dealer_wage_pct = dealer_wage_map.get(product.id, float(product.wage))
            price_info = calculate_bar_price(
                weight=product.weight, purity=product.purity,
                wage_percent=dealer_wage_pct,
                base_metal_price=p_price,
                tax_percent=tax_percent,
                base_purity=p_bp,
            )
            unit_price = price_info.get("total", 0)
            line_total = unit_price * qty

            item = B2BOrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                applied_wage_percent=dealer_wage_pct,
                applied_metal_price=p_price,
                unit_price=unit_price,
                line_total=line_total,
            )
            db.add(item)
            total_amount += line_total

        if total_amount == 0:
            db.rollback()
            return {"success": False, "message": "سفارش خالی — حداقل یک محصول با تعداد مثبت انتخاب کنید"}

        order.total_amount = total_amount
        db.flush()

        return {
            "success": True,
            "message": f"سفارش عمده #{order.id} ثبت شد — در انتظار تایید ادمین",
            "order": order,
        }

    def get_b2b_order(self, db: Session, order_id: int, dealer_id: int = None) -> Optional[B2BOrder]:
        """Get a B2B order with items. If dealer_id given, verify ownership."""
        from sqlalchemy.orm import joinedload
        q = db.query(B2BOrder).options(
            joinedload(B2BOrder.items).joinedload(B2BOrderItem.product),
            joinedload(B2BOrder.dealer),
        ).filter(B2BOrder.id == order_id)
        if dealer_id:
            q = q.filter(B2BOrder.dealer_id == dealer_id)
        return q.first()

    def get_b2b_orders(
        self, db: Session, dealer_id: int, page: int = 1, per_page: int = 20,
    ) -> Tuple[List[B2BOrder], int]:
        """Get paginated B2B orders for a dealer."""
        q = db.query(B2BOrder).filter(B2BOrder.dealer_id == dealer_id)
        total = q.count()
        orders = q.order_by(B2BOrder.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return orders, total

    def list_all_b2b_orders_admin(
        self, db: Session,
        status_filter: str = "",
        dealer_id: int = None,
        page: int = 1, per_page: int = 30,
    ) -> Tuple[List[B2BOrder], int]:
        """Admin: list all B2B orders with optional filters."""
        from sqlalchemy.orm import joinedload
        q = db.query(B2BOrder).options(joinedload(B2BOrder.dealer))
        if status_filter:
            q = q.filter(B2BOrder.status == status_filter)
        if dealer_id:
            q = q.filter(B2BOrder.dealer_id == dealer_id)
        total = q.count()
        orders = q.order_by(B2BOrder.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return orders, total

    def approve_b2b_order(
        self, db: Session, order_id: int, admin_id: int, admin_note: str = "",
    ) -> Dict[str, Any]:
        """Admin approves a B2B order."""
        order = db.query(B2BOrder).filter(B2BOrder.id == order_id).first()
        if not order:
            return {"success": False, "message": "سفارش یافت نشد"}
        if order.status != B2BOrderStatus.SUBMITTED:
            return {"success": False, "message": f"فقط سفارش‌های در انتظار تایید قابل تایید هستند (وضعیت فعلی: {order.status_label})"}

        order.status = B2BOrderStatus.APPROVED
        order.approved_by = admin_id
        order.approved_at = now_utc()
        order.admin_note = admin_note or order.admin_note
        db.flush()
        return {"success": True, "message": f"سفارش #{order.id} تایید شد — آماده پرداخت توسط نماینده"}

    def reject_b2b_order(
        self, db: Session, order_id: int, admin_id: int, admin_note: str = "",
    ) -> Dict[str, Any]:
        """Admin rejects a B2B order."""
        order = db.query(B2BOrder).filter(B2BOrder.id == order_id).first()
        if not order:
            return {"success": False, "message": "سفارش یافت نشد"}
        if order.status != B2BOrderStatus.SUBMITTED:
            return {"success": False, "message": f"فقط سفارش‌های در انتظار تایید قابل رد هستند (وضعیت فعلی: {order.status_label})"}

        order.status = B2BOrderStatus.REJECTED
        order.approved_by = admin_id
        order.admin_note = admin_note or order.admin_note
        db.flush()
        return {"success": True, "message": f"سفارش #{order.id} رد شد"}

    def pay_b2b_order(self, db: Session, order_id: int, dealer_id: int) -> Dict[str, Any]:
        """Dealer pays for an approved B2B order via wallet."""
        from modules.wallet.service import wallet_service

        order = db.query(B2BOrder).filter(
            B2BOrder.id == order_id, B2BOrder.dealer_id == dealer_id,
        ).first()
        if not order:
            return {"success": False, "message": "سفارش یافت نشد"}
        if order.status != B2BOrderStatus.APPROVED:
            return {"success": False, "message": f"فقط سفارش‌های تایید شده قابل پرداخت هستند (وضعیت فعلی: {order.status_label})"}

        # Withdraw from wallet
        try:
            wallet_service.withdraw(
                db, dealer_id, order.total_amount,
                reference_type="b2b_order_payment",
                reference_id=str(order.id),
                description=f"پرداخت سفارش عمده #{order.id} ({order.total_amount // 10:,} تومان)",
                consume_credit=True,
            )
        except ValueError as e:
            return {"success": False, "message": str(e)}

        order.status = B2BOrderStatus.PAID
        order.payment_method = "wallet"
        order.paid_at = now_utc()
        db.flush()
        return {"success": True, "message": f"سفارش #{order.id} پرداخت شد — در انتظار تحویل شمش‌ها"}

    def fulfill_b2b_order(self, db: Session, order_id: int, admin_id: int) -> Dict[str, Any]:
        """Admin fulfills a paid B2B order by assigning bars from warehouse to dealer."""
        from modules.inventory.models import DealerTransfer, TransferType
        from sqlalchemy.orm import joinedload

        order = (
            db.query(B2BOrder)
            .options(joinedload(B2BOrder.items))
            .filter(B2BOrder.id == order_id)
            .first()
        )
        if not order:
            return {"success": False, "message": "سفارش یافت نشد"}
        if order.status != B2BOrderStatus.PAID:
            return {"success": False, "message": f"فقط سفارش‌های پرداخت‌شده قابل تحویل هستند (وضعیت فعلی: {order.status_label})"}

        # Phase 1: Verify ALL items have sufficient warehouse stock before transferring any
        all_bars_to_transfer = []
        for item in order.items:
            available_bars = (
                db.query(Bar)
                .join(User, Bar.dealer_id == User.id)
                .filter(
                    Bar.product_id == item.product_id,
                    Bar.status == BarStatus.ASSIGNED,
                    User.is_warehouse == True,
                )
                .with_for_update(skip_locked=True)
                .limit(item.quantity)
                .all()
            )

            if len(available_bars) < item.quantity:
                return {
                    "success": False,
                    "message": f"موجودی انبار محصول «{item.product.name}» کافی نیست "
                               f"(نیاز: {item.quantity}، موجود: {len(available_bars)}). "
                               f"ابتدا موجودی انبار مرکزی را تکمیل کنید.",
                }
            all_bars_to_transfer.extend(available_bars)

        # Phase 2: All stock verified — now transfer atomically
        for bar in all_bars_to_transfer:
            old_dealer_id = bar.dealer_id
            bar.dealer_id = order.dealer_id

            transfer = DealerTransfer(
                bar_id=bar.id,
                from_dealer_id=old_dealer_id,
                to_dealer_id=order.dealer_id,
                transferred_by=admin_id,
                description=f"تحویل سفارش عمده #{order.id}",
                transfer_type=TransferType.B2B_FULFILLMENT,
                reference_type="b2b_order",
                reference_id=order.id,
            )
            db.add(transfer)

        order.status = B2BOrderStatus.FULFILLED
        order.fulfilled_at = now_utc()
        db.flush()
        return {
            "success": True,
            "message": f"سفارش #{order.id} تحویل شد — {order.total_items} شمش به نمایندگی منتقل شد",
        }

    def cancel_b2b_order(self, db: Session, order_id: int, dealer_id: int) -> Dict[str, Any]:
        """Dealer cancels a B2B order. Refund if already paid."""
        from modules.wallet.service import wallet_service

        order = db.query(B2BOrder).filter(
            B2BOrder.id == order_id, B2BOrder.dealer_id == dealer_id,
        ).first()
        if not order:
            return {"success": False, "message": "سفارش یافت نشد"}

        if order.status in (B2BOrderStatus.FULFILLED, B2BOrderStatus.CANCELLED):
            return {"success": False, "message": f"سفارش در وضعیت {order.status_label} قابل لغو نیست"}

        # Refund if paid
        if order.status == B2BOrderStatus.PAID:
            wallet_service.deposit(
                db, dealer_id, order.total_amount,
                reference_type="b2b_order_refund",
                reference_id=str(order.id),
                description=f"بازگشت وجه سفارش عمده #{order.id} ({order.total_amount // 10:,} تومان)",
            )

        order.status = B2BOrderStatus.CANCELLED
        db.flush()

        refund_msg = " — وجه پرداختی به کیف پول بازگشت" if order.payment_method else ""
        return {"success": True, "message": f"سفارش #{order.id} لغو شد{refund_msg}"}


    # ------------------------------------------
    # Warehouse Distribution (Transfer to Dealer)
    # ------------------------------------------

    def transfer_bars_to_dealer(
        self, db: Session, from_dealer_id: int,
        bar_ids: List[int], to_dealer_id: int, description: str = "",
    ) -> Dict[str, Any]:
        """
        Dealer with can_distribute=True transfers selected bars to another dealer.
        No admin approval needed — direct transfer.
        """
        from modules.inventory.models import DealerTransfer, TransferType
        from modules.inventory.service import inventory_service

        # Validate from-dealer has distribution permission
        from_dealer = self.get_dealer(db, from_dealer_id)
        if not from_dealer or not from_dealer.can_distribute:
            return {"success": False, "message": "شما دسترسی انتقال شمش ندارید"}

        # Validate to-dealer
        if from_dealer_id == to_dealer_id:
            return {"success": False, "message": "مبدا و مقصد نمی‌توانند یکی باشند"}
        to_dealer = self.get_dealer(db, to_dealer_id)
        if not to_dealer or not to_dealer.is_active:
            return {"success": False, "message": "نماینده مقصد نامعتبر یا غیرفعال است"}

        if not bar_ids:
            return {"success": False, "message": "هیچ شمشی انتخاب نشده است"}

        # Validate all bars belong to this dealer and are ASSIGNED
        bars = (
            db.query(Bar)
            .filter(
                Bar.id.in_(bar_ids),
                Bar.dealer_id == from_dealer_id,
                Bar.status == BarStatus.ASSIGNED,
            )
            .all()
        )
        if len(bars) != len(bar_ids):
            return {
                "success": False,
                "message": f"برخی شمش‌ها نامعتبر هستند (انتخاب: {len(bar_ids)}، معتبر: {len(bars)})",
            }

        # Transfer each bar
        for bar in bars:
            inventory_service.transfer_bar_to_dealer(
                db,
                bar_id=bar.id,
                to_dealer_id=to_dealer_id,
                transferred_by=from_dealer.full_name,
                description=description or f"توزیع به {to_dealer.full_name}",
                transfer_type=TransferType.WAREHOUSE_DISTRIBUTION,
            )

        db.flush()
        return {
            "success": True,
            "message": f"{len(bars)} شمش به {to_dealer.full_name} منتقل شد",
            "count": len(bars),
        }

    def get_transfer_history(
        self, db: Session, dealer_id: int,
        page: int = 1, per_page: int = 30,
    ) -> Tuple[List, int]:
        """Get transfer history for a dealer (both sent and received)."""
        from modules.inventory.models import DealerTransfer

        q = db.query(DealerTransfer).filter(
            or_(
                DealerTransfer.from_dealer_id == dealer_id,
                DealerTransfer.to_dealer_id == dealer_id,
            )
        )
        total = q.count()
        items = (
            q.order_by(DealerTransfer.transferred_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total


dealer_service = DealerService()
