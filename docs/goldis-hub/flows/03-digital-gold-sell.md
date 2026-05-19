# Flow 03 — Digital Gold Sell

> **Source:** §12.4 — فروش طلای دیجیتال
> Note: «بازخرید دیجیتال» = همین flow ([D-68](../01-decisions-audit-log.md) — مسیر جدا ندارد)

---

## 1. Goal

Customer sells digital gold (XAU_MG) from wallet, receiving IRR (rial) in return.

## 2. Actors

- **Customer** (authenticated, KYC-cleared, has XAU_MG balance)
- **Brand website** (TalaMala / Goldis / AminZar)
- **Goldis Treasury** (central hedging desk)

## 3. Preconditions

- Customer has sufficient XAU_MG balance in the brand's wallet scope
- Price is fresh (staleness guard)
- Trade enabled for this metal + channel (wallet_sell)
- KYC limits: daily/monthly gold outflow limits

## 4. Trigger

`POST /api/v1/wallet/trades/sell` with `{ asset: XAU_MG, amount_mg }`.

## 5. Steps

```
1. کاربر تو wallet TalaMala → POST /api/v1/wallet/trades/sell
   { asset: XAU_MG, amount_mg: 300 }
2. Wallet.check_balance(user, TalaMala, XAU_MG, 300) → ok
3. Pricing lock (sell side)
4. Wallet.lock(user, TalaMala, XAU_MG, 300, ref=trade_intent)
5. Order.create (brand=TalaMala، ...)
6. confirm:
   - Wallet.consume_lock(user, TalaMala, XAU_MG, 300)
   - Wallet.credit(user, TalaMala, IRR, computed_amount)
   - Treasury.record(source=digital_sell, delta=-300mg)   # تک‌پایی — D-67
   - اگر scope غیر-Goldis (مثل TalaMala) → Inter-company × 2 (D-70، آینهٔ ۱۲.۳/D-69):
       • TalaMala → Goldis، gold، 300mg            # TalaMala طلا را پس می‌دهد
       • Goldis → TalaMala، rial، P_hedge_per_mg(لحظه) × 300mg
     اگر scope=Goldis (برند Goldis/AminZar) → هیچ تعهد بین‌شرکتی، فقط خزانه‌ی −
     # مابه‌التفاوت (P_hedge − مبلغ پرداختی به کاربر) حاشیه‌ی TalaMala
     # این همان مسیر یکتای digital_trade sell است (D-68 — «بازخرید دیجیتال» = همین)
   - Outbox + Notification
```

## 6. DB Writes

- `orders` — new row (order_type=digital_trade, trade_side=sell)
- `wallet_ledger_entries` — debit XAU_MG + credit IRR
- `asset_balances` — XAU_MG decreased, IRR increased
- `wallet_locks` — created then consumed

> Canonical schemas: [Order](../03-schema-index.md#11-order), [Wallet](../03-schema-index.md#2-wallet)

## 7. Treasury Impact

- `treasury_positions` -= `amount_mg` (source=digital_sell) — single-leg ([D-67](../01-decisions-audit-log.md))
- Sign: **negative** (exposure closed)

## 8. Wallet Impact

- `asset_balances[user, scope, XAU_MG]` -= amount_mg (debit via lock→consume)
- `asset_balances[user, scope, IRR]` += computed_rial (credit)
- Lock mechanism: lock → consume (atomic, prevents double-spend)

## 9. Inter-Company Impact

**Goldis-side (Goldis/AminZar scope):** No inter-company entries.

**Non-Goldis (TalaMala scope):** 2 entries ([D-70](../01-decisions-audit-log.md) — mirror of D-69):
- TalaMala → Goldis, gold, amount_mg (TalaMala returns gold)
- Goldis → TalaMala, rial, P_hedge_per_mg × amount_mg

Margin (P_hedge − amount_paid_to_user) stays with TalaMala.

## 10. Audit & Events

- `outbox_events`:
  - `DigitalGoldSold`
  - `TreasuryPositionOpened` (negative delta)
  - `InterCompanyObligationCreated` (if non-Goldis)
  - `WalletDebited`, `WalletCredited`

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Insufficient XAU_MG balance | Reject trade |
| Price lock expired | Release wallet lock, reject |
| KYC gold outflow limit exceeded | Reject trade |
| Concurrent trade drains balance | Lock mechanism prevents double-spend |

## 12. Invariants

- «بازخرید دیجیتال» is NOT a separate flow — it IS this flow ([D-68](../01-decisions-audit-log.md))
- Sell-side pricing uses `trade_side=sell` formula from pricing ladder ([D-72](../01-decisions-audit-log.md))
- Treasury single-leg for digital_sell ([D-67](../01-decisions-audit-log.md))
- Non-Goldis inter-company is mirror of digital_buy ([D-70](../01-decisions-audit-log.md))

## 13. Related References

- [Flow 02 — Digital Gold Buy](02-digital-gold-buy.md) (mirror flow)
- [Domain Models — Wallet](../02-domain-models.md#۴-مدل-wallet-per-wallet-scope)
- [Schema: Wallet](../03-schema-index.md#2-wallet) | [Order](../03-schema-index.md#11-order)
- [API: Wallet](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-46](../01-decisions-audit-log.md), [D-67](../01-decisions-audit-log.md), [D-68](../01-decisions-audit-log.md), [D-69](../01-decisions-audit-log.md), [D-70](../01-decisions-audit-log.md), [D-72](../01-decisions-audit-log.md)
