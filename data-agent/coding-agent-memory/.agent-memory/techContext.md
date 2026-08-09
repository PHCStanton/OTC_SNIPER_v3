# Technical Context — VPS Data Agent

## Technologies Used
- **Language**: Python 3.11+ / 3.12+ (Conda Env: `QuFLX-v2`)
- **Frontend Stack**: React 18, Vite 6, `@tailwindcss/vite` (Tailwind CSS v4), `recharts`, Lucide Icons
- **Broker Engine**: `PocketOptionSession` wrapping `pocketoptionapi` (Engine.IO v4, `gv.set_csv` hook, `change_symbol`)
- **WebSocket Gateway**: `websockets` & `pocketoptionapi` (dedicated regional endpoints `api-eu.po.market` / `demo-api-eu.po.market`)
- **HTTP & SSE Server**: Python standard `http.server` with thread-safe Server-Sent Events broadcaster
- **Data Processing**: `pandas`, `pyarrow`, `numpy`
- **GCP Analytics**: `google-cloud-bigquery`, `google-cloud-storage` (project `otc-sniper-prod`)
- **Local Fallback Storage**: SQLite (`data-agent/data/ticks_fallback.db`)
- **Messaging Gateway**: OpenWA (`data-agent/OpenWA`), bridge reads **`OPENWA_API_URL`**
- **Containerization**: Docker Compose (`docker-compose.vps.yml`)
- **Testing**: Pytest at monorepo root `C:\v3\OTC_SNIPER\tests\`

## Development & Execution Commands
```powershell
conda activate QuFLX-v2
cd C:\v3\OTC_SNIPER

# Full test suite
conda run -n QuFLX-v2 python -m pytest tests/test_vps_tick_collector.py tests/test_vps_phase1_runtime.py tests/test_vps_phase3_context_trades.py -v

# Start data agent (from monorepo root)
python data-agent/src/vps_server.py

# UI (development)
cd data-agent/ui; npm run dev

# UI (production build)
cd data-agent/ui; npm run build
```

## DaaS API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/status` | System health, collector, sink, and Bayesian summary |
| `GET` | `/api/v1/stream?asset={sym}` | Zero-latency Server-Sent Events (SSE) live tick stream |
| `GET` | `/api/v1/assets` | Dynamic broker catalog and real-time session payouts |
| `GET` | `/api/v1/ticks/velocity?asset={sym}` | Rolling 5-second tick density and volatility timeseries |
| `GET` | `/api/v1/ticks/raw?asset={sym}` | 100% clean, unmutated raw tick baseline |
| `GET` | `/api/v1/ticks/filtered?asset={sym}` | Raw ticks evaluated against active Bayesian/risk gates |
| `GET` | `/api/v1/priors` | Empirical Bayesian categorical win-rate distributions |
| `POST` | `/api/v1/subscribe` | Dynamic ticker subscription (`change_symbol`) |
| `POST` | `/api/v1/alerts/test` | Test dispatch formatted telemetry alert via OpenWA |
| `POST` | `/api/v1/trades/record` | Validated trade outcome feedback for prior updating |
| `POST` | `/api/v1/auth/connect` | Hot-swap SSID credentials at runtime |
| `POST` | `/api/v1/auth/disconnect` | Standby disconnect |

## Environment Configuration (`data-agent/.env` — untracked)
Canonical keys (see `.env.example`):

| Variable | Role |
|---|---|
| `TARGET_ASSETS` | Comma-separated initial subscriptions (e.g. `EURUSD_otc,GBPUSD_otc`) |
| `OPENWA_API_URL` | OpenWA bridge base URL (default `http://localhost:3000`) |
| `PO_SSID` | Pocket Option session token (`42["auth", {...}]` or raw token) |
| `TELEMETRY_PORT` | HTTP DaaS port (default 8090) |
| `GCP_PROJECT_ID` | BigQuery project (`otc-sniper-prod`) |
| `XAI_API_KEY` | Hermes / xAI |

**Never** commit active `.env` or print `PO_SSID` / API keys into git.
