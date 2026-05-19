# Flow 04 — Physical Purchase from Wallet

> **Source:** §12.5.1 — خرید محصول فیزیکی با wallet XAU_MG (چهار حالت تسویه)
> **D-31:** gold withdrawal as separate flow removed — this replaces it.

---

## 1. Goal

Customer uses their XAU_MG wallet balance to purchase a physical gold bar. Supports split payment: gold wallet + IRR wallet + gateway (any combination).

## 2. Actors

- **Customer** (authenticated, has XAU_MG balance)
- **Brand website** (determines wallet scope)
- **Payment gateway** (if rial shortfall exists)
- **Goldis Treasury**
- **Warehouse operator** (if delivery requested)

## 3. Preconditions

- Customer has XAU_MG balance in the brand's scope
- Product exists and is in stock
- Price is fresh
- KYC limits allow the transaction
- O-03: withdrawal only as existing products — customer must choose an available bar of exact weight

## 4. Trigger

`POST /api/v1/orders` with `order_type: physical_purchase_from_wallet`.

## 5. Steps

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

## 6. DB Writes

- `orders` — order_type=physical_purchase_from_wallet
- `order_items` — with full price snapshot
- `order_payment_allocations` — up to 3 rows (wallet_gold, wallet_rial, gateway_rial)
- `wallet_locks` — 1 or 2 locks (XAU_MG + optional IRR)
- `wallet_ledger_entries` — debit XAU_MG, optional debit IRR
- `asset_balances` — XAU_MG decreased, optional IRR decreased
- `bars` — status SOLD, customer_id set
- `payments` — if gateway portion exists

> Canonical schemas: [Order](../03-schema-index.md#11-order), [Wallet](../03-schema-index.md#2-wallet), [Inventory](../03-schema-index.md#10-inventory)

## 7. Treasury Impact

Two independent legs ([D-66](../01-decisions-audit-log.md)):
- Leg 1: delta = −gold_part_mg (digital gold consumed → exposure closed)
- Leg 2: delta = +pure_gold_mg (physical bar exits → exposure opened)
- Net: −wage_gold_mg (wage is production cost, removed from exposure)

⚠️ Recording only Leg 1 is a BUG — an unhedged bar would leave the system with lost exposure.

## 8. Wallet Impact

- XAU_MG: lock → consume (debit gold_part_mg)
- IRR (optional): lock → consume (debit irr_from_wallet)
- Both via lock mechanism for atomicity

## 9. Inter-Company Impact

Same as [Flow 01](01-physical-bar-purchase-site.md) §9 — if payment_receiver ≠ Goldis, 2 entries (rial + gold).

## 10. Audit & Events

- `outbox_events`: `OrderPaid`, `TreasuryPositionOpened` (×2 legs), `InterCompanyObligationCreated` (if non-Goldis), `WalletDebited`

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Insufficient XAU_MG | Reject |
| Insufficient IRR + no gateway | Reject |
| Gateway fails after wallet locks | Release all locks, release reservation, cancel price lock |
| Concurrent wallet drain | Lock mechanism prevents over-spend |
| Treasury cap | Reject (inline hard block) |

## 12. Invariants

- Split payment: atomic confirm or atomic release — never partial ([D-39](../01-decisions-audit-log.md))
- Treasury two-leg recording is MANDATORY ([D-66](../01-decisions-audit-log.md))
- `pure_gold_mg = weight_mg × purity / 1000` — always pure weight
- Fulfillment task only on delivery request, not payment ([D-77](../01-decisions-audit-log.md))

## 13. Related References

- [Flow 01 — Physical Bar Purchase](01-physical-bar-purchase-site.md) (gateway-only variant)
- [Domain Models — Wallet](../02-domain-models.md#۴-مدل-wallet-per-wallet-scope)
- [Schema: Order](../03-schema-index.md#11-order) (see `order_payment_allocations`)
- [API: Physical from wallet](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-31](../01-decisions-audit-log.md), [D-39](../01-decisions-audit-log.md), [D-47](../01-decisions-audit-log.md), [D-66](../01-decisions-audit-log.md), [D-77](../01-decisions-audit-log.md)
