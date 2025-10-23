#!/usr/bin/env python3
"""
Stochastic Oscillator Calculator

Implements the Stochastic Oscillator (5-3-3) for precise entry timing.

The Stochastic Oscillator is a momentum indicator that shows the location
of the current close relative to the high/low range over a set number of periods.

For day trading with 2-3 trades per day:
- Settings: 5-period for %K, 3-period SMA for %D
- Overbought: > 80 (avoid long entries)
- Oversold: < 20 (avoid short entries)
- Best entries: Crossovers exiting extreme zones
"""

import pandas as pd
import numpy as np


class StochasticCalculator:
    """
    Calculate Stochastic Oscillator (5-3-3)

    Components:
    - %K: Fast stochastic (raw calculation)
    - %D: Slow stochastic (SMA of %K)

    Interpretation:
    - > 80: Overbought (good for short entries, avoid longs)
    - < 20: Oversold (good for long entries, avoid shorts)
    - Crossover: %K crossing above %D = bullish, below = bearish
    """

    def __init__(self, k_period: int = 5, d_period: int = 3, smooth_period: int = 3):
        """
        Initialize Stochastic calculator

        Args:
            k_period: Period for %K calculation (default 5 for day trading)
            d_period: Period for %D smoothing (default 3)
            smooth_period: Additional smoothing period (default 3)
        """
        self.k_period = k_period
        self.d_period = d_period
        self.smooth_period = smooth_period

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Stochastic Oscillator

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with added columns:
                - stoch_k: Fast stochastic (0-100)
                - stoch_d: Slow stochastic (0-100)
                - stoch_signal: 'overbought', 'oversold', 'neutral'
                - stoch_crossover: 'bullish', 'bearish', 'none'
        """
        print(f"\n📊 Calculating Stochastic Oscillator ({self.k_period}-{self.d_period}-{self.smooth_period})...")

        # Calculate %K (Fast Stochastic)
        # %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
        low_min = df['low'].rolling(window=self.k_period).min()
        high_max = df['high'].rolling(window=self.k_period).max()

        # Raw stochastic
        stoch_raw = 100 * (df['close'] - low_min) / (high_max - low_min)

        # Smooth %K
        df['stoch_k'] = stoch_raw.rolling(window=self.smooth_period).mean()

        # Calculate %D (Slow Stochastic - SMA of %K)
        df['stoch_d'] = df['stoch_k'].rolling(window=self.d_period).mean()

        # Identify zones
        df['stoch_signal'] = 'neutral'
        df.loc[df['stoch_k'] > 80, 'stoch_signal'] = 'overbought'
        df.loc[df['stoch_k'] < 20, 'stoch_signal'] = 'oversold'

        # Detect crossovers
        df['stoch_crossover'] = 'none'

        # Bullish crossover: %K crosses above %D
        k_above_d = df['stoch_k'] > df['stoch_d']
        k_above_d_prev = k_above_d.shift(1).fillna(False)
        df.loc[k_above_d & ~k_above_d_prev, 'stoch_crossover'] = 'bullish'

        # Bearish crossover: %K crosses below %D
        df.loc[~k_above_d & k_above_d_prev, 'stoch_crossover'] = 'bearish'

        # Calculate momentum strength
        df['stoch_momentum'] = df['stoch_k'] - df['stoch_d']

        print(f"   ✅ Stochastic calculated")
        print(f"   📊 Current %K: {df['stoch_k'].iloc[-1]:.1f}")
        print(f"   📊 Current %D: {df['stoch_d'].iloc[-1]:.1f}")
        print(f"   📊 Signal: {df['stoch_signal'].iloc[-1]}")

        return df


if __name__ == '__main__':
    """Test the Stochastic calculator"""
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

    # Calculate Stochastic
    calculator = StochasticCalculator()
    df = calculator.calculate(df)

    # Show results
    print("\n📋 Sample Stochastic values:")
    print(df[['timestamp', 'close', 'stoch_k', 'stoch_d', 'stoch_signal', 'stoch_crossover']].tail(10).to_string())
