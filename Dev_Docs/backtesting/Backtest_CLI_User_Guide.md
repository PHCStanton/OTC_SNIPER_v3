# OTEO Backtest CLI User Guide

**File:** `scripts/backtest_oteo_levels.py`  
**Primary output folder:** `@reports/backtests/`  
**Environment:** `QuFLX-v2`  
**Last updated:** 2026-05-15

---

## 1. Purpose

The OTEO Backtest CLI lets you replay historical OTC tick logs through the current production OTEO signal stack and evaluate whether specific assets, expiries, confidence bands, regimes, and OTEO levels are producing a real edge.

It supports two modes:

| Mode | Purpose | Best used for |
|---|---|---|
| `replay` | Replays historical tick logs through Level 1, Level 2, and Level 3 signal logic. | Finding which levels, assets, regimes, and expiries perform best. |
| `ghost-reprice` | Re-scores actual Auto-Ghost entries at alternate expiries. | Checking whether real Auto-Ghost entries would perform better at 15s, 30s, 60s, etc. |

The CLI produces three output files per run:

1. **CSV** — every scored signal/trade row.
2. **JSON summary** — structured totals and grouped performance metrics.
3. **Markdown analysis report** — human-readable performance matrices, suppression audit, and recommendations.

---

## 2. Required Terminal Pattern

Use PowerShell from the repository root:

```powershell
cd C:\v3\OTC_SNIPER
```

Run commands through the `QuFLX-v2` environment:

```powershell
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py --help
```

Do **not** run this from inside `app/`, `scripts/`, or another subfolder unless you also adjust paths manually.

---

## 3. Quick Start Commands

### 3.1 Replay historical tick logs

Use this when you want to replay raw tick data through Level 1, Level 2, and Level 3.

```powershell
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py `
  --mode replay `
  --dates 2026-05-13 2026-05-14 `
  --assets EURUSD_otc AUDCHF_otc `
  --expiry 15 30 60 90 120 180 300 `
  --tick-root app/data/tick_logs `
  --report-root @reports/backtests `
  --payout-pct 92 `
  --report-title "EURUSD + AUDCHF OTEO Replay Analysis"
```

Expected outputs:

```text
@reports/backtests/oteo_level_backtest_2026-05-13_2026-05-14_<timestamp>.csv
@reports/backtests/oteo_level_backtest_2026-05-13_2026-05-14_<timestamp>_summary.json
@reports/backtests/oteo_level_backtest_2026-05-13_2026-05-14_<timestamp>_analysis.md
```

---

### 3.2 Reprice actual Auto-Ghost trades

Use this when you want to check whether real Auto-Ghost entries would have performed better at different expiries.

```powershell
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py `
  --mode ghost-reprice `
  --sessions auto_ghost_1778794718 `
  --expiry 15 30 60 90 120 180 300 `
  --tick-root app/data/tick_logs `
  --ghost-session-root app/data/ghost_trades/sessions `
  --report-root @reports/backtests `
  --payout-pct 92 `
  --report-title "Auto-Ghost Session Expiry Reprice"
```

Expected outputs:

```text
@reports/backtests/oteo_ghost_reprice_auto_ghost_1778794718_<timestamp>.csv
@reports/backtests/oteo_ghost_reprice_auto_ghost_1778794718_<timestamp>_summary.json
@reports/backtests/oteo_ghost_reprice_auto_ghost_1778794718_<timestamp>_analysis.md
```

---

## 4. CLI Arguments

| Argument | Required? | Applies to | Example | Explanation |
|---|---:|---|---|---|
| `--mode` | Optional | Both | `--mode replay` | Selects `replay` or `ghost-reprice`. Defaults to `replay`. |
| `--dates` | Yes for replay | `replay` | `--dates 2026-05-13 2026-05-14` | Tick-log dates to replay. Each date expects files like `app/data/tick_logs/EURUSD_otc/2026-05-13.jsonl`. |
| `--assets` | Optional | `replay` | `--assets EURUSD_otc AUDCHF_otc` | Limits replay to selected assets. If omitted, the CLI scans all asset folders under `--tick-root`. |
| `--sessions` | Optional | `ghost-reprice` | `--sessions auto_ghost_1778794718` | Ghost session IDs or explicit `.jsonl` paths. If omitted, all ghost session files are repriced. |
| `--expiry` | Optional | Both | `--expiry 15 30 60 90 120 180 300` | Expiry seconds to test. Defaults to `15 30 60 90 120 180 300`. |
| `--tick-root` | Optional | Both | `--tick-root app/data/tick_logs` | Root folder for tick logs. Defaults to `app/data/tick_logs`. |
| `--ghost-session-root` | Optional | `ghost-reprice` | `--ghost-session-root app/data/ghost_trades/sessions` | Root folder for Auto-Ghost session JSONL files. |
| `--report-root` | Optional | Both | `--report-root @reports/backtests` | Folder where CSV, JSON, and Markdown reports are written. |
| `--payout-pct` | Optional | Both | `--payout-pct 92` | Broker payout percentage used for net P/L and breakeven calculations. |
| `--report-title` | Optional | Both | `--report-title "EURUSD Replay"` | Custom title shown at the top of the Markdown report. |

---

## 5. Input Data Requirements

### 5.1 Tick log format

Replay and ghost repricing both require tick logs under:

```text
app/data/tick_logs/<ASSET>/<YYYY-MM-DD>.jsonl
```

Example:

```text
app/data/tick_logs/EURUSD_otc/2026-05-13.jsonl
```

Each JSONL row must include:

```json
{"t": 1778794718.0, "p": 1.08421, "a": "EURUSD_otc"}
```

| Field | Meaning | Required? |
|---|---|---:|
| `t` | Unix timestamp in seconds | Yes |
| `p` | Price | Yes |
| `a` | Asset name | Yes |

Validation behavior:

- Missing `t`, `p`, or `a` raises `TickSchemaError`.
- Invalid JSON raises `TickSchemaError` with file and line number.
- Non-finite numbers (`NaN`, `Infinity`) are rejected.
- Rows are sorted by timestamp before replay.

---

### 5.2 Ghost session format

Ghost repricing reads Auto-Ghost sessions from:

```text
app/data/ghost_trades/sessions/*.jsonl
```

Required fields per trade:

| Field | Meaning | Required? |
|---|---|---:|
| `asset` | Asset traded | Yes |
| `direction` | `CALL` or `PUT` | Yes |
| `entry_time` | Actual entry timestamp | Yes |
| `entry_price` | Actual entry price | Yes |

Optional fields preserved in the output:

| Field | Meaning |
|---|---|
| `id` / `trade_id` | Trade identifier |
| `session_id` | Source Auto-Ghost session |
| `expiration_seconds` | Original expiry used live/simulated |
| `outcome` | Original recorded outcome |
| `exit_time` | Original exit timestamp |
| `exit_price` | Original exit price |
| `payout_pct` | Trade-specific payout percentage |
| `confidence` | Original confidence label |
| `oteo_score` | Original OTEO score |
| `strategy_level` | Strategy level used by Auto-Ghost |

Validation behavior:

- Missing required ghost fields raises `GhostTradeSchemaError`.
- Invalid directions raise `GhostTradeSchemaError`.
- Missing matching tick files raise `FileNotFoundError` loudly.

---

## 6. Understanding Output Files

### 6.1 CSV file

The CSV is the most detailed output. Each row represents one scored entry at one expiry.

Important columns:

| Column | Meaning | How to use it |
|---|---|---|
| `asset` | Asset being evaluated | Compare which assets consistently win or lose. |
| `level` | `L1`, `L2`, `L3`, or `GHOST_REPRICE` | Compare raw OTEO vs filtered Level 2/3 performance. |
| `entry_time` | Signal/trade entry timestamp | Trace exact entries back to tick logs. |
| `entry_price` | Price at entry | Used for expiry outcome scoring. |
| `direction` | `CALL` or `PUT` | Helps detect directional bias. |
| `expiry_seconds` | Tested expiry | Primary field for expiry optimization. |
| `exit_time` | Exit timestamp used for scoring | Confirms the expiry tick selected. |
| `exit_price` | Exit price used for scoring | Confirms price movement. |
| `price_delta` | Exit minus entry | Positive favors CALL, negative favors PUT. |
| `outcome` | `win`, `loss`, `draw`, `missing_exit`, or `insufficient_data` | Main result field. Do not treat `missing_exit` as a loss. |
| `net_pl` | Unit profit/loss based on payout | Used for ROI and edge assessment. |
| `payout_pct` | Payout assumption | Changes breakeven win-rate. |
| `oteo_score` | Final OTEO score after policy layer | Compare score bands to results. |
| `confidence` | Confidence label | Compare HIGH/MEDIUM/LOW buckets. |
| `level2_suppressed_reason` | Level 2 suppression reason | Shows why signals are being filtered. |
| `level3_suppressed_reason` | Level 3 suppression reason | Shows higher-level risk filters. |
| `adx_regime` | Market trend strength state | Useful for regime-specific tuning. |
| `trend_direction` | Market trend direction | Helps identify trend-aligned vs reversal behavior. |
| `cci_state` | CCI state such as overbought/oversold | Useful for exhaustion strategy analysis. |
| `tick_health` | Tick-flow health | Detects low/dead market issues. |
| `regime_label` | Level 3 market regime | Compare performance per regime. |
| `source_session` | Ghost session source | Used in `ghost-reprice` mode. |
| `original_expiration_seconds` | Original Auto-Ghost expiry | Compare original expiry vs alternate expiries. |
| `original_outcome` | Original Auto-Ghost outcome | Compare recorded result vs repriced outcomes. |

---

### 6.2 Summary JSON file

The JSON summary is structured for programmatic review or AI analysis.

Top-level shape:

```json
{
  "summary": {
    "overall": {},
    "by_level_expiry": {},
    "by_asset_expiry": {},
    "by_regime_expiry": {},
    "by_confidence_expiry": {}
  },
  "row_count": 1234
}
```

Use this file when you want exact grouped totals without asking an AI to parse CSV manually.

---

### 6.3 Markdown analysis report

The Markdown report is the best file for human review and AI review.

It contains:

1. Header and metadata.
2. Overall statistics.
3. Level × Expiry win-rate matrix.
4. Asset × Expiry win-rate matrix.
5. Regime × Expiry win-rate matrix.
6. Confidence × Expiry win-rate matrix.
7. Suppression audit.
8. Recommendations.

The `⚠️ n=X` label means the sample is smaller than `MIN_SAMPLE_SIZE = 30` settled trades. Treat those cells as directional hints only, not proof.

---

## 7. How to Use the Data to Improve Results

### 7.1 Compare Level 1 vs Level 2 vs Level 3

Use the **Level × Expiry Win-Rate Matrix**.

Questions to ask:

- Does Level 2 improve win-rate over raw Level 1?
- Does Level 3 improve win-rate further, or does it over-filter?
- Does one level perform better at short expiries while another performs better at longer expiries?

Action examples:

| Observation | Possible action |
|---|---|
| L1 wins more than L2/L3 | Filters may be too strict or incorrectly suppressing good entries. |
| L2 improves over L1 | Level 2 policy is adding value; keep tuning around its best expiry. |
| L3 improves over L2 | Regime filtering is valuable; prioritize Level 3 deployment. |
| L3 has too few trades | Level 3 may be over-filtering or needs more sample data. |

---

### 7.2 Optimize expiry selection

Use:

- `by_level_expiry`
- `by_asset_expiry`
- Markdown best/worst expiry recommendations
- Ghost reprice output

Do not choose an expiry from a small sample. Minimum recommended sample:

```text
30 settled trades per cell minimum
100+ settled trades preferred for production decisions
```

Action examples:

| Observation | Possible action |
|---|---|
| 15s has high win-rate but low sample | Collect more data before changing defaults. |
| 30s consistently beats 60s across assets | Consider making 30s the preferred Auto-Ghost expiry. |
| Ghost reprice shows original 60s losing but 15s winning | Auto-Ghost expiry may be too long for current signal timing. |
| Long expiries show many `missing_exit` rows | Tick logs may not extend far enough after entries; do not treat this as strategy failure. |

---

### 7.3 Identify weak assets

Use the **Asset × Expiry Win-Rate Matrix** and the recommendation section.

The report flags asset exclusion candidates when win-rate falls below:

```text
EXCLUSION_WIN_RATE_THRESHOLD = 45.0%
```

Action examples:

| Observation | Possible action |
|---|---|
| Asset is below 45% across all expiries | Consider excluding or reducing priority for that asset. |
| Asset performs well only at one expiry | Restrict that asset to its proven expiry. |
| Asset has good Level 1 but bad Level 3 | Regime filters may be misclassifying that asset's behavior. |
| Asset has many missing exits | Tick coverage may be incomplete; fix data before making decisions. |

---

### 7.4 Tune by market regime

Use the **Regime × Expiry Win-Rate Matrix**.

Questions to ask:

- Which regimes are profitable?
- Which regimes should be suppressed?
- Does expiry preference change by regime?

Action examples:

| Observation | Possible action |
|---|---|
| `RANGE_BOUND` performs best at 15s/30s | Prefer short expiries during range-bound exhaustion signals. |
| `STRONG_MOMENTUM` underperforms on reversal entries | Suppress countertrend reversal trades during strong momentum. |
| `CHOPPY` has low win-rate | Add stricter chop suppression or require higher confidence. |
| One regime has small sample | Do not tune yet; collect more live/ghost data. |

---

### 7.5 Tune by confidence band

Use the **Confidence × Expiry Win-Rate Matrix**.

Questions to ask:

- Is `HIGH` confidence actually outperforming `MEDIUM`?
- Are low-confidence trades worth taking at any expiry?
- Does confidence interact with expiry?

Action examples:

| Observation | Possible action |
|---|---|
| HIGH confidence performs best | Keep high-confidence threshold and prioritize those signals. |
| MEDIUM beats HIGH | Investigate whether scoring is overconfident in certain conditions. |
| LOW confidence is consistently losing | Suppress low-confidence entries. |
| Confidence performance changes by expiry | Use confidence-specific expiry rules. |

---

### 7.6 Audit suppression reasons

Use the **Suppression Audit**.

This section tells you which Level 2 and Level 3 filters are most often blocking trades.

Action examples:

| Observation | Possible action |
|---|---|
| One suppression reason dominates | Review whether that rule is too aggressive. |
| Suppression reason correlates with improved win-rate | Keep or strengthen that filter. |
| Suppressed trades would have won often | The filter may be blocking valid signals and needs tuning. |
| Dead/low market suppressions are frequent | Verify tick stream quality and market-session conditions. |

Important: the current CSV primarily records actionable rows. For deeper suppressed-signal analysis, preserve raw streaming logs and compare them with backtest rows.

---

## 8. How to Present Results to AI for Better Analysis

When asking an AI to analyze backtest results, do not only paste a screenshot or a single win-rate number. Provide structured context and the generated files.

### 8.1 Minimum AI review package

Provide these items together:

1. The exact CLI command used.
2. The generated `_analysis.md` content.
3. The generated `_summary.json` content.
4. The date range and assets tested.
5. The payout percentage.
6. Whether the run was `replay` or `ghost-reprice`.
7. Any operational goal, such as:
   - improve Auto-Ghost win-rate,
   - choose best expiry,
   - identify bad assets,
   - tune Level 2/Level 3 filters,
   - compare live session behavior.

---

### 8.2 AI prompt template — general strategy review

Use this prompt when you want the AI to recommend improvements:

```text
You are reviewing OTC_SNIPER OTEO backtest results.

Goal:
Improve Auto-Ghost / OTEO performance without overfitting.

Command used:
<paste exact CLI command>

Run type:
<replay or ghost-reprice>

Date range:
<dates>

Assets:
<assets or all assets>

Payout:
<payout percentage>

Analysis Markdown:
<paste generated _analysis.md>

Summary JSON:
<paste generated _summary.json>

Please analyze:
1. Which expiry has the strongest evidence-backed edge?
2. Which assets should be excluded, restricted, or prioritized?
3. Whether Level 2 and Level 3 improve over Level 1.
4. Which regimes and confidence bands are safe or unsafe.
5. Which conclusions are reliable vs small-sample only.
6. What exact next backtest should be run before changing production logic.
7. What production setting changes are justified now, if any.
```

---

### 8.3 AI prompt template — expiry optimization

Use this prompt when deciding whether to change Auto-Ghost expiry defaults:

```text
You are optimizing OTC_SNIPER Auto-Ghost expiry selection.

Only recommend an expiry change if the evidence is strong enough and not based on small samples.

Command used:
<paste exact CLI command>

Generated Markdown report:
<paste _analysis.md>

Summary JSON:
<paste _summary.json>

Please determine:
1. Best expiry overall.
2. Best expiry per asset.
3. Best expiry per regime.
4. Whether current original expiries underperform alternate expiries.
5. Which expiry recommendations need more data before implementation.
6. A conservative rollout plan for any expiry change.
```

---

### 8.4 AI prompt template — Level 2 / Level 3 filter tuning

Use this prompt when you want to tune policy filters:

```text
You are reviewing Level 2 and Level 3 OTEO filter performance.

Do not suggest code changes unless the data clearly supports them.
Separate high-confidence conclusions from hypotheses.

Command used:
<paste exact CLI command>

Analysis report:
<paste _analysis.md>

Summary JSON:
<paste _summary.json>

Please analyze:
1. Does Level 2 improve win-rate and ROI over Level 1?
2. Does Level 3 improve win-rate and ROI over Level 2?
3. Which suppression reasons appear most often?
4. Are any filters likely too strict?
5. Are any regimes unsafe enough to suppress?
6. What additional backtest should be run to confirm before implementation?
```

---

## 9. Recommended Backtesting Workflow

### Step 1 — Run broad replay

Run all available assets across several dates:

```powershell
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py `
  --mode replay `
  --dates 2026-05-13 2026-05-14 2026-05-15 `
  --expiry 15 30 60 90 120 180 300 `
  --report-title "Broad Multi-Asset OTEO Replay"
```

Goal: identify global best/worst levels, expiries, assets, and regimes.

---

### Step 2 — Run focused asset replay

Run only the strongest and weakest assets:

```powershell
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py `
  --mode replay `
  --dates 2026-05-13 2026-05-14 2026-05-15 `
  --assets EURUSD_otc AUDCHF_otc `
  --expiry 15 30 60 `
  --report-title "Focused Asset Replay"
```

Goal: confirm whether broad-run conclusions hold for specific assets.

---

### Step 3 — Reprice real Auto-Ghost sessions

```powershell
conda run -n QuFLX-v2 python scripts/backtest_oteo_levels.py `
  --mode ghost-reprice `
  --sessions auto_ghost_1778794718 `
  --expiry 15 30 60 90 120 180 300 `
  --report-title "Real Auto-Ghost Expiry Reprice"
```

Goal: determine whether actual entries were good but expiry selection was poor.

---

### Step 4 — Ask AI for evidence-ranked recommendations

Provide the Markdown report, JSON summary, and exact command to AI using the templates above.

Goal: turn raw results into cautious, evidence-ranked tuning recommendations.

---

### Step 5 — Validate on a new date range

Never change production logic based on one run only. Re-run on unseen dates.

Good validation pattern:

| Dataset | Purpose |
|---|---|
| Initial date range | Discover possible improvements. |
| Second date range | Confirm the improvement is repeatable. |
| Live/ghost session | Verify behavior in real runtime conditions. |

---

## 10. Decision Rules

Use these conservative rules before changing trading logic.

### Safe to consider changing a setting when:

- The relevant cell has at least `30` settled trades.
- Preferably the total supporting sample has `100+` settled trades.
- The win-rate is above breakeven for the configured payout.
- The same pattern appears across more than one date.
- The improvement appears in both Markdown matrix and JSON summary.
- Ghost reprice confirms the same expiry behavior for real entries.

### Do not change a setting when:

- The result is based on fewer than `30` settled trades.
- The edge appears on only one asset or one short date window.
- There are many `missing_exit` rows.
- Tick logs are incomplete or have gaps.
- The win-rate is above 50% but still below payout breakeven.
- The AI recommendation is based only on narrative, not the JSON/Markdown data.

---

## 11. Payout and Breakeven

The CLI uses payout percentage to calculate net P/L and breakeven win-rate.

Formula:

```text
breakeven win-rate = 100 / (1 + payout_pct / 100)
```

Examples:

| Payout | Breakeven win-rate |
|---:|---:|
| 92% | 52.08% |
| 90% | 52.63% |
| 85% | 54.05% |
| 80% | 55.56% |

Important: a 51% win-rate can still lose money when payout is below 100%.

---

## 12. Troubleshooting

### `--dates is required when --mode replay`

Replay mode needs at least one date:

```powershell
--dates 2026-05-13
```

---

### `No tick files found under ...`

The CLI could not find matching tick logs.

Check:

- Is the date correct?
- Is the asset folder name exact?
- Does the file exist under `app/data/tick_logs/<ASSET>/<DATE>.jsonl`?

---

### `Missing tick file for ghost trade ...`

Ghost repricing found a trade but no matching tick file for that trade's asset/date.

Fix by adding the required tick log:

```text
app/data/tick_logs/<trade_asset>/<trade_date>.jsonl
```

---

### `TickSchemaError`

The tick JSONL file has invalid structure.

Common causes:

- Missing `t`, `p`, or `a`.
- Invalid JSON on a line.
- Empty asset string.
- Non-numeric timestamp or price.

The error includes the exact file and line number.

---

### `GhostTradeSchemaError`

The ghost session file has invalid structure.

Common causes:

- Missing `asset`, `direction`, `entry_time`, or `entry_price`.
- Direction is not `CALL` or `PUT`.
- Entry timestamp or price is not numeric.

The error includes the exact file and line number.

---

## 13. Best Practice Summary

1. Start with `replay` mode to understand broad strategy behavior.
2. Use `ghost-reprice` mode to evaluate real Auto-Ghost entries.
3. Compare Level 1, Level 2, and Level 3 before tuning filters.
4. Do not trust cells marked `⚠️ n=X` as final proof.
5. Use payout-adjusted breakeven, not raw 50%, as the success threshold.
6. Present AI with the exact command, Markdown report, and JSON summary.
7. Validate any proposed improvement on a new date range before changing production settings.
8. Treat `missing_exit` as a data coverage issue, not an automatic strategy loss.
9. Prefer conservative changes that improve multiple assets/dates/regimes.
10. Keep all generated reports in `@reports/backtests/` for historical comparison.

---

## 14. Closure Note

This guide is intended to make the OTEO Backtest CLI usable by a human operator and easy to package for AI-assisted analysis. The safest workflow is always:

```text
Run backtest → review Markdown + JSON → ask AI with full context → validate on unseen data → only then tune production behavior.
```
