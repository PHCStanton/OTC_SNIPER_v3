# Kalman Filter Pre-Filtering Backtest Report

**Generated:** 2026-06-21T14:27:35Z  
**Kalman configuration:** Q=1.0e-09, R=1.0e-07  

## Overall Statistics Comparison

| Metric | Baseline (Raw Ticks) | Kalman Filtered Ticks |
| --- | --- | --- |
| Total Trades Evaluated | 56728 | 35714 |
| Wins | 29156 | 19285 |
| Losses | 26259 | 15775 |
| Win-Rate | 52.61% | 55.01% |
| Net P/L (units) | 564.5200 | 1967.2000 |

## Expiry Duration Performance matrix (Kalman Active)

_Win-rate per level × expiry cell for executed Kalman-smoothed trades. ⚠️ = fewer than 30 trades._

Level | 15s | 30s | 60s | 90s | 120s | 180s | 300s
--- | --- | --- | --- | --- | --- | --- | ---
L1 | 49.0% n=681 | 49.5% n=687 | 50.5% n=687 | 49.9% n=694 | 49.0% n=688 | 49.2% n=691 | 53.3% n=685
L2 | 55.6% n=2406 | 60.6% n=2428 | 56.8% n=2444 | 53.9% n=2459 | 55.5% n=2454 | 52.4% n=2473 | 51.6% n=2423
L3 | 54.9% n=1856 | 61.1% n=1870 | 58.1% n=1882 | 55.2% n=1889 | 58.6% n=1891 | 55.3% n=1904 | 52.8% n=1868

## Recommendations & Calibration Analysis

Breakeven win-rate at 92.0% payout: **52.08%**  
✅ **Kalman pre-filtering improved the win-rate** from 52.61% to 55.01%.