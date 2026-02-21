# CLAUDE.md — TalaMala v4 Full Project Context (Backend)

> **نکته:** معادل فارسی TalaMala همیشه **طلاملا** است (نه طلامالا).

> **این فایل تمام دانش، معماری، قراردادها، باگ‌های شناخته‌شده و نقشه راه توسعه پروژه TalaMala v4 را شامل می‌شود.**
> **Claude Code: هر تغییری در پروژه بدی، اول این فایل رو بخون.**

---

## ⚠️ Multi-Repo Workspace

> این پروژه بخش **بک‌اند** است. فرانت POS در فولدر کناری `talamala_pos/` قرار دارد.
> هر کدام **git مستقل** دارند. کامیت و پوش باید جداگانه انجام شود.
>
> ```bash
> # فقط بک‌اند
> git -C /path/to/talamala_v4 add . && git -C /path/to/talamala_v4 commit -m "..." && git -C /path/to/talamala_v4 push
> ```

---

## 1. خلاصه پروژه

**TalaMala v4** یک فروشگاه اینترنتی شمش طلای فیزیکی مبتنی بر شبکه نمایندگان (B2B2C) است.

> **⚠️ بیزینس‌مدل**: ما فروشگاه شمش فیزیکی هستیم، **نه** صرافی یا پلتفرم معاملاتی طلای آبشده.
> فیچرهای مختص ترید/صرافی (خرید خُرد دوره‌ای DCA، داشبورد PNL، نوسان‌گیری، طلای دیجیتال کسری) در scope پروژه **نیستند**.
> کیف پول طلایی (XAU_MG) فقط برای مصارف داخلی: تسویه سود نمایندگان + پاداش وفاداری مشتریان.

- **Stack**: FastAPI + Jinja2 Templates + PostgreSQL + SQLAlchemy + Alembic
- **UI**: فارسی (RTL) با Bootstrap 5 RTL + Vazirmatn font + Bootstrap Icons
- **Auth**: OTP-based (SMS) + single JWT cookie (`auth_token`) for all user types
- **User Model**: Unified `users` table with role flags (`is_customer`, `is_dealer`, `is_admin`)
- **Payment**: کیف پول + چند درگاه (Zibal, Sepehr, Top, Parsian) با لایه abstraction + انتخاب درگاه فعال از تنظیمات ادمین
- **Pricing**: فرمول ساده قیمت شمش: طلای خام + اجرت + مالیات (روی اجرت)

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
│   ├── user/                    # Unified User model (customers + dealers + admins in one table)
│   ├── admin/                   # SystemSetting, RequestLog, admin settings page, staff service
│   ├── auth/                    # Login (OTP), JWT, deps (require_customer etc.)
│   ├── catalog/                 # Product, ProductCategory, CardDesign, PackageType, Batch
│   ├── inventory/               # Bar, BarImage, OwnershipHistory, DealerTransfer
│   ├── shop/                    # Public storefront (product list + detail)
│   ├── cart/                    # Cart, CartItem, checkout, delivery location API
│   ├── order/                   # Order, OrderItem, delivery_service, admin order mgmt
│   ├── payment/                 # Wallet pay, multi-gateway (Zibal/Sepehr/Top/Parsian), refund
│   │   └── gateways/            # BaseGateway abstraction + per-gateway implementations
│   ├── wallet/                  # Double-entry ledger, topup, withdraw, admin, PRECIOUS_METALS registry
│   │   ├── models.py            # Account, LedgerEntry, WalletTopup, WithdrawalRequest + PRECIOUS_METALS metadata
│   │   └── routes.py            # Wallet routes incl. generic /{asset_type} buy/sell for precious metals
│   ├── coupon/                  # DISCOUNT/CASHBACK coupons, admin CRUD
│   ├── customer/                # Profile, CustomerAddress, GeoProvince/City/District
│   ├── verification/            # QR/serial code authenticity check
│   ├── dealer/                  # DealerTier, DealerSale, BuybackRequest, SubDealerRelation, B2BOrder, B2BOrderItem, POS, admin mgmt, REST API
│   │   └── auth_deps.py         # Shared API Key auth dependency (used by dealer + pos)
│   ├── dealer_request/          # DealerRequest, attachments, admin review (approve/revision/reject)
│   ├── pos/                     # Customer-facing POS API (reserve→confirm/cancel pattern)
│   ├── review/                  # Product reviews (star rating) + comments/Q&A + likes
│   ├── rasis/                   # Rasis POS device integration (auto-sync inventory + pricing)
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
│   │   ├── wallet.html          # Unified wallet dashboard (all users)
│   │   ├── wallet_withdraw.html
│   │   ├── wallet_transactions.html
│   │   ├── wallet_trade.html     # Generic precious metal buy/sell (gold, silver, etc.)
│   │   ├── profile.html
│   │   ├── addresses.html       # Address book CRUD
│   │   ├── tickets.html         # Customer ticket list
│   │   ├── ticket_new.html      # Customer create ticket
│   │   └── ticket_detail.html   # Customer ticket conversation
│   ├── admin/
│   │   ├── base_admin.html      # Admin sidebar layout
│   │   ├── dashboard.html
│   │   ├── settings.html        # Asset prices (gold/silver) + tax, shipping config + active gateway + precious metal trade fees (gold + silver)
│   │   ├── catalog/             # products, categories, designs, packages, batches
│   │   ├── inventory/           # bars, edit_bar
│   │   ├── orders/list.html     # Order management + delivery status
│   │   ├── wallet/              # accounts, detail, withdrawals
│   │   ├── coupon/              # list, form, detail
│   │   ├── tickets/             # admin ticket list + detail
│   │   ├── reviews/             # admin review + comment list + detail
│   │   └── logs/                # request audit log list
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

### user/models.py (Unified User Model)
- **User**: id, mobile (unique), first_name, last_name, national_id, birth_date, is_active, created_at
  - **Role flags**: `is_customer` (bool), `is_dealer` (bool), `is_admin` (bool) — a user can have multiple roles
  - **Identity**: mobile, first_name, last_name, national_id, birth_date
  - **Customer fields**: customer_type (real/legal), company_name, economic_code, postal_code, address, phone, referral_code
  - **Dealer fields**: tier_id (FK→dealer_tiers), province_id, city_id, district_id, dealer_address, landline_phone, is_warehouse, is_postal_hub, commission_percent, api_key (unique), otp_code, otp_expiry, rasis_sharepoint (Integer, nullable — Rasis POS device mapping)
  - **Admin fields**: admin_role (admin/operator), operator_permissions (JSON)
  - Properties: `full_name`, `display_name`, `is_staff` (→ is_admin), `is_profile_complete`, `primary_redirect`, `tier_name`, `type_label`, `type_icon`, `type_color`, `has_permission()`
  - Relationship: `bars_at_location` → list of Bar objects at this dealer

### admin/models.py
- **SystemSetting**: id, key (unique), value, description
- **RequestLog**: id, method, path, query_string, status_code, ip_address, user_agent, user_type, user_id, user_display, body_preview, response_time_ms, created_at — لاگ درخواست‌ها (middleware ثبت میکنه)

### customer/address_models.py
- **GeoProvince**: id, name (unique), sort_order → has many GeoCity
- **GeoCity**: id, province_id (FK), name, sort_order → has many GeoDistrict
- **GeoDistrict**: id, city_id (FK), name
- **CustomerAddress**: id, user_id (FK→users), title, province_id, city_id, district_id, address, postal_code, receiver_name, receiver_phone, is_default

### catalog/models.py
- **ProductCategory**: id, name (unique), slug (unique), sort_order, is_active
- **ProductCategoryLink**: id, product_id (FK → products), category_id (FK → product_categories) — M2M junction (UniqueConstraint)
- **Product**: id, name, weight (Decimal), purity (int: 750=18K), wage (Numeric 5,2 — percent), is_wage_percent, design, card_design_id, package_type_id, metal_type (String(20), default="gold"), is_active
  - `metal_type` maps to `PRECIOUS_METALS` keys ("gold", "silver") — determines which asset price + base purity to use for pricing
  - Properties: `categories` (list of ProductCategory), `category_ids` (list of int)
- **ProductImage**: id, product_id, path, is_default
- **CardDesign / CardDesignImage**: طرح کارت‌های هدیه
- **PackageType / PackageTypeImage**: بسته‌بندی — price (BigInteger, ریال, default=0), is_active (Boolean, default=True)
- **Batch / BatchImage**: بچ تولید (ذوب)

### inventory/models.py
- **Bar**: id, serial_code (unique), product_id, batch_id, dealer_id (FK→users), customer_id (FK→users), claim_code (unique, nullable — for POS/gift), status (RAW/ASSIGNED/RESERVED/SOLD), reserved_customer_id, reserved_until, delivered_at (nullable — NULL = custodial/"امانی", set = physically delivered)
  - Relationship: `dealer_location` → User (physical location), `customer` → User (owner)
  - Custodial gold ("طلای امانی") = bars with `status == SOLD` and `delivered_at IS NULL`
- **BarImage**: id, bar_id, file_path
- **OwnershipHistory**: id, bar_id, previous_owner_id, new_owner_id, transfer_date, description
- **DealerTransfer**: id, bar_id, from_dealer_id, to_dealer_id, transferred_by, transferred_at, description (table: dealer_location_transfers)
- **BarTransfer**: id, bar_id, from_customer_id, to_mobile, otp_hash, otp_expiry, status (Pending/Completed/Cancelled/Expired), created_at

### cart/models.py
- **Cart**: id, customer_id (FK→users, unique), created_at
- **CartItem**: id, cart_id, product_id, quantity, package_type_id (FK→package_types, nullable)

### order/models.py
- **Order**: id, customer_id (FK→users), status (Pending/Paid/Cancelled), cancellation_reason, cancelled_at, delivery_method (Pickup/Postal), is_gift (bool), pickup_dealer_id (FK→users), shipping_province, shipping_city, shipping_address, shipping_postal_code, delivery_code_hash, delivery_status, total_amount, shipping_cost, insurance_cost, coupon_code, promo_choice (DISCOUNT/CASHBACK), promo_amount, cashback_settled, payment_method, payment_ref, paid_at, track_id, delivered_at, created_at
- **OrderItem**: id, order_id, product_id, bar_id, applied_metal_price, applied_unit_price, applied_weight, applied_purity, applied_wage_percent, applied_tax_percent, final_gold_amount, final_wage_amount, final_tax_amount, package_type_id (FK→package_types, nullable), applied_package_price (BigInteger, default=0), line_total (= gold_total + package_price)
- **OrderStatusLog**: id, order_id (FK→orders, CASCADE), field ("status"/"delivery_status"), old_value, new_value, changed_by, description, created_at — audit trail for status changes

### wallet/models.py
- **AssetCode** (enum values): `IRR`, `XAU_MG` (gold milligrams), `XAG_MG` (silver milligrams)
- **PRECIOUS_METALS** (dict): Metadata registry for generic metal trading. Keys: `"gold"`, `"silver"`. Each entry contains: `asset_code`, `asset_key` (pricing), `label`, `unit`, `base_purity` (750 for gold, 999 for silver), `fee_customer_key`, `fee_dealer_key`, `fee_customer_default`, `fee_dealer_default`. Used by routes to validate `{asset_type}` path param, drive buy/sell logic generically, and provide base purity for pricing calculations.
- **Account**: id, user_id (FK→users), asset_code (IRR/XAU_MG/XAG_MG), balance, locked_balance, credit_balance (non-withdrawable store credit)
  - `available_balance` = balance - locked (for purchases)
  - `withdrawable_balance` = balance - locked - credit (for bank withdrawals)
- **LedgerEntry**: id, account_id, txn_type (Deposit/Withdraw/Payment/Refund/Hold/Release/Commit/Credit), delta_balance, delta_locked, delta_credit, balance_after, locked_after, credit_after, idempotency_key, reference_type, reference_id, description
  - Properties: `is_gold` (bool — XAU_MG account), `is_silver` (bool — XAG_MG account), `is_precious_metal` (bool — any metal account)
- **WalletTopup**: id, user_id (FK→users), amount_irr, status, ref_number, gateway
- **WithdrawalRequest**: id, user_id (FK→users), amount_irr, status (PENDING/PAID/REJECTED), shaba_number, account_holder

### coupon/models.py
- **Coupon**: id, code (unique), title, description, coupon_type (DISCOUNT/CASHBACK), discount_mode (PERCENT/FIXED), discount_value, max_discount_amount, scope (GLOBAL/PRODUCT/CATEGORY), scope_product_id, min_order_amount, first_purchase_only, is_private, max_per_customer, max_total_uses, status (ACTIVE/INACTIVE/EXPIRED)
- **CouponCategory**: id, coupon_id, category_id → M2M junction (coupon ↔ product_categories)
- **CouponMobile**: id, coupon_id, mobile → whitelist
- **CouponUsage**: id, coupon_id, user_id (FK→users), order_id, discount_applied

### dealer/models.py
- **DealerTier**: id, name, slug (unique), sort_order, is_end_customer, is_active
- **DealerSale**: id, dealer_id (FK→users), bar_id, customer_name/mobile/national_id, sale_price, commission_amount, metal_profit_mg, discount_wage_percent (Numeric 5,2 — تخفیف اجرت از سهم نماینده), metal_type (String(20), default="gold"), parent_dealer_id (FK→users, nullable — parent dealer for sub-dealer sales), parent_commission_mg (Numeric 12,4, nullable — parent's share in mg), description, created_at
  - `applied_metal_price` — metal price at time of sale (was `applied_gold_price`)
  - `metal_type` — which metal was sold ("gold", "silver")
- **BuybackRequest**: id, dealer_id (FK→users), bar_id, customer_name/mobile, buyback_price, status (Pending/Approved/Completed/Rejected), admin_note, description, wage_refund_amount (rial), wage_refund_customer_id (FK→users), created_at, updated_at
- **SubDealerRelation**: id, parent_dealer_id (FK→users, CASCADE), child_dealer_id (FK→users, CASCADE), commission_split_percent (Numeric 5,2, default=20), is_active, created_at, deactivated_at, admin_note
  - UniqueConstraint(parent_dealer_id, child_dealer_id), CheckConstraint(0-100), CheckConstraint(no self-ref)
  - Properties: `status_label`, `status_color`
- **B2BOrderStatus** (enum): Submitted / Approved / Paid / Fulfilled / Rejected / Cancelled
- **B2BOrder**: id, dealer_id (FK→users), status, total_amount (BigInteger), applied_tax_percent, payment_method, payment_ref, paid_at, admin_note, approved_by (FK→users), approved_at, fulfilled_at, created_at, updated_at
  - Properties: `status_label`, `status_color`, `total_items`
  - Relationships: dealer, approver, items
- **B2BOrderItem**: id, order_id (FK→b2b_orders, CASCADE), product_id (FK→products, RESTRICT), quantity, applied_wage_percent, applied_metal_price, unit_price, line_total
  - CheckConstraint(quantity > 0)
- Note: Dealer-specific fields (tier, address, api_key, etc.) are on the unified **User** model

### ticket/models.py
- **TicketCategory** (enum): Financial / Technical / Sales / Complaints / Other (دپارتمان)
- **Ticket**: id, subject, body, category (TicketCategory), status (Open/InProgress/Answered/Closed), priority (Low/Medium/High), sender_type (CUSTOMER/DEALER/STAFF), user_id (FK→users), assigned_to (FK→users), created_at, updated_at, closed_at
  - Properties: sender_name, sender_mobile, status_label/color, priority_label/color, category_label/color, sender_type_label/color, message_count, public_message_count
  - Relationships: user, assigned_staff, messages
- **TicketMessage**: id, ticket_id (FK), sender_type (CUSTOMER/DEALER/STAFF), sender_name (denormalized), body, is_internal (staff-only note), is_initial (first message for attachments), created_at
  - Properties: sender_type_label, sender_badge_color, is_staff_message
  - Relationships: attachments
- **TicketAttachment**: id, message_id (FK→ticket_messages, CASCADE), file_path, created_at
  - Relationship: message

### review/models.py
- **Review**: id, product_id (FK→products), user_id (FK→users), order_item_id (FK→order_items, unique), rating (1-5), body (Text), admin_reply, admin_reply_at, created_at
  - Relationships: product, user, order_item, images
  - CheckConstraint: rating 1-5
- **ReviewImage**: id, review_id (FK→reviews, CASCADE), file_path
- **ProductComment**: id, product_id (FK→products), user_id (FK→users), parent_id (FK→self, CASCADE — threaded), body (Text), sender_type (CUSTOMER/ADMIN), sender_name, created_at
  - Properties: `is_admin`, `has_admin_reply`, `sender_badge_color`, `sender_type_label`
  - Relationships: product, user, parent, replies, images
- **CommentImage**: id, comment_id (FK→product_comments, CASCADE), file_path
- **CommentLike**: id, comment_id (FK→product_comments, CASCADE), user_id (FK→users, CASCADE), created_at
  - UniqueConstraint: (comment_id, user_id)

### pricing/models.py
- **Asset**: id, asset_code (unique, e.g. "gold_18k", "silver"), asset_label, price_per_gram (BigInteger, rial), stale_after_minutes (default 15), auto_update (bool, default True), update_interval_minutes (default 5), source_url, updated_at, updated_by
  - Properties: `is_fresh` (bool), `minutes_since_update` (float)
  - Constants: `GOLD_18K = "gold_18k"`, `SILVER = "silver"`

### dealer_request/models.py
- **DealerRequestStatus** (enum): Pending / Approved / Rejected / RevisionNeeded
- **DealerRequest**: id, user_id (FK→users), first_name, last_name, birth_date, email, mobile, gender, province_id (FK→geo_provinces), city_id (FK→geo_cities), status, admin_note, created_at, updated_at
  - Properties: `full_name`, `status_label`, `status_color`, `gender_label`, `province_name`, `city_name`
  - Relationships: user, province, city, attachments
- **DealerRequestAttachment**: id, dealer_request_id (FK, CASCADE), file_path, original_filename, created_at

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
- `get_current_active_user(request, db)` — Returns User or None (single `auth_token` cookie)
- `require_login` — Depends, raises 401 if not logged in (any role — used by unified wallet)
- `require_customer` — Depends, raises 401 if not `is_customer`
- `require_dealer` — Depends, raises 401 if not `is_dealer`
- `require_staff` — Depends, raises 401 if not `is_admin`
- `require_super_admin` — Depends, raises 401 if not `admin_role=="admin"`
- `require_operator_or_admin` — Either admin role

### Pricing
`modules/pricing/calculator.py` → `calculate_bar_price()`
- Metal price from `Asset` table (asset_code="gold_18k" or "silver"), NOT SystemSetting
- Tax from SystemSetting key `tax_percent`
- `modules/pricing/models.py` → `Asset` model (per-asset price with staleness guard)
- `modules/pricing/service.py` → `get_price_value()`, `require_fresh_price()`, `is_price_fresh()`, `get_product_pricing(db, product)` (returns metal price + base purity + tax based on product's `metal_type`)
- `modules/pricing/feed_service.py` → `fetch_gold_price_goldis()` (auto-fetch from goldis.ir)
- Background scheduler fetches gold price every N minutes (configurable per asset)
- Staleness guard: blocks checkout/POS/wallet if price expired (configurable per asset)
- `calculate_bar_price()` now takes `base_metal_price` + `base_purity` params (generic for any metal)

### Payment Gateway
- لایه انتزاعی `modules/payment/gateways/` با `BaseGateway` و الگوی registry
- درگاه‌های فعال: **Zibal** (sandbox: `ZIBAL_MERCHANT=zibal`)، **Sepehr** (SOAP)، **Top** (REST)، **Parsian** (SOAP via `zeep`)
- تنظیم `active_gateway` در SystemSetting تعیین می‌کند کدام درگاه استفاده شود
- `payment_service.create_gateway_payment()` و `verify_gateway_callback()` — عمومی برای همه درگاه‌ها
- هر درگاه callback مجزا دارد (متد GET یا POST بسته به درگاه)
- شارژ کیف پول هم از درگاه فعال استفاده می‌کند (نه فقط Zibal)

### Currency
- **تمام مبالغ در دیتابیس به ریال ذخیره می‌شوند**
- فیلتر Jinja2 `| toman` تبدیل ریال → تومان (÷10) با فرمت فارسی
- در فرم‌ها: کاربر تومان وارد می‌کند، route `×10` می‌کند

### Template Filters (common/templating.py)
- `| toman` — int rial → formatted toman string
- `| persian_number` — English digits → Persian
- `| jdate` — Gregorian → Jalali date

### ⚠️ Cache Busting — الزامی بعد از تغییر CSS/JS
> **قانون بدون استثنا**: هر بار که فایل CSS یا JavaScript در پوشه `static/` تغییر کند (حتی یک خط)، **باید** مقدار `STATIC_VERSION` در `common/templating.py` بامپ شود.

```python
# common/templating.py — خط 88
STATIC_VERSION = "1.1"  # ← عدد را افزایش بده
```

- تمام فایل‌های CSS/JS در templateها با `?v={{ STATIC_VER }}` لود می‌شوند
- بدون بامپ ورژن، مرورگر کاربران (مخصوصاً موبایل) نسخه کش‌شده قدیمی را نشان می‌دهد
- فایل‌های تأثیرپذیر: `base.html`، `public/verify.html`، `admin/dashboard.html`
- **چک‌لیست**: آیا فایلی در `static/css/` یا `static/vendor/` یا `static/js/` تغییر کرد؟ → `STATIC_VERSION` را بامپ کن

---

## 5. 🐛 باگ‌های شناخته‌شده

### BUG-1: فیلتر دسته‌بندی در shop/home — ✅ FIXED
**فیکس**: `p.category_id == cat_id` بجای `p.get("product")` در `modules/shop/routes.py`

### BUG-2: Wallet topup — ✅ FIXED
**فیکس**: Topup حالا از درگاه فعال (active_gateway) استفاده میکنه + callback route اضافه شد (`/wallet/topup/{gateway}/callback`)

### BUG-3: int_parsing در checkout — ✅ NOT A BUG
**بررسی**: کد فعلی `.isdigit()` قبل از تبدیل چک میکنه. مشکلی وجود نداره.

### BUG-4: CSRF ارور بعد از idle — ✅ FIXED
**فیکس**: Middleware `csrf_cookie_refresh` در `main.py` اضافه شد که در هر GET request بدون cookie، CSRF cookie تازه ست میکنه.

### BUG-5: آمار ادمین بعد از idle قدیمی نشان داده می‌شود — ✅ FIXED
**فیکس**: Middleware `no_cache_admin` در `main.py` اضافه شد که هدرهای `Cache-Control: no-cache, no-store, must-revalidate` برای همه صفحات `/admin/*` و `/dealer/*` ست میکنه. مرورگر دیگر صفحات ادمین را کش نمیکنه.

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
| 9 | Payment (wallet + multi-gateway: Zibal/Sepehr/Top/Parsian) | ✅ |
| 9.5 | Categories, Geo, Addresses, Profile, Verify | ✅ |
| 10 | Verification بهبود (QR, history, API) | ✅ |
| 11 | Dealer / Reseller (POS, buyback, commission) | ✅ |
| 12 | Admin Dashboard (stats, Chart.js, alerts) | ✅ |
| 13 | Ticketing / Support (customer + dealer + admin) | ✅ |
| 14 | Dealer POS REST API (API Key auth, JSON endpoints) | ✅ |
| 14.5 | Bar Claim & Gifting + Ownership Transfer | ✅ |
| 15 | Customer-Facing POS API (reserve→confirm/cancel) | ✅ |
| 16 | Reviews & Comments (star rating, Q&A, likes) | ✅ |
| 21 | Dealer B2B Dashboard (inventory, analytics, sub-dealer, B2B orders) | ✅ |

---

## 7. فازهای آینده (ROADMAP) — مدل B2B2C شمش فیزیکی

> **اصل راهبردی**: تمام فازها حول محور «شمش فیزیکی + شبکه نمایندگان» طراحی شده‌اند.
> فیچرهای صرافی/ترید (DCA، داشبورد PNL، طلای دیجیتال کسری) عمداً حذف شده‌اند.

### 📌 Phase 17: Notifications (بحرانی)
- SMS تراکنشی (Kavenegar production): lifecycle سفارش، کیف پول، انتقال مالکیت، تیکت، بازخرید
- مرکز اعلان داخلی (In-app): مدل Notification + صفحه اعلان‌ها + badge خوانده‌نشده
- Email: تأییدیه سفارش (فاکتور HTML)، خلاصه ماهانه، خوش‌آمدگویی
- تنظیمات اعلان مشتری (انتخاب کانال به تفکیک رویداد)

### 📌 Phase 18: Shahkar + Security Hardening (الزامی)
- احراز هویت شاهکار (تطبیق موبایل + کد ملی) → full_name, national_id → readonly
- Step-up auth: OTP مجدد برای تراکنش‌های حساس (سفارش بالای X تومان، برداشت، انتقال مالکیت)
- Rate limiting روی OTP، ورود ناموفق، API endpoints

### 📌 Phase 19: Loyalty + Referral (بالا)
- سطح‌بندی مشتریان بر اساس وزن کل خرید (برنز/نقره/طلا/الماس) → تخفیف اجرت، ارسال رایگان
- پاداش طلایی (Gold Rewards): کشبک به صورت میلی‌گرم طلا در XAU_MG wallet (non-withdrawable credit)
- برنامه معرفی (Referral): کد اختصاصی + پاداش طلایی به معرف و معرفی‌شده

### 📌 Phase 20: Gift System (بالا)
- کارت هدیه فیزیکی طلا: کد فعال‌سازی + وزن مشخص + فروش سازمانی (B2B عیدی/جوایز)
- بسته‌بندی کادویی: گسترش PackageType با آپشن‌های کادویی (جعبه چرم، عروسی، نوروزی) + پیام تبریک
- کمپین‌های مناسبتی (نوروز، ولنتاین، یلدا)

### 📌 Phase 21: Dealer Portal Enhancement — B2B Dashboard (بالا)
- داشبورد تحلیلی نماینده: نمودار فروش، مقایسه دوره‌ای، رتبه‌بندی، کمیسیون تجمیعی
- تسویه سود طلایی: واریز gold_profit_mg به XAU_MG wallet نماینده + تبدیل به ریال + برداشت بانکی
- زیرمجموعه‌ها (Sub-dealer): نماینده اصلی → زیرنماینده + تقسیم کمیسیون + درخت نمایندگان
- سفارش عمده نمایندگان (B2B Orders): ثبت سفارش عمده از پنل نماینده + تأیید ادمین
- اعلان‌های اختصاصی نماینده (موجودی کم، محصول جدید، تغییر قیمت)

### 📌 Phase 22: Advanced Inventory & Tracking (متوسط-بالا)
- هشدار موجودی: آستانه هر محصول + اعلان ادمین/نماینده + پیش‌بینی اتمام
- رهگیری فیزیکی: لاگ جابجایی شمش بین لوکیشن‌ها + بارکد/QR scan + گزارش مغایرت
- ارتقای مدل امانی: درخواست تحویل فیزیکی از پنل مشتری + انتخاب لوکیشن + تأیید OTP
- ادغام رهگیری پست: API پست ایران/تیپاکس + نمایش وضعیت + اعلان خودکار

### 📌 Phase 23: SEO + Content (متوسط)
- بلاگ/مجله آموزشی: ماژول Article + آموزش محصول فیزیکی (نه تحلیل بازار)
- SEO فنی: JSON-LD Product schema، Clean URL/slug، XML sitemap، FAQ schema
- ابزارهای تعاملی: ماشین‌حساب قیمت شمش، راهنمای انتخاب شمش

### 📌 Phase 24: Advanced Analytics + PDF (متوسط-پایین)
- گزارش ادمین: عملکرد نمایندگان، فروش محصول/دسته/دوره، مشتریان ارزشمند (LTV)، conversion funnel
- گزارش نماینده: خلاصه فروش ماهانه + کمیسیون + لیست مشتریان
- PDF Export: فاکتور سفارش، تسویه‌حساب نماینده، گزارش مدیریتی، گواهی اصالت شمش

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

### Test Bars (Custodial — طلای/نقره امانی)
| سریال‌کد | نوع | خریدار | مالک فعلی | توضیح |
|----------|------|--------|-----------|--------|
| TSCST001 | طلا | 09351234567 | 09351234567 | امانی عادی (خریدار = مالک) |
| TSCST002 | طلا | 09351234567 | 09359876543 | انتقال یافته (خریدار ≠ مالک) |
| TSCST003 | نقره | 09351234567 | 09351234567 | نقره امانی عادی |

### Payment Gateways
- **Zibal**: `ZIBAL_MERCHANT=zibal` → sandbox (auto-succeed), `your-real-id` → production
- **Sepehr**: `SEPEHR_TERMINAL_ID=99079327` → test terminal
- **Top**: `TOP_USERNAME` + `TOP_PASSWORD`
- **Parsian**: `PARSIAN_PIN` (SOAP via `zeep`)
- درگاه فعال با SystemSetting `active_gateway` تعیین می‌شود (مقدار: `zibal`/`sepehr`/`top`/`parsian`)
- Callbacks: `{BASE_URL}/payment/{gateway}/callback`

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

### ⚠️ وقتی ماژول یا فیچر مهم جدید اضافه می‌کنی — الزام مستندسازی:
> **قانون بدون استثنا**: بعد از ساخت هر ماژول، فیچر مهم یا endpoint جدید، **حتماً** این سندها بروزرسانی شوند:

1. **CLAUDE.md** → بخش‌های مربوطه:
   - ساختار فایل‌ها (بخش 2)
   - مدل‌های دیتابیس (بخش 3) — اگر مدل جدید داری
   - API Endpoints (بخش 11) — اگر route جدید داری
   - فازهای تکمیل‌شده (بخش 6) — اگر فاز جدید تکمیل شده
2. **docs/Feature-Catalog.md** → ماژول + endpoint ها + جدول دسترسی
3. **docs/Test-Playbook.md** → تست‌کیس‌های جدید
4. **scripts/seed.py** → داده تست برای ماژول جدید (اگر لازم)

**چرا مهمه؟** بدون مستندسازی، ماژول‌ها «گم» می‌شوند (مثل review و pos که کد کامل داشتند ولی مستند نشده بودند).

### الگوی Atomic Transaction (پرداخت):
```python
# 1. wallet_service.withdraw() → flush (no commit)
# 2. Set order.payment_* fields
# 3. order_service.finalize_order() → commit (atomic)
# 4. Route's db.commit() → no-op
# On failure: db.rollback() undoes everything
```

### وقتی درگاه پرداخت جدید اضافه می‌کنی:
1. کلاس جدید از `BaseGateway` در `modules/payment/gateways/` بساز
2. متدهای `request_payment()` و `verify_payment()` را پیاده‌سازی کن
3. در `modules/payment/gateways/__init__.py` → `GATEWAY_REGISTRY` اضافه کن
4. Callback route جدید در `modules/payment/routes.py` اضافه کن
5. Callback route جدید برای topup در `modules/wallet/routes.py` اضافه کن
6. env var مربوطه را در `config/settings.py` و `.env.example` اضافه کن

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

## 10. فرمول قیمت‌گذاری فلزات (عمومی)

```
raw_metal = weight × (purity / base_purity) × metal_price
wage      = raw_metal × (wage% / 100)
tax       = wage × (tax% / 100)          ← مالیات فقط روی اجرت
total     = raw_metal + wage + tax
```

- `base_purity`: 750 for gold (18K reference), 999 for silver (pure reference) — defined in `PRECIOUS_METALS` dict
- `metal_price`: per-gram price from `Asset` table (e.g. `gold_18k`, `silver`)
- تابع: `calculate_bar_price()` در `modules/pricing/calculator.py` — now accepts `base_metal_price` + `base_purity` params
- Helper: `get_product_pricing(db, product)` در `modules/pricing/service.py` — returns `(metal_price, base_purity, tax_percent)` based on product's `metal_type`
- product.wage = اجرت مشتری نهایی (auto-sync به ProductTierWage)
- سطوح نمایندگان: هر سطح اجرت کمتری دارد → اختلاف = سود نماینده (به فلز)

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
- `POST /auth/send-otp` — Send OTP
- `POST /auth/verify-otp` — Verify → JWT cookie
- `GET /auth/logout` — Clear cookie

### Customer
- `GET/POST /profile` — Profile
- `GET/POST /addresses` — Address CRUD
- `POST /addresses/{id}/delete|default`
- `GET /api/geo/cities?province_id=X`
- `GET /api/geo/districts?city_id=X`
- `GET /api/geo/dealers?province_id=X&city_id=X&district_id=X` — فیلتر نمایندگان بر اساس موقعیت (همه optional)

### Cart & Orders
- `GET /cart` — Cart page
- `POST /cart/update` — افزودن/حذف آیتم (با product_id + action + package_type_id)
- `POST /cart/set-package` — تغییر بسته‌بندی آیتم سبد خرید
- `GET /checkout` — Checkout
- `POST /cart/checkout` — Place order
- `GET /orders` — My orders
- `GET /orders/{id}` — Order detail

### Payment
- `POST /payment/{id}/wallet` — Wallet pay
- `POST /payment/{order_id}/gateway` — Pay via active gateway (replaces per-gateway routes)
- `GET /payment/zibal/callback` — Zibal callback
- `POST /payment/sepehr/callback` — Sepehr callback
- `GET /payment/top/callback` — Top callback
- `POST /payment/parsian/callback` — Parsian callback
- `POST /payment/{id}/refund` — Admin refund

### Wallet (unified — all user types via `require_login`)
- `GET /wallet` — Dashboard (IRR + gold balance for all users)
- `GET /wallet/transactions` — History (supports `?asset=irr|gold` filter)
- `POST /wallet/topup` — Charge (via active gateway)
- `GET /wallet/topup/zibal/callback` — Zibal topup callback
- `POST /wallet/topup/sepehr/callback` — Sepehr topup callback
- `GET /wallet/topup/top/callback` — Top topup callback
- `POST /wallet/topup/parsian/callback` — Parsian topup callback
- `GET/POST /wallet/withdraw` — Withdrawal (+ past withdrawal history)
- `GET /wallet/{asset_type}` — Precious metal buy/sell page (validates `asset_type` in `PRECIOUS_METALS`: gold, silver, etc.)
- `POST /wallet/{asset_type}/buy` — Buy metal: convert IRR → metal account (with role-based fee)
- `POST /wallet/{asset_type}/sell` — Sell metal: convert metal account → IRR (with role-based fee)
- **Precious metal trade fees** (configurable in admin settings):
  - Gold: `gold_fee_customer_percent` (default 2%), `gold_fee_dealer_percent` (default 0.5%)
  - Silver: `silver_fee_customer_percent` (default 1.5%), `silver_fee_dealer_percent` (default 0.3%)

### AJAX APIs
- `GET /api/delivery/locations?province=X&city=Y` — returns pickup dealers for province/city
- `GET /api/coupon/check?code=X`

### Dealer Request (Customer)
- `GET /dealer-request` — Show form (new) or status page (existing)
- `GET /dealer-request?edit=1` — Show pre-filled form for RevisionNeeded requests
- `POST /dealer-request` — Submit new or resubmit revised request

### Dealer Panel (Web)
- `GET /dealer/dashboard` — Dealer dashboard (stats, quick actions)
- `GET/POST /dealer/pos` — POS sale form
- `GET/POST /dealer/buyback` — Buyback request form
- `GET /dealer/sales` — Sales history
- `GET /dealer/buybacks` — Buyback history
- `GET /dealer/inventory` — Physical inventory at dealer location
- `GET /dealer/sub-dealers` — Sub-dealer network (read-only)
- `GET /dealer/b2b-orders` — B2B bulk order list
- `GET /dealer/b2b-orders/new` — New B2B order catalog
- `POST /dealer/b2b-orders/new` — Submit B2B order
- `GET /dealer/b2b-orders/{id}` — B2B order detail
- `POST /dealer/b2b-orders/{id}/pay` — Pay via wallet
- `POST /dealer/b2b-orders/{id}/cancel` — Cancel order

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
- `/admin/bars|orders|settings`
- `GET /admin/customers` — لیست کاربران + جستجو + فیلتر (فعال/غیرفعال)
- `GET /admin/customers/{id}` — جزئیات کاربر (تب‌ها: خلاصه، تراکنش کیف پول، سفارشات، درخواست برداشت)
- `POST /admin/customers/{id}` — ویرایش اطلاعات مشتری (نام، موبایل، کد ملی، نوع مشتری، وضعیت فعال/غیرفعال)
- `/admin/wallets` — حساب‌ها, `/admin/wallets/withdrawals/list` — برداشت‌ها
- `/admin/coupons`
- `GET /admin/dealer-requests` — Dealer request list (filter: status, search)
- `GET /admin/dealer-requests/{id}` — Dealer request detail
- `POST /admin/dealer-requests/{id}/approve` — Approve request
- `POST /admin/dealer-requests/{id}/revision` — Request revision (admin_note required)
- `POST /admin/dealer-requests/{id}/reject` — Reject request
- `/admin/dealers` — Dealer list + create/edit
- `GET /admin/dealers/sales` — گزارش فروش نمایندگان (فیلتر: نماینده، تاریخ، جستجو، تخفیف + آمار تجمیعی)
- `POST /admin/dealers/{id}/generate-api-key` — Generate POS API key
- `POST /admin/dealers/{id}/revoke-api-key` — Revoke POS API key
- `POST /admin/dealers/{id}/rasis-sync` — Manual full sync of dealer inventory + pricing to Rasis POS device
- `GET /admin/dealers/{id}/sub-dealers` — Sub-dealer management
- `POST /admin/dealers/{id}/sub-dealers/add` — Create sub-dealer relation
- `POST /admin/dealers/sub-dealers/{rel_id}/deactivate` — Deactivate relation
- `GET /admin/dealers/b2b-orders` — All B2B orders (filter: dealer, status)
- `GET /admin/dealers/b2b-orders/{id}` — B2B order detail
- `POST /admin/dealers/b2b-orders/{id}/approve` — Approve B2B order
- `POST /admin/dealers/b2b-orders/{id}/reject` — Reject B2B order
- `POST /admin/dealers/b2b-orders/{id}/fulfill` — Fulfill (assign bars from warehouse)
- `/admin/dealers/buybacks` — Buyback approval/rejection
- `GET /admin/tickets` — Ticket list (tabs: all/customer/dealer + status/category filter + search)
- `GET /admin/tickets/{id}` — Ticket detail + reply + internal notes + assign
- `POST /admin/tickets/{id}/reply` — Admin reply (with file attachments)
- `POST /admin/tickets/{id}/internal-note` — Staff-only internal note (invisible to customer/dealer)
- `POST /admin/tickets/{id}/status` — Change status (sends notification)
- `POST /admin/tickets/{id}/close` — Close ticket
- `POST /admin/tickets/{id}/assign` — Assign to staff

### Reviews & Comments (Customer)
- `POST /reviews/submit` — Submit review (from order detail page, with images)
- `POST /reviews/comment` — Add comment on product page (with images for buyers)
- `POST /reviews/comment/{comment_id}/like` — Toggle like (AJAX, CSRF via header)

### Customer-Facing POS API (JSON, API Key auth via X-API-Key header)
- `GET /api/pos/categories` — Product categories with available stock at dealer
- `GET /api/pos/products?category_id=X` — Products with live pricing + stock count
- `POST /api/pos/reserve` — Reserve a bar before card payment (2-minute hold)
- `POST /api/pos/confirm` — Confirm sale after successful payment
- `POST /api/pos/cancel` — Cancel reservation (payment failed)
- `GET /api/pos/receipt/{sale_id}` — Receipt data for printing

### Admin Reviews
- `GET /admin/reviews` — Review + comment list (tabs: comments/reviews, search, pagination)
- `GET /admin/reviews/comment/{id}` — Comment detail + replies
- `GET /admin/reviews/review/{id}` — Review detail
- `POST /admin/reviews/comment/{id}/reply` — Admin reply to comment
- `POST /admin/reviews/review/{id}/reply` — Admin reply to review
- `POST /admin/reviews/comment/{id}/delete` — Delete comment
- `POST /admin/reviews/review/{id}/delete` — Delete review

### Request Audit Log
- `GET /admin/logs` — لاگ درخواست‌ها با فیلتر (متد، وضعیت، مسیر، نوع کاربر، IP)

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
TOP_USERNAME=your-top-username
TOP_PASSWORD=your-top-password
PARSIAN_PIN=your-parsian-pin
RASIS_API_URL=https://rasis-api-url
RASIS_USERNAME=your-rasis-username
RASIS_PASSWORD=your-rasis-password
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
- [ ] **فایل CSS/JS تغییر کرد؟ → `STATIC_VERSION` در `common/templating.py` بامپ شد**
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

> **⚠️ الزامی و بدون استثنا**: بعد از **هر** تغییر کدی (حتی یک خط)، **حتماً** تغییرات را commit و push کن. این کار را هرگز فراموش نکن!

### قوانین:
- **بلافاصله** بعد از اتمام هر تسک یا تغییر: `git add [files]` + `git commit -m "..."` + `git push`
- پیام کامیت انگلیسی، مختصر و گویا باشد (توضیح **چرا**، نه فقط **چه**)
- **هرگز** تغییرات را بدون commit و push رها نکن — حتی اگر تغییر کوچک باشد
- اگر چند تغییر مرتبط داری، یک commit با پیام جامع بزن
- اگر تغییرات غیرمرتبط داری، commit های جداگانه بزن
- فقط فایل‌هایی که خودت تغییر دادی را stage کن — تغییرات ناشناخته دیگران را commit نکن
- بعد از push حتماً `git status` بزن تا مطمئن شوی همه چیز پوش شده
