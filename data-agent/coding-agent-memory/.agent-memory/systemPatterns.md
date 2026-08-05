# System Patterns — VPS Data Agent

## Architecture Overview
The Data Agent uses a **4-Layer Decoupled System Architecture**:

```
Layer 1: Ingestion & Storage
  - Pocket Option WebSocket -> SSIDTickCollector
  - SSIDTickCollector -> GCPTickSink (Buffer Queue)
  - GCPTickSink -> GCP BigQuery (raw_ticks) + GCS (Parquet)
  - Fallback: Local SQLite database (ticks_fallback.db)

Layer 2: Bayesian Analytics Engine
  - BigQuery / SQLite -> BayesianPriorUpdater
  - BayesianPriorUpdater -> Atomic write to app/data/ghost_trades/stats/bayesian_priors.json
  - bayesian_priors.json -> bayesian_signal_filter.py

Layer 3: Hermes Autonomous Supervisor
  - Bayesian Signals & Market Metrics -> HermesMarketTools
  - HermesMarketTools -> XAIProvider (xAI API: grok-2 / grok-beta)
  - XAIProvider Reasoning -> Formatted Trade Signal Cards

Layer 4: WhatsApp Communication Gateway
  - Trade Signal Cards -> OpenWABridge
  - OpenWABridge -> OpenWA NestJS Server -> WhatsApp Client
```

## Key Design Patterns
1. **Composition Root (`vps_server.py`)**:
   - Module import defines types/functions only.
   - `load_env_file()` → `AgentSettings.from_env()` → event loop → `build_services()` → HTTP + tasks.
   - Shared `BayesianPriorUpdater` instance injected into Hermes and `DataBridgeAPI`.

2. **Thread-safe subscription gateway**:
   - HTTP runs on a worker thread; collector `add_asset` is async on the owner loop.
   - Use `asyncio.run_coroutine_threadsafe(...).result(timeout=...)` — never mutate `collector.assets` from HTTP alone for live wire subscribe.

3. **Producer-Consumer Buffer Pattern (Phase 2)**:
   - Sync `push_tick` → `BufferedTick` (ingestion_id + raw copy) under `threading.Lock`.
   - Flush takes atomic snapshot swap; restore failed batch ahead of newer ticks.
   - Async `_flush_mutex` serializes flushes; does not protect ingress.
   - SQLite write via `asyncio.to_thread`; `INSERT OR IGNORE` on unique `ingestion_id`.
   - `total_flushed` advances only after local commit; BQ is best-effort after that.

4. **Resilient Local Fallback Pattern**:
   - SQLite is the local durability boundary; BQ failure leaves rows for later sync.

5. **Cross-process Prior Store (Phase 4)**:
   - Shared module: `shared/bayesian_prior_store.py` (monorepo root; no app↔data-agent service coupling).
   - Sidecar lock `bayesian_priors.json.lock` (msvcrt on Windows, fcntl elsewhere).
   - Transaction: lock → read → validate → mutate → temp + fsync → atomic replace (with Windows share-violation retry).
   - Writers: `BayesianPriorUpdater` and `BayesianSignalFilter.on_trade_outcome` delegate fully; memory refreshed only from committed result.
   - Corrupt on-disk data raises; never silently overwritten with empty priors.

6. **Provider / Bridge Adapters**:
   - `XAIProvider` offline fallback; `OpenWABridge` optional messaging via `OPENWA_API_URL`.

## Boundary Decisions (remediation)
- SQLite is the local durability boundary.
- Market context is a dependency, not a fabricated dict (Phase 3):
  - `TickFieldContextProvider` uses only valid tick fields; no hardcoded scores.
  - Requested gates fail closed on missing/invalid context (`*_context_unavailable`).
  - Unknown gate names → client error (`unknown_gates`).
  - Manipulation severity is authoritative; `has_manipulation` is metadata only.
  - `POST /trades/record` validates `asset` + strict JSON boolean `won`; `recorded:true` only after updater commit.
- OpenWA is optional; data-agent health does not depend on OpenWA (Phase 5).
