#!/usr/bin/env python3
"""
Generate Multi-Timeframe EMA Ribbon Charts
Each EMA line creates gradient ribbon to price
Faster EMAs = more opacity (darker), Slower EMAs = less opacity (lighter)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.mtf_ribbon_fetcher import MTFRibbonFetcher
from reporting.mtf_ribbon_chart import MTFRibbonChart


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent / 'src' / 'strategy' / 'strategy_params.json'
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config.get('mtf_ribbon_cloud', {})


def main():
    """
    Generate ribbon charts for each timeframe
    """
    print("\n" + "="*80)
    print("MULTI-TIMEFRAME EMA RIBBON CHART GENERATOR")
    print("="*80 + "\n")

    # Load config
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

    # Focus on priority timeframes for ribbon view
    priority_timeframes = [1, 3, 5, 8, 13]  # Most useful for trading

    print(f"   Symbol: {symbol}")
    print(f"   Timeframes to chart: {priority_timeframes}")
    print(f"   EMA Periods: {len(ema_periods)} ribbons per chart")
    print(f"   Historical Data: {days_back} days")
    print(f"   ✅ Configuration loaded\n")

    # Step 1: Fetch data
    print("="*80)
    print("STEP 1: FETCHING DATA")
    print("="*80)

    fetcher = MTFRibbonFetcher(symbol=symbol)
    mtf_data = fetcher.fetch_and_calculate_all(days_back=days_back)

    if not mtf_data:
        print("❌ ERROR: Failed to fetch data")
        sys.exit(1)

    print(f"\n✅ Data fetched for {len(mtf_data)} timeframes\n")

    # Step 2: Generate COMBINED chart (all timeframes in one)
    print("="*80)
    print("STEP 2: GENERATING COMBINED CHART")
    print("="*80)

    chart_gen = MTFRibbonChart(output_dir='charts/mtf_ribbon')

    print("📊 Creating combined chart with ALL timeframes...")
    combined_fig = chart_gen.create_combined_ribbon_chart(
        mtf_data=mtf_data,
        ema_periods=ema_periods,
        symbol=symbol,
        base_timeframe=1
    )

    print(f"\n✅ Combined chart generated\n")

    # Step 3: Save combined chart
    print("="*80)
    print("STEP 3: SAVING CHART")
    print("="*80)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    combined_path = chart_gen.output_dir / f'combined_{symbol}_all_timeframes_{timestamp}.html'

    combined_fig.write_html(
        str(combined_path),
        auto_open=True,  # Auto-open this one!
        include_plotlyjs='cdn'
    )

    print(f"✅ Saved: {combined_path}")

    # Summary
    print("\n" + "="*80)
    print("✅ COMBINED RIBBON CHART COMPLETE")
    print("="*80)
    print(f"📊 Chart: ALL {len(mtf_data)} timeframes combined")
    print(f"📁 Location: {combined_path}")
    print(f"\n🎨 Features:")
    print(f"   ✅ All 9 timeframes overlaid in ONE chart")
    print(f"   ✅ {len(ema_periods)} EMA ribbons per timeframe")
    print(f"   ✅ Total: {len(mtf_data) * len(ema_periods)} ribbons!")
    print(f"\n💡 How to read:")
    print(f"   - DARKER areas = Faster EMAs (5, 8, 10)")
    print(f"   - LIGHTER areas = Slower EMAs (100, 145, 200)")
    print(f"   - GREEN = Price above EMAs (support)")
    print(f"   - RED = Price below EMAs (resistance)")
    print(f"   - YELLOW = NATURAL OVERLAP of green+red from different TFs!")
    print(f"\n🔥 The yellow appears automatically when:")
    print(f"   - Some timeframes show green (bullish)")
    print(f"   - Other timeframes show red (bearish)")
    print(f"   - Their semi-transparent ribbons OVERLAP = YELLOW!")
    print(f"\n📖 Chart opened automatically in browser!")
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
