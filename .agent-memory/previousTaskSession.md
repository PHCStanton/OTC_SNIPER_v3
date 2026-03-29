Context condensed for continuation.

We reviewed the codebase and identified Phase 7 settings scope. The user asked us to first inspect `.agents\Reviewer.json`, report back, and then update `Dev_Docs/OTC_SNIPER_v3_Implementation_Plan_26-03-24.md` to reflect Phase 7 modifications, but **not** to implement Phase 7 until explicitly instructed to proceed.

What happened:
- Read the current frontend state:
  - `app/frontend/src/stores/useSettingsStore.js` already contains frontend-persisted settings for OTEO, ghost trading, session risk defaults, and UI preferences.
  - `app/frontend/src/stores/useRiskStore.js` computes session stats and reads settings from `useSettingsStore`.
  - `app/frontend/src/stores/useTradingStore.js` forwards trade outcomes to `useRiskStore` in Auto Mode.
  - `app/frontend/src/stores/useAuthStore.js` handles SSID connect/disconnect only and should remain separate from future Auth0 logic.
  - `app/frontend/src/stores/useLayoutStore.js` already supports `activeView: 'settings'`.
  - `app/frontend/src/components/layout/MainLayout.jsx` currently uses a `SettingsPlaceholder` inline stub.
  - `app/frontend/src/components/layout/TopBar.jsx` already routes to settings via `setActiveView('settings')`.
  - `app/frontend/src/components/auth/ConnectDialog.jsx` is the correct place for SSID connect/disconnect.
  - `app/backend/config.py` already has Chrome/session settings and creates `data/settings` directories.
- Reviewed the legacy reference:
  - `legacy_reference/frontend_reference/components/SettingsView.jsx` showed a monolithic settings page with General, OTEO, Ghost Trading, and Trading Controls sections.
- Then we produced a concrete Phase 7 plan:
  - **Account Settings**: broker/session identity, SSID saved status, balance display, clear saved SSID controls, and an Auth0-ready placeholder card.
  - **App Settings**: OTEO enable + warmup/cooldown, ghost trading, trading controls, and UI preferences.
  - **Risk Settings**: initial balance, payout percentage, risk percent per trade or fixed amount, drawdown, risk:reward ratio, trades per run, max runs per session.
  - Auth0 provision strategy: do not add Auth0 state to `useAuthStore`; reserve a separate `useUserStore` namespace for future user profile/auth state.

Files inspected:
- `app/frontend/src/stores/useSettingsStore.js`
- `app/frontend/src/stores/useRiskStore.js`
- `app/frontend/src/stores/useTradingStore.js`
- `app/frontend/src/stores/useAuthStore.js`
- `app/frontend/src/stores/useLayoutStore.js`
- `app/frontend/src/components/layout/MainLayout.jsx`
- `app/frontend/src/components/layout/TopBar.jsx`
- `app/frontend/src/components/auth/ConnectDialog.jsx`
- `app/backend/config.py`
- `legacy_reference/frontend_reference/components/SettingsView.jsx`
- `.agents/Reviewer.json`

Reviewer report we provided:
- No blockers.
- Medium observation: keep future Auth0 user/profile state out of `useAuthStore`.
- Low observation: `useSettingsStore` setters need validation before Phase 7 UI ships.
- Low observation: remove `SettingsPlaceholder` inline function when Phase 7 replaces it.

Plan doc update already applied:
- `Dev_Docs/OTC_SNIPER_v3_Implementation_Plan_26-03-24.md` was updated to include:
  - Phase 7 with Account / App / Risk tabs
  - Auth0-ready boundary language
  - recommended settings per panel
  - validation checklist
  - updated immediate next actions
- The patch successfully updated the plan file, and the final content reflects those changes.

Important implementation decisions:
- Phase 7 is **plan-only for now**; do not implement settings UI yet.
- Keep `useAuthStore` strictly for SSID connect/disconnect.
- Reserve a `useUserStore.js` for later Auth0 integration.
- Settings should remain frontend/localStorage first; backend persistence is not part of Phase 7.

Most recent user instruction before compaction:
- “Please update the 'Dev_Docs/OTC_SNIPER_v3_Implementation_Plan_26-03-24.md' (see below for file content) to reflect these modifications for phase 7. Then wait for Prompts to proceed. Don't implement Phase 7 before command to Proceed.”

Current status / open next step:
- Wait for the user’s explicit “Proceed” command before implementing Phase 7.
- If they do proceed, the next work would be to build `SettingsView.jsx`, `AccountSettings.jsx`, `AppSettings.jsx`, `RiskSettings.jsx`, validation in `useSettingsStore`, and possibly the `useUserStore.js` stub, while keeping Auth0 integration deferred.

Task progress:
- [x] Read current codebase state (stores, components, layout)
- [x] Review legacy reference for settings patterns
- [x] Analyze what settings are meaningful at this stage
- [x] Design Phase 7 settings architecture
- [x] Update implementation plan document
- [x] Wait for user prompt to proceed