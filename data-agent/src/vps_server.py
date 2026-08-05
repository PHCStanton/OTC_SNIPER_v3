"""
VPS Data Agent Main Orchestrator & Telemetry HTTP Server

Design:
  - Composition root: import defines types/functions only; resources are built after env load.
  - Manages SSIDTickCollector, GCPTickSink, BayesianPriorUpdater, Hermes, OpenWA, DataBridgeAPI.
  - HTTP API runs on a worker thread; async collector commands use a thread-safe gateway.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, Dict, List, Optional

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
    from data_agent.src.api_bridge import DataBridgeAPI
except ImportError:
    try:
        from src.tick_collector.ssid_collector import SSIDTickCollector
        from src.tick_collector.gcp_sink import GCPTickSink
        from src.bayesian.prior_updater import BayesianPriorUpdater
        from src.hermes.market_tools import HermesMarketTools
        from src.whatsapp.openwa_bridge import OpenWABridge
        from src.api_bridge import DataBridgeAPI
    except ImportError:
        from tick_collector.ssid_collector import SSIDTickCollector
        from tick_collector.gcp_sink import GCPTickSink
        from bayesian.prior_updater import BayesianPriorUpdater
        from hermes.market_tools import HermesMarketTools
        from whatsapp.openwa_bridge import OpenWABridge
        from api_bridge import DataBridgeAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("data_agent.vps_server")

SUBSCRIBE_TIMEOUT_SECONDS = 10.0
DEFAULT_TELEMETRY_PORT = 8090
DEFAULT_OPENWA_API_URL = "http://localhost:8080"


class ConfigurationError(ValueError):
    """Raised when environment configuration is invalid."""


@dataclass(frozen=True)
class AgentSettings:
    """Validated runtime settings loaded from the environment after dotenv load."""

    telemetry_port: int
    target_assets: Optional[List[str]]
    po_ssid: str
    openwa_api_url: str
    gcp_project_id: str
    subscribe_timeout_sec: float = SUBSCRIBE_TIMEOUT_SECONDS
    openwa_recipient: str = ""
    openwa_api_key: str = ""

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "AgentSettings":
        source = env if env is not None else os.environ

        port_raw = (source.get("TELEMETRY_PORT") or str(DEFAULT_TELEMETRY_PORT)).strip()
        try:
            telemetry_port = int(port_raw)
        except ValueError as exc:
            raise ConfigurationError(
                f"TELEMETRY_PORT must be an integer in 1..65535, got {port_raw!r}"
            ) from exc
        if not (1 <= telemetry_port <= 65535):
            raise ConfigurationError(
                f"TELEMETRY_PORT must be an integer in 1..65535, got {telemetry_port}"
            )

        raw_assets = source.get("TARGET_ASSETS")
        target_assets: Optional[List[str]]
        if raw_assets is None:
            target_assets = None
        else:
            target_assets = parse_target_assets(raw_assets)

        timeout_raw = (source.get("SUBSCRIBE_TIMEOUT_SECONDS") or str(SUBSCRIBE_TIMEOUT_SECONDS)).strip()
        try:
            subscribe_timeout_sec = float(timeout_raw)
        except ValueError as exc:
            raise ConfigurationError(
                f"SUBSCRIBE_TIMEOUT_SECONDS must be a positive number, got {timeout_raw!r}"
            ) from exc
        if subscribe_timeout_sec <= 0:
            raise ConfigurationError(
                f"SUBSCRIBE_TIMEOUT_SECONDS must be positive, got {subscribe_timeout_sec}"
            )

        # Canonical name is OPENWA_API_URL; OPENWA_SERVER_URL is a temporary legacy alias.
        openwa_api_url = (
            (source.get("OPENWA_API_URL") or source.get("OPENWA_SERVER_URL") or DEFAULT_OPENWA_API_URL)
            .strip()
            .rstrip("/")
        )
        if not openwa_api_url:
            raise ConfigurationError("OPENWA_API_URL cannot be empty")

        po_ssid = (source.get("PO_SSID") or "demo_ssid_placeholder").strip()
        gcp_project_id = (source.get("GCP_PROJECT_ID") or "otc-sniper-prod").strip()
        if not gcp_project_id:
            raise ConfigurationError("GCP_PROJECT_ID cannot be empty")

        return cls(
            telemetry_port=telemetry_port,
            target_assets=target_assets,
            po_ssid=po_ssid,
            openwa_api_url=openwa_api_url,
            gcp_project_id=gcp_project_id,
            subscribe_timeout_sec=subscribe_timeout_sec,
            openwa_recipient=(source.get("OPENWA_RECIPIENT_PHONE") or "").strip(),
            openwa_api_key=(source.get("OPENWA_API_KEY") or "").strip(),
        )


def parse_target_assets(raw: str) -> List[str]:
    """Parse a comma-separated TARGET_ASSETS string into a non-empty normalized list."""
    assets = [a.strip() for a in raw.split(",") if a.strip()]
    if not assets:
        raise ConfigurationError(
            "TARGET_ASSETS is set but empty after parsing; provide at least one asset "
            "or unset the variable to use collector defaults"
        )
    return assets


def normalize_asset_symbol(asset: str) -> str:
    """Normalize a user-supplied asset ticker for subscription."""
    if asset is None:
        return ""
    return str(asset).strip()


@dataclass
class AgentServices:
    """Runtime service container constructed after environment validation."""

    settings: AgentSettings
    loop: asyncio.AbstractEventLoop
    sink: GCPTickSink
    collector: SSIDTickCollector
    updater: BayesianPriorUpdater
    tools: HermesMarketTools
    wa_bridge: OpenWABridge
    bridge_api: DataBridgeAPI

    def subscribe_asset_sync(self, asset: str) -> Dict[str, Any]:
        """
        Thread-safe subscription gateway: schedule collector.add_asset on the owner loop
        and wait for completion. Safe to call from the HTTP worker thread.
        """
        asset_clean = normalize_asset_symbol(asset)
        if not asset_clean:
            return {
                "status": "error",
                "code": "invalid_asset",
                "message": "Asset ticker cannot be empty.",
                "subscribed": False,
            }

        if self.loop.is_closed():
            return {
                "status": "error",
                "code": "loop_closed",
                "message": "Event loop is closed; cannot subscribe assets.",
                "subscribed": False,
                "asset": asset_clean,
            }

        try:
            future = asyncio.run_coroutine_threadsafe(
                self.collector.add_asset(asset_clean),
                self.loop,
            )
            subscribed = future.result(timeout=self.settings.subscribe_timeout_sec)
        except FuturesTimeoutError:
            logger.error("Subscription timed out for asset %s", asset_clean)
            return {
                "status": "error",
                "code": "subscribe_timeout",
                "message": f"Subscription timed out after {self.settings.subscribe_timeout_sec}s.",
                "subscribed": False,
                "asset": asset_clean,
            }
        except Exception as err:
            logger.error("Subscription failed for asset %s: %s", asset_clean, err, exc_info=False)
            return {
                "status": "error",
                "code": "subscribe_failed",
                "message": str(err),
                "subscribed": False,
                "asset": asset_clean,
            }

        if not subscribed:
            return {
                "status": "error",
                "code": "subscribe_rejected",
                "message": f"Collector rejected subscription for {asset_clean}.",
                "subscribed": False,
                "asset": asset_clean,
            }

        return {
            "status": "ok",
            "subscribed": True,
            "asset": asset_clean,
            "all_assets": sorted(self.collector.assets),
        }


def build_services(settings: AgentSettings, loop: asyncio.AbstractEventLoop) -> AgentServices:
    """Construct all runtime services. Call only after load_env_file() + validation."""
    sink = GCPTickSink(gcp_project_id=settings.gcp_project_id)
    collector = SSIDTickCollector(
        ssid=settings.po_ssid,
        assets=settings.target_assets,
    )
    updater = BayesianPriorUpdater()
    tools = HermesMarketTools(priors_updater=updater)
    wa_bridge = OpenWABridge(
        api_url=settings.openwa_api_url,
        api_key=settings.openwa_api_key or None,
        default_recipient=settings.openwa_recipient or None,
    )
    bridge_api = DataBridgeAPI(prior_updater=updater)

    collector.register_callback(sink.push_tick)

    return AgentServices(
        settings=settings,
        loop=loop,
        sink=sink,
        collector=collector,
        updater=updater,
        tools=tools,
        wa_bridge=wa_bridge,
        bridge_api=bridge_api,
    )


class TelemetryHTTPHandler(BaseHTTPRequestHandler):
    """Simple HTTP telemetry & DaaS API handler for Data Agent."""

    # Injected by the composition root before the HTTP server starts.
    services: Optional[AgentServices] = None

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress standard HTTP access logs to keep console clean

    def _require_services(self) -> AgentServices:
        if self.services is None:
            raise RuntimeError("AgentServices not bound to TelemetryHTTPHandler")
        return self.services

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

        # Liveness: process HTTP is responsive (does not depend on OpenWA).
        if path in ("/api/health/live", "/api/health/live/"):
            self._send_json(200, {
                "status": "alive",
                "service": "data-agent",
            })
            return

        # Readiness: required internal services constructed; collector conditional on SSID.
        if path in ("/api/health/ready", "/api/health/ready/"):
            self._send_json(*_readiness_response(self.services))
            return

        services = self._require_services()

        if path == "/api/status":
            self._send_json(200, {
                "status": "online",
                "collector": services.collector.metrics,
                "sink": services.sink.metrics,
                "bayesian": services.tools.get_bayesian_summary(),
            })
        elif path in ("/api/priors", "/api/v1/priors"):
            result = services.bridge_api.get_bayesian_priors()
            self._send_json(_api_http_status(result, default=200), result)
        elif path.startswith("/api/v1/ticks/raw"):
            asset = query.get("asset", [None])[0]
            limit = int(query.get("limit", [100])[0])
            result = services.bridge_api.get_raw_ticks(asset=asset, limit=limit)
            self._send_json(_api_http_status(result, default=200), result)
        elif path.startswith("/api/v1/ticks/filtered"):
            asset = query.get("asset", [None])[0]
            limit = int(query.get("limit", [100])[0])
            gates = query.get("gates", ["bayesian,volatility,liquidity"])[0]
            result = services.bridge_api.get_filtered_ticks(
                asset=asset, limit=limit, gates_str=gates
            )
            self._send_json(_api_http_status(result, default=200), result)
        elif path.startswith("/api/v1/context"):
            asset = query.get("asset", ["EURUSD_otc"])[0]
            result = services.bridge_api.get_market_context(asset=asset)
            self._send_json(_api_http_status(result, default=200), result)
        else:
            self._send_json(404, {"error": f"Endpoint not found: {self.path}"})

    def do_POST(self) -> None:
        services = self._require_services()
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except json.JSONDecodeError as err:
            self._send_json(400, {"status": "error", "code": "invalid_json", "message": str(err)})
            return

        if self.path == "/api/v1/trades/record":
            result = services.bridge_api.record_trade_outcome(payload)
            http_status = int(result.get("http_status") or (200 if result.get("recorded") else 400))
            self._send_json(http_status, result)
        elif self.path == "/api/v1/subscribe":
            asset_to_sub = payload.get("asset", "")
            result = services.subscribe_asset_sync(asset_to_sub)
            http_status = _subscribe_http_status(result)
            self._send_json(http_status, result)
        else:
            self._send_json(404, {"error": "Endpoint not found"})


def _api_http_status(result: Dict[str, Any], default: int = 200) -> int:
    """Honor structured http_status from bridge payloads; fall back by status field."""
    if "http_status" in result:
        try:
            return int(result["http_status"])
        except (TypeError, ValueError):
            pass
    if result.get("status") == "error":
        return 400
    return default


def _readiness_response(
    services: Optional[AgentServices],
) -> tuple[int, Dict[str, Any]]:
    """
    Build readiness HTTP status + payload.

    Ready when AgentServices is bound. Collector running is required only when
    a real PO_SSID is configured (standby mode is ready without a live stream).
    OpenWA is intentionally not a readiness dependency.
    """
    if services is None:
        return 503, {
            "status": "not_ready",
            "reasons": ["services_not_bound"],
            "openwa_required": False,
        }

    settings = services.settings
    ssid = (settings.po_ssid or "").strip()
    ssid_configured = bool(ssid) and ssid != "demo_ssid_placeholder"
    collector_metrics = services.collector.metrics
    collector_running = bool(collector_metrics.get("running"))

    reasons: List[str] = []
    if ssid_configured and not collector_running:
        reasons.append("collector_not_running")

    if reasons:
        return 503, {
            "status": "not_ready",
            "reasons": reasons,
            "ssid_configured": ssid_configured,
            "collector_running": collector_running,
            "openwa_required": False,
        }

    return 200, {
        "status": "ready",
        "ssid_configured": ssid_configured,
        "collector_running": collector_running,
        "openwa_required": False,
        "services": {
            "sink": True,
            "collector": True,
            "bridge_api": True,
            "updater": True,
        },
    }


def _subscribe_http_status(result: Dict[str, Any]) -> int:
    if result.get("status") == "ok":
        return 200
    code = result.get("code")
    if code in ("invalid_asset", "subscribe_rejected"):
        return 400
    if code == "subscribe_timeout":
        return 504
    if code == "loop_closed":
        return 503
    return 500


def run_http_server(port: int = DEFAULT_TELEMETRY_PORT) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", port), TelemetryHTTPHandler)
    logger.info("VPS Telemetry API Server listening on port %s", port)
    server.serve_forever()
    return server


def load_env_file() -> Optional[Path]:
    """Load key-value pairs from .env or data-agent/.env into os.environ (no overwrite)."""
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
                logger.warning("Could not load %s: %s", env_path, err)
            return env_path
    return None


def main() -> None:
    """Composition root: load env, validate, build services, then run HTTP + asyncio loop."""
    load_env_file()
    settings = AgentSettings.from_env()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    services = build_services(settings, loop)

    TelemetryHTTPHandler.services = services

    http_thread = Thread(
        target=run_http_server,
        args=(settings.telemetry_port,),
        daemon=True,
        name="data-agent-http",
    )
    http_thread.start()

    logger.info("Data Agent Services Initialized. Press Ctrl+C to terminate.")
    collector_task: Optional[asyncio.Task] = None
    sink_task: Optional[asyncio.Task] = None
    shutdown_failed = False
    try:
        sink_task = loop.create_task(services.sink.start())

        po_ssid = settings.po_ssid
        if po_ssid and po_ssid != "demo_ssid_placeholder":
            collector_task = loop.create_task(services.collector.start())
            logger.info("SSIDTickCollector task launched for live streaming.")
        else:
            logger.info(
                "PO_SSID not configured. Tick Collector standby "
                "(GCP Sink & Telemetry API active)."
            )

        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down VPS Data Agent...")
    finally:
        try:
            # Bounded durable final flush; surface terminal persistence failures.
            loop.run_until_complete(_shutdown_services(services, collector_task))
        except Exception as err:
            shutdown_failed = True
            logger.exception("Shutdown durability failed: %s", err)
        finally:
            try:
                if sink_task and not sink_task.done():
                    sink_task.cancel()
                pending = asyncio.all_tasks(loop) if not loop.is_closed() else []
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception as err:
                logger.exception("Error while cancelling remaining tasks: %s", err)
            try:
                loop.close()
            except Exception as err:
                logger.exception("Error while closing event loop: %s", err)

    if shutdown_failed:
        raise SystemExit(1)


async def _shutdown_services(
    services: AgentServices,
    collector_task: Optional[asyncio.Task],
) -> None:
    """Stop collector then sink with final local flush (Task 2.3 wiring)."""
    if collector_task is not None and not collector_task.done():
        try:
            await services.collector.stop()
        except Exception as err:
            logger.warning("Collector stop error (continuing to sink flush): %s", err)
        collector_task.cancel()
        try:
            await collector_task
        except asyncio.CancelledError:
            pass
        except Exception as err:
            logger.warning("Collector task cleanup error: %s", err)

    await services.sink.stop()


if __name__ == "__main__":
    main()
