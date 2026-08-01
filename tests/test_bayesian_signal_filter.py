from __future__ import annotations

import sys
import json
import tempfile
import threading
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from app.backend.services.extensions.bayesian_signal_filter import BayesianSignalFilter
from app.backend.services.auto_ghost import AutoGhostConfig, AutoGhostService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def empty_filter(tmp_path):
    """BayesianSignalFilter with NO priors — cold start."""
    priors_file = tmp_path / "bayesian_priors.json"  # does not exist yet
    return BayesianSignalFilter({"enabled": True, "min_win_probability": 0.55, "priors_file": priors_file})


@pytest.fixture()
def seeded_filter(tmp_path):
    """BayesianSignalFilter with a minimal seeded priors file."""
    priors_file = tmp_path / "bayesian_priors.json"
    priors_data = {
        "total_wins": 100,
        "total_losses": 90,
        "total_trades": 190,
        "feature_counts": {
            "oteo_band=85-92": {"win": 60, "loss": 40},
            "regime=RANGE_BOUND": {"win": 55, "loss": 45},
            "confidence=HIGH": {"win": 70, "loss": 30},
            "z_band=-0.5_to_0.5": {"win": 50, "loss": 50},
            "has_manip=MANIP_FALSE": {"win": 80, "loss": 70},
            "direction=CALL": {"win": 55, "loss": 45},
        },
    }
    priors_file.write_text(json.dumps(priors_data), encoding="utf-8")
    return BayesianSignalFilter({"enabled": True, "min_win_probability": 0.55, "priors_file": priors_file})


# ---------------------------------------------------------------------------
# Original tests — unchanged, still passing
# ---------------------------------------------------------------------------

def test_bayesian_signal_filter_initialization():
    filter_ext = BayesianSignalFilter({"enabled": True, "min_win_probability": 0.55})
    assert filter_ext.enabled is True
    assert filter_ext.min_win_probability == 0.55
    assert filter_ext.total_wins > 0
    assert filter_ext.total_losses > 0


def test_bayesian_signal_filter_probability_calculation():
    filter_ext = BayesianSignalFilter({"enabled": True, "min_win_probability": 0.55})

    oteo_high = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.8,
        "manipulation": False,
        "recommended": "CALL"
    }
    prob = filter_ext.predict_win_probability(oteo_high)
    assert 0.0 <= prob <= 1.0


def test_bayesian_signal_filter_veto_logic():
    filter_ext = BayesianSignalFilter({"enabled": True, "min_win_probability": 0.99})

    oteo_test = {
        "oteo_score": 75.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "MEDIUM",
        "z_score": 0.2,
        "manipulation": False,
        "recommended": "CALL"
    }

    class DummyConfig:
        bayesian_filter_enabled = True
        bayesian_min_probability = 0.99

    allowed, reason = filter_ext.on_consider_signal("EURUSD_otc", 1.0850, oteo_test, DummyConfig())
    assert allowed is False
    assert "Bayesian Win Probability" in reason


def test_bayesian_signal_filter_disabled_pass():
    filter_ext = BayesianSignalFilter({"enabled": False, "min_win_probability": 0.55})

    oteo_test = {
        "oteo_score": 50.0,
        "regime_label": "CHOPPY",
        "confidence": "LOW",
        "z_score": -2.0,
        "manipulation": True,
        "recommended": "PUT"
    }

    class DummyConfig:
        bayesian_filter_enabled = False
        bayesian_min_probability = 0.55

    allowed, reason = filter_ext.on_consider_signal("EURUSD_otc", 1.0850, oteo_test, DummyConfig())
    assert allowed is True
    assert reason is None


# ---------------------------------------------------------------------------
# R1: cold-start (empty priors) — probability should be ~0.5
# ---------------------------------------------------------------------------

def test_cold_start_probability_near_50(empty_filter):
    """With no prior observations, all feature likelihoods collapse to 0.5."""
    prob = empty_filter.predict_win_probability({
        "oteo_score": 80.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
    })
    assert 0.0 <= prob <= 1.0
    # With empty priors the prior is 0.5 and all likelihoods cancel → ~0.5
    assert abs(prob - 0.5) < 0.01


# ---------------------------------------------------------------------------
# R2: defaultdict auto-vivification guard
# ---------------------------------------------------------------------------

def test_predict_does_not_pollute_feature_counts(empty_filter):
    """Calling predict_win_probability must NOT create phantom keys in feature_counts."""
    initial_key_count = len(empty_filter.feature_counts)

    empty_filter.predict_win_probability({
        "oteo_score": 78.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.5,
        "manipulation": False,
        "recommended": "CALL",
    })

    assert len(empty_filter.feature_counts) == initial_key_count, (
        "predict_win_probability must not create new defaultdict entries for unseen features"
    )


# ---------------------------------------------------------------------------
# Online learning: on_trade_outcome
# ---------------------------------------------------------------------------

def test_on_trade_outcome_increments_win(empty_filter):
    trade_data = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
        "outcome": "win",
    }
    wins_before = empty_filter.total_wins
    empty_filter.on_trade_outcome(trade_data)
    assert empty_filter.total_wins == wins_before + 1
    assert empty_filter.feature_counts["oteo_band=85-92"]["win"] == 1


def test_on_trade_outcome_increments_loss(empty_filter):
    trade_data = {
        "oteo_score": 70.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "MEDIUM",
        "z_score": -0.2,
        "manipulation": False,
        "recommended": "PUT",
        "outcome": "loss",
    }
    losses_before = empty_filter.total_losses
    empty_filter.on_trade_outcome(trade_data)
    assert empty_filter.total_losses == losses_before + 1


def test_on_trade_outcome_ignores_invalid_outcome(empty_filter):
    """Outcomes that are not 'win' or 'loss' should be silently ignored."""
    wins_before = empty_filter.total_wins
    losses_before = empty_filter.total_losses
    empty_filter.on_trade_outcome({"outcome": "pending", "oteo_score": 80.0})
    assert empty_filter.total_wins == wins_before
    assert empty_filter.total_losses == losses_before


# ---------------------------------------------------------------------------
# Priors persistence roundtrip
# ---------------------------------------------------------------------------

def test_save_load_roundtrip(tmp_path):
    """Saving priors then loading them in a new instance produces identical state."""
    priors_file = tmp_path / "bayesian_priors.json"
    f1 = BayesianSignalFilter({"enabled": True, "priors_file": priors_file})

    # Record a win and a loss
    outcome_base = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
    }
    f1.on_trade_outcome({**outcome_base, "outcome": "win"})
    f1.on_trade_outcome({**outcome_base, "outcome": "loss"})

    # Load into a fresh instance from the same priors file
    f2 = BayesianSignalFilter({"enabled": True, "priors_file": priors_file})
    assert f2.total_wins == f1.total_wins
    assert f2.total_losses == f1.total_losses
    assert f2.feature_counts["oteo_band=85-92"]["win"] == f1.feature_counts["oteo_band=85-92"]["win"]


# ---------------------------------------------------------------------------
# R6: cached probability reuse in on_consider_signal
# ---------------------------------------------------------------------------

def test_on_consider_signal_reuses_cached_probability(seeded_filter):
    """If bayesian_win_probability is already in oteo_result, do not recompute."""
    oteo = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
        # Pre-inject a cached value that will definitely pass the floor
        "bayesian_win_probability": 0.99,
    }

    class DummyConfig:
        bayesian_filter_enabled = True
        bayesian_min_probability = 0.55

    allowed, reason = seeded_filter.on_consider_signal("EURUSD_otc", 1.0, oteo, DummyConfig())
    assert allowed is True
    # The cached value must be preserved (not overwritten by recomputation)
    assert oteo["bayesian_win_probability"] == 0.99


# ---------------------------------------------------------------------------
# Feature extraction boundary tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected_band", [
    (0.0,   "<65"),
    (64.9,  "<65"),
    (65.0,  "65-74"),
    (74.9,  "65-74"),
    (75.0,  "75-84"),
    (84.9,  "75-84"),
    (85.0,  "85-92"),
    (92.9,  "85-92"),
    (93.0,  "93+"),
    (100.0, "93+"),
])
def test_oteo_band_boundaries(empty_filter, score, expected_band):
    feats = empty_filter._extract_features({"oteo_score": score})
    assert feats["oteo_band"] == expected_band


@pytest.mark.parametrize("z,expected_band", [
    (-2.0,  "<-1.5"),
    (-1.5,  "-1.5_to_-0.5"),
    (-0.5,  "-0.5_to_0.5"),
    (0.0,   "-0.5_to_0.5"),
    (0.5,   "-0.5_to_0.5"),
    (0.51,  "0.5_to_1.5"),
    (1.5,   "0.5_to_1.5"),
    (1.51,  ">1.5"),
    (3.0,   ">1.5"),
])
def test_z_band_boundaries(empty_filter, z, expected_band):
    feats = empty_filter._extract_features({"z_score": z})
    assert feats["z_band"] == expected_band


def test_missing_all_fields_graceful(empty_filter):
    """Passing an empty dict must not raise — all features fall back to defaults."""
    prob = empty_filter.predict_win_probability({})
    assert 0.0 <= prob <= 1.0


# ---------------------------------------------------------------------------
# R4: Thread safety — concurrent on_trade_outcome calls
# ---------------------------------------------------------------------------

def test_thread_safe_concurrent_updates(empty_filter):
    """Concurrent trade outcome updates must not corrupt win/loss counters."""
    N = 50
    errors = []

    def record_win():
        try:
            empty_filter.on_trade_outcome({
                "oteo_score": 88.0,
                "regime_label": "RANGE_BOUND",
                "confidence": "HIGH",
                "z_score": 0.3,
                "manipulation": False,
                "recommended": "CALL",
                "outcome": "win",
            })
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=record_win) for _ in range(N)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread exceptions: {errors}"
    assert empty_filter.total_wins == N
