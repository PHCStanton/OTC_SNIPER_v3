# Session-First Learning & AI Pulse Adaptive Tuning — Decision Record

**Branch:** `feat/ai_kb` · **Date:** 2026-09-04 · **Status:** Implemented ([~] pending @Reviewer phase-gate)
**Source prompt:** `prompts/prompt-master/SESSION1st_LEARNING_Ai_PULSE_ADAPTIVE_TUNING_26.09.04`

---

## 1. Executive Summary

Live session behavior now dynamically validates (and, when cold, overrules) the historical
knowledge base. A standalone in-memory `SessionPerformanceTracker` records settled ghost
outcomes keyed strictly by `AutoGhostService._session_id`, computes a **3-layer effective
win rate** whose weights shift from **40/30/30 → 60/20/20** as the session establishes, and
feeds a structured `### SESSION CONTEXT & PERFORMANCE LAYERS` block into the AI Pulse prompt
with **deterministic policy directives**. Tiered mutation authority is enforced: Category A
(bayesian floor +0.02 cold-streak adaptation, session-local regime vetoes) is automatic,
in-memory/update_config-routed, and audit-logged; Category B (pausing, presets, amounts,
persisted regime lists) remains propose-only via Guardian/user cards. The KB staging
invariant is untouched — no master file (`bayesian_priors*.json`, `condition_patterns.json`)
is ever written by live paths.

## 2. Architecture Context

| Concern | Owner | Mechanism |
|---|---|---|
| Session state (settled outcomes, streak, per-regime, horizon split) | `SessionPerformanceTracker` (`app/backend/services/session_tracker.py`) | In-memory deques/counters keyed by `_session_id` |
| Session lifecycle binding | `AutoGhostService._reset_session` → `tracker.ensure_session()` | Archive-then-reset; calibration sessions never archived |
| Effective WR engine | `tracker.effective_win_rate()` | Weight matrix + renormalization guardrail |
| AI Pulse injection | `streaming.py::_build_pulse_user_msg` / `_render_session_context_section` | Pure-function prompt section (backward-compatible kwarg) |
| Category A mutations | `AutoGhostService._apply_category_a_mutations()` | `update_config()` clamp route + `_session_audit_log` + `logger.warning` |
| Category B mutations | CalibrationService Guardian / frontend card (unchanged) | Propose-only, user-approved |

## 3. The Three-Layer Effective Win Rate

`effective_wr = w_session·WR_session + w_recent·WR_recent + w_kb·WR_kb`

**Weight Distribution Matrix** (keyed by settled session sample size `N`):

| Session Settled Trades (N) | w_session | w_recent (last 3 sessions) | w_kb (book/priors) |
|---|:---:|:---:|:---:|
| N < 10 (early) | **0.40** | **0.30** | **0.30** |
| 10 ≤ N < 20 (developing) | **0.50** | **0.25** | **0.25** |
| N ≥ 20 (established) | **0.60** | **0.20** | **0.20** |

**Layer specifications & guardrails:**
- **Layer 1 (session):** current session settled trades (optionally horizon-filtered 60s/300s).
- **Layer 2 (recent):** up to 3 most recent live ghost sessions **on the same UTC calendar day
  and same horizon**. Sessions with zero evidence on that horizon are skipped without
  consuming a slot. In-process history only — a fresh server start legitimately omits Layer 2.
- **Layer 3 (book):** sample-size-weighted WR across `KnowledgeBaseLoader` patterns matching
  the current regime + UTC 4h block (`min_sample_size=20`, top 8). The book itself is
  recency-weighted at mining time (21-day half-life backfill), so no separate per-pattern
  recency pass is needed (patterns carry no timestamps). **Missing → `None`, never a
  hallucinated 50.0%.**
- **Renormalization rule:** any missing layer is dropped and remaining weights renormalized
  to Σw = 1.0, with a structured `logger.info` reweighting event. If no layer has data,
  `effective_wr` is `None` (rendered `UNAVAILABLE` in the prompt).

## 4. Tiered Mutation Authority (Safety Model)

### Category A — Automatic, Zero Operator Interruption
Every mutation routes through `AutoGhostService.update_config()` (declarative spec-table
clamps) or in-memory state, and writes a structured audit record
(`_session_audit_log`, `logger.warning`):

1. **Bayesian floor adaptation** — trigger: 3 consecutive settled losses (tracker streak,
   void-free, session-scoped); action: `bayesian_min_probability += 0.02` per 3-loss step
   (escalates at −3, −6, −9, …), clamped `[0.50, 0.90]` via
   `_AUTO_GHOST_FIELD_SPECS["bayesian_min_probability"]`. **Invariant:** float fraction
   semantics (`0.535 → 0.555`) — never percent integer (`53.5`). Guarded on
   `bayesian_filter_enabled` (a floor bump is meaningless while the filter is off).
2. **Session-local regime veto** — trigger: regime at 0 wins / ≥5 settled, or WR ≤ 2/12
   (~16.7%) with N ≥ 12. Stored in `AutoGhostService._session_vetoed_regimes`;
   `consider_signal()` rejects with reason `session_regime_veto` **before** the persisted
   regime gate. **Invariant:** `config.allowed_regimes` is NEVER written (an empty list
   evaluates to "allow all regimes" — catastrophic bypass). Vetoes dissolve automatically
   when `_session_id` resets.

### Category B — Propose-Only (never automated)
Pausing/disabling Auto-Ghost, switching Relaxed/Conservative/Strict presets, altering base
amount / expiration duration / max drawdown, and permanent `allowed_regimes` changes are
surfaced exclusively as `guardian_proposal` cards or click-to-apply AI Pulse suggestion
cards (explicit user approval), consistent with the calibration autonomy tiers.

## 5. Session-First Bias & Isolation Rules
- **Keying:** tracker state is keyed strictly by `AutoGhostService._session_id`
  (`auto_ghost_{epoch}` live, `auto_ghost_calib_{epoch}` calibration). New session id ⇒
  archive previous live session into Layer-2 history + full reset.
- **Calibration isolation:** calibration-mode settlements never enter the tracker, never
  archive into Layer-2 history, and never trigger Category A mutations (calibration
  autonomy is owned by `CalibrationService`).
- **Void semantics:** `void` outcomes are neither wins nor losses — zero WR evidence; they
  never touch streaks, settled counts, or regime stats.
- **Horizon isolation:** 60s and 300s expiries tracked separately end-to-end.
- **UTC 4h blocks:** origin 22:00 UTC (Block 0 = 22:00–02:00 … Block 5 = 18:00–22:00) via
  `shared/utc_time_blocks.py`.

## 6. Deterministic Policy Directives (Prompt Contract)
Computed in `AutoGhostService._session_policy_directives()` — the LLM is *given* the rules,
never allowed to invent trade policy:
1. Streak ≤ −3 → direct the model to recommend raising the Bayesian probability floor /
   tightening confluence requirements (never relaxing gates while cold).
2. Regime N ≥ 5 with WR < 35% → instruct the model to advise pausing signals in that regime.
3. Effective WR > 65% with N ≥ 10 → permit normal or expanded signal evaluation.

## 7. Files Touched

| File | Change |
|---|---|
| `app/backend/services/session_tracker.py` | **NEW** — `SessionPerformanceTracker`, weight matrix, 3-layer engine, veto candidates |
| `app/backend/services/auto_ghost.py` | Tracker wiring (`__init__`, `_reset_session`, `report_outcome`), Category A (`_apply_category_a_mutations`, `_write_audit`, `_record_session_tracker`), `session_regime_veto` gate, `session_performance_snapshot()` + directives |
| `app/backend/services/streaming.py` | `_render_session_context_section()` (NEW), `### SESSION CONTEXT & PERFORMANCE LAYERS` injection in `_build_pulse_user_msg` (backward-compatible kwarg), wiring in `_run_ai_pulse_insight` |
| `test_session_tracker.py` | **NEW** — 7 contract tests (voids/calib isolation, weight matrix, Layer-2 guardrails, floor bump, veto isolation, snapshot/prompt, directives) |
| `test_auto_ghost.py` | Test 17 — tracker integration smoke (deltas, void exclusion, snapshot) |
| `Dev_Docs/Session_First_Learning_Decision_Record_26-09-04.md` | This record |

## 8. Verification Checklist
- [x] Step 0 pre-flight: 54/54 calibration tests green before implementation.
- [x] `test_tracker_ignores_voids_and_calib_sessions`
- [x] `test_effective_wr_weight_transitions` (N = 5 / 15 / 25 + renormalization, Σw = 1)
- [x] `test_bayesian_floor_auto_bump_on_3_loss_streak` (+0.02, clamp 0.90, audit entry)
- [x] `test_session_regime_veto_isolated_from_allowed_regimes` (no `allowed_regimes` writes)
- [x] Full regression (calibration, autonomy, KB, pre-flight, ghost suites) — see memory log.
- [ ] @Reviewer phase-gate sign-off (PHASE_REVIEW_PROTOCOL)

## 9. Risk Assessment

| Risk | Mitigation |
|---|---|
| Veto suppresses a regime that recovers intraday | Vetoes are session-local and dissolve on `_session_id` reset; prompt shows them explicitly |
| Floor bump tightens too far | +0.02 per 3-loss step, hard clamp 0.90, audit-logged, spec-table clamped |
| Stale Layer-2 evidence after restart | In-process history only; missing Layer 2 → renormalization (fail-safe, honest) |
| Calibration pollution | Triple guard: mode check + calib-prefix check in service AND tracker; calib sessions never archived |
| Prompt regression | New section is a pure function; omitted kwarg ⇒ byte-identical legacy prompt (tested) |

## 10. Out-of-Scope (untouched, per contract)
A3 suggestion-effectiveness ledger; raw integer Bayesian prior rewrites; Discord/Phase 6;
`CalibrationService` lock/D4 semantics.
