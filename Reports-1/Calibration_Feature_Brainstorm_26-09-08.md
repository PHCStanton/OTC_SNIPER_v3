# Calibration Feature & UI/UX — Brainstorm Round-Table (26-09-08)

> Produced by @Investigator (read-only survey) + brainstorm round-table from @Architect, @UI-Designer, @Researcher, @Optimizer, @Debugger/@Tester perspectives. Ideation only — no code changes. Handoff to @Coder/@Architect for any item the user approves.

---

## 1. Summary

The Calibration stack (Phases 0–5 + stability remediation + calibrated apply + session-first learning + AI Pulse intelligence injection) is functionally mature: a single-owner state machine, tiered autonomy, Guardian proposals, gate-family synthesis, asset profiling, Bayesian decoupling, and Layer-2 archival are all live. The highest-value remaining opportunities are **(a) statistical honesty** (confidence intervals instead of point estimates), **(b) evidence utilization** (the settled-trade corpus is richer than what surfaces), **(c) interactivity of Guardian proposals**, and **(d) post-apply efficacy tracking** (closing the loop: did the calibration actually help live trading?).

---

## 2. Current State Map (verified in code)

| Surface | File | State |
|---|---|---|
| State machine (IDLE→RUNNING→ANALYZING→PROPOSING→DONE/ABORTED), 409 lock, drain, watchdogs, budgets | `calibration_service.py` (1,243 lines) | ✅ Stable (BUG-1/2/3 closed) |
| Tier A/B autonomy, catastrophic rule (REV2), regime N≥20 guard | `calibration_autonomy.py` | ✅ Live; **ARCH-01 open** (empty `allowed_regimes` auto-apply hardening, `calibration_autonomy.py:120-130`) |
| Calibrated Apply Gates — 6 families + assets + Bayesian floor synthesis | `calibrated_apply.py` | ✅ Live (F-1 closed) |
| Live calibration status + budgets + calibratedGates card | `useCalibrationStore.js`, `CalibrationPanel.jsx` (536 lines) | ✅ Live |
| Calibrate tab + mini ribbon in Ghost Controller | `GhostTradingWidget.jsx` | ✅ Live |
| Session-first 3-layer WR engine, calibration isolation, Layer-2 archive | `session_tracker.py` | ✅ Live (76/76 tests) |
| AI Pulse calibration-intelligence prompt injection | `streaming.py::_render_calibration_context_section()` | ✅ Live |
| Multi-horizon Bayesian prior stores (60s/300s) | `bayesian_priors*.json` | ✅ Seeded (17,285 trades / 29 patterns) |
| Session Guardian (propose-only N≥20, warm-start divergence) | `calibration_autonomy.py` | ✅ Live — **propose-only, not interactive** |
| Discord NotificationSink | — | ❌ Deferred again (do not start without explicit command) |

---

### A. Calibration Engine & Statistics (@Architect / @Researcher)

| # | Idea | Value | Why now |
|---|---|---|---|
| A-1 | **Wilson confidence intervals on all WR displays.** Every win rate (panel StatBox, final report, prime/hazard asset profiling, KB warm-start) currently shows a bare point estimate. With N=24 a "58% WR" has a 95% CI of roughly ±20pp — meaningless precision. Render WR as `58% [37–77]` and color by CI width, not point estimate. | 🔼🔼🔼 | Prevents over-confident gate application from tiny samples. `CalibrationPanel.jsx:59-61` and `calibrated_apply.py` asset profiling (`≥60% WR` hard cutoffs on small per-asset N) are the exact risk spots. |
| A-2 | **Sequential early-stop / extend (SPRT-lite).** Instead of fixed 24-trades/25-min, if after N≥12 the evidence is already conclusive (WR CI excludes 50% by a wide margin), propose early finalize; if inconclusive at budget end, offer a one-click "extend 10 min / 12 trades" instead of auto-DONE. | 🔼🔼🔼 | Saves dead sessions; inconclusive calibrations currently still auto-finalize and synthesize gates from weak evidence. |
| A-3 | **Stratified coverage budget.** A run can settle 20 trades in TREND and 2 in RANGE, then the regime gate gets whitelisted from a 2-trade regime. Add coverage-aware budgets: soft per-regime/per-UTC-block targets, a live coverage matrix, and a finalize warning listing cells with N < 3. | 🔼🔼🔼 | Directly defends regime-family gates against sampling bias; cheap to compute from `_settled_trades` regime labels (already stored). |
| A-4 | **Calibration replay / what-if simulator (offline).** Pure function: replay the run's settled trades against candidate gate configs (current user gates, synthesized gates, presets) → "Under proposed gates, 11 of these 24 trades would have passed; projected WR 63% vs 50%." No live risk, no writes. Mount on the Apply card as a "Simulate" tab. | 🔼🔼🔼 | Biggest UX confidence booster: lets the user *see* what the gates would have done before applying. |
| A-5 | **Post-apply efficacy tracking (close the learning loop).** Tag live trades executed under applied calibrated gates (e.g. `entry_context: calibrated_apply:<calibration_id>`), then after N≥20 live trades report "Calibration efficacy": live WR under calibrated gates vs pre-calibration baseline. Surface as a drift card + auto-flag on decay. | 🔼🔼🔼 | Currently nothing proves the calibration *worked*. This is the missing feedback loop (lighter-weight than the deferred A3 ledger). |
| A-6 | **Scheduled recalibration advisor.** Use warm-start divergence (`guardian_prior_transfer`, `calibration_autonomy.py:213`) plus KB recency decay to passively recommend re-runs: "Last calibration 9 days ago; live WR drifted −7pp from KB warm-start → recalibration advised" (a badge, never auto-start). | 🔼🔼 | Guardians already compute the signal; it just needs a persistent surface instead of a one-shot notification. |
| A-7 | **Split-horizon calibration budgets.** One budget currently mixes 60s and 300s trades; the 300s store is freshly seeded and statistically young. Offer optional per-horizon budgets (e.g. 18×60s + 6×300s) so each prior store gets targeted evidence. | 🔼🔼 | Horizon isolation already exists end-to-end; this is budget arithmetic + a UI split. |
| A-8 | **Rollback stack for applied gates.** Every `tier_a_applied` and Apply-card action is last-write-wins with no undo. Keep a small in-memory stack and add a one-click "Revert to pre-calibration gates" — reuse the existing `config_snapshot` / `_restore_snapshot` machinery. | 🔼🔼 | Fail-safe UX on machinery that already exists. |

### Guardian interactivity (its own slice)

| # | Idea | Value |
|---|---|---|
| A-9 | **Guardian proposal inbox.** Guardian proposals are currently propose-only notifications (`guardian_proposal` in TopBar). Build an interactive inbox: each proposal card shows field, current → proposed value, rationale, evidence N, and Accept/Reject buttons dispatching `updateRuntimeStrategyConfig`. Rejected proposals are remembered for the run. | 🔼🔼🔼 |
| A-10 | **Gate-diff visualization on the Apply card.** Show current live gate value vs synthesized value side-by-side (`min_zscore: -1.2 → -0.8`) with change arrows, instead of only proposed values. Users currently cannot see what actually changes. | 🔼🔼 |

### B. Calibration UI/UX (@UI-Designer)

| # | Idea | Value | Notes |
|---|---|---|---|
| B-1 | **Milestone timeline strip.** A horizontal event timeline inside the Calibrate tab: start → milestone reviews → Tier A applied changes (dots, hover = field + rationale) → guardian proposals → drain → DONE. Turns the invisible internal state machine into a visible narrative. | 🔼🔼🔼 | Data already exists in the changelog/journal events; purely a rendering feature. |
| B-2 | **Coverage matrix heat grid.** 6 UTC blocks × regimes mini-heatmap with settled-trade counts per cell (green = covered, amber = thin N<3, gray = none). Replaces abstract budget meters with "what did I actually learn." | 🔼🔼 | Pairs with A-3. |
| B-3 | **CI-aware StatBox.** Upgrade the WR StatBox (`W x / y L`) to include the Wilson interval and a sample-size chip (`N=14 · CI ±18pp`) so the tone (emerald/rose) reflects *confidence*, not just direction. | 🔼🔼 | Tiny change, big honesty win. |
| B-4 | **Per-asset profiling tooltips / expandable detail.** Prime/Hazard badges exist; clicking a badge should open a mini table per asset: N, WR, PnL, avg manipulation, sample verdict (`Prime (weak N=3)`). `calibrated_apply.py` already returns `per_asset` — currently truncated to badge rows. | 🔼🔼 | |
| B-5 | **Projected-finish ETA.** Combine budgets into one line: `~18m 40s remaining · 24/24 trades · ETA 21:47 UTC`. The two meters currently force mental math. | 🔼 | |
| B-6 | **Post-run comparison card ("Before → After").** After Apply, show a compact diff of the protocol: which family changed, old vs new, and (with A-4) projected impact. Add "Undo" here (ties to A-8). | 🔼🔼 | |
| B-7 | **Calibration history browser.** DONE sessions are pruned to newest 20 on disk. Add a lightweight history list (id, date, duration, N, WR, PnL, gates-hash) with "Compare to current gates" and "Re-apply these gates" — persisted as a small JSON ledger independent of the 20-file pruning. | 🔼🔼 | |
| B-8 | **TTS milestone announcements (reuse Grok TTS).** Voice cues already exist for wins/losses; add optional spoken milestone summaries via the existing `/api/ai/speak` chain. | 🔼 | Low effort, fits existing audio UX. |
| B-9 | **Readability pass on the Calibrate tab.** `text-[7.5px]`/`text-[8px]` type is below comfortable reading for most users. Propose minimum 9–10px for primary data with `title` tooltips, and a density toggle (Compact / Comfortable) on the Ghost widget. | 🔼🔼 | Accessibility + user fatigue. |
| B-10 | **First-run guided calibration.** A 3-step coach-mark overlay on the Calibrate tab (what gets snapshotted → what happens during the run → what you get at the end). Shown once, dismissible. | 🔼 | |

---

### C. Overall UI/UX beyond Calibration (@UI-Designer)

| # | Idea | Value |
|---|---|---|
| C-1 | **Unified notification center with actions + filters.** TopBar dropdown now carries trade insights, `ai_pulse_aborted` rejections, guardian proposals, and guardian alignment — mixed streams with no filtering. Add filter chips (All / Guardian / Rejections / Insights), per-type grouping, and inline actions on guardian proposals (ties to A-9). | 🔼🔼🔼 |
| C-2 | **Global protocol-drift indicator.** A small TopBar chip showing whether current running gates match the most recent calibration ("⚡ Calibrated" vs "⚠ Drifted since 08-31"). One source of truth for "am I running what I tuned?" | 🔼🔼 |
| C-3 | **Command palette (Ctrl+K).** Fast actions: start/stop calibration, toggle Bayesian, apply calibrated gates, switch assets. The dense widget benefits from keyboard-first operation. | 🔼 |
| C-4 | **Journal ↔ Calibration cross-links.** In JournalView, calibration-archived sessions could link back to their Apply card and vice versa ("This session's gates came from calibration #abc123"). | 🔼 |
| C-5 | **Guardian audio identity.** Distinct soft chime for guardian proposals (currently only wins/losses/clicks have audio identity). | 🔼 |

---

### D. Robustness & Testing (@Tester / @Debugger)

| # | Idea | Value |
|---|---|---|
| D-1 | **Close ARCH-01 (tracked).** `enforce_milestone` empty-`allowed_regimes` auto-apply hardening at `calibration_autonomy.py:120-130` — defense-in-depth non-empty whitelist check. Owner @Architect + @Coder; regression test alongside F-1's `test_tier_a_empty_allowed_regimes_never_surfaced`. | 🔼🔼 |
| D-2 | **Property-based tests for autonomy enforcement.** Hypothesis-style fuzzing of `parse_autonomy_payload` + `enforce_milestone` with malformed/adversarial AI JSON (nested objects, wrong types, huge lists, injection strings). The AI-emitted surface is the least trustworthy input in the loop. | 🔼🔼 |
| D-3 | **Guardian-loop watchdog.** Time-budget watchdog exists; the `_guardian_loop` AI calls have no equivalent timeout wrapper (milestone review got `asyncio.wait_for(90s)` after BUG-3 — apply the same pattern to guardian AI calls). | 🔼🔼 |
| D-4 | **M14 debt (tracked): split `test_auto_ghost.py`.** Still deferred; do it opportunistically when touching `auto_ghost.py` next. | 🔼 |
| D-5 | **Calibration soak test.** A scripted mock-clock harness that runs a full virtual calibration (start → milestones → catastrophic REV2 path → drain → finalize → archival → AI Pulse context injection) to catch cross-phase regressions the unit suites cannot see. | 🔼 |

---

### E. Performance & Data (@Optimizer)

| # | Idea | Value |
|---|---|---|
| E-1 | **Incremental status payload.** `_emit_status` sends the full status every 5s; settled-trades-derived stats (per-regime, per-asset) can be computed once per settlement rather than per emit. | 🔼 |
| E-2 | **Final-report export.** One-click export of the final report + calibrated gates (JSON/CSV/Markdown) — pairs with B-7 history. | 🔼 |
| E-3 | **Prior-store freshness stamping.** The 300s store was seeded from mixed-vintage data; stamp each pattern bucket with a last-updated date so the AI Pulse context block can qualify stale evidence ("pattern last confirmed 2026-07-xx"). | 🔼 |

---

## 4. Prioritization (Impact × Effort)

| Priority | Items | Rationale |
|---|---|---|
| **P0 — do first** | A-1 (Wilson CI), A-4 (replay simulator), A-9 (Guardian inbox), A-5 (efficacy tracking) | Highest trust-building; closes the biggest loop gaps; all well-scoped. |
| **P1 — next** | A-2 (early-stop/extend), A-3 + B-2 (coverage), B-1 (timeline), B-6 (before→after + undo), C-1 (notification center), D-2 (fuzz tests), D-3 (guardian watchdog) | Solid incremental value, moderate effort. |
| **P2 — backlog** | A-6, A-7, A-8, A-10, B-3..B-10, C-2..C-5, D-1..D-5, E-1..E-3 | Polish, debt, and breadth. |

## 5. Explicitly Out of Scope (standing)
- Phase 6 Discord NotificationSink — deferred again by user (2026-08-31). Do not start.
- No master Bayesian prior file rewrites; session tracker remains read-only against the KB.
- A3 ledger remains out unless the user re-scopes it (A-5 above is deliberately a lighter-weight alternative).

## 6. Risk Forecast (if ideas are ignored)
- Regime/asset gates applied from thin samples (A-1/A-3) → false-confidence configs that underperform live, eroding trust in calibration.
- Guardian proposals buried in notifications → tuned improvements silently lost after every run.
- No efficacy loop (A-5) → no way to distinguish "calibration worked" from "market changed"; KB/prior stores age without a freshness signal.



