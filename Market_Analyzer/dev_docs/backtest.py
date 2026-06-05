"""
backtest.py — QuFLX-Unify Backtesting Engine
=============================================
Runs all trading strategies against historical tick data (JSONL format)
with full market regime detection and performance attribution.

Market Regime Labels (via MarketRegimeAnalyzer):
  STRONG_TREND      — High ADX, clear directional move. Best for momentum.
  TREND_PULLBACK    — Macro trend intact, short counter-move. Reversal entries.
  RANGE_BOUND       — Price in S/R band. Mean-reversion at edges.
  CHOP_WHIPSAW      — Dangerous — signals heavily suppressed in analysis.
  INSUFFICIENT_DATA — Warmup candles, too few data points.

Usage:
  conda activate QuFLX-v2
  python backtest.py <path_to_jsonl_or_directory>

Examples:
  python backtest.py "c:\\v3\\OTC_SNIPER\\app\\data\\tick_logs\\AVAX_otc\\2026-04-01.jsonl"
  python backtest.py "c:\\v3\\OTC_SNIPER\\app\\data\\tick_logs"
"""

import os
import sys
import json
import time
import datetime
import csv
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd

# ── Strategy imports ──────────────────────────────────────────────────────────
BOT_DIR = r"c:\bots\mgx-po-trader1"
if BOT_DIR not in sys.path:
    sys.path.insert(0, BOT_DIR)

# Suppress browser-dependent modules not needed in backtest context
import types
sys.modules.setdefault("undetected_chromedriver", types.ModuleType("undetected_chromedriver"))

try:
    from bot.strategies.advanced import AdvancedStrategies
    from bot.strategies.alternative import AlternativeStrategies
    from bot.strategies.basic import BasicStrategies
    print("[OK] Strategy modules loaded.")
except ImportError as e:
    print(f"[ERROR] Error importing strategies: {e}")
    sys.exit(1)

# ── Regime analyzer import ────────────────────────────────────────────────────
ANALYZER_DIR = str(Path(__file__).parent)
if ANALYZER_DIR not in sys.path:
    sys.path.insert(0, ANALYZER_DIR)

try:
    from Market_Analyzer import MarketRegimeAnalyzer, MarketRegime
    print("[OK] MarketRegimeAnalyzer loaded.")
except ImportError as e:
    print(f"[ERROR] Error importing MarketRegimeAnalyzer: {e}")
    sys.exit(1)


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class Candle:
    timestamp: float
    open:      float
    high:      float
    low:       float
    close:     float
    volume:    float = 0.0
    # Tick-level quality (populated when raw ticks are available)
    tick_reversal_density: float = 0.0
    tick_zero_move_ratio:  float = 0.0
    tick_volatility:       float = 0.0


# ── Engine ────────────────────────────────────────────────────────────────────

class BacktestEngine:
    """
    Main backtesting engine.
    Converts JSONL tick files → 1-min candles → runs strategies → tags with regime.
    """

    def __init__(self):
        self.advanced    = AdvancedStrategies()
        self.alternative = AlternativeStrategies()
        self.basic       = BasicStrategies()

        # Regime analyzer with 20-candle primary and 30-candle secondary windows
        self.regime_analyzer = MarketRegimeAnalyzer(
            adx_period=14,
            primary_window=20,
            secondary_window=30,
            pullback_period=5,
            min_candles=35,   # < 35 candles → INSUFFICIENT_DATA
        )

        # Strategy map: name → callable
        self.strategy_map: Dict[str, Any] = {
            # ── Advanced ──────────────────────────────────────────────────
            "Aggressive Momentum Scalper":   self.advanced.aggressive_momentum_scalper,
            "Rapid RSI Extremes":            self.advanced.rapid_rsi_extremes,
            "Dual EMA Crossover":            self.advanced.dual_ema_crossover_aggressive,
            "Volume Price Breakout":         self.advanced.volume_price_breakout,
            "Triple Confirmation Scalper":   self.advanced.triple_confirmation_scalper,
            # ── Alternative ───────────────────────────────────────────────
            "RSI + Volume Strategy":         self.alternative.rsi_volume_strategy,
            "Smart Martingale":              self.alternative.smart_martingale,
            "Two Candle Breakout":           self.alternative.two_candle_breakout,
            "Triple Confluence":             self.alternative.triple_confluence,
            "Reversal Candle Trap":          self.alternative.reversal_candle_trap,
            # ── Basic ─────────────────────────────────────────────────────
            "Momentum Breakout":             self.basic.momentum_breakout,
            "1-Minute Reversal":             self.basic.one_minute_reversal,
            "Rapid MA Cross":                self.basic.rapid_ma_cross,
            "Impulse Spike":                 self.basic.impulse_spike,
        }

    # ── Data loading ──────────────────────────────────────────────────────────

    def load_ticks_to_candles(self, filepath: str) -> List[Candle]:
        """
        Convert a JSONL tick file to 1-minute candles.
        Also computes per-candle tick-level quality metrics from raw ticks.
        """
        ticks = []
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    # Validate required fields
                    if "t" in record and "p" in record:
                        ticks.append(record)
                except (json.JSONDecodeError, KeyError):
                    continue

        if not ticks:
            return []

        df = pd.DataFrame(ticks)
        # Deduplicate and sort
        df = df.drop_duplicates(subset=["t"]).sort_values("t")
        df["dt"] = pd.to_datetime(df["t"], unit="s")
        df.set_index("dt", inplace=True)

        # Resample to 1-min OHLC
        ohlc    = df["p"].resample("1min").ohlc()
        volumes = df["p"].resample("1min").count()
        ts      = ohlc.index.astype(np.int64) // 10 ** 9

        # Build candle list with tick-level quality enrichment
        candles = []
        for idx, row in ohlc.dropna().iterrows():
            minute_ts    = int(idx.timestamp())
            next_min_ts  = minute_ts + 60

            # Sub-candle tick quality (from raw ticks within this minute)
            minute_ticks = [
                t for t in ticks
                if minute_ts <= t.get("t", 0) < next_min_ts
            ]
            tick_rev_den  = 0.0
            tick_zero_rat = 0.0
            tick_vol      = 0.0
            if len(minute_ticks) >= 2:
                prices = np.array([t["p"] for t in minute_ticks], dtype=np.float64)
                moves  = np.diff(prices)
                signs  = np.sign(moves)
                nz     = signs[signs != 0]
                if len(nz) > 1:
                    tick_rev_den = float(np.sum(nz[1:] != nz[:-1]) / (len(nz) - 1))
                tick_zero_rat = float(np.sum(moves == 0.0) / len(moves))
                rets  = moves / prices[:-1]
                tick_vol = float(np.std(rets)) if len(rets) > 0 else 0.0

            candles.append(Candle(
                timestamp=minute_ts,
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=float(volumes.get(idx, 0)),
                tick_reversal_density=round(tick_rev_den,  4),
                tick_zero_move_ratio= round(tick_zero_rat, 4),
                tick_volatility=      round(tick_vol,      8),
            ))

        return candles

    # ── Backtest run ──────────────────────────────────────────────────────────

    def run_backtest(self, candles: List[Candle], asset_name: str) -> List[Dict]:
        """
        Run all strategies on the candle series with full regime tagging.
        Returns a list of trade result dicts, one per signal generated.
        """
        results = []
        n = len(candles)

        # Minimum candles: enough for indicator warmup + at least one trade window
        WARMUP = 50
        if n < WARMUP + 1:
            return []

        # ── Pre-compute regime series for the entire candle array ──────────
        print(f"    Computing regime series for {n} candles ...", end=" ", flush=True)  # noqa
        t0 = time.time()
        regime_series = self.regime_analyzer.precompute_regime_series(candles)
        print(f"done ({time.time() - t0:.2f}s)")

        # Cooldown tracking per strategy
        last_signal_time = {name: 0.0 for name in self.strategy_map}

        for i in range(WARMUP, n - 1):
            current_slice  = candles[: i + 1]
            entry_candle   = candles[i]
            outcome_candle = candles[i + 1]   # 1-minute expiry assumption

            # ── Temporal context ──────────────────────────────────────────
            dt      = datetime.datetime.fromtimestamp(entry_candle.timestamp)
            hour    = dt.hour
            weekday = dt.strftime("%A")

            # ── Regime context (pre-computed) ──────────────────────────────
            regime_result = regime_series.at(i)
            regime_label  = regime_result.label                          # e.g. "STRONG_TREND"
            regime_conf   = regime_result.confidence
            t_score       = regime_result.tradability_score
            trend_dir     = regime_result.trend_direction
            regime_flags  = "|".join(regime_result.flags) if regime_result.flags else ""

            # ── Legacy volatility context (body size) ─────────────────────
            bodies = [abs(c.close - c.open) for c in current_slice[-10:]]
            avg_body_pips = (np.mean(bodies) if bodies else 0) * 100_000

            # ── Consecutive same-colored candles ──────────────────────────
            consecutive_color = 0
            is_green = entry_candle.close >= entry_candle.open
            for c in reversed(current_slice[:-1]):
                if (c.close >= c.open) == is_green:
                    consecutive_color += 1
                else:
                    break

            # ── Strategy signal evaluation ────────────────────────────────
            for name, strategy_func in self.strategy_map.items():
                try:
                    signal = strategy_func(current_slice)
                except Exception:
                    continue

                if not signal:
                    continue

                # Outcome evaluation
                win = False
                mae_pips = 0.0
                if signal == "call":
                    win      = outcome_candle.close > entry_candle.close
                    mae_pips = (entry_candle.close - outcome_candle.low) * 100_000
                elif signal == "put":
                    win      = outcome_candle.close < entry_candle.close
                    mae_pips = (outcome_candle.high - entry_candle.close) * 100_000

                # Cooldown
                cooldown_sec = -1.0
                if last_signal_time[name] > 0:
                    cooldown_sec = entry_candle.timestamp - last_signal_time[name]

                results.append({
                    # Identification
                    "asset":            asset_name,
                    "strategy":         name,
                    "time":             dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "hour":             hour,
                    "weekday":          weekday,
                    # Regime (rich)
                    "regime":           regime_label,
                    "regime_confidence":round(regime_conf, 3),
                    "tradability_score":t_score,
                    "trend_direction":  trend_dir,
                    "regime_flags":     regime_flags,
                    # Market context
                    "volatility_pips":  round(avg_body_pips, 4),
                    "tick_density":     entry_candle.volume,
                    "tick_rev_density": entry_candle.tick_reversal_density,
                    "tick_zero_ratio":  entry_candle.tick_zero_move_ratio,
                    "consecutive":      consecutive_color,
                    "cooldown_min":     round(cooldown_sec / 60, 2) if cooldown_sec > 0 else -1,
                    # Trade outcome
                    "signal":           signal,
                    "entry":            entry_candle.close,
                    "exit":             outcome_candle.close,
                    "mae_pips":         round(max(0.0, mae_pips), 4),
                    "result":           "WIN" if win else "LOSS",
                })
                last_signal_time[name] = entry_candle.timestamp

        return results


# ── Analysis ──────────────────────────────────────────────────────────────────

_REGIME_ORDER = [
    MarketRegime.STRONG_TREND.value,
    MarketRegime.TREND_PULLBACK.value,
    MarketRegime.RANGE_BOUND.value,
    MarketRegime.CHOP_WHIPSAW.value,
    MarketRegime.INSUFFICIENT_DATA.value,
]


def analyze_results(all_results: List[Dict]) -> None:
    """
    Print comprehensive regime-aware performance analysis to stdout.
    """
    if not all_results:
        print("\n⚠ No trades generated.")
        return

    df = pd.DataFrame(all_results)
    df["is_win"] = df["result"] == "WIN"

    _section("Overall Performance by Strategy")
    summary = df.groupby("strategy").agg(
        trades=   ("is_win", "count"),
        wins=     ("is_win", "sum"),
        win_rate= ("is_win", "mean"),
    ).sort_values("win_rate", ascending=False)
    summary["win_rate"] = _pct(summary["win_rate"])
    print(summary.to_string())

    # ── Strategy × Regime Matrix ──────────────────────────────────────────
    _section("Strategy × Regime Performance Matrix")
    print("(Win rates — the core output for strategy-regime pairing decisions)\n")

    pivot = df.pivot_table(
        index="strategy",
        columns="regime",
        values="is_win",
        aggfunc="mean",
    )
    # Reorder columns where present
    cols_ordered = [c for c in _REGIME_ORDER if c in pivot.columns]
    cols_ordered += [c for c in pivot.columns if c not in cols_ordered]
    pivot = pivot[cols_ordered]
    pivot_pct = pivot.applymap(lambda x: f"{x * 100:.1f}%" if pd.notna(x) else "—")
    print(pivot_pct.to_string())

    # ── Trade count matrix (transparency) ─────────────────────────────────
    _section("Strategy × Regime Trade Count")
    count_pivot = df.pivot_table(
        index="strategy",
        columns="regime",
        values="is_win",
        aggfunc="count",
    )
    count_pivot = count_pivot.reindex(columns=cols_ordered, fill_value=0)
    print(count_pivot.to_string())

    # ── Regime Distribution by Asset ──────────────────────────────────────
    _section("Regime Distribution by Asset")
    regime_dist = df.groupby(["asset", "regime"]).size().unstack(fill_value=0)
    # Normalise to percentage
    regime_pct = regime_dist.div(regime_dist.sum(axis=1), axis=0) * 100
    regime_pct = regime_pct.round(1)
    regime_pct = regime_pct.reindex(
        columns=[c for c in _REGIME_ORDER if c in regime_pct.columns], fill_value=0.0
    )
    print(regime_pct.to_string(), "\n(% of trades per asset in each regime)")

    # ── Tradability-Filtered Win Rates ─────────────────────────────────────
    _section("Tradability-Filtered Win Rates (score ≥ 50 only)")
    tradable = df[df["tradability_score"] >= 50]
    if tradable.empty:
        print("  No trades with tradability_score ≥ 50 found.")
    else:
        t_summary = tradable.groupby("strategy").agg(
            trades=   ("is_win", "count"),
            win_rate= ("is_win", "mean"),
        ).sort_values("win_rate", ascending=False)
        t_summary["win_rate"] = _pct(t_summary["win_rate"])
        print(f"  Trades evaluated: {len(tradable)} / {len(df)} total")
        print(t_summary.to_string())

    # ── Performance by Asset ──────────────────────────────────────────────
    _section("Performance by Asset × Strategy (Top 3 per asset)")
    asset_summary = df.groupby(["asset", "strategy"]).agg(
        trades=   ("is_win", "count"),
        win_rate= ("is_win", "mean"),
    )
    asset_summary["win_rate"] = _pct(asset_summary["win_rate"])
    # Show top 3 strategies per asset by win rate
    top3 = (
        asset_summary
        .reset_index()
        .sort_values(["asset", "win_rate"], ascending=[True, False])
        .groupby("asset")
        .head(3)
        .set_index(["asset", "strategy"])
    )
    print(top3.to_string())

    # ── Best Performing Hours ──────────────────────────────────────────────
    _section("Best Performing Hours (Top 10)")
    hour_summary = df.groupby("hour").agg(
        trades=   ("is_win", "count"),
        win_rate= ("is_win", "mean"),
    ).sort_values("win_rate", ascending=False).head(10)
    hour_summary["win_rate"] = _pct(hour_summary["win_rate"])
    print(hour_summary.to_string())

    # ── Performance by Day of Week ─────────────────────────────────────────
    _section("Performance by Day of Week")
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                 "Saturday", "Sunday"]
    day_summary = df.groupby("weekday").agg(
        trades=   ("is_win", "count"),
        win_rate= ("is_win", "mean"),
    ).reindex([d for d in day_order if d in df["weekday"].unique()])
    day_summary["win_rate"] = _pct(day_summary["win_rate"])
    print(day_summary.to_string())

    # ── Trade Quality (Win vs Loss) ────────────────────────────────────────
    _section("Trade Quality Averages (Win vs Loss)")
    quality = df.groupby("result").agg(
        avg_tick_density=   ("tick_density",    "mean"),
        avg_volatility_pips=("volatility_pips", "mean"),
        avg_mae_pips=       ("mae_pips",        "mean"),
        avg_consecutive=    ("consecutive",     "mean"),
        avg_t_score=        ("tradability_score","mean"),
        avg_tick_rev_den=   ("tick_rev_density", "mean"),
    ).round(3)
    print(quality.to_string())

    # ── Regime Transition Analysis ─────────────────────────────────────────
    _section("Win Rate by Tradability Score Band")
    bins   = [0, 20, 40, 60, 80, 100]
    labels = ["0-20", "21-40", "41-60", "61-80", "81-100"]
    df["t_band"] = pd.cut(df["tradability_score"], bins=bins, labels=labels, right=True)
    band_summary = df.groupby("t_band", observed=True).agg(
        trades=   ("is_win", "count"),
        win_rate= ("is_win", "mean"),
    )
    band_summary["win_rate"] = _pct(band_summary["win_rate"])
    print(band_summary.to_string())


# ── Export ────────────────────────────────────────────────────────────────────

def export_results(all_results: List[Dict], output_dir: str = ".") -> None:
    """
    Export all regime-tagged trade results to CSV and JSON.
    """
    if not all_results:
        print("  No results to export.")
        return

    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ── CSV ───────────────────────────────────────────────────────────────
    csv_path = out / f"backtest_results_{ts}.csv"
    fieldnames = list(all_results[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    print(f"  [OK] CSV exported  -> {csv_path}")

    # ── JSON ─────────────────────────────────────────────────────────────
    json_path = out / f"backtest_results_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  [OK] JSON exported -> {json_path}")

    # ── Regime summary JSON ──────────────────────────────────────────────
    df = pd.DataFrame(all_results)
    df["is_win"] = df["result"] == "WIN"

    regime_matrix = (
        df.groupby(["strategy", "regime"])
        .agg(trades=("is_win", "count"), win_rate=("is_win", "mean"))
        .reset_index()
        .to_dict(orient="records")
    )
    summary_path = out / f"regime_matrix_{ts}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(regime_matrix, f, indent=2)
    print(f"  [OK] Regime matrix -> {summary_path}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print(f"\n{'-' * 70}")
    print(f"  {title}")
    print(f"{'-' * 70}")


def _pct(series: pd.Series) -> pd.Series:
    return (series * 100).round(2).astype(str) + "%"


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="QuFLX Backtest Engine — Strategy × Regime Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backtest.py data/AVAX_otc/2026-04-01.jsonl
  python backtest.py "c:\\v3\\OTC_SNIPER\\app\\data\\tick_logs"
  python backtest.py data/ --export-dir results/
        """,
    )
    parser.add_argument("path", help="Path to a .jsonl file or directory of .jsonl files")
    parser.add_argument(
        "--export-dir", "-o",
        default="backtest_output",
        help="Directory for CSV/JSON exports (default: backtest_output/)",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip CSV/JSON file export (print analysis only)",
    )
    args = parser.parse_args()

    engine      = BacktestEngine()
    all_results: List[Dict] = []

    input_path = Path(args.path)
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = sorted(input_path.rglob("*.jsonl"))
    else:
        print(f"✗ Path not found: {input_path}")
        sys.exit(1)

    print(f"\n{'=' * 70}")
    print(f"  QuFLX Backtest Engine -- {len(files)} file(s) queued")
    print(f"{'=' * 70}\n")

    t_start = time.time()

    for f in files:
        asset_name = f.parent.name if input_path.is_dir() else f.stem
        print(f">> [{asset_name}] {f.name}")
        candles = engine.load_ticks_to_candles(str(f))
        if not candles:
            print(f"    [WARN] No valid candles - skipping.")
            continue
        print(f"    Candles: {len(candles)}")
        file_results = engine.run_backtest(candles, asset_name)
        all_results.extend(file_results)
        wins  = sum(1 for r in file_results if r["result"] == "WIN")
        total = len(file_results)
        wr    = (wins / total * 100) if total else 0
        print(f"    Trades: {total}  |  Win rate: {wr:.1f}%")

    elapsed = time.time() - t_start
    print(f"\n  Total trades: {len(all_results)}")
    print(f"  Processing time: {elapsed:.2f}s")

    # ── Analysis ──────────────────────────────────────────────────────────
    analyze_results(all_results)

    # ── Export ────────────────────────────────────────────────────────────
    if not args.no_export and all_results:
        _section("Exporting Results")
        # noqa
        export_results(all_results, output_dir=args.export_dir)

    print(f"\n{'=' * 70}")
    print("  Backtest complete.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
