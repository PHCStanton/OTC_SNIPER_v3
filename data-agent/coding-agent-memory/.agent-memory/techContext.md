# Technical Context — VPS Data Agent

## Technologies Used
- **Language**: Python 3.11+
- **WebSocket Streaming**: `websockets`
- **HTTP Client**: `httpx`
- **Data Processing**: `pandas`, `pyarrow`
- **GCP Analytics**: `google-cloud-bigquery`, `google-cloud-storage`
- **AI Reasoning**: xAI API (Grok models: `grok-2`, `grok-beta`) via OpenAI-compatible endpoints (`https://api.x.ai/v1`)
- **Messaging Gateway**: OpenWA Node/NestJS WhatsApp Gateway (`data-agent/OpenWA`)
- **Local Fallback Storage**: SQLite 3 (`data-agent/data/ticks_fallback.db`)
- **Containerization**: Docker, Docker Compose
- **Testing**: Pytest, Pytest-Asyncio

## Development Setup
- Conda Environment: `QuFLX-v2` (Python 3.11.13)
- Execution Commands (PowerShell Compatible):
  - Run full test suite: `pytest -o pythonpath=. tests/test_vps_data_agent_full_suite.py -v`
  - Start telemetry server locally: `python data-agent/src/vps_server.py`

## Dependencies (`data-agent/requirements.txt`)
- `websockets>=11.0`
- `httpx>=0.24.0`
- `pandas>=2.0.0`
- `pyarrow>=12.0.0`
- `pydantic>=2.0.0`
- `pytest>=7.0.0`
- `pytest-asyncio>=0.21.0`
- `google-cloud-bigquery>=3.10.0`
- `google-cloud-storage>=2.10.0`

## Technical Constraints & Guidelines
- PowerShell compatibility: Always set `pythonpath=.` via `-o pythonpath=.` flag in `pytest` commands.
- Defensive imports: Soft import `google.cloud.bigquery` and `google.cloud.storage` so local fallback mode operates seamlessly without crashing if GCP packages are uninstalled.
- Fail-Fast & Explicit Error Handling: Never swallow exceptions silently; log errors explicitly with context.
