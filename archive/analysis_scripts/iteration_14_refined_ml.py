#!/usr/bin/env python3
"""
ITERATION 14: REFINED ML + QUALITY SCORE

Iteration 13 FAILED (-1.20%) because:
- ML patterns were TOO LOOSE (152 signals → 80 trades)
- 50 losing trades destroyed capital
- You only took 17 trades, bot took 80 (5x overtrading!)

Fix: COMBINE ML patterns with Iteration 10's quality filtering
- Keep Iteration 10's quality_score >= 50
- Keep Iteration 10's 5% TP (prevents overtrading)
- Keep Iteration 10's profit lock
- ADD ML-discovered entry criteria as EXTRA filters

This should give us high-quality trades that match YOUR style!
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'src'))
from strategy.entry_detector_user_pattern import EntryDetector

print("\n" + "="*80)
print("🚀 ITERATION 14: REFINED ML + QUALITY SCORE")
print("="*80)

data_dir = Path(__file__).parent / 'trading_data'

# Load data
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

print(f"\n⚙️  ITERATION 14 SETTINGS:")
print(f"   Base: Iteration 10 (quality_score >= 50)")
print(f"   + ML Entry Filter: Tighter momentum/RSI checks")
print(f"   TP: 5.0% (prevent overtrading)")
print(f"   SL: 0.75%")
print(f"   Profit Lock: 1.5%")

# Load ML params
with open(data_dir / 'deep_ml_analysis_results.json', 'r') as f:
    ml_data = json.load(f)
    ml_params = ml_data['iteration_13_params']

print(f"\n📊 ML Filters:")
print(f"   LONG: RSI 63-74, Momentum >0.3%")
print(f"   SHORT: RSI 23-46, Momentum <-0.4%")

# ============================================================================
# CUSTOM EXIT MANAGER (Iteration 10 settings)
# ============================================================================

class Iteration10ExitManager:
    def __init__(self):
        """Iteration 10 proven settings"""
        self.take_profit_pct = 5.0
        self.stop_loss_pct = 0.75
        self.profit_lock_threshold = 1.5
        self.max_hold_hours = 48

    def check_exit(self, entry_price, entry_time, current_price, current_time,
                   direction, peak_profit_pct):
        result = {
            'should_exit': False,
            'exit_reason': '',
            'exit_price': current_price,
            'profit_pct': 0.0
        }

        if direction == 'long':
            profit_pct = (current_price - entry_price) / entry_price * 100
        else:
            profit_pct = (entry_price - current_price) / entry_price * 100

        result['profit_pct'] = profit_pct

        # Exit 1: Take profit
        if profit_pct >= self.take_profit_pct:
            result['should_exit'] = True
            result['exit_reason'] = f'Take profit: {profit_pct:.2f}%'
            return result

        # Exit 2: Stop loss
        if profit_pct <= -self.stop_loss_pct:
            result['should_exit'] = True
            result['exit_reason'] = f'Stop loss: {profit_pct:.2f}%'
            return result

        # Exit 3: Profit lock
        if peak_profit_pct >= self.profit_lock_threshold and profit_pct <= 0:
            result['should_exit'] = True
            result['exit_reason'] = f'Profit lock: peaked {peak_profit_pct:.2f}%, now {profit_pct:.2f}%'
            return result

        # Exit 4: Trailing stop
        if peak_profit_pct >= 2.0:
            trailing_width = 1.5
            if profit_pct < peak_profit_pct - trailing_width:
                result['should_exit'] = True
                result['exit_reason'] = f'Trailing stop: {profit_pct:.2f}% < peak {peak_profit_pct:.2f}%'
                return result

        # Exit 5: Time exit
        hours_held = (current_time - entry_time).total_seconds() / 3600
        if hours_held >= self.max_hold_hours:
            result['should_exit'] = True
            result['exit_reason'] = f'Time exit: {hours_held:.1f}h at {profit_pct:.2f}%'
            return result

        return result


# ============================================================================
# RUN BACKTEST
# ============================================================================

print("\n" + "="*80)
print("🤖 RUNNING ITERATION 14")
print("="*80)

# Get Iteration 10 signals
detector = EntryDetector(df_5m=df_5m_period, df_15m=df_15m_period)
df_signals = detector.scan_historical_signals(df_15m_period)

print(f"\n🎯 Iteration 10 detector found {df_signals['entry_signal'].sum()} signals")

# Filter signals with ML criteria
print(f"\n🔍 Applying ML filters...")

filtered_signals = []
for i in range(len(df_signals)):
    row = df_signals.iloc[i]
    if not row['entry_signal']:
        continue

    # Calculate momentum (need previous candles)
    if i < 4:
        continue

    prev_5 = df_signals.iloc[i-4:i]
    momentum = (row['close'] - prev_5.iloc[0]['close']) / prev_5.iloc[0]['close'] * 100

    # Apply ML filters
    if row['entry_direction'] == 'long':
        # LONG ML filter
        rsi_ok = ml_params['entry_long']['rsi_7_range'][0] <= row['rsi_7'] <= ml_params['entry_long']['rsi_7_range'][1]
        momentum_ok = momentum > ml_params['entry_long']['min_momentum_1h']

        if rsi_ok and momentum_ok:
            filtered_signals.append(i)

    elif row['entry_direction'] == 'short':
        # SHORT ML filter
        rsi_ok = ml_params['entry_short']['rsi_7_range'][0] <= row['rsi_7'] <= ml_params['entry_short']['rsi_7_range'][1]
        momentum_ok = momentum < ml_params['entry_short']['max_momentum_1h']

        if rsi_ok and momentum_ok:
            filtered_signals.append(i)

print(f"✅ ML filters passed: {len(filtered_signals)} signals (from {df_signals['entry_signal'].sum()})")

# Mark filtered signals
df_signals['ml_filtered_signal'] = False
for idx in filtered_signals:
    df_signals.iloc[idx, df_signals.columns.get_loc('ml_filtered_signal')] = True

# Run backtest with filtered signals
exit_manager = Iteration10ExitManager()
initial_capital = 1000.0
capital = initial_capital
trades = []

in_position = False
current_trade = None

for i in range(len(df_signals)):
    row = df_signals.iloc[i]

    if not in_position and row['ml_filtered_signal']:
        current_trade = {
            'entry_time': row['timestamp'],
            'entry_price': row['close'],
            'direction': row['entry_direction'],
            'quality_score': row.get('entry_quality_score', 0),
            'rsi_7': row['rsi_7'],
            'peak_profit_pct': 0.0
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

print(f"\n📊 ITERATION 14 RESULTS:")
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
user_actual_pnl = 73.63
capture_pct = (capital - initial_capital) / user_actual_pnl * 100

print("\n" + "="*80)
print("📊 COMPARISON")
print("="*80)

print(f"\n{'Iteration':<25} {'Trades':<8} {'WR':<8} {'Return':<10} {'Capture'}")
print(f"{'-'*75}")
print(f"{'User (ACTUAL)':<25} {17:<8} {'100%':<8} {'+7.36%':<10} {'100%'}")
print(f"{'Iteration 10 (Best)':<25} {39:<8} {'41.0%':<8} {'+2.19%':<10} {'29.7%'}")
print(f"{'Iteration 13 (ML only)':<25} {80:<8} {'37.5%':<8} {'-1.20%':<10} {'-16.4%'}")
print(f"{'ITERATION 14 (Refined)':<25} {total_trades:<8} {f'{win_rate:.1f}%':<8} {f'{return_pct:+.2f}%':<10} {f'{capture_pct:.1f}%'}")

print(f"\n{'Metric':<20} {'Iter 10':<15} {'Iter 14':<15} {'Change'}")
print(f"{'-'*60}")
print(f"{'Return':<20} {'+2.19%':<15} {f'{return_pct:+.2f}%':<15} {f'{return_pct - 2.19:+.2f}%'}")
print(f"{'Capture':<20} {'29.7%':<15} {f'{capture_pct:.1f}%':<15} {f'{capture_pct - 29.7:+.1f}%'}")
print(f"{'Trades':<20} {39:<15} {total_trades:<15} {total_trades - 39:+d}")

if return_pct > 2.19:
    improvement = ((return_pct / 2.19) - 1) * 100
    print(f"\n🎉 IMPROVED! +{improvement:.1f}% better than Iteration 10!")
elif return_pct >= 1.5:
    print(f"\n✅ Good performance, quality filtering working")
else:
    print(f"\n⚠️ Still not beating Iteration 10")

print("\n" + "="*80)

# Save
results_data = {
    'iteration': 14,
    'description': 'Refined ML + Iteration 10 quality score',
    'results': {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'return_pct': return_pct,
        'profit_capture_pct': capture_pct
    },
    'trades': trades
}

with open(data_dir / 'iteration_14_results.json', 'w') as f:
    json.dump(results_data, f, indent=2, default=str)

print(f"💾 Results saved to: iteration_14_results.json\n")
