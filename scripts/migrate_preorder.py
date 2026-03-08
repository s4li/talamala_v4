"""
Migration: Pre-order / Central Warehouse Feature
====================================================
Run on production server AFTER git pull:
    cd /path/to/talamala_v4
    source env/bin/activate
    python scripts/migrate_preorder.py

Idempotent: safe to run multiple times. Already-applied steps are skipped.

What it does:
1. Adds is_central_warehouse column to users table
2. Adds is_preorder column to bars table
3. Adds preorder_delivery_days to system_settings
4. Marks existing bars with dealer_id=NULL as needing attention (report only)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from config.database import SessionLocal


def col_exists(db, table, column):
    """Check if a column exists in a table."""
    r = db.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return r.scalar() > 0


def setting_exists(db, key):
    """Check if a system setting exists."""
    r = db.execute(text(
        "SELECT COUNT(*) FROM system_settings WHERE key = :k"
    ), {"k": key})
    return r.scalar() > 0


def run():
    db = SessionLocal()
    step = 0
    total = 5
    ok = True

    def log(msg, status="OK"):
        nonlocal step
        step += 1
        print(f"  [{step:2d}/{total}] {status:4s}  {msg}")

    def skip(msg):
        nonlocal step
        step += 1
        print(f"  [{step:2d}/{total}] SKIP  {msg}  (already done)")

    print("=" * 60)
    print("  Migration: Pre-order / Central Warehouse")
    print("=" * 60)

    try:
        # 1. Add is_central_warehouse to users
        if not col_exists(db, "users", "is_central_warehouse"):
            db.execute(text(
                "ALTER TABLE users ADD COLUMN is_central_warehouse BOOLEAN NOT NULL DEFAULT false"
            ))
            log("Add users.is_central_warehouse column")
        else:
            skip("users.is_central_warehouse")

        # 2. Add is_preorder to bars
        if not col_exists(db, "bars", "is_preorder"):
            db.execute(text(
                "ALTER TABLE bars ADD COLUMN is_preorder BOOLEAN NOT NULL DEFAULT false"
            ))
            log("Add bars.is_preorder column")
        else:
            skip("bars.is_preorder")

        # 3. Create partial index for preorder bars (performance)
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_bars_is_preorder ON bars (is_preorder) WHERE is_preorder = true"
        ))
        log("Create partial index ix_bars_is_preorder")

        # 4. Add preorder_delivery_days setting
        if not setting_exists(db, "preorder_delivery_days"):
            db.execute(text("""
                INSERT INTO system_settings (key, value, description)
                VALUES (
                    'preorder_delivery_days',
                    :val,
                    :desc
                )
            """), {
                "val": "\u06F3 \u062A\u0627 \u06F5 \u0631\u0648\u0632 \u06A9\u0627\u0631\u06CC",
                "desc": "\u0632\u0645\u0627\u0646 \u062A\u062D\u0648\u06CC\u0644 \u0634\u0645\u0634 \u067E\u06CC\u0634\u200C\u0633\u0641\u0627\u0631\u0634 - \u062F\u0631 \u0635\u0641\u062D\u0647 \u062A\u0633\u0648\u06CC\u0647 \u0646\u0645\u0627\u06CC\u0634 \u062F\u0627\u062F\u0647 \u0645\u06CC\u200C\u0634\u0648\u062F",
            })
            log("Add preorder_delivery_days setting")
        else:
            skip("preorder_delivery_days setting")

        # 5. Report orphan bars (dealer_id=NULL with status != RAW)
        orphan_count = db.execute(text(
            "SELECT COUNT(*) FROM bars WHERE dealer_id IS NULL AND status != 'RAW'"
        )).scalar()
        if orphan_count > 0:
            log(
                f"Found {orphan_count} orphan bars (dealer_id=NULL, status!=RAW) — "
                "assign them to a dealer via admin panel",
                status="WARN"
            )
        else:
            log("No orphan bars found")

        # --- Commit ---
        db.commit()
        print(f"\n  COMMIT — all {step} steps completed.")

    except Exception as e:
        db.rollback()
        print(f"\n  FAIL at step {step}: {e}")
        print("  ROLLBACK — no changes applied.")
        ok = False

    # --- Verification (outside transaction) ---
    if ok:
        print("\n" + "=" * 60)
        print("  Verification")
        print("=" * 60)

        checks = [
            ("users.is_central_warehouse exists", True,
             "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='users' AND column_name='is_central_warehouse'"),
            ("bars.is_preorder exists", True,
             "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='bars' AND column_name='is_preorder'"),
            ("preorder_delivery_days setting", True,
             "SELECT COUNT(*) FROM system_settings WHERE key='preorder_delivery_days'"),
            ("Central warehouse dealers", None,
             "SELECT COUNT(*) FROM users WHERE is_central_warehouse = true"),
            ("Preorder bars", None,
             "SELECT COUNT(*) FROM bars WHERE is_preorder = true"),
            ("Orphan bars (dealer_id=NULL, status!=RAW)", None,
             "SELECT COUNT(*) FROM bars WHERE dealer_id IS NULL AND status != 'RAW'"),
            ("Total bars", None,
             "SELECT COUNT(*) FROM bars"),
        ]

        all_pass = True
        for label, expect_positive, sql in checks:
            try:
                val = db.execute(text(sql)).scalar()
                if expect_positive is True:
                    status = "PASS" if val > 0 else "FAIL"
                elif expect_positive is False:
                    status = "PASS" if val == 0 else "WARN"
                else:
                    status = "INFO"
                if status in ("FAIL", "WARN"):
                    all_pass = False
                print(f"  [{status}] {label}: {val}")
            except Exception as e:
                print(f"  [FAIL] {label}: {e}")
                all_pass = False

        print("\n" + "=" * 60)
        if all_pass:
            print("  ALL CHECKS PASSED")
        else:
            print("  SOME CHECKS NEED ATTENTION (see WARN/FAIL above)")
        print("=" * 60)

        print("\n  Next steps:")
        print("  1. Create a 'factory' dealer in admin panel (check 'central warehouse')")
        print("  2. Use 'Pre-order' button in bar management to create preorder bars")
        print("  3. If orphan bars exist, assign them to a dealer via admin panel")

    db.close()
    return ok


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
