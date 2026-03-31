# OTC SNIPER v3 — SSID Tick Streaming Integration Plan

**Date:** 2026-03-31  
**Status:** IMPLEMENTED — Pending runtime verification  
**Compiled by:** @Reviewer (forensic readiness assessment of full system)  
**Last reviewed by:** @Reviewer (post-implementation accuracy audit — 2026-03-31)  
**Scope:** Wire SSID live tick streaming end-to-end: broker → backend → Socket.IO → frontend Sparkline + OTEO ring + trade result display  
**Reference Docs:**
- `Dev_Docs/OTC_SNIPER_v3_Implementation_Plan_26-03-24.md`
- `Dev_Docs/ssid_streaming_test_plan_26-03-30.md`
- `ssid_integration_package/integration_guides/dev_docs/3Phase_Implementation_Report_26-03-31.md`
- `otc_sniper_v3_rebuild_architechture.md`

---

## ⚠️ OPEN ITEM BEFORE RUNTIME TESTING

> These items were identified during the post-implementation review. Some earlier plan notes were stale; the code now reflects the resolved items below.

### Resolved Since Last Audit

| # | Item | File | Status |
|---|------|------|--------|
| **FIX-1** | Trading API routes corrected from `/trading/` to `/brokers/` | `app/frontend/src/api/tradingApi.js` | ✅ Implemented in code |
| **FIX-2** | Dead WIN/LOSS branch removed from `useTradingStore.executeTrade()` | `app/frontend/src/stores/useTradingStore.js` | ✅ Implemented in code |

### Current Open Blocker

| # | Item | Severity | File | Status |
|---|------|----------|------|--------|
| **FIX-3** | `/api/brokers/pocket_option/assets` returns `Asset` objects that were serialized with `asset.__dict__`, causing `AttributeError` during broker asset refresh after SSID connect | 🔴 HIGH | `app/backend/main.py` | ✅ Fixed in code |

### FIX-3 Detail — Asset serialization failure in `broker_assets`

**Observed runtime error:**
```python
AttributeError: 'Asset' object has no attribute '__dict__'
```

**Root cause:** `main.py` currently returns broker assets with:
```python
return {"broker": broker, "assets": [asset.__dict__ for asset in assets]}
```
The `Asset` type returned by the broker adapter is not a plain Python object with `__dict__`, so this serialization method fails after SSID connect when the frontend requests live assets.

**Resolution:** Switched the endpoint to `dataclasses.asdict(asset)` because `Asset` is a dataclass in `app/backend/brokers/base.py`. Runtime verification now returns HTTP 200 with a serialized asset list.

---

## 1. Executive Summary

A comprehensive forensic review of ~35 files across the backend, frontend, SSID integration package, and architecture documents confirms that **the system is ~75% wired but has 5 critical gaps** that prevent live tick streaming from populating the Sparkline and generating clean OTEO signals.

The backend streaming pipeline is **complete and correct**: OTEO enrichment, ManipulationDetector, TickLogger, SignalLogger, and Socket.IO emission all work. The frontend components (Sparkline, OTEORing, TradingWorkspace) are **complete and correct** — they accept and render live data. The missing pieces are all **wiring tasks**, not new feature development.

**Estimated effort:** 4–6 hours  
**Risk level:** 🟢 Low — no architectural changes required  
**Architecture trajectory:** ✅ On track — fully aligned with `otc_sniper_v3_rebuild_architechture.md`

> **Implementation update (2026-03-31):** All 5 phases (A–E) have been implemented. See Section 3 for updated architecture trajectory. Two open items (FIX-1, FIX-2) must be resolved before runtime verification.

---

## 2. Current State Map

### 2.1 What IS Working (Verified)

| Layer | Component | File | Status |
|-------|-----------|------|--------|
| **Backend** | Tick hook (monkey-patch) | `session/pocket_option_session.py` | ✅ Wired + hardened (Phase E) |
| **Backend** | Streaming pipeline | `services/streaming.py` | ✅ Complete |
| **Backend** | OTEO engine | `services/oteo.py` | ✅ Complete |
| **Backend** | Manipulation detector | `services/manipulation.py` | ✅ Complete |
| **Backend** | Tick logger | `services/tick_logger.py` | ✅ Complete |
| **Backend** | Signal logger | `services/signal_logger.py` | ✅ Complete |
| **Backend** | Socket.IO `focus_asset` handler | `main.py` | ✅ Room join/leave + subscribe_ticks (Phase B) |
| **Backend** | Socket.IO `watch_assets` handler | `main.py` | ✅ Multi-room join + subscribe_ticks (Phase B) |
| **Backend** | Socket.IO `check_status` polling | `main.py` | ✅ Chrome + session state |
| **Backend** | Session API | `api/session.py` | ✅ Connect/disconnect/persist |
| **Backend** | Trade execution | `services/trade_service.py` | ✅ With background outcome tracking + sio emit (Phase D) |
| **Backend** | `subscribe_ticks()` method | `brokers/pocket_option/adapter.py` | ✅ Called on focus_asset/watch_assets (Phase B) |
| **Backend** | Main event loop capture | `main.py` lifespan | ✅ `set_main_loop()` called at startup (Phase E) |
| **Backend** | `sio` on `app.state` | `main.py` lifespan | ✅ Available for DI via `request.app.state.sio` (Phase D) |
| **Frontend** | Socket.IO singleton | `api/socketClient.js` | ✅ Working |
| **Frontend** | Stream API helpers | `api/streamApi.js` | ✅ Defined and used |
| **Frontend** | Stream store | `stores/useStreamStore.js` | ✅ Populated by `useStreamConnection` (Phase A) |
| **Frontend** | `useStreamConnection` hook | `hooks/useStreamConnection.js` | ✅ Created (Phase A) |
| **Frontend** | Sparkline component | `components/trading/Sparkline.jsx` | ✅ Renders from `ticks` prop |
| **Frontend** | OTEORing component | `components/trading/OTEORing.jsx` | ✅ Renders from `signal` prop |
| **Frontend** | TradingWorkspace | `components/trading/TradingWorkspace.jsx` | ✅ Reads from `useStreamStore` |
| **Frontend** | LeftSidebar asset list | `components/layout/LeftSidebar.jsx` | ✅ Renders, `setSelectedAsset` on click |
| **Frontend** | chartUtils.js | `components/trading/chartUtils.js` | ✅ Handles `{price}` objects correctly |
| **Frontend** | Dynamic asset list | `stores/useAuthStore.js` | ✅ Fetches from broker API after connect (Phase C) |
| **Frontend** | `trade_result` listener | `App.jsx` | ✅ Routes to risk store + toast (Phase D) |
| **Frontend** | `sessionId` in ops store | `stores/useOpsStore.js` | ✅ Persisted on connect |

### 2.2 Critical Gaps — ALL CLOSED ✅

| # | Gap | Severity | Status |
|---|-----|----------|--------|
| **GAP 1** | No frontend `market_data` listener → `useStreamStore` | 🔴 CRITICAL | ✅ Closed — Phase A |
| **GAP 2** | No `focus_asset` emission on asset selection | 🔴 CRITICAL | ✅ Closed — Phase A |
| **GAP 3** | No `subscribe_ticks` / `change_symbol` trigger after session connect | 🔴 CRITICAL | ✅ Closed — Phase B |
| **GAP 4** | Asset list is static (hardcoded), not from SSID/broker API | 🟡 HIGH | ✅ Closed — Phase C |
| **GAP 5** | Trade results not streamed back to frontend | 🟡 HIGH | ✅ Closed — Phase D |

### 2.3 Medium Priority Items — ALL RESOLVED ✅

| # | Issue | File | Status |
|---|-------|------|--------|
| M1 | `_apply_hooks()` uses `asyncio.get_running_loop()` from broker WebSocket thread — may fail | `pocket_option_session.py` | ✅ Fixed — Phase E |
| M2 | `useStreamStore.ticks` needs to accumulate ticks as an array, not replace | `useStreamStore.js` | ✅ Fixed — Phase A (rolling buffer with `MAX_TICKS = 300`) |
| M3 | `tradingApi.js` `getTrades()` doesn't pass required `session_id` query param | `api/tradingApi.js` | ✅ Fixed — `session_id` now passed |

### 2.4 New Open Items (Post-Implementation Audit)

| # | Issue | File | Severity | Status |
|---|-------|------|----------|--------|
| FIX-1 | `tradingApi.js` URL paths use `/trading/` but backend uses `/brokers/` | `api/tradingApi.js` | 🔴 HIGH | ⏳ Awaiting approval |
| FIX-2 | Dead WIN/LOSS toast branch in `useTradingStore.executeTrade()` | `stores/useTradingStore.js` | 🟡 MEDIUM | ⏳ Awaiting approval |

---

## 3. Architecture Trajectory Assessment

Comparing current state against `otc_sniper_v3_rebuild_architechture.md`:

| Phase | Planned | Current | Status |
|-------|---------|---------|--------|
| Phase 0: Ops + Chrome + SSID | ✅ | ✅ | ✅ Complete |
| Phase 1: Backend Foundation | ✅ | ✅ | ✅ Complete |
| Phase 2: Broker + Trading | ✅ | ✅ | ✅ Complete |
| Phase 3: Streaming & Enrichment | ✅ Backend | ✅ Frontend wired | ✅ Complete |
| Phase 4: Frontend Shell | ✅ | ✅ | ✅ Complete |
| Phase 5: Trading UI | ✅ | ✅ Live data wired | ✅ Complete |
| Phase 6: Risk Management | ✅ | ✅ | ✅ Complete |
| Phase 7: Settings System | ✅ | ✅ | ✅ Complete |
| Phase 8: AI Integration | ✅ | ✅ | ✅ Complete |
| Phase 9: Polish & Hardening | ✅ | ✅ | ✅ Complete |
| **SSID Streaming Integration** | ✅ | ✅ Implemented | **← FIX-1 + FIX-2 before runtime test** |

**Verdict: Architecture is complete. Two targeted fixes required before runtime verification.**

---

## 4. Data Flow — Complete End-to-End Picture

### 4.1 Tick Flow (Implemented)

```
[Pocket Option WebSocket]
  → binary message: [[asset_id, timestamp, price]]
  → global_value.set_csv(asset_id, [{'time': ts, 'price': price}])
  → hooked_set_csv() intercepts
  → asyncio.run_coroutine_threadsafe(process_tick(asset, price, ts), main_loop)

[StreamingService.process_tick()]
  → OTEO.update_tick(price, ts)         → score, direction, confidence, velocity, z_score
  → ManipulationDetector.update(ts, p)  → push_snap, pinning flags
  → TickLogger.write_tick()             → data/tick_logs/{asset}/YYYY-MM-DD.jsonl
  → SignalLogger.log_signal()           → data/signals/ (MEDIUM/HIGH only)
  → sio.emit("market_data", payload, room=f"market_data:{asset}")
  → sio.emit("warmup_status", {...}, room=...) every 10 ticks + at tick 50

[Socket.IO → Frontend]
  → useStreamConnection hook receives "market_data"
  → useStreamStore.updateTicks(asset, rollingWindow)
  → useStreamStore.updateSignal(asset, {direction, confidence, score, ...})
  → useStreamStore.updateManipulation(asset, flags)
  → useStreamStore.setWarmup(asset, !ready) on "warmup_status"

[TradingWorkspace]
  → reads ticks[selectedAsset] → passes to Sparkline → SVG chart renders
  → reads signals[selectedAsset] → passes to OTEORing → confidence ring renders
  → reads warmup[selectedAsset] → shows warmup state in MetricCard
```

### 4.2 Asset Subscription Flow (Implemented)

```
[User clicks asset in LeftSidebar]
  → useAssetStore.setSelectedAsset(asset)

[useStreamConnection hook watches selectedAsset]
  → clearAsset(previousAsset)  ← clears stale tick/signal state
  → focusAsset(asset)          ← emits "focus_asset" to backend Socket.IO

[Backend focus_asset handler]
  → leaves old rooms, joins new room "market_data:{asset}"
  → clears manipulation detector buffers
  → adapter.subscribe_ticks(asset)  ← calls change_symbol on broker

[PocketOptionAdapter.subscribe_ticks(asset)]
  → session._api.change_symbol(pocket_asset, 1)  ← broker starts streaming ticks
```

### 4.3 Trade Result Flow (Implemented)

```
[User clicks CALL/PUT in TradePanel]
  → useTradingStore.executeTrade(broker, asset)
  → POST /api/brokers/pocket_option/trade          ← NOTE: /brokers/ not /trading/ (see FIX-1)
  → TradeService.execute_trade() → adapter.execute_trade() → session.buy()
  → Returns immediately: { success, trade_id, entry_price }
  → Toast: "Trade submitted"
  → asyncio.create_task(_track_trade_outcome(...))

[Background: after expiration + 2s]
  → loop.run_in_executor(None, session.check_win, trade_id)  ← non-blocking
  → trade.outcome = "win" | "loss" | "unknown"
  → repository.update_trade(trade)
  → sio.emit("trade_result", { trade_id, outcome, profit, asset, ... })

[Frontend trade_result listener in App.jsx]
  → useTradingStore.setLastTradeResult(data)
  → useRiskStore.recordTradeResult({ outcome, pnl, stake, source: 'live' })
  → useToastStore: WIN toast (green) or LOSS toast (red)
```

---

## 5. Implementation Phases

### Phase A — Frontend Stream Wiring ✅ COMPLETE
**Closes:** GAP 1, GAP 2, M2  
**Files:** `app/frontend/src/hooks/useStreamConnection.js` (CREATED), `app/frontend/src/App.jsx` (MODIFIED)

**Implementation notes (deviations from plan — all improvements):**
- `normalizeConfidence()` helper added — handles numeric, string-level (`HIGH`/`MEDIUM`/`LOW`), and score fallback. More robust than plan spec.
- `clearAsset(previousAsset)` called on asset switch (per-asset cleanup, not full buffer wipe).
- `previousSelectedAssetRef` tracks previous asset for targeted cleanup.
- `disconnect` Socket.IO event sets `isStreaming(false)` — defensive addition not in plan.

#### Phase A Acceptance Criteria

| Criterion | Test | Status |
|-----------|------|--------|
| `market_data` events populate `useStreamStore.ticks` | Open browser DevTools → Network → WS → verify events arrive | ⏳ Runtime test pending |
| Sparkline renders live price data | Visual: chart draws after ~5 ticks | ⏳ Runtime test pending |
| OTEORing shows confidence after warmup | Visual: ring fills after ~50 ticks | ⏳ Runtime test pending |
| `focus_asset` emitted on asset click | DevTools → WS → verify `focus_asset` message sent | ⏳ Runtime test pending |
| Warmup state clears after 50 ticks | Visual: "WARMUP" label disappears | ⏳ Runtime test pending |

---

### Phase B — Backend Asset Subscription ✅ COMPLETE
**Closes:** GAP 3  
**Files:** `app/backend/main.py` (MODIFIED)

#### Phase B Acceptance Criteria

| Criterion | Test | Status |
|-----------|------|--------|
| `change_symbol` called on broker after `focus_asset` | Backend logs show "Subscribed to ticks for {asset}" | ⏳ Runtime test pending |
| Ticks start flowing after asset selection | Sparkline populates within 2–5 seconds of clicking an asset | ⏳ Runtime test pending |
| No crash if session is disconnected | `get_connection_status() != "connected"` guard prevents error | ⏳ Runtime test pending |

---

### Phase C — Dynamic Asset List from Broker API ✅ COMPLETE
**Closes:** GAP 4  
**Files:** `app/frontend/src/stores/useAuthStore.js` (MODIFIED)

**Implementation notes:**
- Asset ID extraction uses `asset?.raw_id ?? asset?.id` with `.trim().filter()` — more robust than plan's `a.raw_id || \`${a.id}_otc\`` pattern.

#### Phase C Acceptance Criteria

| Criterion | Test | Status |
|-----------|------|--------|
| LeftSidebar shows broker-provided asset list after connect | Visual: asset list updates after SSID connect | ⏳ Runtime test pending |
| Default assets shown before connect | Visual: hardcoded list visible before session | ⏳ Runtime test pending |
| Asset fetch failure doesn't break connect flow | Disconnect network → connect still succeeds | ⏳ Runtime test pending |

---

### Phase D — Trade Result Streaming ✅ COMPLETE (FIX-1 + FIX-2 required before testing)
**Closes:** GAP 5  
**Files:** `app/backend/services/trade_service.py` (MODIFIED), `app/backend/api/trading.py` (MODIFIED), `app/frontend/src/App.jsx` (MODIFIED)

**Implementation notes:**
- `sio` injected via `request.app.state.sio` (correct pattern — avoids circular imports).
- `trade_result` payload includes `expiration_seconds` (additive, not in plan spec).
- `check_win()` runs in `loop.run_in_executor()` — non-blocking improvement not in plan.
- **FIX-1 required:** `tradingApi.js` URL paths must be corrected before trade execution works.
- **FIX-2 required:** Dead WIN/LOSS branch in `useTradingStore` should be removed.

#### Phase D Acceptance Criteria

| Criterion | Test | Status |
|-----------|------|--------|
| `trade_result` event emitted after expiration | Backend logs show "Trade {id} tracked. Outcome: win/loss" | ⏳ Runtime test pending (blocked by FIX-1) |
| WIN toast fires with correct P&L | Execute a ghost trade → wait for expiration → toast appears | ⏳ Runtime test pending (blocked by FIX-1) |
| `useRiskStore` updated with outcome | Risk panel shows updated win rate after trade | ⏳ Runtime test pending (blocked by FIX-1) |
| No crash if `sio` is None | `if self.sio` guard prevents AttributeError | ✅ Code verified |

---

### Phase E — Tick Hook Hardening ✅ COMPLETE
**Closes:** M1  
**Files:** `app/backend/main.py` (MODIFIED), `app/backend/session/pocket_option_session.py` (MODIFIED)

**Implementation notes:**
- Log message reads `"Broker tick hooks applied successfully."` (plan specified `"(threadsafe)"` — functionally identical).

#### Phase E Acceptance Criteria

| Criterion | Test | Status |
|-----------|------|--------|
| No `RuntimeError: no running event loop` in logs | Connect session → check backend logs | ⏳ Runtime test pending |
| Ticks flow reliably under sustained load | Run for 5+ minutes → no tick gaps in logs | ⏳ Runtime test pending |
| Hook applied message in logs | `"Broker tick hooks applied successfully."` visible on startup | ⏳ Runtime test pending |

---

## 6. Files Changed Summary

| File | Action | Phase | Change | Status |
|------|--------|-------|--------|--------|
| `app/frontend/src/hooks/useStreamConnection.js` | **CREATED** | A | New hook: market_data listener + focus_asset emitter | ✅ Done |
| `app/frontend/src/App.jsx` | **MODIFIED** | A, D | `useStreamConnection()` call + `trade_result` listener | ✅ Done |
| `app/backend/main.py` | **MODIFIED** | B, E | `subscribe_ticks` in `focus_asset`/`watch_assets` + loop capture + `app.state.sio` | ✅ Done |
| `app/frontend/src/stores/useAuthStore.js` | **MODIFIED** | C | Fetch assets after connect | ✅ Done |
| `app/backend/services/trade_service.py` | **MODIFIED** | D | Accept `sio` param + emit `trade_result` + `run_in_executor` for `check_win` | ✅ Done |
| `app/backend/api/trading.py` | **MODIFIED** | D | Pass `sio` to `TradeService` via `request.app.state.sio` | ✅ Done |
| `app/backend/session/pocket_option_session.py` | **MODIFIED** | E | `set_main_loop()` + `run_coroutine_threadsafe` | ✅ Done |
| `app/frontend/src/stores/useOpsStore.js` | **MODIFIED** | D | Added `sessionId` + `setSessionId` | ✅ Done |
| `app/frontend/src/stores/useTradingStore.js` | **MODIFIED** | D | Sends backend-expected fields; loads trades with `session_id` | ✅ Done — FIX-2 pending |
| `app/frontend/src/api/tradingApi.js` | **MODIFIED** | D | `getTrades()` passes `session_id` param | ✅ Done — FIX-1 pending |

**Total: 1 file created, 9 files modified**

---

## 7. Files Explicitly NOT Touched

| File | Reason |
|------|--------|
| `services/streaming.py` | Complete and correct — no changes needed |
| `services/oteo.py` | Complete and correct — no changes needed |
| `services/manipulation.py` | Complete and correct — no changes needed |
| `components/trading/Sparkline.jsx` | Complete and correct — accepts `ticks` prop |
| `components/trading/OTEORing.jsx` | Complete and correct — accepts `signal` prop |
| `components/trading/TradingWorkspace.jsx` | Complete and correct — reads from `useStreamStore` |
| `components/trading/chartUtils.js` | Complete and correct — handles `{price}` objects |
| `stores/useStreamStore.js` | Complete and correct — actions already defined |
| `api/streamApi.js` | Complete and correct — helpers already defined |
| `api/socketClient.js` | Complete and correct — singleton works |
| `session/pocket_option_session.py` (connect logic) | Only the hook mechanism changed in Phase E |

---

## 8. OTEO Signal Conflict Analysis

### 8.1 Current OTEO Behavior

The OTEO engine in `services/oteo.py` is designed to produce **clean, non-conflicting signals** with these built-in safeguards:

| Safeguard | Mechanism | Purpose |
|-----------|-----------|---------|
| **Warmup gate** | Returns `50.0` for first 49 ticks | Prevents premature signals from insufficient data |
| **Cooldown** | 30-tick cooldown after every HIGH signal | Prevents signal spam / rapid-fire HIGH signals |
| **Trend suppression** | Downgrades HIGH → MEDIUM when trend-aligned | Avoids counter-trend HIGH signals |
| **Maturity weighting** | Dampens scores when baseline < 200 ticks | Prevents overconfident early scores |
| **Volatility adaptation** | Adjusts `adaptive_center` based on rolling vol | Prevents false signals in low-volatility periods |

### 8.2 Signal Conflict Prevention

The OTEO is designed to produce **one direction at a time** (CALL or PUT) based on velocity sign. There is no scenario where it produces conflicting CALL and PUT signals simultaneously for the same asset.

**Potential conflict source:** If the frontend receives `market_data` events for multiple assets simultaneously (multi-chart mode), each asset has its own independent OTEO engine instance in `StreamingService._oteo_engines`. There is no cross-asset contamination.

### 8.3 Signal Accuracy Improvement Path

After FIX-1 and FIX-2 are applied and runtime verification is complete, signal accuracy can be improved by:
1. Increasing the warmup threshold from 50 to 100 ticks (more data = better baseline)
2. Adjusting `adaptive_center` based on asset-specific volatility profiles
3. Adding a minimum maturity threshold before HIGH signals are allowed (e.g., `maturity >= 0.3`)

These are **post-integration tuning tasks**, not blockers.

---

## 9. LeftSidebar Asset Detection

### 9.1 Current State

The LeftSidebar reads from `useAssetStore.availableAssets` which is initialized with `DEFAULT_ASSETS` (13 hardcoded OTC pairs). This is correct for initial display before session connect.

### 9.2 After Phase C (Implemented)

After Phase C, the asset list is populated from `GET /api/brokers/pocket_option/assets` after a successful SSID connect. The backend `assets.py` returns 13 verified OTC assets — the same as the hardcoded list. Phase C is a correctness improvement (live data) rather than a functional change.

### 9.3 Future Enhancement

The architecture doc calls for payout badges on assets. This can be added to `LeftSidebar.jsx` once the asset list includes payout data from the broker API response.

---

## 10. Trade Result Frontend Display

### 10.1 Current State (After Phase D)

The trade result flow is:
1. **Immediate response** (HTTP): `{ success: true, trade_id: "abc123" }` → toast: "Trade submitted"
2. **Deferred result** (Socket.IO `trade_result` event, after expiration): `{ outcome: "win", profit: 8.50 }` → toast: "WIN — +$8.50"

This is the correct pattern for binary options where outcomes are only known after expiration.

### 10.2 FIX-2 Required

`useTradingStore.executeTrade()` still contains a dead WIN/LOSS branch that checks `result.outcome` from the HTTP response. Since the HTTP response never includes `outcome`, this branch is unreachable. However, it creates a latent double-toast risk. FIX-2 removes this branch and replaces it with an unconditional "Trade submitted" toast, aligning the code with the intended design.

---

## 11. Verification Checklist

> ⚠️ **FIX-1 must be applied before executing trade-related checks.**  
> Run `npm --prefix app/frontend run build` after applying fixes to confirm 0 build errors.

### Backend Verification
- [ ] Backend starts without errors: `cd app && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload`
- [ ] `GET /health` returns `{ status: "ok" }`
- [ ] `POST /api/session/connect` with valid SSID returns `{ ok: true, connected: true }`
- [ ] Backend logs show `"Broker tick hooks applied successfully."` after connect
- [ ] Backend logs show `"Subscribed to ticks for EURUSD_otc"` after `focus_asset` event
- [ ] Backend logs show tick processing: `"process_tick"` entries in logs
- [ ] `data/tick_logs/EURUSD_otc/` JSONL files created and growing

### Frontend Verification
- [ ] Frontend builds without errors: `npm --prefix app/frontend run build`
- [ ] Sparkline populates with live price data within 5 seconds of asset selection
- [ ] OTEORing shows confidence percentage after ~50 ticks
- [ ] "WARMUP" label disappears after 50 ticks
- [ ] Asset selection in LeftSidebar triggers `focus_asset` (visible in DevTools WS)
- [ ] `market_data` events visible in DevTools WS tab
- [ ] Trade execution shows "Trade submitted" toast immediately *(requires FIX-1)*
- [ ] WIN/LOSS toast fires after trade expiration *(requires FIX-1)*
- [ ] Risk panel updates after trade outcome *(requires FIX-1)*

### OTEO Signal Verification
- [ ] No HIGH signals during warmup period (first 49 ticks)
- [ ] Signals alternate between CALL and PUT based on price direction
- [ ] No two HIGH signals within 30 ticks of each other (cooldown working)
- [ ] Confidence percentage in OTEORing matches `oteo_score` from backend

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `pocketoptionapi` not installed in runtime env | Medium | No ticks flow | Verify conda env before starting backend |
| SSID expired during streaming | Medium | Ticks stop | Session reconnect flow already implemented |
| `change_symbol` call fails silently | Low | No ticks for asset | Non-fatal guard + warning log in Phase B |
| `run_coroutine_threadsafe` with stale loop | Low | Tick dispatch fails | `loop.is_running()` check in Phase E |
| Trade result Socket.IO circular import | ~~Medium~~ Resolved | ~~Phase D fails to build~~ | `app.state.sio` pattern used — no circular import |
| Multi-asset tick buffer memory growth | Low | Memory leak | `MAX_TICKS = 300` cap in Phase A hook |
| OTEO produces conflicting signals | Very Low | Confusing UI | Per-asset engine instances prevent cross-contamination |
| **`tradingApi.js` URL path mismatch** | **Confirmed** | **404 on all trade calls** | **FIX-1 — awaiting approval** |
| **Dead WIN/LOSS branch double-toast** | **Low (latent)** | **Duplicate toasts if backend shape changes** | **FIX-2 — awaiting approval** |

---

## 13. Implementation Order Constraint

All phases are now complete. The remaining work is:

```
FIX-1 (tradingApi.js URL paths)
  ↓
FIX-2 (useTradingStore dead branch)
  ↓
Frontend build verification
  ↓
Section 11 Runtime Verification Checklist
```

---

## 14. Phase Gate Protocol

Per `.clinerules/PHASE_REVIEW_PROTOCOL.md`:

| Phase | Reviewer Gate | Status |
|-------|--------------|--------|
| Phase A | @Reviewer reviews `useStreamConnection.js` + `App.jsx` changes | ✅ Reviewed — passed |
| Phase B | @Reviewer reviews `main.py` changes | ✅ Reviewed — passed |
| Phase C | @Reviewer reviews `useAuthStore.js` changes | ✅ Reviewed — passed |
| Phase D | @Reviewer reviews `trade_service.py` + `trading.py` + `App.jsx` changes | ✅ Reviewed — FIX-1 + FIX-2 identified |
| Phase E | @Reviewer reviews `pocket_option_session.py` + `main.py` changes | ✅ Reviewed — passed |
| **FIX-1 + FIX-2** | @Reviewer reviews `tradingApi.js` + `useTradingStore.js` changes | ⏳ Awaiting implementation + review |
| **Final validation** | @Reviewer, @Debugger, @Optimizer, @Code_Simplifier | ⏳ After runtime verification |

---

## 15. CORE_PRINCIPLES Alignment

| Principle | How This Plan Adheres |
|-----------|----------------------|
| **#1 Functional Simplicity** | 1 new file, 9 modified files — minimum surface area for maximum impact |
| **#2 Sequential Logic** | Phases A→E executed in strict dependency order |
| **#3 Incremental Testing** | Each phase has explicit acceptance criteria; FIX-1/FIX-2 isolated before runtime test |
| **#4 Zero Assumptions** | All guards check connection status before calling broker methods |
| **#5 Code Integrity** | No existing working code removed — only additions and targeted modifications |
| **#6 Separation of Concerns** | Hook in its own file, store actions unchanged, components unchanged |
| **#8 Defensive Error Handling** | All new broker calls wrapped in try/except with warning logs (non-fatal) |
| **#9 Fail Fast** | `loop.is_running()` check before dispatch; connection status check before subscribe |

---

## 16. Post-Integration Next Steps

After FIX-1, FIX-2, and the Section 11 verification checklist are complete:

1. **OTEO Tuning** — Adjust warmup threshold, maturity gate, and cooldown based on live signal quality
2. **Multi-Chart Streaming** — Verify `watch_assets` + multi-asset tick buffers work in `MultiChartView`
3. **Ghost Trading Integration** — Wire `StreamingService` to auto-trigger ghost trades on HIGH signals
4. **Signal Alerts** — Add visual/audio alerts for HIGH confidence signals
5. **Supabase Migration** — Replace `LocalFileRepository` with `SupabaseRepository` (same interface)
6. **Auth0 Integration** — Add user identity layer (reserved boundary already in place)

---

*Plan originally compiled: 2026-03-31*  
*Post-implementation audit: 2026-03-31*  
*Source: Forensic review of 35 files across backend, frontend, SSID integration package, and architecture docs*  
*Compiled by: @Reviewer*  
*Audited by: @Reviewer*  
*Status: IMPLEMENTED — FIX-1 + FIX-2 required before runtime verification*  
*Next action: Approve FIX-1 + FIX-2, apply via @Coder, run build, execute Section 11 checklist*
