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
- **Asynchronous Hot-path Queueing:** Ticks are enqueued thread-safely via `loop.call_soon_threadsafe` and consumed asynchronously in a background queue worker task, isolating the event loop from high market volatility.
- **Memory-Buffered Logging:** I/O logging is offloaded from the tick processing hot-path. Ticks are buffered in memory and flushed periodically in batch cycles.
- **Modular Extension Hook Pattern:** Dynamic discovery (`ExtensionManager`) and execution (`BaseExtension`) hooks inside core pipelines (`streaming.py` and `auto_ghost.py`), allowing premium plugins to modify state or veto signals dynamically without patching core code.

## Data Flow
- Frontend → API client → thin routes → business services → repository → persisted state

## Streaming Path
- Pocket Option tick callback (`PocketOptionSession`) -> `StreamingService.enqueue_tick` (thread-safe handoff)
- `StreamingService` background consumer queue -> `_process_tick_inner` -> socket emission -> `TickLogger.write_tick` (memory buffer)
- Frontend client -> throttled store batching -> selectors -> UI components (Sparkline, OTEORing, MultiChartView)

## Legacy Note
- The older Redis Pub/Sub gateway exists only in `legacy_reference/backend_reuse/data_streaming/redis_gateway.py` and is not part of the current v3 runtime path.

## Technical Decisions
- **JSON/JSONL as source of truth (v3):** Kept as the primary data store structure before executing the eventual Supabase migration.
- **Port Isolation:** Running the app on port 8001 to prevent conflict with QuFLX v2 on 8000.
- **AI Advisory Only:** The AI component (Grok) acts strictly as an advisory system for session analysis, signal confirmation, and risk insights. It does not execute live trades autonomously. Extended for native TTS voice profiles (grok/browser + custom) and dynamic z-score/regime filters in analysis (5 optimal cutoffs with per-regime WRs). AI can propose adaptive gate values (z-score, regimes, etc.) from recent trades + KB for Ghost Controller calibration.
- **Profile-Driven Config:** Extensible profiles for model/reasoning/voice/TTS and (future) execution filters. Profile selection drives fast vs quality paths and filter application.
- **Direct tick streaming in v3:** Live market data is currently routed directly from the broker tick callback into Socket.IO, without Redis in the runtime path.
- **Direct Socket.IO dev connection:** Local frontend development may connect directly to the backend Socket.IO endpoint when the Vite proxy handshake is unreliable.
- **Explicit trade rejection feedback:** Frontend trade flows must validate broker response success and render failure state immediately.
- **Zustand Selector Hygiene:** Prohibits broad Zustand hook destructuring (e.g. `const { x, y } = useStore()`) in high-frequency rendering contexts to avoid global re-render cascades. Components must consume state through narrow selectors (e.g. `const x = useStore((s) => s.x)`).
- **requestAnimationFrame Throttling:** Non-critical UI elements (such as historical tick arrays/sparklines) are throttled via requestAnimationFrame (10 FPS active, 2 FPS inactive) to prevent browser main-thread congestion.
