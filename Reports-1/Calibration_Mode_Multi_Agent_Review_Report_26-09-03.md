# Multi-Agent Calibration Mode Review & Diagnostic Report

**Date:** 2026-09-03  
**Scope:** Full diagnostic of [`Auto_Ghost_Calibration_Mode_Plan_26-08-26.md`](file:///c:/v3/OTC_SNIPER/Dev_Docs/Auto_Ghost_Calibration_Mode_Plan_26-08-26.md) and [`Calibration_Mode_Stability_Remediation_Plan_26-08-31.md`](file:///c:/v3/OTC_SNIPER/Dev_Docs/Calibration_Mode_Stability_Remediation_Plan_26-08-31.md)  
**Method:** @Investigator forensic code analysis + @Reviewer plan audit + @Debugger live-state verification + @Optimizer efficiency review  
**Codebase state:** `feat/ai_kb` branch, 88/88 tests green, Vite build clean  
**Core Principles audited against:** [CORE_PRINCIPLES.md](file:///c:/v3/OTC_SNIPER/.agents/CORE_PRINCIPLES.md)  

---

## Executive Summary

The Calibration Mode architecture is **well-designed and fundamentally sound**. The single-owner `CalibrationService` pattern directly addresses the historical 2026-06-16 failure where calibration state was smeared across five files. The Stability Remediation (R1-R5) successfully hardened the crash-safety gaps discovered by forensic disk analysis.

However, this review identifies **3 active bugs, 5 high-priority observations, and 8 optimization/simplification opportunities** that should be addressed before considering the calibration subsystem production-ready.

---

## Part 1: Plan Quality Assessment

### 1.1 Auto-Ghost Calibration Mode Plan (26-08-26)

| Criterion | Rating | Notes |
|---|---|---|
| **Architectural clarity** | 5/5 | Single-owner `CalibrationService` is the correct pattern. Mermaid diagram is accurate and complete. |
| **Historical lesson integration** | 5/5 | Explicitly honors the 2026-06-16 smeared-state failure. Every design decision traces to a root cause. |
| **Risk identification** | 4.5/5 | Excellent — identified 5-surface leak, copy-mode execute, 409 lock, payout unit mismatch, AND the inert manipulation veto (A1). Minor gap: did not anticipate the crash-resilience gap that the Stability Plan later found. |
| **Verification completeness** | 4/5 | Strong contract test battery defined. Gap: no chaos/crash-recovery tests specified (the Stability Plan had to add these). |
| **Statistical rigor** | 4/5 | REV2 bootstrap model is honest about N<20 limitations. Guardian deferred rigor is sound. |
| **Scope discipline** | 5/5 | Phase 6 deferred cleanly. Open decisions resolved explicitly. |
| **Plan size vs. complexity** | 3/5 | At 322 lines and ~47KB, the plan is **extremely dense**. While thoroughness is valuable, the sheer volume creates cognitive overhead for reviewing agents and may slow future onboarding. |

> [!TIP]
> **Recommendation:** Future plans of this scope should include a 1-page "decision summary" at the top with links to detail sections, reducing the cognitive load for reviewers.

### 1.2 Stability Remediation Plan (26-08-31)

| Criterion | Rating | Notes |
|---|---|---|
| **Diagnostic accuracy** | 5/5 | Forensically confirmed 2 real production failures on disk. Root causes correctly identified. |
| **Fix correctness** | 5/5 | D4-restore-before-AI-review ordering is the right fix. Exception-safe finalize is textbook. |
| **R5 incident response** | 5/5 | The reconcile-one-shot and skip-active-calibration fixes correctly address the repeated notification incident. |
| **Scope containment** | 5/5 | Zero scope creep — no Phase 6, no new features, only hardening. |
| **Remediation completeness** | 4/5 | All critical and high findings addressed. M-6 (mount-time status fetch) is implemented. |

---

## Part 2: Code Cross-Reference Findings

### CRITICAL — Active Bugs

#### BUG-1: Third STALE_ABORTED Session — Possible Ongoing Crash Pattern

**Evidence:** Live disk state shows **3 `STALE_ABORTED` sessions** (`...119574`, `...127900`, `...195745`) out of 41 total sessions (7.3% crash rate). The most recent session (`...467893`) was in `RUNNING` on disk, subsequently reconciled to `STALE_ABORTED` at boot.

```
auto_ghost_calib_1788119574.json  state=STALE_ABORTED  (original plan discovery)
auto_ghost_calib_1788127900.json  state=STALE_ABORTED  (original plan discovery)
auto_ghost_calib_1788195745.json  state=STALE_ABORTED  <-- NEW since remediation
auto_ghost_calib_1788467893.json  state=STALE_ABORTED  <-- JUST reconciled (was RUNNING)
```

**Analysis:** `...195745` has epoch `1788195745` which is between the original plan implementation and the stability remediation. However, `...467893` (epoch 2026-09-03) occurred **after the R1 fix was deployed**, meaning sessions are still crashing during finalize or being interrupted by process death. The 7.3% failure rate is high for a feature with a 409 lock on user config.

**Recommendation:** Investigate `...467893` — was this a normal process stop (Ctrl+C during a session) or an unexpected crash? If the latter, the finalize path may still have a code path that can hang or crash. Consider adding a `graceful_shutdown` hook to Python's `atexit` module that triggers `abort()` on the active calibration.

> [!CAUTION]
> The `STALE_ABORTED` recovery does NOT restore the user's pre-calibration config. Each crash leaves the user's protocol settings replaced with the calibration baseline until manually corrected. This is explicitly called out in the reconciliation log but could silently degrade live trading.

#### BUG-2: Guardian Emits `ai_pulse` Notification Type — Breaks C5 Contract

**File:** [`calibration_service.py:1051-1056`](file:///c:/v3/OTC_SNIPER/app/backend/services/calibration_service.py#L1051-L1056)

The Guardian loop emits notifications with `"type": "ai_pulse"` — the same type that the calibration plan's C5 contract explicitly forbids during calibration (to prevent AI-triggered execution and pending-card rendering). While the Guardian runs post-DONE (not during RUNNING), the App.jsx notification handler at `:205` processes `ai_pulse` notifications identically regardless of calibration state, potentially triggering the existing "Update Ghost Protocol" one-click Apply card rendering and toast sounds.

```python
# calibration_service.py:1051-1056
await self._sio.emit("notification", {
    "type": "ai_pulse",  # <-- same type as regular AI Pulse
    "message": f"Session Guardian: {item.get('rationale')}",
    ...
})
```

**Recommendation:** Use a dedicated `"type": "guardian_proposal"` to disambiguate Guardian suggestions from regular AI Pulse notifications. Update the frontend to handle this type with its own UI treatment.

#### BUG-3: `_finalize` Missing `asyncio.wait_for` on Final AI Review

**File:** [`calibration_service.py:597-600`](file:///c:/v3/OTC_SNIPER/app/backend/services/calibration_service.py#L597-L600)

The Stability Remediation Plan R1-1 specifies the final AI review must be wrapped in `asyncio.wait_for(timeout=90)`. The mid-run milestone review at `:821` correctly has the timeout. However, the **final** review call at `:598` does **not** use `wait_for`:

```python
# Line 598 — NO timeout wrapping!
if final_state == "DONE":
    await self._run_milestone_review(
        settled, apply_tier_a=False, is_final=True,
    )
```

Inside `_run_milestone_review`, the AI call itself has a timeout at `:821`, but `_persist_observations` (`:889`) and `_emit_named` (`:898`) are outside the timeout scope. If `_emit_named` blocks (Socket.IO backpressure), the finalize can still hang after the D4 restore, which is less critical but still violates the "timeout-bounded" contract.

**Recommendation:** Wrap the entire `_run_milestone_review` call at `:598` in `asyncio.wait_for(timeout=90.0)` as the remediation plan's code sample specifies.

---

### HIGH — Observations

#### H-1: A3 Suggestion-Effectiveness Ledger — Completely Missing

Both plans acknowledge the A3 ledger as incomplete. Zero implementation exists — no matches for ledger, suggestion effectiveness, or pre/post WR delta tracking. The AI prompt at `:914-920` does not inject "your last 3 suggestions averaged +X pp" context.

**Impact:** The AI cannot learn from its own recommendations. Each milestone review starts from scratch without feedback on prior suggestion quality.

**Recommendation:** This is a significant gap for the self-improvement loop. Implement a lightweight JSON ledger keyed by `{field, direction}` with a rolling window of pre/post 20-trade WR deltas. Priority: Medium (useful but not blocking).

#### H-2: Calibration File Accumulation — No Retention Policy

41 calibration session files currently on disk. Each is 4-6KB. No cleanup or archival policy exists. Over weeks of daily calibration runs, this will accumulate hundreds of files in `app/data/calibration_sessions/`.

**Recommendation:** Add a retention policy (e.g., keep last 20 DONE sessions + all STALE_ABORTED for forensics). Purge during `_reconcile_stale_sessions()`.

#### H-3: `_time_budget_watchdog` — Direct State Mutation Outside `_finalize`

**File:** [`calibration_service.py:1101-1115`](file:///c:/v3/OTC_SNIPER/app/backend/services/calibration_service.py#L1101-L1115)

The watchdog directly mutates `self._state = "ANALYZING"` and then calls `_finalize_after_drain()`. The `_on_outcome._check_budgets_sync` (`:697-717`) can race with the watchdog — both check `self._state == "RUNNING"` and both call `_finalize_after_drain()`. The `_finalizing` flag prevents double-finalize, but the state mutation happens outside any lock, creating a potential window where both paths set `self._state = "ANALYZING"` and one of them's `_journal` entry is lost.

**Recommendation:** Consolidate all terminal-transition logic into a single `_request_terminal()` followed by `_begin_drain()` path. The watchdog should use `_request_terminal("DONE", "time_budget_elapsed")` + `_begin_drain()` instead of directly mutating state.

#### H-4: `classify_alignment` Operates on Single Trade, Not Window

**File:** [`ghost_protocol_profiles.py:309-354`](file:///c:/v3/OTC_SNIPER/app/backend/services/ghost_protocol_profiles.py#L309-L354)

```python
alignment = classify_alignment(trades[-1], self._warm_start_baseline)
```

The alignment classification uses only the **last single trade's** features (`:1085`), not a rolling window. A single outlier trade can flip the alignment from "Relaxed" to "Strict" and trigger a notification + preset suggestion. This is noisy and statistically unreliable.

**Recommendation:** Use the last 10-20 trades' mean features for classification, consistent with how `detect_market_drift` already uses `trades[-20:]`.

#### H-5: `warm_start_baseline.json` Expected WR is 50.18% — Marginal

The generated baseline shows `"expected_wr": 50.18` — barely above random. The Guardian prior-transfer divergence threshold is 8pp (`PRIOR_TRANSFER_DIVERGENCE_PP = 8.0`), meaning the Guardian won't flag prior-transfer failure until live WR drops below ~42% or exceeds ~58%. This is a very wide band that may miss meaningful performance degradation.

**Recommendation:** Consider reducing `PRIOR_TRANSFER_DIVERGENCE_PP` to 5.0pp or making it adaptive based on the expected_wr confidence interval.

---

### MEDIUM — Optimization & Simplification Opportunities

#### OPT-1: `calibration_service.py` Size — 1,147 Lines (Principle #6 Concern)

The CalibrationService has grown to **1,147 lines** with the Guardian, alignment, drift, milestone, persistence, watchdog, and emission logic all in one file. While the single-owner pattern is correct, the file's internal structure could be improved.

**Recommendation:** Extract pure-function helpers into their own modules:
- `_ask_milestone_ai` - inline AI integration could move to a `calibration_ai.py` adapter
- `_guardian_loop` + `_run_alignment_and_drift` - `calibration_guardian.py`
- `_persist` + `_reconcile_stale_sessions` - `calibration_persistence.py`

The `CalibrationService` class would then delegate to these, maintaining single ownership while improving readability. (Consistent with Principle #6: one file = one responsibility.)

#### OPT-2: Redundant Tier B Check in `enforce_milestone`

**File:** [`calibration_autonomy.py:95-106`](file:///c:/v3/OTC_SNIPER/app/backend/services/calibration_autonomy.py#L95-L106)

```python
if field in CALIBRATION_TIER_B_FIELDS:  # line 95 — R2-4 fix
    proposals.append(...)
    continue
if field in locked_fields:              # line 98
    rejected.append(...)
    continue
if field not in CALIBRATION_TIER_A_FIELDS:
    if field in CALIBRATION_TIER_B_FIELDS:  # line 102 — DEAD CODE
        proposals.append(item)
```

Line 102's `CALIBRATION_TIER_B_FIELDS` check is **dead code** — it's unreachable because the `continue` at line 96 always exits first. This was introduced by the R2-4 fix which correctly added the early route at line 95 but didn't remove the original check at line 102.

**Recommendation:** Remove lines 102-103 (dead code cleanup).

#### OPT-3: `_as_change_list` Called Multiple Times on Same Input

**File:** [`calibration_autonomy.py:89, 63-64`](file:///c:/v3/OTC_SNIPER/app/backend/services/calibration_autonomy.py#L63-L64)

`_as_change_list(payload.get("tier_a_changes"))` is called at line 63 (inside `parse_autonomy_payload`) AND again at line 89 (inside `enforce_milestone`). The parsed payload from `parse_autonomy_payload` already contains sanitized lists, so the second call re-validates unnecessarily.

**Recommendation:** Remove the redundant `_as_change_list()` wrapping inside `enforce_milestone` since the input is already validated.

#### OPT-4: Guardian Loop Sleep Interval is Hardcoded

**File:** [`calibration_service.py:1028`](file:///c:/v3/OTC_SNIPER/app/backend/services/calibration_service.py#L1028)

```python
await asyncio.sleep(30)
```

The 30-second Guardian poll interval is hardcoded. During periods of low trade activity, this creates unnecessary computation. During high activity, 30s may be too slow to catch rapid regime changes.

**Recommendation:** Make the interval configurable (default 30s) and consider an event-driven approach where the Guardian wakes on trade settlement rather than polling.

#### OPT-5: `_persist()` Called Excessively in Hot Paths

Within `_on_outcome` (`:675`) and `_journal` (`:284`), `_persist()` is called synchronously on every single trade settlement. Each persist does a full JSON serialization of the entire session state + `os.replace`. For a 24-trade calibration, this produces ~100+ file writes (settlement - persist, journal - persist, budget check - persist, milestone - persist x N).

**Recommendation:** Debounce persistence to every 2-3 seconds or on state transitions only. The `_finalize` path already ensures a final persist, so intermediate writes only need to survive process crashes — and with the R1-3 reconciliation, stale sessions are already handled.

#### OPT-6: `build_strictness_presets` — Static Presets Rebuilt on Every Call

**File:** [`ghost_protocol_profiles.py:158-181`](file:///c:/v3/OTC_SNIPER/app/backend/services/ghost_protocol_profiles.py#L158-L181)

The presets are static constants with only one dynamic adjustment (Strict Bayesian floor when WR < 45%). The function deep-copies `_BACKEND_PRESETS`, converts to frontend keys, and validates missing keys on every call.

**Recommendation:** Precompute the three preset frontend representations at module load time and apply the WR-based Bayesian adjustment inline. Eliminates ~20 dict operations per call.

#### OPT-7: Population Variance Used in `_mean_std`

**File:** [`ghost_protocol_profiles.py:231-237`](file:///c:/v3/OTC_SNIPER/app/backend/services/ghost_protocol_profiles.py#L231-L237)

```python
var = sum((x - mean) ** 2 for x in values) / n  # population variance
```

Uses population variance (`/n`) instead of sample variance (`/(n-1)`). Since this is used for drift detection z-scores against centroid reference distributions, sample variance (`n-1`) is statistically more appropriate for small N (the `DRIFT_MIN_N` is only 8).

**Recommendation:** Use `/(n - 1)` for Bessel's correction when `n > 1`.

#### OPT-8: `get_calibration_service` Singleton Re-binds on Every API Call

**File:** [`calibration_service.py:1137-1144`](file:///c:/v3/OTC_SNIPER/app/backend/services/calibration_service.py#L1137-L1144)

The R5 fix correctly added a one-shot flag for reconciliation. However, `bind()` is still called on every API call from `strategy.py`, re-assigning `self._auto_ghost` and `self._sio` references. This is idempotent but unnecessary after the first bind.

**Recommendation:** Add a guard: `if self._auto_ghost is auto_ghost and self._sio is sio: return`.

---

## Part 3: Core Principles Compliance Audit

| Principle | Status | Evidence |
|---|---|---|
| **#1 Functional Simplicity** | PARTIAL | Architecture is correct but file sizes (1,147 lines service + 47KB plan) push complexity thresholds. |
| **#2 Sequential Logic** | PASS | State machine transitions are explicit and well-documented. |
| **#3 Incremental Testing** | PASS | 88/88 tests green. Each phase was tested before proceeding. |
| **#4 Zero Assumptions** | PASS | Every gap identified (EX-1 through EX-23) was verified by file:line evidence. |
| **#5 Code Integrity** | PASS | No breaking changes to existing contracts (5-surface routing, 409 lock, Bayesian units). |
| **#6 Separation of Concerns** | PARTIAL | Single-owner is correct, but `calibration_service.py` at 1,147 lines combines 6+ concerns (see OPT-1). |
| **#7 Stop Patching** | PASS | The Stability Remediation was a targeted fix, not infinite patching. The R5 incident response was clean. |
| **#8 Zero Silent Failures** | PASS | R3-2 loud baseline-missing notification. STALE_ABORTED uses `logger.error`. Kill-switch emits loud abort. |
| **#9 Fail Fast** | PASS | Session-id fail-fast guard (`:419-423`). CalibrationStateError on invalid transitions. |

---

## Part 4: Prioritized Recommendations

### Immediate (before next live calibration run)

| # | Item | Severity | Effort |
|---|---|---|---|
| 1 | **BUG-3:** Add `asyncio.wait_for(timeout=90.0)` around the final `_run_milestone_review` call at line 598 | CRITICAL | 5 min |
| 2 | **BUG-1:** Investigate the STALE_ABORTED pattern — add `atexit` shutdown hook for active calibrations | CRITICAL | 30 min |
| 3 | **BUG-2:** Change Guardian notification type from `ai_pulse` to `guardian_proposal` | HIGH | 15 min |
| 4 | **OPT-2:** Remove dead code at `calibration_autonomy.py:102-103` | LOW | 2 min |

### Short-term (next sprint)

| # | Item | Severity | Effort |
|---|---|---|---|
| 5 | **H-3:** Consolidate watchdog and settlement budget transitions through `_request_terminal` | HIGH | 1 hr |
| 6 | **H-4:** Use rolling window (N=20) for `classify_alignment` instead of single trade | HIGH | 30 min |
| 7 | **H-2:** Add session file retention policy (keep 20 DONE, all ABORTED) | MED | 30 min |
| 8 | **OPT-5:** Debounce `_persist()` to reduce I/O from ~100 writes to ~10 per calibration | MED | 1 hr |
| 9 | **OPT-7:** Fix population variance to sample variance in `_mean_std` | MED | 5 min |

### Medium-term (backlog)

| # | Item | Severity | Effort |
|---|---|---|---|
| 10 | **OPT-1:** Extract Guardian, persistence, and AI adapter into separate modules | MED | 2 hr |
| 11 | **H-1:** Implement A3 suggestion-effectiveness ledger | MED | 3 hr |
| 12 | **H-5:** Reduce `PRIOR_TRANSFER_DIVERGENCE_PP` from 8.0 to 5.0 | LOW | 5 min |
| 13 | **OPT-4:** Make Guardian poll interval configurable | LOW | 15 min |
| 14 | **OPT-6:** Precompute strictness preset frontend representations | LOW | 30 min |
| 15 | **OPT-8:** Guard against redundant `bind()` re-assignment | LOW | 5 min |

---

## Part 5: What's Working Exceptionally Well

These aspects of the implementation are **best-in-class** and should be preserved:

1. **Single-owner pattern:** `CalibrationService` is the sole authority. No other module touches calibration state. This directly prevents the 2026-06-16 smeared-state class of bugs.

2. **Five-surface silent routing:** The `emit_trade_channel` helper with contract tests is the correct architecture. Silence by routing (not by suppression) is robust against UI regression.

3. **Spec-table config validation:** `_AUTO_GHOST_FIELD_SPECS` with casters and bounds means the AI can never set impossible values through `update_config`. The Bayesian `(0.50, 0.90)` clamp is production-critical.

4. **409 runtime-config lock:** Prevents the exact failure mode that killed the 2026-06-16 calibration (400ms debounced sync overwriting the preset). The lock is verified by both backend and frontend.

5. **Epoch changelog:** Every config mutation is journaled with `{field, old, new, trade_index, rationale, evidence_n}`. This makes the non-stationary dataset scientifically usable.

6. **Catastrophic-evidence rule (REV2):** The <=2/12 threshold is conservative and honest about the 24-trade sample limitation.

7. **D4 restore-before-AI-review:** The R1-1 fix puts the user's config safety above the AI review's completion — exactly the right priority order.

8. **Warm-start baseline with recency decay:** The 21-day half-life + 56-day lookback is well-calibrated for a market that changes weekly but has monthly patterns.

---

## Part 6: Open Items Inventory

These items are tracked but not yet resolved:

| # | Item | Source | Status |
|---|---|---|---|
| 1 | Phase 3 P1: `_finalize` awaits AI review before D4 restore | Original Plan | FIXED by R1-1 |
| 2 | Phase 3 P1: Tier B rejects `amount`/`expiration` | Original Plan | FIXED by R2-4 |
| 3 | Phase 3 P1: Guardian `allowed_regimes` empty = allow-all | Original Plan | FIXED by R2-3 |
| 4 | A3 suggestion-effectiveness ledger | Both plans | Not implemented |
| 5 | Live Bayesian scoring uses unweighted integers | Original Plan | Open |
| 6 | Corrupt warm-start disables D7 with only a log | Original Plan | Mitigated (R3-2 loud notification) |
| 7 | Staging-modal copy talks about integer prior merges | Original Plan | Open (cosmetic) |
| 8 | Manual live browser calibration pass | Both plans | Not performed |
| 9 | Phase 6 Discord NotificationSink | Both plans | Deferred |
| 10 | M14: Split `test_auto_ghost.py` monolith | PreFlight Plan | Deferred |

---

## Conclusion

The Calibration Mode subsystem is architecturally sound and well-tested (88/88 green). The Stability Remediation successfully addressed the most critical crash-safety gaps. However, **BUG-3 (missing timeout on final review)** is the most urgent fix — it's a single-line change that the remediation plan specified but the implementation missed. The 7.3% STALE_ABORTED rate (BUG-1) should be investigated before running more calibration sessions, and the Guardian notification type mismatch (BUG-2) should be corrected to maintain the C5 contract's integrity.

The optimization opportunities (OPT-1 through OPT-8) are low-risk, high-value improvements that can be addressed incrementally without disrupting the working system.

---

*Report produced by @Investigator + @Reviewer + @Debugger + @Optimizer. Findings are grounded in live code forensics and disk state analysis. All line references verified against the current `feat/ai_kb` branch.*
