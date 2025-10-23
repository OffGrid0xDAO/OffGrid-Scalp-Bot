#!/usr/bin/env python3
"""
MACD (Moving Average Convergence Divergence) Calculator

Calculates MACD in two configurations:
- Fast MACD (5/13/5) for scalping
- Standard MACD (12/26/9) for confirmation
"""

import pandas as pd
import numpy as np


class MACDCalculator:
    """
    Calculate MACD indicator

    MACD combines trend-following and momentum
    Components:
    - MACD Line: Fast EMA - Slow EMA
    - Signal Line: EMA of MACD Line
    - Histogram: MACD Line - Signal Line
    """

    def __init__(
        self,
        fast_config={'fast': 5, 'slow': 13, 'signal': 5},
        standard_config={'fast': 12, 'slow': 26, 'signal': 9}
    ):
        """
        Initialize MACD calculator

        Args:
            fast_config: Fast MACD parameters (for scalping)
            standard_config: Standard MACD parameters (for confirmation)
        """
        self.fast_config = fast_config
        self.standard_config = standard_config

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate both Fast and Standard MACD

        Args:
            df: DataFrame with 'close' column

        Returns:
            DataFrame with MACD columns added
        """
        print(f"\n📈 Calculating MACD (Fast & Standard)...")

        # Fast MACD (for scalping)
        df = self._calculate_macd(
            df,
            self.fast_config['fast'],
            self.fast_config['slow'],
            self.fast_config['signal'],
            prefix='macd_fast'
        )

        # Standard MACD (for confirmation)
        df = self._calculate_macd(
            df,
            self.standard_config['fast'],
            self.standard_config['slow'],
            self.standard_config['signal'],
            prefix='macd_std'
        )

        print(f"   ✅ Fast MACD ({self.fast_config['fast']}/{self.fast_config['slow']}/{self.fast_config['signal']})")
        print(f"   ✅ Standard MACD ({self.standard_config['fast']}/{self.standard_config['slow']}/{self.standard_config['signal']})")

        return df

    def _calculate_macd(
        self,
        df: pd.DataFrame,
        fast_period: int,
        slow_period: int,
        signal_period: int,
        prefix: str
    ) -> pd.DataFrame:
        """
        Calculate MACD for specific parameters

        Args:
            df: DataFrame with 'close' column
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line EMA period
            prefix: Column name prefix (e.g., 'macd_fast', 'macd_std')

        Returns:
            DataFrame with MACD columns added
        """
        # Calculate Fast and Slow EMAs
        fast_ema = df['close'].ewm(span=fast_period, adjust=False).mean()
        slow_ema = df['close'].ewm(span=slow_period, adjust=False).mean()

        # MACD Line = Fast EMA - Slow EMA
        macd_line = fast_ema - slow_ema
        df[f'{prefix}_line'] = macd_line

        # Signal Line = EMA of MACD Line
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        df[f'{prefix}_signal'] = signal_line

        # Histogram = MACD Line - Signal Line
        histogram = macd_line - signal_line
        df[f'{prefix}_histogram'] = histogram

        # Detect crossovers
        df[f'{prefix}_crossover'] = self._detect_crossovers(macd_line, signal_line)

        # Determine trend
        df[f'{prefix}_trend'] = self._determine_trend(macd_line, signal_line, histogram)

        return df

    def _detect_crossovers(
        self,
        macd_line: pd.Series,
        signal_line: pd.Series
    ) -> pd.Series:
        """
        Detect MACD line crossovers with signal line

        Args:
            macd_line: MACD line values
            signal_line: Signal line values

        Returns:
            Crossover signals ('bullish', 'bearish', 'none')
        """
        # Current and previous positions (convert to boolean explicitly)
        above = (macd_line > signal_line).astype(bool)
        prev_above = above.shift(1).fillna(False).astype(bool)

        crossover = pd.Series('none', index=macd_line.index)

        # Bullish crossover: MACD crosses above signal
        bullish = above & ~prev_above
        crossover[bullish] = 'bullish'

        # Bearish crossover: MACD crosses below signal
        bearish = ~above & prev_above
        crossover[bearish] = 'bearish'

        return crossover

    def _determine_trend(
        self,
        macd_line: pd.Series,
        signal_line: pd.Series,
        histogram: pd.Series
    ) -> pd.Series:
        """
        Determine overall MACD trend

        Bullish: MACD > Signal AND Histogram > 0
        Bearish: MACD < Signal AND Histogram < 0
        Neutral: Mixed signals

        Args:
            macd_line: MACD line values
            signal_line: Signal line values
            histogram: Histogram values

        Returns:
            Trend classification
        """
        trend = pd.Series('neutral', index=macd_line.index)

        # Strong bullish: MACD > Signal AND Histogram > 0
        strong_bullish = (macd_line > signal_line) & (histogram > 0)
        trend[strong_bullish] = 'strong_bullish'

        # Strong bearish: MACD < Signal AND Histogram < 0
        strong_bearish = (macd_line < signal_line) & (histogram < 0)
        trend[strong_bearish] = 'strong_bearish'

        # Weak bullish: MACD > Signal BUT Histogram < 0 (divergence)
        weak_bullish = (macd_line > signal_line) & (histogram < 0)
        trend[weak_bullish] = 'weak_bullish'

        # Weak bearish: MACD < Signal BUT Histogram > 0 (divergence)
        weak_bearish = (macd_line < signal_line) & (histogram > 0)
        trend[weak_bearish] = 'weak_bearish'

        return trend


def calculate_macd(
    df: pd.DataFrame,
    fast_config={'fast': 5, 'slow': 13, 'signal': 5},
    standard_config={'fast': 12, 'slow': 26, 'signal': 9}
) -> pd.DataFrame:
    """
    Convenience function to calculate MACD

    Args:
        df: DataFrame with 'close' column
        fast_config: Fast MACD parameters
        standard_config: Standard MACD parameters

    Returns:
        DataFrame with MACD columns added
    """
    calculator = MACDCalculator(fast_config=fast_config, standard_config=standard_config)
    return calculator.calculate(df)
