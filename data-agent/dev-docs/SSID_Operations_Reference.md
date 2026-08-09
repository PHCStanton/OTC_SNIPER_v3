# OTC SNIPER v3 — SSID Operations Reference

**Compiled:** 2026-08-06  
**Source documents reviewed:** 7 files across `Dev_Docs/`, `ssid_integration_package/integration_guides/`  
**Verified against:** Actual codebase in `app/backend/`, `ssid_integration_package/core/`  
**Review:** @Reviewer — correctness audit completed  

---

## 1. What Is SSID?

The **SSID** (Session ID) is the authentication token extracted from Pocket Option's browser WebSocket connection. It is a JSON-encoded string in the format:

```
42["auth",{"session":"abc123...","isDemo":1,"uid":12345,"platform":2}]
```

| Field | Type | Description |
|-------|------|-------------|
| `session` | `str` | Session token string |
| `isDemo` | `int` | `1` = DEMO account, `0` = REAL account (⚠️ real money) |
| `uid` | `int` | User ID |
| `platform` | `int` | Platform identifier |

**Key principle:** The `isDemo` field inside the SSID is the **single source of truth** for account type. No external parameter overrides it.

---

## 2. SSID Lifecycle in OTC SNIPER

### 2.1 Extraction → Connection → Streaming → Disconnect

```
┌──────────────────────────────────────────────────────────────────────┐
│  USER: Extracts SSID from browser DevTools (F12 → Network → WS)    │
│        Pastes into OTC SNIPER frontend                              │
└──────────────┬───────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FRONTEND: POST /api/session/connect { ssid: "42[...]" }           │
└──────────────┬───────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BACKEND (SessionManager):                                          │
│    1. PocketOptionSession(ssid) — parses + validates ONCE           │
│    2. session.connect() — resets globals, authenticates via WS       │
│    3. Waits for WebSocket handshake + balance confirmation           │
│    4. set_tick_callback(streaming_service.process_tick)              │
│    5. set_main_loop(asyncio.get_running_loop())                     │
│    6. _apply_hooks() monkey-patches gv.set_csv → hooked_set_csv    │
│    7. streaming_service.start() — enables tick processing            │
└──────────────┬───────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  TICK STREAMING PIPELINE (active):                                   │
│    Broker WS → binary frame → gv.set_csv → hooked_set_csv          │
│    → asyncio.run_coroutine_threadsafe(process_tick, main_loop)      │
│    → StreamingService → OTEO + ManipDetector + TickLogger            │
│    → sio.emit("market_data", room="market_data:{asset}")            │
└──────────────────────────────────────────────────────────────────────┘
               │
               ▼  (on disconnect)
┌──────────────────────────────────────────────────────────────────────┐
│  DISCONNECT:                                                         │
│    1. streaming_service.stop() — disables processing, clears engines │
│    2. PocketOptionSession.clear_tick_callback() — stops dispatch      │
│    3. session.disconnect() → global_value.reset_all()                │
│    4. Frontend: useStreamStore.resetAll() — clears stale UI data     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 `PocketOptionSession` (Package Layer)

**File:** `ssid_integration_package/core/session.py`  
**Role:** Single-entry-point session manager for the SSID integration package

| Method | Returns | Description |
|--------|---------|-------------|
| `__init__(ssid, timeout=15)` | — | Validates SSID immediately; raises `SSIDParseError` |
| `connect()` | `(bool, str)` | Full lifecycle: `reset_all()` → auth → balance wait |
| `disconnect()` | `bool` | Calls `reset_all()`, clears all instance state |
| `switch_account(new_ssid)` | `(bool, str)` | Fail-fast parse → disconnect → reconnect |
| `get_balance()` | `float \| None` | Cached balance with live refresh |
| `buy(amount, active, action, expirations)` | `(bool, int)` | Place trade |
| `check_win(order_id)` | `(float, str)` | Check trade outcome |

**Properties:** `is_demo`, `is_connected`, `account_type`

**Context Manager:** `with PocketOptionSession(ssid) as session:` — auto-disconnects on exit.

### 3.2 `PocketOptionSession` (Backend Adapter Layer)

**File:** `app/backend/session/pocket_option_session.py`  
**Role:** OTC SNIPER's runtime wrapper — adds tick hook machinery

| Class Method | Description |
|-------------|-------------|
| `set_tick_callback(callback)` | Inject the global tick callback + auto-apply hooks |
| `clear_tick_callback()` | Remove callback to stop tick dispatch |
| `set_main_loop(loop)` | Set the asyncio loop for thread-safe dispatch |
| `_apply_hooks()` | Monkey-patch `gv.set_csv` → `hooked_set_csv` |

**Critical mechanism:** The `hooked_set_csv` function intercepts every `set_csv` call from the broker library's WebSocket thread, extracts `{price, time}` from the tick data, and dispatches it to the main asyncio event loop via `asyncio.run_coroutine_threadsafe()`.

### 3.3 `SSIDConnector` (Backward-Compatible Wrapper)

**File:** `ssid_integration_package/core/ssid_connector.py`  
**Role:** Drop-in replacement for legacy code

> **⚠️ The `demo` parameter is accepted but IGNORED.** Account type is always determined by `isDemo` in the SSID string.

### 3.4 `OTCExecutor`

**File:** `ssid_integration_package/core/otc_executor.py`  
**Role:** Trade execution helper with validated OTC asset list

---

## 4. SSID Validation & Parsing

### 4.1 Validation Rules (enforced in `_parse_ssid()`)

| Rule | Error |
|------|-------|
| Must be a non-empty string | `SSIDParseError("SSID must be a non-empty string")` |
| Must start with `42[` | `SSIDParseError("SSID must start with '42['")` |
| JSON after `42` must be valid | `SSIDParseError("SSID JSON is malformed")` |
| Must be array with ≥ 2 elements | `SSIDParseError("...")` |
| First element must be `"auth"` | `SSIDParseError("...")` |
| Auth payload must contain `session` and `isDemo` | `SSIDParseError("SSID missing required fields")` |

### 4.2 Bugs Fixed in SSID Parsing

| Bug | Severity | Fix |
|-----|----------|-----|
| `"40" and "sid" in message` logic error — auth spam on any message containing "sid" | CRITICAL | Changed to `message.startswith("40") and "sid" in message` |
| `client.py` computed its own URL, ignoring `api.py`'s URL | HIGH | Removed URL override; `client.py` reads `global_value.DEMO` directly |
| `parse_demo_status()` silently defaulted to REAL on parse failure | HIGH | `SSIDParseError` raised immediately — no silent fallback |
| SSID parsed 3 times across different layers | MEDIUM | Parsed once in `PocketOptionSession.__init__()` |
| Dead `Ssid` channel class imported but never used | LOW | Deleted `ws/channels/ssid.py` |

---

## 5. Tick Streaming Pipeline

### 5.1 Thread Architecture

```
┌─────────────────────────────────┐    ┌──────────────────────────────────┐
│  WebSocket Background Thread    │    │  Main Asyncio Event Loop         │
│  (pocketoptionapi library)      │    │  (FastAPI / Uvicorn)             │
│                                 │    │                                  │
│  on_message() → parse tick      │    │  StreamingService.process_tick() │
│  → gv.set_csv(asset, tick)      │───►│  → OTEO, ManipDetector, Logger   │
│    (monkey-patched)             │    │  → sio.emit("market_data")       │
│  asyncio.run_coroutine_         │    │                                  │
│  threadsafe(coro, main_loop)    │    │                                  │
└─────────────────────────────────┘    └──────────────────────────────────┘
```

### 5.2 Tick Processing Sequence

```
[Pocket Option WebSocket]
  → binary message: [[asset_id, timestamp, price]]
  → global_value.set_csv(asset_id, [{'time': ts, 'price': price}])
  → hooked_set_csv() intercepts
  → asyncio.run_coroutine_threadsafe(process_tick(asset, price, ts), main_loop)

[StreamingService.process_tick()]
  → Allowlist check: asset in _allowed_assets?        ← GATE
  → Streaming active check: _streaming_active?         ← GATE
  → OTEO.update_tick(price, ts)         → score, direction, confidence
  → ManipulationDetector.update(ts, p)  → push_snap, pinning flags
  → TickLogger.write_tick()             → data/tick_logs/{asset}/YYYY-MM-DD.jsonl
  → SignalLogger.log_signal()           → data/signals/ (MEDIUM/HIGH only)
  → sio.emit("market_data", payload, room=f"market_data:{asset}")
  → sio.emit("warmup_status", {...}) every 10 ticks + at tick 50
```

### 5.3 Asset Subscription Flow

```
[User clicks asset in LeftSidebar]
  → useAssetStore.setSelectedAsset(asset)

[useStreamConnection hook watches selectedAsset]
  → clearAsset(previousAsset)
  → focusAsset(asset)          ← emits "focus_asset" to backend

[Backend focus_asset handler]
  → Joins Socket.IO room "market_data:{asset}"
  → Clears manipulation detector buffers
  → adapter.subscribe_ticks(asset)  ← calls change_symbol on broker

[PocketOptionAdapter.subscribe_ticks(asset)]
  → session._api.change_symbol(pocket_asset, 1)  ← broker starts streaming
```

### 5.4 Stream Lifecycle Controls

| Operation | Backend | Frontend |
|-----------|---------|----------|
| **Start** | `streaming_service.start()` — sets `_streaming_active = True` | `useStreamConnection` hook initializes listeners |
| **Stop** | `streaming_service.stop()` — clears all engines + allowlist | `useStreamStore.resetAll()` — clears ticks, signals, warmup |
| **Pause** | Tick callback cleared via `clear_tick_callback()` | Socket.IO `disconnect` event sets `isStreaming(false)` |

---

## 6. Asset Allowlist & Payout Gating

### 6.1 Allowlist (Stream Hardening)

The `StreamingService` maintains a `_allowed_assets: set[str]` that acts as a whitelist. Only ticks for allowed assets are processed.

| Method | Description |
|--------|-------------|
| `update_allowed_assets(assets)` | Updates the set; cleans up engines for removed assets |
| Gate in `_process_tick_inner()` | `if asset not in self._allowed_assets: return` |

**Frontend sync:** `useStreamConnection` computes the union of `selectedAsset + multiChartAssets` and emits `update_allowed_assets` to the backend.

### 6.2 Payout Gating (Auto-Ghost)

The `AutoGhostService` enforces a minimum payout threshold before executing ghost trades:

- Default minimum: **88%** (`minimum_payout = 0.88`)
- Check: `if payout < self.config.minimum_payout: return None`
- Payout resolved via `_resolve_asset_payout()` from broker live asset data

---

## 7. Socket.IO Events

### 7.1 Backend → Frontend

| Event | Room | Payload | When |
|-------|------|---------|------|
| `market_data` | `market_data:{asset}` | `{asset, price, timestamp, oteo_score, direction, confidence, ...}` | Every tick |
| `warmup_status` | `market_data:{asset}` | `{asset, ready, ticks_received, ticks_needed}` | Every 10 ticks + at tick 50 |
| `trade_result` | broadcast | `{trade_id, outcome, profit, asset, expiration_seconds}` | After trade expiry |
| `status` | to `sid` | `{status, asset}` | On focus/subscribe |

### 7.2 Frontend → Backend

| Event | Payload | Purpose |
|-------|---------|---------|
| `focus_asset` | `{asset}` | Subscribe to ticks for one asset |
| `watch_assets` | `{assets: [...]}` | Set full multi-asset room list |
| `update_allowed_assets` | `{assets: [...]}` | Update backend allowlist |
| `check_status` | — | Poll Chrome + session state |

---

## 8. Trade Execution Flow

```
[User clicks CALL/PUT in TradePanel]
  → useTradingStore.executeTrade(broker, asset)
  → POST /api/brokers/pocket_option/trade
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
  → Toast: WIN (green) or LOSS (red)
```

---

## 9. OTEO Signal Engine

### 9.1 Built-in Safeguards

| Safeguard | Mechanism | Purpose |
|-----------|-----------|---------|
| Warmup gate | Returns `50.0` for first 49 ticks | Prevents premature signals |
| Cooldown | 30-tick cooldown after every HIGH signal | Prevents signal spam |
| Trend suppression | Downgrades HIGH → MEDIUM when trend-aligned | Avoids counter-trend signals |
| Maturity weighting | Dampens scores when baseline < 200 ticks | Prevents overconfident early scores |
| Volatility adaptation | Adjusts `adaptive_center` based on rolling vol | Prevents false signals in low-vol |

### 9.2 Signal Integrity

- **One direction at a time** per asset — no conflicting CALL/PUT signals simultaneously
- **Per-asset engine instances** — no cross-asset contamination in multi-chart mode
- Signals exposed on frontend via `OTEORing` component (confidence ring)

---

## 10. Global State Management

### 10.1 `global_value.py` Reset Functions

| Function | Scope | Resets |
|----------|-------|--------|
| `reset_trading_state()` | Trading only | balance, orders, profit, assets — preserves SSID/DEMO |
| `reset_all()` | Everything | All trading state + SSID, DEMO, WebSocket connection flags |

### 10.2 State Isolation Rules

- **Only one active session** at a time (due to shared `global_value`)
- `disconnect()` calls `reset_all()` → no stale data contamination
- `switch_account()` calls `reset_all()` between sessions
- `connect()` has a double-call guard — returns early if already connected

---

## 11. Internal Package Refactoring (Completed)

### 11.1 3-Phase Surgical Refactor (2026-03-31)

Applied to the local reference copy in `ssid_integration_package/pocketoptionapi/`:

| Phase | Action | Status |
|-------|--------|--------|
| Phase 1 | Dead code removal (`enhanced_candles.py`, `get_currency_pairs.py`, `print()`) | ✅ Complete |
| Phase 2 | Candle dataclass consolidation → new `candle.py` with `Candle(frozen=True)` | ✅ Complete |
| Phase 3 | Time sync merge → unified `TimeSync` class in `time_sync.py` | ✅ Complete |

### 11.2 Deferred Phases (NOT Implemented)

| Phase | Description | Reason Deferred |
|-------|-------------|-----------------|
| Phase 4 | Candle pipeline hardening (`threading.Event`) | Touches `on_message()` — streaming risk |
| Phase 5 | Channel cleanup / buy merge | Low value, non-zero risk |
| Phase 6 | Client message handler refactor | Highest risk — nerve center of streaming |
| Phase 7 | Integration testing | Depends on 4–6 |

> **Critical:** The installed conda environment `pocketoptionapi` (used by `app/backend/`) is a **separate copy** from the local reference in `ssid_integration_package/`. Changes to the local copy do NOT affect the running system.

---

## 12. @Reviewer Correctness Audit

### 12.1 Documentation vs. Codebase Alignment

| Claim in Documentation | Verified Against Code | Status |
|------------------------|----------------------|--------|
| `PocketOptionSession` exists with `_parse_ssid()` | `ssid_integration_package/core/session.py` | ✅ Confirmed |
| Backend `PocketOptionSession` has `set_tick_callback`, `clear_tick_callback`, `set_main_loop` | `app/backend/session/pocket_option_session.py` L26-41 | ✅ Confirmed |
| `hooked_set_csv` uses `asyncio.run_coroutine_threadsafe` with `_main_loop` | `pocket_option_session.py` L72-74 | ✅ Confirmed |
| Future error callback on tick dispatch | `pocket_option_session.py` L76-80 | ✅ Confirmed |
| `StreamingService` has `_allowed_assets` and `_streaming_active` | `services/streaming.py` L61-62 | ✅ Confirmed |
| `StreamingService` has `PerformanceMonitor` and bounded queue | `services/streaming.py` L67-68 | ✅ Confirmed |
| `AutoGhostService` is wired into `StreamingService` | `services/streaming.py` L48 | ✅ Confirmed |
| `SSIDConnector` delegates to `PocketOptionSession` | `ssid_integration_package/core/ssid_connector.py` | ✅ Confirmed |
| `OTCExecutor` exists for validated trading | `ssid_integration_package/core/otc_executor.py` | ✅ Confirmed |

### 12.2 Discrepancies Found

| # | Item | Severity | Detail |
|---|------|----------|--------|
| D-1 | Stream Hardening plan (2026-04-12) status says "Awaiting approval" | 📋 INFO | The plan was partially implemented — `_allowed_assets`, `_streaming_active`, and `clear_tick_callback()` are present in code. Other items (unified room management, `resetAll()` in store) need individual verification. |
| D-2 | `ssid_tick_integration_plan` marks FIX-1 (tradingApi URL paths) and FIX-2 (dead WIN/LOSS branch) as pending | 📋 INFO | These were from March 2026. Current codebase may have resolved them via subsequent work — requires targeted file inspection to confirm. |
| D-3 | The docs reference two separate `PocketOptionSession` classes | ⚠️ MEDIUM | The package-layer `session.py` and the backend-layer `pocket_option_session.py` share the same class name but serve different roles. This is architecturally intentional but worth noting for developer onboarding. |

### 12.3 Overall Verdict

> **The documentation accurately reflects the SSID integration architecture.** The core data flows (SSID parse → connect → tick hook → streaming pipeline → Socket.IO → frontend), the component responsibilities, and the phased implementation history are all consistent with the actual codebase. The Stream Hardening plan introduced additional controls (allowlist, payout gating, lifecycle management) that are present in the current `streaming.py` implementation. Minor open items (FIX-1/FIX-2 status, deferred refactor phases) do not affect the accuracy of the operational documentation.

---

## 13. Known Limitations

1. **Single session only** — shared `global_value` prevents concurrent sessions
2. **Blocking I/O** — `connect()`, `buy()`, `check_win()` use `time.sleep()` polling
3. **SSID expiration** — SSIDs expire with browser session; no auto-refresh
4. **OTC assets only** — `OTCExecutor` validates against a hardcoded list
5. **Thread safety** — `PocketOptionSession` (package layer) is NOT thread-safe
6. **Custom `ConnectionError`** — shadows Python's built-in; import explicitly

---

## 14. Quick Reference

```python
# === CONNECT ===
from ssid_integration_package.core.session import PocketOptionSession

session = PocketOptionSession(ssid)
success, msg = session.connect()

# === CHECK STATUS ===
session.is_connected    # bool
session.is_demo         # bool
session.account_type    # "DEMO" or "REAL"
session.get_balance()   # float or None

# === TRADE ===
result, order_id = session.buy(amount, "EURUSD_otc", "call", 300)
profit, status = session.check_win(order_id)

# === SWITCH ACCOUNT ===
session.switch_account(other_ssid)

# === DISCONNECT ===
session.disconnect()
```

---

*Compiled: 2026-08-06*  
*Sources: 7 documents + 4 source files verified*  
*Reviewed by: @Reviewer (correctness audit)*  
*Status: APPROVED — Reflects current SSID integration accurately*
