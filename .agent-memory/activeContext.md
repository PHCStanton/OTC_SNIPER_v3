# Active Context

## Summary
- This file tracks the immediate working state of the project
- The Auto-Ghost trader executed a 401-trade test session, providing data that drove Phase A (Critical Fixes) and Phase B (Policy Tuning) of the Level 2 Implementation Plan
- Critical issues involving per-tick recomputation, Auto-Ghost task leaks, and Manipulation Detection accuracy have been successfully resolved
- The Level 2 policy has been converted into a formalized `Level2PolicyConfig` dataclass and tightened based on data-driven analysis
- The frontend trading workspace has now been upgraded with modular mini-chart cards, per-asset session stats, and a more explainable main OTEO gauge with manipulation and confluence detail

## Latest Changes
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
- Auto-Ghost is hardened against silent asyncio task failures and stale locks.
- The trading workspace UI is stable and now exposes more interpretable signal context, including manipulation labels and live confluence badges.
- Multi-chart cards are modular, performant, and user-configurable, with per-asset stats and improved focus/watchlist interactions.

## Validation
- Python compile and smoke tests passed successfully
- Frontend build and UI rendering validated successfully
- The latest frontend build passed after the multi-chart modularization, confluence-gauge enhancements, and selector hardening
- 401 ghost trades were successfully captured and analyzed, proving the end-to-end pipeline works perfectly.

## Active Risks
- The tighter Level 2 policy and stricter manipulation detector will likely reduce total trade frequency. The next live test cycle needs to verify if the win-rate improvement justifies the volume reduction.
- Macro S/R fallback still uses absolute min/max (ISSUE-11 - LOW severity), which is non-critical but noted for future polish.
- Confluence badges are currently limited to the signal and `market_context` fields already emitted in the live payload. Any deeper explainability will require additional backend signal metadata.

## Next Steps
- Run a new Auto-Ghost session to benchmark the new `Level2PolicyConfig` and hardened Manipulation Detector.
- Begin outlining Level 3 Regime Classification logic now that the Level 2 foundation is stable and performant.
- Validate the new confluence badges and larger mini-chart gauges during a live session to confirm readability under real streaming load.

## Environment Notes
- Backend start: `conda run -n QuFLX-v2 python -m uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend dev: `cd C:\v3\OTC_SNIPER\app\frontend; npm run dev`
- Frontend build: `npm --prefix C:\v3\OTC_SNIPER\app\frontend run build`
- Conda environment: `QuFLX-v2`
