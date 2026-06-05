# OTEO Level Backtest Plan — 2026-05-15

## Executive Summary

This plan adds a deterministic OTC_SNIPER backtester for replaying historical tick logs through the current production OTEO stack. The backtester is intentionally separate from `Market_Analyzer/dev_docs/backtest.py` because this utility must validate the live Level 1/2/3 signal path as implemented in `app/backend/services/`.

Current status:

- [x] **Phase 1 — Backtest core + tests**: implemented, verified, reviewed, and explicitly approved for continuation.
- [x] **Phase 2 — Ghost trade reprice mode**: implemented, verified, and reviewed (signed off 2026-05-15).
- [x] **Phase 3 — Markdown analysis report + recommendation matrices**: implemented, verified, reviewed (signed off 2026-05-15), and explicitly approved.
- [x] **Phase 4 — Final multi-agent review**: complete (signed off 2026-05-15).

## Architecture Context

The backtester must replay the actual production stack rather than duplicate strategy rules:

| Level | Production module | Backtest responsibility |
|---|---|---|
| Level 1 | `app/backend/services/oteo.py` | Call `OTEO.update_tick(price, timestamp)` and record raw actionable signals. |
| Level 2 | `app/backend/services/market_context.py` | Call `MarketContextEngine.update_tick()` and `apply_level2_policy(..., enabled=True)`. |
| Level 3 | `app/backend/services/regime_classifier.py` + `market_context.py` | Classify regime on closed ready candles, persist last regime, then call `apply_level3_policy()`. |
| Tick source | `app/data/tick_logs/{asset}/{YYYY-MM-DD}.jsonl` | Validate and sort ticks by timestamp before replay. |
| Reports | `@reports/backtests/` | Export raw CSV and summary JSON in Phase 1. |

## Current State Map

| File | Status | Notes |
|---|---|---|
| `scripts/backtest_oteo_levels.py` | Added in Phase 1 | CLI + replay core + CSV/JSON export. |
| `test_backtest_oteo_levels.py` | Added in Phase 1 | Deterministic unit coverage for schema validation, expiry outcomes, level separation, and summaries. |
| `app/data/ghost_trades/sessions/*.jsonl` | Read-only Phase 2 input | Actual Auto-Ghost trades used by `--mode ghost-reprice`. |
| `app/backend/services/oteo.py` | Read-only dependency | No production code changes. |
| `app/backend/services/market_context.py` | Read-only dependency | No production code changes. |
| `app/backend/services/regime_classifier.py` | Read-only dependency | No production code changes. |

## Implementation Phases

### Phase 1 — Backtest Core + Tests `[x]`

Deliverables:

- `scripts/backtest_oteo_levels.py`
- `test_backtest_oteo_levels.py`

Implemented behavior:

- Parses tick JSONL files with fail-fast validation for required fields: `t`, `p`, `a`.
- Sorts ticks by timestamp before replay.
- Replays Level 1, Level 2, and Level 3 independently.
- Uses expiry matrix defaults: `15, 30, 60, 90, 120, 180, 300` seconds.
- Evaluates CALL/PUT outcomes using nearest tick at or after `entry_time + expiry_seconds`.
- Separates `win`, `loss`, `draw`, `missing_exit`, and `insufficient_data` outcomes.
- Exports raw CSV and summary JSON to `@reports/backtests/`.

Verification already run:

```powershell
conda run -n QuFLX-v2 python -m unittest test_backtest_oteo_levels.py
```

```powershell
conda run -n QuFLX-v2 python -m py_compile scripts/backtest_oteo_levels.py test_backtest_oteo_levels.py
conda run -n QuFLX-v2 python -m unittest test_backtest_oteo_levels.py test_level3_phase1.py test_level3_phase2.py test_level3_phase3.py
```

Result: `23` tests passed.

Review gate:

> `"Phase 1 completed. Perform full incremental review."`

Status: ✅ Passed, then explicitly approved for Phase 2 continuation.

### Phase 2 — Ghost Trade Reprice Mode `[x]`

Deliverables:

- `scripts/backtest_oteo_levels.py`
- `test_backtest_oteo_levels.py`

Implemented behavior:

- Add `--mode ghost-reprice`.
- Load actual ghost trades from `app/data/ghost_trades/sessions/*.jsonl`.
- Match entries to tick files by asset/date.
- Keep real entry timestamp, direction, and price.
- Re-score alternate expiries: `15, 30, 60, 90, 120, 180, 300`.
- Fail loudly when a matching tick file is missing.
- Preserve original trade metadata for comparison: original expiration, original outcome, original exit time/price, source session, strategy level, confidence, OTEO score, and trade id.
- Export ghost reprice CSV + summary JSON to `@reports/backtests/` using the same summary contract as replay mode.
- Support direct script execution by adding the repository root to `sys.path` before importing backend modules.

Verification already run:

```powershell
conda run -n QuFLX-v2 python -m unittest test_backtest_oteo_levels.py
```

Result: `8` tests passed.

```powershell
conda run -n QuFLX-v2 python -m py_compile scripts/backtest_oteo_levels.py test_backtest_oteo_levels.py
conda run -n QuFLX-v2 python -m unittest test_backtest_oteo_levels.py test_level3_phase1.py test_level3_phase2.py test_level3_phase3.py
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py --mode ghost-reprice --sessions auto_ghost_1778794718 --expiry 15 30 60 --tick-root app/data/tick_logs --ghost-session-root app/data/ghost_trades/sessions --report-root @reports/backtests
```

Result: `26` tests passed, CLI generated:

```text
@reports/backtests/oteo_ghost_reprice_auto_ghost_1778794718_20260515T010328Z.csv
@reports/backtests/oteo_ghost_reprice_auto_ghost_1778794718_20260515T010328Z_summary.json
```

Review gate:

> `"Phase 2 completed. Perform full incremental review."`

Status: ✅ Passed (signed off 2026-05-15).

### Phase 3 — Analysis Report `[~]`

Deliverables:

- `scripts/backtest_oteo_levels.py`
- `test_backtest_oteo_levels.py`

Implemented behavior:

- Added `generate_markdown_report(rows, summary, ...)` — pure function, no side effects, fully testable.
- Added `_breakeven_win_rate(payout_pct)` — computes minimum win-rate needed to break even.
- Added `_matrix_table(grouped, ...)` — renders Level × Expiry, Asset × Expiry, Regime × Expiry, and Confidence × Expiry win-rate tables with ⚠️ small-sample warnings.
- Added `_suppression_audit(rows)` — counts Level 2 and Level 3 suppression reasons, sorted by frequency.
- Added `_recommendations(summary, ...)` — deterministic bullets for: overall edge vs breakeven, asset exclusion candidates (win-rate < 45%), small-sample asset warnings, and best/worst expiry ranking.
- Added `_write_markdown(content, path)` — writes Markdown to disk with parent directory creation.
- Wired `generate_markdown_report` into both `run_replay` and `run_ghost_reprice` — every CLI run now emits a `_analysis.md` alongside the existing CSV and JSON.
- Added `--report-title` CLI argument for optional custom Markdown report title.
- Added `MIN_SAMPLE_SIZE = 30` and `EXCLUSION_WIN_RATE_THRESHOLD = 45.0` as named constants.

Verification run:

```powershell
conda run -n QuFLX-v2 python -m py_compile scripts/backtest_oteo_levels.py test_backtest_oteo_levels.py
conda run -n QuFLX-v2 python -m unittest test_backtest_oteo_levels.py test_level3_phase1.py test_level3_phase2.py test_level3_phase3.py
```

Result: `39` tests passed (13 new Phase 3 tests + 26 existing).

Review gate:

> `"Phase 3 completed. Perform full incremental review."`

Status: ✅ Passed (signed off 2026-05-15). User approved Phase 4 continuation.

### Phase 4 — Final Review `[x]`

Behavior:

- Final validation: `39/39` tests passed. `py_compile` clean.
- Final multi-agent review delegated per `PHASE_REVIEW_PROTOCOL.md`.

#### Final Multi-Agent Verdicts

| Specialist | Verdict | Justification |
|---|---|---|
| @Reviewer | ✅ | All 3 plan phases fully implemented; all plan checklist items satisfied; CORE_PRINCIPLES alignment confirmed; 0 blocking issues across all 3 phases. |
| @Debugger | ✅ | No silent failure paths: schema errors raise named exceptions with file+line context; `missing_exit` is explicit and never counted as loss; `FileNotFoundError` is raised (not swallowed) for missing tick or session files; no empty catch blocks. |
| @Optimizer | ✅ | Tick cache (`tick_cache` dict) prevents repeated disk reads for the same file; `bisect_left` gives O(log n) expiry lookup; `generate_markdown_report` is a single-pass list-append builder — no redundant re-traversals. Low-severity: asset aggregation loop in `_recommendations` recomputes win-rate inline (avoids reading the stale dict field) — acceptable. |
| @Code_Simplifier | ✅ | Each helper has a single purpose and a single exit point; no cross-phase coupling; named constants replace all magic numbers; `_write_markdown`/`_write_csv`/`_write_json` are three-line pure writers. No simplification candidates rise to blocking level. |

Status: ✅ Passed (signed off 2026-05-15). Implementation Plan closed.

## CLI Contract

Phase 1 replay example:

```powershell
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py --mode replay --dates 2026-05-13 2026-05-14 --assets EURUSD_otc AUDCHF_otc --expiry 15 30 60 90 120 180 300
```

Output files:

```text
@reports/backtests/oteo_level_backtest_<dates>_<timestamp>.csv
@reports/backtests/oteo_level_backtest_<dates>_<timestamp>_summary.json
```

Phase 2 ghost reprice example:

```powershell
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py --mode ghost-reprice --sessions auto_ghost_1778794718 --expiry 15 30 60 90 120 180 300
```

Output files:

```text
@reports/backtests/oteo_ghost_reprice_<session-or-count>_<timestamp>.csv
@reports/backtests/oteo_ghost_reprice_<session-or-count>_<timestamp>_summary.json
@reports/backtests/oteo_ghost_reprice_<session-or-count>_<timestamp>_analysis.md
```

Phase 3 Markdown report is emitted automatically by both modes. Optional custom title:

```powershell
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py --mode replay --dates 2026-05-13 --assets EURUSD_otc --expiry 15 30 60 --report-title "EURUSD May 13 Analysis"
```

Output files (Phase 3 addition):

```text
@reports/backtests/oteo_level_backtest_<dates>_<timestamp>_analysis.md
```

## Verification Checklist

- [x] Tick schema validation fails fast for missing `t`, `p`, or `a`.
- [x] Expiry evaluator handles CALL win/loss and missing exits explicitly.
- [x] Replay emits separate Level 1, Level 2, and Level 3 rows.
- [x] Summary totals match raw rows.
- [x] New script and test compile in `QuFLX-v2`.
- [x] Existing Level 3 unit tests still pass.
- [x] Phase 1 review gate completed.
- [x] User explicitly approves moving to Phase 2.
- [x] Ghost trade schema validation fails fast for missing required entry fields.
- [x] Ghost reprice keeps actual entry timestamp, direction, and price.
- [x] Ghost reprice scores alternate expiries against matching tick files.
- [x] Ghost reprice fails loudly when the matching tick file is missing.
- [x] Direct `python scripts/backtest_oteo_levels.py --mode ghost-reprice ...` execution works.
- [x] Phase 2 review gate completed.
- [x] User explicitly approves moving to Phase 3.
- [x] `generate_markdown_report` emits all 8 required sections.
- [x] `_breakeven_win_rate` is correct at 92% and 80% payout.
- [x] `_matrix_table` renders ⚠️ small-sample warnings and em-dash for zero-settled cells.
- [x] `_suppression_audit` counts reasons correctly and sorts by frequency.
- [x] `_recommendations` flags insufficient sample, below-breakeven, exclusion candidates, and best/worst expiry.
- [x] Both `run_replay` and `run_ghost_reprice` emit `_analysis.md` alongside CSV and JSON.
- [x] `--report-title` CLI argument accepted and passed through.
- [x] Phase 3 review gate completed.
- [x] User explicitly approves moving to Phase 4.
- [x] Phase 4 final multi-agent review completed.
- [x] Implementation Plan closed (2026-05-15).

## Files Touched Summary

| File | Phase | Purpose |
|---|---|---|
| `scripts/backtest_oteo_levels.py` | 1 | Production-stack replay, expiry scoring, CSV/JSON export. |
| `test_backtest_oteo_levels.py` | 1 | Focused deterministic tests for Phase 1 behavior. |
| `Dev_Docs/backtesting/OTEO_Level_Backtest_Plan_26-05-15.md` | 1 | Plan status and verification tracking. |
| `scripts/backtest_oteo_levels.py` | 2 | Ghost session loading, reprice rows, ghost CLI mode, direct script import path. |
| `test_backtest_oteo_levels.py` | 2 | Focused tests for ghost schema validation, alternate expiry repricing, and missing tick failure. |
| `Dev_Docs/backtesting/OTEO_Level_Backtest_Plan_26-05-15.md` | 2 | Phase 2 status and verification tracking. |
| `scripts/backtest_oteo_levels.py` | 3 | `generate_markdown_report`, `_matrix_table`, `_suppression_audit`, `_recommendations`, `_breakeven_win_rate`, `_write_markdown`, `MIN_SAMPLE_SIZE`, `EXCLUSION_WIN_RATE_THRESHOLD`; wired into `run_replay` and `run_ghost_reprice`; `--report-title` CLI arg. |
| `test_backtest_oteo_levels.py` | 3 | `MarkdownReportTests` — 13 deterministic tests covering breakeven math, matrix rendering, suppression audit, recommendation logic, and full report structure. |
| `Dev_Docs/backtesting/OTEO_Level_Backtest_Plan_26-05-15.md` | 3 | Phase 3 status, CLI contract, verification checklist, and files touched. |

## Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| False conclusions from missing expiry ticks | HIGH | `missing_exit` is tracked separately and not counted as loss. |
| Strategy drift from duplicated logic | HIGH | Backtester imports production services directly. |
| Corrupt or partial tick JSONL files | MEDIUM | Tick loader validates schema and raises `TickSchemaError` with file/line. |
| Corrupt or partial ghost session JSONL files | MEDIUM | Ghost loader validates required entry fields and raises `GhostTradeSchemaError` with file/line. |
| Misleading ghost repricing from absent historical ticks | HIGH | Missing matching tick file raises `FileNotFoundError`; missing expiry tick remains explicit `missing_exit`. |
| Overfitting small samples | MEDIUM | Phase 3 added `MIN_SAMPLE_SIZE` labels (⚠️ n=X) in all matrices and deterministic recommendation guardrails. |
| Level 3 unavailable early in replay | LOW | Level 3 rows are only emitted after regime state exists, matching streaming behavior. |
