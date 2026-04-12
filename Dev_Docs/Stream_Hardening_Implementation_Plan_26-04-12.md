# OTC SNIPER v3 — Stream Hardening & Auto-Ghost Asset Filtering Implementation Plan

**File date:** 2026-04-12  
**Status:** Plan — Awaiting explicit approval before implementation  
**Compiled by:** @Investigator (forensic analysis), @Reviewer (quality assessment)  
**Scope:** Harden the streaming lifecycle, restrict Auto-Ghost to user-visible assets with payout gating, fix tick delivery reliability, and add explicit Start/Stop stream controls  
**CORE_PRINCIPLES:** All changes must comply with `.agents/CORE_PRINCIPLES.md`

---

## 1. Executive Summary

A deep forensic investigation of **20+ files** across the backend and frontend identified **3 CRITICAL**, **4 HIGH**, and **3 MEDIUM** severity issues directly responsible for three user-reported concerns:

1. **Auto-Ghost trades assets not visible to the user** — with potentially low payout percentages, destroying the system's statistical edge.
2. **No way to cleanly stop streaming** — after clicking Disconnect, data keeps flowing, requiring a full gateway restart and browser data clear.
3. **Tick delivery freezes intermittently** — some assets appear frozen until the user double-clicks or adds a new asset.

The root cause of all three problems traces to a single architectural gap: **the broker's tick hook (`hooked_set_csv`) is a global, unfiltered firehose** — it captures ticks for *every* asset the broker streams, regardless of what the user has selected in the frontend. There is no backend-side allowlist, no stream lifecycle control, and no payout-gating mechanism.

---

## 2. Issue Tracker — Forensic Findings

### 🔴 CRITICAL Issues

#### ISSUE-01: Auto-Ghost Trades Assets Not Visible to User (No Allowlist)

**Severity:** CRITICAL  
**Files:** `auto_ghost.py` (L112-148), `streaming.py` (L91-98, L177-183)  
**Core Principle Violated:** #4 (Zero Assumptions)

**Root Cause:** `StreamingService.process_tick()` processes **every tick** from the broker hook, creates OTEO engines on-the-fly for any asset (`_get_or_create_engines` at L71-89), and feeds actionable signals to `auto_ghost.consider_signal()` at L177-183. The Auto-Ghost service has **zero awareness** of which assets the user has selected in the frontend.

**Evidence:**
- `auto_ghost.py` L112-148: `consider_signal()` checks enabled, halted, session_trades, drawdown, manipulation, cooldown, concurrent_trades — but **never checks if the asset is in an approved/visible set**.
- `streaming.py` L71-89: `_get_or_create_engines()` lazily creates engines for **any** asset string.
- `pocket_option_session.py` L45-73: `hooked_set_csv` fires for **every** `set_csv` call with a price update.

**Impact:** Ghost trades execute on assets with potentially low payout percentages (60-75%), destroying the statistical edge.

---

#### ISSUE-02: No Payout-Rate Gating on Auto-Ghost Execution

**Severity:** CRITICAL  
**Files:** `auto_ghost.py` (entire file), `trade_service.py` (L45-57, L106)  
**Core Principle Violated:** #9 (Fail Fast)

**Root Cause:** `AutoGhostService.consider_signal()` never checks the asset's current payout percentage before executing. The payout is only resolved *after* the trade is submitted, inside `TradeService.execute_trade()` at L106, and only for record-keeping — not as a gate.

**Evidence:**
- `auto_ghost.py`: No `payout` parameter in `consider_signal()`, no payout check anywhere.
- `trade_service.py` L45-57: `_resolve_payout_pct()` exists but is only used to populate `TradeRecord.payout_pct`.

**Impact:** With a 60% payout, you need >62.5% win rate just to break even — far higher than the typical ~55-58% edge.

---

#### ISSUE-03: Disconnect Does Not Stop Tick Streaming

**Severity:** CRITICAL  
**Files:** `pocket_option_session.py` (L195-224, L38-78), `session/manager.py` (L35-43), `main.py` (L46-49)  
**Core Principle Violated:** #8 (Zero Silent Failures)

**Root Cause:** When the user clicks "Disconnect":
1. `SessionManager.disconnect()` calls `session.disconnect()` which resets globals.
2. **BUT** the monkey-patched `hooked_set_csv` is **never unpatched**. `_original_set_csv` is set once and the hook persists forever.
3. The `_tick_callback` class variable is **never cleared** on disconnect.
4. `StreamingService` has no concept of "streaming active" vs "streaming stopped".

**Evidence:**
- `pocket_option_session.py` L195-224: `disconnect()` never touches `_tick_callback`, `_original_set_csv`, or `_main_loop`.
- `main.py` L49: `set_tick_callback()` is called once at module level and never revoked.
- No `StreamingService.stop()` or `StreamingService.pause()` method exists.

**Impact:** After Disconnect, stale ticks continue flowing, engines keep computing, and Auto-Ghost can still trigger trades.

---

### 🟠 HIGH Issues

#### ISSUE-04: No Mechanism to Stop Trading an Asset When Removed from Multi-Chart

**Severity:** HIGH  
**Files:** `useAssetStore.js` (L71-74), `useStreamConnection.js` (L161-184), `streaming.py` (L199-204), `main.py` (L86-111)

**Root Cause:** When a user removes an asset from multi-chart:
- Frontend updates Zustand store and calls `watchAssets()` with updated list.
- Backend updates Socket.IO rooms but **never unsubscribes** from the broker's tick stream.
- `StreamingService` keeps engines alive — they are **never cleaned up**.
- Auto-Ghost continues receiving signals for the removed asset.

**Evidence:**
- `adapter.py` L64-78: `subscribe_ticks()` exists but there is no `unsubscribe_ticks()`.
- `streaming.py`: No method to remove/deactivate engines for a specific asset.

---

#### ISSUE-05: Tick Delivery Has No Backpressure or Error Visibility

**Severity:** HIGH  
**Files:** `pocket_option_session.py` (L45-73)

**Root Cause:** `hooked_set_csv` uses `asyncio.run_coroutine_threadsafe()` to dispatch ticks. The returned `Future` is **never awaited or checked** — if `process_tick` raises, the error is silently lost. No rate-limiting, no queue depth monitoring, no dropped-tick logging.

**Impact:** Directly explains the "frozen state until double-click" symptom. Ticks queue during busy periods, then burst-process when the Socket.IO room is re-joined.

---

#### ISSUE-06: `focus_asset` and `watch_assets` Have Conflicting Room Management

**Severity:** HIGH  
**Files:** `main.py` (L60-111), `useStreamConnection.js` (L161-184)

**Root Cause:**
- `focus_asset` (L61-74): Leaves **all** rooms, joins **one** room.
- `watch_assets` (L86-111): Leaves **all** rooms, joins **multiple** rooms.
- These two handlers fight each other. The frontend fires them from separate `useEffect` hooks with no coordination.

**Evidence:** Both handlers at L67-68 and L92-93 iterate `session.get("rooms", [])` and leave all rooms before joining new ones.

**Impact:** Brief data gaps for multi-chart assets when switching the main chart. Contributes to the "frozen" appearance.

---

#### ISSUE-07: Frontend `useStreamConnection` Has Race Condition Between Effects

**Severity:** HIGH  
**Files:** `useStreamConnection.js` (L161-177, L179-184)

**Root Cause:** `focusAsset(selectedAsset)` fires in one `useEffect` (L161-177), and `watchAssets(multiChartAssets)` fires in a separate `useEffect` (L179-184). Timing between these two effects is not guaranteed. If `focus_asset` fires after `watch_assets`, multi-chart rooms are dropped.

---

### 🟡 MEDIUM Issues

#### ISSUE-08: `RuntimeStrategyConfigRequest` Missing Fields

**Severity:** MEDIUM  
**Files:** `api/strategy.py` (L11-18)

The Pydantic model is missing `auto_ghost_max_session_trades`, `auto_ghost_max_drawdown_amount`, and `auto_ghost_drawdown_cooldown_seconds`. The frontend sends these (App.jsx L168-174) but they're silently dropped.

---

#### ISSUE-09: Engine Memory Leak — Engines Never Cleaned Up

**Severity:** MEDIUM  
**Files:** `streaming.py` (L38-41, L71-89)

`_oteo_engines`, `_market_context_engines`, `_manip_engines`, and `_tick_counts` grow unboundedly. Every asset that ever sends a tick gets permanent engine allocations.

---

#### ISSUE-10: `clear_detector_buffers` Only Clears Manipulation, Not OTEO

**Severity:** MEDIUM  
**Files:** `streaming.py` (L199-204)

On focus switch, only the manipulation detector's buffers are cleared. OTEO and market context engines retain stale state.

---

## 3. Current State Map

### What Works

| Layer | Component | Status |
|-------|-----------|--------|
| Backend | Tick hook (monkey-patch) | ✅ Fires for all assets |
| Backend | StreamingService pipeline | ✅ Processes ticks, enriches, emits |
| Backend | OTEO + Level 2 Policy | ✅ Stable and tuned |
| Backend | Auto-Ghost execution | ✅ Functional but unfiltered |
| Backend | Manipulation Detector | ✅ Hardened with 15s block |
| Frontend | Socket.IO singleton | ✅ Connected |
| Frontend | useStreamConnection hook | ✅ Receives market_data |
| Frontend | Sparkline + OTEORing | ✅ Renders correctly |
| Frontend | MultiChartView | ✅ Modular cards with gauges |
| Frontend | LeftSidebar asset list | ✅ Payout filtering works |

### What's Broken

| Layer | Component | Issue |
|-------|-----------|-------|
| Backend | StreamingService | No allowlist — processes ALL assets |
| Backend | AutoGhostService | No payout gate — trades any asset |
| Backend | StreamingService | No start/stop lifecycle |
| Backend | PocketOptionSession | Tick callback never cleared on disconnect |
| Backend | main.py | focus_asset and watch_assets conflict |
| Frontend | useStreamConnection | Race condition between two effects |
| Backend | strategy.py | Missing config fields |
| Backend | StreamingService | Engine memory leak |

---

## 4. Implementation Plan

### Phase A: Asset Allowlist & Payout Gate

**Priority:** HIGHEST — Directly affects profitability  
**Addresses:** ISSUE-01, ISSUE-02, ISSUE-04, ISSUE-09  
**Estimated Complexity:** ~80 lines across 4 files

#### A.1 — Add `_allowed_assets` to `StreamingService`

**File:** `app/backend/services/streaming.py`

```python
class StreamingService:
    def __init__(self, sio_server=None):
        # ... existing init ...
        self._allowed_assets: set[str] = set()
        self._streaming_active: bool = False
```

#### A.2 — Add `update_allowed_assets()` method

**File:** `app/backend/services/streaming.py`

```python
def update_allowed_assets(self, assets: list[str]) -> None:
    """Update the set of assets allowed for processing and trading."""
    new_set = set(a.strip() for a in assets if a and isinstance(a, str))
    removed = self._allowed_assets - new_set
    
    # Clean up engines for removed assets
    for asset in removed:
        self._oteo_engines.pop(asset, None)
        self._market_context_engines.pop(asset, None)
        self._manip_engines.pop(asset, None)
        self._tick_counts.pop(asset, None)
        logger.info("Cleaned up engines for removed asset: %s", asset)
    
    self._allowed_assets = new_set
    logger.info("Allowed assets updated: %s", sorted(new_set))
```

#### A.3 — Gate `process_tick()` with allowlist check

**File:** `app/backend/services/streaming.py`

Add at the top of `_process_tick_inner()`:
```python
if not self._streaming_active:
    return
if asset not in self._allowed_assets:
    return
```

#### A.4 — Add `minimum_payout` to `AutoGhostConfig`

**File:** `app/backend/services/auto_ghost.py`

```python
@dataclass(frozen=True)
class AutoGhostConfig:
    # ... existing fields ...
    minimum_payout: float = 0.88  # 88% minimum payout to trade
```

#### A.5 — Add payout check to `consider_signal()`

**File:** `app/backend/services/auto_ghost.py`

Add a new parameter and check:
```python
async def consider_signal(
    self,
    *,
    asset: str,
    price: float,
    timestamp: float,
    oteo_result: dict[str, Any],
    manipulation: dict[str, Any],
    payout: float = 0.0,  # NEW: current payout fraction (0.0-1.0)
) -> dict[str, Any] | None:
    # ... existing checks ...
    
    # Payout gate — reject assets below minimum threshold
    if self.config.minimum_payout > 0 and payout < self.config.minimum_payout:
        logger.debug("Auto-Ghost skipped %s: payout %.1f%% < minimum %.1f%%",
                     asset, payout * 100, self.config.minimum_payout * 100)
        return None
```

#### A.6 — Resolve payout in `StreamingService` and pass to Auto-Ghost

**File:** `app/backend/services/streaming.py`

In `_process_tick_inner()`, before calling `auto_ghost.consider_signal()`:
```python
# Resolve current payout for this asset
payout = self._resolve_asset_payout(asset)

await self.auto_ghost.consider_signal(
    asset=asset,
    price=price,
    timestamp=timestamp,
    oteo_result=oteo_result,
    manipulation=manipulation,
    payout=payout,
)
```

Add helper method:
```python
def _resolve_asset_payout(self, asset: str) -> float:
    """Get the current payout fraction for an asset from the broker."""
    try:
        from ..brokers.pocket_option.assets import _load_live_assets
        live_assets = _load_live_assets()
        for a in live_assets:
            if a.raw_id == asset:
                return float(a.payout)
    except Exception:
        pass
    return 0.0
```

#### A.7 — Add `update_allowed_assets` Socket.IO event

**File:** `app/backend/main.py`

```python
@sio.event
async def update_allowed_assets(sid, data):
    """Update the set of assets the streaming service is allowed to process."""
    assets = data.get("assets", [])
    streaming_service.update_allowed_assets(assets)
```

#### A.8 — Wire frontend to emit `update_allowed_assets`

**File:** `app/frontend/src/hooks/useStreamConnection.js`

Merge the two separate `useEffect` hooks into a single unified effect that:
1. Computes the full asset set: `selectedAsset` + `multiChartAssets`
2. Emits a single `watch_assets` event with the full set
3. Emits `update_allowed_assets` with the same set

```javascript
useEffect(() => {
    if (!selectedAsset) return;
    
    const allAssets = new Set([selectedAsset, ...(multiChartAssets || [])]);
    const assetList = [...allAssets].slice(0, 9);
    
    initSocket();
    watchAssets(assetList);
    
    // Tell backend which assets are allowed for processing
    getSocket().emit('update_allowed_assets', { assets: assetList });
    
    // Clean up tick buffers for assets no longer in the set
    const bufferMap = tickBufferRef.current;
    for (const key of Object.keys(bufferMap)) {
        if (!allAssets.has(key)) {
            delete bufferMap[key];
            clearAsset(key);
        }
    }
}, [selectedAsset, multiChartAssets, clearAsset]);
```

**File:** `app/frontend/src/api/streamApi.js`

Add:
```javascript
export function updateAllowedAssets(assets) {
    getSocket().emit('update_allowed_assets', { assets });
}
```

---

### Phase B: Explicit Stream Start/Stop Lifecycle

**Priority:** HIGH — Eliminates the "need to restart" problem  
**Addresses:** ISSUE-03  
**Estimated Complexity:** ~60 lines across 4 files

#### B.1 — Add `start()` and `stop()` to `StreamingService`

**File:** `app/backend/services/streaming.py`

```python
def start(self) -> None:
    """Enable tick processing."""
    self._streaming_active = True
    logger.info("StreamingService started — tick processing enabled")

def stop(self) -> None:
    """Disable tick processing and clean up all engines."""
    self._streaming_active = False
    self._allowed_assets.clear()
    self._oteo_engines.clear()
    self._market_context_engines.clear()
    self._manip_engines.clear()
    self._tick_counts.clear()
    logger.info("StreamingService stopped — all engines cleared")
```

#### B.2 — Add `clear_tick_callback()` to `PocketOptionSession`

**File:** `app/backend/session/pocket_option_session.py`

```python
@classmethod
def clear_tick_callback(cls):
    """Remove the tick callback to stop dispatching ticks."""
    cls._tick_callback = None
    logger.info("Tick callback cleared")
```

#### B.3 — Wire disconnect to stop streaming

**File:** `app/backend/api/session.py`

In `disconnect_session()`:
```python
@router.post("/disconnect")
async def disconnect_session(request: Request) -> JSONResponse:
    sm = get_session_manager()
    
    # Stop streaming before disconnecting
    streaming_service = request.app.state.streaming_service
    streaming_service.stop()
    PocketOptionSession.clear_tick_callback()
    
    state = sm.disconnect()
    return JSONResponse(content={
        "ok": True,
        "connected": state.connected,
        "message": state.message,
    })
```

#### B.4 — Wire connect to start streaming

**File:** `app/backend/api/session.py`

After successful connect, re-apply the tick callback and start streaming:
```python
# After successful connect, re-enable streaming
try:
    streaming_service = request.app.state.streaming_service
    PocketOptionSession.set_tick_callback(streaming_service.process_tick)
    streaming_service.start()
except Exception as stream_exc:
    logger.warning("Stream start after connect failed (non-fatal): %s", stream_exc)
```

#### B.5 — Frontend: Reset stream state on disconnect

**File:** `app/frontend/src/stores/useStreamStore.js`

Add a `resetAll` action:
```javascript
resetAll: () => set({
    ticks: {},
    signals: {},
    manipulation: {},
    warmup: {},
    tradeMarkers: {},
    isStreaming: false,
}),
```

Wire this in the frontend disconnect flow so the UI clears all stale data.

---

### Phase C: Fix Tick Delivery Reliability

**Priority:** HIGH — Fixes the frozen-chart symptom  
**Addresses:** ISSUE-05, ISSUE-06, ISSUE-07  
**Estimated Complexity:** ~70 lines across 3 files

#### C.1 — Unified Room Management in Backend

**File:** `app/backend/main.py`

Replace the conflicting `focus_asset` and `watch_assets` handlers with a unified approach:

```python
@sio.event
async def focus_asset(sid, data):
    """Focus on a single asset — adds it to the watched set without dropping others."""
    asset = data.get("asset")
    if not asset:
        return

    session = await sio.get_session(sid)
    current_rooms = set(session.get("rooms", []))
    
    room = f"market_data:{asset}"
    if room not in current_rooms:
        await sio.enter_room(sid, room)
        current_rooms.add(room)
    
    await sio.save_session(sid, {"rooms": list(current_rooms)})
    streaming_service.clear_detector_buffers(asset)
    await sio.emit("status", {"status": "focused", "asset": asset}, to=sid)

    try:
        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION)
        if adapter.get_connection_status() == "connected":
            await adapter.subscribe_ticks(asset)
    except Exception as sub_err:
        logger.warning("subscribe_ticks failed for %s: %s", asset, sub_err)


@sio.event
async def watch_assets(sid, data):
    """Set the full list of watched assets — syncs rooms to match exactly."""
    assets = data.get("assets", [])
    if not assets:
        return

    session = await sio.get_session(sid)
    current_rooms = set(session.get("rooms", []))
    target_rooms = {f"market_data:{a}" for a in assets[:9]}
    
    # Leave rooms no longer needed
    for room in current_rooms - target_rooms:
        await sio.leave_room(sid, room)
    
    # Join new rooms
    for room in target_rooms - current_rooms:
        await sio.enter_room(sid, room)
    
    # Subscribe to ticks for new assets
    try:
        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION)
        if adapter.get_connection_status() == "connected":
            new_assets = [a for a in assets[:9] if f"market_data:{a}" not in current_rooms]
            for asset in new_assets:
                await adapter.subscribe_ticks(asset)
    except Exception as sub_err:
        logger.warning("subscribe_ticks (multi) failed: %s", sub_err)

    await sio.save_session(sid, {"rooms": list(target_rooms)})
```

#### C.2 — Add Future Error Handling in Tick Hook

**File:** `app/backend/session/pocket_option_session.py`

In `hooked_set_csv`, add error visibility to the dispatched Future:

```python
future = asyncio.run_coroutine_threadsafe(
    cls._tick_callback(asset, price, ts),
    loop,
)
future.add_done_callback(
    lambda f: logging.getLogger("PocketOptionSession").error(
        "Tick dispatch error for %s: %s", key, f.exception()
    ) if not f.cancelled() and f.exception() else None
)
```

#### C.3 — Merge Frontend Effects into Single Unified Effect

**File:** `app/frontend/src/hooks/useStreamConnection.js`

Replace the two separate `useEffect` hooks (L161-177 and L179-184) with a single unified effect:

```javascript
useEffect(() => {
    if (!selectedAsset) return;

    const allAssets = new Set([selectedAsset]);
    if (Array.isArray(multiChartAssets)) {
        for (const a of multiChartAssets) {
            if (a) allAssets.add(a);
        }
    }
    const assetList = [...allAssets].slice(0, 9);

    // Clean up assets no longer in the set
    const previousAsset = previousSelectedAssetRef.current;
    if (previousAsset && !allAssets.has(previousAsset)) {
        clearAsset(previousAsset);
        delete tickBufferRef.current[previousAsset];
    }
    previousSelectedAssetRef.current = selectedAsset;

    initSocket();
    setWarmup(selectedAsset, true);
    watchAssets(assetList);

    // Tell backend which assets are allowed for processing
    getSocket().emit('update_allowed_assets', { assets: assetList });
}, [selectedAsset, multiChartAssets, clearAsset, setWarmup]);
```

---

### Phase D: Cleanup & Hardening

**Priority:** MEDIUM — Polish and correctness  
**Addresses:** ISSUE-08, ISSUE-10  
**Estimated Complexity:** ~30 lines across 3 files

#### D.1 — Add Missing Fields to `RuntimeStrategyConfigRequest`

**File:** `app/backend/api/strategy.py`

```python
class RuntimeStrategyConfigRequest(BaseModel):
    oteo_level2_enabled: bool = Field(default=False)
    oteo_level3_enabled: bool = Field(default=False)
    auto_ghost_enabled: bool = Field(default=False)
    auto_ghost_amount: float = Field(default=1.0, gt=0)
    auto_ghost_expiration_seconds: int = Field(default=60, ge=5, le=3600)
    auto_ghost_max_concurrent_trades: int = Field(default=3, ge=1, le=20)
    auto_ghost_per_asset_cooldown_seconds: int = Field(default=30, ge=0, le=3600)
    # NEW fields:
    auto_ghost_max_session_trades: int = Field(default=100, ge=1, le=10000)
    auto_ghost_max_drawdown_amount: float = Field(default=0.0, ge=0)
    auto_ghost_drawdown_cooldown_seconds: int = Field(default=300, ge=0, le=36000)
    auto_ghost_minimum_payout: float = Field(default=0.88, ge=0.0, le=1.0)
```

Wire these through `update_runtime_settings()` and `AutoGhostService.update_config()`.

#### D.2 — Add `minimum_payout` to Frontend Settings

**File:** `app/frontend/src/stores/useSettingsStore.js`

Add `autoGhostMinimumPayout: 88` to `SETTINGS_DEFAULTS` and wire through `validateSettings()`.

#### D.3 — Add Error Handling to Strategy API

**File:** `app/backend/api/strategy.py`

Wrap `update_runtime_config` in try/except:
```python
@router.post("/runtime-config")
async def update_runtime_config(body: RuntimeStrategyConfigRequest, request: Request) -> JSONResponse:
    try:
        streaming_service = request.app.state.streaming_service
        config = streaming_service.update_runtime_settings(...)
        return JSONResponse(content={"ok": True, **config})
    except Exception as exc:
        logger.error("Failed to update runtime config: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(exc)},
        )
```

---

## 5. Files Changed Summary

| File | Action | Phase | Change |
|------|--------|-------|--------|
| `app/backend/services/streaming.py` | MODIFIED | A, B | Add `_allowed_assets`, `_streaming_active`, `update_allowed_assets()`, `start()`, `stop()`, `_resolve_asset_payout()`, gate `_process_tick_inner()` |
| `app/backend/services/auto_ghost.py` | MODIFIED | A | Add `minimum_payout` to config, add payout param + check to `consider_signal()` |
| `app/backend/main.py` | MODIFIED | A, C | Add `update_allowed_assets` event, refactor `focus_asset`/`watch_assets` room management |
| `app/backend/session/pocket_option_session.py` | MODIFIED | B, C | Add `clear_tick_callback()`, add Future error callback in hook |
| `app/backend/api/session.py` | MODIFIED | B | Wire `stop()`/`start()` and `clear_tick_callback()` into disconnect/connect |
| `app/backend/api/strategy.py` | MODIFIED | D | Add missing config fields, add error handling |
| `app/frontend/src/hooks/useStreamConnection.js` | MODIFIED | A, C | Merge two effects into one, emit `update_allowed_assets` |
| `app/frontend/src/api/streamApi.js` | MODIFIED | A | Add `updateAllowedAssets()` helper |
| `app/frontend/src/stores/useStreamStore.js` | MODIFIED | B | Add `resetAll()` action |
| `app/frontend/src/stores/useSettingsStore.js` | MODIFIED | D | Add `autoGhostMinimumPayout` setting |

**Total: 10 files modified, 0 files created**

---

## 6. Files Explicitly NOT Touched

| File | Reason |
|------|--------|
| `services/oteo.py` | No changes needed — OTEO core is stable |
| `services/market_context.py` | No changes needed — Level 2 policy is stable |
| `services/manipulation.py` | No changes needed — detector is hardened |
| `services/trade_service.py` | No changes needed — trade execution is correct |
| `components/trading/Sparkline.jsx` | No changes needed — renders from props |
| `components/trading/MultiChartView.jsx` | No changes needed — already has remove button |
| `components/trading/TradingWorkspace.jsx` | No changes needed — reads from store |
| `stores/useAssetStore.js` | No changes needed — already has `removeMultiChartAsset` |

---

## 7. Implementation Order & Dependencies

```
Phase A (Asset Allowlist + Payout Gate)
  ├── A.1-A.3: Backend StreamingService changes
  ├── A.4-A.6: Backend AutoGhost payout gate
  ├── A.7: Backend Socket.IO event
  └── A.8: Frontend unified effect + emit
       ↓
Phase B (Stream Start/Stop Lifecycle)
  ├── B.1: StreamingService start/stop
  ├── B.2: PocketOptionSession clear_tick_callback
  ├── B.3-B.4: Wire into session API
  └── B.5: Frontend stream state reset
       ↓
Phase C (Tick Delivery Reliability)
  ├── C.1: Unified room management
  ├── C.2: Future error handling in hook
  └── C.3: Merged frontend effects (done in A.8)
       ↓
Phase D (Cleanup & Hardening)
  ├── D.1: Missing strategy config fields
  ├── D.2: Frontend minimum payout setting
  └── D.3: Strategy API error handling
```

---

## 8. Verification Checklist

### Phase A Verification
- [ ] Auto-Ghost only trades assets visible in the main chart or multi-chart view
- [ ] Auto-Ghost rejects assets with payout below the configured minimum (default 88%)
- [ ] Removing an asset from multi-chart stops Auto-Ghost from trading it
- [ ] Backend logs show "Allowed assets updated: [...]" when assets change
- [ ] Backend logs show "Auto-Ghost skipped {asset}: payout X% < minimum Y%" for low-payout assets
- [ ] Engine cleanup occurs when assets are removed (no memory leak)

### Phase B Verification
- [ ] Clicking Disconnect stops all tick processing immediately
- [ ] No ticks are processed after disconnect (verify via backend logs)
- [ ] Reconnecting re-enables tick processing
- [ ] Frontend stream state resets on disconnect (no stale data)
- [ ] Auto-Ghost stops executing after disconnect

### Phase C Verification
- [ ] Switching the main chart asset does NOT drop multi-chart subscriptions
- [ ] All multi-chart assets continue updating when the main chart changes
- [ ] No "frozen" assets in the multi-chart view during normal operation
- [ ] Backend logs show tick dispatch errors (if any) instead of silent failures

### Phase D Verification
- [ ] `auto_ghost_max_session_trades`, `auto_ghost_max_drawdown_amount`, `auto_ghost_drawdown_cooldown_seconds` are correctly forwarded from frontend to backend
- [ ] `auto_ghost_minimum_payout` setting appears in App Settings
- [ ] Strategy API returns structured error on failure (not raw 500)

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Allowlist blocks legitimate assets | Low | Missed trades | Allowlist is always the union of selected + multi-chart assets |
| Payout data unavailable | Medium | All assets rejected | Default to 0.0 payout → Auto-Ghost skips (safe failure) |
| `stop()` called during active trade | Low | Trade outcome lost | `stop()` only disables new tick processing, not pending trade tracking |
| Room sync race on rapid asset switching | Low | Brief data gap | Unified effect eliminates the race condition |
| Memory freed too aggressively | Low | Re-warmup needed | Only freed when asset is removed from allowlist |

---

## 10. Risk Forecast — What Breaks If Ignored

| If Ignored | Consequence |
|---|---|
| ISSUE-01 (No allowlist) | Auto-Ghost continues trading low-payout assets, eroding edge. Every session bleeds money on 60-75% payout trades. |
| ISSUE-02 (No payout gate) | Same as above — even if allowlist is added, payout can change mid-session. |
| ISSUE-03 (No stream stop) | Users cannot get a clean session without restarting the backend. Stale data accumulates. |
| ISSUE-05 (No backpressure) | Under high tick volume, the UI freezes and then bursts. Users lose trust in real-time accuracy. |
| ISSUE-06/07 (Room conflicts) | Multi-chart assets intermittently stop updating, creating false impression of market stagnation. |

---

## 11. CORE_PRINCIPLES Alignment

| Principle | How This Plan Adheres |
|-----------|----------------------|
| **#1 Functional Simplicity** | Minimal changes — 10 files modified, 0 new files. Single allowlist set is the source of truth. |
| **#2 Sequential Logic** | Phases A→D execute in strict dependency order. Each builds on the previous. |
| **#3 Incremental Testing** | Each phase has explicit verification criteria. @Reviewer sign-off required per phase. |
| **#4 Zero Assumptions** | Payout defaults to 0.0 (safe rejection). Allowlist defaults to empty (no processing until frontend sends assets). |
| **#5 Code Integrity** | No existing working code removed. All changes are additive gates and lifecycle methods. |
| **#6 Separation of Concerns** | Allowlist lives in StreamingService. Payout gate lives in AutoGhost. Room management lives in main.py. |
| **#8 Defensive Error Handling** | Future error callbacks added. Strategy API wrapped in try/except. |
| **#9 Fail Fast** | Payout check rejects early. Allowlist check rejects early. Streaming active check rejects early. |

---

## 12. Phase Gate Protocol

Per `.clinerules/PHASE_REVIEW_PROTOCOL.md`:

| Phase | Reviewer Gate | Status |
|-------|--------------|--------|
| Phase A | @Reviewer reviews streaming.py + auto_ghost.py + main.py + useStreamConnection.js | [ ] Pending |
| Phase B | @Reviewer reviews session.py + pocket_option_session.py + streaming.py | [ ] Pending |
| Phase C | @Reviewer reviews main.py + pocket_option_session.py | [ ] Pending |
| Phase D | @Reviewer reviews strategy.py + useSettingsStore.js | [ ] Pending |
| **Final** | @Reviewer + @Debugger + @Optimizer + @Code_Simplifier | [ ] Pending |

---

*Plan compiled: 2026-04-12*  
*Source: Forensic investigation of 20+ files across backend and frontend*  
*Compiled by: @Investigator, @Reviewer*  
*Status: Awaiting explicit approval before implementation*
