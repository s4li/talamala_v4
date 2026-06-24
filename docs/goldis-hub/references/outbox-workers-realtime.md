# Reference — Outbox Pattern, Workers & Realtime

> Cross-cutting reference for the outbox event pattern, background workers/scheduler,
> and the SSE realtime broadcast system.

> **DRY rule:** No SQL here. Canonical schemas → [Schema Index](../03-schema-index.md).
> Decision rationale → [Decisions](../01-decisions-audit-log.md).

---

## ۱. Outbox Pattern

### ۱.۱. اصل

هر transaction که داده حساس را تغییر می‌دهد → `outbox_events` entry در **همان transaction**. publisher worker جدا follow میکند.

### ۱.۲. Outbox Table Structure

- `event_type`: e.g. `OrderPaid`, `TreasuryPositionOpened`
- `aggregate_type` + `aggregate_id`: source entity
- `company_id` / `brand_id` / `channel_id`: multi-company context
- `payload`: JSONB event data
- `status`: pending → published | failed
- `retry_count` + `next_retry_at`: exponential backoff

### ۱.۳. Publisher Worker

```
outbox_publisher (continuous, poll 1s, parallelism=2):
  SELECT * FROM outbox_events WHERE status='pending' ORDER BY created_at LIMIT N FOR UPDATE SKIP LOCKED
  for each event:
    dispatch to EVENT_HANDLERS[event.event_type]
    UPDATE status='published', published_at=now()
    on error: retry_count++, next_retry_at=exponential_backoff
```

### ۱.۴. Subscriber Registry (in-process فاز ۱)

```python
EVENT_HANDLERS: dict[str, list[Callable]] = {
    "OrderPaid": [
        notification_service.handle_order_paid,
        accounting_service.handle_order_paid,
        realtime_broadcaster.broadcast_user_order,
    ],
    "TreasuryThresholdReached": [
        notification_service.alert_admins,
    ],
    # ...
}
```

### ۱.۵. Idempotency Guarantee

- Publisher checks: `outbox_events.status != 'published'` before dispatch
- Each handler must be idempotent (safe to re-execute)
- `FOR UPDATE SKIP LOCKED` prevents double-processing in parallel

> Canonical schemas: [Outbox + Audit](../03-schema-index.md#13-outbox--audit)

---

## ۲. Event Catalog

### ۲.۱. Full Event List

**Identity / KYC:**
- `UserRegistered`, `UserKycSubmitted`, `UserKycApproved`, `UserKycRejected`, `UserLevelChanged`

**Pricing:**
- `PriceSourceFetched`, `PriceSourceFailed`, `InternalBasePriceChanged`
- `PriceLockCreated`, `PriceLockExpired`

**Inventory:**
- `InventoryReserved`, `InventoryReleased`, `InventoryConsumed`, `InventoryTransferred`

**Order:**
- `OrderCreated`, `OrderPaid`, `OrderReservationExpired`

**Payment:**
- `PaymentStarted`, `PaymentVerified`, `PaymentFailed`

**POS:**
- `PosTransactionImported`, `PosOrderCreated`

**Wallet:**
- `WalletCredited`, `WalletDebited`, `WalletLocked`, `WalletUnlocked`
- `WalletToppedUp`, `WalletTopupFailed`

**Trade:**
- `DigitalGoldBought`, `DigitalGoldSold`

**Buyback:**
- `BuybackCompleted` (تحویل‌نشده — آنلاین)
- `PhysicalBuybackRequested`, `PhysicalBuybackReceived`, `PhysicalBuybackVerified`
- `PhysicalBuybackApproved`, `PhysicalBuybackCompleted`, `PhysicalBuybackRejected`

**Withdrawal:**
- `WithdrawalRequested`, `WithdrawalApproved`, `WithdrawalRejected`
- `WithdrawalCompleted`, `WithdrawalFailed`

**Treasury:**
- `TreasuryPositionOpened`, `TreasuryPositionCancelled`, `TreasuryThresholdReached`

**Inter-Company Ledger:**
- `InterCompanyObligationCreated` (موقع sale — gold + rial)
- `InterCompanyRialSettled`, `InterCompanyGoldSettled` (تأیید settle)
- `InterCompanyObligationCorrected` (admin correction — buyback does NOT reverse)

**Fulfillment:**
- `FulfillmentTaskCreated`, `FulfillmentTaskAssigned`, `FulfillmentTaskCompleted`
- `FulfillmentPicked`, `FulfillmentPacked`, `FulfillmentHandedOver`, `FulfillmentDelivered`
- Exception: `FulfillmentDeliveryFailed`, `FulfillmentLostInTransit`, `FulfillmentDamaged`

**Inventory Transfer:**
- `InventoryTransferCreated`, `InventoryTransferDispatched`
- `InventoryTransferReceived`, `InventoryTransferCompleted`
- `InventoryTransferDiscrepancy`

**Marketplace:**
- `ExternalOrderFetched`, `ExternalOrderImported`, `ExternalOrderFailed`
- `ChannelInventoryPushed`, `ChannelPricePushed`

**Notification:**
- `NotificationDispatched`, `NotificationFailed`

**Hedge Buy:**
- `HedgeBuyRecorded`, `TreasuryPositionUpdated`, `BulkGoldIntake`

**Dealer Commission:**
- `DealerCommissionRecorded`, `DealerCommissionSettled`

**Audit:**
- `AuditEntryCreated`

> Full event documentation: [Security & Audit Events](../05-security-audit-events.md)

---

## ۳. Background Workers

### ۳.۱. Worker Architecture

- **Library:** APScheduler + asyncio (نه Celery، نه Arq)
- **Reason:** تک‌سرور، تیم کوچک، حداقل dependency
- **Deployment:** هر worker یک systemd unit مستقل: `talamala-workers.service` → `python -m app.workers`

### ۳.۲. Worker Registry

| Worker | Frequency | Config | Description |
|--------|-----------|--------|-------------|
| `outbox_publisher` | continuous (poll 1s) | parallelism=2 | Dispatch outbox events to handlers |
| `pricing_fetcher` | dynamic per source | configurable | Fetch market prices from external sources |
| `marketplace_poller` | 60s | per channel | Pull new orders from DigiKala/Basalam |
| `lock_expirer` | 30s | — | Release expired price locks + inventory reservations + **inventory_pending_holds** ([D-105](../01-decisions-audit-log.md)) via state/version-guarded UPDATE (no blind delete) |
| `treasury_monitor` | 30s | — | Check treasury caps, send alerts ([D-47](../01-decisions-audit-log.md)) — back-up only; real gate is the inline check ([D-101](../01-decisions-audit-log.md)) |
| `reconciliation_worker` | per period (5–15m) | — | **Financial core** ([D-106](../01-decisions-audit-log.md)): recompute each balance/exposure from its ledger; assert the 3 self-reconciliation identities + the cross-ledger solvency identity; write a snapshot; raise an incident on any non-zero residue; drive the external 3-way reconcile (bank/gateway, physical bars, counterparty) |
| `notification_dispatcher` | continuous | parallelism=4 | Send SMS/push notifications |
| `payout_processor` | 30s | — | Process approved rial withdrawals |
| `pos_transaction_reconciler` | hourly | per channel | Reconcile POS transactions |
| `fulfillment_reminder` | hourly | — | Alert on stuck fulfillment tasks |

### ۳.۳. Supervisor Pattern

```python
async def main():
    workers = [
        OutboxPublisherWorker(),
        PricingFetcherWorker(),
        MarketplacePollerWorker(),
        LockExpirerWorker(),
        TreasuryMonitorWorker(),
        NotificationDispatcherWorker(),
        PayoutProcessorWorker(),
        ReconciliationWorker(),   # D-106: ledger/exposure/inter-company invariants + cross-ledger solvency identity
        # SettlementDailyWorker حذف شد (D-06b) — inter_company_ledger real-time
    ]
    tasks = [asyncio.create_task(w.loop()) for w in workers]
    await asyncio.gather(*tasks)
```

### ۳.۴. Removed Workers

- **SettlementDailyWorker** — حذف شد ([D-06](../01-decisions-audit-log.md)). Inter-company ledger real-time است، settle دستی.

---

## ۴. Realtime — SSE (Server-Sent Events)

### ۴.۱. Endpoint

- `GET /api/v1/realtime/stream` — SSE with JWT in query or cookie

### ۴.۲. Architecture

- In-process broadcaster that subscribes to outbox publisher
- Phase 1: single process, in-memory broadcast
- Phase 2 (multi-process): Redis Pub/Sub added

### ۴.۳. Topics

| Topic Pattern | Audience | Data |
|---------------|----------|------|
| `wallet.{user_id}.{wallet_scope}` | User | Balance changes |
| `order.{user_id}` | User | Order status changes |
| `pricing.channel.{channel_id}` | All | Price updates |
| `treasury.alert` | Admin only | Treasury threshold alerts |
| `fulfillment.task.{location_id}` | Warehouse | New/updated tasks |
| `settlement.alert` | Accountant only | Settlement alerts |

---

## ۵. Code Generation Rules (§22 — LLM Instructions)

### ۵.۱. Technical Rules

- Type hints کامل (mypy strict)
- SQLModel (Table) for DB, Pydantic (Create/Update/Read) for API — never expose Table directly
- async-first (SQLAlchemy 2.x async + asyncpg)
- Explicit transaction per service method
- `SELECT FOR UPDATE` for: wallet balance, bar reservation, treasury_settings
- `idempotency_key` in all mutating POSTs
- Repository pattern for DB, Service pattern for business logic
- Comments: English. Commit messages: English. UI/user messages: Persian.
- No business logic in route handlers — always in service
- **No float for money/gold/weight.** Integer for amount, Decimal for rate/coefficient.

### ۵.۲. Product Rules

- No financial logic without audit/ledger
- No balance change without LedgerEntry
- No treasury change without TreasuryPosition row
- No critical setting change without audit_logs
- Critical event → outbox in same transaction

### ۵.۳. Interaction Rules

- مرحله به مرحله (≤ 500 lines per step)
- هر مرحله: model + service + route + test + alembic migration
- Tests alongside code — not after
- Never code something whose spec is unclear

---

## ۶. Related References

- [Security & Audit Events](../05-security-audit-events.md) (canonical event list + audit rules)
- [Finance Reference](finance-wallet-treasury-ledger.md) (treasury alert worker context)
- [Inventory Reference](inventory-bars-warehouse.md) (lock_expirer, fulfillment_reminder context)
