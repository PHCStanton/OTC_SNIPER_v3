# Spike Pockets & Timeframe Backtest Report

**Generated:** 2026-06-21T19:00:18Z  

## 1. Overall Statistics Comparison

* **Total Evaluated Signals:** 56728
* **Settled Trades:** 55415
* **Wins:** 29156 | **Losses:** 26259
* **Cumulative Win-Rate:** 52.61%
* **Cumulative P/L (units):** 564.5200

## 2. Pocket Durations & Active Regimes

| Pocket State | Count | Avg Duration (sec) | Dominant Regime |
| --- | --- | --- | --- |
| Vol:HIGH | Liq:HIGH | Manip:LOW | 4 | 14.8s | TREND_PULLBACK |
| Vol:HIGH | Liq:HIGH | Manip:MEDIUM | 1 | 2.6s | TREND_PULLBACK |
| Vol:HIGH | Liq:LOW | Manip:LOW | 3 | 29.5s | TREND_PULLBACK |
| Vol:LOW | Liq:HIGH | Manip:LOW | 191 | 402.3s | TREND_PULLBACK |
| Vol:LOW | Liq:HIGH | Manip:MEDIUM | 91 | 1.8s | TREND_PULLBACK |
| Vol:LOW | Liq:LOW | Manip:LOW | 2 | 2.8s | UNKNOWN |
| Vol:MEDIUM | Liq:HIGH | Manip:LOW | 98 | 10.1s | TREND_PULLBACK |
| Vol:MEDIUM | Liq:HIGH | Manip:MEDIUM | 4 | 2.5s | TREND_PULLBACK |
| Vol:MEDIUM | Liq:LOW | Manip:LOW | 2 | 382.6s | STRONG_MOMENTUM |
| Vol:MEDIUM | Liq:MEDIUM | Manip:LOW | 1 | 29.5s | RANGE_BOUND |

## 3. Pocket Performance Matrix

_Win-rate and trade counts of executed signals under specific spike pocket states._

Pocket State | 15s | 30s | 60s | 90s | 120s | 180s | 300s
--- | --- | --- | --- | --- | --- | --- | ---
Vol:HIGH | Liq:HIGH | Manip:LOW | 52.6% n=19 | 63.2% n=19 | 72.2% n=18 | 78.9% n=19 | 78.9% n=19 | 78.9% n=19 | 78.9% n=19
Vol:HIGH | Liq:HIGH | Manip:MEDIUM | 100.0% ⚠️ n=1 | 0.0% ⚠️ n=1 | 100.0% ⚠️ n=1 | 100.0% ⚠️ n=1 | 100.0% ⚠️ n=1 | 100.0% ⚠️ n=1 | 100.0% ⚠️ n=1
Vol:HIGH | Liq:LOW | Manip:LOW | 0.0% ⚠️ n=7 | 0.0% ⚠️ n=7 | 0.0% ⚠️ n=7 | 0.0% ⚠️ n=7 | 57.1% ⚠️ n=7 | 0.0% ⚠️ n=7 | 14.3% ⚠️ n=7
Vol:LOW | Liq:HIGH | Manip:LOW | 51.4% n=7248 | 52.5% n=7330 | 52.9% n=7304 | 51.7% n=7337 | 50.8% n=7355 | 51.4% n=7408 | 55.2% n=7202
Vol:LOW | Liq:HIGH | Manip:MEDIUM | 37.8% n=82 | 33.3% n=81 | 18.3% n=82 | 46.3% n=82 | 48.1% n=81 | 35.4% n=82 | 40.5% n=79
Vol:LOW | Liq:LOW | Manip:LOW | 66.7% ⚠️ n=6 | 0.0% ⚠️ n=6 | 0.0% ⚠️ n=6 | 0.0% ⚠️ n=6 | 0.0% ⚠️ n=6 | 0.0% ⚠️ n=6 | 0.0% ⚠️ n=6
Vol:MEDIUM | Liq:HIGH | Manip:LOW | 53.9% n=471 | 62.1% n=472 | 59.1% n=477 | 61.7% n=465 | 65.6% n=482 | 57.9% n=456 | 63.0% n=441
Vol:MEDIUM | Liq:HIGH | Manip:MEDIUM | 33.3% ⚠️ n=6 | 33.3% ⚠️ n=6 | 100.0% ⚠️ n=6 | 33.3% ⚠️ n=6 | 66.7% ⚠️ n=6 | 66.7% ⚠️ n=6 | 66.7% ⚠️ n=6
Vol:MEDIUM | Liq:LOW | Manip:LOW | 66.7% ⚠️ n=9 | 66.7% ⚠️ n=9 | 66.7% ⚠️ n=9 | 66.7% ⚠️ n=9 | 66.7% ⚠️ n=9 | 66.7% ⚠️ n=9 | 66.7% ⚠️ n=9
Vol:MEDIUM | Liq:MEDIUM | Manip:LOW | 100.0% ⚠️ n=9 | 100.0% ⚠️ n=9 | 66.7% ⚠️ n=9 | 66.7% ⚠️ n=9 | 100.0% ⚠️ n=9 | 33.3% ⚠️ n=9 | 100.0% ⚠️ n=9

## 4. Pocket Option 22:00 UTC Start Timeframe Performance

_Aggregated win-rate by 4-Hour block offsets from 22:00 UTC rollover start._

| 4-Hour Block | UTC Actual Time | Settled Trades | Win-Rate | Net P/L |
| --- | --- | --- | --- | --- |
| Block 0 | 22:00 - 02:00 UTC | 16340 | 44.47% | -2387.36 |
| Block 1 | 02:00 - 06:00 UTC | 772 | 50.00% | -30.88 |
| Block 2 | 06:00 - 10:00 UTC | 14844 | 52.30% | 62.88 |
| Block 3 | 10:00 - 14:00 UTC | 0 | 0.00% | 0.00 |
| Block 4 | 14:00 - 18:00 UTC | 0 | 0.00% | 0.00 |
| Block 5 | 18:00 - 22:00 UTC | 23459 | 58.57% | 2919.88 |

## 5. Strategic Recommendations & Findings

Breakeven win-rate at 92.0% payout: **52.08%**  

### Recommended Spike Pockets to Target
* **Vol:HIGH | Liq:HIGH | Manip:LOW** at **90s** expiry: **78.95%** win-rate (n=19)
* **Vol:HIGH | Liq:HIGH | Manip:LOW** at **120s** expiry: **78.95%** win-rate (n=19)
* **Vol:HIGH | Liq:HIGH | Manip:LOW** at **180s** expiry: **78.95%** win-rate (n=19)
* **Vol:HIGH | Liq:HIGH | Manip:LOW** at **300s** expiry: **78.95%** win-rate (n=19)
* **Vol:HIGH | Liq:HIGH | Manip:LOW** at **60s** expiry: **72.22%** win-rate (n=18)

### Spike Pockets to Avoid
* **Vol:LOW | Liq:HIGH | Manip:MEDIUM** at **60s** expiry: **18.29%** win-rate (n=82)
* **Vol:LOW | Liq:HIGH | Manip:MEDIUM** at **30s** expiry: **33.33%** win-rate (n=81)
* **Vol:LOW | Liq:HIGH | Manip:MEDIUM** at **180s** expiry: **35.37%** win-rate (n=82)
* **Vol:LOW | Liq:HIGH | Manip:MEDIUM** at **15s** expiry: **37.80%** win-rate (n=82)
* **Vol:LOW | Liq:HIGH | Manip:MEDIUM** at **300s** expiry: **40.51%** win-rate (n=79)