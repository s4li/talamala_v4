# API Index — Goldis Hub v2.7

> **Canonical home for all API contracts and conventions.**
> Flow files reference specific endpoints via markdown links to this document.

> **Source:** `goldis-hub-architecture-v2.7.md` §13

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

