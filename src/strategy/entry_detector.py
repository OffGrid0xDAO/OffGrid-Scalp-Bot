#!/usr/bin/env python3
"""
Entry Detector - Confluence Gap Strategy

Implements the proven 55.3% win rate strategy:
- Confluence gap > 30 points
- Volume elevated or spike
- Optional: EMA alignment, MACD confirmation, RSI range

This is the core signal generator that identifies high-probability trade setups.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, Optional, List


class EntryDetector:
    """
    Detect high-probability entry signals using confluence gap strategy

    Proven performance (ETH 1h, 123 signals):
    - 55.3% win rate reaching +1% TP
    - 36.6% win rate reaching +2% TP
    - Average profit: 1.87%
    - Best trades: +10-12%
    """

    def __init__(self, params_file: str = None):
        """
        Initialize entry detector

        Args:
            params_file: Path to strategy parameters JSON file
        """
        if params_file is None:
            params_file = Path(__file__).parent / 'strategy_params.json'

        with open(params_file, 'r') as f:
            self.params = json.load(f)

        self.entry_filters = self.params['entry_filters']
        self.ribbon_settings = self.params['ribbon_settings']

    def detect_signal(self, df: pd.DataFrame) -> Dict:
        """
        Detect entry signal on latest candle - OPTIMIZED FOR 2-3 QUALITY TRADES/DAY

        Enhanced with professional day trading indicators:
        - Stochastic Oscillator (5-3-3) for entry timing
        - Bollinger Bands for volatility breakouts
        - VWAP for institutional price levels
        - Quality scoring system for trade selection

        Args:
            df: DataFrame with all indicators (must have at least last candle)

        Returns:
            dict with:
                - signal: bool (True if entry detected)
                - direction: 'long' or 'short'
                - entry_price: float
                - confidence: float (confluence gap size)
                - quality_score: float (0-100, for ranking trades)
                - confluence_long: float
                - confluence_short: float
                - volume_status: str
                - filters_passed: dict
                - reason: str (why signal was generated/rejected)
        """
        # Get latest candle data
        latest = df.iloc[-1]

        # Initialize result
        result = {
            'signal': False,
            'direction': None,
            'entry_price': latest['close'],
            'confidence': 0.0,
            'quality_score': 0.0,
            'confluence_long': latest.get('confluence_score_long', 0),
            'confluence_short': latest.get('confluence_score_short', 0),
            'volume_status': latest.get('volume_status', 'normal'),
            'filters_passed': {},
            'reason': ''
        }

        # Check if required columns exist
        if 'confluence_score_long' not in df.columns or 'confluence_score_short' not in df.columns:
            result['reason'] = 'Missing confluence score columns'
            return result

        # Calculate confluence gap
        long_score = latest['confluence_score_long']
        short_score = latest['confluence_score_short']
        gap = abs(long_score - short_score)

        # Determine direction
        if long_score > short_score:
            direction = 'long'
            score = long_score
        else:
            direction = 'short'
            score = short_score

        result['direction'] = direction
        result['confidence'] = gap

        # FILTER 1: Confluence gap threshold (PRIMARY FILTER)
        gap_min = self.entry_filters['confluence_gap_min']
        if gap < gap_min:
            result['reason'] = f'Confluence gap {gap:.1f} < {gap_min} threshold'
            return result
        result['filters_passed']['confluence_gap'] = True

        # FILTER 2: Minimum confluence score
        score_min = self.entry_filters['confluence_score_min']
        if score < score_min:
            result['reason'] = f'Confluence score {score:.1f} < {score_min} threshold'
            return result
        result['filters_passed']['confluence_score'] = True

        # FILTER 3: Volume confirmation (CRITICAL - adds 10% to win rate)
        volume_status = latest.get('volume_status', 'normal')
        volume_required = self.entry_filters['volume_requirement']
        if volume_status not in volume_required:
            result['reason'] = f'Volume {volume_status} not in {volume_required}'
            return result
        result['filters_passed']['volume'] = True

        # FILTER 4: RSI range (optional - avoid extreme overbought/oversold)
        if 'rsi_14' in df.columns:
            rsi_range = self.entry_filters['rsi_range']
            rsi = latest['rsi_14']

            if direction == 'long':
                # For long: avoid overbought (RSI > 70)
                if rsi > rsi_range[1]:
                    result['reason'] = f'RSI {rsi:.1f} > {rsi_range[1]} (overbought)'
                    return result
            else:
                # For short: avoid oversold (RSI < 30)
                if rsi < rsi_range[0]:
                    result['reason'] = f'RSI {rsi:.1f} < {rsi_range[0]} (oversold)'
                    return result
            result['filters_passed']['rsi_range'] = True

        # FILTER 5: EMA alignment (optional)
        if self.entry_filters['require_ema_alignment']:
            if 'alignment_pct' not in df.columns:
                result['reason'] = 'EMA alignment required but alignment_pct column missing'
                return result

            alignment = latest['alignment_pct']
            if direction == 'long' and alignment < 0.70:
                result['reason'] = f'Long requires alignment > 0.70, got {alignment:.2f}'
                return result
            elif direction == 'short' and alignment > 0.30:
                result['reason'] = f'Short requires alignment < 0.30, got {alignment:.2f}'
                return result
            result['filters_passed']['ema_alignment'] = True

        # FILTER 6: MACD confirmation (optional)
        if self.entry_filters['require_macd_confirmation']:
            if 'macd_fast_trend' not in df.columns:
                result['reason'] = 'MACD confirmation required but macd_fast_trend column missing'
                return result

            macd_trend = latest['macd_fast_trend']
            if direction == 'long' and macd_trend not in ['strong_bullish', 'weak_bullish']:
                result['reason'] = f'Long requires bullish MACD, got {macd_trend}'
                return result
            elif direction == 'short' and macd_trend not in ['strong_bearish', 'weak_bearish']:
                result['reason'] = f'Short requires bearish MACD, got {macd_trend}'
                return result
            result['filters_passed']['macd_confirmation'] = True

        # FILTER 7: Price vs EMA20 (optional)
        if self.entry_filters['min_price_above_ema20']:
            if 'MMA20_value' in df.columns:
                ema20 = latest['MMA20_value']
                price = latest['close']

                if direction == 'long' and price < ema20:
                    result['reason'] = f'Long requires price > EMA20, got {price:.2f} < {ema20:.2f}'
                    return result
                elif direction == 'short' and price > ema20:
                    result['reason'] = f'Short requires price < EMA20, got {price:.2f} > {ema20:.2f}'
                    return result
                result['filters_passed']['ema20_position'] = True

        # FILTER 8: Ribbon compression (optional - for high-quality setups)
        if self.ribbon_settings['use_compression_filter']:
            if 'compression_score' in df.columns:
                compression = latest['compression_score']
                threshold = self.ribbon_settings['compression_threshold']

                if compression < threshold:
                    result['reason'] = f'Compression {compression:.1f} < {threshold} threshold'
                    return result
                result['filters_passed']['ribbon_compression'] = True

        # FILTER 9: Stochastic Oscillator (5-3-3) - Entry Timing
        if self.entry_filters.get('use_stochastic', True):
            stoch_k = latest.get('stoch_k', None)
            stoch_d = latest.get('stoch_d', None)

            if stoch_k is not None and stoch_d is not None:
                if direction == 'long':
                    # Long: Stochastic crossing up from oversold (<20) or just crossed above 20
                    if stoch_k < 20:
                        result['filters_passed']['stochastic'] = True
                        result['confidence'] += 0.15  # Strong buy signal
                    elif stoch_k < 50 and stoch_k > stoch_d:
                        result['filters_passed']['stochastic'] = True
                        result['confidence'] += 0.10  # Moderate buy signal
                    elif stoch_k > 80:
                        # Overbought - avoid entry
                        result['reason'] = f'Stochastic overbought: {stoch_k:.1f} > 80'
                        return result
                else:
                    # Short: Stochastic crossing down from overbought (>80) or just crossed below 80
                    if stoch_k > 80:
                        result['filters_passed']['stochastic'] = True
                        result['confidence'] += 0.15  # Strong sell signal
                    elif stoch_k > 50 and stoch_k < stoch_d:
                        result['filters_passed']['stochastic'] = True
                        result['confidence'] += 0.10  # Moderate sell signal
                    elif stoch_k < 20:
                        # Oversold - avoid entry
                        result['reason'] = f'Stochastic oversold: {stoch_k:.1f} < 20'
                        return result

        # FILTER 10: Bollinger Bands - Volatility Breakout Confirmation
        if self.entry_filters.get('use_bollinger', True):
            bb_upper = latest.get('bb_upper', None)
            bb_lower = latest.get('bb_lower', None)
            bb_middle = latest.get('bb_middle', None)
            price = latest['close']

            if bb_upper is not None and bb_lower is not None and bb_middle is not None:
                bb_width = (bb_upper - bb_lower) / bb_middle * 100

                if direction == 'long':
                    # Long: Price crossing above BB middle during expansion
                    if price > bb_middle:
                        result['filters_passed']['bollinger'] = True
                        if bb_width > 4.0:  # Significant volatility
                            result['confidence'] += 0.15
                        else:
                            result['confidence'] += 0.08
                    elif price < bb_lower * 1.01:
                        # Price at lower band - potential mean reversion
                        result['filters_passed']['bollinger'] = True
                        result['confidence'] += 0.10
                else:
                    # Short: Price crossing below BB middle during expansion
                    if price < bb_middle:
                        result['filters_passed']['bollinger'] = True
                        if bb_width > 4.0:  # Significant volatility
                            result['confidence'] += 0.15
                        else:
                            result['confidence'] += 0.08
                    elif price > bb_upper * 0.99:
                        # Price at upper band - potential mean reversion
                        result['filters_passed']['bollinger'] = True
                        result['confidence'] += 0.10

        # FILTER 11: VWAP - Institutional Price Level Filter
        if self.entry_filters.get('use_vwap', True):
            vwap = latest.get('vwap', None)
            price = latest['close']

            if vwap is not None:
                price_vs_vwap = (price - vwap) / vwap * 100

                if direction == 'long':
                    # Long: Price above VWAP (institutional support)
                    if price > vwap:
                        result['filters_passed']['vwap'] = True
                        result['confidence'] += 0.12
                    elif price > vwap * 0.998:  # Within 0.2% of VWAP
                        result['filters_passed']['vwap'] = True
                        result['confidence'] += 0.06
                    else:
                        result['reason'] = f'Price below VWAP for long ({price_vs_vwap:.2f}%)'
                        return result
                else:
                    # Short: Price below VWAP (institutional resistance)
                    if price < vwap:
                        result['filters_passed']['vwap'] = True
                        result['confidence'] += 0.12
                    elif price < vwap * 1.002:  # Within 0.2% of VWAP
                        result['filters_passed']['vwap'] = True
                        result['confidence'] += 0.06
                    else:
                        result['reason'] = f'Price above VWAP for short ({price_vs_vwap:.2f}%)'
                        return result

        # FILTER 12: Ribbon Flip Requirement (OPTIONAL - HIGH QUALITY FILTER)
        if self.entry_filters.get('require_ribbon_flip', False):
            if 'ribbon_flip' not in df.columns:
                result['reason'] = 'Ribbon flip required but column missing'
                return result

            ribbon_flip = latest['ribbon_flip']

            # Check if ribbon flip matches our direction
            if direction == 'long' and ribbon_flip != 'bullish_flip':
                result['reason'] = f'Long requires bullish_flip, got {ribbon_flip}'
                return result
            elif direction == 'short' and ribbon_flip != 'bearish_flip':
                result['reason'] = f'Short requires bearish_flip, got {ribbon_flip}'
                return result

            result['filters_passed']['ribbon_flip'] = True
            result['confidence'] += 0.25  # High quality signal boost

        # FILTER 13: Ribbon Alignment (OPTIONAL - HIGH QUALITY FILTER)
        if self.entry_filters.get('min_ribbon_alignment', 0) > 0:
            if 'alignment_pct' not in df.columns:
                result['reason'] = 'Ribbon alignment required but column missing'
                return result

            alignment = latest['alignment_pct']
            min_alignment = self.entry_filters['min_ribbon_alignment']

            if direction == 'long' and alignment < min_alignment:
                result['reason'] = f'Long requires alignment > {min_alignment:.0%}, got {alignment:.0%}'
                return result
            elif direction == 'short' and alignment > (1 - min_alignment):
                result['reason'] = f'Short requires alignment < {1-min_alignment:.0%}, got {alignment:.0%}'
                return result

            result['filters_passed']['ribbon_alignment'] = True
            result['confidence'] += 0.20

        # CALCULATE QUALITY SCORE (0-100) for trade ranking
        # This helps select only the 2-3 BEST trades per day
        quality_score = self._calculate_quality_score(latest, direction, result['confidence'],
                                                       gap, score, result['filters_passed'])
        result['quality_score'] = quality_score

        # QUALITY THRESHOLD - Only take trades above this score
        min_quality = self.entry_filters.get('min_quality_score', 70)
        if quality_score < min_quality:
            result['reason'] = f'Quality score {quality_score:.1f} < {min_quality} threshold'
            return result

        # ALL FILTERS PASSED!
        result['signal'] = True
        result['reason'] = f'{direction.upper()} signal: gap={gap:.1f}, score={score:.1f}, quality={quality_score:.1f}, filters={len(result["filters_passed"])}'
        return result

    def _calculate_quality_score(self, latest: pd.Series, direction: str,
                                  confidence: float, gap: float, score: float,
                                  filters_passed: dict) -> float:
        """
        Calculate trade quality score (0-100) for ranking and selection

        Higher scores = better trade setups
        Use this to limit to 2-3 best trades per day

        Scoring components:
        - Base confluence (30 pts): gap + score
        - Volume quality (20 pts): spike > elevated > normal
        - Indicator alignment (30 pts): Stoch + BB + VWAP
        - Trend strength (20 pts): ribbon + EMA + MACD

        Returns:
            Quality score 0-100
        """
        quality = 0.0

        # Component 1: Confluence strength (30 points max)
        # Gap: 30-50 = 10pts, 50-70 = 15pts, 70+ = 20pts
        if gap >= 70:
            quality += 20
        elif gap >= 50:
            quality += 15
        elif gap >= 30:
            quality += 10

        # Score: 35-45 = 5pts, 45-60 = 8pts, 60+ = 10pts
        if score >= 60:
            quality += 10
        elif score >= 45:
            quality += 8
        elif score >= 35:
            quality += 5

        # Component 2: Volume quality (20 points max)
        volume_status = latest.get('volume_status', 'normal')
        if volume_status == 'spike':
            quality += 20  # Best - significant interest
        elif volume_status == 'elevated':
            quality += 12  # Good
        elif volume_status == 'normal':
            quality += 5   # Acceptable

        # Component 3: Indicator alignment (30 points max)
        if 'stochastic' in filters_passed:
            quality += 10  # Entry timing confirmed
        if 'bollinger' in filters_passed:
            quality += 10  # Volatility breakout confirmed
        if 'vwap' in filters_passed:
            quality += 10  # Institutional level confirmed

        # Component 4: Trend strength (20 points max)
        if 'ribbon_flip' in filters_passed:
            quality += 8   # Strong trend reversal/continuation
        if 'ribbon_alignment' in filters_passed:
            quality += 6   # Strong directional bias
        if 'ema_alignment' in filters_passed:
            quality += 3   # EMA structure aligned
        if 'macd_confirmation' in filters_passed:
            quality += 3   # Momentum confirmed

        # Bonus: Multiple confirmations
        num_filters = len(filters_passed)
        if num_filters >= 8:
            quality += 5   # Exceptional confluence
        elif num_filters >= 6:
            quality += 3   # Strong confluence

        return min(quality, 100.0)  # Cap at 100

    def _is_ranging_market(self, df: pd.DataFrame, latest: pd.Series) -> bool:
        """
        Detect if market is ranging/consolidating (NO TRADE ZONE!)

        CRITICAL: Ribbon flips during ranging = FALSE SIGNALS!

        Ranging indicators:
        1. Price stuck in tight range (< 3% over 20 candles)
        2. Expansion rate consistently low (< 2.0 average)
        3. High compression (> 70) persisting without breakout
        4. Ribbon state oscillating (flipping back and forth)

        Returns:
            True if ranging, False if trending
        """
        # Need enough history
        if len(df) < 20:
            return False

        # Check 1: Price range
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()
        price_range_pct = (recent_high - recent_low) / recent_low * 100

        # Check 2: Average expansion rate
        if 'expansion_rate' in df.columns:
            avg_expansion = df['expansion_rate'].tail(10).mean()
            expansion_volatility = df['expansion_rate'].tail(10).std()
        else:
            avg_expansion = 0
            expansion_volatility = 0

        # Check 3: Compression persisting
        if 'compression_score' in df.columns:
            compression_high_count = (df['compression_score'].tail(10) > 70).sum()
        else:
            compression_high_count = 0

        # Check 4: Ribbon state oscillations (flipping back/forth)
        if 'ribbon_state' in df.columns:
            recent_states = df['ribbon_state'].tail(5).tolist()
            state_changes = sum(1 for i in range(1, len(recent_states)) if recent_states[i] != recent_states[i-1])
        else:
            state_changes = 0

        # RANGING if:
        # - Price range < 3% (tight consolidation)
        # - AND low expansion (< 2.0 average)
        # - AND (high compression OR oscillating states)
        is_tight_range = price_range_pct < 3.0
        is_low_expansion = abs(avg_expansion) < 2.0
        is_compressed = compression_high_count >= 5
        is_oscillating = state_changes >= 3

        if is_tight_range and is_low_expansion and (is_compressed or is_oscillating):
            return True

        return False

    def _check_ribbon_flip_entry(self, df: pd.DataFrame, direction: str, latest: pd.Series) -> str:
        """
        Enhanced Ribbon Flip Entry Strategy

        GOAL: Catch the BIG MOVES when ribbon fully flips color!

        Entry Conditions for LONG:
        1. Ribbon state changed to 'all_green' (full flip from red/mixed)
        2. Recent compression (score > 60 in last 5 candles)
        3. Now expanding (expansion_rate > 5)
        4. Price above yellow EMA (20 or 21)
        5. Volume confirmation
        6. NOT RANGING (CRITICAL!)

        For SHORT: Everything in reverse

        Returns:
            Description of flip signal if conditions met, empty string otherwise
        """
        # Check if we have ribbon data
        if 'ribbon_state' not in df.columns:
            return ""

        # Need at least 20 candles of history for ranging detection
        if len(df) < 20:
            return ""

        # FILTER OUT RANGING MARKETS (THE BIG FIX!)
        # User insight: "100% of the time when all ribbons turn green and disperse there is huge long opportunity
        # we just have to not allow it to get tricked when this happens in ranging"
        if self._is_ranging_market(df, latest):
            return ""  # NO SIGNAL during ranging!

        current_state = latest['ribbon_state']
        prev_state = df.iloc[-2]['ribbon_state'] if len(df) >= 2 else current_state

        # LONG: Look for bullish ribbon states
        if direction == 'long':
            # Accept all_green OR mixed_green (not just perfect flips)
            if current_state not in ['all_green', 'mixed_green']:
                return ""

            # EITHER: Just flipped from bearish
            just_flipped = prev_state in ['all_red', 'mixed_red', 'mixed']

            # OR: In strong uptrend (all_green)
            in_uptrend = current_state == 'all_green'

            if not (just_flipped or in_uptrend):
                return ""

            # Check for compression → expansion pattern (THE BIG MOVE SETUP)
            if 'compression_score' in df.columns and 'expansion_rate' in df.columns:
                recent_compression = df['compression_score'].tail(10).max()
                current_expansion = latest.get('expansion_rate', 0)

                # More lenient: compression > 50 (not 60)
                if recent_compression > 50 and current_expansion > 3:
                    return f"BREAKOUT! Compression {recent_compression:.0f} → Expanding {current_expansion:.1f}"

            # Price confirmation (more lenient - just needs to be near yellow EMA)
            price = latest['close']
            ema20 = latest.get('MMA20_value', 0)
            ema21 = latest.get('MMA21_value', 0)
            yellow_ema = ema20 if ema20 > 0 else ema21

            # Accept if price is above OR within 1% of yellow EMA
            if yellow_ema > 0 and price >= yellow_ema * 0.99:
                if just_flipped:
                    return f"Ribbon flipped bullish (from {prev_state})"
                else:
                    return f"Strong uptrend (all_green)"

        # SHORT: Look for bearish ribbon states
        elif direction == 'short':
            # Accept all_red OR mixed_red (not just perfect flips)
            if current_state not in ['all_red', 'mixed_red']:
                return ""

            # EITHER: Just flipped from bullish
            just_flipped = prev_state in ['all_green', 'mixed_green', 'mixed']

            # OR: In strong downtrend (all_red)
            in_downtrend = current_state == 'all_red'

            if not (just_flipped or in_downtrend):
                return ""

            # Check for compression → expansion pattern
            if 'compression_score' in df.columns and 'expansion_rate' in df.columns:
                recent_compression = df['compression_score'].tail(10).max()
                current_expansion = latest.get('expansion_rate', 0)

                if recent_compression > 50 and current_expansion > 3:
                    return f"BREAKOUT! Compression {recent_compression:.0f} → Expanding {current_expansion:.1f}"

            # Price confirmation (more lenient)
            price = latest['close']
            ema20 = latest.get('MMA20_value', 0)
            ema21 = latest.get('MMA21_value', 0)
            yellow_ema = ema20 if ema20 > 0 else ema21

            # Accept if price is below OR within 1% of yellow EMA
            if yellow_ema > 0 and price <= yellow_ema * 1.01:
                if just_flipped:
                    return f"Ribbon flipped bearish (from {prev_state})"
                else:
                    return f"Strong downtrend (all_red)"

        return ""

    def scan_historical_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Scan entire dataframe for entry signals

        Args:
            df: DataFrame with all indicators

        Returns:
            DataFrame with additional columns:
                - entry_signal: bool
                - entry_direction: 'long', 'short', or None
                - entry_confidence: float
                - entry_reason: str
        """
        print("\n" + "="*80)
        print("SCANNING FOR ENTRY SIGNALS")
        print("="*80)

        # Initialize columns
        df['entry_signal'] = False
        df['entry_direction'] = None
        df['entry_confidence'] = 0.0
        df['entry_reason'] = ''

        signals_found = 0
        long_signals = 0
        short_signals = 0

        # Scan each candle
        for i in range(len(df)):
            # Need at least some history for indicators
            if i < 50:
                continue

            # Get data up to this point (simulate real-time)
            df_partial = df.iloc[:i+1].copy()

            # Detect signal
            signal = self.detect_signal(df_partial)

            # Record signal
            df.loc[df.index[i], 'entry_signal'] = signal['signal']
            df.loc[df.index[i], 'entry_direction'] = signal['direction']
            df.loc[df.index[i], 'entry_confidence'] = signal['confidence']
            df.loc[df.index[i], 'entry_reason'] = signal['reason']

            if signal['signal']:
                signals_found += 1
                if signal['direction'] == 'long':
                    long_signals += 1
                else:
                    short_signals += 1

        print(f"\n📊 Signal Summary:")
        print(f"   Total signals: {signals_found}")
        print(f"   Long signals: {long_signals}")
        print(f"   Short signals: {short_signals}")
        print(f"   Signal frequency: {signals_found / len(df) * 100:.2f}% of candles")

        return df

    def update_parameters(self, new_params: Dict):
        """
        Update strategy parameters (used by Claude optimizer)

        Args:
            new_params: Dictionary of parameters to update
        """
        print("\n🔧 Updating entry detector parameters:")

        for key, value in new_params.items():
            if key in self.entry_filters:
                old_value = self.entry_filters[key]
                self.entry_filters[key] = value
                print(f"   {key}: {old_value} → {value}")
            elif key in self.ribbon_settings:
                old_value = self.ribbon_settings[key]
                self.ribbon_settings[key] = value
                print(f"   {key}: {old_value} → {value}")

        # Save updated parameters
        params_file = Path(__file__).parent / 'strategy_params.json'
        with open(params_file, 'w') as f:
            json.dump(self.params, f, indent=2)

        print("   ✅ Parameters saved")


if __name__ == '__main__':
    """Test the entry detector on historical data"""
    import sys
    from pathlib import Path

    # Load test data
    data_file = Path(__file__).parent.parent.parent / 'trading_data' / 'indicators' / 'eth_1h_full.csv'

    if not data_file.exists():
        print(f"❌ Test data not found: {data_file}")
        sys.exit(1)

    print(f"📊 Loading test data: {data_file}")
    df = pd.read_csv(data_file)
    print(f"   Loaded {len(df)} candles")

    # Create detector
    detector = EntryDetector()

    # Scan for signals
    df = detector.scan_historical_signals(df)

    # Show sample signals
    signals_df = df[df['entry_signal'] == True][['timestamp', 'close', 'entry_direction',
                                                   'entry_confidence', 'confluence_score_long',
                                                   'confluence_score_short', 'volume_status']]

    print(f"\n📋 Sample signals (first 10):")
    print(signals_df.head(10).to_string())

    # Save signals
    output_file = Path(__file__).parent.parent.parent / 'trading_data' / 'signals' / 'eth_1h_entry_signals.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"\n💾 Signals saved: {output_file}")
