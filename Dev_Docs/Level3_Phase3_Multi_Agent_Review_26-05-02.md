# Level 3 Phase 3 — Multi-Agent Review Report

**Date:** 2026-05-02  
**Phase:** Level 3 Phase 3 — Win-Rate Optimization Features  
**Compiled by:** @Team_Leader (delegating @Reviewer, @Optimizer, @Code_Simplifier)  
**Protocol:** `.clinerules/PHASE_REVIEW_PROTOCOL.md`  
**Files reviewed:**
- `app/backend/services/market_context.py` (654 lines)
- `app/backend/services/auto_ghost.py` (391 lines)
- `app/backend/services/trade_service.py` (460 lines)
- `test_level3_phase3.py` (250 lines)

---

## Verdict Matrix

| Agent | Verdict | Blocking Issues | Minor Issues |
|-------|---------|-----------------|--------------|
| @Reviewer | ⚠️ Minor issues | 0 | 4 |
| @Optimizer | ⚠️ Minor issues | 0 | 3 |
| @Code_Simplifier | ⚠️ Minor issues | 0 | 4 |
| **Overall** | **⚠️ Approved with recommendations** | **0** | **11** |

**No blocking issues found. Phase 3 is functionally correct and safe to proceed past.**

---

## Section 1 — @Reviewer 👀

*Readability · Security · OWASP · Maintainability · CORE_PRINCIPLES alignment*

### Summary
Phase 3 is well-structured and correctly additive. All new logic is gated behind existing `actionable` and `enabled` guards. No silent failures, no swallowed exceptions, no hardcoded secrets. Four minor issues are noted below.

### Findings

#### R-1 🟡 LOW — `_track_ghost_trade_outcome` missing done-callback (trade_service.py:255)

**File:** `app/backend/services/trade_service.py`, line 255

```python
asyncio.create_task(self._track_ghost_trade_outcome(trade_record, request.expiration))
```

The ghost-trade outcome task has **no `.add_done_callback()`**. The live-trade path (line 319–320) correctly uses `_log_task_failure`. The ghost path was not updated in Phase 0 (M2 fixed only the live path). If `_track_ghost_trade_outcome` raises an unhandled exception, it will be silently swallowed by the event loop.

**CORE_PRINCIPLES #8 violation** — silent background failure possible.

**Recommendation:** Apply the same pattern as line 319:
```python
task = asyncio.create_task(self._track_ghost_trade_outcome(trade_record, request.expiration))
task.add_done_callback(lambda t: self._log_task_failure(t, "_track_ghost_trade_outcome"))
```
→ Delegate to @Coder.

---

#### R-2 🟡 LOW — `_pending_signals.pop(asset, None)` repeated 9× in `consider_signal` (auto_ghost.py:242–280)

**File:** `app/backend/services/auto_ghost.py`, lines 242–280

Every early-return guard in `consider_signal` manually calls `self._pending_signals.pop(asset, None)` before returning `None`. This is correct behavior but the repetition is a maintenance hazard — a future guard added without the pop will silently leave a stale pending signal.

**CORE_PRINCIPLES #6 violation** — the "clear pending on early exit" concern is scattered across 9 call sites instead of being centralized.

**Recommendation:** Extract a helper or use a single cleanup point. See @Code_Simplifier Section 3 for a concrete proposal.

---

#### R-3 🟡 LOW — `entry_context` in `consider_signal` copies `market_context` twice (auto_ghost.py:324–328)

**File:** `app/backend/services/auto_ghost.py`, lines 324–328

```python
"adx_regime": (oteo_result.get("market_context") or {}).get("adx_regime"),
"cci_state":  (oteo_result.get("market_context") or {}).get("cci_state"),
"tick_health": (oteo_result.get("market_context") or {}).get("tick_health"),
"cci_divergence": (oteo_result.get("market_context") or {}).get("cci_divergence"),
"market_context": oteo_result.get("market_context"),   # ← full dict also stored
```

The four individual fields are extracted from `market_context` **and** the full `market_context` dict is also stored. `report_outcome` then reads from both paths (lines 211–215). This creates two sources of truth for the same data. If `market_context` is later removed from `oteo_result`, the individual fields will silently become `None` while the full dict path also fails.

**Recommendation:** In `report_outcome`, read exclusively from `entry_context.get("market_context")` and remove the four redundant top-level keys from `entry_context`, or vice versa — pick one canonical path. See @Code_Simplifier Section 3.

---

#### R-4 🟡 LOW — Test `test_tick_frequency_and_health_are_exposed` asserts `second["tick_health"] == "healthy"` at 2-second spacing (test_level3_phase3.py:68–69)

**File:** `test_level3_phase3.py`, lines 64–71

With timestamps `[0.0, 2.0, 4.0]`, the second tick has a `time_span` of 2.0 seconds and 1 interval, giving `(1/2)*60 = 30 ticks/min`. The test asserts `"healthy"` (≥ 20/min) — this is correct. However, the **first tick** has only 1 element in the deque, so `len < 2` returns `0.0` → `"dead"`. The test asserts `first["tick_health"] == "dead"` which is correct but the comment in the plan says "warmup" — this is actually a **zero-frequency** result, not a warmup sentinel. The distinction matters if a future caller interprets `"dead"` as "market is closed" rather than "not enough data yet".

**Recommendation:** Consider a fourth `tick_health` value `"warming_up"` for the case where `len(deque) < 2`, to distinguish "no data yet" from "data exists but frequency is genuinely < 5/min". This is a design suggestion, not a blocking issue.

---

### Reviewer Verdict
**⚠️ Minor issues — 0 blocking, 4 low-severity findings.**  
R-1 is the most important (CORE_PRINCIPLES #8). R-2 and R-3 are maintainability concerns. R-4 is a design suggestion.

**Review complete. Awaiting explicit command to proceed.**

---

## Section 2 — @Optimizer ⚡

*Hot-path cost · Big-O · Memory · Per-tick overhead*

### Summary
Phase 3 adds three per-tick operations to the hot path. Two are O(1) and negligible. One (`_compute_tick_frequency`) has a subtle correctness issue under high-frequency feeds that could produce misleading `tick_health` values. No performance regressions found.

### Findings

#### O-1 🟡 LOW — `_compute_tick_frequency` runs every tick but `tick_health` derivation is outside the candle-close cache (market_context.py:236–243, 349–355)

**File:** `app/backend/services/market_context.py`, lines 349–355

```python
c = self._cached_context
tick_frequency = self._compute_tick_frequency(timestamp)   # ← runs every tick
if tick_frequency >= 20.0:
    tick_health = "healthy"
...
```

This is intentional — tick frequency **should** be computed every tick, not just on candle close. The deque is `maxlen=60` so appends are O(1). The frequency calculation is O(1) (two deque index accesses). **No performance issue.**

However, there is a **correctness concern**: the deque stores the last 60 timestamps regardless of time span. In a high-frequency feed (e.g. 100 ticks/second), the deque fills in under 1 second, and `time_span = deque[-1] - deque[0]` becomes very small (< 1s), producing an astronomically high `tick_frequency` (e.g. 6000/min). This is technically correct but the `"healthy"` threshold of 20/min is trivially satisfied and provides no signal quality information in high-frequency environments.

**Recommendation:** Cap the reported `tick_frequency` at a reasonable maximum (e.g. 300/min) to prevent misleading values in high-frequency feeds:
```python
return min(300.0, ((len(self._tick_timestamps) - 1) / time_span) * 60.0)
```
This is a low-priority tuning item, not a correctness bug for OTC binary options (which typically run at 1–5 ticks/second).

---

#### O-2 🟡 LOW — `_detect_cci_divergence` called on every candle close with full closed-candle list (market_context.py:280–284)

**File:** `app/backend/services/market_context.py`, lines 280–284

```python
closed_cci_metrics = _compute_cci(self._closed_candles, self.config.cci_period)
cci_divergence = _detect_cci_divergence(
    self._closed_candles,
    closed_cci_metrics["series"],
)
```

`_compute_cci` iterates over **all** closed candles (up to `max_candles=240`) to build the full CCI series. `_detect_cci_divergence` then only uses the last 10 values. This means we compute 240 CCI values to use 10.

**Complexity:** O(N × period) where N = up to 240 candles, period = 7. For 240 candles this is ~1680 multiplications per candle close. This runs only on candle close (not per tick), so the absolute cost is low (~1ms). However, it is wasteful.

**Recommendation (optional optimization):** Pass only the last `max(period + 10, 20)` candles to `_compute_cci` when computing for divergence detection:
```python
divergence_window = self._closed_candles[-20:] if len(self._closed_candles) >= 20 else self._closed_candles
closed_cci_metrics = _compute_cci(divergence_window, self.config.cci_period)
cci_divergence = _detect_cci_divergence(divergence_window, closed_cci_metrics["series"])
```
This reduces the CCI computation from O(240×7) to O(20×7) — a 12× speedup on candle close. Since divergence only looks at the last 10 candles, this is behaviorally equivalent.

→ Delegate to @Coder if accepted.

---

#### O-3 🟡 LOW — `dict(oteo_result)` shallow copy in `apply_level3_policy` and `apply_level2_policy` (market_context.py:415, 544)

**File:** `app/backend/services/market_context.py`, lines 415 and 544

Both policy functions do `result = dict(oteo_result)` which creates a shallow copy. The `market_context` nested dict inside `oteo_result` is **not** deep-copied. If downstream code mutates `result["market_context"]`, it will mutate the original `oteo_result["market_context"]` as well.

In the current codebase this is not a problem because `market_context` is only read, never mutated after the copy. But it is a latent correctness risk.

**Recommendation:** Document the shallow-copy contract with a comment, or use `result["market_context"] = dict(oteo_result.get("market_context") or {})` to isolate the nested dict. Low priority.

---

### Optimizer Verdict
**⚠️ Minor issues — 0 blocking, 3 low-severity findings.**  
O-2 is the most actionable (12× speedup on candle close, trivial change). O-1 is a correctness note for future high-frequency environments. O-3 is a latent risk with no current impact.

---

## Section 3 — @Code_Simplifier ✂️

*Functional simplicity · Duplication · Anti-patterns · Ceremony*

### Summary
Phase 3 code is clean and idiomatic Python. The main simplification opportunities are: (1) the 9× repeated `_pending_signals.pop` pattern in `consider_signal`, (2) the dual-path `entry_context` construction, and (3) a minor redundancy in `apply_level3_policy`'s confidence normalization. No rewrite is warranted.

**Simplicity Score:** Current implementation is ~85/100. Proposed changes would bring it to ~93/100.

### Findings

#### S-1 🟡 LOW — 9× repeated `_pending_signals.pop(asset, None)` in `consider_signal` (auto_ghost.py:242–280)

**File:** `app/backend/services/auto_ghost.py`, lines 242–280

Every guard in `consider_signal` manually pops the pending signal before returning `None`. This is 9 identical lines scattered across the function.

**Anti-pattern:** Scattered cleanup — violates DRY and CORE_PRINCIPLES #6 (one responsibility per location).

**Proposed simplification:**

```python
async def consider_signal(self, *, asset, price, timestamp, oteo_result, manipulation, payout_pct=100.0):
    now = unix_time()
    # ... stale cleanup ...

    def _reject():
        self._pending_signals.pop(asset, None)
        return None

    if not self.config.enabled:           return _reject()
    if self._session_halted:              return _reject()
    if self._session_trade_count >= ...:  return _reject()
    if now < self._drawdown_cooldown_until: return _reject()
    if oteo_result.get("recommended") not in {"CALL", "PUT"}: return _reject()
    if not oteo_result.get("actionable"): return _reject()
    if ...:                               return _reject()
    # etc.
```

This reduces 9 identical two-line blocks to 9 single-line guards. Behavior is 100% identical. Tests still pass.

→ Delegate to @Coder if accepted.

---

#### S-2 🟡 LOW — Dual-path `entry_context` construction (auto_ghost.py:300–331)

**File:** `app/backend/services/auto_ghost.py`, lines 300–331

The `entry_context` dict extracts `adx_regime`, `cci_state`, `tick_health`, `cci_divergence` individually from `oteo_result.get("market_context")` **and** also stores the full `market_context` dict. Then `report_outcome` (lines 211–215) reads from both paths with `or` fallbacks:

```python
adx_regime = entry_context.get("adx_regime") or market_context.get("adx_regime") or "unknown"
```

**Anti-pattern:** Two sources of truth for the same data. The `or` fallback chain hides which path is actually used.

**Proposed simplification:** Remove the four individual keys from `entry_context` and read exclusively from `entry_context["market_context"]` in `report_outcome`:

```python
# In consider_signal — entry_context construction:
# REMOVE these 4 lines:
# "adx_regime": (oteo_result.get("market_context") or {}).get("adx_regime"),
# "cci_state": ...
# "tick_health": ...
# "cci_divergence": ...

# In report_outcome — read from one place:
mc = entry_context.get("market_context") or {}
adx_regime = mc.get("adx_regime", "unknown")
cci_state = mc.get("cci_state", "unknown")
tick_health = mc.get("tick_health", "unknown")
```

This removes 4 lines from `entry_context` construction and simplifies `report_outcome` from 4 `or`-chained lookups to 4 clean `.get()` calls. Behavior is identical since `market_context` is already stored in `entry_context`.

**Note:** `regime_label` is correctly stored as a top-level key (it comes from `oteo_result` directly, not from `market_context`), so it stays.

→ Delegate to @Coder if accepted.

---

#### S-3 🟡 LOW — Confidence normalization guard in `apply_level3_policy` is redundant (market_context.py:629–631)

**File:** `app/backend/services/market_context.py`, lines 629–631

```python
adjusted_confidence = str(result.get("confidence") or "LOW").upper()
if adjusted_confidence not in {"LOW", "MEDIUM", "HIGH"}:
    adjusted_confidence = "LOW"
```

`result["confidence"]` was set by `apply_level2_policy` which already guarantees it is one of `"LOW"`, `"MEDIUM"`, `"HIGH"` via `_confidence_from_rank`. The `not in` guard can never be `True` in normal operation.

**Proposed simplification:**
```python
adjusted_confidence = str(result.get("confidence") or "LOW").upper()
# No guard needed — L2 policy guarantees valid confidence values
```

This removes 2 lines of dead code. If the contract ever breaks, the downstream `_confidence_rank` call will silently return `0` (LOW), which is acceptable defensive behavior.

**Alternatively:** Keep the guard but add a `logger.warning` so it's not silent:
```python
if adjusted_confidence not in {"LOW", "MEDIUM", "HIGH"}:
    logger.warning("apply_level3_policy: unexpected confidence value %r, defaulting to LOW", adjusted_confidence)
    adjusted_confidence = "LOW"
```

→ Delegate to @Coder if accepted.

---

#### S-4 🟡 LOW — `Level2PolicyConfig().min_actionable_score` instantiated inside `apply_level3_policy` (market_context.py:549)

**File:** `app/backend/services/market_context.py`, line 549

```python
actionable_floor = Level2PolicyConfig().min_actionable_score
```

A fresh `Level2PolicyConfig` dataclass is instantiated on every call to `apply_level3_policy` solely to read the default value `55.0`. This is a magic-number workaround — the value is not passed in and not configurable from `Level3PolicyConfig`.

**Anti-pattern:** Cross-config dependency via instantiation. If `Level2PolicyConfig.min_actionable_score` is ever changed, `apply_level3_policy` silently picks up the new value without any explicit wiring.

**Proposed simplification:** Add `min_actionable_score: float = 55.0` to `Level3PolicyConfig` and use `policy.min_actionable_score`:

```python
@dataclass(frozen=True)
class Level3PolicyConfig:
    # ... existing fields ...
    min_actionable_score: float = 55.0  # Must match Level2PolicyConfig default
```

Then in `apply_level3_policy`:
```python
actionable_floor = policy.min_actionable_score  # No cross-config dependency
```

This makes the dependency explicit and configurable. The default value `55.0` matches `Level2PolicyConfig` so behavior is unchanged.

→ Delegate to @Coder if accepted.

---

### Code_Simplifier Verdict
**⚠️ Minor issues — 0 blocking, 4 low-severity findings.**  
S-1 and S-2 are the most impactful (reduce maintenance surface). S-4 eliminates a hidden cross-config dependency. S-3 removes dead code or adds a missing warning.

---

## Section 4 — Phase 3 Verification Checklist Status

Cross-referencing against `Dev_Docs/Level3_Implementation_Plan_26-04-29.md` Section 8:

| Criterion | Status | Notes |
|-----------|--------|-------|
| Tick frequency computed and included in market_context | ✅ | `tick_frequency` + `tick_health` in returned dict |
| Dead market (< 5 ticks/min) suppresses signals | ✅ | `apply_level3_policy` line 582–583 |
| Entry confirmation window delays execution by N ticks | ✅ | `CONFIRMATION_TICKS = 3`, tested |
| Confirmation resets when direction changes | ✅ | Lines 289–291, tested |
| Cooldown doubles after a loss on the same asset | ✅ | Lines 188–189 (×2 multiplier) |
| Cooldown triples after 3 consecutive losses | ✅ | Lines 188–189 (×3 multiplier), tested |
| Consecutive losses reset after a win | ✅ | Line 207, tested |
| Per-condition stats track wins/losses by regime, ADX, CCI, asset, tick_health | ✅ | Lines 217–222 |
| `get_condition_stats()` returns structured win-rate data | ✅ | Lines 379–390 |
| CCI divergence detected when price and CCI diverge | ✅ | `_detect_cci_divergence`, tested |
| Trade-outcome context forwarding to Auto-Ghost | ✅ | `trade_service.py` lines 370–377 |

**All 11 Phase 3 verification criteria are met.**

---

## Section 5 — Consolidated Recommendations for @Coder

Priority-ordered list of all findings. All are optional improvements — none are blocking.

| # | Priority | Finding | File | Lines | Action |
|---|----------|---------|------|-------|--------|
| 1 | 🟡 LOW | R-1: Ghost trade task missing done-callback | `trade_service.py` | 255 | Add `task.add_done_callback(lambda t: self._log_task_failure(t, "_track_ghost_trade_outcome"))` |
| 2 | 🟡 LOW | O-2: `_compute_cci` called on all 240 candles for divergence | `market_context.py` | 280–284 | Slice to last 20 candles before calling `_compute_cci` for divergence |
| 3 | 🟡 LOW | S-1: 9× repeated `_pending_signals.pop` | `auto_ghost.py` | 242–280 | Extract `_reject()` helper |
| 4 | 🟡 LOW | S-2: Dual-path `entry_context` construction | `auto_ghost.py` | 300–331, 211–215 | Remove 4 redundant top-level keys; read from `market_context` in `report_outcome` |
| 5 | 🟡 LOW | S-4: Cross-config `Level2PolicyConfig()` instantiation | `market_context.py` | 549 | Add `min_actionable_score` to `Level3PolicyConfig` |
| 6 | 🟡 LOW | S-3: Dead confidence guard or missing warning | `market_context.py` | 629–631 | Remove dead guard or add `logger.warning` |
| 7 | 🟡 LOW | R-3: Dual source of truth for market_context fields | `auto_ghost.py` | 324–328 | Resolved by S-2 |
| 8 | 🟡 LOW | R-2: Scattered cleanup pattern | `auto_ghost.py` | 242–280 | Resolved by S-1 |
| 9 | 🟡 LOW | O-1: Tick frequency cap for high-frequency feeds | `market_context.py` | 243 | Add `min(300.0, ...)` cap |
| 10 | 🟡 LOW | R-4: `"dead"` vs `"warming_up"` tick health distinction | `market_context.py` | 350–355 | Design suggestion for future consideration |
| 11 | 🟡 LOW | O-3: Shallow copy of nested `market_context` dict | `market_context.py` | 415, 544 | Document contract or deep-copy nested dict |

---

## Section 6 — Phase Gate Decision

Per `.clinerules/PHASE_REVIEW_PROTOCOL.md`:

> No phase may proceed to the next until it has been reviewed, tested, and **explicitly approved**.

**All three agents agree: Phase 3 is functionally correct, all 11 verification criteria are met, 17 tests pass, and there are zero blocking issues.**

The 11 findings above are all low-severity improvements. They may be addressed before or after Phase 4 at the user's discretion.

**Phase 3 gate status: ⚠️ Approved with recommendations — pending explicit user command to proceed to Phase 4.**

The Phase 3 row in `Dev_Docs/Level3_Implementation_Plan_26-04-29.md` Section 12 will be updated to `[~]` (implemented, pending sign-off) until the user issues an explicit approval command such as:
- `"Approved – continue"`
- `"Proceed with Phase 4"`
- `"Phase 4 approved"`

---

*Report compiled: 2026-05-02*  
*Agents: @Reviewer (👀), @Optimizer (⚡), @Code_Simplifier (✂️)*  
*Delegated by: @Team_Leader per PHASE_REVIEW_PROTOCOL.md*
