"""
TalaMala v4 - Run ALL Migrations (Safe & Idempotent)
=====================================================
Runs all migration scripts in order. Each step is idempotent —
if already applied, it skips automatically.

Usage:
    python scripts/migrate_all.py

Safety:
    - Every step checks before acting (IF NOT EXISTS, column check, etc.)
    - Full rollback on any error
    - Detailed logging of every operation
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


def log(msg, level="INFO"):
    prefix = {"INFO": "[INFO]", "OK": "[ OK ]", "SKIP": "[SKIP]", "WARN": "[WARN]", "ERR": "[ERR ]"}
    print(f"  {prefix.get(level, '[???]')} {msg}")


def column_exists(conn, table, column):
    r = conn.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name=:t AND column_name=:c
    """), {"t": table, "c": column})
    return r.fetchone() is not None


def table_exists(conn, table):
    r = conn.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='public' AND table_name=:t
    """), {"t": table})
    return r.fetchone() is not None


def index_exists(conn, index_name):
    r = conn.execute(text("""
        SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:i
    """), {"i": index_name})
    return r.fetchone() is not None


def setting_exists(conn, key):
    r = conn.execute(text("SELECT 1 FROM system_settings WHERE key=:k"), {"k": key})
    return r.fetchone() is not None


# ==========================================
# Step 1: Hedging tables (Phase 17.5)
# ==========================================
def step_hedging_tables(conn):
    print("\n" + "=" * 50)
    print("  Step 1: Hedging Tables")
    print("=" * 50)

    # metal_positions
    if table_exists(conn, "metal_positions"):
        log("Table 'metal_positions' already exists", "SKIP")
    else:
        conn.execute(text("""
            CREATE TABLE metal_positions (
                id SERIAL PRIMARY KEY,
                metal_type VARCHAR(20) NOT NULL UNIQUE,
                balance_mg BIGINT NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        log("Created table: metal_positions", "OK")

    # position_ledger
    if table_exists(conn, "position_ledger"):
        log("Table 'position_ledger' already exists", "SKIP")
    else:
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

    # Indexes
    for idx, tbl, cols in [
        ("ix_pos_ledger_metal_created", "position_ledger", "(metal_type, created_at)"),
        ("ix_pos_ledger_source", "position_ledger", "(source_type, source_id)"),
    ]:
        if index_exists(conn, idx):
            log(f"Index '{idx}' already exists", "SKIP")
        elif table_exists(conn, tbl):
            conn.execute(text(f"CREATE INDEX {idx} ON {tbl} {cols}"))
            log(f"Created index: {idx}", "OK")

    # Seed: metal positions
    for mt in ["gold", "silver"]:
        r = conn.execute(text("SELECT 1 FROM metal_positions WHERE metal_type=:mt"), {"mt": mt})
        if r.fetchone():
            log(f"Position '{mt}' already exists", "SKIP")
        else:
            conn.execute(text("INSERT INTO metal_positions (metal_type, balance_mg) VALUES (:mt, 0)"), {"mt": mt})
            log(f"Inserted position: {mt}", "OK")

    # Seed: hedging settings
    for key, val, desc in [
        ("hedge_threshold_gold_mg", "50000", "Gold alert threshold (mg)"),
        ("hedge_threshold_silver_mg", "500000", "Silver alert threshold (mg)"),
        ("hedge_alert_enabled", "true", "Enable hedging threshold alerts"),
        ("hedge_alert_cooldown_minutes", "60", "Minutes between alerts"),
    ]:
        if setting_exists(conn, key):
            log(f"Setting '{key}' already exists", "SKIP")
        else:
            conn.execute(text(
                "INSERT INTO system_settings (key, value, description) VALUES (:k, :v, :d)"
            ), {"k": key, "v": val, "d": desc})
            log(f"Inserted setting: {key}={val}", "OK")


# ==========================================
# Step 2: Blog tables (Phase 23)
# ==========================================
def step_blog_tables(conn):
    print("\n" + "=" * 50)
    print("  Step 2: Blog Tables")
    print("=" * 50)

    blog_tables = {
        "article_categories": """
            CREATE TABLE article_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL UNIQUE,
                slug VARCHAR(200) NOT NULL UNIQUE,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            )
        """,
        "article_tags": """
            CREATE TABLE article_tags (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                slug VARCHAR(100) NOT NULL UNIQUE
            )
        """,
        "articles": """
            CREATE TABLE articles (
                id SERIAL PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                slug VARCHAR(500) NOT NULL UNIQUE,
                excerpt TEXT,
                body TEXT,
                cover_image VARCHAR(500),
                category_id INTEGER REFERENCES article_categories(id) ON DELETE SET NULL,
                author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'Draft',
                meta_title VARCHAR(500),
                meta_description VARCHAR(500),
                view_count INTEGER DEFAULT 0,
                is_featured BOOLEAN DEFAULT FALSE,
                published_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """,
        "article_tag_links": """
            CREATE TABLE article_tag_links (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES article_tags(id) ON DELETE CASCADE,
                UNIQUE(article_id, tag_id)
            )
        """,
        "article_images": """
            CREATE TABLE article_images (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                file_path VARCHAR(500) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """,
        "article_comments": """
            CREATE TABLE article_comments (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                body TEXT NOT NULL,
                is_approved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """,
    }

    for tbl, ddl in blog_tables.items():
        if table_exists(conn, tbl):
            log(f"Table '{tbl}' already exists", "SKIP")
        else:
            conn.execute(text(ddl))
            log(f"Created table: {tbl}", "OK")

    # Blog indexes
    for idx, tbl, cols in [
        ("ix_articles_status_published", "articles", "(status, published_at)"),
        ("ix_articles_category", "articles", "(category_id)"),
        ("ix_articles_author", "articles", "(author_id)"),
        ("ix_article_comments_article", "article_comments", "(article_id)"),
        ("ix_article_comments_approved", "article_comments", "(article_id, is_approved)"),
    ]:
        if index_exists(conn, idx):
            log(f"Index '{idx}' already exists", "SKIP")
        elif table_exists(conn, tbl):
            conn.execute(text(f"CREATE INDEX {idx} ON {tbl} {cols}"))
            log(f"Created index: {idx}", "OK")


# ==========================================
# Step 3: Bars import prep (old system)
# ==========================================
def step_bars_columns(conn):
    print("\n" + "=" * 50)
    print("  Step 3: Bar Extra Columns")
    print("=" * 50)

    # claim_code on bars
    if column_exists(conn, "bars", "claim_code"):
        log("Column bars.claim_code already exists", "SKIP")
    else:
        conn.execute(text("ALTER TABLE bars ADD COLUMN claim_code VARCHAR(20) UNIQUE"))
        log("Added column: bars.claim_code", "OK")

    # delivered_at on bars
    if column_exists(conn, "bars", "delivered_at"):
        log("Column bars.delivered_at already exists", "SKIP")
    else:
        conn.execute(text("ALTER TABLE bars ADD COLUMN delivered_at TIMESTAMPTZ"))
        log("Added column: bars.delivered_at", "OK")


# ==========================================
# Step 4: Buyback OTP columns
# ==========================================
def step_buyback_otp(conn):
    print("\n" + "=" * 50)
    print("  Step 4: Buyback OTP Columns")
    print("=" * 50)

    cols = [
        ("buyback_requests", "otp_hash", "VARCHAR(255)"),
        ("buyback_requests", "otp_expiry", "TIMESTAMPTZ"),
        ("buyback_requests", "seller_user_id", "INTEGER REFERENCES users(id)"),
        ("buyback_requests", "seller_national_id", "VARCHAR(20)"),
    ]

    for tbl, col, dtype in cols:
        if not table_exists(conn, tbl):
            log(f"Table '{tbl}' does not exist, skipping {col}", "WARN")
        elif column_exists(conn, tbl, col):
            log(f"Column {tbl}.{col} already exists", "SKIP")
        else:
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {dtype}"))
            log(f"Added column: {tbl}.{col}", "OK")


# ==========================================
# Step 5: Hedging involved_user_id
# ==========================================
def step_hedging_involved_user(conn):
    print("\n" + "=" * 50)
    print("  Step 5: Hedging involved_user_id")
    print("=" * 50)

    if not table_exists(conn, "position_ledger"):
        log("Table 'position_ledger' does not exist, skipping", "WARN")
        return

    if column_exists(conn, "position_ledger", "involved_user_id"):
        log("Column position_ledger.involved_user_id already exists", "SKIP")
    else:
        conn.execute(text(
            "ALTER TABLE position_ledger ADD COLUMN involved_user_id INTEGER REFERENCES users(id)"
        ))
        log("Added column: position_ledger.involved_user_id", "OK")


# ==========================================
# Verification
# ==========================================
def verify(conn):
    print("\n" + "=" * 50)
    print("  Verification")
    print("=" * 50)

    critical_tables = [
        "metal_positions", "position_ledger",
        "article_categories", "article_tags", "articles",
        "article_tag_links", "article_images", "article_comments",
    ]

    for tbl in critical_tables:
        if table_exists(conn, tbl):
            r = conn.execute(text(f"SELECT count(*) FROM {tbl}"))
            log(f"{tbl}: OK ({r.scalar()} rows)", "OK")
        else:
            log(f"{tbl}: MISSING", "ERR")

    # Check key columns
    key_columns = [
        ("position_ledger", "involved_user_id"),
        ("bars", "claim_code"),
        ("bars", "delivered_at"),
    ]
    for tbl, col in key_columns:
        if table_exists(conn, tbl) and column_exists(conn, tbl, col):
            log(f"{tbl}.{col}: OK", "OK")
        elif table_exists(conn, tbl):
            log(f"{tbl}.{col}: MISSING", "ERR")

    # Buyback OTP columns (optional — table may not exist)
    if table_exists(conn, "buyback_requests"):
        for col in ["otp_hash", "otp_expiry", "seller_user_id", "seller_national_id"]:
            if column_exists(conn, "buyback_requests", col):
                log(f"buyback_requests.{col}: OK", "OK")
            else:
                log(f"buyback_requests.{col}: MISSING", "ERR")


# ==========================================
# Main
# ==========================================
def main():
    print("\n" + "=" * 60)
    print("  TalaMala v4 — Run ALL Migrations")
    print("=" * 60)

    conn = engine.connect()
    trans = conn.begin()

    try:
        # Connection info
        r = conn.execute(text("SELECT current_database(), current_user"))
        row = r.fetchone()
        print(f"\n  Database: {row[0]}")
        print(f"  User:     {row[1]}")

        r = conn.execute(text(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        ))
        print(f"  Tables:   {r.scalar()}")

        # Run all steps
        step_hedging_tables(conn)
        step_blog_tables(conn)
        step_bars_columns(conn)
        step_buyback_otp(conn)
        step_hedging_involved_user(conn)

        # Commit
        trans.commit()
        print("\n  >>> All changes committed successfully <<<")

        # Verify (new connection)
        conn2 = engine.connect()
        try:
            verify(conn2)
        finally:
            conn2.close()

        print("\n" + "=" * 60)
        print("  All migrations completed successfully!")
        print("=" * 60)
        print("\n  Next: systemctl restart talamala")
        print()

    except Exception as e:
        trans.rollback()
        print(f"\n  [ERR ] FAILED — all changes rolled back!")
        print(f"  [ERR ] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
