"""
Phase 4 — Cross-process Bayesian prior transactions.

Verification IDs: T4.1, T4.2 (remediation plan 2026-08-03).
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.bayesian_prior_store import (
    BayesianPriorStore,
    PriorStoreCorruptError,
    PriorStoreLockTimeout,
    PriorStorePersistenceError,
    PriorStoreValidationError,
    apply_trade_outcomes,
    empty_priors,
    normalize_priors,
    validate_trade_outcome,
)
from data_agent.src.bayesian.prior_updater import BayesianPriorUpdater
from app.backend.services.extensions.bayesian_signal_filter import BayesianSignalFilter

# Multiprocess worker lives in a tiny module that does not import data_agent
# (Windows spawn re-imports the test module otherwise and fails conftest aliasing).
from tests._prior_store_mp_worker import mp_prior_store_worker


def _seed(path: Path, wins: int = 1, losses: int = 0) -> None:
    data = {
        "total_wins": wins,
        "total_losses": losses,
        "total_trades": wins + losses,
        "feature_counts": {"seed=1": {"win": wins, "loss": losses}},
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_normalize_rejects_impossible_totals():
    with pytest.raises(PriorStoreValidationError, match="impossible totals"):
        normalize_priors(
            {
                "total_wins": 2,
                "total_losses": 1,
                "total_trades": 9,
                "feature_counts": {},
            }
        )


def test_validate_trade_rejects_string_won():
    with pytest.raises(PriorStoreValidationError, match="boolean"):
        validate_trade_outcome({"won": "false", "features": []})
    with pytest.raises(PriorStoreValidationError, match="boolean"):
        validate_trade_outcome({"won": 1, "features": []})


def test_validate_trade_rejects_bad_features():
    with pytest.raises(PriorStoreValidationError):
        validate_trade_outcome({"won": True, "features": [""]})
    with pytest.raises(PriorStoreValidationError):
        validate_trade_outcome({"won": True, "features": [123]})


def test_lock_timeout_returns_explicit_error(tmp_path):
    path = tmp_path / "priors.json"
    store = BayesianPriorStore(path, lock_timeout_sec=0.3)
    store.update_from_trades([{"won": True, "features": ["a=1"]}])

    held = threading.Event()
    release = threading.Event()

    def holder():
        with store._exclusive_lock():
            held.set()
            release.wait(timeout=5.0)

    t = threading.Thread(target=holder)
    t.start()
    assert held.wait(timeout=2.0)

    contender = BayesianPriorStore(path, lock_timeout_sec=0.25)
    with pytest.raises(PriorStoreLockTimeout):
        contender.update_from_trades([{"won": False, "features": ["b=1"]}])

    release.set()
    t.join(timeout=2.0)


def test_forced_write_failure_preserves_previous_valid_file(tmp_path):
    path = tmp_path / "priors.json"
    _seed(path, wins=7, losses=3)
    before = path.read_text(encoding="utf-8")
    store = BayesianPriorStore(path)

    with patch.object(
        store,
        "_write_atomic_under_lock",
        side_effect=PriorStorePersistenceError("injected replace failure"),
    ):
        with pytest.raises(PriorStorePersistenceError):
            store.update_from_trades([{"won": True, "features": ["x=1"]}])

    assert path.read_text(encoding="utf-8") == before
    data = json.loads(before)
    assert data["total_wins"] == 7
    assert data["total_losses"] == 3


def test_corrupt_file_not_silently_replaced(tmp_path):
    path = tmp_path / "priors.json"
    path.write_text("{not-json", encoding="utf-8")
    store = BayesianPriorStore(path)
    with pytest.raises(PriorStoreCorruptError):
        store.read()
    # File still corrupt on disk
    assert path.read_text(encoding="utf-8") == "{not-json"


def test_updater_delegates_to_store(tmp_path):
    priors = tmp_path / "bayesian_priors.json"
    updater = BayesianPriorUpdater(priors_json_path=str(priors))
    updated = updater.update_priors_from_trades(
        [
            {"won": True, "features": ["oteo_band=85-92"]},
            {"won": False, "features": ["oteo_band=85-92"]},
        ]
    )
    assert updated["total_wins"] == 1
    assert updated["total_losses"] == 1
    assert updated["total_trades"] == 2
    saved = json.loads(priors.read_text(encoding="utf-8"))
    assert saved["total_trades"] == 2


def test_signal_filter_memory_matches_committed_file(tmp_path):
    """App in-memory counters match committed file after every update."""
    priors = tmp_path / "bayesian_priors.json"
    filt = BayesianSignalFilter(
        {"enabled": True, "min_win_probability": 0.55, "priors_file": priors}
    )
    base = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
    }
    for outcome in ("win", "win", "loss"):
        filt.on_trade_outcome({**base, "outcome": outcome})
        disk = json.loads(priors.read_text(encoding="utf-8"))
        assert filt.total_wins == disk["total_wins"]
        assert filt.total_losses == disk["total_losses"]
        assert filt.total_wins + filt.total_losses == disk["total_trades"]


def test_signal_filter_does_not_mutate_before_commit(tmp_path):
    """On persistence failure, in-memory state is unchanged."""
    priors = tmp_path / "bayesian_priors.json"
    _seed(priors, wins=2, losses=1)
    filt = BayesianSignalFilter(
        {"enabled": True, "min_win_probability": 0.55, "priors_file": priors}
    )
    assert filt.total_wins == 2
    with patch.object(
        filt._prior_store,
        "update_from_trades",
        side_effect=PriorStorePersistenceError("fail"),
    ):
        with pytest.raises(PriorStorePersistenceError):
            filt.on_trade_outcome(
                {
                    "outcome": "win",
                    "oteo_score": 88.0,
                    "regime_label": "RANGE_BOUND",
                    "confidence": "HIGH",
                    "z_score": 0.3,
                    "manipulation": False,
                    "recommended": "CALL",
                }
            )
    assert filt.total_wins == 2
    assert filt.total_losses == 1


def test_concurrent_readers_zero_parse_errors(tmp_path):
    path = tmp_path / "priors.json"
    store = BayesianPriorStore(path)
    store.update_from_trades([{"won": True, "features": ["r=0"]}])

    errors: list = []
    stop = threading.Event()

    def writer():
        s = BayesianPriorStore(path, lock_timeout_sec=30.0)
        i = 0
        while not stop.is_set() and i < 40:
            try:
                s.update_from_trades([{"won": i % 2 == 0, "features": [f"r={i % 3}"]}])
            except Exception as exc:
                errors.append(("w", exc))
            i += 1
            time.sleep(0.005)

    def reader():
        s = BayesianPriorStore(path, lock_timeout_sec=30.0)
        for _ in range(80):
            try:
                data = s.read()
                json.dumps(data)  # ensure serializable
                normalize_priors(data)
            except Exception as exc:
                errors.append(("r", exc))
            time.sleep(0.002)

    threads = [threading.Thread(target=writer)] + [
        threading.Thread(target=reader) for _ in range(4)
    ]
    for t in threads:
        t.start()
    threads[0].join(timeout=60)
    stop.set()
    for t in threads[1:]:
        t.join(timeout=15)

    parse_errors = [
        e
        for e in errors
        if isinstance(e[1], json.JSONDecodeError)
        or "JSON" in type(e[1]).__name__
        or "Invalid JSON" in str(e[1])
        or "JSONDecodeError" in str(type(e[1]))
    ]
    assert not parse_errors, f"JSON parse errors under concurrency: {parse_errors}"
    assert not errors, f"Unexpected concurrent errors: {errors}"


def test_two_process_workers_preserve_all_increments(tmp_path):
    """T4.1 — Two process workers perform 100 updates each; all 200 increments persist."""
    path = tmp_path / "mp_priors.json"
    n_each = 100
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(mp_prior_store_worker, (str(path), n_each, True)),
            pool.submit(mp_prior_store_worker, (str(path), n_each, False)),
        ]
        results = [f.result(timeout=180) for f in as_completed(futures)]
    assert set(results) == {n_each}

    data = BayesianPriorStore(path).read()
    assert data["total_wins"] == n_each
    assert data["total_losses"] == n_each
    assert data["total_trades"] == 2 * n_each


def test_apply_trade_outcomes_pure():
    base = empty_priors()
    out = apply_trade_outcomes(
        base,
        [{"won": True, "features": ["a=1"]}, {"won": False, "features": ["a=1"]}],
    )
    assert out["total_wins"] == 1
    assert out["total_losses"] == 1
    assert out["feature_counts"]["a=1"] == {"win": 1, "loss": 1}
