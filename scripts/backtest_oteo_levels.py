from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from bisect import bisect_left
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.backend.services.market_context import MarketContextEngine, apply_level2_policy, apply_level3_policy
from app.backend.services.oteo import OTEO
from app.backend.services.regime_classifier import RegimeClassifier


DEFAULT_EXPIRY_SECONDS = [15, 30, 60, 90, 120, 180, 300]
DEFAULT_TICK_ROOT = Path("app/data/tick_logs")
DEFAULT_GHOST_SESSION_ROOT = Path("app/data/ghost_trades/sessions")
DEFAULT_REPORT_ROOT = Path("@reports/backtests")

# Minimum settled trades required before a win-rate recommendation is meaningful.
MIN_SAMPLE_SIZE = 30
# Win-rate threshold below which an asset/expiry is flagged as an exclusion candidate.
EXCLUSION_WIN_RATE_THRESHOLD = 45.0
# Breakeven win-rate for a given payout percentage: 1 / (1 + payout_pct/100).
# At 92 % payout this is ~52.08 %.  Computed dynamically in the report.
CSV_FIELDNAMES = [
    "date",
    "asset",
    "level",
    "entry_time",
    "entry_price",
    "direction",
    "expiry_seconds",
    "exit_time",
    "exit_price",
    "price_delta",
    "outcome",
    "net_pl",
    "payout_pct",
    "oteo_score",
    "confidence",
    "base_oteo_score",
    "base_confidence",
    "level2_score_adjustment",
    "level2_suppressed_reason",
    "level3_score_adjustment",
    "level3_suppressed_reason",
    "market_ready",
    "adx_regime",
    "trend_direction",
    "cci_state",
    "tick_health",
    "regime_label",
    "regime_confidence",
    "regime_stable",
    "regime_prior",
    "regime_persistence",
    "source_session",
    "original_expiration_seconds",
    "original_outcome",
    "original_exit_time",
    "original_exit_price",
    "strategy_level",
    "trade_id",
]


class TickSchemaError(ValueError):
    """Raised when a tick JSONL row does not match the required backtest schema."""


class GhostTradeSchemaError(ValueError):
    """Raised when a ghost trade JSONL row lacks fields required for repricing."""


@dataclass(frozen=True)
class Tick:
    timestamp: float
    price: float
    asset: str

    def as_dict(self) -> dict[str, Any]:
        return {"t": self.timestamp, "p": self.price, "a": self.asset}


@dataclass(frozen=True)
class BacktestConfig:
    expiry_seconds: list[int] = field(default_factory=lambda: list(DEFAULT_EXPIRY_SECONDS))
    payout_pct: float = 92.0


@dataclass(frozen=True)
class GhostTrade:
    id: str
    source_session: str
    asset: str
    direction: str
    entry_time: float
    entry_price: float
    original_expiration_seconds: int | None = None
    original_outcome: str | None = None
    original_exit_time: float | None = None
    original_exit_price: float | None = None
    payout_pct: float | None = None
    confidence: str | None = None
    oteo_score: float | None = None
    strategy_level: str | None = None
    trade_id: str | None = None


StackFactory = Callable[[], tuple[Any, Any, Any]]


def _production_stack_factory() -> tuple[OTEO, MarketContextEngine, RegimeClassifier]:
    return OTEO(), MarketContextEngine(), RegimeClassifier()


def _require_finite_number(value: Any, *, field_name: str, path: Path, line_number: int) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TickSchemaError(
            f"{path}:{line_number} field '{field_name}' must be numeric, got {value!r}"
        ) from exc
    if not math.isfinite(number):
        raise TickSchemaError(f"{path}:{line_number} field '{field_name}' must be finite, got {value!r}")
    return number


def _validate_tick_row(row: Any, *, path: Path, line_number: int) -> Tick:
    if not isinstance(row, dict):
        raise TickSchemaError(f"{path}:{line_number} tick row must be a JSON object")

    for required in ("t", "p", "a"):
        if required not in row:
            raise TickSchemaError(f"{path}:{line_number} missing required field '{required}'")

    timestamp = _require_finite_number(row["t"], field_name="t", path=path, line_number=line_number)
    price = _require_finite_number(row["p"], field_name="p", path=path, line_number=line_number)
    asset = str(row["a"]).strip()
    if not asset:
        raise TickSchemaError(f"{path}:{line_number} field 'a' must be a non-empty asset string")
    return Tick(timestamp=timestamp, price=price, asset=asset)


def load_ticks_from_file(path: Path | str) -> list[Tick]:
    tick_path = Path(path)
    if not tick_path.exists():
        raise FileNotFoundError(f"Tick file not found: {tick_path}")

    ticks: list[Tick] = []
    with tick_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TickSchemaError(f"{tick_path}:{line_number} invalid JSON: {exc.msg}") from exc
            ticks.append(_validate_tick_row(row, path=tick_path, line_number=line_number))

    return sorted(ticks, key=lambda tick: tick.timestamp)


def _require_ghost_number(value: Any, *, field_name: str, path: Path, line_number: int) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise GhostTradeSchemaError(
            f"{path}:{line_number} field '{field_name}' must be numeric, got {value!r}"
        ) from exc
    if not math.isfinite(number):
        raise GhostTradeSchemaError(f"{path}:{line_number} field '{field_name}' must be finite, got {value!r}")
    return number


def _optional_ghost_number(value: Any, *, field_name: str, path: Path, line_number: int) -> float | None:
    if value is None:
        return None
    return _require_ghost_number(value, field_name=field_name, path=path, line_number=line_number)


def _validate_ghost_trade_row(row: Any, *, path: Path, line_number: int) -> GhostTrade:
    if not isinstance(row, dict):
        raise GhostTradeSchemaError(f"{path}:{line_number} ghost trade row must be a JSON object")

    for required in ("asset", "direction", "entry_time", "entry_price"):
        if required not in row:
            raise GhostTradeSchemaError(f"{path}:{line_number} missing required field '{required}'")

    asset = str(row["asset"]).strip()
    if not asset:
        raise GhostTradeSchemaError(f"{path}:{line_number} field 'asset' must be non-empty")

    direction = str(row["direction"]).upper()
    if direction not in {"CALL", "PUT"}:
        raise GhostTradeSchemaError(f"{path}:{line_number} direction must be CALL or PUT, got {row['direction']!r}")

    original_expiration = row.get("expiration_seconds")
    if original_expiration is not None:
        original_expiration = int(_require_ghost_number(
            original_expiration,
            field_name="expiration_seconds",
            path=path,
            line_number=line_number,
        ))

    return GhostTrade(
        id=str(row.get("id") or row.get("trade_id") or f"{path.stem}:{line_number}"),
        source_session=str(row.get("session_id") or path.stem),
        asset=asset,
        direction=direction,
        entry_time=_require_ghost_number(row["entry_time"], field_name="entry_time", path=path, line_number=line_number),
        entry_price=_require_ghost_number(row["entry_price"], field_name="entry_price", path=path, line_number=line_number),
        original_expiration_seconds=original_expiration,
        original_outcome=str(row["outcome"]) if row.get("outcome") is not None else None,
        original_exit_time=_optional_ghost_number(row.get("exit_time"), field_name="exit_time", path=path, line_number=line_number),
        original_exit_price=_optional_ghost_number(row.get("exit_price"), field_name="exit_price", path=path, line_number=line_number),
        payout_pct=_optional_ghost_number(row.get("payout_pct"), field_name="payout_pct", path=path, line_number=line_number),
        confidence=str(row["confidence"]) if row.get("confidence") is not None else None,
        oteo_score=_optional_ghost_number(row.get("oteo_score"), field_name="oteo_score", path=path, line_number=line_number),
        strategy_level=str(row["strategy_level"]) if row.get("strategy_level") is not None else None,
        trade_id=str(row["trade_id"]) if row.get("trade_id") is not None else None,
    )


def load_ghost_trades_from_file(path: Path | str) -> list[GhostTrade]:
    ghost_path = Path(path)
    if not ghost_path.exists():
        raise FileNotFoundError(f"Ghost session file not found: {ghost_path}")

    trades: list[GhostTrade] = []
    with ghost_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GhostTradeSchemaError(f"{ghost_path}:{line_number} invalid JSON: {exc.msg}") from exc
            trades.append(_validate_ghost_trade_row(row, path=ghost_path, line_number=line_number))
    return trades


def _tick_value(tick: Tick | dict[str, Any], key: str) -> Any:
    if isinstance(tick, Tick):
        if key == "t":
            return tick.timestamp
        if key == "p":
            return tick.price
        if key == "a":
            return tick.asset
    return tick[key]


def evaluate_expiry(
    ticks: Sequence[Tick | dict[str, Any]],
    entry_time: float,
    entry_price: float,
    direction: str,
    expiry_seconds: int,
) -> dict[str, Any]:
    if direction not in {"CALL", "PUT"}:
        raise ValueError(f"evaluate_expiry: direction must be CALL or PUT, got {direction!r}")
    if expiry_seconds <= 0:
        raise ValueError(f"evaluate_expiry: expiry_seconds must be positive, got {expiry_seconds!r}")

    if not ticks:
        return {"outcome": "insufficient_data", "exit_time": None, "exit_price": None, "price_delta": None}

    target_time = float(entry_time) + float(expiry_seconds)
    timestamps = [float(_tick_value(tick, "t")) for tick in ticks]
    exit_index = bisect_left(timestamps, target_time)
    if exit_index >= len(ticks):
        return {"outcome": "missing_exit", "exit_time": None, "exit_price": None, "price_delta": None}

    exit_tick = ticks[exit_index]
    exit_time = float(_tick_value(exit_tick, "t"))
    exit_price = float(_tick_value(exit_tick, "p"))
    price_delta = exit_price - float(entry_price)

    if price_delta == 0:
        outcome = "draw"
    elif direction == "CALL":
        outcome = "win" if price_delta > 0 else "loss"
    else:
        outcome = "win" if price_delta < 0 else "loss"

    return {
        "outcome": outcome,
        "exit_time": exit_time,
        "exit_price": exit_price,
        "price_delta": round(price_delta, 8),
    }


def _normalise_ticks(raw_ticks: Sequence[Tick | dict[str, Any]], asset: str) -> list[Tick]:
    normalised: list[Tick] = []
    for index, raw_tick in enumerate(raw_ticks, start=1):
        if isinstance(raw_tick, Tick):
            tick = raw_tick
        else:
            tick = _validate_tick_row(raw_tick, path=Path("<memory>"), line_number=index)
        if tick.asset != asset:
            raise TickSchemaError(f"<memory>:{index} expected asset {asset!r}, got {tick.asset!r}")
        normalised.append(tick)
    return sorted(normalised, key=lambda tick: tick.timestamp)


def _compact_regime(regime: dict[str, Any] | None) -> dict[str, Any]:
    regime = regime or {}
    return {
        "regime_label": regime.get("regime_label"),
        "regime_confidence": regime.get("regime_confidence"),
        "regime_stable": regime.get("regime_stable"),
        "regime_prior": regime.get("regime_prior"),
        "regime_persistence": regime.get("regime_persistence"),
    }


class BacktestRunner:
    def __init__(self, config: BacktestConfig | None = None, stack_factory: StackFactory | None = None) -> None:
        self.config = config or BacktestConfig()
        self.stack_factory = stack_factory or _production_stack_factory

    def replay_asset_ticks(
        self,
        asset: str,
        ticks: Sequence[Tick | dict[str, Any]],
        *,
        date: str | None = None,
    ) -> list[dict[str, Any]]:
        ordered_ticks = _normalise_ticks(ticks, asset)
        if len(ordered_ticks) < 2:
            return []

        oteo, market_context_engine, regime_classifier = self.stack_factory()
        last_regime: dict[str, Any] | None = None
        rows: list[dict[str, Any]] = []

        for tick in ordered_ticks:
            oteo_result = oteo.update_tick(tick.price, timestamp=tick.timestamp)
            market_context = market_context_engine.update_tick(tick.price, timestamp=tick.timestamp)
            if bool(market_context.get("candle_closed")) and bool(market_context.get("ready")):
                last_regime = regime_classifier.classify(market_context)

            if not isinstance(oteo_result, dict):
                continue

            level1 = dict(oteo_result)
            level2 = apply_level2_policy(level1, market_context, enabled=True)
            level3 = None
            if last_regime is not None:
                level3 = apply_level3_policy(level2, market_context, last_regime)

            for level_name, signal in (("L1", level1), ("L2", level2), ("L3", level3)):
                if signal is None or not bool(signal.get("actionable")):
                    continue
                rows.extend(
                    self._rows_for_signal(
                        asset=asset,
                        date=date,
                        tick=tick,
                        level_name=level_name,
                        signal=signal,
                        market_context=market_context,
                        regime=last_regime,
                        ticks=ordered_ticks,
                    )
                )

        return rows

    def _rows_for_signal(
        self,
        *,
        asset: str,
        date: str | None,
        tick: Tick,
        level_name: str,
        signal: dict[str, Any],
        market_context: dict[str, Any],
        regime: dict[str, Any] | None,
        ticks: Sequence[Tick],
    ) -> list[dict[str, Any]]:
        direction = str(signal.get("recommended") or "").upper()
        if direction not in {"CALL", "PUT"}:
            return []

        rows = []
        for expiry_seconds in self.config.expiry_seconds:
            expiry = evaluate_expiry(ticks, tick.timestamp, tick.price, direction, int(expiry_seconds))
            net_pl = _net_pl_for_outcome(expiry["outcome"], self.config.payout_pct)
            row = {
                "date": date,
                "asset": asset,
                "level": level_name,
                "entry_time": tick.timestamp,
                "entry_price": tick.price,
                "direction": direction,
                "expiry_seconds": int(expiry_seconds),
                "exit_time": expiry["exit_time"],
                "exit_price": expiry["exit_price"],
                "price_delta": expiry["price_delta"],
                "outcome": expiry["outcome"],
                "net_pl": net_pl,
                "payout_pct": self.config.payout_pct,
                "oteo_score": signal.get("oteo_score"),
                "confidence": signal.get("confidence"),
                "base_oteo_score": signal.get("base_oteo_score", signal.get("oteo_score")),
                "base_confidence": signal.get("base_confidence", signal.get("confidence")),
                "level2_score_adjustment": signal.get("level2_score_adjustment", 0.0),
                "level2_suppressed_reason": signal.get("level2_suppressed_reason"),
                "level3_score_adjustment": signal.get("level3_score_adjustment", 0.0),
                "level3_suppressed_reason": signal.get("level3_suppressed_reason"),
                "market_ready": market_context.get("ready"),
                "adx_regime": market_context.get("adx_regime"),
                "trend_direction": market_context.get("trend_direction"),
                "cci_state": market_context.get("cci_state"),
                "tick_health": market_context.get("tick_health"),
                **_compact_regime(regime),
            }
            rows.append(row)
        return rows

    def summarize(self, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
        return {
            "overall": _summarize_group(rows),
            "by_level_expiry": _summarize_by(rows, ("level", "expiry_seconds")),
            "by_asset_expiry": _summarize_by(rows, ("asset", "expiry_seconds")),
            "by_regime_expiry": _summarize_by(rows, ("regime_label", "expiry_seconds")),
            "by_confidence_expiry": _summarize_by(rows, ("confidence", "expiry_seconds")),
        }


def _net_pl_for_outcome(outcome: str, payout_pct: float) -> float:
    if outcome == "win":
        return round(float(payout_pct) / 100.0, 6)
    if outcome == "loss":
        return -1.0
    return 0.0


def _summarize_group(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    trades = len(rows)
    wins = sum(1 for row in rows if row.get("outcome") == "win")
    losses = sum(1 for row in rows if row.get("outcome") == "loss")
    draws = sum(1 for row in rows if row.get("outcome") == "draw")
    missing_exit = sum(1 for row in rows if row.get("outcome") == "missing_exit")
    insufficient_data = sum(1 for row in rows if row.get("outcome") == "insufficient_data")
    settled = wins + losses
    net_pl = round(sum(float(row.get("net_pl") or 0.0) for row in rows), 6)
    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "missing_exit": missing_exit,
        "insufficient_data": insufficient_data,
        "win_rate": round((wins / settled) * 100.0, 2) if settled else 0.0,
        "net_pl": net_pl,
        "roi": round((net_pl / settled) * 100.0, 2) if settled else 0.0,
    }


def _summarize_by(rows: Sequence[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = "|".join(str(row.get(field)) for field in fields)
        grouped.setdefault(key, []).append(row)
    return {key: _summarize_group(group_rows) for key, group_rows in sorted(grouped.items())}


def _date_for_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(float(timestamp), timezone.utc).strftime("%Y-%m-%d")


def _resolve_ghost_session_files(session_root: Path, sessions: Sequence[str] | None) -> list[Path]:
    if not session_root.exists():
        raise FileNotFoundError(f"Ghost session root not found: {session_root}")
    if sessions:
        files = []
        for session in sessions:
            session_path = Path(session)
            if session_path.suffix == ".jsonl" or session_path.parent != Path("."):
                path = session_path
            else:
                path = session_root / f"{session}.jsonl"
            if not path.exists():
                raise FileNotFoundError(f"Ghost session file not found: {path}")
            files.append(path)
        return files

    files = sorted(path for path in session_root.glob("*.jsonl") if path.is_file())
    if not files:
        raise FileNotFoundError(f"No ghost session files found under {session_root}")
    return files


def _tick_file_for_ghost_trade(tick_root: Path, trade: GhostTrade) -> Path:
    date = _date_for_timestamp(trade.entry_time)
    path = tick_root / trade.asset / f"{date}.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            "Missing tick file for ghost trade "
            f"id={trade.id!r} asset={trade.asset!r} date={date!r}: {path}"
        )
    return path


def reprice_ghost_trades(
    session_files: Sequence[Path | str],
    *,
    tick_root: Path,
    expiry_seconds: Sequence[int],
    payout_pct: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    tick_cache: dict[Path, list[Tick]] = {}

    for session_file in session_files:
        for trade in load_ghost_trades_from_file(session_file):
            tick_file = _tick_file_for_ghost_trade(tick_root, trade)
            if tick_file not in tick_cache:
                tick_cache[tick_file] = load_ticks_from_file(tick_file)
            ticks = tick_cache[tick_file]
            trade_payout_pct = trade.payout_pct if trade.payout_pct is not None else float(payout_pct)

            for expiry in expiry_seconds:
                expiry_result = evaluate_expiry(ticks, trade.entry_time, trade.entry_price, trade.direction, int(expiry))
                rows.append({
                    "date": tick_file.stem,
                    "asset": trade.asset,
                    "level": "GHOST_REPRICE",
                    "entry_time": trade.entry_time,
                    "entry_price": trade.entry_price,
                    "direction": trade.direction,
                    "expiry_seconds": int(expiry),
                    "exit_time": expiry_result["exit_time"],
                    "exit_price": expiry_result["exit_price"],
                    "price_delta": expiry_result["price_delta"],
                    "outcome": expiry_result["outcome"],
                    "net_pl": _net_pl_for_outcome(expiry_result["outcome"], trade_payout_pct),
                    "payout_pct": trade_payout_pct,
                    "oteo_score": trade.oteo_score,
                    "confidence": trade.confidence,
                    "source_session": trade.source_session,
                    "original_expiration_seconds": trade.original_expiration_seconds,
                    "original_outcome": trade.original_outcome,
                    "original_exit_time": trade.original_exit_time,
                    "original_exit_price": trade.original_exit_price,
                    "strategy_level": trade.strategy_level,
                    "trade_id": trade.trade_id,
                })

    return rows


def _resolve_tick_files(tick_root: Path, dates: Sequence[str], assets: Sequence[str] | None) -> list[Path]:
    if not dates:
        raise ValueError("At least one --dates value is required")
    candidate_assets = list(assets or [])
    if not candidate_assets:
        candidate_assets = sorted(path.name for path in tick_root.iterdir() if path.is_dir())

    files: list[Path] = []
    for asset in candidate_assets:
        for date in dates:
            path = tick_root / asset / f"{date}.jsonl"
            if path.exists():
                files.append(path)
    if not files:
        raise FileNotFoundError(
            f"No tick files found under {tick_root} for dates={list(dates)!r} assets={candidate_assets!r}"
        )
    return files


# ---------------------------------------------------------------------------
# Phase 3 — Markdown analysis report + recommendation matrices
# ---------------------------------------------------------------------------

def _breakeven_win_rate(payout_pct: float) -> float:
    """Return the minimum win-rate (%) needed to break even at *payout_pct*."""
    return round(100.0 / (1.0 + payout_pct / 100.0), 2)


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}%"


def _fmt_float(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def _sample_label(settled: int, min_sample: int) -> str:
    """Return a warning tag when the sample is too small to be reliable."""
    return "" if settled >= min_sample else f" ⚠️ n={settled}"


def _matrix_table(
    grouped: dict[str, dict[str, Any]],
    row_label: str,
    col_label: str,
    payout_pct: float,
    min_sample: int,
) -> list[str]:
    """Render a Markdown table from a `_summarize_by` result keyed as 'row|col'."""
    # Collect unique row/col values preserving insertion order.
    row_keys: list[str] = []
    col_keys: list[str] = []
    for key in grouped:
        parts = key.split("|", 1)
        r, c = (parts[0], parts[1]) if len(parts) == 2 else (parts[0], "")
        if r not in row_keys:
            row_keys.append(r)
        if c not in col_keys:
            col_keys.append(c)

    col_keys_sorted = sorted(col_keys, key=lambda x: (int(x) if x.lstrip("-").isdigit() else 0, x))

    header = f"| {row_label} \\ {col_label} | " + " | ".join(col_keys_sorted) + " |"
    separator = "| --- | " + " | ".join("---" for _ in col_keys_sorted) + " |"
    lines = [header, separator]

    for r in sorted(row_keys):
        cells = []
        for c in col_keys_sorted:
            key = f"{r}|{c}"
            stats = grouped.get(key)
            if stats is None:
                cells.append("—")
            else:
                settled = stats["wins"] + stats["losses"]
                wr = _fmt_pct(stats["win_rate"] if settled else None)
                tag = _sample_label(settled, min_sample)
                cells.append(f"{wr}{tag}")
        lines.append(f"| {r} | " + " | ".join(cells) + " |")

    return lines


def _suppression_audit(rows: Sequence[dict[str, Any]]) -> list[str]:
    """Count how often each Level 2 / Level 3 suppression reason appears."""
    l2_counts: dict[str, int] = {}
    l3_counts: dict[str, int] = {}
    for row in rows:
        reason2 = row.get("level2_suppressed_reason")
        if reason2:
            l2_counts[str(reason2)] = l2_counts.get(str(reason2), 0) + 1
        reason3 = row.get("level3_suppressed_reason")
        if reason3:
            l3_counts[str(reason3)] = l3_counts.get(str(reason3), 0) + 1

    lines: list[str] = []
    lines.append("### Level 2 Suppression Reasons")
    if l2_counts:
        lines.append("| Reason | Count |")
        lines.append("| --- | --- |")
        for reason, count in sorted(l2_counts.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {reason} | {count} |")
    else:
        lines.append("_No Level 2 suppressions recorded._")

    lines.append("")
    lines.append("### Level 3 Suppression Reasons")
    if l3_counts:
        lines.append("| Reason | Count |")
        lines.append("| --- | --- |")
        for reason, count in sorted(l3_counts.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {reason} | {count} |")
    else:
        lines.append("_No Level 3 suppressions recorded._")

    return lines


def _recommendations(
    summary: dict[str, Any],
    payout_pct: float,
    min_sample: int,
    exclusion_threshold: float,
) -> list[str]:
    """Generate deterministic recommendation bullets from the summary data."""
    breakeven = _breakeven_win_rate(payout_pct)
    lines: list[str] = []
    lines.append(f"Breakeven win-rate at {payout_pct:.0f}% payout: **{breakeven:.2f}%**")
    lines.append("")

    # Overall edge check.
    overall = summary.get("overall", {})
    overall_settled = overall.get("wins", 0) + overall.get("losses", 0)
    overall_wr = overall.get("win_rate", 0.0)
    if overall_settled < min_sample:
        lines.append(
            f"⚠️ **Insufficient overall sample** — only {overall_settled} settled trades "
            f"(minimum {min_sample} required for reliable conclusions)."
        )
    elif overall_wr < breakeven:
        lines.append(
            f"🔴 **Overall win-rate {overall_wr:.1f}% is below breakeven {breakeven:.2f}%** — "
            "the current strategy configuration does not have a positive edge at this payout."
        )
    else:
        lines.append(
            f"✅ **Overall win-rate {overall_wr:.1f}% exceeds breakeven {breakeven:.2f}%** — "
            "positive edge detected across the full sample."
        )

    lines.append("")

    # Asset exclusion candidates.
    by_asset_expiry = summary.get("by_asset_expiry", {})
    asset_stats: dict[str, dict[str, Any]] = {}
    for key, stats in by_asset_expiry.items():
        asset = key.split("|")[0]
        existing = asset_stats.get(asset)
        if existing is None:
            asset_stats[asset] = dict(stats)
        else:
            # Aggregate across expiries for the per-asset verdict.
            existing["wins"] = existing.get("wins", 0) + stats.get("wins", 0)
            existing["losses"] = existing.get("losses", 0) + stats.get("losses", 0)
            existing["trades"] = existing.get("trades", 0) + stats.get("trades", 0)

    exclusion_candidates: list[str] = []
    small_sample_assets: list[str] = []
    for asset, stats in sorted(asset_stats.items()):
        settled = stats.get("wins", 0) + stats.get("losses", 0)
        if settled < min_sample:
            small_sample_assets.append(f"{asset} (n={settled})")
            continue
        wr = round((stats["wins"] / settled) * 100.0, 2) if settled else 0.0
        if wr < exclusion_threshold:
            exclusion_candidates.append(f"{asset} ({wr:.1f}%)")

    if exclusion_candidates:
        lines.append(
            "🔴 **Asset exclusion candidates** (win-rate below "
            f"{exclusion_threshold:.0f}% across all expiries): "
            + ", ".join(exclusion_candidates)
        )
    else:
        lines.append("✅ No asset exclusion candidates detected.")

    if small_sample_assets:
        lines.append(
            f"⚠️ **Small-sample assets** (fewer than {min_sample} settled trades — "
            "results are not yet reliable): " + ", ".join(small_sample_assets)
        )

    lines.append("")

    # Best and worst expiry by overall win-rate.
    by_level_expiry = summary.get("by_level_expiry", {})
    expiry_stats: dict[int, dict[str, Any]] = {}
    for key, stats in by_level_expiry.items():
        parts = key.split("|")
        if len(parts) < 2:
            continue
        try:
            expiry = int(parts[1])
        except ValueError:
            continue
        existing = expiry_stats.get(expiry)
        if existing is None:
            expiry_stats[expiry] = dict(stats)
        else:
            existing["wins"] = existing.get("wins", 0) + stats.get("wins", 0)
            existing["losses"] = existing.get("losses", 0) + stats.get("losses", 0)
            existing["trades"] = existing.get("trades", 0) + stats.get("trades", 0)

    ranked_expiries = []
    for expiry, stats in sorted(expiry_stats.items()):
        settled = stats.get("wins", 0) + stats.get("losses", 0)
        if settled >= min_sample:
            wr = round((stats["wins"] / settled) * 100.0, 2)
            ranked_expiries.append((expiry, wr, settled))

    if ranked_expiries:
        ranked_expiries.sort(key=lambda t: -t[1])
        best = ranked_expiries[0]
        worst = ranked_expiries[-1]
        lines.append(
            f"📈 **Best expiry:** {best[0]}s — win-rate {best[1]:.1f}% (n={best[2]})"
        )
        lines.append(
            f"📉 **Worst expiry:** {worst[0]}s — win-rate {worst[1]:.1f}% (n={worst[2]})"
        )
    else:
        lines.append("⚠️ No expiry bucket has sufficient sample size for ranking.")

    return lines


def generate_markdown_report(
    rows: Sequence[dict[str, Any]],
    summary: dict[str, Any],
    *,
    title: str = "OTEO Backtest Analysis Report",
    payout_pct: float = 92.0,
    min_sample: int = MIN_SAMPLE_SIZE,
    exclusion_threshold: float = EXCLUSION_WIN_RATE_THRESHOLD,
    generated_at: str | None = None,
) -> str:
    """
    Produce a Markdown analysis report from backtest rows and their summary.

    Sections:
      1. Header + metadata
      2. Overall statistics
      3. Level × Expiry matrix
      4. Asset × Expiry matrix
      5. Regime × Expiry matrix
      6. Confidence × Expiry matrix
      7. Suppression audit
      8. Recommendations
    """
    ts = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_rows = len(rows)
    overall = summary.get("overall", {})
    settled = overall.get("wins", 0) + overall.get("losses", 0)

    md: list[str] = []

    # --- Header ---
    md.append(f"# {title}")
    md.append("")
    md.append(f"**Generated:** {ts}  ")
    md.append(f"**Total rows:** {total_rows}  ")
    md.append(f"**Settled trades:** {settled}  ")
    md.append(f"**Payout:** {payout_pct:.0f}%  ")
    md.append(f"**Breakeven win-rate:** {_breakeven_win_rate(payout_pct):.2f}%  ")
    md.append("")

    # --- Overall statistics ---
    md.append("## Overall Statistics")
    md.append("")
    md.append("| Metric | Value |")
    md.append("| --- | --- |")
    md.append(f"| Trades (rows) | {overall.get('trades', 0)} |")
    md.append(f"| Wins | {overall.get('wins', 0)} |")
    md.append(f"| Losses | {overall.get('losses', 0)} |")
    md.append(f"| Draws | {overall.get('draws', 0)} |")
    md.append(f"| Missing exit | {overall.get('missing_exit', 0)} |")
    md.append(f"| Insufficient data | {overall.get('insufficient_data', 0)} |")
    md.append(f"| Win-rate | {_fmt_pct(overall.get('win_rate'))} |")
    md.append(f"| Net P/L (units) | {_fmt_float(overall.get('net_pl'), 4)} |")
    md.append(f"| ROI | {_fmt_pct(overall.get('roi'))} |")
    md.append("")

    # --- Level × Expiry matrix ---
    md.append("## Level × Expiry Win-Rate Matrix")
    md.append("")
    md.append(
        f"_Win-rate per (Level, Expiry) cell. "
        f"⚠️ = fewer than {min_sample} settled trades — treat as indicative only._"
    )
    md.append("")
    md.extend(
        _matrix_table(
            summary.get("by_level_expiry", {}),
            row_label="Level",
            col_label="Expiry (s)",
            payout_pct=payout_pct,
            min_sample=min_sample,
        )
    )
    md.append("")

    # --- Asset × Expiry matrix ---
    md.append("## Asset × Expiry Win-Rate Matrix")
    md.append("")
    md.append(
        f"_Win-rate per (Asset, Expiry) cell. "
        f"⚠️ = fewer than {min_sample} settled trades._"
    )
    md.append("")
    md.extend(
        _matrix_table(
            summary.get("by_asset_expiry", {}),
            row_label="Asset",
            col_label="Expiry (s)",
            payout_pct=payout_pct,
            min_sample=min_sample,
        )
    )
    md.append("")

    # --- Regime × Expiry matrix ---
    md.append("## Regime × Expiry Win-Rate Matrix")
    md.append("")
    md.append(
        f"_Win-rate per (Regime, Expiry) cell. "
        f"⚠️ = fewer than {min_sample} settled trades._"
    )
    md.append("")
    md.extend(
        _matrix_table(
            summary.get("by_regime_expiry", {}),
            row_label="Regime",
            col_label="Expiry (s)",
            payout_pct=payout_pct,
            min_sample=min_sample,
        )
    )
    md.append("")

    # --- Confidence × Expiry matrix ---
    md.append("## Confidence × Expiry Win-Rate Matrix")
    md.append("")
    md.append(
        f"_Win-rate per (Confidence, Expiry) cell. "
        f"⚠️ = fewer than {min_sample} settled trades._"
    )
    md.append("")
    md.extend(
        _matrix_table(
            summary.get("by_confidence_expiry", {}),
            row_label="Confidence",
            col_label="Expiry (s)",
            payout_pct=payout_pct,
            min_sample=min_sample,
        )
    )
    md.append("")

    # --- Suppression audit ---
    md.append("## Suppression Audit")
    md.append("")
    md.extend(_suppression_audit(rows))
    md.append("")

    # --- Recommendations ---
    md.append("## Recommendations")
    md.append("")
    for line in _recommendations(summary, payout_pct, min_sample, exclusion_threshold):
        md.append(line)
    md.append("")

    return "\n".join(md)


def _write_markdown(content: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_csv(rows: Sequence[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    extra_fields = sorted({key for row in rows for key in row.keys()} - set(CSV_FIELDNAMES))
    fieldnames = [*CSV_FIELDNAMES, *extra_fields]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _report_prefix(dates: Sequence[str]) -> str:
    date_part = "_".join(dates)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"oteo_level_backtest_{date_part}_{timestamp}"


def _ghost_report_prefix(session_files: Sequence[Path]) -> str:
    if len(session_files) == 1:
        session_part = session_files[0].stem
    else:
        session_part = f"{len(session_files)}_sessions"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"oteo_ghost_reprice_{session_part}_{timestamp}"


def run_replay(
    *,
    dates: Sequence[str],
    assets: Sequence[str] | None,
    expiry_seconds: Sequence[int],
    tick_root: Path,
    report_root: Path,
    payout_pct: float,
    report_title: str = "OTEO Replay Backtest Analysis",
) -> dict[str, Path]:
    runner = BacktestRunner(BacktestConfig(expiry_seconds=[int(value) for value in expiry_seconds], payout_pct=payout_pct))
    rows: list[dict[str, Any]] = []

    for tick_file in _resolve_tick_files(tick_root, dates, assets):
        ticks = load_ticks_from_file(tick_file)
        if not ticks:
            continue
        asset = ticks[0].asset
        date = tick_file.stem
        rows.extend(runner.replay_asset_ticks(asset, ticks, date=date))

    summary = runner.summarize(rows)
    prefix = _report_prefix(dates)
    csv_path = report_root / f"{prefix}.csv"
    json_path = report_root / f"{prefix}_summary.json"
    md_path = report_root / f"{prefix}_analysis.md"
    _write_csv(rows, csv_path)
    _write_json({"summary": summary, "row_count": len(rows)}, json_path)
    _write_markdown(
        generate_markdown_report(rows, summary, title=report_title, payout_pct=payout_pct),
        md_path,
    )
    return {"csv": csv_path, "json": json_path, "md": md_path}


def run_ghost_reprice(
    *,
    sessions: Sequence[str] | None,
    expiry_seconds: Sequence[int],
    tick_root: Path,
    ghost_session_root: Path,
    report_root: Path,
    payout_pct: float,
    report_title: str = "OTEO Ghost Reprice Analysis",
) -> dict[str, Path]:
    session_files = _resolve_ghost_session_files(ghost_session_root, sessions)
    rows = reprice_ghost_trades(
        session_files,
        tick_root=tick_root,
        expiry_seconds=[int(value) for value in expiry_seconds],
        payout_pct=payout_pct,
    )
    runner = BacktestRunner(BacktestConfig(expiry_seconds=[int(value) for value in expiry_seconds], payout_pct=payout_pct))
    summary = runner.summarize(rows)
    prefix = _ghost_report_prefix([Path(path) for path in session_files])
    csv_path = report_root / f"{prefix}.csv"
    json_path = report_root / f"{prefix}_summary.json"
    md_path = report_root / f"{prefix}_analysis.md"
    _write_csv(rows, csv_path)
    _write_json({"summary": summary, "row_count": len(rows)}, json_path)
    _write_markdown(
        generate_markdown_report(rows, summary, title=report_title, payout_pct=payout_pct),
        md_path,
    )
    return {"csv": csv_path, "json": json_path, "md": md_path}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay OTC_SNIPER OTEO Level 1/2/3 signals over tick logs.")
    parser.add_argument("--mode", choices=["replay", "ghost-reprice"], default="replay")
    parser.add_argument("--dates", nargs="+", help="Date(s) in YYYY-MM-DD format. Required for replay mode.")
    parser.add_argument("--assets", nargs="*", help="Optional asset list. If omitted, all assets with matching tick files are used.")
    parser.add_argument("--sessions", nargs="*", help="Ghost session id(s) or JSONL path(s). If omitted, all sessions are repriced.")
    parser.add_argument("--expiry", nargs="+", type=int, default=DEFAULT_EXPIRY_SECONDS, help="Expiry seconds to test")
    parser.add_argument("--tick-root", type=Path, default=DEFAULT_TICK_ROOT)
    parser.add_argument("--ghost-session-root", type=Path, default=DEFAULT_GHOST_SESSION_ROOT)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--payout-pct", type=float, default=92.0)
    parser.add_argument("--report-title", type=str, default=None, help="Optional title for the Markdown analysis report.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.mode == "replay":
        if not args.dates:
            parser.error("--dates is required when --mode replay")
        title = args.report_title or "OTEO Replay Backtest Analysis"
        report_paths = run_replay(
            dates=args.dates,
            assets=args.assets,
            expiry_seconds=args.expiry,
            tick_root=args.tick_root,
            report_root=args.report_root,
            payout_pct=args.payout_pct,
            report_title=title,
        )
    else:
        title = args.report_title or "OTEO Ghost Reprice Analysis"
        report_paths = run_ghost_reprice(
            sessions=args.sessions,
            expiry_seconds=args.expiry,
            tick_root=args.tick_root,
            ghost_session_root=args.ghost_session_root,
            report_root=args.report_root,
            payout_pct=args.payout_pct,
            report_title=title,
        )
    print(f"CSV report:      {report_paths['csv']}")
    print(f"JSON summary:    {report_paths['json']}")
    print(f"Markdown report: {report_paths['md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())