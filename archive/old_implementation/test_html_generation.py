#!/usr/bin/env python3
"""Quick test of trading_analysis.html generation"""

from visualize_trading_analysis import TradingVisualizer

print("🧪 Testing trading_analysis.html generation...")

visualizer = TradingVisualizer(
    ema_data_file='trading_data/ema_data_5min.csv',
    decisions_file='trading_data/claude_decisions.csv',
    optimal_trades_file='trading_data/optimal_trades.json',
    backtest_trades_file='trading_data/backtest_trades.json'
)

if visualizer.load_data():
    print("✅ Data loaded")
    
    fig = visualizer.create_visualization(hours_back=24, show_all_emas=True)
    
    if fig:
        print("✅ Figure created")
        
        # save_html adds 'trading_data/' prefix, so just pass filename
        html_path = visualizer.save_html(fig, 'trading_analysis.html')
        print(f"✅ HTML saved: {html_path}")
        
        import os
        if os.path.exists(html_path):
            size_kb = os.path.getsize(html_path) / 1024
            print(f"📊 File size: {size_kb:.0f}KB")
            print(f"🌐 Open: file://{os.path.abspath(html_path)}")
        else:
            print("❌ File doesn't exist!")
    else:
        print("❌ Figure is None")
else:
    print("❌ Could not load data")
