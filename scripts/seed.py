"""
TalaMala v4 - Comprehensive Database Seeder
==============================================
Seeds ALL modules with initial data for testing.

Usage:
    python scripts/seed.py          # Full seed
    python scripts/seed.py --reset  # Drop all data and reseed

Modules seeded:
  1. Admin users (admin + operator)
  2. Test customers
  3. System settings (gold price, tax, shipping, etc.)
  4. Products (TalaMala v2 gold bar weights)
  5. Card designs + Package types + Batches
  6. Locations (branches + postal hub)
  7. Bars (assigned, with location)
  8. Sample coupons (public + mobile-restricted)
  9. Test wallet credit
"""

import sys
import os
import io
import random
import string
import shutil

# Fix Windows console encoding for Persian text
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal, Base, engine
from modules.admin.models import SystemUser, SystemSetting
from modules.customer.models import Customer
from modules.customer.address_models import GeoProvince, GeoCity, GeoDistrict, CustomerAddress
from modules.catalog.models import (
    ProductCategory, ProductCategoryLink, Product, ProductImage, CardDesign, CardDesignImage,
    PackageType, PackageTypeImage, Batch, BatchImage, ProductTierWage,
)
from modules.inventory.models import (
    Bar, BarImage, OwnershipHistory, BarStatus,
    DealerTransfer, BarTransfer,
)
from modules.cart.models import Cart, CartItem
from modules.order.models import Order, OrderItem
from modules.wallet.models import Account, LedgerEntry, WalletTopup, WithdrawalRequest, OwnerType
from modules.coupon.models import Coupon, CouponMobile, CouponUsage, CouponCategory
from modules.dealer.models import Dealer, DealerTier, DealerSale, BuybackRequest
from modules.ticket.models import Ticket, TicketMessage, TicketAttachment, TicketStatus, TicketPriority, TicketCategory, SenderType
from modules.review.models import Review, ReviewImage, ProductComment, CommentImage, CommentLike
from modules.dealer_request.models import DealerRequest, DealerRequestAttachment


def generate_serial() -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))


def ensure_tables():
    """Create all tables if they don't exist (safe to call multiple times)."""
    print("[0/9] Ensuring all tables exist...")
    Base.metadata.create_all(bind=engine)
    print("  + All tables OK\n")


def seed():
    db = SessionLocal()
    try:
        print("=" * 50)
        print("  TalaMala v4 — Comprehensive Seeder")
        print("=" * 50)

        # Ensure all tables exist first
        ensure_tables()

        # ==========================================
        # 1. Admin Users
        # ==========================================
        print("\n[1/9] Admin Users")

        admins_data = [
            {"mobile": "09123456789", "full_name": "مدیر سیستم", "role": "admin"},
            {"mobile": "09121111111", "full_name": "اپراتور تهران", "role": "operator"},
            {"mobile": "09121023589", "full_name": "ادمین ۱", "role": "admin"},
            {"mobile": "09120725564", "full_name": "ادمین ۲", "role": "admin"},
        ]
        for data in admins_data:
            existing = db.query(SystemUser).filter(SystemUser.mobile == data["mobile"]).first()
            if not existing:
                user_obj = SystemUser(**data)
                db.add(user_obj)
                print(f"  + {data['role']}: {data['mobile']} ({data['full_name']})")
            else:
                user_obj = existing
                print(f"  = exists: {data['mobile']}")

        # Set operator permissions (after flush to ensure objects exist)
        db.flush()
        op_user = db.query(SystemUser).filter(SystemUser.mobile == "09121111111").first()
        if op_user:
            op_user.permissions = ["dashboard", "orders", "inventory", "tickets", "customers"]
            print(f"  ~ operator permissions set: {op_user.permissions}")

        # ==========================================
        # 2. Test Customers
        # ==========================================
        print("\n[2/9] Test Customers")

        customers_data = [
            {
                "mobile": "09351234567", "national_id": "0012345678",
                "first_name": "علی", "last_name": "رضایی",
                "customer_type": "real",
                "postal_code": "1234567890",
                "address": "تهران، خیابان ولیعصر، پلاک ۱۰۰",
                "phone": "02112345678",
            },
            {
                "mobile": "09359876543", "national_id": "0087654321",
                "first_name": "مریم", "last_name": "احمدی",
                "customer_type": "legal",
                "company_name": "شرکت زرین تجارت",
                "economic_code": "411111111111",
                "postal_code": "9876543210",
                "address": "اصفهان، خیابان چهارباغ، پلاک ۵۰",
                "phone": "03132005678",
            },
            {
                "mobile": "09131112233", "national_id": "1234567890",
                "first_name": "رضا", "last_name": "محمدی",
                "customer_type": "real",
                "postal_code": "1122334455",
                "address": "شیراز، خیابان زند، پلاک ۲۰",
            },
        ]
        for data in customers_data:
            existing = db.query(Customer).filter(Customer.mobile == data["mobile"]).first()
            if not existing:
                db.add(Customer(**data))
                print(f"  + {data['first_name']} {data['last_name']}: {data['mobile']}")
            else:
                print(f"  = exists: {data['mobile']}")

        db.flush()

        # ==========================================
        # 3. System Settings
        # ==========================================
        print("\n[3/9] System Settings")

        settings_data = {
            "site_name":            ("طلاملا", "نام سایت"),
            "site_logo":            ("", "لوگوی سایت"),
            "support_phone":        ("02112345678", "شماره پشتیبانی"),
            "support_telegram":     ("@talamala", "تلگرام پشتیبانی"),
            "gold_price":           ("52000000", "قیمت طلای ۱۸ عیار هر گرم (ریال)"),
            "silver_price":         ("550000", "قیمت نقره خالص هر گرم (ریال)"),
            "gold_price_source":    ("tgju", "منبع قیمت طلا"),
            "tax_percent":          ("10", "درصد مالیات بر ارزش افزوده"),
            "min_order_amount":     ("10000000", "حداقل مبلغ سفارش (ریال)"),
            "reservation_minutes":  ("15", "مدت زمان رزرو (دقیقه)"),
            "shipping_cost":        ("500000", "هزینه ارسال پستی (ریال)"),
            "insurance_percent":    ("1.5", "درصد بیمه پست"),
            "insurance_cap":        ("500000000", "سقف بیمه پست (ریال)"),
            "gold_spread_percent":  ("2", "اسپرد تبدیل ریال به طلا (درصد)"),
        }

        for key, (value, desc) in settings_data.items():
            existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if not existing:
                db.add(SystemSetting(key=key, value=value, description=desc))
                print(f"  + {key} = {value}")
            else:
                print(f"  = exists: {key}")

        db.flush()

        # ==========================================
        # 4. Card Designs + Package Types + Batches
        # ==========================================
        print("\n[4/9] Catalog Accessories")

        for name in ["طرح کلاسیک", "طرح مدرن", "طرح هدیه", "طرح نوروز"]:
            if not db.query(CardDesign).filter(CardDesign.name == name).first():
                db.add(CardDesign(name=name))
                print(f"  + Design: {name}")

        pkg_data = [
            {"name": "جعبه استاندارد", "price": 0},
            {"name": "جعبه لوکس", "price": 5_000_000},
            {"name": "جعبه هدیه ویژه", "price": 15_000_000},
            {"name": "پاکت ساده", "price": 1_000_000},
        ]
        for pd in pkg_data:
            existing = db.query(PackageType).filter(PackageType.name == pd["name"]).first()
            if not existing:
                db.add(PackageType(name=pd["name"], price=pd["price"], is_active=True))
                print(f"  + Package: {pd['name']} ({pd['price']} rial)")
            else:
                existing.price = pd["price"]
                print(f"  = Package: {pd['name']} (price updated)")

        batches_data = [
            {"batch_number": "B-1403-001", "melt_number": "M-001", "operator": "استاد کریمی", "purity": 750},
            {"batch_number": "B-1403-002", "melt_number": "M-002", "operator": "استاد کریمی", "purity": 750},
            {"batch_number": "B-1403-003", "melt_number": "M-003", "operator": "استاد احمدی", "purity": 750},
        ]
        for bd in batches_data:
            if not db.query(Batch).filter(Batch.batch_number == bd["batch_number"]).first():
                db.add(Batch(**bd))
                print(f"  + Batch: {bd['batch_number']}")

        db.flush()

        # ==========================================
        # 4.5 Product Categories
        # ==========================================
        print("\n[4.5] Product Categories")

        categories_data = [
            ("شمش طلا طلاملا", "gold-talamala", 1),
            ("شمش طلا سرمایه‌ای", "gold-investment", 2),
            ("شمش نقره طلاملا", "silver-talamala", 3),
            ("شمش نقره سرمایه‌ای", "silver-investment", 4),
        ]

        cat_map = {}
        for cat_name, cat_slug, sort_order in categories_data:
            existing = db.query(ProductCategory).filter(ProductCategory.slug == cat_slug).first()
            if not existing:
                cat = ProductCategory(name=cat_name, slug=cat_slug, sort_order=sort_order, is_active=True)
                db.add(cat)
                db.flush()
                cat_map[cat_slug] = cat
                print(f"  + {cat_name}")
            else:
                cat_map[cat_slug] = existing
                print(f"  = exists: {cat_name}")

        db.flush()

        # ==========================================
        # 5. Products (Real products from _private data)
        # ==========================================
        print("\n[5/9] Products (44 = 11 weights × 4 types)")

        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        IMG_SRC_BASE = os.path.join(PROJECT_ROOT, "_private", "عکس محصولات")
        IMG_DST_BASE = os.path.join(PROJECT_ROOT, "static", "uploads", "products")
        os.makedirs(IMG_DST_BASE, exist_ok=True)

        # Product type definitions (folder → Excel sheet mapping)
        product_types = [
            {
                "folder": "شمش طلا با بسته بندی",
                "slug": "gold-talamala",
                "category_slug": "gold-talamala",
                "name_prefix": "شمش طلا طلاملا",
                "purity": 995,
            },
            {
                "folder": "شمش طلا بدون بسته بندی",
                "slug": "gold-investment",
                "category_slug": "gold-investment",
                "name_prefix": "شمش طلا سرمایه‌ای",
                "purity": 995,
            },
            {
                "folder": "شمش نقره با بسته بندی",
                "slug": "silver-talamala",
                "category_slug": "silver-talamala",
                "name_prefix": "شمش نقره طلاملا",
                "purity": 999.9,
            },
            {
                "folder": "شمش نقره بدون بسته بندی",
                "slug": "silver-investment",
                "category_slug": "silver-investment",
                "name_prefix": "شمش نقره سرمایه‌ای",
                "purity": 999.9,
            },
        ]

        # Weight definitions: (grams, persian_label, {folder overrides for non-standard names})
        weights_def = [
            (0.1,  "۱۰۰ سوت",  {"شمش نقره با بسته بندی": "0.1 g"}),
            (0.2,  "۲۰۰ سوت",  {}),
            (0.5,  "۵۰۰ سوت",  {}),
            (1.0,  "۱ گرم",     {}),
            (2.5,  "۲.۵ گرم",   {}),
            (5.0,  "۵ گرم",     {}),
            (10.0, "۱۰ گرم",    {}),
            (20.0, "۲۰ گرم",    {}),
            (31.1, "۱ اونس",    {
                "شمش طلا با بسته بندی": "1ounce",
                "شمش طلا بدون بسته بندی": "1ounce",
                "شمش نقره با بسته بندی": "1onuce",
                "شمش نقره بدون بسته بندی": "1onuce",
            }),
            (50.0, "۵۰ گرم",    {"شمش طلا بدون بسته بندی": "50G"}),
            (100.0,"۱۰۰ گرم",   {}),
        ]

        def weight_to_folder(weight_grams, ptype_folder, overrides):
            """Convert weight to image folder name."""
            if ptype_folder in overrides:
                return overrides[ptype_folder]
            if weight_grams == 31.1:
                return "1ounce"
            if weight_grams == int(weight_grams):
                return f"{int(weight_grams)}g"
            return f"{weight_grams}g"

        # Wage data from Excel (× 100 = percentages)
        # {type_slug: {weight: [distributor%, wholesaler%, store%, end_customer%]}}
        wage_data = {
            "gold-talamala": {
                0.1:  [14.0, 17.0, 18.5, 42.0],
                0.2:  [7.0,  8.4,  9.2,  25.0],
                0.5:  [5.0,  6.3,  6.5,  16.0],
                1.0:  [3.8,  5.1,  5.3,  13.0],
                2.5:  [2.8,  4.1,  4.3,  11.0],
                5.0:  [2.4,  3.7,  3.9,  9.0],
                10.0: [1.3,  2.1,  2.3,  8.7],
                20.0: [1.0,  1.8,  2.0,  5.8],
                31.1: [0.6,  1.3,  1.5,  5.6],
                50.0: [0.4,  0.6,  0.9,  4.8],
                100.0:[0.2,  0.4,  0.7,  3.8],
            },
            "gold-investment": {
                0.1:  [3.5,  5.0,  7.0,  11.0],
                0.2:  [3.5,  5.0,  7.0,  11.0],
                0.5:  [2.0,  2.8,  4.0,  7.0],
                1.0:  [1.5,  2.3,  3.0,  6.0],
                2.5:  [1.5,  2.3,  3.0,  6.0],
                5.0:  [1.3,  1.7,  2.5,  4.5],
                10.0: [1.0,  1.5,  2.1,  4.0],
                20.0: [1.0,  1.2,  1.9,  3.5],
                31.1: [0.6,  1.2,  1.7,  3.0],
                50.0: [0.4,  0.8,  1.0,  2.5],
                100.0:[0.2,  0.6,  0.8,  1.5],
            },
            "silver-talamala": {
                0.1:  [56.0,  68.0,  74.0,  168.0],
                0.2:  [28.0,  33.6,  36.8,  100.0],
                0.5:  [20.0,  25.2,  26.0,  64.0],
                1.0:  [15.2,  20.4,  21.2,  52.0],
                2.5:  [11.2,  16.4,  17.2,  44.0],
                5.0:  [9.6,   14.8,  15.6,  36.0],
                10.0: [5.2,   8.4,   9.2,   34.8],
                20.0: [4.0,   7.2,   8.0,   23.2],
                31.1: [2.4,   5.2,   6.0,   22.4],
                50.0: [1.5,   2.4,   3.6,   19.2],
                100.0:[0.8,   1.6,   2.8,   15.2],
            },
            "silver-investment": {
                0.1:  [42.0,  51.0,  55.5,  126.0],
                0.2:  [21.0,  25.2,  27.6,  75.0],
                0.5:  [15.0,  18.9,  19.5,  48.0],
                1.0:  [11.4,  15.3,  15.9,  39.0],
                2.5:  [8.4,   12.3,  12.9,  33.0],
                5.0:  [7.2,   11.1,  11.7,  27.0],
                10.0: [3.9,   6.3,   6.9,   26.1],
                20.0: [3.0,   5.4,   6.0,   17.4],
                31.1: [2.4,   3.9,   4.5,   16.8],
                50.0: [1.6,   1.8,   2.7,   14.4],
                100.0:[0.8,   1.2,   2.1,   11.4],
            },
        }

        product_map = {}
        default_design = db.query(CardDesign).first()
        default_package = db.query(PackageType).first()

        for ptype in product_types:
            cat = cat_map.get(ptype["category_slug"])
            type_wages = wage_data.get(ptype["slug"], {})

            for weight_grams, weight_label, folder_overrides in weights_def:
                name = f"{ptype['name_prefix']} {weight_label}"
                existing = db.query(Product).filter(Product.name == name).first()
                if existing:
                    product_map[name] = existing
                    print(f"  = exists: {name}")
                    continue

                # End-customer wage (index 3) for product.wage
                tier_wages_list = type_wages.get(weight_grams, [0, 0, 0, 0])
                end_customer_wage = tier_wages_list[3]

                p = Product(
                    name=name,
                    weight=weight_grams,
                    purity=ptype["purity"],
                    card_design_id=default_design.id if default_design else None,
                    package_type_id=default_package.id if default_package else None,
                    wage=end_customer_wage,
                    is_wage_percent=True,
                    is_active=True,
                )
                db.add(p)
                db.flush()

                # M2M category link
                if cat:
                    db.add(ProductCategoryLink(product_id=p.id, category_id=cat.id))

                # Copy images from _private to static/uploads/products/
                folder_name = weight_to_folder(weight_grams, ptype["folder"], folder_overrides)
                img_src_dir = os.path.join(IMG_SRC_BASE, ptype["folder"], folder_name)
                if os.path.isdir(img_src_dir):
                    # Prefer website-sized images if available
                    site_dir = os.path.join(img_src_dir, "ابعاد سایت")
                    if os.path.isdir(site_dir):
                        src_files = [
                            os.path.join(site_dir, f)
                            for f in sorted(os.listdir(site_dir))
                            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
                        ]
                    else:
                        src_files = [
                            os.path.join(img_src_dir, f)
                            for f in sorted(os.listdir(img_src_dir))
                            if os.path.isfile(os.path.join(img_src_dir, f))
                            and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
                        ]

                    for idx, src_path in enumerate(src_files):
                        ext = os.path.splitext(src_path)[1].lower()
                        clean_name = f"{ptype['slug']}_{folder_name}_{idx + 1}{ext}"
                        dst_path = os.path.join(IMG_DST_BASE, clean_name)
                        shutil.copy2(src_path, dst_path)
                        rel_path = f"static/uploads/products/{clean_name}"
                        db.add(ProductImage(
                            product_id=p.id,
                            file_path=rel_path,
                            is_default=(idx == 0),
                        ))

                product_map[name] = p
                print(f"  + {name} ({weight_grams}g, purity={ptype['purity']}, wage={end_customer_wage}%)")

        db.flush()

        # ==========================================
        # 6. (Removed — locations merged into dealers)
        # ==========================================

        # ==========================================
        # 7. Bars (inventory) — created AFTER dealers (section 10)
        # ==========================================
        print("\n[6/9] Bars (deferred — created after dealers)")

        # (Bars will be created in section 10.5 after dealers exist)
        _bar_batch1 = db.query(Batch).filter(Batch.batch_number == "B-1403-001").first()

        # ==========================================
        # 8. Sample Coupons
        # ==========================================
        print("\n[8/9] Coupons")

        coupons_data = [
            {
                "code": "WELCOME10", "title": "خوش‌آمدگویی ۱۰٪ تخفیف",
                "description": "تخفیف ویژه اولین خرید",
                "coupon_type": "DISCOUNT", "discount_mode": "PERCENT",
                "discount_value": 10, "max_discount_amount": 50_000_000,
                "first_purchase_only": True, "max_per_customer": 1, "max_total_uses": 100,
            },
            {
                "code": "CASHBACK5", "title": "۵٪ کشبک",
                "description": "۵ درصد مبلغ خرید به کیف پول واریز می‌شود",
                "coupon_type": "CASHBACK", "discount_mode": "PERCENT",
                "discount_value": 5, "max_discount_amount": 20_000_000,
                "max_per_customer": 3,
            },
            {
                "code": "FIXED500", "title": "۵۰۰ هزار تومان تخفیف",
                "description": "تخفیف ثابت برای خرید بالای ۵ میلیون",
                "coupon_type": "DISCOUNT", "discount_mode": "FIXED",
                "discount_value": 5_000_000, "min_order_amount": 50_000_000,
                "max_per_customer": 1, "max_total_uses": 50,
            },
            {
                "code": "VIP2026", "title": "کد ویژه VIP (موبایل خاص)",
                "description": "تخفیف ۱۵٪ برای مشتریان ویژه",
                "coupon_type": "DISCOUNT", "discount_mode": "PERCENT",
                "discount_value": 15, "max_discount_amount": 100_000_000,
                "is_private": True, "max_per_customer": 5,
                "_mobiles": ["09351234567", "09359876543"],
            },
            {
                "code": "GOLD10", "title": "۱۰٪ تخفیف شمش طلا",
                "description": "فقط برای دسته شمش طلا",
                "coupon_type": "DISCOUNT", "discount_mode": "PERCENT",
                "discount_value": 10, "max_discount_amount": 80_000_000,
                "scope": "CATEGORY", "max_per_customer": 2,
                "_category_slugs": ["gold-talamala", "gold-investment"],
            },
        ]

        for cd in coupons_data:
            if db.query(Coupon).filter(Coupon.code == cd["code"]).first():
                print(f"  = exists: {cd['code']}")
                continue

            mobiles = cd.pop("_mobiles", [])
            cat_slugs = cd.pop("_category_slugs", [])
            coupon = Coupon(
                code=cd["code"], title=cd["title"],
                description=cd.get("description", ""),
                coupon_type=cd.get("coupon_type", "DISCOUNT"),
                discount_mode=cd.get("discount_mode", "PERCENT"),
                discount_value=cd["discount_value"],
                max_discount_amount=cd.get("max_discount_amount"),
                scope=cd.get("scope", "GLOBAL"),
                min_order_amount=cd.get("min_order_amount", 0),
                first_purchase_only=cd.get("first_purchase_only", False),
                is_private=cd.get("is_private", False),
                max_per_customer=cd.get("max_per_customer", 1),
                max_total_uses=cd.get("max_total_uses"),
                status="ACTIVE",
            )
            db.add(coupon)
            db.flush()
            for m in mobiles:
                db.add(CouponMobile(coupon_id=coupon.id, mobile=m, note="Seed VIP"))
            for slug in cat_slugs:
                cat = db.query(ProductCategory).filter(ProductCategory.slug == slug).first()
                if cat:
                    db.add(CouponCategory(coupon_id=coupon.id, category_id=cat.id))
            db.flush()
            tag = f" [mobile: {', '.join(mobiles)}]" if mobiles else ""
            if cat_slugs:
                tag += f" [categories: {', '.join(cat_slugs)}]"
            print(f"  + {cd['code']}: {cd['title']}{tag}")

        # ==========================================
        # 8.5 Geographic Data (Provinces / Cities / Districts)
        # ==========================================
        print("\n[8.5] Geographic Data")

        geo_data = {
            "تهران": {
                "cities": ["تهران", "شهریار", "اسلامشهر", "ورامین", "ری", "قدس", "پاکدشت", "ملارد", "رباط‌کریم", "بومهن", "دماوند"],
                "districts": {
                    "تهران": ["همه محله‌ها", "تهرانپارس", "نارمک", "پیروزی", "ونک", "سعادت‌آباد", "شهرک غرب",
                              "پونک", "ستارخان", "آریاشهر", "جنت‌آباد", "اکباتان", "تجریش", "ولیعصر",
                              "میرداماد", "یوسف‌آباد", "امیرآباد", "انقلاب", "بازار", "مولوی", "جمهوری",
                              "فردوسی", "آزادی", "صادقیه", "المهدی", "چیتگر", "اندرزگو", "زعفرانیه"],
                },
            },
            "اصفهان": {
                "cities": ["اصفهان", "کاشان", "نجف‌آباد", "خمینی‌شهر", "شاهین‌شهر", "فلاورجان", "لنجان"],
                "districts": {"اصفهان": ["همه محله‌ها", "چهارباغ", "جلفا", "خوراسگان", "شاهین‌ویلا", "ملک‌شهر"]},
            },
            "فارس": {
                "cities": ["شیراز", "مرودشت", "کازرون", "فسا", "جهرم", "لار", "داراب", "آباده"],
                "districts": {"شیراز": ["همه محله‌ها", "زند", "معالی‌آباد", "قصرالدشت", "ملاصدرا", "صدرا"]},
            },
            "خراسان رضوی": {
                "cities": ["مشهد", "نیشابور", "سبزوار", "تربت‌حیدریه", "قوچان", "کاشمر", "گناباد", "چناران"],
                "districts": {"مشهد": ["همه محله‌ها", "وکیل‌آباد", "احمدآباد", "هاشمیه", "الهیه", "سجاد"]},
            },
            "آذربایجان شرقی": {
                "cities": ["تبریز", "مراغه", "مرند", "میانه", "اهر", "سراب", "بناب", "شبستر"],
                "districts": {"تبریز": ["همه محله‌ها", "ولیعصر", "آزادی", "ائل‌گلی", "باغمیشه", "رشدیه"]},
            },
            "خوزستان": {
                "cities": ["اهواز", "آبادان", "خرمشهر", "دزفول", "شوشتر", "ماهشهر", "بهبهان", "اندیمشک"],
                "districts": {"اهواز": ["همه محله‌ها", "کیانپارس", "گلستان", "زیتون", "پادادشهر"]},
            },
            "گیلان": {
                "cities": ["رشت", "بندر انزلی", "لاهیجان", "لنگرود", "آستارا", "تالش", "فومن", "صومعه‌سرا"],
                "districts": {"رشت": ["همه محله‌ها"]},
            },
            "مازندران": {
                "cities": ["ساری", "بابل", "آمل", "قائم‌شهر", "بهشهر", "تنکابن", "رامسر", "نوشهر", "چالوس", "نور"],
                "districts": {"ساری": ["همه محله‌ها"]},
            },
            "کرمان": {
                "cities": ["کرمان", "رفسنجان", "جیرفت", "سیرجان", "بم", "زرند", "بردسیر"],
                "districts": {"کرمان": ["همه محله‌ها"]},
            },
            "البرز": {
                "cities": ["کرج", "فردیس", "نظرآباد", "هشتگرد", "محمدشهر", "مشکین‌دشت"],
                "districts": {"کرج": ["همه محله‌ها", "گوهردشت", "مهرشهر", "عظیمیه", "گلشهر", "جهانشهر"]},
            },
            "قم": {
                "cities": ["قم"],
                "districts": {"قم": ["همه محله‌ها"]},
            },
            "کرمانشاه": {
                "cities": ["کرمانشاه", "اسلام‌آباد غرب", "سنقر", "کنگاور", "پاوه", "جوانرود", "هرسین"],
                "districts": {"کرمانشاه": ["همه محله‌ها"]},
            },
            "آذربایجان غربی": {
                "cities": ["ارومیه", "خوی", "مهاباد", "بوکان", "میاندوآب", "سلماس", "پیرانشهر", "نقده"],
                "districts": {"ارومیه": ["همه محله‌ها"]},
            },
            "هرمزگان": {
                "cities": ["بندرعباس", "قشم", "کیش", "میناب", "بندر لنگه", "حاجی‌آباد"],
                "districts": {"بندرعباس": ["همه محله‌ها"]},
            },
            "سیستان و بلوچستان": {
                "cities": ["زاهدان", "چابهار", "ایرانشهر", "سراوان", "زابل", "خاش", "نیک‌شهر"],
                "districts": {"زاهدان": ["همه محله‌ها"]},
            },
            "لرستان": {
                "cities": ["خرم‌آباد", "بروجرد", "دورود", "الیگودرز", "کوهدشت", "نورآباد"],
                "districts": {"خرم‌آباد": ["همه محله‌ها"]},
            },
            "همدان": {
                "cities": ["همدان", "ملایر", "نهاوند", "تویسرکان", "بهار", "اسدآباد", "کبودرآهنگ"],
                "districts": {"همدان": ["همه محله‌ها"]},
            },
            "مرکزی": {
                "cities": ["اراک", "ساوه", "خمین", "دلیجان", "محلات", "شازند", "تفرش"],
                "districts": {"اراک": ["همه محله‌ها"]},
            },
            "گلستان": {
                "cities": ["گرگان", "گنبد کاووس", "علی‌آباد کتول", "بندر ترکمن", "آق‌قلا", "مینودشت"],
                "districts": {"گرگان": ["همه محله‌ها"]},
            },
            "اردبیل": {
                "cities": ["اردبیل", "پارس‌آباد", "خلخال", "مشگین‌شهر", "نمین", "نیر"],
                "districts": {"اردبیل": ["همه محله‌ها"]},
            },
            "یزد": {
                "cities": ["یزد", "میبد", "اردکان", "تفت", "بافق", "ابرکوه", "مهریز"],
                "districts": {"یزد": ["همه محله‌ها"]},
            },
            "زنجان": {
                "cities": ["زنجان", "ابهر", "خدابنده", "خرمدره", "ماهنشان", "طارم"],
                "districts": {"زنجان": ["همه محله‌ها"]},
            },
            "سمنان": {
                "cities": ["سمنان", "شاهرود", "دامغان", "گرمسار", "مهدی‌شهر"],
                "districts": {"سمنان": ["همه محله‌ها"]},
            },
            "قزوین": {
                "cities": ["قزوین", "تاکستان", "بویین‌زهرا", "آبیک", "آوج", "الموت"],
                "districts": {"قزوین": ["همه محله‌ها"]},
            },
            "بوشهر": {
                "cities": ["بوشهر", "برازجان", "کنگان", "گناوه", "دیلم", "دیر", "جم"],
                "districts": {"بوشهر": ["همه محله‌ها"]},
            },
            "کهگیلویه و بویراحمد": {
                "cities": ["یاسوج", "دهدشت", "گچساران", "دوگنبدان", "لیکک"],
                "districts": {"یاسوج": ["همه محله‌ها"]},
            },
            "چهارمحال و بختیاری": {
                "cities": ["شهرکرد", "بروجن", "فارسان", "لردگان", "اردل", "کیار"],
                "districts": {"شهرکرد": ["همه محله‌ها"]},
            },
            "کردستان": {
                "cities": ["سنندج", "سقز", "مریوان", "بانه", "قروه", "بیجار", "دیواندره", "کامیاران"],
                "districts": {"سنندج": ["همه محله‌ها"]},
            },
            "ایلام": {
                "cities": ["ایلام", "دهلران", "ایوان", "آبدانان", "مهران", "دره‌شهر"],
                "districts": {"ایلام": ["همه محله‌ها"]},
            },
            "خراسان شمالی": {
                "cities": ["بجنورد", "شیروان", "اسفراین", "جاجرم", "فاروج"],
                "districts": {"بجنورد": ["همه محله‌ها"]},
            },
            "خراسان جنوبی": {
                "cities": ["بیرجند", "قاین", "طبس", "فردوس", "نهبندان", "سربیشه"],
                "districts": {"بیرجند": ["همه محله‌ها"]},
            },
        }

        existing_prov = db.query(GeoProvince).count()
        if existing_prov == 0:
            sort_idx = 0
            for prov_name, prov_info in geo_data.items():
                sort_idx += 1
                prov = GeoProvince(name=prov_name, sort_order=sort_idx)
                db.add(prov)
                db.flush()

                for city_name in prov_info["cities"]:
                    city = GeoCity(province_id=prov.id, name=city_name)
                    db.add(city)
                    db.flush()

                    district_list = prov_info.get("districts", {}).get(city_name, [])
                    for dist_name in district_list:
                        db.add(GeoDistrict(city_id=city.id, name=dist_name))

            db.flush()
            total_cities = db.query(GeoCity).count()
            total_districts = db.query(GeoDistrict).count()
            print(f"  + {len(geo_data)} provinces, {total_cities} cities, {total_districts} districts")
        else:
            print(f"  = geo data exists ({existing_prov} provinces)")

        # ==========================================
        # 9. Wallet: Credit test customer
        # ==========================================
        print("\n[9/9] Test Wallet Credit")

        test_customer = db.query(Customer).filter(Customer.mobile == "09351234567").first()
        if test_customer:
            existing_acct = db.query(Account).filter(
                Account.owner_type == OwnerType.CUSTOMER,
                Account.owner_id == test_customer.id,
                Account.asset_code == "IRR",
            ).first()
            if not existing_acct:
                acct = Account(
                    owner_type=OwnerType.CUSTOMER,
                    owner_id=test_customer.id,
                    customer_id=test_customer.id,
                    asset_code="IRR",
                    balance=100_000_000, locked_balance=0,
                )
                db.add(acct)
                db.flush()
                db.add(LedgerEntry(
                    account_id=acct.id, txn_type="Deposit",
                    delta_balance=100_000_000, delta_locked=0,
                    balance_after=100_000_000, locked_after=0,
                    idempotency_key="seed:initial_credit:1",
                    reference_type="seed", reference_id="initial",
                    description="شارژ اولیه تستی",
                ))
                print(f"  + {test_customer.full_name} -> 10,000,000 toman (IRR)")
            else:
                print(f"  = wallet exists for {test_customer.full_name}")

            # Gold wallet for test customer
            existing_gold = db.query(Account).filter(
                Account.owner_type == OwnerType.CUSTOMER,
                Account.owner_id == test_customer.id,
                Account.asset_code == "XAU_MG",
            ).first()
            if not existing_gold:
                db.add(Account(
                    owner_type=OwnerType.CUSTOMER,
                    owner_id=test_customer.id,
                    customer_id=test_customer.id,
                    asset_code="XAU_MG",
                    balance=0, locked_balance=0,
                ))
                print(f"  + {test_customer.full_name} -> Gold wallet (XAU_MG)")
            else:
                print(f"  = gold wallet exists for {test_customer.full_name}")

        # ==========================================
        # 9.1 Sample Withdrawal Requests
        # ==========================================
        print("\n[9.1] Sample Withdrawal Requests")

        existing_wr = db.query(WithdrawalRequest).count()
        if existing_wr == 0 and test_customer:
            from modules.wallet.models import WithdrawalStatus

            acct = db.query(Account).filter(
                Account.owner_type == OwnerType.CUSTOMER,
                Account.owner_id == test_customer.id,
                Account.asset_code == "IRR",
            ).first()

            wr_data = [
                {
                    "amount_irr": 5_000_000,
                    "shaba_number": "IR820540102680020817909002",
                    "account_holder": "علی رضایی",
                    "status": WithdrawalStatus.PENDING,
                },
                {
                    "amount_irr": 10_000_000,
                    "shaba_number": "IR062960000000100324200001",
                    "account_holder": "علی رضایی",
                    "status": WithdrawalStatus.PENDING,
                },
                {
                    "amount_irr": 3_000_000,
                    "shaba_number": "IR820540102680020817909002",
                    "account_holder": "علی رضایی",
                    "status": WithdrawalStatus.PAID,
                    "admin_note": "واریز شد - شماره پیگیری ۱۲۳۴۵۶",
                },
                {
                    "amount_irr": 2_000_000,
                    "shaba_number": "IR062960000000100324200001",
                    "account_holder": "علی رضایی",
                    "status": WithdrawalStatus.REJECTED,
                    "admin_note": "شماره شبا با نام صاحب حساب مطابقت ندارد",
                },
            ]

            total_pending_hold = 0
            for wd in wr_data:
                wr = WithdrawalRequest(
                    customer_id=test_customer.id,
                    amount_irr=wd["amount_irr"],
                    shaba_number=wd["shaba_number"],
                    account_holder=wd["account_holder"],
                    status=wd["status"],
                    admin_note=wd.get("admin_note"),
                )
                db.add(wr)
                status_label = wd["status"].value if hasattr(wd["status"], "value") else wd["status"]
                print(f"  + Withdrawal {wd['amount_irr'] // 10:,} toman [{status_label}]")

                if wd["status"] == WithdrawalStatus.PENDING:
                    total_pending_hold += wd["amount_irr"]

            # Hold funds for pending withdrawals
            if acct and total_pending_hold > 0:
                acct.locked_balance += total_pending_hold
                db.flush()
                db.add(LedgerEntry(
                    account_id=acct.id, txn_type="Hold",
                    delta_balance=0, delta_locked=total_pending_hold,
                    balance_after=acct.balance, locked_after=acct.locked_balance,
                    idempotency_key="seed:withdrawal_hold:1",
                    reference_type="seed", reference_id="withdrawal_hold",
                    description=f"بلوکه تستی برای درخواست‌های برداشت",
                ))
                print(f"  + Held {total_pending_hold // 10:,} toman for pending withdrawals")

            db.flush()
        else:
            print(f"  = {existing_wr} withdrawal requests exist, skipping")

        # ==========================================
        # 9.5. Dealer Tiers
        # ==========================================
        print("\n[9.5] Dealer Tiers")

        tiers_data = [
            {"name": "پخش", "slug": "distributor", "sort_order": 1, "is_end_customer": False},
            {"name": "بنکدار", "slug": "wholesaler", "sort_order": 2, "is_end_customer": False},
            {"name": "فروشگاه", "slug": "store", "sort_order": 3, "is_end_customer": False},
            {"name": "مشتری نهایی", "slug": "end_customer", "sort_order": 4, "is_end_customer": True},
        ]

        tier_map = {}
        for td in tiers_data:
            existing = db.query(DealerTier).filter(DealerTier.slug == td["slug"]).first()
            if not existing:
                tier = DealerTier(**td, is_active=True)
                db.add(tier)
                db.flush()
                tier_map[td["slug"]] = tier
                ec = " [END-CUSTOMER]" if td["is_end_customer"] else ""
                print(f"  + {td['name']} ({td['slug']}){ec}")
            else:
                tier_map[td["slug"]] = existing
                print(f"  = exists: {td['name']}")

        db.flush()

        # ==========================================
        # 9.6. Product Tier Wages
        # ==========================================
        print("\n[9.6] Product Tier Wages")

        # Wage data from Excel (same as section 5, reused for tier wages)
        # {type_slug: {weight: [distributor%, wholesaler%, store%, end_customer%]}}
        tier_slugs_order = ["distributor", "wholesaler", "store", "end_customer"]

        existing_tw = db.query(ProductTierWage).count()
        if existing_tw == 0:
            tw_count = 0
            # Build category_id → type_slug lookup
            cat_id_to_slug = {}
            for slug, cat_obj in cat_map.items():
                cat_id_to_slug[cat_obj.id] = slug

            all_products = db.query(Product).filter(Product.is_active == True).all()
            for p in all_products:
                # Determine product type from category
                type_slug = None
                for cid in p.category_ids:
                    if cid in cat_id_to_slug:
                        type_slug = cat_id_to_slug[cid]
                        break
                if not type_slug or type_slug not in wage_data:
                    continue

                weight_key = float(p.weight)
                wages = wage_data[type_slug].get(weight_key)
                if not wages:
                    continue

                for idx, tier_slug in enumerate(tier_slugs_order):
                    tier = tier_map.get(tier_slug)
                    if tier:
                        db.add(ProductTierWage(
                            product_id=p.id,
                            tier_id=tier.id,
                            wage_percent=wages[idx],
                        ))
                        tw_count += 1
            db.flush()
            print(f"  + {tw_count} tier wages created")
        else:
            print(f"  = {existing_tw} tier wages exist, skipping")

        # ==========================================
        # 10. Dealers
        # ==========================================
        print("\n[10] Dealers")

        tier_distributor = tier_map.get("distributor")
        tier_wholesaler = tier_map.get("wholesaler")
        tier_store = tier_map.get("store")

        # Lookup geo IDs for dealer addresses
        def geo_ids(province_name, city_name):
            prov = db.query(GeoProvince).filter(GeoProvince.name == province_name).first()
            city = db.query(GeoCity).filter(GeoCity.province_id == prov.id, GeoCity.name == city_name).first() if prov else None
            return (prov.id if prov else None, city.id if city else None)

        geo_tehran = geo_ids("تهران", "تهران")
        geo_esfahan = geo_ids("اصفهان", "اصفهان")
        geo_shiraz = geo_ids("فارس", "شیراز")
        geo_mashhad = geo_ids("خراسان رضوی", "مشهد")
        geo_tabriz = geo_ids("آذربایجان شرقی", "تبریز")

        dealers_data = [
            # --- انبار مرکزی (postal hub + warehouse) ---
            {
                "mobile": "00000000000",
                "full_name": "انبار مرکزی تهران",
                "national_id": "0000000000",
                "api_key": None,
                "tier_id": None,
                "province_id": geo_tehran[0], "city_id": geo_tehran[1],
                "address": "تهران، خیابان ولیعصر، پلاک ۱۲۳",
                "landline_phone": "02188001234",
                "is_warehouse": True,
                "is_postal_hub": True,
            },
            # --- شهرستان ---
            {
                "mobile": "09161234567",
                "full_name": "احمد نوری",
                "national_id": "1111111111",
                "api_key": "test_esfahan_key_0000000000000000",
                "tier_id": tier_distributor.id if tier_distributor else None,
                "province_id": geo_esfahan[0], "city_id": geo_esfahan[1],
                "address": "اصفهان، خیابان چهارباغ، پلاک ۴۵",
                "landline_phone": "03132001234",
            },
            {
                "mobile": "09171234567",
                "full_name": "سارا کریمی",
                "national_id": "2222222222",
                "api_key": "test_shiraz__key_1111111111111111",
                "tier_id": tier_wholesaler.id if tier_wholesaler else None,
                "province_id": geo_shiraz[0], "city_id": geo_shiraz[1],
                "address": "شیراز، خیابان زند، پلاک ۷۸",
                "landline_phone": "07136001234",
            },
            {
                "mobile": "09181234567",
                "full_name": "حسین موسوی",
                "national_id": "3333333333",
                "api_key": "test_mashhad_key_2222222222222222",
                "tier_id": tier_store.id if tier_store else None,
                "province_id": geo_mashhad[0], "city_id": geo_mashhad[1],
                "address": "مشهد، بلوار وکیل‌آباد، پلاک ۲۲",
                "landline_phone": "05138001234",
            },
            {
                "mobile": "09141234567",
                "full_name": "یوسف قربانی",
                "national_id": "4444444444",
                "api_key": "test_tabriz__key_3333333333333333",
                "tier_id": tier_distributor.id if tier_distributor else None,
                "province_id": geo_tabriz[0], "city_id": geo_tabriz[1],
                "address": "تبریز، خیابان آزادی، پلاک ۳۳",
                "landline_phone": "04135001234",
            },
            # --- تهران ---
            {
                "mobile": "09121234567",
                "full_name": "محمد رضایی",
                "national_id": "5555555555",
                "api_key": "test_mirdmad_key_4444444444444444",
                "tier_id": tier_distributor.id if tier_distributor else None,
                "province_id": geo_tehran[0], "city_id": geo_tehran[1],
                "address": "بلوار میرداماد، برج آرین، طبقه دوم اداری، واحد ۵",
                "landline_phone": "02145241",
            },
            {
                "mobile": "09122345678",
                "full_name": "علی حسینی",
                "national_id": "6666666666",
                "api_key": "test_nasrkhr_key_5555555555555555",
                "tier_id": tier_wholesaler.id if tier_wholesaler else None,
                "province_id": geo_tehran[0], "city_id": geo_tehran[1],
                "address": "بازار تهران، خیابان ناصر خسرو، پاساژ شمس العماره، طبقه منفی ۱، واحد ۳۰۵",
                "landline_phone": "02186091012",
            },
            {
                "mobile": "09123456780",
                "full_name": "فاطمه احمدی",
                "national_id": "7777777777",
                "api_key": "test_ordibht_key_6666666666666666",
                "tier_id": tier_wholesaler.id if tier_wholesaler else None,
                "province_id": geo_tehran[0], "city_id": geo_tehran[1],
                "address": "بازار بزرگ تهران، پاساژ اردیبهشت، طبقه هم‌کف، پلاک ۶۸",
                "landline_phone": "02186091013",
            },
            {
                "mobile": "09124567890",
                "full_name": "رضا محمدی",
                "national_id": "8888888888",
                "api_key": "test_shahrak_key_7777777777777777",
                "tier_id": tier_store.id if tier_store else None,
                "province_id": geo_tehran[0], "city_id": geo_tehran[1],
                "address": "بلوار فرحزادی، مجتمع تجاری لیدوما، تجاری دوم (G2)، واحد ۱۵",
                "landline_phone": "02186091014",
            },
            {
                "mobile": "09125678901",
                "full_name": "مریم کاظمی",
                "national_id": "9999999999",
                "api_key": "test_karimkh_key_8888888888888888",
                "tier_id": tier_store.id if tier_store else None,
                "province_id": geo_tehran[0], "city_id": geo_tehran[1],
                "address": "میدان ولی‌عصر(عج)، خیابان کریمخان، مجتمع تجاری الماس کریمخان، طبقه دوم، واحد ۲۰۸",
                "landline_phone": "02186091015",
            },
        ]

        for dd in dealers_data:
            existing = db.query(Dealer).filter(Dealer.mobile == dd["mobile"]).first()
            if not existing:
                dealer = Dealer(
                    mobile=dd["mobile"],
                    full_name=dd["full_name"],
                    national_id=dd["national_id"],
                    api_key=dd.get("api_key"),
                    tier_id=dd.get("tier_id"),
                    province_id=dd.get("province_id"),
                    city_id=dd.get("city_id"),
                    address=dd.get("address"),
                    landline_phone=dd.get("landline_phone"),
                    is_warehouse=dd.get("is_warehouse", False),
                    is_postal_hub=dd.get("is_postal_hub", False),
                )
                db.add(dealer)
                db.flush()
                tags = []
                if dd.get("is_warehouse"): tags.append("warehouse")
                if dd.get("is_postal_hub"): tags.append("postal_hub")
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                print(f"  + {dd['full_name']}: {dd['mobile']}{tag_str}")
            else:
                if not existing.tier_id and dd.get("tier_id"):
                    existing.tier_id = dd["tier_id"]
                    print(f"  ~ updated tier: {dd['mobile']}")
                elif not existing.api_key and dd.get("api_key"):
                    existing.api_key = dd["api_key"]
                    print(f"  ~ updated api_key: {dd['mobile']}")
                else:
                    print(f"  = exists: {dd['mobile']}")

        db.flush()

        # ==========================================
        # 10.5. Bars (inventory) — now that dealers exist
        # ==========================================
        print("\n[10.5] Bars (Inventory)")

        existing_bar_count = db.query(Bar).count()
        if existing_bar_count > 0:
            print(f"  = {existing_bar_count} bars already exist, skipping")
        else:
            batch1 = _bar_batch1

            # Use all active dealers as locations for bars
            all_dealer_locs = db.query(Dealer).filter(Dealer.is_active == True).all()

            total_bars = 0
            used_serials = set()

            all_products = db.query(Product).filter(Product.is_active == True).all()
            for product in all_products:
                w = float(product.weight)
                if w <= 1:
                    count_per_dealer = 5
                elif w <= 5:
                    count_per_dealer = 3
                elif w <= 50:
                    count_per_dealer = 2
                else:
                    count_per_dealer = 1

                for dlr in all_dealer_locs:
                    for _ in range(count_per_dealer):
                        serial = generate_serial()
                        while serial in used_serials:
                            serial = generate_serial()
                        used_serials.add(serial)

                        db.add(Bar(
                            serial_code=serial,
                            status=BarStatus.ASSIGNED,
                            product_id=product.id,
                            batch_id=batch1.id if batch1 else None,
                            dealer_id=dlr.id,
                        ))
                        total_bars += 1

            db.flush()
            print(f"  + {total_bars} bars for {len(all_products)} products across {len(all_dealer_locs)} dealers")

            # --- Test bars for claim & transfer testing ---
            first_product = db.query(Product).first()
            first_dealer = db.query(Dealer).filter(Dealer.is_active == True).first()
            test_customer_1 = db.query(Customer).filter(Customer.mobile == "09351234567").first()

            if first_product and first_dealer:
                claim_bar_1 = Bar(
                    serial_code="TSCLM001", status=BarStatus.SOLD,
                    product_id=first_product.id, batch_id=batch1.id if batch1 else None,
                    dealer_id=first_dealer.id, customer_id=None, claim_code="ABC123",
                )
                db.add(claim_bar_1)
                claim_bar_2 = Bar(
                    serial_code="TSCLM002", status=BarStatus.SOLD,
                    product_id=first_product.id, batch_id=batch1.id if batch1 else None,
                    dealer_id=first_dealer.id, customer_id=None, claim_code="XYZ789",
                )
                db.add(claim_bar_2)
                if test_customer_1:
                    transfer_bar = Bar(
                        serial_code="TSTRF001", status=BarStatus.SOLD,
                        product_id=first_product.id, batch_id=batch1.id if batch1 else None,
                        dealer_id=first_dealer.id, customer_id=test_customer_1.id, claim_code=None,
                    )
                    db.add(transfer_bar)
                db.flush()
                print("  + 3 test bars (TSCLM001, TSCLM002, TSTRF001)")

        # Create dealer wallets (IRR + XAU_MG)
        print("\n  Dealer Wallets:")
        all_dealers = db.query(Dealer).all()
        for d in all_dealers:
            for asset in ["IRR", "XAU_MG"]:
                existing = db.query(Account).filter(
                    Account.owner_type == OwnerType.DEALER,
                    Account.owner_id == d.id,
                    Account.asset_code == asset,
                ).first()
                if not existing:
                    db.add(Account(
                        owner_type=OwnerType.DEALER,
                        owner_id=d.id,
                        asset_code=asset,
                        balance=0, locked_balance=0,
                    ))
                    print(f"    + {d.full_name} ({asset})")
        db.flush()

        # ==========================================
        # 11. Sample Support Tickets
        # ==========================================
        print("\n[11] Sample Tickets")

        existing_tickets = db.query(Ticket).count()
        if existing_tickets == 0:
            test_customer_1 = db.query(Customer).filter(Customer.mobile == "09351234567").first()
            test_dealer_1 = db.query(Dealer).filter(Dealer.mobile == "09161234567").first()
            admin_user = db.query(SystemUser).filter(SystemUser.mobile == "09123456789").first()

            if test_customer_1:
                t1 = Ticket(
                    subject="مشکل در پرداخت آنلاین",
                    body="سلام، من سعی کردم از درگاه بانکی پرداخت کنم ولی بعد از رفتن به صفحه بانک، خطای اتصال دریافت می‌کنم. لطفا بررسی کنید.",
                    sender_type=SenderType.CUSTOMER,
                    customer_id=test_customer_1.id,
                    priority=TicketPriority.HIGH,
                    category=TicketCategory.FINANCIAL,
                    status=TicketStatus.ANSWERED,
                    assigned_to=admin_user.id if admin_user else None,
                )
                db.add(t1)
                db.flush()
                db.add(TicketMessage(
                    ticket_id=t1.id,
                    sender_type=SenderType.CUSTOMER,
                    sender_name=test_customer_1.full_name,
                    body=t1.body,
                    is_initial=True,
                ))
                db.add(TicketMessage(
                    ticket_id=t1.id,
                    sender_type=SenderType.STAFF,
                    sender_name="مدیر سیستم",
                    body="سلام، مشکل درگاه بانکی بررسی و رفع شد. لطفا مجددا تلاش کنید.",
                ))
                print(f"  + Ticket #{t1.id}: {t1.subject} [Financial]")

                t2 = Ticket(
                    subject="سوال درباره گارانتی شمش",
                    body="آیا شمش‌های خریداری شده گارانتی اصالت دارند؟ چطور می‌توانم اصالت شمش را بررسی کنم؟",
                    sender_type=SenderType.CUSTOMER,
                    customer_id=test_customer_1.id,
                    priority=TicketPriority.LOW,
                    category=TicketCategory.SALES,
                    status=TicketStatus.OPEN,
                )
                db.add(t2)
                db.flush()
                db.add(TicketMessage(
                    ticket_id=t2.id,
                    sender_type=SenderType.CUSTOMER,
                    sender_name=test_customer_1.full_name,
                    body=t2.body,
                    is_initial=True,
                ))
                print(f"  + Ticket #{t2.id}: {t2.subject} [Sales]")

            if test_dealer_1:
                t3 = Ticket(
                    subject="درخواست افزایش موجودی شعبه",
                    body="موجودی شمش‌های ۱ گرمی در شعبه اصفهان تمام شده. لطفا موجودی جدید ارسال کنید.",
                    sender_type=SenderType.DEALER,
                    dealer_id=test_dealer_1.id,
                    priority=TicketPriority.MEDIUM,
                    category=TicketCategory.SALES,
                    status=TicketStatus.IN_PROGRESS,
                    assigned_to=admin_user.id if admin_user else None,
                )
                db.add(t3)
                db.flush()
                db.add(TicketMessage(
                    ticket_id=t3.id,
                    sender_type=SenderType.DEALER,
                    sender_name=test_dealer_1.full_name,
                    body=t3.body,
                    is_initial=True,
                ))
                db.add(TicketMessage(
                    ticket_id=t3.id,
                    sender_type=SenderType.STAFF,
                    sender_name="مدیر سیستم",
                    body="درخواست شما ثبت شد. ارسال از انبار مرکزی در ۲ روز کاری انجام خواهد شد.",
                ))
                db.add(TicketMessage(
                    ticket_id=t3.id,
                    sender_type=SenderType.DEALER,
                    sender_name=test_dealer_1.full_name,
                    body="متشکرم. لطفا بعد از ارسال کد رهگیری پست را هم اطلاع دهید.",
                ))
                print(f"  + Ticket #{t3.id}: {t3.subject} [Sales]")

            db.flush()
        else:
            print(f"  = {existing_tickets} tickets exist, skipping")

        # ==========================================
        # Commit
        # ==========================================
        db.commit()

        print("\n" + "=" * 50)
        print("  Seed completed successfully!")
        print("=" * 50)

        print("\n--- Summary ---")
        print(f"  Admin users:    {db.query(SystemUser).count()}")
        print(f"  Customers:      {db.query(Customer).count()}")
        print(f"  Settings:       {db.query(SystemSetting).count()}")
        print(f"  Products:       {db.query(Product).count()}")
        print(f"  Categories:     {db.query(ProductCategory).count()}")
        print(f"  Provinces:      {db.query(GeoProvince).count()}")
        print(f"  Cities:         {db.query(GeoCity).count()}")
        print(f"  Card Designs:   {db.query(CardDesign).count()}")
        print(f"  Package Types:  {db.query(PackageType).count()}")
        print(f"  Batches:        {db.query(Batch).count()}")
        print(f"  Bars:           {db.query(Bar).count()}")
        print(f"  Coupons:        {db.query(Coupon).count()}")
        print(f"  Wallet Accts:   {db.query(Account).count()}")
        print(f"  Dealer Tiers:   {db.query(DealerTier).count()}")
        print(f"  Tier Wages:     {db.query(ProductTierWage).count()}")
        print(f"  Dealers:        {db.query(Dealer).count()}")
        print(f"  Tickets:        {db.query(Ticket).count()}")
        print(f"  Withdrawals:    {db.query(WithdrawalRequest).count()}")

        print("\n--- Credentials ---")
        print(f"  Admin:    09123456789")
        print(f"  Operator: 09121111111")
        print(f"  Customer: 09351234567 (wallet: 10M toman)")
        print(f"  Customer: 09359876543")
        print(f"  Customer: 09131112233")
        print(f"  Dealer:   09161234567 (esfahan, tier: distributor)")
        print(f"  Dealer:   09171234567 (shiraz, tier: wholesaler)")
        print(f"  Dealer:   09181234567 (mashhad, tier: store)")

        print(f"\n--- Dealer API Keys (for POS) ---")
        for dd in dealers_data:
            print(f"  {dd['mobile']}: {dd['api_key']}")

        print(f"\n--- Settings ---")
        print(f"  Gold price: 5,200,000 toman/gram")
        print(f"  Tax: 10%")
        print(f"  Shipping: 50,000 toman")

        print(f"\n--- Coupons ---")
        print(f"  WELCOME10 : 10% off (first purchase)")
        print(f"  CASHBACK5 : 5% cashback")
        print(f"  FIXED500  : 500K toman off (min 5M order)")
        print(f"  VIP2026   : 15% off (mobile: 09351234567, 09359876543)")
        print(f"  GOLD10    : 10% off (category: gold-talamala + gold-investment)")

    except Exception as e:
        db.rollback()
        print(f"\nSeed failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def reset_and_seed():
    """Drop all tables and recreate + seed."""
    print("WARNING: Dropping ALL tables...")
    # Drop orphan tables (created by migrations but no longer have models)
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS location_transfers CASCADE"))
        conn.commit()
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped")
    Base.metadata.create_all(bind=engine)
    print("All tables recreated")
    seed()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        confirm = input("This will DELETE ALL DATA. Type 'yes' to confirm: ")
        if confirm.strip().lower() == "yes":
            reset_and_seed()
        else:
            print("Aborted.")
    else:
        seed()
