"""
Technical Indicators with Fourier Filtering

This module implements various technical indicators with Fourier Transform
filtering applied to detect true signals and filter out noise.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
from .fourier_processor import FourierTransformProcessor


class FourierIndicators:
    """
    Technical indicators with Fourier filtering.

    Implements:
    - RSI with Fourier filtering
    - MACD with Fourier filtering
    - Volume analysis with Fourier
    - ATR with Fourier
    - Stochastic with Fourier
    - Bollinger Band Width with Fourier
    """

    def __init__(self,
                 rsi_period: int = 14,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 atr_period: int = 14,
                 stoch_k_period: int = 14,
                 stoch_d_period: int = 3,
                 bb_period: int = 20,
                 bb_std: float = 2.0,
                 n_harmonics: int = 5,
                 noise_threshold: float = 0.3):
        """
        Initialize Fourier Indicators.

        Args:
            rsi_period: RSI period (default: 14)
            macd_fast: MACD fast period (default: 12)
            macd_slow: MACD slow period (default: 26)
            macd_signal: MACD signal period (default: 9)
            atr_period: ATR period (default: 14)
            stoch_k_period: Stochastic K period (default: 14)
            stoch_d_period: Stochastic D period (default: 3)
            bb_period: Bollinger Band period (default: 20)
            bb_std: Bollinger Band standard deviations (default: 2.0)
            n_harmonics: Harmonics for Fourier (default: 5)
            noise_threshold: Noise threshold (default: 0.3)
        """
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.atr_period = atr_period
        self.stoch_k_period = stoch_k_period
        self.stoch_d_period = stoch_d_period
        self.bb_period = bb_period
        self.bb_std = bb_std

        self.fourier = FourierTransformProcessor(
            n_harmonics=n_harmonics,
            noise_threshold=noise_threshold,
            detrend_method='linear'
        )

    # ========== RSI ==========
    def calculate_rsi(self, data: pd.Series, period: int = None) -> pd.Series:
        """Calculate Relative Strength Index."""
        if period is None:
            period = self.rsi_period

        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def fourier_rsi(self, data: pd.Series) -> Dict[str, pd.Series]:
        """RSI with Fourier filtering."""
        # Calculate raw RSI
        rsi_raw = self.calculate_rsi(data)

        # Apply Fourier filtering
        result = self.fourier.process_signal(rsi_raw)
        rsi_filtered = pd.Series(result['filtered'], index=rsi_raw.index)

        # Calculate RSI momentum
        rsi_momentum = rsi_filtered.diff(5)

        # Divergence detection (raw vs filtered)
        divergence = rsi_raw - rsi_filtered

        return {
            'rsi_raw': rsi_raw,
            'rsi_filtered': rsi_filtered,
            'rsi_momentum': rsi_momentum,
            'rsi_divergence': divergence,
            'rsi_phase_momentum': result['phase_momentum']
        }

    # ========== MACD ==========
    def calculate_macd(self, data: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD."""
        ema_fast = data.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = data.ewm(span=self.macd_slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def fourier_macd(self, data: pd.Series) -> Dict[str, pd.Series]:
        """MACD with Fourier filtering."""
        # Calculate raw MACD
        macd_raw, signal_raw, histogram_raw = self.calculate_macd(data)

        # Apply Fourier to MACD line
        result_macd = self.fourier.process_signal(macd_raw)
        macd_filtered = pd.Series(result_macd['filtered'], index=macd_raw.index)

        # Apply Fourier to signal line
        result_signal = self.fourier.process_signal(signal_raw)
        signal_filtered = pd.Series(result_signal['filtered'], index=signal_raw.index)

        # Filtered histogram
        histogram_filtered = macd_filtered - signal_filtered

        # MACD momentum
        macd_momentum = macd_filtered.diff(5)

        return {
            'macd_raw': macd_raw,
            'macd_filtered': macd_filtered,
            'signal_raw': signal_raw,
            'signal_filtered': signal_filtered,
            'histogram_raw': histogram_raw,
            'histogram_filtered': histogram_filtered,
            'macd_momentum': macd_momentum,
            'macd_phase_momentum': result_macd['phase_momentum']
        }

    # ========== Volume ==========
    def fourier_volume(self, volume: pd.Series) -> Dict[str, pd.Series]:
        """Volume analysis with Fourier filtering."""
        # Apply Fourier to volume
        result = self.fourier.process_signal(volume)
        volume_filtered = pd.Series(result['filtered'], index=volume.index)

        # Volume moving average
        volume_ma = volume.rolling(window=20).mean()

        # Filtered volume MA
        volume_filtered_ma = volume_filtered.rolling(window=20).mean()

        # Volume momentum
        volume_momentum = volume_filtered.pct_change(5) * 100

        # Volume anomaly (deviation from filtered)
        volume_anomaly = (volume - volume_filtered) / volume_filtered * 100

        # Volume relative to average
        volume_relative = volume / volume_ma
        volume_filtered_relative = volume_filtered / volume_filtered_ma

        return {
            'volume_raw': volume,
            'volume_filtered': volume_filtered,
            'volume_ma': volume_ma,
            'volume_filtered_ma': volume_filtered_ma,
            'volume_momentum': volume_momentum,
            'volume_anomaly': volume_anomaly,
            'volume_relative': volume_relative,
            'volume_filtered_relative': volume_filtered_relative,
            'volume_phase_momentum': result['phase_momentum']
        }

    # ========== ATR ==========
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calculate Average True Range."""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean()

        return atr

    def fourier_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, pd.Series]:
        """ATR with Fourier filtering."""
        # Calculate raw ATR
        atr_raw = self.calculate_atr(high, low, close)

        # Apply Fourier
        result = self.fourier.process_signal(atr_raw)
        atr_filtered = pd.Series(result['filtered'], index=atr_raw.index)

        # ATR momentum (volatility expansion/contraction)
        atr_momentum = atr_filtered.pct_change(5) * 100

        # Volatility regime
        atr_ma = atr_filtered.rolling(window=20).mean()
        volatility_regime = atr_filtered / atr_ma

        return {
            'atr_raw': atr_raw,
            'atr_filtered': atr_filtered,
            'atr_momentum': atr_momentum,
            'volatility_regime': volatility_regime,
            'atr_phase_momentum': result['phase_momentum']
        }

    # ========== Stochastic ==========
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator."""
        lowest_low = low.rolling(window=self.stoch_k_period).min()
        highest_high = high.rolling(window=self.stoch_k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=self.stoch_d_period).mean()

        return k, d

    def fourier_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, pd.Series]:
        """Stochastic with Fourier filtering."""
        # Calculate raw Stochastic
        k_raw, d_raw = self.calculate_stochastic(high, low, close)

        # Apply Fourier to K line
        result_k = self.fourier.process_signal(k_raw)
        k_filtered = pd.Series(result_k['filtered'], index=k_raw.index)

        # Apply Fourier to D line
        result_d = self.fourier.process_signal(d_raw)
        d_filtered = pd.Series(result_d['filtered'], index=d_raw.index)

        # Stochastic momentum
        stoch_momentum = k_filtered.diff(5)

        return {
            'stoch_k_raw': k_raw,
            'stoch_k_filtered': k_filtered,
            'stoch_d_raw': d_raw,
            'stoch_d_filtered': d_filtered,
            'stoch_momentum': stoch_momentum,
            'stoch_phase_momentum': result_k['phase_momentum']
        }

    # ========== Bollinger Bands ==========
    def calculate_bollinger_bands(self, data: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        ma = data.rolling(window=self.bb_period).mean()
        std = data.rolling(window=self.bb_period).std()

        upper = ma + (self.bb_std * std)
        lower = ma - (self.bb_std * std)

        # Band width
        width = (upper - lower) / ma * 100

        return upper, lower, ma, width

    def fourier_bollinger(self, data: pd.Series) -> Dict[str, pd.Series]:
        """Bollinger Bands with Fourier filtering."""
        # Calculate raw BB
        upper_raw, lower_raw, ma_raw, width_raw = self.calculate_bollinger_bands(data)

        # Apply Fourier to width (volatility measure)
        result = self.fourier.process_signal(width_raw)
        width_filtered = pd.Series(result['filtered'], index=width_raw.index)

        # Width momentum (volatility expansion/contraction)
        width_momentum = width_filtered.diff(5)

        # Bollinger squeeze detection
        width_ma = width_filtered.rolling(window=20).mean()
        bb_squeeze = width_filtered < (0.5 * width_ma)

        # Price position in bands
        price_position = (data - lower_raw) / (upper_raw - lower_raw) * 100

        return {
            'bb_upper': upper_raw,
            'bb_lower': lower_raw,
            'bb_middle': ma_raw,
            'bb_width_raw': width_raw,
            'bb_width_filtered': width_filtered,
            'bb_width_momentum': width_momentum,
            'bb_squeeze': bb_squeeze.astype(int),
            'bb_price_position': price_position,
            'bb_phase_momentum': result['phase_momentum']
        }

    # ========== Composite Processing ==========
    def process_all_indicators(self,
                               open_: pd.Series,
                               high: pd.Series,
                               low: pd.Series,
                               close: pd.Series,
                               volume: pd.Series) -> pd.DataFrame:
        """
        Process all indicators with Fourier filtering.

        Args:
            open_: Open price series
            high: High price series
            low: Low price series
            close: Close price series
            volume: Volume series

        Returns:
            DataFrame with all indicators (raw and filtered)
        """
        df = pd.DataFrame(index=close.index)

        # Price Fourier
        price_result = self.fourier.process_signal(close)
        df['price_filtered'] = price_result['filtered']
        df['price_phase_momentum'] = price_result['phase_momentum']

        # RSI
        rsi_dict = self.fourier_rsi(close)
        for key, value in rsi_dict.items():
            if isinstance(value, pd.Series):
                df[key] = value
            else:
                df[key] = value

        # MACD
        macd_dict = self.fourier_macd(close)
        for key, value in macd_dict.items():
            if isinstance(value, pd.Series):
                df[key] = value
            else:
                df[key] = value

        # Volume
        volume_dict = self.fourier_volume(volume)
        for key, value in volume_dict.items():
            if isinstance(value, pd.Series):
                df[key] = value
            else:
                df[key] = value

        # ATR
        atr_dict = self.fourier_atr(high, low, close)
        for key, value in atr_dict.items():
            if isinstance(value, pd.Series):
                df[key] = value
            else:
                df[key] = value

        # Stochastic
        stoch_dict = self.fourier_stochastic(high, low, close)
        for key, value in stoch_dict.items():
            if isinstance(value, pd.Series):
                df[key] = value
            else:
                df[key] = value

        # Bollinger Bands
        bb_dict = self.fourier_bollinger(close)
        for key, value in bb_dict.items():
            if isinstance(value, pd.Series):
                df[key] = value
            else:
                df[key] = value

        return df

    def get_indicator_signals(self, indicators: pd.DataFrame) -> pd.DataFrame:
        """
        Generate individual signals from each indicator.

        Args:
            indicators: DataFrame with all indicators

        Returns:
            DataFrame with signal strengths for each indicator
        """
        signals = pd.DataFrame(index=indicators.index)

        # RSI signal (-1 to 1)
        # Bullish when RSI filtered is rising and not overbought
        rsi_trend = np.tanh(indicators['rsi_momentum'] / 10)
        rsi_level = (indicators['rsi_filtered'] - 50) / 50  # Normalize around 50
        signals['rsi_signal'] = (rsi_trend + rsi_level) / 2
        signals['rsi_signal'] = signals['rsi_signal'].clip(-1, 1)

        # MACD signal
        macd_cross = np.sign(indicators['histogram_filtered'])
        macd_momentum = np.tanh(indicators['macd_momentum'] / indicators['macd_filtered'].std())
        signals['macd_signal'] = (macd_cross + macd_momentum) / 2
        signals['macd_signal'] = signals['macd_signal'].clip(-1, 1)

        # Volume signal (confirmation)
        # High volume + rising = bullish confirmation
        volume_strength = np.tanh((indicators['volume_filtered_relative'] - 1) * 2)
        volume_trend = np.tanh(indicators['volume_momentum'] / 10)
        signals['volume_signal'] = (volume_strength + volume_trend) / 2
        signals['volume_signal'] = signals['volume_signal'].clip(-1, 1)

        # ATR signal (volatility)
        # Expanding volatility can confirm trend
        signals['atr_signal'] = np.tanh(indicators['atr_momentum'] / 10)
        signals['atr_signal'] = signals['atr_signal'].clip(-1, 1)

        # Stochastic signal
        stoch_level = (indicators['stoch_k_filtered'] - 50) / 50
        stoch_trend = np.tanh(indicators['stoch_momentum'] / 10)
        signals['stoch_signal'] = (stoch_level + stoch_trend) / 2
        signals['stoch_signal'] = signals['stoch_signal'].clip(-1, 1)

        # BB signal (volatility breakout)
        # Squeeze release + price position
        bb_expansion = np.tanh(indicators['bb_width_momentum'] / 10)
        bb_position = (indicators['bb_price_position'] - 50) / 50
        signals['bb_signal'] = (bb_expansion + bb_position) / 2
        signals['bb_signal'] = signals['bb_signal'].clip(-1, 1)

        return signals
