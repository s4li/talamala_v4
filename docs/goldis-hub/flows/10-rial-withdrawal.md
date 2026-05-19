# Flow 10 — Rial Withdrawal

> **Source:** §12.6 — برداشت ریال
> Note: Only rial withdrawal exists. Gold withdrawal was removed ([D-31](../01-decisions-audit-log.md)) — use [Flow 04](04-physical-purchase-from-wallet.md) instead.

---

## 1. Goal

Customer withdraws IRR from their wallet to a verified bank account. Requires operator approval (all withdrawals in v1).

## 2. Actors

- **Customer** (authenticated, has IRR balance)
- **Operator** (Goldis ops center, role=operator or higher, permission `withdrawal:approve`)
- **Payout system** (bank API transfer)

## 3. Preconditions

- Customer has sufficient IRR balance in the specified wallet scope
- Customer has a verified bank account (`user_bank_accounts`)
- KYC limits: daily/monthly rial withdrawal limits

## 4. Trigger

`POST /api/v1/withdrawals/rial` with `{ from_wallet, amount_rial, bank_account_id }`.

## 5. Steps

```
1. User → /api/v1/withdrawals/rial
   { from_wallet: Goldis, amount_rial, bank_account_id }
2. KYC + Wallet.check_balance(Goldis, IRR)
3. Wallet.lock(Goldis, IRR, amount)
4. Order.create(order_type=withdrawal_rial, status=WithdrawalRequested)
   + INSERT withdrawal_details (bank_account_id)
5. اپراتور (admin_role=operator) در پنل ادمین → POST /api/v1/admin/withdrawals/{id}/approve
   → status=OperatorApproved
6. Payout worker → Goldis bank API (یا TalaMala bank API برای from_wallet=TalaMala)
7. on success:
   - Wallet.consume_lock
   - status=Completed
   - Audit + Notification
8. on fail:
   - Wallet.release_lock
   - status=Failed
   - Notification (با تلاش مجدد یا تماس)
```

> **نکته:** برای v1، **همه‌ی** برداشتها نیاز به تأیید اپراتور دارند (تصمیم تیم). در آینده می‌توان آستانه‌ی مبلغ تعریف کرد که زیرش auto-approve باشد.

## 6. DB Writes

- `orders` — order_type=withdrawal_rial, status tracks state machine
- `withdrawal_details` — bank_account_id, payout tracking, operator decision
- `wallet_locks` — IRR lock created, then consumed or released
- `wallet_ledger_entries` — debit IRR (on success)
- `asset_balances` — IRR decreased (on success)

> Canonical schemas: [Order (withdrawal_details)](../03-schema-index.md#11-order), [Wallet](../03-schema-index.md#2-wallet)

## 7. Treasury Impact

**None.** Rial withdrawal has no gold exposure change.

## 8. Wallet Impact

- `wallet_locks` — IRR locked at request time
- On approve + payout success: lock consumed, balance decreased
- On reject / payout fail: lock released, balance unchanged
- Uses `withdrawable_balance` (excludes credit_limit — [D-46](../01-decisions-audit-log.md))

## 9. Inter-Company Impact

**None.** Rial withdrawal is a direct payout from the brand's bank account to customer. No obligations between companies.

## 10. Audit & Events

- `audit_logs`: withdrawal request, operator approve/reject (mandatory — sensitive action)
- `outbox_events`:
  - `WithdrawalRequested`
  - `WithdrawalApproved` / `WithdrawalRejected`
  - `WithdrawalCompleted` / `WithdrawalFailed`

> Canonical event list: [Events](../05-security-audit-events.md)

## 11. Failure Cases

| Failure | Handling |
|---------|----------|
| Insufficient IRR balance | Reject request |
| KYC withdrawal limit exceeded | Reject request |
| Bank account not verified | Reject request |
| Operator rejects | Lock released, status=Rejected, notification |
| Payout API fails | Lock released, status=Failed, notification with retry/contact |
| Concurrent withdrawal drains balance | Lock mechanism prevents over-withdrawal |

## 12. Invariants

- All withdrawals require operator approval in v1 — no auto-approve
- Gold withdrawal does NOT exist ([D-31](../01-decisions-audit-log.md)) — use physical purchase from wallet instead
- Lock → approve → consume pattern: atomic, prevents over-withdrawal
- `withdrawable_balance = balance - locked - credit` (credit_limit NOT included for withdrawals)
- Payout goes to the bank API matching the wallet scope (Goldis bank for goldis scope, TalaMala bank for talamala scope)

## 13. Related References

- [Flow 09 — Rial Wallet Topup](09-rial-wallet-topup.md) (reverse flow — IRR in)
- [Flow 04 — Physical Purchase from Wallet](04-physical-purchase-from-wallet.md) (gold "withdrawal" as product purchase)
- [Schema: Order (withdrawal_details)](../03-schema-index.md#11-order) | [Wallet](../03-schema-index.md#2-wallet)
- [API: Withdrawal](../04-api-index.md)
- [Reference: Finance/Wallet/Treasury](../references/finance-wallet-treasury-ledger.md)
- Decisions: [D-31](../01-decisions-audit-log.md), [D-46](../01-decisions-audit-log.md)
