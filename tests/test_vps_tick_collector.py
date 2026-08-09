"""
Unit test for VPS Tick Collector and GCP Sink Fallback.
"""

import asyncio
import os
import sqlite3
import pytest
from data_agent.src.tick_collector.ssid_collector import SSIDTickCollector
from data_agent.src.tick_collector.gcp_sink import GCPTickSink


@pytest.mark.asyncio
async def test_gcp_sink_local_fallback(tmp_path):
    db_file = tmp_path / "test_ticks.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=0.5)

    sample_tick = {
        "timestamp": 1700000000.0,
        "asset": "EURUSD_otc",
        "price": 1.0850,
        "dir": "up",
        "is_demo": 1,
        "received_at": 1700000000.1,
    }

    sink.push_tick(sample_tick)
    await sink.flush()

    assert sink.metrics["total_flushed"] == 1

    # Verify SQLite insertion
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT asset, price FROM ticks")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0][0] == "EURUSD_otc"
    assert abs(rows[0][1] - 1.0850) < 1e-4


def test_ssid_collector_instantiation():
    collector = SSIDTickCollector(ssid="test_ssid_12345", assets=["EURUSD_otc"])
    metrics = collector.metrics
    assert metrics["running"] is False
    assert "EURUSD_otc" in collector.assets


def test_ssid_collector_auto_detect_demo_and_real():
    # 1. Real account SSID frame (isDemo: 0)
    real_frame = '42["auth",{"session":"real_session_token_xyz","isDemo":0,"uid":99999,"platform":2}]'
    collector_real = SSIDTickCollector(ssid=real_frame, assets=["EURUSD_otc"])
    assert collector_real.is_demo == 0
    assert collector_real.ssid == "real_session_token_xyz"
    assert "api-us-north.po.market" in collector_real.target_ws_url

    # 2. Demo account SSID frame (isDemo: 1)
    demo_frame = '42["auth",{"session":"demo_session_token_abc","isDemo":1,"uid":88888,"platform":2}]'
    collector_demo = SSIDTickCollector(ssid=demo_frame, assets=["EURUSD_otc"])
    assert collector_demo.is_demo == 1
    assert collector_demo.ssid == "demo_session_token_abc"
    assert "demo-api-eu.po.market" in collector_demo.target_ws_url
