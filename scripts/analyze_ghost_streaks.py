import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

def analyze_streaks(session_path: Path):
    if not session_path.exists():
        print(f"File not found: {session_path}")
        return

    trades = []
    with open(session_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                trades.append(json.loads(line))

    if not trades:
        print(f"No trades found in {session_path.name}")
        return

    # Sort trades by entry time to ensure chronological analysis
    trades.sort(key=lambda x: x.get('entry_time') or x.get('timestamp') or 0)

    current_streak_type = None
    current_streak_count = 0
    current_streak_start_time = None
    
    streaks = []

    for trade in trades:
        outcome = trade.get('outcome')
        # Skip void or pending trades for streak analysis
        if outcome not in ['win', 'loss']:
            continue
            
        timestamp = trade.get('entry_time') or trade.get('timestamp') or 0

        if outcome == current_streak_type:
            current_streak_count += 1
        else:
            # Streak ended, record it
            if current_streak_type is not None:
                duration = timestamp - current_streak_start_time
                streaks.append({
                    'type': current_streak_type,
                    'count': current_streak_count,
                    'start_time': current_streak_start_time,
                    'end_time': timestamp,
                    'duration_seconds': duration
                })
            
            # Start new streak
            current_streak_type = outcome
            current_streak_count = 1
            current_streak_start_time = timestamp

    # Add the last streak
    if current_streak_type is not None:
        last_timestamp = trades[-1].get('entry_time') or trades[-1].get('timestamp') or 0
        streaks.append({
            'type': current_streak_type,
            'count': current_streak_count,
            'start_time': current_streak_start_time,
            'end_time': last_timestamp,
            'duration_seconds': last_timestamp - current_streak_start_time
        })

    # Summary Statistics
    win_streaks = [s for s in streaks if s['type'] == 'win']
    loss_streaks = [s for s in streaks if s['type'] == 'loss']

    def get_stats(streak_list):
        if not streak_list:
            return {"max_count": 0, "avg_count": 0, "max_duration": 0, "avg_duration": 0}
        counts = [s['count'] for s in streak_list]
        durations = [s['duration_seconds'] for s in streak_list]
        return {
            "max_count": max(counts),
            "avg_count": sum(counts) / len(counts),
            "max_duration": max(durations),
            "avg_duration": sum(durations) / len(durations)
        }

    win_stats = get_stats(win_streaks)
    loss_stats = get_stats(loss_streaks)

    print(f"\n--- Analysis for {session_path.name} ---")
    print(f"Total Trades: {len(trades)}")
    print(f"Total Streaks: {len(streaks)}")
    
    print("\nWIN STREAKS:")
    print(f"  Max Streak: {win_stats['max_count']} trades")
    print(f"  Avg Streak: {win_stats['avg_count']:.2f} trades")
    print(f"  Max Duration: {win_stats['max_duration']/60:.2f} minutes")
    print(f"  Avg Duration: {win_stats['avg_duration']/60:.2f} minutes")

    print("\nLOSS STREAKS (Recovery Analysis):")
    print(f"  Max Streak: {loss_stats['max_count']} trades")
    print(f"  Avg Streak: {loss_stats['avg_count']:.2f} trades")
    print(f"  Max Time to Recovery: {loss_stats['max_duration']/60:.2f} minutes")
    print(f"  Avg Time to Recovery: {loss_stats['avg_duration']/60:.2f} minutes")
    
    # Identify the longest loss streak for "Market Recovery" advice
    if loss_streaks:
        longest_loss = max(loss_streaks, key=lambda x: x['count'])
        print(f"\nLongest Loss Streak occurred at: {datetime.fromtimestamp(longest_loss['start_time'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

def main():
    parser = argparse.ArgumentParser(description="Analyze win/loss streaks in ghost trade sessions.")
    parser.add_argument("--session", type=Path, help="Path to a specific session file.")
    parser.add_argument("--dir", type=Path, default=Path("app/data/ghost_trades/sessions"), help="Directory to scan.")
    parser.add_argument("--latest", action="store_true", help="Analyze only the most recent session.")
    
    args = parser.parse_args()

    if args.session:
        analyze_streaks(args.session)
    elif args.latest:
        files = sorted(args.dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
        if files:
            analyze_streaks(files[0])
    else:
        for file in sorted(args.dir.glob("*.jsonl")):
            analyze_streaks(file)

if __name__ == "__main__":
    main()
