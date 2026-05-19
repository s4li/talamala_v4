# دفتر تصمیمات معماری گلدیس هاب

> **این فایل تنها مرجع canonical برای تمام تصمیمات معماری (D-01…D-99)، اصلاحات P0، و fixهای BLOCKER/HIGH است.**
> Flow files و reference files فقط با لینک `[D-XX](01-decisions-audit-log.md)` به اینجا ارجاع میدهند.
>
> **ماهیت:** این جدولها **changelog/تاریخچهی استدلال** هستند (چرا هر تصمیم گرفته شد) — برای حسابرسی و حافظهی تیم.
> بدنهی سند از v2.1 تمیز بازنویسی شده و مستقیما مدل نهایی را می‌گوید.
> تصمیمات زیر با تیم نهایی شده‌اند و در پیاده‌سازی دوباره بحث نمیشوند.

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

## ۲۰. ابهامات — وضعیت

> For open/unreviewed items, see [00-overview.md §0.1](00-overview.md#۰۱-موارد-باز--بازبینینشده-تمرکز-داور-اینجا).

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

