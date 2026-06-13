#!/usr/bin/env python3
"""
Offline Trade Intelligence Analyzer - Core and Join Validation (Phase 1)
Parses ghost trades, signals, and tick logs, normalizes to UTC, and merges data deterministically.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple, Set

# Define Custom Exceptions
class SchemaError(ValueError):
    """Raised when a JSONL line fails schema validation."""
    pass

class JoinAmbiguityError(ValueError):
    """Raised when multiple candidate signals match a single ghost trade within the tolerance window."""
    pass

class MissingTickFileError(FileNotFoundError):
    """Raised when a required tick file for an asset and date is missing."""
    pass

def format_utc_datetime(timestamp: float) -> str:
    """Normalize timestamp to Gregorian UTC format: YYYY-MM-DD HH:mm:ss UTC."""
    dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

def validate_ghost_trade(row: Any, filename: str, line_number: int) -> dict:
    """
    Validate and normalize a ghost trade record.
    Raises SchemaError if required fields are missing or malformed.
    """
    if not isinstance(row, dict):
        raise SchemaError(f"{filename}:{line_number} Ghost trade row must be a JSON object, got {type(row).__name__}")

    # Check required fields
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
        raise SchemaError(f"{filename}:{line_number} Ghost trade numeric fields ('entry_time'/'entry_price') are malformed") from exc

    if not math.isfinite(entry_time_val) or not math.isfinite(entry_price_val):
        raise SchemaError(f"{filename}:{line_number} Ghost trade numeric fields must be finite values")

    asset = str(row["asset"]).strip()
    if not asset:
        raise SchemaError(f"{filename}:{line_number} Ghost trade field 'asset' cannot be empty")

    direction = str(row["direction"]).strip().upper()
    if direction not in ("CALL", "PUT"):
        raise SchemaError(f"{filename}:{line_number} Ghost trade 'direction' must be CALL or PUT, got {row['direction']!r}")

    # Optional exit time / price
    exit_time = row.get("exit_time") or row.get("exit_time")
    if exit_time is not None:
        try:
            exit_time = float(exit_time)
            if not math.isfinite(exit_time):
                raise SchemaError(f"{filename}:{line_number} Ghost trade exit_time must be finite")
        except (ValueError, TypeError) as exc:
            raise SchemaError(f"{filename}:{line_number} Ghost trade field 'exit_time' must be numeric") from exc

    exit_price = row.get("exit_price")
    if exit_price is not None:
        try:
            exit_price = float(exit_price)
            if not math.isfinite(exit_price):
                raise SchemaError(f"{filename}:{line_number} Ghost trade exit_price must be finite")
        except (ValueError, TypeError) as exc:
            raise SchemaError(f"{filename}:{line_number} Ghost trade field 'exit_price' must be numeric") from exc

    # Return structured dict
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
        "oteo_score": float(row.get("oteo_score") or 0.0),
        "base_oteo_score": float(row.get("base_oteo_score") or row.get("oteo_score") or 0.0),
        "level2_score_adjustment": float(row.get("level2_score_adjustment") or 0.0),
        "strategy_level": str(row.get("strategy_level") or "unknown"),
        "confidence": str(row.get("confidence") or "unknown"),
        "amount": float(row.get("amount") or 0.0),
        "expiration_seconds": int(row.get("expiration_seconds") or 60),
        "entry_context": row.get("entry_context") or {}
    }

def validate_signal(row: Any, filename: str, line_number: int) -> dict:
    """
    Validate and normalize a runtime signal record.
    Raises SchemaError if required fields are missing or malformed.
    """
    if not isinstance(row, dict):
        raise SchemaError(f"{filename}:{line_number} Signal row must be a JSON object, got {type(row).__name__}")

    required = ["t", "asset", "score", "dir", "price"]
    for field in required:
        if field not in row:
            raise SchemaError(f"{filename}:{line_number} Signal missing required field: '{field}'")

    try:
        t_val = float(row["t"])
        score_val = float(row["score"])
        price_val = float(row["price"])
    except (ValueError, TypeError) as exc:
        raise SchemaError(f"{filename}:{line_number} Signal numeric fields ('t'/'score'/'price') are malformed") from exc

    if not math.isfinite(t_val) or not math.isfinite(score_val) or not math.isfinite(price_val):
        raise SchemaError(f"{filename}:{line_number} Signal numeric fields must be finite values")

    asset = str(row["asset"]).strip()
    if not asset:
        raise SchemaError(f"{filename}:{line_number} Signal field 'asset' cannot be empty")

    direction = str(row["dir"]).strip().upper()
    if direction not in ("CALL", "PUT"):
        raise SchemaError(f"{filename}:{line_number} Signal direction must be CALL or PUT, got {row['dir']!r}")

    return {
        "t": t_val,
        "asset": asset,
        "score": score_val,
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
        "market_context": row.get("market_context") or {}
    }

def validate_tick(row: Any, filename: str, line_number: int) -> dict:
    """
    Validate and normalize a tick record.
    Raises SchemaError if required fields are missing or malformed.
    """
    if not isinstance(row, dict):
        raise SchemaError(f"{filename}:{line_number} Tick row must be a JSON object, got {type(row).__name__}")

    for required in ("t", "p", "a"):
        if required not in row:
            raise SchemaError(f"{filename}:{line_number} Tick missing required field: '{required}'")

    try:
        t_val = float(row["t"])
        p_val = float(row["p"])
    except (ValueError, TypeError) as exc:
        raise SchemaError(f"{filename}:{line_number} Tick numeric fields ('t'/'p') are malformed") from exc

    if not math.isfinite(t_val) or not math.isfinite(p_val):
        raise SchemaError(f"{filename}:{line_number} Tick numeric fields must be finite values")

    asset = str(row["a"]).strip()
    if not asset:
        raise SchemaError(f"{filename}:{line_number} Tick field 'a' cannot be empty")

    return {
        "t": t_val,
        "p": p_val,
        "a": asset,
        "b": str(row.get("b") or "unknown")
    }

def join_trade_with_signals(trade: dict, signals: list[dict], tolerance: float = 5.0) -> Tuple[dict | None, float | None]:
    """
    Match a ghost trade to its corresponding signal log record.
    Prioritizes exact timestamp match in entry_context, then proximity-based join.
    Raises JoinAmbiguityError if duplicate equidistant matches occur.
    """
    asset = trade["asset"]
    direction = trade["direction"]  # Normalised to CALL or PUT in validate_ghost_trade
    entry_time = trade["entry_time"]

    # 1. Filter signals matching asset and direction
    candidates = [
        s for s in signals
        if s["asset"] == asset and s["dir"] == direction
    ]
    if not candidates:
        return None, None

    # 2. Check for exact match via entry_context timestamp
    entry_context = trade.get("entry_context")
    exact_ts = None
    if isinstance(entry_context, dict):
        exact_ts = entry_context.get("timestamp")

    if exact_ts is not None:
        try:
            exact_ts_val = float(exact_ts)
            exact_matches = [
                s for s in candidates
                if abs(s["t"] - exact_ts_val) < 0.001
            ]
            if len(exact_matches) == 1:
                matched = exact_matches[0]
                drift = abs(matched["t"] - entry_time)
                return matched, drift
            elif len(exact_matches) > 1:
                raise JoinAmbiguityError(
                    f"Multiple exact entry_context timestamp matches found for trade {trade['id']!r} "
                    f"at timestamp {exact_ts_val}"
                )
        except (ValueError, TypeError):
            pass

    # 3. Proximity matching within tolerance window
    valid_candidates = []
    for s in candidates:
        drift = abs(s["t"] - entry_time)
        if drift <= tolerance:
            valid_candidates.append((s, drift))

    if not valid_candidates:
        return None, None

    # Sort by time drift ascending
    valid_candidates.sort(key=lambda x: x[1])

    min_drift = valid_candidates[0][1]
    # Check if multiple equidistant signals exist (tolerance < 0.001s margin)
    closest = [
        cand for cand in valid_candidates
        if abs(cand[1] - min_drift) < 0.001
    ]

    if len(closest) > 1:
        # Check if they represent truly distinct signals
        distinct_signals = {(c[0]["t"], c[0]["score"]) for c in closest}
        if len(distinct_signals) > 1:
            raise JoinAmbiguityError(
                f"Join Ambiguity: Ghost trade {trade['id']!r} matched multiple distinct signals "
                f"equidistantly (min drift: {min_drift:.4f}s). Candidates: "
                f"{[(c[0]['t'], c[0]['score']) for c in closest]}"
            )

    matched_signal, drift = closest[0]
    return matched_signal, drift

def load_jsonl_file(path: Path, parser_func: Any, fail_fast: bool) -> Tuple[list[dict], list[dict]]:
    """Loads a JSONL file and validates each line using parser_func."""
    items = []
    schema_errors = []
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

def main() -> int:
    parser = argparse.ArgumentParser(description="OTC SNIPER Phase 1 Historical Analyzer")
    parser.add_argument(
        "--sessions",
        default="*",
        help="Comma-separated ghost session IDs to analyze or '*' to process all files (default: *)"
    )
    parser.add_argument(
        "--signal-root",
        default="app/data/signals",
        help="Base directory for daily signal logs (default: app/data/signals)"
    )
    parser.add_argument(
        "--tick-root",
        default="app/data/tick_logs",
        help="Base directory for tick log assets (default: app/data/tick_logs)"
    )
    parser.add_argument(
        "--ghost-session-root",
        default="app/data/ghost_trades/sessions",
        help="Base directory for ghost session JSONL files (default: app/data/ghost_trades/sessions)"
    )
    parser.add_argument(
        "--report-root",
        default="@reports/analysis",
        help="Directory where output files are stored (default: @reports/analysis)"
    )
    parser.add_argument(
        "--tolerance-seconds",
        type=float,
        default=5.0,
        help="Time tolerance in seconds for matching signals to trades (default: 5.0)"
    )
    parser.add_argument(
        "--utc-only",
        action="store_true",
        default=True,
        help="Enforces strict UTC calculations (default: True)"
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="If set, do not abort on ambiguity, schema errors, or missing tick logs; log them instead."
    )

    args = parser.parse_args()
    fail_fast = not args.no_fail_fast

    signal_root = Path(args.signal_root)
    tick_root = Path(args.tick_root)
    ghost_session_root = Path(args.ghost_session_root)
    
    # Resolve report root path
    report_root = Path(args.report_root)
    if str(args.report_root).startswith("@"):
        report_root = Path(str(args.report_root).replace("@", ""))
    
    report_root.mkdir(parents=True, exist_ok=True)

    print(f"Starting Offline Analyzer Core (Phase 1)...")
    print(f"Ghost session root: {ghost_session_root}")
    print(f"Signals root:       {signal_root}")
    print(f"Ticks root:         {tick_root}")
    print(f"Report root:        {report_root}")
    print(f"Tolerance:          {args.tolerance_seconds}s")
    print(f"Fail fast:          {fail_fast}")

    # 1. Resolve ghost session files
    if not ghost_session_root.exists():
        print(f"Error: Ghost session root directory not found: {ghost_session_root}", file=sys.stderr)
        return 1

    session_files = []
    if args.sessions == "*":
        session_files = sorted(ghost_session_root.glob("*.jsonl"))
    else:
        for s_id in args.sessions.split(","):
            s_id = s_id.strip()
            if not s_id:
                continue
            path = ghost_session_root / f"{s_id}.jsonl"
            if not path.exists():
                path = ghost_session_root / s_id
            if not path.exists():
                print(f"Error: Session file not found: {s_id}", file=sys.stderr)
                return 1
            session_files.append(path)

    if not session_files:
        print(f"Warning: No ghost session files found to analyze.")
        return 0

    print(f"Found {len(session_files)} ghost session files to analyze.")

    # 2. Parse ghost trades
    all_trades: list[dict] = []
    parsing_warnings = []

    for path in session_files:
        trades, warnings = load_jsonl_file(path, validate_ghost_trade, fail_fast)
        all_trades.extend(trades)
        parsing_warnings.extend(warnings)

    print(f"Parsed {len(all_trades)} ghost trades total.")

    if not all_trades:
        print("No trades found to join.")
        return 0

    # 3. Cache signals daily files based on dates needed
    unique_dates: Set[str] = set()
    for trade in all_trades:
        dt = datetime.fromtimestamp(trade["entry_time"], tz=timezone.utc)
        unique_dates.add(dt.strftime("%Y-%m-%d"))
        # Load adjacent days for midnight boundary conditions
        prev_day = datetime.fromtimestamp(trade["entry_time"] - 86400, tz=timezone.utc).strftime("%Y-%m-%d")
        next_day = datetime.fromtimestamp(trade["entry_time"] + 86400, tz=timezone.utc).strftime("%Y-%m-%d")
        unique_dates.add(prev_day)
        unique_dates.add(next_day)

    # Store signals in a nested dictionary: signals_by_asset_and_date[asset][date_str] = list of signals
    signals_by_asset_and_date: dict[str, dict[str, list[dict]]] = {}
    print(f"Loading signal logs for unique dates: {sorted(list(unique_dates))}")
    for date_str in unique_dates:
        sig_file = signal_root / f"{date_str}.jsonl"
        if sig_file.exists():
            sig_list, warnings = load_jsonl_file(sig_file, validate_signal, fail_fast)
            for sig in sig_list:
                asset = sig["asset"]
                if asset not in signals_by_asset_and_date:
                    signals_by_asset_and_date[asset] = {}
                if date_str not in signals_by_asset_and_date[asset]:
                    signals_by_asset_and_date[asset][date_str] = []
                signals_by_asset_and_date[asset][date_str].append(sig)
            parsing_warnings.extend(warnings)
        else:
            print(f"Note: Daily signal file not found: {sig_file.name}")

    # Sort signals inside each bucket by timestamp
    for asset in signals_by_asset_and_date:
        for date_str in signals_by_asset_and_date[asset]:
            signals_by_asset_and_date[asset][date_str].sort(key=lambda s: s["t"])

    # 4. Perform the deterministic join and tick log verification
    joined_records = []
    unjoined_missing_signals = []
    ambiguous_joins = []
    missing_tick_files = []
    verified_tick_files = set()

    for trade in all_trades:
        # Resolve matching signal
        asset = trade["asset"]
        entry_time = trade["entry_time"]
        
        # Determine candidate dates (same day, prev day, next day) in UTC
        dt = datetime.fromtimestamp(entry_time, tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d")
        prev_date_str = datetime.fromtimestamp(entry_time - 86400, tz=timezone.utc).strftime("%Y-%m-%d")
        next_date_str = datetime.fromtimestamp(entry_time + 86400, tz=timezone.utc).strftime("%Y-%m-%d")
        
        # Gather signals from cached dates for this asset
        relevant_signals = []
        asset_signals = signals_by_asset_and_date.get(asset, {})
        for d in (prev_date_str, date_str, next_date_str):
            if d in asset_signals:
                relevant_signals.extend(asset_signals[d])
                
        # Resolve matching signal from this small candidate list
        matched_signal = None
        drift = None
        try:
            matched_signal, drift = join_trade_with_signals(trade, relevant_signals, tolerance=args.tolerance_seconds)
        except JoinAmbiguityError as exc:
            if fail_fast:
                raise
            ambiguous_joins.append({"trade": trade, "error": str(exc)})
            continue

        if matched_signal is None:
            unjoined_missing_signals.append(trade)
            continue

        # Enforce tick file check
        asset = trade["asset"]
        trade_date = datetime.fromtimestamp(trade["entry_time"], tz=timezone.utc).strftime("%Y-%m-%d")
        tick_file = tick_root / asset / f"{trade_date}.jsonl"

        tick_file_verified = False
        if not tick_file.exists():
            err_msg = f"Missing tick log file for trade {trade['id']} (asset: {asset}, date: {trade_date}): expected at {tick_file}"
            if fail_fast:
                raise MissingTickFileError(err_msg)
            missing_tick_files.append({"trade": trade, "expected_path": str(tick_file)})
        else:
            tick_file_verified = True
            if tick_file not in verified_tick_files:
                # Perform sample parse check to verify integrity
                try:
                    _, tick_warnings = load_jsonl_file(tick_file, validate_tick, fail_fast)
                    parsing_warnings.extend(tick_warnings)
                    verified_tick_files.add(tick_file)
                except SchemaError as exc:
                    if fail_fast:
                        raise
                    parsing_warnings.append({"file": tick_file.name, "line": "n/a", "error": str(exc)})

        # Build merged dataset row
        mc = matched_signal.get("market_context") or {}
        merged_row = {
            "session_id": trade["session_id"],
            "trade_id": trade["id"],
            "asset": asset,
            "direction": trade["direction"],
            "amount": trade["amount"],
            "expiration_seconds": trade["expiration_seconds"],
            "entry_time_utc": format_utc_datetime(trade["entry_time"]),
            "entry_time_epoch": trade["entry_time"],
            "exit_time_utc": format_utc_datetime(trade["exit_time"]) if trade.get("exit_time") else "—",
            "exit_time_epoch": trade.get("exit_time") or "—",
            "entry_price": trade["entry_price"],
            "exit_price": trade.get("exit_price") or "—",
            "outcome": trade["outcome"],
            "profit": trade["profit"],
            "payout_pct": trade["payout_pct"],
            "strategy_level": trade["strategy_level"],
            "confidence": trade["confidence"],
            "signal_time_epoch": matched_signal["t"],
            "signal_time_drift_seconds": round(drift, 4) if drift is not None else "—",
            "signal_price": matched_signal["price"],
            "signal_oteo_score": matched_signal["score"],
            "signal_base_oteo_score": matched_signal["score"],
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
            "signal_regime_stable": matched_signal.get("regime_stable") if matched_signal.get("regime_stable") is not None else "—",
            "tick_file_verified": tick_file_verified,
            "tick_file_path": str(tick_file)
        }
        joined_records.append(merged_row)

    # 5. Export Output Artifacts
    # A. Joined CSV Dataset
    csv_file = report_root / "joined_trades.csv"
    csv_headers = [
        "session_id", "trade_id", "asset", "direction", "amount", "expiration_seconds",
        "entry_time_utc", "entry_time_epoch", "exit_time_utc", "exit_time_epoch",
        "entry_price", "exit_price", "outcome", "profit", "payout_pct",
        "strategy_level", "confidence", "signal_time_epoch", "signal_time_drift_seconds",
        "signal_price", "signal_oteo_score", "signal_base_oteo_score", "signal_confidence",
        "signal_manipulation", "signal_level2_enabled", "signal_level2_score_adjustment",
        "signal_level2_suppressed_reason", "signal_level3_enabled", "signal_level3_score_adjustment",
        "signal_level3_suppressed_reason", "signal_regime_label", "signal_regime_confidence",
        "signal_regime_stable", "tick_file_verified", "tick_file_path"
    ]
    
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(joined_records)

    # B. Phase 2 - Manipulation-First Diagnostics
    manip_trades = [r for r in joined_records if r["signal_manipulation"] is True]
    non_manip_trades = [r for r in joined_records if r["signal_manipulation"] is False]
    
    def calc_split_stats(records: list[dict]) -> dict:
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
            "small_sample_warning": total < 5
        }
        
    global_manip = calc_split_stats(manip_trades)
    global_non_manip = calc_split_stats(non_manip_trades)
    
    # Per-Asset Diagnostics
    asset_diagnostics = {}
    assets_set = {r["asset"] for r in joined_records}
    for asset in assets_set:
        asset_all = [r for r in joined_records if r["asset"] == asset]
        asset_manip = [r for r in asset_all if r["signal_manipulation"] is True]
        asset_non_manip = [r for r in asset_all if r["signal_manipulation"] is False]
        
        manip_stats = calc_split_stats(asset_manip)
        non_manip_stats = calc_split_stats(asset_non_manip)
        
        total_trades = len(asset_all)
        manip_rate = (len(asset_manip) / total_trades * 100.0) if total_trades > 0 else 0.0
        
        win_rate_delta = manip_stats["win_rate_pct"] - non_manip_stats["win_rate_pct"]
        expectancy_delta = manip_stats["expectancy"] - non_manip_stats["expectancy"]
        
        asset_diagnostics[asset] = {
            "total_trades": total_trades,
            "manipulation_rate_pct": round(manip_rate, 2),
            "manipulation_stats": manip_stats,
            "non_manipulation_stats": non_manip_stats,
            "win_rate_delta_pct": round(win_rate_delta, 2),
            "expectancy_delta": round(expectancy_delta, 4),
            "damage_factor": round(-expectancy_delta, 4)
        }
        
    ranked_by_frequency = sorted(
        [{"asset": a, "rate_pct": d["manipulation_rate_pct"]} for a, d in asset_diagnostics.items()],
        key=lambda x: x["rate_pct"],
        reverse=True
    )
    ranked_by_damage = sorted(
        [{"asset": a, "damage_factor": d["damage_factor"]} for a, d in asset_diagnostics.items() if d["manipulation_stats"]["total_trades"] > 0],
        key=lambda x: x["damage_factor"],
        reverse=True
    )

    # Strategy Level Vulnerability
    level_diagnostics = {}
    levels_set = {r["strategy_level"] for r in joined_records}
    for lvl in levels_set:
        lvl_all = [r for r in joined_records if r["strategy_level"] == lvl]
        lvl_manip = [r for r in lvl_all if r["signal_manipulation"] is True]
        lvl_non_manip = [r for r in lvl_all if r["signal_manipulation"] is False]
        
        level_diagnostics[lvl] = {
            "total_trades": len(lvl_all),
            "manipulation_stats": calc_split_stats(lvl_manip),
            "non_manipulation_stats": calc_split_stats(lvl_non_manip)
        }

    # Weak UTC Hourly Windows
    hourly_manip_degradation = {}
    for hour in range(24):
        hour_trades = []
        for r in joined_records:
            dt = datetime.fromtimestamp(r["entry_time_epoch"], tz=timezone.utc)
            if dt.hour == hour:
                hour_trades.append(r)
        if not hour_trades:
            continue
            
        h_manip = [r for r in hour_trades if r["signal_manipulation"] is True]
        h_non_manip = [r for r in hour_trades if r["signal_manipulation"] is False]
        
        m_stats = calc_split_stats(h_manip)
        nm_stats = calc_split_stats(h_non_manip)
        
        degradation = nm_stats["win_rate_pct"] - m_stats["win_rate_pct"]
        
        hourly_manip_degradation[f"{hour:02d}:00"] = {
            "total_trades": len(hour_trades),
            "manip_trades": len(h_manip),
            "manip_win_rate_pct": m_stats["win_rate_pct"],
            "non_manip_win_rate_pct": nm_stats["win_rate_pct"],
            "win_rate_degradation_pct": round(degradation, 2)
        }
        
    weak_hours = sorted(
        [{"hour": h, "degradation_pct": d["win_rate_degradation_pct"], "manip_trades": d["manip_trades"]} for h, d in hourly_manip_degradation.items() if d["manip_trades"] > 0],
        key=lambda x: x["degradation_pct"],
        reverse=True
    )

    # Re-calculate overall performance stats
    wins = sum(1 for r in joined_records if r["outcome"] == "win")
    losses = sum(1 for r in joined_records if r["outcome"] == "loss")
    settled = wins + losses
    net_profit = sum(float(r["profit"]) for r in joined_records)
    win_rate = (wins / settled * 100.0) if settled > 0 else 0.0
    
    drifts = [float(r["signal_time_drift_seconds"]) for r in joined_records if r["signal_time_drift_seconds"] != "—"]
    avg_drift = sum(drifts) / len(drifts) if drifts else 0.0

    manip_signals = len(manip_trades)
    manip_rate = (manip_signals / len(joined_records) * 100.0) if joined_records else 0.0

    summary_stats = {
        "metadata": {
            "analyzer_phase": "Phase 2 - Manipulation-First Diagnostics",
            "run_timestamp_utc": format_utc_datetime(datetime.now(timezone.utc).timestamp()),
            "sessions_analyzed": len(session_files)
        },
        "totals": {
            "total_ghost_trades_parsed": len(all_trades),
            "successfully_joined": len(joined_records),
            "unjoined_missing_signals": len(unjoined_missing_signals),
            "unjoined_ambiguous": len(ambiguous_joins),
            "missing_tick_files": len(missing_tick_files),
            "parsing_validation_warnings": len(parsing_warnings)
        },
        "performance_of_joined": {
            "wins": wins,
            "losses": losses,
            "settled": settled,
            "win_rate_pct": round(win_rate, 2),
            "net_profit": round(net_profit, 2),
            "average_drift_seconds": round(avg_drift, 4),
            "manipulation_rate_pct": round(manip_rate, 2)
        },
        "manipulation_diagnostics": {
            "global_splits": {
                "manipulation_present": global_manip,
                "manipulation_absent": global_non_manip
            },
            "assets": asset_diagnostics,
            "levels": level_diagnostics,
            "hourly_degradation": hourly_manip_degradation,
            "rankings": {
                "asset_manipulation_frequency": ranked_by_frequency,
                "asset_manipulation_damage": ranked_by_damage,
                "weak_utc_hours": weak_hours
            }
        }
    }

    summary_file = report_root / "summary_statistics.json"
    with summary_file.open("w", encoding="utf-8") as f:
        json.dump(summary_stats, f, indent=2)

    # C. Markdown Mismatch Audit Report
    audit_file = report_root / "mismatch_audit.md"
    with audit_file.open("w", encoding="utf-8") as f:
        f.write(f"# Historical Analyzer Mismatch Audit & Diagnostics\n\n")
        f.write(f"**Run Timestamp (UTC):** {summary_stats['metadata']['run_timestamp_utc']}\n")
        f.write(f"**Sessions Analyzed:** {summary_stats['metadata']['sessions_analyzed']}\n\n")
        
        f.write(f"## Executive Summary\n\n")
        f.write(f"| Metric | Count |\n")
        f.write(f"| --- | --- |\n")
        f.write(f"| Total Ghost Trades Parsed | {summary_stats['totals']['total_ghost_trades_parsed']} |\n")
        f.write(f"| Successfully Joined | {summary_stats['totals']['successfully_joined']} |\n")
        f.write(f"| Unjoined (Missing Signals) | {summary_stats['totals']['unjoined_missing_signals']} |\n")
        f.write(f"| Unjoined (Ambiguous Matches) | {summary_stats['totals']['unjoined_ambiguous']} |\n")
        f.write(f"| Missing Tick Files | {summary_stats['totals']['missing_tick_files']} |\n")
        f.write(f"| Parsing Validation Errors/Warnings | {summary_stats['totals']['parsing_validation_warnings']} |\n\n")

        # Add Manipulation Diagnostics Section
        f.write(f"## Manipulation-First Diagnostics\n\n")
        f.write(f"### Global Performance Splits\n\n")
        f.write(f"| Setup Context | Trades | Settled | Wins | Losses | Win Rate | Net Profit | Expectancy |\n")
        f.write(f"| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        f.write(f"| Manipulation Present | {global_manip['total_trades']} | {global_manip['settled_trades']} | {global_manip['wins']} | {global_manip['losses']} | {global_manip['win_rate_pct']}% | ${global_manip['net_profit']:.2f} | {global_manip['expectancy']:.4f} |\n")
        f.write(f"| Manipulation Absent | {global_non_manip['total_trades']} | {global_non_manip['settled_trades']} | {global_non_manip['wins']} | {global_non_manip['losses']} | {global_non_manip['win_rate_pct']}% | ${global_non_manip['net_profit']:.2f} | {global_non_manip['expectancy']:.4f} |\n\n")

        f.write(f"### Asset Performance Degradation Under Manipulation\n\n")
        f.write(f"Ranked by **Manipulation Frequency**:\n\n")
        f.write(f"| Asset | Total Trades | Manipulation Rate | Manip WR | Non-Manip WR | WR Delta | Expectancy Delta | Damage Factor |\n")
        f.write(f"| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for rank in ranked_by_frequency:
            asset = rank["asset"]
            diag = asset_diagnostics[asset]
            warn = " ⚠️" if diag["manipulation_stats"]["small_sample_warning"] or diag["non_manipulation_stats"]["small_sample_warning"] else ""
            f.write(f"| {asset} | {diag['total_trades']} | {diag['manipulation_rate_pct']}% | {diag['manipulation_stats']['win_rate_pct']}% | {diag['non_manipulation_stats']['win_rate_pct']}% | {diag['win_rate_delta_pct']}% | {diag['expectancy_delta']:.4f} | {diag['damage_factor']:.4f}{warn} |\n")
        f.write(f"\n_⚠️ denotes small sample sizes (less than 5 trades) in one or both of the splits._\n\n")

        f.write(f"### Strategy Level Vulnerability Analysis\n\n")
        f.write(f"| Strategy Level | Total Trades | Manip Trades | Manip WR | Non-Manip WR | Win Rate Delta |\n")
        f.write(f"| --- | --- | --- | --- | --- | --- |\n")
        for lvl, diag in sorted(level_diagnostics.items()):
            m_wr = diag["manipulation_stats"]["win_rate_pct"]
            nm_wr = diag["non_manipulation_stats"]["win_rate_pct"]
            delta = round(m_wr - nm_wr, 2)
            f.write(f"| {lvl.upper()} | {diag['total_trades']} | {diag['manipulation_stats']['total_trades']} | {m_wr}% | {nm_wr}% | {delta}% |\n")
        f.write(f"\n")

        f.write(f"### Weakest UTC Hourly Windows Under Manipulation\n\n")
        f.write(f"Sorted by **Win Rate Degradation** (where manipulation hurt performance the most):\n\n")
        f.write(f"| Hour (UTC) | Total Trades | Manip Trades | Manip WR | Non-Manip WR | Degradation |\n")
        f.write(f"| --- | --- | --- | --- | --- | --- |\n")
        for wh in weak_hours[:10]:
            hour = wh["hour"]
            h_data = hourly_manip_degradation[hour]
            f.write(f"| {hour} | {h_data['total_trades']} | {h_data['manip_trades']} | {h_data['manip_win_rate_pct']}% | {h_data['non_manip_win_rate_pct']}% | {h_data['win_rate_degradation_pct']}% |\n")
        f.write(f"\n")

        if unjoined_missing_signals:
            f.write(f"## Unjoined Trades (Missing Signals)\n\n")
            f.write(f"| Trade ID | Session ID | Asset | Direction | Entry Time (UTC) | Price |\n")
            f.write(f"| --- | --- | --- | --- | --- | --- |\n")
            for ut in unjoined_missing_signals[:100]:
                f.write(f"| {ut['id']} | {ut['session_id']} | {ut['asset']} | {ut['direction']} | {format_utc_datetime(ut['entry_time'])} | {ut['entry_price']} |\n")
            if len(unjoined_missing_signals) > 100:
                f.write(f"\n_...and {len(unjoined_missing_signals) - 100} more unjoined trades._\n")
            f.write(f"\n")

        if ambiguous_joins:
            f.write(f"## Ambiguous Join Audits\n\n")
            f.write(f"| Trade ID | Asset | Direction | Entry Time (UTC) | Match Details |\n")
            f.write(f"| --- | --- | --- | --- | --- |\n")
            for aj in ambiguous_joins:
                tr = aj["trade"]
                f.write(f"| {tr['id']} | {tr['asset']} | {tr['direction']} | {format_utc_datetime(tr['entry_time'])} | {aj['error']} |\n")
            f.write(f"\n")

        if missing_tick_files:
            f.write(f"## Missing Tick Log Files\n\n")
            f.write(f"| Trade ID | Asset | UTC Date | Expected File Path |\n")
            f.write(f"| --- | --- | --- | --- |\n")
            for mt in missing_tick_files:
                tr = mt["trade"]
                dt = datetime.fromtimestamp(tr["entry_time"], tz=timezone.utc).strftime("%Y-%m-%d")
                f.write(f"| {tr['id']} | {tr['asset']} | {dt} | `{mt['expected_path']}` |\n")
            f.write(f"\n")

        if parsing_warnings:
            f.write(f"## Parsing & Schema Warnings\n\n")
            f.write(f"| File | Line | Details |\n")
            f.write(f"| --- | --- | --- |\n")
            for pw in parsing_warnings[:100]:
                f.write(f"| {pw['file']} | {pw['line']} | {pw['error']} |\n")
            if len(parsing_warnings) > 100:
                f.write(f"\n_...and {len(parsing_warnings) - 100} more parsing warnings._\n")
            f.write(f"\n")

    print("\nPhase 1 Join complete. Outputs written to:")
    print(f"  - CSV Joined Ledger:  {csv_file}")
    print(f"  - Summary Statistics: {summary_file}")
    print(f"  - Mismatch Audit Report: {audit_file}")
    print("Success.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
