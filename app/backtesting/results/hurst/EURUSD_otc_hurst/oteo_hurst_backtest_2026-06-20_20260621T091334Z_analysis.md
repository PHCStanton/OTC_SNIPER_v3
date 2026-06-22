# Hurst Exponent backtest & Calibration Analysis

**Generated:** 2026-06-21T09:13:34Z  
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

## Recommendations & Calibration Analysis

Breakeven win-rate at 92.0% payout: **52.08%**  
❌ **Hurst filtering did not improve the overall win-rate** (Baseline: 47.41%, Hurst: 0.00%).