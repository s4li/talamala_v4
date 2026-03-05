"""
TalaMala v4 - Hedging Ledger: Add involved_user_id Column
============================================================
Safe migration script for PRODUCTION database.

Adds involved_user_id column to position_ledger table to track
which customer/dealer was involved in each hedging operation.

Usage:
    python scripts/migrate_hedging_involved_user.py

Safety:
    - Only adds column IF NOT EXISTS
    - Never drops/alters existing data
    - Full rollback on any error
"""

import sys
import os
import io

# Fix console encoding for Persian text
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from config.database import engine


def log(msg: str, level: str = "INFO"):
    prefix = {"INFO": "[INFO]", "OK": "[ OK ]", "SKIP": "[SKIP]", "WARN": "[WARN]", "ERR": "[ERR ]"}
    print(f"  {prefix.get(level, '[???]')} {msg}")


def main():
    print("=" * 60)
    print("  Hedging Ledger: Add involved_user_id Column")
    print("=" * 60)

    conn = engine.connect()
    trans = conn.begin()

    try:
        # Check connection
        result = conn.execute(text("SELECT current_database(), current_user"))
        row = result.fetchone()
        print(f"\n  Database: {row[0]}")
        print(f"  User:     {row[1]}\n")

        # Check if column already exists
        result = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'position_ledger'
              AND column_name = 'involved_user_id'
        """))

        if result.fetchone():
            log("Column 'involved_user_id' already exists in position_ledger", "SKIP")
        else:
            # Add the column
            conn.execute(text("""
                ALTER TABLE position_ledger
                ADD COLUMN involved_user_id INTEGER REFERENCES users(id)
            """))
            log("Added column: position_ledger.involved_user_id (FK -> users.id)", "OK")

        # Commit
        trans.commit()
        print("\n  >>> All changes committed successfully <<<")

        # Verify
        conn2 = engine.connect()
        try:
            result = conn2.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'position_ledger'
                  AND column_name = 'involved_user_id'
            """))
            row = result.fetchone()
            if row:
                log(f"Verified: {row[0]} ({row[1]}, nullable={row[2]})", "OK")
            else:
                log("Column NOT FOUND after migration!", "ERR")
        finally:
            conn2.close()

        print("\n" + "=" * 60)
        print("  Migration completed successfully!")
        print("=" * 60)
        print("\n  Next steps:")
        print("  1. Restart the application: systemctl restart talamala")
        print()

    except Exception as e:
        trans.rollback()
        print(f"\n  [ERR ] Migration FAILED - all changes rolled back!")
        print(f"  [ERR ] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
