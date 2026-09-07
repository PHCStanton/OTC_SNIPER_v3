"""Calibrated Apply Gates contract tests (feat/ai_kb, 2026-09-04).

Verifies the post-calibration one-click apply payload and the Bayesian
decoupling from strictness presets:

- build_calibrated_gates: family extraction (last-write-wins), Guardian
  proposal precedence + never-empty guard, Bayesian choice/READY semantics,
  evidence passthrough.
- Preset decoupling: strictness presets never force-enable the Bayesian
  filter; floor values intact; Conservative renamed "Balanced".
- Finalize integration: DONE attaches calibrated_gates to the final report.
"""

from __future__ import annotations

import pytest

from app.backend.services.calibrated_apply import (
    _suggest_bayesian_floor,
    build_calibrated_gates,
)
from app.backend.services.ghost_protocol_profiles import build_strictness_presets


def _entry(field: str, new, epoch: int, evidence_n: int = 8, rationale: str = "tighten") -> dict:
    """A changelog ``tier_a_applied`` record matching the epoch contract."""
    return {
        "epoch": epoch,
        "event": "tier_a_applied",
        "ts": 0.0,
        "field": field,
        "old": None,
        "new": new,
        "trade_index": epoch,
        "rationale": rationale,
        "evidence_n": evidence_n,
    }


_FINAL = {
    "settled_wins": 12,
    "settled_losses": 8,
    "settled_voids": 1,
    "win_rate": 60.0,
    "calibration_pnl": 4.2,
}


def test_families_last_write_wins_and_absent_families():
    changelog = [
        _entry("min_zscore", -1.5, 5),
        _entry("min_zscore", -1.0, 9),
        _entry("max_zscore", 1.5, 9),
    ]
    out = build_calibrated_gates(changelog, final_report=_FINAL)
    fam = out["families"]["zscore"]
    assert fam["gates"]["ghostMinZScore"] == -1.0  # last write wins
    assert fam["gates"]["ghostMaxZScore"] == 1.5
    assert fam["changes"] == 2
    # Untouched families are absent — the card never invents values.
    assert "volatility" not in out["families"]
    assert "regimes" not in out["families"]
    # No Tier A floor change -> WR-based suggestion (60% >= 56 -> 0.50), floor
    # only: `enabled` is NEVER part of the payload (user choice on the card).
    assert out["bayesian"]["gates"]["autoGhostBayesianMinProbability"] == 50.0
    assert "autoGhostBayesianFilterEnabled" not in out["bayesian"]["gates"]
    assert out["evidence"]["settled"] == 20
    assert out["evidence"]["win_rate"] == 60.0
    assert out["evidence"]["voids"] == 1


def test_regimes_proposal_precedence_and_never_empty():
    changelog = [_entry("allowed_regimes", ["A", "B", "C"], 6, evidence_n=6)]
    proposals = [
        {
            "field": "allowed_regimes",
            "family": "regimes",
            "bucket": "regimes:BAD",
            "new": ["A", "B"],
            "rationale": "Drop BAD: 8/20 wins (40.0% WR, N=20 >= 20)",
            "evidence_n": 20,
        }
    ]
    out = build_calibrated_gates(changelog, final_report=_FINAL, proposals=proposals)
    regimes = out["families"]["regimes"]
    assert regimes["gates"]["ghostAllowedRegimes"] == ["A", "B"]
    assert regimes["gates"]["ghostRegimeGateEnabled"] is True
    assert regimes["proposal"] is True
    assert regimes["evidence_n"] == 20


def test_regimes_proposal_requires_non_empty():
    proposals = [{"field": "allowed_regimes", "new": [], "evidence_n": 20}]
    out = build_calibrated_gates([], final_report=_FINAL, proposals=proposals)
    assert "regimes" not in out["families"]
    assert out["families"] == {}


def test_tier_a_empty_allowed_regimes_never_surfaced():
    # F-1: an empty allowed_regimes from a Tier A changelog entry must NOT
    # surface on the Apply card (would degrade to "allow all regimes"). The
    # family is omitted entirely, never emitted as [].
    changelog = [_entry("allowed_regimes", [], 12, evidence_n=20)]
    out = build_calibrated_gates(changelog, final_report=_FINAL)
    # The regimes family has no other gate (regime_gate_enabled absent here) so
    # it must not appear with an empty whitelist.
    assert "regimes" not in out["families"]
    # A non-empty list still surfaces normally.
    good = build_calibrated_gates(
        [_entry("allowed_regimes", ["A", "B"], 12, evidence_n=20)],
        final_report=_FINAL,
    )
    assert good["families"]["regimes"]["gates"]["ghostAllowedRegimes"] == ["A", "B"]


def test_bayesian_floor_suggestions_deterministic():
    assert _suggest_bayesian_floor(40.0) == 0.58
    assert _suggest_bayesian_floor(57.0) == 0.50
    assert _suggest_bayesian_floor(50.0) == 0.535
    assert _suggest_bayesian_floor(None) == 0.535
    assert _suggest_bayesian_floor("bad") == 0.535


def test_bayesian_tier_a_floor_wins_over_suggestion():
    changelog = [_entry("bayesian_min_probability", 0.56, 12)]
    out = build_calibrated_gates(changelog, final_report=_FINAL)
    assert out["bayesian"]["gates"]["autoGhostBayesianMinProbability"] == 56.0
    assert "autoGhostBayesianFilterEnabled" not in out["bayesian"]["gates"]


def test_presets_do_not_force_bayesian_filter():
    presets = build_strictness_presets()
    assert set(presets.keys()) == {"relaxed", "conservative", "strict"}
    for preset in presets.values():
        gates = preset["gates"]
        # Decoupling: preset never toggles the filter (None -> store keeps the
        # user's current setting via the `??` fallback in applyGhostProtocolGates).
        assert gates.get("autoGhostBayesianFilterEnabled") is None
    # Floor values intact (percent form).
    assert presets["relaxed"]["gates"]["autoGhostBayesianMinProbability"] == 50.0
    assert presets["conservative"]["gates"]["autoGhostBayesianMinProbability"] == 53.5
    assert presets["strict"]["gates"]["autoGhostBayesianMinProbability"] == 58.0
    # "Balanced" rename (secondary generic presets).
    assert presets["conservative"]["name"] == "Balanced"


def test_presets_strict_floor_escalation_unchanged():
    presets = build_strictness_presets(final_report={"win_rate": 40.0})
    assert presets["strict"]["gates"]["autoGhostBayesianMinProbability"] == 60.0


# ---------------------------------------------------------------------------
# Finalize integration (CalibrationHarness from the calibration contract suite)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_finalize_attaches_calibrated_gates():
    from test_calibration_contracts import CalibrationHarness

    harness = CalibrationHarness()
    try:
        await harness.calibration.start()
        assert harness.calibration.state == "RUNNING"

        # 3W/1L evidence (N=4 < MILESTONE_SIZE=12 → no background milestone task).
        outcomes = [("win", 0.85), ("win", 0.85), ("win", 0.85), ("loss", -1.0)]
        for i, (outcome, profit) in enumerate(outcomes):
            harness.auto_ghost.report_outcome(
                f"g{i}", outcome, profit,
                asset="EURUSD_otc",
                entry_context={"regime_label": "RANGE_BOUND", "expiration_seconds": 60},
            )

        await harness.calibration._finalize(final_state="DONE")
        assert harness.calibration._final_report["final_state"] == "DONE"

        gates = harness.calibration._final_report["calibrated_gates"]
        assert gates["evidence"]["settled"] == 4
        assert gates["evidence"]["win_rate"] == 75.0
        assert isinstance(gates["bayesian"]["ready"], bool)
        # Tier A changelog has no applied changes in this minimal run —
        # the card must not invent families.
        assert gates["families"] == {}
    finally:
        harness.cleanup()


def test_build_calibrated_gates_synthesize_missing_all_families():
    """Verify that when synthesize_missing=True with N>=8 settled trades,
    all 6 gate families (zscore, volatility, liquidity, confidence, manipulation, regimes)
    are populated with concrete values, regimes are extracted, and Bayesian is optional.
    """
    final_report = {
        "settled_wins": 8,
        "settled_losses": 4,
        "settled_voids": 0,
        "win_rate": 66.7,
        "calibration_pnl": 2.8,
    }
    settled_trades = [
        {"outcome": "win", "entry_context": {"regime_label": "RANGE_BOUND"}},
        {"outcome": "win", "entry_context": {"regime_label": "RANGE_BOUND"}},
        {"outcome": "win", "entry_context": {"regime_label": "TREND_PULLBACK"}},
        {"outcome": "loss", "entry_context": {"regime_label": "CHOPPY"}},
    ]
    out = build_calibrated_gates(
        [],
        final_report=final_report,
        synthesize_missing=True,
        settled_trades=settled_trades,
    )
    families = out["families"]
    assert "zscore" in families
    assert families["zscore"]["gates"]["ghostMinZScoreEnabled"] is True
    assert families["zscore"]["gates"]["ghostMinZScore"] == -2.0
    assert families["zscore"]["gates"]["ghostMaxZScore"] == 2.0

    assert "volatility" in families
    assert families["volatility"]["gates"]["autoGhostVolatilityGateEnabled"] is True
    assert families["volatility"]["gates"]["minVolatilityScore"] == 15.0
    assert families["volatility"]["gates"]["maxVolatilityScore"] == 85.0

    assert "liquidity" in families
    assert families["liquidity"]["gates"]["autoGhostLiquidityGateEnabled"] is True
    assert families["liquidity"]["gates"]["minLiquidityScore"] == 15.0
    assert families["liquidity"]["gates"]["maxLiquidityScore"] == 85.0

    assert "confidence" in families
    assert families["confidence"]["gates"]["ghostMinConfidenceEnabled"] is True
    assert families["confidence"]["gates"]["ghostMinConfidence"] == 70.0

    assert "manipulation" in families
    assert families["manipulation"]["gates"]["autoGhostManipulationSeverityThreshold"] == 0.35

    assert "regimes" in families
    assert families["regimes"]["gates"]["ghostRegimeGateEnabled"] is True
    assert "RANGE_BOUND" in families["regimes"]["gates"]["ghostAllowedRegimes"]
    assert "TREND_PULLBACK" in families["regimes"]["gates"]["ghostAllowedRegimes"]
    assert "CHOPPY" not in families["regimes"]["gates"]["ghostAllowedRegimes"]

    # Bayesian floor is provided, but enabled is NOT part of payload (optional)
    assert out["bayesian"]["gates"]["autoGhostBayesianMinProbability"] == 50.0
    assert "autoGhostBayesianFilterEnabled" not in out["bayesian"]["gates"]


def test_build_calibrated_gates_asset_profiling_and_blacklist():
    """Verify that settled trades are profiled per-asset to isolate Prime Assets
    and synthesize a Recommended Blacklist for toxic/manipulated pairs.
    """
    final_report = {
        "settled_wins": 6,
        "settled_losses": 4,
        "settled_voids": 0,
        "win_rate": 60.0,
        "calibration_pnl": 2.0,
    }
    settled_trades = [
        # EURUSD: 3 wins, 0 losses -> Prime
        {"asset": "EURUSD_otc", "outcome": "win", "pnl": 0.85, "entry_context": {"manipulation_score": 0.05}},
        {"asset": "EURUSD_otc", "outcome": "win", "pnl": 0.85, "entry_context": {"manipulation_score": 0.08}},
        {"asset": "EURUSD_otc", "outcome": "win", "pnl": 0.85, "entry_context": {"manipulation_score": 0.02}},
        # EURCHF: 0 wins, 3 losses, high manipulation -> Toxic Hazard
        {"asset": "EURCHF_otc", "outcome": "loss", "pnl": -1.0, "entry_context": {"manipulation_score": 0.45}},
        {"asset": "EURCHF_otc", "outcome": "loss", "pnl": -1.0, "entry_context": {"manipulation_score": 0.50}},
        {"asset": "EURCHF_otc", "outcome": "loss", "pnl": -1.0, "entry_context": {"manipulation_score": 0.40}},
        # GBPUSD: 3 wins, 1 loss -> Prime
        {"asset": "GBPUSD_otc", "outcome": "win", "pnl": 0.85, "entry_context": {"manipulation_score": 0.10}},
        {"asset": "GBPUSD_otc", "outcome": "win", "pnl": 0.85, "entry_context": {"manipulation_score": 0.12}},
        {"asset": "GBPUSD_otc", "outcome": "win", "pnl": 0.85, "entry_context": {"manipulation_score": 0.09}},
        {"asset": "GBPUSD_otc", "outcome": "loss", "pnl": -1.0, "entry_context": {"manipulation_score": 0.15}},
    ]
    out = build_calibrated_gates(
        [],
        final_report=final_report,
        settled_trades=settled_trades,
    )

    assert "EURUSD_otc" in out["prime_assets"]
    assert "GBPUSD_otc" in out["prime_assets"]
    assert out["recommended_blacklist"] == ["EURCHF_otc"]
    
    assert "assets" in out["families"]
    asset_fam = out["families"]["assets"]
    assert asset_fam["gates"]["ghostBlacklist"] == ["EURCHF_otc"]
    assert "EURCHF_otc" in asset_fam["rationale"]


def test_build_calibrated_gates_clean_assets_no_blacklist():
    """Verify that when no assets are toxic, recommended_blacklist is empty
    and the assets family is not forced into the payload.
    """
    final_report = {
        "settled_wins": 5,
        "settled_losses": 1,
        "settled_voids": 0,
        "win_rate": 83.3,
        "calibration_pnl": 3.25,
    }
    settled_trades = [
        {"asset": "EURUSD_otc", "outcome": "win", "pnl": 0.85, "entry_context": {"manipulation_score": 0.05}},
        {"asset": "EURUSD_otc", "outcome": "win", "pnl": 0.85, "entry_context": {"manipulation_score": 0.06}},
        {"asset": "GBPUSD_otc", "outcome": "win", "pnl": 0.85, "entry_context": {"manipulation_score": 0.10}},
        {"asset": "GBPUSD_otc", "outcome": "loss", "pnl": -1.0, "entry_context": {"manipulation_score": 0.12}},
    ]
    out = build_calibrated_gates(
        [],
        final_report=final_report,
        settled_trades=settled_trades,
    )

    assert "EURUSD_otc" in out["prime_assets"]
    assert out["recommended_blacklist"] == []
    assert "assets" not in out["families"]


