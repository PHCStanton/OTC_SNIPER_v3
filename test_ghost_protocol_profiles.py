"""Phase 5 — strictness presets (M8) and market-drift detector (A4)."""

from __future__ import annotations

from app.backend.services.ghost_protocol_profiles import (
    FRONTEND_GATE_KEYS,
    backend_gates_to_frontend,
    build_strictness_presets,
    classify_alignment,
    compute_feature_centroids,
    detect_market_drift,
)


def test_presets_cover_all_m8_gate_families():
    presets = build_strictness_presets()
    assert set(presets) == {"relaxed", "conservative", "strict"}
    for key, preset in presets.items():
        gates = preset["gates"]
        missing = [k for k in FRONTEND_GATE_KEYS if k not in gates or gates[k] is None]
        assert not missing, f"{key} missing {missing}"
        assert gates["autoGhostBayesianMinProbability"] >= 50
        assert gates["autoGhostMinimumPayout"] >= 85
        assert gates["autoGhostMaxConcurrentTrades"] >= 1


def test_strict_is_tighter_than_relaxed():
    presets = build_strictness_presets()
    relaxed = presets["relaxed"]["gates"]
    strict = presets["strict"]["gates"]
    assert strict["ghostMaxZScore"] < relaxed["ghostMaxZScore"]
    assert strict["autoGhostMaxConcurrentTrades"] == 1
    assert strict["autoGhostBayesianMinProbability"] > relaxed["autoGhostBayesianMinProbability"]
    assert strict["ghostRegimeGateEnabled"] is True
    assert relaxed["ghostRegimeGateEnabled"] is False


def test_backend_to_frontend_bayesian_is_percent():
    frontend = backend_gates_to_frontend({
        "bayesian_min_probability": 0.535,
        "min_zscore": -1.5,
        "min_zscore_enabled": True,
        "max_zscore": 1.5,
        "max_zscore_enabled": True,
        "regime_gate_enabled": False,
        "allowed_regimes": [],
        "volatility_gate_enabled": True,
        "min_volatility": 20,
        "max_volatility": 80,
        "liquidity_gate_enabled": True,
        "min_liquidity": 20,
        "max_liquidity": 80,
        "bayesian_filter_enabled": True,
        "minimum_payout_pct": 88.0,
        "amount": 1.0,
        "max_concurrent_trades": 2,
        "min_confidence": 75.0,
        "min_confidence_enabled": True,
        "manipulation_severity_threshold": 0.35,
    })
    assert frontend["autoGhostBayesianMinProbability"] == 53.5


def test_drift_detector_fires_on_ood_stream():
    centroids = {
        "overall": {
            "volatility": {"mean": 50.0, "std": 5.0, "n": 40},
            "liquidity": {"mean": 50.0, "std": 5.0, "n": 40},
            "manipulation": {"mean": 0.10, "std": 0.05, "n": 40},
            "z_score": {"mean": 0.0, "std": 0.4, "n": 40},
        }
    }
    in_dist = [
        {"volatility": 51.0, "liquidity": 49.0, "manipulation": 0.11, "z_score": 0.05}
        for _ in range(12)
    ]
    ood = [
        {"volatility": 90.0, "liquidity": 10.0, "manipulation": 0.85, "z_score": 2.4}
        for _ in range(12)
    ]
    quiet = detect_market_drift(in_dist, centroids)
    loud = detect_market_drift(ood, centroids)
    assert quiet["drifted"] is False
    assert loud["drifted"] is True
    assert len(loud["drifted_dims"]) >= 2


def test_alignment_prefers_relaxed_in_favorable_pocket():
    warm = {
        "by_utc_4h_block": {"5": {"wr": 62.0, "n": 40}},
        "feature_centroids": {
            "overall": {
                "volatility": {"mean": 40.0, "std": 10.0, "n": 40},
                "liquidity": {"mean": 40.0, "std": 10.0, "n": 40},
                "manipulation": {"mean": 0.30, "std": 0.1, "n": 40},
                "z_score": {"mean": 0.0, "std": 1.0, "n": 40},
            }
        },
    }
    live = {"volatility": 70.0, "liquidity": 65.0, "manipulation": 0.10, "z_score": 0.2, "utc_4h_block": 5}
    out = classify_alignment(live, warm)
    assert out["level"] == "relaxed"


def test_centroids_from_trades():
    trades = [
        {
            "outcome": "win",
            "entry_time": 1780000000.0,
            "entry_context": {
                "z_score": 0.2,
                "manipulation": {"Push": 0.1},
                "market_context": {"volatility_score": 55.0, "liquidity_score": 60.0},
            },
        }
        for _ in range(5)
    ]
    centroids = compute_feature_centroids(trades)
    assert centroids["overall"]["volatility"]["n"] == 5
    assert centroids["overall"]["volatility"]["mean"] == 55.0
