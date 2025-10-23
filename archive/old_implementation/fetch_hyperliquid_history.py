#!/usr/bin/env python3
"""
Fetch Historical Data from Hyperliquid API
Downloads OHLCV candlestick data for multiple timeframes and calculates EMAs
"""

import csv
import os
import time
from datetime import datetime, timedelta
from hyperliquid.info import Info
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()


class HyperliquidDataFetcher:
    """Fetch and process historical data from Hyperliquid"""

    def __init__(self, symbol='ETH'):
        self.symbol = symbol
        self.info = Info(skip_ws=True)

    def fetch_candles(self, interval, start_time, end_time=None):
        """
        Fetch candlestick data from Hyperliquid

        Args:
            interval: '1m', '3m', '5m', '15m', '1h', etc.
            start_time: Start timestamp (ms since epoch)
            end_time: End timestamp (ms since epoch), defaults to now

        Returns:
            List of candles [{'t': timestamp, 'o': open, 'h': high, 'l': low, 'c': close, 'v': volume}, ...]
        """
        print(f"\n📊 Fetching {interval} candles for {self.symbol}...")

        if end_time is None:
            end_time = int(time.time() * 1000)

        try:
            # Hyperliquid API call
            candles = self.info.candles_snapshot(
                name=self.symbol,
                interval=interval,
                startTime=start_time,
                endTime=end_time
            )

            print(f"   ✅ Fetched {len(candles)} candles")
            return candles

        except Exception as e:
            print(f"   ❌ Error fetching candles: {e}")
            return []

    def fetch_multiple_batches(self, interval, days_back=30):
        """
        Fetch data in batches to work around 5000 candle limit

        Args:
            interval: '1m', '3m', '5m', '15m'
            days_back: How many days of history to fetch

        Returns:
            Combined list of all candles
        """
        print(f"\n🔄 Fetching {days_back} days of {interval} data in batches...")

        # Calculate interval in milliseconds
        interval_ms = {
            '1m': 60 * 1000,
            '3m': 3 * 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
        }[interval]

        # Hyperliquid limit is 5000 candles per request
        max_candles = 5000
        batch_duration_ms = max_candles * interval_ms

        # Calculate start/end times
        end_time = int(time.time() * 1000)
        start_time = end_time - (days_back * 24 * 60 * 60 * 1000)

        all_candles = []
        current_end = end_time

        batch_num = 1
        while current_end > start_time:
            current_start = max(start_time, current_end - batch_duration_ms)

            print(f"\n   Batch {batch_num}: {datetime.fromtimestamp(current_start/1000)} to {datetime.fromtimestamp(current_end/1000)}")

            candles = self.fetch_candles(interval, current_start, current_end)

            if candles:
                all_candles.extend(candles)
                print(f"   Total candles so far: {len(all_candles)}")

            current_end = current_start - interval_ms  # Move back by one interval to avoid gaps
            batch_num += 1

            # Rate limiting
            time.sleep(0.5)

        # Sort by timestamp (oldest first)
        all_candles.sort(key=lambda x: x['t'])

        print(f"\n   ✅ Total candles fetched: {len(all_candles)}")
        return all_candles

    def calculate_emas(self, candles, periods=[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]):
        """
        Calculate EMAs for given periods (28 EMAs total)

        Args:
            candles: List of candle dicts with 'c' (close) price
            periods: List of EMA periods to calculate (default: all 28 EMAs)

        Returns:
            DataFrame with all EMAs
        """
        print(f"\n📈 Calculating EMAs for {len(periods)} periods...")

        # Extract close prices
        closes = [float(c['c']) for c in candles]
        df = pd.DataFrame({'close': closes})

        # Calculate each EMA
        for period in periods:
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()

        print(f"   ✅ EMAs calculated")
        return df

    def determine_ema_colors(self, df, periods=[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]):
        """
        Determine EMA colors based on comparison to current price

        COLOR LOGIC:
        - GREEN: if current price is ABOVE the EMA (price > EMA)
        - RED: if current price is BELOW the EMA (price < EMA)
        - NEUTRAL: if price equals EMA exactly

        Args:
            df: DataFrame with EMA columns and 'close' price
            periods: List of EMA periods

        Returns:
            DataFrame with color columns added
        """
        for period in periods:
            ema_col = f'ema_{period}'
            color_col = f'ema_{period}_color'

            # Green if price ABOVE EMA, red if price BELOW EMA
            df[color_col] = np.where(
                df['close'] > df[ema_col],
                'green',
                np.where(
                    df['close'] < df[ema_col],
                    'red',
                    'neutral'
                )
            )

        return df

    def analyze_ribbon_state(self, df, periods=[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]):
        """
        Analyze ribbon state based on EMA colors

        Args:
            df: DataFrame with EMA color columns
            periods: List of EMA periods

        Returns:
            DataFrame with ribbon_state column added
        """
        # Count green and red EMAs for each row
        green_counts = []
        red_counts = []

        for idx in range(len(df)):
            green_count = sum(1 for p in periods if df.loc[idx, f'ema_{p}_color'] == 'green')
            red_count = sum(1 for p in periods if df.loc[idx, f'ema_{p}_color'] == 'red')
            green_counts.append(green_count)
            red_counts.append(red_count)

        df['green_count'] = green_counts
        df['red_count'] = red_counts

        # Determine ribbon state
        total_emas = len(periods)
        df['ribbon_state'] = np.where(
            df['green_count'] >= total_emas * 0.92,
            'all_green',
            np.where(
                df['red_count'] >= total_emas * 0.92,
                'all_red',
                np.where(
                    df['green_count'] >= total_emas * 0.75,
                    'mixed_green',
                    np.where(
                        df['red_count'] >= total_emas * 0.75,
                        'mixed_red',
                        'mixed'
                    )
                )
            )
        )

        return df

    def detect_ema_crossovers(self, df, cross_pairs=[(5, 10), (10, 20), (20, 50), (50, 100)]):
        """
        Detect EMA crossovers for multiple pairs

        Args:
            df: DataFrame with EMA columns
            cross_pairs: List of (fast_ema, slow_ema) tuples to check

        Returns:
            DataFrame with crossover columns added
        """
        print(f"\n🔀 Detecting EMA crossovers for {len(cross_pairs)} pairs...")

        for fast, slow in cross_pairs:
            fast_col = f'ema_{fast}'
            slow_col = f'ema_{slow}'
            cross_col = f'ema_cross_{fast}_{slow}'

            # Check if EMAs exist
            if fast_col not in df.columns or slow_col not in df.columns:
                continue

            # Determine position (fast above or below slow)
            df[f'ema_pos_{fast}_{slow}'] = np.where(df[fast_col] > df[slow_col], 'above', 'below')

            # Detect crossovers by comparing current and previous position
            prev_pos = df[f'ema_pos_{fast}_{slow}'].shift(1)

            df[cross_col] = 'none'
            # Golden cross: fast crosses above slow (bullish)
            df.loc[(df[f'ema_pos_{fast}_{slow}'] == 'above') & (prev_pos == 'below'), cross_col] = 'golden_cross'
            # Death cross: fast crosses below slow (bearish)
            df.loc[(df[f'ema_pos_{fast}_{slow}'] == 'below') & (prev_pos == 'above'), cross_col] = 'death_cross'

        print(f"   ✅ Crossovers detected")
        return df

    def save_to_csv(self, candles, df, output_file, periods=[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]):
        """
        Save processed data to CSV in bot-compatible format

        Args:
            candles: Original candle data
            df: DataFrame with EMAs and analysis
            output_file: Output CSV file path
            periods: List of EMA periods
        """
        print(f"\n💾 Saving to {output_file}...")

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Build output rows
        rows = []
        for i, candle in enumerate(candles):
            # Skip rows where EMAs haven't been calculated yet (NaN)
            if pd.isna(df.loc[i, 'ema_5']):
                continue

            row = {
                'timestamp': datetime.fromtimestamp(candle['t'] / 1000).isoformat(),
                'open': candle['o'],
                'high': candle['h'],
                'low': candle['l'],
                'close': candle['c'],
                'volume': candle['v'],
                'price': candle['c'],
                'ribbon_state': df.loc[i, 'ribbon_state']
            }

            # Add all EMAs
            for period in periods:
                row[f'MMA{period}_value'] = df.loc[i, f'ema_{period}']
                row[f'MMA{period}_color'] = df.loc[i, f'ema_{period}_color']
                row[f'MMA{period}_intensity'] = 'normal'

            # Add EMA crossovers
            cross_pairs = [(5, 10), (10, 20), (20, 50), (50, 100)]
            for fast, slow in cross_pairs:
                cross_col = f'ema_cross_{fast}_{slow}'
                if cross_col in df.columns:
                    row[cross_col] = df.loc[i, cross_col]

            rows.append(row)

        # Write CSV
        headers = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'price', 'ribbon_state']
        for period in periods:
            headers.extend([f'MMA{period}_value', f'MMA{period}_color', f'MMA{period}_intensity'])

        # Add crossover columns
        cross_pairs = [(5, 10), (10, 20), (20, 50), (50, 100)]
        for fast, slow in cross_pairs:
            headers.append(f'ema_cross_{fast}_{slow}')

        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        print(f"   ✅ Saved {len(rows)} rows")
        print(f"   First: {rows[0]['timestamp']}")
        print(f"   Last: {rows[-1]['timestamp']}")


def main():
    print("="*80)
    print("HYPERLIQUID HISTORICAL DATA FETCHER")
    print("="*80)

    symbol = os.getenv('SYMBOL', 'ETH')
    print(f"\n📊 Symbol: {symbol}")

    # Initialize fetcher
    fetcher = HyperliquidDataFetcher(symbol=symbol)

    # Timeframes to fetch
    timeframes = ['1m', '3m', '5m', '15m']
    days_back = 30

    print(f"\n📅 Fetching {days_back} days of data for timeframes: {', '.join(timeframes)}")

    for interval in timeframes:
        print(f"\n{'='*80}")
        print(f"Processing {interval} timeframe")
        print(f"{'='*80}")

        # Fetch candles
        candles = fetcher.fetch_multiple_batches(interval, days_back=days_back)

        if not candles:
            print(f"   ⚠️  No candles fetched for {interval}, skipping...")
            continue

        # Calculate EMAs
        df = fetcher.calculate_emas(candles)

        # Determine colors
        df = fetcher.determine_ema_colors(df)

        # Detect EMA crossovers
        df = fetcher.detect_ema_crossovers(df)

        # Analyze ribbon state
        df = fetcher.analyze_ribbon_state(df)

        # Save to CSV
        output_file = f'trading_data/{symbol.lower()}_historical_{interval}.csv'
        fetcher.save_to_csv(candles, df, output_file)

        print(f"\n   ✅ {interval} complete!")

    print(f"\n{'='*80}")
    print("✅ ALL TIMEFRAMES COMPLETE!")
    print(f"{'='*80}")
    print(f"\n📂 Data saved to: trading_data/")
    print(f"\n📋 Next steps:")
    print(f"   1. Review the CSV files in trading_data/")
    print(f"   2. Use these files for backtesting")
    print(f"   3. Run: python3 backtest.py")


if __name__ == '__main__':
    main()
