# System Patterns

## Summary
- The system is divided into a workspace root (`C:\v3\OTC_SNIPER`) for planning and memory files, and a functional app root (`C:\v3\OTC_SNIPER\app`)
- The backend uses FastAPI and Socket.IO on port 8001
- The frontend uses React, Vite, Tailwind CSS, and Zustand
- This file captures enduring architecture patterns rather than session-specific troubleshooting details

## Key Design Patterns
- **Modular Scope Design:** Distinct scopes for components such as `global`, `accounts`, and `brokers`
- **Repository Pattern:** Abstract `DataRepository` allows JSONL storage to be swapped for a database later without breaking business logic
- **Registry Pattern:** Supports dynamic discovery of broker instances and settings schemas
- **Fail-Fast Validation:** Pydantic validation is used to avoid silent runtime failures
- **Async Boundary Protection:** Blocking broker calls are offloaded from the FastAPI event loop and wrapped with timeouts
- **Split Transport Model:** Trade execution flows over HTTP, while sparklines and trade result updates flow over Socket.IO
- **Auto-Ghost Simulation Pattern:** Purpose-built background execution engine for automated strategy validation. It uses the `trigger_mode` metadata in WebSocket payloads to differentiate background activity from manual user actions.

## Data Flow
- Frontend → API client → thin routes → business services → repository → persisted state

## Streaming Path
- Pocket Option tick callback (`PocketOptionSession`) -> `StreamingService.process_tick()`
- `StreamingService` enriches/logs tick data and emits `market_data` / `warmup_status` over Socket.IO
- Frontend consumer for live sparklines is still pending in `app/frontend/src`

## Legacy Note
- The older Redis Pub/Sub gateway exists only in `legacy_reference/backend_reuse/data_streaming/redis_gateway.py` and is not part of the current v3 runtime path.

## Technical Decisions
- **JSON/JSONL as source of truth (v3):** Kept as the primary data store structure before executing the eventual Supabase migration.
- **Port Isolation:** Running the app on port 8001 to prevent conflict with QuFLX v2 on 8000.
- **AI Advisory Only:** The AI component (Grok) acts strictly as an advisory system for session analysis, signal confirmation, and risk insights. It does not execute live trades autonomously.
- **Direct tick streaming in v3:** Live market data is currently routed directly from the broker tick callback into Socket.IO, without Redis in the runtime path.
- **Direct Socket.IO dev connection:** Local frontend development may connect directly to the backend Socket.IO endpoint when the Vite proxy handshake is unreliable.
- **Explicit trade rejection feedback:** Frontend trade flows must validate broker response success and render failure state immediately.
