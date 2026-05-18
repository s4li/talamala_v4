# Decision Framework: v2.7 — Closing Critical Gaps
**Date:** 2026-05-18  
**Prepared for:** Stakeholder alignment before finalizing spec v2.4  
**Status:** Awaiting decisions on 4 architectural issues

---

## TL;DR — 4 Critical Gaps Found by Jaminy

The v2.4 spec is **detailed and well-structured**, but it has **4 architectural voids** that would cause **production failures**. These are not typos or clarity issues—they're missing subsystems.

Each gap requires a **design decision** before implementation can proceed. Below is the framework for those decisions.

---

## GAP 1: Price Lock Deadlock (BLOCKER) 🔴

### The Problem
1. Customer sees product price = **100 ریال**
2. Payment lock expires (5 min) before checkout completes (network delay, customer goes AFK)
3. Price is now **120 ریال**, but customer already authorized 100 ریال
4. System **forbids refunds** (D-31: "no refunds, only buyback")
5. **Money is trapped** — can't refund, can't fulfill order, can't adjust invoice

### Why It Matters
- iranians bank transfers via **SADAD/SEPEHR** are **non-reversible** — once Goldis' account receives money, reversal requires **manual intervention + customer bank approval** (can take days)
- If price lock fails, system cannot recover without violating D-31

### What's Missing
A **Payment Reconciliation** subsystem:
- **Reconciliation Window**: Allow small price variance (e.g., ±2 ريال) for payment approval
- **Treasury Rebalancing**: If price rises after payment received, treasury covers the difference; if price drops, profit goes to treasury
- **Payment Hold Queue**: Don't finalize ledger until reconciliation approves
- **Manual Review Dashboard**: ادمین can see stuck payments, approve/reject with reason

### Decision Needed
**Q: Should v1 support price-variance reconciliation, or lock payment = instant final until v2?**

| Option | Impact | Effort |
|--------|--------|--------|
| A. Price variance (±2%): accept, reconcile automatically | Safe, realistic | 2 days: new endpoint + reconciliation job |
| B. Price lock = instant final (no flexibility) | Risky: might strand payments | 0 days: spec only, no code change |
| C. Manual reconciliation only: admin reviews each case | Safe but slow | 3 days: dashboard + email alerts |

**Recommendation:** A (auto-reconcile ±2%) — Iranian banking reality requires flexibility

---

## GAP 2: Treasury Exposure Race Condition (HIGH) 🟠

### The Problem
1. Exposure cap = **100 کیلوگرم** (system setting)
2. Two customers **simultaneously** place orders for 60 کیلوگرم each
3. Both pass the check: `treasury.balance - order_weight < cap` (100 - 60 = OK, 100 - 60 = OK)
4. Both orders **finalize simultaneously**
5. Treasury is now **-20 کیلوگرم short** (negative balance)

### Why It Matters
- §10.1 (Treasury Exposure) is a **safety rule** — exceeding it means we're **short on physical gold** (hedge/broker hasn't delivered yet)
- Concurrent orders can collectively bypass the rule because the check happens **before** the DB `UPDATE` is committed

### What's Missing
A **Pending Exposure** reservation system:
- Reserve (lock) metal on **checkout**, not on **payment finalization**
- Two customers each reserve 60 کیلوگرم → first succeeds, second fails (or waits in queue)
- Final ledger entry only happens if reserve is still valid at payment

### Decision Needed
**Q: Should v1 use optimistic locking (check + update atomically) or pessimistic locking (reserve on checkout)?**

| Option | Impact | Effort |
|--------|--------|--------|
| A. Optimistic: Increase PRAGMA `SERIALIZABLE` isolation on treasury table | Simplest, DB handles it | 0.5 days: alter table constraints |
| B. Pessimistic: `inventory_pending_holds` table reserves metal on checkout | Flexible, customer can see reservation | 2 days: new table + logic |
| C. Manual queue: Orders queue if cap exceeded; admin approves when hedge arrives | Safe but UX friction | 1.5 days: UI + email |

**Recommendation:** B (pessimistic reserve on checkout) — Aligns with D-62 (inventory stages) and gives customers visibility

---

## GAP 3: Orphaned Payment Risk (HIGH) 🟠

### The Problem
1. Customer payment verified by **Zibal/Sepehr/etc** ✅
2. Gateway sends callback: `PaymentVerified` event
3. **System crashes** (or DB connection drops) **before** we write `inter_company_ledger` entry
4. Payment is logged in **bank statement** but **not in Goldis ledger**
5. Customer or auditor sees: Money left their account, but Goldis shows zero gold owed

### Why It Matters
- **Iranian banking audits** will flag this — mandatory **statement reconciliation** (تطابق حساب)
- If this happens repeatedly, Goldis' books fail audit or requires manual reconciliation every month

### What's Missing
A **Payment State Machine** with idempotent recovery:
- State: `Gateway_Verified_But_Order_Pending` (intermediate state)
- If system crashes, **recovery job** on startup: "Replay all unfinalized payments"
- Idempotency key on `inter_company_ledger` prevents double-entry

### Decision Needed
**Q: Should v1 have automatic recovery or manual dashboard?**

| Option | Impact | Effort |
|--------|--------|--------|
| A. Auto-recovery: Startup job replays missed payments, idempotent inserts | Safe, invisible to user | 1.5 days: recovery job + idempotency |
| B. Manual review: Dashboard lists unfinalized payments, ادمین approves | Safe but requires vigilance | 1 day: UI only |
| C. Both: Recovery job + alerts if replay fails | Safest | 2 days |

**Recommendation:** A + B (auto-recovery + alerts) — Iranian banking requires both safety and audit trail

---

## GAP 4: POS Offline Reconciliation (MEDIUM) 🟡

### The Problem
1. Dealer POS (small device, e.g., mobile) charges card via gateway ✅
2. **WiFi drops** before device sends `POST /api/pos/confirm`
3. Device tries to reconnect for 10 minutes, then times out
4. Dealer manually closes app
5. **System state**: Order is `pending` (not confirmed), gold has been reserved, but customer was charged
6. No clear way to recover: recharge = double charge, ignore = customer angry

### Why It Matters
- **Small dealer shops** (غرفه‌های بازار) often have **poor connectivity** (shared WiFi, 3G dropouts)
- If POS goes offline 2-3 times per week, support tickets spike

### What's Missing
A **POS Offline Queue** with **eventual consistency**:
- POS stores `POST /api/pos/confirm` requests **locally** if network fails
- On reconnect, device retries (idempotent) with unique `request_id`
- **Server-side idempotency**: `payment_ref` + `request_id` ensures single order even if retry fires twice
- **UI**: Dealer sees "⏳ Pending upload" badge; can manually retry or view local queue

### Decision Needed
**Q: Should v1 have offline queue or require online-only POS?**

| Option | Impact | Effort |
|--------|--------|--------|
| A. Offline-first POS: Local SQLite queue + retry logic + idempotency | Robust, better UX | 3 days: POS logic + server idempotency |
| B. Online-only: POS must have network; if offline, reject sale | Simpler | 0 days: document requirement |
| C. Hybrid: Online preferred, but cache last N sales locally for retry only | Good balance | 2 days |

**Recommendation:** A (offline-first) — Iranian connectivity is unreliable; dealers need this

---

## Impact on v2.4 → v2.7 Timeline

### Option 1: Fast v1 MVP (Skip All 4)
- Release v2.4 **as-is**, implement v1 without these subsystems
- **Risk**: Price deadlock + race conditions + orphaned payments = support load, audit issues
- **Effort**: 0 days extra

### Option 2: Robust v1 (Implement All 4)
- Decisions on each gap → v2.7 spec → implementation
- **Risk**: Delayed release (2-3 weeks)
- **Effort**: 6-8 days design + code

### Option 3: Hybrid (Implement 1+2+3, Skip 4)
- Address payment safety + treasury consistency (critical)
- POS offline support deferred to v1.1
- **Risk**: POS dealers might experience double-charge scenarios
- **Effort**: 4-5 days

---

## Recommended Path Forward

### 1. **Jaminy Decision Meeting** (30 min)
Answer for each gap:
- **Gap 1 (Price Lock)**: A (auto-reconcile ±2%) or B (lock = final)?
- **Gap 2 (Treasury Race)**: A (optimistic) or B (pessimistic) or C (queue)?
- **Gap 3 (Orphaned Payment)**: A (auto-recovery) or B (manual) or both?
- **Gap 4 (POS Offline)**: A (offline queue) or B (online only) or C (hybrid)?

### 2. **Create v2.7 Spec** (1-2 days)
- For each "A" or "B" decision, add:
  - New sections (e.g., §14.1: Payment Reconciliation)
  - New tables/endpoints
  - New state machines / workflows
  - Decision log entries (D-90 through D-93)

### 3. **Implementation** (4-6 days)
- Design review with Jaminy
- Implement subsystems in order: Payment > Treasury > Idempotency > POS
- Integration tests for each

### 4. **v1 Launch** (May 2026)
- Go live with decided subset
- Mark remaining as "v1.1 roadmap"

---

## Next Step

**Jaminy**: Please respond with your decision on each gap (A / B / C) and the desired release timeline.

**Claude Code**: Once decisions are made, I will:
1. Generate v2.7 spec with new sections + endpoints
2. Update CLAUDE.md with new subsystems
3. Create implementation plan with test cases
