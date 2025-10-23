#!/usr/bin/env python3
"""
FULL BACKTEST: Iteration 10 on ALL Historical Data

Run Iteration 10 (our winner: +2.19% in 17 days) on the ENTIRE dataset
to see:
1. Overall performance across all market conditions
2. Maximum drawdown
3. Monthly returns
4. Win rate consistency
5. Trade frequency

This gives us realistic expectations before live deployment!
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from datetime import timedelta

sys.path.append(str(Path(__file__).parent / 'src'))
from strategy.entry_detector_user_pattern import EntryDetector
from strategy.exit_manager_user_pattern import ExitManager

print("\n" + "="*80)
print("🚀 FULL BACKTEST: ITERATION 10 ON ALL HISTORICAL DATA")
print("="*80)

data_dir = Path(__file__).parent / 'trading_data'

# Load ALL data
print("\n📊 Loading full historical data...")
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')

for df in [df_15m, df_5m]:
    df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"   15m data: {len(df_15m)} candles")
print(f"   5m data: {len(df_5m)} candles")
print(f"   Period: {df_15m['timestamp'].min()} to {df_15m['timestamp'].max()}")

total_days = (df_15m['timestamp'].max() - df_15m['timestamp'].min()).days
print(f"   Total days: {total_days}")

print(f"\n⚙️  ITERATION 10 SETTINGS:")
print(f"   Timeframe: 15m primary, 5m confirmation")
print(f"   Quality Score: >= 50")
print(f"   Volume Ratio: >= 1.0")
print(f"   Take Profit: 5.0%")
print(f"   Stop Loss: 0.75%")
print(f"   Profit Lock: 1.5%")
print(f"   Max Hold: 48h")

# ============================================================================
# RUN FULL BACKTEST
# ============================================================================

print("\n" + "="*80)
print("🤖 RUNNING FULL BACKTEST")
print("="*80)

# Get signals
detector = EntryDetector(df_5m=df_5m, df_15m=df_15m)
df_signals = detector.scan_historical_signals(df_15m)

print(f"\n🎯 Total signals found: {df_signals['entry_signal'].sum()}")

# Run backtest
exit_manager = ExitManager()
initial_capital = 1000.0
capital = initial_capital
trades = []
equity_curve = []

in_position = False
current_trade = None

for i in range(len(df_signals)):
    row = df_signals.iloc[i]

    # Record equity
    equity_curve.append({
        'timestamp': row['timestamp'],
        'capital': capital,
        'in_position': in_position
    })

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
            current_trade['capital_after'] = capital

            trades.append(current_trade)
            in_position = False
            current_trade = None

# Close final position
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
    current_trade['capital_after'] = capital
    trades.append(current_trade)

# ============================================================================
# CALCULATE METRICS
# ============================================================================

print("\n" + "="*80)
print("📊 OVERALL PERFORMANCE")
print("="*80)

total_trades = len(trades)
winning_trades = [t for t in trades if t['profit_pct'] > 0]
losing_trades = [t for t in trades if t['profit_pct'] <= 0]
win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
total_return = (capital - initial_capital) / initial_capital * 100

print(f"\n💰 RETURNS:")
print(f"   Starting Capital: ${initial_capital:.2f}")
print(f"   Ending Capital: ${capital:.2f}")
print(f"   Total P&L: ${capital - initial_capital:+.2f}")
print(f"   Total Return: {total_return:+.2f}%")
print(f"   Annualized Return: {(total_return / total_days * 365):+.2f}%")

print(f"\n📈 TRADES:")
print(f"   Total Trades: {total_trades}")
print(f"   Winners: {len(winning_trades)} ({win_rate:.1f}%)")
print(f"   Losers: {len(losing_trades)}")
print(f"   Avg Trade Frequency: {total_days / total_trades:.1f} days per trade" if total_trades > 0 else "   No trades")

if len(winning_trades) > 0:
    avg_win = np.mean([t['profit_pct'] for t in winning_trades])
    max_win = max([t['profit_pct'] for t in winning_trades])
    print(f"\n✅ WINNERS:")
    print(f"   Average Win: {avg_win:.2f}%")
    print(f"   Max Win: {max_win:.2f}%")
    print(f"   Total Win P&L: ${sum([t['pnl'] for t in winning_trades]):+.2f}")

if len(losing_trades) > 0:
    avg_loss = np.mean([t['profit_pct'] for t in losing_trades])
    max_loss = min([t['profit_pct'] for t in losing_trades])
    print(f"\n❌ LOSERS:")
    print(f"   Average Loss: {avg_loss:.2f}%")
    print(f"   Max Loss: {max_loss:.2f}%")
    print(f"   Total Loss P&L: ${sum([t['pnl'] for t in losing_trades]):+.2f}")

# Calculate max drawdown
df_equity = pd.DataFrame(equity_curve)
df_equity['peak'] = df_equity['capital'].cummax()
df_equity['drawdown'] = (df_equity['capital'] - df_equity['peak']) / df_equity['peak'] * 100
max_drawdown = df_equity['drawdown'].min()

print(f"\n📉 RISK METRICS:")
print(f"   Max Drawdown: {max_drawdown:.2f}%")

if len(winning_trades) > 0 and len(losing_trades) > 0:
    profit_factor = abs(sum([t['pnl'] for t in winning_trades]) / sum([t['pnl'] for t in losing_trades]))
    print(f"   Profit Factor: {profit_factor:.2f}")

# Monthly breakdown
trades_df = pd.DataFrame(trades)
if len(trades_df) > 0:
    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
    trades_df['month'] = trades_df['exit_time'].dt.to_period('M')

    monthly_stats = trades_df.groupby('month').agg({
        'pnl': 'sum',
        'profit_pct': 'count'
    }).rename(columns={'profit_pct': 'trades'})

    monthly_stats['return_pct'] = (monthly_stats['pnl'] / 100) * 100  # Rough monthly return

    print(f"\n📅 MONTHLY BREAKDOWN:")
    print(f"\n{'Month':<12} {'Trades':<8} {'P&L':<12} {'Return'}")
    print("-" * 50)
    for month, row in monthly_stats.iterrows():
        print(f"{str(month):<12} {int(row['trades']):<8} ${row['pnl']:+8.2f}   {row['return_pct']:+.2f}%")

    print(f"\n{'Average/month:':<12} {monthly_stats['trades'].mean():<8.1f} ${monthly_stats['pnl'].mean():+8.2f}   {monthly_stats['return_pct'].mean():+.2f}%")

# ============================================================================
# SAVE RESULTS
# ============================================================================

print("\n" + "="*80)
print("💾 SAVING RESULTS")
print("="*80)

full_results = {
    'backtest_type': 'FULL_HISTORICAL',
    'iteration': 10,
    'period': {
        'start': str(df_15m['timestamp'].min()),
        'end': str(df_15m['timestamp'].max()),
        'total_days': total_days
    },
    'performance': {
        'total_return_pct': total_return,
        'annualized_return_pct': (total_return / total_days * 365),
        'total_pnl': capital - initial_capital,
        'final_capital': capital,
        'max_drawdown_pct': max_drawdown
    },
    'trades': {
        'total': total_trades,
        'winners': len(winning_trades),
        'losers': len(losing_trades),
        'win_rate': win_rate,
        'avg_win': np.mean([t['profit_pct'] for t in winning_trades]) if winning_trades else 0,
        'avg_loss': np.mean([t['profit_pct'] for t in losing_trades]) if losing_trades else 0,
        'max_win': max([t['profit_pct'] for t in winning_trades]) if winning_trades else 0,
        'max_loss': min([t['profit_pct'] for t in losing_trades]) if losing_trades else 0
    },
    'trade_list': trades,
    'equity_curve': equity_curve,
    'monthly_breakdown': {str(k): v for k, v in monthly_stats.to_dict('index').items()} if len(trades_df) > 0 else {}
}

with open(data_dir / 'iteration_10_FULL_backtest.json', 'w') as f:
    json.dump(full_results, f, indent=2, default=str)

print(f"✅ Full results saved to: iteration_10_FULL_backtest.json")

# ============================================================================
# VERDICT
# ============================================================================

print("\n" + "="*80)
print("✅ DEPLOYMENT READINESS CHECK")
print("="*80)

checks = []

# Check 1: Positive return
if total_return > 0:
    checks.append(("✅", f"Positive return: {total_return:+.2f}%"))
else:
    checks.append(("❌", f"Negative return: {total_return:+.2f}%"))

# Check 2: Win rate > 35%
if win_rate > 35:
    checks.append(("✅", f"Win rate acceptable: {win_rate:.1f}% (>35%)"))
else:
    checks.append(("⚠️", f"Win rate low: {win_rate:.1f}%"))

# Check 3: Max drawdown < 10%
if max_drawdown > -10:
    checks.append(("✅", f"Max drawdown acceptable: {max_drawdown:.2f}% (>-10%)"))
else:
    checks.append(("⚠️", f"Max drawdown high: {max_drawdown:.2f}%"))

# Check 4: Profit factor > 1.0
if len(winning_trades) > 0 and len(losing_trades) > 0:
    pf = abs(sum([t['pnl'] for t in winning_trades]) / sum([t['pnl'] for t in losing_trades]))
    if pf > 1.0:
        checks.append(("✅", f"Profit factor good: {pf:.2f} (>1.0)"))
    else:
        checks.append(("❌", f"Profit factor bad: {pf:.2f}"))

# Check 5: Enough trades
if total_trades > 20:
    checks.append(("✅", f"Sufficient trades: {total_trades} (>20)"))
else:
    checks.append(("⚠️", f"Few trades: {total_trades}"))

print("\n")
for emoji, msg in checks:
    print(f"{emoji} {msg}")

passed = sum(1 for emoji, _ in checks if emoji == "✅")
total = len(checks)

print(f"\n{'='*80}")
if passed >= 4:
    print("🚀 VERDICT: READY FOR LIVE DEPLOYMENT!")
    print(f"   Passed {passed}/{total} checks")
    print(f"   Expected return: ~{(total_return / total_days * 365):.1f}% annualized")
    print(f"   Recommended position size: 5-10% (test phase)")
elif passed >= 3:
    print("⚠️  VERDICT: PROCEED WITH CAUTION")
    print(f"   Passed {passed}/{total} checks")
    print(f"   Recommended: Paper trade first")
else:
    print("❌ VERDICT: NOT READY")
    print(f"   Only passed {passed}/{total} checks")
    print(f"   Recommended: Further optimization needed")

print("="*80 + "\n")
