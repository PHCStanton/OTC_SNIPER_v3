## 0. ACTIVE WORK — Auto-Ghost Calibration Mode Stability & Integrity Remediation (2026-09-03/04) ✅ COMPLETE

**Plan documents:**
- Diagnostic Report: `Reports-1/Calibration_Mode_Multi_Agent_Review_Report_26-09-03.md`
- Implementation Plan: `brain/a7ef0473-8a3e-4eb6-82fa-a4703b7666ae/implementation_plan.md`
- Walkthrough: `brain/a7ef0473-8a3e-4eb6-82fa-a4703b7666ae/walkthrough.md`
- Base Plan: `Dev_Docs/Auto_Ghost_Calibration_Mode_Plan_26-08-26.md` & `Dev_Docs/Calibration_Mode_Stability_Remediation_Plan_26-08-31.md`
- **Protocol:** `.agents/workflows/phase-review-protocol.md`. conda `QuFLX-v2`; PowerShell `;` not `&&`.
- **Branch:** `feat/ai_kb`

### Status: All Planned Stability Fixes Implemented & Verified ✅

| ID | Finding & Remediation | File(s) | Status |
|---|---|---|---|
| **BUG-3** | **Finalize AI Review Timeout:** Wrapped `_run_milestone_review` in `CalibrationService._finalize` with `asyncio.wait_for(..., timeout=90.0)` + `except asyncio.TimeoutError`. Prevents wedged LLM providers from stranding finalize or forcing an invalid `ABORTED`. | `app/backend/services/calibration_service.py` | Verified ✅ |
| **BUG-1** | **Server Shutdown & Boot Restore:** Added FastAPI `lifespan` shutdown hook in `main.py` calling `calib.abort(reason="server_shutdown")`. In `_reconcile_stale_sessions`, auto-restored `config_snapshot` into `AutoGhostService` for interrupted sessions marked `STALE_ABORTED`. | `app/backend/main.py`, `app/backend/services/calibration_service.py` | Verified ✅ |
| **BUG-2** | **Guardian Notification Separation:** Switched Guardian emissions from `"ai_pulse"` to `"guardian_proposal"` and `"guardian_alignment"`. Updated `TopBar.jsx` with `ShieldAlert` cyan badge styling, preventing pulse card collisions in `GhostTradingWidget.jsx`. | `app/backend/services/calibration_service.py`, `app/frontend/src/components/layout/TopBar.jsx` | Verified ✅ |
| **H-3** | **Time Budget Watchdog Drain Alignment:** Refactored `_time_budget_watchdog` to use `_request_terminal("DONE", "time_budget_elapsed")` and `_begin_drain()`. Eliminates state race with `_check_budgets_sync`. | `app/backend/services/calibration_service.py` | Verified ✅ |
| **OPT-7 / H-4** | **Bessel's Sample Variance & 10-Trade Rolling Window:** Changed `_mean_std` to sample variance ($N-1$); enhanced `classify_alignment` to average features across a rolling 10-trade slice (`trades[-min(len(trades), 10):]`) to suppress single-trade noise. | `app/backend/services/ghost_protocol_profiles.py`, `app/backend/services/calibration_service.py` | Verified ✅ |
| **OPT-2 / H-2** | **Dead Code & Disk Cleanup:** Pruned unreachable Tier B check in `calibration_autonomy.py`; implemented automated pruning of `DONE` session files keeping newest 20 while preserving all aborts. | `app/backend/services/calibration_autonomy.py`, `app/backend/services/calibration_service.py` | Verified ✅ |
| **Contracts** | **Regression Tests:** Added `test_reconcile_restores_snapshot_and_prunes_done` and `test_guardian_notification_types`. | `test_calibration_contracts.py` | Verified ✅ |

### Verification Evidence
1. `conda run -n QuFLX-v2 python -m pytest test_calibration_contracts.py test_calibration_autonomy.py test_ghost_protocol_profiles.py -v` → **54 passed in 20.19s**
2. `conda run -n QuFLX-v2 python -m pytest test_kb_health_phase4.py test_ai_pulse_prompt.py test_auto_ghost.py -v` → **36 passed in 1.56s**
3. `npm --prefix app/frontend run build` → **Clean build in 25.78s** (1704 modules transformed)

### Clarification Decisions Persisted
1. **Bayesian Priors vs Calibration:** Calibration mode tunes the Bayesian floor gate threshold (`bayesian_min_probability`), while priors (`bayesian_priors.json`) come pre-seeded from disk and are updated only via staging/backfill commits.
2. **Ghost Trader Bayesian Config:** Starts with the active protocol config (`active_protocol.json` / `AutoGhostConfig` defaults). If disabled or uncalibrated, it can be updated via the Trading Journal staging flow.
3. **Phase 6 Discord NotificationSink:** Remains strictly **DEFERRED** per user instructions. Do not start.

### Open Follow-ups
1. Live paper browser calibration dry-run (observing visual transition across IDLE → CALIBRATING → ANALYZING → PROPOSING → DONE/ABORTED and snapshot restore).
2. Phase 6 Discord NotificationSink (pending explicit user request).

### Locked design (still true)
- Ghost kind only (D1). Silent = route all five live surfaces, not rename one event. Copy-mode `execute` hard-blocked while RUNNING (D2). Runtime-config 409 while RUNNING/ANALYZING/PROPOSING (C3). D4 auto-restore snapshot on DONE/ABORTED (including `None` fields via `dataclasses.replace`). Budget counts settled win/loss only. Kill-switch is CalibrationService-owned, not the 300s drawdown cooldown. `minimum_payout_pct` is **85.0 percent**, never `0.85`. Bayesian floor is **0.50–0.90 float**. Master KB writes only via staging commit (N≥5/N≥20, `.bak`). UTC 4h blocks origin **22:00** (block 5 = 18:00–22:00, block 0 = 22:00–02:00).

### Key modules (cite these, don't re-derive)
- `app/backend/services/calibration_service.py` — single owner of calibration state + Guardian loop (alignment/drift after DONE).
- `app/backend/services/calibration_autonomy.py` — pure Tier A/B + `guardian_proposals` + `guardian_prior_transfer`.
- `app/backend/services/kb_health.py` — audit + `stage_historical_backfill` (staging-only) + warm-start.
- `app/backend/services/ghost_protocol_profiles.py` — presets, `FRONTEND_GATE_KEYS` (M8), `detect_market_drift`, `classify_alignment`.
- `shared/utc_time_blocks.py`, `shared/bayesian_prior_store.py` (integer counts + optional `recency` overlay).
- Frontend: `useCalibrationStore.js`, `CalibrationPanel.jsx`, `useSettingsStore.js` `applyGhostProtocolGates` / `GHOST_STRICTNESS_PRESETS`.
- CLI: `scripts/kb_health_backfill.py --audit --backfill --stage-only`. APIs: `GET /api/analysis/kb-health`, `POST /api/analysis/kb-backfill`, `GET /api/analysis/warm-start`.

### Open follow-ups (NOT Phase 6)
1. Phase 3 P1s: `_finalize` awaits AI before D4 restore (can stick PROPOSING); locked `amount`/`expiration` dropped from Tier B; Guardian empty `allowed_regimes` = allow-all.
2. A3 suggestion-effectiveness ledger incomplete.
3. Phase 4 suggestions: live Bayesian scoring still unweighted integers; corrupt warm-start only logged; staging-modal copy still describes integer prior merges.
4. Live paper calibration (badge, silence, restore, Apply cards) not browser-verified.
5. Phase 6 Discord — wait for explicit command.

### NEXT STEP
- Do **not** implement Phase 6.
- Optional: Phase 3 P1s, A3 ledger, Phase 4 scoring/overlay-read, live calibration dry-run.
- `.agent-memory/activeContext.md` + `progress.md` record PreFlight as complete — do NOT re-add that milestone.

### Phase 0 implementation record (historical, 2026-08-26) — complete
- **P0-1 Payout (EX-9):** asset summaries now resolve payout via `await self._resolve_asset_payout_pct(asset)` (TTL cache); rendered `Payout=85.0%` or `Payout=UNAVAILABLE`; trade lines show `entry_context.payout_pct` (None-safe per M5); user_msg gained `Minimum Payout Gate: {x:.1f}% (percent units...)` context line.
- **P0-2 Bayesian WP:** `self._latest_bayesian_wp` cache merged → `WP60=/WP300=` per asset summary (UNAVAILABLE fallback).
- **P0-3 HTF (M5):** NEW `StreamingService._compute_pulse_htf_summary(asset)` computes direction-agnostic verdict ON DEMAND (chosen over a cache — verified no `_last_htf` field exists); uses `HTFDirectionalBiasEngine.get_instance().compute_htf_trend(closed_candles)` + `compute_tick_flow_ratio(recent_ticks, 60s/300s)`; local import; try/except → None → UNAVAILABLE marker.
- **P0-4 Vol/Liq:** `volatility_score`/`liquidity_score` from `mc_engine._cached_context` in summaries; vol/liq gate bands + Bayesian floor lines added to user_msg.
- **P0-5 Trajectory:** `PulseTrajectoryEngine.get_instance().get_trajectory_analytics()` → attribution distribution line in user_msg (fail-soft try/except → UNAVAILABLE).
- **P0-6 Confidence (M7, THREE sites):** prompt JSON example rebuilt WITHOUT `"confidence": 85` (+ honesty instruction #4); both regex fallbacks now go through NEW module-level `_extract_pulse_signal_from_text()` emitting `confidence: None`.
- **P0-7 Rolling stats:** rolling last-20 settled WR + explicit N>=20 sample-size rule line in user_msg.
- **P0-8 Clamp (M6/EX-21):** `_AUTO_GHOST_FIELD_SPECS["bayesian_min_probability"]` → `(float, 0.50, 0.90)` in `auto_ghost.py`.
- **Refactor for testability:** prompt construction extracted to module-level pure builders in `streaming.py` (after `normalize_otc_asset_symbol`): `_build_ai_pulse_system_msg()`, `_build_pulse_asset_summary()`, `_build_pulse_user_msg()`, `_extract_pulse_signal_from_text()`, `_fmt_or_unavailable()`. `_run_ai_pulse_insight` rewired to call them — behavior preserved.
- **Tests:** NEW `test_ai_pulse_prompt.py` — 24 tests (system prompt contract, asset summary, user message, regex fallback, HTF on-demand computation, Bayesian clamp). **Verification: 109/109 passed** (85 prior + 24 new); py_compile clean.

### Key code facts (updated 2026-08-31 — stale 2026-08-26 line numbers below are historical)
- Calibration owner is `CalibrationService`, not smeared state. Silent UI = `emit_trade_channel(..., calibration=True)` on all five surfaces.
- `_AUTO_GHOST_FIELD_SPECS["bayesian_min_probability"]` is `(float, 0.50, 0.90)` (P0-8). Payout gate is percent.
- `loadGhostProtocol` / `applyGhostProtocolGates` now load vol/liq/Bayesian/payout/amount/concurrency (M8). Do not revert to z-score+regime-only.
- Historical note (pre-Phase-0 tree): prompt `"confidence": 85`, unbounded Bayesian spec, no HTF cache — those Phase 0/1 gaps are closed. Pulse-path manip veto `> 0` vs default `0.0` is still an intentional A1 behavior change when calibration sets 0.35.

## 0.b COMPLETED — PreFlight Gate Remediation (2026-08-23/24) ✅ (M14 deferred — open follow-up: split ~500-line `test_auto_ghost.py` into per-gate modules)

**Plan document (historical):** `Dev_Docs/PreFlight_Gate_Remediation_Plan_26-08-23.md` — all 8 phases + post-audit Z-score fix complete. Final report: `Reports-1/PreFlight_Gate_Remediation_and_Execution_Integrity_Report_26-08-24.md`. Milestone already recorded in `activeContext.md` + `progress.md` — do NOT re-add.
**Protocol:** `.agents/PHASE_REVIEW_PROTOCOL.md`; **Environment:** conda `QuFLX-v2`; PowerShell (`;` separators, no `&&`).

### Verification commands (all green as of session end)
```
conda run -n QuFLX-v2 python -m pytest test_preflight_gate_contracts.py test_auto_ghost.py test_ghost_tick_safety.py test_htf_directional_bias.py test_pulse_trajectory_engine.py tests/test_bayesian_signal_filter.py tests/test_bayesian_prior_updater.py test_knowledge_base_retrieval.py
→ 85 passed
npm --prefix app/frontend run build  → clean
```
NOTE: do NOT chain these two with `;` in one line — conda run swallows the separator and passes it to pytest.

### Post-Remediation Polish & Audit Fixes (2026-08-24)
- **Z-Score Gate Forwarding Fix:** Added `auto_ghost_min_zscore_enabled`, `auto_ghost_min_zscore`, `auto_ghost_max_zscore_enabled`, `auto_ghost_max_zscore` to `_AUTO_GHOST_FORWARD_MAP` and `_param_values` in `streaming.py::update_runtime_settings`. Verified with new contract test in `test_preflight_gate_contracts.py::TestStreamingSettingsForwardingContract`.

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



