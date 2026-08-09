# System Patterns — VPS Data Agent

## Architecture Overview
The Data Agent uses a **4-Layer Decoupled System Architecture**:

```
Layer 1: Ingestion & Storage
  - Pocket Option WebSocket -> PocketOptionSession (Engine.IO Handshake)
  - PocketOptionSession -> hooked_set_csv -> SSIDTickCollector
  - SSIDTickCollector -> GCPTickSink (Buffer Queue)
  - GCPTickSink -> GCP BigQuery (raw_ticks) + GCS (Parquet)
  - Fallback: Local SQLite database (ticks_fallback.db)

Layer 2: Bayesian Analytics Engine
  - BigQuery / SQLite -> BayesianPriorUpdater
  - BayesianPriorUpdater -> Atomic write to app/data/ghost_trades/stats/bayesian_priors.json
  - bayesian_priors.json -> bayesian_signal_filter.py & DataBridgeAPI

Layer 3: DaaS REST API & SSE Broadcaster
  - DataBridgeAPI -> REST endpoints (/api/v1/ticks/raw, /api/v1/ticks/filtered, /api/v1/ticks/velocity, /api/v1/assets)
  - TelemetryHTTPHandler -> Zero-latency Server-Sent Events (/api/v1/stream)

Layer 4: Hermes Autonomous Supervisor & Alerts
  - Bayesian Signals & Market Metrics -> HermesMarketTools
  - HermesMarketTools -> XAIProvider (xAI API: grok-2 / grok-beta)
  - OpenWABridge -> OpenWA Gateway -> WhatsApp Alerts
```

## Key Design Patterns

1. **Broker Session & Tick Interception (`PocketOptionSession`)**:
   - Single source of truth for Pocket Option authentication, regional connection routing, and balance verification.
   - Intercepts live ticks via monkey-patched `global_value.set_csv` on the event loop.
   - Ticker subscriptions via `session._api.change_symbol(asset, 1)`.
   - Worker thread event loop guard in `connect()` ensures compatibility with `ThreadPoolExecutor` and async tasks.

2. **Server-Sent Events (SSE) Broadcaster Pattern**:
   - Thread-safe `_broadcast_sse_event(event_type, data)` hooked into `SSIDTickCollector` callback chain.
   - Dispatches live ticks to connected clients over `GET /api/v1/stream?asset={symbol}`.
   - Emits periodic `: keepalive` comments to prevent proxy timeouts.
   - Frontend consumes stream via native browser `EventSource`.

3. **Composition Root (`vps_server.py`)**:
   - Module import defines types/functions only.
   - `load_env_file()` → `AgentSettings.from_env()` → event loop → `build_services()` → HTTP + background tasks.
   - Shared `BayesianPriorUpdater` instance injected into Hermes and `DataBridgeAPI`.

4. **Producer-Consumer Buffer & Fallback Vault**:
   - Sync `push_tick` → `BufferedTick` (ingestion_id + raw copy) under `threading.Lock`.
   - Atomic snapshot flush; failed batches restored ahead of newer ticks.
   - SQLite write via `asyncio.to_thread`; `INSERT OR IGNORE` on unique `ingestion_id`.
   - BigQuery streaming insert is attempted; if unavailable (e.g. free tier), 100% of ticks are preserved in local SQLite (`ticks_fallback.db`).

5. **Cross-process Prior Store**:
   - Shared module: `shared/bayesian_prior_store.py` (monorepo root).
   - Sidecar lock `bayesian_priors.json.lock` (msvcrt on Windows, fcntl elsewhere).
   - Transaction: lock → read → validate → mutate → temp + fsync → atomic replace.

6. **Pristine Raw Data Policy**:
   - Zero synthetic scores or fabricated metrics injected into raw data.
   - Missing context fails closed across all gates.
