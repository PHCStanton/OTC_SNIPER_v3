"""
run_full_backtest_report.py
============================
Orchestrates a full OTEO backtest across ALL assets and ALL available dates,
then produces an HTML report showing:

  1. Best-performing assets per day of the week (UTC)
  2. Best-performing assets per hour of the day (UTC)

Usage (from C:\\v3\\OTC_SNIPER):
  python run_full_backtest_report.py [--expiry 15 30 60 90 120 180 300]
                                     [--payout-pct 92]
                                     [--report-root results]
                                     [--min-trades 5]
                                     [--top-n 5]
                                     [--level L3]
                                     [--skip-backtest]  # skip if CSV already exists

Run in QuFLX-v2 conda env from C:\\v3\\OTC_SNIPER directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
TICK_ROOT = REPO_ROOT / "app" / "data" / "tick_logs"
BACKTEST_SCRIPT = REPO_ROOT / "scripts" / "backtest_oteo_levels.py"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOURS = [f"{h:02d}:00" for h in range(24)]


# ── Step 1: Discover all dates ─────────────────────────────────────────────────
def discover_dates(tick_root: Path) -> list[str]:
    """Return sorted unique date strings (YYYY-MM-DD) found across all asset dirs."""
    dates: set[str] = set()
    for asset_dir in tick_root.iterdir():
        if not asset_dir.is_dir():
            continue
        for jsonl in asset_dir.glob("*.jsonl"):
            dates.add(jsonl.stem)
    return sorted(dates)


# ── Step 2: Run backtest ───────────────────────────────────────────────────────
def run_backtest(
    dates: list[str],
    tick_root: Path,
    report_root: Path,
    expiry: list[int],
    payout_pct: float,
) -> Path:
    """Invoke backtest_oteo_levels.py --mode replay over all dates/assets.
    Returns the path to the generated CSV file."""
    report_root.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(BACKTEST_SCRIPT),
        "--mode", "replay",
        "--dates", *dates,
        "--tick-root", str(tick_root),
        "--report-root", str(report_root),
        "--expiry", *[str(e) for e in expiry],
        "--payout-pct", str(payout_pct),
        "--report-title", "Full OTC Asset Backtest",
    ]

    print(f"\n[RUNNER] Running backtest for {len(dates)} dates across all assets...")
    print(f"[RUNNER] Command: {' '.join(cmd[:6])} ... (truncated)")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))

    if result.returncode != 0:
        print("[RUNNER ERROR] Backtest failed:")
        print(result.stderr[-3000:] if result.stderr else "(no stderr)")
        raise RuntimeError("Backtest script exited with non-zero status.")

    print(result.stdout)

    # Parse CSV path from output
    for line in result.stdout.splitlines():
        if line.strip().startswith("CSV report:"):
            csv_path = Path(line.split(":", 1)[1].strip())
            print(f"[RUNNER] CSV output: {csv_path}")
            return csv_path

    # Fallback: find the newest CSV in report_root
    csvs = sorted(report_root.glob("oteo_level_backtest_*.csv"), key=lambda p: p.stat().st_mtime)
    if not csvs:
        raise FileNotFoundError(f"No CSV found in {report_root}")
    return csvs[-1]


# ── Step 3: Load & aggregate CSV ───────────────────────────────────────────────
def load_csv(csv_path: Path) -> list[dict]:
    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f"[RUNNER] Loaded {len(rows):,} rows from CSV")
    return rows


def _aggregate(
    rows: list[dict],
    group_fn,          # row -> group key (str)
    level_filter: str | None,
    min_trades: int,
) -> dict[str, dict[str, dict]]:
    """
    Returns: { group_key: { asset: { wins, losses, trades, win_rate } } }
    Only counts rows with outcome in {win, loss}.
    """
    # group_key -> asset -> {wins, losses}
    data: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "losses": 0}))

    for row in rows:
        outcome = row.get("outcome", "")
        if outcome not in ("win", "loss"):
            continue

        # Optionally filter by strategy level
        if level_filter and row.get("level", "") != level_filter:
            continue

        asset = row.get("asset", "")
        try:
            ts = float(row.get("entry_time", 0))
            group_key = group_fn(ts)
        except (ValueError, TypeError):
            continue

        bucket = data[group_key][asset]
        if outcome == "win":
            bucket["wins"] += 1
        else:
            bucket["losses"] += 1

    # Compute win_rate, filter by min_trades
    result: dict[str, dict[str, dict]] = {}
    for group_key, assets in data.items():
        result[group_key] = {}
        for asset, stats in assets.items():
            total = stats["wins"] + stats["losses"]
            if total < min_trades:
                continue
            wr = round((stats["wins"] / total) * 100, 2)
            result[group_key][asset] = {
                "wins": stats["wins"],
                "losses": stats["losses"],
                "trades": total,
                "win_rate": wr,
            }

    return result


def aggregate_by_dow(rows: list[dict], level_filter: str | None, min_trades: int) -> dict:
    def group_fn(ts: float) -> str:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return DAYS[dt.weekday()]

    return _aggregate(rows, group_fn, level_filter, min_trades)


def aggregate_by_hour(rows: list[dict], level_filter: str | None, min_trades: int) -> dict:
    def group_fn(ts: float) -> str:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return f"{dt.hour:02d}:00"

    return _aggregate(rows, group_fn, level_filter, min_trades)


def top_assets(asset_dict: dict[str, dict], top_n: int) -> list[tuple[str, dict]]:
    """Return top_n assets sorted by win_rate desc."""
    return sorted(asset_dict.items(), key=lambda kv: -kv[1]["win_rate"])[:top_n]


# ── Step 4: Generate HTML ──────────────────────────────────────────────────────
def _wr_color(wr: float) -> str:
    """Return a CSS class based on win rate."""
    if wr >= 65:
        return "wr-excellent"
    if wr >= 58:
        return "wr-good"
    if wr >= 52:
        return "wr-ok"
    return "wr-poor"


def _render_asset_badges(ranked: list[tuple[str, dict]], breakeven: float) -> str:
    if not ranked:
        return '<span class="no-data">No data (insufficient trades)</span>'
    parts = []
    for asset, stats in ranked:
        wr = stats["win_rate"]
        cls = _wr_color(wr)
        parts.append(
            f'<span class="badge {cls}" title="{stats["trades"]} trades | '
            f'{stats["wins"]}W / {stats["losses"]}L">'
            f'{asset} <em>{wr:.1f}%</em></span>'
        )
    return " ".join(parts)


def generate_html(
    dow_data: dict,
    hour_data: dict,
    top_n: int,
    breakeven: float,
    csv_path: Path,
    total_rows: int,
    level_filter: str | None,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── Day-of-Week section ──
    dow_rows_html = []
    for day in DAYS:
        assets = dow_data.get(day, {})
        ranked = top_assets(assets, top_n)
        dow_rows_html.append(f"""
        <tr>
          <td class="day-label">{day}</td>
          <td class="badges-cell">{_render_asset_badges(ranked, breakeven)}</td>
        </tr>""")

    # ── Hour section ──
    hour_rows_html = []
    for hour in HOURS:
        assets = hour_data.get(hour, {})
        ranked = top_assets(assets, top_n)
        hour_rows_html.append(f"""
        <tr>
          <td class="hour-label">{hour} UTC</td>
          <td class="badges-cell">{_render_asset_badges(ranked, breakeven)}</td>
        </tr>""")

    level_label = level_filter if level_filter else "All Levels"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OTC Sniper — Asset Performance Report</title>
  <meta name="description" content="Best-performing OTC assets per day of week and UTC hour, derived from OTEO backtest results." />
  <style>
    /* ── Reset & Base ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=JetBrains+Mono:wght@400;600&display=swap');

    :root {{
      --bg:          #0a0c14;
      --bg2:         #0f1220;
      --bg3:         #151927;
      --card:        #1a1f2e;
      --card-border: rgba(255,255,255,0.06);
      --accent:      #6366f1;
      --accent2:     #8b5cf6;
      --gold:        #f59e0b;
      --text:        #e2e8f0;
      --text-muted:  #64748b;
      --text-dim:    #94a3b8;

      --wr-excellent: #10b981;
      --wr-good:      #3b82f6;
      --wr-ok:        #f59e0b;
      --wr-poor:      #ef4444;
    }}

    html {{ scroll-behavior: smooth; }}

    body {{
      font-family: 'Inter', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      line-height: 1.6;
    }}

    /* ── Header ── */
    .site-header {{
      background: linear-gradient(135deg, #0f1220 0%, #1a1040 50%, #0f1220 100%);
      border-bottom: 1px solid var(--card-border);
      padding: 2.5rem 2rem 2rem;
      text-align: center;
      position: relative;
      overflow: hidden;
    }}
    .site-header::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: radial-gradient(ellipse 80% 60% at 50% -20%, rgba(99,102,241,0.18), transparent);
      pointer-events: none;
    }}
    .site-header .logo {{
      font-size: 0.75rem;
      letter-spacing: 0.25em;
      text-transform: uppercase;
      color: var(--accent);
      font-weight: 600;
      margin-bottom: 0.5rem;
    }}
    .site-header h1 {{
      font-size: clamp(1.6rem, 4vw, 2.8rem);
      font-weight: 900;
      background: linear-gradient(135deg, #e2e8f0, var(--accent), var(--accent2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 0.75rem;
    }}
    .site-header .subtitle {{
      color: var(--text-dim);
      font-size: 0.95rem;
      max-width: 600px;
      margin: 0 auto;
    }}

    /* ── Meta bar ── */
    .meta-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      justify-content: center;
      padding: 1rem 2rem;
      background: var(--bg2);
      border-bottom: 1px solid var(--card-border);
    }}
    .meta-pill {{
      display: flex;
      align-items: center;
      gap: 0.4rem;
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 999px;
      padding: 0.3rem 0.9rem;
      font-size: 0.78rem;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-dim);
    }}
    .meta-pill .label {{ color: var(--text-muted); }}
    .meta-pill .value {{ color: var(--text); font-weight: 600; }}

    /* ── Layout ── */
    main {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 2.5rem 1.5rem;
    }}

    /* ── Legend ── */
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 2rem;
      align-items: center;
    }}
    .legend-title {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--text-muted);
      margin-right: 0.25rem;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.78rem;
      color: var(--text-dim);
    }}
    .legend-dot {{
      width: 10px; height: 10px;
      border-radius: 50%;
    }}
    .legend-dot.excellent {{ background: var(--wr-excellent); }}
    .legend-dot.good      {{ background: var(--wr-good); }}
    .legend-dot.ok        {{ background: var(--wr-ok); }}
    .legend-dot.poor      {{ background: var(--wr-poor); }}

    /* ── Section cards ── */
    .section-card {{
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      margin-bottom: 2.5rem;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }}
    .section-head {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1.25rem 1.75rem;
      border-bottom: 1px solid var(--card-border);
      background: linear-gradient(90deg, rgba(99,102,241,0.08), transparent);
    }}
    .section-icon {{
      font-size: 1.4rem;
    }}
    .section-head h2 {{
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--text);
    }}
    .section-head .section-sub {{
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-left: auto;
    }}

    /* ── Table ── */
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    tr {{
      border-bottom: 1px solid rgba(255,255,255,0.04);
      transition: background 0.15s;
    }}
    tr:hover {{ background: rgba(99,102,241,0.04); }}
    tr:last-child {{ border-bottom: none; }}

    td {{
      padding: 0.85rem 1.75rem;
      vertical-align: top;
    }}

    .day-label, .hour-label {{
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
      color: var(--accent);
      font-size: 0.88rem;
      min-width: 120px;
      padding-top: 1.1rem;
      white-space: nowrap;
    }}
    .hour-label {{
      color: var(--accent2);
      min-width: 100px;
    }}

    .badges-cell {{
      padding-top: 0.85rem;
      padding-bottom: 0.85rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      align-items: center;
    }}

    /* ── Badges ── */
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.35rem 0.75rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.01em;
      border: 1px solid transparent;
      cursor: default;
      transition: transform 0.1s, box-shadow 0.1s;
      position: relative;
    }}
    .badge:hover {{
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }}
    .badge em {{
      font-style: normal;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      opacity: 0.9;
    }}

    .wr-excellent {{
      background: rgba(16,185,129,0.15);
      border-color: rgba(16,185,129,0.3);
      color: #34d399;
    }}
    .wr-good {{
      background: rgba(59,130,246,0.15);
      border-color: rgba(59,130,246,0.3);
      color: #60a5fa;
    }}
    .wr-ok {{
      background: rgba(245,158,11,0.15);
      border-color: rgba(245,158,11,0.3);
      color: #fbbf24;
    }}
    .wr-poor {{
      background: rgba(239,68,68,0.12);
      border-color: rgba(239,68,68,0.25);
      color: #f87171;
    }}

    .no-data {{
      color: var(--text-muted);
      font-size: 0.82rem;
      font-style: italic;
    }}

    /* ── Tooltip hint ── */
    .badge[title]:hover::after {{
      content: attr(title);
      position: absolute;
      bottom: calc(100% + 6px);
      left: 50%;
      transform: translateX(-50%);
      background: #1e2535;
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 0.4rem 0.7rem;
      border-radius: 6px;
      font-size: 0.72rem;
      white-space: nowrap;
      z-index: 10;
      pointer-events: none;
      font-family: 'JetBrains Mono', monospace;
    }}

    /* ── Footer ── */
    footer {{
      text-align: center;
      padding: 2rem;
      color: var(--text-muted);
      font-size: 0.78rem;
      border-top: 1px solid var(--card-border);
    }}
    footer a {{ color: var(--accent); text-decoration: none; }}

    /* ── Responsive ── */
    @media (max-width: 640px) {{
      .meta-bar {{ padding: 0.75rem 1rem; }}
      td {{ padding: 0.6rem 1rem; }}
      .day-label, .hour-label {{ min-width: 80px; font-size: 0.8rem; }}
      .badge {{ font-size: 0.72rem; padding: 0.3rem 0.55rem; }}
    }}
  </style>
</head>
<body>

<header class="site-header">
  <div class="logo">OTC Sniper v3 · OTEO Strategy</div>
  <h1>Asset Performance Report</h1>
  <p class="subtitle">
    Best-performing OTC assets ranked by win-rate, broken down by
    <strong>Day of Week</strong> and <strong>UTC Hour</strong>.
    Top {top_n} assets per slot shown.
  </p>
</header>

<div class="meta-bar">
  <div class="meta-pill"><span class="label">Generated</span><span class="value">{generated_at}</span></div>
  <div class="meta-pill"><span class="label">Total rows</span><span class="value">{total_rows:,}</span></div>
  <div class="meta-pill"><span class="label">Level filter</span><span class="value">{level_label}</span></div>
  <div class="meta-pill"><span class="label">Breakeven</span><span class="value">{breakeven:.2f}%</span></div>
  <div class="meta-pill"><span class="label">Min trades/slot</span><span class="value">shown in tooltip</span></div>
  <div class="meta-pill"><span class="label">Source</span><span class="value">{csv_path.name}</span></div>
</div>

<main>

  <div class="legend">
    <span class="legend-title">Win-Rate Key:</span>
    <span class="legend-item"><span class="legend-dot excellent"></span>≥65% Excellent</span>
    <span class="legend-item"><span class="legend-dot good"></span>≥58% Good</span>
    <span class="legend-item"><span class="legend-dot ok"></span>≥52% OK</span>
    <span class="legend-item"><span class="legend-dot poor"></span>&lt;52% Below breakeven</span>
    <span style="color:var(--text-muted);font-size:0.75rem;margin-left:auto">Hover badge for trade count</span>
  </div>

  <!-- ── Day of Week ── -->
  <section class="section-card" id="day-of-week">
    <div class="section-head">
      <span class="section-icon">📅</span>
      <h2>Best Assets by Day of Week (UTC)</h2>
      <span class="section-sub">Top {top_n} per day · sorted by win-rate</span>
    </div>
    <table>
      <tbody>
        {''.join(dow_rows_html)}
      </tbody>
    </table>
  </section>

  <!-- ── UTC Hour ── -->
  <section class="section-card" id="utc-hour">
    <div class="section-head">
      <span class="section-icon">🕐</span>
      <h2>Best Assets by UTC Hour</h2>
      <span class="section-sub">Top {top_n} per hour · sorted by win-rate</span>
    </div>
    <table>
      <tbody>
        {''.join(hour_rows_html)}
      </tbody>
    </table>
  </section>

</main>

<footer>
  Generated by <strong>OTC Sniper v3</strong> · OTEO Backtest Engine ·
  Source: <code>{csv_path.name}</code>
</footer>

</body>
</html>"""


# ── CLI ────────────────────────────────────────────────────────────────────────
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Full backtest runner + HTML performance report.")
    p.add_argument("--expiry", nargs="+", type=int, default=[15, 30, 60, 90, 120, 180, 300])
    p.add_argument("--payout-pct", type=float, default=92.0)
    p.add_argument("--report-root", type=Path, default=Path("results"))
    p.add_argument("--min-trades", type=int, default=5,
                   help="Minimum settled trades per (asset, slot) to include in ranking")
    p.add_argument("--top-n", type=int, default=5, help="Number of top assets to show per slot")
    p.add_argument("--level", type=str, default=None,
                   help="Filter by strategy level: L1, L2, L3 (default: all)")
    p.add_argument("--skip-backtest", action="store_true",
                   help="Skip running the backtest; use the most recent CSV in --report-root")
    p.add_argument("--csv", type=Path, default=None,
                   help="Directly supply an existing CSV instead of running the backtest")
    return p


def main() -> int:
    args = _build_parser().parse_args()
    report_root: Path = args.report_root.resolve() if not args.report_root.is_absolute() else args.report_root
    report_root = REPO_ROOT / args.report_root if not args.report_root.is_absolute() else args.report_root

    breakeven = round(100.0 / (1.0 + args.payout_pct / 100.0), 2)

    # ── Find / run backtest ──
    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"[ERROR] CSV not found: {csv_path}")
            return 1
    elif args.skip_backtest:
        csvs = sorted(report_root.glob("oteo_level_backtest_*.csv"), key=lambda p: p.stat().st_mtime)
        if not csvs:
            print(f"[ERROR] No existing CSVs in {report_root}. Remove --skip-backtest to run fresh.")
            return 1
        csv_path = csvs[-1]
        print(f"[RUNNER] Re-using existing CSV: {csv_path}")
    else:
        dates = discover_dates(TICK_ROOT)
        if not dates:
            print(f"[ERROR] No tick log dates found under {TICK_ROOT}")
            return 1
        print(f"[RUNNER] Found {len(dates)} unique dates: {dates[0]} to {dates[-1]}")
        csv_path = run_backtest(dates, TICK_ROOT, report_root, args.expiry, args.payout_pct)

    # ── Load data ──
    rows = load_csv(csv_path)
    total_rows = len(rows)

    # ── Aggregate ──
    print(f"[RUNNER] Aggregating by day-of-week and UTC hour (level={args.level or 'all'})...")
    dow_data = aggregate_by_dow(rows, args.level, args.min_trades)
    hour_data = aggregate_by_hour(rows, args.level, args.min_trades)

    # ── Generate HTML ──
    html = generate_html(
        dow_data=dow_data,
        hour_data=hour_data,
        top_n=args.top_n,
        breakeven=breakeven,
        csv_path=csv_path,
        total_rows=total_rows,
        level_filter=args.level,
    )

    html_path = report_root / "asset_performance_report.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    print(f"\n[RUNNER] SUCCESS - HTML report written: {html_path}")
    print(f"[RUNNER]    Open: file:///{html_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
