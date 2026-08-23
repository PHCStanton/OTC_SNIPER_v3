# Executive Diagnostic and Audit Report — OTC_SNIPER

**Audit Date:** 2026-08-23
**Scope:** AI Pulse candle-synchronized execution, HTF Directional Bias Engine, Pre-Flight Validation Gate, Multi-Candle Wait scheduling, Defensive Asset Parsing, UI Telemetry, Bayesian Adaptive Expiries / Dual-Horizon Prior Routing, Pulse Trajectory Post-Mortem Engine.
**Method:** Read-only forensic investigation (diagnose-quflx protocol). Five parallel specialist audits (@Investigator, @Debugger, @Optimizer, @Code_Simplifier/@UI-Designer, @Tester) followed by direct line-level verification of every CRITICAL/HIGH finding by the lead investigator. All citations below were verified against actual source code — nothing is paraphrased without evidence.
**Constraint compliance:** No code was modified during this diagnostic.

---

## 1. Summary

The AI Pulse pipeline is architecturally sound and connects end-to-end (generation → clock alignment → scheduling → pre-flight gate → execution → trajectory settlement), and the shared Bayesian prior store is production-grade. However, **two of the four headline pre-flight validation gates are provably inert due to dictionary key-contract breaks** (tick-flow veto and Bayesian floor never receive their inputs), a **capacity-check race** can oversubscribe `max_concurrent_trades`, the **PREMATURE_EXPIRATION post-mortem branch is mathematically unreachable** for 60s trades, and **one unit test is currently failing** (horizon isolation in `bayesian_signal_filter`). Overall system health is good; execution-critical correctness has three CRITICAL defects that must be remediated before the pre-flight gate can be trusted in live sessions.

---

## 2. Executive Scorecard

| Dimension | Score | Basis |
|---|---|---|
| Execution Reliability | 68% | Capacity race (C3); silent capacity-loss drop between T−5s and T (H7) |
| Timing Synchronization | 88% | Candle-open math exact; ≤5s snap overshoot floor (M3); no T−15s phase as documented (M2) |
| Bayesian Precision | 62% | Floor gate inert in pre-flight (C2); 1 failing horizon-isolation test (H2); prior store itself excellent |
| Mathematical Soundness | 74% | PREMATURE_EXPIRATION unreachable (H1); confluence scoring otherwise coherent |
| Error Containment | 82% | No bare excepts found in scoped paths; several log-only swallows in non-fatal paths |
| Performance | 84% | One O(N)-per-tick numpy hotspot (H5); flow-ratio full rescans (M7); otherwise bounded deques/caches |
| UI/UX Telemetry | 86% | Countdown functional with cleanup; local-drift and early-clear issues (M11) |
| Test Integrity | 93% | 72/73 passing; coverage gaps exactly where the CRITICALs hide |

### **Overall Stability Score: 74 / 100**
### **Readiness Rating: CONDITIONAL — NOT ready to trust the Pre-Flight Gate as a safety layer until C1–C3 are fixed.**

---

## 3. Critical Issues (Severity-Rated)

| ID | Severity | Title | Location |
|---|---|---|---|
| C1 | 🔴 CRITICAL | Pre-flight HTF tick-flow veto is dead code — `recent_ticks` never populated | `auto_ghost.py:1010`, `streaming.py:726–740` |
| C2 | 🔴 CRITICAL | Pre-flight Bayesian floor gate never fires — WP key absent from context snapshot | `auto_ghost.py:1027`, `market_context.py` (`apply_level2_policy`), `extensions/bayesian_signal_filter.py` |
| C3 | 🔴 CRITICAL | Capacity-check race oversubscribes `max_concurrent_trades` | `auto_ghost.py:711–716 → 806 → 815` |
| H1 | 🟠 HIGH | `PREMATURE_EXPIRATION` attribution unreachable for 60s trades | `pulse_trajectory_engine.py:128–131, 185` |
| H2 | 🟠 HIGH | Failing test: horizon isolation skip-on-missing-expiration | `tests/test_bayesian_signal_filter.py::test_on_trade_outcome_skips_when_missing_expiration` |
| H3 | 🟠 HIGH | ~175-line copy-paste config boilerplate (`update_config` + 40-kwarg forward) | `auto_ghost.py:122–297`, `streaming.py:129–243` |
| H4 | 🟠 HIGH | `consider_signal` is a 310-line multi-responsibility function | `auto_ghost.py:516–825` |
| H5 | 🟠 HIGH | Per-tick numpy array materialization outside cache gate | `market_context.py:547–552` |
| H6 | 🟠 HIGH | Entry-price fallback `or 1.0` corrupts trajectory MFE/MAE; failed executes hold capacity | `auto_ghost.py:868–872, 905–913` |
| H7 | 🟠 HIGH | Silent pending-setup drop between T−5s and T (no `ai_pulse_aborted` emit) | `auto_ghost.py:844–850 vs 969–974` |

---

## 4. End-to-End Execution Trace & Verification (@Investigator / @Debugger)

### 4.1 Verified signal chain (CONNECTS ✅)

1. **Generation:** `StreamingService._ai_pulse_loop` (`streaming.py:748`) → `_run_ai_pulse_insight` (`streaming.py:772`); JSON block parsed at `streaming.py:910–920`, regex fallback at `925–955`.
2. **Schedule hop:** `streaming.py:977–988` — `if self.auto_ghost.config.auto_execute_ai_pulse and extracted_signal:` → `asyncio.create_task(self.auto_ghost.schedule_candle_open_pulse_execution(...))`.
3. **Clock alignment:** `target_candle_open = (int(now // 60) + wait_m) * 60.0` (`auto_ghost.py:946`) — exact future candle-open epoch. Multi-minute waits compute correctly; no midnight-UTC hazard in this arithmetic (pure epoch math).
4. **Pre-flight gate at T−5s:** `auto_ghost.py:964–1034` — capacity (969), target-price proximity ±0.4% (977–991), manipulation (994–1004), HTF confluence veto (1006–1023), Bayesian floor (1025–1034). Each abort path logs AND emits `ai_pulse_aborted` ✅.
5. **Execution:** final sleep to exact T (`1037–1038`) → `execute_ai_pulse_signal` (`1041` → def at `827`) → `TradeService.execute_trade(BrokerType.POCKET_OPTION, request)` with `trigger_mode="ai_pulse"` (`892–903`).
6. **Settlement:** `PulseTrajectoryEngine.register_pulse_trade` / `record_tick` / `settle_pulse_trade` with `_trade_lock`-guarded state and `deque(maxlen=500)` settled history (`pulse_trajectory_engine.py:58–61, 87–88, 222–223`).

### 4.2 Dictionary key-contract audit — THREE BREAKS FOUND

**🔴 C1 — `recent_ticks` is never delivered to the pre-flight gate.**
Producer side, `auto_ghost.py:1009–1016`:
```python
candles_1m = mc.get("closed_candles") or []
recent_ticks = mc.get("recent_ticks") or []
confluence = htf_engine.evaluate_directional_confluence(...)
```
The consumer of `mc` is `trade_service._get_market_context` → bound at `streaming.py:78` to `_get_asset_market_context_snapshot` (`streaming.py:726–740`), which populates ONLY: `closed_candles`, `manipulation`, `regime_label`, `regime_confidence`, `regime_stable`, `volatility_score`, `liquidity_score` (+ whatever `_cached_context` holds). A repo-wide search confirms **no code path ever writes `"recent_ticks"` into market context** — the only other uses of `recent_ticks` are engine pre-seeding (`streaming.py:367`) and `trade_service` price lookups.

**Consequence (proven):** `compute_tick_flow_ratio([])` returns `50.0` (`htf_directional_bias.py:173–174, 184–185`) → `tick_delta_60 = 0` → microstructure contribution is permanently neutral → the DIVERGENT veto condition `(is_call and tick_flow_60s < 38.0) or (not is_call and tick_flow_60s > 62.0)` (`htf_directional_bias.py:260–262`) is **unreachable**. The entire rolling tick-flow subsystem (a headline feature of the 2026-08-17 delivery) contributes nothing at execution time.

**🔴 C2 — Bayesian win probability never reaches the pre-flight gate.**
Consumer, `auto_ghost.py:1026–1029`:
```python
calibrated_floor = confluence.get("calibrated_bayesian_floor", self.config.bayesian_min_probability)
b_prob = mc.get("bayesian_win_probability_60s") or mc.get("bayesian_win_probability")
```
Producer, `extensions/bayesian_signal_filter.py`: writes `oteo_result["market_context"]["bayesian_win_probability*"]` — but `apply_level2_policy` explicitly isolates that dict (`market_context.py`): `result["market_context"] = dict(market_context)` with the comment *"Keep the nested market_context isolated from upstream callers."* The per-tick enriched copy is discarded after the tick. The snapshot reads `mc_engine._cached_context`, which **never contains any `bayesian_win_probability` key** (verified by repo-wide search: the key is written only inside `bayesian_signal_filter.py`).

**Consequence (proven):** `b_prob` is always `None` → step 5 of the pre-flight gate is silently skipped whenever reached. The calibrated 51%–56% Bayesian floor — the core risk control of the AI Pulse auto-executor — **does not run**. This violates CORE_PRINCIPLE #8 (zero silent failures): the gate fails *open*, silently.

**🟡 M1 — RegimeClassifier key mismatch in the snapshot.**
`regime_classifier.py::classify` returns `regime_label`, `regime_confidence`, `regime_detail` (verified). But the snapshot reads (`streaming.py:736–737`):
```python
ctx["regime_confidence"] = regime.get("confidence")
ctx["regime_stable"] = regime.get("stable")
```
Both keys are wrong → `regime_confidence`/`regime_stable` in the snapshot context are always `None`. Currently low blast radius (primary consumers use `oteo_result` payload keys, which are correct at `streaming.py:591–597`), but it is a latent contract break for any future consumer of the snapshot.

**Contracts verified OK ✅:** `closed_candles` (snapshot → resampler, dict/dataclass dual handling at `htf_directional_bias.py:46–50`); direction casing normalized at boundaries (`direction.upper()` at gate, `.lower()` at request, `ActivePulseTrade.__post_init__` lowercases); asset normalization (`normalize_otc_asset_symbol`, `streaming.py:35–56`, enforced again at `auto_ghost.py:836` and `935`); `expiration_seconds` propagation through entry_context → TradeExecutionRequest → trajectory record; `wait_minutes` consistent between JSON path (`streaming.py:984`) and regex fallback (`932, 947`).

### 4.3 Race conditions & timing hazards (@Debugger)

**🔴 C3 — Capacity-check race (TOCTOU).** `consider_signal` checks capacity at `auto_ghost.py:713–714`:
```python
if len(self._active_assets) >= self.config.max_concurrent_trades:
    return self._reject(asset, 'max_concurrent_trades')
```
then `await`s `execute_trade` at `806` before adding at `815`. `consider_signal` runs as concurrent tasks spawned per actionable tick (`streaming.py:671–692`, semaphore-bounded but not serialized). Two tasks for different assets can both pass the check before either reaches `815` → transient oversubscription of the core risk cap. Same pattern applies to the cooldown check at `715–716`.

**🟡 M2 — Documented T−15s phase does not exist.** The architecture docs describe a two-phase pre-flight ($T-15\text{s}$ → $T-5\text{s}$); implementation has a single sleep to $T-5\text{s}$ (`auto_ghost.py:963–965`). Doc/code divergence — either implement the early phase or correct the documentation.

**🟡 M3 — Snap overshoot floor.** `_ai_pulse_loop` computes `sleep_duration = max(5.0, delay)` (`streaming.py:758`); when the computed delay to the $:45\text{s}$ offset is < 5s, the loop overshoots the snap by up to 5s. Downstream scheduling still lands on the exact candle open (independent math), so impact is limited to insight freshness, not execution precision.

**🟡 H7 — Silent drop window between T−5s and T.** If capacity is consumed by another trade between the T−5s check and T, `execute_ai_pulse_signal`'s internal re-check (`auto_ghost.py:844–850`) skips **with a log line only** — no `ai_pulse_aborted` emission. The UI pending card lingers until its local countdown expires (see M11). Defense-in-depth re-check is correct; the observability gap is not.

**Locking verified OK ✅:** `PulseTrajectoryEngine` uses a class-level singleton lock plus `_trade_lock` around all state mutations (`pulse_trajectory_engine.py:49–61, 87, 98, 141, 222`); `BayesianPriorStore` uses a real cross-platform sidecar lock (`msvcrt.locking` / `fcntl.flock`, `bayesian_prior_store.py:214–230`) with timeout, fsync'd temp-file atomic replace, bounded Windows replace-retry (`383–408`), and fail-closed corruption handling (`296–321`) — no deadlock or torn-write vector identified.

**Exception containment:** No bare `except:` clauses in scoped files. Extension hook failures are logged-and-continue (`auto_ghost.py:708–709`, `streaming.py:495–496, 546–547`) — acceptable for plugin isolation. `_release_asset` / advisory tasks carry done-callback error logging (`auto_ghost.py:752, 818, 911`). AI Pulse loop backoff resets `consecutive_failures` on success (`streaming.py:765`).

---

## 5. Mathematical & Bayesian Calibration Audit (@Architect)

1. **Confluence scoring is coherent:** HTF ±40 + tick-flow ±60 clamped to [−100, +100] (`htf_directional_bias.py:225–238`); tiered floors 52.0/53.5/55.5/56.0 map monotonically to STRONG_ALIGNMENT/ALIGNED/COUNTER_TREND/DIVERGENT (241–265). ⚠️ But because of C1, in production the score currently degenerates to HTF-only ±40.
2. **`PREMATURE_EXPIRATION` is unreachable for 60s trades (H1).** Checkpoints fill only while a trade is active (`pulse_trajectory_engine.py:128–131`); a 60s trade settles at ≈60s, so `checkpoints[180]`/`checkpoints[300]` are always `None` → `cp_180_fav is True or cp_300_fav is True` (line 185) can never be true. The engine's flagship "extend to 300s" recommendation can never be produced. Fix requires sampling checkpoints beyond expiration (keep the trade registered until `max(CHECKPOINT_INTERVALS)` or settle-time + lookahead window).
3. **STRUCTURAL_TRAP ratio test is scale-invariant** (`mfe <= mae * 0.1`, line 193) — sound across assets. However MFE/MAE are stored in raw price units; cross-asset analytics aggregation would need pip-normalization if ever compared across symbols.
4. **Bayesian prior store math is pure and validated**: `apply_trade_outcomes` is a pure function with strict schema normalization (rejects bool-as-int, impossible totals, empty feature keys — `bayesian_prior_store.py:69–119`). Laplace-style smoothing lives in the filter layer; store integrity is solid.
5. **Horizon isolation regression (H2):** `tests/test_bayesian_signal_filter.py::test_on_trade_outcome_skips_when_missing_expiration` FAILS (`assert 1 == 0` — a trade with missing `expiration_seconds` was scored into the default bucket instead of being skipped). This is exactly the class of bug the Phase-1 "Horizon Integrity" work was meant to prevent — treat as a regression, delegate to @Debugger/@Coder.
6. **Candle-open arithmetic** `(int(now // 60) + wait_m) * 60` is exact and timezone-safe (epoch-based; midnight rollover poses no hazard here). ✅

---

## 6. Performance & Latency Optimization Audit (@Optimizer)

Load model: ~10 assets × ~5 ticks/s = 50 ticks/s through ONE serialized consumer loop (`streaming.py:451–472`) — blocking work delays every asset.

| ID | Sev | Finding | Location | Fix |
|---|---|---|---|---|
| H5 | HIGH | Fresh `np.array(deque)` + diff/std on EVERY tick, outside the `_cached_context` gate — ~50 allocations/s | `market_context.py:547–552` | Welford incremental variance, or compute on candle close only |
| M7 | MED | `compute_tick_flow_ratio` full-window scan, called twice (60s+300s) per confluence eval | `htf_directional_bias.py:179–197` | Sliding up/down counters per asset; O(1) amortized |
| M8 | MED | Prior store re-reads JSON from disk on every access; no in-memory cache | `bayesian_prior_store.py:286–321` | Cache with mtime invalidation |
| L1 | LOW | `tick_flow_300s` computed but unused in scoring | `htf_directional_bias.py:219, 276` | Use it or drop it |
| L4 | LOW | `re`/`json` imported inside `_run_ai_pulse_insight` per invocation | `streaming.py:777–778` | Hoist to module level |

**Verified efficient ✅:** bounded structures everywhere that matter — `_closed_candles` deque(240), `_settled_trajectories` deque(500), tick queue maxsize=500 with drop-telemetry, payout cache TTL 60s, buffered signal logger, `asyncio.to_thread` for blocking payout resolution (`streaming.py:399`), semaphore-bounded signal tasks with explicit backpressure warning (`streaming.py:661–667`).

---

## 7. Code Simplification & Refactoring Recommendations (@Code_Simplifier)

| ID | Target | Evidence | Recommendation | Est. Savings |
|---|---|---|---|---|
| H3 | `AutoGhostService.update_config` | ~90 repeated `if x is not None: updates[k] = clamp(...)` blocks (`auto_ghost.py:122–297`); mirrored by 40-kwarg 1:1 forwarding in `update_runtime_settings` (`streaming.py:129–243`) | Declarative spec table `{field: (caster, min, max)}` iterated once; name-mapping dict + `**updates` forward in streaming | ~190 lines |
| H4 | `consider_signal` | 310 lines mixing gate cascade, advisory dispatch, context build, request build, execution, bookkeeping (`auto_ghost.py:516–825`) | Extract `_passes_ghost_gates()`, `_build_trade_request()`, `_finalize_execution()` | Readability, enables locking fix for C3 |
| M4 | PUT wait-minutes regex | Searches the WHOLE insight text for `Wait:` (`streaming.py:946`) — can borrow a Wait value belonging to a different entry | Scope the wait search to the PUT match span | Correctness |
| L4 | Inline imports | `re`, `json`, service getters imported per pulse call (`streaming.py:774–778`) | Hoist to module level | Hygiene |
| M9/M10 | Trajectory input hygiene | `register_pulse_trade` silently returns on bad input (`pulse_trajectory_engine.py:74–75`); `settle_pulse_trade` falls back exit→entry price (147) masking missing exits | Log-warning on reject; flag `exit_price_unresolved` in report instead of silent substitution | Observability |

---

## 8. UI/UX & Telemetry Review (@UI-Designer / @Frontend-Specialist)

**Verified OK ✅** (`GhostTradingWidget.jsx`): `ai_pulse_pending` / `ai_pulse_aborted` listeners registered AND cleaned up symmetrically; countdown interval cleaned up on effect teardown; MM:SS formatting via `padStart(2,'0')` keeps width stable (no layout shift); semantic colors follow the emerald(win)/rose(loss)/amber(pending) convention elsewhere in the app.

Findings:

| ID | Sev | Finding | Detail |
|---|---|---|---|
| M11 | MED | Countdown is client-decremented from a one-shot `seconds_remaining` | Backend emits `ai_pulse_pending` once at schedule time; the widget then decrements locally (`setInterval` 1s). Background-tab throttling desyncs the timer, and at 0 the card clears itself **without binding to an actual `trade_entry`/abort event** — for multi-minute waits the UI can dismiss a setup that still executes. Bind card lifetime to terminal events (`trade_entry` with `trigger_mode="ai_pulse"`, or `ai_pulse_aborted`), not the local clock. |
| M12 | LOW | Countdown lacks `tabular-nums` | Other numeric readouts in the app use `tabular-nums`; add for pixel-stability across font loads. |
| M13 | LOW | Abort reason surfaced only transiently | `ai_pulse_aborted` clears the pending card; consider a toast/notification so users learn WHY a setup was vetoed (feeds trust in the gate system — especially once C1/C2 make vetoes real again). |

---

## 9. Automated Test Suite Results (@Tester)

`conda run -n QuFLX-v2 python -m pytest ... -v --tb=short`:

| Suite | Passed | Failed |
|---|---|---|
| test_htf_directional_bias.py | 10 | 0 |
| test_auto_ghost.py | 1 | 0 (single monolithic smoke test, ~500 lines — M14: split into focused cases) |
| test_pulse_trajectory_engine.py | 7 | 0 |
| tests/test_journal_stats_service.py | 3 | 0 |
| tests/test_vps_phase4_prior_store.py | 12 | 0 (incl. cross-process lock test) |
| tests/test_bayesian_protocol.py | 6 | 0 |
| tests/test_bayesian_signal_filter.py | 33 | **1** ❌ |
| **Total** | **72** | **1** (11.26s) |

**Failure (verbatim):**
```
tests\test_bayesian_signal_filter.py::test_on_trade_outcome_skips_when_missing_expiration FAILED
tests\test_bayesian_signal_filter.py:195: in test_on_trade_outcome_skips_when_missing_expiration
    assert empty_filter.total_wins == 0
E   assert 1 == 0
```

**Coverage gaps (the CRITICALs hid precisely here):**
1. 🔴 No test feeds a realistic `_get_asset_market_context_snapshot()` payload through `schedule_candle_open_pulse_execution` — an integration assertion that `recent_ticks`/`bayesian_win_probability_60s` arrive populated would have caught C1+C2 immediately.
2. 🟠 No end-to-end test for the target-price proximity REJECTION path (price deviating > 0.4%).
3. 🟠 No end-to-end test for `wait_minutes >= 2` scheduling landing on the correct candle open.
4. 🟠 No test exercises `PREMATURE_EXPIRATION` (it cannot pass as written — see H1; add the test together with the lookahead-window fix).
5. 🟡 `test_auto_ghost.py` is one monolithic smoke test; split per-gate (capacity, cooldown, z-score, regime, manipulation, Bayesian) for diagnosability.

---

## 10. CORE_PRINCIPLES Compliance Matrix

| # | Principle | Status | Notes |
|---|---|---|---|
| 1 | Functional Simplicity First | ⚠️ Partial | H3/H4 boilerplate bloat; otherwise lean |
| 2 | Sequential Logic | ✅ Pass | Trace chain clean and traceable |
| 3 | Incremental Testing | ❌ Fail | 1 failing test shipped unnoticed (H2); gate-integration coverage absent |
| 4 | Zero Assumptions | ⚠️ Partial | Hardcoded fallbacks: payout 85.0 (`auto_ghost.py:873`), entry price 1.0 (868–872) |
| 5 | Code Integrity | ✅ Pass | No breaking changes detected in scoped modules |
| 6 | Separation of Concerns | ⚠️ Partial | `consider_signal` 310 lines (H4); snapshot builder doing producer+enricher duty |
| 7 | Stop Patching, Start Rewriting | ✅ Pass | Recent refactor (`_sync_extension_states`) moved the right direction; H3/H4 are the next rewrite candidates |
| 8 | Defensive & Explicit Error Handling | ❌ **Fail** | C1/C2 are silent fail-open gates — textbook violation. Required phrasing applies: *“This catch/guard path swallows the failure and will cause silent misbehavior in production. Must either fail closed loudly or propagate.”* |
| 9 | Fail Fast, Fail Loud, Fail Predictably | ⚠️ Partial | Store layer exemplary; pre-flight gate fails silent (C1/C2); H7 observability gap |

---

## 11. Risk Forecast (what breaks next if ignored)

1. **C1+C2 unremediated:** Every AI Pulse auto-execution trades with HTF-trend-only filtering and NO Bayesian floor and NO adverse-tick-flow veto. A manipulation spike or adverse micro-flow regime will execute at full size. Expect degraded win-rate and misleading post-mortem analytics (attribution distribution skewed because gates that should veto never do).
2. **C3 unremediated:** Under volatile bursts (exactly when signals cluster), concurrent `consider_signal` tasks exceed `max_concurrent_trades` — capital-risk cap violated in ghost mode today, and this code path is shared with future live execution.
3. **H2 unremediated:** Horizon contamination silently corrupts dual-horizon priors — the 51–56% calibration foundation erodes invisibly.
4. **H1 unremediated:** The trajectory engine's adaptive-horizon recommendations (its entire purpose) never fire; journal card shows permanent 0 premature expirations, creating false confidence in 60s expiry.
5. **M11 unremediated:** Users lose trust in pending setups that vanish or linger incorrectly.

---

## 12. Prioritized Action Plan

### 🔴 HIGH PRIORITY (block live reliance on AI Pulse auto-execution)
1. **[C1] Wire `recent_ticks` into the context snapshot** — @Coder: in `_get_asset_market_context_snapshot` (`streaming.py:726`), attach a bounded recent-tick slice per asset (e.g., last 300 ticks from `TickLogger.load_recent` cached in memory, or maintain a per-asset `deque(maxlen=600)` updated in `_process_tick_inner`). Add integration test asserting non-empty ticks reach `evaluate_directional_confluence`.
2. **[C2] Propagate Bayesian WP to the gate** — @Coder/@Architect: either (a) have `bayesian_signal_filter.on_consider_signal` results persisted into a per-asset latest-WP cache on `StreamingService` exposed via the snapshot, or (b) evaluate the Bayesian floor inside `execute_ai_pulse_signal` using the filter directly. Must fail CLOSED (skip trade + emit `ai_pulse_aborted`) when WP is unavailable and `bayesian_filter_enabled` is true.
3. **[C3] Close the capacity TOCTOU race** — @Coder: reserve capacity synchronously BEFORE the first await (add to `_active_assets` optimally before `execute_trade`, discard on failure), or serialize the check-and-reserve under a single-event-loop critical section. Apply the same pattern in `execute_ai_pulse_signal` (which already reserves early — align semantics).
4. **[H2] Fix horizon-isolation regression** — @Debugger root-cause, then @Coder: restore skip-on-missing-`expiration_seconds` in `on_trade_outcome`; keep the failing test green.

### 🟠 MEDIUM PRIORITY (next sprint)
5. **[H1] Make PREMATURE_EXPIRATION reachable** — @Coder: keep pulse trades registered for a post-settlement observation window (until 300s or next-trade eviction) so 120/180/300s checkpoints sample; add boundary tests.
6. **[H7] Emit `ai_pulse_aborted` from `execute_ai_pulse_signal` skip paths** — @Coder.
7. **[M1] Fix snapshot regime keys** (`confidence`→`regime_confidence`, `stable`→`regime_stable`) — @Coder, one-line + test.
8. **[M2] Reconcile T−15s doc vs T−5s implementation** — @Architect decision, then implement or amend docs.
9. **[H5] Replace per-tick numpy volatility with incremental Welford or candle-close computation** — @Optimizer/@Coder.
10. **[M11] Bind pending-card lifetime to terminal events, add `tabular-nums`** — @UI-Designer/@Frontend-Specialist.
11. **[M3/M4/L1/L4] Snap overshoot floor, scoped PUT wait regex, use-or-drop `tick_flow_300s`, hoist inline imports** — @Coder batch.

### 🟢 LOW PRIORITY (polish)
12. **[H3/H4] Declarative config spec table + `consider_signal` decomposition** — @Code_Simplifier/@Coder (recommend rewrite over patch per Core Principle #7).
13. **[M8] In-memory prior cache with mtime invalidation** — @Optimizer.
14. **[M14] Split `test_auto_ghost.py` into per-gate test modules; add proximity-rejection and wait≥2 e2e tests** — @Tester.
15. **[M9/M10] Trajectory input logging + `exit_price_unresolved` flag** — @Coder.
16. **[M5/M6] Replace hardcoded 85.0 payout fallback with explicit None-handling; add lock to `HTFDirectionalBiasEngine.get_instance()` for consistency** — @Coder.

---

## 13. Verified-OK Register (audited and found correct)

- Candle-open scheduling arithmetic and multi-minute wait math (`auto_ghost.py:943–947`)
- Reserved-token asset defense chain (`streaming.py:30–56` → `auto_ghost.py:836, 935`)
- `PulseTrajectoryEngine` thread safety (locked singleton, `_trade_lock`, `deque(maxlen=500)`)
- `BayesianPriorStore` transactional integrity (real OS-level sidecar lock, fsync atomic replace, Windows retry, fail-closed corruption, strict schema)
- Tick-queue backpressure with drop telemetry; signal-task semaphore bounding
- ProactorEventLoop exception handler correctly narrow-scoped (`streaming.py:290–302`)
- All Socket.IO emissions wrapped with logged failure handlers
- AI Pulse exponential backoff with success-reset (`streaming.py:751–770`)
- Direction-case normalization at every module boundary
- Frontend listener/interval lifecycle hygiene in `GhostTradingWidget.jsx`
- 72/73 automated tests passing

---

## 14. Sign-off

Per the Phase Review Protocol, this report is delivered by @Investigator for triage. Remediation handoff: **@Debugger** (H2 root cause) → **@Coder** (all fixes, priority order above), with **@Reviewer** phase-gate review after each remediation batch. No code was modified during this diagnostic.

*— End of Report —*