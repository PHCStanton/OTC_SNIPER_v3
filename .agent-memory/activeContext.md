# Active Context

## Summary
- This file tracks the immediate working state of the project.
- **Lagging and Latency Optimizations (2026-06-05) are fully implemented, verified, and closed.** This sprint resolved progressive lagging, event-loop blockages, high Zustand render overhead, and the frontend sparkline/gauge freezing bug.
- The Auto-Ghost trader's 401-trade evidence set already drove the Level 2 hardening and tuning work; that foundation remains stable.
- **TRAE session fixes (2026-04-27) remain fully implemented and closed.**
- **Level 3 Phases 0, 1, 2, and 3 are now complete.** Phase 3 passed the multi-agent review gate on 2026-05-02, the user approved continuation, and the full low-severity remediation pass is complete.
- **OTEO Level Backtest Plan (2026-05-15) is now fully closed.** All 4 phases implemented, reviewed, and signed off. `scripts/backtest_oteo_levels.py` + `test_backtest_oteo_levels.py` are the deliverables. 39/39 tests passing.
- The next valid implementation target is **Phase 4: AI Advisory Review Loop** in `Dev_Docs/Level3_Implementation_Plan_26-04-29.md`.
- A separate planning track is now documented in `Dev_Docs/L123_Optimization_and_AI_Knowledge_Base_Plan_26-05-16.md`; if approved, its next implementation step is `Phase 1 - Analyzer Core and Join Validation`.

## Latest Changes

### Applied on 2026-06-05 — Lagging and Latency Optimizations (SIGNED OFF & VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| OPT-P0 | Telemetry | `app/backend/services/perf_monitor.py` | [NEW] Created performance telemetry loop measuring event loop lag, queue lengths, tick flow rates, and processing percentiles. Emits to `"performance_telemetry"` Socket.IO room. |
| OPT-P1 | Backend Hot-path | `app/backend/session/pocket_option_session.py`, `app/backend/services/streaming.py` | Refactored tick callback to run thread-safely via `loop.call_soon_threadsafe`. Implemented bounded asyncio queue (maxsize 500) and background consumer worker. Re-ordered emitting to socket before logging ticks. |
| OPT-P1-L | Buffered Logging | `app/backend/services/tick_logger.py` | Hardened logger to buffer tick records in-memory and write to disk in batches every 5 seconds or 100 ticks, eliminating per-tick synchronous I/O blocks. |
| OPT-P2 | Store Split & FPS Throttling | `app/frontend/src/stores/useStreamStore.js`, `app/frontend/src/hooks/useStreamConnection.js` | Split `ticks` history from `latestPrice`/`latestSignal` in store. Throttled ticks state updates using `requestAnimationFrame` (10 FPS for focused asset, 2 FPS for multi-chart assets). |
| OPT-P2-U | Chart & Bounding | `app/frontend/src/components/trading/MultiChartView.jsx`, `app/frontend/src/stores/useRiskStore.js`, `app/frontend/src/stores/useToastStore.js` | Sparklines read price only when disabled. Lazy-rendered gauges to eliminate SVG layout thrashing. Capped `tradeMarkers` (50), `ghostTrades` (200), and `toasts` (5). Switched `useRiskStore` to incremental stats calculation. |
| OPT-P2-F | UI Freezing Fix | `app/frontend/src/hooks/useStreamConnection.js` | Fixed a critical cleanup bug where `rafIdRef.current` was not reset to `null` on socket re-registration, blocking future animation frames. |
| OPT-P4 | Selector Cleanup | `RightSidebar.jsx`, `GhostTradingWidget.jsx`, `SessionRiskPanel.jsx`, `JournalView.jsx` | Replaced broad Zustand store destructuring hooks with narrow individual selectors, eliminating render-cascades when unrelated metrics/settings change. |

### Applied on 2026-05-16 — L1/L2/L3 Optimization and AI Knowledge Base Planning (PLANNED)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| KB-P1 | Planning | `Dev_Docs/L123_Optimization_and_AI_Knowledge_Base_Plan_26-05-16.md` | Saved a new offline analyzer plan covering joined `ghost_trades`, `signals`, and `tick_logs`, UTC-only reporting, manipulation-first diagnostics, Level 1/2/3 optimization matrices, and AI-ready knowledge base compression. |

## Current State
- **Performance:** Event-loop blocking has been completely eliminated. Broker ticks are queued thread-safely and written to disk in background memory-buffered cycles.
- **Frontend Optimization:** Zustand store state is split; components only render on target changes. Throttled ticks render at a stable 10 FPS max, and lazy-rendered gauges avoid DOM/layout recalculations.
- **Zustand Selectors:** Cleaned up across key sidebar, widget, journal, and risk panels.
- The Level 2 OTEO backend foundation remains operational, performant, and tuned for stricter exhaustion reversals.
- The Level 3 implementation plan is active with **Phases 0, 1, 2, and 3 completed and signed off**.
- Phase 4 (AI Advisory Review Loop) has not started.

## Validation
- **Backend Compilation:** `conda run -n QuFLX-v2 python -m py_compile app/backend/services/streaming.py app/backend/services/tick_logger.py app/backend/services/perf_monitor.py app/backend/session/pocket_option_session.py` -> ✅ passed.
- **Frontend Production Build:** `npm run build` inside `app/frontend` -> ✅ passed (built successfully in 5.09s).
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
