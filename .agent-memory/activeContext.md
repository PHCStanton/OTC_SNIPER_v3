# Active Context

## Current Work
**Three critical gaps fixed — live tick subscription, live payout fetch, payout UI badge**

### Fixes Applied (2026-03-31)

| Gap | File(s) Changed | What Was Fixed |
|-----|----------------|----------------|
| **GAP-A** — No live ticks after `focus_asset` | `app/backend/brokers/pocket_option/adapter.py` | Removed private `SessionManager()` instance from adapter. All session access now goes through `get_session_manager()` global singleton. `subscribe_ticks()`, `execute_trade()`, `get_balance()`, `connect()`, `disconnect()`, and `get_connection_status()` all use the singleton. |
| **GAP-B** — Payout hardcoded at 80% | `app/backend/brokers/pocket_option/assets.py` | Added `_get_live_payout_map()` which reads `pocketoptionapi.global_value.asset_manager` for live `profit_percent` values. Added `build_asset_list_with_live_payouts()` which uses live data when available, falls back to 0.8. Adapter now calls this instead of `build_asset_list()`. |
| **GAP-C** — Payout not shown in sidebar | `app/frontend/src/stores/useAssetStore.js`, `useAuthStore.js`, `LeftSidebar.jsx` | Added `assetPayouts` map to asset store. `useAuthStore.connect()` now builds and stores the payout map after fetching assets. `LeftSidebar` renders a payout badge (e.g. `85%`) next to each asset name. |

### Verification
- Backend import smoke test: ✅ `imports OK`, 13 assets, payout=0.8 (correct fallback before connect)
- Frontend build: ✅ 1656 modules, 0 errors

---

## Previous Work
**Inspection update complete — legacy Redis streaming vs current v3 live tick path**

The current v3 app does **not** use Redis for live market streaming. The backend uses a direct broker tick callback:
- `app/backend/session/pocket_option_session.py` captures Pocket Option tick updates
- `app/backend/main.py` wires the callback into `StreamingService.process_tick`
- `app/backend/services/streaming.py` enriches/logs/emits `market_data` and `warmup_status` via Socket.IO

The legacy reference `legacy_reference/backend_reuse/data_streaming/redis_gateway.py` shows the older Redis Pub/Sub architecture, but that gateway is **reference-only** for this rebuild.

## New Current Work
**SSID integration package refactor documentation completed and ready for OTC_SNIPER streaming implementation**

Two permanent documentation artifacts were created in `ssid_integration_package/integration_guides/dev_docs/`:
- `ssid_integration_package/integration_guides/dev_docs/3_Phase_Refactor_Plan.md`
- `ssid_integration_package/integration_guides/dev_docs/3Phase_Implementation_Report_26-03-31.md`

The supporting verification report remains here:
- `ssid_integration_package/ssid_streaming_test/scripts/ssid_streaming_implementation_report_26-03-30.md`

### Key Refactor Outcome
- Completed a safe 3-phase refactor of the local `ssid_integration_package/pocketoptionapi` copy
- Removed dead/broken candle modules and empty channel code
- Added a canonical frozen `Candle` dataclass plus `CandleCollection`
- Merged duplicate time sync implementations into one `TimeSync` with backward-compatible aliases
- Preserved the live tick streaming path entirely: `gv.set_csv` → `asyncio.run_coroutine_threadsafe` → `StreamingService.process_tick`

### Verification Highlights
- Import smoke test passed for `PocketOptionAPI` and `PocketOption`
- Dead-symbol grep returned 0 results for `EnhancedCandles`, `CandleData`, `TimeSynchronizer`, `get_currency_pairs`, and old candle/time-sync imports
- Direct smoke tests confirmed `Candle.to_list()` and `TimeSync.server_datetime` work as expected
- Final multi-agent review passed with all four specialist verdicts: @Reviewer ✅, @Debugger ✅, @Optimizer ✅, @Code_Simplifier ✅

## Current Status
- Phase 9 (Polish and Hardening) remains COMPLETE ✅
- Build verification remains valid: `npm --prefix C:\v3\OTC_SNIPER\app\frontend run build` → 1654 modules, 0 errors
- No code changes were required for the inspection task
- SSID integration package refactor docs are now complete and stored in `ssid_integration_package/integration_guides/dev_docs/`

## Current Findings
- Redis is **not implemented** in the current v3 runtime flow
- Tick data is already captured and streamed server-side through Socket.IO
- I did **not** find a frontend sparkline consumer in `app/frontend/src`, so the UI population path still appears incomplete
- The next implementation target is now the SSID streaming integration into the OTC_SNIPER app using the documented 3-phase refactor baseline

## Key Design Decisions Made (Phase 9)

- **Toast system:** Zustand store (`useToastStore`) — no external library, self-expiring via `setTimeout`, accessible via `aria-live="polite"`.
- **Error boundaries:** Class-based React boundaries at App root + per-zone (TopBar, LeftSidebar, MainView, RightSidebar). Never silent — always `console.error`.
- **Ghost trading banner:** Driven by `useSettingsStore.ghostTradingEnabled` — zero prop drilling, one-click exit.
- **Loading skeletons:** Reusable `LoadingSkeleton`, `CardSkeleton`, `TableRowSkeleton` — available for future async surfaces.
- **Live tick stream (current v3):** Direct broker callback → `StreamingService` → Socket.IO `market_data` / `warmup_status` events.

## Build Verification
- `npm --prefix C:\v3\OTC_SNIPER\app\frontend run build` → ✅ 1654 modules, 0 errors

## Previous Phases
- Phase 7 (Settings System) — COMPLETE ✅
- Phase 8 (AI Service Integration) — COMPLETE ✅
- Phase 9 (Polish and Hardening) — COMPLETE ✅

## Next Steps
- If Redis-based transport is still desired, implement a Redis gateway/bridge based on the legacy reference
- Add or restore the frontend `market_data` subscription and sparkline population path
- Optional future work: Supabase migration, Auth0 integration, CDP SSID extraction
- Use `ssid_integration_package/integration_guides/dev_docs/3Phase_Implementation_Report_26-03-31.md` as the implementation baseline for integrating SSID streaming into OTC_SNIPER
- Keep `ssid_integration_package/ssid_streaming_test/scripts/ssid_streaming_implementation_report_26-03-30.md` as the verified runtime reference for thread-safe live tick capture

## Blockers
None for the inspection task.

## Environment Notes
- Backend: `cd C:\v3\OTC_SNIPER\app && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload`
- Frontend dev: `cd C:\v3\OTC_SNIPER\app\frontend && npm run dev` → http://localhost:5173
- Frontend build: `npm --prefix C:\v3\OTC_SNIPER\app\frontend run build` → `dist/` (verified ✅)
- Chrome debug port: `CHROME_PORT=9222`
- Ops enabled: `QFLX_ENABLE_OPS=1`
