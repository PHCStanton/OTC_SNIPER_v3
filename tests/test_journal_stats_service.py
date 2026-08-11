"""Unit tests for JournalStatsService — OTC SNIPER v3."""

import json
import shutil
import tempfile
from pathlib import Path
import pytest

from app.backend.services.journal_stats_service import (
    JournalStatsService,
    _get_score_band,
    _get_z_band,
)


@pytest.fixture
def mock_env(tmp_path):
    data_dir = tmp_path / "data"
    ghost_sessions_dir = data_dir / "ghost_trades" / "sessions"
    ghost_stats_dir = data_dir / "ghost_trades" / "stats"
    ghost_sessions_dir.mkdir(parents=True, exist_ok=True)
    ghost_stats_dir.mkdir(parents=True, exist_ok=True)

    kb_dir = tmp_path / "reports" / "analysis" / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)
    kb_file = kb_dir / "condition_patterns.json"
    kb_file.write_text(json.dumps({"metadata": {"total_patterns": 0}, "patterns": []}), encoding="utf-8")

    priors_file = ghost_stats_dir / "bayesian_priors.json"
    priors_file.write_text(json.dumps({
        "total_wins": 10,
        "total_losses": 10,
        "total_trades": 20,
        "feature_counts": {
            "regime=RANGE_BOUND": {"win": 5, "loss": 5}
        }
    }), encoding="utf-8")

    # Create dummy session 1 with 4 trades
    s1 = ghost_sessions_dir / "session_1.jsonl"
    trades_s1 = [
        {
            "id": "t1", "session_id": "session_1", "asset": "EURUSD_otc", "outcome": "win", "profit": 18.4,
            "expiration_seconds": 60, "oteo_score": 88.0,
            "entry_context": {
                "regime_label": "RANGE_BOUND", "z_score": 0.2, "confidence": "HIGH",
                "market_context": {"atr": 0.0004, "tick_frequency": 120.0},
                "manipulation": {}
            }
        },
        {
            "id": "t2", "session_id": "session_1", "asset": "EURUSD_otc", "outcome": "win", "profit": 18.4,
            "expiration_seconds": 60, "oteo_score": 86.0,
            "entry_context": {
                "regime_label": "RANGE_BOUND", "z_score": 0.1, "confidence": "HIGH",
                "market_context": {"atr": 0.0003, "tick_frequency": 110.0},
                "manipulation": {}
            }
        },
        {
            "id": "t3", "session_id": "session_1", "asset": "GBPUSD_otc", "outcome": "loss", "profit": -20.0,
            "expiration_seconds": 120, "oteo_score": 78.0,
            "entry_context": {
                "regime_label": "CHOPPY", "z_score": -1.6, "confidence": "LOW",
                "market_context": {"atr": 0.0015, "tick_frequency": 60.0},
                "manipulation": {"Push & Snap": 0.85}
            }
        },
        {
            "id": "t4", "session_id": "session_1", "asset": "GBPUSD_otc", "outcome": "loss", "profit": -20.0,
            "expiration_seconds": 60, "oteo_score": 62.0,
            "entry_context": {
                "regime_label": "CHOPPY", "z_score": -0.8, "confidence": "MEDIUM",
                "market_context": {"atr": 0.0008, "tick_frequency": 70.0},
                "manipulation": {"Push & Snap": 0.90}
            }
        }
    ]
    with s1.open("w", encoding="utf-8") as f:
        for t in trades_s1:
            f.write(json.dumps(t) + "\n")

    class MockSettings:
        def __init__(self):
            self.data_dir = data_dir

    service = JournalStatsService(settings=MockSettings())
    service.kb_path = kb_file
    service.bayesian_priors_path = priors_file
    service.staged_updates_path = ghost_stats_dir / "staged_knowledge_updates.json"
    service._ensure_staging_file()

    return service, data_dir, kb_file, priors_file


def test_score_and_z_bands():
    assert _get_score_band(45) == "<50"
    assert _get_score_band(60) == "<65"
    assert _get_score_band(70) == "65-74"
    assert _get_score_band(80) == "75-84"
    assert _get_score_band(90) == "85-92"
    assert _get_score_band(95) == "93+"

    assert _get_z_band(-2.0) == "<-1.5"
    assert _get_z_band(-1.0) == "-1.5_to_-0.5"
    assert _get_z_band(0.0) == "-0.5_to_0.5"
    assert _get_z_band(1.0) == "0.5_to_1.5"
    assert _get_z_band(2.0) == ">1.5"
    assert _get_z_band(None) == "UNKNOWN"


def test_compute_journal_stats(mock_env):
    service, _, _, _ = mock_env
    stats = service.compute_journal_stats(session_id="session_1", kind="ghost")

    assert stats["total_trades"] == 4
    assert stats["wins"] == 2
    assert stats["losses"] == 2
    assert stats["win_rate"] == 50.0
    assert stats["total_profit"] == -3.20

    # Volatility checks
    vol_bands = {b["band"]: b for b in stats["volatility"]["bands"]}
    assert vol_bands["Optimal (0.0002-0.0006)"]["trades"] == 2
    assert vol_bands["Optimal (0.0002-0.0006)"]["win_rate"] == 100.0

    # Liquidity checks
    liq_bands = {b["band"]: b for b in stats["liquidity"]["bands"]}
    assert liq_bands["Balanced (80-150/min)"]["trades"] == 2
    assert liq_bands["Low (<80/min)"]["trades"] == 2

    # Manipulation checks
    manip_leaderboard = stats["manipulation"]["leaderboard"]
    gbp = next((a for a in manip_leaderboard if a["asset"] == "GBPUSD_otc"), None)
    assert gbp is not None
    assert gbp["manipulation_freq_pct"] == 100.0
    assert gbp["danger_level"] == "HIGH"
    assert gbp["dominant_manipulation_type"] == "Push & Snap"

    eur = next((a for a in manip_leaderboard if a["asset"] == "EURUSD_otc"), None)
    assert eur is not None
    assert eur["manipulation_freq_pct"] == 0.0
    assert eur["danger_level"] == "LOW"

    # Regimes ranking checks
    regimes_map = {r["regime"]: r for r in stats["regimes"]}
    assert regimes_map["RANGE_BOUND"]["win_rate"] == 100.0
    assert regimes_map["RANGE_BOUND"]["classification"] == "FAVOURED"
    assert regimes_map["CHOPPY"]["win_rate"] == 0.0
    assert regimes_map["CHOPPY"]["classification"] == "AVOID"

    # Expiries checks
    exp_map = {e["duration_seconds"]: e for e in stats["expiries"]["expiries"]}
    assert exp_map[60]["trades"] == 3
    assert exp_map[120]["trades"] == 1


def test_staging_and_transactional_commit(mock_env):
    service, _, kb_file, priors_file = mock_env

    # 1. Stage report
    staged = service.stage_session_report(session_id="session_1", kind="ghost", notes="Test batch")
    staged_id = staged["staged_id"]
    assert staged["status"] == "PENDING_REVIEW"

    reports = service.get_staged_reports()
    assert len(reports) == 1
    assert reports[0]["staged_id"] == staged_id

    # 2. Commit staged report with backup creation
    res = service.commit_staged_to_knowledge_base(staged_id=staged_id, commit_bayesian=True, commit_kb=True)
    assert res["success"] is True
    assert res["status"] == "COMMITTED"
    assert len(res["backups"]) >= 1

    # Verify Bayesian priors were updated
    priors_data = json.loads(priors_file.read_text(encoding="utf-8"))
    assert priors_data["total_wins"] == 12  # 10 initial + 2 new
    assert priors_data["total_losses"] == 12 # 10 initial + 2 new
    assert priors_data["total_trades"] == 24
    assert priors_data["feature_counts"]["regime=RANGE_BOUND"]["win"] == 7  # 5 + 2

    # Verify Knowledge Base was updated
    kb_data = json.loads(kb_file.read_text(encoding="utf-8"))
    assert len(kb_data["patterns"]) >= 1
