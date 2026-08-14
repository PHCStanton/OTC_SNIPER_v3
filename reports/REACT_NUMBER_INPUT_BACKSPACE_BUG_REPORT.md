# React Number Input Backspace / Forced-Zero Bug Report

**Repository:** OTC_SNIPER_v3  
**Date:** 2026-08-14  
**Severity:** UX / functional (blocks normal editing of amount, expiry, and settings numeric fields)  
**Status:** Open — fix prompt prepared for Antigravity Agent  
**Scope:** All controlled `<input type="number">` fields in the frontend (trade panel, ghost widget, settings, shared components)

---

## 1. Problem Statement

In multiple dialog boxes and panels, numeric fields that show amounts, expiry times, and related settings **cannot be cleared with Backspace/Delete**. A leading or residual `0` always remains. The user must select-all and overwrite, or focus and type over the digit. This affects everyday trade entry and configuration workflows.

**User-reported behaviour:**
- Numbered digit inputs always keep a zero in front / cannot erase fully.
- Backspace inside the dialog does not clear the field; only select-and-replace works.

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

When the user deletes the last digit:
1. `e.target.value` becomes `""` (empty string).
2. `Number("")` evaluates to `0`.
3. State is set to `0`.
4. React re-renders the input with `value={0}`.
5. The field immediately shows `0` again — backspace appears broken.

The same pattern appears wherever handlers call `Number(event.target.value)` (or equivalent) before allowing an empty intermediate state.

---

## 3. Confirmed Locations (frontend)

### Primary (trade execution UI — Put / Call panel)

| File | Fields |
|------|--------|
| `app/frontend/src/components/trading/TradePanel.jsx` | `amount`, `duration` |

```jsx
onChange={(event) => setAmount(Number(event.target.value))}
onChange={(event) => setDuration(Number(event.target.value))}
```

Store: `app/frontend/src/stores/useTradingStore.js` (`amount`, `duration`; initial values `20` and `60`).  
`resolveTradeStake` / `validateTradeRequest` already coerce with `Number(...)`, so empty string is safe at submit time.

### Ghost / protocol UI

| File | Fields |
|------|--------|
| `app/frontend/src/components/shared/GhostTradingWidget.jsx` | `ghostAmount`, `ghostMaxTradesPerTimeframe`, `ghostTimeframeSeconds` |
| `app/frontend/src/components/settings/GhostSettings.jsx` | Same pattern: `ghostAmount`, `ghostMaxTradesPerTimeframe`, `ghostTimeframeSeconds` |

### Shared `NumberInput` + consumers

| File | Notes |
|------|--------|
| `app/frontend/src/components/shared/StitchComponents.jsx` | `NumberInput` currently does `onChange(e.target.value)` (string). If any store setter still forces `Number(...)` on every keystroke, empty still collapses to `0`. |
| `app/frontend/src/components/settings/RiskSettings.jsx` | Uses `NumberInput` for balance, payout %, risk %, drawdown, fixed amount, RR, trades/run, max runs |
| `app/frontend/src/components/settings/AppSettings.jsx` | Uses `NumberInput` for warmup/cooldown bars |

### Non-issue for this bug

- `type="range"` sliders (always have a value; not cleared by typing).
- `<select>` expiry dropdowns.

**Audit requirement:** Grep the entire `app/frontend` tree for `type="number"` and for `Number(e.target.value)` / `Number(event.target.value)` and fix every editable digit field, not only the table above.

---

## 4. Solution

### Principle

Allow an **empty string** while the user is editing. Coerce to number only when validating, calculating stake, or submitting a trade/settings payload.

### Recommended onChange pattern

```jsx
onChange={(event) => {
  const raw = event.target.value;
  // Allow empty so Backspace can clear the field
  setAmount(raw === '' ? '' : Number(raw));
}}
```

Same for `duration` and any other free-typed numeric field.

### Shared `NumberInput` (preferred central fix)

Harden `NumberInput` in `StitchComponents.jsx` so all consumers inherit correct behaviour:

```jsx
export function NumberInput({ value, onChange, min, max, step, suffix, icon: Icon }) {
  return (
    <div className="flex h-14 w-full items-center overflow-hidden rounded-lg bg-white shadow-inner">
      <div className="flex h-full w-12 items-center justify-center bg-gray-50 text-gray-400">
        {Icon ? <Icon size={18} /> : <span className="text-lg font-bold">#</span>}
      </div>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value === undefined || value === null ? '' : value}
        onChange={(e) => {
          const raw = e.target.value;
          onChange(raw === '' ? '' : raw); // keep string; parent may Number() on blur/submit
        }}
        className="h-full flex-1 px-4 text-xl font-black text-black outline-none"
      />
      {suffix && (
        <div className="flex h-full items-center bg-gray-100 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500 border-l border-gray-200">
          {suffix}
        </div>
      )}
    </div>
  );
}
```

Store setters used by settings may accept `string | number` and normalize on commit, **or** coerce only when `raw !== ''`:

```js
setInitialBalance: (v) => set({ initialBalance: v === '' ? '' : Number(v) }),
```

Ensure any math helpers (`computeRiskMetrics`, `resolveTradeStake`, etc.) use `Number(x) || 0` (or equivalent) so `''` does not NaN-break the UI.

### TradePanel (mandatory)

Update both amount and duration inputs as in §4 pattern. Preset duration buttons that call `setDuration(60)` etc. remain valid (they pass numbers).

### Validation

Existing checks such as `!(Number(amount) > 0)` already treat empty as invalid — keep that. Do not auto-write `0` back into state while the user is mid-edit.

### Optional polish

- `onBlur`: if value is `''`, restore last valid default (e.g. amount `20`, duration `60`) or leave empty and keep Call/Put disabled.
- Prefer not using `type="number"` alone for currency if locale issues appear later; current fix is sufficient for the backspace bug.

---

## 5. Acceptance Criteria

1. User can fully clear amount and duration fields with Backspace/Delete in TradePanel.
2. User can fully clear simulated amount and other free-typed number fields in Ghost widget and Ghost settings.
3. All `NumberInput`-backed settings fields can be cleared and retyped without a forced zero.
4. Empty amount/duration still disables Call/Put (`canTrade` stays false).
5. Submitting / executing still uses numeric values only when valid (`Number(x) > 0`).
6. No regression on preset chips (5s, 15s, 1M, etc.) or range sliders.
7. Repo-wide grep shows no remaining `onChange={(e) => setX(Number(e.target.value))}` on free-typed number inputs without empty-string handling.

---

## 6. Related Files Checklist

- [ ] `app/frontend/src/components/trading/TradePanel.jsx`
- [ ] `app/frontend/src/stores/useTradingStore.js` (only if setters need to accept `''`)
- [ ] `app/frontend/src/components/shared/GhostTradingWidget.jsx`
- [ ] `app/frontend/src/components/settings/GhostSettings.jsx`
- [ ] `app/frontend/src/components/shared/StitchComponents.jsx` (`NumberInput`)
- [ ] `app/frontend/src/components/settings/RiskSettings.jsx`
- [ ] `app/frontend/src/components/settings/AppSettings.jsx`
- [ ] `app/frontend/src/stores/useSettingsStore.js` (setter coercion audit)
- [ ] Any other `type="number"` under `app/frontend/src`

---

## 7. References

- React controlled components: value must reflect state on every keystroke; intermediate empty state must be representable.
- `Number("") === 0` is the direct cause of the “stuck zero” behaviour.

---

*Report generated for OTC_SNIPER_v3 engineering. Pair with Antigravity Agent fix prompt for implementation.*
