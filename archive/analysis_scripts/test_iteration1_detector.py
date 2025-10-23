#!/usr/bin/env python3
"""Test the Iteration 1 detector to see what's failing"""

import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'src'))
from strategy.entry_detector_user_pattern import EntryDetector

# Load data
data_dir = Path(__file__).parent / 'trading_data'
df_1h = pd.read_csv(data_dir / 'indicators' / 'eth_1h_full.csv')
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')

df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])

# Filter to period
start = pd.Timestamp('2025-09-21')
end = pd.Timestamp('2025-10-22')
df_1h_period = df_1h[(df_1h['timestamp'] >= start) & (df_1h['timestamp'] < end)].copy()
df_15m_period = df_15m[(df_15m['timestamp'] >= start) & (df_15m['timestamp'] < end)].copy()
df_5m_period = df_5m[(df_5m['timestamp'] >= start) & (df_5m['timestamp'] < end)].copy()

print(f"Period data: {len(df_1h_period)} 1h candles")

# Initialize detector
detector = EntryDetector(df_5m=df_5m_period, df_15m=df_15m_period)

# Test on a few candles with ribbon flips
print("\n" + "="*80)
print("TESTING DETECTOR ON SAMPLE CANDLES")
print("="*80)

# Find candles with strong alignment
for idx in range(100, min(200, len(df_1h_period))):
    row = df_1h_period.iloc[idx]

    # Check if this could be a signal
    alignment = row['alignment_pct']
    compression = row['compression_score']
    expansion = row['expansion_rate']
    long_score = row['confluence_score_long']
    short_score = row['confluence_score_short']

    if alignment >= 0.75 or alignment <= 0.25:
        print(f"\n🔍 Testing candle {idx}: {row['timestamp']}")
        print(f"   Alignment: {alignment:.3f}")
        print(f"   Compression: {compression:.1f}")
        print(f"   Expansion: {expansion:.2f}")
        print(f"   Confluence: Long={long_score:.1f}, Short={short_score:.1f}")

        # Test detector
        df_partial = df_1h_period.iloc[:idx+1].copy()
        result = detector.detect_signal(df_partial)

        print(f"   Signal: {result['signal']}")
        print(f"   Reason: {result['reason']}")
        print(f"   Filters passed: {list(result['filters_passed'].keys())}")

        if idx >= 105:  # Test a few
            break

print("\n" + "="*80)
