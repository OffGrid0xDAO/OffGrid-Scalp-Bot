#!/usr/bin/env python3
"""
Gradient Color Mapper for Multi-Timeframe EMA Ribbon Cloud
Maps EMA positions to smooth gradient colors (green → yellow → red)
"""

import numpy as np
import pandas as pd
from typing import Tuple, List


class GradientMapper:
    """
    Maps EMA ribbon positions to gradient colors for cloud visualization

    Color Logic:
    - 100% EMAs above price = Pure Green (bullish)
    - 50% EMAs above/below = Yellow (neutral)
    - 0% EMAs above price = Pure Red (bearish)

    Supports smooth RGB interpolation for professional gradient effects
    """

    # Color stops (RGB tuples)
    COLOR_BULLISH = (0, 255, 0)      # Pure green
    COLOR_NEUTRAL = (255, 255, 0)    # Yellow
    COLOR_BEARISH = (255, 0, 0)      # Pure red

    def __init__(self, opacity: float = 0.3):
        """
        Initialize gradient mapper

        Args:
            opacity: Opacity for cloud fills (0.0-1.0)
        """
        self.opacity = opacity

    def calculate_ema_ratio(
        self,
        current_price: float,
        ema_values: List[float]
    ) -> float:
        """
        Calculate ratio of EMAs above current price

        Args:
            current_price: Current price
            ema_values: List of EMA values (or numpy array)

        Returns:
            Ratio of EMAs above price (0.0 to 1.0)
        """
        # Convert to numpy array if needed
        if isinstance(ema_values, (list, tuple)):
            ema_array = np.array(ema_values)
        else:
            ema_array = ema_values

        # Remove NaN values
        ema_array = ema_array[~np.isnan(ema_array)]

        if len(ema_array) == 0:
            return 0.5  # Neutral if no EMAs

        # Count EMAs below price (price is above them = support = bullish)
        emas_below = np.sum(ema_array < current_price)
        total_emas = len(ema_array)

        ratio = emas_below / total_emas
        return ratio

    def ratio_to_rgb(self, ratio: float) -> Tuple[int, int, int]:
        """
        Convert EMA ratio to RGB color - PURE GREEN to RED gradient (no yellow)

        Args:
            ratio: Ratio of EMAs below price (0.0 to 1.0)
                   0.0 = all EMAs above price (resistance) = RED
                   1.0 = all EMAs below price (support) = GREEN

        Returns:
            RGB color tuple (R, G, B)
        """
        # Clamp ratio to [0, 1]
        ratio = max(0.0, min(1.0, ratio))

        # Direct interpolation from RED to GREEN
        # ratio = 0.0 → pure red (255, 0, 0)
        # ratio = 0.5 → balanced (127, 127, 0) - still red/green mix
        # ratio = 1.0 → pure green (0, 255, 0)

        r = int(255 * (1 - ratio))  # Red decreases as ratio increases
        g = int(255 * ratio)         # Green increases as ratio increases
        b = 0                        # No blue component

        return (r, g, b)

    def rgb_to_rgba_string(self, rgb: Tuple[int, int, int], opacity: float = None) -> str:
        """
        Convert RGB tuple to RGBA string for Plotly

        Args:
            rgb: RGB color tuple
            opacity: Opacity override (uses default if None)

        Returns:
            RGBA string like 'rgba(255, 0, 0, 0.3)'
        """
        if opacity is None:
            opacity = self.opacity

        return f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {opacity})'

    def ratio_to_rgba(self, ratio: float, opacity: float = None) -> str:
        """
        Convert EMA ratio directly to RGBA string

        Args:
            ratio: Ratio of EMAs above price (0.0 to 1.0)
            opacity: Opacity override

        Returns:
            RGBA string for Plotly
        """
        rgb = self.ratio_to_rgb(ratio)
        return self.rgb_to_rgba_string(rgb, opacity)

    def calculate_cloud_strength(self, ratio: float) -> int:
        """
        Calculate cloud conviction strength score (0-100)

        Args:
            ratio: Ratio of EMAs above price (0.0 to 1.0)

        Returns:
            Strength score (0-100)
            - 100 = Strong bullish (all EMAs below price)
            - 0 = Strong bearish (all EMAs above price)
            - 50 = Neutral
        """
        return int(ratio * 100)

    def get_strength_color(self, strength: int) -> str:
        """
        Get color for strength indicator based on score

        Args:
            strength: Strength score (0-100)

        Returns:
            Color name for strength bar
        """
        if strength >= 70:
            return 'green'
        elif strength >= 55:
            return 'lightgreen'
        elif strength >= 45:
            return 'yellow'
        elif strength >= 30:
            return 'orange'
        else:
            return 'red'

    def create_gradient_palette(self, num_steps: int = 256) -> List[str]:
        """
        Create a smooth gradient palette with N color steps

        Args:
            num_steps: Number of color steps in palette

        Returns:
            List of RGBA color strings
        """
        palette = []

        for i in range(num_steps):
            ratio = i / (num_steps - 1)
            rgba = self.ratio_to_rgba(ratio)
            palette.append(rgba)

        return palette

    def map_series_to_colors(
        self,
        price_series: pd.Series,
        ema_df: pd.DataFrame,
        ema_columns: List[str]
    ) -> pd.Series:
        """
        Map entire price series to gradient colors based on EMA positions

        Args:
            price_series: Series of prices (indexed by timestamp)
            ema_df: DataFrame with EMA columns
            ema_columns: List of EMA column names to consider

        Returns:
            Series of RGBA color strings
        """
        colors = []

        for idx in price_series.index:
            if idx not in ema_df.index:
                # Default to neutral if no EMA data
                colors.append(self.ratio_to_rgba(0.5))
                continue

            current_price = price_series.loc[idx]
            ema_values = ema_df.loc[idx, ema_columns].values

            # Remove NaN values
            ema_values = ema_values[~np.isnan(ema_values)]

            # Calculate ratio and convert to color
            ratio = self.calculate_ema_ratio(current_price, ema_values)
            color = self.ratio_to_rgba(ratio)
            colors.append(color)

        return pd.Series(colors, index=price_series.index)

    def calculate_compression(
        self,
        ema_values: List[float]
    ) -> float:
        """
        Calculate EMA compression (how tightly packed the EMAs are)

        Args:
            ema_values: List of EMA values (or numpy array)

        Returns:
            Compression ratio (0.0 to 1.0)
            1.0 = highly compressed (EMAs very close together)
            0.0 = highly expanded (EMAs far apart)
        """
        # Convert to numpy array if needed
        if isinstance(ema_values, (list, tuple)):
            ema_array = np.array(ema_values)
        else:
            ema_array = ema_values

        # Remove NaN values
        ema_array = ema_array[~np.isnan(ema_array)]

        if len(ema_array) < 2:
            return 0.5  # Neutral if not enough data

        # Calculate the range of EMAs
        ema_min = np.min(ema_array)
        ema_max = np.max(ema_array)
        ema_range = ema_max - ema_min

        if ema_min == 0:
            return 0.5

        # Calculate compression as percentage of price
        # Smaller range = more compressed = higher value
        compression_pct = (ema_range / ema_min) * 100

        # Convert to 0-1 scale (inverted - smaller range = higher compression)
        # Typical range: 0-10% = highly compressed, >20% = expanded
        if compression_pct < 1:
            compression = 1.0  # Very compressed
        elif compression_pct > 20:
            compression = 0.0  # Very expanded
        else:
            # Linear interpolation between 1% and 20%
            compression = 1.0 - ((compression_pct - 1) / 19)

        return max(0.0, min(1.0, compression))

    def calculate_divergence_score(
        self,
        current_price: float,
        ema_values: List[float]
    ) -> float:
        """
        Calculate average divergence between price and EMAs

        Args:
            current_price: Current price
            ema_values: List of EMA values

        Returns:
            Average percentage divergence (positive = price above EMAs)
        """
        if not ema_values:
            return 0.0

        divergences = [(current_price - ema) / ema * 100 for ema in ema_values if ema > 0]

        if not divergences:
            return 0.0

        return np.mean(divergences)

    def get_color_description(self, ratio: float) -> str:
        """
        Get human-readable description of color/sentiment

        Args:
            ratio: Ratio of EMAs above price (0.0 to 1.0)

        Returns:
            Description string
        """
        if ratio >= 0.9:
            return "Strong Bullish"
        elif ratio >= 0.7:
            return "Bullish"
        elif ratio >= 0.55:
            return "Slightly Bullish"
        elif ratio >= 0.45:
            return "Neutral"
        elif ratio >= 0.3:
            return "Slightly Bearish"
        elif ratio >= 0.1:
            return "Bearish"
        else:
            return "Strong Bearish"
