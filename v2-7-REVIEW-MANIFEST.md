# TalaMala v5 Spec v2.7 — Complete Review Manifest

**Date:** 2026-05-18  
**Version:** 2.7 (Final for v1 MVP)  
**Status:** ✅ Ready for external review

---

## 📦 Package Contents (Complete Checklist)

### Core Spec Document
- [x] `talamala_v5_architecture_spec.md` (v2.7)
  - [x] Updated version header (2.6 → 2.7)
  - [x] §0.0 "راهنمای داور" (guidance for external reviewers)
  - [x] §14.0 Introduction (why 4 subsystems matter)
  - [x] §14.1 D-90 Payment Reconciliation (400 lines, with schemas)
  - [x] §14.2 D-91 Pending Reserves (300 lines, with schemas)
  - [x] §14.3 D-92 Payment State Machine (300 lines, with schemas)
  - [x] §14.4 D-93 POS Offline Queue (300 lines, with schemas)
  - [x] §2.5 Decision Log: D-90, D-91, D-92, D-93 entries (4 entries)
  - [x] §21 Roadmap: Integration into Phase 1-4

### Supporting Documents for Review
- [x] `SPEC-v2-7-SUMMARY.md` (1-2 pages)
  - [x] Quick comparison table: 4 gaps → 4 solutions
  - [x] Implementation order with phases
  - [x] New endpoints (8 admin, 1 POS)
  - [x] New tables (5 total)
  - [x] Testing checkpoints
  
- [x] `SPEC-v2-7-REVIEW-PACKAGE.md` (Review Package)
  - [x] Executive summary (why this matters)
  - [x] Files to review (ordered)
  - [x] 🎯 Specific questions per subsystem (4 sections)
  - [x] Architectural checklist (design, banking, feasibility)
  - [x] Edge cases for each subsystem
  - [x] Recommended review order
  - [x] Quick stats table
  - [x] Background context

- [x] `DECISION-FRAMEWORK-v2-7.md` (Context)
  - [x] Problem statements (TL;DR)
  - [x] 3 options per gap (A/B/C) with tradeoffs
  - [x] Why v2.7 chose specific options
  - [x] Effort estimates
  - [x] Recommended paths

- [x] `REVIEW-INSTRUCTIONS.md` (For Reviewers)
  - [x] Step-by-step review process (5 steps)
  - [x] Timing estimates per step
  - [x] Verification checklist
  - [x] Feedback template (copy-paste ready)
  - [x] Focus areas by expertise (architect, engineer, payments, database)
  - [x] Common questions + answers
  - [x] Success criteria
  - [x] Contact info placeholder

### This Document
- [x] `v2-7-REVIEW-MANIFEST.md` (This file)
  - [x] Complete checklist of all items
  - [x] Verification of spec quality
  - [x] Commit history
  - [x] Instructions for sender

---

## ✅ Spec Quality Verification

### Content Verification
- [x] All 4 subsystems (D-90–D-93) documented with:
  - [x] Problem statement
  - [x] Root cause analysis
  - [x] Proposed solution with rationale
  - [x] SQL table schemas (CREATE TABLE)
  - [x] API endpoints (GET/POST with paths, params)
  - [x] State transitions / flows (pseudocode or narrative)
  - [x] Edge cases listed
  - [x] Integration with existing v5 model

### Architectural Quality
- [x] **No silent data loss:** All failures logged or retryable
- [x] **Idempotency:** D-90, D-92, D-93 use idempotency keys
- [x] **Manual override:** All subsystems have admin intervention paths
- [x] **No hot-path bottlenecks:** New tables not on critical path
- [x] **State machines explicit:** D-92 has clear linear transitions
- [x] **Async patterns:** D-92, D-93 use async with retry logic
- [x] **Audit trail:** All changes can be logged for compliance

### Iranian Banking Constraints
- [x] **No blind refunds:** D-90 uses treasury adjustment, not refund
- [x] **Async settlement OK:** D-92 uses eventual consistency
- [x] **Non-reversible transfers:** D-90 reconciliation handles this
- [x] **Offline resilience:** D-93 handles dropped connections
- [x] **Full audit trail:** All changes logged per §19

### Implementation Feasibility
- [x] **Schema only, no migrations:** Fresh v5 start per D-23
- [x] **Admin-only endpoints:** No customer-facing changes
- [x] **Pure software:** No external dependencies
- [x] **4-6 week estimate reasonable:** Based on subsystem complexity
- [x] **1-2 engineers feasible:** No parallel track dependencies

---

## 📋 Commit History (for Verification)

```
be87654 docs(v5): add §14 critical subsystems (D-90–D-93) for production safety
├─ Added §14.0–14.4 (1200+ lines of schemas, flows, endpoints)
├─ Updated §2.5 Decision Log with D-90–D-93
├─ Bumped version 2.6 → 2.7
└─ Updated header with new focus

01733b4 docs: add v2.7 summary & decision framework for 4 critical subsystems
├─ Created SPEC-v2-7-SUMMARY.md (1 page quick ref)
├─ Created DECISION-FRAMEWORK-v2-7.md (context + options)
└─ Ready for external review

978935b docs: note v2.7 spec ready (4 critical subsystems added)
└─ Updated CLAUDE.md with v2.7 status notice
```

All commits include proper attribution: `Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>`

---

## 🚀 To Send for External Review

### Bundle Contents (Send All 5 Files)
```
talamala_v5_architecture_spec.md (v2.7) — PRIMARY
├─ SPEC-v2-7-SUMMARY.md
├─ SPEC-v2-7-REVIEW-PACKAGE.md
├─ DECISION-FRAMEWORK-v2-7.md
└─ REVIEW-INSTRUCTIONS.md
```

### Sender's Intro (Suggested)
```
Dear [Reviewer],

We've completed TalaMala v5 architecture v2.7, which adds 4 critical subsystems 
for production financial safety:

- D-90: Payment Reconciliation (handle price lock deadlock)
- D-91: Pending Reserves (prevent treasury race condition)
- D-92: Payment State Machine (recover from crashes)
- D-93: POS Offline Queue (support offline devices)

Please review the attached documents in this order:
1. SPEC-v2-7-REVIEW-PACKAGE.md (5 min intro)
2. SPEC-v2-7-SUMMARY.md (1 page quick ref)
3. talamala_v5_architecture_spec.md §14 (30–60 min deep dive)
4. Use REVIEW-INSTRUCTIONS.md template for feedback

Your review should take 1–2 hours total. Please assess:
- Is each subsystem architecturally sound?
- Do they respect Iranian banking constraints?
- Are they implementable in 4-6 weeks?
- Any edge cases that break the design?

Thanks,
[Your name]
```

### Alternative: Email Subject Line
```
Subject: TalaMala v5 Spec v2.7 Review — 4 Critical Subsystems for Production Safety

v2.7 is ready. See REVIEW-INSTRUCTIONS.md for process. Feedback template included.
```

---

## 🔍 Pre-Send Verification Checklist

Before sending to reviewers, verify:

- [x] All 5 files present and error-free
- [x] Version numbers consistent (2.7 everywhere)
- [x] No placeholder text (e.g., "[to be filled]") except REVIEW-INSTRUCTIONS.md
- [x] Commit history pushed to repo
- [x] No sensitive data in files (no API keys, passwords, internal emails)
- [x] File permissions readable (chmod 644 or equiv)
- [x] Links between documents work (if sent as HTML or within wiki)

---

## 📊 Review Metrics

| Metric | Value |
|--------|-------|
| **Spec size** | 3000+ lines (v2.7) |
| **New sections** | 5 (§14.0–14.4) |
| **New subsystems** | 4 (D-90–D-93) |
| **New schemas** | 5 tables |
| **New endpoints** | 9 (8 admin, 1 POS) |
| **Decision log entries** | 4 new (D-90–D-93) |
| **Estimated review time** | 1–2 hours |
| **Estimated implementation** | 4–6 weeks (1-2 engineers) |
| **Risk level** | **CRITICAL** (financial safety) |

---

## ⚠️ Known Issues / Limitations

### In Scope for Review
- All 4 subsystems fully designed
- Schemas, endpoints, state machines complete
- Edge cases identified and addressed
- Iranian banking constraints explicitly considered

### Out of Scope (v2.8+)
- Detailed performance tuning (indexes, query plans)
- Detailed error message copy (UX writing)
- Detailed testing strategy (§19 in spec provides skeleton)
- Monitoring/alerting rules (outside spec, ops decision)

### Not Yet Designed (but not blockers)
- Reconciliation reporting dashboard (UI/UX, not architecture)
- Offline device sync protocol (implementation detail)
- POS device app side (Kotlin, outside this repo)

---

## ✨ Success Criteria for Review

Review is successful if reviewer provides:

1. **Clear verdict:**
   - ✅ All 4 subsystems approved → Ready to implement
   - ⚠️ Concerns raised → Design adjustments needed
   - ❌ Blockers found → Cannot implement until resolved

2. **Specific feedback on each subsystem:**
   - D-90: Soundness? Iranian banking? Effort reasonable?
   - D-91: Race conditions safe? Locking strategy sound?
   - D-92: Recovery job safe? Idempotency guaranteed?
   - D-93: Offline resilience? UX acceptable? Support load?

3. **Edge cases or concerns:**
   - Any scenario that breaks the design?
   - Suggestions for improvement?
   - Questions for clarification?

4. **Confidence level:**
   - "I'm confident this is production-ready"
   - "I have concerns but they're addressable"
   - "This needs significant rework"

---

## 🎓 Supporting Context (If Reviewers New to Project)

**TalaMala:** Iranian physical gold marketplace
- **Users:** Customers (buy), Dealers (POS/resell), Admin (operations)
- **Payments:** SADAD (non-reversible), IPG gateways (reversible)
- **Constraint:** Iran isolation (no external APIs, unreliable connectivity)
- **Treasury:** Central gold exposure cap (risk management)
- **Pricing:** Dynamic (gold price + fee + tax per channel)

**v2.6 Problems Found:**
- Price can change mid-checkout → no recovery path
- Concurrent orders can bypass treasury cap → race condition
- System crash after gateway approval = orphaned payment
- POS devices offline → lost sales, no fallback

**v2.7 Solutions:**
- Auto-reconcile ±2%, manual review >2% (D-90)
- Reserve gold on checkout, finalize on payment (D-91)
- State machine + recovery job + idempotency (D-92)
- Local device queue + eventual sync (D-93)

---

## 📞 Sender's Checklist (After Review Received)

- [ ] Reviewer provided verdict (PASS / CONCERN / FAIL)
- [ ] Feedback on all 4 subsystems documented
- [ ] Edge cases or concerns listed
- [ ] Questions for clarification noted
- [ ] If CONCERN or FAIL: Design adjustments planned
- [ ] If PASS: Ready to start Phase 1 implementation

---

## 🏁 Final Status

**v2.7 is ready to send to external reviewers.**

All documents prepared, spec complete, commit history clean. Reviewers have everything needed to assess the 4 critical subsystems for production correctness.

**Timeline:**
- **Now:** Send for external review
- **2-3 days:** Expect feedback
- **After feedback:** Design adjustments (if any)
- **Week 2:** Begin Phase 1 implementation

---

**Prepared:** 2026-05-18  
**By:** Claude Code (with Salam oversight)  
**Status:** ✅ **READY TO SHIP FOR REVIEW**
