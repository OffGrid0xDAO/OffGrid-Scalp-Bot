#!/usr/bin/env python3
"""
Multi-Timeframe Ribbon Aggregator
Combines EMA ribbons from 9 timeframes into unified cloud boundaries and color signals
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from indicators.gradient_mapper import GradientMapper


class MTFRibbonAggregator:
    """
    Aggregates EMA ribbons from multiple timeframes into cloud visualization data

    Combines 9 timeframes × 35 EMAs = 315 total EMA lines into:
    - Upper cloud boundary (highest EMA across all TFs)
    - Lower cloud boundary (lowest EMA across all TFs)
    - Gradient color based on EMA positions relative to price
    - Cloud strength/conviction score
    """

    def __init__(
        self,
        ema_periods: List[int] = None,
        smoothing_window: int = 3,
        boundary_method: str = 'minmax',
        percentile_lower: int = 10,
        percentile_upper: int = 90
    ):
        """
        Initialize aggregator

        Args:
            ema_periods: List of EMA periods to use (default: standard 35 periods)
            smoothing_window: Rolling window for boundary smoothing
            boundary_method: 'minmax' or 'percentile' for boundary calculation
            percentile_lower: Lower percentile if using percentile method
            percentile_upper: Upper percentile if using percentile method
        """
        if ema_periods is None:
            self.ema_periods = [
                5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50,
                55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115,
                120, 125, 130, 135, 140, 145, 200
            ]
        else:
            self.ema_periods = ema_periods

        self.smoothing_window = smoothing_window
        self.boundary_method = boundary_method
        self.percentile_lower = percentile_lower
        self.percentile_upper = percentile_upper

        self.gradient_mapper = GradientMapper()

    def align_timeframes_to_base(
        self,
        mtf_data: Dict[int, pd.DataFrame],
        base_tf_minutes: int = 1
    ) -> pd.DataFrame:
        """
        Align all timeframes to a common base timeframe (forward-fill)

        Args:
            mtf_data: Dictionary mapping timeframe (minutes) to DataFrame
            base_tf_minutes: Base timeframe in minutes

        Returns:
            DataFrame with all EMAs aligned to base timeframe timestamps
        """
        if base_tf_minutes not in mtf_data:
            raise ValueError(f"Base timeframe {base_tf_minutes}min not found in data")

        # Get base timeframe data
        base_df = mtf_data[base_tf_minutes].copy()
        base_index = base_df.index

        # Create result DataFrame starting with base OHLCV
        aligned_df = base_df[['open', 'high', 'low', 'close', 'volume']].copy()

        # Add EMAs from each timeframe with prefix
        for tf_minutes, df in sorted(mtf_data.items()):
            # Create EMA column names for this timeframe
            for period in self.ema_periods:
                src_col = f'MMA{period}'
                if src_col not in df.columns:
                    continue

                # Target column with timeframe prefix
                target_col = f'TF{tf_minutes}_{src_col}'

                # Reindex to base timeframe and forward-fill
                aligned_df[target_col] = df[src_col].reindex(base_index, method='ffill')

        return aligned_df

    def calculate_cloud_boundaries(
        self,
        aligned_df: pd.DataFrame,
        timeframes: List[int]
    ) -> pd.DataFrame:
        """
        Calculate upper and lower cloud boundaries from all EMAs

        Args:
            aligned_df: DataFrame with aligned EMA columns
            timeframes: List of timeframes used

        Returns:
            DataFrame with cloud_upper and cloud_lower columns added
        """
        result_df = aligned_df.copy()

        # Get all EMA column names
        ema_columns = []
        for tf in timeframes:
            for period in self.ema_periods:
                col = f'TF{tf}_MMA{period}'
                if col in result_df.columns:
                    ema_columns.append(col)

        if not ema_columns:
            raise ValueError("No EMA columns found in aligned data")

        # Calculate boundaries row by row
        if self.boundary_method == 'minmax':
            # Simple min/max across all EMAs
            result_df['cloud_lower'] = result_df[ema_columns].min(axis=1)
            result_df['cloud_upper'] = result_df[ema_columns].max(axis=1)

        elif self.boundary_method == 'percentile':
            # Use percentiles to reduce outlier impact
            result_df['cloud_lower'] = result_df[ema_columns].quantile(
                self.percentile_lower / 100,
                axis=1
            )
            result_df['cloud_upper'] = result_df[ema_columns].quantile(
                self.percentile_upper / 100,
                axis=1
            )

        # Apply smoothing to reduce noise
        if self.smoothing_window > 1:
            result_df['cloud_lower'] = result_df['cloud_lower'].rolling(
                window=self.smoothing_window,
                center=False
            ).mean()
            result_df['cloud_upper'] = result_df['cloud_upper'].rolling(
                window=self.smoothing_window,
                center=False
            ).mean()

        return result_df

    def calculate_gradient_colors(
        self,
        aligned_df: pd.DataFrame,
        timeframes: List[int]
    ) -> pd.DataFrame:
        """
        Calculate gradient colors based on EMA positions relative to price

        Args:
            aligned_df: DataFrame with aligned EMA columns and cloud boundaries
            timeframes: List of timeframes used

        Returns:
            DataFrame with cloud_color and cloud_strength columns added
        """
        result_df = aligned_df.copy()

        # Get all EMA column names
        ema_columns = []
        for tf in timeframes:
            for period in self.ema_periods:
                col = f'TF{tf}_MMA{period}'
                if col in result_df.columns:
                    ema_columns.append(col)

        colors = []
        strengths = []
        descriptions = []

        for idx in result_df.index:
            current_price = result_df.loc[idx, 'close']
            ema_values = result_df.loc[idx, ema_columns].values

            # Remove NaN values
            ema_values = ema_values[~np.isnan(ema_values)]

            if len(ema_values) == 0:
                # Default to neutral
                colors.append(self.gradient_mapper.ratio_to_rgba(0.5))
                strengths.append(50)
                descriptions.append("Neutral")
                continue

            # Calculate ratio of EMAs below price (bullish when EMAs are support)
            ratio = self.gradient_mapper.calculate_ema_ratio(current_price, ema_values)

            # Convert to color
            color = self.gradient_mapper.ratio_to_rgba(ratio)
            strength = self.gradient_mapper.calculate_cloud_strength(ratio)
            description = self.gradient_mapper.get_color_description(ratio)

            colors.append(color)
            strengths.append(strength)
            descriptions.append(description)

        result_df['cloud_color'] = colors
        result_df['cloud_strength'] = strengths
        result_df['cloud_sentiment'] = descriptions

        return result_df

    def aggregate_full(
        self,
        mtf_data: Dict[int, pd.DataFrame],
        base_tf_minutes: int = 1
    ) -> pd.DataFrame:
        """
        Complete aggregation pipeline: align, calculate boundaries, calculate colors

        Args:
            mtf_data: Dictionary mapping timeframe (minutes) to DataFrame with EMAs
            base_tf_minutes: Base timeframe for alignment

        Returns:
            DataFrame with full cloud visualization data
        """
        print(f"\n{'='*70}")
        print(f"Multi-Timeframe Ribbon Aggregation")
        print(f"{'='*70}")
        print(f"Timeframes: {sorted(mtf_data.keys())}")
        print(f"Base timeframe: {base_tf_minutes}min")
        print(f"Total EMA lines: {len(mtf_data)} TFs × {len(self.ema_periods)} EMAs = {len(mtf_data) * len(self.ema_periods)}")
        print(f"Boundary method: {self.boundary_method}")
        print(f"Smoothing window: {self.smoothing_window}")
        print(f"{'='*70}\n")

        # Step 1: Align all timeframes to base
        print("📊 Step 1: Aligning timeframes to base...")
        aligned_df = self.align_timeframes_to_base(mtf_data, base_tf_minutes)
        print(f"   ✅ Aligned to {base_tf_minutes}min: {len(aligned_df)} candles, {len(aligned_df.columns)} columns")

        # Step 2: Calculate cloud boundaries
        print("\n📊 Step 2: Calculating cloud boundaries...")
        cloud_df = self.calculate_cloud_boundaries(aligned_df, list(mtf_data.keys()))
        print(f"   ✅ Boundaries calculated: cloud_upper, cloud_lower")

        # Step 3: Calculate gradient colors
        print("\n📊 Step 3: Calculating gradient colors...")
        final_df = self.calculate_gradient_colors(cloud_df, list(mtf_data.keys()))
        print(f"   ✅ Colors calculated: cloud_color, cloud_strength, cloud_sentiment")

        # Remove NaN rows (from smoothing)
        initial_rows = len(final_df)
        final_df = final_df.dropna(subset=['cloud_lower', 'cloud_upper'])
        final_rows = len(final_df)

        print(f"\n{'='*70}")
        print(f"✅ Aggregation complete")
        print(f"Output: {final_rows} candles ({initial_rows - final_rows} dropped due to NaN)")
        print(f"Columns: {len(final_df.columns)} total")
        print(f"{'='*70}\n")

        return final_df

    def get_summary_stats(self, aggregated_df: pd.DataFrame) -> Dict:
        """
        Get summary statistics of cloud data

        Args:
            aggregated_df: Aggregated DataFrame with cloud data

        Returns:
            Dictionary of statistics
        """
        stats = {
            'total_candles': len(aggregated_df),
            'avg_cloud_strength': aggregated_df['cloud_strength'].mean(),
            'max_cloud_strength': aggregated_df['cloud_strength'].max(),
            'min_cloud_strength': aggregated_df['cloud_strength'].min(),
            'bullish_candles': (aggregated_df['cloud_strength'] >= 60).sum(),
            'bearish_candles': (aggregated_df['cloud_strength'] <= 40).sum(),
            'neutral_candles': ((aggregated_df['cloud_strength'] > 40) &
                               (aggregated_df['cloud_strength'] < 60)).sum(),
            'avg_cloud_width': (aggregated_df['cloud_upper'] - aggregated_df['cloud_lower']).mean(),
            'avg_cloud_width_pct': ((aggregated_df['cloud_upper'] - aggregated_df['cloud_lower']) /
                                   aggregated_df['close'] * 100).mean()
        }

        return stats

    def print_summary(self, aggregated_df: pd.DataFrame):
        """
        Print summary statistics of aggregated cloud data

        Args:
            aggregated_df: Aggregated DataFrame
        """
        stats = self.get_summary_stats(aggregated_df)

        print(f"\n{'='*70}")
        print(f"Multi-Timeframe Cloud Summary Statistics")
        print(f"{'='*70}")
        print(f"Total Candles: {stats['total_candles']}")
        print(f"")
        print(f"Cloud Strength:")
        print(f"  Average: {stats['avg_cloud_strength']:.1f}/100")
        print(f"  Range: {stats['min_cloud_strength']:.0f} - {stats['max_cloud_strength']:.0f}")
        print(f"")
        print(f"Sentiment Distribution:")
        print(f"  Bullish (≥60): {stats['bullish_candles']} ({stats['bullish_candles']/stats['total_candles']*100:.1f}%)")
        print(f"  Neutral (40-60): {stats['neutral_candles']} ({stats['neutral_candles']/stats['total_candles']*100:.1f}%)")
        print(f"  Bearish (≤40): {stats['bearish_candles']} ({stats['bearish_candles']/stats['total_candles']*100:.1f}%)")
        print(f"")
        print(f"Cloud Width:")
        print(f"  Average: ${stats['avg_cloud_width']:.2f}")
        print(f"  Average %: {stats['avg_cloud_width_pct']:.2f}%")
        print(f"{'='*70}\n")
