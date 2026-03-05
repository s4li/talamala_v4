#!/usr/bin/env python3
"""
TalaMala v4 — Automated Test Runner
Runs against a live server at BASE_URL using httpx.
Uses a session pool so each user logs in ONLY ONCE (avoids OTP rate limits).
Auto-sets up test accounts in DB before running (roles, wallets, API keys).
"""
import httpx
import json
import sys
import os
import re
import time
from dataclasses import dataclass, field

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000"
OTP_CODE = "111111"

# Test accounts
ADMIN_MOBILE = "09123456789"
OPERATOR_MOBILE = "09121111111"
CUSTOMER_MOBILE = "09351234567"  # U3 - has wallet balance
CUSTOMER2_MOBILE = "09359876543"  # U4 - no balance
CUSTOMER3_MOBILE = "09131112233"  # U5
DEALER_MOBILE = "09161234567"  # D1 - Esfahan (is_warehouse)
DEALER2_MOBILE = "09171234567"  # D2 - Shiraz
DEALER_API_KEY = "test_esfahan_key_0000000000000000"
DEALER2_API_KEY = "test_shiraz__key_1111111111111111"


def setup_test_database():
    """Ensure test accounts have proper roles, wallets, and API keys."""
    from sqlalchemy import text
    from config.database import engine

    with engine.begin() as conn:
        # 1. Set admin role
        conn.execute(text("""
            UPDATE users SET is_admin = true, admin_role = 'admin',
                first_name = 'ادمین', last_name = 'سیستم'
            WHERE mobile = :m
        """), {"m": ADMIN_MOBILE})

        # 2. Set operator role
        conn.execute(text("""
            UPDATE users SET is_admin = true, admin_role = 'operator',
                first_name = 'اپراتور', last_name = 'تست'
            WHERE mobile = :m
        """), {"m": OPERATOR_MOBILE})

        # 3. Set customer names
        conn.execute(text("""
            UPDATE users SET first_name = 'علی', last_name = 'مشتری'
            WHERE mobile = :m AND first_name = 'کاربر'
        """), {"m": CUSTOMER_MOBILE})

        # 4. Set dealer D1 (Esfahan, warehouse)
        conn.execute(text("""
            UPDATE users SET is_dealer = true, tier_id = 1,
                first_name = 'نماینده', last_name = 'اصفهان',
                api_key = :key, is_warehouse = true
            WHERE mobile = :m
        """), {"m": DEALER_MOBILE, "key": DEALER_API_KEY})

        # 5. Create dealer D2 if missing
        r = conn.execute(text("SELECT id FROM users WHERE mobile = :m"), {"m": DEALER2_MOBILE})
        if not r.fetchone():
            conn.execute(text("""
                INSERT INTO users (mobile, first_name, last_name, national_id,
                    is_dealer, tier_id, api_key, is_active)
                VALUES (:m, 'نماینده', 'شیراز', :nid, true, 2, :key, true)
            """), {"m": DEALER2_MOBILE, "nid": f"DEALER_{DEALER2_MOBILE}",
                   "key": DEALER2_API_KEY})
        else:
            conn.execute(text("""
                UPDATE users SET is_dealer = true, tier_id = 2,
                    first_name = 'نماینده', last_name = 'شیراز',
                    api_key = :key
                WHERE mobile = :m
            """), {"m": DEALER2_MOBILE, "key": DEALER2_API_KEY})

        # 6. Create wallet accounts for customer U3 (IRR with 10M toman = 100M rial)
        r = conn.execute(text("""
            SELECT id FROM users WHERE mobile = :m
        """), {"m": CUSTOMER_MOBILE})
        cust_row = r.fetchone()
        if cust_row:
            cust_id = cust_row[0]
            for asset in ['IRR', 'XAU_MG', 'XAG_MG']:
                r2 = conn.execute(text("""
                    SELECT id FROM accounts WHERE user_id = :uid AND asset_code = :ac
                """), {"uid": cust_id, "ac": asset})
                if not r2.fetchone():
                    bal = 100_000_000 if asset == 'IRR' else 0
                    conn.execute(text("""
                        INSERT INTO accounts (user_id, asset_code, balance, locked_balance, credit_balance)
                        VALUES (:uid, :ac, :bal, 0, 0)
                    """), {"uid": cust_id, "ac": asset, "bal": bal})

        # 7. Clear OTP rate limits by resetting otp_code/expiry
        conn.execute(text("""
            UPDATE users SET otp_code = NULL, otp_expiry = NULL
            WHERE mobile IN (:m1, :m2, :m3, :m4, :m5, :m6, :m7)
        """), {"m1": ADMIN_MOBILE, "m2": OPERATOR_MOBILE, "m3": CUSTOMER_MOBILE,
               "m4": CUSTOMER2_MOBILE, "m5": CUSTOMER3_MOBILE,
               "m6": DEALER_MOBILE, "m7": DEALER2_MOBILE})

    print("  ✅ Test database setup complete")


# ─── Session Pool ────────────────────────────────────────────
# One httpx.Client per user, logged in once, reused across all tests.
_sessions: dict[str, httpx.Client] = {}


def get_session(mobile: str) -> httpx.Client:
    """Get or create a logged-in session for the given mobile number."""
    if mobile in _sessions:
        return _sessions[mobile]

    c = httpx.Client(timeout=30)
    # 1. GET login page → CSRF cookie
    c.get(f"{BASE_URL}/auth/login", follow_redirects=True)
    csrf = c.cookies.get("csrf_token", "")

    # 2. Send OTP
    c.post(f"{BASE_URL}/auth/send-otp",
           data={"mobile": mobile, "csrf_token": csrf})
    csrf = c.cookies.get("csrf_token", "")

    # 3. Verify OTP (DON'T follow redirect — capture auth_token Set-Cookie)
    r = c.post(f"{BASE_URL}/auth/verify-otp",
               data={"mobile": mobile, "code": OTP_CODE, "csrf_token": csrf})

    if "auth_token" not in c.cookies:
        print(f"    ⚠️  LOGIN FAILED for {mobile} (status={r.status_code})")
        # Try to extract error
        m = re.search(r'alert[^>]*>(.*?)</div', r.text, re.DOTALL)
        if m:
            print(f"       Error: {m.group(1).strip()[:80]}")

    _sessions[mobile] = c
    return c


def get_anon_client() -> httpx.Client:
    """Get an anonymous (not logged in) client."""
    return httpx.Client(timeout=30)


def get_csrf(client: httpx.Client) -> str:
    """Get CSRF token from client cookies."""
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
        status = "✅" if passed else "❌"
        msg = f"  {status} {test_id}: {description}"
        if details and not passed:
            msg += f" — {details}"
        print(msg)

    @property
    def passed_count(self):
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self):
        return sum(1 for r in self.results if not r.passed)


def _get(client, path, **kw):
    """GET with follow_redirects=True by default."""
    return client.get(f"{BASE_URL}{path}", follow_redirects=True, **kw)


def _post(client, path, data=None, **kw):
    """POST — auto-adds CSRF token from cookies to form data."""
    if data is None:
        data = {}
    csrf = client.cookies.get("csrf_token", "")
    if csrf and "csrf_token" not in data:
        data["csrf_token"] = csrf
    return client.post(f"{BASE_URL}{path}", data=data, follow_redirects=True, **kw)


# ─── Test Suites ─────────────────────────────────────────────

def run_ts01_auth():
    suite = TestSuite("TS-01: احراز هویت (Auth)")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    # TS-01-01: Login page
    with get_anon_client() as c:
        r = c.get(f"{BASE_URL}/auth/login", follow_redirects=True)
        suite.add("TS-01-01", "صفحه لاگین باز شود",
                  r.status_code == 200 and ("موبایل" in r.text or "mobile" in r.text.lower()))

    # TS-01-02/03: Admin login
    c = get_session(ADMIN_MOBILE)
    suite.add("TS-01-02", "OTP ادمین ارسال شود", "auth_token" in c.cookies)
    suite.add("TS-01-03", "لاگین ادمین موفق", "auth_token" in c.cookies)
    # Verify admin can access dashboard
    r = _get(c, "/admin/dashboard")
    suite.add("TS-01-03b", "ادمین → dashboard 200", r.status_code == 200)

    # TS-01-04/05: Customer login
    c = get_session(CUSTOMER_MOBILE)
    suite.add("TS-01-04", "OTP مشتری ارسال شود", "auth_token" in c.cookies)
    suite.add("TS-01-05", "لاگین مشتری موفق", "auth_token" in c.cookies)

    # TS-01-06: Dealer login
    c = get_session(DEALER_MOBILE)
    suite.add("TS-01-06", "لاگین نماینده موفق", "auth_token" in c.cookies)

    # TS-01-07: Operator login
    c = get_session(OPERATOR_MOBILE)
    suite.add("TS-01-07", "لاگین اپراتور موفق", "auth_token" in c.cookies)

    # TS-01-10: Wrong OTP
    with get_anon_client() as c:
        c.get(f"{BASE_URL}/auth/login", follow_redirects=True)
        csrf = get_csrf(c)
        c.post(f"{BASE_URL}/auth/send-otp", data={"mobile": "09399999999", "csrf_token": csrf})
        csrf = get_csrf(c)
        r = c.post(f"{BASE_URL}/auth/verify-otp",
                   data={"mobile": "09399999999", "code": "000000", "csrf_token": csrf})
        suite.add("TS-01-10", "OTP اشتباه → خطا", "auth_token" not in c.cookies)

    # TS-01-11: Invalid mobile (short)
    with get_anon_client() as c:
        c.get(f"{BASE_URL}/auth/login", follow_redirects=True)
        csrf = get_csrf(c)
        r = c.post(f"{BASE_URL}/auth/send-otp",
                   data={"mobile": "1234", "csrf_token": csrf}, follow_redirects=True)
        suite.add("TS-01-11", "موبایل کوتاه → خطا", "auth_token" not in c.cookies)

    # TS-01-21: Access without login
    with get_anon_client() as c:
        r = c.get(f"{BASE_URL}/wallet", follow_redirects=False)
        suite.add("TS-01-21", "wallet بدون لاگین → redirect", r.status_code in (302, 303, 401))

    # TS-01-22: Customer → admin
    c = get_session(CUSTOMER_MOBILE)
    r = c.get(f"{BASE_URL}/admin/dashboard", follow_redirects=False)
    suite.add("TS-01-22", "مشتری → admin → 401", r.status_code in (302, 303, 401, 403))

    # TS-01-23: Customer → dealer
    r = c.get(f"{BASE_URL}/dealer/dashboard", follow_redirects=False)
    suite.add("TS-01-23", "مشتری → dealer → 401", r.status_code in (302, 303, 401, 403))

    return suite


def run_ts02_shop():
    suite = TestSuite("TS-02: فروشگاه (Shop)")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    with get_anon_client() as c:
        r = c.get(f"{BASE_URL}/", follow_redirects=True)
        suite.add("TS-02-01", "صفحه اصلی", r.status_code == 200 and len(r.text) > 500)

        r = c.get(f"{BASE_URL}/?category=1", follow_redirects=True)
        suite.add("TS-02-02", "فیلتر دسته‌بندی", r.status_code == 200)

        r = c.get(f"{BASE_URL}/?sort=price_asc", follow_redirects=True)
        suite.add("TS-02-04", "مرتب‌سازی ارزان‌ترین", r.status_code == 200)

        r = c.get(f"{BASE_URL}/?sort=price_desc", follow_redirects=True)
        suite.add("TS-02-05", "مرتب‌سازی گران‌ترین", r.status_code == 200)

        r = c.get(f"{BASE_URL}/product/1", follow_redirects=True)
        suite.add("TS-02-07", "جزئیات محصول", r.status_code == 200 and ("وزن" in r.text or "قیمت" in r.text))

        r = c.get(f"{BASE_URL}/product/99999", follow_redirects=True)
        suite.add("TS-02-18", "product_id نامعتبر → 404", r.status_code == 404)

    return suite


def run_ts03_cart():
    suite = TestSuite("TS-03: سبد خرید (Cart)")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(CUSTOMER_MOBILE)

    # Use form-based endpoint with "increase" action (adds or increases)
    r = _post(c, "/cart/update", {"product_id": "1", "action": "increase"})
    suite.add("TS-03-01", "افزودن به سبد", r.status_code == 200)

    r = _get(c, "/cart")
    suite.add("TS-03-03", "مشاهده سبد", r.status_code == 200)

    r = _post(c, "/cart/update", {"product_id": "1", "action": "increase"})
    suite.add("TS-03-04", "افزایش تعداد", r.status_code == 200)

    # Use API endpoint for AJAX-style cart update
    csrf = get_csrf(c)
    r = c.post(f"{BASE_URL}/api/cart/update",
               json={"product_id": 1, "change": -1},
               headers={"X-CSRF-Token": csrf})
    suite.add("TS-03-05", "کاهش تعداد (API)", r.status_code == 200)

    r = _post(c, "/cart/update", {"product_id": "1", "action": "remove"})
    suite.add("TS-03-06", "حذف از سبد", r.status_code == 200)

    # Add without login
    with get_anon_client() as anon:
        r = anon.post(f"{BASE_URL}/cart/update", data={"product_id": "1", "action": "increase"},
                      follow_redirects=False)
        suite.add("TS-03-08", "افزودن بدون لاگین → redirect", r.status_code in (302, 303, 401))

    return suite


def run_ts04_checkout():
    suite = TestSuite("TS-04: ثبت سفارش (Checkout)")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(CUSTOMER_MOBILE)

    # Add item to cart
    _post(c, "/cart/update", {"product_id": "1", "action": "add"})

    r = _get(c, "/checkout")
    suite.add("TS-04-01", "صفحه چک‌اوت", r.status_code == 200)

    r = _get(c, "/orders")
    suite.add("TS-04-25", "لیست سفارشات", r.status_code == 200)

    # Coupon AJAX check
    r = _get(c, "/api/coupon/check?code=WELCOME10")
    suite.add("TS-04-12", "بررسی کوپن AJAX", r.status_code == 200)

    r = _get(c, "/api/coupon/check?code=INVALID123")
    suite.add("TS-04-13", "کوپن نامعتبر", r.status_code in (200, 400))

    # Delivery locations AJAX
    r = _get(c, "/api/delivery/locations?province=1")
    suite.add("TS-04-04", "AJAX لود نمایندگان", r.status_code == 200)

    return suite


def run_ts05_payment():
    suite = TestSuite("TS-05: پرداخت (Payment)")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    # Pay someone else's order (should fail with error or redirect)
    c = get_session(CUSTOMER2_MOBILE)
    r = _post(c, "/payment/1/wallet")
    # Should NOT succeed — either 403, or page with error, or redirect
    suite.add("TS-05-09", "پرداخت سفارش دیگری → خطا",
              r.status_code in (200, 302, 403, 404) and
              ("خطا" in r.text or "اجازه" in r.text or r.status_code in (403, 404) or "auth" in str(r.url)))

    return suite


def run_ts06_wallet():
    suite = TestSuite("TS-06: کیف پول (Wallet)")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(CUSTOMER_MOBILE)

    r = _get(c, "/wallet")
    suite.add("TS-06-01", "داشبورد کیف پول مشتری", r.status_code == 200 and ("موجودی" in r.text or "کیف" in r.text))

    d = get_session(DEALER_MOBILE)
    r = _get(d, "/wallet")
    suite.add("TS-06-02", "داشبورد کیف پول نماینده", r.status_code == 200)

    r = _get(c, "/wallet/transactions")
    suite.add("TS-06-03", "تاریخچه تراکنش‌ها", r.status_code == 200)

    r = _get(c, "/wallet/transactions?asset=irr")
    suite.add("TS-06-04", "فیلتر IRR", r.status_code == 200)

    r = _get(c, "/wallet/transactions?asset=gold")
    suite.add("TS-06-05", "فیلتر طلا", r.status_code == 200)

    r = _get(c, "/wallet/withdraw")
    suite.add("TS-06-11", "صفحه برداشت", r.status_code == 200)

    r = _get(c, "/wallet/gold")
    suite.add("TS-06-16", "صفحه خرید/فروش طلا", r.status_code == 200)

    r = _get(c, "/wallet/silver")
    suite.add("TS-06-20", "صفحه خرید/فروش نقره", r.status_code == 200)

    r = c.get(f"{BASE_URL}/wallet/platinum", follow_redirects=False)
    suite.add("TS-06-27", "asset_type نامعتبر → redirect to /wallet",
              r.status_code in (302, 303, 404, 422))

    return suite


def run_ts07_coupon():
    suite = TestSuite("TS-07: کوپن (Coupon)")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(CUSTOMER_MOBILE)

    for code, tid, desc in [
        ("WELCOME10", "TS-07-01", "کوپن WELCOME10"),
        ("CASHBACK5", "TS-07-02", "کوپن CASHBACK5"),
        ("FIXED500", "TS-07-03", "کوپن FIXED500"),
    ]:
        r = _get(c, f"/api/coupon/check?code={code}")
        suite.add(tid, desc, r.status_code == 200)

    r = _get(c, "/api/coupon/check?code=")
    suite.add("TS-07-17", "کد کوپن خالی", r.status_code in (200, 400))

    return suite


def run_ts08_admin_catalog():
    suite = TestSuite("TS-08: پنل مدیریت — کاتالوگ")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(ADMIN_MOBILE)

    for path, tid, desc in [
        ("/admin/products", "TS-08-01", "لیست محصولات"),
        ("/admin/designs", "TS-08-12", "لیست طرح کارت‌ها"),
        ("/admin/packages", "TS-08-16", "لیست بسته‌بندی‌ها"),
        ("/admin/batches", "TS-08-20", "لیست بچ‌ها"),
    ]:
        r = _get(c, path)
        suite.add(tid, desc, r.status_code == 200)

    return suite


def run_ts09_admin_orders():
    suite = TestSuite("TS-09: پنل مدیریت — سفارشات")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(ADMIN_MOBILE)
    r = _get(c, "/admin/orders")
    suite.add("TS-09-01", "لیست سفارشات", r.status_code == 200)

    r = _get(c, "/admin/orders?status=Pending")
    suite.add("TS-09-02", "فیلتر Pending", r.status_code == 200)

    return suite


def run_ts10_admin_bars():
    suite = TestSuite("TS-10: پنل مدیریت — شمش‌ها")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(ADMIN_MOBILE)

    r = _get(c, "/admin/bars")
    suite.add("TS-10-01", "لیست شمش‌ها", r.status_code == 200)

    r = _get(c, "/admin/bars?status=ASSIGNED")
    suite.add("TS-10-02", "فیلتر ASSIGNED", r.status_code == 200)

    r = _get(c, "/api/admin/bars/lookup?serial=TSCLM001")
    suite.add("TS-10-12", "lookup API معتبر", r.status_code == 200)

    r = _get(c, "/api/admin/bars/lookup?serial=INVALIDXYZ")
    suite.add("TS-10-13", "lookup نامعتبر", r.status_code in (200, 404))

    return suite


def run_ts11_dealer_pos():
    suite = TestSuite("TS-11: نمایندگان — POS و فروش")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(DEALER_MOBILE)

    r = _get(c, "/dealer/pos")
    suite.add("TS-11-01", "فرم POS فروش", r.status_code == 200, f"status={r.status_code}")

    r = _get(c, "/dealer/sales")
    suite.add("TS-11-08", "تاریخچه فروش", r.status_code == 200, f"status={r.status_code}")

    r = _get(c, "/dealer/inventory")
    suite.add("TS-11-09", "موجودی نماینده", r.status_code == 200, f"status={r.status_code}")

    r = _get(c, "/dealer/scan/lookup?serial=TSCLM001")
    suite.add("TS-11-10", "scan lookup", r.status_code == 200, f"status={r.status_code}")

    return suite


def run_ts12_to_ts15():
    suite = TestSuite("TS-12~15: بازخرید/B2B/زیرمجموعه/توزیع")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    d = get_session(DEALER_MOBILE)
    a = get_session(ADMIN_MOBILE)

    for path, tid, desc, client in [
        ("/dealer/buybacks", "TS-12-04", "لیست بازخریدها", d),
        ("/admin/dealers/buybacks", "TS-12-05", "بازخریدها (ادمین)", a),
        ("/dealer/b2b-orders", "TS-13-01", "لیست B2B", d),
        ("/dealer/b2b-orders/new", "TS-13-02", "سفارش B2B جدید", d),
        ("/admin/dealers/b2b-orders", "TS-13-07", "B2B ادمین", a),
        ("/dealer/sub-dealers", "TS-14-01", "زیرمجموعه‌ها", d),
        ("/dealer/transfers", "TS-15-01", "صفحه توزیع", d),
        ("/dealer/transfers?tab=history", "TS-15-04", "تاریخچه انتقال", d),
    ]:
        r = _get(client, path)
        suite.add(tid, desc, r.status_code == 200, f"status={r.status_code}")

    return suite


def run_ts16_verification():
    suite = TestSuite("TS-16: احراز اصالت و QR")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    with get_anon_client() as c:
        r = c.get(f"{BASE_URL}/verify", follow_redirects=True)
        suite.add("TS-16-01", "صفحه احراز اصالت", r.status_code == 200)

        r = c.get(f"{BASE_URL}/verify/check?code=TSCLM001", follow_redirects=True)
        suite.add("TS-16-02", "سریال معتبر", r.status_code == 200)

        r = c.get(f"{BASE_URL}/verify/check?code=FAKE123", follow_redirects=True)
        suite.add("TS-16-03", "سریال نامعتبر", r.status_code in (200, 404))

        r = c.get(f"{BASE_URL}/verify/api/check?code=TSCLM001", follow_redirects=True)
        suite.add("TS-16-04", "API بررسی", r.status_code == 200)

    return suite


def run_ts17_profile():
    suite = TestSuite("TS-17: پروفایل و آدرس")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(CUSTOMER_MOBILE)

    r = _get(c, "/profile")
    suite.add("TS-17-01", "مشاهده پروفایل", r.status_code == 200)

    r = _get(c, "/addresses")
    suite.add("TS-17-05", "لیست آدرس‌ها", r.status_code == 200)

    r = _get(c, "/api/geo/cities?province_id=1")
    suite.add("TS-17-11", "API شهرها", r.status_code == 200)

    r = _get(c, "/api/geo/districts?city_id=1")
    suite.add("TS-17-12", "API محله‌ها", r.status_code == 200)

    r = _get(c, "/api/geo/dealers?province_id=1")
    suite.add("TS-17-13", "API نمایندگان", r.status_code == 200)

    r = _get(c, "/invite")
    suite.add("TS-17-10", "صفحه دعوت", r.status_code == 200)

    return suite


def run_ts18_admin_customers():
    suite = TestSuite("TS-18: مدیریت کاربران ادمین")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(ADMIN_MOBILE)

    r = _get(c, "/admin/customers")
    suite.add("TS-18-01", "لیست مشتریان", r.status_code == 200)

    r = _get(c, "/admin/customers?q=09351234567")
    suite.add("TS-18-02", "جستجو با موبایل", r.status_code == 200)

    r = _get(c, "/admin/customers/create")
    suite.add("TS-18-05", "فرم ایجاد مشتری", r.status_code == 200)

    return suite


def run_ts19_tickets():
    suite = TestSuite("TS-19: تیکتینگ / پشتیبانی")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(CUSTOMER_MOBILE)
    r = _get(c, "/tickets")
    suite.add("TS-19-01", "لیست تیکت‌ها مشتری", r.status_code == 200)

    r = _get(c, "/tickets/new")
    suite.add("TS-19-02", "فرم ایجاد تیکت", r.status_code == 200)

    d = get_session(DEALER_MOBILE)
    r = _get(d, "/tickets")
    suite.add("TS-19-07", "لیست تیکت‌ها نماینده", r.status_code == 200)

    a = get_session(ADMIN_MOBILE)
    r = _get(a, "/admin/tickets")
    suite.add("TS-19-09", "لیست تیکت‌ها ادمین", r.status_code == 200)

    r = _get(a, "/admin/tickets?status=Open")
    suite.add("TS-19-10", "فیلتر Open", r.status_code == 200)

    return suite


def run_ts20_dealer_api():
    suite = TestSuite("TS-20: POS REST API نماینده")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    headers = {"X-API-Key": DEALER_API_KEY}
    with get_anon_client() as c:
        r = c.get(f"{BASE_URL}/api/dealer/info", headers=headers)
        suite.add("TS-20-01", "GET /api/dealer/info", r.status_code == 200)

        r = c.get(f"{BASE_URL}/api/dealer/info", headers={"X-API-Key": "invalid_key"})
        suite.add("TS-20-02", "API Key نامعتبر → 401", r.status_code in (401, 403))

        r = c.get(f"{BASE_URL}/api/dealer/info")
        suite.add("TS-20-03", "بدون API Key → 401", r.status_code in (401, 403, 422))

        r = c.get(f"{BASE_URL}/api/dealer/products", headers=headers)
        suite.add("TS-20-04", "لیست محصولات API", r.status_code == 200)

        r = c.get(f"{BASE_URL}/api/dealer/sales", headers=headers)
        suite.add("TS-20-07", "تاریخچه فروش API", r.status_code == 200)

    return suite


def run_ts22_ownership():
    suite = TestSuite("TS-22: ثبت مالکیت و انتقال")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(CUSTOMER_MOBILE)
    r = _get(c, "/my-bars")
    suite.add("TS-22-01", "لیست شمش‌های من", r.status_code == 200)

    r = _get(c, "/claim-bar")
    suite.add("TS-22-02", "فرم ثبت مالکیت", r.status_code == 200)

    return suite


def run_ts23_custodial():
    suite = TestSuite("TS-23: تحویل فیزیکی و طلای امانی")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    d = get_session(DEALER_MOBILE)
    r = _get(d, "/dealer/deliveries")
    suite.add("TS-23-08", "لیست تحویل‌ها نماینده", r.status_code == 200)

    return suite


def run_ts26_dealer_request():
    suite = TestSuite("TS-26: درخواست نمایندگی")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    c = get_session(CUSTOMER3_MOBILE)
    r = _get(c, "/dealer-request")
    suite.add("TS-26-01", "فرم درخواست نمایندگی", r.status_code == 200)

    a = get_session(ADMIN_MOBILE)
    r = _get(a, "/admin/dealer-requests")
    suite.add("TS-26-08", "لیست درخواست‌ها ادمین", r.status_code == 200)

    return suite


def run_ts27_reviews():
    suite = TestSuite("TS-27: نظرات و پرسش‌وپاسخ")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    a = get_session(ADMIN_MOBILE)
    r = _get(a, "/admin/reviews")
    suite.add("TS-27-10", "لیست نظرات ادمین", r.status_code == 200)

    return suite


def run_ts28_to_ts34():
    suite = TestSuite("TS-28~34: Rasis/Pricing/Reconciliation/Trade/Notifications/Hedging/Blog")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    a = get_session(ADMIN_MOBILE)
    d = get_session(DEALER_MOBILE)
    c = get_session(CUSTOMER_MOBILE)

    tests = [
        ("/admin/rasis", "TS-28-01", "صفحه راسیس", a),
        ("/dealer/reconciliation", "TS-30-01", "انبارگردانی نماینده", d),
        ("/admin/reconciliation", "TS-30-09", "انبارگردانی ادمین", a),
        ("/notifications", "TS-32-01", "لیست اعلان‌ها", c),
        ("/notifications/api/unread-count", "TS-32-04", "badge خوانده‌نشده", c),
        ("/notifications/settings", "TS-32-05", "تنظیمات اعلان", c),
        ("/admin/notifications/send", "TS-32-09", "فرم برادکست", a),
        ("/admin/hedging", "TS-33-01", "داشبورد هجینگ", a),
        ("/admin/hedging/ledger", "TS-33-07", "ledger کامل", a),
        ("/admin/hedging/record", "TS-33-04", "فرم ثبت hedge", a),
        ("/admin/hedging/adjust", "TS-33-06", "فرم تنظیم موجودی", a),
        ("/admin/hedging/api/position", "TS-33-10", "API position", a),
    ]
    for path, tid, desc, client in tests:
        r = _get(client, path)
        suite.add(tid, desc, r.status_code == 200, f"status={r.status_code}")

    # Blog (public)
    with get_anon_client() as anon:
        r = anon.get(f"{BASE_URL}/blog", follow_redirects=True)
        suite.add("TS-34-01", "لیست مقالات عمومی", r.status_code == 200)

        r = anon.get(f"{BASE_URL}/sitemap.xml", follow_redirects=True)
        suite.add("TS-34-10", "sitemap.xml", r.status_code == 200)

    # Blog admin
    blog_admin = [
        ("/admin/blog", "TS-34-16", "لیست مقالات ادمین"),
        ("/admin/blog/new", "TS-34-17", "فرم ایجاد مقاله"),
        ("/admin/blog/categories", "TS-34-21", "دسته‌بندی بلاگ"),
        ("/admin/blog/comments", "TS-34-27", "کامنت‌ها ادمین"),
    ]
    for path, tid, desc in blog_admin:
        r = _get(a, path)
        suite.add(tid, desc, r.status_code == 200, f"status={r.status_code}")

    return suite


def run_ts35_to_ts40():
    suite = TestSuite("TS-35~40: Staff/Tiers/Dashboard/Log/Settings")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    a = get_session(ADMIN_MOBILE)
    d = get_session(DEALER_MOBILE)

    tests = [
        ("/admin/dealers", "TS-35-01", "لیست نمایندگان", a),
        ("/admin/dealers/tiers/list", "TS-36-01", "لیست تیرها", a),
        ("/admin/dealers/tiers/new", "TS-36-02", "فرم تیر جدید", a),
        ("/admin/dealers/sales", "TS-35-02", "گزارش فروش نمایندگان", a),
        ("/admin/dashboard", "TS-37-01", "داشبورد ادمین", a),
        ("/dealer/dashboard", "TS-38-01", "داشبورد نماینده", d),
        ("/admin/logs", "TS-39-01", "لیست لاگ‌ها", a),
        ("/admin/logs?method=POST", "TS-39-02", "فیلتر POST", a),
        ("/admin/settings", "TS-40-01", "صفحه تنظیمات", a),
    ]
    for path, tid, desc, client in tests:
        r = _get(client, path)
        suite.add(tid, desc, r.status_code == 200, f"status={r.status_code}")

    # No-cache headers
    r = a.get(f"{BASE_URL}/admin/dashboard", follow_redirects=True)
    cc = r.headers.get("cache-control", "")
    suite.add("TS-37-08", "no-cache header admin", "no-cache" in cc or "no-store" in cc)

    r = d.get(f"{BASE_URL}/dealer/dashboard", follow_redirects=True)
    cc = r.headers.get("cache-control", "")
    suite.add("TS-38-06", "no-cache header dealer", "no-cache" in cc or "no-store" in cc)

    return suite


def run_ts50_admin_coupons():
    suite = TestSuite("TS-50: مدیریت کوپن ادمین")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    a = get_session(ADMIN_MOBILE)

    r = _get(a, "/admin/coupons")
    suite.add("TS-50-01", "لیست کوپن‌ها", r.status_code == 200)

    r = _get(a, "/admin/coupons/new")
    suite.add("TS-50-02", "فرم ایجاد کوپن", r.status_code == 200)

    return suite


def run_ts_neg():
    suite = TestSuite("TS-NEG: تست‌های منفی و امنیتی")
    print(f"\n{'='*60}\n  {suite.name}\n{'='*60}")

    # TS-NEG-B: Auth/IDOR
    endpoints = [
        ("/wallet", "TS-NEG-B01"),
        ("/orders", "TS-NEG-B02"),
        ("/profile", "TS-NEG-B03"),
        ("/admin/dashboard", "TS-NEG-B04"),
        ("/dealer/dashboard", "TS-NEG-B05"),
    ]
    for path, tid in endpoints:
        with get_anon_client() as anon:
            r = anon.get(f"{BASE_URL}{path}", follow_redirects=False)
            suite.add(tid, f"بدون لاگین → {path}", r.status_code in (302, 303, 401, 403))

    # Customer → admin
    c = get_session(CUSTOMER_MOBILE)
    r = c.get(f"{BASE_URL}/admin/products", follow_redirects=False)
    suite.add("TS-NEG-B06", "مشتری → admin", r.status_code in (302, 303, 401, 403))

    r = c.get(f"{BASE_URL}/dealer/pos", follow_redirects=False)
    suite.add("TS-NEG-B07", "مشتری → dealer", r.status_code in (302, 303, 401, 403))

    d = get_session(DEALER_MOBILE)
    r = d.get(f"{BASE_URL}/admin/settings", follow_redirects=False)
    suite.add("TS-NEG-B08", "نماینده → admin settings", r.status_code in (302, 303, 401, 403))

    # TS-NEG-E: Edge cases
    with get_anon_client() as anon:
        r = anon.get(f"{BASE_URL}/product/abc", follow_redirects=True)
        suite.add("TS-NEG-E01", "product_id حروفی", r.status_code in (404, 422))

        r = anon.get(f"{BASE_URL}/nonexistent/page", follow_redirects=True)
        suite.add("TS-NEG-E09", "مسیر ناموجود → 404", r.status_code == 404)

        r = anon.request("PUT", f"{BASE_URL}/auth/send-otp")
        suite.add("TS-NEG-E08", "PUT → 405", r.status_code == 405)

    return suite


# ─── Main ────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  TalaMala v4 — Automated Test Runner")
    print(f"  Server: {BASE_URL}")
    print("=" * 60)

    # Check server
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            print("  ❌ Server not healthy!")
            return 1
    except Exception:
        print("  ❌ Server not reachable!")
        return 1

    print("  ✅ Server is healthy\n")

    # Setup test database (roles, wallets, API keys)
    print("  Setting up test database...")
    try:
        setup_test_database()
    except Exception as e:
        print(f"  ⚠️  DB setup error (non-fatal): {e}")

    print("  Logging in test users...")

    # Pre-login all users
    for mobile, label in [
        (ADMIN_MOBILE, "Admin"),
        (OPERATOR_MOBILE, "Operator"),
        (CUSTOMER_MOBILE, "Customer U3"),
        (CUSTOMER2_MOBILE, "Customer U4"),
        (CUSTOMER3_MOBILE, "Customer U5"),
        (DEALER_MOBILE, "Dealer D1"),
    ]:
        c = get_session(mobile)
        status = "✅" if "auth_token" in c.cookies else "❌"
        print(f"    {status} {label} ({mobile})")

    all_suites = []

    runners = [
        run_ts01_auth,
        run_ts02_shop,
        run_ts03_cart,
        run_ts04_checkout,
        run_ts05_payment,
        run_ts06_wallet,
        run_ts07_coupon,
        run_ts08_admin_catalog,
        run_ts09_admin_orders,
        run_ts10_admin_bars,
        run_ts11_dealer_pos,
        run_ts12_to_ts15,
        run_ts16_verification,
        run_ts17_profile,
        run_ts18_admin_customers,
        run_ts19_tickets,
        run_ts20_dealer_api,
        run_ts22_ownership,
        run_ts23_custodial,
        run_ts26_dealer_request,
        run_ts27_reviews,
        run_ts28_to_ts34,
        run_ts35_to_ts40,
        run_ts50_admin_coupons,
        run_ts_neg,
    ]

    for runner in runners:
        try:
            suite = runner()
            all_suites.append(suite)
        except Exception as e:
            print(f"  ❌ {runner.__name__} CRASHED: {e}")
            import traceback
            traceback.print_exc()
            all_suites.append(TestSuite(runner.__name__, [TestResult(runner.__name__, str(e), False)]))

    # Summary
    print(f"\n{'='*60}")
    print("  خلاصه نتایج تست")
    print(f"{'='*60}")

    total_passed = 0
    total_failed = 0
    failed_tests = []

    for suite in all_suites:
        p = suite.passed_count
        f = suite.failed_count
        total_passed += p
        total_failed += f
        status = "✅" if f == 0 else "❌"
        print(f"  {status} {suite.name}: {p}/{p+f}")
        for r in suite.results:
            if not r.passed:
                failed_tests.append(r)

    total = total_passed + total_failed
    pct = total_passed * 100 // total if total else 0
    print(f"\n  {'='*40}")
    print(f"  مجموع: {total_passed}/{total} passed ({pct}%)")

    if failed_tests:
        print(f"\n  تست‌های ناموفق ({total_failed}):")
        for t in failed_tests:
            print(f"    ❌ {t.test_id}: {t.description}")
            if t.details:
                print(f"       → {t.details}")

    close_all_sessions()
    return total_failed


if __name__ == "__main__":
    failed = main()
    sys.exit(1 if failed else 0)
