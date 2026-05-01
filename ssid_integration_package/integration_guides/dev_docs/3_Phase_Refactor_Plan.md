# 3-Phase Surgical Refactor Plan — SSID Integration Package
**Date:** 2026-03-31  
**Author:** @Architect → @Reviewer  
**Status:** APPROVED FOR IMPLEMENTATION  
**Scope:** `pocketoptionapi/ws/objects/`, `pocketoptionapi/ws/channels/`, `api.py`, `stable_api.py`  
**Supersedes:** `Research/Refactor_Implementation_Plan_2026-03-30.md` (7-phase full refactor — NOT recommended)

---

## ⚠️ Critical Decision Context

This plan is the **safe alternative** to the full 7-phase refactor. It was produced after a conflict analysis between the original refactor plan and the verified working SSID live streaming pipeline.

### Why NOT the Full 7-Phase Refactor

| Risk Score | Category | Score |
|-----------|----------|-------|
| 🔴 Instability Risk | Full refactor destabilises working streaming | **72 / 100** |
| 🟡 Unnecessary Complexity | Adds abstraction layers over working code | **58 / 100** |
| 🟢 Broker Violations / Rate Limiting | Low — no protocol changes | **25 / 100** |
| 🟡 Integration Difficulty | Requires deep threading + asyncio knowledge | **65 / 100** |
| 🔴 Benefits of Full Refactor | Marginal gain vs high risk | **45 / 100** |
| ✅ Benefits of Surgical 3-Phase | High gain, low risk | **78 / 100** |

**Overall recommendation against full 7-phase refactor: 35/100**  
**Recommendation FOR this surgical 3-phase approach: 85/100**

### The Golden Asset — Do Not Touch
The live streaming pipeline is **proven, functional, and the foundation for the entire OTC SNIPER system**:
- `gv.set_csv` monkey-patch → `asyncio.run_coroutine_threadsafe` → `StreamingService.process_tick`
- Sustained ~8.2 ticks/sec, 0% packet loss, verified auth
- This pipeline depends on the **installed conda environment `pocketoptionapi`**, NOT the local copy in this package
- The local copy in `ssid_integration_package/pocketoptionapi/` is a reference/development copy

**Do NOT refactor `client.py` (Phase 6 of the original plan) until the streaming pipeline has been independently migrated and re-verified in isolation.**

---

## Table of Contents

1. [Current State Map](#1-current-state-map)
2. [Architecture Context](#2-architecture-context)
3. [Phase 1 — Dead Code Removal](#phase-1--dead-code-removal)
4. [Phase 2 — Candle Dataclass Consolidation](#phase-2--candle-dataclass-consolidation)
5. [Phase 3 — Time Sync Merge](#phase-3--time-sync-merge)
6. [Deferred Phases (Do Not Implement Yet)](#deferred-phases--do-not-implement-yet)
7. [Verification Checklist](#verification-checklist)
8. [Files Touched Summary](#files-touched-summary)
9. [Risk Assessment Table](#risk-assessment-table)
10. [Agent Delegation Map](#agent-delegation-map)

---

## 1. Current State Map

### File Inventory — Problems Identified

| File | Status | Problem | Severity |
|------|--------|---------|----------|
| `objects/enhanced_candles.py` | Dead code | Never populated, never imported by working path | 🔴 Critical |
| `objects/candles.py` | Broken | `get_historical_candles()` references `self.api` which is never set | 🔴 Critical |
| `objects/timesync.py` | Duplicate | Duplicates `objects/time_sync.py` — both used in `client.py` | 🟡 Medium |
| `objects/time_sync.py` | Duplicate | Duplicates `objects/timesync.py` — both used in `api.py` | 🟡 Medium |
| `channels/get_currency_pairs.py` | Empty file | Zero implementation, zero imports | ⚠️ Low |
| `channels/get_balances.py` | Minor issue | Contains `print()` statement at line 16 | ⚠️ Low |
| `channels/buy_advanced.py` | Minor issue | `sys.stdout.write` + blocking `time.sleep` loops | ⚠️ Low |
| `channels/buyv3.py` | Minor issue | Hardcodes `isDemo: 1` | ⚠️ Low |
| `api.py` | Working but fragile | `@property getcandles` creates new instance every call; busy-wait polling | 🟡 Medium |
| `client.py` | Working — DO NOT TOUCH | Monolithic `on_message()` is the nerve center of streaming | 🔴 High Risk to Modify |

### Working Data Flow (Preserve At All Costs)

```
stable_api.get_candles(active, timeframe, count)
    │
    ▼
api.py: get_candles_data()
    │  - Validates params
    │  - Calls self.getcandles(active, interval, count, end_time)
    │
    ▼
channels/candles.py: GetCandles.__call__()
    │  - Sends: 42["loadHistoryPeriod", {...}]
    │
    ▼
Server responds via WebSocket (binary JSON)
    │
    ▼
client.py: on_message()  ← ⚠️ DO NOT REFACTOR IN THIS PLAN
    │  - Detects "loadHistoryPeriod" → sets history_data_ready = True
    │  - Next binary message → self.api.history_data = message["data"]
    │
    ▼
api.py: get_candles_data() busy-waits on self.history_data
    │
    ▼
stable_api.py: get_candles() → [[time, open, high, low, close], ...]
```

### Live Streaming Flow (Golden Asset — Preserve Completely)

```
Library WS Thread (installed pocketoptionapi)
    │  Receives binary frame → parses tick
    │
    ▼
gv.set_csv(asset, [{'time': t, 'price': p}])  ← monkey-patched
    │
    ▼
_threadsafe_set_csv() hook
    │  asyncio.run_coroutine_threadsafe(process_tick(), main_loop)
    │
    ▼
Main Asyncio Thread
    │  StreamingService.process_tick()
    │  → OTEO.update_tick()
    │  → TickLogger.write_tick()
    │  → sio.emit('market_data')
```

---

## 2. Architecture Context

### Two Separate `pocketoptionapi` Copies — Critical Distinction

| Copy | Location | Used By | Status |
|------|----------|---------|--------|
| **Installed (conda)** | `QuFLX-v2` conda env | Live streaming harness, `app/backend/` | ✅ Working — DO NOT MODIFY |
| **Local (reference)** | `ssid_integration_package/pocketoptionapi/` | Development/testing only | 🔧 Safe to refactor |

> **Rule:** All phases in this plan apply ONLY to the local reference copy in `ssid_integration_package/pocketoptionapi/`. Never apply these changes directly to the installed conda environment package without a full regression test of the streaming pipeline first.

### Key Threading Architecture (Must Be Preserved)

The streaming pipeline bridges two execution contexts:

```
┌─────────────────────────────────┐    ┌──────────────────────────────────┐
│  WebSocket Background Thread    │    │  Main Asyncio Event Loop         │
│  (pocketoptionapi library)      │    │  (FastAPI / test harness)        │
│                                 │    │                                  │
│  on_message() → parse tick      │    │  StreamingService.process_tick() │
│  → gv.set_csv(asset, tick)      │───▶│  → OTEO, TickLogger, sio.emit   │
│    (monkey-patched)             │    │                                  │
│  asyncio.run_coroutine_         │    │                                  │
│  threadsafe(coro, main_loop)    │    │                                  │
└─────────────────────────────────┘    └──────────────────────────────────┘
```

**Any refactor that touches `client.py`, `global_value.py`, or the `on_message()` routing MUST be regression-tested against this bridge before merging.**

---

## Phase 1 — Dead Code Removal

**Goal:** Remove files that add confusion without providing value.  
**Risk:** 🟢 Very Low — these files are not referenced in any working code path.  
**Delegate:** @Coder  
**Estimated effort:** 30 minutes  
**Requires @Reviewer sign-off before Phase 2.**

### Pre-Flight Verification (Run Before Any Deletions)

```powershell
# Verify no working imports reference these files
Select-String -Path "ssid_integration_package\pocketoptionapi\*" -Pattern "enhanced_candles" -Recurse
Select-String -Path "ssid_integration_package\pocketoptionapi\*" -Pattern "get_currency_pairs" -Recurse
Select-String -Path "ssid_integration_package\pocketoptionapi\*" -Pattern "CandleData" -Recurse
```

### Tasks

- [ ] **1.1** Delete `objects/enhanced_candles.py`
  - **Reason:** Entirely dead code — `EnhancedCandles` and `CandleData` are never populated by `client.py`'s `on_message()`. The `Candles` object on `PocketOptionAPI` is never written to by the message handler (Problem P13 in original audit).
  - **Verify first:** `grep -r "EnhancedCandles" pocketoptionapi/` → must return 0 results outside this file
  - **Verify first:** `grep -r "CandleData" pocketoptionapi/` → must return 0 results outside this file and `objects/candles.py`

- [ ] **1.2** Delete `channels/get_currency_pairs.py`
  - **Reason:** File is completely empty — zero implementation, zero value.
  - **Verify first:** `grep -r "get_currency_pairs" pocketoptionapi/` → must return 0 results outside this file

- [ ] **1.3** Remove the `print()` statement from `channels/get_balances.py` line 16
  - **Action:** Replace `print(...)` with `logger.debug(...)` or remove entirely
  - **Do NOT change any other logic in this file**

- [ ] **1.4** Import verification after deletions:
  ```powershell
  conda activate QuFLX-v2
  python -c "from pocketoptionapi.api import PocketOptionAPI; print('OK')"
  python -c "from pocketoptionapi.stable_api import PocketOption; print('OK')"
  ```

### Phase 1 Acceptance Criteria

- [ ] `grep -r "enhanced_candles" pocketoptionapi/` → zero results
- [ ] `grep -r "get_currency_pairs" pocketoptionapi/` → zero results
- [ ] `grep -r "print(" pocketoptionapi/ws/channels/` → zero results
- [ ] `python -c "from pocketoptionapi.api import PocketOptionAPI"` → no errors
- [ ] `python -m pytest tests/test_imports.py -v` → all pass

---

## Phase 2 — Candle Dataclass Consolidation

**Goal:** Replace the broken `objects/candles.py` with a clean, immutable `Candle` dataclass.  
**Risk:** 🟢 Low — the current `Candle` class in `objects/candles.py` is broken and unused in the working path. The working path uses raw dicts from `api.history_data`.  
**Delegate:** @Coder  
**Estimated effort:** 1–2 hours  
**Requires @Reviewer sign-off before Phase 3.**

> ⚠️ **Important:** The `stable_api.py` return format `[[time, open, high, low, close], ...]` MUST be preserved for backward compatibility. Do not change the public API surface.

### Tasks

- [ ] **2.1** Create `objects/candle.py` — new canonical candle dataclass:

```python
"""
Canonical candle data model for Pocket Option API.
Replaces the broken objects/candles.py.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass(frozen=True)
class Candle:
    """
    Single OHLC candle — immutable value object.
    
    Server response format from loadHistoryPeriod:
        {"time": int, "open": float, "high": float, "low": float, "close": float}
    
    Legacy list format (stable_api.py output):
        [time, open, high, low, close]
    
    Note: The legacy pocketoptionapi list format is [time, open, CLOSE, high, low]
    (close and high are swapped vs standard OHLC). Verify against live server
    response before using from_list() with legacy data.
    """
    time: int
    open: float
    high: float
    low: float
    close: float

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def candle_type(self) -> str:
        if self.is_bullish:
            return "green"
        elif self.is_bearish:
            return "red"
        return "doji"

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }

    def to_list(self) -> list:
        """Standard OHLC list: [time, open, high, low, close]"""
        return [self.time, self.open, self.high, self.low, self.close]

    @classmethod
    def from_dict(cls, data: dict) -> "Candle":
        """Create from server response dict."""
        return cls(
            time=int(data["time"]),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
        )

    @classmethod
    def from_list(cls, data: list) -> "Candle":
        """
        Parse from legacy list format.
        ⚠️ WARNING: Verify actual server format before using.
        Legacy pocketoptionapi format may be [time, open, close, high, low].
        """
        if len(data) != 5:
            raise ValueError(f"Expected 5 elements, got {len(data)}: {data}")
        return cls(
            time=int(data[0]),
            open=float(data[1]),
            high=float(data[3]),
            low=float(data[4]),
            close=float(data[2]),
        )


class CandleCollection:
    """
    Thread-safe in-memory cache of candles keyed by symbol + timeframe.
    Optional — used for caching retrieved candles to avoid redundant requests.
    """

    def __init__(self):
        self._candles: Dict[str, List[Candle]] = {}

    def _key(self, symbol: str, timeframe: int) -> str:
        return f"{symbol}_{timeframe}"

    def store(self, symbol: str, timeframe: int, candles: List[Candle]) -> None:
        """Store/replace candles for a symbol+timeframe pair (sorted by time)."""
        key = self._key(symbol, timeframe)
        self._candles[key] = sorted(candles, key=lambda c: c.time)

    def get(self, symbol: str, timeframe: int, count: int = 100) -> List[Candle]:
        """Get latest `count` candles for a symbol+timeframe pair."""
        key = self._key(symbol, timeframe)
        candles = self._candles.get(key, [])
        return candles[-count:]

    def clear(self, symbol: Optional[str] = None, timeframe: Optional[int] = None) -> None:
        """Clear cache. If no args, clears everything."""
        if symbol and timeframe:
            self._candles.pop(self._key(symbol, timeframe), None)
        else:
            self._candles.clear()
```

- [ ] **2.2** Delete `objects/candles.py`
  - **Reason:** `get_historical_candles()` references `self.api` which is never set (Problem P1). The `Candles` class is never populated by `client.py`. This file is broken by design.
  - **Verify first:** Confirm `api.py` only uses `self.history_data` (raw dict), not `self.candles` from this class

- [ ] **2.3** Update `api.py` — replace broken `Candles` import:
  ```python
  # REMOVE:
  from pocketoptionapi.ws.objects.candles import Candles
  # ...
  candles = Candles()  # class attribute — never populated
  
  # ADD:
  from pocketoptionapi.ws.objects.candle import Candle, CandleCollection
  # ...
  candle_collection = CandleCollection()  # class attribute — optional cache
  ```
  - **Do NOT change `get_candles_data()` logic** — it still uses `self.history_data` (raw dicts)
  - The `CandleCollection` is added as an optional cache only — do not wire it into the busy-wait loop yet

- [ ] **2.4** Update `stable_api.py` — keep backward-compatible return format:
  - The `get_candles()` method returns `[[time, open, high, low, close], ...]`
  - **Do NOT change this return format** — it is the public API surface
  - Only update the import if `stable_api.py` directly imports from `objects/candles.py`

- [ ] **2.5** Create `objects/__init__.py`:
  ```python
  """Public exports for pocketoptionapi.ws.objects."""
  from pocketoptionapi.ws.objects.candle import Candle, CandleCollection
  from pocketoptionapi.ws.objects.asset import Asset, AssetManager
  from pocketoptionapi.ws.objects.time_sync import TimeSync
  from pocketoptionapi.ws.objects.trade_data import TradeData
  ```
  *(Note: `TimeSync` export will be valid after Phase 3 completes the merge)*

### Phase 2 Acceptance Criteria

- [ ] `python -c "from pocketoptionapi.ws.objects.candle import Candle, CandleCollection; c = Candle(time=1, open=1.0, high=1.1, low=0.9, close=1.05); print(c)"` → prints Candle object
- [ ] `python -c "from pocketoptionapi.api import PocketOptionAPI"` → no errors
- [ ] `python -c "from pocketoptionapi.stable_api import PocketOption"` → no errors
- [ ] `grep -r "from pocketoptionapi.ws.objects.candles" pocketoptionapi/` → zero results
- [ ] `grep -r "CandleData" pocketoptionapi/` → zero results
- [ ] `python -m pytest tests/test_imports.py -v` → all pass

---

## Phase 3 — Time Sync Merge

**Goal:** Merge `objects/timesync.py` + `objects/time_sync.py` into one unified `TimeSync` class.  
**Risk:** 🟡 Medium — both classes are actively used in `client.py` and `api.py`. Requires careful import surgery.  
**Delegate:** @Coder  
**Estimated effort:** 1–2 hours  
**Requires @Reviewer sign-off before marking complete.**

> ⚠️ **Critical:** After this phase, run the full streaming test harness (`ssid_streaming_test/scripts/test_streaming.py`) to verify tick delivery is unaffected. Time sync is used in the WebSocket message handler — any regression here breaks the streaming pipeline.

### Pre-Flight: Audit Current Usage

Before writing any code, @Coder must run:

```powershell
# Find all usages of both time sync classes
Select-String -Path "ssid_integration_package\pocketoptionapi\*" -Pattern "TimeSync|TimeSynchronizer" -Recurse
```

Expected findings:
- `client.py`: imports and uses both `TimeSync` (from `timesync.py`) and `TimeSynchronizer` (from `time_sync.py`)
- `api.py`: imports and uses both `time_sync = TimeSync()` and `sync = TimeSynchronizer()`

### Tasks

- [ ] **3.1** Read both existing files in full before writing anything:
  - `objects/timesync.py` — document all properties and methods
  - `objects/time_sync.py` — document all properties and methods
  - Identify: which properties are used in `client.py`? Which in `api.py`?

- [ ] **3.2** Rewrite `objects/time_sync.py` — unified class combining both:

```python
"""
Unified time synchronization for Pocket Option API.

Merges:
- objects/timesync.py  (TimeSync — server timestamp tracking)
- objects/time_sync.py (TimeSynchronizer — drift-compensated sync + expiration)

Usage:
    time_sync = TimeSync()
    time_sync.server_timestamp = 1711800000  # set from server message
    print(time_sync.synced_datetime)          # drift-compensated current time
    print(time_sync.expiration_timestamp)     # for order expiration
"""
import time
import datetime
from datetime import timezone, timedelta


class TimeSync:
    """
    Server time synchronization with drift compensation and expiration tracking.
    Thread-safe for read access; writes should be from the WS message handler only.
    """

    def __init__(self):
        self._server_timestamp: float = time.time()
        self._local_reference: float = time.time()
        self._expiration_minutes: int = 1

    # ── Server Timestamp ──────────────────────────────────────────────────────

    @property
    def server_timestamp(self) -> float:
        return self._server_timestamp

    @server_timestamp.setter
    def server_timestamp(self, timestamp: float):
        self._server_timestamp = float(timestamp)
        self._local_reference = time.time()  # Reset drift reference on update

    @property
    def server_datetime(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self._server_timestamp)

    # ── Drift-Compensated Time ────────────────────────────────────────────────

    @property
    def synced_timestamp(self) -> float:
        """Current estimated server time, compensating for elapsed local time."""
        elapsed = time.time() - self._local_reference
        return self._server_timestamp + elapsed

    @property
    def synced_datetime(self) -> datetime.datetime:
        """UTC datetime of current estimated server time."""
        return datetime.datetime.fromtimestamp(
            round(self.synced_timestamp), tz=timezone.utc
        )

    # ── Expiration ────────────────────────────────────────────────────────────

    @property
    def expiration_minutes(self) -> int:
        return self._expiration_minutes

    @expiration_minutes.setter
    def expiration_minutes(self, minutes: int):
        self._expiration_minutes = int(minutes)

    @property
    def expiration_datetime(self) -> datetime.datetime:
        return self.server_datetime + timedelta(minutes=self._expiration_minutes)

    @property
    def expiration_timestamp(self) -> float:
        return time.mktime(self.expiration_datetime.timetuple())
```

- [ ] **3.3** Delete `objects/timesync.py`
  - Only after `objects/time_sync.py` has been rewritten and verified

- [ ] **3.4** Update `client.py` imports:
  ```python
  # REMOVE both old imports:
  from pocketoptionapi.ws.objects.timesync import TimeSync
  from pocketoptionapi.ws.objects.time_sync import TimeSynchronizer
  
  # ADD single import:
  from pocketoptionapi.ws.objects.time_sync import TimeSync
  ```
  - Replace `timesync = TimeSync()` and `sync = TimeSynchronizer()` with single `time_sync = TimeSync()`
  - Update all usages: `timesync.server_timestamp` → `time_sync.server_timestamp`, etc.
  - **Do NOT change any other logic in `client.py`**

- [ ] **3.5** Update `api.py` imports:
  ```python
  # REMOVE both old imports:
  from pocketoptionapi.ws.objects.timesync import TimeSync
  from pocketoptionapi.ws.objects.time_sync import TimeSynchronizer
  
  # ADD single import:
  from pocketoptionapi.ws.objects.time_sync import TimeSync
  ```
  - Replace `time_sync = TimeSync()` and `sync = TimeSynchronizer()` with single `time_sync = TimeSync()`
  - Update `synced_datetime` property to use `self.time_sync.synced_datetime`

- [ ] **3.6** Update `objects/__init__.py` (created in Phase 2):
  - Verify `from pocketoptionapi.ws.objects.time_sync import TimeSync` resolves correctly

### Phase 3 Acceptance Criteria

- [ ] `python -c "from pocketoptionapi.ws.objects.time_sync import TimeSync; ts = TimeSync(); ts.server_timestamp = 1711800000; print(ts.synced_datetime)"` → prints UTC datetime
- [ ] `grep -r "TimeSynchronizer" pocketoptionapi/` → zero results
- [ ] `grep -r "from.*timesync import" pocketoptionapi/` → zero results (old module gone)
- [ ] `python -c "from pocketoptionapi.api import PocketOptionAPI"` → no errors
- [ ] `python -c "from pocketoptionapi.stable_api import PocketOption"` → no errors
- [ ] `python -m pytest tests/test_imports.py -v` → all pass
- [ ] **Streaming regression test:** Run `ssid_streaming_test/scripts/test_streaming.py` for 30 seconds → tick rate ≥ 5 ticks/sec, 0 errors

---

## Deferred Phases — Do Not Implement Yet

The following phases from the original 7-phase plan are **explicitly deferred** until the streaming pipeline has been independently migrated and re-verified.

### ❌ Phase 4 — Candle Pipeline Hardening (DEFERRED)

**Why deferred:** Replacing the busy-wait polling with `threading.Event` requires modifying `client.py`'s `on_message()` to call `self.api._candle_event.set()`. This is the same method that routes live tick data. Any mistake here silently breaks the streaming pipeline.

**Condition to unblock:** The streaming pipeline must be migrated to a standalone service that does not depend on `client.py`'s `on_message()` routing. Only then is it safe to refactor the candle response path.

### ❌ Phase 5 — Channel Cleanup / Buy Merge (DEFERRED)

**Why deferred:** The `buyv3.py` / `buy_advanced.py` merge is low-risk but low-value. The hardcoded `isDemo: 1` fix requires verifying `global_value.DEMO` is correctly set in all execution contexts. Deferring avoids any accidental regression in the trading path.

**Condition to unblock:** After Phase 1–3 are complete and stable for ≥ 1 week with no regressions.

### ❌ Phase 6 — Client Message Handler Refactor (DEFERRED — HIGH RISK)

**Why deferred:** `client.py`'s `on_message()` is the nerve center of both the candle retrieval path AND the live streaming tick path. Refactoring it into sub-handlers is the highest-risk change in the entire plan.

**Condition to unblock:** 
1. Streaming pipeline fully migrated to independent service
2. Full integration test suite covering both candle retrieval and live streaming
3. Explicit @Reviewer + @Architect sign-off

### ❌ Phase 7 — Integration Testing (DEFERRED)

**Why deferred:** Depends on Phases 4–6. Unit tests for `Candle` dataclass and `TimeSync` should be written as part of Phases 2 and 3 respectively.

---

## Verification Checklist

### After Phase 1
- [ ] Zero dead code files remain
- [ ] No `print()` in library code
- [ ] Import smoke test passes

### After Phase 2
- [ ] `Candle` dataclass importable and functional
- [ ] `CandleCollection` importable and functional
- [ ] `api.py` and `stable_api.py` import cleanly
- [ ] Backward-compatible `[[t, o, h, l, c], ...]` return format preserved

### After Phase 3
- [ ] Single `TimeSync` class in `objects/time_sync.py`
- [ ] No `TimeSynchronizer` references anywhere
- [ ] No `timesync.py` file exists
- [ ] `client.py` and `api.py` use single `time_sync = TimeSync()` instance
- [ ] **Streaming regression test passes** (most critical gate)

### Final Gate (All 3 Phases Complete)
- [ ] `python -m pytest tests/ -v` → all pass
- [ ] `python -c "from pocketoptionapi.stable_api import PocketOption"` → no errors
- [ ] `grep -r "enhanced_candles\|get_currency_pairs\|CandleData\|TimeSynchronizer\|timesync" pocketoptionapi/` → zero results
- [ ] Historical candle retrieval via SSID works end-to-end (manual test with valid SSID)
- [ ] Live streaming tick rate ≥ 5 ticks/sec sustained for 60 seconds

---

## Files Touched Summary

| File | Action | Phase | Risk |
|------|--------|-------|------|
| `objects/enhanced_candles.py` | **DELETE** | 1 | 🟢 None |
| `channels/get_currency_pairs.py` | **DELETE** | 1 | 🟢 None |
| `channels/get_balances.py` | **EDIT** (remove print) | 1 | 🟢 None |
| `objects/candle.py` | **CREATE** (new dataclass) | 2 | 🟢 None |
| `objects/candles.py` | **DELETE** (broken) | 2 | 🟢 None |
| `objects/__init__.py` | **CREATE** | 2 | 🟢 None |
| `api.py` | **EDIT** (swap Candles import) | 2 | 🟢 Low |
| `stable_api.py` | **EDIT** (update import if needed) | 2 | 🟢 Low |
| `objects/time_sync.py` | **REWRITE** (merge both classes) | 3 | 🟡 Medium |
| `objects/timesync.py` | **DELETE** | 3 | 🟡 Medium |
| `client.py` | **EDIT** (imports + instance rename only) | 3 | 🟡 Medium |
| `api.py` | **EDIT** (imports + instance rename only) | 3 | 🟡 Medium |

**Total: 4 files deleted, 2 files created, 4 files edited, 1 file rewritten**  
*(vs original plan: 8 deleted, 6 created, 4 edited, 1 rewritten — 40% less scope)*

### Files Explicitly NOT Touched in This Plan

| File | Reason |
|------|--------|
| `client.py` (logic) | Nerve center of streaming — only import surgery in Phase 3 |
| `channels/candles.py` | Working — do not touch |
| `channels/change_symbol.py` | Working — do not touch |
| `channels/buyv3.py` | Deferred to Phase 5 |
| `channels/buy_advanced.py` | Deferred to Phase 5 |
| `global_value.py` | Critical to streaming hook — never touch without full regression |

---

## Risk Assessment Table

| Phase | Risk Level | Primary Risk | Mitigation |
|-------|-----------|-------------|------------|
| Phase 1 — Dead Code Removal | 🟢 Very Low | Accidental deletion of referenced file | Pre-flight grep search before every delete |
| Phase 2 — Candle Dataclass | 🟢 Low | Breaking `stable_api.py` return format | Preserve `[[t,o,h,l,c]]` format; only swap import |
| Phase 3 — Time Sync Merge | 🟡 Medium | Breaking `client.py` timestamp handling → streaming regression | Audit all usages first; streaming regression test after |
| Phase 4 (DEFERRED) | 🔴 High | `threading.Event` in `on_message()` breaks streaming | Deferred until streaming is independent |
| Phase 5 (DEFERRED) | 🟡 Medium | `isDemo` flag regression in trading path | Deferred — low value, non-zero risk |
| Phase 6 (DEFERRED) | 🔴 Very High | Monolithic handler refactor destroys streaming | Deferred until full test suite exists |

---

## Agent Delegation Map

| Task | Agent | Notes |
|------|-------|-------|
| Pre-flight grep searches | @Investigator | Read-only verification before any deletion |
| Phase 1 execution | @Coder | Simple deletions + print removal |
| Phase 1 review | @Reviewer | Verify no broken imports |
| Phase 2 execution | @Coder | Create `candle.py`, delete `candles.py`, update imports |
| Phase 2 review | @Reviewer | Verify backward compat + dataclass correctness |
| Phase 3 pre-flight audit | @Investigator | Map all `TimeSync`/`TimeSynchronizer` usages |
| Phase 3 execution | @Coder | Rewrite `time_sync.py`, delete `timesync.py`, update imports |
| Phase 3 review | @Reviewer | Verify imports + streaming regression test |
| Streaming regression test | @Tester | Run `test_streaming.py` for 60 seconds after Phase 3 |
| Final sign-off | @Architect | Confirm all 3 phases complete and stable |

---

## Implementation Protocol

Per `.clinerules/PHASE_REVIEW_PROTOCOL.md`:

1. **After each Phase:** @Team_Leader delegates @Reviewer with: `"Phase X completed. Perform full incremental review."`
2. **@Reviewer** produces a structured report (✅ / ⚠️ / 🔴) before any next phase begins.
3. **No phase proceeds** without explicit user command: `"Proceed with next phase"` or `"Approved – continue"`.
4. **Phase 3 has an additional gate:** Streaming regression test must pass before @Reviewer can sign off.

---

## Notes for @Coder

1. **Git commit after each phase** — one commit per phase for easy rollback.
   ```powershell
   git add -A; git commit -m "Phase 1: Dead code removal — ssid_integration_package"
   git add -A; git commit -m "Phase 2: Candle dataclass consolidation — ssid_integration_package"
   git add -A; git commit -m "Phase 3: Time sync merge — ssid_integration_package"
   ```

2. **The `from_list` format warning** — the legacy `pocketoptionapi` list format is `[time, open, close, high, low]` (close and high are swapped vs standard OHLC). The `Candle.from_list()` method accounts for this, but **verify against a live server response** before using it in production.

3. **`client.py` is sacred in Phase 3** — only change the import lines and the instance variable name. Do not touch `on_message()`, do not touch any message routing logic, do not touch any property access patterns beyond renaming `timesync` → `time_sync` and `sync` → `time_sync`.

4. **The installed conda package is NOT this local copy** — changes here do not affect the running `app/backend/` system. To apply these changes to production, a separate migration plan is required.

5. **If any phase produces an unexpected import error** — stop immediately, do not patch forward. Revert the phase, report to @Reviewer, and re-plan.

---

*Plan compiled by @Architect from conflict analysis of `Research/Refactor_Implementation_Plan_2026-03-30.md` and `ssid_streaming_test/scripts/ssid_streaming_implementation_report_26-03-30.md`.*  
*Timestamp: 2026-03-31*  
*Status: Ready for @Coder implementation — Phase 1 first.*
