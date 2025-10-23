#!/usr/bin/env python3
"""
Process all fetched data through the indicator pipeline

Adds RSI, MACD, VWAP, Volume analysis, and important EMA crossovers
to all timeframe data files
"""

import sys
from pathlib import Path
import pandas as pd
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from indicators.indicator_pipeline import IndicatorPipeline


def process_all_timeframes():
    """Process all timeframe files through indicator pipeline"""

    print("="*80)
    print("PROCESSING ALL TIMEFRAMES THROUGH INDICATOR PIPELINE")
    print("="*80)

    timeframes = ['1m', '3m', '5m', '15m', '30m', '1h']
    symbol = 'eth'
    raw_dir = 'trading_data/raw'
    output_dir = 'trading_data/indicators'

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize pipeline
    pipeline = IndicatorPipeline()

    for tf in timeframes:
        input_file = f'{raw_dir}/{symbol}_historical_{tf}.csv'
        output_file = f'{output_dir}/{symbol}_{tf}_full.csv'

        if not os.path.exists(input_file):
            print(f"\n⚠️  Skipping {tf} - file not found: {input_file}")
            continue

        print(f"\n{'='*80}")
        print(f"Processing {tf} timeframe")
        print(f"{'='*80}")

        try:
            # Load data
            print(f"\n📂 Loading {input_file}...")
            df = pd.read_csv(input_file)
            print(f"   ✅ Loaded {len(df)} rows")

            # Process through pipeline
            df = pipeline.calculate_all(df)

            # Save with all indicators
            print(f"\n💾 Saving to {output_file}...")
            df.to_csv(output_file, index=False)

            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"   ✅ Saved {len(df)} rows ({file_size:.1f} MB)")
            print(f"   📊 Total columns: {len(df.columns)}")

        except Exception as e:
            print(f"\n❌ Error processing {tf}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'='*80}")
    print("✅ ALL TIMEFRAMES PROCESSED")
    print(f"{'='*80}")
    print(f"\n📂 Output directory: {output_dir}/")
    print(f"\n📋 Files created:")
    for tf in timeframes:
        output_file = f'{output_dir}/{symbol}_{tf}_full.csv'
        if os.path.exists(output_file):
            size = os.path.getsize(output_file) / (1024 * 1024)
            print(f"   • {symbol}_{tf}_full.csv ({size:.1f} MB)")


if __name__ == '__main__':
    process_all_timeframes()
