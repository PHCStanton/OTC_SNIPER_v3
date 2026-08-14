# Bayesian Signal Filter, Adaptive Expiries & Gate Interplay: Architectural Assessment & Refactoring Strategy

**Document ID**: `DEV-DOC-2026-08-12-BAYESIAN-ADAPTIVE-GATES`  
**Date**: August 12, 2026  
**Status**: DRAFT / APPROVED FOR IMPLEMENTATION  
**Target Systems**: `app/backend/services/extensions/`, `app/backend/services/auto_ghost.py`, `app/backend/services/journal_stats_service.py`, `shared/bayesian_prior_store.py`

---

## 1. Executive Summary

A comprehensive architectural and quantitative forensic investigation of OTC SNIPER v3's Bayesian filtering subsystem, trade duration telemetry, and volatility/liquidity gating layers was conducted across the 14,731-trade corpus.

### Key Takeaways:
1. **Severe Horizon Conflation**: **93.47% (13,769 / 14,731)** of all recorded historical trades are strictly 60-second (1-minute) expirations. The `BayesianSignalFilter` learns prior probabilities $P(\text{Win} \mid \text{Market Context})$ from these 60s outcomes but evaluates trade entry probabilities agnostic to execution duration.
2. **Extreme Non-60s Data Sparsity**: Contract durations other than 60s (15s, 30s, 45s, 120s, 300s) have negligible sample sizes ($N < 150$ for 15s/30s/120s), making multi-duration Bayesian parameter estimation statistically invalid.
3. **Execution-Prior Disconnect with Adaptive Expiries**: When `VolatilityAdaptiveExpiry` overrides the trade duration to 300s or 15s, the Bayesian filter approves/vetoes based on 60s expectations. If the trade resolves as a loss on a 300s horizon, `on_trade_outcome()` penalizes the 1-minute Bayesian prior, poisoning the core model.
4. **Protective Role of Volatility & Liquidity Gates**: Because volatility and liquidity are not part of the internal Bayesian feature vector, the **Volatility & Liquidity Gates act as mandatory physical guardrails** preventing the Bayesian filter from evaluating signals in market conditions where price dynamics stall or whip.
5. **Clean Two-Layer Decoupling**: The newly implemented **Ghost Journal & Knowledge Base Staging System** serves as an observational data collector across all expiries and remains **100% intact**. Execution guardrails are applied specifically to the live `BayesianSignalFilter` and Auto-Ghost trade router.

---

## 2. Empirical Dataset Distribution

A forensic sweep of all recorded trade sessions in `data/ghost_trades/sessions/*.jsonl` revealed the following duration profile:

```
========================================================================================
                      HISTORICAL TRADE EXPIRATION DISTRIBUTION
========================================================================================
Duration      Trades Count     % of Total     Win Rate (%)     Wins    Losses    Voids
────────────────────────────────────────────────────────────────────────────────────────
60s (1m)         13,769          93.47%          50.37%        6,733    6,635     401
300s (5m)           697           4.73%          51.19%          345      329      23
120s (2m)           137           0.93%          48.85%           64       67       6
45s                  62           0.42%          47.54%           29       32       1
30s                  41           0.28%          50.00%           20       20       1
15s                  23           0.16%          69.57%           16        7       0
77s / 65s             2           0.01%          50.00%            1        1       0
────────────────────────────────────────────────────────────────────────────────────────
TOTAL            14,731         100.00%          50.38%        7,208    7,091     432
========================================================================================
```

### Statistical Analysis:
* **Degrees of Freedom**: The feature space of `BayesianSignalFilter` spans 6 Market Regimes x 5 OTEO Bands x 5 Z-Score Bands x 2 Manipulation States x 2 Directions = 1,200 parameter cells.
* **Sample Sufficiency**:
  * For **60s**, N = 13,769 (~11.5 trades per cell, viable with Laplace smoothing).
  * For **300s**, N = 697 (~0.58 trades per cell, marginal / high variance).
  * For **15s / 30s / 120s**, N <= 137 (<0.1 trades per cell, statistically unviable; Laplace smoothing alpha=1.0 completely overrides empirical signal).

---

## 3. Current Bayesian Implementation Architecture

### 3.1 Feature Vector Extraction
In `app/backend/services/extensions/bayesian_signal_filter.py`:

```python
def _extract_features(self, oteo_result: Dict[str, Any]) -> Dict[str, str]:
    mc = oteo_result.get("market_context") or {}
    
    # 1. OTEO Score Band
    oteo_score = float(oteo_result.get("oteo_score") or 50.0)
    if oteo_score < 65: oteo_band = "<65"
    elif oteo_score < 75: oteo_band = "65-74"
    elif oteo_score < 85: oteo_band = "75-84"
    elif oteo_score < 93: oteo_band = "85-92"
    else: oteo_band = "93+"
    
    # 2. Regime, Confidence, Z-Band, Manipulation, Direction
    regime = str(oteo_result.get("regime_label") or mc.get("regime_label") or "UNKNOWN").upper()
    confidence = str(oteo_result.get("confidence") or "MEDIUM").upper()
    z_band = self._resolve_z_band(oteo_result.get("z_score") or mc.get("z_score"))
    manip = oteo_result.get("manipulation") or mc.get("manipulation")
    has_manip = "MANIP_TRUE" if bool(manip) else "MANIP_FALSE"
    direction = str(oteo_result.get("recommended") or "CALL").upper()

    return {
        "oteo_band": oteo_band,
        "regime": regime,
        "confidence": confidence,
        "z_band": z_band,
        "has_manip": has_manip,
        "direction": direction,
    }
```

### 3.2 Laplace-Smoothed Naive Bayes Formulation
For a candidate signal with extracted feature set F = {f_1, f_2, ..., f_k}:

P(Win | F) = P(Win) * Product(P(f_i | Win)) / [ P(Win) * Product(P(f_i | Win)) + P(Loss) * Product(P(f_i | Loss)) ]

Where Laplace smoothing (alpha = 1.0) is applied to feature counts:
P(f_i | Win) = (Count(f_i, Win) + alpha) / (Total Wins + 2*alpha)

### 3.3 The Core Deficiencies Identified
1. **Duration Agnosticism**: Contract duration T_exp in {15, 30, 60, 120, 300} is not present in F.
2. **Prior Starvation in Active File**: The deployed `app/data/ghost_trades/stats/bayesian_priors.json` contained only N=3 trades prior to staging, causing all probabilities to collapse to ~40%.
3. **Unchecked Feedback Poisoning**: `on_trade_outcome()` processes every completed trade regardless of whether its duration matches the training distribution.

---

## 4. Interaction with Volatility & Liquidity Gates

### 4.1 Sequential Execution Pipeline
Signals flow through `auto_ghost.py` in the following sequence:

1. Incoming Real-Time Tick
2. OTEO Base Signal Computation
3. Z-Score Gate
4. Regime Gate & Stability
5. Volatility Gate Bounds
6. Liquidity Gate Bounds
7. ADX / CCI Direction Gates
8. Bayesian Filter Veto Gate
9. Adaptive Expiry Duration Override
10. Pocket Option Trade Execution
11. Outcome Resolved
12. Bayesian on_trade_outcome Update

### 4.2 The Latent Feature & Structural Guardrail Relationship
* **The Problem**: Because `volatility_score` and `liquidity_score` are excluded from the Bayesian feature vector, the Bayesian probability calculator cannot differentiate between a high-momentum breakout in **high liquidity** versus a fake spike in **dead liquidity (10 ticks/min)**.
* **The Solution Provided by Gates**:
  * The **Liquidity Gate** (80 to 150 ticks/min) ensures that the market has sufficient microstructural depth for order execution and trend propagation.
  * The **Volatility Gate** (0.0002 to 0.0006 ATR) filters out flat/dead market phases where binary options fail to clear the strike price.
* **Conclusion**: Volatility and Liquidity Gates are **essential preconditions** that keep the market in the valid domain where Bayesian prior assumptions hold true.

---

## 5. Impact of Adaptive Expiries on Bayesian Accuracy

In `app/backend/services/extensions/volatility_adaptive_expiry.py`:

```python
# Volatility-Adaptive Duration Mapping
if vol_score < 30.0:    expiry = 300  # 5m (give low-vol mean-reversion time to resolve)
elif vol_score < 50.0:  expiry = 120  # 2m
elif vol_score < 70.0:  expiry = 60   # 1m (sweet spot)
elif vol_score < 85.0:  expiry = 30   # 30s
else:                   expiry = 15   # 15s (high-speed breakout)
```

### The Conflict:
1. **Regime Decay Over Time**: A microstructural directional edge identified by OTEO decays rapidly after 60 seconds due to stochastic Brownian motion. An entry that has a **58% win rate at 60s** often has a **45% win rate at 300s** because the initial momentum dissipates.
2. **False Vetoes / False Approvals**:
   * If a trade is sent as a **300s** contract, the Bayesian filter approves it because it expects a **60s** resolution.
   * If the trade loses at t=300s, `on_trade_outcome()` registers a `loss` for `oteo_band=85-92` and `regime=STRONG_MOMENTUM`.
   * Over time, high-quality 1-minute patterns are penalized and vetoed because of 5-minute expiry failures.

---

## 6. Architecture of the Decoupled Solution

To prevent data corruption while preserving long-term analytical capabilities, the system is separated into two strictly decoupled layers:

### Layer 1: Observational & Knowledge Base Staging (Ghost Journal)
* Collects telemetry across ALL contract durations (15s, 30s, 60s, 120s, 300s).
* Displays Adaptive Expiries performance in `AdaptiveExpiriesCard.jsx`.
* Stages candidate condition patterns into `condition_patterns.json`.
* Leaves empirical observations 100% intact without filtering bias.

### Layer 2: Live Execution & Veto Gating Engine (Auto-Ghost & Bayesian Filter)
* Gating is LOCKED strictly to 60-Second (1-Minute) benchmark horizon.
* `on_trade_outcome()` ONLY updates Bayesian priors for trades with duration == 60s.
* When Bayesian Gating is active, Auto-Ghost clamps execution to 60s.
* Protects the live trading account from uncalibrated multi-minute variance.

---

## 7. Recommended Implementation & Refactoring Strategy

### Phase 1: Immediate Execution Guardrails & Horizon Locking (Current Target)

#### 1. Guard `BayesianSignalFilter.on_trade_outcome()`
In `app/backend/services/extensions/bayesian_signal_filter.py`:
* Add a strict duration filter:
  ```python
  def on_trade_outcome(self, trade_data: Dict[str, Any]) -> None:
      outcome = trade_data.get("outcome")
      if outcome not in ("win", "loss"):
          return
      
      # PHASE 1 GUARD: Only train priors on the statistically established 60s benchmark
      exp_sec = trade_data.get("expiration_seconds", 60)
      if exp_sec != 60:
          logger.debug("Skipping Bayesian prior update for non-60s trade (%ss)", exp_sec)
          return
      ...
  ```

#### 2. Synchronize Auto-Ghost Expiry when Bayesian Filter is Active
In `app/backend/services/auto_ghost.py`:
* When `bayesian_filter_enabled` is `True`, ensure `expiration` defaults strictly to `60` seconds unless explicitly overridden by manual user test flags.
* In `VolatilityAdaptiveExpiry`, enforce `min_adaptive_expiry = 60` and `max_adaptive_expiry = 60` whenever Bayesian gating is engaged.

#### 3. Baseline Prior Seeding via Knowledge Base Staging
* Seed `app/data/ghost_trades/stats/bayesian_priors.json` from the 13,769 60-second historical trades using `JournalStatsService._extract_knowledge_updates()` so the Laplace probability calculations are robustly anchored.

---

### Phase 2: Future Stratified Multi-Duration Bayesian Model (Roadmap)

Once non-60s trades accumulate >= 500 observations per bucket in the Ghost Journal:
1. Extend `bayesian_priors.json` schema to partition by duration:
   ```json
   {
     "expiries": {
       "15s": { "total_wins": 0, "total_losses": 0, "feature_counts": {} },
       "60s": { "total_wins": 6733, "total_losses": 6635, "feature_counts": {} },
       "300s": { "total_wins": 345, "total_losses": 329, "feature_counts": {} }
     }
   }
   ```
2. Update `BayesianSignalFilter.predict_win_probability(oteo_result, target_duration=60)` to evaluate against the specific duration model.
3. Permit `VolatilityAdaptiveExpiry` to route signals to 15s or 300s only when the specific duration prior exceeds the minimum probability threshold.

---

## 8. Summary of Code Changes Required for Phase 1

| Component | Target File | Nature of Change |
|---|---|---|
| **Bayesian Filter** | `app/backend/services/extensions/bayesian_signal_filter.py` | Add `expiration_seconds == 60` check in `on_trade_outcome()`. |
| **Auto-Ghost Router** | `app/backend/services/auto_ghost.py` | Align default contract expiry to 60s when Bayesian gating is active. |
| **Adaptive Expiry Extension** | `app/backend/services/extensions/volatility_adaptive_expiry.py` | Ensure safe clamping to 60s when Bayesian gating is engaged. |
| **Prior Seeding** | `app/data/ghost_trades/stats/bayesian_priors.json` | Seed initial 1-minute historical baseline priors via transactional store. |
| **Unit Tests** | `tests/test_bayesian_signal_filter.py` | Add test cases verifying non-60s outcome rejection and 60s outcome persistence. |
