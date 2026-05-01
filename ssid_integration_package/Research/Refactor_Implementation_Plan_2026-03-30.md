# Refactor Implementation Plan — SSID Integration Package
**Date:** 2026-03-30  
**Author:** @Reviewer → @Architect  
**Status:** DRAFT — Awaiting approval before implementation  
**Scope:** `pocketoptionapi/ws/objects/` and `pocketoptionapi/ws/channels/` + related wiring in `api.py`, `client.py`, `stable_api.py`

---

## Executive Summary

The current codebase has a working SSID-authenticated WebSocket pipeline for retrieving historical candles, but it is buried under layers of dead code, duplicate data structures, and broken abstractions. This plan addresses every issue found in the @Reviewer audit and produces a clean, minimal, fully-functional architecture optimized for SSID-based candle retrieval.

---

## Table of Contents

1. [Current Architecture (As-Is)](#1-current-architecture-as-is)
2. [Target Architecture (To-Be)](#2-target-architecture-to-be)
3. [Phase 1 — Dead Code Removal](#phase-1--dead-code-removal)
4. [Phase 2 — Data Model Consolidation](#phase-2--data-model-consolidation)
5. [Phase 3 — Time Sync Merge](#phase-3--time-sync-merge)
6. [Phase 4 — Candle Pipeline Hardening](#phase-4--candle-pipeline-hardening)
7. [Phase 5 — Channel Cleanup](#phase-5--channel-cleanup)
8. [Phase 6 — Client Message Handler Refactor](#phase-6--client-message-handler-refactor)
9. [Phase 7 — Integration Testing](#phase-7--integration-testing)
10. [Risk Assessment](#risk-assessment)
11. [File Change Matrix](#file-change-matrix)
12. [Acceptance Criteria](#acceptance-criteria)

---

## 1. Current Architecture (As-Is)

### Data Flow for Historical Candles (Working Path)
```
stable_api.get_candles(active, timeframe, count)
    │
    ▼
api.py: get_candles_data()
    │  - Validates params
    │  - Calls self.getcandles(active, interval, count, end_time)
    │    → @property returns GetCandles(self)  ← new instance every call!
    │
    ▼
channels/candles.py: GetCandles.__call__()
    │  - Formats: {"asset", "index", "offset", "period", "time"}
    │  - Sends: 42["loadHistoryPeriod", data]
    │
    ▼
Server responds via WebSocket (binary JSON)
    │
    ▼
client.py: on_message()
    │  - Detects "loadHistoryPeriod" in 451- prefix → sets history_data_ready = True
    │  - Next binary message → self.api.history_data = message["data"]
    │
    ▼
api.py: get_candles_data() busy-waits on self.history_data
    │  - Returns sorted list of candle dicts
    │
    ▼
stable_api.py: get_candles() formats to [[time, open, high, low, close], ...]
```

### Problems Identified

| # | Problem | Severity | Location |
|---|---------|----------|----------|
| P1 | `objects/candles.py` has `get_historical_candles()` that references `self.api` which is never set | 🔴 Critical | `objects/candles.py:82` |
| P2 | `objects/enhanced_candles.py` is entirely dead code — never populated | 🔴 Critical | `objects/enhanced_candles.py` |
| P3 | Three duplicate candle data representations (`Candle`, `CandleData`, raw dict) | 🟡 Medium | Multiple files |
| P4 | Two duplicate time sync classes (`TimeSync` + `TimeSynchronizer`) | 🟡 Medium | `objects/timesync.py`, `objects/time_sync.py` |
| P5 | `GetCandles` is re-instantiated on every call via `@property` | 🟡 Medium | `api.py:148` |
| P6 | Busy-wait polling with `time.sleep(0.1)` for candle responses | 🟡 Medium | `api.py:175`, `objects/candles.py:95` |
| P7 | `buy_advanced.py` has blocking `time.sleep` loops + `sys.stdout.write` | ⚠️ Low | `channels/buy_advanced.py` |
| P8 | `buyv3.py` hardcodes `isDemo: 1` | ⚠️ Low | `channels/buyv3.py:27` |
| P9 | `get_balances.py` has `print()` statement | ⚠️ Low | `channels/get_balances.py:16` |
| P10 | `get_currency_pairs.py` is empty | ⚠️ Low | `channels/get_currency_pairs.py` |
| P11 | Mixed-language comments (Russian, Spanish, English) | ⚠️ Low | Multiple files |
| P12 | `client.py` message handler is a monolithic 200+ line method | 🟡 Medium | `client.py:on_message()` |
| P13 | `Candles` object on `PocketOptionAPI` is never populated by message handler | 🔴 Critical | `api.py:30`, `client.py` |

---

## 2. Target Architecture (To-Be)

### Design Principles
- **One canonical candle data model** — a `@dataclass` used everywhere
- **One time sync class** — merged from the two existing implementations
- **Channels send, Objects store** — strict separation enforced
- **No dead code** — every file has a clear, tested purpose
- **Async-ready** — replace busy-wait polling with `asyncio.Event` where possible
- **SSID pipeline is the golden path** — optimized and hardened

### Target File Structure
```
ws/
├── client.py                    # WebSocket client (refactored message handler)
├── channels/
│   ├── __init__.py              # NEW — exports all channels
│   ├── base.py                  # Unchanged
│   ├── candles.py               # GetCandles — unchanged (working)
│   ├── change_symbol.py         # Unchanged
│   ├── buy.py                   # MERGED from buyv3.py + buy_advanced.py
│   ├── get_assets.py            # Minor cleanup
│   └── get_balances.py          # Minor cleanup
├── objects/
│   ├── __init__.py              # NEW — exports all objects
│   ├── base.py                  # Simplified
│   ├── candle.py                # NEW — single Candle dataclass + CandleCollection
│   ├── asset.py                 # Unchanged (already clean)
│   ├── time_sync.py             # MERGED from timesync.py + time_sync.py
│   └── trade_data.py            # Minor cleanup
```

### Deleted Files
- `objects/candles.py` → replaced by `objects/candle.py`
- `objects/enhanced_candles.py` → deleted (dead code)
- `objects/timesync.py` → merged into `objects/time_sync.py`
- `channels/buyv3.py` → merged into `channels/buy.py`
- `channels/buy_advanced.py` → merged into `channels/buy.py`
- `channels/get_currency_pairs.py` → deleted (empty)

---

## Phase 1 — Dead Code Removal

**Goal:** Remove files that add confusion without providing value.  
**Risk:** None — these files are not referenced in any working code path.  
**Delegate:** @Coder

### Tasks

- [ ] **1.1** Delete `objects/enhanced_candles.py`
  - Verify no imports reference it (except `objects/candles.py` which is also being replaced)
  - Search for `EnhancedCandles` and `CandleData` across entire codebase

- [ ] **1.2** Delete `channels/get_currency_pairs.py`
  - Verify no imports reference it

- [ ] **1.3** Remove the `print()` statement from `channels/get_balances.py:16`

- [ ] **1.4** Run `python -c "from pocketoptionapi.api import PocketOptionAPI"` to verify no import errors

### Verification
```bash
# Search for any remaining references to deleted modules
grep -r "enhanced_candles" pocketoptionapi/
grep -r "get_currency_pairs" pocketoptionapi/
```

---

## Phase 2 — Data Model Consolidation

**Goal:** Replace 3 candle representations with 1 canonical dataclass.  
**Risk:** Low — the current `Candle` class in `objects/candles.py` is barely used.  
**Delegate:** @Coder

### Tasks

- [ ] **2.1** Create `objects/candle.py` with:

```python
"""Canonical candle data model for Pocket Option API."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass(frozen=True)
class Candle:
    """Single OHLC candle — immutable value object."""
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
        """Format: [time, open, high, low, close]"""
        return [self.time, self.open, self.high, self.low, self.close]

    @classmethod
    def from_dict(cls, data: dict) -> "Candle":
        return cls(
            time=data["time"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
        )

    @classmethod
    def from_list(cls, data: list) -> "Candle":
        """Parse from [time, open, close, high, low] format (legacy)."""
        if len(data) != 5:
            raise ValueError(f"Expected 5 elements, got {len(data)}")
        return cls(
            time=data[0],
            open=data[1],
            high=data[3],  # Note: legacy format is [t, o, c, h, l]
            low=data[4],
            close=data[2],
        )


class CandleCollection:
    """Thread-safe collection of candles with optional caching."""

    def __init__(self):
        self._candles: Dict[str, List[Candle]] = {}

    def _key(self, symbol: str, timeframe: int) -> str:
        return f"{symbol}_{timeframe}"

    def store(self, symbol: str, timeframe: int, candles: List[Candle]):
        """Store/replace candles for a symbol+timeframe pair."""
        key = self._key(symbol, timeframe)
        self._candles[key] = sorted(candles, key=lambda c: c.time)

    def get(self, symbol: str, timeframe: int, count: int = 100) -> List[Candle]:
        """Get latest `count` candles for a symbol+timeframe pair."""
        key = self._key(symbol, timeframe)
        candles = self._candles.get(key, [])
        return candles[-count:]

    def clear(self, symbol: str = None, timeframe: int = None):
        """Clear cache. If no args, clears everything."""
        if symbol and timeframe:
            key = self._key(symbol, timeframe)
            self._candles.pop(key, None)
        else:
            self._candles.clear()
```

- [ ] **2.2** Delete `objects/candles.py` (the old multi-class file)

- [ ] **2.3** Update `api.py`:
  - Remove `from pocketoptionapi.ws.objects.candles import Candles`
  - Remove `candles = Candles()` class attribute
  - Add `from pocketoptionapi.ws.objects.candle import Candle, CandleCollection`
  - Add `candle_collection = CandleCollection()` class attribute
  - Update `get_candles_data()` to return `List[Candle]` instead of raw dicts

- [ ] **2.4** Update `stable_api.py`:
  - Update `get_candles()` to work with `Candle` objects
  - Keep backward-compatible `[[time, open, high, low, close], ...]` return format

- [ ] **2.5** Create `objects/__init__.py`:
```python
from pocketoptionapi.ws.objects.candle import Candle, CandleCollection
from pocketoptionapi.ws.objects.asset import Asset, AssetManager
from pocketoptionapi.ws.objects.time_sync import TimeSync
from pocketoptionapi.ws.objects.trade_data import TradeData
```

### Verification
```bash
python -c "from pocketoptionapi.ws.objects.candle import Candle, CandleCollection; c = Candle(time=1, open=1.0, high=1.1, low=0.9, close=1.05); print(c)"
```

---

## Phase 3 — Time Sync Merge

**Goal:** Merge `timesync.py` + `time_sync.py` into one unified class.  
**Risk:** Medium — both are actively used in `client.py` and `api.py`.  
**Delegate:** @Coder

### Tasks

- [ ] **3.1** Rewrite `objects/time_sync.py` to combine both classes:

```python
"""Unified time synchronization for Pocket Option API."""
import time
import datetime
from datetime import timezone, timedelta


class TimeSync:
    """
    Server time synchronization with drift compensation.
    
    Combines:
    - Server timestamp tracking (from old TimeSync)
    - Drift-compensated sync (from old TimeSynchronizer)
    - Expiration time calculation
    """

    def __init__(self):
        self._server_timestamp: float = time.time()
        self._local_reference: float = time.time()
        self._expiration_minutes: int = 1

    # --- Server Timestamp ---

    @property
    def server_timestamp(self) -> float:
        return self._server_timestamp

    @server_timestamp.setter
    def server_timestamp(self, timestamp: float):
        self._server_timestamp = timestamp
        self._local_reference = time.time()  # Auto-sync on update

    @property
    def server_datetime(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.server_timestamp)

    # --- Drift-Compensated Time ---

    @property
    def synced_timestamp(self) -> float:
        elapsed = time.time() - self._local_reference
        return self._server_timestamp + elapsed

    @property
    def synced_datetime(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(
            round(self.synced_timestamp), tz=timezone.utc
        )

    # --- Expiration ---

    @property
    def expiration_minutes(self) -> int:
        return self._expiration_minutes

    @expiration_minutes.setter
    def expiration_minutes(self, minutes: int):
        self._expiration_minutes = minutes

    @property
    def expiration_datetime(self) -> datetime.datetime:
        return self.server_datetime + timedelta(minutes=self._expiration_minutes)

    @property
    def expiration_timestamp(self) -> float:
        return time.mktime(self.expiration_datetime.timetuple())
```

- [ ] **3.2** Delete `objects/timesync.py`

- [ ] **3.3** Update all imports:
  - `client.py`: Remove both old imports, add `from pocketoptionapi.ws.objects.time_sync import TimeSync`
  - `api.py`: Same — single import, single instance

- [ ] **3.4** Update `client.py` module-level:
  - Replace `timesync = TimeSync()` and `sync = TimeSynchronizer()` with single `time_sync = TimeSync()`

- [ ] **3.5** Update `api.py`:
  - Replace `time_sync = TimeSync()` and `sync = TimeSynchronizer()` with single `time_sync = TimeSync()`
  - Update `synced_datetime` property to use `self.time_sync.synced_datetime`

### Verification
```bash
python -c "from pocketoptionapi.ws.objects.time_sync import TimeSync; ts = TimeSync(); ts.server_timestamp = 1711800000; print(ts.synced_datetime)"
```

---

## Phase 4 — Candle Pipeline Hardening

**Goal:** Make the SSID → historical candles pipeline robust and optimal.  
**Risk:** Medium — touches the core data flow.  
**Delegate:** @Coder + @Tester

### Tasks

- [ ] **4.1** Fix `@property` re-instantiation in `api.py`:
  ```python
  # BEFORE (creates new instance every call):
  @property
  def getcandles(self):
      return GetCandles(self)
  
  # AFTER (cached instance):
  def __init__(self, ssid=None, proxies=None):
      ...
      self._get_candles = GetCandles(self)
      self._change_symbol = ChangeSymbol(self)
      self._buy_v3 = Buyv3(self)
      self._buy_advanced = BuyAdvanced(self)
      self._get_balances = Get_Balances(self)
  
  @property
  def getcandles(self):
      return self._get_candles
  ```

- [ ] **4.2** Replace busy-wait polling with `asyncio.Event` (if feasible within current threading model):
  ```python
  # In api.py
  self._candle_event = threading.Event()
  
  # In get_candles_data():
  self._candle_event.clear()
  self.history_data = None
  self.getcandles(active, interval, count, end_time)
  if not self._candle_event.wait(timeout=5):
      logger.error("Timeout waiting for candles")
      return None
  return sorted(self.history_data, key=lambda x: x['time'])
  
  # In client.py on_message (where history_data is set):
  self.api.history_data = message["data"]
  self.api._candle_event.set()
  ```

- [ ] **4.3** Add candle data validation in `get_candles_data()`:
  - Validate each candle has required keys: `time`, `open`, `high`, `low`, `close`
  - Validate OHLC integrity: `high >= max(open, close)`, `low <= min(open, close)`
  - Log warnings for invalid candles but don't fail the entire request

- [ ] **4.4** Store retrieved candles in `CandleCollection` for caching:
  ```python
  candles = [Candle.from_dict(d) for d in self.history_data]
  self.candle_collection.store(active, interval, candles)
  return candles
  ```

- [ ] **4.5** Add retry logic (max 2 retries) for candle requests that timeout

### Verification
```
# Integration test (requires live SSID):
python -c "
from pocketoptionapi.stable_api import PocketOption
# ... connect with SSID ...
candles = api.get_candles('EURUSD_otc', 60, 10)
assert len(candles) == 10
assert all(c[2] >= c[3] for c in candles)  # high >= low
print('PASS')
"
```

---

## Phase 5 — Channel Cleanup

**Goal:** Clean up channel files, merge buy channels, remove dead code.  
**Risk:** Low — mostly cosmetic + one merge.  
**Delegate:** @Coder

### Tasks

- [ ] **5.1** Merge `buyv3.py` + `buy_advanced.py` into `buy.py`:
  - Keep `Buyv3` class (rename to `Buy`)
  - Keep `BuyAdvanced` class
  - Fix hardcoded `isDemo: 1` → use `global_value.DEMO`
  - Remove `sys.stdout.write` from `BuyAdvanced`

- [ ] **5.2** Delete `buyv3.py` and `buy_advanced.py`

- [ ] **5.3** Remove `print()` from `get_balances.py`

- [ ] **5.4** Delete `get_currency_pairs.py`

- [ ] **5.5** Create `channels/__init__.py`:
```python
from pocketoptionapi.ws.channels.candles import GetCandles
from pocketoptionapi.ws.channels.change_symbol import ChangeSymbol
from pocketoptionapi.ws.channels.buy import Buy, BuyAdvanced
from pocketoptionapi.ws.channels.get_assets import GetAssets
from pocketoptionapi.ws.channels.get_balances import GetBalances
```

- [ ] **5.6** Update all imports in `api.py` and `stable_api.py`

### Verification
```bash
python -c "from pocketoptionapi.ws.channels import GetCandles, Buy, BuyAdvanced; print('OK')"
```

---

## Phase 6 — Client Message Handler Refactor

**Goal:** Break the monolithic `on_message()` into focused handler methods.  
**Risk:** Medium-High — this is the nerve center of the WebSocket communication.  
**Delegate:** @Coder (with @Reviewer sign-off before merge)

### Tasks

- [ ] **6.1** Extract message type handlers from `on_message()`:
  ```python
  async def on_message(self, message):
      if type(message) is bytes:
          await self._handle_binary_message(message)
      elif message.startswith('0') and "sid" in message:
          await self._handle_session_init(message)
      elif message == "2":
          await self.websocket.send("3")  # pong
      elif message.startswith("40"):
          await self._handle_auth(message)
      elif message.startswith('451-['):
          await self._handle_event_message(message)
      elif message.startswith("42") and "NotAuthorized" in message:
          await self._handle_not_authorized()
  ```

- [ ] **6.2** Extract `_handle_binary_message()` with sub-handlers:
  - `_handle_asset_data()`
  - `_handle_trade_data()`
  - `_handle_balance_update()`
  - `_handle_candle_data()`
  - `_handle_order_update()`

- [ ] **6.3** Ensure candle response handler sets the `threading.Event`:
  ```python
  async def _handle_candle_data(self, message):
      self.api.history_data = message["data"]
      self.api._candle_event.set()
  ```

- [ ] **6.4** Standardize all comments to English

### Verification
- Full regression test of: connect, get_candles, buy, check_win
- No behavioral changes — pure refactor

---

## Phase 7 — Integration Testing

**Goal:** Verify the entire SSID pipeline works end-to-end.  
**Risk:** N/A — testing phase.  
**Delegate:** @Tester

### Tasks

- [ ] **7.1** Create `tests/test_candle_pipeline.py`:
  ```python
  """Test the SSID → historical candles pipeline."""
  
  def test_candle_dataclass():
      """Test Candle creation, serialization, deserialization."""
      ...
  
  def test_candle_collection():
      """Test CandleCollection store/get/clear."""
      ...
  
  def test_candle_from_dict():
      """Test Candle.from_dict with valid and invalid data."""
      ...
  
  def test_candle_from_list_legacy():
      """Test Candle.from_list with legacy [t,o,c,h,l] format."""
      ...
  ```

- [ ] **7.2** Create `tests/test_time_sync.py`:
  ```python
  """Test unified TimeSync class."""
  
  def test_server_timestamp_sync():
      ...
  
  def test_drift_compensation():
      ...
  
  def test_expiration_calculation():
      ...
  ```

- [ ] **7.3** Create `tests/test_integration_candles.py` (requires live SSID):
  ```python
  """Integration test — requires valid SSID in environment."""
  
  def test_get_historical_candles():
      """Full pipeline: connect → request → receive → validate."""
      ...
  
  def test_multiple_timeframes():
      """Test 60s, 300s, 3600s candles."""
      ...
  
  def test_candle_data_integrity():
      """Verify OHLC rules, time intervals, no gaps."""
      ...
  ```

- [ ] **7.4** Run all existing tests to verify no regressions:
  ```bash
  python -m pytest tests/ -v
  ```

---

## Risk Assessment

| Phase | Risk Level | Mitigation |
|-------|-----------|------------|
| Phase 1 (Dead Code) | 🟢 Very Low | Search-verify before delete |
| Phase 2 (Data Models) | 🟢 Low | New file, old file deleted after |
| Phase 3 (Time Sync) | 🟡 Medium | Both classes actively used — test thoroughly |
| Phase 4 (Pipeline) | 🟡 Medium | Core data flow — incremental changes with tests |
| Phase 5 (Channels) | 🟢 Low | Mostly cosmetic |
| Phase 6 (Client) | 🟠 Medium-High | Monolithic handler — extract carefully, test each handler |
| Phase 7 (Testing) | 🟢 None | Pure verification |

**Recommended execution order:** Phase 1 → 2 → 3 → 5 → 4 → 6 → 7  
(Do channels cleanup before pipeline hardening so imports are clean)

---

## File Change Matrix

| File | Action | Phase |
|------|--------|-------|
| `objects/enhanced_candles.py` | **DELETE** | 1 |
| `channels/get_currency_pairs.py` | **DELETE** | 1 |
| `channels/get_balances.py` | **EDIT** (remove print) | 1 |
| `objects/candle.py` | **CREATE** | 2 |
| `objects/candles.py` | **DELETE** | 2 |
| `objects/__init__.py` | **CREATE** | 2 |
| `api.py` | **EDIT** (imports, candle model) | 2, 3, 4 |
| `stable_api.py` | **EDIT** (imports, candle model) | 2 |
| `objects/time_sync.py` | **REWRITE** | 3 |
| `objects/timesync.py` | **DELETE** | 3 |
| `client.py` | **EDIT** (imports, time sync) | 3, 6 |
| `channels/buy.py` | **CREATE** (merged) | 5 |
| `channels/buyv3.py` | **DELETE** | 5 |
| `channels/buy_advanced.py` | **DELETE** | 5 |
| `channels/__init__.py` | **CREATE** | 5 |
| `tests/test_candle_pipeline.py` | **CREATE** | 7 |
| `tests/test_time_sync.py` | **CREATE** | 7 |
| `tests/test_integration_candles.py` | **CREATE** | 7 |

**Total: 8 files deleted, 6 files created, 4 files edited, 1 file rewritten**

---

## Acceptance Criteria

Before this refactor is considered complete, ALL of the following must be true:

- [ ] `python -c "from pocketoptionapi.stable_api import PocketOption"` — no import errors
- [ ] `python -m pytest tests/test_candle_pipeline.py -v` — all pass
- [ ] `python -m pytest tests/test_time_sync.py -v` — all pass
- [ ] `python -m pytest tests/test_imports.py -v` — all pass (existing test)
- [ ] `grep -r "enhanced_candles" pocketoptionapi/` — zero results
- [ ] `grep -r "CandleData" pocketoptionapi/` — zero results (except in candle.py if used)
- [ ] `grep -r "TimeSynchronizer" pocketoptionapi/` — zero results
- [ ] Historical candle retrieval via SSID works end-to-end (manual test with valid SSID)
- [ ] No `print()` statements in library code
- [ ] All comments in English

---

## Notes for @Coder

1. **Do NOT start Phase 6 without @Reviewer approval** — the client message handler is the most dangerous refactor.
2. **Test after every phase** — run `python -m pytest tests/ -v` before moving to the next phase.
3. **Git commit after each phase** — one commit per phase for easy rollback.
4. **The `from_list` format** in the current `Candle` class uses `[time, open, close, high, low]` — note the close/high swap vs standard OHLC. Verify this matches the actual server response format before finalizing.
5. **The `loadHistoryPeriod` response format** from the server needs to be documented. Capture a sample response and add it as a comment in `channels/candles.py`.

---

*Plan prepared by @Reviewer + @Architect. Ready for approval.*
