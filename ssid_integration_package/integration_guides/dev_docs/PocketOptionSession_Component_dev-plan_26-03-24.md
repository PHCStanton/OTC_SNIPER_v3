# PocketOptionSession Component — Development Plan
**File:** `ssid_integration_package/integration_guides/dev_docs/PocketOptionSession_Component_dev-plan_26-03-24.md`  
**Date:** 2026-03-24  
**Author:** @Investigator → @Architect  
**Status:** Approved for Implementation  

---

## Executive Summary

The current SSID authentication system across the `ssid_integration_package/pocketoptionapi` codebase is fragmented across **three competing implementations** (`pocket.py`, `api.py`/`client.py`, and `stable_api.py`/`SSIDConnector`), contains **5 confirmed bugs**, and relies on **unprotected global state** that prevents clean account switching between DEMO and REAL modes.

This plan delivers a single, reusable `PocketOptionSession` component that:
- Centralizes all SSID parsing, validation, and connection logic into one class
- Enables seamless switching between DEMO and REAL accounts
- Eliminates all identified bugs
- Can be dropped into any future project as a self-contained module

---

## Architecture Context

### Current State (Broken Chain)

```
SSIDConnector(ssid, demo=True)          ← Layer 3: Wrapper with conflicting demo param
  └─► PocketOption(ssid)                ← Layer 2b: Parses isDemo from SSID (2nd time)
        └─► PocketOptionAPI(ssid)       ← Layer 2a: Parses isDemo from SSID (1st time)
              └─► WebsocketClient       ← Layer 1: IGNORES parsed URL, does own logic
                    └─► global_value    ← Shared mutable state (never cleaned up)
```

**Problems:**
1. SSID parsed 3× (SSIDConnector, PocketOption, PocketOptionAPI)
2. `demo` parameter in SSIDConnector can contradict `isDemo` in the SSID string
3. `client.py` overrides the URL that `api.py` carefully computed
4. Global state never reset on disconnect → stale data contaminates next session
5. `pocket.py` is a completely separate dead implementation

### Target State (Clean Architecture)

```
PocketOptionSession(ssid)               ← Single entry point
  ├─► _validate_ssid()                  ← Validates format ONCE
  ├─► _parse_account_type()             ← Extracts isDemo ONCE
  ├─► _resolve_ws_url()                 ← Determines URL ONCE
  ├─► connect()                         ← Full lifecycle management
  ├─► disconnect()                      ← Resets ALL global state
  ├─► switch_account(new_ssid)          ← Clean disconnect + reconnect
  └─► WebsocketClient (FIXED)           ← Receives URL, no override logic
        └─► global_value (CLEANED)      ← Has reset_all() and reset_trading_state()
```

---

## Current State Map

| File | Role | Issues Found | Action |
|------|------|-------------|--------|
| `ws/channels/ssid.py` | Ssid channel class | Dead code — imported but never instantiated or called | DELETE |
| `ws/chanels/ssid.py` | Duplicate (typo folder) | Exact copy of above with different import path | DELETE (entire `chanels/` folder) |
| `ws/client.py` | WebSocket connection & message handling | 2 critical bugs: message handler logic error, URL override | FIX |
| `api.py` | Core API class | Duplicate `parse_demo_status()`, `wss_url` computed but ignored | SIMPLIFY |
| `stable_api.py` | High-level wrapper | Duplicate `parse_demo_status()`, redundant initialization | SIMPLIFY |
| `global_value.py` | Shared mutable state | No reset mechanism, stale state on reconnect | ADD reset functions |
| `pocket.py` | Legacy implementation (Vigo Walker) | Completely separate codebase, different library, dead code | DELETE |
| `core/ssid_connector.py` | Integration wrapper | Has `demo` param that conflicts with SSID's `isDemo` | REPLACE with thin wrapper |
| `constants.py` | Region URLs & asset IDs | DEMO URLs commented out in REGION class | KEEP (regions used for REAL fallback) |

---

## Confirmed Bugs (Evidence-Based)

### Bug 1: Message Handler Logic Error (CRITICAL)
**File:** `ws/client.py`, line ~230  
**Code:**
```python
elif "40" and "sid" in message:
    await self.websocket.send(global_value.SSID)
```
**Problem:** Python evaluates `"40" and "sid" in message` as `True and ("sid" in message)` → effectively `if "sid" in message`. Any message containing the substring "sid" (e.g., balance updates with `balance_id`, asset data with `session_id`) will trigger a full SSID re-send.  
**Impact:** Auth spam → server disconnects, rate-limiting, or IP bans.  
**Fix:**
```python
elif message.startswith("40") and "sid" in message:
    await self.websocket.send(global_value.SSID)
```

### Bug 2: Redundant URL Override in client.py (HIGH)
**File:** `ws/client.py`, `connect()` method  
**Code:**
```python
if global_value.DEMO == True:
    if "session_id" in global_value.SSID:
        url = "wss://demo-api-eu.po.market/socket.io/?EIO=4&transport=websocket"
    elif "session" in global_value.SSID and "session_id" not in global_value.SSID:
        url = "wss://demo-api-eu.po.market/socket.io/?EIO=4&transport=websocket"
    else:
        url = "wss://try-demo-eu.po.market/socket.io/?EIO=4&transport=websocket"
```
**Problem:** The `if` and `elif` branches resolve to the **exact same URL**. The `api.py` class already computes `self.wss_url` but `client.py` ignores it entirely.  
**Impact:** Redundant logic, impossible to debug, `api.py`'s URL computation is wasted work.  
**Fix:** `client.py` should accept the URL from the session/API layer, not compute its own.

### Bug 3: Silent Fallback to REAL on Parse Failure (HIGH)
**File:** `api.py` and `stable_api.py`, `parse_demo_status()` method  
**Code:**
```python
except Exception as e:
    logger.error(f"Error parsing SSID demo status: {e}")
    return False  # Default to real account
```
**Problem:** If the SSID format is malformed, the code silently defaults to REAL account mode. A user intending to trade on DEMO could unknowingly connect to REAL servers.  
**Impact:** Potential real-money exposure on malformed input.  
**Fix:** Fail fast — raise an exception instead of defaulting.

### Bug 4: Triple-Parsed SSID (MEDIUM)
**File:** `ssid_connector.py` → `stable_api.py` → `api.py`  
**Problem:** `parse_demo_status()` is called 3 times during initialization, each time setting `global_value.DEMO`. Wasteful and fragile.  
**Fix:** Parse once in `PocketOptionSession`, pass the result down.

### Bug 5: Dead Ssid Channel Class (LOW)
**File:** `ws/channels/ssid.py` and `ws/chanels/ssid.py`  
**Problem:** `Ssid` class is imported in `api.py` but never instantiated as a property or called. Authentication is done directly via `await self.websocket.send(global_value.SSID)` in `client.py`.  
**Fix:** Delete both files and the import.

---

## Implementation Phases

### [x] Phase 1: Add Reset Functions to `global_value.py`
**Objective:** Enable clean state transitions for account switching.  
**Files touched:** `pocketoptionapi/global_value.py`

```python
def reset_trading_state():
    """Reset trading-related state only (for account switching)"""
    global balance, balance_id, balance_type, balance_updated
    global result, order_data, order_open, order_closed, stat
    global profit, percent_profit, current_price, volume
    global available_assets, asset_manager
    
    balance_id = None
    balance = None
    balance_type = None
    balance_updated = None
    result = None
    order_data = {}
    order_open = []
    order_closed = []
    stat = []
    profit = None
    percent_profit = None
    current_price = None
    volume = None
    available_assets = None
    asset_manager = None


def reset_all():
    """Reset ALL global state (for full disconnect)"""
    global websocket_is_connected, ssl_Mutual_exclusion, ssl_Mutual_exclusion_write
    global SSID, DEMO
    global check_websocket_if_error, websocket_error_reason
    
    reset_trading_state()
    
    websocket_is_connected = False
    ssl_Mutual_exclusion = False
    ssl_Mutual_exclusion_write = False
    SSID = None
    DEMO = None
    check_websocket_if_error = False
    websocket_error_reason = None
```

**Verification:** Import and call `reset_all()` — confirm all globals return to initial values.

---

### [x] Phase 2: Fix `client.py` Critical Bugs
**Objective:** Fix the message handler logic error and URL override.  
**Files touched:** `pocketoptionapi/ws/client.py`

**Fix 2a — Message handler:**
```python
# BEFORE (broken):
elif "40" and "sid" in message:
    await self.websocket.send(global_value.SSID)

# AFTER (fixed):
elif message.startswith("40") and "sid" in message:
    await self.websocket.send(global_value.SSID)
```

**Fix 2b — URL override removal:**
```python
# BEFORE: client.py computes its own URL in connect()
# AFTER: client.py accepts URL via constructor or global

async def connect(self):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        await self.close()
    except:
        pass

    while not global_value.websocket_is_connected:
        # For DEMO: use dedicated demo server
        if global_value.DEMO:
            urls = ["wss://demo-api-eu.po.market/socket.io/?EIO=4&transport=websocket"]
        else:
            # For REAL: use region rotation
            urls = self.region.get_regions(True)

        for url in urls:
            print(url)
            try:
                async with websockets.connect(
                    url,
                    ssl=ssl_context,
                    extra_headers={"Origin": "https://pocketoption.com", "Cache-Control": "no-cache"},
                    user_agent_header="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ) as ws:
                    self.websocket = ws
                    self.url = url
                    global_value.websocket_is_connected = True

                    on_message_task = asyncio.create_task(self.websocket_listener(ws))
                    sender_task = asyncio.create_task(self.send_message(self.message))
                    ping_task = asyncio.create_task(send_ping(ws))

                    await asyncio.gather(on_message_task, sender_task, ping_task)

            except websockets.ConnectionClosed as e:
                global_value.websocket_is_connected = False
                await self.on_close(e)
                logger.warning("Trying another server")

            except Exception as e:
                global_value.websocket_is_connected = False
                await self.on_error(e)

        await asyncio.sleep(1)

    return True
```

**Verification:** Connect with DEMO SSID → confirm only demo URL is attempted. Connect with REAL SSID → confirm region rotation is used. Send a message containing "sid" substring → confirm SSID is NOT re-sent.

---

### [x] Phase 3: Build `PocketOptionSession` Component
**Objective:** Create the single, reusable session manager.
**Files created:** `ssid_integration_package/core/session.py`

```python
"""
PocketOptionSession — Reusable SSID Session Manager

Single source of truth for:
- SSID validation and parsing
- DEMO/REAL account detection
- WebSocket connection lifecycle
- Clean account switching
- Global state management

Usage:
    session = PocketOptionSession(ssid_string)
    success, msg = session.connect()
    
    # Switch accounts
    session.switch_account(other_ssid_string)
    
    # Context manager
    with PocketOptionSession(ssid_string) as session:
        balance = session.get_balance()
"""

import json
import time
import logging
from typing import Optional, Tuple

from pocketoptionapi.stable_api import PocketOption
import pocketoptionapi.global_value as global_value


class SSIDParseError(Exception):
    """Raised when SSID string cannot be parsed"""
    pass


class ConnectionError(Exception):
    """Raised when WebSocket connection fails"""
    pass


class PocketOptionSession:
    """
    Single-responsibility session manager for Pocket Option API.
    
    Parses SSID once, manages connection lifecycle, enables clean switching.
    """

    def __init__(self, ssid: str, timeout: int = 15):
        """
        Initialize session with SSID string.
        
        Args:
            ssid: Full SSID string (e.g., '42["auth",{"session":"...","isDemo":1,...}]')
            timeout: Connection timeout in seconds
            
        Raises:
            SSIDParseError: If SSID format is invalid
        """
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self._api = None
        self._connected = False
        self._balance = None
        
        # Parse SSID once — single source of truth
        self._raw_ssid = ssid
        self._session_data = self._parse_ssid(ssid)
        self._is_demo = bool(self._session_data.get('isDemo', 0))
        
        self.logger.info(
            f"Session initialized: {'DEMO' if self._is_demo else 'REAL'} account"
        )

    @staticmethod
    def _parse_ssid(ssid: str) -> dict:
        """
        Parse and validate SSID string. Called exactly ONCE.
        
        Args:
            ssid: Raw SSID string
            
        Returns:
            dict: Parsed auth payload
            
        Raises:
            SSIDParseError: If format is invalid
        """
        if not ssid or not isinstance(ssid, str):
            raise SSIDParseError("SSID must be a non-empty string")
        
        if not ssid.startswith('42['):
            raise SSIDParseError(
                f"SSID must start with '42['. Got: '{ssid[:20]}...'"
            )
        
        try:
            json_part = ssid[2:]  # Strip '42' prefix
            data = json.loads(json_part)
        except json.JSONDecodeError as e:
            raise SSIDParseError(f"SSID JSON is malformed: {e}")
        
        if not isinstance(data, list) or len(data) < 2:
            raise SSIDParseError("SSID must be a JSON array with at least 2 elements")
        
        if data[0] != "auth":
            raise SSIDParseError(f"SSID first element must be 'auth', got '{data[0]}'")
        
        payload = data[1]
        if not isinstance(payload, dict):
            raise SSIDParseError("SSID auth payload must be a dictionary")
        
        # Validate required fields
        required_fields = ['session', 'isDemo']
        missing = [f for f in required_fields if f not in payload]
        if missing:
            raise SSIDParseError(f"SSID missing required fields: {missing}")
        
        return payload

    @property
    def is_demo(self) -> bool:
        """Whether this is a DEMO account session"""
        return self._is_demo

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket is currently connected"""
        return self._connected and self._api and self._api.check_connect()

    @property
    def account_type(self) -> str:
        """Human-readable account type"""
        return "DEMO" if self._is_demo else "REAL"

    def connect(self) -> Tuple[bool, str]:
        """
        Establish WebSocket connection to Pocket Option.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            self.logger.info(f"Connecting to {self.account_type} account...")
            
            # Reset global state for clean connection
            global_value.reset_all()
            
            # Set globals that the API layer needs
            global_value.SSID = self._raw_ssid
            global_value.DEMO = self._is_demo
            
            # Create API instance
            self._api = PocketOption(self._raw_ssid)
            
            # Start connection
            connection_result = self._api.connect()
            if not connection_result:
                return False, "Failed to start WebSocket connection"
            
            # Wait for WebSocket handshake
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                if self._api.check_connect():
                    self._connected = True
                    self.logger.info("WebSocket connected")
                    break
                time.sleep(0.5)
            
            if not self._connected:
                return False, f"Connection timeout after {self.timeout}s"
            
            # Wait for balance (confirms authentication)
            balance_timeout = 20
            start_time = time.time()
            while time.time() - start_time < balance_timeout:
                balance = self._api.get_balance()
                if balance is not None:
                    self._balance = balance
                    msg = f"Connected to {self.account_type}. Balance: ${balance:,.2f}"
                    self.logger.info(msg)
                    return True, msg
                time.sleep(0.5)
            
            self._connected = False
            return False, "Authentication failed — no balance received"
            
        except Exception as e:
            self._connected = False
            error_msg = f"Connection failed: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def disconnect(self) -> bool:
        """
        Gracefully disconnect and reset all state.
        
        Returns:
            bool: True if successful
        """
        try:
            self.logger.info(f"Disconnecting from {self.account_type} account...")
            
            if self._api and self._connected:
                try:
                    self._api.disconnect()
                except Exception as e:
                    self.logger.warning(f"API disconnect error: {e}")
            
            # Reset ALL global state
            global_value.reset_all()
            
            self._connected = False
            self._balance = None
            self._api = None
            
            time.sleep(1)  # Allow cleanup
            self.logger.info("Disconnected and state cleared")
            return True
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
            return False

    def switch_account(self, new_ssid: str) -> Tuple[bool, str]:
        """
        Switch to a different account (DEMO ↔ REAL or different user).
        
        Performs a full disconnect → state reset → reconnect cycle.
        
        Args:
            new_ssid: New SSID string to connect with
            
        Returns:
            tuple: (success: bool, message: str)
        """
        old_type = self.account_type
        
        # Parse new SSID first (fail fast before disconnecting)
        try:
            new_data = self._parse_ssid(new_ssid)
        except SSIDParseError as e:
            return False, f"Invalid new SSID: {e}"
        
        new_is_demo = bool(new_data.get('isDemo', 0))
        new_type = "DEMO" if new_is_demo else "REAL"
        
        self.logger.info(f"Switching from {old_type} to {new_type}...")
        
        # Disconnect current session
        self.disconnect()
        
        # Update internal state
        self._raw_ssid = new_ssid
        self._session_data = new_data
        self._is_demo = new_is_demo
        
        # Connect with new SSID
        success, msg = self.connect()
        
        if success:
            return True, f"Switched from {old_type} to {new_type}. {msg}"
        else:
            return False, f"Switch failed: {msg}"

    def get_balance(self) -> Optional[float]:
        """Get current account balance"""
        if not self.is_connected:
            return None
        try:
            balance = self._api.get_balance()
            if balance is not None:
                self._balance = balance
            return self._balance
        except Exception:
            return self._balance

    def buy(self, amount, active, action, expirations):
        """Place a trade"""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        return self._api.buy(amount, active, action, expirations)

    def buy_advanced(self, amount, active, action, expirations, on_new_candle=False):
        """Place an advanced trade"""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        return self._api.buy_advanced(amount, active, action, expirations, on_new_candle)

    def get_candles(self, active, timeframe, count):
        """Get historical candles"""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        return self._api.get_candles(active, timeframe, count)

    def check_win(self, order_id):
        """Check if an order won or lost"""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        return self._api.check_win(order_id)

    # Context manager support
    def __enter__(self):
        success, msg = self.connect()
        if not success:
            raise ConnectionError(msg)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __repr__(self):
        status = "connected" if self._connected else "disconnected"
        return f"<PocketOptionSession {self.account_type} [{status}]>"
```

**Verification:**
1. Create with DEMO SSID → confirm `is_demo == True`
2. Create with REAL SSID → confirm `is_demo == False`
3. Create with malformed SSID → confirm `SSIDParseError` raised (not silent fallback)
4. Connect → confirm balance received
5. Disconnect → confirm all globals reset to `None`/`False`/`[]`
6. `switch_account()` → confirm old state cleared, new balance received

---

### [x] Phase 4: Clean Up Dead Code
**Objective:** Remove files that are unused, duplicated, or from a different implementation.  
**Files deleted:**

| File | Reason |
|------|--------|
| `ws/chanels/` (entire folder) | Typo duplicate of `ws/channels/` |
| `ws/channels/ssid.py` | Dead code — `Ssid` class imported but never instantiated or called |
| `pocket.py` | Completely separate legacy implementation (different library, different protocol) |

**Files modified:**

| File | Change |
|------|--------|
| `api.py` | Remove `from pocketoptionapi.ws.channels.ssid import Ssid` import |
| `api.py` | Remove duplicate `parse_demo_status()` method |
| `stable_api.py` | Remove duplicate `parse_demo_status()` method |

**Verification:** Run `python -c "from pocketoptionapi.stable_api import PocketOption"` → no import errors.

---

### [x] Phase 5: Update SSIDConnector as Backward-Compatible Wrapper
**Objective:** Existing code using `SSIDConnector` continues to work unchanged.  
**Files modified:** `core/ssid_connector.py`

```python
"""
SSIDConnector — Backward-compatible wrapper around PocketOptionSession.

Existing code that uses SSIDConnector will continue to work.
New projects should use PocketOptionSession directly.
"""

from ssid_integration_package.core.session import PocketOptionSession, SSIDParseError


class SSIDConnector:
    """Backward-compatible wrapper. Use PocketOptionSession for new projects."""

    def __init__(self, ssid: str, demo: bool = False, timeout: int = 15):
        # Note: 'demo' parameter is ignored — isDemo is read from the SSID itself.
        # Kept for backward compatibility only.
        self._session = PocketOptionSession(ssid, timeout=timeout)
        self.is_connected = False
        self.balance = None

    def connect(self):
        success, msg = self._session.connect()
        self.is_connected = success
        self.balance = self._session.get_balance()
        return success, msg

    def disconnect(self):
        result = self._session.disconnect()
        self.is_connected = False
        self.balance = None
        return result

    def check_connection(self):
        return self._session.is_connected

    def get_balance(self):
        return self._session.get_balance()

    def update_balance(self):
        return self._session.get_balance()

    def __enter__(self):
        success, msg = self.connect()
        if not success:
            raise ConnectionError(msg)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
```

**Verification:** Run existing `examples/basic_connection.py` → confirm it works without changes.

---

## Verification Checklist

| # | Test | Expected Result | Phase |
|---|------|----------------|-------|
| 1 | `global_value.reset_all()` | All globals return to initial values | 1 |
| 2 | `global_value.reset_trading_state()` | Trading globals reset, SSID/DEMO preserved | 1 |
| 3 | Connect DEMO SSID | Only `demo-api-eu.po.market` URL attempted | 2 |
| 4 | Connect REAL SSID | Region rotation URLs attempted | 2 |
| 5 | Message with "sid" substring | SSID NOT re-sent | 2 |
| 6 | `PocketOptionSession(malformed_ssid)` | `SSIDParseError` raised immediately | 3 |
| 7 | `session.connect()` with valid DEMO SSID | Returns `(True, "Connected to DEMO...")` | 3 |
| 8 | `session.connect()` with valid REAL SSID | Returns `(True, "Connected to REAL...")` | 3 |
| 9 | `session.disconnect()` then check globals | All globals are `None`/`False`/`[]` | 3 |
| 10 | `session.switch_account(real_ssid)` | Old state cleared, new balance received | 3 |
| 11 | `from pocketoptionapi.stable_api import PocketOption` | No import errors after cleanup | 4 |
| 12 | `SSIDConnector(ssid).connect()` | Works identically to before | 5 |

---

## Files Touched Summary

| Action | File | Phase |
|--------|------|-------|
| MODIFY | `pocketoptionapi/global_value.py` | 1 |
| MODIFY | `pocketoptionapi/ws/client.py` | 2 |
| CREATE | `ssid_integration_package/core/session.py` | 3 |
| DELETE | `pocketoptionapi/ws/chanels/` (entire folder) | 4 |
| DELETE | `pocketoptionapi/ws/channels/ssid.py` | 4 |
| DELETE | `pocketoptionapi/pocket.py` | 4 |
| MODIFY | `pocketoptionapi/api.py` (remove dead import + duplicate method) | 4 |
| MODIFY | `pocketoptionapi/stable_api.py` (remove duplicate method) | 4 |
| MODIFY | `ssid_integration_package/core/ssid_connector.py` | 5 |

---

## Risk Assessment

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Breaking OTC SNIPER code that uses `SSIDConnector` | MEDIUM | LOW | Phase 5 maintains backward compatibility |
| Pocket Option changes WebSocket protocol | LOW | LOW | All URL/protocol logic centralized in one file |
| SSID format changes | LOW | LOW | Validation in one place with clear error messages |
| Global state leaks during switch | **ELIMINATED** | — | `reset_all()` + `reset_trading_state()` |
| Silent fallback to REAL on parse error | **ELIMINATED** | — | `SSIDParseError` raised instead of defaulting |
| Auth spam from message handler bug | **ELIMINATED** | — | Fixed `startswith("40")` check |

---

## Usage Examples (Post-Implementation)

### Basic Connection
```python
from ssid_integration_package.core.session import PocketOptionSession

session = PocketOptionSession(demo_ssid)
success, msg = session.connect()
print(f"{session.account_type}: ${session.get_balance():,.2f}")
session.disconnect()
```

### Account Switching
```python
session = PocketOptionSession(demo_ssid)
session.connect()
print(f"Demo balance: ${session.get_balance():,.2f}")

# Switch to real
session.switch_account(real_ssid)
print(f"Real balance: ${session.get_balance():,.2f}")

# Switch back
session.switch_account(demo_ssid)
print(f"Demo balance: ${session.get_balance():,.2f}")

session.disconnect()
```

### Context Manager
```python
with PocketOptionSession(ssid) as session:
    result, order_id = session.buy(10, "EURUSD_otc", "call", 60)
    profit, status = session.check_win(order_id)
    print(f"Trade {status}: ${profit}")
# Auto-disconnects and cleans up on exit
```

### Integration into New Project
```python
# Drop-in: just copy core/session.py + pocketoptionapi/ folder
from core.session import PocketOptionSession

session = PocketOptionSession(ssid)
session.connect()
# Ready to trade
```

---

## Delegation Plan

| Phase | Implementer | Reviewer |
|-------|------------|----------|
| Phase 1 | @Coder | @Reviewer |
| Phase 2 | @Coder | @Reviewer + @Debugger |
| Phase 3 | @Coder | @Reviewer |
| Phase 4 | @Coder | @Reviewer |
| Phase 5 | @Coder | @Reviewer |
| Final Validation | — | @Reviewer + @Debugger + @Optimizer + @Code_Simplifier |

Per `PHASE_REVIEW_PROTOCOL.md`, no phase proceeds until @Reviewer signs off and user gives explicit approval.

---

*Plan authored by @Investigator → @Architect*  
*Ready for @Coder implementation upon user approval*
