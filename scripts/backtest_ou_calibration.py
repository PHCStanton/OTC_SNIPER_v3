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
    "direction",
    "ou_half_life",
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
class OUBacktestConfig:
    window_size: int = 300
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

def calculate_rolling_ou(prices: np.ndarray, timestamps: np.ndarray, window_size: int) -> float | None:
    r"""
    Fits the discrete-time AR(1) representation of the Ornstein-Uhlenbeck process:
    X_t - X_{t-1} = c + \beta * X_{t-1} + \epsilon_t
    And computes the reversion half-life \tau = ln(2) / \theta.
    """
    if len(prices) < window_size:
        return None
        
    w_prices = prices[-window_size:]
    w_ts = timestamps[-window_size:]
    
    y = np.diff(w_prices)
    x_lag = w_prices[:-1]
    n = len(y)
    
    if n < 50:
        return None
        
    dt = (w_ts[-1] - w_ts[0]) / n
    if dt <= 0:
        return None
        
    # OLS coefficients
    sum_x = np.sum(x_lag)
    sum_y = np.sum(y)
    sum_xx = np.sum(x_lag**2)
    sum_xy = np.sum(x_lag * y)
    
    denom = n * sum_xx - sum_x**2
    if abs(denom) < 1e-12:
        return None
        
    beta = (n * sum_xy - sum_x * sum_y) / denom
    
    # Verify mean-reverting behavior
    if beta >= 0 or (1.0 + beta) <= 0:
        return None
        
    theta = -math.log(1.0 + beta) / dt
    if theta <= 0:
        return None
        
    tau = math.log(2) / theta
    return float(tau)

class OUBacktestRunner:
    def __init__(self, config: OUBacktestConfig) -> None:
        self.config = config
        self.oteo = OTEO()
        self.market_context_engine = MarketContextEngine()
        self.regime_classifier = RegimeClassifier()
        
        # Deques for rolling tick-level price buffers
        self._price_buffer: deque[float] = deque(maxlen=2000)
        self._ts_buffer: deque[float] = deque(maxlen=2000)

    def run_file(self, path: Path) -> list[dict[str, Any]]:
        ticks = load_ticks_from_file(path)
        if not ticks:
            return []
        
        asset = ticks[0].asset
        date = path.stem
        
        rows: list[dict[str, Any]] = []
        last_regime: dict[str, Any] | None = None
        
        for tick in ticks:
            # Append tick to rolling buffers
            self._price_buffer.append(tick.price)
            self._ts_buffer.append(tick.timestamp)
            
            # Update base components
            oteo_result = self.oteo.update_tick(tick.price, timestamp=tick.timestamp)
            market_context = self.market_context_engine.update_tick(tick.price, timestamp=tick.timestamp)
            
            # Candle closed tracking
            if bool(market_context.get("candle_closed")) and bool(market_context.get("ready")):
                last_regime = self.regime_classifier.classify(market_context)

            if isinstance(oteo_result, dict):
                level1 = dict(oteo_result)
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
                    
                    # 1. Baseline - static expiries
                    for static_exp in self.config.expiry_seconds:
                        static_res = evaluate_expiry(ticks, tick.timestamp, tick.price, direction, static_exp)
                        rows.append(self._build_row(
                            date=date, asset=asset, level=level_name, tick=tick, direction=direction,
                            signal=level_signal, market_context=market_context, static_exp=static_exp,
                            expiry_res=static_res, vetoed=False, veto_reason=None, is_baseline=True,
                            ou_half_life=None
                        ))
                    
                    # 2. Dynamic OU-based expiry
                    prices_arr = np.array(self._price_buffer)
                    ts_arr = np.array(self._ts_buffer)
                    
                    tau = calculate_rolling_ou(prices_arr, ts_arr, self.config.window_size)
                    
                    if tau is None:
                        vetoed = True
                        veto_reason = "non_reverting"
                        chosen_exp = self.config.expiry_seconds[2]  # Fallback default (e.g. 60s)
                    else:
                        vetoed = False
                        veto_reason = None
                        # Round to nearest valid contract expiry
                        chosen_exp = min(self.config.expiry_seconds, key=lambda x: abs(x - tau))
                        
                    expiry_res = evaluate_expiry(ticks, tick.timestamp, tick.price, direction, int(chosen_exp))
                    rows.append(self._build_row(
                        date=date, asset=asset, level=level_name, tick=tick, direction=direction,
                        signal=level_signal, market_context=market_context, static_exp=int(chosen_exp),
                        expiry_res=expiry_res, vetoed=vetoed, veto_reason=veto_reason, is_baseline=False,
                        ou_half_life=tau
                    ))
                    
        return rows

    def _build_row(
        self, *, date: str, asset: str, level: str, tick: Tick, direction: str,
        signal: dict[str, Any], market_context: dict[str, Any], static_exp: int,
        expiry_res: dict[str, Any], vetoed: bool, veto_reason: str | None, is_baseline: bool,
        ou_half_life: float | None
    ) -> dict[str, Any]:
        net_pl = 0.0
        if not vetoed:
            net_pl = _net_pl_for_outcome(expiry_res["outcome"], self.config.payout_pct)
            
        return {
            "date": date,
            "asset": asset,
            "level": f"{level}_BASELINE" if is_baseline else f"{level}_OU",
            "entry_time": tick.timestamp,
            "entry_price": tick.price,
            "direction": direction,
            "ou_half_life": round(ou_half_life, 2) if ou_half_life is not None else None,
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
    window_size: int,
) -> str:
    md = []
    md.append("# Ornstein-Uhlenbeck (OU) Half-Life Calibration Report")
    md.append("")
    md.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ")
    md.append(f"**Rolling Calibration Window:** {window_size} ticks  ")
    md.append("")
    
    baseline_rows = [r for r in rows if "_BASELINE" in r["level"]]
    ou_rows = [r for r in rows if "_OU" in r["level"]]
    
    md.append("## Overall Statistics Comparison")
    md.append("")
    md.append("| Metric | Baseline (Static) | OU Filtered & Calibrated |")
    md.append("| --- | --- | --- |")
    
    b_wins = sum(1 for r in baseline_rows if r["outcome"] == "win")
    b_losses = sum(1 for r in baseline_rows if r["outcome"] == "loss")
    b_settled = b_wins + b_losses
    b_win_rate = (b_wins / b_settled * 100.0) if b_settled else 0.0
    b_pl = sum(r["net_pl"] for r in baseline_rows)
    
    ou_executed = [r for r in ou_rows if not r["vetoed"]]
    ou_wins = sum(1 for r in ou_executed if r["outcome"] == "win")
    ou_losses = sum(1 for r in ou_executed if r["outcome"] == "loss")
    ou_settled = ou_wins + ou_losses
    ou_win_rate = (ou_wins / ou_settled * 100.0) if ou_settled else 0.0
    ou_pl = sum(r["net_pl"] for r in ou_executed)
    
    md.append(f"| Total Signals Evaluated | {len(baseline_rows)} | {len(ou_rows)} |")
    md.append(f"| Suppressed (Non-reverting) | 0 | {len(ou_rows) - len(ou_executed)} |")
    md.append(f"| Executed Trades | {len(baseline_rows)} | {len(ou_executed)} |")
    md.append(f"| Wins | {b_wins} | {ou_wins} |")
    md.append(f"| Losses | {b_losses} | {ou_losses} |")
    md.append(f"| Win-Rate | {b_win_rate:.2f}% | {ou_win_rate:.2f}% |")
    md.append(f"| Net P/L (units) | {b_pl:.4f} | {ou_pl:.4f} |")
    
    md.append("")
    md.append("## Expiry Duration Performance matrix (OU Calibrated Active)")
    md.append("")
    md.append("_Win-rate per level × expiry cell for executed OU calibrated trades. ⚠️ = fewer than 30 trades._")
    md.append("")
    
    md.extend(_matrix_table(summary.get("by_level_expiry", {}), "Level", "Expiry"))
    md.append("")
    
    breakeven = 1 / (1 + payout_pct/100.0) * 100.0
    md.append("## Recommendations & Calibration Analysis")
    md.append("")
    md.append(f"Breakeven win-rate at {payout_pct}% payout: **{breakeven:.2f}%**  ")
    if ou_win_rate > b_win_rate:
        md.append(f"✅ **OU half-life calibration improved the win-rate** from {b_win_rate:.2f}% to {ou_win_rate:.2f}%.")
    else:
        md.append(f"❌ **OU calibration did not improve the overall win-rate** (Baseline: {b_win_rate:.2f}%, OU: {ou_win_rate:.2f}%).")
        
    return "\n".join(md)

def run_backtest(
    *,
    dates: Sequence[str],
    assets: Sequence[str] | None,
    config: OUBacktestConfig,
    report_root: Path,
) -> dict[str, Path]:
    runner = OUBacktestRunner(config)
    rows: list[dict[str, Any]] = []
    
    tick_root = Path(DEFAULT_TICK_ROOT)
    for tick_file in _resolve_tick_files(tick_root, dates, assets):
        rows.extend(runner.run_file(tick_file))
        
    executed_rows = [r for r in rows if not r["vetoed"]]
    
    grouped_level_expiry = {}
    for r in executed_rows:
        level_clean = r["level"].replace("_OU", "").replace("_BASELINE", "")
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
    prefix = f"oteo_ou_backtest_{date_part}_{timestamp}"
    
    asset_name = "unknown_asset"
    if assets:
        asset_name = assets[0]
    elif rows:
        asset_name = rows[0]["asset"]
        
    target_report_dir = report_root / "ou_calibration" / f"{asset_name}_ou_calibration"
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
        
    md_content = generate_markdown_report(rows, summary, config.payout_pct, config.window_size)
    md_path.write_text(md_content, encoding="utf-8")
    
    return {"csv": csv_path, "json": json_path, "md": md_path}

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay OTC_SNIPER OU Half-Life Calibration over ticks.")
    parser.add_argument("--dates", nargs="+", required=True, help="Dates in YYYY-MM-DD format")
    parser.add_argument("--assets", nargs="*", help="Optional asset list filter")
    parser.add_argument("--window-size", type=int, default=300, help="Sliding window size in ticks")
    parser.add_argument("--payout-pct", type=float, default=92.0)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    
    args = parser.parse_args(argv)
    
    config = OUBacktestConfig(
        window_size=args.window_size,
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
