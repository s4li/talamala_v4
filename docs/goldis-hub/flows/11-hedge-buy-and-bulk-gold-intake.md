# Flow 11 — Hedge Buy & Bulk Gold Intake

> **Source:** §12.5.3 الف — خرید طلای خام از بازار (P0-7)
> Goldis as Central Hedging Desk — covers gold obligations from non-Goldis sales.

---

## 1. Goal

Goldis operator purchases raw gold (granules, large ingots) from the market to cover gold obligations created by TalaMala/AminZar sales. The gold is stored in `bulk_gold_inventory` and periodically delivered to creditor companies via settlement.

## 2. Actors

- **Goldis operator** (admin_role=operator or higher, permission `treasury:hedge`)
- **Goldis Treasury** (Central Hedging Desk — [D-06](../01-decisions-audit-log.md))
- **External supplier** (gold market — offline)

## 3. Preconditions

- Actor has admin/operator role with treasury:hedge permission
- Treasury capacity check passes ([D-47](../01-decisions-audit-log.md): max_short_exposure_mg)
- Market rate is reasonable (optional: verify against reference prices)

## 4. Trigger

`POST /api/v1/admin/treasury/hedge-buy/request` with `{ metal_type, amount_mg, supplier_name, purchase_price_per_gram_rial, notes }`.

## 5. Steps

```
۱. Operator Goldis → /api/v1/admin/treasury/hedge-buy/request
   {
     metal_type: "gold",
     amount_mg: 500000,
     supplier_name: "قیمتی طلا",
     purchase_price_per_gram_rial: 650000,
     notes: "پوشش تعهد فروش TalaMala (۲۰۲۶-۰۵-۱۸)"
   }

۲. Backend:
   - Treasury.check_capacity (سقف دو‌طرفه D-47: max_short_exposure_mg check)
   - Pricing.verify_market_rate (optional: تأیید نرخ با نقاط مرجع)
   - INSERT bulk_gold_inventory (
       location_id = goldis_warehouse,
       owner_company_id = Goldis,
       acquisition_source = "hedge_buy",
       total_weight_mg = 500000,
       total_pure_weight_mg = 500000 (assuming purity=1000 for raw),
       reference_type = "treasure_hedge_buy",
       reference_id = generated_id
     )
   - INSERT bulk_gold_movements (intake، weight_mg_delta=+500000)
   - Treasury.record (source=hedge_buy، delta=-500000)  # D-90: hedge_buy کاهش exposure (عکس short position)
   - Audit log + Notification

۳. Flow اختیاری برای compliance:
   - اپراتور می‌تواند hedge_buy را تا قبل از تحویل فیزیکی «pending» نگه دارد
   - بعد از تحویل فیزیکی از supplier: Operator تأیید میکند
   - وزن اسکن/تأیید شده → bulk_gold_inventory.last_counted_at update

۴. Settlement دورهای (روزانه یا هفتگی):
   - Operator:
     POST /api/v1/admin/inter-company/settle-gold
     {
       creditor: "TalaMala",
       asset_type: "gold",
       amount_mg: 150000,  -- حداکثر از pending obligations
       source_bulk_gold_id: <bulk_gold_id>
     }
   - Backend:
     - Withdraw از bulk_gold_inventory (weight_mg_delta=-150000)
     - INSERT inventory_movement (from=goldis_warehouse, to=talamala_warehouse)
     - UPDATE inter_company_ledger (status=settled)
     - Audit log + Notification
```

**قوانین:**
- Hedge Buy **تنها در سطح Goldis** (operator only) قابل ایجاد است
- هر hedge_buy یک source برای multiple settlements می‌تواند باشد
- وزن در دسترس برای settlement نباید از total_weight_mg بیشتر شود (CHECK constraint یا service-level validation)
- هر settlement، obligation های open موجود در `inter_company_ledger` را FIFO consume میکند و در `inter_company_settle_actions` audit record میسازد (نه entry جدید)

## 6. DB Writes

- `bulk_gold_inventory` — new row (acquisition_source=hedge_buy)
- `bulk_gold_movements` — intake record (weight_mg_delta=+amount_mg)
- `treasury_positions` — delta=-amount_mg (hedge_buy reduces exposure)
- On settlement: `inter_company_ledger` updated (status=settled), `inventory_movements` for physical transfer

> Canonical schemas: [Inventory (bulk_gold)](../03-schema-index.md#10-inventory), [Treasury](../03-schema-index.md#3-treasury), [Inter-Company](../03-schema-index.md#4-inter-company-ledger)

## 7. Treasury Impact

- `treasury_positions` delta = **−amount_mg** (hedge_buy = closing exposure)
- Sign: **negative** — buying gold from market offsets short position from sales
- Subject to bidirectional caps ([D-47](../01-decisions-audit-log.md))

## 8. Wallet Impact

**None.** Hedge buy is a treasury operation — no wallet involved.

## 9. Inter-Company Impact

- Hedge buy itself: no inter-company entries (Goldis buying from external market)
- Settlement phase: FIFO consume **existing open** gold obligations in `inter_company_ledger` + audit in `inter_company_settle_actions` (see [Flow 12](12-inter-company-settlement.md))
  - If `source_bulk_gold_id` provided: `bulk_gold_inventory` withdrawal + `bulk_gold_movements` + `inventory_movements`

## 10. Audit & Events

- `audit_logs`: hedge buy request, treasury position change (mandatory — financial operation)
- `outbox_events`:
  - `HedgeBuyRecorded`
  - `TreasuryPositionUpdated`
  - `BulkGoldIntake`
  - On settlement: `InterCompanyGoldSettled`

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Treasury cap exceeded (D-47) | Reject hedge buy request |
| Market rate suspiciously off | Warning + optional reject |
| Bulk gold weight exceeds settlement total | Service-level validation prevents over-withdrawal |
| Operator without treasury:hedge permission | Reject (403) |

## 12. Invariants

- Hedge Buy is **Goldis-only** operation — no other company can create hedge buys
- `treasury_positions` delta is always **negative** for hedge_buy (closing exposure)
- Available settlement weight ≤ total_weight_mg (cannot over-withdraw from bulk_gold_inventory)
- Settlement FIFO-consumes existing open obligations in `inter_company_ledger` — does NOT create new ledger entries
- Bulk gold = raw gold (granules, ingots) — NOT serialized bars; stored by weight (mg) not serial ([D-83](../01-decisions-audit-log.md))
- Physical delivery to creditor company is a **separate real-world event** — operator confirms in system after actual delivery

## 13. Related References

- [Flow 12 — Inter-Company Settlement](12-inter-company-settlement.md) (settlement of obligations)
- [Domain Models — Treasury](../02-domain-models.md#۵-مدل-treasury-central-hedging-desk-goldis-only)
- [Schema: Inventory (bulk_gold)](../03-schema-index.md#10-inventory) | [Treasury](../03-schema-index.md#3-treasury) | [Inter-Company](../03-schema-index.md#4-inter-company-ledger)
- [API: Treasury](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-06](../01-decisions-audit-log.md), [D-47](../01-decisions-audit-log.md), [D-82](../01-decisions-audit-log.md), [D-83](../01-decisions-audit-log.md), [D-84](../01-decisions-audit-log.md), [D-90](../01-decisions-audit-log.md)
