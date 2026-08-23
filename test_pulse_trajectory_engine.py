from __future__ import annotations

import threading
import time
import pytest
from app.backend.services.pulse_trajectory_engine import (
    PulseTrajectoryEngine,
    ActivePulseTrade,
    CHECKPOINT_INTERVALS,
)


@pytest.fixture(autouse=True)
def reset_engine():
    engine = PulseTrajectoryEngine.get_instance()
    with engine._trade_lock:
        engine._active_trades.clear()
        engine._settled_trajectories.clear()
    yield engine
    with engine._trade_lock:
        engine._active_trades.clear()
        engine._settled_trajectories.clear()


def test_trajectory_engine_empty_analytics(reset_engine):
    engine = reset_engine
    analytics = engine.get_trajectory_analytics()
    assert analytics["total_trades"] == 0
    assert analytics["clean_wins"] == 0
    assert analytics["win_rate"] == 0.0
    assert analytics["horizon_recommendations"] == {"60s": 0, "300s": 0}
    assert analytics["recent_trajectories"] == []


def test_trajectory_engine_call_lifecycle(reset_engine):
    engine = reset_engine
    now = time.time()
    trade_id = "test_pulse_call_1"

    engine.register_pulse_trade(
        trade_id=trade_id,
        asset="EURUSD_otc",
        direction="CALL",
        entry_price=1.0500,
        opened_at=now,
        expiration_seconds=60,
        entry_context={"regime_label": "TREND_PULLBACK", "pulse_confidence": 85},
    )

    # Check registered
    with engine._trade_lock:
        assert trade_id in engine._active_trades
        trade = engine._active_trades[trade_id]
        assert trade.entry_price == 1.0500
        assert trade.direction == "call"

    # Simulate ticks with price increase
    engine.record_tick("EURUSD_otc", price=1.0510, timestamp=now + 10)
    engine.record_tick("EURUSD_otc", price=1.0520, timestamp=now + 35)
    engine.record_tick("EURUSD_otc", price=1.0495, timestamp=now + 45)
    engine.record_tick("EURUSD_otc", price=1.0525, timestamp=now + 60)

    # Settle trade as win
    report = engine.settle_pulse_trade(
        trade_id=trade_id,
        exit_price=1.0525,
        outcome="win",
        settled_at=now + 60,
    )

    assert report is not None
    assert report["outcome"] == "win"
    assert report["attribution"] == "CLEAN_WIN"
    assert report["recommended_horizon"] == 60
    assert report["mfe"] == round(1.0525 - 1.0500, 6)
    assert report["mae"] == round(1.0500 - 1.0495, 6)
    assert report["checkpoints"]["30s"]["price"] == 1.0520
    assert report["checkpoints"]["30s"]["favorable"] is True
    assert report["checkpoints"]["60s"]["price"] == 1.0525
    assert report["checkpoints"]["60s"]["favorable"] is True


def test_trajectory_engine_premature_expiration_attribution(reset_engine):
    engine = reset_engine
    now = time.time()
    trade_id = "test_premature_1"

    engine.register_pulse_trade(
        trade_id=trade_id,
        asset="GBPUSD_otc",
        direction="CALL",
        entry_price=1.2000,
        opened_at=now,
        expiration_seconds=60,
    )

    # Price dropped at 60s (loss), but recovered strongly at 180s/300s
    engine.record_tick("GBPUSD_otc", price=1.1990, timestamp=now + 30)
    engine.record_tick("GBPUSD_otc", price=1.1985, timestamp=now + 60)
    engine.record_tick("GBPUSD_otc", price=1.2020, timestamp=now + 180)
    engine.record_tick("GBPUSD_otc", price=1.2030, timestamp=now + 300)

    report = engine.settle_pulse_trade(
        trade_id=trade_id,
        exit_price=1.1985,
        outcome="loss",
        settled_at=now + 60,
    )

    assert report is not None
    assert report["attribution"] == "PREMATURE_EXPIRATION"
    assert report["recommended_horizon"] == 300
    assert "Extend" in report["recommendation"] or "extend" in report["recommendation"]


def test_trajectory_engine_momentum_exhaustion_attribution(reset_engine):
    engine = reset_engine
    now = time.time()
    trade_id = "test_exhaustion_1"

    engine.register_pulse_trade(
        trade_id=trade_id,
        asset="USDJPY_otc",
        direction="PUT",
        entry_price=150.00,
        opened_at=now,
        expiration_seconds=300,
    )

    # Price dropped quickly at 60s (PUT was winning), then reversed upward by 300s (loss)
    engine.record_tick("USDJPY_otc", price=149.80, timestamp=now + 60)  # PUT favorable at 60s
    engine.record_tick("USDJPY_otc", price=150.20, timestamp=now + 180)
    engine.record_tick("USDJPY_otc", price=150.35, timestamp=now + 300)

    report = engine.settle_pulse_trade(
        trade_id=trade_id,
        exit_price=150.35,
        outcome="loss",
        settled_at=now + 300,
    )

    assert report is not None
    assert report["attribution"] == "MOMENTUM_EXHAUSTION"
    assert report["recommended_horizon"] == 60
    assert "60s" in report["recommendation"]


def test_trajectory_engine_structural_trap_attribution(reset_engine):
    engine = reset_engine
    now = time.time()
    trade_id = "test_trap_1"

    engine.register_pulse_trade(
        trade_id=trade_id,
        asset="AUDCAD_otc",
        direction="CALL",
        entry_price=0.9000,
        opened_at=now,
        expiration_seconds=60,
    )

    # Immediate adverse spike against CALL (price collapsed to 0.8950, max price was entry price)
    engine.record_tick("AUDCAD_otc", price=0.8970, timestamp=now + 30)
    engine.record_tick("AUDCAD_otc", price=0.8950, timestamp=now + 60)

    report = engine.settle_pulse_trade(
        trade_id=trade_id,
        exit_price=0.8950,
        outcome="loss",
        settled_at=now + 60,
    )

    assert report is not None
    assert report["attribution"] == "STRUCTURAL_TRAP"
    assert report["mfe"] == 0.0
    assert report["mae"] == round(0.9000 - 0.8950, 6)


def test_trajectory_engine_bounded_deque_eviction(reset_engine):
    engine = reset_engine
    now = time.time()

    # Settle 550 trades to verify bounded maxlen=500
    for i in range(550):
        t_id = f"bulk_trade_{i}"
        engine.register_pulse_trade(
            trade_id=t_id,
            asset="EURUSD_otc",
            direction="CALL",
            entry_price=1.0500,
            opened_at=now,
        )
        engine.settle_pulse_trade(
            trade_id=t_id,
            exit_price=1.0510,
            outcome="win",
        )

    with engine._trade_lock:
        assert len(engine._settled_trajectories) == 500

    history = engine.get_trajectory_history(limit=50)
    assert len(history) == 50
    assert history[-1]["trade_id"] == "bulk_trade_549"


def test_trajectory_engine_thread_safety(reset_engine):
    engine = reset_engine
    threads = []
    num_threads = 8
    trades_per_thread = 25

    def worker(worker_id: int):
        for i in range(trades_per_thread):
            t_id = f"th_{worker_id}_{i}"
            now = time.time()
            engine.register_pulse_trade(
                trade_id=t_id,
                asset="EURUSD_otc",
                direction="CALL" if i % 2 == 0 else "PUT",
                entry_price=1.0500 + (worker_id * 0.001),
                opened_at=now,
            )
            # Record some concurrent ticks
            engine.record_tick("EURUSD_otc", price=1.0505, timestamp=now + 10)
            engine.record_tick("EURUSD_otc", price=1.0495, timestamp=now + 35)

            engine.settle_pulse_trade(
                trade_id=t_id,
                exit_price=1.0510,
                outcome="win" if i % 2 == 0 else "loss",
            )

    for w in range(num_threads):
        t = threading.Thread(target=worker, args=(w,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    analytics = engine.get_trajectory_analytics()
    assert analytics["total_trades"] == num_threads * trades_per_thread
    assert len(engine.get_trajectory_history(limit=500)) == num_threads * trades_per_thread
