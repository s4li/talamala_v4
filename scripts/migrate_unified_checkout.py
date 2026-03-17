"""
Migration: Unified Dealer Checkout + All Missing Columns
=========================================================
Comprehensive migration that adds ALL columns needed by the current codebase
that may be missing from the production database.

Safe to run multiple times (IF NOT EXISTS / idempotent).
Each step uses SAVEPOINT so one failure doesn't abort the rest.

Run on production server:
    source ../env1/bin/activate
    python scripts/migrate_unified_checkout.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import engine
from sqlalchemy import text


def safe_execute(conn, sql, label):
    """Execute SQL inside a SAVEPOINT so failures don't abort the transaction."""
    try:
        conn.execute(text("SAVEPOINT sp"))
        conn.execute(text(sql))
        conn.execute(text("RELEASE SAVEPOINT sp"))
        print(f"  -> {label} OK")
        return True
    except Exception as e:
        conn.execute(text("ROLLBACK TO SAVEPOINT sp"))
        msg = str(e).split("\n")[0]
        if "already exists" in msg or "does not exist" in msg:
            print(f"  -> {label} (skipped: {msg[:80]})")
        else:
            print(f"  -> {label} NOTE: {msg[:100]}")
        return False


def column_exists(conn, table, column):
    """Check if a column exists in a table."""
    result = conn.execute(text(
        f"SELECT 1 FROM information_schema.columns "
        f"WHERE table_name='{table}' AND column_name='{column}'"
    )).fetchone()
    return result is not None


def constraint_exists(conn, table, constraint_name):
    """Check if a constraint exists."""
    result = conn.execute(text(
        f"SELECT 1 FROM pg_constraint "
        f"WHERE conrelid = '{table}'::regclass AND conname = '{constraint_name}'"
    )).fetchone()
    return result is not None


def run_migration():
    with engine.connect() as conn:
        print("=" * 60)
        print("Migration: Comprehensive Schema Sync")
        print("=" * 60)

        # ==========================================
        # 1. Users table: new columns
        # ==========================================
        print("\n[1/7] Users table columns...")
        user_cols = [
            ("shahkar_verified", "BOOLEAN NOT NULL DEFAULT false"),
            ("shahkar_verified_at", "TIMESTAMPTZ DEFAULT NULL"),
            ("custom_credit_limit_mg", "BIGINT DEFAULT NULL"),
            ("is_central_warehouse", "BOOLEAN NOT NULL DEFAULT false"),
        ]
        for col_name, col_def in user_cols:
            safe_execute(conn,
                f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_def}",
                col_name)

        # ==========================================
        # 2. Bars table: new columns
        # ==========================================
        print("\n[2/7] Bars table columns...")
        safe_execute(conn,
            "ALTER TABLE bars ADD COLUMN IF NOT EXISTS is_preorder BOOLEAN NOT NULL DEFAULT false",
            "is_preorder")

        # ==========================================
        # 3. Accounts + Dealer Tiers: credit system
        # ==========================================
        print("\n[3/7] Credit system columns...")
        safe_execute(conn,
            "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS credit_limit_mg BIGINT DEFAULT 0 NOT NULL",
            "accounts.credit_limit_mg")
        safe_execute(conn,
            "ALTER TABLE dealer_tiers ADD COLUMN IF NOT EXISTS default_credit_limit_mg BIGINT DEFAULT 0 NOT NULL",
            "dealer_tiers.default_credit_limit_mg")

        # ==========================================
        # 4. Orders table: gold-for-gold fields
        # ==========================================
        print("\n[4/7] Orders table columns...")
        order_cols = [
            ("payment_asset_code", "VARCHAR(10) DEFAULT NULL"),
            ("gold_total_mg", "BIGINT DEFAULT NULL"),
            ("delivery_otp_hash", "VARCHAR DEFAULT NULL"),
            ("delivery_otp_expiry", "TIMESTAMPTZ DEFAULT NULL"),
        ]
        for col, defn in order_cols:
            safe_execute(conn,
                f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col} {defn}",
                f"orders.{col}")

        # ==========================================
        # 5. Order Items: gold + gift box fields
        # ==========================================
        print("\n[5/7] Order Items columns...")
        oi_cols = [
            ("gold_cost_mg", "BIGINT DEFAULT NULL"),
            ("applied_dealer_wage_percent", "NUMERIC(5,2) DEFAULT NULL"),
            ("gift_box_id", "INTEGER DEFAULT NULL REFERENCES gift_boxes(id)"),
            ("applied_gift_box_price", "BIGINT DEFAULT 0"),
        ]
        for col, defn in oi_cols:
            safe_execute(conn,
                f"ALTER TABLE order_items ADD COLUMN IF NOT EXISTS {col} {defn}",
                f"order_items.{col}")

        # Fix applied_package_price if it exists
        if column_exists(conn, "order_items", "applied_package_price"):
            safe_execute(conn,
                "ALTER TABLE order_items ALTER COLUMN applied_package_price SET DEFAULT 0",
                "applied_package_price default=0")
            safe_execute(conn,
                "ALTER TABLE order_items ALTER COLUMN applied_package_price DROP NOT NULL",
                "applied_package_price nullable")
        else:
            print("  -> applied_package_price: column doesn't exist (skip)")

        # ==========================================
        # 6. Cart Items: gift box
        # ==========================================
        print("\n[6/7] Cart Items columns...")
        safe_execute(conn,
            "ALTER TABLE cart_items ADD COLUMN IF NOT EXISTS gift_box_id INTEGER DEFAULT NULL REFERENCES gift_boxes(id)",
            "cart_items.gift_box_id")

        # ==========================================
        # 7. Constraints + Tier defaults
        # ==========================================
        print("\n[7/7] Constraints + defaults...")

        # Drop old constraints
        safe_execute(conn,
            "ALTER TABLE accounts DROP CONSTRAINT IF EXISTS ck_account_balance_nonneg",
            "drop ck_account_balance_nonneg")
        safe_execute(conn,
            "ALTER TABLE accounts DROP CONSTRAINT IF EXISTS ck_account_credit_nonneg",
            "drop ck_account_credit_nonneg")

        # Add new credit constraint
        if constraint_exists(conn, "accounts", "ck_account_balance_with_credit"):
            print("  -> ck_account_balance_with_credit already exists")
        else:
            safe_execute(conn,
                "ALTER TABLE accounts ADD CONSTRAINT ck_account_balance_with_credit CHECK (balance >= -credit_limit_mg)",
                "add ck_account_balance_with_credit")

        # Set default credit limits for dealer tiers
        tier_credits = [
            ("distributor", 500000),   # 500g
            ("wholesaler", 250000),    # 250g
            ("store", 100000),         # 100g
            ("end_customer", 0),
        ]
        for slug, mg in tier_credits:
            safe_execute(conn,
                f"UPDATE dealer_tiers SET default_credit_limit_mg = {mg} WHERE slug = '{slug}' AND default_credit_limit_mg = 0",
                f"{slug}: {mg/1000}g")

        # ==========================================
        # Commit
        # ==========================================
        print("\nCommitting...")
        conn.execute(text("COMMIT"))
        print("Done!")

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print("\nDeploy steps:")
        print("  1. git pull")
        print("  2. python scripts/migrate_unified_checkout.py")
        print("  3. sudo systemctl restart talamala_v4")


if __name__ == "__main__":
    run_migration()
