"""
Comprehensive Unit & Integration Test Suite for VPS Data Agent Architecture.
"""

import asyncio
import json
import pytest
from data_agent.src.tick_collector.ssid_collector import SSIDTickCollector
from data_agent.src.tick_collector.gcp_sink import GCPTickSink
from data_agent.src.bayesian.prior_updater import BayesianPriorUpdater
from data_agent.src.hermes.xai_provider import XAIProvider
from data_agent.src.hermes.market_tools import HermesMarketTools
from data_agent.src.whatsapp.openwa_bridge import OpenWABridge


@pytest.mark.asyncio
async def test_full_pipeline_flow(tmp_path):
    # 1. Initialize local sink
    db_path = tmp_path / "test_ticks.db"
    sink = GCPTickSink(local_db_path=str(db_path), flush_interval_sec=0.1)

    # 2. Initialize collector and hook up sink callback
    collector = SSIDTickCollector(ssid="mock_ssid_999", assets=["EURUSD_otc"])
    collector.register_callback(sink.push_tick)

    # 3. Simulate tick reception
    mock_tick = {
        "time": 1700000010.0,
        "asset": "EURUSD_otc",
        "price": 1.0920,
        "dir": "CALL",
    }
    collector._dispatch_tick(mock_tick)

    # 4. Flush sink
    await sink.flush()
    assert sink.metrics["total_flushed"] == 1

    # 5. Calibrate priors
    priors_file = tmp_path / "bayesian_priors.json"
    updater = BayesianPriorUpdater(priors_json_path=str(priors_file))
    updater.update_priors_from_trades([{"won": True, "features": ["oteo_band=85-92"]}])

    # 6. Hermes market tools
    tools = HermesMarketTools(priors_updater=updater)
    summary = tools.get_bayesian_summary()
    assert summary["total_trades"] == 1
    assert summary["overall_win_rate"] == 100.0

    # 7. WhatsApp Alert formatting
    alert_msg = tools.format_whatsapp_alert(
        asset="EURUSD_otc",
        direction="CALL",
        confidence=0.88,
        bayesian_prob=0.91,
        reason="Oteo band 85-92 high confidence setup",
    )
    assert "EURUSD_otc" in alert_msg
    assert "CALL" in alert_msg

    # 8. OpenWA bridge dispatch check
    bridge = OpenWABridge()
    sent = await bridge.send_message(alert_msg)
    assert sent is True


@pytest.mark.asyncio
async def test_xai_provider_offline_mode():
    provider = XAIProvider(api_key="")
    assert provider.is_configured is False

    response = await provider.chat_completion(
        messages=[{"role": "user", "content": "Analyze current EURUSD_otc market condition"}]
    )
    assert response["status"] == "mocked"
    assert "offline evaluation mode" in response["content"]
