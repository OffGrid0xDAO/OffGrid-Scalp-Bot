#!/usr/bin/env python3
"""
Bollinger Bands Calculator

Implements Bollinger Bands for volatility breakout detection.

Bollinger Bands consist of:
- Middle Band: SMA (typically 20-period)
- Upper Band: Middle + (2 * Standard Deviation)
- Lower Band: Middle - (2 * Standard Deviation)

For day trading with 2-3 trades per day:
- Settings: 13-period SMA, 3 standard deviations (for high volatility markets)
- OR: 20-period SMA, 2 standard deviations (standard setting)
- Trade on channel expansion in direction of breakout
- Set stop-loss at opposite band
"""

import pandas as pd
import numpy as np


class BollingerCalculator:
    """
    Calculate Bollinger Bands

    Components:
    - bb_middle: Simple Moving Average (center line)
    - bb_upper: Middle + (std_dev * standard deviations)
    - bb_lower: Middle - (std_dev * standard deviations)
    - bb_width: Bandwidth as % of middle band

    Interpretation:
    - Price at upper band: Potential resistance/overbought
    - Price at lower band: Potential support/oversold
    - Expanding bands: Increasing volatility (trend)
    - Contracting bands: Decreasing volatility (consolidation)
    - Breakout signals: Price crossing outside bands during expansion
    """

    def __init__(self, period: int = 20, std_dev: int = 2):
        """
        Initialize Bollinger Bands calculator

        Args:
            period: Period for SMA calculation (default 20)
            std_dev: Number of standard deviations (default 2)
        """
        self.period = period
        self.std_dev = std_dev

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Bollinger Bands

        Args:
            df: DataFrame with price data

        Returns:
            DataFrame with added columns:
                - bb_middle: Middle band (SMA)
                - bb_upper: Upper band
                - bb_lower: Lower band
                - bb_width: Band width as % of middle
                - bb_percent: Price position within bands (0-1)
                - bb_position: 'above', 'upper', 'middle', 'lower', 'below'
                - bb_squeeze: True if bands are contracting (low volatility)
        """
        print(f"\n📊 Calculating Bollinger Bands ({self.period}-period, {self.std_dev} std dev)...")

        # Calculate middle band (SMA)
        df['bb_middle'] = df['close'].rolling(window=self.period).mean()

        # Calculate standard deviation
        rolling_std = df['close'].rolling(window=self.period).std()

        # Calculate upper and lower bands
        df['bb_upper'] = df['bb_middle'] + (rolling_std * self.std_dev)
        df['bb_lower'] = df['bb_middle'] - (rolling_std * self.std_dev)

        # Calculate bandwidth (% of middle band)
        df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle']) * 100

        # Calculate price position within bands (0 = lower band, 1 = upper band)
        band_range = df['bb_upper'] - df['bb_lower']
        df['bb_percent'] = np.where(
            band_range > 0,
            (df['close'] - df['bb_lower']) / band_range,
            0.5
        )

        # Classify price position
        df['bb_position'] = 'middle'
        df.loc[df['close'] > df['bb_upper'], 'bb_position'] = 'above'  # Breakout above
        df.loc[df['close'] < df['bb_lower'], 'bb_position'] = 'below'  # Breakout below
        df.loc[(df['close'] <= df['bb_upper']) & (df['bb_percent'] > 0.7), 'bb_position'] = 'upper'
        df.loc[(df['close'] >= df['bb_lower']) & (df['bb_percent'] < 0.3), 'bb_position'] = 'lower'

        # Detect squeeze (contracting bands = consolidation)
        # Squeeze = bandwidth < 75% of its 20-period average
        avg_width = df['bb_width'].rolling(window=20).mean()
        df['bb_squeeze'] = df['bb_width'] < (avg_width * 0.75)

        # Detect expansion (expanding bands = volatility increase)
        width_change = df['bb_width'].pct_change(periods=3)
        df['bb_expanding'] = width_change > 0.10  # 10% width increase over 3 periods

        # Calculate distance from bands (for stop-loss placement)
        df['bb_distance_upper'] = ((df['bb_upper'] - df['close']) / df['close']) * 100
        df['bb_distance_lower'] = ((df['close'] - df['bb_lower']) / df['close']) * 100

        print(f"   ✅ Bollinger Bands calculated")
        print(f"   📊 Current price: {df['close'].iloc[-1]:.2f}")
        print(f"   📊 Upper band: {df['bb_upper'].iloc[-1]:.2f}")
        print(f"   📊 Middle band: {df['bb_middle'].iloc[-1]:.2f}")
        print(f"   📊 Lower band: {df['bb_lower'].iloc[-1]:.2f}")
        print(f"   📊 Width: {df['bb_width'].iloc[-1]:.2f}%")
        print(f"   📊 Position: {df['bb_position'].iloc[-1]}")

        return df


if __name__ == '__main__':
    """Test the Bollinger Bands calculator"""
    # Create sample data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    })

    # Calculate Bollinger Bands
    calculator = BollingerCalculator()
    df = calculator.calculate(df)

    # Show results
    print("\n📋 Sample Bollinger Bands values:")
    print(df[['timestamp', 'close', 'bb_upper', 'bb_middle', 'bb_lower',
              'bb_width', 'bb_position']].tail(10).to_string())
