# Reference — Testing Strategy

> Cross-cutting reference for the testing approach, test categories,
> concurrency testing, CI pipeline, and implementation roadmap.

> **DRY rule:** No SQL here. Canonical schemas → [Schema Index](../03-schema-index.md).
> Decision rationale → [Decisions](../01-decisions-audit-log.md).

---

## ۱. Testing Philosophy

- **Tests alongside code** — not after. هر مرحله شامل: model + service + route + test + migration.
- **Concurrency-first:** Financial operations (wallet, inventory, treasury) must be tested under concurrent load.
- **Idempotency-first:** Payment callbacks, outbox publisher, and settle operations must be safe to re-execute.
- **No mocks for financial paths:** Integration tests against real Postgres (testcontainers).

---

## ۲. Unit Tests (pytest)

### ۲.۱. Pricing

- Pricing formula calculation for all rounding policies (`floor`, `round_half_up`, `ceiling`, `bankers`)
- Price ladder resolution: P0 → P_hedge → P_partner → P_retail
- Channel formula priority resolution (specific > general)
- Buy/sell spread calculation ([D-72](../01-decisions-audit-log.md))
- Price lock TTL validation (60s..300s range — [D-50](../01-decisions-audit-log.md))

### ۲.۲. Wallet

- Credit / debit / lock / release operations
- Balance calculation: `available = max(0, balance + credit_limit - locked)`
- Withdrawable balance: `balance - locked - credit`
- Credit limit enforcement (DB CHECK constraint)
- Scope isolation: operations on goldis wallet cannot affect talamala wallet ([D-46](../01-decisions-audit-log.md))

### ۲.۳. KYC

- Limit checks per user level
- Per-user override vs default behavior
- Gold outflow limit (combines physical_purchase + digital_sell — [D-31](../01-decisions-audit-log.md))

### ۲.۴. Treasury

- Sign convention: positive for sales, negative for hedge_buy; exposure = SUM(open signed delta) — no coverage ([D-100](../01-decisions-audit-log.md))
- Bidirectional cap check ([D-47](../01-decisions-audit-log.md)); canonical formula `committed + reserved + this_tx` within caps; advisory-lock serialization ([D-101](../01-decisions-audit-log.md))
- Dual-leg transactions (buyback, physical_purchase_from_wallet) net to **exactly 0 mg** — every leg derives from the SAME FLOOR-rounded integer ([D-104](../01-decisions-audit-log.md))
- `inventory_pending_holds` expire and are excluded from the reserved-sum once expired ([D-105](../01-decisions-audit-log.md))

### ۲.۵. Buyback

- Buyback credit calculation from snapshot
- Forward transaction (never reverse original sale — [D-58](../01-decisions-audit-log.md))
- Scope restriction: online buyback only in same scope ([D-71](../01-decisions-audit-log.md))

---

## ۳. Integration Tests (pytest + testcontainers Postgres)

### ۳.۱. Order Lifecycles

| Lifecycle | Flow |
|-----------|------|
| Purchase (physical) | cart → checkout → payment → inventory consume → treasury → inter-company → fulfill |
| Digital trade (buy) | wallet lock → payment → wallet credit (XAU_MG) → treasury → inter-company |
| Digital trade (sell) | wallet lock (XAU_MG) → consume → wallet credit (IRR) → treasury → inter-company |
| Physical from wallet | wallet lock (XAU_MG + IRR) → gateway → consume all → treasury (dual-leg) → inter-company |
| Buyback undelivered | validate → wallet credit (XAU_MG + IRR) → bar reset → treasury (dual-leg, net ≈ 0) |
| Buyback physical | state machine: request → receive → verify → approve → credit → complete |
| POS sale | reserve → card payment → confirm → inventory consume → dealer_sale → commission |
| Rial withdrawal | request → operator approve → payout → wallet consume → complete |

### ۳.۲. Payment

- Payment callback idempotency (same callback twice → same result)
- Payment state machine recovery ([D-92](../01-decisions-audit-log.md)): crash after gateway verify, before ledger
- Price lock expiry during payment ([D-96](../01-decisions-audit-log.md)): reconciliation flow
- Split payment (gold + rial wallet + gateway): all-or-nothing

### ۳.۳. Inventory

- Reserve / consume / release cycle
- Two-stage transfer ([D-62](../01-decisions-audit-log.md)): DRAFT → DISPATCHED → RECEIVED → COMPLETED
- Transfer with discrepancy handling
- Fulfillment state machine: pending → picking → packed → handed_over → delivered
- Bar status transitions: all valid and invalid paths
- Preorder lifecycle: preorder → in_stock (factory delivery)

### ۳.۴. Settlement & Reconciliation

- Inter-company **net** running account ([D-102](../01-decisions-audit-log.md)): settle appends an opposite-direction row → net → 0; NO FIFO / status / row-mutation
- Opposite-direction obligations (digital buy↔sell, buyback, commission offset) **auto-net to zero** — no second independent obligation lingers
- Dealer commission settlement + treasury offset auto-nets in the inter-company balance ([D-84](../01-decisions-audit-log.md)/[D-102](../01-decisions-audit-log.md))
- **Reconciliation worker** ([D-106](../01-decisions-audit-log.md)): `balance == Σ ledger`, `open exposure == Σ signed delta`, `inter-company outstanding == NET`; the cross-ledger solvency identity holds; **zero residue** after a randomized transaction storm

### ۳.۵. Marketplace

- Duplicate prevention (dedup_key UniqueViolation → skip)
- External order import → internal order creation
- D-56 enforcement: marketplace always Goldis-side

---

## ۴. Concurrency Tests (asyncio.gather)

### ۴.۱. Critical Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| N tasks همزمان روی wallet یک کاربر | Only one succeeds if insufficient balance; no double-spend |
| N tasks همزمان روی reserve یک bar | Only one succeeds; others get reservation conflict |
| N callbacks همزمان روی یک payment | Idempotent — all return same result, side effects once only |
| 2 checkouts that together exceed treasury cap | At most one succeeds — advisory-lock serializes the cap check ([D-97](../01-decisions-audit-log.md)/[D-101](../01-decisions-audit-log.md)) |
| Concurrent price lock creation + expiry | Lock expirer doesn't expire locks in active use |
| Double gateway callback on one payment | Credited exactly once; callback dedup on (gateway, ref) |
| Abandoned checkout hold + lock_expirer | Expired hold leaves the reserved-sum; cap recovers ([D-105](../01-decisions-audit-log.md)) |
| Randomized transaction storm then reconcile | Reconciliation worker reports **0 drift** on all invariants ([D-106](../01-decisions-audit-log.md)) |

### ۴.۲. Implementation Pattern

```python
async def test_wallet_double_spend():
    # Setup: user with 1000mg XAU_MG
    tasks = [
        wallet_service.debit(user_id, scope, XAU_MG, 800)
        for _ in range(3)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = [r for r in results if not isinstance(r, Exception)]
    assert len(successes) == 1  # exactly one succeeds
    # Verify: balance = 200mg, not negative
```

---

## ۵. Outbox Tests

- Event is stored in same transaction as data change (atomicity)
- Publisher does NOT double-publish (idempotency)
- Failed handler → retry with exponential backoff
- `FOR UPDATE SKIP LOCKED` prevents parallel processing of same event

---

## ۶. CI Pipeline

### ۶.۱. Tools

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner |
| `mypy` (strict) | Type checking |
| `ruff` | Linting |
| `black` | Code formatting |

### ۶.۲. Database

- Alembic up/down test: verify all migrations are reversible
- `testcontainers` Postgres: real DB for integration tests (no SQLite)

### ۶.۳. Pipeline Steps

```
1. ruff check → lint errors
2. black --check → format errors
3. mypy --strict → type errors
4. pytest --cov → unit + integration + concurrency tests
5. alembic upgrade head + alembic downgrade base → migration reversibility
```

---

## ۷. Implementation Roadmap

> ⚠️ **بازبینی پیش از ساخت (D-100…D-110) این roadmap را بازچینش می‌کند:**
> - **فاز ۰ harness قبل از هر کد مالی اجباری است** ([D-110](../01-decisions-audit-log.md)).
> - **فاز ۰.۵ (ویرایش سند، نه کد):** اعمال D-100…D-108 روی schema/flow + **D-109 بسته شد** (Rasis کاملاً حذف؛ POS greenfield).
> - **زنجیره‌ی مالی نو را جلو بیندازید:** wallet ledger → treasury (signed-sum) → inter-company (net) → outbox در یک finalize اتمیک، اول به‌صورت پروتوتایپ عمودی با تست‌های پولی+concurrency — نه آخر.
> - **reconciliation worker ([D-106](../01-decisions-audit-log.md)) جزء هسته‌ی مالی است (فاز ۳، نه ۶).**
> - تخمین هفته‌ایِ زیر **خوش‌بینانه است** (هشدار P۵)؛ به‌عنوان ترتیب نسبی بخوانید، نه تقویم قطعی.

### فاز ۰ — Infrastructure + Build-discipline harness ([D-110](../01-decisions-audit-log.md))
1. Project structure (`app/contexts/<name>/...`) + **import-linter** context-boundary contracts
2. Database setup + Alembic (async) + **enum strategy decided per column** (native enum via `alembic-postgresql-enum`, or `VARCHAR+CHECK`) — downgrade must stay reversible
3. Authentication + JWT + middleware; commit/rollback ONLY at the use-case boundary
4. Platform context (Companies/Brands/Channels)
5. Outbox infra + Audit log infra
6. Testing infra (pytest fixtures, testcontainers, factories) + **concurrency/idempotency fixtures** (the money-safety harness)

### فاز ۱ — Core Domain (هفته ۲-۳)
7. Identity (User, Session, JWT)
8. KYC (with Shahkar stub)
9. Catalog
10. Pricing (Source + Config + Internal Base + Channel Formula + PriceLock)
11. Wallet (multi-asset ledger — [D-46](../01-decisions-audit-log.md): isolated scopes)

### فاز ۲ — Transactional (هفته ۴-۵)
12. Inventory
13. Cart
14. Order (purchase only)
15. Payment (Zibal + Sepehr)
16. Fulfillment

### فاز ۳ — Treasury + Trade + Settlement (هفته ۶-۷)
17. Treasury basic (record + read)
18. Wallet trades (digital_trade buy/sell)
19. Withdrawal rial only ([D-31](../01-decisions-audit-log.md))
20. Physical purchase from wallet
21. Buyback (a: undelivered, b: physical)
22. Hedge Buy + bulk_gold_inventory
23. Inter-Company Ledger — signed **NET** running account ([D-06](../01-decisions-audit-log.md)/[D-102](../01-decisions-audit-log.md))
24. Treasury alert worker
    + **Reconciliation + solvency-invariant worker** ([D-106](../01-decisions-audit-log.md)) — financial core, NOT phase 6

### فاز ۴ — Dealer Network (هفته ۸-۹)
> ✅ **D-109 بسته شد:** Rasis کاملاً حذف شد — POS این فاز کاملاً **greenfield** است (فقط اپِ `talamala_pos` — [D-44](../01-decisions-audit-log.md)/[D-109](../01-decisions-audit-log.md))؛ دیگر gate ندارد.
25. Dealer + Tier + Commission rates/ledger ([D-73](../01-decisions-audit-log.md))
26. POS context
27. POS reserve→confirm flow
28. DealerSale + commission
29. Commission settlement + treasury offset ([D-84](../01-decisions-audit-log.md))

### فاز ۵ — Marketplace (هفته ۱۰)
30. Adapter interface + DigiKala adapter ([D-56](../01-decisions-audit-log.md))
31. Marketplace poller worker

### فاز ۶ — Realtime & Polish (هفته ۱۱)
32. SSE endpoint + broadcaster
33. Notification preferences
34. Admin reporting + Audit viewer

### فاز ۷ — Launch (هفته ۱۲)
35. Staging smoke testing
36. Production deployment + DNS switch
37. (Optional) import-bars-from-csv admin tool

> **Migration:** Fresh start ([D-23](../01-decisions-audit-log.md)) — no v4 data migration.
> POS Android app: not yet in production ([D-44](../01-decisions-audit-log.md)) — no backward compatibility needed.

---

## ۸. Related References

- [Security & Audit Events](../05-security-audit-events.md)
- [Finance Reference](finance-wallet-treasury-ledger.md) (wallet, treasury, payment tests)
- [Commercial Reference](commercial-pricing-orders.md) (pricing, order, buyback tests)
- [Inventory Reference](inventory-bars-warehouse.md) (bar, transfer, fulfillment tests)
- [Outbox & Workers Reference](outbox-workers-realtime.md) (outbox, worker tests)
