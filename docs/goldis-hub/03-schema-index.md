# Schema Index — Goldis Hub v2.7

> **Canonical home for all SQL schemas.**
> No other file in this repository should contain `CREATE TABLE` statements.
> Flow files and reference documents link here via markdown anchors.

> **Source:** `goldis-hub-architecture-v2.7.md` §3.2, §4.3, §5.4, §6.3, §8.2, §11.1–§11.9

---

## Table of Contents

| # | Domain | Tables | Source |
|---|--------|--------|--------|
| 1 | [Platform (Companies/Brands/Channels)](#1-platform) | companies, brands, sales_channels, payment_accounts, inventory_locations | §3.2 |
| 2 | [Wallet](#2-wallet) | asset_types, asset_balances, wallet_ledger_entries, wallet_locks | §4.3 |
| 3 | [Treasury](#3-treasury) | treasury_positions, treasury_settings, treasury_position_snapshots | §5.4 |
| 4 | [Inter-Company Ledger](#4-inter-company-ledger) | inter_company_ledger, inter_company_settle_actions | §6.3 |
| 5 | [Fulfillment](#5-fulfillment) | fulfillment_tasks, fulfillment_events | §8.2 |
| 6 | [Identity](#6-identity) | users, admin_users, sessions, user_bank_accounts | §11.1 |
| 7 | [KYC](#7-kyc) | kyc_records, user_level_defaults | §11.2 |
| 8 | [Catalog](#8-catalog) | products, packaging_types, product_images, product_channel_availability, external_product_mappings | §11.3 |
| 9 | [Pricing](#9-pricing) | price_sources, source_prices, pricing_configs, pricing_config_sources, internal_base_prices, channel_pricing_formulas, price_locks | §11.4 |
| 10 | [Inventory](#10-inventory) | bars, inventory_reservations, inventory_movements, bulk_gold_inventory, bulk_gold_movements | §11.5 |
| 11 | [Order](#11-order) | orders, order_items, order_status_log, withdrawal_details, order_payment_allocations, physical_buyback_requests | §11.6 |
| 12 | [Payment](#12-payment) | payment_providers, payments, payment_transactions, wallet_topups | §11.7 |
| 13 | [Outbox + Audit](#13-outbox--audit) | outbox_events, audit_logs | §11.8 |
| 14 | [Supplementary (D-62/D-63/D-73/D-96/D-97/D-99)](#14-supplementary) | sales_channel_payment_accounts, dealer_tiers, dealer_sales, dealer_commission_rates, dealer_commission_ledger, inventory_transfer_documents, inventory_transfer_items, payment_reconciliations, inventory_pending_holds, pos_pending_requests | §11.9 |
| 15 | [POS Devices & Transactions](#15-pos-devices--transactions) | pos_devices, pos_transactions | §9.2 |

---

## 1. Platform

> Source: §3.2 — Companies, Brands, Sales Channels, Payment Accounts, Inventory Locations
> Related decisions: [D-56, D-32](01-decisions-audit-log.md)

```sql
CREATE TABLE companies (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,        -- goldis | talamala | aminzar
    name VARCHAR(200) NOT NULL,
    legal_name VARCHAR(300) NOT NULL,
    company_types JSONB NOT NULL,            -- ["operator", "producer", "supplier", "brand_owner"]
    tax_id VARCHAR(50) NULL,
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE brands (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,        -- goldis | talamala | aminzar
    name VARCHAR(200) NOT NULL,
    brand_owner_company_id BIGINT NOT NULL REFERENCES companies(id),
    operator_company_id BIGINT NOT NULL REFERENCES companies(id),
    payment_receiver_company_id BIGINT NOT NULL REFERENCES companies(id),
    domain VARCHAR(200) NULL,                -- talamala.ir
    logo_url VARCHAR(500) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE sales_channels (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    brand_id BIGINT NOT NULL REFERENCES brands(id),
    channel_type VARCHAR(30) NOT NULL,
    -- website | marketplace | pos | admin_panel | offline | internal
    owning_company_id BIGINT NOT NULL REFERENCES companies(id),
    operator_company_id BIGINT NOT NULL REFERENCES companies(id),
    seller_company_id BIGINT NOT NULL REFERENCES companies(id),  -- D-56: فروشنده‌ی حقوقی (موجودی)
    payment_receiver_company_id BIGINT NOT NULL REFERENCES companies(id),  -- D-56: گیرندهی پول
    default_payment_account_id BIGINT NULL,  -- FK اضافه شود بعد از payment_accounts
    adapter_class VARCHAR(200) NULL,         -- for marketplace
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE payment_accounts (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    provider_id BIGINT NOT NULL,             -- FK به payment_providers
    account_type VARCHAR(20) NOT NULL,       -- ipg | pos | bank_transfer | wallet
    merchant_id VARCHAR(100) NULL,
    terminal_id VARCHAR(100) NULL,
    settlement_bank_account VARCHAR(50) NULL,
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- بعد از ایجاد payment_accounts:
ALTER TABLE sales_channels
    ADD CONSTRAINT fk_default_payment_account
    FOREIGN KEY (default_payment_account_id) REFERENCES payment_accounts(id);

CREATE TABLE inventory_locations (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    owner_company_id BIGINT NOT NULL REFERENCES companies(id),
    -- مالک حقوقی (مثلا شرکت طلاملا)
    manager_company_id BIGINT NOT NULL REFERENCES companies(id),
    -- شرکتی که فیزیکی این مکان را اداره میکند (مثلا شرکت گلدیس اگر تحت قرارداد لجستیک)
    -- این دو می‌توانند متفاوت باشند (بخش ۷.۶ — مدل عملیاتی TalaMala)
    location_type VARCHAR(30) NOT NULL,
    -- warehouse | factory | safe_box | store | external_marketplace | branch | dealer
    -- D-62: in_transit (انبار مجازی موجودی در راه — غیرقابل‌فروش؛ هیچجا
    --   reserve/فروش نمی‌شود تا رسید مقصد). انتقال دو‌مرحله‌ای روی این بناست.
    is_sellable BOOLEAN NOT NULL DEFAULT TRUE,  -- D-62: برای location_type='in_transit' = FALSE
    address VARCHAR(500) NULL,
    -- D-32: آیا این مکان می‌تواند physical buyback را تأیید کند؟
    -- TRUE برای: warehouse مرکزی Goldis، dealer هایی با is_buyback_center
    can_buyback BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
-- ⚠ توجه: نام ستون `company_id` در سند قبلی به `owner_company_id` تغییر کرد.
-- در v5 از ابتدا با دو ستون owner / manager پیاده می‌شود.
```


---

## 2. Wallet

> Source: §4.3 — Asset Types, Balances, Ledger, Locks
> Related decisions: [D-46](01-decisions-audit-log.md) (scope isolation)

```sql
CREATE TABLE asset_types (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,        -- IRR | XAU_MG | XAG_MG
    name VARCHAR(100) NOT NULL,
    minor_unit_name VARCHAR(20) NOT NULL,    -- rial | milligram
    minor_unit_scale INT NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- موجودی فعلی per (user, legal_entity, asset)
CREATE TABLE asset_balances (
    user_id BIGINT NOT NULL REFERENCES users(id),
    wallet_scope VARCHAR(20) NOT NULL,  -- D-46: goldis | aminzar | talamala (سطل قابلمشاهدهی کاربر)
    company_id BIGINT NOT NULL REFERENCES companies(id),  -- D-46: مشتق از scope (goldis/aminzar→شرکت گلدیس، talamala→شرکت طلاملا) — برای حسابداری/inter-company
    asset_type_id BIGINT NOT NULL REFERENCES asset_types(id),
    current_balance_minor BIGINT NOT NULL DEFAULT 0,
    locked_balance_minor BIGINT NOT NULL DEFAULT 0,
    credit_limit_minor BIGINT NOT NULL DEFAULT 0,   -- for dealer XAU_MG only
    version BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, wallet_scope, asset_type_id),  -- D-46: scope-keyed، نه company-keyed
    CONSTRAINT chk_balance_within_credit
        CHECK (current_balance_minor >= -credit_limit_minor)
);
-- D-46: wallet_ledger_entries و wallet_locks هم ستون wallet_scope میگیرند
-- (همراستا با asset_balances). سه scope کاملا ایزوله — هیچ انتقال مستقیم بین scopeها.

-- Append-only ledger (D-46: wallet_scope required)
CREATE TABLE wallet_ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),
    wallet_scope VARCHAR(20) NOT NULL,      -- D-46: goldis | aminzar | talamala — کلید scope
    company_id BIGINT NOT NULL REFERENCES companies(id),  -- مشتق برای حسابداری
    asset_type_id BIGINT NOT NULL REFERENCES asset_types(id),
    direction VARCHAR(10) NOT NULL,          -- credit | debit
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    delta_balance BIGINT NOT NULL,           -- signed
    delta_locked BIGINT NOT NULL DEFAULT 0,
    balance_after_minor BIGINT NOT NULL,
    locked_after_minor BIGINT NOT NULL,
    reference_type VARCHAR(50) NOT NULL,
    -- order | trade | withdrawal | buyback | adjustment | lock | release | commit | settlement | topup
    reference_id VARCHAR(100) NOT NULL,
    idempotency_key VARCHAR(100) NOT NULL,
    description TEXT NULL,
    metadata JSONB NULL,
    created_by BIGINT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (wallet_scope, user_id, idempotency_key)  -- D-46: scope-keyed idempotency
);
CREATE INDEX ix_ledger_user_scope_asset
    ON wallet_ledger_entries (user_id, wallet_scope, asset_type_id, created_at DESC);

CREATE TABLE wallet_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),
    wallet_scope VARCHAR(20) NOT NULL,      -- D-46: goldis | aminzar | talamala — کلید scope
    company_id BIGINT NOT NULL REFERENCES companies(id),  -- مشتق برای حسابداری
    asset_type_id BIGINT NOT NULL REFERENCES asset_types(id),
    amount_minor BIGINT NOT NULL,
    reference_type VARCHAR(50) NOT NULL,
    reference_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    expires_at TIMESTAMPTZ NULL,
    idempotency_key VARCHAR(100) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (wallet_scope, user_id, idempotency_key)  -- D-46: scope-keyed idempotency
);
```


---

## 3. Treasury

> Source: §5.4 — Positions, Settings, Snapshots
> Related decisions: [D-47](01-decisions-audit-log.md) (bidirectional caps), [D-100](01-decisions-audit-log.md) (signed-sum exposure — coverage model removed), [D-101](01-decisions-audit-log.md) (two-level cap + advisory lock), [D-90](01-decisions-audit-log.md) (hedge_buy = negative delta)

```sql
-- D-100: SIGNED-SUM exposure model. The coverage mechanism is REMOVED
-- (covered_amount_mg, covered_at, status 'partially_covered'/'covered', and the
--  POST /positions/{id}/cover endpoint are gone). hedge_buy is a NEGATIVE delta row (D-90).
CREATE TABLE treasury_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metal_type VARCHAR(20) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    -- order_physical | digital_buy | digital_sell | marketplace_sale
    -- pos_sale | physical_purchase_from_wallet | buyback
    -- hedge_buy | hedge_sell | dealer_commission | manual_adjustment
    -- (gold withdrawal حذف شد — D-31. hedging merge شد در Treasury — D-42)
    source_id VARCHAR(100) NULL,
    sales_channel_id BIGINT NULL REFERENCES sales_channels(id),
    triggered_by_brand_id BIGINT NULL REFERENCES brands(id),
    delta_amount_mg BIGINT NOT NULL,   -- signed: + opens exposure, − closes (hedge_buy/digital_sell). D-104: integer mg, FLOOR.
    metal_price_per_gram_rial NUMERIC(20, 2) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    -- D-100: ONLY two values — 'open' (counted in exposure) | 'cancelled' (ignored). No coverage states.
    note TEXT NULL,
    metadata JSONB NULL,
    actor_id BIGINT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_treasury_metal_status ON treasury_positions (metal_type, status);
-- D-100 canonical exposure:
--   exposure(metal) = SUM(delta_amount_mg) WHERE metal_type=? AND status='open'
-- D-101 hard cap check (inline, EVERY txn — sale+buy, all channels, no exception):
--   committed = SUM(open positions);  reserved = SUM(live inventory_pending_holds — D-105);
--   ALLOW iff  (committed + reserved + this_tx_delta)  stays within
--             [ −max_short_exposure_mg , +max_open_exposure_mg ].
--   Serialize (read committed + read reserved + compare + INSERT hold) with
--   pg_advisory_xact_lock(hashtext('treasury:'||metal_type)). Keep it tiny; NEVER hold across a gateway round-trip.

CREATE TABLE treasury_settings (
    metal_type VARCHAR(20) PRIMARY KEY,
    max_open_exposure_mg BIGINT NOT NULL,    -- D-47: سقف سمت فروش (exposure مثبت)
    max_short_exposure_mg BIGINT NOT NULL,   -- D-47: سقف سمت خرید/بازخرید (exposure منفی)
    warning_threshold_percent NUMERIC(5, 2) NOT NULL DEFAULT 70.0,
    auto_block_at_cap BOOLEAN NOT NULL DEFAULT TRUE
);
-- D-47: علاوه بر worker ۳۰s، چک inline سد سخت در لحظه‌ی هر تراکنش (فروش+خرید،
-- همه‌ی کانالها بدون استثنا). هر دو سقف per فلز قابل تغییر لحظهای اپراتور با audit.
-- D-101: داخل ناحیه‌ی advisory-lock با SELECT ساده خوانده شود (نه SELECT FOR UPDATE —
--   آن کل فروش‌ها را روی یک ردیف سریالایز و ویرایش زنده‌ی سقف را بلاک می‌کند).

CREATE TABLE treasury_position_snapshots (
    id BIGSERIAL PRIMARY KEY,
    metal_type VARCHAR(20) NOT NULL,
    total_open_exposure_mg BIGINT NOT NULL,
    user_owed_mg BIGINT NOT NULL,             -- bedshkar به user (sum across all wallets)
    physical_stock_mg BIGINT NOT NULL,        -- مجموع bars در انبارها
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```


---

## 4. Inter-Company Ledger

> Source: §6.3 — Ledger + Settle Actions
> Related decisions: [D-06b](01-decisions-audit-log.md) (real-time ledger replaces old settlement), [D-102](01-decisions-audit-log.md) (signed NET running account — FIFO/status removed)

```sql
-- D-102: SIGNED NET RUNNING ACCOUNT (replaces the old gross-FIFO + status model).
-- Each row is an append-only movement "debtor owes creditor amount_minor" (always > 0).
-- OUTSTANDING is never stored — it is the NET of all rows per unordered {company-pair, asset}:
--   net_B_owes_A(asset) = SUM(amount WHERE debtor=B AND creditor=A AND asset)
--                       − SUM(amount WHERE debtor=A AND creditor=B AND asset)
--   (positive ⇒ B owes A ; negative ⇒ A owes B ; zero ⇒ settled).
-- Opposite-direction movements (digital buy↔sell, buyback, D-84 commission offset) AUTO-NET in this
--   sum — no second independent obligation is ever created.
-- SETTLEMENT = append a row in the OPPOSITE direction (source_type='settlement', recorded_by set),
--   which moves the net toward zero. Rows are NEVER mutated. No status / settled_amount / FIFO consume.
CREATE TABLE inter_company_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debtor_company_id BIGINT NOT NULL REFERENCES companies(id),
    creditor_company_id BIGINT NOT NULL REFERENCES companies(id),
    asset_type VARCHAR(10) NOT NULL,  -- 'XAU_MG' | 'IRR'
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    -- mg برای gold (D-104: integer، FLOOR)، rial برای rial
    source_type VARCHAR(50) NOT NULL,
    -- 'sale' | 'digital_trade' | 'supplier_purchase' | 'commission_offset' | 'settlement' | 'manual_adjustment'
    source_order_id UUID NULL REFERENCES orders(id),
    notes TEXT NULL,
    recorded_by BIGINT NULL REFERENCES users(id),  -- NULL for auto obligation rows; set for operator settlement/adjustment rows
    idempotency_key VARCHAR(100) NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_companies_different CHECK (debtor_company_id <> creditor_company_id)
);
-- The net query is direction-agnostic, so index BOTH directions of the pair:
CREATE INDEX ix_icledger_pair ON inter_company_ledger (creditor_company_id, debtor_company_id, asset_type, created_at);
CREATE INDEX ix_icledger_pair_rev ON inter_company_ledger (debtor_company_id, creditor_company_id, asset_type, created_at);
CREATE INDEX ix_icledger_order ON inter_company_ledger (source_order_id);

-- D-102: the old `inter_company_settle_actions` table is REMOVED. A settlement is now a normal
--   ledger row (source_type='settlement', recorded_by); the sensitive operator action is captured
--   by audit_logs (mandatory per §17 / D-107). There is no FIFO "affected_ledger_ids" anymore.
```


---

## 5. Fulfillment

> Source: §8.2 — Tasks + Events
> Related decisions: [D-77, D-78, D-79, D-80](01-decisions-audit-log.md)

```sql
CREATE TABLE fulfillment_tasks (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    order_item_id BIGINT NOT NULL REFERENCES order_items(id),
    product_id BIGINT NOT NULL REFERENCES products(id),
    bar_id BIGINT NOT NULL REFERENCES bars(id),  -- D-77: شمش مشخص تخصیص‌یافته (D-49). انبار‌دار همین سریال را برمیدارد؛ اسکن سریال pick باید با این بخواند وگرنه خطا. (برای چند شمش، چند ردیف task)
    quantity INT NOT NULL,
    amount_mg BIGINT NULL,
    source_location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    destination_type VARCHAR(30) NOT NULL,
    -- customer_pickup | courier | store
    -- D-80: internal_transfer حذف شد — هر انتقال داخلی بین انبارها فقط از
    --   مسیر دو‌مرحله‌ای D-62 می‌رود. fulfillment فقط تحویل مرتبط با
    --   order_id مشتری است (همیشه order_id دارد).
    destination_address VARCHAR(500) NULL,
    courier_provider VARCHAR(50) NULL,
    tracking_number VARCHAR(100) NULL,
    assigned_to BIGINT NULL REFERENCES users(id),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    -- pending | picking | picked | packed | handed_over | delivered | cancelled
    -- D-79 (استثناها): delivery_failed | lost_in_transit | damaged
    --   هیچ‌کدام خود‌کار بسته نمیشوند — تصمیم اپراتور/حسابدار + audit + reason الزامی
    delivery_otp_hash VARCHAR(255) NULL,   -- D-78: OTP گیرنده؛ بدون آن delivered بسته نمی‌شود
    delivery_otp_expiry TIMESTAMPTZ NULL,  -- D-78
    delivered_confirmed_by BIGINT NULL REFERENCES users(id),  -- D-78: نقش مقصد (نه انبار‌دار مبدأ)
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    picked_at TIMESTAMPTZ NULL,
    packed_at TIMESTAMPTZ NULL,
    handed_over_at TIMESTAMPTZ NULL,       -- D-78: «از دست ما خارج شد» (انبار‌دار)، نه «رسید»
    delivered_at TIMESTAMPTZ NULL          -- D-78: فقط با OTP گیرنده ست می‌شود؛ bar.delivered_at هم همینجا
);
CREATE INDEX ix_fulfillment_status_created
    ON fulfillment_tasks (status, created_at);

CREATE TABLE fulfillment_events (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES fulfillment_tasks(id),
    event_type VARCHAR(30) NOT NULL,
    actor_id BIGINT NULL REFERENCES users(id),
    old_status VARCHAR(30) NULL,
    new_status VARCHAR(30) NOT NULL,
    notes TEXT NULL,
    metadata JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```


---

## 6. Identity

> Source: §11.1 — Users, Admin Users, Sessions, Bank Accounts

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    mobile VARCHAR(15) UNIQUE NOT NULL,
    national_id VARCHAR(20) UNIQUE NULL,
    first_name VARCHAR(100) NULL,
    last_name VARCHAR(100) NULL,
    birth_date DATE NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE admin_users (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(id),
    admin_role VARCHAR(50) NOT NULL,
    -- super_admin | admin | operator | accountant | warehouse | pricer
    permissions JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),
    refresh_token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    user_agent VARCHAR(500) NULL,
    ip_address INET NULL,
    revoked_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_bank_accounts (
    -- برای withdrawal ریالی
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    iban VARCHAR(50) NOT NULL,
    bank_name VARCHAR(100) NOT NULL,
    account_holder VARCHAR(200) NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```


---

## 7. KYC

> Source: §11.2 — KYC Records, User Level Defaults
> Related decisions: [D-61](01-decisions-audit-log.md)

```sql
CREATE TABLE kyc_records (
    user_id BIGINT PRIMARY KEY REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'NotStarted',
    user_level VARCHAR(20) NOT NULL DEFAULT 'L0',  -- D-108: canonical levels L0 | L1 | L2 (per D-61); value resolves to user_level_defaults.level
    shahkar_verified_at TIMESTAMPTZ NULL,
    shahkar_response JSONB NULL,
    documents JSONB NOT NULL DEFAULT '[]',
    -- Limits (بازنویسیs از user_level defaults)
    daily_buy_limit_rial BIGINT NULL,
    monthly_buy_limit_rial BIGINT NULL,
    daily_sell_limit_rial BIGINT NULL,
    monthly_sell_limit_rial BIGINT NULL,
    -- gold outflow limit: شامل physical_purchase_from_wallet و digital_trade sell
    -- (gold withdrawal جدا نداریم — D-31)
    daily_gold_outflow_limit_mg BIGINT NULL,
    monthly_gold_outflow_limit_mg BIGINT NULL,
    daily_rial_withdrawal_limit_rial BIGINT NULL,
    monthly_rial_withdrawal_limit_rial BIGINT NULL,
    requires_manual_approval BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_by BIGINT NULL REFERENCES users(id),
    reviewed_at TIMESTAMPTZ NULL,
    rejection_reason TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_level_defaults (
    level VARCHAR(20) PRIMARY KEY,   -- D-108: 'L0' | 'L1' | 'L2' (seed all three). Replaces Normal/Verified/Premium.
    daily_buy_limit_rial BIGINT NOT NULL,
    monthly_buy_limit_rial BIGINT NOT NULL,
    daily_sell_limit_rial BIGINT NOT NULL,
    monthly_sell_limit_rial BIGINT NOT NULL,
    daily_gold_outflow_limit_mg BIGINT NOT NULL,
    monthly_gold_outflow_limit_mg BIGINT NOT NULL,
    daily_rial_withdrawal_limit_rial BIGINT NOT NULL,
    monthly_rial_withdrawal_limit_rial BIGINT NOT NULL,
    notes TEXT NULL
);
```


---

## 8. Catalog

> Source: §11.3 — Products, Packaging, Images, Channel Availability, External Mappings
> Related decisions: [D-51](01-decisions-audit-log.md) (purity model)

> **مدل چندSKU:** یک کارخانه می‌تواند چندین مدل/طرح برای یک وزن یکسان داشته باشد (مثل «شمش ۱g امینزر مدل سیمرغ» و «شمش ۱g امینزر مدل گل رز»). هر مدل یک `product_id` مستقل با `model_code` یکتا دارد. توضیح بیشتر در بخش ۷.۴.

```sql
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(300) NOT NULL,                  -- "شمش 1گرمی امینزر مدل سیمرغ"
    model_code VARCHAR(50) NULL,                 -- "SIM-1G" — برای سریالسازی preorder
    product_type VARCHAR(30) NOT NULL,
    -- bar | melted | digital | coin | jewelry
    metal_type VARCHAR(20) NOT NULL,             -- gold | silver
    weight_mg BIGINT NOT NULL,
    purity INT NOT NULL,                         -- D-51: parts-per-1000 (0..1000)؛ فرمول وزن خالص همیشه ×purity/1000
    is_physical BOOLEAN NOT NULL,
    default_producer_company_id BIGINT NULL REFERENCES companies(id),
    buyback_percent NUMERIC(5, 2) NULL,          -- default به ازای هر محصول (بازنویسی در channel_pricing_formulas)
    purchase_wage_percent NUMERIC(5, 2) NULL,    -- اجرت طلایی خرید از کارخانه (metadata، supplier_purchase خارج از scope v1)
    packaging_type_id BIGINT NULL REFERENCES packaging_types(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE packaging_types (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,                  -- "پلمب کارتی"، "جعبه طلایی"، "بسته‌بندی هدیه"
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE product_images (...);
CREATE TABLE product_channel_availability (
    product_id BIGINT REFERENCES products(id),
    channel_id BIGINT REFERENCES sales_channels(id),
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (product_id, channel_id)
);
CREATE TABLE external_product_mappings (...);
```


---

## 9. Pricing

> Source: §11.4 — Price Sources, Configs, Internal Base Prices, Channel Formulas, Price Locks
> Related decisions: [D-65](01-decisions-audit-log.md) (pricing ladder), [D-72](01-decisions-audit-log.md) (spread), [D-50/D-28](01-decisions-audit-log.md) (lock TTL)

(مدل کامل مشابه بخش قبلی، ولی **بدون** tenant_id — pricing config مرکزی است.)

```sql
CREATE TABLE price_sources (...);
CREATE TABLE source_prices (...);
CREATE TABLE pricing_configs (
    id BIGSERIAL PRIMARY KEY,
    metal_type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_by BIGINT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_active_pricing_config
    ON pricing_configs (metal_type) WHERE is_active = TRUE;

CREATE TABLE pricing_config_sources (...);
CREATE TABLE internal_base_prices (
    id BIGSERIAL PRIMARY KEY,
    metal_type VARCHAR(20) NOT NULL,
    config_id BIGINT NOT NULL REFERENCES pricing_configs(id),
    price_per_gram_rial NUMERIC(20, 2) NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    calculation_snapshot JSONB NOT NULL,
    created_by BIGINT NULL REFERENCES users(id)
);
CREATE INDEX ix_internal_base_eff ON internal_base_prices (metal_type, effective_from DESC);

CREATE TABLE channel_pricing_formulas (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NULL REFERENCES brands(id),
    sales_channel_id BIGINT NULL REFERENCES sales_channels(id),
    product_id BIGINT NULL REFERENCES products(id),
    product_type VARCHAR(30) NULL,
    coefficient NUMERIC(8, 4) NOT NULL DEFAULT 1.0,
    margin_percent NUMERIC(6, 3) NOT NULL DEFAULT 0,
    fixed_fee_rial BIGINT NOT NULL DEFAULT 0,
    tax_percent NUMERIC(6, 3) NOT NULL DEFAULT 0,
    wage_type VARCHAR(20) NOT NULL DEFAULT 'none',  -- none | percent | fixed | per_gram
    wage_value NUMERIC(12, 4) NOT NULL DEFAULT 0,
    -- D-32: buyback_percent — درصد از value که موقع buyback (هر سه زیرflow)
    -- به wallet IRR کاربر برمیگردد. در order_items.buyback_credit_rial snapshot می‌شود.
    buyback_percent NUMERIC(6, 3) NOT NULL DEFAULT 0,
    rounding_policy VARCHAR(20) NOT NULL DEFAULT 'floor',
    -- D-27: floor بهعنوان default. می‌توان به round_half_up/ceiling/bankers تغییر داد به ازای هر فرمول
    lock_ttl_seconds INT NOT NULL DEFAULT 120,
    -- D-50 (بازنویسی D-28): ۲ دقیقه default، بازهی مجاز ۶۰s..۳۰۰s (کف ۱ دقیقه برای شرایط پرنوسان)
    dealer_tier_id BIGINT NULL,  -- D-65: بعد سطح. NULL=مشتری نهایی (P_retail)؛ مقدار=سطح همکار (P_partner). FK به dealer_tiers بعد از context دیلر اضافه شود. رزولوشن با priority.
    trade_side VARCHAR(10) NULL,  -- D-72: buy|sell|NULL. spread دو‌طرفه — قیمت خرید و فروش دیجیتال مارجین مستقل دارند. NULL=هر دو سمت. «کارمزد معامله»ی v4 همین مارجین است (مفهوم جدا نداریم).
    priority INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_lock_ttl CHECK (lock_ttl_seconds BETWEEN 60 AND 300)
);

CREATE TABLE price_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),
    sales_channel_id BIGINT NOT NULL REFERENCES sales_channels(id),
    brand_id BIGINT NOT NULL REFERENCES brands(id),
    product_id BIGINT NOT NULL REFERENCES products(id),
    quantity INT NOT NULL,
    amount_mg BIGINT NOT NULL,
    base_metal_price_per_gram_rial NUMERIC(20, 2) NOT NULL,
    source_prices_snapshot JSONB NOT NULL,
    formula_snapshot JSONB NOT NULL,
    final_price_rial BIGINT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    idempotency_key VARCHAR(100) NULL,
    used_in_order_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (idempotency_key)
);
```


---

## 10. Inventory

> Source: §11.5 — Bars, Reservations, Movements, Bulk Gold Inventory/Movements
> Related decisions: [D-49](01-decisions-audit-log.md) (custodial model), [D-71](01-decisions-audit-log.md) (sale_wallet_scope), [D-79](01-decisions-audit-log.md) (damage/loss)

```sql
CREATE TABLE bars (
    id BIGSERIAL PRIMARY KEY,
    serial_code VARCHAR(100) UNIQUE NOT NULL,
    product_id BIGINT NOT NULL REFERENCES products(id),
    producer_company_id BIGINT NOT NULL REFERENCES companies(id),
    owner_company_id BIGINT NOT NULL REFERENCES companies(id),
    -- مالک حقوقی فعلی شمش (تا قبل از فروش، مال یک شرکت است؛ بعد از فروش، مشتری در bars.customer_id)
    current_location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    assigned_channel_id BIGINT NULL REFERENCES sales_channels(id),
    -- اگر null باشد bar در pool عمومی است و موقع فروش می‌تواند به هر channel/brand بره
    -- اگر مقدار داشته باشد، فقط در آن channel قابل فروش است
    claim_code VARCHAR(50) UNIQUE NULL,
    customer_id BIGINT NULL REFERENCES users(id),
    sale_wallet_scope VARCHAR(20) NULL,  -- D-71: goldis|aminzar|talamala — در لحظه‌ی فروش از scope سفارش پر، سپس IMMUTABLE (انتقال مالکیت عوضش نمیکند). NULL=هنوز فروش‌نرفته. مبنای قطعی بازخرید/گزارش/scope. بازخرید آنلاین فقط در همین scope مجاز است.
    is_preorder BOOLEAN NOT NULL DEFAULT FALSE,
    -- TRUE = سریال از سیستم تولید شده ولی فیزیکی تولید نشده (در کارخانه)
    -- بعد از تحویل کارخانه → Goldis: is_preorder=FALSE + status: RAW→ASSIGNED + location: factory→warehouse
    -- (بخش ۷.۳)
    status VARCHAR(20) NOT NULL DEFAULT 'RAW',
    -- RAW       : تولید شده / در انبار (قابل فروش)
    -- ASSIGNED  : برای channel تخصیص‌یافته (قابل reserve)
    -- RESERVED  : موقتا رزرو شده (POS یا checkout)
    -- SOLD      : فروختهشده (مالک دارد — custodial یا تحویل‌شده)
    -- DAMAGED   : آسیبدیده / پلمب‌شکسته → نیاز به بررسی، قابل فروش نیست (D-79)
    -- LOST      : گم/دزدیده → رویداد زیان، خزانه compensate (D-79)
    -- IN_INSPECTION : در حال بررسی (damaged return، اصالت‌سنجی buyback) → تا confirm نشده قابل فروش نیست
    reserved_customer_id BIGINT NULL REFERENCES users(id),
    reserved_until TIMESTAMPTZ NULL,
    delivered_at TIMESTAMPTZ NULL,
    version INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_bars_preorder ON bars (is_preorder) WHERE is_preorder = TRUE;
CREATE INDEX ix_bars_location_status ON bars (current_location_id, status);
CREATE INDEX ix_bars_channel_status ON bars (assigned_channel_id, status);

CREATE TABLE inventory_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bar_id BIGINT NOT NULL REFERENCES bars(id),
    user_id BIGINT NOT NULL REFERENCES users(id),
    sales_channel_id BIGINT NOT NULL REFERENCES sales_channels(id),
    order_id UUID NULL,
    cart_id BIGINT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'reserved',
    expires_at TIMESTAMPTZ NOT NULL,
    idempotency_key VARCHAR(100) NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE inventory_movements (
    id BIGSERIAL PRIMARY KEY,
    bar_id BIGINT NOT NULL REFERENCES bars(id),
    movement_type VARCHAR(30) NOT NULL,
    from_location_id BIGINT NULL REFERENCES inventory_locations(id),
    to_location_id BIGINT NULL REFERENCES inventory_locations(id),
    reference_type VARCHAR(50) NULL,
    reference_id VARCHAR(100) NULL,
    actor_id BIGINT NULL REFERENCES users(id),
    metadata JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- P0-8: Bulk Gold Inventory (raw/melted gold by weight, no serial)
-- برای ذخیرهی طلای خام/ذوبشده که سریالدار نیستند (granules، large bars from smelting)
-- مثلا: «۱۰۰g طلای ۷۵۰ خام در انبار Goldis»
CREATE TABLE bulk_gold_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    owner_company_id BIGINT NOT NULL REFERENCES companies(id),
    metal_type VARCHAR(20) NOT NULL,           -- gold | silver
    purity INT NOT NULL,                       -- parts-per-1000 (750, 999, etc.)
    total_weight_mg BIGINT NOT NULL CHECK (total_weight_mg > 0),
    total_pure_weight_mg BIGINT NOT NULL,     -- weight_mg × purity / 1000
    grade VARCHAR(50) NULL,                    -- granules | ingot | smelted_scrap | etc.
    acquisition_source VARCHAR(50) NOT NULL,  -- hedge_buy | supplier_purchase | scrap_remelting | physical_buyback_return | etc.
    reference_type VARCHAR(50) NULL,           -- inter_company_ledger | purchase_order | buyback_request | etc.
    reference_id VARCHAR(100) NULL,
    -- Tracking
    received_from VARCHAR(100) NULL,           -- supplier/miner name یا previous location description
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_counted_at TIMESTAMPTZ NULL,
    last_counted_by BIGINT NULL REFERENCES users(id),
    notes TEXT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_bulk_gold_location ON bulk_gold_inventory (location_id);
CREATE INDEX ix_bulk_gold_owner ON bulk_gold_inventory (owner_company_id);
CREATE INDEX ix_bulk_gold_source ON bulk_gold_inventory (acquisition_source, metal_type);

-- Ledger for bulk gold movements (in/out)
CREATE TABLE bulk_gold_movements (
    id BIGSERIAL PRIMARY KEY,
    bulk_gold_id UUID NOT NULL REFERENCES bulk_gold_inventory(id),
    movement_type VARCHAR(30) NOT NULL,      -- intake | withdrawal | conversion | recount | etc.
    from_location_id BIGINT NULL REFERENCES inventory_locations(id),
    to_location_id BIGINT NULL REFERENCES inventory_locations(id),
    weight_mg_delta BIGINT NOT NULL,          -- positive=intake، negative=withdrawal
    reason VARCHAR(100) NULL,
    actor_id BIGINT NULL REFERENCES users(id),
    approval_id BIGINT NULL REFERENCES users(id),  -- for withdrawals/conversions
    metadata JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_bulk_movements_inventory ON bulk_gold_movements (bulk_gold_id);
```


---

## 11. Order

> Source: §11.6 — Orders, Items, Status Log, Withdrawal Details, Payment Allocations, Physical Buyback
> Related decisions: [D-31](01-decisions-audit-log.md) (no gold withdrawal), [D-32](01-decisions-audit-log.md) (buyback replaces refund), [D-39](01-decisions-audit-log.md) (split payment), [D-65](01-decisions-audit-log.md) (pricing ladder)

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),

    -- ابعاد چندشرکتی
    brand_id BIGINT NOT NULL REFERENCES brands(id),
    sales_channel_id BIGINT NOT NULL REFERENCES sales_channels(id),
    seller_company_id BIGINT NOT NULL REFERENCES companies(id),
    producer_company_id BIGINT NULL REFERENCES companies(id),    -- از bar/product
    operator_company_id BIGINT NOT NULL REFERENCES companies(id),
    payment_account_id BIGINT NULL REFERENCES payment_accounts(id),
    payment_receiver_company_id BIGINT NULL REFERENCES companies(id),
    -- settlement_rule_id حذف شد (D-06b: inter_company_ledger مستقیم استفاده می‌شود)
    fulfillment_location_id BIGINT NULL REFERENCES inventory_locations(id),

    order_type VARCHAR(30) NOT NULL,
    -- purchase | digital_trade | withdrawal_rial | pos_sale
    -- marketplace_sale | physical_purchase_from_wallet | buyback
    -- (gold withdrawal حذف شد — D-31. refund حذف شد — D-32)
    trade_side VARCHAR(10) NULL,             -- buy | sell (فقط digital_trade؛ بازخرید دیجیتال = همان digital_trade sell — D-68)
    -- withdrawal_asset removed (فقط rial withdrawal داریم)
    status VARCHAR(30) NOT NULL,
    total_amount_rial BIGINT NULL,
    total_gold_amount_mg BIGINT NULL,
    payment_asset VARCHAR(20) NULL,          -- IRR | XAU_MG
    price_lock_id UUID NULL REFERENCES price_locks(id),
    payment_id UUID NULL,
    cancellation_reason TEXT NULL,
    cancelled_at TIMESTAMPTZ NULL,
    paid_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_orders_user_status ON orders (user_id, status);
CREATE INDEX ix_orders_channel_created ON orders (sales_channel_id, created_at DESC);
CREATE INDEX ix_orders_brand_created ON orders (brand_id, created_at DESC);

CREATE TABLE order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id),
    bar_id BIGINT NULL REFERENCES bars(id),
    quantity INT NOT NULL,
    amount_mg BIGINT NULL,
    unit_price_rial BIGINT NULL,
    final_price_rial BIGINT NULL,
    raw_hedge_price_rial BIGINT NULL,        -- D-65: P_hedge_per_mg(لحظه‌ی فروش) × pure_gold_mg — تنها مبنای inter_company_ledger (cost_price_rial سابق؛ supplier_price_rial حذف شد — D-48)
    producer_company_id BIGINT NULL REFERENCES companies(id),
    -- D-32: buyback snapshot moment of purchase. در buyback (هر زیرflow) به wallet IRR کاربر برمیگردد.
    buyback_credit_rial BIGINT NOT NULL DEFAULT 0,
    -- وزن خالص طلا (cost) برای buyback. در صورت buyback به wallet XAU_MG برمیگردد.
    -- محاسبه: weight × purity / 1000
    pure_gold_mg BIGINT NULL,
    price_snapshot JSONB NOT NULL,
    metadata JSONB NULL
);

CREATE TABLE order_status_log (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    old_status VARCHAR(30) NULL,
    new_status VARCHAR(30) NOT NULL,
    changed_by BIGINT NULL REFERENCES users(id),
    reason TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- withdrawal فقط برای ریال — gold withdrawal در v5 وجود ندارد (D-31)
CREATE TABLE withdrawal_details (
    order_id UUID PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
    bank_account_id BIGINT NOT NULL REFERENCES user_bank_accounts(id),
    payout_provider VARCHAR(50) NULL,
    payout_tracking_code VARCHAR(100) NULL,
    operator_id BIGINT NULL REFERENCES users(id),
    operator_decided_at TIMESTAMPTZ NULL,
    operator_note TEXT NULL,
    rejection_reason TEXT NULL,
    failure_reason TEXT NULL,
    completed_at TIMESTAMPTZ NULL
);

-- جدول order_payment_allocations
-- برای پشتیبانی از split payment در physical_purchase_from_wallet
-- (و آینده برای هر orderی که چند منبع پرداخت دارد).
-- هر allocation یک منبع پرداخت را explicit ثبت میکند با link به wallet_lock یا payment.
-- این جدول split payment را قابل audit، rollback، و idempotent میکند.
CREATE TABLE order_payment_allocations (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    allocation_type VARCHAR(30) NOT NULL,
    -- wallet_gold | wallet_rial | gateway_rial
    company_id BIGINT NULL REFERENCES companies(id),       -- legal entity صاحب wallet
    asset_type_id BIGINT NULL REFERENCES asset_types(id),  -- IRR یا XAU_MG
    amount_minor BIGINT NOT NULL,                          -- مقدار (rial یا mg)
    wallet_lock_id UUID NULL REFERENCES wallet_locks(id),
    payment_id UUID NULL,                                  -- FK اضافه می‌شود بعد از payments
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending | locked | paid | consumed | released | failed
    metadata JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_allocation_link CHECK (
        (allocation_type IN ('wallet_gold', 'wallet_rial') AND wallet_lock_id IS NOT NULL) OR
        (allocation_type = 'gateway_rial' AND payment_id IS NOT NULL)
    )
);
CREATE INDEX ix_allocations_order ON order_payment_allocations (order_id);
CREATE INDEX ix_allocations_status ON order_payment_allocations (status)
    WHERE status IN ('pending', 'locked');

-- نکته (D-39 از Q&A، Q-01 resolved):
-- در physical_purchase_from_wallet با split:
--   ۳ allocation ساخته می‌شود (حداکثر): wallet_gold + wallet_rial + gateway_rial
--   هر کدام lock/consume/release جدا دارند.
--   atomic confirm: یا همه consume میشوند یا همه release.

-- D-32: physical_buyback request — برای zir-flow (b) بخش ۱۲.۵.۲
-- state machine: PhysicalRequested → PhysicalReceived → AuthenticityVerified →
--                Approved → WalletCredited → Completed | Rejected
CREATE TABLE physical_buyback_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),
    bar_id BIGINT NOT NULL REFERENCES bars(id),
    source_order_id UUID NOT NULL REFERENCES orders(id),  -- order اصلی خرید
    source_order_item_id BIGINT NOT NULL REFERENCES order_items(id),
    target_location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    -- باید target_location.can_buyback = TRUE باشد
    status VARCHAR(30) NOT NULL DEFAULT 'PhysicalRequested',
    -- PhysicalRequested | PhysicalReceived | AuthenticityVerified |
    -- Approved | WalletCredited | Completed | Rejected
    received_by BIGINT NULL REFERENCES users(id),
    received_at TIMESTAMPTZ NULL,
    verified_by BIGINT NULL REFERENCES users(id),
    verified_at TIMESTAMPTZ NULL,
    approved_by BIGINT NULL REFERENCES users(id),
    approved_at TIMESTAMPTZ NULL,
    rejected_at TIMESTAMPTZ NULL,
    rejection_reason TEXT NULL,
    -- snapshot از مقادیر در order اصلی (برای اطمینان از consistency)
    refund_gold_mg BIGINT NOT NULL,        -- = order_item.pure_gold_mg
    refund_buyback_credit_rial BIGINT NOT NULL,  -- = order_item.buyback_credit_rial
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL
);
CREATE INDEX ix_physical_buyback_user ON physical_buyback_requests (user_id);
CREATE INDEX ix_physical_buyback_location_status
    ON physical_buyback_requests (target_location_id, status);
```


---

## 12. Payment

> Source: §11.7 — Providers, Payments, Transactions, Wallet Topups
> Related decisions: [D-92](01-decisions-audit-log.md) (payment state machine), [D-76](01-decisions-audit-log.md) (scope-keyed topup)

```sql
CREATE TABLE payment_providers (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,        -- zibal | sepehr | top | parsian
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- payment_accounts قبلا تعریف شده بخش ۳.۲

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NULL REFERENCES orders(id),          -- nullable برای topup/wallet charge (بدون order)
    user_id BIGINT NOT NULL REFERENCES users(id),
    payment_account_id BIGINT NOT NULL REFERENCES payment_accounts(id),
    payment_receiver_company_id BIGINT NOT NULL REFERENCES companies(id),
    amount_rial BIGINT NOT NULL,
    
    -- D-92: State Machine columns (Critical Subsystems)
    payment_state VARCHAR(30) NOT NULL DEFAULT 'pending',
    -- pending | gateway_verified_pending | inter_company_ledger_created | finalized | failed | cancelled
    -- ⚠️ D-103: payment_state is OBSERVABILITY / alerting ONLY. Finalize is ONE atomic transaction
    --   (gateway-verify OUTSIDE the tx; then wallet ledger → treasury → inter-company → outbox → order.Paid
    --    all INSIDE one tx). Crash recovery = idempotent retry of the WHOLE op keyed on idempotency_key.
    --   No control-flow branch may read payment_state to resume a saga; these are not checkpoints.
    gateway VARCHAR(50) NULL,                          -- درگاه استفاده‌شده (zibal, sepehr, top, parsian)
    gateway_ref VARCHAR(100) NULL,                     -- reference from gateway
    gateway_verified_at TIMESTAMPTZ NULL,              -- when gateway confirmed payment
    
    -- Legacy fields (backward compatibility)
    authority VARCHAR(255) NULL,                       -- درگاه reference
    tracking_code VARCHAR(255) NULL,                   -- tracking code
    rrn VARCHAR(50) NULL,                              -- RRN
    
    -- Ledger integration
    ledger_entry_id UUID NULL REFERENCES inter_company_ledger(id),
    finalized_at TIMESTAMPTZ NULL,
    failed_at TIMESTAMPTZ NULL,
    failure_reason TEXT NULL,
    
    -- Idempotency (D-92: critical for recovery after crash)
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE payment_transactions (...);  -- مشابه قبل

-- بعد از ایجاد payments، FK روی order_payment_allocations.payment_id:
ALTER TABLE order_payment_allocations
    ADD CONSTRAINT fk_allocation_payment
    FOREIGN KEY (payment_id) REFERENCES payments(id);

-- شارژ wallet ریالی (Rial Topup) — بخش ۱۲.۵.۴
CREATE TABLE wallet_topups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),
    wallet_scope VARCHAR(20) NOT NULL,  -- D-76: goldis|aminzar|talamala — از فرانت/کانال resolve، کیف همان scope شارژ می‌شود (ایزوله، D-46)
    company_id BIGINT NOT NULL REFERENCES companies(id),  -- D-76: مشتق از scope (legal entity برای حسابداری)
    brand_id BIGINT NOT NULL REFERENCES brands(id),       -- از کدام brand شارژ شد
    sales_channel_id BIGINT NOT NULL REFERENCES sales_channels(id),
    amount_rial BIGINT NOT NULL CHECK (amount_rial > 0),
    payment_id UUID NULL REFERENCES payments(id),
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    -- created | gateway_started | completed | failed | expired
    idempotency_key VARCHAR(100) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    UNIQUE (wallet_scope, user_id, idempotency_key)  -- P0-1.1 fixed: scope-keyed، not company_id (goldis+aminzar share شرکت گلدیس)
);
CREATE INDEX ix_wallet_topups_user ON wallet_topups (user_id, created_at DESC);
```


---

## 13. Outbox + Audit

> Source: §11.8 — Outbox Events, Audit Logs

(مشابه نسخه‌ی قبلی، با اضافه‌شدن `tenant_id` → `company_id` در audit.)

```sql
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id VARCHAR(100) NOT NULL,
    company_id BIGINT NULL REFERENCES companies(id),
    brand_id BIGINT NULL REFERENCES brands(id),
    channel_id BIGINT NULL REFERENCES sales_channels(id),
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    retry_count INT NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ NULL,
    next_retry_at TIMESTAMPTZ NULL
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_type VARCHAR(20) NOT NULL,
    actor_id BIGINT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100) NOT NULL,
    company_id BIGINT NULL REFERENCES companies(id),
    old_value JSONB NULL,
    new_value JSONB NULL,
    ip_address INET NULL,
    user_agent VARCHAR(500) NULL,
    metadata JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```


---

## 14. Supplementary

> Source: §11.9 — Tables from override decisions (D-62/D-63/D-73/D-96/D-97/D-99)

> این جداول از تصمیمات override می‌آیند و در SQL اصلی نبودند.

```sql
-- D-63: لیست اولویت‌دار درگاه به ازای هر کانال + fallback خود‌کار
-- (جایگزین تکمقداری sales_channels.default_payment_account_id؛
--  آن ستون میماند فقط بهعنوان «اولین پیش‌فرض» / سازگاری)
CREATE TABLE sales_channel_payment_accounts (
    id BIGSERIAL PRIMARY KEY,
    sales_channel_id BIGINT NOT NULL REFERENCES sales_channels(id),
    payment_account_id BIGINT NOT NULL REFERENCES payment_accounts(id),
    priority INT NOT NULL DEFAULT 0,           -- کوچکتر = اولویت بالاتر
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,  -- اپراتور می‌تواند موقتا غیرفعال کند
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (sales_channel_id, payment_account_id)
);
CREATE INDEX ix_scpa_channel_prio
    ON sales_channel_payment_accounts (sales_channel_id, priority)
    WHERE is_enabled = TRUE;
-- موقع پرداخت: اولین payment_account enabled و سالم؛ اگر down → بعدی.
-- هر بار درگاهی خطا/down داد (حتی اگر fallback پوشش داد) → notification+audit (D-63).

-- جدول پایه‌ی سطوح نمایندگان (پیشنیاز D-65 و D-94)
CREATE TABLE dealer_tiers (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- D-94 (اصلاح‌شده): فروش نمایندهای (POS یا دیگر) — سند مرجع برای کمیسیون
CREATE TABLE dealer_sales (
    id BIGSERIAL PRIMARY KEY,
    dealer_user_id BIGINT NOT NULL REFERENCES users(id),    -- نماینده‌ی فروشنده
    order_id UUID NOT NULL REFERENCES orders(id),           -- سفارش پشتیبان
    bar_id BIGINT NULL REFERENCES bars(id),                 -- شمش فروختهشده (اختیاری — برای سفارشهای دیجیتالی)
    pure_gold_mg BIGINT NOT NULL CHECK (pure_gold_mg > 0),  -- مقدار طلای خالص
    metal_profit_mg BIGINT NOT NULL DEFAULT 0,              -- سود نماینده در طلا (مبنای کمیسیون)
    sale_type VARCHAR(30) NOT NULL DEFAULT 'pos_sale',      -- pos_sale | marketplace | direct | ...
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_dealer_sales_dealer ON dealer_sales (dealer_user_id, created_at DESC);
CREATE INDEX ix_dealer_sales_order ON dealer_sales (order_id);

-- D-73: نرخ کمیسیون نماینده (Gold-for-Gold)
CREATE TABLE dealer_commission_rates (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NULL REFERENCES products(id),     -- پیش‌فرض محصول
    product_type VARCHAR(30) NULL,                        -- یا per نوع محصول
    dealer_tier_id BIGINT NULL,                           -- NULL=همه‌ی سطوح؛ FK بعد از dealer_tiers
    trade_side VARCHAR(10) NOT NULL,                      -- sale | buyback
    commission_percent NUMERIC(6,3) NOT NULL,             -- درصد pure_gold_mg تراکنش (D-73 بند۵)
    priority INT NOT NULL DEFAULT 0,                       -- رزولوشن مشخصترین، مثل D-65
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_dcr_side CHECK (trade_side IN ('sale','buyback'))
);
-- نگهبان (D-73): فروش → Σکمیسیون ≤ (P_retail−P_hedge)؛
--   بازخرید → کمیسیون ≤ اسپرد بازخرید؛ نقض → رد/هشدار اپراتور.

-- D-73 (P۱): تسویه‌ی کمیسیون نماینده — جدا از inter_company_ledger
-- (آن شرکت↔شرکت است؛ نماینده کاربر است). بدهی طلایی TalaMala→نماینده.
CREATE TABLE dealer_commission_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_user_id BIGINT NOT NULL REFERENCES users(id),
    seller_company_id BIGINT NOT NULL REFERENCES companies(id),  -- بدهکار (TalaMala)
    dealer_sale_id BIGINT NULL,                 -- FK به DealerSale (context دیلر)
    trade_side VARCHAR(10) NOT NULL,            -- sale | buyback
    amount_mg BIGINT NOT NULL CHECK (amount_mg > 0),  -- طلا (Gold-for-Gold)
    status VARCHAR(20) NOT NULL DEFAULT 'open', -- open | partial | settled | cancelled
    settled_amount_mg BIGINT NOT NULL DEFAULT 0,
    -- D-73 بند۷: کمیسیون بازخرید فقط بعد از AuthenticityVerified ثبت شود
    -- D-73 P۳: واریز این طلا به کیف نماینده یک پای خزانهای +pure_gold_mg
    --   میسازد و تابع سقفهای D-47 است.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    settled_at TIMESTAMPTZ NULL,
    settled_by BIGINT NULL REFERENCES users(id),
    CONSTRAINT chk_dcl_settled CHECK (settled_amount_mg <= amount_mg)
);
CREATE INDEX ix_dcl_dealer_status
    ON dealer_commission_ledger (dealer_user_id, status);

-- D-62: انتقال بینانبار دو‌مرحله‌ای (DRAFT→DISPATCHED→RECEIVED→COMPLETED|DISCREPANCY)
CREATE TABLE inventory_transfer_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_code VARCHAR(50) UNIQUE NOT NULL,   -- TRF-20260518-001
    source_location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    destination_location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    in_transit_location_id BIGINT NULL REFERENCES inventory_locations(id),
    -- virtual in-transit location (D-62: موجودی در راه)
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    -- DRAFT | DISPATCHED | RECEIVED | COMPLETED | DISCREPANCY | CANCELLED
    otp_hash VARCHAR(255) NULL,        -- D-62: OTP تحویل اجباری بین مبدأ/مقصد
    otp_expiry TIMESTAMPTZ NULL,
    created_by BIGINT NOT NULL REFERENCES users(id),
    dispatched_by BIGINT NULL REFERENCES users(id),
    received_by BIGINT NULL REFERENCES users(id),
    completed_by BIGINT NULL REFERENCES users(id),
    notes TEXT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    dispatched_at TIMESTAMPTZ NULL,
    received_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    CONSTRAINT chk_itd_locations
        CHECK (source_location_id != destination_location_id),
    -- D-107: separation of duties — the dispatcher must not also be the receiver
    CONSTRAINT chk_itd_maker_checker
        CHECK (dispatched_by IS NULL OR received_by IS NULL OR dispatched_by <> received_by)
);
CREATE INDEX ix_itd_status ON inventory_transfer_documents (status, created_at DESC);
CREATE INDEX ix_itd_source ON inventory_transfer_documents (source_location_id);
CREATE INDEX ix_itd_dest ON inventory_transfer_documents (destination_location_id);

CREATE TABLE inventory_transfer_items (
    id BIGSERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES inventory_transfer_documents(id) ON DELETE CASCADE,
    bar_id BIGINT NOT NULL REFERENCES bars(id),
    dispatch_snapshot JSONB NULL,      -- snapshot of bar at dispatch time
    item_status VARCHAR(20) NOT NULL DEFAULT 'expected',
    -- expected | dispatched | received | missing | unexpected
    scanned_dispatch_at TIMESTAMPTZ NULL,
    scanned_receipt_at TIMESTAMPTZ NULL,
    discrepancy_reason TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_iti_document ON inventory_transfer_items (document_id);
CREATE INDEX ix_iti_bar ON inventory_transfer_items (bar_id);
CREATE UNIQUE INDEX uq_iti_doc_bar ON inventory_transfer_items (document_id, bar_id);

-- D-96: جدول reconciliations برای Price Lock (D-96)
CREATE TABLE payment_reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(id),
    order_id UUID NOT NULL REFERENCES orders(id),
    authorized_amount_rial BIGINT NOT NULL,           -- مبلغ auth شده
    actual_price_at_payment_rial BIGINT NOT NULL,     -- قیمت new
    variance_rial BIGINT NOT NULL,                     -- تفاوت (signed)
    variance_percent NUMERIC(5,2) NOT NULL,            -- percentage
    reconciliation_status VARCHAR(20) DEFAULT 'pending',
    -- pending | auto_approved | auto_adjusted | manual_review | rejected
    treasury_adjustment_mg BIGINT NULL,                -- D-104: integer mg, FLOOR (was NUMERIC(12,4))
    adjustment_reason TEXT NULL,
    reviewed_by BIGINT NULL REFERENCES users(id),      -- admin review
    reviewed_at TIMESTAMPTZ NULL,
    approved_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_payment_recon_payment ON payment_reconciliations (payment_id);
CREATE INDEX ix_payment_recon_status ON payment_reconciliations (reconciliation_status, created_at DESC);

-- D-97/D-101: Pending Reserves — soft treasury hold at checkout, finalized into a treasury_position at PaymentVerified.
-- D-104: integer mg (BIGINT). D-105: holds EXPIRE — an abandoned checkout must not throttle the cap forever.
CREATE TABLE inventory_pending_holds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    metal_type VARCHAR(20) NOT NULL DEFAULT 'gold',    -- D-101: the cap is per metal, so reserved-sum filters by metal
    wallet_scope VARCHAR(20) NOT NULL,
    pure_gold_mg_reserved BIGINT NOT NULL,             -- D-104: integer mg, FLOOR (was NUMERIC(12,4))
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,                   -- D-105: TTL; lock_expirer releases stale holds
    finalized_at TIMESTAMPTZ NULL,                     -- set when payment confirmed (→ becomes a treasury_position)
    released_at TIMESTAMPTZ NULL,                      -- set when order cancelled OR expired
    CONSTRAINT chk_only_one_state
        CHECK ( (finalized_at IS NULL AND released_at IS NULL) OR
                (finalized_at IS NOT NULL AND released_at IS NULL) OR
                (finalized_at IS NULL AND released_at IS NOT NULL) ),
    UNIQUE (order_id)  -- one hold per order (an idempotent checkout retry maps to the same order_id, never a 2nd hold)
);
-- D-101 reserved-sum used by the cap check counts ONLY LIVE holds:
--   SUM(pure_gold_mg_reserved) WHERE metal_type=? AND finalized_at IS NULL
--                                    AND released_at IS NULL AND expires_at > now()
CREATE INDEX ix_hold_live ON inventory_pending_holds (metal_type)
    WHERE finalized_at IS NULL AND released_at IS NULL;

-- D-99: POS Offline Queue (D-99)
CREATE TABLE pos_pending_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_id BIGINT NOT NULL REFERENCES users(id),
    pos_session_id VARCHAR(100) NOT NULL,
    request_id VARCHAR(100) NOT NULL,
    sale_data JSONB NOT NULL,                          -- complete sale JSON
    payment_ref VARCHAR(100) NULL,                     -- gateway ref
    request_state VARCHAR(30) NOT NULL DEFAULT 'received',
    -- received | processing | pos_confirmed | server_confirmed | failed
    server_confirmed_at TIMESTAMPTZ NULL,
    error_reason TEXT NULL,
    expires_at TIMESTAMPTZ NOT NULL,                   -- 24-hour TTL
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (dealer_id, pos_session_id, request_id)
);
CREATE INDEX ix_pos_request_dealer ON pos_pending_requests (dealer_id, request_state);
CREATE INDEX ix_pos_request_expires ON pos_pending_requests (expires_at);
```

---

## 15. POS Devices & Transactions

> Source: §9.2 — POS device registration, transaction tracking, reconciliation
> Related: [POS as First-class Sales Channel](02-domain-models.md#۹-pos-as-first-class-sales-channel)

```sql
CREATE TABLE pos_devices (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    sales_channel_id BIGINT NOT NULL REFERENCES sales_channels(id),
    terminal_id VARCHAR(100) NOT NULL,
    device_id VARCHAR(100) NULL,
    dealer_id BIGINT NULL,                   -- اگر متعلق به dealer است
    api_key_hash VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pos_transactions (
    id BIGSERIAL PRIMARY KEY,
    pos_device_id BIGINT NOT NULL REFERENCES pos_devices(id),
    payment_account_id BIGINT NOT NULL REFERENCES payment_accounts(id),
    terminal_id VARCHAR(100) NOT NULL,
    trace_number VARCHAR(50) NOT NULL,
    rrn VARCHAR(50) NULL,
    amount_rial BIGINT NOT NULL,
    paid_at TIMESTAMPTZ NOT NULL,
    raw_data JSONB NULL,
    matched_order_id UUID NULL REFERENCES orders(id),
    settlement_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    reconciliation_status VARCHAR(20) NOT NULL DEFAULT 'unmatched',
    -- unmatched | matched | discrepancy
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (terminal_id, trace_number)
);
```

