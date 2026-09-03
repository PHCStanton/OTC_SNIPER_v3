"""Phase 3 — Calibration Mode tiered autonomy (pure enforcement).

Server-side whitelist, one gate-family per milestone, catastrophic-evidence
rule (REV2), raise-only manipulation, regime N>=20 guard. No I/O, no AI.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from .auto_ghost import (
    CALIBRATION_GATE_FAMILIES,
    CALIBRATION_TIER_A_FIELDS,
    CALIBRATION_TIER_B_FIELDS,
)

logger = logging.getLogger(__name__)

# REV2: 0–2 wins out of 12 is catastrophic (≤16.7% WR on a full milestone).
CATASTROPHIC_MAX_WINS_PER_12 = 2
MILESTONE_SIZE = 12
REGIME_MIN_N = 20
BAYESIAN_LO = 0.50
BAYESIAN_HI = 0.90


def family_for_field(field: str) -> str | None:
    for name, members in CALIBRATION_GATE_FAMILIES.items():
        if field in members:
            return name
    return None


def is_catastrophic(evidence_n: int, wins: int, losses: int) -> bool:
    """True only for unambiguous wipeouts on a full 12-trade milestone."""
    total = int(wins) + int(losses)
    if total < MILESTONE_SIZE or int(evidence_n) < MILESTONE_SIZE:
        return False
    return int(wins) <= CATASTROPHIC_MAX_WINS_PER_12


def parse_autonomy_payload(text: str) -> dict[str, Any]:
    """Extract the JSON object from an AI response. Fail loud on garbage."""
    if not text or not str(text).strip():
        return {"tier_a_changes": [], "tier_b_proposals": [], "observations": []}
    blob = str(text)
    match = re.search(r"```json\s*(\{.*?\})\s*```", blob, re.DOTALL | re.IGNORECASE)
    if not match:
        match = re.search(r"(\{.*\})", blob, re.DOTALL)
    if not match:
        logger.warning("Calibration autonomy: no JSON object in AI response")
        return {"tier_a_changes": [], "tier_b_proposals": [], "observations": []}
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        logger.warning("Calibration autonomy: invalid JSON: %s", exc)
        return {"tier_a_changes": [], "tier_b_proposals": [], "observations": []}
    if not isinstance(parsed, dict):
        return {"tier_a_changes": [], "tier_b_proposals": [], "observations": []}
    return {
        "tier_a_changes": _as_change_list(parsed.get("tier_a_changes")),
        "tier_b_proposals": _as_change_list(parsed.get("tier_b_proposals")),
        "observations": _as_observation_list(parsed.get("observations")),
    }


def enforce_milestone(
    payload: dict[str, Any],
    *,
    current: dict[str, Any],
    locked_fields: set[str],
    settled_wins: int,
    settled_losses: int,
    regime_counts: dict[str, int] | None = None,
    is_first_milestone: bool = False,
    apply_tier_a: bool = True,
) -> dict[str, Any]:
    """Filter AI output to the legal surface. Never mutates config itself."""
    regime_counts = regime_counts or {}
    catastrophic = is_catastrophic(
        settled_wins + settled_losses, settled_wins, settled_losses
    )
    applied: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for item in _as_change_list(payload.get("tier_a_changes")):
        field = item["field"]
        # R2-4 (M-4): Tier B-classified fields (amount / expiration_seconds)
        # are PROPOSE-ONLY — never auto-applied by Tier A, and never rejected
        # as "locked". True locked internals (mode, block_on_manipulation, ...
        # not in CALIBRATION_TIER_B_FIELDS) still reject below.
        if field in CALIBRATION_TIER_B_FIELDS:
            proposals.append({**item, "requires_confirm": True, "reason": "tier_b_route"})
            continue
        if field in locked_fields:
            rejected.append({**item, "reason": "locked"})
            continue
        if field not in CALIBRATION_TIER_A_FIELDS:
            if field in CALIBRATION_TIER_B_FIELDS:
                proposals.append(item)
            else:
                rejected.append({**item, "reason": "unknown_field"})
            continue
        if field == "manipulation_severity_threshold":
            try:
                new_v = float(item["new"])
                old_v = float(current.get(field) or 0.0)
            except (TypeError, ValueError):
                rejected.append({**item, "reason": "invalid_value"})
                continue
            if new_v < old_v:
                rejected.append({**item, "reason": "manipulation_raise_only"})
                continue
        if field == "bayesian_min_probability":
            try:
                item = {**item, "new": max(BAYESIAN_LO, min(BAYESIAN_HI, float(item["new"])))}
            except (TypeError, ValueError):
                rejected.append({**item, "reason": "invalid_value"})
                continue
        if field in {"regime_gate_enabled", "allowed_regimes"}:
            if is_first_milestone:
                rejected.append({**item, "reason": "regime_not_on_first_milestone"})
                continue
            if any(int(n) < REGIME_MIN_N for n in regime_counts.values()) or not regime_counts:
                rejected.append({**item, "reason": "regime_n_below_20"})
                continue
        if not apply_tier_a or not catastrophic:
            proposals.append({**item, "demoted": "not_catastrophic" if apply_tier_a else "final_report_only"})
            continue
        applied.append(item)

    for item in _as_change_list(payload.get("tier_b_proposals")):
        field = item["field"]
        if field in locked_fields or field not in CALIBRATION_TIER_B_FIELDS:
            rejected.append({**item, "reason": "tier_b_rejected"})
            continue
        proposals.append(item)

    # Max ONE gate family auto-applied.
    if applied:
        keep_family = family_for_field(applied[0]["field"])
        kept: list[dict[str, Any]] = []
        for item in applied:
            fam = family_for_field(item["field"])
            if fam == keep_family:
                kept.append(item)
            else:
                proposals.append({**item, "demoted": "one_family_per_milestone"})
        applied = kept

    return {
        "applied": applied,
        "proposals": proposals,
        "rejected": rejected,
        "observations": _as_observation_list(payload.get("observations")),
        "catastrophic": catastrophic,
    }


def guardian_proposals(
    trades: list[dict[str, Any]],
    *,
    already_emitted: set[str],
    min_n: int = 20,
) -> list[dict[str, Any]]:
    """Deterministic N>=20 bucket suggestions. Propose-only. One family max."""
    by_regime: dict[str, list[str]] = {}
    for trade in trades:
        outcome = str(trade.get("outcome") or "").lower()
        if outcome not in {"win", "loss"}:
            continue
        ctx = trade.get("entry_context") or {}
        regime = str(ctx.get("regime_label") or trade.get("regime_label") or "UNKNOWN")
        by_regime.setdefault(regime, []).append(outcome)

    for regime, outcomes in sorted(by_regime.items(), key=lambda kv: len(kv[1]), reverse=True):
        family = f"regimes:{regime}"
        if family in already_emitted:
            continue
        if len(outcomes) < min_n:
            continue
        wins = sum(1 for o in outcomes if o == "win")
        wr = wins / len(outcomes)
        if wr >= 0.45:
            continue
        remaining = [r for r in by_regime if r != regime]
        if not remaining:
            # R2-3 (M-3): never propose a whitelist that degrades to allow-all.
            logger.info(
                "Guardian: skipping regime-drop proposal for %s — it is the last "
                "observed regime; an empty allowed_regimes would degrade to allow-all.",
                regime,
            )
            continue
        return [{
            "field": "allowed_regimes",
            "family": "regimes",
            "bucket": family,
            "new": remaining,
            "rationale": (
                f"Drop {regime}: {wins}/{len(outcomes)} wins "
                f"({wr * 100:.1f}% WR, N={len(outcomes)} ≥ {min_n})"
            ),
            "evidence_n": len(outcomes),
        }]
    return []


PRIOR_TRANSFER_MIN_N = 10
PRIOR_TRANSFER_DIVERGENCE_PP = 8.0


def guardian_prior_transfer(
    trades: list[dict[str, Any]],
    baseline: dict[str, Any] | None,
    *,
    already_emitted: set[str],
    min_n: int = PRIOR_TRANSFER_MIN_N,
    divergence_pp: float = PRIOR_TRANSFER_DIVERGENCE_PP,
) -> list[dict[str, Any]]:
    """Flag live WR divergence vs the KB warm-start baseline. Propose-only."""
    if not baseline or baseline.get("expected_wr") is None:
        return []
    bucket = "warm_start:overall"
    if bucket in already_emitted:
        return []
    settled = [
        str(t.get("outcome") or "").lower()
        for t in trades
        if str(t.get("outcome") or "").lower() in {"win", "loss"}
    ]
    if len(settled) < min_n:
        return []
    wins = sum(1 for o in settled if o == "win")
    live_wr = wins / len(settled) * 100.0
    expected = float(baseline["expected_wr"])
    delta = live_wr - expected
    if abs(delta) < float(divergence_pp):
        return []
    direction = "below" if delta < 0 else "above"
    return [{
        "kind": "prior_transfer_failure",
        "field": None,
        "family": "warm_start",
        "bucket": bucket,
        "new": None,
        "live_wr": round(live_wr, 2),
        "expected_wr": round(expected, 2),
        "delta_pp": round(delta, 2),
        "rationale": (
            f"Live WR {live_wr:.1f}% is {direction} KB warm-start "
            f"{expected:.1f}% (Δ {delta:+.1f}pp, N={len(settled)} ≥ {min_n}) "
            f"— prior-transfer failure; re-run calibration advised"
        ),
        "evidence_n": len(settled),
    }]


def _as_change_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "").strip()
        if not field or "new" not in item:
            continue
        out.append({
            "field": field,
            "new": item.get("new"),
            "rationale": str(item.get("rationale") or ""),
            "evidence_n": int(item.get("evidence_n") or 0),
        })
    return out


def _as_observation_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").upper()
        text = str(item.get("text") or "").strip()
        if kind not in {"USER_SUGGESTION", "DEV_SUGGESTION"} or not text:
            continue
        out.append({"kind": kind, "text": text})
    return out
