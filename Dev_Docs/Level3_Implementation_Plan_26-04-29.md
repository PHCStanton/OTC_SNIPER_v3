# OTC SNIPER v3 — Level 3 Implementation Plan: Regime-Aware Trading

**File date:** 2026-04-29  
**Status:** Plan — Awaiting explicit approval before implementation  
**Compiled by:** @Investigator (full-stack forensic analysis), @Reviewer (quality assessment), @Architect (regime design)  
**Scope:** Implement Level 3 regime-aware trading: deterministic regime classifier, win-rate optimization features, AI advisory review loop, volatility-adaptive expiry, and frontend visualization  
**Reference documents:**
- `Dev_Docs/Pre_Level3_Critical_Review_26-04-11.md`
- `Dev_Docs/Pre_Level3_Implementation_Summary_26-4-11.md`
- `Dev_Docs/Level2_Implementation_Plan_26-04-04.md`
- `Dev_Docs/OTEO_update_plan_26-03-30.md` (Section 8)
- `app/Ai_Docs/Market_Regimes.md`
- `.agent-memory/activeContext.md`
- `.agent-memory/progress.md`
**CORE_PRINCIPLES:** All changes must comply with `.agents/CORE_PRINCIPLES.md`

---

## 1. Executive Summary

Level 3 is the **Advanced Phase** of the OTEO strategy. It transitions the system from static criteria (Level 1) and isolated market context (Level 2) into **dynamic, regime-aware trading** that automatically adapts its behavior based on the detected market state.

The implementation is organized into **7 phases** executed in strict dependency order:

| Phase | Name | Priority | New Files | Modified Files |
|-------|------|----------|-----------|----------------|
| **Phase 0** | Pre-Implementation Bug Fixes | CRITICAL | 0 | 5 |
| **Phase 1** | Regime Classifier | HIGHEST | 1 | 2 |
| **Phase 2** | Level 3 Signal Policy | HIGH | 0 | 2 |
| **Phase 3** | Win-Rate Optimization Features | HIGH | 0 | 3 |
| **Phase 4** | AI Advisory Review Loop | MEDIUM | 1 | 3 |
| **Phase 5** | Frontend L3 Visualization | MEDIUM | 0 | 3 |
| **Phase 6** | Volatility-Adaptive Expiry | MEDIUM | 0 | 3 |

**Total: 2 new files, ~14 files modified, ~500 lines of new/changed code**

### Design Philosophy

1. **Deterministic first, AI second** — The regime classifier uses existing Level 2 indicators (ADX, CCI, S/R, ATR, DI). AI validates and advises but never overrides.
2. **Additive, not destructive** — Level 3 is a filter layer on top of Level 2, just as Level 2 is a filter on Level 1. All three remain independently testable.
3. **Data-driven tuning** — Per-condition win-rate tracking provides the feedback loop needed for empirical threshold adjustment.
4. **OTEO's sweet spot is exhaustion reversal** — The regime classifier's primary job is to identify when reversals are likely to succeed and when they are dangerous.

---

## 2. Market Regime Definitions

Based on `app/Ai_Docs/Market_Regimes.md` and OTC binary options domain knowledge, Level 3 classifies the market into **6 regimes** using a deterministic decision tree:

### 2.1 Regime Taxonomy

| # | Regime Label | Market Behavior | OTEO Suitability | Default Action |
|---|---|---|---|---|
| 1 | `TREND_PULLBACK` | Clear HH/HL or LH/LL with regular pullbacks. Moderate ADX. | ⚠️ Conditional | Allow trend-aligned entries near structure only |
| 2 | `STRONG_MOMENTUM` | Persistent one-directional move, minimal retracement. High ADX. | 🔴 Dangerous | Suppress or heavily penalize reversal signals |
| 3 | `RANGE_BOUND` | Price oscillates between S/R. No overall direction. Low ADX. | ✅ Ideal | Boost reversal signals near S/R boundaries |
| 4 | `CHOPPY` | Erratic wicks, fake breakouts, no clear structure. | 🔴 Avoid | Suppress all signals — no statistical edge |
| 5 | `BREAKOUT` | Price breaks through S/R with expanding volatility. | 🔴 Dangerous | Suppress until breakout stabilizes |
| 6 | `TREND_REVERSAL` | ADX falling from high, DI crossing, CCI divergence. | ✅ Good | Boost reversal signals aligned with the new direction |

### 2.2 Detection Logic (Deterministic Decision Tree)

Each regime is detected using **thresholds on existing Level 2 data**. No new indicators are needed for the initial classifier.

```
INPUT: market_context dict from MarketContextEngine.update_tick()
  → adx, adx_slope, plus_di, minus_di, cci, cci_slope, cci_state
  → micro_support, micro_resistance, macro_support, macro_resistance
  → nearest_structure_atr, atr, reversal_friendly, trend_direction

DECISION TREE:

1. Is ADX unavailable or candle count < 14?
   → Return "INSUFFICIENT_DATA"

2. Is ATR spiking (current ATR > 1.5 × rolling ATR mean) AND price beyond S/R?
   → "BREAKOUT"

3. Is ADX > 40 AND DI spread > 15?
   → "STRONG_MOMENTUM"

4. Is ADX > 20 AND ADX ≤ 40?
   a. Is ADX_slope < -0.3 AND was ADX recently > 35?
      → "TREND_REVERSAL"
   b. Is price near S/R (nearest_structure_atr < 0.4)?
      → "TREND_PULLBACK"
   c. Otherwise → "TREND_PULLBACK" (moderate trend, pullback expected)

5. Is ADX ≤ 20?
   a. Are S/R levels well-defined (both micro support AND resistance exist)?
      i. Is ATR stable (no spiking) AND CCI cycling between extremes?
         → "RANGE_BOUND"
      ii. Otherwise → "CHOPPY"
   b. No clear S/R structure?
      → "CHOPPY"

DEFAULT: "RANGE_BOUND" (conservative fallback — OTEO reversal bias)
```

### 2.3 Regime Confidence Score

Each regime classification also produces a **confidence score (0-100)** indicating how clearly the market matches the regime pattern:

| Factor | Weight | Description |
|--------|--------|-------------|
| ADX clarity | 30% | How far ADX is from the boundary thresholds |
| DI spread | 20% | Directional strength clarity |
| S/R structure quality | 20% | Both micro and macro levels exist and are well-separated |
| CCI alignment | 15% | CCI state matches the expected pattern for the regime |
| ATR stability | 15% | Consistent vs erratic volatility |

---

## 3. Pre-Implementation Issue Tracker

These issues from the `Pre_Level3_Critical_Review` **must be resolved before** Level 3 logic is added.

### 3.1 Issues to Fix in Phase 0

| # | Severity | Issue | File | Fix |
|---|----------|-------|------|-----|
| C1 | 🔴 CRITICAL | `strategy_level` tagging broken — `oteo_result` never contains `level3_enabled` | `auto_ghost.py:247` | Inject `level3_enabled` into enriched result in `_process_tick_inner()` |
| M2 | 🟠 MODERATE | Live trade outcome tracking has no exception callback | `trade_service.py:311` | Add `.add_done_callback()` matching `auto_ghost.py` pattern |
| M3 | 🟠 MODERATE | `candle_closed = True` on first tick — triggers premature indicator recompute | `market_context.py:196` | Set `candle_closed = False` on first candle creation |
| M4 | 🟠 MODERATE | Macro S/R fallback uses absolute min/max — produces false regime labels | `market_context.py:229-232` | Upgrade to 10th/90th percentile fallback |
| M5 | 🟠 MODERATE | `distant_structure_atr` hardcoded `1.35` in policy instead of config | `market_context.py:409` | Include `distant_structure_atr` in `market_context` dict or pass config |

---

## 4. Implementation Phases

### Phase 0: Pre-Implementation Bug Fixes (CRITICAL)

**Priority:** CRITICAL — Must complete before any Level 3 logic  
**Addresses:** ISSUE-C1, M2, M3, M4, M5  
**Estimated complexity:** ~40 lines across 3 files

#### 0.1 — Fix `strategy_level` tagging (ISSUE-C1)

**File:** `app/backend/services/streaming.py`

In `_process_tick_inner()`, inject `level3_enabled` into the enriched result dict before it reaches Auto-Ghost:

```python
# After applying Level 2 policy
if self.level2_enabled:
    oteo_result = apply_level2_policy(oteo_result, market_context)

# Inject level flags for downstream consumers (Auto-Ghost strategy tagging)
oteo_result["level2_enabled"] = self.level2_enabled
oteo_result["level3_enabled"] = self.level3_enabled
```

This ensures `auto_ghost.py:247` correctly reads `oteo_result.get("level3_enabled")`.

#### 0.2 — Add exception callback to live trade tracking (ISSUE-M2)

**File:** `app/backend/services/trade_service.py`

```python
task = asyncio.create_task(self._track_trade_outcome(trade_record, adapter, request.expiration))
task.add_done_callback(
    lambda t: logger.error("_track_trade_outcome failed: %s", t.exception())
    if not t.cancelled() and t.exception() else None
)
```

#### 0.3 — Fix first-tick candle_closed semantics (ISSUE-M3)

**File:** `app/backend/services/market_context.py`

```diff
 if self._current_candle is None:
     self._current_candle = Candle(candle_start, price, price, price, price)
-    candle_closed = True
+    candle_closed = False  # First candle is just created, not closed
```

#### 0.4 — Upgrade macro S/R fallback to percentile-based (ISSUE-M4)

**File:** `app/backend/services/market_context.py`

```python
if macro_support is None and closed_candles:
    lows = sorted(c.low for c in closed_candles[-self.config.macro_lookback:])
    macro_support = lows[max(0, len(lows) // 10)]  # ~10th percentile

if macro_resistance is None and closed_candles:
    highs = sorted(c.high for c in closed_candles[-self.config.macro_lookback:])
    macro_resistance = highs[min(len(highs) - 1, len(highs) * 9 // 10)]  # ~90th percentile
```

#### 0.5 — Wire `distant_structure_atr` from config (ISSUE-M5)

**File:** `app/backend/services/market_context.py`

Include the config value in the `market_context` dict returned by `update_tick()`:

```python
context = {
    # ... existing fields ...
    "distant_structure_atr_threshold": self.config.distant_structure_atr,
}
```

Then in `apply_level2_policy()`, replace the hardcoded `1.35`:

```diff
-if nearest_structure_atr is not None and nearest_structure_atr > 1.35:
+distant_threshold = market_context.get("distant_structure_atr_threshold", 1.35)
+if nearest_structure_atr is not None and nearest_structure_atr > distant_threshold:
```

---

### Phase 1: Regime Classifier Module (HIGHEST)

**Priority:** HIGHEST — Core of Level 3  
**New file:** `app/backend/services/regime_classifier.py`  
**Estimated complexity:** ~180 lines

#### 1.1 — Create `RegimeClassifier` class

**File:** `app/backend/services/regime_classifier.py` (NEW)

```python
"""
Deterministic market regime classifier.

Uses Level 2 market context data (ADX, CCI, S/R, ATR, DI) to assign
a regime label and confidence score to the current market state.

Regime taxonomy aligned with app/Ai_Docs/Market_Regimes.md:
  1. TREND_PULLBACK     — Trending with regular pullbacks
  2. STRONG_MOMENTUM    — Persistent one-directional move
  3. RANGE_BOUND        — Oscillating between S/R
  4. CHOPPY             — Erratic, no clear structure
  5. BREAKOUT           — Price breaking through S/R
  6. TREND_REVERSAL     — Direction changing
  7. INSUFFICIENT_DATA  — Not enough candles for classification
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegimeConfig:
    """Tunable thresholds for regime classification."""
    # ADX boundaries
    strong_momentum_adx: float = 40.0
    trend_pullback_adx_min: float = 20.0
    range_bound_adx_max: float = 20.0
    
    # DI spread
    strong_momentum_di_spread: float = 15.0
    
    # ADX slope for reversal detection
    reversal_adx_slope: float = -0.3
    reversal_prior_adx_min: float = 35.0
    
    # ATR breakout multiplier
    breakout_atr_multiplier: float = 1.5
    
    # S/R proximity for pullback detection
    pullback_structure_atr: float = 0.4
    
    # Minimum candles for classification
    min_candles: int = 14
    
    # Regime persistence — how many candle closes a regime must hold
    # before it's considered stable (reduces regime flapping)
    persistence_candles: int = 3
    
    # ATR rolling window for breakout detection
    atr_rolling_window: int = 10


@dataclass
class RegimeState:
    """Current regime classification result."""
    label: str = "INSUFFICIENT_DATA"
    confidence: float = 0.0
    prior_label: str | None = None
    persistence_count: int = 0
    detail: dict = field(default_factory=dict)


class RegimeClassifier:
    """
    Deterministic market regime classifier.
    
    Called once per closed candle (not per tick) to classify the current
    market state. Uses the same caching strategy as MarketContextEngine.
    """
    
    def __init__(self, config: RegimeConfig | None = None):
        self.config = config or RegimeConfig()
        self._state = RegimeState()
        self._atr_history: deque[float] = deque(maxlen=self.config.atr_rolling_window)
        self._peak_adx: float = 0.0  # Track recent ADX peak for reversal detection
    
    def classify(self, market_context: dict) -> dict:
        """
        Classify the current market regime from Level 2 context data.
        
        Args:
            market_context: dict from MarketContextEngine.update_tick()
            
        Returns:
            dict with keys: regime_label, regime_confidence, regime_detail,
                           regime_prior, regime_stable
        """
        adx = market_context.get("adx")
        adx_slope = market_context.get("adx_slope")
        plus_di = market_context.get("plus_di")
        minus_di = market_context.get("minus_di")
        cci = market_context.get("cci")
        cci_state = market_context.get("cci_state")
        atr = market_context.get("atr")
        nearest_structure_atr = market_context.get("nearest_structure_atr")
        micro_support = market_context.get("micro_support")
        micro_resistance = market_context.get("micro_resistance")
        reversal_friendly = market_context.get("reversal_friendly", False)
        
        # Track ATR history for breakout detection
        if atr is not None:
            self._atr_history.append(atr)
        
        # Track peak ADX for reversal detection
        if adx is not None and adx > self._peak_adx:
            self._peak_adx = adx
        # Decay peak slowly
        if adx is not None and adx < self._peak_adx:
            self._peak_adx = max(adx, self._peak_adx * 0.97)
        
        # Step 1: Insufficient data
        if adx is None:
            return self._emit("INSUFFICIENT_DATA", 0.0, {})
        
        di_spread = abs((plus_di or 0) - (minus_di or 0))
        has_structure = micro_support is not None and micro_resistance is not None
        avg_atr = sum(self._atr_history) / len(self._atr_history) if self._atr_history else (atr or 1.0)
        atr_ratio = (atr / avg_atr) if avg_atr > 0 and atr is not None else 1.0
        
        # Step 2: Breakout detection
        if atr_ratio > self.config.breakout_atr_multiplier and nearest_structure_atr is not None and nearest_structure_atr > 1.0:
            confidence = min(100, 50 + (atr_ratio - 1.0) * 30 + di_spread)
            return self._emit("BREAKOUT", confidence, {
                "atr_ratio": round(atr_ratio, 2),
                "di_spread": round(di_spread, 1),
                "trigger": "ATR spike + price beyond structure",
            })
        
        # Step 3: Strong momentum
        if adx > self.config.strong_momentum_adx and di_spread > self.config.strong_momentum_di_spread:
            confidence = min(100, 40 + (adx - 40) * 1.5 + di_spread)
            return self._emit("STRONG_MOMENTUM", confidence, {
                "adx": round(adx, 1),
                "di_spread": round(di_spread, 1),
                "trigger": "High ADX + strong DI spread",
            })
        
        # Step 4: Moderate ADX zone (20-40)
        if adx > self.config.trend_pullback_adx_min:
            # Check for trend reversal
            if (adx_slope is not None and adx_slope < self.config.reversal_adx_slope
                    and self._peak_adx > self.config.reversal_prior_adx_min
                    and reversal_friendly):
                confidence = min(100, 50 + abs(adx_slope) * 30 + (self._peak_adx - adx) * 0.8)
                return self._emit("TREND_REVERSAL", confidence, {
                    "adx": round(adx, 1),
                    "adx_slope": round(adx_slope, 2),
                    "peak_adx": round(self._peak_adx, 1),
                    "trigger": "Falling ADX from peak + reversal_friendly",
                })
            
            # Otherwise: trend with pullback
            near_structure = (nearest_structure_atr is not None 
                            and nearest_structure_atr < self.config.pullback_structure_atr)
            confidence = min(100, 40 + adx * 0.8 + (15 if near_structure else 0))
            return self._emit("TREND_PULLBACK", confidence, {
                "adx": round(adx, 1),
                "near_structure": near_structure,
                "trigger": "Moderate ADX trend zone",
            })
        
        # Step 5: Low ADX zone (≤ 20) — range or choppy
        if has_structure:
            # Check for clean range behavior
            cci_cycling = cci_state in ("oversold", "overbought")
            atr_stable = atr_ratio < 1.3
            
            if atr_stable and (cci_cycling or (cci is not None and abs(cci) > 50)):
                confidence = min(100, 50 + (20 - adx) * 1.5 + (15 if cci_cycling else 0))
                return self._emit("RANGE_BOUND", confidence, {
                    "adx": round(adx, 1),
                    "cci_state": cci_state,
                    "atr_stable": atr_stable,
                    "trigger": "Low ADX + structure + CCI cycling",
                })
            else:
                confidence = min(100, 30 + atr_ratio * 10)
                return self._emit("CHOPPY", confidence, {
                    "adx": round(adx, 1),
                    "atr_ratio": round(atr_ratio, 2),
                    "trigger": "Low ADX + unstable ATR or no CCI cycle",
                })
        
        # No structure + low ADX
        confidence = min(100, 40 + (20 - adx))
        return self._emit("CHOPPY", confidence, {
            "adx": round(adx, 1),
            "has_structure": False,
            "trigger": "Low ADX + no S/R structure",
        })
    
    def _emit(self, label: str, confidence: float, detail: dict) -> dict:
        """Update internal state and return regime classification."""
        prior = self._state.label
        
        # Persistence logic — regime must hold for N candle closes to be stable
        if label == self._state.label:
            self._state.persistence_count += 1
        else:
            self._state.prior_label = prior
            self._state.persistence_count = 1
        
        self._state.label = label
        self._state.confidence = round(min(100, max(0, confidence)), 1)
        self._state.detail = detail
        
        stable = self._state.persistence_count >= self.config.persistence_candles
        
        return {
            "regime_label": label,
            "regime_confidence": self._state.confidence,
            "regime_detail": detail,
            "regime_prior": prior if prior != label else None,
            "regime_stable": stable,
            "regime_persistence": self._state.persistence_count,
        }
    
    def reset(self) -> None:
        """Reset classifier state (e.g., on asset switch)."""
        self._state = RegimeState()
        self._atr_history.clear()
        self._peak_adx = 0.0
```

#### 1.2 — Integrate RegimeClassifier into StreamingService

**File:** `app/backend/services/streaming.py`

Add regime classifier alongside existing engines:

```python
from .regime_classifier import RegimeClassifier, RegimeConfig

# In _get_or_create_engines():
if asset not in self._regime_classifiers:
    self._regime_classifiers[asset] = RegimeClassifier()

# In _process_tick_inner(), after market context update:
if self.level3_enabled and market_context and candle_closed:
    regime = self._regime_classifiers[asset].classify(market_context)
    oteo_result["regime"] = regime
```

**Key design:** The regime classifier runs **only on candle close**, not per-tick, matching the caching strategy of MarketContextEngine.

#### 1.3 — Add regime data to streaming payload

**File:** `app/backend/services/streaming.py`

In the payload construction:

```python
if self.level3_enabled and "regime" in oteo_result:
    payload["regime_label"] = oteo_result["regime"]["regime_label"]
    payload["regime_confidence"] = oteo_result["regime"]["regime_confidence"]
    payload["regime_stable"] = oteo_result["regime"]["regime_stable"]
    payload["regime_detail"] = oteo_result["regime"]["regime_detail"]
```

---

### Phase 2: Level 3 Signal Policy (HIGH)

**Priority:** HIGH — Regime-driven trading decisions  
**Estimated complexity:** ~100 lines across 2 files

#### 2.1 — Create `apply_level3_policy()` function

**File:** `app/backend/services/market_context.py` (append to existing)

```python
@dataclass(frozen=True)
class Level3PolicyConfig:
    """Tunable weights for Level 3 regime-based policy adjustments."""
    # Regime score adjustments
    range_bound_boost: float = 6.0
    trend_reversal_boost: float = 5.0
    trend_pullback_aligned_boost: float = 3.0
    trend_pullback_counter_penalty: float = -8.0
    strong_momentum_penalty: float = -12.0
    breakout_penalty: float = -10.0
    choppy_penalty: float = -15.0
    
    # Regime confidence scaling — adjustments scale with regime confidence
    min_regime_confidence_for_boost: float = 50.0
    
    # Hard suppression thresholds
    suppress_in_choppy: bool = True
    suppress_counter_strong_momentum: bool = True
    suppress_in_breakout: bool = True
    
    # Unstable regime caution
    unstable_regime_penalty: float = -3.0


def apply_level3_policy(
    oteo_result: dict,
    market_context: dict,
    regime: dict,
    config: Level3PolicyConfig | None = None,
) -> dict:
    """
    Apply Level 3 regime-aware policy adjustments.
    
    This function runs AFTER apply_level2_policy() and further refines
    the signal based on the detected market regime.
    """
    cfg = config or Level3PolicyConfig()
    
    regime_label = regime.get("regime_label", "INSUFFICIENT_DATA")
    regime_confidence = regime.get("regime_confidence", 0)
    regime_stable = regime.get("regime_stable", False)
    
    if regime_label == "INSUFFICIENT_DATA":
        return oteo_result
    
    score = oteo_result.get("oteo_score", 50.0)
    direction = oteo_result.get("recommended", "")
    trend_direction = market_context.get("trend_direction")
    actionable = oteo_result.get("actionable", False)
    
    l3_adjustment = 0.0
    l3_suppressed_reason = None
    confidence_scale = min(1.0, regime_confidence / 100.0) if regime_confidence >= cfg.min_regime_confidence_for_boost else 0.5
    
    # Regime-specific policy
    if regime_label == "RANGE_BOUND":
        l3_adjustment += cfg.range_bound_boost * confidence_scale
    
    elif regime_label == "TREND_REVERSAL":
        l3_adjustment += cfg.trend_reversal_boost * confidence_scale
    
    elif regime_label == "TREND_PULLBACK":
        # Only allow trend-aligned entries
        trend_aligned = (
            (direction == "call" and trend_direction == "bullish") or
            (direction == "put" and trend_direction == "bearish")
        )
        if trend_aligned:
            l3_adjustment += cfg.trend_pullback_aligned_boost * confidence_scale
        else:
            l3_adjustment += cfg.trend_pullback_counter_penalty * confidence_scale
            if cfg.suppress_counter_strong_momentum:
                l3_suppressed_reason = "L3: counter-trend in pullback regime"
    
    elif regime_label == "STRONG_MOMENTUM":
        l3_adjustment += cfg.strong_momentum_penalty * confidence_scale
        if cfg.suppress_counter_strong_momentum and actionable:
            # Check if signal is counter-trend
            counter_trend = (
                (direction == "put" and trend_direction == "bullish") or
                (direction == "call" and trend_direction == "bearish")
            )
            if counter_trend:
                l3_suppressed_reason = "L3: reversal suppressed in strong momentum"
    
    elif regime_label == "BREAKOUT":
        l3_adjustment += cfg.breakout_penalty * confidence_scale
        if cfg.suppress_in_breakout and actionable:
            l3_suppressed_reason = "L3: signal suppressed during breakout"
    
    elif regime_label == "CHOPPY":
        l3_adjustment += cfg.choppy_penalty * confidence_scale
        if cfg.suppress_in_choppy and actionable:
            l3_suppressed_reason = "L3: signal suppressed in choppy regime"
    
    # Unstable regime caution
    if not regime_stable:
        l3_adjustment += cfg.unstable_regime_penalty
    
    # Apply adjustments
    new_score = max(0, min(100, score + l3_adjustment))
    result = {**oteo_result}
    result["oteo_score"] = new_score
    result["level3_score_adjustment"] = round(l3_adjustment, 2)
    result["regime_label"] = regime_label
    result["regime_confidence"] = regime_confidence
    result["regime_stable"] = regime_stable
    
    # Handle suppression
    if l3_suppressed_reason:
        result["actionable"] = False
        result["level3_suppressed_reason"] = l3_suppressed_reason
        # Preserve L2 suppression if it already exists
        if result.get("level2_suppressed_reason"):
            result["level3_suppressed_reason"] = f"{result['level2_suppressed_reason']} + {l3_suppressed_reason}"
    
    # Confidence adjustment based on regime
    confidence = result.get("confidence", "LOW")
    if l3_adjustment >= 8.0 and confidence != "HIGH" and new_score >= 75:
        result["confidence"] = "HIGH"
    elif l3_adjustment <= -8.0 and confidence == "HIGH":
        result["confidence"] = "MEDIUM"
    
    return result
```

#### 2.2 — Wire Level 3 policy into StreamingService

**File:** `app/backend/services/streaming.py`

In `_process_tick_inner()`, after Level 2 policy:

```python
# Level 3: Regime-aware policy
if self.level3_enabled and "regime" in oteo_result:
    oteo_result = apply_level3_policy(oteo_result, market_context, oteo_result["regime"])
```

---

### Phase 3: Win-Rate Optimization Features (HIGH)

**Priority:** HIGH — Directly improves profitability  
**Estimated complexity:** ~120 lines across 3 files

These features address the most common failure modes in OTC binary options trading.

#### 3.1 — Tick Frequency Health Check

**File:** `app/backend/services/market_context.py`

Add a tick frequency tracker to `MarketContextEngine`:

```python
def __init__(self, config=None):
    # ... existing init ...
    self._tick_timestamps: deque[float] = deque(maxlen=60)  # last 60 ticks

def _compute_tick_frequency(self, timestamp: float) -> float:
    """Compute ticks per minute from recent tick timestamps."""
    self._tick_timestamps.append(timestamp)
    if len(self._tick_timestamps) < 2:
        return 0.0
    time_span = self._tick_timestamps[-1] - self._tick_timestamps[0]
    if time_span <= 0:
        return 0.0
    return (len(self._tick_timestamps) - 1) / time_span * 60.0
```

Include in the market_context dict:

```python
context["tick_frequency"] = round(self._compute_tick_frequency(timestamp), 1)
context["tick_health"] = "healthy" if context["tick_frequency"] >= 20 else "low" if context["tick_frequency"] >= 5 else "dead"
```

**Policy integration:** In `apply_level3_policy()`, add:

```python
tick_health = market_context.get("tick_health", "healthy")
if tick_health == "dead":
    l3_suppressed_reason = "L3: dead market (tick frequency < 5/min)"
elif tick_health == "low":
    l3_adjustment -= 3.0  # Penalize low-liquidity signals
```

#### 3.2 — Entry Timing Confirmation Window

**File:** `app/backend/services/auto_ghost.py`

Add a pending signal confirmation mechanism:

```python
# In __init__:
self._pending_signals: dict[str, tuple[dict, int]] = {}  # asset -> (signal, tick_count)
CONFIRMATION_TICKS = 3  # Signal must hold for 3 consecutive ticks

async def consider_signal(self, *, asset, price, timestamp, oteo_result, manipulation, payout=0.0):
    # ... existing pre-flight checks ...
    
    direction = oteo_result.get("recommended")
    
    # Entry confirmation window
    if asset in self._pending_signals:
        pending_signal, count = self._pending_signals[asset]
        if pending_signal.get("recommended") == direction:
            count += 1
            if count >= self.CONFIRMATION_TICKS:
                # Signal confirmed — proceed to execution
                del self._pending_signals[asset]
                # ... existing execution logic ...
            else:
                self._pending_signals[asset] = (oteo_result, count)
                return None  # Still confirming
        else:
            # Direction changed — reset confirmation
            del self._pending_signals[asset]
            return None
    else:
        # First actionable tick — start confirmation
        self._pending_signals[asset] = (oteo_result, 1)
        return None
```

#### 3.3 — Adaptive Cooldown After Losses

**File:** `app/backend/services/auto_ghost.py`

Modify `report_outcome()` to extend cooldown after losses:

```python
def report_outcome(self, asset: str, outcome: str, ...):
    # ... existing logic ...
    
    if outcome == "loss":
        # Double the cooldown for this asset after a loss
        extended_cooldown = self.config.per_asset_cooldown_seconds * 2
        self._cooldown_until[asset] = time.time() + extended_cooldown
        logger.info("Extended cooldown for %s after loss: %ds", asset, extended_cooldown)
    
    # Track consecutive losses per asset
    if outcome == "loss":
        self._consecutive_losses[asset] = self._consecutive_losses.get(asset, 0) + 1
        if self._consecutive_losses[asset] >= 3:
            # Triple cooldown after 3 consecutive losses
            self._cooldown_until[asset] = time.time() + self.config.per_asset_cooldown_seconds * 3
            logger.warning("Triple cooldown for %s after %d consecutive losses", 
                          asset, self._consecutive_losses[asset])
    elif outcome == "win":
        self._consecutive_losses.pop(asset, None)
```

#### 3.4 — Per-Condition Win Rate Tracking

**File:** `app/backend/services/auto_ghost.py`

Add condition-level statistics:

```python
# In __init__:
self._condition_stats: dict[str, dict] = {}  # "regime:RANGE_BOUND" -> {wins, losses}

def report_outcome(self, asset: str, outcome: str, entry_context: dict | None = None):
    # ... existing logic ...
    
    if entry_context and outcome in ("win", "loss"):
        is_win = outcome == "win"
        
        # Track by regime
        regime = entry_context.get("regime_label", "unknown")
        self._update_condition_stat(f"regime:{regime}", is_win)
        
        # Track by ADX regime  
        adx_regime = entry_context.get("adx_regime", "unknown")
        self._update_condition_stat(f"adx:{adx_regime}", is_win)
        
        # Track by CCI state
        cci_state = entry_context.get("cci_state", "unknown")
        self._update_condition_stat(f"cci:{cci_state}", is_win)
        
        # Track by asset
        self._update_condition_stat(f"asset:{asset}", is_win)
        
        # Track by tick health
        tick_health = entry_context.get("tick_health", "unknown")
        self._update_condition_stat(f"tick_health:{tick_health}", is_win)

def _update_condition_stat(self, key: str, is_win: bool) -> None:
    stats = self._condition_stats.setdefault(key, {"wins": 0, "losses": 0})
    if is_win:
        stats["wins"] += 1
    else:
        stats["losses"] += 1

def get_condition_stats(self) -> dict:
    """Return per-condition win rates for analysis."""
    result = {}
    for key, stats in self._condition_stats.items():
        total = stats["wins"] + stats["losses"]
        result[key] = {
            **stats,
            "total": total,
            "win_rate": round(stats["wins"] / total * 100, 1) if total > 0 else 0,
        }
    return result
```

#### 3.5 — CCI Divergence Detection

**File:** `app/backend/services/market_context.py`

Add divergence detection to the context:

```python
def _detect_cci_divergence(self, candles: list, cci_values: list) -> str | None:
    """
    Detect CCI divergence over the last N candles.
    
    Bearish divergence: price makes higher high, CCI makes lower high
    Bullish divergence: price makes lower low, CCI makes higher low
    """
    if len(candles) < 10 or len(cci_values) < 10:
        return None
    
    recent = candles[-5:]
    prior = candles[-10:-5]
    recent_cci = cci_values[-5:]
    prior_cci = cci_values[-10:-5]
    
    recent_high = max(c.high for c in recent)
    prior_high = max(c.high for c in prior)
    recent_low = min(c.low for c in recent)
    prior_low = min(c.low for c in prior)
    
    recent_cci_max = max(recent_cci)
    prior_cci_max = max(prior_cci)
    recent_cci_min = min(recent_cci)
    prior_cci_min = min(prior_cci)
    
    # Bearish divergence: higher price high + lower CCI high
    if recent_high > prior_high and recent_cci_max < prior_cci_max - 10:
        return "bearish"
    
    # Bullish divergence: lower price low + higher CCI low
    if recent_low < prior_low and recent_cci_min > prior_cci_min + 10:
        return "bullish"
    
    return None
```

Include in context dict:

```python
context["cci_divergence"] = self._detect_cci_divergence(closed_candles, cci_values)
```

**Policy integration:** In `apply_level3_policy()`:

```python
cci_divergence = market_context.get("cci_divergence")
if cci_divergence:
    if (cci_divergence == "bearish" and direction == "put") or \
       (cci_divergence == "bullish" and direction == "call"):
        l3_adjustment += 4.0  # Divergence confirms reversal direction
```

---

### Phase 4: AI Advisory Review Loop (MEDIUM)

**Priority:** MEDIUM — Validates regime classifier, provides advisory insight  
**New file:** `app/backend/services/ai_review.py`  
**Estimated complexity:** ~120 lines

#### 4.1 — Create `AIReviewService`

**File:** `app/backend/services/ai_review.py` (NEW)

```python
"""
Periodic AI review service for regime validation and setup grading.

Sends snapshots of the current market state to the AI provider for
advisory analysis. AI responses are informational only — they never
trigger trades or override the deterministic policy.
"""

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AIReviewService:
    """Background AI review loop."""
    
    def __init__(self, ai_service, interval_seconds: int = 300):
        self.ai_service = ai_service
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_review: dict | None = None
        self._last_review_time: float = 0
    
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._review_loop())
        self._task.add_done_callback(
            lambda t: logger.error("AI review loop failed: %s", t.exception())
            if not t.cancelled() and t.exception() else None
        )
        logger.info("AI review loop started (interval: %ds)", self.interval_seconds)
    
    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("AI review loop stopped")
    
    async def _review_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval_seconds)
            if not self._running:
                break
            try:
                await self._perform_review()
            except Exception as exc:
                logger.error("AI review iteration failed: %s", exc)
    
    async def _perform_review(self) -> None:
        """Collect current state snapshot and send to AI for review."""
        # This will be called by StreamingService to inject current state
        pass
    
    async def review_snapshot(self, snapshot: dict) -> dict | None:
        """
        Send a market state snapshot to AI for regime validation.
        
        Args:
            snapshot: {
                asset, regime_label, regime_confidence, regime_detail,
                adx, cci, cci_state, atr, nearest_structure_atr,
                recent_signals (last 5), recent_outcomes (last 10),
                condition_stats (from AutoGhost)
            }
        
        Returns:
            AI review result or None if unavailable
        """
        if not self.ai_service:
            return None
        
        prompt = self._build_review_prompt(snapshot)
        
        try:
            response = await self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}],
                context=None,
            )
            
            self._last_review = {
                "timestamp": time.time(),
                "asset": snapshot.get("asset"),
                "regime_label": snapshot.get("regime_label"),
                "ai_response": response.get("response", ""),
                "model": response.get("model"),
            }
            self._last_review_time = time.time()
            
            logger.info("AI review completed for %s (regime: %s)", 
                        snapshot.get("asset"), snapshot.get("regime_label"))
            return self._last_review
            
        except Exception as exc:
            logger.warning("AI review failed (non-fatal): %s", exc)
            return None
    
    def _build_review_prompt(self, snapshot: dict) -> str:
        """Build the AI review prompt from the snapshot."""
        return f"""You are an OTC binary options market analyst. Review this market state snapshot and provide:
1. Do you agree with the regime classification? (YES/NO + brief reason)
2. Setup quality grade (A/B/C/D/F) for taking reversal trades right now
3. Any caution flags or unusual conditions
4. One-sentence trading recommendation

Market State:
- Asset: {snapshot.get('asset', 'Unknown')}
- Detected Regime: {snapshot.get('regime_label', 'Unknown')} (confidence: {snapshot.get('regime_confidence', 0)}%)
- ADX: {snapshot.get('adx', 'N/A')} (slope: {snapshot.get('adx_slope', 'N/A')})
- CCI: {snapshot.get('cci', 'N/A')} (state: {snapshot.get('cci_state', 'N/A')})
- ATR: {snapshot.get('atr', 'N/A')}
- Nearest Structure: {snapshot.get('nearest_structure_atr', 'N/A')} ATR units
- Tick Frequency: {snapshot.get('tick_frequency', 'N/A')}/min
- Recent Win Rate: {snapshot.get('recent_win_rate', 'N/A')}%
- Condition Stats: {snapshot.get('condition_stats', {})}

Respond concisely (max 150 words). Focus on actionable insight."""
    
    def get_last_review(self) -> dict | None:
        return self._last_review
```

#### 4.2 — Wire AI review into StreamingService

**File:** `app/backend/services/streaming.py`

```python
from .ai_review import AIReviewService

# In __init__:
self.ai_review: AIReviewService | None = None

# Method to attach AI service (called from main.py during setup):
def attach_ai_review(self, ai_service, interval: int = 300) -> None:
    self.ai_review = AIReviewService(ai_service, interval)

# On start():
if self.level3_enabled and self.ai_review:
    self.ai_review.start()

# On stop():
if self.ai_review:
    self.ai_review.stop()
```

#### 4.3 — Add AI review endpoint

**File:** `app/backend/api/strategy.py`

```python
@router.get("/ai-review")
async def get_ai_review(request: Request) -> JSONResponse:
    """Get the latest AI regime review result."""
    streaming = request.app.state.streaming_service
    if not streaming.ai_review:
        return JSONResponse(content={"available": False, "review": None})
    review = streaming.ai_review.get_last_review()
    return JSONResponse(content={"available": True, "review": review})
```

---

### Phase 5: Frontend L3 Visualization (MEDIUM)

**Priority:** MEDIUM — User-facing regime awareness  
**Estimated complexity:** ~60 lines across 3 files

#### 5.1 — Extend frontend signal model with L3 fields

**File:** `app/frontend/src/hooks/useStreamConnection.js`

Add Level 3 fields to the signal object:

```javascript
const signal = {
    // ... existing L1/L2 fields ...
    
    // Level 3 regime fields
    level3_enabled: Boolean(payload.level3_enabled),
    level3_score_adjustment: Number(payload.level3_score_adjustment ?? 0),
    level3_suppressed_reason: payload.level3_suppressed_reason ?? null,
    regime_label: payload.regime_label ?? null,
    regime_confidence: Number(payload.regime_confidence ?? 0),
    regime_stable: Boolean(payload.regime_stable),
    regime_detail: payload.regime_detail ?? null,
    cci_divergence: payload.cci_divergence ?? null,
    tick_health: payload.tick_health ?? null,
};
```

#### 5.2 — Add regime badge to OTEORing

**File:** `app/frontend/src/components/trading/OTEORing.jsx`

Replace the current ADX-based regime chip with a real regime label:

```jsx
// Regime badge with color coding
const REGIME_COLORS = {
    RANGE_BOUND: 'text-green-400',      // OTEO sweet spot
    TREND_REVERSAL: 'text-emerald-400',  // Good for reversals
    TREND_PULLBACK: 'text-yellow-400',   // Conditional
    STRONG_MOMENTUM: 'text-red-400',     // Dangerous
    BREAKOUT: 'text-orange-400',         // Dangerous
    CHOPPY: 'text-red-500',             // Avoid
    INSUFFICIENT_DATA: 'text-gray-500',
};

// In the render:
{signal.regime_label && (
    <div className={`text-xs font-mono ${REGIME_COLORS[signal.regime_label] || 'text-gray-400'}`}>
        {signal.regime_label.replace('_', ' ')}
        {signal.regime_stable ? ' ✓' : ' ~'}
        {signal.regime_confidence > 0 && ` ${signal.regime_confidence}%`}
    </div>
)}
```

#### 5.3 — Add regime chip to MultiChartView mini-cards

**File:** `app/frontend/src/components/trading/MultiChartView.jsx`

Add regime label to the mini-chart card overlay, replacing the current `adx_regime` chip:

```jsx
{signal?.regime_label && (
    <span className={`text-[10px] px-1 rounded ${REGIME_CHIP_COLORS[signal.regime_label]}`}>
        {signal.regime_label.replace('_', ' ')}
    </span>
)}
```

---

### Phase 6: Volatility-Adaptive Expiry (MEDIUM)

**Priority:** MEDIUM — Optimizes trade duration for current conditions  
**Estimated complexity:** ~50 lines across 3 files

#### 6.1 — Add expiry suggestion to MarketContextEngine

**File:** `app/backend/services/market_context.py`

```python
def _suggest_expiry(self, atr: float, regime_label: str) -> int:
    """
    Suggest optimal expiry in seconds based on current volatility and regime.
    
    High ATR → longer expiry (reversal needs time to develop)
    Low ATR → shorter expiry (small moves consumed quickly)
    """
    if atr is None:
        return 60  # default
    
    # Compute ATR percentile from history
    if not self._atr_history:
        return 60
    
    sorted_atrs = sorted(self._atr_history)
    percentile = sorted_atrs.index(min(sorted_atrs, key=lambda x: abs(x - atr))) / len(sorted_atrs)
    
    # Base expiry from ATR percentile
    if percentile > 0.75:
        base_expiry = 120  # High volatility — give more time
    elif percentile > 0.5:
        base_expiry = 60   # Normal volatility
    elif percentile > 0.25:
        base_expiry = 60   # Low-normal
    else:
        base_expiry = 30   # Very low volatility — quick resolution
    
    # Regime adjustment
    if regime_label in ("RANGE_BOUND", "TREND_REVERSAL"):
        return base_expiry  # Standard — reversal expected
    elif regime_label == "TREND_PULLBACK":
        return min(180, base_expiry + 30)  # Extra time for pullback to complete
    elif regime_label in ("STRONG_MOMENTUM", "BREAKOUT"):
        return max(30, base_expiry - 30)  # Shorter — less time in danger
    
    return base_expiry
```

Include in context:

```python
context["suggested_expiry"] = self._suggest_expiry(atr, regime_label)
```

#### 6.2 — Use suggested expiry in Auto-Ghost

**File:** `app/backend/services/auto_ghost.py`

In `consider_signal()`, use the suggested expiry if available:

```python
# Use suggested expiry from Level 3 if available, otherwise config default
suggested_expiry = oteo_result.get("market_context", {}).get("suggested_expiry")
expiry = suggested_expiry if suggested_expiry and self.config.use_adaptive_expiry else self.config.expiration_seconds
```

Add config field:

```python
@dataclass(frozen=True)
class AutoGhostConfig:
    # ... existing fields ...
    use_adaptive_expiry: bool = False  # Opt-in — must be explicitly enabled
```

#### 6.3 — Add adaptive expiry toggle to frontend settings

**File:** `app/frontend/src/stores/useSettingsStore.js`

Add `autoGhostAdaptiveExpiry: false` to `SETTINGS_DEFAULTS` and wire through the settings sync.

---

## 5. Files Changed Summary

| File | Action | Phase(s) | Change |
|------|--------|----------|--------|
| `app/backend/services/streaming.py` | MODIFIED | 0, 1, 2, 4 | Inject level flags, add regime classifier engines, wire L3 policy, attach AI review |
| `app/backend/services/market_context.py` | MODIFIED | 0, 2, 3, 6 | Fix M3/M4/M5, add L3PolicyConfig + apply_level3_policy, tick frequency, CCI divergence, suggested expiry |
| `app/backend/services/trade_service.py` | MODIFIED | 0 | Add exception callback (M2) |
| `app/backend/services/auto_ghost.py` | MODIFIED | 3 | Entry confirmation, adaptive cooldown, per-condition stats, adaptive expiry |
| `app/backend/services/regime_classifier.py` | **NEW** | 1 | RegimeClassifier with config, persistence, confidence scoring |
| `app/backend/services/ai_review.py` | **NEW** | 4 | AIReviewService with periodic snapshots and prompt building |
| `app/backend/api/strategy.py` | MODIFIED | 4 | Add `/ai-review` endpoint |
| `app/frontend/src/hooks/useStreamConnection.js` | MODIFIED | 5 | Add L3 signal fields |
| `app/frontend/src/components/trading/OTEORing.jsx` | MODIFIED | 5 | Real regime badge with color coding |
| `app/frontend/src/components/trading/MultiChartView.jsx` | MODIFIED | 5 | Regime chip on mini-cards |
| `app/frontend/src/stores/useSettingsStore.js` | MODIFIED | 6 | Add adaptive expiry toggle |

**Total: 2 new files, 9 files modified**

---

## 6. Files Explicitly NOT Touched

| File | Reason |
|------|--------|
| `services/oteo.py` | OTEO core is stable — Level 3 is additive |
| `services/manipulation.py` | Manipulation detector is hardened — no changes needed |
| `models/domain.py` | `strategy_level` and `entry_context` already support L3 metadata |
| `models/requests.py` | Confidence validator handles all types |
| `components/trading/Sparkline.jsx` | Renders from props — no changes needed |
| `api/session.py` | Session lifecycle unaffected by Level 3 |
| `stores/useTradingStore.js` | Trade execution path unchanged |

---

## 7. Implementation Order & Dependencies

```
Phase 0 (Pre-Implementation Bug Fixes) — MUST COMPLETE FIRST
  ├── 0.1: Fix strategy_level tagging (streaming.py)
  ├── 0.2: Fix live trade exception callback (trade_service.py)
  ├── 0.3: Fix first-tick candle_closed (market_context.py)
  ├── 0.4: Fix macro S/R percentile fallback (market_context.py)
  └── 0.5: Wire distant_structure_atr from config (market_context.py)
       ↓
Phase 1 (Regime Classifier)
  ├── 1.1: Create regime_classifier.py
  ├── 1.2: Integrate into StreamingService
  └── 1.3: Add regime to streaming payload
       ↓
Phase 2 (Level 3 Signal Policy)
  ├── 2.1: Create apply_level3_policy()
  └── 2.2: Wire into StreamingService
       ↓
Phase 3 (Win-Rate Optimizations)
  ├── 3.1: Tick frequency health check (market_context.py)
  ├── 3.2: Entry confirmation window (auto_ghost.py)
  ├── 3.3: Adaptive cooldown after losses (auto_ghost.py)
  ├── 3.4: Per-condition win rate tracking (auto_ghost.py)
  └── 3.5: CCI divergence detection (market_context.py)
       ↓
Phase 4 (AI Advisory Review Loop) — can run in parallel with Phase 5
  ├── 4.1: Create ai_review.py
  ├── 4.2: Wire into StreamingService
  └── 4.3: Add API endpoint
       ↓
Phase 5 (Frontend L3 Visualization) — can run in parallel with Phase 4
  ├── 5.1: Extend signal model
  ├── 5.2: OTEORing regime badge
  └── 5.3: MultiChartView regime chip
       ↓
Phase 6 (Volatility-Adaptive Expiry)
  ├── 6.1: Expiry suggestion in MarketContextEngine
  ├── 6.2: Wire into Auto-Ghost
  └── 6.3: Frontend settings toggle
```

---

## 8. Verification Checklist

### Phase 0 Verification
- [ ] `strategy_level` correctly tags as `"level3"` when L3 is enabled (check ghost trade JSONL)
- [ ] Live trade tracking tasks have exception callbacks (check for log entries on failure)
- [ ] First tick does NOT trigger full indicator recompute (verify via backend logs)
- [ ] Macro S/R fallback uses percentile values (verify by inspecting context dict)
- [ ] Changing `distant_structure_atr` in config affects actual policy behavior

### Phase 1 Verification
- [ ] `RegimeClassifier` produces one of 7 valid labels for each candle close
- [ ] Regime label changes when market conditions change (test with different ADX values)
- [ ] Regime persistence prevents flapping (regime holds for N candle closes)
- [ ] Regime data appears in streaming payload when L3 is enabled
- [ ] Regime data does NOT appear when L3 is disabled
- [ ] `regime_classifier.py` has zero external dependencies beyond stdlib

### Phase 2 Verification
- [ ] `RANGE_BOUND` regime boosts OTEO reversal signals
- [ ] `STRONG_MOMENTUM` regime suppresses counter-trend signals
- [ ] `CHOPPY` regime suppresses all signals
- [ ] `BREAKOUT` regime suppresses signals
- [ ] `TREND_PULLBACK` allows only trend-aligned entries
- [ ] `TREND_REVERSAL` boosts reversal signals
- [ ] Unstable regimes receive penalty
- [ ] L3 adjustments appear in trade records (`level3_score_adjustment`)
- [ ] L3 suppression reasons appear in payload (`level3_suppressed_reason`)

### Phase 3 Verification
- [ ] Tick frequency computed and included in market_context
- [ ] Dead market (< 5 ticks/min) suppresses signals
- [ ] Entry confirmation window delays execution by N ticks
- [ ] Confirmation resets when direction changes
- [ ] Cooldown doubles after a loss on the same asset
- [ ] Cooldown triples after 3 consecutive losses
- [ ] Consecutive losses reset after a win
- [ ] Per-condition stats track wins/losses by regime, ADX, CCI, asset, tick_health
- [ ] `get_condition_stats()` returns structured win-rate data
- [ ] CCI divergence detected when price and CCI diverge

### Phase 4 Verification
- [ ] AI review loop runs at configured interval
- [ ] AI review produces structured response
- [ ] AI review is advisory-only — does NOT modify signals or trigger trades
- [ ] `GET /api/strategy/ai-review` returns latest review or null
- [ ] AI review loop stops when streaming stops
- [ ] AI service failure does not crash the streaming pipeline

### Phase 5 Verification
- [ ] L3 fields appear in frontend signal object when L3 enabled
- [ ] OTEORing shows real regime label with appropriate color
- [ ] Regime stability indicator (✓ vs ~) displays correctly
- [ ] MultiChartView mini-cards show regime chip
- [ ] Frontend build passes with 0 errors

### Phase 6 Verification
- [ ] Suggested expiry varies with ATR percentile
- [ ] High ATR → longer suggested expiry
- [ ] Low ATR → shorter suggested expiry
- [ ] Auto-Ghost uses suggested expiry when adaptive expiry enabled
- [ ] Auto-Ghost uses config default when adaptive expiry disabled
- [ ] Frontend settings toggle for adaptive expiry works

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Regime classifier misclassifies during transition | Medium | Wrong policy applied | Persistence logic requires N candle closes; unstable penalty applied |
| Regime suppression reduces trade volume too much | Medium | Miss profitable setups | All suppressions are configurable; can disable per-regime |
| Entry confirmation window misses fast signals | Low | Missed entries | Window is 3 ticks (~3 seconds) — fast enough for 60s expiry |
| CCI divergence false positives | Medium | Incorrect boost | Divergence adds only +4 to score; not enough to override other factors |
| AI review produces misleading advice | Low | User confusion | AI is advisory-only with clear labeling; deterministic policy always takes precedence |
| Tick frequency metric noisy during warmup | Medium | False dead-market suppression | Only suppress when frequency < 5/min (very conservative threshold) |
| Adaptive expiry produces suboptimal results | Medium | Worse outcomes | Opt-in feature (disabled by default); user must explicitly enable |
| Regime flapping in transitions | Medium | Inconsistent signals | Persistence counter + unstable penalty mitigate this |

---

## 10. Risk Forecast — What Breaks If Ignored

| If Ignored | Consequence |
|---|---|
| Phase 0 bug fixes | `strategy_level` never tags L3 → no L3 performance comparison possible. Macro S/R fallback produces false regime labels. Policy uses hardcoded instead of config values. |
| Phase 1 (Regime Classifier) | No regime awareness → L3 has no foundation. All other phases depend on this. |
| Phase 2 (L3 Policy) | Regime labels exist but have zero effect on signals → Level 3 is cosmetic only. |
| Phase 3 (Win-Rate Optimizations) | Continue trading dead markets, entering on momentary spikes, no data-driven tuning capability. |
| Phase 4 (AI Review) | No external validation of regime accuracy. Missing the feedback loop that improves the classifier. |
| Phase 5 (Frontend Viz) | Users can't see what regime is active → can't build intuition or override when needed. |
| Phase 6 (Adaptive Expiry) | Fixed 60s expiry regardless of volatility → suboptimal trade duration in high/low ATR. |

---

## 11. CORE_PRINCIPLES Alignment

| Principle | How This Plan Adheres |
|-----------|----------------------|
| **#1 Functional Simplicity** | Regime classifier is a single file with zero external dependencies. Decision tree, not ML. |
| **#2 Sequential Logic** | 7 phases in strict dependency order. Each builds on the previous. |
| **#3 Incremental Testing** | Each phase has explicit verification criteria. @Reviewer sign-off required per phase. |
| **#4 Zero Assumptions** | Regime defaults to `INSUFFICIENT_DATA` when indicators are unavailable. All thresholds configurable. |
| **#5 Code Integrity** | Level 3 is additive. L1 and L2 remain unchanged and independently testable. |
| **#6 Separation of Concerns** | Classifier in its own module. Policy in its own function. AI review in its own service. |
| **#7 Stop Patching** | Clean new modules rather than patching existing L2 code. |
| **#8 Defensive Error Handling** | All new async tasks have exception callbacks. AI failures are non-fatal. |
| **#9 Fail Fast** | Regime validation at API boundary. Tick health check gates early. |

---

## 12. Phase Gate Protocol

Per `.clinerules/PHASE_REVIEW_PROTOCOL.md`:

| Phase | Reviewer Gate | Status |
|-------|--------------|--------|
| Phase 0 | @Reviewer reviews streaming.py + market_context.py + trade_service.py | [ ] Pending |
| Phase 1 | @Reviewer reviews regime_classifier.py + streaming.py integration | [ ] Pending |
| Phase 2 | @Reviewer reviews apply_level3_policy() + StreamingService wiring | [ ] Pending |
| Phase 3 | @Reviewer reviews market_context.py + auto_ghost.py optimizations | [ ] Pending |
| Phase 4 | @Reviewer reviews ai_review.py + strategy.py endpoint | [ ] Pending |
| Phase 5 | @Reviewer reviews useStreamConnection.js + OTEORing.jsx + MultiChartView.jsx | [ ] Pending |
| Phase 6 | @Reviewer reviews expiry suggestion + auto_ghost.py + useSettingsStore.js | [ ] Pending |
| **Final** | @Reviewer + @Debugger + @Optimizer + @Code_Simplifier | [ ] Pending |

---

## 13. Future Scalability Paths

These are **NOT in scope** for this plan but the architecture supports them:

| Feature | Description | Prerequisite |
|---------|-------------|--------------|
| **Multi-Timeframe Fusion** | 5-minute candle context alongside 1-minute | New candle aggregation period in MarketContextEngine |
| **EMA Cross Confirmation** | 5/13 EMA as additional trend confirmation | ~15 lines in MarketContextEngine |
| **Time-of-Day Filter** | Configurable trading windows by hour | Per-condition stats data + simple hour check |
| **Adaptive Payout Threshold** | Adjust min payout based on session win rate | Session stats already tracked |
| **Historical Calibration Loop** | Post-session analysis suggests threshold updates | Journal analytics (Phase 1 of journal plan) |
| **Candlestick Pattern Detection** | Pin bar, engulfing, doji as extra confirmation | New detector on closed candles |
| **Multi-Asset Correlation Filter** | Suppress when 3+ assets signal simultaneously | Track signal timestamps across assets |
| **Regime Persistence Score** | Weight regime confidence by how long it's been active | Already partially implemented (persistence_count) |

---

## 14. Regime Classifier vs AI Review — Separation of Concerns

| Aspect | Regime Classifier (Deterministic) | AI Review (Advisory) |
|--------|-----------------------------------|---------------------|
| **Runs** | Every candle close | Every N minutes (configurable) |
| **Latency** | <1ms | 1-5 seconds (API call) |
| **Cost** | Zero | API token cost |
| **Authority** | Directly affects policy decisions | Advisory only — displayed to user |
| **Reliability** | 100% (deterministic) | Depends on API availability |
| **Tuning** | Config thresholds | Prompt engineering |
| **Purpose** | Classify regime for policy | Validate classifier + provide context |

**Design rule:** The AI **never overrides** the deterministic classifier. If AI disagrees with the regime, it flags it for the user — but the policy continues using the deterministic classification.

---

## 15. Live Context Handoff Checklist

Use this section when resuming Level 3 work later.

- [ ] Phase 0 bug fixes completed and verified
- [ ] `regime_classifier.py` exists and produces valid labels
- [ ] `apply_level3_policy()` exists and adjusts scores/confidence/actionable
- [ ] Tick frequency health check integrated into context and policy
- [ ] Entry confirmation window active in Auto-Ghost
- [ ] Adaptive cooldown active in Auto-Ghost
- [ ] Per-condition win rate tracking active
- [ ] CCI divergence detection integrated
- [ ] AI review loop operational (optional — depends on API key)
- [ ] Frontend displays regime labels in OTEORing and MultiChartView
- [ ] Volatility-adaptive expiry available as opt-in feature
- [ ] Auto-Ghost benchmark session run with L3 enabled
- [ ] Per-condition stats analyzed for threshold tuning opportunities

---

*Plan compiled: 2026-04-29*  
*Source: Forensic investigation of 25+ files, Pre_Level3_Critical_Review, Market_Regimes.md, and full L1→L2→L3 architecture analysis*  
*Compiled by: @Investigator, @Reviewer, @Architect*  
*Status: Awaiting explicit approval before implementation*
