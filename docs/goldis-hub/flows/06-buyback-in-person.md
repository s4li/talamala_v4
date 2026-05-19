# Flow 06 — Buyback — In-Person (State Machine)

> **Source:** §12.5.2 حالت (b) — بازخرید حضوری (نیاز‌مند تأیید)
> Note: Original sale is NEVER reversed. Buyback is always an independent forward transaction.

---

## 1. Goal

Customer brings back a physically delivered bar (`delivered_at IS NOT NULL`) to an authorized buyback center. A multi-step state machine governs receipt, authenticity verification, approval, and wallet credit.

## 2. Actors

- **Customer** (owner of bar, bar physically in hand)
- **Buyback center staff** (receive + verify — separation of duties recommended)
- **Admin/operator** (final approval)
- **System** (wallet credit + treasury after approval)

## 3. Preconditions

- `bar.status == SOLD` and `bar.delivered_at IS NOT NULL` (bar physically delivered to customer)
- `bar.customer_id == current_user`
- `target_location.can_buyback == TRUE` (authorized center: Goldis warehouse or dealer with `is_buyback_center`)

## 4. Trigger

`POST /api/v1/buyback/physical/request` with `{ bar_id, target_location_id }`.

## 5. Steps

### State Machine

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

### Full Flow

```
1. User → POST /api/v1/buyback/physical/request
     { bar_id, target_location_id (مغازهی نماینده یا انبار) }
2. Validate:
   - bar.customer_id == current_user
   - bar.status == SOLD، delivered_at IS NOT NULL
   - target_location.can_buyback == TRUE
3. INSERT physical_buyback_request (status=PhysicalRequested, target_location_id)
4. کاربر شمش را به مرکز میبرد.
5. کارشناس → POST /api/v1/admin/buyback/physical/{id}/receive
   → status=PhysicalReceived
6. کارشناس بررسی میکند: سریال، اصالت، وزن، عیار
   POST /api/v1/admin/buyback/physical/{id}/verify [اگر OK] یا /reject
   → status=AuthenticityVerified | Rejected
7. کارشناس تأیید نهایی → POST /api/v1/admin/buyback/physical/{id}/approve
   → status=Approved
8. سیستم در DB transaction (فقط بعد از Approved):
   - old_sale_wallet_scope = bar.sale_wallet_scope          # snapshot BEFORE clearing
   - old_pure_gold_mg = original_order_item.pure_gold_mg    # snapshot BEFORE clearing
   - Wallet.credit(user, old_sale_wallet_scope, XAU_MG, old_pure_gold_mg)
   - اگر ثبت مالکیت+OTP تأیید شد: Wallet.credit(user, old_sale_wallet_scope, IRR, order_item.buyback_credit_rial)
   - # فقط بعد از wallet credit و audit:
   - bar.status = ASSIGNED, customer_id = NULL, delivered_at = NULL, sale_wallet_scope = NULL  (D-92: ready for resale in any scope)
   - bar.current_location_id = target_location_id  (location تغییر میکند)
   - INSERT inventory_movement (type=transfer_in, to=target_location)
   - Treasury: دو پای متقابل ⇒ خالص ≈ صفر (physical→digital)
   - فروش اصلی reverse نمی‌شود (تراکنش بازخرید مستقل)
   - status=WalletCredited → Completed
   - Audit log + Outbox: PhysicalBuybackCompleted + Notification
```

## 6. DB Writes

- `physical_buyback_requests` — new row, status transitions through state machine
- `bars` — status: SOLD → ASSIGNED, customer_id = NULL, delivered_at = NULL, sale_wallet_scope = NULL, current_location_id updated
- `inventory_movements` — transfer_in to target_location
- `wallet_ledger_entries` — credit XAU_MG (always) + credit IRR (conditional)
- `asset_balances` — user's balances increased

> Canonical schemas: [Order (physical_buyback_requests)](../03-schema-index.md#11-order), [Inventory](../03-schema-index.md#10-inventory), [Wallet](../03-schema-index.md#2-wallet)

## 7. Treasury Impact

Two counterbalancing legs → **net ≈ zero** (same as [Flow 05](05-buyback-undelivered.md)):
- Leg 1: +pure_gold_mg (gold to wallet)
- Leg 2: −pure_gold_mg (physical bar returned)
- Physical↔digital conversion: treasury neutral

## 8. Wallet Impact

- XAU_MG: +pure_gold_mg (always, from `order_item.pure_gold_mg`)
- IRR: +buyback_credit_rial (conditional — only if ownership verified + OTP)
- Both credits go to `bars.sale_wallet_scope` (scope of original sale)
- Wage + tax + profit from original sale is **burned**
- ⚠️ Wallet MUST NOT be credited before `AuthenticityVerified`

## 9. Inter-Company Impact

**No new inter-company entries** for buyback (same as [Flow 05](05-buyback-undelivered.md)). Only `buyback_credit_rial` is a rial cost.

## 10. Audit & Events

- `audit_logs`: **mandatory at every state transition** (receive, verify, approve, reject)
- `outbox_events`:
  - `PhysicalBuybackRequested`, `PhysicalBuybackReceived`, `PhysicalBuybackVerified`
  - `PhysicalBuybackApproved`, `PhysicalBuybackCompleted` OR `PhysicalBuybackRejected`
  - `WalletCredited`

> Canonical event list: [Events](../05-security-audit-events.md)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Bar not delivered (delivered_at IS NULL) | Reject — use [Flow 05](05-buyback-undelivered.md) instead |
| Target location not authorized | Reject (can_buyback != TRUE) |
| Authenticity check fails | → Rejected with reason |
| Weight/purity mismatch | → Rejected with reason |
| Bar not owned by requesting user | Reject (403) |

## 12. Invariants

- Original sale NEVER reversed — buyback is independent forward transaction
- Wallet credit only AFTER `AuthenticityVerified` — never before
- Separation of duties: receive ≠ verify (or at minimum, audited)
- `buyback_credit_rial` is immutable snapshot from purchase time ([D-32](../01-decisions-audit-log.md))
- Bar returns to ASSIGNED with `sale_wallet_scope = NULL` → resaleable in any scope ([D-92](../01-decisions-audit-log.md))
- Dealer commission for buyback only recorded after `AuthenticityVerified` ([D-73](../01-decisions-audit-log.md) بند۷)
- Treasury net ≈ zero, no inter-company obligations

## 13. Related References

- [Flow 05 — Buyback Undelivered](05-buyback-undelivered.md) (automatic variant for custodial bars)
- [Flow 03 — Digital Gold Sell](03-digital-gold-sell.md) (for «بازخرید دیجیتال» — [D-68](../01-decisions-audit-log.md))
- [Schema: Order (physical_buyback_requests)](../03-schema-index.md#11-order) | [Inventory](../03-schema-index.md#10-inventory)
- [API: Buyback](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-32](../01-decisions-audit-log.md), [D-58](../01-decisions-audit-log.md), [D-73](../01-decisions-audit-log.md), [D-92](../01-decisions-audit-log.md)
