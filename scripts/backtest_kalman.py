from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import deque
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
    "smoothed_price",
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
class KalmanBacktestConfig:
    kalman_q: float = 1e-9
    kalman_r: float = 1e-7
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

class KalmanFilter:
    """
    1D Kalman Filter state estimator.
    Models the hidden fair price as a random walk, and tick observations as noisy signals.
    """
    def __init__(self, q: float, r: float) -> None:
        self.q = q  # Process noise covariance
        self.r = r  # Measurement noise covariance
        self.x = None  # Estimated state
        self.p = 1.0   # State estimation error covariance

    def update(self, z: float) -> float:
        if self.x is None:
            self.x = z
            return self.x
            
        # Predict
        x_pred = self.x
        p_pred = self.p + self.q
        
        # Update
        y = z - x_pred  # Innovation
        s = p_pred + self.r  # Innovation covariance
        k = p_pred / s  # Kalman Gain
        
        self.x = x_pred + k * y
        self.p = (1.0 - k) * p_pred
        return self.x

class KalmanBacktestRunner:
    def __init__(self, config: KalmanBacktestConfig) -> None:
        self.config = config
        
        # Base engines for baseline (raw prices)
        self.oteo_base = OTEO()
        self.context_base = MarketContextEngine()
        self.regime_base = RegimeClassifier()
        
        # Base engines for Kalman smoothed prices
        self.oteo_kf = OTEO()
        self.context_kf = MarketContextEngine()
        self.regime_kf = RegimeClassifier()
        
        self.kf = KalmanFilter(config.kalman_q, config.kalman_r)

    def run_file(self, path: Path) -> list[dict[str, Any]]:
        ticks = load_ticks_from_file(path)
        if not ticks:
            return []
        
        asset = ticks[0].asset
        date = path.stem
        
        rows: list[dict[str, Any]] = []
        last_regime_base: dict[str, Any] | None = None
        last_regime_kf: dict[str, Any] | None = None
        
        for tick in ticks:
            # 1. Update baseline (raw prices)
            oteo_res_base = self.oteo_base.update_tick(tick.price, timestamp=tick.timestamp)
            context_res_base = self.context_base.update_tick(tick.price, timestamp=tick.timestamp)
            if bool(context_res_base.get("candle_closed")) and bool(context_res_base.get("ready")):
                last_regime_base = self.regime_base.classify(context_res_base)
                
            if isinstance(oteo_res_base, dict):
                level1 = dict(oteo_res_base)
                level2 = apply_level2_policy(level1, context_res_base, enabled=True)
                level3 = None
                if last_regime_base is not None:
                    level3 = apply_level3_policy(level2, context_res_base, last_regime_base)

                for level_name, level_signal in (("L1", level1), ("L2", level2), ("L3", level3)):
                    if level_signal is None or not bool(level_signal.get("actionable")):
                        continue
                    direction = str(level_signal.get("recommended") or "").upper()
                    if direction not in {"CALL", "PUT"}:
                        continue
                    for static_exp in self.config.expiry_seconds:
                        expiry_res = evaluate_expiry(ticks, tick.timestamp, tick.price, direction, static_exp)
                        rows.append(self._build_row(
                            date=date, asset=asset, level=f"{level_name}_BASELINE", tick=tick,
                            smoothed_price=None, direction=direction, static_exp=static_exp,
                            expiry_res=expiry_res, signal=level_signal, market_context=context_res_base
                        ))

            # 2. Update Kalman Smoothed Prices
            smoothed_price = self.kf.update(tick.price)
            oteo_res_kf = self.oteo_kf.update_tick(smoothed_price, timestamp=tick.timestamp)
            context_res_kf = self.context_kf.update_tick(smoothed_price, timestamp=tick.timestamp)
            if bool(context_res_kf.get("candle_closed")) and bool(context_res_kf.get("ready")):
                last_regime_kf = self.regime_kf.classify(context_res_kf)
                
            if isinstance(oteo_res_kf, dict):
                level1_kf = dict(oteo_res_kf)
                level2_kf = apply_level2_policy(level1_kf, context_res_kf, enabled=True)
                level3_kf = None
                if last_regime_kf is not None:
                    level3_kf = apply_level3_policy(level2_kf, context_res_kf, last_regime_kf)

                for level_name, level_signal in (("L1", level1_kf), ("L2", level2_kf), ("L3", level3_kf)):
                    if level_signal is None or not bool(level_signal.get("actionable")):
                        continue
                    direction = str(level_signal.get("recommended") or "").upper()
                    if direction not in {"CALL", "PUT"}:
                        continue
                    for static_exp in self.config.expiry_seconds:
                        # Entry executes at raw price
                        expiry_res = evaluate_expiry(ticks, tick.timestamp, tick.price, direction, static_exp)
                        rows.append(self._build_row(
                            date=date, asset=asset, level=f"{level_name}_KALMAN", tick=tick,
                            smoothed_price=smoothed_price, direction=direction, static_exp=static_exp,
                            expiry_res=expiry_res, signal=level_signal, market_context=context_res_kf
                        ))

        return rows

    def _build_row(
        self, *, date: str, asset: str, level: str, tick: Tick, smoothed_price: float | None,
        direction: str, static_exp: int, expiry_res: dict[str, Any], signal: dict[str, Any],
        market_context: dict[str, Any]
    ) -> dict[str, Any]:
        net_pl = _net_pl_for_outcome(expiry_res["outcome"], self.config.payout_pct)
        return {
            "date": date,
            "asset": asset,
            "level": level,
            "entry_time": tick.timestamp,
            "entry_price": tick.price,
            "smoothed_price": round(smoothed_price, 6) if smoothed_price is not None else None,
            "direction": direction,
            "expiry_seconds": static_exp,
            "exit_time": expiry_res["exit_time"],
            "exit_price": expiry_res["exit_price"],
            "price_delta": expiry_res["price_delta"],
            "outcome": expiry_res["outcome"],
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
    kalman_q: float,
    kalman_r: float,
) -> str:
    md = []
    md.append("# Kalman Filter Pre-Filtering Backtest Report")
    md.append("")
    md.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ")
    md.append(f"**Kalman configuration:** Q={kalman_q:.1e}, R={kalman_r:.1e}  ")
    md.append("")
    
    baseline_rows = [r for r in rows if "_BASELINE" in r["level"]]
    kalman_rows = [r for r in rows if "_KALMAN" in r["level"]]
    
    md.append("## Overall Statistics Comparison")
    md.append("")
    md.append("| Metric | Baseline (Raw Ticks) | Kalman Filtered Ticks |")
    md.append("| --- | --- | --- |")
    
    b_wins = sum(1 for r in baseline_rows if r["outcome"] == "win")
    b_losses = sum(1 for r in baseline_rows if r["outcome"] == "loss")
    b_settled = b_wins + b_losses
    b_win_rate = (b_wins / b_settled * 100.0) if b_settled else 0.0
    b_pl = sum(r["net_pl"] for r in baseline_rows)
    
    k_wins = sum(1 for r in kalman_rows if r["outcome"] == "win")
    k_losses = sum(1 for r in kalman_rows if r["outcome"] == "loss")
    k_settled = k_wins + k_losses
    k_win_rate = (k_wins / k_settled * 100.0) if k_settled else 0.0
    k_pl = sum(r["net_pl"] for r in kalman_rows)
    
    md.append(f"| Total Trades Evaluated | {len(baseline_rows)} | {len(kalman_rows)} |")
    md.append(f"| Wins | {b_wins} | {k_wins} |")
    md.append(f"| Losses | {b_losses} | {k_losses} |")
    md.append(f"| Win-Rate | {b_win_rate:.2f}% | {k_win_rate:.2f}% |")
    md.append(f"| Net P/L (units) | {b_pl:.4f} | {k_pl:.4f} |")
    
    md.append("")
    md.append("## Expiry Duration Performance matrix (Kalman Active)")
    md.append("")
    md.append("_Win-rate per level × expiry cell for executed Kalman-smoothed trades. ⚠️ = fewer than 30 trades._")
    md.append("")
    
    md.extend(_matrix_table(summary.get("by_level_expiry", {}), "Level", "Expiry"))
    md.append("")
    
    breakeven = 1 / (1 + payout_pct/100.0) * 100.0
    md.append("## Recommendations & Calibration Analysis")
    md.append("")
    md.append(f"Breakeven win-rate at {payout_pct}% payout: **{breakeven:.2f}%**  ")
    if k_win_rate > b_win_rate:
        md.append(f"✅ **Kalman pre-filtering improved the win-rate** from {b_win_rate:.2f}% to {k_win_rate:.2f}%.")
    else:
        md.append(f"❌ **Kalman pre-filtering did not improve the overall win-rate** (Baseline: {b_win_rate:.2f}%, Kalman: {k_win_rate:.2f}%).")
        
    return "\n".join(md)

def run_backtest(
    *,
    dates: Sequence[str],
    assets: Sequence[str] | None,
    config: KalmanBacktestConfig,
    report_root: Path,
) -> dict[str, Path]:
    runner = KalmanBacktestRunner(config)
    rows: list[dict[str, Any]] = []
    
    tick_root = Path(DEFAULT_TICK_ROOT)
    for tick_file in _resolve_tick_files(tick_root, dates, assets):
        rows.extend(runner.run_file(tick_file))
        
    kalman_rows = [r for r in rows if "_KALMAN" in r["level"]]
    
    grouped_level_expiry = {}
    for r in kalman_rows:
        level_clean = r["level"].replace("_KALMAN", "").replace("_BASELINE", "")
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
    prefix = f"oteo_kalman_backtest_{date_part}_{timestamp}"
    
    asset_name = "unknown_asset"
    if assets:
        asset_name = assets[0]
    elif rows:
        asset_name = rows[0]["asset"]
        
    target_report_dir = report_root / "kalman" / f"{asset_name}_kalman"
    target_report_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = target_report_dir / f"{prefix}.csv"
    json_path = target_report_dir / f"{prefix}_summary.json"
    md_path = target_report_dir / f"{prefix}_analysis.md"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
        
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "total_rows": len(rows)}, handle, indent=2)
        
    md_content = generate_markdown_report(rows, summary, config.payout_pct, config.kalman_q, config.kalman_r)
    md_path.write_text(md_content, encoding="utf-8")
    
    return {"csv": csv_path, "json": json_path, "md": md_path}

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay OTEO with Kalman Filter Pre-Filtering.")
    parser.add_argument("--dates", nargs="+", required=True, help="Dates in YYYY-MM-DD format")
    parser.add_argument("--assets", nargs="*", help="Optional asset list filter")
    parser.add_argument("--kalman-q", type=float, default=1e-9, help="Process noise covariance")
    parser.add_argument("--kalman-r", type=float, default=1e-7, help="Measurement noise covariance")
    parser.add_argument("--payout-pct", type=float, default=92.0)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    
    args = parser.parse_args(argv)
    
    config = KalmanBacktestConfig(
        kalman_q=args.kalman_q,
        kalman_r=args.kalman_r,
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
