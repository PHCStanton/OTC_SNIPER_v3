# SIGNAL_SNIPER Settings Audit, Layout Optimization, and New Feature Specifications
Date: June 5, 2026
Author: Antigravity AI Engineering Team (via @Researcher, @UI-Designer, and @Coder)

---

## 1. Audit: Unwired vs. Wired Settings

Based on forensic investigation of the SIGNAL_SNIPER repository, here is the state of all settings in `SETTINGS_DEFAULTS` (`useSettingsStore.js`):

| Setting Key | Category | Current Status in Frontend / Backend |
|---|---|---|
| **OTEO Engine** | | |
| `oteoEnabled` | OTEO | **Unwired** (Only lives in store, never used to disable signals). |
| `oteoLevel2Enabled` | OTEO | **Wired** (Synchronized with backend strategy api via `App.jsx`). |
| `oteoLevel3Enabled` | OTEO | **Wired** (Synchronized with backend strategy api via `App.jsx`). |
| `oteoWarmupBars` | OTEO / Risk | **Unwired** (Input exists but not sent to backend or used in metrics). |
| `oteoCooldownBars` | OTEO / Risk | **Unwired** (Input exists but not sent to backend or used in metrics). |
| **Ghost Trading** | | |
| `ghostAmount` | Ghost | **Wired** (Synchronized via `App.jsx` -> `auto_ghost_amount`). |
| `autoGhostEnabled` | Ghost | **Wired** (Controls `GhostTradingWidget` render + strategy config sync). |
| `autoGhostCopyMode` | Ghost | **Wired** (Controls toast double-click action in `App.jsx`). |
| `autoGhostExpirationSeconds` | Ghost | **Wired** (Synchronized via `App.jsx` -> `auto_ghost_expiration_seconds`). |
| `autoGhostMaxConcurrentTrades` | Ghost | **Wired** (Synchronized via `App.jsx` -> `auto_ghost_max_concurrent_trades`). |
| `autoGhostPerAssetCooldownSeconds` | Ghost | **Wired** (Synchronized via `App.jsx` -> `auto_ghost_per_asset_cooldown_seconds`). |
| `autoGhostMaxSessionTrades` | Ghost | **Wired** (Synchronized via `App.jsx` -> `auto_ghost_max_session_trades`). |
| `autoGhostMaxDrawdownAmount` | Ghost | **Wired** (Synchronized via `App.jsx` -> `auto_ghost_max_drawdown_amount`). |
| `autoGhostDrawdownCooldownSeconds`| Ghost | **Wired** (Synchronized via `App.jsx` -> `auto_ghost_drawdown_cooldown_seconds`). |
| `autoGhostMinimumPayout` | Ghost | **Wired** (Synchronized via `App.jsx` -> `auto_ghost_minimum_payout`). |
| `ghostWidgetPosition` | Ghost | **Wired** (Draggable coordinate persistence in `GhostTradingWidget.jsx`). |
| `ghostIcon` | Ghost | **Wired** (Avatar asset selection). |
| **Trade Markers** | | |
| `showGhostEntryMarkers` | Chart | **Wired** (Shows/hides ghost dots in `Sparkline.jsx`). |
| `showLiveEntryMarkers` | Chart | **Wired** (Shows/hides live trade dots in `Sparkline.jsx`). |
| **Session Risk Defaults** | | |
| `initialBalance` | Session Risk| **Wired** (Computes risk boundaries in `useRiskStore.js` / `RightSidebar.jsx`). |
| `payoutPercentage` | Session Risk| **Wired** (Computes risk boundaries in `useRiskStore.js` / `RightSidebar.jsx`). |
| `riskPercentPerTrade` | Session Risk| **Wired** (Computes risk boundaries in `useRiskStore.js` / `RightSidebar.jsx`). |
| `drawdownPercent` | Session Risk| **Wired** (Computes risk boundaries in `useRiskStore.js` / `RightSidebar.jsx`). |
| `riskRewardRatio` | Session Risk| **Wired** (Computes risk boundaries in `useRiskStore.js` / `RightSidebar.jsx`). |
| `useFixedAmount` | Session Risk| **Wired** (Toggles fixed vs percent risk in `useRiskStore.js`). |
| `fixedRiskAmount` | Session Risk| **Wired** (Sets absolute stake in `useRiskStore.js`). |
| `tradesPerRun` | Session Risk| **Wired** (Determines risk run completion inside `useRiskStore.js`). |
| `maxRuns` | Session Risk| **Unwired** (Set in `RiskSettings.jsx` but not evaluated in risk runs). |
| **Risk management** | | |
| `maxDailyLoss` | Risk | **Unwired** (Only exists in store). |
| `maxTradesPerSession` | Risk | **Unwired** (Only exists in store). |
| `stopOnLossStreak` | Risk | **Unwired** (Only exists in store). |
| **AI Integration** | | |
| `aiModel` | AI | **Wired** (Controls LLM request model in `useAIStore.js`). |
| **UI Preferences** | | |
| `showManipulationAlerts` | UI | **Unwired** (Only exists in store). |
| `showSignalConfidence` | UI | **Unwired** (Only exists in store). |
| `autoFocusOnSignal` | UI | **Unwired** (Only exists in store). |
| **Data Feeds** | | |
| `assetAutoRefreshEnabled` | Catalog | **Wired** (Triggers refresh intervals in `LeftSidebar.jsx`). |
| `assetAutoRefreshInterval` | Catalog | **Wired** (Sets seconds for catalog refresh in `LeftSidebar.jsx`). |
| **Modular Charts** | | |
| `miniChartConfig` | UI | **Wired** (Toggles charts, sparklines, stats visibility). |
| `uiSoundsEnabled` | Sound | **Wired** (Mutes/unmutes interface clicks in `soundUtils.js`). |
| `tradingSoundsEnabled` | Sound | **Wired** (Mutes/unmutes win/loss chimes in `soundUtils.js`). |
| `showGlobalTimer` | UI | **Wired** (Mutes/unmutes global timer in `MainLayout.jsx`). |

---

## 2. Design Recommendations: Layout Optimization & Decluttering

### A. Core Strategy: Convert Long Descriptions to Tooltips
To remove text clutter and give the panel a premium look, we will remove inline paragraphs from under settings options. Instead, we will add a small hover tooltip trigger (`Info` icon) next to setting labels.
* **Component Implementation**: Add a React `Tooltip` widget to `StitchComponents.jsx` that renders a floating overlay when hovering over the `Info` icon.
* **Visual Polish**: Render tooltips in a sleek, glassmorphic layout (`bg-[#0c0e12]/95 border border-white/10 backdrop-blur-md`) with uppercase tracking.

### B. Group Settings into Functional Columns
Currently, the settings page suffers from vertical stretching. We will optimize the layout by organizing it into a cleaner multi-column schema:
1. **Quick Toggles Row**: (Sounds, Timer, etc.) Retain at the top but style in a unified, space-saving panel.
2. **Left Column (Signal & AI Protocol)**: 
   - *OTEO Engine Layer* (Confidence Levels, Warmup Bars, Cooldown Bars)
   - *AI Integration* (Model Select, Auto-Focus, Signal Confidence)
3. **Right Column (Simulation & Execution Layer)**:
   - *Auto-Ghost Trader* (Simulation Amount, Timeframe Limit, Cooldowns, Minimum Payout, Expiration)
   - *Confidence Gates* (Min/Max Slider Boundaries)
4. **Bottom Row (Modular Chart Config)**: Keep full width for clean grid widgets.

---

## 3. Specification of Additional Settings

### A. Timeframe Ghost Execution Limit
* **Objective**: Introduce a control allowing the user to limit ghost entries per unit of time (e.g. 2 max trades per minute) to protect simulator metrics during high-frequency market spasms.
* **Settings Added to Store**:
  * `ghostMaxTradesPerTimeframe` (default: `2`, range: `1 - 10`)
  * `ghostTimeframeSeconds` (default: `60`, range: `10 - 300`)
* **API Payload Mapping**:
  * `auto_ghost_max_trades_per_timeframe`: `ghostMaxTradesPerTimeframe`
  * `auto_ghost_timeframe_seconds`: `ghostTimeframeSeconds`

### B. Dual-Bounded Confidence Threshold Gate
* **Objective**: Replace the single slider with two range sliders (Minimum and Maximum confidence limits), each accompanied by an independent checkbox toggle to enable/disable that boundary check. This lets users carve out specific signal confidence windows (e.g., execute only between 75% and 95%).
* **Settings Added to Store**:
  * `ghostMinConfidence` (default: `75`, range: `50 - 100`)
  * `ghostMinConfidenceEnabled` (default: `true`)
  * `ghostMaxConfidence` (default: `95`, range: `50 - 100`)
  * `ghostMaxConfidenceEnabled` (default: `false`)
* **API Payload Mapping**:
  * `auto_ghost_min_confidence`: `ghostMinConfidence`
  * `auto_ghost_min_confidence_enabled`: `ghostMinConfidenceEnabled`
  * `auto_ghost_max_confidence`: `ghostMaxConfidence`
  * `auto_ghost_max_confidence_enabled`: `ghostMaxConfidenceEnabled`
