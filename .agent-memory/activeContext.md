# Active Context

## Summary
- This file tracks the immediate working state of the project
- The Auto-Ghost trader has been successfully implemented and validated to work alongside the Level 2 OTEO context filter
- CCI confirmation is already implemented in the Level 2 policy; the current focus is on tuning and stabilizing the Level 2 engine before any broader regime work
- A critical performance/accuracy issue was identified in `app/backend/services/market_context.py` and documented in `Dev_Docs/Level2_Implementation_Plan_26-04-04.md`

## Latest Changes
### Applied on 2026-04-06

| Area | File(s) | Outcome |
|------|---------|---------|
| Level 2 Plan Reconciliation | `Dev_Docs/Level2_Implementation_Plan_26-04-04.md` | Corrected stale status markers, added severity-rated issue tracker, and updated implementation order so critical fixes come before tuning. |
| Working State Handoff | `.agent-memory/activeContext.md`, `.agent-memory/progress.md`, `.agent-memory/previousTaskSession.md` | Refreshed memory files to reflect the current review findings and the fact that implementation is paused pending approval. |

### Applied on 2026-04-04

| Area | File(s) | Outcome |
|------|---------|---------|
| Auto-Ghost Logic | `app/backend/services/auto_ghost.py` | Built the AutoGhostService to manage simulated trades concurrently with per-asset cooldowns and manipulation blocking. |
| Streaming Integration | `app/backend/services/streaming.py` | Integrated `AutoGhostService` to automatically execute paper trades when actionable signals are emitted. |
| UI Controls & Display | `app/frontend/src/App.jsx`, `AppSettings.jsx`, `useStreamConnection.js` | Added Auto-Ghost config sync and corrected the Confidence Gauge (`OTEORing`) to accurately display exact `oteo_score` percentages. |
| Ghost Trade Path | `app/backend/data/local_store.py` | Fixed a bug where ghost trades were saved in the `live_trades` folder by correctly resolving Pydantic Enum serialization for `TradeKind`. |

## Evidence
- Auto-Ghost trade records are correctly writing to `app/data/ghost_trades/sessions/*.jsonl`
- Sparklines, confidence gauges, and trade execution events successfully operate over the restored Socket.IO connection
- All smoke tests in `test_auto_ghost.py` pass within the `QuFLX-v2` Conda environment

## Current State
- The Level 2 OTEO backend foundation is fully operational
- Auto-Ghost is active and correctly captures paper trades without risking live capital
- Realtime streaming and UI visualizations are working correctly
- Trade execution uses HTTP and remains stable

## Validation
- Python compile and smoke tests (`test_auto_ghost.py`) passed successfully
- Frontend build and UI rendering validated successfully
- Verified that ghost session records are isolated from live trade logs

## Active Risks
- The Level 2 policy still requires operational tuning, but tuning should not start until the per-tick recomputation issue is fixed
- `market_context.py` currently recomputes ADX/CCI/pivots on incomplete candles, which can distort tuning signals and waste CPU
- Weak/unavailable ADX regimes are still not penalized enough, and the S/R proximity band is still too broad
- Fire-and-forget Auto-Ghost cleanup and manipulation timing logic need hardening before relying on edge-case runtime behavior

## Next Steps
- Wait for approval to proceed with Phase A critical fixes
- Fix candle-close caching / indicator recomputation in `market_context.py`
- Harden Auto-Ghost task cleanup and stale active-asset handling
- Then tune ADX regime penalties and S/R thresholds using the cleaned context data
- Continue towards Level 3 regime classification after Level 2 stabilizes

## Environment Notes
- Backend start: `conda run -n QuFLX-v2 python -m uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend dev: `cd C:\v3\OTC_SNIPER\app\frontend; npm run dev`
- Frontend build: `npm --prefix C:\v3\OTC_SNIPER\app\frontend run build`
- Conda environment: `QuFLX-v2`