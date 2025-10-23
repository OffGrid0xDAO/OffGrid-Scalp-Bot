#!/usr/bin/env python3
"""
Backtest Full Month - MTF Strategy

Run the MTF strategy on the full last month (Sept 21 - Oct 21, 2025)
to see how it performs over a longer period.
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent / 'src'))

from strategy.entry_detector_user_pattern import EntryDetector as MTFEntryDetector
from strategy.exit_manager_user_pattern import ExitManager


print("\n" + "="*80)
print("🚀 FULL MONTH BACKTEST - MTF STRATEGY")
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

# Filter to last month (Sept 21 - Oct 21)
start_date = pd.Timestamp('2025-09-21')
end_date = pd.Timestamp('2025-10-22')

df_1h_period = df_1h[(df_1h['timestamp'] >= start_date) & (df_1h['timestamp'] < end_date)].copy()
df_15m_period = df_15m[(df_15m['timestamp'] >= start_date) & (df_15m['timestamp'] < end_date)].copy()
df_5m_period = df_5m[(df_5m['timestamp'] >= start_date) & (df_5m['timestamp'] < end_date)].copy()

print(f"\nPeriod: {start_date.date()} to {end_date.date()} (30 days)")
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
            'peak_profit_pct': 0.0,
            'entry_index': i
        }
        in_position = True

        print(f"\n📍 ENTRY #{len(trades)+1}: {current_trade['direction'].upper()} at ${current_trade['entry_price']:.2f}")
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
            current_trade['exit_index'] = i

            position_size = capital * 0.1
            pnl = position_size * (exit_result['profit_pct'] / 100)
            current_trade['pnl'] = pnl
            capital += pnl

            trades.append(current_trade)

            print(f"🚪 EXIT #{len(trades)}: {current_trade['exit_reason']}")
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
    current_trade['exit_index'] = len(df_signals) - 1

    position_size = capital * 0.1
    pnl = position_size * (profit_pct / 100)
    current_trade['pnl'] = pnl
    capital += pnl

    trades.append(current_trade)

# Calculate statistics
print("\n" + "="*80)
print("📊 FULL MONTH BACKTEST RESULTS")
print("="*80)

if not trades:
    print("\n❌ No trades completed")
    results = {
        'period': {'start': str(start_date), 'end': str(end_date), 'days': 30},
        'trades': [],
        'total_trades': 0,
        'win_rate': 0,
        'total_pnl': 0,
        'return_pct': 0
    }
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
    print(f"  Period: 30 days ({start_date.date()} to {end_date.date()})")
    print(f"  Initial Capital: ${initial_capital:.2f}")
    print(f"  Final Capital: ${capital:.2f}")
    print(f"  Total P&L: ${total_pnl:+.2f}")
    print(f"  Return: {return_pct:+.2f}%")
    print(f"  Annualized Return: {return_pct * 12:+.2f}%")

    print(f"\n📈 Trade Breakdown:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Trades per Week: {total_trades / 4.3:.1f}")
    print(f"  Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"  Losing Trades: {len(losing_trades)} ({100-win_rate:.1f}%)")

    if profits:
        print(f"\n✅ Winning Trades:")
        print(f"  Average Profit: {np.mean(profits):.2f}%")
        print(f"  Largest Win: {max(profits):.2f}%")
        print(f"  Total Wins: ${sum(t['pnl'] for t in winning_trades):+.2f}")

    if losses:
        print(f"\n❌ Losing Trades:")
        print(f"  Average Loss: {np.mean(losses):.2f}%")
        print(f"  Largest Loss: {min(losses):.2f}%")
        print(f"  Total Losses: ${sum(t['pnl'] for t in losing_trades):+.2f}")

    # Profit factor
    if losses:
        profit_factor = abs(sum(t['pnl'] for t in winning_trades)) / abs(sum(t['pnl'] for t in losing_trades))
        print(f"\n📊 Performance Metrics:")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"  Avg Win/Loss Ratio: {abs(np.mean(profits) / np.mean(losses)):.2f}")

    # Exit reasons
    print(f"\n🚪 Exit Reasons:")
    exit_reasons = {}
    for t in trades:
        reason = t['exit_reason'].split(' ')[0]
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count} ({count/total_trades*100:.1f}%)")

    # Save results
    results = {
        'period': {
            'start': str(start_date),
            'end': str(end_date),
            'days': 30
        },
        'capital': {
            'initial': initial_capital,
            'final': capital,
            'pnl': total_pnl,
            'return_pct': return_pct
        },
        'trades': {
            'total': total_trades,
            'winning': len(winning_trades),
            'losing': len(losing_trades),
            'win_rate': win_rate
        },
        'trade_list': trades,
        'signals_df': df_signals.to_dict('records'),
        'generated_at': datetime.now().isoformat()
    }

    results_file = data_dir / 'full_month_backtest_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Results saved to: {results_file}")

print("\n" + "="*80)
print("✅ FULL MONTH BACKTEST COMPLETE!")
print("="*80)
print("\n📊 Next: Generate interactive HTML chart")
print("   Run: python generate_interactive_chart.py")

# Return results for use by chart generator
import pickle
with open(data_dir / 'full_month_results.pkl', 'wb') as f:
    pickle.dump({
        'df_signals': df_signals,
        'trades': trades,
        'results': results
    }, f)
