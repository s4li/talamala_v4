# سند معماری گلدیس هاب — پلتفرم متمرکز چندبرندی فروش، خرید و مدیریت دارایی طلا

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
2. **۲.۵ «دفتر تصمیمات» (D-46…D-80) غیرقطعی است** — فقط *چرایی* تغییرات برای حسابرسی. برای ساخت سیستم به بدنه نگاه کن، نه این جدول.
3. همه‌ی `Q-01…Q-10` و نقاط `A-1…A-13` / `F-1…F-4` **حل شده‌اند** (نگاشتشان در بخش ۲۰ (ابهامات — وضعیت) و بخش ۲.۵ (تصمیمهای معماری)).
4. **تمرکز بازبینی روی ۰.۱ (موارد باز) باشد** — تصمیمات ۲.۵ با تیم نهایی شده‌اند؛ بازنکن مگر یک **باگ مالی/همزمانی/تفکیک وظایف اثبات‌پذیر** نشان دهی.

## ۰.۱ موارد باز / بازبینی‌نشده (تمرکز داور اینجا)

اینها هنوز عمیق بازبینی **نشده‌اند** و بیشترین ارزش بازبینی بی‌رونی را دارند:

- **عملیات چندنقشی بازبینی‌نشده:** state machine بازخرید حضوری (۱۲.۵.۲ب)، عملیات تسویه‌ی بین‌شرکتی (۶.۵)، intake شمش از کارخانه (۷.۳ + D-48)، برداشت ریال (۱۲.۶)، تسویه تراکنش POS (۹) — از منظر تفکیک وظایف و درگیری واحدهای مختلف.
- **هشدار scope (P۵ در ۲.۵):** زیرسیستم قیمت(D-65/72)+دفترکل(۶)+خزانه(D-47/67)+نماینده(D-73) سنگین‌ترین و پرریسک‌ترین بخش است؛ تخمین ۱۲ هفته دیگر واقع‌بینانه نیست.
- **موارد تصمیم‌گرفته ولی فقط پیشنویسی (نیاز‌مند طراحی تفصیلی پیاده‌سازی):** موتور resolution نردبان قیمت + کمیسیون (D-65/73)، fallback درگاه (D-63)، پیاده‌سازی چک inline خزانه (D-47)، محاسبهی دقیق گردکردن/منبعقیمت تعهدات بین‌شرکتی.
- ابهامات سطح۲ باز سند: `Q-05`(جزئیات ریز)، و هر چیزی که در بخش ۲۰ (ابهامات — وضعیت) هنوز ✅ نخورده.

> **سؤال پیشنهادی به داور:** «با فرض اینکه ۲.۵ قطعی است، فقط روی بخش ۰.۱ (موارد باز / بازبینی‌نشده (تمرکز داور اینجا)) و باگهای مالی/همزمانی/تفکیک وظایف کشفنشده تمرکز کن. تصمیمات ۲.۵ را بازنکن مگر باگ مالی اثبات‌پذیر نشان دهی.»

---

## ۰.۲ راهنمای استفاده از این سند

این سند **ورودی فاز پیاده‌سازی** است. هنگام استفاده با یک LLM بهعنوان مهندس پیاده‌ساز:

1. کل این سند را یکبار به مدل بده تا context کامل بسازد.
2. **مرحله به مرحله** کد بخواه — نه یکجا. ترتیب پیشنهادی در بخش ۲۱ آمده.
3. هر تصمیم architectural اینجا **explicit** است — assumption نیست.
4. در فاز پیاده‌سازی، LLM باید قبل از کدنویسی هر context، فایل `talamala_v4/CLAUDE.md` و `talamala_pos/CLAUDE.md` را بخواند تا با current state آشنا شود.
5. ابهامات: همه‌ی Q-01…Q-10 در بخش ۲۰ (ابهامات — وضعیت) حل شده‌اند. موارد باز باقیمانده در **بخش ۰.۱ (موارد باز / بازبینی‌نشده)** فهرست شده — قبل از پیاده‌سازی context مربوطه باید حل شوند.

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
<tr><td>**Goldis**</td><td>اپراتور + میز hedging مرکزی + فروشنده چندبرندی</td><td>مدیریت مرکزی پلتفرم (تیم فنی، حسابداری، نظارت)، **مرکز hedging** برای فروشهای TalaMala (طلای خام را از بازار یا از مشتریان می‌خرد و دورهای به TalaMala تحویل می‌دهد)، **فروشنده‌ی واقعی** در brand های Goldis و AminZar (سایت `aminzar.com` را با اجازه‌ی شرکت امین زر بهعنوان brand بازاریابی می‌گرداند — مدیریت، فروش، سود مال Goldis است)</td></tr>
<tr><td>**TalaMala**</td><td>کارخانه + فروشنده مستقل + مالک برند</td><td>کارخانه‌ای تولید شمش (با برند طلاملا)، فروشنده‌ی مستقل از طریق سایت/POS/marketplace، گیرندهی پول از فروش برند طلاملا به حساب خود، طرف hedging با Goldis (rial→Goldis ، gold از Goldis)</td></tr>
<tr><td>**AminZar**</td><td>کارخانه تنها (تأمین‌کننده)</td><td>فقط کارخانه‌ای تولید شمش (با برند امین زر). شمشها را با حاشیه‌ی سود به Goldis می‌فروشد. **هیچ کانال فروش مستقیم ندارد** — سایت `aminzar.com` را Goldis می‌گرداند (با اجازه). سود امین زر فقط از طریق حاشیه‌ی درصد اجرت است (مثلا اگر امین زر اجرت ۲ درصد تعیین کند، Goldis آن را با ۲.۲ درصد می‌فروشد).</td></tr>
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
<tr><td>AminZar</td><td>شرکت امین زر</td><td>شرکت گلدیس</td><td>**Goldis**</td><td>**Goldis**</td><td>شرکت امین زر (یا multi)</td></tr>
</tbody>
</table>

**نکتهها:**
- `brand_owner` = مالک علامت تجاری
- `operator` = کسی که سایت و عملیات backend را اداره میکند (همیشه Goldis در v1، طبق D-03)
- `payment_receiver` = پول مشتری به حساب کدام شرکت می‌رود
- `seller_company` = فروشنده‌ی حقوقی (صاحب موجودی فیزیکی). در برند امین زر چون Goldis می‌فروشد، `seller_company = Goldis`
- `producer` = پیش‌فرض تولیدکننده، ولی هر brand می‌تواند محصول چند producer را بفروشد (cross-brand sale طبق D-07)
- این مقادیر **default به ازای هر برند** هستند ولی می‌توانند به ازای هر کانال فروش بازنویسی شوند (مثلا برند طلاملا روی DigiKala، payment_receiver به Goldis تنظیم می‌شود — بخش marketplace)

### ۱.۴. ابعاد یک سفارش

هر سفارش باید به این سؤالها قطعی جواب بدهد:

<table>
<thead>
<tr><th>بعد</th><th>پاسخگو</th></tr>
</thead>
<tbody>
<tr><td>از کدام brand فروخته شد؟</td><td>`order.brand_id`</td></tr>
<tr><td>از کدام channel؟</td><td>`order.sales_channel_id`</td></tr>
<tr><td>تولیدکننده‌ی محصول کیست؟</td><td>`order.producer_company_id` (از bar/product می‌آید — صرفا اطلاعاتی، تأثیر مالی ندارد در v1)</td></tr>
<tr><td>فروشنده‌ی حقوقی کیست؟</td><td>`order.seller_company_id` (= صاحب موجودی فیزیکی که شمش از انبارش خارج شد)</td></tr>
<tr><td>operator کیست؟</td><td>`order.operator_company_id` (همیشه Goldis در فاز ۱)</td></tr>
<tr><td>پول به کجا رفت؟</td><td>`order.payment_account_id` → `payment_account.company_id` (= `seller_company` معمولا)</td></tr>
<tr><td>تسویه hedging چی؟</td><td>اگر `seller_company != Goldis` → یک جفت `inter_company_ledger` entry (rial + gold) به/از Goldis — D-06b</td></tr>
<tr><td>از کجا fulfill می‌شود؟</td><td>`order.fulfillment_location_id`</td></tr>
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
  <td>کیف‌پول چنددارایی، ایزوله به ازای هر scope (D-46: سه کیف جداگانهٔ Goldis / AminZar / TalaMala)</td>
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

## ۲. تصمیمهای معماری اصلی

این تصمیمها در سه دور Q&A با تیم نهایی شده‌اند. **هیچ‌کدام در فاز پیاده‌سازی نباید دوباره بحث شوند.**

<table>
<thead>
<tr><th>#</th><th>تصمیم</th><th>انتخاب نهایی</th><th>منبع</th></tr>
</thead>
<tbody>
<tr><td>D-01</td><td>سبک معماری</td><td>**Modular Monolith** با مرزهای bounded context صریح، آماده برای استخراج سرویس در آینده</td><td>تیم</td></tr>
<tr><td>D-02</td><td>مدل multi-company</td><td>**One Platform / Multi Brand / Multi Company / Centralized Ops by Goldis**</td><td>تیم</td></tr>
<tr><td>D-03</td><td>Operator مرکزی</td><td>همیشه Goldis در فاز ۱ — یک admin panel برای همه برندها</td><td>تیم</td></tr>
<tr><td>D-04</td><td>Wallet scope</td><td>**سه کیف کاملا ایزوله به ازای هر کیف‌پول-scope** (goldis/aminzar/talamala) — جزئیات: D-46، ۴</td><td>تیم</td></tr>
<tr><td>D-05</td><td>KYC scope</td><td>**مشترک** — یک KYC، اسناد شاهکار یکبار، هر دو شرکت قبول می‌کنند</td><td>تیم</td></tr>
<tr><td>D-06</td><td>Treasury scope</td><td>**مرکزی Goldis = Central Hedging Desk**. هر فروش (هر شرکت) trigger میزند به hedging: فروشنده اتومات از Goldis طلای خام معادل می‌خرد، و Goldis مسئول است از بازار خام بخرد و فیزیکی تحویل دهد. هر خرید Goldis از بازار → exposure کاهش.</td><td>تیم</td></tr>
<tr><td>D-06b</td><td>**Inter-Company Ledger (Hub-and-Spoke)**</td><td>هر فروش غیر-Goldis (payment به TalaMala/AminZar رفت) **دو obligation همزمان** ایجاد میکند: ۱) `Seller → Goldis: rial` به اندازه‌ی قیمت طلای خام در لحظه‌ی فروش، ۲) `Goldis → Seller: gold mg` به اندازه‌ی وزن خالص. یک طرف ledger همیشه Goldis است (Hub). تسویه دستی توسط اپراتور Goldis، rial سریع/روزانه و gold دورهای فیزیکی. فروشهای خود Goldis هیچ inter-company entry ندارند، فقط treasury exposure را افزا‌یش میدهند.</td><td>تیم</td></tr>
<tr><td>D-06c</td><td>**Inventory ownership model**</td><td>هر `inventory_location` یک `owner_company_id` دارد. شمشهای موجود در انبار هر برند **مال خود همان برند** هستند (قبلا خریداری/تولید شده). **مدل consignment وجود ندارد**. مدل تأمین و توزیع شمشها در بخش چرخه‌ی تولید توضیح داده می‌شود.</td><td>تیم</td></tr>
<tr><td>D-06d</td><td>**Gold settle بدون bar مشخص**</td><td>وقتی Goldis طلای خام را به TalaMala تحویل می‌دهد، فقط مقدار وزن (mg) ثبت می‌شود — نه bar خاص. اپراتور می‌گوید «۱۰g طلای خام تحویل دادم» و قدیمیترین obligation ها FIFO settle میشوند. این طلای خام (گرانول/شمش بزرگ) برای hedging موجودی فروشنده یا تولید بعدی است، **نه refill همان شمش فروختهشده**.</td><td>تیم</td></tr>
<tr><td>D-07</td><td>Cross-brand sale</td><td>**مجاز** — bar تولید TalaMala می‌تواند در برند گلدیس فروخته شود (با settlement)</td><td>تیم</td></tr>
<tr><td>D-08</td><td>Payment gateway</td><td>**به ازای برند** (با چند `payment_account`): Goldis IPG برای Goldis+AminZar، TalaMala IPG برای TalaMala</td><td>تیم</td></tr>
<tr><td>D-09</td><td>Inventory location</td><td>**به ازای هر شخصیت حقوقی ولی fulfillment مرکزی** — انبار اصلی Goldis است، ولی bar میداند producer/owner کیست</td><td>تیم</td></tr>
<tr><td>D-10</td><td>DealerNetwork</td><td>حفظ کامل + توسعه — per-company با opt-in</td><td>تیم</td></tr>
<tr><td>D-11</td><td>POS as sales_channel</td><td>**first-class** — `channels.type='pos'` با terminal_id/payment_account اختصاصی</td><td>ChatGPT proposal</td></tr>
<tr><td>D-12</td><td>Settlement context</td><td>**bounded context جدا** — محاسبهی سهم/سود/طلب بین Goldis ↔ TalaMala ↔ AminZar</td><td>ChatGPT proposal + تیم</td></tr>
<tr><td>D-13</td><td>Fulfillment context</td><td>**bounded context جدا** — task برای انبار‌دار، pick/pack/handover</td><td>ChatGPT proposal</td></tr>
<tr><td>D-14</td><td>Digital gold inventory</td><td>**بدون جدول جداگانه** — همان Treasury Position. (سقف با **D-47 دو‌طرفه شد**: `max_open_exposure_mg` + `max_short_exposure_mg` + چک inline)</td><td>معمار</td></tr>
<tr><td>D-15</td><td>Marketplace integration</td><td>Adapter pattern با ۳ mode: push_managed / pull_only / bidirectional</td><td>معمار</td></tr>
<tr><td>D-16</td><td>Withdrawal model (v1)</td><td>**فقط ریال** — `order_type=withdrawal_rial` + جدول `withdrawal_details` اختصاصی. gold withdrawal در v1 نداریم (D-31)</td><td>معمار + تیم</td></tr>
<tr><td>D-17</td><td>Tech stack</td><td>Python 3.12+ / FastAPI / **SQLModel** / PostgreSQL 16+ / asyncpg / Alembic / Pydantic v2</td><td>تیم + ChatGPT</td></tr>
<tr><td>D-18</td><td>Async/Sync</td><td>**async-first** (تیم async-experienced)</td><td>تیم</td></tr>
<tr><td>D-19</td><td>Frontend</td><td>**کامل جدا** — هر brand یک Next.js/SPA فرانت، admin panel جدا، POS Android. backend فقط REST API.</td><td>ChatGPT proposal + تیم</td></tr>
<tr><td>D-20</td><td>Server</td><td>تک‌سرور Linux + systemd (مثل v4) با چند worker process مستقل</td><td>تیم</td></tr>
<tr><td>D-21</td><td>Message broker</td><td>**Postgres Outbox** primary، Redis Streams **فقط** برای SSE fan-out و rate limit (اختیاری)</td><td>معمار</td></tr>
<tr><td>D-22</td><td>Realtime</td><td>SSE در فاز ۱ (پشت nginx سادهتر)</td><td>معمار</td></tr>
<tr><td>D-23</td><td>Migration از v4</td><td>**Fresh start کامل** — هیچ data از v4 (wallet balance، order، KYC، dealer) به v5 منتقل نمی‌شود. v5 از صفر شروع می‌شود. v4 data و کاربران v4 خارج از scope طراحی v5 هستند. (تصمیم تیم)</td><td>تیم</td></tr>
<tr><td>D-24</td><td>Compliance</td><td>شاهکار (موبایل + کد ملی) + OTP. AML/retention infrastructure-ready ولی feature بعدا</td><td>تیم</td></tr>
<tr><td>D-25</td><td>Worker scheduler</td><td>**APScheduler در process جدا + asyncio loop**. نه Celery، نه Arq</td><td>معمار</td></tr>
<tr><td>D-26</td><td>Source of truth</td><td>PostgreSQL برای همهچیز. هیچ state critical در Redis/Memory.</td><td>معمار</td></tr>
</tbody>
</table>

### تصمیمات دور دوم Q&A (حل ابهامات O-01 تا O-20)

<table>
<thead>
<tr><th>#</th><th>تصمیم</th><th>انتخاب نهایی</th></tr>
</thead>
<tbody>
<tr><td>D-27</td><td>Rounding policy</td><td>**floor بهعنوان default**، قابل بازنویسی به ازای فرمول در `channel_pricing_formulas.rounding_policy`. نکته: floor در دراز مدت به ضرر شرکت — تیم پذیرفت</td></tr>
<tr><td>D-28</td><td>Price lock TTL</td><td>**۲ دقیقه default**، قابل بازنویسی تا حداکثر ۵ دقیقه به ازای هر کانال/formula (`channel_pricing_formulas.lock_ttl_seconds`). متعادل با ریسک نوسان طلا</td></tr>
<tr><td>D-29</td><td>AminZar wallet</td><td>**scope=aminzar کاملا جدا و ایزوله** (در Goldis merge نمی‌شود) — D-46</td></tr>
<tr><td>D-30</td><td>Decimal precision</td><td>Standard: `rate=NUMERIC(20,2)`، `percent=NUMERIC(6,3)`، `coefficient=NUMERIC(8,4)`، `wage_value=NUMERIC(12,4)`</td></tr>
<tr><td>D-31</td><td>**برداشت طلا**</td><td>**حذف کامل** — کاربر نمی‌تواند طلای دیجیتال را به‌صورت فیزیکی برداشت کند. بهجای آن: فروش به ریال (digital_trade sell) یا خرید کالای فیزیکی با wallet XAU_MG</td></tr>
<tr><td>D-32</td><td>**Refund/Buyback model**</td><td>**Refund نداریم. «cancel» نداریم.** Buyback فقط **۲ حالت**: (a) بازخرید تحویل‌نشده (آنلاین مستقل؛ فروش اصلی reverse نمی‌شود)، (b) بازخرید حضوری. «بازخرید دیجیتال» = همان `digital_trade sell`. در هر دو: وزن خالص طلا → wallet XAU_MG؛ `buyback_credit_rial` → wallet IRR فقط با ثبت مالکیت+OTP؛ اجرت/مالیات/سود می‌سوزد. جزئیات: D-53/D-58/D-59/D-68/D-70</td><td>تیم</td></tr>
<tr><td>D-33</td><td>Conversion mismatch</td><td>افزوده در wallet باقی میماند (no auto-conversion)</td></tr>
<tr><td>D-34</td><td>POS payment_account</td><td>**per-device** — هر دستگاه POS یک payment_account با terminal_id جدا</td></tr>
<tr><td>D-35</td><td>Gift box</td><td>modifier جدا (جدول `gift_boxes` با FK به `order_items`)</td></tr>
<tr><td>D-36</td><td>Catalog</td><td>**مرکزی + channel availability + bar serial pre-assignment**. کاربر admin یکجا همه محصولات تعریف میکند. شمشها تک‌به‌تک یا دستهای به یک channel/فروشگاه pre-assign میشوند</td></tr>
<tr><td>D-37</td><td>DigiKala adapter</td><td>mode = `push_managed`</td></tr>
<tr><td>D-38</td><td>Settlement scope</td><td>منتفی — جایش `inter_company_ledger` real-time hub-and-spoke (D-06b)</td></tr>
<tr><td>D-39</td><td>Profit share</td><td>**بدون profit share در v1**. هر فروشنده، کل سود فروش (اجرت + مالیات + اختلاف قیمت) را خودش نگه میدارد. Goldis فقط بابت hedging قیمت طلای خام را میگیرد و طلای خام را تحویل می‌دهد. تیم گفت: «بابت فروش کسی سودی به کسی نمی‌دهد» **⚠️ تفسیرش با D-65 دقیق شد:** profit-share فروش نداریم، ولی قیمت عمدهی طلای Goldis (مبنای hedging = P_hedge) ذاتا مارجین خود Goldis (پوشش مالیات+حداقلسود) را دارد.</td></tr>
<tr><td>D-40</td><td>Brand access</td><td>خود‌کار — frontend مشخص میکند کاربر کدام wallet/brand را میبیند. هیچ opt-in جدا</td></tr>
<tr><td>D-41</td><td>Dealer multi-company</td><td>**مجاز** — unique بر `(company_id, user_id)`، نه فقط user_id</td></tr>
<tr><td>D-42</td><td>Hedging</td><td>merge در Treasury با `source_type IN ('hedge_buy', 'hedge_sell')` — جدول جدا نداریم</td></tr>
<tr><td>D-43</td><td>Observability</td><td>فاز ۱: structured JSON log → stdout → journalctl. فاز ۲: Loki/Grafana</td></tr>
<tr><td>D-44</td><td>POS Android</td><td>**Greenfield** — نسخه قدیم هنوز پروداکشن نرفته. هیچ backward compat نیاز نیست</td></tr>
<tr><td>D-45</td><td>SSE auth</td><td>JWT در httpOnly cookie</td></tr>
</tbody>
</table>

### ۲.۵. دفتر تصمیمات (Decision Log — D-46…D-80)

> **ماهیت:** این جدول **changelog/تاریخچهی استدلال** است (چرا هر تصمیم گرفته شد) — برای حسابرسی و حافظهی تیم. **بدنهی سند از v2.1 تمیز بازنویسی شده و مستقیما مدل نهایی را می‌گوید؛ دیگر برای رفع تناقض نیازی به مراجعهی اجباری به این جدول نیست.** این جدول مرجع «چرا»ست، نه «چه». تصمیمات زیر با تیم نهایی شده‌اند و در پیاده‌سازی دوباره بحث نمیشوند.

<table>
<thead>
<tr><th>#</th><th>تصمیم</th><th>انتخاب نهایی</th><th>اثر روی</th></tr>
</thead>
<tbody>
<tr><td>D-46</td><td>**Wallet scope** (بازنویسی D-04/D-29)</td><td>کیف‌پول per **wallet-scope** نه به ازای هر شخصیت حقوقی. سه scope: `goldis` / `aminzar` / `talamala`. هر سه **کاملا ایزوله، بدون انتقال مستقیم** (AminZar حقوقا زیر شرکت گلدیس ولی برای کاربر کیف جدا). کلید `asset_balances` و `wallet_ledger_entries` و `wallet_locks` بعد `wallet_scope` میگیرد؛ `company_id` حفظ می‌شود (مشتق: goldis/aminzar→شرکت گلدیس، talamala→شرکت طلاملا) برای حسابداری/دفترکل بین‌شرکتی. گزارش حسابداری باید بدهی scope=aminzar را از scope=goldis تفکیک کند. هجینگ بدون تغییر (فروش AminZar هنوز Goldis-side).</td><td>Wallet، Accounting، ۴</td></tr>
<tr><td>D-47</td><td>**Treasury سد سخت + سقف دو‌طرفه**</td><td>علاوه بر worker ۳۰s (که فقط هشدار/پشتیبان است)، در لحظه‌ی **هر** تراکنش (فروش+خرید، فیزیکی+دیجیتال+POS، بدون استثنا) یک چک inline همگام: اگر از سقف رد شود تراکنش **رد می‌شود**. سقف **دو‌طرفه per فلز**: `max_open_exposure_mg` (سمت فروش) + `max_short_exposure_mg` (سمت خرید/بازخرید/فروش کاربر). اپراتور هر دو را per فلز هر زمان تغییر می‌دهد، با audit_log.</td><td>Treasury، ۵</td></tr>
<tr><td>D-48</td><td>**Supplier purchase داخل scope** (بازنویسی D-7.2)</td><td>خرید از کارخانه داخل سامانه است، به‌صورت جریان **فقط-طلا (بدون ریال)** روی همان batch preorder. Goldis به کارخانه می‌دهد: اصل طلا + معادل اجرت به طلا؛ کارخانه شمش حکشده/پلمبشده برمی‌گرداند. تعهد طلایی Goldis↔کارخانه روی همان `inter_company_ledger` با `asset='gold'`, `source_type='supplier_purchase'` رصد می‌شود (جدول جدید لازم نیست). `purchase_wage_percent` عملیاتی می‌شود (دیگر صرفا metadata نیست). طلای اجرت = هزینهی حسابداری، **بدون** اثر روی exposure/سقف خزانه.</td><td>Inventory، Inter-Company، Catalog، ۷.۲</td></tr>
<tr><td>D-49</td><td>**امانی = شمش مشخص allocated** (شفافسازی مدل امانی — مستقل از Q-10 سند)</td><td>طلای امانی یعنی شمش مشخص سریالدار که از **لحظه‌ی خرید** به مشتری تخصیص و قفل می‌شود (allocated، نه pooled). عملیات کنترلشدهی **«تعویض شمش»** (سریال قدیم→جدید هم‌وزن/هم‌عیار) برای موارد گم/آسیب، فقط اپراتور، با ثبت در `ownership_history` + `audit_logs`.</td><td>Fulfillment، Inventory، ۸</td></tr>
<tr><td>D-50</td><td>**Price-lock TTL** (بازنویسی D-28)</td><td>بازهی مجاز ۶۰–۳۰۰ ثانیه (CHECK از `BETWEEN 30 AND 300` به `BETWEEN 60 AND 300`)، پیش‌فرض ۱۲۰s. کف ۱ دقیقه برای شرایط پرنوسان.</td><td>Pricing، ۱۱.۴</td></tr>
<tr><td>D-51</td><td>**قرارداد عیار**</td><td>عیار همیشه **parts-per-1000** (عدد صحیح ۰..۱۰۰۰؛ ۱۸ع=۷۵۰، ۲۴ع=۹۹۹). فرمول وزن خالص همیشه `weight_mg × purity / 1000`. نمونههای `9999` در سند غلطاند و اصلاح میشوند.</td><td>Catalog، Pricing، همه‌ی محاسبات طلا</td></tr>
<tr><td>D-52</td><td>**برداشت ریال** (تأکید)</td><td>در v1 **همه‌ی** برداشتهای ریالی نیاز به تأیید دستی اپراتور دارند — هیچ آستانه‌ی auto-approve نیست.</td><td>Withdrawal، ۱۲.۶</td></tr>
<tr><td>D-53</td><td>**گیت مزیت بازخرید** (اصلاح D-32)</td><td>اجرت/مالیات/سود **همیشه** می‌سوزد. وزن طلای خالص **همیشه** به wallet XAU_MG برمیگردد (طلای واقعی اصالت‌سنجیشده — کاربر همیشه می‌تواند بفروشد). ولی `buyback_credit_rial` **فقط** وقتی پرداخت می‌شود که شمش در لحظه‌ی بازخرید به نام همان کاربر **ثبت مالکیت** شده باشد و با **OTP** واقعیت‌سنجی شود. ثبت‌نشده→صفر (می‌سوزد). ثبت تأخیری اگر قبل/حین بازخرید انجام و OTP تأیید شود، مزیت برقرار است.</td><td>Order/Buyback، ۱۲.۵.۲</td></tr>
<tr><td>D-54</td><td>**ثبت مالکیت per کانال**</td><td>آنلاین: خود‌کار در لحظه‌ی خرید (کد در پنل). POS: **موبایل‌محور** — نماینده موبایل (+کد ملی) را وارد میکند، کاربر پیدا/ساخته می‌شود، شمش به نامش ثبت، کد در پنل فعال؛ موبایل ندهد→ثبت‌نشده. Marketplace: **هرگز** ثبت نمی‌شود. **کارت هدیه: کاملا بیرون از سیستم claim/ثبت** — نه `claim_code`، نه ثبت مالکیت، نه مزیت ریالی؛ حامل فیزیکی = مالک (ولی همچنان می‌تواند برای ارزش طلای خالص بازخرید حضوری کند).</td><td>Inventory، Order، POS</td></tr>
<tr><td>D-55</td><td>**انتقال مالکیت**</td><td>برای شمشهای ثبتشده، هر مالک می‌تواند به موبایل دیگری منتقل کند، با تأیید **OTP** + ثبت در `ownership_history` + `audit_logs`. مزیت `buyback_credit_rial` (از snapshot سفارش اول) **همراه شمش** به مالک جدید ثبتشده منتقل می‌شود.</td><td>Inventory، Order</td></tr>
<tr><td>D-56</td><td>**Marketplace انحصارا Goldis** (حل خلأ ۱۲.۸)</td><td>Goldis **انحصارا** همه‌ی فروش در بازارهای ثالث آنلاین (دیجیکالا/باسلام/…) را برای **همه‌ی** برندها در دست دارد؛ برندها حق ورود مستقیم به این بازارها ندارند. در marketplace همیشه `seller_company=Goldis` و `payment_receiver=Goldis`؛ هیچ ردیف بین‌شرکتی marketplace. سایت اختصاصی هر برند مستثناست (talamala.ir همچنان برند TalaMala با پول به TalaMala).</td><td>Marketplace، ۱۲.۸</td></tr>
<tr><td>D-57</td><td>**POS فقط انبار خود نماینده** (تأکید)</td><td>نماینده با POS فقط کالاهایی را که از قبل برای او تعریف و به انبار خودش ورود خورده می‌فروشد (نه pool مرکزی).</td><td>POS، ۱۲.۷</td></tr>
<tr><td>D-58</td><td>**«لغو» حذف — همهچیز Buyback** (بازنویسی D-32 زیرflow a)</td><td>مفهوم cancel وجود ندارد. فروش اول **همیشه معتبر و کامل** میماند (سود پیش فروشنده). اگر مشتری پشیمان شد، یک تراکنش **بازخرید مستقل روبهجلو** رخ می‌دهد (نه باطلکردن فروش). اقتصاد همیشه یکسان: اجرت/مالیات/سود می‌سوزد، وزن خالص→کیف XAU_MG، `buyback_credit_rial`→کیف IRR (با شرط D-53)، در scope برند فروش. سه **حالت عملیاتی** (نه مدل مالی متفاوت): (۱) تحویل‌نشده=آنلاین/اتومات، شمش بهحالت قابل‌فروش، بدون state machine؛ (۲) تحویل‌شده=حضوری با state machine + اصالت‌سنجی؛ (۳) دیجیتال=فروش طلای دیجیتال کیف. زیرflow `cancel_before_delivery` با `Order.status=Cancelled` **منسوخ** است.</td><td>Order/Buyback، ۱۲.۵.۲</td></tr>
<tr><td>D-60</td><td>**حل Q-10 — منبع شمش physical_purchase_from_wallet**</td><td>شمش فیزیکی از موجودی **همان scope/برند کیف‌پول** برداشته می‌شود (نه انبار مرکزی Goldis). این جریان از نظر پول/برند/فروشنده دقیقا مثل یک خرید فیزیکی عادی است؛ فقط ابزار پرداخت بهجای ریال/درگاه، طلای کیف است → `seller_company`=همان scope، تعهد بین‌شرکتی طبق قاعدهی فروش غیر-Goldis. اگر شمش هم‌وزن در آن scope موجود نبود، خرید انجام نمی‌شود (سازگار با O-03). **مبنا:** طلای دیجیتال کاغذی نیست — هر خرید دیجیتال scope غیر-Goldis یک تعهد طلای واقعی از Goldis میسازد که Goldis دورهای فیزیکی تحویل می‌دهد؛ پس انبار آن scope از همین مسیر پر می‌شود.</td><td>Inventory، Treasury، ۱۲.۵، ۲۰</td></tr>
<tr><td>D-61</td><td>**حل Q-06 — مدل سطوح KYC در v1**</td><td>سه سطح: **L0** (فقط موبایل+OTP) → **هیچ تراکنش مالی** (فقط مرور/سبد/مشاهده قیمت؛ نه خرید، نه کیف‌پول، نه شارژ). **L1** (شاهکار موبایل↔کدملی منطبق + نام/کدملی) → سطح پایهی معامله با سقفهای محتاطانه. **L2** (L1 + احراز مالکیت حساب بانکی: تطبیق شبا↔کدملی + تأیید دستی اپراتور اختیاری) → سقفهای بالاتر/سفارشی. اعداد سقفها (۴ بعد×روزانه/ماهانه) در `user_level_defaults` **اپراتور-تنظیم با audit**، نه hard-code در سند. آستانه‌های پیشرفتهی AML همان «فیچر بعدی» D-24 باقی میماند.</td><td>KYC، ۱۱.۲، ۲۰</td></tr>
<tr><td>D-62</td><td>**حل Q-07 + انتقال انبار دو‌مرحله‌ای**</td><td>**(الف)** هیچ TTL/بازتخصیص خود‌کار روی طلا نیست — فقط گزارش/هشدار **سن‌خوردگی** (شمشهای راکد در یک کانال) و ابزار دستی اپراتور برای برداشتن/تغییر `assigned_channel_id` (با `inventory_movement`+audit). **(ب) انتقال بین انبارها = سند انتقال دو‌مرحله‌ای** (الگو‌ی WMS/ERP): `DRAFT → DISPATCHED (Goods Issue، اسکن سریال خروج، مبدأ کم) → RECEIVED (Goods Receipt، اسکن سریال ورود در مقصد) → COMPLETED`، شاخهی `DISCREPANCY` برای مغایرت. موجودی در راه = **`inventory_location` مجازی با `location_type='in_transit'`** و پرچم غیرقابل‌فروش (هیچجا reserve/فروش نمی‌شود تا رسید). **تفکیک وظایف:** فرستنده ≠ گیرنده؛ هر مرحله audit + `inventory_movement` per شمش. **v1:** اسکن دو‌طرفه + تفکیک وظایف + audit + **OTP تحویل اجباری** بین مبدأ/مقصد + هشدار «گیرکرده در راه»؛ بارنامه/پیک/بیمه = metadata اختیاری. آستانه‌های سن‌خوردگی/گیرکرده **اپراتور-تنظیم با audit**. ارتقا‌ی `DealerTransfer`/`ReconciliationSession` v4.</td><td>Inventory، Fulfillment، ۱۱.۵، ۲۰</td></tr>
<tr><td>D-63</td><td>**حل Q-08 — انتخاب درگاه (به ازای کانال، بدون انتخاب کاربر در v1)**</td><td>هر `sales_channel` یک **لیست اولویت‌دار از `payment_account`ها** دارد. موقع پرداخت، اولین درگاه **فعال و سالم** خود‌کار انتخاب می‌شود؛ اگر down بود **fallback خود‌کار** روی درگاه بعدی لیست. کاربر هیچ انتخابی نمیبیند (multi-PSP UX به v2 موکول؛ مدل طوری بماند که بعدا بدون تغییر اضافه شود). اپراتور می‌تواند per `payment_account` «موقتا غیرفعال» کند. **الزامی:** هر بار درگاهی خطا/down تشخیص داده شد (حتی اگر fallback پوشش داد) → **اطلاع‌رسانی به اپراتور/ادمین** (notification + audit) که کدام PSP مشکل دارد.</td><td>Payment، ۱۱.۷، ۲۰</td></tr>
<tr><td>D-64</td><td>**حل Q-09 — برداشت فقط به حساب خود کاربر**</td><td>برداشت ریال **فقط** به حساب بانکی متعلق به همان کاربر مجاز است: نام صاحب شبا باید با کد ملی KYC تطبیق داده شود (`user_bank_accounts.is_verified=TRUE` از طریق استعلام بانکی/شاهکار). برداشت به حساب شخص دیگر **ممنوع** — شرط صریح سازمان مبارزه با پولشویی (ضد الگو‌ی واریز-کارت-A / برداشت-حساب-B). دولایه با D-52 (احراز سیستمی + تأیید اپراتور). اشخاص حقوقی (حساب بهنام شرکت) **خارج از scope v1**، موکول به v2/onboarding دستی.</td><td>Withdrawal، Compliance، ۱۱.۱، ۲۰</td></tr>
<tr><td>D-65</td><td>**نردبان قیمت + بعد سطح (حل A-1/A-2، اصلاح تفسیر D-39)**</td><td>**نقاط قیمتی نامدار per فلز در لحظه:** `P0`=`internal_base_price` (هزینهی مرجع خام، داخلی، بی‌سود) → `P_hedge`=قیمت عمدهی Goldis = P0 + حداقلمارجین Goldis که **تضمینا ≥ مالیات دولت + حداقل سود** → `P_partner(tier)` (هر `DealerTier` یک عدد، همیشه ≥ P_hedge) → `P_retail` (مشتری نهایی پیش‌فرض، بالاترین). **هیچکس زیر P_hedge نمی‌خرد؛ Goldis هرگز بی‌سود/زیرمالیات نمی‌فروشد. بعد سطح:** ستون `dealer_tier_id BIGINT NULL` به `channel_pricing_formulas` (رزولوشن با همان `priority`؛ `NULL`=مشتری نهایی). v1 فقط مشتری نهایی + سطوح همکار/نماینده (VIP خرده به v2). برای **طلای دیجیتال** (بدون اجرت) تمایز سطح کاملا در مارجین متال فرمول است (شکاف مدل اجرت‌محور v4 رفع شد). **Invariant:** هم موقع ذخیرهی فرمول هم موقع ساخت price_lock باید خروجی ≥ P_hedge ≥ (P0+مالیات+حداقلمارجین)؛ نقض ⇒ رد/clamp + هشدار اپراتور. P_hedge **یک نقطهی per-فلز در سطح شرکت Goldis** (نه per کانال) تا ریاضی بین‌شرکتی یکدست بماند. **حل A-1:** تنها مبنای `inter_company_ledger` = `order_items.raw_hedge_price_rial` = `P_hedge_per_mg(لحظه‌ی فروش) × pure_gold_mg`؛ ۱۲.۱ گام d/e اصلاح، خطوط «cost transfer reverse» منسوخ. **`cost_price_rial` → نام/تعریف `raw_hedge_price_rial`؛ `supplier_price_rial` حذف** (بیمصرف بعد از D-48). **اصلاح تفسیر D-39 (نه نقض):** «بابت فروش profit-share نیست» سرجایش است؛ ولی قیمت عمدهی طلای Goldis ذاتا مارجین خود Goldis (پوشش مالیات+حداقلسود) را دارد — این دو سازگارند.</td><td>Pricing، Inter-Company، Catalog، ۵، ۶.۴، ۱۱.۴، ۱۱.۶، ۱۲.۱</td></tr>
<tr><td>D-75</td><td>**حل A-11 — بسته‌بندی/جعبهی هدیه = کالای ریالی جدا**</td><td>بسته‌بندی یک کالای جدا با قیمت ریالی مستقل است که فقط در صورت خواست مشتری به سفارش اضافه می‌شود (D-35/v4). مرزها: (۱) **صرفا ریالی** — نه طلا، نه `pure_gold_mg`؛ وارد نردبان D-65 نمی‌شود، exposure خزانه نمیسازد، تعهد بین‌شرکتی ندارد. (۲) در بازخرید **برنمیگردد** (مثل اجرت می‌سوزد — D-53). (۳) پرداختش **همیشه ریالی** است؛ حتی در `physical_purchase_from_wallet` سهم بسته‌بندی از کیف ریالی/درگاه، نه طلای کیف. (۴) پولش به scope فروشنده می‌رود؛ هیچ ردیف بین‌شرکتی ندارد. (۵) **خارج از مبنای کمیسیون نماینده** (D-73 بند۵؛ مبنا فقط `pure_gold_mg`).</td><td>Catalog، Order، Pricing، ۱۱.۶</td></tr>
<tr><td>D-80</td><td>**حل F-4 — مرز Fulfillment ↔ انتقال داخلی (D-62)**</td><td>مرز بر اساس «مشتری درگیر است یا نه»: **fulfillment = فقط جابهجایی گرهخورده به سفارش مشتری** (همیشه `order_id` دارد — تحویل حضوری/پیک/فروشگاه). **همه‌ی انتقال‌های داخلی بین انبارها (بدون مشتری) فقط از مسیر دو‌مرحله‌ای D-62.** مقصد `internal_transfer` از `fulfillment_tasks` **حذف**. اتصال: اگر شمش مورد تحویل در انبار دیگری است، **اول** انتقال D-62 (مرکزی→محل تحویل)، **بعد** task fulfillment در مقصد — پشتسر هم، نه موازی. یک مفهوم/یک سیستم؛ بدون گزارش دوگانه.</td><td>Fulfillment، Inventory، ۸</td></tr>
<tr><td>D-79</td><td>**حل F-3 — مسیرهای استثنای تحویل (گم/پسزده/آسیب)**</td><td>به `fulfillment_tasks.status` اضافه می‌شود: **`delivery_failed`** (پیک نتوانست/مشتری پس زد/آدرس غلط) → شمش با همان فرایند دو‌مرحله‌ای D-62 (in-transit + اسکن ورود) به انبار برمیگردد؛ تا برنگشته «در راه برگشت». **`lost_in_transit`** (گم/دزدیده) → رویداد زیان: عملیات ادعا از پیک، حسابداری ثبت زیان (audit + accounting)، **خزانه: یک پای جبرانی exposure** (طلا فروخته/هجشده ولی فیزیکش نیست). **`damaged`** (پلمب‌شکسته) → برمیگردد + شمش «نیاز‌مند بازرسی» (پلمب/ذوب مجدد) — مستقیم قابل فروش دوباره نیست. هیچ‌کدام **خود‌کار** بسته نمیشوند؛ تصمیم اپراتور/حسابدار + audit + reason الزامی. تا روشنشدن سرنوشت، شمش نه «فروش تمامشده» نه «موجود انبار» — حالت معلق «زیان در حال بررسی» با اثر خزانهای.</td><td>Fulfillment، Treasury، Accounting، ۸</td></tr>
<tr><td>D-78</td><td>**حل F-2 — اثبات تحویل با OTP + تفکیک نقش**</td><td>انبار‌دار فقط `handed_over` را میزند («از دست ما خارج شد»، نه «رسید»). `delivered` **فقط با OTP گیرنده** بسته می‌شود (+ اسکن سریال در تحویل حضوری)، و **توسط انبار‌دار مبدأ بسته نمی‌شود** — نقش مقصد (پیکتأیید/کارمند فروشگاه/نماینده) در `delivered_confirmed_by`. `delivery_otp_hash`+`delivery_otp_expiry` (مثل v4) به `fulfillment_tasks` برمیگردد. تا قبل از تأیید، شمش «در حال تحویل»؛ `bar.delivered_at` فقط در لحظه‌ی تأیید واقعی ست می‌شود (نه موقع handover). تفکیک وظیفه: درآورنده‌ی شمش از انبار ≠ بندنده‌ی «تحویل‌شده».</td><td>Fulfillment، ۸</td></tr>
<tr><td>D-77</td><td>**حل F-1 — fulfillment_task: شمش مشخص + trigger=درخواست تحویل**</td><td>(۱) `fulfillment_tasks` ستون `bar_id` میگیرد (به شمش تخصیص‌یافتهی D-49 اشاره میکند؛ برای چند شمش، چند ردیف). انبار‌دار **همان سریال** را برمیدارد؛ **اسکن سریال pick اجباری** و باید با `bar_id` بخواند وگرنه خطا — تضمین بستن «تخصیصدهندهی فروش» و «انبار‌دار» به یک سریال واحد. (۲) trigger ساخت task = **«درخواست تحویل»** است، نه «پرداخت سفارش». فروش امانی (`delivered_at=NULL`) **هیچ taskی نمیسازد** (شمش در خزانه قفل). فقط با درخواست تحویل مشتری یا تحویل فوری POS/فروشگاه task ساخته می‌شود (برگشت مفهوم `CustodialDeliveryRequest` v4 که در ۸ گم بود).</td><td>Fulfillment، Inventory، ۸، ۱۲.۱</td></tr>
<tr><td>D-76</td><td>**حل A-12 — تاپآپ به scope درست (ایزوله)**</td><td>`wallet_topup` بعد `wallet_scope` میگیرد؛ از **فرانت/کانال** resolve می‌شود (talamala→talamala، goldis→goldis، aminzar→**aminzar**) و کیف ریالی همان scope شارژ می‌شود. سه فرانت کاملا **ایزوله** (D-46): امینزر در goldis merge **نمی‌شود**، هرچند legal entity هر دو شرکت گلدیس و درگاه شارژش Goldis IPG است (`company_id` مشتق از scope فقط برای حسابداری). متن قدیمی ۱۲.۵.۴ که «گلدیس/امینزر → wallet Goldis» میگفت اصلاح شد. **یادآوری کلی:** هر فرانت (فعلا ۳ تا) همهچیزش — کیف، تاپآپ، بازخرید، گزارش — ایزولهٔ همان scope است.</td><td>Wallet، Payment، ۱۱.۷، ۱۲.۵.۴</td></tr>
<tr><td>D-74</td><td>**حل A-13 — نقره (XAG) خارج از scope v1**</td><td>در v1 **هیچ ورودی به نقره** نداریم: نه محصول نقره، نه قیمتگذاری/فرمول نقره، نه trade/POS/بازخرید نقره. اول کل زنجیرهی **طلا** بینقص نهایی شود؛ سپس **عینا همان روال** برای نقره تکرار می‌شود. **ساختار باید metal-generic بماند** (asset `XAG_MG`، `metal_type`، `PRECIOUS_METALS`، خزانه/قیمت به ازای فلز فقط بهعنوان نقطهی توسعه نگه داشته شوند — حذف نشوند)، ولی هیچ مسیر فعال نقره در v1 ساخته/seed/نمایش داده نشود. همه‌ی D-46…D-73 metal-genericاند و موقع افزودن نقره بدون بازطراحی اعمال میشوند.</td><td>Catalog، Pricing، Treasury، Wallet، سراسری</td></tr>
<tr><td>D-73</td><td>**مدل نهایی نماینده (تخت، بدون شبکه) + اصلاحات P۱–P۴**</td><td>**۱)** POS = فروش برند TalaMala (v1 همه TalaMala)؛ پول→TalaMala (نه نماینده)؛ هج خود‌کار با Goldis مبنای P_hedge (۶/D-69). **۲)** نماینده = فقط مکان/اپراتور (نه مالک موجودی، نه دریافتکنندهی پول). **۳)** پاداش نماینده = کمیسیون طلایی جدا از TalaMala (از حاشیه‌ی خودش)، دو نرخ: فروش و بازخرید — نه gap نردبان (A-10 حل). **۴)** جدول `dealer_commission_rates` (محصول/نوع، `dealer_tier_id` NULL=همه، `trade_side` میگیرد: `sale` یا `buyback`) → درصد طلایی؛ پیش‌فرض محصول + override سطح؛ رزولوشن مثل D-65. **۵)** مبنای درصد = `pure_gold_mg` تراکنش در لحظه‌ی فروش (Gold-for-Gold)، نه ریال. **۶)** نگهبان فروش: Σکمیسیون ≤ `P_retail−P_hedge`. **۶ب (P۲):** نگهبان بازخرید جدا: کمیسیون بازخرید ≤ اسپرد بازخرید؛ نقض → رد/هشدار اپراتور. **۷)** کمیسیون بازخرید فقط بعد از `AuthenticityVerified` (D-53)، نه قبلش. **۸ (P۱ اصلاح‌شده):** تسویه روی **`dealer_commission_ledger` جدا** (بدهی طلایی TalaMala→نماینده، Gold-for-Gold، دورهای) — **نه** روی `inter_company_ledger` (آن شرکت↔شرکت است و نماینده کاربر است؛ آلودن گزارش هجینگ ممنوع). رکورد روی `DealerSale`+`metal_profit_mg`. **۹)** `SubDealerRelation` و هر مفهوم زیرنماینده/شبکهای/MLM/ارتقا‌ی‌تیمی **از کل scope v5 حذف** (نه v1 نه v2 نه زیرساخت)؛ شبکه تخت. **۱۰ (P۴):** `P_partner`/`dealer_tier_id` (D-65) در v1 فقط **زیرساخت خالی** است — مسیر فعال «همکار برای خودش می‌خرد» نداریم؛ فعالشدن=آینده. **P۳:** کمیسیون طلایی واریزی به کیف نماینده = طلای دیجیتال جدید ⇒ یک پای خزانهای `+pure_gold_mg` میسازد و تابع سقفهای D-47 است.</td><td>Dealer، Pricing، Treasury، ۹، ۱۱.۵، ۱۲.۷، context۱۵</td></tr>
<tr><td>D-72</td><td>**حل A-9 — کارمزد معاملهی دیجیتال = مارجین نردبان + spread دو‌طرفه**</td><td>(الف) «کارمزد معاملهی دیجیتال نقشمحور v4» (`gold_fee_customer/dealer_percent`…) مفهوم جدا **نیست** — همان فاصلهی نردبان D-65 است (`P_retail−P_hedge` مشتری، `P_partner−P_hedge` همکار). افزونگی مدل v4 حذف. (ب) `channel_pricing_formulas` بعد `trade_side VARCHAR(10) NULL` میگیرد (مقادیر: `buy` یا `sell` یا `NULL`) تا **spread دو‌طرفه** ممکن شود: قیمت خرید (کاربر می‌خرد) و قیمت فروش (کاربر می‌فروشد) مارجین مستقل دارند؛ رزولوشن با همان `priority`. Invariant D-65 هر دو سمت: قیمت خرید ≥ P_hedge؛ قیمتی که به فروشنده‌ی کاربر میدهیم ≤ P_hedge (حاشیه منفی نشود). قیمت `digital_trade sell` (= همان «بازخرید دیجیتال» D-68) از فرمول `trade_side=sell` می‌آید.</td><td>Pricing، Wallet، ۱۱.۴</td></tr>
<tr><td>D-71</td><td>**حل A-8 — برچسب scope روی شمش (`sale_wallet_scope`)**</td><td>`bars` ستون `sale_wallet_scope VARCHAR(20) NULL` میگیرد: در لحظه‌ی فروش از scope سفارش (goldis/aminzar/talamala) پر و IMMUTABLE **تا زمان status=SOLD** (انتقال مالکیت — D-55 — عوضش نمیکند، چون حساب به فروش اول گره خورده). هنگام بازخرید (status برمیگردد به ASSIGNED)، `sale_wallet_scope=NULL` می‌شود تا شمش دوباره در هر scope فروخته شود (D-92). همه‌ی مسیرهای بازخرید/انتقال/گزارش تفکیکی D-46 از این برچسب تصمیم میگیرند، نه استنتاج ضمنی. شمش فروش‌نرفته=`NULL` (مالکیت شرکتی). برای کارت هدیه/مارکت‌پلیس (بدون ثبت مالکیت — D-54): `sale_wallet_scope` پر می‌شود (برای خزانه/بین‌شرکتی) ولی `customer_id=NULL` — دو بعد مستقل. **قاعده:** بازخرید آنلاین فقط در همان scope/وبسایتی که خرید انجام شده مجاز است.</td><td>Inventory، Wallet، Buyback، ۱۱.۵</td></tr>
<tr><td>D-70</td><td>**حل A-7 — تعهد بین‌شرکتی digital_trade sell غیر-Goldis**</td><td>جملهی مبهم ۱۲.۴ («Settlement: Goldis طلب از TalaMala») با مدل صریح جایگزین شد. scope غیر-Goldis: جفت تازهی مخالف فروش → `TalaMala→Goldis طلا amount_mg` + `Goldis→TalaMala ریال P_hedge_per_mg×amount_mg`. scope=Goldis: هیچ تعهد بین‌شرکتی، فقط خزانه‌ی `−` تک‌پایی `digital_sell` (D-67). آینهٔ دقیق ۱۲.۳/D-69 و همان مسیر یکتای D-68. مابه‌التفاوت (P_hedge − پرداختی به کاربر) حاشیه‌ی scope فروشنده.</td><td>Inter-Company، Treasury، ۱۲.۴</td></tr>
<tr><td>D-69</td><td>**حل A-6 — یکدستی digital_trade buy غیر-Goldis با ۱۲.۱**</td><td>۱۲.۳ اصلاح: مبنای تعهد بین‌شرکتی خرید دیجیتال scope غیر-Goldis = **`P_hedge_per_mg × amount_mg`** (D-65)، نه `internal_base_price` و نه قیمتی که کاربر پرداخت. صریح: خرید دیجیتال scope غیر-Goldis از نظر خزانه/بین‌شرکتی **همسنگ فروش فیزیکی غیر-Goldis** است (همان مدل ۱۲.۱)؛ تنها تفاوت: شمش/اجرت ندارد و خزانهاش تک‌پایی `digital_buy` است (D-67). مابه‌التفاوت (قیمت کاربر − P_hedge) سود scope فروشنده. ۱۲.۲ (AminZar، Goldis-side) بدون تعهد بین‌شرکتی — تأیید شد.</td><td>Inter-Company، Treasury، ۱۲.۲، ۱۲.۳</td></tr>
<tr><td>D-68</td><td>**حل A-5 — یکیسازی digital_buyback با digital_trade sell**</td><td>«بازخرید دیجیتال» یک مسیر فنی جدا **نیست** — صرفا همان **`digital_trade` با `trade_side=sell`** است (نام بازاریابی). زیرflow (c) `digital_buyback` **حذف** می‌شود. در نتیجه Buyback فقط **۲ حالت** دارد (نه ۳): تحویل‌نشده + حضوری — هر دو مرتبط با شمش فیزیکی (D-58/D-59). منسوخها: `order_type=buyback` فقط برای فیزیکی؛ endpointهای `/buyback/quote` و `/buyback/digital` حذف → استفاده از `/wallet/trades/sell`؛ رویداد `DigitalBuybackCompleted` حذف = `DigitalGoldSold`؛ در ۵.۲ مدخل `digital_buyback` صرفا **مترادف `digital_sell`** است؛ بند «(c)» در D-32/۱۲.۵.۲/Q-03/roadmap منسوخ. قیمت فروش دیجیتال از نردبان D-65 سمت فروش می‌آید (همان نقشی که `buyback_quote` ادعا میکرد).</td><td>Order، Wallet، Treasury، ۵.۲، ۱۲.۴، ۱۲.۵.۲، ۱۳، ۱۴</td></tr>
<tr><td>D-67</td><td>**حل A-4 — بازنویسی ۵.۲ به مدل تک‌پایی/دوپایی**</td><td>`treasury_positions` per **پای** ثبت می‌شود نه per تراکنش؛ علامت از پای می‌آید نه `source_type`. تک‌پایی: `+`=`order_physical`/`pos_sale`/`marketplace_sale`/`digital_buy`؛ `−`=`hedge_buy`/`digital_sell`/`digital_buyback`. دوپایی (net≈صفر): `buyback` تحویل‌نشده/حضوری (D-59) و `physical_purchase_from_wallet` (D-66). برچسب ثابت `−` برای `buyback`/`physical_purchase_from_wallet` در ۵.۲ قدیمی **همان باگ تک‌پایی** بود که پیاده‌ساز به آن استناد میکرد.</td><td>Treasury، ۵.۲</td></tr>
<tr><td>D-66</td><td>**حل A-3 — physical_purchase_from_wallet دوپایی** (آینهٔ D-59)</td><td>خرید کالای فیزیکی با کیف = تبدیل digital→physical. دو پای مستقل: پای۱ `−gold_part_mg` (مصرف طلای دیجیتال کیف)، پای۲ `+pure_gold_mg` (خروج شمش فیزیکی = فروش فیزیکی). **خزانه‌ی خالص** = `−gold_part_mg + pure_gold_mg = −wage_gold_mg` (if `gold_part_mg = pure_gold_mg + wage_gold_mg`). اگر wage به‌صورت طلا refund شود، net=صفر؛ درغیر صورت net=−wage_gold_mg (هزینهای به treasury). اگر فروش غیر-Goldis بود، تعهد بین‌شرکتی پای۲ مثل هر فروش فیزیکی با مبنای P_hedge (D-65). متن ۱۲.۵ که فقط `delta=-gold_part_mg` داشت **باگ** بود (شمش هجنشده از سیستم خارج و exposure گم میشد).</td><td>Treasury، Inter-Company، ۱۲.۵</td></tr>
<tr><td>D-59</td><td>**حل Q-05 — بازخرید فروش را معکوس نمیکند**</td><td>بازخرید **هرگز** تعهدهای بین‌شرکتی فروش اصلی را معکوس نمیکند (`reverses_ledger_id` برای فروش استفاده نمی‌شود). هر بازخرید **دو پای مستقل** دارد: پای۱ طلا به کیف کاربر (+pure_gold_mg)، پای۲ منبع (شمش فیزیکی برمیگردد یا طلای کیف مصرف می‌شود، −pure_gold_mg). نتیجه: **تحویل‌نشده/حضوری = تبدیل physical↔digital ⇒ خزانه ≈ صفر، هیچ جفت تعهد طلایی تازهای، فقط `buyback_credit_rial` بهعنوان هزینهی ریالی ثبت می‌شود. دیجیتال = خروج واقعی طلا ⇒ خزانه −pure_gold_mg + یک جفت تعهد تازهی مخالف (TalaMala→Goldis طلا، Goldis→TalaMala ریال) به قیمت خام لحظه‌ی بازخرید.** این، باگ ضمنی «buyback → −pure_gold_mg» در ۵.۲/۱۲.۵.۲ را برای حالتهای فیزیکی/تحویل‌نشده تصحیح میکند (دوبار-حساب). جزئیات گردکردن/منبعقیمت به فاز پیاده‌سازی.</td><td>Inter-Company، Treasury، ۵.۲، ۱۲.۵.۲</td></tr>
<tr><td>D-81</td><td>**P0-1.1 — اصلاح wallet_topups idempotency constraint**</td><td>`wallet_topups` UNIQUE constraint نادرست بود: `UNIQUE (company_id, idempotency_key)`. دلیل نادرستی: scope aminzar و scope goldis هر دو به شرکت گلدیس نقشه میشوند (legal entity یکسان)؛ اگر دو کاربر از scopes متفاوت با idempotency_key یکسان شارژ کنند، یکی reject می‌شود (نادرست). **اصلاح:** `UNIQUE (wallet_scope, user_id, idempotency_key)` — هر کاربر در هر scope یک فضای idempotency جدا دارد.</td><td>Wallet، P0-1.1</td></tr>
<tr><td>D-82</td><td>**P0-7 — Hedge Buy flow (خرید طلای خام از بازار)**</td><td>Goldis Central Hedging Desk در پاسخ به فروشهای غیر-Goldis (scope=TalaMala یا aminzar)، طلای خام از بازار می‌خرد و دورهای تحویل می‌دهد. این flow با bulk_gold_inventory (P0-8) و inter-company settlement مرتبط است. **موارد:** ۱) API `/admin/treasury/hedge-buy/request` برای تسجیل خرید. ۲) وزن و پرایس ثبت می‌شود. ۳) Treasury exposure نسبت به سقفهای D-47 چک می‌شود. ۴) Settlement دورهای: operator تحویل طلا به creditor company را آپروو میکند. ۵) هر settlement یک inter_company_ledger entry میسازد (`source_type='hedge_buy_settlement'`).</td><td>Treasury، Inventory، Inter-Company، ۱۲.۵.۳ الف، D-47</td></tr>
<tr><td>D-83</td><td>**P0-8 — Bulk Gold Inventory (طلای خام بی‌سریال)**</td><td>جداول جدید برای ذخیرهی طلای خام (granules، ingots، سقط scrap) که سریالدار نیستند و به صورت وزن (mg) ثبت میشوند. **موارد:** ۱) `bulk_gold_inventory`: مالکیت، موقعیت، وزن کل، عیار، منبع (hedge_buy، supplier_purchase، etc.). ۲) `bulk_gold_movements`: ledger حرکات وزن (intake، withdrawal، conversion، recount). ۳) با `bars` table هیچ تضادی ندارد: bar برای شمش سریالدار است؛ bulk برای خام است.</td><td>Inventory، ۱۱.۵، D-82 related</td></tr>
<tr><td>D-84</td><td>**P0-9 — Commission gold exposure offset (dealer commission settlement)**</td><td>وقتی نماینده commission طلایی (gold-for-gold) TalaMala دریافت میکند (wallet deposit XAU_MG)، یک پای خزانهای +pure_gold_mg میسازد (dealer حالا طلا دارد، exposure افزا‌یش یافت). **این باید offset شود** اگر commission از منبع TalaMala بود: یک inter_company_ledger entry ریاضیای بین TalaMala و Goldis قدیمیترین hedge obligation را میپوشاند (TalaMala debt←Goldis، gold credit←Goldis). **علت:** اگر offset نباشد، TalaMala طلا داده (treasury −) ولی مقابلرقم (hedged liability) قید نشده (mismatch). شامل D-73، D-82 (Hedge Buy)، و inter-company settlement logic.</td><td>Treasury، Dealer، Inter-Company، D-73 P۳، D-82</td></tr>
<tr><td>D-90</td><td>**علامت delta در hedge_buy**</td><td>در flow `/admin/treasury/hedge-buy/request`، `Treasury.record(source=hedge_buy, delta)` باید **منفی** باشد (−amount_mg)، نه مثبت. دلیل: hedge_buy exposure را **کاهش** می‌دهد (خزانه را تقویت میکند). علامت مثبت باعث می‌شود exposure دوبرابر شود و فروشهای جدید قفل شوند.</td><td>Treasury، ۱۲.۵.۳ الف</td></tr>
<tr><td>D-91</td><td>**pure_gold_mg در تمام Treasury.record calls**</td><td>در فروشهای فیزیکی (۱۲.۱/POS/Marketplace/فیزیکی از wallet)، `Treasury.record(delta=+weight_mg)` نادرست است. صحیح: `delta=+pure_gold_mg = weight × purity / 1000`. دلیل: hedging مبنای exposure روی `pure_gold_mg` است، نه وزن خام. عدم رعایت این قاعده باعث عدم تطابق exposure با تعهدات واقعی و ریسک مالی شدید می‌شود.</td><td>Treasury، ۱۲.۱، ۱۲.۷، ۱۲.۸</td></tr>
<tr><td>D-92</td><td>**sale_wallet_scope نباید برای همیشه IMMUTABLE باشد**</td><td>طبق D-71، `sale_wallet_scope` IMMUTABLE تعریف شده بود. اما وقتی شمش به وسیله بازخرید برمیگردد به تالار (status=ASSIGNED, customer_id=NULL)، این فیلد باید NULL شود تا شمش در هر scope دوباره فروخته شود. بدون این، cross-scope resale ممکن نیست و contradiction ایجاد می‌شود.</td><td>Inventory، Buyback، D-71</td></tr>
<tr><td>D-93</td><td>**API برای D-62 (two-stage inventory transfer)**</td><td>جداول `inventory_transfer_documents` و `items` وجود دارند اما هیچ endpoint برای create/dispatch/receive/complete معرفی نشده. بدون این API، انبار‌داران نمی‌توانند از فرایند استفاده کنند. ✅ **اصلاح v2.7**: 8 endpoint در ۱۳ اضافه شد: `POST /admin/inventory/transfers`, `GET .../transfers`, `GET .../transfers/{id}`, `POST .../dispatch`, `POST .../receive`, `POST .../confirm`, `POST .../discrepancy`, `POST .../cancel`.</td><td>Inventory، ۱۲، ۱۳</td></tr>
<tr><td>D-94</td><td>**جدول dealer_sales گمشده**</td><td>`dealer_commission_ledger` FK به `dealer_sale_id` دارد اما این جدول تعریف نشده است. لازم: جدول `dealer_sales` با فیلدهای اصلی (id, dealer_user_id, order_id, bar_id, pure_gold_mg, sale_type).</td><td>Dealer، Schema</td></tr>
<tr><td>D-95</td><td>**Hedge Buy و Dealer Commission Offset در Roadmap نیستند**</td><td>فازهای ۲۱ پیاده‌سازی هیچ اشاره‌ای به این دو قابلیت حیاتی ندارند. Hedge Buy برای Treasury ضروری و Offset برای جلوگیری از نشت مالی لازم است. لازم: Hedge Buy در فاز ۳ و Commission Offset در فاز ۴.</td><td>Roadmap، D-82، D-84</td></tr>
</tbody>
</table>

> **⚠️ اثر روی scope/تخمین:** D-47، D-48 و D-53 scope را سنگینتر کردهاند (supplier_purchase داخل؛ سقف دو‌طرفه؛ گیت ثبت مالکیت). D-58/D-59 و حذف SubDealer/MLM (D-73) برعکس **سادهتر** کردهاند. **هشدار P۵:** زیرسیستم **قیمت(D-65/72) + دفترکل(۶) + خزانه(D-47/67) + نماینده(D-73)** الان سنگین‌ترین و پرریسک‌ترین بخش پروژه است (باگ = ضرر مالی مستقیم). توصیه: در پیاده‌سازی **اول یک پروتوتایپ end-to-end از همین زنجیره با تستهای پولی واقعی** ساخته شود، نه CRUDهای ساده. تخمین ۱۲ هفتهی بخش ۲۲ دیگر واقع‌بینانه نیست و باید بازبینی شود.

## ۲.۶. اصلاحات P0 — Schema Implementation Fixes (نسخه ۲.۳)

### ۲.۶.۱ اصلاحات P0 در v2.2 (بازبینی ChatGPT + DeepSeek اول)

<table>
<thead>
<tr><th>Fix</th><th>موضوع</th><th>اصلاح</th></tr>
</thead>
<tbody>
<tr><td>P0-1</td><td>wallet_scope missing from ledger/locks</td><td>`wallet_ledger_entries` و `wallet_locks` ستون `wallet_scope VARCHAR(20)` اضافه شدند. UNIQUE constraint هم scope-keyed: `UNIQUE (wallet_scope, user_id, idempotency_key)` (۴.۳)</td></tr>
<tr><td>P0-2</td><td>payments.order_id NOT NULL but topup has no order</td><td>`payments.order_id` را `NULLABLE` کردیم (برای topup payments که order ندارند) (۱۱.۷)</td></tr>
<tr><td>P0-3</td><td>sales_channels missing seller/payment receiver columns</td><td>`seller_company_id` و `payment_receiver_company_id` به `sales_channels` اضافه شدند (۳.۲) — D-56 marketplace override require میکند</td></tr>
<tr><td>P0-4</td><td>physical_purchase_from_wallet calculates with product.weight_mg not pure_gold_mg</td><td>محاسبهٔ treasury و wallet lock از `pure_gold_mg = weight × (purity / 1000)` استفاده میکند، نه `weight_mg` مستقیم (۱۲.۵ گام ۳) — purity factor الزامی برای درستی</td></tr>
<tr><td>P0-5</td><td>treasury concurrency: no SELECT FOR UPDATE lock</td><td>توضیح اضافه شد (۱۲.۱۰ و context service layer): checkpoint validation و `SELECT ... FOR UPDATE` درون transaction checking (implementation detail)</td></tr>
<tr><td>P0-6</td><td>inter_company_ledger creation دقیقتر شد</td><td>۶.۴: هر فروش غیر-Goldis دقیقا دو ردیف ledger (rial+gold) میسازد، ایجاد شده در سمت یک transaction (بدون دوبارشماری)</td></tr>
</tbody>
</table>

### ۲.۶.۲ اصلاحات P0 در v2.3 (بازبینی DeepSeek دوم — 2026-05-18)

<table>
<thead>
<tr><th>Fix</th><th>موضوع</th><th>اصلاح</th></tr>
</thead>
<tbody>
<tr><td>P0-1.1</td><td>wallet_topups idempotency scope bug</td><td>`wallet_topups` ستون UNIQUE constraint تغییر: `UNIQUE (company_id, idempotency_key)` ❌ → `UNIQUE (wallet_scope, user_id, idempotency_key)` ✅. دلیل: goldis+aminzar هر دو شرکت گلدیس دارند؛ تنها wallet_scope+user_id+key می‌تواند idempotency را تضمین کند (۱۱.۸)</td></tr>
<tr><td>P0-7</td><td>Hedge Buy flow missing entirely</td><td>بخش ۱۲.۵.۳ (الف. Hedge Buy — خرید طلای خام از بازار (P0-7)) الف اضافه شد: Hedge Buy جریان خرید طلای خام از بازار برای پوشش تعهد بین‌شرکتی. API، state، settlement دورهای توثیق شد.</td></tr>
<tr><td>P0-8</td><td>Bulk Gold Inventory model missing</td><td>دو جدول جدید اضافه: `bulk_gold_inventory` (ذخیرهی طلای خام بی‌سریال) و `bulk_gold_movements` (ledger حرکات). محل: بعد از `inventory_movements` در ۱۱.۵</td></tr>
<tr><td>P0-9</td><td>Commission gold creates exposure without inter-company offset</td><td>توضیح اضافه در D-73 و جریان Hedge Buy: وقتی commission طلایی dealer settled شود (deposit به کیف dealer XAU_MG)، یک پای exposure +pure_gold_mg میسازد. این **باید** با inter_company_ledger entry offset شود اگر commission در TalaMala settled شود (D-73 P۳)</td></tr>
</tbody>
</table>

### ۲.۶.۳ اصلاحات BLOCKER/HIGH در v2.4 (نهاییسازی implementation-safe — 2026-05-18)

> بعد از بررسی عمیق، **۸ ابهام/contradiction باقی مانده** که implementation را غلط راهنمایی میکرد.

<table>
<thead>
<tr><th>Fix</th><th>موضوع</th><th>اصلاح</th></tr>
</thead>
<tbody>
<tr><td>FIX-1</td><td>**BLOCKER:** Duplicate inter-company ledger entry در 12.1</td><td>**مشکل:** Step 4e (checkout) و step 7 (mark_paid) هر دو inter_company_ledger میساختند → دوبارشماری. **اصلاح:** Step 4e کامل حذف شد. فقط step 7 (mark_paid/PaymentVerified) ledger میسازد. اضافه: توضیح "⚠️ فقط بعد از تأیید پرداخت، نه موقع checkout" در 6.4 و 12.1 (P0-6 override)</td></tr>
<tr><td>FIX-2A</td><td>**BLOCKER:** Marketplace contradiction — diagram 3.1 line 278</td><td>**مشکل:** `talamala_digikala payee=TalaMala` (غلط، D-56 می‌گوید Goldis). **اصلاح:** تغییر به `payee=Goldis` + annotation "D-56: marketplace همیشه Goldis"</td></tr>
<tr><td>FIX-2B</td><td>**BLOCKER:** Marketplace contradiction — 12.8 comment lines 2222-2226</td><td>**مشکل:** Comment میگفت "اگر brand=TalaMala، TalaMala inter_company_ledger دریافت میکند" (نادرست، D-56 منع میکند). **اصلاح:** Comment حذف. جایگزین: "D-56: marketplace همیشه seller=Goldis، payment_receiver=Goldis؛ هیچ inter_company_ledger entry نیست"</td></tr>
<tr><td>FIX-2C</td><td>**BLOCKER:** Marketplace Note — بعد از 12.8 flow</td><td>**اضافه:** صریح note "⚠️ D-56 (قطعی): هیچ inter-company entry در marketplace نیست. پول به Goldis. TalaMala marketplace income مستقیم ندارد."</td></tr>
<tr><td>FIX-3</td><td>**BLOCKER:** Supplier purchase contradiction 7.3 line 821</td><td>**مشکل:** "هیچ ledger entry — supplier purchase خارج از scope" (نادرست، D-48 می‌گوید داخل). **اصلاح:** جایگزین با صریح: inter_company_ledger entry ثبت شود (source_type='supplier_purchase') از Goldis→AminZar + توضیح wage_gold_mg</td></tr>
<tr><td>FIX-4</td><td>**BLOCKER:** Mensoukh API endpoints در 13</td><td>**مشکل:** `/orders/{id}/cancel` و `/orders/{order_id}/cancel-before-delivery` هنوز فهرست شده (D-58: cancel منسوخ). Buyback header "۳ زیرflow" (نادرست: فقط ۲ — تحویل‌نشده و حضوری). **اصلاح:** ۱) endpoint cancel حذف. ۲) endpoint cancel-before-delivery حذف. ۳) header به "۲ حالت" تغییر (D-58). ۴) labels (a)/(b) renumber. ۵) (c) digital_buyback = /wallet/trades/sell annotation</td></tr>
<tr><td>FIX-5</td><td>**HIGH:** Wallet API company_code vs wallet_scope</td><td>**مشکل:** `/wallet/balances?company_code=X` و `/wallet/ledger?company_code=X` (D-46 violation: scope نه company_code). **اصلاح:** تمام `company_code` → `wallet_scope` (۳ جا در 13). اضافه: `locked_balance` و `credit_balance` فیلدها به response</td></tr>
<tr><td>FIX-6</td><td>**HIGH:** D-62 schema missing from 11.9</td><td>**مشکل:** D-62 تصمیم دو‌مرحله‌ای انتقال تولید شده (DRAFT→DISPATCHED→RECEIVED→COMPLETED) ولی جدول ندارد. **اصافه:** `inventory_transfer_documents` و `inventory_transfer_items` tables + all fields (reference_code, status enum, OTP, locations, movements) + indexes</td></tr>
<tr><td>FIX-7</td><td>**HIGH:** bars.status insufficient enum برای D-79</td><td>**مشکل:** `bars.status` فقط ۴ مقدار (`RAW`، `ASSIGNED`، `RESERVED`، `SOLD`) دارد اما D-79 نیاز به موارد اضافی دارد: `DAMAGED`, `LOST`, `IN_INSPECTION`. **اصلاح:** Enum توسیع + مستند: DAMAGED (پلمب‌شکسته)، LOST (رویداد زیان)، IN_INSPECTION (بازرسی بازخرید/آسیب)</td></tr>
</tbody>
</table>

### ۲.۶.۴ Decision Log Entries v2.4

<table>
<thead>
<tr><th>ID</th><th>تصمیم</th><th>تاثیر</th></tr>
</thead>
<tbody>
<tr><td>D-85</td><td>inter_company_ledger **فقط** در PaymentVerified — نه checkout</td><td>P0-6 fix برای 12.1: تمام فروش غیر-Goldis دقیقا یک بار ledger میسازند (یقینی‌سازی دوبارشماری). atomic transaction: checkout→payment→mark_paid.</td></tr>
<tr><td>D-86</td><td>Marketplace = Goldis-exclusive (D-56 قطعی)</td><td>D-56 در تمام جاها (diagram، comments، note) apply شد. هیچ TalaMala marketplace income. منطق: Goldis infrastructure/payment منیجر = حق انحصار</td></tr>
<tr><td>D-87</td><td>Supplier purchase ledger at intake (D-48 override)</td><td>7.3 اصلاح: inter_company_ledger ✅ (نه ❌). debtor=Goldis, creditor=AminZar, amount=pure+wage_mg. هدف: Goldis↔AminZar obligation tracking از محل تولید</td></tr>
<tr><td>D-88</td><td>bars.status enum extended (D-79 support)</td><td>DAMAGED, LOST, IN_INSPECTION اضافه شدند تا edge cases پوشش داده شوند (damaged goods, loss tracking, buyback inspection)</td></tr>
<tr><td>D-89</td><td>D-62 Two-stage transfer schema</td><td>جداول `inventory_transfer_documents` و `inventory_transfer_items` برای دو‌مرحله‌ای انتقالِ بین‌انبار. وضعیت‌ها: DRAFT → DISPATCHED → RECEIVED → COMPLETED (یا DISCREPANCY در صورت عدم تطابق). شامل OTP، حسابرسی و مکان مجازی در‌حال‌انتقال (virtual in-transit location) برای توزیع نمایندگان</td></tr>
<tr><td>D-96</td><td>**Price Lock Reconciliation** — قفل قیمت ۵دقیقهای</td><td>بین checkout و پرداخت اگر قیمت تغییر کند (شبکه/تأخیر)، سیستم پول را تو خلأ نندازد. **راهحل:** `payment_reconciliations` جدول → تطابق خود‌کار ±۲٪، treasury rebalancing، manual dashboard برای admin.</td></tr>
<tr><td>D-97</td><td>**Pending Reserves** — رزرو طلا بر روی checkout</td><td>سقف خزانه (treasury exposure cap) در checkout checkedشود، سپس در submit order رزرو شود. دو customer همزمان هم نتوانند سقف را نقض کنند. **راهحل:** `inventory_pending_holds` جدول → reserve on checkout، finalize on payment.</td></tr>
<tr><td>D-98</td><td>**Payment State Machine** — منع پول یتیم</td><td>اگر سیستم بعد از gateway verification crash کند، دوباره مدار شود. **راهحل:** `payment_states` enum = `verified_pending` (state جدید) → recovery job on startup replays. idempotency + alerts.</td></tr>
<tr><td>D-99</td><td>**POS Offline Queue** — دستگاههای بدون اینترنت</td><td>اگر WiFi قطع شود، `/api/pos/confirm` موفق نشود. **راهحل:** Local SQLite queue on POS device → `payment_pending_queue` جدول on server → retry with `request_id` idempotency.</td></tr>
</tbody>
</table>

---

## ۳. مدل Companies / Brands / Channels

### ۳.۱. ساختار

```
                ┌─────────────────────────────────────────────────────┐
                │   Operator: شرکت گلدیس                              │
                │   (یک admin panel، یک تیم ops، یک پروژه backend)     │
                └─────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
   ┌────▼────┐                    ┌────▼────┐                    ┌────▼────┐
   │ Brand:  │                    │ Brand:  │                    │ Brand:  │
   │ Goldis  │                    │ AminZar │                    │TalaMala │
   │         │                    │         │                    │         │
   │ owner:  │                    │ owner:  │                    │ owner:  │
   │ Goldis  │                    │ AminZar │                    │TalaMala │
   │         │                    │   Co.   │                    │   Co.   │
   │         │                    │         │                    │         │
   │ payee:  │                    │ payee:  │                    │ payee:  │
   │ Goldis  │                    │ Goldis  │                    │TalaMala │
   │         │                    │         │                    │   Co.   │
   └────┬────┘                    └────┬────┘                    └────┬────┘
        │                              │                              │
        │   ┌──────────────────────────┼──────────────────────────┐   │
        │   │                          │                          │   │
   ┌────▼───▼──┐         ┌─────────────▼─────────────┐    ┌───────▼───▼─────┐
   │ Channel:  │         │ Channel:                  │    │ Channel:        │
   │ goldis.ir │         │ aminzar.ir                │    │ talamala.ir     │
   │           │         │                           │    │                 │
   │ type:web  │         │ type:web                  │    │ type:web        │
   │ pay:Goldis│         │ pay:Goldis                │    │ pay:TalaMala    │
   │   IPG     │         │   IPG                     │    │   IPG           │
   └───────────┘         └───────────────────────────┘    └─────────────────┘
   
   Channels دیگر:
   • goldis_digikala (brand=Goldis, type=marketplace, payee=Goldis)
   • talamala_digikala (brand=TalaMala, type=marketplace, payee=Goldis)   # D-56: marketplace همیشه Goldis
   • goldis_dealer_pos_X (brand=Goldis, type=pos, payee=Goldis)
   • talamala_pos_Y (brand=TalaMala, type=pos, payee=TalaMala)
   • admin_panel (channel for admin operations — virtual)
```

### ۳.۲. مدل داده

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

### ۳.۳. تشخیص brand/channel در API

- Storefront frontend ها → **domain → channel lookup** (server-side) + هدر `X-Channel-Code` بهعنوان fallback
- Admin panel → کاربر در پنل، brand/channel را explicit انتخاب میکند (با permission)
- POS app → `terminal_id` + `device_id` در JWT claim → resolve به یک خاص `sales_channel`
- ⚠️ **هیچ frontend نمی‌تواند brand_id را آزاد در body بفرستد** — همیشه از channel resolution می‌آید

---

## ۴. مدل Wallet (Per-wallet-scope)

> هر کاربر **سه کیف کاملا ایزوله** دارد، با کلید `wallet_scope`. `company_id` فقط مشتق و برای حسابداری است.

### ۴.۱. ساختار

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

### ۴.۲. قواعد (D-46)

- کلید کیف = **`wallet_scope`** (goldis|aminzar|talamala)، نه legal_entity. `company_id` فقط مشتق و برای حسابداری/inter-company نگه داشته می‌شود.
- هر scope **فقط در همان scope/برند قابل خرج** است (TalaMala→talamala، Goldis→goldis، AminZar→**aminzar**).
- **هر سه کاملا ایزوله — هیچ transfer مستقیم بین هیچ‌کدام** (حتی goldis↔aminzar که حقوقا یک شرکتاند). برای جابهجایی: فروش به ریال → برداشت → شارژ مجدد.
- **AminZar در Goldis merge نمی‌شود** هرچند legal entity هر دو شرکت گلدیس و درگاه AminZar همان Goldis IPG است.
- **UX (D-40):** Frontend هر برند فقط scope خودش را «موجودی شما» نشان می‌دهد (نام scope/شرکت پنهان). در admin panel هر سه scope در تبهای جدا، با **تفکیک گزارشی بدهی aminzar از goldis** (الزام D-46).

### ۴.۳. مدل داده

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

### ۴.۴. تعامل با Treasury و Inter-Company Ledger

- وقتی کاربر طلای دیجیتال می‌خرد در برند طلاملا (سمت دیجیتال هم مثل فروش فیزیکی هست):
  - پول → حساب TalaMala (payment_account TalaMala IPG)
  - Wallet TalaMala (XAU_MG) کاربر `+amount_mg`
  - **Goldis Treasury** position `+amount_mg` (open exposure برای Goldis)
  - **Inter-company hedging entries (دو ردیف):**
    - `inter_company_ledger`: TalaMala → Goldis، rial، به اندازه‌ی `raw_gold_price × amount_mg`
    - `inter_company_ledger`: Goldis → TalaMala، gold، `amount_mg`
- مدل ledger real-time است (بخش ۶)؛ تسویه دستی توسط اپراتور Goldis

---

## ۵. Treasury مرکزی Goldis (Central Hedging Desk)

### ۵.۱. مفهوم

- **یک Treasury** برای کل پلتفرم — managed by شرکت گلدیس
- نقش Treasury: ثبت **open exposure** Goldis در بازار طلا
- هر فروش طلا (در هر brand، هر channel) → exposure Goldis بالا (چون Goldis بدهی طلا به فروشنده یا مشتری پیدا میکند)
- Goldis از بازار خام می‌خرد (`hedge_buy`) → exposure پایین
- Digital gold inventory ≠ جدول جدا. این **همان Treasury** است.

### ۵.۲. Sign convention (explicit)

> `treasury_positions` **per پای** ثبت می‌شود، نه per تراکنش. علامت از **پای** می‌آید نه از `source_type`. بعضی تراکنشها تک‌پاییاند (علامت ثابت)، بعضی دوپایی (یک `+` و یک `−`، خالص ≈ صفر).
>
> `treasury_positions.delta_amount_mg` بر اساس نگاه **Goldis**:
>
> **تراکنش‌های تک‌پایی (علامت ثابت):**
> - + (exposure باز — Goldis بدهکار طلا شد): `order_physical`، `pos_sale`، `marketplace_sale`، `digital_buy` (در هر brand، شامل فروشهای خود Goldis — چون Goldis باید خام بخرد)
> - − (exposure بسته): `hedge_buy`، `digital_sell` (فروش طلای دیجیتال — «بازخرید دیجیتال» همین است)
>
> **تراکنش‌های دوپایی (net ≈ صفر):**
> - `buyback` تحویل‌نشده/حضوری: پای `+pure_gold_mg` (طلا به کیف) و پای `−pure_gold_mg` (شمش برگشتی/مصرف) ⇒ خنثی
> - `physical_purchase_from_wallet`: پای `−gold_part_mg` (مصرف طلای دیجیتال کیف) و پای `+pure_gold_mg` (خروج شمش فیزیکی) ⇒ خنثی
>
> sum(delta_amount_mg WHERE status IN ('open','partially_covered')) = current open exposure

### ۵.۳. Cap و alert (دو‌طرفه + چک inline)

- **سقف دو‌طرفه به ازای هر فلز:** `max_open_exposure_mg` (سمت فروش، exposure مثبت) + `max_short_exposure_mg` (سمت خرید/بازخرید، exposure منفی). هر دو اپراتور-تنظیم، با audit.
- **چک inline سد سخت در لحظه‌ی هر تراکنش** (فروش+خرید، فیزیکی+دیجیتال+POS، بدون استثنا): اگر این تراکنش از سقف مربوطه رد شود، **همان تراکنش رد می‌شود** (مثل `require_fresh_price`).
- `warning_threshold_percent` (مثلا ۷۰٪) برای هر دو طرف.
- `auto_block_at_cap`: worker (۱۲.۱۰) فقط **هشدار/پشتیبان** است؛ سد واقعی همان چک inline است.

### ۵.۴. مدل داده

```sql
CREATE TABLE treasury_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metal_type VARCHAR(20) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    -- order_physical | digital_buy | digital_sell | marketplace_sale
    -- pos_sale | physical_purchase_from_wallet | buyback
    -- hedge_buy | hedge_sell | manual_adjustment
    -- (gold withdrawal حذف شد — D-31. hedging merge شد در Treasury — D-42)
    source_id VARCHAR(100) NULL,
    sales_channel_id BIGINT NULL REFERENCES sales_channels(id),
    triggered_by_brand_id BIGINT NULL REFERENCES brands(id),
    delta_amount_mg BIGINT NOT NULL,
    metal_price_per_gram_rial NUMERIC(20, 2) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    -- open | partially_covered | covered | cancelled
    covered_amount_mg BIGINT NOT NULL DEFAULT 0,
    note TEXT NULL,
    metadata JSONB NULL,
    actor_id BIGINT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    covered_at TIMESTAMPTZ NULL
);
CREATE INDEX ix_treasury_metal_status ON treasury_positions (metal_type, status);

CREATE TABLE treasury_settings (
    metal_type VARCHAR(20) PRIMARY KEY,
    max_open_exposure_mg BIGINT NOT NULL,    -- D-47: سقف سمت فروش (exposure مثبت)
    max_short_exposure_mg BIGINT NOT NULL,   -- D-47: سقف سمت خرید/بازخرید (exposure منفی)
    warning_threshold_percent NUMERIC(5, 2) NOT NULL DEFAULT 70.0,
    auto_block_at_cap BOOLEAN NOT NULL DEFAULT TRUE
);
-- D-47: علاوه بر worker ۳۰s، چک inline سد سخت در لحظه‌ی هر تراکنش (فروش+خرید،
-- همه‌ی کانالها بدون استثنا). هر دو سقف per فلز قابل تغییر لحظهای اپراتور با audit.

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

## ۶. Inter-Company Ledger — مدل Hedging مرکزی (Context حیاتی)

### ۶.۱. مفهوم — Goldis بهعنوان Central Hedging Desk

این context **انحصارا مسئول است** برای track و settle obligations بین شرکتها (Goldis ↔ TalaMala، Goldis ↔ AminZar، در آینده Goldis ↔ موارد دیگر).

**مدل کسب‌و‌کار (D-06b):**

اصل اساسی بازار طلا: **هر کسی طلا بفروشد، باید بلافاصله معادل وزن خام آن طلا را از بازار بخرد** — وگرنه با بالا رفتن قیمت ضرر میکند (open exposure). این کار را hedging میگویند.

در پلتفرم ما، **Goldis نقش Central Hedging Desk** را برای همه‌ی برندها بازی میکند. یعنی هر فروشگاهی (TalaMala، AminZar، یا حتی خود Goldis) که شمش می‌فروشد، **به‌صورت اتوماتیک از Goldis طلای خام معادل آن را می‌خرد**، و Goldis مسئول است که از بازار خام تهیه کند و دورهای فیزیکی به آن فروشنده تحویل دهد.

> **مالکیت شمشها قبل از فروش:** شمشهایی که هماکنون در انبار / فروشگاه / POS هر برند هستند، **مال خود همان برند** هستند (قبلا خریداری/تولید شده‌اند). این **مدل consignment نیست** — هیچ مالکیت معلق وجود ندارد. مدل تأمین و توزیع شمشها (چرخه‌ی تولید) در بخش بعدی توضیح داده می‌شود؛ این بخش فقط **سمت فروش و hedging** را پوشش می‌دهد.

**وقتی هر فروشگاه (مثلا TalaMala) یک شمش می‌فروشد:**

- پول مشتری می‌رود به حساب TalaMala (مثلا ۵۲۰M ریال) — کل سود فروش (اجرت + مالیات) نزد TalaMala میماند
- شمش از انبار TalaMala خارج می‌شود — این یک کاهش سادهٔ inventory برای TalaMala است (مالکیت با خودش بود)
- **همزمان یک تراکنش hedging اتوماتیک شکل میگیرد**: TalaMala از Goldis معادل وزن خام طلا را به قیمت طلای خام در همان لحظه «خریده»

این **دو obligation همزمان** در `inter_company_ledger` ثبت میکند:

<table>
<thead>
<tr><th>Direction</th><th>Asset</th><th>Amount</th><th>معنی</th></tr>
</thead>
<tbody>
<tr><td>`TalaMala → Goldis`</td><td>ریال</td><td>`raw_gold_price_per_mg × weight_mg`</td><td>TalaMala باید بهای معادل وزن خام را به Goldis بپردازد (تسویه روزانه)</td></tr>
<tr><td>`Goldis → TalaMala`</td><td>gold خام (mg)</td><td>`weight_mg`</td><td>Goldis باید معادل وزن خام طلا را فیزیکی به TalaMala تحویل دهد (تسویه دورهای)</td></tr>
</tbody>
</table>

**سود فروش نزد TalaMala میماند.** Goldis فقط بهای طلای خام را میگیرد و طلای خام را تحویل می‌دهد — هیچ profit share نیست (D-39).

**نکتهی مهم:** آنچه Goldis به TalaMala تحویل می‌دهد **طلای خام** است (مثلا گرانول، شمش بزرگ استاندارد، یا هر فرم خامی که بازار می‌دهد)، **نه همان مدل شمشی که TalaMala فروخت**. TalaMala این طلای خام را برای hedging موجودی خود نگه میدارد یا در چرخه‌ی تولید بعدی استفاده میکند.

**جهت ledger همیشه hub-and-spoke است:**
- یک طرف obligation همیشه **Goldis** است (debtor یا creditor)
- در v1 obligation peer-to-peer (مثلا TalaMala ↔ AminZar مستقیم) **نداریم** — همه از طریق Goldis میگذرد
- این constraint در sense تجاری هست (نه DB-level)، چون انعطاف آینده برای peer-to-peer لازم می‌شود

**فروشهای خود Goldis (سایت Goldis، فروشهایی که payment به Goldis می‌رود):**
- payment_receiver = Goldis
- **هیچ inter_company_ledger entry بی‌رونی** ساخته نمی‌شود (Goldis از خودش نمی‌تواند بدهکار شود)
- فقط `treasury_positions` داخلی Goldis آپدیت می‌شود (Goldis exposure باز دارد و باید خودش از بازار بخرد)

### ۶.۲. چرا Real-Time Ledger و نه Settlement Worker روزانه

> **توضیح**: در نسخه‌ی قبلی این سند، Settlement بهعنوان worker روزانهای طراحی شده بود که batch تسویه میساخت. **این رویکرد اشتباه بود** — مدل واقعی این است که هر فروش **بلافاصله** یک obligation real-time ایجاد میکند (چون hedging باید سریع باشد)، و اپراتور Goldis در پایان روز / دوره به‌صورت دستی settle میکند.

**اصلاح**: حالا Settlement context عملا تبدیل می‌شود به **Inter-Company Ledger management**:
- ledger entries در لحظه‌ی هر sale ساخته میشوند (real-time)
- اپراتور Goldis در هر زمان می‌تواند `/admin/inter-company/settle-rial` یا `/admin/inter-company/settle-gold` بزند
- جمعبندی دورهای (مثلا «در ماه گذشته TalaMala چقدر بدهکار شد») از طریق aggregate query روی همین ledger ساخته می‌شود (نه جدول جداگانه)

**خلاصه: یک جدول `inter_company_ledger` + endpoint های settle. بدون settlement_rules پیچیده، بدون worker روزانه.**

### ۶.۳. مدل داده — `inter_company_ledger`

```sql
-- جدول یک‌پارچه برای تمام obligations بین شرکتها (هم gold هم rial)
CREATE TABLE inter_company_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debtor_company_id BIGINT NOT NULL REFERENCES companies(id),
    creditor_company_id BIGINT NOT NULL REFERENCES companies(id),
    asset_type VARCHAR(10) NOT NULL,  -- 'XAU_MG' | 'IRR'
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    -- mg برای gold، rial برای rial
    settled_amount_minor BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    -- open | partial | settled | cancelled
    source_type VARCHAR(50) NOT NULL,
    -- 'sale' | 'buyback' | 'manual_adjustment' | 'cancellation_reversal'
    source_order_id UUID NULL REFERENCES orders(id),
    -- در صورت buyback یا cancel، این entry می‌تواند یک entry قبلی را معکوس کند
    reverses_ledger_id UUID NULL REFERENCES inter_company_ledger(id),
    notes TEXT NULL,
    idempotency_key VARCHAR(100) NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    settled_at TIMESTAMPTZ NULL,
    settled_by BIGINT NULL REFERENCES users(id),
    CONSTRAINT chk_settled_le_amount CHECK (settled_amount_minor <= amount_minor),
    CONSTRAINT chk_companies_different CHECK (debtor_company_id <> creditor_company_id)
);
CREATE INDEX ix_icledger_pair_status
    ON inter_company_ledger (creditor_company_id, debtor_company_id, asset_type, status);
CREATE INDEX ix_icledger_order ON inter_company_ledger (source_order_id);
CREATE INDEX ix_icledger_open
    ON inter_company_ledger (status, created_at)
    WHERE status IN ('open', 'partial');

-- audit trail: هر action settle که اپراتور انجام می‌دهد
CREATE TABLE inter_company_settle_actions (
    id BIGSERIAL PRIMARY KEY,
    creditor_company_id BIGINT NOT NULL REFERENCES companies(id),
    debtor_company_id BIGINT NOT NULL REFERENCES companies(id),
    asset_type VARCHAR(10) NOT NULL,
    amount_minor BIGINT NOT NULL,
    affected_ledger_ids UUID[] NOT NULL,  -- FIFO consumed entries
    notes TEXT NULL,
    actor_id BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> **⚠️ توجه**: در نسخه‌ی قبلی این سند جداول `settlement_rules`، `settlements` و `settlement_items` تعریف شده بودند. **این جداول حذف شدند** و با `inter_company_ledger` جایگزین شدند. مدل واقعی کسب‌و‌کار با ledger سادهی real-time بهتر mapping می‌شود.

### ۶.۴. جریان (real-time در زمان فروش، بدون worker)

**در زمان هر sale غیر-Goldis** (payment_receiver != Goldis):

```
1. order saved (status=Paid)
2. pure_gold_mg = sum(order_items.pure_gold_mg)
   # وزن خالص طلا
3. raw_hedge_rial = sum(order_items.raw_hedge_price_rial)
   # D-65: raw_hedge_price = P_hedge_per_mg × pure_gold_mg
   #   P_hedge = قیمت عمدهی Goldis (= P0 + حداقلمارجین Goldis، شامل مالیات)
   #   ⚠️ «raw_gold_price» اینجا یعنی قیمت عمدهی Goldis، نه اسپات بازار بی‌رونی
   # snapshot در لحظه‌ی فروش، ذخیره در order_item.raw_hedge_price_rial
4. INSERT inter_company_ledger (دو ردیف):
   a. (debtor=payment_receiver, creditor=Goldis,
       asset='IRR', amount=raw_hedge_rial,
       source='sale', source_order_id=order.id)
   b. (debtor=Goldis, creditor=payment_receiver,
       asset='XAU_MG', amount=pure_gold_mg,
       source='sale', source_order_id=order.id)
5. treasury_positions.update(...)  # Goldis exposure +weight_mg
6. Outbox: InterCompanyObligationCreated × 2
```

**در زمان sale Goldis-side** (payment_receiver = Goldis):
- هیچ inter_company_ledger entry ساخته نمی‌شود
- فقط `treasury_positions.update(...)` # Goldis exposure +weight_mg
- Goldis مسئول خرید مستقیم از بازار است

### ۶.۵. Settle Operations (دستی توسط اپراتور Goldis)

#### Settle rial (فروشنده پول طلای خام را به Goldis پرداخت)

سناریو: فردا TalaMala واریز بانکی به حساب Goldis میکند بابت همه‌ی فروشهای دیروز.

```
POST /api/v1/admin/inter-company/settle-rial
Body: { creditor_company_id: Goldis, debtor_company_id: TalaMala, amount_rial, notes }

1. Validate: actor has admin/operator role
2. Find FIFO open rial obligations (debtor=TalaMala, creditor=Goldis, asset=rial)
3. Consume from oldest until amount مصرف شود:
   - برای هر entry: settled_amount_minor += min(remaining_amount, entry_remaining)
   - وقتی settled_amount_minor == amount_minor → status='settled'، settled_at=now
   - در غیر صورت → status='partial'
4. INSERT inter_company_settle_actions (audit)
5. Outbox: InterCompanyRialSettled
```

#### Settle gold (Goldis طلای خام را به فروشنده تحویل داد)

سناریو: Goldis در پایان هفته (یا هر دوره) معادل وزن خام طلا را فیزیکی به TalaMala تحویل می‌دهد (به‌صورت گرانول/شمش بزرگ/هر فرم خام). اپراتور Goldis تحویل را در سیستم ثبت میکند.

```
POST /api/v1/admin/inter-company/settle-gold
Body: { creditor_company_id: TalaMala, debtor_company_id: Goldis, amount_mg, notes }

(منطق FIFO مشابه بالا، روی asset='gold')
```

**نکته:** این endpoint **فقط ledger را آپدیت میکند** — تحویل واقعی طلای خام در دنیای واقعی توسط تیم عملیات Goldis انجام می‌شود (و در صورت نیاز، یک inventory_movement جدا برای ثبت ورود گرانول به انبار TalaMala ثبت می‌شود — این طلا برای hedging یا تولید بعدی بهکار می‌رود، **ربطی به refill شمشهای فروختهشده ندارد**).

### ۶.۶. نمونه واقعی

کاربر در برند طلاملا شمش ۱g می‌خرد، قیمت کل ۵۲M ریال (= ۴۸M طلای خام + ۴M اجرت/مالیات/سود TalaMala):

- پرداخت → TalaMala IPG (۵۲M به حساب TalaMala)
- شمش از inventory_location TalaMala (مال خود TalaMala) به مشتری (یا custodial)
- در همان transaction:
  - `inter_company_ledger`: TalaMala → Goldis، rial، **۴۸M** (قیمت طلای خام در لحظه‌ی فروش)، status=open
  - `inter_company_ledger`: Goldis → TalaMala، gold، **۱۰۰۰mg** (وزن خالص طلا)، status=open
  - `treasury_positions`: Goldis exposure +۱۰۰۰mg
- **سود ۴M (= ۵۲M − ۴۸M) نزد TalaMala باقی میماند.**

عملیاتهای بعدی (دستی توسط اپراتور Goldis):
1. Goldis از بازار طلای خام معادل ۱g می‌خرد (مثلا به ۴۷.۸M چون قیمت تغییر کرده) — این یک operation داخلی Goldis است که در `treasury_movements` ثبت می‌شود؛ exposure کاهش مییابد
2. TalaMala فردا ۴۸M ریال به حساب Goldis واریز میکند → اپراتور `settle-rial` میزند → rial obligation به ۰ میرسد (status=settled)
3. Goldis هر هفته/ماه مجموع طلای خامی که برای hedging TalaMala خریده را فیزیکی به انبار TalaMala تحویل می‌دهد → اپراتور `settle-gold` میزند → gold obligation به ۰ میرسد
4. این طلای خام تحویلی برای hedging موجودی TalaMala یا تولید شمش بعدی استفاده می‌شود (نه refill همان شمش فروختهشده)

### ۶.۷. Buyback و اثرش بر دفتر بین‌شرکتی

**بازخرید هرگز فروش اصلی را reverse نمیکند.** «لغو» وجود ندارد؛ فروش اول همیشه معتبر میماند و بازخرید یک تراکنش **مستقل روبهجلو** است:

- **بازخرید تحویل‌نشده / حضوری:** تبدیل physical↔digital است → اثر خزانه ≈ **خنثی** (دو پای متقابل)، **هیچ جفت تعهد طلایی تازهای** ساخته نمی‌شود؛ فقط `buyback_credit_rial` بهعنوان هزینهی ریالی ثبت می‌شود.
- **بازخرید دیجیتال** = همان `digital_trade sell` (مسیر جدا ندارد). در scope غیر-Goldis یک **جفت تازهی مخالف** میسازد: `seller→Goldis طلا amount_mg` + `Goldis→seller ریال P_hedge×amount_mg`. در scope=Goldis هیچ تعهد بین‌شرکتی، فقط خزانه‌ی `−`.

جزئیات کامل flow در بخش Buyback (۱۲.۵.۲).

### ۶.۸. Future (در v1 پیاده‌سازی نمی‌شود)

اگر در v2+ تصمیم به profit_share گرفته شود:
- ستونهای جدید به `inter_company_ledger` اضافه می‌شود (یا entry جدا با asset='profit')
- یا یک context جدید برای profit settlement
- در v1 هیچ نیاز به این نیست — سود همیشه نزد فروشگاه میماند

---

## ۷. Production Cycle — چرخه‌ی تولید و تأمین شمش

> این بخش روشن میکند که شمشها قبل از فروش از کجا می‌آیند و چگونه وارد انبار فروشندهها میشوند. **سمت فروش و hedging در بخش ۶ توضیح داده شد؛ این بخش سمت تأمین است.**

### ۷.۱. سه جریان تأمین

**جریان ۱ — AminZar (factory-only) → Goldis:**
- شرکت امین زر کارخانه است (فقط تولید). شمشهای تولید AminZar را با حاشیه‌ی سود به Goldis می‌فروشد.
- بعد از تحویل به Goldis، شمشها مال Goldis هستند و در channelهای Goldis (سایت Goldis، سایت AminZar که Goldis می‌گرداند، DigiKala، Basalam) فروخته میشوند.

**جریان ۲ — TalaMala (factory + seller) برای خودش:**
- شرکت طلاملا کارخانه است و خودش هم می‌فروشد. شمشهای تولید TalaMala مستقیما وارد انبار TalaMala میشوند و در channelهای TalaMala (سایت TalaMala، POS های TalaMala) فروخته میشوند.
- این یک جریان **داخلی TalaMala** است — هیچ obligation بین TalaMala و Goldis ایجاد نمیکند.

**جریان ۳ — TalaMala (factory) → Goldis (بهعنوان supplier):**
- TalaMala می‌تواند بخشی از تولید خود را به Goldis بفروشد (مثل AminZar).
- Goldis این شمشهای TalaMala را در channelهای خودش (سایت Goldis، DigiKala، Basalam) می‌فروشد.
- ⚠️ **توجه:** Goldis طلای **خام** از TalaMala نمی‌خرد — فقط شمشهای تولیدی برند TalaMala را می‌خرد.

**جریان معکوس (Goldis → TalaMala برای شمش):** در v1 وجود ندارد. TalaMala تنها از تولید کارخانه‌ای خودش تأمین می‌شود. آنچه از Goldis به TalaMala میرسد فقط طلای **خام** برای settle obligation های hedging است (بخش ۶.۵).

### ۷.۲. Supplier Purchase — خرید از کارخانه (داخل scope v1)

خرید از کارخانهها (AminZar و TalaMala-as-supplier) **داخل سامانه** است، به‌صورت یک جریان **فقط-طلا (بدون ریال)** روی همان batch preorder:

- Goldis به کارخانه می‌دهد: **اصل طلا** (وزن خالص شمشها) + **معادل اجرت به‌صورت طلا** (`purchase_wage_percent` — عملیاتی، نه metadata). کارخانه شمش حکشده/پلمبشده برمی‌گرداند.
- تعهد طلایی Goldis↔کارخانه روی همان `inter_company_ledger` با `asset='gold'`, `source_type='supplier_purchase'` رصد می‌شود (جدول جدا لازم نیست؛ کارخانه‌ایک طرف تعهد، Goldis طرف دیگر).
- **طلای اجرت = هزینهی حسابداری**، **بدون** اثر روی exposure/سقف خزانه (سقف معیار ریسک هجنشده است، نه هزینهی تولید).
- جریان ورود سریالها (preorder → in_stock) در ۷.۳.

### ۷.۳. مدل Preorder Bar — سریالها از پیش تولید میشوند

سیستم سریالها را از قبل تولید میکند، کارخانه فقط حک میکند:

```
1. اپراتور Goldis: «از AminZar 100 تا شمش 1g مدل سیمرغ سفارش بده»
2. سیستم 100 ردیف bar تولید میکند با:
   - serial = یکتا و قابل پیشبینی (مثلا "AM-1G-SIM-000001"..."AM-1G-SIM-000100")
   - product_id = شمش 1g مدل سیمرغ AminZar
   - status = 'preorder'                # هنوز فیزیکی وجود ندارد
   - current_location_id = factory_AminZar  # محل پیش‌فرض
   - owner_company_id = Goldis           # از پیش رزرو
3. لیست سریالها به AminZar تحویل داده می‌شود (PDF / API export)
4. AminZar شمشها را تولید میکند:
   - سریال را روی شمش laser engrave میکند
   - کارت پلمب با اطلاعات ثابت (وزن، عیار، تولیدکننده، QR ثابت، سریال) آماده میکند
   - شمش + کارت پلمب میشوند
5. تحویل به Goldis: اپراتور Goldis سریالها را اسکن میکند (یا batch import):
   - status: preorder → in_stock
   - current_location_id: factory_AminZar → goldis_warehouse
   - INSERT inter_company_ledger (asset='gold', source_type='supplier_purchase',
       debtor=Goldis, creditor=AminZar,
       amount=sum(pure_gold_mg) + sum(wage_gold_mg))
     # D-48: supplier_purchase داخل scope — تعهد طلایی Goldis↔کارخانه رصد می‌شود
     # wage_gold_mg = weight × (purchase_wage_percent/100) — cost-only، اثر روی exposure ندارد
```

**نکتهی مهم:** کارت پلمب فقط در کارخانه چاپ می‌شود. در لحظه‌ی فروش هیچ کارت دوم چاپ نمی‌شود (فقط فاکتور رسمی برای مشتری).

### ۷.۴. کاتالوگ — چندین SKU per Producer per Weight

برخلاف v4 که هر weight یک محصول بود، در v5 یک کارخانه می‌تواند **چندین مدل/طرح** برای یک وزن یکسان داشته باشد:

- شمش ۱ گرمی AminZar مدل **سیمرغ**
- شمش ۱ گرمی AminZar مدل **گل رز**
- شمش ۱ گرمی AminZar مدل **کلاسیک**

هر یک یک `product_id` جداگانه با ویژگیهای خود:

```sql
products
├── id BIGSERIAL PK
├── producer_company_id BIGINT NOT NULL  -- AminZar / TalaMala
├── name VARCHAR(200)                    -- "شمش 1گرمی امینزر مدل سیمرغ"
├── model_code VARCHAR(50)               -- "SIM-1G" (برای سریالسازی)
├── weight_mg BIGINT NOT NULL
├── purity SMALLINT NOT NULL             -- D-51: parts-per-1000 (750=18ع، 999=24ع). فرمول همیشه /1000
├── buyback_percent NUMERIC(5,2)         -- مثلا 98.0
├── purchase_wage_percent NUMERIC(5,2)   -- اجرت طلایی برای reporting (10.0 = +10٪ طلا)
├── packaging_type_id BIGINT FK
├── is_active BOOLEAN
└── ...
```

### ۷.۵. توزیع داخلی شمشها (Internal Inventory Movement)

بعد از intake شمش وارد انبار Goldis می‌شود. سه مسیر دارد:

1. **در انبار Goldis میماند** برای فروش از سایت Goldis، سایت AminZar (که Goldis می‌گرداند)، DigiKala، Basalam — همگی seller=Goldis، بدون inter-company entry
2. **به مغازهی نماینده یا POS device** که مدیریت آن با Goldis است — مالکیت با Goldis میماند، فقط `current_location_id` تغییر میکند
3. **به انبار TalaMala** — این فقط برای **طلای خام** (settle obligation hedging) است، نه شمشهای آماده

### ۷.۶. مدل عملیاتی TalaMala — لجستیک Goldis، پول TalaMala

طبق توافق انحصاری بین Goldis و شرکت طلاملا:

- TalaMala فقط نقش **brand owner + factory + payment receiver** را دارد
- Goldis تمام operationهای فنی و فیزیکی برای برند طلاملا را انجام می‌دهد:
  - نرم‌افزار (سایت، اپ POS، API)
  - مدیریت انبار و fulfillment
  - ارسال و دریافت (logistics)
  - مدیریت دستگاه POS (device management)
  - support کاربر
- ولی **پول و سود فروش** مال TalaMala است (طبق ۱.۲ و ۶.۱)
- شمشهای TalaMala می‌توانند هم در انبار TalaMala (مدیریت TalaMala) باشند هم در انبار Goldis (مدیریت Goldis، مالکیت TalaMala)
- انتقال شمش بین این دو انبار = فقط `inventory_movement` ساده، بدون ledger entry

این مدل در `inventory_locations` با دو ستون قابل تشخیص است:
- `owner_company_id` — مالک حقوقی (مثلا TalaMala)
- `manager_company_id` — کسی که فیزیکی مدیریت میکند (مثلا Goldis)

این دو می‌توانند متفاوت باشند.

---

## ۸. فرایند تحویل کالا

### ۸.۱. مفهوم

تیم انبار Goldis باید در یک admin panel ببیند:
- چه سفارشهایی از کدام brand آمده
- چه کالایی، چند تا، چه وزن
- از کجا برداشت شود (کدام انبار/صندوق)
- به کجا برود (مشتری/پیک/فروشگاه/انتقال داخلی)
- وضعیت آماده‌سازی

### ۸.۲. مدل داده

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

### ۸.۳. جریان

```
0. ⚠️ D-77: trigger ساخت task = «درخواست تحویل» است، نه «پرداخت سفارش».
   فروش امانی (delivered_at=NULL) هیچ taskی نمیسازد (شمش در خزانه قفل).
   فقط با درخواست تحویل مشتری (یا تحویل فوری در POS/فروشگاه) task ساخته
   می‌شود، با bar_id همان شمش تخصیص‌یافته (D-49).
1. Delivery requested → Fulfillment.create_task(order_item, bar)
2. INSERT fulfillment_tasks (status=pending)
3. انبار‌دار از admin panel: GET /admin/fulfillment/tasks?status=pending
4. انبار‌دار: POST /admin/fulfillment/tasks/{id}/assign-self
5. POST /admin/fulfillment/tasks/{id}/pick  → status=picking → picked
6. POST /admin/fulfillment/tasks/{id}/pack
7. POST /admin/fulfillment/tasks/{id}/handover  → courier info
   # D-78: انبار‌دار فقط «به پیک دادم» را میزند = handed_over (از دست ما خارج شد، نه «رسید»)
8. POST /admin/fulfillment/tasks/{id}/confirm-delivery → status=delivered
   # D-78: فقط با OTP گیرنده (+ اسکن سریال در تحویل حضوری). انبار‌دار مبدأ
   #   این را نمیبندد — نقش مقصد (پیکتأیید/کارمند فروشگاه/نماینده) با
   #   delivered_confirmed_by. تا قبل از این، شمش «در حال تحویل»؛
   #   bar.delivered_at فقط همینجا ست می‌شود.
```

---

## ۹. POS as First-class Sales Channel

### ۹.۱. مفهوم

POS = `sales_channels.channel_type = 'pos'`. یک channel POS مشخص دارد:
- `brand_id` (Goldis یا TalaMala)
- `terminal_id`
- `default_payment_account_id` (Goldis POS device → Goldis payment_account، TalaMala POS device → TalaMala payment_account)
- `device_id`

### ۹.۲. مدل داده

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

### ۹.۳. جریان POS sale (مختصر — برای جزئیات کامل به بخش ۱۲.۷ مراجعه شود)

```
1. POS device → GET /api/v1/pos/inventory (Bearer=api_key)
   • Backend از device → channel → dealer → location میرسد
   • Returns: لیست بارهای موجود در انبار **همان نماینده** + price preview
2. نماینده/کاربر یک bar انتخاب میکند
3. POS device → POST /api/v1/pos/reserve { bar_id, customer_mobile }
   • bar lock می‌شود (status=RESERVED، reserved_until=+N min)
4. کشیدن کارت روی POS hardware
5. POS device → POST /api/v1/pos/confirm { reservation_id, trace_number, rrn, amount, paid_at }
   • Order با order_type=pos_sale + Inventory.consume + Treasury + Settlement + DealerSale
6. در صورت fail → POST /api/v1/pos/cancel → release reservation
```

---

## ۱۰. لیست کامل Bounded Contexts

<table>
<thead>
<tr><th>#</th><th>Context</th><th>Global/Per-Company</th><th>مسئولیت</th></tr>
</thead>
<tbody>
<tr><td>1</td><td>**platform**</td><td>Global</td><td>Companies، Brands، SalesChannels، PaymentAccounts، InventoryLocations</td></tr>
<tr><td>2</td><td>**identity**</td><td>Global</td><td>User، Session، JWT، RBAC، Permission، SSO</td></tr>
<tr><td>3</td><td>**kyc**</td><td>Global</td><td>Shahkar، KYC status، user_level، limits، اسناد</td></tr>
<tr><td>4</td><td>**catalog**</td><td>Global</td><td>Product، Variant، Attribute، Image، ChannelAvailability، ExternalMapping</td></tr>
<tr><td>5</td><td>**pricing**</td><td>Hybrid</td><td>Source prices (global)، Internal base price، Channel formula، PriceLock</td></tr>
<tr><td>6</td><td>**inventory**</td><td>Global</td><td>Bar، Reservation، Movement، Transfer بین لوکیشنها</td></tr>
<tr><td>7</td><td>**cart**</td><td>Per-channel</td><td>Cart، CartItem</td></tr>
<tr><td>8</td><td>**order**</td><td>Per-brand</td><td>Order (با ۷ order_type)، OrderItem، OrderStatusLog، WithdrawalDetail (فقط rial)، PhysicalPurchaseFromWallet، Buyback</td></tr>
<tr><td>9</td><td>**payment**</td><td>Per-account</td><td>Payment، PaymentTransaction، Callback (Refund حذف شد — D-32. بهجای آن Buyback در order context)</td></tr>
<tr><td>10</td><td>**wallet**</td><td>Per-wallet-scope</td><td>AssetBalance، LedgerEntry، Lock</td></tr>
<tr><td>11</td><td>**treasury**</td><td>Goldis-only</td><td>Position، Coverage، Alert</td></tr>
<tr><td>12</td><td>**inter_company**</td><td>Inter-company</td><td>InterCompanyLedger (real-time obligations: gold + rial)، SettleActions (audit)، Reports (aggregate). جایگزین settlement قدیمی.</td></tr>
<tr><td>13</td><td>**fulfillment**</td><td>Goldis-ops</td><td>Task، Event</td></tr>
<tr><td>14</td><td>**pos**</td><td>Per-channel</td><td>Device، Transaction، Reconciliation</td></tr>
<tr><td>15</td><td>**dealer**</td><td>Per-company (opt-in)</td><td>Dealer، Tier، Sale، Commission (`dealer_commission_rates`+`dealer_commission_ledger`). ⚠️ SubDealer/شبکهای حذف — D-73</td></tr>
<tr><td>16</td><td>**marketplace**</td><td>Per-channel</td><td>ExternalChannel، ExternalOrder، Mapping، SyncLog، Adapter</td></tr>
<tr><td>17</td><td>**accounting**</td><td>Per-company</td><td>AccountingEvent، Export</td></tr>
<tr><td>18</td><td>**notification**</td><td>Per-user</td><td>Notification، Preference، Dispatcher</td></tr>
<tr><td>19</td><td>**realtime**</td><td>Global</td><td>SSE endpoint، event broadcaster</td></tr>
<tr><td>20</td><td>**audit**</td><td>Global</td><td>AuditLog (append-only)</td></tr>
<tr><td>21</td><td>**outbox**</td><td>Global</td><td>OutboxEvent + Publisher worker</td></tr>
<tr><td>22</td><td>**support**</td><td>Per-brand</td><td>Ticket، Message، Attachment</td></tr>
<tr><td>23</td><td>**content**</td><td>Per-brand</td><td>Blog، Article، FAQ، Page (SEO)</td></tr>
<tr><td>24</td><td>**reporting**</td><td>Global view</td><td>Read-only viewها برای dashboard/export</td></tr>
</tbody>
</table>

### قواعد تعامل بین context ها

1. هیچ context مستقیما جدول دیگر context را نمیخواند/نمینویسد. فقط از service interface.
2. هر تغییر دادهی حساس (wallet، treasury، order status، price، kyc، dealer commission، settlement) → audit_logs entry.
3. هر event حیاتی → outbox_events entry در همان transaction.
4. SQLModel layer split: `Table` models (DB) / `Create` / `Update` / `Read` / `Internal DTO`. هیچ Table model مستقیم به API response نمی‌رود.
5. تراکنش‌های دیتابیس per-request scope با commit در پایان operation.

---

## ۱۱. مدل دادهی سایر context ها

(جدولهای قبلی در بخشهای ۳-۸ آمدند. اینجا بقیه.)

### ۱۱.۱. Identity

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

### ۱۱.۲. KYC

```sql
CREATE TABLE kyc_records (
    user_id BIGINT PRIMARY KEY REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'NotStarted',
    user_level VARCHAR(20) NOT NULL DEFAULT 'Normal',
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
    level VARCHAR(20) PRIMARY KEY,
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

### ۱۱.۳. Catalog

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

### ۱۱.۴. Pricing

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

### ۱۱.۵. Inventory

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

### ۱۱.۶. Order

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

### ۱۱.۷. Payment

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

### ۱۱.۸. Outbox + Audit

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

### ۱۱.۹. جداول تکمیلی جلسهی بازبینی (D-62 / D-63 / D-73)

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
        CHECK (source_location_id != destination_location_id)
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
    treasury_adjustment_mg NUMERIC(12,4) NULL,         -- ریاضی treasury
    adjustment_reason TEXT NULL,
    reviewed_by BIGINT NULL REFERENCES users(id),      -- admin review
    reviewed_at TIMESTAMPTZ NULL,
    approved_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_payment_recon_payment ON payment_reconciliations (payment_id);
CREATE INDEX ix_payment_recon_status ON payment_reconciliations (reconciliation_status, created_at DESC);

-- D-97: Pending Reserves برای Checkout (D-97)
CREATE TABLE inventory_pending_holds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    wallet_scope VARCHAR(20) NOT NULL,
    pure_gold_mg_reserved NUMERIC(12,4) NOT NULL,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalized_at TIMESTAMPTZ NULL,                     -- set when payment confirmed
    released_at TIMESTAMPTZ NULL,                      -- set when order cancelled
    CONSTRAINT chk_only_one_state
        CHECK ( (finalized_at IS NULL AND released_at IS NULL) OR
                (finalized_at IS NOT NULL AND released_at IS NULL) OR
                (finalized_at IS NULL AND released_at IS NOT NULL) ),
    UNIQUE (order_id)  -- one hold به ازای هر سفارش
);
CREATE INDEX ix_hold_wallet_scope ON inventory_pending_holds (wallet_scope, released_at);

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

## ۱۲. جریانهای اصلی

### ۱۲.۱. خرید شمش از سایت TalaMala

```
1. درخواست به talamala.ir → frontend → POST /api/v1/cart/items
   Header: X-Channel-Code=talamala_web
2. Backend resolve میکند: brand=TalaMala, channel=talamala_web,
   payment_account=TalaMala IPG, operator=Goldis
3. POST /api/v1/pricing/locks → price_lock with snapshot
4. POST /api/v1/checkout/start →
   a. KYC + limits check
   b. Inventory.reserve(channel=talamala_web, product) →
      یک bar انتخاب می‌شود (cross-brand allowed):
      ترجیح: producer=TalaMala → if none, producer=Goldis → if none, AminZar
   c. Order.create(
        brand_id=TalaMala,
        sales_channel_id=talamala_web,
        seller_company_id=TalaMala,
        operator_company_id=Goldis,
        payment_account_id=TalaMala_IPG,
        payment_receiver_company_id=TalaMala,
        fulfillment_location_id=<TalaMala_warehouse | TalaMala_dealer_location>,
        order_type=purchase
      )
   d. INSERT order_items با buyback snapshot (D-32) + cost snapshot (D-06b):
      - pure_gold_mg = product.weight_mg × product.purity / 1000
      - buyback_credit_rial = final_price_rial × formula.buyback_percent / 100
      - raw_hedge_price_rial = P_hedge_per_mg(لحظه‌ی فروش) × pure_gold_mg   # D-65 — نه internal_base_price خالص
        (snapshot قیمت عمدهی Goldis در لحظه‌ی فروش — تنها مبنای inter_company_ledger)

   e. **هیچ ledger entry اینجا ساخته نمی‌شود — فقط در step 7 (mark_paid)**
5. POST /api/v1/payments/start → TalaMala IPG → redirect to bank
6. Bank callback → POST /api/v1/payments/callback/zibal [IDEMPOTENT]
7. on verified:
   - UPDATE payments status=verified
   - Order.mark_paid:
     • UPDATE orders status=Paid
     • Inventory.consume(bar) → status=SOLD, customer_id=user_id
     • (D-77: اگر تحویل فوری/POS → create_task(order_item, bar)؛ اگر امانی → هیچ task، فقط هنگام درخواست تحویل ساخته می‌شود)
     • Treasury.record(source=order_physical, delta=+pure_gold_mg,  # D-91: pure weight not raw weight
                       triggered_by_brand=TalaMala)
     • اگر payment_receiver != Goldis:
       INSERT inter_company_ledger × 2 (rial + gold per بخش ۶.۴)
     • Accounting.record_event
     • Outbox: OrderPaid, TreasuryPositionOpened,
               InterCompanyObligationCreated, AccountingEventCreated
               (D-77: FulfillmentTaskCreated اینجا نیست — فقط هنگام درخواست تحویل)
     • Notification → user
8. (D-77) امانی: شمش در خزانه قفل؛ هنگام درخواست تحویل → task با bar_id
   → انبار‌دار pick (اسکن سریال) → pack → handover (به پیک دادم)
   → confirm-delivery با OTP گیرنده (نقش مقصد، نه انبار‌دار — D-78)
```

### ۱۲.۲. خرید طلای دیجیتال در برند امین زر

```
1. کاربر در aminzar.ir → POST /api/v1/wallet/trades/buy
   { asset: XAU_MG, amount_mg: 500, channel: aminzar_web }
2. brand=AminZar, channel=aminzar_web, payment_account=Goldis_IPG,
   payment_receiver=Goldis, seller_company=Goldis
   (چون برند امین زر توسط Goldis اداره می‌شود — D-06b, ۱.۳)
3. KYC + limits
4. Treasury.check_capacity(gold, +500mg) → ok
5. Pricing.create_price_lock(channel=aminzar_web, asset=XAU_MG, 500mg)
6. Order.create(
     brand_id=AminZar, ...,
     order_type=digital_trade, trade_side=buy,
     payment_receiver=Goldis, seller_company=Goldis
   )
7. Payment → Goldis IPG → redirect
8. on verified:
   - Wallet scope=aminzar, company=شرکت گلدیس (XAU_MG) of user → +500mg  # D-46: ایزوله، نه merge در Goldis
   - Treasury.record(source=digital_buy, delta=+500mg,
                     triggered_by_brand=AminZar)
   - Inter-company ledger: **هیچ entry** — چون seller=Goldis (Goldis-side sale)
   - Accounting + Outbox + Notification
```

> **نکته:** هرچند brand_owner = شرکت امین زر، ولی چون Goldis این برند را اداره میکند و پول/سود مال Goldis است، از نظر hedging یک فروش Goldis-side محسوب می‌شود. **wallet scope=aminzar اما کاملا از goldis جدا است** (D-46: سه scope ایزوله). شرکت امین زر فقط در لحظه‌ی تأمین شمش از کارخانهاش به Goldis سود میگیرد (در context چرخه‌ی تولید — بخش بعدی).

### ۱۲.۳. خرید طلای دیجیتال در برند طلاملا

```
مشابه ۱۱.۲ ولی:
- payment_account=TalaMala_IPG, payment_receiver=TalaMala
- Wallet at TalaMala (XAU_MG) of user → +500mg
- Treasury مرکزی Goldis: +500mg (تک‌پایی digital_buy — D-67؛ treasury
  مرکزی است حتی اگر پول رفته به TalaMala)
- Inter-company ledger × 2 (TalaMala-side):
  • TalaMala → Goldis، rial = P_hedge_per_mg(لحظه) × 500mg   # D-69/D-65 — نه internal_base_price، نه قیمتی که کاربر پرداخت
  • Goldis → TalaMala، gold، 500mg
  (status=open، تا اپراتور settle کند)
  # D-69: خرید دیجیتال scope غیر-Goldis همسنگ فروش فیزیکی غیر-Goldis
  #   است (همان مدل ۱۲.۱)؛ فقط شمش/اجرت ندارد و خزانهاش تک‌پایی
  #   digital_buy است. مابه‌التفاوت (قیمت کاربر − P_hedge) سود TalaMala.
```

این کلید فهم سیستم است: **پول و wallet هر برند جداست، ولی Goldis بهعنوان Central Hedging Desk از طریق `inter_company_ledger` real-time در هر فروش obligation میگیرد و دورهای settle میکند.**

### ۱۲.۴. فروش طلای دیجیتال

```
1. کاربر تو wallet TalaMala → POST /api/v1/wallet/trades/sell
   { asset: XAU_MG, amount_mg: 300 }
2. Wallet.check_balance(user, TalaMala, XAU_MG, 300) → ok
3. Pricing lock (sell side)
4. Wallet.lock(user, TalaMala, XAU_MG, 300, ref=trade_intent)
5. Order.create (brand=TalaMala، ...)
6. confirm:
   - Wallet.consume_lock(user, TalaMala, XAU_MG, 300)
   - Wallet.credit(user, TalaMala, IRR, computed_amount)
   - Treasury.record(source=digital_sell, delta=-300mg)   # تک‌پایی — D-67
   - اگر scope غیر-Goldis (مثل TalaMala) → Inter-company × 2 (D-70، آینهٔ ۱۲.۳/D-69):
       • TalaMala → Goldis، gold، 300mg            # TalaMala طلا را پس می‌دهد
       • Goldis → TalaMala، rial، P_hedge_per_mg(لحظه) × 300mg
     اگر scope=Goldis (برند Goldis/AminZar) → هیچ تعهد بین‌شرکتی، فقط خزانه‌ی −
     # مابه‌التفاوت (P_hedge − مبلغ پرداختی به کاربر) حاشیه‌ی TalaMala
     # این همان مسیر یکتای digital_trade sell است (D-68 — «بازخرید دیجیتال» = همین)
   - Outbox + Notification
```

### ۱۲.۵. خرید محصول فیزیکی با wallet XAU_MG (چهار حالت تسویه)

> **D-31:** gold withdrawal بهعنوان flow جدا حذف شد. بهجای آن کاربر می‌تواند با wallet XAU_MG یک محصول فیزیکی بخرد (که اساسا همان تأثیر را دارد).
>
> **O-03:** برداشت فقط در قالب محصولات موجود امکان‌پذیر است. اگر کاربر ۱۰g میخواهد، باید یک شمش ۱۰g موجود انتخاب کند. اگر اجرت ۲٪ دارد، نیاز است ۱۰.۲g در wallet داشته باشد، یا تفاوت را ریالی پرداخت کند.

#### ۱۲.۵.۱ الف. جریان کامل physical_purchase_from_wallet

**Split payment کامل (D از Q&A):** فاز ۱ هر سه منبع پشتیبانی می‌شود:
1. wallet XAU_MG (gold part)
2. wallet IRR (در همان legal_entity — rial part)
3. gateway (مازاد rial اگر wallet IRR کافی نباشد)

```
1. User → /api/v1/orders {
     order_type: physical_purchase_from_wallet,
     from_wallet: TalaMala,
     product_id: <10g bar product>,
     gold_use_amount_mg: <how much XAU_MG to spend>,  ← optional override
                                                       ← default: حداکثر ممکن از wallet
     use_irr_wallet_for_difference: true | false,
     pay_remaining_in_gateway: true | false
   }
2. KYC limits check
3. Pricing.calculate_total(channel, product) →
   pure_gold_mg = product.weight_mg × (product.purity / 1000)  -- P0 fix: use pure_gold_mg، not weight_mg
   total_gold_mg_required = pure_gold_mg + wage_gold_mg  -- wage in mg if gold، else separately rial
   if wage_type=rial → wage_rial separately
4. Wallet.check_balance(user, TalaMala, XAU_MG) → wallet_gold_balance
   Wallet.check_balance(user, TalaMala, IRR) → wallet_irr_balance

5. Split payment plan:
   gold_part_mg = min(wallet_gold_balance, total_gold_mg_required, gold_use_amount_mg or max)
   gold_shortage_mg = total_gold_mg_required - gold_part_mg

   if gold_shortage_mg > 0:
     shortage_rial = gold_shortage_mg × current_metal_price_per_mg
     if use_irr_wallet_for_difference:
       irr_from_wallet = min(wallet_irr_balance, shortage_rial)
     else:
       irr_from_wallet = 0
     irr_from_gateway = shortage_rial - irr_from_wallet
     if irr_from_gateway > 0 and not pay_remaining_in_gateway:
       → reject (موجودی کافی نیست)

6. Wallet.lock(XAU_MG, gold_part_mg) → lock_id_gold
7. if irr_from_wallet > 0: Wallet.lock(IRR, irr_from_wallet) → lock_id_irr
8. Pricing.create_price_lock(channel, product, split_payment_plan)
   → snapshot شامل: gold_part_mg, irr_from_wallet, irr_from_gateway, metal_price
9. Inventory.reserve(bar)
10. Order.create(
      order_type=physical_purchase_from_wallet,
      payment_asset='SPLIT',
      total_gold_amount_mg=gold_part_mg,
      total_amount_rial=irr_from_wallet+irr_from_gateway,
      ...
    )
10a. INSERT order_payment_allocations برای wallet ها (gateway بعد می‌آید):
     • (allocation_type=wallet_gold, asset=XAU_MG, amount=gold_part_mg,
        wallet_lock_id=lock_id_gold, status=locked)
     • if irr_from_wallet > 0:
       (allocation_type=wallet_rial, asset=IRR, amount=irr_from_wallet,
        wallet_lock_id=lock_id_irr, status=locked)

11. if irr_from_gateway > 0:
    # ترتیب مهم برای رعایت CHECK constraint:
    # اول Payment ساخته می‌شود، بعد allocation که payment_id الزامی است
    a. payment = Payment.create(amount=irr_from_gateway, payment_state='pending')
    b. INSERT order_payment_allocation(
         allocation_type=gateway_rial, asset=IRR, amount=irr_from_gateway,
         payment_id=payment.id, status=pending
       )
    c. Payment.start(payment.id) → redirect URL

12. confirm (after gateway verified یا اگر gateway نداشت بلافاصله):
    در یک DB transaction:
    - Wallet.consume_lock(XAU_MG, gold_part_mg)
      → UPDATE allocations[wallet_gold].status = consumed
    - if irr_from_wallet > 0:
      Wallet.consume_lock(IRR, irr_from_wallet)
      → UPDATE allocations[wallet_rial].status = consumed
    - if irr_from_gateway > 0:
      Payment.verify (idempotent)
      → UPDATE allocations[gateway_rial].status = paid
    - Inventory.consume(bar) → customer_id=user, delivered_at=null (custodial)
      یا اگر کاربر در فروشگاه تحویل گرفت: delivered_at=now()
    - Treasury.record دو پای مستقل (D-66 — آینهٔ D-59):
        # gold_part_mg = pure_gold_mg + wage_gold_mg (جمع: فلز خالص + اجرت طلایی)
        پای۱: delta=−gold_part_mg            # مصرف کل طلای دیجیتال کیف ⇒ exposure بسته
        پای۲: delta=+pure_gold_mg            # خروج فقط فلز خالص شمش تحویلی ⇒ exposure باز (اجرت منهی)
      ⇒ net change = −wage_gold_mg (اجرت طلایی = هزینهی ساخت و تولید)
      # این هزینه از exposure Goldis جدا می‌شود و در مارجین TalaMala/AminZar گذاشته می‌شود.
      ⚠️ ثبت تنها پای۱ (متن قدیمی) باگ است: یک شمش هجنشده از سیستم خارج و exposure گم می‌شود
    - اگر payment_receiver != Goldis (یعنی from_wallet=TalaMala):
      INSERT inter_company_ledger × 2 (rial + gold per بخش ۶.۴)
    - (D-77: اگر تحویل فوری → create_task(order_item, bar)؛ اگر امانی → بدون task تا درخواست تحویل)
    - Accounting + Outbox + Notification

13. on fail (gateway timeout / cancel):
    - Wallet.release_lock(XAU_MG)
      → UPDATE allocations[wallet_gold].status = released
    - if irr_from_wallet: Wallet.release_lock(IRR)
      → UPDATE allocations[wallet_rial].status = released
    - UPDATE allocations[gateway_rial].status = failed
    - Inventory.release(bar)
    - PriceLock.cancel
    - Order.status = PaymentFailed
```

> **⚠️ نکته complexity:** این flow پیچیده است. تست concurrency حساس است — همزمانی lock بر دو wallet (XAU + IRR) + reservation + gateway callback. توصیه: integration test کامل با مسیرهای edge (gold فقط، gold+wallet_irr، gold+gateway، هر سه).

### ۱۲.۵.۲. Buyback — دو حالت در v1

Refund نداریم؛ «لغو» هم نداریم. **فروش اصلی همیشه معتبر میماند و هرگز reverse نمی‌شود.** بازخرید همیشه یک تراکنش **مستقل روبهجلو** است، با دو حالت عملیاتی:

<table>
<thead>
<tr><th>حالت</th><th>شرایط</th><th>تأیید</th></tr>
</thead>
<tbody>
<tr><td>(a) **بازخرید تحویل‌نشده**</td><td>bar.status=SOLD، `delivered_at IS NULL` (شمش هنوز در خزانه‌ی ماست)</td><td>اتومات (آنلاین)</td></tr>
<tr><td>(b) **بازخرید حضوری**</td><td>bar.status=SOLD، `delivered_at IS NOT NULL` (مشتری شمش را حضوری میآورد)</td><td>کارشناس مرکز Authorized — state machine</td></tr>
</tbody>
</table>

> «بازخرید دیجیتال» مسیر جدا **نیست** = همان `digital_trade sell` (۱۲.۴).

**در هر دو حالت:**
- وزن خالص (`weight × purity / 1000`) → wallet **XAU_MG** (همیشه).
- `order_items.buyback_credit_rial` (snapshot موقع خرید) → wallet **IRR** — **فقط اگر** شمش در لحظه‌ی بازخرید به نام کاربر ثبت مالکیت شده باشد و با **OTP** تأیید شود؛ وگرنه ۰.
- اجرت + مالیات + سود + هزینههای اضافه **می‌سوزد**.
- هر دو واریز به **scope برند فروش همان شمش** (`bars.sale_wallet_scope`).
- خزانه: تبدیل physical↔digital ⇒ **خنثی** (پای `+pure_gold_mg` به کیف، پای `−pure_gold_mg` شمش برگشتی)؛ **هیچ تعهد بین‌شرکتی تازهای** ساخته نمی‌شود؛ فقط `buyback_credit_rial` هزینهی ریالی است.
- بازخرید آنلاین فقط در همان scope/وبسایتی که خرید انجام شده مجاز است.

#### حالت (a) — بازخرید تحویل‌نشده (آنلاین، اتومات)

```
1. User → POST /api/v1/orders/{order_id}/buyback   (شمش هنوز تحویل نشده)
2. Validate:
   - order.user_id == current_user
   - bar.status == SOLD، bar.delivered_at IS NULL
   - (اگر fulfillment_task ساخته شده و packed/handed_over: حالت (a) مجاز نیست → حالت (b))
3. اتومات (در یک DB transaction):
   - یک سفارش بازخرید مستقل (order_type=buyback) ثبت می‌شود — فروش اصلی دستنخورده
   - bar.status = ASSIGNED, customer_id = NULL, sale_wallet_scope = NULL  (شمش به خزانه برمیگردد، قابل فروش دوباره در هر scope — D-92)
   - اگر fulfillment_task باز بود → بسته/کنسل می‌شود
   - Wallet.credit(user, bars.sale_wallet_scope, XAU_MG, order_item.pure_gold_mg)
   - اگر ثبت مالکیت+OTP: Wallet.credit(user, scope, IRR, order_item.buyback_credit_rial)
   - Treasury: دو پای متقابل ⇒ خالص ≈ صفر (physical→digital)
   - Audit log + Outbox: BuybackCompleted + Notification
```

#### حالت (b) — بازخرید حضوری (نیاز‌مند تأیید)

> این زیرflow **state machine صریح** دارد چون شامل تحویل فیزیکی است.

**شرایط مرکز buyback:**
- یا inventory_location با `company_id = goldis` و `location_type = warehouse` (دفتر مرکزی)
- یا dealer با flag `is_buyback_center = TRUE` (نماینده authorized)

**State machine:**

```
PhysicalRequested        (کاربر در پنل یا حضوری اعلام آمادگی)
   │
   ▼
PhysicalReceived         (کارشناس مرکز شمش را تحویل گرفت)
   │
   ▼
AuthenticityVerified     (کارشناس سریال + اصالت + وزن + عیار تأیید کرد)
   │
   ▼
Approved                 (تأیید نهایی برای credit کردن wallet)
   │
   ▼
WalletCredited           (هر دو wallet XAU_MG و IRR credit شدند)
   │
   ▼
Completed                (bar.location update شد + treasury/settlement)
```

اگر در هر مرحله مشکل: → `Rejected` با reason ثبت می‌شود.

**Flow کامل:**
```
1. User → POST /api/v1/buyback/physical/request
     { bar_id, target_location_id (مغازهی نماینده یا انبار) }
2. Validate:
   - bar.customer_id == current_user
   - bar.status == SOLD، delivered_at IS NOT NULL
   - target_location.can_buyback == TRUE
3. INSERT physical_buyback_request (status=PhysicalRequested, target_location_id)
4. کاربر شمش را به مرکز میبرد.
5. کارشناس → POST /api/v1/admin/buyback/{id}/receive
   → status=PhysicalReceived
6. کارشناس بررسی میکند: سریال، اصالت، وزن، عیار
   POST /api/v1/admin/buyback/{id}/verify [اگر OK] یا /reject
   → status=AuthenticityVerified | Rejected
7. کارشناس تأیید نهایی → POST /api/v1/admin/buyback/{id}/approve
   → status=Approved
8. سیستم در DB transaction (فقط بعد از Approved):
   - Wallet.credit(user, bars.sale_wallet_scope, XAU_MG, order_item.pure_gold_mg)
   - اگر ثبت مالکیت+OTP تأیید شد: Wallet.credit(user, scope, IRR, order_item.buyback_credit_rial)
   - bar.status = ASSIGNED, customer_id = NULL, delivered_at = NULL, sale_wallet_scope = NULL  (D-92: ready for resale in any scope)
   - bar.current_location_id = target_location_id  (location تغییر میکند)
   - INSERT inventory_movement (type=transfer_in, to=target_location)
   - Treasury: دو پای متقابل ⇒ خالص ≈ صفر (physical→digital)
   - فروش اصلی reverse نمی‌شود (تراکنش بازخرید مستقل)
   - status=WalletCredited → Completed
   - Audit log + Outbox: PhysicalBuybackCompleted + Notification
```

**قواعد امنیت‌ی:**
- Wallet **نباید** قبل از `AuthenticityVerified` credit شود
- separation of duties: کارشناس receive ≠ کارشناس verify (یا حداقل auditشده باشد)
- audit_log الزامی در هر transition

#### «بازخرید دیجیتال» — مسیر جدا ندارد

فروش طلای دیجیتال کیف **همان `digital_trade sell` (۱۲.۴)** است؛ از `/wallet/trades/sell` استفاده می‌شود. قیمتش از نردبان قیمت سمت فروش (`trade_side=sell`) می‌آید. مدل خزانه/بین‌شرکتیاش در ۱۲.۴ آمده.

### ۱۲.۵.۳ الف. Hedge Buy — خرید طلای خام از بازار (P0-7)

> **مفهوم:** Goldis بهعنوان Central Hedging Desk در پاسخ به فروشهای غیر-Goldis (TalaMala/AminZar)، طلای خام را از بازار می‌خرد و به صورت دورهای به فروشنده تحویل می‌دهد. این جریان تعهد طلایی بین‌شرکتی را پوشش می‌دهد.

```
۱. Operator Goldis → /api/v1/admin/treasury/hedge-buy/request
   {
     metal_type: "gold",
     amount_mg: 500000,
     supplier_name: "قیمتی طلا",
     purchase_price_per_gram_rial: 650000,
     notes: "پوشش تعهد فروش TalaMala (۲۰۲۶-۰۵-۱۸)"
   }

۲. Backend:
   - Treasury.check_capacity (سقف دو‌طرفه D-47: max_short_exposure_mg check)
   - Pricing.verify_market_rate (optional: تأیید نرخ با نقاط مرجع)
   - INSERT bulk_gold_inventory (
       location_id = goldis_warehouse,
       owner_company_id = Goldis,
       acquisition_source = "hedge_buy",
       total_weight_mg = 500000,
       total_pure_weight_mg = 500000 (assuming purity=1000 for raw),
       reference_type = "treasure_hedge_buy",
       reference_id = generated_id
     )
   - INSERT bulk_gold_movements (intake، weight_mg_delta=+500000)
   - Treasury.record (source=hedge_buy، delta=-500000)  # D-90: hedge_buy کاهش exposure (عکس short position)
   - Audit log + Notification

۳. Flow اختیاری برای compliance:
   - اپراتور می‌تواند hedge_buy را تا قبل از تحویل فیزیکی «pending» نگه دارد
   - بعد از تحویل فیزیکی از supplier: Operator تأیید میکند
   - وزن اسکن/تأیید شده → bulk_gold_inventory.last_counted_at update

۴. Settlement دورهای (روزانه یا هفتگی):
   - Operator:
     POST /api/v1/admin/inter-company/settle
     {
       creditor: "TalaMala",
       asset_type: "gold",
       amount_mg: 150000,  -- حداکثر از pending obligations
       source_bulk_gold_id: <bulk_gold_id>
     }
   - Backend:
     - Withdraw از bulk_gold_inventory (weight_mg_delta=-150000)
     - INSERT inventory_movement (from=goldis_warehouse, to=talamala_warehouse)
     - UPDATE inter_company_ledger (status=settled)
     - Audit log + Notification
```

**قوانین:**
- Hedge Buy **تنها در سطح Goldis** (operator only) قابل ایجاد است
- هر hedge_buy یک source برای multiple settlements می‌تواند باشد
- وزن در دسترس برای settlement نباید از total_weight_mg بیشتر شود (CHECK constraint یا service-level validation)
- هر settlement یک `inter_company_ledger.source_type='hedge_buy_settlement'` entry میسازد

### ۱۲.۵.۴. شارژ wallet ریالی (Rial Topup) — اتومات، بدون اپراتور

> کاربر در سایت هر brand می‌تواند wallet ریالی همان brand را از طریق gateway شارژ کند. **هیچ تأیید اپراتوری لازم نیست** — مثل خرید عادی.

```
1. User → POST /api/v1/wallet/topup
   Header: X-Channel-Code=<channel>
   Body: { amount_rial }
   • Backend resolves: فرانت/کانال → wallet_scope (D-76/D-46)
     (طلاملا→scope=talamala، گلدیس→scope=goldis، امینزر→scope=aminzar)
     ⚠️ سه scope کاملا ایزوله؛ امینزر merge در goldis نمی‌شود
     (هرچند legal entity هر دو شرکت گلدیس و درگاهش Goldis IPG است)
   • resolve payment_account: همان payment_account default channel
2. Backend:
   - INSERT wallet_topups (status=created)
   - Payment.create(amount=amount_rial, type=topup)
   - Payment.start → redirect URL gateway
3. کاربر → gateway → پرداخت → callback
4. Payment.callback (idempotent):
   - Payment.verify
   - if verified:
     • Wallet.credit(user, <company>, IRR, amount_rial, ref=topup)
     • UPDATE wallet_topups status=completed
     • Audit + Outbox: WalletToppedUp
     • Notification
   - if failed:
     • UPDATE wallet_topups status=failed
     • Notification (با تلاش مجدد)
```

**نکته:** هیچ Treasury impact ندارد (پول می‌آید، تعهد طلایی تغییری نمیکند). فقط Accounting event ثبت می‌شود.

### ۱۲.۶. برداشت ریال

> **«اپراتور» در این flow کیست؟**
> کارمند مرکز عملیات Goldis با role = `operator` (یا بالاتر: `admin`، `super_admin`). در سیستم RBAC، این role دسترسی به `withdrawal:approve` دارد. هدف: بررسی KYC، AML thresholds، fraud detection قبل از payout.

```
1. User → /api/v1/withdrawals/rial
   { from_wallet: Goldis, amount_rial, bank_account_id }
2. KYC + Wallet.check_balance(Goldis, IRR)
3. Wallet.lock(Goldis, IRR, amount)
4. Order.create(order_type=withdrawal_rial, status=WithdrawalRequested)
   + INSERT withdrawal_details (bank_account_id)
5. اپراتور (admin_role=operator) در پنل ادمین → POST /api/v1/admin/withdrawals/{id}/approve
   → status=OperatorApproved
6. Payout worker → Goldis bank API (یا TalaMala bank API برای from_wallet=TalaMala)
7. on success:
   - Wallet.consume_lock
   - status=Completed
   - Audit + Notification
8. on fail:
   - Wallet.release_lock
   - status=Failed
   - Notification (با تلاش مجدد یا تماس)
```

> **نکته:** برای v1، **همه‌ی** برداشتها نیاز به تأیید اپراتور دارند (تصمیم تیم). در آینده می‌توان آستانه‌ی مبلغ تعریف کرد که زیرش auto-approve باشد.

### ۱۲.۷. POS sale (sample: TalaMala POS at dealer)

> اپ POS لیست شمشهای موجود در انبار **همان نماینده** را نشان می‌دهد. نماینده/کاربر یکی را انتخاب میکند (نه scan). بعد از انتخاب و رفتن به مرحله‌ی پرداخت، شمش lock می‌شود.

```
1. POS Android app → GET /api/v1/pos/inventory
   Header: X-API-Key=<device api key>
   • Backend resolve میکند: device → sales_channel → dealer → inventory_location
   • returns: list of bars where:
       - current_location_id = <dealer's inventory_location>
       - status IN ('ASSIGNED', 'RAW')
   • هر bar شامل: serial_code, weight_mg, purity, product_name, product_id
       + price preview (محاسبهشده توسط Pricing با channel formula)

2. نماینده / کاربر یک bar را از لیست انتخاب میکند، می‌رود به مرحله پرداخت

3. POS app → POST /api/v1/pos/reserve
   Body: { bar_id, customer_mobile }
   • Backend:
     - validate: bar در dealer's location، status قابل reserve
     - Pricing.create_price_lock(channel, bar.product_id)
     - bar.status = RESERVED, reserved_until = +N min
     - returns: reservation_id, amount_rial, price_lock_id

4. کارتکشی روی POS hardware (TalaMala terminal — payment_account اختصاصی)

5. POS app → POST /api/v1/pos/confirm
   Body: { reservation_id, trace_number, rrn, amount_rial, paid_at, request_id }  # D-99: optional request_id for idempotency
   • Backend در DB transaction:
     - **D-99:** اگر `request_id` ارائه شده:
       - **INSERT/SELECT** `pos_pending_requests` با idempotency key = `(dealer_id, pos_session_id, request_id)`
       - اگر قبلا موجود: از `server_confirmed_at` return کن (idempotent)
     - INSERT pos_transactions (با terminal_id, trace_number, rrn)
     - Order.create(
         order_type=pos_sale, status=Paid,
         brand=<channel.brand>, payment_receiver=<channel.payment_account.company>
       )
     - INSERT order_items (با pure_gold_mg, buyback_credit_rial snapshot — D-32)
     - Inventory.consume(bar) → customer_id=resolved_user_id
     - Treasury.record(source=pos_sale, delta=+pure_gold_mg)  # D-91: pure weight
     - چون POS برای TalaMala است → payment_receiver=TalaMala:
       INSERT inter_company_ledger × 2 (rial + gold per بخش ۶.۴)
     - DealerSale (commission for dealer به‌صورت Gold-for-Gold)
     - **D-99:** UPDATE `pos_pending_requests` SET request_state='server_confirmed', server_confirmed_at=now()
     - Audit + Outbox + Notification

6. on fail (cancel یا timeout):
   - POST /api/v1/pos/cancel { reservation_id }
   - bar.status = ASSIGNED (release)
   - PriceLock cancel
```

### ۱۲.۸. Marketplace pull (DigiKala)

```
Worker هر دقیقه:
  for each channel where type=marketplace, mode in {pull_only, push_managed}:
    adapter = build_adapter(channel)
    new = await adapter.fetch_new_orders(since=channel.last_sync_at)
    for ext in new:
      dedup_key = adapter.compute_dedup_key(ext)
      try INSERT external_orders (..., dedup_key)
      except UniqueViolation: continue   # already imported

      internal_product_id = lookup_mapping(channel, ext.sku)
      Order.create(
        order_type=marketplace_sale, status=Paid,
        brand=channel.brand,
        payment_receiver=channel.payment_receiver,  # marketplace → Goldis
        seller_company=channel.seller_company,
      )
      Inventory.consume(channel, product)
      Treasury.record(source=marketplace_sale, delta=+pure_gold_mg)  # D-91: pure weight
      # D-56 (قطعی): marketplace همیشه seller=Goldis و payment_receiver=Goldis
      # هیچ inter_company_ledger entry برای marketplace وجود ندارد
      # (حتی اگر brand=TalaMala — چون Goldis انحصارا marketplace را اداره میکند)
      Outbox: ExternalOrderImported + OrderPaid + ...
    await adapter.acknowledge_orders(...)
    UPDATE channels.last_sync_at = now()
```

> **⚠️ D-56 (قطعی):** هیچ inter-company entry در marketplace نیست. تمام درآمد به Goldis می‌رود. TalaMala هیچ marketplace income مستقیم ندارد — فقط از فروش مستقیم سایتش (channel talamala_direct).

### ۱۲.۹. Inter-Company Settle (دستی، on-demand)

> **توجه**: نسخه‌ی قبلی این سند یک «Settlement daily worker» داشت. این **حذف شد** (D-06b). بهجای آن، در لحظه‌ی هر sale ledger entry ساخته می‌شود و اپراتور هر زمان دستی settle میزند.

```
سناریوی typical:
1. TalaMala فروش میکند → دو entry (gold + rial) با status=open ثبت می‌شود
2. حسابدار/اپراتور Goldis تو پنل میبیند: GET /admin/inter-company/ledger?status=open
3. وقتی TalaMala معادل بهای طلای خام را به Goldis بانکی منتقل کرد:
   POST /admin/inter-company/settle-rial { creditor=Goldis, debtor=TalaMala, amount, notes }
   → FIFO consume open rial obligations از قدیمیترین
4. وقتی Goldis طلای خام (گرانول/شمش بزرگ) را فیزیکی به انبار TalaMala تحویل داد:
   POST /admin/inter-company/settle-gold { creditor=TalaMala, debtor=Goldis, amount, notes }
   → FIFO consume open gold obligations
   + اپراتور می‌تواند یک inventory_movement جدا ثبت کند (ورود طلای خام به انبار TalaMala — این طلای خام برای hedging یا تولید بعدی است، نه refill شمشهای فروختهشده)
```

هیچ worker اتوماتی نیست. اپراتور دستی tracking میکند.

### ۱۲.۱۰. Treasury alert

```
# D-47: این worker فقط هشدار/پشتیبان است. سد واقعی = چک inline سد سخت
#   در سرویس هر تراکنش (قبل commit؛ اگر از سقف رد شود تراکنش رد می‌شود).
worker هر ۳۰ ثانیه:
  for each metal:
    net = SUM(delta_amount_mg) where status IN ('open','partially_covered')  # علامتدار
    s = treasury_settings[metal]
    # سمت فروش (net مثبت):
    if net >= s.max_open_exposure_mg:
      if s.auto_block_at_cap: set sell-block flag
      notify admin (critical)
    elif net > 0 and net / s.max_open_exposure_mg >= warning_threshold:
      throttled notify admin (warning: sell side)
    # سمت خرید/بازخرید (net منفی):
    if -net >= s.max_short_exposure_mg:
      if s.auto_block_at_cap: set buy-block flag
      notify admin (critical)
    elif net < 0 and -net / s.max_short_exposure_mg >= warning_threshold:
      throttled notify admin (warning: buy side)
```

---

## ۱۳. API contracts (نمونه)

### Conventions

- Base: `/api/v1`
- Headers الزامی: `Authorization: Bearer <jwt>`، `X-Channel-Code` (مگر در روترهای global/auth)
- Header الزامی برای POST تغییردهنده: `Idempotency-Key` (UUID)
- Response format: JSON با `{ data | error: {code, message}, meta }`

### Identity & KYC
- POST `/auth/send-otp` { mobile }
- POST `/auth/verify-otp` { mobile, otp } → JWT
- POST `/auth/refresh` { refresh_token }
- GET `/me`
- POST `/me/kyc/start-shahkar` { national_id }
- POST `/me/kyc/upload-doc`
- POST `/admin/kyc/{user_id}/approve`
- PUT `/admin/users/{user_id}/level`

### Platform (Companies/Brands/Channels)
- GET `/admin/companies`
- POST `/admin/companies`
- GET `/admin/brands`
- POST `/admin/brands`
- GET `/admin/sales-channels`
- POST `/admin/sales-channels`
- GET `/public/channel/{code}` — برای frontend boot

### Catalog
- GET `/products?channel_code=X`
- GET `/products/{id}`
- POST `/admin/products`
- POST `/admin/external-product-mappings`

### Pricing
- GET `/pricing/quote?channel_code=X&product_id=Y&quantity=N` — preview
- POST `/pricing/locks` — { channel_code, product_id, quantity, idempotency_key }
- GET `/pricing/locks/{id}`
- POST `/admin/pricing/sources/manual` — manual override
- POST `/admin/pricing/configs`
- GET `/admin/pricing/internal-base-prices`

### Cart/Checkout/Order
- POST `/cart/items`
- DELETE `/cart/items/{id}`
- POST `/checkout/start`
- GET `/orders`
- GET `/orders/{id}`
- POST `/admin/orders/{id}/status`

### Payment
- POST `/payments/start` { order_id }
- POST `/payments/callback/{provider}` — webhook
- (refund endpoint حذف شد — D-32. برای بازگشت پول از Buyback API استفاده می‌شود)

### POS
- GET `/pos/inventory` — لیست بارهای موجود در انبار نماینده (با price preview)
- POST `/pos/reserve` { bar_id, customer_mobile } — انتخاب bar مشخص + lock
- POST `/pos/confirm` { reservation_id, trace_number, rrn, amount, paid_at }
- POST `/pos/cancel` { reservation_id }
- GET `/admin/pos/transactions`
- POST `/admin/pos/reconcile`

### Wallet
- GET `/wallet/balances` → array of {wallet_scope, asset_code, balance, locked, locked_balance, credit_balance}
  # D-46: wallet_scope (نه company_code) زیرا goldis+aminzar هم شرکت گلدیس هستند
- GET `/wallet/ledger?wallet_scope=X&asset=Y`
- POST `/wallet/topup` { amount_rial } — شارژ wallet ریالی (به ازای هر برند auto-routed)
- GET `/wallet/topups` — تاریخچه شارژ
- POST `/wallet/trades/buy` { from_wallet, asset, amount, price_lock_id }
- POST `/wallet/trades/sell` { from_wallet, asset, amount, price_lock_id }
- POST `/admin/wallet/adjustments` { user_id, wallet_scope, asset, amount, direction, reason } (audit-mandatory)

### Withdrawal (فقط ریال — D-31)
- POST `/withdrawals/rial` { from_wallet, amount_rial, bank_account_id }
- GET `/withdrawals`
- POST `/admin/withdrawals/{id}/approve`
- POST `/admin/withdrawals/{id}/reject`
- POST `/admin/withdrawals/{id}/complete`

### Physical purchase from wallet (بهجای gold withdrawal)
- POST `/orders/physical-from-wallet` { from_wallet, product_id, pay_difference_in_rial }

### Buyback (بهجای refund) — ۲ حالت در v1 (D-58)

**(a) بازخرید تحویل‌نشده** (آنلاین، اتومات):
- POST `/buyback/undelivered` { order_id } — بازخرید فوری سفارش تحویل‌نشده، wallet credit بلافاصله

**(b) بازخرید حضوری** (حضوری، state machine):
- POST `/buyback/physical/request` { bar_id, target_location_id }
- GET `/buyback/physical/{id}` — برای کاربر مشاهدهی وضعیت
- POST `/admin/buyback/physical/{id}/receive` — کارشناس مرکز تحویل گرفت
- POST `/admin/buyback/physical/{id}/verify` — تأیید اصالت
- POST `/admin/buyback/physical/{id}/approve` — تأیید نهایی، wallet credit
- POST `/admin/buyback/physical/{id}/reject` — رد در هر مرحله با reason

**(c) بازخرید دیجیتال**:
- (endpoint جدا ندارد — از `/wallet/trades/sell` استفاده می‌شود — D-68)

### فرایند تحویل کالا
- GET `/admin/fulfillment/tasks?status=X`
- POST `/admin/fulfillment/tasks/{id}/assign-self`
- POST `/admin/fulfillment/tasks/{id}/pick`
- POST `/admin/fulfillment/tasks/{id}/pack`
- POST `/admin/fulfillment/tasks/{id}/handover` { courier, tracking }
- POST `/admin/fulfillment/tasks/{id}/confirm-delivery` { otp, serial? } — D-78 (جایگزین `/complete`؛ فقط نقش مقصد، با OTP گیرنده)

### Inventory Transfers (دو‌مرحله‌ای — D-62)
- POST `/admin/inventory/transfers` { source_location_id, destination_location_id, in_transit_location_id?, bar_ids: [UUID], idempotency_key } — ایجاد document با status=DRAFT
- GET `/admin/inventory/transfers?status=X` — لیست documentها (DRAFT/DISPATCHED/RECEIVED/COMPLETED/DISCREPANCY/CANCELLED)
- GET `/admin/inventory/transfers/{id}` — جزئیات + لیست items
- POST `/admin/inventory/transfers/{id}/dispatch` { dispatched_by_user_id } — تغییر status به DISPATCHED + OTP generate برای مقصد
- POST `/admin/inventory/transfers/{id}/receive` { otp_code, received_by_user_id } — تأیید OTP + مطابقت barها + status → RECEIVED
- POST `/admin/inventory/transfers/{id}/confirm` — تغییر status به COMPLETED (فقط اگر همه items matched)
- POST `/admin/inventory/transfers/{id}/discrepancy` { item_id, discrepancy_reason } — علامتگذاری item به عنوان discrepancy + status → DISCREPANCY
- POST `/admin/inventory/transfers/{id}/cancel` { cancel_reason } — لغو انتقال (فقط اگر هنوز DRAFT یا DISPATCHED)

### Treasury
- GET `/admin/treasury/positions?status=open&metal=gold`
- POST `/admin/treasury/positions/{id}/cover` { amount_mg, source_note }
- GET `/admin/treasury/snapshot`
- PUT `/admin/treasury/settings`

### Inter-Company Ledger (بخش ۶ — جایگزین Settlement قدیمی)
- GET `/admin/inter-company/ledger?creditor=X&debtor=Y&asset=gold|rial&status=open|partial|settled` — لیست obligations
- GET `/admin/inter-company/balance?company_a=X&company_b=Y` — net balance بین دو شرکت
- POST `/admin/inter-company/settle-rial` { creditor_company_id, debtor_company_id, amount_rial, notes } — تأیید پرداخت ریالی، FIFO consume open entries
- POST `/admin/inter-company/settle-gold` { creditor_company_id, debtor_company_id, amount_mg, notes, source_bulk_gold_id? } — تأیید تحویل طلا، FIFO consume. اگر `source_bulk_gold_id` ارائه شود (D-82 Hedge Buy): طلا از `bulk_gold_inventory` برداشته شود و `inventory_movement` ایجاد شود.
- GET `/admin/inter-company/settle-actions?company_a=X&company_b=Y&date_from=...` — audit log همه‌ی settle actions
- GET `/admin/inter-company/reports?period=month` — جمعبندی دورهای (aggregate query)

### Marketplace
- POST `/admin/external-channels`
- POST `/admin/external-channels/{id}/trigger-sync`
- GET `/admin/external-orders`
- POST `/admin/external-channels/{id}/push-inventory`

### Realtime
- GET `/realtime/stream` — SSE (با JWT in query یا cookie)

### Reporting/Audit
- GET `/admin/reports/sales?from=X&to=Y&brand=Z`
- GET `/admin/reports/wallet`
- GET `/admin/reports/treasury`
- GET `/admin/reports/settlement`
- GET `/admin/audit-logs?resource_type=X`

---

## ۱۴. Outbox Pattern و Events

### الگو

هر transaction که دادهی حساس را تغییر می‌دهد → outbox_events entry در **همان transaction**. publisher worker جدا فالو میکند.

```python
async def mark_order_paid(self, order_id: UUID, payment_id: UUID):
    async with self.uow.begin():
        order = await self.repo.get_for_update(order_id)
        if order.status == OrderStatus.Paid:
            return
        order.status = OrderStatus.Paid
        order.paid_at = utcnow()
        await self.inventory_svc.consume_reservation(order)
        # D-77: create_task اینجا صدا زده نمی‌شود — task فقط هنگام
        #   «درخواست تحویل» ساخته می‌شود (فروش امانی task ندارد).
        #   استثنا: تحویل فوری POS/فروشگاه → همانجا create_task(order_item, bar).
        await self.treasury_svc.record_open_position(order)   # D-47: per پای؛ چک inline سد سخت قبل این
        # D-06b/D-69: settlement_svc حذف شد. اگر فروش غیر-Goldis:
        if order.payment_receiver_company_id != GOLDIS_ID:
            await self.inter_company_svc.record_obligations(order)  # جفت rial(P_hedge)+gold
        await self.accounting_svc.record_event(order)

        events = [
            ("OrderPaid", "Order", str(order.id), {...}),
            ("TreasuryPositionOpened", ...),
            ("AccountingEventCreated", ...),
        ]
        if order.payment_receiver_company_id != GOLDIS_ID:
            events.append(("InterCompanyObligationCreated", ...))
        await self.outbox.enqueue(events)
        # commit در پایان context
        # نکته: FulfillmentTaskCreated اینجا منتشر نمی‌شود (D-77)
```

### Eventهای اصلی

```
# Identity / KYC
UserRegistered, UserKycSubmitted, UserKycApproved, UserKycRejected, UserLevelChanged

# Pricing
PriceSourceFetched, PriceSourceFailed, InternalBasePriceChanged,
PriceLockCreated, PriceLockExpired

# Inventory
InventoryReserved, InventoryReleased, InventoryConsumed, InventoryTransferred

# Order
OrderCreated, OrderPaid, OrderReservationExpired

# Payment
PaymentStarted, PaymentVerified, PaymentFailed

# POS
PosTransactionImported, PosOrderCreated

# Wallet
WalletCredited, WalletDebited, WalletLocked, WalletUnlocked,
WalletToppedUp, WalletTopupFailed

# Trade
DigitalGoldBought, DigitalGoldSold

# Buyback (دو حالت — بازخرید دیجیتال = DigitalGoldSold)
BuybackCompleted,                                    # (a) بازخرید تحویل‌نشده (آنلاین)
PhysicalBuybackRequested, PhysicalBuybackReceived,   # (b) physical state machine
PhysicalBuybackVerified, PhysicalBuybackApproved,
PhysicalBuybackCompleted, PhysicalBuybackRejected,

# Withdrawal (فقط ریالی — D-31)
WithdrawalRequested, WithdrawalApproved, WithdrawalRejected,
WithdrawalCompleted, WithdrawalFailed

# Treasury
TreasuryPositionOpened, TreasuryPositionCovered, TreasuryThresholdReached

# Inter-Company Ledger (بخش ۶)
InterCompanyObligationCreated,     # موقع sale (gold یا rial)
InterCompanyRialSettled,           # اپراتور cash transfer رو تأیید کرد
InterCompanyGoldSettled,           # اپراتور تحویل طلا رو تأیید کرد
InterCompanyObligationCorrected    # فقط برای admin correction (D-59: buyback obligation reverse نمیکند)

# فرایند تحویل کالا
FulfillmentTaskCreated, FulfillmentTaskAssigned, FulfillmentTaskCompleted

# Marketplace
ExternalOrderFetched, ExternalOrderImported, ExternalOrderFailed,
ChannelInventoryPushed, ChannelPricePushed

# Notification
NotificationDispatched, NotificationFailed

# Audit
AuditEntryCreated
```

### Subscriber registry (in-process در فاز ۱)

```python
EVENT_HANDLERS: dict[str, list[Callable]] = {
    "OrderPaid": [
        notification_service.handle_order_paid,
        accounting_service.handle_order_paid,
        realtime_broadcaster.broadcast_user_order,
    ],
    "TreasuryThresholdReached": [
        notification_service.alert_admins,
    ],
    # ...
}
```

---

## ۱۵. Workers / Scheduler

### کتابخانه: APScheduler + asyncio (نه Celery، نه Arq)

دلیل: تک‌سرور، تیم کوچک، حداقل dependency.

### Worker units (هر کدام یک systemd unit مستقل)

<table>
<thead>
<tr><th>Worker</th><th>فرکانس</th><th>تنظیم</th></tr>
</thead>
<tbody>
<tr><td>`outbox_publisher`</td><td>continuous (poll 1s)</td><td>parallelism=2</td></tr>
<tr><td>`pricing_fetcher`</td><td>dynamic به ازای هر منبع</td><td>configured</td></tr>
<tr><td>`marketplace_poller`</td><td>60s</td><td>به ازای هر کانال</td></tr>
<tr><td>`lock_expirer`</td><td>30s</td><td>—</td></tr>
<tr><td>`treasury_monitor`</td><td>30s</td><td>—</td></tr>
<tr><td>`notification_dispatcher`</td><td>continuous</td><td>parallelism=4</td></tr>
<tr><td>`payout_processor`</td><td>30s</td><td>—</td></tr>
<tr><td>`pos_transaction_reconciler`</td><td>hourly</td><td>به ازای هر کانال</td></tr>
<tr><td>`fulfillment_reminder`</td><td>hourly</td><td>—</td></tr>
</tbody>
</table>

### Supervisor

```python
# app/workers/__main__.py
async def main():
    workers = [
        OutboxPublisherWorker(),
        PricingFetcherWorker(),
        MarketplacePollerWorker(),
        LockExpirerWorker(),
        TreasuryMonitorWorker(),
        # SettlementDailyWorker حذف شد (D-06b) — inter_company_ledger real-time است
        NotificationDispatcherWorker(),
        PayoutProcessorWorker(),
        # ...
    ]
    tasks = [asyncio.create_task(w.loop()) for w in workers]
    await asyncio.gather(*tasks)
```

systemd unit `talamala-workers.service` → `python -m app.workers`.

---

## ۱۶. Realtime (SSE)

- یک endpoint: `GET /api/v1/realtime/stream`
- یک in-process broadcaster که به outbox publisher subscribe می‌شود
- topics پیشنهادی:
  - `wallet.{user_id}.{wallet_scope}` — تغییر balance
  - `order.{user_id}` — تغییر status
  - `pricing.channel.{channel_id}` — تغییر قیمت
  - `treasury.alert` — admin only
  - `fulfillment.task.{location_id}` — انبار‌دار
  - `settlement.alert` — accountant only

- در فاز ۲ (اگر چند web process باشیم): Redis Pub/Sub اضافه می‌شود

---

## ۱۷. Security, Compliance, Audit

### Authentication
- JWT access (TTL=15min) + refresh (TTL=30d in DB)
- Bearer header، یا httpOnly cookie برای web frontend
- POS device: API key با hash در DB
- Marketplace adapters: device/service credentials جدا

### Authorization (RBAC + ABAC)
- Roles: `super_admin`, `admin`, `operator`, `accountant`, `warehouse`, `pricer`, `dealer`
- Permission keys hierarchical: `view < create < edit < full`
- ABAC: `accountant` فقط می‌تواند settlement خودش (company-bound) را تأیید کند
- Route protection: `Depends(require_permission("settlement", level="approve"))`

### Idempotency
- Header `Idempotency-Key` در همه‌ی POST تغییردهنده الزامی
- ذخیره: یا در جدول `idempotency_keys` با TTL=۲۴h، یا در ستون idempotency_key entity (پیشنهاد دوم: سادهتر)

### Rate limiting
- `slowapi` (in-memory) برای فاز ۱، بعدا Redis-backed
- مخصوصا سختگیر روی: `/auth/send-otp` (۳/min)، `/payments/start`، `/wallet/trades/*`، `/withdrawals/*` (۱۰/min به ازای هر کاربر)

### Shahkar integration
- sub-module `kyc.shahkar`:
  - `verify(mobile, national_id) → ShahkarResult`
  - Cache result for ۳۰ روز
  - Re-verify اگر `national_id` تغییر کرد

### Audit
- هر action با priority بالا → audit_logs.insert در همان transaction
- لیست actions الزامی: تغییر قیمت، manual override، inventory adjustment، wallet adjustment manual، تغییر KYC level/limits، تأیید/رد withdrawal ریال، mark treasury covered، **inter-company settle (rial/gold)**، buyback (digital و physical)، تغییر role/permission، sync دستی marketplace، تغییر mapping، تغییر payment_account، inventory_movement بین انبارها (مثلا تحویل طلای خام از Goldis به TalaMala برای hedging)
- audit_logs **INSERT ONLY** — DB grant level: `REVOKE UPDATE, DELETE ON audit_logs FROM app_user`

### Payment callback security
- Signature verification اگر provider پشتیبانی کند (Sepehr/Parsian)
- Replay prevention: idempotency_key + در DB ذخیره می‌شود

### Frontend security
- CORS: only configured domains به ازای هر کانال
- CSP headers
- SameSite cookies برای web

---

## ۱۸. Migration Plan — Fresh Start (D-23 updated)

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

2. **چه می‌شود با dealer ها؟** (sub-dealer حذف شد — D-73)
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

- `talamala_pos` (Android) **هنوز پروداکشن نرفته** (D-44) — هیچ backward compatibility نیاز نیست. Android app از اول با API v1 جدید کار میکند.

### Tool احتمالی تنها

اگر در آینده تصمیم گرفته شود bars فیزیکی موجود از v4 وارد شوند، یک admin tool یکبار مصرف لازم می‌شود:

```
POST /admin/migration/import-bars-from-csv
   → CSV format: serial_code, weight_mg, purity, producer_company, current_location
```

این tool **خارج از scope فازهای ۰-۷ پیاده‌سازی است.**

---

## ۱۹. Testing Strategy

### Unit tests (pytest)
- Pricing formulas + همه‌ی rounding policies
- Wallet operations (credit/debit/lock/release)
- Settlement rule calculations (به ازای هر قانون type)
- KYC limit checks

### Integration tests (pytest + testcontainers Postgres)
- Order lifecycle (purchase): cart → checkout → payment → fulfill
- Order lifecycle (digital_trade): buy + sell
- Payment callback idempotency
- Inventory reserve/consume/release (concurrent)
- Wallet double-spend prevention (concurrent)
- Marketplace duplicate prevention
- Settlement daily calculation
- POS reserve→confirm→reconcile

### Concurrency tests (asyncio.gather)
- N task همزمان روی wallet یک کاربر
- N task همزمان روی reserve یک bar
- N callback همزمان روی یک payment

### Outbox tests
- event در همان transaction ذخیره می‌شود
- publisher دو بار publish نمیکند

### CI
- pytest + mypy + ruff + black
- Alembic up/down test

---

## ۲۰. ابهامات — وضعیت

تمام ابهامات اصلی (O-01…O-20) و سطح۲ (**Q-01…Q-10**) **حل شده‌اند**. نقاط کشفشدهی بازبینی (A-1…A-13، F-1…F-4) هم حل شده‌اند. استدلال و نگاشت Q→D در **۲.۵ (دفتر تصمیمات)**:

<table>
<thead>
<tr><th>Q</th><th>حلشده در</th><th>Q</th><th>حلشده در</th></tr>
</thead>
<tbody>
<tr><td>Q-01 split payment</td><td>۱۲.۵</td><td>Q-06 سطوح KYC</td><td>D-61</td></tr>
<tr><td>Q-02 physical buyback</td><td>۱۲.۵.۲ب</td><td>Q-07 inventory aging/transfer</td><td>D-62</td></tr>
<tr><td>Q-03 قیمت buyback</td><td>D-53/D-59</td><td>Q-08 انتخاب درگاه</td><td>D-63</td></tr>
<tr><td>Q-04 settlement_rules</td><td>منتفی (D-06b)</td><td>Q-09 برداشت ریال</td><td>D-64</td></tr>
<tr><td>Q-05 reverse در buyback</td><td>D-59</td><td>Q-10 منبع شمش wallet</td><td>D-60</td></tr>
</tbody>
</table>

> **موارد باز باقیمانده در بخش ۰.۱ (موارد باز / بازبینی‌نشده (تمرکز داور اینجا))** فهرست شده‌اند (تمرکز بازبینی بعدی آنجاست).

---

## ۲۰.۵. نکات اضافی برای D-84/D-95 — عملیات Commission Offset

### خلاصه عملیاتی

**D-84 (Commission Gold Exposure Offset)** و **D-95 (Dealer Commission Settlement + Offset)** دو فیچر مرتبطاند:

1. **واریز کمیسیون TalaMala** (فاز ۴):
   - نماینده TalaMala محصولات فروخت → کمیسیون عایدی طلایی
   - Goldis کمیسیون را به کیف نماینده واریز میکند (XAU_MG +)
   - Treasury position «در معرض خطر» می‌شود (+pure_gold_mg)
   
2. **مقابلرقم مالی TalaMala**:
   - TalaMala تعهد به Goldis دارد (supplier_purchase یا hedge_buy): «Goldis −X طلا بابت تحویل»
   - TalaMala درآمد گلیسیار از نمایندهها: «نماینده کمیسیون +Y طلا فروخت»
   - این دو منبع **می‌توانند offset شوند** تا treasury balance را حفظ کنند.

3. **روند settlement (v1 — Manual)**:
   - **ماهانه**, اپراتور:
     - لیست کمیسیونهای TalaMala ماه = X mg
     - لیست تعهدات قدیم ریالی/طلایی Goldis↔TalaMala
     - فراخوانی: `POST /admin/inter-company/settle-offset { TalaMala, Goldis, comment="May commission offset" }`
     - سیستم: **FIFO consume** قدیمیترین hedge obligation و commission obligation خود‌کار
     - نتیجه: هر دو بخش treasury balance میماند

4. **اگر offset نشود**:
   - Treasury position روزافزون بدتر می‌شود
   - TalaMala debtor و creditor Goldis باقی میماند
   - **نشت مالی**: Goldis طلا داده، TalaMala بدهکار نماند = سود Goldis کم

### توثیق برای v1

اگر در v1 automation نباشد (تنها manual settlement):
- **Runbook برای اپراتور**: روز هفتم هر ماه، این endpoint را اجرا کن
- **Alert**: اگر تعهدات offset نشده ۳۰ روز بیشتر باقی بماند، warning
- **در فاز ۵**: worker automated منتشر شود (schedule: ماهانه یکم)

---

## ۲۱. Implementation Roadmap

### فاز ۰ — Infrastructure (هفته ۱)
1. Project structure (folders: `app/contexts/<name>/...`)
2. Database setup + Alembic init
3. Authentication + JWT + middleware (Identity context base)
4. Platform context (Companies/Brands/Channels) — برای resolve از همه middleware ها
5. Outbox infra (table + skeleton publisher)
6. Audit log infra
7. Testing infra (pytest fixtures, testcontainers Postgres, factories)

### فاز ۱ — Core domain (هفته ۲-۳)
8. Identity (User، Session، JWT)
9. KYC (با Shahkar stub اولیه)
10. Catalog
11. Pricing (Source + Config + Internal Base + Channel Formula + PriceLock)
12. Wallet (به ازای کیف‌پول multi-asset ledger — D-46: goldis/aminzar/talamala ایزوله)

### فاز ۲ — Transactional (هفته ۴-۵)
13. Inventory
14. Cart
15. Order (purchase only)
16. Payment (Zibal + Sepehr — برای دو tenant)
17. فرایند تحویل کالا

### فاز ۳ — Treasury + Trade + Settlement (هفته ۶-۷)
18. Treasury basic (record + read) — با merge شدن hedging (D-42)
19. Wallet trades (digital_trade buy/sell)
20. Withdrawal **فقط ریال** (D-31 — gold withdrawal حذف شد)
21. physical_purchase_from_wallet flow (بهجای gold withdrawal)
22. Buyback (دو حالت در v1):
    - (a) بازخرید تحویل‌نشده — آنلاین اتومات (فروش اصلی reverse نمی‌شود)
    - (b) بازخرید حضوری — state machine کامل (PhysicalRequested → … → Completed)
    - (بازخرید دیجیتال = همان `digital_trade sell` — جدا پیاده نمی‌شود)
23. **Hedge Buy flow + bulk_gold_inventory intake** (D-95): Goldis خرید طلای خام از بازار/ارزی یا دریافت طلا از تولیدکنندهها (supplier purchase D-48)؛ ثبت در treasury (−exposure)؛ تولید شمش و توزیع در شبکه.
24. Inter-Company Ledger (D-06b): جدول `inter_company_ledger`، endpointهای settle، FIFO consume. **بدون settlement_rules، بدون worker روزانه.**
25. Treasury alert worker

### فاز ۴ — DealerNetwork (هفته ۸-۹)
26. Dealer + Tier + dealer_commission_rates + dealer_commission_ledger (بدون SubDealer/شبکه — D-73)
27. POS context (sales_channels.type=pos)
28. POS reserve→confirm flow
29. DealerSale + commission
30. **Dealer commission settlement + treasury/inter-company offset** (D-84/D-95):
    - (a) واریز کمیسیون طلایی نماینده: `POST /admin/dealer/{id}/deposit-commission { amount_mg, source_dealer_sales_ids }` ← XAU_MG wallet نماینده +، Treasury position +pure_gold_mg (exposure افزا‌یش)
    - (b) Treasury check: اگر TalaMala commission (یعنی نماینده TalaMala محصولات فروخته)، یک inter_company_ledger entry ایجاد می‌شود **بهجای** FIFO settle:
      - `debtor=TalaMala, creditor=Goldis, asset=gold, amount=commission_amount_mg`
      - دلیل: TalaMala طلا به نماینده داد (treasury −)، ولی این طلا باید از hedge obligation Goldis (تعهد Goldis→TalaMala) پوشش خوردہ شود. بدون offset، Treasury balance misaligned میماند.
    - (c) Manual settlement flow (v1): اپراتور ماہانہ: `POST /admin/inter-company/settle-offset { company_a=TalaMala, company_b=Goldis, comment="commission settlement month N" }` → FIFO consume oldest hedge obligation + commission obligation خود‌کار offset
    - (d) نکته پیاده‌سازی: اگر in v1 offset خود‌کار نباشد (فقط manual)، توثیق شود که *اپراتور هر ماه این endpoint را اجرا میکند*. در فاز ۵+ می‌تواند worker شود.

### فاز ۵ — Marketplace (هفته ۱۰)
31. Adapter interface + skeleton
32. DigiKala adapter (mode=`push_managed` per D-37)
33. Marketplace poller worker

### فاز ۶ — Realtime & polish (هفته ۱۱)
34. SSE endpoint + broadcaster
35. Notification preferences UI (API)
36. Admin reporting endpoints
37. Audit viewer API

### فاز ۷ — Launch (هفته ۱۲)
> **توجه: Migration از v4 وجود ندارد (D-23: Fresh start)** — فاز ۷ شامل launch tasks است نه ETL.

38. Communication plan با کاربران v4 (خارج از scope توسعه — تیم بیزینس)
39. Staging environment final smoke testing
40. Production deployment + DNS switch
41. (Optional) Admin tool یکبار مصرف import-bars-from-csv برای bars فیزیکی موجود v4

---

## ۲۲. دستورالعمل به LLM پیاده‌ساز

### قبل از کدنویسی هر context

1. این سند را کامل بخوان
2. `talamala_v4/CLAUDE.md` و `talamala_pos/CLAUDE.md` را بخوان
3. ابهامات بخش ۱۹ مربوط به context را بررسی کن — اگر حل نشده، **سؤال بپرس**
4. ساختار folder/file context را اول طراحی کن (بدون مدل)، تأیید بگیر

### قواعد فنی الزامی

- Type hints کامل (mypy strict)
- SQLModel (Table) برای DB، Pydantic (Create/Update/Read) برای API — هرگز Table مستقیم به API
- async-first (SQLAlchemy 2.x async + asyncpg)
- Explicit transaction در هر service method
- `SELECT FOR UPDATE` برای wallet balance، bar reservation، treasury_settings update
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

---

## ۲۳. سیستمهای بحرانی برای امنیت مالی (v2.7 — Critical Subsystems)

### ۲۳.۱ نقش و اهمیت

۴ subsystem زیر به منظور جلوگیری از خطرات مالی حیاتی در تولید پیاده‌سازی شده‌اند:

1. **D-96: Payment Reconciliation** — جلوگیری از پولهای گیرافتاده اگر قیمت بین lock و payment تغییر کند
2. **D-97: Pending Reserves** — منع از نقض سقف خزانه به سبب condition race
3. **D-98: Payment State Machine** — بازیابی خود‌کار پرداختهای orphaned بعد از crash
4. **D-99: POS Offline Queue** — پشتیبانی از دستگاههای بدون اینترنت پایا

---

### ۲۳.۲ D-96: Payment Reconciliation — مطابقتدهی قیمت

**مشکل:**
- Customer مقدار ریال را authorize میکند بر اساس قیمت لحظه‌ی checkout
- Payment lock تنها ۵ دقیقه معتبر است
- اگر network delay یا customer idle، قیمت تغییر میکند
- System D-31 ممنوع میکند: refund ندهید
- **Blocker:** پول گیر میافتد، customer ناراضی، audit issue

**راهحل:**

```sql
-- جدول reconciliations
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
    treasury_adjustment_mg NUMERIC(12,4) NULL,         -- ریاضی treasury
    adjustment_reason TEXT NULL,
    reviewed_by BIGINT NULL REFERENCES users(id),      -- admin review
    reviewed_at TIMESTAMPTZ NULL,
    approved_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Flow:**
1. Payment verified ← gateway callback
2. System calculates: `variance = authorized_amount_rial - actual_price_at_payment_rial`
3. If `|variance_percent| <= 2%`:
   - **Auto-approve**: treasury absorbs or pockets difference
   - `reconciliation_status = auto_approved`
   - Finalize ledger entry immediately
4. Else (>2% variance):
   - Create record with `manual_review` status
   - Alert admin: "Large price variance [details]"
   - Admin reviews + approves/rejects
   - If approved: adjust treasury, finalize
   - If rejected: refund via separate buyback flow (not direct refund — D-31 compliance)

**Endpoints:**
- `GET /admin/payments/reconciliations` — list pending reviews
- `POST /admin/payments/reconciliations/{id}/approve` — approve with optional treasure adjustment
- `POST /admin/payments/reconciliations/{id}/reject` — reject (triggers buyback + refund)

---

### ۲۳.۳ D-97: Pending Reserves — رزرو بر روی Checkout

**مشکل:**
- Treasury exposure cap = `100 kg`
- Two customers simultaneously `POST /checkout` each for `60 kg`
- Both pass the check: `exposure + 60 <= 100` ✅
- Both POST `/payment` ← payments verified ← **both finalize simultaneously**
- **Result:** Treasury = `-20 kg` (short by 20 kg) 🚨

**راهحل:**

```sql
-- Pending reserves (locked before payment)
CREATE TABLE inventory_pending_holds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    wallet_scope VARCHAR(20) NOT NULL,
    pure_gold_mg_reserved NUMERIC(12,4) NOT NULL,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalized_at TIMESTAMPTZ NULL,                     -- set when payment confirmed
    released_at TIMESTAMPTZ NULL,                      -- set when order cancelled
    CONSTRAINT chk_only_one_state
        CHECK ( (finalized_at IS NULL AND released_at IS NULL) OR
                (finalized_at IS NOT NULL AND released_at IS NULL) OR
                (finalized_at IS NULL AND released_at IS NOT NULL) )
);
```

**Flow:**

1. **Checkout (POST /checkout)**:
   - Calculate `pure_gold_mg` from cart items
   - **Check:** `treasury.current_balance - pure_gold_mg >= treasury.min_balance_threshold`
   - If OK: **INSERT** `inventory_pending_holds` (reserve locked until payment)
   - If NOT OK: Reject checkout with "Insufficient availability" (not "lack of credit")

2. **Payment (POST /payment/{order_id})**:
   - Gateway verifies payment ✅
   - **SELECT inventory_pending_holds WHERE order_id = ?** (check still locked)
   - If still locked: Finalize ledger entry + `UPDATE inventory_pending_holds SET finalized_at = now()`
   - If released (order cancelled meanwhile): Reject this payment

3. **Cancel Order (POST /orders/{id}/cancel before payment)**:
   - **UPDATE inventory_pending_holds SET released_at = now()**
   - Release the lock
   - Notify customer

**Invariant:** At any moment, `treasury.balance >= min_threshold + sum(pending_holds.pure_gold_mg)`

---

### ۲۳.۴ D-98: Payment State Machine — منع پول یتیم

**مشکل:**
- Gateway verifies payment ✅ (بانک پول را قبول کرد)
- System crashes **before** writing `inter_company_ledger` entry
- **Result:** پول در حساب بانکی تأیید شده، اما در دفاتر Goldis ثبت نشده
- Audit: Reconciliation fail, monthly variance

**راهحل:**

**جدول:** تعریف کامل `payments` با تمام ستونهای D-92 در بخش ۱۱.۷ موجود است (payment_state، gateway_verified_at، ledger_entry_id، idempotency_key).

**Flow:**

1. **Gateway Callback** (e.g., `GET /payment/zibal/callback?ref=X`):
   - Verify signature, amount, order_id
   - **INSERT** `payments` with `payment_state = 'gateway_verified_pending'`
   - **Return 200 OK** to gateway immediately (idempotent)
   - Fire off async job: `create_ledger_entry(payment_id)`

2. **Async Job** (with retry + exponential backoff):
   ```python
   def create_ledger_entry(payment_id):
       payment = db.get(Payment, payment_id)
       if payment.payment_state != 'gateway_verified_pending':
           return  # already processed or failed
       
       try:
           # Create inter_company_ledger entry
           ledger_entry = inter_company_ledger.create(
               order_id=payment.order_id,
               idempotency_key=payment.idempotency_key  # prevent duplicate
           )
           payment.ledger_entry_id = ledger_entry.id
           payment.payment_state = 'inter_company_ledger_created'
           db.commit()
       except IntegrityError:  # idempotency_key duplicate
           # Already created, just mark as done
           payment.payment_state = 'inter_company_ledger_created'
           db.commit()
           return
   ```

3. **Recovery Job** (runs on startup):
   ```python
   def recover_pending_payments():
       # Find all payments in 'gateway_verified_pending' state
       pending = db.query(Payment).filter(
           payment_state = 'gateway_verified_pending',
           gateway_verified_at < now() - timedelta(hours=1)
       )
       for payment in pending:
           create_ledger_entry(payment.id)  # retry
   ```

4. **Alert** (if recovery fails):
   - Send email to admin: "Payment recovery failed: [payment_id]"
   - Trigger manual dashboard entry for operator review

**Endpoints:**
- `GET /admin/payments/pending-states` — list all payments not in 'finalized' state
- `POST /admin/payments/{id}/manual-recover` — trigger recovery for specific payment

---

### ۲۳.۵ D-99: POS Offline Queue — دستگاههای بدون اینترنت

**مشکل:**
- POS device (mobile) charges card via gateway ✅
- WiFi drops **before** `/api/pos/confirm` succeeds
- Device retries for 10 min, then gives up
- Dealer manually closes app
- **Result:** سفارش `pending` (unconfirmed)، gold reserved، customer charged — **inconsistent state**
- No recovery path except "call support"

**راهحل:**

```sql
-- Server-side: track pending POS requests
CREATE TABLE pos_pending_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_id BIGINT NOT NULL REFERENCES users(id),
    pos_session_id VARCHAR(100) NOT NULL,             -- device session ID
    request_id VARCHAR(100) NOT NULL,                 -- uniqueness به ازای هر دستگاه
    sale_data JSONB NOT NULL,                         -- full sale details (customer, bar, price)
    payment_ref VARCHAR(100) NOT NULL,                -- gateway ref
    request_state VARCHAR(30) DEFAULT 'received',
    -- received | processing | pos_confirmed | server_confirmed | failed
    server_confirmed_at TIMESTAMPTZ NULL,
    error_reason TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '24 hours'),
    UNIQUE (dealer_id, pos_session_id, request_id)   -- idempotency به ازای هر دستگاه
);

-- Optional: store local queue snapshot from device (for audit)
CREATE TABLE pos_device_queue_snapshots (
    id BIGSERIAL PRIMARY KEY,
    dealer_id BIGINT NOT NULL REFERENCES users(id),
    pos_session_id VARCHAR(100) NOT NULL,
    queue_snapshot JSONB NOT NULL,                   -- array of pending requests on device
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Flow:**

**Device (local logic):**
```typescript
// On POS app
class OfflineQueue {
  private queue: LocalRequest[] = [];  // SQLite on device

  async confirmSale(saleData) {
    const requestId = generateUUID();
    const request = {
      requestId,
      saleData,
      paymentRef: saleData.gateway_ref,
      timestamp: Date.now()
    };
    
    this.queue.push(request);  // save locally
    
    try {
      const res = await POST('/api/pos/confirm', {
        request_id: requestId,
        ...saleData
      }, { timeout: 10s });
      this.queue.splice(0, 1);  // remove from local queue
      return res;
    } catch (err) {
      // Network error — leave in queue
      showMessage("⏳ Sale pending. Will sync when online.");
      return { deferred: true, requestId };
    }
  }

  async syncQueue() {
    while (this.queue.length > 0) {
      const request = this.queue[0];
      try {
        const res = await POST('/api/pos/confirm', {
          request_id: request.requestId,
          ...request.saleData
        });
        this.queue.splice(0, 1);
      } catch (err) {
        break;  // stop if still offline
      }
    }
  }
}
```

**Server (endpoint):**
```python
@app.post("/api/pos/confirm")
async def pos_confirm(
    request_id: str,
    dealer_id: int,
    pos_session_id: str,
    sale_data: dict,
    # ... validation
):
    # 1. Check idempotency
    existing = db.query(PosConfirmedSale).filter(
        request_id=request_id,
        dealer_id=dealer_id
    ).first()
    if existing:
        return { sale_id: existing.sale_id, status: 'already_confirmed' }
    
    # 2. Record pending request
    pending = db.query(PosPendingRequest).filter(
        dealer_id=dealer_id,
        pos_session_id=pos_session_id,
        request_id=request_id
    ).first()
    if not pending:
        pending = PosPendingRequest.create(
            dealer_id=dealer_id,
            pos_session_id=pos_session_id,
            request_id=request_id,
            sale_data=sale_data,
            payment_ref=sale_data['gateway_ref']
        )
    
    # 3. Process sale (create order, finalize ledger, etc.)
    try:
        sale = process_pos_sale(
            dealer_id=dealer_id,
            sale_data=sale_data,
            idempotency_key=f"{dealer_id}:{request_id}"
        )
        pending.request_state = 'server_confirmed'
        pending.server_confirmed_at = now()
        db.commit()
        return { sale_id: sale.id, status: 'confirmed' }
    except Exception as err:
        pending.request_state = 'failed'
        pending.error_reason = str(err)
        db.commit()
        raise
```

**Admin Dashboard:**
- `GET /admin/pos/queue` — list all pending/failed requests
- `POST /admin/pos/queue/{id}/retry` — manual retry
- `POST /admin/pos/queue/{id}/discard` — discard (refund to customer)
- `GET /admin/pos/queue/{dealer_id}/snapshots` — view local queue snapshots

---

## ۲۴. پایان سند

این سند نتیجهی:
- ۳ دور Q&A با تیم Goldis Operations
- ادغام بهترین بخشهای پیشنهاد ChatGPT
- بازنویسی کامل مدل tenancy
- اضافه کردن Settlement، Fulfillment، POS بهعنوان bounded contexts درجهیک
- explicit کردن همه‌ی architectural decisions (تا LLM پیاده‌ساز مجبور به assumption نباشد)

پیاده‌سازی این پروژه با رعایت این سند، حدود **۱۲ هفته** برای فاز ۰ تا ۷ تخمین زده می‌شود (با فرض ۲-۳ مهندس async-experienced).

برای start، LLM پیاده‌ساز را با این prompt کوتاه ارسال کنید:

> «این سند معماری گلدیس هاب است. آن را بهطور کامل بخوان. قبل از کدنویسی، فایلهای talamala_v4/CLAUDE.md و talamala_pos/CLAUDE.md را هم بخوان. سپس فاز ۰ از بخش ۲۱ (Infrastructure) را مرحله‌به‌مرحله کد بزن. بعد از هر مرحله توقف کن و تأیید بگیر. ابهامات بخش ۲۰ که به فاز فعلی مربوط است را اول از من بپرس.»
