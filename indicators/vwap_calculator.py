#!/usr/bin/env python3
"""
VWAP (Volume Weighted Average Price) Calculator

Calculates VWAP and related metrics
"""

import pandas as pd
import numpy as np


class VWAPCalculator:
    """
    Calculate VWAP indicator

    VWAP = Σ(Typical Price × Volume) / Σ(Volume)
    where Typical Price = (High + Low + Close) / 3

    VWAP shows where institutional traders are positioned
    """

    def __init__(self, session_reset=False):
        """
        Initialize VWAP calculator

        Args:
            session_reset: If True, reset VWAP daily at 00:00 UTC
                          If False, continuous VWAP (default)
        """
        self.session_reset = session_reset

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate VWAP and related metrics

        Args:
            df: DataFrame with 'high', 'low', 'close', 'volume' columns
                and 'timestamp' for session detection

        Returns:
            DataFrame with VWAP columns added
        """
        print(f"\n💰 Calculating VWAP...")

        # Calculate typical price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3

        # Calculate cumulative volume-weighted price
        df['tp_volume'] = df['typical_price'] * df['volume']

        if self.session_reset:
            # Reset VWAP daily (requires timestamp column)
            df = self._calculate_session_vwap(df)
        else:
            # Continuous VWAP
            df['vwap'] = df['tp_volume'].cumsum() / df['volume'].cumsum()

        # Calculate distance from VWAP
        df['vwap_distance'] = df['close'] - df['vwap']
        df['vwap_distance_pct'] = (df['vwap_distance'] / df['vwap']) * 100

        # Classify position relative to VWAP
        df['vwap_position'] = self._classify_position(df)

        # Detect bounces off VWAP
        df['vwap_bounce'] = self._detect_bounces(df)

        # Clean up temporary columns
        df.drop(columns=['typical_price', 'tp_volume'], inplace=True)

        print(f"   ✅ VWAP calculated ({'session' if self.session_reset else 'continuous'})")
        return df

    def _calculate_session_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate VWAP with daily session resets

        Args:
            df: DataFrame with timestamp column

        Returns:
            DataFrame with session VWAP
        """
        # Convert timestamp to date for grouping
        if 'timestamp' in df.columns:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date

            # Calculate VWAP per session
            df['vwap'] = df.groupby('date').apply(
                lambda x: (x['tp_volume'].cumsum() / x['volume'].cumsum())
            ).reset_index(level=0, drop=True)

            df.drop(columns=['date'], inplace=True)
        else:
            # Fallback to continuous if no timestamp
            df['vwap'] = df['tp_volume'].cumsum() / df['volume'].cumsum()

        return df

    def _classify_position(self, df: pd.DataFrame) -> pd.Series:
        """
        Classify price position relative to VWAP

        Categories:
        - strong_above: Price > VWAP by >0.5%
        - above: Price > VWAP by 0-0.5%
        - at_vwap: Within ±0.1% of VWAP
        - below: Price < VWAP by 0-0.5%
        - strong_below: Price < VWAP by >0.5%

        Args:
            df: DataFrame with vwap_distance_pct

        Returns:
            Position classifications
        """
        position = pd.Series('at_vwap', index=df.index)

        position[df['vwap_distance_pct'] > 0.5] = 'strong_above'
        position[(df['vwap_distance_pct'] > 0.1) & (df['vwap_distance_pct'] <= 0.5)] = 'above'
        position[(df['vwap_distance_pct'] >= -0.1) & (df['vwap_distance_pct'] <= 0.1)] = 'at_vwap'
        position[(df['vwap_distance_pct'] < -0.1) & (df['vwap_distance_pct'] >= -0.5)] = 'below'
        position[df['vwap_distance_pct'] < -0.5] = 'strong_below'

        return position

    def _detect_bounces(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect bounces off VWAP

        A bounce occurs when:
        1. Price approaches VWAP (within 0.2%)
        2. Then reverses direction

        Args:
            df: DataFrame with VWAP data

        Returns:
            Bounce signals ('bullish_bounce', 'bearish_bounce', 'none')
        """
        bounce = pd.Series('none', index=df.index)

        # Check if price is near VWAP
        near_vwap = abs(df['vwap_distance_pct']) < 0.2

        # Calculate price direction change
        price_change = df['close'].diff()
        prev_price_change = price_change.shift(1)

        # Bullish bounce: Was falling, now rising
        bullish = near_vwap & (prev_price_change < 0) & (price_change > 0)
        bounce[bullish] = 'bullish_bounce'

        # Bearish bounce: Was rising, now falling
        bearish = near_vwap & (prev_price_change > 0) & (price_change < 0)
        bounce[bearish] = 'bearish_bounce'

        return bounce


def calculate_vwap(df: pd.DataFrame, session_reset=False) -> pd.DataFrame:
    """
    Convenience function to calculate VWAP

    Args:
        df: DataFrame with OHLCV data
        session_reset: Reset VWAP daily

    Returns:
        DataFrame with VWAP columns added
    """
    calculator = VWAPCalculator(session_reset=session_reset)
    return calculator.calculate(df)
