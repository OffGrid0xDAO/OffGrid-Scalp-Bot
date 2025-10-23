#!/usr/bin/env python3
"""
Entry Detector - User Pattern Based Strategy

Generated from analysis of 22 optimal trades (Oct 5-21, 2025)
This strategy mimics YOUR trading decisions based on discovered patterns.

Key Characteristics:
- Lower confluence requirements (you trade smaller gaps)
- No MACD trend requirement (you ignore it)
- Wide RSI acceptance (you enter across full range)
- Normal volume OK (you don't need spikes)
- Mid-range Stochastic (you don't wait for extremes)
- S/R awareness but not critical (only 22.7% at exact levels)
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, Optional
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from indicators.mtf_analyzer import MTFAnalyzer
from strategy.ribbon_analyzer import RibbonAnalyzer


class EntryDetector:
    """
    Detect entry signals based on USER's discovered patterns

    Pattern Analysis Results (from 22 trades):
    - LONG: RSI avg 46 (range 29-80), Stoch avg 44 (range 19-68)
    - SHORT: RSI avg 42 (range 25-63), Stoch avg 45 (range 12-74)
    - Confluence gap: 3.3 for longs, 2.0 for shorts (MUCH lower than bot's 30!)
    - Volume: 50% normal, 18% elevated, 18% spike, 14% low
    - MACD: 50/50 bullish/bearish for longs (NOT a factor!)
    - S/R: Only 22.7% at exact levels (awareness but not critical)
    """

    def __init__(self, params_file: str = None, df_5m: pd.DataFrame = None, df_15m: pd.DataFrame = None):
        """
        Initialize entry detector with user-based parameters

        Args:
            params_file: Path to strategy parameters
            df_5m: 5-minute timeframe data for MTF confirmation (optional)
            df_15m: 15-minute timeframe data for MTF confirmation (optional)
        """
        if params_file is None:
            params_file = Path(__file__).parent / 'strategy_params_user.json'

        # Create user-based params if not exists
        if not Path(params_file).exists():
            self._create_default_params(params_file)

        with open(params_file, 'r') as f:
            self.params = json.load(f)

        self.entry_filters = self.params['entry_filters']

        # Multi-timeframe analyzer (if data provided)
        self.mtf_analyzer = None
        if df_5m is not None or df_15m is not None:
            self.mtf_analyzer = MTFAnalyzer(df_5m, df_15m)
            print("✅ Multi-timeframe confirmation enabled (5m, 15m)")

        # Ribbon analyzer for flip detection
        self.ribbon_analyzer = RibbonAnalyzer()
        print("✅ Ribbon flip detection enabled")

    def _create_default_params(self, params_file: str):
        """Create default parameters based on discovered patterns"""
        params = {
            "entry_filters": {
                "confluence_gap_min": 0,  # User trades with ANY gap (avg 3.3 for longs, 2.0 for shorts)
                "confluence_score_min": 10,  # Minimum observed in user trades

                # RSI: Wide acceptance based on user patterns
                "rsi_range": [20, 85],  # User enters across full range (29-80 for longs, 25-63 for shorts)

                # Volume: Accept all levels (user trades 50% on normal volume)
                "volume_requirement": ["spike", "elevated", "normal", "low"],

                # MACD: NOT REQUIRED (user ignores it - 50/50 split)
                "require_macd_confirmation": False,

                # Stochastic: Wide middle range acceptance
                "stoch_range_long": [15, 70],  # Based on user range 19-68
                "stoch_range_short": [10, 75],  # Based on user range 12-74

                # S/R: Awareness but not critical (only 22.7% at exact levels)
                "require_sr_level": False,
                "sr_bonus_weight": 0.2,  # Small bonus if near S/R

                # Quality score: Much lower threshold
                "min_quality_score": 30,  # User trades are simpler, less filtered

                # Other filters from original (kept loose)
                "require_ema_alignment": False,
                "min_price_above_ema20": False,
                "require_ribbon_flip": False,
                "min_ribbon_alignment": 0,
                "use_stochastic": True,
                "use_bollinger": True,
                "use_vwap": False  # Not explicitly in user pattern analysis
            }
        }

        Path(params_file).parent.mkdir(parents=True, exist_ok=True)
        with open(params_file, 'w') as f:
            json.dump(params, f, indent=2)

    def detect_signal(self, df: pd.DataFrame) -> Dict:
        """
        Detect entry signal based on USER patterns

        Strategy: Simple, less filtered, follows user's intuitive trading style

        Args:
            df: DataFrame with all indicators

        Returns:
            dict with signal info
        """
        latest = df.iloc[-1]

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

        # Check required columns
        if 'confluence_score_long' not in df.columns or 'confluence_score_short' not in df.columns:
            result['reason'] = 'Missing confluence score columns'
            return result

        long_score = latest['confluence_score_long']
        short_score = latest['confluence_score_short']
        gap = abs(long_score - short_score)

        # Determine direction (whoever has higher score)
        if long_score > short_score:
            direction = 'long'
            score = long_score
        else:
            direction = 'short'
            score = short_score

        result['direction'] = direction
        result['confidence'] = gap

        # FILTER 0: RIBBON FLIP DETECTION (NEW - PRIMARY TRIGGER!)
        # Objective: Catch ribbon flips EARLY before they fully develop
        # This is the core "early entry" mechanism
        ribbon_flip_detected = False
        ribbon_flip_strength = 0.0

        if 'alignment_pct' in latest:
            alignment_pct = latest['alignment_pct']

            # Get previous alignment to detect forming flips
            if len(df) >= 2:
                prev_alignment = df.iloc[-2]['alignment_pct']
            else:
                prev_alignment = 0.5

            # Early flip detection (ITERATION 4: Use looser thresholds from ML analysis)
            if direction == 'long':
                early_flip_threshold = self.entry_filters.get('ribbon_flip_threshold_long', 0.60)
                # Bullish flip: alignment crossing above threshold (EMAs turning green)
                forming_flip = (alignment_pct >= early_flip_threshold) and (prev_alignment < early_flip_threshold)
                strong_alignment = alignment_pct >= 0.70  # Lowered from 0.80

                if forming_flip:
                    ribbon_flip_detected = True
                    ribbon_flip_strength = alignment_pct
                    result['confidence'] += 20  # Big confidence boost for flip
                elif strong_alignment and alignment_pct > prev_alignment:
                    # Continuation of flip (already flipped, still strengthening)
                    ribbon_flip_detected = True
                    ribbon_flip_strength = alignment_pct
                    result['confidence'] += 10
            else:  # short
                early_flip_threshold = self.entry_filters.get('ribbon_flip_threshold_short', 0.40)
                # Bearish flip: alignment crossing below threshold
                forming_flip = (alignment_pct <= early_flip_threshold) and (prev_alignment > early_flip_threshold)
                strong_alignment = alignment_pct <= 0.30  # Raised from 0.20

                if forming_flip:
                    ribbon_flip_detected = True
                    ribbon_flip_strength = 1.0 - alignment_pct
                    result['confidence'] += 20
                elif strong_alignment and alignment_pct < prev_alignment:
                    ribbon_flip_detected = True
                    ribbon_flip_strength = 1.0 - alignment_pct
                    result['confidence'] += 10

            result['filters_passed']['ribbon_flip'] = ribbon_flip_detected
            result['ribbon_flip_strength'] = ribbon_flip_strength

            # Require ribbon flip if enabled
            if self.entry_filters.get('require_ribbon_flip', True) and not ribbon_flip_detected:
                result['reason'] = f'No ribbon flip detected (alignment: {alignment_pct:.2f})'
                return result

        # FILTER 1: RANGING FILTER (RELAXED - ribbon flip is early signal!)
        # Objective: Avoid choppy ranging, but allow ribbon flips even before expansion starts
        # Note: Expansion often comes AFTER the flip, so don't be too strict
        if 'compression_score' in latest and 'expansion_rate' in latest:
            compression_score = latest['compression_score']
            expansion_rate = latest['expansion_rate']

            # RELAXED: Only filter if VERY compressed (>95) AND strongly contracting (<-1)
            # This allows early ribbon flips even if expansion hasn't started yet
            if compression_score > 95 and expansion_rate < -1.0:
                result['reason'] = f'Extreme ranging: compression {compression_score:.1f} with contraction {expansion_rate:.1f}'
                return result

            result['filters_passed']['ranging_filter'] = True

            # Bonus for strong expansion (breakout momentum)
            if expansion_rate > 3:
                result['confidence'] += 15  # Expansion bonus!

        # FILTER 2: Confluence gap (RELAXED - was 10, now 5 for early entry)
        gap_min = self.entry_filters.get('confluence_gap_min', 0)
        if gap < gap_min:
            result['reason'] = f'Confluence gap {gap:.1f} < {gap_min} threshold'
            return result
        result['filters_passed']['confluence_gap'] = True

        # FILTER 3: Minimum confluence score (REFINED - increased to 20)
        score_min = self.entry_filters['confluence_score_min']
        if score < score_min:
            result['reason'] = f'Confluence score {score:.1f} < {score_min} threshold'
            return result
        result['filters_passed']['confluence_score'] = True

        # FILTER 4: RSI range (wide acceptance)
        if 'rsi_14' in df.columns:
            rsi_range = self.entry_filters['rsi_range']
            rsi = latest['rsi_14']

            if rsi < rsi_range[0] or rsi > rsi_range[1]:
                result['reason'] = f'RSI {rsi:.1f} outside range {rsi_range}'
                return result
            result['filters_passed']['rsi_range'] = True

        # FILTER 5: Stochastic (wide middle range - user's avg ~44 for both)
        if self.entry_filters.get('use_stochastic', True):
            stoch_k = latest.get('stoch_k', None)

            if stoch_k is not None:
                if direction == 'long':
                    stoch_range = self.entry_filters['stoch_range_long']
                    if stoch_k < stoch_range[0] or stoch_k > stoch_range[1]:
                        result['reason'] = f'Stoch K {stoch_k:.1f} outside LONG range {stoch_range}'
                        return result
                else:
                    stoch_range = self.entry_filters['stoch_range_short']
                    if stoch_k < stoch_range[0] or stoch_k > stoch_range[1]:
                        result['reason'] = f'Stoch K {stoch_k:.1f} outside SHORT range {stoch_range}'
                        return result

                result['filters_passed']['stochastic'] = True
                result['confidence'] += 0.1

        # FILTER 6: RSI-7 range (RELAXED - was 25-50, now 20-55 for early entry)
        # User avg: 39.8, False signals avg: 45.0
        if 'rsi_7' in df.columns and 'rsi_7_range' in self.entry_filters:
            rsi_7 = latest['rsi_7']
            rsi_7_range = self.entry_filters['rsi_7_range']

            if rsi_7 < rsi_7_range[0] or rsi_7 > rsi_7_range[1]:
                result['reason'] = f'RSI-7 {rsi_7:.1f} outside range {rsi_7_range}'
                return result
            result['filters_passed']['rsi_7_range'] = True

        # FILTER 7: Stochastic D minimum (RELAXED - was 35, now 30)
        # User avg: 50.8, False signals avg: 45.7
        if 'stoch_d' in df.columns and 'min_stoch_d' in self.entry_filters:
            stoch_d = latest['stoch_d']
            min_stoch_d = self.entry_filters['min_stoch_d']

            if stoch_d < min_stoch_d:
                result['reason'] = f'Stoch D {stoch_d:.1f} < {min_stoch_d} threshold'
                return result
            result['filters_passed']['stoch_d_filter'] = True

        # FILTER 8: Volume status (RELAXED - now allows 'low' for ribbon flips)
        # User: only 5% LOW volume, False signals: 36% LOW volume!
        volume_status = latest.get('volume_status', 'normal')
        volume_requirement = self.entry_filters.get('volume_requirement', ['spike', 'elevated', 'normal'])

        if volume_status not in volume_requirement:
            result['reason'] = f'Volume {volume_status} not in {volume_requirement}'
            return result
        result['filters_passed']['volume_status'] = True

        # FILTER 9: Volume ratio (RELAXED - was 1.0, now 0.8 for early entry)
        if 'volume_ratio' in df.columns and 'min_volume_ratio' in self.entry_filters:
            volume_ratio = latest['volume_ratio']
            min_vol_ratio = self.entry_filters['min_volume_ratio']

            if volume_ratio < min_vol_ratio:
                result['reason'] = f'Volume ratio {volume_ratio:.2f} < {min_vol_ratio} threshold'
                return result
            result['filters_passed']['volume_ratio'] = True

        # OPTIONAL: Bollinger Bands (keep for volatility awareness)
        if self.entry_filters.get('use_bollinger', True):
            bb_upper = latest.get('bb_upper', None)
            bb_lower = latest.get('bb_lower', None)
            bb_middle = latest.get('bb_middle', None)
            price = latest['close']

            if bb_upper and bb_lower and bb_middle:
                if direction == 'long' and price > bb_middle * 0.995:
                    result['filters_passed']['bollinger'] = True
                    result['confidence'] += 0.05
                elif direction == 'short' and price < bb_middle * 1.005:
                    result['filters_passed']['bollinger'] = True
                    result['confidence'] += 0.05

        # FILTER 10: Multi-Timeframe Confirmation (RELAXED - less restrictive now)
        # Check if lower timeframes (5m, 15m) confirm the signal
        if self.mtf_analyzer is not None and self.entry_filters.get('require_mtf_confirmation', True):
            timestamp = latest['timestamp'] if 'timestamp' in latest else pd.Timestamp.now()

            mtf_result = self.mtf_analyzer.get_mtf_confirmation(timestamp, direction)

            if not mtf_result['confirmed']:
                result['reason'] = f'MTF not confirmed: {mtf_result["reason"]}'
                return result

            result['filters_passed']['mtf_confirmation'] = True
            result['confidence'] += mtf_result['mtf_score']  # Add MTF score to confidence

        # BONUS: Support/Resistance awareness (not required, just bonus)
        # User had 22.7% at exact levels, so give small bonus
        if 'support_resistance' in latest or True:  # Would need to calculate
            # This would need S/R detection in indicators
            # For now, skip - but architecture is here
            pass

        # Calculate quality score (simpler than original)
        quality_score = self._calculate_quality_score(latest, direction, score, gap, result['filters_passed'])
        result['quality_score'] = quality_score

        # Quality threshold (much lower - user trades are less filtered)
        min_quality = self.entry_filters.get('min_quality_score', 30)
        if quality_score < min_quality:
            result['reason'] = f'Quality score {quality_score:.1f} < {min_quality} threshold'
            return result

        # SIGNAL APPROVED!
        result['signal'] = True
        result['reason'] = f'{direction.upper()} signal: score={score:.1f}, quality={quality_score:.1f}, filters={len(result["filters_passed"])}'
        return result

    def _calculate_quality_score(self, latest: pd.Series, direction: str,
                                  score: float, gap: float, filters_passed: dict) -> float:
        """
        Calculate quality score - SIMPLER than original

        User's trades are less complex, so scoring is simpler:
        - Base score from confluence (40 pts)
        - Volume bonus (20 pts)
        - Indicator alignment (20 pts)
        - S/R bonus (20 pts)
        """
        quality = 0.0

        # Component 1: Confluence score (40 points)
        # User avg: 32 for longs, 30 for shorts
        if score >= 40:
            quality += 40
        elif score >= 30:
            quality += 30
        elif score >= 20:
            quality += 20
        elif score >= 10:
            quality += 10

        # Component 2: Volume (20 points)
        # User: 50% normal, 18% elevated, 18% spike
        volume_status = latest.get('volume_status', 'normal')
        if volume_status == 'spike':
            quality += 20
        elif volume_status == 'elevated':
            quality += 15
        elif volume_status == 'normal':
            quality += 10  # User trades normal volume often!
        else:
            quality += 5

        # Component 3: Indicator alignment (20 points)
        if 'stochastic' in filters_passed:
            quality += 10
        if 'bollinger' in filters_passed:
            quality += 10

        # Component 4: Support/Resistance bonus (20 points)
        # Could add S/R detection here when available
        quality += 10  # Base assumption

        return min(quality, 100.0)

    def scan_historical_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scan entire dataframe for entry signals"""
        print("\n" + "="*80)
        print("SCANNING FOR ENTRY SIGNALS (USER PATTERN BASED)")
        print("="*80)

        df['entry_signal'] = False
        df['entry_direction'] = None
        df['entry_confidence'] = 0.0
        df['entry_reason'] = ''
        df['entry_quality_score'] = 0.0

        signals_found = 0
        long_signals = 0
        short_signals = 0

        for i in range(50, len(df)):  # Need history for indicators
            df_partial = df.iloc[:i+1].copy()
            signal = self.detect_signal(df_partial)

            df.loc[df.index[i], 'entry_signal'] = signal['signal']
            df.loc[df.index[i], 'entry_direction'] = signal['direction']
            df.loc[df.index[i], 'entry_confidence'] = signal['confidence']
            df.loc[df.index[i], 'entry_reason'] = signal['reason']
            df.loc[df.index[i], 'entry_quality_score'] = signal['quality_score']

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


if __name__ == '__main__':
    """Test the new entry detector"""
    import sys
    from pathlib import Path

    data_file = Path(__file__).parent / 'trading_data' / 'indicators' / 'eth_1h_full.csv'

    if not data_file.exists():
        print(f"❌ Data not found: {data_file}")
        sys.exit(1)

    print(f"📊 Loading data: {data_file}")
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"   Loaded {len(df)} candles")

    detector = EntryDetector()
    df = detector.scan_historical_signals(df)

    # Show signals
    signals_df = df[df['entry_signal'] == True][['timestamp', 'close', 'entry_direction',
                                                   'entry_confidence', 'entry_quality_score']]

    print(f"\n📋 Sample signals (first 20):")
    print(signals_df.head(20).to_string())

    # Save signals
    output_file = Path(__file__).parent / 'trading_data' / 'signals' / 'eth_1h_user_pattern_signals.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"\n💾 Signals saved: {output_file}")
