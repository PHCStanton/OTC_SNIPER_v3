# Hurst Exponent backtest & Calibration Analysis

**Generated:** 2026-06-21T09:17:40Z  
## Overall Statistics Comparison

| Metric | Baseline (Static) | Hurst Filtered |
| --- | --- | --- |
| Total Trades Evaluated | 56728 | 8104 |
| Vetoed/Suppressed | 0 | 8092 |
| Executed Trades | 56728 | 12 |
| Wins | 29156 | 9 |
| Losses | 26259 | 3 |
| Win-Rate | 52.61% | 75.00% |
| Net P/L (units) | 564.5200 | 5.2800 |

## Hurst Veto / Suppression Audit

| Suppression Gate | Count | Ratio |
| --- | --- | --- |
| regime_trending | 5535 | 68.3% |
| regime_chop | 2557 | 31.6% |

## Expiry Duration Performance matrix (Hurst Active)

_Win-rate per level × expiry cell for executed Hurst trades. ⚠️ = fewer than 30 trades._

Level | 15s | 30s | 60s | 90s | 120s | 180s | 300s
--- | --- | --- | --- | --- | --- | --- | ---
L1 | 50.4% n=2126 | 49.1% n=2143 | 49.5% n=2138 | 49.4% n=2148 | 49.0% n=2157 | 49.5% n=2160 | 54.7% n=2130
L2 | 52.0% n=3441 | 54.1% n=3483 | 53.6% n=3470 | 52.4% n=3479 | 51.5% n=3500 | 51.6% n=3509 | 56.7% n=3409
L3 | 51.5% n=2291 | 54.4% n=2314 | 55.0% n=2311 | 54.7% n=2314 | 54.9% n=2330 | 53.5% n=2334 | 54.6% n=2240

## Recommendations & Calibration Analysis

Breakeven win-rate at 92.0% payout: **52.08%**  
✅ **Hurst filtering improved the win-rate** from 52.61% to 75.00%.