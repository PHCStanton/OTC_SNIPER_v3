# SSID Integration Package - OTC Trading

**For Coding Agents & Developers: Complete SSID connection and OTC trade execution integration guide.**

This package provides the **proven working patterns** from the OTC SNIPER project, centralizing authentication, WebSocket lifecycle, and trade execution.

---

## ⚡ Quick Start (3 minutes)

### Primary API: `PocketOptionSession` (Recommended)

```python
from ssid_integration_package.core.session import PocketOptionSession
from ssid_integration_package.core.ssid_connector import SSIDConnector
from ssid_integration_package.core.otc_executor import OTCExecutor

# 1. Get your SSID (from Pocket Option browser developer tools)
# isDemo: 0 = REAL account, isDemo: 1 = DEMO account
ssid = '42["auth",{"session":"your_real_ssid_here","isDemo":0,"uid":12345,"platform":2}]'

# 2. Connect (validates SSID format and detects DEMO/REAL automatically)
session = PocketOptionSession(ssid)
success, message = session.connect()
print(f"Connection: {message} ({session.account_type})")

# 3. Execute trade with validated OTC executor
connector = SSIDConnector(ssid)
connector.connect()
executor = OTCExecutor(connector)
result = executor.execute_trade(
    asset="EURUSD_otc",
    direction="call",  # or "put"
    amount=10.0,
    expiration=300
)
print(result['message'])
```

---

## 🔑 Critical Success Points

### 1. **Single Source of Truth: `isDemo` is in the SSID**

> [!IMPORTANT]
> **Account mode (DEMO vs REAL) is determined ONLY by the `isDemo` field inside the SSID frame.**
> - `isDemo: 0` → REAL account
> - `isDemo: 1` → DEMO account
> External function parameters (like `demo=False`) are ignored or secondary; always ensure your SSID JSON contains the intended `isDemo` value.

### 2. **Connection Sequence (DO NOT SKIP)**

**✅ CORRECT PATTERN:**
```python
session = PocketOptionSession(ssid)
success, msg = session.connect()  # Blocking call with polling & balance verification
if not success:
    raise Exception(f"Connection failed: {msg}")
```

**❌ BROKEN PATTERN:**
```python
api = PocketOption(ssid)
api.connect()  # Missing validation & balance wait!
```

### 3. **Trade Execution**

**✅ WORKS:**
```python
# Always check connection before trade
if not connector.check_connection():
    raise Exception("Lost connection")

result = connector.api.buy(
    amount=10.0,
    active="EURUSD_otc",     # Must end with _otc
    action="call",           # Must be "call"/"put" string
    expirations=300
)
```

### 4. **Asset Validation**

**✅ VERIFIED OTC ASSETS:**
```python
verified_assets = [
    "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc",
    "USDCAD_otc", "USDCHF_otc", "NZDUSD_otc", "EURJPY_otc",
    "EURGBP_otc", "EURAUD_otc", "EURCAD_otc", "AUDNZD_otc",
    "AUDJPY_otc"
]

if asset not in verified_assets:
    raise ValueError(f"Asset {asset} not verified")
```

---

## 🚨 Issues Fixed (Agent Must Know)

### **Issue 1: Demo Trapping & Parameter Confusion**

- **Old Bug:** Code checked `session.demo` or relied on external arguments that contradicted the SSID payload.
- **Fixed:** `isDemo` inside the SSID frame is parsed once and controls all routing and WebSocket server selection.

### **Issue 2: Asset Validation Missing**

- **Fixed:** Hardcoded working OTC asset catalog (`OTCExecutor.OTC_ASSETS`) for guaranteed execution.

### **Issue 3: Missing Balance / Handshake Validation**

- **Fixed:** `connect()` waits for both WebSocket handshake and balance retrieval to guarantee authenticated readiness.

---

## 📁 Package Structure

```
ssid_integration_package/
├── core/
│   ├── session.py            # PocketOptionSession (Primary API)
│   ├── ssid_connector.py     # Backward-compatible wrapper
│   └── otc_executor.py       # Trade execution with validation
├── examples/
│   ├── basic_connection.py   # Connect and disconnect
│   └── simple_trade.py       # Execute trade
├── integration_guides/
│   ├── INTEGRATION_GUIDE.md  # Complete 12-section master guide
│   └── dev_docs/             # Multi-agent review reports & plans
└── config/
    └── config_template.json  # SSID storage template
```

---

## 🔧 Integration Steps

### **Step 1: Imports**

```python
from ssid_integration_package.core.session import PocketOptionSession
from ssid_integration_package.core.ssid_connector import SSIDConnector
from ssid_integration_package.core.otc_executor import OTCExecutor
```

### **Step 2: Context Manager Usage (Cleanest)**

```python
from ssid_integration_package.core.session import PocketOptionSession

ssid = '42["auth",{"session":"...","isDemo":0,"uid":12345,"platform":2}]'

with PocketOptionSession(ssid) as session:
    print(f"Connected to {session.account_type}. Balance: ${session.get_balance():,.2f}")
    result, order_id = session.buy(10.0, "EURUSD_otc", "call", 300)
    print(f"Order: {order_id}")
# Automatically disconnects and calls reset_all() on exit
```

---

## 🧪 Testing & Validation

### **Test 1: Connection Test**
```bash
python -c "
from ssid_integration_package.core.session import PocketOptionSession
session = PocketOptionSession('your_ssid_here')
success, msg = session.connect()
print(f'Result: {success} - {msg}')
session.disconnect()
"
```

---

## 📖 Detailed Reference

For complete architectural details, API signatures, migration instructions, and troubleshooting tables, refer to:
👉 [integration_guides/INTEGRATION_GUIDE.md](file:///c:/v3/OTC_SNIPER/ssid_integration_package/integration_guides/INTEGRATION_GUIDE.md)
