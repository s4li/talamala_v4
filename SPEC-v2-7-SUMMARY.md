# v2.7 Spec Summary — Critical Subsystems Implementation

**Date:** 2026-05-18  
**Status:** ✅ Ready for implementation & external review  
**Decisions Made:** All 4 critical gaps resolved with design + schema

---

## What Changed from v2.6 to v2.7

### The 4 Gemini-Found Critical Gaps → Solutions

| Gap | Issue | v2.7 Solution | Schema |
|-----|-------|---------------|--------|
| **D-90** | Price lock deadlock when price changes mid-checkout | Auto-reconcile ±2%, manual review >2%, treasury adjustment | `payment_reconciliations` table |
| **D-91** | Treasury race: concurrent orders can bypass exposure cap | Reserve (lock) gold on checkout, finalize on payment | `inventory_pending_holds` table |
| **D-92** | Orphaned payment: system crash after gateway OK but before ledger | State machine: `gateway_verified_pending` → async ledger creation + recovery job | `payments.payment_state` enum |
| **D-93** | POS offline: device goes offline after charge, before confirm | Local SQLite queue on device + server-side idempotency + manual recovery dashboard | `pos_pending_requests` table |

---

## Implementation Order (v2.7 → v1)

```
Phase 0: Infrastructure (existing)
├─ Database setup ✅
├─ Company/Brand/Channel models ✅
└─ Wallet (v2.7: scope-keyed, fully isolated) ✅

Phase 1-2: Core Commerce ✅
├─ Catalog, Product, Inventory
├─ Shop, Cart, Orders
├─ Payment (with new state machine from D-92)
└─ **ADD: Payment Reconciliation flow (D-90)**
     └─ Reconciliation table
     └─ ±2% auto-approve logic
     └─ Admin manual review dashboard

Phase 3: Treasury + Trade
├─ Treasury (with Pending Reserves from D-91)
├─ Wallet Trades
├─ Withdrawal (rial only)
├─ Buyback
├─ **ADD: Pending Holds checking**
│   └─ On checkout: reserve
│   └─ On payment: finalize
│   └─ On cancel: release

Phase 4: Dealer Network
├─ Dealer + Tier + Commission
├─ POS (with Offline Queue from D-93)
├─ DealerSale + Stats
├─ **ADD: Offline Queue handling**
│   └─ `pos_pending_requests` table
│   └─ Idempotency per device
│   └─ Manual recovery UI

[continue with existing phases...]
```

---

## New Endpoints (v2.7)

### Admin: Reconciliations
- `GET /admin/payments/reconciliations` — list pending reviews
- `POST /admin/payments/reconciliations/{id}/approve` — approve with optional adjustment
- `POST /admin/payments/reconciliations/{id}/reject` — reject, trigger buyback

### Admin: Payment Recovery (D-92)
- `GET /admin/payments/pending-states` — all non-finalized payments
- `POST /admin/payments/{id}/manual-recover` — trigger recovery

### Admin: POS Queue (D-93)
- `GET /admin/pos/queue` — all pending/failed requests
- `POST /admin/pos/queue/{id}/retry` — manual retry
- `POST /admin/pos/queue/{id}/discard` — discard (refund)
- `GET /admin/pos/queue/{dealer_id}/snapshots` — device queue snapshots

### POS API: Offline Confirm (updated from D-93)
- `POST /api/pos/confirm` — now has `request_id` + idempotency for offline retry

---

## New Database Tables

### payment_reconciliations
- id (UUID)
- payment_id (FK), order_id (FK)
- authorized_amount_rial, actual_price_at_payment_rial
- variance_rial, variance_percent
- reconciliation_status (pending | auto_approved | auto_adjusted | manual_review | rejected)
- treasury_adjustment_mg (for ±2% auto cases)
- reviewed_by (FK), reviewed_at, approved_at

### inventory_pending_holds
- id (UUID)
- order_id (FK), wallet_scope
- pure_gold_mg_reserved
- reserved_at, finalized_at, released_at
- Unique: (order_id) — one hold per order

### payments (updated schema)
- **New column:** `payment_state` VARCHAR(30)
  - Values: pending | gateway_verified_pending | inter_company_ledger_created | finalized | failed | cancelled
- **New column:** `idempotency_key` VARCHAR(100) UNIQUE — critical for recovery
- **New column:** `ledger_entry_id` (FK to inter_company_ledger)
- **New columns:** gateway_verified_at, finalized_at, failed_at, failure_reason

### pos_pending_requests
- id (UUID)
- dealer_id (FK), pos_session_id, request_id
- sale_data (JSONB), payment_ref
- request_state (received | processing | pos_confirmed | server_confirmed | failed)
- server_confirmed_at, error_reason, expires_at
- Unique: (dealer_id, pos_session_id, request_id)

### pos_device_queue_snapshots
- id (BIGSERIAL)
- dealer_id (FK), pos_session_id
- queue_snapshot (JSONB — array of pending requests from device)
- synced_at

---

## Key Decisions for Reviewers

✅ **D-90 (Price Lock):** Auto-reconcile ±2%, admin reviews >2%, no blind refunds  
✅ **D-91 (Treasury Race):** Pessimistic locking (reserve on checkout, finalize on payment)  
✅ **D-92 (Orphaned Payment):** State machine + async recovery job + idempotency key  
✅ **D-93 (POS Offline):** Local queue + server-side deduplication via request_id  

---

## Testing Checkpoints

After implementation, verify:

- [ ] Payment lock scenario: checkout @ 100T, price → 120T by payment time → auto-reconcile fires
- [ ] Treasury cap scenario: two concurrent 60kg checkouts → one succeeds, one fails (pending hold)
- [ ] Crash scenario: system crashes after gateway callback → recovery job replays on startup
- [ ] POS offline scenario: device charges, WiFi dies → stays in local queue, syncs later
- [ ] Manual reviews: admin can approve/reject reconciliations from dashboard

---

## For External Reviewers (Gemini → Claude)

**These are the architectural solutions to your 3 critical issues:**

1. ✅ **Price Lock**: D-90 payment reconciliation + treasury adjustment
2. ✅ **Treasury Race**: D-91 pending reserves + SELECT FOR UPDATE patterns
3. ✅ **Orphaned Payment**: D-92 state machine + recovery job + idempotency
4. ✅ **POS Offline (bonus)**: D-93 offline queue + client-side retry logic

**Please verify** that these solutions:
- Are architecturally sound (no hidden race conditions)
- Follow Iranian banking constraints (no blind refunds, async settling OK)
- Are implementable within 2-3 weeks as added features to existing codebase
- Don't break existing flows (backward compatible)

---

## Rollout Strategy

**v1 MVP:** All 4 subsystems included (not deferrable)  
**Why:** These are blockers for financial correctness, not polish features  

**v1.1 (future):** Enhanced analytics, batch reconciliation reports, offline device sync dashboard

---

**Generated:** 2026-05-18  
**Spec File:** talamala_v5_architecture_spec.md (v2.7)  
**Ready for:** Implementation phase, external review (Gemini/ChatGPT/DeepSeek confirmation)
