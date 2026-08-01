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
1. **Producer-Consumer Buffer Pattern**:
   - `SSIDTickCollector` produces raw ticks to a thread-safe callback queue.
   - `GCPTickSink` consumes ticks in micro-batches every 5 seconds, minimizing HTTP overhead.

2. **Resilient Local Fallback Pattern**:
   - If GCP connectivity or credentials are missing/offline, `GCPTickSink` automatically flushes ticks to local SQLite (`ticks_fallback.db`) with zero data loss.

3. **Atomic File Update Pattern**:
   - `BayesianPriorUpdater` writes JSON output to a temporary file in the target directory and renames it atomically to prevent corruption during concurrent reads by `bayesian_signal_filter.py`.

4. **Provider Adapter Pattern**:
   - `XAIProvider` encapsulates xAI API communications (`https://api.x.ai/v1`), supporting graceful fallback to offline evaluation mode when no API key is provided.

5. **Bridge Adapter Pattern**:
   - `OpenWABridge` provides a clean interface over the OpenWA NestJS REST API, supporting mock logging when no recipient phone number is set.
