# OTEO Replay Backtest Analysis

**Generated:** 2026-06-21T22:16:48Z  
**Total rows:** 65828  
**Settled trades:** 65162  
**Payout:** 92%  
**Breakeven win-rate:** 52.08%  

## Overall Statistics

| Metric | Value |
| --- | --- |
| Trades (rows) | 65828 |
| Wins | 34119 |
| Losses | 31043 |
| Draws | 338 |
| Missing exit | 328 |
| Insufficient data | 0 |
| Win-rate | 52.4% |
| Net P/L (units) | 346.4800 |
| ROI | 0.5% |

## Level × Expiry Win-Rate Matrix

_Win-rate per (Level, Expiry) cell. ⚠️ = fewer than 30 settled trades — treat as indicative only._

| Level \ Expiry (s) | 15 | 30 | 60 | 90 | 120 | 180 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | 50.5% | 50.3% | 52.1% | 52.0% | 51.0% | 52.9% | 49.7% |
| L2 | 50.3% | 50.0% | 50.5% | 53.2% | 53.8% | 58.7% | 51.4% |
| L3 | 52.7% | 52.5% | 50.7% | 51.7% | 52.8% | 56.9% | 53.9% |

## Asset × Expiry Win-Rate Matrix

_Win-rate per (Asset, Expiry) cell. ⚠️ = fewer than 30 settled trades._

| Asset \ Expiry (s) | 15 | 30 | 60 | 90 | 120 | 180 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CADCHF_otc | 51.1% | 50.8% | 51.0% | 52.5% | 52.8% | 56.6% | 51.7% |

## Regime × Expiry Win-Rate Matrix

_Win-rate per (Regime, Expiry) cell. ⚠️ = fewer than 30 settled trades._

| Regime \ Expiry (s) | 15 | 30 | 60 | 90 | 120 | 180 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BREAKOUT | 100.0% ⚠️ n=2 | 100.0% ⚠️ n=2 | 100.0% ⚠️ n=2 | 100.0% ⚠️ n=2 | 100.0% ⚠️ n=2 | 100.0% ⚠️ n=2 | 100.0% ⚠️ n=2 |
| CHOPPY | 47.3% | 50.2% | 47.3% | 50.2% | 49.8% | 46.9% | 44.1% |
| None | 47.5% | 43.1% | 44.5% | 30.8% | 26.9% | 37.5% | 44.7% |
| RANGE_BOUND | 55.7% | 55.5% | 52.6% | 53.1% | 54.8% | 57.3% | 56.0% |
| STRONG_MOMENTUM | 49.9% | 50.8% | 57.0% | 61.5% | 55.1% | 70.1% | 55.9% |
| TREND_PULLBACK | 46.6% | 44.1% | 47.3% | 49.8% | 49.2% | 53.9% | 43.8% |
| TREND_REVERSAL | 40.2% | 54.5% | 62.2% | 69.9% | 73.8% | 77.5% | 74.4% |

## Confidence × Expiry Win-Rate Matrix

_Win-rate per (Confidence, Expiry) cell. ⚠️ = fewer than 30 settled trades._

| Confidence \ Expiry (s) | 15 | 30 | 60 | 90 | 120 | 180 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HIGH | 51.8% | 51.8% | 51.2% | 53.0% | 54.0% | 58.1% | 52.7% |
| MEDIUM | 49.5% | 48.8% | 50.7% | 51.4% | 50.0% | 53.4% | 49.5% |

## Suppression Audit

### Level 2 Suppression Reasons
_No Level 2 suppressions recorded._

### Level 3 Suppression Reasons
_No Level 3 suppressions recorded._

## Recommendations

Breakeven win-rate at 92% payout: **52.08%**

✅ **Overall win-rate 52.4% exceeds breakeven 52.08%** — positive edge detected across the full sample.

✅ No asset exclusion candidates detected.

📈 **Best expiry:** 180s — win-rate 56.6% (n=9313)
📉 **Worst expiry:** 30s — win-rate 50.8% (n=9307)
