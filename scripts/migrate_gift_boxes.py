"""
Migration: CardDesign + PackageType -> GiftBox
================================================
Run on production server:
    cd /path/to/talamala_v4
    source env/bin/activate
    python scripts/migrate_gift_boxes.py

Idempotent: safe to run multiple times. Already-applied steps are skipped.

What it does:
1. Creates gift_boxes + gift_box_images tables
2. Copies package_types data into gift_boxes (preserving IDs)
3. Copies package_type_images into gift_box_images
4. Migrates cart_items.package_type_id -> gift_box_id
5. Migrates order_items.package_type_id -> gift_box_id
6. Drops card_design_id and design columns from products
7. Drops card_designs and card_design_images tables
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from config.database import SessionLocal


def col_exists(db, table, column):
    """Check if a column exists in a table."""
    r = db.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return r.scalar() > 0


def table_exists(db, table):
    """Check if a table exists."""
    r = db.execute(text(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = :t"
    ), {"t": table})
    return r.scalar() > 0


def run():
    db = SessionLocal()
    step = 0
    total = 12
    ok = True

    def log(msg, status="OK"):
        nonlocal step
        step += 1
        print(f"  [{step:2d}/{total}] {status:4s}  {msg}")

    def skip(msg):
        nonlocal step
        step += 1
        print(f"  [{step:2d}/{total}] SKIP  {msg}  (already done)")

    print("=" * 60)
    print("  Migration: GiftBox + Remove CardDesign/Design")
    print("=" * 60)

    try:
        # 1. Create gift_boxes
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS gift_boxes (
                id SERIAL PRIMARY KEY,
                name VARCHAR UNIQUE NOT NULL,
                description TEXT,
                price BIGINT NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
        """))
        log("Create gift_boxes table")

        # 2. Create gift_box_images
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS gift_box_images (
                id SERIAL PRIMARY KEY,
                file_path VARCHAR NOT NULL,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                gift_box_id INTEGER NOT NULL REFERENCES gift_boxes(id) ON DELETE CASCADE
            )
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_gift_box_images_gift_box_id ON gift_box_images(gift_box_id)"))
        log("Create gift_box_images table + index")

        # 3. Copy package_types -> gift_boxes
        r = db.execute(text("""
            INSERT INTO gift_boxes (id, name, price, is_active, sort_order)
            SELECT id, name, price, is_active,
                   ROW_NUMBER() OVER (ORDER BY id) - 1 as sort_order
            FROM package_types
            ON CONFLICT (id) DO NOTHING
        """))
        db.execute(text("SELECT setval('gift_boxes_id_seq', GREATEST((SELECT COALESCE(MAX(id), 0) FROM gift_boxes), 1))"))
        log(f"Copy package_types -> gift_boxes  (rows: {r.rowcount})")

        # 4. Copy package_type_images -> gift_box_images
        r = db.execute(text("""
            INSERT INTO gift_box_images (id, file_path, is_default, gift_box_id)
            SELECT id, file_path, is_default, package_id
            FROM package_type_images
            ON CONFLICT (id) DO NOTHING
        """))
        db.execute(text("SELECT setval('gift_box_images_id_seq', GREATEST((SELECT COALESCE(MAX(id), 0) FROM gift_box_images), 1))"))
        log(f"Copy package_type_images -> gift_box_images  (rows: {r.rowcount})")

        # 5. cart_items: package_type_id -> gift_box_id
        db.execute(text("ALTER TABLE cart_items ADD COLUMN IF NOT EXISTS gift_box_id INTEGER REFERENCES gift_boxes(id) ON DELETE SET NULL"))
        if col_exists(db, "cart_items", "package_type_id"):
            r = db.execute(text("UPDATE cart_items SET gift_box_id = package_type_id WHERE package_type_id IS NOT NULL AND gift_box_id IS NULL"))
            db.execute(text("ALTER TABLE cart_items DROP COLUMN package_type_id"))
            log(f"Migrate cart_items.package_type_id -> gift_box_id  (rows: {r.rowcount})")
        else:
            skip("cart_items.package_type_id -> gift_box_id")

        # 6. order_items: package_type_id -> gift_box_id + applied_gift_box_price
        db.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS gift_box_id INTEGER REFERENCES gift_boxes(id) ON DELETE SET NULL"))
        db.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS applied_gift_box_price BIGINT NOT NULL DEFAULT 0"))
        if col_exists(db, "order_items", "package_type_id"):
            r1 = db.execute(text("UPDATE order_items SET gift_box_id = package_type_id WHERE package_type_id IS NOT NULL AND gift_box_id IS NULL"))
            r2 = db.execute(text("UPDATE order_items SET applied_gift_box_price = COALESCE(applied_package_price, 0) WHERE applied_gift_box_price = 0"))
            db.execute(text("ALTER TABLE order_items DROP COLUMN package_type_id"))
            db.execute(text("ALTER TABLE order_items DROP COLUMN IF EXISTS applied_package_price"))
            log(f"Migrate order_items package -> gift_box  (gift_box: {r1.rowcount}, price: {r2.rowcount})")
        else:
            skip("order_items.package_type_id -> gift_box_id")

        # 7. Drop applied_package_price if still exists
        if col_exists(db, "order_items", "applied_package_price"):
            db.execute(text("ALTER TABLE order_items DROP COLUMN applied_package_price"))
            log("Drop order_items.applied_package_price")
        else:
            skip("order_items.applied_package_price")

        # 8. Drop products.card_design_id
        if col_exists(db, "products", "card_design_id"):
            db.execute(text("ALTER TABLE products DROP COLUMN card_design_id"))
            log("Drop products.card_design_id")
        else:
            skip("products.card_design_id")

        # 9. Drop products.design
        if col_exists(db, "products", "design"):
            db.execute(text("ALTER TABLE products DROP COLUMN design"))
            log("Drop products.design")
        else:
            skip("products.design")

        # 10. Drop card_design tables
        if table_exists(db, "card_design_images") or table_exists(db, "card_designs"):
            db.execute(text("DROP TABLE IF EXISTS card_design_images"))
            db.execute(text("DROP TABLE IF EXISTS card_designs"))
            log("Drop card_design tables")
        else:
            skip("Drop card_design tables")

        # --- Commit ---
        db.commit()
        print(f"\n  COMMIT — all {step} steps completed.")

    except Exception as e:
        db.rollback()
        print(f"\n  FAIL at step {step}: {e}")
        print("  ROLLBACK — no changes applied.")
        ok = False

    # --- Verification (outside transaction) ---
    if ok:
        print("\n" + "=" * 60)
        print("  Verification")
        print("=" * 60)

        checks = [
            ("gift_boxes count", "SELECT COUNT(*) FROM gift_boxes"),
            ("gift_box_images count", "SELECT COUNT(*) FROM gift_box_images"),
            ("cart_items with gift_box", "SELECT COUNT(*) FROM cart_items WHERE gift_box_id IS NOT NULL"),
            ("cart_items total", "SELECT COUNT(*) FROM cart_items"),
            ("order_items total", "SELECT COUNT(*) FROM order_items"),
            ("products.design exists (expect 0)", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='products' AND column_name='design'"),
            ("products.card_design_id exists (expect 0)", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='products' AND column_name='card_design_id'"),
            ("card_designs table exists (expect 0)", "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='card_designs'"),
            ("cart_items.package_type_id exists (expect 0)", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='cart_items' AND column_name='package_type_id'"),
            ("order_items.package_type_id exists (expect 0)", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='order_items' AND column_name='package_type_id'"),
        ]

        all_pass = True
        for label, sql in checks:
            try:
                val = db.execute(text(sql)).scalar()
                expect_zero = "expect 0" in label
                status = "PASS" if (not expect_zero or val == 0) else "WARN"
                if status == "WARN":
                    all_pass = False
                print(f"  [{status}] {label}: {val}")
            except Exception as e:
                print(f"  [FAIL] {label}: {e}")
                all_pass = False

        print("\n" + "=" * 60)
        if all_pass:
            print("  ALL CHECKS PASSED")
        else:
            print("  SOME CHECKS NEED ATTENTION (see WARN above)")
        print("=" * 60)

    db.close()
    return ok


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
