#!/usr/bin/env python3
"""
Fibonacci Signal Generator for Live Trading - ENHANCED

Integrates:
1. Fibonacci Ribbon + FFT analysis (11 EMAs)
2. Volume FFT analysis (volume patterns)
3. Fibonacci Price Levels (retracement & extension)

This creates multi-dimensional signals combining:
- Price ribbon patterns
- Volume confirmation
- Key price level proximity
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
import logging
from scipy import signal as scipy_signal

# Add paths for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'fourier_strategy'))

from fourier_strategy.fibonacci_ribbon_analyzer import FibonacciRibbonAnalyzer

logger = logging.getLogger(__name__)


class FibonacciSignalGenerator:
    """
    Generate trading signals from Fibonacci Ribbons + FFT analysis + Volume FFT + Fib Levels

    Features:
    - 11 Fibonacci EMAs (1,2,3,5,8,13,21,34,55,89,144) each filtered with FFT
    - Volume FFT analysis for volume pattern detection
    - Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%, 78.6%)
    - Fibonacci extension levels (127.2%, 161.8%, 261.8%)
    """

    # Fibonacci retracement levels
    FIB_RETRACEMENT = [0.236, 0.382, 0.5, 0.618, 0.786]

    # Fibonacci extension levels
    FIB_EXTENSION = [1.272, 1.618, 2.618]

    def __init__(
        self,
        compression_threshold: float = 80,
        alignment_threshold: float = 80,
        confluence_threshold: float = 55,
        n_harmonics: int = 5,
        noise_threshold: float = 0.25,
        base_ema_period: int = 20,
        correlation_threshold: float = 0.55,
        min_signal_strength: float = 0.25,
        max_holding_periods: int = 24,
        use_volume_fft: bool = True,
        use_fib_levels: bool = True,
        volume_confirmation_weight: float = 0.15,
        fib_level_weight: float = 0.1
    ):
        """
        Initialize Fibonacci Signal Generator

        Args:
            compression_threshold: How tight ribbons must be (70-95)
            alignment_threshold: How aligned ribbons must be (70-95)
            confluence_threshold: Overall signal agreement (55-80)
            n_harmonics: Number of FFT harmonics (3-10)
            noise_threshold: FFT noise filtering (0.15-0.5)
            base_ema_period: Base EMA period (10-30)
            correlation_threshold: Min correlation for validity (0.4-0.8)
            min_signal_strength: Minimum signal strength (0.15-0.4)
            max_holding_periods: Max periods to hold (12-48)
            use_volume_fft: Apply FFT to volume for pattern detection
            use_fib_levels: Use Fibonacci price levels for entry/exit
            volume_confirmation_weight: Weight of volume signal (0.0-0.3)
            fib_level_weight: Weight of Fibonacci level proximity (0.0-0.2)
        """
        self.compression_threshold = compression_threshold
        self.alignment_threshold = alignment_threshold
        self.confluence_threshold = confluence_threshold
        self.n_harmonics = n_harmonics
        self.noise_threshold = noise_threshold
        self.base_ema_period = base_ema_period
        self.correlation_threshold = correlation_threshold
        self.min_signal_strength = min_signal_strength
        self.max_holding_periods = max_holding_periods
        self.use_volume_fft = use_volume_fft
        self.use_fib_levels = use_fib_levels
        self.volume_confirmation_weight = volume_confirmation_weight
        self.fib_level_weight = fib_level_weight

        # Initialize analyzer
        self.analyzer = FibonacciRibbonAnalyzer(
            n_harmonics=n_harmonics,
            noise_threshold=noise_threshold
        )

        logger.info(
            f"FibonacciSignalGenerator initialized (ENHANCED):\n"
            f"  Compression: {compression_threshold}\n"
            f"  Alignment: {alignment_threshold}\n"
            f"  Confluence: {confluence_threshold}\n"
            f"  FFT Harmonics: {n_harmonics}\n"
            f"  Noise Threshold: {noise_threshold}\n"
            f"  Volume FFT: {'Enabled' if use_volume_fft else 'Disabled'}\n"
            f"  Fib Levels: {'Enabled' if use_fib_levels else 'Disabled'}"
        )

    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Generate trading signal from price data

        Args:
            df: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        Returns:
            Signal dict with:
            - signal: 'LONG', 'SHORT', or 'NEUTRAL'
            - strength: 0.0-1.0 (signal strength)
            - confidence: 0.0-1.0 (confidence level)
            - compression: Ribbon compression score
            - alignment: Ribbon alignment score
            - confluence: Overall confluence score
        """
        try:
            if len(df) < 200:
                logger.debug(f"Not enough data: {len(df)} < 200 candles")
                return None

            # Run Fibonacci Ribbon analysis
            results = self.analyzer.analyze(df)
            signals = results['signals']

            if signals is None or len(signals) == 0:
                return None

            # Get latest values
            latest_compression = float(signals['fibonacci_compression'].iloc[-1])
            latest_alignment = float(signals['fibonacci_alignment'].iloc[-1])
            latest_confluence = float(signals['fibonacci_confluence'].iloc[-1])

            # Check thresholds for signal generation
            compression_met = latest_compression > self.compression_threshold
            alignment_met = abs(latest_alignment) > self.alignment_threshold
            confluence_met = latest_confluence > self.confluence_threshold

            # ENHANCED: Add Volume FFT and Fibonacci levels analysis
            volume_momentum = 0.5
            fib_proximity = 0.5
            fib_levels = {}

            if self.use_volume_fft and 'volume' in df.columns:
                try:
                    volume_data = df['volume'].values
                    _, volume_momentum = self._apply_fft_to_volume(volume_data)
                    logger.debug(f"Volume momentum: {volume_momentum:.2f}")
                except Exception as e:
                    logger.error(f"Volume FFT error: {e}")

            if self.use_fib_levels:
                try:
                    fib_levels = self._calculate_fibonacci_levels(df)
                    if fib_levels:
                        current_price = float(df['close'].iloc[-1])
                        fib_proximity = self._check_fib_level_proximity(current_price, fib_levels)
                        logger.debug(f"Fib level proximity: {fib_proximity:.2f}")
                except Exception as e:
                    logger.error(f"Fibonacci levels error: {e}")

            # Determine signal direction
            if compression_met and alignment_met and confluence_met:
                if latest_alignment > 0:
                    signal_type = 'LONG'
                else:
                    signal_type = 'SHORT'

                # Calculate BASE strength (normalized to 0-1)
                base_strength = (
                    (latest_compression / 100) * 0.4 +
                    (abs(latest_alignment) / 100) * 0.4 +
                    (latest_confluence / 100) * 0.2
                )

                # ENHANCE strength with volume and fib levels
                volume_boost = (volume_momentum - 0.5) * self.volume_confirmation_weight
                fib_boost = (fib_proximity - 0.5) * self.fib_level_weight

                strength = min(base_strength + volume_boost + fib_boost, 1.0)

                # Calculate confidence based on how far above thresholds we are
                compression_margin = (latest_compression - self.compression_threshold) / (100 - self.compression_threshold)
                alignment_margin = (abs(latest_alignment) - self.alignment_threshold) / (100 - self.alignment_threshold)
                confluence_margin = (latest_confluence - self.confluence_threshold) / (100 - self.confluence_threshold)

                base_confidence = (
                    compression_margin * 0.3 +
                    alignment_margin * 0.4 +
                    confluence_margin * 0.3
                )

                # ENHANCE confidence with volume and fib confirmations
                confidence = min(base_confidence + volume_boost + fib_boost, 1.0)

                logger.info(
                    f"🎯 ENHANCED Fibonacci Signal Generated:\n"
                    f"  Type: {signal_type}\n"
                    f"  Strength: {strength:.2f} (base={base_strength:.2f}, vol_boost={volume_boost:+.2f}, fib_boost={fib_boost:+.2f})\n"
                    f"  Confidence: {confidence:.2f}\n"
                    f"  Compression: {latest_compression:.1f} (threshold: {self.compression_threshold})\n"
                    f"  Alignment: {latest_alignment:.1f} (threshold: {self.alignment_threshold})\n"
                    f"  Confluence: {latest_confluence:.1f} (threshold: {self.confluence_threshold})\n"
                    f"  Volume Momentum: {volume_momentum:.2f}\n"
                    f"  Fib Level Proximity: {fib_proximity:.2f}"
                )

                return {
                    'signal': signal_type,
                    'strength': max(strength, self.min_signal_strength),
                    'confidence': confidence,
                    'compression': latest_compression,
                    'alignment': latest_alignment,
                    'confluence': latest_confluence,
                    'volume_momentum': volume_momentum,
                    'fib_proximity': fib_proximity,
                    'fib_levels': fib_levels,
                    'source': 'fibonacci_fft_enhanced',
                    'thresholds_met': {
                        'compression': compression_met,
                        'alignment': alignment_met,
                        'confluence': confluence_met
                    },
                    'enhancements': {
                        'volume_fft_enabled': self.use_volume_fft,
                        'fib_levels_enabled': self.use_fib_levels,
                        'volume_boost': volume_boost,
                        'fib_boost': fib_boost
                    }
                }
            else:
                logger.debug(
                    f"Thresholds not met - "
                    f"Compression: {latest_compression:.1f}/{self.compression_threshold} "
                    f"Alignment: {abs(latest_alignment):.1f}/{self.alignment_threshold} "
                    f"Confluence: {latest_confluence:.1f}/{self.confluence_threshold}"
                )
                return None

        except Exception as e:
            logger.error(f"Error generating Fibonacci signal: {e}", exc_info=True)
            return None

    def _apply_fft_to_volume(self, volume: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Apply FFT to volume data to detect patterns

        Returns:
            - Filtered volume signal
            - Volume momentum score (0-1)
        """
        try:
            if len(volume) < 50:
                return volume, 0.5

            # Apply FFT
            fft = np.fft.fft(volume)
            frequencies = np.fft.fftfreq(len(volume))

            # Keep only n_harmonics strongest frequencies
            magnitudes = np.abs(fft)
            threshold = np.sort(magnitudes)[-self.n_harmonics]

            # Filter
            fft_filtered = fft.copy()
            fft_filtered[magnitudes < threshold] = 0

            # Inverse FFT
            volume_filtered = np.real(np.fft.ifft(fft_filtered))

            # Calculate momentum (recent vs average)
            recent_vol = volume_filtered[-20:].mean()
            avg_vol = volume_filtered.mean()

            if avg_vol > 0:
                volume_momentum = min(recent_vol / avg_vol, 2.0) / 2.0
            else:
                volume_momentum = 0.5

            return volume_filtered, volume_momentum

        except Exception as e:
            logger.error(f"Error in volume FFT: {e}")
            return volume, 0.5

    def _calculate_fibonacci_levels(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """
        Calculate Fibonacci retracement and extension levels from recent swing

        Returns dict with:
            - retracement_levels: List of retracement prices
            - extension_levels: List of extension prices
            - swing_high: Recent high
            - swing_low: Recent low
        """
        try:
            if len(df) < 100:
                return {}

            # Find recent swing high/low (last 50-100 candles)
            lookback = min(100, len(df))
            recent_prices = df['close'].iloc[-lookback:].values

            swing_high = recent_prices.max()
            swing_low = recent_prices.min()
            swing_range = swing_high - swing_low

            if swing_range == 0:
                return {}

            # Calculate retracement levels (from high to low)
            retracement_levels = [
                swing_high - (swing_range * level)
                for level in self.FIB_RETRACEMENT
            ]

            # Calculate extension levels (beyond the range)
            extension_levels = [
                swing_low - (swing_range * (level - 1.0))
                for level in self.FIB_EXTENSION
            ]

            return {
                'retracement_levels': retracement_levels,
                'extension_levels': extension_levels,
                'swing_high': swing_high,
                'swing_low': swing_low,
                'swing_range': swing_range
            }

        except Exception as e:
            logger.error(f"Error calculating Fibonacci levels: {e}")
            return {}

    def _check_fib_level_proximity(self, current_price: float, fib_levels: Dict) -> float:
        """
        Check how close current price is to a Fibonacci level

        Returns score 0.0-1.0:
        - 1.0 = right at a Fibonacci level
        - 0.0 = far from any level
        """
        try:
            if not fib_levels or 'retracement_levels' not in fib_levels:
                return 0.5

            all_levels = (
                fib_levels['retracement_levels'] +
                fib_levels['extension_levels']
            )

            # Find closest level
            distances = [abs(current_price - level) for level in all_levels]
            min_distance = min(distances)

            # Normalize by swing range
            swing_range = fib_levels.get('swing_range', 1.0)
            if swing_range > 0:
                normalized_distance = min_distance / swing_range
            else:
                normalized_distance = 1.0

            # Convert to proximity score (closer = higher score)
            # Within 2% of range = strong proximity
            proximity_score = max(0.0, 1.0 - (normalized_distance / 0.02))

            return proximity_score

        except Exception as e:
            logger.error(f"Error checking Fib level proximity: {e}")
            return 0.5

    def get_current_regime(self, df: pd.DataFrame) -> str:
        """
        Determine current market regime from Fibonacci ribbons

        Returns: 'trending', 'volatile', 'stable', 'mean_reverting'
        """
        try:
            if len(df) < 200:
                return 'stable'

            results = self.analyzer.analyze(df)
            signals = results['signals']

            if signals is None or len(signals) == 0:
                return 'stable'

            # Analyze recent behavior
            recent = signals.tail(50)

            compression = recent['fibonacci_compression'].mean()
            alignment = recent['fibonacci_alignment'].abs().mean()
            confluence = recent['fibonacci_confluence'].mean()

            # High alignment + high compression = trending
            if alignment > 70 and compression > 70:
                return 'trending'

            # Low compression = volatile/expanding
            elif compression < 50:
                return 'volatile'

            # Low alignment = mean reverting
            elif alignment < 40:
                return 'mean_reverting'

            # Otherwise stable
            else:
                return 'stable'

        except Exception as e:
            logger.error(f"Error determining regime: {e}")
            return 'stable'


if __name__ == '__main__':
    """Test Fibonacci Signal Generator"""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("🧪 Testing Fibonacci Signal Generator with Iteration 3 params...")

    # Initialize with Iteration 3 (aggressive) parameters
    generator = FibonacciSignalGenerator(
        compression_threshold=80,
        alignment_threshold=80,
        confluence_threshold=55
    )

    print("✅ Generator initialized successfully")
    print(f"\nParameters:")
    print(f"  Compression threshold: {generator.compression_threshold}")
    print(f"  Alignment threshold: {generator.alignment_threshold}")
    print(f"  Confluence threshold: {generator.confluence_threshold}")
    print(f"  FFT Harmonics: {generator.n_harmonics}")
