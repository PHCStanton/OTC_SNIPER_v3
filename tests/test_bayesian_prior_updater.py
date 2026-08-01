"""
Unit tests for Bayesian Prior Updater.
"""

import json
import pytest
from data_agent.src.bayesian.prior_updater import BayesianPriorUpdater


def test_atomic_prior_update(tmp_path):
    priors_file = tmp_path / "bayesian_priors.json"
    updater = BayesianPriorUpdater(priors_json_path=str(priors_file))

    outcomes = [
        {"won": True, "features": ["oteo_band=85-92", "confidence=HIGH"]},
        {"won": False, "features": ["oteo_band=85-92", "direction=PUT"]},
    ]

    updated = updater.update_priors_from_trades(outcomes)

    assert updated["total_wins"] == 1
    assert updated["total_losses"] == 1
    assert updated["total_trades"] == 2
    assert updated["feature_counts"]["oteo_band=85-92"]["win"] == 1
    assert updated["feature_counts"]["oteo_band=85-92"]["loss"] == 1

    # Verify file content
    with open(priors_file, "r") as f:
        saved = json.load(f)
    assert saved["total_trades"] == 2
