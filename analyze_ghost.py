import json
import pandas as pd

def analyze_ghost_trades(file_path):
    with open(file_path, 'r') as f:
        data = [json.loads(line) for line in f]

    df = pd.json_normalize(data)
    
    # Flatten entry_context
    contexts = [d.get('entry_context', {}).get('market_context', {}) for d in data]
    context_df = pd.json_normalize(contexts)
    df = pd.concat([df, context_df], axis=1)

    print("--- OVERALL PERFORMANCE ---")
    outcomes = df['outcome'].value_counts()
    wins = outcomes.get('win', 0)
    losses = outcomes.get('loss', 0)
    print(f"Total Trades: {len(df)}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {(wins / (wins + losses) * 100) if (wins+losses) > 0 else 0:.2f}%\n")

    print("--- BY TREND REGIME (ADX) ---")
    if 'adx_regime' in df.columns:
        regime_perf = df.groupby('adx_regime')['outcome'].value_counts().unstack().fillna(0)
        if 'win' in regime_perf.columns and 'loss' in regime_perf.columns:
            regime_perf['win_rate'] = regime_perf['win'] / (regime_perf['win'] + regime_perf['loss']) * 100
            print(regime_perf)
    print("\n")
    
    print("--- SUPPORT / RESISTANCE ALIGNMENT ---")
    if 'support_alignment' in df.columns and 'resistance_alignment' in df.columns:
        df['structure_alignment'] = df.apply(lambda x: 'Aligned' if (x['direction']=='call' and x['support_alignment']) or (x['direction']=='put' and x['resistance_alignment']) else 'Unaligned', axis=1)
        align_perf = df.groupby('structure_alignment')['outcome'].value_counts().unstack().fillna(0)
        if 'win' in align_perf.columns and 'loss' in align_perf.columns:
            align_perf['win_rate'] = align_perf['win'] / (align_perf['win'] + align_perf['loss']) * 100
            print(align_perf)
    print("\n")

    print("--- CCI CONFIRMATION ---")
    if 'cci_state' in df.columns:
        df['cci_aligned'] = df.apply(lambda x: 'Aligned' if (x['direction']=='call' and x['cci_state']=='oversold') or (x['direction']=='put' and x['cci_state']=='overbought') else 'Unaligned/Neutral', axis=1)
        cci_perf = df.groupby('cci_aligned')['outcome'].value_counts().unstack().fillna(0)
        if 'win' in cci_perf.columns and 'loss' in cci_perf.columns:
            cci_perf['win_rate'] = cci_perf['win'] / (cci_perf['win'] + cci_perf['loss']) * 100
            print(cci_perf)
            
if __name__ == "__main__":
    analyze_ghost_trades('app/data/ghost_trades/sessions/auto_ghost_1775294721.jsonl')