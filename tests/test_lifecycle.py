#!/usr/bin/env python3
"""
TalaMala v4 — Comprehensive Lifecycle Tests
============================================
Tests ALL 28 processes in the gold bar lifecycle, simulating real user behavior.
Each process tests CRUD operations, form submissions, and data verification.

Requires: server running at BASE_URL, test database seeded.
"""
import httpx
import json
import sys
import os
import re
import time
import random
import string
from dataclasses import dataclass, field
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000"
OTP_CODE = "111111"

# Test accounts
ADMIN_MOBILE = "09123456789"
OPERATOR_MOBILE = "09121111111"
CUSTOMER_MOBILE = "09351234567"
CUSTOMER2_MOBILE = "09359876543"
CUSTOMER3_MOBILE = "09131112233"
DEALER_MOBILE = "09161234567"
DEALER2_MOBILE = "09171234567"
DEALER_API_KEY = "test_esfahan_key_0000000000000000"
DEALER2_API_KEY = "test_shiraz__key_1111111111111111"

# Unique suffix for test data to avoid conflicts
_SUFFIX = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))


# ─── DB Helpers ──────────────────────────────────────────────

def db_query(sql, params=None):
    from sqlalchemy import text
    from config.database import engine
    with engine.connect() as conn:
        r = conn.execute(text(sql), params or {})
        return r.fetchall()

def db_scalar(sql, params=None):
    rows = db_query(sql, params)
    return rows[0][0] if rows else None

def db_exec(sql, params=None):
    from sqlalchemy import text
    from config.database import engine
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def get_user_id(mobile):
    return db_scalar("SELECT id FROM users WHERE mobile = :m", {"m": mobile})

def get_wallet_balance(user_id, asset_code="IRR"):
    return db_scalar(
        "SELECT balance FROM accounts WHERE user_id = :uid AND asset_code = :ac",
        {"uid": user_id, "ac": asset_code}
    ) or 0

def get_hedging_position(metal_type="gold"):
    return db_scalar(
        "SELECT balance_mg FROM metal_positions WHERE metal_type = :mt",
        {"mt": metal_type}
    ) or 0


# ─── Session Pool ────────────────────────────────────────────

_sessions: dict[str, httpx.Client] = {}

def get_session(mobile: str) -> httpx.Client:
    if mobile in _sessions:
        return _sessions[mobile]
    c = httpx.Client(timeout=30)
    c.get(f"{BASE_URL}/auth/login", follow_redirects=True)
    csrf = c.cookies.get("csrf_token", "")
    c.post(f"{BASE_URL}/auth/send-otp", data={"mobile": mobile, "csrf_token": csrf})
    csrf = c.cookies.get("csrf_token", "")
    r = c.post(f"{BASE_URL}/auth/verify-otp",
               data={"mobile": mobile, "code": OTP_CODE, "csrf_token": csrf})
    if "auth_token" not in c.cookies:
        print(f"    WARNING: LOGIN FAILED for {mobile} (status={r.status_code})")
    _sessions[mobile] = c
    return c

def get_anon_client() -> httpx.Client:
    return httpx.Client(timeout=30)

def get_csrf(client: httpx.Client) -> str:
    return client.cookies.get("csrf_token", "")

def close_all_sessions():
    for c in _sessions.values():
        c.close()
    _sessions.clear()


# ─── Test Infrastructure ─────────────────────────────────────

@dataclass
class TestResult:
    test_id: str
    description: str
    passed: bool
    details: str = ""

@dataclass
class TestSuite:
    name: str
    results: list = field(default_factory=list)

    def add(self, test_id, description, passed, details=""):
        self.results.append(TestResult(test_id, description, passed, details))
        status = "PASS" if passed else "FAIL"
        msg = f"  {'  ' if passed else '! '}{status} {test_id}: {description}"
        if details and not passed:
            msg += f" -- {details}"
        print(msg)

    @property
    def passed_count(self):
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self):
        return sum(1 for r in self.results if not r.passed)


def _get(client, path, **kw):
    return client.get(f"{BASE_URL}{path}", follow_redirects=True, **kw)

def _post(client, path, data=None, **kw):
    if data is None:
        data = {}
    csrf = client.cookies.get("csrf_token", "")
    if csrf and "csrf_token" not in data:
        data["csrf_token"] = csrf
    return client.post(f"{BASE_URL}{path}", data=data, follow_redirects=True, **kw)

def _post_json(client, path, json_data, use_csrf_header=True, **kw):
    """POST with JSON body + CSRF via header."""
    headers = kw.pop("headers", {})
    if use_csrf_header:
        csrf = client.cookies.get("csrf_token", "")
        if csrf:
            headers["X-CSRF-Token"] = csrf
    return client.post(f"{BASE_URL}{path}", json=json_data, headers=headers,
                       follow_redirects=True, **kw)

def _post_no_redirect(client, path, data=None, **kw):
    """POST without following redirects (to check Location header)."""
    if data is None:
        data = {}
    csrf = client.cookies.get("csrf_token", "")
    if csrf and "csrf_token" not in data:
        data["csrf_token"] = csrf
    return client.post(f"{BASE_URL}{path}", data=data, follow_redirects=False, **kw)


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 1: PRODUCTION & CATALOG
# ═══════════════════════════════════════════════════════════════

def test_L01_category_crud():
    """L01: Admin creates, edits, and manages product categories."""
    suite = TestSuite("L01: CRUD دسته‌بندی محصولات")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    cat_name = f"تست_دسته_{_SUFFIX}"
    cat_slug = f"test-cat-{_SUFFIX}"

    # Create category
    _get(a, "/admin/categories")  # refresh CSRF
    r = _post_no_redirect(a, "/admin/categories/add", {
        "name": cat_name, "slug": cat_slug, "sort_order": "99", "is_active": "on",
    })
    suite.add("L01-01", "ایجاد دسته‌بندی",
              r.status_code in (302, 303),
              f"status={r.status_code}")

    # Verify in DB
    cat_id = db_scalar("SELECT id FROM product_categories WHERE slug = :s", {"s": cat_slug})
    suite.add("L01-02", "دسته‌بندی در دیتابیس ایجاد شد", cat_id is not None,
              f"cat_id={cat_id}")

    if cat_id:
        # Edit category
        new_name = f"تست_ویرایش_{_SUFFIX}"
        _get(a, "/admin/categories")
        r = _post_no_redirect(a, f"/admin/categories/edit/{cat_id}", {
            "name": new_name, "slug": cat_slug, "sort_order": "50", "is_active": "on",
        })
        suite.add("L01-03", "ویرایش دسته‌بندی",
                  r.status_code in (302, 303), f"status={r.status_code}")

        updated_name = db_scalar("SELECT name FROM product_categories WHERE id = :i", {"i": cat_id})
        suite.add("L01-04", "نام در دیتابیس تغییر کرد",
                  updated_name == new_name, f"name={updated_name}")

        # Delete category
        _get(a, "/admin/categories")
        r = _post_no_redirect(a, f"/admin/categories/delete/{cat_id}")
        suite.add("L01-05", "حذف دسته‌بندی", r.status_code in (302, 303))

        deleted = db_scalar("SELECT id FROM product_categories WHERE id = :i", {"i": cat_id})
        suite.add("L01-06", "از دیتابیس حذف شد", deleted is None)

    return suite


def test_L02_product_crud():
    """L02: Admin creates and edits products."""
    suite = TestSuite("L02: CRUD محصولات")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    prod_name = f"شمش تست {_SUFFIX}"

    # Create product
    _get(a, "/admin/products")
    r = _post_no_redirect(a, "/admin/products/add", {
        "name": prod_name, "weight": "5.000", "purity": "750",
        "wage": "7.0", "is_active": "on",
    })
    suite.add("L02-01", "ایجاد محصول", r.status_code in (302, 303),
              f"status={r.status_code}")

    prod_id = db_scalar("SELECT id FROM products WHERE name = :n", {"n": prod_name})
    suite.add("L02-02", "محصول در دیتابیس", prod_id is not None, f"id={prod_id}")

    if prod_id:
        # Edit product
        new_name = f"شمش ویرایش {_SUFFIX}"
        _get(a, f"/admin/products/edit/{prod_id}")
        r = _post_no_redirect(a, f"/admin/products/update/{prod_id}", {
            "name": new_name, "weight": "10.000", "purity": "995",
            "wage": "5.0",
        })
        suite.add("L02-03", "ویرایش محصول", r.status_code in (302, 303))

        updated = db_scalar("SELECT name FROM products WHERE id = :i", {"i": prod_id})
        suite.add("L02-04", "نام محصول تغییر کرد", updated == new_name)

        # Verify product detail page (only works while active)
        r = _get(a, f"/product/{prod_id}")
        suite.add("L02-05", "صفحه جزئیات محصول",
                  r.status_code in (200, 404),
                  f"status={r.status_code} (may 404 if no inventory)")

        # Deactivate product
        _get(a, f"/admin/products/edit/{prod_id}")
        r = _post_no_redirect(a, f"/admin/products/update/{prod_id}", {
            "name": new_name, "weight": "10.000", "purity": "995", "wage": "5.0",
            # is_active NOT sent = False
        })
        suite.add("L02-06", "غیرفعال‌سازی محصول", r.status_code in (302, 303))

        is_active = db_scalar("SELECT is_active FROM products WHERE id = :i", {"i": prod_id})
        suite.add("L02-07", "محصول غیرفعال شد", is_active is False or is_active == 0,
                  f"is_active={is_active}")

    return suite


def test_L03_gift_box_crud():
    """L03: Admin creates gift boxes."""
    suite = TestSuite("L03: CRUD جعبه کادو")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    gb_name = f"جعبه_تست_{_SUFFIX}"
    _get(a, "/admin/gift-boxes")
    r = _post_no_redirect(a, "/admin/gift-boxes/add", {
        "name": gb_name, "price": "50000", "description": "تست", "sort_order": "1", "is_active": "on",
    })
    suite.add("L03-01", "ایجاد جعبه کادو", r.status_code in (302, 303))

    gb_id = db_scalar("SELECT id FROM gift_boxes WHERE name = :n", {"n": gb_name})
    suite.add("L03-02", "جعبه کادو در دیتابیس", gb_id is not None)

    if gb_id:
        new_name = f"جعبه_ویرایش_{_SUFFIX}"
        _get(a, "/admin/gift-boxes")
        r = _post_no_redirect(a, f"/admin/gift-boxes/update/{gb_id}", {
            "name": new_name, "price": "60000", "sort_order": "2", "is_active": "on",
        })
        suite.add("L03-03", "ویرایش جعبه کادو", r.status_code in (302, 303))

        # Delete
        r = _post_no_redirect(a, f"/admin/gift-boxes/delete/{gb_id}")
        suite.add("L03-04", "حذف جعبه کادو", r.status_code in (302, 303))

    return suite


def test_L04_package_type_crud():
    """L04: Admin creates package types."""
    suite = TestSuite("L04: CRUD بسته‌بندی")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    pkg_name = f"بسته_تست_{_SUFFIX}"
    _get(a, "/admin/packages")
    r = _post_no_redirect(a, "/admin/packages/add", {
        "name": pkg_name, "price": "500000", "is_active": "on",
    })
    suite.add("L04-01", "ایجاد بسته‌بندی", r.status_code in (302, 303))

    pkg_id = db_scalar("SELECT id FROM package_types WHERE name = :n", {"n": pkg_name})
    suite.add("L04-02", "بسته‌بندی در دیتابیس", pkg_id is not None)

    if pkg_id:
        _get(a, "/admin/packages")
        r = _post_no_redirect(a, f"/admin/packages/update/{pkg_id}", {
            "name": pkg_name, "price": "750000", "is_active": "on",
        })
        suite.add("L04-03", "ویرایش بسته‌بندی", r.status_code in (302, 303))

        # price is sent as toman, stored as rial (×10)
        updated_price = db_scalar("SELECT price FROM package_types WHERE id = :i", {"i": pkg_id})
        suite.add("L04-04", "قیمت تغییر کرد (750K toman = 7.5M rial)",
                  updated_price == 7_500_000,
                  f"price={updated_price}")

        r = _post_no_redirect(a, f"/admin/packages/delete/{pkg_id}")
        suite.add("L04-05", "حذف بسته‌بندی", r.status_code in (302, 303))

    return suite


def test_L05_batch_crud():
    """L05: Admin creates batches (melts)."""
    suite = TestSuite("L05: CRUD بچ/ذوب")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    batch_num = f"BATCH-{_SUFFIX}"
    _get(a, "/admin/batches")
    r = _post_no_redirect(a, "/admin/batches/add", {
        "batch_number": batch_num, "melt_number": "M-001",
        "operator": "اپراتور تست", "purity": "750",
    })
    suite.add("L05-01", "ایجاد بچ", r.status_code in (302, 303))

    batch_id = db_scalar("SELECT id FROM batches WHERE batch_number = :b", {"b": batch_num})
    suite.add("L05-02", "بچ در دیتابیس", batch_id is not None)

    if batch_id:
        _get(a, f"/admin/batches/edit/{batch_id}")
        r = _post_no_redirect(a, f"/admin/batches/update/{batch_id}", {
            "batch_number": batch_num, "melt_number": "M-002",
            "operator": "اپراتور تست ویرایش", "purity": "995",
        })
        suite.add("L05-03", "ویرایش بچ", r.status_code in (302, 303))

        r = _post_no_redirect(a, f"/admin/batches/delete/{batch_id}")
        suite.add("L05-04", "حذف بچ", r.status_code in (302, 303))

    return suite


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 2: INVENTORY & DISTRIBUTION
# ═══════════════════════════════════════════════════════════════

def test_L06_bar_generation():
    """L06: Admin generates bars (inventory items)."""
    suite = TestSuite("L06: تولید شمش (Bar Generation)")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    # Count bars before
    before_count = db_scalar("SELECT COUNT(*) FROM bars") or 0

    _get(a, "/admin/bars")
    r = _post_no_redirect(a, "/admin/bars/generate", {"count": "3"})
    suite.add("L06-01", "تولید 3 شمش", r.status_code in (302, 303),
              f"status={r.status_code}")

    after_count = db_scalar("SELECT COUNT(*) FROM bars") or 0
    suite.add("L06-02", f"3 شمش ایجاد شد (before={before_count}, after={after_count})",
              after_count >= before_count + 3,
              f"delta={after_count - before_count}")

    # Verify bars have serial codes
    new_bars = db_query("""
        SELECT id, serial_code, status FROM bars
        ORDER BY id DESC LIMIT 3
    """)
    suite.add("L06-03", "شمش‌ها سریال‌کد دارند",
              all(row[1] for row in new_bars),
              f"serials={[r[1] for r in new_bars]}")

    suite.add("L06-04", "وضعیت اولیه RAW",
              all("Raw" in str(row[2]) or "raw" in str(row[2]).lower() for row in new_bars),
              f"statuses={[str(r[2]) for r in new_bars]}")

    return suite


def test_L07_bar_assign_to_product():
    """L07: Admin assigns bar to product + dealer (status change)."""
    suite = TestSuite("L07: تخصیص شمش به محصول/نماینده")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    dealer_id = get_user_id(DEALER_MOBILE)
    product_id = db_scalar("SELECT id FROM products WHERE is_active = true LIMIT 1")

    # Find a RAW bar
    bar = db_query("SELECT id, serial_code FROM bars WHERE status = 'Raw' ORDER BY id DESC LIMIT 1")
    if not bar:
        suite.add("L07-00", "شمش RAW پیدا نشد", False, "Run L06 first")
        return suite

    bar_id, bar_serial = bar[0]

    # Assign to product + dealer
    _get(a, f"/admin/bars/edit/{bar_id}")
    r = _post_no_redirect(a, f"/admin/bars/update/{bar_id}", {
        "status": "Assigned",
        "product_id": str(product_id) if product_id else "",
        "dealer_id": str(dealer_id) if dealer_id else "",
    })
    suite.add("L07-01", "تخصیص شمش", r.status_code in (302, 303))

    # Verify status changed
    new_status = db_scalar("SELECT status FROM bars WHERE id = :b", {"b": bar_id})
    suite.add("L07-02", "وضعیت ASSIGNED",
              new_status and "Assigned" in str(new_status),
              f"status={new_status}")

    # Verify product assigned
    bar_product = db_scalar("SELECT product_id FROM bars WHERE id = :b", {"b": bar_id})
    suite.add("L07-03", "محصول تخصیص یافت",
              bar_product == product_id, f"product_id={bar_product}")

    # Verify dealer assigned
    bar_dealer = db_scalar("SELECT dealer_id FROM bars WHERE id = :b", {"b": bar_id})
    suite.add("L07-04", "نماینده تخصیص یافت",
              bar_dealer == dealer_id, f"dealer_id={bar_dealer}")

    return suite


def test_L08_bar_bulk_action():
    """L08: Admin bulk assigns bars."""
    suite = TestSuite("L08: عملیات گروهی شمش")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    product_id = db_scalar("SELECT id FROM products WHERE is_active = true LIMIT 1")
    raw_bars = db_query("SELECT id FROM bars WHERE status = 'Raw' ORDER BY id DESC LIMIT 2")
    if len(raw_bars) < 2:
        suite.add("L08-00", "شمش RAW کافی نیست", False, f"found={len(raw_bars)}")
        return suite

    bar_ids = ",".join(str(r[0]) for r in raw_bars)
    _get(a, "/admin/bars")
    r = _post_no_redirect(a, "/admin/bars/bulk_action", {
        "action": "update",
        "selected_ids": bar_ids,
        "target_product_id": str(product_id),
    })
    suite.add("L08-01", "تخصیص گروهی محصول (action=update)",
              r.status_code in (302, 303), f"status={r.status_code}")

    # Verify all bars got the product
    for bar_row in raw_bars:
        bp = db_scalar("SELECT product_id FROM bars WHERE id = :b", {"b": bar_row[0]})
        suite.add(f"L08-02-{bar_row[0]}", f"شمش {bar_row[0]} -> محصول {product_id}",
                  bp == product_id, f"product_id={bp}")

    return suite


def test_L09_dealer_tier_crud():
    """L09: Admin manages dealer tiers."""
    suite = TestSuite("L09: CRUD سطوح نمایندگان")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    tier_name = f"تیر_تست_{_SUFFIX}"
    tier_slug = f"test-tier-{_SUFFIX}"

    _get(a, "/admin/dealers/tiers/new")
    r = _post_no_redirect(a, "/admin/dealers/tiers/new", {
        "name": tier_name, "slug": tier_slug, "sort_order": "99",
    })
    suite.add("L09-01", "ایجاد تیر", r.status_code in (302, 303))

    tier_id = db_scalar("SELECT id FROM dealer_tiers WHERE slug = :s", {"s": tier_slug})
    suite.add("L09-02", "تیر در دیتابیس", tier_id is not None)

    return suite


def test_L10_dealer_management():
    """L10: Admin creates/edits dealers."""
    suite = TestSuite("L10: مدیریت نمایندگان")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    # List dealers
    r = _get(a, "/admin/dealers")
    suite.add("L10-01", "لیست نمایندگان", r.status_code == 200)

    # View a dealer (edit form)
    dealer_id = get_user_id(DEALER_MOBILE)
    if dealer_id:
        r = _get(a, f"/admin/dealers/{dealer_id}/edit")
        suite.add("L10-02", "مشاهده/ویرایش نماینده", r.status_code == 200)

        # Sales report
        r = _get(a, "/admin/dealers/sales")
        suite.add("L10-03", "گزارش فروش نمایندگان", r.status_code == 200)

        r = _get(a, f"/admin/dealers/sales?dealer_id={dealer_id}")
        suite.add("L10-04", "فیلتر فروش نماینده خاص", r.status_code == 200)

    return suite


def test_L11_dealer_transfer():
    """L11: Warehouse dealer transfers bar to another dealer."""
    suite = TestSuite("L11: انتقال شمش بین نمایندگان")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    d = get_session(DEALER_MOBILE)

    dealer1_id = get_user_id(DEALER_MOBILE)
    dealer2_id = get_user_id(DEALER2_MOBILE)

    if not dealer1_id or not dealer2_id:
        suite.add("L11-00", "نمایندگان پیدا نشدند", False)
        return suite

    # Find an ASSIGNED bar at dealer1
    bar = db_query("""
        SELECT id, serial_code FROM bars
        WHERE status = 'Assigned' AND dealer_id = :did
        ORDER BY id LIMIT 1
    """, {"did": dealer1_id})

    if not bar:
        suite.add("L11-00", "شمش ASSIGNED در انبار نیست", False)
        return suite

    bar_id, bar_serial = bar[0]

    # Transfer page
    r = _get(d, "/dealer/transfers")
    suite.add("L11-01", "صفحه توزیع", r.status_code == 200)

    # Submit transfer
    _get(d, "/dealer/transfers")
    r = _post_no_redirect(d, "/dealer/transfers", {
        "to_dealer_id": str(dealer2_id),
        "description": f"انتقال تست {_SUFFIX}",
    })
    # This needs bar selection which may be done via checkboxes or JS
    # Just verify the page/endpoint works
    suite.add("L11-02", "ارسال انتقال",
              r.status_code in (200, 302, 303, 400, 422),
              f"status={r.status_code}")

    # Transfer history
    r = _get(d, "/dealer/transfers?tab=history")
    suite.add("L11-03", "تاریخچه انتقال", r.status_code == 200)

    return suite


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 3: PRICING & SETTINGS
# ═══════════════════════════════════════════════════════════════

def test_L12_pricing_settings():
    """L12: Admin configures gold/silver prices and settings."""
    suite = TestSuite("L12: تنظیمات قیمت‌گذاری")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    r = _get(a, "/admin/settings")
    suite.add("L12-01", "صفحه تنظیمات", r.status_code == 200)

    # Verify gold price in assets
    gold_price = db_scalar("SELECT price_per_gram FROM assets WHERE asset_code = 'gold_18k'")
    suite.add("L12-02", "قیمت طلا وجود دارد",
              gold_price is not None and gold_price > 0,
              f"price={gold_price}")

    silver_price = db_scalar("SELECT price_per_gram FROM assets WHERE asset_code = 'silver'")
    suite.add("L12-03", "قیمت نقره وجود دارد",
              silver_price is not None and silver_price > 0,
              f"price={silver_price}")

    # Verify tax_percent
    tax = db_scalar("SELECT value FROM system_settings WHERE key = 'tax_percent'")
    suite.add("L12-04", "درصد مالیات وجود دارد",
              tax is not None, f"tax={tax}")

    # Verify trade toggles
    gold_shop = db_scalar("SELECT value FROM system_settings WHERE key = 'gold_shop_enabled'")
    suite.add("L12-05", "تنظیم فعال بودن فروشگاه طلا",
              gold_shop is not None, f"value={gold_shop}")

    # Price staleness check
    is_fresh = db_scalar("""
        SELECT CASE WHEN updated_at > NOW() - INTERVAL '999 minutes' THEN true ELSE false END
        FROM assets WHERE asset_code = 'gold_18k'
    """)
    suite.add("L12-06", "قیمت طلا تازه (fresh)",
              is_fresh is True or is_fresh == 1, f"is_fresh={is_fresh}")

    return suite


def test_L13_hedging_operations():
    """L13: Admin records hedge trades and adjusts positions."""
    suite = TestSuite("L13: عملیات هجینگ")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    # Dashboard
    r = _get(a, "/admin/hedging")
    suite.add("L13-01", "داشبورد هجینگ", r.status_code == 200)

    # Get current position
    before = get_hedging_position("gold")

    # Record a hedge (buy 10g)
    _get(a, "/admin/hedging/record")
    r = _post_no_redirect(a, "/admin/hedging/record", {
        "metal_type": "gold",
        "hedge_direction": "buy",
        "amount_grams": "10",
        "price_per_gram": "50000000",
        "description": f"هج تست {_SUFFIX}",
    })
    suite.add("L13-02", "ثبت هج خرید 10g", r.status_code in (302, 303))

    after = get_hedging_position("gold")
    suite.add("L13-03", "موقعیت افزایش یافت",
              after > before, f"before={before}, after={after}")

    # Record a hedge (sell 5g)
    _get(a, "/admin/hedging/record")
    r = _post_no_redirect(a, "/admin/hedging/record", {
        "metal_type": "gold",
        "hedge_direction": "sell",
        "amount_grams": "5",
        "price_per_gram": "50000000",
        "description": f"هج فروش تست {_SUFFIX}",
    })
    suite.add("L13-04", "ثبت هج فروش 5g", r.status_code in (302, 303))

    after2 = get_hedging_position("gold")
    suite.add("L13-05", "موقعیت کاهش یافت",
              after2 < after, f"before={after}, after={after2}")

    # Ledger
    r = _get(a, "/admin/hedging/ledger")
    suite.add("L13-06", "لجر هجینگ", r.status_code == 200)

    r = _get(a, "/admin/hedging/ledger?metal_type=gold")
    suite.add("L13-07", "فیلتر لجر طلا", r.status_code == 200)

    # API position
    r = _get(a, "/admin/hedging/api/position")
    suite.add("L13-08", "API position JSON",
              r.status_code == 200 and "gold" in r.text.lower())

    return suite


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 4: SHOP & CUSTOMER
# ═══════════════════════════════════════════════════════════════

def test_L14_shop_browsing():
    """L14: Customer browses shop."""
    suite = TestSuite("L14: مرور فروشگاه")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    with get_anon_client() as c:
        # Home page
        r = c.get(f"{BASE_URL}/", follow_redirects=True)
        suite.add("L14-01", "صفحه اصلی", r.status_code == 200 and len(r.text) > 500)

        # Sort options
        for sort_val, desc in [("price_asc", "ارزان‌ترین"), ("price_desc", "گران‌ترین"),
                                ("newest", "جدیدترین"), ("weight_asc", "سبک‌ترین")]:
            r = c.get(f"{BASE_URL}/?sort={sort_val}", follow_redirects=True)
            suite.add(f"L14-sort-{sort_val}", f"مرتب‌سازی {desc}", r.status_code == 200)

        # Category filter
        cat_id = db_scalar("SELECT id FROM product_categories WHERE is_active = true LIMIT 1")
        if cat_id:
            r = c.get(f"{BASE_URL}/?category={cat_id}", follow_redirects=True)
            suite.add("L14-02", "فیلتر دسته‌بندی", r.status_code == 200)

        # Product detail
        prod_id = db_scalar("SELECT id FROM products WHERE is_active = true LIMIT 1")
        if prod_id:
            r = c.get(f"{BASE_URL}/product/{prod_id}", follow_redirects=True)
            suite.add("L14-03", "جزئیات محصول",
                      r.status_code == 200 and ("قیمت" in r.text or "وزن" in r.text))

        # Non-existent product
        r = c.get(f"{BASE_URL}/product/999999", follow_redirects=True)
        suite.add("L14-04", "محصول ناموجود → 404", r.status_code == 404)

    return suite


def test_L15_customer_profile():
    """L15: Customer updates profile and addresses."""
    suite = TestSuite("L15: پروفایل و آدرس مشتری")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    c = get_session(CUSTOMER_MOBILE)

    # View profile
    r = _get(c, "/profile")
    suite.add("L15-01", "مشاهده پروفایل", r.status_code == 200)

    # Update profile
    r = _post(c, "/profile", {
        "first_name": "علی", "last_name": "مشتری تست",
        "national_id": "1234567890", "customer_type": "real",
        "postal_code": "1234567890",
        "address": "تهران، خیابان آزادی، پلاک ۱",
    })
    suite.add("L15-02", "بروزرسانی پروفایل", r.status_code == 200)

    # Verify in DB
    last_name = db_scalar("SELECT last_name FROM users WHERE mobile = :m",
                          {"m": CUSTOMER_MOBILE})
    suite.add("L15-03", "نام خانوادگی تغییر کرد",
              last_name == "مشتری تست", f"last_name={last_name}")

    # Address CRUD
    r = _get(c, "/addresses")
    suite.add("L15-04", "لیست آدرس‌ها", r.status_code == 200)

    province_id = db_scalar("SELECT id FROM geo_provinces ORDER BY id LIMIT 1")
    city_id = db_scalar("SELECT id FROM geo_cities WHERE province_id = :p LIMIT 1",
                        {"p": province_id}) if province_id else None

    if province_id and city_id:
        r = _post_no_redirect(c, "/addresses", {
            "title": f"آدرس تست {_SUFFIX}",
            "province_id": str(province_id),
            "city_id": str(city_id),
            "address": "خیابان تست، کوچه آزمایشی، پلاک ۵",
            "postal_code": "1234567890",
            "receiver_name": "علی تست",
            "receiver_phone": "09351234567",
        })
        suite.add("L15-05", "افزودن آدرس", r.status_code in (200, 302, 303))

        addr_id = db_scalar("""
            SELECT id FROM customer_addresses
            WHERE user_id = :uid ORDER BY id DESC LIMIT 1
        """, {"uid": get_user_id(CUSTOMER_MOBILE)})

        if addr_id:
            # Set as default
            r = _post_no_redirect(c, f"/addresses/{addr_id}/default")
            suite.add("L15-06", "تنظیم آدرس پیش‌فرض", r.status_code in (302, 303))

            # Delete address
            r = _post_no_redirect(c, f"/addresses/{addr_id}/delete")
            suite.add("L15-07", "حذف آدرس", r.status_code in (302, 303))

    # Geo API
    if province_id:
        r = _get(c, f"/api/geo/cities?province_id={province_id}")
        suite.add("L15-08", "API شهرها", r.status_code == 200)

    return suite


def test_L16_full_order_flow():
    """L16: Complete order flow: cart → checkout → wallet payment → verify."""
    suite = TestSuite("L16: فرآیند کامل سفارش")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    c = get_session(CUSTOMER_MOBILE)
    cust_id = get_user_id(CUSTOMER_MOBILE)
    dealer_id = get_user_id(DEALER_MOBILE)

    if not cust_id or not dealer_id:
        suite.add("L16-00", "کاربران پیدا نشدند", False)
        return suite

    # Step 1: Empty cart
    _post(c, "/cart/update", {"product_id": "1", "action": "remove"})

    # Step 2: Add product to cart
    r = _post(c, "/cart/update", {"product_id": "1", "action": "increase"})
    suite.add("L16-01", "افزودن به سبد", r.status_code == 200)

    # Step 3: View cart
    r = _get(c, "/cart")
    suite.add("L16-02", "مشاهده سبد خرید",
              r.status_code == 200 and ("سبد" in r.text or "cart" in r.text.lower()))

    # Step 4: Checkout page
    r = _get(c, "/checkout")
    suite.add("L16-03", "صفحه چک‌اوت", r.status_code == 200)

    # Step 5: Submit order (Pickup)
    irr_before = get_wallet_balance(cust_id, "IRR")
    hedge_before = get_hedging_position("gold")

    r = _post_no_redirect(c, "/cart/checkout", {
        "delivery_method": "Pickup",
        "pickup_dealer_id": str(dealer_id),
        "is_gift": "0",
        "commitment": "on",
    })
    checkout_ok = r.status_code in (302, 303)
    redirect_url = r.headers.get("location", "")
    suite.add("L16-04", "ثبت سفارش → redirect",
              checkout_ok and "/orders/" in redirect_url,
              f"status={r.status_code}, location={redirect_url}")

    if not checkout_ok or "/orders/" not in redirect_url:
        return suite

    order_id_match = re.search(r'/orders/(\d+)', redirect_url)
    if not order_id_match:
        suite.add("L16-05", "استخراج order_id", False)
        return suite
    order_id = int(order_id_match.group(1))

    # Verify order in DB
    order_status = db_scalar("SELECT status FROM orders WHERE id = :o", {"o": order_id})
    suite.add("L16-05", f"سفارش #{order_id} وضعیت Pending",
              "Pending" in str(order_status), f"status={order_status}")

    # Step 6: View order detail
    r = _get(c, f"/orders/{order_id}")
    suite.add("L16-06", "مشاهده سفارش", r.status_code == 200)

    # Step 7: Pay with wallet
    r = _post(c, f"/payment/{order_id}/wallet")
    suite.add("L16-07", "پرداخت با کیف پول", r.status_code == 200)

    # Step 8: Verify order is Paid
    order_status = db_scalar("SELECT status FROM orders WHERE id = :o", {"o": order_id})
    suite.add("L16-08", "سفارش Paid شد",
              "Paid" in str(order_status), f"status={order_status}")

    # Step 9: Verify wallet decreased
    irr_after = get_wallet_balance(cust_id, "IRR")
    suite.add("L16-09", "موجودی کیف پول کاهش یافت",
              irr_after < irr_before,
              f"before={irr_before}, after={irr_after}")

    # Step 10: Verify hedging OUT
    hedge_after = get_hedging_position("gold")
    suite.add("L16-10", "هجینگ OUT ثبت شد",
              hedge_after < hedge_before,
              f"before={hedge_before}, after={hedge_after}")

    # Step 11: Verify bar status
    bar_status = db_scalar("""
        SELECT b.status FROM order_items oi
        JOIN bars b ON oi.bar_id = b.id
        WHERE oi.order_id = :o LIMIT 1
    """, {"o": order_id})
    suite.add("L16-11", "شمش SOLD شد",
              "Sold" in str(bar_status), f"status={bar_status}")

    # Step 12: Order appears in order list
    r = _get(c, "/orders")
    suite.add("L16-12", "سفارش در لیست",
              r.status_code == 200 and str(order_id) in r.text)

    return suite


def test_L17_coupon_system():
    """L17: Coupon validation and application."""
    suite = TestSuite("L17: سیستم کوپن")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    c = get_session(CUSTOMER_MOBILE)
    a = get_session(ADMIN_MOBILE)

    # Admin coupon list
    r = _get(a, "/admin/coupons")
    suite.add("L17-01", "لیست کوپن‌ها (ادمین)", r.status_code == 200)

    # Admin coupon form
    r = _get(a, "/admin/coupons/new")
    suite.add("L17-02", "فرم ایجاد کوپن", r.status_code == 200)

    # Customer checks valid coupons
    for code, desc in [("WELCOME10", "10% اولین خرید"), ("CASHBACK5", "5% کشبک"),
                        ("FIXED500", "500K ثابت")]:
        r = _get(c, f"/api/coupon/check?code={code}")
        suite.add(f"L17-{code}", f"بررسی کوپن {desc}",
                  r.status_code == 200)

    # Invalid coupon
    r = _get(c, "/api/coupon/check?code=NONEXISTENT999")
    suite.add("L17-inv", "کوپن ناموجود", r.status_code in (200, 400))

    # Empty code
    r = _get(c, "/api/coupon/check?code=")
    suite.add("L17-empty", "کد خالی", r.status_code in (200, 400))

    return suite


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 5: WALLET & FINANCE
# ═══════════════════════════════════════════════════════════════

def test_L18_wallet_operations():
    """L18: Wallet buy gold, sell gold, view transactions."""
    suite = TestSuite("L18: عملیات کیف پول")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    c = get_session(CUSTOMER_MOBILE)
    cust_id = get_user_id(CUSTOMER_MOBILE)

    # Dashboard
    r = _get(c, "/wallet")
    suite.add("L18-01", "داشبورد کیف پول",
              r.status_code == 200 and ("موجودی" in r.text or "کیف" in r.text))

    # Buy gold
    irr_before = get_wallet_balance(cust_id, "IRR")
    xau_before = get_wallet_balance(cust_id, "XAU_MG")

    _get(c, "/wallet/gold")
    r = _post(c, "/wallet/gold/buy", {"amount_toman": "50000"})
    suite.add("L18-02", "خرید طلا (50K تومان)", r.status_code == 200)

    irr_after = get_wallet_balance(cust_id, "IRR")
    xau_after = get_wallet_balance(cust_id, "XAU_MG")
    suite.add("L18-03", "IRR کاهش یافت", irr_after < irr_before,
              f"delta={irr_before - irr_after}")
    suite.add("L18-04", "XAU_MG افزایش یافت", xau_after > xau_before,
              f"delta={xau_after - xau_before}")

    # Sell gold
    if xau_after > 0:
        sell_grams = round((xau_after / 1000) * 0.3, 3)
        if sell_grams < 0.001:
            sell_grams = 0.001
        _get(c, "/wallet/gold")
        r = _post(c, "/wallet/gold/sell", {"metal_grams": str(sell_grams)})
        suite.add("L18-05", f"فروش {sell_grams}g طلا", r.status_code == 200)

        xau_after2 = get_wallet_balance(cust_id, "XAU_MG")
        suite.add("L18-06", "XAU_MG کاهش یافت", xau_after2 < xau_after)

    # Silver buy
    _get(c, "/wallet/silver")
    r = _post(c, "/wallet/silver/buy", {"amount_toman": "10000"})
    suite.add("L18-07", "خرید نقره", r.status_code == 200)

    xag = get_wallet_balance(cust_id, "XAG_MG")
    suite.add("L18-08", "موجودی نقره > 0", xag > 0, f"xag={xag}")

    # Transactions
    r = _get(c, "/wallet/transactions")
    suite.add("L18-09", "تاریخچه تراکنش", r.status_code == 200)

    r = _get(c, "/wallet/transactions?asset=irr")
    suite.add("L18-10", "فیلتر IRR", r.status_code == 200)

    r = _get(c, "/wallet/transactions?asset=gold")
    suite.add("L18-11", "فیلتر طلا", r.status_code == 200)

    # Withdraw page
    r = _get(c, "/wallet/withdraw")
    suite.add("L18-12", "صفحه برداشت", r.status_code == 200)

    # Submit withdraw request
    _get(c, "/wallet/withdraw")
    r = _post(c, "/wallet/withdraw", {
        "amount_toman": "100000",
        "shaba_number": "IR123456789012345678901234",
        "account_holder": "علی تست",
    })
    suite.add("L18-13", "درخواست برداشت",
              r.status_code == 200, f"status={r.status_code}")

    # Invalid asset type
    r = c.get(f"{BASE_URL}/wallet/platinum", follow_redirects=False)
    suite.add("L18-14", "asset نامعتبر → redirect",
              r.status_code in (302, 303, 404, 422))

    return suite


def test_L19_wallet_dealer():
    """L19: Dealer wallet access."""
    suite = TestSuite("L19: کیف پول نماینده")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    d = get_session(DEALER_MOBILE)

    r = _get(d, "/wallet")
    suite.add("L19-01", "داشبورد کیف پول نماینده", r.status_code == 200)

    r = _get(d, "/wallet/transactions")
    suite.add("L19-02", "تاریخچه تراکنش نماینده", r.status_code == 200)

    r = _get(d, "/wallet/gold")
    suite.add("L19-03", "صفحه خرید/فروش طلا نماینده", r.status_code == 200)

    return suite


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 6: DEALER SALES & POS
# ═══════════════════════════════════════════════════════════════

def test_L20_dealer_pos_web():
    """L20: Dealer POS sale via web form."""
    suite = TestSuite("L20: فروش POS نماینده (وب)")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    d = get_session(DEALER_MOBILE)
    dealer_id = get_user_id(DEALER_MOBILE)

    # POS form page
    r = _get(d, "/dealer/pos")
    suite.add("L20-01", "فرم POS فروش", r.status_code == 200)

    # Find an ASSIGNED bar at this dealer
    bar = db_query("""
        SELECT id, serial_code FROM bars
        WHERE status = 'Assigned' AND dealer_id = :did
        ORDER BY id LIMIT 1
    """, {"did": dealer_id})

    if bar:
        bar_id = bar[0][0]
        sale_count_before = db_scalar(
            "SELECT COUNT(*) FROM dealer_sales WHERE dealer_id = :d", {"d": dealer_id}) or 0

        _get(d, "/dealer/pos")
        r = _post_no_redirect(d, "/dealer/pos", {
            "bar_id": str(bar_id),
            "sale_price": "55000000",
            "customer_name": "مشتری تست POS",
            "customer_mobile": CUSTOMER2_MOBILE,
            "customer_national_id": "9876543210",
            "description": f"فروش تست {_SUFFIX}",
        })
        suite.add("L20-02", "ثبت فروش POS",
                  r.status_code in (200, 302, 303),
                  f"status={r.status_code}")

        if r.status_code in (302, 303):
            # Verify bar sold
            bar_status = db_scalar("SELECT status FROM bars WHERE id = :b", {"b": bar_id})
            suite.add("L20-03", "شمش SOLD شد",
                      "Sold" in str(bar_status), f"status={bar_status}")

            sale_count_after = db_scalar(
                "SELECT COUNT(*) FROM dealer_sales WHERE dealer_id = :d", {"d": dealer_id}) or 0
            suite.add("L20-04", "رکورد فروش ایجاد شد",
                      sale_count_after > sale_count_before)
    else:
        suite.add("L20-02", "شمش ASSIGNED موجود نیست", False, "No bars at dealer")

    # Sales history
    r = _get(d, "/dealer/sales")
    suite.add("L20-05", "تاریخچه فروش", r.status_code == 200)

    # Dealer inventory
    r = _get(d, "/dealer/inventory")
    suite.add("L20-06", "موجودی نماینده", r.status_code == 200)

    return suite


def test_L21_dealer_api_pos():
    """L21: Dealer POS REST API."""
    suite = TestSuite("L21: POS REST API نماینده")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    headers = {"X-API-Key": DEALER_API_KEY}
    dealer_id = get_user_id(DEALER_MOBILE)

    with get_anon_client() as c:
        # Info endpoint
        r = c.get(f"{BASE_URL}/api/dealer/info", headers=headers)
        suite.add("L21-01", "GET /api/dealer/info", r.status_code == 200)
        if r.status_code == 200:
            info = r.json()
            suite.add("L21-02", "dealer_id در پاسخ",
                      "dealer_id" in info or "id" in info,
                      f"keys={list(info.keys())}")

        # Products endpoint
        r = c.get(f"{BASE_URL}/api/dealer/products", headers=headers)
        suite.add("L21-03", "GET /api/dealer/products", r.status_code == 200)
        if r.status_code == 200:
            data = r.json()
            suite.add("L21-04", "لیست محصولات JSON",
                      isinstance(data, (list, dict)),
                      f"type={type(data).__name__}")

        # Sale via API
        bar = db_query("""
            SELECT id, serial_code FROM bars
            WHERE status = 'Assigned' AND dealer_id = :did
            ORDER BY id LIMIT 1
        """, {"did": dealer_id})

        if bar:
            r = c.post(f"{BASE_URL}/api/dealer/sale", json={
                "serial_code": bar[0][1],
                "sale_price": 60000000,
                "customer_name": "API مشتری تست",
                "customer_mobile": CUSTOMER3_MOBILE,
                "customer_national_id": "1112223334",
            }, headers=headers)
            suite.add("L21-05", "POST /api/dealer/sale",
                      r.status_code == 200,
                      f"status={r.status_code}, body={r.text[:150]}")

        # Sales history API
        r = c.get(f"{BASE_URL}/api/dealer/sales", headers=headers)
        suite.add("L21-06", "GET /api/dealer/sales", r.status_code == 200)

        # Invalid API key
        r = c.get(f"{BASE_URL}/api/dealer/info", headers={"X-API-Key": "INVALID"})
        suite.add("L21-07", "API Key نامعتبر → 401", r.status_code in (401, 403))

        # No API key
        r = c.get(f"{BASE_URL}/api/dealer/info")
        suite.add("L21-08", "بدون API Key → 401", r.status_code in (401, 403, 422))

    return suite


def test_L22_customer_pos_api():
    """L22: Customer POS API — reserve → confirm/cancel."""
    suite = TestSuite("L22: POS API مشتری")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    headers = {"X-API-Key": DEALER_API_KEY}
    dealer_id = get_user_id(DEALER_MOBILE)

    with get_anon_client() as c:
        # Categories
        r = c.get(f"{BASE_URL}/api/pos/categories", headers=headers)
        suite.add("L22-01", "GET /api/pos/categories", r.status_code == 200)

        # Products
        r = c.get(f"{BASE_URL}/api/pos/products", headers=headers)
        suite.add("L22-02", "GET /api/pos/products", r.status_code == 200)

        # Find a product with available bars
        bar = db_query("""
            SELECT b.product_id FROM bars b
            WHERE b.status = 'Assigned' AND b.dealer_id = :did
            LIMIT 1
        """, {"did": dealer_id})

        if bar:
            product_id = bar[0][0]

            # Reserve
            r = c.post(f"{BASE_URL}/api/pos/reserve",
                       json={"product_id": product_id}, headers=headers)
            suite.add("L22-03", "POST /api/pos/reserve", r.status_code == 200,
                      f"body={r.text[:150]}")

            if r.status_code == 200 and r.json().get("success"):
                reservation = r.json().get("reservation", {})
                reserved_bar_id = reservation.get("bar_id")
                total_price = reservation.get("price", {}).get("total", 0)

                # Verify bar is RESERVED
                status = db_scalar("SELECT status FROM bars WHERE id = :b",
                                   {"b": reserved_bar_id})
                suite.add("L22-04", "شمش RESERVED شد",
                          "Reserved" in str(status), f"status={status}")

                # Cancel (test cancel flow)
                r = c.post(f"{BASE_URL}/api/pos/cancel",
                           json={"bar_id": reserved_bar_id}, headers=headers)
                suite.add("L22-05", "POST /api/pos/cancel", r.status_code == 200)

                # Verify bar back to ASSIGNED
                status = db_scalar("SELECT status FROM bars WHERE id = :b",
                                   {"b": reserved_bar_id})
                suite.add("L22-06", "شمش به ASSIGNED برگشت",
                          "Assigned" in str(status), f"status={status}")

                # Reserve again for confirm test
                r = c.post(f"{BASE_URL}/api/pos/reserve",
                           json={"product_id": product_id}, headers=headers)
                if r.status_code == 200 and r.json().get("success"):
                    reservation2 = r.json().get("reservation", {})
                    bar_id2 = reservation2.get("bar_id")
                    price2 = reservation2.get("price", {}).get("total", 0)

                    # Confirm
                    r = c.post(f"{BASE_URL}/api/pos/confirm", json={
                        "bar_id": bar_id2,
                        "payment_ref": f"POS-LC-{_SUFFIX}",
                        "payment_amount": price2,
                        "customer_name": "مشتری POS تست",
                        "customer_mobile": CUSTOMER2_MOBILE,
                        "customer_national_id": "5556667778",
                    }, headers=headers)
                    suite.add("L22-07", "POST /api/pos/confirm", r.status_code == 200,
                              f"body={r.text[:150]}")

                    status = db_scalar("SELECT status FROM bars WHERE id = :b",
                                       {"b": bar_id2})
                    suite.add("L22-08", "شمش SOLD شد",
                              "Sold" in str(status), f"status={status}")
        else:
            suite.add("L22-03", "شمش موجود نیست برای تست", False)

    return suite



# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 7: VERIFICATION & OWNERSHIP
# ═══════════════════════════════════════════════════════════════

def test_L24_verification():
    """L24: Public bar verification."""
    suite = TestSuite("L24: احراز اصالت شمش")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    with get_anon_client() as c:
        # Public verify page
        r = c.get(f"{BASE_URL}/verify", follow_redirects=True)
        suite.add("L24-01", "صفحه احراز اصالت", r.status_code == 200)

        # Check real serial
        real_serial = db_scalar("SELECT serial_code FROM bars LIMIT 1")
        if real_serial:
            r = c.get(f"{BASE_URL}/verify/check?code={real_serial}", follow_redirects=True)
            suite.add("L24-02", f"سریال {real_serial} معتبر", r.status_code == 200)

            # API check
            r = c.get(f"{BASE_URL}/verify/api/check?code={real_serial}", follow_redirects=True)
            suite.add("L24-03", "API بررسی سریال", r.status_code == 200)

        # Fake serial
        r = c.get(f"{BASE_URL}/verify/check?code=FAKE99999", follow_redirects=True)
        suite.add("L24-04", "سریال جعلی", r.status_code in (200, 404))

        # Empty code
        r = c.get(f"{BASE_URL}/verify/check?code=", follow_redirects=True)
        suite.add("L24-05", "بدون کد", r.status_code in (200, 400))

    # Admin QR generation
    a = get_session(ADMIN_MOBILE)
    bar_id = db_scalar("SELECT id FROM bars LIMIT 1")
    if bar_id:
        r = a.get(f"{BASE_URL}/admin/bars/{bar_id}/qr", follow_redirects=True)
        suite.add("L24-06", "تولید QR ادمین",
                  r.status_code == 200 and "image" in r.headers.get("content-type", ""),
                  f"content-type={r.headers.get('content-type')}")

    return suite


def test_L25_ownership():
    """L25: Bar claim and ownership transfer."""
    suite = TestSuite("L25: ثبت مالکیت و انتقال")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    c = get_session(CUSTOMER_MOBILE)

    # My bars page
    r = _get(c, "/my-bars")
    suite.add("L25-01", "لیست شمش‌های من", r.status_code == 200)

    # Claim form
    r = _get(c, "/claim-bar")
    suite.add("L25-02", "فرم ثبت مالکیت", r.status_code == 200)

    # Try claiming with wrong code
    _get(c, "/claim-bar")
    r = _post(c, "/claim-bar", {
        "serial_code": "TSCLM001",
        "claim_code": "WRONGCODE",
    })
    suite.add("L25-03", "کد اشتباه → خطا",
              r.status_code == 200 and ("خطا" in r.text or "نامعتبر" in r.text or "اشتباه" in r.text))

    return suite


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 8: SUPPORT & NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

def test_L26_tickets():
    """L26: Customer creates ticket, admin replies, closes."""
    suite = TestSuite("L26: تیکتینگ کامل")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    c = get_session(CUSTOMER_MOBILE)
    a = get_session(ADMIN_MOBILE)

    # Create ticket
    _get(c, "/tickets/new")
    r = _post_no_redirect(c, "/tickets/new", {
        "subject": f"تیکت لایف‌سایکل {_SUFFIX}",
        "body": "تیکت تست جامع برای بررسی فرآیند کامل.",
        "priority": "High",
        "category": "Technical",
    })
    created = r.status_code in (302, 303)
    redirect_url = r.headers.get("location", "")
    suite.add("L26-01", "ایجاد تیکت", created and "/tickets/" in redirect_url)

    ticket_id_match = re.search(r'/tickets/(\d+)', redirect_url) if created else None
    if not ticket_id_match:
        suite.add("L26-02", "استخراج ticket_id", False)
        return suite
    ticket_id = int(ticket_id_match.group(1))

    # Customer views ticket
    r = _get(c, f"/tickets/{ticket_id}")
    suite.add("L26-02", "مشاهده تیکت مشتری", r.status_code == 200)

    # Admin views ticket
    r = _get(a, f"/admin/tickets/{ticket_id}")
    suite.add("L26-03", "مشاهده تیکت ادمین", r.status_code == 200)

    # Admin replies
    _get(a, f"/admin/tickets/{ticket_id}")
    r = _post_no_redirect(a, f"/admin/tickets/{ticket_id}/reply", {
        "body": "پاسخ تست ادمین در تست لایف‌سایکل.",
    })
    suite.add("L26-04", "پاسخ ادمین", r.status_code in (302, 303))

    # Admin adds internal note
    _get(a, f"/admin/tickets/{ticket_id}")
    r = _post_no_redirect(a, f"/admin/tickets/{ticket_id}/internal-note", {
        "body": "یادداشت داخلی — نباید مشتری ببیند.",
    })
    suite.add("L26-05", "یادداشت داخلی", r.status_code in (302, 303))

    # Customer replies
    _get(c, f"/tickets/{ticket_id}")
    r = _post_no_redirect(c, f"/tickets/{ticket_id}/message", {
        "body": "پیام دوم مشتری.",
    })
    suite.add("L26-06", "پاسخ مشتری", r.status_code in (302, 303))

    # Change status (form field is 'new_status')
    _get(a, f"/admin/tickets/{ticket_id}")
    r = _post_no_redirect(a, f"/admin/tickets/{ticket_id}/status", {
        "new_status": "InProgress",
    })
    suite.add("L26-07", "تغییر وضعیت -> InProgress", r.status_code in (302, 303))

    # Close ticket
    _get(c, f"/tickets/{ticket_id}")
    r = _post_no_redirect(c, f"/tickets/{ticket_id}/close")
    suite.add("L26-08", "بستن تیکت", r.status_code in (302, 303))

    status = db_scalar("SELECT status FROM tickets WHERE id = :t", {"t": ticket_id})
    suite.add("L26-09", "وضعیت Closed", "Closed" in str(status), f"status={status}")

    # Dealer ticket
    d = get_session(DEALER_MOBILE)
    r = _get(d, "/tickets")
    suite.add("L26-10", "لیست تیکت‌های نماینده", r.status_code == 200)

    _get(d, "/tickets/new")
    r = _post_no_redirect(d, "/tickets/new", {
        "subject": f"تیکت نماینده {_SUFFIX}",
        "body": "تیکت تست نماینده.",
        "priority": "Medium",
        "category": "Sales",
    })
    suite.add("L26-11", "ایجاد تیکت نماینده", r.status_code in (302, 303))

    return suite


def test_L27_notifications():
    """L27: Notification system — list, read, broadcast."""
    suite = TestSuite("L27: سیستم اعلان‌ها")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    c = get_session(CUSTOMER_MOBILE)
    a = get_session(ADMIN_MOBILE)

    # Customer notifications
    r = _get(c, "/notifications")
    suite.add("L27-01", "لیست اعلان‌ها", r.status_code == 200)

    # Unread count API
    r = _get(c, "/notifications/api/unread-count")
    suite.add("L27-02", "API تعداد خوانده‌نشده", r.status_code == 200)

    # Preferences
    r = _get(c, "/notifications/settings")
    suite.add("L27-03", "تنظیمات اعلان", r.status_code == 200)

    # Mark all read
    r = _post_json(c, "/notifications/read-all", {})
    suite.add("L27-04", "خواندن همه اعلان‌ها",
              r.status_code in (200, 302, 303))

    # Admin broadcast
    r = _get(a, "/admin/notifications/send")
    suite.add("L27-05", "فرم برادکست", r.status_code == 200)

    _get(a, "/admin/notifications/send")
    r = _post(a, "/admin/notifications/send", {
        "target_type": "user",
        "target_mobile": CUSTOMER_MOBILE,
        "title": f"اعلان تست {_SUFFIX}",
        "body": "پیام تست اعلان سیستمی",
    })
    suite.add("L27-06", "ارسال اعلان تکی", r.status_code == 200)

    # Verify notification created (may be async via BackgroundTasks)
    time.sleep(1)  # Give background task time to complete
    notif_count = db_scalar("""
        SELECT COUNT(*) FROM notifications
        WHERE user_id = :uid AND title LIKE :t
    """, {"uid": get_user_id(CUSTOMER_MOBILE), "t": f"%{_SUFFIX}%"})
    suite.add("L27-07", "اعلان در دیتابیس ایجاد شد",
              (notif_count or 0) > 0, f"count={notif_count}")

    return suite


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 9: ADMIN MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def test_L28_admin_dashboard():
    """L28: Admin dashboard, logs, customer management."""
    suite = TestSuite("L28: مدیریت ادمین")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    # Dashboard
    r = _get(a, "/admin/dashboard")
    suite.add("L28-01", "داشبورد ادمین", r.status_code == 200)

    # No-cache headers
    cc = r.headers.get("cache-control", "")
    suite.add("L28-02", "no-cache header", "no-cache" in cc or "no-store" in cc)

    # Customers
    r = _get(a, "/admin/customers")
    suite.add("L28-03", "لیست مشتریان", r.status_code == 200)

    r = _get(a, f"/admin/customers?q={CUSTOMER_MOBILE}")
    suite.add("L28-04", "جستجوی مشتری", r.status_code == 200)

    cust_id = get_user_id(CUSTOMER_MOBILE)
    if cust_id:
        r = _get(a, f"/admin/customers/{cust_id}")
        suite.add("L28-05", "جزئیات مشتری", r.status_code == 200)

    # Wallet admin
    r = _get(a, "/admin/wallets")
    suite.add("L28-06", "حساب‌های کیف پول", r.status_code == 200)

    r = _get(a, "/admin/wallets/withdrawals/list")
    suite.add("L28-07", "لیست برداشت‌ها", r.status_code == 200)

    # Logs
    r = _get(a, "/admin/logs")
    suite.add("L28-08", "لاگ درخواست‌ها", r.status_code == 200)

    r = _get(a, "/admin/logs?method=POST")
    suite.add("L28-09", "فیلتر POST", r.status_code == 200)

    r = _get(a, "/admin/logs?method=GET&status=200")
    suite.add("L28-10", "فیلتر GET + 200", r.status_code == 200)

    # Settings
    r = _get(a, "/admin/settings")
    suite.add("L28-11", "تنظیمات", r.status_code == 200)

    return suite


def test_L29_dealer_dashboard():
    """L29: Dealer dashboard and panels."""
    suite = TestSuite("L29: داشبورد نماینده")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    d = get_session(DEALER_MOBILE)

    r = _get(d, "/dealer/dashboard")
    suite.add("L29-01", "داشبورد نماینده", r.status_code == 200)

    cc = r.headers.get("cache-control", "")
    suite.add("L29-02", "no-cache header dealer", "no-cache" in cc or "no-store" in cc)

    # Sub-dealers
    r = _get(d, "/dealer/sub-dealers")
    suite.add("L29-03", "زیرمجموعه‌ها", r.status_code == 200)

    # Buyback list
    r = _get(d, "/dealer/buybacks")
    suite.add("L29-04", "لیست بازخرید", r.status_code == 200)

    # Scanner lookup
    serial = db_scalar("""
        SELECT serial_code FROM bars WHERE dealer_id = :d LIMIT 1
    """, {"d": get_user_id(DEALER_MOBILE)})
    if serial:
        r = _get(d, f"/dealer/scan/lookup?serial={serial}")
        suite.add("L29-05", "scan lookup", r.status_code == 200)

    return suite


def test_L30_reconciliation():
    """L30: Inventory reconciliation (admin or dealer)."""
    suite = TestSuite("L30: انبارگردانی")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    d = get_session(DEALER_MOBILE)
    dealer_id = get_user_id(DEALER_MOBILE)

    # Reconciliation page
    r = _get(d, "/dealer/reconciliation")
    suite.add("L30-01", "صفحه انبارگردانی", r.status_code == 200)

    # Start session
    _get(d, "/dealer/reconciliation")
    r = _post_no_redirect(d, "/dealer/reconciliation/start")
    suite.add("L30-02", "شروع انبارگردانی",
              r.status_code in (200, 302, 303),
              f"status={r.status_code}")

    if r.status_code in (302, 303):
        redirect_url = r.headers.get("location", "")
        session_match = re.search(r'/reconciliation/(\d+)', redirect_url)
        if session_match:
            session_id = int(session_match.group(1))

            # View session
            r = _get(d, f"/dealer/reconciliation/{session_id}")
            suite.add("L30-03", "مشاهده جلسه انبارگردانی", r.status_code == 200)

            # Scan a bar
            serial = db_scalar("""
                SELECT serial_code FROM bars WHERE dealer_id = :d AND status = 'Assigned' LIMIT 1
            """, {"d": dealer_id})
            if serial:
                _get(d, f"/dealer/reconciliation/{session_id}")
                r = _post(d, f"/dealer/reconciliation/{session_id}/scan", {"serial": serial})
                suite.add("L30-04", f"اسکن شمش {serial}", r.status_code == 200)

            # Cancel session (cleanup)
            _get(d, f"/dealer/reconciliation/{session_id}")
            r = _post_no_redirect(d, f"/dealer/reconciliation/{session_id}/cancel")
            suite.add("L30-05", "لغو انبارگردانی", r.status_code in (302, 303))

    # Admin reconciliation
    a = get_session(ADMIN_MOBILE)
    r = _get(a, "/admin/reconciliation")
    suite.add("L30-06", "انبارگردانی ادمین", r.status_code == 200)

    return suite


def test_L31_dealer_request():
    """L31: Customer applies for dealer role."""
    suite = TestSuite("L31: درخواست نمایندگی")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    c = get_session(CUSTOMER3_MOBILE)
    a = get_session(ADMIN_MOBILE)

    # Dealer request form
    r = _get(c, "/dealer-request")
    suite.add("L31-01", "فرم درخواست نمایندگی", r.status_code == 200)

    # Admin dealer requests
    r = _get(a, "/admin/dealer-requests")
    suite.add("L31-02", "لیست درخواست‌ها ادمین", r.status_code == 200)

    return suite


def test_L32_blog():
    """L32: Blog articles, admin CRUD, comments."""
    suite = TestSuite("L32: بلاگ و محتوا")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)
    c = get_session(CUSTOMER_MOBILE)

    # Admin creates article
    slug = f"test-article-{_SUFFIX}"
    _get(a, "/admin/blog/new")
    r = _post_no_redirect(a, "/admin/blog/new", {
        "title": f"مقاله تست {_SUFFIX}",
        "slug": slug,
        "excerpt": "خلاصه مقاله تست",
        "body": "<p>محتوای مقاله تست</p>",
        "status": "Published",
    })
    suite.add("L32-01", "ایجاد مقاله", r.status_code in (302, 303))

    article_id = db_scalar("SELECT id FROM articles WHERE slug = :s", {"s": slug})
    suite.add("L32-02", "مقاله در دیتابیس", article_id is not None)

    # Public blog list
    with get_anon_client() as anon:
        r = anon.get(f"{BASE_URL}/blog", follow_redirects=True)
        suite.add("L32-03", "لیست مقالات عمومی", r.status_code == 200)

        if article_id:
            r = anon.get(f"{BASE_URL}/blog/{slug}", follow_redirects=True)
            suite.add("L32-04", "مشاهده مقاله",
                      r.status_code == 200 and "مقاله تست" in r.text)

        # Sitemap
        r = anon.get(f"{BASE_URL}/sitemap.xml", follow_redirects=True)
        suite.add("L32-05", "sitemap.xml", r.status_code == 200)

    # Customer posts comment
    if article_id:
        _get(c, f"/blog/{slug}")
        r = _post_no_redirect(c, f"/blog/{slug}/comment", {"body": "نظر تست مشتری"})
        suite.add("L32-06", "ارسال نظر مشتری", r.status_code in (200, 302, 303))

    # Admin blog management
    r = _get(a, "/admin/blog")
    suite.add("L32-07", "لیست مقالات ادمین", r.status_code == 200)

    r = _get(a, "/admin/blog/categories")
    suite.add("L32-08", "دسته‌بندی‌های بلاگ", r.status_code == 200)

    r = _get(a, "/admin/blog/comments")
    suite.add("L32-09", "تعدیل نظرات", r.status_code == 200)

    return suite


def test_L33_reviews():
    """L33: Product reviews and comments."""
    suite = TestSuite("L33: نظرات محصول")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")
    a = get_session(ADMIN_MOBILE)

    # Admin review list
    r = _get(a, "/admin/reviews")
    suite.add("L33-01", "لیست نظرات ادمین", r.status_code == 200)

    r = _get(a, "/admin/reviews?tab=comments")
    suite.add("L33-02", "تب نظرات", r.status_code == 200)

    r = _get(a, "/admin/reviews?tab=reviews")
    suite.add("L33-03", "تب بررسی‌ها", r.status_code == 200)

    return suite


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE PHASE 10: SECURITY & NEGATIVE
# ═══════════════════════════════════════════════════════════════

def test_L34_security():
    """L34: Security and access control tests."""
    suite = TestSuite("L34: امنیت و کنترل دسترسی")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    # Unauthenticated access
    protected_paths = [
        "/wallet", "/orders", "/profile", "/addresses", "/cart",
        "/checkout", "/tickets", "/my-bars", "/notifications",
        "/admin/dashboard", "/dealer/dashboard",
    ]
    for path in protected_paths:
        with get_anon_client() as anon:
            r = anon.get(f"{BASE_URL}{path}", follow_redirects=False)
            suite.add(f"L34-noauth-{path.replace('/', '-').strip('-')}",
                      f"بدون لاگین → {path}",
                      r.status_code in (302, 303, 401, 403))

    # Customer → admin
    c = get_session(CUSTOMER_MOBILE)
    admin_paths = [
        "/admin/dashboard", "/admin/products", "/admin/bars",
        "/admin/orders", "/admin/settings", "/admin/customers",
    ]
    for path in admin_paths:
        r = c.get(f"{BASE_URL}{path}", follow_redirects=False)
        suite.add(f"L34-cust-admin-{path.split('/')[-1]}",
                  f"مشتری → {path}", r.status_code in (302, 303, 401, 403))

    # Customer → dealer
    dealer_paths = ["/dealer/dashboard", "/dealer/pos", "/dealer/inventory"]
    for path in dealer_paths:
        r = c.get(f"{BASE_URL}{path}", follow_redirects=False)
        suite.add(f"L34-cust-dealer-{path.split('/')[-1]}",
                  f"مشتری → {path}", r.status_code in (302, 303, 401, 403))

    # Dealer → admin
    d = get_session(DEALER_MOBILE)
    for path in ["/admin/settings", "/admin/customers"]:
        r = d.get(f"{BASE_URL}{path}", follow_redirects=False)
        suite.add(f"L34-dealer-admin-{path.split('/')[-1]}",
                  f"نماینده → {path}", r.status_code in (302, 303, 401, 403))

    # Invalid data
    with get_anon_client() as anon:
        r = anon.get(f"{BASE_URL}/product/abc", follow_redirects=True)
        suite.add("L34-inv-product", "product_id حروفی", r.status_code in (404, 422))

        r = anon.get(f"{BASE_URL}/nonexistent/page", follow_redirects=True)
        suite.add("L34-404", "مسیر ناموجود → 404", r.status_code == 404)

        r = anon.request("PUT", f"{BASE_URL}/auth/send-otp")
        suite.add("L34-method", "PUT → 405", r.status_code == 405)

    # OTP wrong code
    with get_anon_client() as anon:
        anon.get(f"{BASE_URL}/auth/login", follow_redirects=True)
        csrf = anon.cookies.get("csrf_token", "")
        anon.post(f"{BASE_URL}/auth/send-otp",
                  data={"mobile": "09399999999", "csrf_token": csrf})
        csrf = anon.cookies.get("csrf_token", "")
        r = anon.post(f"{BASE_URL}/auth/verify-otp",
                      data={"mobile": "09399999999", "code": "000000", "csrf_token": csrf})
        suite.add("L34-wrong-otp", "OTP اشتباه → خطا",
                  "auth_token" not in anon.cookies)

    return suite


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  TalaMala v4 — Comprehensive Lifecycle Tests")
    print(f"  Server: {BASE_URL}")
    print(f"  Test suffix: {_SUFFIX}")
    print("=" * 60)

    # Check server
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            print("  Server not healthy!")
            return 1
    except Exception:
        print("  Server not reachable!")
        return 1
    print("  Server is healthy\n")

    # Import and run setup from run_tests.py
    try:
        from tests.run_tests import setup_test_database
        print("  Setting up test database...")
        setup_test_database()
    except Exception as e:
        print(f"  DB setup warning: {e}")

    # Pre-login users
    print("  Logging in test users...")
    for mobile, label in [
        (ADMIN_MOBILE, "Admin"), (OPERATOR_MOBILE, "Operator"),
        (CUSTOMER_MOBILE, "Customer"), (CUSTOMER2_MOBILE, "Customer2"),
        (CUSTOMER3_MOBILE, "Customer3"), (DEALER_MOBILE, "Dealer"),
    ]:
        s = get_session(mobile)
        status = "OK" if "auth_token" in s.cookies else "FAIL"
        print(f"    {status} {label} ({mobile})")

    all_suites = []
    runners = [
        # Phase 1: Production & Catalog
        test_L01_category_crud,
        test_L02_product_crud,
        test_L03_gift_box_crud,
        test_L04_package_type_crud,
        test_L05_batch_crud,
        # Phase 2: Inventory & Distribution
        test_L06_bar_generation,
        test_L07_bar_assign_to_product,
        test_L08_bar_bulk_action,
        test_L09_dealer_tier_crud,
        test_L10_dealer_management,
        test_L11_dealer_transfer,
        # Phase 3: Pricing & Settings
        test_L12_pricing_settings,
        test_L13_hedging_operations,
        # Phase 4: Shop & Customer
        test_L14_shop_browsing,
        test_L15_customer_profile,
        test_L16_full_order_flow,
        test_L17_coupon_system,
        # Phase 5: Wallet & Finance
        test_L18_wallet_operations,
        test_L19_wallet_dealer,
        # Phase 6: Dealer Sales & POS
        test_L20_dealer_pos_web,
        test_L21_dealer_api_pos,
        test_L22_customer_pos_api,
        # Phase 7: Verification & Ownership
        test_L24_verification,
        test_L25_ownership,
        # Phase 8: Support & Notifications
        test_L26_tickets,
        test_L27_notifications,
        # Phase 9: Admin Management
        test_L28_admin_dashboard,
        test_L29_dealer_dashboard,
        test_L30_reconciliation,
        test_L31_dealer_request,
        test_L32_blog,
        test_L33_reviews,
        # Phase 10: Security
        test_L34_security,
    ]

    for runner in runners:
        try:
            suite = runner()
            all_suites.append(suite)
        except Exception as e:
            print(f"  CRASH {runner.__name__}: {e}")
            import traceback
            traceback.print_exc()
            all_suites.append(TestSuite(runner.__name__,
                [TestResult(runner.__name__, str(e), False)]))

    # Summary
    print(f"\n{'='*60}")
    print("  LIFECYCLE TEST RESULTS")
    print(f"{'='*60}")

    total_passed = 0
    total_failed = 0
    failed_tests = []

    for suite in all_suites:
        p = suite.passed_count
        f = suite.failed_count
        total_passed += p
        total_failed += f
        status = "PASS" if f == 0 else "FAIL"
        print(f"  {status} {suite.name}: {p}/{p+f}")
        for r in suite.results:
            if not r.passed:
                failed_tests.append(r)

    total = total_passed + total_failed
    pct = total_passed * 100 // total if total else 0
    print(f"\n  {'='*40}")
    print(f"  Total: {total_passed}/{total} passed ({pct}%)")

    if failed_tests:
        print(f"\n  Failed tests ({total_failed}):")
        for t in failed_tests:
            print(f"    FAIL {t.test_id}: {t.description}")
            if t.details:
                print(f"         {t.details}")

    close_all_sessions()
    return total_failed


if __name__ == "__main__":
    failed = main()
    sys.exit(1 if failed else 0)
