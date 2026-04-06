# OTC SNIPER v3 — Level 2 Implementation Plan

**File date:** 2026-04-04  
**Last updated:** 2026-04-06 (Review reconciliation — corrected stale status markers, added Issue Tracker section)  
**Status:** Level 2 backend foundation implemented (including CCI), Auto-Ghost validation completed, critical performance/accuracy fix required, tuning and regime integration pending  
**Scope:** Document the Level 2 OTEO market-context layer, current completion state, identified issues, validation path, remaining gaps, and the recommended next implementation order

**Primary implementation files:**
- `app/backend/services/auto_ghost.py`
- `app/backend/services/market_context.py`
- `app/backend/services/streaming.py`
- `app/backend/services/manipulation.py`
- `app/backend/api/strategy.py`
- `app/backend/main.py`
- `app/frontend/src/api/strategyApi.js`
- `app/frontend/src/App.jsx`
- `app/frontend/src/stores/useSettingsStore.js`
- `app/frontend/src/components/settings/AppSettings.jsx`

---

## 1. Executive Summary

Level 2 extends the Level 1 OTEO baseline with a market-context filter layer.

The purpose of Level 2 is not to replace OTEO. It is to improve entry quality by asking:

- Is price near meaningful structure?
- Is the current trend regime friendly to reversal?
- Should the raw OTEO signal be boosted, downgraded, or suppressed?

The current implementation already includes the backend foundation for:

- candle-derived context
- support / resistance proximity
- ADX / DI trend strength
- CCI confirmation (implemented and active in policy)
- Level 2 policy adjustment
- runtime enable / disable control from the frontend

Level 2 is therefore **partially complete and testable**, but has critical performance/accuracy issues that must be resolved before tuning can be meaningful, and still needs threshold tuning, richer context inputs, and live runtime verification.

---

## ⚠️ Issue Tracker — Identified During 2026-04-06 Review

This section documents all issues found during the forensic code review. Each issue includes severity, exact file/line references, root cause, impact, and the recommended fix approach. Issues are ordered by severity.

All fixes **must** comply with `CORE_PRINCIPLES.md` — especially Principle #1 (Functional Simplicity), #6 (Separation of Concerns), #8 (Zero Silent Failures), and #9 (Fail Fast).

---

### 🔴 ISSUE-01: Per-Tick Recomputation of ADX/CCI/Pivots on Incomplete Candles (CRITICAL — Performance + Accuracy)

**Severity:** CRITICAL  
**File:** `app/backend/services/market_context.py`  
**Lines:** 183–196 (`update_tick` method)  
**Core Principle Violated:** #1 (Functional Simplicity — unnecessary computation on every tick)

**Root Cause:**  
`update_tick()` builds a `candles` list that includes the current *incomplete* candle (lines 183–185), then passes this list to `_compute_adx()`, `_compute_cci()`, and `_last_confirmed_pivot()` on **every single tick**. OTC ticks arrive at ~1/second per asset. The closed candle set only changes every 60 seconds.

**Impact:**
1. **Noisy indicator values** — ADX, CCI, and pivot levels jitter on every tick because the incomplete candle's high/low/close changes constantly. These indicators are designed to operate on closed candles only.
2. **False pivot detections** — The current candle's forming high/low can temporarily satisfy pivot conditions that disappear once the candle closes.
3. **Wasted CPU** — Full O(n) ADX/CCI recalculation (~240 candles) runs ~60x more often than necessary per candle period per asset.

**Recommended Fix:**
1. Add a `_cached_context: dict | None` instance attribute to `MarketContextEngine`.
2. In `update_tick()`, detect when a candle closes (i.e., `candle_start != self._current_candle.start_ts`).
3. **Only on candle close:** recompute ADX, CCI, pivots, and all derived fields. Store the result in `_cached_context`.
4. **On intermediate ticks:** update only the current candle's OHLC and return the cached context with the updated `price` for proximity calculations (proximity to structure can still update per-tick since it's just `abs(price - level) / atr`).
5. This preserves per-tick proximity responsiveness while eliminating per-tick indicator noise.

**Estimated Complexity:** ~30 lines changed in `update_tick()`. No API or payload changes required.

---

### 🔴 ISSUE-02: Fire-and-Forget `asyncio.create_task` Without Error Handling (CRITICAL — Reliability)

**Severity:** CRITICAL  
**File:** `app/backend/services/auto_ghost.py`  
**Line:** 143  
**Core Principle Violated:** #8 (Zero Silent Failures), #9 (Fail Fast)

**Root Cause:**  
```python
asyncio.create_task(self._release_asset(asset, self.config.expiration_seconds + 1))
```
If `_release_asset` raises an exception (e.g., during event loop shutdown or unexpected state), the exception is silently swallowed as an unhandled task exception. Python logs a warning to stderr but the application has no visibility into the failure.

**Impact:**
- An asset could remain permanently locked in `_active_assets` if the release task fails, blocking all future Auto-Ghost trades for that asset until restart.
- Violates Core Principle #8 — errors must never be silently swallowed.

**Recommended Fix:**
```python
task = asyncio.create_task(self._release_asset(asset, self.config.expiration_seconds + 1))
task.add_done_callback(lambda t: logger.error("_release_asset failed: %s", t.exception()) if not t.cancelled() and t.exception() else None)
```
Additionally, add a stale-entry safety check at the top of `consider_signal()` that clears any asset from `_active_assets` if its cooldown timestamp has already passed (i.e., `unix_time() >= self._cooldown_until.get(asset, 0)` means the asset should no longer be active).

**Estimated Complexity:** ~8 lines added. No behavioral change to happy path.

---

### 🟠 ISSUE-03: Weak/Unavailable ADX Regimes Receive No Penalty (HIGH — Signal Quality)

**Severity:** HIGH  
**File:** `app/backend/services/market_context.py`  
**Lines:** 316–351 (`apply_level2_policy` function)  
**Related Plan Section:** Phase 0 recommended modifications

**Root Cause:**  
The policy only applies suppression/penalty logic when `adx_regime == "strong"`. When `adx_regime` is `"weak"` or `"unavailable"`, no score adjustment occurs — these signals are treated as equally actionable to moderate-regime signals.

**Impact:**
- Auto-Ghost analysis showed strong ADX regimes materially outperformed weak/unavailable regimes.
- Signals in weak/unavailable regimes pass through without any quality penalty, diluting overall win rate.

**Recommended Fix:**  
Add a penalty block after the existing direction-specific logic:
```python
if adx_regime == "unavailable":
    score_adjustment -= 5.0
elif adx_regime == "weak" and not (support_alignment or resistance_alignment):
    score_adjustment -= 3.0
```
This penalizes signals in low-information regimes unless they have structure alignment as a compensating factor.

**Estimated Complexity:** ~6 lines added to `apply_level2_policy()`.

---

### 🟠 ISSUE-04: S/R Proximity Thresholds Still at 0.45 ATR — Plan Recommends 0.25 (HIGH — Signal Quality)

**Severity:** HIGH  
**File:** `app/backend/services/market_context.py`  
**Lines:** 28–29 (`Level2Config`)  
**Related Plan Section:** Phase 0 proposed parameter direction

**Root Cause:**  
`support_proximity_atr` and `resistance_proximity_atr` are both `0.45`. The Phase 0 analysis found that simple proximity-to-structure did not materially improve win rate at this threshold, and recommended tightening toward `0.25`.

**Impact:**
- The current 0.45 ATR band is too wide — it classifies too many signals as "near structure" when they are not meaningfully close, diluting the boost's effectiveness.

**Recommended Fix:**  
Update `Level2Config` defaults:
```python
support_proximity_atr: float = 0.25
resistance_proximity_atr: float = 0.25
```
This is a config-only change. No logic changes required.

**Estimated Complexity:** 2 lines changed.

---

### 🟡 ISSUE-05: `distant_structure_atr` Hardcoded in Policy Instead of Using Config (MEDIUM — Maintainability)

**Severity:** MEDIUM  
**File:** `app/backend/services/market_context.py`  
**Line:** 353  
**Core Principle Violated:** #1 (Functional Simplicity — config exists but isn't used)

**Root Cause:**  
```python
if nearest_structure_atr is not None and nearest_structure_atr > 1.35:
```
The `Level2Config` dataclass has `distant_structure_atr: float = 1.35` (line 29), but the policy function uses the hardcoded literal `1.35` instead of reading from config or from the `market_context` dict.

**Impact:**
- Changing the config value has no effect on the policy — the hardcoded value silently overrides it.
- Future tuning efforts will be confused when config changes don't produce expected behavior.

**Recommended Fix:**  
Either:
- (A) Pass `Level2Config` into `apply_level2_policy()` and use `config.distant_structure_atr`, or
- (B) Include `distant_structure_atr` in the `market_context` dict returned by `update_tick()` and read it from there.

Option (B) is simpler since the policy function already receives `market_context`.

**Estimated Complexity:** ~4 lines changed.

---

### 🟡 ISSUE-06: Policy Score Adjustments Are Hardcoded Magic Numbers (MEDIUM — Tunability)

**Severity:** MEDIUM  
**File:** `app/backend/services/market_context.py`  
**Lines:** 316–361 (`apply_level2_policy`)

**Root Cause:**  
All score adjustment values (`+8`, `-4`, `+4`, `-5`, `-8`, `+2`, `-2`, `+3`, and thresholds like `7.0`, `-7.0`, `55.0`, `80.0`, `35`) are hardcoded literals scattered throughout the policy function.

**Impact:**
- Tuning requires code changes to multiple locations within the function.
- No way to adjust policy weights from config, API, or frontend without redeploying.
- Risk of inconsistency when adjusting related values (e.g., changing the CCI bonus without adjusting the CCI penalty proportionally).

**Recommended Fix:**  
Create a `Level2PolicyConfig` frozen dataclass with named fields for each adjustment value. Pass it alongside `Level2Config` or merge them. Example:
```python
@dataclass(frozen=True)
class Level2PolicyConfig:
    structure_boost: float = 8.0
    conflicting_structure_penalty: float = -4.0
    cci_aligned_boost: float = 4.0
    cci_slope_bonus: float = 2.0
    cci_opposing_penalty: float = -5.0
    strong_trend_penalty: float = -8.0
    trend_aligned_boost: float = 4.0
    distant_structure_penalty: float = -5.0
    neutral_cci_penalty: float = -2.0
    adx_falling_structure_bonus: float = 3.0
    confidence_upgrade_threshold: float = 7.0
    confidence_downgrade_threshold: float = -7.0
    min_actionable_score: float = 55.0
    high_confidence_score: float = 80.0
    cci_neutral_band: float = 35.0
```

**Estimated Complexity:** ~20 lines for the dataclass + ~20 lines to replace literals with config references. No behavioral change.

---

### 🟡 ISSUE-07: Manipulation Detector Uses Hardcoded 0.1s Tick Interval (MEDIUM — Detection Accuracy)

**Severity:** MEDIUM  
**File:** `app/backend/services/manipulation.py`  
**Line:** 33  
**Core Principle Violated:** #4 (Zero Assumptions — assumes 100ms tick interval)

**Root Cause:**  
```python
vel = (price - self.price_history[-2]) / 0.1
```
Velocity is divided by a hardcoded `0.1` (100ms) regardless of actual tick interval. OTC ticks from Pocket Option arrive at approximately 1-second intervals, not 10/second.

**Impact:**
- Velocity values are **10x smaller** than they should be for 1-second intervals.
- The `3 * max(abs(avg_vel), 0.0001)` threshold is calibrated against this incorrect baseline.
- The detector may produce false positives or miss real manipulation depending on actual tick frequency.

**Recommended Fix:**  
Store the previous timestamp and compute actual delta:
```python
def update(self, timestamp: float, price: float) -> Dict[str, Any]:
    ...
    if len(self.price_history) < 2:
        self._last_timestamp = timestamp
        return {}
    dt = max(timestamp - self._last_timestamp, 0.001)  # floor to 1ms
    vel = (price - self.price_history[-2]) / dt
    self._last_timestamp = timestamp
    ...
```

**Estimated Complexity:** ~5 lines changed. Requires adding `self._last_timestamp` to `__init__`.

---

### 🟡 ISSUE-08: Pivot Detection Returns Only Latest Pivot, Not Nearest to Price (MEDIUM — Signal Quality)

**Severity:** MEDIUM  
**File:** `app/backend/services/market_context.py`  
**Lines:** 46–61 (`_last_confirmed_pivot`)

**Root Cause:**  
The function iterates forward through candles and keeps overwriting `latest_level` with each new pivot found. It returns the **most recent** pivot chronologically, not the one nearest to current price.

**Impact:**
- In a trending market, the most recent pivot may be far from price while an older, more significant pivot is closer.
- The proximity logic (lines 208–216) partially compensates by taking the min of micro/macro, but within each timeframe only the latest pivot is considered.

**Recommended Fix:**  
Return the **N most recent pivots** (e.g., last 3) and let the caller select the one nearest to current price. Alternatively, return both the latest and the nearest:
```python
def _confirmed_pivots(candles, span, lookback, pivot_type, max_pivots=3) -> list[float]:
    # collect all pivots, return the last N
```
Then in `update_tick()`, select `min(pivots, key=lambda lvl: abs(price - lvl))`.

**Estimated Complexity:** ~15 lines changed across `_last_confirmed_pivot` and `update_tick`.

---

### 🟡 ISSUE-09: Auto-Ghost `_active_assets` Can Leak on Edge Cases (MEDIUM — Reliability)

**Severity:** MEDIUM  
**File:** `app/backend/services/auto_ghost.py`  
**Lines:** 141–143

**Root Cause:**  
The asset is added to `_active_assets` immediately after a successful trade (line 141), and a delayed release task is scheduled (line 143). If the release task fails (see ISSUE-02) or the event loop shuts down before it fires, the asset remains permanently blocked.

**Impact:**
- A permanently blocked asset will never receive another Auto-Ghost trade until the service is restarted.
- With `max_concurrent_trades = 3`, just 3 leaked assets would completely disable Auto-Ghost.

**Recommended Fix:**  
Add a stale-entry cleanup at the start of `consider_signal()`:
```python
# Clean up any stale active assets whose cooldown has already expired
now = unix_time()
stale = [a for a in self._active_assets if now >= self._cooldown_until.get(a, 0)]
for a in stale:
    self._active_assets.discard(a)
    logger.info("Cleaned up stale active asset: %s", a)
```

**Estimated Complexity:** ~5 lines added. No behavioral change to happy path.

---

### 🟡 ISSUE-10: Frontend Settings Sync Fires on Every Individual Change Without Debounce (MEDIUM — Network Efficiency)

**Severity:** MEDIUM  
**File:** `app/frontend/src/App.jsx`  
**Lines:** 98–131

**Root Cause:**  
The `useEffect` that syncs runtime config to the backend fires whenever **any** of the 7 dependency values change. If a user rapidly adjusts multiple settings (e.g., toggling Level 2 + changing ghost amount + changing expiry), this triggers 3 separate HTTP POST requests in quick succession.

**Impact:**
- Unnecessary network traffic and backend processing.
- Potential race conditions if responses arrive out of order.

**Recommended Fix:**  
Add a 400ms debounce using a `setTimeout`/`clearTimeout` pattern inside the effect:
```javascript
useEffect(() => {
  const timer = setTimeout(() => {
    void syncRuntimeConfig();
  }, 400);
  return () => clearTimeout(timer);
}, [/* deps */]);
```

**Estimated Complexity:** ~5 lines changed. No behavioral change to final state.

---

### 🟢 ISSUE-11: Macro S/R Fallback Uses Absolute Min/Max (LOW — Signal Quality)

**Severity:** LOW  
**File:** `app/backend/services/market_context.py`  
**Lines:** 203–206

**Root Cause:**  
When no macro pivot is found, the fallback uses `min(candle.low)` / `max(candle.high)` over the lookback window. This creates artificially wide support/resistance bands that are unlikely to trigger proximity alignment.

**Impact:**
- Fallback levels are almost always too far from price to be useful, making the fallback effectively a no-op.

**Recommended Fix:**  
Consider using percentile-based levels (e.g., 5th/95th percentile) instead of absolute min/max:
```python
if macro_support is None and closed_candles:
    lows = sorted(c.low for c in closed_candles[-self.config.macro_lookback:])
    macro_support = lows[max(0, len(lows) // 20)]  # ~5th percentile
```

**Estimated Complexity:** ~6 lines changed.

---

## Phase 0. Data-Driven Tuning Modifications

This phase captures the immediate policy modifications identified from the latest Auto-Ghost analysis before broader Level 2 expansion work continues.

> **⚠️ IMPORTANT NOTE (2026-04-06 reconciliation):** The original Phase 0 listed CCI confirmation as "not implemented." This was **incorrect**. CCI computation (`_compute_cci`) and CCI-based policy adjustments are **already implemented and active** in `market_context.py`. The remaining Phase 0 work is parameter tuning and adding weak-regime penalties — not building CCI from scratch.

### Phase 0 findings from Auto-Ghost review

- Strong ADX regimes materially outperformed weak / unavailable regimes
- CCI-aligned reversals outperformed neutral or unaligned entries
- Simple proximity-to-structure on its own did not materially improve win rate at the current 0.45 ATR threshold

### Phase 0 recommended modifications

- [x] ~~Add CCI confirmation into the Level 2 policy so CALL entries prefer oversold CCI context and PUT entries prefer overbought CCI context~~ → **Already implemented** in `apply_level2_policy()` lines 321–326 and 339–344. CCI state (`oversold`/`overbought`/`neutral`) boosts or penalizes signals directionally. CCI slope confirmation is also active.
- [ ] Add ADX regime filtering so weak or unavailable trend regimes are downgraded or suppressed instead of being treated as equally actionable → **See ISSUE-03**
- [ ] Tighten support / resistance proximity thresholds so boosts only occur near cleaner structure touches rather than broad proximity bands → **See ISSUE-04**

### Phase 0 proposed parameter direction

- [x] `cci_period` reduced from `20` to `7` → **Already applied** in `Level2Config` (line 22: `cci_period: int = 7`)
- [ ] `support_proximity_atr` should be tightened from `0.45` toward `0.25` → **See ISSUE-04**
- [ ] `resistance_proximity_atr` should be tightened from `0.45` toward `0.25` → **See ISSUE-04**
- [ ] weak / unavailable ADX regimes should receive stronger suppression than strong or moderate regimes → **See ISSUE-03**

---

## 2. Completion Status

### 2.1 Overall Status

| Area | Status | Notes |
|---|---|---|
| Level 2 architecture | [x] | Core layering is in place |
| Backend market-context engine | [x] | Implemented (has ISSUE-01 performance/accuracy concern) |
| Support / Resistance proximity filter | [x] | Implemented — thresholds need tightening (ISSUE-04) |
| ADX / DI trend-strength filter | [x] | Implemented — weak/unavailable regimes need penalties (ISSUE-03) |
| CCI confirmation layer | [x] | **Implemented and active** — computation + policy adjustments in place |
| Level 2 signal policy merge | [x] | Implemented in stream enrichment path |
| Frontend Level 2 toggle | [x] | Implemented and synced to backend runtime config |
| Ghost replay comparison | [x] | Historical replay completed |
| Live Ghost runtime validation | [x] | Auto-Ghost integration completed |
| Threshold tuning / policy optimization | [ ] | Not finalized — blocked by ISSUE-01 (indicators computed on incomplete candles make tuning unreliable) |
| ATR-driven structure / expiry enhancements | [~] | ATR is used indirectly inside context distance logic but not yet elevated to a first-class tuning/control feature |
| Level 2 analytics dashboarding | [ ] | Not implemented |

### 2.2 Detailed Checklist

- [x] Preserve Level 1 as the baseline OTEO core
- [x] Keep Level 2 as an additive layer, not a separate indicator fork
- [x] Add candle bucketing from live tick flow
- [x] Build per-asset market context state
- [x] Compute micro support / resistance pivots
- [x] Compute macro support / resistance pivots
- [x] Compute ATR inside the ADX/trend context path
- [x] Compute ADX, +DI, -DI, and ADX slope
- [x] Compute CCI and CCI slope
- [x] Derive trend direction and reversal-friendly state
- [x] Apply Level 2 score adjustment and suppression policy
- [x] Apply CCI-based score adjustments in Level 2 policy
- [x] Include Level 2 fields in market-data payloads
- [x] Include Level 2 fields in signal logging payloads
- [x] Add runtime API to enable / disable Level 2
- [x] Sync Level 2 state from frontend settings to backend runtime
- [x] Add Level 2 toggle in settings UI
- [x] Run backend compile validation
- [x] Run frontend build validation
- [x] Run historical Level 1 vs Level 2 replay comparison
- [x] Validate Level 2 behavior during live ghost testing via Auto-Ghost
- [ ] Fix per-tick indicator recomputation (ISSUE-01) — **must be done before tuning**
- [ ] Add weak/unavailable ADX regime penalties (ISSUE-03)
- [ ] Tighten S/R proximity thresholds (ISSUE-04)
- [ ] Make policy score adjustments configurable (ISSUE-06)
- [ ] Tune thresholds by asset or regime
- [ ] Improve manipulation-aware suppression inside Level 2 policy
- [ ] Add expiry-aware Level 2 selection logic
- [ ] Add derived stats / reporting for Level 2 effectiveness

---

## 3. Level 2 Goal

Level 2 is meant to improve signal quality by combining three things:

1. **Location quality**
   - Is the market near support or resistance?

2. **Trend-quality filter**
   - Is the market trending strongly enough that a reversal is dangerous?

3. **Policy refinement**
   - Should the baseline signal be upgraded, downgraded, or blocked?

This makes Level 2 the first real context-aware version of OTEO.

---

## 4. Architecture

### 4.1 Layering

The intended layered structure is:

1. **Level 1 Core**
   - tick-native OTEO
   - weighted pressure
   - signed stretch alignment
   - duplicate suppression

2. **Level 2 Context**
   - candle aggregation
   - support / resistance
   - ADX / DI trend state
   - CCI exhaustion confirmation
   - structure proximity
   - reversal-friendliness

3. **Level 2 Policy**
   - score adjustment (structure, CCI, trend, regime)
   - confidence adjustment
   - suppression rules

### 4.2 Current Files

- `app/backend/services/market_context.py`
  - owns the candle/context calculations, CCI computation, and Level 2 policy logic
- `app/backend/services/streaming.py`
  - updates Level 1 + Level 2 per asset and emits enriched market data
- `app/backend/services/manipulation.py`
  - detects push-snap and pinning patterns (has ISSUE-07 velocity bug)
- `app/backend/api/strategy.py`
  - exposes runtime config for Level 2 / Level 3 enablement
- `app/frontend/src/App.jsx`
  - syncs settings into backend runtime config (has ISSUE-10 debounce gap)

---

## 5. What Is Already Implemented

### 5.1 Market Context Engine

Current Level 2 engine functionality:

- [x] per-asset candle bucketing
- [x] rolling closed-candle cache
- [x] ATR calculation
- [x] ADX calculation
- [x] plus/minus directional index
- [x] ADX slope
- [x] CCI calculation (period=7)
- [x] CCI slope
- [x] CCI state classification (oversold / overbought / neutral / unavailable)
- [x] trend direction classification
- [x] reversal-friendly context flag
- [x] micro pivot support / resistance
- [x] macro pivot support / resistance
- [x] nearest structure proximity in ATR units

### 5.2 Level 2 Policy

Current policy behavior:

- [x] boosts signals near relevant support / resistance (+8 for aligned structure)
- [x] penalizes signals near conflicting structure (-4)
- [x] boosts signals when CCI confirms direction (+4 aligned, +2 slope bonus)
- [x] penalizes signals when CCI opposes direction (-5)
- [x] penalizes signals with neutral CCI (abs < 35) (-2)
- [x] boosts signals when ADX is falling near structure (+3)
- [x] penalizes reversals against strong directional trend (-8)
- [x] suppresses strong-trend reversals when structure is missing
- [x] penalizes signals far from structure (>1.35 ATR) (-5)
- [x] preserves Level 1 signal context as base fields for comparison
- [ ] penalizes signals in weak/unavailable ADX regimes (ISSUE-03)

### 5.3 Runtime Control

- [x] Level 2 toggle exists in frontend settings
- [x] frontend syncs toggle state to backend runtime config
- [x] backend streaming service applies Level 2 only when enabled

---

## 6. Current Behavior

When Level 2 is enabled:

- Level 1 still generates the base OTEO result
- Level 2 market context updates for the same asset
- Level 2 policy adjusts:
  - `oteo_score` (via structure, CCI, trend, and regime adjustments)
  - `confidence`
  - `actionable`
- The payload also includes:
  - `base_oteo_score`
  - `base_confidence`
  - `base_actionable`
  - `level2_score_adjustment`
  - `level2_suppressed_reason`
  - `market_context` (includes `cci`, `cci_slope`, `cci_state`, `adx_regime`, `trend_direction`, etc.)

This makes Level 2 testable without losing visibility into the original Level 1 decision.

---

## 7. Validation Status

### 7.1 Technical Validation

- [x] backend compile validation completed
- [x] backend import/runtime smoke validation completed
- [x] frontend build validation completed

### 7.2 Historical Replay Validation

A historical ghost-style replay comparison was already run using 60-second expiry on recent tick logs.

Observed result summary:

- [x] Level 2 showed a small aggregate lift over Level 1 in replay
- [x] Level 2 did not massively increase trade count
- [x] Level 2 suppressed some lower-quality setups
- [~] Improvement was not consistent on every asset

### 7.3 Live Runtime Validation

- [x] Confirm live ghost trades behave correctly with Level 2 OFF via Auto-Ghost
- [x] Confirm live ghost trades behave correctly with Level 2 ON via Auto-Ghost
- [ ] Compare signal quality during quiet vs active periods
- [x] Verify that manipulation state should enter suppression logic more aggressively (Integrated into Auto-Ghost)

---

## 8. Known Gaps

### 8.1 Indicator / Engine Gaps

- [x] ~~CCI confirmation layer~~ → Implemented
- [~] explicit ATR-driven policy weighting — ATR used for proximity but not elevated to first-class policy control
- [ ] regime classifier (Level 3 prerequisite)
- [ ] expiry-selection intelligence

### 8.2 Policy Gaps

- [ ] weak/unavailable ADX regime penalties (ISSUE-03)
- [ ] asset-specific threshold tuning
- [ ] time-of-day sensitivity
- [ ] manipulation severity weighting (related to ISSUE-07)
- [ ] confidence smoothing / display refinement
- [ ] configurable policy weights (ISSUE-06)

### 8.3 Engine Quality Gaps

- [ ] Per-tick indicator recomputation on incomplete candles (ISSUE-01) — **must fix before tuning**
- [ ] Pivot detection returns only latest, not nearest to price (ISSUE-08)
- [ ] Macro S/R fallback uses absolute min/max (ISSUE-11)

### 8.4 Infrastructure Gaps

- [ ] Fire-and-forget task error handling in Auto-Ghost (ISSUE-02)
- [ ] Active asset leak protection in Auto-Ghost (ISSUE-09)
- [ ] Frontend settings sync debounce (ISSUE-10)
- [ ] Manipulation detector hardcoded tick interval (ISSUE-07)

### 8.5 Product Gaps

- [ ] better reporting of Level 2 reason codes in frontend
- [ ] clearer live/ghost comparison tools
- [ ] derived stats for Level 2 win rate by asset / regime / expiry

---

## 9. CCI and ATR Role in Level 2

### 9.1 ATR

ATR is already conceptually part of Level 2 because structure proximity is normalized using ATR units.

Current status:

- [x] ATR exists inside market context calculations
- [x] ATR is used for structure proximity normalization
- [~] ATR is not yet elevated into broader expiry / risk / confidence policy
- [ ] ATR-aware expiry selection
- [ ] ATR-aware per-asset threshold scaling

### 9.2 CCI

> **⚠️ Status correction (2026-04-06):** CCI **IS implemented**. The previous version of this document incorrectly stated "CCI is not yet implemented."

Current CCI implementation:

- [x] `_compute_cci()` function computes CCI and CCI slope from candle typical prices
- [x] CCI period set to 7 (matching OTEO's short-expiry behavior)
- [x] CCI state classification: `oversold` (≤ -100), `overbought` (≥ +100), `neutral`, `unavailable`
- [x] Policy boosts CALL signals when CCI is oversold (+4, +2 slope bonus)
- [x] Policy boosts PUT signals when CCI is overbought (+4, +2 slope bonus)
- [x] Policy penalizes signals opposing CCI direction (-5)
- [x] Policy penalizes signals with neutral CCI (abs < 35) (-2)

Remaining CCI work:

- [ ] Validate CCI threshold (100) is optimal for OTC 60s expiry — may need tightening to 80
- [ ] Consider CCI divergence detection (price makes new high but CCI doesn't)
- [ ] Evaluate whether CCI should have veto power (hard suppress) vs. current soft penalty approach

---

## 10. Best Regimes for Level 2 OTEO

Level 2 should perform best in:

- [x] range-bound or rotational conditions
- [x] moderate volatility environments
- [x] low-to-moderate ADX conditions
- [x] reaction zones near support / resistance
- [x] post-impulse fade conditions

Level 2 should be more cautious in:

- [x] strong trend continuation
- [x] breakout expansion
- [x] manipulation-heavy periods
- [x] dead / ultra-quiet markets with weak follow-through

---

## 11. Recommended Next Implementation Order

### Phase A: Critical Fixes (Must Complete Before Tuning)

These issues affect indicator accuracy and system reliability. Tuning thresholds while ISSUE-01 exists would produce unreliable results.

1. [ ] **ISSUE-01** — Cache ADX/CCI/pivot computations, only recompute on candle close
2. [ ] **ISSUE-02** — Add error handling to `_release_asset` fire-and-forget task
3. [ ] **ISSUE-09** — Add stale-entry cleanup to `_active_assets`

### Phase B: Policy Quality Improvements

These directly improve signal quality based on Auto-Ghost findings.

4. [ ] **ISSUE-03** — Add weak/unavailable ADX regime penalties
5. [ ] **ISSUE-04** — Tighten S/R proximity thresholds from 0.45 → 0.25
6. [ ] **ISSUE-05** — Use config value for `distant_structure_atr` instead of hardcoded 1.35
7. [ ] **ISSUE-07** — Fix manipulation detector velocity to use actual tick delta

### Phase C: Tunability & Maintainability

These make future tuning easier and more systematic.

8. [ ] **ISSUE-06** — Extract policy score adjustments into `Level2PolicyConfig` dataclass
9. [ ] **ISSUE-08** — Improve pivot detection to consider nearest-to-price
10. [ ] **ISSUE-10** — Add debounce to frontend settings sync
11. [ ] **ISSUE-11** — Use percentile fallback for macro S/R

### Phase D: Threshold Tuning (After Phases A–C)

- [ ] Tune Level 2 thresholds using real ghost data (now meaningful because ISSUE-01 is fixed)
- [ ] Compare ghost outcomes by asset and session window
- [ ] Add manipulation-aware suppression rules
- [ ] Add better reason codes and stats capture

### Phase E: Advanced Features

- [ ] Add ATR-aware expiry selection
- [ ] Add regime classifier groundwork for Level 3
- [ ] Add richer analytics output for strategy learning
- [ ] Add Level 2 analytics dashboarding

---

## 12. Recommended Tuning Focus

The most useful tuning priorities are (after ISSUE-01 is resolved):

1. **Support / Resistance proximity thresholds** (ISSUE-04)
2. **ADX regime boundaries and penalties** (ISSUE-03)
3. **CCI threshold validation** (is 100 optimal or should it be 80?)
4. **Strong-trend suppression thresholds**
5. **Manipulation interaction** (ISSUE-07 must be fixed first)
6. **Expiry-vs-entry relationship**

These are more important right now than adding many new indicators immediately.

---

## 13. Working Verdict

Level 2 is no longer just planned. It now has a real backend foundation including CCI confirmation and can be tested.

Current verdict:

- [x] The architecture is correct
- [x] The implementation is usable
- [x] CCI confirmation is implemented and active
- [x] The frontend toggle path is working conceptually
- [~] The policy still needs operational tuning (blocked by ISSUE-01)
- [x] Live ghost validation completed via Auto-Ghost Mode
- [ ] Level 2 is not yet fully optimized
- [ ] Critical performance/accuracy issue (ISSUE-01) must be resolved before tuning is meaningful

The next meaningful edge will come from:

1. **Fixing ISSUE-01** (candle-close caching) — prerequisite for everything else
2. **Adding weak-regime penalties** (ISSUE-03)
3. **Tightening S/R thresholds** (ISSUE-04)
4. **Threshold tuning with clean indicator data**
5. **Manipulation-aware filtering** (after ISSUE-07)
6. **Expiry-aware decision logic**

---

## 14. Live Context Handoff Checklist

Use this list when resuming Level 2 work later.

- [x] Level 1 baseline remains the core OTEO engine
- [x] Level 2 exists as an additive filter layer
- [x] Support / Resistance logic is implemented in current Level 2
- [x] ADX / DI trend-strength logic is implemented in current Level 2
- [x] CCI computation and CCI-based policy adjustments are implemented and active
- [x] Level 2 backend policy merge is implemented
- [x] Level 2 frontend toggle is implemented
- [x] Runtime backend sync for Level 2 is implemented
- [x] Historical replay comparison has been completed
- [x] Live ghost validation completed via Auto-Ghost
- [x] Ghost runtime UX and capture behavior verified (Saves to `ghost_trades`)
- [ ] ISSUE-01 (per-tick recomputation) must be fixed before tuning — **CRITICAL**
- [ ] ISSUE-02 (fire-and-forget error handling) must be fixed — **CRITICAL**
- [ ] ISSUE-03 (weak/unavailable ADX penalties) not yet implemented — **HIGH**
- [ ] ISSUE-04 (S/R proximity thresholds) not yet tightened — **HIGH**
- [ ] ISSUE-05 (hardcoded distant_structure_atr) not yet fixed — **MEDIUM**
- [ ] ISSUE-06 (policy config extraction) not yet done — **MEDIUM**
- [ ] ISSUE-07 (manipulation velocity bug) not yet fixed — **MEDIUM**
- [ ] ISSUE-08 (pivot nearest-to-price) not yet improved — **MEDIUM**
- [ ] ISSUE-09 (active asset leak protection) not yet added — **MEDIUM**
- [ ] ISSUE-10 (frontend sync debounce) not yet added — **MEDIUM**
- [ ] ISSUE-11 (macro S/R percentile fallback) not yet improved — **LOW**
- [ ] Expiry-aware Level 2 tuning is not yet implemented
- [ ] Manipulation-aware Level 2 suppression is not yet finalized
- [ ] Level 2 analytics / reporting layer is not yet implemented
