"""
VPS Data Agent Main Orchestrator & Telemetry HTTP Server

Design:
  - Manages background tasks for SSIDTickCollector, GCPTickSink, BayesianPriorUpdater, and OpenWABridge.
  - Exposes an HTTP API for telemetry monitoring by the OTC_SNIPER web app.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, Dict

# Dynamically resolve sys.path to allow execution from root, subdirectories, or standalone scripts
_SRC_DIR = Path(__file__).resolve().parent
_DATA_AGENT_DIR = _SRC_DIR.parent
_ROOT_DIR = _DATA_AGENT_DIR.parent

for _p in [str(_ROOT_DIR), str(_DATA_AGENT_DIR), str(_SRC_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from data_agent.src.tick_collector.ssid_collector import SSIDTickCollector
    from data_agent.src.tick_collector.gcp_sink import GCPTickSink
    from data_agent.src.bayesian.prior_updater import BayesianPriorUpdater
    from data_agent.src.hermes.market_tools import HermesMarketTools
    from data_agent.src.whatsapp.openwa_bridge import OpenWABridge
except ImportError:
    try:
        from src.tick_collector.ssid_collector import SSIDTickCollector
        from src.tick_collector.gcp_sink import GCPTickSink
        from src.bayesian.prior_updater import BayesianPriorUpdater
        from src.hermes.market_tools import HermesMarketTools
        from src.whatsapp.openwa_bridge import OpenWABridge
    except ImportError:
        from tick_collector.ssid_collector import SSIDTickCollector
        from tick_collector.gcp_sink import GCPTickSink
        from bayesian.prior_updater import BayesianPriorUpdater
        from hermes.market_tools import HermesMarketTools
        from whatsapp.openwa_bridge import OpenWABridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("data_agent.vps_server")

# Global agent instances
sink = GCPTickSink()
collector = SSIDTickCollector(ssid=os.getenv("PO_SSID", "demo_ssid_placeholder"))
updater = BayesianPriorUpdater()
tools = HermesMarketTools(priors_updater=updater)
wa_bridge = OpenWABridge()

# Wire collector callbacks to push ticks to GCP sink
collector.register_callback(sink.push_tick)


# Initialize Data Bridge API router
try:
    from data_agent.src.api_bridge import DataBridgeAPI
except ImportError:
    try:
        from src.api_bridge import DataBridgeAPI
    except ImportError:
        from api_bridge import DataBridgeAPI

bridge_api = DataBridgeAPI()

class TelemetryHTTPHandler(BaseHTTPRequestHandler):
    """Simple HTTP telemetry & DaaS API handler for Data Agent."""

    def log_message(self, format, *args):
        pass  # Suppress standard HTTP access logs to keep console clean

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_OPTIONS(self) -> None:
        self._send_json(200, {"status": "ok"})

    def do_GET(self) -> None:
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query = parse_qs(parsed_url.query)

        if path == "/api/status":
            self._send_json(200, {
                "status": "online",
                "collector": collector.metrics,
                "sink": sink.metrics,
                "bayesian": tools.get_bayesian_summary(),
            })
        elif path in ("/api/priors", "/api/v1/priors"):
            self._send_json(200, bridge_api.get_bayesian_priors())
        elif path.startswith("/api/v1/ticks/raw"):
            asset = query.get("asset", [None])[0]
            limit = int(query.get("limit", [100])[0])
            self._send_json(200, bridge_api.get_raw_ticks(asset=asset, limit=limit))
        elif path.startswith("/api/v1/ticks/filtered"):
            asset = query.get("asset", [None])[0]
            limit = int(query.get("limit", [100])[0])
            gates = query.get("gates", ["bayesian,volatility,liquidity"])[0]
            self._send_json(200, bridge_api.get_filtered_ticks(asset=asset, limit=limit, gates_str=gates))
        elif path.startswith("/api/v1/context"):
            asset = query.get("asset", ["EURUSD_otc"])[0]
            self._send_json(200, bridge_api.get_market_context(asset=asset))
        else:
            self._send_json(404, {"error": f"Endpoint not found: {self.path}"})

    def do_POST(self) -> None:
        if self.path == "/api/v1/trades/record":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8")) if post_data else {}
                self._send_json(200, bridge_api.record_trade_outcome(payload))
            except Exception as err:
                self._send_json(400, {"error": f"Invalid JSON payload: {err}"})
        else:
            self._send_json(404, {"error": "Endpoint not found"})


def run_http_server(port: int = 8090) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", port), TelemetryHTTPHandler)
    logger.info(f"VPS Telemetry API Server listening on port {port}")
    server.serve_forever()
    return server


def load_env_file() -> None:
    """Load key-value pairs from .env or data-agent/.env into os.environ."""
    for env_path in [Path(".env"), Path("data-agent/.env"), _DATA_AGENT_DIR / ".env"]:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception as err:
                logger.warning(f"Could not load {env_path}: {err}")
            break


if __name__ == "__main__":
    load_env_file()
    port = int(os.getenv("TELEMETRY_PORT", "8090"))
    t = Thread(target=run_http_server, args=(port,), daemon=True)
    t.start()

    logger.info("Data Agent Services Initialized. Press Ctrl+C to terminate.")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(sink.start())

        po_ssid = os.getenv("PO_SSID", "").strip()
        if po_ssid and po_ssid != "demo_ssid_placeholder":
            collector.ssid = po_ssid
            loop.create_task(collector.start())
            logger.info("🟢 SSIDTickCollector task launched for live streaming.")
        else:
            logger.info("ℹ️ PO_SSID not configured. Tick Collector standby (GCP Sink & Telemetry API active).")

        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down VPS Data Agent...")
