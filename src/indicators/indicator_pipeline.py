#!/usr/bin/env python3
"""
Indicator Pipeline

Orchestrates calculation of all technical indicators
Ensures proper dependency order and efficient processing
"""

import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

from .rsi_calculator import RSICalculator
from .macd_calculator import MACDCalculator
from .vwap_calculator import VWAPCalculator
from .volume_analyzer import VolumeAnalyzer
from .stochastic_calculator import StochasticCalculator
from .bollinger_calculator import BollingerCalculator


class IndicatorPipeline:
    """
    Orchestrate all indicator calculations

    Processing order:
    1. EMAs (already calculated by data fetcher)
    2. Additional important EMA crossovers
    3. Independent indicators in parallel (RSI, MACD, VWAP, Volume)
    4. Confluence scoring
    """

    # Important EMA crossover pairs
    IMPORTANT_EMA_CROSSES = [
        (9, 21),    # Short-term (day trading/scalping)
        (8, 21),    # Fibonacci-based
        (12, 26),   # MACD default
        (20, 50),   # Intermediate (swing trading)
        (50, 200),  # Golden/Death cross (long-term)
    ]

    def __init__(self):
        """Initialize indicator pipeline"""
        self.rsi_calculator = RSICalculator(periods=[7, 14])
        self.macd_calculator = MACDCalculator()
        self.vwap_calculator = VWAPCalculator(session_reset=False)  # Continuous VWAP
        self.volume_analyzer = VolumeAnalyzer(ema_period=20, spike_threshold=2.0)
        self.stochastic_calculator = StochasticCalculator(k_period=5, d_period=3, smooth_period=3)  # 5-3-3 for day trading
        self.bollinger_calculator = BollingerCalculator(period=20, std_dev=2)  # Standard 20-period, 2 std dev

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all indicators

        Args:
            df: DataFrame with OHLCV data and existing EMAs

        Returns:
            DataFrame with all indicators added
        """
        print("\n" + "="*80)
        print("CALCULATING ALL INDICATORS")
        print("="*80)

        # Step 1: Add important EMA crossovers (if not already present)
        df = self._add_important_ema_crossovers(df)

        # Step 2: Calculate independent indicators in parallel
        df = self._calculate_parallel_indicators(df)

        # Step 3: Calculate confluence score
        df = self._calculate_confluence_score(df)

        print("\n" + "="*80)
        print("✅ ALL INDICATORS COMPLETE")
        print("="*80)

        return df

    def _add_important_ema_crossovers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add important EMA crossover pairs

        Crossovers:
        - 9/21: Short-term (day trading/scalping)
        - 8/21: Fibonacci-based
        - 12/26: MACD default (intermediate)
        - 20/50: Swing trading
        - 50/200: Golden/Death cross (long-term, institutional)

        Args:
            df: DataFrame with EMA columns

        Returns:
            DataFrame with crossover columns added
        """
        print("\n🔀 Adding important EMA crossovers...")

        for fast, slow in self.IMPORTANT_EMA_CROSSES:
            # Check for both ema_X and MMAX_value column naming
            fast_col = f'ema_{fast}' if f'ema_{fast}' in df.columns else f'MMA{fast}_value'
            slow_col = f'ema_{slow}' if f'ema_{slow}' in df.columns else f'MMA{slow}_value'
            cross_col = f'ema_cross_{fast}_{slow}'

            # Skip if already exists or EMAs not present
            if cross_col in df.columns:
                continue
            if fast_col not in df.columns or slow_col not in df.columns:
                print(f"   ⚠️  Skipping {fast}/{slow} - EMAs not found (looking for {fast_col}, {slow_col})")
                continue

            # Determine position
            above = df[fast_col] > df[slow_col]
            prev_above = above.shift(1).fillna(False)

            # Detect crossovers
            df[cross_col] = 'none'
            df.loc[above & ~prev_above, cross_col] = 'golden_cross'
            df.loc[~above & prev_above, cross_col] = 'death_cross'

            print(f"   ✅ Added {fast}/{slow} crossover")

        return df

    def _calculate_parallel_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate independent indicators in parallel

        These don't depend on each other, so can run simultaneously

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with all indicators added
        """
        print("\n⚡ Calculating indicators in parallel...")

        # Calculate in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=6) as executor:
            # Submit all calculations
            rsi_future = executor.submit(self.rsi_calculator.calculate, df.copy())
            macd_future = executor.submit(self.macd_calculator.calculate, df.copy())
            vwap_future = executor.submit(self.vwap_calculator.calculate, df.copy())
            volume_future = executor.submit(self.volume_analyzer.analyze, df.copy())
            stochastic_future = executor.submit(self.stochastic_calculator.calculate, df.copy())
            bollinger_future = executor.submit(self.bollinger_calculator.calculate, df.copy())

            # Wait for all to complete and merge results
            rsi_df = rsi_future.result()
            macd_df = macd_future.result()
            vwap_df = vwap_future.result()
            volume_df = volume_future.result()
            stochastic_df = stochastic_future.result()
            bollinger_df = bollinger_future.result()

        # Merge all indicator columns back to main dataframe
        indicator_columns = []

        # RSI columns
        rsi_cols = [col for col in rsi_df.columns if col.startswith('rsi_')]
        indicator_columns.extend(rsi_cols)

        # MACD columns
        macd_cols = [col for col in macd_df.columns if col.startswith('macd_')]
        indicator_columns.extend(macd_cols)

        # VWAP columns
        vwap_cols = [col for col in vwap_df.columns if col.startswith('vwap')]
        indicator_columns.extend(vwap_cols)

        # Volume columns
        volume_cols = [col for col in volume_df.columns if col.startswith('volume_') or col == 'accumulation_distribution']
        indicator_columns.extend(volume_cols)

        # Stochastic columns
        stochastic_cols = [col for col in stochastic_df.columns if col.startswith('stoch_')]
        indicator_columns.extend(stochastic_cols)

        # Bollinger columns
        bollinger_cols = [col for col in bollinger_df.columns if col.startswith('bb_')]
        indicator_columns.extend(bollinger_cols)

        # Add all indicator columns to main dataframe
        for col in indicator_columns:
            if col == 'rsi_7':
                df[col] = rsi_df[col]
            elif col == 'rsi_14':
                df[col] = rsi_df[col]
            elif col.startswith('rsi_'):
                df[col] = rsi_df[col]
            elif col.startswith('macd_'):
                df[col] = macd_df[col]
            elif col.startswith('vwap'):
                df[col] = vwap_df[col]
            elif col in volume_cols:
                df[col] = volume_df[col]
            elif col.startswith('stoch_'):
                df[col] = stochastic_df[col]
            elif col.startswith('bb_'):
                df[col] = bollinger_df[col]

        print(f"   ✅ Parallel calculation complete ({len(indicator_columns)} columns added)")
        return df

    def _calculate_confluence_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate confluence score (0-100)

        Weights:
        - EMA Ribbon: 40%
        - RSI: 20%
        - MACD: 20%
        - VWAP: 10%
        - Volume: 10%

        Args:
            df: DataFrame with all indicators

        Returns:
            DataFrame with confluence scores added
        """
        print("\n🎯 Calculating confluence scores...")

        # Initialize scores
        df['confluence_score_long'] = 0.0
        df['confluence_score_short'] = 0.0

        # EMA Ribbon score (40 points max)
        if 'alignment_pct' in df.columns:
            # Long: alignment_pct > 0.85 = 40 points, > 0.70 = 30 points, > 0.55 = 15 points
            df.loc[df['alignment_pct'] > 0.85, 'confluence_score_long'] += 40
            df.loc[(df['alignment_pct'] > 0.70) & (df['alignment_pct'] <= 0.85), 'confluence_score_long'] += 30
            df.loc[(df['alignment_pct'] > 0.55) & (df['alignment_pct'] <= 0.70), 'confluence_score_long'] += 15

            # Short: alignment_pct < 0.15 = 40 points, < 0.30 = 30 points, < 0.45 = 15 points
            df.loc[df['alignment_pct'] < 0.15, 'confluence_score_short'] += 40
            df.loc[(df['alignment_pct'] < 0.30) & (df['alignment_pct'] >= 0.15), 'confluence_score_short'] += 30
            df.loc[(df['alignment_pct'] < 0.45) & (df['alignment_pct'] >= 0.30), 'confluence_score_short'] += 15

        # RSI score (20 points max)
        if 'rsi_14' in df.columns:
            # Long: RSI > 45 and < 70 (not overbought, has momentum)
            df.loc[(df['rsi_14'] > 45) & (df['rsi_14'] < 70), 'confluence_score_long'] += 20
            # Short: RSI < 55 and > 30 (not oversold, has momentum down)
            df.loc[(df['rsi_14'] < 55) & (df['rsi_14'] > 30), 'confluence_score_short'] += 20

        # MACD score (20 points max)
        if 'macd_fast_trend' in df.columns:
            # Long: MACD bullish
            df.loc[df['macd_fast_trend'].isin(['strong_bullish', 'weak_bullish']), 'confluence_score_long'] += 20
            # Short: MACD bearish
            df.loc[df['macd_fast_trend'].isin(['strong_bearish', 'weak_bearish']), 'confluence_score_short'] += 20

        # VWAP score (10 points max)
        if 'vwap_position' in df.columns:
            # Long: Price above VWAP
            df.loc[df['vwap_position'].isin(['above', 'strong_above']), 'confluence_score_long'] += 10
            # Short: Price below VWAP
            df.loc[df['vwap_position'].isin(['below', 'strong_below']), 'confluence_score_short'] += 10

        # Volume score (10 points max)
        if 'volume_status' in df.columns:
            # Long or Short: Elevated volume confirms move
            df.loc[df['volume_status'].isin(['elevated', 'spike']), 'confluence_score_long'] += 10
            df.loc[df['volume_status'].isin(['elevated', 'spike']), 'confluence_score_short'] += 10

        # Determine overall direction
        df['confluence_direction'] = 'neutral'
        df.loc[df['confluence_score_long'] > df['confluence_score_short'], 'confluence_direction'] = 'long'
        df.loc[df['confluence_score_short'] > df['confluence_score_long'], 'confluence_direction'] = 'short'

        # Best score
        df['confluence_score'] = df[['confluence_score_long', 'confluence_score_short']].max(axis=1)

        print(f"   ✅ Confluence scores calculated")
        print(f"   📊 Score range: {df['confluence_score'].min():.0f} - {df['confluence_score'].max():.0f}")

        return df


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convenience function to process a dataframe through the indicator pipeline

    Args:
        df: DataFrame with OHLCV data and EMAs

    Returns:
        DataFrame with all indicators added
    """
    pipeline = IndicatorPipeline()
    return pipeline.calculate_all(df)
