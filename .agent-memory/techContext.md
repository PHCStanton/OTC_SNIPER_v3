# Technical Context

## Summary
- This file captures the working technical environment, runtime constraints, and implementation rules
- Backend stack: Python, FastAPI, Pydantic, and Socket.IO
- Frontend stack: React, Vite, Zustand, Tailwind CSS, and lucide-react
- AI integration: Grok 4.1 API

## Runtime Path
- Pocket Option broker ticks are captured through `PocketOptionSession`
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

## Runtime Constraints
- The functional app lives strictly in `app/`. Workspace root remains for planning.
- Functional simplicity first; eliminate unnecessary complexity.
- Zero assumptions: verify everything; ask if unclear.
- Defensive & explicit error handling: never swallow errors.
- Blocking broker SDK calls must not run directly on the async request path.
- Trade execution uses REST, while sparklines and live trade results depend on Socket.IO connectivity.
- **Execution Boundary:** Manual user trades are strictly mapped to the active SSID environment (Live/Demo). Automated simulation is strictly handled by the background Auto-Ghost module.
- Sparkline and live result paths should be revalidated after the latest Socket.IO client change.

## Coding Standards
- Strict separation of concerns (one purpose per module/file/class).
- Stop patching, start rewriting after 2-3 failed patches.
- Maintain military-grade discipline as defined in `.agentrules`.

## Validation Expectations
- Incremental testing: test after every single change.
- Verify everything before proceeding.
