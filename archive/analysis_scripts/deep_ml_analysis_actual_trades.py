#!/usr/bin/env python3
"""
DEEP ML ANALYSIS: Your ACTUAL 17 Trades
Analyze entry AND exit patterns to discover:
1. What indicators were present at YOUR entries
2. What made you exit (momentum, reversal, time?)
3. How to replicate your 7.36% performance
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import timedelta

print("\n" + "="*80)
print("🤖 DEEP ML ANALYSIS: YOUR ACTUAL TRADING PATTERNS")
print("="*80)

data_dir = Path(__file__).parent / 'trading_data'

# Load your actual trades
with open(data_dir / 'user_trades_ACTUAL_exits.json', 'r') as f:
    user_data = json.load(f)
user_trades = pd.DataFrame(user_data['trades'])
user_trades['entry_time'] = pd.to_datetime(user_trades['entry_time'])
user_trades['exit_time'] = pd.to_datetime(user_trades['exit_time'])

# Load 15m data
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

# Load 5m data for higher resolution
df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')
df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])

print(f"\n📊 Analyzing {len(user_trades)} complete trades")
print(f"   Total PNL: ${user_data['total_pnl']:.2f}")
print(f"   Return: {user_data['return_pct']:.2f}%")
print(f"   Win Rate: {user_data['win_rate']:.1f}%")

# ============================================================================
# PART 1: ENTRY ANALYSIS
# ============================================================================

print("\n" + "="*80)
print("🎯 PART 1: ENTRY PATTERN ANALYSIS")
print("="*80)

entry_patterns = []

for idx, trade in user_trades.iterrows():
    entry_time = trade['entry_time']
    direction = trade['direction']

    # Find entry candle on 15m
    tolerance = timedelta(minutes=1)
    entry_15m = df_15m[
        (df_15m['timestamp'] >= entry_time - tolerance) &
        (df_15m['timestamp'] <= entry_time + tolerance)
    ]

    # Find entry candle on 5m
    entry_5m = df_5m[
        (df_5m['timestamp'] >= entry_time - tolerance) &
        (df_5m['timestamp'] <= entry_time + tolerance)
    ]

    if len(entry_15m) > 0 and len(entry_5m) > 0:
        candle_15m = entry_15m.iloc[0]
        candle_5m = entry_5m.iloc[0]

        # Get previous candles for momentum
        idx_15m = df_15m[df_15m['timestamp'] == candle_15m['timestamp']].index[0]
        prev_5_candles = df_15m.iloc[max(0, idx_15m-5):idx_15m]

        # Calculate price momentum
        price_change_1h = ((candle_15m['close'] - prev_5_candles.iloc[0]['close']) / prev_5_candles.iloc[0]['close'] * 100) if len(prev_5_candles) > 0 else 0

        pattern = {
            'trade_num': trade['trade_num'],
            'direction': direction,
            'profit_pct': trade['profit_pct'],
            # 15m indicators at entry
            'rsi_7_15m': candle_15m.get('rsi_7'),
            'rsi_14_15m': candle_15m.get('rsi_14'),
            'stoch_k_15m': candle_15m.get('stoch_k'),
            'stoch_d_15m': candle_15m.get('stoch_d'),
            'volume_ratio_15m': candle_15m.get('volume_ratio'),
            'volume_status_15m': candle_15m.get('volume_status'),
            'alignment_pct_15m': candle_15m.get('alignment_pct'),
            'compression_15m': candle_15m.get('compression_score'),
            'expansion_rate_15m': candle_15m.get('expansion_rate'),
            'bb_position_15m': (candle_15m['close'] - candle_15m.get('bb_lower', candle_15m['close'])) / (candle_15m.get('bb_upper', candle_15m['close']) - candle_15m.get('bb_lower', candle_15m['close'])) if candle_15m.get('bb_upper') else 0.5,
            # 5m indicators at entry
            'rsi_7_5m': candle_5m.get('rsi_7'),
            'stoch_d_5m': candle_5m.get('stoch_d'),
            'alignment_pct_5m': candle_5m.get('alignment_pct'),
            # Momentum
            'price_momentum_1h': price_change_1h,
        }

        entry_patterns.append(pattern)

df_entries = pd.DataFrame(entry_patterns)

print(f"\n✅ Analyzed {len(df_entries)} entry points")

# Separate by direction
long_entries = df_entries[df_entries['direction'] == 'long']
short_entries = df_entries[df_entries['direction'] == 'short']

print(f"\n📈 LONG ENTRY PATTERNS ({len(long_entries)} trades):")
print(f"\n   RSI-7 (15m):")
print(f"      Range: {long_entries['rsi_7_15m'].min():.1f} - {long_entries['rsi_7_15m'].max():.1f}")
print(f"      Median: {long_entries['rsi_7_15m'].median():.1f}")
print(f"      Q1-Q3: {long_entries['rsi_7_15m'].quantile(0.25):.1f} - {long_entries['rsi_7_15m'].quantile(0.75):.1f}")

print(f"\n   Stoch D (15m):")
print(f"      Range: {long_entries['stoch_d_15m'].min():.1f} - {long_entries['stoch_d_15m'].max():.1f}")
print(f"      Median: {long_entries['stoch_d_15m'].median():.1f}")

print(f"\n   Ribbon Alignment (15m):")
print(f"      Range: {long_entries['alignment_pct_15m'].min():.3f} - {long_entries['alignment_pct_15m'].max():.3f}")
print(f"      Median: {long_entries['alignment_pct_15m'].median():.3f}")

print(f"\n   Volume Ratio (15m):")
print(f"      Range: {long_entries['volume_ratio_15m'].min():.2f} - {long_entries['volume_ratio_15m'].max():.2f}")
print(f"      Median: {long_entries['volume_ratio_15m'].median():.2f}")

print(f"\n   Compression (15m):")
print(f"      Range: {long_entries['compression_15m'].min():.1f} - {long_entries['compression_15m'].max():.1f}")
print(f"      Median: {long_entries['compression_15m'].median():.1f}")

print(f"\n   Price Momentum (1h):")
print(f"      Range: {long_entries['price_momentum_1h'].min():.2f}% - {long_entries['price_momentum_1h'].max():.2f}%")
print(f"      Median: {long_entries['price_momentum_1h'].median():.2f}%")

print(f"\n📉 SHORT ENTRY PATTERNS ({len(short_entries)} trades):")
print(f"\n   RSI-7 (15m):")
print(f"      Range: {short_entries['rsi_7_15m'].min():.1f} - {short_entries['rsi_7_15m'].max():.1f}")
print(f"      Median: {short_entries['rsi_7_15m'].median():.1f}")

print(f"\n   Stoch D (15m):")
print(f"      Range: {short_entries['stoch_d_15m'].min():.1f} - {short_entries['stoch_d_15m'].max():.1f}")
print(f"      Median: {short_entries['stoch_d_15m'].median():.1f}")

print(f"\n   Ribbon Alignment (15m):")
print(f"      Range: {short_entries['alignment_pct_15m'].min():.3f} - {short_entries['alignment_pct_15m'].max():.3f}")
print(f"      Median: {short_entries['alignment_pct_15m'].median():.3f}")

print(f"\n   Price Momentum (1h):")
print(f"      Range: {short_entries['price_momentum_1h'].min():.2f}% - {short_entries['price_momentum_1h'].max():.2f}%")
print(f"      Median: {short_entries['price_momentum_1h'].median():.2f}%")

# ============================================================================
# PART 2: EXIT ANALYSIS
# ============================================================================

print("\n" + "="*80)
print("🚪 PART 2: EXIT PATTERN ANALYSIS")
print("="*80)

exit_patterns = []

for idx, trade in user_trades.iterrows():
    exit_time = trade['exit_time']
    entry_time = trade['entry_time']

    # Find exit candle
    tolerance = timedelta(minutes=1)
    exit_15m = df_15m[
        (df_15m['timestamp'] >= exit_time - tolerance) &
        (df_15m['timestamp'] <= exit_time + tolerance)
    ]

    if len(exit_15m) > 0:
        exit_candle = exit_15m.iloc[0]

        # Calculate hold time
        hold_hours = (exit_time - entry_time).total_seconds() / 3600

        # Get price action during trade
        trade_candles = df_15m[
            (df_15m['timestamp'] >= entry_time) &
            (df_15m['timestamp'] <= exit_time)
        ]

        if len(trade_candles) > 1:
            # Find peak profit (approximate)
            if trade['direction'] == 'long':
                peak_price = trade_candles['high'].max()
                peak_profit = (peak_price - trade['entry_price']) / trade['entry_price'] * 100
            else:
                peak_price = trade_candles['low'].min()
                peak_profit = (trade['entry_price'] - peak_price) / trade['entry_price'] * 100

            # Exit momentum
            exit_rsi = exit_candle.get('rsi_7')
            exit_stoch = exit_candle.get('stoch_d')

            pattern = {
                'trade_num': trade['trade_num'],
                'direction': trade['direction'],
                'profit_pct': trade['profit_pct'],
                'hold_hours': hold_hours,
                'peak_profit': peak_profit,
                'profit_giveback': peak_profit - trade['profit_pct'],
                'exit_rsi_7': exit_rsi,
                'exit_stoch_d': exit_stoch,
                'exit_alignment': exit_candle.get('alignment_pct'),
                'num_candles': len(trade_candles),
            }

            exit_patterns.append(pattern)

df_exits = pd.DataFrame(exit_patterns)

print(f"\n✅ Analyzed {len(df_exits)} exit points")

print(f"\n⏱️  HOLD TIME ANALYSIS:")
print(f"   Range: {df_exits['hold_hours'].min():.1f}h - {df_exits['hold_hours'].max():.1f}h")
print(f"   Median: {df_exits['hold_hours'].median():.1f}h")
print(f"   Mean: {df_exits['hold_hours'].mean():.1f}h")

print(f"\n🎯 PROFIT CAPTURE:")
print(f"   Actual Profit (avg): {df_exits['profit_pct'].mean():.2f}%")
print(f"   Peak Profit (avg): {df_exits['peak_profit'].mean():.2f}%")
print(f"   Giveback (avg): {df_exits['profit_giveback'].mean():.2f}%")
print(f"   Capture Ratio: {(df_exits['profit_pct'].mean() / df_exits['peak_profit'].mean() * 100):.1f}%")

print(f"\n📊 EXIT RSI-7:")
print(f"   Range: {df_exits['exit_rsi_7'].min():.1f} - {df_exits['exit_rsi_7'].max():.1f}")
print(f"   Median: {df_exits['exit_rsi_7'].median():.1f}")

print(f"\n📊 EXIT Stoch D:")
print(f"   Range: {df_exits['exit_stoch_d'].min():.1f} - {df_exits['exit_stoch_d'].max():.1f}")
print(f"   Median: {df_exits['exit_stoch_d'].median():.1f}")

# Find big winners vs small winners
big_winners = df_exits[df_exits['profit_pct'] > 5]
small_winners = df_exits[df_exits['profit_pct'] <= 5]

print(f"\n🔥 BIG WINNERS (>{5}%) Analysis ({len(big_winners)} trades):")
if len(big_winners) > 0:
    print(f"   Avg Profit: {big_winners['profit_pct'].mean():.2f}%")
    print(f"   Avg Hold Time: {big_winners['hold_hours'].mean():.1f}h")
    print(f"   Avg Peak: {big_winners['peak_profit'].mean():.2f}%")
    print(f"   Avg Giveback: {big_winners['profit_giveback'].mean():.2f}%")
    print(f"   Capture Ratio: {(big_winners['profit_pct'].mean() / big_winners['peak_profit'].mean() * 100):.1f}%")

print(f"\n💰 SMALL WINNERS (<={5}%) Analysis ({len(small_winners)} trades):")
if len(small_winners) > 0:
    print(f"   Avg Profit: {small_winners['profit_pct'].mean():.2f}%")
    print(f"   Avg Hold Time: {small_winners['hold_hours'].mean():.1f}h")
    print(f"   Avg Peak: {small_winners['peak_profit'].mean():.2f}%")
    print(f"   Avg Giveback: {small_winners['profit_giveback'].mean():.2f}%")
    print(f"   Capture Ratio: {(small_winners['profit_pct'].mean() / small_winners['peak_profit'].mean() * 100):.1f}%")

# ============================================================================
# PART 3: ML-DISCOVERED RULES
# ============================================================================

print("\n" + "="*80)
print("🤖 ML-DISCOVERED TRADING RULES")
print("="*80)

print(f"\n1️⃣  ENTRY RULES:")

# LONG entry rules
long_rsi_q1 = long_entries['rsi_7_15m'].quantile(0.25)
long_rsi_q3 = long_entries['rsi_7_15m'].quantile(0.75)
long_stoch_median = long_entries['stoch_d_15m'].median()
long_alignment_median = long_entries['alignment_pct_15m'].median()
long_momentum_median = long_entries['price_momentum_1h'].median()

print(f"\n   LONG Entry Criteria:")
print(f"      - RSI-7 (15m): {long_rsi_q1:.0f}-{long_rsi_q3:.0f} (Q1-Q3)")
print(f"      - Stoch D (15m): >{long_stoch_median:.0f}")
print(f"      - Alignment (15m): >{long_alignment_median:.2f}")
print(f"      - 1h Momentum: >{long_momentum_median:.1f}%")

# SHORT entry rules
short_rsi_q1 = short_entries['rsi_7_15m'].quantile(0.25)
short_rsi_q3 = short_entries['rsi_7_15m'].quantile(0.75)
short_stoch_median = short_entries['stoch_d_15m'].median()
short_alignment_median = short_entries['alignment_pct_15m'].median()
short_momentum_median = short_entries['price_momentum_1h'].median()

print(f"\n   SHORT Entry Criteria:")
print(f"      - RSI-7 (15m): {short_rsi_q1:.0f}-{short_rsi_q3:.0f} (Q1-Q3)")
print(f"      - Stoch D (15m): <{short_stoch_median:.0f}")
print(f"      - Alignment (15m): <{short_alignment_median:.2f}")
print(f"      - 1h Momentum: <{short_momentum_median:.1f}%")

print(f"\n2️⃣  EXIT RULES:")

median_hold = df_exits['hold_hours'].median()
median_exit_rsi = df_exits['exit_rsi_7'].median()
avg_capture_ratio = (df_exits['profit_pct'].mean() / df_exits['peak_profit'].mean())

print(f"\n   Exit Strategy:")
print(f"      - Typical hold time: ~{median_hold:.0f} hours")
print(f"      - Exit when RSI-7 hits: {median_exit_rsi:.0f} (median)")
print(f"      - Capture {avg_capture_ratio*100:.0f}% of peak profit")
print(f"      - For big winners (>5%): Hold {big_winners['hold_hours'].mean():.0f}h avg")
print(f"      - For small winners (<5%): Hold {small_winners['hold_hours'].mean():.0f}h avg")

print(f"\n3️⃣  ADAPTIVE TP RULES:")

if len(big_winners) > 0 and len(small_winners) > 0:
    print(f"\n   If momentum strong:")
    print(f"      - TP: {big_winners['profit_pct'].median():.1f}% (median big winner)")
    print(f"      - Max hold: {big_winners['hold_hours'].max():.0f}h")

    print(f"\n   If momentum weak:")
    print(f"      - TP: {small_winners['profit_pct'].median():.1f}% (median small winner)")
    print(f"      - Max hold: {small_winners['hold_hours'].max():.0f}h")

# ============================================================================
# PART 4: ITERATION 13 PARAMETERS
# ============================================================================

print("\n" + "="*80)
print("⚙️  ITERATION 13 RECOMMENDED PARAMETERS")
print("="*80)

iteration_13_params = {
    'entry_long': {
        'rsi_7_range': [int(long_rsi_q1), int(long_rsi_q3)],
        'min_stoch_d': int(long_stoch_median),
        'min_alignment': float(long_alignment_median),
        'min_momentum_1h': float(long_momentum_median),
    },
    'entry_short': {
        'rsi_7_range': [int(short_rsi_q1), int(short_rsi_q3)],
        'max_stoch_d': int(short_stoch_median),
        'max_alignment': float(short_alignment_median),
        'max_momentum_1h': float(short_momentum_median),
    },
    'exit': {
        'adaptive_tp_strong': float(big_winners['profit_pct'].median()) if len(big_winners) > 0 else 5.0,
        'adaptive_tp_weak': float(small_winners['profit_pct'].median()) if len(small_winners) > 0 else 2.5,
        'stop_loss': 0.75,
        'max_hold_hours': int(df_exits['hold_hours'].quantile(0.75)),
        'target_capture_ratio': float(avg_capture_ratio),
    }
}

print(f"\n```json")
print(json.dumps(iteration_13_params, indent=2))
print(f"```")

# Save analysis
output_data = {
    'entry_analysis': {
        'long_patterns': long_entries.to_dict('records'),
        'short_patterns': short_entries.to_dict('records'),
    },
    'exit_analysis': df_exits.to_dict('records'),
    'iteration_13_params': iteration_13_params
}

with open(data_dir / 'deep_ml_analysis_results.json', 'w') as f:
    json.dump(output_data, f, indent=2, default=str)

print(f"\n💾 Analysis saved to: deep_ml_analysis_results.json")

print("\n" + "="*80)
print("💡 KEY TAKEAWAYS FOR ITERATION 13")
print("="*80)

print(f"\n1. Your LONG entries have momentum bias (median {long_momentum_median:.1f}%)")
print(f"2. Your SHORT entries catch reversals (median momentum {short_momentum_median:.1f}%)")
print(f"3. You hold big winners {big_winners['hold_hours'].mean():.0f}h vs small {small_winners['hold_hours'].mean():.0f}h")
print(f"4. You capture {avg_capture_ratio*100:.0f}% of peak (gives back {(1-avg_capture_ratio)*100:.0f}%)")
print(f"5. Your exits cluster around RSI {median_exit_rsi:.0f}")

print("\n🚀 Ready to build Iteration 13 with these patterns!")
print("="*80 + "\n")
