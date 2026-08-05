"""
Phase 5 — UI integrity helpers and operational health endpoints.

Verification IDs: T5.1–T5.3 (remediation plan 2026-08-03).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from data_agent.src.vps_server import (
    AgentServices,
    AgentSettings,
    TelemetryHTTPHandler,
    _readiness_response,
)


ROOT = Path(__file__).resolve().parents[1]
UI_UTILS = ROOT / "data-agent" / "ui" / "src" / "assetUtils.js"
COMPOSE_FILE = ROOT / "data-agent" / "docker-compose.vps.yml"
DOCKERFILE = ROOT / "data-agent" / "Dockerfile.vps"


def _eval_js(expression: str):
    """Evaluate a small ESM expression against assetUtils via node."""
    script = f"""
import {{
  formatPayoutLabel,
  resolveSelectedAsset,
  canSubmitCustomAsset,
  buildCustomCatalogEntry,
  matchesPayoutFilter,
}} from 'file:///{UI_UTILS.as_posix()}';
const result = ({expression});
process.stdout.write(JSON.stringify(result));
"""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"node failed: {proc.stderr or proc.stdout}")
    return json.loads(proc.stdout)


def test_blank_custom_input_not_submittable():
    assert _eval_js("canSubmitCustomAsset('')") is False
    assert _eval_js("canSubmitCustomAsset('   ')") is False


def test_whitespace_input_trims_for_submit():
    assert _eval_js("canSubmitCustomAsset('  BTCUSD  ')") is True
    entry = _eval_js("buildCustomCatalogEntry('  BTCUSD  ')")
    assert entry["symbol"] == "BTCUSD"
    assert entry["payout"] is None  # never invent 90


def test_payout_display_known_and_unknown():
    assert _eval_js("formatPayoutLabel(85)") == "85%"
    assert _eval_js("formatPayoutLabel(92)") == "92%"
    assert _eval_js("formatPayoutLabel(null)") == "—%"
    assert _eval_js("formatPayoutLabel(undefined)") == "—%"


def test_resolve_selected_payout_from_catalog():
    catalog = [
        {"symbol": "BTCUSD", "payout": 85},
        {"symbol": "EURUSD_otc", "payout": 92},
        {"symbol": "CUSTOM_X", "payout": None},
    ]
    # Pass catalog inline via JSON
    script_catalog = json.dumps(catalog)
    btc = _eval_js(
        f"formatPayoutLabel(resolveSelectedAsset({script_catalog}, 'BTCUSD')?.payout)"
    )
    eur = _eval_js(
        f"formatPayoutLabel(resolveSelectedAsset({script_catalog}, 'EURUSD_otc')?.payout)"
    )
    unk = _eval_js(
        f"formatPayoutLabel(resolveSelectedAsset({script_catalog}, 'CUSTOM_X')?.payout)"
    )
    missing = _eval_js(
        f"formatPayoutLabel(resolveSelectedAsset({script_catalog}, 'NOPE')?.payout)"
    )
    assert btc == "85%"
    assert eur == "92%"
    assert unk == "—%"
    assert missing == "—%"


def test_unknown_payout_excluded_from_high_payout_tabs():
    assert _eval_js("matchesPayoutFilter({payout: null}, '90%+')") is False
    assert _eval_js("matchesPayoutFilter({payout: 92}, '92%+')") is True
    assert _eval_js("matchesPayoutFilter({payout: null}, 'ALL')") is True


def test_health_live_payload_independent_of_services():
    """Liveness must not require OpenWA or bound services for the response builder."""
    # Ready without services is not ready
    status, body = _readiness_response(None)
    assert status == 503
    assert body["status"] == "not_ready"
    assert "services_not_bound" in body["reasons"]
    assert body["openwa_required"] is False


def test_health_ready_standby_without_ssid():
    settings = AgentSettings.from_env({
        "PO_SSID": "demo_ssid_placeholder",
        "TELEMETRY_PORT": "8090",
        "OPENWA_API_URL": "http://localhost:8080",
    })
    collector = MagicMock()
    collector.metrics = {"running": False}
    services = AgentServices(
        settings=settings,
        loop=MagicMock(),
        sink=MagicMock(),
        collector=collector,
        updater=MagicMock(),
        tools=MagicMock(),
        wa_bridge=MagicMock(),
        bridge_api=MagicMock(),
    )
    status, body = _readiness_response(services)
    assert status == 200
    assert body["status"] == "ready"
    assert body["ssid_configured"] is False
    assert body["openwa_required"] is False


def test_health_ready_requires_collector_when_ssid_configured():
    settings = AgentSettings.from_env({
        "PO_SSID": "live_session_token_xyz",
        "TELEMETRY_PORT": "8090",
        "OPENWA_API_URL": "http://localhost:8080",
    })
    collector = MagicMock()
    collector.metrics = {"running": False}
    services = AgentServices(
        settings=settings,
        loop=MagicMock(),
        sink=MagicMock(),
        collector=collector,
        updater=MagicMock(),
        tools=MagicMock(),
        wa_bridge=MagicMock(),
        bridge_api=MagicMock(),
    )
    status, body = _readiness_response(services)
    assert status == 503
    assert body["status"] == "not_ready"
    assert "collector_not_running" in body["reasons"]

    collector.metrics = {"running": True}
    status2, body2 = _readiness_response(services)
    assert status2 == 200
    assert body2["status"] == "ready"


def test_dockerfile_and_compose_declare_data_agent_health():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "HEALTHCHECK" in dockerfile
    assert "/api/health/live" in dockerfile
    assert "healthcheck:" in compose
    assert "/api/health/live" in compose
    # Must not require OpenWA service_healthy dependency
    assert "condition: service_healthy" not in compose


def test_compose_config_validates_if_docker_available():
    """Validate compose file when docker compose is installed; skip otherwise."""
    try:
        proc = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE_FILE), "config"],
            capture_output=True,
            text=True,
            cwd=str(COMPOSE_FILE.parent),
            timeout=60,
            check=False,
        )
    except FileNotFoundError:
        pytest.skip("docker not installed")
    if proc.returncode != 0 and "docker" in (proc.stderr or "").lower() and "not" in (proc.stderr or "").lower():
        pytest.skip(f"docker unavailable: {proc.stderr}")
    # Some environments lack docker daemon; treat that as skip
    if proc.returncode != 0 and (
        "Cannot connect" in (proc.stderr or "")
        or "error during connect" in (proc.stderr or "").lower()
        or "permission denied" in (proc.stderr or "").lower()
    ):
        pytest.skip(f"docker daemon unavailable: {proc.stderr}")
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_telemetry_handler_has_services_attr_default_none():
    # Composition root binds services before HTTP starts; import default is None.
    assert hasattr(TelemetryHTTPHandler, "services")
    assert TelemetryHTTPHandler.services is None
