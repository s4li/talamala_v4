"""
Fix Orphan Bars: Assign to Central Warehouse as Pre-order
==========================================================
Run on production server AFTER migrate_preorder.py:
    cd /path/to/talamala_v4
    source env/bin/activate
    python scripts/fix_orphan_bars.py

Idempotent: safe to run multiple times. Already-fixed bars are skipped.

What it does:
1. Finds the central warehouse dealer (is_central_warehouse=True)
2. Counts orphan bars (dealer_id=NULL, status != RAW)
3. Assigns them to central warehouse + marks is_preorder=True
4. Verifies results
"""

import sys
import os
import io

# Fix Windows encoding for Persian output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from config.database import SessionLocal


def run():
    db = SessionLocal()
    ok = True

    print("=" * 60)
    print("  Fix Orphan Bars → Central Warehouse (Pre-order)")
    print("=" * 60)

    try:
        # 1. Find central warehouse dealer
        cw = db.execute(text(
            "SELECT id, first_name, last_name, mobile "
            "FROM users "
            "WHERE is_dealer = true AND is_central_warehouse = true AND is_active = true "
            "LIMIT 1"
        )).fetchone()

        if not cw:
            print("\n  [FAIL] No active central warehouse dealer found!")
            print("  Create one first: Admin → Dealers → New → check 'Central Warehouse'")
            db.close()
            return False

        cw_id = cw[0]
        cw_name = f"{cw[1]} {cw[2]}" if cw[1] and cw[2] else cw[3]
        print(f"\n  [1/4] Central warehouse: {cw_name} (id={cw_id})")

        # 2. Count orphan bars (before fix)
        orphan_count = db.execute(text(
            "SELECT COUNT(*) FROM bars WHERE dealer_id IS NULL AND status != 'Raw'"
        )).scalar()
        print(f"  [2/4] Orphan bars found: {orphan_count}")

        if orphan_count == 0:
            print("\n  No orphan bars to fix. Everything is clean!")
            db.close()
            return True

        # 3. Show breakdown by status and product
        print("\n  Breakdown by status:")
        rows = db.execute(text(
            "SELECT status, COUNT(*) FROM bars "
            "WHERE dealer_id IS NULL AND status != 'Raw' "
            "GROUP BY status ORDER BY status"
        )).fetchall()
        for status, cnt in rows:
            print(f"    {status}: {cnt}")

        print("\n  Breakdown by product:")
        rows = db.execute(text(
            "SELECT COALESCE(p.name, 'No product'), COUNT(*) FROM bars b "
            "LEFT JOIN products p ON b.product_id = p.id "
            "WHERE b.dealer_id IS NULL AND b.status != 'Raw' "
            "GROUP BY p.name ORDER BY COUNT(*) DESC"
        )).fetchall()
        for pname, cnt in rows:
            print(f"    {pname}: {cnt}")

        # 4. Fix: assign to central warehouse + mark as preorder
        result = db.execute(text(
            "UPDATE bars SET dealer_id = :cw_id, is_preorder = true "
            "WHERE dealer_id IS NULL AND status != 'Raw'"
        ), {"cw_id": cw_id})
        fixed = result.rowcount
        print(f"\n  [3/4] Fixed {fixed} bars → dealer_id={cw_id}, is_preorder=true")

        # Commit
        db.commit()
        print(f"  [4/4] COMMIT — {fixed} bars updated.")

    except Exception as e:
        db.rollback()
        print(f"\n  [FAIL] Error: {e}")
        print("  ROLLBACK — no changes applied.")
        ok = False

    # --- Verification ---
    if ok:
        print("\n" + "=" * 60)
        print("  Verification")
        print("=" * 60)

        checks = [
            ("Remaining orphan bars (expect 0)",
             "SELECT COUNT(*) FROM bars WHERE dealer_id IS NULL AND status != 'Raw'",
             0),
            ("Bars at central warehouse",
             f"SELECT COUNT(*) FROM bars WHERE dealer_id = {cw_id}",
             None),
            ("Pre-order bars at central warehouse",
             f"SELECT COUNT(*) FROM bars WHERE dealer_id = {cw_id} AND is_preorder = true",
             None),
            ("Total bars in system",
             "SELECT COUNT(*) FROM bars",
             None),
            ("RAW bars (no dealer, OK)",
             "SELECT COUNT(*) FROM bars WHERE status = 'Raw'",
             None),
        ]

        all_pass = True
        for label, sql, expect in checks:
            try:
                val = db.execute(text(sql)).scalar()
                if expect is not None:
                    status = "PASS" if val == expect else "WARN"
                else:
                    status = "INFO"
                if status == "WARN":
                    all_pass = False
                print(f"  [{status}] {label}: {val}")
            except Exception as e:
                print(f"  [FAIL] {label}: {e}")
                all_pass = False

        print("\n" + "=" * 60)
        if all_pass:
            print("  ALL CHECKS PASSED")
        else:
            print("  SOME CHECKS NEED ATTENTION")
        print("=" * 60)

    db.close()
    return ok


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
