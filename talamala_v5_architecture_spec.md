# سند معماری TalaMala v5 — پلتفرم متمرکز چندبرندی فروش، خرید و مدیریت دارایی طلا

> **نسخه:** 2.4 (نهایی‌سازی implementation-safe — حذف ابهام‌های باقی‌مانده و ۸ اصلاح BLOCKER — 2026-05-18)
> **نسخه قبل:** 2.3 (بازبینیِ خارجی دوم + اصلاحاتِ P0 تکمیلی — 2026-05-18)
> **تاریخ:** 2026-05-18
> **وضعیت:** ✅ آماده برای پیاده‌سازی — implementation-safe (تمام P0/P1 + ۸ BLOCKER issue fixed)
> **منبع:** سه دور Q&A با تیم Goldis Ops + ادغام ChatGPT + DeepSeek review (۲ بار) + ۳۵ تصمیمِ اصلاحیِ بازبینی (D-46…D-80) + ۱۰ اصلاحِ P0/P1 schema

---

## ۰.۰ راهنمای داورِ خارجی (⚠️ قبل از هر بازبینی بخوان)

این سند پس از یک بازبینیِ عمیق **یکپارچه و تمیزسازی شده** (v2.1):

1. **بدنه‌ی سند نرماتیو و تمیز است** — مستقیماً مدلِ نهایی را می‌گوید (بدون متنِ خط‌خورده/منسوخ). آن را معتبر بخوان.
2. **§۲.۵ «دفترِ تصمیمات» (D-46…D-80) غیرنرماتیو است** — فقط *چراییِ* تغییرات برای حسابرسی. برای ساختِ سیستم به بدنه نگاه کن، نه این جدول.
3. همه‌ی `Q-01…Q-10` و نقاطِ `A-1…A-13` / `F-1…F-4` **حل شده‌اند** (نگاشتشان در §۲۰/§۲.۵).
4. **تمرکزِ بازبینی روی §۰.۱ (موارد باز) باشد** — تصمیماتِ §۲.۵ با تیم نهایی شده‌اند؛ بازنکن مگر یک **باگِ مالی/همزمانی/تفکیک‌وظایفِ اثبات‌پذیر** نشان دهی.

## ۰.۱ موارد باز / بازبینی‌نشده (تمرکزِ داور اینجا)

این‌ها هنوز عمیق بازبینی **نشده‌اند** و بیشترین ارزشِ بازبینیِ بیرونی را دارند:

- **عملیاتِ چندنقشیِ بازبینی‌نشده:** state machineِ بازخریدِ حضوری (§۱۲.۵.۲ب)، عملیاتِ تسویه‌ی بین‌شرکتی (§۶.۵)، intakeِ شمش از کارخانه (§۷.۳ + D-48)، برداشتِ ریال (§۱۲.۶)، آشتیِ تراکنشِ POS (§۹) — از منظرِ تفکیکِ وظایف و درگیریِ واحدهای مختلف.
- **هشدارِ scope (P۵ در §۲.۵):** زیرسیستمِ قیمت(D-65/72)+دفترکل(§۶)+خزانه(D-47/67)+نماینده(D-73) سنگین‌ترین و پرریسک‌ترین بخش است؛ تخمینِ ۱۲ هفته دیگر واقع‌بینانه نیست.
- **مواردِ تصمیم‌گرفته ولی فقط طرح‌وار (نیازمندِ طراحیِ تفصیلیِ پیاده‌سازی):** موتورِ resolutionِ نردبانِ قیمت + کمیسیون (D-65/73)، fallbackِ درگاه (D-63)، پیاده‌سازیِ چکِ inlineِ خزانه (D-47)، محاسبه‌ی دقیقِ گرد‌کردن/منبع‌قیمتِ تعهداتِ بین‌شرکتی.
- ابهاماتِ سطح‌۲ِ بازِ سند: `Q-05`(جزئیاتِ ریز)، و هر چیزی که در §۲۰ هنوز ✅ نخورده.

> **سؤالِ پیشنهادی به داور:** «با فرضِ اینکه §۲.۵ قطعی است، فقط روی بخش ۰.۱ و باگ‌های مالی/همزمانی/تفکیک‌وظایفِ کشف‌نشده تمرکز کن. تصمیماتِ §۲.۵ را بازنکن مگر باگِ مالیِ اثبات‌پذیر نشان دهی.»

---

## ۰. راهنمای استفاده از این سند

این سند **ورودی فاز پیاده‌سازی** است. هنگام استفاده با یک LLM به‌عنوان مهندس پیاده‌ساز:

1. کل این سند را یک‌بار به مدل بده تا context کامل بسازد.
2. **مرحله به مرحله** کد بخواه — نه یک‌جا. ترتیب پیشنهادی در بخش ۲۱ آمده.
3. هر تصمیم architectural اینجا **explicit** است — assumption نیست.
4. در فاز پیاده‌سازی، LLM باید قبل از کدنویسی هر context، فایل `talamala_v4/CLAUDE.md` و `talamala_pos/CLAUDE.md` را بخواند تا با current state آشنا شود.
5. ابهامات: همه‌ی Q-01…Q-10 در §۲۰ حل شده‌اند. مواردِ بازِ باقی‌مانده در **§۰.۱** فهرست شده — قبل از پیاده‌سازیِ context مربوطه باید حل شوند.

---

## ۱. خلاصه پروژه و دامنه

### ۱.۱. کسب‌و‌کار

TalaMala v5 یک **پلتفرم متمرکز چندبرندی** برای فروش، خرید و مدیریت دارایی طلا است. این سیستم جایگزین چند پروژه‌ی فعلی می‌شود:

- **talamala_v4** — backend فعلی FastAPI + Jinja2 + PostgreSQL در پروداکشن (با کاربر و دیتای واقعی)
- **talamala_pos** — Android/Kotlin frontend دستگاه POS

### ۱.۲. شخصیت‌های حقوقی (Companies)

| Company | نوع | نقش‌ها |
|---|---|---|
| **Goldis Co.** | operator + central hedging desk + multi-brand seller | مدیریت مرکزی پلتفرم (تیم فنی، حسابداری، نظارت)، **مرکز hedging** برای فروش‌های TalaMala (طلای خام را از بازار یا از AminZar می‌خرد و دوره‌ای به TalaMala تحویل می‌دهد)، **فروشنده‌ی واقعی** در brand های Goldis و AminZar (سایت `aminzar.com` را با اجازه‌ی AminZar Co. به‌عنوان brand بازاریابی می‌گرداند — مدیریت، فروش، سود مال Goldis است) |
| **TalaMala Co.** | factory + independent seller + brand owner | کارخانه‌ی تولید شمش (با brand TalaMala)، فروشنده‌ی مستقل از طریق سایت/POS/marketplace، گیرنده‌ی پول از فروش brand TalaMala به حساب خود، طرف hedging با Goldis (rial→Goldis ، gold از Goldis) |
| **AminZar Co.** | factory-only (supplier) | فقط کارخانه‌ی تولید شمش (با brand AminZar). شمش‌ها را با حاشیه‌ی سود به Goldis می‌فروشد. **هیچ کانال فروش مستقیم ندارد** — سایت `aminzar.com` را Goldis می‌گرداند (با اجازه). سود AminZar فقط در لحظه‌ی تحویل شمش به Goldis (با حاشیه روی قیمت خام) است. |

### ۱.۳. برندها (Brands)

| Brand | brand_owner | operator | payment_receiver (default) | seller_company (default) | producer (default) |
|---|---|---|---|---|---|
| Goldis | Goldis Co. | Goldis Co. | Goldis Co. | Goldis Co. | multi (Goldis/AminZar/TalaMala) |
| TalaMala | TalaMala Co. | Goldis Co. | TalaMala Co. | TalaMala Co. | TalaMala Co. (یا multi) |
| AminZar | AminZar Co. | Goldis Co. | **Goldis Co.** | **Goldis Co.** | AminZar Co. (یا multi) |

**نکته‌ها:**
- `brand_owner` = مالک علامت تجاری
- `operator` = کسی که سایت و عملیات backend را اداره می‌کند (همیشه Goldis در v1، طبق D-03)
- `payment_receiver` = پول مشتری به حساب کدام شرکت می‌رود
- `seller_company` = فروشنده‌ی حقوقی (صاحب موجودی فیزیکی). در brand AminZar چون Goldis میفروشد، `seller_company = Goldis`
- `producer` = پیش‌فرض تولیدکننده، ولی هر brand می‌تواند محصول چند producer را بفروشد (cross-brand sale طبق D-07)
- این مقادیر **default per brand** هستند ولی می‌توانند per `sales_channel` override شوند (مثلاً brand TalaMala روی DigiKala، payment_receiver به Goldis تنظیم می‌شود — بخش marketplace)

### ۱.۴. ابعاد یک سفارش

هر سفارش باید به این سؤال‌ها قطعی جواب بدهد:

| بُعد | پاسخ‌گو |
|---|---|
| از کدام brand فروخته شد؟ | `order.brand_id` |
| از کدام channel؟ | `order.sales_channel_id` |
| تولیدکننده‌ی محصول کیست؟ | `order.producer_company_id` (از bar/product می‌آید — صرفاً اطلاعاتی، تأثیر مالی ندارد در v1) |
| فروشنده‌ی حقوقی کیست؟ | `order.seller_company_id` (= صاحب موجودی فیزیکی که شمش از انبارش خارج شد) |
| operator کیست؟ | `order.operator_company_id` (همیشه Goldis در فاز ۱) |
| پول به کجا رفت؟ | `order.payment_account_id` → `payment_account.company_id` (= `seller_company` معمولاً) |
| تسویه hedging چی؟ | اگر `seller_company != Goldis` → یک جفت `inter_company_ledger` entry (rial + gold) به/از Goldis — D-06b |
| از کجا fulfill می‌شود؟ | `order.fulfillment_location_id` |

### ۱.۵. دامنه — IN scope

شمش فیزیکی، طلای دیجیتال، marketplace چندکاناله، wallet چنددارایی per-legal-entity، DealerNetwork، Treasury مرکزی، **Inter-Company Hedging Ledger** (real-time hub-and-spoke با Goldis در مرکز)، Accounting، Fulfillment عملیاتی، Realtime، Notification، Audit کامل، Pricing مرکزی با snapshot، **rial withdrawal** دومرحله‌ای، physical_purchase_from_wallet (به‌جای gold withdrawal)، **Buyback کامل (digital + cancel-before-delivery + physical حضوری)**.

> **خارج از scope v1:** gold withdrawal (جایگزین = physical_purchase_from_wallet)، refund (جایگزین = buyback)، profit_share/commission settlement.

### ۱.۶. دامنه — OUT of scope

- DCA دوره‌ای، نوسان‌گیری، PNL dashboard
- ارز/کریپتو
- زیورآلات سفارشی (شاید بعداً)
- ⚠️ **Jinja2 و server-side rendering** — کاملاً حذف می‌شود. فقط API.

---

## ۲. تصمیم‌های معماری اصلی

این تصمیم‌ها در سه دور Q&A با تیم نهایی شده‌اند. **هیچ‌کدام در فاز پیاده‌سازی نباید دوباره بحث شوند.**

| # | تصمیم | انتخاب نهایی | منبع |
|---|--------|----------------|----------|
| D-01 | سبک معماری | **Modular Monolith** با مرزهای bounded context صریح، آماده برای استخراج سرویس در آینده | تیم |
| D-02 | مدل multi-company | **One Platform / Multi Brand / Multi Company / Centralized Ops by Goldis** | تیم |
| D-03 | Operator مرکزی | همیشه Goldis در فاز ۱ — یک admin panel برای همه برندها | تیم |
| D-04 | Wallet scope | **سه کیفِ کاملاً ایزوله per wallet-scope** (goldis/aminzar/talamala) — جزئیات: D-46، §۴ | تیم |
| D-05 | KYC scope | **مشترک** — یک KYC، اسناد شاهکار یک‌بار، هر دو شرکت قبول می‌کنند | تیم |
| D-06 | Treasury scope | **مرکزی Goldis = Central Hedging Desk**. هر فروش (هر شرکت) trigger می‌زند به hedging: فروشنده اتومات از Goldis طلای خام معادل می‌خرد، و Goldis مسئول است از بازار خام بخرد و فیزیکی تحویل دهد. هر خرید Goldis از بازار → exposure کاهش. | تیم |
| D-06b | **Inter-Company Ledger (Hub-and-Spoke)** | هر فروش غیر-Goldis (payment به TalaMala/AminZar رفت) **دو obligation همزمان** ایجاد می‌کند: ۱) `Seller → Goldis: rial` به اندازه‌ی قیمت طلای خام در لحظه‌ی فروش، ۲) `Goldis → Seller: gold mg` به اندازه‌ی وزن خالص. یک طرف ledger همیشه Goldis است (Hub). تسویه دستی توسط اپراتور Goldis، rial سریع/روزانه و gold دوره‌ای فیزیکی. فروش‌های خود Goldis هیچ inter-company entry ندارند، فقط treasury exposure را افزایش می‌دهند. | تیم |
| D-06c | **Inventory ownership model** | هر `inventory_location` یک `owner_company_id` دارد. شمش‌های موجود در انبار هر برند **مال خود همان برند** هستند (قبلاً خریداری/تولید شده). **مدل consignment وجود ندارد**. مدل تأمین و توزیع شمش‌ها در بخش چرخه‌ی تولید توضیح داده می‌شود. | تیم |
| D-06d | **Gold settle بدون bar مشخص** | وقتی Goldis طلای خام را به TalaMala تحویل می‌دهد، فقط مقدار وزن (mg) ثبت می‌شود — نه bar خاص. اپراتور می‌گوید «۱۰g طلای خام تحویل دادم» و قدیمی‌ترین obligation ها FIFO settle می‌شوند. این طلای خام (گرانول/شمش بزرگ) برای hedging موجودی فروشنده یا تولید بعدی است، **نه refill همان شمش فروخته‌شده**. | تیم |
| D-07 | Cross-brand sale | **مجاز** — bar تولید TalaMala می‌تواند در brand Goldis فروخته شود (با settlement) | تیم |
| D-08 | Payment gateway | **per-brand** (با چند `payment_account`): Goldis IPG برای Goldis+AminZar، TalaMala IPG برای TalaMala | تیم |
| D-09 | Inventory location | **per legal-entity ولی fulfillment مرکزی** — انبار اصلی Goldis است، ولی bar می‌داند producer/owner کیست | تیم |
| D-10 | DealerNetwork | حفظ کامل + توسعه — per-company با opt-in | تیم |
| D-11 | POS as sales_channel | **first-class** — `channels.type='pos'` با terminal_id/payment_account اختصاصی | ChatGPT proposal |
| D-12 | Settlement context | **bounded context جدا** — محاسبه‌ی سهم/سود/طلب بین Goldis ↔ TalaMala ↔ AminZar | ChatGPT proposal + تیم |
| D-13 | Fulfillment context | **bounded context جدا** — task برای انباردار، pick/pack/handover | ChatGPT proposal |
| D-14 | Digital gold inventory | **بدون جدول جداگانه** — همان Treasury Position. (سقف با **D-47 دوطرفه شد**: `max_open_exposure_mg` + `max_short_exposure_mg` + چکِ inline) | معمار |
| D-15 | Marketplace integration | Adapter pattern با ۳ mode: push_managed / pull_only / bidirectional | معمار |
| D-16 | Withdrawal model (v1) | **فقط ریال** — `order_type=withdrawal_rial` + جدول `withdrawal_details` اختصاصی. gold withdrawal در v1 نداریم (D-31) | معمار + تیم |
| D-17 | Tech stack | Python 3.12+ / FastAPI / **SQLModel** / PostgreSQL 16+ / asyncpg / Alembic / Pydantic v2 | تیم + ChatGPT |
| D-18 | Async/Sync | **async-first** (تیم async-experienced) | تیم |
| D-19 | Frontend | **کامل جدا** — هر brand یک Next.js/SPA فرانت، admin panel جدا، POS Android. backend فقط REST API. | ChatGPT proposal + تیم |
| D-20 | Server | تک‌سرور Linux + systemd (مثل v4) با چند worker process مستقل | تیم |
| D-21 | Message broker | **Postgres Outbox** primary، Redis Streams **فقط** برای SSE fan-out و rate limit (اختیاری) | معمار |
| D-22 | Realtime | SSE در فاز ۱ (پشت nginx ساده‌تر) | معمار |
| D-23 | Migration از v4 | **Fresh start کامل** — هیچ data از v4 (wallet balance، order، KYC، dealer) به v5 منتقل نمی‌شود. v5 از صفر شروع می‌شود. v4 data و کاربران v4 خارج از scope طراحی v5 هستند. (تصمیم تیم) | تیم |
| D-24 | Compliance | شاهکار (موبایل + کد ملی) + OTP. AML/retention infrastructure-ready ولی feature بعداً | تیم |
| D-25 | Worker scheduler | **APScheduler در process جدا + asyncio loop**. نه Celery، نه Arq | معمار |
| D-26 | Source of truth | PostgreSQL برای همه‌چیز. هیچ state critical در Redis/Memory. | معمار |

### تصمیمات دور دوم Q&A (حل ابهامات O-01 تا O-20)

| # | تصمیم | انتخاب نهایی |
|---|--------|----------------|
| D-27 | Rounding policy | **floor به‌عنوان default**، قابل override per-formula در `channel_pricing_formulas.rounding_policy`. نکته: floor در دراز مدت به ضرر شرکت — تیم پذیرفت |
| D-28 | Price lock TTL | **۲ دقیقه default**، قابل override تا حداکثر ۵ دقیقه per channel/formula (`channel_pricing_formulas.lock_ttl_seconds`). متعادل با ریسک نوسان طلا |
| D-29 | AminZar wallet | **scope=aminzar کاملاً جدا و ایزوله** (در Goldis merge نمی‌شود) — D-46 |
| D-30 | Decimal precision | Standard: `rate=NUMERIC(20,2)`، `percent=NUMERIC(6,3)`، `coefficient=NUMERIC(8,4)`، `wage_value=NUMERIC(12,4)` |
| D-31 | **برداشت طلا** | **حذف کامل** — کاربر نمی‌تواند طلای دیجیتال را به‌صورت فیزیکی برداشت کند. به‌جای آن: فروش به ریال (digital_trade sell) یا خرید کالای فیزیکی با wallet XAU_MG |
| D-32 | **Refund/Buyback model** | **Refund نداریم. «cancel» نداریم.** Buyback فقط **۲ حالت**: (a) بازخریدِ تحویل‌نشده (آنلاینِ مستقل؛ فروشِ اصلی reverse نمی‌شود)، (b) بازخریدِ حضوری. «بازخریدِ دیجیتال» = همان `digital_trade sell`. در هر دو: وزن خالص طلا → wallet XAU_MG؛ `buyback_credit_rial` → wallet IRR فقط با ثبت‌مالکیت+OTP؛ اجرت/مالیات/سود می‌سوزد. جزئیات: D-53/D-58/D-59/D-68/D-70 | تیم |
| D-33 | Conversion mismatch | افزوده در wallet باقی می‌ماند (no auto-conversion) |
| D-34 | POS payment_account | **per-device** — هر دستگاه POS یک payment_account با terminal_id جدا |
| D-35 | Gift box | modifier جدا (جدول `gift_boxes` با FK به `order_items`) |
| D-36 | Catalog | **مرکزی + channel availability + bar serial pre-assignment**. کاربر admin یک‌جا همه محصولات تعریف می‌کند. شمش‌ها دونه‌دونه یا دسته‌ای به یک channel/فروشگاه pre-assign می‌شوند |
| D-37 | DigiKala adapter | mode = `push_managed` |
| D-38 | Settlement scope | منتفی — جایش `inter_company_ledger` real-time hub-and-spoke (D-06b) |
| D-39 | Profit share | **بدون profit share در v1**. هر فروشنده، کل سود فروش (اجرت + مالیات + اختلاف قیمت) را خودش نگه می‌دارد. Goldis فقط بابت hedging قیمت طلای خام را می‌گیرد و طلای خام را تحویل می‌دهد. تیم گفت: «بابت فروش کسی سودی به کسی نمی‌دهد» **⚠️ تفسیرش با D-65 دقیق شد:** profit-shareِ فروش نداریم، ولی قیمتِ عمده‌ی طلای Goldis (مبنای hedging = P_hedge) ذاتاً مارجینِ خودِ Goldis (پوششِ مالیات+حداقل‌سود) را دارد. |
| D-40 | Brand access | خودکار — frontend مشخص می‌کند کاربر کدام wallet/brand را می‌بیند. هیچ opt-in جدا |
| D-41 | Dealer multi-company | **مجاز** — unique بر `(company_id, user_id)`، نه فقط user_id |
| D-42 | Hedging | merge در Treasury با `source_type IN ('hedge_buy', 'hedge_sell')` — جدول جدا نداریم |
| D-43 | Observability | فاز ۱: structured JSON log → stdout → journalctl. فاز ۲: Loki/Grafana |
| D-44 | POS Android | **Greenfield** — نسخه قدیم هنوز پروداکشن نرفته. هیچ backward compat نیاز نیست |
| D-45 | SSE auth | JWT در httpOnly cookie |

### ۲.۵. دفترِ تصمیمات (Decision Log — D-46…D-80)

> **ماهیت:** این جدول **changelog/تاریخچه‌ی استدلال** است (چرا هر تصمیم گرفته شد) — برای حسابرسی و حافظه‌ی تیم. **بدنه‌ی سند از v2.1 تمیز بازنویسی شده و مستقیماً مدلِ نهایی را می‌گوید؛ دیگر برای رفعِ تناقض نیازی به مراجعه‌ی اجباری به این جدول نیست.** این جدول مرجعِ «چرا»ست، نه «چه». تصمیماتِ زیر با تیم نهایی شده‌اند و در پیاده‌سازی دوباره بحث نمی‌شوند.

| # | تصمیم | انتخاب نهایی | اثر روی |
|---|--------|----------------|----------|
| D-46 | **Wallet scope** (override D-04/D-29) | کیف‌پول per **wallet-scope** نه per legal-entity. سه scope: `goldis` / `aminzar` / `talamala`. هر سه **کاملاً ایزوله، بدون انتقال مستقیم** (AminZar حقوقاً زیر Goldis Co. ولی برای کاربر کیف جدا). کلید `asset_balances` و `wallet_ledger_entries` و `wallet_locks` بُعد `wallet_scope` می‌گیرد؛ `company_id` حفظ می‌شود (مشتق: goldis/aminzar→Goldis Co.، talamala→TalaMala Co.) برای حسابداری/دفترکل بین‌شرکتی. گزارش حسابداری باید بدهی scope=aminzar را از scope=goldis تفکیک کند. هجینگ بدون تغییر (فروش AminZar هنوز Goldis-side). | Wallet، Accounting، §۴ |
| D-47 | **Treasury سدِ سخت + سقف دوطرفه** | علاوه بر worker ۳۰s (که فقط هشدار/پشتیبان است)، در لحظه‌ی **هر** تراکنش (فروش+خرید، فیزیکی+دیجیتال+POS، بدون استثنا) یک چک inline همگام: اگر از سقف رد شود تراکنش **رد می‌شود**. سقف **دوطرفه per فلز**: `max_open_exposure_mg` (سمت فروش) + `max_short_exposure_mg` (سمت خرید/بازخرید/فروش کاربر). اپراتور هر دو را per فلز هر زمان تغییر می‌دهد، با audit_log. | Treasury، §۵ |
| D-48 | **Supplier purchase داخل scope** (override D-7.2) | خرید از کارخانه داخل سامانه است، به‌صورت جریانِ **فقط-طلا (بدون ریال)** روی همان batch preorder. Goldis به کارخانه می‌دهد: اصل طلا + معادل اجرت به طلا؛ کارخانه شمش حک‌شده/پلمب‌شده برمی‌گرداند. تعهد طلایی Goldis↔کارخانه روی همان `inter_company_ledger` با `asset='gold'`, `source_type='supplier_purchase'` رصد می‌شود (جدول جدید لازم نیست). `purchase_wage_percent` عملیاتی می‌شود (دیگر صرفاً metadata نیست). طلای اجرت = هزینه‌ی حسابداری، **بدون** اثر روی exposure/سقف خزانه. | Inventory، Inter-Company، Catalog، §۷.۲ |
| D-49 | **امانی = شمشِ مشخصِ allocated** (شفاف‌سازی مدل امانی — مستقل از Q-10 سند) | طلای امانی یعنی شمشِ مشخصِ سریال‌دار که از **لحظه‌ی خرید** به مشتری تخصیص و قفل می‌شود (allocated، نه pooled). عملیات کنترل‌شده‌ی **«تعویض شمش»** (سریال قدیم→جدیدِ هم‌وزن/هم‌عیار) برای موارد گم/آسیب، فقط اپراتور، با ثبت در `ownership_history` + `audit_logs`. | Fulfillment، Inventory، §۸ |
| D-50 | **Price-lock TTL** (override D-28) | بازه‌ی مجاز ۶۰–۳۰۰ ثانیه (CHECK از `BETWEEN 30 AND 300` به `BETWEEN 60 AND 300`)، پیش‌فرض ۱۲۰s. کف ۱ دقیقه برای شرایط پرنوسان. | Pricing، §۱۱.۴ |
| D-51 | **قرارداد عیار** | عیار همیشه **parts-per-1000** (عدد صحیح ۰..۱۰۰۰؛ ۱۸ع=۷۵۰، ۲۴ع=۹۹۹). فرمول وزن خالص همیشه `weight_mg × purity / 1000`. نمونه‌های `9999` در سند غلط‌اند و اصلاح می‌شوند. | Catalog، Pricing، همه‌ی محاسبات طلا |
| D-52 | **برداشت ریال** (تأکید) | در v1 **همه‌ی** برداشت‌های ریالی نیاز به تأیید دستی اپراتور دارند — هیچ آستانه‌ی auto-approve نیست. | Withdrawal، §۱۲.۶ |
| D-53 | **گیتِ مزیت بازخرید** (اصلاح D-32) | اجرت/مالیات/سود **همیشه** می‌سوزد. وزن طلای خالص **همیشه** به wallet XAU_MG برمی‌گردد (طلای واقعیِ اصالت‌سنجی‌شده — کاربر همیشه می‌تواند بفروشد). ولی `buyback_credit_rial` **فقط** وقتی پرداخت می‌شود که شمش در لحظه‌ی بازخرید به نام همان کاربر **ثبت مالکیت** شده باشد و با **OTP** واقعیت‌سنجی شود. ثبت‌نشده→صفر (می‌سوزد). ثبت تأخیری اگر قبل/حین بازخرید انجام و OTP تأیید شود، مزیت برقرار است. | Order/Buyback، §۱۲.۵.۲ |
| D-54 | **ثبت مالکیت per کانال** | آنلاین: خودکار در لحظه‌ی خرید (کد در پنل). POS: **موبایل‌محور** — نماینده موبایل (+کد ملی) را وارد می‌کند، کاربر پیدا/ساخته می‌شود، شمش به نامش ثبت، کد در پنل فعال؛ موبایل ندهد→ثبت‌نشده. Marketplace: **هرگز** ثبت نمی‌شود. **کارت هدیه: کاملاً بیرون از سیستم claim/ثبت** — نه `claim_code`، نه ثبت مالکیت، نه مزیت ریالی؛ حاملِ فیزیکی = مالک (ولی همچنان می‌تواند برای ارزش طلای خالص بازخرید حضوری کند). | Inventory، Order، POS |
| D-55 | **انتقال مالکیت** | برای شمش‌های ثبت‌شده، هر مالک می‌تواند به موبایل دیگری منتقل کند، با تأیید **OTP** + ثبت در `ownership_history` + `audit_logs`. مزیت `buyback_credit_rial` (از snapshot سفارش اول) **همراه شمش** به مالک جدیدِ ثبت‌شده منتقل می‌شود. | Inventory، Order |
| D-56 | **Marketplace انحصاراً Goldis** (حل خلأ §۱۲.۸) | Goldis **انحصاراً** همه‌ی فروش در بازارهای ثالث آنلاین (دیجی‌کالا/باسلام/…) را برای **همه‌ی** برندها در دست دارد؛ برندها حق ورود مستقیم به این بازارها ندارند. در marketplace همیشه `seller_company=Goldis` و `payment_receiver=Goldis`؛ هیچ ردیف بین‌شرکتی marketplace. سایت اختصاصی هر برند مستثناست (talamala.ir همچنان برند TalaMala با پول به TalaMala). | Marketplace، §۱۲.۸ |
| D-57 | **POS فقط انبار خودِ نماینده** (تأکید) | نماینده با POS فقط کالاهایی را که از قبل برای او تعریف و به انبار خودش ورود خورده می‌فروشد (نه pool مرکزی). | POS، §۱۲.۷ |
| D-58 | **«لغو» حذف — همه‌چیز Buyback** (override D-32 زیرflow a) | مفهوم cancel وجود ندارد. فروش اول **همیشه معتبر و کامل** می‌ماند (سود پیش فروشنده). اگر مشتری پشیمان شد، یک تراکنشِ **بازخریدِ مستقلِ روبه‌جلو** رخ می‌دهد (نه باطل‌کردن فروش). اقتصاد همیشه یکسان: اجرت/مالیات/سود می‌سوزد، وزن خالص→کیف XAU_MG، `buyback_credit_rial`→کیف IRR (با شرط D-53)، در scope برندِ فروش. سه **حالت عملیاتی** (نه مدل مالی متفاوت): (۱) تحویل‌نشده=آنلاین/اتومات، شمش به‌حالت قابل‌فروش، بدون state machine؛ (۲) تحویل‌شده=حضوری با state machine + اصالت‌سنجی؛ (۳) دیجیتال=فروش طلای دیجیتال کیف. زیرflow `cancel_before_delivery` با `Order.status=Cancelled` **منسوخ** است. | Order/Buyback، §۱۲.۵.۲ |
| D-60 | **حل Q-10 — منبع شمشِ physical_purchase_from_wallet** | شمش فیزیکی از موجودیِ **همان scope/برندِ کیف‌پول** برداشته می‌شود (نه انبار مرکزی Goldis). این جریان از نظر پول/برند/فروشنده دقیقاً مثل یک خرید فیزیکی عادی است؛ فقط ابزار پرداخت به‌جای ریال/درگاه، طلای کیف است → `seller_company`=همان scope، تعهد بین‌شرکتی طبق قاعده‌ی فروش غیر-Goldis. اگر شمش هم‌وزن در آن scope موجود نبود، خرید انجام نمی‌شود (سازگار با O-03). **مبنا:** طلای دیجیتال کاغذی نیست — هر خرید دیجیتال scope غیر-Goldis یک تعهد طلای واقعی از Goldis می‌سازد که Goldis دوره‌ای فیزیکی تحویل می‌دهد؛ پس انبار آن scope از همین مسیر پُر می‌شود. | Inventory، Treasury، §۱۲.۵، §۲۰ |
| D-61 | **حل Q-06 — مدل سطوح KYC در v1** | سه سطح: **L0** (فقط موبایل+OTP) → **هیچ تراکنش مالی** (فقط مرور/سبد/مشاهده قیمت؛ نه خرید، نه کیف‌پول، نه شارژ). **L1** (شاهکار موبایل↔کدملی منطبق + نام/کدملی) → سطح پایه‌ی معامله با سقف‌های محتاطانه. **L2** (L1 + احراز مالکیت حساب بانکی: تطبیق شبا↔کدملی + تأیید دستی اپراتور اختیاری) → سقف‌های بالاتر/سفارشی. اعداد سقف‌ها (۴ بُعد×روزانه/ماهانه) در `user_level_defaults` **اپراتور-تنظیم با audit**، نه hard-code در سند. آستانه‌های پیشرفته‌ی AML همان «فیچر بعدی» D-24 باقی می‌ماند. | KYC، §۱۱.۲، §۲۰ |
| D-62 | **حل Q-07 + انتقال انبار دومرحله‌ای** | **(الف)** هیچ TTL/بازتخصیصِ خودکار روی طلا نیست — فقط گزارش/هشدار **سن‌خوردگی** (شمش‌های راکد در یک کانال) و ابزار دستیِ اپراتور برای برداشتن/تغییر `assigned_channel_id` (با `inventory_movement`+audit). **(ب) انتقال بین انبارها = سند انتقال دومرحله‌ای** (الگوی WMS/ERP): `DRAFT → DISPATCHED (Goods Issue، اسکن سریالِ خروج، مبدأ کم) → RECEIVED (Goods Receipt، اسکن سریالِ ورود در مقصد) → COMPLETED`، شاخه‌ی `DISCREPANCY` برای مغایرت. موجودیِ در راه = **`inventory_location` مجازی با `location_type='in_transit'`** و پرچم غیرقابل‌فروش (هیچ‌جا reserve/فروش نمی‌شود تا رسید). **تفکیک وظایف:** فرستنده ≠ گیرنده؛ هر مرحله audit + `inventory_movement` per شمش. **v1:** اسکن دوطرفه + تفکیک وظایف + audit + **OTP تحویل اجباری** بین مبدأ/مقصد + هشدار «گیرکرده در راه»؛ بارنامه/پیک/بیمه = metadata اختیاری. آستانه‌های سن‌خوردگی/گیرکرده **اپراتور-تنظیم با audit**. ارتقای `DealerTransfer`/`ReconciliationSession` v4. | Inventory، Fulfillment، §۱۱.۵، §۲۰ |
| D-63 | **حل Q-08 — انتخاب درگاه (per-channel، بدون انتخاب کاربر در v1)** | هر `sales_channel` یک **لیست اولویت‌دار از `payment_account`ها** دارد. موقع پرداخت، اولین درگاهِ **فعال و سالم** خودکار انتخاب می‌شود؛ اگر down بود **fallback خودکار** روی درگاه بعدیِ لیست. کاربر هیچ انتخابی نمی‌بیند (multi-PSP UX به v2 موکول؛ مدل طوری بماند که بعداً بدون تغییر اضافه شود). اپراتور می‌تواند per `payment_account` «موقتاً غیرفعال» کند. **الزامی:** هر بار درگاهی خطا/down تشخیص داده شد (حتی اگر fallback پوشش داد) → **اطلاع‌رسانی به اپراتور/ادمین** (notification + audit) که کدام PSP مشکل دارد. | Payment، §۱۱.۷، §۲۰ |
| D-64 | **حل Q-09 — برداشت فقط به حساب خودِ کاربر** | برداشت ریال **فقط** به حساب بانکیِ متعلق به همان کاربر مجاز است: نام صاحب شبا باید با کد ملیِ KYC تطبیق داده شود (`user_bank_accounts.is_verified=TRUE` از طریق استعلام بانکی/شاهکار). برداشت به حساب شخص دیگر **ممنوع** — شرط صریح سازمان مبارزه با پول‌شویی (ضد الگوی واریز-کارت-A / برداشت-حساب-B). دولایه با D-52 (احراز سیستمی + تأیید اپراتور). اشخاص حقوقی (حساب به‌نام شرکت) **خارج از scope v1**، موکول به v2/onboarding دستی. | Withdrawal، Compliance، §۱۱.۱، §۲۰ |
| D-65 | **نردبانِ قیمت + بُعدِ سطح (حل A-1/A-2، اصلاح تفسیر D-39)** | **نقاط قیمتیِ نام‌دار per فلز در لحظه:** `P0`=`internal_base_price` (هزینه‌ی مرجعِ خام، داخلی، بی‌سود) → `P_hedge`=قیمتِ عمده‌ی Goldis = P0 + حداقل‌مارجینِ Goldis که **تضمیناً ≥ مالیاتِ دولت + حداقل سود** → `P_partner(tier)` (هر `DealerTier` یک عدد، همیشه ≥ P_hedge) → `P_retail` (مشتریِ نهاییِ پیش‌فرض، بالاترین). **هیچ‌کس زیر P_hedge نمی‌خرد؛ Goldis هرگز بی‌سود/زیرِمالیات نمی‌فروشد.** **بُعدِ سطح:** ستونِ `dealer_tier_id BIGINT NULL` به `channel_pricing_formulas` (رزولوشن با همان `priority`؛ `NULL`=مشتریِ نهایی). v1 فقط مشتریِ نهایی + سطوحِ همکار/نماینده (VIPِ خرده به v2). برای **طلای دیجیتال** (بدون اجرت) تمایزِ سطح کاملاً در مارجینِ متالِ فرمول است (شکافِ مدلِ اجرت‌محورِ v4 رفع شد). **Invariant:** هم موقع ذخیره‌ی فرمول هم موقع ساخت price_lock باید خروجی ≥ P_hedge ≥ (P0+مالیات+حداقل‌مارجین)؛ نقض ⇒ رد/clamp + هشدار اپراتور. P_hedge **یک نقطه‌ی per-فلز در سطح شرکت Goldis** (نه per کانال) تا ریاضیِ بین‌شرکتی یکدست بماند. **حل A-1:** تنها مبنای `inter_company_ledger` = `order_items.raw_hedge_price_rial` = `P_hedge_per_mg(لحظه‌ی فروش) × pure_gold_mg`؛ §۱۲.۱ گام d/e اصلاح، خطوط «cost transfer reverse» منسوخ. **`cost_price_rial` → نام/تعریف `raw_hedge_price_rial`؛ `supplier_price_rial` حذف** (بی‌مصرف بعد از D-48). **اصلاح تفسیر D-39 (نه نقض):** «بابتِ فروش profit-share نیست» سرجایش است؛ ولی قیمتِ عمده‌ی طلای Goldis ذاتاً مارجینِ خودِ Goldis (پوششِ مالیات+حداقل‌سود) را دارد — این دو سازگارند. | Pricing، Inter-Company، Catalog، §۵، §۶.۴، §۱۱.۴، §۱۱.۶، §۱۲.۱ |
| D-75 | **حل A-11 — بسته‌بندی/جعبه‌ی هدیه = کالای ریالیِ جدا** | بسته‌بندی یک کالای جدا با قیمتِ ریالیِ مستقل است که فقط در صورتِ خواستِ مشتری به سفارش اضافه می‌شود (D-35/v4). مرزها: (۱) **صرفاً ریالی** — نه طلا، نه `pure_gold_mg`؛ وارد نردبانِ D-65 نمی‌شود، exposure خزانه نمی‌سازد، تعهدِ بین‌شرکتی ندارد. (۲) در بازخرید **برنمی‌گردد** (مثل اجرت می‌سوزد — D-53). (۳) پرداختش **همیشه ریالی** است؛ حتی در `physical_purchase_from_wallet` سهمِ بسته‌بندی از کیفِ ریالی/درگاه، نه طلای کیف. (۴) پولش به scope فروشنده می‌رود؛ هیچ ردیفِ بین‌شرکتی ندارد. (۵) **خارج از مبنای کمیسیونِ نماینده** (D-73 بندِ۵؛ مبنا فقط `pure_gold_mg`). | Catalog، Order، Pricing، §۱۱.۶ |
| D-80 | **حل F-4 — مرزِ Fulfillment ↔ انتقالِ داخلی (D-62)** | مرز بر اساسِ «مشتری درگیر است یا نه»: **fulfillment = فقط جابه‌جاییِ گره‌خورده به سفارشِ مشتری** (همیشه `order_id` دارد — تحویلِ حضوری/پیک/فروشگاه). **همه‌ی انتقال‌های داخلیِ بینِ انبارها (بدونِ مشتری) فقط از مسیرِ دومرحله‌ای D-62.** مقصدِ `internal_transfer` از `fulfillment_tasks` **حذف**. اتصال: اگر شمشِ موردِ تحویل در انبارِ دیگری است، **اول** انتقالِ D-62 (مرکزی→محلِ تحویل)، **بعد** taskِ fulfillment در مقصد — پشتِ‌سرِ هم، نه موازی. یک مفهوم/یک سیستم؛ بدونِ گزارشِ دوگانه. | Fulfillment، Inventory، §۸ |
| D-79 | **حل F-3 — مسیرهای استثنای تحویل (گم/پس‌زده/آسیب)** | به `fulfillment_tasks.status` اضافه می‌شود: **`delivery_failed`** (پیک نتوانست/مشتری پس زد/آدرس غلط) → شمش با همان فرایندِ دومرحله‌ای D-62 (in-transit + اسکنِ ورود) به انبار برمی‌گردد؛ تا برنگشته «در راهِ برگشت». **`lost_in_transit`** (گم/دزدیده) → رویدادِ زیان: عملیات ادعا از پیک، حسابداری ثبتِ زیان (audit + accounting)، **خزانه: یک پایِ جبرانیِ exposure** (طلا فروخته/هج‌شده ولی فیزیکش نیست). **`damaged`** (پلمب‌شکسته) → برمی‌گردد + شمش «نیازمندِ بازرسی» (پلمب/ذوبِ مجدد) — مستقیم قابلِ فروشِ دوباره نیست. هیچ‌کدام **خودکار** بسته نمی‌شوند؛ تصمیمِ اپراتور/حسابدار + audit + reason الزامی. تا روشن‌شدنِ سرنوشت، شمش نه «فروشِ تمام‌شده» نه «موجودِ انبار» — حالتِ معلقِ «زیانِ در حالِ بررسی» با اثرِ خزانه‌ای. | Fulfillment، Treasury، Accounting، §۸ |
| D-78 | **حل F-2 — اثباتِ تحویل با OTP + تفکیکِ نقش** | انباردار فقط `handed_over` را می‌زند («از دستِ ما خارج شد»، نه «رسید»). `delivered` **فقط با OTPِ گیرنده** بسته می‌شود (+ اسکنِ سریال در تحویلِ حضوری)، و **توسطِ انباردارِ مبدأ بسته نمی‌شود** — نقشِ مقصد (پیک‌تأیید/کارمندِ فروشگاه/نماینده) در `delivered_confirmed_by`. `delivery_otp_hash`+`delivery_otp_expiry` (مثل v4) به `fulfillment_tasks` برمی‌گردد. تا قبل از تأیید، شمش «در حالِ تحویل»؛ `bar.delivered_at` فقط در لحظه‌ی تأییدِ واقعی ست می‌شود (نه موقعِ handover). تفکیکِ وظیفه: درآورنده‌ی شمش از انبار ≠ بندنده‌ی «تحویل‌شده». | Fulfillment، §۸ |
| D-77 | **حل F-1 — fulfillment_task: شمشِ مشخص + trigger=درخواستِ تحویل** | (۱) `fulfillment_tasks` ستونِ `bar_id` می‌گیرد (به شمشِ تخصیص‌یافته‌ی D-49 اشاره می‌کند؛ برای چند شمش، چند ردیف). انباردار **همان سریال** را برمی‌دارد؛ **اسکنِ سریالِ pick اجباری** و باید با `bar_id` بخواند وگرنه خطا — تضمینِ بستنِ «تخصیص‌دهنده‌ی فروش» و «انباردار» به یک سریالِ واحد. (۲) trigger ساختِ task = **«درخواستِ تحویل»** است، نه «پرداختِ سفارش». فروشِ امانی (`delivered_at=NULL`) **هیچ taskی نمی‌سازد** (شمش در خزانه قفل). فقط با درخواستِ تحویلِ مشتری یا تحویلِ فوریِ POS/فروشگاه task ساخته می‌شود (برگشتِ مفهومِ `CustodialDeliveryRequest` v4 که در §۸ گم بود). | Fulfillment، Inventory، §۸، §۱۲.۱ |
| D-76 | **حل A-12 — تاپ‌آپ به scope درست (ایزوله)** | `wallet_topup` بُعدِ `wallet_scope` می‌گیرد؛ از **فرانت/کانال** resolve می‌شود (talamala→talamala، goldis→goldis، aminzar→**aminzar**) و کیفِ ریالیِ همان scope شارژ می‌شود. سه فرانت کاملاً **ایزوله** (D-46): امین‌زر در goldis merge **نمی‌شود**، هرچند legal entityِ هر دو Goldis Co. و درگاهِ شارژش Goldis IPG است (`company_id` مشتق از scope فقط برای حسابداری). متنِ قدیمیِ §۱۲.۵.۴ که «گلدیس/امین‌زر → wallet Goldis» می‌گفت اصلاح شد. **یادآوریِ کلی:** هر فرانت (فعلاً ۳ تا) همه‌چیزش — کیف، تاپ‌آپ، بازخرید، گزارش — ایزولهٔ همان scope است. | Wallet، Payment، §۱۱.۷، §۱۲.۵.۴ |
| D-74 | **حل A-13 — نقره (XAG) خارج از scope v1** | در v1 **هیچ ورودی به نقره** نداریم: نه محصولِ نقره، نه قیمت‌گذاری/فرمولِ نقره، نه trade/POS/بازخریدِ نقره. اول کلِ زنجیره‌ی **طلا** بی‌نقص نهایی شود؛ سپس **عیناً همان روال** برای نقره تکرار می‌شود. **ساختار باید metal-generic بماند** (asset `XAG_MG`، `metal_type`، `PRECIOUS_METALS`، خزانه/قیمت per-metal فقط به‌عنوان نقطه‌ی توسعه نگه داشته شوند — حذف نشوند)، ولی هیچ مسیرِ فعالِ نقره در v1 ساخته/seed/نمایش داده نشود. همه‌ی D-46…D-73 metal-generic‌اند و موقعِ افزودنِ نقره بدون بازطراحی اعمال می‌شوند. | Catalog، Pricing، Treasury، Wallet، سراسری |
| D-73 | **مدلِ نهاییِ نماینده (تخت، بدون شبکه) + اصلاحاتِ P۱–P۴** | **۱)** POS = فروشِ برندِ TalaMala (v1 همه TalaMala)؛ پول→TalaMala (نه نماینده)؛ هجِ خودکار با Goldis مبنای P_hedge (§۶/D-69). **۲)** نماینده = فقط مکان/اپراتور (نه مالکِ موجودی، نه دریافت‌کننده‌ی پول). **۳)** پاداشِ نماینده = کمیسیونِ طلاییِ جدا از TalaMala (از حاشیه‌ی خودش)، دو نرخ: فروش و بازخرید — نه gapِ نردبان (A-10 حل). **۴)** جدولِ `dealer_commission_rates` (محصول/نوع، `dealer_tier_id` NULL=همه، `trade_side` sale|buyback) → درصدِ طلایی؛ پیش‌فرضِ محصول + override سطح؛ رزولوشن مثلِ D-65. **۵)** مبنای درصد = `pure_gold_mg`ِ تراکنش در لحظه‌ی فروش (Gold-for-Gold)، نه ریال. **۶)** نگهبانِ فروش: Σکمیسیون ≤ `P_retail−P_hedge`. **۶ب (P۲):** نگهبانِ بازخرید جدا: کمیسیونِ بازخرید ≤ اسپردِ بازخرید؛ نقض → رد/هشدارِ اپراتور. **۷)** کمیسیونِ بازخرید فقط بعد از `AuthenticityVerified` (D-53)، نه قبلش. **۸ (P۱ اصلاح‌شده):** تسویه روی **`dealer_commission_ledger` جدا** (بدهیِ طلاییِ TalaMala→نماینده، Gold-for-Gold، دوره‌ای) — **نه** روی `inter_company_ledger` (آن شرکت↔شرکت است و نماینده کاربر است؛ آلودنِ گزارشِ هجینگ ممنوع). رکورد روی `DealerSale`+`metal_profit_mg`. **۹)** `SubDealerRelation` و هر مفهومِ زیرنماینده/شبکه‌ای/MLM/ارتقای‌تیمی **از کلِ scope v5 حذف** (نه v1 نه v2 نه زیرساخت)؛ شبکه تخت. **۱۰ (P۴):** `P_partner`/`dealer_tier_id` (D-65) در v1 فقط **زیرساختِ خالی** است — مسیرِ فعالِ «همکار برای خودش می‌خرد» نداریم؛ فعال‌شدن=آینده. **P۳:** کمیسیونِ طلاییِ واریزی به کیفِ نماینده = طلای دیجیتالِ جدید ⇒ یک پایِ خزانه‌ای `+pure_gold_mg` می‌سازد و تابعِ سقف‌های D-47 است. | Dealer، Pricing، Treasury، §۹، §۱۱.۵، §۱۲.۷، context۱۵ |
| D-72 | **حل A-9 — کارمزدِ معامله‌ی دیجیتال = مارجینِ نردبان + spreadِ دوطرفه** | (الف) «کارمزدِ معامله‌ی دیجیتالِ نقش‌محورِ v4» (`gold_fee_customer/dealer_percent`…) مفهومِ جدا **نیست** — همان فاصله‌ی نردبانِ D-65 است (`P_retail−P_hedge` مشتری، `P_partner−P_hedge` همکار). افزونگیِ مدلِ v4 حذف. (ب) `channel_pricing_formulas` بُعدِ `trade_side VARCHAR(10) NULL` (buy|sell|NULL) می‌گیرد تا **spreadِ دوطرفه** ممکن شود: قیمتِ خرید (کاربر می‌خرد) و قیمتِ فروش (کاربر می‌فروشد) مارجینِ مستقل دارند؛ رزولوشن با همان `priority`. Invariantِ D-65 هر دو سمت: قیمتِ خرید ≥ P_hedge؛ قیمتی که به فروشنده‌ی کاربر می‌دهیم ≤ P_hedge (حاشیه منفی نشود). قیمتِ `digital_trade sell` (= همان «بازخریدِ دیجیتال» D-68) از فرمولِ `trade_side=sell` می‌آید. | Pricing، Wallet، §۱۱.۴ |
| D-71 | **حل A-8 — برچسبِ scope روی شمش (`sale_wallet_scope`)** | `bars` ستونِ `sale_wallet_scope VARCHAR(20) NULL` می‌گیرد: در لحظه‌ی فروش از scopeِ سفارش (goldis/aminzar/talamala) پر و **IMMUTABLE** (انتقالِ مالکیت — D-55 — عوضش نمی‌کند، چون حساب به فروشِ اول گره خورده). همه‌ی مسیرهای بازخرید/انتقال/گزارشِ تفکیکیِ D-46 از این برچسب تصمیم می‌گیرند، نه استنتاجِ ضمنی. شمشِ فروش‌نرفته=`NULL` (مالکیتِ شرکتی). برای کارت‌هدیه/مارکت‌پلیس (بدون ثبت‌مالکیت — D-54): `sale_wallet_scope` پر می‌شود (برای خزانه/بین‌شرکتی) ولی `customer_id=NULL` — دو بُعدِ مستقل. **قاعده:** بازخریدِ آنلاین فقط در همان scope/وب‌سایتی که خرید انجام شده مجاز است. | Inventory، Wallet، Buyback، §۱۱.۵ |
| D-70 | **حل A-7 — تعهدِ بین‌شرکتیِ digital_trade sell غیر-Goldis** | جمله‌ی مبهمِ §۱۲.۴ («Settlement: Goldis طلب از TalaMala») با مدلِ صریح جایگزین شد. scope غیر-Goldis: جفتِ تازه‌ی مخالفِ فروش → `TalaMala→Goldis طلا amount_mg` + `Goldis→TalaMala ریال P_hedge_per_mg×amount_mg`. scope=Goldis: هیچ تعهد بین‌شرکتی، فقط خزانه‌ی `−` تک‌پاییِ `digital_sell` (D-67). آینهٔ دقیقِ §۱۲.۳/D-69 و همان مسیرِ یکتای D-68. مابه‌التفاوتِ (P_hedge − پرداختی به کاربر) حاشیه‌ی scope فروشنده. | Inter-Company، Treasury، §۱۲.۴ |
| D-69 | **حل A-6 — یکدستیِ digital_trade buy غیر-Goldis با §۱۲.۱** | §۱۲.۳ اصلاح: مبنای تعهدِ بین‌شرکتیِ خرید دیجیتالِ scope غیر-Goldis = **`P_hedge_per_mg × amount_mg`** (D-65)، نه `internal_base_price` و نه قیمتی که کاربر پرداخت. صریح: خرید دیجیتالِ scope غیر-Goldis از نظر خزانه/بین‌شرکتی **هم‌سنگِ فروشِ فیزیکیِ غیر-Goldis** است (همان مدلِ §۱۲.۱)؛ تنها تفاوت: شمش/اجرت ندارد و خزانه‌اش تک‌پاییِ `digital_buy` است (D-67). مابه‌التفاوتِ (قیمتِ کاربر − P_hedge) سودِ scope فروشنده. §۱۲.۲ (AminZar، Goldis-side) بدون تعهد بین‌شرکتی — تأیید شد. | Inter-Company، Treasury، §۱۲.۲، §۱۲.۳ |
| D-68 | **حل A-5 — یکی‌سازی digital_buyback با digital_trade sell** | «بازخریدِ دیجیتال» یک مسیرِ فنیِ جدا **نیست** — صرفاً همان **`digital_trade` با `trade_side=sell`** است (نامِ بازاریابی). زیرflow (c) `digital_buyback` **حذف** می‌شود. در نتیجه Buyback فقط **۲ حالت** دارد (نه ۳): تحویل‌نشده + حضوری — هر دو مرتبط با شمشِ فیزیکی (D-58/D-59). منسوخ‌ها: `order_type=buyback` فقط برای فیزیکی؛ endpointهای `/buyback/quote` و `/buyback/digital` حذف → استفاده از `/wallet/trades/sell`؛ رویدادِ `DigitalBuybackCompleted` حذف = `DigitalGoldSold`؛ در §۵.۲ مدخلِ `digital_buyback` صرفاً **مترادفِ `digital_sell`** است؛ بندِ «(c)» در D-32/§۱۲.۵.۲/Q-03/roadmap منسوخ. قیمتِ فروشِ دیجیتال از نردبانِ D-65 سمتِ فروش می‌آید (همان نقشی که `buyback_quote` ادعا می‌کرد). | Order، Wallet، Treasury، §۵.۲، §۱۲.۴، §۱۲.۵.۲، §۱۳، §۱۴ |
| D-67 | **حل A-4 — بازنویسی §۵.۲ به مدلِ تک‌پایی/دوپایی** | `treasury_positions` per **پای** ثبت می‌شود نه per تراکنش؛ علامت از پای می‌آید نه `source_type`. تک‌پایی: `+`=`order_physical`/`pos_sale`/`marketplace_sale`/`digital_buy`؛ `−`=`hedge_buy`/`digital_sell`/`digital_buyback`. دوپایی (net≈صفر): `buyback` تحویل‌نشده/حضوری (D-59) و `physical_purchase_from_wallet` (D-66). برچسبِ ثابتِ `−` برای `buyback`/`physical_purchase_from_wallet` در §۵.۲ قدیمی **همان باگِ تک‌پایی** بود که پیاده‌ساز به آن استناد می‌کرد. | Treasury، §۵.۲ |
| D-66 | **حل A-3 — physical_purchase_from_wallet دوپایی** (آینهٔ D-59) | خرید کالای فیزیکی با کیف = تبدیلِ digital→physical. دو پای مستقل: پای۱ `−gold_part_mg` (مصرفِ طلای دیجیتالِ کیف)، پای۲ `+pure_gold_mg` (خروجِ شمشِ فیزیکی = فروشِ فیزیکی). **خزانه‌ی خالص ≈ صفر**، نه `−gold_part_mg`. اگر فروش غیر-Goldis بود، تعهدِ بین‌شرکتیِ پای۲ مثل هر فروشِ فیزیکی با مبنای P_hedge (D-65). متنِ §۱۲.۵ که فقط `delta=-gold_part_mg` داشت **باگ** بود (شمشِ هج‌نشده از سیستم خارج و exposure گم می‌شد). | Treasury، Inter-Company، §۱۲.۵ |
| D-59 | **حل Q-05 — بازخرید فروش را معکوس نمی‌کند** | بازخرید **هرگز** تعهدهای بین‌شرکتیِ فروشِ اصلی را معکوس نمی‌کند (`reverses_ledger_id` برای فروش استفاده نمی‌شود). هر بازخرید **دو پای مستقل** دارد: پای۱ طلا به کیف کاربر (+pure_gold_mg)، پای۲ منبع (شمش فیزیکی برمی‌گردد یا طلای کیف مصرف می‌شود، −pure_gold_mg). نتیجه: **تحویل‌نشده/حضوری = تبدیل physical↔digital ⇒ خزانه ≈ صفر، هیچ جفت تعهد طلاییِ تازه‌ای، فقط `buyback_credit_rial` به‌عنوان هزینه‌ی ریالی ثبت می‌شود.** **دیجیتال = خروج واقعی طلا ⇒ خزانه −pure_gold_mg + یک جفت تعهد تازه‌ی مخالف (TalaMala→Goldis طلا، Goldis→TalaMala ریال) به قیمت خامِ لحظه‌ی بازخرید.** این، باگِ ضمنیِ «buyback → −pure_gold_mg» در §۵.۲/§۱۲.۵.۲ را برای حالت‌های فیزیکی/تحویل‌نشده تصحیح می‌کند (دوبار-حساب). جزئیات گرد‌کردن/منبع‌قیمت به فاز پیاده‌سازی. | Inter-Company، Treasury، §۵.۲، §۱۲.۵.۲ |
| D-81 | **P0-1.1 — اصلاحِ wallet_topups idempotency constraint** | `wallet_topups` UNIQUE constraint نادرست بود: `UNIQUE (company_id, idempotency_key)`. دلیل نادرستی: scope aminzar و scope goldis هر دو به Goldis Co. نقشه می‌شوند (legal entity یکسان)؛ اگر دو کاربر از scopes متفاوت با idempotency_key یکسان شارژ کنند، یکی reject می‌شود (نادرست). **اصلاح:** `UNIQUE (wallet_scope, user_id, idempotency_key)` — هر کاربر در هر scope یک فضای idempotency جدا دارد. | Wallet، P0-1.1 |
| D-82 | **P0-7 — Hedge Buy flow (خرید طلای خام از بازار)** | Goldis Central Hedging Desk در پاسخ به فروش‌های غیر-Goldis (scope=TalaMala یا aminzar)، طلای خام از بازار می‌خرد و دوره‌ای تحویل می‌دهد. این flow با bulk_gold_inventory (P0-8) و inter-company settlement مرتبط است. **موارد:** ۱) API `/admin/treasury/hedge-buy/request` برای تسجیل خرید. ۲) وزن و پرایس ثبت می‌شود. ۳) Treasury exposure نسبت به سقف‌های D-47 چک می‌شود. ۴) Settlement دوره‌ای: operator تحویل طلا به creditor company را آپروو می‌کند. ۵) هر settlement یک inter_company_ledger entry می‌سازد (`source_type='hedge_buy_settlement'`). | Treasury، Inventory، Inter-Company، §۱۲.۵.۳ الف، D-47 |
| D-83 | **P0-8 — Bulk Gold Inventory (طلای خام بی‌سریال)** | جداول جدید برای ذخیره‌ی طلای خام (granules، ingots، سقط scrap) که سریال‌دار نیستند و به صورت وزن (mg) ثبت می‌شوند. **موارد:** ۱) `bulk_gold_inventory`: مالکیت، موقعیت، وزن کل، عیار، منبع (hedge_buy، supplier_purchase، etc.). ۲) `bulk_gold_movements`: ledger حرکات وزن (intake، withdrawal، conversion، recount). ۳) با `bars` table هیچ تضادی ندارد: bar برای شمش سریال‌دار است؛ bulk برای خام است. | Inventory، §۱۱.۵، D-82 related |
| D-84 | **P0-9 — Commission gold exposure offset (dealer commission settlement)** | وقتی نماینده commission طلاییِ (gold-for-gold) TalaMala دریافت می‌کند (wallet deposit XAU_MG)، یک پای خزانه‌ای +pure_gold_mg می‌سازد (dealer حالا طلا دارد، exposure افزایش یافت). **این باید offset شود** اگر commission از منبع TalaMala بود: یک inter_company_ledger entry ریاضی‌ای بین TalaMala و Goldis قدیمی‌ترین hedge obligation را می‌پوشاند (TalaMala debt←Goldis، gold credit←Goldis). **علت:** اگر offset نباشد، TalaMala طلا داده (treasury −) ولی مقابل‌رقم (hedged liability) قید نشده (mismatch). شامل D-73، D-82 (Hedge Buy)، و inter-company settlement logic. | Treasury، Dealer، Inter-Company، D-73 P۳، D-82 |

> **⚠️ اثر روی scope/تخمین:** D-47، D-48 و D-53 scope را سنگین‌تر کرده‌اند (supplier_purchase داخل؛ سقف دوطرفه؛ گیت ثبت‌مالکیت). D-58/D-59 و حذفِ SubDealer/MLM (D-73) برعکس **ساده‌تر** کرده‌اند. **هشدارِ P۵:** زیرسیستمِ **قیمت(D-65/72) + دفترکل(§۶) + خزانه(D-47/67) + نماینده(D-73)** الان سنگین‌ترین و پرریسک‌ترین بخشِ پروژه است (باگ = ضررِ مالیِ مستقیم). توصیه: در پیاده‌سازی **اول یک پروتوتایپِ end-to-end از همین زنجیره با تست‌های پولیِ واقعی** ساخته شود، نه CRUDهای ساده. تخمین ۱۲ هفته‌ی بخش ۲۲ دیگر واقع‌بینانه نیست و باید بازبینی شود.

## ۲.۶. اصلاحات P0 — Schema Implementation Fixes (نسخه ۲.۳)

### ۲.۶.۱ اصلاحات P0 در v2.2 (بازبینیِ ChatGPT + DeepSeek اول)

| Fix | موضوع | اصلاح |
|---|---|---|
| P0-1 | wallet_scope missing from ledger/locks | `wallet_ledger_entries` و `wallet_locks` ستونِ `wallet_scope VARCHAR(20)` اضافه شدند. UNIQUE constraint هم scope-keyed: `UNIQUE (wallet_scope, user_id, idempotency_key)` (§۴.۳) |
| P0-2 | payments.order_id NOT NULL but topup has no order | `payments.order_id` را `NULLABLE` کردیم (برای topup payments که order ندارند) (§۱۱.۷) |
| P0-3 | sales_channels missing seller/payment receiver columns | `seller_company_id` و `payment_receiver_company_id` به `sales_channels` اضافه شدند (§۳.۲) — D-56 marketplace override require میکند |
| P0-4 | physical_purchase_from_wallet calculates with product.weight_mg not pure_gold_mg | محاسبهٔ treasury و wallet lock از `pure_gold_mg = weight × (purity / 1000)` استفاده می‌کند، نه `weight_mg` مستقیم (§۱۲.۵ گام ۳) — purity factor الزامی برای درستی |
| P0-5 | treasury concurrency: no SELECT FOR UPDATE lock | توضیح اضافه شد (§۱۲.۱۰ و context service layer): checkpoint validation و `SELECT ... FOR UPDATE` درون transaction checking (implementation detail) |
| P0-6 | inter_company_ledger creation دقیق‌تر شد | §۶.۴: هر فروشِ غیر-Goldis دقیقاً دو ردیف ledger (rial+gold) می‌سازد، ایجاد شده در سمت یک transaction (بدون دوبار‌شماری) |

### ۲.۶.۲ اصلاحات P0 در v2.3 (بازبینیِ DeepSeek دوم — 2026-05-18)

| Fix | موضوع | اصلاح |
|---|---|---|
| P0-1.1 | wallet_topups idempotency scope bug | `wallet_topups` ستونِ UNIQUE constraint تغییر: `UNIQUE (company_id, idempotency_key)` ❌ → `UNIQUE (wallet_scope, user_id, idempotency_key)` ✅. دلیل: goldis+aminzar هر دو Goldis Co. دارند؛ تنها wallet_scope+user_id+key می‌تواند idempotency را تضمین کند (§۱۱.۸) |
| P0-7 | Hedge Buy flow missing entirely | بخش ۱۲.۵.۳ الف اضافه شد: Hedge Buy جریانِ خرید طلای خام از بازار برای پوشش تعهد بین‌شرکتی. API، state، settlement دوره‌ای توثیق شد. |
| P0-8 | Bulk Gold Inventory model missing | دو جدول جدید اضافه: `bulk_gold_inventory` (ذخیره‌ی طلای خام بی‌سریال) و `bulk_gold_movements` (ledger حرکات). محل: بعد از `inventory_movements` در §۱۱.۵ |
| P0-9 | Commission gold creates exposure without inter-company offset | توضیح اضافه در D-73 و جریان Hedge Buy: وقتی commission طلاییِ dealer settled شود (deposit به کیف dealer XAU_MG)، یک پای exposure +pure_gold_mg می‌سازد. این **باید** با inter_company_ledger entry offset شود اگر commission در TalaMala settled شود (D-73 P۳) |

### ۲.۶.۳ اصلاحات BLOCKER/HIGH در v2.4 (نهایی‌سازی implementation-safe — 2026-05-18)

> بعد از بررسی عمیق، **۸ ابهام/contradiction باقی مانده** که implementation را غلط راهنمایی می‌کرد.

| Fix | موضوع | اصلاح |
|---|---|---|
| FIX-1 | **BLOCKER:** Duplicate inter-company ledger entry در §12.1 | **مشکل:** Step 4e (checkout) و step 7 (mark_paid) هر دو inter_company_ledger می‌ساختند → دوبار‌شماری. **اصلاح:** Step 4e کامل حذف شد. فقط step 7 (mark_paid/PaymentVerified) ledger می‌سازد. اضافه: توضیح "⚠️ فقط بعد از تأیید پرداخت، نه موقع checkout" در §6.4 و §12.1 (P0-6 override) |
| FIX-2A | **BLOCKER:** Marketplace contradiction — diagram §3.1 line 278 | **مشکل:** `talamala_digikala payee=TalaMala` (غلط، D-56 می‌گوید Goldis). **اصلاح:** تغییر به `payee=Goldis` + annotation "D-56: marketplace همیشه Goldis" |
| FIX-2B | **BLOCKER:** Marketplace contradiction — §12.8 comment lines 2222-2226 | **مشکل:** Comment می‌گفت "اگر brand=TalaMala، TalaMala inter_company_ledger دریافت می‌کند" (نادرست، D-56 منع می‌کند). **اصلاح:** Comment حذف. جایگزین: "D-56: marketplace همیشه seller=Goldis، payment_receiver=Goldis؛ هیچ inter_company_ledger entry نیست" |
| FIX-2C | **BLOCKER:** Marketplace Note — بعد از §12.8 flow | **اضافه:** صریح note "⚠️ D-56 (قطعی): هیچ inter-company entry در marketplace نیست. پول به Goldis. TalaMala marketplace income مستقیم ندارد." |
| FIX-3 | **BLOCKER:** Supplier purchase contradiction §7.3 line 821 | **مشکل:** "هیچ ledger entry — supplier purchase خارج از scope" (نادرست، D-48 می‌گوید داخل). **اصلاح:** جایگزین با صریح: inter_company_ledger entry ثبت شود (source_type='supplier_purchase') از Goldis→AminZar + توضیح wage_gold_mg |
| FIX-4 | **BLOCKER:** Mensoukh API endpoints در §13 | **مشکل:** `/orders/{id}/cancel` و `/orders/{order_id}/cancel-before-delivery` هنوز فهرست شده (D-58: cancel منسوخ). Buyback header "۳ زیرflow" (نادرست: فقط ۲ — تحویل‌نشده و حضوری). **اصلاح:** ۱) endpoint cancel حذف. ۲) endpoint cancel-before-delivery حذف. ۳) header به "۲ حالت" تغییر (D-58). ۴) labels (a)/(b) renumber. ۵) (c) digital_buyback = /wallet/trades/sell annotation |
| FIX-5 | **HIGH:** Wallet API company_code vs wallet_scope | **مشکل:** `/wallet/balances?company_code=X` و `/wallet/ledger?company_code=X` (D-46 violation: scope نه company_code). **اصلاح:** تمام `company_code` → `wallet_scope` (۳ جا در §13). اضافه: `locked_balance` و `credit_balance` فیلدها به response |
| FIX-6 | **HIGH:** D-62 schema missing from §11.9 | **مشکل:** D-62 تصمیمِ دومرحله‌ای انتقال تولید شده (DRAFT→DISPATCHED→RECEIVED→COMPLETED) ولی جدول ندارد. **اصافه:** `inventory_transfer_documents` و `inventory_transfer_items` tables + all fields (reference_code, status enum, OTP, locations, movements) + indexes |
| FIX-7 | **HIGH:** bars.status insufficient enum برای D-79 | **مشکل:** `bars.status` فقط `RAW|ASSIGNED|RESERVED|SOLD` (D-79 نیاز: DAMAGED, LOST, IN_INSPECTION). **اصلاح:** Enum توسیع + مستند: DAMAGED (packing damaged)، LOST (loss event)، IN_INSPECTION (buyback/damage inspection) |

### ۲.۶.۴ Decision Log Entries v2.4

| ID | تصمیم | تاثیر |
|---|---|---|
| D-85 | inter_company_ledger **فقط** در PaymentVerified — نه checkout | P0-6 fix برای §12.1: تمام فروشِ غیر-Goldis دقیقاً یک بار ledger می‌سازند (یقینی‌سازیِ دوبار‌شماری). atomic transaction: checkout→payment→mark_paid. |
| D-86 | Marketplace = Goldis-exclusive (D-56 قطعی) | D-56 در تمام جاها (diagram، comments، note) apply شد. هیچ TalaMala marketplace income. منطق: Goldis infrastructure/payment منیجر = حق انحصار |
| D-87 | Supplier purchase ledger at intake (D-48 override) | §7.3 اصلاح: inter_company_ledger ✅ (نه ❌). debtor=Goldis, creditor=AminZar, amount=pure+wage_mg. هدف: Goldis↔AminZar obligation tracking از محل تولید |
| D-88 | bars.status enum extended (D-79 support) | DAMAGED, LOST, IN_INSPECTION اضافه شدند تا edge cases پوشش داده شوند (damaged goods, loss tracking, buyback inspection) |
| D-89 | D-62 Two-stage transfer schema | inventory_transfer_documents (DRAFT→DISPATCHED→RECEIVED→COMPLETED|DISCREPANCY) + items. OTP + audit. warehouse-to-warehouse distribution via virtual in-transit location |

---

## ۳. مدل Companies / Brands / Channels

### ۳.۱. ساختار

```
                ┌─────────────────────────────────────────────────────┐
                │   Operator: Goldis Co.                              │
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
    payment_receiver_company_id BIGINT NOT NULL REFERENCES companies(id),  -- D-56: گیرنده‌ی پول
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
    -- مالک حقوقی (مثلاً TalaMala Co.)
    manager_company_id BIGINT NOT NULL REFERENCES companies(id),
    -- شرکتی که فیزیکی این مکان را اداره می‌کند (مثلاً Goldis Co. اگر تحت قرارداد لجستیک)
    -- این دو می‌توانند متفاوت باشند (بخش ۷.۶ — مدل عملیاتی TalaMala)
    location_type VARCHAR(30) NOT NULL,
    -- warehouse | factory | safe_box | store | external_marketplace | branch | dealer
    -- D-62: in_transit (انبارِ مجازیِ موجودیِ در راه — غیرقابل‌فروش؛ هیچ‌جا
    --   reserve/فروش نمی‌شود تا رسیدِ مقصد). انتقالِ دومرحله‌ای روی این بناست.
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

- Storefront frontend ها → **domain → channel lookup** (server-side) + هدر `X-Channel-Code` به‌عنوان fallback
- Admin panel → کاربر در پنل، brand/channel را explicit انتخاب می‌کند (با permission)
- POS app → `terminal_id` + `device_id` در JWT claim → resolve به یک خاص `sales_channel`
- ⚠️ **هیچ frontend نمی‌تواند brand_id را آزاد در body بفرستد** — همیشه از channel resolution می‌آید

---

## ۴. مدل Wallet (Per-wallet-scope)

> هر کاربر **سه کیفِ کاملاً ایزوله** دارد، با کلیدِ `wallet_scope`. `company_id` فقط مشتق و برای حسابداری است.

### ۴.۱. ساختار

```
User Ali (mobile=0912...)
├── KYC: یکی، مشترک
├── Wallet scope = goldis      (legal: Goldis Co.)   ← فقط brand Goldis
│   ├── IRR / XAU_MG / XAG_MG (XAG آینده — D-74)
├── Wallet scope = aminzar     (legal: Goldis Co.)   ← فقط brand AminZar، کاملاً جدا از goldis
│   ├── IRR / XAU_MG / XAG_MG
└── Wallet scope = talamala    (legal: TalaMala Co.) ← فقط brand TalaMala
    ├── IRR / XAU_MG / XAG_MG
```

### ۴.۲. قواعد (D-46)

- کلیدِ کیف = **`wallet_scope`** (goldis|aminzar|talamala)، نه legal_entity. `company_id` فقط مشتق و برای حسابداری/inter-company نگه داشته می‌شود.
- هر scope **فقط در همان scope/برند قابل خرج** است (TalaMala→talamala، Goldis→goldis، AminZar→**aminzar**).
- **هر سه کاملاً ایزوله — هیچ transferِ مستقیم بینِ هیچ‌کدام** (حتی goldis↔aminzar که حقوقاً یک شرکت‌اند). برای جابه‌جایی: فروش به ریال → برداشت → شارژِ مجدد.
- **AminZar در Goldis merge نمی‌شود** هرچند legal entity هر دو Goldis Co. و درگاهِ AminZar همان Goldis IPG است.
- **UX (D-40):** Frontend هر برند فقط scope خودش را «موجودی شما» نشان می‌دهد (نامِ scope/شرکت پنهان). در admin panel هر سه scope در تب‌های جدا، با **تفکیکِ گزارشیِ بدهیِ aminzar از goldis** (الزامِ D-46).

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
    wallet_scope VARCHAR(20) NOT NULL,  -- D-46: goldis | aminzar | talamala (سطل قابل‌مشاهده‌ی کاربر)
    company_id BIGINT NOT NULL REFERENCES companies(id),  -- D-46: مشتق از scope (goldis/aminzar→Goldis Co.، talamala→TalaMala Co.) — برای حسابداری/inter-company
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
-- D-46: wallet_ledger_entries و wallet_locks هم ستون wallet_scope می‌گیرند
-- (هم‌راستا با asset_balances). سه scope کاملاً ایزوله — هیچ انتقال مستقیم بین scopeها.

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
    -- order | trade | withdrawal | buyback | adjustment | lock | release | commit | settlement
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

- وقتی کاربر طلای دیجیتال می‌خرد در brand TalaMala (سمت دیجیتال هم مثل فروش فیزیکی هست):
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

- **یک Treasury** برای کل پلتفرم — managed by Goldis Co.
- نقش Treasury: ثبت **open exposure** Goldis در بازار طلا
- هر فروش طلا (در هر brand، هر channel) → exposure Goldis بالا (چون Goldis بدهی طلا به فروشنده یا مشتری پیدا می‌کند)
- Goldis از بازار خام می‌خرد (`hedge_buy`) → exposure پایین
- Digital gold inventory ≠ جدول جدا. این **همان Treasury** است.

### ۵.۲. Sign convention (explicit)

> `treasury_positions` **per پای** ثبت می‌شود، نه per تراکنش. علامت از **پای** می‌آید نه از `source_type`. بعضی تراکنش‌ها تک‌پایی‌اند (علامتِ ثابت)، بعضی دوپایی (یک `+` و یک `−`، خالص ≈ صفر).
>
> `treasury_positions.delta_amount_mg` بر اساس نگاه **Goldis**:
>
> **تراکنش‌های تک‌پایی (علامتِ ثابت):**
> - **+** (exposure باز — Goldis بدهکار طلا شد): `order_physical`، `pos_sale`، `marketplace_sale`، `digital_buy` (در هر brand، شامل فروش‌های خود Goldis — چون Goldis باید خام بخرد)
> - **−** (exposure بسته): `hedge_buy`، `digital_sell` (فروشِ طلای دیجیتال — «بازخریدِ دیجیتال» همین است)
>
> **تراکنش‌های دوپایی (net ≈ صفر):**
> - `buyback` تحویل‌نشده/حضوری: پای `+pure_gold_mg` (طلا به کیف) و پای `−pure_gold_mg` (شمشِ برگشتی/مصرف) ⇒ خنثی
> - `physical_purchase_from_wallet`: پای `−gold_part_mg` (مصرفِ طلای دیجیتالِ کیف) و پای `+pure_gold_mg` (خروجِ شمشِ فیزیکی) ⇒ خنثی
>
> sum(delta_amount_mg WHERE status IN ('open','partially_covered')) = current open exposure

### ۵.۳. Cap و alert (دوطرفه + چکِ inline)

- **سقفِ دوطرفه per metal:** `max_open_exposure_mg` (سمتِ فروش، exposure مثبت) + `max_short_exposure_mg` (سمتِ خرید/بازخرید، exposure منفی). هر دو اپراتور-تنظیم، با audit.
- **چکِ inline سدِ سخت در لحظه‌ی هر تراکنش** (فروش+خرید، فیزیکی+دیجیتال+POS، بدون استثنا): اگر این تراکنش از سقفِ مربوطه رد شود، **همان تراکنش رد می‌شود** (مثل `require_fresh_price`).
- `warning_threshold_percent` (مثلاً ۷۰٪) برای هر دو طرف.
- `auto_block_at_cap`: worker (§۱۲.۱۰) فقط **هشدار/پشتیبان** است؛ سدِ واقعی همان چکِ inline است.

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
-- D-47: علاوه بر worker ۳۰s، چک inline سدِ سخت در لحظه‌ی هر تراکنش (فروش+خرید،
-- همه‌ی کانال‌ها بدون استثنا). هر دو سقف per فلز قابل تغییر لحظه‌ای اپراتور با audit.

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

### ۶.۱. مفهوم — Goldis به‌عنوان Central Hedging Desk

این context **انحصاراً مسئول است** برای track و settle obligations بین شرکت‌ها (Goldis ↔ TalaMala، Goldis ↔ AminZar، در آینده Goldis ↔ موارد دیگر).

**مدل کسب‌و‌کار (D-06b):**

اصل اساسی بازار طلا: **هر کسی طلا بفروشد، باید بلافاصله معادل وزن خام آن طلا را از بازار بخرد** — وگرنه با بالا رفتن قیمت ضرر می‌کند (open exposure). این کار را hedging می‌گویند.

در پلتفرم ما، **Goldis نقش Central Hedging Desk** را برای همه‌ی برندها بازی می‌کند. یعنی هر فروشگاهی (TalaMala، AminZar، یا حتی خود Goldis) که شمش می‌فروشد، **به‌صورت اتوماتیک از Goldis طلای خام معادل آن را می‌خرد**، و Goldis مسئول است که از بازار خام تهیه کند و دوره‌ای فیزیکی به آن فروشنده تحویل دهد.

> **مالکیت شمش‌ها قبل از فروش:** شمش‌هایی که هم‌اکنون در انبار / فروشگاه / POS هر برند هستند، **مال خود همان برند** هستند (قبلاً خریداری/تولید شده‌اند). این **مدل consignment نیست** — هیچ مالکیت معلق وجود ندارد. مدل تأمین و توزیع شمش‌ها (چرخه‌ی تولید) در بخش بعدی توضیح داده می‌شود؛ این بخش فقط **سمت فروش و hedging** را پوشش می‌دهد.

**وقتی هر فروشگاه (مثلاً TalaMala) یک شمش می‌فروشد:**

- پول مشتری می‌رود به حساب TalaMala (مثلاً ۵۲۰M ریال) — کل سود فروش (اجرت + مالیات) نزد TalaMala می‌ماند
- شمش از انبار TalaMala خارج می‌شود — این یک کاهش سادهٔ inventory برای TalaMala است (مالکیت با خودش بود)
- **همزمان یک تراکنش hedging اتوماتیک شکل می‌گیرد**: TalaMala از Goldis معادل وزن خام طلا را به قیمت طلای خام در همان لحظه «خریده»

این **دو obligation همزمان** در `inter_company_ledger` ثبت می‌کند:

| Direction | Asset | Amount | معنی |
|---|---|---|---|
| `TalaMala → Goldis` | ریال | `raw_gold_price_per_mg × weight_mg` | TalaMala باید بهای معادل وزن خام را به Goldis بپردازد (تسویه روزانه) |
| `Goldis → TalaMala` | gold خام (mg) | `weight_mg` | Goldis باید معادل وزن خام طلا را فیزیکی به TalaMala تحویل دهد (تسویه دوره‌ای) |

**سود فروش نزد TalaMala می‌ماند.** Goldis فقط بهای طلای خام را می‌گیرد و طلای خام را تحویل می‌دهد — هیچ profit share نیست (D-39).

**نکته‌ی مهم:** آنچه Goldis به TalaMala تحویل می‌دهد **طلای خام** است (مثلاً گرانول، شمش بزرگ استاندارد، یا هر فرم خامی که بازار می‌دهد)، **نه همان مدل شمشی که TalaMala فروخت**. TalaMala این طلای خام را برای hedging موجودی خود نگه می‌دارد یا در چرخه‌ی تولید بعدی استفاده می‌کند.

**جهت ledger همیشه hub-and-spoke است:**
- یک طرف obligation همیشه **Goldis** است (debtor یا creditor)
- در v1 obligation peer-to-peer (مثلاً TalaMala ↔ AminZar مستقیم) **نداریم** — همه از طریق Goldis می‌گذرد
- این constraint در sense تجاری هست (نه DB-level)، چون انعطاف آینده برای peer-to-peer لازم می‌شود

**فروش‌های خود Goldis (سایت Goldis، فروش‌هایی که payment به Goldis می‌رود):**
- payment_receiver = Goldis
- **هیچ inter_company_ledger entry بیرونی** ساخته نمی‌شود (Goldis از خودش نمی‌تواند بدهکار شود)
- فقط `treasury_positions` داخلی Goldis آپدیت می‌شود (Goldis exposure باز دارد و باید خودش از بازار بخرد)

### ۶.۲. چرا Real-Time Ledger و نه Settlement Worker روزانه

> **توضیح**: در نسخه‌ی قبلی این سند، Settlement به‌عنوان worker روزانه‌ای طراحی شده بود که batch تسویه می‌ساخت. **این رویکرد اشتباه بود** — مدل واقعی این است که هر فروش **بلافاصله** یک obligation real-time ایجاد می‌کند (چون hedging باید سریع باشد)، و اپراتور Goldis در پایان روز / دوره به‌صورت دستی settle می‌کند.

**اصلاح**: حالا Settlement context عملاً تبدیل می‌شود به **Inter-Company Ledger management**:
- ledger entries در لحظه‌ی هر sale ساخته می‌شوند (real-time)
- اپراتور Goldis در هر زمان می‌تواند `/admin/inter-company/settle-rial` یا `/admin/inter-company/settle-gold` بزند
- جمع‌بندی دوره‌ای (مثلاً «در ماه گذشته TalaMala چقدر بدهکار شد») از طریق aggregate query روی همین ledger ساخته می‌شود (نه جدول جداگانه)

**خلاصه: یک جدول `inter_company_ledger` + endpoint های settle. بدون settlement_rules پیچیده، بدون worker روزانه.**

### ۶.۳. مدل داده — `inter_company_ledger`

```sql
-- جدول یکپارچه برای تمام obligations بین شرکت‌ها (هم gold هم rial)
CREATE TABLE inter_company_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debtor_company_id BIGINT NOT NULL REFERENCES companies(id),
    creditor_company_id BIGINT NOT NULL REFERENCES companies(id),
    asset_type VARCHAR(10) NOT NULL,  -- 'gold' | 'rial'
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

> **⚠️ توجه**: در نسخه‌ی قبلی این سند جداول `settlement_rules`، `settlements` و `settlement_items` تعریف شده بودند. **این جداول حذف شدند** و با `inter_company_ledger` جایگزین شدند. مدل واقعی کسب‌و‌کار با ledger ساده‌ی real-time بهتر mapping می‌شود.

### ۶.۴. جریان (real-time در زمان فروش، بدون worker)

**در زمان هر sale غیر-Goldis** (payment_receiver != Goldis):

```
1. order saved (status=Paid)
2. weight_mg = sum(order_items.pure_gold_mg)
   # pure_gold_mg = weight × (purity / 1000) — وزن خالص طلا
3. raw_hedge_rial = sum(order_items.raw_hedge_price_rial)
   # D-65: raw_hedge_price = P_hedge_per_mg × pure_gold_mg
   #   P_hedge = قیمتِ عمده‌ی Goldis (= P0 + حداقل‌مارجینِ Goldis، شاملِ مالیات)
   #   ⚠️ «raw_gold_price» اینجا یعنی قیمتِ عمده‌ی Goldis، نه اسپاتِ بازارِ بیرونی
   # snapshot در لحظه‌ی فروش، ذخیره در order_item.raw_hedge_price_rial
4. INSERT inter_company_ledger (دو ردیف):
   a. (debtor=payment_receiver, creditor=Goldis,
       asset='rial', amount=raw_hedge_rial,
       source='sale', source_order_id=order.id)
   b. (debtor=Goldis, creditor=payment_receiver,
       asset='gold', amount=weight_mg,
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

سناریو: فردا TalaMala واریز بانکی به حساب Goldis می‌کند بابت همه‌ی فروش‌های دیروز.

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

سناریو: Goldis در پایان هفته (یا هر دوره) معادل وزن خام طلا را فیزیکی به TalaMala تحویل می‌دهد (به‌صورت گرانول/شمش بزرگ/هر فرم خام). اپراتور Goldis تحویل را در سیستم ثبت می‌کند.

```
POST /api/v1/admin/inter-company/settle-gold
Body: { creditor_company_id: TalaMala, debtor_company_id: Goldis, amount_mg, notes }

(منطق FIFO مشابه بالا، روی asset='gold')
```

**نکته:** این endpoint **فقط ledger را آپدیت می‌کند** — تحویل واقعی طلای خام در دنیای واقعی توسط تیم عملیات Goldis انجام می‌شود (و در صورت نیاز، یک inventory_movement جدا برای ثبت ورود گرانول به انبار TalaMala ثبت می‌شود — این طلا برای hedging یا تولید بعدی به‌کار می‌رود، **ربطی به refill شمش‌های فروخته‌شده ندارد**).

### ۶.۶. نمونه واقعی

کاربر در brand TalaMala شمش ۱g می‌خرد، قیمت کل ۵۲M ریال (= ۴۸M طلای خام + ۴M اجرت/مالیات/سود TalaMala):

- پرداخت → TalaMala IPG (۵۲M به حساب TalaMala)
- شمش از inventory_location TalaMala (مال خود TalaMala) به مشتری (یا custodial)
- در همان transaction:
  - `inter_company_ledger`: TalaMala → Goldis، rial، **۴۸M** (قیمت طلای خام در لحظه‌ی فروش)، status=open
  - `inter_company_ledger`: Goldis → TalaMala، gold، **۱۰۰۰mg** (وزن خالص طلا)، status=open
  - `treasury_positions`: Goldis exposure +۱۰۰۰mg
- **سود ۴M (= ۵۲M − ۴۸M) نزد TalaMala باقی می‌ماند.**

عملیات‌های بعدی (دستی توسط اپراتور Goldis):
1. Goldis از بازار طلای خام معادل ۱g می‌خرد (مثلاً به ۴۷.۸M چون قیمت تغییر کرده) — این یک operation داخلی Goldis است که در `treasury_movements` ثبت می‌شود؛ exposure کاهش می‌یابد
2. TalaMala فردا ۴۸M ریال به حساب Goldis واریز می‌کند → اپراتور `settle-rial` می‌زند → rial obligation به ۰ می‌رسد (status=settled)
3. Goldis هر هفته/ماه مجموع طلای خامی که برای hedging TalaMala خریده را فیزیکی به انبار TalaMala تحویل می‌دهد → اپراتور `settle-gold` می‌زند → gold obligation به ۰ می‌رسد
4. این طلای خام تحویلی برای hedging موجودی TalaMala یا تولید شمش بعدی استفاده می‌شود (نه refill همان شمش فروخته‌شده)

### ۶.۷. Buyback و اثرش بر دفترِ بین‌شرکتی

**بازخرید هرگز فروشِ اصلی را reverse نمی‌کند.** «لغو» وجود ندارد؛ فروشِ اول همیشه معتبر می‌ماند و بازخرید یک تراکنشِ **مستقلِ روبه‌جلو** است:

- **بازخریدِ تحویل‌نشده / حضوری:** تبدیلِ physical↔digital است → اثرِ خزانه ≈ **خنثی** (دو پای متقابل)، **هیچ جفتِ تعهدِ طلاییِ تازه‌ای** ساخته نمی‌شود؛ فقط `buyback_credit_rial` به‌عنوان هزینه‌ی ریالی ثبت می‌شود.
- **بازخریدِ دیجیتال** = همان `digital_trade sell` (مسیرِ جدا ندارد). در scope غیر-Goldis یک **جفتِ تازه‌ی مخالف** می‌سازد: `seller→Goldis طلا amount_mg` + `Goldis→seller ریال P_hedge×amount_mg`. در scope=Goldis هیچ تعهدِ بین‌شرکتی، فقط خزانه‌ی `−`.

جزئیاتِ کاملِ flow در بخش Buyback (§۱۲.۵.۲).

### ۶.۸. Future (در v1 پیاده‌سازی نمی‌شود)

اگر در v2+ تصمیم به profit_share گرفته شود:
- ستون‌های جدید به `inter_company_ledger` اضافه می‌شود (یا entry جدا با asset='profit')
- یا یک context جدید برای profit settlement
- در v1 هیچ نیاز به این نیست — سود همیشه نزد فروشگاه می‌ماند

---

## ۷. Production Cycle — چرخه‌ی تولید و تأمین شمش

> این بخش روشن می‌کند که شمش‌ها قبل از فروش از کجا می‌آیند و چگونه وارد انبار فروشنده‌ها می‌شوند. **سمت فروش و hedging در بخش ۶ توضیح داده شد؛ این بخش سمت تأمین است.**

### ۷.۱. سه جریان تأمین

**جریان ۱ — AminZar (factory-only) → Goldis:**
- AminZar Co. کارخانه است (فقط تولید). شمش‌های تولید AminZar را با حاشیه‌ی سود به Goldis می‌فروشد.
- بعد از تحویل به Goldis، شمش‌ها مال Goldis هستند و در channelهای Goldis (سایت Goldis، سایت AminZar که Goldis می‌گرداند، DigiKala، Basalam) فروخته می‌شوند.

**جریان ۲ — TalaMala (factory + seller) برای خودش:**
- TalaMala Co. کارخانه است و خودش هم می‌فروشد. شمش‌های تولید TalaMala مستقیماً وارد انبار TalaMala می‌شوند و در channelهای TalaMala (سایت TalaMala، POS های TalaMala) فروخته می‌شوند.
- این یک جریان **داخلی TalaMala** است — هیچ obligation بین TalaMala و Goldis ایجاد نمی‌کند.

**جریان ۳ — TalaMala (factory) → Goldis (به‌عنوان supplier):**
- TalaMala می‌تواند بخشی از تولید خود را به Goldis بفروشد (مثل AminZar).
- Goldis این شمش‌های TalaMala را در channelهای خودش (سایت Goldis، DigiKala، Basalam) می‌فروشد.
- ⚠️ **توجه:** Goldis طلای **خام** از TalaMala نمی‌خرد — فقط شمش‌های تولیدی برند TalaMala را می‌خرد.

**جریان معکوس (Goldis → TalaMala برای شمش):** در v1 وجود ندارد. TalaMala تنها از تولید کارخانه‌ی خودش تأمین می‌شود. آنچه از Goldis به TalaMala می‌رسد فقط طلای **خام** برای settle obligation های hedging است (بخش ۶.۵).

### ۷.۲. Supplier Purchase — خرید از کارخانه (داخل scope v1)

خرید از کارخانه‌ها (AminZar و TalaMala-as-supplier) **داخل سامانه** است، به‌صورت یک جریانِ **فقط-طلا (بدون ریال)** روی همان batch preorder:

- Goldis به کارخانه می‌دهد: **اصلِ طلا** (وزنِ خالصِ شمش‌ها) + **معادلِ اجرت به‌صورتِ طلا** (`purchase_wage_percent` — عملیاتی، نه metadata). کارخانه شمشِ حک‌شده/پلمب‌شده برمی‌گرداند.
- تعهدِ طلاییِ Goldis↔کارخانه روی همان `inter_company_ledger` با `asset='gold'`, `source_type='supplier_purchase'` رصد می‌شود (جدولِ جدا لازم نیست؛ کارخانه یک طرفِ تعهد، Goldis طرفِ دیگر).
- **طلای اجرت = هزینه‌ی حسابداری**، **بدون** اثر روی exposure/سقفِ خزانه (سقف معیارِ ریسکِ هج‌نشده است، نه هزینه‌ی تولید).
- جریانِ ورودِ سریال‌ها (preorder → in_stock) در §۷.۳.

### ۷.۳. مدل Preorder Bar — سریال‌ها از پیش تولید می‌شوند

سیستم سریال‌ها را از قبل تولید می‌کند، کارخانه فقط حک می‌کند:

```
1. اپراتور Goldis: «از AminZar 100 تا شمش 1g مدل سیمرغ سفارش بده»
2. سیستم 100 ردیف bar تولید می‌کند با:
   - serial = یکتا و قابل پیش‌بینی (مثلاً "AM-1G-SIM-000001"..."AM-1G-SIM-000100")
   - product_id = شمش 1g مدل سیمرغ AminZar
   - status = 'preorder'                # هنوز فیزیکی وجود ندارد
   - current_location_id = factory_AminZar  # محل پیش‌فرض
   - owner_company_id = Goldis           # از پیش رزرو
3. لیست سریال‌ها به AminZar تحویل داده می‌شود (PDF / API export)
4. AminZar شمش‌ها را تولید می‌کند:
   - سریال را روی شمش laser engrave می‌کند
   - کارت پلمب با اطلاعات ثابت (وزن، عیار، تولیدکننده، QR ثابت، سریال) آماده می‌کند
   - شمش + کارت پلمب می‌شوند
5. تحویل به Goldis: اپراتور Goldis سریال‌ها را اسکن می‌کند (یا batch import):
   - status: preorder → in_stock
   - current_location_id: factory_AminZar → goldis_warehouse
   - INSERT inter_company_ledger (asset='gold', source_type='supplier_purchase',
       debtor=Goldis, creditor=AminZar,
       amount=sum(pure_gold_mg) + sum(wage_gold_mg))
     # D-48: supplier_purchase داخل scope — تعهد طلایی Goldis↔کارخانه رصد می‌شود
     # wage_gold_mg = weight × (purchase_wage_percent/100) — cost-only، اثر روی exposure ندارد
```

**نکته‌ی مهم:** کارت پلمب فقط در کارخانه چاپ می‌شود. در لحظه‌ی فروش هیچ کارت دوم چاپ نمی‌شود (فقط فاکتور رسمی برای مشتری).

### ۷.۴. کاتالوگ — چندین SKU per Producer per Weight

برخلاف v4 که هر weight یک محصول بود، در v5 یک کارخانه می‌تواند **چندین مدل/طرح** برای یک وزن یکسان داشته باشد:

- شمش ۱ گرمی AminZar مدل **سیمرغ**
- شمش ۱ گرمی AminZar مدل **گل رز**
- شمش ۱ گرمی AminZar مدل **کلاسیک**

هر یک یک `product_id` جداگانه با ویژگی‌های خود:

```sql
products
├── id BIGSERIAL PK
├── producer_company_id BIGINT NOT NULL  -- AminZar / TalaMala
├── name VARCHAR(200)                    -- "شمش 1گرمی امین‌زر مدل سیمرغ"
├── model_code VARCHAR(50)               -- "SIM-1G" (برای سریال‌سازی)
├── weight_mg BIGINT NOT NULL
├── purity SMALLINT NOT NULL             -- D-51: parts-per-1000 (750=18ع، 999=24ع). فرمول همیشه /1000
├── buyback_percent NUMERIC(5,2)         -- مثلاً 98.0
├── purchase_wage_percent NUMERIC(5,2)   -- اجرت طلایی برای reporting (10.0 = +10٪ طلا)
├── packaging_type_id BIGINT FK
├── is_active BOOLEAN
└── ...
```

### ۷.۵. توزیع داخلی شمش‌ها (Internal Inventory Movement)

بعد از intake شمش وارد انبار Goldis می‌شود. سه مسیر دارد:

1. **در انبار Goldis می‌ماند** برای فروش از سایت Goldis، سایت AminZar (که Goldis می‌گرداند)، DigiKala، Basalam — همگی seller=Goldis، بدون inter-company entry
2. **به مغازه‌ی نماینده یا POS device** که مدیریت آن با Goldis است — مالکیت با Goldis می‌ماند، فقط `current_location_id` تغییر می‌کند
3. **به انبار TalaMala** — این فقط برای **طلای خام** (settle obligation hedging) است، نه شمش‌های آماده

### ۷.۶. مدل عملیاتی TalaMala — لجستیک Goldis، پول TalaMala

طبق توافق انحصاری بین Goldis و TalaMala Co.:

- TalaMala فقط نقش **brand owner + factory + payment receiver** را دارد
- Goldis تمام operationهای فنی و فیزیکی برای brand TalaMala را انجام می‌دهد:
  - نرم‌افزار (سایت، اپ POS، API)
  - مدیریت انبار و fulfillment
  - ارسال و دریافت (logistics)
  - مدیریت دستگاه POS (device management)
  - support کاربر
- ولی **پول و سود فروش** مال TalaMala است (طبق ۱.۲ و ۶.۱)
- شمش‌های TalaMala می‌توانند هم در انبار TalaMala (مدیریت TalaMala) باشند هم در انبار Goldis (مدیریت Goldis، مالکیت TalaMala)
- انتقال شمش بین این دو انبار = فقط `inventory_movement` ساده، بدون ledger entry

این مدل در `inventory_locations` با دو ستون قابل تشخیص است:
- `owner_company_id` — مالک حقوقی (مثلاً TalaMala)
- `manager_company_id` — کسی که فیزیکی مدیریت می‌کند (مثلاً Goldis)

این دو می‌توانند متفاوت باشند.

---

## ۸. Fulfillment (Context جدید)

### ۸.۱. مفهوم

تیم انبار Goldis باید در یک admin panel ببیند:
- چه سفارش‌هایی از کدام brand آمده
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
    bar_id BIGINT NOT NULL REFERENCES bars(id),  -- D-77: شمشِ مشخصِ تخصیص‌یافته (D-49). انباردار همین سریال را برمی‌دارد؛ اسکنِ سریالِ pick باید با این بخواند وگرنه خطا. (برای چند شمش، چند ردیفِ task)
    quantity INT NOT NULL,
    amount_mg BIGINT NULL,
    source_location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    destination_type VARCHAR(30) NOT NULL,
    -- customer_pickup | courier | store
    -- D-80: internal_transfer حذف شد — هر انتقالِ داخلیِ بینِ انبارها فقط از
    --   مسیرِ دومرحله‌ای D-62 می‌رود. fulfillment فقط تحویلِ مرتبط با
    --   order_id مشتری است (همیشه order_id دارد).
    destination_address VARCHAR(500) NULL,
    courier_provider VARCHAR(50) NULL,
    tracking_number VARCHAR(100) NULL,
    assigned_to BIGINT NULL REFERENCES users(id),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    -- pending | picking | picked | packed | handed_over | delivered | cancelled
    -- D-79 (استثناها): delivery_failed | lost_in_transit | damaged
    --   هیچ‌کدام خودکار بسته نمی‌شوند — تصمیمِ اپراتور/حسابدار + audit + reason الزامی
    delivery_otp_hash VARCHAR(255) NULL,   -- D-78: OTPِ گیرنده؛ بدون آن delivered بسته نمی‌شود
    delivery_otp_expiry TIMESTAMPTZ NULL,  -- D-78
    delivered_confirmed_by BIGINT NULL REFERENCES users(id),  -- D-78: نقشِ مقصد (نه انباردارِ مبدأ)
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    picked_at TIMESTAMPTZ NULL,
    packed_at TIMESTAMPTZ NULL,
    handed_over_at TIMESTAMPTZ NULL,       -- D-78: «از دستِ ما خارج شد» (انباردار)، نه «رسید»
    delivered_at TIMESTAMPTZ NULL          -- D-78: فقط با OTPِ گیرنده ست می‌شود؛ bar.delivered_at هم همین‌جا
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
0. ⚠️ D-77: trigger ساختِ task = «درخواستِ تحویل» است، نه «پرداختِ سفارش».
   فروشِ امانی (delivered_at=NULL) هیچ taskی نمی‌سازد (شمش در خزانه قفل).
   فقط با درخواستِ تحویلِ مشتری (یا تحویلِ فوری در POS/فروشگاه) task ساخته
   می‌شود، با bar_idِ همان شمشِ تخصیص‌یافته (D-49).
1. Delivery requested → Fulfillment.create_task(order_item, bar)
2. INSERT fulfillment_tasks (status=pending)
3. انباردار از admin panel: GET /admin/fulfillment/tasks?status=pending
4. انباردار: POST /admin/fulfillment/tasks/{id}/assign-self
5. POST /admin/fulfillment/tasks/{id}/pick  → status=picking → picked
6. POST /admin/fulfillment/tasks/{id}/pack
7. POST /admin/fulfillment/tasks/{id}/handover  → courier info
   # D-78: انباردار فقط «به پیک دادم» را می‌زند = handed_over (از دستِ ما خارج شد، نه «رسید»)
8. POST /admin/fulfillment/tasks/{id}/confirm-delivery → status=delivered
   # D-78: فقط با OTPِ گیرنده (+ اسکنِ سریال در تحویلِ حضوری). انباردارِ مبدأ
   #   این را نمی‌بندد — نقشِ مقصد (پیک‌تأیید/کارمندِ فروشگاه/نماینده) با
   #   delivered_confirmed_by. تا قبل از این، شمش «در حالِ تحویل»؛
   #   bar.delivered_at فقط همین‌جا ست می‌شود.
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
   • Backend از device → channel → dealer → location می‌رسد
   • Returns: لیست بارهای موجود در انبار **همان نماینده** + price preview
2. نماینده/کاربر یک bar انتخاب می‌کند
3. POS device → POST /api/v1/pos/reserve { bar_id, customer_mobile }
   • bar lock می‌شود (status=RESERVED، reserved_until=+N min)
4. کشیدن کارت روی POS hardware
5. POS device → POST /api/v1/pos/confirm { reservation_id, trace_number, rrn, amount, paid_at }
   • Order با order_type=pos_sale + Inventory.consume + Treasury + Settlement + DealerSale
6. در صورت fail → POST /api/v1/pos/cancel → release reservation
```

---

## ۱۰. لیست کامل Bounded Contexts

| # | Context | Global/Per-Company | مسئولیت |
|---|---------|----------------|---------|
| 1 | **platform** | Global | Companies، Brands، SalesChannels، PaymentAccounts، InventoryLocations |
| 2 | **identity** | Global | User، Session، JWT، RBAC، Permission، SSO |
| 3 | **kyc** | Global | Shahkar، KYC status، user_level، limits، اسناد |
| 4 | **catalog** | Global | Product، Variant، Attribute، Image، ChannelAvailability، ExternalMapping |
| 5 | **pricing** | Hybrid | Source prices (global)، Internal base price، Channel formula، PriceLock |
| 6 | **inventory** | Global | Bar، Reservation، Movement، Transfer بین لوکیشن‌ها |
| 7 | **cart** | Per-channel | Cart، CartItem |
| 8 | **order** | Per-brand | Order (با ۷ order_type)، OrderItem، OrderStatusLog، WithdrawalDetail (فقط rial)، PhysicalPurchaseFromWallet، Buyback |
| 9 | **payment** | Per-account | Payment، PaymentTransaction، Callback (Refund حذف شد — D-32. به‌جای آن Buyback در order context) |
| 10 | **wallet** | Per-company | AssetBalance، LedgerEntry، Lock |
| 11 | **treasury** | Goldis-only | Position، Coverage، Alert |
| 12 | **inter_company** | Inter-company | InterCompanyLedger (real-time obligations: gold + rial)، SettleActions (audit)، Reports (aggregate). جایگزین settlement قدیمی. |
| 13 | **fulfillment** | Goldis-ops | Task، Event |
| 14 | **pos** | Per-channel | Device، Transaction، Reconciliation |
| 15 | **dealer** | Per-company (opt-in) | Dealer، Tier، Sale، Commission (`dealer_commission_rates`+`dealer_commission_ledger`). ⚠️ SubDealer/شبکه‌ای حذف — D-73 |
| 16 | **marketplace** | Per-channel | ExternalChannel، ExternalOrder، Mapping، SyncLog، Adapter |
| 17 | **accounting** | Per-company | AccountingEvent، Export |
| 18 | **notification** | Per-user | Notification، Preference، Dispatcher |
| 19 | **realtime** | Global | SSE endpoint، event broadcaster |
| 20 | **audit** | Global | AuditLog (append-only) |
| 21 | **outbox** | Global | OutboxEvent + Publisher worker |
| 22 | **support** | Per-brand | Ticket، Message، Attachment |
| 23 | **content** | Per-brand | Blog، Article، FAQ، Page (SEO) |
| 24 | **reporting** | Global view | Read-only viewها برای dashboard/export |

### قواعد تعامل بین context ها

1. هیچ context مستقیماً جدول دیگر context را نمی‌خواند/نمی‌نویسد. فقط از service interface.
2. هر تغییر داده‌ی حساس (wallet، treasury، order status، price، kyc، dealer commission، settlement) → audit_logs entry.
3. هر event حیاتی → outbox_events entry در همان transaction.
4. SQLModel layer split: `Table` models (DB) / `Create` / `Update` / `Read` / `Internal DTO`. هیچ Table model مستقیم به API response نمی‌رود.
5. تراکنش‌های دیتابیس per-request scope با commit در پایان operation.

---

## ۱۱. مدل داده‌ی سایر context ها

(جدول‌های قبلی در بخش‌های ۳-۸ آمدند. اینجا بقیه.)

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
    -- Limits (overrides از user_level defaults)
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

> **مدل چندSKU:** یک کارخانه می‌تواند چندین مدل/طرح برای یک وزن یکسان داشته باشد (مثل «شمش ۱g امین‌زر مدل سیمرغ» و «شمش ۱g امین‌زر مدل گل رز»). هر مدل یک `product_id` مستقل با `model_code` یکتا دارد. توضیح بیشتر در بخش ۷.۴.

```sql
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(300) NOT NULL,                  -- "شمش 1گرمی امین‌زر مدل سیمرغ"
    model_code VARCHAR(50) NULL,                 -- "SIM-1G" — برای سریال‌سازی preorder
    product_type VARCHAR(30) NOT NULL,
    -- bar | melted | digital | coin | jewelry
    metal_type VARCHAR(20) NOT NULL,             -- gold | silver
    weight_mg BIGINT NOT NULL,
    purity INT NOT NULL,                         -- D-51: parts-per-1000 (0..1000)؛ فرمول وزن خالص همیشه ×purity/1000
    is_physical BOOLEAN NOT NULL,
    default_producer_company_id BIGINT NULL REFERENCES companies(id),
    buyback_percent NUMERIC(5, 2) NULL,          -- default per product (override در channel_pricing_formulas)
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
    -- به wallet IRR کاربر برمی‌گردد. در order_items.buyback_credit_rial snapshot می‌شود.
    buyback_percent NUMERIC(6, 3) NOT NULL DEFAULT 0,
    rounding_policy VARCHAR(20) NOT NULL DEFAULT 'floor',
    -- D-27: floor به‌عنوان default. می‌توان به round_half_up/ceiling/bankers تغییر داد per formula
    lock_ttl_seconds INT NOT NULL DEFAULT 120,
    -- D-50 (override D-28): ۲ دقیقه default، بازه‌ی مجاز ۶۰s..۳۰۰s (کف ۱ دقیقه برای شرایط پرنوسان)
    dealer_tier_id BIGINT NULL,  -- D-65: بُعدِ سطح. NULL=مشتریِ نهایی (P_retail)؛ مقدار=سطحِ همکار (P_partner). FK به dealer_tiers بعد از context دیلر اضافه شود. رزولوشن با priority.
    trade_side VARCHAR(10) NULL,  -- D-72: buy|sell|NULL. spreadِ دوطرفه — قیمتِ خرید و فروشِ دیجیتال مارجینِ مستقل دارند. NULL=هر دو سمت. «کارمزدِ معامله»ی v4 همین مارجین است (مفهومِ جدا نداریم).
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
    sale_wallet_scope VARCHAR(20) NULL,  -- D-71: goldis|aminzar|talamala — در لحظه‌ی فروش از scopeِ سفارش پر، سپس IMMUTABLE (انتقالِ مالکیت عوضش نمی‌کند). NULL=هنوز فروش‌نرفته. مبنای قطعیِ بازخرید/گزارش/scope. بازخریدِ آنلاین فقط در همین scope مجاز است.
    is_preorder BOOLEAN NOT NULL DEFAULT FALSE,
    -- TRUE = سریال از سیستم تولید شده ولی فیزیکی تولید نشده (در کارخانه)
    -- بعد از تحویل کارخانه → Goldis: is_preorder=FALSE + status: RAW→ASSIGNED + location: factory→warehouse
    -- (بخش ۷.۳)
    status VARCHAR(20) NOT NULL DEFAULT 'RAW',
    -- RAW       : تولید شده / در انبار (قابل فروش)
    -- ASSIGNED  : برای channel تخصیص‌یافته (قابل reserve)
    -- RESERVED  : موقتاً رزرو شده (POS یا checkout)
    -- SOLD      : فروخته‌شده (مالک دارد — custodial یا تحویل‌شده)
    -- DAMAGED   : آسیب‌دیده / پلمب‌شکسته → نیاز به بررسی، قابل فروش نیست (D-79)
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
-- برای ذخیره‌ی طلای خام/ذوب‌شده که سریال‌دار نیستند (granules، large bars from smelting)
-- مثلاً: «۱۰۰g طلای ۷۵۰ خام در انبار Goldis»
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
    trade_side VARCHAR(10) NULL,             -- buy | sell (فقط digital_trade؛ بازخریدِ دیجیتال = همان digital_trade sell — D-68)
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
    -- D-32: buyback snapshot moment of purchase. در buyback (هر زیرflow) به wallet IRR کاربر برمی‌گردد.
    buyback_credit_rial BIGINT NOT NULL DEFAULT 0,
    -- وزن خالص طلا (cost) برای buyback. در صورت buyback به wallet XAU_MG برمی‌گردد.
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
-- هر allocation یک منبع پرداخت را explicit ثبت می‌کند با link به wallet_lock یا payment.
-- این جدول split payment را قابل audit، rollback، و idempotent می‌کند.
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
--   atomic confirm: یا همه consume می‌شوند یا همه release.

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

-- payment_accounts قبلاً تعریف شده بخش ۳.۲

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NULL REFERENCES orders(id),        -- P0 fix: nullable برای topup payments (بدون order)
    user_id BIGINT NOT NULL REFERENCES users(id),
    payment_account_id BIGINT NOT NULL REFERENCES payment_accounts(id),
    payment_receiver_company_id BIGINT NOT NULL REFERENCES companies(id),
    amount_rial BIGINT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'created',
    authority VARCHAR(255) NULL,
    tracking_code VARCHAR(255) NULL,
    rrn VARCHAR(50) NULL,
    idempotency_key VARCHAR(100) NULL UNIQUE,
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
    wallet_scope VARCHAR(20) NOT NULL,  -- D-76: goldis|aminzar|talamala — از فرانت/کانال resolve، کیفِ همان scope شارژ می‌شود (ایزوله، D-46)
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
    UNIQUE (wallet_scope, user_id, idempotency_key)  -- P0-1.1 fixed: scope-keyed، not company_id (goldis+aminzar share Goldis Co.)
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

### ۱۱.۹. جداولِ تکمیلیِ جلسه‌ی بازبینی (D-62 / D-63 / D-73)

> این جداول از تصمیماتِ override می‌آیند و در SQLِ اصلی نبودند.

```sql
-- D-63: لیستِ اولویت‌دارِ درگاه per channel + fallback خودکار
-- (جایگزینِ تک‌مقداریِ sales_channels.default_payment_account_id؛
--  آن ستون می‌ماند فقط به‌عنوان «اولینِ پیش‌فرض» / سازگاری)
CREATE TABLE sales_channel_payment_accounts (
    id BIGSERIAL PRIMARY KEY,
    sales_channel_id BIGINT NOT NULL REFERENCES sales_channels(id),
    payment_account_id BIGINT NOT NULL REFERENCES payment_accounts(id),
    priority INT NOT NULL DEFAULT 0,           -- کوچک‌تر = اولویتِ بالاتر
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,  -- اپراتور می‌تواند موقتاً غیرفعال کند
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (sales_channel_id, payment_account_id)
);
CREATE INDEX ix_scpa_channel_prio
    ON sales_channel_payment_accounts (sales_channel_id, priority)
    WHERE is_enabled = TRUE;
-- موقعِ پرداخت: اولین payment_accountِ enabled و سالم؛ اگر down → بعدی.
-- هر بار درگاهی خطا/down داد (حتی اگر fallback پوشش داد) → notification+audit (D-63).

-- D-73: نرخِ کمیسیونِ نماینده (Gold-for-Gold)
CREATE TABLE dealer_commission_rates (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NULL REFERENCES products(id),     -- پیش‌فرضِ محصول
    product_type VARCHAR(30) NULL,                        -- یا per نوعِ محصول
    dealer_tier_id BIGINT NULL,                           -- NULL=همه‌ی سطوح؛ FK بعد از dealer_tiers
    trade_side VARCHAR(10) NOT NULL,                      -- sale | buyback
    commission_percent NUMERIC(6,3) NOT NULL,             -- درصدِ pure_gold_mgِ تراکنش (D-73 بند۵)
    priority INT NOT NULL DEFAULT 0,                       -- رزولوشنِ مشخص‌ترین، مثلِ D-65
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_dcr_side CHECK (trade_side IN ('sale','buyback'))
);
-- نگهبان (D-73): فروش → Σکمیسیون ≤ (P_retail−P_hedge)؛
--   بازخرید → کمیسیون ≤ اسپردِ بازخرید؛ نقض → رد/هشدارِ اپراتور.

-- D-73 (P۱): تسویه‌ی کمیسیونِ نماینده — جدا از inter_company_ledger
-- (آن شرکت↔شرکت است؛ نماینده کاربر است). بدهیِ طلاییِ TalaMala→نماینده.
CREATE TABLE dealer_commission_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_user_id BIGINT NOT NULL REFERENCES users(id),
    seller_company_id BIGINT NOT NULL REFERENCES companies(id),  -- بدهکار (TalaMala)
    dealer_sale_id BIGINT NULL,                 -- FK به DealerSale (context دیلر)
    trade_side VARCHAR(10) NOT NULL,            -- sale | buyback
    amount_mg BIGINT NOT NULL CHECK (amount_mg > 0),  -- طلا (Gold-for-Gold)
    status VARCHAR(20) NOT NULL DEFAULT 'open', -- open | partial | settled | cancelled
    settled_amount_mg BIGINT NOT NULL DEFAULT 0,
    -- D-73 بند۷: کمیسیونِ بازخرید فقط بعد از AuthenticityVerified ثبت شود
    -- D-73 P۳: واریزِ این طلا به کیفِ نماینده یک پایِ خزانه‌ای +pure_gold_mg
    --   می‌سازد و تابعِ سقف‌های D-47 است.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    settled_at TIMESTAMPTZ NULL,
    settled_by BIGINT NULL REFERENCES users(id),
    CONSTRAINT chk_dcl_settled CHECK (settled_amount_mg <= amount_mg)
);
CREATE INDEX ix_dcl_dealer_status
    ON dealer_commission_ledger (dealer_user_id, status);

-- D-62: انتقالِ بین‌انبارِ دومرحله‌ای (DRAFT→DISPATCHED→RECEIVED→COMPLETED|DISCREPANCY)
CREATE TABLE inventory_transfer_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_code VARCHAR(50) UNIQUE NOT NULL,   -- TRF-20260518-001
    source_location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    destination_location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    in_transit_location_id BIGINT NULL REFERENCES inventory_locations(id),
    -- virtual in-transit location (D-62: موجودیِ در راه)
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
```

---

## ۱۲. جریان‌های اصلی

### ۱۲.۱. خرید شمش از سایت TalaMala

```
1. درخواست به talamala.ir → frontend → POST /api/v1/cart/items
   Header: X-Channel-Code=talamala_web
2. Backend resolve می‌کند: brand=TalaMala, channel=talamala_web,
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
        (snapshot قیمتِ عمده‌ی Goldis در لحظه‌ی فروش — تنها مبنای inter_company_ledger)

   e. **هیچ ledger entry اینجا ساخته نمی‌شود — فقط در step 7 (mark_paid)**
5. POST /api/v1/payments/start → TalaMala IPG → redirect to bank
6. Bank callback → POST /api/v1/payments/callback/zibal [IDEMPOTENT]
7. on verified:
   - UPDATE payments status=verified
   - Order.mark_paid:
     • UPDATE orders status=Paid
     • Inventory.consume(bar) → status=SOLD, customer_id=user_id
     • (D-77: اگر تحویلِ فوری/POS → create_task(order_item, bar)؛ اگر امانی → هیچ task، فقط هنگامِ درخواستِ تحویل ساخته می‌شود)
     • Treasury.record(source=order_physical, delta=+weight_mg,
                       triggered_by_brand=TalaMala)
     • اگر payment_receiver != Goldis:
       INSERT inter_company_ledger × 2 (rial + gold per بخش ۶.۴)
     • Accounting.record_event
     • Outbox: OrderPaid, TreasuryPositionOpened,
               InterCompanyObligationCreated, AccountingEventCreated
               (D-77: FulfillmentTaskCreated اینجا نیست — فقط هنگامِ درخواستِ تحویل)
     • Notification → user
8. (D-77) امانی: شمش در خزانه قفل؛ هنگامِ درخواستِ تحویل → task با bar_id
   → انباردار pick (اسکنِ سریال) → pack → handover (به پیک دادم)
   → confirm-delivery با OTPِ گیرنده (نقشِ مقصد، نه انباردار — D-78)
```

### ۱۲.۲. خرید طلای دیجیتال در brand AminZar

```
1. کاربر در aminzar.ir → POST /api/v1/wallet/trades/buy
   { asset: XAU_MG, amount_mg: 500, channel: aminzar_web }
2. brand=AminZar, channel=aminzar_web, payment_account=Goldis_IPG,
   payment_receiver=Goldis, seller_company=Goldis
   (چون brand AminZar توسط Goldis اداره می‌شود — D-06b, ۱.۳)
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
   - Wallet at Goldis (XAU_MG) of user → +500mg
   - Treasury.record(source=digital_buy, delta=+500mg,
                     triggered_by_brand=AminZar)
   - Inter-company ledger: **هیچ entry** — چون seller=Goldis (Goldis-side sale)
   - Accounting + Outbox + Notification
```

> **نکته:** هرچند brand_owner = AminZar Co.، ولی چون Goldis این برند را اداره می‌کند و پول/سود مال Goldis است، از نظر hedging یک فروش Goldis-side محسوب می‌شود. AminZar Co. فقط در لحظه‌ی تأمین شمش از کارخانه‌اش به Goldis سود می‌گیرد (در context چرخه‌ی تولید — بخش بعدی).

### ۱۲.۳. خرید طلای دیجیتال در brand TalaMala

```
مشابه ۱۱.۲ ولی:
- payment_account=TalaMala_IPG, payment_receiver=TalaMala
- Wallet at TalaMala (XAU_MG) of user → +500mg
- Treasury مرکزی Goldis: +500mg (تک‌پاییِ digital_buy — D-67؛ treasury
  مرکزی است حتی اگر پول رفته به TalaMala)
- Inter-company ledger × 2 (TalaMala-side):
  • TalaMala → Goldis، rial = P_hedge_per_mg(لحظه) × 500mg   # D-69/D-65 — نه internal_base_price، نه قیمتی که کاربر پرداخت
  • Goldis → TalaMala، gold، 500mg
  (status=open، تا اپراتور settle کند)
  # D-69: خرید دیجیتالِ scope غیر-Goldis هم‌سنگِ فروشِ فیزیکیِ غیر-Goldis
  #   است (همان مدلِ §۱۲.۱)؛ فقط شمش/اجرت ندارد و خزانه‌اش تک‌پاییِ
  #   digital_buy است. مابه‌التفاوتِ (قیمتِ کاربر − P_hedge) سودِ TalaMala.
```

این کلید فهم سیستم است: **پول و wallet هر برند جداست، ولی Goldis به‌عنوان Central Hedging Desk از طریق `inter_company_ledger` real-time در هر فروش obligation می‌گیرد و دوره‌ای settle می‌کند.**

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
   - اگر scope غیر-Goldis (مثل TalaMala) → Inter-company × 2 (D-70، آینهٔ §۱۲.۳/D-69):
       • TalaMala → Goldis، gold، 300mg            # TalaMala طلا را پس می‌دهد
       • Goldis → TalaMala، rial، P_hedge_per_mg(لحظه) × 300mg
     اگر scope=Goldis (برند Goldis/AminZar) → هیچ تعهد بین‌شرکتی، فقط خزانه‌ی −
     # مابه‌التفاوتِ (P_hedge − مبلغِ پرداختی به کاربر) حاشیه‌ی TalaMala
     # این همان مسیرِ یکتای digital_trade sell است (D-68 — «بازخریدِ دیجیتال» = همین)
   - Outbox + Notification
```

### ۱۲.۵. خرید محصول فیزیکی با wallet XAU_MG (physical_purchase_from_wallet)

> **D-31:** gold withdrawal به‌عنوان flow جدا حذف شد. به‌جای آن کاربر می‌تواند با wallet XAU_MG یک محصول فیزیکی بخرد (که اساساً همان تأثیر را دارد).
>
> **O-03:** برداشت فقط در قالب محصولات موجود امکان‌پذیر است. اگر کاربر ۱۰g می‌خواهد، باید یک شمش ۱۰g موجود انتخاب کند. اگر اجرت ۲٪ دارد، نیاز است ۱۰.۲g در wallet داشته باشد، یا تفاوت را ریالی پرداخت کند.

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
    a. payment = Payment.create(amount=irr_from_gateway, status=created)
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
        پای۱: delta=-gold_part_mg            # مصرفِ طلای دیجیتالِ کیف ⇒ exposure بسته
        پای۲: delta=+pure_gold_mg(شمشِ تحویلی) # خروجِ شمشِ فیزیکی = فروشِ فیزیکی ⇒ exposure باز
      ⇒ net change در exposure Goldis ≈ صفر (تبدیلِ digital→physical)، نه منفی
      ⚠️ ثبتِ تنها پای۱ (متنِ قدیمی) باگ است: یک شمشِ هج‌نشده از سیستم خارج و exposure گم می‌شود
    - اگر payment_receiver != Goldis (یعنی from_wallet=TalaMala):
      INSERT inter_company_ledger × 2 (rial + gold per بخش ۶.۴)
    - (D-77: اگر تحویلِ فوری → create_task(order_item, bar)؛ اگر امانی → بدون task تا درخواستِ تحویل)
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

Refund نداریم؛ «لغو» هم نداریم. **فروشِ اصلی همیشه معتبر می‌ماند و هرگز reverse نمی‌شود.** بازخرید همیشه یک تراکنشِ **مستقلِ روبه‌جلو** است، با دو حالتِ عملیاتی:

| حالت | شرایط | تأیید |
|---|---|---|
| (a) **بازخریدِ تحویل‌نشده** | bar.status=SOLD، `delivered_at IS NULL` (شمش هنوز در خزانه‌ی ماست) | اتومات (آنلاین) |
| (b) **بازخریدِ حضوری** | bar.status=SOLD، `delivered_at IS NOT NULL` (مشتری شمش را حضوری می‌آورد) | کارشناسِ مرکزِ Authorized — state machine |

> «بازخریدِ دیجیتال» مسیرِ جدا **نیست** = همان `digital_trade sell` (§۱۲.۴).

**در هر دو حالت:**
- وزنِ خالص (`weight × purity / 1000`) → wallet **XAU_MG** (همیشه).
- `order_items.buyback_credit_rial` (snapshot موقع خرید) → wallet **IRR** — **فقط اگر** شمش در لحظه‌ی بازخرید به نامِ کاربر ثبت‌مالکیت شده باشد و با **OTP** تأیید شود؛ وگرنه ۰.
- اجرت + مالیات + سود + هزینه‌های اضافه **می‌سوزد**.
- هر دو واریز به **scope برندِ فروشِ همان شمش** (`bars.sale_wallet_scope`).
- خزانه: تبدیلِ physical↔digital ⇒ **خنثی** (پای `+pure_gold_mg` به کیف، پای `−pure_gold_mg` شمشِ برگشتی)؛ **هیچ تعهدِ بین‌شرکتیِ تازه‌ای** ساخته نمی‌شود؛ فقط `buyback_credit_rial` هزینه‌ی ریالی است.
- بازخریدِ آنلاین فقط در همان scope/وب‌سایتی که خرید انجام شده مجاز است.

#### حالت (a) — بازخریدِ تحویل‌نشده (آنلاین، اتومات)

```
1. User → POST /api/v1/orders/{order_id}/buyback   (شمش هنوز تحویل نشده)
2. Validate:
   - order.user_id == current_user
   - bar.status == SOLD، bar.delivered_at IS NULL
   - (اگر fulfillment_task ساخته شده و packed/handed_over: حالت (a) مجاز نیست → حالت (b))
3. اتومات (در یک DB transaction):
   - یک سفارشِ بازخریدِ مستقل (order_type=buyback) ثبت می‌شود — فروشِ اصلی دست‌نخورده
   - bar.status = ASSIGNED, customer_id = NULL  (شمش به خزانه برمی‌گردد، قابلِ فروشِ دوباره)
   - اگر fulfillment_task باز بود → بسته/کنسل می‌شود
   - Wallet.credit(user, bars.sale_wallet_scope, XAU_MG, order_item.pure_gold_mg)
   - اگر ثبت‌مالکیت+OTP: Wallet.credit(user, scope, IRR, order_item.buyback_credit_rial)
   - Treasury: دو پای متقابل ⇒ خالص ≈ صفر (physical→digital)
   - Audit log + Outbox: BuybackCompleted + Notification
```

#### حالت (b) — بازخریدِ حضوری (نیازمند تأیید)

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
     { bar_id, target_location_id (مغازه‌ی نماینده یا انبار) }
2. Validate:
   - bar.customer_id == current_user
   - bar.status == SOLD، delivered_at IS NOT NULL
   - target_location.can_buyback == TRUE
3. INSERT physical_buyback_request (status=PhysicalRequested, target_location_id)
4. کاربر شمش را به مرکز می‌برد.
5. کارشناس → POST /api/v1/admin/buyback/{id}/receive
   → status=PhysicalReceived
6. کارشناس بررسی می‌کند: سریال، اصالت، وزن، عیار
   POST /api/v1/admin/buyback/{id}/verify [اگر OK] یا /reject
   → status=AuthenticityVerified | Rejected
7. کارشناس تأیید نهایی → POST /api/v1/admin/buyback/{id}/approve
   → status=Approved
8. سیستم در DB transaction (فقط بعد از Approved):
   - Wallet.credit(user, bars.sale_wallet_scope, XAU_MG, order_item.pure_gold_mg)
   - اگر ثبت‌مالکیت+OTP تأیید شد: Wallet.credit(user, scope, IRR, order_item.buyback_credit_rial)
   - bar.status = ASSIGNED, customer_id = NULL, delivered_at = NULL
   - bar.current_location_id = target_location_id  (location تغییر می‌کند)
   - INSERT inventory_movement (type=transfer_in, to=target_location)
   - Treasury: دو پای متقابل ⇒ خالص ≈ صفر (physical→digital)
   - فروشِ اصلی reverse نمی‌شود (تراکنشِ بازخریدِ مستقل)
   - status=WalletCredited → Completed
   - Audit log + Outbox: PhysicalBuybackCompleted + Notification
```

**قواعد امنیتی:**
- Wallet **نباید** قبل از `AuthenticityVerified` credit شود
- separation of duties: کارشناس receive ≠ کارشناس verify (یا حداقل audit‌شده باشد)
- audit_log الزامی در هر transition

#### «بازخریدِ دیجیتال» — مسیرِ جدا ندارد

فروشِ طلای دیجیتالِ کیف **همان `digital_trade sell` (§۱۲.۴)** است؛ از `/wallet/trades/sell` استفاده می‌شود. قیمتش از نردبانِ قیمت سمتِ فروش (`trade_side=sell`) می‌آید. مدلِ خزانه/بین‌شرکتی‌اش در §۱۲.۴ آمده.

### ۱۲.۵.۳ الف. Hedge Buy — خرید طلای خام از بازار (P0-7)

> **مفهوم:** Goldis به‌عنوان Central Hedging Desk در پاسخ به فروش‌های غیر-Goldis (TalaMala/AminZar)، طلای خام را از بازار می‌خرد و به صورت دوره‌ای به فروشنده تحویل می‌دهد. این جریان تعهد طلایی بین‌شرکتی را پوشش می‌دهد.

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
   - Treasury.check_capacity (سقف دوطرفه D-47: max_short_exposure_mg check)
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
   - Treasury.record (source=hedge_buy، delta=+500000)
   - Audit log + Notification

۳. Flow اختیاری برای compliance:
   - اپراتور می‌تواند hedge_buy را تا قبل از تحویل فیزیکی «pending» نگه دارد
   - بعد از تحویل فیزیکی از supplier: Operator تأیید می‌کند
   - وزن اسکن/تأیید شده → bulk_gold_inventory.last_counted_at update

۴. Settlement دوره‌ای (روزانه یا هفتگی):
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
- هر settlement یک `inter_company_ledger.source_type='hedge_buy_settlement'` entry می‌سازد

### ۱۲.۵.۴. شارژ wallet ریالی (Rial Topup) — اتومات، بدون اپراتور

> کاربر در سایت هر brand می‌تواند wallet ریالی همان brand را از طریق gateway شارژ کند. **هیچ تأیید اپراتوری لازم نیست** — مثل خرید عادی.

```
1. User → POST /api/v1/wallet/topup
   Header: X-Channel-Code=<channel>
   Body: { amount_rial }
   • Backend resolves: فرانت/کانال → wallet_scope (D-76/D-46)
     (طلاملا→scope=talamala، گلدیس→scope=goldis، امین‌زر→scope=aminzar)
     ⚠️ سه scope کاملاً ایزوله؛ امین‌زر merge در goldis نمی‌شود
     (هرچند legal entity هر دو Goldis Co. و درگاهش Goldis IPG است)
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

**نکته:** هیچ Treasury impact ندارد (پول می‌آید، تعهد طلایی تغییری نمی‌کند). فقط Accounting event ثبت می‌شود.

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

> **نکته:** برای v1، **همه‌ی** برداشت‌ها نیاز به تأیید اپراتور دارند (تصمیم تیم). در آینده می‌توان آستانه‌ی مبلغ تعریف کرد که زیرش auto-approve باشد.

### ۱۲.۷. POS sale (sample: TalaMala POS at dealer)

> اپ POS لیست شمش‌های موجود در انبار **همان نماینده** را نشان می‌دهد. نماینده/کاربر یکی را انتخاب می‌کند (نه scan). بعد از انتخاب و رفتن به مرحله‌ی پرداخت، شمش lock می‌شود.

```
1. POS Android app → GET /api/v1/pos/inventory
   Header: X-API-Key=<device api key>
   • Backend resolve می‌کند: device → sales_channel → dealer → inventory_location
   • returns: list of bars where:
       - current_location_id = <dealer's inventory_location>
       - status IN ('ASSIGNED', 'RAW')
   • هر bar شامل: serial_code, weight_mg, purity, product_name, product_id
       + price preview (محاسبه‌شده توسط Pricing با channel formula)

2. نماینده / کاربر یک bar را از لیست انتخاب می‌کند، می‌رود به مرحله پرداخت

3. POS app → POST /api/v1/pos/reserve
   Body: { bar_id, customer_mobile }
   • Backend:
     - validate: bar در dealer's location، status قابل reserve
     - Pricing.create_price_lock(channel, bar.product_id)
     - bar.status = RESERVED, reserved_until = +N min
     - returns: reservation_id, amount_rial, price_lock_id

4. کارت‌کشی روی POS hardware (TalaMala terminal — payment_account اختصاصی)

5. POS app → POST /api/v1/pos/confirm
   Body: { reservation_id, trace_number, rrn, amount_rial, paid_at }
   • Backend در DB transaction:
     - INSERT pos_transactions (با terminal_id, trace_number, rrn)
     - Order.create(
         order_type=pos_sale, status=Paid,
         brand=<channel.brand>, payment_receiver=<channel.payment_account.company>
       )
     - INSERT order_items (با pure_gold_mg, buyback_credit_rial snapshot — D-32)
     - Inventory.consume(bar) → customer_id=resolved_user_id
     - Treasury.record(source=pos_sale, delta=+weight)
     - چون POS برای TalaMala است → payment_receiver=TalaMala:
       INSERT inter_company_ledger × 2 (rial + gold per بخش ۶.۴)
     - DealerSale (commission for dealer به‌صورت Gold-for-Gold)
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
      Treasury.record(source=marketplace_sale, +weight)
      # D-56 (قطعی): marketplace همیشه seller=Goldis و payment_receiver=Goldis
      # هیچ inter_company_ledger entry برای marketplace وجود ندارد
      # (حتی اگر brand=TalaMala — چون Goldis انحصاراً marketplace را اداره می‌کند)
      Outbox: ExternalOrderImported + OrderPaid + ...
    await adapter.acknowledge_orders(...)
    UPDATE channels.last_sync_at = now()
```

> **⚠️ D-56 (قطعی):** هیچ inter-company entry در marketplace نیست. تمام درآمد به Goldis می‌رود. TalaMala هیچ marketplace income مستقیم ندارد — فقط از فروش مستقیم سایتش (channel talamala_direct).

### ۱۲.۹. Inter-Company Settle (دستی، on-demand)

> **توجه**: نسخه‌ی قبلی این سند یک «Settlement daily worker» داشت. این **حذف شد** (D-06b). به‌جای آن، در لحظه‌ی هر sale ledger entry ساخته می‌شود و اپراتور هر زمان دستی settle می‌زند.

```
سناریوی typical:
1. TalaMala فروش می‌کند → دو entry (gold + rial) با status=open ثبت می‌شود
2. حسابدار/اپراتور Goldis تو پنل می‌بیند: GET /admin/inter-company/ledger?status=open
3. وقتی TalaMala معادل بهای طلای خام را به Goldis بانکی منتقل کرد:
   POST /admin/inter-company/settle-rial { creditor=Goldis, debtor=TalaMala, amount, notes }
   → FIFO consume open rial obligations از قدیمی‌ترین
4. وقتی Goldis طلای خام (گرانول/شمش بزرگ) را فیزیکی به انبار TalaMala تحویل داد:
   POST /admin/inter-company/settle-gold { creditor=TalaMala, debtor=Goldis, amount, notes }
   → FIFO consume open gold obligations
   + اپراتور می‌تواند یک inventory_movement جدا ثبت کند (ورود طلای خام به انبار TalaMala — این طلای خام برای hedging یا تولید بعدی است، نه refill شمش‌های فروخته‌شده)
```

هیچ worker اتوماتی نیست. اپراتور دستی tracking می‌کند.

### ۱۲.۱۰. Treasury alert

```
# D-47: این worker فقط هشدار/پشتیبان است. سدِ واقعی = چکِ inline سدِ سخت
#   در سرویسِ هر تراکنش (قبلِ commit؛ اگر از سقف رد شود تراکنش رد می‌شود).
worker هر ۳۰ ثانیه:
  for each metal:
    net = SUM(delta_amount_mg) where status IN ('open','partially_covered')  # علامت‌دار
    s = treasury_settings[metal]
    # سمتِ فروش (net مثبت):
    if net >= s.max_open_exposure_mg:
      if s.auto_block_at_cap: set sell-block flag
      notify admin (critical)
    elif net > 0 and net / s.max_open_exposure_mg >= warning_threshold:
      throttled notify admin (warning: sell side)
    # سمتِ خرید/بازخرید (net منفی):
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
- Headers الزامی: `Authorization: Bearer <jwt>`، `X-Channel-Code` (مگر در روتر‌های global/auth)
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
  # D-46: wallet_scope (نه company_code) زیرا goldis+aminzar هم Goldis Co. هستند
- GET `/wallet/ledger?wallet_scope=X&asset=Y`
- POST `/wallet/topup` { amount_rial } — شارژ wallet ریالی (per brand auto-routed)
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

### Physical purchase from wallet (به‌جای gold withdrawal)
- POST `/orders/physical-from-wallet` { from_wallet, product_id, pay_difference_in_rial }

### Buyback (به‌جای refund) — ۲ حالت در v1 (D-58)

**(a) بازخریدِ تحویل‌نشده** (آنلاین، اتومات):
- POST `/buyback/undelivered` { order_id } — بازخریدِ فوری سفارش تحویل‌نشده، wallet credit با‌فاصله

**(b) بازخریدِ حضوری** (حضوری، state machine):
- POST `/buyback/physical/request` { bar_id, target_location_id }
- GET `/buyback/physical/{id}` — برای کاربر مشاهده‌ی وضعیت
- POST `/admin/buyback/physical/{id}/receive` — کارشناس مرکز تحویل گرفت
- POST `/admin/buyback/physical/{id}/verify` — تأیید اصالت
- POST `/admin/buyback/physical/{id}/approve` — تأیید نهایی، wallet credit
- POST `/admin/buyback/physical/{id}/reject` — رد در هر مرحله با reason

**(c) بازخریدِ دیجیتال**:
- (endpoint جدا ندارد — از `/wallet/trades/sell` استفاده می‌شود — D-68)

### Fulfillment
- GET `/admin/fulfillment/tasks?status=X`
- POST `/admin/fulfillment/tasks/{id}/assign-self`
- POST `/admin/fulfillment/tasks/{id}/pick`
- POST `/admin/fulfillment/tasks/{id}/pack`
- POST `/admin/fulfillment/tasks/{id}/handover` { courier, tracking }
- POST `/admin/fulfillment/tasks/{id}/confirm-delivery` { otp, serial? } — D-78 (جایگزینِ `/complete`؛ فقط نقشِ مقصد، با OTPِ گیرنده)

### Treasury
- GET `/admin/treasury/positions?status=open&metal=gold`
- POST `/admin/treasury/positions/{id}/cover` { amount_mg, source_note }
- GET `/admin/treasury/snapshot`
- PUT `/admin/treasury/settings`

### Inter-Company Ledger (بخش ۶ — جایگزین Settlement قدیمی)
- GET `/admin/inter-company/ledger?creditor=X&debtor=Y&asset=gold|rial&status=open|partial|settled` — لیست obligations
- GET `/admin/inter-company/balance?company_a=X&company_b=Y` — net balance بین دو شرکت
- POST `/admin/inter-company/settle-rial` { creditor_company_id, debtor_company_id, amount_rial, notes } — تأیید پرداخت ریالی، FIFO consume open entries
- POST `/admin/inter-company/settle-gold` { creditor_company_id, debtor_company_id, amount_mg, notes } — تأیید تحویل طلا، FIFO consume
- GET `/admin/inter-company/settle-actions?company_a=X&company_b=Y&date_from=...` — audit log همه‌ی settle actions
- GET `/admin/inter-company/reports?period=month` — جمع‌بندی دوره‌ای (aggregate query)

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

هر transaction که داده‌ی حساس را تغییر می‌دهد → outbox_events entry در **همان transaction**. publisher worker جدا فالو می‌کند.

```python
async def mark_order_paid(self, order_id: UUID, payment_id: UUID):
    async with self.uow.begin():
        order = await self.repo.get_for_update(order_id)
        if order.status == OrderStatus.Paid:
            return
        order.status = OrderStatus.Paid
        order.paid_at = utcnow()
        await self.inventory_svc.consume_reservation(order)
        # D-77: create_task اینجا صدا زده نمی‌شود — task فقط هنگامِ
        #   «درخواستِ تحویل» ساخته می‌شود (فروشِ امانی task ندارد).
        #   استثنا: تحویلِ فوریِ POS/فروشگاه → همان‌جا create_task(order_item, bar).
        await self.treasury_svc.record_open_position(order)   # D-47: per پای؛ چکِ inline سدِ سخت قبلِ این
        # D-06b/D-69: settlement_svc حذف شد. اگر فروشِ غیر-Goldis:
        if order.payment_receiver_company_id != GOLDIS_ID:
            await self.inter_company_svc.record_obligations(order)  # جفتِ rial(P_hedge)+gold
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
OrderCreated, OrderPaid, OrderCancelled

# Payment
PaymentStarted, PaymentVerified, PaymentFailed

# POS
PosTransactionImported, PosOrderCreated

# Wallet
WalletCredited, WalletDebited, WalletLocked, WalletUnlocked,
WalletToppedUp, WalletTopupFailed

# Trade
DigitalGoldBought, DigitalGoldSold

# Buyback (دو حالت — بازخریدِ دیجیتال = DigitalGoldSold)
BuybackCompleted,                                    # (a) بازخریدِ تحویل‌نشده (آنلاین)
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
InterCompanyObligationReversed     # موقع buyback یا cancel

# Fulfillment
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

| Worker | فرکانس | تنظیم |
|--------|----------|---------|
| `outbox_publisher` | continuous (poll 1s) | parallelism=2 |
| `pricing_fetcher` | dynamic per source | configured |
| `marketplace_poller` | 60s | per channel |
| `lock_expirer` | 30s | — |
| `treasury_monitor` | 30s | — |
| `notification_dispatcher` | continuous | parallelism=4 |
| `payout_processor` | 30s | — |
| `pos_transaction_reconciler` | hourly | per channel |
| `fulfillment_reminder` | hourly | — |

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
  - `wallet.{user_id}.{company_code}` — تغییر balance
  - `order.{user_id}` — تغییر status
  - `pricing.channel.{channel_id}` — تغییر قیمت
  - `treasury.alert` — admin only
  - `fulfillment.task.{location_id}` — انباردار
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
- ذخیره: یا در جدول `idempotency_keys` با TTL=۲۴h، یا در ستون idempotency_key entity (پیشنهاد دوم: ساده‌تر)

### Rate limiting
- `slowapi` (in-memory) برای فاز ۱، بعداً Redis-backed
- مخصوصاً سخت‌گیر روی: `/auth/send-otp` (۳/min)، `/payments/start`، `/wallet/trades/*`، `/withdrawals/*` (۱۰/min per user)

### Shahkar integration
- sub-module `kyc.shahkar`:
  - `verify(mobile, national_id) → ShahkarResult`
  - Cache result for ۳۰ روز
  - Re-verify اگر `national_id` تغییر کرد

### Audit
- هر action با priority بالا → audit_logs.insert در همان transaction
- لیست actions الزامی: تغییر قیمت، manual override، inventory adjustment، wallet adjustment manual، تغییر KYC level/limits، تأیید/رد withdrawal ریال، mark treasury covered، **inter-company settle (rial/gold)**، buyback (digital و physical)، تغییر role/permission، sync دستی marketplace، تغییر mapping، تغییر payment_account، inventory_movement بین انبارها (مثلاً تحویل طلای خام از Goldis به TalaMala برای hedging)
- audit_logs **INSERT ONLY** — DB grant level: `REVOKE UPDATE, DELETE ON audit_logs FROM app_user`

### Payment callback security
- Signature verification اگر provider پشتیبانی کند (Sepehr/Parsian)
- Replay prevention: idempotency_key + در DB ذخیره می‌شود

### Frontend security
- CORS: only configured domains per channel
- CSP headers
- SameSite cookies برای web

---

## ۱۸. Migration Plan — Fresh Start (D-23 updated)

> **تصمیم نهایی تیم:** v5 از **صفر کامل** شروع می‌شود. هیچ data از v4 به v5 منتقل نمی‌شود.

### اصول fresh start

- ❌ **No data migration** — wallet balances، orders، KYC، dealers، bars، tickets، articles — هیچ‌کدام از v4 منتقل نمی‌شوند
- ❌ **No ETL scripts** نیاز نیست
- ❌ **No reconcile** بین v4 و v5
- ✅ **Greenfield**: کاربران v5 از صفر ثبت‌نام می‌کنند، KYC از نو، wallet با balance=0

### استراتژی cutover

این تصمیم نیاز به **پلن جداگانه از تیم بیزینس** دارد که خارج از scope این سند است:

1. **چه می‌شود با کاربران v4 که balance دارند؟**
   - اعلام: قبل از cutover کاربران باید balance خود را به ریال تبدیل و برداشت کنند
   - یا: بعد از cutover با تماس manual reconciliation
   - این تصمیم تجاری/حقوقی است — خارج از scope architectural

2. **چه می‌شود با dealer ها؟** (sub-dealer حذف شد — D-73)
   - باید قبل از v5 launch، در پنل v5 ثبت‌نام مجدد شوند
   - manual onboarding

3. **چه می‌شود با bar های فیزیکی موجود در انبار؟**
   - فقط فیزیکی هستند، در v5 با sticker جدید یا re-scan وارد inventory شوند
   - یا: یک "import bars" admin tool یک‌بار اجرا شود (این *تنها* tool migration که شاید لازم باشد)

### مزایای fresh start

- پیاده‌سازی v5 ساده‌تر — هیچ data shape سازگاری نیاز نیست
- ETL scripts، reconcile، D-day window پیچیده — همه حذف شدند
- زمان development ~ ۱-۲ هفته کمتر (فاز ۷ migration در roadmap)

### معایب

- کاربران v4 تجربه‌ی re-onboarding خواهند داشت
- نیاز به communication plan قبل از cutover
- bar های فیزیکی موجود نیاز به admin tool یا manual import

### نکته‌ی مهم — POS

- `talamala_pos` (Android) **هنوز پروداکشن نرفته** (D-44) — هیچ backward compatibility نیاز نیست. Android app از اول با API v1 جدید کار می‌کند.

### Tool احتمالی تنها

اگر در آینده تصمیم گرفته شود bars فیزیکی موجود از v4 وارد شوند، یک admin tool یک‌بار مصرف لازم می‌شود:

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
- Settlement rule calculations (per rule type)
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
- publisher دو بار publish نمی‌کند

### CI
- pytest + mypy + ruff + black
- Alembic up/down test

---

## ۲۰. ابهامات — وضعیت

تمام ابهاماتِ اصلی (O-01…O-20) و سطح‌۲ (**Q-01…Q-10**) **حل شده‌اند**. نقاطِ کشف‌شده‌ی بازبینی (A-1…A-13، F-1…F-4) هم حل شده‌اند. استدلال و نگاشتِ Q→D در **§۲.۵ (دفترِ تصمیمات)**:

| Q | حل‌شده در | Q | حل‌شده در |
|---|---|---|---|
| Q-01 split payment | §۱۲.۵ | Q-06 سطوح KYC | D-61 |
| Q-02 physical buyback | §۱۲.۵.۲ب | Q-07 inventory aging/transfer | D-62 |
| Q-03 قیمت buyback | D-53/D-59 | Q-08 انتخاب درگاه | D-63 |
| Q-04 settlement_rules | منتفی (D-06b) | Q-09 برداشت ریال | D-64 |
| Q-05 reverse در buyback | D-59 | Q-10 منبع شمشِ wallet | D-60 |

> **مواردِ بازِ باقی‌مانده در §۰.۱** فهرست شده‌اند (تمرکزِ بازبینیِ بعدی آنجاست).

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
12. Wallet (per-company multi-asset ledger)

### فاز ۲ — Transactional (هفته ۴-۵)
13. Inventory
14. Cart
15. Order (purchase only)
16. Payment (Zibal + Sepehr — برای دو tenant)
17. Fulfillment

### فاز ۳ — Treasury + Trade + Settlement (هفته ۶-۷)
18. Treasury basic (record + read) — با merge شدن hedging (D-42)
19. Wallet trades (digital_trade buy/sell)
20. Withdrawal **فقط ریال** (D-31 — gold withdrawal حذف شد)
21. physical_purchase_from_wallet flow (به‌جای gold withdrawal)
22. Buyback (دو حالت در v1):
    - (a) بازخریدِ تحویل‌نشده — آنلاین اتومات (فروشِ اصلی reverse نمی‌شود)
    - (b) بازخریدِ حضوری — state machine کامل (PhysicalRequested → … → Completed)
    - (بازخریدِ دیجیتال = همان `digital_trade sell` — جدا پیاده نمی‌شود)
23. Inter-Company Ledger (D-06b): جدول `inter_company_ledger`، endpointهای settle، FIFO consume. **بدون settlement_rules، بدون worker روزانه.**
24. Treasury alert worker

### فاز ۴ — DealerNetwork (هفته ۸-۹)
23. Dealer + Tier + dealer_commission_rates + dealer_commission_ledger (بدون SubDealer/شبکه — D-73)
24. POS context (sales_channels.type=pos)
25. POS reserve→confirm flow
26. DealerSale + commission

### فاز ۵ — Marketplace (هفته ۱۰)
27. Adapter interface + skeleton
28. DigiKala adapter (mode=`push_managed` per D-37)
29. Marketplace poller worker

### فاز ۶ — Realtime & polish (هفته ۱۱)
30. SSE endpoint + broadcaster
31. Notification preferences UI (API)
32. Admin reporting endpoints
33. Audit viewer API

### فاز ۷ — Launch (هفته ۱۲)
> **توجه: Migration از v4 وجود ندارد (D-23: Fresh start)** — فاز ۷ شامل launch tasks است نه ETL.

34. Communication plan با کاربران v4 (خارج از scope توسعه — تیم بیزینس)
35. Staging environment final smoke testing
36. Production deployment + DNS switch
37. (Optional) Admin tool یک‌بار مصرف import-bars-from-csv برای bars فیزیکی موجود v4

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
- زبان comment ها: انگلیسی. زبان commit message: انگلیسی. زبان UI/پیام‌های کاربر: فارسی.
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
- هرگز کدی نزن که قبلاً پرسیده‌اش روشن نیست

### قواعد مخصوص migration

- هیچ change ای روی DB پروداکشن v4 بدون تأیید
- ETL scripts را به‌صورت idempotent بنویس (قابل re-run)
- Dry-run همیشه قبل از run واقعی

---

## ۲۲. پایان سند

این سند نتیجه‌ی:
- ۳ دور Q&A با تیم Goldis Operations
- ادغام بهترین بخش‌های پیشنهاد ChatGPT
- بازنویسی کامل مدل tenancy
- اضافه کردن Settlement، Fulfillment، POS به‌عنوان bounded contexts درجه‌یک
- explicit کردن همه‌ی architectural decisions (تا LLM پیاده‌ساز مجبور به assumption نباشد)

پیاده‌سازی این پروژه با رعایت این سند، حدود **۱۲ هفته** برای فاز ۰ تا ۷ تخمین زده می‌شود (با فرض ۲-۳ مهندس async-experienced).

برای start، LLM پیاده‌ساز را با این prompt کوتاه shoot کنید:

> «این سند معماری TalaMala v5 است. آن را به‌طور کامل بخوان. قبل از کدنویسی، فایل‌های talamala_v4/CLAUDE.md و talamala_pos/CLAUDE.md را هم بخوان. سپس فاز ۰ از بخش ۲۱ (Infrastructure) را مرحله‌به‌مرحله کد بزن. بعد از هر مرحله توقف کن و تأیید بگیر. ابهامات بخش ۲۰ که به فاز فعلی مربوط است را اول از من بپرس.»
