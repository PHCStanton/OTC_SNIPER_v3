"""
Phase 2 — Lossless tick buffering and non-blocking persistence.

Verification IDs: T2.1, T2.2, T2.3 (remediation plan 2026-08-03).
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from typing import List
from unittest.mock import patch

import pytest

from data_agent.src.tick_collector.gcp_sink import BufferedTick, GCPTickSink


def _make_tick(i: int, asset: str = "EURUSD_otc") -> dict:
    return {
        "timestamp": 1700000000.0 + i,
        "asset": asset,
        "price": 1.0850 + i * 0.0001,
        "dir": "up" if i % 2 == 0 else "down",
        "is_demo": 1,
        "received_at": 1700000000.1 + i,
    }


def _count_rows(db_path) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM ticks").fetchone()[0]


def _ingestion_ids(db_path) -> List[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT ingestion_id FROM ticks WHERE ingestion_id IS NOT NULL ORDER BY id"
        ).fetchall()
    return [r[0] for r in rows]


@pytest.mark.asyncio
async def test_concurrent_pushes_persist_exactly_n_unique_rows(tmp_path):
    """T2.1 — Concurrent threads push N unique ticks; SQLite has exactly N unique rows."""
    db_file = tmp_path / "concurrent.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=60.0)
    n = 200
    threads = 8
    per_thread = n // threads

    def worker(start: int) -> None:
        for i in range(start, start + per_thread):
            sink.push_tick(_make_tick(i))

    ts = [
        threading.Thread(target=worker, args=(t * per_thread,))
        for t in range(threads)
    ]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    assert sink.metrics["buffer_size"] == n
    await sink.flush()
    assert sink.metrics["buffer_size"] == 0
    assert sink.metrics["total_flushed"] == n
    assert _count_rows(db_file) == n
    ids = _ingestion_ids(db_file)
    assert len(ids) == n
    assert len(set(ids)) == n


@pytest.mark.asyncio
async def test_ticks_after_snapshot_remain_in_next_batch(tmp_path):
    """Ticks arriving after snapshot belong to the next batch."""
    db_file = tmp_path / "snapshot.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=60.0)

    sink.push_tick(_make_tick(1))
    sink.push_tick(_make_tick(2))
    batch = sink._take_snapshot()
    assert len(batch) == 2

    # Arrives after snapshot swap
    sink.push_tick(_make_tick(3))
    assert sink.metrics["buffer_size"] == 1

    # Restore path not used — write first batch then flush remainder
    await asyncio.to_thread(sink._write_batch_to_sqlite, batch)
    sink._total_flushed += len(batch)

    await sink.flush()
    assert _count_rows(db_file) == 3
    assert sink.metrics["buffer_size"] == 0


@pytest.mark.asyncio
async def test_sqlite_failure_restores_batch_and_metrics_unchanged(tmp_path):
    """T2.2 — Injected SQLite failure restores batch; total_flushed does not advance."""
    db_file = tmp_path / "fail.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=60.0)

    for i in range(5):
        sink.push_tick(_make_tick(i))

    original_ids = [b.ingestion_id for b in list(sink._buffer)]

    with patch.object(
        sink,
        "_write_batch_to_sqlite",
        side_effect=sqlite3.OperationalError("injected disk full"),
    ):
        with pytest.raises(sqlite3.OperationalError, match="injected disk full"):
            await sink.flush()

    assert sink.metrics["total_flushed"] == 0
    assert sink.metrics["flush_failures"] == 1
    assert sink.metrics["flush_retries"] == 1
    assert sink.metrics["buffer_size"] == 5
    restored_ids = [b.ingestion_id for b in list(sink._buffer)]
    assert restored_ids == original_ids
    assert _count_rows(db_file) == 0

    # Recovery flush succeeds with same ingestion IDs (idempotent)
    await sink.flush()
    assert sink.metrics["total_flushed"] == 5
    assert _count_rows(db_file) == 5
    assert set(_ingestion_ids(db_file)) == set(original_ids)


@pytest.mark.asyncio
async def test_retry_after_ambiguous_failure_creates_no_duplicates(tmp_path):
    """Retry after success-then-error ambiguity creates no duplicate local rows."""
    db_file = tmp_path / "idempotent.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=60.0)

    ticks = [_make_tick(i) for i in range(3)]
    buffered = [BufferedTick.create(t) for t in ticks]

    # First write succeeds
    await asyncio.to_thread(sink._write_batch_to_sqlite, buffered)
    assert _count_rows(db_file) == 3

    # Retry same batch (ambiguous client failure after commit)
    await asyncio.to_thread(sink._write_batch_to_sqlite, buffered)
    assert _count_rows(db_file) == 3
    assert len(set(_ingestion_ids(db_file))) == 3


@pytest.mark.asyncio
async def test_event_loop_heartbeat_during_slow_sqlite_write(tmp_path):
    """T2.3 — Slow SQLite write does not stall an event-loop heartbeat."""
    db_file = tmp_path / "slow.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=60.0)
    sink.push_tick(_make_tick(0))

    real_write = sink._write_batch_to_sqlite

    def slow_write(batch):
        time.sleep(0.35)
        return real_write(batch)

    heartbeats = 0

    async def heartbeat():
        nonlocal heartbeats
        for _ in range(20):
            await asyncio.sleep(0.02)
            heartbeats += 1

    with patch.object(sink, "_write_batch_to_sqlite", side_effect=slow_write):
        hb_task = asyncio.create_task(heartbeat())
        await sink.flush()
        await hb_task

    # If the loop were blocked by sync SQLite, heartbeats would be ~0–1.
    assert heartbeats >= 5
    assert sink.metrics["total_flushed"] == 1


@pytest.mark.asyncio
async def test_stop_final_flush_or_raises(tmp_path):
    """Stop performs a final durable flush or raises a visible error."""
    db_file = tmp_path / "stop_ok.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=60.0)
    await sink.start()
    for i in range(4):
        sink.push_tick(_make_tick(i))
    await sink.stop()
    assert _count_rows(db_file) == 4
    assert sink.metrics["buffer_size"] == 0

    # Failure path: persistent SQLite errors make stop raise
    db_fail = tmp_path / "stop_fail.db"
    sink_fail = GCPTickSink(
        local_db_path=str(db_fail),
        flush_interval_sec=60.0,
        shutdown_flush_attempts=2,
    )
    sink_fail.push_tick(_make_tick(99))
    with patch.object(
        sink_fail,
        "_write_batch_to_sqlite",
        side_effect=sqlite3.OperationalError("persistent failure"),
    ):
        with pytest.raises(RuntimeError, match="shutdown flush failed"):
            await sink_fail.stop()
    assert sink_fail.metrics["buffer_size"] == 1
    assert sink_fail.metrics["total_flushed"] == 0


@pytest.mark.asyncio
async def test_push_does_not_mutate_raw_payload(tmp_path):
    """Ingestion envelope must not mutate the caller's raw tick dict."""
    db_file = tmp_path / "raw.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=60.0)
    raw = _make_tick(1)
    snapshot = dict(raw)
    sink.push_tick(raw)
    assert raw == snapshot
    assert "ingestion_id" not in raw
    await sink.flush()
    assert "ingestion_id" not in raw


@pytest.mark.asyncio
async def test_restore_keeps_failed_batch_ahead_of_newer(tmp_path):
    """Failed snapshot is restored ahead of ticks received after the snapshot."""
    db_file = tmp_path / "order.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=60.0)

    sink.push_tick(_make_tick(1, asset="A"))
    sink.push_tick(_make_tick(2, asset="B"))
    batch = sink._take_snapshot()

    sink.push_tick(_make_tick(3, asset="C"))  # newer after snapshot
    sink._restore_snapshot_before_newer_ticks(batch)

    with sink._buffer_lock:
        assets = [b.tick["asset"] for b in sink._buffer]
    assert assets == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_cancel_after_snapshot_restores_or_persists(tmp_path):
    """Cancelled flush after snapshot must not lose ticks (buffer restore and/or SQLite)."""
    db_file = tmp_path / "cancel.db"
    sink = GCPTickSink(local_db_path=str(db_file), flush_interval_sec=60.0)
    for i in range(3):
        sink.push_tick(_make_tick(i))

    real_write = sink._write_batch_to_sqlite
    started_thread = threading.Event()
    release_thread = threading.Event()

    def blocking_write(batch):
        # Snapshot already taken before write runs in the worker thread.
        started_thread.set()
        release_thread.wait(timeout=5.0)
        return real_write(batch)

    with patch.object(sink, "_write_batch_to_sqlite", side_effect=blocking_write):
        flush_task = asyncio.create_task(sink.flush())
        # Wait until write thread is inside blocked write (snapshot already taken)
        assert await asyncio.to_thread(started_thread.wait, 5.0)
        flush_task.cancel()
        release_thread.set()
        with pytest.raises(asyncio.CancelledError):
            await flush_task

    buffered = sink.metrics["buffer_size"]
    rows = _count_rows(db_file)
    # Must not be empty in both places — lossless contract
    assert buffered + rows >= 3
    # Recovery path still works
    if buffered:
        await sink.flush()
    assert _count_rows(db_file) == 3
    assert sink.metrics["buffer_size"] == 0


@pytest.mark.asyncio
async def test_existing_fallback_test_still_passes(tmp_path):
    """Regression shape of original local fallback test."""
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
    with sqlite3.connect(db_file) as conn:
        rows = conn.execute("SELECT asset, price FROM ticks").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "EURUSD_otc"
    assert abs(rows[0][1] - 1.0850) < 1e-4
