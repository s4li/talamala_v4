# Flow 07 — POS Sale

> **Source:** §12.7 — POS sale (sample: TalaMala POS at dealer)

---

## 1. Goal

Dealer sells a physical gold bar to a customer via POS device at dealer location. Bar is selected from dealer inventory, reserved, paid via card terminal, and ownership transferred.

## 2. Actors

- **Customer** (walk-in at dealer location)
- **Dealer** (operates POS device)
- **POS device** (Android app, API-key authenticated)
- **Payment terminal** (card payment)
- **Goldis Treasury**

## 3. Preconditions

- POS device registered and active (linked to a sales_channel with channel_type=pos)
- Bars available at dealer's inventory_location (status ASSIGNED or RAW)
- Price is fresh (staleness guard)
- Trade enabled for this metal + channel (dealer_pos)
- Treasury two-level cap check passes ([D-101](../01-decisions-audit-log.md)): at reserve, write an `inventory_pending_holds` row (with `expires_at` per [D-105](../01-decisions-audit-log.md)) inside `pg_advisory_xact_lock(hashtext('treasury:'||metal_type))`, enforcing `committed + reserved + this_tx ≤ cap` (committed = SUM open treasury_positions, reserved = SUM live pending_holds); finalized into a `treasury_position` at confirm.

## 4. Trigger

`POST /api/v1/pos/reserve` with `{ bar_id, customer_mobile }` from POS device.

## 5. Steps

```
1. POS Android app → GET /api/v1/pos/inventory
   Header: X-API-Key=<device api key>
   • Backend resolve میکند: device → sales_channel → dealer → inventory_location
   • returns: list of bars where:
       - current_location_id = <dealer's inventory_location>
       - status IN ('ASSIGNED', 'RAW')
   • هر bar شامل: serial_code, weight_mg, purity, product_name, product_id
       + price preview (محاسبهشده توسط Pricing با channel formula)

2. نماینده / کاربر یک bar را از لیست انتخاب میکند، می‌رود به مرحله پرداخت

3. POS app → POST /api/v1/pos/reserve
   Body: { bar_id, customer_mobile }
   • Backend:
     - validate: bar در dealer's location، status قابل reserve
     - Pricing.create_price_lock(channel, bar.product_id)
     - **D-101:** زیر `pg_advisory_xact_lock(hashtext('treasury:'||metal_type))`:
       - plain SELECT از `treasury_settings` (نه SELECT FOR UPDATE)
       - enforce `committed + reserved + this_tx ≤ cap`
       - INSERT `inventory_pending_holds` (با `expires_at` per [D-105](../01-decisions-audit-log.md)) — نه فقط bar.status=RESERVED
     - bar.status = RESERVED, reserved_until = +N min
     - returns: reservation_id, amount_rial, price_lock_id

4. کارتکشی روی POS hardware (TalaMala terminal — payment_account اختصاصی)

5. POS app → POST /api/v1/pos/confirm
   Body: { reservation_id, trace_number, rrn, amount_rial, paid_at, request_id }  # D-99: optional request_id for idempotency
   • Backend در DB transaction:
     - **D-99:** اگر `request_id` ارائه شده:
       - **INSERT/SELECT** `pos_pending_requests` با idempotency key = `(dealer_id, pos_session_id, request_id)`
       - اگر قبلا موجود: از `server_confirmed_at` return کن (idempotent)
     - INSERT pos_transactions (با terminal_id, trace_number, rrn)
     - Order.create(
         order_type=pos_sale, status=Paid,
         brand=<channel.brand>, payment_receiver=<channel.payment_account.company>
       )
     - INSERT order_items (با pure_gold_mg, buyback_credit_rial snapshot — D-32)
     - Inventory.consume(bar) → customer_id=resolved_user_id
     - **D-101:** finalize `inventory_pending_holds` row → `treasury_position` (source=pos_sale, delta=+pure_gold_mg); global lock order: advisory(treasury per metal) → wallet rows → bar  # D-91: pure weight
     - چون POS برای TalaMala است → payment_receiver=TalaMala:
       INSERT inter_company_ledger × 2 (rial + gold per بخش ۶.۴)
     - DealerSale (commission for dealer به‌صورت Gold-for-Gold)
     - **D-99:** UPDATE `pos_pending_requests` SET request_state='server_confirmed', server_confirmed_at=now()
     - Audit + Outbox + Notification

6. on fail (cancel یا timeout):
   - POST /api/v1/pos/cancel { reservation_id }
   - bar.status = ASSIGNED (release)
   - PriceLock cancel
```

## 6. DB Writes

- `pos_transactions` — trace_number, rrn, amount from card terminal
- `pos_pending_requests` — idempotency tracking for offline queue ([D-99](../01-decisions-audit-log.md))
- `orders` — order_type=pos_sale, status=Paid
- `order_items` — with price + buyback snapshots
- `bars` — status: RESERVED → SOLD, customer_id set
- `dealer_sales` — commission record (Gold-for-Gold)

> Canonical schemas: [Order](../03-schema-index.md#11-order), [Inventory](../03-schema-index.md#10-inventory), [POS](../03-schema-index.md#15-pos-devices--transactions), [Supplementary (dealer_sales, pos_pending_requests)](../03-schema-index.md#14-supplementary)

## 7. Treasury Impact

- `treasury_positions` += `pure_gold_mg` (source=pos_sale)
- Sign: **positive** (open exposure)
- Same as [Flow 01](01-physical-bar-purchase-site.md)

## 8. Wallet Impact

- No direct wallet impact (customer pays via card terminal)
- Dealer commission is tracked in `dealer_sales` / `dealer_commission_ledger` — settled separately via [Flow 15](15-dealer-commission-settlement.md)

## 9. Inter-Company Impact

Same logic as [Flow 01](01-physical-bar-purchase-site.md):
- If payment_receiver ≠ Goldis (e.g., TalaMala POS): 2 entries (rial + gold)
- If payment_receiver == Goldis (Goldis POS): no inter-company entries

> [D-56](../01-decisions-audit-log.md): POS channel determines payment_receiver from channel config.

## 10. Audit & Events

- `outbox_events`:
  - `PosTransactionImported`, `PosOrderCreated`
  - `OrderPaid`, `TreasuryPositionOpened`
  - `InterCompanyObligationCreated` (if non-Goldis)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Card payment fails | POS app calls `/pos/cancel` → release reservation |
| Reservation timeout (N min) | Expiry worker releases bar |
| Network failure during confirm | [D-99](../01-decisions-audit-log.md): offline queue — POS retries with same request_id (idempotent) |
| Bar already reserved/sold | Reject reserve attempt |
| Treasury cap exceeded | [D-101](../01-decisions-audit-log.md): two-level cap check fails under advisory lock → reject reserve |

## 12. Invariants

- Bar is physically at dealer location — `current_location_id` must match dealer's location
- `pure_gold_mg = weight_mg × purity / 1000` — always pure weight ([D-91](../01-decisions-audit-log.md))
- Offline idempotency: `(dealer_id, pos_session_id, request_id)` is unique key ([D-99](../01-decisions-audit-log.md))
- POS confirm is idempotent — duplicate calls with same request_id return cached result
- Buyback snapshot (D-32) taken at POS sale time, same as website purchase

## 13. Related References

- [Flow 01 — Physical Bar Purchase](01-physical-bar-purchase-site.md) (website variant)
- [Domain Models — POS](../02-domain-models.md#۹-pos-as-first-class-sales-channel)
- [Schema: POS](../03-schema-index.md#15-pos-devices--transactions) | [Supplementary (dealer_sales)](../03-schema-index.md#14-supplementary)
- [API: POS](../04-api-index.md)
- [Reference: Commercial/Pricing](../references/commercial-pricing-orders.md)
- Decisions: [D-32](../01-decisions-audit-log.md), [D-47](../01-decisions-audit-log.md), [D-56](../01-decisions-audit-log.md), [D-91](../01-decisions-audit-log.md), [D-99](../01-decisions-audit-log.md), [D-101](../01-decisions-audit-log.md), [D-105](../01-decisions-audit-log.md)
