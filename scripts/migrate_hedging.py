"""
TalaMala v4 - Hedging Module Migration (Phase 17.5)
====================================================
Safe migration script for PRODUCTION database.

Creates hedging tables + seed data WITHOUT touching existing data.
Every operation is logged with detail.

Usage:
    python scripts/migrate_hedging.py

Safety:
    - Only creates NEW tables (IF NOT EXISTS)
    - Only inserts seed data if not already present (ON CONFLICT DO NOTHING)
    - Never drops/alters existing tables
    - Full logging of every operation
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

from sqlalchemy import text, inspect
from config.database import engine


HEDGING_TABLES = [
    "metal_positions",
    "position_ledger",
]

HEDGING_SETTINGS = [
    ("hedge_threshold_gold_mg", "50000", "Gold alert threshold (mg) - default 50g"),
    ("hedge_threshold_silver_mg", "500000", "Silver alert threshold (mg) - default 500g"),
    ("hedge_alert_enabled", "true", "Enable hedging threshold alerts"),
    ("hedge_alert_cooldown_minutes", "60", "Minimum minutes between threshold alerts"),
]


def log(msg: str, level: str = "INFO"):
    prefix = {"INFO": "[INFO]", "OK": "[ OK ]", "SKIP": "[SKIP]", "WARN": "[WARN]", "ERR": "[ERR ]"}
    print(f"  {prefix.get(level, '[???]')} {msg}")


def check_connection(conn):
    """Verify database connection and show current state."""
    print("=" * 60)
    print("  Hedging Module Migration (Phase 17.5)")
    print("=" * 60)

    result = conn.execute(text("SELECT current_database(), current_user, version()"))
    row = result.fetchone()
    print(f"\n  Database: {row[0]}")
    print(f"  User:     {row[1]}")
    print(f"  Server:   {row[2][:60]}...")

    result = conn.execute(text(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'public'"
    ))
    total_tables = result.scalar()
    print(f"  Existing tables: {total_tables}")
    print()


def check_existing_tables(conn):
    """Check which hedging tables already exist."""
    print("[1/5] Checking existing hedging tables...")

    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    already_exist = []
    need_create = []

    for table in HEDGING_TABLES:
        if table in existing:
            already_exist.append(table)
            log(f"Table '{table}' already exists", "SKIP")
        else:
            need_create.append(table)
            log(f"Table '{table}' needs creation", "INFO")

    return already_exist, need_create


def create_tables(conn, need_create):
    """Create hedging tables that don't exist yet."""
    print(f"\n[2/5] Creating tables ({len(need_create)} to create)...")

    if not need_create:
        log("All hedging tables already exist, nothing to create", "SKIP")
        return

    # -- metal_positions --
    if "metal_positions" in need_create:
        conn.execute(text("""
            CREATE TABLE metal_positions (
                id SERIAL PRIMARY KEY,
                metal_type VARCHAR(20) NOT NULL UNIQUE,
                balance_mg BIGINT NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        log("Created table: metal_positions", "OK")

    # -- position_ledger (depends on users) --
    if "position_ledger" in need_create:
        conn.execute(text("""
            CREATE TABLE position_ledger (
                id SERIAL PRIMARY KEY,
                metal_type VARCHAR(20) NOT NULL,
                direction VARCHAR(10) NOT NULL,
                amount_mg BIGINT NOT NULL,
                balance_after_mg BIGINT NOT NULL,
                source_type VARCHAR(50) NOT NULL,
                source_id VARCHAR(100),
                description TEXT,
                metal_price_per_gram BIGINT,
                recorded_by INTEGER REFERENCES users(id),
                idempotency_key VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        log("Created table: position_ledger", "OK")


def create_indexes(conn):
    """Create indexes (skip if already exist)."""
    print("\n[3/5] Creating indexes...")

    indexes = [
        ("ix_pos_ledger_metal_created", "position_ledger", "(metal_type, created_at)"),
        ("ix_pos_ledger_source", "position_ledger", "(source_type, source_id)"),
    ]

    # Get existing indexes
    result = conn.execute(text(
        "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
    ))
    existing_indexes = {row[0] for row in result.fetchall()}

    for idx_name, table, columns in indexes:
        if idx_name in existing_indexes:
            log(f"Index '{idx_name}' already exists", "SKIP")
        else:
            # Check if table exists first
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :tbl"
            ), {"tbl": table})
            if not result.fetchone():
                log(f"Index '{idx_name}' skipped - table '{table}' not found", "WARN")
                continue

            conn.execute(text(
                f"CREATE INDEX {idx_name} ON {table} {columns}"
            ))
            log(f"Created index: {idx_name} ON {table} {columns}", "OK")


def seed_data(conn):
    """Insert seed data (initial positions + system settings) if not already present."""
    print("\n[4/5] Seeding hedging data...")

    # -- Initial metal positions (gold + silver with zero balance) --
    metals = [
        ("gold", "Gold position"),
        ("silver", "Silver position"),
    ]

    pos_inserted = 0
    pos_skipped = 0
    for metal_type, label in metals:
        result = conn.execute(text(
            "SELECT id FROM metal_positions WHERE metal_type = :mt"
        ), {"mt": metal_type})
        if result.fetchone():
            log(f"Position '{label}' (metal_type={metal_type}) already exists", "SKIP")
            pos_skipped += 1
        else:
            conn.execute(text(
                "INSERT INTO metal_positions (metal_type, balance_mg) VALUES (:mt, 0)"
            ), {"mt": metal_type})
            log(f"Inserted position: '{label}' (metal_type={metal_type}, balance=0)", "OK")
            pos_inserted += 1

    log(f"Positions: {pos_inserted} inserted, {pos_skipped} skipped (already exist)", "INFO")

    # -- System settings for hedging thresholds --
    settings_inserted = 0
    settings_skipped = 0
    for key, value, description in HEDGING_SETTINGS:
        result = conn.execute(text(
            "SELECT id FROM system_settings WHERE key = :key"
        ), {"key": key})
        if result.fetchone():
            log(f"Setting '{key}' already exists", "SKIP")
            settings_skipped += 1
        else:
            conn.execute(text(
                "INSERT INTO system_settings (key, value, description) "
                "VALUES (:key, :value, :desc)"
            ), {"key": key, "value": value, "desc": description})
            log(f"Inserted setting: '{key}' = '{value}'", "OK")
            settings_inserted += 1

    log(f"Settings: {settings_inserted} inserted, {settings_skipped} skipped (already exist)", "INFO")


def verify_results(conn):
    """Verify all tables, indexes, and seed data."""
    print("\n[5/5] Verification...")

    # Verify tables
    print("\n  --- Tables ---")
    for table in HEDGING_TABLES:
        result = conn.execute(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :tbl"
        ), {"tbl": table})
        exists = result.fetchone() is not None

        if exists:
            count_result = conn.execute(text(f"SELECT count(*) FROM {table}"))
            count = count_result.scalar()
            log(f"{table}: EXISTS ({count} rows)", "OK")
        else:
            log(f"{table}: MISSING!", "ERR")

    # Verify indexes
    print("\n  --- Indexes ---")
    result = conn.execute(text(
        "SELECT indexname, tablename FROM pg_indexes "
        "WHERE schemaname = 'public' AND tablename IN :tables"
    ), {"tables": tuple(HEDGING_TABLES)})
    indexes = result.fetchall()
    for idx_name, table_name in indexes:
        log(f"{idx_name} ON {table_name}", "OK")

    if not indexes:
        log("No hedging indexes found", "WARN")

    # Verify seed data - positions
    print("\n  --- Metal Positions ---")
    result = conn.execute(text(
        "SELECT id, metal_type, balance_mg FROM metal_positions ORDER BY id"
    ))
    positions = result.fetchall()
    for pos in positions:
        grams = pos[2] / 1000.0
        log(f"Position #{pos[0]}: {pos[1]} = {pos[2]}mg ({grams:.1f}g)", "OK")

    if not positions:
        log("No metal positions found!", "ERR")

    # Verify seed data - settings
    print("\n  --- Hedging Settings ---")
    for key, _, _ in HEDGING_SETTINGS:
        result = conn.execute(text(
            "SELECT key, value, description FROM system_settings WHERE key = :key"
        ), {"key": key})
        row = result.fetchone()
        if row:
            log(f"{row[0]} = {row[1]} ({row[2]})", "OK")
        else:
            log(f"Setting '{key}' MISSING!", "ERR")

    # Verify foreign keys
    print("\n  --- Foreign Keys ---")
    result = conn.execute(text("""
        SELECT tc.constraint_name, tc.table_name, kcu.column_name,
               ccu.table_name AS foreign_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name IN :tables
        ORDER BY tc.table_name
    """), {"tables": tuple(HEDGING_TABLES)})
    fks = result.fetchall()
    for fk in fks:
        log(f"{fk[1]}.{fk[2]} -> {fk[3]} ({fk[0]})", "OK")

    if not fks:
        log("No foreign keys found (may indicate table creation issue)", "WARN")


def main():
    conn = engine.connect()
    trans = conn.begin()

    try:
        # Step 0: Connection check
        check_connection(conn)

        # Step 1: Check existing state
        already_exist, need_create = check_existing_tables(conn)

        # Step 2: Create tables
        create_tables(conn, need_create)

        # Step 3: Create indexes
        create_indexes(conn)

        # Step 4: Seed data
        seed_data(conn)

        # Commit all changes
        trans.commit()
        print("\n  >>> All changes committed successfully <<<")

        # Step 5: Verify (read-only, new transaction)
        conn2 = engine.connect()
        try:
            verify_results(conn2)
        finally:
            conn2.close()

        print("\n" + "=" * 60)
        print("  Migration completed successfully!")
        print("=" * 60)
        print("\n  Next steps:")
        print("  1. Review the output above carefully")
        print("  2. Restart the application: systemctl restart talamala")
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
