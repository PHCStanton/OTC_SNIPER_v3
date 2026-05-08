import os
import json
from collections import defaultdict

def process_signal_files(signal_dir):
    """Process all signal JSONL files and return asset statistics"""
    asset_signals = defaultdict(lambda: {
        'total_signals': 0,
        'manipulated_signals': 0,
        'signals': []
    })
    
    for filename in os.listdir(signal_dir):
        if not filename.endswith('.jsonl') or filename.startswith('.'):
            continue
            
        filepath = os.path.join(signal_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    asset = data['asset']
                    asset_signals[asset]['total_signals'] += 1
                    if data.get('manip', False):
                        asset_signals[asset]['manipulated_signals'] += 1
                    asset_signals[asset]['signals'].append(data)
                except json.JSONDecodeError:
                    continue
    
    return asset_signals

def process_ghost_trades(ghost_dir):
    """Process all ghost trade JSONL files and return trade statistics"""
    asset_trades = defaultdict(lambda: {
        'total_trades': 0,
        'total_profit': 0.0,
        'manipulated_trades': 0,
        'trades': []
    })
    
    sessions_dir = os.path.join(ghost_dir, 'sessions')
    for filename in os.listdir(sessions_dir):
        if not filename.endswith('.jsonl') or filename.startswith('.'):
            continue
            
        filepath = os.path.join(sessions_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    asset = data['asset']
                    asset_trades[asset]['total_trades'] += 1
                    # Fixed the None check for profit
                    profit = data.get('profit')
                    asset_trades[asset]['total_profit'] += profit if profit is not None else 0.0
                    
                    # Check for manipulation at entry
                    if data.get('manip_at_entry') and data['manip_at_entry'] != {}:
                        asset_trades[asset]['manipulated_trades'] += 1
                    # Also check entry context manipulation
                    if data.get('entry_context', {}).get('manipulation', {}) != {}:
                        asset_trades[asset]['manipulated_trades'] += 1
                        
                    asset_trades[asset]['trades'].append(data)
                except json.JSONDecodeError:
                    continue
    
    return asset_trades

def generate_report(asset_signals, asset_trades, output_file='trade_analysis.html'):
    """Generate HTML report with analysis results"""
    # Combine signal and trade data
    combined_data = {}
    all_assets = set(asset_signals.keys()).union(set(asset_trades.keys()))
    
    for asset in all_assets:
        combined_data[asset] = {
            'total_signals': asset_signals[asset]['total_signals'],
            'manipulated_signals': asset_signals[asset]['manipulated_signals'],
            'total_trades': asset_trades[asset]['total_trades'],
            'total_profit': asset_trades[asset]['total_profit'],
            'manipulated_trades': asset_trades[asset]['manipulated_trades'],
            'total_manipulated': asset_signals[asset]['manipulated_signals'] + asset_trades[asset]['manipulated_trades'],
            'net_profit_per_trade': asset_trades[asset]['total_profit'] / max(1, asset_trades[asset]['total_trades']) if asset_trades[asset]['total_trades'] > 0 else 0
        }
    
    # Sort by total trades to find least traded assets
    sorted_by_trades = sorted(combined_data.items(), key=lambda x: x[1]['total_trades'])
    
    # Find top 10 most profitable least traded assets
    # First filter assets with at least 1 trade
    tradable_assets = [a for a in sorted_by_trades if a[1]['total_trades'] > 0]
    
    # For least traded assets, take the smallest group first, then sort by profit
    if tradable_assets:
        min_trade_count = tradable_assets[0][1]['total_trades']
        least_traded = [a for a in tradable_assets if a[1]['total_trades'] == min_trade_count]
        # Sort least traded assets by profit descending
        least_traded_sorted = sorted(least_traded, key=lambda x: x[1]['total_profit'], reverse=True)
        top_10_profitable_least = least_traded_sorted[:10]
    else:
        top_10_profitable_least = []
    
    # Sort assets by least manipulation
    sorted_by_manipulation = sorted(combined_data.items(), key=lambda x: x[1]['total_manipulated'])
    
    # Generate HTML
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OTC Sniper Trade Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        body {{
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            text-align: center;
            color: #2c3e50;
            margin-bottom: 30px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        h2 {{
            color: #34495e;
            margin-bottom: 20px;
            padding-left: 10px;
            border-left: 4px solid #3498db;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #3498db;
        }}
        
        .stat-label {{
            font-size: 0.9rem;
            color: #7f8c8d;
            margin-top: 5px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            overflow-x: auto;
            display: block;
        }}
        
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        
        th {{
            background-color: #3498db;
            color: white;
        }}
        
        tr:hover {{
            background-color: #f5f7fa;
        }}
        
        .profit-positive {{
            color: #27ae60;
            font-weight: bold;
        }}
        
        .profit-negative {{
            color: #e74c3c;
            font-weight: bold;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 20px 0;
        }}
        
        .asset-list {{
            max-height: 500px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OTC Sniper Trade & Signal Analysis Report</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{total_assets}}</div>
                <div class="stat-label">Total Assets</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{total_signals}}</div>
                <div class="stat-label">Total Signals Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{total_trades}}</div>
                <div class="stat-label">Total Trades Executed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{total_profit:.2f}}</div>
                <div class="stat-label">Total Net Profit ($)</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Top 10 Most Profitable Assets with Least Trades</h2>
            <div class="asset-list">
                <table>
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Total Trades</th>
                            <th>Total Profit</th>
                            <th>Profit Per Trade</th>
                            <th>Manipulated Trades</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{top_10_rows}}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="section">
            <h2>Assets with Least Manipulation Flags</h2>
            <div class="asset-list">
                <table>
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Total Trades</th>
                            <th>Total Manipulated Flags</th>
                            <th>Total Profit</th>
                            <th>Profit Per Trade</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{least_manip_rows}}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="section">
            <h2>Profit Distribution Chart</h2>
            <div class="chart-container">
                <canvas id="profitChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('profitChart').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {profit_labels},
                datasets: [{{
                    label: 'Total Profit per Asset',
                    data: {profit_values},
                    backgroundColor: 'rgba(52, 152, 219, 0.6)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Total Profit ($)'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Asset'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    # Calculate summary stats
    total_assets = len(combined_data)
    total_signals = sum(v['total_signals'] for v in combined_data.values())
    total_trades = sum(v['total_trades'] for v in combined_data.values())
    total_profit = sum(v['total_profit'] for v in combined_data.values())
    
    # Generate top 10 rows
    top_10_rows = ""
    for asset, stats in top_10_profitable_least:
        profit_class = "profit-positive" if stats['total_profit'] >= 0 else "profit-negative"
        top_10_rows += f"""<tr>
            <td>{asset}</td>
            <td>{stats['total_trades']}</td>
            <td class="{profit_class}">{stats['total_profit']:.2f}</td>
            <td class="{profit_class}">{stats['net_profit_per_trade']:.2f}</td>
            <td>{stats['total_manipulated']}</td>
        </tr>"""
    
    # Generate least manip rows
    least_manip_rows = ""
    for asset, stats in sorted_by_manipulation[:10]:
        profit_class = "profit-positive" if stats['total_profit'] >= 0 else "profit-negative"
        least_manip_rows += f"""<tr>
            <td>{asset}</td>
            <td>{stats['total_trades']}</td>
            <td>{stats['total_manipulated']}</td>
            <td class="{profit_class}">{stats['total_profit']:.2f}</td>
            <td class="{profit_class}">{stats['net_profit_per_trade']:.2f}</td>
        </tr>"""
    
    # Chart data
    profit_chart_data = sorted(combined_data.items(), key=lambda x: x[1]['total_profit'], reverse=True)[:15]
    profit_labels = json.dumps([asset for asset, _ in profit_chart_data])
    profit_values = json.dumps([stats['total_profit'] for _, stats in profit_chart_data])
    
    # Replace placeholders
    html = html.format(
        total_assets=total_assets,
        total_signals=total_signals,
        total_trades=total_trades,
        total_profit=total_profit,
        top_10_rows=top_10_rows,
        least_manip_rows=least_manip_rows,
        profit_labels=profit_labels,
        profit_values=profit_values
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Report generated successfully: {output_file}")
    print(f"Analyzed {total_assets} assets, {total_signals} total signals, {total_trades} total trades")
    print(f"Total net profit: ${total_profit:.2f}")

def main():
    signal_dir = 'app/data/signals'
    ghost_dir = 'app/data/ghost_trades'
    
    print("Processing signal files...")
    asset_signals = process_signal_files(signal_dir)
    
    print("Processing ghost trade files...")
    asset_trades = process_ghost_trades(ghost_dir)
    
    print("Generating HTML report...")
    generate_report(asset_signals, asset_trades)

if __name__ == "__main__":
    main()