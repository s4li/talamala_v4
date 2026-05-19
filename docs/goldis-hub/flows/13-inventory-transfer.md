# Flow 13 — Inventory Transfer (Two-Stage)

> **Source:** D-62 + §11.9 + §13 — انتقال بین‌انبار دو‌مرحله‌ای (WMS/ERP pattern)
> Note: This is for **internal transfers between warehouses** (no customer involved). Customer-related movement goes through [Flow 14 (Fulfillment)](14-fulfillment-delivery.md) — [D-80](../01-decisions-audit-log.md).

---

## 1. Goal

Transfer serialized bars between inventory locations using a two-stage document flow with mandatory barcode scanning, OTP verification, and separation of duties (sender ≠ receiver).

## 2. Actors

- **Source warehouse operator** (creates document, dispatches bars)
- **Destination warehouse operator** (receives bars, confirms via OTP)
- **Admin** (can view all transfers, resolve discrepancies)

## 3. Preconditions

- Source and destination locations exist and are different
- Bars are at the source location with sellable status (not RESERVED/SOLD)
- Source operator has inventory transfer permission
- `source_location_id != destination_location_id` (CHECK constraint)

## 4. Trigger

`POST /api/v1/admin/inventory/transfers` with `{ source_location_id, destination_location_id, in_transit_location_id?, bar_ids: [UUID], idempotency_key }`.

## 5. Steps

### State Machine

```
DRAFT                (سند ایجاد شد، بارها انتخاب شدند)
   │
   ▼
DISPATCHED           (Goods Issue: اسکن سریال خروج، مبدأ کم)
   │                 + OTP generate برای مقصد
   ▼
RECEIVED             (Goods Receipt: اسکن سریال ورود در مقصد، تأیید OTP)
   │
   ▼
COMPLETED            (همه items matched → تکمیل)
   │
   └─→ DISCREPANCY   (بعضی items missing/unexpected → بررسی)
       └─→ CANCELLED  (لغو — فقط اگر هنوز DRAFT یا DISPATCHED)
```

### Full Flow

```
1. Source operator → POST /api/v1/admin/inventory/transfers
   { source_location_id, destination_location_id, in_transit_location_id?, bar_ids, idempotency_key }
   → INSERT inventory_transfer_documents (status=DRAFT)
   → INSERT inventory_transfer_items per bar (item_status=expected)

2. Source operator → POST /api/v1/admin/inventory/transfers/{id}/dispatch
   { dispatched_by_user_id }
   → اسکن سریال هر bar در مبدأ (scan validation: bar must match)
   → bars.current_location_id = in_transit_location_id (virtual, non-sellable)
   → INSERT inventory_movement per bar (from=source, to=in_transit)
   → status=DISPATCHED, OTP generate برای مقصد
   → تفکیک وظایف: dispatched_by ≠ received_by

3. Destination operator → POST /api/v1/admin/inventory/transfers/{id}/receive
   { otp_code, received_by_user_id }
   → تأیید OTP (mandatory — D-62)
   → اسکن سریال هر bar در مقصد (match against expected items)
   → bars.current_location_id = destination_location_id
   → INSERT inventory_movement per bar (from=in_transit, to=destination)
   → item_status: expected → received (matched) or missing/unexpected
   → status=RECEIVED

4a. If all items matched:
   → POST /api/v1/admin/inventory/transfers/{id}/confirm
   → status=COMPLETED

4b. If discrepancy found:
   → POST /api/v1/admin/inventory/transfers/{id}/discrepancy
   { item_id, discrepancy_reason }
   → status=DISCREPANCY → admin investigation

5. Cancel (only DRAFT or DISPATCHED):
   → POST /api/v1/admin/inventory/transfers/{id}/cancel { cancel_reason }
   → if DISPATCHED: bars moved back to source_location
   → status=CANCELLED
```

**موجودی در راه:** `inventory_location` مجازی با `location_type='in_transit'` و `is_sellable=FALSE` — هیچجا reserve/فروش نمی‌شود تا رسید.

## 6. DB Writes

- `inventory_transfer_documents` — document with status transitions
- `inventory_transfer_items` — per-bar tracking (expected → dispatched → received/missing/unexpected)
- `bars` — current_location_id transitions (source → in_transit → destination)
- `inventory_movements` — per-bar movement audit at each stage

> Canonical schemas: [Inventory (transfer documents)](../03-schema-index.md#10-inventory), [Supplementary (transfer tables)](../03-schema-index.md#14-supplementary)

## 7. Treasury Impact

**None.** Inventory transfer is a physical location change — no exposure change. Gold ownership and treasury position unchanged.

## 8. Wallet Impact

**None.** No wallet involved in internal transfers.

## 9. Inter-Company Impact

**None.** This is intra-company movement (between locations of the same or any company). Inter-company gold delivery uses [Flow 12 (Settlement)](12-inter-company-settlement.md) instead.

## 10. Audit & Events

- `audit_logs`: **mandatory at every state transition** (draft, dispatch, receive, confirm, discrepancy, cancel)
- `inventory_movements`: per-bar movement records at dispatch and receipt
- `outbox_events`:
  - `InventoryTransferCreated`, `InventoryTransferDispatched`
  - `InventoryTransferReceived`, `InventoryTransferCompleted`
  - `InventoryTransferDiscrepancy` (alert: missing/unexpected bars)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Bar not at source location | Reject (bar must be at source) |
| OTP verification fails | Reject receive attempt |
| Serial scan mismatch at dispatch | Reject dispatch for that bar |
| Serial scan mismatch at receipt | Mark item as unexpected/missing → DISCREPANCY |
| Sender = receiver (same user) | Reject — separation of duties ([D-62](../01-decisions-audit-log.md)) |
| Stuck in transit alert | Configurable timeout threshold → operator notification |

## 12. Invariants

- Sender ≠ Receiver (separation of duties — [D-62](../01-decisions-audit-log.md))
- OTP mandatory between source/destination
- In-transit bars are **non-sellable** (virtual location with `is_sellable=FALSE`)
- Every state transition generates `inventory_movement` + audit
- `source_location_id != destination_location_id` (CHECK constraint)
- Fulfillment (customer delivery) and inventory transfer are **separate systems** ([D-80](../01-decisions-audit-log.md)): if bar needs transfer before delivery, transfer first (D-62), then fulfillment task at destination

## 13. Related References

- [Flow 14 — Fulfillment Delivery](14-fulfillment-delivery.md) (customer-facing delivery — separate system)
- [Schema: Inventory (transfer documents)](../03-schema-index.md#10-inventory) | [Supplementary](../03-schema-index.md#14-supplementary)
- [API: Inventory Transfers](../04-api-index.md)
- [Reference: Inventory/Location](../references/inventory-location-transfer.md)
- Decisions: [D-62](../01-decisions-audit-log.md), [D-80](../01-decisions-audit-log.md), [D-89](../01-decisions-audit-log.md), [D-93](../01-decisions-audit-log.md)
