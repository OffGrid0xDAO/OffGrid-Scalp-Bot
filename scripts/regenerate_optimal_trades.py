#!/usr/bin/env python3
"""
Regenerate Optimal Trades Analysis

Quick script to re-run optimal trade finder on existing data.
Useful for seeing what's theoretically possible.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from analysis.optimal_trade_finder import OptimalTradeFinder

# Load data
data_file = Path(__file__).parent.parent / 'trading_data' / 'indicators' / 'eth_1h_full.csv'

if not data_file.exists():
    print(f"❌ Data file not found: {data_file}")
    sys.exit(1)

print(f"📊 Loading: {data_file}")
df = pd.read_csv(data_file)
print(f"   {len(df)} candles")

# Find optimal trades (24 candles = 1 day for 1h timeframe)
finder = OptimalTradeFinder(min_profit_pct=1.0, max_hold_candles=24)
optimal_trades = finder.scan_all_optimal_trades(df)

# Analyze
if optimal_trades:
    analysis = finder.analyze_optimal_conditions(optimal_trades)

    # Save
    output_file = Path(__file__).parent.parent / 'trading_data' / 'backtest' / 'eth_1h_optimal_trades.csv'
    finder.save_optimal_trades(optimal_trades, str(output_file))

print("\n✅ Done!")
