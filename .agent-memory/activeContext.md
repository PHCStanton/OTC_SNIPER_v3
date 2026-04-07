# Active Context

## Summary
- This file tracks the immediate working state of the project
- The Auto-Ghost trader executed a 401-trade test session, providing data that drove Phase A (Critical Fixes) and Phase B (Policy Tuning) of the Level 2 Implementation Plan
- Critical issues involving per-tick recomputation, Auto-Ghost task leaks, and Manipulation Detection accuracy have been successfully resolved
- The Level 2 policy has been converted into a formalized `Level2PolicyConfig` dataclass and tightened based on data-driven analysis

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

## Evidence
- Smoke tests (`test_auto_ghost.py`) passed successfully confirming the new `Level2PolicyConfig` and `ManipulationDetector` logic works without regressions.
- The `check_manipulation.py` and `check_tick_gaps.py` scripts verified that the prior manipulation logic was too fleeting to block the trades, leading to the logic hardening.

## Current State
- The Level 2 OTEO backend foundation is fully operational, performant, and tuned for stricter exhaustion reversals.
- Manipulation Detection now has state persistence (15s block on spikes) and realistic OTC pinning bounds.
- Auto-Ghost is hardened against silent asyncio task failures and stale locks.

## Validation
- Python compile and smoke tests passed successfully
- Frontend build and UI rendering validated successfully
- 401 ghost trades were successfully captured and analyzed, proving the end-to-end pipeline works perfectly.

## Active Risks
- The tighter Level 2 policy and stricter manipulation detector will likely reduce total trade frequency. The next live test cycle needs to verify if the win-rate improvement justifies the volume reduction.
- Macro S/R fallback still uses absolute min/max (ISSUE-11 - LOW severity), which is non-critical but noted for future polish.

## Next Steps
- Run a new Auto-Ghost session to benchmark the new `Level2PolicyConfig` and hardened Manipulation Detector.
- Begin outlining Level 3 Regime Classification logic now that the Level 2 foundation is stable and performant.

## Environment Notes
- Backend start: `conda run -n QuFLX-v2 python -m uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend dev: `cd C:\v3\OTC_SNIPER\app\frontend; npm run dev`
- Frontend build: `npm --prefix C:\v3\OTC_SNIPER\app\frontend run build`
- Conda environment: `QuFLX-v2`