"""Full Test Suite for VPS Data Agent Subsystem and DaaS Data Bridge API."""
import os
import json
import pytest
from data_agent.src.filters.bayesian_filter import BayesianFilter
from data_agent.src.filters.volatility_filter import VolatilityFilter
from data_agent.src.filters.liquidity_filter import LiquidityFilter
from data_agent.src.filters.manipulation_filter import ManipulationFilter
from data_agent.src.filters.pipeline_manager import FilterPipelineManager
from data_agent.src.api_bridge import DataBridgeAPI
from data_agent.src.hermes.xai_provider import XAIProvider


def test_decoupled_filter_pipeline():
    """Verify that individual filters evaluate correctly and independently."""
    manager = FilterPipelineManager()

    mock_tick = {"asset": "EURUSD_otc", "price": 1.0850, "dir": 1}
    mock_ctx_pass = {
        "volatility_score": 45.0,
        "liquidity_score": 55.0,
        "bayesian_posterior_prob": 0.95,
        "has_manipulation": False,
        "manipulation_severity": 0.02
    }

    # Test passing pipeline
    passed, vetoes = manager.evaluate_pipeline(mock_tick, active_gates=["bayesian", "volatility", "liquidity", "manipulation"], market_context=mock_ctx_pass)
    assert passed is True
    assert len(vetoes) == 0

    # Test failing volatility gate
    mock_ctx_vol_fail = dict(mock_ctx_pass)
    mock_ctx_vol_fail["volatility_score"] = 15.0  # Below min 30.0
    passed_vol, vetoes_vol = manager.evaluate_pipeline(mock_tick, active_gates=["volatility"], market_context=mock_ctx_vol_fail)
    assert passed_vol is False
    assert any("volatility" in v for v in vetoes_vol)


def test_data_bridge_api_endpoints():
    """Verify that DataBridgeAPI returns clean raw data and gated overlays."""
    api = DataBridgeAPI(db_path="data-agent/data/test_ticks.db")

    # Test clean raw ticks endpoint
    raw_res = api.get_raw_ticks(asset="EURUSD_otc", limit=10)
    assert raw_res["status"] == "ok"
    assert raw_res["mode"] == "RAW_CLEAN_DATA"
    assert isinstance(raw_res["ticks"], list)

    # Test filtered overlay endpoint
    filt_res = api.get_filtered_ticks(asset="EURUSD_otc", limit=5, gates_str="bayesian,volatility")
    assert filt_res["status"] == "ok"
    assert filt_res["mode"] == "DYNAMIC_FILTERED_OVERLAY"
    assert "bayesian" in filt_res["active_gates"]

    # Test trade outcome recording
    rec_res = api.record_trade_outcome({"asset": "EURUSD_otc", "won": True})
    assert rec_res["status"] == "ok"
    assert rec_res["recorded"] is True


@pytest.mark.asyncio
async def test_xai_provider_offline_mode():
    """Verify xAI provider gracefully handles offline mode without API key."""
    provider = XAIProvider(api_key=None)
    res = await provider.chat_completion(
        messages=[{"role": "user", "content": "Analyze market"}]
    )
    assert res["status"] == "mocked"
    assert "Hermes Agent operating in offline evaluation mode" in res["content"]
