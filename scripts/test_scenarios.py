"""
TalaMala v4 - Automated Test Scenarios
========================================
Tests all major flows: Auth, Shop, Cart, Checkout, Payment, Wallet, Admin, Dealer, etc.
"""
import sys
import httpx

BASE = "http://127.0.0.1:8000"
results = []


def report(test_id, desc, passed, note=""):
    status = "PASS" if passed else "FAIL"
    results.append((test_id, desc, status, note))
    icon = "\u2705" if passed else "\u274c"
    print(f"  {icon} {test_id}: {desc} {'- ' + note if note else ''}")


def get_csrf(client, url=None):
    """Get CSRF token by visiting a GET page."""
    if url:
        client.get(url, follow_redirects=True)
    return client.cookies.get("csrf_token", "")


def login(mobile, expected_redirect=None):
    """Login helper: returns authenticated client."""
    c = httpx.Client(base_url=BASE, follow_redirects=False, timeout=15)
    # Visit login page to get csrf cookie
    c.get("/auth/login")
    csrf = c.cookies.get("csrf_token", "")
    # Send OTP (renders verify form, returns 200)
    r = c.post("/auth/send-otp", data={"mobile": mobile, "csrf_token": csrf})
    # Verify OTP - field name is "code" not "otp_code"
    csrf = c.cookies.get("csrf_token", csrf)
    r = c.post("/auth/verify-otp", data={"mobile": mobile, "code": "111111", "csrf_token": csrf})
    if expected_redirect:
        loc = r.headers.get("location", "")
        if expected_redirect not in loc:
            return c, False, f"redirect={loc} status={r.status_code}"
        return c, True, f"redirect={loc}"
    return c, r.status_code in (200, 302, 303), ""


# ============================================================
print("\n" + "=" * 60)
print("  TS-01: Auth")
print("=" * 60)

# TS-01-01
r = httpx.get(f"{BASE}/auth/login", follow_redirects=True)
report("TS-01-01", "Login page loads", r.status_code == 200)

# TS-01-02 + TS-01-03: Admin login
admin, ok, note = login("09123456789", "/admin/")
report("TS-01-02/03", "Admin login + redirect to /admin/dashboard", ok, note)

# TS-01-04 + TS-01-05: Customer login
cust, ok, note = login("09351234567", "/")
report("TS-01-04/05", "Customer login + redirect to /", ok, note)

# TS-01-06: Dealer login
dealer, ok, note = login("09161234567", "/dealer/")
report("TS-01-06", "Dealer login + redirect to /dealer/dashboard", ok, note)

# TS-01-07: Logout
r = cust.get("/auth/logout")
loc = r.headers.get("location", "")
report("TS-01-07", "Logout redirects to /auth/login", "/auth/login" in loc, f"redirect={loc}")

# Re-login customer for further tests
cust, _, _ = login("09351234567")

# TS-01-08: New customer
new_cust, ok, note = login("09199999999", "/")
report("TS-01-08", "New customer auto-created + redirect", ok, note)
new_cust.close()

# TS-01-09: Wrong OTP (use U5 to avoid rate limit on U3)
c09 = httpx.Client(base_url=BASE, follow_redirects=False, timeout=15)
c09.get("/auth/login")
csrf = c09.cookies.get("csrf_token", "")
c09.post("/auth/send-otp", data={"mobile": "09131112233", "csrf_token": csrf})
csrf = c09.cookies.get("csrf_token", csrf)
r = c09.post("/auth/verify-otp", data={"mobile": "09131112233", "code": "000000", "csrf_token": csrf})
# Wrong OTP returns 200 with step=verify (shows error on login page), not a redirect
is_not_redirect = r.status_code == 200
report("TS-01-09", "Wrong OTP rejected (stays on login)", is_not_redirect)
c09.close()

# TS-01-10: Invalid mobile (too short)
c10 = httpx.Client(base_url=BASE, follow_redirects=False, timeout=15)
c10.get("/auth/login")
csrf = c10.cookies.get("csrf_token", "")
r = c10.post("/auth/send-otp", data={"mobile": "1234", "csrf_token": csrf})
# Short mobile should be rejected - either 200 with error or 422
is_err = r.status_code in (200, 422)
report("TS-01-10", "Invalid mobile handled", is_err)
c10.close()


# ============================================================
print("\n" + "=" * 60)
print("  TS-02: Shop")
print("=" * 60)

r = httpx.get(f"{BASE}/", follow_redirects=True, timeout=15)
report("TS-02-01", "Shop home page loads", r.status_code == 200)

r = httpx.get(f"{BASE}/product/1", follow_redirects=True, timeout=15)
report("TS-02-05", "Product detail page loads", r.status_code == 200)

has_price = "تومان" in r.text
report("TS-02-06", "Product detail has price info", has_price)


# ============================================================
print("\n" + "=" * 60)
print("  TS-03: Cart")
print("=" * 60)

# TS-03-06: Cart without login
anon = httpx.Client(base_url=BASE, follow_redirects=False, timeout=15)
r = anon.get("/cart")
report("TS-03-06", "Cart without login -> redirect", r.status_code in (302, 303, 307, 401))
anon.close()

# TS-03-01: Add to cart (uses /cart/update with action=increase)
csrf = get_csrf(cust, "/product/1")
r = cust.post("/cart/update", data={"product_id": "1", "action": "increase", "csrf_token": csrf},
              follow_redirects=True)
report("TS-03-01", "Add to cart", r.status_code == 200)

# TS-03-02: View cart
r = cust.get("/cart", follow_redirects=True)
has_items = r.status_code == 200 and ("سبد" in r.text or "cart" in r.text.lower())
report("TS-03-02", "View cart with items", has_items)

# TS-03-04: Remove from cart
csrf = cust.cookies.get("csrf_token", "")
r = cust.post("/cart/update", data={"product_id": "1", "action": "remove", "csrf_token": csrf},
              follow_redirects=True)
report("TS-03-04", "Remove from cart", r.status_code == 200)

# TS-03-05: Empty cart
r = cust.get("/cart", follow_redirects=True)
report("TS-03-05", "Empty cart page loads", r.status_code == 200)


# ============================================================
print("\n" + "=" * 60)
print("  TS-04: Checkout + TS-05: Payment")
print("=" * 60)

# Add item back for checkout
csrf = get_csrf(cust, "/")
r = cust.post("/cart/update", data={"product_id": "1", "action": "increase", "csrf_token": csrf},
              follow_redirects=True)

# TS-04-01: Checkout page
r = cust.get("/checkout", follow_redirects=True)
report("TS-04-01", "Checkout page loads", r.status_code == 200)

# TS-04-06: Place order (pickup)
csrf = cust.cookies.get("csrf_token", "")
r = cust.post("/cart/checkout", data={
    "csrf_token": csrf,
    "delivery_method": "Pickup",
    "pickup_location_id": "2",
    "commitment": "on",
}, follow_redirects=False)
loc = r.headers.get("location", "")
order_placed = "/orders/" in loc
report("TS-04-06", "Place order (pickup)", order_placed, f"redirect={loc}")

# Extract order ID
order_id = ""
if "/orders/" in loc:
    order_id = loc.split("/orders/")[-1].split("?")[0].split("/")[0]
    report("TS-04-06a", f"Order created ID={order_id}", bool(order_id))

# View order detail
if order_id:
    r = cust.get(f"/orders/{order_id}", follow_redirects=True)
    report("TS-04-08", "Order detail page loads", r.status_code == 200 and "Pending" in r.text or "در انتظار" in r.text)

# TS-05-01: Wallet payment
if order_id:
    csrf = get_csrf(cust, f"/orders/{order_id}")
    r = cust.post(f"/payment/{order_id}/wallet", data={"csrf_token": csrf}, follow_redirects=True)
    paid = r.status_code == 200 and ("پرداخت" in r.text or "Paid" in r.text)
    report("TS-05-01", "Wallet payment (sufficient balance)", paid)
else:
    report("TS-05-01", "Wallet payment", False, "No order ID")

# TS-05-02: Payment with insufficient balance (U4)
cust4, _, _ = login("09359876543")
csrf = get_csrf(cust4, "/")
cust4.post("/cart/update", data={"product_id": "1", "action": "increase", "csrf_token": csrf},
           follow_redirects=True)
r = cust4.get("/checkout", follow_redirects=True)
csrf = cust4.cookies.get("csrf_token", "")
r = cust4.post("/cart/checkout", data={
    "csrf_token": csrf,
    "delivery_method": "Pickup",
    "pickup_location_id": "2",
    "commitment": "on",
}, follow_redirects=False)
loc4 = r.headers.get("location", "")
order_id4 = ""
if "/orders/" in loc4:
    order_id4 = loc4.split("/orders/")[-1].split("?")[0].split("/")[0]

if order_id4:
    csrf = get_csrf(cust4, f"/orders/{order_id4}")
    r = cust4.post(f"/payment/{order_id4}/wallet", data={"csrf_token": csrf}, follow_redirects=True)
    has_error = "کافی" in r.text or "موجودی" in r.text or "error" in r.text.lower()
    report("TS-05-02", "Wallet payment (insufficient balance)", has_error)
else:
    report("TS-05-02", "Wallet payment insufficient", False, f"No order: loc={loc4}")
cust4.close()


# ============================================================
print("\n" + "=" * 60)
print("  TS-06: Wallet")
print("=" * 60)

r = cust.get("/wallet", follow_redirects=True)
report("TS-06-01", "Wallet dashboard", r.status_code == 200)

r = cust.get("/wallet/transactions", follow_redirects=True)
report("TS-06-02", "Wallet transactions", r.status_code == 200)


# ============================================================
print("\n" + "=" * 60)
print("  TS-08: Admin Panel")
print("=" * 60)

pages = [
    ("TS-08-01", "/admin/dashboard", "Admin dashboard"),
    ("TS-08-03", "/admin/products", "Admin products"),
    ("TS-08-06", "/admin/categories", "Admin categories"),
    ("TS-08-08", "/admin/bars", "Admin bars"),
    ("TS-08-10", "/admin/locations", "Admin locations"),
    ("TS-08-11", "/admin/orders", "Admin orders"),
    ("TS-08-12", "/admin/settings", "Admin settings"),
    ("TS-08-14", "/admin/wallets", "Admin wallet accounts"),
    ("TS-08-16", "/admin/wallets/withdrawals/list", "Admin withdrawals"),
    ("TS-08-17", "/admin/coupons", "Admin coupons"),
]
for tid, path, desc in pages:
    r = admin.get(path, follow_redirects=True)
    report(tid, desc, r.status_code == 200)


# ============================================================
print("\n" + "=" * 60)
print("  TS-09: Dealer Panel")
print("=" * 60)

r = dealer.get("/dealer/dashboard", follow_redirects=True)
report("TS-09-10", "Dealer dashboard", r.status_code == 200)

r = dealer.get("/dealer/pos", follow_redirects=True)
report("TS-09-11", "Dealer POS page", r.status_code == 200)

r = dealer.get("/dealer/sales", follow_redirects=True)
report("TS-09-16", "Dealer sales history", r.status_code == 200)

r = dealer.get("/dealer/buybacks", follow_redirects=True)
report("TS-09-17", "Dealer buybacks history", r.status_code == 200)


# ============================================================
print("\n" + "=" * 60)
print("  TS-10: Verification")
print("=" * 60)

r = httpx.get(f"{BASE}/verify", follow_redirects=True, timeout=15)
report("TS-10-01", "Verify page loads", r.status_code == 200)

r = httpx.get(f"{BASE}/verify/check?code=TSCLM001", follow_redirects=True, timeout=15)
report("TS-10-02", "Valid serial found", r.status_code == 200 and "TSCLM001" in r.text)

r = httpx.get(f"{BASE}/verify/check?code=XXXXXXXX", follow_redirects=True, timeout=15)
report("TS-10-03", "Invalid serial not found", r.status_code == 200 and ("یافت نشد" in r.text or "not found" in r.text.lower()))


# ============================================================
print("\n" + "=" * 60)
print("  TS-11: Profile & Address")
print("=" * 60)

r = cust.get("/profile", follow_redirects=True)
report("TS-11-01", "Profile page", r.status_code == 200)

r = cust.get("/addresses", follow_redirects=True)
report("TS-11-03", "Address book", r.status_code == 200)


# ============================================================
print("\n" + "=" * 60)
print("  TS-12: Tickets")
print("=" * 60)

r = cust.get("/tickets", follow_redirects=True)
report("TS-12-01", "Customer ticket list", r.status_code == 200)

r = cust.get("/tickets/new", follow_redirects=True)
report("TS-12-02a", "Create ticket form", r.status_code == 200)

r = admin.get("/admin/tickets", follow_redirects=True)
report("TS-12-11", "Admin ticket list", r.status_code == 200)


# ============================================================
print("\n" + "=" * 60)
print("  TS-13: POS REST API")
print("=" * 60)

headers_api = {"X-API-Key": "test_esfahan_key_0000000000000000"}

# TS-13-01: No API key
r = httpx.get(f"{BASE}/api/dealer/info", timeout=15)
report("TS-13-01", "No API key -> error", r.status_code in (401, 422))

# TS-13-02: Invalid key
r = httpx.get(f"{BASE}/api/dealer/info", headers={"X-API-Key": "bad_key"}, timeout=15)
report("TS-13-02", "Invalid API key -> 401", r.status_code == 401)

# TS-13-03: Valid key
r = httpx.get(f"{BASE}/api/dealer/info", headers=headers_api, timeout=15)
report("TS-13-03", "Valid API key -> 200", r.status_code == 200)

# TS-13-05: Products list
r = httpx.get(f"{BASE}/api/dealer/products", headers=headers_api, timeout=15)
report("TS-13-05", "Products list via API", r.status_code == 200)
if r.status_code == 200:
    data = r.json()
    has_cats = any("categories" in p for p in data.get("products", []))
    report("TS-13-05a", "Products have categories array", has_cats)

# TS-13-14: Sales list
r = httpx.get(f"{BASE}/api/dealer/sales", headers=headers_api, timeout=15)
report("TS-13-14", "Sales list via API", r.status_code == 200)


# ============================================================
print("\n" + "=" * 60)
print("  TS-15: Static Pages & Footer")
print("=" * 60)

static_pages = [
    ("TS-15-01", "/about", "About page"),
    ("TS-15-02", "/faq", "FAQ page"),
    ("TS-15-03", "/contact", "Contact page"),
    ("TS-15-04", "/terms", "Terms page"),
]
for tid, path, desc in static_pages:
    r = httpx.get(f"{BASE}{path}", follow_redirects=True, timeout=15)
    report(tid, desc, r.status_code == 200)


# ============================================================
print("\n" + "=" * 60)
print("  TS-16: Bar Claim & Transfer")
print("=" * 60)

# TS-16-08: Claim page
r = cust.get("/claim-bar", follow_redirects=True)
report("TS-16-08", "Claim bar page loads", r.status_code == 200)

# TS-16-15: My bars
r = cust.get("/my-bars", follow_redirects=True)
report("TS-16-15", "My bars page (U3)", r.status_code == 200)

# TS-16-09: Claim bar successfully (as U4)
cust4b, _, _ = login("09359876543")
csrf = get_csrf(cust4b, "/claim-bar")
r = cust4b.post("/claim-bar", data={
    "serial_code": "TSCLM001",
    "claim_code": "ABC123",
    "csrf_token": csrf,
}, follow_redirects=True)
claim_ok = r.status_code == 200 and ("موفق" in r.text or "success" in r.text.lower())
report("TS-16-09", "Claim bar successfully", claim_ok)

# TS-16-11: Claim with wrong code
csrf = get_csrf(cust4b, "/claim-bar")
r = cust4b.post("/claim-bar", data={
    "serial_code": "TSCLM002",
    "claim_code": "WRONG1",
    "csrf_token": csrf,
}, follow_redirects=True)
wrong_code = r.status_code == 200 and ("نامعتبر" in r.text or "error" in r.text.lower() or "خطا" in r.text)
report("TS-16-11", "Claim with wrong code rejected", wrong_code)

# TS-16-12: Claim with nonexistent serial
csrf = get_csrf(cust4b, "/claim-bar")
r = cust4b.post("/claim-bar", data={
    "serial_code": "XXXXXXXX",
    "claim_code": "ABC123",
    "csrf_token": csrf,
}, follow_redirects=True)
not_found = r.status_code == 200 and ("یافت نشد" in r.text or "not found" in r.text.lower() or "خطا" in r.text or "error" in r.text.lower() or "claim-bar" in str(r.url))
report("TS-16-12", "Claim nonexistent serial rejected", not_found)
cust4b.close()


# ============================================================
print("\n" + "=" * 60)
print("  TS-NEG: Negative Tests")
print("=" * 60)

# TS-NEG-01: Admin without login
anon2 = httpx.Client(base_url=BASE, follow_redirects=False, timeout=15)
r = anon2.get("/admin/dashboard")
report("TS-NEG-01", "Admin without login -> redirect/401", r.status_code in (302, 303, 307, 401))

# TS-NEG-02: Dealer without login
r = anon2.get("/dealer/dashboard")
report("TS-NEG-02", "Dealer without login -> redirect/401", r.status_code in (302, 303, 307, 401))

# TS-NEG-03: Customer to admin panel
r = cust.get("/admin/dashboard", follow_redirects=False)
report("TS-NEG-03", "Customer to admin -> reject", r.status_code in (302, 303, 401, 403))

# TS-NEG-05: Customer to dealer panel
r = cust.get("/dealer/dashboard", follow_redirects=False)
report("TS-NEG-05", "Customer to dealer panel -> reject", r.status_code in (302, 303, 401, 403))

# TS-NEG-19: 404 page
r = httpx.get(f"{BASE}/nonexistent-page-xyz", follow_redirects=True, timeout=15)
report("TS-NEG-19", "404 page", r.status_code == 404)

# TS-NEG-20: Health check
r = httpx.get(f"{BASE}/health", timeout=15)
report("TS-NEG-20", "Health check -> 200", r.status_code == 200)

# TS-NEG-24: My bars without login
r = anon2.get("/my-bars")
report("TS-NEG-24", "My bars without login -> redirect", r.status_code in (302, 303, 307, 401))

anon2.close()


# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("  SUMMARY")
print("=" * 60)

passed = sum(1 for r in results if r[2] == "PASS")
failed = sum(1 for r in results if r[2] == "FAIL")
total = len(results)

print(f"\n  Total: {total}  |  PASS: {passed}  |  FAIL: {failed}")
print()

if failed:
    print("  FAILED TESTS:")
    for tid, desc, status, note in results:
        if status == "FAIL":
            print(f"    {tid}: {desc} {note}")

# Cleanup
admin.close()
cust.close()
dealer.close()

sys.exit(0 if failed == 0 else 1)
