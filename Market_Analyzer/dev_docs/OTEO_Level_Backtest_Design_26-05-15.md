# OTEO Level Backtest Design — Multi-Expiry Analysis

**Version:** 1.0.0  
**Date:** 2026-05-15  
**Status:** Design proposal — not yet implemented  
**Scope:** Backtest the actual OTC SNIPER Level 1, Level 2, and Level 3 trading stack against historical tick data and ghost trade records, with a 7-way expiry sweep  
**Author:** @Investigator / @Architect synthesis

---

## 1. Executive Summary

The ghost-trade analysis for 2026-05-13 and 2026-05-14 revealed that Auto-Ghost is close to profitability but not quite there:
- 49.2% win rate on 2026-05-14, net -177.80 over 191 trades
- `STRONG_MOMENTUM` regime lost -240.40 (84 trades, 44% win rate)
- `MEDIUM` confidence dragged -247.60 (138 trades, 47.1% win rate)
- **High-scoring OTEO losses**: 23 trades with OTEO ≥ 90 still lost

These results raise fundamental questions:

1. **Expiry sensitivity** — Would shorter or longer expiries improve specific regimes?
2. **Level effectiveness** — How much does each layer (L1, L2, L3) actually help or hurt?
3. **Policy tuning** — Can stronger `STRONG_MOMENTUM` suppression or `MEDIUM`-confidence filtering fix the bleeding?
4. **Asset selectivity** — Which assets are systemically poor and should be excluded?

This document proposes a backtesting script that answers these questions by replaying **the actual production OTEO stack** across historical tick data.

---

## 2. Design Principles

| Principle | Rationale |
|---|---|
| **Test actual production code** | Not an external strategy library — replay `OTEO`, `MarketContextEngine`, `RegimeClassifier`, `apply_level2_policy`, `apply_level3_policy` directly |
| **Level separation** | Level 1, Level 2, and Level 3 must be testable independently |
| **Multi-expiry matrix** | Every signal evaluated at 15, 30, 60, 90, 120, 180, 300 seconds |
| **Ghost-reprice mode** | Take actual ghost trade entries from JSONL and re-score them at alternate expiries |
| **Deterministic analysis** | No AI in Phase 1 — deterministic rules only |
| **Export-first** | CSV + JSON + Markdown reports, not just console output |

---

## 3. Architecture Overview

### 3.1 Two Operational Modes

#### Mode A: `--mode replay`

Replay raw tick data through the full OTEO + Level 2 + Level 3 pipeline and generate new signals.

```
tick_logs/*.jsonl
    → OTEO.update_tick()                  # Level 1 raw signal
    → MarketContextEngine.update_tick()    # Level 2 market context
    → apply_level2_policy()               # Level 2 filtered
    → RegimeClassifier.classify()         # Level 3 regime
    → apply_level3_policy()               # Level 3 filtered
    → evaluate at all expiries
    → export CSV + JSON + Markdown
```

#### Mode B: `--mode ghost-reprice`

Load actual ghost trades from JSONL session files, keep the original entry price/direction, and re-score them at alternate expiries.

```
ghost_trades/sessions/*.jsonl
    → filter by --dates
    → match each ghost entry to its asset's tick file
    → keep original entry_time, direction
    → find exit_price at entry_time + expiry_seconds
    → evaluate win/loss at all 7 expiries
    → export CSV + JSON + Markdown
```

### 3.2 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    TICK DATA INPUT                      │
│  app/data/tick_logs/{asset}/{date}.jsonl                │
│  Format: {"t": <ts>, "p": <price>, "a": <asset>, ...}   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              OTEO ENGINE (Level 1)                       │
│  - update_tick(price, timestamp)                         │
│  - Returns: oteo_score, recommended, confidence,         │
│             velocity, pressure_pct, z_score, actionable   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           MARKET CONTEXT ENGINE (Level 2 data)           │
│  - update_tick(price, timestamp)                         │
│  - Returns: ADX, ATR, S/R, CCI, DI, tick_health, etc.   │
│  - Cached context; recomputes on candle close             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           LEVEL 2 POLICY (Level 2 filter)                │
│  - apply_level2_policy(oteo_result, market_context)      │
│  - Adjusts score based on S/R proximity, ADX regime,     │
│    CCI state, structure alignment                        │
│  - Can suppress or boost the signal                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           REGIME CLASSIFIER (Level 3 context)            │
│  - RegimeClassifier.classify(market_context)              │
│  - Called on candle close when context is ready           │
│  - Returns regime_label, regime_confidence, regime_stable │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           LEVEL 3 POLICY (Level 3 filter)                │
│  - apply_level3_policy(level2_result, mc, regime)        │
│  - Regime-based adjustments                              │
│  - Can suppress if regime is dangerous                    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              EXPIRY MATRIX EVALUATION                    │
│  For each signal at each level:                          │
│  - Record entry price, direction, timestamp              │
│  - Find exit_price at entry_time + 15, 30, 60, 90,      │
│    120, 180, 300 seconds                                 │
│  - Determine win/loss/missing                            │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              EXPORT & ANALYSIS                           │
│  - CSV: one row per (level × signal × expiry)            │
│  - JSON: summary matrices                                │
│  - Markdown: human-readable report with tables            │
│  - Console: quick summary during run                     │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Expiry Sweep Matrix

All signals are evaluated at these expiries:

| Expiry | Label | Rationale |
|---|---:|---|
| **15s** | Ultra-short | Catches immediate snap-back; low slippage risk |
| **30s** | Very short | Common OTC scalping window |
| **60s** | Baseline | Current Auto-Ghost default |
| **90s** | Short+ | Gives reversal more time to confirm |
| **120s** | 2-minute | Medium window for pullback/trend trades |
| **180s** | 3-minute | Longer reversal horizon |
| **300s** | 5-minute | Full candle formation; tests trend sustainability |

---

## 5. Report Structure

### 5.1 Console output during run

```
DATE_UTC 2026-05-14
ASSETS AUDCAD_otc EURCHF_otc ...
TOTAL_TICK_FILES 34 TOTAL_TICKS 1,847,291
PROCESSING_TIME 142.3s

LEVEL 1 SIGNALS: 312    WARMUP_SKIPPED: 58
LEVEL 2 SIGNALS: 289    SUPPRESSED: 23
LEVEL 3 SIGNALS: 267    BLOCKED: 22

=== LEVEL 3 × EXPIRY MATRIX ===
Expiry  Trades  Wins  Losses  Win_Rate  Net_P/L  Edge
15s     267     148   119     55.4%     +998.40  ✅
30s     267     141   126     52.8%     +349.80  ⚠️
60s     267     132   135     49.4%     -211.20  ❌
90s     267     129   138     48.3%     -371.40  ❌
...

=== BLOCKED SIGNAL POST-HOC ===
L3 blocked 22 signals.  If allowed:
  15s: 12 would have won, 10 lost — Filter helped slightly
  60s: 8 would have won, 14 lost — Filter helped

=== ASSET FLAGS ===
CADCHF_otc: 23 trades, 30.4% WR — BELOW BREAKEVEN — review
KESUSD_otc: 17 trades, 35.3% WR — BELOW BREAKEVEN — review
...
```

### 5.2 CSV columns

| Column | Description |
|---|---|
| `asset` | Asset symbol |
| `level` | L1 / L2 / L3 |
| `signal_index` | Sequential counter within file |
| `timestamp` | Entry timestamp (UTC) |
| `direction` | CALL or PUT |
| `entry_price` | Price at signal time |
| `oteo_score` | Raw OTEO score |
| `confidence` | L1/L2/L3 confidence |
| `regime` | Level 3 regime label (or null for L1/L2) |
| `regime_confidence` | Regime confidence |
| `expiry_seconds` | Expiry used for this row |
| `expiry_label` | 15s / 30s / 60s / 90s / 120s / 180s / 300s |
| `exit_price` | Price at entry_time + expiry |
| `outcome` | WIN / LOSS / MISSING_EXIT |
| `raw_profit` | Profit as if same payout applied |

### 5.3 JSON summary structure

```json
{
  "run_id": "20260515_143022",
  "date_utc": "2026-05-14",
  "assets": ["EURUSD_otc", "AUDCAD_otc"],
  "total_ticks": 1847291,
  "processing_seconds": 142.3,
  "levels": {
    "L1": {"total_signals": 312},
    "L2": {"total_signals": 289, "suppressed": 23},
    "L3": {"total_signals": 267, "blocked": 22}
  },
  "expiry_matrix": {
    "L3": {
      "15s":  {"trades": 267, "wins": 148, "losses": 119, "win_rate": 0.554, "net_pl": 998.40},
      "60s":  {"trades": 267, "wins": 132, "losses": 135, "win_rate": 0.494, "net_pl": -211.20}
    }
  },
  "regime_matrix": {
    "STRONG_MOMENTUM": {
      "15s": {"trades": 84, "win_rate": 0.44, "net_pl": -240.40}
    }
  },
  "asset_flags": [
    {"asset": "CADCHF_otc", "trades": 23, "win_rate": 0.304, "breakeven": 0.521, "verdict": "BELOW_BREAKEVEN"}
  ],
  "blocked_signal_audit": {
    "total_blocked": 22,
    "post_hoc_by_expiry": {
      "15s": {"would_have_won": 12, "would_have_lost": 10, "filter_helped": true}
    }
  }
}
```

---

## 6. Key Analysis Dimensions

### 6.1 Level × Expiry matrix

Shows which strategy layer performs best at which expiry.

### 6.2 Regime × Expiry matrix

Shows which regime prefers which expiry.

### 6.3 Confidence × Expiry matrix

Shows whether confidence levels are reliable across different expiries.

### 6.4 Asset × Expiry matrix

Shows which assets do better at long vs short expiries.

### 6.5 Blocked signal post-hoc audit

For every signal that Level 2 or Level 3 suppressed, the script evaluates whether suppression was helpful.

### 6.6 Ghost reprice mode

In Mode B, for each ghost trade, the script:

1. Loads the ghost entry from `auto_ghost_*.jsonl`
2. Extracts: `asset`, `entry_time`, `direction`, `entry_price`
3. Matches to the corresponding tick file: `tick_logs/{asset}/{date}.jsonl`
4. For each expiry: finds nearest tick at `entry_time + expiry`
5. Evaluates outcome
6. Reports the original 60s outcome alongside the alternate outcomes

---

## 7. Recommended Policy Variants

| Profile | Description |
|---|---|
| `baseline_current` | Current `Level3PolicyConfig` defaults |
| `strong_momentum_block` | Hard-block all counter-trend signals in STRONG_MOMENTUM |
| `stable_regime_only` | Require `regime_stable = True` for any boost |
| `structure_confirmed_only` | Require `nearest_structure_atr <= 0.5` for reversals |
| `high_confidence_only` | Block MEDIUM confidence entirely |
| `cci_extreme_only` | Only allow signals when CCI is oversold/overbought |
| `range_reversal_only` | Only trade RANGE_BOUND and TREND_REVERSAL regimes |

---

## 8. Breakeven Calculation

```python
breakeven_wr = 1 / (1 + payout_pct / 100)
```

| Payout | Breakeven Win Rate |
|---|---:|
| 88% | 53.2% |
| 89% | 52.9% |
| 90% | 52.6% |
| 91% | 52.4% |
| 92% | 52.1% |

---

## 9. Success Criteria

- [ ] Replay mode reads tick JSONL and runs actual OTEO + Level 2 + Level 3
- [ ] Expiry matrix results produced for all 7 expiries
- [ ] Ghost-reprice mode loads ghost trades and re-evaluates at alternate expiries
- [ ] CSV, JSON, and Markdown reports are exported
- [ ] Blocked signal audit is included
- [ ] Asset exclusion candidates are flagged automatically
- [ ] Tests pass
- [ ] A 2-day backtest completes in under 5 minutes

---

## 10. Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| Overfitting expiry choices to 2 days | False confidence | Validate against held-out days |
| Tick data gaps cause missing exits | Under-counted losses | Track `MISSING_EXIT` separately |
| Slow processing | Impatient iteration | Add progress bars |
| Stale market context caching | Wrong regime labels | Hard-reset engines per file |