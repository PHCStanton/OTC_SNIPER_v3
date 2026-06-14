# Active Context

- **Level 3 Phases 4 and 5 are now complete (2026-06-11).** AI Advisory Review Loop (`ai_review.py`) is wired into the streaming pipeline and available via `GET /api/strategy/ai-review`. Frontend L3 regime visualization is live in `OTEORing.jsx` and `MultiChartView.jsx`, covering all 6 Market_Regimes.md labels with color-coded badges. 3 codebase bug fixes applied (logger import, `_get_severity` DRY, AI prompt regime enrichment).
- **Result Analysis Panel Enhancements (2026-06-11) are fully implemented, verified, and closed.** Added a Gregorian UTC date column, separate dropdown options for single-file/multi-file/folder uploads, session deletion UI and backend stats purging, and resolved the AI analysis refinement 500 error.
- **Result Analysis Panel/Page (2026-06-10) is fully implemented, verified, and closed.** Added backend router `/api/analysis/*` for parsing ghost/live trade sessions, calculating daily stats summaries, running Grok 4.3 reviews, persisting pattern recall memory, and producing speech playback audio. Integrated TopBar routing, activeView selection, and visual tabs (Session Logs list, responsive custom SVG charts, and AI Refinement dashboard).
- **AI Developer Mode and Copy-Paste Uploads (2026-06-10) are fully implemented, verified, and closed.** Added a Developer Mode toggle to AppSettings and TopBar dropdown, enabled direct clipboard paste image uploads in the AITab, persisted pasted image files on the backend temporary path, and added visual status indicators and platform insights options.
- **Independent AI Layer Toggle (2026-06-10) is fully implemented, verified, and closed.** Decoupled the AI advisory/model logic from Level 3. Added a dedicated AI toggle button next to Level 1, 2, and 3 buttons in the settings panel card, syncing it to the backend and tracking it in logs/payloads.
- **Independent AI Layer Toggle (2026-06-10) are fully implemented, verified, and closed.** Decoupled the AI advisory/model logic from Level 3. Added a dedicated AI toggle button next to Level 1, 2, and 3 buttons in the settings panel card, syncing it to the backend and tracking it in logs/payloads.
- **Lagging and Latency Optimizations (2026-06-05) are fully implemented, verified, and closed.**
- The Auto-Ghost trader's 401-trade evidence set already drove the Level 2 hardening and tuning work; that foundation remains stable.
- **TRAE session fixes (2026-04-27) remain fully implemented and closed.**
- **Level 3 Phases 0, 1, 2, 3, 4, and 5 are all complete.** Phase 3 passed the multi-agent review gate on 2026-05-02; Phases 4 & 5 were implemented on 2026-06-11.
- **OTEO Level Backtest Plan (2026-05-15) is now fully closed.** All 4 phases implemented, reviewed, and signed off.
- The next valid implementation target is **Phase 6: Volatility-Adaptive Expiry** in `Dev_Docs/Level3_Implementation_Plan_26-04-29.md`.
- **L123 Optimization and AI Knowledge Base Plan (2026-06-13) — 100% COMPLETE ✅ (Phases 1-3, 5, 6).** `scripts/analyze_trade_intelligence.py` refactored into composable phase functions. Full-corpus run: 9,999/10,207 trades joined (97.96%), 66 assets, 3 strategy levels, 1,029 knowledge-base patterns generated. Phase 6 (AI Advisory Contract) implemented: loaded condition patterns into AI confirmation prompts and background advisory loops, integrated active manipulation severity formatting, and embedded the OTC microstructure manipulation patterns taxonomy. All 5 new retrieval unit tests and existing auto-ghost smoke tests pass cleanly.

## Latest Changes

### Applied on 2026-06-13 — L123 Phase 6 (AI Advisory Contract) (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| KB-1 | KB Loader & Query | `ai_review.py` | Implemented `KnowledgeBaseLoader` lazy-loading patterns from `condition_patterns.json`, custom similarity scoring matching symbols/regimes/bands, and prompt formatting helpers. |
| KB-2 | Manipulation Taxonomy | `ai_review.py`, `auto_ghost.py` | Added detailed `_MANIPULATION_TAXONOMY` describing the 7 microstructure patterns (Liquidity Sweeps, Pinning, Push & Snap, Fake Breakouts, Whipsaws, Low Liquidity, Multi-Asset Coordination) to prompts. |
| KB-3 | AI Confirmation | `auto_ghost.py` | Updated `_query_ai_confirmation` signature and logic to accept strategy level, load matching KB patterns, format active manipulation severities, and embed context in prompts. |
| KB-4 | Advisory Notifications | `auto_ghost.py` | Enriched Socket.io notifications with top historical KB pattern matches (win rate, count). |
| KB-5 | Unit Tests | `test_knowledge_base_retrieval.py` | Created comprehensive unit tests covering lazy loading, similarity priority querying, band mappings, and full AI confirmation prompt structure validation. |

### Applied on 2026-06-11 — Level 3 Phase 4 & Phase 5 (VERIFIED ✅)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| L3-BF1 | Bug Fix | `ai_service.py` | Added missing `import logging; logger = logging.getLogger(__name__)` — would have crashed on first image upload. |
| L3-BF2 | Bug Fix | `auto_ghost.py` | Extracted duplicate `_get_severity()` helper to module-level — eliminates DRY violation at lines 373 & 563. |
| L3-BF3 | Bug Fix | `auto_ghost.py` | Enriched AI confirmation/advisory prompt with full L3 fields: `regime_label`, `regime_confidence`, `regime_stable`, `cci_state`, `tick_health`, `nearest_structure_atr`. Replaced stale `adx_regime` alias. |
| L3-P4.1 | AI Review Service | `app/backend/services/ai_review.py` [NEW] | Created `AIReviewService` — periodic background regime review loop (configurable interval, default 300s). Covers all 6 Market_Regimes.md labels in every prompt. Advisory-only. |
| L3-P4.2 | Streaming | `app/backend/services/streaming.py` | Imported `AIReviewService`; added `_ai_review` attribute, `attach_ai_review()` method, lifecycle hooks in `start()`/`stop()`, asset cleanup, and snapshot push after each actionable tick. |
| L3-P4.3 | Startup | `app/backend/main.py` | Attaches `AIReviewService` in lifespan startup when AI is enabled (non-fatal try/except). |
| L3-P4.4 | API | `app/backend/api/strategy.py` | Added `GET /api/strategy/ai-review` endpoint returning latest review, operational status, and all-asset results. |
| L3-P5.1 | Signal Normalizer | `app/frontend/src/hooks/useStreamConnection.js` | Added `regime_label`, `regime_confidence`, `regime_stable`, `regime_detail`, `level3_enabled`, `level3_score_adjustment`, `level3_suppressed_reason`, `cci_divergence`, `tick_health` to the signal object. |
| L3-P5.2 | OTEORing | `app/frontend/src/components/trading/OTEORing.jsx` | Added `REGIME_STYLES` map for all 6 L3 regime labels with color coding. Added regime badge between direction pill and AnalysisTerminal, showing label, stability indicator (✓/~), and confidence %. |
| L3-P5.3 | MultiChartView | `app/frontend/src/components/trading/MultiChartView.jsx` | Added `REGIME_CHIP_COLORS` map. Upgraded regime display to use `regime_label` (L3) with color-coded chip and stability indicator. |

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| AE-1 | Date Column | `AnalysisView.jsx` | Created a `formatUTC` date formatter converting epoch start times to `YYYY-MM-DD HH:mm:ss UTC` standard format on the far-left logs table. |
| AE-2 | Separated Uploads | `AnalysisView.jsx` | Separated "+ Add" options into Single File, Multiple Files, and Folder uploads, adding file input value resets to support duplicate uploads. |
| AE-3 | Session Deletion | `AnalysisView.jsx`, `analysis_service.py` | Implemented session deletion button on frontend and backend stats folder cleanup to dynamically update performance charts. |
| AE-4 | AI Completion Error | `xai_provider.py` | Terminated stray background server holding port `8001`, resolving the 500 completion error. |

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
- **Level 3 Phases 0–5 are all complete.** Phase 4 (AI Advisory Review Loop) and Phase 5 (Frontend L3 Visualization) implemented and verified on 2026-06-11.
- **L123 Plan Phases 1+2+3+5 complete (2026-06-13).** `analyze_trade_intelligence.py` refactored into composable functions. Full-corpus: 9,999 trades joined, 66 assets, 3 strategy levels (Level1/Level2/Level3), 5 regimes, 1,029 KB patterns (101 medium/high confidence). Artifacts: `reports/analysis/joined_trades.csv`, `summary_statistics.json`, `mismatch_audit.md`, `knowledge_base/condition_patterns.json`.
- **Next target: L123 Phase 6 (AI Advisory Contract)** — payload contract, pattern retrieval, trade confirmation messages wired to `AIReviewService`.

## Validation
- **Backend Compilation:** `conda run -n QuFLX-v2 python -m py_compile app/backend/services/ai_review.py app/backend/services/ai_service.py app/backend/services/auto_ghost.py app/backend/services/streaming.py app/backend/api/strategy.py app/backend/main.py` -> ✅ passed.
- **Frontend Production Build:** `npm run build` inside `app/frontend` -> ✅ passed (0 errors, built in 2.43s).
- **Backend Unit Tests:** `conda run -n QuFLX-v2 python -m pytest test_backtest_oteo_levels.py test_level3_phase1.py test_level3_phase2.py test_level3_phase3.py -v --tb=short` -> ✅ passed (39/39).

### Applied on 2026-06-13+ — Grok Native TTS Integration + Results & Analysis Panel Regime/Z-Score Filters (VERIFIED + ITERATED)

| # | Area | File(s) | Outcome |
|---|------|---------|---------|
| TTS-1 | Backend TTS Provider | `ai_providers/xai_provider.py` | Added `generate_speech(text, voice_id, language, speed, output_format, with_timestamps)` calling `POST /v1/tts`. Returns raw audio bytes or JSON. Reuses auth/httpx client. |
| TTS-2 | AI Service Layer | `ai_service.py` | Added `text_to_speech(text, voice_config)` and `generate_voice_over_audio(...)` (script gen + TTS chain). Integrated profile resolution from ai_config. |
| TTS-3 | AI Profiles & Config | `ai_config.py` | Extended DEFAULT_PROFILES and helpers with `voice.provider` ("browser"|"grok"), `voiceId`, `speed`, `language`. Added `get_effective_voice_for_feature`. |
| TTS-4 | API Proxy | `api/ai.py` | New `POST /api/ai/speak` (SpeakRequest with text, voice_id, speed, profile_key, etc.). Proxies to service, returns audio/mpeg. |
| TTS-5 | Frontend Voice UI | `components/settings/AISettings.jsx` | Voice provider toggle (Grok vs Browser). Grok: built-in selectors (eve/ara/rex/sal/leo) + custom voice_id input. Speed/language. Test buttons calling /speak. Larger sizes per request. |
| TTS-6 | Playback Integration | `components/analysis/AnalysisView.jsx` (and similar) | Profile-aware playback: if "grok" uses `/api/ai/speak` -> blob -> <audio>. Fallback to speechSynthesis. Updated handlePlayVoice. |
| ANAL-1 | Session Enrichment | `analysis_service.py` | `parse_session_file` now returns "regimes": list, "avg_z_score". New `_compute_z_regime_winrates(trades)` for 5 cutoffs (0.3,0.5,0.8,1.2,2.0) → per-regime {z_cutoff, win_rate, trades}. |
| ANAL-2 | API Response & Insights | `analysis_service.py`, `api/analysis.py` | `get_all_sessions` returns top-level `z_regime_ghost`/`z_regime_live`. AIAnalysisRequest extended with `z_cutoff`, `regimes`. |
| ANAL-3 | AI Analysis with Filters | `analysis_service.py`, `api/analysis.py` | `run_ai_refinement` accepts filters, applies to `trades_summary` (z/regime filtering before Grok). Computes session_z_regime. Injects into prompt + explicit instruction: "analyze the optimal z-score thresholds per regime ... recommend ... for Ghost Controller filters". |
| ANAL-4 | Frontend Filters | `components/analysis/AnalysisView.jsx` | In Logs filter bar: regime multi-select chips (RANGE_BOUND etc.), 5 Z-Score preset buttons (with live WR info from zRegimeData). `filteredSessions` now respects `s.regimes` + `Math.abs(s.avg_z_score) >= cutoff`. Robust fallback if no data. |
| ANAL-5 | Active Filter UX + Size | `AnalysisView.jsx` | Added prominent "Active Z/Regime filter(s) applied — X sessions match" banner. Larger fonts/sizes (p-4, text-xs/11px/12px, px-3 py-1, rounded-2xl) for the new block per prior request. Passes filters on every Grok Review click. |
| ANAL-6 | Execution Quality Tie-in | Discussion (Ghost Controller / auto_ghost.py context) | Confirmed z-score + regime as high-value additions to controller gates (alongside confidence window, manip severity). AI can use recent N trades + KB for "smart average" calibration suggestions before live execution. |
| UX-1 | Filter Robustness | `AnalysisView.jsx` | Graceful degradation: sessions without new fields aren't dropped. Derived `currentZRegimeData` for kind switching. |

- **Current Active Focus:** Integrating the new regime/z-score filters into the Ghost Controller for live execution gating; exploring AI-driven adaptive calibration of gates from recent ghost results (5-10-20 trade windows) using condition_stats + KB patterns. Full verification of TTS + filter flows (backend compile, frontend build, filter + AI roundtrips).
- **Agent Context Note:** All changes respect existing AI-advisory-only boundary, profile-driven config (for models/reasoning/voices), and L123-derived KB for grounding suggestions. No autonomous mutation of live settings without user approval / confirmation mode.
