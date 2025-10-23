#!/usr/bin/env python3
"""
Regenerate optimal_trades.json from ALL current historical data
"""

import json
import pandas as pd
from smart_trade_finder import SmartTradeFinder
from datetime import datetime, timedelta

print("\n🎯 Regenerating optimal trades from ALL historical data...")

# Calculate how many hours of data we have
df = pd.read_csv('trading_data/ema_data_5min.csv', on_bad_lines='skip')
df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
df = df.dropna(subset=['timestamp'])
oldest = df['timestamp'].min()
newest = df['timestamp'].max()
hours_span = int((newest - oldest).total_seconds() / 3600)

print(f"📊 Data span: {hours_span} hours ({oldest} to {newest})")

# Find all trades in entire history
finder = SmartTradeFinder(ema_5min_file='trading_data/ema_data_5min.csv')
results = finder.find_smart_trades(hours_back=hours_span)

# Save to optimal_trades.json
with open('trading_data/optimal_trades.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)

total_trades = results.get('total_trades', 0)
total_pnl = results.get('total_pnl_pct', 0)

print(f"✅ Found {total_trades} optimal trades")
print(f"💰 Total PnL: {total_pnl:+.2f}%")
print(f"📁 Saved to: trading_data/optimal_trades.json\n")
