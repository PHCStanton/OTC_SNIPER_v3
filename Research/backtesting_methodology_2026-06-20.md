# Backtesting Methodology: Hurst-Guided Ornstein-Uhlenbeck Adaptive Expiry
**Date: 2026-06-20**  
**Author: @Engineer / @Researcher**

---

## 1. Executive Summary
To optimize contract expiration times for anti-persistent mean-reversion setups, we propose replacing the current static step-wise L2 expiry mapping (e.g., $H < 0.35 \to 60s$, $H < 0.44 \to 120s$) with an adaptive model based on a rolling Ornstein-Uhlenbeck (OU) process.

This document outlines a standardized, quantitative approach to backtest and calibrate this model using the repository's existing tick logs (`app/data/tick_logs/`) and backtesting framework (`scripts/backtest_oteo_levels.py`).

---

## 2. Mathematical Foundations

### The Ornstein-Uhlenbeck (OU) Process
We model the price $X_t$ of a mean-reverting asset using the stochastic differential equation (SDE):
$$dX_t = \theta (\mu - X_t) dt + \sigma dW_t$$

Where:
* $\theta$: Speed of mean reversion ($\theta > 0$)
* $\mu$: Long-term price mean
* $\sigma$: Standard deviation (instantaneous volatility)
* $dW_t$: Increment of a standard Wiener process

### Discrete-Time Parameter Estimation
To run parameter estimation efficiently over high-frequency tick data, we fit an autoregressive AR(1) model via Ordinary Least Squares (OLS) on a rolling lookback window of $N$ ticks:
$$X_t = a + b X_{t-1} + \epsilon_t$$

Where:
* $a = \mu (1 - e^{-\theta dt})$
* $b = e^{-\theta dt}$
* $\epsilon_t \sim \mathcal{N}(0, \sigma_{\text{eq}}^2)$

From the fitted slope $b$, we extract the speed of mean reversion:
$$\theta = -\frac{\ln(b)}{dt}$$

And calculate the **mean-reversion half-life** ($\tau$), which represents the expected time for the price deviation to decay by 50% toward the long-term mean:
$$\tau = \frac{\ln(2)}{\theta}$$

---

## 3. Backtesting Framework Design

We suggest two complementary backtesting approaches to validate the model's predictive accuracy and commercial edge.

### Approach A: Repricing Historical Ghost Trades
Since we already have recorded ghost trade sessions under `app/data/ghost_trades/sessions/`, we can evaluate how dynamic expiry would have altered the outcome of these actual historical signals.

1. **Trade Extraction**: Parse JSONL files using the existing `load_ghost_trades_from_file()` function.
2. **Pre-trade Window Fitting**: For each trade, load the corresponding tick file from `app/data/tick_logs/<asset>/<date>.jsonl`. Select the $N$ ticks prior to the trade's `entry_time`.
3. **Fit AR(1) & Extract Expiry**: Estimate $\theta$ and calculate half-life $\tau$. Round $\tau$ to the nearest broker contract expiry duration (e.g. 15s, 30s, 60s, 120s, 180s, 300s).
4. **Outcome Evaluation**: Call the existing `evaluate_expiry()` function with the dynamically selected expiry time.
5. **Comparison**: Compare the resulting Win/Loss statistics against both the *original static execution* and the *re-priced static baseline* over identical signals.

### Approach B: End-to-End Tick Replay
To test the model in a sandbox environment that evaluates the OTEO signals and the adaptive expiry concurrently:

1. Use `BacktestRunner` in `scripts/backtest_oteo_levels.py`.
2. For each actionable signal generated:
   * Instantiate a temporary window of ticks directly preceding the signal.
   * Run the AR(1) regression to calculate the dynamic expiry time.
   * Log the trade using this dynamic duration.
3. Aggregate results using `_summarize_by()` to isolate performance by regime, asset, and hour.

---

## 4. Parameter Calibration (Optimization)

To maximize performance, we must calibrate the lookback window size and scale factor coefficients.

### Key Optimization Variables
| Variable | Range | Description |
| --- | --- | --- |
| **Lookback Window Size ($N$)** | $100$ to $1000$ ticks | Number of preceding ticks used to estimate the AR(1) parameters. Larger windows reduce noise but introduce lag. |
| **Vol/Hurst Scale Factor ($C$)** | $0.5$ to $5.0$ | Scalar coefficient in the composite expiry formula: $\text{Expiry} = C \cdot \frac{1 - H}{V}$ |
| **Min/Max Expiry Caps** | $15$s to $600$s | Absolute boundaries to prevent extreme estimations from issuing unviable contract terms. |

### Loss & Objective Functions
* **Objective 1 (P&L Focus)**: Maximize the Profit Factor (Gross Wins / Gross Losses) at standard Pocket Option payout levels:
  $$\text{Maximize } \sum \text{net\_pl}$$
* **Objective 2 (Resolution Alignment)**: Minimize the Mean Absolute Deviation between the predicted half-life $\tau$ and the actual time-to-cross ($T_{\text{cross}}$) the deviation boundary:
  $$\text{Minimize } \frac{1}{M} \sum_{i=1}^M \left| \tau_i - T_{\text{cross}, i} \right|$$

---

## 5. Implementation Roadmap
1. **Develop Script** (`scripts/backtest_ou_calibration.py`): Implement the OLS AR(1) fitting routine using Python's `numpy` for fast vectorized regressions.
2. **Reprice Sample Session**: Test the script on a single day's tick log to verify execution speed.
3. **Execute Param Grid Search**: Run a grid-search across dates using the QuFLX conda environment.
4. **Generate Performance Report**: Create an HTML comparison report comparing static vs. dynamic win rates across assets and time blocks.
