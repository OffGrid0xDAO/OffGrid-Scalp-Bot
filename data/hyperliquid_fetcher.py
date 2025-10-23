#!/usr/bin/env python3
"""
Hyperliquid Historical Data Fetcher - Enhanced Version
Fetches 1 year of OHLCV data across 6 timeframes with resume capability
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from hyperliquid.info import Info
from dotenv import load_dotenv

load_dotenv()


class HyperliquidFetcher:
    """
    Fetch historical OHLCV data from Hyperliquid API

    Features:
    - Batch fetching for large date ranges (overcomes 5000 candle limit)
    - Resume capability with checkpoints
    - Support for 6 timeframes: 1m, 3m, 5m, 15m, 30m, 1h
    - Up to 1 year of historical data
    - Progress tracking and error handling
    """

    # Timeframe intervals in milliseconds
    INTERVALS_MS = {
        '1m': 60 * 1000,
        '3m': 3 * 60 * 1000,
        '5m': 5 * 60 * 1000,
        '15m': 15 * 60 * 1000,
        '30m': 30 * 60 * 1000,
        '1h': 60 * 60 * 1000,
    }

    # API limits
    MAX_CANDLES_PER_REQUEST = 5000
    RATE_LIMIT_DELAY_SECONDS = 1.0  # Delay between batches

    def __init__(self, symbol: str = 'ETH', checkpoint_dir: str = 'trading_data/.checkpoints'):
        """
        Initialize fetcher

        Args:
            symbol: Trading symbol (e.g., 'ETH', 'BTC')
            checkpoint_dir: Directory for checkpoint files
        """
        self.symbol = symbol
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.info = Info(skip_ws=True)

    def fetch_candles(self, interval: str, start_time: int, end_time: int) -> List[Dict]:
        """
        Fetch single batch of candles from Hyperliquid

        Args:
            interval: Timeframe ('1m', '3m', '5m', '15m', '30m', '1h')
            start_time: Start timestamp (milliseconds)
            end_time: End timestamp (milliseconds)

        Returns:
            List of candle dictionaries with keys: t, o, h, l, c, v
        """
        try:
            candles = self.info.candles_snapshot(
                name=self.symbol,
                interval=interval,
                startTime=start_time,
                endTime=end_time
            )
            return candles if candles else []

        except Exception as e:
            print(f"   ❌ Error fetching candles: {e}")
            return []

    def fetch_historical_data(
        self,
        interval: str,
        days_back: int = 365,
        use_checkpoint: bool = True
    ) -> List[Dict]:
        """
        Fetch historical data with batch support and resume capability

        Args:
            interval: Timeframe ('1m', '3m', '5m', '15m', '30m', '1h')
            days_back: Number of days to fetch (max 365)
            use_checkpoint: Use checkpoint for resume capability

        Returns:
            List of all candles fetched
        """
        print(f"\n🔄 Fetching {days_back} days of {interval} data...")

        # Check for existing checkpoint
        checkpoint_file = self.checkpoint_dir / f"{self.symbol}_{interval}_checkpoint.json"
        if use_checkpoint and checkpoint_file.exists():
            print(f"   📂 Found checkpoint, resuming...")
            checkpoint = self.load_checkpoint(checkpoint_file)
            all_candles = checkpoint['candles']
            start_from_batch = checkpoint['last_batch'] + 1
            total_batches = checkpoint['total_batches']
        else:
            all_candles = []
            start_from_batch = 1
            total_batches = self._calculate_total_batches(interval, days_back)

        # Calculate time range
        interval_ms = self.INTERVALS_MS[interval]
        end_time = int(time.time() * 1000)
        start_time = end_time - (days_back * 24 * 60 * 60 * 1000)

        # Calculate batch parameters
        batch_duration_ms = self.MAX_CANDLES_PER_REQUEST * interval_ms

        current_end = end_time
        batch_num = 1

        # Skip already fetched batches
        if start_from_batch > 1:
            skip_duration = (start_from_batch - 1) * batch_duration_ms
            current_end = end_time - skip_duration
            batch_num = start_from_batch

        # Fetch in batches
        while current_end > start_time and batch_num <= total_batches:
            current_start = max(start_time, current_end - batch_duration_ms)

            print(f"   Batch {batch_num}/{total_batches}: "
                  f"{datetime.fromtimestamp(current_start/1000).strftime('%Y-%m-%d %H:%M')} to "
                  f"{datetime.fromtimestamp(current_end/1000).strftime('%Y-%m-%d %H:%M')}")

            # Fetch batch
            candles = self.fetch_candles(interval, current_start, current_end)

            if candles:
                all_candles.extend(candles)
                print(f"   ✅ Fetched {len(candles)} candles | Total: {len(all_candles)}")
            else:
                print(f"   ⚠️  No data for this batch")

            # Save checkpoint every 10 batches
            if batch_num % 10 == 0 and use_checkpoint:
                self.save_checkpoint(
                    checkpoint_file,
                    all_candles,
                    batch_num,
                    total_batches
                )
                print(f"   💾 Checkpoint saved")

            # Move to next batch
            current_end = current_start - interval_ms
            batch_num += 1

            # Rate limiting
            time.sleep(self.RATE_LIMIT_DELAY_SECONDS)

        # Remove duplicates and sort
        all_candles = self._deduplicate_candles(all_candles)
        all_candles.sort(key=lambda x: x['t'])

        # Clean up checkpoint
        if use_checkpoint and checkpoint_file.exists():
            checkpoint_file.unlink()

        print(f"\n   ✅ Total candles fetched: {len(all_candles)}")
        if all_candles:
            first_time = datetime.fromtimestamp(all_candles[0]['t'] / 1000)
            last_time = datetime.fromtimestamp(all_candles[-1]['t'] / 1000)
            print(f"   📅 Range: {first_time.strftime('%Y-%m-%d')} to {last_time.strftime('%Y-%m-%d')}")

        return all_candles

    def _calculate_total_batches(self, interval: str, days_back: int) -> int:
        """Calculate total number of batches needed"""
        interval_ms = self.INTERVALS_MS[interval]
        total_duration_ms = days_back * 24 * 60 * 60 * 1000
        batch_duration_ms = self.MAX_CANDLES_PER_REQUEST * interval_ms
        return int(np.ceil(total_duration_ms / batch_duration_ms))

    def _deduplicate_candles(self, candles: List[Dict]) -> List[Dict]:
        """Remove duplicate candles based on timestamp"""
        seen_timestamps = set()
        unique_candles = []

        for candle in candles:
            t = candle['t']
            if t not in seen_timestamps:
                seen_timestamps.add(t)
                unique_candles.append(candle)

        return unique_candles

    def save_checkpoint(
        self,
        checkpoint_file: Path,
        candles: List[Dict],
        last_batch: int,
        total_batches: int
    ):
        """Save progress checkpoint"""
        checkpoint = {
            'symbol': self.symbol,
            'candles': candles,
            'last_batch': last_batch,
            'total_batches': total_batches,
            'saved_at': datetime.now().isoformat()
        }

        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)

    def load_checkpoint(self, checkpoint_file: Path) -> Dict:
        """Load progress checkpoint"""
        with open(checkpoint_file, 'r') as f:
            return json.load(f)

    def calculate_emas(
        self,
        candles: List[Dict],
        periods: List[int] = None
    ) -> pd.DataFrame:
        """
        Calculate EMAs for all periods

        Args:
            candles: List of candle dictionaries
            periods: List of EMA periods (default: all 28 EMAs)

        Returns:
            DataFrame with EMA columns
        """
        if periods is None:
            # Include all EMAs needed for important crossovers:
            # 8/21 (Fibonacci), 9/21 (Short-term), 12/26 (MACD), 20/50 (Intermediate), 50/200 (Golden/Death)
            periods = [5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
                      85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 200]

        print(f"\n📈 Calculating {len(periods)} EMAs...")

        # Create DataFrame with OHLCV data
        df = pd.DataFrame([
            {
                'timestamp': c['t'],
                'open': float(c['o']),
                'high': float(c['h']),
                'low': float(c['l']),
                'close': float(c['c']),
                'volume': float(c['v'])
            }
            for c in candles
        ])

        # Calculate EMAs
        for period in periods:
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()

        print(f"   ✅ EMAs calculated")
        return df

    def determine_ema_colors(
        self,
        df: pd.DataFrame,
        periods: List[int] = None
    ) -> pd.DataFrame:
        """
        Determine EMA colors based on price position

        GREEN: price > EMA (bullish)
        RED: price < EMA (bearish)
        NEUTRAL: price == EMA

        Args:
            df: DataFrame with EMA columns
            periods: List of EMA periods

        Returns:
            DataFrame with color columns added
        """
        if periods is None:
            # Include all EMAs needed for important crossovers:
            # 8/21 (Fibonacci), 9/21 (Short-term), 12/26 (MACD), 20/50 (Intermediate), 50/200 (Golden/Death)
            periods = [5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
                      85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 200]

        for period in periods:
            ema_col = f'ema_{period}'
            color_col = f'ema_{period}_color'

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

    def analyze_ribbon_state(
        self,
        df: pd.DataFrame,
        periods: List[int] = None
    ) -> pd.DataFrame:
        """
        Analyze EMA ribbon state

        States:
        - all_green: 85%+ EMAs are green
        - mixed_green: 65-85% EMAs are green
        - mixed: 35-65% mixed
        - mixed_red: 65-85% EMAs are red
        - all_red: 85%+ EMAs are red

        Args:
            df: DataFrame with EMA color columns
            periods: List of EMA periods

        Returns:
            DataFrame with ribbon_state column
        """
        if periods is None:
            # Include all EMAs needed for important crossovers:
            # 8/21 (Fibonacci), 9/21 (Short-term), 12/26 (MACD), 20/50 (Intermediate), 50/200 (Golden/Death)
            periods = [5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
                      85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 200]

        # Count green/red EMAs per row
        green_counts = []
        for idx in range(len(df)):
            green_count = sum(
                1 for p in periods
                if df.loc[idx, f'ema_{p}_color'] == 'green'
            )
            green_counts.append(green_count)

        df['green_count'] = green_counts
        total_emas = len(periods)
        df['alignment_pct'] = df['green_count'] / total_emas

        # Determine ribbon state
        df['ribbon_state'] = np.where(
            df['alignment_pct'] >= 0.85,
            'all_green',
            np.where(
                df['alignment_pct'] <= 0.15,
                'all_red',
                np.where(
                    df['alignment_pct'] >= 0.65,
                    'mixed_green',
                    np.where(
                        df['alignment_pct'] <= 0.35,
                        'mixed_red',
                        'mixed'
                    )
                )
            )
        )

        return df

    def detect_ema_crossovers(
        self,
        df: pd.DataFrame,
        cross_pairs: List[tuple] = None
    ) -> pd.DataFrame:
        """
        Detect EMA crossovers (golden/death crosses)

        Args:
            df: DataFrame with EMA columns
            cross_pairs: List of (fast_period, slow_period) tuples

        Returns:
            DataFrame with crossover columns
        """
        if cross_pairs is None:
            # Important crossover pairs:
            cross_pairs = [
                (5, 10),    # Fast scalping
                (10, 20),   # Scalping/day trading
                (8, 21),    # Fibonacci-based
                (9, 21),    # Short-term/scalping
                (12, 26),   # MACD default (swing trading)
                (20, 50),   # Intermediate (swing trading)
                (50, 100),  # Medium-term
                (50, 200),  # Golden/Death cross (institutional)
            ]

        print(f"\n🔀 Detecting {len(cross_pairs)} EMA crossover pairs...")

        for fast, slow in cross_pairs:
            fast_col = f'ema_{fast}'
            slow_col = f'ema_{slow}'
            cross_col = f'ema_cross_{fast}_{slow}'

            if fast_col not in df.columns or slow_col not in df.columns:
                continue

            # Determine position
            df[f'_pos_{fast}_{slow}'] = np.where(
                df[fast_col] > df[slow_col],
                'above',
                'below'
            )

            # Detect crossovers
            prev_pos = df[f'_pos_{fast}_{slow}'].shift(1)

            df[cross_col] = 'none'
            # Golden cross: fast crosses above slow
            df.loc[
                (df[f'_pos_{fast}_{slow}'] == 'above') & (prev_pos == 'below'),
                cross_col
            ] = 'golden_cross'
            # Death cross: fast crosses below slow
            df.loc[
                (df[f'_pos_{fast}_{slow}'] == 'below') & (prev_pos == 'above'),
                cross_col
            ] = 'death_cross'

            # Clean up temp column
            df.drop(columns=[f'_pos_{fast}_{slow}'], inplace=True)

        print(f"   ✅ Crossovers detected")
        return df

    def save_to_csv(
        self,
        df: pd.DataFrame,
        output_file: str,
        periods: List[int] = None
    ):
        """
        Save processed data to CSV

        Args:
            df: DataFrame with all indicators
            output_file: Output file path
            periods: List of EMA periods
        """
        if periods is None:
            # Include all EMAs needed for important crossovers:
            # 8/21 (Fibonacci), 9/21 (Short-term), 12/26 (MACD), 20/50 (Intermediate), 50/200 (Golden/Death)
            periods = [5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
                      85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 200]

        print(f"\n💾 Saving to {output_file}...")

        # Create output directory
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Prepare output DataFrame
        output_df = df.copy()

        # Convert timestamp to ISO format
        output_df['timestamp'] = pd.to_datetime(
            output_df['timestamp'],
            unit='ms'
        ).dt.strftime('%Y-%m-%dT%H:%M:%S')

        # Add price column (same as close)
        output_df['price'] = output_df['close']

        # Rename EMA columns to MMA format (for compatibility)
        rename_dict = {}
        for period in periods:
            rename_dict[f'ema_{period}'] = f'MMA{period}_value'
            rename_dict[f'ema_{period}_color'] = f'MMA{period}_color'
            # Add intensity column (placeholder for now)
            output_df[f'MMA{period}_intensity'] = 'normal'

        output_df.rename(columns=rename_dict, inplace=True)

        # Select columns in correct order
        base_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                     'price', 'ribbon_state']

        ema_cols = []
        for period in periods:
            ema_cols.extend([
                f'MMA{period}_value',
                f'MMA{period}_color',
                f'MMA{period}_intensity'
            ])

        cross_cols = [col for col in output_df.columns if col.startswith('ema_cross_')]

        all_cols = base_cols + ema_cols + cross_cols

        # Filter to only existing columns
        final_cols = [col for col in all_cols if col in output_df.columns]

        # Save CSV
        output_df[final_cols].to_csv(output_file, index=False)

        print(f"   ✅ Saved {len(output_df)} rows")
        print(f"   📅 First: {output_df['timestamp'].iloc[0]}")
        print(f"   📅 Last: {output_df['timestamp'].iloc[-1]}")


def main():
    """Main execution function"""
    print("=" * 80)
    print("HYPERLIQUID HISTORICAL DATA FETCHER - ENHANCED")
    print("=" * 80)

    # Configuration
    symbol = os.getenv('SYMBOL', 'ETH')
    days_back = int(os.getenv('DAYS_BACK', '365'))  # 1 year
    timeframes = os.getenv('TIMEFRAMES', '1m,3m,5m,15m,30m,1h').split(',')

    print(f"\n📊 Symbol: {symbol}")
    print(f"📅 History: {days_back} days")
    print(f"⏱️  Timeframes: {', '.join(timeframes)}")

    # Initialize fetcher
    fetcher = HyperliquidFetcher(symbol=symbol)

    # EMA periods (all 28)
    ema_periods = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
                   85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]

    # Process each timeframe
    for interval in timeframes:
        print(f"\n{'=' * 80}")
        print(f"Processing {interval} timeframe")
        print(f"{'=' * 80}")

        try:
            # Fetch candles
            candles = fetcher.fetch_historical_data(
                interval=interval,
                days_back=days_back,
                use_checkpoint=True
            )

            if not candles:
                print(f"   ⚠️  No candles fetched for {interval}, skipping...")
                continue

            # Calculate EMAs
            df = fetcher.calculate_emas(candles, periods=ema_periods)

            # Determine EMA colors
            df = fetcher.determine_ema_colors(df, periods=ema_periods)

            # Analyze ribbon state
            df = fetcher.analyze_ribbon_state(df, periods=ema_periods)

            # Detect crossovers
            df = fetcher.detect_ema_crossovers(df)

            # Save to CSV
            output_file = f'trading_data/raw/{symbol.lower()}_historical_{interval}.csv'
            fetcher.save_to_csv(df, output_file, periods=ema_periods)

            print(f"\n   ✅ {interval} complete!")

        except Exception as e:
            print(f"\n   ❌ Error processing {interval}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'=' * 80}")
    print("✅ ALL TIMEFRAMES COMPLETE!")
    print(f"{'=' * 80}")
    print(f"\n📂 Data saved to: trading_data/raw/")
    print(f"\n📋 Next steps:")
    print(f"   1. Review CSV files in trading_data/raw/")
    print(f"   2. Run indicator pipeline to add RSI, MACD, VWAP, Volume")
    print(f"   3. Convert to Parquet + SQLite for better performance")
    print(f"   4. Begin optimal trade detection")


if __name__ == '__main__':
    main()
