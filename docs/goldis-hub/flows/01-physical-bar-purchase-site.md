# Flow 01 — Physical Bar Purchase (Site)

> **Source:** §12.1 — خرید شمش از سایت TalaMala

---

## 1. Goal

Customer purchases a physical gold bar from a brand website (e.g., talamala.ir). The bar is either custodially held or delivered.

## 2. Actors

- **Customer** (authenticated, KYC-cleared)
- **Brand website** (TalaMala / Goldis / AminZar)
- **Payment gateway** (IPG of payment_receiver company)
- **Goldis Treasury** (central hedging desk)
- **Warehouse operator** (fulfillment, only if delivery requested)

## 3. Preconditions

- Customer KYC level sufficient for purchase amount (limits per [D-61](../01-decisions-audit-log.md))
- Product is active and in stock (at least one bar available in brand's inventory)
- Price is fresh (staleness guard per asset)
- Trade is enabled for this metal + channel (trade guard)
- Treasury capacity check passes — two-level cap per [D-101](../01-decisions-audit-log.md): at checkout an `inventory_pending_holds` row (with `expires_at`, [D-105](../01-decisions-audit-log.md)) is written under `pg_advisory_xact_lock(hashtext('treasury:'||metal_type))` enforcing `committed + reserved + this_tx ≤ cap`; at PaymentVerified the hold is finalized into a `treasury_position`. Lock order: advisory(treasury per metal) → wallet rows → bar.

## 4. Trigger

`POST /api/v1/cart/items` with `X-Channel-Code` header → checkout flow starts.

## 5. Steps

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
7. on verified (gateway-verify happens OUTSIDE the tx; the writes below execute in ONE atomic transaction per [D-103](../01-decisions-audit-log.md) — order: wallet ledger → treasury position (finalized from the pending hold) → inter-company net rows → outbox → order.status=Paid; crash recovery = idempotent retry keyed on a stable business key, NOT a saga):
   - UPDATE payments status=verified
   - Order.mark_paid:
     • UPDATE orders status=Paid
     • Inventory.consume(bar) → status=SOLD, customer_id=user_id
     • (D-77: اگر تحویل فوری/POS → create_task(order_item, bar)؛ اگر امانی → هیچ task، فقط هنگام درخواست تحویل ساخته می‌شود)
     • Treasury.finalize_from_hold(source=order_physical, delta=+pure_gold_mg,  # D-91 pure weight; D-101/D-105 finalized from the pending hold
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

## 6. DB Writes

- `orders` — new row (order_type=purchase, status=Paid)
- `order_items` — with buyback_credit_rial, raw_hedge_price_rial, pure_gold_mg snapshots
- `bars` — status: RESERVED → SOLD, customer_id set, sale_wallet_scope set ([D-71](../01-decisions-audit-log.md))
- `inventory_pending_holds` — created at checkout (with `expires_at`, [D-105](../01-decisions-audit-log.md)), finalized at PaymentVerified ([D-101](../01-decisions-audit-log.md))
- `price_locks` — created at step 3, used_in_order_id set at step 4
- `payments` / `payment_states` — gateway payment record; per [D-103](../01-decisions-audit-log.md) the state machine ([D-98](../01-decisions-audit-log.md)) is observability/alerting only and is never read to resume control-flow

> Canonical schemas: [Order](../03-schema-index.md#11-order), [Inventory](../03-schema-index.md#10-inventory), [Payment](../03-schema-index.md#12-payment), [Pricing](../03-schema-index.md#9-pricing)

## 7. Treasury Impact

- `treasury_positions` += `pure_gold_mg` (source=order_physical, triggered_by_brand)
- Sign: **positive** (Goldis now owes gold — open exposure)
- Two-level cap check under advisory lock: pending_hold at checkout, finalize at PaymentVerified ([D-101](../01-decisions-audit-log.md))

> Canonical schema: [Treasury](../03-schema-index.md#3-treasury)

## 8. Wallet Impact

- No wallet writes at purchase time (customer pays via gateway)
- Wallet writes happen only during buyback (see [Flow 05](05-buyback-undelivered.md), [Flow 06](06-buyback-in-person.md))

## 9. Inter-Company Impact

If `payment_receiver != Goldis` (e.g., TalaMala-side sale):
- 2 entries in `inter_company_ledger`:
  - TalaMala → Goldis, rial, `raw_hedge_price_rial` (P_hedge × pure_gold_mg)
  - Goldis → TalaMala, gold, `pure_gold_mg`

If `payment_receiver == Goldis`: no inter-company entries (Goldis buys from market directly).

> Canonical schema: [Inter-Company Ledger](../03-schema-index.md#4-inter-company-ledger)
> Flow logic: see [§6.4 in domain models](../02-domain-models.md)

## 10. Audit & Events

- `audit_logs`: order creation, payment verification, inventory consumption
- `outbox_events`:
  - `OrderPaid`
  - `TreasuryPositionOpened`
  - `InterCompanyObligationCreated` (if non-Goldis)
  - `AccountingEventCreated`
  - `FulfillmentTaskCreated` (only when delivery requested — [D-77](../01-decisions-audit-log.md))

> Canonical event list: [Events](../05-security-audit-events.md)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Price lock expired | Reject checkout, user must re-lock |
| Inventory reserve fails (no stock) | Reject checkout |
| Gateway payment fails/times out | Release reservation, cancel price lock, Order → PaymentFailed |
| Treasury cap exceeded | Reject checkout (two-level cap hard block under advisory lock — [D-47](../01-decisions-audit-log.md), [D-101](../01-decisions-audit-log.md)) |
| KYC limit exceeded | Reject checkout |

## 12. Invariants

- `pure_gold_mg = weight_mg × purity / 1000` — always pure weight, never raw weight ([D-91](../01-decisions-audit-log.md))
- Buyback snapshot is immutable once order is paid — `buyback_credit_rial` and `pure_gold_mg` frozen at purchase time ([D-32](../01-decisions-audit-log.md))
- `raw_hedge_price_rial` = P_hedge_per_mg × pure_gold_mg — sole basis for inter_company_ledger ([D-65](../01-decisions-audit-log.md))
- Fulfillment task NOT created at payment — only when customer requests delivery ([D-77](../01-decisions-audit-log.md))
- `bar.sale_wallet_scope` set at sale, IMMUTABLE while `status=SOLD`; reset to NULL when the bar returns via buyback (resaleable in any scope) ([D-71](../01-decisions-audit-log.md), [D-92](../01-decisions-audit-log.md))

## 13. Related References

- [Domain Models — Companies/Brands/Channels](../02-domain-models.md#۳-مدل-companies--brands--channels)
- [Domain Models — Inter-Company Ledger](../02-domain-models.md)
- [Schema: Order](../03-schema-index.md#11-order) | [Inventory](../03-schema-index.md#10-inventory) | [Payment](../03-schema-index.md#12-payment)
- [API: Cart/Checkout/Order](../04-api-index.md) | [Payment](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- [Reference: Inventory/Bars](../references/inventory-bars-warehouse.md)
- Decisions: [D-06b](../01-decisions-audit-log.md), [D-32](../01-decisions-audit-log.md), [D-47](../01-decisions-audit-log.md), [D-49](../01-decisions-audit-log.md), [D-65](../01-decisions-audit-log.md), [D-71](../01-decisions-audit-log.md), [D-77](../01-decisions-audit-log.md), [D-78](../01-decisions-audit-log.md), [D-91](../01-decisions-audit-log.md), [D-92](../01-decisions-audit-log.md), [D-98](../01-decisions-audit-log.md), [D-101](../01-decisions-audit-log.md), [D-103](../01-decisions-audit-log.md), [D-105](../01-decisions-audit-log.md)
