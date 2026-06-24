# Goldis Hub — Architecture Documentation

> **Version:** 2.7 (Implementation-ready — 2026-05-18)
> **Source:** `goldis-hub-architecture-v2.7.md` (3599-line monolith → structured DDD split)

---

## Navigation

### Root Documents

| File | Content |
|---|---|
| [00-overview.md](00-overview.md) | Project summary, scope, companies/brands, migration plan, roadmap, LLM instructions |
| [01-decisions-audit-log.md](01-decisions-audit-log.md) | All architectural decisions D-01…D-110 (incl. §2.7 Pre-Build Review D-100…D-110 — authoritative/override), P0 fixes, FIX-1…7, ambiguity resolution |
| [02-domain-models.md](02-domain-models.md) | Bounded contexts, domain concepts, Companies/Brands/Channels narrative, Wallet/Treasury/Inter-Company concepts |
| [03-schema-index.md](03-schema-index.md) | All SQL schemas (canonical home — other files reference here) |
| [04-api-index.md](04-api-index.md) | Complete API contracts & conventions |
| [05-security-audit-events.md](05-security-audit-events.md) | Authentication, authorization, compliance, audit events |

### End-to-End Flows (`flows/`)

Each file follows a strict 13-section template (Goal → Actors → Preconditions → Trigger → Steps → DB writes → Treasury → Wallet → Inter-company → Audit → Failures → Invariants → References).

| # | Flow | Source |
|---|---|---|
| [01](flows/01-physical-bar-purchase-site.md) | Physical Bar Purchase (Site) | §12.1 |
| [02](flows/02-digital-gold-buy.md) | Digital Gold Buy (AminZar + TalaMala) | §12.2 + §12.3 |
| [03](flows/03-digital-gold-sell.md) | Digital Gold Sell | §12.4 |
| [04](flows/04-physical-purchase-from-wallet.md) | Physical Purchase from Wallet | §12.5.1 |
| [05](flows/05-buyback-undelivered.md) | Buyback — Undelivered (Online, Automatic) | §12.5.2(a) |
| [06](flows/06-buyback-in-person.md) | Buyback — In-Person (State Machine) | §12.5.2(b) |
| [07](flows/07-pos-sale.md) | POS Sale | §12.7 |
| [08](flows/08-marketplace-sale.md) | Marketplace Sale (DigiKala) | §12.8 |
| [09](flows/09-rial-wallet-topup.md) | Rial Wallet Topup | §12.5.4 |
| [10](flows/10-rial-withdrawal.md) | Rial Withdrawal | §12.6 |
| [11](flows/11-hedge-buy-and-bulk-gold-intake.md) | Hedge Buy & Bulk Gold Intake | §12.5.3 + D-82/D-83 |
| [12](flows/12-inter-company-settlement.md) | Inter-Company Settlement | §12.9 + §6.5 |
| [13](flows/13-inventory-transfer.md) | Inventory Transfer (Two-Stage) | D-62 + D-93 |
| [14](flows/14-fulfillment-delivery.md) | Fulfillment & Delivery | §8 + D-77/D-78/D-79/D-80 |
| [15](flows/15-dealer-commission-settlement.md) | Dealer Commission Settlement | D-73 + D-84 + §20.5 |

### Reference Documents (`references/`)

Canonical home for shared domain logic referenced by multiple flows.

| File | Content |
|---|---|
| [finance-wallet-treasury-ledger.md](references/finance-wallet-treasury-ledger.md) | Wallet model (D-46), Treasury (D-47), Inter-Company Ledger (§6), sign conventions, cap/alert, settle operations |
| [commercial-pricing-orders.md](references/commercial-pricing-orders.md) | Pricing ladder (D-65), spread (D-72), POS model, order types, gift box (D-75), critical subsystems D-96/D-98 |
| [inventory-bars-warehouse.md](references/inventory-bars-warehouse.md) | Bar lifecycle, production cycle (§7), custodial model (D-49), ownership transfer (D-55), bulk gold (D-83), pending reserves (D-97) |
| [identity-kyc-users.md](references/identity-kyc-users.md) | User model, KYC levels (D-61), Shahkar, bank account verification (D-64), limits |
| [outbox-workers-realtime.md](references/outbox-workers-realtime.md) | Outbox pattern, event list, subscriber registry, workers/scheduler (§15), SSE (§16), POS offline queue (D-99) |
| [testing-strategy.md](references/testing-strategy.md) | Unit/integration/concurrency/outbox tests, CI pipeline |

---

## How to Use

1. **New to the project?** Start with [00-overview.md](00-overview.md).
2. **Implementing a feature?** Find the matching flow in `flows/` — it's your primary guide.
3. **Need a schema?** All SQL lives in [03-schema-index.md](03-schema-index.md).
4. **Need decision context?** Check [01-decisions-audit-log.md](01-decisions-audit-log.md) for the "why".
5. **Cross-cutting concern?** Check `references/` for shared domain logic.

## DRY Principle

- Schemas appear **only** in `03-schema-index.md`.
- Decisions appear **only** in `01-decisions-audit-log.md`.
- Flow files **reference** both via markdown links — they never duplicate.
- Reference files hold **canonical** shared logic — flows link to them.

## Source Document

The original monolithic document is preserved at:
`goldis-hub-architecture-v2.7.md` (3599 lines, v2.7, 2026-05-18)
