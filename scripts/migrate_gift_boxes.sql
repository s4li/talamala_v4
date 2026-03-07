-- ============================================================
-- Migration: CardDesign → GiftBox
-- ============================================================
-- این اسکریپت روی سرور پروداکشن اجرا بشه.
-- داده‌های package_types به gift_boxes منتقل می‌شن (با حفظ id).
-- cart_items و order_items آپدیت می‌شن.
-- card_designs حذف می‌شه.
-- ============================================================

BEGIN;

-- 1. ساخت جدول gift_boxes
CREATE TABLE gift_boxes (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description TEXT,
    price BIGINT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- 2. ساخت جدول gift_box_images
CREATE TABLE gift_box_images (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    gift_box_id INTEGER NOT NULL REFERENCES gift_boxes(id) ON DELETE CASCADE
);
CREATE INDEX ix_gift_box_images_gift_box_id ON gift_box_images(gift_box_id);

-- 3. انتقال داده از package_types به gift_boxes (حفظ id ها)
INSERT INTO gift_boxes (id, name, price, is_active, sort_order)
SELECT id, name, price, is_active,
       ROW_NUMBER() OVER (ORDER BY id) - 1 as sort_order
FROM package_types;
SELECT setval('gift_boxes_id_seq', (SELECT COALESCE(MAX(id), 0) FROM gift_boxes));

-- 4. انتقال عکس‌ها (FK ستون = package_id)
INSERT INTO gift_box_images (id, file_path, is_default, gift_box_id)
SELECT id, file_path, is_default, package_id
FROM package_type_images;
SELECT setval('gift_box_images_id_seq', COALESCE((SELECT MAX(id) FROM gift_box_images), 0));

-- 5. cart_items: اضافه gift_box_id، کپی داده، حذف package_type_id
ALTER TABLE cart_items ADD COLUMN gift_box_id INTEGER REFERENCES gift_boxes(id) ON DELETE SET NULL;
UPDATE cart_items SET gift_box_id = package_type_id WHERE package_type_id IS NOT NULL;
ALTER TABLE cart_items DROP COLUMN package_type_id;

-- 6. order_items: اضافه gift_box_id و applied_gift_box_price، کپی داده، حذف قدیمی‌ها
ALTER TABLE order_items ADD COLUMN gift_box_id INTEGER REFERENCES gift_boxes(id) ON DELETE SET NULL;
ALTER TABLE order_items ADD COLUMN applied_gift_box_price BIGINT NOT NULL DEFAULT 0;
UPDATE order_items SET gift_box_id = package_type_id WHERE package_type_id IS NOT NULL;
UPDATE order_items SET applied_gift_box_price = COALESCE(applied_package_price, 0);
ALTER TABLE order_items DROP COLUMN package_type_id;
ALTER TABLE order_items DROP COLUMN applied_package_price;

-- 7. حذف card_design_id و design از products
ALTER TABLE products DROP COLUMN IF EXISTS card_design_id;
ALTER TABLE products DROP COLUMN IF EXISTS design;

-- 8. حذف جداول card_design
DROP TABLE IF EXISTS card_design_images;
DROP TABLE IF EXISTS card_designs;

COMMIT;
