#!/usr/bin/env python3
"""
Offline Trade Intelligence Analyzer
Phases 1, 2, and 3 — Core Join Validation, Manipulation Diagnostics,
and L1/L2/L3 Optimization Matrices.

Architecture: each phase is a standalone function returning a structured
result dict. main() orchestrates them sequentially and delegates all
export work to dedicated export functions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class SchemaError(ValueError):
    """Raised when a JSONL line fails schema validation."""
    pass

class JoinAmbiguityError(ValueError):
    """Raised when multiple candidate signals match a single ghost trade within the tolerance window."""
    pass

class MissingTickFileError(FileNotFoundError):
    """Raised when a required tick file for an asset and date is missing."""
    pass


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def format_utc_datetime(timestamp: float) -> str:
    """Normalize timestamp to Gregorian UTC format: YYYY-MM-DD HH:mm:ss UTC."""
    dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _calc_stats(records: List[dict]) -> dict:
    """Compute wins, losses, win rate, net profit, expectancy for a record set."""
    total = len(records)
    wins = sum(1 for r in records if r["outcome"] == "win")
    losses = sum(1 for r in records if r["outcome"] == "loss")
    settled = wins + losses
    win_rate = (wins / settled * 100.0) if settled > 0 else 0.0
    net_profit = sum(float(r["profit"]) for r in records)
    expectancy = (net_profit / total) if total > 0 else 0.0
    return {
        "total_trades": total,
        "settled_trades": settled,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(win_rate, 2),
        "net_profit": round(net_profit, 2),
        "expectancy": round(expectancy, 4),
        "small_sample_warning": total < 10,
    }


def _score_band(score: float) -> str:
    """Return the label for a stable OTEO score bucket."""
    if score < 50:
        return "<50"
    elif score < 65:
        return "50-64"
    elif score < 75:
        return "65-74"
    elif score < 85:
        return "75-84"
    elif score < 93:
        return "85-92"
    else:
        return "93+"


# ---------------------------------------------------------------------------
# Schema validators
# ---------------------------------------------------------------------------

def validate_ghost_trade(row: Any, filename: str, line_number: int) -> dict:
    """
    Validate and normalize a ghost trade record.
    Raises SchemaError if required fields are missing or malformed.
    """
    if not isinstance(row, dict):
        raise SchemaError(
            f"{filename}:{line_number} Ghost trade row must be a JSON object, got {type(row).__name__}"
        )

    required = ["session_id", "asset", "direction", "entry_price", "outcome"]
    for field in required:
        if field not in row:
            raise SchemaError(f"{filename}:{line_number} Ghost trade missing required field: '{field}'")

    # Entry time can be entry_time or timestamp
    entry_time = row.get("entry_time") or row.get("timestamp")
    if entry_time is None:
        raise SchemaError(f"{filename}:{line_number} Ghost trade missing 'entry_time' or 'timestamp'")

    try:
        entry_time_val = float(entry_time)
        entry_price_val = float(row["entry_price"])
    except (ValueError, TypeError) as exc:
        raise SchemaError(
            f"{filename}:{line_number} Ghost trade numeric fields ('entry_time'/'entry_price') are malformed"
        ) from exc

    if not math.isfinite(entry_time_val) or not math.isfinite(entry_price_val):
        raise SchemaError(f"{filename}:{line_number} Ghost trade numeric fields must be finite values")

    asset = str(row["asset"]).strip()
    if not asset:
        raise SchemaError(f"{filename}:{line_number} Ghost trade field 'asset' cannot be empty")

    direction = str(row["direction"]).strip().upper()
    if direction not in ("CALL", "PUT"):
        raise SchemaError(
            f"{filename}:{line_number} Ghost trade 'direction' must be CALL or PUT, got {row['direction']!r}"
        )

    # Optional exit time / price — fix: distinct fallback field names
    exit_time_raw = row.get("exit_time") or row.get("end_time")
    exit_time: Optional[float] = None
    if exit_time_raw is not None:
        try:
            exit_time = float(exit_time_raw)
            if not math.isfinite(exit_time):
                raise SchemaError(f"{filename}:{line_number} Ghost trade exit_time must be finite")
        except (ValueError, TypeError) as exc:
            raise SchemaError(
                f"{filename}:{line_number} Ghost trade field 'exit_time' must be numeric"
            ) from exc

    exit_price: Optional[float] = None
    exit_price_raw = row.get("exit_price")
    if exit_price_raw is not None:
        try:
            exit_price = float(exit_price_raw)
            if not math.isfinite(exit_price):
                raise SchemaError(f"{filename}:{line_number} Ghost trade exit_price must be finite")
        except (ValueError, TypeError) as exc:
            raise SchemaError(
                f"{filename}:{line_number} Ghost trade field 'exit_price' must be numeric"
            ) from exc

    return {
        "id": str(row.get("id") or row.get("trade_id") or f"{filename}_line{line_number}"),
        "session_id": str(row["session_id"]),
        "asset": asset,
        "direction": direction,
        "entry_time": entry_time_val,
        "entry_price": entry_price_val,
        "exit_time": exit_time,
        "exit_price": exit_price,
        "outcome": str(row["outcome"]).lower(),
        "profit": float(row.get("profit") or 0.0),
        "payout_pct": float(row.get("payout_pct") or 0.0),
        # Preserve both raw score and adjusted score separately (fix M3)
        "oteo_score": float(row.get("oteo_score") or 0.0),
        "base_oteo_score": float(row.get("base_oteo_score") or row.get("oteo_score") or 0.0),
        "level2_score_adjustment": float(row.get("level2_score_adjustment") or 0.0),
        "strategy_level": str(row.get("strategy_level") or "unknown"),
        "confidence": str(row.get("confidence") or "unknown"),
        "amount": float(row.get("amount") or 0.0),
        "expiration_seconds": int(row.get("expiration_seconds") or 60),
        "entry_context": row.get("entry_context") or {},
    }


def validate_signal(row: Any, filename: str, line_number: int) -> dict:
    """
    Validate and normalize a runtime signal record.
    Raises SchemaError if required fields are missing or malformed.
    """
    if not isinstance(row, dict):
        raise SchemaError(
            f"{filename}:{line_number} Signal row must be a JSON object, got {type(row).__name__}"
        )

    required = ["t", "asset", "score", "dir", "price"]
    for field in required:
        if field not in row:
            raise SchemaError(f"{filename}:{line_number} Signal missing required field: '{field}'")

    try:
        t_val = float(row["t"])
        score_val = float(row["score"])
        price_val = float(row["price"])
    except (ValueError, TypeError) as exc:
        raise SchemaError(
            f"{filename}:{line_number} Signal numeric fields ('t'/'score'/'price') are malformed"
        ) from exc

    if not math.isfinite(t_val) or not math.isfinite(score_val) or not math.isfinite(price_val):
        raise SchemaError(f"{filename}:{line_number} Signal numeric fields must be finite values")

    asset = str(row["asset"]).strip()
    if not asset:
        raise SchemaError(f"{filename}:{line_number} Signal field 'asset' cannot be empty")

    direction = str(row["dir"]).strip().upper()
    if direction not in ("CALL", "PUT"):
        raise SchemaError(
            f"{filename}:{line_number} Signal direction must be CALL or PUT, got {row['dir']!r}"
        )

    # Resolve base score separately from adjusted score
    base_score = float(row.get("base_score") or row.get("base_oteo_score") or score_val)

    return {
        "t": t_val,
        "asset": asset,
        "score": score_val,
        "base_score": base_score,
        "dir": direction,
        "price": price_val,
        "conf": str(row.get("conf") or "unknown"),
        "manip": bool(row.get("manip", False)),
        "level2_enabled": bool(row.get("level2_enabled", False)),
        "level2_score_adjustment": float(row.get("level2_score_adjustment") or 0.0),
        "level2_suppressed_reason": row.get("level2_suppressed_reason"),
        "level3_enabled": bool(row.get("level3_enabled", False)),
        "level3_score_adjustment": float(row.get("level3_score_adjustment") or 0.0),
        "level3_suppressed_reason": row.get("level3_suppressed_reason"),
        "regime_label": row.get("regime_label"),
        "regime_confidence": row.get("regime_confidence"),
        "regime_stable": row.get("regime_stable"),
        "market_context": row.get("market_context") or {},
    }


def validate_tick(row: Any, filename: str, line_number: int) -> dict:
    """
    Validate and normalize a tick record.
    Raises SchemaError if required fields are missing or malformed.
    """
    if not isinstance(row, dict):
        raise SchemaError(
            f"{filename}:{line_number} Tick row must be a JSON object, got {type(row).__name__}"
        )

    for required_field in ("t", "p", "a"):
        if required_field not in row:
            raise SchemaError(
                f"{filename}:{line_number} Tick missing required field: '{required_field}'"
            )

    try:
        t_val = float(row["t"])
        p_val = float(row["p"])
    except (ValueError, TypeError) as exc:
        raise SchemaError(
            f"{filename}:{line_number} Tick numeric fields ('t'/'p') are malformed"
        ) from exc

    if not math.isfinite(t_val) or not math.isfinite(p_val):
        raise SchemaError(f"{filename}:{line_number} Tick numeric fields must be finite values")

    asset = str(row["a"]).strip()
    if not asset:
        raise SchemaError(f"{filename}:{line_number} Tick field 'a' cannot be empty")

    return {
        "t": t_val,
        "p": p_val,
        "a": asset,
        "b": str(row.get("b") or "unknown"),
    }


# ---------------------------------------------------------------------------
# JSONL loader
# ---------------------------------------------------------------------------

def load_jsonl_file(
    path: Path, parser_func: Callable, fail_fast: bool
) -> Tuple[List[dict], List[dict]]:
    """Load a JSONL file and validate each line using parser_func."""
    items: List[dict] = []
    schema_errors: List[dict] = []
    if not path.exists():
        return items, schema_errors

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                validated = parser_func(row, path.name, line_number)
                items.append(validated)
            except json.JSONDecodeError as exc:
                err_msg = f"{path.name}:{line_number} Invalid JSON: {exc.msg}"
                if fail_fast:
                    raise SchemaError(err_msg) from exc
                schema_errors.append({"file": path.name, "line": line_number, "error": err_msg})
            except SchemaError as exc:
                if fail_fast:
                    raise
                schema_errors.append({"file": path.name, "line": line_number, "error": str(exc)})
            except Exception as exc:
                err_msg = f"{path.name}:{line_number} Unexpected parsing error: {exc}"
                if fail_fast:
                    raise SchemaError(err_msg) from exc
                schema_errors.append({"file": path.name, "line": line_number, "error": err_msg})

    return items, schema_errors


# ---------------------------------------------------------------------------
# Join helper
# ---------------------------------------------------------------------------

def join_trade_with_signals(
    trade: dict, signals: List[dict], tolerance: float = 5.0
) -> Tuple[Optional[dict], Optional[float]]:
    """
    Match a ghost trade to its corresponding signal log record.
    Priority order:
      1. Exact timestamp match in entry_context.
      2. Nearest proximity match within tolerance seconds.
    Raises JoinAmbiguityError if equidistant distinct signals exist.
    """
    asset = trade["asset"]
    direction = trade["direction"]
    entry_time = trade["entry_time"]

    candidates = [s for s in signals if s["asset"] == asset and s["dir"] == direction]
    if not candidates:
        return None, None

    # Exact match via entry_context.timestamp
    entry_context = trade.get("entry_context")
    exact_ts: Optional[float] = None
    if isinstance(entry_context, dict):
        raw_ts = entry_context.get("timestamp")
        if raw_ts is not None:
            try:
                exact_ts = float(raw_ts)
            except (ValueError, TypeError):
                exact_ts = None

    if exact_ts is not None:
        exact_matches = [s for s in candidates if abs(s["t"] - exact_ts) < 0.001]
        if len(exact_matches) == 1:
            matched = exact_matches[0]
            drift = abs(matched["t"] - entry_time)
            return matched, drift
        elif len(exact_matches) > 1:
            raise JoinAmbiguityError(
                f"Multiple exact entry_context timestamp matches found for trade {trade['id']!r} "
                f"at timestamp {exact_ts}"
            )

    # Proximity matching within tolerance window
    valid_candidates = [
        (s, abs(s["t"] - entry_time))
        for s in candidates
        if abs(s["t"] - entry_time) <= tolerance
    ]
    if not valid_candidates:
        return None, None

    valid_candidates.sort(key=lambda x: x[1])
    min_drift = valid_candidates[0][1]
    closest = [cand for cand in valid_candidates if abs(cand[1] - min_drift) < 0.001]

    if len(closest) > 1:
        distinct_signals = {(c[0]["t"], c[0]["score"]) for c in closest}
        if len(distinct_signals) > 1:
            raise JoinAmbiguityError(
                f"Join Ambiguity: Ghost trade {trade['id']!r} matched multiple distinct signals "
                f"equidistantly (min drift: {min_drift:.4f}s). Candidates: "
                f"{[(c[0]['t'], c[0]['score']) for c in closest]}"
            )

    matched_signal, drift = closest[0]
    return matched_signal, drift


# ---------------------------------------------------------------------------
# Phase 1 — Analyzer Core and Join Validation
# ---------------------------------------------------------------------------

def run_phase1_join(
    session_files: List[Path],
    signal_root: Path,
    tick_root: Path,
    tolerance_seconds: float,
    fail_fast: bool,
) -> dict:
    """
    Parse ghost trades, load matching signal files, perform deterministic join,
    verify tick log existence, and return all join outputs + audit data.

    Returns a dict with:
      joined_records       — list of merged rows ready for downstream phases
      unjoined_missing     — trades with no signal match
      ambiguous_joins      — trades that hit JoinAmbiguityError
      missing_tick_files   — trades whose tick file was absent
      parsing_warnings     — non-fatal schema warnings collected during parsing
      all_trades_parsed    — total raw ghost trades parsed
    """
    print("\n[Phase 1] Analyzer Core and Join Validation")

    # Parse ghost trades
    all_trades: List[dict] = []
    parsing_warnings: List[dict] = []

    for path in session_files:
        trades, warnings = load_jsonl_file(path, validate_ghost_trade, fail_fast)
        all_trades.extend(trades)
        parsing_warnings.extend(warnings)

    print(f"  Parsed {len(all_trades)} ghost trades from {len(session_files)} session file(s).")

    if not all_trades:
        print("  No trades found. Skipping join.")
        return {
            "joined_records": [],
            "unjoined_missing": [],
            "ambiguous_joins": [],
            "missing_tick_files": [],
            "parsing_warnings": parsing_warnings,
            "all_trades_parsed": 0,
        }

    # Determine which UTC dates need signal files (same day + adjacent for boundary safety)
    unique_dates: Set[str] = set()
    for trade in all_trades:
        for offset in (-86400, 0, 86400):
            dt = datetime.fromtimestamp(trade["entry_time"] + offset, tz=timezone.utc)
            unique_dates.add(dt.strftime("%Y-%m-%d"))

    # Load and index signal files by asset → date → sorted list
    signals_by_asset_date: Dict[str, Dict[str, List[dict]]] = {}
    print(f"  Loading signal logs for {len(unique_dates)} date(s)...")
    for date_str in sorted(unique_dates):
        sig_file = signal_root / f"{date_str}.jsonl"
        if sig_file.exists():
            sig_list, warnings = load_jsonl_file(sig_file, validate_signal, fail_fast)
            parsing_warnings.extend(warnings)
            for sig in sig_list:
                asset = sig["asset"]
                signals_by_asset_date.setdefault(asset, {}).setdefault(date_str, []).append(sig)
        else:
            print(f"    Note: Signal file not found: {sig_file.name}")

    # Sort each bucket by timestamp
    for asset in signals_by_asset_date:
        for date_str in signals_by_asset_date[asset]:
            signals_by_asset_date[asset][date_str].sort(key=lambda s: s["t"])

    # Join loop
    joined_records: List[dict] = []
    unjoined_missing: List[dict] = []
    ambiguous_joins: List[dict] = []
    missing_tick_files: List[dict] = []
    verified_tick_files: Set[Path] = set()

    for trade in all_trades:
        asset = trade["asset"]
        entry_time = trade["entry_time"]
        dt = datetime.fromtimestamp(entry_time, tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d")
        prev_date = datetime.fromtimestamp(entry_time - 86400, tz=timezone.utc).strftime("%Y-%m-%d")
        next_date = datetime.fromtimestamp(entry_time + 86400, tz=timezone.utc).strftime("%Y-%m-%d")

        # Gather candidate signals from adjacent dates
        asset_signals = signals_by_asset_date.get(asset, {})
        relevant_signals: List[dict] = []
        for d in (prev_date, date_str, next_date):
            relevant_signals.extend(asset_signals.get(d, []))

        matched_signal: Optional[dict] = None
        drift: Optional[float] = None
        try:
            matched_signal, drift = join_trade_with_signals(
                trade, relevant_signals, tolerance=tolerance_seconds
            )
        except JoinAmbiguityError as exc:
            if fail_fast:
                raise
            ambiguous_joins.append({"trade": trade, "error": str(exc)})
            continue

        if matched_signal is None:
            unjoined_missing.append(trade)
            continue

        # Tick log existence check (sample-parse only first time per file)
        tick_file = tick_root / asset / f"{date_str}.jsonl"
        tick_file_verified = False
        if not tick_file.exists():
            err_msg = (
                f"Missing tick log file for trade {trade['id']} "
                f"(asset: {asset}, date: {date_str}): expected at {tick_file}"
            )
            if fail_fast:
                raise MissingTickFileError(err_msg)
            missing_tick_files.append({"trade": trade, "expected_path": str(tick_file)})
        else:
            tick_file_verified = True
            if tick_file not in verified_tick_files:
                # Sample first 100 lines only to avoid loading 100 MB+ files
                try:
                    _sample_tick_file(tick_file, fail_fast, parsing_warnings)
                    verified_tick_files.add(tick_file)
                except SchemaError as exc:
                    if fail_fast:
                        raise
                    parsing_warnings.append({"file": tick_file.name, "line": "n/a", "error": str(exc)})

        # Build merged row — separate base_oteo_score from adjusted score (fix M3)
        merged_row = {
            "session_id": trade["session_id"],
            "trade_id": trade["id"],
            "asset": asset,
            "direction": trade["direction"],
            "amount": trade["amount"],
            "expiration_seconds": trade["expiration_seconds"],
            "entry_time_utc": format_utc_datetime(entry_time),
            "entry_time_epoch": entry_time,
            "exit_time_utc": format_utc_datetime(trade["exit_time"]) if trade.get("exit_time") else "—",
            "exit_time_epoch": trade.get("exit_time") or "—",
            "entry_price": trade["entry_price"],
            "exit_price": trade.get("exit_price") or "—",
            "outcome": trade["outcome"],
            "profit": trade["profit"],
            "payout_pct": trade["payout_pct"],
            "strategy_level": trade["strategy_level"],
            "confidence": trade["confidence"],
            # Signal join fields
            "signal_time_epoch": matched_signal["t"],
            "signal_time_drift_seconds": round(drift, 4) if drift is not None else "—",
            "signal_price": matched_signal["price"],
            "signal_oteo_score": matched_signal["score"],
            "signal_base_oteo_score": matched_signal["base_score"],   # now distinct from score
            "signal_confidence": matched_signal["conf"],
            "signal_manipulation": matched_signal["manip"],
            "signal_level2_enabled": matched_signal["level2_enabled"],
            "signal_level2_score_adjustment": matched_signal["level2_score_adjustment"],
            "signal_level2_suppressed_reason": matched_signal["level2_suppressed_reason"] or "—",
            "signal_level3_enabled": matched_signal["level3_enabled"],
            "signal_level3_score_adjustment": matched_signal["level3_score_adjustment"],
            "signal_level3_suppressed_reason": matched_signal["level3_suppressed_reason"] or "—",
            "signal_regime_label": matched_signal.get("regime_label") or "—",
            "signal_regime_confidence": matched_signal.get("regime_confidence") or "—",
            "signal_regime_stable": (
                matched_signal.get("regime_stable")
                if matched_signal.get("regime_stable") is not None
                else "—"
            ),
            "tick_file_verified": tick_file_verified,
            "tick_file_path": str(tick_file),
        }
        joined_records.append(merged_row)

    print(
        f"  Join complete: {len(joined_records)} joined, "
        f"{len(unjoined_missing)} unmatched, "
        f"{len(ambiguous_joins)} ambiguous, "
        f"{len(missing_tick_files)} missing tick files."
    )

    return {
        "joined_records": joined_records,
        "unjoined_missing": unjoined_missing,
        "ambiguous_joins": ambiguous_joins,
        "missing_tick_files": missing_tick_files,
        "parsing_warnings": parsing_warnings,
        "all_trades_parsed": len(all_trades),
    }


def _sample_tick_file(path: Path, fail_fast: bool, warnings: List[dict]) -> None:
    """Sample-parse the first 100 lines of a tick file for schema integrity."""
    with path.open("r", encoding="utf-8") as fh:
        for i, raw_line in enumerate(fh):
            if i >= 100:
                break
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                validate_tick(row, path.name, i + 1)
            except (json.JSONDecodeError, SchemaError) as exc:
                err_msg = f"{path.name}:{i + 1} Tick sample parse error: {exc}"
                if fail_fast:
                    raise SchemaError(err_msg) from exc
                warnings.append({"file": path.name, "line": i + 1, "error": err_msg})


# ---------------------------------------------------------------------------
# Phase 2 — Manipulation-First Diagnostics
# ---------------------------------------------------------------------------

def run_phase2_manipulation(joined_records: List[dict]) -> dict:
    """
    Compute manipulation-linked performance diagnostics from the joined dataset.
    Returns per-asset, per-level, and hourly split statistics with damage rankings.
    """
    print("\n[Phase 2] Manipulation-First Diagnostics")

    manip_trades = [r for r in joined_records if r["signal_manipulation"] is True]
    non_manip_trades = [r for r in joined_records if r["signal_manipulation"] is False]

    global_manip = _calc_stats(manip_trades)
    global_non_manip = _calc_stats(non_manip_trades)

    # Per-asset splits
    asset_diagnostics: Dict[str, dict] = {}
    for asset in {r["asset"] for r in joined_records}:
        asset_all = [r for r in joined_records if r["asset"] == asset]
        asset_manip = [r for r in asset_all if r["signal_manipulation"] is True]
        asset_non_manip = [r for r in asset_all if r["signal_manipulation"] is False]

        m_stats = _calc_stats(asset_manip)
        nm_stats = _calc_stats(asset_non_manip)
        total = len(asset_all)
        manip_rate = (len(asset_manip) / total * 100.0) if total > 0 else 0.0
        wr_delta = m_stats["win_rate_pct"] - nm_stats["win_rate_pct"]
        exp_delta = m_stats["expectancy"] - nm_stats["expectancy"]

        asset_diagnostics[asset] = {
            "total_trades": total,
            "manipulation_rate_pct": round(manip_rate, 2),
            "manipulation_stats": m_stats,
            "non_manipulation_stats": nm_stats,
            "win_rate_delta_pct": round(wr_delta, 2),
            "expectancy_delta": round(exp_delta, 4),
            "damage_factor": round(-exp_delta, 4),
        }

    # Per strategy level splits
    level_diagnostics: Dict[str, dict] = {}
    for lvl in {r["strategy_level"] for r in joined_records}:
        lvl_all = [r for r in joined_records if r["strategy_level"] == lvl]
        level_diagnostics[lvl] = {
            "total_trades": len(lvl_all),
            "manipulation_stats": _calc_stats([r for r in lvl_all if r["signal_manipulation"] is True]),
            "non_manipulation_stats": _calc_stats([r for r in lvl_all if r["signal_manipulation"] is False]),
        }

    # UTC hourly degradation
    hourly_degradation: Dict[str, dict] = {}
    for hour in range(24):
        hour_trades = [
            r for r in joined_records
            if datetime.fromtimestamp(r["entry_time_epoch"], tz=timezone.utc).hour == hour
        ]
        if not hour_trades:
            continue
        h_manip = [r for r in hour_trades if r["signal_manipulation"] is True]
        h_non_manip = [r for r in hour_trades if r["signal_manipulation"] is False]
        m_stats = _calc_stats(h_manip)
        nm_stats = _calc_stats(h_non_manip)
        degradation = nm_stats["win_rate_pct"] - m_stats["win_rate_pct"]
        hourly_degradation[f"{hour:02d}:00"] = {
            "total_trades": len(hour_trades),
            "manip_trades": len(h_manip),
            "manip_win_rate_pct": m_stats["win_rate_pct"],
            "non_manip_win_rate_pct": nm_stats["win_rate_pct"],
            "win_rate_degradation_pct": round(degradation, 2),
        }

    # Rankings
    ranked_by_frequency = sorted(
        [{"asset": a, "rate_pct": d["manipulation_rate_pct"]} for a, d in asset_diagnostics.items()],
        key=lambda x: x["rate_pct"],
        reverse=True,
    )
    ranked_by_damage = sorted(
        [
            {"asset": a, "damage_factor": d["damage_factor"]}
            for a, d in asset_diagnostics.items()
            if d["manipulation_stats"]["total_trades"] > 0
        ],
        key=lambda x: x["damage_factor"],
        reverse=True,
    )
    weak_hours = sorted(
        [
            {"hour": h, "degradation_pct": d["win_rate_degradation_pct"], "manip_trades": d["manip_trades"]}
            for h, d in hourly_degradation.items()
            if d["manip_trades"] > 0
        ],
        key=lambda x: x["degradation_pct"],
        reverse=True,
    )

    print(
        f"  Manipulation rate: {round(len(manip_trades) / len(joined_records) * 100, 2) if joined_records else 0}% "
        f"({len(manip_trades)} of {len(joined_records)} joined trades)"
    )

    return {
        "global_splits": {
            "manipulation_present": global_manip,
            "manipulation_absent": global_non_manip,
        },
        "assets": asset_diagnostics,
        "levels": level_diagnostics,
        "hourly_degradation": hourly_degradation,
        "rankings": {
            "asset_manipulation_frequency": ranked_by_frequency,
            "asset_manipulation_damage": ranked_by_damage,
            "weak_utc_hours": weak_hours,
        },
    }


# ---------------------------------------------------------------------------
# Phase 3 — L1/L2/L3 Optimization Matrices
# ---------------------------------------------------------------------------

def run_phase3_optimization(joined_records: List[dict]) -> dict:
    """
    Build optimization matrices for Level 1, 2, and 3 signals covering:
    - Best and worst assets (by expectancy and win rate)
    - UTC hour-of-day performance table
    - UTC day-of-week performance table
    - OTEO score-band performance table
    - Strategy level comparison table (L1 vs L2 vs L3)
    - Regime × score-band × outcome cross-tab
    All summaries include expectancy, win rate, and sample size.
    """
    print("\n[Phase 3] L1/L2/L3 Optimization Matrices")

    # --- Helper: group records and compute stats per key ---
    def _group_stats(records: List[dict], key_fn: Callable) -> Dict[str, dict]:
        groups: Dict[str, List[dict]] = {}
        for r in records:
            k = key_fn(r)
            groups.setdefault(k, []).append(r)
        return {k: _calc_stats(v) for k, v in groups.items()}

    WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # 1. Asset performance table (all levels combined)
    asset_stats = _group_stats(joined_records, lambda r: r["asset"])
    asset_table = sorted(
        [{"asset": a, **s} for a, s in asset_stats.items()],
        key=lambda x: x["expectancy"],
        reverse=True,
    )

    # 2. Best and worst assets (minimum 5 trades, by expectancy)
    qualified = [a for a in asset_table if a["total_trades"] >= 5]
    best_assets = qualified[:5]
    worst_assets = list(reversed(qualified))[:5]

    # 3. UTC hour-of-day table
    def _hour_key(r: dict) -> str:
        return f"{datetime.fromtimestamp(r['entry_time_epoch'], tz=timezone.utc).hour:02d}:00"

    hourly_stats = _group_stats(joined_records, _hour_key)
    hourly_table = sorted(
        [{"hour_utc": h, **s} for h, s in hourly_stats.items()],
        key=lambda x: x["hour_utc"],
    )

    # 4. UTC day-of-week table
    def _weekday_key(r: dict) -> str:
        dow = datetime.fromtimestamp(r["entry_time_epoch"], tz=timezone.utc).weekday()
        return WEEKDAY_NAMES[dow]

    weekday_stats = _group_stats(joined_records, _weekday_key)
    weekday_order = {d: i for i, d in enumerate(WEEKDAY_NAMES)}
    weekday_table = sorted(
        [{"weekday": d, **s} for d, s in weekday_stats.items()],
        key=lambda x: weekday_order.get(x["weekday"], 99),
    )

    # 5. OTEO score-band table (using signal_oteo_score)
    def _band_key(r: dict) -> str:
        return _score_band(float(r.get("signal_oteo_score") or 0))

    score_band_stats = _group_stats(joined_records, _band_key)
    BAND_ORDER = ["<50", "50-64", "65-74", "75-84", "85-92", "93+"]
    score_band_table = sorted(
        [{"score_band": b, **s} for b, s in score_band_stats.items()],
        key=lambda x: BAND_ORDER.index(x["score_band"]) if x["score_band"] in BAND_ORDER else 99,
    )

    # 6. Strategy level comparison table
    level_stats = _group_stats(joined_records, lambda r: r["strategy_level"])
    level_table = sorted(
        [{"strategy_level": lvl, **s} for lvl, s in level_stats.items()],
        key=lambda x: x["strategy_level"],
    )

    # 7. Per-level asset breakdown (separated by strategy level)
    per_level_asset_breakdown: Dict[str, List[dict]] = {}
    for lvl in {r["strategy_level"] for r in joined_records}:
        lvl_records = [r for r in joined_records if r["strategy_level"] == lvl]
        lvl_asset_stats = _group_stats(lvl_records, lambda r: r["asset"])
        per_level_asset_breakdown[lvl] = sorted(
            [{"asset": a, **s} for a, s in lvl_asset_stats.items()],
            key=lambda x: x["expectancy"],
            reverse=True,
        )

    # 8. Per-level score-band breakdown
    per_level_score_band: Dict[str, List[dict]] = {}
    for lvl in {r["strategy_level"] for r in joined_records}:
        lvl_records = [r for r in joined_records if r["strategy_level"] == lvl]
        lvl_band_stats = _group_stats(lvl_records, _band_key)
        per_level_score_band[lvl] = sorted(
            [{"score_band": b, **s} for b, s in lvl_band_stats.items()],
            key=lambda x: BAND_ORDER.index(x["score_band"]) if x["score_band"] in BAND_ORDER else 99,
        )

    # 9. Regime × score-band × outcome cross-tab
    regime_band_crosstab: Dict[str, Dict[str, dict]] = {}
    for r in joined_records:
        regime = str(r.get("signal_regime_label") or "unknown")
        band = _score_band(float(r.get("signal_oteo_score") or 0))
        regime_band_crosstab.setdefault(regime, {}).setdefault(band, []).append(r)

    regime_band_stats: Dict[str, Dict[str, dict]] = {
        regime: {band: _calc_stats(records) for band, records in bands.items()}
        for regime, bands in regime_band_crosstab.items()
    }

    print(
        f"  Matrices built: {len(asset_table)} assets, {len(hourly_table)} UTC hours, "
        f"{len(weekday_table)} weekdays, {len(score_band_table)} score bands, "
        f"{len(level_table)} strategy level(s), {len(regime_band_stats)} regime(s)."
    )

    return {
        "asset_table": asset_table,
        "best_assets": best_assets,
        "worst_assets": worst_assets,
        "hourly_table": hourly_table,
        "weekday_table": weekday_table,
        "score_band_table": score_band_table,
        "level_table": level_table,
        "per_level_asset_breakdown": per_level_asset_breakdown,
        "per_level_score_band": per_level_score_band,
        "regime_band_stats": regime_band_stats,
    }


# ---------------------------------------------------------------------------
# Phase 5 — AI-Ready Knowledge Base Compression (stub — Phase 4 optional)
# ---------------------------------------------------------------------------

def run_phase5_knowledge_base(
    joined_records: List[dict],
    phase3_result: dict,
) -> dict:
    """
    Compress optimization matrices into compact condition-pattern summaries
    suitable for low-cost AI retrieval. Each pattern captures key condition
    dimensions with win rate, expectancy, sample size, and a confidence tier.

    Phase 4 (Dual-Regime Comparison) enriches patterns further but is not
    required to produce a usable knowledge base.
    """
    print("\n[Phase 5] AI-Ready Knowledge Base Compression")

    def _confidence_tier(sample_size: int) -> str:
        if sample_size >= 50:
            return "HIGH"
        elif sample_size >= 20:
            return "MEDIUM"
        elif sample_size >= 10:
            return "LOW"
        else:
            return "VERY_LOW"

    patterns: List[dict] = []

    # Build one pattern per asset × strategy_level × score_band × regime combination
    for r in joined_records:
        asset = r["asset"]
        level = r["strategy_level"]
        band = _score_band(float(r.get("signal_oteo_score") or 0))
        regime = str(r.get("signal_regime_label") or "unknown")
        direction = r["direction"]
        # Use these as the grouping key
        r["_pattern_key"] = f"{asset}|{level}|{band}|{regime}|{direction}"

    pattern_groups: Dict[str, List[dict]] = {}
    for r in joined_records:
        key = r["_pattern_key"]
        pattern_groups.setdefault(key, []).append(r)

    for key, group in pattern_groups.items():
        parts = key.split("|")
        asset, level, band, regime, direction = parts
        stats = _calc_stats(group)
        pattern = {
            "pattern_key": key,
            "asset": asset,
            "strategy_level": level,
            "oteo_score_band": band,
            "regime_label": regime,
            "direction": direction,
            "sample_size": stats["total_trades"],
            "win_rate_pct": stats["win_rate_pct"],
            "expectancy": stats["expectancy"],
            "net_profit": stats["net_profit"],
            "confidence_tier": _confidence_tier(stats["total_trades"]),
            "suppression_candidate": stats["win_rate_pct"] < 45.0 and stats["total_trades"] >= 5,
            "boost_candidate": stats["win_rate_pct"] > 60.0 and stats["total_trades"] >= 5,
        }
        patterns.append(pattern)

    # Sort by expectancy descending for easy top-N retrieval
    patterns.sort(key=lambda p: p["expectancy"], reverse=True)

    # Summary stats for the knowledge base header
    total_patterns = len(patterns)
    high_conf = sum(1 for p in patterns if p["confidence_tier"] in ("HIGH", "MEDIUM"))
    suppression_candidates = sum(1 for p in patterns if p["suppression_candidate"])
    boost_candidates = sum(1 for p in patterns if p["boost_candidate"])

    print(
        f"  Knowledge base: {total_patterns} patterns "
        f"({high_conf} medium/high confidence, "
        f"{suppression_candidates} suppression candidates, "
        f"{boost_candidates} boost candidates)."
    )

    return {
        "metadata": {
            "total_patterns": total_patterns,
            "high_confidence_patterns": high_conf,
            "suppression_candidates": suppression_candidates,
            "boost_candidates": boost_candidates,
            "generated_utc": format_utc_datetime(datetime.now(timezone.utc).timestamp()),
        },
        "patterns": patterns,
    }


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

CSV_HEADERS = [
    "session_id", "trade_id", "asset", "direction", "amount", "expiration_seconds",
    "entry_time_utc", "entry_time_epoch", "exit_time_utc", "exit_time_epoch",
    "entry_price", "exit_price", "outcome", "profit", "payout_pct",
    "strategy_level", "confidence", "signal_time_epoch", "signal_time_drift_seconds",
    "signal_price", "signal_oteo_score", "signal_base_oteo_score", "signal_confidence",
    "signal_manipulation", "signal_level2_enabled", "signal_level2_score_adjustment",
    "signal_level2_suppressed_reason", "signal_level3_enabled", "signal_level3_score_adjustment",
    "signal_level3_suppressed_reason", "signal_regime_label", "signal_regime_confidence",
    "signal_regime_stable", "tick_file_verified", "tick_file_path",
]


def export_joined_csv(joined_records: List[dict], report_root: Path) -> Path:
    """Write the raw joined dataset to CSV."""
    csv_file = report_root / "joined_trades.csv"
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(joined_records)
    print(f"  CSV Joined Ledger:      {csv_file}")
    return csv_file


def export_summary_json(
    phase1: dict,
    phase2: dict,
    phase3: dict,
    phase5: Optional[dict],
    session_files: List[Path],
    report_root: Path,
) -> Path:
    """Write the machine-readable aggregate summary JSON."""
    joined_records = phase1["joined_records"]
    wins = sum(1 for r in joined_records if r["outcome"] == "win")
    losses = sum(1 for r in joined_records if r["outcome"] == "loss")
    settled = wins + losses
    net_profit = sum(float(r["profit"]) for r in joined_records)
    win_rate = (wins / settled * 100.0) if settled > 0 else 0.0
    manip_count = sum(1 for r in joined_records if r["signal_manipulation"] is True)
    manip_rate = (manip_count / len(joined_records) * 100.0) if joined_records else 0.0
    drifts = [
        float(r["signal_time_drift_seconds"])
        for r in joined_records
        if r["signal_time_drift_seconds"] != "—"
    ]
    avg_drift = sum(drifts) / len(drifts) if drifts else 0.0

    summary = {
        "metadata": {
            "analyzer_phases": "Phase 1 + Phase 2 + Phase 3",
            "run_timestamp_utc": format_utc_datetime(datetime.now(timezone.utc).timestamp()),
            "sessions_analyzed": len(session_files),
        },
        "totals": {
            "total_ghost_trades_parsed": phase1["all_trades_parsed"],
            "successfully_joined": len(joined_records),
            "unjoined_missing_signals": len(phase1["unjoined_missing"]),
            "unjoined_ambiguous": len(phase1["ambiguous_joins"]),
            "missing_tick_files": len(phase1["missing_tick_files"]),
            "parsing_validation_warnings": len(phase1["parsing_warnings"]),
        },
        "performance_of_joined": {
            "wins": wins,
            "losses": losses,
            "settled": settled,
            "win_rate_pct": round(win_rate, 2),
            "net_profit": round(net_profit, 2),
            "average_drift_seconds": round(avg_drift, 4),
            "manipulation_rate_pct": round(manip_rate, 2),
        },
        "manipulation_diagnostics": phase2,
        "optimization_matrices": phase3,
    }

    if phase5 is not None:
        summary["knowledge_base_summary"] = phase5["metadata"]

    summary_file = report_root / "summary_statistics.json"
    with summary_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary Statistics:     {summary_file}")
    return summary_file


def export_knowledge_base_json(phase5: dict, report_root: Path) -> Path:
    """Write the compact knowledge base patterns JSON."""
    kb_dir = report_root / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)
    kb_file = kb_dir / "condition_patterns.json"
    with kb_file.open("w", encoding="utf-8") as f:
        json.dump(phase5, f, indent=2)
    print(f"  Knowledge Base JSON:    {kb_file}")
    return kb_file


def export_markdown_report(
    phase1: dict,
    phase2: dict,
    phase3: dict,
    session_files: List[Path],
    report_root: Path,
) -> Path:
    """Write the human-readable full analysis and mismatch audit report."""
    joined_records = phase1["joined_records"]
    global_manip = phase2["global_splits"]["manipulation_present"]
    global_non_manip = phase2["global_splits"]["manipulation_absent"]
    asset_diagnostics = phase2["assets"]
    level_diagnostics = phase2["levels"]
    hourly_degradation = phase2["hourly_degradation"]
    rankings = phase2["rankings"]
    weak_hours = rankings["weak_utc_hours"]

    run_ts = format_utc_datetime(datetime.now(timezone.utc).timestamp())
    total_parsed = phase1["all_trades_parsed"]
    successfully_joined = len(joined_records)
    unjoined_missing = phase1["unjoined_missing"]
    ambiguous_joins = phase1["ambiguous_joins"]
    missing_tick_files = phase1["missing_tick_files"]
    parsing_warnings = phase1["parsing_warnings"]

    audit_file = report_root / "mismatch_audit.md"
    with audit_file.open("w", encoding="utf-8") as f:

        f.write("# Historical Analyzer — Full Analysis Report\n\n")
        f.write(f"**Run Timestamp (UTC):** {run_ts}\n")
        f.write(f"**Sessions Analyzed:** {len(session_files)}\n")
        f.write(f"**Phases Run:** Phase 1 + Phase 2 + Phase 3\n\n")

        # ── Phase 1 — Join Summary ──
        f.write("---\n\n## Phase 1 — Join Summary\n\n")
        f.write("| Metric | Count |\n| --- | --- |\n")
        f.write(f"| Total Ghost Trades Parsed | {total_parsed} |\n")
        f.write(f"| Successfully Joined | {successfully_joined} |\n")
        f.write(f"| Unjoined (Missing Signals) | {len(unjoined_missing)} |\n")
        f.write(f"| Unjoined (Ambiguous Matches) | {len(ambiguous_joins)} |\n")
        f.write(f"| Missing Tick Files | {len(missing_tick_files)} |\n")
        f.write(f"| Parsing Validation Errors/Warnings | {len(parsing_warnings)} |\n\n")

        # ── Phase 2 — Manipulation Diagnostics ──
        f.write("---\n\n## Phase 2 — Manipulation-First Diagnostics\n\n")
        f.write("### Global Performance Splits\n\n")
        f.write("| Setup Context | Trades | Settled | Wins | Losses | Win Rate | Net Profit | Expectancy |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        f.write(
            f"| Manipulation Present | {global_manip['total_trades']} | {global_manip['settled_trades']} | "
            f"{global_manip['wins']} | {global_manip['losses']} | {global_manip['win_rate_pct']}% | "
            f"${global_manip['net_profit']:.2f} | {global_manip['expectancy']:.4f} |\n"
        )
        f.write(
            f"| Manipulation Absent | {global_non_manip['total_trades']} | {global_non_manip['settled_trades']} | "
            f"{global_non_manip['wins']} | {global_non_manip['losses']} | {global_non_manip['win_rate_pct']}% | "
            f"${global_non_manip['net_profit']:.2f} | {global_non_manip['expectancy']:.4f} |\n\n"
        )

        f.write("### Asset Performance Under Manipulation (Ranked by Frequency)\n\n")
        f.write(
            "| Asset | Total Trades | Manip Rate | Manip WR | Non-Manip WR | "
            "WR Delta | Exp Delta | Damage Factor |\n"
        )
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for rank in rankings["asset_manipulation_frequency"]:
            a = rank["asset"]
            d = asset_diagnostics[a]
            warn = " ⚠️" if (
                d["manipulation_stats"]["small_sample_warning"]
                or d["non_manipulation_stats"]["small_sample_warning"]
            ) else ""
            f.write(
                f"| {a} | {d['total_trades']} | {d['manipulation_rate_pct']}% | "
                f"{d['manipulation_stats']['win_rate_pct']}% | {d['non_manipulation_stats']['win_rate_pct']}% | "
                f"{d['win_rate_delta_pct']}% | {d['expectancy_delta']:.4f} | {d['damage_factor']:.4f}{warn} |\n"
            )
        f.write("\n_⚠️ denotes small sample sizes (< 10 trades) in one or both splits._\n\n")

        f.write("### Strategy Level Vulnerability\n\n")
        f.write("| Strategy Level | Total Trades | Manip Trades | Manip WR | Non-Manip WR | WR Delta |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for lvl, d in sorted(level_diagnostics.items()):
            m_wr = d["manipulation_stats"]["win_rate_pct"]
            nm_wr = d["non_manipulation_stats"]["win_rate_pct"]
            delta = round(m_wr - nm_wr, 2)
            f.write(
                f"| {lvl.upper()} | {d['total_trades']} | "
                f"{d['manipulation_stats']['total_trades']} | {m_wr}% | {nm_wr}% | {delta}% |\n"
            )
        f.write("\n")

        f.write("### Weakest UTC Hourly Windows Under Manipulation\n\n")
        f.write("| Hour (UTC) | Total Trades | Manip Trades | Manip WR | Non-Manip WR | Degradation |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for wh in weak_hours[:10]:
            hour = wh["hour"]
            hd = hourly_degradation[hour]
            f.write(
                f"| {hour} | {hd['total_trades']} | {hd['manip_trades']} | "
                f"{hd['manip_win_rate_pct']}% | {hd['non_manip_win_rate_pct']}% | "
                f"{hd['win_rate_degradation_pct']}% |\n"
            )
        f.write("\n")

        # ── Phase 3 — Optimization Matrices ──
        f.write("---\n\n## Phase 3 — L1/L2/L3 Optimization Matrices\n\n")

        # Strategy Level Comparison
        f.write("### Strategy Level Comparison\n\n")
        f.write("| Level | Trades | Wins | Losses | Win Rate | Net Profit | Expectancy |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for row in phase3["level_table"]:
            f.write(
                f"| {row['strategy_level'].upper()} | {row['total_trades']} | "
                f"{row['wins']} | {row['losses']} | {row['win_rate_pct']}% | "
                f"${row['net_profit']:.2f} | {row['expectancy']:.4f} |\n"
            )
        f.write("\n")

        # OTEO Score-Band Table
        f.write("### OTEO Score-Band Performance\n\n")
        f.write("| Score Band | Trades | Wins | Win Rate | Net Profit | Expectancy | Confidence |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for row in phase3["score_band_table"]:
            warn = " ⚠️" if row["small_sample_warning"] else ""
            f.write(
                f"| {row['score_band']} | {row['total_trades']} | {row['wins']} | "
                f"{row['win_rate_pct']}% | ${row['net_profit']:.2f} | {row['expectancy']:.4f} | "
                f"{'Low' if row['small_sample_warning'] else 'OK'}{warn} |\n"
            )
        f.write("\n")

        # UTC Hour-of-Day Table
        f.write("### UTC Hour-of-Day Performance\n\n")
        f.write("| Hour (UTC) | Trades | Wins | Win Rate | Net Profit | Expectancy |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for row in phase3["hourly_table"]:
            f.write(
                f"| {row['hour_utc']} | {row['total_trades']} | {row['wins']} | "
                f"{row['win_rate_pct']}% | ${row['net_profit']:.2f} | {row['expectancy']:.4f} |\n"
            )
        f.write("\n")

        # Day-of-Week Table
        f.write("### UTC Day-of-Week Performance\n\n")
        f.write("| Weekday | Trades | Wins | Win Rate | Net Profit | Expectancy |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for row in phase3["weekday_table"]:
            f.write(
                f"| {row['weekday']} | {row['total_trades']} | {row['wins']} | "
                f"{row['win_rate_pct']}% | ${row['net_profit']:.2f} | {row['expectancy']:.4f} |\n"
            )
        f.write("\n")

        # Best Assets
        f.write("### Best Assets (≥5 trades, by Expectancy)\n\n")
        f.write("| Rank | Asset | Trades | Win Rate | Expectancy |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for i, row in enumerate(phase3["best_assets"], 1):
            f.write(
                f"| {i} | {row['asset']} | {row['total_trades']} | "
                f"{row['win_rate_pct']}% | {row['expectancy']:.4f} |\n"
            )
        f.write("\n")

        # Worst Assets
        f.write("### Worst Assets (≥5 trades, by Expectancy)\n\n")
        f.write("| Rank | Asset | Trades | Win Rate | Expectancy |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for i, row in enumerate(phase3["worst_assets"], 1):
            f.write(
                f"| {i} | {row['asset']} | {row['total_trades']} | "
                f"{row['win_rate_pct']}% | {row['expectancy']:.4f} |\n"
            )
        f.write("\n")

        # Regime × Score-Band Cross-Tab
        f.write("### Regime × Score-Band Cross-Tab\n\n")
        for regime, bands in sorted(phase3["regime_band_stats"].items()):
            f.write(f"**Regime: {regime}**\n\n")
            f.write("| Score Band | Trades | Win Rate | Expectancy |\n")
            f.write("| --- | --- | --- | --- |\n")
            BAND_ORDER = ["<50", "50-64", "65-74", "75-84", "85-92", "93+"]
            for band in BAND_ORDER:
                if band in bands:
                    s = bands[band]
                    f.write(
                        f"| {band} | {s['total_trades']} | {s['win_rate_pct']}% | {s['expectancy']:.4f} |\n"
                    )
            f.write("\n")

        # ── Audit sections ──
        if unjoined_missing:
            f.write("---\n\n## Unjoined Trades (Missing Signals)\n\n")
            f.write("| Trade ID | Session ID | Asset | Direction | Entry Time (UTC) | Price |\n")
            f.write("| --- | --- | --- | --- | --- | --- |\n")
            for ut in unjoined_missing[:100]:
                f.write(
                    f"| {ut['id']} | {ut['session_id']} | {ut['asset']} | {ut['direction']} | "
                    f"{format_utc_datetime(ut['entry_time'])} | {ut['entry_price']} |\n"
                )
            if len(unjoined_missing) > 100:
                f.write(f"\n_...and {len(unjoined_missing) - 100} more unjoined trades._\n")
            f.write("\n")

        if ambiguous_joins:
            f.write("---\n\n## Ambiguous Join Audits\n\n")
            f.write("| Trade ID | Asset | Direction | Entry Time (UTC) | Details |\n")
            f.write("| --- | --- | --- | --- | --- |\n")
            for aj in ambiguous_joins:
                tr = aj["trade"]
                f.write(
                    f"| {tr['id']} | {tr['asset']} | {tr['direction']} | "
                    f"{format_utc_datetime(tr['entry_time'])} | {aj['error']} |\n"
                )
            f.write("\n")

        if missing_tick_files:
            f.write("---\n\n## Missing Tick Log Files\n\n")
            f.write("| Trade ID | Asset | UTC Date | Expected File Path |\n")
            f.write("| --- | --- | --- | --- |\n")
            for mt in missing_tick_files:
                tr = mt["trade"]
                dt_str = datetime.fromtimestamp(tr["entry_time"], tz=timezone.utc).strftime("%Y-%m-%d")
                f.write(f"| {tr['id']} | {tr['asset']} | {dt_str} | `{mt['expected_path']}` |\n")
            f.write("\n")

        if parsing_warnings:
            f.write("---\n\n## Parsing & Schema Warnings\n\n")
            f.write("| File | Line | Details |\n| --- | --- | --- |\n")
            for pw in parsing_warnings[:100]:
                f.write(f"| {pw['file']} | {pw['line']} | {pw['error']} |\n")
            if len(parsing_warnings) > 100:
                f.write(f"\n_...and {len(parsing_warnings) - 100} more parsing warnings._\n")
            f.write("\n")

    print(f"  Full Analysis Report:   {audit_file}")
    return audit_file


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def _resolve_report_root(raw: str) -> Path:
    """Strip a leading '@' convention and return a resolved Path."""
    cleaned = raw.lstrip("@")
    return Path(cleaned)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OTC SNIPER Offline Trade Intelligence Analyzer (Phase 1 + 2 + 3)"
    )
    parser.add_argument(
        "--sessions",
        default="*",
        help="Comma-separated ghost session IDs or '*' to process all (default: *)",
    )
    parser.add_argument(
        "--signal-root",
        default="app/data/signals",
        help="Base directory for daily signal logs (default: app/data/signals)",
    )
    parser.add_argument(
        "--tick-root",
        default="app/data/tick_logs",
        help="Base directory for tick log assets (default: app/data/tick_logs)",
    )
    parser.add_argument(
        "--ghost-session-root",
        default="app/data/ghost_trades/sessions",
        help="Base directory for ghost session JSONL files",
    )
    parser.add_argument(
        "--report-root",
        default="@reports/analysis",
        help="Output directory for all artifacts (default: @reports/analysis)",
    )
    parser.add_argument(
        "--tolerance-seconds",
        type=float,
        default=5.0,
        help="Time tolerance in seconds for signal-to-trade matching (default: 5.0)",
    )
    parser.add_argument(
        "--utc-only",
        action="store_true",
        default=True,
        help="Enforce UTC-only time grouping (default: True)",
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Continue on schema errors and ambiguities instead of aborting",
    )
    parser.add_argument(
        "--skip-knowledge-base",
        action="store_true",
        help="Skip Phase 5 knowledge base compression",
    )

    args = parser.parse_args()
    fail_fast = not args.no_fail_fast

    signal_root = Path(args.signal_root)
    tick_root = Path(args.tick_root)
    ghost_session_root = Path(args.ghost_session_root)
    report_root = _resolve_report_root(args.report_root)
    report_root.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("OTC SNIPER — Offline Trade Intelligence Analyzer")
    print("=" * 60)
    print(f"  Ghost session root: {ghost_session_root}")
    print(f"  Signals root:       {signal_root}")
    print(f"  Ticks root:         {tick_root}")
    print(f"  Report root:        {report_root}")
    print(f"  Tolerance:          {args.tolerance_seconds}s")
    print(f"  Fail fast:          {fail_fast}")

    # Resolve session files
    if not ghost_session_root.exists():
        print(f"Error: Ghost session root not found: {ghost_session_root}", file=sys.stderr)
        return 1

    session_files: List[Path] = []
    if args.sessions == "*":
        session_files = sorted(ghost_session_root.glob("*.jsonl"))
    else:
        for s_id in args.sessions.split(","):
            s_id = s_id.strip()
            if not s_id:
                continue
            candidate = ghost_session_root / f"{s_id}.jsonl"
            if not candidate.exists():
                candidate = ghost_session_root / s_id
            if not candidate.exists():
                print(f"Error: Session file not found: {s_id}", file=sys.stderr)
                return 1
            session_files.append(candidate)

    if not session_files:
        print("Warning: No ghost session files found.")
        return 0

    print(f"\n  Found {len(session_files)} ghost session file(s) to analyze.")

    # ── Run phases sequentially ──
    phase1 = run_phase1_join(
        session_files=session_files,
        signal_root=signal_root,
        tick_root=tick_root,
        tolerance_seconds=args.tolerance_seconds,
        fail_fast=fail_fast,
    )

    joined_records = phase1["joined_records"]
    if not joined_records:
        print("\nNo joined records to analyze. Check signal files and session data.")
        return 0

    phase2 = run_phase2_manipulation(joined_records)
    phase3 = run_phase3_optimization(joined_records)

    phase5: Optional[dict] = None
    if not args.skip_knowledge_base:
        phase5 = run_phase5_knowledge_base(joined_records, phase3)

    # ── Export all artifacts ──
    print("\n[Exporting Artifacts]")
    export_joined_csv(joined_records, report_root)
    export_summary_json(phase1, phase2, phase3, phase5, session_files, report_root)
    export_markdown_report(phase1, phase2, phase3, session_files, report_root)
    if phase5 is not None:
        export_knowledge_base_json(phase5, report_root)

    print("\n" + "=" * 60)
    print("Analysis complete.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
