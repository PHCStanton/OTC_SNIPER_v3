# 👀 Pre-Level 3 Critical Review — 2026-04-11

**Reviewer**: @Reviewer  
**Scope**: Full-stack assessment of OTC SNIPER readiness for Level 3 implementation  
**Documents reviewed**: `OTEO_update_plan_26-03-30.md`, `Pre_Level3_Implementation_Summary_26-4-11.md`, `activeContext.md`, `progress.md`  
**Codebase files audited**: 15+ files across backend services, API, models, config, and frontend stores/hooks/components

---

## Executive Summary

The Level 2 foundation is **structurally sound and well-architected**. The codebase follows clean layered separation (OTEO Core → Market Context → Signal Policy), the toggle infrastructure for Level 3 is already wired end-to-end, and the domain model correctly supports strategy-level tagging. However, **one critical bug** and **several moderate concerns** must be addressed before Level 3 implementation begins.

---

## ✅ Strengths

| Area | Files | Assessment |
|------|-------|------------|
| **Architecture** | All services | Clean 4-layer design (Core → Context → Policy → AI). Each service has one clear responsibility. |
| **Level 2 Policy** | [market_context.py](file:///c:/v3/OTC_SNIPER/app/backend/services/market_context.py) | Fully formalized as `Level2PolicyConfig` frozen dataclass. All magic numbers extracted. |
| **Caching Strategy** | [market_context.py](file:///c:/v3/OTC_SNIPER/app/backend/services/market_context.py#L208) | Heavy indicators (ADX/CCI/Pivots) only recompute on closed candles (`_cached_context`). Proximity calculations happen per-tick as intended. |
| **Toggle Wiring** | [strategy.py](file:///c:/v3/OTC_SNIPER/app/backend/api/strategy.py), [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py#L57), [useSettingsStore.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/stores/useSettingsStore.js#L94-L95) | Level 3 toggle flows correctly: Settings UI → API → StreamingService. L3 auto-disables when L2 is off. |
| **Domain Model** | [domain.py](file:///c:/v3/OTC_SNIPER/app/backend/models/domain.py#L65), [requests.py](file:///c:/v3/OTC_SNIPER/app/backend/models/requests.py#L25) | `strategy_level`, `trigger_mode`, `entry_context`, and `manipulation_at_entry` fields ready for Level 3 metadata. |
| **Auto-Ghost Hardening** | [auto_ghost.py](file:///c:/v3/OTC_SNIPER/app/backend/services/auto_ghost.py) | Stale-asset cleanup, exception callbacks on async tasks, drawdown limits, session caps — all solid. |
| **Frontend Signal Model** | [useStreamConnection.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/hooks/useStreamConnection.js#L92-L113) | Rich signal object includes L2 metadata, market context, regime, manipulation — ready for L3 extension. |
| **Settings Validation** | [useSettingsStore.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/stores/useSettingsStore.js#L92-L152) | All inputs validated, clamped, and persisted through a single `validateSettings()` gate. |
| **Error Handling** | [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py#L96-L101) | Top-level try/except on `process_tick` prevents silent asyncio failures. |

---

## 🚨 Issues — Severity Rated

### CRITICAL

#### ISSUE-C1: `strategy_level` tagging is broken for Level 3

**File**: [auto_ghost.py:183](file:///c:/v3/OTC_SNIPER/app/backend/services/auto_ghost.py#L183)

```python
strategy_level="level3" if oteo_result.get("level3_enabled") else "level2" if oteo_result.get("level2_enabled") else "level1",
```

> [!CAUTION]
> The `oteo_result` dictionary returned by `apply_level2_policy()` **never contains a `level3_enabled` key**. The `level3_enabled` flag lives on `StreamingService.level3_enabled`, not in the enriched result dict. This means **all trades will be tagged as `"level2"` or `"level1"`, never `"level3"`**, even when Level 3 is active.

**Impact**: Every ghost trade session file and performance analysis will have incorrect `strategy_level`. When Level 3 is implemented, there will be no way to distinguish Level 3 trades from Level 2 — breaking the entire comparison pipeline.

**Fix**: Either inject `level3_enabled` into the enriched result in `_process_tick_inner()`, or pass the flag directly from the `StreamingService` to `AutoGhostService.consider_signal()`.

---

### MODERATE

#### ISSUE-M1: `reversal_friendly` computed but never used

**File**: [market_context.py:278](file:///c:/v3/OTC_SNIPER/app/backend/services/market_context.py#L278)

```python
"reversal_friendly": adx is not None and (adx < 28 or (adx_slope is not None and adx_slope < -0.5)),
```

> [!WARNING]
> This field is computed every time context is rebuilt, returned in the context dict, rendered in the frontend ([OTEORing.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/trading/OTEORing.jsx#L55)), but **`apply_level2_policy()` never references it**. It has zero policy impact.

**Recommendation**: Either integrate it into the Level 2 policy (e.g., as a confidence boost for reversal entries in reversal-friendly regimes) or explicitly document it as "reserved for Level 3 regime classification."

---

#### ISSUE-M2: Live trade outcome tracking has no exception callback

**File**: [trade_service.py:197](file:///c:/v3/OTC_SNIPER/app/backend/services/trade_service.py#L197)

```python
asyncio.create_task(self._track_trade_outcome(trade_record, adapter, request.expiration))
```

> [!WARNING]
> Unlike `auto_ghost.py:197` which adds `.add_done_callback(lambda t: ...)` to catch exceptions, the live trade tracking task has **no exception callback**. If `_track_trade_outcome` raises an unhandled exception, it will be silently swallowed by asyncio. This violates **CORE_PRINCIPLES #8** (Zero Silent Failures).

**Fix**: Add the same `done_callback` pattern from `auto_ghost.py`.

---

#### ISSUE-M3: `candle_closed = True` on first tick is semantically misleading

**File**: [market_context.py:196](file:///c:/v3/OTC_SNIPER/app/backend/services/market_context.py#L194-L196)

```python
if self._current_candle is None:
    self._current_candle = Candle(candle_start, price, price, price, price)
    candle_closed = True  # ← triggers full indicator recompute
```

> [!NOTE]
> Setting `candle_closed = True` when the very first candle is created causes a full ADX/CCI/pivot recomputation before any candle has actually completed. While harmless when `len(candles) < period`, it's semantically incorrect and could produce misleading early-session context values as candle count approaches thresholds. Consider setting `candle_closed = False` here and only triggering recomputation when a candle actually completes.

---

#### ISSUE-M4: Macro S/R fallback still uses absolute extremes (ISSUE-11)

**File**: [market_context.py:229-232](file:///c:/v3/OTC_SNIPER/app/backend/services/market_context.py#L229-L232)

```python
if macro_support is None and closed_candles:
    macro_support = min(candle.low for candle in closed_candles[-self.config.macro_lookback:])
if macro_resistance is None and closed_candles:
    macro_resistance = max(candle.high for candle in closed_candles[-self.config.macro_lookback:])
```

> [!WARNING]
> Already noted as ISSUE-11 (LOW severity). However, **Level 3 regime classification will likely depend heavily on S/R structure accuracy**. If Level 3 uses S/R distance to distinguish range-bound from trending regimes, this fallback could produce false regime labels. Recommend upgrading to percentile-based fallback (e.g., 10th/90th percentile) before Level 3 implementation.

---

### LOW

#### ISSUE-L1: No structured error handling in strategy API

**File**: [strategy.py](file:///c:/v3/OTC_SNIPER/app/backend/api/strategy.py#L34-L46)

The `update_runtime_config` endpoint has no try/except. If `update_runtime_settings` raises, it propagates as a raw 500 error. Should wrap in a try/except and return a structured JSON error per **CORE_PRINCIPLES #8**.

---

#### ISSUE-L2: Frontend signal model has no Level 3 fields

**File**: [useStreamConnection.js:108-113](file:///c:/v3/OTC_SNIPER/app/frontend/src/hooks/useStreamConnection.js#L108-L113)

The signal object captures `level2_enabled`, `level2_score_adjustment`, etc., but has no placeholder for Level 3 metadata (regime label, AI grade, L3 score adjustment). Will need extension when Level 3 processing is added.

---

#### ISSUE-L3: ManipulationDetector imports numpy for trivial operations

**File**: [manipulation.py](file:///c:/v3/OTC_SNIPER/app/backend/services/manipulation.py#L5)

`np.isfinite`, `np.mean` on a deque of floats. Could use `math.isfinite` and `sum()/len()` to eliminate the numpy dependency, keeping the module lighter per **CORE_PRINCIPLES #1** (Functional Simplicity First).

---

## 🔧 Optimization Recommendations

| # | Area | File | Suggestion |
|---|------|------|------------|
| O1 | ADX compute | [market_context.py](file:///c:/v3/OTC_SNIPER/app/backend/services/market_context.py#L85-L148) | `_compute_adx` iterates the full candle array on every closed-candle event. Refactor to use incremental Wilder smoothing that only updates with the newest closed candle. |
| O2 | Pivot scan | [market_context.py](file:///c:/v3/OTC_SNIPER/app/backend/services/market_context.py#L67-L82) | `_last_confirmed_pivot` scans from scratch on every call. Memoize last-known pivot levels and only re-scan when the lookback window changes. |
| O3 | CCI compute | [market_context.py](file:///c:/v3/OTC_SNIPER/app/backend/services/market_context.py#L155-L177) | Same full-recompute pattern as ADX. Could be made incremental. |
| O4 | Streaming payload | [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py#L121-L140) | Manual field-by-field copy from enriched_result into payload. Could use `payload.update(enriched_result)` directly if the result dict is already clean. |

> [!TIP]
> O1–O3 are performance optimizations that become increasingly important as multiple assets stream simultaneously (multi-chart mode). They don't block Level 3 but would reduce CPU load when Level 3 adds more computation on top.

---

## 📊 Level 3 Readiness Grid

| Component | Status | Notes |
|-----------|--------|-------|
| Backend toggle (`level3_enabled`) | ✅ Wired | API + StreamingService + frontend settings all connected |
| Strategy level tagging | ⚠️ **BUG** | See ISSUE-C1 — `oteo_result` never contains `level3_enabled` |
| Level 2 data inputs for regime | ✅ Available | ADX, CCI, S/R, ATR, DI, slopes — all computed and stable |
| `reversal_friendly` flag | ⚠️ Unused | Computed but has no policy effect — needs integration |
| AI service foundation | ✅ Ready | Provider-agnostic, advisory-only, image understanding works |
| Regime classifier module | ❌ Not started | New module needed (e.g., `regime_classifier.py`) |
| Multi-timeframe fusion | ❌ Not started | Currently 1m candles only |
| AI Review Loop | ❌ Not started | Background task with periodic snapshots |
| Advanced Signal Policy (L3) | ❌ Not started | Level 3 policy that uses regime labels |
| Frontend L3 visualization | ⚠️ Partial | Regime chip exists (ADX-based). Needs real regime labels. |

---

## 🎯 Pre-Implementation Checklist

Before starting Level 3 implementation, these items should be resolved:

- [ ] **Fix ISSUE-C1** — Inject `level3_enabled` into the signal pipeline so `strategy_level` is tagged correctly
- [ ] **Fix ISSUE-M2** — Add `done_callback` to live trade tracking tasks  
- [ ] **Decide on `reversal_friendly` (ISSUE-M1)** — Integrate into L2 policy or reserve for L3
- [ ] **Address ISSUE-M4** — Upgrade macro S/R fallback to percentile-based before L3 depends on it
- [ ] **Run a benchmark Auto-Ghost session** — Validate the tuned Level 2 policy with the hardened manipulation detector
- [ ] **Validate sparkline + live trade result wiring** — Still listed as open validation in progress.md

---

## CORE_PRINCIPLES Compliance Summary

| Principle | Status | Notes |
|-----------|--------|-------|
| #1 Functional Simplicity | ✅ | Architecture is clean. Minor numpy simplification opportunity. |
| #2 Sequential Logic | ✅ | Pipeline flows logically: tick → OTEO → context → policy → emit |
| #3 Incremental Testing | ⚠️ | Smoke tests exist but live runtime validation still has gaps |
| #4 Zero Assumptions | ✅ | Defensive null checks throughout. `np.isfinite` guards on price. |
| #5 Code Integrity | ✅ | No breaking changes detected. Backward compatible. |
| #6 Separation of Concerns | ✅ | Each service file has one purpose. Clean boundaries. |
| #7 Stop Patching | ✅ | No evidence of patch-on-patch patterns |
| #8 Defensive Error Handling | ⚠️ | ISSUE-M2 (live trade task), ISSUE-L1 (strategy API). Two gaps. |
| #9 Fail Fast | ⚠️ | Strategy API and trade service could benefit from earlier input validation |

---

**Overall Verdict**: The codebase is **structurally ready for Level 3 implementation** after the critical bug (ISSUE-C1) and moderate items are resolved. The architecture is clean, scalable, and adheres to the layered design principles outlined in the OTEO update plan. No rewrites are needed — only targeted fixes and extensions.
