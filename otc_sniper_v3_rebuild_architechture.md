# 🏗️ OTC SNIPER v3 — Updated Architecture (Workspace + App Root)

**Updated:** 2026-03-26 — Added Chrome lifecycle management, ops layer, and manual-first SSID workflow per cross-project architecture review against QuFLX-v2.

Building on the previous plan, here's the expanded architecture incorporating all additional requirements, the new workspace/app-root split, and the **Phase 0 ops layer** for Chrome session management and SSID input.

---

## 📁 Updated Directory Structure

### Workspace Root

```
C:\v3\OTC_SNIPER\
├── Dev_Docs/                         # Implementation plans and living design docs
├── legacy_reference/                 # Read-only legacy references copied from v2
├── ssid_integration_package/         # Integration package reference / vendored source
├── app/                              # Functional application root (backend + frontend)
├── .clinerules/                      # Workspace-level agent rules
├── .agent-memory/                    # Workspace memory/context files
├── .env                              # Workspace-level env (optional)
└── otc_sniper_v3_rebuild_architechture.md
```

### Functional App Root

```
app/
├── backend/
├── frontend/
├── data/
├── .env
├── README.md
└── start.py
```

> **Important:** The workspace root is `C:\v3\OTC_SNIPER`, but the actual functional OTC SNIPER app must live under `C:\v3\OTC_SNIPER\app`.

### Application Structure (inside `app/`)

```
otc_sniper_v3/
├── .clinerules/                          
├── .agent-memory/                        
│
├── backend/
│   ├── main.py                           # FastAPI + Socket.IO (single server)
│   ├── config.py                         # Pydantic Settings
│   ├── dependencies.py                   # DI container
│   │
│   ├── session/                          # 🔑 SSID SESSION (from integration package)
│   │   ├── manager.py                    
│   │   ├── pocket_option_session.py      
│   │   └── models.py                     
│   │
│   ├── brokers/                          # 🔌 MULTI-BROKER
│   │   ├── base.py                       
│   │   ├── registry.py                   
│   │   └── pocket_option/
│   │       ├── adapter.py                
│   │       ├── assets.py                 # normalize + verified list
│   │       └── config.py                 
│   │
│   ├── api/                              # 🌐 THIN ROUTE CONTROLLERS
│   │   ├── ops.py                        # Phase 0: Chrome lifecycle + combined status
│   │   ├── session.py                    # Phase 0: SSID connect/disconnect/status/ssid-status
│   │   ├── auth.py                       
│   │   ├── trading.py                    
│   │   ├── assets.py                     
│   │   ├── settings.py                   
│   │   └── risk.py                       # Risk management endpoints
│   │
│   ├── services/                         # 📊 BUSINESS LOGIC
│   │   ├── trade_service.py              
│   │   ├── signal_engine.py              # OTEO + manipulation
│   │   ├── ghost_trader.py               
│   │   ├── risk_service.py              # NEW: Session risk tracking
│   │   └── settings_service.py           
│   │
│   ├── streaming/                        # 📡 REAL-TIME
│   │   ├── gateway.py                    
│   │   ├── collector.py                  
│   │   └── enrichment.py                 
│   │
│   ├── data/                             # 💾 DATA ACCESS LAYER (Supabase-ready)
│   │   ├── __init__.py
│   │   ├── repository.py                # Abstract repository interface
│   │   ├── local_store.py               # JSONL file-based (current)
│   │   ├── supabase_store.py            # Future: Supabase adapter (same interface)
│   │   ├── tick_logger.py               # Per-asset JSONL with rotation
│   │   ├── signal_logger.py             # Signal JSONL logging
│   │   └── trade_logger.py              # Trade result logging (live + ghost)
│   │
│   ├── auth/                             
│   │   ├── tokens.py                     
│   │   └── middleware.py                 
│   │
│   ├── models/                           # Pydantic everywhere
│   │   ├── requests.py                   
│   │   ├── responses.py                  
│   │   └── domain.py                     
│   │
│   └── pocketoptionapi/                  # Vendored API
│       └── ...
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx                      
│   │   ├── App.jsx                       # Router + MainLayout
│   │   │
│   │   ├── api/                          # API client layer
│   │   │   ├── client.js                 
│   │   │   ├── opsApi.js                # Phase 0: Chrome start/stop/status, session connect/disconnect
│   │   │   ├── authApi.js                
│   │   │   ├── tradingApi.js             
│   │   │   ├── assetsApi.js              
│   │   │   ├── settingsApi.js            
│   │   │   ├── riskApi.js               
│   │   │   └── streamApi.js              
│   │   │
│   │   ├── stores/                       # Zustand
│   │   │   ├── useOpsStore.js           # Phase 0: Chrome/SSID status, busy flags, start/stop actions
│   │   │   ├── useAuthStore.js           
│   │   │   ├── useTradingStore.js        
│   │   │   ├── useAssetStore.js          
│   │   │   ├── useStreamStore.js         
│   │   │   ├── useSettingsStore.js       
│   │   │   ├── useRiskStore.js          # Session risk state
│   │   │   └── useLayoutStore.js        # Sidebar collapse state
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── MainLayout.jsx        # 3-column: Left | Center | Right
│   │   │   │   ├── TopBar.jsx            # Status + ops
│   │   │   │   ├── LeftSidebar.jsx      # NEW: Collapsible asset list
│   │   │   │   └── RightSidebar.jsx     # NEW: Collapsible nav + tab views
│   │   │   │
│   │   │   ├── trading/
│   │   │   │   ├── ChartArea.jsx         # Sparkline + OTEO ring + Risk chart
│   │   │   │   ├── Sparkline.jsx         # SVG price chart
│   │   │   │   ├── OTEORing.jsx          
│   │   │   │   ├── TradePanel.jsx        # CALL/PUT + amount + expiry
│   │   │   │   ├── TradeHistory.jsx     # Unified: session table + results
│   │   │   │   └── MultiChartView.jsx   # KEEP: Multi-asset grid
│   │   │   │   └── MiniSparkline.jsx    # KEEP: Mini chart cards
│   │   │   │
│   │   │   ├── risk/                    # NEW: Risk management components
│   │   │   │   ├── VerticalRiskChart.jsx # Rebuilt from TSX → JSX
│   │   │   │   ├── SessionRiskPanel.jsx  # Quick risk overview (next to sparkline)
│   │   │   │   └── RiskSummaryCards.jsx  # P/L, Win Rate, Growth stats
│   │   │   │
│   │   │   ├── auth/
│   │   │   │   ├── LoginScreen.jsx       
│   │   │   │   └── AccountSwitcher.jsx   
│   │   │   │
│   │   │   ├── settings/
│   │   │   │   ├── SettingsView.jsx      # Container with tabs
│   │   │   │   ├── AccountSettings.jsx  # NEW: SSID, broker, credentials
│   │   │   │   └── AppSettings.jsx      # NEW: OTEO, trading, ghost, UI prefs
│   │   │   │
│   │   │   └── shared/
│   │   │       ├── ErrorBoundary.jsx     
│   │   │       ├── Toast.jsx             
│   │   │       └── LoadingSkeleton.jsx   
│   │   │
│   │   ├── hooks/
│   │   │   ├── useStreamConnection.js    
│   │   │   ├── useTradeExecution.js      
│   │   │   ├── useOpsControl.js          
│   │   │   └── useRiskTracking.js       # NEW
│   │   │
│   │   └── utils/
│   │       ├── config.js                 
│   │       ├── formatters.js             
│   │       └── assetUtils.js             
│   │
│   └── ...
│
├── data/                                 # 💾 PRESERVED DATA STRUCTURE
│   ├── _db_schema.json                   # ✅ KEEP: Supabase migration blueprint
│   ├── auth/
│   │   ├── users.json
│   │   ├── credentials/
│   │   └── sessions/
│   ├── tick_logs/                        # ✅ KEEP: Per-asset JSONL with archive
│   │   ├── _manifest.json
│   │   ├── {ASSET}/                      # Active tick files
│   │   └── archive/{ASSET}/             # Rotated files
│   ├── signals/                          # ✅ KEEP: JSONL signal logs
│   ├── ghost_trades/
│   │   ├── sessions/                     # ✅ KEEP: JSONL session files
│   │   └── stats/                        # ✅ KEEP: Per-asset + aggregate stats
│   ├── live_trades/                     # NEW: Real trade results (same schema)
│   │   ├── sessions/
│   │   └── stats/
│   ├── settings/
│   │   ├── global.json
│   │   ├── accounts/                     # Per-account settings
│   │   └── brokers/                      # Per-broker config
│   └── data_output/logs/                 # Chrome/collector logs
│
├── .env
├── start.py
└── README.md
```

---

## 🔑 Key Design Decisions for New Requirements

### 1. Settings Architecture (Separated & Extensible)

**Two distinct categories with a registry pattern:**

```
settings/
├── global.json          ← App-wide defaults
├── accounts/
│   ├── demo.json        ← Demo account preferences
│   └── real.json        ← Real account preferences
└── brokers/
    └── pocket_option.json ← Broker-specific config
```

**Backend: Settings Service with Schema Registry**
```python
# services/settings_service.py
class SettingsService:
    """
    Settings are organized into SCOPES:
    - "account.*"  → SSID, broker credentials, account preferences
    - "app.oteo"   → OTEO engine parameters
    - "app.trading" → Trade controls (max concurrent, cooldown, amounts)
    - "app.ghost"  → Ghost trading config
    - "app.ui"     → Theme, layout preferences
    - "app.risk"   → Risk management defaults
    
    Adding a new setting category:
    1. Add scope prefix to VALID_SCOPES
    2. Add Pydantic schema to models/settings.py
    3. Frontend auto-discovers via GET /api/settings/schema
    """
    VALID_SCOPES = ["account", "app.oteo", "app.trading", "app.ghost", "app.ui", "app.risk"]
```

**Frontend: Tab-based Settings View**
```
**SettingsView.jsx (container)**
├── AccountSettings.jsx    ← Tab 1: SSID management, broker selection, credentials
└── AppSettings.jsx        ← Tab 2: Sections auto-generated from schema
    ├── OTEO Engine section
    ├── Trading Controls section
    ├── Ghost Trading section
    ├── Risk Management section
    └── UI Preferences section
```

The key insight: **settings schema is defined once in the backend** and the frontend renders controls dynamically. Adding a new setting = add to schema + it appears in UI automatically.

### Settings Scope Rules

- **Account Settings**: SSID, broker selection, credentials, demo/real account config, session/auth preferences.
- **App Settings**: Navigation, UI layout, trading controls, OTEO config, risk UI config, ghost trading options, component toggles.
- Keep these scopes separate in backend schemas and frontend tabs so features can be added/removed without impacting account security state.

---

### 2. Data Layer (Supabase-Ready Repository Pattern)

The current data structure is excellent. We preserve it exactly and add an abstraction layer:

```python
# data/repository.py
class DataRepository(ABC):
    """Abstract interface — swap local ↔ Supabase without changing business logic."""
    
    @abstractmethod
    async def write_tick(self, tick: TickRecord) -> None: ...
    
    @abstractmethod
    async def write_signal(self, signal: SignalRecord) -> None: ...
    
    @abstractmethod
    async def write_trade(self, trade: TradeRecord) -> None: ...
    
    @abstractmethod
    async def get_trades(self, session_id: str, limit: int) -> List[TradeRecord]: ...
    
    @abstractmethod
    async def get_asset_stats(self, asset: str) -> AssetStats: ...

# data/local_store.py
class LocalFileRepository(DataRepository):
    """Current JSONL file-based storage. Uses _db_schema.json as blueprint."""
    # Writes to tick_logs/{ASSET}/, signals/, ghost_trades/sessions/, live_trades/sessions/
    # Reads _manifest.json for rotation
    # Archives per _db_schema.json retention_days

# data/supabase_store.py (future)
class SupabaseRepository(DataRepository):
    """Same interface, writes to Supabase tables matching _db_schema.json."""
    # Tables created from _db_schema.json columns/indexes
    # Migration script reads _db_schema.json and creates tables
```

**New addition: `live_trades/`** — Same structure as `ghost_trades/` but for real executed trades. Both use identical JSONL schema so they can be queried/exported the same way.

### Data Migration Rule

- Keep JSON/JSONL as the operational source of truth in v3 until a database migration is explicitly enabled.
- The schema in `data/_db_schema.json` remains the migration contract for a future Supabase backend.
- Loggers, repositories, and stats collectors must write through one data-access layer so a database swap is isolated to the repository implementation.

---

### 3. Layout: Collapsible Left + Right Sidebars

```
┌──────────────────────────────────────────────────────────────────┐
│  TopBar: [WS●] [CHROME●] [STREAM●] [SSID●]    [Profile ▾]     │
├────────┬─────────────────────────────────────────┬───────────────┤
│ LEFT   │              CENTER                     │    RIGHT      │
│ SIDEBAR│                                         │    SIDEBAR    │
│ (◀ ▶)  │  ┌─────────────────┬──────────────┐    │    (◀ ▶)      │
│         │  │   Sparkline     │ Risk Chart   │    │               │
│ Search  │  │   + OTEO Ring   │ (Vertical)   │    │  Navigation   │
│ ─────── │  └─────────────────┴──────────────┘    │  ──────────── │
│ ★ Quick │                                         │  📊 Trading   │
│ Select  │  ┌────────────────────────────────┐    │  📈 MultiChart│
│ ─────── │  │  Trade Panel                   │    │  ⚙️ Settings  │
│ All     │  │  [CALL]  Amount  Expiry  [PUT] │    │  👻 Ghost     │
│ Assets  │  └────────────────────────────────┘    │  📋 History   │
│ List    │                                         │  🎯 Risk Mgmt │
│         │  ┌────────────────────────────────┐    │               │
│ (from   │  │  Trade History / Session Table  │    │  ──────────── │
│  SSID   │  │  W W L W L  +$50.20            │    │  Active View  │
│  API)   │  │  Session 2: W W W W  +$202.40  │    │  Content      │
│         │  └────────────────────────────────┘    │  Renders Here │
│         │                                         │               │
├────────┴─────────────────────────────────────────┴───────────────┤
│  Status Bar (optional)                                            │
└──────────────────────────────────────────────────────────────────┘
```

**LeftSidebar.jsx** — Collapsible, dedicated to asset discovery:
- Search bar (instant filter)
- Quick Select (starred favourites, localStorage)
- Full asset list with payout badges
- Collapse to icon-only rail (just stars visible)

**RightSidebar.jsx** — Collapsible, navigation + tab views:
- Navigation menu (icon + label when expanded, icon-only when collapsed)
- Active tab content renders in the sidebar body
- Tabs: Trading (default), MultiChart, Settings, Ghost Stats, History, Risk Management
- When collapsed: just navigation icons, clicking expands + shows content

**Layout state managed by `useLayoutStore.js`:**
```javascript
export const useLayoutStore = create((set) => ({
  leftOpen: true,
  rightOpen: true,
  activeTab: 'trading',
  toggleLeft: () => set(s => ({ leftOpen: !s.leftOpen })),
  toggleRight: () => set(s => ({ rightOpen: !s.rightOpen })),
  setActiveTab: (tab) => set({ activeTab: tab, rightOpen: true }),
}));
```

---

### 4. Risk Management (TSX → JSX, Lightweight)

**Rebuilt components (no TypeScript, no external deps):**

| TSX Source | JSX Target | Purpose |
|-----------|-----------|---------|
| `VerticalRiskChart.tsx` | `risk/VerticalRiskChart.jsx` | SVG vertical bar chart (pure SVG, no libs) |
| `SessionTable.tsx` + `TradeHistory` | `trading/TradeHistory.jsx` | Unified: shows W/L badges + session P/L + export |
| `TradeSessionsManager.tsx` | `risk/SessionRiskPanel.jsx` | Compact version next to sparkline |
| `RiskVisualizationPrototype.tsx` | Absorbed into `risk/` components | Config controls become part of Settings |

**SessionRiskPanel.jsx** — The "Quick Risk on the Fly" next to the Sparkline:
```
┌─────────────────┬──────────────┐
│   Sparkline     │  Risk Chart  │
│   + OTEO Ring   │  ┌────────┐  │
│                 │  │ TP +10%│  │
│   ● 1.08542    │  │  ▓▓▓▓  │  │
│                 │  │  ────  │  │
│                 │  │  ░░░░  │  │
│                 │  │ DD -10%│  │
│                 │  └────────┘  │
│                 │  $5193 +3.3% │
└─────────────────┴──────────────┘
```

The VerticalRiskChart sits right next to the Sparkline in the ChartArea, showing real-time session risk position. It updates live as trades complete.

### Risk Layout Rule

- `SessionTable.tsx` and trade-history UI should be unified into one lightweight `TradeHistory.jsx` / `SessionRiskPanel.jsx` flow so the same trade result data powers both the compact quick-view and the detailed session history.
- The risk chart must remain optional and composable, not hard-coupled to the trade history table.

---

### 5. MultiChartView + MiniSparkline (Preserved)

Both components are well-built. They move into `components/trading/` with minimal changes:
- Remove `useRef` inside `useEffect` (React rules violation in current code)
- Socket.IO integration via `useStreamStore` instead of direct socket prop
- Asset normalization via `assetUtils.js`

### MultiChart Rule

- `MultiChartView.jsx` remains a separate multi-asset workspace view.
- `MiniSparkline.jsx` remains the compact, reusable tile component for multi-asset and summary surfaces.
- Keep both components lightweight and driven by the same canonical market-data store.

---

## 🤖 AI API Integration Recommendations

Since QuFLX already has **Grok 4.1 API** integrated, here are the most impactful use cases for OTC SNIPER v3:

### **Tier 1: High Impact, Low Complexity** (Implement First)

#### 1. **Trade Journal AI Analyst**
- **What:** After each trading session, send the session data (trades, P/L, asset, timing, OTEO scores at entry) to Grok
- **Why:** Grok analyzes patterns: "You tend to lose on PUT trades during the first 10 minutes. Your win rate on EURUSD is 72% but only 45% on AUDJPY. Consider focusing on your strongest assets."
- **Implementation:** `POST /api/ai/analyze-session` → sends session JSONL to Grok → returns structured insights
- **Frontend:** "AI Insights" card in the RightSidebar after session ends

#### 2. **Signal Confidence Booster**
- **What:** When OTEO generates a HIGH confidence signal, optionally send the last 50 ticks + OTEO metrics to Grok for a second opinion
- **Why:** Adds a "consensus" layer — if both OTEO and Grok agree, confidence is even higher
- **Implementation:** `services/ai_service.py` → called from `enrichment.py` when OTEO score > 75
- **Frontend:** Small "AI ✓" badge on the signal when Grok confirms

#### 3. **Risk Management Advisor**
- **What:** Feed current session state (balance, P/L, win rate, consecutive losses) to Grok
- **Why:** "You've had 3 consecutive losses. Statistically, your next trade has a 60% chance of winning, but your drawdown is at 7% of your 10% limit. Recommendation: reduce position size by 50% or take a 5-minute break."
- **Implementation:** Triggered when drawdown exceeds 50% of limit or after 3 consecutive losses
- **Frontend:** Toast notification or modal with AI recommendation

### **Tier 2: Medium Impact, Medium Complexity**

#### 4. **Asset Selection Assistant**
- **What:** "Which OTC assets should I focus on right now?" → Grok analyzes recent tick volatility, OTEO warmup status, and historical win rates across all assets
- **Why:** Helps traders pick the best opportunities instead of randomly selecting
- **Implementation:** `POST /api/ai/suggest-assets` → analyzes last hour of tick data + ghost trade stats
- **Frontend:** "AI Picks" section in LeftSidebar

#### 5. **Manipulation Pattern Explainer**
- **What:** When manipulation is detected (push/snap or pinning), Grok explains what's happening in plain English
- **Why:** Educates the trader: "Price was pushed up 15 pips in 3 seconds then snapped back. This is a classic stop-hunt pattern. Avoid trading for the next 30 seconds."
- **Implementation:** Triggered on manipulation detection events
- **Frontend:** Expandable tooltip on the manipulation badge

#### 6. **Settings Optimizer**
- **What:** "Optimize my OTEO settings for EURUSD" → Grok analyzes historical ghost trade data and suggests parameter tweaks
- **Why:** Data-driven parameter tuning instead of guesswork
- **Implementation:** `POST /api/ai/optimize-settings` → sends ghost trade stats + current settings → returns suggested changes

### **Tier 3: Advanced (Future)**

#### 7. **Natural Language Trade Execution**
- "Buy $10 CALL on EURUSD for 5 minutes" → Grok parses → executes trade
- Useful for voice-controlled trading or quick commands

#### 8. **Market Regime Detection**
- Grok analyzes tick patterns across multiple assets to detect market regime changes (trending, ranging, volatile)
- Adjusts OTEO parameters automatically

### **Architecture for AI Integration**

```python
# backend/services/ai_service.py
class AIService:
    """Single interface for all AI operations. Swappable provider."""
    
    def __init__(self, provider: str = "grok"):
        self.provider = self._get_provider(provider)
    
    async def analyze_session(self, session_data: dict) -> AIInsight: ...
    async def confirm_signal(self, signal_data: dict) -> AIConfirmation: ...
    async def risk_advice(self, risk_state: dict) -> AIAdvice: ...
    async def suggest_assets(self, market_data: dict) -> List[AssetSuggestion]: ...
```

```python
# backend/api/ai.py
router = APIRouter(prefix="/api/ai")

@router.post("/analyze-session")
async def analyze_session(request: SessionAnalysisRequest): ...

@router.post("/confirm-signal")  
async def confirm_signal(request: SignalConfirmRequest): ...

@router.post("/risk-advice")
async def risk_advice(request: RiskAdviceRequest): ...
```

**Key principle:** AI is always **advisory, never autonomous**. It suggests, the trader decides. No auto-trading based on AI alone.

### AI Usage Guidance

- Use AI where it adds interpretation, summarization, or recommendation value:
  - session review
  - asset selection suggestions
  - risk advisories
  - manipulation explanation
  - settings tuning suggestions
- Do **not** use AI as the primary execution path for live trades or account operations.
- AI output must be structured and bounded; the backend should validate response shape before any UI display.

---

## 📋 Updated Implementation Phases

**Phase 0: Ops + Chrome + Manual SSID** *(NEW — PREREQUISITE)* — Chrome lifecycle management, manual SSID input, status polling, `.env` persistence. Ported from QuFLX-v2 `ops.py` + `TopBar.jsx` pattern.
**Phase 1: Foundation** — Backend skeleton, session layer, data repository
**Phase 2: Broker + Trading** — Adapter, trade execution, trade logging
**Phase 3: Streaming** — Socket.IO, OTEO, collector, tick logging
**Phase 4: Frontend Shell** — MainLayout, sidebars, stores, API client *(TopBar must include Chrome + SSID badges)*
**Phase 5: Trading UI** — Sparkline, OTEO ring, trade panel, trade history
**Phase 6: Risk Management** — VerticalRiskChart, SessionRiskPanel, risk tracking
**Phase 7: MultiChart + Settings** — MultiChartView, settings architecture
**Phase 8: AI Integration** — AI service, session analysis, signal confirmation
**Phase 9: Polish** — Ghost trading, ops control, export, final testing

Each phase gets a @Reviewer gate.

### Implementation Order Constraint

1. **Phase 0 MUST be completed first.** Without Chrome management and SSID input, no subsequent phase can be tested against a live Pocket Option session.
2. Create the `app/` functional root and move all runtime code under it.
3. Preserve the workspace-level docs/reference folders only for planning and migration.
4. Delete `netstat_chrome_session.bat` (cross-project v2 dependency) during Phase 0.
5. Implement Phase 1 backend foundation after Phase 0 is verified.
6. Only then scaffold frontend shell, layout, and secondary features.

### Chrome + SSID Architecture Rule (NEW)

- Chrome must be managed as a backend subprocess via `api/ops.py`, not launched by external scripts.
- The SSID is a full `42["auth",{...}]` WebSocket auth frame, NOT a cookie. All validation must expect this format.
- Manual SSID input (paste from DevTools) is the primary path. Automated CDP extraction is a future enhancement only.
- SSID persistence to `.env` must refresh in-memory config after write to avoid stale state.
- Chrome spawn flags must NOT include `--disable-web-security` or `--allow-running-insecure-content` by default (security improvement over v2).
- Status polling via Socket.IO `check_status` must distinguish between "Chrome running" and "authenticated session active" — these are separate states.

---

## 📌 Current Workplan Note

The detailed implementation plan is saved at:

`C:\v3\OTC_SNIPER\Dev_Docs\OTC_SNIPER_v3_Implementation_Plan_26-03-24.md`

and the functional app code must be placed under:

`C:\v3\OTC_SNIPER\app\`

**Next step:** Begin **Phase 0** (Ops + Chrome + Manual SSID) — create `app/backend/api/ops.py`, extract `app/backend/api/session.py`, add `check_status` Socket.IO event, update `config.py`, and delete `netstat_chrome_session.bat`.
