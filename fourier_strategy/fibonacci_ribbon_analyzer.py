#!/usr/bin/env python3
"""
Fibonacci EMA Ribbon Analyzer with Fourier Transform

Uses Fibonacci sequence (1,2,3,5,8,13,21,34,55,89,144) to create EMA ribbons,
then applies Fourier transform analysis to each ribbon to find:
- Compression zones (ribbons converging)
- Expansion zones (ribbons diverging)
- Alignment patterns (all ribbons pointing same direction)
- Cross patterns (Golden/Death crosses at multiple levels)
- Fractal self-similarity across Fibonacci levels

This reveals natural market structure and optimal entry points.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks


class FibonacciRibbonAnalyzer:
    """
    Analyzes Fibonacci EMA ribbons with Fourier transform

    The Fibonacci sequence naturally appears in market fractals.
    Each EMA period represents a different fractal level.
    """

    # Fibonacci sequence for EMA periods
    FIBONACCI_PERIODS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

    def __init__(self,
                 use_periods: List[int] = None,
                 n_harmonics: int = 5,
                 noise_threshold: float = 0.3):
        """
        Initialize Fibonacci Ribbon Analyzer

        Args:
            use_periods: Which Fibonacci periods to use (default: all 11)
            n_harmonics: Number of harmonics for Fourier filtering
            noise_threshold: Threshold for noise removal
        """
        self.periods = use_periods if use_periods else self.FIBONACCI_PERIODS
        self.n_harmonics = n_harmonics
        self.noise_threshold = noise_threshold

        # Storage for EMAs and their Fourier transforms
        self.emas = {}
        self.fourier_emas = {}
        self.frequencies = {}

    def calculate_emas(self, df: pd.DataFrame) -> Dict[int, pd.Series]:
        """
        Calculate EMA for each Fibonacci period

        Args:
            df: DataFrame with 'close' column

        Returns:
            dict: {period: EMA series}
        """
        print(f"\n📊 Calculating {len(self.periods)} Fibonacci EMAs...")

        for period in self.periods:
            self.emas[period] = df['close'].ewm(span=period, adjust=False).mean()

        print(f"   ✅ Calculated EMAs: {self.periods}")

        return self.emas

    def apply_fourier_to_ribbons(self) -> Dict[int, pd.Series]:
        """
        Apply Fourier transform to each EMA ribbon

        Returns:
            dict: {period: Fourier-filtered EMA}
        """
        print(f"\n🌊 Applying Fourier transform to each ribbon...")

        for period, ema in self.emas.items():
            # Apply FFT
            signal = ema.values
            n = len(signal)

            # Compute FFT
            fft_values = fft(signal)
            frequencies = fftfreq(n)

            # Keep only top N harmonics
            fft_filtered = fft_values.copy()
            magnitude = np.abs(fft_values)

            # Find top harmonics
            threshold = np.percentile(magnitude, (1 - self.noise_threshold) * 100)
            fft_filtered[magnitude < threshold] = 0

            # Inverse FFT to get filtered signal
            filtered_signal = np.fft.ifft(fft_filtered).real

            self.fourier_emas[period] = pd.Series(filtered_signal, index=ema.index)
            self.frequencies[period] = frequencies

        print(f"   ✅ Fourier filtering complete")

        return self.fourier_emas

    def calculate_ribbon_compression(self, window: int = 20) -> pd.Series:
        """
        Calculate ribbon compression score

        Compression = std of all EMAs / mean of all EMAs
        High compression → Ribbons converging → Potential breakout

        Args:
            window: Rolling window for compression calculation

        Returns:
            Series: Compression score (0-1, higher = more compressed)
        """
        # Stack all EMAs into a DataFrame
        ema_df = pd.DataFrame(self.fourier_emas)

        # Calculate rolling std and mean across all EMAs
        ribbon_std = ema_df.std(axis=1)
        ribbon_mean = ema_df.mean(axis=1)

        # Compression = 1 - (std / mean)
        # Higher value = more compressed
        compression = 1 - (ribbon_std / ribbon_mean)

        # Normalize to 0-100
        compression_score = compression * 100

        return compression_score.fillna(0)

    def calculate_ribbon_alignment(self) -> pd.Series:
        """
        Calculate ribbon alignment score

        Alignment = % of ribbons pointing in same direction
        100% = all ribbons trending same way → Strong trend

        Returns:
            Series: Alignment score (-100 to +100)
                    +100 = all ribbons bullish
                    -100 = all ribbons bearish
        """
        alignment_scores = []

        # Get all Fourier-filtered EMAs
        ema_df = pd.DataFrame(self.fourier_emas)

        for i in range(len(ema_df)):
            if i < 5:  # Need history for slope calculation
                alignment_scores.append(0)
                continue

            # Calculate slope for each EMA (recent 5 periods)
            slopes = []
            for period in self.periods:
                ema_values = ema_df[period].iloc[i-5:i+1].values
                if len(ema_values) > 1:
                    slope = (ema_values[-1] - ema_values[0]) / len(ema_values)
                    slopes.append(1 if slope > 0 else -1)

            # Calculate alignment
            if slopes:
                bullish_count = sum(1 for s in slopes if s > 0)
                bearish_count = sum(1 for s in slopes if s < 0)
                total = len(slopes)

                if bullish_count > bearish_count:
                    alignment = (bullish_count / total) * 100
                else:
                    alignment = -(bearish_count / total) * 100

                alignment_scores.append(alignment)
            else:
                alignment_scores.append(0)

        return pd.Series(alignment_scores, index=ema_df.index)

    def detect_golden_crosses(self, fast_period: int = 13, slow_period: int = 55) -> pd.Series:
        """
        Detect Golden/Death crosses between Fibonacci EMAs

        Golden Cross (bullish): Fast EMA crosses above Slow EMA
        Death Cross (bearish): Fast EMA crosses below Slow EMA

        Args:
            fast_period: Fast EMA period (default: 13)
            slow_period: Slow EMA period (default: 55)

        Returns:
            Series: Cross signals (+1 = golden, -1 = death, 0 = no cross)
        """
        if fast_period not in self.fourier_emas or slow_period not in self.fourier_emas:
            return pd.Series(0, index=self.fourier_emas[self.periods[0]].index)

        fast_ema = self.fourier_emas[fast_period]
        slow_ema = self.fourier_emas[slow_period]

        # Detect crosses
        crosses = []
        for i in range(len(fast_ema)):
            if i == 0:
                crosses.append(0)
                continue

            # Previous and current positions
            prev_fast = fast_ema.iloc[i-1]
            prev_slow = slow_ema.iloc[i-1]
            curr_fast = fast_ema.iloc[i]
            curr_slow = slow_ema.iloc[i]

            # Golden cross: fast crosses above slow
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                crosses.append(1)
            # Death cross: fast crosses below slow
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                crosses.append(-1)
            else:
                crosses.append(0)

        return pd.Series(crosses, index=fast_ema.index)

    def calculate_fibonacci_confluence(self) -> pd.Series:
        """
        Calculate overall Fibonacci confluence score

        Combines:
        - Ribbon compression (higher = better)
        - Ribbon alignment (absolute value, higher = better)
        - Multiple cross confirmations
        - Fractal harmony (EMAs at golden ratio)

        Returns:
            Series: Confluence score (0-100)
        """
        print("\n🎯 Calculating Fibonacci confluence...")

        # 1. Compression score (0-100)
        compression = self.calculate_ribbon_compression()

        # 2. Alignment score (0-100)
        alignment = self.calculate_ribbon_alignment().abs()

        # 3. Multiple timeframe crosses
        # Check crosses at different Fibonacci levels
        cross_13_55 = self.detect_golden_crosses(13, 55)
        cross_21_89 = self.detect_golden_crosses(21, 89)
        cross_34_144 = self.detect_golden_crosses(34, 144)

        # Cross confirmation score
        cross_score = (cross_13_55.abs() + cross_21_89.abs() + cross_34_144.abs()) * 33.33

        # 4. Fractal harmony (EMAs at golden ratio positions)
        ema_df = pd.DataFrame(self.fourier_emas)

        # Check if EMAs are in Golden Ratio relationship (1.618)
        harmony_scores = []
        for i in range(len(ema_df)):
            # Compare consecutive Fibonacci levels
            harmony = 0
            count = 0
            for j in range(len(self.periods) - 1):
                p1 = self.periods[j]
                p2 = self.periods[j + 1]

                if p1 in ema_df.columns and p2 in ema_df.columns:
                    v1 = ema_df[p1].iloc[i]
                    v2 = ema_df[p2].iloc[i]

                    # Golden ratio check
                    if v1 > 0:
                        ratio = v2 / v1
                        # Check if ratio is close to Fibonacci ratio
                        expected_ratio = p2 / p1
                        harmony += 100 * (1 - abs(ratio - expected_ratio) / expected_ratio)
                        count += 1

            harmony_scores.append(harmony / count if count > 0 else 0)

        harmony = pd.Series(harmony_scores, index=ema_df.index)

        # Combine all factors (weighted)
        confluence = (
            compression * 0.25 +      # 25% weight
            alignment * 0.25 +         # 25% weight
            cross_score * 0.30 +       # 30% weight
            harmony * 0.20             # 20% weight
        )

        print(f"   ✅ Confluence calculated")
        print(f"      Avg Compression: {compression.mean():.2f}")
        print(f"      Avg Alignment: {alignment.mean():.2f}")
        print(f"      Cross Signals: {cross_score.sum()}")
        print(f"      Avg Harmony: {harmony.mean():.2f}")

        return confluence.fillna(0)

    def generate_fibonacci_signals(self,
                                   confluence_threshold: float = 60,
                                   alignment_threshold: float = 70) -> pd.DataFrame:
        """
        Generate trading signals based on Fibonacci ribbon analysis

        Args:
            confluence_threshold: Minimum confluence score for signal
            alignment_threshold: Minimum alignment score for directional bias

        Returns:
            DataFrame with signals and scores
        """
        print(f"\n🎯 Generating Fibonacci signals...")
        print(f"   Confluence threshold: {confluence_threshold}")
        print(f"   Alignment threshold: {alignment_threshold}")

        # Calculate all components
        confluence = self.calculate_fibonacci_confluence()
        alignment = self.calculate_ribbon_alignment()
        compression = self.calculate_ribbon_compression()

        # Generate signals
        signals = pd.DataFrame(index=confluence.index)
        signals['fibonacci_confluence'] = confluence
        signals['fibonacci_alignment'] = alignment
        signals['fibonacci_compression'] = compression

        # Signal generation logic
        signals['fibonacci_signal'] = 0

        # Long signal: High confluence + Bullish alignment
        long_condition = (
            (confluence > confluence_threshold) &
            (alignment > alignment_threshold) &
            (compression > 60)  # Ribbons compressed (potential breakout)
        )

        # Short signal: High confluence + Bearish alignment
        short_condition = (
            (confluence > confluence_threshold) &
            (alignment < -alignment_threshold) &
            (compression > 60)
        )

        signals.loc[long_condition, 'fibonacci_signal'] = 1
        signals.loc[short_condition, 'fibonacci_signal'] = -1

        print(f"   ✅ Generated {len(signals[signals['fibonacci_signal'] == 1])} long signals")
        print(f"   ✅ Generated {len(signals[signals['fibonacci_signal'] == -1])} short signals")

        return signals

    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Complete Fibonacci ribbon analysis

        Args:
            df: OHLCV DataFrame

        Returns:
            dict with all analysis results
        """
        print("\n" + "="*70)
        print("FIBONACCI RIBBON ANALYSIS")
        print("="*70)

        # Calculate EMAs
        self.calculate_emas(df)

        # Apply Fourier transform
        self.apply_fourier_to_ribbons()

        # Generate signals
        signals = self.generate_fibonacci_signals()

        # Merge with original dataframe
        result_df = df.copy()
        result_df = pd.concat([result_df, signals], axis=1)

        # Add individual Fibonacci EMAs to dataframe
        for period in self.periods:
            result_df[f'fib_ema_{period}'] = self.fourier_emas[period]

        print("\n✅ Fibonacci analysis complete!")

        return {
            'df': result_df,
            'emas': self.emas,
            'fourier_emas': self.fourier_emas,
            'signals': signals,
            'n_long_signals': len(signals[signals['fibonacci_signal'] == 1]),
            'n_short_signals': len(signals[signals['fibonacci_signal'] == -1])
        }


if __name__ == '__main__':
    """Test Fibonacci Ribbon Analyzer"""
    print("Fibonacci Ribbon Analyzer - Test Mode")
    print("\nThis module analyzes Fibonacci EMA ribbons with Fourier transform")
    print("to find optimal confluence entry points.\n")

    print("Fibonacci periods used:", FibonacciRibbonAnalyzer.FIBONACCI_PERIODS)
    print("\nIntegrate this with the Fourier strategy for enhanced signals!")
