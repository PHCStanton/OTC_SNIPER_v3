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
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.backend.services.market_context import MarketContextEngine, apply_level2_policy, apply_level3_policy
from app.backend.services.oteo import OTEO
from app.backend.services.regime_classifier import RegimeClassifier
from app.backend.services.manipulation import ManipulationDetector

DEFAULT_EXPIRY_SECONDS = [15, 30, 60, 90, 120, 180, 300]
DEFAULT_TICK_ROOT = Path("app/data/tick_logs")
DEFAULT_REPORT_ROOT = Path("app/backtesting/results")
MIN_SAMPLE_SIZE = 10

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
    "pocket_state",
    "vol_level",
    "liq_level",
    "manip_level",
    "utc_hour_offset",
    "utc_4hour_offset",
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
class PocketBacktestConfig:
    payout_pct: float = 92.0
    expiry_seconds: list[int] = field(default_factory=lambda: list(DEFAULT_EXPIRY_SECONDS))

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
    entry_time: float,
    entry_price: float,
    direction: str,
    expiry_seconds: int,
) -> dict[str, Any]:
    if not ticks:
        return {"outcome": "insufficient_data", "exit_time": None, "exit_price": None, "price_delta": None}
    target_time = entry_time + expiry_seconds
    timestamps = [tick.timestamp for tick in ticks]
    
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

class PocketTracker:
    def __init__(self) -> None:
        self.log_returns: deque[float] = deque(maxlen=1000)
        self.last_price: float | None = None
        self.tick_timestamps: deque[float] = deque(maxlen=60)
        self.manip_detector = ManipulationDetector()

    def update(self, timestamp: float, price: float) -> tuple[str, str, str, str]:
        # 1. Volatility calculation
        vol_level = "LOW"
        if self.last_price is not None and self.last_price > 0 and price > 0:
            log_ret = math.log(price / self.last_price)
            self.log_returns.append(log_ret)
            
            if len(self.log_returns) >= 100:
                fast_returns = list(self.log_returns)[-100:]
                std_fast = np.std(fast_returns)
                std_slow = np.std(self.log_returns)
                
                ratio = std_fast / max(std_slow, 1e-8)
                if ratio > 2.0:
                    vol_level = "HIGH"
                elif ratio > 1.2:
                    vol_level = "MEDIUM"
                else:
                    vol_level = "LOW"
        self.last_price = price

        # 2. Liquidity (tick frequency) calculation
        self.tick_timestamps.append(timestamp)
        liq_level = "LOW"
        freq = 0.0
        if len(self.tick_timestamps) >= 2:
            dt = self.tick_timestamps[-1] - self.tick_timestamps[0]
            if dt > 0:
                freq = ((len(self.tick_timestamps) - 1) / dt) * 60.0
                
            if freq >= 40.0:
                liq_level = "HIGH"
            elif freq >= 15.0:
                liq_level = "MEDIUM"
            else:
                liq_level = "LOW"

        # 3. Manipulation Level calculation
        manip_flags = self.manip_detector.update(timestamp, price)
        push_snap = manip_flags.get("push_snap", 0.0)
        pinning = manip_flags.get("pinning", 0.0)
        
        manip_level = "LOW"
        if push_snap >= 0.7 or pinning >= 0.7:
            manip_level = "HIGH"
        elif push_snap >= 0.3 or pinning >= 0.3:
            manip_level = "MEDIUM"
        else:
            manip_level = "LOW"
            
        pocket_state = f"Vol:{vol_level} | Liq:{liq_level} | Manip:{manip_level}"
        return vol_level, liq_level, manip_level, pocket_state

def calculate_time_offsets(timestamp: float) -> tuple[int, int]:
    """Calculate hour offset and 4-hour offset from Pocket Option day start (22:00 UTC)."""
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    
    # Minutes since midnight
    mins_today = dt.hour * 60 + dt.minute
    
    # 22:00 UTC in minutes is 22 * 60 = 1320
    # Offset relative to 22:00 UTC
    offset_mins = (mins_today - 1320) % (24 * 60)
    
    offset_hour = offset_mins // 60
    offset_4hour = offset_hour // 4
    
    return int(offset_hour), int(offset_4hour)

class PocketBacktestRunner:
    def __init__(self, config: PocketBacktestConfig) -> None:
        self.config = config
        self.oteo = OTEO()
        self.context = MarketContextEngine()
        self.regime = RegimeClassifier()
        self.pocket_tracker = PocketTracker()

    def run_file(self, path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        ticks = load_ticks_from_file(path)
        if not ticks:
            return [], []
        
        asset = ticks[0].asset
        date = path.stem
        
        rows: list[dict[str, Any]] = []
        pockets_log: list[dict[str, Any]] = []
        
        last_regime: dict[str, Any] | None = None
        current_pocket_state = ""
        current_pocket_start_time = 0.0
        current_pocket_regimes = defaultdict(int)
        
        for tick in ticks:
            # 1. Update pocket tracking
            vol_lvl, liq_lvl, manip_lvl, pocket_state = self.pocket_tracker.update(tick.timestamp, tick.price)
            
            # 2. Update engine states
            oteo_res = self.oteo.update_tick(tick.price, timestamp=tick.timestamp)
            context_res = self.context.update_tick(tick.price, timestamp=tick.timestamp)
            if bool(context_res.get("candle_closed")) and bool(context_res.get("ready")):
                last_regime = self.regime.classify(context_res)
                
            # Log pocket duration transitions
            if pocket_state != current_pocket_state:
                if current_pocket_state:
                    dur = tick.timestamp - current_pocket_start_time
                    dom_regime = max(current_pocket_regimes, key=current_pocket_regimes.get) if current_pocket_regimes else "UNKNOWN"
                    pockets_log.append({
                        "pocket_state": current_pocket_state,
                        "duration_seconds": dur,
                        "dominant_regime": dom_regime,
                        "start_time": current_pocket_start_time,
                        "end_time": tick.timestamp
                    })
                current_pocket_state = pocket_state
                current_pocket_start_time = tick.timestamp
                current_pocket_regimes.clear()
            
            if last_regime:
                current_pocket_regimes[last_regime.get("regime_label", "UNKNOWN")] += 1

            if isinstance(oteo_res, dict):
                level1 = dict(oteo_res)
                level2 = apply_level2_policy(level1, context_res, enabled=True)
                level3 = None
                if last_regime is not None:
                    level3 = apply_level3_policy(level2, context_res, last_regime)

                for level_name, level_signal in (("L1", level1), ("L2", level2), ("L3", level3)):
                    if level_signal is None or not bool(level_signal.get("actionable")):
                        continue
                    direction = str(level_signal.get("recommended") or "").upper()
                    if direction not in {"CALL", "PUT"}:
                        continue
                        
                    hour_offset, four_hour_offset = calculate_time_offsets(tick.timestamp)
                    
                    for static_exp in self.config.expiry_seconds:
                        expiry_res = evaluate_expiry(ticks, tick.timestamp, tick.price, direction, static_exp)
                        net_pl = _net_pl_for_outcome(expiry_res["outcome"], self.config.payout_pct)
                        
                        rows.append({
                            "date": date,
                            "asset": asset,
                            "level": level_name,
                            "entry_time": tick.timestamp,
                            "entry_price": tick.price,
                            "direction": direction,
                            "expiry_seconds": static_exp,
                            "exit_time": expiry_res["exit_time"],
                            "exit_price": expiry_res["exit_price"],
                            "price_delta": expiry_res["price_delta"],
                            "outcome": expiry_res["outcome"],
                            "net_pl": net_pl,
                            "payout_pct": self.config.payout_pct,
                            "pocket_state": pocket_state,
                            "vol_level": vol_lvl,
                            "liq_level": liq_lvl,
                            "manip_level": manip_lvl,
                            "utc_hour_offset": hour_offset,
                            "utc_4hour_offset": four_hour_offset,
                            "adx_regime": context_res.get("adx_regime"),
                            "trend_direction": context_res.get("trend_direction"),
                        })
                        
        # Log the final pocket state
        if current_pocket_state:
            dur = ticks[-1].timestamp - current_pocket_start_time
            dom_regime = max(current_pocket_regimes, key=current_pocket_regimes.get) if current_pocket_regimes else "UNKNOWN"
            pockets_log.append({
                "pocket_state": current_pocket_state,
                "duration_seconds": dur,
                "dominant_regime": dom_regime,
                "start_time": current_pocket_start_time,
                "end_time": ticks[-1].timestamp
            })
            
        return rows, pockets_log

def _matrix_table(summary: dict[str, dict[str, Any]], row_label: str, col_label: str) -> list[str]:
    lines = []
    expiries = sorted({int(key.split("|")[-1]) for key in summary.keys() if "|" in key})
    rows_keys = sorted({"|".join(key.split("|")[:-1]) for key in summary.keys() if "|" in key})
    
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
    trades: list[dict[str, Any]],
    pockets: list[dict[str, Any]],
    payout_pct: float,
    summary: dict[str, Any],
) -> str:
    md = []
    md.append("# Spike Pockets & Timeframe Backtest Report")
    md.append("")
    md.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ")
    md.append("")
    
    md.append("## 1. Overall Statistics Comparison")
    md.append("")
    
    b_wins = sum(1 for r in trades if r["outcome"] == "win")
    b_losses = sum(1 for r in trades if r["outcome"] == "loss")
    b_settled = b_wins + b_losses
    b_win_rate = (b_wins / b_settled * 100.0) if b_settled else 0.0
    b_pl = sum(r["net_pl"] for r in trades)
    
    md.append(f"* **Total Evaluated Signals:** {len(trades)}")
    md.append(f"* **Settled Trades:** {b_settled}")
    md.append(f"* **Wins:** {b_wins} | **Losses:** {b_losses}")
    md.append(f"* **Cumulative Win-Rate:** {b_win_rate:.2f}%")
    md.append(f"* **Cumulative P/L (units):** {b_pl:.4f}")
    md.append("")
    
    # Pockets duration summary
    md.append("## 2. Pocket Durations & Active Regimes")
    md.append("")
    md.append("| Pocket State | Count | Avg Duration (sec) | Dominant Regime |")
    md.append("| --- | --- | --- | --- |")
    
    pockets_grouped = defaultdict(list)
    for p in pockets:
        pockets_grouped[p["pocket_state"]].append(p)
        
    for state in sorted(pockets_grouped.keys()):
        group = pockets_grouped[state]
        avg_dur = np.mean([p["duration_seconds"] for p in group])
        
        regimes_in_state = defaultdict(int)
        for p in group:
            regimes_in_state[p["dominant_regime"]] += 1
        dom_regime = max(regimes_in_state, key=regimes_in_state.get) if regimes_in_state else "UNKNOWN"
        
        md.append(f"| {state} | {len(group)} | {avg_dur:.1f}s | {dom_regime} |")
    md.append("")
    
    # Pocket Performance matrix
    md.append("## 3. Pocket Performance Matrix")
    md.append("")
    md.append("_Win-rate and trade counts of executed signals under specific spike pocket states._")
    md.append("")
    md.extend(_matrix_table(summary.get("by_pocket_expiry", {}), "Pocket State", "Expiry"))
    md.append("")
    
    # Time block distribution
    md.append("## 4. Pocket Option 22:00 UTC Start Timeframe Performance")
    md.append("")
    md.append("_Aggregated win-rate by 4-Hour block offsets from 22:00 UTC rollover start._")
    md.append("")
    md.append("| 4-Hour Block | UTC Actual Time | Settled Trades | Win-Rate | Net P/L |")
    md.append("| --- | --- | --- | --- | --- |")
    
    block_labels = {
        0: "22:00 - 02:00 UTC",
        1: "02:00 - 06:00 UTC",
        2: "06:00 - 10:00 UTC",
        3: "10:00 - 14:00 UTC",
        4: "14:00 - 18:00 UTC",
        5: "18:00 - 22:00 UTC",
    }
    
    for block_idx in range(6):
        block_trades = [t for t in trades if t["utc_4hour_offset"] == block_idx]
        b_w = sum(1 for t in block_trades if t["outcome"] == "win")
        b_l = sum(1 for t in block_trades if t["outcome"] == "loss")
        b_s = b_w + b_l
        b_wr = (b_w / b_s * 100.0) if b_s else 0.0
        b_net = sum(t["net_pl"] for t in block_trades)
        
        md.append(f"| Block {block_idx} | {block_labels.get(block_idx)} | {b_s} | {b_wr:.2f}% | {b_net:.2f} |")
    md.append("")
    
    # Top pocket recommendations
    md.append("## 5. Strategic Recommendations & Findings")
    md.append("")
    
    breakeven = 1 / (1 + payout_pct/100.0) * 100.0
    md.append(f"Breakeven win-rate at {payout_pct}% payout: **{breakeven:.2f}%**  ")
    md.append("")
    
    # Identify high-performance pockets with n >= MIN_SAMPLE_SIZE
    valid_pockets = []
    pocket_expiries = summary.get("by_pocket_expiry", {})
    for key, val in pocket_expiries.items():
        parts = key.split("|")
        state = "|".join(parts[:-1])
        exp = parts[-1]
        settled = val["wins"] + val["losses"]
        if settled >= MIN_SAMPLE_SIZE:
            valid_pockets.append((state, exp, val["win_rate"], settled))
            
    valid_pockets.sort(key=lambda x: x[2], reverse=True)
    
    md.append("### Recommended Spike Pockets to Target")
    recommend_count = 0
    for state, exp, wr, settled in valid_pockets:
        if wr > breakeven + 2.0:
            md.append(f"* **{state}** at **{exp}s** expiry: **{wr:.2f}%** win-rate (n={settled})")
            recommend_count += 1
            if recommend_count >= 5:
                break
    if recommend_count == 0:
        md.append("_No pockets met the target profitability threshold with a valid sample size._")
        
    md.append("")
    md.append("### Spike Pockets to Avoid")
    avoid_count = 0
    valid_pockets.sort(key=lambda x: x[2])
    for state, exp, wr, settled in valid_pockets:
        if wr < breakeven:
            md.append(f"* **{state}** at **{exp}s** expiry: **{wr:.2f}%** win-rate (n={settled})")
            avoid_count += 1
            if avoid_count >= 5:
                break
    if avoid_count == 0:
        md.append("_No pockets met the avoidance criteria._")
        
    return "\n".join(md)

def run_backtest(
    *,
    dates: Sequence[str],
    assets: Sequence[str] | None,
    config: PocketBacktestConfig,
    report_root: Path,
) -> dict[str, Path]:
    runner = PocketBacktestRunner(config)
    trades: list[dict[str, Any]] = []
    pockets: list[dict[str, Any]] = []
    
    tick_root = Path(DEFAULT_TICK_ROOT)
    for tick_file in _resolve_tick_files(tick_root, dates, assets):
        f_trades, f_pockets = runner.run_file(tick_file)
        trades.extend(f_trades)
        pockets.extend(f_pockets)
        
    # Group performance by pocket state and expiry
    grouped_pocket_expiry = {}
    for t in trades:
        key = f"{t['pocket_state']}|{t['expiry_seconds']}"
        grouped_pocket_expiry.setdefault(key, []).append(t)
        
    summary_by_pocket_expiry = {}
    for key, group in grouped_pocket_expiry.items():
        wins = sum(1 for r in group if r["outcome"] == "win")
        losses = sum(1 for r in group if r["outcome"] == "loss")
        draws = sum(1 for r in group if r["outcome"] == "draw")
        settled = wins + losses
        summary_by_pocket_expiry[key] = {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate": (wins / settled * 100.0) if settled else 0.0
        }
        
    summary = {
        "by_pocket_expiry": summary_by_pocket_expiry
    }
    
    date_part = "_".join(dates)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"oteo_pockets_backtest_{date_part}_{timestamp}"
    
    asset_name = "unknown_asset"
    if assets:
        asset_name = assets[0]
    elif trades:
        asset_name = trades[0]["asset"]
        
    target_report_dir = report_root / "pockets" / f"{asset_name}_pockets"
    target_report_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = target_report_dir / f"{prefix}.csv"
    json_path = target_report_dir / f"{prefix}_summary.json"
    md_path = target_report_dir / f"{prefix}_analysis.md"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(trades)
        
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "total_trades": len(trades)}, handle, indent=2)
        
    md_content = generate_markdown_report(trades, pockets, config.payout_pct, summary)
    md_path.write_text(md_content, encoding="utf-8")
    
    return {"csv": csv_path, "json": json_path, "md": md_path}

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate OTEO strategy against Volatility/Liquidity/Manipulation pockets.")
    parser.add_argument("--dates", nargs="+", required=True, help="Dates in YYYY-MM-DD format")
    parser.add_argument("--assets", nargs="*", help="Optional asset list filter")
    parser.add_argument("--payout-pct", type=float, default=92.0)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    
    args = parser.parse_args(argv)
    
    config = PocketBacktestConfig(
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
