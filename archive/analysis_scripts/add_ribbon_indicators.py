#!/usr/bin/env python3
"""
Add Ribbon Indicators to Existing Data

Adds compression_score, expansion_rate, alignment_pct, and ribbon_flip
to the existing indicator CSV files for 1h, 15m, and 5m timeframes.
"""

import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / 'src'))
from strategy.ribbon_analyzer import RibbonAnalyzer

print("\n" + "="*80)
print("🎀 ADDING RIBBON INDICATORS TO DATA")
print("="*80)

data_dir = Path(__file__).parent / 'trading_data' / 'indicators'

# Files to process
files = {
    'eth_1h_full.csv': '1h',
    'eth_15m_full.csv': '15m',
    'eth_5m_full.csv': '5m'
}

analyzer = RibbonAnalyzer()

for filename, timeframe in files.items():
    filepath = data_dir / filename

    if not filepath.exists():
        print(f"\n⚠️  File not found: {filepath}")
        continue

    print(f"\n📊 Processing {timeframe} timeframe: {filename}")

    # Load data
    df = pd.read_csv(filepath)
    print(f"   Loaded {len(df)} candles")

    # Check if MMA columns exist
    mma_cols = [col for col in df.columns if col.startswith('MMA')]
    print(f"   Found {len(mma_cols)} MMA columns")

    if len(mma_cols) == 0:
        print(f"   ❌ No MMA columns found - skipping ribbon analysis")
        continue

    # Add ribbon indicators
    print(f"   🎀 Calculating ribbon indicators...")
    df = analyzer.analyze_all(df)

    # Save back
    df.to_csv(filepath, index=False)
    print(f"   ✅ Saved updated file with ribbon indicators")

    # Show sample
    if 'alignment_pct' in df.columns:
        print(f"   📈 Alignment range: {df['alignment_pct'].min():.2f} - {df['alignment_pct'].max():.2f}")
    if 'compression_score' in df.columns:
        print(f"   📊 Compression range: {df['compression_score'].min():.1f} - {df['compression_score'].max():.1f}")
    if 'expansion_rate' in df.columns:
        print(f"   📉 Expansion range: {df['expansion_rate'].min():.1f} - {df['expansion_rate'].max():.1f}")

print("\n" + "="*80)
print("✅ RIBBON INDICATORS ADDED!")
print("="*80)
print("\n💡 You can now run backtests with ribbon flip detection!")
