# 🔌 OTC SNIPER — Plugin System

> **Modular, tiered extensions for the OTC SNIPER Binary Options platform.**
> Install premium features without touching core code. Uninstall cleanly with zero residue.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Available Plugins](#available-plugins)
  - [Adaptive Edge (Premium)](#1-adaptive-edge--premium)
  - [AI Pulse & Noise Filter (Elite)](#2-ai-pulse--noise-filter--elite)
- [Installation](#installation)
- [Uninstallation](#uninstallation)
- [Configuration](#configuration)
- [Plugin Development Guide](#plugin-development-guide)
- [File Structure](#file-structure)

---

## Overview

The OTC SNIPER plugin system enables **modular, tiered feature packaging** built on top of the core Hurst Exponent engine. Plugins extend the platform's trading intelligence without modifying core files directly — all integration is handled through the `ExtensionManager` and `BaseExtension` hook system.

### Design Principles

| Principle | Description |
|---|---|
| **Atomic Install/Uninstall** | Every plugin ships with a single `install.py` that copies files, injects imports, and creates backups. Uninstall reverts everything cleanly. |
| **Zero Core Modifications** | Core `streaming.py` and `auto_ghost.py` delegate to the `ExtensionManager` — plugins register themselves automatically via dynamic discovery. |
| **Manifest-Driven** | Each plugin declares its files, destinations, and code injection points in a `manifest.json`. No hardcoded paths in the installer logic. |
| **Tiered Monetization** | Plugins map to product tiers (Free → Premium → Elite), enabling upsell paths while the free tier delivers significant standalone value. |

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│                   OTC SNIPER Core                  │
│                                                    │
│  streaming.py ──→ ExtensionManager.on_tick_processed()
│                   ExtensionManager.on_candle_closed()
│                                                    │
│  auto_ghost.py ─→ ExtensionManager.on_consider_signal()
│                                                    │
└──────────────┬─────────────────────┬───────────────┘
               │                     │
    ┌──────────▼──────────┐ ┌───────▼────────────┐
    │  BaseExtension      │ │  BaseExtension     │
    │  ─────────────      │ │  ─────────────     │
    │  HurstAdaptiveExpiry│ │  HurstAiNoise      │
    │  (adaptive_edge)    │ │  (ai_pulse_noise)  │
    └─────────────────────┘ └────────────────────┘
```

### Core Components

| Component | Location | Purpose |
|---|---|---|
| `BaseExtension` | `app/backend/services/extensions/base.py` | Abstract base class defining the 3 lifecycle hooks all plugins must implement. |
| `ExtensionManager` | `app/backend/services/extensions/manager.py` | Auto-discovers installed plugin modules in the `extensions/` directory and dispatches lifecycle events. |

### Lifecycle Hooks

Every plugin extends `BaseExtension` and can override three hooks:

```python
# 1. Called on every incoming tick — inject telemetry or modify oteo_result
def on_tick_processed(self, asset, price, timestamp, oteo_result, market_context) -> Dict

# 2. Called when a 60s candle closes — ideal for heavy computations (Hurst R/S)
def on_candle_closed(self, asset, closed_candle, market_context) -> Dict

# 3. Veto Gate — approve or reject a trade signal before execution
def on_consider_signal(self, asset, price, oteo_result, config) -> Tuple[bool, str | None]
```

---

## Available Plugins

### 1. Adaptive Edge — `Premium`

**Plugin ID:** `adaptive_edge`
**Version:** `1.0.0`

Delivers vectorized multi-scale R/S Hurst calculations and adaptive binary option contract expirations optimized for mean-reverting OTC markets.

#### Features

| Feature | Description |
|---|---|
| **Vectorized Multi-Scale R/S** | NumPy-accelerated Rescaled Range computation across scales `[16, 32, 64, 128, 256]` — replaces naive Python loops. |
| **Regime Hysteresis State Machine** | Prevents high-frequency regime flipping with configurable escape-buffer thresholds between `mean_reverting`, `random_walk`, and `trending` states. |
| **Adaptive Expiry Duration** | Dynamically adjusts binary option contract duration: shorter expiry (60s) for strong mean reversion (H ≤ 0.35), longer expiry (120s) for moderate reversion. |
| **Trade Veto Gate** | Automatically suppresses trade signals during `trending` or `random_walk` (chop) regimes. |

#### Default Settings

| Parameter | Default | Range | Description |
|---|---|---|---|
| `mean_revert_limit` | `0.44` | 0.30 – 0.50 | Hurst threshold below which market is classified as mean-reverting. |
| `trend_limit` | `0.58` | 0.50 – 0.70 | Hurst threshold above which market is classified as trending. |
| `min_adaptive_expiry` | `60` | 10 – 300 | Base expiry duration in seconds for anti-persistent trades. |

#### Files

| Type | Source | Installed Destination |
|---|---|---|
| Backend | `backend/hurst_adaptive_expiry.py` | `app/backend/services/extensions/hurst_adaptive_expiry.py` |
| Frontend | `frontend/HurstExpirySettings.jsx` | `app/frontend/src/components/shared/HurstExpirySettings.jsx` |

---

### 2. AI Pulse & Noise Filter — `Elite`

**Plugin ID:** `ai_pulse_noise`
**Version:** `1.0.0`

Applies microstructure-aware scale-cutoff noise filters and dynamic AI confidence gating to eliminate false signals caused by bid-ask bounces and platform quantization artifacts.

#### Features

| Feature | Description |
|---|---|
| **Microstructure Scale Cutoff** | Excludes short R/S scales below a configurable threshold, filtering bid-ask bounce noise from the Hurst calculation. |
| **Dynamic AI Confidence Floor** | Vetoes trade signals where the combined OTEO AI confidence score falls below a tunable threshold. |
| **Filtered Hurst Override** | Replaces the baseline Hurst value with the noise-filtered calculation in `oteo_result` and `market_context`. |

#### Default Settings

| Parameter | Default | Range | Description |
|---|---|---|---|
| `hurst_min_scale_cutoff` | `12` | 4 – 30 | Minimum R/S scale (in ticks). Scales below this are excluded from Hurst computation. |
| `hurst_ai_confidence_threshold` | `80.0` | 50 – 95 | OTEO score floor. Trades below this confidence level are vetoed. |

#### Files

| Type | Source | Installed Destination |
|---|---|---|
| Backend | `backend/hurst_ai_noise.py` | `app/backend/services/extensions/hurst_ai_noise.py` |
| Frontend | `frontend/HurstAiSettings.jsx` | `app/frontend/src/components/shared/HurstAiSettings.jsx` |

---

## Installation

Each plugin is installed via its own `install.py` script. Run from the **workspace root** (`c:\v3\OTC_SNIPER`):

### Install Adaptive Edge (Premium)

```powershell
conda activate QuFLX
python plugins/adaptive_edge/install.py
```

### Install AI Pulse & Noise Filter (Elite)

```powershell
conda activate QuFLX
python plugins/ai_pulse_noise/install.py
```

### What the installer does

1. **Copies backend files** → `app/backend/services/extensions/`
2. **Copies frontend files** → `app/frontend/src/components/shared/`
3. **Injects imports & component references** into `GhostTradingWidget.jsx` (with `.bak` backup created first)
4. **Auto-discovery** — The `ExtensionManager` detects new `.py` files on next server restart. No manual registration needed.

> [!IMPORTANT]
> After installing a plugin, **restart the backend server** and **rebuild the frontend** for changes to take effect.

---

## Uninstallation

Each plugin supports clean, atomic uninstallation:

### Uninstall Adaptive Edge

```powershell
python plugins/adaptive_edge/install.py --uninstall
```

### Uninstall AI Pulse & Noise Filter

```powershell
python plugins/ai_pulse_noise/install.py --uninstall
```

### What the uninstaller does

1. **Reverts code injections** — Replaces injected code with the original `find_pattern` from the manifest.
2. **Deletes copied files** — Removes backend and frontend files from their installed destinations.
3. **Cleans up backups** — Removes `.bak` files created during installation.

> [!WARNING]
> If you manually edited any injected target files (e.g., `GhostTradingWidget.jsx`) after installation, the uninstaller's pattern matching may fail. In that case, restore from the `.bak` backup manually.

---

## Configuration

### Backend Configuration

Plugin settings are passed through the `ExtensionManager` via the strategy API. Settings persist in the Zustand store on the frontend and are synced to the backend on each API call.

### Frontend Configuration

When a plugin is installed and active, its settings panel renders inline within the **Ghost Trading Widget**:

- **Adaptive Edge** → `HurstExpirySettings` component (gold accent, `#ffb800`)
- **AI Pulse & Noise Filter** → `HurstAiSettings` component (purple accent)

Settings are controlled via sliders and update the Zustand `useSettingsStore` in real-time.

### License Detection

The platform dynamically detects installed plugins by checking for registered extensions in the `ExtensionManager`:

| State | Badge | Description |
|---|---|---|
| Plugin installed & active | `🟢 Active` | Extension is registered and processing ticks. |
| Plugin not installed | `🔒 Locked` | UI shows feature preview with upsell messaging. |

---

## Plugin Development Guide

To create a new plugin, follow this structure:

### 1. Create the plugin directory

```
plugins/
└── your_plugin_name/
    ├── manifest.json          # File mapping & injection points
    ├── install.py             # Install/uninstall script
    ├── backend/
    │   └── your_module.py     # BaseExtension subclass
    └── frontend/
        └── YourSettings.jsx   # React settings component
```

### 2. Define the manifest

```json
{
  "plugin_id": "your_plugin_name",
  "name": "Your Plugin Display Name",
  "version": "1.0.0",
  "description": "What this plugin does.",
  "backend_files": [
    {
      "src": "backend/your_module.py",
      "dest": "app/backend/services/extensions/your_module.py"
    }
  ],
  "frontend_files": [
    {
      "src": "frontend/YourSettings.jsx",
      "dest": "app/frontend/src/components/shared/YourSettings.jsx"
    }
  ],
  "injection_points": [
    {
      "target_file": "app/frontend/src/components/shared/GhostTradingWidget.jsx",
      "find_pattern": "// exact text to find in target",
      "replacement_code": "// replacement including your additions"
    }
  ]
}
```

### 3. Implement the backend extension

```python
from app.backend.services.extensions.base import BaseExtension

class YourExtension(BaseExtension):
    def __init__(self, settings):
        defaults = {"enabled": True, "your_param": 42}
        defaults.update(settings)
        super().__init__(defaults)

    def on_tick_processed(self, asset, price, timestamp, oteo_result, market_context):
        # Append data to oteo_result per tick
        return oteo_result

    def on_candle_closed(self, asset, closed_candle, market_context):
        # Heavy computation on candle close
        return {}

    def on_consider_signal(self, asset, price, oteo_result, config):
        # Return (True, None) to allow, (False, "reason") to veto
        return True, None
```

### 4. Copy the install script

Copy `install.py` from an existing plugin — the logic is fully manifest-driven and requires no modification.

> [!TIP]
> The `ExtensionManager` auto-discovers any `.py` file in `app/backend/services/extensions/` that contains a `BaseExtension` subclass. No manual registration is needed — just drop the file and restart.

---

## File Structure

```
plugins/
├── README.md                              ← You are here
│
├── adaptive_edge/                         ← Premium Tier
│   ├── manifest.json                      # File mapping & injection definitions
│   ├── install.py                         # Atomic install/uninstall script
│   ├── backend/
│   │   └── hurst_adaptive_expiry.py       # Vectorized R/S + regime state machine
│   └── frontend/
│       └── HurstExpirySettings.jsx        # Expiry threshold sliders
│
└── ai_pulse_noise/                        ← Elite Tier
    ├── manifest.json                      # File mapping & injection definitions
    ├── install.py                         # Atomic install/uninstall script
    ├── backend/
    │   └── hurst_ai_noise.py              # Noise-filtered Hurst + AI confidence gate
    └── frontend/
        └── HurstAiSettings.jsx            # Scale cutoff & confidence sliders

app/backend/services/extensions/           ← Core Hook System (not a plugin)
├── __init__.py
├── base.py                                # BaseExtension abstract class
└── manager.py                             # ExtensionManager auto-discovery
```

---

<p align="center">
  <strong>OTC SNIPER</strong> — Precision Binary Options Intelligence<br/>
  <sub>Built with the Hurst Exponent at its core.</sub>
</p>
