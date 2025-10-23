#!/usr/bin/env python3
"""
Volume Analyzer

Analyzes volume patterns, spikes, and trends
"""

import pandas as pd
import numpy as np


class VolumeAnalyzer:
    """
    Analyze volume patterns

    Features:
    - Volume EMA for baseline
    - Spike detection (unusual volume)
    - Volume trend analysis
    - Accumulation/Distribution detection
    """

    def __init__(self, ema_period=20, spike_threshold=2.0, elevated_threshold=1.5):
        """
        Initialize volume analyzer

        Args:
            ema_period: Period for volume EMA (default: 20)
            spike_threshold: Volume spike threshold (e.g., 2.0 = 2× average)
            elevated_threshold: Elevated volume threshold (e.g., 1.5 = 1.5× average)
        """
        self.ema_period = ema_period
        self.spike_threshold = spike_threshold
        self.elevated_threshold = elevated_threshold

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze volume patterns

        Args:
            df: DataFrame with 'volume' and 'close' columns

        Returns:
            DataFrame with volume analysis columns added
        """
        print(f"\n📊 Analyzing Volume...")

        # Calculate volume EMA (average volume)
        df['volume_ema'] = df['volume'].ewm(span=self.ema_period, adjust=False).mean()

        # Calculate volume ratio (current vs average)
        df['volume_ratio'] = df['volume'] / df['volume_ema']

        # Detect spikes and classify volume
        df['volume_status'] = self._classify_volume(df)

        # Calculate volume trend (is volume increasing or decreasing?)
        df['volume_trend'] = self._calculate_volume_trend(df)

        # Detect accumulation/distribution
        df['accumulation_distribution'] = self._detect_accumulation_distribution(df)

        print(f"   ✅ Volume analyzed (EMA: {self.ema_period}, Spike threshold: {self.spike_threshold}×)")
        return df

    def _classify_volume(self, df: pd.DataFrame) -> pd.Series:
        """
        Classify volume levels

        Categories:
        - spike: Volume > 2× average (major event)
        - elevated: Volume > 1.5× average (high interest)
        - normal: Volume within 0.5-1.5× average
        - low: Volume < 0.5× average (weak participation)

        Args:
            df: DataFrame with volume_ratio

        Returns:
            Volume status classifications
        """
        status = pd.Series('normal', index=df.index)

        status[df['volume_ratio'] >= self.spike_threshold] = 'spike'
        status[
            (df['volume_ratio'] >= self.elevated_threshold) &
            (df['volume_ratio'] < self.spike_threshold)
        ] = 'elevated'
        status[df['volume_ratio'] < 0.5] = 'low'

        return status

    def _calculate_volume_trend(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate volume trend direction

        Compares current volume to short-term average

        Args:
            df: DataFrame with volume

        Returns:
            Trend direction ('increasing', 'decreasing', 'stable')
        """
        # Short-term volume average (last 5 periods)
        short_vol_avg = df['volume'].rolling(window=5).mean()

        # Compare current to short-term average
        trend = pd.Series('stable', index=df.index)

        trend[df['volume'] > short_vol_avg * 1.1] = 'increasing'
        trend[df['volume'] < short_vol_avg * 0.9] = 'decreasing'

        return trend

    def _detect_accumulation_distribution(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect accumulation (buying pressure) vs distribution (selling pressure)

        Logic:
        - Accumulation: Volume increasing on up moves
        - Distribution: Volume increasing on down moves
        - Neutral: Mixed or low volume

        Args:
            df: DataFrame with volume and close data

        Returns:
            Accumulation/Distribution signal
        """
        ad_signal = pd.Series('neutral', index=df.index)

        # Price direction
        price_up = df['close'] > df['close'].shift(1)
        price_down = df['close'] < df['close'].shift(1)

        # Volume status
        high_volume = df['volume_ratio'] >= self.elevated_threshold

        # Accumulation: High volume on up moves
        accumulation = price_up & high_volume
        ad_signal[accumulation] = 'accumulation'

        # Distribution: High volume on down moves
        distribution = price_down & high_volume
        ad_signal[distribution] = 'distribution'

        return ad_signal


def analyze_volume(
    df: pd.DataFrame,
    ema_period=20,
    spike_threshold=2.0,
    elevated_threshold=1.5
) -> pd.DataFrame:
    """
    Convenience function to analyze volume

    Args:
        df: DataFrame with volume data
        ema_period: Volume EMA period
        spike_threshold: Spike detection threshold
        elevated_threshold: Elevated volume threshold

    Returns:
        DataFrame with volume analysis columns added
    """
    analyzer = VolumeAnalyzer(
        ema_period=ema_period,
        spike_threshold=spike_threshold,
        elevated_threshold=elevated_threshold
    )
    return analyzer.analyze(df)
