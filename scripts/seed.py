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
import random
import string

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal, Base, engine
from modules.admin.models import SystemUser, SystemSetting
from modules.customer.models import Customer
from modules.customer.address_models import GeoProvince, GeoCity, GeoDistrict, CustomerAddress
from modules.catalog.models import (
    ProductCategory, Product, ProductImage, CardDesign, CardDesignImage,
    PackageType, PackageTypeImage, Batch, BatchImage, ProductTierWage,
)
from modules.inventory.models import (
    Bar, BarImage, OwnershipHistory, BarStatus,
    Location, LocationType, LocationTransfer, BarTransfer,
)
from modules.cart.models import Cart, CartItem
from modules.order.models import Order, OrderItem
from modules.wallet.models import Account, LedgerEntry, WalletTopup, WithdrawalRequest, OwnerType
from modules.coupon.models import Coupon, CouponMobile, CouponUsage, CouponCategory
from modules.dealer.models import Dealer, DealerTier, DealerSale, BuybackRequest
from modules.ticket.models import Ticket, TicketMessage, TicketAttachment, TicketStatus, TicketPriority, TicketCategory, SenderType


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
        ]
        for data in admins_data:
            existing = db.query(SystemUser).filter(SystemUser.mobile == data["mobile"]).first()
            if not existing:
                db.add(SystemUser(**data))
                print(f"  + {data['role']}: {data['mobile']} ({data['full_name']})")
            else:
                print(f"  = exists: {data['mobile']}")

        # ==========================================
        # 2. Test Customers
        # ==========================================
        print("\n[2/9] Test Customers")

        customers_data = [
            {"mobile": "09351234567", "national_id": "0012345678", "first_name": "علی", "last_name": "رضایی"},
            {"mobile": "09359876543", "national_id": "0087654321", "first_name": "مریم", "last_name": "احمدی"},
            {"mobile": "09131112233", "national_id": "1234567890", "first_name": "رضا", "last_name": "محمدی"},
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
            "site_name":            ("طلامالا", "نام سایت"),
            "site_logo":            ("", "لوگوی سایت"),
            "support_phone":        ("02112345678", "شماره پشتیبانی"),
            "support_telegram":     ("@talamala", "تلگرام پشتیبانی"),
            "gold_price":           ("52000000", "قیمت طلای ۱۸ عیار هر گرم (ریال)"),
            "gold_price_source":    ("tgju", "منبع قیمت طلا"),
            "tax_percent":          ("10", "درصد مالیات بر ارزش افزوده"),
            "profit_percent":       ("7", "درصد سود پیش‌فرض"),
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

        for name in ["جعبه استاندارد", "جعبه لوکس", "جعبه هدیه ویژه", "پاکت ساده"]:
            if not db.query(PackageType).filter(PackageType.name == name).first():
                db.add(PackageType(name=name))
                print(f"  + Package: {name}")

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
            ("شمش گرمی", "shamsh-gerami", 1),
            ("شمش سرمایه‌ای", "shamsh-sarmayei", 2),
            ("زیور آلات", "zivar", 3),
            ("سکه", "sekke", 4),
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
        # 5. Products (TalaMala v2 weights)
        # ==========================================
        print("\n[5/9] Products (TalaMala v2)")

        #                    name                 weight  purity  wage%  profit%  comm%
        products_data = [
            ("شمش طلای ۱۰۰ میلی‌گرم",            0.100, 750, 7,  7.0, 0.0),
            ("شمش طلای ۲۰۰ میلی‌گرم",            0.200, 750, 7,  7.0, 0.0),
            ("شمش طلای ۲۵۰ میلی‌گرم",            0.250, 750, 7,  7.0, 0.0),
            ("شمش طلای ۵۰۰ میلی‌گرم",            0.500, 750, 7,  7.0, 0.0),
            ("شمش طلای ۱ گرم",                    1.000, 750, 7,  7.0, 0.0),
            ("شمش طلای ۱.۵ گرم",                  1.500, 750, 6,  7.0, 0.0),
            ("شمش طلای ۲ گرم",                    2.000, 750, 6,  7.0, 0.0),
            ("شمش طلای ۲.۵ گرم",                  2.500, 750, 6,  7.0, 0.0),
            ("شمش طلای ۵ گرم",                    5.000, 750, 5,  7.0, 0.0),
            ("شمش طلای ۱۰ گرم",                  10.000, 750, 5,  7.0, 0.0),
            ("شمش طلای ۵۰ گرم",                  50.000, 750, 4,  7.0, 0.0),
            ("شمش طلای ۱۰۰ گرم",                100.000, 750, 3,  7.0, 0.0),
        ]

        product_map = {}
        cat_gerami = cat_map.get("shamsh-gerami")
        cat_sarmayei = cat_map.get("shamsh-sarmayei")

        # Get first design and package for product assignment
        default_design = db.query(CardDesign).first()
        default_package = db.query(PackageType).first()

        for name, weight, purity, wage, profit, comm in products_data:
            existing = db.query(Product).filter(Product.name == name).first()
            if not existing:
                # Assign category: ≤ 2.5g = گرمی, > 2.5g = سرمایه‌ای
                cat = cat_gerami if weight <= 2.5 else cat_sarmayei
                p = Product(
                    name=name, weight=weight, purity=purity,
                    category_id=cat.id if cat else None,
                    card_design_id=default_design.id if default_design else None,
                    package_type_id=default_package.id if default_package else None,
                    wage=wage, is_wage_percent=True,
                    profit_percent=profit, commission_percent=comm,
                    stone_price=0, accessory_cost=0, accessory_profit_percent=0,
                    is_active=True,
                )
                db.add(p)
                db.flush()
                product_map[name] = p
                print(f"  + {name} ({weight}g)")
            else:
                product_map[name] = existing
                print(f"  = exists: {name}")

        db.flush()

        # ==========================================
        # 6. Locations
        # ==========================================
        print("\n[6/9] Locations")

        locations_data = [
            ("انبار مرکزی تهران", LocationType.WAREHOUSE, "تهران", "تهران",
             "تهران، خیابان ولیعصر، پلاک ۱۲۳", "02188001234", True),
            ("نمایندگی اصفهان", LocationType.BRANCH, "اصفهان", "اصفهان",
             "اصفهان، خیابان چهارباغ، پلاک ۴۵", "03132001234", False),
            ("نمایندگی شیراز", LocationType.BRANCH, "فارس", "شیراز",
             "شیراز، خیابان زند، پلاک ۷۸", "07136001234", False),
            ("نمایندگی مشهد", LocationType.BRANCH, "خراسان رضوی", "مشهد",
             "مشهد، بلوار وکیل‌آباد، پلاک ۲۲", "05138001234", False),
            ("نمایندگی تبریز", LocationType.BRANCH, "آذربایجان شرقی", "تبریز",
             "تبریز، خیابان آزادی، پلاک ۳۳", "04135001234", False),
        ]

        location_map = {}
        for name, loc_type, province, city, address, phone, is_postal in locations_data:
            existing = db.query(Location).filter(Location.name == name).first()
            if not existing:
                loc = Location(
                    name=name, location_type=loc_type,
                    province=province, city=city,
                    address=address, phone=phone,
                    is_postal_hub=is_postal,
                )
                db.add(loc)
                db.flush()
                location_map[name] = loc
                tag = " [postal hub]" if is_postal else ""
                print(f"  + {name} ({city}){tag}")
            else:
                location_map[name] = existing
                print(f"  = exists: {name}")

        db.flush()

        # ==========================================
        # 7. Bars (inventory)
        # ==========================================
        print("\n[7/9] Bars (Inventory)")

        existing_bar_count = db.query(Bar).count()
        if existing_bar_count > 0:
            print(f"  = {existing_bar_count} bars already exist, skipping")
        else:
            batch1 = db.query(Batch).filter(Batch.batch_number == "B-1403-001").first()

            stock_per_location = {
                "شمش طلای ۱۰۰ میلی‌گرم": 10,
                "شمش طلای ۲۰۰ میلی‌گرم": 8,
                "شمش طلای ۲۵۰ میلی‌گرم": 8,
                "شمش طلای ۵۰۰ میلی‌گرم": 6,
                "شمش طلای ۱ گرم": 10,
                "شمش طلای ۱.۵ گرم": 6,
                "شمش طلای ۲ گرم": 6,
                "شمش طلای ۲.۵ گرم": 5,
                "شمش طلای ۵ گرم": 5,
                "شمش طلای ۱۰ گرم": 4,
                "شمش طلای ۵۰ گرم": 2,
                "شمش طلای ۱۰۰ گرم": 2,
            }

            locations = list(location_map.values())
            if not locations:
                locations = db.query(Location).filter(Location.is_active == True).all()

            total_bars = 0
            used_serials = set()

            for prod_name, count_per_loc in stock_per_location.items():
                product = product_map.get(prod_name)
                if not product:
                    product = db.query(Product).filter(Product.name == prod_name).first()
                if not product:
                    continue

                for loc in locations:
                    for _ in range(count_per_loc):
                        serial = generate_serial()
                        while serial in used_serials:
                            serial = generate_serial()
                        used_serials.add(serial)

                        db.add(Bar(
                            serial_code=serial,
                            status=BarStatus.ASSIGNED,
                            product_id=product.id,
                            batch_id=batch1.id if batch1 else None,
                            location_id=loc.id,
                        ))
                        total_bars += 1

            db.flush()
            print(f"  + {total_bars} bars across {len(locations)} locations")

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
                "_category_slugs": ["shamsh-gerami"],
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
        # 9.5. Dealer Tiers
        # ==========================================
        print("\n[9.5] Dealer Tiers")

        tiers_data = [
            {"name": "عامل", "slug": "amel", "sort_order": 1, "is_end_customer": False},
            {"name": "بنکدار", "slug": "bankdar", "sort_order": 2, "is_end_customer": False},
            {"name": "نماینده", "slug": "namayandeh", "sort_order": 3, "is_end_customer": False},
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

        # Wage percentages: {product_weight: {tier_slug: wage%}}
        # Lower weight = higher wage, lower tier = lower wage
        tier_wage_config = {
            0.1:   {"amel": 3.0, "bankdar": 5.0, "namayandeh": 7.0, "end_customer": 10.0},
            0.2:   {"amel": 3.0, "bankdar": 5.0, "namayandeh": 7.0, "end_customer": 10.0},
            0.25:  {"amel": 3.0, "bankdar": 5.0, "namayandeh": 7.0, "end_customer": 10.0},
            0.5:   {"amel": 3.0, "bankdar": 5.0, "namayandeh": 7.0, "end_customer": 10.0},
            1.0:   {"amel": 3.0, "bankdar": 5.0, "namayandeh": 7.0, "end_customer": 10.0},
            1.5:   {"amel": 2.5, "bankdar": 4.0, "namayandeh": 6.0, "end_customer": 8.0},
            2.0:   {"amel": 2.5, "bankdar": 4.0, "namayandeh": 6.0, "end_customer": 8.0},
            2.5:   {"amel": 2.5, "bankdar": 4.0, "namayandeh": 6.0, "end_customer": 8.0},
            5.0:   {"amel": 2.0, "bankdar": 3.0, "namayandeh": 5.0, "end_customer": 7.0},
            10.0:  {"amel": 2.0, "bankdar": 3.0, "namayandeh": 5.0, "end_customer": 7.0},
            50.0:  {"amel": 1.5, "bankdar": 2.5, "namayandeh": 4.0, "end_customer": 5.0},
            100.0: {"amel": 1.0, "bankdar": 2.0, "namayandeh": 3.0, "end_customer": 4.0},
        }

        existing_tw = db.query(ProductTierWage).count()
        if existing_tw == 0:
            tw_count = 0
            all_products = db.query(Product).filter(Product.is_active == True).all()
            for p in all_products:
                weight_key = float(p.weight)
                wage_map = tier_wage_config.get(weight_key)
                if not wage_map:
                    continue
                for slug, wage_pct in wage_map.items():
                    tier = tier_map.get(slug)
                    if tier:
                        db.add(ProductTierWage(
                            product_id=p.id,
                            tier_id=tier.id,
                            wage_percent=wage_pct,
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

        # Get branch locations for assigning dealers
        branch_esfahan = db.query(Location).filter(Location.name == "نمایندگی اصفهان").first()
        branch_shiraz = db.query(Location).filter(Location.name == "نمایندگی شیراز").first()
        branch_mashhad = db.query(Location).filter(Location.name == "نمایندگی مشهد").first()

        tier_amel = tier_map.get("amel")
        tier_bankdar = tier_map.get("bankdar")
        tier_namayandeh = tier_map.get("namayandeh")

        dealers_data = [
            {
                "mobile": "09161234567",
                "full_name": "احمد نوری",
                "national_id": "1111111111",
                "location_id": branch_esfahan.id if branch_esfahan else None,
                "commission_percent": 2.0,
                "api_key": "test_esfahan_key_0000000000000000",
                "tier_id": tier_amel.id if tier_amel else None,
            },
            {
                "mobile": "09171234567",
                "full_name": "سارا کریمی",
                "national_id": "2222222222",
                "location_id": branch_shiraz.id if branch_shiraz else None,
                "commission_percent": 2.5,
                "api_key": "test_shiraz__key_1111111111111111",
                "tier_id": tier_bankdar.id if tier_bankdar else None,
            },
            {
                "mobile": "09181234567",
                "full_name": "حسین موسوی",
                "national_id": "3333333333",
                "location_id": branch_mashhad.id if branch_mashhad else None,
                "commission_percent": 3.0,
                "api_key": "test_mashhad_key_2222222222222222",
                "tier_id": tier_namayandeh.id if tier_namayandeh else None,
            },
        ]

        for dd in dealers_data:
            existing = db.query(Dealer).filter(Dealer.mobile == dd["mobile"]).first()
            if not existing:
                from decimal import Decimal
                dealer = Dealer(
                    mobile=dd["mobile"],
                    full_name=dd["full_name"],
                    national_id=dd["national_id"],
                    location_id=dd["location_id"],
                    commission_percent=Decimal(str(dd["commission_percent"])),
                    api_key=dd["api_key"],
                    tier_id=dd["tier_id"],
                )
                db.add(dealer)
                db.flush()
                loc_name = "—"
                if dd["location_id"]:
                    loc = db.query(Location).filter(Location.id == dd["location_id"]).first()
                    loc_name = loc.name if loc else "—"
                print(f"  + {dd['full_name']}: {dd['mobile']} ({loc_name}) [tier_id={dd['tier_id']}]")
            else:
                # Update tier_id if missing
                if not existing.tier_id and dd["tier_id"]:
                    existing.tier_id = dd["tier_id"]
                    print(f"  ~ updated tier: {dd['mobile']}")
                if not existing.api_key:
                    existing.api_key = dd["api_key"]
                    print(f"  ~ updated api_key: {dd['mobile']}")
                else:
                    print(f"  = exists: {dd['mobile']}")

        db.flush()

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
        print(f"  Locations:      {db.query(Location).count()}")
        print(f"  Bars:           {db.query(Bar).count()}")
        print(f"  Coupons:        {db.query(Coupon).count()}")
        print(f"  Wallet Accts:   {db.query(Account).count()}")
        print(f"  Dealer Tiers:   {db.query(DealerTier).count()}")
        print(f"  Tier Wages:     {db.query(ProductTierWage).count()}")
        print(f"  Dealers:        {db.query(Dealer).count()}")
        print(f"  Tickets:        {db.query(Ticket).count()}")

        print("\n--- Credentials ---")
        print(f"  Admin:    09123456789")
        print(f"  Operator: 09121111111")
        print(f"  Customer: 09351234567 (wallet: 10M toman)")
        print(f"  Customer: 09359876543")
        print(f"  Customer: 09131112233")
        print(f"  Dealer:   09161234567 (esfahan, 2%)")
        print(f"  Dealer:   09171234567 (shiraz, 2.5%)")
        print(f"  Dealer:   09181234567 (mashhad, 3%)")

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
        print(f"  GOLD10    : 10% off (category: shamsh-gerami only)")

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
