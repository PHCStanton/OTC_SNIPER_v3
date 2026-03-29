# Active Context

## Current Work
**Phase 6 (Risk Management) — COMPLETE**

Full Risk Manager surface built, reviewed, patched, and verified with a clean production build (1643 modules, 0 errors).

**@Reviewer gate passed.** All 3 MEDIUM issues resolved by @Coder. No blocking issues remain.

## Phase 6 Deliverables — Done

| File | Status | Notes |
|------|--------|-------|
| `app/frontend/src/utils/riskMath.js` | ✅ Created | Pure risk math utility — riskPerTrade, TP target, DD limit, min win rate |
| `app/frontend/src/stores/useRiskStore.js` | ✅ Rewritten | Trade Run tracking, VOID state, Manual Override, summarizeSession() pure function |
| `app/frontend/src/stores/useSettingsStore.js` | ✅ Updated | Added session risk defaults: initialBalance, payoutPercentage, riskPercentPerTrade, drawdownPercent, riskRewardRatio, useFixedAmount, fixedRiskAmount, tradesPerRun, maxRuns |
| `app/frontend/src/stores/useTradingStore.js` | ✅ Updated | Auto Mode wiring — forwards validated outcome + pnl to useRiskStore after each live trade |
| `app/frontend/src/components/risk/VerticalRiskChart.jsx` | ✅ Created | SVG session visualizer — balance bar, TP line, DD line, current balance label |
| `app/frontend/src/components/risk/SessionControls.jsx` | ✅ Created | Mode toggle (Auto/Manual), Add Win/Loss/Void, New Trade Run, Sync, Export, Reset |
| `app/frontend/src/components/risk/TradeRunHistory.jsx` | ✅ Created | W/L/V badge history per Trade Run, click-to-cycle Manual Override, edited indicator |
| `app/frontend/src/components/risk/SessionRiskPanel.jsx` | ✅ Created | Main Phase 6 container — header, stat cards, chart, controls, trade run history |
| `app/frontend/src/components/shared/RiskPlaceholder.jsx` | ✅ Replaced | Now a thin wrapper that renders SessionRiskPanel |

## Key Design Decisions Made (Phase 6)

- **Mandatory terminology locked in:** Trade = single executed trade (WIN/LOSS/VOID), Trade Run = group of consecutive trades, Session = full trading day arc.
- **VOID state:** Recorded but excluded from P&L, win rate, and streak. Increments `sessionVoids` and `totalTrades` only. Does not break streaks.
- **Three modes:** Auto (live SSID), Manual (button entry), Manual Override (click any badge to cycle WIN→LOSS→VOID).
- **`summarizeSession()` pure function:** All session math is recomputed from source data on every mutation — no stale derived state. Correct for financial tracking.
- **`syncStartBalance()` guard:** Only called when `startBalance === 0` (initial sync). JSDoc documents this assumption explicitly.
- **Settings separation:** Risk configuration inputs (balance, payout %, risk %, drawdown %, R:R) live in `useSettingsStore` and will be surfaced in Phase 7 Settings Tab. Phase 6 reads them but does not provide input UI for them.
- **RightSidebar unchanged:** Remains the always-visible ambient pulse (P&L, win rate, streak, drawdown). No duplication with the Risk Manager Tab.
- **Export:** CSV export of full session trade history built into `SessionRiskPanel`.

## Architecture: Three Distinct Surfaces

| Surface | Role |
|---|---|
| **Settings Tab (Phase 7)** | Configure — balance, risk %, payout %, drawdown %, R:R |
| **RightSidebar** | Observe — live ambient pulse, always visible |
| **Risk Manager Tab** | Manage — session command center, visualization, Trade Run tracking |

## Recent Changes
- Implemented full Phase 6 Risk Manager surface (5 new files, 3 updated stores).
- Locked in Trade / Trade Run / Session / VOID terminology in implementation plan (sections 5.5 and 5.6).
- @Reviewer gate passed: 0 critical, 0 high, 3 medium (all fixed), 3 low (deferred to Phase 9).
- @Coder fixed: duplicate `completeCurrentTradeRun` action removed, `syncStartBalance` JSDoc added, dead import removed from `SessionRiskPanel`.
- Production build verified: 1643 modules, 0 errors, JS bundle 273.56 kB.

## Next Steps
1. **Phase 7** — Settings System (SettingsView, AccountSettings, AppSettings, RiskSettings).
   - Risk configuration inputs (balance, payout %, risk %, drawdown %, R:R) move here from `useSettingsStore` defaults.
   - Account settings and app settings clearly separated.
   - Settings changes validated before persistence.
2. **Reviewer gate** — required before Phase 8.

## Blockers
None.

## Environment Notes
- Backend: `cd C:\v3\OTC_SNIPER\app && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload`
- Frontend dev: `cd C:\v3\OTC_SNIPER\app\frontend && npm run dev` → http://localhost:5173
- Frontend build: `npm --prefix C:\v3\OTC_SNIPER\app\frontend run build` → `dist/` (verified ✅)
- Chrome debug port: `CHROME_PORT=9222`
- Ops enabled: `QFLX_ENABLE_OPS=1`
