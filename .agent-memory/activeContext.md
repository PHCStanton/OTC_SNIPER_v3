# Active Context

## Summary
- This file tracks the immediate working state of the project.
- **Independent AI Layer Toggle (2026-06-10) is fully implemented, verified, and closed.** Decoupled the AI advisory/model logic from Level 3. Added a dedicated AI toggle button next to Level 1, 2, and 3 buttons in the settings panel card, syncing it to the backend and tracking it in logs/payloads.
- **Lagging and Latency Optimizations (2026-06-05) are fully implemented, verified, and closed.**
- The Auto-Ghost trader's 401-trade evidence set already drove the Level 2 hardening and tuning work; that foundation remains stable.
- **TRAE session fixes (2026-04-27) remain fully implemented and closed.**
- **Level 3 Phases 0, 1, 2, and 3 are now complete.** Phase 3 passed the multi-agent review gate on 2026-05-02, the user approved continuation, and the full low-severity remediation pass is complete.
- **OTEO Level Backtest Plan (2026-05-15) is now fully closed.** All 4 phases implemented, reviewed, and signed off.
- The next valid implementation target is **Phase 4: AI Advisory Review Loop** in `Dev_Docs/Level3_Implementation_Plan_26-04-29.md`.
- A separate planning track is now documented in `Dev_Docs/L123_Optimization_and_AI_Knowledge_Base_Plan_26-05-16.md`; if approved, its next implementation step is `Phase 1 - Analyzer Core and Join Validation`.

## Latest Changes

### Applied on 2026-06-10 — Independent AI Layer Toggle (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| AI-T0 | AI State Settings | `app/frontend/src/stores/useSettingsStore.js`, `app/frontend/src/App.jsx` | Added `oteoAiEnabled` setting to the frontend store and synced it to the backend under the `oteo_ai_enabled` field. |
| AI-T1 | settings Card UI | `app/frontend/src/components/settings/AppSettings.jsx`, `app/frontend/src/components/layout/TopBar.jsx` | Renamed `Level 3 (AI)` button to `Level 3` and exported the reusable `AiChipIcon` from TopBar. Placed the independent AI button next to Level 1/2/3 indicators inside the OTEO Signal Layer settings card with matching selected/deselected glow effects. |
| AI-T2 | Backend Router & Streaming | `app/backend/api/strategy.py`, `app/backend/services/streaming.py` | Updated FastAPI routes and the streaming service configuration to receive `oteo_ai_enabled`. Added a defensive check to prevent AttributeError on test stubs. Passed the setting to Socket.IO ticks payload, signal loggers, and AutoGhost signals. |
| AI-T3 | Auto-Ghost Logger | `app/backend/services/auto_ghost.py` | Appended the status of `oteo_ai_enabled` inside the Auto-Ghost trade entry context for better analytical reporting. |

### Applied on 2026-06-06 — UI Refactoring (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| UI-R0 | Sparkline Dot Visibility | `app/frontend/src/components/trading/chartUtils.js`, `app/frontend/src/components/trading/Sparkline.jsx` | Added a custom `paddingRight` parameter to `buildChartPoints` (set to 180 in Sparkline) to shift the right boundary of the sparkline leftwards. Connected the latest price dot to the right axis with a dashed tracker line and updated the "Last Price" yellow label box with a semi-transparent background and blur backdrop to prevent dot overlap. |
| UI-R1 | Chart/Runs Toggle | `app/frontend/src/components/layout/RightSidebar.jsx` | Moved the Chart/Runs view toggle from the sidebar top header to a layout position directly below the Call/Put action cards grid, resolving accidental button-clicking. |
| UI-R2 | Session P&L Header Relocation | `app/frontend/src/components/layout/RightSidebar.jsx` | Relocated Session P&L value and status icon next to the "Session Risk" header title, removing the large dedicated Card element to save vertical space. |
| UI-R3 | Session P&L Font Size | `app/frontend/src/components/layout/RightSidebar.jsx` | Increased P&L value font-size to text-sm and weight to black (900) in the header for easier reading under trading pressure. |
| UI-R4 | Session Reset Button Relocation | `app/frontend/src/components/layout/RightSidebar.jsx` | Added a gold refresh-styled session reset button directly to the left of the Chart/Runs toggle, wired to the backend session reset action. |

## Current State
- **Performance:** Event-loop blocking has been completely eliminated. Broker ticks are queued thread-safely and written to disk in background memory-buffered cycles.
- **Frontend Optimization:** Zustand store state is split; components only render on target changes. Throttled ticks render at a stable 10 FPS max, and lazy-rendered gauges avoid DOM/layout recalculations.
- **Independent AI Toggle:** Users can now enable/disable the AI Layer independently in the Settings panel OTEO Signal card. Selecting/deselecting the AI button lights it up using a golden glow effect, mirroring the TopBar.
- The Level 2 OTEO backend foundation remains operational, performant, and tuned for stricter exhaustion reversals.
- The Level 3 implementation plan is active with **Phases 0, 1, 2, and 3 completed and signed off**.
- Phase 4 (AI Advisory Review Loop) has not started.

## Validation
- **Backend Compilation:** `conda run -n QuFLX-v2 python -m py_compile app/backend/services/streaming.py app/backend/services/tick_logger.py app/backend/services/perf_monitor.py app/backend/session/pocket_option_session.py` -> ✅ passed.
- **Frontend Production Build:** `npm run build` inside `app/frontend` -> ✅ passed (built successfully in 10.52s).
- **Backend Unit Tests:** `conda run -n QuFLX-v2 python -m unittest test_backtest_oteo_levels.py test_level3_phase1.py test_level3_phase2.py test_level3_phase3.py` -> ✅ passed (39/39).

## Active Risks
- Runtime validation is needed in a live trading session to verify the performance telemetry metrics (lag, queue lengths, processing percentiles) are stable under high market volatility.
- Auto-Ghost execution cooldowns and win-rate condition stats need tracking during the next active session.

## Next Steps
- Begin **Phase 4** of `Dev_Docs/Level3_Implementation_Plan_26-04-29.md` (AI Advisory Review Loop) when explicitly approved.
- Start a live or ghost session to observe telemetry stats and verify the new `PerformanceMonitor` outputs in the console / explainability UI.
- If explicitly approved, begin `Phase 1 - Analyzer Core and Join Validation` from `Dev_Docs/L123_Optimization_and_AI_Knowledge_Base_Plan_26-05-16.md`.

## Environment Notes
- Backend start: `conda run -n QuFLX-v2 python -m uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend dev: `cd C:\v3\OTC_SNIPER\app\frontend; npm run dev`
- Frontend build: `npm --prefix C:\v3\OTC_SNIPER\app\frontend run build`
- Conda environment: `QuFLX-v2`
