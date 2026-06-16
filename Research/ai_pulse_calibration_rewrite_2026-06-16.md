# Research: AI Pulse Calibration Extension & Ghost Protocol Suggestions
**Date:** 2026-06-16  
**Author:** @Researcher (AI Assistant Pair Programmer)  
**Status:** Under Review  

## 1. Feature Overview & Requirements
The goal is to merge the capabilities of the deprecated Calibration feature into the **AI Pulse** pipeline. Instead of a distinct, standalone calibration run, the AI Pulse will dynamically analyze the market context alongside the current Ghost Trading session metrics to provide continuous, settings-aware updates to the Ghost Controller.

### Key Requirements
1. **Explicit Direction & Actionable Insights:**
   - Extend the AI Pulse insight messages.
   - Include explicit trade direction recommendations (`CALL` or `PUT`) under defined confluence conditions.
   - Provide estimated entry wait times (e.g., "wait 2-3 mins for pullback").
   - Mention target price levels or price ranges for entries.
2. **Session & Settings-Aware Prompts:**
   - Supply the AI with current Ghost Controller configurations.
   - Supply current session performance (PnL, wins, losses, win rates) and per-condition (regime, asset, tick health) metrics.
3. **Structured Ghost Protocol Suggestions:**
   - Prompt the AI to output suggested Ghost Controller parameters as a clean JSON block within its response.
   - Suggested settings should cover:
     - `ghostAmount`
     - `autoGhostExpirationSeconds` (validated options: 15, 30, 60, 120, 300)
     - `ghostMaxTradesPerTimeframe` & `ghostTimeframeSeconds`
     - `ghostMinConfidence` & `ghostMinConfidenceEnabled`
     - `ghostMaxConfidence` & `ghostMaxConfidenceEnabled`
     - `autoGhostManipulationSeverityThreshold` & `autoGhostBlockOnManipulation`
     - `ghostMinZScore` & `ghostMinZScoreEnabled`
     - `ghostMaxZScore` & `ghostMaxZScoreEnabled`
     - `ghostRegimeGateEnabled`
     - `ghostAllowedRegimes` (list)
     - `ghostRequireRegimeStable`
     - `whitelistAssets` (specific assets to star/prefer)
4. **Update Ghost Protocol Action:**
   - In the frontend **AI Tools Tab**, display the latest suggestion parameters.
   - A single-click button **"Update Ghost Protocol"** that applies the suggested settings to the Zustand settings store, which will trigger the auto-sync mechanism to the backend.
   - Automatically star/favorite the assets suggested by the AI by adding them to the `starredAssets` group in `useAssetStore`.
5. **AI Chat Panel Extension:**
   - Add a button **"Extend to Chat"** that switches the current workspace view to the main AI chat panel and populates the prompt draft box with the context of the latest suggestion and pulse insight for further questioning.

---

## 2. Architecture & Code Analysis

### 2.1 Backend Pipeline (Python)
The background loop for the AI Pulse is located in [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py#L554-L635). It executes at an interval defined by `self.auto_ghost.config.ai_pulse_interval_seconds`.

#### Proposed Python Prompt Injection
We will enrich the user and system prompts in `streaming.py` inside `_run_ai_pulse_insight` by query-joining the current state of `self.auto_ghost`.

```python
# Extract current settings
config = self.auto_ghost.config
allowed_regimes = config.allowed_regimes or []
min_z = config.min_zscore if config.min_zscore_enabled else "Disabled"
max_z = config.max_zscore if config.max_zscore_enabled else "Disabled"
manip_threshold = config.manipulation_severity_threshold if config.block_on_manipulation else "Disabled"
min_conf = config.min_confidence if config.min_confidence_enabled else "Disabled"
max_conf = config.max_confidence if config.max_confidence_enabled else "Disabled"

# Extract session performance
session_trades = self.auto_ghost._session_trade_count
session_wins = self.auto_ghost._session_wins
session_losses = self.auto_ghost._session_losses
session_pnl = self.auto_ghost._session_pnl
win_rate = (session_wins / max(1, session_trades)) * 100.0

# Extract condition-based win rates
condition_stats = self.auto_ghost.get_condition_stats()
```

#### Structured JSON Parsing in Backend
To extract the suggestions cleanly, the backend will process the text returned by the AI. We will search for a JSON block marked by ` ```json ... ``` ` or standard curly braces `{ ... }`.

```python
import re
import json

def extract_suggestions(text: str) -> tuple[str, dict]:
    # Extract json block
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL | re.IGNORECASE)
    if not json_match:
        json_match = re.search(r'(\{.*?\})', text, re.DOTALL)
    
    clean_message = text
    suggestions = {}
    
    if json_match:
        try:
            json_str = json_match.group(1)
            suggestions = json.loads(json_str)
            # Remove the JSON text from the user-visible message
            clean_message = text.replace(json_match.group(0), "").strip()
        except Exception as e:
            logger.warning(f"Failed to parse AI pulse suggestions JSON: {e}")
            
    return clean_message, suggestions
```

### 2.2 Socket.IO Interface
The socket notification event `notification` will be updated to include the parsed suggestions dictionary:
```python
await self.sio.emit("notification", {
    "type": "ai_pulse",
    "message": clean_message,
    "timestamp": time.time(),
    "suggestions": suggestions,  # Dictionary containing suggested keys and values
})
```

### 2.3 Frontend State Management (Javascript)
We need to update:
1. [useNotificationStore.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/stores/useNotificationStore.js): Update `addNotification` to accept and store the `suggestions` field.
2. [useAssetStore.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/stores/useAssetStore.js): Add a new action `setStarredAssets(starredAssets)` to easily whitelist assets.
3. [App.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/App.jsx): Forward the `suggestions` property from socket data into the notification store.

---

## 3. UI/UX Design Proposals

### 3.1 AI Tools Tab in Ghost Controller Widget
Currently, `activeTab === 'ai'` displays configuration parameters. We will keep these parameters at the top (or in a collapsible section) and add the **AI Pulse Panel**:

- **Latest Market Insight Panel:**
  - Vibrant yellow text indicators showing trade directions (`CALL` or `PUT`).
  - Clear wait times & price boundaries.
- **Dynamic Suggestions Card (Only visible if suggestions are present):**
  - Side-by-side view comparing "Current Gate Value" vs "AI Suggested Value" (e.g. `Allowed Regimes: [Choppy] -> [Range Bound, Trend Pullback]`).
  - Whitelisted Assets: Displays a row of small starred badges representing assets the AI wants the user to target.
  - Action Buttons:
    - **Update Ghost Protocol** (Premium amber color, applies values to Zustand, auto-syncs to API, stars assets, triggers success toast).
    - **Extend to Chat** (A gray/ghost outline button, opens AI tab, prepopulates question, closes widget).

---

## 4. Viability & Safety Assessment
- **Highly Viable:** The settings store and backend routes are already built to sync in real-time when Zustand properties are modified. No new API endpoints are strictly required for applying the settings because the store's automatic sync mechanism is already wired in.
- **Defensive Design:**
  - The JSON parser on the backend uses try/catch blocks and regex filters to avoid crashes on malformed AI text outputs.
  - The suggested parameter names are validated on both the backend and frontend (via the existing `validateSettings` schema in `useSettingsStore.js`) to prevent corrupted parameters from being injected.
  - Quick Select (Favorites) modifications are local to the frontend, which are safe and non-blocking for trade executions.
