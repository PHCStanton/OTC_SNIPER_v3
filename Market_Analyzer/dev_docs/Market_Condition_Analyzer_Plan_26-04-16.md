# Market Condition Analyzer Plan
**Version**: 1.0.0  
**Date**: 2026-04-16  
**Scope**: Phase 1 only — standalone tick/session analyzer  
**Status**: Draft

## Executive Summary
We need a lightweight local analysis tool that can score market conditions from OTC tick session files before any AI call or trade execution is made. The goal is to identify favorable vs unfavorable conditions early, especially chop/whipsaw sessions where direction and expiry guesses fail frequently.

This plan intentionally covers **only Phase 1**: a standalone analyzer that reads tick JSONL session files, computes regime/quality metrics, and outputs a compact verdict for later review. Any alert-dispatch or AI-routing changes are explicitly deferred until this analyzer has been validated against several good and bad sessions.

## Architecture Context

### Why this tool is needed
- The collected `AUDCHF_otc_Tick_Snippet.jsonl` sample shows a session that is highly noisy and reversal-heavy.
- A single session can look tradable at the start and deteriorate within minutes.
- Sending full tick files to the AI is too expensive and too slow for routine screening.
- The analyzer must run locally, quickly, and predictably on session files without model calls.

### What the analyzer should answer
1. Is this session trending, ranging, or whipsawing?
2. Is the current market condition suitable for short-expiry OTC trades?
3. What are the key reasons for the score?
4. Should the session be skipped, watched, or considered tradable?

### Design principles
- **Fast-fail** on malformed input.
- **No AI dependency** in Phase 1.
- **Small output surface**: a single JSON result plus optional human-readable summary.
- **Reusable metrics**: the output should be simple enough to feed into later alert and AI routing work.
- **Conservative stance**: when the analyzer is uncertain, it should lean toward caution.

## Current State Map

| Area | Current State | Gap |
|---|---|---|
| Tick data collection | Tick JSONL session files already exist in `data/OTC_SNIPER_Ghost_Trader/` | No analysis layer over the sessions |
| Manual review | Possible but expensive and slow | No automated scoring or regime summary |
| AI ask flow | Can analyze context, but is too slow for session screening | No pre-filter to avoid low-quality sessions |
| Alert dispatch | Existing dispatcher can consume market signals | No standalone tradability gate before alerts |
| Historical validation | Session files can be replayed | No tool to compare multiple sessions consistently |

## Phase 1: Standalone Market Condition Analyzer

### Objective
Build a local analyzer that reads one tick JSONL session file at a time and returns a compact assessment of market quality.

### 1.1 Input contract
- **Input**: a `.jsonl` file containing tick records.
- Expected fields per line:
  - `t`: timestamp
  - `p`: price
  - `a`: asset symbol
  - `b`: source/broker tag
- The analyzer must:
  - ignore duplicate ticks safely,
  - validate required fields,
  - fail fast on malformed records,
  - tolerate minor session inconsistencies without crashing.

### 1.2 Output contract
The tool should return a structure like:

```json
{
  "asset": "AUDCHF_otc",
  "file": "data/OTC_SNIPER_Ghost_Trader/AUDCHF_otc_Tick_Snippet.jsonl",
  "sample_ticks": 1502,
  "duration_seconds": 735.56,
  "window_minutes": 15,
  "tradability_score": 27,
  "regime": "CHOP_WHIPSAW",
  "verdict": "AVOID",
  "flags": ["HIGH_REVERSAL_DENSITY", "LOW_DIRECTIONAL_EFFICIENCY"],
  "metrics": {
    "directional_efficiency": 0.48,
    "reversal_density": 34.2,
    "zero_move_ratio": 0.239,
    "realized_range_pips": 43.2,
    "net_move_pips": -5.0,
    "tick_volatility": 0.00013
  }
}
```

### 1.3 Core metrics
The first version should compute only metrics that are cheap, robust, and useful for regime detection:

1. **Directional efficiency**
   - `abs(net_move) / range`
   - Helps distinguish trend vs chop.

2. **Reversal density**
   - Count sign changes in tick-to-tick moves per minute.
   - High values indicate whipsaw behavior.

3. **Zero-move ratio**
   - Percentage of consecutive ticks with no price change.
   - Useful for dead or stagnant conditions.

4. **Realized range**
   - High-low range in pips over a window.
   - Measures how much the market actually moved.

5. **Net move**
   - End price minus start price in pips.
   - Helps distinguish clean trend from random drift.

6. **Tick volatility**
   - Standard deviation of tick-to-tick returns.
   - Useful as a baseline noise estimate.

7. **Session continuity checks**
   - Duplicate detection
   - Timestamp monotonicity
   - Gap detection

### 1.4 Scoring logic
Use a simple score model first, not a complex ML model.

#### Suggested regime bands
| Score | Regime | Action |
|---|---|---|
| 70–100 | Strong Trend | Favorable |
| 50–69 | Weak Trend | Caution |
| 30–49 | Range / Mixed | Only selective setups |
| 0–29 | Chop / Whipsaw | Avoid |

#### Suggested initial weighting
- Directional efficiency: high weight
- Reversal density: high negative weight
- Zero-move ratio: medium negative weight
- Range quality: medium weight
- Session continuity issues: penalty

The exact formula should be simple enough to tune by hand after testing on several session files.

### 1.5 Processing model
The analyzer should support:
- **Single-file mode**: analyze one session file and print a result.
- **Batch mode**: analyze multiple session files and compare scores.
- **Windowed mode**: compute rolling windows, ideally 5-minute and 15-minute views.

### 1.6 Proposed module layout
- `backend/analysis/market_condition_analyzer.py`
- `backend/analysis/__init__.py`
- `backend/tests/test_market_condition_analyzer.py`
- Optional CLI entrypoint:
  - `python -m backend.analysis.market_condition_analyzer <file.jsonl>`

### 1.7 Minimal code shape
```python
def analyze_tick_session(path: str, window_minutes: int = 15) -> dict:
    """Return a compact market condition assessment for one JSONL tick session."""

def load_ticks(path: str) -> list[dict]:
    """Validate and deduplicate raw tick records."""

def compute_metrics(ticks: list[dict], window_minutes: int) -> dict:
    """Calculate regime and quality metrics."""

def score_market(metrics: dict) -> dict:
    """Convert metrics into a tradability score and verdict."""
```

## Verification Checklist

- [ ] Confirm the analyzer correctly reads JSONL tick files.
- [ ] Confirm duplicate ticks are removed without breaking timestamps.
- [ ] Confirm malformed lines fail fast with a clear error.
- [ ] Confirm a single session file produces a compact JSON result.
- [ ] Confirm 5-minute and 15-minute windows can both be computed.
- [ ] Confirm a clearly choppy file scores lower than a cleaner trending file.
- [ ] Confirm the tool runs quickly enough for repeated local use.
- [ ] Confirm output is stable enough to support later alert-gating work.

## Files Touched Summary

### Planned new files
- `v2_Dev_Docs/Analysis_Tools/Market_Condition_Analyzer_Plan_26-04-16.md`
- `backend/analysis/market_condition_analyzer.py`
- `backend/analysis/__init__.py`
- `backend/tests/test_market_condition_analyzer.py`

### Explicitly not in scope for Phase 1
- Alert dispatcher changes
- AI model routing changes
- Dashboard widgets
- Automatic trade suppression logic

## Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| Overfitting to one bad session | Misleading score thresholds | Validate against multiple good/bad session files before trusting the score |
| Duplicate or malformed ticks | Broken metrics | Deduplicate and validate input before computation |
| Too many metrics too early | Hard-to-maintain code | Keep Phase 1 small and rule-based |
| False confidence from one window size | Wrong regime calls | Compare 5-minute and 15-minute windows before making decisions |
| Analyzer becomes too slow | Not useful in practice | Keep implementation local, vectorized, and AI-free |

## Validation Strategy for Deciding the Next Phase
Phase 2 and beyond should only be considered after Phase 1 is exercised on a small set of session files:
- at least one clear trend session,
- at least one clear chop/whipsaw session,
- at least one neutral or mixed session.

Only after that comparison should we decide whether to proceed with alert gating, AI routing changes, or dashboard integration.
