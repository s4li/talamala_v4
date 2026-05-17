# سند معماری TalaMala v5 — پلتفرم متمرکز چندبرندی فروش، خرید و مدیریت دارایی طلا

> **نسخه:** 2.0 (Final Draft)
> **تاریخ:** 2026-05-13
> **وضعیت:** آماده برای تأیید نهایی تیم و سپس فاز پیاده‌سازی
> **منبع:** سه دور Q&A عمیق با تیم Goldis Operations + ادغام پیشنهاد ChatGPT

---

## ۰. راهنمای استفاده از این سند

این سند **ورودی فاز پیاده‌سازی** است. هنگام استفاده با یک LLM به‌عنوان مهندس پیاده‌ساز:

1. کل این سند را یک‌بار به مدل بده تا context کامل بسازد.
2. **مرحله به مرحله** کد بخواه — نه یک‌جا. ترتیب پیشنهادی در بخش ۲۱ آمده.
3. هر تصمیم architectural اینجا **explicit** است — assumption نیست.
4. در فاز پیاده‌سازی، LLM باید قبل از کدنویسی هر context، فایل `talamala_v4/CLAUDE.md` و `talamala_pos/CLAUDE.md` را بخواند تا با current state آشنا شود.
5. ابهامات باقیمانده در بخش ۱۹ لیست شده‌اند — قبل از پیاده‌سازی context مربوطه باید حل شوند.

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
| D-04 | Wallet scope | **Per-legal-entity** — کاربر دو wallet دارد: یکی Goldis (شامل brand Goldis+AminZar)، یکی TalaMala | تیم |
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
| D-14 | Digital gold inventory | **بدون جدول جداگانه** — همان Treasury Position با `max_open_exposure_mg` cap | معمار |
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
| D-29 | AminZar wallet | **merge** در Goldis wallet (نه جدا) |
| D-30 | Decimal precision | Standard: `rate=NUMERIC(20,2)`، `percent=NUMERIC(6,3)`، `coefficient=NUMERIC(8,4)`، `wage_value=NUMERIC(12,4)` |
| D-31 | **برداشت طلا** | **حذف کامل** — کاربر نمی‌تواند طلای دیجیتال را به‌صورت فیزیکی برداشت کند. به‌جای آن: فروش به ریال (digital_trade sell) یا خرید کالای فیزیکی با wallet XAU_MG |
| D-32 | **Refund/Buyback model** | **Refund حذف. Buyback با ۳ زیرflow در v1**: (a) `cancel_before_delivery` — لغو آنلاین تا قبل از تحویل، (b) `physical_buyback` — برگرداندن شمش فیزیکی تحویل‌شده در یک مرکز buyback authorized، (c) `digital_buyback` — فروش طلای دیجیتال از wallet. در هر سه: وزن خالص طلا (`weight × purity / 1000`) به wallet XAU_MG برمی‌گردد + `buyback_credit_rial` (snapshot موقع خرید) به wallet IRR. اجرت/مالیات/سود سوخت می‌شود. |
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

### تصمیمات جلسه‌ی بازبینی 2026-05-16/17 (Override — D-46…D-72)

> این تصمیم‌ها در یک جلسه‌ی بازبینی قدم‌به‌قدم با تیم نهایی شد و **بعضی تصمیم‌های قبلی را override می‌کند**. هرجای سند با این‌ها تعارض داشت، **این‌ها معتبرند**.

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
| D-72 | **حل A-9 — کارمزدِ معامله‌ی دیجیتال = مارجینِ نردبان + spreadِ دوطرفه** | (الف) «کارمزدِ معامله‌ی دیجیتالِ نقش‌محورِ v4» (`gold_fee_customer/dealer_percent`…) مفهومِ جدا **نیست** — همان فاصله‌ی نردبانِ D-65 است (`P_retail−P_hedge` مشتری، `P_partner−P_hedge` همکار). افزونگیِ مدلِ v4 حذف. (ب) `channel_pricing_formulas` بُعدِ `trade_side VARCHAR(10) NULL` (buy|sell|NULL) می‌گیرد تا **spreadِ دوطرفه** ممکن شود: قیمتِ خرید (کاربر می‌خرد) و قیمتِ فروش (کاربر می‌فروشد) مارجینِ مستقل دارند؛ رزولوشن با همان `priority`. Invariantِ D-65 هر دو سمت: قیمتِ خرید ≥ P_hedge؛ قیمتی که به فروشنده‌ی کاربر می‌دهیم ≤ P_hedge (حاشیه منفی نشود). قیمتِ `digital_trade sell` (= همان «بازخریدِ دیجیتال» D-68) از فرمولِ `trade_side=sell` می‌آید. | Pricing، Wallet، §۱۱.۴ |
| D-71 | **حل A-8 — برچسبِ scope روی شمش (`sale_wallet_scope`)** | `bars` ستونِ `sale_wallet_scope VARCHAR(20) NULL` می‌گیرد: در لحظه‌ی فروش از scopeِ سفارش (goldis/aminzar/talamala) پر و **IMMUTABLE** (انتقالِ مالکیت — D-55 — عوضش نمی‌کند، چون حساب به فروشِ اول گره خورده). همه‌ی مسیرهای بازخرید/انتقال/گزارشِ تفکیکیِ D-46 از این برچسب تصمیم می‌گیرند، نه استنتاجِ ضمنی. شمشِ فروش‌نرفته=`NULL` (مالکیتِ شرکتی). برای کارت‌هدیه/مارکت‌پلیس (بدون ثبت‌مالکیت — D-54): `sale_wallet_scope` پر می‌شود (برای خزانه/بین‌شرکتی) ولی `customer_id=NULL` — دو بُعدِ مستقل. **قاعده:** بازخریدِ آنلاین فقط در همان scope/وب‌سایتی که خرید انجام شده مجاز است. | Inventory، Wallet، Buyback، §۱۱.۵ |
| D-70 | **حل A-7 — تعهدِ بین‌شرکتیِ digital_trade sell غیر-Goldis** | جمله‌ی مبهمِ §۱۲.۴ («Settlement: Goldis طلب از TalaMala») با مدلِ صریح جایگزین شد. scope غیر-Goldis: جفتِ تازه‌ی مخالفِ فروش → `TalaMala→Goldis طلا amount_mg` + `Goldis→TalaMala ریال P_hedge_per_mg×amount_mg`. scope=Goldis: هیچ تعهد بین‌شرکتی، فقط خزانه‌ی `−` تک‌پاییِ `digital_sell` (D-67). آینهٔ دقیقِ §۱۲.۳/D-69 و همان مسیرِ یکتای D-68. مابه‌التفاوتِ (P_hedge − پرداختی به کاربر) حاشیه‌ی scope فروشنده. | Inter-Company، Treasury، §۱۲.۴ |
| D-69 | **حل A-6 — یکدستیِ digital_trade buy غیر-Goldis با §۱۲.۱** | §۱۲.۳ اصلاح: مبنای تعهدِ بین‌شرکتیِ خرید دیجیتالِ scope غیر-Goldis = **`P_hedge_per_mg × amount_mg`** (D-65)، نه `internal_base_price` و نه قیمتی که کاربر پرداخت. صریح: خرید دیجیتالِ scope غیر-Goldis از نظر خزانه/بین‌شرکتی **هم‌سنگِ فروشِ فیزیکیِ غیر-Goldis** است (همان مدلِ §۱۲.۱)؛ تنها تفاوت: شمش/اجرت ندارد و خزانه‌اش تک‌پاییِ `digital_buy` است (D-67). مابه‌التفاوتِ (قیمتِ کاربر − P_hedge) سودِ scope فروشنده. §۱۲.۲ (AminZar، Goldis-side) بدون تعهد بین‌شرکتی — تأیید شد. | Inter-Company، Treasury، §۱۲.۲، §۱۲.۳ |
| D-68 | **حل A-5 — یکی‌سازی digital_buyback با digital_trade sell** | «بازخریدِ دیجیتال» یک مسیرِ فنیِ جدا **نیست** — صرفاً همان **`digital_trade` با `trade_side=sell`** است (نامِ بازاریابی). زیرflow (c) `digital_buyback` **حذف** می‌شود. در نتیجه Buyback فقط **۲ حالت** دارد (نه ۳): تحویل‌نشده + حضوری — هر دو مرتبط با شمشِ فیزیکی (D-58/D-59). منسوخ‌ها: `order_type=buyback` فقط برای فیزیکی؛ endpointهای `/buyback/quote` و `/buyback/digital` حذف → استفاده از `/wallet/trades/sell`؛ رویدادِ `DigitalBuybackCompleted` حذف = `DigitalGoldSold`؛ در §۵.۲ مدخلِ `digital_buyback` صرفاً **مترادفِ `digital_sell`** است؛ بندِ «(c)» در D-32/§۱۲.۵.۲/Q-03/roadmap منسوخ. قیمتِ فروشِ دیجیتال از نردبانِ D-65 سمتِ فروش می‌آید (همان نقشی که `buyback_quote` ادعا می‌کرد). | Order، Wallet، Treasury، §۵.۲، §۱۲.۴، §۱۲.۵.۲، §۱۳، §۱۴ |
| D-67 | **حل A-4 — بازنویسی §۵.۲ به مدلِ تک‌پایی/دوپایی** | `treasury_positions` per **پای** ثبت می‌شود نه per تراکنش؛ علامت از پای می‌آید نه `source_type`. تک‌پایی: `+`=`order_physical`/`pos_sale`/`marketplace_sale`/`digital_buy`؛ `−`=`hedge_buy`/`digital_sell`/`digital_buyback`. دوپایی (net≈صفر): `buyback` تحویل‌نشده/حضوری (D-59) و `physical_purchase_from_wallet` (D-66). برچسبِ ثابتِ `−` برای `buyback`/`physical_purchase_from_wallet` در §۵.۲ قدیمی **همان باگِ تک‌پایی** بود که پیاده‌ساز به آن استناد می‌کرد. | Treasury، §۵.۲ |
| D-66 | **حل A-3 — physical_purchase_from_wallet دوپایی** (آینهٔ D-59) | خرید کالای فیزیکی با کیف = تبدیلِ digital→physical. دو پای مستقل: پای۱ `−gold_part_mg` (مصرفِ طلای دیجیتالِ کیف)، پای۲ `+pure_gold_mg` (خروجِ شمشِ فیزیکی = فروشِ فیزیکی). **خزانه‌ی خالص ≈ صفر**، نه `−gold_part_mg`. اگر فروش غیر-Goldis بود، تعهدِ بین‌شرکتیِ پای۲ مثل هر فروشِ فیزیکی با مبنای P_hedge (D-65). متنِ §۱۲.۵ که فقط `delta=-gold_part_mg` داشت **باگ** بود (شمشِ هج‌نشده از سیستم خارج و exposure گم می‌شد). | Treasury، Inter-Company، §۱۲.۵ |
| D-59 | **حل Q-05 — بازخرید فروش را معکوس نمی‌کند** | بازخرید **هرگز** تعهدهای بین‌شرکتیِ فروشِ اصلی را معکوس نمی‌کند (`reverses_ledger_id` برای فروش استفاده نمی‌شود). هر بازخرید **دو پای مستقل** دارد: پای۱ طلا به کیف کاربر (+pure_gold_mg)، پای۲ منبع (شمش فیزیکی برمی‌گردد یا طلای کیف مصرف می‌شود، −pure_gold_mg). نتیجه: **تحویل‌نشده/حضوری = تبدیل physical↔digital ⇒ خزانه ≈ صفر، هیچ جفت تعهد طلاییِ تازه‌ای، فقط `buyback_credit_rial` به‌عنوان هزینه‌ی ریالی ثبت می‌شود.** **دیجیتال = خروج واقعی طلا ⇒ خزانه −pure_gold_mg + یک جفت تعهد تازه‌ی مخالف (TalaMala→Goldis طلا، Goldis→TalaMala ریال) به قیمت خامِ لحظه‌ی بازخرید.** این، باگِ ضمنیِ «buyback → −pure_gold_mg» در §۵.۲/§۱۲.۵.۲ را برای حالت‌های فیزیکی/تحویل‌نشده تصحیح می‌کند (دوبار-حساب). جزئیات گرد‌کردن/منبع‌قیمت به فاز پیاده‌سازی. | Inter-Company، Treasury، §۵.۲، §۱۲.۵.۲ |

> **⚠️ اثر روی scope/تخمین:** D-47، D-48 و D-53 scope را نسبت به سند اولیه سنگین‌تر کرده‌اند (supplier_purchase که خارج بود حالا داخل است؛ سقف دوطرفه؛ گیت ثبت‌مالکیت در بازخرید). D-58/D-59 برعکس scope بازخرید را **ساده‌تر** کرده‌اند (حذف منطق cancel/reverse). تخمین ۱۲ هفته‌ی بخش ۲۲ باید با لحاظ این‌ها بازبینی شود.

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
   • talamala_digikala (brand=TalaMala, type=marketplace, payee=TalaMala)
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

## ۴. مدل Wallet (Per-legal-entity)

### ۴.۱. ساختار

```
User Ali (mobile=0912...)
├── KYC: یکی، مشترک
├── Wallet at Goldis Co.                ← شامل brand Goldis + brand AminZar
│   ├── IRR balance
│   ├── XAU_MG balance
│   └── XAG_MG balance (آینده)
└── Wallet at TalaMala Co.              ← فقط brand TalaMala
    ├── IRR balance
    ├── XAU_MG balance
    └── XAG_MG balance (آینده)
```

### ۴.۲. قواعد

- Wallet کاربر **در یک legal_entity فقط در همان legal_entity قابل خرج است**
- مثال: کاربر در brand TalaMala خرید می‌کند → wallet TalaMala استفاده می‌شود
- مثال: کاربر در brand Goldis یا AminZar خرید می‌کند → wallet Goldis استفاده می‌شود (D-29: AminZar wallet جدا ندارد)
- **هیچ transfer مستقیمی بین دو wallet نیست**. اگر کاربر بخواهد، باید از یکی فروش به ریال و سپس برداشت ریال، بعد deposit به دیگری.
- **UX (D-40):** Frontend هر brand فقط wallet مربوط به خودش را نشان می‌دهد. کاربر در frontend AminZar وقتی balance ببیند، در پشت‌پرده wallet Goldis است ولی به کاربر فقط «موجودی شما» نمایش داده می‌شود — نه نام Goldis. در admin panel هر دو wallet در tab های جدا visible است.

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

-- Append-only ledger
CREATE TABLE wallet_ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),
    company_id BIGINT NOT NULL REFERENCES companies(id),
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
    UNIQUE (company_id, idempotency_key)
);
CREATE INDEX ix_ledger_user_company_asset
    ON wallet_ledger_entries (user_id, company_id, asset_type_id, created_at DESC);

CREATE TABLE wallet_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(id),
    company_id BIGINT NOT NULL REFERENCES companies(id),
    asset_type_id BIGINT NOT NULL REFERENCES asset_types(id),
    amount_minor BIGINT NOT NULL,
    reference_type VARCHAR(50) NOT NULL,
    reference_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    expires_at TIMESTAMPTZ NULL,
    idempotency_key VARCHAR(100) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, idempotency_key)
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

> **⚠️ D-67:** `treasury_positions` **per پای** ثبت می‌شود، نه per تراکنش. علامت از **پای** می‌آید نه از `source_type`. بعضی تراکنش‌ها تک‌پایی‌اند (علامتِ ثابت)، بعضی دوپایی (یک `+` و یک `−`، خالص ≈ صفر).
>
> `treasury_positions.delta_amount_mg` بر اساس نگاه **Goldis**:
>
> **تراکنش‌های تک‌پایی (علامتِ ثابت):**
> - **+** (exposure باز — Goldis بدهکار طلا شد): `order_physical`، `pos_sale`، `marketplace_sale`، `digital_buy` (در هر brand، شامل فروش‌های خود Goldis — چون Goldis باید خام بخرد)
> - **−** (exposure بسته): `hedge_buy`، `digital_sell` (digital_trade sell — شاملِ آنچه قبلاً `digital_buyback` نامیده می‌شد، D-68)
>
> **تراکنش‌های دوپایی (net ≈ صفر):**
> - `buyback` تحویل‌نشده/حضوری (D-59): پای `+pure_gold_mg` (طلا به کیف) و پای `−pure_gold_mg` (شمشِ برگشتی/مصرف) ⇒ خنثی
> - `physical_purchase_from_wallet` (D-66): پای `−gold_part_mg` (مصرفِ طلای دیجیتالِ کیف) و پای `+pure_gold_mg` (خروجِ شمشِ فیزیکی) ⇒ خنثی
>
> sum(delta_amount_mg WHERE status IN ('open','partially_covered')) = current open exposure

### ۵.۳. Cap و alert

- `treasury_settings.max_open_exposure_mg` per metal (مثلاً ۵ کیلو طلا)
- `warning_threshold_percent` (مثلاً ۷۰٪)
- `auto_block_at_cap`: اگر true، خرید دیجیتال در همه brandها block می‌شود تا coverage

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

### ۶.۷. Reverse در صورت Buyback یا Cancel

اگر سفارش قبل از تحویل cancel شود یا physical buyback انجام شود، باید obligation های قبلی reverse شوند:

- **cancel_before_delivery**: همان جفت ledger entry که در sale ساخته شده بود، با مقدار منفی reverse می‌شود (یا دو entry جدید با direction معکوس و `reverses_ledger_id` اشاره به entry اصلی)
- **physical_buyback**: مشابه — TalaMala شمش را پس می‌گیرد و طلای خام به Goldis برمی‌گردد (در عمل)، پس obligation ها معکوس می‌شوند
- **digital_buyback** از wallet: مشابه از نظر hedging — کاربر طلا را می‌فروشد به TalaMala، TalaMala باید این طلا را به Goldis برگرداند

جزئیات flow در بخش Buyback (بعد).

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

### ۷.۲. ⚠️ Supplier Purchase — override شد به «داخل scope» (D-48)

> **⚠️ این بخش با D-48 override شد.** خرید از کارخانه **داخل scope v1** است: جریانِ **فقط-طلا** روی همان batch preorder (Goldis اصل‌طلا + اجرت‌طلا می‌دهد، شمش حک‌شده می‌گیرد؛ تعهد روی `inter_company_ledger` با `asset='gold'`, `source_type='supplier_purchase'`). `purchase_wage_percent` عملیاتی است؛ طلای اجرت = هزینه‌ی حسابداری بدون اثر خزانه. متن قدیمی زیر فقط برای تاریخچه نگه داشته شده.

تصمیم قبلی (**override شده** — دیگر معتبر نیست): **فرآیند خرید Goldis از کارخانه‌ها (AminZar و TalaMala) داخل سامانه پیاده‌سازی نمی‌شود.** این تسویه‌ها بیرون از پلتفرم (به‌صورت دستی/توافقی) انجام می‌شوند.

این یعنی:
- هیچ context `supplier_purchase` در v1 نداریم
- هیچ `inter_company_ledger` entry با `source_type='supplier_purchase'` ساخته نمی‌شود
- در v1، شمش‌ها صرفاً به‌صورت یک **intake event** ساده وارد سامانه می‌شوند (status `preorder` → `in_stock`)، بدون اثر مالی روی ledger
- `purchase_wage_percent` فقط به‌عنوان **metadata** روی product نگه داشته می‌شود (برای reporting و آینده)

این تصمیم scope را خیلی ساده‌تر می‌کند. در v2+، اگر تیم نیاز ببیند، context supplier_purchase اضافه می‌شود.

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
   - (هیچ ledger entry — supplier purchase خارج از scope است)
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
    quantity INT NOT NULL,
    amount_mg BIGINT NULL,
    source_location_id BIGINT NOT NULL REFERENCES inventory_locations(id),
    destination_type VARCHAR(30) NOT NULL,
    -- customer_pickup | courier | store | internal_transfer
    destination_address VARCHAR(500) NULL,
    courier_provider VARCHAR(50) NULL,
    tracking_number VARCHAR(100) NULL,
    assigned_to BIGINT NULL REFERENCES users(id),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    -- pending | picking | picked | packed | handed_over | delivered | cancelled
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    picked_at TIMESTAMPTZ NULL,
    packed_at TIMESTAMPTZ NULL,
    handed_over_at TIMESTAMPTZ NULL,
    delivered_at TIMESTAMPTZ NULL
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
1. Order paid → trigger Fulfillment.create_task(order)
2. INSERT fulfillment_tasks (status=pending)
3. انباردار از admin panel: GET /admin/fulfillment/tasks?status=pending
4. انباردار: POST /admin/fulfillment/tasks/{id}/assign-self
5. POST /admin/fulfillment/tasks/{id}/pick  → status=picking → picked
6. POST /admin/fulfillment/tasks/{id}/pack
7. POST /admin/fulfillment/tasks/{id}/handover  → courier info
8. POST /admin/fulfillment/tasks/{id}/complete → status=delivered
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
| 15 | **dealer** | Per-company (opt-in) | Dealer، Tier، SubDealer، Sale، Commission |
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
    -- RAW | ASSIGNED | RESERVED | SOLD
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
    trade_side VARCHAR(10) NULL,             -- buy | sell (فقط برای digital_trade و buyback)
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
    order_id UUID NOT NULL REFERENCES orders(id),
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
    company_id BIGINT NOT NULL REFERENCES companies(id),  -- wallet کدام legal entity
    brand_id BIGINT NOT NULL REFERENCES brands(id),       -- از کدام brand شارژ شد
    sales_channel_id BIGINT NOT NULL REFERENCES sales_channels(id),
    amount_rial BIGINT NOT NULL CHECK (amount_rial > 0),
    payment_id UUID NULL REFERENCES payments(id),
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    -- created | gateway_started | completed | failed | expired
    idempotency_key VARCHAR(100) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    UNIQUE (company_id, idempotency_key)
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

   e. **اگر payment_receiver != Goldis** (یعنی فروش TalaMala-side):
      INSERT inter_company_ledger × 2:
        (debtor=TalaMala, creditor=Goldis, asset=rial,
         amount=sum(order_items.raw_hedge_price_rial))   # D-65
        (debtor=Goldis, creditor=TalaMala, asset=gold,
         amount=sum(order_items.pure_gold_mg))
5. POST /api/v1/payments/start → TalaMala IPG → redirect to bank
6. Bank callback → POST /api/v1/payments/callback/zibal [IDEMPOTENT]
7. on verified:
   - UPDATE payments status=verified
   - Order.mark_paid:
     • UPDATE orders status=Paid
     • Inventory.consume(bar) → status=SOLD, customer_id=user_id
     • Fulfillment.create_task(order_item) → status=pending
     • Treasury.record(source=order_physical, delta=+weight_mg,
                       triggered_by_brand=TalaMala)
     • اگر payment_receiver != Goldis:
       INSERT inter_company_ledger × 2 (rial + gold per بخش ۶.۴)
     • Accounting.record_event
     • Outbox: OrderPaid, FulfillmentTaskCreated, TreasuryPositionOpened,
               InterCompanyObligationCreated, AccountingEventCreated
     • Notification → user
8. انباردار → /admin/fulfillment/tasks → pick → pack → handover → delivered
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
   total_gold_mg_required = product.weight_mg + wage_mg
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
    - Fulfillment.create_task
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

### ۱۲.۵.۲. Buyback — مدل یکپارچه برای v1 (سه زیرflow)

> **⚠️ override D-58/D-59:** «لغو» وجود ندارد — زیرflow (a) دیگر `cancel_before_delivery` با `Order.status=Cancelled` نیست؛ یک **بازخریدِ آنلاینِ مستقل** است که شمش هنوز دستِ ماست. فروش اصلی همیشه معتبر می‌ماند و **هیچ‌وقت معکوس نمی‌شود**. اثر خزانه/بین‌شرکتی طبق D-59 (تحویل‌نشده/حضوری ⇒ خنثی + فقط هزینه‌ی ریالی؛ دیجیتال ⇒ خزانه − + جفت مخالف). متن سه‌زیرflow زیر با همین لنز خوانده شود.

> **D-32:** Refund نداریم. به‌جای آن **Buyback** با **سه زیرflow** در v1 پیاده می‌شود:
>
> | زیرflow | trigger | شرایط | تأیید |
> |---|---|---|---|
> | (a) `cancel_before_delivery` | کاربر تو سایت دکمه می‌زند | bar.status=SOLD، delivered_at IS NULL، fulfillment_task.status IN ('pending', 'picking') | اتومات (آنلاین) |
> | (b) `physical_buyback` | کاربر شمش فیزیکی را حضوری می‌برد | bar.status=SOLD، delivered_at IS NOT NULL | کارشناس مرکز Authorized |
> | (c) `digital_buyback` | کاربر در سایت طلای دیجیتال wallet را می‌فروشد | wallet XAU_MG balance کافی | اتومات (آنلاین) |
>
> **در هر سه**:
> - `weight × purity / 1000` به wallet XAU_MG برمی‌گردد
> - `order_items.buyback_credit_rial` (snapshot موقع خرید) به wallet IRR برمی‌گردد
> - اجرت + مالیات + سود + هزینه‌های اضافه سوخت می‌شوند

#### زیرflow (a) — Cancel Before Delivery (آنلاین، اتومات)

```
1. User → POST /api/v1/orders/{order_id}/cancel-before-delivery
2. Validate:
   - order.user_id == current_user
   - order.status == Paid
   - bar.status == SOLD
   - bar.delivered_at IS NULL (هنوز فیزیکی تحویل داده نشده)
   - fulfillment_task.status IN ('pending', 'picking')
   (اگر packed/handed_over: cancel_before_delivery دیگر مجاز نیست — physical_buyback لازم است)
3. اتومات (در یک DB transaction):
   - Order.status = Cancelled
   - bar.status = ASSIGNED, customer_id = NULL, delivered_at = NULL
   - fulfillment_task.status = cancelled
   - Wallet.credit(user, <wallet matched با brand>, XAU_MG, order_item.pure_gold_mg)
   - Wallet.credit(user, <wallet matched با brand>, IRR, order_item.buyback_credit_rial)
   - Treasury.record(source=buyback, sub_type=cancel, delta=-order_item.pure_gold_mg)
   - (منسوخ — D-58/D-59/D-65: بازخرید فروشِ اصلی را reverse نمی‌کند؛ cost transfer وجود ندارد)
   - Audit log
   - Outbox: BuybackCancelCompleted
   - Notification
```

#### زیرflow (b) — Physical Buyback (حضوری، نیازمند تأیید)

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
8. سیستم در DB transaction:
   - Wallet.credit(user, wallet by brand, XAU_MG, order_item.pure_gold_mg)
   - Wallet.credit(user, wallet by brand, IRR, order_item.buyback_credit_rial)
   - bar.status = ASSIGNED
   - bar.customer_id = NULL
   - bar.delivered_at = NULL
   - bar.current_location_id = target_location_id  ⚠️ مهم: location تغییر می‌کند
   - INSERT inventory_movement (type=transfer_in, to=target_location)
   - Treasury.record(source=buyback, sub_type=physical, delta=-pure_gold_mg)
   - (منسوخ — D-58/D-59/D-65: بازخرید فروشِ اصلی را reverse نمی‌کند؛ cost transfer وجود ندارد)
   - status=WalletCredited → Completed
   - Audit log + Outbox + Notification
```

**قواعد امنیتی:**
- Wallet **نباید** قبل از `AuthenticityVerified` credit شود
- separation of duties: کارشناس receive ≠ کارشناس verify (یا حداقل audit‌شده باشد)
- audit_log الزامی در هر transition

#### زیرflow (c) — Digital Buyback ❌ منسوخ (D-68)

> **⚠️ D-68: این زیرflow حذف شد.** «بازخریدِ دیجیتال» = همان `digital_trade sell` (§۱۲.۴). از `/wallet/trades/sell` استفاده کن، نه `/buyback/digital`. متنِ زیر صرفاً تاریخی است.

> کاربر طلای دیجیتال در wallet را می‌فروشد. هیچ shemmesh فیزیکی درگیر نیست.

```
1. User → POST /api/v1/buyback/digital
     { from_wallet: <Goldis | TalaMala>, asset: XAU_MG, amount_mg }
2. KYC limits + Wallet.check_balance(user, from_wallet, XAU_MG, amount_mg)
3. Pricing.buyback_quote(asset, amount_mg) → قیمت لحظه‌ای buyback
   (با spread — مثل digital_trade sell)
4. Wallet.lock(user, from_wallet, XAU_MG, amount_mg, ref=buyback_intent)
5. Order.create(order_type=buyback, trade_side=sell, status=Confirmed)
6. confirm (atomic):
   - Wallet.consume_lock(XAU_MG, amount_mg)
   - Wallet.credit(user, from_wallet, IRR, buyback_quote_price)
   - Treasury.record(source=buyback, sub_type=digital, delta=-amount_mg)
   - Accounting + Outbox + Notification
7. on fail یا timeout price_lock:
   - Wallet.release_lock
   - Order.status=Cancelled
```

> **توجه:** زیرflow (c) با (a) و (b) فرق بنیادی دارد:
> - (a) و (b) مربوط به یک bar مشخص هستند و `buyback_credit_rial` از order قبلی استفاده می‌کنند
> - (c) مستقل از هر bar هست و قیمت buyback لحظه‌ای از Pricing.buyback_quote محاسبه می‌شود

### ۱۲.۵.۴. شارژ wallet ریالی (Rial Topup) — اتومات، بدون اپراتور

> کاربر در سایت هر brand می‌تواند wallet ریالی همان brand را از طریق gateway شارژ کند. **هیچ تأیید اپراتوری لازم نیست** — مثل خرید عادی.

```
1. User → POST /api/v1/wallet/topup
   Header: X-Channel-Code=<channel>
   Body: { amount_rial }
   • Backend resolves: brand → wallet company
     (طلاملا → wallet TalaMala، گلدیس/امین‌زر → wallet Goldis)
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
      # DigiKala (و سایر marketplaces): payment_receiver=Goldis
      # اگر brand=TalaMala ولی seller=Goldis (مغازه‌گردانی Goldis):
      #   → دو inter_company_ledger entry بین Goldis و TalaMala
      #     (rial: Goldis→TalaMala, gold: TalaMala→Goldis)
      #     چون TalaMala باید سود فروش را بگیرد ولی Goldis مدیریت می‌کند
      # ⚠️ مدل دقیق marketplace settlement در بخش بعدی روشن می‌شود
      Outbox: ExternalOrderImported + OrderPaid + ...
    await adapter.acknowledge_orders(...)
    UPDATE channels.last_sync_at = now()
```

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
worker هر ۳۰ ثانیه:
  for each metal:
    open = SUM(delta_amount_mg) where status IN ('open','partially_covered')
    setting = treasury_settings[metal]
    if open >= setting.max_open_exposure_mg:
      if setting.auto_block_at_cap: set global block flag
      notify admin (critical)
    elif open / max >= warning_threshold:
      throttled notify admin (warning)
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
- POST `/orders/{id}/cancel`
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
- GET `/wallet/balances` → array of {company_code, asset_code, balance, locked}
- GET `/wallet/ledger?company_code=X&asset=Y`
- POST `/wallet/topup` { amount_rial } — شارژ wallet ریالی (per brand auto-routed)
- GET `/wallet/topups` — تاریخچه شارژ
- POST `/wallet/trades/buy` { from_wallet, asset, amount, price_lock_id }
- POST `/wallet/trades/sell` { from_wallet, asset, amount, price_lock_id }
- POST `/admin/wallet/adjustments` { user_id, company_code, asset, amount, direction, reason } (audit-mandatory)

### Withdrawal (فقط ریال — D-31)
- POST `/withdrawals/rial` { from_wallet, amount_rial, bank_account_id }
- GET `/withdrawals`
- POST `/admin/withdrawals/{id}/approve`
- POST `/admin/withdrawals/{id}/reject`
- POST `/admin/withdrawals/{id}/complete`

### Physical purchase from wallet (به‌جای gold withdrawal)
- POST `/orders/physical-from-wallet` { from_wallet, product_id, pay_difference_in_rial }

### Buyback (به‌جای refund) — ۳ زیرflow کامل در v1

**(a) Cancel before delivery** (آنلاین، اتومات):
- POST `/orders/{order_id}/cancel-before-delivery`

**(b) Physical buyback** (حضوری، state machine):
- POST `/buyback/physical/request` { bar_id, target_location_id }
- GET `/buyback/physical/{id}` — برای کاربر مشاهده‌ی وضعیت
- POST `/admin/buyback/physical/{id}/receive` — کارشناس مرکز تحویل گرفت
- POST `/admin/buyback/physical/{id}/verify` — تأیید اصالت
- POST `/admin/buyback/physical/{id}/approve` — تأیید نهایی، wallet credit
- POST `/admin/buyback/physical/{id}/reject` — رد در هر مرحله با reason

**(c) Digital buyback** (آنلاین):
- POST `/buyback/quote` { asset, amount_mg } — قیمت لحظه‌ای
- POST `/buyback/digital` { from_wallet, asset, amount_mg }

### Fulfillment
- GET `/admin/fulfillment/tasks?status=X`
- POST `/admin/fulfillment/tasks/{id}/assign-self`
- POST `/admin/fulfillment/tasks/{id}/pick`
- POST `/admin/fulfillment/tasks/{id}/pack`
- POST `/admin/fulfillment/tasks/{id}/handover` { courier, tracking }
- POST `/admin/fulfillment/tasks/{id}/complete`

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
        await self.fulfillment_svc.create_task(order)
        await self.treasury_svc.record_open_position(order)
        await self.settlement_svc.draft_item(order)
        await self.accounting_svc.record_event(order)

        await self.outbox.enqueue([
            ("OrderPaid", "Order", str(order.id), {...}),
            ("FulfillmentTaskCreated", "FulfillmentTask", ...),
            ("TreasuryPositionOpened", ...),
            ("SettlementItemDrafted", ...),
            ("AccountingEventCreated", ...),
        ])
        # commit در پایان context
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

# Buyback (هر سه زیرflow)
BuybackCancelCompleted,                              # (a) cancel_before_delivery
PhysicalBuybackRequested, PhysicalBuybackReceived,   # (b) physical state machine
PhysicalBuybackVerified, PhysicalBuybackApproved,
PhysicalBuybackCompleted, PhysicalBuybackRejected,
DigitalBuybackCompleted                              # (c) digital_buyback

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
| `settlement_daily` | cron 23:59 | — |
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

2. **چه می‌شود با dealer ها و sub-dealer ها؟**
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

## ۲۰. ابهامات باقیمانده

> **به‌روزرسانی (2026-05-13):** همه ۲۰ ابهام اصلی (O-01 تا O-20) با تیم حل شدند و به D-27 تا D-45 منتقل شدند (بخش ۲).

### ابهامات سطح ۲ که فعلاً مطرح نشده‌اند و در پیاده‌سازی هر context باید روشن شوند:

| # | ابهام | اثر |
|---|---------|---------|
| ~~Q-01~~ | **حل شد:** split payment در `physical_purchase_from_wallet` هر سه منبع را پشتیبانی می‌کند: ۱) wallet XAU_MG ۲) wallet IRR در همان legal_entity ۳) gateway IRR. ترتیب استفاده بر اساس flag های request کاربر (`use_irr_wallet_for_difference`، `pay_remaining_in_gateway`). جزئیات: بخش ۱۲.۵. | ✅ RESOLVED |
| ~~Q-02~~ | **حل شد** — physical buyback در v1 پیاده می‌شود. مرکز buyback: `inventory_locations.can_buyback = TRUE`. نماینده authorized یا انبار مرکزی Goldis. بدون پست — فقط حضوری. | ✅ RESOLVED |
| ~~Q-03~~ | **حل شد** — قیمت buyback **نیازی به price_lock ندارد**. در (a) cancel_before_delivery و (b) physical_buyback از `order_items.buyback_credit_rial` (snapshot موقع خرید) استفاده می‌شود. فقط در (c) digital_buyback نیاز به price_lock لحظه‌ای است. | ✅ RESOLVED |
| ~~Q-04~~ | **منتفی** — settlement_rules دیگر وجود ندارد (D-06b). inter_company_ledger مستقیم پر می‌شود. | ✅ RESOLVED |
| ~~Q-05~~ | **حل شد (D-59):** بازخرید فروش اصلی را معکوس **نمی‌کند**. تحویل‌نشده/حضوری ⇒ تبدیل physical↔digital، خزانه ≈ صفر، بدون تعهد طلاییِ تازه، فقط `buyback_credit_rial` هزینه. دیجیتال ⇒ خزانه − + جفت تعهد تازه‌ی مخالف به قیمت خام لحظه‌ی بازخرید. | ✅ RESOLVED |
| ~~Q-06~~ | **حل شد (D-61):** سه سطح L0/L1/L2. L0 بدون تراکنش مالی؛ L1 با شاهکار؛ L2 با احراز حساب بانکی. اعداد سقف اپراتور-تنظیم در `user_level_defaults`. AML پیشرفته بعداً (D-24). | ✅ RESOLVED |
| ~~Q-07~~ | **حل شد (D-62):** بدون TTL خودکار؛ فقط گزارش سن‌خوردگی + ابزار دستی اپراتور. به‌علاوه انتقال بین انبارها دومرحله‌ای با in-transitِ مجازی + اسکن دوطرفه + OTP تحویل + تفکیک وظایف. | ✅ RESOLVED |
| ~~Q-08~~ | **حل شد (D-63):** لیست اولویت‌دار per-channel + fallback خودکار؛ بدون انتخاب کاربر در v1؛ اطلاع‌رسانی الزامی به اپراتور وقتی درگاهی مشکل دارد. | ✅ RESOLVED |
| ~~Q-09~~ | **حل شد (D-64):** فقط حساب خودِ کاربرِ احرازشده (تطبیق شبا↔کدملی). حساب غیر ممنوع — شرط سازمان مبارزه با پول‌شویی. اشخاص حقوقی به v2 موکول. | ✅ RESOLVED |
| ~~Q-10~~ | **حل شد (D-60):** شمش فیزیکی از موجودیِ همان scope/برندِ کیف‌پول برداشته می‌شود (مثل فروش عادی، seller=همان scope). اگر موجود نبود خرید انجام نمی‌شود. مبنا: طلای دیجیتال کاغذی نیست — تعهد طلای واقعیِ Goldis→scope انبار را دوره‌ای پُر می‌کند. | ✅ RESOLVED |

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
22. Buyback complete (هر سه زیرflow در v1):
    - (a) `cancel_before_delivery` — آنلاین اتومات
    - (b) `physical_buyback` — حضوری با state machine کامل (PhysicalRequested → ... → Completed)
    - (c) `digital_buyback` — آنلاین اتومات
23. Inter-Company Ledger (D-06b): جدول `inter_company_ledger`، endpointهای settle، FIFO consume. **بدون settlement_rules، بدون worker روزانه.**
24. Treasury alert worker

### فاز ۴ — DealerNetwork (هفته ۸-۹)
23. Dealer + Tier + SubDealer
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
