#!/usr/bin/env python3
"""
ITERATION 10: Aggressive Improvements on 15m Timeframe
Goal: Hit 4-5% return to match user's performance

Changes from previous (15m, 1.66% return, 34.2% capture):
1. Stop loss: 1.0% → 0.75% (match user's -0.56% avg loss)
2. Profit lock: NEW - Don't let +1.5% winners become losers
3. Quality score: 20 → 50 (only best setups)
4. Volume ratio: 0.5 → 1.0 (elevated/spike preferred)
5. Confluence min: 10 → 15 (higher quality)
6. Volume req: Remove "low" (skip low volume)

Expected: 25-30 trades, 55-65% WR, +2.5-3.5% return, 50-70% capture
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
print("🚀 ITERATION 10: AGGRESSIVE IMPROVEMENTS (15m Timeframe)")
print("="*80)

# Load data
data_dir = Path(__file__).parent / 'trading_data'
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')

for df in [df_15m, df_5m]:
    df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter to USER's exact period (Oct 5-21, 2025 - 17 days)
start_date = pd.Timestamp('2025-10-05')
end_date = pd.Timestamp('2025-10-22')

df_15m_period = df_15m[(df_15m['timestamp'] >= start_date) & (df_15m['timestamp'] < end_date)].copy()
df_5m_period = df_5m[(df_5m['timestamp'] >= start_date) & (df_5m['timestamp'] < end_date)].copy()

print(f"\n📅 Period: {start_date.date()} to {end_date.date()} (17 days)")
print(f"   15m: {len(df_15m_period)} candles (PRIMARY TIMEFRAME)")
print(f"   5m:  {len(df_5m_period)} candles (MTF confirmation)")

# Load user's trades for comparison
with open(data_dir / 'optimal_trades.json', 'r') as f:
    user_data = json.load(f)
user_trades = user_data['optimal_entries']

print(f"\n👤 USER BENCHMARK:")
print(f"   22 trades | 90.9% win rate | +4.86% return | $1048.61")

print(f"\n⚙️  ITERATION 10 SETTINGS:")
print(f"   Stop Loss: 0.75% (was 1.0%)")
print(f"   Profit Lock: +1.5% peak → exit if goes negative")
print(f"   Quality Score: ≥50 (was 20)")
print(f"   Volume Ratio: ≥1.0 (was 0.5)")
print(f"   Confluence: ≥15 (was 10)")
print(f"   Volume Types: spike/elevated/normal only (removed 'low')")

# Run bot backtest on 15m timeframe
print("\n" + "="*80)
print("🤖 RUNNING ITERATION 10 BACKTEST")
print("="*80)

detector = EntryDetector(df_5m=df_5m_period, df_15m=df_15m_period)
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

print(f"\n📊 ITERATION 10 RESULTS:")
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

print(f"\n{'Metric':<20} {'Bot':<15} {'User':<15} {'Gap':<15} {'Status'}")
print(f"{'-'*75}")
print(f"{'Trades':<20} {total_trades:<15} {22:<15} {total_trades - 22:<15} {'✅' if abs(total_trades - 22) <= 5 else '⚠️'}")
print(f"{'Win Rate':<20} {win_rate:.1f}%{'':<10} {'90.9%':<15} {win_rate - 90.9:+.1f}%{'':<7} {'✅' if win_rate >= 70 else '⚠️' if win_rate >= 50 else '❌'}")
print(f"{'Return':<20} {return_pct:+.2f}%{'':<10} {'+4.86%':<15} {return_pct - 4.86:+.2f}%{'':<7} {'✅' if return_pct >= 4.0 else '⚠️' if return_pct >= 2.5 else '❌'}")
print(f"{'Capital':<20} ${capital:.2f}{'':<8} {'$1048.61':<15} ${capital - 1048.61:+.2f}{'':<4} {'✅' if capital >= 1040 else '⚠️' if capital >= 1025 else '❌'}")

capture_pct = (capital - initial_capital) / 48.61 * 100
print(f"\n🎯 Profit Capture: {capture_pct:.1f}%")

if capture_pct >= 80:
    print("   ✅ 80%+ EXCELLENT! Close to user performance!")
    emoji = "🎉"
elif capture_pct >= 60:
    print("   ⚠️  60-80% GOOD! Getting closer")
    emoji = "👍"
elif capture_pct >= 40:
    print("   ⚠️  40-60% PROGRESS - need more refinement")
    emoji = "📈"
else:
    print("   ❌ <40% - need different approach")
    emoji = "🔍"

# Compare to previous iterations
print("\n" + "="*80)
print("📊 ITERATION COMPARISON")
print("="*80)

print(f"\n{'Iteration':<20} {'Timeframe':<12} {'Trades':<8} {'WR':<8} {'Return':<10} {'Capture'}")
print(f"{'-'*75}")
print(f"{'Baseline (Sep 21-Oct 22)':<20} {'1h':<12} {6:<8} {'83.3%':<8} {'+1.24%':<10} {'25.5%'}")
print(f"{'Iteration 5 (full)':<20} {'1h':<12} {49:<8} {'51.0%':<8} {'+1.54%':<10} {'31.7%'}")
print(f"{'Focused (tight)':<20} {'1h':<12} {12:<8} {'66.7%':<8} {'+0.82%':<10} {'16.8%'}")
print(f"{'Focused (loose)':<20} {'1h':<12} {26:<8} {'34.6%':<8} {'+0.78%':<10} {'16.0%'}")
print(f"{'Focused 15m':<20} {'15m':<12} {39:<8} {'41.0%':<8} {'+1.66%':<10} {'34.2%'}")
print(f"{'ITERATION 10':<20} {'15m':<12} {total_trades:<8} {f'{win_rate:.1f}%':<8} {f'{return_pct:+.2f}%':<10} {f'{capture_pct:.1f}%'}")

# Improvement analysis
prev_return = 1.66
prev_capture = 34.2
improvement_return = ((return_pct - prev_return) / prev_return * 100) if prev_return > 0 else 0
improvement_capture = capture_pct - prev_capture

print(f"\n{emoji} ITERATION 10 vs Previous (15m, +1.66%, 34.2%):")
print(f"   Return: {return_pct:+.2f}% vs +1.66% ({improvement_return:+.1f}% change)")
print(f"   Capture: {capture_pct:.1f}% vs 34.2% ({improvement_capture:+.1f} pts)")

# Show trades
print("\n" + "="*80)
print("📋 ITERATION 10 TRADES")
print("="*80)

for i, trade in enumerate(trades, 1):
    emoji_trade = "✅" if trade['profit_pct'] > 0 else "❌"
    print(f"\n{emoji_trade} Trade #{i}: {trade['direction'].upper()}")
    print(f"   Entry: {trade['entry_time']} @ ${trade['entry_price']:.2f} (Q={trade['quality_score']:.0f})")
    print(f"   Exit:  {trade['exit_time']} @ ${trade['exit_price']:.2f}")
    print(f"   Result: {trade['profit_pct']:+.2f}% (${trade['pnl']:+.2f})")
    print(f"   Peak: {trade['peak_profit_pct']:+.2f}% | Reason: {trade['exit_reason']}")

print("\n" + "="*80)
print("💡 ASSESSMENT")
print("="*80)

if return_pct >= 4.0:
    print("\n🎉 SUCCESS! Hit 4%+ target!")
    print(f"   Iteration 10 achieved {return_pct:+.2f}% return ({capture_pct:.1f}% capture)")
    print(f"   Ready for production deployment on 15m timeframe")
elif return_pct >= 2.5:
    print(f"\n👍 GOOD PROGRESS! Hit {return_pct:+.2f}% ({capture_pct:.1f}% capture)")
    print(f"   Close to target. Next iteration:")
    print(f"   - Analyze which trades user had that bot missed")
    print(f"   - Add S/R detection for bonus points")
    print(f"   - Consider chart pattern recognition")
elif return_pct >= 1.66:
    print(f"\n📈 IMPROVED! From +1.66% to {return_pct:+.2f}% ({capture_pct:.1f}% capture)")
    print(f"   Moving in right direction. Continue iterating.")
else:
    print(f"\n⚠️  Filters may be TOO STRICT")
    print(f"   Only {total_trades} trades found")
    print(f"   Try loosening quality score or volume requirements")

print("\n" + "="*80)

# Save results
results_data = {
    'iteration': 10,
    'timeframe': '15m',
    'period': f'{start_date.date()} to {end_date.date()}',
    'params': {
        'stop_loss': 0.75,
        'profit_lock': 1.5,
        'quality_score_min': 50,
        'volume_ratio_min': 1.0,
        'confluence_min': 15,
        'volume_types': ['spike', 'elevated', 'normal']
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

output_file = data_dir / 'iteration_10_results.json'
with open(output_file, 'w') as f:
    json.dump(results_data, f, indent=2, default=str)

print(f"💾 Results saved to: {output_file}\n")
