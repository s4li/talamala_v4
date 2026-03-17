"""
Migration: Unified Dealer Checkout + All Missing Columns
=========================================================
Comprehensive migration that adds ALL columns needed by the current codebase
that may be missing from the production database.

Safe to run multiple times (IF NOT EXISTS / idempotent).

Run on production server:
    python scripts/migrate_unified_checkout.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import engine
from sqlalchemy import text


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
            try:
                conn.execute(text(f"""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS
                    {col_name} {col_def}
                """))
                print(f"  -> {col_name} OK")
            except Exception as e:
                print(f"  -> Note ({col_name}): {e}")

        # ==========================================
        # 2. Bars table: new columns
        # ==========================================
        print("\n[2/7] Bars table columns...")
        try:
            conn.execute(text("""
                ALTER TABLE bars ADD COLUMN IF NOT EXISTS
                is_preorder BOOLEAN NOT NULL DEFAULT false
            """))
            print("  -> is_preorder OK")
        except Exception as e:
            print(f"  -> Note: {e}")

        # ==========================================
        # 3. Accounts + Dealer Tiers: credit system
        # ==========================================
        print("\n[3/7] Credit system columns...")
        credit_cols = [
            ("accounts", "credit_limit_mg", "BIGINT DEFAULT 0 NOT NULL"),
            ("dealer_tiers", "default_credit_limit_mg", "BIGINT DEFAULT 0 NOT NULL"),
        ]
        for tbl, col, defn in credit_cols:
            try:
                conn.execute(text(f"""
                    ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {defn}
                """))
                print(f"  -> {tbl}.{col} OK")
            except Exception as e:
                print(f"  -> Note: {e}")

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
            try:
                conn.execute(text(f"""
                    ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col} {defn}
                """))
                print(f"  -> orders.{col} OK")
            except Exception as e:
                print(f"  -> Note: {e}")

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
            try:
                conn.execute(text(f"""
                    ALTER TABLE order_items ADD COLUMN IF NOT EXISTS {col} {defn}
                """))
                print(f"  -> order_items.{col} OK")
            except Exception as e:
                print(f"  -> Note: {e}")

        # Fix applied_package_price: make nullable with default 0
        try:
            conn.execute(text("""
                ALTER TABLE order_items ALTER COLUMN applied_package_price SET DEFAULT 0
            """))
            conn.execute(text("""
                ALTER TABLE order_items ALTER COLUMN applied_package_price DROP NOT NULL
            """))
            print("  -> order_items.applied_package_price: nullable + default=0")
        except Exception as e:
            print(f"  -> Note (applied_package_price fix): {e}")

        # ==========================================
        # 6. Cart Items: gift box
        # ==========================================
        print("\n[6/7] Cart Items columns...")
        try:
            conn.execute(text("""
                ALTER TABLE cart_items ADD COLUMN IF NOT EXISTS
                gift_box_id INTEGER DEFAULT NULL REFERENCES gift_boxes(id)
            """))
            print("  -> cart_items.gift_box_id OK")
        except Exception as e:
            print(f"  -> Note: {e}")

        # ==========================================
        # 7. Constraints + Tier defaults
        # ==========================================
        print("\n[7/7] Constraints + defaults...")

        # Drop old constraints
        for old in ["ck_account_balance_nonneg", "ck_account_credit_nonneg"]:
            try:
                conn.execute(text(f"ALTER TABLE accounts DROP CONSTRAINT IF EXISTS {old}"))
                print(f"  -> Dropped {old}")
            except Exception as e:
                print(f"  -> Note: {e}")

        # Add new credit constraint (check first to avoid transaction abort)
        has_constraint = conn.execute(text("""
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'accounts'::regclass
            AND conname = 'ck_account_balance_with_credit'
        """)).fetchone()
        if has_constraint:
            print("  -> ck_account_balance_with_credit already exists")
        else:
            conn.execute(text("""
                ALTER TABLE accounts ADD CONSTRAINT ck_account_balance_with_credit
                CHECK (balance >= -credit_limit_mg)
            """))
            print("  -> Added: balance >= -credit_limit_mg")

        # Set default credit limits for dealer tiers
        tier_credits = [
            ("distributor", 500000),   # 500g
            ("wholesaler", 250000),    # 250g
            ("store", 100000),         # 100g
            ("end_customer", 0),
        ]
        for slug, mg in tier_credits:
            try:
                conn.execute(text(f"""
                    UPDATE dealer_tiers SET default_credit_limit_mg = {mg}
                    WHERE slug = :slug AND default_credit_limit_mg = 0
                """), {"slug": slug})
                print(f"  -> {slug}: {mg/1000}g")
            except Exception as e:
                print(f"  -> Note ({slug}): {e}")

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
        print("  3. sudo systemctl restart talamala")
        print("  4. Verify: Admin > Dealers > Tiers (credit limits)")


if __name__ == "__main__":
    run_migration()
