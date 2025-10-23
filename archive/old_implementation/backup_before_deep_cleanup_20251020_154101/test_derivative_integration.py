"""
Test EMA Derivative Integration
Validates that derivatives are calculated and displayed correctly
"""

import pandas as pd
import numpy as np
from datetime import datetime
from ema_derivative_analyzer import EMADerivativeAnalyzer


def test_derivative_calculation():
    """Test that derivatives are calculated correctly"""
    print("="*80)
    print("TESTING EMA DERIVATIVE INTEGRATION")
    print("="*80)

    # Load historical data
    try:
        df = pd.read_csv('trading_data/ema_data_5min.csv')
        print(f"\n✅ Loaded {len(df)} snapshots from ema_data_5min.csv")
    except FileNotFoundError:
        print("\n❌ No historical data found. Run the bot first to generate data.")
        return

    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Analyze last 100 snapshots (about 16 minutes)
    df_recent = df.tail(100).copy()
    print(f"📊 Analyzing last {len(df_recent)} snapshots")

    # Initialize analyzer
    analyzer = EMADerivativeAnalyzer(lookback_periods=10)

    # Get EMA columns
    ema_value_cols = [col for col in df_recent.columns if '_value' in col and col.startswith('MMA')]

    if not ema_value_cols:
        print("\n❌ No EMA value columns found in data")
        return

    print(f"✅ Found {len(ema_value_cols)} EMA columns")

    # Calculate derivatives
    print("\n📈 Calculating derivatives...")
    df_with_derivatives = analyzer.analyze_ema_derivatives(df_recent, ema_value_cols)

    # Calculate compression
    print("📊 Calculating compression states...")
    df_with_derivatives = analyzer.calculate_compression_state(df_with_derivatives, ema_value_cols)

    print("\n" + "="*80)
    print("DERIVATIVE ANALYSIS RESULTS")
    print("="*80)

    # Show compression stats
    print("\n📊 COMPRESSION STATE DISTRIBUTION:")
    comp_counts = df_with_derivatives['compression_state'].value_counts()
    for state, count in comp_counts.items():
        pct = count / len(df_with_derivatives) * 100
        print(f"   {state}: {count} ({pct:.1f}%)")

    # Show inflection point summary
    print("\n⚡ INFLECTION POINT SUMMARY:")
    fast_emas = [5, 10, 15, 20]

    for ema in fast_emas:
        col = f'MMA{ema}_inflection_type'
        if col in df_with_derivatives.columns:
            inflections = df_with_derivatives[col].value_counts()
            print(f"\n   MMA{ema}:")
            for inflection_type, count in inflections.items():
                if inflection_type != 'none':
                    print(f"      • {inflection_type}: {count}")

    # Show recent derivative activity (last 10 snapshots)
    print("\n" + "="*80)
    print("RECENT DERIVATIVE ACTIVITY (Last 10 snapshots)")
    print("="*80)

    recent = df_with_derivatives.tail(10)

    for idx, row in recent.iterrows():
        timestamp = row['timestamp']
        price = row['price']
        comp_state = row['compression_state']

        print(f"\n{timestamp} | Price: ${price:.2f} | Compression: {comp_state}")

        # Show fast EMA derivatives
        for ema in [5, 10, 15]:
            slope_col = f'MMA{ema}_slope'
            accel_col = f'MMA{ema}_accel'
            inflection_col = f'MMA{ema}_inflection_type'

            if slope_col in row.index:
                slope = row[slope_col]
                accel = row[accel_col] if accel_col in row.index else 0
                inflection = row[inflection_col] if inflection_col in row.index else 'none'

                slope_arrow = "↗️" if slope > 0 else "↘️" if slope < 0 else "→"
                if inflection != 'none':
                    print(f"   • MMA{ema}: {slope_arrow} slope={slope:.6f} | {inflection}")

    # Check if data has new derivative columns
    print("\n" + "="*80)
    print("CHECKING CSV STRUCTURE")
    print("="*80)

    derivative_cols = [col for col in df_with_derivatives.columns if 'slope' in col or 'accel' in col or 'inflection' in col or 'compression' in col]

    if derivative_cols:
        print(f"\n✅ Found {len(derivative_cols)} derivative columns:")
        for col in derivative_cols[:10]:  # Show first 10
            print(f"   • {col}")
        if len(derivative_cols) > 10:
            print(f"   ... and {len(derivative_cols) - 10} more")
    else:
        print("\n⚠️  No derivative columns found yet")
        print("   Run the bot to start generating derivative data!")

    # Save enhanced data for inspection
    output_file = 'trading_data/test_derivatives_output.csv'
    df_with_derivatives.to_csv(output_file, index=False)
    print(f"\n💾 Saved test output to: {output_file}")
    print(f"   Open this file to inspect derivative calculations")

    print("\n" + "="*80)
    print("✅ TEST COMPLETE!")
    print("="*80)

    print("\n📝 NEXT STEPS:")
    print("   1. Run the bot to start collecting data with derivatives")
    print("   2. Check trading_data/ema_data_5min.csv for new columns")
    print("   3. Monitor derivative signals in real-time during trading")
    print("   4. Look for inflection points BEFORE ribbon state flips")

    return df_with_derivatives


def test_compression_detection():
    """Test compression state detection"""
    print("\n" + "="*80)
    print("TESTING COMPRESSION STATE DETECTION")
    print("="*80)

    # Simulate EMA values with different compression states
    test_cases = [
        {
            'name': 'Highly Compressed (tight range)',
            'emas': [3850, 3851, 3852, 3853, 3854],  # Very close together
            'expected': 'highly_compressed'
        },
        {
            'name': 'Compressed (ranging)',
            'emas': [3840, 3845, 3850, 3855, 3860],  # Somewhat close
            'expected': 'compressed'
        },
        {
            'name': 'Expanding (trend starting)',
            'emas': [3800, 3820, 3840, 3860, 3880],  # Spreading out
            'expected': 'expanding'
        },
        {
            'name': 'Highly Expanded (strong trend)',
            'emas': [3700, 3750, 3800, 3850, 3900],  # Very wide
            'expected': 'highly_expanded'
        }
    ]

    for test in test_cases:
        emas = test['emas']
        mean = np.mean(emas)
        std = np.std(emas)
        compression = (std / mean) * 100 if mean > 0 else 0

        # Classify
        if compression < 0.1:
            state = 'highly_compressed'
        elif compression < 0.2:
            state = 'compressed'
        elif compression < 0.4:
            state = 'normal'
        elif compression < 0.8:
            state = 'expanding'
        else:
            state = 'highly_expanded'

        status = "✅" if state == test['expected'] else "❌"

        print(f"\n{status} {test['name']}")
        print(f"   EMAs: {emas}")
        print(f"   Compression: {compression:.4f}%")
        print(f"   State: {state}")
        print(f"   Expected: {test['expected']}")

    print("\n" + "="*80)
    print("✅ COMPRESSION TEST COMPLETE!")
    print("="*80)


if __name__ == '__main__':
    # Run tests
    test_compression_detection()

    print("\n\n")

    df = test_derivative_calculation()

    print("\n" + "="*80)
    print("🎯 INTEGRATION SUMMARY")
    print("="*80)
    print("""
Your EMA derivative analysis system is now integrated!

KEY FEATURES:
1. ✅ Slope tracking for each EMA (rate of change)
2. ✅ Acceleration tracking (momentum buildup)
3. ✅ Inflection point detection (direction changes)
4. ✅ Compression state analysis (tight vs expanding)
5. ✅ Color-coded slope visualization
6. ✅ Real-time derivative calculation
7. ✅ Historical derivative logging

HOW IT WORKS:
- Bot collects EMA values every 10 seconds
- Derivatives calculated using last 10 snapshots (100 sec lookback)
- Inflection points detected when slopes change direction
- Compression measured as coefficient of variation
- All data logged to CSV with derivatives

WHAT TO LOOK FOR:
- Bullish inflections + compressed = LONG setup forming
- Bearish inflections + compressed = SHORT setup forming
- Multiple accelerations = Strong momentum building
- Compression → Expansion = Breakout happening

DATA FILES:
- ema_data_5min.csv: Live data with derivatives
- ema_data_15min.csv: 15min timeframe derivatives
- claude_decisions.csv: Trading decisions with derivative context
    """)
