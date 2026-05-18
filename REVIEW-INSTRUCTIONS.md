# TalaMala v5 Spec v2.7 — Review Instructions

**To External Reviewers:** Thank you for reviewing this architecture. Please follow the instructions below.

---

## Step 1: Download/Clone Context

You have received:
- `talamala_v5_architecture_spec.md` (v2.7) — **PRIMARY** — 3000+ lines
- `SPEC-v2-7-SUMMARY.md` — Quick 1-page overview
- `SPEC-v2-7-REVIEW-PACKAGE.md` — This package, with checklist
- `DECISION-FRAMEWORK-v2-7.md` — Context on why decisions were made

---

## Step 2: Quick Brief (5 min)

Read **SPEC-v2-7-SUMMARY.md** sections:
1. "What Changed from v2.6 to v2.7" (table)
2. "New Database Tables" (5 tables)

This gives you the gist of 4 subsystems.

---

## Step 3: Deep Review (30–60 min)

Open **talamala_v5_architecture_spec.md** (v2.7) and read:

1. **§0.0 "راهنمای داورِ خارجی"** (at top)
   - Understand the review scope
   
2. **§14.0 – §14.4** (~400 lines)
   - §14.1: Payment Reconciliation (D-90)
   - §14.2: Pending Reserves (D-91)
   - §14.3: Payment State Machine (D-92)
   - §14.4: POS Offline Queue (D-93)

3. **§2.5 Decision Log** — Find D-90, D-91, D-92, D-93 entries
   - See the rationale for each

4. **§21 Implementation Roadmap** — How these fit into v1 MVP
   - Phase 1-2: Payment reconciliation + state machine
   - Phase 3: Pending reserves
   - Phase 4: POS offline queue

---

## Step 4: Verify Against Checklist

Use **SPEC-v2-7-REVIEW-PACKAGE.md**, section "🎯 Specific Questions for Reviewers":

For each of the 4 subsystems (D-90, D-91, D-92, D-93):
- [ ] Read the "Please verify" checklist
- [ ] Read the "Edge cases to consider"
- [ ] Mark any concerns as ⚠️ or ❌

---

## Step 5: Provide Feedback

Reply with your assessment on:

### A. Design Soundness (Must Pass)
**For each subsystem, state:**
- ✅ "Architecturally sound, no concerns"
- ⚠️ "Concern: [specific issue]"
- ❌ "Blocker: [issue that prevents implementation]"

### B. Iranian Banking Constraints (Must Pass)
**Do the 4 subsystems respect:**
- ✅ No blind refunds (D-90 reconciliation)
- ✅ Async settlement acceptable (D-92 recovery job)
- ✅ Eventual consistency acceptable (D-93 offline queue)
- ✅ Full audit trail (all changes logged)

### C. Implementation Feasibility (Should Pass)
**Can this be built in 4-6 weeks by 1-2 engineers?**
- ✅ Yes, reasonable scope
- ⚠️ Concern: [effort estimate too low]
- ❌ Too complex, needs simplification

### D. Edge Cases (Document)
**For each concern you raise, state:**
- What edge case breaks the design?
- Why is it a problem?
- Suggested fix (if you have one)

---

## Template for Response

Copy-paste and fill in:

```
# TalaMala v5 Spec v2.7 — Review Feedback

**Reviewer:** [Name/Model]  
**Date:** [Date]  
**Overall Assessment:** [PASS / PASS with concerns / FAIL]

## D-90: Payment Reconciliation
- **Soundness:** [✅ / ⚠️ / ❌]
- **Concerns:** [List or N/A]
- **Iranian Banking:** [✅ / ⚠️]

## D-91: Pending Reserves
- **Soundness:** [✅ / ⚠️ / ❌]
- **Concerns:** [List or N/A]
- **Race Conditions:** [Verified safe / Concern: ...]

## D-92: Payment State Machine
- **Soundness:** [✅ / ⚠️ / ❌]
- **Idempotency:** [Verified / Concern: ...]
- **Recovery:** [Verified / Concern: ...]

## D-93: POS Offline Queue
- **Soundness:** [✅ / ⚠️ / ❌]
- **Offline Resilience:** [Verified / Concern: ...]
- **UX/Support Load:** [Acceptable / Concern: ...]

## General Issues (If Any)
- [Issue 1]
- [Issue 2]

## Recommendations
[Any suggestions for improvement?]

## Ready to Implement?
- ✅ **YES** — All 4 subsystems approved
- ⚠️ **YES, with clarifications** — [List specific clarifications needed]
- ❌ **NO** — [Blockers that must be resolved first]
```

---

## Specific Focus Areas (by Expertise)

### If You're a Systems Architect
Focus on:
- §14 schemas and state machines
- Concurrency/race conditions (D-91, D-92)
- Idempotency patterns (D-92, D-93)

### If You're a Backend Engineer
Focus on:
- Implementation complexity of each subsystem
- New table designs and indexes
- Async job patterns (D-92, D-93)
- Testing strategy (§19 in main spec)

### If You're a Financial/Payments Expert
Focus on:
- Payment reconciliation logic (D-90)
- Iranian banking constraints
- Audit trail completeness
- Reversibility (or lack thereof) under constraints

### If You're a Database Specialist
Focus on:
- Schema normalization
- Foreign key constraints
- Concurrency (locks, isolation levels)
- Recovery/crash-safety

---

## Common Questions

**Q: How long should review take?**  
A: 30–60 minutes total. Start with SUMMARY (5 min), then deep dive into ONE subsystem (15 min each), then checklist (5 min).

**Q: Should I read the entire spec, or just §14?**  
A: Start with §0.0 (context) + §14 (new), then optionally reference §2.5 (decisions) and §21 (roadmap).

**Q: What if I find a blocker?**  
A: State it clearly in the feedback. Don't assume we'll catch it in implementation. Better to fix design now than rework code later.

**Q: Can I suggest a better design for one subsystem?**  
A: Absolutely. If you have a simpler or safer alternative, include it. State both "current design" and "alternative" clearly.

**Q: What if I'm uncertain about something?**  
A: Mark as ⚠️ and explain the uncertainty. That's helpful feedback.

---

## Success Criteria

Your review is successful if you:
1. ✅ Read §0, §14 in main spec
2. ✅ Checked all items in SPEC-v2-7-REVIEW-PACKAGE.md checklist
3. ✅ Provided feedback on all 4 subsystems (D-90, D-91, D-92, D-93)
4. ✅ Stated clear recommendation: PASS / PASS with concerns / FAIL
5. ✅ Identified any blockers or edge cases

---

## Contact/Questions During Review

If you have questions while reviewing:
- Check §0.1 "موارد باز" (open items in spec)
- Check DECISION-FRAMEWORK-v2-7.md for context
- Ask directly (contact info: [to be filled by sender])

---

## After Review

Once you submit feedback:
1. Sender reviews your feedback
2. Design adjustments if needed (unlikely for v2.7, but possible)
3. Implementation begins (4-6 weeks)
4. You're invited to code review when ready

---

**Thank you for reviewing!** Your feedback is critical for production correctness.

Generated: 2026-05-18  
Version: 2.7 (Final for v1 MVP)
