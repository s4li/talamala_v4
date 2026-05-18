# TalaMala v5 Architecture Spec v2.7 — Review Package
**Date:** 2026-05-18  
**Status:** Ready for external review (Gemini, ChatGPT, DeepSeek)  
**Primary Focus:** 4 critical subsystems for production financial safety

---

## 📋 Executive Summary for Reviewers

### What This Is
**v2.7** adds **4 architectural subsystems** to solve critical financial & operational risks found during v2.6 bake-off:

1. **D-90: Payment Reconciliation** — Handle price changes mid-checkout without violating no-refund policy
2. **D-91: Pending Reserves** — Prevent concurrent orders from bypassing treasury exposure cap
3. **D-92: Payment State Machine** — Recover from system crashes that orphan payments after gateway approval
4. **D-93: POS Offline Queue** — Support offline POS devices without data loss or inconsistency

### Why Now
- **Gemini analysis** identified 3 production blockers (price deadlock, race condition, orphaned payment)
- **Iranian banking reality:** Non-reversible SADAD transfers + unreliable connectivity require these subsystems
- **These are NOT polish features** — they are foundational for v1 correctness

### Design Philosophy
- **Pessimistic locking** (D-91): Prevent problems before they happen
- **State machines** (D-92): Make payment lifecycle explicit and recoverable
- **Idempotency** (D-92, D-93): Every operation is safely retryable
- **Async + eventual consistency** (D-92, D-93): Don't block user on IO
- **Manual override** (D-90, D-93): Admin can always intervene for edge cases

---

## 📂 Files to Review (In Order)

### 1. **talamala_v5_architecture_spec.md** (v2.7) — PRIMARY
Location: `/talamala_v4/talamala_v5_architecture_spec.md`

**Sections to focus on:**
- §0.0: Read first (context for reviewers)
- §0.1: Known open items (not related to v2.7)
- **§14.0 – §14.4:** The 4 subsystems (NEW — ~400 lines)
  - §14.1: D-90 Payment Reconciliation
  - §14.2: D-91 Pending Reserves
  - §14.3: D-92 Payment State Machine
  - §14.4: D-93 POS Offline Queue
- §2.5 (Decision Log): D-90 through D-93 entries
- §21 (Roadmap): Integration into Phase 1-4

### 2. **SPEC-v2-7-SUMMARY.md** — QUICK START
Location: `/talamala_v4/SPEC-v2-7-SUMMARY.md`

**What it contains:**
- 1-page table comparing 4 gaps → solutions
- Implementation order
- New endpoints (admin + POS)
- New database tables (schemas)
- Testing checkpoints
- Key decisions highlighted

### 3. **DECISION-FRAMEWORK-v2-7.md** — CONTEXT
Location: `/talamala_v4/DECISION-FRAMEWORK-v2-7.md`

**What it contains:**
- Why each gap is critical
- Multiple options for each (A/B/C) with tradeoffs
- Why specific options were chosen in v2.7
- Effort estimates

---

## 🎯 Specific Questions for Reviewers

### For Each Subsystem:

#### D-90: Price Reconciliation
**Please verify:**
- [ ] ±2% auto-approval threshold is reasonable for Iranian market (consider price volatility)
- [ ] `payment_reconciliations` table design is complete (no missing fields for audit trail?)
- [ ] Treasury adjustment logic (`variance_rial` split) doesn't create new holes
- [ ] Admin manual review process (GET → POST approve/reject) is operationally feasible
- [ ] Alternative: Should we allow **dynamic threshold per asset** (gold ±2%, silver ±1.5%)?

**Edge cases to consider:**
- Concurrent reconciliation requests for same payment
- Treasury goes negative mid-reconciliation — rollback safe?
- Large variance (e.g., 50%) → admin rejects → trigger buyback → refund path clear?

#### D-91: Pending Reserves
**Please verify:**
- [ ] Reserve on checkout + finalize on payment is **atomic safe** (can payment fail after reserve locked?)
- [ ] `inventory_pending_holds` enforces **one hold per order** (no duplicate reserves)
- [ ] Release logic on order cancel is **idempotent** (safe to call multiple times?)
- [ ] Check: `treasury.balance >= threshold + sum(pending)` happens atomically with `SELECT FOR UPDATE`?
- [ ] What if pending hold expires (24h timeout)? Auto-release or manual?

**Edge cases:**
- Customer pays with card → payment fails → hold released → customer immediately re-orders with same hold ID (race)
- Checkout reserves 60kg, payment processes, concurrent checkout reserves 40kg (total 100kg+) — race?
- Treasury cap changes mid-transaction — which value applies?

#### D-92: Payment State Machine
**Please verify:**
- [ ] State transitions are **linear and monotonic** (never go backward, e.g., `finalized` → `pending` is forbidden)
- [ ] Idempotency key is **globally unique** per payment (not just per user)
- [ ] Recovery job runs **on every startup** (not just once)
- [ ] Async ledger creation has **exponential backoff + max retries** (doesn't spam DB on failure)
- [ ] `gateway_verified_pending` → `inter_company_ledger_created` transition is **atomic** (IntegrityError on duplicate idempotency_key is caught and safely ignored)
- [ ] Manual recovery endpoint allows admin to **force transition** if recovery job stuck?

**Edge cases:**
- Payment verified, idempotency_key collision on ledger creation (concurrent callbacks) — handled gracefully?
- Recovery job runs while async job is in-flight (same payment) — double-processing?
- Gateway sends 2 callbacks for same payment (network duplicate) — idempotency prevents double ledger?

#### D-93: POS Offline Queue
**Please verify:**
- [ ] **Device-side:** Local SQLite queue is **optional** (POS must gracefully degrade if SQLite unavailable)
- [ ] **Server-side:** Idempotency key is `(dealer_id, pos_session_id, request_id)` — **unique per device**, not global
- [ ] **Expiry:** 24-hour TTL on pending requests — is this long enough? Too long?
- [ ] **Manual retry:** Admin can force-retry or discard for stuck requests — what happens to customer refund?
- [ ] **Sync UI:** Device shows "⏳ Pending" badge + queue count — is this UX sufficient?

**Edge cases:**
- Device session crashes → new session ID → old pending requests orphaned (24h wait?)
- Customer paid, device offline, dealer force-discards request after 10min → customer charged but no order (support load)
- Two devices with same `dealer_id` but different `pos_session_id` send overlapping requests — both processed (double-sale)?

---

## 🔍 Architectural Review Checklist

### Design Soundness
- [ ] All 4 subsystems **avoid silent data loss** (no unlogged failures)
- [ ] All 4 use **idempotency keys** where applicable (safe to retry without duplication)
- [ ] All 4 have **manual override paths** (admin can always intervene)
- [ ] **No new bottlenecks** (none of the new tables/endpoints are on hot path for every order)

### Iranian Banking Constraints
- [ ] D-90: **No blind refunds** — treasury adjustment only, or buyback trigger? ✅
- [ ] D-92: **Async settlement is acceptable** — no requirement for instant finality? ✅
- [ ] D-93: **Eventual consistency OK** — offline device can settle hours later? ✅
- [ ] All: **Audit trail complete** — every change logged for month-end reconciliation? ✅

### Implementation Feasibility
- [ ] New tables are **schema-only, no data migration** from v4 (fresh v5 start per D-23)
- [ ] New endpoints are **admin-only** (no customer-facing changes, backward compatible)
- [ ] New flows are **pure software** (no hardware/third-party dependencies outside scope)
- [ ] Estimated effort **4-6 weeks** for all 4 (D-90, D-91, D-92, D-93) reasonable?

### Testing Requirements
- [ ] Each subsystem has **clear acceptance criteria** (testable without fuzzing)
- [ ] **No implicit timing assumptions** (e.g., "wait 1 sec, then check" is fragile)
- [ ] **Failure paths are testable** (can simulate crash, network dropout, etc.)

---

## 🚀 Recommended Review Order

1. **Read §0.0** (context for this review)
2. **Skim SPEC-v2-7-SUMMARY.md** (1 page, understand 4 solutions at high level)
3. **Deep-dive §14.1 – §14.4** in main spec (flows, schemas, endpoints)
4. **Reference DECISION-FRAMEWORK-v2-7.md** as needed (context on why each decision)
5. **Use checklist above** to verify each subsystem
6. **Provide feedback:**
   - ✅ "All sound" → Ready for implementation
   - ⚠️ "Concern: [issue]" → Needs design adjustment before implementation
   - ❌ "Blocker: [issue]" → Cannot proceed until resolved

---

## 📊 Quick Stats

| Metric | Count |
|--------|-------|
| New database tables | 5 (`payment_reconciliations`, `inventory_pending_holds`, `payments.updated`, `pos_pending_requests`, `pos_device_queue_snapshots`) |
| New admin endpoints | 8 (reconciliations, recovery, POS queue) |
| New POS endpoint | 1 (confirm, enhanced with idempotency) |
| New state transitions | 5 (payment state machine) |
| Lines added to spec | ~400 |
| Decisions (D-90–D-93) | 4 |

---

## 🎓 Background Context (If Reviewers Are New)

### Why This Matters
- **Price Lock Deadlock (D-90):** Iranian SADAD transfers non-reversible. If system accepts payment then changes price, money is permanently stuck unless manual intervention.
- **Treasury Race (D-91):** Concurrent orders can collectively exceed exposure cap if checked independently. With 100+ dealers, race windows are frequent.
- **Orphaned Payment (D-92):** System crashes happen. Payment verified by bank but not recorded in books = monthly audit variance + potential loss.
- **POS Offline (D-93):** Small dealer shops in bazaars have unreliable WiFi. Device offline = lost sales, customer left hanging.

### What v2.6 Had (Before v2.7)
- Payment API was basic (no state machine, crash = loss)
- Treasury cap checked but not locked (race possible)
- No reconciliation (price mismatch = stuck money)
- POS design assumed always-online

### What v2.7 Adds
- Explicit state machine + recovery (D-92)
- Pessimistic locking (D-91)
- Automatic reconciliation + manual review (D-90)
- Offline-first POS with sync (D-93)

---

## 📞 Questions Before Sending to Reviewers?

If you want to clarify anything before external review, the key points are:

- **D-90:** Is ±2% auto-approve OK, or too generous?
- **D-91:** Is pessimistic locking the right tradeoff vs. optimistic?
- **D-92:** Is async recovery + exponential backoff acceptable for Iran?
- **D-93:** Is 24h TTL on offline requests reasonable?

---

**Prepared:** 2026-05-18  
**Version:** 2.7 (Final for v1 MVP)  
**Status:** 🟢 Ready for external review
