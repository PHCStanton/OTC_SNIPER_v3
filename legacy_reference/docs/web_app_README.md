# OTC SNIPER — Web Application

> **Real-time OTC binary options analysis platform powered by the OTEO momentum engine.**  
> Built on React + FastAPI + Redis. Designed for speed, clarity, and zero-latency signal delivery.

---

## Table of Contents

1. [Overview](#overview)
2. [Feature Summary](#feature-summary)
3. [Architecture & Data Flow](#architecture--data-flow)
4. [Startup Workflow](#startup-workflow)
5. [The OTEO Engine & Asset Warmup System](#the-oteo-engine--asset-warmup-system)
6. [Asset Normalization](#asset-normalization)
7. [Manipulation Detection](#manipulation-detection)
8. [Frontend UI Guide](#frontend-ui-guide)
9. [Ops Control (Chrome / Stream / SSID)](#ops-control-chrome--stream--ssid)
10. [Port Reference](#port-reference)
11. [File Structure](#file-structure)
12. [Environment Variables](#environment-variables)

---

## Overview

OTC SNIPER is a standalone web application that intercepts live price ticks from Pocket Option (via Chrome DevTools Protocol), enriches them with the **OTEO** (OTC Tick Exhaustion Oscillator) momentum scoring engine, detects market manipulation patterns, and delivers real-time signals to a React dashboard.

The platform is designed for **OTC binary options trading** where conditions change in seconds. Every design decision prioritises low latency, honest signal readiness, and zero silent failures.

---

## Feature Summary

| Feature | Description |
|---------|-------------|
| **Live Sparkline Chart** | SVG-based real-time price chart with adaptive scaling, green fill area, and a pulsing live-price dot |
| **OTEO Momentum Ring** | Circular progress ring (0–100 score) showing momentum exhaustion probability. Cyan = high score (≥75), amber = building |
| **CALL / PUT Signal** | Direction recommendation derived from price velocity — trades *opposite* momentum (exhaustion strategy) |
| **Confidence Level** | HIGH / MEDIUM / LOW based on OTEO score thresholds (>75 / >55 / ≤55) |
| **OTEO Warmup Indicator** | Amber progress bar showing tick count toward the 50-tick warmup threshold |
| **Manipulation Detection** | Real-time Push/Snap and Pinning detection overlaid on the Sparkline |
| **Asset Search & Filter** | Instant search across all available OTC assets |
| **Quick Select (Favourites)** | Star any asset to pin it to the Quick Select bar for one-click access |
| **Auto-Refresh** | Configurable asset list refresh (manual / 1 / 3 / 5 / 10 min) |
| **Ops Control TopBar** | Launch Chrome, start/stop the tick collector, and connect SSID — all from the UI |
| **Toast Feedback** | All ops actions (Chrome start/stop, stream start/stop, SSID connect) show toast notifications |
| **Demo / Real Account Toggle** | Switch between demo and real account balances and trade history |
| **Trade Execution** | CALL / PUT trade buttons with configurable amount and expiration |
| **Session Trade History** | Scrollable table of trades with WIN / LOSS / PENDING status |
| **WebSocket Account Updates** | Live balance and trade history pushed via WebSocket every second |

---

## Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CHROME (Pocket Option)                       │
│                   Chrome DevTools Protocol :9222                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  WebSocket frames intercepted
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              OTC Sniper Collector  (collector_main.py)              │
│   Parses tick frames → normalize_asset() → PUBLISH to Redis         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  Redis PUBLISH  "market_data" channel
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Redis  (localhost:6379)                           │
│              Shared message bus — also used by QuFLX v2             │
└──────────┬──────────────────────────────────────────────────────────┘
           │  SUBSCRIBE
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│          Redis Streaming Gateway  (redis_gateway.py :3001)          │
│                                                                     │
│  enrichment_handler()                                               │
│  ├── normalize_asset()          ← consistent room naming            │
│  ├── OTEO.update_tick()         ← momentum scoring                  │
│  ├── ManipulationDetector.update() ← push/snap + pinning            │
│  └── warmup_status emit         ← every 10 ticks                    │
│                                                                     │
│  SocketIOBridge → room: market_data:{ASSET}                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  Socket.IO  (asset-scoped rooms)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              React Frontend  (Vite dev server :5175)                │
│                                                                     │
│  TradingPlatform.jsx                                                │
│  ├── Sparkline.jsx          ← price chart + OTEO ring               │
│  ├── TopBar.jsx             ← ops control + status badges           │
│  └── Trade buttons          ← CALL / PUT execution                  │
└─────────────────────────────────────────────────────────────────────┘
                               │  WebSocket (:8001/ws)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              FastAPI Backend  (main.py :8001)                       │
│  /api/connect   /api/assets   /api/trade   /api/state               │
└─────────────────────────────────────────────────────────────────────┘
```

### Two Separate Concerns

| Layer | Purpose | Port |
|-------|---------|------|
| **Redis Streaming Gateway** | High-frequency tick delivery via Socket.IO | 3001 |
| **FastAPI Backend** | Account management, trade execution, asset lists | 8001 |

These are intentionally separate. The streaming gateway handles thousands of ticks per minute without blocking the trading API.

---

## Startup Workflow

### Quick Start (using batch files)

```bat
REM 1. Start everything at once
start_app.bat

REM Or start individually:
run_backend.bat    REM Starts FastAPI backend on :8001
run_frontend.bat   REM Starts Vite dev server on :5175
```

### Manual Start (full control)

```powershell
# 1. Activate conda environment
conda activate QuFLX-v2

# 2. Start Redis (if not already running)
redis-server

# 3. Start the Redis Streaming Gateway
cd ssid/web_app/backend
uvicorn data_streaming.redis_gateway:socket_app --host 0.0.0.0 --port 3001

# 4. Start the FastAPI Backend
uvicorn main:app --host 0.0.0.0 --port 8001

# 5. Start the Frontend
cd ssid/web_app/frontend
npm run dev
```

### In-App Startup (via TopBar buttons)

Once the frontend is running, use the **TopBar** to complete the data pipeline:

```
1. Click [CHROME]  → Opens Chrome with Pocket Option + remote debugging on :9222
2. Click [STREAM]  → Starts the OTC Sniper Collector (tick interceptor)
3. Click [SSID]    → Connects to your Pocket Option demo/real account
4. Select an asset → Ticks begin flowing; OTEO warmup starts
```

> ⚠️ **Important:** The OTC Sniper Collector (`collector_main.py`) and the QuFLX v2 Collector (`backend/services/collector/main.py`) **must not run simultaneously** — both connect to Chrome DevTools on port 9222 and will conflict.

---

## The OTEO Engine & Asset Warmup System

### What is OTEO?

**OTEO** (OTC Tick Exhaustion Oscillator) is a momentum scoring engine that detects when a price move is likely to reverse. It scores 0–100:

- **Score > 75** → HIGH confidence reversion signal (cyan ring)
- **Score 55–75** → MEDIUM confidence (amber ring)
- **Score < 55** → LOW confidence / noise

The direction is always **opposite to momentum** — if price is moving up fast (positive velocity), OTEO signals **PUT** (expecting exhaustion and reversal).

### How the Score is Calculated

Each tick feeds into a three-step calculation:

```
1. VELOCITY
   velocity = (price[last] - price[last-50]) / 5.0
   → Measures price change over the last 50 ticks (~5 seconds at 1 tick/sec)
   → Normalised by dividing by 5 to approximate per-second rate

2. Z-SCORE  (statistical deviation from baseline)
   baseline = all ticks in buffer EXCEPT the most recent 20
   mu    = mean(baseline)
   sigma = std(baseline)  [floor: 0.0001 to prevent division by zero]
   z_score = (current_price - mu) / sigma
   → Measures how far the current price is from its recent "normal"
   → Excludes last 20 ticks to avoid self-reference bias

3. OTEO SCORE  (sigmoid of momentum product)
   product = |velocity| × |z_score|
   score   = 100 × (1 - 1 / (1 + e^(-3.5 × (product - 0.85))))
   → Sigmoid curve centred at product=0.85
   → High velocity + high z-score = high exhaustion probability
```

### The Warmup System

**Why warmup is needed:** OTEO requires a statistical baseline to compute a meaningful z-score. Without enough historical ticks, the baseline is too small to be reliable.

**Warmup threshold:** `≥ 50 ticks`

**During warmup (< 50 ticks):**
- `update_tick()` returns `50.0` (neutral float — no signal)
- The frontend shows an **amber warmup bar**: `OTEO Warming: X/50 ticks`
- All OTEO fields in the payload default to: `oteo_score=50.0`, `recommended=CALL`, `confidence=LOW`

**After warmup (≥ 50 ticks):**
- `update_tick()` returns a full scoring dict
- The frontend shows a **green "OTEO Ready"** indicator
- The OTEO ring begins reflecting real scores

**Warmup timeline at normal tick frequency:**
```
~50 seconds  → OTEO produces first real score
~70 seconds  → Baseline has 50+ ticks, z-score is statistically meaningful
~5 minutes   → Tick buffer (maxlen=300) is fully populated
```

### Warmup Status Events

The gateway emits `warmup_status` Socket.IO events to keep the frontend in sync:

```json
{
  "asset": "EURUSD",
  "ready": false,
  "ticks_received": 23
}
```

Events are emitted:
- **Every 10 ticks** (progress updates)
- **At exactly tick 50** (ready transition)
- **On `focus_asset`** (immediate status for newly focused asset)

### Warmup Preservation on Asset Switch

When you switch to a different asset and then switch back, **OTEO warmup progress is preserved**. Only the ManipulationDetector buffers are cleared on focus switch (to prevent cross-asset contamination). The OTEO tick buffer and tick count survive the switch.

```
User selects EURUSD  → 45 ticks accumulated
User switches to AUDNZD → EURUSD OTEO preserved at 45 ticks
User switches back to EURUSD → warmup resumes from 45 (not 0)
```

### Tick Buffer Architecture

```
OTEO.ticks  deque(maxlen=300)
│
├── Last 50 ticks  → velocity calculation window
├── All except last 20 → z-score baseline
└── Full buffer → statistical stability over time
```

---

## Asset Normalization

All asset names are normalized to the canonical `EURUSDOTC` format internally. This matches the QuFLX-v2 standard. The PocketOption API format (`EURUSD_otc`) is only used at the trade execution boundary via `to_pocket_option_format()`.

**Single source of truth:** `backend/src/asset_utils.py` → `normalize_asset()`

| Raw Input | Normalized Output |
|-----------|------------------|
| `EURUSD_OTC` | `EURUSDOTC` |
| `EURUSD_otc` | `EURUSDOTC` |
| `#EURUSD` | `EURUSDOTC` |
| `EURUSD-OTC` | `EURUSDOTC` |
| `OTCQ-EURUSD` | `OTCQEURUSD` |
| `OTCO-EURUSD` | `OTCOEURUSD` |
| `OTC-EURUSD` | `OTCEURUSD` |
| `eurusd` | `EURUSD` |

**Room naming:** `market_data:EURUSDOTC`  
**Frontend comparison:** Both `data.asset` (from gateway) and `selectedAsset.id` (from API) are normalized before comparison to handle format mismatches.

---

## Manipulation Detection

The `ManipulationDetector` runs on every tick alongside OTEO and flags two common OTC manipulation patterns:

### Push & Snap
A rapid price push in one direction followed by an immediate reversal. Detected by analysing velocity spikes in the tick buffer.

### Pinning
Price held artificially close to a round number or strike price near expiry. Detected by measuring price variance over a rolling window.

**Frontend display:** When either flag is active, a red `PUSH/SNAP` or `PINNING` label flashes in the top-left corner of the Sparkline.

**Payload field:**
```json
{
  "manipulation": {
    "push_snap": true,
    "pinning": false
  }
}
```

> **Note:** ManipulationDetector buffers **are** cleared on asset focus switch (unlike OTEO) because velocity and price history from one asset would produce false positives on another.

---

## Frontend UI Guide

### TopBar (Status + Controls)

```
[ WS ● ]  [ CHROME ● ]  [ STREAM ● ]  [ SSID ● ]          [ Profile ▾ ]
```

| Badge | Meaning | Clickable? |
|-------|---------|-----------|
| **WS** | Socket.IO connection to gateway | No |
| **CHROME** | Chrome DevTools Protocol status | Yes — start/stop Chrome |
| **STREAM** | Tick collector running status | Yes — start/stop collector |
| **SSID** | Pocket Option account connection | Yes — connect/disconnect |

Status dot colours:
- 🟢 Green glow = connected / streaming
- 🟡 Amber pulse = connecting / pending
- 🔴 Red glow = error
- ⚫ Grey = disconnected

### Left Sidebar — Asset Panel

- **Search bar** — filter assets by name or ID in real time
- **Quick Select** — starred assets appear here for instant access (persisted in localStorage)
- **All Assets** — full list with payout percentage badges
- **Star icon** — click to add/remove from Quick Select
- **Refresh button** — manually refresh asset list from the API
- **Auto-refresh dropdown** — set automatic refresh interval

### Main Chart Area

```
┌─────────────────────────────────────────────────────┐
│  EURUSD/OTC                          92% PAYOUT     │
│                                                     │
│  ╭──────────────────────────────╮  ╭──────────╮    │
│  │   SVG Sparkline              │  │  OTEO    │    │
│  │   (price line + fill)        │  │  Ring    │    │
│  │   ● live dot                 │  │   75     │    │
│  ╰──────────────────────────────╯  │  CALL    │    │
│                                    ╰──────────╯    │
│  ⚡ OTEO Warming: 23/50 ticks                       │
│                                                     │
│  [ Expiration: 1m ▾ ]  [ Amount: $10 ]             │
└─────────────────────────────────────────────────────┘
```

### CALL / PUT Buttons

Large, full-height buttons on the right panel. Disabled until an asset is selected. Show loading state during trade execution.

### Trade History Table

Scrollable session history showing: Time, Asset, Direction, Amount, Result (WIN/LOSS/PENDING). Updated live via WebSocket.

---

## Ops Control (Chrome / Stream / SSID)

The Ops system allows launching and stopping the data pipeline directly from the UI. It requires the environment variable `QFLX_ENABLE_OPS=1` to be set (security gate — prevents accidental process control in production).

### Endpoints (served by Redis Gateway on :3001)

| Endpoint | Method | Action |
|----------|--------|--------|
| `/ops/chrome/start` | POST | Launch Chrome with `--remote-debugging-port=9222` |
| `/ops/chrome/stop` | POST | Kill Chrome process |
| `/ops/stream/start` | POST | Start `collector_main.py` |
| `/ops/stream/stop` | POST | Stop collector |
| `/ops/status` | GET | Return running status of all processes |

### Security

- Requires `QFLX_ENABLE_OPS=1` environment variable
- Localhost-only by default
- Optional `X-QFLX-OPS-TOKEN` header for additional auth

### Chrome Profile

Chrome is launched using the **same profile directory** as the QuFLX v2 main platform (`Chrome_profile/`), so Pocket Option sessions persist between restarts — no need to log in again.

---

## Port Reference

| Port | Service | Notes |
|------|---------|-------|
| **5175** | React Frontend (Vite) | Dev server |
| **3001** | Redis Streaming Gateway | Socket.IO + Ops endpoints |
| **8001** | FastAPI Backend | Trading API + WebSocket |
| **6379** | Redis | Shared with QuFLX v2 |
| **9222** | Chrome DevTools Protocol | **One collector at a time only** |

---

## File Structure

```
ssid/web_app/
├── README.md                          ← This document
├── .env                               ← Environment variables
├── start_app.bat                      ← Launch everything
├── run_backend.bat                    ← Backend only
├── run_frontend.bat                   ← Frontend only
│
├── backend/
│   ├── main.py                        ← FastAPI trading API (:8001)
│   ├── data_streaming/
│   │   ├── redis_gateway.py           ← Redis → Socket.IO gateway (:3001)
│   │   ├── ops.py                     ← Process control endpoints
│   │   └── streaming_server.py        ← DEPRECATED legacy server
│   └── src/
│       ├── asset_utils.py             ← normalize_asset() — single source of truth
│       ├── oteo_indicator.py          ← OTEO momentum scoring engine
│       ├── manipulation_detector.py   ← Push/Snap + Pinning detection
│       ├── collector_main.py          ← Self-contained tick collector
│       └── collector_interceptor.py   ← Chrome WS frame parser
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── TradingPlatform.jsx    ← Main app component
│       │   ├── Sparkline.jsx          ← SVG price chart + OTEO ring
│       │   ├── TopBar.jsx             ← Status badges + ops buttons
│       │   └── LoginScreen.jsx        ← SSID login screen
│       ├── hooks/
│       │   └── useOpsControl.js       ← Shared Chrome/Stream ops hook
│       └── config.js                  ← STREAM_URL, API_URL, WS_URL
│
├── .agent-memory/                     ← AI agent context files
│   ├── activeContext.md
│   ├── systemPatterns.md
│   ├── techContext.md
│   └── progress.md
│
└── Dev_Docs/                          ← Development documentation
    └── Critical_Bug_fixes_Plan_26-03-20.md
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Required for ops control (Chrome/Stream start/stop from UI)
QFLX_ENABLE_OPS=1

# Optional: ops security token (sent as X-QFLX-OPS-TOKEN header)
QFLX_OPS_TOKEN=your_secret_token

# Redis connection (defaults shown)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API URLs (frontend reads these via config.js)
VITE_STREAM_URL=http://localhost:3001
VITE_API_URL=http://localhost:8001/api
VITE_WS_URL=ws://localhost:8001/ws
```

---

## Socket.IO Event Reference

| Event | Direction | Payload |
|-------|-----------|---------|
| `market_data` | Server → Client | `{asset, price, timestamp, oteo_score, recommended, action, confidence, manipulation}` |
| `warmup_status` | Server → Client | `{asset, ready, ticks_received}` |
| `status` | Server → Client | `{status: "connected" \| "focused", asset?}` |
| `focus_asset` | Client → Server | `{asset: "EURUSD"}` — join asset room |
| `join_room` | Client → Server | `{room: "market_data:EURUSD"}` — explicit room join |

---

## Known Limitations & Planned Improvements

| Item | Status |
|------|--------|
| Manipulation flag UI overlay | Planned — currently text-only |
| OTEO history seeding from CSV | Planned — would pre-warm engines on startup |
| Signal log (scrollable history) | Planned |
| Pydantic input validation on enrichment handler | Planned |
| CORS restriction for production | TODO — currently `allow_origins=["*"]` |
| `_asset_tick_counts` cleanup for inactive assets | Known — grows unbounded in long sessions |

---

*Last updated: 2026-03-20*  
*Version: 0.1.0*  
*Stack: React 18 · Vite 6 · Tailwind CSS 3 · FastAPI 0.115 · python-socketio · NumPy 2.2 · Redis 5*
