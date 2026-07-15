# OTC_SNIPER Patterns Roadmap — Extracting Actionable Intelligence from Historical Data
**Date:** 2026-07-12  
**Author:** @Researcher / @Team_Leader  
**Status:** Draft – Ready for Implementation  
**Goal:** Systematically extract high-value trading patterns from the rich dataset in `app/data/` (PO statements, ghost_trades, live_trades, signals, tick_logs) to improve gates, risk management, scheduling, and signal quality.

---

## 1. Executive Summary

We have five high-leverage pattern categories that can directly improve the Sniper engine. Each pattern will be extracted via dedicated analysis scripts and fed back into configurable gates, cooldowns, and schedules.

### Priority Order (Recommended)
1. **Hurst & Z-Score Sweet Spots** (Highest immediate impact on gates)
2. **Loss-Streak & Drawdown Analysis** (Risk management & circuit breakers)
3. **Asset-Specific Golden Hours** (Scheduling & asset whitelisting)
4. **Execution Latency & Slippage Impact** (Short-expiry viability)
5. **OTEO Score Decay (Signal Aging)** (Signal lifetime management)

---

## 2. Pattern 1 – Hurst & Z-Score Sweet Spots

**Objective:** Replace guessed thresholds with empirically optimal gating windows per asset.

**Data Sources:**  
- `ghost_trades` and `live_trades` (hurst_value, z_score, outcome)  
- `signals` (oteo_score at generation)

**Analysis Script:** `scripts/analyze_hurst_zscore_sweetspots.py`

**Outputs:**
- Per-asset optimal ranges (e.g., Hurst 0.28–0.38 + |Z| > 2.1 → 73% win rate)
- Recommended gate defaults for switchboard
- Heatmap visualization of win rate vs. Hurst × Z-Score

**Integration:**
- Feed optimal ranges into `HurstConfig` and `OTEOGateConfig`
- Add to Auto-Ghost consider_signal gates

---

## 3. Pattern 2 – Loss-Streak & Drawdown Probability

**Objective:** Build smart circuit breakers to prevent deep drawdowns.

**Data Sources:**  
- `ghost_trades` and `live_trades` (consecutive outcomes, session P&L)

**Analysis Script:** `scripts/analyze_streak_drawdown.py`

**Outputs:**
- Probability tables (P(3-loss streak), P(4-loss streak), etc.) per asset
- Recommended cooldown durations after n consecutive losses
- Drawdown distribution curves

**Integration:**
- Dynamic cooldowns in Auto-Ghost (`per_asset_cooldown_seconds` becomes adaptive)
- Session-level halt rules (`max_drawdown_amount` + streak-based pause)

---

## 4. Pattern 3 – Asset-Specific Golden Hours

**Objective:** Create targeted active-trading schedules per asset.

**Data Sources:**  
- `ghost_trades` / `live_trades` with UTC timestamps

**Analysis Script:** `scripts/analyze_golden_hours.py`

**Outputs:**
- Hourly win-rate heatmap per asset
- Recommended active windows (e.g., EUR/CHF 08:00–11:00 UTC)
- Whitelist/blacklist suggestions

**Integration:**
- Add `active_hours` config per asset in Ghost Protocol
- Auto-enable/disable assets based on current UTC time

---

## 5. Pattern 4 – Execution Latency & Slippage Impact

**Objective:** Quantify how broker delay affects short-expiry performance.

**Data Sources:**  
- `signals` (generation timestamp) + `ghost_trades` / `live_trades` (entry timestamp)

**Analysis Script:** `scripts/analyze_slippage_impact.py`

**Outputs:**
- Slippage distribution per asset and expiry
- Win-rate decay curves vs. delay (ms)
- Recommended minimum expiry per asset

**Integration:**
- Add slippage-aware veto or minimum expiry adjustment in execution path

---

## 6. Pattern 5 – OTEO Score Decay & Signal Aging

**Objective:** Determine maximum useful lifetime of a generated signal.

**Data Sources:**  
- `signals` vs. actual entry timestamps in trades

**Analysis Script:** `scripts/analyze_signal_aging.py`

**Outputs:**
- Win-rate vs. signal age (seconds) curves per asset/expiry
- Recommended maximum signal lifetime

**Integration:**
- Auto-cancel or ignore signals older than threshold

---

## 7. Implementation Roadmap

**Phase 1 (1–2 days)**  
- Implement `analyze_hurst_zscore_sweetspots.py` and `analyze_streak_drawdown.py`  
- Feed results into switchboard defaults

**Phase 2 (1 day)**  
- Implement `analyze_golden_hours.py` and integrate active-hours scheduling

**Phase 3 (1–2 days)**  
- Implement slippage and signal-aging analyses  
- Add dynamic gates based on findings

**Phase 4 (Ongoing)**  
- Integrate findings into AI Calibration loop (Grok reviews patterns and proposes gate updates)

---

## 8. Expected Impact

- More precise gates → higher win rates on filtered trades
- Smart cooldowns and scheduling → reduced drawdowns and better risk-adjusted returns
- Data-driven calibration → fewer manual guesses, faster iteration

This roadmap turns your historical data into a continuous improvement engine for the entire OTC_SNIPER platform.

---

**Next Step Recommendation**

Start with **Phase 1** (Hurst/Z-Score and Streak analysis) — these give the fastest, highest-impact wins.

Would you like me to begin drafting the first analysis script (`analyze_hurst_zscore_sweetspots.py`) now?

Let me know how you want to proceed.