# Previous Task Session Summary

## 1. Completed Tasks (2026-06-22)

### 1.1 Kalman Filter Backtester & Analysis
*   **Harness Implementation:** Created and ran [backtest_kalman.py](file:///c:/v3/OTC_SNIPER/scripts/backtest_kalman.py) to pre-filter high-frequency tick prices ($Q = 1e-9, R = 1e-7$) prior to indicator calculations while executing at raw ticks.
*   **Performance Impact:** Backtests on `2026-06-19` EURUSD data showed a **+2.40%** overall win rate improvement (from $52.61\%$ to $55.01\%$) and a **3.5x increase in Net Profit** (+1,967.20 units vs. +564.52 units baseline) by reducing false crossover signals by $37\%$.

### 1.2 Hurst Exponent Calibration & Preset Sweep
*   **Optimization & Veto Audit:** Optimized trade expiry logic in [backtest_hurst.py](file:///c:/v3/OTC_SNIPER/scripts/backtest_hurst.py) to run $100\times$ faster by passing pre-computed timestamps. 
*   **Strict vs. Relaxed Presets Sweep:** Ran a sweep of 5 presets (Hurst MR limits from 0.44 to 0.50). Discovered that relaxing the MR limit above 0.44 instantly crashes the win-rate (collapsing to $6.98\% - 40.0\%$) since entries are forced into random walks ($H \approx 0.50$). Strict threshold of $H \le 0.44$ is required for positive expectancy.
*   **Kalman-Hurst Collision:** Identified that applying a Kalman Filter *before* the Hurst exponent calculation smooths price ticks and skews Hurst to $H > 0.60$ (persistent trend), causing the engines to veto $100\%$ of trades.

### 1.3 Spike Pockets & Timeframe Backtest
*   **State Matrix Classifier:** Created [backtest_pockets.py](file:///c:/v3/OTC_SNIPER/scripts/backtest_pockets.py) to classify ticks into 3D "Spike Pockets" based on Volatility, Liquidity (Quote Frequency), and Manipulation (`push_snap`/`pinning`) levels.
*   **Rollover timeframes:** Backtested 295,295 trades over a 5-day dataset. Discovered that the 18:00 - 22:00 UTC time block offsets (pre-rollover) are highly profitable ($52.23\%$ win rate), whereas 22:00 - 02:00 UTC post-rollover rollover hours lose heavily ($48.54\%$ win rate). Identified `Vol:HIGH | Liq:HIGH | Manip:LOW` as the top pocket ($78.95\%$ win rate).

### 1.4 Unified Backtesting Filing System Reorganization
*   **Structured Outputs:** Modified all 5 backtest scripts to default to [app/backtesting/results](file:///c:/v3/OTC_SNIPER/app/backtesting/results) and write outputs dynamically to nested `{backtest_type}/{asset}_*/` subdirectories.
*   **Clean Up & Migration:** Developed and ran a migration script to clean up old files and place them into the organized folders.
*   **Instructions Guide:** Created [backtest_instructions.md](file:///c:/v3/OTC_SNIPER/scripts/backtest_instructions.md) with exact execution commands.

---

## 2. Recommended Future Tests

### What Else We Can Test (Recommended Next Steps)
Based on our findings, here are the top three tests we recommend running next to build a highly optimized, high-volume automated strategy:

*   **A. The Hybrid Kalman-Hurst Strategy:**
    As we saw in the sweep test, applying the Kalman filter before calculating the Hurst exponent artificially smooths the ticks and vetoes 100% of trades.
    *   *What to test:* Modify the backtester to feed raw price ticks to the Hurst exponent regime classifier, but feed Kalman-smoothed ticks to the OTEO indicators. This gives the strategy the benefits of both worlds: low-noise crossover entries combined with strict Hurst mean-reversion protection.
*   **B. Volatility-Adaptive Expiries Sweep:**
    Instead of static expiries, we can test a dynamic formula where the expiry duration scales continuously based on the current Volatility Score ($V$) and Hurst exponent ($H$): $$\text{Expiry} = C \cdot \frac{1 - H}{V}$$
    *   *What to test:* Sweep the constant $C$ to find the optimal scaling factor that maps to broker-accepted expiration increments (30s, 60s, 120s, 300s).
*   **C. State-Space Ornstein-Uhlenbeck (OU) Parameter Tracking:**
    Currently, the OU half-life calibration script [backtest_ou_calibration.py](file:///c:/v3/OTC_SNIPER/scripts/backtest_ou_calibration.py) uses a rolling 300-tick OLS regression to fit the mean-reversion speed ($\theta$) and the optimal contract half-life ($\tau$).
    *   *What to test:* Implement a recursive state-space Kalman tracker to update the OU parameters tick-by-tick without a sliding window, reducing estimation lag and improving expiry accuracy.

### Additional Suggested Tests

*   **Test 4: Kalman-Hurst Collision Sweep (Raw vs Kalman-Filtered Price Sweeps):**
    Analyze the correlation and regime classification differences between raw ticks and Kalman pre-filtered price ticks ($Q = 10^{-9}$, $R = 10^{-7}$) under the 5 Hurst presets (Highly Relaxed, Low-Med, Med, High-Med, Optimal) to investigate why price smoothing blocks 100% of trades when calculated upstream of Hurst.
*   **Test 5: Hurst Exponent Manual Confirmation Badge UI Gating:**
    Expose the calculated Hurst Exponent as a color-coded indicator badge in the frontend UI (Green for $H < 0.44$, Orange for $0.44 \le H \le 0.52$, Red for $H > 0.52$) rather than a hard silent veto, letting a human trader confirm or override entries based on visually apparent market structure.
*   **Test 6: Kalman-Smoothed Level 2/3 Pivot Trading (No-Hurst Baseline):**
    Benchmark high-volume execution of Level 2/3 structural pivot indicator setups smoothed with a Kalman filter, completely bypassing the Hurst exponent regime vetoes, to maximize trade volume for semi-manual operations while preserving 55%+ win-rates.


