#!/usr/bin/env python3
"""
Recalculate User's ACTUAL PNL using their exact entry/exit timestamps
Compare to the bot-calculated 4.86%
"""

import pandas as pd
import json
from pathlib import Path
from datetime import timedelta

data_dir = Path(__file__).parent / 'trading_data'

# Load user's trades with entry/exit timestamps
with open(data_dir / 'optimal_trades.json', 'r') as f:
    user_data = json.load(f)
user_trades = user_data['optimal_entries']

# Load 15m price data
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

print("\n" + "="*80)
print("🔍 RECALCULATING USER'S ACTUAL PNL")
print("="*80)

print(f"\n📊 User provided {len(user_trades)} trades with exact entry/exit times")

# Calculate actual PNL
capital = 1000.0
results = []

for i, trade in enumerate(user_trades, 1):
    entry_time = pd.to_datetime(trade['timestamp'])
    exit_time = pd.to_datetime(trade['exit_timestamp'])
    direction = trade['direction']

    # Find entry price (nearest 15m candle)
    tolerance = timedelta(minutes=1)
    entry_candles = df_15m[
        (df_15m['timestamp'] >= entry_time - tolerance) &
        (df_15m['timestamp'] <= entry_time + tolerance)
    ]

    exit_candles = df_15m[
        (df_15m['timestamp'] >= exit_time - tolerance) &
        (df_15m['timestamp'] <= exit_time + tolerance)
    ]

    if len(entry_candles) == 0 or len(exit_candles) == 0:
        print(f"⚠️  Trade #{i}: Skipping - no price data found")
        continue

    entry_price = entry_candles.iloc[0]['close']
    exit_price = exit_candles.iloc[0]['close']

    # Calculate profit
    if direction == 'long':
        profit_pct = (exit_price - entry_price) / entry_price * 100
    else:
        profit_pct = (entry_price - exit_price) / entry_price * 100

    position_size = capital * 0.1
    pnl = position_size * (profit_pct / 100)
    capital += pnl

    results.append({
        'trade_num': i,
        'entry_time': entry_time,
        'exit_time': exit_time,
        'direction': direction,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'profit_pct': profit_pct,
        'pnl': pnl,
        'capital': capital
    })

    emoji = "✅" if profit_pct > 0 else "❌"
    print(f"{emoji} Trade #{i}: {direction.upper()} | Entry: {entry_price:.2f} → Exit: {exit_price:.2f} | {profit_pct:+.2f}% (${pnl:+.2f})")

# Summary
total_pnl = capital - 1000
return_pct = (capital - 1000) / 1000 * 100
winners = [r for r in results if r['profit_pct'] > 0]
losers = [r for r in results if r['profit_pct'] <= 0]
win_rate = len(winners) / len(results) * 100 if results else 0

print("\n" + "="*80)
print("📊 ACTUAL USER PERFORMANCE (Using Your Exact Exits)")
print("="*80)

print(f"\nTotal Trades: {len(results)}")
print(f"Winners: {len(winners)} ({win_rate:.1f}%)")
print(f"Losers: {len(losers)}")
print(f"\nStarting Capital: $1,000.00")
print(f"Final Capital: ${capital:.2f}")
print(f"Total PNL: ${total_pnl:+.2f}")
print(f"Return: {return_pct:+.2f}%")

# Compare to bot-calculated
print("\n" + "="*80)
print("⚖️  COMPARISON")
print("="*80)

with open(data_dir / 'user_trades_profit.json', 'r') as f:
    bot_calc = json.load(f)

print(f"\n{'Metric':<20} {'Your Actual Exits':<20} {'Bot-Calculated':<20} {'Difference'}")
print(f"{'-'*80}")
print(f"{'Total PNL':<20} ${total_pnl:+.2f}{'':<14} ${bot_calc['total_pnl']:+.2f}{'':<12} ${total_pnl - bot_calc['total_pnl']:+.2f}")
print(f"{'Return %':<20} {return_pct:+.2f}%{'':<14} {bot_calc['return_pct']:+.2f}%{'':<13} {return_pct - bot_calc['return_pct']:+.2f}%")
print(f"{'Win Rate':<20} {win_rate:.1f}%{'':<14} {bot_calc['win_rate']:.1f}%{'':<13} {win_rate - bot_calc['win_rate']:+.1f}%")

if total_pnl > bot_calc['total_pnl']:
    diff = total_pnl - bot_calc['total_pnl']
    print(f"\n✅ Your ACTUAL exits were BETTER by ${diff:+.2f} ({(diff/bot_calc['total_pnl']*100):+.1f}%)")
    print(f"   The bot exit manager LEFT MONEY ON THE TABLE!")
else:
    diff = bot_calc['total_pnl'] - total_pnl
    print(f"\n❌ Bot exit manager was better by ${diff:+.2f}")
    print(f"   Your actual exits gave back some profit")

# Save corrected data
corrected_data = {
    'total_trades': len(results),
    'win_rate': win_rate,
    'total_pnl': total_pnl,
    'return_pct': return_pct,
    'final_capital': capital,
    'trades': results
}

with open(data_dir / 'user_trades_ACTUAL_exits.json', 'w') as f:
    json.dump(corrected_data, f, indent=2, default=str)

print(f"\n💾 Corrected data saved to: user_trades_ACTUAL_exits.json")
print("="*80 + "\n")
