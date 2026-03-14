"""
Migration: Unified Dealer Checkout + Shahkar Fields
=====================================================
Adds shahkar_verified columns to users table (was in old Customer model but
missing from unified User model).

NOTE: The dealer gold-for-gold columns (orders, order_items, accounts, dealer_tiers)
should already exist from migrate_dealer_gold.py. This script re-checks them
with IF NOT EXISTS for safety.

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
        print("Migration: Unified Dealer Checkout + Shahkar")
        print("=" * 60)

        # ==========================================
        # 1. Users: shahkar_verified fields
        # ==========================================
        print("\n[1/2] Adding shahkar fields to users...")
        user_cols = [
            ("shahkar_verified", "BOOLEAN NOT NULL DEFAULT false"),
            ("shahkar_verified_at", "TIMESTAMPTZ DEFAULT NULL"),
        ]
        for col_name, col_def in user_cols:
            try:
                conn.execute(text(f"""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS
                    {col_name} {col_def}
                """))
                print(f"  -> {col_name} added (or already exists)")
            except Exception as e:
                print(f"  -> Note ({col_name}): {e}")

        # ==========================================
        # 2. Safety re-check: dealer gold columns
        # ==========================================
        print("\n[2/2] Safety check: dealer gold columns...")
        safety_checks = [
            ("accounts", "credit_limit_mg", "BIGINT DEFAULT 0 NOT NULL"),
            ("dealer_tiers", "default_credit_limit_mg", "BIGINT DEFAULT 0 NOT NULL"),
            ("users", "custom_credit_limit_mg", "BIGINT DEFAULT NULL"),
            ("orders", "payment_asset_code", "VARCHAR(10) DEFAULT NULL"),
            ("orders", "gold_total_mg", "BIGINT DEFAULT NULL"),
            ("orders", "delivery_otp_hash", "VARCHAR DEFAULT NULL"),
            ("orders", "delivery_otp_expiry", "TIMESTAMPTZ DEFAULT NULL"),
            ("order_items", "gold_cost_mg", "BIGINT DEFAULT NULL"),
            ("order_items", "applied_dealer_wage_percent", "NUMERIC(5,2) DEFAULT NULL"),
        ]
        for tbl, col, defn in safety_checks:
            try:
                conn.execute(text(f"""
                    ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {defn}
                """))
                print(f"  -> {tbl}.{col} OK")
            except Exception as e:
                print(f"  -> Note ({tbl}.{col}): {e}")

        # ==========================================
        # Commit
        # ==========================================
        print("\nCommitting...")
        conn.execute(text("COMMIT"))
        print("Done!")

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. git pull")
        print("  2. python scripts/migrate_unified_checkout.py")
        print("  3. systemctl restart talamala")


if __name__ == "__main__":
    run_migration()
