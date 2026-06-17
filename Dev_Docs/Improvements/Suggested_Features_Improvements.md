# Suggested Features & Improvements: AI Tools Tab

This document outlines proposed UI/UX and backend enhancements to further optimize the AI Advisory, Pulse Insights, and Ghost Protocol Suggestions inside the OTC SNIPER platform.

---

## 1. UI/UX Enhancements

### 1.1 Dynamic "Protocol Status" Badge
* **Concept:** A visual status chip at the top of the AI Tools tab indicating if the active settings of the Ghost Controller match the AI's latest suggestions.
* **States:**
  * 🟢 **`CALIBRATED`** (Active settings are in sync with the latest AI suggestions).
  * 🟡 **`OUT OF SYNC`** (AI has proposed new parameters, but they haven't been applied yet. The "Update Ghost Protocol" button will pulse gently to draw attention).
  * ⚪ **`WAITING`** (AI Pulse is running but hasn't gathered enough trade data to recommend calibration parameters).

### 1.2 Applied Protocol History Log
* **Concept:** A small, collapsible panel in the widget showing a historical record of applied configurations.
* **Details:**
  * Tracks when the user clicked "Update Ghost Protocol" during the session.
  * Shows parameter deltas (e.g. `Z-Score: Default -> Min -0.8`, `Regimes: +Range Bound`).
  * Allows a user to rollback to a previous configuration if performance degrades.

---

## 2. AI Prompt & Suggestion Logic

### 2.1 Suggestion Confidence Rating
* **Concept:** The AI includes a `confidence` rating inside the suggestions JSON block: `"confidence": "high" | "medium" | "low"`.
* **Heuristics:**
  * **Low:** Session has $< 5$ trades (statistical sample size is too small; suggestions are preliminary).
  * **Medium:** Session has $5 - 15$ trades.
  * **High:** Session has $> 15$ trades (strong win/loss clustering patterns detected).
* **UI Representation:** Displays next to the suggestions card (e.g. `AI Confidence: High (based on 18 trades)`).

### 2.2 Developer Mode Prompt Customizer
* **Concept:** A settings text area in the UI (visible when Developer Mode is active) that allows developers to append custom prompt constraints.
* **Examples of Custom Constraints:**
  * *"Do not suggest whitelisting EUR pairs today."*
  * *"Strictly maintain a minimum Z-Score gate of at least -0.5."*
* **Implementation:** The custom instructions string is saved in `useSettingsStore` and injected dynamically into the backend system message wrapper in `streaming.py`.

---

## 3. Microstructure & Market Context Contextualization

### 3.1 Adaptive Cooldown Recommendations
* **Concept:** The AI suggests individual asset cooldown times based on recent performance.
* **Details:**
  * If `GBPUSD_otc` is experiencing a sequence of rapid regime switches or high manipulation severity, the AI suggests increasing its specific cooldown from 30s to 120s: `"autoGhostPerAssetCooldownSeconds": 120`.

### 3.2 Dynamic Z-Score Bounds Tuning
* **Concept:** AI adjusts the Z-score boundaries based on the volatility of the session.
* **Details:**
  * For high-volatility regimes, the AI suggests narrowing bounds (e.g. `-0.3 to 1.2`) to capture only the cleanest signals.
  * For quiet range-bound regimes, it expands bounds (e.g. `-0.8 to 1.8`) to avoid suppressing valid trades.
