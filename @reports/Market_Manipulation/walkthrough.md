# Walkthrough: Market Manipulation Severity scoring

We have evolved the market manipulation detection flags from static binary true/false values to continuous severity scores ($0.0 - 1.0$), implemented exponential decay over consolidations, corrected the baseline average velocity to use Mean Absolute Velocity, and added a configurable execution gate in Auto-Ghost.

---

## Changes Made

### 1. Backend Service Layer
- **[manipulation.py](file:///c:/v3/OTC_SNIPER/app/backend/services/manipulation.py)**:
  - Replaced the signed average velocity baseline with rolling **Mean Absolute Velocity (MAV)** to prevent positive/negative cancellation.
  - Implemented **Exponential Decay** ($e^{-t/5.0}$) over the 15-second shock consolidation window to continuously decay push-snap severity.
  - Scaling pinning severity proportionally ($1.0 - \frac{\text{price\_range}}{\text{threshold}}$).
  - Only return keys with severity $> 0.01$, returning `{}` if none exist (guarantees backwards compatibility).
- **[auto_ghost.py](file:///c:/v3/OTC_SNIPER/app/backend/services/auto_ghost.py)**:
  - Added `manipulation_severity_threshold` (default `0.0`) configuration and status fields.
  - Updated `consider_signal()` to block trade execution only if any active severity is $\ge$ the threshold.
- **[streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py)**:
  - Added a dynamic OTEO score discount penalty: $\text{Adjusted Score} = \text{Score} - \text{Severity} \times 20.0$.
  - Integrated automatic confidence and actionability downgrades on penalized signals (downgrades HIGH to MEDIUM if $< 70$, downgrades to LOW and disables actionable if $\le 55$).
- **[strategy.py](file:///c:/v3/OTC_SNIPER/app/backend/api/strategy.py)**:
  - Exposed `auto_ghost_manipulation_severity_threshold` inside Pydantic requests schema and post updates handler.

### 2. Frontend Settings & Synchronization
- **[useSettingsStore.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/stores/useSettingsStore.js)**:
  - Integrated state settings for `autoGhostManipulationSeverityThreshold` and its set actions.
- **[App.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/App.jsx)**:
  - Synchronized frontend settings store to backend runtime strategy config on adjustment events.
- **[AppSettings.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/settings/AppSettings.jsx)**:
  - Rendered a new **Manipulation Severity Gate** slider control in the "Confidence Gates & Alerts" settings panel.

### 3. Frontend Visualization & Stream Integration
- **[useStreamConnection.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/hooks/useStreamConnection.js)**:
  - Preserved numeric floats in the websocket parser when reading manipulation payloads.
- **[chartUtils.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/trading/chartUtils.js)**:
  - Formatted active manipulation warning badges to print severity percentage values (e.g. `Push & Snap (85%)` or `Pinning (42%)`).

---

## Verification Results

### 1. Automated Unit & Regression Tests
We created a new test suite file **[test_manipulation_severity.py](file:///c:/v3/OTC_SNIPER/test_manipulation_severity.py)** checking:
1. MAV baseline calculation accuracy and resistance to fake spike triggers.
2. Push & Snap exponential decay rates at 0s, 5s, and 25s.
3. Pinning severity ranges between 0.0 and 1.0.
4. Auto-Ghost trade filtering based on adjustable thresholds.

All tests passed successfully:
```
Ran 4 tests in 0.033s

OK
```

We also ran the full system regression suites:
- Auto-Ghost & Level 3: `18/18` tests passed.
- OTEO Levels Backtesting: `21/21` tests passed.
- Level 3 Phase 1-3 Core: `39/39` tests passed.

---

### 2. Frontend Compilation & Bundle Check
A production build was executed inside `app/frontend`:
```
vite v6.4.1 building for production...
✓ 1689 modules transformed.
✓ built in 5.48s
dist/assets/index-dmmv0hWI.js                  455.98 kB │ gzip: 126.55 kB
```
The application compiles cleanly with zero bundler issues.
