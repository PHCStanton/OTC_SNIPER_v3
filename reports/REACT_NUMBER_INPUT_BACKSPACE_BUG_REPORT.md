# React Number Input Backspace / Forced-Zero Bug Report & Fix

**Repository:** OTC_SNIPER_v3  
**Date:** 2026-08-14  
**Severity:** UX / functional (blocks normal editing of amount, expiry, and settings numeric fields)  
**Status:** Resolved & Verified  
**Scope:** All controlled `<input type="number">` fields in the frontend (trade panel, ghost widget, settings, shared components)

---

## 1. Problem Statement

In multiple dialog boxes and panels, numeric fields that show amounts, expiry times, and related settings **could not be cleared with Backspace/Delete**. A leading or residual `0` always remained. The user had to select-all and overwrite, or focus and type over the digit. This affected everyday trade entry and configuration workflows.

**User-reported behaviour:**
- Numbered digit inputs always kept a zero in front / could not erase fully.
- Backspace inside the dialog did not clear the field; only select-and-replace worked.

---

## 2. Root Cause

Classic React controlled-input anti-pattern:

```jsx
<input
  type="number"
  value={amount}  // number from state
  onChange={(e) => setAmount(Number(e.target.value))}
/>
```

When the user deleted the last digit:
1. `e.target.value` became `""` (empty string).
2. `Number("")` evaluated to `0`.
3. State was set to `0`.
4. React re-rendered the input with `value={0}`.
5. The field immediately showed `0` again — backspace appeared broken.

Furthermore, in `useSettingsStore.js`, the schema normalization function `toNumber(value, fallback)` immediately returned `fallback` on `""`:
```javascript
// Problematic schema validation:
if (value === '' || value === null || value === undefined) return fallback;
```
This caused any cleared field in `RiskSettings` or `AppSettings` to snap back to its initial default (e.g. `1000` or `0`) on the next keystroke frame.

---

## 3. Confirmed Locations (frontend)

### Primary (trade execution UI — Put / Call panel)
- `app/frontend/src/components/trading/TradePanel.jsx` (`amount`, `duration`)

### Ghost / protocol UI
- `app/frontend/src/components/shared/GhostTradingWidget.jsx` (`ghostAmount`, `ghostMaxTradesPerTimeframe`, `ghostTimeframeSeconds`)
- `app/frontend/src/components/settings/GhostSettings.jsx` (`ghostAmount`, `ghostMaxTradesPerTimeframe`, `ghostTimeframeSeconds`)

### Shared `NumberInput` + consumers
- `app/frontend/src/components/shared/StitchComponents.jsx` (`NumberInput`)
- `app/frontend/src/components/settings/RiskSettings.jsx` (balance, payout %, risk %, drawdown, fixed amount, RR, trades/run, max runs)
- `app/frontend/src/components/settings/AppSettings.jsx` (warmup/cooldown bars)

### AI Settings
- `app/frontend/src/components/settings/AISettings.jsx` (`maxTokens`)

---

## 4. Resolution & Implementation

### A. Number Input Component (`StitchComponents.jsx`)
- Upgraded the shared `NumberInput` component to accept `value ?? ''`.
- Handled empty string gracefully in `onChange`:
  ```jsx
  onChange={(e) => {
    const raw = e.target.value;
    onChange(raw === '' ? '' : Number(raw));
  }}
  ```
- This automatically resolved all inputs in `RiskSettings.jsx` and `AppSettings.jsx`.

### B. Execution Panel (`TradePanel.jsx`)
- Updated `amount` and `duration` fields to allow `""` during user typing.
- Added dynamic symbol switching between `$` (USD mode) and `%` (PCT mode).
- Added an amber-themed calculated stake preview badge (`= $XX.XX`) when `%` mode is active.
- Upgraded the top toggle to a sleek Stitch pill switch (`$ USD` vs `% PCT`).

### C. Ghost Engine (`GhostTradingWidget.jsx` & `GhostSettings.jsx`)
- Updated `ghostAmount`, `ghostMaxTradesPerTimeframe`, and `ghostTimeframeSeconds` inputs to preserve empty strings while editing.

### D. AI Settings (`AISettings.jsx`)
- Updated `maxTokens` input to preserve empty strings during editing.

### E. Store Normalization & Persistence (`useSettingsStore.js` & `useTradingStore.js`)
- `toNumber` now returns `''` when `value === ''`, allowing intermediate typing state.
- `partialize` replaces empty strings with fallback defaults when writing to `localStorage`.
- `resolveTradeStake` and `validateTradeRequest` safely treat empty strings as 0 / unselected without crashing.

---

## 5. Verification & Testing

- **Compilation:** Executed `npm run build` with 0 errors (1,701 modules transformed).
- **Submodule Cleanup:** Safely unlinked the accidental `app/frontend/edex-ui` submodule pointer from Git.
- **Acceptance Criteria Met:** All inputs clear cleanly with Backspace/Delete without forcing `0`.
