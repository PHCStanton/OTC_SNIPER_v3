# Active Context

- **Calibration Feature Deprecated & Completely Removed (2026-06-16).** Stripped all backend properties (`ai_calibration_phase`), FastAPI request parameters (`calib_context`), and session metadata checks from `auto_ghost.py`, `streaming.py`, `strategy.py`, `analysis.py`, and `analysis_service.py`. Decoupled settings stores (`useSettingsStore.js`), sync layers (`App.jsx`), and Layout Timers (`GlobalTimer.jsx`). Removed the calibration trigger UI panel from `AnalysisView.jsx` and renamed the tab to **AI Refinement**. Verified backend compilation and pytest suite (`test_auto_ghost.py`) passed cleanly.
- **Calibration AI Advisory Alignment & Bug Fixes are fully complete and verified (2026-06-15).** Fixed Zustand settings store validation bug in `useSettingsStore.js` to allow `aiCalibrationPhase` changes to persist and sync. Added session-level `is_calibration` parsing in `analysis_service.py` to auto-tag calibration sessions. Added clear `Calib` and `Tuned` status badges to session logs list (`AnalysisView.jsx`) and floating controller widget header (`GhostTradingWidget.jsx`). Verified clean frontend production builds and automated test suite execution (`test_auto_ghost.py`).
- **Z-Score & Regime Gates (Ghost Protocol) Integration & Stale Tick Filtering is now fully complete and verified (2026-06-14).** Resolved the JSX compilation syntax error, calibration stopwatch auto-stop, and Grok audio overlapping in `AnalysisView.jsx`. Implemented settings, validation, and `loadGhostProtocol` actions in `useSettingsStore.js` and wired them to sync via `App.jsx`. Configured FastAPI strategy router, streaming service updates, and implemented the actual Z-Score and Market Regime confluences validation checks inside `auto_ghost.py`. Applied a 15-minute (900s) age limit constraint on historical ticks loaded during engine pre-seeding in `streaming.py` to prevent stale context data from corrupting initialization state.
- **Level 3 Phases 4 and 5 are complete (2026-06-11).** AI Advisory Review Loop (`ai_review.py`) is wired into the streaming pipeline and available via `GET /api/strategy/ai-review`. Frontend L3 regime visualization is live in `OTEORing.jsx` and `MultiChartView.jsx`, covering all 6 `Market_Regimes.md` labels with color-coded badges. 3 codebase bug fixes applied (logger import, `_get_severity` DRY, AI prompt regime enrichment).
- **L123 Optimization and AI Knowledge Base Plan (2026-06-13) — 100% COMPLETE ✅ (Phases 1-3, 5, 6).** `scripts/analyze_trade_intelligence.py` refactored into composable phase functions. Full-corpus run: 9,999/10,207 trades joined (97.96%), 66 assets, 3 strategy levels, 1,029 knowledge-base patterns generated. Phase 6 (AI Advisory Contract) implemented: loaded condition patterns into AI confirmation prompts and background advisory loops, integrated active manipulation severity formatting, and embedded the OTC microstructure manipulation patterns taxonomy. All 5 new retrieval unit tests and existing auto-ghost smoke tests pass cleanly.
- **Result Analysis Panel Enhancements (2026-06-11) are fully implemented, verified, and closed.** Added a Gregorian UTC date column, separate dropdown options for single-file/multi-file/folder uploads, session deletion UI and backend stats purging, and resolved the AI analysis refinement 500 error.
- **Result Analysis Panel/Page (2026-06-10) is fully implemented, verified, and closed.** Added backend router `/api/analysis/*` for parsing ghost/live trade sessions, calculating daily stats summaries, running Grok 4.3 reviews, persisting pattern recall memory, and producing speech playback audio. Integrated TopBar routing, activeView selection, and visual tabs (Session Logs list, responsive custom SVG charts, and AI Refinement dashboard).
- **AI Developer Mode and Copy-Paste Uploads (2026-06-10) are fully implemented, verified, and closed.** Added a Developer Mode toggle to AppSettings and TopBar dropdown, enabled direct clipboard paste image uploads in the AITab, persisted pasted image files on the backend temporary path, and added visual status indicators and platform insights options.
- **Independent AI Layer Toggle (2026-06-10) is fully implemented, verified, and closed.** Decoupled the AI advisory/model logic from Level 3. Added a dedicated AI toggle button next to Level 1, 2, and 3 buttons in the settings panel card, syncing it to the backend and tracking it in logs/payloads.
- **Lagging and Latency Optimizations (2026-06-05) are fully implemented, verified, and closed.**
- The Auto-Ghost trader's 401-trade evidence set already drove the Level 2 hardening and tuning work; that foundation remains stable.
- **TRAE session fixes (2026-04-27) remain fully implemented and closed.**
- The next valid implementation target is **Phase 6: Volatility-Adaptive Expiry** in `Dev_Docs/Level3_Implementation_Plan_26-04-29.md`.

## Latest Changes

### Applied on 2026-06-16 — Deprecation & Removal of Calibration Feature (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| CALIB-1 | Backend API | `strategy.py`, `analysis.py` | Removed `ai_calibration_phase` request config fields and `calib_context` analysis refinement parameters. |
| CALIB-2 | Backend Services | `streaming.py`, `auto_ghost.py`, `analysis_service.py` | Stripped calibration checks from streaming updates, Auto-Ghost configs, log parsing, and Grok prompt generation. |
| CALIB-3 | Zustand Store | `useSettingsStore.js`, `App.jsx` | Removed state defaults and validation mappings for `aiCalibrationPhase` and `calibTimer`. Wired out of config synchronization. |
| CALIB-4 | Layout Components | `GlobalTimer.jsx`, `GhostTradingWidget.jsx` | Decoupled stopwatch timers, removed `CALIB` state sync alerts, and replaced conditional badges with clean simulated `Ghost` markers. |
| CALIB-5 | Analysis Panel | `AnalysisView.jsx` | Removed local calibration states, effects, suggest gates, dynamic calculations, and renamed tab to **AI Refinement**. |
| CALIB-6 | Verification | `test_auto_ghost.py` | Executed backend tests in `QuFLX-v2` conda environment. **1 test passed in 0.32s** successfully. |

### Applied on 2026-06-15 — Calibration AI Advisory Alignment and Bug Fixes (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| CAL-1 | Zustand Store | `useSettingsStore.js` | Fixed serialization bug by adding `aiCalibrationPhase` to the `validateSettings()` return schema. |
| CAL-2 | Backend Parser | `analysis_service.py` | Added session-level `is_calibration` boolean check to `parse_session_file` by scanning trade entry contexts. |
| CAL-3 | Badging UI | `AnalysisView.jsx`, `GhostTradingWidget.jsx` | Placed `Calib` and `Tuned` status badges on session log rows and floating controller widget title bar. |
| CAL-4 | Verification | `test_auto_ghost.py` | Verified backend compilation and full ghost suite tests with zero failures. |

### Applied on 2026-06-14 — Z-Score & Regime Gates (Ghost Protocol) Integration & Stale Tick Filtering (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| GP-1 | Backend Gates | `auto_ghost.py` | Added Z-Score min/max bounds checks and Market Regime whitelist membership / stability filters in `consider_signal()`. Exposes new gates in the status payload. |
| GP-2 | Backend Routing | `strategy.py`, `streaming.py` | Extended API config schemas and streaming update payload methods to support Z-Score and allowed regime config options. |
| GP-3 | State Store | `useSettingsStore.js`, `App.jsx` | Added defaults and setters for Z-Score bounds and regime chips. Implemented `loadGhostProtocol` to instantly load named strategy configs. Wired setting sync in `App.jsx`. |
| GP-4 | Controller Settings | `GhostTradingWidget.jsx` | Added min/max Z-Score Gate sliders (range -3 to +3), allowed regime multi-select chips, and telemetry indicators in the UI widget panel. |
| GP-5 | Calibration Tab | `AnalysisView.jsx` | Implemented 3rd top-level "Ai-Calibration" tab with Ghost Protocol profile selectors, N-trades or timed stopwatch calibration runners, suggested gates recomputation, and one-click apply function. Resolved compiling syntax error (unbalanced tags) in `AnalysisView.jsx`. |
| GP-6 | Seeding Filter | `streaming.py` | Applied a 15-minute (900s) age limit constraint on historical ticks loaded during engine pre-seeding to prevent stale context data from corrupting initialization state. |
| GP-7 | Calibration Timer | `GlobalTimer.jsx` | Resolved a critical stopwatch leak and stale closure where the interval would run infinitely in the background after calibration deactivation. |
| GP-8 | Gate Unit Tests | `test_auto_ghost.py` | Added Test 7 and Test 8 verifying that the Auto-Ghost trader correctly applies Z-Score bounds and Market Regime whitelist/stability gates. |
| GP-9 | Hook Order Fix | `AnalysisView.jsx` | Resolved React Rules of Hooks violation by moving conditional Zustand store hook calls to top-level declarations. |

### Applied on 2026-06-13 — L123 Phase 6 (AI Advisory Contract) (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| KB-1 | KB Loader & Query | `ai_review.py` | Implemented `KnowledgeBaseLoader` lazy-loading patterns from `condition_patterns.json`, custom similarity scoring matching symbols/regimes/bands, and prompt formatting helpers. |
| KB-2 | Manipulation Taxonomy | `ai_review.py`, `auto_ghost.py` | Added detailed `_MANIPULATION_TAXONOMY` describing the 7 microstructure patterns (Liquidity Sweeps, Pinning, Push & Snap, Fake Breakouts, Whipsaws, Low Liquidity, Multi-Asset Coordination) to prompts. |
| KB-3 | AI Confirmation | `auto_ghost.py` | Updated `_query_ai_confirmation` signature and logic to accept strategy level, load matching KB patterns, format active manipulation severities, and embed context in prompts. |
| KB-4 | Advisory Notifications | `auto_ghost.py` | Enriched Socket.io notifications with top historical KB pattern matches (win rate, count). |
| KB-5 | Unit Tests | `test_knowledge_base_retrieval.py` | Created comprehensive unit tests covering lazy loading, similarity priority querying, band mappings, and full AI confirmation prompt structure validation. |

### Applied on 2026-06-13+ — Grok Native TTS Integration + Results & Analysis Panel Regime/Z-Score Filters (VERIFIED + ITERATED)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| TTS-1 | Backend TTS Provider | `ai_providers/xai_provider.py` | Added `generate_speech(text, voice_id, language, speed, output_format, with_timestamps)` calling `POST /v1/tts`. Reuses auth/httpx client. |
| TTS-2 | AI Service Layer | `ai_service.py` | Added `text_to_speech(text, voice_config)` and `generate_voice_over_audio(...)` (script gen + TTS chain). Integrated profile resolution from `ai_config`. |
| TTS-3 | AI Profiles & Config | `ai_config.py` | Extended `DEFAULT_PROFILES` and helpers with `voice.provider` ("browser"\|"grok"), `voiceId`, `speed`, `language`. |
| TTS-4 | API Proxy | `api/ai.py` | New `POST /api/ai/speak` SpeakRequest proxy returning `audio/mpeg`. |
| TTS-5 | Frontend Voice UI | `components/settings/AISettings.jsx` | Voice provider toggle (Grok vs Browser). Grok: selectors (eve/ara/rex/sal/leo) + custom voice_id input. Speed/language. Test playbacks. |
| TTS-6 | Playback Integration | `components/analysis/AnalysisView.jsx` | Profile-aware playback: calls `/api/ai/speak` -> blob -> `<audio>`. Fallback to browser `speechSynthesis`. |
| ANAL-1 | Session Enrichment | `analysis_service.py` | `parse_session_file` returns "regimes" list and "avg_z_score". New `_compute_z_regime_winrates(trades)` for 5 cutoffs (0.3,0.5,0.8,1.2,2.0) → per-regime {z_cutoff, win_rate, trades}. |
| ANAL-2 | API Response & Insights | `analysis_service.py`, `api/analysis.py` | `get_all_sessions` returns top-level `z_regime_ghost`/`z_regime_live`. AIAnalysisRequest extended with `z_cutoff`, `regimes`. |
| ANAL-3 | AI Analysis with Filters | `analysis_service.py`, `api/analysis.py` | `run_ai_refinement` filters trades by Z/regime before Grok. Prompts include the optimal data + active filters and are instructed to recommend Ghost Controller settings. |
| ANAL-4 | Frontend Filters | `components/analysis/AnalysisView.jsx` | Added regime multi-select chips and Z preset buttons to Logs filter bar. Client filters sessions accordingly. |
| ANAL-5 | Active Filter UX | `AnalysisView.jsx` | Added active filters banner, larger styling, and passes active filters to Grok Review. |

## Current State
- **Z-Score & Regime Gates (Ghost Protocol):** Fully operational on both backend and frontend. Auto-Ghost trading evaluates Z-Score bounds and active regimes before execution.
- **AI Advisory & Knowledge Base:** Composable analyzer joins 97.96% of trades, yields 1,029 KB patterns. The AI reviews and confirms signals using matched patterns and active manipulation indicators.
- **Audio & TTS:** Grok native TTS provides voice overs for scripts and session reports.
- **Performance:** Event-loop lag eliminated, queue worker is thread-safe and non-blocking, tick writing buffered, Zustand state optimized to prevent render cascades, and UI components throttled.
- **Stability:** Clean compiler check for backend and error-free Vite production build.

## Validation
- **Backend Compilation:** `conda run -n QuFLX-v2 python -m py_compile app/backend/services/ai_review.py app/backend/services/ai_service.py app/backend/services/auto_ghost.py app/backend/services/streaming.py app/backend/api/strategy.py app/backend/main.py` -> ✅ passed.
- **Frontend Production Build:** `npm run build` inside `app/frontend` -> ✅ passed (0 errors, built in 2.43s).
- **Backend Unit Tests:** `conda run -n QuFLX-v2 python -m pytest test_backtest_oteo_levels.py test_level3_phase1.py test_level3_phase2.py test_level3_phase3.py test_knowledge_base_retrieval.py -v --tb=short` -> ✅ passed (44/44 tests clean).
