# Flow 05 — Buyback — Undelivered (Online, Automatic)

> **Source:** §12.5.2 حالت (a) — بازخرید تحویل‌نشده (آنلاین، اتومات)
> Note: Refund does not exist. Original sale is NEVER reversed. Buyback is an independent forward transaction.

---

## 1. Goal

Customer requests buyback of a bar that has been sold but NOT physically delivered (custodial gold, `delivered_at IS NULL`). The bar returns to inventory; customer receives gold + optional rial credit to wallet.

## 2. Actors

- **Customer** (owner of bar)
- **System** (automatic approval — no manual intervention)

## 3. Preconditions

- `bar.status == SOLD` and `bar.delivered_at IS NULL` (custodial — bar still in our vault)
- `bar.customer_id == current_user`
- If a fulfillment_task exists and is packed/handed_over: this variant NOT allowed → must use [Flow 06 (in-person)](06-buyback-in-person.md)
- Buyback only allowed in the same scope/website where original purchase was made

## 4. Trigger

`POST /api/v1/buyback/undelivered` with `{ order_id }`

## 5. Steps

```
1. User → POST /api/v1/buyback/undelivered { order_id }   (شمش هنوز تحویل نشده)
2. Validate:
   - order.user_id == current_user
   - bar.status == SOLD، bar.delivered_at IS NULL
   - (اگر fulfillment_task ساخته شده و packed/handed_over: حالت (a) مجاز نیست → حالت (b))
3. اتومات (در یک DB transaction):
   - یک سفارش بازخرید مستقل (order_type=buyback) ثبت می‌شود — فروش اصلی دستنخورده
   - old_sale_wallet_scope = bar.sale_wallet_scope          # snapshot BEFORE clearing
   - old_pure_gold_mg = order_item.pure_gold_mg             # snapshot BEFORE clearing
   - Wallet.credit(user, old_sale_wallet_scope, XAU_MG, old_pure_gold_mg)
   - اگر ثبت مالکیت+OTP: Wallet.credit(user, old_sale_wallet_scope, IRR, order_item.buyback_credit_rial)
   - اگر fulfillment_task باز بود → بسته/کنسل می‌شود
   - # فقط بعد از wallet credit و audit:
   - bar.status = ASSIGNED, customer_id = NULL, sale_wallet_scope = NULL  (شمش به خزانه برمیگردد، قابل فروش دوباره در هر scope — D-92)
   - Treasury: دو پای متقابل ⇒ خالص ≈ صفر (physical→digital)
   - Audit log + Outbox: BuybackCompleted + Notification
```

**در هر دو حالت بازخرید:**
- وزن خالص (`weight × purity / 1000`) → wallet **XAU_MG** (همیشه).
- `order_items.buyback_credit_rial` (snapshot موقع خرید) → wallet **IRR** — **فقط اگر** شمش در لحظه‌ی بازخرید به نام کاربر ثبت مالکیت شده باشد و با **OTP** تأیید شود؛ وگرنه ۰.
- اجرت + مالیات + سود + هزینههای اضافه **می‌سوزد**.
- هر دو واریز به **scope برند فروش همان شمش** (`bars.sale_wallet_scope`).
- خزانه: تبدیل physical↔digital ⇒ **خنثی** (پای `+pure_gold_mg` به کیف، پای `−pure_gold_mg` شمش برگشتی)؛ **هیچ تعهد بین‌شرکتی تازهای** ساخته نمی‌شود؛ فقط `buyback_credit_rial` هزینهی ریالی است.
- بازخرید آنلاین فقط در همان scope/وبسایتی که خرید انجام شده مجاز است.

## 6. DB Writes

- `orders` — new row (order_type=buyback) — original order is NOT modified
- `bars` — status: SOLD → ASSIGNED, customer_id = NULL, sale_wallet_scope = NULL ([D-92](../01-decisions-audit-log.md))
- `wallet_ledger_entries` — credit XAU_MG (always) + credit IRR (conditional)
- `asset_balances` — user's balances increased
- `fulfillment_tasks` — cancelled if open

> Canonical schemas: [Order](../03-schema-index.md#11-order), [Inventory](../03-schema-index.md#10-inventory), [Wallet](../03-schema-index.md#2-wallet)

## 7. Treasury Impact

Two counterbalancing legs → **net ≈ zero**:
- Leg 1: +pure_gold_mg (gold credited to wallet — digital asset created)
- Leg 2: −pure_gold_mg (physical bar returned to inventory)
- Physical↔digital conversion: treasury neutral

**No new inter-company obligations** created for buyback.

## 8. Wallet Impact

- XAU_MG: +pure_gold_mg (always, from `order_item.pure_gold_mg`)
- IRR: +buyback_credit_rial (conditional — only if ownership verified + OTP)
- Both credits go to `bars.sale_wallet_scope` (scope of original sale)
- Wage + tax + profit from original sale is **burned** (not returned)

## 9. Inter-Company Impact

**No new inter-company entries.** Buyback is a physical↔digital conversion. Only `buyback_credit_rial` is a rial cost (not an inter-company obligation).

## 10. Audit & Events

- `audit_logs`: buyback transaction, bar status change, wallet credits
- `outbox_events`:
  - `BuybackCompleted`
  - `WalletCredited` (XAU_MG + optional IRR)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Bar already delivered | Reject — must use [Flow 06 (in-person)](06-buyback-in-person.md) |
| Fulfillment task packed/handed_over | Reject — must use Flow 06 |
| Bar not owned by user | Reject (403) |
| Scope mismatch (wrong website) | Reject |

## 12. Invariants

- Original sale is **NEVER** reversed — buyback is always a new independent forward transaction
- `buyback_credit_rial` is immutable snapshot from purchase time ([D-32](../01-decisions-audit-log.md))
- Bar returns to ASSIGNED (resaleable in any scope) — `sale_wallet_scope = NULL` ([D-92](../01-decisions-audit-log.md))
- Treasury net ≈ zero for buyback — no exposure change
- No inter-company obligations for buyback (unlike digital sell which creates them in non-Goldis scope)

## 13. Related References

- [Flow 06 — Buyback In-Person](06-buyback-in-person.md) (state machine variant for delivered bars)
- [Flow 03 — Digital Gold Sell](03-digital-gold-sell.md) (separate flow for «بازخرید دیجیتال» — D-68)
- [Domain Models — Buyback](../02-domain-models.md)
- [Schema: Order](../03-schema-index.md#11-order) | [Inventory](../03-schema-index.md#10-inventory) | [Wallet](../03-schema-index.md#2-wallet)
- [API: Buyback](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-32](../01-decisions-audit-log.md), [D-58](../01-decisions-audit-log.md), [D-71](../01-decisions-audit-log.md), [D-92](../01-decisions-audit-log.md)
