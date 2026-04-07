# 401-Trade Auto-Ghost Session Report (Level 2 Context Tuning)
**Date:** 2026-04-06
**Session ID:** auto_ghost_1775496615
**Trades Logged:** 401
**Time Window:** 17:31:07 -> 20:07:21

## 1. Executive Summary
An Auto-Ghost trading session recorded 401 paper trades across a 2.5-hour window. The market conditions during this period were identified as sub-optimal, characterized by heavy manipulation and erratic, non-trending chop. 

This toxic environment served as an ideal stress test for the Level 2 Context Engine. The analysis revealed that the initial Level 2 policy was too "forgiving" (stacking bonuses on weak baseline setups) and the `ManipulationDetector` was too fleeting (checking for single-tick anomalies rather than persisting a defensive state).

All findings from this session have been directly translated into logic changes within the `MarketContextEngine` and `ManipulationDetector`, officially completing Phase A (Critical Fixes) and Phase B (Tuning) of the Level 2 Implementation Plan.

---

## 2. Statistical Analysis Breakdown

The 401 trades were analyzed in chronological chunks of 100 to map shifting market conditions.

### GROUP 1 (Trades 1 to 100)
- **Time Window:** 17:31:07 -> 18:08:29
- **Win Rate:** 52.0% (51W / 47L / 2 Voids)
- **Key Insight:** `HIGH` Confidence underperformed `MEDIUM` (48.5% vs 60.0%). `strong` ADX trend regimes performed poorly for reversals (35.5%).

### GROUP 2 (Trades 101 to 200)
- **Time Window:** 18:08:48 -> 18:46:23
- **Win Rate:** 41.0% (41W / 59L / 0 Voids)
- **Key Insight:** A highly toxic window. `HIGH` Confidence failed completely (39.6%). Trades `aligned` with structure performed *worse* (36.8%) than unaligned trades (43.5%), indicating structure was breaking cleanly.

### GROUP 3 (Trades 201 to 300)
- **Time Window:** 18:46:43 -> 19:24:19
- **Win Rate:** 45.5% (45W / 54L / 1 Void)
- **Key Insight:** Structure alignment recovered slightly (55.3%). CCI extremes proved their worth: `overbought` (66.7%) and `oversold` (56.2%). `strong` ADX continued to lose heavily (33.3%).

### GROUP 4 (Trades 301 to 400)
- **Time Window:** 19:24:31 -> 20:07:02
- **Win Rate:** 54.1% (53W / 45L / 0 Voids)
- **Key Insight:** `moderate` ADX regimes thrived (66.7%). `oversold` CCI was phenomenal (88.9%).

---

## 3. Vulnerability Findings

### 3.1 The "HIGH Confidence" Trap
The original Level 2 policy was purely additive. A weak Level 1 signal (e.g., score 60) could hit a Support level (+8) and have oversold CCI (+4), pushing its final score above 80 (HIGH Confidence). However, in choppy or heavily trending markets, these bonuses were artificially inflating fundamentally weak setups.

### 3.2 Neutral CCI Leniancy
Whenever CCI hit an extreme (`oversold`/`overbought`), the win rate spiked (e.g., 88.9% in Group 4). Conversely, `neutral` CCI accounted for the vast majority of losses. The original `-2.0` penalty for a neutral CCI (abs < 35) was insufficient to suppress trades in choppy markets. Reversals require verified exhaustion.

### 3.3 Strong Trend Bleed
Level 2 relies on reversals. Across all 400 trades, whenever the `adx_regime` was `strong`, the win rate plummeted (often down to 33%). The previous `-8.0` penalty was easily offset if the trade simply hit a Support level (+8.0), meaning the system was still attempting to catch falling knives.

### 3.4 Manipulation Detector Leakage
Despite the user witnessing heavy manipulation, Auto-Ghost executed 401 trades without blocking a single one for manipulation at the moment of entry. A script (`check_tick_gaps.py`) verified that the tick flow from the broker was consistent and uninterrupted.
The issue was the `ManipulationDetector` logic:
- **Push & Snap:** It only flagged velocity spikes on the *exact single tick*. The flag cleared immediately on the next tick, allowing Auto-Ghost to enter.
- **Pinning:** It demanded prices stay within exactly two decimal points for 20 straight ticks, which is too strict for jittery OTC data.

---

## 4. Applied Hardening & Fixes

Based on these findings, the team implemented the following logic changes across the backend:

### 4.1 Level2PolicyConfig Extracted and Tightened
All hardcoded "magic numbers" in `market_context.py` were moved into a `Level2PolicyConfig` dataclass, with the following optimizations applied:
- **Neutral CCI Penalty:** Increased from `-2.0` to `-6.0`.
- **Neutral CCI Band:** Widened from `35.0` to `50.0`.
- **Strong Trend Suppression:** A `strong` ADX regime now blocks the trade *entirely* (via `suppress_reason`) unless the CCI is also at a confirmed extreme (`oversold`/`overbought`).
- **HIGH Confidence Floor:** Added `high_confidence_base_floor = 65.0`. A trade cannot achieve `HIGH` confidence unless its original baseline `oteo_score` was already strong enough to warrant it.
- **S/R Proximity:** Tightened from `0.45` ATR to `0.25` ATR so bonuses are only awarded on precise structure touches.

### 4.2 Manipulation Detector Persistence
The `ManipulationDetector` (`manipulation.py`) was rewritten for realistic OTC conditions:
- **Memory Block (Push & Snap):** When a velocity spike is detected, the `push_snap` flag now persists for **15 seconds** to allow the market shock to absorb before allowing trades.
- **Loosened Pinning Tolerance:** Instead of checking strict decimal equality, the detector now evaluates if the entire max/min range of the last 20 ticks is abnormally tight (less than 0.005% of the asset's average price).

### 4.3 Engine Performance Optimization (Prerequisite)
To ensure the tuned thresholds operate on clean data, `MarketContextEngine` was upgraded with `_cached_context`. Heavy indicators (ADX, CCI, Pivots) now strictly compute only when a 60-second candle closes, rather than on every tick. This eliminates the indicator noise that would have invalidated these new threshold settings.

## 5. Conclusion
The 401-trade session successfully stress-tested the Level 2 logic. The engine is now structurally hardened against false-positive indicator noise, silent async failures, manipulation shocks, and weak-exhaustion setups. The next Auto-Ghost session should yield a lower overall trade frequency, but a substantially more defensive win rate.