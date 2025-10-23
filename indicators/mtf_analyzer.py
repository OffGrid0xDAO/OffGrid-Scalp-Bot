#!/usr/bin/env python3
"""
Multi-Timeframe (MTF) Analyzer

Provides trend and momentum confirmation from lower timeframes (5m, 15m)
to validate 1h entry signals.

Concept:
- 1h timeframe: Primary signal generation
- 15m timeframe: Intermediate trend confirmation
- 5m timeframe: Short-term momentum confirmation

Entry only when all timeframes align!
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta


class MTFAnalyzer:
    """
    Multi-Timeframe Analysis for trade confirmation

    Checks if lower timeframes (5m, 15m) confirm the 1h signal
    """

    def __init__(self, df_5m: pd.DataFrame = None, df_15m: pd.DataFrame = None):
        """
        Initialize MTF analyzer

        Args:
            df_5m: 5-minute timeframe data with indicators
            df_15m: 15-minute timeframe data with indicators
        """
        self.df_5m = df_5m
        self.df_15m = df_15m

        # Ensure timestamps are datetime
        if self.df_5m is not None and 'timestamp' in self.df_5m.columns:
            self.df_5m['timestamp'] = pd.to_datetime(self.df_5m['timestamp'])
        if self.df_15m is not None and 'timestamp' in self.df_15m.columns:
            self.df_15m['timestamp'] = pd.to_datetime(self.df_15m['timestamp'])

    def get_mtf_confirmation(self, timestamp: pd.Timestamp, direction: str) -> Dict:
        """
        Check if lower timeframes confirm the 1h signal

        Args:
            timestamp: The 1h candle timestamp
            direction: 'long' or 'short'

        Returns:
            dict with confirmation status and scores
        """
        result = {
            'confirmed': False,
            'mtf_score': 0.0,
            'tf_5m_trend': None,
            'tf_15m_trend': None,
            'tf_5m_momentum': None,
            'tf_15m_momentum': None,
            'reason': ''
        }

        # Get 15m confirmation
        if self.df_15m is not None:
            tf_15m = self._analyze_timeframe(self.df_15m, timestamp, direction, '15m')
            result['tf_15m_trend'] = tf_15m['trend']
            result['tf_15m_momentum'] = tf_15m['momentum']
            result['mtf_score'] += tf_15m['score']
        else:
            result['reason'] = 'No 15m data'
            return result

        # Get 5m confirmation
        if self.df_5m is not None:
            tf_5m = self._analyze_timeframe(self.df_5m, timestamp, direction, '5m')
            result['tf_5m_trend'] = tf_5m['trend']
            result['tf_5m_momentum'] = tf_5m['momentum']
            result['mtf_score'] += tf_5m['score']
        else:
            result['reason'] = 'No 5m data'
            return result

        # Confirmation logic:
        # - 15m must be aligned or neutral
        # - 5m must be aligned or neutral
        # - At least one must be strongly aligned

        # RELAXED FOR ITERATION 1: Allow catching ribbon flips early
        tf_15m_ok = tf_15m['trend'] != 'opposing'
        tf_5m_ok = tf_5m['trend'] != 'opposing'

        at_least_one_aligned = (tf_15m['trend'] == 'aligned' or tf_5m['trend'] == 'aligned')

        if tf_15m_ok and tf_5m_ok and at_least_one_aligned:
            result['confirmed'] = True
            result['reason'] = f'15m: {tf_15m["trend"]}, 5m: {tf_5m["trend"]}'
        else:
            result['confirmed'] = False
            result['reason'] = f'No alignment - 15m: {tf_15m["trend"]}, 5m: {tf_5m["trend"]}'

        return result

    def _analyze_timeframe(self, df: pd.DataFrame, target_time: pd.Timestamp,
                          direction: str, timeframe: str) -> Dict:
        """
        Analyze a specific timeframe for trend and momentum

        Args:
            df: DataFrame for this timeframe
            target_time: The 1h timestamp we're checking
            direction: 'long' or 'short'
            timeframe: '5m' or '15m'

        Returns:
            dict with trend, momentum, and score
        """
        # Get recent candles (look back 1 hour = 12 x 5m or 4 x 15m)
        if timeframe == '5m':
            lookback_candles = 12
        elif timeframe == '15m':
            lookback_candles = 4
        else:
            lookback_candles = 4

        # Find candles around target time
        time_window_start = target_time - pd.Timedelta(hours=1)
        time_window_end = target_time + pd.Timedelta(minutes=5)  # Allow small buffer

        recent_candles = df[(df['timestamp'] >= time_window_start) &
                           (df['timestamp'] <= time_window_end)].tail(lookback_candles)

        if len(recent_candles) < 3:
            return {
                'trend': 'unknown',
                'momentum': 'unknown',
                'score': 0.0
            }

        # Get latest candle
        latest = recent_candles.iloc[-1]

        # Analyze trend using EMAs
        trend = self._get_trend_status(recent_candles, latest, direction)

        # Analyze momentum using RSI and price action
        momentum = self._get_momentum_status(recent_candles, latest, direction)

        # Calculate confirmation score (0-1)
        score = self._calculate_tf_score(trend, momentum)

        return {
            'trend': trend,
            'momentum': momentum,
            'score': score
        }

    def _get_trend_status(self, recent_candles: pd.DataFrame, latest: pd.Series,
                         direction: str) -> str:
        """
        Determine trend status from EMAs and price action

        Returns: 'aligned', 'neutral', or 'opposing'
        """
        # Check if we have EMA data
        if 'ema_9' not in recent_candles.columns or 'ema_21' not in recent_candles.columns:
            # Fallback: use price trend
            if len(recent_candles) >= 3:
                price_start = recent_candles.iloc[0]['close']
                price_end = recent_candles.iloc[-1]['close']
                price_change = (price_end - price_start) / price_start * 100

                if direction == 'long':
                    if price_change > 0.5:
                        return 'aligned'
                    elif price_change < -0.5:
                        return 'opposing'
                else:  # short
                    if price_change < -0.5:
                        return 'aligned'
                    elif price_change > 0.5:
                        return 'opposing'

            return 'neutral'

        # EMA analysis
        ema_9 = latest['ema_9']
        ema_21 = latest['ema_21']
        price = latest['close']

        # Check EMA alignment
        if direction == 'long':
            # For long: price > ema_9 > ema_21 (bullish)
            if price > ema_9 and ema_9 > ema_21:
                return 'aligned'
            elif price < ema_9 and ema_9 < ema_21:
                return 'opposing'
            else:
                return 'neutral'
        else:  # short
            # For short: price < ema_9 < ema_21 (bearish)
            if price < ema_9 and ema_9 < ema_21:
                return 'aligned'
            elif price > ema_9 and ema_9 > ema_21:
                return 'opposing'
            else:
                return 'neutral'

    def _get_momentum_status(self, recent_candles: pd.DataFrame, latest: pd.Series,
                            direction: str) -> str:
        """
        Determine momentum status from RSI and recent price action

        Returns: 'aligned', 'neutral', or 'opposing'
        """
        # Check if we have RSI
        if 'rsi_14' in latest:
            rsi = latest['rsi_14']

            if direction == 'long':
                # For long: RSI rising and not overbought
                if rsi > 50 and rsi < 70:
                    return 'aligned'
                elif rsi > 70:
                    return 'neutral'  # Overbought but still bullish
                elif rsi < 30:
                    return 'opposing'
                else:
                    return 'neutral'
            else:  # short
                # For short: RSI falling and not oversold
                if rsi < 50 and rsi > 30:
                    return 'aligned'
                elif rsi < 30:
                    return 'neutral'  # Oversold but still bearish
                elif rsi > 70:
                    return 'opposing'
                else:
                    return 'neutral'

        # Fallback: recent candles direction
        if len(recent_candles) >= 3:
            recent_highs = recent_candles['high'].tail(3).tolist()
            recent_lows = recent_candles['low'].tail(3).tolist()

            if direction == 'long':
                # Higher highs and higher lows
                if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
                    return 'aligned'
                elif recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
                    return 'opposing'
            else:  # short
                # Lower highs and lower lows
                if recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
                    return 'aligned'
                elif recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
                    return 'opposing'

        return 'neutral'

    def _calculate_tf_score(self, trend: str, momentum: str) -> float:
        """
        Calculate confirmation score for a timeframe

        Returns: 0.0 to 0.5 (max 1.0 when both timeframes combined)
        """
        score = 0.0

        # Trend contribution (0.3 max)
        if trend == 'aligned':
            score += 0.3
        elif trend == 'neutral':
            score += 0.1
        # opposing adds 0

        # Momentum contribution (0.2 max)
        if momentum == 'aligned':
            score += 0.2
        elif momentum == 'neutral':
            score += 0.05
        # opposing adds 0

        return score

    def get_mtf_summary(self, timestamp: pd.Timestamp, direction: str) -> str:
        """
        Get human-readable summary of MTF analysis

        Args:
            timestamp: The 1h candle timestamp
            direction: 'long' or 'short'

        Returns:
            Summary string
        """
        result = self.get_mtf_confirmation(timestamp, direction)

        if not result['confirmed']:
            return f"❌ MTF: Not confirmed - {result['reason']}"

        summary_parts = []

        if result['tf_15m_trend']:
            summary_parts.append(f"15m: {result['tf_15m_trend']}/{result['tf_15m_momentum']}")

        if result['tf_5m_trend']:
            summary_parts.append(f"5m: {result['tf_5m_trend']}/{result['tf_5m_momentum']}")

        score_desc = "Strong" if result['mtf_score'] > 0.7 else "Moderate" if result['mtf_score'] > 0.4 else "Weak"

        return f"✅ MTF: {score_desc} ({result['mtf_score']:.2f}) - {', '.join(summary_parts)}"


if __name__ == '__main__':
    """Test MTF analyzer"""
    print("MTF Analyzer loaded successfully!")
    print("\nUsage:")
    print("  1. Load 5m and 15m data with indicators")
    print("  2. Create MTFAnalyzer(df_5m, df_15m)")
    print("  3. Call get_mtf_confirmation(timestamp, direction)")
    print("\nFeatures:")
    print("  - Trend analysis using EMAs")
    print("  - Momentum analysis using RSI")
    print("  - Price action confirmation")
    print("  - Scoring system (0-1.0)")
