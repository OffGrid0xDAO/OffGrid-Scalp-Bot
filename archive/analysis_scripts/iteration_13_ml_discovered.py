#!/usr/bin/env python3
"""
ITERATION 13: ML-DISCOVERED PATTERNS from Your ACTUAL 17 Trades

Key Discoveries:
1. LONG entries: RSI 63-74, Stoch >52, Alignment >0.43, Momentum >0.3%
2. SHORT entries: RSI 24-46, Stoch <38, Alignment <0.49, Momentum <-0.4%
3. Adaptive TP: Strong moves 8.7%, Weak moves 3.2%
4. Hold time: ~7-12 hours
5. Capture ratio: 73% of peak profit

This iteration ONLY takes trades that match YOUR entry patterns!
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'src'))

print("\n" + "="*80)
print("🚀 ITERATION 13: ML-DISCOVERED PATTERNS (From Your 17 Trades)")
print("="*80)

# Load ML-discovered parameters
data_dir = Path(__file__).parent / 'trading_data'
with open(data_dir / 'deep_ml_analysis_results.json', 'r') as f:
    ml_data = json.load(f)
    ml_params = ml_data['iteration_13_params']

print("\n📊 ML-Discovered Entry Rules:")
print(f"\n   LONG Entry:")
print(f"      RSI-7: {ml_params['entry_long']['rsi_7_range'][0]:.0f}-{ml_params['entry_long']['rsi_7_range'][1]:.0f}")
print(f"      Stoch D: >{ml_params['entry_long']['min_stoch_d']:.0f}")
print(f"      Alignment: >{ml_params['entry_long']['min_alignment']:.2f}")
print(f"      Momentum 1h: >{ml_params['entry_long']['min_momentum_1h']:.2f}%")

print(f"\n   SHORT Entry:")
print(f"      RSI-7: {ml_params['entry_short']['rsi_7_range'][0]:.0f}-{ml_params['entry_short']['rsi_7_range'][1]:.0f}")
print(f"      Stoch D: <{ml_params['entry_short']['max_stoch_d']:.0f}")
print(f"      Alignment: <{ml_params['entry_short']['max_alignment']:.2f}")
print(f"      Momentum 1h: <{ml_params['entry_short']['max_momentum_1h']:.2f}%")

print(f"\n📊 ML-Discovered Exit Rules:")
print(f"      Strong TP: {ml_params['exit']['adaptive_tp_strong']:.1f}%")
print(f"      Weak TP: {ml_params['exit']['adaptive_tp_weak']:.1f}%")
print(f"      Stop Loss: {ml_params['exit']['stop_loss']:.2f}%")
print(f"      Max Hold: {ml_params['exit']['max_hold_hours']:.0f}h")

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


# ============================================================================
# CUSTOM ENTRY DETECTOR using ML-discovered patterns
# ============================================================================

class MLDiscoveredEntryDetector:
    """Entry detector that ONLY matches YOUR actual trading patterns"""

    def __init__(self, ml_params):
        self.ml_params = ml_params

    def check_long_entry(self, row, prev_5_candles):
        """Check if LONG entry matches YOUR pattern"""
        params = self.ml_params['entry_long']

        # Calculate momentum
        if len(prev_5_candles) < 4:
            return False
        momentum = (row['close'] - prev_5_candles.iloc[0]['close']) / prev_5_candles.iloc[0]['close'] * 100

        # Match YOUR long criteria
        if not (params['rsi_7_range'][0] <= row['rsi_7'] <= params['rsi_7_range'][1]):
            return False
        if row['stoch_d'] < params['min_stoch_d']:
            return False
        if row['alignment_pct'] < params['min_alignment']:
            return False
        if momentum < params['min_momentum_1h']:
            return False

        return True

    def check_short_entry(self, row, prev_5_candles):
        """Check if SHORT entry matches YOUR pattern"""
        params = self.ml_params['entry_short']

        # Calculate momentum
        if len(prev_5_candles) < 4:
            return False
        momentum = (row['close'] - prev_5_candles.iloc[0]['close']) / prev_5_candles.iloc[0]['close'] * 100

        # Match YOUR short criteria
        if not (params['rsi_7_range'][0] <= row['rsi_7'] <= params['rsi_7_range'][1]):
            return False
        if row['stoch_d'] > params['max_stoch_d']:
            return False
        if row['alignment_pct'] > params['max_alignment']:
            return False
        if momentum > params['max_momentum_1h']:
            return False

        return True

    def scan_signals(self, df):
        """Scan for signals matching YOUR patterns"""
        signals = []

        for i in range(5, len(df)):  # Need 5 candles for momentum
            row = df.iloc[i]
            prev_5 = df.iloc[i-4:i]

            long_signal = self.check_long_entry(row, prev_5)
            short_signal = self.check_short_entry(row, prev_5)

            if long_signal:
                signals.append({
                    'timestamp': row['timestamp'],
                    'price': row['close'],
                    'direction': 'long',
                    'rsi_7': row['rsi_7'],
                    'stoch_d': row['stoch_d']
                })
            elif short_signal:
                signals.append({
                    'timestamp': row['timestamp'],
                    'price': row['close'],
                    'direction': 'short',
                    'rsi_7': row['rsi_7'],
                    'stoch_d': row['stoch_d']
                })

        return signals


# ============================================================================
# ADAPTIVE EXIT MANAGER using ML-discovered patterns
# ============================================================================

class MLDiscoveredExitManager:
    """Exit manager using YOUR actual exit patterns"""

    def __init__(self, ml_params):
        self.params = ml_params['exit']
        self.stop_loss = self.params['stop_loss']
        self.max_hold_hours = self.params['max_hold_hours']
        self.target_capture = self.params['target_capture_ratio']

    def get_adaptive_tp(self, momentum):
        """Adaptive TP based on entry momentum (strong vs weak)"""
        # Strong momentum = use big winner TP
        # Weak momentum = use small winner TP
        if abs(momentum) > 0.5:
            return self.params['adaptive_tp_strong']
        else:
            return self.params['adaptive_tp_weak']

    def check_exit(self, entry_price, entry_time, current_price, current_time,
                   direction, peak_profit_pct, entry_momentum, current_rsi):

        result = {
            'should_exit': False,
            'exit_reason': '',
            'exit_price': current_price,
            'profit_pct': 0.0
        }

        # Calculate current profit
        if direction == 'long':
            profit_pct = (current_price - entry_price) / entry_price * 100
        else:
            profit_pct = (entry_price - current_price) / entry_price * 100

        result['profit_pct'] = profit_pct

        # Get adaptive TP
        adaptive_tp = self.get_adaptive_tp(entry_momentum)

        # Exit 1: Adaptive Take Profit
        if profit_pct >= adaptive_tp:
            result['should_exit'] = True
            result['exit_reason'] = f'Adaptive TP hit: {profit_pct:.2f}% >= {adaptive_tp:.1f}%'
            return result

        # Exit 2: Stop Loss
        if profit_pct <= -self.stop_loss:
            result['should_exit'] = True
            result['exit_reason'] = f'Stop loss: {profit_pct:.2f}%'
            return result

        # Exit 3: RSI Reversal (YOU exit around RSI 51)
        if direction == 'long' and current_rsi > 75 and profit_pct > 1.0:
            result['should_exit'] = True
            result['exit_reason'] = f'RSI overbought: {current_rsi:.0f} (profit secured: {profit_pct:.2f}%)'
            return result
        elif direction == 'short' and current_rsi < 25 and profit_pct > 1.0:
            result['should_exit'] = True
            result['exit_reason'] = f'RSI oversold: {current_rsi:.0f} (profit secured: {profit_pct:.2f}%)'
            return result

        # Exit 4: Capture 73% of peak (YOUR average)
        if peak_profit_pct > 2.0:
            target_profit = peak_profit_pct * self.target_capture
            if profit_pct < target_profit:
                result['should_exit'] = True
                result['exit_reason'] = f'Capture ratio: {profit_pct:.2f}% < {target_profit:.2f}% (73% of peak {peak_profit_pct:.2f}%)'
                return result

        # Exit 5: Time limit (YOUR median hold ~7h, max 11h from ML)
        hours_held = (current_time - entry_time).total_seconds() / 3600
        if hours_held >= self.max_hold_hours:
            result['should_exit'] = True
            result['exit_reason'] = f'Max hold time: {hours_held:.1f}h at {profit_pct:.2f}%'
            return result

        return result


# ============================================================================
# RUN BACKTEST
# ============================================================================

print("\n" + "="*80)
print("🤖 RUNNING ITERATION 13 (ML-Discovered Patterns)")
print("="*80)

detector = MLDiscoveredEntryDetector(ml_params)
signals = detector.scan_signals(df_15m_period)

print(f"\n🎯 Found {len(signals)} signals matching YOUR entry patterns")

# Backtest
exit_manager = MLDiscoveredExitManager(ml_params)
initial_capital = 1000.0
capital = initial_capital
trades = []

in_position = False
current_trade = None

# Convert signals to dataframe
df_signals = df_15m_period.copy()
df_signals['entry_signal'] = False
df_signals['entry_direction'] = ''

for signal in signals:
    idx = df_signals[df_signals['timestamp'] == signal['timestamp']].index
    if len(idx) > 0:
        df_signals.loc[idx[0], 'entry_signal'] = True
        df_signals.loc[idx[0], 'entry_direction'] = signal['direction']

# Run backtest
for i in range(5, len(df_signals)):
    row = df_signals.iloc[i]
    prev_5 = df_signals.iloc[i-4:i]

    # Calculate momentum for adaptive TP
    momentum = (row['close'] - prev_5.iloc[0]['close']) / prev_5.iloc[0]['close'] * 100

    if not in_position and row['entry_signal']:
        current_trade = {
            'entry_time': row['timestamp'],
            'entry_price': row['close'],
            'direction': row['entry_direction'],
            'entry_rsi': row['rsi_7'],
            'entry_momentum': momentum,
            'peak_profit_pct': 0.0
        }
        in_position = True

    elif in_position and current_trade:
        # Calculate profit
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
            current_trade['peak_profit_pct'],
            current_trade['entry_momentum'],
            row['rsi_7']
        )

        if exit_result['should_exit']:
            current_trade['exit_time'] = row['timestamp']
            current_trade['exit_price'] = exit_result['exit_price']
            current_trade['profit_pct'] = exit_result['profit_pct']
            current_trade['exit_reason'] = exit_result['exit_reason']

            # Calculate PNL
            position_size = capital * 0.1
            pnl = position_size * (exit_result['profit_pct'] / 100)
            current_trade['pnl'] = pnl
            capital += pnl

            trades.append(current_trade)
            in_position = False
            current_trade = None

# Close final position if any
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

print(f"\n📊 ITERATION 13 RESULTS:")
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
print("📊 COMPARISON TO USER & ITERATION 10")
print("="*80)

print(f"\n{'Iteration':<25} {'Trades':<8} {'WR':<8} {'Return':<10} {'Capture'}")
print(f"{'-'*75}")
print(f"{'User (ACTUAL)':<25} {17:<8} {'100%':<8} {'+7.36%':<10} {'100%'}")
print(f"{'Iteration 10 (Best)':<25} {39:<8} {'41.0%':<8} {'+2.19%':<10} {'29.7%'}")
print(f"{'ITERATION 13 (ML)':<25} {total_trades:<8} {f'{win_rate:.1f}%':<8} {f'{return_pct:+.2f}%':<10} {f'{capture_pct:.1f}%'}")

print(f"\n{'Metric':<20} {'Iter 10':<15} {'Iter 13':<15} {'Change'}")
print(f"{'-'*60}")
print(f"{'Return':<20} {'+2.19%':<15} {f'{return_pct:+.2f}%':<15} {f'{return_pct - 2.19:+.2f}%'}")
print(f"{'Capture':<20} {'29.7%':<15} {f'{capture_pct:.1f}%':<15} {f'{capture_pct - 29.7:+.1f}%'}")
print(f"{'Trades':<20} {39:<15} {total_trades:<15} {total_trades - 39:+d}")

if return_pct > 2.19:
    improvement = ((return_pct / 2.19) - 1) * 100
    print(f"\n🎉 IMPROVED! +{improvement:.1f}% better than Iteration 10!")
    print(f"   ML-discovered patterns are working!")
elif return_pct >= 1.8:
    print(f"\n✅ Similar performance, fewer trades")
else:
    print(f"\n⚠️ Worse than Iteration 10")
    print(f"   ML patterns may be too restrictive")

print("\n" + "="*80)

# Save results
results_data = {
    'iteration': 13,
    'description': 'ML-discovered patterns from your actual 17 trades',
    'ml_params': ml_params,
    'results': {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'return_pct': return_pct,
        'profit_capture_pct': capture_pct
    },
    'trades': trades
}

with open(data_dir / 'iteration_13_results.json', 'w') as f:
    json.dump(results_data, f, indent=2, default=str)

print(f"💾 Results saved to: iteration_13_results.json\n")
