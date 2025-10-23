#!/usr/bin/env python3
"""
Deep Analysis of User's 22 Optimal Trades
Focus on ribbon indicators and patterns we're missing
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

print("\n" + "="*80)
print("🔍 DEEP ANALYSIS: USER'S 22 OPTIMAL TRADES")
print("="*80)

# Load optimal trades
data_dir = Path(__file__).parent / 'trading_data'
with open(data_dir / 'optimal_trades.json', 'r') as f:
    optimal_data = json.load(f)

optimal_trades = optimal_data['optimal_entries']
print(f"\n✅ Loaded {len(optimal_trades)} optimal trades")

# Load 1h data with ribbon indicators
df_1h = pd.read_csv(data_dir / 'indicators' / 'eth_1h_full.csv')
df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])

print("\n" + "="*80)
print("📊 ANALYZING RIBBON INDICATORS AT EACH OPTIMAL ENTRY")
print("="*80)

results = []

for i, trade in enumerate(optimal_trades, 1):
    entry_time = pd.to_datetime(trade['timestamp'])
    direction = trade['direction']

    # Find the candle at entry time
    candle = df_1h[df_1h['timestamp'] == entry_time]

    if len(candle) == 0:
        print(f"\n❌ Trade #{i}: No candle found at {entry_time}")
        continue

    candle = candle.iloc[0]

    # Get previous candle for flip detection
    candle_idx = df_1h[df_1h['timestamp'] == entry_time].index[0]
    if candle_idx > 0:
        prev_candle = df_1h.iloc[candle_idx - 1]
        prev_alignment = prev_candle['alignment_pct']
    else:
        prev_alignment = 0.5

    # Extract key indicators
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

    # Check if ribbon flip happened
    if direction == 'long':
        ribbon_flip = (alignment_pct >= 0.75) and (prev_alignment < 0.75)
        strong_alignment = alignment_pct >= 0.80
        gap = confluence_long - confluence_short
        score = confluence_long
    else:
        ribbon_flip = (alignment_pct <= 0.25) and (prev_alignment > 0.25)
        strong_alignment = alignment_pct <= 0.20
        gap = confluence_short - confluence_long
        score = confluence_short

    result = {
        'trade_num': i,
        'timestamp': str(entry_time),
        'direction': direction,
        'alignment_pct': alignment_pct,
        'prev_alignment': prev_alignment,
        'ribbon_flip': ribbon_flip,
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

    # Print analysis
    flip_emoji = "🔄" if ribbon_flip else "⚪"
    align_emoji = "💪" if strong_alignment else "😐"

    print(f"\n{flip_emoji} Trade #{i}: {direction.upper()} @ {entry_time}")
    print(f"   Alignment: {alignment_pct:.3f} (prev: {prev_alignment:.3f})")
    print(f"   Ribbon Flip: {ribbon_flip} | Strong: {strong_alignment}")
    print(f"   Compression: {compression_score:.1f} | Expansion: {expansion_rate:.2f}")
    print(f"   Confluence: {score:.1f} (gap: {gap:.1f})")
    print(f"   RSI-14: {rsi_14:.1f} | RSI-7: {rsi_7:.1f}")
    print(f"   Volume: {volume_status} (ratio: {volume_ratio:.2f})")
    print(f"   Stoch: K={stoch_k:.1f}, D={stoch_d:.1f}")

# Convert to DataFrame for analysis
df_results = pd.DataFrame(results)

print("\n" + "="*80)
print("📊 STATISTICAL ANALYSIS")
print("="*80)

print(f"\n🔄 RIBBON FLIP PATTERNS:")
print(f"   Trades with ribbon flip: {df_results['ribbon_flip'].sum()} / {len(df_results)} ({df_results['ribbon_flip'].sum()/len(df_results)*100:.1f}%)")
print(f"   Trades with strong alignment: {df_results['strong_alignment'].sum()} / {len(df_results)} ({df_results['strong_alignment'].sum()/len(df_results)*100:.1f}%)")

print(f"\n📏 ALIGNMENT DISTRIBUTION:")
print(f"   Average: {df_results['alignment_pct'].mean():.3f}")
print(f"   Min: {df_results['alignment_pct'].min():.3f}")
print(f"   Max: {df_results['alignment_pct'].max():.3f}")
print(f"   Std: {df_results['alignment_pct'].std():.3f}")

# Group by direction
print(f"\n🎯 BY DIRECTION:")
for direction in ['long', 'short']:
    dir_data = df_results[df_results['direction'] == direction]
    if len(dir_data) > 0:
        print(f"\n   {direction.upper()} trades ({len(dir_data)}):")
        print(f"      Alignment: {dir_data['alignment_pct'].mean():.3f} ± {dir_data['alignment_pct'].std():.3f}")
        print(f"      Ribbon flips: {dir_data['ribbon_flip'].sum()} / {len(dir_data)}")
        print(f"      Compression: {dir_data['compression_score'].mean():.1f} ± {dir_data['compression_score'].std():.1f}")
        print(f"      Expansion: {dir_data['expansion_rate'].mean():.2f} ± {dir_data['expansion_rate'].std():.2f}")

print(f"\n📊 COMPRESSION & EXPANSION:")
print(f"   Compression: {df_results['compression_score'].mean():.1f} (range: {df_results['compression_score'].min():.1f} - {df_results['compression_score'].max():.1f})")
print(f"   Expansion: {df_results['expansion_rate'].mean():.2f} (range: {df_results['expansion_rate'].min():.2f} - {df_results['expansion_rate'].max():.2f})")

print(f"\n💎 CONFLUENCE SCORES:")
print(f"   Average score: {df_results['confluence_score'].mean():.1f}")
print(f"   Average gap: {df_results['confluence_gap'].mean():.1f}")
print(f"   Gap range: {df_results['confluence_gap'].min():.1f} to {df_results['confluence_gap'].max():.1f}")

print(f"\n📉 RSI PATTERNS:")
print(f"   RSI-14: {df_results['rsi_14'].mean():.1f} (range: {df_results['rsi_14'].min():.1f} - {df_results['rsi_14'].max():.1f})")
print(f"   RSI-7: {df_results['rsi_7'].mean():.1f} (range: {df_results['rsi_7'].min():.1f} - {df_results['rsi_7'].max():.1f})")

print(f"\n📊 STOCHASTIC:")
print(f"   Stoch K: {df_results['stoch_k'].mean():.1f} (range: {df_results['stoch_k'].min():.1f} - {df_results['stoch_k'].max():.1f})")
print(f"   Stoch D: {df_results['stoch_d'].mean():.1f} (range: {df_results['stoch_d'].min():.1f} - {df_results['stoch_d'].max():.1f})")

print(f"\n📦 VOLUME:")
volume_counts = df_results['volume_status'].value_counts()
for status, count in volume_counts.items():
    print(f"   {status}: {count} ({count/len(df_results)*100:.1f}%)")
print(f"   Volume ratio: {df_results['volume_ratio'].mean():.2f} (range: {df_results['volume_ratio'].min():.2f} - {df_results['volume_ratio'].max():.2f})")

# Find key discriminators
print("\n" + "="*80)
print("🔍 KEY PATTERNS IDENTIFIED")
print("="*80)

# Alignment threshold
long_trades = df_results[df_results['direction'] == 'long']
short_trades = df_results[df_results['direction'] == 'short']

if len(long_trades) > 0:
    print(f"\n📈 LONG ENTRIES:")
    print(f"   Alignment range: {long_trades['alignment_pct'].min():.3f} - {long_trades['alignment_pct'].max():.3f}")
    print(f"   {(long_trades['alignment_pct'] >= 0.75).sum()} / {len(long_trades)} were >= 0.75 ({(long_trades['alignment_pct'] >= 0.75).sum()/len(long_trades)*100:.1f}%)")
    print(f"   {(long_trades['alignment_pct'] >= 0.60).sum()} / {len(long_trades)} were >= 0.60 ({(long_trades['alignment_pct'] >= 0.60).sum()/len(long_trades)*100:.1f}%)")

if len(short_trades) > 0:
    print(f"\n📉 SHORT ENTRIES:")
    print(f"   Alignment range: {short_trades['alignment_pct'].min():.3f} - {short_trades['alignment_pct'].max():.3f}")
    print(f"   {(short_trades['alignment_pct'] <= 0.25).sum()} / {len(short_trades)} were <= 0.25 ({(short_trades['alignment_pct'] <= 0.25).sum()/len(short_trades)*100:.1f}%)")
    print(f"   {(short_trades['alignment_pct'] <= 0.40).sum()} / {len(short_trades)} were <= 0.40 ({(short_trades['alignment_pct'] <= 0.40).sum()/len(short_trades)*100:.1f}%)")

# Save results
output_file = data_dir / 'optimal_trades_ribbon_analysis.csv'
df_results.to_csv(output_file, index=False)
print(f"\n💾 Detailed analysis saved to: {output_file}")

print("\n" + "="*80)
print("✅ DEEP ANALYSIS COMPLETE!")
print("="*80)
