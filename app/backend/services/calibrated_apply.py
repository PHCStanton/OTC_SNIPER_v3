"""Calibrated Apply Gates (feat/ai_kb, 2026-09-04).

Compiles the post-calibration "Apply Calibrated Gates" payload from REAL
calibration evidence only:

- Tier A gate changes actually applied during the run (changelog
  ``tier_a_applied`` events, last-write-wins per field), grouped into gate
  families (Z-Score, Volatility, Liquidity, Regimes, Confidence, Manipulation).
- Guardian propose-only proposals (e.g. an ``allowed_regimes`` drop backed by
  N>=20 evidence) take precedence over weaker Tier A regime writes.
- Bayesian floor derived from calibration evidence; the ``enabled`` choice is
  left to the user — the card defaults it ON only when the 60s prior store is
  READY (``total_trades >= 500``). Bayesian is a CHOICE, never a preset side
  effect.

Pure functions except :func:`bayesian_prior_ready` (read-only prior store
check). Backend units (Bayesian 0.50-0.90 float) are converted to the
frontend 50-90 scale via ``ghost_protocol_profiles`` key naming; family gates
here are already frontend-keyed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)

# Mirrors shared.bayesian_protocol.compute_protocol_health READY threshold.
BAYESIAN_READY_MIN_TRADES = 500

# Backend AutoGhostConfig field -> frontend Apply-card key, aligned per family.
# Order matters: zip() pairs them (backend_field, frontend_key).
_FAMILY_FIELD_MAP: dict[str, tuple[tuple[str, str], ...]] = {
    "zscore": (
        ("min_zscore", "ghostMinZScore"),
        ("min_zscore_enabled", "ghostMinZScoreEnabled"),
        ("max_zscore", "ghostMaxZScore"),
        ("max_zscore_enabled", "ghostMaxZScoreEnabled"),
    ),
    "volatility": (
        ("volatility_gate_enabled", "autoGhostVolatilityGateEnabled"),
        ("min_volatility", "minVolatilityScore"),
        ("max_volatility", "maxVolatilityScore"),
    ),
    "liquidity": (
        ("liquidity_gate_enabled", "autoGhostLiquidityGateEnabled"),
        ("min_liquidity", "minLiquidityScore"),
        ("max_liquidity", "maxLiquidityScore"),
    ),
    "regimes": (
        ("regime_gate_enabled", "ghostRegimeGateEnabled"),
        ("allowed_regimes", "ghostAllowedRegimes"),
    ),
    "confidence": (
        ("min_confidence", "ghostMinConfidence"),
        ("min_confidence_enabled", "ghostMinConfidenceEnabled"),
    ),
    "manipulation": (
        ("manipulation_severity_threshold", "autoGhostManipulationSeverityThreshold"),
    ),
    "assets": (
        ("blacklist_assets", "ghostBlacklist"),
    ),
}


def build_calibrated_gates(
    changelog: list[dict[str, Any]] | None,
    *,
    final_report: Mapping[str, Any] | None = None,
    proposals: list[dict[str, Any]] | None = None,
    bayesian_ready: bool = False,
    synthesize_missing: bool = False,
    settled_trades: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compile the frontend "Apply Calibrated Gates" payload (pure function).

    Consumes applied Tier A changes and Guardian/AI proposals.
    When synthesize_missing=True, populates solid baseline starting values
    for all gate families based on session win rate and settled trades evidence.
    """
    applied: dict[str, dict[str, Any]] = {}
    for entry in changelog or []:
        if not isinstance(entry, dict) or entry.get("event") != "tier_a_applied":
            continue
        field = str(entry.get("field") or "")
        if field and entry.get("new") is not None:
            applied[field] = entry  # last-write-wins (changelog is append-ordered)

    # Ingest AI / milestone proposals for any fields not already modified by in-flight Tier A
    for proposal in proposals or []:
        if not isinstance(proposal, dict):
            continue
        field = str(proposal.get("field") or "")
        if field and field != "allowed_regimes" and proposal.get("new") is not None and field not in applied:
            applied[field] = proposal

    families: dict[str, dict[str, Any]] = {}
    for fam, pairs in _FAMILY_FIELD_MAP.items():
        gates: dict[str, Any] = {}
        latest: dict[str, Any] | None = None
        for backend_field, frontend_key in pairs:
            hit = applied.get(backend_field)
            if hit is None:
                continue
            value = hit["new"]
            # F-1: never surface an empty allowed_regimes (would degrade to
            # "allow all regimes" downstream). Mirrors the proposal-path guard.
            # An empty list contributes no gate; if the family then has no
            # gates it is omitted entirely — safer than emitting [].
            if backend_field == "allowed_regimes" and not (
                isinstance(value, list) and value
            ):
                continue
            gates[frontend_key] = value
            if latest is None or int(hit.get("epoch", 0) or 0) >= int(latest.get("epoch", 0) or 0):
                latest = hit
        if gates:
            changes_count = len(gates)
            if synthesize_missing:
                if fam == "zscore":
                    gates.setdefault("ghostMinZScoreEnabled", True)
                    gates.setdefault("ghostMaxZScoreEnabled", True)
                elif fam == "volatility":
                    gates.setdefault("autoGhostVolatilityGateEnabled", True)
                elif fam == "liquidity":
                    gates.setdefault("autoGhostLiquidityGateEnabled", True)
                elif fam == "confidence":
                    gates.setdefault("ghostMinConfidenceEnabled", True)
                elif fam == "regimes" and gates.get("ghostAllowedRegimes"):
                    gates.setdefault("ghostRegimeGateEnabled", True)

            families[fam] = {
                "gates": gates,
                "rationale": latest.get("rationale") if latest else None,
                "evidence_n": latest.get("evidence_n") if latest else None,
                "changes": changes_count,
            }

    # Guardian proposals (propose-only, N>=20 evidence) outrank weaker
    # Tier A regime writes. The proposal itself guarantees a non-empty
    # whitelist (calibration_autonomy R2-3/M-3 guard).
    for proposal in proposals or []:
        if not isinstance(proposal, dict):
            continue
        if str(proposal.get("field") or "") != "allowed_regimes":
            continue
        new_regimes = proposal.get("new")
        if not isinstance(new_regimes, list) or not new_regimes:
            continue
        families["regimes"] = {
            "gates": {
                "ghostRegimeGateEnabled": True,
                "ghostAllowedRegimes": [str(r).upper() for r in new_regimes],
            },
            "rationale": proposal.get("rationale"),
            "evidence_n": proposal.get("evidence_n"),
            "changes": families.get("regimes", {}).get("changes", 0),
            "proposal": True,
        }
        break

    settled_n = 0
    wr = None
    if final_report:
        settled_n = int(final_report.get("settled_wins", 0) or 0) + int(
            final_report.get("settled_losses", 0) or 0
        )
        try:
            wr = float(final_report["win_rate"]) if final_report.get("win_rate") is not None else None
        except (TypeError, ValueError):
            wr = None

    if synthesize_missing and settled_n >= 8:

        # Tier 1: Favorable (WR >= 56%), Tier 2: Balanced (45% <= WR < 56%), Tier 3: Strict (WR < 45%)
        if "zscore" not in families:
            min_z = -2.0 if (wr is not None and wr >= 56.0) else (-1.0 if (wr is not None and wr < 45.0) else -1.5)
            max_z = 2.0 if (wr is not None and wr >= 56.0) else (1.0 if (wr is not None and wr < 45.0) else 1.5)
            families["zscore"] = {
                "gates": {
                    "ghostMinZScoreEnabled": True,
                    "ghostMinZScore": min_z,
                    "ghostMaxZScoreEnabled": True,
                    "ghostMaxZScore": max_z,
                },
                "rationale": f"Calibrated Z-score bounds [±{max_z}] tailored for session win rate ({wr or '—'}%)",
                "evidence_n": settled_n,
                "changes": 4,
            }

        if "volatility" not in families:
            min_v = 15.0 if (wr is not None and wr >= 56.0) else (30.0 if (wr is not None and wr < 45.0) else 20.0)
            max_v = 85.0 if (wr is not None and wr >= 56.0) else (70.0 if (wr is not None and wr < 45.0) else 80.0)
            families["volatility"] = {
                "gates": {
                    "autoGhostVolatilityGateEnabled": True,
                    "minVolatilityScore": min_v,
                    "maxVolatilityScore": max_v,
                },
                "rationale": f"Calibrated volatility gate [{min_v}%–{max_v}%] for session stability",
                "evidence_n": settled_n,
                "changes": 3,
            }

        if "liquidity" not in families:
            min_l = 15.0 if (wr is not None and wr >= 56.0) else (35.0 if (wr is not None and wr < 45.0) else 20.0)
            max_l = 85.0 if (wr is not None and wr >= 56.0) else (85.0 if (wr is not None and wr < 45.0) else 80.0)
            families["liquidity"] = {
                "gates": {
                    "autoGhostLiquidityGateEnabled": True,
                    "minLiquidityScore": min_l,
                    "maxLiquidityScore": max_l,
                },
                "rationale": f"Calibrated liquidity gate [{min_l}%–{max_l}%] for tick rate health",
                "evidence_n": settled_n,
                "changes": 3,
            }

        if "confidence" not in families:
            min_c = 70.0 if (wr is not None and wr >= 56.0) else (80.0 if (wr is not None and wr < 45.0) else 75.0)
            families["confidence"] = {
                "gates": {
                    "ghostMinConfidenceEnabled": True,
                    "ghostMinConfidence": min_c,
                },
                "rationale": f"Calibrated minimum confidence (≥{min_c}%) from calibration performance",
                "evidence_n": settled_n,
                "changes": 2,
            }

        if "manipulation" not in families:
            thresh = 0.30 if (wr is not None and wr < 45.0) else 0.35
            families["manipulation"] = {
                "gates": {
                    "autoGhostManipulationSeverityThreshold": thresh,
                },
                "rationale": f"Calibrated manipulation severity cap (≤{thresh}) for broker protection",
                "evidence_n": settled_n,
                "changes": 1,
            }

        if "regimes" not in families:
            # Check observed regimes from settled trades
            regime_wins: dict[str, int] = {}
            regime_losses: dict[str, int] = {}
            for t in (settled_trades or []):
                if not isinstance(t, dict):
                    continue
                outcome = str(t.get("outcome") or "").lower()
                ctx = t.get("entry_context") or {}
                regime = str(ctx.get("regime_label") or t.get("regime_label") or "").upper()
                if not regime or regime in {"UNKNOWN", "NONE"}:
                    continue
                if outcome == "win":
                    regime_wins[regime] = regime_wins.get(regime, 0) + 1
                elif outcome == "loss":
                    regime_losses[regime] = regime_losses.get(regime, 0) + 1

            winning_regimes = [
                r for r, w in regime_wins.items()
                if w > 0 and w >= regime_losses.get(r, 0)
            ]
            if winning_regimes:
                families["regimes"] = {
                    "gates": {
                        "ghostRegimeGateEnabled": True,
                        "ghostAllowedRegimes": sorted(winning_regimes),
                    },
                    "rationale": f"Whitelisted winning regimes observed in calibration: {', '.join(sorted(winning_regimes))}",
                    "evidence_n": sum(regime_wins.values()) + sum(regime_losses.values()),
                    "changes": 2,
                }
            else:
                families["regimes"] = {
                    "gates": {
                        "ghostRegimeGateEnabled": False,
                        "ghostAllowedRegimes": [],
                    },
                    "rationale": "No dominant winning regimes identified yet — regime gate remains open.",
                    "evidence_n": settled_n,
                    "changes": 2,
                }

    prime_assets: list[str] = []
    recommended_blacklist: list[str] = []
    per_asset: dict[str, dict[str, Any]] = {}

    if "assets" not in families and settled_trades:
        asset_stats: dict[str, dict[str, Any]] = {}
        for t in (settled_trades or []):
            if not isinstance(t, dict):
                continue
            asset = str(t.get("asset") or "").strip()
            if not asset:
                continue
            outcome = str(t.get("outcome") or "").lower()
            profit = float(t.get("profit") or t.get("simulated_profit") or t.get("pnl") or 0.0)

            manip = t.get("manipulation_at_entry") or t.get("manipulation_score")
            if not manip and isinstance(t.get("entry_context"), dict):
                manip = t["entry_context"].get("manipulation_score") or t["entry_context"].get("manipulation")
            manip_score = 0.0
            if isinstance(manip, dict):
                manip_score = float(manip.get("push_snap") or manip.get("severity") or 0.0)
            elif isinstance(manip, (int, float)):
                manip_score = float(manip)

            if asset not in asset_stats:
                asset_stats[asset] = {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "profit": 0.0,
                    "manip_scores": [],
                }
            stat = asset_stats[asset]
            stat["trades"] += 1
            stat["profit"] += profit
            stat["manip_scores"].append(manip_score)
            if outcome == "win":
                stat["wins"] += 1
            elif outcome == "loss":
                stat["losses"] += 1

        for asset, s in asset_stats.items():
            trades = s["trades"]
            wins = s["wins"]
            losses = s["losses"]
            wr_asset = (wins / trades * 100.0) if trades else 0.0
            avg_manip = (sum(s["manip_scores"]) / len(s["manip_scores"])) if s["manip_scores"] else 0.0
            pnl = round(s["profit"], 2)

            per_asset[asset] = {
                "trades": trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round(wr_asset, 1),
                "net_pnl": pnl,
                "avg_manipulation": round(avg_manip, 3),
            }

            # Hazard / Toxic criteria:
            # 1. Losses >= 2 and win_rate <= 25% (or 0 wins with >= 2 trades)
            # 2. Or losses > wins and avg_manipulation >= 0.25
            if (losses >= 2 and wr_asset <= 25.0) or (losses > wins and avg_manip >= 0.25):
                recommended_blacklist.append(asset)
            elif wr_asset >= 60.0 and avg_manip < 0.20 and pnl > 0:
                prime_assets.append(asset)

        if recommended_blacklist:
            families["assets"] = {
                "gates": {
                    "ghostBlacklist": sorted(recommended_blacklist),
                },
                "rationale": f"Auto-blacklist {len(recommended_blacklist)} toxic/manipulated assets: {', '.join(sorted(recommended_blacklist))}",
                "evidence_n": len(settled_trades or []),
                "changes": len(recommended_blacklist),
                "prime_assets": sorted(prime_assets),
                "recommended_blacklist": sorted(recommended_blacklist),
                "per_asset": per_asset,
            }

    bayes_hit = applied.get("bayesian_min_probability")
    floor = bayes_hit["new"] if bayes_hit is not None else _suggest_bayesian_floor(
        (final_report or {}).get("win_rate"),
    )
    bayesian: dict[str, Any] = {
        "ready": bool(bayesian_ready),
        # Floor suggestion only — `enabled` is the user's explicit choice on
        # the card (default ON solely when the prior store is READY).
        "gates": (
            {"autoGhostBayesianMinProbability": round(float(floor) * 100.0, 1)}
            if floor is not None
            else None
        ),
    }

    evidence: dict[str, Any] | None = None
    if final_report:
        settled = int(final_report.get("settled_wins", 0) or 0) + int(
            final_report.get("settled_losses", 0) or 0
        )
        evidence = {
            "settled": settled,
            "win_rate": final_report.get("win_rate"),
            "voids": int(final_report.get("settled_voids", 0) or 0),
            "pnl": final_report.get("calibration_pnl"),
        }

    return {
        "families": families,
        "bayesian": bayesian,
        "evidence": evidence,
        "proposals": [p for p in (proposals or []) if isinstance(p, dict)],
        "prime_assets": sorted(prime_assets),
        "recommended_blacklist": sorted(recommended_blacklist),
        "asset_performance": per_asset,
    }


def _suggest_bayesian_floor(win_rate: Any) -> float | None:
    """Deterministic floor suggestion from the calibration win rate (percent).

    Mirrors the alignment thresholds (ghost_protocol_profiles):
    WR < 45% -> 0.58, WR >= 56% -> 0.50, otherwise 0.535.
    """
    try:
        wr = float(win_rate)
    except (TypeError, ValueError):
        return 0.535
    if wr < 45.0:
        return 0.58
    if wr >= 56.0:
        return 0.50
    return 0.535


def bayesian_prior_ready(priors_path: str | Path | None = None) -> bool:
    """True when the 60s Bayesian prior store is READY (N >= 500 trades).

    Read-only; any failure (missing/corrupt/unreadable store) fails soft to
    False with a loud warning — the apply card then defaults the Bayesian
    checkbox OFF, which is always safe.
    """
    try:
        from shared.bayesian_prior_store import BayesianPriorStore
        from .extensions.bayesian_signal_filter import _DEFAULT_PRIORS_FILE_60S

        path = Path(priors_path) if priors_path is not None else _DEFAULT_PRIORS_FILE_60S
        doc = BayesianPriorStore(path).read()
        total = int(doc.get("total_trades", 0) or 0)
        return total >= BAYESIAN_READY_MIN_TRADES
    except Exception as exc:
        logger.warning("Bayesian prior readiness check failed (treating as NOT READY): %s", exc)
        return False
