#!/usr/bin/env python3
"""
Quick test of data fetcher
Fetches 7 days of 5min data to verify it works
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.hyperliquid_fetcher import HyperliquidFetcher

print("Testing HyperliquidFetcher...")
print("Fetching 7 days of 5m data as a test")

fetcher = HyperliquidFetcher(symbol='ETH')

# Fetch small dataset for testing
candles = fetcher.fetch_historical_data(
    interval='5m',
    days_back=7,
    use_checkpoint=False
)

print(f"\n✅ Successfully fetched {len(candles)} candles")

if candles:
    # Calculate EMAs
    df = fetcher.calculate_emas(candles)
    df = fetcher.determine_ema_colors(df)
    df = fetcher.analyze_ribbon_state(df)
    df = fetcher.detect_ema_crossovers(df)
    
    # Save test output
    fetcher.save_to_csv(df, 'trading_data/test/eth_5m_test.csv')
    
    print(f"✅ Test successful!")
    print(f"📊 {len(df)} candles processed")
    print(f"📂 Saved to: trading_data/test/eth_5m_test.csv")
else:
    print("❌ No data fetched")
