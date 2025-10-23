#!/usr/bin/env python3
"""
Focused Backtest on 15-MINUTE Timeframe
Period: Oct 5-21 (17 days where user made 22 trades)
Goal: Match user's +4.86% return by operating on same timeframe
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'src'))
from strategy.entry_detector_user_pattern import EntryDetector
from strategy.exit_manager_user_pattern import ExitManager

print("\n" + "="*80)
print("🎯 FOCUSED BACKTEST: 15-MINUTE TIMEFRAME")
print("="*80)

# Load data
data_dir = Path(__file__).parent / 'trading_data'
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')

for df in [df_15m, df_5m]:
    df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter to USER's exact period (Oct 5-21, 2025 - 17 days)
start_date = pd.Timestamp('2025-10-05')
end_date = pd.Timestamp('2025-10-22')  # Inclusive of Oct 21

df_15m_period = df_15m[(df_15m['timestamp'] >= start_date) & (df_15m['timestamp'] < end_date)].copy()
df_5m_period = df_5m[(df_5m['timestamp'] >= start_date) & (df_5m['timestamp'] < end_date)].copy()

print(f"\n📅 Period: {start_date.date()} to {end_date.date()} (17 days)")
print(f"   15m: {len(df_15m_period)} candles (PRIMARY TIMEFRAME)")
print(f"   5m:  {len(df_5m_period)} candles (for MTF confirmation)")

# Load user's trades for comparison
with open(data_dir / 'optimal_trades.json', 'r') as f:
    user_data = json.load(f)
user_trades = user_data['optimal_entries']

print(f"\n👤 USER BENCHMARK:")
print(f"   22 trades")
print(f"   90.9% win rate (20 wins, 2 losses)")
print(f"   +4.86% return ($1000 → $1048.61)")

# Run bot backtest on 15m timeframe
print("\n" + "="*80)
print("🤖 RUNNING BOT BACKTEST ON 15-MINUTE TIMEFRAME")
print("="*80)

# Use EntryDetector with 15m as PRIMARY timeframe, 5m for confirmation
detector = EntryDetector(df_5m=df_5m_period, df_15m=df_15m_period)

# Scan 15m dataframe (not 1h!)
df_signals = detector.scan_historical_signals(df_15m_period)

exit_manager = ExitManager()
initial_capital = 1000.0
capital = initial_capital
trades = []

in_position = False
current_trade = None

for i in range(len(df_signals)):
    row = df_signals.iloc[i]

    if not in_position and row['entry_signal']:
        current_trade = {
            'entry_time': row['timestamp'],
            'entry_price': row['close'],
            'direction': row['entry_direction'],
            'quality_score': row.get('entry_quality_score', 0),
            'peak_profit_pct': 0.0,
            'entry_index': i
        }
        in_position = True

    elif in_position and current_trade:
        if current_trade['direction'] == 'long':
            profit_pct = (row['close'] - current_trade['entry_price']) / current_trade['entry_price'] * 100
        else:
            profit_pct = (current_trade['entry_price'] - row['close']) / current_trade['entry_price'] * 100

        current_trade['peak_profit_pct'] = max(current_trade['peak_profit_pct'], profit_pct)

        exit_result = exit_manager.check_exit(
            current_trade['entry_price'],
            current_trade['entry_time'],
            row['close'],
            row['timestamp'],
            current_trade['direction'],
            current_trade['peak_profit_pct']
        )

        if exit_result['should_exit']:
            current_trade['exit_time'] = row['timestamp']
            current_trade['exit_price'] = exit_result['exit_price']
            current_trade['profit_pct'] = exit_result['profit_pct']
            current_trade['exit_reason'] = exit_result['exit_reason']

            position_size = capital * 0.1
            pnl = position_size * (exit_result['profit_pct'] / 100)
            current_trade['pnl'] = pnl
            capital += pnl

            trades.append(current_trade)
            in_position = False
            current_trade = None

# Close any open position
if in_position and current_trade:
    last_row = df_signals.iloc[-1]
    if current_trade['direction'] == 'long':
        profit_pct = (last_row['close'] - current_trade['entry_price']) / current_trade['entry_price'] * 100
    else:
        profit_pct = (current_trade['entry_price'] - last_row['close']) / current_trade['entry_price'] * 100

    current_trade['exit_time'] = last_row['timestamp']
    current_trade['exit_price'] = last_row['close']
    current_trade['profit_pct'] = profit_pct
    current_trade['exit_reason'] = 'End of period'
    position_size = capital * 0.1
    pnl = position_size * (profit_pct / 100)
    current_trade['pnl'] = pnl
    capital += pnl
    trades.append(current_trade)

# Results
total_trades = len(trades)
winning_trades = [t for t in trades if t['profit_pct'] > 0]
losing_trades = [t for t in trades if t['profit_pct'] <= 0]
win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
return_pct = (capital - initial_capital) / initial_capital * 100

print(f"\n📊 BOT RESULTS (15-MINUTE TIMEFRAME):")
print(f"   Trades: {total_trades}")
print(f"   Win Rate: {win_rate:.1f}%")
print(f"   Return: {return_pct:+.2f}%")
print(f"   Final Capital: ${capital:.2f}")
print(f"   P&L: ${capital - initial_capital:+.2f}")

# Comparison
print("\n" + "="*80)
print("⚖️  COMPARISON")
print("="*80)

print(f"\n{'Metric':<20} {'Bot':<15} {'User':<15} {'Gap':<15}")
print(f"{'-'*65}")
print(f"{'Trades':<20} {total_trades:<15} {22:<15} {total_trades - 22:<15}")
print(f"{'Win Rate':<20} {win_rate:.1f}%{'':<10} {'90.9%':<15} {win_rate - 90.9:+.1f}%")
print(f"{'Return':<20} {return_pct:+.2f}%{'':<10} {'+4.86%':<15} {return_pct - 4.86:+.2f}%")
print(f"{'Capital':<20} ${capital:.2f}{'':<8} {'$1048.61':<15} ${capital - 1048.61:+.2f}")

capture_pct = (capital - initial_capital) / 48.61 * 100
print(f"\n🎯 Profit Capture: {capture_pct:.1f}%")

if capture_pct < 50:
    print("   ❌ Below 50% capture - still room for improvement")
elif capture_pct < 80:
    print("   ⚠️  50-80% capture - getting closer!")
else:
    print("   ✅ 80%+ capture - EXCELLENT!")

# Analyze the gap
print("\n" + "="*80)
print("🔍 GAP ANALYSIS")
print("="*80)

if total_trades < 22:
    print(f"\n❌ Bot found FEWER trades ({total_trades} vs 22)")
    print(f"   Missing {22 - total_trades} user trades")
    print(f"   → Filters too strict!")
elif total_trades > 22:
    print(f"\n⚠️  Bot found MORE trades ({total_trades} vs 22)")
    print(f"   {total_trades - 22} extra trades")
    print(f"   → Taking false signals")

if win_rate < 90:
    print(f"\n❌ Win rate gap: {win_rate:.1f}% vs 90.9%")
    print(f"   Losing {90.9 - win_rate:.1f} percentage points")
    print(f"   → Quality filter needed")

if len(winning_trades) > 0:
    avg_win = np.mean([t['profit_pct'] for t in winning_trades])
    print(f"\n📈 Bot avg win: {avg_win:.2f}%")
    print(f"   User avg win: 2.36%")
    if avg_win < 2.36:
        print(f"   → Bot exiting winners too early ({avg_win:.2f}% vs 2.36%)")

if len(losing_trades) > 0:
    avg_loss = np.mean([t['profit_pct'] for t in losing_trades])
    print(f"\n📉 Bot avg loss: {avg_loss:.2f}%")
    print(f"   User avg loss: -0.56%")
    if avg_loss < -0.56:
        print(f"   → Bot letting losers run too long ({avg_loss:.2f}% vs -0.56%)")

# Show summary of trades
print("\n" + "="*80)
print(f"📋 BOT'S TRADES SUMMARY (Showing first 10 and last 5)")
print("="*80)

for i, trade in enumerate(trades[:10], 1):
    emoji = "✅" if trade['profit_pct'] > 0 else "❌"
    print(f"{emoji} #{i}: {trade['direction'].upper()} @ {trade['entry_time']} → {trade['exit_time']}")
    print(f"   {trade['profit_pct']:+.2f}% (${trade['pnl']:+.2f}) - {trade['exit_reason']}")

if len(trades) > 15:
    print("\n   ...")
    for i, trade in enumerate(trades[-5:], len(trades)-4):
        emoji = "✅" if trade['profit_pct'] > 0 else "❌"
        print(f"{emoji} #{i}: {trade['direction'].upper()} @ {trade['entry_time']} → {trade['exit_time']}")
        print(f"   {trade['profit_pct']:+.2f}% (${trade['pnl']:+.2f}) - {trade['exit_reason']}")

print("\n" + "="*80)
print("💡 ASSESSMENT")
print("="*80)

if capture_pct > 50:
    print("\n🎉 SUCCESS! 15-minute timeframe significantly improved profit capture!")
    print(f"   {capture_pct:.1f}% capture vs previous 16-32% on 1h timeframe")
else:
    print("\n⚠️  15-minute timeframe didn't solve the issue. Need different approach:")
    print(f"   Current capture: {capture_pct:.1f}%")

print("\n" + "="*80)
