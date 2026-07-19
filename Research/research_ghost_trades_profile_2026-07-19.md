# Research Paper: Auto-Ghost Trades Winning Asset Profiling (June 15 – July 12, 2026)
**Date Generated:** 2026-07-19

## 1. Executive Summary
This report analyzes 2,362 historical Auto-Ghost trades executed between **June 15, 2026 and July 12, 2026** (excluding the current week). The goal is to identify the top 5 performing winning assets, sketch their statistical "winning profile" against Volatility, Liquidity, and Manipulation, and analyze expiry duration similarities.

Based on cumulative net profit (requiring a minimum of 15 trades for statistical relevance), the top 5 performing assets are:
1. **AUDCAD_otc** (Net Profit: +$279.80)
2. **USDCHF_otc** (Net Profit: +$258.40)
3. **ZARUSD_otc** (Net Profit: +$220.40)
4. **NGNUSD_otc** (Net Profit: +$208.40)
5. **USDARS_otc** (Net Profit: +$199.40)

---

## 2. Top 5 Asset Comparison Matrix

| Asset | Total Trades | Win-Rate | Net Profit | Avg Tick Freq | Avg Sigmoid Liq | Avg ATR Ratio | Impact of Manipulation |
|---|---|---|---|---|---|---|---|
| **AUDCAD_otc** | 127 | 58.1% | +$279.80 | 130.1 /min | 55.5% | 0.0979% | **Severe**: WR drops from 67.9% to 50.0% |
| **USDCHF_otc** | 80 | 60.8% | +$258.40 | 124.4 /min | 53.6% | 0.0840% | **Minor**: WR drops from 61.3% to 58.8% |
| **ZARUSD_otc** | 61 | 61.7% | +$220.40 | 121.9 /min | 52.4% | 0.0943% | **None**: No manipulation flags recorded |
| **NGNUSD_otc** | 50 | 63.3% | +$208.40 | 124.8 /min | 53.9% | 0.1327% | **None**: No manipulation flags recorded |
| **USDARS_otc** | 39 | 65.8% | +$199.40 | 124.0 /min | 53.3% | 0.0257% | **High Tolerance**: WR stays 64.5% despite 82% manip rate |

---

## 3. Detailed Winning Profiles

### 👤 Profile 1: AUDCAD_otc
* **Volatility Profile:** Fits best in medium-to-strong volatility. Avg ATR Ratio is 0.0979%. It performs best in `weak` ADX regimes (64.5% WR, n=31) and `strong` ADX regimes (60.0% WR, n=45).
* **Liquidity Profile:** Average tick frequency of 130.1 ticks/min (Sigmoid: 55.5%). Wins and losses occur at almost identical liquidity levels, indicating liquidity is not the differentiating factor.
* **Manipulation Sensitivity:** **Extremely high.**
  * Without manipulation: **67.9% WR** (57 trades)
  * With manipulation: **50.0% WR** (70 trades)
  * *Insight:* Manipulation completely negates the edge on this asset.
* **Expiries:** Mostly 60s (118 trades, 57.6% WR). 15s performed exceptionally well (5 trades, 80.0% WR).

### 👤 Profile 2: USDCHF_otc
* **Volatility Profile:** Strong mean-reversion characteristics. Avg ATR Ratio is 0.0840%. It performs best in `unavailable` (82.4% WR, n=17) and `weak` ADX regimes (70.4% WR, n=27). Win rate degrades severely in `strong` ADX regimes (**36.8% WR**, n=19).
  * *Insight:* Avoid trading USDCHF_otc in trending markets (strong ADX).
* **Liquidity Profile:** Average tick frequency of 124.4 ticks/min (Sigmoid: 53.6%). Stable across wins and losses.
* **Manipulation Sensitivity:** **Low.**
  * Without manipulation: **61.3% WR** (63 trades)
  * With manipulation: **58.8% WR** (17 trades)
* **Expiries:** Exclusively 60s (79 trades, 60.8% WR).

### 👤 Profile 3: ZARUSD_otc
* **Volatility Profile:** Trend-friendly reversal asset. Avg ATR Ratio is 0.0943%. It performs best in `strong` ADX regimes (72.7% WR, n=22) and worst in `weak` ADX regimes (35.7% WR, n=14).
* **Liquidity Profile:** Average tick frequency of 121.9 ticks/min (Sigmoid: 52.4%).
* **Manipulation Sensitivity:** **Zero.** No trades were flagged for manipulation.
* **Expiries:** Mostly 60s (58 trades, 62.1% WR).

### 👤 Profile 4: NGNUSD_otc
* **Volatility Profile:** High-beta asset. Avg ATR Ratio is 0.1327% (highest in the top 5). Performs well under both `weak` ADX (72.7% WR, n=11) and `strong` ADX (63.6% WR, n=22).
* **Liquidity Profile:** Average tick frequency of 124.8 ticks/min (Sigmoid: 53.9%).
* **Manipulation Sensitivity:** **Zero.** No trades were flagged for manipulation.
* **Expiries:** Mostly 60s (47 trades, 61.7% WR).

### 👤 Profile 5: USDARS_otc
* **Volatility Profile:** Low-beta asset. Avg ATR Ratio is 0.0257% (lowest in the top 5). Performs best in `moderate` ADX (100% WR, n=5) and `unavailable` (70.0% WR, n=20).
* **Liquidity Profile:** Average tick frequency of 124.0 ticks/min (Sigmoid: 53.3%).
* **Manipulation Sensitivity:** **Highly Tolerant.**
  * 82% of all trades (32/39) occurred under manipulation, yet the asset maintained a **64.5% WR**.
  * *Insight:* The OTEO logic successfully filters or adapts to USDARS manipulation, or the manipulation itself is mean-reverting.
* **Expiries:** Mostly 60s (36 trades, 63.9% WR). 15s had a 100% WR (n=2).

---

## 4. Expiry Similarity Analysis
Across all top 5 performing assets, **60s is the absolute dominant expiry duration**, accounting for 96.8% of all executed trades.
* Expiries other than 60s (like 15s and 300s) are rare but show positive win rates where sample sizes are small (e.g., AUDCAD 15s: 80% WR, USDARS 15s: 100% WR).
* The uniformity in expiries suggests the Auto-Ghost trader was mostly configured with static 60s expiries during this time window.

---

## 5. Strategic Recommendations

1. **Implement Dynamic Asset-Based Manipulation Vetoes:**
   * **AUDCAD_otc** must have a hard manipulation veto enabled. A 67.9% WR dropping to 50.0% represents a massive loss of edge.
   * **USDARS_otc** does not need a strict manipulation veto, as it maintains a high WR (64.5%) under active manipulation.
2. **Apply ADX Regime Filtering per Asset:**
   * **USDCHF_otc** should be restricted from executing signals when the ADX regime is `strong` (currently 36.8% WR).
   * **ZARUSD_otc** should be restricted from executing signals when the ADX regime is `weak` (currently 35.7% WR).
3. **Calibrate Liquidity Gates:**
   * The average tick frequency across all winning profiles sits in the **120–130 ticks/min** range (which maps to exactly **52–55%** on the newly implemented Sigmoid scale).
   * **Rule of Thumb:** Auto-Ghost should target a Liquidity score gate of **30% to 70%** for these assets to ensure they are traded during their optimal liquidity window.
