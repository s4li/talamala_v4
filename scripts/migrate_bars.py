"""
Migration script: Import bars from old TalaMala database dump.

Reads the plain-text SQL dump (_private/old_db_plain.sql) and imports
bars + their product assignments into the current v4 database.

Usage:
    python scripts/migrate_bars.py              # dry-run (no DB changes)
    python scripts/migrate_bars.py --apply      # actually insert into DB

Prerequisites:
    - seed.py --reset must have been run first (products, batches, etc. exist)
    - _private/old_db_plain.sql must exist (pg_restore from old_db_dump.sql)
"""

import os
import sys
import re

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from config.database import engine

# ---------------------------------------------------------------------------
# Mapping: old product_id → v4 product name (must match seed.py naming)
# ---------------------------------------------------------------------------
OLD_PRODUCT_TO_V4_NAME = {
    # Gold TalaMala (شمش طلا با بسته‌بندی)
    1:  "شمش طلا طلاملا ۱۰۰ سوت",
    2:  "شمش طلا طلاملا ۲۰۰ سوت",
    3:  "شمش طلا طلاملا ۵۰۰ سوت",
    4:  "شمش طلا طلاملا ۱ گرم",
    5:  "شمش طلا طلاملا ۲.۵ گرم",
    6:  "شمش طلا طلاملا ۵ گرم",
    7:  "شمش طلا طلاملا ۱۰ گرم",
    8:  "شمش طلا طلاملا ۲۰ گرم",
    9:  "شمش طلا طلاملا ۱ اونس",
    10: "شمش طلا طلاملا ۵۰ گرم",
    11: "شمش طلا طلاملا ۱۰۰ گرم",
    # Gold Investment (شمش طلا سرمایه‌ای / بدون بسته‌بندی)
    16: "شمش طلا سرمایه‌ای ۱۰۰ سوت",
    17: "شمش طلا سرمایه‌ای ۲۰۰ سوت",
    18: "شمش طلا سرمایه‌ای ۵۰۰ سوت",
    19: "شمش طلا سرمایه‌ای ۱ گرم",
    20: "شمش طلا سرمایه‌ای ۲.۵ گرم",
    21: "شمش طلا سرمایه‌ای ۵ گرم",
    22: "شمش طلا سرمایه‌ای ۱۰ گرم",
    23: "شمش طلا سرمایه‌ای ۲۰ گرم",
    24: "شمش طلا سرمایه‌ای ۱۰۰ گرم",
    25: "شمش طلا سرمایه‌ای ۵۰ گرم",
    26: "شمش طلا سرمایه‌ای ۱ اونس",
    # Silver TalaMala (شمش نقره با بسته‌بندی)
    27: "شمش نقره طلاملا ۱۰۰ سوت",
}

# Old product IDs to SKIP (inactive/test)
SKIP_PRODUCT_IDS = {12, 13, 14, 15}

# Customers to import (owners of sold bars on real products)
OLD_CUSTOMERS_TO_IMPORT = {
    14: {"mobile": "09122973972", "first_name": "User", "last_name": "New", "national_id": "0072349743"},
    32: {"mobile": "09111274851", "first_name": "User", "last_name": "Guest", "national_id": "GUEST_f1f7e107_09111274851"},
}

# Old batch to create in v4
OLD_BATCH = {"batch_number": "BATCH-20241203", "melt_number": "MELT-001", "operator": "محمد شمسی پور"}


def parse_bars_from_dump(dump_path: str) -> list[dict]:
    """Parse bar records from the plain-text SQL dump."""
    bars = []
    in_bars_section = False

    with open(dump_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            if line.startswith("COPY public.bars "):
                in_bars_section = True
                continue

            if in_bars_section:
                if line == "\\.":
                    break
                parts = line.split("\t")
                if len(parts) < 11:
                    continue

                bar_id = int(parts[0])
                serial_code = parts[1].strip()
                status = parts[2]
                product_id = int(parts[3]) if parts[3] != "\\N" else None
                customer_id = int(parts[4]) if parts[4] != "\\N" else None
                batch_id = int(parts[5]) if parts[5] != "\\N" else None
                created_at = parts[10]

                bars.append({
                    "old_id": bar_id,
                    "serial_code": serial_code,
                    "status": status,
                    "old_product_id": product_id,
                    "old_customer_id": customer_id,
                    "old_batch_id": batch_id,
                    "created_at": created_at,
                })

    return bars


def run_migration(apply: bool = False):
    dump_path = os.path.join(PROJECT_ROOT, "_private", "old_db_plain.sql")
    if not os.path.exists(dump_path):
        print(f"ERROR: Dump file not found: {dump_path}")
        print("Run pg_restore first to convert binary dump to plain text.")
        sys.exit(1)

    # Parse bars from dump
    print("Parsing old database dump...")
    all_bars = parse_bars_from_dump(dump_path)
    print(f"  Found {len(all_bars)} total bars in dump")

    # Filter: skip test/inactive products, skip Raw bars without product
    bars_to_migrate = []
    skipped_test = 0
    skipped_no_product = 0
    for bar in all_bars:
        if bar["old_product_id"] is None:
            skipped_no_product += 1
            continue
        if bar["old_product_id"] in SKIP_PRODUCT_IDS:
            skipped_test += 1
            continue
        if bar["old_product_id"] not in OLD_PRODUCT_TO_V4_NAME:
            print(f"  WARNING: Unknown product_id={bar['old_product_id']} for serial={bar['serial_code']}")
            continue
        bars_to_migrate.append(bar)

    print(f"  Bars to migrate: {len(bars_to_migrate)}")
    print(f"  Skipped (test product): {skipped_test}")
    print(f"  Skipped (no product): {skipped_no_product}")

    # Group by product for summary
    by_product = {}
    for bar in bars_to_migrate:
        pid = bar["old_product_id"]
        v4_name = OLD_PRODUCT_TO_V4_NAME[pid]
        by_product.setdefault(v4_name, []).append(bar)

    print("\n--- Migration Summary ---")
    for name, bar_list in sorted(by_product.items(), key=lambda x: len(x[1]), reverse=True):
        sold_count = sum(1 for b in bar_list if b["status"] == "Sold")
        extra = f" ({sold_count} sold)" if sold_count else ""
        print(f"  {name}: {len(bar_list)} bars{extra}")

    # Identify sold bars on real products
    sold_bars = [b for b in bars_to_migrate if b["status"] == "Sold"]
    if sold_bars:
        print(f"\n--- Sold Bars ({len(sold_bars)}) ---")
        for sb in sold_bars:
            cust = OLD_CUSTOMERS_TO_IMPORT.get(sb["old_customer_id"], {})
            print(f"  {sb['serial_code']} → {OLD_PRODUCT_TO_V4_NAME[sb['old_product_id']]} "
                  f"→ customer: {cust.get('mobile', 'UNKNOWN')} (old_id={sb['old_customer_id']})")

    if not apply:
        print("\n*** DRY RUN — no changes made. Use --apply to insert into database. ***")
        return

    # --- Actually apply to database ---
    print("\n--- Applying migration to database ---")
    with engine.connect() as conn:
        # 1. Build v4 product name → id mapping
        print("Loading v4 products...")
        rows = conn.execute(text("SELECT id, name FROM products")).fetchall()
        v4_product_map = {row[1]: row[0] for row in rows}

        # Verify all needed products exist
        missing = set()
        for pid, v4_name in OLD_PRODUCT_TO_V4_NAME.items():
            if v4_name not in v4_product_map:
                missing.add(v4_name)
        if missing:
            print(f"ERROR: These v4 products don't exist (run seed.py --reset first):")
            for m in missing:
                print(f"  - {m}")
            sys.exit(1)
        print(f"  {len(v4_product_map)} products loaded")

        # 2. Create or find the old batch
        row = conn.execute(text(
            "SELECT id FROM batches WHERE batch_number = :bn"
        ), {"bn": OLD_BATCH["batch_number"]}).fetchone()
        if row:
            batch_id = row[0]
            print(f"  Batch exists: {OLD_BATCH['batch_number']} (id={batch_id})")
        else:
            result = conn.execute(text(
                "INSERT INTO batches (batch_number, melt_number, operator) "
                "VALUES (:bn, :mn, :op) RETURNING id"
            ), {"bn": OLD_BATCH["batch_number"], "mn": OLD_BATCH["melt_number"], "op": OLD_BATCH["operator"]})
            batch_id = result.fetchone()[0]
            print(f"  Created batch: {OLD_BATCH['batch_number']} (id={batch_id})")

        # 3. Create customers for sold bars
        customer_id_map = {}  # old_customer_id → new_customer_id
        for old_cid, cust_data in OLD_CUSTOMERS_TO_IMPORT.items():
            row = conn.execute(text(
                "SELECT id FROM customers WHERE mobile = :m"
            ), {"m": cust_data["mobile"]}).fetchone()
            if row:
                customer_id_map[old_cid] = row[0]
                print(f"  Customer exists: {cust_data['mobile']} (id={row[0]})")
            else:
                result = conn.execute(text(
                    "INSERT INTO customers (first_name, last_name, national_id, mobile, is_active) "
                    "VALUES (:fn, :ln, :nid, :mob, true) RETURNING id"
                ), {
                    "fn": cust_data["first_name"],
                    "ln": cust_data["last_name"],
                    "nid": cust_data["national_id"],
                    "mob": cust_data["mobile"],
                })
                new_id = result.fetchone()[0]
                customer_id_map[old_cid] = new_id
                print(f"  Created customer: {cust_data['mobile']} (id={new_id})")

        # 4. Get existing serial codes to skip duplicates
        existing_serials = set()
        rows = conn.execute(text("SELECT serial_code FROM bars")).fetchall()
        for row in rows:
            existing_serials.add(row[0])
        print(f"  Existing bars in DB: {len(existing_serials)}")

        # 5. Insert bars
        print(f"\nInserting {len(bars_to_migrate)} bars...")
        inserted = 0
        skipped_dup = 0
        for bar in bars_to_migrate:
            if bar["serial_code"] in existing_serials:
                skipped_dup += 1
                continue

            v4_name = OLD_PRODUCT_TO_V4_NAME[bar["old_product_id"]]
            v4_product_id = v4_product_map[v4_name]

            # Map customer for sold bars
            new_customer_id = None
            if bar["status"] == "Sold" and bar["old_customer_id"] in customer_id_map:
                new_customer_id = customer_id_map[bar["old_customer_id"]]

            conn.execute(text(
                "INSERT INTO bars (serial_code, status, product_id, batch_id, customer_id) "
                "VALUES (:sc, :st, :pid, :bid, :cid)"
            ), {
                "sc": bar["serial_code"],
                "st": bar["status"],
                "pid": v4_product_id,
                "bid": batch_id,
                "cid": new_customer_id,
            })
            inserted += 1

        conn.commit()

        print(f"\n=== Migration Complete ===")
        print(f"  Bars inserted: {inserted}")
        print(f"  Bars skipped (duplicate serial): {skipped_dup}")
        print(f"  Batch: {OLD_BATCH['batch_number']}")
        print(f"  Customers created/mapped: {len(customer_id_map)}")


if __name__ == "__main__":
    apply_flag = "--apply" in sys.argv
    run_migration(apply=apply_flag)
