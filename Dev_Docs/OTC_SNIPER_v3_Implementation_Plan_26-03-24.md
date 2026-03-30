# OTC SNIPER v3 — Implementation Plan

**Date:** 2026-03-24  
**Updated:** 2026-03-30 — Phase 4 shell verified complete; Phase 5 trading UI complete; Phase 6 risk manager scope refined with Trade / Trade Run / Session terminology and VOID state; Phase 7 settings scope refined with Account / App / Risk tabs and Auth0-ready boundaries; Phase 8 AI integration scope defined with xAI Grok provider, image understanding, provider-agnostic architecture, and RightSidebar AI tab — COMPLETE ✅
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

Auth0 readiness rule:
- future identity/profile state will live in a separate user profile boundary
- do **not** add Auth0 user fields to `useAuthStore`
- preserve `useAuthStore` for SSID connect/disconnect only
- reserve Account Settings for session identity, broker identity, and future user-profile presentation only

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
- AI may help explain patterns, summarize sessions, suggest assets, propose risk adjustments, and analyze chart screenshots.
- AI must never directly execute trades or override validation.
- AI integration uses a **provider-agnostic service layer** — xAI/Grok today, swappable to OpenAI/Anthropic later without frontend changes.
- The backend is the sole proxy for AI API calls — the API key never reaches the frontend.
- The backend is stateless for AI — no server-side conversation history (frontend owns chat state via Zustand).
- Image understanding (vision) is a first-class capability — users can share chart screenshots for contextual analysis.
- AI functionality degrades gracefully — if no API key is configured, the AI tab is disabled without affecting core trading.

### 5.5 Trading / Risk Terminology

These terms are mandatory throughout the app, docs, and UI:

| Term | Definition |
|---|---|
| **Trade** | One single executed trade — outcome is WIN, LOSS, or VOID. |
| **Trade Run** | A group of consecutive trades in one focused sequence. |
| **Session** | The overall trading day / account session defined by starting balance, drawdown limit, and take-profit target. |
| **VOID** | A recorded trade that is excluded from P&L and win-rate math. Used for break-even outcomes, SSID sync errors, or manual corrections. |

### 5.6 Risk Modes

The risk surface must support three modes:

- **Auto Mode** — default mode. Automatically records WIN / LOSS / VOID from real SSID / Pocket Option trade results.
- **Manual Mode** — user manually enters WIN / LOSS / VOID for each trade.
- **Manual Override** — user can edit/correct any previously recorded trade, balance, or Trade Run at any time to fix SSID errors.

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
│   ├── ops.py
│   ├── session.py
│   ├── trading.py
│   └── ai.py              ← Phase 8 COMPLETE
├── services/
│   ├── ai_service.py      ← Phase 8 COMPLETE
│   └── ai_providers/      ← Phase 8 COMPLETE
│       ├── __init__.py
│       └── xai_provider.py
├── streaming/
├── data/
├── auth/
├── models/
│   └── ai_models.py       ← Phase 8 COMPLETE
└── pocketoptionapi/
```

### 6.4 Frontend Structure
```text
app/frontend/src/
├── api/
│   └── aiApi.js            ← Phase 8 COMPLETE
├── stores/
│   └── useAIStore.js       ← Phase 8 COMPLETE
├── components/
│   ├── layout/
│   ├── trading/
│   ├── risk/
│   ├── ai/                 ← Phase 8 COMPLETE
│   │   └── AITab.jsx
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

### Phase 1 — Backend Foundation ✅

**Goal:** Create the runtime backbone for live trading.

### Phase 2 — Broker + Trade Execution ✅

**Goal:** Make live trade execution reliable and explicit.

### Phase 3 — Streaming and Enrichment ✅

**Goal:** Provide live market data and signal enrichment.

### Phase 4 — Frontend Shell ✅

**Goal:** Establish a high-end, glowy UI shell with dual themes and Risk Manager visualization.

### Phase 5 — Trading UI
**Goal:** Make the core trading view fast and usable.

### Phase 6 — Risk Management
**Goal:** Deliver a simple, session-aware Risk Manager built from the proven legacy risk foundation.

### Phase 7 — Settings System ✅

**Goal:** Make settings structured, scalable, and Auth0-ready without mixing session identity into the wrong store.

### Phase 8 — AI Integration ✅
**Goal:** Add advisory-only AI intelligence with text chat and image/screenshot analysis using a provider-agnostic architecture. The AI surfaces in a dedicated tab in the RightSidebar, keeping it ambient and always accessible during trading.

> **Status:** COMPLETE ✅

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

### AI (Phase 8) — Verified ✅
- `GET /api/ai/status` returns correct state when API key is present vs. absent
- `POST /api/ai/chat` returns structured response with model and usage fields
- `POST /api/ai/chat` with empty messages array → 422 validation error
- `POST /api/ai/analyze-image` with valid base64 JPEG → returns analysis text
- `POST /api/ai/analyze-image` with oversized image (>20MB) → 413 error
- `POST /api/ai/analyze-image` with invalid format (e.g., GIF) → 400 error
- AI endpoint with missing/invalid API key → 503 with clear error message
- AI endpoint timeout handling → structured error, no silent failure
- Advisory-only enforcement: no AI endpoint returns trade execution payloads
- Frontend AI tab disabled state when `GET /api/ai/status` returns `enabled: false`
- RightSidebar Risk/AI tab toggle preserves state across sidebar collapse/expand
- Image upload converts to base64 correctly for JPEG and PNG
- Conversation cap: store trims messages beyond 20 entries

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
| AI overreach | High | Advisory-only AI with structured validation; no trade execution paths in AI router |
| AI API key leaked to frontend | High | Backend is sole proxy; API key read from `.env` server-side only, never in HTTP responses |
| AI provider outage blocks trading | Medium | Graceful degradation — `GET /api/ai/status` disables AI tab; core trading unaffected |
| Runaway AI costs from large images | Medium | Backend validates image size (<20MB) and format before proxying; conversation cap at ~20 messages |
| AI provider lock-in | Medium | Provider-agnostic service layer; swapping providers requires only a new provider file |
| Prompt injection via user input | Low | System prompt is server-side only; user messages passed as `user` role content |

---

## 11. Immediate Next Actions

1. **[REVIEW]** Delegate @Reviewer for Phase 7 & 8 verification (MANDATORY per protocol).
2. **[Phase 9]** Proceed to Polish and Hardening (after approval).

---

## 12. Notes on the Rebuild Architecture File

The architecture summary file `otc_sniper_v3_rebuild_architechture.md` has been updated (2026-03-26) to reflect:
- **Phase 0 ops layer** — Chrome lifecycle management and manual SSID input (NEW)
- **SSID workflow** — manual-first with `.env` persistence and auto-reconnect (NEW)
- **TopBar badge requirements** — Chrome and SSID status badges aligned with v2 pattern (NEW)
- **Security improvements** — removal of `--disable-web-security` Chrome flags (NEW)
- **Settings split** — Account / App / Risk tabs with a reserved Auth0-ready user profile boundary (NEW)
- the workspace/app root split
- the new `C:\v3\OTC_SNIPER\app` runtime requirement
- the settings split between Account and App scopes
- the local-to-Supabase data migration rule
- the risk visualization layout rule
- the multi-chart preservation rule
- the AI advisory-only policy

This plan is the execution companion to that architecture file.
