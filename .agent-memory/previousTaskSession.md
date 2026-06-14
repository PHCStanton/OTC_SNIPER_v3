## Ai-Calibration + Ghost Protocol Implementation Session (2026-06-13)

This session implemented the Ai-Calibration tab and Ghost Protocol system. Core goals: add Z-Score + Regime Detection Gates as extra confluences directly in the Ghost Controller's Controller Settings; create a dedicated 3rd tab called `Ai-Calibration`; introduce a user-calibratable "Ghost Protocol" (customisable strategy profiles for the Ghost Trader only) with one-click AI-suggested parameter application, calibration runners (N trades or timed), dynamic suggestions from live analysis data, and profile persistence modeled on the existing voice/AI profiles system.

**Key design constraints (strictly followed):**
- AI / gates only ever modify Ghost execution parameters (never user live balance or live trade executions).
- Ghost Trader mirrors the user's account (balance/lot sizing simulation for realism).
- Trades execute exactly as before (Signal Click or Select + Manual).
- Live trader results intentionally will not 100% match Ghost results.
- Protocols are customisable user profiles (create/save/load bundles of gate values + description).

### What was completed — UI Modifications

*   **GhostTradingWidget.jsx (Controller Settings tab inside floating Auto Ghost Controller widget):**
    *   Added full "Z-Score Gate Bounds (Ai-Calibration)" section after Confidence Gate: min/max Z sliders (range -3 to +3, 0.1 steps) with independent enable checkboxes.
    *   Added full "Regime Gate (Ai-Calibration)" section: multi-select clickable chips for `RANGE_BOUND | TREND_REVERSAL | TREND_PULLBACK | STRONG_MOMENTUM | CHOPPY`, plus "Require Regime Stable" checkbox.
    *   Added live "Active Protocol Gates" summary line in the Telemetry tab (shows current Z range + active regimes + stable flag) for immediate visual feedback.
    *   All new controls are fully wired to `useSettingsStore` (destructuring + setters) and update instantly.
    *   Edge-case polish: empty `allowedRegimes` displays "(All regimes allowed if empty)".

*   **AnalysisView.jsx (Analysis panel):**
    *   Renamed the 3rd top-level tab from "AI Refinement" to **Ai-Calibration**.
    *   Inserted a prominent new top-level card at the start of the 'ai' tab content:
        *   Header: "Ai-Calibration — Ghost Protocol" with explanation of safety boundaries.
        *   Active Ghost Protocol selector (dropdown) + "Save Current" button that captures live gate values into a named bundle.
        *   Calibration Run section (fully functional):
            *   "Start 30-trade Calib" and "10 min Timed" buttons (user-spec: N trades or 5-15 min using Global Timer Bar pattern).
            *   In-tab wired state machine: `calibMode`, `calibTarget`, `calibRunning`, `calibStartTrades` (from `useRiskStore.ghostTotalTrades`), `calibStartTime`, `calibElapsedMs`, `calibCollectedTrades`.
            *   Live progress display + percentage (trades delta or stopwatch-style elapsed).
            *   Auto-stop on trade target; manual Stop & Compute; Reset.
            *   Uses local `setInterval` + `useEffect` (mirrors GlobalTimer stopwatch/alert logic).
        *   Dynamic AI Suggested Gates panel:
            *   "Recompute from Analysis" button.
            *   `computeDynamicSuggestionsFromData()` function that reads `currentZRegimeData` (sourced from existing `/api/analysis/sessions` + `analysis_service._compute_z_regime_winrates` containing the 5 optimal cutoffs per regime).
            *   Heuristic derives top-WR regimes for `allowedRegimes`, biases min/max Z around the best cutoff, suggests stable flag.
            *   Displays the four values + explanatory note.
        *   Big one-click apply button: "★ ONE-CLICK APPLY SUGGESTED GATES TO GHOST CONTROLLER".
            *   Calls `useSettingsStore.getState()` setters for all z-score + regime fields (plus a confidence nudge for demo confluence).
            *   Values appear live in the open Ghost widget.
    *   Added supporting React state, `useEffect` for calibration timer, helper functions (`startCalibration`, `stopCalibration`, `resetCalibration`, formatters, progress calc), and import for `useRiskStore`.
    *   References to GlobalTimer stopwatch for timed calibration runs.

*   **useSettingsStore.js:**
    *   New `SETTINGS_DEFAULTS` entries for all gates (`ghostMinZScoreEnabled`, `ghostMinZScore`, `ghostMaxZScoreEnabled`, `ghostMaxZScore`, `ghostAllowedRegimes`, `ghostRequireRegimeStable`) + profile system (`ghostProtocols: null`, `activeGhostProtocol: 'default'`).
    *   Full load/deserialization logic (handles arrays or comma-strings for regimes, merges defaults).
    *   New setters for every gate field + `setGhostProtocols`, `setActiveGhostProtocol`.
    *   `loadGhostProtocol(key)` helper that both activates the profile *and* immediately applies its `gates` object to the live ghost* settings (modeled exactly after `aiProfiles` + `featureProfiles` / voice profile switching).

*   **App.jsx:**
    *   Destructured all new ghost z/regime values from the store.
    *   Added them (with enabled guards) to the `auto_ghost_*` payload object sent on runtime config updates.
    *   Added the new values to the relevant `useEffect` dependency array so changes trigger backend sync.

*   **Minor / discoverability polish:**
    *   Updated some internal links/tooltips that still referenced "AI Refinement" (cosmetic).
    *   Added clear comments and UI text explaining navigation (must enable Auto-Ghost to see widget; gates live in its "Controller Settings" tab; Ai-Calibration is the 3rd tab of the Analysis view).

### What was completed — Backend Modifications

*   **auto_ghost.py:**
    *   Extended `AutoGhostConfig` dataclass with the six new fields (`min_zscore_enabled`, `min_zscore`, `max_zscore_enabled`, `max_zscore`, `allowed_regimes: list[str] | None`, `require_regime_stable`).
    *   Updated `update_config(...)` signature and the big reconstruction block that builds the fresh `AutoGhostConfig`.
    *   Added explicit gate enforcement logic inside `consider_signal()` (immediately after the existing numeric confidence gates, before payout/timeframe checks):
        *   Pulls `z_score`, `regime_label`, `regime_stable` from the already-enriched `oteo_result`.
        *   Min/Max Z checks (when enabled).
        *   Regime membership check (when `allowed_regimes` is non-empty).
        *   Stable requirement check.
        *   All skips are logged with clear "(Ai-Calibration gate)" or "(Ghost Protocol)" markers.
    *   Extended `status()` return dict to expose the six new values (so frontend/backend stay in sync and the widget can reflect them).
    *   Empty / null `allowed_regimes` → treated as "allow all" (no filter applied).

*   **strategy.py:**
    *   Added the six new `auto_ghost_*` fields to `RuntimeStrategyConfigRequest` (including `auto_ghost_allowed_regimes: list[str] | None`).
    *   Forwarded every new field through the `update_runtime_settings(...)` call to the streaming service.

*   **streaming.py:**
    *   Extended `update_runtime_settings(...)` signature with the six new optional parameters.
    *   Passed them through to `self.auto_ghost.update_config(...)`.

*   **App.jsx (frontend sync glue, listed above but critical for round-trip):**
    *   The payload now carries the new gates so that changes made in the widget or one-click apply are persisted to the backend AutoGhostService on the next update cycle.

### Additional / Cross-cutting

*   **Ghost Protocol profile system:** Fully functional save/load of named bundles containing the exact gate values. Persisted via the same Zustand + localStorage mechanism as `aiProfiles`. Load applies gates instantly (one-click style).
*   **Dynamic suggestions source of truth:** Reuses the existing rich z-regime analysis pipeline (`analysis_service`, `/api/analysis/sessions` returning `z_regime_ghost`, the 5 optimal cutoffs per regime) — no new heavy AI call required for the first version.
*   **Calibration data collection:** Directly observes live `ghostTotalTrades` delta (RiskStore) for the "N trades" path and uses a self-contained timer for the timed path. Data naturally flows into the next `fetchData()` / z-regime recompute because ghost trades are already enriched with z/regime at execution time.
*   **Verification performed in-session:** All new UI sections render (confirmed via file reads), store round-trips, backend config accepts/forwards/enforces the gates, empty-regime edge case handled on both sides.
*   **Safety / separation of concerns:** Every change explicitly documents and enforces that only the Ghost path is affected. Live user execution and balance paths are untouched.

### Verification Status

*   **UI renders:** Ghost widget Controller Settings now contains the two new gate sections + telemetry summary. AnalysisView 3rd tab now titled "Ai-Calibration" and contains the full calibration + one-click + profile UI at the top.
*   **Store + sync:** New fields appear in defaults, load logic, setters, App.jsx payload, and backend request models.
*   **Backend enforcement:** Gates are evaluated inside `consider_signal` before any ghost trade is allowed; status dict exposes them.
*   **Profile persistence:** `ghostProtocols` + `loadGhostProtocol` work the same way as the voice/AI profile system.
*   **No breakage:** Existing confidence, manipulation, timeframe, payout, drawdown gates continue to function exactly as before.

### Next Session Targets

*   Hook the calibration timers more deeply into the actual GlobalTimer component (drive its alerts or share elapsed state).
*   Make the "AI Suggested" card call a real lightweight Grok prompt (using the same enriched ghost trade + z_regime_ghost context + KB patterns) instead of the current heuristic.
*   Surface the current active Ghost Protocol gates in additional places (Risk panel, session stats, or a dedicated mini visualizer card).
*   Add end-to-end test that runs a short calibration, applies gates, and verifies ghost execution decisions respect the new Z/regime filters.
*   Document the Ghost Protocol feature in the main Dev_Docs and add a small "How to calibrate" walkthrough.

The flow is now complete and usable: enable Auto-Ghost → open widget → see new gates → go to Analysis → Ai-Calibration tab → run calibration (trades or time) → recompute suggestions from real analysis data → one-click apply → Ghost immediately narrows its entries using the new confluences. All while keeping strict separation from live user trading.
