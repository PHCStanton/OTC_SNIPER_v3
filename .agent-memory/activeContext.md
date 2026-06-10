# Active Context

## Summary
- This file tracks the immediate working state of the project.
- **We are currently working on the Git branch `feature/ai-developer-mode-paste`.**
- **AI Developer Mode and Copy-Paste Uploads (2026-06-10) are fully implemented, verified, and closed.** Added a Developer Mode toggle to AppSettings and TopBar dropdown, enabled direct clipboard paste image uploads in the AITab, persisted pasted image files on the backend temporary path, and added visual status indicators and platform insights options.
- **Independent AI Layer Toggle (2026-06-10) is fully implemented, verified, and closed.** Decoupled the AI advisory/model logic from Level 3. Added a dedicated AI toggle button next to Level 1, 2, and 3 buttons in the settings panel card, syncing it to the backend and tracking it in logs/payloads.
- **Lagging and Latency Optimizations (2026-06-05) are fully implemented, verified, and closed.**
- The Auto-Ghost trader's 401-trade evidence set already drove the Level 2 hardening and tuning work; that foundation remains stable.
- **TRAE session fixes (2026-04-27) remain fully implemented and closed.**
- **Level 3 Phases 0, 1, 2, and 3 are now complete.** Phase 3 passed the multi-agent review gate on 2026-05-02, the user approved continuation, and the full low-severity remediation pass is complete.
- **OTEO Level Backtest Plan (2026-05-15) is now fully closed.** All 4 phases implemented, reviewed, and signed off.
- The next valid implementation target is **Phase 4: AI Advisory Review Loop** in `Dev_Docs/Level3_Implementation_Plan_26-04-29.md`.
- A separate planning track is now documented in `Dev_Docs/L123_Optimization_and_AI_Knowledge_Base_Plan_26-05-16.md`; if approved, its next implementation step is `Phase 1 - Analyzer Core and Join Validation`.

## Latest Changes

### Applied on 2026-06-10 — AI Developer Mode & Paste Uploads (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| AI-D0 | Git Branch | N/A | Switched to and isolated features in the `feature/ai-developer-mode-paste` branch. |
| AI-D1 | Settings Store | `useSettingsStore.js`, `useAIStore.js` | Added `aiDevMode` setting and updated the AI store context builder to pass `developerMode: settings.aiDevMode` to the backend. |
| AI-D2 | AppSettings UI | `AppSettings.jsx` | Added a Developer Mode toggle inside the AI Integration & Feeds section card. |
| AI-D3 | Clipboard Paste UI | `AITab.jsx` | Added clipboard paste image listeners in the textarea. Paste operations read the file as a Data URL, set the preview, and notify via toast. Rendered a `DEVELOPER MODE ACTIVE` status label when enabled. |
| AI-D4 | TopBar Menu | `TopBar.jsx` | Replaced the AI icon button with a relative dropdown menu containing toggles for Dev Mode, navigation shortcuts, placeholder actions, and a functional developer prompt injector. |
| AI-D5 | Temp Directories | `config.py` | Automatically creates `data/tmp/uploaded_images` on app startup. |
| AI-D6 | Models & Prompts | `ai_models.py`, `ai_service.py` | Updated `AIContext` model schema and system prompt compiler to insert platform-development instructions if `developer_mode` is `True`. |
| AI-D7 | Image Persistence | `ai_service.py` | Automatically decodes base64 pasted/uploaded screenshots and writes raw binary files to `data/tmp/uploaded_images` for offline inspection. |

### Applied on 2026-06-10 — Independent AI Layer Toggle (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| AI-T0 | AI State Settings | `app/frontend/src/stores/useSettingsStore.js`, `app/frontend/src/App.jsx` | Added `oteoAiEnabled` setting to the frontend store and synced it to the backend under the `oteo_ai_enabled` field. |
| AI-T1 | settings Card UI | `app/frontend/src/components/settings/AppSettings.jsx`, `app/frontend/src/components/layout/TopBar.jsx` | Renamed `Level 3 (AI)` button to `Level 3` and exported the reusable `AiChipIcon` from TopBar. Placed the independent AI button next to Level 1/2/3 indicators inside the OTEO Signal Layer settings card with matching selected/deselected glow effects. |
| AI-T2 | Backend Router & Streaming | `app/backend/api/strategy.py`, `app/backend/services/streaming.py` | Updated FastAPI routes and the streaming service configuration to receive `oteo_ai_enabled`. Added a defensive check to prevent AttributeError on test stubs. Passed the setting to Socket.IO ticks payload, signal loggers, and AutoGhost signals. |
| AI-T3 | Auto-Ghost Logger | `app/backend/services/auto_ghost.py` | Appended the status of `oteo_ai_enabled` inside the Auto-Ghost trade entry context for better analytical reporting. |

## Current State
- **Performance:** Event-loop blocking has been completely eliminated.
- **Frontend Optimization:** Zustand store state is split; components only render on target changes.
- **Independent AI Toggle:** Users can now enable/disable the AI Layer independently in the Settings panel OTEO Signal card.
- **Developer Mode & Dropdown:** TopBar AI button opens a dropdown menu containing navigation commands, placeholder actions, and Developer Mode switches. System prompt changes in Dev Mode to support software construction discussions.
- **Pasting screenshots:** Direct clipboard screenshot paste operations are fully functional in AITab, and the backend writes temporary image files to `app/data/tmp/uploaded_images/` automatically.
- The Level 3 implementation plan is active with **Phases 0, 1, 2, and 3 completed and signed off**.
- Phase 4 (AI Advisory Review Loop) has not started.

## Validation
- **Backend Compilation:** `conda run -n QuFLX-v2 python -m py_compile app/backend/config.py app/backend/models/ai_models.py app/backend/services/ai_service.py` -> ✅ passed.
- **Frontend Production Build:** `npm run build` inside `app/frontend` -> ✅ passed (built successfully in 21.63s).
- **Backend Unit Tests:** `conda run -n QuFLX-v2 python -m unittest test_backtest_oteo_levels.py test_level3_phase1.py test_level3_phase2.py test_level3_phase3.py` -> ✅ passed (39/39).
