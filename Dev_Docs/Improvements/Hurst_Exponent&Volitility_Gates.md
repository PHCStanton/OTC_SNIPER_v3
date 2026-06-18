OTC_SNIPER v3 – Hurst Exponent & Volatility Enhancements Proposal
Date: 2026-06-14
Prepared for: Pieter
Status: Ready for Implementation Planning

1. Hurst Exponent – Implementation Summary & Benefits
Recommended Implementation

Add a lightweight calculate_hurst() method in MarketContextEngine (or regime_classifier.py).
Use Rescaled Range (R/S) analysis on the last 200–400 ticks (fast, sufficient for our short-expiry environment).
Calculate once per closed candle and cache the value.
Expose hurst_exponent (0.0–1.0) in the market context payload sent to Auto-Ghost and the frontend.

How the App and Users Benefit

Dramatically improves TREND_REVERSAL detection (H < 0.45 + high |z-score| = high-probability exhaustion).
Better distinction between CHOP_WHIPSAW (H ≈ 0.5) and true RANGE_BOUND (H < 0.5 with reversion).
Reduces false signals in noisy, random-walk conditions.
Gives users clearer regime awareness in the Ghost Controller and Analysis panel.
Long-term: Enables memory-based learning (store which Hurst + regime combinations performed best per asset).

Settings Implementation (Ghost Controller)

Add under "Advanced Gates" tab:
Toggle: "Use Hurst Filter" (default: ON)
Slider: Min Hurst for Reversal (0.30 – 0.50, default 0.45)
Slider: Max Hurst for Trending (0.55 – 0.80, default 0.65)
Toggle: "Require Strong Hurst Confirmation" for momentum trades


Gate vs Other Options

Primary Recommendation: Use as a soft multiplier on Level 3 score rather than a hard gate initially (e.g. boost reversal score by 15–25% when H < 0.45).
Hard Gate Option: Block signals when H is in the random zone (0.48–0.52) during high volatility.
Hybrid: Start with multiplier, let AI Calibration (Phase 4) suggest optimal thresholds based on recent ghost performance.


2. Volatility Determination – Implementation Summary & Benefits
Recommended Implementation

Add calculate_volatility_score() in MarketContextEngine using:
ATR (relative to price)
Standard deviation of tick returns
Average tick interval (frequency)

Output a normalized 0.0–1.0 score.
Classify into Low / Medium / High volatility buckets.
Cache per closed candle.

How the App and Users Benefit

Enables dynamic expiry selection (High Vol → shorter expiry, Low Vol → longer expiry).
Improves signal filtering: Suppress reversals in High Volatility + Chop (common losing pattern).
Helps users quickly identify which assets are "tradable" right now.
Strong synergy with Hurst: Low H + Low Vol = excellent mean-reversion setups.

Settings Implementation (Ghost Controller)

Add under "Advanced Gates" tab:
Toggle: "Use Volatility Filter" (default: ON)
Volatility Classification thresholds (Low/Medium/High)
Auto Expiry Adjustment toggle (default: ON)
Slider: Min Volatility for Trading (avoid ultra-low vol)


Gate vs Other Options

Primary Recommendation: Use for smart expiry suggestion + soft suppression in High Vol + Chop regime.
Hard Gate Option: Block all signals when volatility is extreme and Hurst is near 0.5.
Best Combined Rule: Only allow reversals when volatility is Medium and Hurst is Low.


3. Additional Recommendations
High-Value Quick Wins

Composite Regime Score
Combine Hurst + Volatility + Z-Score + ADX into a single Setup Quality Score (0–100). Display this prominently in the Ghost Controller and sparkline. This gives users one clear number instead of many indicators.
Dynamic Expiry Engine
Let the Ghost Controller auto-recommend expiry based on volatility + Hurst. Example: High Vol + Low Hurst → 30s expiry.
AI Calibration Integration
Once the above are live, feed recent ghost performance + Hurst/Volatility data into the AI Review Loop. Let Grok suggest optimal gate values per asset or session.
Visual Enhancements
Color-coded regime labels in the sparkline and Ghost widget.
Small volatility meter (Low/Med/High) next to the asset name.
"Best Expiry" recommendation badge when a strong setup appears.


Why These Matter

They turn raw signals into actionable intelligence.
Reduce cognitive load for the user.
Improve win rate by matching strategy (OTEO reversals) to market conditions (volatility + memory).
Create a strong feedback loop for continuous improvement via the offline analyzer and AI.