"""
Comprehensive test: GiftBox migration + design removal
Run after restoring production backup and running migrate_gift_boxes.py
"""
import re
import sys
import os

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from fastapi.testclient import TestClient
from config.database import SessionLocal
from sqlalchemy import text
from common.security import hash_otp, _otp_verify_attempts, _otp_attempts

client = TestClient(app)
db = SessionLocal()

results = []


def test(name, ok, detail=""):
    s = "PASS" if ok else "FAIL"
    results.append((name, s))
    suffix = f": {detail}" if detail else ""
    print(f"  [{s}] {name}{suffix}")


def get_csrf(url, cookies):
    r = client.get(url, cookies=cookies)
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    return m.group(1) if m else None, r


def login(mobile):
    # Clear rate limit for this mobile
    _otp_verify_attempts.pop(mobile, None)
    _otp_attempts.pop(mobile, None)
    hashed = hash_otp(mobile, "999999")
    db.execute(
        text("UPDATE users SET otp_code=:h, otp_expiry=NOW()+INTERVAL '5 min' WHERE mobile=:m"),
        {"m": mobile, "h": hashed},
    )
    db.commit()
    # Use a fresh client to avoid cookie contamination
    fresh = TestClient(app)
    r1 = fresh.get("/auth/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r1.text)
    csrf = m.group(1) if m else ""
    r = fresh.post(
        "/auth/verify-otp",
        data={"mobile": mobile, "code": "999999", "csrf_token": csrf},
        cookies={"csrf_token": csrf},
        follow_redirects=False,
    )
    return dict(r.cookies), r.status_code


# --- Find real users ---
admin_m = db.execute(text("SELECT mobile FROM users WHERE is_admin=true AND admin_role='admin' LIMIT 1")).scalar()
if not admin_m:
    admin_m = db.execute(text("SELECT mobile FROM users WHERE is_admin=true LIMIT 1")).scalar()
cust_row = db.execute(text(
    "SELECT id, mobile FROM users WHERE is_admin=false AND is_active=true "
    "AND mobile != :prev LIMIT 1"
), {"prev": admin_m or ""}).fetchone()
cust_id, cust_m = cust_row[0], cust_row[1]

print("=" * 60)
print("  Login")
print("=" * 60)
admin_cookies, admin_status = login(admin_m)
test(f"Admin login ({admin_m})", admin_status in (302, 303), f"status={admin_status}")

cust_cookies, cust_status = login(cust_m)
test(f"Customer login ({cust_m})", cust_status in (302, 303), f"status={cust_status}")

# === ADMIN PAGES ===
print()
print("=" * 60)
print("  Admin Pages")
print("=" * 60)

for url, name in [
    ("/admin/products", "Products list"),
    ("/admin/packages", "Packages"),
    ("/admin/gift-boxes", "Gift boxes"),
    ("/admin/batches", "Batches"),
    ("/admin/dashboard", "Dashboard"),
]:
    r = client.get(url, cookies=admin_cookies)
    test(name, r.status_code == 200, f"status={r.status_code}")

# Edit product — no design field
r = client.get("/admin/products/edit/1", cookies=admin_cookies)
if r.status_code == 200:
    has_design = 'name="design"' in r.text
    test("Edit product (no design field)", not has_design, f"design_field={has_design}")
else:
    # Product 1 might not exist — try another
    pid = db.execute(text("SELECT id FROM products LIMIT 1")).scalar()
    r = client.get(f"/admin/products/edit/{pid}", cookies=admin_cookies)
    has_design = 'name="design"' in r.text
    test("Edit product (no design field)", r.status_code == 200 and not has_design,
         f"status={r.status_code}, design_field={has_design}")

# /admin/designs should be gone
r = client.get("/admin/designs", cookies=admin_cookies, follow_redirects=False)
test("Designs route removed", r.status_code in (404, 405), f"status={r.status_code}")

# === CUSTOMER PAGES ===
print()
print("=" * 60)
print("  Customer Pages")
print("=" * 60)

for url, name in [
    ("/", "Shop home"),
    ("/cart", "Cart"),
    ("/orders", "Orders"),
    ("/wallet", "Wallet"),
]:
    r = client.get(url, cookies=cust_cookies)
    test(name, r.status_code == 200, f"status={r.status_code}")

# Product detail — no p.design reference
pid = db.execute(text("SELECT id FROM products WHERE is_active=true LIMIT 1")).scalar()
r = client.get(f"/product/{pid}", cookies=cust_cookies)
has_old = "p.design" in r.text
test("Product detail (no design ref)", r.status_code == 200 and not has_old,
     f"status={r.status_code}, old_ref={has_old}")

# === CART + GIFT BOX FLOW ===
print()
print("=" * 60)
print("  Cart + Gift Box Flow")
print("=" * 60)

# Add to cart (needs CSRF)
csrf_cart, _ = get_csrf("/cart", cust_cookies)
if csrf_cart:
    r = client.post("/cart/update", data={"product_id": str(pid), "action": "add", "csrf_token": csrf_cart},
                     cookies={**cust_cookies, "csrf_token": csrf_cart}, follow_redirects=False)
    test("Add to cart", r.status_code in (302, 303), f"status={r.status_code}")
else:
    test("Add to cart", False, "no CSRF (customer not logged in?)")

# Set gift box
csrf, _ = get_csrf("/cart", cust_cookies)
if csrf:
    item = db.execute(
        text("SELECT ci.id FROM cart_items ci JOIN carts c ON ci.cart_id=c.id "
             "WHERE c.customer_id=:uid ORDER BY ci.id DESC LIMIT 1"),
        {"uid": cust_id},
    ).fetchone()
    gb = db.execute(text("SELECT id, name FROM gift_boxes WHERE is_active=true LIMIT 1")).fetchone()

    if item and gb:
        # Route expects product_id, not item_id
        item_product = db.execute(
            text("SELECT product_id FROM cart_items WHERE id=:id"), {"id": item[0]}
        ).scalar()
        r = client.post("/cart/set-gift-box", data={
            "product_id": str(item_product), "gift_box_id": str(gb[0]), "csrf_token": csrf,
        }, cookies={**cust_cookies, "csrf_token": csrf}, follow_redirects=False)
        test(f"Set gift box ({gb[1]})", r.status_code in (302, 303), f"status={r.status_code}")

        saved = db.execute(text("SELECT gift_box_id FROM cart_items WHERE id=:id"), {"id": item[0]}).scalar()
        test("Gift box saved in DB", saved == gb[0], f"gift_box_id={saved}")
    else:
        test("Set gift box", False, "no cart item or gift box")
else:
    test("Cart CSRF", False, "not found")

# Checkout page
r = client.get("/checkout", cookies=cust_cookies)
test("Checkout page loads", r.status_code == 200, f"status={r.status_code}")

# === GIFT BOX ADMIN CRUD ===
print()
print("=" * 60)
print("  Gift Box Admin CRUD")
print("=" * 60)

csrf, _ = get_csrf("/admin/gift-boxes", admin_cookies)

# Create
r = client.post("/admin/gift-boxes/add", data={
    "name": "test_auto_gb", "price": "10000", "description": "auto test",
    "sort_order": "99", "is_active": "on", "csrf_token": csrf,
}, cookies={**admin_cookies, "csrf_token": csrf}, follow_redirects=False)
test("Create gift box", r.status_code in (302, 303), f"status={r.status_code}")

gb_new = db.execute(text("SELECT id, price FROM gift_boxes WHERE name='test_auto_gb'")).fetchone()
test("Gift box in DB", gb_new is not None,
     f"id={gb_new[0]}, price={gb_new[1]}" if gb_new else "not found")

if gb_new:
    # Update
    csrf, _ = get_csrf("/admin/gift-boxes", admin_cookies)
    r = client.post(f"/admin/gift-boxes/update/{gb_new[0]}", data={
        "name": "test_auto_gb_updated", "price": "20000", "description": "updated",
        "sort_order": "88", "is_active": "on", "csrf_token": csrf,
    }, cookies={**admin_cookies, "csrf_token": csrf}, follow_redirects=False)
    test("Update gift box", r.status_code in (302, 303), f"status={r.status_code}")

    new_name = db.execute(text(f"SELECT name FROM gift_boxes WHERE id={gb_new[0]}")).scalar()
    test("Update persisted", new_name == "test_auto_gb_updated", f"name={new_name}")

    # Delete
    csrf, _ = get_csrf("/admin/gift-boxes", admin_cookies)
    r = client.post(f"/admin/gift-boxes/delete/{gb_new[0]}", data={"csrf_token": csrf},
                     cookies={**admin_cookies, "csrf_token": csrf}, follow_redirects=False)
    test("Delete gift box", r.status_code in (302, 303), f"status={r.status_code}")

    gone = db.execute(text(f"SELECT id FROM gift_boxes WHERE id={gb_new[0]}")).fetchone()
    test("Delete confirmed", gone is None, "deleted" if gone is None else "still exists")

# === DB INTEGRITY CHECKS ===
print()
print("=" * 60)
print("  DB Integrity Checks")
print("=" * 60)

checks = [
    ("gift_boxes exist", "SELECT COUNT(*) FROM gift_boxes", lambda v: v > 0),
    ("gift_box_images exist", "SELECT COUNT(*) FROM gift_box_images", lambda v: v > 0),
    ("products.design gone", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='products' AND column_name='design'", lambda v: v == 0),
    ("products.card_design_id gone", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='products' AND column_name='card_design_id'", lambda v: v == 0),
    ("card_designs table gone", "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='card_designs'", lambda v: v == 0),
    ("cart_items.package_type_id gone", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='cart_items' AND column_name='package_type_id'", lambda v: v == 0),
    ("order_items.package_type_id gone", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='order_items' AND column_name='package_type_id'", lambda v: v == 0),
    ("cart_items.gift_box_id exists", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='cart_items' AND column_name='gift_box_id'", lambda v: v == 1),
    ("order_items.gift_box_id exists", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='order_items' AND column_name='gift_box_id'", lambda v: v == 1),
]

for label, sql, check_fn in checks:
    val = db.execute(text(sql)).scalar()
    test(label, check_fn(val), f"value={val}")

# === SUMMARY ===
print()
print("=" * 60)
passed = sum(1 for _, s in results if s == "PASS")
failed = sum(1 for _, s in results if s == "FAIL")
total = len(results)
print(f"  Results: {passed} PASS, {failed} FAIL, {total} total")
if failed:
    print()
    print("  Failed tests:")
    for n, s in results:
        if s == "FAIL":
            print(f"    - {n}")
print("=" * 60)

db.close()
sys.exit(0 if failed == 0 else 1)
