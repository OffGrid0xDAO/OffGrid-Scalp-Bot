#!/usr/bin/env python3
"""
ITERATION 11: ML-LEARNED EXIT STRATEGY
Goal: Match user's +4.86% return using EXACT exit parameters learned from user's 22 trades

Changes from Iteration 10 (+2.19%, 45% capture):
1. Take Profit: 5.0% → 2.5% (user's median)
2. Stop Loss: 0.75% → 0.6% (user's median)
3. Trailing Width: 1.5-2.5% → 0.9% (user's median)
4. Profit Lock: 1.5% → 0.7% (user's pattern)

SAME entry filters as Iteration 10 (quality=50, vol_ratio=1.0)

Expected: Same ~39 trades, but better exits → 60-80% capture, 3-4% return
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'src'))
from strategy.entry_detector_user_pattern import EntryDetector
from strategy.exit_manager_user_learned import ExitManager  # ML-LEARNED!

print("\n" + "="*80)
print("🚀 ITERATION 11: ML-LEARNED EXIT STRATEGY (15m Timeframe)")
print("="*80)

# Load data
data_dir = Path(__file__).parent / 'trading_data'
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')

for df in [df_15m, df_5m]:
    df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter to USER's exact period (Oct 5-21, 2025)
start_date = pd.Timestamp('2025-10-05')
end_date = pd.Timestamp('2025-10-22')

df_15m_period = df_15m[(df_15m['timestamp'] >= start_date) & (df_15m['timestamp'] < end_date)].copy()
df_5m_period = df_5m[(df_5m['timestamp'] >= start_date) & (df_5m['timestamp'] < end_date)].copy()

print(f"\n📅 Period: {start_date.date()} to {end_date.date()} (17 days)")

# Load user's trades for comparison
with open(data_dir / 'user_trades_profit.json', 'r') as f:
    user_data = json.load(f)

print(f"\n👤 USER BENCHMARK:")
print(f"   22 trades | 90.9% WR | +4.86% return | $1048.61")

print(f"\n⚙️  ITERATION 11 EXIT SETTINGS (ML-LEARNED FROM USER):")
print(f"   Take Profit: 2.5% (was 5.0%) - User's median TP")
print(f"   Stop Loss: 0.6% (was 0.75%) - User's median loss")
print(f"   Trailing: 0.9% (was 1.5-2.5%) - User's median giveback")
print(f"   Profit Lock: 0.7% (was 1.5%) - User's reversal threshold")

print(f"\n⚙️  ENTRY SETTINGS (Same as Iteration 10):")
print(f"   Quality Score: ≥50")
print(f"   Volume Ratio: ≥1.0")
print(f"   Confluence: ≥15")

# Run backtest
print("\n" + "="*80)
print("🤖 RUNNING ITERATION 11 BACKTEST")
print("="*80)

detector = EntryDetector(df_5m=df_5m_period, df_15m=df_15m_period)
df_signals = detector.scan_historical_signals(df_15m_period)

exit_manager = ExitManager()  # ML-LEARNED exit manager!
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

print(f"\n📊 ITERATION 11 RESULTS:")
print(f"   Trades: {total_trades}")
print(f"   Wins/Losses: {len(winning_trades)}/{len(losing_trades)}")
print(f"   Win Rate: {win_rate:.1f}%")
print(f"   Return: {return_pct:+.2f}%")
print(f"   Final Capital: ${capital:.2f}")
print(f"   P&L: ${capital - initial_capital:+.2f}")

# Detailed stats
if len(winning_trades) > 0:
    avg_win = np.mean([t['profit_pct'] for t in winning_trades])
    max_win = np.max([t['profit_pct'] for t in winning_trades])
    print(f"\n📈 Winning Trades:")
    print(f"   Avg Win: {avg_win:.2f}%")
    print(f"   Max Win: {max_win:.2f}%")

if len(losing_trades) > 0:
    avg_loss = np.mean([t['profit_pct'] for t in losing_trades])
    max_loss = np.min([t['profit_pct'] for t in losing_trades])
    print(f"\n📉 Losing Trades:")
    print(f"   Avg Loss: {avg_loss:.2f}%")
    print(f"   Max Loss: {max_loss:.2f}%")

# Comparison
print("\n" + "="*80)
print("⚖️  COMPARISON vs USER")
print("="*80)

capture_pct = (capital - initial_capital) / 48.61 * 100

print(f"\n{'Metric':<20} {'Bot':<15} {'User':<15} {'Gap':<15} {'Status'}")
print(f"{'-'*75}")
print(f"{'Trades':<20} {total_trades:<15} {22:<15} {total_trades - 22:<15} {'✅' if abs(total_trades - 22) <= 5 else '⚠️'}")
print(f"{'Win Rate':<20} {win_rate:.1f}%{'':<10} {'90.9%':<15} {win_rate - 90.9:+.1f}%{'':<7} {'✅' if win_rate >= 70 else '⚠️' if win_rate >= 50 else '❌'}")
print(f"{'Return':<20} {return_pct:+.2f}%{'':<10} {'+4.86%':<15} {return_pct - 4.86:+.2f}%{'':<7} {'✅' if return_pct >= 4.0 else '⚠️' if return_pct >= 2.5 else '❌'}")
print(f"{'Avg Win':<20} {avg_win:.2f}%{'':<10} {'2.44%':<15} {avg_win - 2.44:+.2f}%{'':<7} {'✅' if avg_win >= 2.3 else '⚠️'}")
print(f"{'Avg Loss':<20} {avg_loss:.2f}%{'':<10} {'-0.60%':<15} {avg_loss + 0.60:+.2f}%{'':<7} {'✅' if avg_loss >= -0.65 else '⚠️'}")

print(f"\n🎯 Profit Capture: {capture_pct:.1f}%")

if capture_pct >= 80:
    print("   🎉 80%+ EXCELLENT! Matched user performance!")
    emoji = "🎉"
elif capture_pct >= 60:
    print("   ✅ 60-80% GREAT! Very close to user")
    emoji = "✅"
elif capture_pct >= 45:
    print("   ⚠️  45-60% GOOD PROGRESS")
    emoji = "👍"
else:
    print("   ❌ <45% - more work needed")
    emoji = "🔍"

# Compare iterations
print("\n" + "="*80)
print("📊 ALL ITERATIONS COMPARISON")
print("="*80)

print(f"\n{'Iteration':<25} {'Trades':<8} {'WR':<8} {'Return':<10} {'Capture'}")
print(f"{'-'*70}")
print(f"{'Focused 15m':<25} {39:<8} {'41.0%':<8} {'+1.66%':<10} {'34.2%'}")
print(f"{'Iteration 10 (tighter)':<25} {39:<8} {'41.0%':<8} {'+2.19%':<10} {'45.0%'}")
print(f"{'ITERATION 11 (ML exits)':<25} {total_trades:<8} {f'{win_rate:.1f}%':<8} {f'{return_pct:+.2f}%':<10} {f'{capture_pct:.1f}%'}")

# Improvement
iter10_return = 2.19
iter10_capture = 45.0
improvement_return = return_pct - iter10_return
improvement_capture = capture_pct - iter10_capture

print(f"\n{emoji} ITERATION 11 vs Iteration 10:")
print(f"   Return: {return_pct:+.2f}% vs +2.19% ({improvement_return:+.2f} pts)")
print(f"   Capture: {capture_pct:.1f}% vs 45.0% ({improvement_capture:+.1f} pts)")

if improvement_capture > 0:
    print(f"   ✅ EXIT OPTIMIZATION WORKED!")
else:
    print(f"   ⚠️  Need further tuning")

# Show all trades
print("\n" + "="*80)
print(f"📋 ALL {total_trades} TRADES")
print("="*80)

for i, trade in enumerate(trades, 1):
    emoji_trade = "✅" if trade['profit_pct'] > 0 else "❌"
    print(f"\n{emoji_trade} #{i}: {trade['direction'].upper()} @ {trade['entry_time']}")
    print(f"   Exit: {trade['exit_time']} | {trade['profit_pct']:+.2f}% (${trade['pnl']:+.2f})")
    print(f"   Peak: {trade['peak_profit_pct']:+.2f}% | {trade['exit_reason']}")

# Assessment
print("\n" + "="*80)
print("💡 FINAL ASSESSMENT")
print("="*80)

if return_pct >= 4.0:
    print(f"\n🎉 SUCCESS! Hit 4%+ target!")
    print(f"   Iteration 11: {return_pct:+.2f}% return ({capture_pct:.1f}% capture)")
    print(f"   ML-learned exits are WORKING!")
elif return_pct >= 3.0:
    print(f"\n✅ VERY CLOSE! {return_pct:+.2f}% ({capture_pct:.1f}% capture)")
    print(f"   Gap to 4.86%: {4.86 - return_pct:.2f}%")
    print(f"   Likely need better ENTRY selection (match user's 22 trades)")
elif return_pct > iter10_return:
    print(f"\n👍 IMPROVED! From +{iter10_return}% to {return_pct:+.2f}%")
    print(f"   ML exits helped! Keep optimizing.")
else:
    print(f"\n⚠️  Same/worse than Iteration 10")
    print(f"   May need to re-tune entry filters")

print("\n" + "="*80)

# Save results
results_data = {
    'iteration': 11,
    'description': 'ML-learned exit strategy from user trades',
    'exit_params': {
        'take_profit': 2.5,
        'stop_loss': 0.6,
        'trailing_width': 0.9,
        'profit_lock': 0.7
    },
    'results': {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'return_pct': return_pct,
        'final_capital': capital,
        'profit_capture_pct': capture_pct,
        'avg_win': avg_win if len(winning_trades) > 0 else 0,
        'avg_loss': avg_loss if len(losing_trades) > 0 else 0
    },
    'trades': trades
}

output_file = data_dir / 'iteration_11_results.json'
with open(output_file, 'w') as f:
    json.dump(results_data, f, indent=2, default=str)

print(f"💾 Results saved to: {output_file}\n")
