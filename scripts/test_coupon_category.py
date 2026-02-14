"""Test coupon category restriction (M2M)."""
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal

# Import all models to resolve relationships
from modules.admin.models import SystemUser, SystemSetting  # noqa
from modules.customer.models import Customer  # noqa
from modules.customer.address_models import GeoProvince, GeoCity, GeoDistrict, CustomerAddress  # noqa
from modules.catalog.models import ProductCategory, Product, ProductImage  # noqa
from modules.inventory.models import Bar, Location, BarImage, OwnershipHistory  # noqa
from modules.cart.models import Cart, CartItem  # noqa
from modules.order.models import Order, OrderItem  # noqa
from modules.wallet.models import Account, LedgerEntry, WalletTopup, WithdrawalRequest  # noqa
from modules.coupon.models import Coupon, CouponMobile, CouponUsage, CouponCategory  # noqa
from modules.dealer.models import Dealer, DealerSale, BuybackRequest  # noqa

from modules.coupon.service import coupon_service, CouponValidationError

db = SessionLocal()

# 1. Check GOLD10 coupon exists with categories
coupon = db.query(Coupon).filter(Coupon.code == "GOLD10").first()
print(f"1. GOLD10 coupon: id={coupon.id}, scope={coupon.scope}")
cats = db.query(CouponCategory).filter(CouponCategory.coupon_id == coupon.id).all()
print(f"   Categories: {[(c.category_id, c.category.name) for c in cats]}")

# 2. Get category IDs
gold_bar_cat = db.query(ProductCategory).filter(ProductCategory.slug == "shamsh-gerami").first()
other_cat = db.query(ProductCategory).filter(ProductCategory.slug != "shamsh-gerami").first()
print(f"\n2. Gold bar category: id={gold_bar_cat.id}, name={gold_bar_cat.name}")
print(f"   Other category: id={other_cat.id}, name={other_cat.name}")

# 3. Test: GOLD10 with gold-bar category → should pass
try:
    result = coupon_service.validate(
        db, "GOLD10", customer_id=1, order_amount=50_000_000,
        category_ids=[gold_bar_cat.id]
    )
    print(f"\n3. GOLD10 + gold-bar category: PASS (discount={result['discount_amount']//10:,} toman)")
except CouponValidationError as e:
    print(f"\n3. GOLD10 + gold-bar category: FAIL - {e}")

# 4. Test: GOLD10 with other category → should fail
try:
    result = coupon_service.validate(
        db, "GOLD10", customer_id=1, order_amount=50_000_000,
        category_ids=[other_cat.id]
    )
    print(f"4. GOLD10 + other category: FAIL (should have been rejected!)")
except CouponValidationError as e:
    print(f"4. GOLD10 + other category: PASS (correctly rejected: {e})")

# 5. Test: GOLD10 with no category_ids → should fail
try:
    result = coupon_service.validate(
        db, "GOLD10", customer_id=1, order_amount=50_000_000,
        category_ids=[]
    )
    print(f"5. GOLD10 + empty categories: FAIL (should have been rejected!)")
except CouponValidationError as e:
    print(f"5. GOLD10 + empty categories: PASS (correctly rejected: {e})")

# 6. Test: WELCOME10 (GLOBAL scope) with any category → should pass
try:
    result = coupon_service.validate(
        db, "WELCOME10", customer_id=1, order_amount=50_000_000,
        category_ids=[other_cat.id]
    )
    print(f"6. WELCOME10 (GLOBAL) + any category: PASS (discount={result['discount_amount']//10:,} toman)")
except CouponValidationError as e:
    print(f"6. WELCOME10 (GLOBAL) + any category: FAIL - {e}")

# 7. Test: GOLD10 with both gold-bar and other → should pass (intersection not empty)
try:
    result = coupon_service.validate(
        db, "GOLD10", customer_id=1, order_amount=50_000_000,
        category_ids=[gold_bar_cat.id, other_cat.id]
    )
    print(f"7. GOLD10 + mixed categories: PASS (discount={result['discount_amount']//10:,} toman)")
except CouponValidationError as e:
    print(f"7. GOLD10 + mixed categories: FAIL - {e}")

db.close()
print("\nAll tests complete!")
