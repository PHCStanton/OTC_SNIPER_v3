"""Phase 4 — KB health audit, recency decay, staging-only backfill, warm-start."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from shared.bayesian_prior_store import (
    DEFAULT_RECENCY_HALF_LIFE_DAYS,
    apply_trade_outcomes,
    empty_priors,
    recency_weight,
)
from shared.utc_time_blocks import utc_4h_block, utc_4h_label
from app.backend.services.kb_health import (
    KbHealthError,
    _parse_generated_utc,
    audit_kb_health,
    stage_historical_backfill,
)
from app.backend.services.journal_stats_service import JournalStatsService


SECONDS_PER_DAY = 86400.0


def _unix(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp()


def test_parse_generated_utc_accepts_canonical_kb_format():
    parsed = _parse_generated_utc("2026-06-13 04:28:57 UTC")
    assert parsed is not None
    assert parsed == datetime(2026, 6, 13, 4, 28, 57, tzinfo=timezone.utc)
    iso = _parse_generated_utc("2026-06-13T04:28:57Z")
    assert iso is not None
    assert iso.year == 2026 and iso.month == 6 and iso.day == 13


def test_recency_weight_90_vs_10_day_contract():
    """90-day-old trade contributes <50% of a 10-day-old trade at default half-life."""
    w90 = recency_weight(90.0, DEFAULT_RECENCY_HALF_LIFE_DAYS)
    w10 = recency_weight(10.0, DEFAULT_RECENCY_HALF_LIFE_DAYS)
    assert w90 / w10 < 0.5
    assert DEFAULT_RECENCY_HALF_LIFE_DAYS == 21.0


def test_apply_trade_outcomes_recency_weights_old_less_than_half_recent():
    as_of = _unix(2026, 8, 30, 12)
    old = as_of - 90 * SECONDS_PER_DAY
    recent = as_of - 10 * SECONDS_PER_DAY
    priors = apply_trade_outcomes(
        empty_priors(),
        [
            {"won": True, "features": ["utc_4h_block=5"], "entry_time": old},
            {"won": True, "features": ["utc_4h_block=5"], "entry_time": recent},
        ],
        as_of_unix=as_of,
        half_life_days=DEFAULT_RECENCY_HALF_LIFE_DAYS,
    )
    rec = priors["recency"]
    w90 = recency_weight(90.0)
    w10 = recency_weight(10.0)
    assert rec["total_weighted_wins"] == pytest.approx(w90 + w10, rel=1e-6)
    assert w90 < 0.5 * w10
    # Unweighted integers still count both trades equally.
    assert priors["total_wins"] == 2


def test_runtime_update_inherits_recency_decay():
    t0 = 1_700_000_000.0
    seeded = apply_trade_outcomes(
        empty_priors(),
        [{"won": True, "features": ["regime=RANGE_BOUND"], "entry_time": t0}],
        as_of_unix=t0,
        half_life_days=21.0,
    )
    later = apply_trade_outcomes(
        seeded,
        [{"won": False, "features": ["regime=RANGE_BOUND"]}],
        as_of_unix=t0 + 21.0 * SECONDS_PER_DAY,
        half_life_days=21.0,
    )
    rec = later["recency"]
    assert rec["total_weighted_wins"] == pytest.approx(0.5, rel=1e-6)
    assert rec["total_weighted_losses"] == pytest.approx(1.0, rel=1e-6)


def test_utc_4h_labels_match_plan_pockets():
    assert utc_4h_label(utc_4h_block(_unix(2026, 1, 1, 18, 0))) == "18:00-22:00"
    assert utc_4h_label(utc_4h_block(_unix(2026, 1, 1, 22, 0))) == "22:00-02:00"


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_backfill_is_staging_only_and_emits_warm_start(tmp_path):
    sessions = tmp_path / "sessions"
    kb_path = tmp_path / "condition_patterns.json"
    priors_60 = tmp_path / "bayesian_priors.json"
    priors_300 = tmp_path / "bayesian_priors_300s.json"
    staged = tmp_path / "stats" / "staged_knowledge_updates.json"
    warm = tmp_path / "stats" / "warm_start_baseline.json"

    kb_path.write_text(json.dumps({"metadata": {"total_patterns": 0, "generated_utc": "2026-06-13 04:28:57 UTC"}, "patterns": []}), encoding="utf-8")
    priors_60.write_text(json.dumps({
        "total_wins": 100, "total_losses": 80, "total_trades": 180, "feature_counts": {}
    }), encoding="utf-8")
    priors_300.write_text(json.dumps({
        "total_wins": 10, "total_losses": 10, "total_trades": 20, "feature_counts": {}
    }), encoding="utf-8")

    as_of = _unix(2026, 8, 30, 19)  # 19:00 UTC → block 5
    trades = []
    for i in range(12):
        trades.append({
            "id": f"t{i}",
            "session_id": "s1",
            "asset": "EURUSD_otc",
            "direction": "CALL",
            "outcome": "win" if i % 3 else "loss",
            "profit": 1.0 if i % 3 else -1.0,
            "expiration_seconds": 60,
            "oteo_score": 88.0,
            "strategy_level": "level3",
            "entry_time": as_of - (i * SECONDS_PER_DAY),
            "entry_context": {"regime_label": "RANGE_BOUND", "z_score": 0.2, "confidence": "HIGH"},
        })
    _write_jsonl(sessions / "s1.jsonl", trades)

    kb_before = kb_path.read_text(encoding="utf-8")
    priors_before = priors_60.read_text(encoding="utf-8")

    result = stage_historical_backfill(
        sessions_dir=sessions,
        staged_path=staged,
        warm_start_path=warm,
        kb_path=kb_path,
        priors_60_path=priors_60,
        priors_300_path=priors_300,
        lookback_days=56,
        half_life_days=21.0,
        as_of_unix=as_of,
        min_sample_size=5,
    )

    assert result["master_kb_written"] is False
    assert result["master_priors_written"] is False
    assert kb_path.read_text(encoding="utf-8") == kb_before
    assert priors_60.read_text(encoding="utf-8") == priors_before
    assert staged.exists()
    staged_data = json.loads(staged.read_text(encoding="utf-8"))
    report = staged_data["staged_reports"][0]
    assert report["source"] == "kb_backfill"
    assert report["status"] == "PENDING_REVIEW"
    assert report["bayesian_deltas"]["total_wins_delta"] == 0
    assert report["bayesian_deltas"]["recency"] is not None
    assert any(p.get("utc_4h_block") is not None for p in report["candidate_patterns"])
    assert warm.exists()
    baseline = json.loads(warm.read_text(encoding="utf-8"))
    assert baseline["expected_wr"] is not None
    assert "5" in baseline["by_utc_4h_block"]
    assert baseline["by_utc_4h_block"]["5"]["label"] == "18:00-22:00"
    assert result["warm_start"]["source"] == "kb_backfill"


def test_audit_horizon_isolation_fails_on_shared_file(tmp_path):
    shared = tmp_path / "bayesian_priors.json"
    shared.write_text(json.dumps({
        "total_wins": 1, "total_losses": 1, "total_trades": 2, "feature_counts": {}
    }), encoding="utf-8")
    kb = tmp_path / "condition_patterns.json"
    kb.write_text(json.dumps({"metadata": {}, "patterns": []}), encoding="utf-8")
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    audit = audit_kb_health(
        kb_path=kb,
        priors_60_path=shared,
        priors_300_path=shared,
        sessions_dir=sessions,
    )
    assert audit["priors"]["horizon_isolation"]["ok"] is False
    assert audit["priors"]["horizon_isolation"]["issues"]


def test_backfill_refuses_staged_path_colliding_with_kb_before_write(tmp_path):
    kb_path = tmp_path / "condition_patterns.json"
    original = json.dumps({"metadata": {"total_patterns": 99}, "patterns": [{"keep": True}]})
    kb_path.write_text(original, encoding="utf-8")
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    with pytest.raises(KbHealthError, match="collides with master KB"):
        stage_historical_backfill(
            sessions_dir=sessions,
            staged_path=kb_path,
            warm_start_path=tmp_path / "warm.json",
            kb_path=kb_path,
            priors_60_path=tmp_path / "p60.json",
            priors_300_path=tmp_path / "p300.json",
            lookback_days=56,
        )
    assert kb_path.read_text(encoding="utf-8") == original
    assert not (tmp_path / "warm.json").exists()


def test_backfill_refuses_empty_window(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    with pytest.raises(KbHealthError, match="No settled trades"):
        stage_historical_backfill(
            sessions_dir=sessions,
            staged_path=tmp_path / "staged.json",
            warm_start_path=tmp_path / "warm.json",
            kb_path=tmp_path / "kb.json",
            priors_60_path=tmp_path / "p60.json",
            priors_300_path=tmp_path / "p300.json",
            lookback_days=56,
        )


def test_journal_extracts_utc4h_pattern_keys(tmp_path):
    data_dir = tmp_path / "data"
    sessions_dir = data_dir / "ghost_trades" / "sessions"
    stats_dir = data_dir / "ghost_trades" / "stats"
    sessions_dir.mkdir(parents=True)
    stats_dir.mkdir(parents=True)
    kb_dir = tmp_path / "reports" / "analysis" / "knowledge_base"
    kb_dir.mkdir(parents=True)
    kb_file = kb_dir / "condition_patterns.json"
    kb_file.write_text(json.dumps({"metadata": {"total_patterns": 0}, "patterns": []}), encoding="utf-8")
    priors_file = stats_dir / "bayesian_priors.json"
    priors_file.write_text(json.dumps({
        "total_wins": 0, "total_losses": 0, "total_trades": 0, "feature_counts": {}
    }), encoding="utf-8")

    entry = _unix(2026, 8, 30, 19, 10)
    trades = [{
        "id": "t1", "session_id": "s1", "asset": "EURUSD_otc", "outcome": "win",
        "profit": 1.0, "expiration_seconds": 60, "oteo_score": 88.0,
        "direction": "CALL", "strategy_level": "level3",
        "entry_time": entry,
        "entry_context": {"regime_label": "RANGE_BOUND", "z_score": 0.1, "confidence": "HIGH"},
    }]
    _write_jsonl(sessions_dir / "s1.jsonl", trades)

    class MockSettings:
        def __init__(self):
            self.data_dir = data_dir

    service = JournalStatsService(settings=MockSettings())
    service.kb_path = kb_file
    service.bayesian_priors_path = priors_file
    service.staged_updates_path = stats_dir / "staged_knowledge_updates.json"
    service._ensure_staging_file()

    stats = service.compute_journal_stats(session_id="s1", kind="ghost")
    keys = {p["pattern_key"] for p in stats["candidate_patterns"]}
    assert any("utc4h:5" in k for k in keys)
    assert any(p.get("utc_4h_label") == "18:00-22:00" for p in stats["candidate_patterns"])
    assert "utc_4h_block=5" in stats["bayesian_deltas"]["feature_deltas"]


def test_commit_recency_overlay_does_not_double_count_integers(tmp_path):
    data_dir = tmp_path / "data"
    sessions_dir = data_dir / "ghost_trades" / "sessions"
    stats_dir = data_dir / "ghost_trades" / "stats"
    sessions_dir.mkdir(parents=True)
    stats_dir.mkdir(parents=True)
    kb_file = tmp_path / "condition_patterns.json"
    kb_file.write_text(json.dumps({"metadata": {"total_patterns": 0}, "patterns": []}), encoding="utf-8")
    priors_file = stats_dir / "bayesian_priors.json"
    priors_file.write_text(json.dumps({
        "total_wins": 10, "total_losses": 10, "total_trades": 20, "feature_counts": {}
    }), encoding="utf-8")
    priors_300 = stats_dir / "bayesian_priors_300s.json"
    priors_300.write_text(json.dumps({
        "total_wins": 3, "total_losses": 2, "total_trades": 5, "feature_counts": {}
    }), encoding="utf-8")

    class MockSettings:
        def __init__(self):
            self.data_dir = data_dir

    service = JournalStatsService(settings=MockSettings())
    service.kb_path = kb_file
    service.bayesian_priors_path = priors_file
    service.staged_updates_path = stats_dir / "staged_knowledge_updates.json"
    service._ensure_staging_file()

    staged = {
        "staged_id": "staged_kb_backfill_1",
        "status": "PENDING_REVIEW",
        "source": "kb_backfill",
        "commit_mode": "recency_overlay_and_patterns",
        "candidate_patterns": [{
            "pattern_key": "EURUSD_otc|level3|85-92|RANGE_BOUND|CALL|utc4h:5",
            "asset": "EURUSD_otc",
            "strategy_level": "level3",
            "oteo_score_band": "85-92",
            "regime_label": "RANGE_BOUND",
            "direction": "CALL",
            "utc_4h_block": 5,
            "utc_4h_label": "18:00-22:00",
            "sample_size": 12,
            "win_rate_pct": 66.7,
            "expectancy": 1.0,
            "net_profit": 12.0,
            "confidence_tier": "MEDIUM",
            "suppression_candidate": False,
            "boost_candidate": True,
        }],
        "bayesian_deltas": {
            "total_wins_delta": 0,
            "total_losses_delta": 0,
            "feature_deltas": {},
            "commit_mode": "recency_overlay_and_patterns",
            "recency": {
                "half_life_days": 21.0,
                "as_of_unix": 1.0,
                "total_weighted_wins": 4.2,
                "total_weighted_losses": 2.1,
                "feature_counts": {"utc_4h_block=5": {"win": 4.2, "loss": 2.1}},
            },
            "recency_300s": {
                "half_life_days": 21.0,
                "as_of_unix": 1.0,
                "total_weighted_wins": 1.5,
                "total_weighted_losses": 0.5,
                "feature_counts": {"utc_4h_block=5": {"win": 1.5, "loss": 0.5}},
            },
        },
    }
    service.staged_updates_path.write_text(json.dumps({"staged_reports": [staged]}), encoding="utf-8")
    res = service.commit_staged_to_knowledge_base(
        staged_id="staged_kb_backfill_1", commit_bayesian=True, commit_kb=True, min_sample_size=5,
    )
    assert res["success"] is True
    priors = json.loads(priors_file.read_text(encoding="utf-8"))
    assert priors["total_wins"] == 10
    assert priors["total_losses"] == 10
    assert priors["recency"]["total_weighted_wins"] == pytest.approx(4.2)
    priors_300_data = json.loads(priors_300.read_text(encoding="utf-8"))
    assert priors_300_data["total_wins"] == 3
    assert priors_300_data["total_losses"] == 2
    assert priors_300_data["recency"]["total_weighted_wins"] == pytest.approx(1.5)
    kb = json.loads(kb_file.read_text(encoding="utf-8"))
    assert kb["patterns"][0]["utc_4h_block"] == 5
    assert kb["metadata"]["generated_utc"].endswith(" UTC")
    assert _parse_generated_utc(kb["metadata"]["generated_utc"]) is not None
