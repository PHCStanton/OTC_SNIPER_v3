"""Tests for Calibration Intelligence integration into AI Pulse and SessionPerformanceTracker Layer 2."""

from __future__ import annotations

import json
from pathlib import Path
from time import time as unix_time
import pytest

from app.backend.services.session_tracker import (
    SessionPerformanceTracker,
    SessionSnapshot,
)
from app.backend.services.calibration_service import CalibrationService
from app.backend.services.streaming import (
    _render_calibration_context_section,
    _build_pulse_user_msg,
    _build_ai_pulse_system_msg,
)
from app.backend.services.auto_ghost import AutoGhostConfig


def test_archive_calibration_session_populates_layer2():
    tracker = SessionPerformanceTracker()
    tracker.ensure_session("ag_session_live_1")

    # Initially layer 2 is empty
    assert tracker.layer2_recent_wr() is None

    # Simulate completed calibration trades
    calib_trades = [
        {"outcome": "win", "expiration_seconds": 60, "asset": "EURCHF_otc"},
        {"outcome": "win", "expiration_seconds": 60, "asset": "NZDUSD_otc"},
        {"outcome": "loss", "expiration_seconds": 60, "asset": "AUDUSD_otc"},
        {"outcome": "win", "expiration_seconds": 300, "asset": "EURUSD_otc"},
        {"outcome": "loss", "expiration_seconds": 300, "asset": "AUDCHF_otc"},
    ]

    archived = tracker.archive_calibration_session(
        session_id="auto_ghost_calib_1725700000",
        settled_trades=calib_trades,
    )
    assert archived is True

    # Layer 2 now has evidence!
    # Overall: 3 wins (2 @ 60s, 1 @ 300s), 2 losses (1 @ 60s, 1 @ 300s) -> 3 / 5 = 60.0%
    assert tracker.layer2_recent_wr() == pytest.approx(0.60)
    assert tracker.layer2_recent_wr(horizon=60) == pytest.approx(2 / 3)
    assert tracker.layer2_recent_wr(horizon=300) == pytest.approx(1 / 2)

    # Live session counters remain strictly unaffected (0 settled in active live session)
    assert tracker.settled_count == 0
    assert tracker.current_streak == 0


def test_render_calibration_context_section_formatting():
    calib_ctx = {
        "calibration_id": "auto_ghost_calib_1725700000",
        "state": "DONE",
        "ended_at": unix_time() - 300,
        "elapsed_minutes": 5.0,
        "settled_total": 24,
        "settled_wins": 15,
        "settled_losses": 9,
        "win_rate_pct": 62.5,
        "pnl": 12.40,
        "prime_assets": ["EURCHF_otc (80.0% WR)", "NZDUSD_otc (75.0% WR)"],
        "hazard_assets": ["AUDUSD_otc (20.0% WR)", "AUDCHF_otc (0.0% WR)"],
        "favoured_regimes": ["RANGE_BOUND (70.0% WR, N=10)", "TREND_REVERSAL (60.0% WR, N=6)"],
    }

    rendered = _render_calibration_context_section(calib_ctx)
    assert "### LATEST CALIBRATION INTELLIGENCE (auto_ghost_calib_1725700000)" in rendered
    assert "Status: COMPLETED | Concluded: 5.0m ago" in rendered
    assert "N=24 settled trades (15W / 9L, 62.5% WR, Net PnL=+$12.40)" in rendered
    assert "Prime / High-Conviction Assets (Empirically Proven): EURCHF_otc" in rendered
    assert "Hazard / Toxic Assets (Empirically Quarantined): AUDUSD_otc" in rendered
    assert "Favoured Market Regimes: RANGE_BOUND" in rendered
    assert "Operational Directive" in rendered


def test_build_pulse_user_msg_with_calibration_context():
    cfg = AutoGhostConfig()
    calib_ctx = {
        "calibration_id": "auto_ghost_calib_9999",
        "elapsed_minutes": 2.5,
        "settled_total": 20,
        "settled_wins": 14,
        "settled_losses": 6,
        "win_rate_pct": 70.0,
        "pnl": 15.00,
        "prime_assets": ["EURCHF_otc"],
        "hazard_assets": ["AUDUSD_otc"],
    }
    session_ctx = {
        "session_id": "ag_session_fresh",
        "settled_count": 0,
        "streak": 0,
        "session_wr": None,
        "utc_4h_block": 2,
        "utc_4h_label": "06:00-10:00",
    }

    msg = _build_pulse_user_msg(
        config=cfg,
        summaries_str="- EURCHF_otc: Price=0.9350, Regime=RANGE_BOUND",
        recent_trades_str="None",
        is_insufficient=True,
        session_trade_count=0,
        session_wins=0,
        session_losses=0,
        session_pnl=0.0,
        rolling_stats={"window": 20, "win_rate": None},
        trajectory_analytics={},
        lookback_seconds=180,
        session_context=session_ctx,
        calibration_context=calib_ctx,
    )

    # Both calibration intelligence and session context are present
    assert "### LATEST CALIBRATION INTELLIGENCE (auto_ghost_calib_9999)" in msg
    assert "### SESSION CONTEXT & PERFORMANCE LAYERS" in msg
    assert "Prime / High-Conviction Assets" in msg


def test_ai_pulse_system_msg_contains_calibration_grounding():
    sys_msg = _build_ai_pulse_system_msg()
    assert "5. Calibration Evidence Grounding:" in sys_msg
    assert "LATEST CALIBRATION INTELLIGENCE" in sys_msg


def test_calibration_service_get_latest_calibration_context():
    service = CalibrationService()
    # In empty state without calibration, returns None (or disk fallback if files exist)
    # Now simulate populated in-memory state
    service._calibration_id = "auto_ghost_calib_1725705555"
    service._state = "DONE"
    service._settled_wins = 16
    service._settled_losses = 8
    service._calibration_pnl = 14.50
    service._final_report = {
        "ended_at": unix_time() - 120,
        "calibrated_gates": {
            "prime_assets": ["EURCHF_otc", "NZDUSD_otc"],
            "recommended_blacklist": ["AUDUSD_otc"],
        },
    }
    service._settled_trades = [
        {"asset": "EURCHF_otc", "outcome": "win", "regime": "RANGE_BOUND"},
        {"asset": "AUDUSD_otc", "outcome": "loss", "regime": "TREND_REVERSAL"},
    ]

    ctx = service.get_latest_calibration_context()
    assert ctx is not None
    assert ctx["calibration_id"] == "auto_ghost_calib_1725705555"
    assert ctx["settled_total"] == 24
    assert ctx["settled_wins"] == 16
    assert ctx["settled_losses"] == 8
    assert ctx["win_rate_pct"] == pytest.approx(66.7, rel=0.1)
    assert ctx["pnl"] == 14.50
    assert "EURCHF_otc" in ctx["prime_assets"]
    assert "AUDUSD_otc" in ctx["hazard_assets"]
    assert ctx["elapsed_minutes"] == pytest.approx(2.0, abs=0.5)

