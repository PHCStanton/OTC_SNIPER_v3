# SSID Integration Package — Complete Integration Guide

**Version:** 2.0.0  
**Date:** 2026-03-24  
**Status:** Production-Ready (Multi-Agent Reviewed & Approved)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Fresh Integration (New Project)](#4-fresh-integration-new-project)
5. [Migration Guide (Replacing Old SSID System)](#5-migration-guide-replacing-old-ssid-system)
6. [API Reference](#6-api-reference)
7. [Configuration](#7-configuration)
8. [Usage Examples](#8-usage-examples)
9. [Error Handling](#9-error-handling)
10. [Troubleshooting](#10-troubleshooting)
11. [Known Limitations](#11-known-limitations)
12. [Changelog — What Was Fixed](#12-changelog--what-was-fixed)

---

## 1. Overview

The `ssid_integration_package` provides a clean, single-entry-point session manager for connecting to the Pocket Option trading API via WebSocket using SSID authentication.

### What This Package Does

- **Validates and parses** your SSID string once (no redundant parsing)
- **Manages the full WebSocket lifecycle** — connect, authenticate, trade, disconnect
- **Enables clean account switching** between DEMO and REAL accounts
- **Resets all global state** on disconnect (no stale data contamination)
- **Provides backward compatibility** for projects using the old `SSIDConnector` API

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `PocketOptionSession` | `core/session.py` | **Primary API** — use this for new projects |
| `SSIDConnector` | `core/ssid_connector.py` | Backward-compatible wrapper (delegates to `PocketOptionSession`) |
| `OTCExecutor` | `core/otc_executor.py` | Trade execution helper with validated OTC asset list |

---

## 2. Architecture

```
PocketOptionSession(ssid)               ← Single entry point (new projects)
  ├── _parse_ssid()                     ← Validates SSID format ONCE, raises SSIDParseError
  ├── _is_demo                          ← Extracted once from SSID, stored as instance var
  ├── connect()                         ← Full lifecycle: reset → auth → balance wait
  ├── disconnect()                      ← Calls reset_all(), clears all instance state
  ├── switch_account(new_ssid)          ← Fail-fast parse → disconnect → reconnect
  ├── get_balance()                     ← Cached balance with live refresh
  ├── buy() / buy_advanced()            ← Trade execution
  ├── get_candles()                     ← Historical data
  └── check_win()                       ← Order result checking

SSIDConnector(ssid, demo)               ← Backward-compatible wrapper (existing projects)
  └── delegates to PocketOptionSession  ← 'demo' param is IGNORED (read from SSID)

Internal layers (you don't touch these):
  PocketOption (stable_api.py)          ← High-level API wrapper
    └── PocketOptionAPI (api.py)        ← Core API + WebSocket management
          └── WebsocketClient (ws/client.py) ← WebSocket protocol handler
                └── global_value.py     ← Shared state (with reset_all() / reset_trading_state())
```

### Design Principles

1. **Single source of truth** — SSID is parsed exactly once in `PocketOptionSession.__init__()`
2. **Fail fast** — Malformed SSIDs raise `SSIDParseError` immediately (no silent fallback)
3. **Clean state transitions** — `reset_all()` guarantees no stale data between sessions
4. **Account type from SSID** — `isDemo` is read from the SSID payload, not from a separate parameter

---

## 3. Prerequisites

### Python Version
- Python 3.8+

### Required Dependencies
```
websockets
requests
pandas
tzlocal
```

### Install Dependencies
```bash
pip install websockets requests pandas tzlocal
```

### Obtaining Your SSID

1. Log in to [Pocket Option](https://pocketoption.com) in your browser
2. Open Developer Tools (`F12` or `Ctrl+Shift+I`)
3. Go to the **Network** tab → filter by **WS** (WebSocket)
4. Look for the WebSocket connection to `po.market`
5. In the **Messages** tab, find the message starting with `42["auth",{...}]`
6. Copy the **entire message** — this is your SSID

**SSID Format:**
```
42["auth",{"session":"abc123...","isDemo":1,"uid":12345,"platform":2}]
```

- `isDemo: 1` = DEMO account
- `isDemo: 0` = REAL account (⚠️ real money)

---

## 4. Fresh Integration (New Project)

### Step 1: Copy the Package

Copy the entire `ssid_integration_package/` directory into your project:

```
your_project/
├── ssid_integration_package/          ← Copy this entire folder
│   ├── core/
│   │   ├── session.py                 ← PocketOptionSession (primary API)
│   │   ├── ssid_connector.py          ← Backward-compatible wrapper
│   │   └── otc_executor.py            ← Trade execution helper
│   ├── pocketoptionapi/               ← Internal API layer
│   │   ├── api.py
│   │   ├── stable_api.py
│   │   ├── global_value.py
│   │   ├── constants.py
│   │   ├── expiration.py
│   │   └── ws/
│   │       ├── client.py
│   │       ├── channels/
│   │       └── objects/
│   ├── config/
│   │   └── config_template.json
│   └── examples/
│       ├── basic_connection.py
│       └── simple_trade.py
├── your_code.py
└── ...
```

### Step 2: Basic Connection

```python
from ssid_integration_package.core.session import PocketOptionSession

# Your SSID string (from browser dev tools)
ssid = '42["auth",{"session":"your_session_here","isDemo":1,"uid":12345,"platform":2}]'

# Create session — SSID is validated immediately
session = PocketOptionSession(ssid)

# Connect (blocking, with timeout)
success, message = session.connect()

if success:
    print(f"Connected to {session.account_type}")
    print(f"Balance: ${session.get_balance():,.2f}")
else:
    print(f"Connection failed: {message}")

# Always disconnect when done
session.disconnect()
```

### Step 3: Using Context Manager (Recommended)

```python
from ssid_integration_package.core.session import PocketOptionSession

ssid = '42["auth",{"session":"...","isDemo":1,"uid":12345,"platform":2}]'

with PocketOptionSession(ssid) as session:
    print(f"Balance: ${session.get_balance():,.2f}")
    
    # Place a trade
    result, order_id = session.buy(
        amount=5.0,
        active="EURUSD_otc",
        action="call",
        expirations=300
    )
    
    if result:
        print(f"Trade placed! Order ID: {order_id}")
        
        # Check result after expiration
        import time
        time.sleep(310)
        profit, status = session.check_win(order_id)
        print(f"Result: {status} — Profit: ${profit}")

# Auto-disconnects and cleans up on exit
```

### Step 4: Account Switching

```python
from ssid_integration_package.core.session import PocketOptionSession

demo_ssid = '42["auth",{"session":"...","isDemo":1,...}]'
real_ssid = '42["auth",{"session":"...","isDemo":0,...}]'

session = PocketOptionSession(demo_ssid)
session.connect()
print(f"Demo balance: ${session.get_balance():,.2f}")

# Switch to real account (full disconnect → reconnect cycle)
success, msg = session.switch_account(real_ssid)
if success:
    print(f"Real balance: ${session.get_balance():,.2f}")

# Switch back to demo
session.switch_account(demo_ssid)

session.disconnect()
```

### Step 5: Using OTCExecutor for Validated Trading

```python
from ssid_integration_package.core.session import PocketOptionSession
from ssid_integration_package.core.ssid_connector import SSIDConnector
from ssid_integration_package.core.otc_executor import OTCExecutor

ssid = '42["auth",{"session":"...","isDemo":1,...}]'

# OTCExecutor requires SSIDConnector (not PocketOptionSession directly)
connector = SSIDConnector(ssid)
success, msg = connector.connect()

if success:
    executor = OTCExecutor(connector)
    
    # Lists only verified working OTC assets
    print("Available assets:", executor.get_available_assets())
    
    # Execute trade with full validation
    result = executor.execute_trade(
        asset="EURUSD_otc",
        direction="call",
        amount=5.0,
        expiration=300
    )
    
    if result['success']:
        print(f"Trade executed: {result['message']}")
    else:
        print(f"Trade failed: {result['error']}")

connector.disconnect()
```

---

## 5. Migration Guide (Replacing Old SSID System)

If your existing project uses the old SSID authentication system (direct `PocketOption` instantiation, old `SSIDConnector`, or the legacy `pocket.py` approach), follow this guide to migrate.

### 5.1 Identify What You're Replacing

**Old patterns to look for in your codebase:**

```python
# Pattern A: Direct PocketOption usage
from pocketoptionapi.stable_api import PocketOption
api = PocketOption(ssid, demo=True)
api.connect()

# Pattern B: Old SSIDConnector with demo parameter
from ssid_connector import SSIDConnector
connector = SSIDConnector(ssid, demo=True)

# Pattern C: Legacy pocket.py
from pocketoptionapi.pocket import PocketOp
# (completely different library — must be fully replaced)

# Pattern D: Manual SSID parsing
def parse_demo_status(ssid):
    # ... custom parsing logic ...
    
# Pattern E: Direct global_value manipulation
import pocketoptionapi.global_value as global_value
global_value.SSID = ssid
global_value.DEMO = True
```

### 5.2 Migration Path by Pattern

#### Pattern A → PocketOptionSession (Recommended)

**Before:**
```python
from pocketoptionapi.stable_api import PocketOption
import pocketoptionapi.global_value as global_value

# Manual global state setup
global_value.SSID = ssid
global_value.DEMO = True

api = PocketOption(ssid)
api.connect()

# ... trading ...

# No cleanup — stale state remains!
```

**After:**
```python
from ssid_integration_package.core.session import PocketOptionSession

session = PocketOptionSession(ssid)  # Auto-detects DEMO/REAL from SSID
success, msg = session.connect()     # Handles all global state internally

# ... trading via session.buy(), session.get_balance(), etc. ...

session.disconnect()  # Cleans up ALL global state
```

#### Pattern B → SSIDConnector (Drop-in Compatible)

If you're already using `SSIDConnector`, the new version is a **drop-in replacement**. The only behavioral change is that the `demo` parameter is now **ignored** — account type is always read from the SSID's `isDemo` field.

**Before:**
```python
from old_package.ssid_connector import SSIDConnector
connector = SSIDConnector(ssid, demo=True)  # 'demo' could contradict SSID
```

**After:**
```python
from ssid_integration_package.core.ssid_connector import SSIDConnector
connector = SSIDConnector(ssid, demo=True)  # 'demo' is accepted but IGNORED
# Account type is determined by isDemo in the SSID string itself
```

> **⚠️ Important:** If your old code relied on the `demo` parameter to override the SSID's `isDemo` value, you must now ensure your SSID string has the correct `isDemo` value. The `demo` parameter exists only for backward compatibility and has no effect.

#### Pattern C → Full Replacement Required

The legacy `pocket.py` (Vigo Walker implementation) used a completely different library and protocol. There is no compatibility layer.

**Action:** Delete all references to `pocket.py` / `PocketOp` and replace with `PocketOptionSession`.

#### Pattern D → Delete Custom Parsing

All custom `parse_demo_status()` functions are now redundant. `PocketOptionSession._parse_ssid()` handles all validation and parsing.

**Action:** Delete your custom parsing functions and rely on `PocketOptionSession`.

#### Pattern E → Stop Manipulating global_value Directly

`PocketOptionSession` manages all global state internally. Direct manipulation of `global_value` will cause conflicts.

**Action:** Remove all direct `global_value.SSID = ...` and `global_value.DEMO = ...` assignments. Let `PocketOptionSession.connect()` handle it.

### 5.3 Step-by-Step Migration Checklist

```
□ 1. Copy ssid_integration_package/ into your project
□ 2. Search your codebase for old import patterns:
      - grep for: "from pocketoptionapi.pocket import"
      - grep for: "parse_demo_status"
      - grep for: "global_value.SSID ="
      - grep for: "global_value.DEMO ="
      - grep for: "from.*ssid_connector import SSIDConnector"
□ 3. Replace all old imports with new ones:
      - from ssid_integration_package.core.session import PocketOptionSession
      - from ssid_integration_package.core.ssid_connector import SSIDConnector
□ 4. Remove any manual global_value manipulation
□ 5. Remove any custom SSID parsing functions
□ 6. Delete old files that are no longer needed:
      - pocket.py (legacy implementation)
      - ws/channels/ssid.py (dead code)
      - ws/chanels/ (typo duplicate folder)
      - Any custom ssid_connector.py from the old system
□ 7. Update your disconnect logic to use session.disconnect()
      (ensures global state is properly reset)
□ 8. Test connection with a DEMO SSID first
□ 9. Test account switching if your app supports it
□ 10. Test with REAL SSID (small amounts)
```

### 5.4 Files to Delete from Old System

If your project contains any of these files from the old SSID system, they should be removed:

| File | Reason |
|------|--------|
| `pocket.py` | Legacy implementation — completely separate codebase |
| `ws/channels/ssid.py` | Dead code — `Ssid` class was never actually used |
| `ws/chanels/` (entire folder) | Typo duplicate of `ws/channels/` |
| Any `parse_demo_status()` functions | Redundant — parsing is centralized in `PocketOptionSession` |
| Any `get_ws_url()` methods | Redundant — URL resolution is handled by `client.py` via `global_value.DEMO` |

### 5.5 Breaking Changes to Be Aware Of

| Change | Impact | Mitigation |
|--------|--------|------------|
| `demo` parameter on `SSIDConnector` is ignored | Code that relied on `demo=True` overriding a REAL SSID will now connect to REAL | Ensure your SSID has the correct `isDemo` value |
| Malformed SSIDs now raise `SSIDParseError` | Code that silently fell back to REAL on parse failure will now crash | Add try/except for `SSIDParseError` at initialization |
| `global_value` is fully reset on disconnect | Code that read global state after disconnect will get `None` values | Read balance/state before calling `disconnect()` |
| No more triple-parsing of SSID | Shouldn't affect anything, but internal state flow is different | Test thoroughly |

---

## 6. API Reference

### PocketOptionSession

```python
from ssid_integration_package.core.session import PocketOptionSession, SSIDParseError, ConnectionError
```

#### Constructor

```python
PocketOptionSession(ssid: str, timeout: int = 15)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ssid` | `str` | required | Full SSID string starting with `42["auth",{...}]` |
| `timeout` | `int` | `15` | Connection timeout in seconds |

**Raises:** `SSIDParseError` if SSID format is invalid.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_demo` | `bool` | Whether this is a DEMO account |
| `is_connected` | `bool` | Whether WebSocket is currently connected |
| `account_type` | `str` | `"DEMO"` or `"REAL"` |

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `connect()` | `Tuple[bool, str]` | Connect to Pocket Option. Returns `(success, message)` |
| `disconnect()` | `bool` | Disconnect and reset all state |
| `switch_account(new_ssid)` | `Tuple[bool, str]` | Switch to different account (full cycle) |
| `get_balance()` | `Optional[float]` | Get current balance (cached with live refresh) |
| `buy(amount, active, action, expirations)` | `Tuple[bool, int]` | Place a trade |
| `buy_advanced(amount, active, action, expirations, on_new_candle)` | `Tuple[bool, int]` | Place advanced trade |
| `get_candles(active, timeframe, count)` | `list` | Get historical candles |
| `check_win(order_id)` | `Tuple[float, str]` | Check trade result |

#### Context Manager

```python
with PocketOptionSession(ssid) as session:
    # session is connected and authenticated
    balance = session.get_balance()
# auto-disconnects on exit
```

### SSIDConnector (Backward-Compatible)

```python
from ssid_integration_package.core.ssid_connector import SSIDConnector
```

| Method | Returns | Description |
|--------|---------|-------------|
| `connect()` | `Tuple[bool, str]` | Connect via PocketOptionSession |
| `disconnect()` | `bool` | Disconnect and clean up |
| `check_connection()` | `bool` | Check if session is active |
| `get_balance()` | `Optional[float]` | Get current balance |
| `update_balance()` | `Optional[float]` | Force refresh balance |

### Exceptions

| Exception | Raised When |
|-----------|-------------|
| `SSIDParseError` | SSID string is malformed, missing fields, or invalid format |
| `ConnectionError` | WebSocket connection fails or trade attempted while disconnected |

---

## 7. Configuration

### Config Template

Copy `config/config_template.json` to `config/pocket_option_config.json` and fill in your SSID:

```json
{
  "ssid": "42[\"auth\",{\"session\":\"YOUR_REAL_SSID_HERE\",\"isDemo\":1,\"uid\":12345,\"platform\":2}]",
  "demo": false,
  "default_asset": "EURUSD_otc",
  "default_amount": 10.0,
  "default_expiration": 300
}
```

> **Note:** The `demo` field in config is for your reference only. The actual account type is always determined by the `isDemo` field inside the SSID string.

### SSID Refresh

SSIDs expire periodically. When your connection fails with authentication errors:

1. Log back into Pocket Option in your browser
2. Extract the new SSID from WebSocket messages (see [Prerequisites](#3-prerequisites))
3. Update your config file with the new SSID

---

## 8. Usage Examples

### Basic Connection & Balance Check

```python
from ssid_integration_package.core.session import PocketOptionSession

session = PocketOptionSession(ssid)
success, msg = session.connect()

if success:
    print(f"{session.account_type} account")
    print(f"Balance: ${session.get_balance():,.2f}")
    session.disconnect()
```

### Place a Trade

```python
with PocketOptionSession(ssid) as session:
    # Buy CALL on EURUSD OTC, $10, 5-minute expiry
    result, order_id = session.buy(10, "EURUSD_otc", "call", 300)
    
    if result:
        print(f"Order placed: {order_id}")
        
        # Wait for result
        import time
        time.sleep(310)
        
        profit, status = session.check_win(order_id)
        print(f"{status}: ${profit}")
```

### Account Switching (DEMO ↔ REAL)

```python
session = PocketOptionSession(demo_ssid)
session.connect()

# Trade on demo...
session.buy(5, "EURUSD_otc", "call", 60)

# Switch to real
success, msg = session.switch_account(real_ssid)
if success:
    print(f"Now on REAL: ${session.get_balance():,.2f}")

session.disconnect()
```

### Get Historical Candles

```python
with PocketOptionSession(ssid) as session:
    candles = session.get_candles("EURUSD_otc", 60, 100)
    # Returns: [[time, open, high, low, close], ...]
    
    for candle in candles[-5:]:
        print(f"Time: {candle[0]}, O: {candle[1]}, H: {candle[2]}, L: {candle[3]}, C: {candle[4]}")
```

### Error Handling

```python
from ssid_integration_package.core.session import (
    PocketOptionSession, SSIDParseError, ConnectionError
)

try:
    session = PocketOptionSession(ssid)
except SSIDParseError as e:
    print(f"Invalid SSID: {e}")
    # SSID format is wrong — fix it before retrying
    exit(1)

success, msg = session.connect()
if not success:
    print(f"Connection failed: {msg}")
    exit(1)

try:
    result, order_id = session.buy(10, "EURUSD_otc", "call", 300)
except ConnectionError:
    print("Lost connection during trade")
finally:
    session.disconnect()
```

---

## 9. Error Handling

### SSIDParseError — Common Causes

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `SSID must be a non-empty string` | Empty or None SSID passed | Check your config file |
| `SSID must start with '42['` | Missing protocol prefix | Ensure you copied the full WebSocket message |
| `SSID JSON is malformed` | Corrupted or truncated SSID | Re-extract from browser |
| `SSID missing required fields: ['session']` | Incomplete auth payload | Ensure SSID contains `session` and `isDemo` fields |

### Connection Failures

| Message | Cause | Fix |
|---------|-------|-----|
| `Connection timeout after 15s` | Server unreachable or SSID expired | Check internet; refresh SSID |
| `Authentication failed — no balance received` | SSID expired or invalid | Get a fresh SSID from browser |
| `Failed to start WebSocket connection` | Network/firewall issue | Check firewall rules for WSS connections |

### Trade Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ConnectionError: Not connected` | Trade attempted without active connection | Call `session.connect()` first |
| `Asset not in verified OTC list` | Using non-OTC or unverified asset | Use assets from `OTCExecutor.OTC_ASSETS` |
| `Insufficient balance` | Trade amount exceeds balance | Reduce amount or top up account |

---

## 10. Troubleshooting

### Connection Issues

**Problem:** `Connection timeout after 15s`
```python
# Increase timeout
session = PocketOptionSession(ssid, timeout=30)
```

**Problem:** Connection works on DEMO but not REAL
- REAL accounts use region rotation (multiple server URLs)
- Check if your network blocks any of the `api-l.po.market` endpoints
- Try from a different network

**Problem:** `NotAuthorized` error in logs
- Your SSID has expired — extract a new one from the browser
- SSIDs typically expire after the browser session ends

### Trading Issues

**Problem:** Trade returns `(False, None)`
- Check `session.is_connected` before trading
- Verify the asset is available (markets close on weekends for non-OTC)
- OTC assets (ending in `_otc`) are available 24/7

**Problem:** `check_win()` times out
- The default timeout is 120 seconds
- For longer expirations, the result may take time to appear
- Ensure the order ID is correct

### State Issues

**Problem:** Stale balance after account switch
- `switch_account()` calls `reset_all()` internally
- If balance appears stale, call `session.get_balance()` to force refresh

**Problem:** Multiple sessions interfering
- The package uses `global_value` (module-level shared state)
- **Only one active session is supported at a time**
- Always `disconnect()` before creating a new session

---

## 11. Known Limitations

1. **Single session only** — Due to shared `global_value` state, only one `PocketOptionSession` can be active at a time. Creating a second session without disconnecting the first will cause conflicts.

2. **Blocking I/O** — `connect()`, `buy()`, and `check_win()` are blocking calls that use `time.sleep()` polling. They are not async-compatible.

3. **SSID expiration** — SSIDs expire when the browser session ends. There is no automatic refresh mechanism. You must manually extract a new SSID.

4. **OTC assets only** — The `OTCExecutor` validates against a hardcoded list of OTC assets. Non-OTC assets may work via `session.buy()` directly but are not validated.

5. **Thread safety** — The `OTCExecutor` has internal locking for thread safety. `PocketOptionSession` itself is not thread-safe — do not call its methods from multiple threads simultaneously.

6. **Custom `ConnectionError`** — The package defines its own `ConnectionError` class that shadows Python's built-in. Import it explicitly from `session.py` to avoid confusion.

---

## 12. Changelog — What Was Fixed

### Bugs Fixed (from Investigation)

| # | Severity | Bug | Fix |
|---|----------|-----|-----|
| 1 | **CRITICAL** | `"40" and "sid" in message` evaluated as `True and ("sid" in message)` — any message with "sid" substring triggered SSID re-send (auth spam) | Changed to `message.startswith("40") and "sid" in message` |
| 2 | **HIGH** | `client.py` computed its own URL with redundant branches (both resolved to same URL), ignoring `api.py`'s computed URL | Removed URL override; `client.py` now reads `global_value.DEMO` directly |
| 3 | **HIGH** | `parse_demo_status()` silently defaulted to REAL account on parse failure (`except: return False`) | `SSIDParseError` raised immediately — no silent fallback |
| 4 | **MEDIUM** | SSID parsed 3 times (SSIDConnector → stable_api → api.py), each setting `global_value.DEMO` | Parsed once in `PocketOptionSession.__init__()`, result passed down |
| 5 | **LOW** | Dead `Ssid` channel class imported but never used | Deleted `ws/channels/ssid.py` and `ws/chanels/` folder |

### Dead Code Removed

| Item | Status |
|------|--------|
| `pocket.py` (legacy Vigo Walker implementation) | ✅ Deleted |
| `ws/channels/ssid.py` (unused Ssid class) | ✅ Deleted |
| `ws/chanels/` (typo duplicate folder) | ✅ Deleted |
| `parse_demo_status()` in `api.py` and `stable_api.py` | ✅ Removed |
| `get_ws_url()` and `self.wss_url` in `api.py` | ✅ Removed |
| Ssid import in `api.py` | ✅ Removed |

### Post-Review Patches Applied

| ID | File | Change |
|----|------|--------|
| D-1 | `session.py` | Added double-call guard to `connect()` — returns early if already connected |
| D-3 | `session.py` | Added warning log to `get_balance()` except block (was silently swallowing errors) |
| R-2 | `session.py` | Removed unused `import asyncio` |
| D-2/S-2 | `stable_api.py` | Added `disconnect()` method to `PocketOption` class |
| R-1/S-1 | `api.py` | Replaced internal SSID parse with `global_value.DEMO`; removed dead `get_ws_url()` |

### New Features

| Feature | Description |
|---------|-------------|
| `PocketOptionSession` | Single-entry-point session manager with full lifecycle control |
| `reset_all()` | Resets ALL global state for clean disconnect/reconnect |
| `reset_trading_state()` | Resets trading state only (preserves connection info) |
| `switch_account()` | Clean DEMO ↔ REAL switching with fail-fast validation |
| Context manager support | `with PocketOptionSession(ssid) as session:` |
| `SSIDParseError` | Explicit error for malformed SSIDs (no more silent failures) |

---

## Quick Reference Card

```python
# === CONNECT ===
from ssid_integration_package.core.session import PocketOptionSession

session = PocketOptionSession(ssid)
success, msg = session.connect()

# === CHECK STATUS ===
session.is_connected    # bool
session.is_demo         # bool
session.account_type    # "DEMO" or "REAL"
session.get_balance()   # float or None

# === TRADE ===
result, order_id = session.buy(amount, "EURUSD_otc", "call", 300)
profit, status = session.check_win(order_id)

# === SWITCH ACCOUNT ===
session.switch_account(other_ssid)

# === DISCONNECT ===
session.disconnect()

# === CONTEXT MANAGER ===
with PocketOptionSession(ssid) as session:
    session.buy(10, "EURUSD_otc", "put", 60)
```

---

*Guide compiled: 2026-03-24*  
*Package version: 2.0.0*  
*Review status: Multi-Agent Reviewed & Approved*
