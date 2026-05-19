# Flow 14 — Fulfillment & Delivery

> **Source:** §8 — فرایند تحویل کالا
> Note: Fulfillment = only customer-order-related delivery (always has `order_id`). Internal warehouse transfers use [Flow 13](13-inventory-transfer.md) — [D-80](../01-decisions-audit-log.md).

---

## 1. Goal

Warehouse operator picks, packs, and delivers a specific bar to the customer (or courier/store). Delivery is confirmed only via customer OTP — not by the warehouse operator who dispatched it.

## 2. Actors

- **Warehouse operator** (picks, packs, hands over — `assign-self`, `pick`, `pack`, `handover`)
- **Delivery agent** (courier, store employee, or dealer — confirms delivery with OTP)
- **Customer** (receives bar, provides OTP)
- **Admin** (manages exception cases: lost, damaged, failed)

## 3. Preconditions

- Order is paid (status=Paid) AND delivery has been requested
- [D-77](../01-decisions-audit-log.md): trigger = **delivery request**, NOT payment. Custodial sale (`delivered_at=NULL`) creates NO task.
- `fulfillment_tasks.bar_id` points to the specific allocated bar ([D-49](../01-decisions-audit-log.md)/[D-77](../01-decisions-audit-log.md))
- Bar is at the source location

## 4. Trigger

Delivery requested → `Fulfillment.create_task(order_item, bar)` → INSERT fulfillment_tasks.

## 5. Steps

### State Machine

```
pending              (task ساخته شد)
   │
   ▼
picking → picked     (انبار‌دار bar_id مشخص را اسکن + برداشت — D-77 serial scan اجباری)
   │
   ▼
packed               (بسته‌بندی شد)
   │
   ▼
handed_over          (D-78: «از دست ما خارج شد» — انبار‌دار، نه «رسید»)
   │
   ▼
delivered            (D-78: فقط با OTP گیرنده + اسکن سریال → bar.delivered_at ست می‌شود)
```

استثناها ([D-79](../01-decisions-audit-log.md)):
```
delivery_failed      (پیک نتوانست / مشتری پس زد / آدرس غلط)
                     → شمش با فرایند D-62 به انبار برمیگردد
lost_in_transit      (گم/دزدیده → رویداد زیان + خزانه compensate)
damaged              (پلمب‌شکسته → بازرسی، قابل فروش نیست)
```

### Full Flow

```
0. ⚠️ D-77: trigger ساخت task = «درخواست تحویل» است، نه «پرداخت سفارش».
   فروش امانی (delivered_at=NULL) هیچ taskی نمیسازد (شمش در خزانه قفل).
   فقط با درخواست تحویل مشتری (یا تحویل فوری در POS/فروشگاه) task ساخته
   می‌شود، با bar_id همان شمش تخصیص‌یافته (D-49).

1. Delivery requested → Fulfillment.create_task(order_item, bar)
2. INSERT fulfillment_tasks (status=pending)
3. انبار‌دار از admin panel: GET /admin/fulfillment/tasks?status=pending
4. انبار‌دار: POST /admin/fulfillment/tasks/{id}/assign-self
5. POST /admin/fulfillment/tasks/{id}/pick  → status=picking → picked
   # D-77: اسکن سریال pick اجباری — باید با bar_id بخواند وگرنه خطا
6. POST /admin/fulfillment/tasks/{id}/pack
7. POST /admin/fulfillment/tasks/{id}/handover  → courier info
   # D-78: انبار‌دار فقط «به پیک دادم» را میزند = handed_over
   # (از دست ما خارج شد، نه «رسید»)
8. POST /admin/fulfillment/tasks/{id}/confirm-delivery → status=delivered
   # D-78: فقط با OTP گیرنده (+ اسکن سریال در تحویل حضوری).
   # انبار‌دار مبدأ این را نمیبندد — نقش مقصد
   # (پیکتأیید/کارمند فروشگاه/نماینده) با delivered_confirmed_by.
   # تا قبل از این، شمش «در حال تحویل»؛
   # bar.delivered_at فقط همینجا ست می‌شود.
```

## 6. DB Writes

- `fulfillment_tasks` — status transitions through state machine
- `fulfillment_events` — event log at each transition (actor, old_status, new_status, notes)
- `bars` — `delivered_at` set only at confirmed delivery ([D-78](../01-decisions-audit-log.md))
- For exception paths ([D-79](../01-decisions-audit-log.md)):
  - `bars.status` → DAMAGED / LOST / IN_INSPECTION as needed

> Canonical schemas: [Fulfillment](../03-schema-index.md#5-fulfillment), [Inventory](../03-schema-index.md#10-inventory)

## 7. Treasury Impact

**Normal delivery:** None — treasury was already adjusted at sale time.

**Exception paths ([D-79](../01-decisions-audit-log.md)):**
- `lost_in_transit`: treasury compensating entry (gold sold/hedged but physical lost — exposure adjustment needed)
- `damaged`: no treasury impact until bar fate decided

## 8. Wallet Impact

**None.** Fulfillment does not touch wallet. Payment was already completed.

## 9. Inter-Company Impact

**None.** Fulfillment is an operational process. Inter-company obligations were created at sale time.

## 10. Audit & Events

- `fulfillment_events`: **mandatory at every state transition** (each step logged with actor + timestamp)
- `audit_logs`: all transitions + exception decisions
- `outbox_events`:
  - `FulfillmentTaskCreated`, `FulfillmentPicked`, `FulfillmentPacked`
  - `FulfillmentHandedOver`, `FulfillmentDelivered`
  - Exception: `FulfillmentDeliveryFailed`, `FulfillmentLostInTransit`, `FulfillmentDamaged`

> Canonical event list: [Events](../05-security-audit-events.md)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Serial scan mismatch at pick ([D-77](../01-decisions-audit-log.md)) | Reject — must scan correct bar_id serial |
| Courier cannot deliver (address/customer issue) | → `delivery_failed` → return via D-62 process |
| Bar lost in transit | → `lost_in_transit` → loss event + treasury compensate + operator decision ([D-79](../01-decisions-audit-log.md)) |
| Bar damaged (seal broken) | → `damaged` → return + inspection → not immediately resaleable ([D-79](../01-decisions-audit-log.md)) |
| OTP expired | Regenerate OTP — delivery not confirmed without valid OTP |

## 12. Invariants

- Task trigger = **delivery request**, not payment ([D-77](../01-decisions-audit-log.md))
- `bar_id` is specific allocated bar ([D-49](../01-decisions-audit-log.md)/[D-77](../01-decisions-audit-log.md)) — serial scan at pick must match
- Warehouse operator only marks `handed_over` — **never** `delivered` ([D-78](../01-decisions-audit-log.md))
- `delivered` requires OTP from recipient role (courier confirmer / store employee / dealer) ([D-78](../01-decisions-audit-log.md))
- `bar.delivered_at` set only at actual delivery confirmation, not at handover
- Exception statuses **never auto-close** — operator/accountant decision + audit + reason mandatory ([D-79](../01-decisions-audit-log.md))
- Fulfillment ≠ internal transfer ([D-80](../01-decisions-audit-log.md)): if bar is at wrong warehouse, first transfer (D-62), then fulfill

## 13. Related References

- [Flow 13 — Inventory Transfer](13-inventory-transfer.md) (internal movement — separate system, [D-80](../01-decisions-audit-log.md))
- [Domain Models — Fulfillment](../02-domain-models.md#۸-فرایند-تحویل-کالا)
- [Schema: Fulfillment](../03-schema-index.md#5-fulfillment) | [Inventory](../03-schema-index.md#10-inventory)
- [API: Fulfillment](../04-api-index.md)
- [Reference: Inventory/Location](../references/inventory-bars-warehouse.md)
- Decisions: [D-13](../01-decisions-audit-log.md), [D-49](../01-decisions-audit-log.md), [D-77](../01-decisions-audit-log.md), [D-78](../01-decisions-audit-log.md), [D-79](../01-decisions-audit-log.md), [D-80](../01-decisions-audit-log.md)
