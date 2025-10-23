#!/usr/bin/env python3
"""
Multi-Timeframe Ribbon Data Fetcher
Fetches and resamples data across 9 custom timeframes for EMA ribbon cloud visualization
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.hyperliquid_fetcher import HyperliquidFetcher


class MTFRibbonFetcher:
    """
    Fetches and synchronizes OHLCV data across 9 timeframes for multi-timeframe EMA ribbon analysis

    Timeframes: 1min, 2min, 3min, 5min, 8min, 13min, 21min, 34min, 55min

    Strategy:
    - Fetch 1min data from Hyperliquid API
    - Resample to create custom timeframes (2m, 8m, 13m, 21m, 34m, 55m)
    - Use native 3m and 5m data for accuracy
    - Calculate 35-period EMA ribbon on each timeframe
    """

    # Target timeframes in minutes
    TIMEFRAMES = [1, 2, 3, 5, 8, 13, 21, 34, 55]

    # EMA periods (same as existing system)
    EMA_PERIODS = [
        5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50,
        55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115,
        120, 125, 130, 135, 140, 145, 200
    ]

    def __init__(self, symbol: str = 'ETH'):
        """
        Initialize multi-timeframe fetcher

        Args:
            symbol: Trading symbol (e.g., 'ETH', 'BTC')
        """
        self.symbol = symbol
        self.fetcher = HyperliquidFetcher(symbol=symbol)

    def fetch_all_timeframes(self, days_back: int = 30) -> Dict[int, pd.DataFrame]:
        """
        Fetch data for all 9 timeframes

        Args:
            days_back: Number of days of historical data to fetch

        Returns:
            Dictionary mapping timeframe (in minutes) to DataFrame
        """
        print(f"\n{'='*70}")
        print(f"Multi-Timeframe Data Fetch - {self.symbol}")
        print(f"{'='*70}")
        print(f"Target timeframes: {self.TIMEFRAMES} minutes")
        print(f"Historical period: {days_back} days")
        print(f"{'='*70}\n")

        timeframe_data = {}

        # Step 1: Fetch native 1m data (base for resampling)
        print("📊 Fetching 1-minute base data...")
        data_1m = self._fetch_and_process('1m', days_back)
        if data_1m is not None and not data_1m.empty:
            timeframe_data[1] = data_1m
            print(f"   ✅ 1min: {len(data_1m)} candles")
        else:
            print(f"   ❌ Failed to fetch 1min data")
            return {}

        # Step 2: Fetch native 3m data
        if 3 in self.TIMEFRAMES:
            print("📊 Fetching 3-minute data...")
            data_3m = self._fetch_and_process('3m', days_back)
            if data_3m is not None and not data_3m.empty:
                timeframe_data[3] = data_3m
                print(f"   ✅ 3min: {len(data_3m)} candles")

        # Step 3: Fetch native 5m data
        if 5 in self.TIMEFRAMES:
            print("📊 Fetching 5-minute data...")
            data_5m = self._fetch_and_process('5m', days_back)
            if data_5m is not None and not data_5m.empty:
                timeframe_data[5] = data_5m
                print(f"   ✅ 5min: {len(data_5m)} candles")

        # Step 4: Resample 1m data to create custom timeframes
        print("\n🔄 Resampling to custom timeframes...")
        custom_timeframes = [2, 8, 13, 21, 34, 55]

        for tf_minutes in custom_timeframes:
            if tf_minutes in self.TIMEFRAMES:
                print(f"   Resampling {tf_minutes}min from 1min base...")
                resampled = self._resample_ohlcv(data_1m.copy(), f'{tf_minutes}T')
                if resampled is not None and not resampled.empty:
                    timeframe_data[tf_minutes] = resampled
                    print(f"   ✅ {tf_minutes}min: {len(resampled)} candles")
                else:
                    print(f"   ❌ Failed to resample {tf_minutes}min")

        print(f"\n{'='*70}")
        print(f"✅ Successfully fetched {len(timeframe_data)} timeframes")
        print(f"{'='*70}\n")

        return timeframe_data

    def _fetch_and_process(self, interval: str, days_back: int) -> pd.DataFrame:
        """
        Fetch data from Hyperliquid and convert to DataFrame

        Args:
            interval: API interval string ('1m', '3m', '5m', etc.)
            days_back: Number of days to fetch

        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Fetch historical data
            candles = self.fetcher.fetch_historical_data(
                interval=interval,
                days_back=days_back,
                use_checkpoint=False  # Disable checkpoints for speed
            )

            if not candles:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(candles)

            # Ensure proper column names (Hyperliquid API format)
            # Expected format: {'t': timestamp, 'o': open, 'h': high, 'l': low, 'c': close, 'v': volume}
            if 't' in df.columns:
                df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
                df = df.rename(columns={
                    'o': 'open',
                    'h': 'high',
                    'l': 'low',
                    'c': 'close',
                    'v': 'volume'
                })
            elif 'timestamp' not in df.columns:
                # Fallback if format is different
                df['timestamp'] = pd.to_datetime(df.index)

            # Set timestamp as index
            df = df.set_index('timestamp')

            # Keep only OHLCV columns
            ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[[col for col in ohlcv_cols if col in df.columns]]

            # Convert to numeric
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Remove any NaN rows
            df = df.dropna()

            # Sort by timestamp
            df = df.sort_index()

            return df

        except Exception as e:
            print(f"   ❌ Error fetching {interval} data: {e}")
            return None

    def _resample_ohlcv(self, df: pd.DataFrame, resample_rule: str) -> pd.DataFrame:
        """
        Resample OHLCV data to a different timeframe

        Args:
            df: DataFrame with OHLCV data (timestamp index)
            resample_rule: Pandas resample rule (e.g., '2T' for 2 minutes)

        Returns:
            Resampled DataFrame
        """
        try:
            # OHLCV aggregation rules
            resampled = df.resample(resample_rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })

            # Remove incomplete candles (last candle might be partial)
            resampled = resampled.dropna()

            return resampled

        except Exception as e:
            print(f"   ❌ Resampling error: {e}")
            return None

    def calculate_mtf_emas(self, timeframe_data: Dict[int, pd.DataFrame]) -> Dict[int, pd.DataFrame]:
        """
        Calculate all 35 EMAs for each timeframe

        Args:
            timeframe_data: Dictionary mapping timeframe to DataFrame

        Returns:
            Dictionary with EMA-enriched DataFrames
        """
        print(f"\n{'='*70}")
        print(f"Calculating EMAs for {len(timeframe_data)} timeframes")
        print(f"EMA Periods: {len(self.EMA_PERIODS)} periods")
        print(f"{'='*70}\n")

        enriched_data = {}

        for tf_minutes, df in timeframe_data.items():
            print(f"⚙️  Calculating EMAs for {tf_minutes}min timeframe...")

            # Make a copy to avoid modifying original
            df_with_emas = df.copy()

            # Calculate each EMA period
            for period in self.EMA_PERIODS:
                ema_col = f'MMA{period}'
                df_with_emas[ema_col] = df_with_emas['close'].ewm(
                    span=period,
                    adjust=False
                ).mean()

            # Calculate EMA colors (green if price > EMA, red if price < EMA)
            for period in self.EMA_PERIODS:
                ema_col = f'MMA{period}'
                color_col = f'MMA{period}_color'

                df_with_emas[color_col] = np.where(
                    df_with_emas['close'] > df_with_emas[ema_col],
                    'green',
                    'red'
                )

            # Remove NaN rows (from EMA calculations)
            df_with_emas = df_with_emas.dropna()

            enriched_data[tf_minutes] = df_with_emas

            print(f"   ✅ {tf_minutes}min: {len(df_with_emas)} candles with {len(self.EMA_PERIODS)} EMAs")

        print(f"\n{'='*70}")
        print(f"✅ EMA calculation complete")
        print(f"Total EMA lines: {len(timeframe_data)} TFs × {len(self.EMA_PERIODS)} EMAs = {len(timeframe_data) * len(self.EMA_PERIODS)} lines")
        print(f"{'='*70}\n")

        return enriched_data

    def fetch_and_calculate_all(self, days_back: int = 30) -> Dict[int, pd.DataFrame]:
        """
        Convenience method: Fetch all timeframes and calculate EMAs

        Args:
            days_back: Number of days of historical data

        Returns:
            Dictionary with EMA-enriched DataFrames for all timeframes
        """
        # Fetch all timeframes
        timeframe_data = self.fetch_all_timeframes(days_back=days_back)

        if not timeframe_data:
            print("❌ Failed to fetch timeframe data")
            return {}

        # Calculate EMAs
        enriched_data = self.calculate_mtf_emas(timeframe_data)

        return enriched_data
