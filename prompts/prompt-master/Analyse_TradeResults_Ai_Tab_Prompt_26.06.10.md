### REFINED PROMPT FOR ANTIGRAVITY
## Objective
Create a modular and visual "Result Analysis" Panel/Page in the OTC Sniper v3 frontend, accessed via the "Analyze Trade Results" dropdown menu option in app/frontend/src/components/layout/TopBar.jsx. This page will aggregate and process data from ghost trades, sniper (live) trades, tick logs, and signal JSONL logs, feeding them into a Grok 4.3 Expert AI Analyzer API to reduce losses, identify hidden market patterns, suggest optimal parameters, and output visual reports with text-to-speech voice playback support.
## Context
- Stack: React 18, Vite, Tailwind CSS v4 (@tailwindcss/vite), Zustand 5, FastAPI Python backend.
- UI: A dark, gold-accented, glassmorphic aesthetic matching the current design system.
- Trade Session Log Locations:
  - Ghost Trades: `app/data/ghost_trades/sessions`
  - Sniper (Live User) Trades: `app/data/live_trades/sessions`
  - Signals Stream Data: `app/data/signals` (JSONL format with details of ticks and OTEO score metrics)
  - Tick Logs: `app/data/tick_logs` (Raw tick data used for backtesting and analysis)
- References:
  - `Market_Analyzer/dev_docs` for market regime definitions and conditions.
  - `Dev_Docs/backtesting` for OTEO levels and backtest results.
## Target State
1. **Frontend Layout & Routing**:
   - Wired up so clicking "Analyze Trade Results" in `TopBar.jsx` navigates to `activeView === 'analysis'`.
   - Rendered within `MainLayout.jsx` with a modular, tabbed dashboard structure:
     - **Tab 1: Session Logs**: Split view comparing "Ghost Session Results" and "Sniper Session Results" (User's live trades) with list view, pagination, filtering by date/asset, and outcome summaries.
     - **Tab 2: Stats & Insights**: Visual charts (performance over time, best/worst assets by win rate/loss count, win rate by time of day / day of week, win rate by expiration time: 30s vs 1m vs 2m).
     - **Tab 3: AI Signal Refinement & Pattern Recall**: A control panel to run analysis via Grok 4.3 API, detailing Level 1, 2, and 3 confluences, manipulation types, intensity/severity, and suggestions to maximize win rates. Included is a visual report viewer.
2. **Backend API Endpoints (`app/backend/api/analysis.py` or similar)**:
   - Endpoint `GET /api/analysis/sessions` to load and parse sessions from ghost and live paths, generating daily summaries to store in `app/data/ghost_trades/stats` and `app/data/live_trades/stats`.
   - Endpoint `POST /api/analysis/run-ai-refinement` to parse files in `app/data/signals` and `app/data/tick_logs`, feed summaries (using token-efficient templates) into Grok 4.3, and generate a detailed report.
   - Grok 4.3 System Prompt: Prompt instructions designed to produce actionable steps, highlight why losses occurred, identify missing pattern behaviors, and suggest optimal expiration adjustments.
   - Voice API Integration: Audio generation endpoint to convert the AI recommendations to speech, with frontend voice playback controls.
3. **Pattern Memory System**:
   - A lightweight database/file-based recall mechanism to store identified market patterns. Over time, new patterns detected by the AI are saved, queried, and referenced in future advisory checks.
## Scope
- Modify:
  - `app/frontend/src/components/layout/TopBar.jsx` (wire navigation)
  - `app/frontend/src/components/layout/MainLayout.jsx` (add view router state)
  - `app/frontend/src/stores/useLayoutStore.js` (add 'analysis' state)
- New Files:
  - `app/frontend/src/components/analysis/AnalysisView.jsx` (and child components)
  - `app/backend/api/analysis.py` (FastAPI router)
  - `app/backend/services/analysis_service.py` (parsing logs, Grok connection, pattern database, Voice API wrapper)
- Do NOT touch:
  - Critical core logic files in `app/backend/api/strategy.py` or streaming services unless integrating new runtime signals.
## Constraints
- Do not mix unrelated layouts; keep styling unified with the dark theme.
- API keys or secrets MUST be loaded from environment variables (`.env`).
- Autonomy: Ask before running destructive terminal commands or adding database migrations.
## Verification & Acceptance Criteria
- [ ] Backend routes compile successfully.
- [ ] Frontend builds successfully (`npm run build`).
- [ ] Navigation toggles correctly from the TopBar AI dropdown into the modular Analysis view.
- [ ] After building, verify UI layout at 375px and 1440px using the browser agent.
- [ ] Mock or test Grok 4.3 and Voice API responses to ensure the frontend loads summaries, charts, and plays recommendation audio.