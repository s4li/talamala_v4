"""
Migration: Add OTP + seller fields to buyback_requests table
=============================================================
Run: python scripts/migrate_buyback_otp.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import engine
from sqlalchemy import text

MIGRATIONS = [
    ("otp_hash", "ALTER TABLE buyback_requests ADD COLUMN otp_hash VARCHAR"),
    ("otp_expiry", "ALTER TABLE buyback_requests ADD COLUMN otp_expiry TIMESTAMP WITH TIME ZONE"),
    ("seller_national_id", "ALTER TABLE buyback_requests ADD COLUMN seller_national_id VARCHAR"),
    ("seller_user_id", "ALTER TABLE buyback_requests ADD COLUMN seller_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"),
    ("is_owner", "ALTER TABLE buyback_requests ADD COLUMN is_owner BOOLEAN NOT NULL DEFAULT FALSE"),
]


def run():
    with engine.connect() as conn:
        # Check which columns already exist
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'buyback_requests'"
        ))
        existing = {row[0] for row in result}
        print(f"[INFO] Existing columns: {sorted(existing)}")

        applied = 0
        for col_name, sql in MIGRATIONS:
            if col_name in existing:
                print(f"[SKIP] Column '{col_name}' already exists")
                continue
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[OK]   Added column '{col_name}'")
                applied += 1
            except Exception as e:
                conn.rollback()
                print(f"[ERR]  Failed to add '{col_name}': {e}")
                return False

        if applied == 0:
            print("\n[INFO] All columns already exist — nothing to do.")
        else:
            print(f"\n[OK] {applied} column(s) added successfully.")
        return True


if __name__ == "__main__":
    print("=" * 50)
    print("Buyback OTP Migration")
    print("=" * 50)
    success = run()
    sys.exit(0 if success else 1)
