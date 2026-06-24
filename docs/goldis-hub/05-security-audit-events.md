# Security, Compliance, Audit & Events — Goldis Hub v2.7

> **Canonical home for authentication, authorization, compliance, audit, and event specifications.**
> Related schemas: [outbox_events, audit_logs](03-schema-index.md#13-outbox--audit)

---

## ۱۷. Security, Compliance, Audit

### Authentication
- JWT access (TTL=15min) + refresh (TTL=30d in DB)
- Bearer header، یا httpOnly cookie برای web frontend
- POS device: API key با hash در DB
- Marketplace adapters: device/service credentials جدا

### Authorization (RBAC + ABAC)
- Roles: `super_admin`, `admin`, `operator`, `accountant`, `warehouse`, `pricer`, `dealer`
- Permission keys hierarchical: `view < create < edit < full`
- ABAC: `accountant` فقط می‌تواند settlement خودش (company-bound) را تأیید کند
- Route protection: `Depends(require_permission("settlement", level="approve"))`

### Segregation of Duties (SoD — اجباری، D-107)
- maker ≠ checker روی همه‌ی workflowهای dual-control اجباری است: گارد سراسری لایه‌ی app `if maker_id == checker_id: raise` روی transfer/buyback/withdrawal **قبل** از هر منطق approval.
- `inventory_transfer_documents`: `CHECK(dispatched_by IS NULL OR received_by IS NULL OR dispatched_by <> received_by)`.
- trio بازخرید (`received_by`/`verified_by`/`approved_by`): نقش‌های متوالی نباید یک `user_id` باشند (گارد لایه‌ی app، قبل از approval).
- `super_admin` از actor بودن در گام‌های تأیید مالی **منع** می‌شود (bypass permission ≠ bypass SoD).
- گزارش کارآگاهی دوره‌ای روی `audit_logs` برای same-actor-both-halves و same-device.

### Idempotency
- Header `Idempotency-Key` در همه‌ی POST تغییردهنده الزامی
- ذخیره: یا در جدول `idempotency_keys` با TTL=۲۴h، یا در ستون idempotency_key entity (پیشنهاد دوم: سادهتر)

### Rate limiting
- `slowapi` (in-memory) برای فاز ۱، بعدا Redis-backed
- مخصوصا سختگیر روی: `/auth/send-otp` (۳/min)، `/payments/start`، `/wallet/trades/*`، `/withdrawals/*` (۱۰/min به ازای هر کاربر)

### Shahkar integration
- sub-module `kyc.shahkar`:
  - `verify(mobile, national_id) → ShahkarResult`
  - Cache result for ۳۰ روز
  - Re-verify اگر `national_id` تغییر کرد

### Audit
- هر action با priority بالا → audit_logs.insert در همان transaction
- لیست actions الزامی: تغییر قیمت، manual override، inventory adjustment، wallet adjustment manual، تغییر KYC level/limits، تأیید/رد withdrawal ریال، cancel treasury position (تغییر status از open به cancelled)، **inter-company settle (rial/gold)**، buyback (digital و physical)، تغییر role/permission، sync دستی marketplace، تغییر mapping، تغییر payment_account، inventory_movement بین انبارها (مثلا تحویل طلای خام از Goldis به TalaMala برای hedging)
- audit_logs **INSERT ONLY** — DB grant level: `REVOKE UPDATE, DELETE ON audit_logs FROM app_user`

### Payment callback security
- Signature verification اگر provider پشتیبانی کند (Sepehr/Parsian)
- Replay prevention: idempotency_key + در DB ذخیره می‌شود

### Frontend security
- CORS: only configured domains به ازای هر کانال
- CSP headers
- SameSite cookies برای web

---

---

## ۱۴. Outbox Pattern و Events

### الگو

هر transaction که دادهی حساس را تغییر می‌دهد → outbox_events entry در **همان transaction**. publisher worker جدا فالو میکند.

```python
async def mark_order_paid(self, order_id: UUID, payment_id: UUID):
    async with self.uow.begin():
        order = await self.repo.get_for_update(order_id)
        if order.status == OrderStatus.Paid:
            return
        await self.inventory_svc.consume_reservation(order)
        # D-77: create_task اینجا صدا زده نمی‌شود — task فقط هنگام
        #   «درخواست تحویل» ساخته می‌شود (فروش امانی task ندارد).
        #   استثنا: تحویل فوری POS/فروشگاه → همانجا create_task(order_item, bar).
        await self.treasury_svc.finalize_from_hold(order)   # D-101/D-105: hold → treasury_position؛ چک سد سخت قبلاً موقع checkout زیر advisory lock انجام شده
        # D-06b/D-69: settlement_svc حذف شد. اگر فروش غیر-Goldis:
        if order.payment_receiver_company_id != GOLDIS_ID:
            await self.inter_company_svc.record_obligations(order)  # جفت rial(P_hedge)+gold
        await self.accounting_svc.record_event(order)

        events = [
            ("OrderPaid", "Order", str(order.id), {...}),
            ("TreasuryPositionOpened", ...),
            ("AccountingEventCreated", ...),
        ]
        if order.payment_receiver_company_id != GOLDIS_ID:
            events.append(("InterCompanyObligationCreated", ...))
        await self.outbox.enqueue(events)
        order.status = OrderStatus.Paid   # D-103: order.Paid آخرین mutation، بعد از outbox.enqueue، در همان tx اتمیک
        order.paid_at = utcnow()
        # commit در پایان context
        # نکته: FulfillmentTaskCreated اینجا منتشر نمی‌شود (D-77)
```

### Eventهای اصلی

```
# Identity / KYC
UserRegistered, UserKycSubmitted, UserKycApproved, UserKycRejected, UserLevelChanged

# Pricing
PriceSourceFetched, PriceSourceFailed, InternalBasePriceChanged,
PriceLockCreated, PriceLockExpired

# Inventory
InventoryReserved, InventoryReleased, InventoryConsumed, InventoryTransferred

# Order
OrderCreated, OrderPaid, OrderReservationExpired

# Payment
PaymentStarted, PaymentVerified, PaymentFailed

# POS
PosTransactionImported, PosOrderCreated

# Wallet
WalletCredited, WalletDebited, WalletLocked, WalletUnlocked,
WalletToppedUp, WalletTopupFailed

# Trade
DigitalGoldBought, DigitalGoldSold

# Buyback (دو حالت — بازخرید دیجیتال = DigitalGoldSold)
BuybackCompleted,                                    # (a) بازخرید تحویل‌نشده (آنلاین)
PhysicalBuybackRequested, PhysicalBuybackReceived,   # (b) physical state machine
PhysicalBuybackVerified, PhysicalBuybackApproved,
PhysicalBuybackCompleted, PhysicalBuybackRejected,

# Withdrawal (فقط ریالی — D-31)
WithdrawalRequested, WithdrawalApproved, WithdrawalRejected,
WithdrawalCompleted, WithdrawalFailed

# Treasury
TreasuryPositionOpened, TreasuryPositionCancelled, TreasuryThresholdReached

# Inter-Company Ledger (بخش ۶)
InterCompanyObligationCreated,     # موقع sale (gold یا rial)
InterCompanyRialSettled,           # اپراتور cash transfer رو تأیید کرد
InterCompanyGoldSettled,           # اپراتور تحویل طلا رو تأیید کرد
InterCompanyObligationCorrected    # فقط برای admin correction (D-59: buyback obligation reverse نمیکند)

# فرایند تحویل کالا
FulfillmentTaskCreated, FulfillmentTaskAssigned, FulfillmentTaskCompleted

# Marketplace
ExternalOrderFetched, ExternalOrderImported, ExternalOrderFailed,
ChannelInventoryPushed, ChannelPricePushed

# Notification
NotificationDispatched, NotificationFailed

# Audit
AuditEntryCreated
```

### Subscriber registry (in-process در فاز ۱)

```python
EVENT_HANDLERS: dict[str, list[Callable]] = {
    "OrderPaid": [
        notification_service.handle_order_paid,
        accounting_service.handle_order_paid,
        realtime_broadcaster.broadcast_user_order,
    ],
    "TreasuryThresholdReached": [
        notification_service.alert_admins,
    ],
    # ...
}
```

---

