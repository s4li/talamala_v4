# Reference — Commercial: Pricing, Orders & Buyback

> Cross-cutting reference for pricing resolution, order types/lifecycle,
> buyback model, marketplace integration, and dealer commission model.

> **DRY rule:** No SQL here. Canonical schemas → [Schema Index](../03-schema-index.md).
> Decision rationale → [Decisions](../01-decisions-audit-log.md).

---

## ۱. Pricing Architecture

### ۱.۱. Price Pipeline

```
External Sources (TGJU, Goldis.ir, manual)
    ↓
price_sources → source_prices (raw market data)
    ↓
pricing_configs → pricing_config_sources (weighted aggregation per metal)
    ↓
internal_base_prices (Goldis wholesale = P0)
    ↓
channel_pricing_formulas (per brand/channel/product/tier/trade_side)
    ↓
Final customer price = P0 × coefficient + margin + fixed_fee + wage + tax
    ↓
price_locks (snapshot valid for lock_ttl_seconds)
```

### ۱.۲. Price Ladder ([D-65](../01-decisions-audit-log.md))

| Level | Description |
|-------|-------------|
| P0 | Internal base price (Goldis wholesale — از source aggregation) |
| P_hedge | P0 + حداقل مارجین Goldis (مبنای inter_company_ledger) |
| P_partner | P_hedge + مارجین سطح همکار (dealer tier) |
| P_retail | P_partner + مارجین فروشگاه (مشتری نهایی) |

- رزولوشن: specific formula overrides general (product > product_type > brand > default)
- `priority` field determines resolution order
- `dealer_tier_id`: NULL = مشتری نهایی; value = سطح همکار

### ۱.۳. Buy/Sell Spread ([D-72](../01-decisions-audit-log.md))

`trade_side` field in `channel_pricing_formulas`:
- `buy` — قیمت خرید طلای دیجیتال (کاربر می‌خرد)
- `sell` — قیمت فروش/بازخرید طلای دیجیتال (کاربر می‌فروشد)
- `NULL` — هر دو سمت

مارجین مستقل برای هر سمت: «کارمزد معامله» v4 همین مارجین spread است (مفهوم جدا نداریم).

### ۱.۴. Price Lock ([D-50](../01-decisions-audit-log.md), [D-28](../01-decisions-audit-log.md))

- TTL: ۲ دقیقه default، بازه مجاز ۶۰s..۳۰۰s (کف ۱ دقیقه برای شرایط پرنوسان)
- Snapshot شامل: base price, formula params, final price, source prices
- `idempotency_key` unique
- Status: active → used | expired | cancelled

### ۱.۵. Rounding Policy ([D-27](../01-decisions-audit-log.md))

- Default: `floor` (به نفع مشتری)
- Per-formula override: `round_half_up`, `ceiling`, `bankers`

### ۱.۶. Buyback Percent ([D-32](../01-decisions-audit-log.md))

هر formula یک `buyback_percent` دارد. موقع خرید اصلی:
```
buyback_credit_rial = final_price_rial × buyback_percent / 100
```
این مقدار snapshot در `order_items.buyback_credit_rial` → در بازخرید به wallet IRR کاربر برمیگردد.

### ۱.۷. Hedge Price for Inter-Company

`raw_hedge_price_rial` در `order_items`:
```
raw_hedge_price_rial = P_hedge_per_mg(لحظه فروش) × pure_gold_mg
```
- تنها مبنای inter_company_ledger (snapshot قیمت عمدهی Goldis در لحظه فروش)
- [D-65](../01-decisions-audit-log.md): P_hedge ≠ internal_base_price خالص

> Canonical schemas: [Pricing](../03-schema-index.md#9-pricing)

---

## ۲. Order Types & Lifecycle

### ۲.۱. هفت نوع سفارش

| order_type | Description | Payment | Treasury | Inter-Company |
|-----------|-------------|---------|----------|---------------|
| `purchase` | خرید شمش فیزیکی از سایت | Gateway (rial) | + pure_gold_mg | ✅ if non-Goldis |
| `digital_trade` (buy) | خرید طلای دیجیتال | Gateway (rial) | + amount_mg | ✅ if non-Goldis |
| `digital_trade` (sell) | فروش طلای دیجیتال / بازخرید دیجیتال ([D-68](../01-decisions-audit-log.md)) | Wallet credit (rial) | − amount_mg | ✅ if non-Goldis (reversed pair) |
| `pos_sale` | فروش از POS نماینده | POS card (rial) | + pure_gold_mg | ✅ if non-Goldis |
| `marketplace_sale` | فروش از DigiKala/Basalam | Marketplace | + pure_gold_mg | ❌ always Goldis-side ([D-56](../01-decisions-audit-log.md)) |
| `physical_purchase_from_wallet` | خرید شمش با wallet طلایی | Split (gold+rial+gateway) | net ≈ −wage_gold_mg | ✅ if non-Goldis |
| `buyback` | بازخرید تحویل‌نشده (اتومات) | Wallet credit | net ≈ ۰ | ❌ (خنثی — [D-58](../01-decisions-audit-log.md)) |
| `withdrawal_rial` | برداشت ریال از کیف | Bank transfer | ❌ | ❌ |

### ۲.۲. Multi-Company Dimensions (per order)

هر order شامل:
- `brand_id` — برند فروش (Goldis / TalaMala / AminZar)
- `sales_channel_id` — کانال فروش
- `seller_company_id` — فروشنده حقوقی (موجودی)
- `operator_company_id` — مدیر عملیات (همیشه Goldis در v1)
- `payment_account_id` → `payment_receiver_company_id` — گیرنده پول
- `fulfillment_location_id` — مبدأ تحویل

### ۲.۳. Channel Resolution

```
Frontend domain → channel lookup → brand + payment_account + seller + operator
```
- Web: domain-based + `X-Channel-Code` fallback
- POS: `terminal_id` + `device_id` in JWT → resolve to channel
- Admin: explicit selection
- **هیچ frontend نمی‌تواند brand_id را آزاد در body بفرستد**

### ۲.۴. Key Snapshots in order_items

- `pure_gold_mg` = weight × purity / 1000 (buyback basis — always XAU_MG)
- `buyback_credit_rial` = snapshot at purchase (D-32)
- `raw_hedge_price_rial` = snapshot P_hedge × pure_gold_mg (inter-company basis — D-65)
- `price_snapshot` = full pricing calculation (JSON)

> Canonical schemas: [Order](../03-schema-index.md#11-order)

---

## ۳. Buyback Model ([D-32](../01-decisions-audit-log.md), [D-58](../01-decisions-audit-log.md))

### ۳.۱. اصول بنیادی

- **Refund نداریم.** «لغو» وجود ندارد.
- **فروش اصلی همیشه معتبر میماند و هرگز reverse نمی‌شود.**
- بازخرید همیشه یک تراکنش **مستقل روبهجلو** است.

### ۳.۲. سه حالت بازخرید

| حالت | شرایط | تأیید | مسیر |
|------|--------|------|------|
| (a) بازخرید تحویل‌نشده | bar.delivered_at IS NULL | اتومات (آنلاین) | [Flow 05](../flows/05-buyback-undelivered.md) |
| (b) بازخرید حضوری | bar.delivered_at IS NOT NULL | State machine (کارشناس) | [Flow 06](../flows/06-buyback-in-person.md) |
| (c) بازخرید دیجیتال | طلای دیجیتال کیف | = `digital_trade sell` ([D-68](../01-decisions-audit-log.md)) | [Flow 03](../flows/03-digital-gold-sell.md) |

### ۳.۳. قواعد مشترک (a) و (b)

- وزن خالص (`weight × purity / 1000`) → wallet **XAU_MG** (همیشه)
- `buyback_credit_rial` (snapshot موقع خرید) → wallet **IRR** — **فقط اگر** ثبت مالکیت + OTP
- اجرت + مالیات + سود **می‌سوزد**
- هر دو واریز به **scope برند فروش همان شمش** (`bars.sale_wallet_scope` — [D-71](../01-decisions-audit-log.md))
- خزانه: تبدیل physical↔digital ⇒ **خنثی** (دو پای متقابل)
- **هیچ تعهد بین‌شرکتی تازهای** ساخته نمی‌شود

### ۳.۴. بازخرید آنلاین: Scope Restriction

بازخرید آنلاین (حالت a) فقط در همان scope/وبسایتی که خرید انجام شده مجاز است ([D-71](../01-decisions-audit-log.md)).

---

## ۴. Marketplace Integration ([D-56](../01-decisions-audit-log.md))

### ۴.۱. Pull Adapter Pattern

```
Worker هر ۶۰ ثانیه:
  for each channel where type=marketplace:
    adapter = build_adapter(channel)
    new = adapter.fetch_new_orders(since=last_sync_at)
    for ext in new:
      dedup_key → INSERT external_orders (UniqueViolation → skip)
      → Order.create(order_type=marketplace_sale, status=Paid)
```

### ۴.۲. Goldis-Only Rule

- **D-56 (قطعی):** marketplace همیشه seller=Goldis و payment_receiver=Goldis
- هیچ inter-company entry در marketplace نیست
- حتی اگر brand=TalaMala — Goldis انحصارا marketplace را اداره میکند
- TalaMala هیچ marketplace income مستقیم ندارد

> Canonical schemas: [Platform (marketplace channels)](../03-schema-index.md#1-platform), [Catalog (external mappings)](../03-schema-index.md#8-catalog)

---

## ۵. Dealer Commission Model ([D-73](../01-decisions-audit-log.md))

### ۵.۱. Gold-for-Gold

کمیسیون نماینده در طلا محاسبه و تسویه می‌شود (نه ریال):
```
commission_mg = pure_gold_mg × commission_percent / 100
```

### ۵.۲. Commission Rates — Priority Resolution

مشابه D-65 pricing: specific formula overrides general (product > product_type > tier > default). `trade_side`: sale | buyback.

### ۵.۳. Commission Ledger — جدا از inter_company_ledger

`dealer_commission_ledger` جدا از `inter_company_ledger` (آن شرکت↔شرکت؛ نماینده کاربر است). بدهی طلایی TalaMala→نماینده.

### ۵.۴. Guard Rail

- فروش: Σ کمیسیون ≤ (P_retail − P_hedge) — نقض → رد/هشدار
- بازخرید: کمیسیون ≤ اسپرد بازخرید — نقض → رد/هشدار

### ۵.۵. Treasury Offset ([D-84](../01-decisions-audit-log.md))

واریز کمیسیون به کیف نماینده (XAU_MG +) → یک پای خزانهای `+pure_gold_mg` میسازد → تابع سقفهای D-47. اپراتور ماهانه offset settlement انجام می‌دهد.

> Canonical schemas: [Supplementary (dealer)](../03-schema-index.md#14-supplementary)

---

## ۶. Production Cycle — تأمین شمش (§7)

### ۶.۱. سه جریان تأمین

| جریان | مبدأ | مقصد | نوع |
|--------|------|------|-----|
| ۱. AminZar → Goldis | کارخانه امین زر | انبار Goldis | supplier purchase (فقط طلا) |
| ۲. TalaMala برای خودش | کارخانه طلاملا | انبار TalaMala | داخلی (بدون obligation) |
| ۳. TalaMala → Goldis | کارخانه طلاملا | انبار Goldis | supplier purchase (شمش، نه خام) |

### ۶.۲. Preorder Model

سیستم سریالها را از قبل تولید میکند → کارخانه حک میکند → بعد از تحویل به Goldis:
- `is_preorder`: TRUE → FALSE
- `status`: preorder → in_stock
- `current_location_id`: factory → warehouse
- INSERT inter_company_ledger (asset='gold', source_type='supplier_purchase', wage included)

### ۶.۳. Supplier Purchase — Gold-Only

Goldis به کارخانه می‌دهد: **اصل طلا + معادل اجرت (طلایی)**. تعهد طلایی Goldis↔کارخانه روی همان `inter_company_ledger` رصد می‌شود. **طلای اجرت = هزینه حسابداری، بدون اثر بر exposure** ([D-48](../01-decisions-audit-log.md)).

---

## ۷. Related Flows

- [Flow 01 — Physical Bar Purchase (Site)](../flows/01-physical-bar-purchase-site.md)
- [Flow 02 — Digital Gold Buy](../flows/02-digital-gold-buy.md)
- [Flow 03 — Digital Gold Sell](../flows/03-digital-gold-sell.md)
- [Flow 04 — Physical Purchase from Wallet](../flows/04-physical-purchase-from-wallet.md)
- [Flow 05 — Buyback Undelivered](../flows/05-buyback-undelivered.md)
- [Flow 06 — Buyback In-Person](../flows/06-buyback-in-person.md)
- [Flow 07 — POS Sale](../flows/07-pos-sale.md)
- [Flow 08 — Marketplace Sale](../flows/08-marketplace-sale.md)
- [Flow 12 — Inter-Company Settlement](../flows/12-inter-company-settlement.md)
- [Flow 15 — Dealer Commission Settlement](../flows/15-dealer-commission-settlement.md)

## ۸. Key Decisions

| Decision | Summary |
|----------|---------|
| [D-27](../01-decisions-audit-log.md) | Rounding policy: floor default |
| [D-28](../01-decisions-audit-log.md) | Price lock TTL |
| [D-32](../01-decisions-audit-log.md) | No refund — buyback forward transaction with snapshot |
| [D-48](../01-decisions-audit-log.md) | Supplier purchase tracked in inter_company_ledger |
| [D-50](../01-decisions-audit-log.md) | Lock TTL 60-300s range |
| [D-51](../01-decisions-audit-log.md) | Purity as parts-per-1000 |
| [D-56](../01-decisions-audit-log.md) | Marketplace always Goldis-side |
| [D-58](../01-decisions-audit-log.md) | Buyback never reverses original sale |
| [D-65](../01-decisions-audit-log.md) | Price ladder: P0 → P_hedge → P_partner → P_retail |
| [D-68](../01-decisions-audit-log.md) | Digital buyback = digital_trade sell (no separate path) |
| [D-71](../01-decisions-audit-log.md) | sale_wallet_scope immutable after sale |
| [D-72](../01-decisions-audit-log.md) | Buy/sell spread with independent margins |
| [D-73](../01-decisions-audit-log.md) | Dealer commission Gold-for-Gold, separate ledger |
| [D-84](../01-decisions-audit-log.md) | Commission treasury offset |
