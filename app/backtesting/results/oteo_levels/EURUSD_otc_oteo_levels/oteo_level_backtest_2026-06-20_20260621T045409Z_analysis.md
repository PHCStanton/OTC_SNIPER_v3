# OTEO Replay Backtest Analysis

**Generated:** 2026-06-21T04:54:09Z  
**Total rows:** 1176  
**Settled trades:** 966  
**Payout:** 92%  
**Breakeven win-rate:** 52.08%  

## Overall Statistics

| Metric | Value |
| --- | --- |
| Trades (rows) | 1176 |
| Wins | 458 |
| Losses | 508 |
| Draws | 16 |
| Missing exit | 194 |
| Insufficient data | 0 |
| Win-rate | 47.4% |
| Net P/L (units) | -86.6400 |
| ROI | -9.0% |

## Level × Expiry Win-Rate Matrix

_Win-rate per (Level, Expiry) cell. ⚠️ = fewer than 30 settled trades — treat as indicative only._

| Level \ Expiry (s) | 15 | 30 | 60 | 90 | 120 | 180 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | 44.0% | 50.0% | 48.0% | 43.1% | 47.1% | 57.1% | 41.7% |
| L2 | 44.0% | 50.0% | 48.0% | 43.1% | 47.1% | 57.1% | 41.7% |

## Asset × Expiry Win-Rate Matrix

_Win-rate per (Asset, Expiry) cell. ⚠️ = fewer than 30 settled trades._

| Asset \ Expiry (s) | 15 | 30 | 60 | 90 | 120 | 180 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EURUSD_otc | 44.0% | 50.0% | 48.0% | 43.1% | 47.1% | 57.1% | 41.7% |

## Regime × Expiry Win-Rate Matrix

_Win-rate per (Regime, Expiry) cell. ⚠️ = fewer than 30 settled trades._

| Regime \ Expiry (s) | 15 | 30 | 60 | 90 | 120 | 180 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| None | 44.0% | 50.0% | 48.0% | 43.1% | 47.1% | 57.1% | 41.7% |

## Confidence × Expiry Win-Rate Matrix

_Win-rate per (Confidence, Expiry) cell. ⚠️ = fewer than 30 settled trades._

| Confidence \ Expiry (s) | 15 | 30 | 60 | 90 | 120 | 180 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HIGH | 55.6% ⚠️ n=18 | 50.0% ⚠️ n=20 | 40.0% ⚠️ n=20 | 40.0% ⚠️ n=20 | 40.0% ⚠️ n=20 | 62.5% ⚠️ n=16 | 50.0% ⚠️ n=12 |
| MEDIUM | 42.4% | 50.0% | 49.2% | 43.5% | 48.3% | 56.4% | 40.5% |

## Suppression Audit

### Level 2 Suppression Reasons
_No Level 2 suppressions recorded._

### Level 3 Suppression Reasons
_No Level 3 suppressions recorded._

## Recommendations

Breakeven win-rate at 92% payout: **52.08%**

🔴 **Overall win-rate 47.4% is below breakeven 52.08%** — the current strategy configuration does not have a positive edge at this payout.

✅ No asset exclusion candidates detected.

📈 **Best expiry:** 180s — win-rate 57.1% (n=126)
📉 **Worst expiry:** 300s — win-rate 41.7% (n=96)
