# Reference — Finance: Wallet, Treasury & Inter-Company Ledger

> Cross-cutting reference for the three financial pillars of Goldis Hub:
> Wallet (per-user, per-scope), Treasury (Goldis-only exposure), and
> Inter-Company Ledger (real-time obligations between companies).

> **DRY rule:** No SQL here. Canonical schemas → [Schema Index](../03-schema-index.md).
> Decision rationale → [Decisions](../01-decisions-audit-log.md).

---

## ۱. Wallet Model — Per-wallet-scope Isolation

### ۱.۱. ساختار سه‌کیفه

هر کاربر **سه کیف کاملا ایزوله** دارد، با کلید `wallet_scope`:

```
User Ali (mobile=0912...)
├── KYC: یکی، مشترک
├── Wallet scope = goldis      (legal: شرکت گلدیس)   ← فقط برند گلدیس
│   ├── IRR / XAU_MG / XAG_MG (XAG آینده — D-74)
├── Wallet scope = aminzar     (legal: شرکت گلدیس)   ← فقط برند امین زر، کاملا جدا از goldis
│   ├── IRR / XAU_MG / XAG_MG
└── Wallet scope = talamala    (legal: شرکت طلاملا) ← فقط برند طلاملا
    ├── IRR / XAU_MG / XAG_MG
```

### ۱.۲. قواعد Scope Isolation ([D-46](../01-decisions-audit-log.md))

- کلید کیف = **`wallet_scope`** (goldis|aminzar|talamala)، نه legal_entity. `company_id` فقط مشتق و برای حسابداری/inter-company نگه داشته می‌شود.
- هر scope **فقط در همان scope/برند قابل خرج** است (TalaMala→talamala، Goldis→goldis، AminZar→**aminzar**).
- **هر سه کاملا ایزوله — هیچ transfer مستقیم بین هیچ‌کدام** (حتی goldis↔aminzar که حقوقا یک شرکتاند). برای جابهجایی: فروش به ریال → برداشت → شارژ مجدد.
- **AminZar در Goldis merge نمی‌شود** هرچند legal entity هر دو شرکت گلدیس و درگاه AminZar همان Goldis IPG است.
- **UX ([D-40](../01-decisions-audit-log.md)):** Frontend هر برند فقط scope خودش را «موجودی شما» نشان می‌دهد (نام scope/شرکت پنهان). در admin panel هر سه scope در تبهای جدا، با **تفکیک گزارشی بدهی aminzar از goldis** (الزام D-46).

### ۱.۳. Asset Types

| Code | Name | Minor Unit | Notes |
|------|------|-----------|-------|
| IRR | ریال | rial | واحد پایه پول ایران |
| XAU_MG | طلا (میلی‌گرم) | milligram | Gold digital balance |
| XAG_MG | نقره (میلی‌گرم) | milligram | آینده — [D-74](../01-decisions-audit-log.md) |

### ۱.۴. Wallet Operations

- **Balance check:** `available_balance = max(0, current_balance + credit_limit - locked)`
- **Withdrawable balance:** `balance - locked - credit` (credit limit NOT included for bank withdrawals)
- **Lock → Consume/Release:** Pessimistic locking for payments. Lock expires → auto-release.
- **Credit limit:** Only for dealer XAU_MG accounts. DB CHECK: `current_balance >= -credit_limit`.
- **Idempotency:** Per `(wallet_scope, user_id, idempotency_key)` — scope-keyed.

### ۱.۵. تعامل با Treasury و Inter-Company Ledger

وقتی کاربر طلای دیجیتال می‌خرد در برند طلاملا:
- پول → حساب TalaMala (payment_account TalaMala IPG)
- Wallet TalaMala (XAU_MG) کاربر `+amount_mg`
- **Goldis Treasury** position `+amount_mg` (open exposure برای Goldis)
- **Inter-company hedging entries (دو ردیف):**
  - `inter_company_ledger`: TalaMala → Goldis، rial، به اندازه‌ی `raw_gold_price × amount_mg`
  - `inter_company_ledger`: Goldis → TalaMala، gold، `amount_mg`
- مدل ledger real-time است (بخش ۶)؛ تسویه دستی توسط اپراتور Goldis

> Canonical schemas: [Wallet](../03-schema-index.md#2-wallet)

---

## ۲. Treasury مرکزی Goldis (Central Hedging Desk)

### ۲.۱. مفهوم

- **یک Treasury** برای کل پلتفرم — managed by شرکت گلدیس
- نقش Treasury: ثبت **open exposure** Goldis در بازار طلا
- هر فروش طلا (در هر brand، هر channel) → exposure Goldis بالا (چون Goldis بدهی طلا به فروشنده یا مشتری پیدا میکند)
- Goldis از بازار خام می‌خرد (`hedge_buy`) → exposure پایین
- Digital gold inventory ≠ جدول جدا. این **همان Treasury** است.

### ۲.۲. Sign Convention (explicit)

`treasury_positions.delta_amount_mg` بر اساس نگاه **Goldis**:

**تراکنش‌های تک‌پایی (علامت ثابت):**
- **+** (exposure باز — Goldis بدهکار طلا شد): `order_physical`، `pos_sale`، `marketplace_sale`، `digital_buy` (در هر brand، شامل فروشهای خود Goldis)
- **−** (exposure بسته): `hedge_buy`، `digital_sell` (بازخرید دیجیتال = همین)

**تراکنش‌های دوپایی (net ≈ صفر):**
- `buyback` تحویل‌نشده/حضوری: پای `+pure_gold_mg` (طلا به کیف) و پای `−pure_gold_mg` (شمش برگشتی/مصرف) ⇒ خنثی
- `physical_purchase_from_wallet`: پای `−gold_part_mg` (مصرف طلای دیجیتال کیف) و پای `+pure_gold_mg` (خروج شمش فیزیکی) ⇒ خنثی

> **D-100 (signed-sum):** `exposure(metal) = sum(delta_amount_mg WHERE status='open')`. مدل coverage حذف شد؛ `hedge_buy` یک ردیف با delta منفی است (D-90). status فقط `open`/`cancelled`.

### ۲.۳. Cap و Alert (دو‌طرفه + چک inline) — [D-47](../01-decisions-audit-log.md)

- **سقف دو‌طرفه به ازای هر فلز:** `max_open_exposure_mg` (سمت فروش، exposure مثبت) + `max_short_exposure_mg` (سمت خرید/بازخرید، exposure منفی). هر دو اپراتور-تنظیم، با audit.
- **چک inline سد سخت در لحظه‌ی هر تراکنش** (فروش+خرید، فیزیکی+دیجیتال+POS، بدون استثنا): اگر این تراکنش از سقف مربوطه رد شود، **همان تراکنش رد می‌شود** (مثل `require_fresh_price`).
- `warning_threshold_percent` (مثلا ۷۰٪) برای هر دو طرف.
- `auto_block_at_cap`: worker (۱۲.۱۰) فقط **هشدار/پشتیبان** است؛ سد واقعی همان چک inline است.
- **D-101 فرمول/قفل:** `committed + reserved + this_tx` در بازه‌ی `[−max_short_exposure_mg, +max_open_exposure_mg]`؛ `committed = SUM(open positions)`، `reserved = SUM(inventory_pending_holds زنده — D-105)`. ناحیه‌ی بحرانی با `pg_advisory_xact_lock(hashtext('treasury:'||metal_type))` سریالایز می‌شود (نه `SELECT FOR UPDATE` روی `treasury_settings`).

### ۲.۴. Treasury Alert Worker

```
worker هر ۳۰ ثانیه:
  for each metal:
    net = SUM(delta_amount_mg) where status = 'open'   # D-100
    if net >= max_open_exposure_mg → sell-block + critical alert
    elif net > 0 and net / max >= warning_threshold → throttled warning
    if -net >= max_short_exposure_mg → buy-block + critical alert
    elif net < 0 and -net / max_short >= warning_threshold → throttled warning
```

> Canonical schemas: [Treasury](../03-schema-index.md#3-treasury)

---

## ۳. Inter-Company Ledger — مدل Hedging مرکزی

### ۳.۱. مفهوم — Goldis بهعنوان Central Hedging Desk ([D-06](../01-decisions-audit-log.md))

اصل اساسی بازار طلا: **هر کسی طلا بفروشد، باید بلافاصله معادل وزن خام آن طلا را از بازار بخرد** — وگرنه با بالا رفتن قیمت ضرر میکند (open exposure).

در پلتفرم ما، **Goldis نقش Central Hedging Desk** را برای همه‌ی برندها بازی میکند. هر فروشگاهی (TalaMala، AminZar، یا حتی خود Goldis) که شمش می‌فروشد، **به‌صورت اتوماتیک از Goldis طلای خام معادل آن را می‌خرد**.

### ۳.۲. Hub-and-Spoke

- جهت ledger همیشه hub-and-spoke: یک طرف obligation همیشه **Goldis**
- در v1 obligation peer-to-peer (مثلا TalaMala ↔ AminZar مستقیم) **نداریم** — همه از طریق Goldis
- فروشهای خود Goldis: هیچ inter_company_ledger entry ساخته نمی‌شود (Goldis از خودش نمی‌تواند بدهکار شود)

### ۳.۳. Real-Time Ledger vs Daily Worker

هر فروش **بلافاصله** یک obligation real-time ایجاد میکند (hedging باید سریع باشد). اپراتور Goldis در پایان روز/دوره به‌صورت دستی settle میکند. **یک جدول `inter_company_ledger` + endpoint های settle. بدون settlement_rules پیچیده، بدون worker روزانه.**

### ۳.۴. جریان در زمان فروش غیر-Goldis

**وقتی هر فروشگاه (مثلا TalaMala) یک شمش می‌فروشد:**

| Direction | Asset | Amount | معنی |
|-----------|-------|--------|------|
| TalaMala → Goldis | ریال | `raw_gold_price_per_mg × weight_mg` | TalaMala باید بهای معادل وزن خام را به Goldis بپردازد |
| Goldis → TalaMala | gold خام (mg) | `weight_mg` | Goldis باید معادل وزن خام طلا را فیزیکی به TalaMala تحویل دهد |

**سود فروش نزد TalaMala میماند.** Goldis فقط بهای طلای خام را میگیرد و طلای خام را تحویل می‌دهد — هیچ profit share نیست ([D-39](../01-decisions-audit-log.md)).

### ۳.۵. Settle Operations (دستی توسط اپراتور Goldis)

#### Settle Rial
```
POST /api/v1/admin/inter-company/settle-rial
Body: { creditor_company_id: Goldis, debtor_company_id: TalaMala, amount_rial, notes }
→ D-102: append an OPPOSITE-direction settlement row (debtor=Goldis, creditor=TalaMala,
         asset='IRR', source_type='settlement') → net rial moves toward zero. No FIFO/status.
→ audit in audit_logs
```

#### Settle Gold
```
POST /api/v1/admin/inter-company/settle-gold
Body: { creditor_company_id: TalaMala, debtor_company_id: Goldis, amount_mg, notes }
→ D-102: append an OPPOSITE-direction settlement row (debtor=TalaMala, creditor=Goldis,
         asset='XAU_MG', source_type='settlement') → net gold moves toward zero. No FIFO/status.
→ اگر source_bulk_gold_id: withdraw from bulk_gold_inventory + inventory_movement
```

### ۳.۶. Buyback و اثرش بر دفتر بین‌شرکتی

**بازخرید هرگز فروش اصلی را reverse نمیکند** ([D-32](../01-decisions-audit-log.md)/[D-58](../01-decisions-audit-log.md)):

- **بازخرید تحویل‌نشده / حضوری:** تبدیل physical↔digital ⇒ اثر خزانه ≈ **خنثی** (دو پای متقابل)، **هیچ جفت تعهد طلایی تازهای** ساخته نمی‌شود
- **بازخرید دیجیتال** = همان `digital_trade sell`. در scope غیر-Goldis یک **جفت تازهی مخالف** (rial + gold reversed); در scope=Goldis فقط خزانه‌ی `−`

### ۳.۷. نمونه واقعی

کاربر در برند طلاملا شمش ۱g می‌خرد، قیمت کل ۵۲M ریال (= ۴۸M طلای خام + ۴M اجرت/مالیات/سود TalaMala):

- پرداخت → TalaMala IPG (۵۲M به حساب TalaMala)
- شمش از inventory_location TalaMala به مشتری
- در همان transaction:
  - `inter_company_ledger`: TalaMala → Goldis، rial، **۴۸M** (ردیف append-only علامت‌دار، بدون status — D-102)
  - `inter_company_ledger`: Goldis → TalaMala، gold، **۱۰۰۰mg** (ردیف append-only علامت‌دار، بدون status — D-102)
  - `treasury_positions`: Goldis exposure +۱۰۰۰mg
- **سود ۴M (= ۵۲M − ۴۸M) نزد TalaMala باقی میماند**

عملیاتهای بعدی:
1. Goldis از بازار طلای خام معادل ۱g می‌خرد → treasury exposure کاهش مییابد
2. TalaMala فردا ۴۸M ریال واریز → اپراتور `settle-rial` → ردیف جهت‌مخالف append → **net** rial→۰ (D-102)
3. Goldis هفتگی/ماهانه طلای خام فیزیکی به TalaMala تحویل → `settle-gold` → ردیف جهت‌مخالف append → **net** gold→۰

> Canonical schemas: [Inter-Company Ledger](../03-schema-index.md#4-inter-company-ledger)

---

## ۴. Payment Model

### ۴.۱. Payment Account Resolution ([D-63](../01-decisions-audit-log.md))

هر channel یک لیست اولویت‌دار درگاه دارد (`sales_channel_payment_accounts`). موقع پرداخت: اولین payment_account enabled و سالم؛ اگر down → fallback به بعدی. هر بار درگاهی خطا داد → notification + audit.

### ۴.۲. Payment State — Observability Only ([D-103](../01-decisions-audit-log.md) override of [D-92](../01-decisions-audit-log.md))

finalize یک **transaction اتمیک واحد** است: gateway-verify خارج از tx؛ سپس در یک tx: wallet ledger → treasury position (from hold) → inter-company net rows → outbox events → order.status=Paid. بازیابی crash = **retry idempotent کل عملیات** با کلید کسب‌وکاریِ پایدار (نه saga؛ نه consume کردن state برای resume).

`payment_states` صرفاً برای observability/alerting است و **هیچ شاخه‌ی control-flow** آن را برای resume نمی‌خواند:

```
pending → verified_pending → finalized
                          → failed
                          → cancelled
```

- `gateway_verified_at`: when gateway confirmed payment (observability)
- `idempotency_key`: کلید کسب‌وکاری پایدار برای retry idempotent finalize

### ۴.۳. Split Payment (physical_purchase_from_wallet)

سه منبع ممکن:
1. wallet XAU_MG (gold part)
2. wallet IRR (در همان legal_entity — rial part)
3. gateway (مازاد rial)

ثبت در `order_payment_allocations` — هر allocation یک منبع پرداخت explicit با link به wallet_lock یا payment. Atomic confirm: یا همه consume یا همه release.

### ۴.۴. Rial Topup ([D-76](../01-decisions-audit-log.md))

کاربر در سایت هر brand می‌تواند wallet ریالی همان brand را شارژ کند. **هیچ تأیید اپراتوری لازم نیست.** Backend resolves: فرانت/کانال → wallet_scope (ایزوله per D-46).

### ۴.۵. Rial Withdrawal ([D-64](../01-decisions-audit-log.md))

- **همه‌ی** برداشتها نیاز به تأیید اپراتور دارند (v1)
- حساب بانکی باید به نام خود کاربر باشد (national_id match — D-64)
- برداشت به حساب شخص ثالث **ممنوع** (D-64)

> Canonical schemas: [Payment](../03-schema-index.md#12-payment), [Wallet](../03-schema-index.md#2-wallet)

---

## ۵. Critical Financial Subsystems

### ۵.۱. Payment Reconciliation ([D-96](../01-decisions-audit-log.md))

Handles price lock expiry during gateway round-trip: `payment_reconciliations` tracks variance between authorized amount and actual price, with auto-approve thresholds.

### ۵.۲. Pending Reserves ([D-97](../01-decisions-audit-log.md))

`inventory_pending_holds`: per-order treasury reserve during checkout. Prevents race condition where treasury cap check passes at checkout but breaches by payment time. Finalized or released atomically.

### ۵.۳. Payment State Machine ([D-103](../01-decisions-audit-log.md) override of [D-92](../01-decisions-audit-log.md))

Observability-only state tracking for orphaned payment recovery ([D-103](../01-decisions-audit-log.md)). finalize یک transaction اتمیک واحد است؛ بازیابی = retry idempotent کل عملیات با کلید کسب‌وکاری پایدار (نه checkpoint/saga per-step). `payment_states` فقط observability/alerting است و هیچ control-flow ای آن را برای resume نمی‌خواند.

### ۵.۴. POS Offline Queue ([D-99](../01-decisions-audit-log.md))

`pos_pending_requests`: offline-capable POS devices can queue sales with idempotency key `(dealer_id, pos_session_id, request_id)`. 24-hour TTL. Server-side dedup on retry.

> Canonical schemas: [Supplementary (critical subsystems)](../03-schema-index.md#14-supplementary)

---

## ۶. Related Flows

- [Flow 01 — Physical Bar Purchase (Site)](../flows/01-physical-bar-purchase-site.md)
- [Flow 02 — Digital Gold Buy](../flows/02-digital-gold-buy.md)
- [Flow 03 — Digital Gold Sell](../flows/03-digital-gold-sell.md)
- [Flow 04 — Physical Purchase from Wallet](../flows/04-physical-purchase-from-wallet.md)
- [Flow 05 — Buyback Undelivered](../flows/05-buyback-undelivered.md)
- [Flow 06 — Buyback In-Person](../flows/06-buyback-in-person.md)
- [Flow 09 — Rial Wallet Topup](../flows/09-rial-wallet-topup.md)
- [Flow 10 — Rial Withdrawal](../flows/10-rial-withdrawal.md)
- [Flow 11 — Hedge Buy & Bulk Gold Intake](../flows/11-hedge-buy-and-bulk-gold-intake.md)
- [Flow 12 — Inter-Company Settlement](../flows/12-inter-company-settlement.md)
- [Flow 15 — Dealer Commission Settlement](../flows/15-dealer-commission-settlement.md)

## ۷. Key Decisions

| Decision | Summary |
|----------|---------|
| [D-06](../01-decisions-audit-log.md) | Goldis = Central Hedging Desk, hub-and-spoke model |
| [D-31](../01-decisions-audit-log.md) | Gold withdrawal removed — use physical_purchase_from_wallet |
| [D-32](../01-decisions-audit-log.md) | No refund — buyback is independent forward transaction |
| [D-39](../01-decisions-audit-log.md) | No profit share — Goldis only charges raw gold price |
| [D-40](../01-decisions-audit-log.md) | Frontend shows only own scope balance |
| [D-46](../01-decisions-audit-log.md) | Three isolated wallet scopes per user |
| [D-47](../01-decisions-audit-log.md) | Bidirectional treasury caps with inline hard check |
| [D-58](../01-decisions-audit-log.md) | Buyback never reverses original sale |
| [D-63](../01-decisions-audit-log.md) | Priority-based payment account fallback |
| [D-64](../01-decisions-audit-log.md) | Third-party bank withdrawal forbidden |
| [D-74](../01-decisions-audit-log.md) | XAG_MG reserved for future silver |
| [D-76](../01-decisions-audit-log.md) | Topup auto-routes to channel's wallet_scope |
| [D-92](../01-decisions-audit-log.md) | Payment state machine for crash recovery |
| [D-96](../01-decisions-audit-log.md) | Payment reconciliation for price lock variance |
| [D-97](../01-decisions-audit-log.md) | Pending reserves prevent treasury race condition |
| [D-99](../01-decisions-audit-log.md) | POS offline queue with idempotency |
| [D-100](../01-decisions-audit-log.md) | Treasury = signed-sum exposure (coverage model removed) |
| [D-101](../01-decisions-audit-log.md) | Two-level cap + canonical formula + advisory lock per metal |
| [D-102](../01-decisions-audit-log.md) | Inter-company = signed NET running account (FIFO/status removed) |
| [D-103](../01-decisions-audit-log.md) | Atomic payment finalize; payment_state observability-only |
| [D-104](../01-decisions-audit-log.md) | Integer milligram everywhere + single FLOOR rounding |
| [D-105](../01-decisions-audit-log.md) | Pending holds expire (lock_expirer) |
| [D-106](../01-decisions-audit-log.md) | Reconciliation + solvency-invariant worker (financial core) |
