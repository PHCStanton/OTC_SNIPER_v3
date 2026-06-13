# Historical Analyzer Mismatch Audit & Diagnostics

**Run Timestamp (UTC):** 2026-06-13 02:42:01 UTC
**Sessions Analyzed:** 1

## Executive Summary

| Metric | Count |
| --- | --- |
| Total Ghost Trades Parsed | 100 |
| Successfully Joined | 99 |
| Unjoined (Missing Signals) | 0 |
| Unjoined (Ambiguous Matches) | 1 |
| Missing Tick Files | 0 |
| Parsing Validation Errors/Warnings | 0 |

## Manipulation-First Diagnostics

### Global Performance Splits

| Setup Context | Trades | Settled | Wins | Losses | Win Rate | Net Profit | Expectancy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Manipulation Present | 47 | 47 | 23 | 24 | 48.94% | $-58.80 | -1.2511 |
| Manipulation Absent | 52 | 52 | 26 | 26 | 50.0% | $-43.00 | -0.8269 |

### Asset Performance Degradation Under Manipulation

Ranked by **Manipulation Frequency**:

| Asset | Total Trades | Manipulation Rate | Manip WR | Non-Manip WR | WR Delta | Expectancy Delta | Damage Factor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| USDARS_otc | 1 | 100.0% | 100.0% | 0.0% | 100.0% | 18.4000 | -18.4000 ⚠️ |
| GBPJPY_otc | 12 | 91.67% | 45.45% | 0.0% | 45.45% | 17.4545 | -17.4545 ⚠️ |
| EURNZD_otc | 14 | 85.71% | 58.33% | 100.0% | -41.67% | -15.7500 | 15.7500 ⚠️ |
| CADCHF_otc | 6 | 83.33% | 60.0% | 0.0% | 60.0% | 22.9200 | -22.9200 ⚠️ |
| GBPAUD_otc | 5 | 80.0% | 75.0% | 100.0% | -25.0% | -9.6000 | 9.6000 ⚠️ |
| EURJPY_otc | 7 | 71.43% | 20.0% | 100.0% | -80.0% | -30.7200 | 30.7200 ⚠️ |
| CHFJPY_otc | 10 | 70.0% | 28.57% | 0.0% | 28.57% | 10.8571 | -10.8571 ⚠️ |
| MADUSD_otc | 3 | 33.33% | 0.0% | 50.0% | -50.0% | -19.2000 | 19.2000 ⚠️ |
| AUDUSD_otc | 20 | 5.0% | 100.0% | 47.37% | 52.63% | 20.2105 | -20.2105 ⚠️ |
| NZDUSD_otc | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 20.0000 | -20.0000 ⚠️ |
| LBPUSD_otc | 8 | 0.0% | 0.0% | 37.5% | -37.5% | 5.7000 | -5.7000 ⚠️ |
| QARCNY_otc | 2 | 0.0% | 0.0% | 50.0% | -50.0% | 0.8000 | -0.8000 ⚠️ |
| GBPUSD_otc | 10 | 0.0% | 0.0% | 70.0% | -70.0% | -6.8800 | 6.8800 ⚠️ |

_⚠️ denotes small sample sizes (less than 5 trades) in one or both of the splits._

### Strategy Level Vulnerability Analysis

| Strategy Level | Total Trades | Manip Trades | Manip WR | Non-Manip WR | Win Rate Delta |
| --- | --- | --- | --- | --- | --- |
| LEVEL3 | 99 | 47 | 48.94% | 50.0% | -1.06% |

### Weakest UTC Hourly Windows Under Manipulation

Sorted by **Win Rate Degradation** (where manipulation hurt performance the most):

| Hour (UTC) | Total Trades | Manip Trades | Manip WR | Non-Manip WR | Degradation |
| --- | --- | --- | --- | --- | --- |
| 01:00 | 43 | 19 | 42.11% | 58.33% | 16.22% |
| 02:00 | 35 | 19 | 47.37% | 43.75% | -3.62% |
| 03:00 | 18 | 7 | 71.43% | 45.45% | -25.98% |
| 04:00 | 3 | 2 | 50.0% | 0.0% | -50.0% |

## Ambiguous Join Audits

| Trade ID | Asset | Direction | Entry Time (UTC) | Match Details |
| --- | --- | --- | --- | --- |
| 4c7f0650-9e81-4581-86be-86a3356f194a | GBPUSD_otc | CALL | 2026-06-13 02:56:42 UTC | Join Ambiguity: Ghost trade '4c7f0650-9e81-4581-86be-86a3356f194a' matched multiple distinct signals equidistantly (min drift: 0.0000s). Candidates: [(1781319402.606, 88.8), (1781319402.606, 89.3)] |

