"""Unit tests for BayesianProtocol specification, manager, and activation lifecycle."""

from __future__ import annotations

import json
import pytest
import shutil
import tempfile
from pathlib import Path

from shared.bayesian_protocol import (
    BayesianProtocolManager,
    ProtocolHealth,
    ProtocolError,
    ProtocolValidationError,
    compute_protocol_health,
    validate_protocol_dict,
)
from shared.bayesian_prior_store import BayesianPriorStore


@pytest.fixture()
def temp_stats_dir(tmp_path):
    stats_dir = tmp_path / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)
    return stats_dir


@pytest.fixture()
def protocol_manager(temp_stats_dir):
    return BayesianProtocolManager(temp_stats_dir)


def test_compute_protocol_health():
    # READY: N >= 500 and horizon in {60, 300}
    assert compute_protocol_health(60, 500) == ProtocolHealth.READY
    assert compute_protocol_health(300, 1000) == ProtocolHealth.READY

    # EXPERIMENTAL: 100 <= N < 500
    assert compute_protocol_health(60, 250) == ProtocolHealth.EXPERIMENTAL
    assert compute_protocol_health(120, 600) == ProtocolHealth.EXPERIMENTAL

    # UNSAFE: N < 100
    assert compute_protocol_health(60, 99) == ProtocolHealth.UNSAFE
    assert compute_protocol_health(300, 0) == ProtocolHealth.UNSAFE


def test_validate_protocol_dict_valid():
    raw = {
        "schema_version": 1,
        "id": "proto_test_1",
        "name": "60s Range Bound Edge",
        "horizon_seconds": 60,
        "source_sessions": ["session_1", "session_2"],
        "priors": {
            "total_wins": 300,
            "total_losses": 250,
            "total_trades": 550,
            "feature_counts": {
                "regime=RANGE_BOUND": {"win": 200, "loss": 150}
            }
        },
        "patterns": [
            {"pattern_key": "EURUSD|level3|85-92|RANGE_BOUND|CALL", "sample_size": 20}
        ]
    }
    validated = validate_protocol_dict(raw)
    assert validated["id"] == "proto_test_1"
    assert validated["name"] == "60s Range Bound Edge"
    assert validated["horizon_seconds"] == 60
    assert validated["trade_count"] == 550
    assert validated["health"] == ProtocolHealth.READY.value
    assert len(validated["patterns"]) == 1


def test_validate_protocol_dict_invalid_priors():
    raw = {
        "id": "proto_bad",
        "name": "Bad Priors",
        "priors": {
            "total_wins": 50,
            "total_losses": 50,
            "total_trades": 200, # mismatch
        }
    }
    with pytest.raises(ProtocolValidationError):
        validate_protocol_dict(raw)


def test_save_list_get_delete_protocol(protocol_manager):
    proto_data = {
        "id": "proto_alpha",
        "name": "Alpha 60s",
        "horizon_seconds": 60,
        "priors": {
            "total_wins": 350,
            "total_losses": 250,
            "total_trades": 600,
            "feature_counts": {}
        }
    }
    saved = protocol_manager.save_protocol(proto_data)
    assert saved["id"] == "proto_alpha"
    assert saved["health"] == ProtocolHealth.READY.value

    # List protocols
    proto_list = protocol_manager.list_protocols()
    assert len(proto_list) == 1
    assert proto_list[0]["id"] == "proto_alpha"
    assert proto_list[0]["win_rate"] == 58.3

    # Get protocol
    fetched = protocol_manager.get_protocol("proto_alpha")
    assert fetched is not None
    assert fetched["name"] == "Alpha 60s"

    # Delete protocol
    deleted = protocol_manager.delete_protocol("proto_alpha")
    assert deleted is True
    assert protocol_manager.get_protocol("proto_alpha") is None


def test_activate_protocol(protocol_manager, temp_stats_dir):
    # Create two protocols
    p1 = {
        "id": "proto_60_ready",
        "name": "60s Baseline READY",
        "horizon_seconds": 60,
        "priors": {
            "total_wins": 300,
            "total_losses": 300,
            "total_trades": 600,
            "feature_counts": {
                "confidence=HIGH": {"win": 200, "loss": 100}
            }
        }
    }
    p2 = {
        "id": "proto_unsafe",
        "name": "Unsafe Protocol",
        "horizon_seconds": 60,
        "priors": {
            "total_wins": 10,
            "total_losses": 10,
            "total_trades": 20,
            "feature_counts": {}
        }
    }
    protocol_manager.save_protocol(p1)
    protocol_manager.save_protocol(p2)

    # Activating UNSAFE protocol must fail
    with pytest.raises(ProtocolValidationError, match="UNSAFE"):
        protocol_manager.activate_protocol("proto_unsafe")

    # Activate READY protocol
    active = protocol_manager.activate_protocol("proto_60_ready")
    assert active["id"] == "proto_60_ready"
    assert active["health"] == "READY"

    # Verify live bayesian_priors.json was updated
    live_store = BayesianPriorStore(temp_stats_dir / "bayesian_priors.json")
    live_data = live_store.read()
    assert live_data["total_trades"] == 600
    assert live_data["feature_counts"]["confidence=HIGH"]["win"] == 200

    # Verify active protocol pointer
    info = protocol_manager.get_active_protocol_info()
    assert info["id"] == "proto_60_ready"

    # Verify list reflects active status
    proto_list = protocol_manager.list_protocols()
    assert proto_list[0]["is_active"] is True


def test_import_legacy_staging_bundle(protocol_manager):
    legacy_bundle = {
        "staged_id": "staged_1786686494_auto_ghost_1786547913",
        "timestamp": "2026-08-14T05:48:14.756998+00:00",
        "session_id": "auto_ghost_1786547913",
        "selected_patterns": [
            {"pattern_key": "AUDCAD_otc|level3|85-92|RANGE_BOUND|PUT", "sample_size": 5}
        ],
        "bayesian_deltas": {
            "total_wins_delta": 66,
            "total_losses_delta": 36,
            "total_trades_delta": 102,
            "feature_deltas": {
                "oteo_band=85-92": {"win": 20, "loss": 8}
            }
        }
    }
    raw_json = json.dumps(legacy_bundle)
    imported = protocol_manager.import_from_json(raw_json)

    assert imported["id"] == "proto_staged_1786686494_auto_ghost_1786547913"
    assert imported["trade_count"] == 102
    assert imported["health"] == ProtocolHealth.EXPERIMENTAL.value
    assert imported["priors"]["total_wins"] == 66
    assert imported["priors"]["total_losses"] == 36
    assert len(imported["patterns"]) == 1
