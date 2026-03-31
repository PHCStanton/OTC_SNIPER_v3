# OTC SNIPER v3 — SSID Streaming Test Plan

**Date:** 2026-03-30  
**Status:** Plan — Awaiting explicit "Approve and Proceed" before implementation  
**Compiled by:** @Investigator (forensic analysis of full tick delivery chain)  
**Scope:** Verify that the `pocketoptionapi` library delivers real live tick data from Pocket Option's WebSocket servers through the v3 streaming pipeline  
**Test File:** `scripts/test_streaming.py`  
**Environment:** `QuFLX-v2` conda environment  
**CORE_PRINCIPLES:** All test code must adhere to `.agents/CORE_PRINCIPLES.md`

---

## 1. Executive Summary

This plan defines a **live streaming test** that connects to the real Pocket Option WebSocket using a valid SSID, subscribes to an OTC asset, and verifies that live tick data flows through the entire v3 streaming pipeline — from the broker's WebSocket all the way through OTEO enrichment and Socket.IO emission.

The purpose is to **validate the `pocketoptionapi` library's direct WebSocket approach** before wiring the frontend, since the developer is familiar with the previous WebSocket interception + Redis approach (used in the legacy `web_app`) but has not yet seen this direct-connection method in action.

---

## 2. Investigation Findings — Complete Tick Delivery Chain

### 2.1 The `pocketoptionapi` Library (Installed Version)

The `pocketoptionapi` library is installed in the `QuFLX-v2` conda environment at:
```
C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi
```

**Critical note:** The local copy at `ssid_integration_package/pocketoptionapi/` is an **older, incomplete version** that does NOT have the `set_csv` function. The installed version in the conda environment is the correct one.

### 2.2 How Live Ticks Flow (Complete Chain)

```
Step 1: PocketOption(ssid).connect()
  → Starts a WebSocket thread to wss://demo-api-eu.po.market/socket.io/
  → Authenticates with the SSID string
  → Server responds with 451-["successauth"]
  → global_value.websocket_is_connected = True

Step 2: api.change_symbol("EURUSD_otc", 60)
  → Sends 42["changeSymbol",{"asset":"EURUSD_otc","period":60}]
  → Server responds with 451-["updateStream"]
  → WebsocketClient.updateStream = True

Step 3: Live tick arrives as binary WebSocket message
  → Parsed as list: [[asset_id, timestamp, price]]
  → Creates dict: h = {'time': timestamp, 'price': price}
  → Calls global_value.set_csv(asset_id, [h])

Step 4: OUR MONKEY-PATCH intercepts set_csv
  → PocketOptionSession._apply_hooks() replaced gv.set_csv with hooked_set_csv
  → hooked_set_csv extracts: asset (key), price (tick['price']), timestamp (tick['time'])
  → Schedules async call: StreamingService.process_tick(asset, price, timestamp)

Step 5: StreamingService enriches and emits
  → OTEO.update_tick(price, timestamp) — scoring, velocity, z-score, maturity, cooldown
  → ManipulationDetector.update(timestamp, price) — push_snap, pinning flags
  → TickLogger.write_tick() — async JSONL persistence to data/tick_logs/
  → SignalLogger.log_signal() — async JSONL for MEDIUM/HIGH signals to data/signals/
  → sio.emit("market_data", payload, room=f"market_data:{asset}")
  → sio.emit("warmup_status", {...}, room=...) — every 10 ticks + at tick 50
```

### 2.3 The `set_csv` Function (Installed Version)

Located in the installed `global_value.py`, `set_csv(key, value, path=None)` is the library's internal function for writing tick data to CSV files. It receives:
- `key` — the asset identifier (e.g., `"EURUSD_otc"`)
- `value` — a list of tick dicts, each with `{'time': timestamp, 'price': price_value}`
- `path` — optional subdirectory

The v3 monkey-patch in `PocketOptionSession._apply_hooks()` replaces this function to intercept every tick before it's written to CSV, extracting the asset/price/timestamp and routing it into the `StreamingService`.

### 2.4 Key Difference from Legacy Approach

| Aspect | Legacy (web_app) | v3 (OTC SNIPER) |
|--------|-------------------|------------------|
| **Tick source** | Chrome WebSocket interception via CDP | `pocketoptionapi` library's own WebSocket client |
| **Transport** | Redis Pub/Sub (`market_data` channel) | Direct in-process callback |
| **Collector** | Separate `collector_main.py` process | No separate collector — library IS the collector |
| **SSID usage** | Browser session cookie | Direct WebSocket auth frame |
| **Latency** | Higher (Chrome → CDP → Redis → Gateway) | Lower (Library WS → callback → StreamingService) |
| **Complexity** | Higher (3 processes: Chrome, Collector, Gateway) | Lower (1 process: FastAPI + Socket.IO) |

### 2.5 Frontend Status (Not Yet Wired)

The frontend has all building blocks ready but **nothing connects `market_data` events to the store**:

| Component | Status | Purpose |
|-----------|--------|---------|
| `socketClient.js` | ✅ Exists | Socket.IO singleton, connects to backend |
| `streamApi.js` | ✅ Exists | `focusAsset()`, `watchAssets()`, `onMarketData()`, `onSignal()` helpers |
| `useStreamStore.js` | ✅ Exists | Zustand store with `updateTicks`, `updateSignal`, `setWarmup` |
| `App.jsx` | ⚠️ Partial | Only subscribes to `status_update`, NOT `market_data` |
| `useMarketStream` hook | ❌ Missing | No hook wires `market_data` → `useStreamStore` |

**This test focuses on the backend pipeline only.** Frontend wiring is Phase 10A work.

---

## 3. Prerequisites

### 3.1 Environment
- **Conda environment:** `QuFLX-v2` (has `pocketoptionapi` installed)
- **Python packages required:** `pocketoptionapi`, `python-socketio[asyncio_client]`, `uvicorn`, `aiofiles`, `numpy`, `fastapi`
- **All should already be installed** in the conda env

### 3.2 Valid SSID
The test requires a valid Pocket Option SSID. The test script will attempt to read it from:
1. `app/.env` → `PO_SSID_DEMO` or `PO_SSID_REAL` environment variable
2. If not found → prompt the user for manual input

### 3.3 Network
- Internet connection required (connects to `wss://demo-api-eu.po.market`)
- No Chrome or browser needed — the library connects directly

### 3.4 No Backend Server Required
The test script runs the streaming pipeline **in-process** — it does not need the full FastAPI/uvicorn server running. It instantiates `StreamingService` directly and connects a Socket.IO test client to verify event emission.

---

## 4. Test Architecture

### 4.1 Test File Location
```
scripts/test_streaming.py
```

### 4.2 Test Structure

```python
# scripts/test_streaming.py — Live Streaming Pipeline Test

# Phase A: Setup
#   1. Activate QuFLX-v2 conda env (must be done before running)
#   2. Import pocketoptionapi from installed package
#   3. Import StreamingService, OTEO, ManipulationDetector from app/backend
#   4. Create a temp data directory for tick/signal logs
#   5. Read SSID from .env or prompt user

# Phase B: Connection
#   6. Set global_value.SSID and global_value.DEMO
#   7. Create PocketOption(ssid) instance
#   8. Call api.connect() — starts WebSocket thread
#   9. Wait for connection (check_connect() polling, 15s timeout)
#   10. Verify balance retrieval (authentication confirmation)

# Phase C: Tick Hook Setup
#   11. Create Socket.IO AsyncServer (in-memory, no HTTP)
#   12. Create StreamingService(sio_server=sio)
#   13. Apply PocketOptionSession.set_tick_callback(streaming_service.process_tick)
#   14. Connect a Socket.IO AsyncClient to the server
#   15. Client joins room "market_data:{asset}" via focus_asset event

# Phase D: Subscribe to Asset
#   16. Call api.change_symbol("EURUSD_otc", 60) to start tick stream
#   17. Start collecting ticks for configurable duration (default: 90 seconds)

# Phase E: Live Tick Collection & Display
#   18. For each tick received via Socket.IO market_data event:
#       - Print tick data in real-time (asset, price, timestamp, OTEO score, confidence)
#       - Track tick count, warmup transition, signal events
#       - Detect OTEO warmup → enriched transition at tick 50
#   19. Also listen for warmup_status events

# Phase F: Verification & Summary
#   20. Print summary table:
#       - Total ticks received
#       - OTEO warmup completed? (yes/no, at which tick)
#       - OTEO score range (min/max)
#       - Signals detected (HIGH/MEDIUM count)
#       - Manipulation flags detected
#       - Tick log files created? (check temp data dir)
#       - Signal log files created?
#   21. Print PASS/FAIL for each verification point

# Phase G: Cleanup
#   22. Disconnect PocketOption session
#   23. Clean up temp data directory (optional — user can keep for inspection)
#   24. Print final status
```

### 4.3 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    test_streaming.py                              │
│                                                                   │
│  ┌──────────────────┐     ┌──────────────────────────────────┐   │
│  │ PocketOption API  │     │ StreamingService                 │   │
│  │ (installed lib)   │     │ (from app/backend/services)      │   │
│  │                   │     │                                  │   │
│  │ connect(ssid)     │     │  ┌─────────┐  ┌──────────────┐  │   │
│  │ change_symbol()   │────▶│  │  OTEO   │  │ Manipulation │  │   │
│  │                   │     │  │ Engine  │  │  Detector    │  │   │
│  │ global_value      │     │  └─────────┘  └──────────────┘  │   │
│  │   .set_csv ──────▶│     │                                  │   │
│  │   (monkey-patched)│     │  ┌─────────┐  ┌──────────────┐  │   │
│  └──────────────────┘     │  │  Tick   │  │   Signal     │  │   │
│                            │  │ Logger  │  │   Logger     │  │   │
│                            │  └─────────┘  └──────────────┘  │   │
│                            │                                  │   │
│                            │  Socket.IO emit("market_data")   │   │
│                            └──────────────┬───────────────────┘   │
│                                           │                       │
│  ┌────────────────────────────────────────▼───────────────────┐   │
│  │ Socket.IO Test Client                                      │   │
│  │                                                            │   │
│  │  on("market_data") → print tick + collect stats            │   │
│  │  on("warmup_status") → print warmup progress               │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Console Output (real-time)                                 │   │
│  │                                                            │   │
│  │  [TICK   1] EURUSD_otc | 1.08234 | warmup (1/50)          │   │
│  │  [TICK   2] EURUSD_otc | 1.08236 | warmup (2/50)          │   │
│  │  ...                                                       │   │
│  │  [TICK  50] EURUSD_otc | 1.08241 | OTEO: 62.3 CALL MED    │   │
│  │  [TICK  51] EURUSD_otc | 1.08239 | OTEO: 71.8 PUT  MED    │   │
│  │  ...                                                       │   │
│  │  ═══════════════════════════════════════════════════════    │   │
│  │  SUMMARY                                                   │   │
│  │  Total ticks: 87                                           │   │
│  │  OTEO warmup: YES (tick 50)                                │   │
│  │  Score range: 42.1 — 78.6                                  │   │
│  │  Signals: 0 HIGH, 3 MEDIUM                                 │   │
│  │  Tick logs: YES (data/tick_logs/EURUSD_otc/)               │   │
│  └────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 5. Test Cases

### T1 — Pocket Option WebSocket Connection
| Aspect | Detail |
|--------|--------|
| **What** | Connect to Pocket Option using SSID via `pocketoptionapi` library |
| **How** | `PocketOption(ssid).connect()` → poll `check_connect()` for 15s |
| **Pass** | `check_connect()` returns `True` within 15 seconds |
| **Fail** | Timeout or `NotAuthorized` error |
| **Validates** | The `pocketoptionapi` library can authenticate with a valid SSID |

### T2 — Balance Retrieval (Authentication Proof)
| Aspect | Detail |
|--------|--------|
| **What** | Retrieve account balance after connection |
| **How** | `api.get_balance()` polling for 20s |
| **Pass** | Balance is a non-None numeric value |
| **Fail** | Balance remains None after 20s |
| **Validates** | SSID is valid and session is fully authenticated |

### T3 — Tick Hook (Monkey-Patch) Applied
| Aspect | Detail |
|--------|--------|
| **What** | Verify `PocketOptionSession.set_tick_callback()` successfully patches `global_value.set_csv` |
| **How** | Check that `global_value.set_csv` is not the original function after hook application |
| **Pass** | `global_value.set_csv` is the hooked version |
| **Fail** | `global_value.set_csv` is still the original CSV writer |
| **Validates** | The monkey-patch mechanism works with the installed library version |

### T4 — Asset Subscription (changeSymbol)
| Aspect | Detail |
|--------|--------|
| **What** | Subscribe to an OTC asset's live tick stream |
| **How** | `api.change_symbol("EURUSD_otc", 60)` |
| **Pass** | Server responds with `updateStream` event (library sets `updateStream = True`) |
| **Fail** | No response or error |
| **Validates** | The library can subscribe to specific asset streams |

### T5 — Live Tick Reception
| Aspect | Detail |
|--------|--------|
| **What** | Receive at least 1 live tick from Pocket Option |
| **How** | Wait for `market_data` event on Socket.IO test client (30s timeout) |
| **Pass** | At least 1 tick received with valid `asset`, `price`, `timestamp` fields |
| **Fail** | No ticks received within 30 seconds |
| **Validates** | The complete chain: PO WebSocket → `set_csv` hook → `StreamingService.process_tick()` → Socket.IO emit |

### T6 — Tick Payload Shape
| Aspect | Detail |
|--------|--------|
| **What** | Verify the `market_data` payload contains all expected fields |
| **How** | Inspect the first received tick payload |
| **Pass** | Payload contains: `asset`, `price`, `timestamp`, `source`, `oteo_score`, `manipulation` |
| **Fail** | Any required field is missing |
| **Validates** | `StreamingService` correctly enriches and formats the payload |

### T7 — OTEO Warmup Transition
| Aspect | Detail |
|--------|--------|
| **What** | Verify OTEO transitions from warmup (score=50.0) to enriched scoring at tick 50 |
| **How** | Collect ticks and check: ticks 1-49 have `oteo_score: 50.0`, tick 50+ has enriched dict fields |
| **Pass** | Tick 50 includes `velocity`, `z_score`, `maturity`, `confidence`, `recommended` |
| **Fail** | Tick 50+ still returns `oteo_score: 50.0` without enrichment fields |
| **Validates** | OTEO engine warms up correctly from live data |

### T8 — Warmup Status Events
| Aspect | Detail |
|--------|--------|
| **What** | Verify `warmup_status` Socket.IO events fire at expected intervals |
| **How** | Listen for `warmup_status` events during tick collection |
| **Pass** | Events fire at tick 10, 20, 30, 40, 50 with `ready: false` → `ready: true` at 50 |
| **Fail** | No warmup events received, or `ready` never becomes `true` |
| **Validates** | Frontend warmup indicator will work correctly when wired |

### T9 — Tick Logging (JSONL Persistence)
| Aspect | Detail |
|--------|--------|
| **What** | Verify ticks are written to JSONL files in the data directory |
| **How** | After collection, check `data/tick_logs/{asset}/` for `.jsonl` files |
| **Pass** | At least 1 JSONL file exists with valid tick records |
| **Fail** | No files created, or files contain invalid JSON |
| **Validates** | `TickLogger` correctly persists live tick data |

### T10 — Signal Logging
| Aspect | Detail |
|--------|--------|
| **What** | Verify MEDIUM/HIGH signals are logged to the signals directory |
| **How** | After collection (if any MEDIUM/HIGH signals fired), check `data/signals/` |
| **Pass** | If signals fired: JSONL file exists with valid signal records. If no signals: directory exists but empty (acceptable — depends on market conditions) |
| **Fail** | Signal logger crashes or produces invalid output |
| **Validates** | `SignalLogger` correctly captures enriched signal data |

### T11 — Tick Data Quality
| Aspect | Detail |
|--------|--------|
| **What** | Verify tick prices are realistic and timestamps are sequential |
| **How** | Check that prices are within reasonable range for the asset, timestamps increase monotonically |
| **Pass** | All prices > 0, all timestamps increase, no NaN/Inf values |
| **Fail** | Prices are 0, negative, NaN, or timestamps are out of order |
| **Validates** | The data quality from the direct WebSocket approach matches expectations |

### T12 — Multi-Tick Throughput
| Aspect | Detail |
|--------|--------|
| **What** | Measure tick frequency over the collection period |
| **How** | Count total ticks / elapsed seconds |
| **Pass** | At least 0.5 ticks/second average (OTC markets typically deliver 1-10 ticks/sec) |
| **Fail** | Less than 0.5 ticks/second or zero ticks |
| **Validates** | The direct WebSocket approach delivers sufficient data for real-time trading |

---

## 6. Expected Console Output

```
╔══════════════════════════════════════════════════════════════════╗
║          OTC SNIPER v3 — Live Streaming Pipeline Test           ║
╚══════════════════════════════════════════════════════════════════╝

[SETUP] Conda environment: QuFLX-v2
[SETUP] pocketoptionapi location: C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi
[SETUP] Reading SSID from app/.env (PO_SSID_DEMO)...
[SETUP] SSID loaded: 42["auth",{"session":"a1b2...","isDemo":1}] (truncated)
[SETUP] Account type: DEMO
[SETUP] Test asset: EURUSD_otc
[SETUP] Collection duration: 90 seconds

── Phase B: Connection ─────────────────────────────────────────────
[CONN] Connecting to Pocket Option (DEMO)...
[CONN] WebSocket connecting to wss://demo-api-eu.po.market/socket.io/...
[CONN] ✅ T1 PASS — Connected in 3.2s
[CONN] Retrieving balance...
[CONN] ✅ T2 PASS — Balance: $50,000.00 (DEMO)

── Phase C: Tick Hook Setup ────────────────────────────────────────
[HOOK] Applying tick callback hook...
[HOOK] ✅ T3 PASS — set_csv monkey-patch applied successfully
[HOOK] StreamingService initialized with Socket.IO server
[HOOK] Test client connected to Socket.IO
[HOOK] Joined room: market_data:EURUSD_otc

── Phase D: Asset Subscription ─────────────────────────────────────
[SUB]  Subscribing to EURUSD_otc (period=60)...
[SUB]  ✅ T4 PASS — changeSymbol sent, awaiting ticks...

── Phase E: Live Tick Collection (90s) ─────────────────────────────
[TICK    1] EURUSD_otc | price: 1.08234 | ts: 1711828800.12 | OTEO: 50.0 (warmup 1/50)
[TICK    2] EURUSD_otc | price: 1.08236 | ts: 1711828801.05 | OTEO: 50.0 (warmup 2/50)
[TICK    3] EURUSD_otc | price: 1.08235 | ts: 1711828801.98 | OTEO: 50.0 (warmup 3/50)
...
[WARMUP ] EURUSD_otc | ticks: 10 | ready: false
[TICK   10] EURUSD_otc | price: 1.08241 | ts: 1711828810.33 | OTEO: 50.0 (warmup 10/50)
...
[WARMUP ] EURUSD_otc | ticks: 20 | ready: false
...
[WARMUP ] EURUSD_otc | ticks: 50 | ready: true
[TICK   50] EURUSD_otc | price: 1.08252 | ts: 1711828850.44 | OTEO: 58.3 | CALL | LOW | maturity: 0.15
[TICK   51] EURUSD_otc | price: 1.08249 | ts: 1711828851.21 | OTEO: 61.7 | PUT  | MEDIUM | maturity: 0.16
[SIGNAL ] EURUSD_otc | score: 61.7 | PUT | MEDIUM | price: 1.08249
...
[TICK   87] EURUSD_otc | price: 1.08261 | ts: 1711828890.55 | OTEO: 45.2 | CALL | LOW | maturity: 0.34

── Phase F: Verification Summary ───────────────────────────────────
╔══════════════════════════════════════════════════════════════════╗
║                      TEST RESULTS                                ║
╠══════════════════════════════════════════════════════════════════╣
║  T1  Connection              ✅ PASS  (3.2s)                    ║
║  T2  Balance                 ✅ PASS  ($50,000.00 DEMO)         ║
║  T3  Tick Hook               ✅ PASS  (set_csv patched)         ║
║  T4  Asset Subscription      ✅ PASS  (EURUSD_otc)              ║
║  T5  Live Tick Reception     ✅ PASS  (87 ticks in 90s)         ║
║  T6  Payload Shape           ✅ PASS  (all fields present)      ║
║  T7  OTEO Warmup Transition  ✅ PASS  (enriched at tick 50)     ║
║  T8  Warmup Status Events    ✅ PASS  (5 events, ready=true@50) ║
║  T9  Tick Logging            ✅ PASS  (1 JSONL file, 87 lines)  ║
║  T10 Signal Logging          ✅ PASS  (3 MEDIUM signals logged) ║
║  T11 Tick Data Quality       ✅ PASS  (all prices valid)        ║
║  T12 Tick Throughput         ✅ PASS  (0.97 ticks/sec avg)      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Total Ticks:     87                                             ║
║  Duration:        90.0s                                          ║
║  Avg Frequency:   0.97 ticks/sec                                 ║
║  OTEO Score Range: 42.1 — 78.6                                   ║
║  Signals:         0 HIGH, 3 MEDIUM, 84 LOW                      ║
║  Manipulation:    0 push_snap, 0 pinning                         ║
║  Tick Log Files:  1 (data/tick_logs/EURUSD_otc/2026-03-30.jsonl) ║
║  Signal Log Files: 1 (data/signals/)                             ║
║                                                                  ║
║  OVERALL: 12/12 PASSED ✅                                        ║
╚══════════════════════════════════════════════════════════════════╝

── Phase G: Cleanup ────────────────────────────────────────────────
[CLEAN] Disconnecting from Pocket Option...
[CLEAN] Session disconnected.
[CLEAN] Tick log files preserved at: app/data/tick_logs/EURUSD_otc/
[CLEAN] Done.
```

---

## 7. Implementation Details

### 7.1 SSID Source Strategy

The test script reads the SSID in this priority order:

1. **`app/.env`** → `PO_SSID_DEMO` (for demo account) or `PO_SSID_REAL` (for real account)
2. **Command-line argument** → `python scripts/test_streaming.py --ssid "42[\"auth\",{...}]"`
3. **Interactive prompt** → If neither is available, prompt the user to paste the SSID

Default account type is **DEMO** (safe for testing). Use `--real` flag for real account.

### 7.2 Configurable Parameters

| Parameter | Default | CLI Flag | Description |
|-----------|---------|----------|-------------|
| Asset | `EURUSD_otc` | `--asset` | OTC asset to subscribe to |
| Duration | `90` seconds | `--duration` | How long to collect ticks |
| Account | `demo` | `--real` | Use real account instead of demo |
| Data dir | `app/data` | `--data-dir` | Where tick/signal logs are written |
| Verbose | `false` | `--verbose` | Print raw WebSocket messages |

### 7.3 Error Handling

The test script must handle these failure modes explicitly:

| Failure | Detection | Response |
|---------|-----------|----------|
| `pocketoptionapi` not importable | `ImportError` at startup | Print clear message: "Run in QuFLX-v2 conda env" |
| Invalid/expired SSID | `NotAuthorized` WebSocket message | Print: "SSID is invalid or expired. Get a new one from Chrome DevTools." |
| Connection timeout | `check_connect()` returns False after 15s | Print: "Connection timeout. Check internet and SSID." |
| No ticks received | 0 ticks after 30s of subscription | Print: "No ticks received. Asset may be closed or SSID may lack permissions." |
| `set_csv` not found | `hasattr(gv, 'set_csv')` is False | Print: "Wrong pocketoptionapi version. Ensure QuFLX-v2 conda env is active." |

### 7.4 sys.path Configuration

The test script needs to import from `app/backend/`. It will add the necessary paths:

```python
import sys
from pathlib import Path

# Add app/backend to sys.path so we can import StreamingService, OTEO, etc.
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_APP_BACKEND = _PROJECT_ROOT / "app" / "backend"

sys.path.insert(0, str(_APP_BACKEND.parent))  # for "from backend.services.streaming import ..."
sys.path.insert(0, str(_APP_BACKEND))          # for direct imports if needed
```

### 7.5 Socket.IO In-Process Test

To verify Socket.IO emission without running a full HTTP server, the test will:

1. Create a `socketio.AsyncServer(async_mode='asgi')` 
2. Pass it to `StreamingService(sio_server=sio)`
3. Create a `socketio.AsyncClient()` that connects via an in-process ASGI transport
4. The client joins the appropriate room and listens for `market_data` events

If in-process Socket.IO transport proves too complex, the fallback approach is:
- Skip Socket.IO verification
- Instead, directly inspect the `StreamingService` output by adding a simple callback collector
- This still validates the entire pipeline except the final Socket.IO emission step

---

## 8. Dependencies Check

Before running the test, verify these are available in the `QuFLX-v2` conda environment:

```bash
conda activate QuFLX-v2
python -c "import pocketoptionapi; print('pocketoptionapi OK')"
python -c "import socketio; print('python-socketio OK')"
python -c "import uvicorn; print('uvicorn OK')"
python -c "import aiofiles; print('aiofiles OK')"
python -c "import numpy; print('numpy OK')"
python -c "import fastapi; print('fastapi OK')"
```

If `python-socketio[asyncio_client]` is not installed:
```bash
pip install "python-socketio[asyncio_client]"
```

---

## 9. Run Instructions

```bash
# 1. Activate the conda environment
conda activate QuFLX-v2

# 2. Navigate to project root
cd C:\v3\OTC_SNIPER

# 3. Run the test (demo account, default asset, 90 seconds)
python scripts/test_streaming.py

# 4. Or with custom parameters
python scripts/test_streaming.py --asset GBPJPY_otc --duration 120

# 5. Or with a specific SSID
python scripts/test_streaming.py --ssid "42[\"auth\",{\"session\":\"abc123\",\"isDemo\":1}]"

# 6. Or for real account
python scripts/test_streaming.py --real
```

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SSID expired during test | Medium | Test fails at T1/T2 | Clear error message + instructions to get new SSID |
| OTC market closed (weekend) | Medium | No ticks received (T5 fails) | Test during market hours; print market schedule hint |
| `pocketoptionapi` version mismatch | Low | `set_csv` not found (T3 fails) | Verify conda env before running |
| Network interruption | Low | Connection drops mid-test | Graceful disconnect + partial results |
| Tick frequency too low | Low | T12 fails | Adjust threshold; OTC markets vary |
| Socket.IO in-process transport issues | Medium | T5-T8 may not work via Socket.IO | Fallback to direct callback collector |

---

## 11. Success Criteria

The test is considered **successful** if:

1. ✅ All 12 test cases pass (T1–T12)
2. ✅ Live tick data from Pocket Option is visible in real-time console output
3. ✅ OTEO enrichment produces meaningful scores after warmup
4. ✅ Tick and signal JSONL files are created with valid data
5. ✅ The entire pipeline runs without crashes or silent failures

If the test passes, it confirms that:
- The `pocketoptionapi` direct WebSocket approach **works** for live tick data
- The v3 streaming pipeline (OTEO + ManipulationDetector + Loggers) is **functional**
- The backend is **ready for frontend wiring** (Phase 10A)

---

## 12. Post-Test Next Steps

After a successful test:

1. **Phase 10A** — Wire frontend `market_data` subscription (`useMarketStream` hook → `useStreamStore` → Sparkline)
2. **Phase 10E** — Settings API + `global.json` defaults
3. **Phase 10B** — Backend Ghost Trader integration into `StreamingService`
4. **Phase 10C** — Trade Manager + Tick Log Cleanup task
5. **Phase 10D** — Frontend Ghost Trading UI + Signal Alerts

Each phase will be reviewer-gated per `PHASE_REVIEW_PROTOCOL.md`.

---

## 13. CORE_PRINCIPLES Alignment

| Principle | How This Test Adheres |
|-----------|----------------------|
| **#1 Functional Simplicity** | Single test file, no test framework dependency, clear sequential flow |
| **#2 Sequential Logic** | Phases A→G execute in strict order; each depends on the previous |
| **#3 Incremental Testing** | Each test case validates one specific aspect of the pipeline |
| **#4 Zero Assumptions** | SSID is validated before use; library version is checked; all paths have explicit error handling |
| **#8 Defensive Error Handling** | Every failure mode has a clear error message and graceful exit |
| **#9 Fail Fast** | Invalid SSID, missing library, or connection failure stops the test immediately with a clear reason |

---

*Document compiled: 2026-03-30*  
*Source: Forensic investigation of `pocketoptionapi` installed library, `app/backend/` streaming pipeline, and `app/frontend/` Socket.IO client*  
*No code changes made — test plan only*  
*Awaiting explicit "Approve and Proceed" command before implementation*
