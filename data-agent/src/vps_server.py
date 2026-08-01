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


class TelemetryHTTPHandler(BaseHTTPRequestHandler):
    """Simple HTTP telemetry handler for OTC_SNIPER frontend."""

    def log_message(self, format, *args):
        pass  # Suppress standard HTTP access logs to keep console clean

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_GET(self) -> None:
        if self.path == "/api/status":
            self._send_json(200, {
                "status": "online",
                "collector": collector.metrics,
                "sink": sink.metrics,
                "bayesian": tools.get_bayesian_summary(),
            })
        elif self.path == "/api/priors":
            self._send_json(200, updater.load_current_priors())
        else:
            self._send_json(404, {"error": "Endpoint not found"})


def run_http_server(port: int = 8090) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", port), TelemetryHTTPHandler)
    logger.info(f"VPS Telemetry API Server listening on port {port}")
    server.serve_forever()
    return server


if __name__ == "__main__":
    port = int(os.getenv("TELEMETRY_PORT", "8090"))
    t = Thread(target=run_http_server, args=(port,), daemon=True)
    t.start()

    logger.info("Data Agent Services Initialized. Press Ctrl+C to terminate.")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(sink.start())
        # loop.create_task(collector.start()) # Launched when valid SSID is configured
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down VPS Data Agent...")
