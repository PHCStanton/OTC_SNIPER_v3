# Forensic Analysis: UI/UX Mismatch & Stitch Design Language Refactoring Assessment
Date: June 5, 2026
Author: Antigravity AI Engineering Team (via @Investigator and @UI-Designer)

---

## 1. Summary
The SIGNAL_SNIPER application currently exhibits a UI split-personality. While `AppSettings.jsx` implements the premium, high-contrast **Stitch Design Language** (featuring `#ffb800` amber-yellow accents, heavy `font-black` uppercase typography, high-tracking letter spacing, `#1a1c22` card wrappers, and custom input/toggle components), the rest of the application still uses a legacy Canary Yellow style (featuring `#f5df19` canary-yellow accents, rounded-3xl/2xl cards with `#151a22` backgrounds, softer typography, and legacy inputs).

To achieve platform uniformity, we must harmonize the global styles and refactor all frontend components to adopt the premium Stitch look and feel.

---

## 2. Key Aesthetic Mismatches

### A. Accent Colors
*   **Legacy Style (Rest of App):** Uses `#f5df19` (a bright canary yellow) for badges, toggles, borders, active text, stars, and chart indicators.
*   **Stitch Style (AppSettings):** Uses `#ffb800` (a deep, premium amber-yellow) for primary actions, active nodes, toggles, and highlights.

### B. Cards and Containers
*   **Legacy Style:** Cards use `rounded-3xl` / `rounded-2xl` with a `#151a22` background and a standard border of `border-white/5`.
*   **Stitch Style:** Cards use `rounded-[20px]` with a `#1a1c22` background, an inner padding of `p-6`, `shadow-xl`, and `border-white/5` (e.g., `SectionCard`).

### C. Typography and Casing
*   **Legacy Style:** Mixed case for headers and options, standard tracking, and standard weights (`font-bold`, `font-semibold`).
*   **Stitch Style:** Aggressive typography using:
    *   `font-black` (font weight 900) for headers and interactive options.
    *   `uppercase` casing for almost all headers, titles, labels, options, and descriptions.
    *   Wide tracking (`tracking-wider`, `tracking-widest`, `tracking-[0.15em]`) for metadata labels and tags.
    *   Tight tracking (`tracking-tighter`) for primary page titles.

### D. Form Controls
*   **Legacy Inputs:** Use white background, black bold text, with standard input heights and thin borders. Toggles use standard round switches with `translate-x-5` transition offsets.
*   **Stitch Inputs:**
    *   `NumberInput` has a fixed height of `h-14`, a white background, inner shadow (`shadow-inner`), a prefix icon block on `bg-gray-50 text-gray-400`, `font-black text-black` input, and a stylized grey suffix block (`bg-gray-100 px-4 text-[10px] font-black uppercase tracking-widest text-gray-500 border-l border-gray-200`).
    *   `Toggle Switch` uses a custom height/width (`h-6 w-11`), a grey/amber background transition (`bg-[#2d3139]` to `bg-[#ffb800]`), and a custom transition offset (`translate-x-1` to `translate-x-6`).
    *   `Select Options` are styled with custom chevron overlays and heavy text.

---

## 3. Scope of Affected Files

Based on our forensic search, the Canary Yellow style (`#f5df19`) and softer typography are present in **25+ files** across the application. The major files that require refactoring are:

| Component Path | Current Visual Language | Required Stitch Modifications |
|---|---|---|
| **Layout & Shell** | | |
| [LeftSidebar.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/layout/LeftSidebar.jsx) | `#f5df19` active tabs, quick select star, toggle switches, text tags. | Standardize to `#ffb800` accent. Update toggle switch classes. Apply uppercase tracked typography for labels and categories. |
| [TopBar.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/layout/TopBar.jsx) | Canary yellow indicators, normal weights. | Convert accent to amber-yellow, apply `font-black uppercase` to titles, system status labels, and stats. |
| [GlobalTimer.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/layout/GlobalTimer.jsx) | Canary yellow clock, normal button weights. | Apply Stitch fonts, `#ffb800` active mode indicators, and font-black timers. |
| **Settings Workspace** | | |
| [SettingsView.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/settings/SettingsView.jsx) | `#f5df19` tab outlines/fill, radial gradient, legacy header format. | Apply Stitch primary buttons, header layout, `#ffb800` accent, and uppercase tracked text. |
| [AccountSettings.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/settings/AccountSettings.jsx) | Legacy `PanelCard`, canary yellow state highlights. | Replace `PanelCard` with `SectionCard`. Refactor SSID inputs/rows. Update button and badge styles. |
| [RiskSettings.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/settings/RiskSettings.jsx) | Legacy `SectionCard`, `#f5df19` inputs and toggles. | Replace local card with `SectionCard`. Replace inputs with `NumberInput` and toggles with Stitch toggles. Change accent to `#ffb800`. |
| **Trading Terminal** | | |
| [TradingWorkspace.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/trading/TradingWorkspace.jsx) | Legacy canary wrapper. | Update icon highlights and typography. |
| [TradePanel.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/trading/TradePanel.jsx) | Canary yellow focus rings, legacy buttons. | Re-style number inputs, selection pills, and primary buttons using the Stitch specifications. |
| [TradeHistory.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/trading/TradeHistory.jsx) | `#f5df19` highlights, legacy action buttons. | Update active tabs, list actions, and text casing to uppercase font-black. |
| [TradeDetailsModal.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/trading/TradeDetailsModal.jsx) | Canary yellow SVG lines, chips, and labels. | Update all SVG fill/stroke colors to `#ffb800`, chip styles, and header formats. |
| [Sparkline.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/trading/Sparkline.jsx) | Canary gradients, telemetry labels. | Convert grid overlays and text items to the Stitch typography. Use `#ffb800` active states. |
| [MultiChartView.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/trading/MultiChartView.jsx) | Card margins, outlines, stars in canary. | Standardize to `#ffb800` and uppercase font-black labels. |
| [OTEORing.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/trading/OTEORing.jsx) | SVG stroke gradient using `#f5df19`. | Update stroke gradient to `#ffb800`. |
| **Journal & Analytics** | | |
| [JournalView.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/journal/JournalView.jsx) | Canary buttons, icons, filters. | Apply Stitch style to header actions, status widgets, and tab controls. |
| [StatCard.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/journal/StatCard.jsx) | Softer typography and borders. | Apply `SectionCard`-like formatting. Convert labels to wide tracking uppercase. |
| [StreakAnalytics.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/journal/StreakAnalytics.jsx) | Legacy container. | Standardize card margins, borders, and badge styling. |
| **Shared & Utility** | | |
| [GhostTradingWidget.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/shared/GhostTradingWidget.jsx) | Floating trigger and badge in `#f5df19`. | Standardize to `#ffb800` styling and Stitch font weights. |
| [ToastContainer.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/shared/ToastContainer.jsx) | Toasts themed with `#f5df19` border/glow. | Harmonize border/glow to `#ffb800` theme. |
| [PercentageGauge.jsx](file:///c:/v3/OTC_SNIPER/app/frontend/src/components/shared/PercentageGauge.jsx) | Default fill color `#f5df19`. | Update default gauge fill to `#ffb800`. |

---

## 4. Proposed Refactoring Steps

### Phase 1: Shared Core Components & Global Variables
1. Define unified components in a shared settings area or use `AppSettings`' layouts:
    *   `SectionCard`
    *   `InputGroup`
    *   `NumberInput`
    *   `ToggleSwitch`
2. We should ideally export these from a shared module (e.g. `app/frontend/src/components/shared/FormControls.jsx` or similar) to prevent code duplication, or keep them localized if we want strictly self-contained settings pages. However, to satisfy **Separation of Concerns** and **Code Reuse**, exporting these shared UI components is highly recommended.

### Phase 2: Shell & Layout Alignment
1. Refactor `TopBar`, `LeftSidebar`, `RightSidebar`, `GlobalTimer`, `ToastContainer` and `GhostTradingWidget` to use `#ffb800` and uppercase tracked text.
2. Standardize scrollbars and hover indicators.

### Phase 3: Settings Views Refactoring
1. Align `SettingsView`, `AccountSettings`, and `RiskSettings` by reusing the new `SectionCard`, `NumberInput`, and toggle switches.
2. Convert all colors to `#ffb800`.

### Phase 4: Trading Panels & Charts
1. Update `TradePanel` buttons, custom duration selectors, and input sizing.
2. Standardize `TradeHistory` and `TradeDetailsModal` layout structure, replacing Canary Yellow elements with Stitch elements.
3. Update SVG coordinates and colors in `OTEORing` and `TradeDetailsModal`.

### Phase 5: Journal & Analytics Page
1. Convert `JournalView` header actions and stats panels to the Stitch color scheme and card styles.

---

## 5. Risk Assessment & Safe Execution
*   **Zero Silent Failures:** When modifying form fields, ensure that input validation handlers and change callbacks are perfectly preserved. We must not break the state synchronization hooks that bind to the Zustand stores.
*   **Layout Breaks:** Since Stitch uses aggressive casing and tracking, we must verify that text labels do not overflow or wrap awkwardly on smaller screen heights and widths.
*   **Incremental Testing:** Run local validation builds after updating each view to ensure zero compilation or syntax errors.
