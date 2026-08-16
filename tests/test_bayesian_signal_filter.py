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
# Basic Tests
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


def test_bayesian_signal_filter_veto_logic(seeded_filter):
    seeded_filter.min_win_probability = 0.99

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

    allowed, reason = seeded_filter.on_consider_signal("EURUSD_otc", 1.0850, oteo_test, DummyConfig())
    assert allowed is False
    assert "Bayesian Win Probability" in reason


def test_bayesian_signal_filter_disabled_pass(seeded_filter):
    seeded_filter.enabled = False

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

    allowed, reason = seeded_filter.on_consider_signal("EURUSD_otc", 1.0850, oteo_test, DummyConfig())
    assert allowed is True
    assert reason is None


# ---------------------------------------------------------------------------
# Fail-closed checks on empty priors
# ---------------------------------------------------------------------------

def test_cold_start_empty_priors_vetoed_in_consider_signal(empty_filter):
    """When priors are empty, on_consider_signal must fail closed with bayesian_priors_unavailable."""
    oteo_test = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
    }

    class DummyConfig:
        bayesian_filter_enabled = True
        bayesian_min_probability = 0.55

    allowed, reason = empty_filter.on_consider_signal("EURUSD_otc", 1.0850, oteo_test, DummyConfig())
    assert allowed is False
    assert "bayesian_priors_unavailable" in reason


def test_cold_start_probability_near_50(empty_filter):
    """With no prior observations, predict_win_probability defaults to 0.5."""
    prob = empty_filter.predict_win_probability({
        "oteo_score": 80.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
    })
    assert 0.0 <= prob <= 1.0
    assert abs(prob - 0.5) < 0.01


# ---------------------------------------------------------------------------
# Defaultdict auto-vivification guard
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

    assert len(empty_filter.feature_counts) == initial_key_count


# ---------------------------------------------------------------------------
# Online learning: on_trade_outcome & Horizon Guard (Phase 1)
# ---------------------------------------------------------------------------

def test_on_trade_outcome_skips_when_missing_expiration(empty_filter):
    """Trades missing expiration_seconds must be skipped (fail-closed)."""
    trade_data = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
        "outcome": "win",
        # missing expiration_seconds
    }
    empty_filter.on_trade_outcome(trade_data)
    assert empty_filter.total_wins == 0
    assert empty_filter.total_losses == 0


def test_on_trade_outcome_skips_non_60s_expiry(empty_filter):
    """Non-60s trade outcomes (e.g. 120s or 300s) must be skipped to avoid horizon conflation."""
    trade_data_300 = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
        "outcome": "win",
        "expiration_seconds": 300,
    }
    empty_filter.on_trade_outcome(trade_data_300)
    assert empty_filter.total_wins == 0

    trade_data_120 = {
        "outcome": "loss",
        "expiration_seconds": 120,
        "entry_context": {
            "oteo_score": 70.0,
            "regime_label": "RANGE_BOUND",
            "confidence": "LOW",
        }
    }
    empty_filter.on_trade_outcome(trade_data_120)
    assert empty_filter.total_losses == 0


def test_on_trade_outcome_increments_60s_win(empty_filter):
    """Valid 60s win increments counters and feature counts."""
    trade_data = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
        "outcome": "win",
        "expiration_seconds": 60,
    }
    wins_before = empty_filter.total_wins
    empty_filter.on_trade_outcome(trade_data)
    assert empty_filter.total_wins == wins_before + 1
    assert empty_filter.feature_counts["oteo_band=85-92"]["win"] == 1


def test_on_trade_outcome_increments_60s_loss_with_nested_entry_context(empty_filter):
    """Valid 60s loss with nested entry_context extracts features and increments counts."""
    trade_data = {
        "outcome": "loss",
        "profit": -10.0,
        "entry_context": {
            "oteo_score": 70.0,
            "regime_label": "STRONG_MOMENTUM",
            "confidence": "MEDIUM",
            "z_score": -0.8,
            "manipulation": True,
            "recommended": "PUT",
            "expiration_seconds": 60,
        }
    }
    losses_before = empty_filter.total_losses
    empty_filter.on_trade_outcome(trade_data)
    assert empty_filter.total_losses == losses_before + 1
    assert empty_filter.feature_counts["oteo_band=65-74"]["loss"] == 1
    assert empty_filter.feature_counts["regime=STRONG_MOMENTUM"]["loss"] == 1
    assert empty_filter.feature_counts["has_manip=MANIP_TRUE"]["loss"] == 1
    assert empty_filter.feature_counts["z_band=-1.5_to_-0.5"]["loss"] == 1
    assert empty_filter.feature_counts["direction=PUT"]["loss"] == 1


def test_extract_features_nested_vs_flat_equivalence(empty_filter):
    """_extract_features produces identical dictionaries for flat and nested dict structures."""
    flat_data = {
        "oteo_score": 95.0,
        "regime_label": "TREND_REVERSAL",
        "confidence": "HIGH",
        "z_score": 1.8,
        "manipulation": True,
        "recommended": "PUT",
    }
    nested_data = {
        "entry_context": flat_data
    }

    feats_flat = empty_filter._extract_features(flat_data)
    feats_nested = empty_filter._extract_features(nested_data)

    assert feats_flat == feats_nested
    assert feats_flat["oteo_band"] == "93+"
    assert feats_flat["regime"] == "TREND_REVERSAL"
    assert feats_flat["confidence"] == "HIGH"
    assert feats_flat["z_band"] == ">1.5"
    assert feats_flat["has_manip"] == "MANIP_TRUE"
    assert feats_flat["direction"] == "PUT"


# ---------------------------------------------------------------------------
# Priors persistence roundtrip
# ---------------------------------------------------------------------------

def test_save_load_roundtrip(tmp_path):
    """Saving priors then loading them in a new instance produces identical state."""
    priors_file = tmp_path / "bayesian_priors.json"
    f1 = BayesianSignalFilter({"enabled": True, "priors_file": priors_file})

    outcome_base = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "z_score": 0.3,
        "manipulation": False,
        "recommended": "CALL",
        "expiration_seconds": 60,
    }
    f1.on_trade_outcome({**outcome_base, "outcome": "win"})
    f1.on_trade_outcome({**outcome_base, "outcome": "loss"})

    f2 = BayesianSignalFilter({"enabled": True, "priors_file": priors_file})
    assert f2.total_wins == f1.total_wins
    assert f2.total_losses == f1.total_losses
    assert f2.feature_counts["oteo_band=85-92"]["win"] == f1.feature_counts["oteo_band=85-92"]["win"]


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


# ---------------------------------------------------------------------------
# Thread safety — concurrent on_trade_outcome calls
# ---------------------------------------------------------------------------

def test_thread_safe_concurrent_updates(empty_filter):
    """Concurrent trade outcome updates must not corrupt win/loss counters."""
    N = 30
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
                "expiration_seconds": 60,
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


# ---------------------------------------------------------------------------
# Multi-Horizon Tests (60s vs 300s)
# ---------------------------------------------------------------------------

def test_multi_horizon_prediction_and_routing(tmp_path):
    priors_60 = tmp_path / "bayesian_priors_60.json"
    priors_300 = tmp_path / "bayesian_priors_300.json"

    priors_60.write_text(json.dumps({
        "total_wins": 100,
        "total_losses": 100,
        "total_trades": 200,
        "feature_counts": {
            "oteo_band=85-92": {"win": 60, "loss": 40},
            "regime=RANGE_BOUND": {"win": 70, "loss": 30},
            "confidence=HIGH": {"win": 60, "loss": 40},
            "z_band=-0.5_to_0.5": {"win": 50, "loss": 50},
            "has_manip=MANIP_FALSE": {"win": 50, "loss": 50},
            "direction=CALL": {"win": 50, "loss": 50},
        }
    }), encoding="utf-8")

    priors_300.write_text(json.dumps({
        "total_wins": 100,
        "total_losses": 100,
        "total_trades": 200,
        "feature_counts": {
            "oteo_band=85-92": {"win": 40, "loss": 60},
            "regime=RANGE_BOUND": {"win": 30, "loss": 70},
            "confidence=HIGH": {"win": 40, "loss": 60},
            "z_band=-0.5_to_0.5": {"win": 50, "loss": 50},
            "has_manip=MANIP_FALSE": {"win": 50, "loss": 50},
            "direction=CALL": {"win": 50, "loss": 50},
        }
    }), encoding="utf-8")

    b_filter = BayesianSignalFilter({
        "enabled": True,
        "min_win_probability": 0.55,
        "priors_file": priors_60,
        "priors_file_300s": priors_300,
    })

    signal = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "direction": "CALL",
        "z_score": 0.0,
        "manipulation": False,
    }

    prob_60 = b_filter.predict_win_probability(signal, horizon_seconds=60)
    prob_300 = b_filter.predict_win_probability(signal, horizon_seconds=300)

    assert prob_60 > prob_300, "60s probability should be higher than 300s given the seeded distributions"
    assert prob_60 > 0.55
    assert prob_300 < 0.55

    # Test on_consider_signal with 60s
    pass_60, reason_60 = b_filter.on_consider_signal("EURUSD", 1.1, dict(signal, override_expiration_seconds=60), None)
    assert pass_60 is True
    assert reason_60 is None

    # Test on_consider_signal with 300s
    pass_300, reason_300 = b_filter.on_consider_signal("EURUSD", 1.1, dict(signal, override_expiration_seconds=300), None)
    assert pass_300 is False
    assert "Bayesian Win Probability" in reason_300
    assert "300s" in reason_300

    # Test on_trade_outcome routes 300s to 300s store
    trade_outcome_300 = {
        "oteo_score": 88.0,
        "regime_label": "RANGE_BOUND",
        "confidence": "HIGH",
        "direction": "CALL",
        "z_score": 0.0,
        "manipulation": False,
        "outcome": "win",
        "expiration_seconds": 300,
    }
    b_filter.on_trade_outcome(trade_outcome_300)

    assert b_filter._priors_state[300]["total_wins"] == 101
    assert b_filter._priors_state[60]["total_wins"] == 100  # unchanged


