# Active Context

## Current Work
**Phase 4 (Frontend Shell) — COMPLETE**

React + Vite + Tailwind v4 + Zustand frontend shell built, installed, and verified with a clean production build (1624 modules, 0 errors).

**SSID connection workflow validated via frontend**

The Connect Session modal now successfully connects to both DEMO and REAL Pocket Option accounts through the backend session endpoint after the PocketOption constructor signature fix.

## Phase 4 Deliverables — Done

| File | Status | Notes |
|------|--------|-------|
| `app/frontend/package.json` | ✅ Rewritten | React 18, Zustand 5, Tailwind v4, Socket.IO, lucide-react |
| `app/frontend/vite.config.js` | ✅ Created | @vitejs/plugin-react + @tailwindcss/vite + proxy to :8001 |
| `app/frontend/jsconfig.json` | ✅ Created | allowJs + jsx: react-jsx (replaces broken tsconfig.json) |
| `app/frontend/index.html` | ✅ Fixed | Points to src/main.jsx |
| `app/frontend/tailwind.config.js` | ✅ Fixed | Minimal v4 config (theme in CSS @theme block) |
| `app/frontend/src/index.css` | ✅ Created | Tailwind v4 @import + @theme glow design tokens |
| `app/frontend/src/main.jsx` | ✅ Created | React 18 createRoot |
| `app/frontend/src/App.jsx` | ✅ Created | Socket.IO init + check_status polling every 5s |
| `app/frontend/src/api/socketClient.js` | ✅ Created | Socket.IO singleton |
| `app/frontend/src/api/opsApi.js` | ✅ Created | Chrome + session HTTP endpoints |
| `app/frontend/src/api/tradingApi.js` | ✅ Created | Trade execution + history |
| `app/frontend/src/api/streamApi.js` | ✅ Created | focusAsset, watchAssets, onMarketData, onSignal |
| `app/frontend/src/stores/useOpsStore.js` | ✅ Kept | Chrome/session status |
| `app/frontend/src/stores/useLayoutStore.js` | ✅ Kept | Sidebar + view + dashboardMode |
| `app/frontend/src/stores/useAuthStore.js` | ✅ Created | SSID input + connect/disconnect |
| `app/frontend/src/stores/useAssetStore.js` | ✅ Created | Selected asset + OTC list |
| `app/frontend/src/stores/useTradingStore.js` | ✅ Created | Trade form + execution |
| `app/frontend/src/stores/useSettingsStore.js` | ✅ Created | OTEO + ghost + risk + UI prefs |
| `app/frontend/src/stores/useStreamStore.js` | ✅ Created | Ticks + signals + manipulation |
| `app/frontend/src/stores/useRiskStore.js` | ✅ Created | Session P&L + win rate + streak |
| `app/frontend/src/components/layout/MainLayout.jsx` | ✅ Created | Full app shell |
| `app/frontend/src/components/layout/TopBar.jsx` | ✅ Created | Chrome badge + Session badge + Tab toggle |
| `app/frontend/src/components/layout/LeftSidebar.jsx` | ✅ Created | Collapsible nav + asset list |
| `app/frontend/src/components/layout/RightSidebar.jsx` | ✅ Created | Collapsible session risk panel |
| `app/frontend/src/components/shared/TradingPlaceholder.jsx` | ✅ Created | Trading view placeholder |
| `app/frontend/src/components/shared/RiskPlaceholder.jsx` | ✅ Created | Risk view placeholder |
| `app/frontend/src/components/auth/ConnectDialog.jsx` | ✅ Created | SSID connect/disconnect modal |

## Key Design Decisions Made (Phase 4)

- **Tailwind v4**: Uses `@import "tailwindcss"` + `@theme {}` in CSS instead of `theme.extend` in config. The `tailwind.config.js` is minimal (v4 convention).
- **JSX not TSX**: All frontend files are `.jsx`/`.js` per plan spec. `jsconfig.json` replaces `tsconfig.json`.
- **Dark mode**: Driven by `dashboardMode === 'risk'` in `App.jsx` — adds `dark` class to root div. Trading = light, Risk Manager = dark.
- **Socket.IO proxy**: Vite dev server proxies `/api` and `/socket.io` to `http://127.0.0.1:8001`.
- **Status polling**: `App.jsx` emits `check_status` every 5s; `status_update` response updates `useOpsStore`.
- **ConnectDialog**: Opened from TopBar session badge. Supports SSID paste or empty-string auto-reconnect from `.env`.

## API Surface Consumed (Phase 4 → Phase 0 Backend)

```
POST /api/ops/chrome/start      → chromeStart() in opsApi.js
POST /api/ops/chrome/stop       → chromeStop() in opsApi.js
GET  /api/ops/chrome/status     → chromeStatus() in opsApi.js
GET  /api/ops/status            → opsStatus() in opsApi.js
POST /api/session/connect       → sessionConnect(ssid, demo) in opsApi.js
POST /api/session/disconnect    → sessionDisconnect() in opsApi.js
GET  /api/session/status        → sessionStatus() in opsApi.js
GET  /api/session/ssid-status   → sessionSsidStatus() in opsApi.js

Socket.IO emit: check_status    → triggers status_update
Socket.IO recv: status_update   → updates useOpsStore
Socket.IO emit: focus_asset     → streamApi.focusAsset()
Socket.IO emit: watch_assets    → streamApi.watchAssets()
Socket.IO recv: market_data     → streamApi.onMarketData()
Socket.IO recv: signal          → streamApi.onSignal()
```

## Recent Changes
- Removed broken Vite vanilla TypeScript boilerplate (main.ts, counter.ts, style.css, assets/, tsconfig.json).
- Rebuilt frontend scaffold from scratch with correct React + Vite + Tailwind v4 stack.
- All 8 Zustand stores created (2 existing kept, 6 new).
- Full layout shell with TopBar, LeftSidebar, RightSidebar, MainLayout.
- ConnectDialog for SSID management wired to Phase 0 backend.
- Fixed backend session wrapper to pass the required `demo` flag into `PocketOption(ssid, demo)` for the installed Pocket Option API.
- Verified successful frontend SSID connection for both DEMO and REAL accounts.
- Normalized `.env` formatting for `PO_SSID_DEMO` to match canonical env style.
- Production build verified: 1624 modules, 0 errors, 0 vulnerabilities.

## Next Steps
1. **@Reviewer** — review the SSID/backend fix pass and confirm no regressions.
2. Proceed with **Phase 5** (Trading UI).
   - `Sparkline.jsx` — live tick chart
   - `OTEORing.jsx` — signal confidence ring
   - `TradePanel.jsx` — buy/sell controls
   - `TradeHistory.jsx` — recent trades table
   - `MultiChartView.jsx` — multi-asset grid
   - `MiniSparkline.jsx` — compact chart for multi-chart

## Blockers
None. SSID connection is working via the frontend for both account modes.

## Environment Notes
- Backend: `cd C:\v3\OTC_SNIPER\app && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload`
- Frontend dev: `cd C:\v3\OTC_SNIPER\app\frontend && npm run dev` → http://localhost:5173
- Frontend build: `npm run build` → `dist/` (verified ✅)
- Chrome debug port: `CHROME_PORT=9222`
- Ops enabled: `QFLX_ENABLE_OPS=1`
