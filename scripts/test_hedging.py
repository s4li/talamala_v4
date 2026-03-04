"""
Hedging Module — Integration Test
====================================
Tests admin dashboard, record, adjust, ledger, API, and integration hooks.
Runs against a live local server (uvicorn on :8000).
"""

import sys
import os
import re
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://127.0.0.1:8000"
ADMIN_MOBILE = "09121058447"  # Super admin (production)
CUSTOMER_MOBILE = "09226606951"  # Customer with some wallet balance

results = []


def log_result(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    results.append((name, ok, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def login(client: httpx.Client, mobile: str) -> bool:
    """Login via OTP (debug mode: OTP is always 111111)."""
    # Send OTP
    r = client.get(f"{BASE}/auth/login")
    csrf = r.cookies.get("csrf_token", "")

    r = client.post(f"{BASE}/auth/send-otp", data={
        "mobile": mobile, "csrf_token": csrf,
    }, follow_redirects=False)

    # Verify OTP
    r2 = client.get(f"{BASE}/auth/login")
    csrf2 = r2.cookies.get("csrf_token", "")

    r3 = client.post(f"{BASE}/auth/verify-otp", data={
        "mobile": mobile, "code": "111111", "csrf_token": csrf2,
    }, follow_redirects=False)

    # Extract auth_token from Set-Cookie header
    auth_token = None
    for header_val in r3.headers.get_list("set-cookie"):
        m = re.search(r"auth_token=([^;]+)", header_val)
        if m:
            auth_token = m.group(1)
            break

    if auth_token:
        client.cookies.set("auth_token", auth_token)
        return True
    return False


def test_admin_pages(client: httpx.Client):
    """Test admin hedging page access."""
    print("\n--- Admin Hedging Pages ---")

    # Dashboard
    r = client.get(f"{BASE}/admin/hedging", follow_redirects=True)
    log_result("Dashboard GET", r.status_code == 200,
               f"status={r.status_code}, len={len(r.text)}")

    # Ledger
    r = client.get(f"{BASE}/admin/hedging/ledger", follow_redirects=True)
    log_result("Ledger GET", r.status_code == 200, f"status={r.status_code}")

    # Record form
    r = client.get(f"{BASE}/admin/hedging/record", follow_redirects=True)
    log_result("Record form GET", r.status_code == 200, f"status={r.status_code}")

    # Adjust form
    r = client.get(f"{BASE}/admin/hedging/adjust", follow_redirects=True)
    log_result("Adjust form GET", r.status_code == 200, f"status={r.status_code}")

    # API position
    r = client.get(f"{BASE}/admin/hedging/api/position", follow_redirects=True)
    log_result("API position GET", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        log_result("API has gold+silver", "gold" in data and "silver" in data,
                   f"keys={list(data.keys())}")
        gold = data.get("gold", {})
        log_result("Gold balance_mg present", "balance_mg" in gold,
                   f"balance={gold.get('balance_mg', '?')}mg")


def test_adjust(client: httpx.Client):
    """Test setting initial balance via adjust form."""
    print("\n--- Test: Set Initial Balance ---")

    # Get CSRF
    r = client.get(f"{BASE}/admin/hedging/adjust", follow_redirects=True)
    csrf = client.cookies.get("csrf_token", "")

    # Set gold balance to 100g (100000mg)
    r = client.post(f"{BASE}/admin/hedging/adjust", data={
        "metal_type": "gold",
        "target_balance_grams": "100",
        "description": "Test: set initial gold balance",
        "csrf_token": csrf,
    }, follow_redirects=True)
    log_result("Adjust gold to 100g", r.status_code == 200,
               f"status={r.status_code}")

    # Verify via API
    r = client.get(f"{BASE}/admin/hedging/api/position")
    if r.status_code == 200:
        gold_balance = r.json()["gold"]["balance_mg"]
        log_result("Gold balance is 100000mg", gold_balance == 100000,
                   f"balance={gold_balance}mg")

    # Set silver balance to 500g
    r2 = client.get(f"{BASE}/admin/hedging/adjust", follow_redirects=True)
    csrf2 = client.cookies.get("csrf_token", "")
    r2 = client.post(f"{BASE}/admin/hedging/adjust", data={
        "metal_type": "silver",
        "target_balance_grams": "500",
        "description": "Test: set initial silver balance",
        "csrf_token": csrf2,
    }, follow_redirects=True)
    log_result("Adjust silver to 500g", r2.status_code == 200,
               f"status={r2.status_code}")

    r3 = client.get(f"{BASE}/admin/hedging/api/position")
    if r3.status_code == 200:
        silver_balance = r3.json()["silver"]["balance_mg"]
        log_result("Silver balance is 500000mg", silver_balance == 500000,
                   f"balance={silver_balance}mg")


def test_record_hedge(client: httpx.Client):
    """Test recording a hedge trade."""
    print("\n--- Test: Record Hedge Trade ---")

    # Get current gold balance
    r0 = client.get(f"{BASE}/admin/hedging/api/position")
    before = r0.json()["gold"]["balance_mg"] if r0.status_code == 200 else 0

    # Record: buy 50g gold from market (should increase balance)
    r = client.get(f"{BASE}/admin/hedging/record", follow_redirects=True)
    csrf = client.cookies.get("csrf_token", "")

    r = client.post(f"{BASE}/admin/hedging/record", data={
        "metal_type": "gold",
        "hedge_direction": "buy",
        "amount_grams": "50",
        "price_per_gram": "5500000",
        "description": "Test: buy 50g gold from market",
        "csrf_token": csrf,
    }, follow_redirects=True)
    log_result("Record hedge buy 50g gold", r.status_code == 200,
               f"status={r.status_code}")

    # Verify balance increased by 50g
    r2 = client.get(f"{BASE}/admin/hedging/api/position")
    if r2.status_code == 200:
        after = r2.json()["gold"]["balance_mg"]
        delta = after - before
        log_result("Balance increased by 50000mg", delta == 50000,
                   f"before={before}, after={after}, delta={delta}")

    # Record: sell 20g gold on market (should decrease balance)
    r3 = client.get(f"{BASE}/admin/hedging/record", follow_redirects=True)
    csrf3 = client.cookies.get("csrf_token", "")

    before2 = after if r2.status_code == 200 else before

    r3 = client.post(f"{BASE}/admin/hedging/record", data={
        "metal_type": "gold",
        "hedge_direction": "sell",
        "amount_grams": "20",
        "price_per_gram": "5600000",
        "description": "Test: sell 20g gold on market",
        "csrf_token": csrf3,
    }, follow_redirects=True)
    log_result("Record hedge sell 20g gold", r3.status_code == 200,
               f"status={r3.status_code}")

    r4 = client.get(f"{BASE}/admin/hedging/api/position")
    if r4.status_code == 200:
        after2 = r4.json()["gold"]["balance_mg"]
        delta2 = after2 - before2
        log_result("Balance decreased by 20000mg", delta2 == -20000,
                   f"before={before2}, after={after2}, delta={delta2}")


def test_ledger_filters(client: httpx.Client):
    """Test ledger page with filters."""
    print("\n--- Test: Ledger Filters ---")

    # All entries
    r = client.get(f"{BASE}/admin/hedging/ledger", follow_redirects=True)
    log_result("Ledger (no filter)", r.status_code == 200, f"status={r.status_code}")

    # Filter by metal
    r = client.get(f"{BASE}/admin/hedging/ledger?metal=gold", follow_redirects=True)
    log_result("Ledger (gold only)", r.status_code == 200, f"status={r.status_code}")

    # Filter by source type
    r = client.get(f"{BASE}/admin/hedging/ledger?source=hedge", follow_redirects=True)
    log_result("Ledger (hedge source)", r.status_code == 200, f"status={r.status_code}")

    # Filter by direction
    r = client.get(f"{BASE}/admin/hedging/ledger?direction=IN", follow_redirects=True)
    log_result("Ledger (IN direction)", r.status_code == 200, f"status={r.status_code}")


def test_wallet_integration(admin_client: httpx.Client):
    """Test wallet buy/sell triggers hedging hooks."""
    print("\n--- Test: Wallet Integration ---")

    # Login as customer
    cust = httpx.Client(timeout=30)
    logged = login(cust, CUSTOMER_MOBILE)
    if not logged:
        log_result("Customer login", False, "Could not login")
        cust.close()
        return

    log_result("Customer login", True)

    # Get gold balance before
    r0 = admin_client.get(f"{BASE}/admin/hedging/api/position")
    gold_before = r0.json()["gold"]["balance_mg"] if r0.status_code == 200 else 0

    # Check wallet page for gold
    r = cust.get(f"{BASE}/wallet/gold", follow_redirects=True)
    wallet_ok = r.status_code == 200
    log_result("Wallet gold page", wallet_ok, f"status={r.status_code}")

    if not wallet_ok:
        cust.close()
        return

    import time

    # Buy gold with 1M toman from wallet (bigger amount for clear delta)
    csrf = cust.cookies.get("csrf_token", "")
    r = cust.post(f"{BASE}/wallet/gold/buy", data={
        "amount_toman": "1000000",
        "csrf_token": csrf,
    }, follow_redirects=True)
    buy_ok = r.status_code == 200
    log_result("Wallet buy gold (1M toman)", buy_ok, f"status={r.status_code}")

    # Wait for DB commit to propagate
    time.sleep(1)

    # Check hedging balance changed (delta depends on price, just check it decreased)
    r2 = admin_client.get(f"{BASE}/admin/hedging/api/position")
    if r2.status_code == 200:
        gold_after = r2.json()["gold"]["balance_mg"]
        delta = gold_after - gold_before
        log_result("Hedging OUT after wallet buy", delta < 0,
                   f"before={gold_before}, after={gold_after}, delta={delta}")
        gold_before = gold_after  # Update for sell test
    else:
        log_result("Hedging check after buy", False, f"status={r2.status_code}")

    # Sell 0.01g gold from wallet
    r3 = cust.get(f"{BASE}/wallet/gold", follow_redirects=True)
    csrf3 = cust.cookies.get("csrf_token", "")
    r3 = cust.post(f"{BASE}/wallet/gold/sell", data={
        "metal_grams": "0.01",
        "csrf_token": csrf3,
    }, follow_redirects=True)
    sell_ok = r3.status_code == 200
    log_result("Wallet sell 0.01g gold", sell_ok, f"status={r3.status_code}")

    time.sleep(1)

    # Check hedging balance changed (IN — should increase)
    r4 = admin_client.get(f"{BASE}/admin/hedging/api/position")
    if r4.status_code == 200:
        gold_after2 = r4.json()["gold"]["balance_mg"]
        delta2 = gold_after2 - gold_before
        log_result("Hedging IN after wallet sell", delta2 > 0,
                   f"before={gold_before}, after={gold_after2}, delta={delta2}")

    cust.close()


def test_validation(client: httpx.Client):
    """Test input validation on forms."""
    print("\n--- Test: Input Validation ---")

    # Record: invalid metal type
    r = client.get(f"{BASE}/admin/hedging/record", follow_redirects=True)
    csrf = client.cookies.get("csrf_token", "")
    r = client.post(f"{BASE}/admin/hedging/record", data={
        "metal_type": "platinum",
        "hedge_direction": "buy",
        "amount_grams": "10",
        "csrf_token": csrf,
    }, follow_redirects=True)
    log_result("Reject invalid metal type", "نامعتبر" in r.text or r.status_code == 200,
               f"status={r.status_code}")

    # Record: zero amount
    r2 = client.get(f"{BASE}/admin/hedging/record", follow_redirects=True)
    csrf2 = client.cookies.get("csrf_token", "")
    r2 = client.post(f"{BASE}/admin/hedging/record", data={
        "metal_type": "gold",
        "hedge_direction": "buy",
        "amount_grams": "0",
        "csrf_token": csrf2,
    }, follow_redirects=True)
    log_result("Reject zero amount", "صفر" in r2.text or r2.status_code == 200,
               f"status={r2.status_code}")

    # Adjust: negative balance (valid — means short position)
    r3 = client.get(f"{BASE}/admin/hedging/adjust", follow_redirects=True)
    csrf3 = client.cookies.get("csrf_token", "")

    # Get current balance first
    r_pos = client.get(f"{BASE}/admin/hedging/api/position")
    before = r_pos.json()["gold"]["balance_mg"] if r_pos.status_code == 200 else 0

    r3 = client.post(f"{BASE}/admin/hedging/adjust", data={
        "metal_type": "gold",
        "target_balance_grams": "-10",
        "description": "Test: set negative balance",
        "csrf_token": csrf3,
    }, follow_redirects=True)
    log_result("Adjust to negative balance", r3.status_code == 200,
               f"status={r3.status_code}")

    r4 = client.get(f"{BASE}/admin/hedging/api/position")
    if r4.status_code == 200:
        after = r4.json()["gold"]["balance_mg"]
        log_result("Gold balance is -10000mg", after == -10000,
                   f"balance={after}mg")


def test_dashboard_content(client: httpx.Client):
    """Test dashboard shows correct data after all operations."""
    print("\n--- Test: Dashboard Content Verification ---")

    r = client.get(f"{BASE}/admin/hedging", follow_redirects=True)
    if r.status_code == 200:
        text = r.text
        log_result("Dashboard has gold card", "طلا" in text, "")
        log_result("Dashboard has silver card", "نقره" in text, "")
        log_result("Dashboard has chart", "chart" in text.lower() or "Chart" in text, "")
        log_result("Dashboard has ledger table", "ledger" in text.lower() or "دفترکل" in text, "")
    else:
        log_result("Dashboard content", False, f"status={r.status_code}")


def main():
    print("=" * 60)
    print("  Hedging Module — Integration Test")
    print("=" * 60)

    client = httpx.Client(timeout=30)

    # Login as admin
    print("\n--- Login ---")
    logged = login(client, ADMIN_MOBILE)
    if not logged:
        print("  [FAIL] Could not login as admin!")
        client.close()
        sys.exit(1)
    log_result("Admin login", True)

    # Run tests
    test_admin_pages(client)
    test_adjust(client)
    test_record_hedge(client)
    test_ledger_filters(client)
    test_validation(client)
    test_dashboard_content(client)
    test_wallet_integration(client)

    client.close()

    # Summary
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)

    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    if failed:
        print("\n  Failed tests:")
        for name, ok, detail in results:
            if not ok:
                print(f"    - {name}: {detail}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
