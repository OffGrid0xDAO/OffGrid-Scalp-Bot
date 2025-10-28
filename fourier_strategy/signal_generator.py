"""
Signal Generator for Fourier-Based Trading Strategy

This module combines all Fourier-filtered signals to generate
entry/exit signals with confidence scores.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


class SignalGenerator:
    """
    Generates trading signals from Fourier-filtered indicators.

    Combines:
    - Filtered price trend
    - EMA alignment and momentum
    - Technical indicator signals
    - Cross-indicator correlations
    - Phase alignment
    """

    def __init__(self,
                 correlation_threshold: float = 0.7,
                 min_signal_strength: float = 0.5,
                 signal_weights: Dict[str, float] = None,
                 max_holding_periods: int = 336):  # ~2 weeks for hourly data
        """
        Initialize Signal Generator.

        Args:
            correlation_threshold: Minimum correlation for signal confirmation (default: 0.7)
            min_signal_strength: Minimum composite signal strength to trade (default: 0.5)
            signal_weights: Custom weights for each component (default: equal weights)
            max_holding_periods: Maximum bars to hold a position (default: 336 = 2 weeks hourly)
        """
        self.correlation_threshold = correlation_threshold
        self.min_signal_strength = min_signal_strength
        self.max_holding_periods = max_holding_periods

        # Default signal weights
        if signal_weights is None:
            self.signal_weights = {
                'price_trend': 0.20,      # 20% - Filtered price trend
                'ema_alignment': 0.20,     # 20% - EMA ribbon alignment
                'rsi': 0.10,               # 10% - RSI signal
                'macd': 0.15,              # 15% - MACD signal
                'volume': 0.10,            # 10% - Volume confirmation
                'stochastic': 0.10,        # 10% - Stochastic
                'correlation': 0.10,       # 10% - Correlation score
                'phase_momentum': 0.05     # 5%  - Phase alignment
            }
        else:
            self.signal_weights = signal_weights

        # Normalize weights to sum to 1
        total_weight = sum(self.signal_weights.values())
        self.signal_weights = {k: v/total_weight for k, v in self.signal_weights.items()}

    def calculate_price_trend_signal(self,
                                     price_raw: pd.Series,
                                     price_filtered: pd.Series,
                                     lookback: int = 10) -> pd.Series:
        """
        Calculate price trend signal from filtered price.

        Args:
            price_raw: Raw price series
            price_filtered: Filtered price series
            lookback: Lookback period for trend

        Returns:
            Trend signal (-1 to 1)
        """
        # Calculate slope of filtered price
        price_change = price_filtered.pct_change(lookback) * 100

        # Normalize to [-1, 1]
        trend_signal = np.tanh(price_change / 5)

        return trend_signal

    def calculate_composite_signal(self,
                                   price_filtered: pd.Series,
                                   ema_results: Dict,
                                   indicators: pd.DataFrame,
                                   indicator_signals: pd.DataFrame,
                                   correlation_score: pd.Series) -> pd.DataFrame:
        """
        Calculate composite signal from all components.

        Args:
            price_filtered: Filtered price series
            ema_results: Results from MultiTimeframeEMA
            indicators: All indicators (raw and filtered)
            indicator_signals: Individual indicator signals
            correlation_score: Correlation scores

        Returns:
            DataFrame with composite signals and components
        """
        df = pd.DataFrame(index=price_filtered.index)

        # 1. Price trend signal
        price_trend = self.calculate_price_trend_signal(
            price_filtered,
            price_filtered
        )
        df['price_trend_signal'] = price_trend

        # 2. EMA alignment signal
        if 'alignment' in ema_results:
            ema_signal = ema_results['alignment']['filtered_alignment_score']
            df['ema_signal'] = ema_signal
        else:
            df['ema_signal'] = 0

        # 3. Individual indicator signals
        if 'rsi_signal' in indicator_signals.columns:
            df['rsi_signal'] = indicator_signals['rsi_signal']
        else:
            df['rsi_signal'] = 0

        if 'macd_signal' in indicator_signals.columns:
            df['macd_signal'] = indicator_signals['macd_signal']
        else:
            df['macd_signal'] = 0

        if 'volume_signal' in indicator_signals.columns:
            df['volume_signal'] = indicator_signals['volume_signal']
        else:
            df['volume_signal'] = 0

        if 'stoch_signal' in indicator_signals.columns:
            df['stoch_signal'] = indicator_signals['stoch_signal']
        else:
            df['stoch_signal'] = 0

        # 4. Correlation signal (normalized)
        # High correlation = strong confirmation
        corr_signal = (correlation_score - 50) / 50  # Normalize around 50
        df['correlation_signal'] = corr_signal.clip(-1, 1)

        # 5. Phase momentum signal (from price)
        if 'price_phase_momentum' in indicators.columns:
            phase_signal = indicators['price_phase_momentum']
            # Phase momentum is already in reasonable range
            df['phase_signal'] = phase_signal
        else:
            df['phase_signal'] = 0

        # Calculate weighted composite signal
        composite = (
            self.signal_weights['price_trend'] * df['price_trend_signal'] +
            self.signal_weights['ema_alignment'] * df['ema_signal'] +
            self.signal_weights['rsi'] * df['rsi_signal'] +
            self.signal_weights['macd'] * df['macd_signal'] +
            self.signal_weights['volume'] * df['volume_signal'] +
            self.signal_weights['stochastic'] * df['stoch_signal'] +
            self.signal_weights['correlation'] * df['correlation_signal'] +
            self.signal_weights['phase_momentum'] * df['phase_signal']
        )

        df['composite_signal'] = composite.clip(-1, 1)

        return df

    def calculate_signal_confidence(self,
                                    signals_df: pd.DataFrame,
                                    correlation_score: pd.Series,
                                    volatility: pd.Series = None) -> pd.Series:
        """
        Calculate confidence score for signals (0-100).

        Higher confidence when:
        - Multiple indicators agree
        - High correlation between indicators
        - Lower volatility (more predictable)

        Args:
            signals_df: DataFrame with all signal components
            correlation_score: Correlation scores
            volatility: Optional volatility measure

        Returns:
            Confidence score (0-100)
        """
        # 1. Agreement between components
        signal_cols = [col for col in signals_df.columns if 'signal' in col and col != 'composite_signal']

        if len(signal_cols) > 0:
            # Calculate how many signals agree with composite
            composite = signals_df['composite_signal']
            agreements = []

            for col in signal_cols:
                # Signals agree if same sign and similar magnitude
                same_sign = np.sign(signals_df[col]) == np.sign(composite)
                agreements.append(same_sign.astype(int))

            agreement_df = pd.DataFrame(agreements).T
            agreement_score = agreement_df.mean(axis=1) * 100
        else:
            agreement_score = pd.Series(50, index=signals_df.index)

        # 2. Correlation component (0-100 already)
        corr_component = correlation_score

        # 3. Signal strength component
        signal_strength = abs(signals_df['composite_signal']) * 100

        # Weighted confidence
        confidence = (
            0.4 * agreement_score +
            0.3 * corr_component +
            0.3 * signal_strength
        )

        # Adjust for volatility if provided
        if volatility is not None:
            vol_ma = volatility.rolling(window=20).mean()
            vol_factor = 1 - np.tanh((volatility - vol_ma) / vol_ma)  # Lower confidence in high vol
            confidence = confidence * vol_factor

        confidence = confidence.clip(0, 100)

        return confidence

    def generate_entry_exit_signals(self,
                                   signals_df: pd.DataFrame,
                                   confidence: pd.Series) -> pd.DataFrame:
        """
        Generate entry and exit signals based on composite signal and confidence.

        Args:
            signals_df: DataFrame with composite signals
            confidence: Confidence scores

        Returns:
            DataFrame with entry/exit signals and reasons
        """
        df = pd.DataFrame(index=signals_df.index)

        composite = signals_df['composite_signal']

        # Entry conditions
        # LONG: Strong positive signal with reasonable confidence
        long_entry = (
            (composite > self.min_signal_strength) &
            (confidence > 40)  # Lower threshold to allow more trades
        )

        # SHORT: Strong negative signal with reasonable confidence
        short_entry = (
            (composite < -self.min_signal_strength) &
            (confidence > 40)  # Lower threshold to allow more trades
        )

        df['long_entry'] = long_entry.astype(int)
        df['short_entry'] = short_entry.astype(int)

        # Exit conditions
        # Exit LONG when signal turns negative or confidence drops
        long_exit = (
            (composite < 0) |
            (confidence < 25)  # Lower exit threshold
        )

        # Exit SHORT when signal turns positive or confidence drops
        short_exit = (
            (composite > 0) |
            (confidence < 25)  # Lower exit threshold
        )

        df['long_exit'] = long_exit.astype(int)
        df['short_exit'] = short_exit.astype(int)

        # Generate position signals with max holding period
        # 1 = Long, -1 = Short, 0 = No position
        position = pd.Series(0, index=df.index)
        bars_in_position = 0

        for i in range(len(df)):
            if i == 0:
                continue

            prev_position = position.iloc[i-1]

            # Only enter if not already in a position (prevent overtrading)
            # Enter long only when crossing threshold
            if df['long_entry'].iloc[i] and prev_position == 0:
                position.iloc[i] = 1
                bars_in_position = 0
            # Enter short only when crossing threshold
            elif df['short_entry'].iloc[i] and prev_position == 0:
                position.iloc[i] = -1
                bars_in_position = 0
            # Exit long
            elif prev_position == 1 and (df['long_exit'].iloc[i] or bars_in_position >= self.max_holding_periods):
                position.iloc[i] = 0
                bars_in_position = 0
            # Exit short
            elif prev_position == -1 and (df['short_exit'].iloc[i] or bars_in_position >= self.max_holding_periods):
                position.iloc[i] = 0
                bars_in_position = 0
            # Maintain previous position (this prevents re-entering every bar)
            else:
                position.iloc[i] = prev_position
                if prev_position != 0:
                    bars_in_position += 1

        df['position'] = position

        # Generate trade signals (1 = enter long, -1 = enter short, 0 = no change)
        df['trade_signal'] = df['position'].diff().fillna(0)

        return df

    def generate_signal_reasons(self,
                               signals_df: pd.DataFrame,
                               trade_signals: pd.DataFrame) -> pd.DataFrame:
        """
        Generate human-readable reasons for each signal.

        Args:
            signals_df: DataFrame with signal components
            trade_signals: DataFrame with trade signals

        Returns:
            DataFrame with signal reasons
        """
        df = trade_signals.copy()

        reasons = []

        for i in range(len(df)):
            if df['trade_signal'].iloc[i] != 0:
                reason_parts = []

                # Check each component
                if abs(signals_df['price_trend_signal'].iloc[i]) > 0.3:
                    direction = "up" if signals_df['price_trend_signal'].iloc[i] > 0 else "down"
                    reason_parts.append(f"Price trending {direction}")

                if abs(signals_df['ema_signal'].iloc[i]) > 0.5:
                    direction = "bullish" if signals_df['ema_signal'].iloc[i] > 0 else "bearish"
                    reason_parts.append(f"EMA {direction} alignment")

                if abs(signals_df['macd_signal'].iloc[i]) > 0.3:
                    direction = "bullish" if signals_df['macd_signal'].iloc[i] > 0 else "bearish"
                    reason_parts.append(f"MACD {direction}")

                if abs(signals_df['rsi_signal'].iloc[i]) > 0.3:
                    direction = "rising" if signals_df['rsi_signal'].iloc[i] > 0 else "falling"
                    reason_parts.append(f"RSI {direction}")

                if signals_df['volume_signal'].iloc[i] > 0.3:
                    reason_parts.append("High volume confirmation")

                if signals_df['correlation_signal'].iloc[i] > 0.5:
                    reason_parts.append("Strong indicator correlation")

                reason = "; ".join(reason_parts) if reason_parts else "Composite signal threshold met"
                reasons.append(reason)
            else:
                reasons.append("")

        df['signal_reason'] = reasons

        return df

    def process(self,
               price_raw: pd.Series,
               price_filtered: pd.Series,
               ema_results: Dict,
               indicators: pd.DataFrame,
               indicator_signals: pd.DataFrame,
               correlation_score: pd.Series,
               volatility: pd.Series = None) -> Dict[str, pd.DataFrame]:
        """
        Complete signal generation pipeline.

        Args:
            price_raw: Raw price series
            price_filtered: Filtered price series
            ema_results: EMA analysis results
            indicators: All indicators
            indicator_signals: Individual indicator signals
            correlation_score: Correlation scores
            volatility: Optional volatility measure

        Returns:
            Dictionary with:
                - 'signals': Signal components and composite
                - 'confidence': Confidence scores
                - 'trades': Entry/exit signals with reasons
        """
        # Calculate composite signal
        signals_df = self.calculate_composite_signal(
            price_filtered,
            ema_results,
            indicators,
            indicator_signals,
            correlation_score
        )

        # Calculate confidence
        confidence = self.calculate_signal_confidence(
            signals_df,
            correlation_score,
            volatility
        )

        signals_df['confidence'] = confidence

        # Generate entry/exit signals
        trade_signals = self.generate_entry_exit_signals(signals_df, confidence)

        # Add reasons
        trade_signals_with_reasons = self.generate_signal_reasons(signals_df, trade_signals)

        return {
            'signals': signals_df,
            'confidence': confidence,
            'trades': trade_signals_with_reasons
        }
