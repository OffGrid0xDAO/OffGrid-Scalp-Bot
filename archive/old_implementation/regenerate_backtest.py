#!/usr/bin/env python3
"""
Regenerate backtest with current trading rules
"""

import json
from run_backtest import run_backtest
import pandas as pd

print("\n🎯 Regenerating backtest with current trading rules...")

# Calculate total hours available
df = pd.read_csv('trading_data/ema_data_5min.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
hours_span = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600

# Use a very large number to ensure we get ALL data (not filtered by "last N hours from now")
hours_back = 1000  # Will include all data since it goes back further than data exists

print(f"📊 Running backtest on ALL historical data ({hours_span:.1f} hours)...")

# Run backtest on all available data
backtest_results = run_backtest(hours_back=hours_back)

# Save results
with open('trading_data/backtest_trades.json', 'w') as f:
    json.dump(backtest_results, f, indent=2, default=str)

total_trades = backtest_results.get('total_trades', 0)
total_pnl = backtest_results.get('total_pnl_pct', 0)
win_rate = backtest_results.get('win_rate', 0)
debug = backtest_results.get('debug', {})

print(f"\n✅ Backtest complete!")
print(f"   Total Signals: {debug.get('total_signals', '?')}")
print(f"   Blocked (in position): {debug.get('blocked_by_position', '?')}")
print(f"   Trades Taken: {total_trades}")
print(f"   Win Rate: {win_rate*100:.1f}%")
print(f"   Total PnL: {total_pnl:+.2f}%")
print(f"   📁 Saved to: trading_data/backtest_trades.json\n")
