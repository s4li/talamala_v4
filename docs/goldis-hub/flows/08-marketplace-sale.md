# Flow 08 — Marketplace Sale (DigiKala)

> **Source:** §12.8 — Marketplace pull (DigiKala)

---

## 1. Goal

Import and process orders from external marketplaces (DigiKala, Basalam, etc.) via pull adapter. All marketplace sales are Goldis-side — no inter-company obligations.

## 2. Actors

- **Marketplace platform** (DigiKala, Basalam — external)
- **Marketplace sync worker** (periodic pull)
- **Goldis** (operator, seller, payment receiver — always)

## 3. Preconditions

- Marketplace channel configured (channel_type=marketplace, adapter_class set)
- Product mappings exist (external SKU → internal product_id)
- Inventory available for the mapped products
- Treasury capacity check passes ([D-101](../01-decisions-audit-log.md)): سفارش‌های marketplace از قبل پرداخت‌شده وارد می‌شوند (Order.create status=Paid، بدون gateway round-trip)، پس checkout→payment gap وجود ندارد — سقف در یک گامِ inline واحد اعمال می‌شود: زیر `pg_advisory_xact_lock(hashtext('treasury:'||metal_type))` شرطِ `committed + reserved + this_tx ≤ cap` چک و سپس `treasury_position` مستقیم نوشته می‌شود. مرحله‌ی `inventory_pending_holds`/finalize اینجا استفاده نمی‌شود — آن hold دو‌مرحله‌ای فقط برای flowهای دارای gateway round-trip است (01/04/07). `reserved` همچنان holdهای زنده‌ی آن flowها را جمع می‌زند. ترتیب قفل: advisory(treasury per metal) → wallet rows → bar.

## 4. Trigger

Automated: marketplace sync worker runs every minute, pulls new orders via adapter.

## 5. Steps

```
Worker هر دقیقه:
  for each channel where type=marketplace, mode in {pull_only, push_managed}:
    adapter = build_adapter(channel)
    new = await adapter.fetch_new_orders(since=channel.last_sync_at)
    for ext in new:
      dedup_key = adapter.compute_dedup_key(ext)
      try INSERT external_orders (..., dedup_key)
      except UniqueViolation: continue   # already imported

      internal_product_id = lookup_mapping(channel, ext.sku)
      Order.create(
        order_type=marketplace_sale, status=Paid,
        brand=channel.brand,
        payment_receiver=channel.payment_receiver,  # marketplace → Goldis
        seller_company=channel.seller_company,
      )
      pg_advisory_xact_lock(hashtext('treasury:'||metal_type))   # D-101 serialize — advisory BEFORE bar
      if committed + reserved + this_tx > cap:   # D-101 canonical formula
        Outbox: ExternalOrderFailed; alert admin; continue   # skip rather than breach cap
      Inventory.consume(channel, product)   # bar → SOLD (AFTER advisory per global lock order advisory→wallet→bar)
      Treasury.record(source=marketplace_sale, delta=+pure_gold_mg)  # D-91 pure weight; D-101: marketplace writes treasury_position directly (no pending_hold/finalize — payment already settled)
      # D-56 (قطعی): marketplace همیشه seller=Goldis و payment_receiver=Goldis
      # هیچ inter_company_ledger entry برای marketplace وجود ندارد
      # (حتی اگر brand=TalaMala — چون Goldis انحصارا marketplace را اداره میکند)
      Outbox: ExternalOrderImported + OrderPaid + ...
    await adapter.acknowledge_orders(...)
    UPDATE channels.last_sync_at = now()
```

> **⚠️ D-56 (قطعی):** هیچ inter-company entry در marketplace نیست. تمام درآمد به Goldis می‌رود. TalaMala هیچ marketplace income مستقیم ندارد — فقط از فروش مستقیم سایتش (channel talamala_direct).

## 6. DB Writes

- `external_orders` — imported order with dedup_key (UniqueViolation = skip)
- `orders` — order_type=marketplace_sale, status=Paid
- `order_items` — with price snapshot + pure_gold_mg
- `bars` — status → SOLD, customer_id set (if physical)
- `inventory_reservations` → consumed

> Canonical schemas: [Order](../03-schema-index.md#11-order), [Inventory](../03-schema-index.md#10-inventory)

## 7. Treasury Impact

- `treasury_positions` += `pure_gold_mg` (source=marketplace_sale)
- Sign: **positive** (open exposure — Goldis owes gold)
- Same single-leg as website physical sale

## 8. Wallet Impact

- **No wallet impact.** Marketplace payments are handled externally by the marketplace platform.

## 9. Inter-Company Impact

**No inter-company entries — ever.** ([D-56](../01-decisions-audit-log.md) definitive)

- Marketplace is always seller=Goldis, payment_receiver=Goldis
- Even if brand=TalaMala on marketplace — Goldis exclusively operates marketplace
- TalaMala has no direct marketplace income

## 10. Audit & Events

- `outbox_events`:
  - `ExternalOrderFetched`, `ExternalOrderImported`
  - `OrderPaid`, `TreasuryPositionOpened`
  - `ChannelInventoryPushed` (if push_managed mode)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Duplicate order (dedup_key) | Skip silently (UniqueViolation) |
| Product mapping not found | `ExternalOrderFailed` event, skip order, alert admin |
| No inventory for product | `ExternalOrderFailed` event, skip order |
| Treasury cap exceeded | `ExternalOrderFailed` event, skip order, alert admin (single inline cap check under advisory lock — [D-101](../01-decisions-audit-log.md)) |
| Adapter connection failure | Worker retries next cycle, alert if persistent |
| Marketplace API rate limit | Backoff, retry next cycle |

## 12. Invariants

- Marketplace = always Goldis-side ([D-56](../01-decisions-audit-log.md)) — no exceptions
- Dedup via `dedup_key` — idempotent import
- `pure_gold_mg = weight_mg × purity / 1000` — always pure weight ([D-91](../01-decisions-audit-log.md))
- Payment already received by marketplace — order created as status=Paid directly

## 13. Related References

- [Flow 01 — Physical Bar Purchase](01-physical-bar-purchase-site.md) (direct sale variant)
- [Schema: Order](../03-schema-index.md#11-order)
- [API: Marketplace](../04-api-index.md)
- [Reference: Outbox/Workers](../references/outbox-workers-realtime.md)
- Decisions: [D-47](../01-decisions-audit-log.md), [D-56](../01-decisions-audit-log.md), [D-91](../01-decisions-audit-log.md), [D-101](../01-decisions-audit-log.md)
