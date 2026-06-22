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
