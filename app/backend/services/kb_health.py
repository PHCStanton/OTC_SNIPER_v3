"""Phase 4 — KB health audit, recency-weighted backfill, Guardian warm-start.

Contracts (REV2):
  - Master KB (`condition_patterns.json`) and integer prior files are NEVER
    written here. Backfill emits a staged report + a warm-start baseline.
  - UTC 4-hour blocks use the 22:00 UTC rollover origin (A1).
  - Bayesian recency overlay uses exponential decay with a 21-day default
    half-life (A2). Integer counts are informational on the staged payload
    and are not applied to master priors (avoids double-counting history).
  - Warm-start baseline is the Session Guardian prior-transfer reference (D7).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional
import sys

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared.bayesian_prior_store import (
    DEFAULT_RECENCY_HALF_LIFE_DAYS,
    apply_trade_outcomes,
    recency_weight,
)
from shared.utc_time_blocks import (
    SECONDS_PER_DAY,
    utc_4h_block,
    utc_4h_label,
    trade_entry_unix,
)
from .ghost_protocol_profiles import compute_feature_centroids

logger = logging.getLogger("otc_sniper.kb_health")

DEFAULT_LOOKBACK_DAYS = 56  # ~8 weeks
DEFAULT_AUDIT_WINDOW_DAYS = 30
STALE_AFTER_DAYS = 30.0
WARM_START_MIN_N = 20
PRIOR_TRANSFER_MIN_N = 10
PRIOR_TRANSFER_DIVERGENCE_PP = 8.0
WARM_START_SCHEMA_VERSION = 1
BACKFILL_COMMIT_MODE = "recency_overlay_and_patterns"
BACKFILL_SOURCE = "kb_backfill"


class KbHealthError(RuntimeError):
    """Loud failure for KB health / backfill operations."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")


def _parse_generated_utc(raw: Any) -> Optional[datetime]:
    """Parse KB metadata timestamps. Canonical form is ``YYYY-MM-DD HH:MM:SS UTC``."""
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    iso = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _file_age_days(path: Path, now: Optional[datetime] = None) -> Optional[float]:
    if not path.exists():
        return None
    now = now or _utc_now()
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return max(0.0, (now - mtime).total_seconds() / SECONDS_PER_DAY)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".kb_health_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(tmp_name).replace(path)
    except Exception:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _oteo_band(score: Any) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if value < 65:
        return "<65"
    if value < 75:
        return "65-74"
    if value < 85:
        return "75-84"
    if value < 93:
        return "85-92"
    return "93+"


def _z_band(z_score: Any) -> str:
    if z_score is None:
        return "UNKNOWN"
    try:
        zv = float(z_score)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if zv < -1.5:
        return "<-1.5"
    if zv < -0.5:
        return "-1.5_to_-0.5"
    if zv <= 0.5:
        return "-0.5_to_0.5"
    if zv <= 1.5:
        return "0.5_to_1.5"
    return ">1.5"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise KbHealthError(f"Corrupt JSON at {path}: {exc}") from exc
    except OSError as exc:
        raise KbHealthError(f"Failed reading {path}: {exc}") from exc


def load_session_trades(sessions_dir: Path) -> List[Dict[str, Any]]:
    """Load every JSON object from ``*.jsonl`` session files. Skip bad lines loudly via log."""
    if not sessions_dir.exists():
        return []
    trades: List[Dict[str, Any]] = []
    for path in sorted(sessions_dir.glob("*.jsonl")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Failed reading session file %s: %s", path, exc)
            raise KbHealthError(f"Failed reading session file {path}: {exc}") from exc
        for line_no, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping invalid JSON in %s:%s", path.name, line_no)
                continue
            if isinstance(row, dict):
                trades.append(row)
    return trades


def _settled(trades: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for trade in trades:
        outcome = str(trade.get("outcome") or "").strip().lower()
        if outcome in {"win", "loss"}:
            out.append(dict(trade))
    return out


def _within_lookback(trade: Mapping[str, Any], *, as_of_unix: float, lookback_days: int) -> bool:
    unix = trade_entry_unix(trade)
    if unix is None:
        return False
    age_days = (as_of_unix - unix) / SECONDS_PER_DAY
    return 0.0 <= age_days <= float(lookback_days)


def _horizon_seconds(trade: Mapping[str, Any]) -> int:
    raw = trade.get("expiration_seconds")
    ctx = trade.get("entry_context")
    if raw is None and isinstance(ctx, Mapping):
        raw = ctx.get("expiration_seconds")
    try:
        return int(raw) if raw is not None else 60
    except (TypeError, ValueError):
        return 60


def _regime_label(trade: Mapping[str, Any]) -> str:
    ctx = trade.get("entry_context") if isinstance(trade.get("entry_context"), Mapping) else {}
    return str(ctx.get("regime_label") or ctx.get("regime") or trade.get("regime_label") or "UNKNOWN").upper().strip()


def _direction(trade: Mapping[str, Any]) -> str:
    return str(trade.get("direction") or "CALL").upper().strip()


def _confidence(trade: Mapping[str, Any]) -> str:
    ctx = trade.get("entry_context") if isinstance(trade.get("entry_context"), Mapping) else {}
    return str(trade.get("confidence") or ctx.get("confidence") or "MEDIUM").upper().strip()


def _features_for_trade(trade: Mapping[str, Any], block: int) -> List[str]:
    ctx = trade.get("entry_context") if isinstance(trade.get("entry_context"), Mapping) else {}
    score = trade.get("oteo_score") or ctx.get("oteo_score") or 50.0
    z_score = ctx.get("z_score")
    manip = ctx.get("manipulation") or trade.get("manipulation_at_entry")
    has_manip = "MANIP_TRUE" if (isinstance(manip, (dict, list, bool)) and bool(manip)) else "MANIP_FALSE"
    return [
        f"oteo_band={_oteo_band(score)}",
        f"regime={_regime_label(trade)}",
        f"confidence={_confidence(trade)}",
        f"z_band={_z_band(z_score)}",
        f"has_manip={has_manip}",
        f"direction={_direction(trade)}",
        f"utc_4h_block={block}",
    ]


def _read_priors_summary(path: Path, now: datetime) -> Dict[str, Any]:
    exists = path.exists()
    age = _file_age_days(path, now) if exists else None
    summary: Dict[str, Any] = {
        "path": str(path),
        "exists": exists,
        "age_days": round(age, 2) if age is not None else None,
        "stale": bool(age is not None and age > STALE_AFTER_DAYS),
        "total_trades": 0,
        "total_wins": 0,
        "total_losses": 0,
        "has_recency": False,
        "feature_keys": 0,
    }
    if not exists:
        return summary
    data = _load_json(path)
    summary["total_wins"] = int(data.get("total_wins") or 0)
    summary["total_losses"] = int(data.get("total_losses") or 0)
    summary["total_trades"] = int(data.get("total_trades") or (summary["total_wins"] + summary["total_losses"]))
    summary["has_recency"] = isinstance(data.get("recency"), dict)
    summary["feature_keys"] = len(data.get("feature_counts") or {})
    return summary


def audit_kb_health(
    *,
    kb_path: Path,
    priors_60_path: Path,
    priors_300_path: Path,
    sessions_dir: Path,
    now: Optional[datetime] = None,
    audit_window_days: int = DEFAULT_AUDIT_WINDOW_DAYS,
) -> Dict[str, Any]:
    """Pattern coverage vs last 30 days, prior freshness, horizon-isolation check."""
    now = now or _utc_now()
    as_of_unix = now.timestamp()

    kb_exists = kb_path.exists()
    kb_age = _file_age_days(kb_path, now) if kb_exists else None
    patterns: List[Dict[str, Any]] = []
    generated_utc = None
    generated_age = None
    if kb_exists:
        kb_data = _load_json(kb_path)
        patterns = list(kb_data.get("patterns") or [])
        generated_utc = (kb_data.get("metadata") or {}).get("generated_utc")
        parsed = _parse_generated_utc(generated_utc)
        if parsed is not None:
            generated_age = max(0.0, (now - parsed).total_seconds() / SECONDS_PER_DAY)

    with_utc = sum(1 for p in patterns if p.get("utc_4h_block") is not None or "utc4h:" in str(p.get("pattern_key") or ""))
    kb_assets = {
        str(p.get("asset") or "").strip().lower().replace("_otc", "")
        for p in patterns
        if p.get("asset")
    }

    recent_trades = [
        t for t in _settled(load_session_trades(sessions_dir))
        if _within_lookback(t, as_of_unix=as_of_unix, lookback_days=audit_window_days)
    ]
    recent_assets = {
        str(t.get("asset") or "").strip().lower().replace("_otc", "")
        for t in recent_trades
        if t.get("asset")
    }
    covered = recent_assets & kb_assets if recent_assets else set()
    coverage_pct = round((len(covered) / len(recent_assets) * 100.0), 1) if recent_assets else 0.0

    priors_60 = _read_priors_summary(priors_60_path, now)
    priors_300 = _read_priors_summary(priors_300_path, now)
    isolation_issues: List[str] = []
    if priors_60_path.resolve() == priors_300_path.resolve():
        isolation_issues.append("60s and 300s priors resolve to the SAME file — horizon isolation is broken")
    if not priors_300_path.exists():
        isolation_issues.append(f"300s priors file missing: {priors_300_path}")
    if not priors_60_path.exists():
        isolation_issues.append(f"60s priors file missing: {priors_60_path}")

    return {
        "generated_utc": _utc_now_iso(),
        "audit_window_days": audit_window_days,
        "kb": {
            "path": str(kb_path),
            "exists": kb_exists,
            "total_patterns": len(patterns),
            "generated_utc": generated_utc,
            "file_age_days": round(kb_age, 2) if kb_age is not None else None,
            "generated_age_days": round(generated_age, 2) if generated_age is not None else None,
            "stale": bool((generated_age or kb_age or 0) > STALE_AFTER_DAYS) if kb_exists else True,
            "with_utc_4h": with_utc,
            "coverage_last_window": {
                "session_trades": len(recent_trades),
                "distinct_assets": len(recent_assets),
                "kb_assets": len(kb_assets),
                "assets_covered": len(covered),
                "coverage_pct": coverage_pct,
                "uncovered_assets": sorted(recent_assets - kb_assets),
            },
        },
        "priors": {
            "60s": priors_60,
            "300s": priors_300,
            "horizon_isolation": {
                "ok": len(isolation_issues) == 0,
                "issues": isolation_issues,
            },
        },
    }


def _weighted_wr(wins: float, losses: float) -> Optional[float]:
    total = wins + losses
    if total <= 0:
        return None
    return wins / total


def extract_recency_patterns(
    trades: List[Mapping[str, Any]],
    *,
    as_of_unix: float,
    half_life_days: float,
) -> List[Dict[str, Any]]:
    """Build utc-4h-sliced candidate patterns with recency-weighted win rates."""
    groups: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "asset": "",
        "strategy_level": "",
        "oteo_score_band": "",
        "regime_label": "",
        "direction": "",
        "utc_4h_block": None,
        "utc_4h_label": "",
        "n": 0,
        "wins": 0,
        "losses": 0,
        "weighted_n": 0.0,
        "weighted_wins": 0.0,
        "weighted_losses": 0.0,
        "profit": 0.0,
    })
    for trade in trades:
        outcome = str(trade.get("outcome") or "").strip().lower()
        if outcome not in {"win", "loss"}:
            continue
        unix = trade_entry_unix(trade)
        if unix is None:
            continue
        weight = recency_weight((as_of_unix - unix) / SECONDS_PER_DAY, half_life_days)
        ctx = trade.get("entry_context") if isinstance(trade.get("entry_context"), Mapping) else {}
        asset = str(trade.get("asset") or "UNKNOWN")
        level = str(trade.get("strategy_level") or ctx.get("strategy_level") or "level3")
        band = _oteo_band(trade.get("oteo_score") or ctx.get("oteo_score") or 50.0)
        regime = _regime_label(trade)
        direction = _direction(trade)
        block = utc_4h_block(unix)
        key = f"{asset}|{level}|{band}|{regime}|{direction}|utc4h:{block}"
        pg = groups[key]
        pg["pattern_key"] = key
        pg["asset"] = asset
        pg["strategy_level"] = level
        pg["oteo_score_band"] = band
        pg["regime_label"] = regime
        pg["direction"] = direction
        pg["utc_4h_block"] = block
        pg["utc_4h_label"] = utc_4h_label(block)
        pg["n"] += 1
        pg["weighted_n"] += weight
        pg["profit"] += float(trade.get("profit") or 0.0)
        if outcome == "win":
            pg["wins"] += 1
            pg["weighted_wins"] += weight
        else:
            pg["losses"] += 1
            pg["weighted_losses"] += weight

    patterns: List[Dict[str, Any]] = []
    for pg in groups.values():
        n = int(pg["n"])
        decided = int(pg["wins"]) + int(pg["losses"])
        unweighted_wr = (pg["wins"] / decided * 100.0) if decided else 0.0
        weighted_decided = pg["weighted_wins"] + pg["weighted_losses"]
        weighted_wr = (pg["weighted_wins"] / weighted_decided * 100.0) if weighted_decided else 0.0
        net = round(float(pg["profit"]), 2)
        if n >= 20:
            tier = "HIGH"
        elif n >= 10:
            tier = "MEDIUM"
        elif n >= 5:
            tier = "LOW"
        else:
            tier = "VERY_LOW"
        patterns.append({
            "pattern_key": pg["pattern_key"],
            "asset": pg["asset"],
            "strategy_level": pg["strategy_level"],
            "oteo_score_band": pg["oteo_score_band"],
            "regime_label": pg["regime_label"],
            "direction": pg["direction"],
            "utc_4h_block": pg["utc_4h_block"],
            "utc_4h_label": pg["utc_4h_label"],
            "sample_size": n,
            "weighted_sample_size": round(pg["weighted_n"], 4),
            "win_rate_pct": round(weighted_wr, 1),
            "unweighted_win_rate_pct": round(unweighted_wr, 1),
            "expectancy": round(net / n, 2) if n else 0.0,
            "net_profit": net,
            "confidence_tier": tier,
            "suppression_candidate": (weighted_wr < 48.0 and n >= 5),
            "boost_candidate": (weighted_wr >= 60.0 and n >= 5),
        })
    patterns.sort(key=lambda p: (p["sample_size"], p["win_rate_pct"]), reverse=True)
    return patterns


def _bucket_warm_start(
    trades: List[Mapping[str, Any]],
    *,
    as_of_unix: float,
    half_life_days: float,
    key_fn,
) -> Dict[str, Dict[str, Any]]:
    buckets: Dict[str, Dict[str, float]] = defaultdict(lambda: {
        "n": 0.0, "wins": 0.0, "weighted_n": 0.0, "weighted_wins": 0.0,
    })
    for trade in trades:
        outcome = str(trade.get("outcome") or "").strip().lower()
        if outcome not in {"win", "loss"}:
            continue
        unix = trade_entry_unix(trade)
        if unix is None:
            continue
        key = key_fn(trade, unix)
        if key is None:
            continue
        weight = recency_weight((as_of_unix - unix) / SECONDS_PER_DAY, half_life_days)
        buckets[str(key)]["n"] += 1
        buckets[str(key)]["weighted_n"] += weight
        if outcome == "win":
            buckets[str(key)]["wins"] += 1
            buckets[str(key)]["weighted_wins"] += weight
    out: Dict[str, Dict[str, Any]] = {}
    for key, stats in buckets.items():
        wr = _weighted_wr(stats["weighted_wins"], stats["weighted_n"] - stats["weighted_wins"])
        out[key] = {
            "n": int(stats["n"]),
            "weighted_n": round(stats["weighted_n"], 4),
            "wr": round(wr * 100.0, 2) if wr is not None else None,
        }
    return out


def build_warm_start_baseline(
    trades: List[Mapping[str, Any]],
    *,
    as_of_unix: float,
    half_life_days: float,
    lookback_days: int,
) -> Dict[str, Any]:
    settled = [
        t for t in _settled(trades)
        if _within_lookback(t, as_of_unix=as_of_unix, lookback_days=lookback_days)
    ]
    overall = _bucket_warm_start(
        settled, as_of_unix=as_of_unix, half_life_days=half_life_days,
        key_fn=lambda _t, _u: "ALL",
    ).get("ALL", {"n": 0, "weighted_n": 0.0, "wr": None})
    by_regime = _bucket_warm_start(
        settled, as_of_unix=as_of_unix, half_life_days=half_life_days,
        key_fn=lambda t, _u: _regime_label(t),
    )
    by_utc = _bucket_warm_start(
        settled, as_of_unix=as_of_unix, half_life_days=half_life_days,
        key_fn=lambda _t, unix: str(utc_4h_block(unix)),
    )
    for block, stats in by_utc.items():
        stats["label"] = utc_4h_label(int(block))
    by_z = _bucket_warm_start(
        settled, as_of_unix=as_of_unix, half_life_days=half_life_days,
        key_fn=lambda t, _u: _z_band((t.get("entry_context") or {}).get("z_score") if isinstance(t.get("entry_context"), Mapping) else None),
    )
    return {
        "schema_version": WARM_START_SCHEMA_VERSION,
        "generated_utc": datetime.fromtimestamp(as_of_unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "as_of_unix": as_of_unix,
        "half_life_days": half_life_days,
        "lookback_days": lookback_days,
        "source": BACKFILL_SOURCE,
        "min_n_for_expectation": WARM_START_MIN_N,
        "expected_wr": overall.get("wr"),
        "expected_n": overall.get("n"),
        "expected_weighted_n": overall.get("weighted_n"),
        "by_regime": by_regime,
        "by_utc_4h_block": by_utc,
        "by_z_band": by_z,
        "feature_centroids": compute_feature_centroids(settled),
    }


def _horizon_prior_payload(
    trades: List[Mapping[str, Any]],
    *,
    horizon: int,
    as_of_unix: float,
    half_life_days: float,
) -> Dict[str, Any]:
    dated: List[Dict[str, Any]] = []
    for trade in trades:
        if _horizon_seconds(trade) != horizon:
            continue
        unix = trade_entry_unix(trade)
        if unix is None:
            continue
        outcome = str(trade.get("outcome") or "").strip().lower()
        if outcome not in {"win", "loss"}:
            continue
        block = utc_4h_block(unix)
        dated.append({
            "won": outcome == "win",
            "features": _features_for_trade(trade, block),
            "entry_time": unix,
        })
    if not dated:
        return {
            "total_wins": 0,
            "total_losses": 0,
            "total_trades": 0,
            "feature_counts": {},
            "recency": None,
        }
    built = apply_trade_outcomes(
        {"total_wins": 0, "total_losses": 0, "total_trades": 0, "feature_counts": {}},
        dated,
        as_of_unix=as_of_unix,
        half_life_days=half_life_days,
    )
    return built


def _refuse_master_collision(
    staged_path: Path,
    warm_start_path: Path,
    kb_path: Path,
    priors_60_path: Path,
    priors_300_path: Path,
) -> None:
    """Fail before any write if a backfill output path aliases a master file."""
    protected = {kb_path.resolve(), priors_60_path.resolve(), priors_300_path.resolve()}
    if staged_path.resolve() == kb_path.resolve():
        raise KbHealthError(
            "Refusing to stage into condition_patterns.json — staging path collides with master KB"
        )
    if staged_path.resolve() in {priors_60_path.resolve(), priors_300_path.resolve()}:
        raise KbHealthError("Refusing to stage into a Bayesian priors master file")
    if warm_start_path.resolve() in protected:
        raise KbHealthError("Refusing to write warm-start baseline over a master KB or priors file")


def stage_historical_backfill(
    *,
    sessions_dir: Path,
    staged_path: Path,
    warm_start_path: Path,
    kb_path: Path,
    priors_60_path: Path,
    priors_300_path: Path,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    half_life_days: float = DEFAULT_RECENCY_HALF_LIFE_DAYS,
    as_of_unix: Optional[float] = None,
    min_sample_size: int = 5,
) -> Dict[str, Any]:
    """Re-score ~8 weeks of sessions with recency weighting. Staging-only. Never writes master KB."""
    if lookback_days <= 0:
        raise KbHealthError("lookback_days must be > 0")
    if half_life_days <= 0:
        raise KbHealthError("half_life_days must be > 0")
    _refuse_master_collision(
        staged_path, warm_start_path, kb_path, priors_60_path, priors_300_path,
    )

    now_unix = float(as_of_unix) if as_of_unix is not None else _utc_now().timestamp()
    all_trades = load_session_trades(sessions_dir)
    window = [
        t for t in _settled(all_trades)
        if _within_lookback(t, as_of_unix=now_unix, lookback_days=lookback_days)
    ]
    if not window:
        raise KbHealthError(
            f"No settled trades with entry timestamps in the last {lookback_days} days under {sessions_dir}"
        )

    patterns = extract_recency_patterns(window, as_of_unix=now_unix, half_life_days=half_life_days)
    staged_patterns = [p for p in patterns if int(p.get("sample_size") or 0) >= min_sample_size]
    priors_60 = _horizon_prior_payload(window, horizon=60, as_of_unix=now_unix, half_life_days=half_life_days)
    priors_300 = _horizon_prior_payload(window, horizon=300, as_of_unix=now_unix, half_life_days=half_life_days)
    baseline = build_warm_start_baseline(
        window, as_of_unix=now_unix, half_life_days=half_life_days, lookback_days=lookback_days,
    )
    audit = audit_kb_health(
        kb_path=kb_path,
        priors_60_path=priors_60_path,
        priors_300_path=priors_300_path,
        sessions_dir=sessions_dir,
        now=datetime.fromtimestamp(now_unix, tz=timezone.utc),
    )

    recency_60 = priors_60.get("recency")
    staged_id = f"staged_kb_backfill_{int(now_unix)}"
    wins = sum(1 for t in window if str(t.get("outcome")).lower() == "win")
    losses = len(window) - wins
    wr = round(wins / len(window) * 100.0, 1) if window else 0.0
    profit = round(sum(float(t.get("profit") or 0.0) for t in window), 2)

    staged_entry = {
        "staged_id": staged_id,
        "created_utc": datetime.fromtimestamp(now_unix, tz=timezone.utc).isoformat(),
        "session_id": "KB_BACKFILL",
        "kind": "ghost",
        "status": "PENDING_REVIEW",
        "source": BACKFILL_SOURCE,
        "commit_mode": BACKFILL_COMMIT_MODE,
        "user_notes": (
            f"Recency-weighted backfill of last {lookback_days} days "
            f"(half-life {half_life_days}d). Integer prior deltas are 0 to avoid "
            f"double-counting history. Commit writes the recency overlay + utc4h patterns only."
        ),
        "sessions_count": len({str(t.get("session_id") or "") for t in window}),
        "total_trades": len(window),
        "win_rate": wr,
        "net_profit": profit,
        "statistical_significance": len(window) >= 25,
        "lookback_days": lookback_days,
        "half_life_days": half_life_days,
        "candidate_patterns": staged_patterns,
        "bayesian_deltas": {
            "total_wins_delta": 0,
            "total_losses_delta": 0,
            "total_trades_delta": 0,
            "feature_deltas": {},
            "recency": recency_60,
            "recency_300s": priors_300.get("recency"),
            "commit_mode": BACKFILL_COMMIT_MODE,
        },
        "sweet_spot_volatility": None,
        "sweet_spot_liquidity": None,
        "audit": {
            "kb_stale": audit["kb"]["stale"],
            "kb_with_utc_4h": audit["kb"]["with_utc_4h"],
            "horizon_isolation_ok": audit["priors"]["horizon_isolation"]["ok"],
            "horizon_isolation_issues": audit["priors"]["horizon_isolation"]["issues"],
        },
        "warm_start_path": str(warm_start_path),
    }

    existing: Dict[str, Any] = {"staged_reports": []}
    if staged_path.exists():
        existing = _load_json(staged_path)
        if not isinstance(existing, dict):
            raise KbHealthError(f"Staged updates file is not an object: {staged_path}")
        if "staged_reports" not in existing or not isinstance(existing.get("staged_reports"), list):
            existing["staged_reports"] = []
    reports = [r for r in existing["staged_reports"] if r.get("staged_id") != staged_id]
    reports.insert(0, staged_entry)
    _atomic_write_json(staged_path, {"staged_reports": reports})
    _atomic_write_json(warm_start_path, baseline)

    logger.info(
        "KB backfill staged %s (%d patterns, N=%d, warm-start WR=%s) — master KB untouched",
        staged_id, len(staged_patterns), len(window), baseline.get("expected_wr"),
    )
    return {
        "staged": staged_entry,
        "warm_start": baseline,
        "audit": audit,
        "master_kb_written": False,
        "master_priors_written": False,
        "window_trades": len(window),
        "window_wins": wins,
        "window_losses": losses,
    }


def load_warm_start_baseline(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    data = _load_json(path)
    if not isinstance(data, dict) or "expected_wr" not in data:
        raise KbHealthError(f"Warm-start baseline at {path} is missing expected_wr")
    return data


def default_paths_from_settings(settings: Any) -> Dict[str, Path]:
    data_dir = Path(settings.data_dir)
    repo_root = Path(__file__).resolve().parents[3]
    kb_path = repo_root / "reports" / "analysis" / "knowledge_base" / "condition_patterns.json"
    stats_dir = data_dir / "ghost_trades" / "stats"
    return {
        "sessions_dir": data_dir / "ghost_trades" / "sessions",
        "staged_path": stats_dir / "staged_knowledge_updates.json",
        "warm_start_path": stats_dir / "warm_start_baseline.json",
        "kb_path": kb_path,
        "priors_60_path": stats_dir / "bayesian_priors.json",
        "priors_300_path": stats_dir / "bayesian_priors_300s.json",
    }
