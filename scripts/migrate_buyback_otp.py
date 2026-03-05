"""
Migration: Buyback OTP rewrite + hedging involved_user_id
==========================================================
Run: python scripts/migrate_buyback_otp.py

Changes:
  1. buyback_requests: add otp_hash, otp_expiry, seller_national_id, seller_user_id, is_owner
  2. position_ledger: add involved_user_id
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import engine
from sqlalchemy import text

# (table_name, column_name, ALTER SQL)
MIGRATIONS = [
    ("buyback_requests", "otp_hash", "ALTER TABLE buyback_requests ADD COLUMN otp_hash VARCHAR"),
    ("buyback_requests", "otp_expiry", "ALTER TABLE buyback_requests ADD COLUMN otp_expiry TIMESTAMP WITH TIME ZONE"),
    ("buyback_requests", "seller_national_id", "ALTER TABLE buyback_requests ADD COLUMN seller_national_id VARCHAR"),
    ("buyback_requests", "seller_user_id", "ALTER TABLE buyback_requests ADD COLUMN seller_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"),
    ("buyback_requests", "is_owner", "ALTER TABLE buyback_requests ADD COLUMN is_owner BOOLEAN NOT NULL DEFAULT FALSE"),
    ("position_ledger", "involved_user_id", "ALTER TABLE position_ledger ADD COLUMN involved_user_id INTEGER REFERENCES users(id)"),
]


def get_existing_columns(conn, table_name):
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :tbl"
    ), {"tbl": table_name})
    return {row[0] for row in result}


def run():
    with engine.connect() as conn:
        applied = 0
        tables_checked = {}

        for table_name, col_name, sql in MIGRATIONS:
            if table_name not in tables_checked:
                tables_checked[table_name] = get_existing_columns(conn, table_name)
                print(f"[INFO] {table_name}: {len(tables_checked[table_name])} columns exist")

            if col_name in tables_checked[table_name]:
                print(f"[SKIP] {table_name}.{col_name} already exists")
                continue
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[OK]   Added {table_name}.{col_name}")
                applied += 1
            except Exception as e:
                conn.rollback()
                print(f"[ERR]  Failed to add {table_name}.{col_name}: {e}")
                return False

        if applied == 0:
            print("\n[INFO] All columns already exist — nothing to do.")
        else:
            print(f"\n[OK] {applied} column(s) added successfully.")
        return True


if __name__ == "__main__":
    print("=" * 50)
    print("Buyback OTP + Hedging Migration")
    print("=" * 50)
    success = run()
    sys.exit(0 if success else 1)
