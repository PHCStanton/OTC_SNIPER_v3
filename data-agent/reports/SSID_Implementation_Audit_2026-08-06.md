# SSID Implementation Audit Report

**Date:** 2026-08-06  
**Scope:** Full forensic analysis of SSID implementation vs. `SSID_Operations_Reference.md`  
**Conducted by:** @Investigator (forensic analysis) + @Reviewer (correctness audit)  
**Issue reported:** User sees no tick in UI and no data collected in BigQuery  

---

## Executive Summary

The **main OTC SNIPER app** (FastAPI backend + React frontend) SSID implementation **closely matches** the reference document. The tick streaming pipeline from SSID → WebSocket → `hooked_set_csv` → `StreamingService` → Socket.IO → UI is architecturally sound and correctly wired.

However, the **data-agent's tick collection and BigQuery ingestion pipeline is completely disconnected** from the main app's SSID flow. This is the root cause of the reported symptoms: no ticks in UI from the data-agent perspective, and no data reaching BigQuery.

---

## Part 1 — @Investigator Forensic Analysis

### 1.1 Critical Finding: Two Disconnected SSID Systems

There are **two separate and independent SSID-based systems** that never communicate:

| System | SSID Source | Tick Pipeline | Storage |
|--------|------------|---------------|---------|
| **Main App** (`app/backend/`) | User pastes in frontend → `POST /api/session/connect` | `hooked_set_csv` → `StreamingService.process_tick` → Socket.IO → UI | Local JSONL files only (`tick_logger.py`) |
| **Data Agent** (`data-agent/src/`) | `PO_SSID` env var in `data-agent/.env` | `SSIDTickCollector` → WebSocket → `GCPTickSink.push_tick` → SQLite → BigQuery | SQLite + BigQuery (when GCP creds work) |

> **⚠️ ROOT CAUSE:** The data-agent's `SSIDTickCollector` opens its **own independent WebSocket** to Pocket Option using the `PO_SSID` from `data-agent/.env`. It does NOT hook into the main app's `PocketOptionSession` or `StreamingService`. The main app has zero references to `GCPTickSink`, `SSIDTickCollector`, or BigQuery anywhere in `app/backend/`.

### 1.2 Evidence — No Cross-System Integration

| Search | Result |
|--------|--------|
| `grep "SSIDTickCollector" app/` | **0 matches** |
| `grep "GCPTickSink" app/` | **0 matches** |
| `grep "BigQuery" app/backend/` | **0 matches** |
| `grep "data-agent" app/backend/*.py` | **0 matches** |
| `grep "process_tick" data-agent/` | **0 matches** |

### 1.3 Why No Tick in the UI (Data Agent Context)

The data-agent **does not emit to the UI at all**. It has its own VPS HTTP telemetry server on port 8090 (`vps_server.py`) which serves metrics via `/api/status`, but:

- It has **no Socket.IO server** and no `sio.emit("market_data", ...)` anywhere
- It does not connect to the main app's Socket.IO
- The ticks it collects go to `GCPTickSink.push_tick()` → SQLite → (optionally) BigQuery streaming insert
- The UI only receives ticks from the **main app's** `StreamingService` via Socket.IO

### 1.4 Why No Data in BigQuery

Three independent failure points:

| # | Issue | Severity | Evidence |
|---|-------|----------|----------|
| **BQ-1** | GCP credentials path is relative and may not resolve | CRITICAL | `.env` line 3: `GOOGLE_APPLICATION_CREDENTIALS=data-agent/configs/otc-sniper-prod-e0f838b011f8.json` — if the CWD doesn't match the project root, this path fails silently |
| **BQ-2** | `GCPTickSink._init_gcp_clients()` swallows auth errors | HIGH | `gcp_sink.py` L172-174: Falls back to "Local-Fallback Mode" on any exception — no explicit error surfaced to the user |
| **BQ-3** | Collector may not be running | HIGH | `vps_server.py` L561-562: `SSIDTickCollector.start()` only runs if `PO_SSID != "demo_ssid_placeholder"`, but if `vps_server.py` is not running as a separate process, none of this executes |
| **BQ-4** | `PO_SSID` in data-agent `.env` shows `isDemo: 0` (REAL account) | WARNING | The SSID in data-agent `.env` is for a REAL account, not demo. If this is a different SSID than what the user connected with in the main app, ticks would come from a different session |

### 1.5 The `warmup_status` Event — Doc vs. Code Mismatch

| Ref Doc Claim | Actual Code | Status |
|---------------|-------------|--------|
| Payload includes `ticks_needed` field | `streaming.py` L558-563: Emits `{asset, ready, ticks_received}` — **missing `ticks_needed`** | MISMATCH |

The reference doc (Section 7.1) says the payload is `{asset, ready, ticks_received, ticks_needed}`, but `streaming.py` L558-563 only sends `{asset, ready, ticks_received}`. The `ticks_needed` field is absent.

---

## Part 2 — @Reviewer Correctness Audit

### 2.1 Reference Doc vs. Main App Codebase — Section-by-Section

#### Section 2: SSID Lifecycle ✅

| Claim | Code Location | Status |
|-------|---------------|--------|
| `POST /api/session/connect` accepts `{ ssid: "42[...]" }` | `session.py` L144-227 | ✅ Confirmed |
| `PocketOptionSession(ssid)` parses + validates once | `pocket_option_session.py` L95-106 | ✅ Confirmed |
| `session.connect()` resets globals, authenticates via WS | `pocket_option_session.py` L150-208 | ✅ Confirmed |
| `set_tick_callback(streaming_service.process_tick)` | `main.py` L82 + `session.py` L205 | ✅ Confirmed |
| `set_main_loop(asyncio.get_running_loop())` | `main.py` L219 | ✅ Confirmed |
| `_apply_hooks()` monkey-patches `gv.set_csv` | `pocket_option_session.py` L44-93 | ✅ Confirmed |
| `streaming_service.start()` enables tick processing | `session.py` L206 | ✅ Confirmed |

#### Section 3: Core Components ✅

| Claim | Code Location | Status |
|-------|---------------|--------|
| Backend `PocketOptionSession` has `set_tick_callback`, `clear_tick_callback`, `set_main_loop` | `pocket_option_session.py` L26-41 | ✅ Confirmed |
| `hooked_set_csv` uses `asyncio.run_coroutine_threadsafe` with `_main_loop` | `pocket_option_session.py` L72-74 | ✅ Confirmed |
| Future error callback on tick dispatch | `pocket_option_session.py` L76-80 | ✅ Confirmed |
| `SSIDConnector` delegates to `PocketOptionSession`, `demo` param ignored | `ssid_connector.py` L15-18 | ✅ Confirmed |

#### Section 4: SSID Validation ✅

| Validation Rule | Code Location | Status |
|----------------|---------------|--------|
| Non-empty string check | `pocket_option_session.py` L96-97 | ✅ Confirmed |
| Must start with `42[` | `pocket_option_session.py` L110-111 | ✅ Confirmed |
| JSON parse after `42` | `pocket_option_session.py` L113-116 | ✅ Confirmed |
| Array with >= 2 elements | `pocket_option_session.py` L118-119 | ✅ Confirmed |
| First element must be `"auth"` | `pocket_option_session.py` L120-121 | ✅ Confirmed |
| Must contain `session` and `isDemo` | `pocket_option_session.py` L127-129 | ✅ Confirmed |

#### Section 5: Tick Streaming Pipeline ✅

| Claim | Code Location | Status |
|-------|---------------|--------|
| `StreamingService` has `_allowed_assets` and `_streaming_active` | `streaming.py` L61-62 | ✅ Confirmed |
| `process_tick` checks `_streaming_active` and `_allowed_assets` gates | `streaming.py` L376-379 | ✅ Confirmed |
| Bounded queue (500) with drop policy | `streaming.py` L68 + L386-391 | ✅ Confirmed |
| `PerformanceMonitor` integrated | `streaming.py` L67 | ✅ Confirmed |
| `AutoGhostService` wired into `StreamingService` | `streaming.py` L48 | ✅ Confirmed |
| OTEO, ManipulationDetector, TickLogger in pipeline | `streaming.py` L430-432 + L567-572 | ✅ Confirmed |

#### Section 6: Asset Allowlist & Payout Gating ✅

| Claim | Code Location | Status |
|-------|---------------|--------|
| `update_allowed_assets()` cleans up engines for removed assets | `streaming.py` L225-244 | ✅ Confirmed |
| Gate in `_process_tick_inner()` | `streaming.py` L424 | ✅ Confirmed |
| Frontend sync: union of selected + multi-chart | `useStreamConnection.js` L201-219 | ✅ Confirmed |
| AutoGhost payout gate with resolve | `streaming.py` L338-369 | ✅ Confirmed |

#### Section 7: Socket.IO Events ✅/⚠️

| Event | Doc Claim | Actual | Status |
|-------|-----------|--------|--------|
| `market_data` room | `market_data:{asset}` | `streaming.py` L546-548 | ✅ Match |
| `warmup_status` payload | `{asset, ready, ticks_received, ticks_needed}` | `{asset, ready, ticks_received}` — **`ticks_needed` missing** | ⚠️ Mismatch |
| `focus_asset` handler | Joins room + subscribes | `main.py` L100-122 | ✅ Match |
| `watch_assets` handler | Multi-room management | `main.py` L126-160 | ✅ Match |
| `update_allowed_assets` handler | Backend allowlist update | `main.py` L164-169 | ✅ Match |
| `check_status` handler | Chrome + session state | `main.py` L173-208 | ✅ Match |

#### Section 10: Global State — `reset_all()` ⚠️

| Claim | Actual | Status |
|-------|--------|--------|
| `disconnect()` calls `reset_all()` | `pocket_option_session.py` L224-231: Manually resets individual globals with comments "reset_all() not available in this API version" | ⚠️ Partial Match |
| `connect()` calls `reset_all()` | `pocket_option_session.py` L163-170: Same manual approach | ⚠️ Partial Match |

The doc says `reset_all()` is called, but the code manually resets individual fields because `reset_all()` is unavailable in this API version. The functional outcome is equivalent, but the mechanism differs.

---

## Part 3 — Discrepancies & Issues Summary

### 3.1 Critical Issues (Causing Reported Symptoms)

| # | Issue | Severity | Detail | Recommendation |
|---|-------|----------|--------|----------------|
| **C-1** | Data-agent and main app are fully disconnected systems | CRITICAL | `SSIDTickCollector` in `data-agent/` opens its own WebSocket to PO. It is not wired into `app/backend/`'s `StreamingService`. No ticks flow from the main app to BigQuery. | @Architect: Design bridge between `StreamingService` and `GCPTickSink`, or integrate `GCPTickSink` as a callback in `StreamingService._process_tick_inner()` |
| **C-2** | `vps_server.py` may not be running | CRITICAL | The data-agent is a separate process started via `python data-agent/start.py` or `data-agent/src/vps_server.py`. If it's not running, no ticks are collected or sent to BigQuery regardless of SSID validity. | Verify the data-agent process is running: `GET http://localhost:8090/api/health/live` |
| **C-3** | GCP credentials path may not resolve | CRITICAL | `GOOGLE_APPLICATION_CREDENTIALS=data-agent/configs/...` is relative. If `vps_server.py` is started from a different CWD, BigQuery client init fails silently and falls back to local SQLite. | Use absolute path or resolve dynamically in code |

### 3.2 Medium Issues (Documentation Accuracy)

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| **M-1** | `warmup_status` missing `ticks_needed` field | MEDIUM | Doc claims `{asset, ready, ticks_received, ticks_needed}` but code emits only `{asset, ready, ticks_received}` |
| **M-2** | `reset_all()` documented but not used | MEDIUM | Code uses manual per-field resets with comment "reset_all() not available in this API version" |
| **M-3** | Two `PocketOptionSession` classes share the same name | INFO | Package-layer `session.py` and backend-layer `pocket_option_session.py` — architecturally intentional but confusing |

### 3.3 Low Issues (Cosmetic / Maintenance)

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| **L-1** | `data-agent/.env` contains REAL account SSID (`isDemo: 0`) | INFO | Potential security concern — real credentials in plaintext `.env` |
| **L-2** | Data-agent `SSIDTickCollector._handle_message` event name matching | INFO | Handles `tick`, `quote`, `updateStream`, `updateTick`, `loadHistory` — this list may need updates if the broker changes event names |

---

## Part 4 — Root Cause Diagnosis

### "No tick in UI"

The **main app's tick pipeline is correctly wired** and should produce ticks in the UI when:
1. SSID is connected via `/api/session/connect`
2. An asset is selected in the frontend (triggers `focus_asset` + `update_allowed_assets`)
3. The broker WebSocket starts streaming ticks
4. `hooked_set_csv` intercepts → `StreamingService.process_tick` → Socket.IO `market_data` event

**If you are not seeing ticks in the main app UI**, the likely causes are:
- SSID session not connected or expired
- No asset selected in the frontend
- Asset not in `_allowed_assets` set
- `streaming_service.start()` not called (only happens in `session.py` connect handler)

### "No data collected in BigQuery"

This is **expected behavior** given the current architecture:

1. The main app (`app/backend/`) has **zero BigQuery integration**. It writes ticks only to local JSONL files via `TickLogger`.
2. The data-agent (`data-agent/`) is the only component with BigQuery integration, but it runs as a **separate process** with its **own WebSocket connection** using a separately configured SSID.
3. Even if the data-agent is running, `GCPTickSink` will silently fall back to SQLite-only if GCP auth fails.

---

## Part 5 — Recommended Actions

### Immediate (Fix the reported issue)

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | Verify main app SSID connection is active: `GET /api/session/status` | User |
| P0 | Verify data-agent process is running: `GET http://localhost:8090/api/health/ready` | User |
| P0 | Check data-agent sink metrics: `GET http://localhost:8090/api/status` → look at `sink.has_gcp_connection` and `sink.total_flushed` | User |
| P1 | Fix GCP credentials path to absolute in `data-agent/.env` | @Coder |

### Architectural (Long-term)

| Priority | Action | Owner |
|----------|--------|-------|
| P1 | Bridge `StreamingService` to `GCPTickSink` so main app ticks flow to BigQuery without needing a separate data-agent WebSocket | @Architect |
| P2 | Update `warmup_status` payload to include `ticks_needed: 50` as documented | @Coder |
| P2 | Update reference doc Section 10 to reflect manual reset approach instead of `reset_all()` | @Coder |
| P3 | Unify SSID management so data-agent automatically inherits the main app's active session | @Architect |

---

## Part 6 — Verification Checklist

```
[ ] Main app session connected: GET /api/session/status → connected: true
[ ] Ticks appearing in UI after selecting an asset
[ ] Data-agent process running: GET http://localhost:8090/api/health/live → alive
[ ] Data-agent sink has GCP connection: GET http://localhost:8090/api/status → sink.has_gcp_connection: true
[ ] Data-agent collecting ticks: → collector.total_ticks > 0
[ ] BigQuery table receiving rows: SELECT COUNT(*) FROM otc_sniper_analytics.raw_ticks
[ ] GCP credentials file exists and is readable at the configured path
```

---

*Report compiled: 2026-08-06*  
*@Investigator — forensic read-only analysis*  
*@Reviewer — correctness audit against reference documentation*  
*Status: INVESTIGATION COMPLETE — Actionable findings delivered*
