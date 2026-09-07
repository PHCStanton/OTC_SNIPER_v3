"""Session-First Learning contract tests (feat/ai_kb, 2026-09-04).

Verifies the session tracker, the 3-layer effective WR engine, and the tiered
Category A mutation guardrails:

- test_tracker_ignores_voids_and_calib_sessions   (Step 1 isolation contract)
- test_effective_wr_weight_transitions            (Step 2 matrix + renormalization)
- test_layer2_same_day_and_horizon_isolation      (Layer 2 guardrails)
- test_bayesian_floor_auto_bump_on_3_loss_streak  (Step 4 Category A.1)
- test_session_regime_veto_isolated_from_allowed_regimes (Step 4 Category A.2)
- test_snapshot_and_policy_directives             (Step 3 prompt contract)
- test_expansion_and_regime_pause_directives      (Step 3.5 deterministic rules)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from app.backend.services.auto_ghost import AutoGhostConfig, AutoGhostService
from app.backend.services.session_tracker import (
    CALIB_SESSION_PREFIX,
    SessionPerformanceTracker,
    SessionSnapshot,
    effective_wr_weights,
)


class _StubTradeService:
    """Minimal trade-service stub for AutoGhostService construction."""

    def __init__(self):
        self.executed = []

    def _get_market_context(self, asset: str) -> dict:
        return {}

    def _latest_logged_price(self, asset: str):
        return None

    async def execute_trade(self, broker, request):
        self.executed.append(request)
        return {"success": True, "message": "trade executed"}


def _make_service(**config_kwargs) -> AutoGhostService:
    return AutoGhostService(_StubTradeService(), config=AutoGhostConfig(**config_kwargs))


def _mint_live_session(service: AutoGhostService) -> str:
    """Enable Auto-Ghost so a live (non-calibration) session id is minted."""
    service.update_config(enabled=True)
    session_id = service._session_id
    assert session_id and not session_id.startswith(CALIB_SESSION_PREFIX)
    return session_id


# ---------------------------------------------------------------------------
# 1. Void filtering + calibration session isolation
# ---------------------------------------------------------------------------

def test_tracker_ignores_voids_and_calib_sessions():
    tracker = SessionPerformanceTracker()
    tracker.ensure_session("auto_ghost_1000")
    tracker.record_settlement(outcome="win", regime_label="RANGE_BOUND", horizon=60, session_id="auto_ghost_1000")
    tracker.record_settlement(outcome="void", regime_label="RANGE_BOUND", horizon=60, session_id="auto_ghost_1000")
    tracker.record_settlement(outcome="loss", regime_label="RANGE_BOUND", horizon=60, session_id="auto_ghost_1000")
    tracker.record_settlement(outcome="void", regime_label="RANGE_BOUND", horizon=60, session_id="auto_ghost_1000")
    assert tracker.settled_count == 2
    assert tracker.last_10_settled == ["win", "loss"]
    assert tracker.current_streak == -1  # void did not break or reset the streak
    assert tracker.rolling_session_wr == pytest.approx(0.5)

    # Calibration sessions never record into the live tracker.
    calib_tracker = SessionPerformanceTracker()
    calib_tracker.record_settlement(outcome="loss", session_id=f"{CALIB_SESSION_PREFIX}999")
    assert calib_tracker.settled_count == 0
    assert calib_tracker.current_streak == 0

    # Service-level: calibration mode never pollutes the live tracker.
    service = _make_service()
    service.set_calibration_mode(True)
    for i in range(5):
        service.report_outcome(
            trade_id=f"c{i}", outcome="loss", profit=-1.0,
            entry_context={"regime_label": "RANGE_BOUND", "expiration_seconds": 60},
        )
    assert service._session_id.startswith(CALIB_SESSION_PREFIX)
    assert service.session_tracker.settled_count == 0
    assert not service._session_vetoed_regimes  # calibration losses never trigger vetoes


# ---------------------------------------------------------------------------
# 2. Effective WR weight matrix + renormalization rule
# ---------------------------------------------------------------------------

def test_effective_wr_weight_transitions():
    assert effective_wr_weights(5) == (0.40, 0.30, 0.30)
    assert effective_wr_weights(9) == (0.40, 0.30, 0.30)
    assert effective_wr_weights(10) == (0.50, 0.25, 0.25)
    assert effective_wr_weights(15) == (0.50, 0.25, 0.25)
    assert effective_wr_weights(19) == (0.50, 0.25, 0.25)
    assert effective_wr_weights(20) == (0.60, 0.20, 0.20)
    assert effective_wr_weights(25) == (0.60, 0.20, 0.20)

    # N=5 session (4W/1L), Layer 2 absent, Layer 3 stubbed:
    # renormalized weights = 0.40/0.70 (session) + 0.30/0.70 (kb).
    tracker = SessionPerformanceTracker()
    tracker.ensure_session("auto_ghost_1")
    for _ in range(4):
        tracker.record_settlement(outcome="win", regime_label="RANGE_BOUND", horizon=60, session_id="auto_ghost_1")
    tracker.record_settlement(outcome="loss", regime_label="RANGE_BOUND", horizon=60, session_id="auto_ghost_1")
    tracker.layer3_kb_wr = lambda **kwargs: 0.58  # stub Layer 3 (58% book WR)
    result = tracker.effective_win_rate(regime_label="RANGE_BOUND", horizon=60)
    assert result["renormalized"] is True
    assert result["missing_layers"] == ["recent"]
    assert abs(sum(result["weights"].values()) - 1.0) < 1e-9
    assert result["weights"]["session"] == pytest.approx(0.40 / 0.70)
    assert result["weights"]["kb"] == pytest.approx(0.30 / 0.70)
    expected = (0.8 * (0.40 / 0.70)) + (0.58 * (0.30 / 0.70))
    assert result["effective_wr"] == pytest.approx(expected)

    # All three layers present -> exact spec weights, no renormalization.
    tracker2 = SessionPerformanceTracker()
    tracker2.ensure_session("auto_ghost_a")
    tracker2.record_settlement(outcome="win", horizon=60, session_id="auto_ghost_a")
    assert tracker2.ensure_session("auto_ghost_b") is True  # archives session a (today)
    tracker2.record_settlement(outcome="win", horizon=60, session_id="auto_ghost_b")
    tracker2.layer3_kb_wr = lambda **kwargs: 0.55
    result2 = tracker2.effective_win_rate(regime_label="RANGE_BOUND", horizon=60)
    assert result2["renormalized"] is False
    assert result2["weights"] == {"session": 0.40, "recent": 0.30, "kb": 0.30}
    assert result2["effective_wr"] == pytest.approx(0.4 * 1.0 + 0.3 * 1.0 + 0.3 * 0.55)

    # No data anywhere -> None; NEVER a hallucinated default 50.0%.
    empty = SessionPerformanceTracker()
    empty.ensure_session("auto_ghost_x")
    empty.layer3_kb_wr = lambda **kwargs: None
    res3 = empty.effective_win_rate(regime_label=None)
    assert res3["effective_wr"] is None
    assert set(res3["missing_layers"]) == {"session", "recent", "kb"}


def test_layer2_same_day_and_horizon_isolation():
    tracker = SessionPerformanceTracker()
    tracker.ensure_session("auto_ghost_a", now=time.time())
    for _ in range(3):
        tracker.record_settlement(outcome="win", horizon=60, session_id="auto_ghost_a")
    tracker.record_settlement(outcome="loss", horizon=300, session_id="auto_ghost_a")
    tracker.ensure_session("auto_ghost_b")  # archives session a (today)

    # Same UTC day + same horizon (60s): 3 wins from archived session a.
    assert tracker.layer2_recent_wr(horizon=60) == pytest.approx(1.0)
    # Horizon isolation: 300s layer sees only the single loss.
    assert tracker.layer2_recent_wr(horizon=300) == pytest.approx(0.0)
    # Overall layer (no horizon): 3W/1L.
    assert tracker.layer2_recent_wr() == pytest.approx(0.75)

    # Yesterday's sessions are excluded (same-UTC-calendar-day rule).
    yesterday = time.time() - 86400
    tracker._history.append(
        SessionSnapshot(
            session_id="auto_ghost_old",
            ended_at=yesterday,
            utc_date=datetime.fromtimestamp(yesterday, tz=timezone.utc).strftime("%Y-%m-%d"),
            wins_by_horizon={60: 10},
            losses_by_horizon={60: 0},
        )
    )
    # Still 3W/1L — yesterday's 10W session contributes nothing.
    assert tracker.layer2_recent_wr() == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 3. Category A.1 — Bayesian floor auto-bump on 3-loss cold streak
# ---------------------------------------------------------------------------

def test_bayesian_floor_auto_bump_on_3_loss_streak():
    service = _make_service(bayesian_filter_enabled=True, bayesian_min_probability=0.535)
    _mint_live_session(service)
    for i in range(3):
        service.report_outcome(
            trade_id=f"t{i}", outcome="loss", profit=-1.0, asset=None, expiration_seconds=60,
        )
    assert service.config.bayesian_min_probability == pytest.approx(0.555)
    audits = [a for a in service._session_audit_log if a["type"] == "bayesian_floor_adaptation"]
    assert len(audits) == 1
    assert audits[0]["old"] == pytest.approx(0.535)
    assert audits[0]["new"] == pytest.approx(0.555)
    assert audits[0]["streak"] == -3

    # A 4th loss does NOT double-bump (escalation is per 3-loss step: -3, -6, ...).
    service.report_outcome(trade_id="t3", outcome="loss", profit=-1.0, asset=None, expiration_seconds=60)
    assert service.config.bayesian_min_probability == pytest.approx(0.555)

    # Clamped at the hard 0.90 ceiling (float fraction — never percent form).
    service.update_config(bayesian_min_probability=0.895)
    for i in range(4, 7):
        service.report_outcome(trade_id=f"t{i}", outcome="loss", profit=-1.0, asset=None, expiration_seconds=60)
    assert service.config.bayesian_min_probability == pytest.approx(0.90)


# ---------------------------------------------------------------------------
# 4. Category A.2 — session-local regime veto isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_regime_veto_isolated_from_allowed_regimes():
    service = _make_service()
    _mint_live_session(service)
    service.CONFIRMATION_TICKS = 1
    for i in range(5):
        service.report_outcome(
            trade_id=f"v{i}", outcome="loss", profit=-1.0, asset=None,
            entry_context={"regime_label": "RANGE_BOUND", "expiration_seconds": 60},
        )
    assert "RANGE_BOUND" in service._session_vetoed_regimes
    # allowed_regimes config NEVER touched — especially never set to [].
    assert service.config.allowed_regimes is None
    audits = [a for a in service._session_audit_log if a["type"] == "session_regime_veto"]
    assert len(audits) == 1 and audits[0]["regime"] == "RANGE_BOUND"

    # Vetoed regime -> rejected in-gate with reason session_regime_veto.
    vetoed_oteo = {"recommended": "CALL", "actionable": True, "oteo_score": 80.0, "regime_label": "RANGE_BOUND"}
    res = await service.consider_signal(
        asset="EURUSD", price=1.1, timestamp=1000.0,
        oteo_result=vetoed_oteo, manipulation={}, payout_pct=100.0,
    )
    assert res is None
    assert service._reject_counts.get("session_regime_veto", 0) >= 1

    # Non-vetoed regime still trades normally.
    ok_oteo = {"recommended": "PUT", "actionable": True, "oteo_score": 80.0, "regime_label": "TREND_PULLBACK"}
    res2 = await service.consider_signal(
        asset="GBPUSD", price=1.2, timestamp=1001.0,
        oteo_result=ok_oteo, manipulation={}, payout_pct=100.0,
    )
    assert res2 is not None and res2["success"] is True

    # Veto dissolves when the session resets (new _session_id).
    service.set_calibration_mode(True)
    service.set_calibration_mode(False)
    assert service._session_vetoed_regimes == set()
    assert service.config.allowed_regimes is None


# ---------------------------------------------------------------------------
# 5. Snapshot + deterministic policy directives (Step 3 prompt contract)
# ---------------------------------------------------------------------------

def test_snapshot_and_policy_directives():
    service = _make_service(bayesian_filter_enabled=True, bayesian_min_probability=0.535)
    _mint_live_session(service)
    for i in range(3):
        service.report_outcome(
            trade_id=f"d{i}", outcome="loss", profit=-1.0, asset=None,
            entry_context={"regime_label": "BREAKOUT", "expiration_seconds": 60},
        )
    snap = service.session_performance_snapshot()
    assert snap["settled_count"] == 3
    assert snap["streak"] == -3
    assert snap["session_wr"] == pytest.approx(0.0)
    assert snap["vetoed_regimes"] == []  # 0/5 veto threshold not reached at N=3
    assert any(d.startswith("COLD STREAK ACTIVE") for d in snap["policy_directives"])
    assert snap["effective"]["renormalized"] is True
    assert "utc_4h_block" in snap and "per_regime" in snap

    # Prompt renderer contract (Step 3 section).
    from app.backend.services.streaming import _build_pulse_user_msg, _render_session_context_section

    section = _render_session_context_section(snap)
    assert section.startswith("### SESSION CONTEXT & PERFORMANCE LAYERS")
    assert "Effective 3-Layer Win Rate" in section
    assert "DETERMINISTIC POLICY DIRECTIVES" in section
    assert "COLD STREAK ACTIVE" in section
    assert "Active Session Vetoes" in section
    assert _render_session_context_section(None) == ""
    assert _render_session_context_section({}) == ""

    # Section injects into the full pulse prompt without breaking existing sections.
    msg = _build_pulse_user_msg(
        config=AutoGhostConfig(),
        summaries_str="- EURUSD_otc: ...",
        recent_trades_str="- Trade 1: ...",
        is_insufficient=True,
        session_trade_count=3,
        session_wins=0,
        session_losses=3,
        session_pnl=-3.0,
        rolling_stats={"window": 20, "wins": 0, "losses": 0, "win_rate": None},
        trajectory_analytics={},
        lookback_seconds=120,
        session_context=snap,
    )
    assert "### SESSION CONTEXT & PERFORMANCE LAYERS" in msg
    assert "Active Session Performance:" in msg  # existing Phase 0 contract intact

    # Backward compatible: omitted session_context keeps the prompt unchanged.
    msg_no_ctx = _build_pulse_user_msg(
        config=AutoGhostConfig(),
        summaries_str="s",
        recent_trades_str="r",
        is_insufficient=False,
        session_trade_count=0,
        session_wins=0,
        session_losses=0,
        session_pnl=0.0,
        rolling_stats={"window": 20, "wins": 0, "losses": 0, "win_rate": None},
        trajectory_analytics={},
        lookback_seconds=120,
    )
    assert "### SESSION CONTEXT" not in msg_no_ctx


def test_expansion_and_regime_pause_directives():
    # Expansion: effective WR > 65% with N >= 10.
    tracker = SessionPerformanceTracker()
    tracker.ensure_session("auto_ghost_e")
    for i in range(10):
        outcome = "win" if i < 9 else "loss"
        tracker.record_settlement(
            outcome=outcome, regime_label="RANGE_BOUND", horizon=60, session_id="auto_ghost_e",
        )
    tracker.layer3_kb_wr = lambda **kwargs: 0.60
    tracker.layer2_recent_wr = lambda **kwargs: 0.70
    eff = tracker.effective_win_rate(regime_label="RANGE_BOUND")
    assert eff["effective_wr"] > 0.65 and eff["n_session"] >= 10
    directives = AutoGhostService._session_policy_directives(
        eff, tracker.per_regime_stats, tracker.current_streak,
    )
    assert any(d.startswith("EXPANSION PERMITTED") for d in directives)

    # Regime pause: N >= 5 with WR < 35%.
    tracker_p = SessionPerformanceTracker()
    tracker_p.ensure_session("auto_ghost_p")
    for _ in range(5):
        tracker_p.record_settlement(
            outcome="loss", regime_label="BREAKOUT", horizon=60, session_id="auto_ghost_p",
        )
    directives_p = AutoGhostService._session_policy_directives(
        {"effective_wr": None, "n_session": 5}, tracker_p.per_regime_stats, -5,
    )
    assert any(d.startswith("REGIME PAUSE ADVISED") for d in directives_p)
