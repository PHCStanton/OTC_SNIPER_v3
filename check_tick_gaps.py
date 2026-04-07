import json
from collections import defaultdict

def main():
    ghost_filepath = r"c:\v3\OTC_SNIPER\app\data\ghost_trades\sessions\Level2_auto_ghost_1775496615.jsonl"
    
    # Extract entry times and assets from the Ghost trades
    trade_events = []
    try:
        with open(ghost_filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    t = json.loads(line)
                    trade_events.append({
                        'asset': t['asset'],
                        'entry_time': t['entry_context']['timestamp']
                    })
    except Exception as e:
        print(f"Error reading ghost file: {e}")
        return

    print(f"Total ghost trades extracted: {len(trade_events)}")
    
    if not trade_events:
        return
        
    # Group trades by asset
    trades_by_asset = defaultdict(list)
    for t in trade_events:
        trades_by_asset[t['asset']].append(t['entry_time'])
        
    print("\nAnalyzing tick continuity around trade entries for 2026-04-06...")
    
    for asset, times in trades_by_asset.items():
        tick_filepath = rf"c:\v3\OTC_SNIPER\app\data\tick_logs\{asset}\2026-04-06.jsonl"
        
        try:
            # Read tick timestamps
            ticks = []
            with open(tick_filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        ticks.append(json.loads(line)['t'])
                        
            if not ticks:
                continue
                
            # For each trade, check the tick interval right before the trade
            for trade_time in times:
                # Find ticks within 5 seconds before the trade
                recent_ticks = [ts for ts in ticks if trade_time - 5 <= ts <= trade_time]
                
                if not recent_ticks:
                    print(f"  [{asset}] WARNING: No ticks found in the 5 seconds before trade at {trade_time}!")
                    continue
                    
                # Calculate max gap between these recent ticks
                if len(recent_ticks) >= 2:
                    gaps = [recent_ticks[i] - recent_ticks[i-1] for i in range(1, len(recent_ticks))]
                    max_gap = max(gaps)
                    if max_gap > 1.5:  # Standard OTC tick is ~1s, so >1.5s is a noticeable gap
                        print(f"  [{asset}] Trade at {trade_time}: Noticeable tick gap of {max_gap:.2f}s just before entry.")
                        
        except FileNotFoundError:
            print(f"  No tick log found for {asset} on 2026-04-06")
        except Exception as e:
            print(f"  Error reading tick log for {asset}: {e}")

if __name__ == '__main__':
    main()