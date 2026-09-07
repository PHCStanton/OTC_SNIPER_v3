"""Phase 5 — strictness profiles, alignment, and market-drift detection.

Pure functions. No I/O. Backend units: Bayesian 0.50–0.90 float, payout percent.
Frontend Apply cards receive the converted gate map (Bayesian as 50–90).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared.utc_time_blocks import trade_entry_unix, utc_4h_block

STRICTNESS_KEYS = ("relaxed", "conservative", "strict")

# Frontend keys loadGhostProtocol must apply (M8). Missing any of these is a silent no-op.
FRONTEND_GATE_KEYS = (
    "ghostMinZScore",
    "ghostMinZScoreEnabled",
    "ghostMaxZScore",
    "ghostMaxZScoreEnabled",
    "ghostRegimeGateEnabled",
    "ghostAllowedRegimes",
    "autoGhostVolatilityGateEnabled",
    "minVolatilityScore",
    "maxVolatilityScore",
    "autoGhostLiquidityGateEnabled",
    "minLiquidityScore",
    "maxLiquidityScore",
    "autoGhostBayesianMinProbability",
    "autoGhostMinimumPayout",
    "ghostAmount",
    "autoGhostMaxConcurrentTrades",
    "ghostMinConfidence",
    "ghostMinConfidenceEnabled",
    "autoGhostManipulationSeverityThreshold",
)

DRIFT_Z_THRESHOLD = 2.0
DRIFT_MIN_N = 8
DRIFT_MIN_DIMENSIONS = 2
ALIGNMENT_RELAXED_WR = 56.0
ALIGNMENT_STRICT_WR = 49.0
FEATURE_DIMS = ("volatility", "liquidity", "manipulation", "z_score")

# Concrete gate-delta sets (backend AutoGhostConfig units).
_BACKEND_PRESETS: dict[str, dict[str, Any]] = {
    "relaxed": {
        "label": "Relaxed",
        "rationale": "Favorable pocket (high vol / high liq / low manip) — wider z, higher concurrency, lower Bayesian floor.",
        "min_zscore_enabled": True,
        "min_zscore": -2.5,
        "max_zscore_enabled": True,
        "max_zscore": 2.5,
        "regime_gate_enabled": False,
        "allowed_regimes": [],
        "volatility_gate_enabled": False,
        "min_volatility": 0.0,
        "max_volatility": 100.0,
        "liquidity_gate_enabled": False,
        "min_liquidity": 0.0,
        "max_liquidity": 100.0,
        "bayesian_min_probability": 0.50,
        "minimum_payout_pct": 85.0,
        "amount": 1.0,
        "max_concurrent_trades": 3,
        "min_confidence_enabled": True,
        "min_confidence": 70.0,
        "manipulation_severity_threshold": 0.35,
    },
    "conservative": {
        "label": "Balanced",
        "rationale": "Mixed readings — near-baseline gates.",
        "min_zscore_enabled": True,
        "min_zscore": -1.5,
        "max_zscore_enabled": True,
        "max_zscore": 1.5,
        "regime_gate_enabled": False,
        "allowed_regimes": [],
        "volatility_gate_enabled": True,
        "min_volatility": 20.0,
        "max_volatility": 80.0,
        "liquidity_gate_enabled": True,
        "min_liquidity": 20.0,
        "max_liquidity": 80.0,
        "bayesian_min_probability": 0.535,
        "minimum_payout_pct": 88.0,
        "amount": 1.0,
        "max_concurrent_trades": 2,
        "min_confidence_enabled": True,
        "min_confidence": 75.0,
        "manipulation_severity_threshold": 0.35,
    },
    "strict": {
        "label": "Strict",
        "rationale": "Adverse HTF / thin liquidity / high manipulation — tight z, 1 concurrent, elevated Bayesian floor.",
        "min_zscore_enabled": True,
        "min_zscore": -1.0,
        "max_zscore_enabled": True,
        "max_zscore": 1.0,
        "regime_gate_enabled": True,
        "allowed_regimes": ["RANGE_BOUND", "TREND_REVERSAL"],
        "volatility_gate_enabled": True,
        "min_volatility": 30.0,
        "max_volatility": 70.0,
        "liquidity_gate_enabled": True,
        "min_liquidity": 40.0,
        "max_liquidity": 100.0,
        "bayesian_min_probability": 0.58,
        "minimum_payout_pct": 90.0,
        "amount": 1.0,
        "max_concurrent_trades": 1,
        "min_confidence_enabled": True,
        "min_confidence": 80.0,
        "manipulation_severity_threshold": 0.45,
    },
}


def backend_gates_to_frontend(gates: Mapping[str, Any]) -> dict[str, Any]:
    """Convert AutoGhostConfig-native gates to Zustand Apply-card keys."""
    bayesian = gates.get("bayesian_min_probability")
    bayesian_ui = round(float(bayesian) * 100.0, 1) if bayesian is not None else None
    return {
        "ghostMinZScore": gates.get("min_zscore"),
        "ghostMinZScoreEnabled": gates.get("min_zscore_enabled"),
        "ghostMaxZScore": gates.get("max_zscore"),
        "ghostMaxZScoreEnabled": gates.get("max_zscore_enabled"),
        "ghostRegimeGateEnabled": gates.get("regime_gate_enabled"),
        "ghostAllowedRegimes": list(gates.get("allowed_regimes") or []),
        "autoGhostVolatilityGateEnabled": gates.get("volatility_gate_enabled"),
        "minVolatilityScore": gates.get("min_volatility"),
        "maxVolatilityScore": gates.get("max_volatility"),
        "autoGhostLiquidityGateEnabled": gates.get("liquidity_gate_enabled"),
        "minLiquidityScore": gates.get("min_liquidity"),
        "maxLiquidityScore": gates.get("max_liquidity"),
        "autoGhostBayesianFilterEnabled": gates.get("bayesian_filter_enabled"),
        "autoGhostBayesianMinProbability": bayesian_ui,
        "autoGhostMinimumPayout": gates.get("minimum_payout_pct"),
        "ghostAmount": gates.get("amount"),
        "autoGhostMaxConcurrentTrades": gates.get("max_concurrent_trades"),
        "ghostMinConfidence": gates.get("min_confidence"),
        "ghostMinConfidenceEnabled": gates.get("min_confidence_enabled"),
        "autoGhostManipulationSeverityThreshold": gates.get("manipulation_severity_threshold"),
    }


def build_strictness_presets(*, final_report: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Three named presets. Optional calibration final-report can raise Strict Bayesian floor."""
    presets: dict[str, Any] = {}
    wr = None
    if final_report:
        try:
            wr = float(final_report["win_rate"]) if final_report.get("win_rate") is not None else None
        except (TypeError, ValueError):
            wr = None
    for key in STRICTNESS_KEYS:
        backend = dict(_BACKEND_PRESETS[key])
        if key == "strict" and wr is not None and wr < 45.0:
            backend["bayesian_min_probability"] = min(0.90, float(backend["bayesian_min_probability"]) + 0.02)
        frontend = backend_gates_to_frontend(backend)
        missing = [k for k in FRONTEND_GATE_KEYS if k not in frontend or frontend[k] is None]
        if missing:
            raise ValueError(f"Preset {key} missing frontend gate keys: {missing}")
        presets[key] = {
            "key": key,
            "name": backend["label"],
            "rationale": backend["rationale"],
            "gates": frontend,
        }
    return presets


def _manip_severity(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    if isinstance(raw, Mapping):
        vals = []
        for value in raw.values():
            try:
                vals.append(float(value))
            except (TypeError, ValueError):
                if value:
                    vals.append(1.0)
        return max(vals) if vals else 0.0
    return None


def extract_trade_features(trade: Mapping[str, Any]) -> dict[str, Any]:
    ctx = trade.get("entry_context") if isinstance(trade.get("entry_context"), Mapping) else {}
    mc = ctx.get("market_context") if isinstance(ctx.get("market_context"), Mapping) else {}
    unix = trade_entry_unix(trade)
    vol = mc.get("volatility_score")
    liq = mc.get("liquidity_score")
    z_raw = ctx.get("z_score")
    try:
        z_score = float(z_raw) if z_raw is not None else None
    except (TypeError, ValueError):
        z_score = None
    try:
        volatility = float(vol) if vol is not None else None
    except (TypeError, ValueError):
        volatility = None
    try:
        liquidity = float(liq) if liq is not None else None
    except (TypeError, ValueError):
        liquidity = None
    return {
        "volatility": volatility,
        "liquidity": liquidity,
        "manipulation": _manip_severity(ctx.get("manipulation")),
        "z_score": z_score,
        "utc_4h_block": utc_4h_block(unix) if unix is not None else None,
    }


def _mean_std(values: Sequence[float]) -> dict[str, Any]:
    n = len(values)
    if n == 0:
        return {"mean": None, "std": None, "n": 0}
    mean = sum(values) / n
    if n > 1:
        var = sum((x - mean) ** 2 for x in values) / (n - 1)
    else:
        var = 0.0
    return {"mean": round(mean, 6), "std": round(math.sqrt(var), 6), "n": n}


def compute_feature_centroids(trades: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[float]] = {dim: [] for dim in FEATURE_DIMS}
    by_block: dict[str, dict[str, list[float]]] = {}
    for trade in trades:
        feat = extract_trade_features(trade)
        for dim in FEATURE_DIMS:
            val = feat.get(dim)
            if val is None:
                continue
            buckets[dim].append(float(val))
            block = feat.get("utc_4h_block")
            if block is None:
                continue
            by_block.setdefault(str(block), {d: [] for d in FEATURE_DIMS})[dim].append(float(val))
    overall = {dim: _mean_std(buckets[dim]) for dim in FEATURE_DIMS}
    per_block = {
        block: {dim: _mean_std(vals[dim]) for dim in FEATURE_DIMS}
        for block, vals in by_block.items()
    }
    return {"overall": overall, "by_utc_4h_block": per_block}


def detect_market_drift(
    live_samples: Sequence[Mapping[str, Any]],
    centroids: Optional[Mapping[str, Any]],
    *,
    z_threshold: float = DRIFT_Z_THRESHOLD,
    min_n: int = DRIFT_MIN_N,
    min_dimensions: int = DRIFT_MIN_DIMENSIONS,
) -> dict[str, Any]:
    """True when the live window is out-of-distribution vs recency-weighted centroids."""
    overall = (centroids or {}).get("overall") if isinstance(centroids, Mapping) else centroids
    if not isinstance(overall, Mapping):
        return {"drifted": False, "reason": "no_centroids", "z_scores": {}, "n": 0}
    live_vals: dict[str, list[float]] = {dim: [] for dim in FEATURE_DIMS}
    for sample in live_samples:
        feat = sample if all(d in sample for d in FEATURE_DIMS) else extract_trade_features(sample)
        for dim in FEATURE_DIMS:
            val = feat.get(dim)
            if val is None:
                continue
            live_vals[dim].append(float(val))
    z_scores: dict[str, float] = {}
    drifted_dims: list[str] = []
    n_used = 0
    for dim in FEATURE_DIMS:
        live = live_vals[dim]
        ref = overall.get(dim) or {}
        ref_mean = ref.get("mean")
        ref_std = ref.get("std")
        if ref_mean is None or ref_std is None or len(live) < min_n:
            continue
        n_used = max(n_used, len(live))
        live_mean = sum(live) / len(live)
        denom = max(float(ref_std), 1e-6)
        z = abs(live_mean - float(ref_mean)) / denom
        z_scores[dim] = round(z, 3)
        if z >= z_threshold:
            drifted_dims.append(dim)
    drifted = len(drifted_dims) >= min_dimensions
    return {
        "drifted": drifted,
        "reason": "ood" if drifted else "in_distribution",
        "drifted_dims": drifted_dims,
        "z_scores": z_scores,
        "n": n_used,
    }


def classify_alignment(
    live_sample: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    warm_start: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    """Justify Relaxed / Conservative / Strict from live readings vs warm-start pockets.

    Supports either a single trade/feature dict or a rolling window of trades/features.
    When given a sequence, averages feature values to prevent single-trade noise.
    """
    if isinstance(live_sample, Sequence) and not isinstance(live_sample, (str, bytes, Mapping)):
        if not live_sample:
            return {"level": "conservative", "message": "No samples — Conservative default", "favorable": False, "adverse": False}
        feats = [s if "volatility" in s else extract_trade_features(s) for s in live_sample]
        # Average numeric feature values across the rolling window
        vol_vals = [f.get("volatility") for f in feats if f.get("volatility") is not None]
        liq_vals = [f.get("liquidity") for f in feats if f.get("liquidity") is not None]
        manip_vals = [f.get("manipulation") for f in feats if f.get("manipulation") is not None]
        feat = {
            "volatility": sum(vol_vals) / len(vol_vals) if vol_vals else None,
            "liquidity": sum(liq_vals) / len(liq_vals) if liq_vals else None,
            "manipulation": sum(manip_vals) / len(manip_vals) if manip_vals else None,
            "utc_4h_block": feats[-1].get("utc_4h_block"),
        }
    else:
        feat = live_sample if "volatility" in live_sample else extract_trade_features(live_sample)

    block = feat.get("utc_4h_block")
    block_wr = None
    if warm_start and block is not None:
        by_utc = (warm_start.get("by_utc_4h_block") or {})
        stats = by_utc.get(str(block)) or {}
        block_wr = stats.get("wr")
    centroids = (warm_start or {}).get("feature_centroids") or {}
    overall = centroids.get("overall") if isinstance(centroids, Mapping) else {}
    vol_mean = ((overall.get("volatility") or {}) if isinstance(overall, Mapping) else {}).get("mean")
    liq_mean = ((overall.get("liquidity") or {}) if isinstance(overall, Mapping) else {}).get("mean")
    manip_mean = ((overall.get("manipulation") or {}) if isinstance(overall, Mapping) else {}).get("mean")
    vol = feat.get("volatility")
    liq = feat.get("liquidity")
    manip = feat.get("manipulation")
    favorable = (
        vol is not None and vol_mean is not None and vol >= vol_mean
        and liq is not None and liq_mean is not None and liq >= liq_mean
        and manip is not None and manip_mean is not None and manip <= manip_mean
    )
    adverse = (
        (manip is not None and manip_mean is not None and manip > manip_mean)
        or (liq is not None and liq_mean is not None and liq < liq_mean)
    )
    if favorable and (block_wr is None or block_wr >= ALIGNMENT_RELAXED_WR):
        level = "relaxed"
        text = "Conditions aligned — Relaxed justified"
    elif adverse or (block_wr is not None and block_wr <= ALIGNMENT_STRICT_WR):
        level = "strict"
        text = "Conditions adverse — Strict justified"
    else:
        level = "conservative"
        text = "Conditions mixed — Conservative justified"
    return {
        "level": level,
        "message": text,
        "utc_4h_block": block,
        "block_wr": block_wr,
        "favorable": bool(favorable),
        "adverse": bool(adverse),
    }
