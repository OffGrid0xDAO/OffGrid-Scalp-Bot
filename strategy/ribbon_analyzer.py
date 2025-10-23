#!/usr/bin/env python3
"""
Ribbon Analyzer - EMA Compression/Expansion Detection

Detects powerful EMA ribbon patterns:
- Compression: EMAs tightly packed (setup phase) - score > 60
- Expansion: EMAs spreading apart (move phase) - rate > 5
- Color Flip: Majority of EMAs change color (trigger) - > 85%

Research shows: Compression → Expansion → Color Flip = +75% to +12,000% potential!
"""

import pandas as pd
import numpy as np
from typing import Dict, List


class RibbonAnalyzer:
    """
    Analyze EMA ribbon for compression/expansion patterns

    Ribbon States:
    1. Compression (Setup): EMAs tightly packed, low volatility, waiting for breakout
    2. Expansion (Momentum): EMAs spreading rapidly, strong directional move
    3. Color Flip (Trigger): 85%+ EMAs change from red→green or green→red
    """

    # All 35 EMAs we're tracking
    EMA_PERIODS = [5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
                   85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 200]

    def __init__(self):
        """Initialize ribbon analyzer"""
        pass

    def calculate_compression_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ribbon compression score (0-100)

        Higher score = more compressed (EMAs tighter together)
        100 = Perfectly compressed (all EMAs at same price)
        0 = Maximum dispersion

        Args:
            df: DataFrame with EMA columns (MMA{period}_value)

        Returns:
            DataFrame with 'compression_score' column added
        """
        # Collect all EMA values for each candle
        ema_values = []
        for period in self.EMA_PERIODS:
            col = f'MMA{period}_value'
            if col in df.columns:
                ema_values.append(df[col])

        if not ema_values:
            print("⚠️  No EMA columns found for compression calculation")
            df['compression_score'] = 0
            return df

        # Stack EMAs into array (rows=candles, cols=EMAs)
        ema_array = np.column_stack(ema_values)

        # Calculate range (max - min) across all EMAs for each candle
        ema_range = np.max(ema_array, axis=1) - np.min(ema_array, axis=1)

        # Calculate median EMA value (reference price)
        ema_median = np.median(ema_array, axis=1)

        # Compression score = 100 * (1 - range/median)
        # When range is 0 (all EMAs same), score = 100
        # When range equals median (very spread out), score = 0
        compression_score = 100 * (1 - np.minimum(ema_range / ema_median, 1.0))

        df['compression_score'] = compression_score
        return df

    def calculate_expansion_rate(self, df: pd.DataFrame, lookback: int = 3) -> pd.DataFrame:
        """
        Calculate ribbon expansion rate

        Measures how fast EMAs are spreading apart
        Positive = expanding, Negative = contracting

        Args:
            df: DataFrame with compression_score
            lookback: Periods to look back for rate calculation

        Returns:
            DataFrame with 'expansion_rate' column added
        """
        if 'compression_score' not in df.columns:
            df = self.calculate_compression_score(df)

        # Expansion rate = change in compression score over lookback period
        # Negative change = expanding (compression decreasing)
        # Positive change = compressing (compression increasing)
        compression_change = df['compression_score'].diff(lookback)

        # Flip sign so positive = expanding
        df['expansion_rate'] = -compression_change

        # Smooth with 3-period EMA to reduce noise
        df['expansion_rate'] = df['expansion_rate'].ewm(span=3).mean()

        return df

    def detect_ribbon_flip(self, df: pd.DataFrame, threshold: float = 0.85) -> pd.DataFrame:
        """
        Detect when ribbon "flips" color

        A flip occurs when 85%+ of EMAs change from:
        - Red to Green = Bullish flip
        - Green to Red = Bearish flip

        Args:
            df: DataFrame with EMA color columns (MMA{period}_color)
            threshold: Minimum % of EMAs that must align (0.85 = 85%)

        Returns:
            DataFrame with 'ribbon_flip' column:
                - 'bullish_flip': Majority switched from red to green
                - 'bearish_flip': Majority switched from green to red
                - 'none': No flip detected
        """
        # Count green EMAs for each candle
        green_count = pd.Series(0, index=df.index)
        total_emas = 0

        for period in self.EMA_PERIODS:
            color_col = f'MMA{period}_color'
            if color_col in df.columns:
                green_count += (df[color_col] == 'green').astype(int)
                total_emas += 1

        if total_emas == 0:
            print("⚠️  No EMA color columns found for ribbon flip detection")
            df['ribbon_flip'] = 'none'
            df['alignment_pct'] = 0.5
            return df

        # Calculate alignment percentage
        alignment_pct = green_count / total_emas
        df['alignment_pct'] = alignment_pct

        # Detect flips
        df['ribbon_flip'] = 'none'

        # Bullish flip: alignment crosses above threshold
        bullish_flip = (alignment_pct >= threshold) & (alignment_pct.shift(1) < threshold)
        df.loc[bullish_flip, 'ribbon_flip'] = 'bullish_flip'

        # Bearish flip: alignment crosses below (1 - threshold)
        bearish_flip = (alignment_pct <= (1 - threshold)) & (alignment_pct.shift(1) > (1 - threshold))
        df.loc[bearish_flip, 'ribbon_flip'] = 'bearish_flip'

        return df

    def detect_compression_breakout(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect compression → expansion breakout pattern

        Classic pattern:
        1. Compression score > 60 (tight range)
        2. Suddenly expansion rate > 5 (spreading fast)
        3. Ribbon flips color

        This is the +75% to +12,000% setup from research!

        Args:
            df: DataFrame with all ribbon indicators

        Returns:
            DataFrame with 'compression_breakout' column:
                - 'bullish_breakout': Compressed → expanding → bullish flip
                - 'bearish_breakout': Compressed → expanding → bearish flip
                - 'none': No breakout detected
        """
        # Ensure all indicators calculated
        if 'compression_score' not in df.columns:
            df = self.calculate_compression_score(df)
        if 'expansion_rate' not in df.columns:
            df = self.calculate_expansion_rate(df)
        if 'ribbon_flip' not in df.columns:
            df = self.detect_ribbon_flip(df)

        df['compression_breakout'] = 'none'

        # Look for recent compression (within last 5 candles)
        recent_compression = df['compression_score'].rolling(5).max() > 60

        # Current expansion
        expanding = df['expansion_rate'] > 5

        # Ribbon flip
        bullish_flip = df['ribbon_flip'] == 'bullish_flip'
        bearish_flip = df['ribbon_flip'] == 'bearish_flip'

        # Bullish breakout
        bullish_breakout = recent_compression & expanding & bullish_flip
        df.loc[bullish_breakout, 'compression_breakout'] = 'bullish_breakout'

        # Bearish breakout
        bearish_breakout = recent_compression & expanding & bearish_flip
        df.loc[bearish_breakout, 'compression_breakout'] = 'bearish_breakout'

        return df

    def calculate_ribbon_trend_strength(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ribbon trend strength (0-100)

        Combines:
        - Alignment percentage (are EMAs aligned?)
        - Expansion rate (are they spreading?)
        - Slope (are they all pointing same direction?)

        Args:
            df: DataFrame with EMAs

        Returns:
            DataFrame with 'ribbon_trend_strength' column
        """
        # Ensure alignment calculated
        if 'alignment_pct' not in df.columns:
            df = self.detect_ribbon_flip(df)

        # Ensure expansion calculated
        if 'expansion_rate' not in df.columns:
            df = self.calculate_expansion_rate(df)

        # Calculate slope of fast EMA (EMA8 or EMA10)
        fast_ema_col = 'MMA8_value' if 'MMA8_value' in df.columns else 'MMA10_value'
        if fast_ema_col in df.columns:
            slope = df[fast_ema_col].diff(3)  # 3-candle slope
            slope_normalized = np.tanh(slope / df[fast_ema_col] * 100) * 50 + 50  # Scale to 0-100
        else:
            slope_normalized = 50

        # Alignment score (0-100)
        # Convert alignment_pct (0-1) to 0-100 scale where extremes (0 or 1) = 100
        alignment_score = (1 - abs(df['alignment_pct'] - 0.5) * 2) * 100

        # Expansion score (0-100)
        # Expansion rate > 10 = 100 points
        expansion_score = np.minimum(abs(df['expansion_rate']) / 10 * 100, 100)

        # Combined trend strength
        trend_strength = (alignment_score * 0.5 + expansion_score * 0.3 + slope_normalized * 0.2)

        df['ribbon_trend_strength'] = trend_strength

        return df

    def analyze_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all ribbon indicators

        Args:
            df: DataFrame with EMA columns

        Returns:
            DataFrame with all ribbon analysis columns:
                - compression_score
                - expansion_rate
                - ribbon_flip
                - alignment_pct
                - compression_breakout
                - ribbon_trend_strength
        """
        print("\n🎀 Analyzing EMA Ribbon...")

        df = self.calculate_compression_score(df)
        print(f"   ✅ Compression score (range: {df['compression_score'].min():.1f} - {df['compression_score'].max():.1f})")

        df = self.calculate_expansion_rate(df)
        print(f"   ✅ Expansion rate (range: {df['expansion_rate'].min():.1f} - {df['expansion_rate'].max():.1f})")

        df = self.detect_ribbon_flip(df)
        bullish_flips = (df['ribbon_flip'] == 'bullish_flip').sum()
        bearish_flips = (df['ribbon_flip'] == 'bearish_flip').sum()
        print(f"   ✅ Ribbon flips ({bullish_flips} bullish, {bearish_flips} bearish)")

        df = self.detect_compression_breakout(df)
        bullish_breakouts = (df['compression_breakout'] == 'bullish_breakout').sum()
        bearish_breakouts = (df['compression_breakout'] == 'bearish_breakout').sum()
        print(f"   ✅ Compression breakouts ({bullish_breakouts} bullish, {bearish_breakouts} bearish)")

        df = self.calculate_ribbon_trend_strength(df)
        print(f"   ✅ Trend strength (range: {df['ribbon_trend_strength'].min():.1f} - {df['ribbon_trend_strength'].max():.1f})")

        return df


if __name__ == '__main__':
    """Test ribbon analyzer on historical data"""
    import sys
    from pathlib import Path

    # Load test data
    data_file = Path(__file__).parent.parent.parent / 'trading_data' / 'indicators' / 'eth_1h_full.csv'

    if not data_file.exists():
        print(f"❌ Test data not found: {data_file}")
        sys.exit(1)

    print(f"📊 Loading test data: {data_file}")
    df = pd.read_csv(data_file)
    print(f"   Loaded {len(df)} candles")

    # Create analyzer
    analyzer = RibbonAnalyzer()

    # Analyze ribbon
    df = analyzer.analyze_all(df)

    # Show high-compression setups (potential breakouts)
    high_compression = df[df['compression_score'] > 70][['timestamp', 'close', 'compression_score',
                                                           'expansion_rate', 'alignment_pct',
                                                           'ribbon_flip']]
    print(f"\n📋 High compression setups (score > 70):")
    print(high_compression.head(10).to_string())

    # Show breakouts
    breakouts = df[df['compression_breakout'] != 'none'][['timestamp', 'close', 'compression_breakout',
                                                            'compression_score', 'expansion_rate',
                                                            'alignment_pct']]
    print(f"\n🚀 Compression breakouts:")
    print(breakouts.to_string())

    # Save results
    output_file = Path(__file__).parent.parent.parent / 'trading_data' / 'analysis' / 'eth_1h_ribbon_analysis.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"\n💾 Analysis saved: {output_file}")
