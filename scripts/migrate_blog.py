"""
TalaMala v4 - Blog Module Migration (Phase 23)
===============================================
Safe migration script for PRODUCTION database.

Creates blog tables + seed data WITHOUT touching existing data.
Every operation is logged with detail.

Usage:
    python scripts/migrate_blog.py

Safety:
    - Only creates NEW tables (IF NOT EXISTS)
    - Only inserts seed data if not already present (ON CONFLICT DO NOTHING)
    - Never drops/alters existing tables
    - Full logging of every operation
    - Dry-run check before any write
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
from config.database import engine, SessionLocal


BLOG_TABLES = [
    "article_categories",
    "article_tags",
    "articles",
    "article_tag_links",
    "article_images",
    "article_comments",
]

BLOG_INDEXES = [
    "ix_article_status_published",
    "ix_article_comment_article",
    "ix_article_comment_approved",
]


def log(msg: str, level: str = "INFO"):
    prefix = {"INFO": "[INFO]", "OK": "[ OK ]", "SKIP": "[SKIP]", "WARN": "[WARN]", "ERR": "[ERR ]"}
    print(f"  {prefix.get(level, '[???]')} {msg}")


def check_connection(conn):
    """Verify database connection and show current state."""
    print("=" * 60)
    print("  Blog Module Migration (Phase 23)")
    print("=" * 60)

    # Show database info
    result = conn.execute(text("SELECT current_database(), current_user, version()"))
    row = result.fetchone()
    print(f"\n  Database: {row[0]}")
    print(f"  User:     {row[1]}")
    print(f"  Server:   {row[2][:60]}...")

    # Show total table count
    result = conn.execute(text(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'public'"
    ))
    total_tables = result.scalar()
    print(f"  Existing tables: {total_tables}")
    print()


def check_existing_tables(conn):
    """Check which blog tables already exist."""
    print("[1/5] Checking existing blog tables...")

    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    already_exist = []
    need_create = []

    for table in BLOG_TABLES:
        if table in existing:
            already_exist.append(table)
            log(f"Table '{table}' already exists", "SKIP")
        else:
            need_create.append(table)
            log(f"Table '{table}' needs creation", "INFO")

    return already_exist, need_create


def create_tables(conn, need_create):
    """Create blog tables that don't exist yet."""
    print(f"\n[2/5] Creating tables ({len(need_create)} to create)...")

    if not need_create:
        log("All blog tables already exist, nothing to create", "SKIP")
        return

    # -- article_categories --
    if "article_categories" in need_create:
        conn.execute(text("""
            CREATE TABLE article_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL UNIQUE,
                slug VARCHAR(200) NOT NULL UNIQUE,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true
            )
        """))
        log("Created table: article_categories", "OK")

    # -- article_tags --
    if "article_tags" in need_create:
        conn.execute(text("""
            CREATE TABLE article_tags (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                slug VARCHAR(100) NOT NULL UNIQUE
            )
        """))
        log("Created table: article_tags", "OK")

    # -- articles (depends on article_categories + users) --
    if "articles" in need_create:
        conn.execute(text("""
            CREATE TABLE articles (
                id SERIAL PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                slug VARCHAR(500) NOT NULL UNIQUE,
                excerpt TEXT,
                body TEXT NOT NULL DEFAULT '',
                cover_image VARCHAR(500),
                category_id INTEGER REFERENCES article_categories(id) ON DELETE SET NULL,
                author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'Draft',
                meta_title VARCHAR(200),
                meta_description VARCHAR(500),
                view_count INTEGER NOT NULL DEFAULT 0,
                is_featured BOOLEAN NOT NULL DEFAULT false,
                published_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        log("Created table: articles", "OK")

    # -- article_tag_links (depends on articles + article_tags) --
    if "article_tag_links" in need_create:
        conn.execute(text("""
            CREATE TABLE article_tag_links (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES article_tags(id) ON DELETE CASCADE,
                UNIQUE(article_id, tag_id)
            )
        """))
        log("Created table: article_tag_links", "OK")

    # -- article_images (depends on articles) --
    if "article_images" in need_create:
        conn.execute(text("""
            CREATE TABLE article_images (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                file_path VARCHAR NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        log("Created table: article_images", "OK")

    # -- article_comments (depends on articles + users) --
    if "article_comments" in need_create:
        conn.execute(text("""
            CREATE TABLE article_comments (
                id SERIAL PRIMARY KEY,
                article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                body TEXT NOT NULL,
                is_approved BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        log("Created table: article_comments", "OK")


def create_indexes(conn):
    """Create indexes (IF NOT EXISTS)."""
    print("\n[3/5] Creating indexes...")

    indexes = [
        ("ix_article_status_published", "articles", "(status, published_at)"),
        ("ix_article_category", "articles", "(category_id)"),
        ("ix_article_author", "articles", "(author_id)"),
        ("ix_article_tag_link_article", "article_tag_links", "(article_id)"),
        ("ix_article_tag_link_tag", "article_tag_links", "(tag_id)"),
        ("ix_article_images_article", "article_images", "(article_id)"),
        ("ix_article_comment_article", "article_comments", "(article_id)"),
        ("ix_article_comment_approved", "article_comments", "(article_id, is_approved)"),
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
                log(f"Index '{idx_name}' skipped — table '{table}' not found", "WARN")
                continue

            conn.execute(text(
                f"CREATE INDEX {idx_name} ON {table} {columns}"
            ))
            log(f"Created index: {idx_name} ON {table} {columns}", "OK")


def seed_data(conn):
    """Insert seed data (categories + tags) if not already present."""
    print("\n[4/5] Seeding blog data...")

    # -- Categories --
    categories = [
        ("آموزش سرمایه‌گذاری", "investment-education", "آموزش‌های سرمایه‌گذاری در طلا و نقره", 1),
        ("شناخت محصول", "product-knowledge", "معرفی و شناخت انواع شمش طلا و نقره", 2),
        ("اخبار بازار", "market-news", "اخبار و تحلیل بازار طلا و نقره", 3),
        ("راهنمای خرید", "buying-guide", "راهنمای انتخاب و خرید شمش طلا", 4),
    ]

    cat_inserted = 0
    cat_skipped = 0
    for name, slug, desc, sort_order in categories:
        result = conn.execute(text(
            "SELECT id FROM article_categories WHERE slug = :slug"
        ), {"slug": slug})
        if result.fetchone():
            log(f"Category '{name}' (slug={slug}) already exists", "SKIP")
            cat_skipped += 1
        else:
            conn.execute(text(
                "INSERT INTO article_categories (name, slug, description, sort_order, is_active) "
                "VALUES (:name, :slug, :desc, :sort, true)"
            ), {"name": name, "slug": slug, "desc": desc, "sort": sort_order})
            log(f"Inserted category: '{name}' (slug={slug})", "OK")
            cat_inserted += 1

    log(f"Categories: {cat_inserted} inserted, {cat_skipped} skipped (already exist)", "INFO")

    # -- Tags --
    tags = [
        ("طلا", "gold"),
        ("نقره", "silver"),
        ("شمش", "bullion"),
        ("سرمایه‌گذاری", "investment"),
        ("آموزش", "education"),
    ]

    tag_inserted = 0
    tag_skipped = 0
    for name, slug in tags:
        result = conn.execute(text(
            "SELECT id FROM article_tags WHERE slug = :slug"
        ), {"slug": slug})
        if result.fetchone():
            log(f"Tag '{name}' (slug={slug}) already exists", "SKIP")
            tag_skipped += 1
        else:
            conn.execute(text(
                "INSERT INTO article_tags (name, slug) VALUES (:name, :slug)"
            ), {"name": name, "slug": slug})
            log(f"Inserted tag: '{name}' (slug={slug})", "OK")
            tag_inserted += 1

    log(f"Tags: {tag_inserted} inserted, {tag_skipped} skipped (already exist)", "INFO")


def verify_results(conn):
    """Verify all tables, indexes, and seed data."""
    print("\n[5/5] Verification...")

    # Verify tables
    print("\n  --- Tables ---")
    for table in BLOG_TABLES:
        result = conn.execute(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :tbl"
        ), {"tbl": table})
        exists = result.fetchone() is not None

        if exists:
            # Get row count
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
    ), {"tables": tuple(BLOG_TABLES)})
    indexes = result.fetchall()
    for idx_name, table_name in indexes:
        log(f"{idx_name} ON {table_name}", "OK")

    if not indexes:
        log("No blog indexes found", "WARN")

    # Verify seed data
    print("\n  --- Seed Data ---")
    result = conn.execute(text("SELECT id, name, slug, sort_order FROM article_categories ORDER BY sort_order"))
    cats = result.fetchall()
    for cat in cats:
        log(f"Category #{cat[0]}: {cat[1]} (slug={cat[2]}, sort={cat[3]})", "OK")

    result = conn.execute(text("SELECT id, name, slug FROM article_tags ORDER BY id"))
    tags = result.fetchall()
    for tag in tags:
        log(f"Tag #{tag[0]}: {tag[1]} (slug={tag[2]})", "OK")

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
    """), {"tables": tuple(BLOG_TABLES)})
    fks = result.fetchall()
    for fk in fks:
        log(f"{fk[1]}.{fk[2]} -> {fk[3]} ({fk[0]})", "OK")

    if not fks:
        log("No foreign keys found (may indicate table creation issue)", "WARN")


def ensure_upload_dir():
    """Create blog upload directory if missing."""
    print("\n  --- Upload Directory ---")
    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "static", "uploads", "blog",
    )
    if os.path.isdir(upload_dir):
        log(f"{upload_dir} already exists", "SKIP")
    else:
        os.makedirs(upload_dir, exist_ok=True)
        log(f"Created: {upload_dir}", "OK")


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

        # Upload dir (filesystem, not DB)
        ensure_upload_dir()

        print("\n" + "=" * 60)
        print("  Migration completed successfully!")
        print("=" * 60)
        print("\n  Next steps:")
        print("  1. Review the output above carefully")
        print("  2. Ensure TinyMCE is in static/vendor/tinymce/")
        print("  3. Restart the application: systemctl restart talamala")
        print()

    except Exception as e:
        trans.rollback()
        print(f"\n  [ERR ] Migration FAILED — all changes rolled back!")
        print(f"  [ERR ] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
