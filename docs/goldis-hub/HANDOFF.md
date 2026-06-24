# Handoff Note — Goldis Hub Documentation Package

> **Date:** 2026-05-19
> **Status:** Ready for implementation

---

## Documentation Package is Ready for Coding

The Goldis Hub v2.7 architecture is fully captured in 28 structured DDD + End-to-End Flow files (the modular set under `docs/goldis-hub/`). All business logic, decisions (D-01..D-110, including the authoritative §2.7 Pre-Build Review decisions D-100..D-110 which override earlier ones), schemas, API contracts, and operational flows live here without summarization or omission.

## Source of Truth

- **The modular docs (`docs/goldis-hub/`: 00–05 + `flows/` + `references/`)** are the **single source of truth** for all implementation work.
- The original v2.7 monolith has been **removed** (content split and updated across the modular set; recoverable from git history).

## How to Use for Implementation

For any feature or flow, use these files together:

| Need | Go to |
|------|-------|
| End-to-end flow (steps, state machine, DB writes, treasury/wallet/inter-company impact) | `flows/01..15-*.md` |
| SQL schemas (CREATE TABLE, constraints, indexes) | `03-schema-index.md` |
| API contracts (endpoints, request/response) | `04-api-index.md` |
| Architectural decisions (D-01..D-110; §2.7 D-100..D-110 override earlier decisions) | `01-decisions-audit-log.md` |
| Domain concepts and bounded contexts | `02-domain-models.md` |
| Security, RBAC, events, outbox | `05-security-audit-events.md` |
| Cross-cutting deep-dives | `references/*.md` |

## File Inventory

### Root Files (6)
- `README.md` — Navigation index
- `00-overview.md` — Project overview + bounded contexts
- `01-decisions-audit-log.md` — All architectural decisions (D-01..D-110, incl. §2.7 Pre-Build Review D-100..D-110 which override earlier ones)
- `02-domain-models.md` — Domain concepts (no SQL — links to schema index)
- `03-schema-index.md` — Canonical SQL schemas (15 sections)
- `04-api-index.md` — API contracts and conventions
- `05-security-audit-events.md` — Security + Outbox events

### Flow Files (15) — `flows/`
| # | Flow | Source |
|---|------|--------|
| 01 | Physical Bar Purchase (Site) | §8 + D-49/D-90/D-91/D-92 |
| 02 | Digital Gold Buy | §4 + D-46/D-47 |
| 03 | Digital Gold Sell | §4 + D-46/D-47 |
| 04 | Physical Purchase from Wallet | §8 + D-31 |
| 05 | Buyback — Undelivered | §8 + D-32/D-58 |
| 06 | Buyback — In-Person | §8 + D-32/D-58 |
| 07 | POS Sale | §12.5 + D-93/D-94 |
| 08 | Marketplace Sale | §12.4 + D-56 |
| 09 | Rial Wallet Topup | §4 + D-63/D-96 |
| 10 | Rial Withdrawal | §4 + D-31/D-64 |
| 11 | Hedge Buy & Bulk Gold Intake | §12.5.3 + D-82 |
| 12 | Inter-Company Settlement | §6 + D-06b |
| 13 | Inventory Transfer (Two-Stage) | §11.9 + D-62 |
| 14 | Fulfillment & Delivery | §8 + D-77/D-78/D-79/D-80 |
| 15 | Dealer Commission Settlement | D-73 |

### Reference Files (6) — `references/`
| File | Scope |
|------|-------|
| `finance-wallet-treasury-ledger.md` | Wallet scopes, treasury sign convention, inter-company ledger, payment model, critical subsystems |
| `commercial-pricing-orders.md` | Price pipeline, 7 order types, buyback model, marketplace, dealer commission, production cycle |
| `inventory-bars-warehouse.md` | Bar lifecycle, locations, transfers, fulfillment, bulk gold, POS inventory |
| `identity-kyc-users.md` | User model, auth, RBAC+ABAC, KYC levels, Shahkar, dealer tiers, audit |
| `outbox-workers-realtime.md` | Outbox pattern, full event catalog, 9 workers, SSE realtime, code generation |
| `testing-strategy.md` | Unit/integration/concurrency tests, CI pipeline, 7-phase roadmap |

## DRY Rules Enforced

- **SQL schemas** exist ONLY in `03-schema-index.md` — flow and reference files link, never duplicate
- **Decisions** exist ONLY in `01-decisions-audit-log.md` — others reference via `[D-XX](../01-decisions-audit-log.md)`
- **Events** exist ONLY in `05-security-audit-events.md` — flows list event names, link for details

## Validation Results (2026-05-19)

| Check | Result |
|-------|--------|
| All markdown links point to existing files | PASS (0 broken) |
| All schema anchors match `03-schema-index.md` headings | PASS (8 fixed during audit) |
| No `CREATE TABLE` in reference files | PASS |
| No `CREATE TABLE` in flow files | PASS |
| All 15 flows have exactly 13 sections | PASS |

## Implementation Order (Suggested)

0. **Build-discipline harness (D-110)** — Alembic async+SQLModel with explicit per-column enum strategy (native PG enum via `alembic-postgresql-enum`, or `VARCHAR+CHECK` for reversible downgrade), `import-linter` enforcing the 24-context boundary (no Table model crosses; `payment` must not import `treasury` internals), commit/rollback only at the use-case boundary, `asyncpg statement_cache_size=0` if a transaction-mode pooler is used, `testcontainers` Postgres + concurrency/idempotency fixtures. No financial context ships before this harness.
1. **Platform + Identity + KYC** (foundations: users, companies, brands, channels)
2. **Catalog + Pricing + Inventory** (products, bars, locations, price pipeline)
3. **Wallet + Payment + Reconciliation/Solvency worker (D-106)** (double-entry ledger, atomic payment finalize; scheduled worker running the 3 self-reconciliations + cross-ledger solvency identity + treasury_position_snapshots + alert on any nonzero residue + external 3-way recon + blind cycle-count of custodial bars — part of the financial core, NOT a later phase)
4. **Cart + Orders + Fulfillment** (checkout, delivery, OTP confirmation)
5. **Treasury + Inter-Company Ledger** (hedging desk, multi-company settlement)
6. **POS + Marketplace** (dealer POS, external channel sync)
7. **Buyback + Withdrawal** (buyback flows, rial withdrawal)
8. **Dealer Commission** (Gold-for-Gold settlement)
9. **Outbox + Workers + Realtime** (event publishing, SSE)
10. **Reporting + Audit** (dashboards, admin tools)
