# Implementation Plan: Integrating Calibration Context + AI Advisory Insights into Results Analysis + Voice Readback for Bell Notifications

**Note (user revision 2026-06-15):** This plan is persisted in `./Dev_Docs/` (following convention of `L123_Optimization_and_AI_Knowledge_Base_Plan_26-05-16.md`, `journal_implementation_plan_26-04-28.md`, etc.) as `calibration_ai_advisory_integration_plan_2026-06-15.md`. The sessions working copy is the editable draft during planning.

## Context
The user has recently implemented AI Tools (AI Pulse for periodic market insights + AI Suggestions for gate/optimization advice) directly into the Ghost Controller (GhostTradingWidget + AutoGhostService). These feed the Advisory layer via socket notifications (types: "ai_pulse", "ai_advisory"). Confirmation mode was removed; everything is strictly advisory-only. User values the concrete outputs:
- Blacklist/Whitelist asset suggestions.
- Watch-list advice for future moves.
- On-the-fly regime info + what to watch.

The "Ai-Calibration / Ghost Protocol" (Z-score + regime gates) lives in AnalysisView (dedicated tab with 30-trade or timed runs, "Stop & Compute Suggestions" that derives heuristic suggestions from z_regime data + applies only to ghost), useSettingsStore (gates + shared calibTimer*), GlobalTimer (deep integration), and is enforced in auto_ghost.py before AI advisory triggers.

Current gaps (per user feedback):
- Results Analysis panel (AnalysisView "Grok Review"/run-ai-refinement + z_regime insights) has no awareness of active/past calibration phases or the real-time AI Pulse/Suggestions advisories generated *during* calib (when gates are typically disabled for data collection).
- No explicit "calibration session" vs. "tuned/live ghost session" classification. Sessions are just kind='ghost' vs 'live' in ghost_trades/ vs live_trades/ dirs + analysis_service. "Stop & Compute" does not auto-tag or save calib context.
- Results Analysis does not explicitly surface favorable/unfavorable assets with session-specific details useful for operational (post-calib) runs.
- No voice readback for the short AI advisory outputs that appear in the Bell dropdown (TopBar + useNotificationStore). Voice/TTS (Grok native + browser fallback) exists only for full report playback in AnalysisView and test buttons in AISettings (via /api/ai/speak + blob Audio).

Goals: Close the loop between lightweight real-time Ghost AI advisory (Pulse/Suggestions during calib) + deeper post-hoc Results Analysis (Grok + regime/asset stats), support explicit calib session lifecycle (flag on start, auto-classify on Stop & Compute, tuned phase after gate apply), enhance asset insights, and add convenient play-voice buttons to Bell AI notifs. Prioritize UX (clear distinction, low friction, visual feedback), efficiency/speed (reuse existing pipelines/notifs/AI calls/TTS paths, short texts, async/background, minimal new state), while strictly following CORE_PRINCIPLES.md (functional simplicity, sequential logic, strict separation of concerns, defensive error handling, fail fast, zero silent failures, stop-patching/rewrite if >2-3 patches, incremental verification, delegate specialists via @ if domain touches).

This is a polish/integration task on top of recent Phase 9 / L123 / Ghost Protocol work (see progress.md, App.jsx, analysis_service.py, auto_ghost.py, streaming.py).

## Recommended Approach (Chosen for Simplicity + Leverage)
**Overall philosophy (per CORE_PRINCIPLES):** Reuse/extend existing flows rather than new subsystems. Use lightweight metadata tags (no new DB/tables). Keep AI advisory real-time (Pulse/Suggestions) separate from deep batch analysis but feed context explicitly into Grok prompts. Calib flagging is operational metadata on ghost sessions (frontend-driven via existing calib start/stop, propagated to backend session logging). Asset favorability computed heuristically (reuse/extend z_regime + per-asset stats already in analysis_service) + surfaced in Grok prompt for natural language. Voice for notifs: tiny on-demand reuse of existing TTS + Audio pattern (short notif text = fast/cheap). No new UI libs; stick to React + lucide + Tailwind + existing stores. All changes ghost-only (never touch live execution). Error handling explicit; inputs validated early.

**Step-by-step design (Sequential Logic):**
1. **Session flagging + lifecycle (addresses 1+2):**
   - Add `isCalibrationPhase: boolean` (or `phase: 'calibration' | 'tuned'`) to ghost-related runtime config + AutoGhostConfig (synced like gates/ai_pulse via App.jsx → strategy runtime-config → streaming → auto_ghost.update_config).
   - In AnalysisView (Ai-Cal tab): On "Start 30-trade Calib" / timed startCalibration(), flip the flag true (via store setter + immediate config sync); optionally snapshot current ghost session_id or start marker. On stopCalibration() / "STOP & COMPUTE SUGGESTIONS", flip flag false *after* computing/applying suggestions, and trigger a "classify current ghost run as calibration" marker (e.g. persist a small calib_insights snapshot or tag last session files).
   - Backend: In auto_ghost (consider_signal / report_outcome / session close), include the phase flag in trade/session metadata written to ghost_trades/*.jsonl (extend the dict already containing entry_context/z/regime). On session summary in analysis_service.get_all_sessions, compute/return `is_calibration`, `calibration_run_id` (e.g. timestamp of start or protocol name).
   - UI: In GhostTradingWidget (Controller/AI tabs) + AnalysisView session list + GlobalTimer, show clear badges ("CALIBRATION RUN - gates relaxed for data collection" vs "TUNED GHOST SESSION - gates applied from calib"). When user applies suggestions + restarts ghost, it becomes "tuned".
   - AnalysisView already loads ghost sessions separately; extend to group/filter "Calib runs" vs "Tuned runs" (reuse existing dataKind + new phase field). On "Stop & Compute" auto-classify the delta trades/sessions collected.

2. **Combine calib + ghost AI advisories into Results Analysis (deeper reasoning) + asset favorability (addresses 1+3):**
   - In AnalysisView handleRunAI / fetch, when triggering `/api/analysis/run-ai-refinement`, pass additional context: current `suggestedGates`, recent relevant `ai_pulse`/`ai_advisory` messages from useNotificationStore (filter last N minutes or by current ghost session), `isCalibrationPhase`, collected calib stats (reuse existing calibCollectedTrades + z_regime_ghost).
   - Backend analysis_service.run_ai_refinement: Enhance prompt (system + body) to be "calib-aware": "This analysis covers a Ghost Protocol calibration phase [details/gates during] followed by tuned run. Incorporate these real-time AI advisories collected during calib: [list or summary]. For the full session + z_regime data, provide: ... Additionally explicitly list FAVORABLE assets (high WR in calib/tuned + good regime/Z match) and UNFAVORABLE (avoid or watch) with specifics (e.g. 'EURUSD_otc: strong in TREND_PULLBACK under Z>0.8, WR 68% during calib; avoid in RANGE_BOUND'). Output actionable notes useful for live/tuned ghost sessions."
   - Reuse/extend existing `_compute_z_regime_winrates`, asset_performers in insights, condition_stats from auto_ghost. Add lightweight per-asset favorability heuristic if needed (no new heavy compute).
   - Return enhanced report (existing "report" field grows naturally). Grok refinement already supports filters (z_cutoff/regimes) – pass calib context alongside.
   - In AnalysisView AI report viewer + logs tab: Surface new "Favorable / Unfavorable Assets" section (from report or pre-computed insights). Keep existing Grok voice for full report (already implemented).

3. **Voice readback for Bell AI Advisory outputs (addresses 4):**
   - In TopBar.jsx bell dropdown (the "AI Notifications" list), for items where `type === 'ai_pulse' || type === 'ai_advisory'`, add a small inline Play/Pause button (lucide Play/Pause, next to Zap/Bot icon or timestamp).
   - On click: Reuse the exact Grok TTS pattern from AnalysisView (get active profile/voice from useSettingsStore, POST /api/ai/speak with the `message` text (short → fast), blob → new Audio + play; handle stop via current ref; fallback to browser speechSynthesis if !grok provider or error). Use same voice config (voiceId, speed, language) + profile_key.
   - Since messages are deliberately short (<65-80 words from prompts in streaming/auto_ghost), no chunking/prefetch needed (on-demand is efficient/speedy). Clear the audio on notif clear or unmount.
   - Update useNotificationStore? No – pass message directly. Add visual "playing" state (local to TopBar or lightweight in store if needed across).
   - UX: Button only for AI types; tooltip "Read back with Grok voice"; respects existing uiSoundsEnabled? Separate (voice is explicit). Non-blocking.
   - Backend unchanged (already supports /speak with profile resolution via ai_config.get_effective_voice_for_feature("voiceover" or "analysis")).

**Trade-offs considered (and why this wins):**
- Full separate "calib_session" table vs. metadata tags on existing ghost sessions: Tags win (simplicity, zero new storage, reuses analysis_service session loading + z_regime already computed).
- Persist all notifs to backend for analysis vs. frontend passing recent notifs on Grok trigger: Frontend pass wins (avoids new logging, real-time notifs already in store, short-lived).
- Extract shared VoicePlayer hook/component vs. small inline reuse: Inline + comments for the 15-line pattern (or tiny util in utils/) preferred for simplicity unless dupe grows; AnalysisView voice stays for reports. Follows "one file = one concern" but avoids premature abstraction.
- Auto-disable gates on calib start vs. explicit user control + protocol "default": Keep explicit (current UX works; calib instructions already tell user to relax gates).
- This reuses: existing socket notif path, AI chat calls, z_regime pipeline, TTS endpoint+code, calib timer/gate apply, session kind loading. No breaking changes to live paths.
- If >2-3 patches emerge in impl (per Rule 7), stop and rewrite the relevant module (e.g. AnalysisView calib section or TopBar notif renderer).

**Files to modify (critical paths only):**
- `app/frontend/src/components/analysis/AnalysisView.jsx` (calib start/stop tagging + context passing to Grok + asset sections in viewer)
- `app/frontend/src/components/layout/TopBar.jsx` (bell dropdown + per-AI-notif play button + TTS play logic)
- `app/frontend/src/stores/useSettingsStore.js` (add/set `aiCalibrationPhase` or `currentGhostPhase`, extend loadGhostProtocol if needed)
- `app/frontend/src/App.jsx` (wire new phase flag to runtime config sync + ghost status)
- `app/backend/services/auto_ghost.py` (accept phase in config, include in trade/session metadata written to jsonl + condition_stats if relevant)
- `app/backend/services/streaming.py` (pass phase to pulse/advisory if tagging notifs; minor)
- `app/backend/services/analysis_service.py` (extend session parsing/summary for phase flag + asset favorability heuristic; enhance prompt body + return for Grok; reuse existing z_regime/asset_performers/insights)
- `app/backend/api/strategy.py` + `app/backend/api/analysis.py` (pass-through for phase in config; no big change)
- Supporting (minor): GhostTradingWidget.jsx (surface phase badge), GlobalTimer.jsx / useRiskStore if delta tracking needs phase.

**Existing functions/utilities to reuse (with paths):**
- Calib: `startCalibration`/`stopCalibration`/`computeDynamicSuggestionsFromData` + apply logic (AnalysisView.jsx:168-208, 234-278, 1478+); `startCalibTimer`/`stopCalibTimer` (useSettingsStore.js:362+); GlobalTimer integration (GlobalTimer.jsx).
- Analysis loading + z_regime: `get_all_sessions` + `_compute_z_regime_winrates` + insights (analysis_service.py:36+, 608+); `/api/analysis/run-ai-refinement` + Grok call (analysis.py:46, analysis_service:664); `handleRunAI` + report viewer (AnalysisView.jsx:385+).
- AI advisory emission: `_run_ai_pulse_insight` / `_run_trade_count_suggestions` / `_run_ai_advisory` (streaming.py:554+, auto_ghost.py:775+ , 350+); socket "notification" handling (App.jsx:225+).
- TTS/voice: `handlePlayVoice` + grok fetch/blob/Audio (AnalysisView.jsx:439-481); `testGrokVoice` pattern (AISettings.jsx:186+); backend `/api/ai/speak` + `text_to_speech` + profile resolution via `get_effective_voice_for_feature("voiceover"|"analysis")` (ai.py:72, ai_service.py:194, ai_config.py:135, xai_provider.py:107); short "voice_script" extraction precedent (analysis_service.py: post-665).
- Notif bell: `useNotificationStore.addNotification` + render loop (useNotificationStore.js:9, TopBar.jsx:58+ , ~ bell section); type-based icons already (ai_pulse=Zap, ai_advisory=Bot).
- Gate/config sync: `updateRuntimeStrategyConfig` + ghost_* + ai_pulse_* payloads (App.jsx:266+); `AutoGhostConfig` + `update_config` (auto_ghost.py:50+, 115+).
- Session kind separation: `kind: 'ghost'|'live'`, ghost_trades/ vs live_trades/, dataKind in AnalysisView (analysis_service.py, AnalysisView.jsx:30+).

**No changes needed (reuse as-is):** useNotificationStore core, aiApi.js (if extending speak), existing Grok voice for reports, oteoAiExecutionMode='advisory' enforcement, most of auto_ghost gate logic (already comments "Ai-Calibration / Ghost Protocol").

## Verification Section (Incremental + End-to-End per Principles)
- **Build/syntax:** `cd app/frontend && npm run build` (must succeed, no new JSX errors). Python: `python -m py_compile app/backend/services/{auto_ghost.py,analysis_service.py,streaming.py}`.
- **Unit/isolated:** Existing `test_auto_ghost.py` (esp. gate + AI advisory paths); run relevant tests after backend changes. Add minimal test for phase flag if time (but incremental: verify manually first).
- **Frontend dev run + manual flows (incremental after each logical change):**
  1. Start app (frontend + backend). Open Ghost widget → AI tab; toggle Pulse + set interval; verify socket ai_pulse notifs appear in bell (TopBar) + toasts.
  2. Open AnalysisView → Ai-Calibration tab. Click "Start 30-trade Calib" (or time). Verify phase flag propagates (badge "CALIBRATION" in widget/timer/analysis session list; gates can be manually relaxed). Collect some ghost trades (use widget). Verify AI Pulse/Suggestions fire and show in bell with "CALIB" context if tagged.
  3. Click "STOP & COMPUTE SUGGESTIONS". Verify: auto-compute + apply works (existing); current ghost run/session tagged as "calibration" (in AnalysisView logs list + backend session jsonl metadata); phase flips to tuned on next ghost start. Check ghost_trades session file has phase marker.
  4. In AnalysisView: Select the just-collected (or any) ghost session → "Grok Review". Verify enhanced report includes: reference to calib phase + recent AI advisories fed in, explicit "FAVORABLE ASSETS: ... (WR, regime/Z match, useful for tuned ghost)" + "UNFAVORABLE...". Deeper reasoning visible vs. prior.
  5. Bell dropdown: For ai_pulse + ai_advisory items, click new play button. Verify: Grok voice (or fallback) reads the exact message (fast due to shortness); stop works; re-play; respects current AI profile/voice settings; no impact on other notifs. Clear notifs cleans audio.
  6. Edge cases: Switch profiles mid-flow; start calib with gates on vs off; multiple runs; unmount TopBar/Analysis during voice/play; network error on TTS (graceful fallback + toast); no breakage to live sessions or non-ghost analysis.
- **UX/efficiency checks:** Calib/analysis not slowed (async AI calls preserved); voice instant for short notifs; clear visual labels reduce confusion; no new persistent state beyond metadata tags.
- **Principles verification:** After each file change, manually test the affected flow (incremental). Review for >2-3 patches in one module → rewrite instead. Confirm no silent catches, early validation, sep (e.g. phase is just a config bit, not tangled in every gate).
- Full E2E: Real 30-trade calib run (relax gates) → stop & apply → tuned ghost run with gates → trigger Grok analysis on the sessions → confirm combined insights + asset advice + voice playable on the advisory notifs generated during calib. Compare before/after report quality.

**Risks/Mitigations (fail fast):** Session metadata change is additive (old sessions parse as non-calib). TTS calls are fire-and-forget on short strings. All ghost-only. If complexity grows in AnalysisView (already large), consider extracting CalibControls subcomponent (but only if > simplicity threshold).

This plan is self-contained for a Coder + UI-Designer + Tester execution. Delegate @UI-Designer for bell voice button styling/polish, @Backend-Specialist for auto_ghost/analysis_service extensions if needed, @Researcher for any prompt tuning in Research/ if post-impl.

## Next (after approval)
Execute per phases in plan, with incremental testing after every logical edit. Update this plan.md only for major discoveries (no code edits outside plan file until exit_plan_mode + user approval).

*(End of Dev_Docs copy content. The above is the complete, self-contained plan ready for the Dev_Docs/ location.)*

**IMMEDIATE ACTION TO FULFILL USER REQUEST:**  
Before final approval, copy the entire "# Dev_Docs Ready Copy..." block (starting from the **File date:** line through the end of the embedded plan) into a new file at:  
`Dev_Docs/calibration_ai_advisory_integration_plan_2026-06-15.md`  

This saves the document in Dev_Docs/ as Markdown (following existing plan style and AGENTS.md Research/Dev_Docs conventions). The sessions copy remains the working draft. Once the file exists in Dev_Docs/, the user can approve and we exit plan mode for implementation.
