# Historical Analyzer — Full Analysis Report

**Run Timestamp (UTC):** 2026-06-13 04:28:57 UTC
**Sessions Analyzed:** 198
**Phases Run:** Phase 1 + Phase 2 + Phase 3

---

## Phase 1 — Join Summary

| Metric | Count |
| --- | --- |
| Total Ghost Trades Parsed | 10207 |
| Successfully Joined | 9999 |
| Unjoined (Missing Signals) | 19 |
| Unjoined (Ambiguous Matches) | 189 |
| Missing Tick Files | 27 |
| Parsing Validation Errors/Warnings | 1435 |

---

## Phase 2 — Manipulation-First Diagnostics

### Global Performance Splits

| Setup Context | Trades | Settled | Wins | Losses | Win Rate | Net Profit | Expectancy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Manipulation Present | 632 | 629 | 331 | 298 | 52.62% | $110.80 | 0.1753 |
| Manipulation Absent | 9367 | 9121 | 4577 | 4544 | 50.18% | $-16157.18 | -1.7249 |

### Asset Performance Under Manipulation (Ranked by Frequency)

| Asset | Total Trades | Manip Rate | Manip WR | Non-Manip WR | WR Delta | Exp Delta | Damage Factor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| USDINR_otc | 1 | 100.0% | 0.0% | 0.0% | 0.0% | -20.0000 | 20.0000 ⚠️ |
| USDVND_otc | 1 | 100.0% | 100.0% | 0.0% | 100.0% | 18.4000 | -18.4000 ⚠️ |
| CHFNOK_otc | 7 | 71.43% | 20.0% | 0.0% | 20.0% | 12.6400 | -12.6400 ⚠️ |
| USDDZD_otc | 12 | 66.67% | 25.0% | 50.0% | -25.0% | -9.6000 | 9.6000 ⚠️ |
| USDPKR_otc | 3 | 66.67% | 0.0% | 0.0% | 0.0% | 0.0000 | -0.0000 ⚠️ |
| USDARS_otc | 17 | 64.71% | 45.45% | 16.67% | 28.78% | 11.9545 | -11.9545 ⚠️ |
| GBPJPY_otc | 23 | 60.87% | 42.86% | 55.56% | -12.7% | -5.8318 | 5.8318 ⚠️ |
| EURJPY_otc | 120 | 52.5% | 47.62% | 54.39% | -6.77% | -5.2335 | 5.2335 |
| JODCNY_otc | 16 | 43.75% | 71.43% | 33.33% | 38.1% | 14.6286 | -14.6286 ⚠️ |
| OMRCNY_otc | 12 | 41.67% | 60.0% | 85.71% | -25.71% | -14.4743 | 14.4743 ⚠️ |
| USDMXN_otc | 5 | 40.0% | 50.0% | 33.33% | 16.67% | 6.4000 | -6.4000 ⚠️ |
| CHFJPY_otc | 87 | 37.93% | 60.61% | 44.44% | 16.17% | 12.7826 | -12.7826 |
| CADJPY_otc | 103 | 34.95% | 42.86% | 50.75% | -7.89% | -1.0458 | 1.0458 |
| EURNZD_otc | 309 | 24.6% | 56.58% | 49.79% | 6.79% | 4.8400 | -4.8400 |
| GBPAUD_otc | 122 | 22.13% | 59.26% | 49.47% | 9.79% | 2.5457 | -2.5457 |
| AUDNZD_otc | 348 | 19.83% | 50.72% | 45.88% | 4.84% | 1.7327 | -1.7327 |
| NZDJPY_otc | 16 | 18.75% | 100.0% | 53.85% | 46.15% | 12.3948 | -12.3948 ⚠️ |
| EURRUB_otc | 22 | 18.18% | 100.0% | 55.56% | 44.44% | 17.5250 | -17.5250 ⚠️ |
| #AXP_otc | 35 | 17.14% | 40.0% | 53.57% | -13.57% | -1.9719 | 1.9719 ⚠️ |
| USDJPY_otc | 65 | 13.85% | 75.0% | 42.86% | 32.14% | 19.2645 | -19.2645 ⚠️ |
| USDCHF_otc | 164 | 9.76% | 43.75% | 46.26% | -2.51% | -1.2443 | 1.2443 |
| AUDCAD_otc | 849 | 9.66% | 53.66% | 50.8% | 2.86% | 1.4027 | -1.4027 |
| EURCHF_otc | 442 | 7.92% | 45.71% | 50.0% | -4.29% | 0.8126 | -0.8126 |
| #AAPL_otc | 32 | 6.25% | 100.0% | 33.33% | 66.67% | 36.8013 | -36.8013 ⚠️ |
| CADCHF_otc | 605 | 5.62% | 58.82% | 51.51% | 7.31% | 2.5679 | -2.5679 |
| AUDCHF_otc | 757 | 4.62% | 54.29% | 52.59% | 1.7% | 1.3875 | -1.3875 |
| MADUSD_otc | 144 | 2.78% | 50.0% | 53.96% | -3.96% | -1.0657 | 1.0657 ⚠️ |
| BHDCNY_otc | 115 | 2.61% | 66.67% | 35.14% | 31.53% | 10.3795 | -10.3795 ⚠️ |
| GBPUSD_otc | 577 | 2.6% | 46.67% | 51.0% | -4.33% | -1.3639 | 1.3639 |
| EURTRY_otc | 87 | 1.15% | 100.0% | 47.62% | 52.38% | 27.0390 | -27.0390 ⚠️ |
| EURGBP_otc | 948 | 1.05% | 50.0% | 51.83% | -1.83% | 0.8257 | -0.8257 |
| EURUSD_otc | 1457 | 0.75% | 54.55% | 50.99% | 3.56% | 3.1785 | -3.1785 |
| NZDUSD_otc | 155 | 0.65% | 100.0% | 49.02% | 50.98% | 21.1091 | -21.1091 ⚠️ |
| AUDUSD_otc | 858 | 0.12% | 100.0% | 50.47% | 49.53% | 19.4975 | -19.4975 ⚠️ |
| IRRUSD_otc | 10 | 0.0% | 0.0% | 30.0% | -30.0% | 22.4800 | -22.4800 ⚠️ |
| EURHUF_otc | 3 | 0.0% | 0.0% | 33.33% | -33.33% | 9.0833 | -9.0833 ⚠️ |
| UAHUSD_otc | 24 | 0.0% | 0.0% | 56.52% | -56.52% | -1.5917 | 1.5917 ⚠️ |
| #XOM_otc | 2 | 0.0% | 0.0% | 50.0% | -50.0% | 1.5000 | -1.5000 ⚠️ |
| BTCUSD_otc | 5 | 0.0% | 0.0% | 40.0% | -40.0% | 16.6960 | -16.6960 ⚠️ |
| DOTUSD_otc | 3 | 0.0% | 0.0% | 33.33% | -33.33% | 9.0000 | -9.0000 ⚠️ |
| #MSFT_otc | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 25.0000 | -25.0000 ⚠️ |
| LTCUSD_otc | 2 | 0.0% | 0.0% | 100.0% | -100.0% | -23.0000 | 23.0000 ⚠️ |
| USDTHB_otc | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 20.0000 | -20.0000 ⚠️ |
| USDBRL_otc | 2 | 0.0% | 0.0% | 0.0% | 0.0% | 20.0000 | -20.0000 ⚠️ |
| AVAX_otc | 73 | 0.0% | 0.0% | 52.11% | -52.11% | 4.8686 | -4.8686 ⚠️ |
| USDCAD_otc | 220 | 0.0% | 0.0% | 48.18% | -48.18% | 1.5389 | -1.5389 ⚠️ |
| SYPUSD_otc | 2 | 0.0% | 0.0% | 50.0% | -50.0% | 0.8000 | -0.8000 ⚠️ |
| KESUSD_otc | 144 | 0.0% | 0.0% | 50.0% | -50.0% | -1.0941 | 1.0941 ⚠️ |
| AEDCNY_otc | 262 | 0.0% | 0.0% | 48.28% | -48.28% | 3.7524 | -3.7524 ⚠️ |
| BNB-USD_otc | 48 | 0.0% | 0.0% | 44.68% | -44.68% | 10.9485 | -10.9485 ⚠️ |
| SARCNY_otc | 11 | 0.0% | 0.0% | 54.55% | -54.55% | 5.4182 | -5.4182 ⚠️ |
| VISA_otc | 3 | 0.0% | 0.0% | 33.33% | -33.33% | 16.3600 | -16.3600 ⚠️ |
| SOL-USD_otc | 11 | 0.0% | 0.0% | 45.45% | -45.45% | 4.6318 | -4.6318 ⚠️ |
| NGNUSD_otc | 78 | 0.0% | 0.0% | 57.14% | -57.14% | -2.6777 | 2.6777 ⚠️ |
| VIX_otc | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 25.0000 | -25.0000 ⚠️ |
| LBPUSD_otc | 138 | 0.0% | 0.0% | 49.28% | -49.28% | 0.7754 | -0.7754 ⚠️ |
| QARCNY_otc | 26 | 0.0% | 0.0% | 52.0% | -52.0% | 1.5769 | -1.5769 ⚠️ |
| ADA-USD_otc | 144 | 0.0% | 0.0% | 42.86% | -42.86% | 5.8535 | -5.8535 ⚠️ |
| #FB_otc | 1 | 0.0% | 0.0% | 0.0% | 0.0% | 25.0000 | -25.0000 ⚠️ |
| ETHUSD_otc | 3 | 0.0% | 0.0% | 100.0% | -100.0% | -22.3333 | 22.3333 ⚠️ |
| LINK_otc | 2 | 0.0% | 0.0% | 50.0% | -50.0% | 1.0000 | -1.0000 ⚠️ |
| TNDUSD_otc | 11 | 0.0% | 0.0% | 63.64% | -63.64% | -12.0500 | 12.0500 ⚠️ |
| MATIC_otc | 8 | 0.0% | 0.0% | 50.0% | -50.0% | 0.8000 | -0.8000 ⚠️ |
| USDCNH_otc | 2 | 0.0% | 0.0% | 50.0% | -50.0% | 0.8000 | -0.8000 ⚠️ |
| ZARUSD_otc | 180 | 0.0% | 0.0% | 55.0% | -55.0% | -3.2725 | 3.2725 ⚠️ |
| DOGE_otc | 63 | 0.0% | 0.0% | 38.71% | -38.71% | 6.3008 | -6.3008 ⚠️ |

_⚠️ denotes small sample sizes (< 10 trades) in one or both splits._

### Strategy Level Vulnerability

| Strategy Level | Total Trades | Manip Trades | Manip WR | Non-Manip WR | WR Delta |
| --- | --- | --- | --- | --- | --- |
| LEVEL1 | 564 | 0 | 0.0% | 48.3% | -48.3% |
| LEVEL2 | 6171 | 3 | 100.0% | 50.13% | 49.87% |
| LEVEL3 | 3264 | 629 | 52.4% | 50.71% | 1.69% |

### Weakest UTC Hourly Windows Under Manipulation

| Hour (UTC) | Total Trades | Manip Trades | Manip WR | Non-Manip WR | Degradation |
| --- | --- | --- | --- | --- | --- |
| 19:00 | 726 | 2 | 0.0% | 50.71% | 50.71% |
| 17:00 | 448 | 11 | 36.36% | 47.43% | 11.07% |
| 11:00 | 523 | 18 | 38.89% | 48.67% | 9.78% |
| 13:00 | 531 | 7 | 42.86% | 49.71% | 6.85% |
| 10:00 | 423 | 30 | 43.33% | 49.74% | 6.41% |
| 07:00 | 209 | 35 | 51.43% | 55.49% | 4.06% |
| 14:00 | 661 | 21 | 47.62% | 50.76% | 3.14% |
| 20:00 | 327 | 11 | 50.0% | 52.15% | 2.15% |
| 06:00 | 524 | 54 | 50.0% | 51.72% | 1.72% |
| 00:00 | 456 | 62 | 50.0% | 51.53% | 1.53% |

---

## Phase 3 — L1/L2/L3 Optimization Matrices

### Strategy Level Comparison

| Level | Trades | Wins | Losses | Win Rate | Net Profit | Expectancy |
| --- | --- | --- | --- | --- | --- | --- |
| LEVEL1 | 564 | 270 | 289 | 48.3% | $119.52 | 0.2119 |
| LEVEL2 | 6171 | 2994 | 2976 | 50.15% | $-14424.20 | -2.3374 |
| LEVEL3 | 3264 | 1644 | 1577 | 51.04% | $-1741.70 | -0.5336 |

### OTEO Score-Band Performance

| Score Band | Trades | Wins | Win Rate | Net Profit | Expectancy | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| 50-64 | 9 | 6 | 66.67% | $147.00 | 16.3333 | Low ⚠️ |
| 65-74 | 291 | 139 | 48.1% | $-642.65 | -2.2084 | OK |
| 75-84 | 3657 | 1803 | 50.52% | $-5005.95 | -1.3689 | OK |
| 85-92 | 3123 | 1524 | 50.2% | $-4626.76 | -1.4815 | OK |
| 93+ | 2919 | 1436 | 50.44% | $-5918.01 | -2.0274 | OK |

### UTC Hour-of-Day Performance

| Hour (UTC) | Trades | Wins | Win Rate | Net Profit | Expectancy |
| --- | --- | --- | --- | --- | --- |
| 00:00 | 456 | 233 | 51.32% | $-617.10 | -1.3533 |
| 01:00 | 347 | 166 | 48.54% | $-324.28 | -0.9345 |
| 02:00 | 264 | 132 | 50.57% | $-414.55 | -1.5703 |
| 03:00 | 60 | 32 | 55.17% | $136.60 | 2.2767 |
| 04:00 | 39 | 21 | 53.85% | $7.65 | 0.1962 |
| 05:00 | 244 | 127 | 52.26% | $193.85 | 0.7945 |
| 06:00 | 524 | 268 | 51.54% | $-350.00 | -0.6679 |
| 07:00 | 209 | 114 | 54.81% | $-10.30 | -0.0493 |
| 08:00 | 328 | 164 | 50.77% | $-402.50 | -1.2271 |
| 09:00 | 607 | 308 | 51.08% | $-691.30 | -1.1389 |
| 10:00 | 423 | 203 | 49.27% | $-1355.35 | -3.2041 |
| 11:00 | 523 | 244 | 48.32% | $-1233.65 | -2.3588 |
| 12:00 | 478 | 229 | 49.04% | $-93.08 | -0.1947 |
| 13:00 | 531 | 259 | 49.62% | $-718.00 | -1.3522 |
| 14:00 | 661 | 312 | 50.65% | $177.99 | 0.2693 |
| 15:00 | 514 | 248 | 50.1% | $-1119.05 | -2.1771 |
| 16:00 | 527 | 248 | 48.25% | $-1097.11 | -2.0818 |
| 17:00 | 448 | 207 | 47.15% | $-1685.75 | -3.7628 |
| 18:00 | 347 | 159 | 47.6% | $-1651.35 | -4.7589 |
| 19:00 | 726 | 355 | 50.57% | $-1292.95 | -1.7809 |
| 20:00 | 327 | 163 | 52.08% | $-222.90 | -0.6817 |
| 21:00 | 305 | 157 | 53.4% | $627.90 | 2.0587 |
| 22:00 | 547 | 272 | 50.94% | $-2518.65 | -4.6045 |
| 23:00 | 564 | 287 | 51.99% | $-1392.49 | -2.4690 |

### UTC Day-of-Week Performance

| Weekday | Trades | Wins | Win Rate | Net Profit | Expectancy |
| --- | --- | --- | --- | --- | --- |
| Mon | 1939 | 975 | 50.75% | $-1898.05 | -0.9789 |
| Tue | 1310 | 666 | 51.71% | $-461.14 | -0.3520 |
| Wed | 1288 | 597 | 46.75% | $-4986.80 | -3.8717 |
| Thu | 1207 | 591 | 49.58% | $-2292.90 | -1.8997 |
| Fri | 1810 | 869 | 49.97% | $-2145.73 | -1.1855 |
| Sat | 1669 | 846 | 52.45% | $-3689.45 | -2.2106 |
| Sun | 776 | 364 | 50.56% | $-572.30 | -0.7375 |

### Best Assets (≥5 trades, by Expectancy)

| Rank | Asset | Trades | Win Rate | Expectancy |
| --- | --- | --- | --- | --- |
| 1 | TNDUSD_otc | 11 | 63.64% | 12.0500 |
| 2 | OMRCNY_otc | 12 | 75.0% | 11.4833 |
| 3 | NZDJPY_otc | 16 | 62.5% | 4.0625 |
| 4 | EURRUB_otc | 22 | 63.64% | 3.8614 |
| 5 | ZARUSD_otc | 180 | 55.0% | 3.2725 |

### Worst Assets (≥5 trades, by Expectancy)

| Rank | Asset | Trades | Win Rate | Expectancy |
| --- | --- | --- | --- | --- |
| 1 | IRRUSD_otc | 10 | 30.0% | -22.4800 |
| 2 | BTCUSD_otc | 5 | 40.0% | -16.6960 |
| 3 | #AAPL_otc | 32 | 37.5% | -16.1013 |
| 4 | CHFNOK_otc | 7 | 14.29% | -15.9714 |
| 5 | BNB-USD_otc | 48 | 44.68% | -10.9485 |

### Regime × Score-Band Cross-Tab

**Regime: RANGE_BOUND**

| Score Band | Trades | Win Rate | Expectancy |
| --- | --- | --- | --- |
| 65-74 | 1 | 100.0% | 18.4000 |
| 75-84 | 81 | 47.5% | -1.4580 |
| 85-92 | 141 | 50.0% | -2.1975 |
| 93+ | 263 | 52.49% | 0.0173 |

**Regime: STRONG_MOMENTUM**

| Score Band | Trades | Win Rate | Expectancy |
| --- | --- | --- | --- |
| 50-64 | 3 | 66.67% | 5.6000 |
| 65-74 | 206 | 51.94% | 1.2748 |
| 75-84 | 361 | 51.83% | -1.0201 |
| 85-92 | 329 | 46.08% | -1.1763 |
| 93+ | 1 | 0.0% | -20.0000 |

**Regime: TREND_PULLBACK**

| Score Band | Trades | Win Rate | Expectancy |
| --- | --- | --- | --- |
| 75-84 | 80 | 52.5% | 0.1850 |
| 85-92 | 158 | 54.19% | 1.4475 |
| 93+ | 164 | 43.29% | -1.6354 |

**Regime: TREND_REVERSAL**

| Score Band | Trades | Win Rate | Expectancy |
| --- | --- | --- | --- |
| 50-64 | 1 | 100.0% | 18.4000 |
| 65-74 | 2 | 50.0% | -0.8000 |
| 75-84 | 48 | 55.32% | -0.5208 |
| 85-92 | 99 | 36.08% | -6.5556 |
| 93+ | 149 | 54.73% | 2.3513 |

**Regime: —**

| Score Band | Trades | Win Rate | Expectancy |
| --- | --- | --- | --- |
| 50-64 | 5 | 60.0% | 22.3600 |
| 65-74 | 82 | 37.5% | -11.2445 |
| 75-84 | 3087 | 50.32% | -1.4608 |
| 85-92 | 2396 | 51.1% | -1.4648 |
| 93+ | 2342 | 50.46% | -2.5554 |

---

## Unjoined Trades (Missing Signals)

| Trade ID | Session ID | Asset | Direction | Entry Time (UTC) | Price |
| --- | --- | --- | --- | --- | --- |
| 868730bf-6f30-4602-8dd1-ded6b77f2623 | auto_ghost_1775487956 | EURRUB_otc | CALL | 2026-04-06 15:21:06 UTC | 85.31758 |
| b017baa8-d4af-47fd-a2d9-561e4a71f071 | auto_ghost_1775540011 | EURGBP_otc | CALL | 2026-04-07 05:48:44 UTC | 0.89898 |
| 961caea2-2c39-48f3-93f8-ab89682c22ae | auto_ghost_1775576405 | CADCHF_otc | PUT | 2026-04-07 16:54:18 UTC | 0.64161 |
| 99d237a2-c58f-4035-a681-87aa709238a5 | auto_ghost_1775762908 | CADCHF_otc | CALL | 2026-04-09 19:35:09 UTC | 0.63095 |
| 8b0ac1cb-4b3c-4bda-b15d-9af79480d8ac | auto_ghost_1775762908 | EURRUB_otc | PUT | 2026-04-09 19:35:09 UTC | 85.40774 |
| 9f2d50c7-ea76-40d9-9791-8a08b94d4cd1 | auto_ghost_1775762908 | BTCUSD_otc | PUT | 2026-04-09 19:35:09 UTC | 67175.268 |
| af31af19-1bd1-4a76-a274-57128f4752e7 | auto_ghost_1775762908 | CADJPY_otc | PUT | 2026-04-09 19:35:09 UTC | 112.963 |
| d8e86371-2c5e-4e72-bfde-3e195eac54e4 | auto_ghost_1775781782 | EURUSD_otc | PUT | 2026-04-10 00:52:20 UTC | 1.16142 |
| 96148e62-3d98-46c7-a234-0b55cffb2db0 | auto_ghost_1775829967 | AEDCNY_otc | PUT | 2026-04-10 14:33:56 UTC | 1.82787 |
| f9e98780-7dc1-448c-817b-119332713857 | auto_ghost_1775834714 | EURGBP_otc | PUT | 2026-04-10 15:30:10 UTC | 0.89437 |
| 4a0f51fd-f208-4c1d-8136-b2800467d8dc | auto_ghost_1775863774 | AEDCNY_otc | CALL | 2026-04-10 23:30:53 UTC | 1.85294 |
| 5a161499-0918-4171-8084-25a3414bcb67 | auto_ghost_1775896747 | EURGBP_otc | CALL | 2026-04-11 09:03:08 UTC | 0.89632 |
| cb832494-2575-4085-829d-af14f2e112ac | auto_ghost_1775927152 | AUDNZD_otc | CALL | 2026-04-11 17:19:33 UTC | 1.1604 |
| e8b40b24-bd5f-4273-bf89-c8a4a04f61d7 | auto_ghost_1775947156 | AUDNZD_otc | PUT | 2026-04-11 22:40:58 UTC | 1.16542 |
| f93a4f53-1f6c-4f91-bbe1-42dde47765a5 | auto_ghost_1776711614 | EURUSD_otc | CALL | 2026-04-20 21:04:38 UTC | 1.16055 |
| 697cde30-0e3f-427a-94cc-96f8d7171083 | auto_ghost_1778048619 | ZARUSD_otc | CALL | 2026-05-06 09:10:41 UTC | 0.054796 |
| b47cc7e8-954b-43e6-b67c-422091932bae | auto_ghost_1775477241 | CADCHF_otc | PUT | 2026-04-06 14:24:30 UTC | 0.62841 |
| c08b8a31-bcf8-4c72-8ffe-da792e11e8a9 | auto_ghost_1775496615 | #AXP_otc | CALL | 2026-04-06 18:43:06 UTC | 172.348 |
| 2d93a9bf-5d69-4e4e-983d-7908ad37005f | auto_ghost_1775496615 | GBPUSD_otc | PUT | 2026-04-06 18:48:08 UTC | 1.32162 |

---

## Ambiguous Join Audits

| Trade ID | Asset | Direction | Entry Time (UTC) | Details |
| --- | --- | --- | --- | --- |
| 1b659253-e4c0-4759-8651-c39eaa45753c | EURUSD_otc | CALL | 2026-04-05 07:44:10 UTC | Multiple exact entry_context timestamp matches found for trade '1b659253-e4c0-4759-8651-c39eaa45753c' at timestamp 1775382250.611 |
| 88791f86-b997-454e-89f0-d2c7537aee0b | AUDNZD_otc | CALL | 2026-04-05 07:44:11 UTC | Multiple exact entry_context timestamp matches found for trade '88791f86-b997-454e-89f0-d2c7537aee0b' at timestamp 1775382251.61 |
| 3aa760cf-535a-4174-82c4-c17174c35cac | AUDNZD_otc | CALL | 2026-04-05 07:46:14 UTC | Multiple exact entry_context timestamp matches found for trade '3aa760cf-535a-4174-82c4-c17174c35cac' at timestamp 1775382374.345 |
| 8f75275a-d07b-4802-88ef-07b4ba740ebb | EURJPY_otc | CALL | 2026-04-05 07:46:58 UTC | Multiple exact entry_context timestamp matches found for trade '8f75275a-d07b-4802-88ef-07b4ba740ebb' at timestamp 1775382418.505 |
| 3d2595bd-582d-45a5-b350-ad3edc5ed207 | AUDNZD_otc | CALL | 2026-04-05 07:48:26 UTC | Multiple exact entry_context timestamp matches found for trade '3d2595bd-582d-45a5-b350-ad3edc5ed207' at timestamp 1775382506.201 |
| d06518a2-7bc5-41ff-873c-3a21106446ee | EURJPY_otc | PUT | 2026-04-05 07:49:04 UTC | Multiple exact entry_context timestamp matches found for trade 'd06518a2-7bc5-41ff-873c-3a21106446ee' at timestamp 1775382543.746 |
| 0075c1c4-840a-4d04-8458-a6ee5ca8fef0 | AUDNZD_otc | CALL | 2026-04-05 07:50:44 UTC | Multiple exact entry_context timestamp matches found for trade '0075c1c4-840a-4d04-8458-a6ee5ca8fef0' at timestamp 1775382644.366 |
| 7ffbb48f-8932-44c4-8c07-9252dbdd6e1d | EURJPY_otc | PUT | 2026-04-05 07:51:50 UTC | Multiple exact entry_context timestamp matches found for trade '7ffbb48f-8932-44c4-8c07-9252dbdd6e1d' at timestamp 1775382710.432 |
| c2d10b06-8c4e-41f1-b5ff-9d72e0115f45 | EURUSD_otc | PUT | 2026-04-05 07:52:50 UTC | Multiple exact entry_context timestamp matches found for trade 'c2d10b06-8c4e-41f1-b5ff-9d72e0115f45' at timestamp 1775382770.587 |
| b21dac43-7bda-42c8-8732-bbe2cf290535 | AUDCAD_otc | PUT | 2026-04-05 07:54:15 UTC | Multiple exact entry_context timestamp matches found for trade 'b21dac43-7bda-42c8-8732-bbe2cf290535' at timestamp 1775382855.725 |
| 370e1ae5-541b-4305-a352-2d5d071b043e | EURUSD_otc | PUT | 2026-04-05 07:54:22 UTC | Multiple exact entry_context timestamp matches found for trade '370e1ae5-541b-4305-a352-2d5d071b043e' at timestamp 1775382861.729 |
| f6e679b1-51f0-42e1-9e51-3a5ce28ce480 | AUDNZD_otc | PUT | 2026-04-05 07:57:20 UTC | Multiple exact entry_context timestamp matches found for trade 'f6e679b1-51f0-42e1-9e51-3a5ce28ce480' at timestamp 1775383039.896 |
| e12e18d1-ab53-4ec6-8513-a27c2efcfbf3 | EURJPY_otc | CALL | 2026-04-05 07:58:28 UTC | Multiple exact entry_context timestamp matches found for trade 'e12e18d1-ab53-4ec6-8513-a27c2efcfbf3' at timestamp 1775383108.01 |
| 34279f7c-e685-482a-ad9e-fd15ea45ad1e | AUDNZD_otc | PUT | 2026-04-05 07:58:50 UTC | Multiple exact entry_context timestamp matches found for trade '34279f7c-e685-482a-ad9e-fd15ea45ad1e' at timestamp 1775383130.542 |
| 5c7e5b37-8600-47bc-a773-80eede240a92 | EURUSD_otc | PUT | 2026-04-05 07:59:19 UTC | Multiple exact entry_context timestamp matches found for trade '5c7e5b37-8600-47bc-a773-80eede240a92' at timestamp 1775383159.551 |
| 1844e3a1-ab05-4ddf-ba06-4326198c08bb | EURUSD_otc | CALL | 2026-04-05 08:02:58 UTC | Multiple exact entry_context timestamp matches found for trade '1844e3a1-ab05-4ddf-ba06-4326198c08bb' at timestamp 1775383378.416 |
| 7dc7ad54-69af-4c39-910e-1dde351eac5e | EURUSD_otc | PUT | 2026-04-05 08:04:48 UTC | Multiple exact entry_context timestamp matches found for trade '7dc7ad54-69af-4c39-910e-1dde351eac5e' at timestamp 1775383487.609 |
| dc489ddd-8e3a-4bdd-bf38-7e18740590fc | EURJPY_otc | CALL | 2026-04-05 08:06:13 UTC | Multiple exact entry_context timestamp matches found for trade 'dc489ddd-8e3a-4bdd-bf38-7e18740590fc' at timestamp 1775383572.878 |
| aa0e45e8-c3de-4364-a743-f333b0e7c209 | AUDCAD_otc | PUT | 2026-04-06 15:08:04 UTC | Multiple exact entry_context timestamp matches found for trade 'aa0e45e8-c3de-4364-a743-f333b0e7c209' at timestamp 1775495284.141 |
| f047b0e6-abb5-4aa5-8375-df0a10af0c8d | AUDCAD_otc | PUT | 2026-04-06 15:10:33 UTC | Multiple exact entry_context timestamp matches found for trade 'f047b0e6-abb5-4aa5-8375-df0a10af0c8d' at timestamp 1775495432.649 |
| d05638a4-1bc0-481c-a042-f7f68901370e | AUDCAD_otc | CALL | 2026-04-06 15:12:11 UTC | Multiple exact entry_context timestamp matches found for trade 'd05638a4-1bc0-481c-a042-f7f68901370e' at timestamp 1775495531.407 |
| 7891460b-5219-4312-b550-e2659d782fd7 | EURJPY_otc | CALL | 2026-04-06 15:12:36 UTC | Multiple exact entry_context timestamp matches found for trade '7891460b-5219-4312-b550-e2659d782fd7' at timestamp 1775495555.502 |
| 8cabee39-0390-4e8d-b348-5fee88c3f1c2 | AUDCAD_otc | PUT | 2026-04-06 15:15:52 UTC | Multiple exact entry_context timestamp matches found for trade '8cabee39-0390-4e8d-b348-5fee88c3f1c2' at timestamp 1775495752.327 |
| 13bce985-41f5-496d-bed5-ff6d87fa622f | USDJPY_otc | CALL | 2026-04-06 15:16:54 UTC | Multiple exact entry_context timestamp matches found for trade '13bce985-41f5-496d-bed5-ff6d87fa622f' at timestamp 1775495812.984 |
| 81c9048a-492e-437a-b278-f37ae4cef5c0 | CADCHF_otc | PUT | 2026-04-06 15:22:05 UTC | Multiple exact entry_context timestamp matches found for trade '81c9048a-492e-437a-b278-f37ae4cef5c0' at timestamp 1775496124.019 |
| 6a482de2-0335-42cb-ad02-ab4faa81e97b | AUDCAD_otc | CALL | 2026-04-10 00:43:07 UTC | Multiple exact entry_context timestamp matches found for trade '6a482de2-0335-42cb-ad02-ab4faa81e97b' at timestamp 1775788987.559 |
| 4e593dee-c8fb-4295-8d5d-111c0ae313fe | AUDCAD_otc | CALL | 2026-04-10 00:43:07 UTC | Multiple exact entry_context timestamp matches found for trade '4e593dee-c8fb-4295-8d5d-111c0ae313fe' at timestamp 1775788987.559 |
| 92160bda-3403-42ba-a296-91c4b3658720 | AUDCAD_otc | CALL | 2026-04-10 00:51:17 UTC | Multiple exact entry_context timestamp matches found for trade '92160bda-3403-42ba-a296-91c4b3658720' at timestamp 1775789477.779 |
| f9680e37-aa8c-426a-bd9f-0eb238f1fd00 | AUDCAD_otc | CALL | 2026-04-10 00:51:17 UTC | Multiple exact entry_context timestamp matches found for trade 'f9680e37-aa8c-426a-bd9f-0eb238f1fd00' at timestamp 1775789477.779 |
| 19497c00-ccd1-4273-b744-03fec358e378 | AUDCAD_otc | CALL | 2026-04-10 00:52:57 UTC | Multiple exact entry_context timestamp matches found for trade '19497c00-ccd1-4273-b744-03fec358e378' at timestamp 1775789576.938 |
| fb4ef39c-f9a3-4fbc-bd39-9e39d9bbcbbf | AUDCAD_otc | CALL | 2026-04-10 00:52:57 UTC | Multiple exact entry_context timestamp matches found for trade 'fb4ef39c-f9a3-4fbc-bd39-9e39d9bbcbbf' at timestamp 1775789576.938 |
| 88676fa4-a6be-44d0-9e51-32c1b93c9485 | EURUSD_otc | CALL | 2026-04-10 00:54:08 UTC | Multiple exact entry_context timestamp matches found for trade '88676fa4-a6be-44d0-9e51-32c1b93c9485' at timestamp 1775789648.581 |
| 89f3c786-ab20-4562-ae01-a363b8cc5861 | EURUSD_otc | CALL | 2026-04-10 00:54:09 UTC | Multiple exact entry_context timestamp matches found for trade '89f3c786-ab20-4562-ae01-a363b8cc5861' at timestamp 1775789648.581 |
| 8b0b3c01-86d5-4510-917f-1bda9d03754d | CADCHF_otc | PUT | 2026-04-10 00:54:37 UTC | Multiple exact entry_context timestamp matches found for trade '8b0b3c01-86d5-4510-917f-1bda9d03754d' at timestamp 1775789677.621 |
| 04ca1fc3-e43f-42a2-b71d-dd0024b1db53 | EURUSD_otc | PUT | 2026-04-10 00:56:00 UTC | Multiple exact entry_context timestamp matches found for trade '04ca1fc3-e43f-42a2-b71d-dd0024b1db53' at timestamp 1775789760.215 |
| 7aac7254-f697-43d8-bf18-b0b4b186a83a | AUDCAD_otc | CALL | 2026-04-10 00:56:57 UTC | Multiple exact entry_context timestamp matches found for trade '7aac7254-f697-43d8-bf18-b0b4b186a83a' at timestamp 1775789816.882 |
| b8036fc6-8639-4258-abe3-faa3a5b3d6b8 | AUDCAD_otc | CALL | 2026-04-10 00:56:57 UTC | Multiple exact entry_context timestamp matches found for trade 'b8036fc6-8639-4258-abe3-faa3a5b3d6b8' at timestamp 1775789816.882 |
| 210df887-65e4-419d-8aea-3667048cfac4 | EURUSD_otc | PUT | 2026-04-10 00:58:02 UTC | Multiple exact entry_context timestamp matches found for trade '210df887-65e4-419d-8aea-3667048cfac4' at timestamp 1775789881.964 |
| 8bab1036-9c4a-4b84-98fa-50de55ce2faf | AUDCAD_otc | CALL | 2026-04-10 01:08:01 UTC | Multiple exact entry_context timestamp matches found for trade '8bab1036-9c4a-4b84-98fa-50de55ce2faf' at timestamp 1775790481.107 |
| 31186a7a-7d07-4065-aea6-4bad9cd90e14 | AUDUSD_otc | PUT | 2026-04-13 09:51:03 UTC | Multiple exact entry_context timestamp matches found for trade '31186a7a-7d07-4065-aea6-4bad9cd90e14' at timestamp 1776081063.643 |
| cb2c82a4-21fb-449a-a559-c4f98750bfdc | EURCHF_otc | CALL | 2026-04-15 06:12:35 UTC | Multiple exact entry_context timestamp matches found for trade 'cb2c82a4-21fb-449a-a559-c4f98750bfdc' at timestamp 1776240754.826 |
| 2057eaba-4c10-4ab5-ab2e-35641f3c37f6 | EURCHF_otc | CALL | 2026-04-15 07:41:51 UTC | Multiple exact entry_context timestamp matches found for trade '2057eaba-4c10-4ab5-ab2e-35641f3c37f6' at timestamp 1776246110.873 |
| a77b6967-3675-4f24-b897-b530b229e99f | AUDCHF_otc | CALL | 2026-04-15 20:03:54 UTC | Multiple exact entry_context timestamp matches found for trade 'a77b6967-3675-4f24-b897-b530b229e99f' at timestamp 1776290634.965 |
| fb96bd8f-0319-4aff-8277-7334307d4373 | AUDCHF_otc | PUT | 2026-04-15 20:08:39 UTC | Multiple exact entry_context timestamp matches found for trade 'fb96bd8f-0319-4aff-8277-7334307d4373' at timestamp 1776290919.59 |
| fcb8b8e0-f41d-458b-8c0f-b3561901fac5 | GBPUSD_otc | PUT | 2026-04-15 21:23:31 UTC | Multiple exact entry_context timestamp matches found for trade 'fcb8b8e0-f41d-458b-8c0f-b3561901fac5' at timestamp 1776295411.584 |
| f737377f-7908-46ce-b4ba-0d8b3df303bb | EURUSD_otc | CALL | 2026-04-15 23:09:00 UTC | Multiple exact entry_context timestamp matches found for trade 'f737377f-7908-46ce-b4ba-0d8b3df303bb' at timestamp 1776301740.093 |
| 0a558460-4c7b-41e2-abad-b356b199ceb2 | EURUSD_otc | PUT | 2026-04-15 23:21:24 UTC | Multiple exact entry_context timestamp matches found for trade '0a558460-4c7b-41e2-abad-b356b199ceb2' at timestamp 1776302484.74 |
| bc1c272c-9b16-4d24-9097-532cb3afb26f | EURUSD_otc | PUT | 2026-04-15 23:27:45 UTC | Multiple exact entry_context timestamp matches found for trade 'bc1c272c-9b16-4d24-9097-532cb3afb26f' at timestamp 1776302865.073 |
| 623f4fb3-f71d-454c-976a-a16a6f7c6f15 | EURJPY_otc | CALL | 2026-05-04 11:34:18 UTC | Multiple exact entry_context timestamp matches found for trade '623f4fb3-f71d-454c-976a-a16a6f7c6f15' at timestamp 1777894458.895 |
| 2cf0a0c0-134b-4c62-a618-7c483c7c2553 | EURJPY_otc | CALL | 2026-05-04 11:56:54 UTC | Multiple exact entry_context timestamp matches found for trade '2cf0a0c0-134b-4c62-a618-7c483c7c2553' at timestamp 1777895814.325 |
| 5a647bc9-512f-4879-937e-44405ac1a340 | EURJPY_otc | CALL | 2026-05-04 11:58:36 UTC | Multiple exact entry_context timestamp matches found for trade '5a647bc9-512f-4879-937e-44405ac1a340' at timestamp 1777895916.042 |
| 126296b8-9b79-4a5b-8d5c-a2da814a1c2d | CHFJPY_otc | CALL | 2026-05-04 19:33:01 UTC | Multiple exact entry_context timestamp matches found for trade '126296b8-9b79-4a5b-8d5c-a2da814a1c2d' at timestamp 1777923181.28 |
| c44d5ad8-6000-4dac-84b2-49cc85d432b3 | CHFJPY_otc | CALL | 2026-05-04 19:42:22 UTC | Multiple exact entry_context timestamp matches found for trade 'c44d5ad8-6000-4dac-84b2-49cc85d432b3' at timestamp 1777923742.053 |
| 66f81abb-d7c7-4c98-b0f2-a8bf69822497 | CHFJPY_otc | CALL | 2026-05-04 19:44:19 UTC | Multiple exact entry_context timestamp matches found for trade '66f81abb-d7c7-4c98-b0f2-a8bf69822497' at timestamp 1777923859.04 |
| a0ff891e-bd41-44e1-9ff1-58b4b4ea7f19 | AUDCAD_otc | PUT | 2026-05-04 19:50:01 UTC | Multiple exact entry_context timestamp matches found for trade 'a0ff891e-bd41-44e1-9ff1-58b4b4ea7f19' at timestamp 1777924201.073 |
| 93946f3d-3d3e-470b-8903-1be02acf6240 | CHFJPY_otc | CALL | 2026-05-04 20:36:23 UTC | Multiple exact entry_context timestamp matches found for trade '93946f3d-3d3e-470b-8903-1be02acf6240' at timestamp 1777926983.268 |
| 50698b50-90f6-4cff-aec3-75b0935fe504 | CHFJPY_otc | PUT | 2026-05-04 21:03:00 UTC | Multiple exact entry_context timestamp matches found for trade '50698b50-90f6-4cff-aec3-75b0935fe504' at timestamp 1777928580.455 |
| 57386475-ee3c-4da2-94b6-6021535eb35a | AUDCAD_otc | CALL | 2026-05-04 21:09:02 UTC | Multiple exact entry_context timestamp matches found for trade '57386475-ee3c-4da2-94b6-6021535eb35a' at timestamp 1777928942.384 |
| 754076f6-57bb-4aba-a38e-08f200c3702b | AUDCAD_otc | CALL | 2026-05-04 21:37:36 UTC | Multiple exact entry_context timestamp matches found for trade '754076f6-57bb-4aba-a38e-08f200c3702b' at timestamp 1777930656.214 |
| cacebf23-f4f8-4d28-91dc-14deca4cb0cc | AUDCAD_otc | PUT | 2026-05-04 22:04:31 UTC | Multiple exact entry_context timestamp matches found for trade 'cacebf23-f4f8-4d28-91dc-14deca4cb0cc' at timestamp 1777932271.128 |
| 4324631f-716e-49ce-acec-be4efb4dd868 | EURCHF_otc | PUT | 2026-05-04 22:10:57 UTC | Multiple exact entry_context timestamp matches found for trade '4324631f-716e-49ce-acec-be4efb4dd868' at timestamp 1777932657.057 |
| b0a88819-55f4-48cf-a5b8-7fa4480dbe59 | EURUSD_otc | PUT | 2026-05-04 22:21:03 UTC | Multiple exact entry_context timestamp matches found for trade 'b0a88819-55f4-48cf-a5b8-7fa4480dbe59' at timestamp 1777933263.748 |
| 59f217a0-5f95-4752-83c6-5abbd9e9a6d4 | EURCHF_otc | PUT | 2026-05-04 22:21:05 UTC | Multiple exact entry_context timestamp matches found for trade '59f217a0-5f95-4752-83c6-5abbd9e9a6d4' at timestamp 1777933265.248 |
| fb3f285e-3877-4802-be80-0f07060ec745 | CADJPY_otc | CALL | 2026-05-04 22:21:09 UTC | Multiple exact entry_context timestamp matches found for trade 'fb3f285e-3877-4802-be80-0f07060ec745' at timestamp 1777933269.244 |
| 61482aa0-6a38-45ec-aef6-4fe31290b248 | CADJPY_otc | CALL | 2026-05-04 22:23:31 UTC | Multiple exact entry_context timestamp matches found for trade '61482aa0-6a38-45ec-aef6-4fe31290b248' at timestamp 1777933411.074 |
| 63fd1602-d125-4c1b-831a-ffe294a4b457 | AUDCAD_otc | PUT | 2026-05-04 22:25:06 UTC | Multiple exact entry_context timestamp matches found for trade '63fd1602-d125-4c1b-831a-ffe294a4b457' at timestamp 1777933506.338 |
| b87953b8-93ef-4635-b8d8-c58d4ab5ee39 | EURCHF_otc | PUT | 2026-05-04 22:31:09 UTC | Multiple exact entry_context timestamp matches found for trade 'b87953b8-93ef-4635-b8d8-c58d4ab5ee39' at timestamp 1777933869.636 |
| 55c447a9-970d-4780-9bfd-8a80074b749d | EURUSD_otc | CALL | 2026-05-04 22:31:13 UTC | Multiple exact entry_context timestamp matches found for trade '55c447a9-970d-4780-9bfd-8a80074b749d' at timestamp 1777933873.076 |
| 20b804d7-90f3-49b4-ae35-485db8e46441 | EURUSD_otc | PUT | 2026-05-04 22:43:40 UTC | Multiple exact entry_context timestamp matches found for trade '20b804d7-90f3-49b4-ae35-485db8e46441' at timestamp 1777934620.142 |
| 84d85117-e57a-4a7e-8f5f-21105032d877 | EURCHF_otc | PUT | 2026-05-04 22:43:52 UTC | Multiple exact entry_context timestamp matches found for trade '84d85117-e57a-4a7e-8f5f-21105032d877' at timestamp 1777934632.213 |
| e1440b88-300e-44f8-a98d-5921006f5a00 | EURUSD_otc | PUT | 2026-05-04 22:50:14 UTC | Multiple exact entry_context timestamp matches found for trade 'e1440b88-300e-44f8-a98d-5921006f5a00' at timestamp 1777935014.512 |
| b9c17a49-f653-4ea4-884d-58388cec7109 | CADJPY_otc | CALL | 2026-05-04 23:04:26 UTC | Multiple exact entry_context timestamp matches found for trade 'b9c17a49-f653-4ea4-884d-58388cec7109' at timestamp 1777935866.744 |
| 50a269eb-5ee6-40d1-a2f9-4acf7b73bc81 | CADJPY_otc | PUT | 2026-05-04 23:12:37 UTC | Multiple exact entry_context timestamp matches found for trade '50a269eb-5ee6-40d1-a2f9-4acf7b73bc81' at timestamp 1777936357.323 |
| ba174d2e-9fbf-4a44-bbd5-47fbb5b30442 | CADJPY_otc | CALL | 2026-05-04 23:22:05 UTC | Multiple exact entry_context timestamp matches found for trade 'ba174d2e-9fbf-4a44-bbd5-47fbb5b30442' at timestamp 1777936925.106 |
| 6d1594c6-a95b-4d42-b41d-14f22c2eb121 | EURUSD_otc | CALL | 2026-05-04 23:24:02 UTC | Multiple exact entry_context timestamp matches found for trade '6d1594c6-a95b-4d42-b41d-14f22c2eb121' at timestamp 1777937042.043 |
| d70f304c-ee92-4aff-99f3-b9c315a36115 | CADJPY_otc | PUT | 2026-05-04 23:24:23 UTC | Multiple exact entry_context timestamp matches found for trade 'd70f304c-ee92-4aff-99f3-b9c315a36115' at timestamp 1777937063.573 |
| 503a455c-aef3-4f76-a025-4d8c729f63ab | EURUSD_otc | PUT | 2026-05-04 23:29:02 UTC | Multiple exact entry_context timestamp matches found for trade '503a455c-aef3-4f76-a025-4d8c729f63ab' at timestamp 1777937342.705 |
| 6faba3e9-33a5-41dc-8a1d-90af1a10a872 | EURUSD_otc | PUT | 2026-05-04 23:34:02 UTC | Multiple exact entry_context timestamp matches found for trade '6faba3e9-33a5-41dc-8a1d-90af1a10a872' at timestamp 1777937642.307 |
| 5665a4fd-0416-49c1-82ac-2fc119a6b1ed | AUDCAD_otc | CALL | 2026-05-04 23:35:01 UTC | Multiple exact entry_context timestamp matches found for trade '5665a4fd-0416-49c1-82ac-2fc119a6b1ed' at timestamp 1777937701.929 |
| 03688835-4946-4125-bce0-026ecc896f40 | EURUSD_otc | PUT | 2026-05-04 23:39:11 UTC | Multiple exact entry_context timestamp matches found for trade '03688835-4946-4125-bce0-026ecc896f40' at timestamp 1777937951.069 |
| 3de9667a-fbee-4d4e-abaa-475706876066 | CADJPY_otc | PUT | 2026-05-04 23:43:16 UTC | Multiple exact entry_context timestamp matches found for trade '3de9667a-fbee-4d4e-abaa-475706876066' at timestamp 1777938196.607 |
| 989c8766-148d-4cb8-a37f-2be13c96c2c6 | EURCHF_otc | CALL | 2026-05-04 23:45:29 UTC | Multiple exact entry_context timestamp matches found for trade '989c8766-148d-4cb8-a37f-2be13c96c2c6' at timestamp 1777938329.945 |
| f4789aac-3d1e-41fb-84aa-bf4531f6f303 | EURUSD_otc | CALL | 2026-05-04 23:46:23 UTC | Multiple exact entry_context timestamp matches found for trade 'f4789aac-3d1e-41fb-84aa-bf4531f6f303' at timestamp 1777938383.628 |
| ca518763-654f-48b7-af4c-8237cb95a12f | AUDCAD_otc | PUT | 2026-05-04 23:48:20 UTC | Multiple exact entry_context timestamp matches found for trade 'ca518763-654f-48b7-af4c-8237cb95a12f' at timestamp 1777938500.914 |
| b4aa1133-7560-4eb6-a76d-6d3757b315bc | EURCHF_otc | PUT | 2026-05-04 23:49:02 UTC | Multiple exact entry_context timestamp matches found for trade 'b4aa1133-7560-4eb6-a76d-6d3757b315bc' at timestamp 1777938542.462 |
| ab884965-b94c-43d4-b697-4a3a230ef861 | CADJPY_otc | PUT | 2026-05-04 23:50:00 UTC | Multiple exact entry_context timestamp matches found for trade 'ab884965-b94c-43d4-b697-4a3a230ef861' at timestamp 1777938600.553 |
| 0731731a-5c28-4c4d-98ba-15da6d93107b | EURCHF_otc | CALL | 2026-05-04 23:50:33 UTC | Multiple exact entry_context timestamp matches found for trade '0731731a-5c28-4c4d-98ba-15da6d93107b' at timestamp 1777938633.608 |
| 6415e600-1281-45da-9482-ce03ad0238f5 | EURCHF_otc | PUT | 2026-05-04 23:54:08 UTC | Multiple exact entry_context timestamp matches found for trade '6415e600-1281-45da-9482-ce03ad0238f5' at timestamp 1777938848.944 |
| 716f11dd-2e20-434b-95c6-a971b2a266b6 | EURUSD_otc | CALL | 2026-05-04 23:58:42 UTC | Multiple exact entry_context timestamp matches found for trade '716f11dd-2e20-434b-95c6-a971b2a266b6' at timestamp 1777939122.032 |
| 7c7339a5-0dd1-442a-bdfb-bf7c14968a51 | EURUSD_otc | CALL | 2026-05-05 00:01:02 UTC | Multiple exact entry_context timestamp matches found for trade '7c7339a5-0dd1-442a-bdfb-bf7c14968a51' at timestamp 1777939262.013 |
| f7d41ec6-eee0-47a7-affc-a435a9ff35aa | CADJPY_otc | PUT | 2026-05-05 00:02:03 UTC | Multiple exact entry_context timestamp matches found for trade 'f7d41ec6-eee0-47a7-affc-a435a9ff35aa' at timestamp 1777939323.992 |
| 009da721-8e9f-49f9-ac4f-aee524356f0d | AUDCAD_otc | CALL | 2026-05-05 00:04:46 UTC | Multiple exact entry_context timestamp matches found for trade '009da721-8e9f-49f9-ac4f-aee524356f0d' at timestamp 1777939486.864 |
| a2dca302-7094-43ae-aa83-6ce98705b887 | EURCHF_otc | PUT | 2026-05-05 00:07:19 UTC | Multiple exact entry_context timestamp matches found for trade 'a2dca302-7094-43ae-aa83-6ce98705b887' at timestamp 1777939639.681 |
| 7d43b265-70ba-4d71-90e4-c568b1951e16 | EURUSD_otc | PUT | 2026-05-05 00:08:26 UTC | Multiple exact entry_context timestamp matches found for trade '7d43b265-70ba-4d71-90e4-c568b1951e16' at timestamp 1777939706.047 |
| 5af60919-b7c3-4845-9dd3-90e43a154ba8 | CADCHF_otc | PUT | 2026-05-06 15:04:03 UTC | Multiple exact entry_context timestamp matches found for trade '5af60919-b7c3-4845-9dd3-90e43a154ba8' at timestamp 1778079843.12 |
| 073eb2d3-a623-479c-b180-5fd778d95f82 | CADCHF_otc | CALL | 2026-05-06 15:22:54 UTC | Multiple exact entry_context timestamp matches found for trade '073eb2d3-a623-479c-b180-5fd778d95f82' at timestamp 1778080974.782 |
| 8be34b46-12b4-4778-a97a-8358833a9089 | CADCHF_otc | PUT | 2026-05-06 15:36:34 UTC | Multiple exact entry_context timestamp matches found for trade '8be34b46-12b4-4778-a97a-8358833a9089' at timestamp 1778081794.316 |
| 113ae363-433d-46b8-b0b1-74d9a92cee3b | CADCHF_otc | CALL | 2026-05-06 17:33:18 UTC | Multiple exact entry_context timestamp matches found for trade '113ae363-433d-46b8-b0b1-74d9a92cee3b' at timestamp 1778088798.725 |
| 6083f374-bc4a-40bc-8f2f-8cfb94ea0a88 | CADCHF_otc | CALL | 2026-05-06 17:46:20 UTC | Multiple exact entry_context timestamp matches found for trade '6083f374-bc4a-40bc-8f2f-8cfb94ea0a88' at timestamp 1778089580.932 |
| 63c9a771-9909-4c7c-9b7b-f0d0741b7469 | CADCHF_otc | PUT | 2026-05-06 18:00:16 UTC | Multiple exact entry_context timestamp matches found for trade '63c9a771-9909-4c7c-9b7b-f0d0741b7469' at timestamp 1778090416.136 |
| 00a29d91-d8e5-4b8d-bae5-49fc442024e0 | AUDCAD_otc | CALL | 2026-05-08 16:19:36 UTC | Multiple exact entry_context timestamp matches found for trade '00a29d91-d8e5-4b8d-bae5-49fc442024e0' at timestamp 1778257176.999 |
| 44ab45c6-f384-480a-8e89-73d93f741380 | EURUSD_otc | PUT | 2026-05-08 16:20:00 UTC | Multiple exact entry_context timestamp matches found for trade '44ab45c6-f384-480a-8e89-73d93f741380' at timestamp 1778257200.596 |
| 11e05a8b-79c4-4055-98a5-a2e016a4a791 | EURUSD_otc | PUT | 2026-05-08 16:22:00 UTC | Multiple exact entry_context timestamp matches found for trade '11e05a8b-79c4-4055-98a5-a2e016a4a791' at timestamp 1778257320.919 |
| 4b7f10c2-afb8-43c1-bbcd-d9017378a5ca | AUDCAD_otc | CALL | 2026-05-08 16:25:36 UTC | Multiple exact entry_context timestamp matches found for trade '4b7f10c2-afb8-43c1-bbcd-d9017378a5ca' at timestamp 1778257536.838 |
| bb8ee13e-45b5-45f4-a671-d72d6fe6f909 | CHFJPY_otc | PUT | 2026-05-08 16:26:53 UTC | Multiple exact entry_context timestamp matches found for trade 'bb8ee13e-45b5-45f4-a671-d72d6fe6f909' at timestamp 1778257613.652 |
| b5d341e8-84e4-4553-b618-d2a2cdb9336c | EURUSD_otc | CALL | 2026-05-08 16:28:37 UTC | Multiple exact entry_context timestamp matches found for trade 'b5d341e8-84e4-4553-b618-d2a2cdb9336c' at timestamp 1778257717.857 |
| dedd2743-2f07-4f7c-be51-57dc2b5bd35c | EURUSD_otc | CALL | 2026-05-08 16:31:22 UTC | Multiple exact entry_context timestamp matches found for trade 'dedd2743-2f07-4f7c-be51-57dc2b5bd35c' at timestamp 1778257882.215 |
| 9f1c54bc-6f8e-46a8-8480-d18da6c5f4de | EURUSD_otc | CALL | 2026-05-08 16:34:01 UTC | Multiple exact entry_context timestamp matches found for trade '9f1c54bc-6f8e-46a8-8480-d18da6c5f4de' at timestamp 1778258041.432 |
| 92b66196-89ad-4911-9b5a-35899f4eae0a | AUDCAD_otc | PUT | 2026-05-08 16:35:06 UTC | Multiple exact entry_context timestamp matches found for trade '92b66196-89ad-4911-9b5a-35899f4eae0a' at timestamp 1778258106.59 |
| 6b2a15c3-0be0-43ee-9e62-c3763c43ad78 | EURUSD_otc | PUT | 2026-05-08 16:38:07 UTC | Multiple exact entry_context timestamp matches found for trade '6b2a15c3-0be0-43ee-9e62-c3763c43ad78' at timestamp 1778258287.382 |
| 61f4ae53-aded-439c-8126-69f0b9c02d81 | EURUSD_otc | PUT | 2026-05-08 17:06:48 UTC | Multiple exact entry_context timestamp matches found for trade '61f4ae53-aded-439c-8126-69f0b9c02d81' at timestamp 1778260008.788 |
| b4cea60b-5b7a-4971-984a-fbfbeefc9ea6 | CHFJPY_otc | CALL | 2026-05-08 17:07:00 UTC | Multiple exact entry_context timestamp matches found for trade 'b4cea60b-5b7a-4971-984a-fbfbeefc9ea6' at timestamp 1778260020.795 |
| 4eeab4be-2ac3-4ad2-b8e1-5466edb6574b | EURUSD_otc | PUT | 2026-05-08 17:13:05 UTC | Multiple exact entry_context timestamp matches found for trade '4eeab4be-2ac3-4ad2-b8e1-5466edb6574b' at timestamp 1778260385.243 |
| c7a91950-4e32-412f-9dc0-66cb0566bf09 | CHFJPY_otc | CALL | 2026-05-08 17:13:08 UTC | Multiple exact entry_context timestamp matches found for trade 'c7a91950-4e32-412f-9dc0-66cb0566bf09' at timestamp 1778260388.245 |
| 67d641d7-a177-4534-99ad-02c228158bbe | EURUSD_otc | CALL | 2026-05-08 17:19:47 UTC | Multiple exact entry_context timestamp matches found for trade '67d641d7-a177-4534-99ad-02c228158bbe' at timestamp 1778260787.279 |
| e9dc2fca-8dc0-4fa2-9e88-31ae7dc9b9d9 | AUDCAD_otc | PUT | 2026-05-08 17:26:04 UTC | Multiple exact entry_context timestamp matches found for trade 'e9dc2fca-8dc0-4fa2-9e88-31ae7dc9b9d9' at timestamp 1778261164.008 |
| 536203b6-eb2f-4b01-a15e-90ba839f9d22 | EURUSD_otc | PUT | 2026-05-08 17:26:41 UTC | Multiple exact entry_context timestamp matches found for trade '536203b6-eb2f-4b01-a15e-90ba839f9d22' at timestamp 1778261201.586 |
| bb820ed9-2c7e-405e-94c3-c4d185a849a1 | EURUSD_otc | PUT | 2026-05-08 17:32:51 UTC | Multiple exact entry_context timestamp matches found for trade 'bb820ed9-2c7e-405e-94c3-c4d185a849a1' at timestamp 1778261571.911 |
| 5d71fd91-d484-446b-8fc4-f4c7781aa1d7 | CADCHF_otc | PUT | 2026-05-08 18:02:17 UTC | Multiple exact entry_context timestamp matches found for trade '5d71fd91-d484-446b-8fc4-f4c7781aa1d7' at timestamp 1778263337.377 |
| 40fd5e17-4ec4-4409-9b18-28ec86f80cbd | AUDCAD_otc | PUT | 2026-05-08 18:08:29 UTC | Multiple exact entry_context timestamp matches found for trade '40fd5e17-4ec4-4409-9b18-28ec86f80cbd' at timestamp 1778263709.548 |
| 482d5ef3-1132-4842-a562-c94018396481 | CHFJPY_otc | PUT | 2026-05-08 18:23:03 UTC | Multiple exact entry_context timestamp matches found for trade '482d5ef3-1132-4842-a562-c94018396481' at timestamp 1778264583.59 |
| fd9ea3d1-1d24-41c5-8c2a-8f8c51d824aa | EURUSD_otc | PUT | 2026-05-11 12:35:48 UTC | Multiple exact entry_context timestamp matches found for trade 'fd9ea3d1-1d24-41c5-8c2a-8f8c51d824aa' at timestamp 1778502948.127 |
| 9b5f352f-beea-4070-9ac5-e725a979a422 | EURUSD_otc | CALL | 2026-05-11 13:43:10 UTC | Multiple exact entry_context timestamp matches found for trade '9b5f352f-beea-4070-9ac5-e725a979a422' at timestamp 1778506990.025 |
| 3773e6ec-47df-44bd-9c61-100517fd5629 | EURUSD_otc | PUT | 2026-05-11 13:50:49 UTC | Multiple exact entry_context timestamp matches found for trade '3773e6ec-47df-44bd-9c61-100517fd5629' at timestamp 1778507449.106 |
| 93f58a30-5bad-47ca-92ad-167404bde5cc | EURUSD_otc | CALL | 2026-05-11 13:55:31 UTC | Multiple exact entry_context timestamp matches found for trade '93f58a30-5bad-47ca-92ad-167404bde5cc' at timestamp 1778507731.238 |
| 96869c36-c754-47e8-aff6-6a872e550014 | EURUSD_otc | CALL | 2026-05-11 14:02:19 UTC | Multiple exact entry_context timestamp matches found for trade '96869c36-c754-47e8-aff6-6a872e550014' at timestamp 1778508139.099 |
| 31f00e86-0963-46d7-99a3-3059738342e2 | EURUSD_otc | PUT | 2026-05-11 14:08:07 UTC | Multiple exact entry_context timestamp matches found for trade '31f00e86-0963-46d7-99a3-3059738342e2' at timestamp 1778508487.668 |
| 290fd534-e9d8-4f56-9be4-0dd46db01047 | EURUSD_otc | CALL | 2026-05-11 14:10:43 UTC | Multiple exact entry_context timestamp matches found for trade '290fd534-e9d8-4f56-9be4-0dd46db01047' at timestamp 1778508643.946 |
| 1a327583-8ca8-44e3-9f06-0ce558fcf115 | EURUSD_otc | CALL | 2026-05-11 14:12:42 UTC | Multiple exact entry_context timestamp matches found for trade '1a327583-8ca8-44e3-9f06-0ce558fcf115' at timestamp 1778508762.286 |
| 9f84cc32-e1d2-4584-a030-a2a65fec9bdd | EURUSD_otc | CALL | 2026-05-11 14:15:35 UTC | Multiple exact entry_context timestamp matches found for trade '9f84cc32-e1d2-4584-a030-a2a65fec9bdd' at timestamp 1778508935.102 |
| 42a511a9-46b0-40a7-b462-83a6df00b592 | NZDUSD_otc | PUT | 2026-05-11 23:34:02 UTC | Multiple exact entry_context timestamp matches found for trade '42a511a9-46b0-40a7-b462-83a6df00b592' at timestamp 1778542442.702 |
| 2ce44f25-5e61-4e95-a687-2918beab264a | NZDUSD_otc | PUT | 2026-05-12 00:22:51 UTC | Multiple exact entry_context timestamp matches found for trade '2ce44f25-5e61-4e95-a687-2918beab264a' at timestamp 1778545371.572 |
| 602f22fd-0893-40cf-8d09-b01c3fda32c2 | NZDUSD_otc | CALL | 2026-05-12 00:36:00 UTC | Multiple exact entry_context timestamp matches found for trade '602f22fd-0893-40cf-8d09-b01c3fda32c2' at timestamp 1778546160.719 |
| 12e0317a-4938-47e8-8d2e-a9462adbb1a6 | NZDUSD_otc | CALL | 2026-05-12 00:49:40 UTC | Multiple exact entry_context timestamp matches found for trade '12e0317a-4938-47e8-8d2e-a9462adbb1a6' at timestamp 1778546980.838 |
| 03bd521a-134e-4158-9a4b-140222753b53 | NZDUSD_otc | CALL | 2026-05-12 01:41:44 UTC | Multiple exact entry_context timestamp matches found for trade '03bd521a-134e-4158-9a4b-140222753b53' at timestamp 1778550104.577 |
| e8108747-3775-4ef7-9358-2abba609c692 | AUDCAD_otc | PUT | 2026-05-12 18:40:40 UTC | Multiple exact entry_context timestamp matches found for trade 'e8108747-3775-4ef7-9358-2abba609c692' at timestamp 1778611240.991 |
| d53268b2-d58a-4df6-9c8a-07918eee7622 | EURUSD_otc | PUT | 2026-05-12 18:55:27 UTC | Multiple exact entry_context timestamp matches found for trade 'd53268b2-d58a-4df6-9c8a-07918eee7622' at timestamp 1778612127.84 |
| 504fc8ec-3b17-496e-b335-ea15ffbd6150 | AEDCNY_otc | CALL | 2026-05-12 18:57:07 UTC | Multiple exact entry_context timestamp matches found for trade '504fc8ec-3b17-496e-b335-ea15ffbd6150' at timestamp 1778612227.609 |
| e1b3e7ee-6206-4dc3-9dfa-da48322408c6 | EURUSD_otc | PUT | 2026-05-12 18:57:16 UTC | Multiple exact entry_context timestamp matches found for trade 'e1b3e7ee-6206-4dc3-9dfa-da48322408c6' at timestamp 1778612236.627 |
| 2548a37e-7dfa-4e74-b701-585bc56edd7f | AEDCNY_otc | PUT | 2026-05-12 19:02:24 UTC | Multiple exact entry_context timestamp matches found for trade '2548a37e-7dfa-4e74-b701-585bc56edd7f' at timestamp 1778612544.057 |
| 7b88ea5c-9e9e-4c80-922c-60e860547a2e | GBPAUD_otc | CALL | 2026-05-12 19:06:43 UTC | Multiple exact entry_context timestamp matches found for trade '7b88ea5c-9e9e-4c80-922c-60e860547a2e' at timestamp 1778612803.098 |
| a4989480-9701-4c99-af90-0cfc2413fcae | AEDCNY_otc | PUT | 2026-05-12 19:07:40 UTC | Multiple exact entry_context timestamp matches found for trade 'a4989480-9701-4c99-af90-0cfc2413fcae' at timestamp 1778612860.188 |
| ec678b02-44f4-42fa-9b09-1386ac14342f | AUDCAD_otc | CALL | 2026-05-12 19:08:48 UTC | Multiple exact entry_context timestamp matches found for trade 'ec678b02-44f4-42fa-9b09-1386ac14342f' at timestamp 1778612928.815 |
| 9657fa25-cb37-48e6-a836-fb65f40a09ac | GBPAUD_otc | CALL | 2026-05-12 19:19:06 UTC | Multiple exact entry_context timestamp matches found for trade '9657fa25-cb37-48e6-a836-fb65f40a09ac' at timestamp 1778613546.323 |
| 46e26861-797d-46ae-bd1a-e8c187c600f0 | EURUSD_otc | PUT | 2026-05-12 19:21:12 UTC | Multiple exact entry_context timestamp matches found for trade '46e26861-797d-46ae-bd1a-e8c187c600f0' at timestamp 1778613672.218 |
| ccdcc990-465c-43c0-b26d-8fe651b8246e | GBPAUD_otc | CALL | 2026-05-12 19:21:54 UTC | Multiple exact entry_context timestamp matches found for trade 'ccdcc990-465c-43c0-b26d-8fe651b8246e' at timestamp 1778613714.44 |
| 80a3566c-6b3a-4b02-b756-b14b8607a8c1 | AUDCAD_otc | CALL | 2026-05-12 19:26:33 UTC | Multiple exact entry_context timestamp matches found for trade '80a3566c-6b3a-4b02-b756-b14b8607a8c1' at timestamp 1778613993.556 |
| d8682b47-e5bb-47e8-a919-6f442b54d327 | CADJPY_otc | CALL | 2026-05-12 19:26:56 UTC | Multiple exact entry_context timestamp matches found for trade 'd8682b47-e5bb-47e8-a919-6f442b54d327' at timestamp 1778614016.114 |
| e88950a5-a6d1-4097-9a5e-cd513f30bebd | EURJPY_otc | CALL | 2026-05-12 19:28:49 UTC | Multiple exact entry_context timestamp matches found for trade 'e88950a5-a6d1-4097-9a5e-cd513f30bebd' at timestamp 1778614129.427 |
| d3a56bae-acff-4862-85f0-69eca17a0e21 | CADCHF_otc | PUT | 2026-06-05 22:36:26 UTC | Multiple exact entry_context timestamp matches found for trade 'd3a56bae-acff-4862-85f0-69eca17a0e21' at timestamp 1780698986.662 |
| f557970e-d2eb-41ca-b6d0-303dbc9451ea | EURUSD_otc | PUT | 2026-06-05 22:38:08 UTC | Multiple exact entry_context timestamp matches found for trade 'f557970e-d2eb-41ca-b6d0-303dbc9451ea' at timestamp 1780699088.342 |
| 3b0f74bc-aa26-4da7-b6e0-ad39e89754a3 | EURUSD_otc | PUT | 2026-06-05 22:49:50 UTC | Multiple exact entry_context timestamp matches found for trade '3b0f74bc-aa26-4da7-b6e0-ad39e89754a3' at timestamp 1780699790.175 |
| 061a8918-c1e8-429a-a25b-12701378df2a | CADCHF_otc | PUT | 2026-06-05 22:59:18 UTC | Multiple exact entry_context timestamp matches found for trade '061a8918-c1e8-429a-a25b-12701378df2a' at timestamp 1780700358.256 |
| b5281f88-ad1c-4987-881f-e7cef793ee85 | EURUSD_otc | PUT | 2026-06-05 23:02:00 UTC | Multiple exact entry_context timestamp matches found for trade 'b5281f88-ad1c-4987-881f-e7cef793ee85' at timestamp 1780700520.214 |
| b5a61b56-3310-4624-b717-8e615ab0d672 | EURUSD_otc | PUT | 2026-06-05 23:04:33 UTC | Multiple exact entry_context timestamp matches found for trade 'b5a61b56-3310-4624-b717-8e615ab0d672' at timestamp 1780700673.982 |
| 528648d1-cf42-4a21-9793-00db6f2632af | EURUSD_otc | CALL | 2026-06-05 23:07:27 UTC | Multiple exact entry_context timestamp matches found for trade '528648d1-cf42-4a21-9793-00db6f2632af' at timestamp 1780700847.756 |
| 0acff0b2-d20e-41ad-8e45-3e9f7d50387f | GBPUSD_otc | CALL | 2026-06-08 09:16:06 UTC | Multiple exact entry_context timestamp matches found for trade '0acff0b2-d20e-41ad-8e45-3e9f7d50387f' at timestamp 1780910166.431 |
| 8d3b8321-873f-4f22-97d1-ad9772db96c2 | EURUSD_otc | CALL | 2026-06-08 09:18:00 UTC | Multiple exact entry_context timestamp matches found for trade '8d3b8321-873f-4f22-97d1-ad9772db96c2' at timestamp 1780910280.182 |
| c7aeb19b-90df-4a0c-b7f8-07a6d925495a | AUDCHF_otc | CALL | 2026-06-08 09:21:12 UTC | Multiple exact entry_context timestamp matches found for trade 'c7aeb19b-90df-4a0c-b7f8-07a6d925495a' at timestamp 1780910472.489 |
| 1567d6e3-5d47-43f4-a3a6-9ef66239d866 | GBPUSD_otc | PUT | 2026-06-08 09:23:20 UTC | Multiple exact entry_context timestamp matches found for trade '1567d6e3-5d47-43f4-a3a6-9ef66239d866' at timestamp 1780910600.219 |
| 36d1ea03-70cd-4d4e-984d-75d136989dec | AUDCHF_otc | PUT | 2026-06-08 09:28:05 UTC | Multiple exact entry_context timestamp matches found for trade '36d1ea03-70cd-4d4e-984d-75d136989dec' at timestamp 1780910885.078 |
| 274922cd-e7a5-401a-af28-2a0f76319dc1 | AUDCHF_otc | CALL | 2026-06-08 09:36:01 UTC | Multiple exact entry_context timestamp matches found for trade '274922cd-e7a5-401a-af28-2a0f76319dc1' at timestamp 1780911361.659 |
| 963468b4-64dd-4901-99dd-69384cf54743 | CADCHF_otc | CALL | 2026-06-08 09:41:02 UTC | Multiple exact entry_context timestamp matches found for trade '963468b4-64dd-4901-99dd-69384cf54743' at timestamp 1780911662.606 |
| 34113e4d-4ff7-4593-a82c-b2e77e395d33 | CADCHF_otc | CALL | 2026-06-08 09:50:22 UTC | Multiple exact entry_context timestamp matches found for trade '34113e4d-4ff7-4593-a82c-b2e77e395d33' at timestamp 1780912222.213 |
| fe670069-60b1-4d59-8398-754aaf153ea2 | AUDNZD_otc | CALL | 2026-06-12 09:29:35 UTC | Multiple exact entry_context timestamp matches found for trade 'fe670069-60b1-4d59-8398-754aaf153ea2' at timestamp 1781256575.067 |
| c9140689-ffd4-4f67-b191-8ede8014012a | EURRUB_otc | PUT | 2026-06-12 10:21:00 UTC | Multiple exact entry_context timestamp matches found for trade 'c9140689-ffd4-4f67-b191-8ede8014012a' at timestamp 1781259660.838 |
| 13e558f3-e493-4cff-840c-be902455bfe4 | EURUSD_otc | CALL | 2026-06-12 11:00:16 UTC | Multiple exact entry_context timestamp matches found for trade '13e558f3-e493-4cff-840c-be902455bfe4' at timestamp 1781262016.285 |
| 8c5bb35b-0b1e-4bc8-940f-05d503b2bf82 | EURUSD_otc | CALL | 2026-06-12 11:05:01 UTC | Multiple exact entry_context timestamp matches found for trade '8c5bb35b-0b1e-4bc8-940f-05d503b2bf82' at timestamp 1781262301.711 |
| cdce2cce-22e5-409c-bf5b-ff624f8ea3e0 | EURUSD_otc | CALL | 2026-06-12 11:07:00 UTC | Multiple exact entry_context timestamp matches found for trade 'cdce2cce-22e5-409c-bf5b-ff624f8ea3e0' at timestamp 1781262420.883 |
| 01ca6d12-c212-48dd-8e8e-ceed8dd59e2b | EURUSD_otc | CALL | 2026-06-12 11:09:05 UTC | Multiple exact entry_context timestamp matches found for trade '01ca6d12-c212-48dd-8e8e-ceed8dd59e2b' at timestamp 1781262545.404 |
| 46d8c683-6e35-4384-9b4f-f06e3422bad7 | EURUSD_otc | CALL | 2026-06-12 11:15:13 UTC | Multiple exact entry_context timestamp matches found for trade '46d8c683-6e35-4384-9b4f-f06e3422bad7' at timestamp 1781262913.116 |
| d80d127f-be75-48e3-bb22-c90318a60a6f | EURUSD_otc | PUT | 2026-06-12 11:39:52 UTC | Multiple exact entry_context timestamp matches found for trade 'd80d127f-be75-48e3-bb22-c90318a60a6f' at timestamp 1781264392.666 |
| f308730b-ba0e-456e-8613-aebd01bfdda6 | EURUSD_otc | CALL | 2026-06-12 11:49:18 UTC | Multiple exact entry_context timestamp matches found for trade 'f308730b-ba0e-456e-8613-aebd01bfdda6' at timestamp 1781264958.7 |
| c3e84bbe-5e5f-4b32-9c6b-b6fbcfc33e75 | EURUSD_otc | CALL | 2026-06-12 11:59:52 UTC | Multiple exact entry_context timestamp matches found for trade 'c3e84bbe-5e5f-4b32-9c6b-b6fbcfc33e75' at timestamp 1781265592.892 |
| 4e8461f5-3a91-4ecb-a4b8-dbf013c160c6 | EURUSD_otc | PUT | 2026-06-12 12:05:59 UTC | Multiple exact entry_context timestamp matches found for trade '4e8461f5-3a91-4ecb-a4b8-dbf013c160c6' at timestamp 1781265959.203 |
| a3dcb315-abd0-46c7-8c23-3a4fad33fa47 | EURUSD_otc | CALL | 2026-06-12 12:12:09 UTC | Multiple exact entry_context timestamp matches found for trade 'a3dcb315-abd0-46c7-8c23-3a4fad33fa47' at timestamp 1781266329.192 |
| 5200374e-8a93-46b1-b1f9-5c49355709fd | EURUSD_otc | PUT | 2026-06-12 12:18:20 UTC | Multiple exact entry_context timestamp matches found for trade '5200374e-8a93-46b1-b1f9-5c49355709fd' at timestamp 1781266700.051 |
| 0a3e1873-8b1a-4c15-920c-d461f97ad63d | EURUSD_otc | PUT | 2026-06-12 12:25:00 UTC | Multiple exact entry_context timestamp matches found for trade '0a3e1873-8b1a-4c15-920c-d461f97ad63d' at timestamp 1781267100.009 |
| 231ebdf0-2268-417d-8b03-785aa39b0c3e | EURUSD_otc | CALL | 2026-06-12 12:27:00 UTC | Multiple exact entry_context timestamp matches found for trade '231ebdf0-2268-417d-8b03-785aa39b0c3e' at timestamp 1781267220.574 |
| 686a0f58-32ae-49b6-8c7c-f42c5ace4d2f | AUDUSD_otc | CALL | 2026-06-13 02:39:44 UTC | Multiple exact entry_context timestamp matches found for trade '686a0f58-32ae-49b6-8c7c-f42c5ace4d2f' at timestamp 1781318384.319 |
| eafbe6a5-bdd5-4ec7-8bd3-d7445ec901bd | EURJPY_otc | CALL | 2026-06-13 02:47:31 UTC | Multiple exact entry_context timestamp matches found for trade 'eafbe6a5-bdd5-4ec7-8bd3-d7445ec901bd' at timestamp 1781318851.705 |
| c6838a47-ff55-4d42-aa0b-ac452353a6ad | EURNZD_otc | CALL | 2026-06-13 02:48:06 UTC | Multiple exact entry_context timestamp matches found for trade 'c6838a47-ff55-4d42-aa0b-ac452353a6ad' at timestamp 1781318886.121 |
| b598ae91-9666-4a98-b9f3-4a2aba09b36a | EURNZD_otc | CALL | 2026-06-13 02:50:03 UTC | Multiple exact entry_context timestamp matches found for trade 'b598ae91-9666-4a98-b9f3-4a2aba09b36a' at timestamp 1781319003.929 |
| c1c2a2ef-5b32-45c0-a5c5-9e7c37b9fcc8 | GBPUSD_otc | CALL | 2026-06-13 02:51:00 UTC | Multiple exact entry_context timestamp matches found for trade 'c1c2a2ef-5b32-45c0-a5c5-9e7c37b9fcc8' at timestamp 1781319060.498 |
| c0301d67-2234-47a3-be5c-a6f4de36db55 | GBPUSD_otc | CALL | 2026-06-13 02:53:00 UTC | Multiple exact entry_context timestamp matches found for trade 'c0301d67-2234-47a3-be5c-a6f4de36db55' at timestamp 1781319180.483 |
| 5cf484c5-dd95-4cdc-af2e-4bb59d12e199 | GBPJPY_otc | CALL | 2026-06-13 02:53:21 UTC | Multiple exact entry_context timestamp matches found for trade '5cf484c5-dd95-4cdc-af2e-4bb59d12e199' at timestamp 1781319201.092 |
| d6c5233f-29f9-46f2-853f-2beea979e8a8 | EURJPY_otc | PUT | 2026-06-13 02:54:33 UTC | Multiple exact entry_context timestamp matches found for trade 'd6c5233f-29f9-46f2-853f-2beea979e8a8' at timestamp 1781319273.735 |
| 99a9b06a-2919-4a8f-8241-2926719fd6c2 | GBPJPY_otc | CALL | 2026-06-13 02:55:56 UTC | Multiple exact entry_context timestamp matches found for trade '99a9b06a-2919-4a8f-8241-2926719fd6c2' at timestamp 1781319356.085 |
| 4c7f0650-9e81-4581-86be-86a3356f194a | GBPUSD_otc | CALL | 2026-06-13 02:56:42 UTC | Multiple exact entry_context timestamp matches found for trade '4c7f0650-9e81-4581-86be-86a3356f194a' at timestamp 1781319402.606 |

---

## Missing Tick Log Files

| Trade ID | Asset | UTC Date | Expected File Path |
| --- | --- | --- | --- |
| 43fb1aea-acc6-4b5a-a4af-7ac601103ae2 | BNB-USD_otc | 2026-04-10 | `app\data\tick_logs\BNB-USD_otc\2026-04-10.jsonl` |
| 648a7b07-3f4a-41fe-b1cb-f9184dc6c733 | BHDCNY_otc | 2026-04-10 | `app\data\tick_logs\BHDCNY_otc\2026-04-10.jsonl` |
| 249e6d82-d796-4142-8211-647b8fc507a5 | EURTRY_otc | 2026-04-15 | `app\data\tick_logs\EURTRY_otc\2026-04-15.jsonl` |
| e40029e8-4863-4062-a6d1-226b443e3d4c | EURTRY_otc | 2026-04-15 | `app\data\tick_logs\EURTRY_otc\2026-04-15.jsonl` |
| 44754c53-2e14-46ac-bde4-e225aa94116a | CADCHF_otc | 2026-04-17 | `app\data\tick_logs\CADCHF_otc\2026-04-17.jsonl` |
| fd3dc00c-0dd2-449e-b130-2c0dd720f2d2 | CADCHF_otc | 2026-04-17 | `app\data\tick_logs\CADCHF_otc\2026-04-17.jsonl` |
| ee8c3a2d-b051-4e8d-8fc0-241f843086d3 | CADCHF_otc | 2026-04-17 | `app\data\tick_logs\CADCHF_otc\2026-04-17.jsonl` |
| 12d2fc21-e668-49ef-88e4-cba843a653c8 | CADCHF_otc | 2026-04-17 | `app\data\tick_logs\CADCHF_otc\2026-04-17.jsonl` |
| 82e8bc23-a314-4863-b921-bfa49df01ff1 | CHFJPY_otc | 2026-04-17 | `app\data\tick_logs\CHFJPY_otc\2026-04-17.jsonl` |
| f3c5090a-7074-4bed-83b0-6dde4aa1c952 | CADCHF_otc | 2026-04-17 | `app\data\tick_logs\CADCHF_otc\2026-04-17.jsonl` |
| bde323ff-8db9-44c0-81b6-117c89e3d480 | CADCHF_otc | 2026-04-17 | `app\data\tick_logs\CADCHF_otc\2026-04-17.jsonl` |
| 29871d7d-7385-467c-89f8-9207482d34b6 | CADCHF_otc | 2026-04-17 | `app\data\tick_logs\CADCHF_otc\2026-04-17.jsonl` |
| c40b2425-a80b-4a2e-9a6e-a12783338edb | AUDNZD_otc | 2026-04-18 | `app\data\tick_logs\AUDNZD_otc\2026-04-18.jsonl` |
| 146de39a-7000-4e91-b45e-49c282189dbf | AUDNZD_otc | 2026-04-18 | `app\data\tick_logs\AUDNZD_otc\2026-04-18.jsonl` |
| 34dc60ba-2a91-40b2-802f-a9ea10db297a | EURJPY_otc | 2026-04-18 | `app\data\tick_logs\EURJPY_otc\2026-04-18.jsonl` |
| 5a4fe0b8-efc8-4bf2-ad75-f4f3537c468d | AUDNZD_otc | 2026-04-18 | `app\data\tick_logs\AUDNZD_otc\2026-04-18.jsonl` |
| afa0a275-61e0-4582-b7d4-c444e28e9de2 | EURJPY_otc | 2026-04-18 | `app\data\tick_logs\EURJPY_otc\2026-04-18.jsonl` |
| 5fd01b36-d320-4567-8d3e-f1f0b6bd402a | DOGE_otc | 2026-06-06 | `app\data\tick_logs\DOGE_otc\2026-06-06.jsonl` |
| c4bd4f7d-12b8-42a5-a0c6-9a53345a4e07 | ADA-USD_otc | 2026-06-06 | `app\data\tick_logs\ADA-USD_otc\2026-06-06.jsonl` |
| edaae50b-40b0-4076-844f-9b0c364ef5f8 | DOGE_otc | 2026-06-06 | `app\data\tick_logs\DOGE_otc\2026-06-06.jsonl` |
| 64151cc9-d3a4-4c11-9609-19fa40916380 | ADA-USD_otc | 2026-06-06 | `app\data\tick_logs\ADA-USD_otc\2026-06-06.jsonl` |
| c4f9b397-ea22-4dfd-bd0f-17480e8ccd0d | DOGE_otc | 2026-06-06 | `app\data\tick_logs\DOGE_otc\2026-06-06.jsonl` |
| c3ffd7b3-3d5d-42e3-8f5f-ea958285b21d | DOGE_otc | 2026-06-06 | `app\data\tick_logs\DOGE_otc\2026-06-06.jsonl` |
| d0e478e4-5778-4ee1-9fef-37f7ce2aeb01 | ADA-USD_otc | 2026-06-06 | `app\data\tick_logs\ADA-USD_otc\2026-06-06.jsonl` |
| 98bc99bc-51d1-471d-aa24-709af9f0c7a6 | ADA-USD_otc | 2026-06-06 | `app\data\tick_logs\ADA-USD_otc\2026-06-06.jsonl` |
| bb2bb9a2-a319-4e7e-b61f-62b12d381e9b | DOGE_otc | 2026-06-06 | `app\data\tick_logs\DOGE_otc\2026-06-06.jsonl` |
| 9192e3d6-1e2c-4ff7-bb89-50a95384e7be | USDCAD_otc | 2026-06-10 | `app\data\tick_logs\USDCAD_otc\2026-06-10.jsonl` |

---

## Parsing & Schema Warnings

| File | Line | Details |
| --- | --- | --- |
| auto_ghost_1775935054.jsonl | 22 | auto_ghost_1775935054.jsonl:22 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775935054.jsonl | 27 | auto_ghost_1775935054.jsonl:27 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775935054.jsonl | 35 | auto_ghost_1775935054.jsonl:35 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775935054.jsonl | 40 | auto_ghost_1775935054.jsonl:40 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775935054.jsonl | 45 | auto_ghost_1775935054.jsonl:45 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775935054.jsonl | 48 | auto_ghost_1775935054.jsonl:48 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 1 | auto_ghost_1775947156.jsonl:1 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 5 | auto_ghost_1775947156.jsonl:5 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 6 | auto_ghost_1775947156.jsonl:6 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 7 | auto_ghost_1775947156.jsonl:7 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 10 | auto_ghost_1775947156.jsonl:10 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 12 | auto_ghost_1775947156.jsonl:12 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 16 | auto_ghost_1775947156.jsonl:16 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 19 | auto_ghost_1775947156.jsonl:19 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 22 | auto_ghost_1775947156.jsonl:22 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 23 | auto_ghost_1775947156.jsonl:23 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 28 | auto_ghost_1775947156.jsonl:28 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 32 | auto_ghost_1775947156.jsonl:32 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 34 | auto_ghost_1775947156.jsonl:34 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 37 | auto_ghost_1775947156.jsonl:37 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 40 | auto_ghost_1775947156.jsonl:40 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 43 | auto_ghost_1775947156.jsonl:43 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 45 | auto_ghost_1775947156.jsonl:45 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 46 | auto_ghost_1775947156.jsonl:46 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 52 | auto_ghost_1775947156.jsonl:52 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 54 | auto_ghost_1775947156.jsonl:54 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 56 | auto_ghost_1775947156.jsonl:56 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775947156.jsonl | 58 | auto_ghost_1775947156.jsonl:58 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775971614.jsonl | 1 | auto_ghost_1775971614.jsonl:1 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775971614.jsonl | 4 | auto_ghost_1775971614.jsonl:4 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775971614.jsonl | 6 | auto_ghost_1775971614.jsonl:6 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775971614.jsonl | 9 | auto_ghost_1775971614.jsonl:9 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775971614.jsonl | 11 | auto_ghost_1775971614.jsonl:11 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775971614.jsonl | 14 | auto_ghost_1775971614.jsonl:14 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775971614.jsonl | 17 | auto_ghost_1775971614.jsonl:17 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775971614.jsonl | 19 | auto_ghost_1775971614.jsonl:19 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 1 | auto_ghost_1775973490.jsonl:1 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 4 | auto_ghost_1775973490.jsonl:4 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 8 | auto_ghost_1775973490.jsonl:8 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 10 | auto_ghost_1775973490.jsonl:10 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 11 | auto_ghost_1775973490.jsonl:11 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 14 | auto_ghost_1775973490.jsonl:14 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 16 | auto_ghost_1775973490.jsonl:16 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 18 | auto_ghost_1775973490.jsonl:18 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 20 | auto_ghost_1775973490.jsonl:20 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 24 | auto_ghost_1775973490.jsonl:24 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 26 | auto_ghost_1775973490.jsonl:26 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 29 | auto_ghost_1775973490.jsonl:29 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 34 | auto_ghost_1775973490.jsonl:34 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 41 | auto_ghost_1775973490.jsonl:41 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 43 | auto_ghost_1775973490.jsonl:43 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 45 | auto_ghost_1775973490.jsonl:45 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775973490.jsonl | 50 | auto_ghost_1775973490.jsonl:50 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775975774.jsonl | 2 | auto_ghost_1775975774.jsonl:2 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775975774.jsonl | 6 | auto_ghost_1775975774.jsonl:6 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775975774.jsonl | 12 | auto_ghost_1775975774.jsonl:12 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775975774.jsonl | 15 | auto_ghost_1775975774.jsonl:15 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775975774.jsonl | 19 | auto_ghost_1775975774.jsonl:19 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1775975774.jsonl | 22 | auto_ghost_1775975774.jsonl:22 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776037630.jsonl | 2 | auto_ghost_1776037630.jsonl:2 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776037630.jsonl | 6 | auto_ghost_1776037630.jsonl:6 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776037630.jsonl | 11 | auto_ghost_1776037630.jsonl:11 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776037630.jsonl | 15 | auto_ghost_1776037630.jsonl:15 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776037630.jsonl | 19 | auto_ghost_1776037630.jsonl:19 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776037630.jsonl | 22 | auto_ghost_1776037630.jsonl:22 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776037630.jsonl | 24 | auto_ghost_1776037630.jsonl:24 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776070839.jsonl | 3 | auto_ghost_1776070839.jsonl:3 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776108993.jsonl | 19 | auto_ghost_1776108993.jsonl:19 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776108993.jsonl | 23 | auto_ghost_1776108993.jsonl:23 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776108993.jsonl | 26 | auto_ghost_1776108993.jsonl:26 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776108993.jsonl | 31 | auto_ghost_1776108993.jsonl:31 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776108993.jsonl | 35 | auto_ghost_1776108993.jsonl:35 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776108993.jsonl | 39 | auto_ghost_1776108993.jsonl:39 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776201648.jsonl | 1 | auto_ghost_1776201648.jsonl:1 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776201648.jsonl | 7 | auto_ghost_1776201648.jsonl:7 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776201648.jsonl | 10 | auto_ghost_1776201648.jsonl:10 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776201648.jsonl | 13 | auto_ghost_1776201648.jsonl:13 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776281066.jsonl | 40 | auto_ghost_1776281066.jsonl:40 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776281066.jsonl | 42 | auto_ghost_1776281066.jsonl:42 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776281066.jsonl | 44 | auto_ghost_1776281066.jsonl:44 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776281066.jsonl | 45 | auto_ghost_1776281066.jsonl:45 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776281066.jsonl | 49 | auto_ghost_1776281066.jsonl:49 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776281066.jsonl | 51 | auto_ghost_1776281066.jsonl:51 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776281066.jsonl | 52 | auto_ghost_1776281066.jsonl:52 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776281066.jsonl | 56 | auto_ghost_1776281066.jsonl:56 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776340427.jsonl | 2 | auto_ghost_1776340427.jsonl:2 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776340427.jsonl | 5 | auto_ghost_1776340427.jsonl:5 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776340427.jsonl | 8 | auto_ghost_1776340427.jsonl:8 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776340427.jsonl | 11 | auto_ghost_1776340427.jsonl:11 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776544787.jsonl | 5 | auto_ghost_1776544787.jsonl:5 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776544787.jsonl | 9 | auto_ghost_1776544787.jsonl:9 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776544787.jsonl | 10 | auto_ghost_1776544787.jsonl:10 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776546299.jsonl | 3 | auto_ghost_1776546299.jsonl:3 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776546299.jsonl | 9 | auto_ghost_1776546299.jsonl:9 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776546299.jsonl | 12 | auto_ghost_1776546299.jsonl:12 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776546299.jsonl | 15 | auto_ghost_1776546299.jsonl:15 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776546299.jsonl | 17 | auto_ghost_1776546299.jsonl:17 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776546299.jsonl | 19 | auto_ghost_1776546299.jsonl:19 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776546299.jsonl | 20 | auto_ghost_1776546299.jsonl:20 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |
| auto_ghost_1776546299.jsonl | 21 | auto_ghost_1776546299.jsonl:21 Ghost trade numeric fields ('entry_time'/'entry_price') are malformed |

_...and 1335 more parsing warnings._

