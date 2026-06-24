# Reference — Inventory: Bars, Warehouse & Physical Operations

> Cross-cutting reference for bar lifecycle, inventory locations,
> transfer model, fulfillment, bulk gold, and production cycle.

> **DRY rule:** No SQL here. Canonical schemas → [Schema Index](../03-schema-index.md).
> Decision rationale → [Decisions](../01-decisions-audit-log.md).

---

## ۱. Bar Lifecycle & Status Enum

### ۱.۱. Status State Machine

```
preorder ─→ RAW ─→ ASSIGNED ─→ RESERVED ─→ SOLD
                                    │          │
                                    └── cancel ─┘── delivered_at=NULL (custodial)
                                                └── delivered_at=set  (physical delivery)
                                                         │
                                                         ├── buyback (a/b) → ASSIGNED (resaleable)
                                                         └── exception:
                                                              DAMAGED | LOST | IN_INSPECTION
```

### ۱.۲. Status Definitions

| Status | Description | Sellable? |
|--------|-------------|-----------|
| `preorder` | سریال تولید شده، فیزیکی در کارخانه | ❌ |
| `RAW` | تولید شده / در انبار (قابل فروش) | ✅ |
| `ASSIGNED` | برای channel تخصیص‌یافته (قابل reserve) | ✅ (in pool) |
| `RESERVED` | موقتا رزرو (POS/checkout، TTL-based) | ❌ |
| `SOLD` | فروخته شده (مالک دارد) | ❌ |
| `DAMAGED` | آسیب‌دیده / پلمب‌شکسته → بررسی ([D-79](../01-decisions-audit-log.md)) | ❌ |
| `LOST` | گم/دزدیده → رویداد زیان ([D-79](../01-decisions-audit-log.md)) | ❌ |
| `IN_INSPECTION` | در حال بررسی (damaged return, buyback) | ❌ |

### ۱.۳. Key Fields on `bars`

- `serial_code` (unique) — حک شده روی شمش، مبنای QR و scan
- `owner_company_id` — مالک حقوقی فعلی (قبل از فروش = شرکت)
- `current_location_id` — موقعیت فیزیکی فعلی
- `assigned_channel_id` — اگر NULL = pool عمومی؛ اگر مقدار = فقط در آن channel
- `customer_id` — مالک مشتری (بعد از فروش)
- `sale_wallet_scope` — در لحظه فروش ست، سپس IMMUTABLE ([D-71](../01-decisions-audit-log.md)). مبنای بازخرید.
- `is_preorder` — TRUE = سریال generated ولی فیزیکی تولید نشده
- `claim_code` — برای POS/gift bar claim
- `reserved_until` — TTL برای reservation release
- `delivered_at` — NULL = custodial/امانی، set = تحویل شده ([D-78](../01-decisions-audit-log.md))
- `version` — optimistic locking

### ۱.۴. Custodial Gold (طلای امانی)

- شمشی که `status == SOLD` و `delivered_at IS NULL`
- شمش در خزانه قفل — مشتری مالک ثبتی است ولی تحویل فیزیکی نگرفته
- فروش امانی هیچ fulfillment task نمی‌سازد ([D-77](../01-decisions-audit-log.md))
- فقط با درخواست تحویل مشتری: task ساخته می‌شود با bar_id مشخص

---

## ۲. Inventory Locations

### ۲.۱. Location Types

| Type | Description | is_sellable |
|------|-------------|-------------|
| `warehouse` | انبار فیزیکی (مرکزی) | TRUE |
| `factory` | کارخانه تولید | TRUE |
| `safe_box` | صندوق امانات | TRUE |
| `store` | فروشگاه / شعبه | TRUE |
| `dealer` | مکان نماینده | TRUE |
| `branch` | شعبه سازمانی | TRUE |
| `in_transit` | انبار مجازی موجودی در راه ([D-62](../01-decisions-audit-log.md)) | **FALSE** |
| `external_marketplace` | انبار مجازی marketplace | depends |

### ۲.۲. Dual Ownership Model (§7.6)

هر location دو ستون:
- `owner_company_id` — مالک حقوقی (مثلا شرکت طلاملا)
- `manager_company_id` — مدیر فیزیکی (مثلا شرکت گلدیس)

این دو می‌توانند متفاوت باشند. مثال: انبار TalaMala مالک TalaMala ولی مدیریت فیزیکی Goldis (§7.6 — لجستیک Goldis، پول TalaMala).

### ۲.۳. Buyback Locations

`can_buyback = TRUE` برای:
- warehouse مرکزی Goldis
- dealer هایی با `is_buyback_center` flag

---

## ۳. Reservation Model

### ۳.۱. جدول `inventory_reservations`

- Per-bar, per-user, per-channel reservation
- TTL-based: `expires_at` → auto-release by `lock_expirer` worker
- Connected to order or cart via `order_id` / `cart_id`
- Idempotency via `idempotency_key`

### ۳.۲. Reservation Flow

```
Checkout/POS → bar.status=RESERVED, reserved_until=+N min
   ↓ payment success → Inventory.consume → bar.status=SOLD
   ↓ payment fail/timeout → release → bar.status=ASSIGNED/RAW
```

---

## ۴. Inventory Transfer — Two-Stage ([D-62](../01-decisions-audit-log.md))

### ۴.۱. State Machine

```
DRAFT → DISPATCHED → RECEIVED → COMPLETED
                              → DISCREPANCY
         ↓
      CANCELLED (only from DRAFT/DISPATCHED)
```

### ۴.۲. Key Rules

- **Sender ≠ Receiver** (separation of duties)
- **OTP mandatory** between source/destination
- **In-transit bars non-sellable** (virtual location with `is_sellable=FALSE`)
- **Serial scan mandatory** at dispatch and receipt
- Discrepancy: missing/unexpected bars → admin investigation
- Cancel from DISPATCHED: bars moved back to source

### ۴.۳. Fulfillment vs Transfer ([D-80](../01-decisions-audit-log.md))

این دو **سیستم جدا** هستند:
- **Fulfillment** = تحویل مرتبط با سفارش مشتری (همیشه `order_id` دارد) → [Flow 14](../flows/14-fulfillment-delivery.md)
- **Transfer** = انتقال داخلی بین انبارها (بدون مشتری) → [Flow 13](../flows/13-inventory-transfer.md)

اگر شمش در انبار اشتباه است: **اول transfer (D-62)، بعد fulfillment.**

---

## ۵. Fulfillment — تحویل کالا

### ۵.۱. Trigger Rule ([D-77](../01-decisions-audit-log.md))

- Trigger = **درخواست تحویل**، نه پرداخت سفارش
- فروش امانی (delivered_at=NULL) هیچ task نمیسازد
- فقط با درخواست تحویل مشتری (یا تحویل فوری POS/فروشگاه) task ساخته می‌شود

### ۵.۲. Handover vs Delivery ([D-78](../01-decisions-audit-log.md))

- `handed_over` = انباردار «به پیک دادم» (از دست ما خارج شد)
- `delivered` = **فقط با OTP گیرنده** + اسکن سریال
- انباردار مبدأ **هرگز** delivered نمی‌زند — نقش مقصد (پیک/فروشگاه/نماینده)
- `bar.delivered_at` فقط در confirm-delivery ست می‌شود

### ۵.۳. Exception Paths ([D-79](../01-decisions-audit-log.md))

| Exception | Status | Handling |
|-----------|--------|----------|
| پیک نتوانست تحویل دهد | `delivery_failed` | برگشت via D-62 process |
| گم/دزدیده | `lost_in_transit` | رویداد زیان + treasury compensate |
| پلمب‌شکسته | `damaged` | بازرسی → قابل فروش نیست |

**هیچکدام خودکار بسته نمیشوند** — تصمیم اپراتور/حسابدار + audit + reason الزامی.

---

## ۶. Bulk Gold Inventory ([D-83](../01-decisions-audit-log.md))

### ۶.۱. مفهوم

طلای خام/ذوب‌شده که سریالدار نیست (granules، large bars from smelting). ذخیره by weight (mg)، not serial.

### ۶.۲. Sources

| Source | Description |
|--------|-------------|
| `hedge_buy` | Goldis از بازار خرید (Central Hedging) |
| `supplier_purchase` | خرید از کارخانه |
| `scrap_remelting` | بازیافت ضایعات |
| `physical_buyback_return` | شمش برگشتی buyback |

### ۶.۳. Movement Ledger

`bulk_gold_movements`: append-only ledger for in/out:
- `intake` (positive delta) — ورود طلای خام
- `withdrawal` (negative delta) — خروج برای settlement یا تولید
- `conversion` — تبدیل خام به شمش (چرخه تولید)
- `recount` — تصحیح وزن بعد از شمارش

### ۶.۴. Settlement Link

وقتی `POST /admin/inter-company/settle-gold` با `source_bulk_gold_id`:
- Withdraw از bulk_gold_inventory (weight_mg_delta=−amount)
- INSERT inventory_movement (from=goldis_warehouse, to=creditor_warehouse)
- INSERT inter_company_ledger (ردیف settlement جهت‌مخالف: debtor=TalaMala، creditor=Goldis، asset=XAU_MG، source_type='settlement' — net تعهد طلا را به سمت صفر می‌برد؛ append-only، بدون FIFO/status و بدون mutate ردیف‌های قبلی — D-102)

---

## ۷. Inventory Movements

### ۷.۱. Movement Types

`inventory_movements` — per-bar audit trail:

| movement_type | Description |
|---------------|-------------|
| `intake` | ورود شمش از کارخانه/supplier |
| `sale` | فروش به مشتری |
| `transfer_out` | خروج برای انتقال بین انبار |
| `transfer_in` | ورود از انتقال بین انبار |
| `buyback_return` | برگشت شمش از بازخرید |
| `delivery` | تحویل به مشتری |
| `return` | برگشت ناموفق |
| `loss` | رویداد زیان |

### ۷.۲. Reference Tracking

هر movement ارجاع به منبع دارد:
- `reference_type`: order | transfer_document | buyback_request | manual_adjustment
- `reference_id`: UUID of source entity
- `actor_id`: who performed the action

---

## ۸. POS Inventory

### ۸.۱. POS Devices

هر POS device → `sales_channel` → `dealer` → `inventory_location`. لیست شمشهای موجود:
```
bars WHERE current_location_id = dealer.location AND status IN ('ASSIGNED', 'RAW')
```

### ۸.۲. Reserve → Confirm Pattern ([D-99](../01-decisions-audit-log.md))

```
GET /pos/inventory → لیست بارهای موجود + price preview
POST /pos/reserve { bar_id, customer_mobile } → bar lock (RESERVED, TTL)
POST /pos/confirm { reservation_id, trace, rrn, amount, paid_at } → SOLD + order
POST /pos/cancel { reservation_id } → release
```

Offline queue: `pos_pending_requests` with idempotency key `(dealer_id, pos_session_id, request_id)`.

---

## ۹. Related Flows

- [Flow 01 — Physical Bar Purchase (Site)](../flows/01-physical-bar-purchase-site.md)
- [Flow 04 — Physical Purchase from Wallet](../flows/04-physical-purchase-from-wallet.md)
- [Flow 05 — Buyback Undelivered](../flows/05-buyback-undelivered.md)
- [Flow 06 — Buyback In-Person](../flows/06-buyback-in-person.md)
- [Flow 07 — POS Sale](../flows/07-pos-sale.md)
- [Flow 08 — Marketplace Sale](../flows/08-marketplace-sale.md)
- [Flow 11 — Hedge Buy & Bulk Gold Intake](../flows/11-hedge-buy-and-bulk-gold-intake.md)
- [Flow 13 — Inventory Transfer](../flows/13-inventory-transfer.md)
- [Flow 14 — Fulfillment Delivery](../flows/14-fulfillment-delivery.md)

## ۱۰. Key Decisions

| Decision | Summary |
|----------|---------|
| [D-13](../01-decisions-audit-log.md) | Bar serial QR for authenticity |
| [D-49](../01-decisions-audit-log.md) | Specific bar allocation at sale |
| [D-51](../01-decisions-audit-log.md) | Purity as parts-per-1000 |
| [D-60](../01-decisions-audit-log.md) | physical_purchase_from_wallet bar source |
| [D-62](../01-decisions-audit-log.md) | Two-stage inventory transfer with OTP |
| [D-71](../01-decisions-audit-log.md) | sale_wallet_scope immutable |
| [D-77](../01-decisions-audit-log.md) | Fulfillment trigger = delivery request, not payment |
| [D-78](../01-decisions-audit-log.md) | Delivery confirmed only via recipient OTP |
| [D-79](../01-decisions-audit-log.md) | Exception paths: delivery_failed / lost / damaged |
| [D-80](../01-decisions-audit-log.md) | Fulfillment ≠ inventory transfer (separate systems) |
| [D-83](../01-decisions-audit-log.md) | Bulk gold = by weight, not serial |
| [D-89](../01-decisions-audit-log.md) | In-transit virtual location non-sellable |
| [D-92](../01-decisions-audit-log.md) | Bar resaleable after buyback in any scope |
| [D-93](../01-decisions-audit-log.md) | Transfer document idempotency |
| [D-99](../01-decisions-audit-log.md) | POS offline queue |
