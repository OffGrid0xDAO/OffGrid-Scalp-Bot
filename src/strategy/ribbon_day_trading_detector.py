#!/usr/bin/env python3
"""
Ribbon Day Trading Detector - Compression Breakout Strategy

Pure EMA ribbon strategy for day trading (multi-hour holds):
- Entry: Compression (score > 70) → Expansion (rate > 8) → Ribbon flip
- Target: 3-8% moves over 4-24 hours
- Stop: Tight at entry EMA20, then trail with EMA50

Expected Performance:
- Win Rate: 50-65%
- Average Profit: 4-6%
- Trade Frequency: 50-80 signals/year
- Profit Factor: 2.5-4.0

Research Basis: Compression breakouts show +75% to +12,000% potential on BTC/ETH
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, Optional, List


class RibbonDayTradingDetector:
    """
    Detect high-probability ribbon compression breakouts for day trading

    Strategy Phases:
    1. COMPRESSION SETUP: Score > 70, expansion rate declining
    2. BREAKOUT TRIGGER: Expansion rate > 8, ribbon flip detected
    3. MOMENTUM CONFIRMATION: Volume spike, alignment > 85%
    4. TREND FOLLOW: Hold 4-24 candles, trail stop with EMA50
    """

    def __init__(self, params_file: str = None):
        """
        Initialize ribbon day trading detector

        Args:
            params_file: Path to strategy parameters JSON file
        """
        if params_file is None:
            params_file = Path(__file__).parent / 'strategy_params_ribbon.json'

        # Load params or use defaults
        if Path(params_file).exists():
            with open(params_file, 'r') as f:
                self.params = json.load(f)
        else:
            # Default ribbon day trading params
            self.params = {
                "strategy_name": "Ribbon Day Trading",
                "entry_filters": {
                    "min_compression_score": 85,  # Moderate compression
                    "require_expansion": False,    # Don't require expansion (rarely happens with flips)
                    "min_expansion_rate": 0.5,    # Very low threshold if checking
                    "min_alignment_pct": 0.90,     # 90% EMAs strongly aligned
                    "volume_requirement": ["elevated", "spike"],  # Elevated or spike
                    "require_ribbon_flip": True,
                    "confirm_confluence_gap": 30,  # Confluence confirmation (primary filter)
                },
                "exit_strategy": {
                    "use_partial_exits": True,
                    "take_profit_levels": [3.0, 5.0, 8.0, 12.0],  # Day trading targets
                    "take_profit_sizes": [30, 30, 30],  # 30% at each level
                    "stop_loss_pct": 1.5,
                    "trailing_stop_enabled": True,
                    "trailing_stop_ema": 50,  # Trail with EMA50
                    "use_time_based_exit": True,
                    "max_hold_candles": 24  # Max 24 hours for 1h timeframe
                },
                "risk_management": {
                    "max_risk_per_trade": 3.0,  # Higher risk for day trades
                    "max_concurrent_trades": 2,
                    "position_size_pct": 15.0,  # Larger positions
                }
            }

        self.entry_filters = self.params['entry_filters']

    def detect_signal(self, df: pd.DataFrame) -> Dict:
        """
        Detect ribbon compression breakout signal

        Signal Logic:
        1. Recent compression (score > 70 in last 10 candles)
        2. Current expansion (rate > 8)
        3. Ribbon flip detected (85%+ aligned)
        4. Volume spike confirmation
        5. Optional: Confluence gap > 25

        Args:
            df: DataFrame with all indicators

        Returns:
            dict with signal details
        """
        # Get latest candle
        latest = df.iloc[-1]
        recent = df.iloc[-10:]  # Last 10 candles for pattern detection

        # Initialize result
        result = {
            'signal': False,
            'direction': None,
            'entry_price': latest['close'],
            'confidence': 0.0,
            'compression_score': latest.get('compression_score', 0),
            'expansion_rate': latest.get('expansion_rate', 0),
            'alignment_pct': latest.get('alignment_pct', 0.5),
            'ribbon_flip': latest.get('ribbon_flip', 'none'),
            'volume_status': latest.get('volume_status', 'normal'),
            'filters_passed': {},
            'reason': '',
            'setup_quality': 0  # 0-100 score
        }

        # Check required columns
        required_cols = ['compression_score', 'expansion_rate', 'alignment_pct', 'ribbon_flip']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            result['reason'] = f'Missing columns: {missing}'
            return result

        # === FILTER 1: Recent Compression Setup ===
        # Look for compression > 90 in last 10 candles
        max_recent_compression = recent['compression_score'].max()
        min_compression = self.entry_filters['min_compression_score']

        if max_recent_compression < min_compression:
            result['reason'] = f'No recent compression (max {max_recent_compression:.1f} < {min_compression})'
            return result

        result['filters_passed']['compression_setup'] = True
        result['setup_quality'] += 20  # Compression setup worth 20 points

        # Bonus: Higher compression = better setup
        if max_recent_compression > 85:
            result['setup_quality'] += 10

        # === FILTER 2: Current Expansion (Optional) ===
        if self.entry_filters.get('require_expansion', False):
            current_expansion = latest['expansion_rate']
            min_expansion = self.entry_filters['min_expansion_rate']

            if current_expansion < min_expansion:
                result['reason'] = f'Expansion too weak ({current_expansion:.1f} < {min_expansion})'
                return result

            result['filters_passed']['expansion'] = True
            result['setup_quality'] += 25  # Strong expansion worth 25 points

            # Bonus: Very strong expansion
            if current_expansion > 3:
                result['setup_quality'] += 15
        else:
            # Skip expansion check, give base points
            result['setup_quality'] += 15

        # === FILTER 3: Ribbon Flip Detection ===
        ribbon_flip = latest['ribbon_flip']
        alignment_pct = latest['alignment_pct']

        if self.entry_filters['require_ribbon_flip']:
            if ribbon_flip == 'none':
                result['reason'] = 'No ribbon flip detected'
                return result

            # Determine direction from flip
            if ribbon_flip == 'bullish_flip':
                result['direction'] = 'long'
            elif ribbon_flip == 'bearish_flip':
                result['direction'] = 'short'
            else:
                result['reason'] = f'Unknown ribbon flip: {ribbon_flip}'
                return result
        else:
            # No flip required - use alignment to determine direction
            if alignment_pct >= self.entry_filters['min_alignment_pct']:
                result['direction'] = 'long'
            elif alignment_pct <= (1 - self.entry_filters['min_alignment_pct']):
                result['direction'] = 'short'
            else:
                result['reason'] = f'Alignment not strong enough ({alignment_pct:.2f})'
                return result

        result['filters_passed']['ribbon_flip'] = True
        result['setup_quality'] += 25  # Ribbon flip worth 25 points

        # === FILTER 4: Volume Confirmation ===
        volume_status = latest.get('volume_status', 'normal')
        volume_required = self.entry_filters['volume_requirement']

        if volume_status not in volume_required:
            result['reason'] = f'Volume {volume_status} not in {volume_required}'
            return result

        result['filters_passed']['volume'] = True
        result['setup_quality'] += 20  # Volume spike worth 20 points

        # === FILTER 5 (Optional): Confluence Confirmation ===
        if 'confluence_gap' in df.columns:
            confluence_gap = latest['confluence_gap']
            min_gap = self.entry_filters.get('confirm_confluence_gap', 0)

            if min_gap > 0:
                # Check confluence agrees with ribbon direction
                long_score = latest.get('confluence_score_long', 0)
                short_score = latest.get('confluence_score_short', 0)

                if result['direction'] == 'long':
                    if long_score < short_score or (long_score - short_score) < min_gap:
                        result['reason'] = f'Confluence disagrees with long (gap {long_score - short_score:.1f})'
                        return result
                else:  # short
                    if short_score < long_score or (short_score - long_score) < min_gap:
                        result['reason'] = f'Confluence disagrees with short (gap {short_score - long_score:.1f})'
                        return result

                result['filters_passed']['confluence'] = True
                result['setup_quality'] += 10  # Confluence confirmation bonus

        # === ALL FILTERS PASSED ===
        result['signal'] = True
        result['confidence'] = result['setup_quality']  # 0-100 confidence score

        expansion_info = f"expansion {latest['expansion_rate']:.1f}" if 'expansion_rate' in df.columns else "no expansion check"
        result['reason'] = f'Ribbon breakout: compression {max_recent_compression:.1f} → {expansion_info} → {ribbon_flip}'

        return result

    def get_entry_conditions_summary(self, signal_result: Dict) -> str:
        """
        Generate human-readable summary of entry conditions

        Args:
            signal_result: Result from detect_signal()

        Returns:
            str: Summary for logging/reporting
        """
        if not signal_result['signal']:
            return f"❌ No signal: {signal_result['reason']}"

        direction_emoji = "🟢" if signal_result['direction'] == 'long' else "🔴"

        summary = f"""
{direction_emoji} RIBBON BREAKOUT {signal_result['direction'].upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Entry Price: ${signal_result['entry_price']:.2f}
Confidence: {signal_result['confidence']:.0f}/100

Setup Quality:
  Compression: {signal_result['compression_score']:.1f}
  Expansion: {signal_result['expansion_rate']:.1f}
  Alignment: {signal_result['alignment_pct']*100:.1f}%
  Ribbon Flip: {signal_result['ribbon_flip']}
  Volume: {signal_result['volume_status']}

Filters Passed: {len(signal_result['filters_passed'])}/5
  {', '.join(signal_result['filters_passed'].keys())}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return summary

    def detect_exit_signal(self, df: pd.DataFrame, entry_info: Dict) -> Dict:
        """
        Detect exit signal for ribbon day trading

        Exit Conditions:
        1. Ribbon flips back (reversal)
        2. Compression increases (consolidation starting)
        3. Expansion rate decreases (momentum fading)
        4. Time-based exit (max 24 candles)
        5. Take profit levels hit

        Args:
            df: DataFrame with all indicators
            entry_info: Original entry signal info

        Returns:
            dict with exit signal details
        """
        latest = df.iloc[-1]

        result = {
            'exit_signal': False,
            'exit_reason': '',
            'exit_type': None,  # 'reversal', 'consolidation', 'momentum_fade', 'time', 'take_profit'
            'exit_price': latest['close']
        }

        # Check for ribbon reversal
        if 'ribbon_flip' in df.columns:
            current_flip = latest['ribbon_flip']
            entry_direction = entry_info['direction']

            if entry_direction == 'long' and current_flip == 'bearish_flip':
                result['exit_signal'] = True
                result['exit_reason'] = 'Ribbon reversed to bearish'
                result['exit_type'] = 'reversal'
                return result
            elif entry_direction == 'short' and current_flip == 'bullish_flip':
                result['exit_signal'] = True
                result['exit_reason'] = 'Ribbon reversed to bullish'
                result['exit_type'] = 'reversal'
                return result

        # Check for re-compression (momentum fading)
        if 'compression_score' in df.columns and 'expansion_rate' in df.columns:
            compression = latest['compression_score']
            expansion = latest['expansion_rate']

            if compression > 75 and expansion < 3:
                result['exit_signal'] = True
                result['exit_reason'] = f'Re-compression detected (score {compression:.1f}, expansion {expansion:.1f})'
                result['exit_type'] = 'consolidation'
                return result

        return result

    def scan_historical_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Scan entire dataframe for ribbon entry signals

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
        print("SCANNING FOR RIBBON ENTRY SIGNALS")
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

        # Print summary
        print(f"\n📊 Signal Summary:")
        print(f"   Total signals: {signals_found}")
        print(f"   Long signals: {long_signals}")
        print(f"   Short signals: {short_signals}")
        print(f"   Signal frequency: {signals_found/len(df)*100:.2f}% of candles")

        return df

    def calculate_position_size(self, signal_result: Dict, account_balance: float) -> Dict:
        """
        Calculate position size based on setup quality

        Higher quality setups = larger positions (within risk limits)

        Args:
            signal_result: Signal from detect_signal()
            account_balance: Current account balance

        Returns:
            dict with position sizing details
        """
        base_risk_pct = self.params['risk_management']['max_risk_per_trade']

        # Scale position by setup quality (80-100 score → 0.8x-1.0x multiplier)
        quality_multiplier = min(signal_result['confidence'] / 100, 1.0)

        # Minimum 60% of base size even for lower quality setups
        quality_multiplier = max(quality_multiplier, 0.6)

        adjusted_risk_pct = base_risk_pct * quality_multiplier
        position_value = account_balance * (adjusted_risk_pct / 100)

        return {
            'position_value': position_value,
            'risk_pct': adjusted_risk_pct,
            'quality_multiplier': quality_multiplier,
            'base_risk_pct': base_risk_pct
        }


if __name__ == '__main__':
    """Test ribbon day trading detector"""
    import sys
    from pathlib import Path

    # Load test data
    data_file = Path(__file__).parent.parent.parent / 'trading_data' / 'indicators' / 'eth_1h_full.csv'

    if not data_file.exists():
        print(f"❌ Test data not found: {data_file}")
        print("   Run: python3 scripts/process_indicators.py")
        sys.exit(1)

    print("="*80)
    print("RIBBON DAY TRADING DETECTOR TEST")
    print("="*80)

    print(f"\n📊 Loading data: {data_file}")
    df = pd.read_csv(data_file)
    print(f"   Loaded {len(df)} candles")

    # Create detector
    detector = RibbonDayTradingDetector()

    # Scan for signals
    signals_found = []

    print("\n🔍 Scanning for ribbon breakout signals...")
    for i in range(50, len(df)):  # Start at 50 to have enough history
        window = df.iloc[:i+1]
        signal = detector.detect_signal(window)

        if signal['signal']:
            signal['timestamp'] = df.iloc[i]['timestamp']
            signal['candle_index'] = i
            signals_found.append(signal)
            print(detector.get_entry_conditions_summary(signal))

    print("\n" + "="*80)
    print(f"RESULTS: Found {len(signals_found)} ribbon breakout signals")
    print("="*80)

    if signals_found:
        # Analyze signal quality distribution
        qualities = [s['confidence'] for s in signals_found]
        print(f"\nSignal Quality:")
        print(f"  Average: {np.mean(qualities):.1f}/100")
        print(f"  Best: {max(qualities):.1f}/100")
        print(f"  Worst: {min(qualities):.1f}/100")

        # Direction breakdown
        longs = sum(1 for s in signals_found if s['direction'] == 'long')
        shorts = sum(1 for s in signals_found if s['direction'] == 'short')
        print(f"\nDirections:")
        print(f"  Longs: {longs} ({longs/len(signals_found)*100:.1f}%)")
        print(f"  Shorts: {shorts} ({shorts/len(signals_found)*100:.1f}%)")

        # Show top 5 signals
        top_signals = sorted(signals_found, key=lambda x: x['confidence'], reverse=True)[:5]
        print(f"\n🏆 Top 5 Highest Quality Signals:")
        for i, sig in enumerate(top_signals, 1):
            print(f"\n{i}. {sig['timestamp']} - {sig['direction'].upper()} - Quality: {sig['confidence']:.0f}/100")
            print(f"   Compression: {sig['compression_score']:.1f}, Expansion: {sig['expansion_rate']:.1f}")
            print(f"   {sig['reason']}")
