"""
Phase 1 — Runtime composition, configuration, and subscription command gateway.

Verification IDs: T1.1, T1.2, T1.3 (remediation plan 2026-08-03).
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import threading
import time
from types import ModuleType
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest


def _import_vps_server() -> ModuleType:
    """Import (or re-import) data_agent.src.vps_server fresh enough for side-effect checks."""
    name = "data_agent.src.vps_server"
    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    return importlib.import_module(name)


def test_import_vps_server_has_no_resource_side_effects():
    """T1.1 — Importing vps_server creates no DB/client/thread/service construction."""
    vs = _import_vps_server()

    assert hasattr(vs, "AgentSettings")
    assert hasattr(vs, "AgentServices")
    assert hasattr(vs, "build_services")
    assert hasattr(vs, "main")
    assert callable(vs.build_services)
    assert callable(vs.main)

    # Pre-remediation constructed sink/collector/bridge_api at import time.
    # Post-remediation: those names must not be live service instances on the module.
    for forbidden in ("sink", "collector", "updater", "tools", "wa_bridge", "bridge_api"):
        assert getattr(vs, forbidden, None) is None, (
            f"Module-level service {forbidden!r} must not be constructed at import"
        )

    # Handler must not ship a pre-bound services container
    assert getattr(vs.TelemetryHTTPHandler, "services", None) is None


def test_agent_settings_parses_configured_assets_and_openwa_url():
    """T1.2 — Environment parsing uses exactly the configured asset set and OpenWA URL."""
    vs = _import_vps_server()
    env = {
        "TELEMETRY_PORT": "8091",
        "TARGET_ASSETS": "EURUSD_otc, GBPUSD_otc, AUDCAD_otc",
        "OPENWA_API_URL": "http://openwa.test:8080/",
        "PO_SSID": "demo_ssid_placeholder",
        "GCP_PROJECT_ID": "otc-sniper-prod",
        "SUBSCRIBE_TIMEOUT_SECONDS": "5",
    }
    settings = vs.AgentSettings.from_env(env)
    assert settings.telemetry_port == 8091
    assert settings.target_assets == ["EURUSD_otc", "GBPUSD_otc", "AUDCAD_otc"]
    assert settings.openwa_api_url == "http://openwa.test:8080"
    assert settings.subscribe_timeout_sec == 5.0


def test_agent_settings_openwa_legacy_alias():
    vs = _import_vps_server()
    env = {
        "OPENWA_SERVER_URL": "http://legacy:3000",
        "PO_SSID": "demo_ssid_placeholder",
    }
    settings = vs.AgentSettings.from_env(env)
    assert settings.openwa_api_url == "http://legacy:3000"


def test_agent_settings_invalid_port_fails_fast():
    vs = _import_vps_server()
    with pytest.raises(vs.ConfigurationError, match="TELEMETRY_PORT"):
        vs.AgentSettings.from_env({"TELEMETRY_PORT": "not-a-port"})


def test_agent_settings_invalid_port_range_fails_fast():
    vs = _import_vps_server()
    with pytest.raises(vs.ConfigurationError, match="TELEMETRY_PORT"):
        vs.AgentSettings.from_env({"TELEMETRY_PORT": "70000"})


def test_agent_settings_empty_target_assets_fails_fast():
    vs = _import_vps_server()
    with pytest.raises(vs.ConfigurationError, match="TARGET_ASSETS"):
        vs.AgentSettings.from_env({"TARGET_ASSETS": "  ,  , "})


def test_build_services_shares_single_updater_instance(tmp_path, monkeypatch):
    """Hermes and DataBridgeAPI share one BayesianPriorUpdater object."""
    vs = _import_vps_server()
    # Keep sink local DB under tmp so we do not touch real ticks_fallback.db
    monkeypatch.chdir(tmp_path)
    settings = vs.AgentSettings.from_env({
        "TELEMETRY_PORT": "8090",
        "TARGET_ASSETS": "EURUSD_otc,GBPUSD_otc",
        "OPENWA_API_URL": "http://localhost:8080",
        "PO_SSID": "demo_ssid_placeholder",
        "GCP_PROJECT_ID": "otc-sniper-prod",
    })
    loop = asyncio.new_event_loop()
    try:
        services = vs.build_services(settings, loop)
        assert services.tools.priors_updater is services.updater
        assert services.bridge_api.prior_updater is services.updater
        assert set(services.collector.assets) == {"EURUSD_otc", "GBPUSD_otc"}
        assert services.wa_bridge.api_url == "http://localhost:8080"
    finally:
        loop.close()


@pytest.mark.asyncio
async def test_http_thread_subscription_uses_owner_loop():
    """T1.3 — HTTP-thread subscription invokes add_asset on the collector owner loop."""
    vs = _import_vps_server()
    loop = asyncio.get_running_loop()
    owner_thread_id = threading.get_ident()
    call_threads: List[int] = []

    class FakeCollector:
        def __init__(self) -> None:
            self.assets = set()
            self.metrics = {"running": False}

        async def add_asset(self, asset: str, *, force: bool = False) -> bool:
            call_threads.append(threading.get_ident())
            self.assets.add(asset)
            return True


    settings = vs.AgentSettings.from_env({
        "TELEMETRY_PORT": "8090",
        "OPENWA_API_URL": "http://localhost:8080",
        "PO_SSID": "demo_ssid_placeholder",
        "SUBSCRIBE_TIMEOUT_SECONDS": "5",
    })
    services = vs.AgentServices(
        settings=settings,
        loop=loop,
        sink=MagicMock(),
        collector=FakeCollector(),  # type: ignore[arg-type]
        updater=MagicMock(),
        tools=MagicMock(),
        wa_bridge=MagicMock(),
        bridge_api=MagicMock(),
    )

    result_holder: dict[str, Any] = {}

    def http_thread_call() -> None:
        result_holder["result"] = services.subscribe_asset_sync("BTCUSD")

    t = threading.Thread(target=http_thread_call, name="fake-http")
    t.start()
    # Drive the loop so the scheduled coroutine can complete
    deadline = time.time() + 5.0
    while t.is_alive() and time.time() < deadline:
        await asyncio.sleep(0.01)
    t.join(timeout=2.0)

    assert result_holder["result"]["status"] == "ok"
    assert result_holder["result"]["asset"] == "BTCUSD"
    assert "BTCUSD" in services.collector.assets
    assert call_threads, "add_asset was not invoked"
    assert call_threads[0] == owner_thread_id


@pytest.mark.asyncio
async def test_duplicate_subscription_is_idempotent():
    """Repeated subscriptions succeed and do not error."""
    from data_agent.src.tick_collector.ssid_collector import SSIDTickCollector

    collector = SSIDTickCollector(ssid="test", assets=["EURUSD_otc"])
    # Simulate live wire state without a real websocket
    collector._running = True

    async def fake_send(msg: str) -> None:
        return None

    collector._ws = MagicMock()
    collector._ws.send = fake_send
    collector._subscribed_assets = {"EURUSD_otc"}

    ok1 = await collector.add_asset("EURUSD_otc")
    ok2 = await collector.add_asset("EURUSD_otc")
    assert ok1 is True and ok2 is True
    assert collector.assets == {"EURUSD_otc"}
    assert collector._subscribed_assets == {"EURUSD_otc"}

    ok3 = await collector.add_asset("GBPUSD_otc")
    assert ok3 is True
    assert "GBPUSD_otc" in collector.assets
    assert "GBPUSD_otc" in collector._subscribed_assets


def test_subscribe_empty_asset_returns_structured_error():
    vs = _import_vps_server()
    loop = asyncio.new_event_loop()
    try:
        settings = vs.AgentSettings.from_env({"PO_SSID": "demo_ssid_placeholder"})
        services = vs.AgentServices(
            settings=settings,
            loop=loop,
            sink=MagicMock(),
            collector=MagicMock(),
            updater=MagicMock(),
            tools=MagicMock(),
            wa_bridge=MagicMock(),
            bridge_api=MagicMock(),
        )
        result = services.subscribe_asset_sync("   ")
        assert result["status"] == "error"
        assert result["code"] == "invalid_asset"
        assert result["subscribed"] is False
    finally:
        loop.close()


def test_sse_lock_is_threading_lock():
    """Verify _sse_lock is a threading.Lock instance (not a Thread)."""
    vs = _import_vps_server()
    import threading
    assert isinstance(vs._sse_lock, type(threading.Lock()))


def test_broadcast_sse_evicts_full_queue():
    """Verify _broadcast_sse_event discards dead/full subscriber queues safely."""
    import queue
    vs = _import_vps_server()
    full_q = queue.Queue(maxsize=1)
    full_q.put_nowait("filler")
    with vs._sse_lock:
        vs._sse_subscribers.add(full_q)
    vs._broadcast_sse_event("tick", {"asset": "TEST", "price": 1.0})
    with vs._sse_lock:
        assert full_q not in vs._sse_subscribers, "Dead queue should be evicted"
        vs._sse_subscribers.clear()


def test_openwa_bridge_has_sync_send_alert():
    """Verify OpenWABridge exposes a synchronous send_alert() method."""
    from data_agent.src.whatsapp.openwa_bridge import OpenWABridge
    bridge = OpenWABridge(api_url="http://localhost:9999")
    assert hasattr(bridge, "send_alert"), "send_alert() method must exist"
    import inspect
    assert not inspect.iscoroutinefunction(bridge.send_alert), "send_alert must be synchronous"


def test_query_limit_cap_constant_exists():
    """Verify MAX_QUERY_LIMIT constant is defined and bounded."""
    vs = _import_vps_server()
    assert hasattr(vs, "MAX_QUERY_LIMIT")
    assert vs.MAX_QUERY_LIMIT == 1000
