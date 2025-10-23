#!/usr/bin/env python3
"""
Match user's optimal trades to nearest 1h candle
Since user trades on 5m/15m, we need to find the corresponding 1h candle
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import timedelta

print("\n" + "="*80)
print("🔍 MATCHING USER TRADES TO 1H CANDLES")
print("="*80)

# Load optimal trades
data_dir = Path(__file__).parent / 'trading_data'
with open(data_dir / 'optimal_trades.json', 'r') as f:
    optimal_data = json.load(f)

optimal_trades = optimal_data['optimal_entries']

# Load 1h data
df_1h = pd.read_csv(data_dir / 'indicators' / 'eth_1h_full.csv')
df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])

print(f"\n✅ Loaded {len(optimal_trades)} optimal trades")
print(f"✅ Loaded {len(df_1h)} 1h candles")

results = []

for i, trade in enumerate(optimal_trades, 1):
    entry_time = pd.to_datetime(trade['timestamp'])
    direction = trade['direction']

    # Find nearest 1h candle (round down to hour)
    hour_time = entry_time.floor('H')

    # Also check the next hour candle
    next_hour = hour_time + timedelta(hours=1)

    # Get both candles
    candle_current = df_1h[df_1h['timestamp'] == hour_time]
    candle_next = df_1h[df_1h['timestamp'] == next_hour]

    # Use the candle that contains this timestamp
    # If entry is at 18:30, it's DURING the 18:00-19:00 candle
    # So we should use the 19:00 candle (which closed at 19:00)
    if len(candle_next) > 0:
        candle = candle_next.iloc[0]
        matched_time = next_hour
    elif len(candle_current) > 0:
        candle = candle_current.iloc[0]
        matched_time = hour_time
    else:
        print(f"\n❌ Trade #{i}: No candle found near {entry_time}")
        continue

    # Get previous candle
    candle_idx = df_1h[df_1h['timestamp'] == matched_time].index[0]
    if candle_idx > 0:
        prev_candle = df_1h.iloc[candle_idx - 1]
        prev_alignment = prev_candle['alignment_pct']
    else:
        prev_alignment = 0.5

    # Extract indicators
    alignment_pct = candle['alignment_pct']
    compression_score = candle['compression_score']
    expansion_rate = candle['expansion_rate']
    confluence_long = candle['confluence_score_long']
    confluence_short = candle['confluence_score_short']
    rsi_14 = candle.get('rsi_14', np.nan)
    rsi_7 = candle.get('rsi_7', np.nan)
    volume_status = candle.get('volume_status', 'unknown')
    volume_ratio = candle.get('volume_ratio', np.nan)
    stoch_k = candle.get('stoch_k', np.nan)
    stoch_d = candle.get('stoch_d', np.nan)

    # Check ribbon flip
    if direction == 'long':
        ribbon_flip = (alignment_pct >= 0.75) and (prev_alignment < 0.75)
        near_flip = (alignment_pct >= 0.60)  # Looser threshold
        strong_alignment = alignment_pct >= 0.80
        gap = confluence_long - confluence_short
        score = confluence_long
    else:
        ribbon_flip = (alignment_pct <= 0.25) and (prev_alignment > 0.25)
        near_flip = (alignment_pct <= 0.40)  # Looser threshold
        strong_alignment = alignment_pct <= 0.20
        gap = confluence_short - confluence_long
        score = confluence_short

    result = {
        'trade_num': i,
        'user_entry_time': str(entry_time),
        'matched_1h_time': str(matched_time),
        'time_diff_minutes': (matched_time - entry_time).total_seconds() / 60,
        'direction': direction,
        'alignment_pct': alignment_pct,
        'prev_alignment': prev_alignment,
        'ribbon_flip': ribbon_flip,
        'near_flip': near_flip,
        'strong_alignment': strong_alignment,
        'compression_score': compression_score,
        'expansion_rate': expansion_rate,
        'confluence_gap': gap,
        'confluence_score': score,
        'rsi_14': rsi_14,
        'rsi_7': rsi_7,
        'volume_status': volume_status,
        'volume_ratio': volume_ratio,
        'stoch_k': stoch_k,
        'stoch_d': stoch_d
    }
    results.append(result)

    # Print
    flip_emoji = "🔄" if ribbon_flip else ("🟡" if near_flip else "⚪")
    print(f"\n{flip_emoji} Trade #{i}: {direction.upper()}")
    print(f"   User entry: {entry_time} → Matched 1h: {matched_time}")
    print(f"   Alignment: {alignment_pct:.3f} (prev: {prev_alignment:.3f})")
    print(f"   Flip: {ribbon_flip} | Near flip: {near_flip} | Strong: {strong_alignment}")
    print(f"   Compression: {compression_score:.1f} | Expansion: {expansion_rate:.2f}")
    print(f"   Confluence: {score:.1f} (gap: {gap:.1f})")
    print(f"   RSI-7: {rsi_7:.1f} | Volume: {volume_status} ({volume_ratio:.2f}x)")

# Analysis
df_results = pd.DataFrame(results)

print("\n" + "="*80)
print("📊 PATTERN ANALYSIS")
print("="*80)

print(f"\n🔄 RIBBON PATTERNS:")
print(f"   Exact flips (0.75/0.25): {df_results['ribbon_flip'].sum()} / {len(df_results)} ({df_results['ribbon_flip'].sum()/len(df_results)*100:.1f}%)")
print(f"   Near flips (0.60/0.40): {df_results['near_flip'].sum()} / {len(df_results)} ({df_results['near_flip'].sum()/len(df_results)*100:.1f}%)")
print(f"   Strong alignment: {df_results['strong_alignment'].sum()} / {len(df_results)} ({df_results['strong_alignment'].sum()/len(df_results)*100:.1f}%)")

print(f"\n📏 ALIGNMENT:")
for direction in ['long', 'short']:
    dir_data = df_results[df_results['direction'] == direction]
    if len(dir_data) > 0:
        print(f"   {direction.upper()} ({len(dir_data)} trades):")
        print(f"      Range: {dir_data['alignment_pct'].min():.3f} - {dir_data['alignment_pct'].max():.3f}")
        print(f"      Average: {dir_data['alignment_pct'].mean():.3f}")
        print(f"      Exact flips: {dir_data['ribbon_flip'].sum()}")
        print(f"      Near flips: {dir_data['near_flip'].sum()}")

print(f"\n📊 COMPRESSION & EXPANSION:")
print(f"   Compression: {df_results['compression_score'].mean():.1f} (range: {df_results['compression_score'].min():.1f} - {df_results['compression_score'].max():.1f})")
print(f"   Expansion: {df_results['expansion_rate'].mean():.2f} (range: {df_results['expansion_rate'].min():.2f} - {df_results['expansion_rate'].max():.2f})")

# Key finding: What % had compression > 95?
high_compression = (df_results['compression_score'] > 95).sum()
print(f"   High compression (>95): {high_compression} / {len(df_results)} ({high_compression/len(df_results)*100:.1f}%)")

print(f"\n💎 CONFLUENCE:")
print(f"   Score: {df_results['confluence_score'].mean():.1f} (range: {df_results['confluence_score'].min():.1f} - {df_results['confluence_score'].max():.1f})")
print(f"   Gap: {df_results['confluence_gap'].mean():.1f} (range: {df_results['confluence_gap'].min():.1f} - {df_results['confluence_gap'].max():.1f})")

print(f"\n📉 RSI-7:")
print(f"   Average: {df_results['rsi_7'].mean():.1f}")
print(f"   Range: {df_results['rsi_7'].min():.1f} - {df_results['rsi_7'].max():.1f}")
outside_range = ((df_results['rsi_7'] < 20) | (df_results['rsi_7'] > 55)).sum()
print(f"   Outside [20,55]: {outside_range} / {len(df_results)} ({outside_range/len(df_results)*100:.1f}%)")

print(f"\n📦 VOLUME:")
volume_counts = df_results['volume_status'].value_counts()
for status, count in volume_counts.items():
    print(f"   {status}: {count} ({count/len(df_results)*100:.1f}%)")
low_volume = (df_results['volume_ratio'] < 1.0).sum()
print(f"   Volume ratio < 1.0: {low_volume} / {len(df_results)} ({low_volume/len(df_results)*100:.1f}%)")

# Save
output_file = data_dir / 'optimal_trades_1h_matched.csv'
df_results.to_csv(output_file, index=False)
print(f"\n💾 Saved to: {output_file}")

print("\n" + "="*80)
print("✅ ANALYSIS COMPLETE!")
print("="*80)
