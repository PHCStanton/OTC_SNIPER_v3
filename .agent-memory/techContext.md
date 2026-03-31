# Technical Context

## Technologies Used
- Backend: Python, FastAPI
- Real-time Streaming: Socket.IO
- Validation: Pydantic
- Frontend: React (JSX), Vite, Zustand, Tailwind CSS, lucide-react
- AI Integration: Grok 4.1 API

Current live data path:
- Pocket Option broker ticks are captured through `PocketOptionSession`
- `StreamingService` enriches and emits `market_data` / `warmup_status` events via Socket.IO
- Redis is not part of the current runtime streaming path in v3

## Development Setup
- Backend functional code runs inside `app/backend`.
- Frontend code runs inside `app/frontend`.
- Ensure Python executes via `conda activate QuFLX-v2`.
- Always run Powershell commands. Do not use `&&`. Instead use `;`.

## Dependencies
- FastAPI
- Pydantic
- Socket.IO
- PocketOption APIs and custom adapters.

## Technical Constraints
- The functional app lives strictly in `app/`. Workspace root remains for planning.
- Functional simplicity first; eliminate unnecessary complexity.
- Zero assumptions: verify everything; ask if unclear.
- Defensive & explicit error handling: never swallow errors.
- Sparkline / live chart consumer still needs to be implemented in the frontend if automatic live chart population is required.

## Coding Standards
- Strict separation of concerns (one purpose per module/file/class).
- Stop patching, start rewriting after 2-3 failed patches.
- Maintain military-grade discipline as defined in `.agentrules`.

## Testing Requirements
- Incremental testing: test after every single change.
- Verify everything before proceeding.
