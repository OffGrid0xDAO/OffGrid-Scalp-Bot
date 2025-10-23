#!/usr/bin/env python3
"""
New Strategy Code Generator

Generates new entry_detector.py and exit_manager.py based on
discovered patterns from user's optimal trades.

This creates a strategy that mimics YOUR trading decisions!
"""

import json
from pathlib import Path
from datetime import datetime


def load_discovered_rules():
    """Load the discovered patterns from analysis"""
    rules_file = Path(__file__).parent / 'trading_data' / 'discovered_rules.json'

    if not rules_file.exists():
        print("❌ Rules file not found. Run analyze_optimal_patterns.py first!")
        return None

    with open(rules_file, 'r') as f:
        return json.load(f)


def generate_new_entry_detector():
    """
    Generate new entry_detector.py based on discovered patterns

    Key changes from analysis:
    1. Reduced confluence gap requirement (3.3 avg for longs, 2.0 for shorts)
    2. Removed MACD trend requirement (50/50 split in longs)
    3. Wider RSI acceptance (29-80 for longs, 25-63 for shorts)
    4. Accept normal volume (not just spikes/elevated)
    5. Stochastic in middle range (19-68 for longs, 12-74 for shorts)
    6. Less emphasis on S/R (only 22.7% at key levels)
    """

    code = '''#!/usr/bin/env python3
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

    def __init__(self, params_file: str = None):
        """Initialize entry detector with user-based parameters"""
        if params_file is None:
            params_file = Path(__file__).parent / 'strategy_params_user.json'

        # Create user-based params if not exists
        if not Path(params_file).exists():
            self._create_default_params(params_file)

        with open(params_file, 'r') as f:
            self.params = json.load(f)

        self.entry_filters = self.params['entry_filters']

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

        # FILTER 1: Minimum confluence score (very loose - user had min of 10)
        score_min = self.entry_filters['confluence_score_min']
        if score < score_min:
            result['reason'] = f'Confluence score {score:.1f} < {score_min} threshold'
            return result
        result['filters_passed']['confluence_score'] = True

        # FILTER 2: RSI range (wide acceptance)
        if 'rsi_14' in df.columns:
            rsi_range = self.entry_filters['rsi_range']
            rsi = latest['rsi_14']

            if rsi < rsi_range[0] or rsi > rsi_range[1]:
                result['reason'] = f'RSI {rsi:.1f} outside range {rsi_range}'
                return result
            result['filters_passed']['rsi_range'] = True

        # FILTER 3: Stochastic (wide middle range - user's avg ~44 for both)
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
        print("\\n" + "="*80)
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

        print(f"\\n📊 Signal Summary:")
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

    print(f"\\n📋 Sample signals (first 20):")
    print(signals_df.head(20).to_string())

    # Save signals
    output_file = Path(__file__).parent / 'trading_data' / 'signals' / 'eth_1h_user_pattern_signals.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"\\n💾 Signals saved: {output_file}")
'''

    return code


def generate_new_exit_manager():
    """
    Generate new exit_manager.py based on user's exit patterns

    For now, use a simple exit strategy since we only have entry data.
    We can refine this later when we analyze exit patterns.
    """

    code = '''#!/usr/bin/env python3
"""
Exit Manager - User Pattern Based Strategy

Simple exit strategy for now.
Can be refined once we analyze user's exit patterns.

Exit Rules:
1. Take profit at +2% (conservative, can be adjusted)
2. Stop loss at -1.5% (tight stop)
3. Trailing stop once in profit
4. Time-based exit after 24 hours if no TP/SL hit
"""

import pandas as pd
from typing import Dict, Optional


class ExitManager:
    """Manage trade exits with simple rules"""

    def __init__(self):
        """Initialize exit manager"""
        self.take_profit_pct = 2.0  # 2% TP
        self.stop_loss_pct = 1.5    # 1.5% SL
        self.trailing_stop_pct = 0.8  # 0.8% trailing after profit
        self.max_hold_hours = 24  # Max hold time

    def check_exit(self, entry_price: float, entry_time: pd.Timestamp,
                   current_price: float, current_time: pd.Timestamp,
                   direction: str, peak_profit_pct: float = 0.0) -> Dict:
        """
        Check if trade should exit

        Args:
            entry_price: Entry price
            entry_time: Entry timestamp
            current_price: Current price
            current_time: Current timestamp
            direction: 'long' or 'short'
            peak_profit_pct: Peak profit reached so far

        Returns:
            dict with exit decision
        """
        result = {
            'should_exit': False,
            'exit_reason': '',
            'exit_price': current_price,
            'profit_pct': 0.0
        }

        # Calculate current profit
        if direction == 'long':
            profit_pct = (current_price - entry_price) / entry_price * 100
        else:
            profit_pct = (entry_price - current_price) / entry_price * 100

        result['profit_pct'] = profit_pct

        # Exit 1: Take profit
        if profit_pct >= self.take_profit_pct:
            result['should_exit'] = True
            result['exit_reason'] = f'Take profit at +{profit_pct:.2f}%'
            return result

        # Exit 2: Stop loss
        if profit_pct <= -self.stop_loss_pct:
            result['should_exit'] = True
            result['exit_reason'] = f'Stop loss at {profit_pct:.2f}%'
            return result

        # Exit 3: Trailing stop (if we've been in profit)
        if peak_profit_pct > 0.5:  # If we've been in profit
            if profit_pct < peak_profit_pct - self.trailing_stop_pct:
                result['should_exit'] = True
                result['exit_reason'] = f'Trailing stop: profit {profit_pct:.2f}% < peak {peak_profit_pct:.2f}%'
                return result

        # Exit 4: Time-based exit
        hours_held = (current_time - entry_time).total_seconds() / 3600
        if hours_held >= self.max_hold_hours:
            result['should_exit'] = True
            result['exit_reason'] = f'Time exit after {hours_held:.1f}h at {profit_pct:.2f}%'
            return result

        return result


if __name__ == '__main__':
    """Test exit manager"""
    from datetime import datetime, timedelta

    exit_mgr = ExitManager()

    # Test scenarios
    entry_price = 4000
    entry_time = pd.Timestamp('2025-10-15 10:00:00')

    # Test 1: Take profit
    result = exit_mgr.check_exit(entry_price, entry_time, 4085,
                                  pd.Timestamp('2025-10-15 14:00:00'), 'long')
    print(f"Test 1 (TP): {result}")

    # Test 2: Stop loss
    result = exit_mgr.check_exit(entry_price, entry_time, 3940,
                                  pd.Timestamp('2025-10-15 14:00:00'), 'long')
    print(f"Test 2 (SL): {result}")

    # Test 3: Time exit
    result = exit_mgr.check_exit(entry_price, entry_time, 4010,
                                  pd.Timestamp('2025-10-16 11:00:00'), 'long')
    print(f"Test 3 (Time): {result}")
'''

    return code


def generate_strategy_files():
    """Generate all strategy files"""
    print("\n" + "="*80)
    print("🔧 GENERATING NEW STRATEGY CODE")
    print("="*80)

    # Load rules
    rules = load_discovered_rules()
    if rules is None:
        return False

    # Generate entry detector
    print("\n📝 Generating new entry_detector.py...")
    entry_code = generate_new_entry_detector()

    output_dir = Path(__file__).parent / 'src' / 'strategy'
    entry_file = output_dir / 'entry_detector_user_pattern.py'

    with open(entry_file, 'w') as f:
        f.write(entry_code)

    print(f"   ✅ Created: {entry_file}")

    # Generate exit manager
    print("\n📝 Generating new exit_manager.py...")
    exit_code = generate_new_exit_manager()

    exit_file = output_dir / 'exit_manager_user_pattern.py'

    with open(exit_file, 'w') as f:
        f.write(exit_code)

    print(f"   ✅ Created: {exit_file}")

    print("\n" + "="*80)
    print("✅ NEW STRATEGY GENERATED!")
    print("="*80)

    print("\nGenerated files:")
    print(f"  1. {entry_file}")
    print(f"  2. {exit_file}")

    print("\nKey differences from old strategy:")
    print("  ✓ Confluence gap: 0 min (vs 30) - you trade any gap!")
    print("  ✓ Volume: Accept normal (vs requiring elevated/spike)")
    print("  ✓ RSI: Wide range 20-85 (vs 30-70)")
    print("  ✓ MACD: Removed requirement (you ignore it)")
    print("  ✓ Stochastic: Middle range 15-70 (vs extremes)")
    print("  ✓ Quality score: 30 min (vs 70) - less filtering!")

    return True


if __name__ == '__main__':
    success = generate_strategy_files()

    if success:
        print("\n📊 Next step: Test the new strategy!")
        print("   Run: python src/strategy/entry_detector_user_pattern.py")
        print("\n📈 Then: Run backtest to compare!")
        print("   Run: python backtest_user_strategy.py")
