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
