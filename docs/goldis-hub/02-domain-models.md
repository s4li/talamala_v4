# مدلهای دامنه و Bounded Contexts — گلدیس هاب

> **این فایل** مفاهیم domain، ساختار Companies/Brands/Channels، مدل Wallet/Treasury/Inter-Company و لیست Bounded Contexts را شامل میشود.
> **SQL schemas** در [03-schema-index.md](03-schema-index.md) هستند (canonical).
> **تصمیمات** در [01-decisions-audit-log.md](01-decisions-audit-log.md) هستند.
> **جریانهای E2E** در [flows/](flows/) هستند.

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

> **Canonical schema:** see [Platform (Companies/Brands/Channels)](03-schema-index.md#1-platform)
> Tables: `companies`, `brands`, `sales_channels`, `payment_accounts`, `inventory_locations`

### ۳.۳. تشخیص brand/channel در API

- Storefront frontend ها → **domain → channel lookup** (server-side) + هدر `X-Channel-Code` بهعنوان fallback
- Admin panel → کاربر در پنل، brand/channel را explicit انتخاب میکند (با permission)
- POS app → `terminal_id` + `device_id` در JWT claim → resolve به یک خاص `sales_channel`
- ⚠️ **هیچ frontend نمی‌تواند brand_id را آزاد در body بفرستد** — همیشه از channel resolution می‌آید

---

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

> **Canonical schema:** see [Wallet](03-schema-index.md#2-wallet)
> Tables: `asset_types`, `asset_balances`, `wallet_ledger_entries`, `wallet_locks`

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

> **Canonical schema:** see [Treasury](03-schema-index.md#3-treasury)
> Tables: `treasury_positions`, `treasury_settings`, `treasury_position_snapshots`

---


---


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

> **Canonical schema:** see [Inter-Company Ledger](03-schema-index.md#4-inter-company-ledger)
> Tables: `inter_company_ledger`, `inter_company_settle_actions`

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

> **Canonical schema:** see [Fulfillment](03-schema-index.md#5-fulfillment)
> Tables: `fulfillment_tasks`, `fulfillment_events`

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


---

## ۹. POS as First-class Sales Channel

### ۹.۱. مفهوم

POS = `sales_channels.channel_type = 'pos'`. یک channel POS مشخص دارد:
- `brand_id` (Goldis یا TalaMala)
- `terminal_id`
- `default_payment_account_id` (Goldis POS device → Goldis payment_account، TalaMala POS device → TalaMala payment_account)
- `device_id`

### ۹.۲. مدل داده

> **Canonical schema:** see [POS Devices & Transactions](03-schema-index.md#15-pos-devices--transactions)
> Tables: `pos_devices`, `pos_transactions`

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

---


> **⚠️ Note:** SQL schemas referenced in the sections above (e.g. `companies`, `brands`, `sales_channels`, `asset_balances`, `treasury_positions`, `inter_company_ledger`, `bars`, `fulfillment_tasks`) are defined in [03-schema-index.md](03-schema-index.md).
> Decision references (D-XX) link to [01-decisions-audit-log.md](01-decisions-audit-log.md).

