# CLAUDE.md — TalaMala v4 Full Project Context

> **این فایل تمام دانش، معماری، قراردادها، باگ‌های شناخته‌شده و نقشه راه توسعه پروژه TalaMala v4 را شامل می‌شود.**
> **Claude Code: هر تغییری در پروژه بدی، اول این فایل رو بخون.**

---

## 1. خلاصه پروژه

**TalaMala v4** یک سیستم ERP فروش شمش طلا (Gold Bullion) است.

- **Stack**: FastAPI + Jinja2 Templates + PostgreSQL + SQLAlchemy + Alembic
- **UI**: فارسی (RTL) با Bootstrap 5 RTL + Vazirmatn font + Bootstrap Icons
- **Auth**: OTP-based (SMS) برای مشتری‌ها + JWT cookie برای ادمین
- **Payment**: کیف پول + درگاه زیبال (sandbox فعال)
- **Pricing**: فرمول محاسبه قیمت طلا بر اساس وزن، عیار، اجرت، سود، مالیات

---

## 2. ساختار فایل‌ها

```
talamala_v4/
├── main.py                      # FastAPI app + router registration
├── config/
│   ├── settings.py              # تمام env vars (تنها جای getenv)
│   └── database.py              # SQLAlchemy engine + SessionLocal
├── common/
│   ├── security.py              # JWT, CSRF, password hashing
│   ├── templating.py            # Jinja2 environment + filters
│   ├── helpers.py               # now_utc, persian formatters
│   ├── upload.py                # Image upload + resize
│   ├── sms.py                   # Kavenegar SMS stub
│   ├── notifications.py         # Ticket SMS notifications (console fallback)
│   └── exceptions.py            # Custom exceptions
├── modules/
│   ├── admin/                   # SystemUser, SystemSetting, admin settings page
│   ├── auth/                    # Login (OTP), JWT, deps (require_customer etc.)
│   ├── catalog/                 # Product, ProductCategory, CardDesign, PackageType, Batch
│   ├── inventory/               # Bar, Location, BarImage, OwnershipHistory
│   ├── shop/                    # Public storefront (product list + detail)
│   ├── cart/                    # Cart, CartItem, checkout, delivery location API
│   ├── order/                   # Order, OrderItem, delivery_service, admin order mgmt
│   ├── payment/                 # Wallet pay, Zibal gateway, refund
│   ├── wallet/                  # Double-entry ledger, topup, withdraw, admin
│   ├── coupon/                  # DISCOUNT/CASHBACK coupons, admin CRUD
│   ├── customer/                # Profile, CustomerAddress, GeoProvince/City/District
│   ├── verification/            # QR/serial code authenticity check
│   ├── dealer/                  # Dealer, DealerSale, BuybackRequest, POS, admin mgmt, REST API
│   └── ticket/                  # Ticket, TicketMessage, TicketAttachment, categories, internal notes
├── templates/
│   ├── base.html                # HTML skeleton (Bootstrap RTL, Vazirmatn)
│   ├── auth/login.html
│   ├── shop/                    # Customer-facing pages
│   │   ├── base_shop.html       # Shop layout (navbar + dropdown + content)
│   │   ├── home.html            # Product grid + category filter + sort
│   │   ├── product_detail.html
│   │   ├── cart.html
│   │   ├── checkout.html        # Pickup/Postal delivery + coupon
│   │   ├── orders.html
│   │   ├── order_detail.html    # Payment buttons + status
│   │   ├── wallet.html
│   │   ├── wallet_withdraw.html
│   │   ├── wallet_transactions.html
│   │   ├── profile.html
│   │   ├── addresses.html       # Address book CRUD
│   │   ├── tickets.html         # Customer ticket list
│   │   ├── ticket_new.html      # Customer create ticket
│   │   └── ticket_detail.html   # Customer ticket conversation
│   ├── admin/
│   │   ├── base_admin.html      # Admin sidebar layout
│   │   ├── dashboard.html
│   │   ├── settings.html        # Gold price, tax, shipping config
│   │   ├── catalog/             # products, categories, designs, packages, batches
│   │   ├── inventory/           # bars, locations, edit_bar
│   │   ├── orders/list.html     # Order management + delivery status
│   │   ├── wallet/              # accounts, detail, withdrawals
│   │   ├── coupon/              # list, form, detail
│   │   └── tickets/             # admin ticket list + detail
│   ├── dealer/
│   │   ├── base_dealer.html     # Dealer sidebar layout
│   │   ├── tickets.html         # Dealer ticket list
│   │   ├── ticket_new.html      # Dealer create ticket
│   │   └── ticket_detail.html   # Dealer ticket conversation
│   └── public/verify.html       # Public authenticity check page
├── scripts/
│   ├── seed.py                  # Database seeder (--reset flag)
│   └── init_db.py               # DB initialization utility
├── alembic/                     # Migrations
├── static/uploads/              # Uploaded images
├── .env.example
└── requirements.txt
```

---

## 3. مدل‌های دیتابیس (Database Models)

### admin/models.py
- **SystemUser**: id, username, mobile, hashed_password, role (super_admin/operator), is_staff=True
- **SystemSetting**: id, key (unique), value, description

### customer/models.py
- **Customer**: id, mobile (unique), full_name, national_id, birth_date, is_active, created_at

### customer/address_models.py
- **GeoProvince**: id, name (unique), sort_order → has many GeoCity
- **GeoCity**: id, province_id (FK), name, sort_order → has many GeoDistrict
- **GeoDistrict**: id, city_id (FK), name
- **CustomerAddress**: id, customer_id (FK), title, province_id, city_id, district_id, address, postal_code, receiver_name, receiver_phone, is_default

### catalog/models.py
- **ProductCategory**: id, name (unique), slug (unique), sort_order, is_active
- **ProductCategoryLink**: id, product_id (FK → products), category_id (FK → product_categories) — M2M junction (UniqueConstraint)
- **Product**: id, name, weight (Decimal), purity (int: 750=18K), wage (Numeric 5,2 — percent), is_wage_percent, design, card_design_id, package_type_id, is_active
  - Properties: `categories` (list of ProductCategory), `category_ids` (list of int)
- **ProductImage**: id, product_id, path, is_default
- **CardDesign / CardDesignImage**: طرح کارت‌های هدیه
- **PackageType / PackageTypeImage**: بسته‌بندی
- **Batch / BatchImage**: بچ تولید (ذوب)

### inventory/models.py
- **Location**: id, name, location_type (WAREHOUSE/BRANCH/CUSTOMER), province, city, address, phone, is_postal_hub, is_active
- **Bar**: id, serial_code (unique), product_id, batch_id, location_id, customer_id, claim_code (unique, nullable — for POS/gift), status (RAW/ASSIGNED/RESERVED/SOLD), reserved_customer_id, reserved_until
- **BarImage**: id, bar_id, file_path
- **OwnershipHistory**: id, bar_id, previous_owner_id, new_owner_id, transfer_date, description
- **LocationTransfer**: id, bar_id, from_location_id, to_location_id, transferred_by, transferred_at, description
- **BarTransfer**: id, bar_id, from_customer_id, to_mobile, otp_hash, otp_expiry, status (Pending/Completed/Cancelled/Expired), created_at

### cart/models.py
- **Cart**: id, customer_id (unique), created_at
- **CartItem**: id, cart_id, product_id, quantity

### order/models.py
- **Order**: id, customer_id, status (Pending/Paid/Cancelled), cancellation_reason, cancelled_at, delivery_method (Pickup/Postal), is_gift (bool), pickup_location_id, shipping_province, shipping_city, shipping_address, shipping_postal_code, delivery_code_hash, delivery_status, total_amount, shipping_cost, insurance_cost, coupon_code, promo_choice (DISCOUNT/CASHBACK), promo_amount, cashback_settled, payment_method, payment_ref, paid_at, track_id, delivered_at, created_at
- **OrderItem**: id, order_id, product_id, bar_id, applied_gold_price, applied_unit_price, applied_weight, applied_purity, applied_wage_percent, applied_tax_percent, final_gold_amount, final_wage_amount, final_tax_amount, line_total

### wallet/models.py
- **Account**: id, customer_id, asset_code (IRR/XAU_MG), owner_type, owner_id, balance, locked_balance, credit_balance (non-withdrawable store credit)
  - `available_balance` = balance - locked (for purchases)
  - `withdrawable_balance` = balance - locked - credit (for bank withdrawals)
- **LedgerEntry**: id, account_id, txn_type (Deposit/Withdraw/Payment/Refund/Hold/Release/Commit/Credit), delta_balance, delta_locked, delta_credit, balance_after, locked_after, credit_after, idempotency_key, reference_type, reference_id, description
- **WalletTopup**: id, customer_id, amount_irr, status, ref_number, gateway
- **WithdrawalRequest**: id, customer_id, amount_irr, status (PENDING/APPROVED/REJECTED), shaba_number, account_holder

### coupon/models.py
- **Coupon**: id, code (unique), title, description, coupon_type (DISCOUNT/CASHBACK), discount_mode (PERCENT/FIXED), discount_value, max_discount_amount, scope (GLOBAL/PRODUCT/CATEGORY), scope_product_id, min_order_amount, first_purchase_only, is_private, max_per_customer, max_total_uses, status (ACTIVE/INACTIVE/EXPIRED)
- **CouponCategory**: id, coupon_id, category_id → M2M junction (coupon ↔ product_categories)
- **CouponMobile**: id, coupon_id, mobile → whitelist
- **CouponUsage**: id, coupon_id, customer_id, order_id, discount_applied

### dealer/models.py
- **Dealer**: id, mobile (unique), full_name, national_id, location_id (FK→locations), commission_percent, is_active, api_key (unique, for POS), otp_code, otp_expiry, created_at
- **DealerSale**: id, dealer_id, bar_id, customer_name/mobile/national_id, sale_price, commission_amount, description, created_at
- **BuybackRequest**: id, dealer_id, bar_id, customer_name/mobile, buyback_price, status (Pending/Approved/Completed/Rejected), admin_note, description, wage_refund_amount (rial), wage_refund_customer_id, created_at, updated_at

### ticket/models.py
- **TicketCategory** (enum): Financial / Technical / Sales / Complaints / Other (دپارتمان)
- **Ticket**: id, subject, body, category (TicketCategory), status (Open/InProgress/Answered/Closed), priority (Low/Medium/High), sender_type (CUSTOMER/DEALER/STAFF), customer_id (FK), dealer_id (FK), assigned_to (FK→SystemUser), created_at, updated_at, closed_at
  - Properties: sender_name, sender_mobile, status_label/color, priority_label/color, category_label/color, sender_type_label/color, message_count, public_message_count
  - Relationships: customer, dealer, assigned_staff, messages
- **TicketMessage**: id, ticket_id (FK), sender_type (CUSTOMER/DEALER/STAFF), sender_name (denormalized), body, is_internal (staff-only note), is_initial (first message for attachments), created_at
  - Properties: sender_type_label, sender_badge_color, is_staff_message
  - Relationships: attachments
- **TicketAttachment**: id, message_id (FK→ticket_messages, CASCADE), file_path, created_at
  - Relationship: message

---

## 4. اصول و قراردادهای کدنویسی

### الگوی ماژول
هر ماژول شامل:
- `models.py` — SQLAlchemy models
- `service.py` — Business logic (class singleton pattern)
- `routes.py` — FastAPI routes (customer-facing)
- `admin_routes.py` — Admin panel routes (optional)

### CSRF Protection
```python
from common.security import csrf_check, new_csrf_token

# GET route: generate token
csrf = new_csrf_token()
response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")

# POST route: verify — ⚠️ اولین پارامتر حتماً request باشه!
csrf_check(request, csrf_token)
```

**⚠️ باگ رایج**: در بعضی route ها `csrf_check(csrf_token)` بدون `request` نوشته شده بود. تابع `csrf_check` حتماً دو پارامتر می‌گیرد: `(request: Request, form_token: str)`. بدون request خطای `'str' object has no attribute 'cookies'` می‌دهد.

### Template Rendering Pattern
```python
csrf = new_csrf_token()
response = templates.TemplateResponse("shop/page.html", {
    "request": request,
    "user": me,
    "cart_count": cart_count,
    "csrf_token": csrf,
    # ...
})
response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
return response
```

### Auth Dependencies (modules/auth/deps.py)
- `get_current_active_user(request, db)` — Returns Customer or SystemUser or None
- `require_customer` — Depends, raises 401 if not customer
- `require_super_admin` — Depends, raises 401 if not super_admin
- `require_operator_or_admin` — Either role

### Pricing
`modules/pricing/calculator.py` → `calculate_bar_price()`
- Gold price from SystemSetting key `gold_price_per_gram_18k` (rial)
- Tax from SystemSetting key `tax_percent`

### Currency
- **تمام مبالغ در دیتابیس به ریال ذخیره می‌شوند**
- فیلتر Jinja2 `| toman` تبدیل ریال → تومان (÷10) با فرمت فارسی
- در فرم‌ها: کاربر تومان وارد می‌کند، route `×10` می‌کند

### Template Filters (common/templating.py)
- `| toman` — int rial → formatted toman string
- `| persian_number` — English digits → Persian
- `| jdate` — Gregorian → Jalali date

---

## 5. 🐛 باگ‌های شناخته‌شده

### BUG-1: فیلتر دسته‌بندی در shop/home — ✅ FIXED
**فیکس**: `p.category_id == cat_id` بجای `p.get("product")` در `modules/shop/routes.py`

### BUG-2: Wallet topup — ✅ FIXED
**فیکس**: Topup حالا از درگاه Zibal استفاده میکنه + callback route اضافه شد (`/wallet/topup/callback`)

### BUG-3: int_parsing در checkout — ✅ NOT A BUG
**بررسی**: کد فعلی `.isdigit()` قبل از تبدیل چک میکنه. مشکلی وجود نداره.

### BUG-4: CSRF ارور بعد از idle — ✅ FIXED
**فیکس**: Middleware `csrf_cookie_refresh` در `main.py` اضافه شد که در هر GET request بدون cookie، CSRF cookie تازه ست میکنه.

---

## 6. فازهای تکمیل‌شده

| فاز | عنوان | وضعیت |
|------|--------|--------|
| 1-2 | Infrastructure + Auth (OTP, JWT) | ✅ |
| 3 | Catalog (Product, Design, Package, Batch) | ✅ |
| 4 | Inventory (Bar, Location, transfers) | ✅ |
| 5 | Shop (listing, detail, pricing) | ✅ |
| 6 | Cart + Orders + Delivery | ✅ |
| 7 | Wallet (double-entry ledger) | ✅ |
| 8 | Coupon (DISCOUNT/CASHBACK) | ✅ |
| 9 | Payment (wallet + Zibal sandbox) | ✅ |
| 9.5 | Categories, Geo, Addresses, Profile, Verify | ✅ |
| 10 | Verification بهبود (QR, history, API) | ✅ |
| 11 | Dealer / Reseller (POS, buyback, commission) | ✅ |
| 12 | Admin Dashboard (stats, Chart.js, alerts) | ✅ |
| 13 | Ticketing / Support (customer + dealer + admin) | ✅ |
| 14 | Dealer POS REST API (API Key auth, JSON endpoints) | ✅ |
| 14.5 | Bar Claim & Gifting + Ownership Transfer | ✅ |

---

## 7. فازهای آینده (ROADMAP)
- نمودار: Chart.js
- گزارش: PDF export

### 📌 Phase 15: Notifications
- SMS (order status, delivery)
- Email
- In-app notification center

### 📌 Phase 16: Shahkar Identity Verification
- اتصال به سامانه شاهکار (تطبیق موبایل + کد ملی)
- پس از احراز: full_name, national_id → readonly
- فیلدهای فعلاً readonly در profile

### 📌 Phase 17: Advanced Features
- Price alerts
- Wishlist
- Product comparison
- Blog/content module

---

## 8. راهنمای اجرا و تست

### Setup (Windows)
```bash
python -m venv env1
env1\Scripts\activate
pip install -r requirements.txt
pip install httpx
copy .env.example .env   # Edit: set DB, keys, BASE_URL=http://127.0.0.1:8000
python scripts/seed.py --reset   # Type: yes
uvicorn main:app --reload
```

### Test Accounts
| نقش | موبایل | توضیح |
|------|---------|--------|
| Super Admin | 09123456789 | دسترسی کامل |
| Operator | 09121111111 | عملیاتی |
| Customer | 09351234567 | کیف پول: 10M تومان |
| Customer | 09359876543 | — |
| Customer | 09131112233 | — |
| Dealer | 09161234567 | نمایندگی اصفهان — پخش |
| Dealer | 09171234567 | نمایندگی شیراز — بنکدار |
| Dealer | 09181234567 | نمایندگی مشهد — فروشگاه |
| Dealer | 09141234567 | نمایندگی تبریز — پخش |
| Dealer | 09121234567 | شعبه میرداماد تهران — پخش |
| Dealer | 09122345678 | شعبه بازار ناصرخسرو — بنکدار |
| Dealer | 09123456780 | شعبه بازار اردیبهشت — بنکدار |
| Dealer | 09124567890 | شعبه شهرک غرب — فروشگاه |
| Dealer | 09125678901 | شعبه کریمخان — فروشگاه |

### Dealer API Keys (POS)
| موبایل | API Key |
|---------|---------|
| 09161234567 | `test_esfahan_key_0000000000000000` |
| 09171234567 | `test_shiraz__key_1111111111111111` |
| 09181234567 | `test_mashhad_key_2222222222222222` |
| 09141234567 | `test_tabriz__key_3333333333333333` |
| 09121234567 | `test_mirdmad_key_4444444444444444` |
| 09122345678 | `test_nasrkhr_key_5555555555555555` |
| 09123456780 | `test_ordibht_key_6666666666666666` |
| 09124567890 | `test_shahrak_key_7777777777777777` |
| 09125678901 | `test_karimkh_key_8888888888888888` |

### Test Coupons
| کد | نوع | توضیح |
|-----|------|--------|
| WELCOME10 | 10% تخفیف | اولین خرید |
| CASHBACK5 | 5% کشبک | واریز به کیف پول |
| FIXED500 | 500K تومان | حداقل سفارش 5M |
| VIP2026 | 15% تخفیف | فقط موبایل‌های خاص |
| GOLD10 | 10% تخفیف | فقط دسته شمش گرمی (CATEGORY scope) |

### Test Bars (Claim & Transfer)
| سریال‌کد | وضعیت | claim_code | مالک | کاربرد |
|----------|--------|------------|------|--------|
| TSCLM001 | SOLD | ABC123 | — | تست ثبت مالکیت موفق |
| TSCLM002 | SOLD | XYZ789 | — | تست کد اشتباه |
| TSTRF001 | SOLD | — | U3 (09351234567) | تست انتقال مالکیت |

### Zibal Sandbox
- `ZIBAL_MERCHANT=zibal` → sandbox (auto-succeed)
- `ZIBAL_MERCHANT=your-real-id` → production
- Callback: `{BASE_URL}/payment/zibal/callback?order_id={id}`

---

## 9. نکات حیاتی برای توسعه

### وقتی مدل جدید اضافه می‌کنی:
1. مدل را در `modules/xxx/models.py` تعریف کن
2. **حتماً** در `main.py` import کن (بخش "Import ALL models")
3. **حتماً** در `alembic/env.py` import کن
4. **حتماً** در `scripts/seed.py` import کن (اگر seed data لازم دارد)
5. `python scripts/seed.py --reset` برای recreate

### وقتی route جدید اضافه می‌کنی:
1. Router بساز
2. در `main.py` → `app.include_router()` اضافه کن
3. POST routes: `csrf_check(request, csrf_token)`
4. GET routes با فرم: `csrf_token` به template + cookie set

### الگوی Atomic Transaction (پرداخت):
```python
# 1. wallet_service.withdraw() → flush (no commit)
# 2. Set order.payment_* fields
# 3. order_service.finalize_order() → commit (atomic)
# 4. Route's db.commit() → no-op
# On failure: db.rollback() undoes everything
```

### فرمت خروجی shop service:
`shop_service.list_products_with_pricing()` → `(List[Product], gold_price_rial, tax_percent_str)`
- هر آیتم یک **Product ORM object** است (نه dict!)
- Dynamic attributes اضافه‌شده: `product.inventory`, `product.final_price`, `product.price_info`
- Category access (M2M): `product.categories` (list), `product.category_ids` (list of int)

### Jinja2 Tips:
- هر `{% if %}` ← `{% endif %}`
- هر `{% for %}` ← `{% endfor %}`
- Dict access: `balance.available` یا `balance['available']`
- Enum: `order.status.value`

### CSS/Z-index:
- `.shop-navbar`: z-index 1050
- `.shop-navbar .dropdown-menu`: z-index 9999
- `.sticky-top` elements: z-index 1

---

## 10. فرمول قیمت‌گذاری طلا (ساده‌شده)

```
raw_gold = weight × (purity / 750) × gold_price_18k
wage     = raw_gold × (wage% / 100)
tax      = wage × (tax% / 100)          ← مالیات فقط روی اجرت
total    = raw_gold + wage + tax
```

- تابع: `calculate_bar_price()` در `modules/pricing/calculator.py`
- product.wage = اجرت مشتری نهایی (auto-sync به ProductTierWage)
- سطوح نمایندگان: هر سطح اجرت کمتری دارد → اختلاف = سود نماینده (به طلا)

---

## 11. API Endpoints

### Public
- `GET /` — Shop home
- `GET /product/{id}` — Product detail
- `GET /verify` — Authenticity page
- `GET /verify/check?code=X` — Check serial
- `GET /health` — Health check

### Auth
- `GET /auth/login` — Login page
- `POST /auth/login/request-otp` — Send OTP
- `POST /auth/login/verify-otp` — Verify → JWT cookie
- `GET /auth/logout` — Clear cookie

### Customer
- `GET/POST /profile` — Profile
- `GET/POST /addresses` — Address CRUD
- `POST /addresses/{id}/delete|default`
- `GET /api/geo/cities?province_id=X`
- `GET /api/geo/districts?city_id=X`

### Cart & Orders
- `GET /cart` — Cart page
- `POST /cart/add|update/{pid}|remove/{pid}`
- `GET /checkout` — Checkout
- `POST /cart/checkout` — Place order
- `GET /orders` — My orders
- `GET /orders/{id}` — Order detail

### Payment
- `POST /payment/{id}/wallet` — Wallet pay
- `POST /payment/{id}/zibal` — Gateway redirect
- `GET /payment/zibal/callback` — Gateway return
- `POST /payment/{id}/refund` — Admin refund

### Wallet
- `GET /wallet` — Dashboard
- `GET /wallet/transactions` — History
- `POST /wallet/topup` — Charge
- `GET/POST /wallet/withdraw` — Withdrawal

### AJAX APIs
- `GET /api/delivery/locations?province=X&city=Y`
- `GET /api/coupon/check?code=X`

### Dealer Panel (Web)
- `GET /dealer/dashboard` — Dealer dashboard (stats, quick actions)
- `GET/POST /dealer/pos` — POS sale form
- `GET/POST /dealer/buyback` — Buyback request form
- `GET /dealer/sales` — Sales history
- `GET /dealer/buybacks` — Buyback history

### Dealer POS REST API (JSON, API Key auth via X-API-Key header)
- `GET /api/dealer/info` — Dealer identity / health check
- `GET /api/dealer/products` — Products + live pricing + available bar serials
- `POST /api/dealer/sale` — Register POS sale (serial_code, sale_price, customer info)
- `GET /api/dealer/sales` — Sales history (paginated)

### Tickets (Customer + Dealer)
- `GET /tickets` — My tickets list
- `GET/POST /tickets/new` — Create ticket (with category + file attachments)
- `GET /tickets/{id}` — Ticket detail + conversation (with attachments)
- `POST /tickets/{id}/message` — Add reply (with file attachments)
- `POST /tickets/{id}/close` — Close ticket

### Ownership (Bar Claim & Transfer)
- `GET /my-bars` — Customer's bar inventory
- `GET /claim-bar` — Claim form (serial + claim_code)
- `POST /claim-bar` — Process bar claim
- `GET /my-bars/{bar_id}/transfer` — Transfer form (enter recipient mobile)
- `POST /my-bars/{bar_id}/transfer` — Send OTP to owner
- `POST /my-bars/{bar_id}/transfer/confirm` — Confirm transfer with OTP

### Admin
- `/admin/dashboard|products|categories|designs|packages|batches`
- `/admin/bars|locations|orders|settings`
- `/admin/wallet/accounts|withdrawals`
- `/admin/coupons`
- `/admin/dealers` — Dealer list + create/edit
- `POST /admin/dealers/{id}/generate-api-key` — Generate POS API key
- `POST /admin/dealers/{id}/revoke-api-key` — Revoke POS API key
- `/admin/dealers/buybacks` — Buyback approval/rejection
- `GET /admin/tickets` — Ticket list (tabs: all/customer/dealer + status/category filter + search)
- `GET /admin/tickets/{id}` — Ticket detail + reply + internal notes + assign
- `POST /admin/tickets/{id}/reply` — Admin reply (with file attachments)
- `POST /admin/tickets/{id}/internal-note` — Staff-only internal note (invisible to customer/dealer)
- `POST /admin/tickets/{id}/status` — Change status (sends notification)
- `POST /admin/tickets/{id}/close` — Close ticket
- `POST /admin/tickets/{id}/assign` — Assign to staff

---

## 12. Environment Variables (.env)

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=talamala_v4
DB_USER=postgres
DB_PASSWORD=xxx
SECRET_KEY=random-64-chars
CUSTOMER_SECRET_KEY=random-64-chars
OTP_SECRET=random-string
SMS_API_KEY=kavenegar-key
ZIBAL_MERCHANT=zibal
SEPEHR_TERMINAL_ID=99079327
DEBUG=true
BASE_URL=http://127.0.0.1:8000
MAINTENANCE_MODE=false
CSRF_ENABLED=true
```

---

## 13. چک‌لیست قبل از هر تغییر

- [ ] CLAUDE.md خوانده شد
- [ ] مدل‌های مرتبط بررسی شدند
- [ ] CSRF: `csrf_check(request, csrf_token)` — دو پارامتر!
- [ ] Template tags balanced (if/endif, for/endfor)
- [ ] Python syntax valid
- [ ] seed.py بدون ارور اجرا می‌شود
- [ ] uvicorn بدون ارور start می‌شود
- [ ] **اسناد docs/ بروزرسانی شدند** (قانون الزامی — پایین ببین)

---

## 14. قانون بروزرسانی مستندات (DOCS SYNC)

> **⚠️ الزامی**: هر تغییر کدی (مدل جدید، route جدید، فیچر جدید، باگ فیکس مهم) باید علاوه بر `CLAUDE.md`، در **هر سه سند** زیر هم منعکس شود:

| سند | مسیر | محتوا |
|------|-------|--------|
| Feature Catalog | `docs/Feature-Catalog.md` | لیست ماژول‌ها، مدل‌ها، endpoint ها، جدول دسترسی |
| Operator Manual | `docs/Operator-Manual.md` | سناریوهای عملیاتی اپراتور |
| Test Playbook | `docs/Test-Playbook.md` | تست‌کیس‌ها با فرمت ID/Action/Input/Expected |

### چه تغییراتی نیاز به بروزرسانی docs دارند:
- اضافه شدن ماژول/مدل جدید → Feature Catalog + Test Playbook
- اضافه شدن route/endpoint جدید → Feature Catalog
- اضافه شدن سناریو عملیاتی جدید → Operator Manual
- تغییر رفتار موجود → هر سه سند (در صورت تأثیر)
- فاز جدید تکمیل‌شده → Feature Catalog (جدول فازها)

---

## 15. قانون کامیت و پوش (AUTO COMMIT & PUSH)

> **⚠️ الزامی**: بعد از هر تغییر کدی (حتی کوچک)، **حتماً** تغییرات را commit و push کن.

### قوانین:
- بعد از اتمام هر تسک یا تغییر، بلافاصله `git add` + `git commit` + `git push` انجام بده
- پیام کامیت فارسی یا انگلیسی مختصر و گویا باشد
- هرگز تغییرات را بدون commit رها نکن
- اگر چند تغییر مرتبط داری، یک commit با پیام جامع بزن
- اگر تغییرات غیرمرتبط داری، commit های جداگانه بزن
