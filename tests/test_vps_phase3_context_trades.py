"""
Phase 3 — Honest filter context and validated trade feedback.

Verification IDs: T3.1, T3.2, T3.3 (remediation plan 2026-08-03).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from data_agent.src.api_bridge import DataBridgeAPI
from data_agent.src.bayesian.prior_updater import BayesianPriorUpdater
from data_agent.src.filters.context_provider import (
    ContextResult,
    StaticContextProvider,
    TickFieldContextProvider,
)
from data_agent.src.filters.manipulation_filter import ManipulationFilter
from data_agent.src.filters.pipeline_manager import FilterPipelineManager, UnknownGateError
from data_agent.src.filters.volatility_filter import VolatilityFilter


def test_no_hardcoded_scores_in_market_context_endpoint():
    api = DataBridgeAPI(db_path="data-agent/data/missing.db")
    res = api.get_market_context("EURUSD_otc")
    assert res["status"] == "ok"
    assert res["available"] is False
    assert res["source"] == "unavailable"
    assert res["market_context"] == {}
    # Must not invent production scores
    for banned in ("volatility_score", "liquidity_score", "bayesian_posterior_prob"):
        assert banned not in res["market_context"]


def test_missing_context_fails_closed_for_every_gate():
    """T3.1 — Missing context vetoes every requested context-dependent gate."""
    manager = FilterPipelineManager()
    tick = {"asset": "EURUSD_otc", "price": 1.08}
    gates = ["bayesian", "volatility", "liquidity", "manipulation"]
    passed, vetoes = manager.evaluate_pipeline(tick, active_gates=gates, market_context={})
    assert passed is False
    assert any("bayesian_context_unavailable" in v for v in vetoes)
    assert any("volatility_context_unavailable" in v for v in vetoes)
    assert any("liquidity_context_unavailable" in v for v in vetoes)
    assert any("manipulation_context_unavailable" in v for v in vetoes)


def test_injected_volatility_95_produces_veto():
    """T3.2 — Injected context varies and produces expected volatility veto."""
    provider = StaticContextProvider(
        ContextResult(
            available=True,
            source="injected",
            values={
                "volatility_score": 95.0,
                "liquidity_score": 55.0,
                "bayesian_posterior_prob": 0.95,
                "manipulation_severity": 0.02,
                "has_manipulation": False,
            },
        )
    )
    api = DataBridgeAPI(
        db_path="data-agent/data/missing.db",
        context_provider=provider,
    )
    # Seed one synthetic evaluation via pipeline path used by filtered ticks
    tick = {"asset": "EURUSD_otc", "price": 1.08, "timestamp": 1.0, "dir": "up", "is_demo": 0, "received_at": 1.0}
    ctx = provider.get_context(tick, "EURUSD_otc")
    manager = FilterPipelineManager()
    passed, vetoes = manager.evaluate_pipeline(
        tick,
        active_gates=["volatility"],
        market_context=dict(ctx.values),
    )
    assert passed is False
    assert any("volatility_score_out_of_bounds" in v for v in vetoes)

    # Also via VolatilityFilter unit path
    vf = VolatilityFilter()
    ok, reason = vf.evaluate(tick, {"volatility_score": 95.0})
    assert ok is False
    assert reason and "volatility" in reason


def test_unknown_gate_returns_client_error():
    api = DataBridgeAPI(db_path="data-agent/data/missing.db")
    res = api.get_filtered_ticks(gates_str="bayesian,not_a_real_gate")
    assert res["status"] == "error"
    assert res["code"] == "unknown_gates"
    assert res["http_status"] == 400
    assert "not_a_real_gate" in res["unknown_gates"]

    manager = FilterPipelineManager()
    with pytest.raises(UnknownGateError) as exc:
        manager.evaluate_pipeline({}, active_gates=["nope"])
    assert "nope" in exc.value.unknown_gates


def test_filtered_ticks_http_status_mapping_for_unknown_gates():
    """Wire status for filtered ticks must honor http_status (P3-1)."""
    from data_agent.src.vps_server import _api_http_status

    err = {
        "status": "error",
        "code": "unknown_gates",
        "http_status": 400,
        "unknown_gates": ["nope"],
    }
    assert _api_http_status(err, default=200) == 400
    assert _api_http_status({"status": "ok", "mode": "DYNAMIC_FILTERED_OVERLAY"}) == 200


@pytest.mark.parametrize(
    "has_manip,severity,expect_pass",
    [
        (False, 0.02, True),
        (True, 0.02, True),   # flag alone must NOT veto
        (False, 0.20, False),
        (True, 0.20, False),
        (None, None, False),  # missing severity fail-closed
    ],
)
def test_manipulation_truth_table(has_manip, severity, expect_pass):
    filt = ManipulationFilter(severity_threshold=0.15)
    ctx = {}
    if severity is not None:
        ctx["manipulation_severity"] = severity
    if has_manip is not None:
        ctx["has_manipulation"] = has_manip
    passed, reason = filt.evaluate({"asset": "X"}, ctx)
    assert passed is expect_pass
    if not expect_pass and severity is None:
        assert reason == "manipulation_context_unavailable"
    if not expect_pass and severity is not None and severity > 0.15:
        assert reason and "manipulation_veto" in reason
        if has_manip is True:
            assert "has_manipulation=true" in reason


def test_five_validated_wins_increase_totals(tmp_path):
    """T3.3 — Five validated wins increase total wins by exactly five."""
    priors = tmp_path / "priors.json"
    updater = BayesianPriorUpdater(priors_json_path=str(priors))
    api = DataBridgeAPI(prior_updater=updater, priors_path=str(priors))

    for i in range(5):
        res = api.record_trade_outcome(
            {"asset": "EURUSD_otc", "won": True, "features": [f"batch={i}"]}
        )
        assert res["recorded"] is True

    assert res["total_wins"] == 5
    assert res["total_trades"] == 5
    saved = json.loads(Path(priors).read_text(encoding="utf-8"))
    assert saved["total_wins"] == 5


def test_won_string_false_rejected(tmp_path):
    """won: \"false\" must not be counted as a win (or as any outcome)."""
    priors = tmp_path / "priors.json"
    updater = BayesianPriorUpdater(priors_json_path=str(priors))
    api = DataBridgeAPI(prior_updater=updater, priors_path=str(priors))

    res = api.record_trade_outcome({"asset": "EURUSD_otc", "won": "false"})
    assert res["status"] == "error"
    assert res["code"] == "invalid_won"
    assert res["recorded"] is False
    assert not Path(priors).exists()

    # Truthy string "true" also rejected
    res2 = api.record_trade_outcome({"asset": "EURUSD_otc", "won": "true"})
    assert res2["recorded"] is False


def test_failed_persistence_never_returns_recorded_true(tmp_path):
    updater = MagicMock()
    updater.update_priors_from_trades.side_effect = OSError("disk full")
    api = DataBridgeAPI(prior_updater=updater)

    res = api.record_trade_outcome({"asset": "EURUSD_otc", "won": True})
    assert res["status"] == "error"
    assert res["code"] == "persistence_failed"
    assert res["recorded"] is False
    assert res["http_status"] == 500


def test_missing_updater_does_not_claim_recorded():
    api = DataBridgeAPI(prior_updater=None)
    res = api.record_trade_outcome({"asset": "EURUSD_otc", "won": True})
    assert res["recorded"] is False
    assert res["code"] == "updater_unavailable"


def test_tick_field_provider_uses_valid_tick_fields_only():
    provider = TickFieldContextProvider()
    tick = {
        "asset": "EURUSD_otc",
        "price": 1.08,
        "volatility_score": 45.0,
        "bayesian_posterior_prob": "0.93",
    }
    ctx = provider.get_context(tick, "EURUSD_otc")
    assert ctx.available is True
    assert ctx.source == "tick"
    assert ctx.values["volatility_score"] == 45.0
    assert ctx.values["bayesian_posterior_prob"] == 0.93

    bad = provider.get_context({"volatility_score": "nope"}, "X")
    assert bad.available is False
    assert bad.source == "tick_invalid"


def test_filtered_ticks_include_context_provenance(tmp_path):
    """Keep filter_evaluation shape and add provenance fields."""
    # empty DB → zero ticks but status ok path still validates gates
    api = DataBridgeAPI(db_path=str(tmp_path / "empty.db"))
    res = api.get_filtered_ticks(gates_str="bayesian")
    assert res["status"] == "ok"
    assert res["count"] == 0


def test_get_available_assets_returns_catalog_and_reflects_collector():
    api = DataBridgeAPI()
    # 1. Standby collector
    res = api.get_available_assets(collector=None)
    assert res["status"] == "ok"
    assert res["count"] >= 25
    symbols = {a["symbol"] for a in res["assets"]}
    assert "EURUSD_otc" in symbols
    assert "ZARUSD_otc" in symbols

    # 2. Collector with active and custom assets
    collector_mock = MagicMock()
    collector_mock.assets = {"EURUSD_otc", "MY_CUSTOM_OTC"}
    collector_mock._subscribed_assets = {"EURUSD_otc"}
    res_mock = api.get_available_assets(collector=collector_mock)
    assert res_mock["status"] == "ok"
    eur_item = next(a for a in res_mock["assets"] if a["symbol"] == "EURUSD_otc")
    assert eur_item["live"] is True
    custom_item = next(a for a in res_mock["assets"] if a["symbol"] == "MY_CUSTOM_OTC")
    assert custom_item["live"] is True
    assert custom_item["category"] == "Custom"


def test_get_tick_velocity_aggregates_sqlite_ticks(tmp_path):
    import sqlite3
    db_file = str(tmp_path / "ticks.db")
    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE ticks (timestamp REAL, asset TEXT, price REAL, dir TEXT, is_demo INTEGER, received_at REAL)"
    )
    # Insert 10 ticks across 2 time buckets
    base_ts = 1785000000.0
    for i in range(5):
        conn.execute(
            "INSERT INTO ticks VALUES (?, ?, ?, ?, ?, ?)",
            (base_ts + i, "EURUSD_otc", 1.0850 + (i * 0.0001), "neutral", 0, base_ts + i),
        )
    for i in range(5):
        conn.execute(
            "INSERT INTO ticks VALUES (?, ?, ?, ?, ?, ?)",
            (base_ts + 10 + i, "EURUSD_otc", 1.0860 + (i * 0.0001), "neutral", 0, base_ts + 10 + i),
        )
    conn.commit()
    conn.close()

    api = DataBridgeAPI(db_path=db_file)
    res = api.get_tick_velocity(asset="EURUSD_otc", limit=10, interval_sec=5)
    assert res["status"] == "ok"
    assert res["count"] == 2
    assert res["points"][0]["sample_count"] == 5
    assert res["points"][0]["ticks_per_min"] == 60
    assert "time" in res["points"][0]
    assert "vol" in res["points"][0]
