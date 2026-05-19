# Flow 09 — Rial Wallet Topup

> **Source:** §12.5.4 — شارژ wallet ریالی (Rial Topup) — اتومات، بدون اپراتور

---

## 1. Goal

Customer charges their IRR wallet via payment gateway. Fully automatic — no operator approval needed.

## 2. Actors

- **Customer** (authenticated)
- **Brand website** (determines wallet scope)
- **Payment gateway** (IPG of the channel's payment account)

## 3. Preconditions

- Customer is authenticated
- Amount is positive
- Channel is active with a valid payment account

## 4. Trigger

`POST /api/v1/wallet/topup` with `{ amount_rial }` and `X-Channel-Code` header.

## 5. Steps

```
1. User → POST /api/v1/wallet/topup
   Header: X-Channel-Code=<channel>
   Body: { amount_rial }
   • Backend resolves: فرانت/کانال → wallet_scope (D-76/D-46)
     (طلاملا→scope=talamala، گلدیس→scope=goldis، امینزر→scope=aminzar)
     ⚠️ سه scope کاملا ایزوله؛ امینزر merge در goldis نمی‌شود
     (هرچند legal entity هر دو شرکت گلدیس و درگاهش Goldis IPG است)
   • resolve payment_account: همان payment_account default channel
2. Backend:
   - INSERT wallet_topups (status=created)
   - Payment.create(amount=amount_rial, type=topup)
   - Payment.start → redirect URL gateway
3. کاربر → gateway → پرداخت → callback
4. Payment.callback (idempotent):
   - Payment.verify
   - if verified:
     • Wallet.credit(user, wallet_scope, IRR, amount_rial, ref=topup)
     • UPDATE wallet_topups status=completed
     • Audit + Outbox: WalletToppedUp
     • Notification
   - if failed:
     • UPDATE wallet_topups status=failed
     • Notification (با تلاش مجدد)
```

**نکته:** هیچ Treasury impact ندارد (پول می‌آید، تعهد طلایی تغییری نمیکند). فقط Accounting event ثبت می‌شود.

## 6. DB Writes

- `wallet_topups` — new row (status: created → completed/failed)
- `payments` — gateway payment record
- `wallet_ledger_entries` — credit IRR to user's wallet
- `asset_balances` — user's IRR balance increased

> Canonical schemas: [Payment (wallet_topups)](../03-schema-index.md#12-payment), [Wallet](../03-schema-index.md#2-wallet)

## 7. Treasury Impact

**None.** Rial topup has no gold exposure change. Only an accounting event is recorded.

## 8. Wallet Impact

- `asset_balances[user, scope, IRR].current_balance_minor` += amount_rial
- `wallet_ledger_entries` — credit entry with reference_type=topup
- Scope determined by channel: talamala → talamala scope, goldis → goldis scope, aminzar → aminzar scope ([D-76](../01-decisions-audit-log.md), [D-46](../01-decisions-audit-log.md))

## 9. Inter-Company Impact

**None.** Topup is a simple rial deposit — no obligations between companies.

## 10. Audit & Events

- `outbox_events`:
  - `WalletToppedUp` (on success)
  - `WalletTopupFailed` (on failure)
  - `PaymentVerified` / `PaymentFailed`

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Gateway payment fails | wallet_topups.status = failed, notification with retry option |
| Gateway timeout | Same as fail — idempotent callback handles late verification |
| Duplicate callback | Idempotent — payment already verified, no double-credit |

## 12. Invariants

- Scope isolation: topup credits ONLY the scope matching the channel ([D-46](../01-decisions-audit-log.md))
- AminZar topup goes to aminzar scope (NOT merged into goldis) even though both use Goldis IPG
- No operator approval needed — fully automatic
- Idempotent callback — duplicate verification is safe
- `wallet_topups.idempotency_key` is scope-keyed: `(wallet_scope, user_id, idempotency_key)` ([P0-1.1](../01-decisions-audit-log.md))

## 13. Related References

- [Flow 10 — Rial Withdrawal](10-rial-withdrawal.md) (reverse flow — IRR out)
- [Schema: Payment (wallet_topups)](../03-schema-index.md#12-payment) | [Wallet](../03-schema-index.md#2-wallet)
- [API: Wallet](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-46](../01-decisions-audit-log.md), [D-76](../01-decisions-audit-log.md)
