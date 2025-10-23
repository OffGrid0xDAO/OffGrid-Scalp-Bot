#!/usr/bin/env python3
"""
RSI (Relative Strength Index) Calculator

Calculates RSI for multiple periods with zone classification
"""

import pandas as pd
import numpy as np


class RSICalculator:
    """
    Calculate RSI indicator

    RSI measures momentum and identifies overbought/oversold conditions
    Formula: RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss
    """

    def __init__(self, periods=[7, 14]):
        """
        Initialize RSI calculator

        Args:
            periods: List of RSI periods to calculate (default: [7, 14])
        """
        self.periods = periods

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RSI for all configured periods

        Args:
            df: DataFrame with 'close' column

        Returns:
            DataFrame with RSI columns added
        """
        print(f"\n📊 Calculating RSI ({len(self.periods)} periods)...")

        for period in self.periods:
            rsi_col = f'rsi_{period}'
            df[rsi_col] = self._calculate_rsi(df['close'], period)

            # Classify zones
            zone_col = f'rsi_{period}_zone'
            df[zone_col] = self._classify_zones(df[rsi_col])

            # Divergence detection (optional - for future use)
            # df[f'rsi_{period}_divergence'] = self._detect_divergence(df, rsi_col)

        print(f"   ✅ RSI calculated for periods: {self.periods}")
        return df

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate RSI for a specific period

        Args:
            prices: Price series (typically close prices)
            period: RSI period

        Returns:
            RSI values as Series
        """
        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gain and loss using EWM (Wilder's smoothing)
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _classify_zones(self, rsi: pd.Series) -> pd.Series:
        """
        Classify RSI into zones

        Zones:
        - overbought: RSI > 70
        - oversold: RSI < 30
        - neutral_high: 50 < RSI <= 70
        - neutral_low: 30 <= RSI <= 50

        Args:
            rsi: RSI values

        Returns:
            Zone classifications
        """
        zones = pd.Series(index=rsi.index, dtype=str)

        zones[rsi > 70] = 'overbought'
        zones[rsi < 30] = 'oversold'
        zones[(rsi >= 50) & (rsi <= 70)] = 'neutral_high'
        zones[(rsi >= 30) & (rsi < 50)] = 'neutral_low'

        return zones

    def _detect_divergence(self, df: pd.DataFrame, rsi_col: str) -> pd.Series:
        """
        Detect bullish/bearish divergence between price and RSI

        Bullish divergence: Price makes lower low, RSI makes higher low
        Bearish divergence: Price makes higher high, RSI makes lower high

        Args:
            df: DataFrame with price and RSI data
            rsi_col: Name of RSI column

        Returns:
            Divergence signals ('bullish', 'bearish', 'none')
        """
        # Find local peaks and troughs
        # This is a simplified version - can be enhanced with more sophisticated peak detection
        window = 14

        price_peaks = df['close'].rolling(window, center=True).apply(
            lambda x: 1 if x[len(x)//2] == x.max() else 0
        )
        price_troughs = df['close'].rolling(window, center=True).apply(
            lambda x: 1 if x[len(x)//2] == x.min() else 0
        )

        rsi_peaks = df[rsi_col].rolling(window, center=True).apply(
            lambda x: 1 if x[len(x)//2] == x.max() else 0
        )
        rsi_troughs = df[rsi_col].rolling(window, center=True).apply(
            lambda x: 1 if x[len(x)//2] == x.min() else 0
        )

        divergence = pd.Series('none', index=df.index)

        # Bullish divergence: price trough but RSI not
        bullish = (price_troughs == 1) & (rsi_troughs == 0)
        divergence[bullish] = 'bullish'

        # Bearish divergence: price peak but RSI not
        bearish = (price_peaks == 1) & (rsi_peaks == 0)
        divergence[bearish] = 'bearish'

        return divergence


def calculate_rsi(df: pd.DataFrame, periods=[7, 14]) -> pd.DataFrame:
    """
    Convenience function to calculate RSI

    Args:
        df: DataFrame with 'close' column
        periods: List of RSI periods

    Returns:
        DataFrame with RSI columns added
    """
    calculator = RSICalculator(periods=periods)
    return calculator.calculate(df)
