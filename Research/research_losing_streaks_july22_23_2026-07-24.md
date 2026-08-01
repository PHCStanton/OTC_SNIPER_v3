# Forensic Investigation Report — Ghost Trades Losing Streaks (July 22–23, 2026)
**Date of Investigation:** 2026-07-24  
**Investigator:** @Investigator  
**Scope:** `app/data/ghost_trades/sessions` (July 22, 2026 to July 23, 2026)

---

## Executive Summary

A comprehensive read-only forensic analysis of all 87 ghost trades recorded across Wednesday, July 22, 2026, and Thursday, July 23, 2026, was conducted to isolate the exact market conditions responsible for consecutive losing streaks.

### Key Performance Metrics
* **Total Executed Trades:** 87
* **Wins:** 34 | **Losses:** 43 | **Voids:** 10
* **Overall Win Rate (valid trades):** **44.16%**
* **Wednesday, July 22:** 43 trades (17 Wins, 20 Losses, 6 Voids) — **45.95% WR** | PnL: -$112.80
* **Thursday, July 23:** 44 trades (17 Wins, 23 Losses, 4 Voids) — **42.50% WR** | PnL: -$167.20
* **Identified Losing Streaks (≥ 3 consecutive losses):** 7 distinct streak clusters accounting for **28 of the 43 total losses (65.1%)**.

---

## 🔍 Root Cause Breakdown

### 1. Primary Failure Mode: `TREND_PULLBACK` Regime Collapse (21.7% WR)
* **Finding:** Out of 43 total losses, **25 losses (58.1%)** occurred under `TREND_PULLBACK` (18 losses) and `TREND_REVERSAL` (7 losses) regimes.
* `TREND_PULLBACK` yielded an abysmal **21.7% Win Rate** (5 Wins vs. 18 Losses). 14 of these 18 losses occurred inside consecutive losing streaks!
* **Diagnosis:** Counter-trend or pullback entries in weak/moderate trend regimes were attempting 60-second reversals against active micro-trends that failed to pull back within 1 minute.
* **Contrast:** `RANGE_BOUND` maintained **53.1% WR** and `STRONG_MOMENTUM` maintained **72.7% WR**.

### 2. Secondary Failure Mode: Static 60s Expiry in Ultra-Low Volatility (< 30)
* **Finding:** **100% of the trades (77 out of 77 valid trades)** occurred during Volatility Scores **< 30.0** (range: 2.9 to 23.1).
* **Impact of Adaptive Expiries:**
  * All trades were forced to execute at a **static 60-second expiration** (`expiration_seconds: 60`).
  * Under our newly implemented **Standalone Volatility-Adaptive Expiry Extension**, a Volatility Score < 30 automatically assigns a **300s (5-minute)** broker interval.
  * In ultra-low volatility conditions, 60 seconds is too short for price to complete its mean-reversion move, leaving trades trapped at entry noise. 300s gives the price 5 full candles to reach structural support/resistance.

### 3. Time-of-Day Risk Windows (UTC Roll-over)
* **23:00 – 01:00 UTC (Late US / Early Asian Roll-over):**
  * Hour 23:00 UTC: 23 trades | 9 Wins / 14 Losses (**39.1% WR**, 10 streak losses).
  * Hour 00:00 UTC: 5 trades | 1 Win / 4 Losses (**20.0% WR**, 4 streak losses).
* **02:00 – 03:00 UTC:**
  * Hour 02:00 UTC: 13 trades | 5 Wins / 8 Losses (**38.5% WR**, 7 streak losses).
* **Contrast (London Session):** Hour 09:00 UTC yielded a **64.3% Win Rate** (9 Wins vs. 5 Losses).

### 4. Manipulation Drag (`push_snap`)
* `push_snap` manipulation was active in 38 out of 87 trades, causing **21 losses**. While low-severity push-snaps (< 0.15) were occasionally tolerated, un-gated manipulation severely dragged performance during low-volatility hours.

---

## 📋 Comprehensive Losing Streaks Table

| Streak # | Date & Time Range (UTC) | Count | Assets Involved | Primary Regimes | Volatility | Manipulation Present |
|---|---|---|---|---|---|---|
| **#1** | July 22 08:49 – 09:29 | 6 | EURCHF_otc, USDJPY_otc | TREND_REVERSAL, TREND_PULLBACK | 3.1 – 12.5 | `push_snap` (up to 0.207) |
| **#2** | July 22 23:37 – 23:38 | 3 | AUDUSD_otc, USDJPY_otc, GBPAUD_otc | TREND_PULLBACK | 3.0 – 8.2 | `push_snap` (0.041) |
| **#3** | July 22 23:44 – July 23 00:31 | 4 | USDJPY_otc, AUDUSD_otc, USDCAD_otc, AUDCHF_otc | TREND_PULLBACK, RANGE_BOUND, TREND_REVERSAL | 2.9 – 19.6 | `push_snap` (0.102) |
| **#4** | July 23 00:42 – 00:59 | 3 | AUDCHF_otc, AUDCAD_otc | RANGE_BOUND, TREND_PULLBACK | 10.0 – 21.1 | `push_snap` (up to 0.256) |
| **#5** | July 23 02:10 – 02:16 | 3 | CADCHF_otc, GBPUSD_otc | RANGE_BOUND, TREND_PULLBACK | 4.8 – 20.8 | `push_snap` (0.056) |
| **#6** | July 23 02:30 – 05:19 | 5 | AUDCAD_otc, CADCHF_otc, AUDCHF_otc, CADJPY_otc | TREND_PULLBACK, RANGE_BOUND, STRONG_MOMENTUM | 8.0 – 23.1 | `push_snap` (0.048) |
| **#7** | July 23 23:39 – 23:58 | 4 | AUDCHF_otc, AUDNZD_otc | RANGE_BOUND, TREND_PULLBACK | 12.5 – 21.8 | `push_snap` (up to 0.129) |

---

## 🎯 Recommendations & Actionable Avoidance Rules

1. **Activate ADX Trend Gate for `TREND_PULLBACK`:**
   * Require ADX Gate to veto counter-trend setups when regime is `TREND_PULLBACK` or `TREND_REVERSAL` unless `reversal_friendly` is explicitly verified.
2. **Deploy Standalone Volatility-Adaptive Expiries (Phase 2):**
   * Automatically transition all trades with Volatility < 30 from static 60s to **300s (5m)** expiries. This gives low-volatility mean-reversion trades time to play out.
3. **Restrict Trading Window (Time-of-Day Filter):**
   * Pause or set Auto-Ghost to conservative mode during **23:00 – 01:00 UTC** and **02:00 – 03:00 UTC** due to poor liquidity/low-volatility drag.
4. **Enforce Manipulation Severity Hard Veto (> 0.15):**
   * Hard-veto entries when `push_snap` severity exceeds 0.15 during low-volatility windows.
