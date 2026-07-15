# Research: Pocket Option Statement "Awareness" Replay Validation
**Date:** 2026-06-28  
**Author:** @Researcher / @Investigator  
**Source File:** [`po_statement_26.01-26.06.xlsx`](file:///c:/v3/OTC_SNIPER/app/data/PO_STATEMENTS/po_statement_26.01-26.06.xlsx)  
**Replay Script:** [`replay_po_statement_validation.py`](file:///c:/v3/OTC_SNIPER/scripts/replay_po_statement_validation.py)  
**Validation Output:** [`po_statement_awareness_validation_summary.json`](file:///c:/v3/OTC_SNIPER/Research/po_statement_awareness_validation_summary.json)

---

## 1. Objective

To validate the statistical edge and capital protection capabilities of the new **"Aware"** trading filters (OTEO Level 3, Hurst exponent vetoes, Kalman pre-filtering, and Regime classification). We replayed the user's historical Pocket Option real trade statement (Jan-June 2026) against high-resolution tick logs to determine how many losing trades would have been prevented (vetoed) and how the overall win rate and net profit change.

---

## 2. Replay Configuration & Matching Heuristics

*   **Timezone Offset:** Detected timezone offset of **+0 hours** (matching Excel timestamps to tick log timestamps).
*   **Total Spreadsheet Trades:** 30,504
*   **Total Matched Trades (with Tick Logs):** 11,720
*   **Total Active Matched Trades (excluding Draws):** 11,592
*   **Veto Logic Parameters:**
    *   Hurst Mean-Reversion Threshold: $H \le 0.44$ (allows trades).
    *   Hurst Momentum/Trend Veto: $H \ge 0.58$ (vetoes trades).
    *   Regime Vetoes: Filters signals against non-optimal regime labels.
    *   Warmup Period: Indicators must have fully initialized (50+ ticks) before evaluation.

---

## 3. Replay Results

The simulation replayed the entire trade history across all matched dates. The empirical findings are detailed below:

### A. Execution Alignment
*   **Unaware Manual Trades:** **11,394 trades (98.29%)**
    *   *Definition:* Trades taken where OTEO did not generate an active, matching signal. The overwhelming majority of the user's manual trades were taken outside the system's structural recommendations.
*   **System Aligned Trades:** **198 trades (1.71%)**
    *   *Definition:* Trades taken in the direction of an active OTEO Level 3 recommendation.

### B. Veto Breakdown (System Aligned Trades Only)
When OTEO generated a signal, the new "Aware" filters applied vetoes:
*   **Approved Wins:** 0 trades
*   **Approved Losses:** 1 trade
*   **Vetoed Wins (False Veto):** 106 trades
*   **Vetoed Losses (True Veto):** 91 trades

#### Veto Reasons Breakdown (197 Vetoes):
1.  **`regime_trending` (126 vetoes):** Vectorized Hurst exponent flagged the market as trending ($H \ge 0.58$ threshold gates).
2.  **`regime_chop` (71 vetoes):** Vectorized Hurst exponent flagged the market as choppy or random walk ($H$ hovering between $0.44$ and $0.58$, default state `"random_walk"`).

### C. Win Rate & Capital Performance

| Metric | Raw System (Before Vetoes) | Adjusted "Aware" System (Approved Only) | Delta |
|---|---|---|---|
| **Win Rate** | 53.54% | **0.00%** | **-53.54%** |
| **Trades Executed** | 198 | 1 | -197 (-99.5%) |

*   **True Veto Rate (Saved Losses):** **98.91%** (Successfully blocked 91 out of 92 losses).
*   **False Veto Rate (Missed Wins):** **100.00%** (Blocked all 106 winning trades).

### D. Estimated Financial Impact
*Normalized to a flat $20.00 trade size at a conservative 90.0% payout:*
*   **Capital Saved (Avoided Losses):** **+$1,820.00** ($20.00 × 91 losses)
*   **Profit Forgone (Missed Wins):** **-$1,908.00** ($20.00 × 0.90 × 106 wins)
*   **Net Financial Benefit:** **-$88.00**

---

## 4. Key Diagnostic Findings

The replay revealed a critical structural behavior in the **Hurst Exponent Regime State Machine**:

1.  **The Warmup Lock Effect:**
    The Hurst filter starts in `"random_walk"` (which is treated as chop and vetoed). To transition into `"mean_reverting"` (allowing trades), the calculated Hurst exponent $H$ must fall below `0.44`.
2.  **Noisy Tick Data:**
    Because the replay script initializes a fresh price buffer for each asset on each date, it only has access to high-frequency tick prices within that single day. Noisy tick-level returns rarely exhibit a clean, persistent mean-reverting profile ($H < 0.44$), keeping the state permanently locked in `"random_walk"` or `"trending"`.
3.  **Conclusion:**
    Under the default configuration, the Hurst veto gate is **hyper-conservative** when run in isolation on single-day files. It effectively mutes the system, protecting the portfolio from drawdowns but also blocking all winning trades.

---

## 5. Proposed Fixes for the Live System

To prevent the Hurst filter from permanently muting the live auto-trader:
*   **Multi-Day Buffer Persistence:** Do not clear the price buffer at the start of each session. Persist the `_price_buffers` and `_regime_states` in a local SQLite file or JSON cache across days to maintain historical context.
*   **Hurst Threshold Calibration:** Increase the mean-reversion threshold from `0.44` to `0.48` for noisier OTC assets, allowing transitions into the `"mean_reverting"` state more easily.
