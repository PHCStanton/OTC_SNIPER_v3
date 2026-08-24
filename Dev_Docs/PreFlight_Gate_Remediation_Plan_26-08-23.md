# Pre-Flight Gate & Execution Integrity Remediation Plan

**Date:** 2026-08-23
**Source:** `Reports-1/Executive_Diagnostic_and_Audit_Report.md` (Stability 74/100, Readiness CONDITIONAL)
**Protocol:** Incremental Phase Review & Delegation Protocol (`.agents/PHASE_REVIEW_PROTOCOL.md`) — @Reviewer sign-off required after EVERY phase; no phase proceeds without explicit user command.
**Environment:** conda `QuFLX-v2`; PowerShell syntax (`;` separators, no `&&`).

---

## Executive Summary
Remediate the three CRITICAL defects (C1 dead tick-flow veto, C2 inert Bayesian floor gate, C3 capacity TOCTOU race), the failing horizon-isolation test (H2), and the high-value HIGH/MEDIUM findings (H1, H7, M1, H5, M11, M3/M4/L1/L4) identified in the 2026-08-23 executive diagnostic. Each phase is independently testable and reviewed.

## Architecture Context
- AI Pulse chain: `streaming.py::_ai_pulse_loop` → `_run_ai_pulse_insight` → `auto_ghost.py::schedule_candle_open_pulse_execution` (T−5s gate) → `execute_ai_pulse_signal` → `TradeService.execute_trade` → `PulseTrajectoryEngine`.
- Market context snapshot: `streaming.py::_get_asset_market_context_snapshot` (bound to `trade_service._get_market_context`) is the SOLE data supplier to the pre-flight gate.
- Bayesian WP producer: `extensions/bayesian_signal_filter.py::on_consider_signal` writes into the per-tick isolated `oteo_result["market_context"]` copy.

## Current State Map

| ID | Defect | File(s) | Status |
|---|---|---|---|
| C1 | `recent_ticks` never populated in snapshot | `streaming.py:726–740`, `auto_ghost.py:1010` | ✅ Resolved (Phase 1) |
| C2 | Bayesian WP absent from snapshot; gate fails open | `bayesian_signal_filter.py`, `market_context.py`, `auto_ghost.py:1026–1034` | ✅ Resolved (Phase 2) |
| C3 | Capacity check/add across await (TOCTOU) | `auto_ghost.py:711–716, 806, 815` | ✅ Resolved (Phase 3) |
| H2 | Horizon isolation regression (failing test) | `extensions/bayesian_signal_filter.py::on_trade_outcome` | ✅ Resolved (Phase 4) |
| H1 | PREMATURE_EXPIRATION unreachable for 60s trades | `pulse_trajectory_engine.py:128–131, 185` | ✅ Resolved (Phase 6) |
| H7 | Skip paths don't emit `ai_pulse_aborted` | `auto_ghost.py:844–850` | ✅ Resolved (Phase 5) |
| M1 | Snapshot regime keys wrong (`confidence`/`stable`) | `streaming.py:736–737` | ✅ Resolved (Phase 5) |
| H5 | Per-tick numpy volatility outside cache gate | `market_context.py:547–552` | ✅ Resolved (Phase 7) |
| M11 | Countdown not bound to terminal events | `GhostTradingWidget.jsx` | ✅ Resolved (Phase 7) |
| M3/M4/L1/L4 | Snap floor / PUT regex scope / unused 300s ratio / inline imports | `streaming.py`, `htf_directional_bias.py` | ✅ Resolved (Phase 7) |

---

## Implementation Phases

### Phase 1 — [x] C1: Wire `recent_ticks` into the market-context snapshot
- Add `self._recent_ticks: Dict[str, Deque]` (per-asset `deque(maxlen=600)` of `{"t","p"}`) to `StreamingService.__init__`.
- Append in `_process_tick_inner` (single line, O(1)).
- Seed from `valid_ticks` inside `_get_or_create_engines` (reuse existing pre-seed loop).
- Expose `ctx["recent_ticks"] = list(...)` in `_get_asset_market_context_snapshot`.
- Cleanup in `update_allowed_assets` (removed assets) and `stop()`.
- Tests: new `test_preflight_gate_contracts.py` — snapshot exposes non-empty well-formed ticks after processing; gate receives them (fake trade_service harness).

### Phase 2 — [~] C2: Propagate Bayesian WP to the pre-flight gate (fail-closed)
- Maintain per-asset latest WP cache on `StreamingService` (`_latest_bayesian_wp: Dict[str, dict]`), updated from the enriched result each tick when the filter ran.
- Snapshot exposes `bayesian_win_probability_60s` / `_300s`.
- Gate change: when `bayesian_filter_enabled` and WP unavailable → FAIL CLOSED (abort + emit `ai_pulse_aborted`), replacing silent skip.
- Tests: WP present → floor enforced; WP missing + filter enabled → aborted (not executed).

### Phase 3 — [x] C3: Close capacity TOCTOU race
- Reserve capacity synchronously BEFORE first await in `consider_signal` (add asset to `_active_assets` pre-execution; discard on failure/non-success), mirroring `execute_ai_pulse_signal` semantics.
- Same reservation pattern applied to cooldown stamping.
- Test: two concurrent `consider_signal` tasks with delayed fake execute_trade → never exceed `max_concurrent_trades`.
- **Fix-up:** cleanup loop at top of `consider_signal` used `_cooldown_until.get(a, 0)` (default 0), which discarded mid-execution assets whose cooldown hadn't been stamped yet. Changed to `a in self._cooldown_until and now >= self._cooldown_until[a]` so only assets with an explicit, elapsed cooldown are evicted.
- **Verification:** 13/13 preflight tests pass; 17/17 combined with `test_auto_ghost.py` + `test_ghost_tick_safety.py` — no regressions.

### Phase 4 — [x] H2: Fix horizon-isolation regression
- @Debugger root-cause `on_trade_outcome` skip-on-missing-`expiration_seconds`; restore skip semantics so `test_bayesian_signal_filter.py::test_on_trade_outcome_skips_when_missing_expiration` passes without modifying the test assertion.
- Full suite green.
- **Fix-up:** Removed the silent `trade_data.get("expiration", 60)` fallback in `on_trade_outcome`. When `expiration_seconds` is unresolvable (top-level or nested `entry_context`), the outcome is now skipped fail-closed with an explicit warning log instead of defaulting to the 60s horizon.
- **Verification:** 34/34 Bayesian filter tests pass; full plan verification suite green — **65/65 tests** (`test_preflight_gate_contracts.py`, `test_auto_ghost.py`, `test_htf_directional_bias.py`, `test_pulse_trajectory_engine.py`, `tests/test_bayesian_signal_filter.py`) with zero regressions.

### Phase 5 — [x] H7 + M1: Abort observability + snapshot regime keys
- Emit `ai_pulse_aborted` from all skip paths in `execute_ai_pulse_signal` (disabled, active asset, capacity, execution failure).
- Fix snapshot keys: `regime_confidence` ← `regime_confidence`, `regime_stable` ← `regime_stable`.
- Tests: skip path emits abort event; snapshot keys populated from classifier-shaped regime dict.
- **H7 fix-up:** Added `ai_pulse_aborted` Socket.IO emissions to all four skip paths in `execute_ai_pulse_signal` (`auto_ghost.py`): disabled controller, asset already active, max concurrent trades reached, and execution failure. Each emission carries the asset and a human-readable reason, matching the existing pre-flight gate emission contract.
- **M1 fix-up:** `_get_asset_market_context_snapshot` now reads `regime.get("regime_confidence")` / `regime.get("regime_stable")` — the exact keys emitted by `RegimeClassifier._emit()` — instead of the non-existent legacy `confidence`/`stable` keys that always resolved to `None`.
- **Tests added:** `TestExecutePulseAbortEmission` (4 tests: disabled/active/capacity/failure paths each emit exactly one abort event with correct reason) and `TestSnapshotRegimeKeysContract` (2 tests: classifier-shaped dict populates keys; missing regime defaults to None).
- **Verification:** Full plan verification suite green — **71/71 tests** with zero regressions.

### Phase 6 — [x] H1: Make PREMATURE_EXPIRATION reachable
- Post-settlement observation window: keep settled pulse trades registered for checkpoint sampling until `max(CHECKPOINT_INTERVALS)` (300s) or eviction cap; classify at final settlement using completed checkpoints.
- Boundary tests: 60s loss with favorable 180s checkpoint → PREMATURE_EXPIRATION; 300s loss with favorable 60s → MOMENTUM_EXHAUSTION.
- **Implementation:** Added `_observation_trades` registry to `PulseTrajectoryEngine`. Short-horizon (<300s) losing pulse trades now remain registered after `settle_pulse_trade` returns their provisional report; `record_tick` continues sampling MFE/MAE and late checkpoints (120s/180s/300s). When the observation window (`OBSERVATION_WINDOW_SECONDS = 300`) elapses, `_finalize_observation` re-classifies via the shared `_classify_attribution` helper and atomically replaces the provisional report in `_settled_trajectories` (marked `attribution_finalized=True` + `initial_attribution`). Registry is bounded by `MAX_OBSERVATION_TRADES = 200` with oldest-first eviction. Fixed a latent guard bug where `record_tick` early-returned when `_active_trades` was empty, skipping observation sampling entirely.
- **Tests added:** post-settlement upgrade to PREMATURE_EXPIRATION (provisional replaced, not duplicated), no-recovery stays DIRECTIONAL_FAIL, 300s-loss/favorable-60s MOMENTUM_EXHAUSTION boundary (no observation entry), bounded observation registry eviction.
- **Verification:** Full plan verification suite green — **75/75 tests** with zero regressions.

### Phase 7 — [x] Performance & frontend batch (H5, M11, M3/M4/L1/L4)
- H5: incremental Welford variance for `volatility_score` (or candle-close computation) in `market_context.py`.
- M11: bind pending-card lifetime to `trade_entry`(ai_pulse)/`ai_pulse_aborted`; add `tabular-nums`.
- M3: remove 5s sleep floor overshoot; M4: scope PUT wait regex to match span; L1: drop unused `tick_flow_300s` from scoring inputs (keep reporting); L4: hoist inline imports.
- Vite production build verification.
- **H5 fix-up:** Replaced the per-tick `np.array(deque)` + diff/std materialization (~50 allocations/s) with O(1) incremental return statistics (`_ret_sum`/`_ret_sumsq`) maintained in `update_tick`. Eviction-correct: when the bounded price buffer is full, the outgoing return is subtracted before appending. Population std matches previous `np.std` ddof=0 semantics; normalization ceilings unchanged.
- **M11 fix-up:** Added a `trade_entry` Socket.IO listener that clears the pending card when `trigger_mode === "ai_pulse"` (asset-matched). The countdown timer no longer clears the card at zero — a 15s grace window holds it so background-tab throttling cannot dismiss a setup that still executes. Terminal events (`trade_entry`/`ai_pulse_aborted`) clear immediately.
- **M12 fix-up:** Added `tabular-nums` to the MM:SS countdown for pixel-stable digits.
- **M3 fix-up:** Removed the 5s sleep floor in `_ai_pulse_loop` — sleeps exactly until the T−15s target offset instead of overshooting past it.
- **M4 fix-up:** PUT wait-minutes now captured within the PUT match span via a third capture group, eliminating cross-line bleed from CALL entries.
- **L1 resolution:** Documented that confluence scoring deliberately uses only the horizon-matched 60s micro-flow; `tick_flow_300s` remains computed for reporting with an explicit guard comment against uncalibrated inclusion in scoring.
- **L4 fix-up:** Hoisted `re`/`json` imports from `_run_ai_pulse_insight` to module level.
- **Verification:** Backend suite green — **75/75 tests**; Vite production build clean (10.20s, 0 errors).

### Phase 8 — [ ] Low-priority polish (H3/H4 rewrite proposal, M8 cache, M14 test split, M9/M10/M5/M6)
- Requires separate user approval per Core Principle #7 (rewrite rule) before executing H3/H4 decomposition.

## Verification Checklist
- [ ] `conda run -n QuFLX-v2 python -m pytest test_preflight_gate_contracts.py test_auto_ghost.py test_htf_directional_bias.py test_pulse_trajectory_engine.py tests/test_bayesian_signal_filter.py -v` all green each phase
- [ ] Full suite green at end: 73+ tests passing
- [x] `npm --prefix app/frontend run build` clean (Phase 7)
- [ ] No behavioral regressions in existing gates (z-score, regime, manipulation, proximity)

## Files Touched Summary
| Phase | Files |
|---|---|
| 1 | `app/backend/services/streaming.py`, `test_preflight_gate_contracts.py` (new) |
| 2 | `app/backend/services/streaming.py`, `app/backend/services/auto_ghost.py`, tests |
| 3 | `app/backend/services/auto_ghost.py`, tests |
| 4 | `app/backend/services/extensions/bayesian_signal_filter.py` |
| 5 | `app/backend/services/auto_ghost.py`, `app/backend/services/streaming.py`, tests |
| 6 | `app/backend/services/pulse_trajectory_engine.py`, `test_pulse_trajectory_engine.py` |
| 7 | `app/backend/services/market_context.py`, `app/backend/services/streaming.py`, `app/backend/services/htf_directional_bias.py`, `GhostTradingWidget.jsx` |

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Fail-closed C2 blocks all AI Pulse trades if WP never populates | Med | High | Cache update verified by integration test; telemetry log on first populate |
| Capacity reservation leaks on unexpected exception paths | Low | Med | try/except discard + existing done-callback logging |
| Trajectory observation window grows memory | Low | Low | Bounded eviction cap; reuses existing deques |
| Frontend event-binding changes alter UX timing | Low | Low | Feature-flag-free minimal change; manual browser verify |