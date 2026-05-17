# Level 1, 2, 3 Optimization and AI Knowledge Base Plan

**File date:** 2026-05-16  
**Status:** Planned - Awaiting approval before implementation  
**Compiled by:** @Team-Leader with delegated findings from @Investigator, @Engineer, and @Reviewer  
**Scope:** Build an offline terminal analysis pipeline that improves Level 1, Level 2, and Level 3 decision quality first, then prepares a compact, low-cost knowledge base for future AI advisory retrieval.

---

## 1. Executive Summary

The immediate goal is not to let AI read raw logs directly. The immediate goal is to create a deterministic evidence layer that explains where current Level 1, Level 2, and Level 3 logic performs well, where it fails, and where manipulation-linked conditions are degrading outcomes.

This plan introduces a new offline analyzer that joins:
- `app/data/ghost_trades/sessions/*.jsonl` as the realized trade outcome ledger
- `app/data/signals/*.jsonl` as the signal-truth ledger
- `app/data/tick_logs/{asset}/{YYYY-MM-DD}.jsonl` as the replay and reconstruction source
- `Market_Analyzer/dev_docs/market_regime_analyzer.py` as a research regime comparator

The analyzer will output UTC-only optimization reports, manipulation diagnostics, Level 1/2/3 comparison matrices, and a compact knowledge base that a future AI layer can query without blowing up the context window or token cost.

---

## 2. Core Objectives

1. Improve Level 1, Level 2, and Level 3 signal quality using historical evidence before introducing any AI decision loop.
2. Quantify where manipulation-correlated setups hurt results so the manipulation detector and related filters can be refined.
3. Determine which assets, score bands, market conditions, and expiry windows are favorable or unfavorable.
4. Produce a compact historical knowledge base for future AI-assisted comparison of current conditions vs past conditions.
5. Keep runtime AI cost low by using retrieval from summarized patterns instead of sending raw logs or long histories to the model.

---

## 3. Non-Negotiable Constraints

- Use `UTC` only for all time grouping, storage, reporting, and future AI retrieval.
- Do not let AI directly consume raw tick logs at runtime.
- Keep the first implementation offline and deterministic.
- Treat production signal logs as the primary context source for manipulation and Level 3 fields.
- Treat ghost trades as the primary realized outcome source.
- Fail fast on missing joins, missing tick files, malformed rows, or ambiguous timestamp matches.
- Follow `.agents/PHASE_REVIEW_PROTOCOL.md` after each phase.

## 4. Source-of-Truth Architecture

### 4.1 Truth Sources

| Layer | Path | Role |
|---|---|---|
| Outcomes | `app/data/ghost_trades/sessions/*.jsonl` | Win/loss, payout, realized expiry, strategy level, entry and exit data |
| Signal truth | `app/data/signals/*.jsonl` | OTEO score, Level 2 and Level 3 adjustments, regime fields, market context, manipulation boolean |
| Replay input | `app/data/tick_logs/{asset}/{YYYY-MM-DD}.jsonl` | Tick-level reconstruction, candle building, regime comparison, time-window enrichment |
| Research regime | `Market_Analyzer/dev_docs/market_regime_analyzer.py` | Secondary offline market-condition comparator |
| Production regime | `app/backend/services/regime_classifier.py` | Runtime regime reference for Level 3 alignment |

### 4.2 Join Strategy

The analyzer must join rows in strict order of confidence:
1. Exact `asset` plus nearest timestamp within a small tolerance window.
2. If needed, compare `entry_context.timestamp`, top-level trade timestamps, direction, and score.
3. If multiple candidate signal rows still match, fail loudly and report the ambiguity.
4. If a required tick file for the corresponding asset/date is missing, fail loudly and report the exact file path.

### 4.3 Why This Architecture

`ghost_trades` alone are not enough for manipulation-first analysis because detailed manipulation evidence is sparse there. `signals` already capture the relevant runtime context in a more complete and cheaper-to-query shape. `tick_logs` should enrich and validate, not replace, the signal ledger.

---

## 5. Planned Deliverables

### 5.1 New Files

| File | Purpose |
|---|---|
| `scripts/analyze_trade_intelligence.py` | Offline terminal analyzer for Level 1/2/3 optimization and AI-ready summaries |
| `test_analyze_trade_intelligence.py` | Focused tests for schema validation, joins, UTC grouping, and aggregation logic |
| `Dev_Docs/L123_Optimization_and_AI_Knowledge_Base_Plan_26-05-16.md` | This implementation plan |

### 5.2 Output Artifacts

| Artifact | Suggested Location | Purpose |
|---|---|---|
| Raw joined CSV | `@reports/analysis/` | Inspect per-trade and per-signal merged evidence |
| Summary JSON | `@reports/analysis/` | Machine-readable aggregate stats for future AI retrieval |
| Markdown report | `@reports/analysis/` | Human-readable optimization and manipulation findings |
| Compact knowledge base JSON | `@reports/analysis/knowledge_base/` | Historical condition patterns for future AI advisory use |

### 5.3 Production Files Read Only

No production trading logic should be modified in the first analysis phase. These files remain dependencies and references only:
- `app/backend/services/streaming.py`
- `app/backend/services/auto_ghost.py`
- `app/backend/services/market_context.py`
- `app/backend/services/regime_classifier.py`
- `Market_Analyzer/dev_docs/market_regime_analyzer.py`

## 6. Implementation Phases

### Phase 1 - Analyzer Core and Join Validation

Deliverables:
- Parse `ghost_trades`, `signals`, and `tick_logs` with fail-fast schema validation.
- Build deterministic join logic for signal rows and realized trade rows.
- Normalize all timestamps to UTC.
- Emit a raw merged dataset and mismatch audit.

Acceptance criteria:
- Missing fields raise named, actionable errors.
- Ambiguous joins are counted and surfaced explicitly.
- Missing tick files are surfaced explicitly.
- Joined rows preserve `strategy_level`, OTEO score fields, direction, asset, and timestamps.

Review gate:
- `Phase 1 completed. Perform full incremental review.`

### Phase 2 - Manipulation-First Diagnostics

Deliverables:
- Add per-asset manipulation rate and manipulation-linked performance deltas.
- Compare win rate and expectancy for manipulation-present vs manipulation-absent contexts.
- Identify weak UTC windows and assets where manipulation materially degrades outcomes.
- Report where Level 1, Level 2, or Level 3 appear more vulnerable under manipulation-linked conditions.

Acceptance criteria:
- The report can rank assets by manipulation frequency and by manipulation damage.
- Small-sample warnings are applied to all manipulation summaries.
- The report never treats missing manipulation detail as manipulation evidence.

Review gate:
- `Phase 2 completed. Perform full incremental review.`

### Phase 3 - Level 1, 2, and 3 Optimization Matrices

Deliverables:
- Add best and worst asset tables.
- Add UTC hour-of-day and day-of-week tables.
- Add OTEO score-band tables.
- Add Level 1/2/3 comparison tables.
- Add regime x score-band x outcome summaries.

Acceptance criteria:
- All summaries are separated by strategy level where applicable.
- Score analysis uses stable buckets, not raw ungrouped floating values.
- The report includes expectancy and sample size, not win rate alone.

Review gate:
- `Phase 3 completed. Perform full incremental review.`

### Phase 4 - Dual-Regime Comparison

Deliverables:
- Preserve the production regime view from `regime_classifier.py`.
- Add an offline research regime view using `market_regime_analyzer.py`.
- Compare which regime labeling approach better explains wins, losses, and manipulative environments.

Acceptance criteria:
- Production and research regime labels are stored separately.
- The report never overwrites production labels with research labels.
- Differences between the two classifiers are visible in the output.

Review gate:
- `Phase 4 completed. Perform full incremental review.`

### Phase 5 - AI-Ready Knowledge Base Compression

Deliverables:
- Convert merged historical rows into compact condition-pattern summaries.
- Store favorable and unfavorable condition clusters with sample size, win rate, expectancy, and suppression or boost suggestions.
- Add nearest-pattern retrieval fields so a future AI layer can compare a current setup against past conditions cheaply.

Acceptance criteria:
- The knowledge base stores summarized patterns, not raw tick histories.
- The output is small enough to retrieve top relevant patterns only.
- The summary includes explicit confidence or reliability markers based on sample size.

Review gate:
- `Phase 5 completed. Perform full incremental review.`

### Phase 6 - AI Advisory Integration Contract

Deliverables:
- Define the payload contract the future AI layer will consume.
- Limit runtime AI context to the top matching historical patterns plus a concise current-condition summary.
- Keep AI advisory-only and outside all execution paths.

Acceptance criteria:
- No AI runtime path reads raw logs directly.
- AI context payloads remain compact and predictable.
- The contract supports future suggestions around threshold tuning, suppression rules, and expiry improvements.

Review gate:
- `Phase 6 completed. Perform full incremental review.`

---

## 7. Metrics and Knowledge Base Schema

Each summarized pattern should be able to capture at least:
- `asset`
- `utc_hour`
- `utc_weekday`
- `strategy_level`
- `direction`
- `oteo_score`
- `oteo_score_band`
- `base_oteo_score`
- `level2_score_adjustment`
- `level3_score_adjustment`
- `production_regime`
- `research_regime`
- `regime_confidence`
- `regime_stable`
- `manipulation_present`
- `market_context` key flags used by Level 2 and Level 3
- `expiration_seconds`
- `outcome`
- `payout_pct`
- `expectancy`
- `sample_size`

## 8. Verification Plan

Implementation verification should include at minimum:

```powershell
conda run -n QuFLX-v2 python -m py_compile scripts/analyze_trade_intelligence.py test_analyze_trade_intelligence.py
```

```powershell
conda run -n QuFLX-v2 python -m unittest test_analyze_trade_intelligence.py
```

```powershell
conda run -n QuFLX-v2 python scripts/analyze_trade_intelligence.py --sessions <session_ids> --signal-root app/data/signals --tick-root app/data/tick_logs --ghost-session-root app/data/ghost_trades/sessions --report-root @reports/analysis --utc-only
```

Manual verification:
- Inspect the mismatch audit for any timestamp-join drift.
- Confirm UTC grouping is correct in hourly and weekday tables.
- Confirm manipulation summaries only use valid signal-side evidence.
- Confirm Level 1/2/3 tables are separated cleanly.
- Confirm the compact knowledge base is materially smaller than the raw merged dataset.

---

## 9. Specialist Recommendations

### @Investigator
The highest-risk failure is building recommendations from incomplete joins or incomplete manipulation evidence. Join quality and evidence quality must be surfaced explicitly in every run.

### @Engineer
The most scalable path is to reuse the reporting pattern from `scripts/backtest_oteo_levels.py` while keeping this analyzer independent from production execution code.

### @Reviewer
The first version should remain read-only against production logic. Use the analyzer to identify changes to the manipulation detector and Level 1/2/3 thresholds before modifying live services.

---

## 10. Recommended Next Action

If this plan is approved, the next implementation step is:

`Phase 1 - Analyzer Core and Join Validation`

No production code changes should be bundled into that first phase. The initial phase should only build the offline analyzer, the join audit, and the raw evidence outputs.
