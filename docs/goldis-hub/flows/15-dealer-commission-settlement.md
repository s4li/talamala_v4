# Flow 15 — Dealer Commission Settlement

> **Source:** D-73 + D-84 + §11.9 — تسویه کمیسیون نمایندگان (Gold-for-Gold)
> Note: Dealer commission is **separate** from inter-company ledger. Dealers are users, not companies — mixing them contaminates hedging reports ([D-73](../01-decisions-audit-log.md) P1).

---

## 1. Goal

Periodically settle accumulated dealer commissions by depositing gold (XAU_MG) to the dealer's wallet. Commission is calculated as a percentage of `pure_gold_mg` per transaction (Gold-for-Gold), stored in `dealer_commission_ledger`, and settled by Goldis/TalaMala operator.

## 2. Actors

- **Dealer** (recipient of commission — passive in settlement flow)
- **TalaMala operator** (initiates commission settlement — commission comes from TalaMala's margin)
- **Goldis Treasury** (affected by gold exposure from commission deposit — [D-73](../01-decisions-audit-log.md) P3)

## 3. Preconditions

- Open commission entries exist in `dealer_commission_ledger` (status=open)
- Dealer has active XAU_MG wallet
- Treasury cap allows additional gold exposure ([D-47](../01-decisions-audit-log.md))
- For buyback commissions: only after `AuthenticityVerified` ([D-73](../01-decisions-audit-log.md) بند۷)

## 4. Trigger

Operator initiates periodic settlement (daily/weekly/monthly) via admin panel.

## 5. Steps

### Commission Recording (at sale/buyback time)

```
1. At POS sale / physical sale time (source flows: 01, 07):
   - Calculate: commission_mg = pure_gold_mg × commission_percent
     (rate from dealer_commission_rates, resolved by product/tier/trade_side — مثل D-65)
   - Guard check (D-73 بند۶): Σکمیسیون ≤ (P_retail − P_hedge)
     → if violated: reject sale / warn operator
   - INSERT dealer_commission_ledger (
       dealer_user_id, seller_company_id=TalaMala,
       trade_side='sale', amount_mg=commission_mg,
       status='open'
     )
   - Record on DealerSale + metal_profit_mg

2. At buyback time (source flows: 05, 06):
   - Guard check (D-73 بند۶ب): commission ≤ buyback spread
   - ⚠️ D-73 بند۷: commission فقط بعد از AuthenticityVerified (نه قبلش)
   - INSERT dealer_commission_ledger (trade_side='buyback', ...)
```

### Commission Settlement (periodic, by operator)

```
3. Operator → admin panel → select dealer + period → settle
   - Aggregate: total_open_mg = SUM(amount_mg) WHERE dealer_user_id=X AND status='open'
   - Treasury.check_capacity (D-47: commission gold = new exposure)
   - در یک DB transaction:
     a. Wallet.credit(dealer, wallet_scope, XAU_MG, total_open_mg)
     b. Treasury.record(source=dealer_commission, delta=+total_open_mg)
        # D-73 P۳: commission gold = new digital gold ⇒ +exposure
     c. UPDATE dealer_commission_ledger entries: status='settled', settled_at=now
     d. D-84: if seller_company=TalaMala:
        INSERT inter_company_ledger offset entry
        (TalaMala→Goldis gold debt partially covered by commission payout)
        → prevents mismatch: TalaMala gave gold (treasury −) but hedged liability not recorded
     e. Audit log + Outbox: DealerCommissionSettled + Notification
```

## 6. DB Writes

- `dealer_commission_ledger` — status: open → settled, settled_at, settled_by
- `dealer_commission_rates` — read-only (configuration, not written in this flow)
- `dealer_sales` — metal_profit_mg recorded at sale time
- `wallet_ledger_entries` — credit XAU_MG to dealer wallet
- `asset_balances` — dealer's XAU_MG balance increased
- `treasury_positions` — delta=+total_open_mg (new gold exposure from commission)
- `inter_company_ledger` — offset entry if TalaMala commission ([D-84](../01-decisions-audit-log.md))

> Canonical schemas: [Supplementary (dealer_commission)](../03-schema-index.md#14-supplementary), [Wallet](../03-schema-index.md#2-wallet), [Treasury](../03-schema-index.md#3-treasury)

## 7. Treasury Impact

- `treasury_positions` += `total_commission_mg` (source=dealer_commission)
- Sign: **positive** — commission gold is new digital gold, creates exposure
- Subject to bidirectional caps ([D-47](../01-decisions-audit-log.md))
- **D-73 P3:** commission deposit to dealer wallet = new gold ⇒ treasury must track it

## 8. Wallet Impact

- Dealer's XAU_MG wallet credited with total_commission_mg
- Wallet scope: determined by seller_company (typically TalaMala scope)
- Dealer can then trade/withdraw this gold via standard wallet flows

## 9. Inter-Company Impact

**D-84 offset:** When commission is from TalaMala:
- TalaMala gives gold (as commission) → treasury exposure increases
- This must be offset in inter_company_ledger to prevent mismatch
- Offset entry: TalaMala→Goldis gold debt partially covered
- Without offset: TalaMala paid gold but hedged liability not recorded → financial mismatch

## 10. Audit & Events

- `audit_logs`: commission recording (at sale), settlement (at payout) — both mandatory
- `outbox_events`:
  - `DealerCommissionRecorded` (at sale/buyback time)
  - `DealerCommissionSettled` (at settlement time)
  - `WalletCredited` (dealer wallet)
  - `TreasuryPositionUpdated` (exposure from commission)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Commission exceeds sale guard (P_retail − P_hedge) | Reject sale or warn operator ([D-73](../01-decisions-audit-log.md) بند۶) |
| Buyback commission exceeds spread | Reject or warn operator ([D-73](../01-decisions-audit-log.md) بند۶ب) |
| Treasury cap exceeded by commission | Reject settlement until cap cleared |
| Commission before AuthenticityVerified (buyback) | Reject — only after verification ([D-73](../01-decisions-audit-log.md) بند۷) |
| No open commission entries for dealer | Nothing to settle |

## 12. Invariants

- Commission is **Gold-for-Gold** — based on `pure_gold_mg`, not rial ([D-73](../01-decisions-audit-log.md) بند۵)
- Commission ledger is **separate** from inter_company_ledger (dealers are users, not companies — [D-73](../01-decisions-audit-log.md) P1)
- Sale guard: Σcommission ≤ `P_retail − P_hedge` ([D-73](../01-decisions-audit-log.md) بند۶)
- Buyback guard: commission ≤ buyback spread ([D-73](../01-decisions-audit-log.md) بند۶ب)
- Buyback commission only after `AuthenticityVerified` ([D-73](../01-decisions-audit-log.md) بند۷)
- Commission gold deposit creates treasury exposure ([D-73](../01-decisions-audit-log.md) P3) — subject to D-47 caps
- Treasury exposure offset mandatory for TalaMala commissions ([D-84](../01-decisions-audit-log.md))
- SubDealer/network/MLM **removed** from entire v5 scope — flat dealer model ([D-73](../01-decisions-audit-log.md) بند۹)

## 13. Related References

- [Flow 07 — POS Sale](07-pos-sale.md) (commission recorded at POS sale time)
- [Flow 06 — Buyback In-Person](06-buyback-in-person.md) (buyback commission after verification)
- [Flow 11 — Hedge Buy](11-hedge-buy-and-bulk-gold-intake.md) (related to D-84 offset)
- [Domain Models — Dealer](../02-domain-models.md)
- [Schema: Supplementary (dealer_commission)](../03-schema-index.md#14-supplementary) | [Wallet](../03-schema-index.md#2-wallet) | [Treasury](../03-schema-index.md#3-treasury)
- [API: Treasury](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-47](../01-decisions-audit-log.md), [D-73](../01-decisions-audit-log.md), [D-84](../01-decisions-audit-log.md), [D-94](../01-decisions-audit-log.md), [D-95](../01-decisions-audit-log.md)
