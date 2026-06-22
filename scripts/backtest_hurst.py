from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.backend.services.market_context import MarketContextEngine, apply_level2_policy, apply_level3_policy
from app.backend.services.oteo import OTEO
from app.backend.services.regime_classifier import RegimeClassifier
from app.backend.services.extensions.hurst_adaptive_expiry import HurstAdaptiveExpiry
from app.backend.services.extensions.hurst_ai_noise import HurstAiNoise

DEFAULT_EXPIRY_SECONDS = [15, 30, 60, 90, 120, 180, 300]
DEFAULT_TICK_ROOT = Path("app/data/tick_logs")
DEFAULT_REPORT_ROOT = Path("app/backtesting/results")
MIN_SAMPLE_SIZE = 30
EXCLUSION_WIN_RATE_THRESHOLD = 45.0

CSV_FIELDNAMES = [
    "date",
    "asset",
    "level",
    "entry_time",
    "entry_price",
    "direction",
    "hurst_value",
    "hurst_regime",
    "vetoed",
    "veto_reason",
    "expiry_seconds",
    "exit_time",
    "exit_price",
    "price_delta",
    "outcome",
    "net_pl",
    "payout_pct",
    "oteo_score",
    "confidence",
    "market_ready",
    "adx_regime",
    "trend_direction",
]

class TickSchemaError(ValueError):
    """Raised when a tick JSONL row does not match the required backtest schema."""

@dataclass(frozen=True)
class Tick:
    timestamp: float
    price: float
    asset: str

@dataclass
class HurstBacktestConfig:
    mean_revert_limit: float = 0.44
    trend_limit: float = 0.58
    min_adaptive_expiry: int = 60
    min_scale_cutoff: int = 12
    ai_confidence_threshold: float = 80.0
    payout_pct: float = 92.0
    expiry_seconds: list[int] = field(default_factory=lambda: list(DEFAULT_EXPIRY_SECONDS))

    # Helper attributes to simulate getattr(config, ...) in extensions
    @property
    def hurst_min_scale_cutoff(self) -> int:
        return self.min_scale_cutoff

    @property
    def hurst_ai_confidence_threshold(self) -> float:
        return self.ai_confidence_threshold

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

def load_ticks_from_file(path: Path) -> list[Tick]:
    if not path.exists():
        raise FileNotFoundError(f"Tick file not found: {path}")
    ticks: list[Tick] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TickSchemaError(f"{path}:{line_number} invalid JSON: {exc.msg}") from exc
            ticks.append(_validate_tick_row(row, path=path, line_number=line_number))
    return sorted(ticks, key=lambda tick: tick.timestamp)

def _resolve_tick_files(tick_root: Path, dates: Sequence[str], assets: Sequence[str] | None) -> list[Path]:
    if not tick_root.exists():
        raise FileNotFoundError(f"Tick root not found: {tick_root}")
    files: list[Path] = []
    target_assets = assets if assets else [d.name for d in tick_root.iterdir() if d.is_dir()]
    for asset in target_assets:
        asset_dir = tick_root / asset
        if not asset_dir.exists():
            continue
        for date in dates:
            file_path = asset_dir / f"{date}.jsonl"
            if file_path.exists():
                files.append(file_path)
    return files

def evaluate_expiry(
    ticks: list[Tick],
    timestamps: list[float],
    entry_time: float,
    entry_price: float,
    direction: str,
    expiry_seconds: int,
) -> dict[str, Any]:
    if not ticks:
        return {"outcome": "insufficient_data", "exit_time": None, "exit_price": None, "price_delta": None}
    target_time = entry_time + expiry_seconds
    
    from bisect import bisect_left
    exit_index = bisect_left(timestamps, target_time)
    if exit_index >= len(ticks):
        return {"outcome": "missing_exit", "exit_time": None, "exit_price": None, "price_delta": None}
        
    exit_tick = ticks[exit_index]
    exit_time = exit_tick.timestamp
    exit_price = exit_tick.price
    price_delta = exit_price - entry_price
    
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

def _net_pl_for_outcome(outcome: str, payout_pct: float) -> float:
    if outcome == "win":
        return round(payout_pct / 100.0, 6)
    if outcome == "loss":
        return -1.0
    return 0.0

class HurstBacktestRunner:
    def __init__(self, config: HurstBacktestConfig) -> None:
        self.config = config
        
        # Instantiate base engine stacks
        self.oteo = OTEO()
        self.market_context_engine = MarketContextEngine()
        self.regime_classifier = RegimeClassifier()
        
        # Instantiate extensions
        self.hurst_l2 = HurstAdaptiveExpiry({
            "enabled": True,
            "mean_revert_limit": config.mean_revert_limit,
            "trend_limit": config.trend_limit,
            "min_adaptive_expiry": config.min_adaptive_expiry
        })
        self.hurst_l3 = HurstAiNoise({
            "enabled": True,
            "hurst_min_scale_cutoff": config.min_scale_cutoff,
            "hurst_ai_confidence_threshold": config.ai_confidence_threshold
        })

    def run_file(self, path: Path) -> list[dict[str, Any]]:
        ticks = load_ticks_from_file(path)
        if not ticks:
            return []
        
        asset = ticks[0].asset
        date = path.stem
        
        rows: list[dict[str, Any]] = []
        last_regime: dict[str, Any] | None = None
        timestamps = [t.timestamp for t in ticks]
        
        for tick in ticks:
            # Update base components
            oteo_result = self.oteo.update_tick(tick.price, timestamp=tick.timestamp)
            market_context = self.market_context_engine.update_tick(tick.price, timestamp=tick.timestamp)
            
            # Identify candle closed and regime
            if bool(market_context.get("candle_closed")) and bool(market_context.get("ready")):
                closed_candle = None  # Extensions only read internal prices buffer
                self.hurst_l2.on_candle_closed(asset, closed_candle, market_context)
                self.hurst_l3.on_candle_closed(asset, closed_candle, market_context)
                last_regime = self.regime_classifier.classify(market_context)

            # Process tick triggers inside extensions to capture buffers & override values
            if isinstance(oteo_result, dict):
                # Copy oteo_result to prevent mutations leaking back into cache
                signal_data = dict(oteo_result)
                signal_data = self.hurst_l2.on_tick_processed(asset, tick.price, tick.timestamp, signal_data, market_context)
                signal_data = self.hurst_l3.on_tick_processed(asset, tick.price, tick.timestamp, signal_data, market_context)

                # Process Level 1, 2, and 3 policies
                level1 = dict(signal_data)
                level2 = apply_level2_policy(level1, market_context, enabled=True)
                level3 = None
                if last_regime is not None:
                    level3 = apply_level3_policy(level2, market_context, last_regime)

                for level_name, level_signal in (("L1", level1), ("L2", level2), ("L3", level3)):
                    if level_signal is None or not bool(level_signal.get("actionable")):
                        continue
                    
                    direction = str(level_signal.get("recommended") or "").upper()
                    if direction not in {"CALL", "PUT"}:
                        continue
                    
                    # 1. Evaluate baseline (unfiltered static expiries)
                    # We output separate rows for the baseline to match oteo_levels backtest format
                    for static_exp in self.config.expiry_seconds:
                        static_res = evaluate_expiry(ticks, timestamps, tick.timestamp, tick.price, direction, static_exp)
                        rows.append(self._build_row(
                            date=date, asset=asset, level=level_name, tick=tick, direction=direction,
                            signal=level_signal, market_context=market_context, static_exp=static_exp,
                            expiry_res=static_res, vetoed=False, veto_reason=None, is_baseline=True
                        ))
                    
                    # 2. Evaluate Hurst-filtered signal
                    allowed_l2, reason_l2 = self.hurst_l2.on_consider_signal(asset, tick.price, level_signal, self.config)
                    allowed_l3, reason_l3 = self.hurst_l3.on_consider_signal(asset, tick.price, level_signal, self.config)
                    
                    vetoed = not (allowed_l2 and allowed_l3)
                    veto_reason = reason_l2 if not allowed_l2 else (reason_l3 if not allowed_l3 else None)
                    
                    # Expiry choice
                    chosen_exp = level_signal.get("override_expiration_seconds")
                    if chosen_exp is None:
                        chosen_exp = self.config.min_adaptive_expiry  # Default fallback
                    
                    expiry_res = evaluate_expiry(ticks, timestamps, tick.timestamp, tick.price, direction, int(chosen_exp))
                    rows.append(self._build_row(
                        date=date, asset=asset, level=level_name, tick=tick, direction=direction,
                        signal=level_signal, market_context=market_context, static_exp=int(chosen_exp),
                        expiry_res=expiry_res, vetoed=vetoed, veto_reason=veto_reason, is_baseline=False
                    ))
                    
        return rows

    def _build_row(
        self, *, date: str, asset: str, level: str, tick: Tick, direction: str,
        signal: dict[str, Any], market_context: dict[str, Any], static_exp: int,
        expiry_res: dict[str, Any], vetoed: bool, veto_reason: str | None, is_baseline: bool
    ) -> dict[str, Any]:
        net_pl = 0.0
        if not vetoed:
            net_pl = _net_pl_for_outcome(expiry_res["outcome"], self.config.payout_pct)
        
        # Determine current Hurst regime & value
        h_val = signal.get("hurst", 0.5)
        h_regime = signal.get("market_context", {}).get("hurst_regime", "random_walk")
        
        return {
            "date": date,
            "asset": asset,
            "level": f"{level}_BASELINE" if is_baseline else f"{level}_HURST",
            "entry_time": tick.timestamp,
            "entry_price": tick.price,
            "direction": direction,
            "hurst_value": h_val,
            "hurst_regime": h_regime,
            "vetoed": vetoed,
            "veto_reason": veto_reason,
            "expiry_seconds": static_exp,
            "exit_time": expiry_res["exit_time"],
            "exit_price": expiry_res["exit_price"],
            "price_delta": expiry_res["price_delta"],
            "outcome": "vetoed" if vetoed else expiry_res["outcome"],
            "net_pl": net_pl,
            "payout_pct": self.config.payout_pct,
            "oteo_score": signal.get("oteo_score"),
            "confidence": signal.get("confidence"),
            "market_ready": market_context.get("ready"),
            "adx_regime": market_context.get("adx_regime"),
            "trend_direction": market_context.get("trend_direction"),
        }

def _matrix_table(summary: dict[str, dict[str, Any]], row_label: str, col_label: str) -> list[str]:
    lines = []
    # Identify unique expiries
    expiries = sorted({int(key.split("|")[1]) for key in summary.keys() if "|" in key})
    rows_keys = sorted({key.split("|")[0] for key in summary.keys() if "|" in key})
    
    headers = [row_label, *[f"{exp}s" for exp in expiries]]
    lines.append(" | ".join(headers))
    lines.append(" | ".join(["---"] * len(headers)))
    
    for row_key in rows_keys:
        row_cells = [row_key]
        for exp in expiries:
            cell_key = f"{row_key}|{exp}"
            cell = summary.get(cell_key)
            if cell:
                wr = cell["win_rate"]
                settled = cell["wins"] + cell["losses"]
                warn = " ⚠️" if settled < MIN_SAMPLE_SIZE else ""
                row_cells.append(f"{wr:.1f}%{warn} n={settled}")
            else:
                row_cells.append("-")
        lines.append(" | ".join(row_cells))
    return lines

def generate_markdown_report(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    payout_pct: float,
) -> str:
    md = []
    md.append("# Hurst Exponent backtest & Calibration Analysis")
    md.append("")
    md.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ")
    
    # Split baseline vs Hurst rows
    baseline_rows = [r for r in rows if "_BASELINE" in r["level"]]
    hurst_rows = [r for r in rows if "_HURST" in r["level"]]
    
    md.append("## Overall Statistics Comparison")
    md.append("")
    md.append("| Metric | Baseline (Static) | Hurst Filtered |")
    md.append("| --- | --- | --- |")
    
    # Calculate baseline overall
    b_wins = sum(1 for r in baseline_rows if r["outcome"] == "win")
    b_losses = sum(1 for r in baseline_rows if r["outcome"] == "loss")
    b_settled = b_wins + b_losses
    b_win_rate = (b_wins / b_settled * 100.0) if b_settled else 0.0
    b_pl = sum(r["net_pl"] for r in baseline_rows)
    
    # Calculate Hurst overall (executed only)
    h_executed = [r for r in hurst_rows if not r["vetoed"]]
    h_wins = sum(1 for r in h_executed if r["outcome"] == "win")
    h_losses = sum(1 for r in h_executed if r["outcome"] == "loss")
    h_settled = h_wins + h_losses
    h_win_rate = (h_wins / h_settled * 100.0) if h_settled else 0.0
    h_pl = sum(r["net_pl"] for r in h_executed)
    
    md.append(f"| Total Trades Evaluated | {len(baseline_rows)} | {len(hurst_rows)} |")
    md.append(f"| Vetoed/Suppressed | 0 | {len(hurst_rows) - len(h_executed)} |")
    md.append(f"| Executed Trades | {len(baseline_rows)} | {len(h_executed)} |")
    md.append(f"| Wins | {b_wins} | {h_wins} |")
    md.append(f"| Losses | {b_losses} | {h_losses} |")
    md.append(f"| Win-Rate | {b_win_rate:.2f}% | {h_win_rate:.2f}% |")
    md.append(f"| Net P/L (units) | {b_pl:.4f} | {h_pl:.4f} |")
    
    md.append("")
    md.append("## Hurst Veto / Suppression Audit")
    md.append("")
    
    veto_counts = {}
    for r in hurst_rows:
        if r["vetoed"]:
            reason = r["veto_reason"] or "unknown"
            veto_counts[reason] = veto_counts.get(reason, 0) + 1
            
    md.append("| Suppression Gate | Count | Ratio |")
    md.append("| --- | --- | --- |")
    total_suppressed = len(hurst_rows) - len(h_executed)
    for reason, count in sorted(veto_counts.items(), key=lambda x: x[1], reverse=True):
        ratio = (count / len(hurst_rows) * 100.0) if len(hurst_rows) else 0.0
        md.append(f"| {reason} | {count} | {ratio:.1f}% |")
    if not veto_counts:
        md.append("| None | 0 | 0.0% |")
        
    md.append("")
    md.append("## Expiry Duration Performance matrix (Hurst Active)")
    md.append("")
    md.append("_Win-rate per level × expiry cell for executed Hurst trades. ⚠️ = fewer than 30 trades._")
    md.append("")
    
    md.extend(_matrix_table(summary.get("by_level_expiry", {}), "Level", "Expiry"))
    md.append("")
    
    # Day of the week and 4-hour block breakdown for executed Hurst trades
    md.append("## Timeframe & Day of the Week Performance (Hurst Active)")
    md.append("")
    md.append("_Performance of executed Hurst trades grouped by day of the week and 4-hour blocks._")
    md.append("")
    
    # 1. Group by Day of the Week
    md.append("### Performance by Day of the Week")
    md.append("")
    md.append("| Day of the Week | Executed Trades | Wins | Losses | Win-Rate | Net P/L |")
    md.append("| --- | --- | --- | --- | --- | --- |")
    
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    by_day = defaultdict(list)
    for r in h_executed:
        dt = datetime.fromtimestamp(r["entry_time"], tz=timezone.utc)
        day_name = dt.strftime("%A")
        by_day[day_name].append(r)
        
    for day in days_order:
        group = by_day.get(day, [])
        if not group:
            continue
        wins_day = sum(1 for r in group if r["outcome"] == "win")
        losses_day = sum(1 for r in group if r["outcome"] == "loss")
        settled_day = wins_day + losses_day
        wr_day = (wins_day / settled_day * 100.0) if settled_day else 0.0
        pl_day = sum(r["net_pl"] for r in group)
        md.append(f"| {day} | {settled_day} | {wins_day} | {losses_day} | {wr_day:.2f}% | {pl_day:.2f} |")
        
    md.append("")
    
    # 2. Group by 4-Hour Block (Rollover start at 22:00 UTC)
    md.append("### Performance by 4-Hour Rollover Blocks")
    md.append("")
    md.append("| 4-Hour Block | UTC Actual Time | Executed Trades | Wins | Losses | Win-Rate | Net P/L |")
    md.append("| --- | --- | --- | --- | --- | --- | --- |")
    
    block_labels = {
        0: "22:00 - 02:00 UTC",
        1: "02:00 - 06:00 UTC",
        2: "06:00 - 10:00 UTC",
        3: "10:00 - 14:00 UTC",
        4: "14:00 - 18:00 UTC",
        5: "18:00 - 22:00 UTC",
    }
    
    by_block = defaultdict(list)
    for r in h_executed:
        dt = datetime.fromtimestamp(r["entry_time"], tz=timezone.utc)
        mins_today = dt.hour * 60 + dt.minute
        offset_mins = (mins_today - 1320) % (24 * 60)
        block_idx = offset_mins // 240
        by_block[block_idx].append(r)
        
    for block_idx in range(6):
        group = by_block.get(block_idx, [])
        if not group:
            md.append(f"| Block {block_idx} | {block_labels.get(block_idx)} | 0 | 0 | 0 | 0.00% | 0.00 |")
            continue
        wins_b = sum(1 for r in group if r["outcome"] == "win")
        losses_b = sum(1 for r in group if r["outcome"] == "loss")
        settled_b = wins_b + losses_b
        wr_b = (wins_b / settled_b * 100.0) if settled_b else 0.0
        pl_b = sum(r["net_pl"] for r in group)
        md.append(f"| Block {block_idx} | {block_labels.get(block_idx)} | {settled_b} | {wins_b} | {losses_b} | {wr_b:.2f}% | {pl_b:.2f} |")
    md.append("")
    
    # Recommendations
    breakeven = 1 / (1 + payout_pct/100.0) * 100.0
    md.append("## Recommendations & Calibration Analysis")
    md.append("")
    md.append(f"Breakeven win-rate at {payout_pct}% payout: **{breakeven:.2f}%**  ")
    if h_win_rate > b_win_rate:
        md.append(f"✅ **Hurst filtering improved the win-rate** from {b_win_rate:.2f}% to {h_win_rate:.2f}%.")
    else:
        md.append(f"❌ **Hurst filtering did not improve the overall win-rate** (Baseline: {b_win_rate:.2f}%, Hurst: {h_win_rate:.2f}%).")
        
    return "\n".join(md)

def run_backtest(
    *,
    dates: Sequence[str],
    assets: Sequence[str] | None,
    config: HurstBacktestConfig,
    report_root: Path,
) -> dict[str, Path]:
    runner = HurstBacktestRunner(config)
    rows: list[dict[str, Any]] = []
    
    tick_root = Path(DEFAULT_TICK_ROOT)
    for tick_file in _resolve_tick_files(tick_root, dates, assets):
        rows.extend(runner.run_file(tick_file))
        
    # Group and summarize
    # To summarize correctly, we only include executed trades in the by_level_expiry groupings
    executed_rows = [r for r in rows if not r["vetoed"]]
    
    # Group calculations
    grouped_level_expiry = {}
    for r in executed_rows:
        # Strip "_HURST" or "_BASELINE" to keep group labels clean
        level_clean = r["level"].replace("_HURST", "").replace("_BASELINE", "")
        key = f"{level_clean}|{r['expiry_seconds']}"
        grouped_level_expiry.setdefault(key, []).append(r)
        
    summary_by_level_expiry = {}
    for key, group in grouped_level_expiry.items():
        wins = sum(1 for r in group if r["outcome"] == "win")
        losses = sum(1 for r in group if r["outcome"] == "loss")
        draws = sum(1 for r in group if r["outcome"] == "draw")
        settled = wins + losses
        summary_by_level_expiry[key] = {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate": (wins / settled * 100.0) if settled else 0.0
        }
        
    summary = {
        "by_level_expiry": summary_by_level_expiry
    }
    
    date_part = "_".join(dates)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"oteo_hurst_backtest_{date_part}_{timestamp}"
    
    asset_name = "unknown_asset"
    if assets:
        asset_name = assets[0]
    elif rows:
        asset_name = rows[0]["asset"]
        
    target_report_dir = report_root / "hurst" / f"{asset_name}_hurst"
    target_report_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = target_report_dir / f"{prefix}.csv"
    json_path = target_report_dir / f"{prefix}_summary.json"
    md_path = target_report_dir / f"{prefix}_analysis.md"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
        
    # Write JSON Summary
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "total_rows": len(rows)}, handle, indent=2)
        
    # Write MD Report
    md_content = generate_markdown_report(rows, summary, config.payout_pct)
    md_path.write_text(md_content, encoding="utf-8")
    
    return {"csv": csv_path, "json": json_path, "md": md_path}

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay OTC_SNIPER Hurst Premium & Elite veto gates over ticks.")
    parser.add_argument("--dates", nargs="+", required=True, help="Dates in YYYY-MM-DD format")
    parser.add_argument("--assets", nargs="*", help="Optional asset list filter")
    parser.add_argument("--mean-revert-limit", type=float, default=0.44)
    parser.add_argument("--trend-limit", type=float, default=0.58)
    parser.add_argument("--min-adaptive-expiry", type=int, default=60)
    parser.add_argument("--min-scale-cutoff", type=int, default=12)
    parser.add_argument("--ai-confidence-threshold", type=float, default=80.0)
    parser.add_argument("--payout-pct", type=float, default=92.0)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    
    args = parser.parse_args(argv)
    
    config = HurstBacktestConfig(
        mean_revert_limit=args.mean_revert_limit,
        trend_limit=args.trend_limit,
        min_adaptive_expiry=args.min_adaptive_expiry,
        min_scale_cutoff=args.min_scale_cutoff,
        ai_confidence_threshold=args.ai_confidence_threshold,
        payout_pct=args.payout_pct
    )
    
    report_paths = run_backtest(
        dates=args.dates,
        assets=args.assets,
        config=config,
        report_root=args.report_root
    )
    
    print(f"CSV report:      {report_paths['csv']}")
    print(f"JSON summary:    {report_paths['json']}")
    print(f"Markdown report: {report_paths['md']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
