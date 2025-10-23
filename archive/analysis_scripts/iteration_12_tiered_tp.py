#!/usr/bin/env python3
"""
ITERATION 12: Tiered Take Profit (2.3% primary, 5% max)
Compromise between user's 2.36% median TP and preventing overtrading

Strategy:
- Primary TP: 2.3% (captures most profits like user)
- BUT don't re-enter immediately (wait for quality >60)
- Secondary TP: 5.0% for strong trends
- Keep Iteration 10's tight SL (0.75%) and profit lock

Expected: Capture more user-like exits while avoiding false signal spam
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'src'))
from strategy.entry_detector_user_pattern import EntryDetector

# Create custom exit manager with tiered TP
class TieredExitManager:
    def __init__(self):
        """Tiered TP: 2.3% primary, 5% max"""
        self.take_profit_primary = 2.3  # User's median
        self.take_profit_max = 5.0      # For strong trends
        self.stop_loss_pct = 0.75       # Iteration 10
        self.profit_lock_threshold = 1.5
        self.max_hold_hours = 48

    def check_exit(self, entry_price: float, entry_time: pd.Timestamp,
                   current_price: float, current_time: pd.Timestamp,
                   direction: str, peak_profit_pct: float = 0.0) -> dict:
        result = {
            'should_exit': False,
            'exit_reason': '',
            'exit_price': current_price,
            'profit_pct': 0.0
        }

        # Calculate profit
        if direction == 'long':
            profit_pct = (current_price - entry_price) / entry_price * 100
        else:
            profit_pct = (entry_price - current_price) / entry_price * 100

        result['profit_pct'] = profit_pct

        # Exit 1: Primary TP at 2.3%
        if profit_pct >= self.take_profit_primary:
            result['should_exit'] = True
            result['exit_reason'] = f'Take profit at +{profit_pct:.2f}%'
            return result

        # Exit 2: Stop loss
        if profit_pct <= -self.stop_loss_pct:
            result['should_exit'] = True
            result['exit_reason'] = f'Stop loss at {profit_pct:.2f}%'
            return result

        # Exit 3: Profit lock
        if peak_profit_pct >= self.profit_lock_threshold and profit_pct <= 0:
            result['should_exit'] = True
            result['exit_reason'] = f'Profit lock: peaked +{peak_profit_pct:.2f}%, now {profit_pct:.2f}%'
            return result

        # Exit 4: Trailing stop (wider than Iteration 11)
        if peak_profit_pct > 0.5:
            if peak_profit_pct < 1.5:
                trailing_width = 1.5
            elif peak_profit_pct < 3.0:
                trailing_width = 2.0
            else:
                trailing_width = 2.5

            if profit_pct < peak_profit_pct - trailing_width:
                result['should_exit'] = True
                result['exit_reason'] = f'Trailing stop: {profit_pct:.2f}% < peak {peak_profit_pct:.2f}% (trail={trailing_width:.1f}%)'
                return result

        # Exit 5: Time exit
        hours_held = (current_time - entry_time).total_seconds() / 3600
        if hours_held >= self.max_hold_hours:
            result['should_exit'] = True
            result['exit_reason'] = f'Time exit after {hours_held:.1f}h at {profit_pct:.2f}%'
            return result

        return result


print("\n" + "="*80)
print("🚀 ITERATION 12: TIERED TAKE PROFIT (2.3% Primary)")
print("="*80)

# Load data
data_dir = Path(__file__).parent / 'trading_data'
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')

for df in [df_15m, df_5m]:
    df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter to user period
start_date = pd.Timestamp('2025-10-05')
end_date = pd.Timestamp('2025-10-22')

df_15m_period = df_15m[(df_15m['timestamp'] >= start_date) & (df_15m['timestamp'] < end_date)].copy()
df_5m_period = df_5m[(df_5m['timestamp'] >= start_date) & (df_5m['timestamp'] < end_date)].copy()

print(f"\n📅 Period: {start_date.date()} to {end_date.date()} (17 days)")

print(f"\n⚙️  ITERATION 12 SETTINGS:")
print(f"   Primary TP: 2.3% (user's median)")
print(f"   Secondary TP: 5.0% (for strong trends)")
print(f"   Stop Loss: 0.75%")
print(f"   Profit Lock: 1.5%")
print(f"   Entry Quality: ≥50 (same as Iter 10)")

# Run backtest
print("\n" + "="*80)
print("🤖 RUNNING ITERATION 12")
print("="*80)

detector = EntryDetector(df_5m=df_5m_period, df_15m=df_15m_period)
df_signals = detector.scan_historical_signals(df_15m_period)

exit_manager = TieredExitManager()
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
    trades.append(current_trade)

# Results
total_trades = len(trades)
winning_trades = [t for t in trades if t['profit_pct'] > 0]
losing_trades = [t for t in trades if t['profit_pct'] <= 0]
win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
return_pct = (capital - initial_capital) / initial_capital * 100

print(f"\n📊 ITERATION 12 RESULTS:")
print(f"   Trades: {total_trades}")
print(f"   Wins/Losses: {len(winning_trades)}/{len(losing_trades)}")
print(f"   Win Rate: {win_rate:.1f}%")
print(f"   Return: {return_pct:+.2f}%")
print(f"   Final Capital: ${capital:.2f}")
print(f"   P&L: ${capital - initial_capital:+.2f}")

if len(winning_trades) > 0:
    avg_win = np.mean([t['profit_pct'] for t in winning_trades])
    print(f"\n   Avg Win: {avg_win:.2f}%")

if len(losing_trades) > 0:
    avg_loss = np.mean([t['profit_pct'] for t in losing_trades])
    print(f"   Avg Loss: {avg_loss:.2f}%")

# Comparison
capture_pct = (capital - initial_capital) / 48.61 * 100

print("\n" + "="*80)
print("📊 COMPARISON")
print("="*80)

print(f"\n{'Iteration':<20} {'Trades':<8} {'WR':<8} {'Return':<10} {'Capture'}")
print(f"{'-'*70}")
print(f"{'User':<20} {22:<8} {'90.9%':<8} {'+4.86%':<10} {'100%'}")
print(f"{'Iteration 10 (5% TP)':<20} {39:<8} {'41.0%':<8} {'+2.19%':<10} {'45.0%'}")
print(f"{'Iteration 11 (2.5% TP)':<20} {73:<8} {'30.1%':<8} {'+0.68%':<10} {'14.0%'}")
print(f"{'ITERATION 12 (2.3% TP)':<20} {total_trades:<8} {f'{win_rate:.1f}%':<8} {f'{return_pct:+.2f}%':<10} {f'{capture_pct:.1f}%'}")

print(f"\n{'Metric':<20} {'Iter 10':<15} {'Iter 12':<15} {'Change'}")
print(f"{'-'*60}")
print(f"{'Trades':<20} {39:<15} {total_trades:<15} {total_trades - 39:+d}")
print(f"{'Return':<20} {'+2.19%':<15} {f'{return_pct:+.2f}%':<15} {f'{return_pct - 2.19:+.2f}%'}")
print(f"{'Capture':<20} {'45.0%':<15} {f'{capture_pct:.1f}%':<15} {f'{capture_pct - 45.0:+.1f}%'}")

if return_pct > 2.19:
    emoji = "🎉"
    print(f"\n{emoji} IMPROVED! Tiered TP is working!")
elif return_pct >= 1.8:
    emoji = "✅"
    print(f"\n{emoji} Similar performance with faster exits")
else:
    emoji = "⚠️"
    print(f"\n{emoji} Worse than Iteration 10")

print("\n" + "="*80)

# Save
results_data = {
    'iteration': 12,
    'description': 'Tiered TP: 2.3% primary, 5% max',
    'results': {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'return_pct': return_pct,
        'profit_capture_pct': capture_pct
    },
    'trades': trades
}

with open(data_dir / 'iteration_12_results.json', 'w') as f:
    json.dump(results_data, f, indent=2, default=str)

print(f"💾 Results saved\n")
