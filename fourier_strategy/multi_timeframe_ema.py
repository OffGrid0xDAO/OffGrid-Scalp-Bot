"""
Multi-Timeframe EMA Ribbon with Fourier Filtering

This module implements EMA ribbons across multiple timeframes with
Fourier filtering to remove noise and detect true trend alignment.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from .fourier_processor import FourierTransformProcessor


class MultiTimeframeEMA:
    """
    Multi-timeframe EMA ribbon with Fourier filtering.

    Creates EMA ribbons at different timeframes and applies Fourier
    filtering to each for noise-free trend detection.
    """

    def __init__(self,
                 base_period: int = 28,
                 timeframe_multipliers: List[int] = [1, 2, 4, 8],
                 n_harmonics: int = 5,
                 noise_threshold: float = 0.3):
        """
        Initialize Multi-Timeframe EMA.

        Args:
            base_period: Base EMA period (default: 28)
            timeframe_multipliers: Multipliers for different timeframes (default: [1,2,4,8])
            n_harmonics: Number of harmonics for Fourier filtering (default: 5)
            noise_threshold: Noise threshold for filtering (default: 0.3)
        """
        self.base_period = base_period
        self.timeframe_multipliers = timeframe_multipliers
        self.ema_periods = [base_period * m for m in timeframe_multipliers]

        # Fourier processor for filtering EMAs
        self.fourier_processor = FourierTransformProcessor(
            n_harmonics=n_harmonics,
            noise_threshold=noise_threshold,
            detrend_method='linear'
        )

    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average.

        Args:
            data: Price series
            period: EMA period

        Returns:
            EMA series
        """
        return data.ewm(span=period, adjust=False).mean()

    def calculate_all_emas(self, data: pd.Series) -> Dict[str, pd.Series]:
        """
        Calculate EMAs for all timeframes.

        Args:
            data: Price series

        Returns:
            Dictionary of EMA series for each period
        """
        emas = {}
        for period in self.ema_periods:
            emas[f'ema_{period}'] = self.calculate_ema(data, period)

        return emas

    def apply_fourier_to_emas(self, emas: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        """
        Apply Fourier filtering to all EMAs.

        Args:
            emas: Dictionary of raw EMA series

        Returns:
            Dictionary of Fourier-filtered EMA series
        """
        filtered_emas = {}

        for name, ema_series in emas.items():
            result = self.fourier_processor.process_signal(ema_series)
            filtered_emas[f'{name}_filtered'] = pd.Series(
                result['filtered'],
                index=ema_series.index
            )

        return filtered_emas

    def calculate_ema_slope(self, ema: pd.Series, lookback: int = 5) -> pd.Series:
        """
        Calculate slope/momentum of EMA.

        Args:
            ema: EMA series
            lookback: Lookback period for slope calculation

        Returns:
            Slope series
        """
        # Calculate percentage change over lookback period
        slope = ema.pct_change(lookback) * 100

        return slope

    def detect_ema_alignment(self,
                            emas: Dict[str, pd.Series],
                            filtered_emas: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Detect EMA alignment (bullish/bearish).

        Bullish: EMAs ordered from fastest (top) to slowest (bottom)
        Bearish: EMAs ordered from slowest (top) to fastest (bottom)

        Args:
            emas: Raw EMAs
            filtered_emas: Fourier-filtered EMAs

        Returns:
            DataFrame with alignment indicators
        """
        df = pd.DataFrame(index=list(emas.values())[0].index)

        # Get EMA values in order
        ema_list = [emas[f'ema_{period}'] for period in self.ema_periods]
        filtered_list = [filtered_emas[f'ema_{period}_filtered'] for period in self.ema_periods]

        # Check raw EMA alignment
        raw_bullish = pd.Series(True, index=df.index)
        raw_bearish = pd.Series(True, index=df.index)

        for i in range(len(ema_list) - 1):
            raw_bullish &= (ema_list[i] > ema_list[i + 1])
            raw_bearish &= (ema_list[i] < ema_list[i + 1])

        df['raw_alignment_bullish'] = raw_bullish.astype(int)
        df['raw_alignment_bearish'] = raw_bearish.astype(int)
        df['raw_alignment_score'] = df['raw_alignment_bullish'] - df['raw_alignment_bearish']

        # Check filtered EMA alignment
        filtered_bullish = pd.Series(True, index=df.index)
        filtered_bearish = pd.Series(True, index=df.index)

        for i in range(len(filtered_list) - 1):
            filtered_bullish &= (filtered_list[i] > filtered_list[i + 1])
            filtered_bearish &= (filtered_list[i] < filtered_list[i + 1])

        df['filtered_alignment_bullish'] = filtered_bullish.astype(int)
        df['filtered_alignment_bearish'] = filtered_bearish.astype(int)
        df['filtered_alignment_score'] = df['filtered_alignment_bullish'] - df['filtered_alignment_bearish']

        return df

    def calculate_price_distance(self,
                                 price: pd.Series,
                                 emas: Dict[str, pd.Series],
                                 filtered_emas: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Calculate price distance from EMA ribbon.

        Args:
            price: Price series
            emas: Raw EMAs
            filtered_emas: Filtered EMAs

        Returns:
            DataFrame with distance metrics
        """
        df = pd.DataFrame(index=price.index)

        # Distance from fastest EMA (raw)
        fastest_period = self.ema_periods[0]
        df['distance_from_fast_ema'] = (
            (price - emas[f'ema_{fastest_period}']) / price * 100
        )

        # Distance from slowest EMA (raw)
        slowest_period = self.ema_periods[-1]
        df['distance_from_slow_ema'] = (
            (price - emas[f'ema_{slowest_period}']) / price * 100
        )

        # Distance from fastest filtered EMA
        df['distance_from_fast_filtered'] = (
            (price - filtered_emas[f'ema_{fastest_period}_filtered']) / price * 100
        )

        # Distance from slowest filtered EMA
        df['distance_from_slow_filtered'] = (
            (price - filtered_emas[f'ema_{slowest_period}_filtered']) / price * 100
        )

        # Average distance from all EMAs
        all_distances = []
        for period in self.ema_periods:
            dist = (price - emas[f'ema_{period}']) / price * 100
            all_distances.append(dist)

        df['avg_distance_raw'] = pd.concat(all_distances, axis=1).mean(axis=1)

        # Average distance from filtered EMAs
        all_filtered_distances = []
        for period in self.ema_periods:
            dist = (price - filtered_emas[f'ema_{period}_filtered']) / price * 100
            all_filtered_distances.append(dist)

        df['avg_distance_filtered'] = pd.concat(all_filtered_distances, axis=1).mean(axis=1)

        return df

    def calculate_ema_momentum(self,
                              emas: Dict[str, pd.Series],
                              filtered_emas: Dict[str, pd.Series],
                              lookback: int = 5) -> pd.DataFrame:
        """
        Calculate momentum/slope for all EMAs.

        Args:
            emas: Raw EMAs
            filtered_emas: Filtered EMAs
            lookback: Lookback period for momentum

        Returns:
            DataFrame with momentum metrics
        """
        df = pd.DataFrame()

        # Calculate slopes for raw EMAs
        for period in self.ema_periods:
            slope = self.calculate_ema_slope(emas[f'ema_{period}'], lookback)
            df[f'ema_{period}_slope'] = slope

        # Calculate slopes for filtered EMAs
        for period in self.ema_periods:
            slope = self.calculate_ema_slope(filtered_emas[f'ema_{period}_filtered'], lookback)
            df[f'ema_{period}_filtered_slope'] = slope

        # Average momentum
        raw_slopes = [df[f'ema_{period}_slope'] for period in self.ema_periods]
        df['avg_momentum_raw'] = pd.concat(raw_slopes, axis=1).mean(axis=1)

        filtered_slopes = [df[f'ema_{period}_filtered_slope'] for period in self.ema_periods]
        df['avg_momentum_filtered'] = pd.concat(filtered_slopes, axis=1).mean(axis=1)

        return df

    def process(self, price: pd.Series) -> Dict[str, pd.DataFrame]:
        """
        Complete processing pipeline for multi-timeframe EMA analysis.

        Args:
            price: Price series

        Returns:
            Dictionary containing:
                - 'emas': Raw EMA series
                - 'filtered_emas': Fourier-filtered EMA series
                - 'alignment': Alignment indicators
                - 'distance': Price distance metrics
                - 'momentum': EMA momentum metrics
        """
        # Calculate all EMAs
        emas = self.calculate_all_emas(price)

        # Apply Fourier filtering
        filtered_emas = self.apply_fourier_to_emas(emas)

        # Detect alignment
        alignment = self.detect_ema_alignment(emas, filtered_emas)

        # Calculate distance
        distance = self.calculate_price_distance(price, emas, filtered_emas)

        # Calculate momentum
        momentum = self.calculate_ema_momentum(emas, filtered_emas)

        # Combine EMAs into DataFrames
        emas_df = pd.DataFrame(emas)
        filtered_emas_df = pd.DataFrame(filtered_emas)

        return {
            'emas': emas_df,
            'filtered_emas': filtered_emas_df,
            'alignment': alignment,
            'distance': distance,
            'momentum': momentum
        }

    def get_signal_strength(self,
                          alignment: pd.DataFrame,
                          distance: pd.DataFrame,
                          momentum: pd.DataFrame) -> pd.Series:
        """
        Calculate composite signal strength from EMA analysis.

        Args:
            alignment: Alignment DataFrame
            distance: Distance DataFrame
            momentum: Momentum DataFrame

        Returns:
            Signal strength series (-1 to 1)
        """
        # Weighted combination of factors
        signal = (
            0.4 * alignment['filtered_alignment_score'] +  # 40% weight on alignment
            0.3 * np.tanh(momentum['avg_momentum_filtered'] / 10) +  # 30% on momentum
            0.3 * np.tanh(-distance['avg_distance_filtered'] / 5)  # 30% on distance (closer is better)
        )

        # Clamp to [-1, 1]
        signal = signal.clip(-1, 1)

        return signal
