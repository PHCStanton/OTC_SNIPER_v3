## 0. ACTIVE WORK — PreFlight Gate Remediation Plan (2026-08-23/24) — ALL PHASES COMPLETE ✅ (M14 deferred)

**Plan document:** `Dev_Docs/PreFlight_Gate_Remediation_Plan_26-08-23.md` (single source of truth — read it FIRST)
**Source diagnostic:** `Reports-1/Executive_Diagnostic_and_Audit_Report.md` (Stability 74/100)
**Protocol:** `.agents/PHASE_REVIEW_PROTOCOL.md` — @Reviewer sign-off after every phase; explicit user command between phases.
**Environment:** conda `QuFLX-v2`; PowerShell (`;` separators, no `&&`).

### Verification commands (all green as of session end)
```
conda run -n QuFLX-v2 python -m pytest test_preflight_gate_contracts.py test_auto_ghost.py test_ghost_tick_safety.py test_htf_directional_bias.py test_pulse_trajectory_engine.py tests/test_bayesian_signal_filter.py tests/test_bayesian_prior_updater.py test_knowledge_base_retrieval.py
→ 84 passed
npm --prefix app/frontend run build  → clean
```
NOTE: do NOT chain these two with `;` in one line — conda run swallows the separator and passes it to pytest.

### Phase 8 rewrite (executed 2026-08-24, user-approved per Core Principle #7)
- **H3:** `AutoGhostService.update_config` rewritten as declarative spec tables (`_AUTO_GHOST_FIELD_SPECS` caster+bounds, `_AUTO_GHOST_LIST_CASTERS`, `_PLUGIN_MANAGED_CONFIG_FIELDS`) in `auto_ghost.py`; `streaming.py::update_runtime_settings` now forwards via `_AUTO_GHOST_FORWARD_MAP`. Explicit None = no-change preserved; unknown fields logged+ignored; disabled→enabled session reset side effect preserved.
- **H4:** `consider_signal` decomposed into `_passes_ghost_gates()` (returns reject reason strings; `_reject` bookkeeping stays at call site), `_build_trade_request()`, `_finalize_execution()`. C3 sync-capacity-reservation preserved exactly.
- **M8:** `BayesianPriorStore.read()` cached on `(mtime_ns, size)`; refreshed after local atomic writes in `_write_atomic_under_lock`.
- **M9/M10:** trajectory registration rejections log warnings; settlement reports carry `"exit_price_unresolved"` flag.
- **M5:** AI Pulse payout is explicit None-handling (no fabricated 85.0); entry_context may carry `payout_pct: None`.
- **M6:** `HTFDirectionalBiasEngine.get_instance()` now lock-guarded (`_instance_lock`).
- **M14 DEFERRED:** split ~500-line `test_auto_ghost.py` into per-gate modules — open follow-up task.

### Completed remediations (all marked ✅ Resolved in plan's Current State Map)
| Phase | Items | Key files |
|---|---|---|
| 1 | C1: `_recent_ticks` wired into `_get_asset_market_context_snapshot` | `streaming.py` |
| 2 | C2: Bayesian WP cache `_latest_bayesian_wp` + fail-closed gate at T−5s | `streaming.py`, `auto_ghost.py` |
| 3 | C3: capacity TOCTOU closed (sync reservation before first await; cooldown-eviction fix-up) | `auto_ghost.py` |
| 4 | H2: removed silent `expiration` fallback in `on_trade_outcome` (fail-closed skip + warning) | `extensions/bayesian_signal_filter.py` |
| 5 | H7: `ai_pulse_aborted` emitted from all 4 skip paths of `execute_ai_pulse_signal`; M1: snapshot reads `regime_confidence`/`regime_stable` classifier keys | `auto_ghost.py`, `streaming.py` |
| 6 | H1: post-settlement observation window (`_observation_trades`, OBSERVATION_WINDOW_SECONDS=300, MAX_OBSERVATION_TRADES=200, `_finalize_observation` replaces provisional report; fixed latent `record_tick` empty-guard bug) → PREMATURE_EXPIRATION reachable for 60s trades | `pulse_trajectory_engine.py` |
| 7 | H5: O(1) incremental return stats (`_ret_sum`/`_ret_sumsq`) replace per-tick np.array; M11: pending-card bound to `trade_entry`(ai_pulse)/`ai_pulse_aborted` + 15s grace; M12: tabular-nums; M3: 5s sleep-floor removed in `_ai_pulse_loop`; M4: PUT wait regex scoped to match span; L1: tick_flow_300s documented report-only; L4: re/json hoisted to module level | `market_context.py`, `GhostTradingWidget.jsx`, `streaming.py`, `htf_directional_bias.py` |

### Key contracts preserved by the rewrite (for future reference)
- `TestExecutePulseAbortEmission` asserts abort reasons: substrings "disabled", "active", "concurrent", "failed".
- `TestCapacityRace`: concurrent consider_signals with max_concurrent_trades=1 must execute exactly once (TOCTOU guard).
- Reject reason strings flow into `_last_reject_reason_by_asset` — treat as observable contract.
- `update_config` resets ghost session on disabled→enabled transition — preserved side effect.

---


---

## 1. Historical Context (2026-06-22 backtesting session)

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

---

## 3. Database & GCP Architecture Assessment (2026-07-12)

### 3.1 Google Cloud Data Agent Kit & Redis Evaluation
*   **Redis Integration Postponed:** Determined that an external Redis instance is not immediately required. Current single-process FastAPI in-memory structures (`deque` and thread-safe queues) handle low-latency checks at microsecond speeds.
*   **GCP Data Agent Kit Sufficiency:** Standard database, data warehouse, and streaming tools (AlloyDB/PostgreSQL, BigQuery, and Dataflow) along with the agent extensions are fully sufficient for data scaling, migration, and ETL feature engineering.
*   **AlloyDB Omni for Development:** Can run AlloyDB Omni locally inside a Docker container for high-performance PostgreSQL testing at zero cloud cost.

### 3.2 Database Migration Strategy (Hybrid Solution)
*   **Supabase for App State & Auth:** Migrate user accounts, Ghost configurations, active trading sessions, and trade execution outcomes to Supabase (utilizing its generous free tier/predictable $25 flat rate for Auth, Realtime, and auto-generated APIs).
*   **BigQuery for Tick History:** Upload high-frequency raw tick logs to BigQuery (leveraging the 10 GB storage and 1 TB query scans free monthly tier) to perform backtests, Hurst calculations, and streak pattern analysis, thereby bypassing Supabase storage and compute limits.



