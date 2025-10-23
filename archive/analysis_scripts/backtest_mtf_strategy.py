#!/usr/bin/env python3
"""
Backtest Strategy with Multi-Timeframe Confirmation

Tests the refined strategy with 5m and 15m confirmation added.
Compares:
1. Refined strategy WITHOUT MTF (13 trades, 53.8% win rate)
2. Refined strategy WITH MTF (should reduce false signals further)
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'src'))

from strategy.entry_detector_user_pattern import EntryDetector as MTFEntryDetector
from strategy.exit_manager_user_pattern import ExitManager


print("\n" + "="*80)
print("🚀 BACKTEST WITH MULTI-TIMEFRAME CONFIRMATION")
print("="*80)

# Load data
data_dir = Path(__file__).parent / 'trading_data'

print("\n📊 Loading data...")
df_1h = pd.read_csv(data_dir / 'indicators' / 'eth_1h_full.csv')
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')

df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])

print(f"   1h:  {len(df_1h)} candles ({df_1h['timestamp'].min()} to {df_1h['timestamp'].max()})")
print(f"   15m: {len(df_15m)} candles ({df_15m['timestamp'].min()} to {df_15m['timestamp'].max()})")
print(f"   5m:  {len(df_5m)} candles ({df_5m['timestamp'].min()} to {df_5m['timestamp'].max()})")

# Filter to test period (Oct 5-21)
start_date = pd.Timestamp('2025-10-05')
end_date = pd.Timestamp('2025-10-22')

df_1h_period = df_1h[(df_1h['timestamp'] >= start_date) & (df_1h['timestamp'] < end_date)].copy()
df_15m_period = df_15m[(df_15m['timestamp'] >= start_date) & (df_15m['timestamp'] < end_date)].copy()
df_5m_period = df_5m[(df_5m['timestamp'] >= start_date) & (df_5m['timestamp'] < end_date)].copy()

print(f"\nFiltered to period: {start_date} to {end_date}")
print(f"   1h:  {len(df_1h_period)} candles")
print(f"   15m: {len(df_15m_period)} candles")
print(f"   5m:  {len(df_5m_period)} candles")

# Initialize MTF detector
print("\n🔧 Initializing MTF Entry Detector...")
detector_mtf = MTFEntryDetector(df_5m=df_5m_period, df_15m=df_15m_period)

# Scan for signals
print("\n" + "="*80)
print("📡 SCANNING FOR SIGNALS WITH MTF CONFIRMATION")
print("="*80)

df_signals = detector_mtf.scan_historical_signals(df_1h_period)

# Run backtest
print("\n" + "="*80)
print("📈 RUNNING BACKTEST")
print("="*80)

exit_manager = ExitManager()
initial_capital = 1000.0
capital = initial_capital
trades = []

in_position = False
current_trade = None

for i in range(len(df_signals)):
    row = df_signals.iloc[i]

    # Check for entry
    if not in_position and row['entry_signal']:
        current_trade = {
            'entry_time': row['timestamp'],
            'entry_price': row['close'],
            'direction': row['entry_direction'],
            'quality_score': row.get('entry_quality_score', 0),
            'peak_profit_pct': 0.0
        }
        in_position = True

        print(f"\n📍 ENTRY: {current_trade['direction'].upper()} at ${current_trade['entry_price']:.2f}")
        print(f"   Time: {current_trade['entry_time']}")
        print(f"   Quality: {current_trade['quality_score']:.1f}")

    # Check for exit
    elif in_position and current_trade:
        # Update peak profit
        if current_trade['direction'] == 'long':
            profit_pct = (row['close'] - current_trade['entry_price']) / current_trade['entry_price'] * 100
        else:
            profit_pct = (current_trade['entry_price'] - row['close']) / current_trade['entry_price'] * 100

        current_trade['peak_profit_pct'] = max(current_trade['peak_profit_pct'], profit_pct)

        # Check exit
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

            print(f"🚪 EXIT: {current_trade['exit_reason']}")
            print(f"   Profit: {current_trade['profit_pct']:+.2f}%")
            print(f"   P&L: ${pnl:+.2f}")
            print(f"   Capital: ${capital:.2f}")

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
    current_trade['exit_reason'] = 'End of backtest'

    position_size = capital * 0.1
    pnl = position_size * (profit_pct / 100)
    current_trade['pnl'] = pnl
    capital += pnl

    trades.append(current_trade)

# Calculate statistics
print("\n" + "="*80)
print("📊 BACKTEST RESULTS WITH MTF")
print("="*80)

if not trades:
    print("\n❌ No trades completed")
else:
    total_trades = len(trades)
    winning_trades = [t for t in trades if t['profit_pct'] > 0]
    losing_trades = [t for t in trades if t['profit_pct'] <= 0]

    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    profits = [t['profit_pct'] for t in winning_trades]
    losses = [t['profit_pct'] for t in losing_trades]
    total_pnl = sum(t['pnl'] for t in trades)
    return_pct = (capital - initial_capital) / initial_capital * 100

    print(f"\n💼 Trading Statistics:")
    print(f"  Initial Capital: ${initial_capital:.2f}")
    print(f"  Final Capital: ${capital:.2f}")
    print(f"  Total P&L: ${total_pnl:+.2f}")
    print(f"  Return: {return_pct:+.2f}%")

    print(f"\n📈 Trade Breakdown:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"  Losing Trades: {len(losing_trades)} ({100-win_rate:.1f}%)")

    if profits:
        print(f"\n✅ Winning Trades:")
        print(f"  Average Profit: {np.mean(profits):.2f}%")
        print(f"  Largest Win: {max(profits):.2f}%")

    if losses:
        print(f"\n❌ Losing Trades:")
        print(f"  Average Loss: {np.mean(losses):.2f}%")
        print(f"  Largest Loss: {min(losses):.2f}%")

    # Comparison
    print("\n" + "="*80)
    print("🔄 COMPARISON: WITHOUT MTF vs WITH MTF")
    print("="*80)

    print(f"\n{'Metric':<25} {'Without MTF':<20} {'With MTF':<20} {'Change':<15}")
    print("-" * 80)

    # Previous results (without MTF)
    no_mtf_trades = 13
    no_mtf_wr = 53.8
    no_mtf_return = 0.55
    no_mtf_pnl = 5.47

    print(f"{'Total Trades':<25} {no_mtf_trades:<20} {total_trades:<20} {total_trades - no_mtf_trades:+d}")
    print(f"{'Win Rate':<25} {no_mtf_wr:<20.1f}% {win_rate:<20.1f}% {win_rate - no_mtf_wr:+.1f}%")
    print(f"{'Return %':<25} {no_mtf_return:<20.2f}% {return_pct:<20.2f}% {return_pct - no_mtf_return:+.2f}%")
    print(f"{'Total P&L':<25} ${no_mtf_pnl:<19.2f} ${total_pnl:<19.2f} ${total_pnl - no_mtf_pnl:+.2f}")

    if win_rate > no_mtf_wr:
        print(f"\n✅ MTF IMPROVED win rate by {win_rate - no_mtf_wr:.1f}%")
    elif win_rate < no_mtf_wr:
        print(f"\n⚠️  MTF REDUCED win rate by {no_mtf_wr - win_rate:.1f}%")

    if return_pct > no_mtf_return:
        print(f"✅ MTF IMPROVED return by {return_pct - no_mtf_return:.2f}%")
    elif return_pct < no_mtf_return:
        print(f"⚠️  MTF REDUCED return by {no_mtf_return - return_pct:.2f}%")

    if total_trades < no_mtf_trades:
        print(f"✅ MTF REDUCED trades by {no_mtf_trades - total_trades} (more selective)")
    elif total_trades > no_mtf_trades:
        print(f"⚠️  MTF INCREASED trades by {total_trades - no_mtf_trades}")

    # Compare to user's trades
    print("\n" + "="*80)
    print("👤 COMPARISON: MTF BOT vs USER TRADES")
    print("="*80)

    user_trades = 22
    user_wr = 90.9
    user_return = 4.86
    user_pnl = 48.61

    print(f"\n{'Metric':<25} {'MTF Bot':<20} {'User':<20} {'Gap':<15}")
    print("-" * 80)
    print(f"{'Total Trades':<25} {total_trades:<20} {user_trades:<20} {user_trades - total_trades:+d}")
    print(f"{'Win Rate':<25} {win_rate:<20.1f}% {user_wr:<20.1f}% {user_wr - win_rate:+.1f}%")
    print(f"{'Return %':<25} {return_pct:<20.2f}% {user_return:<20.2f}% {user_return - return_pct:+.2f}%")
    print(f"{'Total P&L':<25} ${total_pnl:<19.2f} ${user_pnl:<19.2f} ${user_pnl - total_pnl:+.2f}")

    catch_rate = (total_trades / user_trades) * 100
    profit_capture = (total_pnl / user_pnl) * 100

    print(f"\n📊 Capture Rates:")
    print(f"  Trade Capture: {catch_rate:.1f}% of user trades")
    print(f"  Profit Capture: {profit_capture:.1f}% of user profit")

print("\n" + "="*80)
print("✅ MTF BACKTEST COMPLETE!")
print("="*80)
