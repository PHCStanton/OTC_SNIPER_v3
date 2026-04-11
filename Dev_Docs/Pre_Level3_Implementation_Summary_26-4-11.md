# Pre-Level 3 Implementation Summary — 2026-04-11

This document summarizes the current state, infrastructure, and requirements for the **Level 3 OTEO Implementation**, serving as a foundation for the upcoming transition from Level 2 (Market Context) to Level 3 (Advanced Regime Classification).

---

## 1. Goal & Definition

**Level 3** is defined as the "Advanced Phase" of the OTEO strategy. Its primary purpose is to move beyond static criteria (Level 1) and isolated market context (Level 2) into dynamic **Regime-Aware Trading**.

### Core Objectives:
- **Regime Classification**: Automatically detect the current market state (e.g., trend continuation, range-bound mean reversion, squeeze/compression, or high manipulation risk).
- **AI-Assisted Ranking**: Use AI as an advisory layer to rank setup quality and provide scheduled regime reviews.
- **Dynamic Policy Tuning**: Adjust OTEO thresholds and Level 2 filters based on the detected regime.

---

## 2. Current Implementation Status

As of 2026-04-11, the foundation for Level 3 is **pre-wired but logic-pending**.

### Infrastructure Already in Place:
- **Toggles**: The `oteo_level3_enabled` flag is functional in:
  - `app/backend/api/strategy.py` (exposed via `/api/strategy/runtime-config`)
  - `app/backend/services/streaming.py` (affects real-time signal processing)
- **Metadata**:
  - `TradeRecord` (Domain Model) includes `strategy_level: str | None`.
  - `TradeExecutionRequest` (Ghost/Live pipeline) correctly tags trades as `"level3"` if the toggle is enabled.
  - Logging in `app/data/live_trades/sessions/` already captures this metadata.
- **Market Context (Level 2 Prerequisite)**:
  - `market_context.py` is stable and provides S/R levels, ADX trend strength, and CCI alignment.
  - Level 2 is currently considered "stable and performant," providing the necessary data inputs for Level 3 logic.

---

## 3. Core Components to Build

The following modules represent the gap between Level 2 and Level 3:

| Component | Responsibility | Status |
|---|---|---|
| **Regime Classifier** | Logic to analyze Level 2 data (ADX, S/R, ATR) and assign a regime label (e.g., `REVERSAL_FRIENDLY` vs `TREND_FOLLOWER`). | **Planned** |
| **AI Review Loop** | Background task to send periodic snapshots (OTEO state + Context) to AI for advisory ranking and "caution" flags. | **Planned** |
| **Multi-Timeframe Fusion** | Logic to sync structure/regime across multiple candle frames (e.g., 1m, 5m). | **Planned** |
| **Advanced Signal Policy** | A Level 3-specific policy that uses regime labels to refine `actionable` status and `confidence`. | **Planned** |

---

## 4. Verification Strategy

The system is already configured to verify Level 3 trades using the same robust pipeline as Level 1 and 2:

- **Universal Verification**: All trade outcomes are tracked via `TradeService`.
- **Ghost Verification**: Compares `entry_price` vs `exit_price` from the `TickLogger` at expiration time.
- **Live Verification**: Queries the Pocket Option broker API for deterministic win/loss results.
- **Verification Logs**: Session `.jsonl` files are the source of truth for all strategy-level performance comparisons.

---

## 5. Reference Documents

For further design details, refer to:
- [OTEO Update Plan](file:///c:/v3/OTC_SNIPER/Dev_Docs/OTEO_update_plan_26-03-30.md) (Section 8)
- [Level 2 Implementation Plan](file:///c:/v3/OTC_SNIPER/Dev_Docs/Level2_Implementation_Plan_26-04-04.md) (Section 11, Phase E)
- [Active Context](file:///c:/v3/OTC_SNIPER/.agent-memory/activeContext.md) (Section 5)

---

**Summary Verified By:** AI Coding Assistant  
**Date:** 2026-04-11
