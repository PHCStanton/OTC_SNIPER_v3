import json
from collections import defaultdict

def main():
    filepath = r"c:\v3\OTC_SNIPER\app\data\ghost_trades\sessions\Level2_auto_ghost_1775496615.jsonl"
    
    trades = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    trades.append(json.loads(line))
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"Total trades analyzed for manipulation: {len(trades)}")
    
    manipulation_counts = defaultdict(int)
    manipulation_details = []
    
    for t in trades:
        # Check both the top-level manipulation field and the one inside entry_context
        top_man = t.get('manipulation_at_entry')
        ctx_man = t.get('entry_context', {}).get('manipulation', {})
        
        # In AutoGhostService, trades are blocked if config.block_on_manipulation is True
        # So any trade that actually executed means manipulation was empty/falsy at the exact entry tick
        
        if top_man:
            for k, v in top_man.items():
                if v: manipulation_counts[k] += 1
                
        if ctx_man:
            for k, v in ctx_man.items():
                if v: manipulation_counts[f"ctx_{k}"] += 1

    print("\nManipulation Flags Present in Executed Trades:")
    if not manipulation_counts:
        print("  None. All executed trades had empty manipulation flags at the exact moment of entry.")
    else:
        for k, v in manipulation_counts.items():
            print(f"  - {k}: {v}")

if __name__ == '__main__':
    main()