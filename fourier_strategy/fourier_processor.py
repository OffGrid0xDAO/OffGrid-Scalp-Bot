"""
Fourier Transform Processor for Signal Filtering

This module provides advanced signal processing using FFT to filter noise
from financial time series data and extract dominant frequency components.
"""

import numpy as np
from scipy import signal
from scipy.fft import fft, ifft, fftfreq
from typing import Tuple, Optional, Dict
import pandas as pd


class FourierTransformProcessor:
    """
    Core Fourier Transform processor for filtering financial signals.

    Features:
    - Detrending to remove bias before FFT
    - Dominant harmonic extraction
    - Noise filtering
    - Phase and amplitude analysis
    - Causal filtering (no look-ahead bias)
    """

    def __init__(self,
                 n_harmonics: int = 5,
                 noise_threshold: float = 0.3,
                 detrend_method: str = 'linear'):
        """
        Initialize Fourier Transform Processor.

        Args:
            n_harmonics: Number of dominant harmonics to keep (default: 5)
            noise_threshold: Threshold for noise filtering (0-1, default: 0.3)
            detrend_method: Method for detrending ('linear', 'constant', or None)
        """
        self.n_harmonics = n_harmonics
        self.noise_threshold = noise_threshold
        self.detrend_method = detrend_method

    def detrend_signal(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Remove trend from signal before FFT.

        Args:
            data: Input signal array

        Returns:
            Tuple of (detrended_signal, trend)
        """
        if self.detrend_method == 'linear':
            # Linear detrending
            trend = signal.detrend(data, type='linear')
            original_trend = data - trend
            return trend, original_trend
        elif self.detrend_method == 'constant':
            # Remove mean
            trend = signal.detrend(data, type='constant')
            original_trend = data - trend
            return trend, original_trend
        else:
            # No detrending
            return data, np.zeros_like(data)

    def apply_fft(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Apply FFT to signal.

        Args:
            data: Input signal array

        Returns:
            Tuple of (frequencies, fft_values, power_spectrum)
        """
        n = len(data)

        # Apply FFT
        fft_values = fft(data)
        frequencies = fftfreq(n)

        # Calculate power spectrum
        power_spectrum = np.abs(fft_values) ** 2

        return frequencies, fft_values, power_spectrum

    def get_dominant_frequencies(self,
                                 frequencies: np.ndarray,
                                 power_spectrum: np.ndarray) -> np.ndarray:
        """
        Extract dominant frequency components.

        Args:
            frequencies: Frequency array from FFT
            power_spectrum: Power spectrum from FFT

        Returns:
            Indices of dominant frequencies
        """
        # Only consider positive frequencies (Nyquist theorem)
        positive_freq_idx = frequencies > 0
        positive_freqs = frequencies[positive_freq_idx]
        positive_power = power_spectrum[positive_freq_idx]

        # Sort by power and get top N harmonics
        sorted_indices = np.argsort(positive_power)[::-1]

        # Get top N harmonics
        top_indices = sorted_indices[:self.n_harmonics]

        return top_indices

    def filter_noise(self,
                    fft_values: np.ndarray,
                    power_spectrum: np.ndarray) -> np.ndarray:
        """
        Filter out noise by keeping only significant frequency components.

        Args:
            fft_values: FFT coefficients
            power_spectrum: Power spectrum

        Returns:
            Filtered FFT coefficients
        """
        # Calculate threshold based on maximum power
        max_power = np.max(power_spectrum)
        threshold = self.noise_threshold * max_power

        # Create mask for significant frequencies
        mask = power_spectrum >= threshold

        # Apply mask to FFT values
        filtered_fft = fft_values.copy()
        filtered_fft[~mask] = 0

        return filtered_fft

    def keep_top_harmonics(self,
                          fft_values: np.ndarray,
                          frequencies: np.ndarray,
                          power_spectrum: np.ndarray) -> np.ndarray:
        """
        Keep only top N dominant harmonics.

        Args:
            fft_values: FFT coefficients
            frequencies: Frequency array
            power_spectrum: Power spectrum

        Returns:
            Filtered FFT with only top harmonics
        """
        filtered_fft = np.zeros_like(fft_values)

        # Get dominant frequency indices
        positive_freq_idx = frequencies > 0
        positive_power = power_spectrum[positive_freq_idx]

        # Sort and get top N
        sorted_indices = np.argsort(positive_power)[::-1]
        top_indices = sorted_indices[:self.n_harmonics]

        # Map back to full frequency array
        positive_indices = np.where(positive_freq_idx)[0]
        top_full_indices = positive_indices[top_indices]

        # Keep DC component (mean)
        filtered_fft[0] = fft_values[0]

        # Keep top harmonics (both positive and negative frequencies)
        for idx in top_full_indices:
            filtered_fft[idx] = fft_values[idx]
            # Also keep corresponding negative frequency (symmetry)
            filtered_fft[-idx] = fft_values[-idx]

        return filtered_fft

    def reconstruct_signal(self,
                          filtered_fft: np.ndarray,
                          trend: np.ndarray) -> np.ndarray:
        """
        Reconstruct time-domain signal from filtered FFT.

        Args:
            filtered_fft: Filtered FFT coefficients
            trend: Original trend to add back

        Returns:
            Reconstructed signal
        """
        # Inverse FFT
        reconstructed = np.real(ifft(filtered_fft))

        # Add trend back
        reconstructed += trend

        return reconstructed

    def calculate_phase_momentum(self, fft_values: np.ndarray) -> float:
        """
        Calculate phase-based momentum indicator.

        Args:
            fft_values: FFT coefficients

        Returns:
            Phase momentum (-1 to 1)
        """
        # Get phase angles
        phases = np.angle(fft_values)

        # Calculate phase momentum (rate of change)
        phase_diff = np.diff(phases)

        # Normalize to [-1, 1]
        momentum = np.tanh(np.mean(phase_diff))

        return momentum

    def process_signal(self, data: pd.Series) -> Dict[str, np.ndarray]:
        """
        Complete signal processing pipeline.

        Args:
            data: Input signal as pandas Series

        Returns:
            Dictionary containing:
                - 'filtered': Filtered signal
                - 'raw': Original signal
                - 'frequencies': Frequency components
                - 'power_spectrum': Power spectrum
                - 'phase_momentum': Phase-based momentum
                - 'dominant_freqs': Dominant frequency values
        """
        # Convert to numpy array and handle NaN
        signal_array = data.values

        # Remove NaN values (forward fill)
        mask = ~np.isnan(signal_array)
        if not mask.all():
            signal_array = pd.Series(signal_array).fillna(method='ffill').fillna(method='bfill').values

        # Minimum length check
        if len(signal_array) < 10:
            return {
                'filtered': signal_array,
                'raw': signal_array,
                'frequencies': np.array([]),
                'power_spectrum': np.array([]),
                'phase_momentum': 0.0,
                'dominant_freqs': np.array([])
            }

        # Detrend
        detrended, trend = self.detrend_signal(signal_array)

        # Apply FFT
        frequencies, fft_values, power_spectrum = self.apply_fft(detrended)

        # Filter - keep top harmonics
        filtered_fft = self.keep_top_harmonics(fft_values, frequencies, power_spectrum)

        # Reconstruct signal
        filtered_signal = self.reconstruct_signal(filtered_fft, trend)

        # Calculate phase momentum
        phase_momentum = self.calculate_phase_momentum(filtered_fft)

        # Get dominant frequency values
        dominant_idx = self.get_dominant_frequencies(frequencies, power_spectrum)
        positive_freqs = frequencies[frequencies > 0]
        dominant_freqs = positive_freqs[dominant_idx] if len(dominant_idx) > 0 else np.array([])

        return {
            'filtered': filtered_signal,
            'raw': signal_array,
            'frequencies': frequencies,
            'power_spectrum': power_spectrum,
            'phase_momentum': phase_momentum,
            'dominant_freqs': dominant_freqs
        }

    def detect_dominant_cycle(self, data: pd.Series) -> int:
        """
        Detect the dominant market cycle length.

        Args:
            data: Input price series

        Returns:
            Dominant cycle length in periods
        """
        result = self.process_signal(data)

        if len(result['dominant_freqs']) == 0:
            return 20  # Default cycle length

        # Get the most dominant frequency
        dominant_freq = result['dominant_freqs'][0]

        # Convert to period (cycle length)
        if dominant_freq != 0:
            cycle_length = int(1 / abs(dominant_freq))
            # Clamp to reasonable range
            cycle_length = max(5, min(200, cycle_length))
        else:
            cycle_length = 20

        return cycle_length

    def adaptive_filtering(self,
                          data: pd.Series,
                          volatility: pd.Series) -> np.ndarray:
        """
        Adaptive filtering based on market regime (volatility).

        High volatility -> more harmonics (keep more detail)
        Low volatility -> fewer harmonics (smooth more)

        Args:
            data: Input signal
            volatility: Volatility measure (e.g., ATR)

        Returns:
            Adaptively filtered signal
        """
        # Calculate average volatility
        avg_vol = volatility.mean()
        current_vol = volatility.iloc[-1]

        # Adjust n_harmonics based on volatility regime
        if current_vol > 1.5 * avg_vol:
            # High volatility - keep more harmonics
            original_n = self.n_harmonics
            self.n_harmonics = min(10, int(self.n_harmonics * 1.5))
        elif current_vol < 0.5 * avg_vol:
            # Low volatility - use fewer harmonics
            original_n = self.n_harmonics
            self.n_harmonics = max(3, int(self.n_harmonics * 0.7))
        else:
            original_n = self.n_harmonics

        # Process signal
        result = self.process_signal(data)

        # Restore original setting
        self.n_harmonics = original_n

        return result['filtered']
