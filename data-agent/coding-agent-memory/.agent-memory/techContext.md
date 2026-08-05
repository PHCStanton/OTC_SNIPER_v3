# Technical Context — VPS Data Agent

## Technologies Used
- **Language**: Python 3.11+ / 3.12+ (Conda Env: `QuFLX-v2`)
- **Frontend Stack**: React 18, Vite 6, `@tailwindcss/vite` (Tailwind CSS v4), `recharts`, Lucide Icons
- **WebSocket Streaming**: `websockets` (targeting `wss://api-us-north.po.market`)
- **HTTP Client**: `httpx`
- **Data Processing**: `pandas`, `pyarrow`
- **GCP Analytics**: `google-cloud-bigquery`, `google-cloud-storage` (project `otc-sniper-prod`)
- **Local Fallback Storage**: SQLite (`data-agent/data/ticks_fallback.db`)
- **Messaging Gateway**: OpenWA (`data-agent/OpenWA`), bridge reads **`OPENWA_API_URL`**
- **Containerization**: Docker Compose (`docker-compose.vps.yml`)
- **Testing**: Pytest at monorepo root `C:\v3\OTC_SNIPER\tests\`

## Development & Execution Commands
```powershell
conda activate QuFLX-v2
cd C:\v3\OTC_SNIPER

# Phase 0 / remediation baseline
$env:PYTHONDONTWRITEBYTECODE='1'
conda run -n QuFLX-v2 python -m pytest -p no:cacheprovider -o pythonpath=. `
  tests/test_vps_data_agent_full_suite.py `
  tests/test_vps_tick_collector.py `
  tests/test_bayesian_prior_updater.py `
  tests/test_bayesian_signal_filter.py -q

# Start data agent (from monorepo root)
python data-agent/src/vps_server.py

# UI
cd data-agent/ui; npm run dev
```

## Environment Configuration (`data-agent/.env` — untracked)
Canonical keys (see `.env.example`):

| Variable | Role |
|---|---|
| `TARGET_ASSETS` | Comma-separated initial subscriptions; unset → collector defaults |
| `OPENWA_API_URL` | OpenWA bridge base URL (default `http://localhost:8080`) |
| `OPENWA_SERVER_URL` | **Legacy alias only** if `OPENWA_API_URL` unset |
| `PO_SSID` | Pocket Option session; placeholder keeps collector standby |
| `TELEMETRY_PORT` | HTTP DaaS port (default 8090) |
| `SUBSCRIBE_TIMEOUT_SECONDS` | HTTP→asyncio subscribe gateway timeout |
| `GCP_PROJECT_ID` | BigQuery project |
| `XAI_API_KEY` | Hermes / xAI |

**Never** commit active `.env` or print `PO_SSID` / API keys into reports.

## Technical Constraints
- Clean Data Policy: raw ticks unmutated at API boundary.
- PowerShell: use `-o pythonpath=.`; avoid `&&` chains.
- Soft-import GCP libs for local fallback.
- Composition root: importing `vps_server` must not construct DB/clients/threads/services.
- HTTP thread must not mutate collector state directly; use subscription command gateway.
