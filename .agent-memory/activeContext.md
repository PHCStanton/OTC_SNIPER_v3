# Active Context

## Current Work
**Phase 0 (Ops Layer: Chrome Lifecycle + Manual SSID Input) — COMPLETE**

All Phase 0 deliverables implemented and wired into the backend.

## Phase 0 Deliverables — Done

| File | Status | Notes |
|------|--------|-------|
| `app/backend/config.py` | ✅ Updated | Added `chrome_profile_dir`, `chrome_url`, `chrome_executable` fields |
| `app/backend/api/ops.py` | ✅ Created | Chrome start/stop/status + combined /api/ops/status endpoint |
| `app/backend/api/session.py` | ✅ Created | SSID connect/disconnect/status/ssid-status with .env persistence + auto-reconnect |
| `app/backend/main.py` | ✅ Rewritten | ops + session routers registered; check_status Socket.IO event added; duplicate inline session routes removed |
| `netstat_chrome_session.bat` | ✅ Deleted | Cross-project v2 dependency eliminated |

## Key Design Decisions Made

- **Chrome spawn flags**: `--disable-web-security` and `--allow-running-insecure-content` are NOT included by default. Opt-in via `CHROME_INSECURE_MODE=1` in `.env` only.
- **Chrome profile dir**: Lives at `C:\v3\OTC_SNIPER\Chrome_profile\` (one level above `app/`) so it persists across app rebuilds.
- **SSID persistence**: After a successful connect, SSID is written to `.env` AND `os.environ` is refreshed immediately (fixes v2 stale-state bug).
- **Auto-reconnect**: `POST /api/session/connect` with empty `ssid` field falls back to saved `.env` value for the requested account type.
- **Status separation**: `chrome.running` (port probe) and `session.connected` (authenticated WS) are always reported as separate fields — they are distinct states.
- **Session manager**: `get_session_manager()` from `dependencies.py` is the single singleton used by both `session.py` router and `check_status` Socket.IO event.

## API Surface Added (Phase 0)

### HTTP Endpoints
```
POST /api/ops/chrome/start      → Spawn Chrome with remote debugging (idempotent)
POST /api/ops/chrome/stop       → Terminate managed Chrome process
GET  /api/ops/chrome/status     → Live port probe (never stale)
GET  /api/ops/status            → Combined Chrome + session status (TopBar badge source)

POST /api/session/connect       → Connect with SSID or auto-reconnect from .env
POST /api/session/disconnect    → Disconnect active session
GET  /api/session/status        → Current session state
GET  /api/session/ssid-status   → Reports has_demo_ssid / has_real_ssid (no values exposed)
```

### Socket.IO Events
```
emit: check_status              → Triggers status_update response
recv: status_update             → { chrome: {...}, session: {...}, observed_at }
```

## Security Model
- All `/api/ops/*` endpoints require `QFLX_ENABLE_OPS=1` in `.env`
- All `/api/ops/*` endpoints are localhost-only (127.0.0.1 / ::1)
- Optional `X-QFLX-OPS-TOKEN` header for extra protection
- Chrome insecure flags are opt-in only via `CHROME_INSECURE_MODE=1`

## Recent Changes
- Ported OTEO and Manipulation Detection algorithms (Phase 3).
- Implemented `StreamingService` for real-time data orchestration (Phase 3).
- Integrated `python-socketio` into `main.py` ASGI app (Phase 3).
- Monkey-patched `pocketoptionapi.global_value.set_csv` to hook live ticks (Phase 3).
- Added `TickLogger` and `SignalLogger` for JSONL persistence (Phase 3).
- **Phase 0 complete**: Chrome lifecycle management + manual SSID input ops layer.

## Next Steps
1. **@Reviewer** — Phase 0 incremental review (per PHASE_REVIEW_PROTOCOL.md).
2. After review sign-off: proceed with **Phase 1** (Backend Foundation).
   - Rebuild broker adapter around `PocketOptionSession` directly.
   - Add repository abstraction for local storage.
   - Verify real connection through new session layer.
3. **Phase 4** (Frontend Shell) — TopBar with Chrome + SSID badges using `useOpsStore.js`.

## Blockers
None. Phase 0 is complete and awaiting @Reviewer sign-off before Phase 1 begins.

## Environment Notes
- App server: `OTC_PORT=8001` (separate from QuFLX-v2 gateway on 8000)
- Chrome debug port: `CHROME_PORT=9222`
- Ops enabled: `QFLX_ENABLE_OPS=1`
- Start command: `cd C:\v3\OTC_SNIPER\app && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload`
