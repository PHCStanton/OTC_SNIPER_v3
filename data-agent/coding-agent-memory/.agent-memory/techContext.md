# Technical Context — VPS Data Agent

## Technologies Used
- **Language**: Python 3.11+ / 3.12+ (Conda Env: `QuFLX-v2`)
- **WebSocket Streaming**: `websockets` (targeting `wss://api-us-north.po.market`)
- **HTTP Client**: `httpx`
- **Data Processing**: `pandas`, `pyarrow`
- **GCP Analytics & Data Warehouse**: `google-cloud-bigquery`, `google-cloud-storage` (GCP Project: `otc-sniper-prod`)
- **GCP Auth**: Service Account JSON Key (`otc-sniper-data-agent@otc-sniper-prod.iam.gserviceaccount.com`)
- **AI Reasoning**: xAI API (Grok models: `grok-2`, `grok-beta`) via OpenAI-compatible endpoints (`https://api.x.ai/v1`)
- **Messaging Gateway**: OpenWA Node/NestJS WhatsApp Gateway (`data-agent/OpenWA`)
- **Local Fallback Storage**: SQLite 3 (`data-agent/data/ticks_fallback.db`)
- **Containerization**: Docker, Docker Compose (`docker-compose.vps.yml`)
- **Tunneling**: `localtunnel`, VS Code CLI `code-tunnel.exe` (`v1.131.0`)
- **Testing**: Pytest, Pytest-Asyncio (`tests/test_vps_data_agent_full_suite.py`)

## Development & Execution Commands
- Conda Environment Activation: `conda activate QuFLX-v2`
- Run full test suite: `pytest -o pythonpath=. tests/test_vps_data_agent_full_suite.py -v`
- Start VPS server locally: `python data-agent/src/vps_server.py`
- Provision GCP infrastructure: `python data-agent/scripts/setup_gcp_resources.py`
- Expose dev server for external testing: `npx localtunnel --port 5175`

## Environment Configuration (`data-agent/.env`)
```env
GCP_PROJECT_ID=otc-sniper-prod
GOOGLE_APPLICATION_CREDENTIALS=data-agent/configs/otc-sniper-prod-e0f838b011f8.json
PO_SSID=42["auth",{"session":"...","isDemo":0}]
XAI_API_KEY=your_xai_grok_api_key_here
TELEMETRY_PORT=8090
OPENWA_SERVER_URL=http://localhost:3000
OPENWA_RECIPIENT_PHONE=+1234567890
```

## Technical Constraints & Guidelines
- PowerShell compatibility: Always set `pythonpath=.` via `-o pythonpath=.` flag in `pytest` commands.
- Defensive imports: Soft import `google.cloud.bigquery` and `google.cloud.storage` so local fallback mode operates seamlessly without crashing if GCP packages are uninstalled.
- Secrets protection: Never commit `.env` or `data-agent/configs/*.json` files to Git (`.gitignore` enforced).
- Fail-Fast & Explicit Error Handling: Never swallow exceptions silently; log errors explicitly with context.
