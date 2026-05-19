# Flow 02 — Digital Gold Buy (AminZar + TalaMala)

> **Source:** §12.2 (AminZar) + §12.3 (TalaMala)

---

## 1. Goal

Customer buys digital gold (XAU_MG) via a brand wallet. Gold is credited to the customer's wallet in the brand's scope.

## 2. Actors

- **Customer** (authenticated, KYC-cleared)
- **Brand website** (AminZar / TalaMala / Goldis)
- **Payment gateway** (IPG of payment_receiver company)
- **Goldis Treasury** (central hedging desk)

## 3. Preconditions

- Customer KYC level sufficient
- Price is fresh (staleness guard)
- Trade enabled for this metal + channel (wallet_buy)
- Treasury capacity check passes ([D-47](../01-decisions-audit-log.md))

## 4. Trigger

`POST /api/v1/wallet/trades/buy` with `{ asset: XAU_MG, amount_mg, channel }`.

## 5. Steps

### Variant A — AminZar (Goldis-side sale)

```
1. کاربر در aminzar.ir → POST /api/v1/wallet/trades/buy
   { asset: XAU_MG, amount_mg: 500, channel: aminzar_web }
2. brand=AminZar, channel=aminzar_web, payment_account=Goldis_IPG,
   payment_receiver=Goldis, seller_company=Goldis
   (چون برند امین زر توسط Goldis اداره می‌شود — D-06b, ۱.۳)
3. KYC + limits
4. Treasury.check_capacity(gold, +500mg) → ok
5. Pricing.create_price_lock(channel=aminzar_web, asset=XAU_MG, 500mg)
6. Order.create(
     brand_id=AminZar, ...,
     order_type=digital_trade, trade_side=buy,
     payment_receiver=Goldis, seller_company=Goldis
   )
7. Payment → Goldis IPG → redirect
8. on verified:
   - Wallet scope=aminzar, company=شرکت گلدیس (XAU_MG) of user → +500mg  # D-46: ایزوله، نه merge در Goldis
   - Treasury.record(source=digital_buy, delta=+500mg,
                     triggered_by_brand=AminZar)
   - Inter-company ledger: **هیچ entry** — چون seller=Goldis (Goldis-side sale)
   - Accounting + Outbox + Notification
```

> **نکته:** هرچند brand_owner = شرکت امین زر، ولی چون Goldis این برند را اداره میکند و پول/سود مال Goldis است، از نظر hedging یک فروش Goldis-side محسوب می‌شود. **wallet scope=aminzar اما کاملا از goldis جدا است** (D-46: سه scope ایزوله). شرکت امین زر فقط در لحظه‌ی تأمین شمش از کارخانهاش به Goldis سود میگیرد (در context چرخه‌ی تولید).

### Variant B — TalaMala (non-Goldis sale)

```
مشابه ۱۱.۲ ولی:
- payment_account=TalaMala_IPG, payment_receiver=TalaMala
- Wallet at TalaMala (XAU_MG) of user → +500mg
- Treasury مرکزی Goldis: +500mg (تک‌پایی digital_buy — D-67؛ treasury
  مرکزی است حتی اگر پول رفته به TalaMala)
- Inter-company ledger × 2 (TalaMala-side):
  • TalaMala → Goldis، rial = P_hedge_per_mg(لحظه) × 500mg   # D-69/D-65 — نه internal_base_price، نه قیمتی که کاربر پرداخت
  • Goldis → TalaMala، gold، 500mg
  (status=open، تا اپراتور settle کند)
  # D-69: خرید دیجیتال scope غیر-Goldis همسنگ فروش فیزیکی غیر-Goldis
  #   است (همان مدل ۱۲.۱)؛ فقط شمش/اجرت ندارد و خزانهاش تک‌پایی
  #   digital_buy است. مابه‌التفاوت (قیمت کاربر − P_hedge) سود TalaMala.
```

این کلید فهم سیستم است: **پول و wallet هر برند جداست، ولی Goldis بهعنوان Central Hedging Desk از طریق `inter_company_ledger` real-time در هر فروش obligation میگیرد و دورهای settle میکند.**

## 6. DB Writes

- `orders` — new row (order_type=digital_trade, trade_side=buy)
- `order_items` — with price snapshot
- `wallet_ledger_entries` — credit XAU_MG to user's wallet in brand scope
- `asset_balances` — user's XAU_MG balance increased
- `payments` — gateway payment record

> Canonical schemas: [Order](../03-schema-index.md#11-order), [Wallet](../03-schema-index.md#2-wallet), [Payment](../03-schema-index.md#12-payment)

## 7. Treasury Impact

- `treasury_positions` += `amount_mg` (source=digital_buy) — single-leg ([D-67](../01-decisions-audit-log.md))
- Sign: **positive** (Goldis owes gold — open exposure)
- Central treasury applies even if payment went to TalaMala

## 8. Wallet Impact

- `asset_balances[user, scope, XAU_MG].current_balance_minor` += amount_mg
- `wallet_ledger_entries` — credit entry with scope isolation ([D-46](../01-decisions-audit-log.md))
- Scope: aminzar for AminZar brand, talamala for TalaMala brand, goldis for Goldis brand

## 9. Inter-Company Impact

**AminZar (Goldis-side):** No inter-company entries (payment_receiver == Goldis).

**TalaMala (non-Goldis):** 2 entries ([D-69](../01-decisions-audit-log.md)):
- TalaMala → Goldis, rial, P_hedge_per_mg × amount_mg
- Goldis → TalaMala, gold, amount_mg

Margin (user_price − P_hedge) stays with TalaMala.

> Canonical schema: [Inter-Company Ledger](../03-schema-index.md#4-inter-company-ledger)

## 10. Audit & Events

- `outbox_events`:
  - `DigitalGoldBought`
  - `TreasuryPositionOpened`
  - `InterCompanyObligationCreated` (if non-Goldis)
  - `WalletCredited`

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Treasury cap exceeded | Reject trade |
| Price lock expired | Reject, user must re-lock |
| Gateway payment fails | No wallet credit, Order → PaymentFailed |
| KYC limit exceeded | Reject trade |

## 12. Invariants

- Wallet scope isolation: aminzar ≠ goldis even though both map to شرکت گلدیس ([D-46](../01-decisions-audit-log.md))
- Digital buy in non-Goldis scope is equivalent to physical sale for hedging ([D-69](../01-decisions-audit-log.md))
- Treasury is always single-leg for digital_buy ([D-67](../01-decisions-audit-log.md))
- Inter-company uses P_hedge, not user price, not internal_base_price ([D-65](../01-decisions-audit-log.md))

## 13. Related References

- [Domain Models — Wallet](../02-domain-models.md#۴-مدل-wallet-per-wallet-scope)
- [Domain Models — Inter-Company](../02-domain-models.md)
- [Schema: Wallet](../03-schema-index.md#2-wallet) | [Order](../03-schema-index.md#11-order)
- [API: Wallet](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-46](../01-decisions-audit-log.md), [D-47](../01-decisions-audit-log.md), [D-65](../01-decisions-audit-log.md), [D-67](../01-decisions-audit-log.md), [D-69](../01-decisions-audit-log.md)
