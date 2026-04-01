## 1. Previous Conversation

The user is working on OTC_SNIPER v3, a FastAPI + React trading application for Pocket Option binary options. The previous task session attempted to:

1. Remove 13 hardcoded assets and load all 114+ available assets from Pocket Option dynamically
2. Fix payout percentages not updating
3. Add asset search, starred assets (Quick Select), and fix trade execution

The user reported that after those fixes, the hardcoded assets are still loading, payout percentages are not updating, trade executions are not firing, and trade results are not printing on the frontend. They asked for a thorough investigation delegating to @Investigator and @Debugger agents.

## 2. Current Work

A complete forensic investigation was conducted (@Investigator mode). All relevant files were read and the pocketoptionapi module was inspected at the source level. The investigation is complete and a full report was produced. The user needs to toggle to

Act Mode (⌘⇧A) so fixes can be implemented.

## 3. Key Technical Concepts

- __OTC_SNIPER v3 stack:__ FastAPI backend + React/Vite frontend + Socket.IO for real-time ticks
- __pocketoptionapi:__ External Python library at `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi` in the QuFLX-v2 conda environment
- __global_value module:__ The actual attributes are: `DEMO`, `PayoutData`, `SSID`, `balance`, `balance_id`, `balance_type`, `balance_updated`, `check_cache`, `check_csv`, `check_websocket_if_error`, `closed_deals`, `datetime`, `dp`, `get_cache`, `get_csv`, `json`, `logger`, `loglevel`, `order_closed`, `order_data`, `order_open`, `os`, `pairs`, `result`, `rp`, `set_cache`, `set_csv`, `ssl_Mutual_exclusion`, `ssl_Mutual_exclusion_write`, `stat`, `trades`, `websocket_error_reason`, `websocket_is_connected`
- __CRITICAL: `asset_manager` does NOT exist__ in global_value — the entire asset list system was built on a phantom attribute
- __PayoutData:__ The real asset/payout data source. Set by `ws/client.py` when it receives a WebSocket message containing `'[[5,"#AAPL","Apple","stock'`. It's a raw JSON string containing a list of lists where each entry is `[id, symbol, name, category, ?, payout_pct, ...]`
- __GetPayout(pair):__ Method on `PocketOption` class in `stable_api.py` that parses `PayoutData` and returns payout for a specific pair at index `[5]`
- __buy() return:__ Returns `(global_value.result, order_id)` = `(True, "some_id_string")` or `(False, None)` — a tuple of `(bool, str|None)`
- __check_win() return:__ Returns a tuple `(profit_float, status_string)` where status is `"win"` or `"loose"` (typo in the library)
- __pairs dict:__ `global_value.pairs[symbol]['history']` is populated by live tick stream in `ws/client.py` but never used by OTC_SNIPER
- __Zustand persist:__ `partialize` option in `useAssetStore.js` correctly excludes `availableAssets` from localStorage persistence
- __Socket.IO trade_result event:__ Emitted by `trade_service.py` only when `trade.outcome in {"win", "loss", "void"}` — but due to the check_win bug, outcome is always "unknown" so the event is never emitted

## 4. Relevant Files and Code

### `app/backend/brokers/pocket_option/assets.py` (BROKEN — needs rewrite)

- Uses `getattr(gv, "asset_manager", None)` — this attribute NEVER exists
- `build_asset_list_with_live_payouts()` always falls through to 13-item fallback
- `verify_asset_tradeable()` always falls through to static list check
- __Fix:__ Use `global_value.PayoutData` (raw JSON string) to build asset list

### `app/backend/brokers/pocket_option/adapter.py` (BROKEN — needs fix)

- `subscribe_ticks()` double-normalizes: `to_pocket_option_format(normalize_asset(asset))` — breaks stock symbols like `#BA_otc` → `BA_otc`
- `execute_trade()` result parsing: `isinstance(result[0], (int, float))` catches `True` (bool is subclass of int) → sets `entry_price = 1.0` always

### `app/backend/session/pocket_option_session.py` (needs new methods)

- `buy()` passes raw_id directly — correct
- Missing: `get_payout_data()` and `get_payout(pair)` methods to expose the API's payout functions

### `app/backend/services/trade_service.py` (BROKEN — needs fix)

- `_track_trade_outcome()` calls `session.check_win(trade.trade_id)` which returns `(profit, "win"/"loose")` tuple
- The tuple case is NOT handled — falls to `else` branch → `trade.outcome = "unknown"`, `trade.profit = 0.0`
- Emit condition `trade.outcome in {"win", "loss", "void"}` never fires because outcome is always "unknown"
- __Fix:__ Add tuple handling, normalize "loose" → "loss"

### `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi\stable_api.py`

- `GetPayout(pair)`: parses `PayoutData` JSON, finds entry where `i[1] == pair`, returns `i[5]` (payout %)
- `get_payout()`: returns `self.api.GetPayoutData()` = `global_value.PayoutData` (raw JSON string)
- `buy()`: returns `(global_value.result, global_value.order_data.get("id", None))` = `(True/False, id_str/None)`
- `check_win(id_number)`: returns `(order_info["profit"], "win"/"loose")` tuple

### `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi\ws\client.py`

- `PayoutData` is set when message contains `'[[5,"#AAPL","Apple","stock'`
- Format: raw JSON string of list-of-lists, each entry: `[id, symbol, name, category, ?, payout_pct, ...]`
- `pairs[symbol]['history']` populated by live tick stream

### `app/frontend/src/stores/useAssetStore.js`

- `availableAssets: []` — starts empty, populated from broker on connect
- `assetPayouts: {}` — map of raw_id → payout fraction
- `partialize` correctly excludes `availableAssets` from persistence

### `app/frontend/src/stores/useAuthStore.js`

- `connect()` calls `getBrokerAssets('pocket_option')` after session connect
- Builds `assetIds` and `payoutMap` from response
- Calls `assetStore.setAvailableAssets(assetIds)` and `assetStore.setAssetPayouts(payoutMap)`

### `app/frontend/src/App.jsx`

- `socket.on('trade_result', ...)` handler exists and correctly processes win/loss/void outcomes
- Calls `useTradingStore.getState().setLastTradeResult(data)` and `useRiskStore.getState().recordTradeResult(...)`
- The handler is correct — the problem is the backend never emits the event

### `app/frontend/src/components/trading/TradePanel.jsx`

- `handleExecute(direction)` calls `executeTrade(broker, selectedAsset)` from `useTradingStore`
- `canTrade = sessionConnected && !isExecuting && parsedAmount > 0 && parsedDuration > 0`
- Displays `lastTradeResult` when available

### `app/backend/api/trading.py`

- POST `/api/brokers/{broker}/trade` → `TradeService.execute_trade()`
- `TradeExecutionRequest` has: `asset_id`, `direction`, `amount`, `expiration`, `account_key`

### `app/backend/services/trade_service.py`

- `execute_trade()` creates `TradeOrder` and calls `adapter.execute_trade(order)`
- `_track_trade_outcome()` is the broken background task

## 5. Problem Solving

### Root Causes Found:

__Problem 1: Hardcoded 13 assets always shown__

- Root cause: `build_asset_list_with_live_payouts()` references `gv.asset_manager` which doesn't exist → always falls back to `_FALLBACK_OTC_ASSETS` (13 items)
- Fix: Parse `global_value.PayoutData` (the real data source) to build the asset list

__Problem 2: Payout always 80%__

- Root cause: Same as above — fallback always used, hardcoded to 0.8
- Fix: Parse `PayoutData[i][5]` for each asset's real payout percentage

__Problem 3: Trades blocked on non-fallback assets__

- Root cause: `verify_asset_tradeable()` falls through to `raw_id in _FALLBACK_OTC_ASSETS` check
- Fix: Verify against parsed PayoutData list instead

__Problem 4: Trade results never shown on frontend__

- Root cause: `check_win()` returns `(profit, "win"/"loose")` tuple but `trade_service.py` doesn't handle tuples → outcome = "unknown" → emit condition never fires
- Fix: Add tuple handling with "loose" → "loss" normalization

__Problem 5: Entry price always $1.00__

- Root cause: `isinstance(True, (int, float))` is True in Python → `entry_price = float(True) = 1.0`
- Fix: Check `not isinstance(result[0], bool)` before treating as float

__Problem 6: subscribe_ticks breaks stock symbols__

- Root cause: `to_pocket_option_format(normalize_asset(asset))` strips `#` from `#BA_otc`
- Fix: Pass raw asset symbol directly to `change_symbol()`

## 6. Pending Tasks and Next Steps

The investigation is complete. The user needs to __toggle to__

__Act Mode (⌘⇧A)__ to implement the following fixes:

### Fix 1: Rewrite `app/backend/brokers/pocket_option/assets.py`

Replace phantom `asset_manager` with real `PayoutData` parsing:

```python
def build_asset_list_with_live_payouts() -> list[Asset]:
    try:
        import pocketoptionapi.global_value as gv
        payout_data_raw = getattr(gv, "PayoutData", None)
        if payout_data_raw:
            data = json.loads(payout_data_raw)
            assets = []
            for entry in data:
                # entry format: [id, symbol, name, category, ?, payout_pct, ...]
                symbol = entry[1]
                name = entry[2]
                payout_pct = float(entry[5]) / 100.0
                # ... build Asset objects
            if assets:
                return assets
    except Exception as exc:
        logger.warning("Failed to read PayoutData: %s", exc)
    # fallback to _FALLBACK_OTC_ASSETS
```

Also fix `verify_asset_tradeable()` to check against PayoutData.

### Fix 2: Fix `app/backend/services/trade_service.py` `_track_trade_outcome()`

Add tuple handling before the dict/int checks:

```python
if isinstance(outcome_data, tuple) and len(outcome_data) >= 2:
    profit_val, status_str = outcome_data
    trade.profit = float(profit_val) if profit_val is not None else 0.0
    if isinstance(status_str, str):
        normalized = status_str.strip().lower()
        trade.outcome = "loss" if normalized == "loose" else normalized
    else:
        trade.outcome = "win" if trade.profit > 0 else "loss"
```

### Fix 3: Fix `app/backend/brokers/pocket_option/adapter.py` `execute_trade()`

Fix entry_price extraction from buy() result:

```python
if isinstance(result, tuple):
    if len(result) >= 2:
        trade_id = str(result[1]) if result[1] is not None else None
    # result[0] is bool (True/False), NOT a price — don't use as entry_price
    if not result[0]:  # False = trade failed
        return TradeResult(success=False, ...)
```

### Fix 4: Fix `subscribe_ticks()` in `adapter.py`

```python
# Pass raw asset symbol directly — don't normalize
await asyncio.get_running_loop().run_in_executor(
    None, session._api.change_symbol, asset, 1  # use raw asset, not normalized
)
```

### Fix 5: Add `get_payout_data()` and `get_payout()` to `PocketOptionSession`

```python
def get_payout_data(self):
    if not self.is_connected or self._api is None:
        return None
    return self._api.get_payout()  # returns global_value.PayoutData raw JSON

def get_payout(self, pair: str):
    if not self.is_connected or self._api is None:
        return None
    return self._api.GetPayout(pair)
```
