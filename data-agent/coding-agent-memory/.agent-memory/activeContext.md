# Active Context — VPS Data Agent

## Current Work
- Built and verified the **Standalone Data-as-a-Service (DaaS) Microservice & UI Hub** in `data-agent/`.
- Implemented pristine raw clean tick preservation, decoupled modular filter pipeline, DaaS REST API bridge, dynamic runtime asset subscriptions, and Standalone React UI (`data-agent/ui/`) with an OTC-SNIPER style Asset Selectable Left Sidebar.

## Recent Changes & Milestone Accomplishments
- **Decoupled Filter Pipeline (`data-agent/src/filters/`)**:
  - Implemented `BaseFilter` interface and modular gate plugins (`BayesianFilter`, `VolatilityFilter`, `LiquidityFilter`, `ManipulationFilter`).
  - Built `FilterPipelineManager` for on-demand execution of single or combined gates over raw tick sequences.
- **Pristine Raw Data Integrity**:
  - Guaranteed 100% clean, unmutated tick data storage in BigQuery (`otc_sniper_analytics.raw_ticks`) and SQLite (`ticks_fallback.db`). Filters operate dynamically on top of the raw stream.
- **DaaS REST API Bridge (`data-agent/src/api_bridge.py` & `vps_server.py`)**:
  - Exposed REST endpoints on port 8090:
    - `GET /api/v1/ticks/raw`: 100% clean raw tick data.
    - `GET /api/v1/ticks/filtered?gates=...`: Raw ticks overlaid with dynamic filter evaluations.
    - `GET /api/v1/context?asset=...`: Historical volatility, liquidity, manipulation, and regime context.
    - `GET /api/v1/priors`: Dynamic Bayesian feature win-rate matrix.
    - `POST /api/v1/trades/record`: Multi-app trade outcome recorder updating global Bayesian priors.
    - `POST /api/v1/subscribe`: Dynamic runtime asset subscription endpoint.
- **Dynamic Asset Subscription**:
  - Environment variable support `TARGET_ASSETS` in `data-agent/.env`.
  - Added `add_asset` method to `SSIDTickCollector` for runtime Socket.IO frame dispatch (`42["sub", "ANY_TICKER"]`).
- **Standalone React UI (`data-agent/ui/`)**:
  - Configured `@tailwindcss/vite` (Tailwind v4), `recharts`, and Lucide icons.
  - Implemented **Asset Selectable Left Sidebar** matching OTC-SNIPER layout (search bar, payout tabs `ALL`, `92%+`, `90%+`, live stream badges, tick density metrics, and custom asset subscribe drawer).
  - Integrated `bklit-ui` styled Area Charts (tick density & volatility) and Bar Charts (Bayesian win-rate matrix).
- **Test Suite**: Passed 100% in `QuFLX-v2` (`tests/test_vps_data_agent_full_suite.py` - 3/3 passed).

## Next Steps
1. Deploy `docker-compose.vps.yml` container to target cloud VPS.
2. Authenticate OpenWA WhatsApp gateway for mobile alerts.
3. Configure `XAI_API_KEY` in `data-agent/.env` for Grok reasoning models.

## Active Blockers / Risks
- None. All unit/integration tests pass cleanly and production Vite builds compile with 0 errors.
