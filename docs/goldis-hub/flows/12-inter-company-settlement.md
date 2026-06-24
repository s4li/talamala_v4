# Flow 12 — Inter-Company Settlement

> **Source:** §12.9 + §6.5 — Inter-Company Settle (دستی، on-demand)
> Note: Settlement daily worker was **removed** (D-06b). Ledger entries are created real-time at each sale; operator settles manually whenever ready.

---

## 1. Goal

Goldis operator manually settles inter-company obligations (rial and gold) between companies. Rial settlement = bank transfer confirmation. Gold settlement = physical raw gold delivery confirmation. **D-102:** the ledger is a signed **NET running account**; a settlement **APPENDS a row in the opposite direction** that moves the net toward zero (no FIFO, no status, no row mutation).

## 2. Actors

- **Goldis operator** (admin_role=operator or higher, permission `inter_company:settle`)
- **Accounting team** (reviews open obligations)

## 3. Preconditions

- A non-zero **net** outstanding exists for the (company-pair, asset) in `inter_company_ledger` (D-102 — no status column)
- Actor has admin/operator role with `inter_company:settle` permission
- For rial: bank transfer has already been made in real world
- For gold: physical gold delivery has already happened in real world

## 4. Trigger

- Rial: `POST /api/v1/admin/inter-company/settle-rial` with `{ creditor_company_id, debtor_company_id, amount_rial, notes }`
- Gold: `POST /api/v1/admin/inter-company/settle-gold` with `{ creditor_company_id, debtor_company_id, amount_mg, notes, source_bulk_gold_id? }`

## 5. Steps

### Settle Rial (فروشنده پول طلای خام را به Goldis پرداخت)

```
سناریوی typical:
1. TalaMala فروش میکند → دو ردیف (gold + rial) در دفتر append می‌شود (D-102 — بدون status)
2. حسابدار/اپراتور Goldis تو پنل net معوق را میبیند:
   GET /admin/inter-company/balance?company_a=Goldis&company_b=TalaMala
3. وقتی TalaMala معادل بهای طلای خام را به Goldis بانکی منتقل کرد:
   POST /admin/inter-company/settle-rial { creditor=Goldis, debtor=TalaMala, amount, notes }
   → D-102: یک ردیف settlement در جهت مخالف append می‌شود (هیچ FIFO/mutate):
        INSERT inter_company_ledger(debtor=Goldis, creditor=TalaMala, asset='IRR',
              amount_minor=amount, source_type='settlement', recorded_by=actor)
     که net(TalaMala owes Goldis, IRR) را به سمت صفر می‌برد.
   → Outbox: InterCompanyRialSettled   (audit کامل در audit_logs)
```

### Settle Gold (Goldis طلای خام را به فروشنده تحویل داد)

```
سناریو: Goldis در پایان هفته (یا هر دوره) معادل وزن خام طلا را فیزیکی
به TalaMala تحویل می‌دهد (به‌صورت گرانول/شمش بزرگ/هر فرم خام).
اپراتور Goldis تحویل را در سیستم ثبت میکند.

POST /api/v1/admin/inter-company/settle-gold
Body: { creditor_company_id: TalaMala, debtor_company_id: Goldis, amount_mg, notes, source_bulk_gold_id? }
→ D-102: append یک ردیف settlement جهت‌مخالف (هیچ FIFO/status):
     INSERT inter_company_ledger(debtor=TalaMala, creditor=Goldis, asset='XAU_MG',
           amount_minor=amount_mg, source_type='settlement', recorded_by=actor)
   که net gold را به سمت صفر می‌برد.
→ اگر source_bulk_gold_id ارائه شود (D-82 Hedge Buy):
  - Withdraw از bulk_gold_inventory (weight_mg_delta=-amount_mg)
  - INSERT inventory_movement (from=goldis_warehouse, to=talamala_warehouse)
→ Outbox: InterCompanyGoldSettled   (audit کامل در audit_logs)
```

**نکته:** این endpoint **فقط ledger را آپدیت میکند** — تحویل واقعی طلای خام در دنیای واقعی توسط تیم عملیات Goldis انجام می‌شود. این طلا برای hedging یا تولید بعدی بهکار می‌رود، **ربطی به refill شمشهای فروختهشده ندارد**.

هیچ worker اتوماتی نیست. اپراتور دستی tracking میکند.

## 6. DB Writes

- `inter_company_ledger` — a NEW append-only `settlement` row in the opposite direction (D-102 — no row mutated, no status)
- `audit_logs` — the operator settle action (mandatory; the `inter_company_settle_actions` table is removed — D-102)
- `bulk_gold_inventory` — withdrawal if source_bulk_gold_id provided (gold settle only)
- `bulk_gold_movements` — withdrawal record if bulk gold used
- `inventory_movements` — if physical gold transferred between locations

> Canonical schemas: [Inter-Company](../03-schema-index.md#4-inter-company-ledger), [Inventory (bulk_gold)](../03-schema-index.md#10-inventory)

## 7. Treasury Impact

**None directly.** Settlement consumes obligations but does not change treasury exposure. Treasury was already adjusted when the original sale (or hedge buy) occurred.

## 8. Wallet Impact

**None.** Settlement is a company↔company operation. No user wallets involved.

## 9. Inter-Company Impact

**This is the inter-company flow.** It moves the NET toward zero (D-102):
- Rial: debtor pays creditor → append an opposite-direction `settlement` row → net moves toward zero
- Gold: Goldis delivers raw gold → append an opposite-direction `settlement` row → net moves toward zero
- The settle IS a ledger row (`source_type='settlement'`, `recorded_by`); the sensitive action is also in `audit_logs`

## 10. Audit & Events

- `audit_logs`: every settle action is mandatory audit (sensitive financial operation)
- `outbox_events`:
  - `InterCompanyRialSettled` (rial settlement)
  - `InterCompanyGoldSettled` (gold settlement)
  - `BulkGoldWithdrawal` (if bulk gold used as source)

> Canonical event list: [Events](../05-security-audit-events.md)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Net is already zero for the company pair | Reject (nothing to settle) |
| Amount exceeds current net outstanding | Warn / allow but flips the net sign (over-settle) — operator confirms; net simply goes negative |
| source_bulk_gold_id has insufficient weight | Reject |
| Operator without inter_company:settle permission | Reject (403) |

## 12. Invariants

- Settlement is **always manual** — no automatic worker ([D-06b](../01-decisions-audit-log.md))
- Settlement is **append-only** (a row toward zero) — never mutates prior rows; outstanding = NET per (pair, asset) ([D-102](../01-decisions-audit-log.md))
- Opposite-direction obligations (digital buy↔sell, buyback, D-84 commission offset) **auto-net** — no second independent obligation ([D-102](../01-decisions-audit-log.md))
- Gold settlement delivers **raw gold** (granules, ingots) — NOT the same bars that were sold ([D-06d](../01-decisions-audit-log.md))
- Buyback **never reverses** original sale obligations ([D-59](../01-decisions-audit-log.md))
- Profit stays with the seller — Goldis only gets raw gold price ([D-39](../01-decisions-audit-log.md))

## 13. Related References

- [Flow 11 — Hedge Buy](11-hedge-buy-and-bulk-gold-intake.md) (source of bulk gold for settlement)
- [Flow 01 — Physical Bar Purchase](01-physical-bar-purchase-site.md) (creates obligations on non-Goldis sale)
- [Domain Models — Inter-Company](../02-domain-models.md#۶-مدل-inter-company-ledger-hub-and-spoke-real-time)
- [Schema: Inter-Company](../03-schema-index.md#4-inter-company-ledger) | [Inventory](../03-schema-index.md#10-inventory)
- [API: Inter-Company Ledger](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-06b](../01-decisions-audit-log.md), [D-06d](../01-decisions-audit-log.md), [D-39](../01-decisions-audit-log.md), [D-59](../01-decisions-audit-log.md), [D-82](../01-decisions-audit-log.md), [D-85](../01-decisions-audit-log.md)
