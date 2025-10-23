#!/usr/bin/env python3
"""
Add Ribbon Analysis to Existing Indicator Data

Adds:
- compression_score (0-100)
- expansion_rate
- ribbon_flip (bullish_flip, bearish_flip, none)
- alignment_pct (0-1)
- compression_breakout
- ribbon_trend_strength
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategy.ribbon_analyzer import RibbonAnalyzer


def main():
    """Add ribbon analysis to indicator data"""
    # File paths
    data_file = Path(__file__).parent.parent / 'trading_data' / 'indicators' / 'eth_1h_full.csv'

    if not data_file.exists():
        print(f"❌ Data file not found: {data_file}")
        print("   Run: python3 scripts/process_indicators.py first")
        sys.exit(1)

    print("="*80)
    print("ADDING RIBBON ANALYSIS TO INDICATOR DATA")
    print("="*80)

    # Load data
    print(f"\n📊 Loading data: {data_file}")
    df = pd.read_csv(data_file)
    print(f"   Loaded {len(df)} candles with {len(df.columns)} columns")

    # Check if ribbon analysis already exists
    if 'compression_score' in df.columns:
        print("\n⚠️  Ribbon analysis already exists in data")
        response = input("   Recalculate anyway? [y/N]: ")
        if response.lower() != 'y':
            print("   Skipping ribbon analysis")
            sys.exit(0)

        # Remove existing ribbon columns
        ribbon_cols = ['compression_score', 'expansion_rate', 'ribbon_flip',
                      'alignment_pct', 'compression_breakout', 'ribbon_trend_strength']
        df = df.drop(columns=[c for c in ribbon_cols if c in df.columns], errors='ignore')
        print("   Removed existing ribbon columns")

    # Create ribbon analyzer
    print("\n🎀 Initializing ribbon analyzer...")
    analyzer = RibbonAnalyzer()

    # Add ribbon analysis
    df = analyzer.analyze_all(df)

    # Save results
    backup_file = data_file.parent / f"{data_file.stem}_backup.csv"
    print(f"\n💾 Creating backup: {backup_file}")
    import shutil
    shutil.copy(data_file, backup_file)

    print(f"\n💾 Saving updated data: {data_file}")
    df.to_csv(data_file, index=False)
    print(f"   Saved {len(df)} candles with {len(df.columns)} columns")

    # Show summary
    print("\n" + "="*80)
    print("RIBBON ANALYSIS SUMMARY")
    print("="*80)

    print(f"\nCompression Score:")
    print(f"  Min: {df['compression_score'].min():.1f}")
    print(f"  Max: {df['compression_score'].max():.1f}")
    print(f"  Mean: {df['compression_score'].mean():.1f}")
    print(f"  High compression (>70): {(df['compression_score'] > 70).sum()} candles ({(df['compression_score'] > 70).sum()/len(df)*100:.1f}%)")

    print(f"\nExpansion Rate:")
    print(f"  Min: {df['expansion_rate'].min():.1f}")
    print(f"  Max: {df['expansion_rate'].max():.1f}")
    print(f"  Mean: {df['expansion_rate'].mean():.1f}")
    print(f"  Strong expansion (>8): {(df['expansion_rate'] > 8).sum()} candles ({(df['expansion_rate'] > 8).sum()/len(df)*100:.1f}%)")

    print(f"\nRibbon Flips:")
    print(f"  Bullish flips: {(df['ribbon_flip'] == 'bullish_flip').sum()}")
    print(f"  Bearish flips: {(df['ribbon_flip'] == 'bearish_flip').sum()}")
    print(f"  Total flips: {(df['ribbon_flip'] != 'none').sum()}")

    print(f"\nCompression Breakouts:")
    print(f"  Bullish breakouts: {(df['compression_breakout'] == 'bullish_breakout').sum()}")
    print(f"  Bearish breakouts: {(df['compression_breakout'] == 'bearish_breakout').sum()}")
    print(f"  Total breakouts: {(df['compression_breakout'] != 'none').sum()}")

    print(f"\nAlignment:")
    print(f"  Strongly bullish (>85%): {(df['alignment_pct'] > 0.85).sum()} candles")
    print(f"  Strongly bearish (<15%): {(df['alignment_pct'] < 0.15).sum()} candles")
    print(f"  Neutral (30-70%): {((df['alignment_pct'] >= 0.3) & (df['alignment_pct'] <= 0.7)).sum()} candles")

    print("\n✅ Done! Ribbon analysis added to indicator data.")


if __name__ == '__main__':
    main()
