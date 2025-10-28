"""
Hyperliquid Data Adapter for Fourier Strategy

This module adapts data from Hyperliquid API to the format
expected by the Fourier Trading Strategy.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.hyperliquid_fetcher import HyperliquidFetcher


class HyperliquidDataAdapter:
    """
    Adapter to fetch and format Hyperliquid data for Fourier Strategy.

    Features:
    - Fetches data from Hyperliquid API
    - Converts to pandas DataFrame format
    - Standardizes column names
    - Handles multiple timeframes
    """

    def __init__(self, symbol: str = 'ETH'):
        """
        Initialize adapter.

        Args:
            symbol: Trading symbol (e.g., 'ETH', 'BTC')
        """
        self.symbol = symbol
        self.fetcher = HyperliquidFetcher(symbol=symbol)

    def fetch_ohlcv(self,
                    interval: str = '1h',
                    days_back: int = 365,
                    use_checkpoint: bool = True) -> pd.DataFrame:
        """
        Fetch OHLCV data from Hyperliquid and convert to DataFrame.

        Args:
            interval: Timeframe ('1m', '3m', '5m', '15m', '30m', '1h')
            days_back: Number of days to fetch
            use_checkpoint: Use checkpoint for resume capability

        Returns:
            DataFrame with OHLCV data in standard format
        """
        print(f"\n📊 Fetching {self.symbol} data from Hyperliquid...")
        print(f"   Timeframe: {interval}, Period: {days_back} days")

        # Fetch candles from Hyperliquid
        candles = self.fetcher.fetch_historical_data(
            interval=interval,
            days_back=days_back,
            use_checkpoint=use_checkpoint
        )

        if not candles:
            raise ValueError(f"No data fetched for {self.symbol} {interval}")

        # Convert to DataFrame
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

        # Convert timestamp to datetime index
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)

        # Drop timestamp column (we have datetime index now)
        df.drop(columns=['timestamp'], inplace=True)

        # Sort by index
        df.sort_index(inplace=True)

        print(f"\n✅ Fetched {len(df)} candles")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")
        print(f"   Columns: {list(df.columns)}")

        return df

    def fetch_latest_candles(self,
                            interval: str = '1h',
                            limit: int = 500) -> pd.DataFrame:
        """
        Fetch most recent candles (for live trading).

        Args:
            interval: Timeframe
            limit: Number of recent candles

        Returns:
            DataFrame with recent OHLCV data
        """
        # Calculate days needed
        interval_minutes = {
            '1m': 1,
            '3m': 3,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60
        }

        minutes = interval_minutes.get(interval, 60)
        days_needed = int((limit * minutes) / (24 * 60)) + 1
        days_needed = min(days_needed, 30)  # Cap at 30 days

        # Fetch data
        df = self.fetch_ohlcv(
            interval=interval,
            days_back=days_needed,
            use_checkpoint=False  # Don't use checkpoint for recent data
        )

        # Return only last N candles
        return df.tail(limit)

    def validate_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Validate DataFrame has required columns.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, raises ValueError if not
        """
        required_cols = ['open', 'high', 'low', 'close', 'volume']

        missing = [col for col in required_cols if col not in df.columns]

        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")

        # Check for NaN values
        if df[required_cols].isnull().any().any():
            print("⚠️  Warning: DataFrame contains NaN values")

        return True

    def resample_timeframe(self,
                          df: pd.DataFrame,
                          target_interval: str) -> pd.DataFrame:
        """
        Resample DataFrame to different timeframe.

        Args:
            df: Source DataFrame
            target_interval: Target interval ('5m', '15m', '1h', etc.)

        Returns:
            Resampled DataFrame
        """
        # Map interval to pandas resample rule
        resample_rules = {
            '1m': '1T',
            '3m': '3T',
            '5m': '5T',
            '15m': '15T',
            '30m': '30T',
            '1h': '1H',
            '4h': '4H',
            '1d': '1D'
        }

        rule = resample_rules.get(target_interval)
        if not rule:
            raise ValueError(f"Unknown interval: {target_interval}")

        # Resample OHLCV
        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        # Drop NaN rows
        resampled.dropna(inplace=True)

        return resampled

    def get_realtime_price(self) -> float:
        """
        Get current real-time price from Hyperliquid.

        Returns:
            Current market price
        """
        from src.exchange.hyperliquid_client import HyperliquidClient

        client = HyperliquidClient(testnet=False)

        if not client.enabled:
            raise Exception("Hyperliquid client not configured!")

        price = client.get_current_price(self.symbol)

        return price

    def get_account_info(self) -> Dict:
        """
        Get account info from Hyperliquid.

        Returns:
            Account info dictionary
        """
        from src.exchange.hyperliquid_client import HyperliquidClient

        client = HyperliquidClient(testnet=False)

        if not client.enabled:
            raise Exception("Hyperliquid client not configured!")

        return client.get_account_info()


def example_fetch_and_validate():
    """Example: Fetch and validate data for Fourier strategy"""
    print("=" * 70)
    print("HYPERLIQUID DATA ADAPTER - EXAMPLE")
    print("=" * 70)

    # Initialize adapter
    adapter = HyperliquidDataAdapter(symbol='ETH')

    # Fetch 1 hour data for last 30 days
    df = adapter.fetch_ohlcv(interval='1h', days_back=30)

    # Validate
    adapter.validate_dataframe(df)
    print("\n✅ Data validated successfully!")

    # Show sample
    print("\nFirst 5 rows:")
    print(df.head())

    print("\nLast 5 rows:")
    print(df.tail())

    # Get current price
    try:
        current_price = adapter.get_realtime_price()
        print(f"\n💰 Current ETH price: ${current_price:.2f}")
    except Exception as e:
        print(f"\n⚠️  Could not fetch current price: {e}")

    return df


def example_with_fourier_strategy():
    """Example: Use Hyperliquid data with Fourier strategy"""
    print("\n" + "=" * 70)
    print("FOURIER STRATEGY WITH HYPERLIQUID DATA")
    print("=" * 70)

    # Fetch data
    adapter = HyperliquidDataAdapter(symbol='ETH')
    df = adapter.fetch_ohlcv(interval='1h', days_back=90)

    # Run Fourier strategy
    from fourier_strategy import FourierTradingStrategy

    strategy = FourierTradingStrategy(
        n_harmonics=5,
        base_ema_period=28,
        initial_capital=10000.0
    )

    results = strategy.run(df, run_backtest=True, verbose=True)

    # Print summary
    print(strategy.get_summary())

    # Get current signal
    current = strategy.get_current_signal()

    print("\n" + "=" * 70)
    print("CURRENT SIGNAL")
    print("=" * 70)
    print(f"Signal Strength: {current['composite_signal']:.3f}")
    print(f"Confidence: {current['confidence']:.1f}%")
    print(f"Position: {current['position']}")
    print(f"Reason: {current['signal_reason']}")

    # Save results
    strategy.export_results('hyperliquid_fourier_results.csv')
    strategy.visualize('comprehensive', save_path='hyperliquid_fourier_analysis.png')

    return strategy, results


def example_live_data():
    """Example: Fetch latest candles for live trading"""
    print("\n" + "=" * 70)
    print("LIVE DATA FETCHING")
    print("=" * 70)

    adapter = HyperliquidDataAdapter(symbol='ETH')

    # Fetch last 500 candles (for indicator calculation)
    df = adapter.fetch_latest_candles(interval='1h', limit=500)

    print(f"\n✅ Fetched {len(df)} recent candles")
    print(f"   Latest: {df.index[-1]}")
    print(f"   Close: ${df['close'].iloc[-1]:.2f}")

    # Get current price
    try:
        current_price = adapter.get_realtime_price()
        latest_candle_price = df['close'].iloc[-1]
        price_diff = current_price - latest_candle_price

        print(f"\n💰 Current price: ${current_price:.2f}")
        print(f"   Candle close: ${latest_candle_price:.2f}")
        print(f"   Difference: ${price_diff:.2f}")
    except Exception as e:
        print(f"\n⚠️  Could not fetch current price: {e}")

    return df


if __name__ == '__main__':
    # Run examples
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "HYPERLIQUID ADAPTER EXAMPLES" + " " * 24 + "║")
    print("╚" + "═" * 68 + "╝\n")

    # Example 1: Basic fetch and validate
    df1 = example_fetch_and_validate()

    # Example 2: Use with Fourier strategy
    # strategy, results = example_with_fourier_strategy()

    # Example 3: Live data
    # df_live = example_live_data()

    print("\n" + "=" * 70)
    print("EXAMPLES COMPLETE")
    print("=" * 70)
