# Reference — Identity, KYC & User Model

> Cross-cutting reference for user identity, authentication, authorization,
> KYC levels/limits, Shahkar integration, and the dealer/admin role model.

> **DRY rule:** No SQL here. Canonical schemas → [Schema Index](../03-schema-index.md).
> Decision rationale → [Decisions](../01-decisions-audit-log.md).

---

## ۱. User Model — Single Table, Multiple Roles

### ۱.۱. ساختار

یک جدول `users` با فیلدهای مشترک. نقش‌ها via `admin_users` (join table) مشخص می‌شوند:

- **Customer:** هر user implicitly یک مشتری است
- **Admin:** ردیف در `admin_users` با `admin_role` + `permissions` JSON
- **Dealer:** فیلدهای dealer روی user + سطح‌بندی via `dealer_tiers`

### ۱.۲. Bank Accounts

- `user_bank_accounts`: IBAN + bank_name + account_holder + is_verified
- **D-64:** حساب بانکی باید به نام خود کاربر باشد (national_id match). برداشت به حساب شخص ثالث **ممنوع**.

> Canonical schemas: [Identity](../03-schema-index.md#6-identity)

---

## ۲. Authentication

### ۲.۱. JWT Model

- **Access token:** TTL = 15 min (Bearer header یا httpOnly cookie)
- **Refresh token:** TTL = 30 days, stored as hash in `sessions` table
- Session includes: user_agent, ip_address, revoked_at

### ۲.۲. Auth Methods per Actor

| Actor | Method | Details |
|-------|--------|---------|
| Customer/Dealer | OTP via SMS | `POST /auth/send-otp` → `POST /auth/verify-otp` → JWT |
| Admin | OTP via SMS | Same flow, validated against `admin_users` |
| POS Device | API Key | `api_key_hash` in `pos_devices` table |
| Marketplace Adapter | Service credentials | Per-adapter config |

### ۲.۳. Session Management

- `sessions` table tracks active refresh tokens
- Revocation: `revoked_at` timestamp → token rejected on refresh
- Multiple sessions per user allowed

---

## ۳. Authorization — RBAC + ABAC

### ۳.۱. Admin Roles

| Role | Scope | Description |
|------|-------|-------------|
| `super_admin` | Global | Full access, all permissions |
| `admin` | Global | Near-full access |
| `operator` | Per-company | عملیاتی — fulfillment, inventory, withdrawal approve |
| `accountant` | Per-company | Settlement, treasury, financial reports |
| `warehouse` | Per-location | Inventory management, fulfillment |
| `pricer` | Global | Pricing config, price source management |
| `dealer` | Per-dealer | POS sale, inventory at dealer location |

### ۳.۲. Permission Hierarchy

```
view → create → edit → full
```

هر سطح شامل تمام سطوح قبلی. ذخیره: JSON dict in `admin_users.permissions`:
```json
{"products": "edit", "orders": "view", "settlement": "full"}
```

### ۳.۳. ABAC Rules

- `accountant` فقط settlement خودش (company-bound) را تأیید میکند
- Route protection: `Depends(require_permission("settlement", level="approve"))`
- Dealer فقط inventory و sales خودش را میبیند

---

## ۴. KYC (Know Your Customer)

### ۴.۱. KYC Status Flow

```
NotStarted → Pending → Approved | Rejected
                        ↓
                   (requires_manual_approval=TRUE → admin review)
```

### ۴.۲. User Levels ([D-61](../01-decisions-audit-log.md))

| Level | KYC Requirement | Limits |
|-------|----------------|--------|
| `Normal` | فقط موبایل | حداقل (مشاهده + خریدهای خُرد) |
| `Verified` | Shahkar + national_id | متوسط |
| `Premium` | Verified + اسناد اضافی | حداکثر |

### ۴.۳. Limit Types (per level + per user override)

| Limit | Unit | Applies to |
|-------|------|-----------|
| `daily_buy_limit_rial` | rial | خرید روزانه |
| `monthly_buy_limit_rial` | rial | خرید ماهانه |
| `daily_sell_limit_rial` | rial | فروش روزانه |
| `monthly_sell_limit_rial` | rial | فروش ماهانه |
| `daily_gold_outflow_limit_mg` | mg | خروج طلا (physical_purchase + digital_sell) |
| `monthly_gold_outflow_limit_mg` | mg | خروج طلا ماهانه |
| `daily_rial_withdrawal_limit_rial` | rial | برداشت ریال روزانه |
| `monthly_rial_withdrawal_limit_rial` | rial | برداشت ریال ماهانه |

- Default limits per level in `user_level_defaults`
- Per-user override in `kyc_records` (NULL = use default)
- **D-31:** Gold withdrawal removed — gold outflow = `physical_purchase_from_wallet` + `digital_trade sell`

### ۴.۴. Shahkar Integration

- Sub-module: `kyc.shahkar`
- `verify(mobile, national_id) → ShahkarResult`
- Cache result for ۳۰ days
- Re-verify if `national_id` changes
- On success: `shahkar_verified_at` + `shahkar_response` stored in `kyc_records`

### ۴.۵. Limit Enforcement Points

KYC limits are checked at:
- Checkout (purchase + digital_trade buy)
- Wallet trade (digital_trade sell)
- Physical purchase from wallet
- Rial withdrawal request
- POS sale (if customer identified)

> Canonical schemas: [Identity (KYC)](../03-schema-index.md#7-kyc)

---

## ۵. Dealer Role Model

### ۵.۱. Dealer Tiers

`dealer_tiers`: سطح‌بندی نمایندگان. هر سطح:
- نرخ اجرت متفاوت (via `channel_pricing_formulas.dealer_tier_id`)
- نرخ کمیسیون متفاوت (via `dealer_commission_rates.dealer_tier_id`)
- Credit limit default (via `dealer_tiers.default_credit_limit_mg` — اگر custom نباشد)

### ۵.۲. Dealer Fields (on user)

- `tier_id` (FK → dealer_tiers)
- `api_key_hash` — for POS device auth
- `inventory_location_id` — physical location of dealer
- `commission_percent` — quick override

### ۵.۳. Sub-Dealer ([D-73](../01-decisions-audit-log.md))

Sub-dealer/شبکه نمایندگی **حذف شد** در v1. فقط flat dealer list with tiers.

---

## ۶. Security Measures

### ۶.۱. Idempotency

- Header `Idempotency-Key` (UUID) الزامی در همه POST تغییردهنده
- ذخیره: در ستون `idempotency_key` entity (نه جدول جدا)
- Per-scope where applicable: `(wallet_scope, user_id, idempotency_key)`

### ۶.۲. Rate Limiting

| Endpoint | Limit | Note |
|----------|-------|------|
| `/auth/send-otp` | 3/min | سختگیر — prevent OTP spam |
| `/payments/start` | 10/min per user | |
| `/wallet/trades/*` | 10/min per user | |
| `/withdrawals/*` | 10/min per user | |

- Implementation: `slowapi` (in-memory) for v1, Redis-backed later

### ۶.۳. Payment Callback Security

- Signature verification where provider supports (Sepehr/Parsian)
- Replay prevention: idempotency_key stored in DB
- Gateway-specific validation in callback handler

### ۶.۴. Frontend Security

- CORS: only configured domains per channel
- CSP headers
- SameSite cookies for web frontend
- No `brand_id` in body — always from channel resolution

---

## ۷. Audit — Mandatory Actions

هر action با priority بالا → `audit_logs.insert` در **همان transaction**:

- تغییر قیمت / manual override
- Inventory adjustment
- Wallet adjustment manual
- تغییر KYC level/limits
- تأیید/رد withdrawal ریال
- Mark treasury covered
- **Inter-company settle (rial/gold)**
- Buyback (digital و physical)
- تغییر role/permission
- Sync دستی marketplace / تغییر mapping
- تغییر payment_account
- Inventory_movement بین انبارها

**audit_logs: INSERT ONLY** — DB grant: `REVOKE UPDATE, DELETE ON audit_logs FROM app_user`

> Canonical schemas: [Outbox + Audit](../03-schema-index.md#13-outbox--audit)

---

## ۸. Related Flows

- [Flow 01 — Physical Bar Purchase](../flows/01-physical-bar-purchase-site.md) (KYC check at checkout)
- [Flow 09 — Rial Wallet Topup](../flows/09-rial-wallet-topup.md) (payment auth)
- [Flow 10 — Rial Withdrawal](../flows/10-rial-withdrawal.md) (D-64 bank account check)

## ۹. Key Decisions

| Decision | Summary |
|----------|---------|
| [D-23](../01-decisions-audit-log.md) | Fresh start — no v4 data migration |
| [D-31](../01-decisions-audit-log.md) | Gold withdrawal removed |
| [D-61](../01-decisions-audit-log.md) | KYC user levels |
| [D-64](../01-decisions-audit-log.md) | Third-party withdrawal forbidden, national_id match |
| [D-73](../01-decisions-audit-log.md) | Sub-dealer removed in v1 |
