# 🛠️ Data Agent DaaS — Phased Fix & Improvement Plan

**Generated:** 2026-08-03
**Source:** End-to-End Architectural Diagnostic (`diagnostic_report.md`)
**Scope:** `data-agent/` DaaS microservice and its Bayesian/streaming integration with `OTC_SNIPER`
**Constraint:** All changes must be surgically precise — no breaking changes to the 4-layer architecture.

---

## Table of Contents

1. [Phase 1 — Critical Fixes](#phase-1--critical-fixes)
2. [Phase 2 — High-Severity Fixes](#phase-2--high-severity-fixes)
3. [Phase 3 — Medium-Severity Fixes](#phase-3--medium-severity-fixes)
4. [Phase 4 — Low-Severity & Hardening](#phase-4--low-severity--hardening)
5. [Test Strategy](#test-strategy)
6. [Acceptance Checklist](#acceptance-checklist)

---

## Phase 1 — Critical Fixes

> **Target:** Resolve all data-loss, silent-failure, and broken-feedback-loop issues before any VPS deployment.
> **Files affected:** `gcp_sink.py`, `api_bridge.py`

---

### Task 1.1 — Fix Thread-Safe Tick Buffer in `GCPTickSink`

**Finding:** F1 — Race condition between synchronous `push_tick()` and async `flush()`
**File:** `data-agent/src/tick_collector/gcp_sink.py`
**Lines:** L58–L60, L106–L108, L150–L157

**Root Cause:**
`push_tick()` appends to a plain `list` without acquiring any lock. `flush()` uses an `asyncio.Lock`, which is not reentrant and provides no protection against the synchronous `push_tick()` path. The `list.clear()` call inside `flush()` can race with an in-flight `push_tick()`, silently dropping ticks.

**Required Change:**

Replace the plain `list` buffer and `asyncio.Lock` with an `asyncio.Queue`, which is natively coroutine-safe. The `push_tick()` method can use `queue.put_nowait()` (non-blocking, safe to call from a synchronous callback), and `flush()` drains via `queue.get_nowait()` in a tight loop.

```
BEFORE:
  self._buffer: List[Dict] = []
  self._lock = asyncio.Lock()
  def push_tick(tick): self._buffer.append(tick)  <- unprotected

AFTER:
  self._queue: asyncio.Queue = asyncio.Queue()
  def push_tick(tick): self._queue.put_nowait(tick)  <- safe from sync callback
  async def flush(): drain queue via get_nowait() loop
```

**Acceptance Criteria:**
- [ ] `push_tick()` never acquires or blocks on a lock.
- [ ] `flush()` drains only ticks that were enqueued before the drain started.
- [ ] No `asyncio.Lock` remains on the hot-path buffer.
- [ ] Unit test: concurrent `push_tick()` calls + flush yield exactly N ticks persisted, zero dropped.

---

### Task 1.2 — Replace Hardcoded Mock Market Context in Filter Pipeline

**Finding:** F2 — Static `market_ctx` dict makes `/api/v1/ticks/filtered` decorative
**File:** `data-agent/src/api_bridge.py`
**Lines:** L74–L84

**Root Cause:**
`get_filtered_ticks()` constructs a hardcoded market context dict (volatility=45, liquidity=55, posterior=0.92, etc.) instead of deriving it from actual tick data or a live context source. All ticks always pass all gates regardless of market conditions.

**Required Change:**

Two-step fix:

**Step A** — Remove the hardcoded dict. Instead, extract market context from each tick's own fields if available, falling back to computed aggregate stats from the local SQLite database (e.g., recent price variance as a volatility proxy).

**Step B** — Wire `get_market_context()` as the default context provider. This method already returns `volatility_score`, `liquidity_score`, `has_manipulation`, and `manipulation_severity` — even if they are currently stub values, they must at minimum be the same stubs being used instead of a hardcoded dict per-tick.

```
BEFORE (per tick):
  market_ctx = {"volatility_score": 45.0, "liquidity_score": 55.0, ...}  <- always same

AFTER:
  market_ctx = self._build_market_context(t, asset)   <- derives from tick + asset
  # _build_market_context() uses tick fields first, then calls get_market_context()
  # as a baseline, and marks context as "computed" vs "live"
```

**Acceptance Criteria:**
- [ ] No hardcoded numeric constant for `volatility_score`, `liquidity_score`, or `bayesian_posterior_prob` in `get_filtered_ticks()`.
- [ ] Market context varies per tick or per asset request, not globally.
- [ ] Filter veto decisions observable in the UI when market conditions are clearly out of bounds.
- [ ] Integration test: inject a tick with `volatility_score=95` (above `max_volatility=85`), verify it receives a `VOLATILITY_VETO`.

---

### Task 1.3 — Wire `BayesianPriorUpdater` into Trade Outcome Recorder

**Finding:** F3 — `record_trade_outcome()` is a no-op
**File:** `data-agent/src/api_bridge.py`
**Lines:** L23–L26, L130–L135

**Root Cause:**
`DataBridgeAPI.__init__()` instantiates `FilterPipelineManager` but has no reference to `BayesianPriorUpdater`. The `record_trade_outcome()` method logs only and discards the trade data.

**Required Change:**

1. Add `BayesianPriorUpdater` as an injected dependency in `DataBridgeAPI.__init__()`.
2. In `record_trade_outcome()`, convert the incoming `trade_data` payload to the `update_priors_from_trades()` expected format and call it.
3. Inject the updater from `vps_server.py` where both `updater` and `bridge_api` are instantiated.

```python
# api_bridge.py __init__ signature:
def __init__(self, ..., priors_updater=None):
    self.priors_updater = priors_updater or BayesianPriorUpdater()

# record_trade_outcome():
if self.priors_updater:
    self.priors_updater.update_priors_from_trades([{
        "won": trade_data.get("won", False),
        "features": trade_data.get("features", [])
    }])
```

```python
# vps_server.py:
bridge_api = DataBridgeAPI(priors_updater=updater)  # inject shared instance
```

**Acceptance Criteria:**
- [ ] `POST /api/v1/trades/record` with `{"asset": "EURUSD_otc", "won": true, "features": ["oteo_band=85-92"]}` results in an incremented `total_wins` count in `bayesian_priors.json`.
- [ ] The same `BayesianPriorUpdater` instance is shared between `HermesMarketTools` and `DataBridgeAPI`.
- [ ] Unit test: call `record_trade_outcome()` 5x WIN, verify `total_wins` increases by 5 in the priors file.

---

## Phase 2 — High-Severity Fixes

> **Target:** Resolve environment misconfigurations and inter-process file race conditions before VPS deployment.
> **Files affected:** `.env`, `docker-compose.vps.yml`, `prior_updater.py`, `bayesian_signal_filter.py`

---

### Task 2.1 — Fix OpenWA Env Var Name Mismatch

**Finding:** F4
**Files:** `data-agent/.env`, `data-agent/src/whatsapp/openwa_bridge.py`, `data-agent/docker-compose.vps.yml`

**Root Cause:**
`.env` defines `OPENWA_SERVER_URL` but `OpenWABridge` reads `OPENWA_API_URL`. The bridge defaults to `http://localhost:8080` in local dev, ignoring the `.env` value entirely.

**Required Changes:**

Option A _(preferred — minimal surface change)_: Rename the key in `.env` and `.env.example` from `OPENWA_SERVER_URL` to `OPENWA_API_URL` to match the code.

Option B _(fallback)_: Add a secondary `os.getenv("OPENWA_SERVER_URL")` check inside `OpenWABridge.__init__()` to preserve backward compatibility.

**Acceptance Criteria:**
- [ ] Local dev: `python data-agent/src/vps_server.py` reads the correct OpenWA URL from `.env`.
- [ ] Docker: `docker-compose.vps.yml` `OPENWA_API_URL` still overrides for containerized deployment.
- [ ] `openwa_bridge.py` reads from a single, documented env var name.
- [ ] `.env.example` and `.env` both use the same, consistent variable name.

---

### Task 2.2 — Add `TARGET_ASSETS` to Active `.env`

**Finding:** F5
**Files:** `data-agent/.env`, `data-agent/src/vps_server.py` (L55–L57)

**Root Cause:**
`.env` does not contain a `TARGET_ASSETS` entry. `vps_server.py` reads `TARGET_ASSETS` at module-level (before `.env` is loaded — see F9). The `SSIDTickCollector` silently falls back to 3 hardcoded assets instead of the intended 8.

**Required Changes:**

1. Add the `TARGET_ASSETS` line to `data-agent/.env`:
   ```
   TARGET_ASSETS=EURUSD_otc,GBPUSD_otc,USDJPY_otc,AUDCAD_otc,USDCHF_otc,ZARUSD_otc,NGNUSD_otc,USDARS_otc
   ```
2. Coordinate with Task 3.3 (move env load before construction) so `TARGET_ASSETS` is actually available at the time the collector is initialized.

**Acceptance Criteria:**
- [ ] All 8 production assets are subscribed at startup when `TARGET_ASSETS` is set.
- [ ] Default fallback (`EURUSD_otc`, `GBPUSD_otc`, `USDJPY_otc`) applies only when `TARGET_ASSETS` is absent.
- [ ] Integration test: set `TARGET_ASSETS=AUDCAD_otc,ZARUSD_otc`, verify collector subscribes exactly those 2.

---

### Task 2.3 — Resolve Shared `bayesian_priors.json` Cross-Process Race

**Finding:** F6
**Files:**
- `data-agent/src/bayesian/prior_updater.py` (L95–L105) — atomic write (safe)
- `app/backend/services/extensions/bayesian_signal_filter.py` (L80–L93) — non-atomic `open("w")` (unsafe)

**Root Cause:**
Both the data-agent (VPS process) and the OTC_SNIPER app share `app/data/ghost_trades/stats/bayesian_priors.json` via a Docker volume mount. `BayesianSignalFilter._save_priors()` uses a non-atomic direct write that can truncate the file mid-read by the other process.

**Required Change — Two-Part:**

**Part A** — `BayesianSignalFilter._save_priors()` (app side):
Mirror the atomic tempfile+rename pattern already used in `BayesianPriorUpdater.save_priors_atomically()`:

```python
# Replace direct open("w") with tempfile + replace:
import tempfile
with tempfile.NamedTemporaryFile("w", dir=self.priors_file.parent,
                                 delete=False, encoding="utf-8", suffix=".tmp") as tf:
    json.dump(priors_data, tf, indent=2)
    temp_name = tf.name
Path(temp_name).replace(self.priors_file)
```

**Part B** — Add a cross-process file lock:
Use `fcntl.flock` (Linux/Mac) or `msvcrt.locking` (Windows) for a cross-process advisory lock around both the read and write operations in both modules. Alternatively, wrap access in a retry-on-permission-error loop with exponential backoff (2–3 retries, 50ms intervals).

**Acceptance Criteria:**
- [ ] `BayesianSignalFilter._save_priors()` uses tempfile+replace — no direct `open("w")`.
- [ ] Both writers can be triggered simultaneously 100x in a test loop with zero JSON parse errors on concurrent reads.
- [ ] `bayesian_priors.json` is never in a truncated or partial-JSON state.

---

## Phase 3 — Medium-Severity Fixes

> **Target:** Correct logic bugs, unsafe defaults, and UI breakage.
> **Files affected:** `manipulation_filter.py`, `bayesian_filter.py`, `vps_server.py`, `App.jsx`

---

### Task 3.1 — Fix Manipulation Filter OR-Gate Logic

**Finding:** F7
**File:** `data-agent/src/filters/manipulation_filter.py` (L21–L22)

**Root Cause:**
`if has_manip or manip_severity > threshold` fires a veto when `has_manipulation=True` even if severity is 0.01, generating a misleading veto message claiming `severity > threshold` when it isn't.

**Required Change:**

Separate the two conditions into independent veto checks with distinct reason strings:

```python
reasons = []
if manip_severity > self.severity_threshold:
    reasons.append(f"manipulation_severity_exceeded ({manip_severity:.3f} > {self.severity_threshold})")
if has_manip and manip_severity > 0:
    reasons.append("manipulation_flag_active")

if reasons:
    return False, " | ".join(reasons)
return True, None
```

**Acceptance Criteria:**
- [ ] `has_manipulation=True, severity=0.01` — NO veto (severity below threshold, flag alone insufficient).
- [ ] `has_manipulation=False, severity=0.20` (>0.15) — veto with severity reason only.
- [ ] `has_manipulation=True, severity=0.20` — veto with both reasons.
- [ ] Unit tests covering all 4 boolean/severity combinations.

---

### Task 3.2 — Fix Bayesian Filter Fail-Open Default

**Finding:** F8
**File:** `data-agent/src/filters/bayesian_filter.py` (L23–L24)

**Root Cause:**
When `bayesian_posterior_prob` is missing from both `market_context` and `tick_data`, the filter defaults to `0.95` — above the `0.90` threshold — silently passing the tick. Missing data should not be treated as high confidence.

**Required Change:**

Change the default to `None` with an explicit fail-closed veto when the probability cannot be determined:

```python
if posterior_prob is None:
    return False, "bayesian_veto: posterior_probability_unavailable (missing from context)"
```

**Acceptance Criteria:**
- [ ] A tick with no `bayesian_posterior_prob` in any source field is **vetoed**, not passed.
- [ ] The veto reason clearly states the data was missing.
- [ ] Unit test: tick with no bayesian data -> filter returns `(False, "...unavailable...")`.

---

### Task 3.3 — Move `load_env_file()` Before Module-Level Construction

**Finding:** F9
**File:** `data-agent/src/vps_server.py` (L54–L60, L170–L171)

**Root Cause:**
`sink`, `collector`, and `updater` are instantiated at module-import time (L54–L60), before `load_env_file()` is called (L171). Environment variables from `.env` are not yet in `os.environ` when the globals are created.

**Required Change:**

Wrap all service construction in a `_build_services()` factory function and call `load_env_file()` as the very first statement in the `if __name__ == "__main__":` block:

```python
def _build_services():
    """Construct all agent services after env has been loaded."""
    global sink, collector, updater, tools, wa_bridge, bridge_api
    sink = GCPTickSink()
    raw_assets = os.getenv("TARGET_ASSETS")
    ...

if __name__ == "__main__":
    load_env_file()         # <- FIRST: load env
    _build_services()       # <- SECOND: construct using loaded env
    ...
```

**Acceptance Criteria:**
- [ ] `GCPTickSink` reads `GCP_PROJECT_ID` from `.env` when started via `python vps_server.py`.
- [ ] `SSIDTickCollector` uses the `PO_SSID` and `TARGET_ASSETS` values from `.env`.
- [ ] `load_env_file()` is the first executable statement in `__main__` block.
- [ ] Import of the module (not execution) does NOT trigger service construction.

---

### Task 3.4 — Fix JS `.strip()` -> `.trim()` in UI

**Finding:** F10
**File:** `data-agent/ui/src/App.jsx` (L112)

**Root Cause:**
JavaScript `String` has no `.strip()` method. Calling it throws `TypeError` at runtime, breaking the entire "Add Custom Stream" feature.

**Required Change:**

```jsx
// Before:
if (!customAssetInput.strip()) return;

// After:
if (!customAssetInput.trim()) return;
```

**Acceptance Criteria:**
- [ ] Clicking "Add" with a blank input does nothing (no crash).
- [ ] Clicking "Add" with `"  BTCUSD  "` correctly trims and subscribes `BTCUSD`.
- [ ] No `TypeError` in browser console.

---

### Task 3.5 — Fix Hardcoded Payout Badge in UI

**Finding:** F11
**File:** `data-agent/ui/src/App.jsx` (L290–L292)

**Root Cause:**
The selected-asset payout badge always renders `92% Payout` regardless of the asset's actual payout value from `assetCatalog`.

**Required Change:**

Look up the selected asset's payout dynamically:

```jsx
const selectedAssetData = assetCatalog.find((a) => a.symbol === selectedAsset);
const displayPayout = selectedAssetData?.payout ?? '—';

// In JSX:
<span ...>{displayPayout}% Payout</span>
```

**Acceptance Criteria:**
- [ ] Selecting `BTCUSD` shows `85% Payout`.
- [ ] Selecting `EURUSD_otc` shows `92% Payout`.
- [ ] Selecting a custom asset with no payout data shows `—% Payout`.

---

## Phase 4 — Low-Severity & Hardening

> **Target:** Performance, observability, and operational hardening.
> **Files affected:** `gcp_sink.py`, `Dockerfile.vps`, `docker-compose.vps.yml`

---

### Task 4.1 — Offload SQLite I/O from Asyncio Event Loop

**Finding:** F12
**File:** `data-agent/src/tick_collector/gcp_sink.py` (L161–L170)

**Root Cause:**
`flush()` is an `async` coroutine but calls blocking `sqlite3.connect()` + `executemany()` + `commit()` directly, stalling the event loop during every flush cycle.

**Required Change:**

Wrap the SQLite block in `asyncio.to_thread()`:

```python
async def flush(self) -> None:
    ...
    await asyncio.to_thread(self._write_batch_to_sqlite, batch)
    ...

def _write_batch_to_sqlite(self, batch: List[Dict]) -> None:
    """Blocking SQLite write — safe to run in thread pool."""
    with sqlite3.connect(self.local_db_path) as conn:
        conn.executemany("INSERT INTO ticks ...", batch)
        conn.commit()
```

**Acceptance Criteria:**
- [ ] `flush()` does not block the asyncio event loop (verifiable with event loop debug mode).
- [ ] WebSocket heartbeats continue uninterrupted during a flush.
- [ ] SQLite write throughput is unchanged or improved.

---

### Task 4.2 — Add Docker Health Check

**Finding:** F13
**Files:** `data-agent/Dockerfile.vps`, `data-agent/docker-compose.vps.yml`

**Root Cause:**
No `HEALTHCHECK` is defined. Docker cannot detect whether the agent is healthy, stalled, or in a crash-restart loop.

**Required Changes:**

**Dockerfile.vps** — add at the end:
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/api/status')" || exit 1
```

**docker-compose.vps.yml** — add `healthcheck` to `vps-data-agent`:
```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8090/api/status')\""]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 20s
```

**Acceptance Criteria:**
- [ ] `docker inspect otc_vps_data_agent` shows `"Health": "healthy"` within 60s of start.
- [ ] Killing the HTTP server inside the container causes `"Health": "unhealthy"` within 90s.
- [ ] `docker-compose.vps.yml` `depends_on: openwa-gateway` updated to `condition: service_healthy`.

---

## Test Strategy

### Phase 1 Tests (Critical)

| Test ID | Type | What it Tests |
|---------|------|---------------|
| `T1.1a` | Unit | 50 concurrent `push_tick()` + 1 `flush()` -> all 50 ticks in SQLite |
| `T1.1b` | Unit | Zero ticks dropped when flush drains during high-frequency push |
| `T1.2a` | Integration | `/api/v1/ticks/filtered?gates=volatility` with tick having `volatility_score=95` -> veto returned |
| `T1.2b` | Integration | `/api/v1/ticks/filtered` returns per-tick varying evaluations, not uniform PASSED |
| `T1.3a` | Unit | `POST /api/v1/trades/record` x5 WIN -> `total_wins` in priors file increases by 5 |
| `T1.3b` | Integration | Shared `BayesianPriorUpdater` instance updated by both Hermes and API bridge |

### Phase 2 Tests (High)

| Test ID | Type | What it Tests |
|---------|------|---------------|
| `T2.1a` | Env | `OPENWA_API_URL` in `.env` -> bridge uses that URL |
| `T2.2a` | Env | `TARGET_ASSETS=AUDCAD_otc` -> collector subscribes only `AUDCAD_otc` |
| `T2.3a` | Concurrent | 100x simultaneous writes to `bayesian_priors.json` -> zero parse errors |
| `T2.3b` | Unit | `BayesianSignalFilter._save_priors()` uses tempfile+replace pattern |

### Phase 3 Tests (Medium)

| Test ID | Type | What it Tests |
|---------|------|---------------|
| `T3.1a` | Unit | `has_manip=True, severity=0.01` -> NO veto |
| `T3.1b` | Unit | `has_manip=False, severity=0.20` -> veto with severity reason only |
| `T3.2a` | Unit | Tick missing `bayesian_posterior_prob` -> `(False, "...unavailable...")` |
| `T3.3a` | Process | `python vps_server.py` reads `PO_SSID` from `.env` correctly |
| `T3.4a` | Browser | Add Custom Stream with `"  BTCUSD  "` -> subscribes `BTCUSD`, no crash |
| `T3.5a` | UI | Select `BTCUSD` -> header shows `85% Payout` |

### Phase 4 Tests (Low)

| Test ID | Type | What it Tests |
|---------|------|---------------|
| `T4.1a` | Perf | Event loop debug mode: no blocking slowdown during flush |
| `T4.2a` | Docker | `docker inspect` shows `healthy` within 60s |
| `T4.2b` | Docker | Killing the HTTP handler -> `unhealthy` within 90s |

---

## Acceptance Checklist

### Phase 1 Gate
- [ ] T1.1a, T1.1b pass — zero tick loss under concurrent load
- [ ] T1.2a, T1.2b pass — filter pipeline uses real context, not mocks
- [ ] T1.3a, T1.3b pass — trade outcomes update Bayesian priors
- [ ] Existing test suite (`tests/test_vps_data_agent_full_suite.py`) still passes 3/3

### Phase 2 Gate
- [ ] T2.1a pass — OpenWA uses `.env` configured URL
- [ ] T2.2a pass — all 8 assets subscribed at startup
- [ ] T2.3a, T2.3b pass — no JSON corruption under concurrent writes

### Phase 3 Gate
- [ ] T3.1a, T3.1b, T3.2a pass — logic bugs corrected
- [ ] T3.3a pass — env loaded before service construction
- [ ] T3.4a, T3.5a pass — UI Add Stream and payout badge fixed
- [ ] No `TypeError` in browser console

### Phase 4 Gate
- [ ] T4.1a pass — event loop non-blocking during flush
- [ ] T4.2a, T4.2b pass — Docker health checks functional

### Final Deployment Readiness
- [ ] All 4 phase gates complete
- [ ] `docker-compose.vps.yml` tested locally with `docker-compose -f docker-compose.vps.yml up --build`
- [ ] `XAI_API_KEY` configured in `.env` for Hermes Grok reasoning
- [ ] `OPENWA_API_KEY` configured for authenticated WhatsApp dispatch
- [ ] GCP credentials (`GOOGLE_APPLICATION_CREDENTIALS`) verified via `gcloud auth application-default print-access-token`
- [ ] BigQuery dataset `otc_sniper_analytics` and table `raw_ticks` provisioned in `otc-sniper-prod`

---

## File Change Map

```
data-agent/
├── .env                                          [Phase 2.1, 2.2] add OPENWA_API_URL, TARGET_ASSETS
├── .env.example                                  [Phase 2.1] rename OPENWA_SERVER_URL -> OPENWA_API_URL
├── Dockerfile.vps                                [Phase 4.2] add HEALTHCHECK
├── docker-compose.vps.yml                        [Phase 4.2] add healthcheck block
├── src/
│   ├── vps_server.py                             [Phase 3.3, 1.3] lazy construction, inject updater
│   ├── api_bridge.py                             [Phase 1.2, 1.3] real context, wired updater
│   ├── tick_collector/
│   │   └── gcp_sink.py                           [Phase 1.1, 4.1] asyncio.Queue, to_thread SQLite
│   ├── bayesian/
│   │   └── prior_updater.py                      [No change — already correct]
│   ├── filters/
│   │   ├── manipulation_filter.py                [Phase 3.1] fix OR-gate logic
│   │   └── bayesian_filter.py                    [Phase 3.2] fail-closed default
│   └── whatsapp/
│       └── openwa_bridge.py                      [Phase 2.1, optional alias]
└── ui/src/
    └── App.jsx                                   [Phase 3.4, 3.5] .trim(), dynamic payout

app/backend/services/extensions/
└── bayesian_signal_filter.py                     [Phase 2.3] atomic _save_priors()
```

---

*This plan is derived from the read-only diagnostic report dated 2026-08-03 and is subject to revision as implementation uncovers additional context.*
