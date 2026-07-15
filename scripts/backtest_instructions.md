# Backtesting Execution Instructions (PowerShell Terminal)

All backtests must be run within the **QuFLX-v2** Conda environment. Ensure it is activated before running any commands.

```powershell
# Activate the conda environment
conda activate QuFLX-v2
```

---

## 1. OTEO Replay (Base Strategy Levels)
Replays raw tick logs to evaluate base Level 1, 2, and 3 strategy rules (CCI, ADX, Support/Resistance pivots).

*   **Script Location:** `scripts/backtest_oteo_levels.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_oteo_levels.py --mode replay --dates <YYYY-MM-DD> --assets <ASSET_NAME>
    ```
*   **Example (Single Day):**
    ```powershell
    python scripts/backtest_oteo_levels.py --mode replay --dates 2026-06-19 --assets EURUSD_otc
    ```
*   **Example (Multi-Day):**
    ```powershell
    python scripts/backtest_oteo_levels.py --mode replay --dates 2026-06-15 2026-06-16 2026-06-17 2026-06-18 2026-06-19 --assets EURUSD_otc
    ```
*   **Output Directory:** `app/backtesting/results/oteo_levels/<asset_name>_oteo_levels/`

---

## 2. Kalman Filter Pre-Filtering
Evaluates the strategy by pre-filtering tick-level prices through a 1D Kalman Filter state estimator ($Q$ and $R$ variables) prior to indicator engines.

*   **Script Location:** `scripts/backtest_kalman.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_kalman.py --dates <YYYY-MM-DD> --assets <ASSET_NAME> --kalman-q <Q_VALUE> --kalman-r <R_VALUE>
    ```
*   **Example (Optimal Settings):**
    ```powershell
    python scripts/backtest_kalman.py --dates 2026-06-19 --assets EURUSD_otc --kalman-q 1e-9 --kalman-r 1e-7
    ```
*   **Output Directory:** `app/backtesting/results/kalman/<asset_name>_kalman/`

---

## 3. Hurst Exponent Regime Filter
Evaluates performance after applying strict rescaled range (R/S) Hurst exponent veto gates (blocks entries if the market is trending or noisy).

*   **Script Location:** `scripts/backtest_hurst.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_hurst.py --dates <YYYY-MM-DD> --assets <ASSET_NAME> --mean-revert-limit <MR_LIMIT> --trend-limit <TREND_LIMIT>
    ```
*   **Example (Optimal Strict Preset):**
    ```powershell
    python scripts/backtest_hurst.py --dates 2026-06-19 --assets EURUSD_otc --mean-revert-limit 0.44 --trend-limit 0.58
    ```
*   **Output Directory:** `app/backtesting/results/hurst/<asset_name>_hurst/`

---

## 4. Ornstein-Uhlenbeck (OU) Half-Life Calibration
Applies a rolling AR(1) OLS regression over ticks to calculate mean-reversion speeds, calibrate contract durations dynamically, and veto non-reverting trends.

*   **Script Location:** `scripts/backtest_ou_calibration.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_ou_calibration.py --dates <YYYY-MM-DD> --assets <ASSET_NAME>
    ```
*   **Example:**
    ```powershell
    python scripts/backtest_ou_calibration.py --dates 2026-06-19 --assets EURUSD_otc
    ```
*   **Output Directory:** `app/backtesting/results/ou_calibration/<asset_name>_ou_calibration/`

---

## 5. Spike Pockets & Timeframe Analyzer
Evaluates performance across multi-dimensional market pockets (combining Volatility, Liquidity, and Manipulation spike levels) and timezone blocks offsets relative to the 22:00 UTC Platform Rollover.

*   **Script Location:** `scripts/backtest_pockets.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_pockets.py --dates <DATES> --assets <ASSET_NAME>
    ```
*   **Example (Weekly Summary):**
    ```powershell
    python scripts/backtest_pockets.py --dates 2026-06-15 2026-06-16 2026-06-17 2026-06-18 2026-06-19 --assets EURUSD_otc
    ```
*   **Output Directory:** `app/backtesting/results/pockets/<asset_name>_pockets/`

---

## 6. Hybrid Kalman-Hurst Strategy
Evaluates the hybrid strategy by feeding Kalman-smoothed price ticks to the OTEO indicators, while feeding raw price ticks to the Hurst exponent regime classifier, comparing it side-by-side with Baseline, Kalman Only, and Hurst Only strategy configurations.

*   **Script Location:** `scripts/backtest_hybrid_kalman_hurst.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_hybrid_kalman_hurst.py --dates <YYYY-MM-DD> --assets <ASSET_NAME> --kalman-q <Q_VALUE> --kalman-r <R_VALUE> --mean-revert-limit <MR_LIMIT> --trend-limit <TREND_LIMIT>
    ```
*   **Example (Optimal Settings):**
    ```powershell
    python scripts/backtest_hybrid_kalman_hurst.py --dates 2026-06-19 --assets EURUSD_otc --kalman-q 1e-9 --kalman-r 1e-7 --mean-revert-limit 0.44 --trend-limit 0.58
    ```
*   **Output Directory:** `app/backtesting/results/hybrid_kalman_hurst/<asset_name>_hybrid_kalman_hurst/`

---

## 7. Volatility-Adaptive Expiries Sweep
Sweeps the constant $C$ to find the optimal scaling factor mapping continuously computed expiries $C \cdot (1 - H)/V$ to broker-accepted expiration increments (30s, 60s, 120s, 300s).

*   **Script Location:** `scripts/backtest_volatility_adaptive_expiries.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_volatility_adaptive_expiries.py --dates <YYYY-MM-DD> --assets <ASSET_NAME> --c-start <START_VAL> --c-end <END_VAL> --c-step <STEP_VAL>
    ```
*   **Example:**
    ```powershell
    python scripts/backtest_volatility_adaptive_expiries.py --dates 2026-06-19 --assets EURUSD_otc --c-start 10 --c-end 150 --c-step 10
    ```
*   **Output Directory:** `app/backtesting/results/volatility_adaptive/<asset_name>_volatility_adaptive/`

---

## 8. State-Space OU Parameter Tracking (Kalman Filter)
Asynchronously tracks the Ornstein-Uhlenbeck (OU) parameters Speed of Mean Reversion ($\theta$), long-term mean ($\mu$), and optimal half-life duration ($\tau$) recursively tick-by-tick using a 1D Kalman state tracker.

*   **Script Location:** `scripts/backtest_ou_kalman_tracking.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_ou_kalman_tracking.py --dates <YYYY-MM-DD> --assets <ASSET_NAME> --kalman-q-c <Q_C_VAL> --kalman-q-beta <Q_BETA_VAL> --kalman-r <R_VAL>
    ```
*   **Example:**
    ```powershell
    python scripts/backtest_ou_kalman_tracking.py --dates 2026-06-19 --assets EURUSD_otc --kalman-q-c 1e-10 --kalman-q-beta 1e-10 --kalman-r 1e-4
    ```
*   **Output Directory:** `app/backtesting/results/ou_kalman/<asset_name>_ou_kalman/`

---

## 9. Kalman-Hurst Collision Sweep (Test 4)
Analyzes correlation and regime classification differences between raw ticks and Kalman pre-filtered price ticks under 5 Hurst exponent presets to investigate why price smoothing causes 100% signal suppression upstream of Hurst.

*   **Script Location:** `scripts/backtest_kalman_hurst_collision.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_kalman_hurst_collision.py --dates <YYYY-MM-DD> --assets <ASSET_NAME> --kalman-q <Q_VALUE> --kalman-r <R_VALUE> --trend-limit <TREND_LIMIT>
    ```
*   **Example:**
    ```powershell
    python scripts/backtest_kalman_hurst_collision.py --dates 2026-06-19 --assets EURUSD_otc --kalman-q 1e-9 --kalman-r 1e-7 --trend-limit 0.58
    ```
*   **Output Directory:** `app/backtesting/results/kalman_hurst_collision/<asset_name>_collision/`

---

## 10. Kalman-Smoothed Pivot Trading (Test 6)
Benchmarks high-volume trade execution of Level 2/3 structural pivot setups smoothed with a Kalman filter ($Q = 10^{-9}, R = 10^{-7}$) while completely bypassing Hurst vetoes.

*   **Script Location:** `scripts/backtest_kalman_pivot_no_hurst.py`
*   **Command Pattern:**
    ```powershell
    python scripts/backtest_kalman_pivot_no_hurst.py --dates <YYYY-MM-DD> --assets <ASSET_NAME> --kalman-q <Q_VALUE> --kalman-r <R_VALUE> --payout-pct <PAYOUT_PCT>
    ```
*   **Example:**
    ```powershell
    python scripts/backtest_kalman_pivot_no_hurst.py --dates 2026-06-19 --assets EURUSD_otc --kalman-q 1e-9 --kalman-r 1e-7 --payout-pct 92.0
    ```
*   **Output Directory:** `app/backtesting/results/kalman_pivot/<asset_name>_kalman_pivot/`

---

## 11. Bulk Kalman-Smoothed Pivot Trading (Test 6 Bulk Execution)
Runs the Test 6 backtest in parallel across multiple dates (or all available tick log files) and aggregates results into a single consolidated report.

*   **Script Location:** `scripts/run_bulk_kalman_pivot.py`
*   **Command Pattern:**
    ```powershell
    python scripts/run_bulk_kalman_pivot.py --dates <LIST_OF_DATES> --workers <NUM_WORKERS> --kalman-q <Q_VALUE> --kalman-r <R_VALUE>
    ```
*   **Example (Run All Available Data):**
    ```powershell
    python scripts/run_bulk_kalman_pivot.py --all-dates --workers 6
    ```
*   **Example (Run Specific Dates):**
    ```powershell
    python scripts/run_bulk_kalman_pivot.py --dates 2026-06-17 2026-06-18 2026-06-19 --workers 4
    ```
*   **Output Directory:** `app/backtesting/results/kalman_pivot/<asset_name>_kalman_pivot/`
    *   Consolidated MD Report: `bulk_report.md`
    *   Consolidated JSON Summary: `bulk_report_summary.json`

---

## 12. Bulk Volatility-Adaptive Expiries Sweep (Test B Bulk Execution)
Runs the Volatility-Adaptive Expiries Sweep in parallel across multiple dates (or all available tick log files) and aggregates results to identify the global optimal scaling constant $C$.

*   **Script Location:** `scripts/run_bulk_volatility_adaptive.py`
*   **Command Pattern:**
    ```powershell
    python scripts/run_bulk_volatility_adaptive.py --dates <LIST_OF_DATES> --workers <NUM_WORKERS> --c-start <START> --c-end <END> --c-step <STEP>
    ```
*   **Example (Run All Available Data):**
    ```powershell
    python scripts/run_bulk_volatility_adaptive.py --all-dates --workers 6
    ```
*   **Example (Run Specific Dates):**
    ```powershell
    python scripts/run_bulk_volatility_adaptive.py --dates 2026-06-17 2026-06-18 2026-06-19 --workers 4
    ```
*   **Output Directory:** `app/backtesting/results/volatility_adaptive/<asset_name>_volatility_adaptive/`
    *   Consolidated MD Report: `bulk_report.md`
    *   Consolidated JSON Summary: `bulk_report_summary.json`

---

## 13. Bulk Spike Pockets & Timeframe Analyzer (Spike Pockets Bulk Execution)
Runs the Spike Pockets and Timeframe Analyzer in parallel across multiple dates (or all available tick log files) and aggregates results to identify high-probability pockets and timezone block performance.

*   **Script Location:** `scripts/run_bulk_pockets.py`
*   **Command Pattern:**
    ```powershell
    python scripts/run_bulk_pockets.py --dates <LIST_OF_DATES> --workers <NUM_WORKERS> --payout-pct <PAYOUT_PCT>
    ```
*   **Example (Run All Available Data):**
    ```powershell
    python scripts/run_bulk_pockets.py --all-dates --workers 6
    ```
*   **Example (Run Specific Dates):**
    ```powershell
    python scripts/run_bulk_pockets.py --dates 2026-06-17 2026-06-18 2026-06-19 --workers 4
    ```
*   **Output Directory:** `app/backtesting/results/pockets/<asset_name>_pockets/`
    *   Consolidated MD Report: `bulk_report.md`
    *   Consolidated JSON Summary: `bulk_report_summary.json`

---

## 14. Unified Backtesting Framework (Modular Bulk Backtester)
Runs the unified, configuration-driven backtester in parallel across multiple dates and assets. Loads parameter settings directly from a JSON file to enable flexible veto filter configurations and adaptive/static expiries.

*   **Script Location:** `scripts/run_bulk_unified.py`
*   **Command Pattern:**
    ```powershell
    python scripts/run_bulk_unified.py --config-json <PATH_TO_CONFIG> --dates <LIST_OF_DATES> --workers <NUM_WORKERS>
    ```
*   **Example (Baseline Sweep - Run All Dates):**
    ```powershell
    python scripts/run_bulk_unified.py --config-json configs/baseline_config.json --all-dates --workers 6
    ```
*   **Example (Hybrid Optimal Config - Specific Dates):**
    ```powershell
    python scripts/run_bulk_unified.py --config-json configs/hybrid_optimal_config.json --dates 2026-06-17 2026-06-18 2026-06-19 --workers 4
    ```
*   **Output Directory:** `app/backtesting/results/unified/<asset_name>_unified/`
    *   Consolidated MD Report: `unified_bulk_report.md`
    *   Consolidated JSON Summary: `unified_bulk_report_summary.json`
    *   Detailed Trade Log CSV: `trades_raw.csv` (contains full continuous features for ML analysis)

