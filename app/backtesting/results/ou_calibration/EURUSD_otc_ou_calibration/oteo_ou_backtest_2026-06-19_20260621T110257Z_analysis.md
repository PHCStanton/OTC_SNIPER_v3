# Ornstein-Uhlenbeck (OU) Half-Life Calibration Report

**Generated:** 2026-06-21T11:02:59Z  
**Rolling Calibration Window:** 300 ticks  

## Overall Statistics Comparison

| Metric | Baseline (Static) | OU Filtered & Calibrated |
| --- | --- | --- |
| Total Signals Evaluated | 56728 | 8104 |
| Suppressed (Non-reverting) | 0 | 648 |
| Executed Trades | 56728 | 7456 |
| Wins | 29156 | 3846 |
| Losses | 26259 | 3415 |
| Win-Rate | 52.61% | 52.97% |
| Net P/L (units) | 564.5200 | 123.3200 |

## Expiry Duration Performance matrix (OU Calibrated Active)

_Win-rate per level × expiry cell for executed OU calibrated trades. ⚠️ = fewer than 30 trades._

Level | 15s | 30s | 60s | 90s | 120s | 180s | 300s
--- | --- | --- | --- | --- | --- | --- | ---
L1 | 50.2% n=3237 | 48.8% n=2682 | 50.1% n=2314 | 49.5% n=2222 | 48.9% n=2188 | 49.7% n=2189 | 54.9% n=2216
L2 | 51.1% n=5025 | 54.3% n=4241 | 54.2% n=3747 | 53.1% n=3652 | 51.1% n=3605 | 52.0% n=3612 | 56.7% n=3558
L3 | 50.8% n=3345 | 55.1% n=2816 | 56.3% n=2481 | 55.4% n=2431 | 54.4% n=2403 | 53.9% n=2407 | 54.4% n=2305

## Recommendations & Calibration Analysis

Breakeven win-rate at 92.0% payout: **52.08%**  
✅ **OU half-life calibration improved the win-rate** from 52.61% to 52.97%.