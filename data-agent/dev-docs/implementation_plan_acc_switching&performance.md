# Audit: Account Switching & Disconnection Fixes + Performance & Memory Review

Full code audit of the walkthrough changes and adjacent systems for bugs, data bottlenecks, and memory piling risks.

---

## ✅ Walkthrough Changes — Verified Correct

### 1. Unconditional Disconnection API Call
In [pocket_option_session.py](file:///c:/v3/OTC_SNIPER/app/backend/session/pocket_option_session.py#L226-L255):

- `disconnect()` now calls `self._api.disconnect()` unconditionally when `self._api` exists (line 233), **bypassing the old `self._connected` guard**. This is correct — partial connections now get cleaned up.
- Global values are reset after disconnect (`SSID`, `DEMO`, `balance`, etc.)
- `self._api` is nulled, `self._connected` is cleared, `self._balance` is cleared.

✅ **No issues found** — the fix is structurally sound.

### 2. Defensive Socket Cleanup on Timeout/Failure
In [pocket_option_session.py](file:///c:/v3/OTC_SNIPER/app/backend/session/pocket_option_session.py#L150-L224):

- When `self._api.connect()` returns failure (line 180–187): the API wrapper is explicitly disconnected before being nulled. ✅
- When the connection timeout is reached (line 196–202): the API wrapper is explicitly disconnected before being nulled. ✅
- When balance auth fails (line 212–216): `self.disconnect()` is called. ✅
- When any exception occurs (line 217–224): `self.disconnect()` is called. ✅

✅ **No orphaned threads possible** — all failure paths now clean up.

### 3. SessionManager.connect() — Correct
In [manager.py](file:///c:/v3/OTC_SNIPER/app/backend/session/manager.py#L20-L33):

- When `connect()` is called and `self._session is not None`, it calls `self.disconnect()` first (line 21–22). This correctly tears down the old session before creating a new one.

✅ **No double-session leak possible.**

---

## 🐛 Bugs Found

### BUG 1: SQLite Connection Leak in `api_bridge.py` — `get_raw_ticks()` and `get_tick_velocity()`

> [!WARNING]
> **Severity: Medium** — Connection leaks under exceptions

In [api_bridge.py](file:///c:/v3/OTC_SNIPER/data-agent/src/api_bridge.py#L74-L111):

```python
conn = sqlite3.connect(self.db_path)  # line 75
cursor = conn.cursor()
# ...queries...
conn.close()  # line 90 — only reached on success
```

If the `cursor.execute()` or `fetchall()` throws, `conn.close()` is never called. Same pattern at line 231–245 in `get_tick_velocity()`.

**Fix:** Use `with sqlite3.connect(...)` context manager in both methods.

---

### BUG 2: `_tick_counts` KeyError on Cold Asset

In [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py#L554):

```python
self._tick_counts[asset] += 1  # line 554
```

If `_get_or_create_engines()` threw an exception before setting `self._tick_counts[asset]`, this line would raise a `KeyError`. It's unlikely but not impossible under race conditions or import errors.

**Fix:** Use `self._tick_counts[asset] = self._tick_counts.get(asset, 0) + 1`.

---

### BUG 3: `TickLogger.stop()` Schedules Final Flush via `asyncio.create_task()` After Loop May Be Closing

In [tick_logger.py](file:///c:/v3/OTC_SNIPER/app/backend/services/tick_logger.py#L49-L51):

```python
def stop(self):
    self._active = False
    if self._flush_task:
        self._flush_task.cancel()
        self._flush_task = None
    asyncio.create_task(self.flush_all())  # line 50 — can fail if loop is closing
```

If the event loop is shutting down (e.g., during `disconnect → stop()` cascading), `asyncio.create_task()` may raise `RuntimeError: no running event loop`. This silently drops all pending tick data.

**Fix:** Wrap in try/except or use `loop.create_task()` with a loop reference check.

---

### BUG 4: `_original_set_csv` Hook is Never Restored on Disconnect

In [pocket_option_session.py](file:///c:/v3/OTC_SNIPER/app/backend/session/pocket_option_session.py#L44-L93):

The monkey-patch in `_apply_hooks()` replaces `gv.set_csv` with `hooked_set_csv`, saving the original at `cls._original_set_csv`. But `disconnect()` and `clear_tick_callback()` never restore `gv.set_csv` back to the original. After disconnect, the hook remains installed, and if a new session is created, `_apply_hooks()` skips re-patching because `cls._original_set_csv is not None` — but now `cls._tick_callback` is `None`, so ticks silently invoke the hook which just calls the original and returns.

This is **functionally benign** (no crash) but wastes CPU cycles on every tick after disconnect until a new callback is set. Not a correctness bug, but a performance concern during idle periods.

---

## ⚡ Performance Issues & Optimization Opportunities

### PERF 1: `get_live_broker_assets()` Imports `pocketoptionapi.global_value` on Every Call

In [ssid_collector.py](file:///c:/v3/OTC_SNIPER/data-agent/src/tick_collector/ssid_collector.py#L161):

```python
def get_live_broker_assets(self) -> List[Dict[str, Any]]:
    try:
        import pocketoptionapi.global_value as gv  # re-imported every call
```

This is called by `get_available_assets()` which is hit on every frontend asset refresh. While Python caches module imports after the first load, the `try/except ImportError` wrapping adds unnecessary overhead per call.

**Fix:** Move to class-level or module-level import with a lazy flag.

---

### PERF 2: Manipulation Detector Recalculates MAV From Scratch on Every Tick

In [manipulation.py](file:///c:/v3/OTC_SNIPER/app/backend/services/manipulation.py#L42):

```python
mav = np.mean([abs(v) for v in self.velocities]) if self.velocities else 0.0
```

This creates a new list from the entire 300-element deque, then calls `np.mean()` on it — on **every single tick** for **every active asset**. With 9 assets, that's ~2700 list comprehensions + numpy calls per second at ~3 ticks/sec/asset.

**Fix:** Maintain a running sum of absolute velocities and divide by count (O(1) update instead of O(n)).

---

### PERF 3: `process_tick()` Creates Unbounded `asyncio.Task` Objects for `consider_signal()`

In [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py#L600-L613):

```python
signal_task = asyncio.create_task(
    self.auto_ghost.consider_signal(...)
)
signal_task.add_done_callback(...)
```

A new task is created for every actionable tick. These tasks are fire-and-forget — if `consider_signal()` blocks (e.g., waiting on the broker `buy()` call), many tasks can pile up concurrently with no backpressure. There's no tracking of how many tasks are alive.

**Fix:** Use a bounded semaphore or track active signal tasks to limit concurrency.

---

### PERF 4: `_resolve_asset_payout_pct()` Uses `asyncio.to_thread()` on Every Payout Resolution

In [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py#L346):

```python
payout_pct = await asyncio.to_thread(self.trade_service._resolve_payout_pct, adapter, asset)
```

While the 60-second TTL cache mitigates frequency, `asyncio.to_thread()` spawns a thread from the default `ThreadPoolExecutor`. Under high signal volume across many assets, this could saturate the default pool (usually 5–32 workers).

The cache is good. No immediate fix needed — just **monitor** thread pool utilization.

---

## 🗄️ Data Bottleneck Analysis

### BOTTLENECK 1: `TickLogger._buffers` is Unbounded Between Flushes

In [tick_logger.py](file:///c:/v3/OTC_SNIPER/app/backend/services/tick_logger.py#L58-L65):

```python
self._buffers[asset].append(line)
if len(self._buffers[asset]) >= 100:
    await self.flush_asset(asset)
```

The per-asset buffer flushes at 100 items, but if disk I/O is slow (network drive, USB, etc.), the `flush_asset()` call may fail, and the error handler **re-queues the failed lines back** (line 107), potentially growing the buffer unboundedly on persistent I/O failures.

**Fix:** Add a max retry count or cap the re-queued buffer size.

---

### BOTTLENECK 2: `_payout_fail_counts` Dictionary Grows Indefinitely

In [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py#L352-L354):

```python
fail_count = self._payout_fail_counts.get(asset, 0) + 1
self._payout_fail_counts[asset] = fail_count
```

This dict is never cleared unless the streaming service is fully stopped. If assets come and go, old entries persist. Not a large memory concern, but it's technically a leak.

**Fix:** Clear entries in `update_allowed_assets()` when assets are removed. Already done for `_payout_cache` (line 238) but not for `_payout_fail_counts`.

---

## 🧠 Memory Piling Analysis

| Component | Buffer Type | Bounded? | Max Size | Status |
|-----------|-------------|----------|----------|--------|
| `OTEO.ticks` | `deque` | ✅ | 300 | Safe |
| `OTEO.timestamps` | `deque` | ✅ | 300 | Safe |
| `ManipulationDetector.velocities` | `deque` | ✅ | 300 | Safe |
| `ManipulationDetector.price_history` | `deque` | ✅ | 300 | Safe |
| `PerformanceMonitor.processing_durations` | `deque` | ✅ | 200 | Safe |
| `AutoGhost._session_trades` | `deque` | ✅ | 200 | Safe |
| `StreamingService._tick_queue` | `asyncio.Queue` | ✅ | 500 | Safe — drops old on full |
| `TickLogger._buffers` | `dict[list]` | ⚠️ | Flush at 100 | **Risk if I/O fails** |
| `StreamingService._oteo_engines` | `dict` | ⚠️ | Per-asset | Cleaned on `update_allowed_assets` |
| `StreamingService._last_prices` | `dict` | ⚠️ | Per-asset | Never cleaned (**minor leak**) |
| `StreamingService._payout_fail_counts` | `dict` | ⚠️ | Per-asset | Never cleaned (**minor leak**) |
| `AIReviewService._pending_snapshots` | `dict` | ✅ | 1 per asset (overwritten) | Safe |
| `AIReviewService._last_reviews` | `dict` | ⚠️ | Per-asset | Never cleaned (**minor leak**) |

> [!IMPORTANT]
> The critical buffers (deques, Queue) are all properly bounded. The "minor leaks" are `dict` entries for assets that were once subscribed but never cleaned up. These grow very slowly (~200 bytes/asset) and are only a concern over weeks of continuous uptime.

---

## 🔧 Proposed Fixes (Priority Order)

### P1 — SQLite Connection Leak (BUG 1)
- **File:** [api_bridge.py](file:///c:/v3/OTC_SNIPER/data-agent/src/api_bridge.py)
- Change `conn = sqlite3.connect(...)` to `with sqlite3.connect(...) as conn:` in `get_raw_ticks()` and `get_tick_velocity()`

### P2 — TickLogger Stop Crash (BUG 3)
- **File:** [tick_logger.py](file:///c:/v3/OTC_SNIPER/app/backend/services/tick_logger.py)
- Wrap `asyncio.create_task(self.flush_all())` in a try/except

### P3 — `_payout_fail_counts` Cleanup (BOTTLENECK 2)
- **File:** [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py)
- Add `self._payout_fail_counts.pop(asset, None)` in `update_allowed_assets()` removal loop
- Also clean `self._last_prices.pop(asset, None)` in the same loop

### P4 — ManipulationDetector MAV Optimization (PERF 2)
- **File:** [manipulation.py](file:///c:/v3/OTC_SNIPER/app/backend/services/manipulation.py)
- Maintain incremental running sum of `abs(vel)` instead of recomputing from deque

### P5 — _tick_counts KeyError Guard (BUG 2)
- **File:** [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py)
- Use `self._tick_counts.get(asset, 0) + 1`

---

## Open Questions

1. **TickLogger buffer cap on I/O failure**: Should we cap the re-queue at e.g. 500 lines and start dropping oldest ticks after that?
2. **`consider_signal` task concurrency**: Should we add a semaphore (e.g. `max_concurrent_trades` value) to limit how many `consider_signal` tasks can be in-flight?
3. **`_original_set_csv` hook restoration**: Should we restore the original `gv.set_csv` on full session disconnect, or is the current behavior (hook stays installed but is a no-op) acceptable?

---

## Verification Plan

### Automated Tests
```powershell
conda run -n QuFLX-v2 python -m pytest tests/test_vps_tick_collector.py tests/test_vps_phase1_runtime.py tests/test_vps_phase3_context_trades.py -v
```

### Manual Verification
- Connect → disconnect → reconnect cycle to verify no thread leaks
- Check SQLite connections are properly closed under error conditions
