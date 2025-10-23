#!/usr/bin/env python3
"""
Multi-Timeframe EMA Ribbon Cloud Chart Generator
Example script to generate gradient cloud visualization
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.mtf_ribbon_fetcher import MTFRibbonFetcher
from strategy.mtf_ribbon_aggregator import MTFRibbonAggregator
from reporting.mtf_cloud_chart import MTFCloudChartGenerator


def load_config():
    """Load configuration from strategy_params.json"""
    config_path = Path(__file__).parent / 'src' / 'strategy' / 'strategy_params.json'

    with open(config_path, 'r') as f:
        config = json.load(f)

    return config.get('mtf_ribbon_cloud', {})


def main():
    """
    Main execution flow:
    1. Load configuration
    2. Fetch multi-timeframe data
    3. Aggregate into cloud data
    4. Generate and save chart
    """
    print("\n" + "="*80)
    print("MULTI-TIMEFRAME EMA RIBBON CLOUD CHART GENERATOR")
    print("="*80 + "\n")

    # Step 1: Load configuration
    print("📋 Loading configuration...")
    config = load_config()

    symbol = 'ETH'
    timeframes = config.get('timeframes', [1, 2, 3, 5, 8, 13, 21, 34, 55])
    ema_periods = config.get('ema_periods', [
        5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50,
        55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115,
        120, 125, 130, 135, 140, 145, 200
    ])
    days_back = config.get('days_back', 30)
    base_timeframe = config.get('base_timeframe', 1)

    print(f"   Symbol: {symbol}")
    print(f"   Timeframes: {timeframes}")
    print(f"   EMA Periods: {len(ema_periods)} periods")
    print(f"   Total EMA Lines: {len(timeframes)} × {len(ema_periods)} = {len(timeframes) * len(ema_periods)}")
    print(f"   Historical Data: {days_back} days")
    print(f"   ✅ Configuration loaded\n")

    # Step 2: Fetch multi-timeframe data
    print("="*80)
    print("STEP 1: FETCHING MULTI-TIMEFRAME DATA")
    print("="*80)

    fetcher = MTFRibbonFetcher(symbol=symbol)
    mtf_data = fetcher.fetch_and_calculate_all(days_back=days_back)

    if not mtf_data:
        print("❌ ERROR: Failed to fetch multi-timeframe data")
        sys.exit(1)

    print(f"\n✅ Successfully fetched and calculated EMAs for {len(mtf_data)} timeframes\n")

    # Step 3: Aggregate into cloud data
    print("="*80)
    print("STEP 2: AGGREGATING INTO CLOUD DATA")
    print("="*80)

    aggregator = MTFRibbonAggregator(
        ema_periods=ema_periods,
        smoothing_window=config.get('smoothing_window', 3),
        boundary_method=config.get('boundary_method', 'minmax'),
        percentile_lower=config.get('percentile_lower', 10),
        percentile_upper=config.get('percentile_upper', 90)
    )

    aggregated_df = aggregator.aggregate_full(mtf_data, base_tf_minutes=base_timeframe)

    if aggregated_df is None or aggregated_df.empty:
        print("❌ ERROR: Failed to aggregate cloud data")
        sys.exit(1)

    # Print summary statistics
    aggregator.print_summary(aggregated_df)

    # Step 4: Generate chart
    print("="*80)
    print("STEP 3: GENERATING VISUALIZATION")
    print("="*80)

    chart_generator = MTFCloudChartGenerator(
        output_dir=config.get('output_dir', 'charts/mtf_cloud'),
        opacity_base=config.get('cloud_opacity_base', 0.15),
        num_gradient_layers=config.get('num_gradient_layers', 9),
        show_individual_layers=config.get('show_individual_layers', True)
    )

    output_path = chart_generator.create_and_save(
        aggregated_df=aggregated_df,
        timeframes=timeframes,
        ema_periods=ema_periods,
        symbol=symbol,
        auto_open=config.get('auto_open', False)
    )

    # Final summary
    print("\n" + "="*80)
    print("✅ CHART GENERATION COMPLETE")
    print("="*80)
    print(f"📊 Chart saved to: {output_path}")
    print(f"📈 Timeframes visualized: {timeframes}")
    print(f"📉 Total EMA lines: {len(timeframes) * len(ema_periods)}")
    print(f"🕐 Candles: {len(aggregated_df)}")
    print(f"💚 Average cloud strength: {aggregated_df['cloud_strength'].mean():.1f}/100")
    print("\nTo view the chart:")
    print(f"   open {output_path}")
    print("\nTo regenerate with different settings:")
    print("   1. Edit src/strategy/strategy_params.json under 'mtf_ribbon_cloud'")
    print("   2. Run: python3 generate_mtf_cloud_chart.py")
    print("="*80 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
