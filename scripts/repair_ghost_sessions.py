from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EPSILON = 1e-6


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_session_date(row: dict[str, Any]) -> str | None:
    session_date = row.get("date") or row.get("session_date") or row.get("recorded_date")
    if session_date:
        return str(session_date)

    timestamp = _float_or_none(row.get("entry_time"))
    if timestamp is None:
        timestamp = _float_or_none(row.get("timestamp"))
    if timestamp is None:
        return None

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")


def _detect_issues(row: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    entry_context = row.get("entry_context") or {}

    entry_time = _float_or_none(row.get("entry_time"))
    exit_time = _float_or_none(row.get("exit_time"))
    entry_price = _float_or_none(row.get("entry_price"))
    context_price = _float_or_none(entry_context.get("price"))

    if entry_time is not None and exit_time is not None and exit_time + 1 < entry_time:
        issues.append("backwards_exit_time")

    if entry_price is not None and context_price is not None and abs(entry_price - context_price) > EPSILON:
        issues.append("entry_price_mismatch")

    return issues


def _repair_row(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    issues = _detect_issues(row)
    if not issues:
        return row, None

    repaired = deepcopy(row)
    entry_context = repaired.get("entry_context") or {}
    context_price = _float_or_none(entry_context.get("price"))

    original_snapshot = {
        "entry_price": row.get("entry_price"),
        "exit_price": row.get("exit_price"),
        "exit_time": row.get("exit_time"),
        "outcome": row.get("outcome"),
        "profit": row.get("profit"),
        "simulated_profit": row.get("simulated_profit"),
    }

    if context_price is not None:
        repaired["entry_price"] = context_price

    # The real exit tick cannot be reconstructed from the corrupted row alone.
    # Clear outcome fields rather than inventing a false historical result.
    repaired["exit_price"] = None
    repaired["exit_time"] = None
    repaired["outcome"] = "void"
    repaired["profit"] = 0.0
    if "simulated_profit" in repaired:
        repaired["simulated_profit"] = 0.0

    manifest_entry = {
        "id": row.get("id"),
        "trade_id": row.get("trade_id"),
        "asset": row.get("asset"),
        "issues": issues,
        "original": original_snapshot,
        "repaired": {
            "entry_price": repaired.get("entry_price"),
            "exit_price": repaired.get("exit_price"),
            "exit_time": repaired.get("exit_time"),
            "outcome": repaired.get("outcome"),
            "profit": repaired.get("profit"),
            "simulated_profit": repaired.get("simulated_profit"),
        },
    }
    return repaired, manifest_entry


def _iter_session_files(sessions_dir: Path) -> list[Path]:
    return sorted(path for path in sessions_dir.glob("*.jsonl") if path.is_file())


def repair_sessions(
    sessions_dir: Path,
    output_dir: Path,
    start_date: str,
) -> dict[str, Any]:
    output_sessions_dir = output_dir / "sessions"
    output_quarantine_dir = output_dir / "quarantine"
    output_sessions_dir.mkdir(parents=True, exist_ok=True)
    output_quarantine_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sessions_dir": str(sessions_dir),
        "start_date": start_date,
        "repaired_sessions": [],
        "summary": {
            "sessions_scanned": 0,
            "sessions_copied": 0,
            "sessions_repaired": 0,
            "rows_repaired": 0,
        },
    }

    for session_file in _iter_session_files(sessions_dir):
        rows: list[dict[str, Any]] = []
        repaired_rows: list[dict[str, Any]] = []
        quarantine_rows: list[dict[str, Any]] = []
        repaired_entries: list[dict[str, Any]] = []
        relevant = False

        with session_file.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                row = json.loads(raw_line)
                rows.append(row)
                session_date = _resolve_session_date(row)
                if session_date is None or session_date < start_date:
                    repaired_rows.append(row)
                    continue

                relevant = True
                repaired_row, manifest_entry = _repair_row(row)
                repaired_rows.append(repaired_row)
                if manifest_entry is not None:
                    repaired_entries.append(manifest_entry)
                    quarantine_rows.append(row)

        if not relevant:
            continue

        manifest["summary"]["sessions_scanned"] += 1

        target_session_file = output_sessions_dir / session_file.name
        with target_session_file.open("w", encoding="utf-8") as handle:
            for row in repaired_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        manifest["summary"]["sessions_copied"] += 1

        if repaired_entries:
            quarantine_file = output_quarantine_dir / session_file.name
            with quarantine_file.open("w", encoding="utf-8") as handle:
                for row in quarantine_rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")

            manifest["summary"]["sessions_repaired"] += 1
            manifest["summary"]["rows_repaired"] += len(repaired_entries)
            manifest["repaired_sessions"].append(
                {
                    "session_file": session_file.name,
                    "rows_repaired": len(repaired_entries),
                    "quarantine_file": str(quarantine_file),
                    "repaired_rows": repaired_entries,
                }
            )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate non-destructive repaired copies of ghost trade sessions affected by stale ticks."
    )
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        default=Path("app/data/ghost_trades/sessions"),
        help="Source directory containing ghost trade session JSONL files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Target directory for repaired session copies. Defaults to a timestamped folder under app/data/ghost_trades/repairs.",
    )
    parser.add_argument(
        "--start-date",
        default="2026-04-24",
        help="Only process session rows on or after this UTC date (YYYY-MM-DD).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    sessions_dir = args.sessions_dir.resolve()
    if not sessions_dir.exists():
        raise FileNotFoundError(f"Sessions directory does not exist: {sessions_dir}")

    if args.output_dir is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = Path("app/data/ghost_trades/repairs") / f"repair_{stamp}"
    else:
        output_dir = args.output_dir
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = repair_sessions(
        sessions_dir=sessions_dir,
        output_dir=output_dir,
        start_date=args.start_date,
    )

    summary = manifest["summary"]
    print(f"Repair output: {output_dir}")
    print(f"Sessions scanned: {summary['sessions_scanned']}")
    print(f"Sessions copied: {summary['sessions_copied']}")
    print(f"Sessions repaired: {summary['sessions_repaired']}")
    print(f"Rows repaired: {summary['rows_repaired']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
