"""
Unit & Integration Tests for Sigmoid Liquidity and Tick Density Calculations.

Verifies:
- Mathematical accuracy of Sigmoid curve mapping centered at 120 ticks/min.
- Warmup buffer startup dampening.
- Headroom preservation for extreme broker tick bursts (>300 ticks/min).
- Dynamic velocity points in DataBridgeAPI embedding liquidity_score and liquidity_level.
- LiquidityFilter gate evaluations using Sigmoid bounds [30.0, 70.0].
"""

from __future__ import annotations

import sqlite3
import pytest

from data_agent.src.filters.liquidity_math import (
    LIQ_MIDPOINT,
    LIQ_STEEPNESS,
    calculate_sigmoid_liquidity,
    classify_liquidity_level,
)
from data_agent.src.filters.liquidity_filter import LiquidityFilter
from data_agent.src.api_bridge import DataBridgeAPI


def test_sigmoid_exact_midpoint():
    """120.0 ticks/min (the Pocket Option OTC baseline) must map to exactly 50.0%."""
    score, level = calculate_sigmoid_liquidity(tick_frequency=120.0, buffer_len=30)
    assert score == 50.0
    assert level == "MEDIUM"


def test_sigmoid_low_liquidity():
    """Slow tick streams (<60 ticks/min) must produce < 30.0% score and LOW level."""
    # Zero frequency
    score_zero, level_zero = calculate_sigmoid_liquidity(tick_frequency=0.0, buffer_len=30)
    assert score_zero == 0.0
    assert level_zero == "LOW"

    # 60 ticks/min (x = (60-120)/120 = -0.5, exp(2) ≈ 7.389 -> 11.9%)
    score_60, level_60 = calculate_sigmoid_liquidity(tick_frequency=60.0, buffer_len=30)
    assert score_60 < 30.0
    assert level_60 == "LOW"
    assert round(score_60, 1) == 11.9


def test_sigmoid_optimal_otc_band():
    """Typical winning OTC profiles (120-135 ticks/min) must sit in the 50%-60% corridor (MEDIUM)."""
    score_125, level_125 = calculate_sigmoid_liquidity(tick_frequency=125.0, buffer_len=30)
    assert round(score_125, 1) == 54.2
    assert level_125 == "MEDIUM"

    score_130, level_130 = calculate_sigmoid_liquidity(tick_frequency=130.0, buffer_len=30)
    assert round(score_130, 1) == 58.3
    assert level_130 == "MEDIUM"


def test_sigmoid_extreme_burst_headroom():
    """
    High tick bursts (>180 ticks/min) produce > 70.0% (HIGH) while preserving headroom
    for extreme spikes (>300 ticks/min) without flatlining at 100%.
    """
    # 180 ticks/min -> 88.1% (HIGH)
    score_180, level_180 = calculate_sigmoid_liquidity(tick_frequency=180.0, buffer_len=30)
    assert score_180 > 70.0
    assert level_180 == "HIGH"
    assert round(score_180, 1) == 88.1

    # 300 ticks/min (burst)
    score_300, level_300 = calculate_sigmoid_liquidity(tick_frequency=300.0, buffer_len=30)
    assert score_300 > 85.0
    assert level_300 == "HIGH"


def test_sigmoid_warmup_buffer_dampening():
    """Startup with fewer than 30 buffer ticks dampens the score proportionally."""
    # 15 ticks out of 30 warmup target -> 50% multiplier
    score_warmup, _ = calculate_sigmoid_liquidity(tick_frequency=120.0, buffer_len=15, min_warmup_buffer=30)
    assert score_warmup == 25.0  # 50.0% * 0.5 = 25.0%

    # 0 ticks buffer
    score_empty, level_empty = calculate_sigmoid_liquidity(tick_frequency=120.0, buffer_len=0, min_warmup_buffer=30)
    assert score_empty == 0.0
    assert level_empty == "LOW"


def test_classify_liquidity_level():
    """Verify discrete classification utility."""
    assert classify_liquidity_level(15.0) == "LOW"
    assert classify_liquidity_level(29.9) == "LOW"
    assert classify_liquidity_level(30.0) == "MEDIUM"
    assert classify_liquidity_level(50.0) == "MEDIUM"
    assert classify_liquidity_level(69.9) == "MEDIUM"
    assert classify_liquidity_level(70.0) == "HIGH"
    assert classify_liquidity_level(95.0) == "HIGH"


def test_liquidity_filter_gate_evaluations():
    """LiquidityFilter correctly gates based on Sigmoid bounds [30.0, 70.0]."""
    filter_gate = LiquidityFilter(min_liquidity=30.0, max_liquidity=70.0)

    # 1. Normal OTC liquidity (53.3% -> MEDIUM) -> PASS
    passed, veto = filter_gate.evaluate({}, market_context={"liquidity_score": 53.3})
    assert passed is True
    assert veto is None

    # 2. Low liquidity (22.0% -> LOW) -> VETO
    passed_low, veto_low = filter_gate.evaluate({}, market_context={"liquidity_score": 22.0})
    assert passed_low is False
    assert "liquidity_score_out_of_bounds" in veto_low
    assert "[LOW]" in veto_low

    # 3. High liquidity burst (85.0% -> HIGH) -> VETO
    passed_high, veto_high = filter_gate.evaluate({}, market_context={"liquidity_score": 85.0})
    assert passed_high is False
    assert "liquidity_score_out_of_bounds" in veto_high
    assert "[HIGH]" in veto_high

    # 4. Missing score -> FAIL-CLOSED
    passed_none, veto_none = filter_gate.evaluate({}, market_context={})
    assert passed_none is False
    assert veto_none == "liquidity_context_unavailable"


def test_api_bridge_tick_velocity_sigmoid_fields(tmp_path):
    """Verify DataBridgeAPI.get_tick_velocity() embeds liquidity_score and liquidity_level."""
    db_path = tmp_path / "test_velocity.db"

    # Seed test SQLite db with 15 ticks across 3 5-second buckets
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE ticks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "timestamp REAL, "
            "asset TEXT, "
            "price REAL, "
            "received_at REAL, "
            "status TEXT DEFAULT 'pending')"
        )
        base_ts = 1700000000.0
        # Bucket 1: 10 ticks (10 ticks / 5s = 120 ticks/min)
        for i in range(10):
            conn.execute(
                "INSERT INTO ticks (timestamp, asset, price, received_at) VALUES (?, ?, ?, ?)",
                (base_ts + i * 0.4, "EURUSD_otc", 1.0850 + i * 0.0001, base_ts + i * 0.4),
            )
        # Bucket 2: 5 ticks (5 ticks / 5s = 60 ticks/min)
        for i in range(5):
            conn.execute(
                "INSERT INTO ticks (timestamp, asset, price, received_at) VALUES (?, ?, ?, ?)",
                (base_ts + 5.0 + i * 0.8, "EURUSD_otc", 1.0860, base_ts + 5.0 + i * 0.8),
            )

    api = DataBridgeAPI(db_path=str(db_path))
    res = api.get_tick_velocity(asset="EURUSD_otc", limit=10, interval_sec=5)

    assert res["status"] == "ok"
    assert res["count"] == 2
    points = res["points"]
    assert len(points) == 2

    # Check that each point contains the new Sigmoid fields
    for pt in points:
        assert "ticks_per_min" in pt
        assert "liquidity_score" in pt
        assert "liquidity_level" in pt
        assert pt["liquidity_level"] in ("LOW", "MEDIUM", "HIGH")
        assert 0.0 <= pt["liquidity_score"] <= 100.0
        assert "vol" in pt
        assert "sample_count" in pt
