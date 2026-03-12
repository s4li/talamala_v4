"""
Migration: Dealer Gold-for-Gold System
=========================================
Adds credit limit to accounts, gold order fields to orders/order_items,
delivery OTP fields to orders, and credit limit settings to dealer tiers and users.

Run on production server:
    python scripts/migrate_dealer_gold.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import engine
from sqlalchemy import text


def run_migration():
    with engine.connect() as conn:
        print("=" * 60)
        print("Migration: Dealer Gold-for-Gold System")
        print("=" * 60)

        # ==========================================
        # 1. Account: credit_limit_mg
        # ==========================================
        print("\n[1/6] Adding credit_limit_mg to accounts...")
        try:
            conn.execute(text("""
                ALTER TABLE accounts ADD COLUMN IF NOT EXISTS
                credit_limit_mg BIGINT DEFAULT 0 NOT NULL
            """))
            print("  -> credit_limit_mg column added (or already exists)")
        except Exception as e:
            print(f"  -> Note: {e}")

        # Update CHECK constraint (drop old, add new)
        print("  -> Updating CHECK constraint...")
        try:
            conn.execute(text("""
                ALTER TABLE accounts DROP CONSTRAINT IF EXISTS ck_account_balance_nonneg
            """))
            print("  -> Old constraint dropped")
        except Exception as e:
            print(f"  -> Note (drop old): {e}")

        try:
            conn.execute(text("""
                ALTER TABLE accounts ADD CONSTRAINT ck_account_balance_with_credit
                CHECK (balance >= -credit_limit_mg)
            """))
            print("  -> New constraint added: balance >= -credit_limit_mg")
        except Exception as e:
            print(f"  -> Note (add new): {e}")

        # ==========================================
        # 2. DealerTier: default_credit_limit_mg
        # ==========================================
        print("\n[2/6] Adding default_credit_limit_mg to dealer_tiers...")
        try:
            conn.execute(text("""
                ALTER TABLE dealer_tiers ADD COLUMN IF NOT EXISTS
                default_credit_limit_mg BIGINT DEFAULT 0 NOT NULL
            """))
            print("  -> default_credit_limit_mg column added (or already exists)")
        except Exception as e:
            print(f"  -> Note: {e}")

        # ==========================================
        # 3. User: custom_credit_limit_mg
        # ==========================================
        print("\n[3/6] Adding custom_credit_limit_mg to users...")
        try:
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS
                custom_credit_limit_mg BIGINT DEFAULT NULL
            """))
            print("  -> custom_credit_limit_mg column added (or already exists)")
        except Exception as e:
            print(f"  -> Note: {e}")

        # ==========================================
        # 4. Order: gold fields + delivery OTP
        # ==========================================
        print("\n[4/6] Adding gold order fields to orders...")
        order_cols = [
            ("payment_asset_code", "VARCHAR(10) DEFAULT NULL"),
            ("gold_total_mg", "BIGINT DEFAULT NULL"),
            ("delivery_otp_hash", "VARCHAR DEFAULT NULL"),
            ("delivery_otp_expiry", "TIMESTAMPTZ DEFAULT NULL"),
        ]
        for col_name, col_def in order_cols:
            try:
                conn.execute(text(f"""
                    ALTER TABLE orders ADD COLUMN IF NOT EXISTS
                    {col_name} {col_def}
                """))
                print(f"  -> {col_name} added (or already exists)")
            except Exception as e:
                print(f"  -> Note ({col_name}): {e}")

        # ==========================================
        # 5. OrderItem: gold fields
        # ==========================================
        print("\n[5/6] Adding gold fields to order_items...")
        item_cols = [
            ("gold_cost_mg", "BIGINT DEFAULT NULL"),
            ("applied_dealer_wage_percent", "NUMERIC(5,2) DEFAULT NULL"),
        ]
        for col_name, col_def in item_cols:
            try:
                conn.execute(text(f"""
                    ALTER TABLE order_items ADD COLUMN IF NOT EXISTS
                    {col_name} {col_def}
                """))
                print(f"  -> {col_name} added (or already exists)")
            except Exception as e:
                print(f"  -> Note ({col_name}): {e}")

        # ==========================================
        # 6. Commit
        # ==========================================
        print("\n[6/6] Committing...")
        conn.execute(text("COMMIT"))
        print("  -> Done!")

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Restart the application: systemctl restart talamala")
        print("  2. Set credit limits for dealer tiers in Admin > Dealers > Tiers")
        print("  3. Optionally set custom credit limits per dealer in dealer edit form")


if __name__ == "__main__":
    run_migration()
