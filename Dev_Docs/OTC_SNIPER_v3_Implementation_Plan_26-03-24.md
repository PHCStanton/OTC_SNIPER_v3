# OTC SNIPER v3 — Implementation Plan

**Date:** 2026-03-24  
**Updated:** 2026-03-28 — Phase 4 shell verified complete; Phase 5 trading UI design handoff prepared  
**Status:** Draft for clean rebuild execution  
**Workspace Root:** `C:\v3\OTC_SNIPER`  
**Functional App Root:** `C:\v3\OTC_SNIPER\app`

---

## 1. Executive Summary

This plan defines the clean rebuild path for OTC SNIPER v3 using a strict modular architecture, preserving the strongest working patterns from the current web_app and the `ssid_integration_package`, while removing brittle cross-project coupling, TUI dependencies, and monolithic UI/service code.

The rebuild is organized around a clear separation between:
- the **workspace root** (`C:\v3\OTC_SNIPER`) for planning, references, docs, and migration assets
- the **functional app root** (`C:\v3\OTC_SNIPER\app`) for all runtime backend/frontend code

The plan prioritizes:
- **Chrome session lifecycle management** as the foundation for all SSID operations (ported from QuFLX-v2)
- **manual-first SSID input** with `.env` persistence and auto-reconnect on service start
- robust SSID session management via `PocketOptionSession`
- broker abstraction via `BrokerAdapter`
- explicit data access via repository pattern
- lightweight JSX componentization
- future-ready settings and data migration paths
- advisory-only AI integration

> **Critical Design Insight (2026-03-26):** The SSID auth frame is derived from a Chrome browser session where the user is logged into Pocket Option. Without Chrome running with remote debugging on port 9222, there is no valid SSID source. This plan now includes Phase 0 to establish Chrome lifecycle management and manual SSID input before any other backend work begins. This pattern is proven in QuFLX-v2's `ops.py` + `TopBar.jsx` workflow.

---

## 2. Objectives

### Primary Goals
1. Build a reliable live-trading application for OTC execution.
2. Preserve the working data/logging strategy already proven in the existing system.
3. Eliminate legacy coupling to the TUI project and sys.path hacks.
4. Make the app modular enough to support future brokers, data stores, and UI features.
5. Maintain strict compliance with CORE_PRINCIPLES.md.

### Non-Negotiable Constraints
- No silent failures.
- No hidden fallback behavior for SSID/account type.
- No direct runtime dependency on the old TUI app.
- No breaking changes introduced without explicit approval.
- No AI-driven auto-trading.

---

## 3. Current Reference Baseline

The rebuild is based on the best proven patterns from:
- `ssid_integration_package/core/session.py` → `PocketOptionSession`
- `ssid_integration_package/core/otc_executor.py` → verified OTC trade execution pattern
- `web_app/backend/brokers/base.py` → broker abstraction model worth keeping
- `web_app/data/_db_schema.json` → local schema and future Supabase migration contract
- `web_app/frontend/src/components/MultiChartView.jsx`
- `web_app/frontend/src/components/MiniSparkline.jsx`
- `web_app/frontend/src/components/SettingsView.jsx`
- `web_app/uploads/*.tsx` → risk UI patterns to rebuild in lightweight JSX

The copied legacy references are available under:
- `C:\v3\OTC_SNIPER\legacy_reference\backend_reuse`
- `C:\v3\OTC_SNIPER\legacy_reference\frontend_reference`
- `C:\v3\OTC_SNIPER\legacy_reference\risk_components`
- `C:\v3\OTC_SNIPER\legacy_reference\data_schema`
- `C:\v3\OTC_SNIPER\legacy_reference\docs`

---

## 4. Target Architecture Summary

### Workspace Root
The workspace root contains:
- implementation plans in `Dev_Docs/`
- migration/reference assets in `legacy_reference/`
- the integration package reference
- project memory / rules / workspace metadata

### Functional App Root
The runtime application lives in `app/` and contains:
- backend code
- frontend code
- runtime data and logs
- app-specific `.env`
- app-specific startup scripts

### Application Principles
- Single authoritative SSID session manager
- Single broker adapter boundary per broker
- One canonical asset format internally
- One data access layer that can swap from local files to Supabase later
- One frontend store per domain
- Small, composable UI components

---

## 5. Architecture Rules

### 5.1 Scope Separation

#### Account Settings
Must only include account/security/session concerns:
- SSID
- broker selection
- demo/real account choice
- account-specific credentials or connection state

#### App Settings
Must only include application behavior/configuration:
- navigation and layout
- trading controls
- OTEO configuration
- ghost trading options
- risk management settings
- UI behavior and component preferences

### 5.2 Data Strategy
- Continue JSON/JSONL usage as the operational source of truth.
- Preserve `data/_db_schema.json` as the migration blueprint.
- Add a repository layer so local storage can later be replaced by Supabase without changing business logic.

### 5.3 UI Strategy
- Keep UI components small and reusable.
- Build risk visuals in JSX, not TSX, for consistency with the rebuild stack.
- Preserve `MultiChartView.jsx` and `MiniSparkline.jsx` patterns.
- Add collapsible `LeftSidebar.jsx` and `RightSidebar.jsx`.

### 5.4 AI Strategy
- AI is advisory only.
- AI may help explain patterns, summarize sessions, suggest assets, and propose risk adjustments.
- AI must never directly execute trades or override validation.

---

## 6. Proposed Project Layout

### 6.1 Workspace Root
```text
C:\v3\OTC_SNIPER\
├── Dev_Docs\
├── legacy_reference\
├── ssid_integration_package\
├── app\
├── .clinerules\
├── .agent-memory\
├── .env (optional)
└── otc_sniper_v3_rebuild_architechture.md
```

### 6.2 Functional App Root
```text
app\
├── backend\
├── frontend\
├── data\
├── .env\
├── README.md\
└── start.py
```

### 6.3 Backend Structure
```text
app/backend/
├── main.py
├── config.py
├── dependencies.py
├── session/
├── brokers/
├── api/
├── services/
├── streaming/
├── data/
├── auth/
├── models/
└── pocketoptionapi/
```

### 6.4 Frontend Structure
```text
app/frontend/src/
├── api/
├── stores/
├── components/
│   ├── layout/
│   ├── trading/
│   ├── risk/
│   ├── auth/
│   ├── settings/
│   └── shared/
├── hooks/
└── utils/
```

---

## 7. Implementation Phases

### Phase 0 — Ops Layer: Chrome Lifecycle + Manual SSID Input ✅

> **Completed 2026-03-26**
> Established Chrome process management, status polling, and manual SSID input — the same proven workflow used in QuFLX-v2's `ops.py` + `TopBar.jsx`.

**Goal:** Establish Chrome process management, status polling, and manual SSID input.

#### Why This Phase Exists

The original v3 plan (Phases 1–9) assumed the SSID would arrive via Swagger UI or a static config file. This skipped the critical reality that:

1. **Chrome must run with `--remote-debugging-port=9222`** for the user to have a logged-in Pocket Option session
2. **The SSID is a full `42["auth",{...}]` WebSocket frame** (not a cookie) that the user obtains from Chrome DevTools
3. **The backend must manage Chrome as a subprocess** — the user should not need to run a separate `.bat` file
4. **The existing `netstat_chrome_session.bat` calls v2's Python script** — a cross-project dependency that must be eliminated

#### Deliverables

1. **`app/backend/api/ops.py`** — Chrome lifecycle endpoints (ported from v2 `ops.py`, simplified)
   - `POST /api/ops/chrome/start` — Find Chrome executable, spawn with remote debugging flags, return PID
   - `POST /api/ops/chrome/stop` — Terminate managed Chrome process
   - `GET /api/ops/chrome/status` — Probe `config.chrome_port` (default 9222), return running/stopped
   - `GET /api/ops/status` — Combined status: Chrome available + session connected + balance
   - Dev-gate: `QFLX_ENABLE_OPS=1` + localhost-only (same security model as v2)

2. **`app/backend/api/session.py`** — SSID connect/disconnect endpoints (extracted from `main.py`)
   - `POST /api/session/connect` — Accept `{ ssid, demo }`, validate via `PocketOptionSession`, connect
   - `POST /api/session/disconnect` — Disconnect active session
   - `GET /api/session/status` — Return connected/disconnected, account type, balance
   - `GET /api/session/ssid-status` — Return booleans for saved demo/real SSIDs in `.env`
   - SSID persistence: after successful connect, write SSID to `.env` (`PO_SSID_DEMO` / `PO_SSID_REAL`)
   - Auto-reconnect: on connect with empty SSID string, fall back to saved `.env` values

3. **Socket.IO `check_status` event** — Added to `main.py`
   - Probes Chrome port availability (from `config.chrome_port`)
   - Reports active session state from `SessionManager`
   - Returns structured status payload for frontend consumption
   - Polling cadence: frontend calls every 5 seconds (same as v2)

4. **`config.py` updates** — Already has `chrome_port` ✓, add:
   - `chrome_profile_dir` — path to `Chrome_profile/` directory (default: `app_root.parent / "Chrome_profile"`)
   - `chrome_url` — default URL to open (default: `https://pocket2.click/cabinet/demo-quick-high-low`)
   - `chrome_executable` — optional override via `CHROME_PATH` env var

5. **Delete `netstat_chrome_session.bat`** from workspace root — eliminates cross-project dependency on v2

#### Chrome Spawn Flags (v2-aligned, security-improved)

```
chrome.exe
  --remote-debugging-address=127.0.0.1
  --remote-debugging-port=9222
  --user-data-dir=<project>/Chrome_profile
  --no-first-run
  --no-default-browser-check
  --disable-default-apps
  --disable-popup-blocking
  --new-window
  <chrome_url>
```

> **Security improvement over v2:** Do NOT include `--disable-web-security` or `--allow-running-insecure-content` unless explicitly enabled via a separate `CHROME_INSECURE_MODE` env var. These flags weaken browser security and were flagged as High severity in the v2 architecture review.

#### SSID Workflow (Manual-First)

```
User clicks "Chrome" button in TopBar (or calls POST /api/ops/chrome/start)
  → Backend spawns Chrome with remote debugging
  → Chrome opens Pocket Option login page
  → User logs in manually

User opens Chrome DevTools → Network → WS → copies 42["auth",{...}] frame

User pastes SSID into connect dialog (or calls POST /api/session/connect)
  → PocketOptionSession validates the auth frame format
  → PocketOptionSession connects to Pocket Option WebSocket
  → On success: balance returned, SSID persisted to .env
  → On failure: explicit error message returned

Next time: User clicks "Connect" with empty SSID
  → Backend reads saved SSID from .env
  → Auto-reconnects without manual paste
```

#### What NOT to Build in Phase 0

- ❌ Automated CDP cookie/SSID extraction (future enhancement, not foundation)
- ❌ Chrome Extension for SSID capture
- ❌ Any new subprocess services beyond the single FastAPI app
- ❌ Frontend UI (that comes in Phase 4 — Phase 0 is testable via Swagger UI)

#### Required Behaviors
- Chrome spawn must be idempotent (if port 9222 is already listening, return `already_running`)
- Chrome stop must be graceful (terminate, then kill after timeout)
- SSID validation must fail fast with typed exceptions (`SSIDParseError`)
- Status endpoint must never return stale data — always probe live state
- `.env` persistence must update in-memory config after write (fix v2 bug)

#### Acceptance Criteria
- [x] `POST /api/ops/chrome/start` spawns Chrome with remote debugging on port 9222
- [x] `GET /api/ops/chrome/status` correctly reports Chrome running/stopped
- [x] `POST /api/session/connect` with a valid `42["auth",...]` frame returns `connected=true` + balance
- [x] `POST /api/session/connect` with empty SSID falls back to `.env` saved value
- [x] `GET /api/session/status` returns accurate connected/disconnected state
- [x] `GET /api/ops/status` returns combined Chrome + session status
- [x] Socket.IO `check_status` event returns Chrome and session state
- [x] `netstat_chrome_session.bat` is deleted from workspace root
- [x] No cross-project dependency on QuFLX-v2 remains

#### Testing
- Chrome start when Chrome is not installed → structured 424 error
- Chrome start when port 9222 already listening → `already_running` response
- Connect with malformed SSID → 400 error with `SSIDParseError` detail
- Connect with valid SSID → `connected=true`, balance present
- Connect with expired SSID → explicit auth failure message
- Disconnect → session cleared, status returns `disconnected`
- Status polling → accurate real-time state

---

### Phase 1 — Backend Foundation ✅

**Goal:** Create the runtime backbone for live trading.

#### Deliverables
- `app/backend/main.py` as the single FastAPI app entrypoint.
- `app/backend/config.py` for environment and runtime settings.
- `app/backend/models/` for all request/response/domain schemas.
- `app/backend/session/` with `PocketOptionSession` wrapper and session manager.
- `app/backend/brokers/base.py` and `registry.py`.
- `app/backend/brokers/pocket_option/adapter.py` rewritten to use `PocketOptionSession` directly.
- `app/backend/data/` repository interface plus local file implementation.

#### Acceptance Criteria
- [x] Backend starts without depending on the TUI project.
- [x] A real connection can be established through the new session layer.
- [x] Broker adapter can execute a test trade through the new trade path.
- [x] Local data logging works and matches the schema contract.

---

### Phase 2 — Broker + Trade Execution ✅

**Goal:** Make live trade execution reliable and explicit.

#### Acceptance Criteria
- [x] Trade execution uses the verified asset path.
- [x] Trade attempts fail cleanly if the session is disconnected.
- [x] Trade result records are written consistently.

---

### Phase 3 — Streaming and Enrichment ✅

**Goal:** Provide live market data and signal enrichment.

#### Acceptance Criteria
- [x] Real-time ticks are captured and normalized.
- [x] Signals are enriched and delivered to the frontend.
- [x] Warmup state and readiness are exposed cleanly.

---

### Phase 4 — Frontend Shell ✅

**Goal:** Establish a high-end, glowy UI shell with dual themes and Risk Manager visualization.

**Design References:**
- **Theme 1 (Trading):** Light Theme variation of "Neon Glow" dashboard style (Image 1 ref).
- **Theme 2 (Risk Manager):** Dark Theme dashboard style (Image 2 ref).
- **Tab Toggle:** Primary navigation between "Trading View" and "Risk Manager".

#### Deliverables
- `MainLayout.jsx` — Overall app structure with sidebar support.
- `LeftSidebar.jsx` — Collapsible navigation/asset sidebar.
- `RightSidebar.jsx` — Collapsible info/risk sidebar.
- `TopBar.jsx` — Chrome/SSID status badges + Theme toggle + Trade/Risk tab toggle.
- `Zustand Stores` — Auth, Layout (Theme/Tabs), Assets, Trading, Settings, Stream, and Risk.
- `useOpsStore.js` — Chrome/Session lifecycle control.
- `API Client Layer` — `opsApi.js`, `tradingApi.js`, `streamApi.js`.
- `Socket.IO Integration` — Hooking into backend `check_status` and tick streams.

#### Acceptance Criteria
- [x] React + Vite + Tailwind project scaffolded in `app/frontend`.
- [x] Theme provider supporting Light (Trading) and Dark (Risk) modes.
- [x] Tab toggle switches between Trading and Risk views.
- [x] TopBar badges correctly report backend Chrome and Session status.
- [x] Left/Right sidebars collapse/expand with persistence.

#### Phase 4 Verification Summary
- React + Vite + Tailwind v4 shell is built and verified with a clean production build.
- Socket.IO polling updates Chrome/session state in the top bar.
- Sidebar collapse state persists and the Trading/Risk theme split is in place.
- Current gap is visual fidelity to the provided trading-terminal draft, which is now a Phase 5+ styling and content task rather than a shell blocker.

---

### Phase 5 — Trading UI
**Goal:** Make the core trading view fast and usable.

#### Deliverables
- `Sparkline.jsx`
- `OTEORing.jsx`
- `TradePanel.jsx`
- `TradeHistory.jsx`
- `MultiChartView.jsx`
- `MiniSparkline.jsx`

#### Acceptance Criteria
- The main trading area shows chart, signal, action, and results cleanly.
- Multi-chart and mini-chart views reuse the same canonical data.
- Asset switching does not break warmup or state consistency.

---

### Phase 6 — Risk Management
**Goal:** Integrate quick session risk visibility.

#### Deliverables
- `VerticalRiskChart.jsx`
- `SessionRiskPanel.jsx`
- `RiskSummaryCards.jsx`
- unified trade-history / session-table flow

#### Acceptance Criteria
- Risk visualization appears next to the sparkline in the main layout.
- Trade history and session risk data are generated from a shared source.
- The risk UI remains optional and composable.

---

### Phase 7 — Settings System
**Goal:** Make settings structured, scalable, and easy to extend.

#### Deliverables
- `SettingsView.jsx` with tabs/sections
- `AccountSettings.jsx`
- `AppSettings.jsx`
- backend settings schemas and service layer

#### Acceptance Criteria
- Account settings and app settings are clearly separated.
- New setting groups can be added without reworking the UI.
- Settings changes are validated before persistence.

---

### Phase 8 — AI Integration
**Goal:** Add advisory intelligence in a controlled way.

#### Deliverables
- `AIService`
- `/api/ai/*` endpoints
- session analysis
- asset suggestion
- signal confirmation
- risk advice

#### Acceptance Criteria
- AI responses are structured and validated.
- AI only informs decisions and does not execute trades.
- AI functionality can be disabled without impacting core trading.

---

### Phase 9 — Polish and Hardening
**Goal:** Finalize the production-quality experience.

#### Deliverables
- error boundaries
- loading states
- toast notifications
- export utilities
- ghost trading views
- ops controls
- test coverage and regression verification

#### Acceptance Criteria
- No silent failures remain in the critical path.
- Runtime paths are stable under reconnect/reload.
- UI and backend boundaries remain clean.

---

## 8. File Ownership Rules

### Workspace Root Files
- Reference and planning documents only.
- No production runtime code should live directly in the workspace root.

### `app/` Ownership
- All runtime backend code belongs in `app/backend`.
- All runtime frontend code belongs in `app/frontend`.
- All operational data belongs in `app/data`.

### Legacy Reference Folder
- Treat `legacy_reference/` as read-only.
- Copy from it into `app/` only when a design decision is finalized.

---

## 9. Testing Strategy

### Phase 0 (Ops + Chrome + SSID)
- Chrome start/stop/status lifecycle tests
- Chrome not found → structured error test
- Chrome already running → idempotent response test
- SSID format validation tests (malformed, missing fields, valid)
- SSID connect/disconnect lifecycle tests
- `.env` persistence and reload tests
- Auto-reconnect with saved SSID test
- Socket.IO `check_status` response shape tests
- Dev-gate enforcement tests (ops disabled, non-local client)

### Backend
- session parsing validation
- connection lifecycle tests
- broker adapter tests
- trade execution tests
- repository tests
- settings validation tests

### Frontend
- component rendering tests
- layout collapse/expand tests
- asset list behavior tests
- settings tab behavior tests
- risk panel rendering tests

### Integration
- real SSID connection test
- OTC trade path test
- tick stream flow test
- trade history logging test
- reload/reconnect recovery test

### AI
- structured response validation
- advisory-only behavior checks
- timeout and error handling tests

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| No Chrome management = no SSID source | **Critical** | Phase 0 establishes Chrome lifecycle before any other phase |
| Cross-project dependency on v2 scripts | High | Delete `netstat_chrome_session.bat`; v3 owns its own Chrome launcher |
| SSID badge shows "connected" when only service is up (not authenticated) | High | Phase 0 separates Chrome status from authenticated session status |
| Premature CDP automation before manual path works | Medium | Phase 0 is manual-first; CDP extraction is a future enhancement only |
| Stale `.env` SSID after persistence | Medium | Phase 0 requires in-memory config refresh after `.env` write |
| Chrome not found on user's machine | Medium | Structured 424 error with clear message and `CHROME_PATH` hint |
| Reintroducing TUI coupling | High | Keep `app/` isolated from TUI; use `PocketOptionSession` directly |
| Monolithic components return | High | Enforce component ownership and per-domain stores |
| Silent failure in auth/trade flow | Critical | Fail fast, validate early, and return explicit errors |
| Settings become tangled | Medium | Separate account/app scopes and schema-driven rendering |
| Data migration becomes hard later | High | Keep repository abstraction and schema contract intact |
| AI overreach | High | Advisory-only AI with structured validation |

---

## 11. Immediate Next Actions

1. **[Phase 0]** Create `app/backend/api/ops.py` — Chrome start/stop/status endpoints (port from v2 `ops.py`).
2. **[Phase 0]** Extract session endpoints from `main.py` into `app/backend/api/session.py` — connect/disconnect/status/ssid-status.
3. **[Phase 0]** Add `check_status` Socket.IO event to `main.py` — Chrome + session status polling.
4. **[Phase 0]** Update `config.py` — add `chrome_profile_dir`, `chrome_url`, `chrome_executable`.
5. **[Phase 0]** Delete `netstat_chrome_session.bat` — remove cross-project v2 dependency.
6. **[Phase 0]** Test full Chrome → login → paste SSID → connect workflow via Swagger UI.
7. **[Phase 1]** Rebuild the broker adapter around `PocketOptionSession`.
8. **[Phase 1]** Add the repository abstraction for local storage.
9. **[Phase 4]** Scaffold the frontend layout shell, stores, and TopBar with Chrome/SSID badges.
10. **[Phase 5]** Build the trading-terminal UI from the dashboard draft: chart stage, signal cards, execution panel, and logs.
11. Verify the real trade path before adding non-essential features.

---

## 12. Notes on the Rebuild Architecture File

The architecture summary file `otc_sniper_v3_rebuild_architechture.md` has been updated (2026-03-26) to reflect:
- **Phase 0 ops layer** — Chrome lifecycle management and manual SSID input (NEW)
- **SSID workflow** — manual-first with `.env` persistence and auto-reconnect (NEW)
- **TopBar badge requirements** — Chrome and SSID status badges aligned with v2 pattern (NEW)
- **Security improvements** — removal of `--disable-web-security` Chrome flags (NEW)
- the workspace/app root split
- the new `C:\v3\OTC_SNIPER\app` runtime requirement
- the settings split between Account and App scopes
- the local-to-Supabase data migration rule
- the risk visualization layout rule
- the multi-chart preservation rule
- the AI advisory-only policy

This plan is the execution companion to that architecture file.
