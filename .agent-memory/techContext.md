# Technical Context

## Summary
- This file captures the working technical environment, runtime constraints, and implementation rules
- Backend stack: Python, FastAPI, Pydantic, and Socket.IO
- Frontend stack: React, Vite, Zustand, Tailwind CSS, and lucide-react
- AI integration: Grok 4.1 API

## Runtime Path
- Pocket Option broker ticks are captured through `PocketOptionSession`
- Ticks are queued and processed asynchronously by `StreamingService` to isolate the FastAPI event loop
- `StreamingService` enriches and emits `market_data` / `warmup_status` events via Socket.IO
- Redis is not part of the current runtime streaming path in v3

## Development Setup
- Backend functional code runs inside `app/backend`.
- Frontend code runs inside `app/frontend`.
- Use the `QuFLX-v2` conda environment for Python execution.
- In automated terminal execution, `conda run -n QuFLX-v2 ...` is more reliable than interactive activation.
- Always run Powershell commands. Do not use `&&`. Instead use `;`.

## Dependencies
- FastAPI
- Pydantic
- Socket.IO
- PocketOption APIs and custom adapters.
- xAI Grok API (text + native TTS /v1/tts for voice profiles; reasoning_effort support).

## Runtime Constraints
- The functional app lives strictly in `app/`. Workspace root remains for planning.
- Functional simplicity first; eliminate unnecessary complexity.
- Zero assumptions: verify everything; ask if unclear.
- Defensive & explicit error handling: never swallow errors.
- Blocking broker SDK calls must not run directly on the async request path.
- Trade execution uses REST, while sparklines and live trade results depend on Socket.IO connectivity.
- **Execution Boundary:** Manual user trades are strictly mapped to the active SSID environment (Live/Demo). Automated simulation is strictly handled by the background Auto-Ghost module.
- **Zustand Selector Hygiene:** Prohibits broad Zustand hook destructuring (`const { x, y } = useStore()`) in high-frequency rendering contexts to avoid global re-render cascades.
- **requestAnimationFrame Throttling:** Non-critical UI elements (such as historical tick arrays/sparklines) are throttled via requestAnimationFrame (10 FPS active, 2 FPS inactive) to prevent browser main-thread congestion.

## Coding Standards
- Strict separation of concerns (one purpose per module/file/class).
- Stop patching, start rewriting after 2-3 failed patches.
- Maintain military-grade discipline as defined in `.agentrules`.

## Validation Expectations
- Incremental testing: test after every single change.
- Verify everything before proceeding.
- Run backend compilation checks and frontend production builds (`npm run build`) before signing off.

## Recent AI & Analysis Capabilities (2026-06-13+)
- **Grok Native TTS:** Full /v1/tts integration with voice profiles (provider: grok/browser, voiceId, speed, language, custom voices). Proxy endpoint /api/ai/speak. Chained with voice-over script gen. Client playback switches based on active profile.
- **Results & Analysis Panel Filters:** 5 optimal z-score cutoffs (0.3/0.5/0.8/1.2/2.0) + per-regime win rates exposed in filter bar as toggleable chips/presets. Per-session "regimes" + "avg_z_score" enrichment. Client filtering of session list; server-side filtering of AI trade summaries. AI prompts now include the optimal data + active filters and are instructed to recommend specific z/regime combos as Ghost Controller execution gates.
- **Profile Extensibility:** ai_config + frontend profiles drive model (reasoning_effort), voice (TTS), and (future) filter defaults per feature (confirmation, review, analysis, voiceover).
- **AI-Adaptive Context:** Recent N-trade windows (via condition_stats, entry_context with z/regime/manip) + KB patterns enable AI to suggest "smart average" gate values (calibration phase before live execution). Advisory/confirmation modes preserved.
