# System Patterns

## Architecture Overview
The system is divided into a workspace root (`C:\v3\OTC_SNIPER`) for planning/docs, and a functional app root (`C:\v3\OTC_SNIPER\app`). 
The backend uses FastAPI and Socket.IO for the backend server on port 8001. The frontend uses React, Vite, Tailwind CSS, and Zustand.

## Key Design Patterns
1. **Modular Scope Design:** Distinct scopes for components (e.g. `settings` broken down into `global`, `accounts`, `brokers`).
2. **Repository Pattern:** Abstract `DataRepository` to allow swapping local JSONL (`LocalFileRepository`) to a database (Supabase) seamlessly without breaking business logic.
3. **Registry Pattern:** Used for dynamic auto-discovery of broker instances and settings schemas.
4. **Fail-Fast Validation:** Heavy use of Pydantic for validation to avoid silent failures at runtime.

## Data Flow
Frontend (React) -> API Client (REST & Socket.IO) -> Controllers (Thin Routes) -> Business Services (Trade, Risk, Settings, AI) -> Repository -> Persisted state.

Current live streaming path in v3:
- Pocket Option tick callback (`PocketOptionSession`) -> `StreamingService.process_tick()`
- `StreamingService` enriches/logs tick data and emits `market_data` / `warmup_status` over Socket.IO
- Frontend consumer for live sparklines is still pending in `app/frontend/src`

Legacy note:
- The older Redis Pub/Sub gateway exists only in `legacy_reference/backend_reuse/data_streaming/redis_gateway.py` and is not part of the current v3 runtime path.

## Significant Technical Decisions
- **JSON/JSONL as source of truth (v3):** Kept as the primary data store structure before executing the eventual Supabase migration.
- **Port Isolation:** Running the app on port 8001 to prevent conflict with QuFLX v2 on 8000.
- **AI Advisory Only:** The AI component (Grok) acts strictly as an advisory system for session analysis, signal confirmation, and risk insights. It does not execute live trades autonomously.
- **Direct tick streaming in v3:** Live market data is currently routed directly from the broker tick callback into Socket.IO, without Redis in the runtime path.
