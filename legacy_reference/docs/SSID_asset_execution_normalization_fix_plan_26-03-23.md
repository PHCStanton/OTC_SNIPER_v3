# OTC SNIPER — SSID Connection, Trade Execution & Asset Normalization Fix Plan
**File:** `web_app/Dev_Docs/SSID_asset_execution_normalization_fix_plan_26-03-23.md`
**Date:** 2026-03-23
**Author:** @Investigator (Forensic Analysis) → Plan compiled for @Coder / @Architect
**Scope:** `ssid/web_app` (OTC SNIPER) project — Signal Sniper web application
**Status:** 🔴 In Progress — Awaiting @Coder Implementation

---

## Executive Summary

Two critical issues were reported:
1. **Real Account SSID connection** — balance and asset payout percentages not retrieved; trades not executed
2. **Demo Account** — connects but trades fail with "Trade not executed" error in frontend

Forensic investigation revealed **6 distinct bugs** across the trade execution and SSID connection pipeline — 3 CRITICAL, 2 HIGH, 1 MEDIUM. Root causes are:
1. The Asset Normalization changes (OTC_SNIPER_Asset_Normalization_Plan_26-03-22) were **only partially implemented** — `main.py` imports `normalize_asset` and `to_pocket_option_format` but never uses them in the trade endpoint
2. The `PocketOptionAdapter` still uses the **old blind `+ "_otc"` suffix** pattern, creating double suffixes (`EURUSD_otc_otc`)
3. `handleStartSsid` in the frontend is **hardcoded to `demo: true`** — real accounts can never connect
4. `broadcast_updates()` **never includes balance data** in WebSocket pushes
5. Frontend `executeTrade()` checks the **wrong response field** (`status` instead of `success`)
6. Trade result polling is **never started** from the adapter layer

---

## Part 1: Critical Bug Fixes — Asset Normalization (Phase 1)

### 1.1 — Fix `PocketOptionAdapter.get_assets()` — Use `normalize_asset()`

**File:** `web_app/backend/brokers/pocket_option/adapter.py`

**Problem:** Uses old `.replace("_otc", "").upper()` which produces `EURUSD` instead of `EURUSDOTC`.

**Fix:**
```python
# Add import at top of file:
from asset_utils import normalize_asset

# In get_assets() method — replace line:
# BEFORE:
asset_id = str(a.get("name", "")).replace("_otc", "").upper()

# AFTER:
asset_id = normalize_asset(a.get("name", ""))  # → "EURUSDOTC"

# Also ensure raw_id is properly set for trade execution:
assets.append(Asset(
    id=asset_id,                    # "EURUSDOTC" (canonical)
    name=a.get("display", asset_id),
    asset_type=AssetType.OTC,
    payout=float(a.get("payout", 0.0)),
    broker=BrokerType.POCKET_OPTION,
    raw_id=a.get("name", "")        # "EURUSD_otc" (PO API format)
))
```

---

### 1.2 — Fix `PocketOptionAdapter.execute_trade()` — Use `to_pocket_option_format()`

**File:** `web_app/backend/brokers/pocket_option/adapter.py`

**Problem:** Blindly appends `_otc` to asset_id, creating `EURUSD_otc_otc` (double suffix).

**Fix:**
```python
# Add import at top (if not already from 1.1):
from asset_utils import normalize_asset, to_pocket_option_format

# In execute_trade() method — replace the problematic line:
# BEFORE:
po_asset = order.asset_id + "_otc"
if not self.dm.select_asset(po_asset):
    return TradeResult(success=False, message=f"Asset not found: {po_asset}")

# AFTER:
canonical = normalize_asset(order.asset_id)
po_asset = to_pocket_option_format(canonical)  # "EURUSDOTC" → "EURUSD_otc"
if not self.dm.select_asset(po_asset):
    return TradeResult(success=False, message=f"Asset not found: {po_asset}")
```

---

### 1.3 — Fix `main.py` `/api/trade` — Apply Normalization (Phase 3 of Original Plan)

**File:** `web_app/backend/main.py`

**Problem:** `normalize_asset` and `to_pocket_option_format` are imported at the top of `main.py` but **never used** in the `/api/trade` endpoint. The trade endpoint passes `request.asset_id` (raw PocketOption format) directly into `TradeOrder`.

**Fix:**
```python
# In the /api/trade endpoint — normalize the asset_id:
@app.post("/api/trade", dependencies=[Depends(require_role("trader"))])
async def execute_trade(request: TradeRequest):
    account_type = "demo" if request.demo else "real"
    if not BrokerRegistry:
        raise HTTPException(status_code=500, detail="BrokerRegistry unavailable")

    try:
        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_type)
        if adapter.get_connection_status() != "connected":
            raise HTTPException(status_code=400, detail=f"{account_type.capitalize()} account not connected")

        # Normalize asset_id — canonical format for internal use
        canonical_asset = normalize_asset(request.asset_id)

        order = TradeOrder(
            asset_id=canonical_asset,   # ← Use normalized canonical ID
            direction=request.direction,
            amount=request.amount,
            expiration=request.expiration,
            order_type="market",
            broker=BrokerType.POCKET_OPTION
        )

        result = await adapter.execute_trade(order)
        return {"success": result.success, "message": result.message, "trade_id": result.trade_id}
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 1.4 — Fix Frontend `executeTrade()` — Check Correct Response Field

**File:** `web_app/frontend/src/components/TradingPlatform.jsx`

**Problem:** Backend returns `{"success": true/false, "message": "...", "trade_id": "..."}` but frontend checks `response.data.status === 'executed'` (wrong field). This means even successful trades show "Trade failed".

**Fix:**
```javascript
// In executeTrade function — replace the response check:
// BEFORE:
if (response.data.status === 'executed') {
    setSuccess(`${direction.toUpperCase()} — ${selectedAsset.name}`);
} else {
    setError(response.data.error || 'Trade failed');
}

// AFTER:
if (response.data.success) {
    setSuccess(`${direction.toUpperCase()} — ${selectedAsset.name}`);
    // Add trade to local history immediately as PENDING
    setTradeHistory(prev => [{
        asset: selectedAsset.name || selectedAsset.id,
        direction: direction,
        amount: parseFloat(tradeAmount),
        status: 'PENDING',
        trade_id: response.data.trade_id || null,
        open_time: Date.now() / 1000
    }, ...prev]);
} else {
    setError(response.data.message || 'Trade failed');
}
```

---

## Part 2: SSID Connection Fixes (Phase 2)

### 2.1 — Fix `handleStartSsid` — Connect Active Account, Not Always Demo

**File:** `web_app/frontend/src/components/TradingPlatform.jsx`

**Problem:** `handleStartSsid` is hardcoded to `{ demo: true }`. The Real/Demo toggle exists in the UI but is never used for SSID connection.

**Fix:**
```javascript
// In TradingPlatform.jsx — replace handleStartSsid:
// BEFORE:
const response = await axios.post(`${API_URL}/connect`, { demo: true });

// AFTER:
const handleStartSsid = useCallback(async () => {
    const isDemo = activeAccount === 'demo';
    setSsidBusy(true);
    try {
      const response = await axios.post(`${API_URL}/connect`, { demo: isDemo });
      if (response.data.success) {
        if (isDemo) {
          setDemoConnected(true);
          setBalances(prev => ({ ...prev, demo: response.data.balance || 0 }));
          setStatuses(prev => ({ ...prev, demo: 'connected' }));
        } else {
          setRealConnected(true);
          setBalances(prev => ({ ...prev, real: response.data.balance || 0 }));
          setStatuses(prev => ({ ...prev, real: 'connected' }));
        }
        setSuccess(`Connected to ${activeAccount} account`);
      } else {
        setError(response.data.message || 'Failed to connect');
      }
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.detail || 'Failed to connect');
    } finally {
      setSsidBusy(false);
      setTimeout(() => { setSuccess(''); setError(''); }, 3000);
    }
}, [activeAccount]);
```

---

### 2.2 — Fix `handleStopSsid` — Disconnect Active Account

**File:** `web_app/frontend/src/components/TradingPlatform.jsx`

**Fix:**
```javascript
// Replace handleStopSsid:
// BEFORE:
const handleStopSsid = useCallback(async () => {
    setSsidBusy(true);
    setDemoConnected(false);
    setStatuses(prev => ({ ...prev, demo: 'disconnected' }));
    setSuccess('Disconnected');
    setSsidBusy(false);
    setTimeout(() => { setSuccess(''); }, 3000);
}, []);

// AFTER:
const handleStopSsid = useCallback(async () => {
    const isDemo = activeAccount === 'demo';
    setSsidBusy(true);
    if (isDemo) {
      setDemoConnected(false);
      setStatuses(prev => ({ ...prev, demo: 'disconnected' }));
    } else {
      setRealConnected(false);
      setStatuses(prev => ({ ...prev, real: 'disconnected' }));
    }
    setSuccess(`Disconnected from ${activeAccount} account`);
    setSsidBusy(false);
    setTimeout(() => { setSuccess(''); }, 3000);
}, [activeAccount]);
```

---

## Part 3: Trade Result Retrieval & Balance Broadcasting (Phase 3)

### 3.1 — Start Trade Result Polling in `PocketOptionAdapter.connect()`

**File:** `web_app/backend/brokers/pocket_option/adapter.py`

**Problem:** `OTCDataManager._poll_trades_loop()` handles trade result polling but `PocketOptionAdapter.connect()` never calls `dm.start_polling()`. Results (WIN/LOSS) are never retrieved.

**Fix:**
```python
# In the connect() method — add polling start after successful init:
async def connect(self, credentials: Dict[str, str]) -> bool:
    # ... existing init code ...
    loop = asyncio.get_running_loop()
    def init_wrapper():
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        try:
            return self.dm.init()
        finally:
            if not thread_loop.is_closed():
                thread_loop.close()
            asyncio.set_event_loop(None)

    success = await loop.run_in_executor(None, init_wrapper)

    # ADD THIS: Start trade result polling after successful connection
    if success:
        self.dm.start_polling()
        logger.info("Trade result polling started")

    return success
```

---

### 3.2 — Fix `broadcast_updates()` to Include Balance and Trade History

**File:** `web_app/backend/main.py`

**Problem:** The WebSocket broadcast that runs every second sends `{"status": "connected"}` but never includes `balance` or `history`. The frontend expects `data.accounts.demo.balance` and `data.accounts.demo.history` — these are always `undefined`.

**Fix:**
```python
# Replace the broadcast_updates function:
async def broadcast_updates():
    while True:
        if manager.active_connections:
            state = {
                "type": "update",
                "timestamp": time.time(),
                "accounts": {}
            }
            if BrokerRegistry:
                for account_type in ["demo", "real"]:
                    try:
                        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_type)
                        status = adapter.get_connection_status()
                        if status == 'connected':
                            balance = await adapter.get_balance(demo=(account_type == "demo"))
                            history = await adapter.get_trade_history(limit=20)
                            state["accounts"][account_type] = {
                                "status": status,
                                "balance": balance.demo if account_type == "demo" else balance.real,
                                "history": history
                            }
                        else:
                            state["accounts"][account_type] = {"status": status}
                    except KeyError:
                        state["accounts"][account_type] = {"status": "disconnected"}
                    except Exception as e:
                        logger.error("Error in broadcast_updates: %s", e)
                        state["accounts"][account_type] = {"status": "error"}

            await manager.broadcast(state)
        await asyncio.sleep(1)
```

---

### 3.3 — Fix `get_trade_history()` to Map to Frontend-Expected Format

**File:** `web_app/backend/brokers/pocket_option/adapter.py`

**Problem:** `OTCDataManager.trade_history` stores `{ asset_id, direction, amount, timestamp, status, win, profit }` but the frontend expects `{ open_time, asset, direction, amount, status }`.

**Fix:**
```python
# In PocketOptionAdapter — replace get_trade_history:
async def get_trade_history(self, limit: int = 50) -> List[Dict]:
    if not self.dm:
        return []
    raw = self.dm.trade_history[-limit:] if self.dm.trade_history else []
    return [{
        "open_time": t.get("timestamp", 0),
        "asset": t.get("asset_id", t.get("asset", "")),
        "direction": t.get("direction", ""),
        "amount": t.get("amount", 0),
        "status": "WIN" if t.get("win") is True else "LOSS" if t.get("win") is False else "PENDING",
        "trade_id": t.get("trade_id", ""),
        "profit": t.get("profit", 0)
    } for t in raw]
```

---

## Part 4: Concurrent Trade Support + Settings (Phase 4)

### 4.1 — Add `trading` Section to `global.json` Settings

**File:** `web_app/data/settings/global.json`

**Add new section:**
```json
{
  "trading": {
    "max_concurrent_trades": 3,
    "default_amount": 10.0,
    "default_expiration": 60,
    "allow_same_asset_trades": false,
    "cooldown_between_trades_ms": 1000
  }
}
```

Also update the `SettingsManager._write_default_global()` in `web_app/backend/src/settings_manager.py` to include these defaults.

---

### 4.2 — Create `TradeManager` Class

**File:** `web_app/backend/src/trade_manager.py` (NEW FILE)

```python
"""
TradeManager — Concurrent Trade Orchestration
==============================================
Manages active trades, enforces limits from settings, and tracks results.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("TradeManager")


class TradeManager:
    """
    Manages concurrent trade execution with configurable limits.

    Features:
    - Tracks active (pending) trades
    - Enforces max_concurrent_trades from settings
    - Enforces cooldown between trades
    - Prevents duplicate same-asset trades (configurable)
    - Provides trade history with results
    """

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self._active_trades: Dict[str, Dict] = {}
        self._completed_trades: List[Dict] = []
        self._last_trade_time: float = 0
        self._lock = asyncio.Lock()

    def _get_trading_settings(self) -> Dict:
        settings = self.settings_manager.get_global()
        return settings.get("trading", {
            "max_concurrent_trades": 3,
            "default_amount": 10.0,
            "default_expiration": 60,
            "allow_same_asset_trades": False,
            "cooldown_between_trades_ms": 1000
        })

    async def can_place_trade(self, asset_id: str) -> tuple[bool, str]:
        """Check if a new trade can be placed. Returns (allowed, reason)."""
        settings = self._get_trading_settings()

        async with self._lock:
            max_concurrent = settings.get("max_concurrent_trades", 3)
            if len(self._active_trades) >= max_concurrent:
                return False, f"Maximum concurrent trades reached ({max_concurrent})"

            cooldown_ms = settings.get("cooldown_between_trades_ms", 1000)
            elapsed_ms = (time.time() - self._last_trade_time) * 1000
            if elapsed_ms < cooldown_ms:
                remaining = int(cooldown_ms - elapsed_ms)
                return False, f"Trade cooldown active ({remaining}ms remaining)"

            if not settings.get("allow_same_asset_trades", False):
                for trade in self._active_trades.values():
                    if trade.get("asset_id") == asset_id:
                        return False, f"Active trade already exists for {asset_id}"

            return True, "OK"

    async def register_trade(self, trade_id: str, trade_info: Dict) -> None:
        """Register a newly placed trade as active."""
        async with self._lock:
            self._active_trades[trade_id] = {
                **trade_info,
                "placed_at": time.time(),
                "status": "PENDING"
            }
            self._last_trade_time = time.time()

    async def complete_trade(self, trade_id: str, result: Dict) -> None:
        """Move a trade from active to completed."""
        async with self._lock:
            trade = self._active_trades.pop(trade_id, None)
            if trade:
                trade.update(result)
                trade["status"] = "WIN" if result.get("win") else "LOSS"
                trade["completed_at"] = time.time()
                self._completed_trades.append(trade)

    def get_active_trades(self) -> List[Dict]:
        return list(self._active_trades.values())

    def get_all_history(self, limit: int = 50) -> List[Dict]:
        active = list(self._active_tr
### 4.3 � Integrate TradeManager into main.py

**File:** web_app/backend/main.py

Add to module-level imports and initialize:

`python
from src.trade_manager import TradeManager

# After settings_manager initialization:
_trade_manager = TradeManager(settings_manager)
`

Update the /api/trade endpoint to enforce limits:

`python
@app.post("/api/trade", dependencies=[Depends(require_role("trader"))])
async def execute_trade(request: TradeRequest):
    account_type = "demo" if request.demo else "real"
    if not BrokerRegistry:
        raise HTTPException(status_code=500, detail="BrokerRegistry unavailable")

    try:
        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_type)
        if adapter.get_connection_status() != "connected":
            raise HTTPException(status_code=400, detail=f"{account_type.capitalize()} account not connected")

        # Enforce concurrent trade limits from settings
        canonical_asset = normalize_asset(request.asset_id)
        allowed, reason = await _trade_manager.can_place_trade(canonical_asset)
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)

        order = TradeOrder(
            asset_id=canonical_asset,
            direction=request.direction,
            amount=request.amount,
            expiration=request.expiration,
            order_type="market",
            broker=BrokerType.POCKET_OPTION
        )

        result = await adapter.execute_trade(order)

        if result.success and result.trade_id:
            await _trade_manager.register_trade(result.trade_id, {
                "asset_id": canonical_asset,
                "direction": request.direction,
                "amount": request.amount,
                "expiration": request.expiration,
                "account_type": account_type
            })

        return {"success": result.success, "message": result.message, "trade_id": result.trade_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
`

Add /api/trades/active endpoint:

`python
@app.get("/api/trades/active", dependencies=[Depends(require_role("trader"))])
async def get_active_trades():
    return _trade_manager.get_active_trades()
`

---

### 4.4 � Enable Concurrent Trades in Frontend

**File:** web_app/frontend/src/components/TradingPlatform.jsx

Replace single loading state with per-direction state:

`javascript
// REPLACE:
const [loading, setLoading] = useState(false);

// WITH:
const [tradingBusy, setTradingBusy] = useState({ call: false, put: false });

// REPLACE executeTrade loading:
const executeTrade = async (direction) => {
    if (!selectedAsset) return;
    setTradingBusy(prev => ({ ...prev, [direction]: true }));
    setError('');
    try {
      const response = await axios.post(${API_URL}/trade, {
        asset_id: selectedAsset.id,
        direction,
        amount: parseFloat(tradeAmount),
        expiration: parseInt(expiration),
        demo: activeAccount === 'demo'
      });
      if (response.data.success) {
        setSuccess(${direction.toUpperCase()} - );
        setTradeHistory(prev => [{
          asset: selectedAsset.name || selectedAsset.id,
          direction,
          amount: parseFloat(tradeAmount),
          status: 'PENDING',
          trade_id: response.data.trade_id || null,
          open_time: Date.now() / 1000
        }, ...prev]);
      } else {
        setError(response.data.message || 'Trade failed');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setTradingBusy(prev => ({ ...prev, [direction]: false }));
      setTimeout(() => { setError(''); setSuccess(''); }, 3000);
    }
};

// UPDATE CALL/PUT buttons disabled prop:
<button disabled={tradingBusy.call || !selectedAsset} ...>CALL</button>
<button disabled={tradingBusy.put || !selectedAsset} ...>PUT</button>
`

---

### 4.5 � Add Trading Settings UI

**File:** web_app/frontend/src/components/SettingsView.jsx

Add a new "Trading" section before the closing tag:

`jsx
{/* Trading Controls */}
<section className="bg-slate-800 p-4 rounded-xl border border-slate-700">
  <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Trading Controls</h3>
  <div className="grid grid-cols-2 gap-4">
    <div className="flex flex-col">
      <label className="text-xs text-slate-500 mb-1">Max Concurrent Trades</label>
      <input
        type="number" min="1" max="10"
        className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
        value={settings.trading?.max_concurrent_trades || 3}
        onChange={e => updateSetting('trading.max_concurrent_trades', parseInt(e.target.value))}
      />
    </div>
    <div className="flex flex-col">
      <label className="text-xs text-slate-500 mb-1">Default Amount ($)</label>
      <input
        type="number"
        className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
        value={settings.trading?.default_amount || 10}
        onChange={e => updateSetting('trading.default_amount', parseFloat(e.target.value))}
      />
    </div>
    <div className="flex flex-col">
      <label className="text-xs text-slate-500 mb-1">Cooldown (ms)</label>
      <input
        type="number"
        className="bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white"
        value={settings.trading?.cooldown_between_trades_ms || 1000}
        onChange={e => updateSetting('trading.cooldown_between_trades_ms', parseInt(e.target.value))}
      />
    </div>
    <label className="flex items-center gap-2 text-sm cursor-pointer">
      <input
        type="checkbox"
        checked={settings.trading?.allow_same_asset_trades || false}
        onChange={e => updateSetting('trading.allow_same_asset_trades', e.target.checked)}
        className="rounded bg-slate-900 border-slate-700"
      />
      Allow Same-Asset Trades
    </label>
  </div>
</section>
`

---

## Part 5: Active Trades Display (Phase 5)

### 5.1 � Display Active Trade Count Badge

**File:** web_app/frontend/src/components/TradingPlatform.jsx

Add a badge near the trade buttons showing active trade count:

`javascript
// Add state for active trades:
const [activeTrades, setActiveTrades] = useState([]);

// In WebSocket message handler, add after history parsing:
if (data.active_trades) {
    setActiveTrades(data.active_trades);
}

// Near the CALL/PUT buttons, add:
{activeTrades.length > 0 && (
  <div className="text-xs text-amber bg-amber/10 border border-amber/20 rounded px-2 py-1">
    {activeTrades.length} active trade(s)
  </div>
)}
`

---

## Verification Checklist (Post-Implementation)

### Backend Verification
- [ ] 
ormalize_asset("EURUSD_otc") returns "EURUSDOTC"
- [ ] 	o_pocket_option_format("EURUSDOTC") returns "EURUSD_otc"
- [ ] Trade execution for EURUSD_otc produces "EURUSD_otc" (not "EURUSD_otc_otc")
- [ ] /api/trade returns {"success": true/false} (not {"status": "executed"})
- [ ] roadcast_updates() includes alance and history fields
- [ ] Trade result polling starts after successful SSID connection
- [ ] Real account connects when demo: false is sent
- [ ] TradeManager enforces max_concurrent_trades limit
- [ ] /api/trades/active returns active trades list

### Frontend Verification
- [ ] SSID connect button uses ctiveAccount (not hardcoded demo)
- [ ] Trade buttons have per-direction loading state (not single shared loading)
- [ ] Trade success toast shows for esponse.data.success === true
- [ ] Trade history displays with correct WIN/LOSS/PENDING status
- [ ] Trading settings section visible in Settings view
- [ ] Active trade count badge appears when trades are pending

### End-to-End Verification
- [ ] Demo account connects successfully
- [ ] Real account connects successfully
- [ ] Demo trade executes and result (WIN/LOSS) is retrieved
- [ ] Real trade executes and result (WIN/LOSS) is retrieved
- [ ] Balance updates in real-time via WebSocket
- [ ] Multiple concurrent trades can be placed (up to limit)
- [ ] Same-asset trade restriction works when disabled
- [ ] Cooldown between trades is enforced

---

## Files Touched Summary

| File | Change Type | Part |
|------|-------------|------|
| ackend/brokers/pocket_option/adapter.py | FIX � normalization + polling start | Part 1, 3 |
| ackend/main.py | FIX � normalization + broadcast + TradeManager | Part 1, 3, 4 |
| rontend/src/components/TradingPlatform.jsx | FIX � SSID connect + response field + concurrent trades | Part 1, 2, 4 |
| rontend/src/components/SettingsView.jsx | ADD � trading settings section | Part 4 |
| data/settings/global.json | ADD � trading settings | Part 4 |
| ackend/src/settings_manager.py | ADD � trading defaults in _write_default_global | Part 4 |
| ackend/src/trade_manager.py | **NEW** � concurrent trade orchestration | Part 4 |

**Total files:** 7 (6 existing + 1 new)

---

## Risk Assessment

| Phase | Risk Level | Notes |
|-------|-----------|-------|
| Part 1 (Asset Normalization) | ?? Medium | Core trade execution path � test immediately after |
| Part 2 (SSID Real Account) | ?? Low | Simple boolean change � verify both demo and real work |
| Part 3 (Trade Results) | ?? Medium | Polling + broadcast � verify WIN/LOSS appear in history |
| Part 4 (Concurrent Trades) | ?? Medium | New async lock + settings � test under load |
| Part 5 (Active Trades UI) | ?? Low | Display only � no backend logic change |

---

*Plan compiled by @Investigator � ready for @Coder implementation.*  
*Delegate @Reviewer after each Part per PHASE_REVIEW_PROTOCOL.md.*