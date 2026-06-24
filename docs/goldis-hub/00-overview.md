# سند معماری گلدیس هاب — نمای کلی

> **نسخه:** 2.7 (نهایی implementation-ready — ۴ Critical Subsystems — 2026-05-18)
> **نسخه قبل:** 2.6 (DeepSeek P0 fixes + ۸ BLOCKER issues — 2026-05-18)
> **تاریخ:** 2026-05-18
> **وضعیت:** ✅✅✅ آماده برای پیاده‌سازی — implementation-safe (۴ subsystem D-96–D-99 برای امنیت مالی تولید)
> **منبع:** سه دور Q&A با تیم Goldis Ops + ادغام ChatGPT + DeepSeek review (۲ بار) + Gemini analysis (۳ خطر مالی) + ۳۹ تصمیم اصلاحی بازبینی (D-46…D-99) + ۱۲ اصلاح P0/P1 schema + ۴ subsystem بحرانی (D-96–D-99)

---

## ۰. مقدمه و نحوه استفاده

این سند **معماری نهایی سیستم گلدیس هاب** است که برای فاز پیاده‌سازی آماده شده‌است. سه بخش اصلی زیر را قبل از هرکاری بخوانید:

1. **۰.۲** — اگر در فاز پیاده‌سازی هستید، اینجا شروع کنید
2. **۰.۰** — اگر این سند را بیرونی مراجعه می‌کنید
3. **۰.۱** — نکات باز و موارد نیازمند بازبینی عمیق

---

## ۰.۰ راهنمای بازبین خارجی (⚠️ برای داور و بازبین‌های بیرونی)

این سند پس از یک بازبینی عمیق **یک‌پارچه و تمیزسازی شده** (v2.1):

1. **متن اصلی سند قطعی و تمیز است** — مستقیما مدل نهایی را می‌گوید (بدون متن خط‌خورده/منسوخ). آن را معتبر بخوان.
2. **دفتر تصمیمات (D-46…D-80) غیرقطعی است** — فقط *چرایی* تغییرات برای حسابرسی. برای ساخت سیستم به بدنه نگاه کن، نه این جدول. See [01-decisions-audit-log.md](01-decisions-audit-log.md).
3. همه‌ی `Q-01…Q-10` و نقاط `A-1…A-13` / `F-1…F-4` **حل شده‌اند** (نگاشتشان در [01-decisions-audit-log.md](01-decisions-audit-log.md) بخش ابهامات).
4. **تمرکز بازبینی روی ۰.۱ (موارد باز) باشد** — تصمیمات با تیم نهایی شده‌اند؛ بازنکن مگر یک **باگ مالی/همزمانی/تفکیک وظایف اثبات‌پذیر** نشان دهی.

## ۰.۱ موارد باز / بازبینی‌نشده (تمرکز داور اینجا)

اینها هنوز عمیق بازبینی **نشده‌اند** و بیشترین ارزش بازبینی بی‌رونی را دارند:

- **عملیات چندنقشی بازبینی‌نشده:** state machine بازخرید حضوری ([flow 06](flows/06-buyback-in-person.md))، عملیات تسویه‌ی بین‌شرکتی ([flow 12](flows/12-inter-company-settlement.md))، intake شمش از کارخانه ([references/inventory-bars-warehouse.md](references/inventory-bars-warehouse.md) §7.3 + [D-48](01-decisions-audit-log.md#d-48))، برداشت ریال ([flow 10](flows/10-rial-withdrawal.md))، تسویه تراکنش POS ([flow 07](flows/07-pos-sale.md)) — از منظر تفکیک وظایف و درگیری واحدهای مختلف.
- **هشدار scope (P۵ در دفتر تصمیمات):** زیرسیستم قیمت(D-65/72)+دفترکل(§6)+خزانه(D-47/67)+نماینده(D-73) سنگین‌ترین و پرریسک‌ترین بخش است؛ تخمین ۱۲ هفته دیگر واقع‌بینانه نیست.
- **موارد تصمیم‌گرفته ولی فقط پیشنویسی (نیاز‌مند طراحی تفصیلی پیاده‌سازی):** موتور resolution نردبان قیمت + کمیسیون ([D-65/D-73](01-decisions-audit-log.md))، fallback درگاه ([D-63](01-decisions-audit-log.md)), پیاده‌سازی چک inline خزانه ([D-47](01-decisions-audit-log.md))، محاسبهی دقیق گردکردن/منبعقیمت تعهدات بین‌شرکتی.
- ابهامات سطح۲ باز سند: `Q-05`(جزئیات ریز)، و هر چیزی که در بخش ابهامات هنوز ✅ نخورده.

> **سؤال پیشنهادی به داور:** «با فرض اینکه دفتر تصمیمات قطعی است، فقط روی بخش ۰.۱ (موارد باز) و باگهای مالی/همزمانی/تفکیک وظایف کشفنشده تمرکز کن. تصمیمات را بازنکن مگر باگ مالی اثبات‌پذیر نشان دهی.»

---

## ۰.۲ راهنمای استفاده از این سند

این سند **ورودی فاز پیاده‌سازی** است. هنگام استفاده با یک LLM بهعنوان مهندس پیاده‌ساز:

1. کل این مجموعه مستندات را بخوان تا context کامل بسازد.
2. **مرحله به مرحله** کد بخواه — نه یکجا. ترتیب پیشنهادی در بخش Implementation Roadmap (انتهای این فایل) آمده.
3. هر تصمیم architectural اینجا **explicit** است — assumption نیست.
4. در فاز پیاده‌سازی، LLM باید قبل از کدنویسی هر context، فایل `talamala_v4/CLAUDE.md` و `talamala_pos/CLAUDE.md` را بخواند تا با current state آشنا شود.
5. ابهامات: همه‌ی Q-01…Q-10 حل شده‌اند. موارد باز باقیمانده در **بخش ۰.۱** فهرست شده — قبل از پیاده‌سازی context مربوطه باید حل شوند.

---

## ۱. خلاصه پروژه و دامنه

### ۱.۱. کسب‌و‌کار

گلدیس هاب یک **پلتفرم متمرکز چندبرندی** برای فروش، خرید و مدیریت دارایی طلا است. این سیستم جایگزین چند پروژهی فعلی می‌شود:

- **talamala_v4** — backend فعلی FastAPI + Jinja2 + PostgreSQL در پروداکشن (با کاربر و دیتای واقعی)
- **talamala_pos** — Android/Kotlin frontend دستگاه POS

### ۱.۲. شخصیتهای حقوقی (Companies)

<table>
<thead>
<tr><th>Company</th><th>نوع</th><th>نقشها</th></tr>
</thead>
<tbody>
<tr><td><strong>Goldis</strong></td><td>اپراتور + میز hedging مرکزی + فروشنده چندبرندی</td><td>مدیریت مرکزی پلتفرم (تیم فنی، حسابداری، نظارت)، <strong>مرکز hedging</strong> برای فروشهای TalaMala (طلای خام را از بازار یا از مشتریان می‌خرد و دورهای به TalaMala تحویل می‌دهد)، <strong>فروشنده‌ی واقعی</strong> در brand های Goldis و AminZar (سایت <code>aminzar.com</code> را با اجازه‌ی شرکت امین زر بهعنوان brand بازاریابی می‌گرداند — مدیریت، فروش، سود مال Goldis است)</td></tr>
<tr><td><strong>TalaMala</strong></td><td>کارخانه + فروشنده مستقل + مالک برند</td><td>کارخانه‌ای تولید شمش (با برند طلاملا)، فروشنده‌ی مستقل از طریق سایت/POS/marketplace، گیرندهی پول از فروش برند طلاملا به حساب خود، طرف hedging با Goldis (rial→Goldis ، gold از Goldis)</td></tr>
<tr><td><strong>AminZar</strong></td><td>کارخانه تنها (تأمین‌کننده)</td><td>فقط کارخانه‌ای تولید شمش (با برند امین زر). شمشها را با حاشیه‌ی سود به Goldis می‌فروشد. <strong>هیچ کانال فروش مستقیم ندارد</strong> — سایت <code>aminzar.com</code> را Goldis می‌گرداند (با اجازه). سود امین زر فقط از طریق حاشیه‌ی درصد اجرت است (مثلا اگر امین زر اجرت ۲ درصد تعیین کند، Goldis آن را با ۲.۲ درصد می‌فروشد).</td></tr>
</tbody>
</table>

### ۱.۳. برندها (Brands)

<table>
<thead>
<tr><th>Brand</th><th>brand_owner</th><th>operator</th><th>payment_receiver (default)</th><th>seller_company (default)</th><th>producer (default)</th></tr>
</thead>
<tbody>
<tr><td>Goldis</td><td>شرکت گلدیس</td><td>شرکت گلدیس</td><td>شرکت گلدیس</td><td>شرکت گلدیس</td><td>multi (Goldis/AminZar/TalaMala)</td></tr>
<tr><td>TalaMala</td><td>شرکت طلاملا</td><td>شرکت گلدیس</td><td>شرکت طلاملا</td><td>شرکت طلاملا</td><td>شرکت طلاملا (یا multi)</td></tr>
<tr><td>AminZar</td><td>شرکت امین زر</td><td>شرکت گلدیس</td><td><strong>Goldis</strong></td><td><strong>Goldis</strong></td><td>شرکت امین زر (یا multi)</td></tr>
</tbody>
</table>

**نکتهها:**
- `brand_owner` = مالک علامت تجاری
- `operator` = کسی که سایت و عملیات backend را اداره میکند (همیشه Goldis در v1، طبق [D-03](01-decisions-audit-log.md))
- `payment_receiver` = پول مشتری به حساب کدام شرکت می‌رود
- `seller_company` = فروشنده‌ی حقوقی (صاحب موجودی فیزیکی). در برند امین زر چون Goldis می‌فروشد، `seller_company = Goldis`
- `producer` = پیش‌فرض تولیدکننده، ولی هر brand می‌تواند محصول چند producer را بفروشد (cross-brand sale طبق [D-07](01-decisions-audit-log.md))
- این مقادیر **default به ازای هر برند** هستند ولی می‌توانند به ازای هر کانال فروش بازنویسی شوند (مثلا برند طلاملا روی DigiKala، payment_receiver به Goldis تنظیم می‌شود — [flow 08: marketplace](flows/08-marketplace-sale.md))

### ۱.۴. ابعاد یک سفارش

هر سفارش باید به این سؤالها قطعی جواب بدهد:

<table>
<thead>
<tr><th>بعد</th><th>پاسخگو</th></tr>
</thead>
<tbody>
<tr><td>از کدام brand فروخته شد؟</td><td><code>order.brand_id</code></td></tr>
<tr><td>از کدام channel؟</td><td><code>order.sales_channel_id</code></td></tr>
<tr><td>تولیدکننده‌ی محصول کیست؟</td><td><code>order.producer_company_id</code> (از bar/product می‌آید — صرفا اطلاعاتی، تأثیر مالی ندارد در v1)</td></tr>
<tr><td>فروشنده‌ی حقوقی کیست؟</td><td><code>order.seller_company_id</code> (= صاحب موجودی فیزیکی که شمش از انبارش خارج شد)</td></tr>
<tr><td>operator کیست؟</td><td><code>order.operator_company_id</code> (همیشه Goldis در فاز ۱)</td></tr>
<tr><td>پول به کجا رفت؟</td><td><code>order.payment_account_id</code> → <code>payment_account.company_id</code> (= <code>seller_company</code> معمولا)</td></tr>
<tr><td>تسویه hedging چی؟</td><td>اگر <code>seller_company != Goldis</code> → یک جفت <code>inter_company_ledger</code> entry (rial + gold) به/از Goldis — <a href="01-decisions-audit-log.md">D-06b</a></td></tr>
<tr><td>از کجا fulfill می‌شود؟</td><td><code>order.fulfillment_location_id</code></td></tr>
</tbody>
</table>

### ۱.۵. دامنهٔ پروژه

#### شامل این پروژه:

<table>
<thead>
<tr>
  <th>دستهبندی</th>
  <th>ویژگی</th>
</tr>
</thead>
<tbody>
<tr>
  <td rowspan="3"><strong>محصولات و فروش</strong></td>
  <td>شمش فیزیکی</td>
</tr>
<tr>
  <td>طلای دیجیتال (کیف‌پول)</td>
</tr>
<tr>
  <td>بازار چندکاناله (Multi-channel marketplace)</td>
</tr>
<tr>
  <td rowspan="5"><strong>سیستمهای مالی</strong></td>
  <td>کیف‌پول چنددارایی، ایزوله به ازای هر scope (<a href="01-decisions-audit-log.md">D-46</a>: سه کیف جداگانهٔ Goldis / AminZar / TalaMala)</td>
</tr>
<tr>
  <td>خزانهٔ مرکزی و مدیریت تعهدات طلا (Central Treasury & Hedging)</td>
</tr>
<tr>
  <td>دفترکل بین‌شرکتی (Inter-Company Ledger) — پیگیری تعهدات ریالی و طلایی میان شرکتها</td>
</tr>
<tr>
  <td>برداشت ریالی دو‌مرحله‌ای (Two-stage rial withdrawal)</td>
</tr>
<tr>
  <td>خرید فیزیکی از کیف‌پول (Physical purchase from wallet — جایگزین برداشت طلا)</td>
</tr>
<tr>
  <td rowspan="4"><strong>عملیات</strong></td>
  <td>شبکهٔ نمایندگان (Dealer network)</td>
</tr>
<tr>
  <td>فرایند تحویل کالا</td>
</tr>
<tr>
  <td>بازخرید (Buyback) — شمش تحویل‌داده و تحویل‌نشده</td>
</tr>
<tr>
  <td>قیمتگذاری مرکزی (Centralized pricing)</td>
</tr>
<tr>
  <td rowspan="3"><strong>سیستمهای پشتیبان</strong></td>
  <td>اطلاع‌رسانی (Notifications)</td>
</tr>
<tr>
  <td>حسابرسی کامل (Audit trail)</td>
</tr>
<tr>
  <td>پردازش real-time</td>
</tr>
</tbody>
</table>

---

#### خارج از این نسخه:

| ویژگی | جایگزین یا وضعیت |
|---|---|
| **برداشت طلا** (Gold withdrawal) | جایگزین: خرید فیزیکی از کیف‌پول |
| **بازپرداخت** (Refund) | جایگزین: بازخرید شمش |
| **تقسیم سود / کمیسیون** (Profit sharing & settlement) | نسخهٔ آینده |
| **DCA دورهای** (Dollar-Cost Averaging) | فیچر سرمایهگذاری |
| **داشبورد سود/زیان** (PNL dashboard) | فیچر تحلیلی آینده |
| **ترید و نوسانگیری** (Trading & speculation) | خارج از مدل بیزنس |
| **ارز و کریپتو** | فقط طلا و نقره |
| **زیورآلات سفارشی** | شاید بعدا |
| **Jinja2 و server-side rendering** | کاملا حذف — فقط API |

---

## ۱۸. Migration Plan — Fresh Start ([D-23](01-decisions-audit-log.md) updated)

> **تصمیم نهایی تیم:** v5 از **صفر کامل** شروع می‌شود. هیچ data از v4 به v5 منتقل نمی‌شود.

### اصول fresh start

- ❌ **No data migration** — wallet balances، orders، KYC، dealers، bars، tickets، articles — هیچ‌کدام از v4 منتقل نمیشوند
- ❌ **No ETL scripts** نیاز نیست
- ❌ **No reconcile** بین v4 و v5
- ✅ **Greenfield**: کاربران v5 از صفر ثبتنام می‌کنند، KYC از نو، wallet با balance=0

### استراتژی cutover

این تصمیم نیاز به **پلن جداگانه از تیم بیزینس** دارد که خارج از scope این سند است:

1. **چه می‌شود با کاربران v4 که balance دارند؟**
   - اعلام: قبل از cutover کاربران باید balance خود را به ریال تبدیل و برداشت کنند
   - یا: بعد از cutover با تماس manual reconciliation
   - این تصمیم تجاری/حقوقی است — خارج از scope architectural

2. **چه می‌شود با dealer ها؟** (sub-dealer حذف شد — [D-73](01-decisions-audit-log.md))
   - باید قبل از v5 launch، در پنل v5 ثبتنام مجدد شوند
   - manual onboarding

3. **چه می‌شود با bar های فیزیکی موجود در انبار؟**
   - فقط فیزیکی هستند، در v5 با sticker جدید یا re-scan وارد inventory شوند
   - یا: یک "import bars" admin tool یکبار اجرا شود (این *تنها* tool migration که شاید لازم باشد)

### مزایای fresh start

- پیاده‌سازی v5 سادهتر — هیچ data shape سازگاری نیاز نیست
- ETL scripts، reconcile، D-day window پیچیده — همه حذف شدند
- زمان development ~ ۱-۲ هفته کمتر (فاز ۷ migration در roadmap)

### معایب

- کاربران v4 تجربهی re-onboarding خواهند داشت
- نیاز به communication plan قبل از cutover
- bar های فیزیکی موجود نیاز به admin tool یا manual import

### نکتهی مهم — POS

- `talamala_pos` (Android) **هنوز پروداکشن نرفته** ([D-44](01-decisions-audit-log.md)) — هیچ backward compatibility نیاز نیست. Android app از اول با API v1 جدید کار میکند.

### Tool احتمالی تنها

اگر در آینده تصمیم گرفته شود bars فیزیکی موجود از v4 وارد شوند، یک admin tool یکبار مصرف لازم می‌شود:

```
POST /admin/migration/import-bars-from-csv
   → CSV format: serial_code, weight_mg, purity, producer_company, current_location
```

این tool **خارج از scope فازهای ۰-۷ پیاده‌سازی است.**

---

## ۲۱. Implementation Roadmap

> ⚠️ **بازبینی پیش از ساخت (D-100…D-110) این roadmap را بازچینش می‌کند:**
> - **فاز ۰ harness قبل از هر کد مالی اجباری است** ([D-110](01-decisions-audit-log.md)).
> - **فاز ۰.۵ (ویرایش سند، نه کد):** اعمال D-100…D-108 روی schema/flow + **D-109 بسته شد** (Rasis کاملاً حذف؛ POS greenfield).
> - **زنجیره‌ی مالی نو را جلو بیندازید:** wallet ledger → treasury (signed-sum) → inter-company (net) → outbox در یک finalize اتمیک، اول به‌صورت پروتوتایپ عمودی با تست‌های پولی+concurrency — نه آخر.
> - **reconciliation worker ([D-106](01-decisions-audit-log.md)) جزء هسته‌ی مالی است (فاز ۳، نه ۶).**
> - تخمین هفته‌ایِ زیر **خوش‌بینانه است** (هشدار P۵)؛ به‌عنوان ترتیب نسبی بخوانید، نه تقویم قطعی.

### فاز ۰ — Infrastructure + Build-discipline harness ([D-110](01-decisions-audit-log.md)) (هفته ۱)
1. Project structure (`app/contexts/<name>/...`) + **import-linter** context-boundary contracts
2. Database setup + Alembic (async) + **enum strategy تصمیم‌گرفته per column** (native enum via `alembic-postgresql-enum`، یا `VARCHAR+CHECK`) — downgrade باید reversible بماند
3. Authentication + JWT + middleware (Identity context base)؛ commit/rollback **فقط در مرز use-case**
4. Platform context (Companies/Brands/Channels) — برای resolve از همه middleware ها
5. Outbox infra (table + skeleton publisher)
6. Audit log infra
7. Testing infra (pytest fixtures, testcontainers Postgres, factories) + **concurrency/idempotency fixtures** (harness ایمنی پول)

### فاز ۱ — Core domain (هفته ۲-۳)
8. Identity (User، Session، JWT)
9. KYC (با Shahkar stub اولیه)
10. Catalog
11. Pricing (Source + Config + Internal Base + Channel Formula + PriceLock)
12. Wallet (به ازای کیف‌پول multi-asset ledger — [D-46](01-decisions-audit-log.md): goldis/aminzar/talamala ایزوله)

### فاز ۲ — Transactional (هفته ۴-۵)
13. Inventory
14. Cart
15. Order (purchase only)
16. Payment (Zibal + Sepehr — برای دو tenant)
17. فرایند تحویل کالا

### فاز ۳ — Treasury + Trade + Settlement (هفته ۶-۷)
18. Treasury basic (record + read) — با merge شدن hedging ([D-42](01-decisions-audit-log.md))
19. Wallet trades (digital_trade buy/sell)
20. Withdrawal **فقط ریال** ([D-31](01-decisions-audit-log.md) — gold withdrawal حذف شد)
21. physical_purchase_from_wallet flow (بهجای gold withdrawal)
22. Buyback (دو حالت در v1):
    - (a) بازخرید تحویل‌نشده — آنلاین اتومات (فروش اصلی reverse نمی‌شود)
    - (b) بازخرید حضوری — state machine کامل (PhysicalRequested → … → Completed)
    - (بازخرید دیجیتال = همان `digital_trade sell` — جدا پیاده نمی‌شود)
23. **Hedge Buy flow + bulk_gold_inventory intake** ([D-95](01-decisions-audit-log.md)): Goldis خرید طلای خام از بازار/ارزی یا دریافت طلا از تولیدکنندهها (supplier purchase [D-48](01-decisions-audit-log.md))؛ ثبت در treasury (−exposure)؛ تولید شمش و توزیع در شبکه.
24. Inter-Company Ledger ([D-06b](01-decisions-audit-log.md)/[D-102](01-decisions-audit-log.md)): جدول `inter_company_ledger` — دفترِ **NET علامت‌دارِ append-only**؛ outstanding = جمع خالص per (pair, asset)؛ settle = ردیف جهت‌مخالف (جفت‌های مخالف auto-net)؛ بدون FIFO/status/row-mutation. **بدون settlement_rules، بدون worker روزانه.**
25. Treasury alert worker
    + **Reconciliation + solvency-invariant worker** ([D-106](01-decisions-audit-log.md)) — هسته‌ی مالی، نه فاز ۶

### فاز ۴ — DealerNetwork (هفته ۸-۹)
> ✅ **D-109 بسته شد:** Rasis کاملاً حذف شد — POS این فاز کاملاً **greenfield** است (فقط اپِ `talamala_pos`، API v1 جدید — [D-44](01-decisions-audit-log.md)/[D-109](01-decisions-audit-log.md))؛ دیگر gate ندارد.
26. Dealer + Tier + dealer_commission_rates + dealer_commission_ledger (بدون SubDealer/شبکه — [D-73](01-decisions-audit-log.md))
27. POS context (sales_channels.type=pos)
28. POS reserve→confirm flow
29. DealerSale + commission
30. **Dealer commission settlement + treasury/inter-company offset** ([D-84](01-decisions-audit-log.md)/[D-95](01-decisions-audit-log.md)):
    - (a) واریز کمیسیون طلایی نماینده: `POST /admin/dealer/{id}/deposit-commission { amount_mg, source_dealer_sales_ids }` ← XAU_MG wallet نماینده +، Treasury position +pure_gold_mg (exposure افزا‌یش)
    - (b) Treasury check: اگر TalaMala commission (یعنی نماینده TalaMala محصولات فروخته)، یک inter_company_ledger entry ایجاد می‌شود **بهجای** FIFO settle:
      - `debtor=TalaMala, creditor=Goldis, asset=gold, amount=commission_amount_mg`
      - دلیل: TalaMala طلا به نماینده داد (treasury −)، ولی این طلا باید از hedge obligation Goldis (تعهد Goldis→TalaMala) پوشش خوردہ شود. بدون offset، Treasury balance misaligned میماند.
    - (c) Manual settlement flow (v1): اپراتور ماهانه: `POST /admin/inter-company/settle-offset { company_a=TalaMala, company_b=Goldis, comment="commission settlement month N" }` → یک ردیف جهت‌مخالف می‌افزاید تا تعهد hedge + تعهد commission روی همان (pair, asset) به‌صورت **NET** به صفر برسند ([D-102](01-decisions-audit-log.md))؛ بدون FIFO
    - (d) نکته پیاده‌سازی: اگر in v1 offset خود‌کار نباشد (فقط manual)، توثیق شود که *اپراتور هر ماه این endpoint را اجرا میکند*. در فاز ۵+ می‌تواند worker شود.

### فاز ۵ — Marketplace (هفته ۱۰)
31. Adapter interface + skeleton
32. DigiKala adapter (mode=`push_managed` per [D-37](01-decisions-audit-log.md))
33. Marketplace poller worker

### فاز ۶ — Realtime & polish (هفته ۱۱)
34. SSE endpoint + broadcaster
35. Notification preferences UI (API)
36. Admin reporting endpoints
37. Audit viewer API

### فاز ۷ — Launch (هفته ۱۲)
> **توجه: Migration از v4 وجود ندارد ([D-23](01-decisions-audit-log.md): Fresh start)** — فاز ۷ شامل launch tasks است نه ETL.

38. Communication plan با کاربران v4 (خارج از scope توسعه — تیم بیزینس)
39. Staging environment final smoke testing
40. Production deployment + DNS switch
41. (Optional) Admin tool یکبار مصرف import-bars-from-csv برای bars فیزیکی موجود v4

---

## ۲۲. دستورالعمل به LLM پیاده‌ساز

### قبل از کدنویسی هر context

1. این مجموعه مستندات را کامل بخوان
2. `talamala_v4/CLAUDE.md` و `talamala_pos/CLAUDE.md` را بخوان
3. ابهامات مربوط به context را بررسی کن — اگر حل نشده، **سؤال بپرس**
4. ساختار folder/file context را اول طراحی کن (بدون مدل)، تأیید بگیر

### قواعد فنی الزامی

- Type hints کامل (mypy strict)
- SQLModel (Table) برای DB، Pydantic (Create/Update/Read) برای API — هرگز Table مستقیم به API
- async-first (SQLAlchemy 2.x async + asyncpg)
- Explicit transaction در هر service method
- `SELECT FOR UPDATE` برای wallet balance و bar reservation. **خزانه:** ناحیه‌ی بحرانی سقف با `pg_advisory_xact_lock(hashtext('treasury:'||metal_type))` سریالایز می‌شود و `treasury_settings` با `SELECT` ساده داخل همان ناحیه خوانده می‌شود — نه `SELECT FOR UPDATE` روی `treasury_settings` (D-101). ترتیب قفل: advisory(treasury per metal) → wallet rows → bar.
- `idempotency_key` در همه‌ی POST تغییردهنده
- Repository pattern برای DB
- Service pattern برای business logic
- زبان comment ها: انگلیسی. زبان commit message: انگلیسی. زبان UI/پیامهای کاربر: فارسی.
- هیچ business logic در route handler — همیشه در service
- هیچ float برای پول/طلا/وزن. integer برای amount، Decimal برای rate/coefficient.

### قواعد محصولی

- هیچ منطق مالی بدون audit/ledger
- هیچ تغییر balance بدون LedgerEntry
- هیچ تغییر treasury position بدون TreasuryPosition row
- هیچ تغییر critical setting بدون audit_logs
- Event حیاتی → outbox در همان transaction

### قواعد تعامل

- مرحله به مرحله کد بزن. هر مرحله ≤ ۵۰۰ خط
- هر مرحله شامل: مدل + service + route + test + alembic migration
- بعد از هر مرحله تأیید بگیر
- تست همراه با کد — نه بعد از آن
- هرگز کدی نزن که قبلا پرسیدهاش روشن نیست

### قواعد مخصوص migration

- هیچ change ای روی DB پروداکشن v4 بدون تأیید
- ETL scripts را به‌صورت idempotent بنویس (قابل re-run)
- Dry-run همیشه قبل از run واقعی
