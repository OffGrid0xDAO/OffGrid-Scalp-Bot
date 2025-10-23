#!/usr/bin/env python3
"""
Merge Backfilled EMA Data with Existing Dataset
Combines ema_backfill.csv with ema_data_5min.csv
"""

import pandas as pd
import shutil
from datetime import datetime


def merge_backfill():
    """Merge backfilled data with existing dataset"""

    print("="*80)
    print("MERGE BACKFILL DATA")
    print("="*80)

    # File paths
    main_file = 'trading_data/ema_data_5min.csv'
    backfill_file = 'trading_data/ema_backfill.csv'
    backup_file = f'trading_data/ema_data_5min_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    output_file = main_file

    # Check if backfill file exists
    try:
        with open(backfill_file, 'r') as f:
            pass
    except FileNotFoundError:
        print(f"\n❌ Backfill file not found: {backfill_file}")
        print(f"   Run auto_backfill_ema.py first to generate backfill data")
        return

    # Backup original file
    print(f"\n💾 Creating backup...")
    shutil.copy(main_file, backup_file)
    print(f"   ✅ Backup saved: {backup_file}")

    # Load datasets
    print(f"\n📂 Loading datasets...")
    print(f"   Main file: {main_file}")
    df_main = pd.read_csv(main_file, on_bad_lines='skip')
    df_main['timestamp'] = pd.to_datetime(df_main['timestamp'], errors='coerce')
    df_main = df_main.dropna(subset=['timestamp'])
    print(f"   ✅ Loaded {len(df_main)} rows from main file")

    print(f"\n   Backfill file: {backfill_file}")
    df_backfill = pd.read_csv(backfill_file)
    df_backfill['timestamp'] = pd.to_datetime(df_backfill['timestamp'], errors='coerce')
    df_backfill = df_backfill.dropna(subset=['timestamp'])
    print(f"   ✅ Loaded {len(df_backfill)} rows from backfill file")

    # Show time ranges
    print(f"\n📊 Time Ranges:")
    print(f"   Main: {df_main['timestamp'].min()} to {df_main['timestamp'].max()}")
    print(f"   Backfill: {df_backfill['timestamp'].min()} to {df_backfill['timestamp'].max()}")

    # Check for overlaps
    main_start = df_main['timestamp'].min()
    main_end = df_main['timestamp'].max()
    backfill_start = df_backfill['timestamp'].min()
    backfill_end = df_backfill['timestamp'].max()

    if backfill_start < main_end and backfill_end > main_start:
        print(f"\n⚠️  WARNING: Time ranges overlap!")
        print(f"   This may cause duplicate timestamps")
        cont = input("\n   Continue anyway? (y/n): ")
        if cont.lower() != 'y':
            print("   Merge cancelled")
            return

    # Combine datasets
    print(f"\n🔗 Merging datasets...")
    df_combined = pd.concat([df_main, df_backfill], ignore_index=True)

    # Sort by timestamp
    df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)

    # Remove duplicates (keep first occurrence)
    original_count = len(df_combined)
    df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='first')
    duplicates_removed = original_count - len(df_combined)

    if duplicates_removed > 0:
        print(f"   ⚠️  Removed {duplicates_removed} duplicate timestamps")

    print(f"   ✅ Combined dataset: {len(df_combined)} rows")

    # Analyze gaps in combined dataset
    print(f"\n🔍 Analyzing gaps in merged data...")
    gaps = []
    for i in range(1, len(df_combined)):
        time_diff = (df_combined.iloc[i]['timestamp'] - df_combined.iloc[i-1]['timestamp']).total_seconds() / 60
        if time_diff > 15:
            gaps.append({
                'start': df_combined.iloc[i-1]['timestamp'],
                'end': df_combined.iloc[i]['timestamp'],
                'duration_hours': time_diff / 60
            })

    if gaps:
        print(f"   ⚠️  Still {len(gaps)} gaps > 15 minutes:")
        for i, gap in enumerate(gaps, 1):
            print(f"     Gap #{i}: {gap['start']} to {gap['end']} ({gap['duration_hours']:.1f}h)")
    else:
        print(f"   ✅ No gaps > 15 minutes!")

    # Save merged data
    print(f"\n💾 Saving merged dataset...")
    df_combined.to_csv(output_file, index=False)
    print(f"   ✅ Saved to: {output_file}")

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Original rows: {len(df_main)}")
    print(f"   Backfill rows: {len(df_backfill)}")
    print(f"   Duplicates removed: {duplicates_removed}")
    print(f"   Final rows: {len(df_combined)}")
    print(f"   Time range: {df_combined['timestamp'].min()} to {df_combined['timestamp'].max()}")
    print(f"   Duration: {(df_combined['timestamp'].max() - df_combined['timestamp'].min()).total_seconds() / 3600:.1f} hours")

    print(f"\n✅ Merge complete!")
    print(f"   Backup: {backup_file}")
    print(f"   Merged: {output_file}")


if __name__ == '__main__':
    merge_backfill()
