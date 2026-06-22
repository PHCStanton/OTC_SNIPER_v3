# Hurst Exponent backtest & Calibration Analysis

**Generated:** 2026-06-21T21:55:33Z  
## Overall Statistics Comparison

| Metric | Baseline (Static) | Hurst Filtered |
| --- | --- | --- |
| Total Trades Evaluated | 1176 | 168 |
| Vetoed/Suppressed | 0 | 168 |
| Executed Trades | 1176 | 0 |
| Wins | 458 | 0 |
| Losses | 508 | 0 |
| Win-Rate | 47.41% | 0.00% |
| Net P/L (units) | -86.6400 | 0.0000 |

## Hurst Veto / Suppression Audit

| Suppression Gate | Count | Ratio |
| --- | --- | --- |
| regime_chop | 168 | 100.0% |

## Expiry Duration Performance matrix (Hurst Active)

_Win-rate per level × expiry cell for executed Hurst trades. ⚠️ = fewer than 30 trades._

Level | 15s | 30s | 60s | 90s | 120s | 180s | 300s
--- | --- | --- | --- | --- | --- | --- | ---
L1 | 44.0% n=75 | 50.0% n=78 | 48.1% n=77 | 43.1% n=72 | 47.1% n=70 | 57.1% n=63 | 41.7% n=48
L2 | 44.0% n=75 | 50.0% n=78 | 48.1% n=77 | 43.1% n=72 | 47.1% n=70 | 57.1% n=63 | 41.7% n=48

## Timeframe & Day of the Week Performance (Hurst Active)

_Performance of executed Hurst trades grouped by day of the week and 4-hour blocks._

### Performance by Day of the Week

| Day of the Week | Executed Trades | Wins | Losses | Win-Rate | Net P/L |
| --- | --- | --- | --- | --- | --- |

### Performance by 4-Hour Rollover Blocks

| 4-Hour Block | UTC Actual Time | Executed Trades | Wins | Losses | Win-Rate | Net P/L |
| --- | --- | --- | --- | --- | --- | --- |
| Block 0 | 22:00 - 02:00 UTC | 0 | 0 | 0 | 0.00% | 0.00 |
| Block 1 | 02:00 - 06:00 UTC | 0 | 0 | 0 | 0.00% | 0.00 |
| Block 2 | 06:00 - 10:00 UTC | 0 | 0 | 0 | 0.00% | 0.00 |
| Block 3 | 10:00 - 14:00 UTC | 0 | 0 | 0 | 0.00% | 0.00 |
| Block 4 | 14:00 - 18:00 UTC | 0 | 0 | 0 | 0.00% | 0.00 |
| Block 5 | 18:00 - 22:00 UTC | 0 | 0 | 0 | 0.00% | 0.00 |

## Recommendations & Calibration Analysis

Breakeven win-rate at 92.0% payout: **52.08%**  
❌ **Hurst filtering did not improve the overall win-rate** (Baseline: 47.41%, Hurst: 0.00%).