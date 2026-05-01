# Active Context

## Summary
- This file tracks the immediate working state of the project
- The Auto-Ghost trader executed a 401-trade test session, providing data that drove Phase A (Critical Fixes) and Phase B (Policy Tuning) of the Level 2 Implementation Plan
- Critical issues involving per-tick recomputation, Auto-Ghost task leaks, and Manipulation Detection accuracy have been successfully resolved
- The Level 2 policy has been converted into a formalized `Level2PolicyConfig` dataclass and tightened based on data-driven analysis
- The frontend trading workspace has been refined for maximum focus on live/demo execution, while the Auto-Ghost trader operates in the background to provide a low-risk data stream for OTEO Strategy improvement and market behavior analysis.
- The UI now features modular mini-chart cards, per-asset session stats, and a high-fidelity OTEO gauge with manipulation and confluence detail.
- **TRAE session fixes (2026-04-27) are fully implemented and closed.** All 8 issues from the executive report and expert review have been remediated across 6 files.
- **Level 3 implementation is now active in execution.** Phases 0, 1, and 2 of `Dev_Docs/Level3_Implementation_Plan_26-04-29.md` have been completed, validated, and signed off on 2026-05-01. The pre-Phase-3 hardening pass is also complete. Phase 3 has not started yet.

## Latest Changes

### Applied on 2026-04-27 — TRAE Session Fixes (CLOSED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| A.1 | Critical Runtime Fix | `app/backend/api/session.py` | Added `request: Request` param to `auto_connect_session` — resolved `NameError` that silently broke streaming reconnect on the auto-connect path. |
| B.1 | Confidence Contract | `app/backend/models/requests.py` | Added Pydantic `field_validator` to `TradeExecutionRequest.confidence`: accepts `str`, numeric, or `None`; normalizes numerics to `HIGH`/`MEDIUM`/`LOW`; includes `bool` guard. Resolves the 422 rejection blocking manual live trade execution. |
| B.3 | Signal Transport | `app/frontend/src/hooks/useStreamConnection.js` | Cleaned signal object (no duplicate `score`/`label`/`marketContext` aliases); added JSDoc to `normalizeConfidence`. |
| C.1 | Error Handling | `app/frontend/src/api/httpClient.js` | FastAPI 422 `detail` array is now parsed into human-readable field-level messages instead of `[object Object]`. |
| C.2 | Demo Flag | `app/frontend/src/stores/useTradingStore.js` | `demo` flag in trade payload now reads from `useOpsStore.accountType` instead of being hardcoded `false`. |
| D.3 | Performance | `app/backend/services/streaming.py` | `_resolve_asset_payout_pct` now uses a 60s TTL cache (`_payout_cache`) to eliminate repeated broker IO on the hot tick path. |

**Source:** `Dev_Docs/TRAE_Fixes_Implementation_Plan_26-04-27.md` — Plan closed 2026-04-28. All 4 phases (A→D) verified via Phase Review Protocol.

### Applied on 2026-05-01 — Level 3 Phase 0 (SIGNED OFF ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| L3-P0.1 | Strategy Tagging | `app/backend/services/streaming.py` | Injected `level3_enabled` into enriched results and payloads so downstream consumers can correctly tag Level 3 trades. |
| L3-P0.2 | Live Outcome Reliability | `app/backend/services/trade_service.py` | Added explicit done-callback logging for live `_track_trade_outcome()` tasks to prevent silent background failures. |
| L3-P0.3 | Candle Semantics | `app/backend/services/market_context.py` | Fixed first-tick behavior so the initial candle no longer marks `candle_closed=True` and triggers premature indicator recomputation. |
| L3-P0.4 | Macro S/R Fallback | `app/backend/services/market_context.py` | Replaced absolute min/max fallback with percentile-based macro support/resistance levels. |
| L3-P0.5 | Config Truth Source | `app/backend/services/market_context.py` | Routed `distant_structure_atr` through `market_context` so Level 2 policy no longer relies on a hardcoded threshold. |

**Source:** `Dev_Docs/Level3_Implementation_Plan_26-04-29.md` — Status now `In Progress`; Phase 0 signed off 2026-05-01; subsequent backend phases continue below.

### Applied on 2026-05-01 — Level 3 Phase 1 (SIGNED OFF ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| L3-P1.1 | Regime Classifier | `app/backend/services/regime_classifier.py` | Added deterministic `RegimeClassifier` with persisted regime state, confidence scoring, and stability tracking. |
| L3-P1.2 | Candle-Close Contract | `app/backend/services/market_context.py` | Exposed `candle_closed` in returned `market_context` without breaking the cached closed-candle computation model. |
| L3-P1.3 | Streaming Integration | `app/backend/services/streaming.py` | Added per-asset Level 3 classifier lifecycle, persisted `_last_regime`, runtime-toggle invalidation, and regime payload emission. |
| L3-P1.4 | Validation | `test_level3_phase1.py` | Added focused tests for candle-close semantics, regime persistence, runtime-toggle clearing, and classifier recreation after re-enable. |

### Applied on 2026-05-01 — Level 3 Phase 2 (SIGNED OFF ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| L3-P2.1 | Policy Layer | `app/backend/services/market_context.py` | Added `Level3PolicyConfig` and `apply_level3_policy()` to adjust score, confidence, and actionable state from the persisted regime. |
| L3-P2.2 | Streaming Wiring | `app/backend/services/streaming.py` | Wired Level 3 policy after Level 2, emitted `level3_score_adjustment` / `level3_suppressed_reason`, and included regime metadata in the streaming payload and signal logs. |
| L3-P2.3 | Trade Audit Context | `app/backend/services/auto_ghost.py` | Preserved Level 3 score adjustment, suppression reason, and regime metadata inside ghost-trade `entry_context` for downstream analysis. |
| L3-P2.4 | Validation | `test_level3_phase2.py` | Added focused tests for range boost, pullback suppression, choppy suppression, fail-fast enum validation, and non-actionable early-return behavior. |

### Applied on 2026-05-01 — Level 3 Pre-Phase-3 Hardening (COMPLETED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| L3-H.1 | Signal Journal Analytics | `app/backend/services/streaming.py` | Added `regime_confidence` and `regime_stable` to `signal_logger.log_signal()` payloads so later journal analytics can distinguish low-confidence/flapping regimes from stable regimes. |
| L3-H.2 | Regime Transition Coverage | `test_level3_phase1.py` | Added focused classifier transition coverage for `CHOPPY → TREND_PULLBACK → STRONG_MOMENTUM`, including `regime_prior` assertions. |

**Validation:** `conda run -n QuFLX-v2 python -m unittest test_level3_phase1.py test_level3_phase2.py` passed with 10 tests.

### Applied on 2026-04-06

| Area | File(s) | Outcome |
|------|---------|---------|
| Performance Fix | `app/backend/services/market_context.py` | Resolved ISSUE-01: Added `_cached_context` so heavy indicators (ADX/CCI/Pivots) only compute strictly on closed candles, eliminating O(n) CPU waste and indicator noise. |
| Reliability Fix | `app/backend/services/auto_ghost.py` | Resolved ISSUE-02 & ISSUE-09: Added unhandled exception callbacks to `_release_asset` tasks and pre-flight stale-asset cleanup in `consider_signal()` to prevent permanent lock leaks. |
| Signal Quality | `app/backend/services/market_context.py` | Resolved ISSUE-03, 04 & 06: Extracted magic numbers into `Level2PolicyConfig`. Tightened Support/Resistance proximity to `0.25` ATR. Increased penalties for `neutral` CCI and `unavailable`/`weak` ADX regimes. Added a hard floor for `HIGH` confidence. |
| Manipulation Logic | `app/backend/services/manipulation.py` | Resolved ISSUE-07 & logic flaws: Replaced hardcoded `0.1` dt with exact timestamps. Added a 15-second memory block for velocity spikes (Push & Snap). Loosened pinning tolerance to check the overall price range instead of strict decimals. |
| Frontend Polish | `app/frontend/src/App.jsx` | Resolved ISSUE-10: Wrapped `syncRuntimeConfig` in a 400ms debounce to prevent HTTP POST spam during rapid UI toggling. |
| Documentation | `@reports/401Trades_Level2_Ghost_Trade_report_26-04-06.md` | Compiled the findings and logic fixes from the 401-trade ghost session. |

### Applied on 2026-04-07

| Area | File(s) | Outcome |
|------|---------|---------|
| Session Stats | `app/frontend/src/stores/useRiskStore.js`, `app/frontend/src/App.jsx` | Added per-asset session win/loss tracking (`assetStats`) and wired trade-result updates so mini-chart cards can display live W/L context per asset. |
| Mini-Chart UX | `app/frontend/src/components/trading/MultiChartView.jsx`, `app/frontend/src/components/settings/AppSettings.jsx`, `app/frontend/src/stores/useSettingsStore.js` | Added modular mini-chart toggles, card starring, double-click focus selection, regime chips, manipulation pulse, and larger hover gauges. |
| Main Gauge Explainability | `app/frontend/src/hooks/useStreamConnection.js`, `app/frontend/src/components/trading/TradingWorkspace.jsx`, `app/frontend/src/components/trading/OTEORing.jsx` | Enriched the frontend signal model with `market_context`, Level 2 metadata, and manipulation flags. The main OTEO ring now displays active manipulation types and confluence badges for pressure, z-score, trend/context alignment, maturity, and Level 2 effects. |
| Visual Polish | `app/frontend/src/components/trading/OTEORing.jsx`, `app/frontend/src/components/trading/MultiChartView.jsx` | Neutral state styling now uses blue, and mini-chart gauge overlays were enlarged for stronger visual emphasis. |
| Stability Fix | `app/frontend/src/components/trading/MultiChartView.jsx` | Hardened Zustand selectors against missing store branches (`contexts`, `manipulations`) to stop runtime crashes in the multi-chart view. |

### Applied on 2026-04-09

| Area | File(s) | Outcome |
|------|---------|---------|
| UI Refinement | `useSettingsStore.js`, `useTradingStore.js`, `TradePanel.jsx`, `AppSettings.jsx` | Streamlined workspace UI by removing manual Ghost Mode controls to prevent user confusion. Manual execution now defaults strictly to the active SSID environment. |
| Auto-Ghost VX | `App.jsx`, `trade_service.py` | Enhanced Auto-Ghost visibility with detailed toast notifications (Asset + Expiry) upon background execution, driven by new `trigger_mode` metadata in the backend payload. |
| Component Cleanup | `GhostTradingBanner.jsx` | Deleted legacy banner component, simplifying the `MainLayout` DOM tree. |

### Applied on 2026-04-08

| Area | File(s) | Outcome |
|------|---------|---------|
| Stability Fix | `app/frontend/src/components/trading/Sparkline.jsx` | Fixed a critical runtime crash caused by missing `direction` fields in trade markers, and resolved a UI glitch displaying `NaN` for undefined profit values. |
| Performance Fix | `app/frontend/src/components/trading/chartUtils.js`, `Sparkline.jsx` | Prevented `RangeError` call stack overflows on large tick arrays by replacing `Math.min/max` spread operators with standard loops. Consolidated duplicate bounding operations into a single hygienic `useMemo`. |

## Evidence
- Smoke tests (`test_auto_ghost.py`) passed successfully confirming the new `Level2PolicyConfig` and `ManipulationDetector` logic works without regressions.
- The `check_manipulation.py` and `check_tick_gaps.py` scripts verified that the prior manipulation logic was too fleeting to block the trades, leading to the logic hardening.

## Current State
- The Level 2 OTEO backend foundation is fully operational, performant, and tuned for stricter exhaustion reversals.
- Manipulation Detection now has state persistence (15s block on spikes) and realistic OTC pinning bounds.
- Auto-Ghost is hardened against silent asyncio task failures and stale locks, serving as the project's primary data-gathering engine.
- The trading workspace UI is leaner and more focused, exposing interpretable signal context, manipulation labels, and live confluence badges without simulation mode overlap.
- Multi-chart cards are modular, performant, and user-configurable, with per-asset stats and improved focus/watchlist interactions.
- The Level 3 implementation plan is now in execution state with Phases 0, 1, and 2 completed and signed off. The recommended pre-Phase-3 hardening pass is complete, so the codebase is ready for Phase 3 when explicitly approved.

## Validation
- Python compile and smoke tests passed successfully
- Frontend build and UI rendering validated successfully
- The latest frontend build passed after the multi-chart modularization, confluence-gauge enhancements, and selector hardening
- 401 ghost trades were successfully captured and analyzed, proving the end-to-end pipeline works perfectly.
- `python -m py_compile app/backend/services/streaming.py app/backend/services/market_context.py app/backend/services/trade_service.py` passed after the Level 3 Phase 0 edits.
- `conda run -n QuFLX-v2 python -m py_compile app/backend/services/regime_classifier.py app/backend/services/market_context.py app/backend/services/streaming.py app/backend/services/auto_ghost.py test_level3_phase1.py test_level3_phase2.py` passed after Levels 3 Phases 1 and 2.
- `conda run -n QuFLX-v2 python -m unittest test_level3_phase1.py test_level3_phase2.py` passed with 10 tests after the pre-Phase-3 hardening pass.
- Diagnostics were clean for `regime_classifier.py`, `market_context.py`, `streaming.py`, `auto_ghost.py`, `test_level3_phase1.py`, and `test_level3_phase2.py` after the Phase 2 review gate.

## Active Risks
- The tighter Level 2 policy and stricter manipulation detector will likely reduce total trade frequency. The next live test cycle needs to verify if the win-rate improvement justifies the volume reduction.
- Confluence badges are currently limited to the signal and `market_context` fields already emitted in the live payload. Any deeper explainability will require additional backend signal metadata.
- `raw_confidence` (categorical string from backend) is not yet forwarded into the frontend signal object. Currently the backend validator (B.1) handles normalization server-side, which is sufficient — but if a future UI element needs the raw label, this remains an optional add (B.3 from TRAE plan).
- Focused automated coverage now exists for Phase 1 and Phase 2 logic, including regime transition behavior. Broader end-to-end runtime coverage around `StreamingService` and `MarketContextEngine` remains limited.
- Phase 2 stores Level 3 audit metadata in ghost-trade `entry_context` rather than new top-level trade fields. This is acceptable for the current plan state, but deeper journal analytics may later prefer explicit first-class columns.

## Next Steps
- **Run a live manual trade session** to confirm the full confidence contract fix (B.1) works end-to-end: numeric confidence → backend validator → `HIGH`/`MEDIUM`/`LOW` stored in journal.
- Run a new Auto-Ghost session to benchmark the new `Level2PolicyConfig` and hardened Manipulation Detector.
- Begin **Phase 3** of `Dev_Docs/Level3_Implementation_Plan_26-04-29.md` when explicitly approved.
- Validate the new confluence badges and larger mini-chart gauges during a live session to confirm readability under real streaming load.

## Environment Notes
- Backend start: `conda run -n QuFLX-v2 python -m uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend dev: `cd C:\v3\OTC_SNIPER\app\frontend; npm run dev`
- Frontend build: `npm --prefix C:\v3\OTC_SNIPER\app\frontend run build`
- Conda environment: `QuFLX-v2`
