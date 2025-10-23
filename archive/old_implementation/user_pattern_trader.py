"""
User Pattern Trader
Trades based on the patterns found in YOUR 9 profitable trades
Focus on QUALITY over QUANTITY with momentum detection
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional


class UserPatternTrader:
    """
    Trader that mimics user's successful pattern recognition

    Key Differences from Current System:
    1. MOMENTUM DETECTION: Identifies big moves (like your +1.93% trade)
    2. QUALITY SCORING: Multi-factor confidence system
    3. PATTERN MATCHING: Looks for YOUR specific setups
    4. ADAPTIVE FILTERING: Tight AND wide compression both valid
    """

    def __init__(self):
        self.load_rules()

    def load_rules(self):
        """Load user pattern rules"""
        try:
            # Try trading_rules.json first (main config file)
            with open('trading_rules.json', 'r') as f:
                rules = json.load(f)
                # Verify it's a user_pattern version
                if 'user_pattern' in str(rules.get('version', '')).lower():
                    self.rules = rules
                else:
                    # Fall back to dedicated file
                    with open('trading_rules_user_pattern.json', 'r') as f:
                        self.rules = json.load(f)
        except FileNotFoundError:
            # Create default rules based on user's 9 trades
            self.rules = self.create_default_rules()
            self.save_rules()

    def create_default_rules(self) -> dict:
        """Create rules based on user's successful trades"""
        return {
            "version": "user_pattern_1.0",
            "description": "Pattern matching based on 9 profitable user trades",

            # COMPRESSION: Accept both tight AND wide (user trades both)
            "compression": {
                "tight_min": 0.0005,   # 0.05% (your tightest trade)
                "tight_max": 0.0015,   # 0.15%
                "wide_min": 0.0025,    # 0.25%
                "wide_max": 0.0060,    # 0.60% (your widest trade)
                "medium_allowed": True  # Accept 0.15-0.25% too
            },

            # LIGHT EMAs: Accept 0 (strong trend) OR 5+ (transition)
            "light_emas": {
                "strong_trend_max": 2,     # 0-2 = strong trend (3 of your trades)
                "transition_min": 5,        # 5+ = transition (5 of your trades)
                "avoid_middle": True        # Skip 3-4 (you never trade these)
            },

            # RIBBON STATE: All states acceptable (you trade them all)
            "ribbon_state": {
                "allowed": ["all_green", "all_red", "mixed", "mixed_green", "mixed_red"],
                "prefer_aligned": False  # You trade counter-trend too
            },

            # MOMENTUM DETECTION: Catch the big moves
            "momentum": {
                "enabled": True,
                "required": True,  # NEW: Require momentum for most trades
                "lookback_minutes": 10,
                "big_move_threshold": 0.004,  # 0.4% move in 10min (stricter)
                "acceleration_threshold": 1.5  # Move accelerating
            },

            # QUALITY SCORING: Must score high enough
            "quality_filter": {
                "min_score": 60,  # Out of 100 - Adjusted for dual timeframe scoring
                "factors": {
                    "compression_match": 20,       # Matches your patterns
                    "light_ema_match": 15,         # Matches your patterns
                    "momentum_detected": 25,       # Big move happening
                    "ribbon_aligned": 10,          # Single timeframe ribbon
                    "timeframe_alignment": 25,     # NEW: Dual timeframe confluence
                    "volatility_spike": 5          # Vol expansion
                }
            },

            # EXIT RULES: Based on your hold times
            "exit": {
                "quick_exit_minutes": 15,      # Some trades 8-18min
                "medium_exit_minutes": 45,     # Most trades 25-54min
                "long_exit_minutes": 120,      # One trade 158min
                "profit_target_quick": 0.004,  # 0.4% for quick
                "profit_target_medium": 0.007, # 0.7% for medium
                "profit_target_long": 0.015,   # 1.5% for long
                "stop_loss": 0.002,            # 0.2% max loss
                "adaptive_exit": True          # Adjust based on momentum
            },

            # TRADE FREQUENCY: Strict limits (9 trades in ~24hrs = ~0.37/hour)
            "frequency": {
                "max_trades_per_hour": 1,
                "max_trades_per_4_hours": 2,
                "max_trades_per_day": 12,
                "min_time_between_trades_min": 15
            }
        }

    def save_rules(self):
        """Save rules to file"""
        with open('trading_rules_user_pattern.json', 'w') as f:
            json.dump(self.rules, f, indent=2)

    def detect_momentum(self, df: pd.DataFrame, current_idx: int) -> Dict:
        """
        Detect if a big move is happening (like your +1.93% trade)
        Returns momentum score and direction
        """
        if current_idx < 10:
            return {'detected': False, 'score': 0}

        lookback = self.rules['momentum']['lookback_minutes']
        threshold = self.rules['momentum']['big_move_threshold']

        # Get recent price action
        recent_data = df.iloc[max(0, current_idx-lookback):current_idx+1]

        if len(recent_data) < 3:
            return {'detected': False, 'score': 0}

        # Calculate price movement
        start_price = recent_data['price'].iloc[0]
        current_price = recent_data['price'].iloc[-1]
        price_change_pct = abs(current_price - start_price) / start_price

        # Calculate acceleration (is move speeding up?)
        mid_point = len(recent_data) // 2
        first_half_change = abs(recent_data['price'].iloc[mid_point] - recent_data['price'].iloc[0]) / recent_data['price'].iloc[0]
        second_half_change = abs(recent_data['price'].iloc[-1] - recent_data['price'].iloc[mid_point]) / recent_data['price'].iloc[mid_point]

        acceleration = second_half_change / first_half_change if first_half_change > 0 else 1

        # Momentum detected if big move AND accelerating
        if price_change_pct > threshold and acceleration > self.rules['momentum']['acceleration_threshold']:
            direction = 'UP' if current_price > start_price else 'DOWN'
            score = min(100, (price_change_pct / threshold) * 50 + (acceleration / 2) * 50)
            return {
                'detected': True,
                'score': score,
                'direction': direction,
                'magnitude': price_change_pct * 100
            }

        return {'detected': False, 'score': 0}

    def check_timeframe_alignment(self, indicators_5min: Dict, indicators_15min: Dict) -> Dict:
        """
        Check if 5min and 15min timeframes are aligned
        Returns alignment strength and details

        STRONG: Both timeframes agree on direction (ribbon states match)
        MODERATE: Same general direction but different intensity
        WEAK: Timeframes showing different states
        CONFLICTING: Timeframes showing opposite directions
        """
        ribbon_5min = indicators_5min.get('ribbon_state', 'unknown')
        ribbon_15min = indicators_15min.get('ribbon_state', 'unknown')

        # Classify ribbon states into directions
        bullish_states = ['all_green', 'mixed_green']
        bearish_states = ['all_red', 'mixed_red']
        neutral_states = ['mixed', 'unknown', 'yellow']

        is_5min_bullish = ribbon_5min in bullish_states
        is_5min_bearish = ribbon_5min in bearish_states
        is_15min_bullish = ribbon_15min in bullish_states
        is_15min_bearish = ribbon_15min in bearish_states

        # Check for conflicting timeframes (WORST - block trades)
        if (is_5min_bullish and is_15min_bearish) or (is_5min_bearish and is_15min_bullish):
            return {
                'alignment': 'CONFLICTING',
                'score': 0,
                'description': f'5min:{ribbon_5min} conflicts with 15min:{ribbon_15min}',
                'should_trade': False
            }

        # Check for strong alignment (BEST)
        if ribbon_5min == ribbon_15min:
            # Exact match - strongest signal
            return {
                'alignment': 'STRONG',
                'score': 100,
                'description': f'Both timeframes {ribbon_5min}',
                'should_trade': True,
                'direction': 'LONG' if is_5min_bullish else 'SHORT'
            }

        # Check for moderate alignment (GOOD)
        if (is_5min_bullish and is_15min_bullish) or (is_5min_bearish and is_15min_bearish):
            # Same direction, different intensity
            return {
                'alignment': 'MODERATE',
                'score': 70,
                'description': f'5min:{ribbon_5min}, 15min:{ribbon_15min} (same direction)',
                'should_trade': True,
                'direction': 'LONG' if is_5min_bullish else 'SHORT'
            }

        # One or both neutral (WEAK)
        if ribbon_5min in neutral_states or ribbon_15min in neutral_states:
            # Use the non-neutral timeframe if available
            direction = None
            if is_5min_bullish or is_15min_bullish:
                direction = 'LONG'
            elif is_5min_bearish or is_15min_bearish:
                direction = 'SHORT'

            return {
                'alignment': 'WEAK',
                'score': 30,
                'description': f'5min:{ribbon_5min}, 15min:{ribbon_15min} (unclear)',
                'should_trade': False,  # Too uncertain
                'direction': direction
            }

        # Unknown state (safest to not trade)
        return {
            'alignment': 'UNKNOWN',
            'score': 0,
            'description': f'5min:{ribbon_5min}, 15min:{ribbon_15min}',
            'should_trade': False
        }

    def calculate_quality_score(self, indicators_5min: Dict, indicators_15min: Dict,
                               momentum: Dict, timeframe_alignment: Dict) -> Dict:
        """
        Calculate trade quality score based on multiple factors INCLUDING dual timeframe analysis
        Returns score out of 100 and breakdown
        """
        score = 0
        breakdown = {}

        # Extract 5min indicators for compatibility
        indicators = indicators_5min

        # Factor 1: Compression Match (20 points) - reduced from 25
        compression = indicators.get('compression', 0)
        comp_rules = self.rules['compression']

        if comp_rules['tight_min'] <= compression <= comp_rules['tight_max']:
            # Tight compression (5 of your trades)
            compression_score = 20
        elif comp_rules['wide_min'] <= compression <= comp_rules['wide_max']:
            # Wide compression (2 of your trades)
            compression_score = 16
        elif comp_rules['medium_allowed'] and comp_rules['tight_max'] < compression < comp_rules['wide_min']:
            # Medium compression (1 of your trades)
            compression_score = 14
        else:
            compression_score = 0

        score += compression_score
        breakdown['compression_match'] = compression_score

        # Factor 2: Light EMA Match (15 points) - reduced from 20
        light_emas = indicators.get('light_emas', 0)
        ema_rules = self.rules['light_emas']

        if light_emas <= ema_rules['strong_trend_max']:
            # Strong trend (3 of your trades)
            light_ema_score = 15
        elif light_emas >= ema_rules['transition_min']:
            # Transition (5 of your trades)
            light_ema_score = 15
        else:
            # Middle zone (you never trade this)
            light_ema_score = 0

        score += light_ema_score
        breakdown['light_ema_match'] = light_ema_score

        # Factor 3: Momentum Detected (25 points) - reduced from 30
        if momentum.get('detected', False):
            momentum_score = min(25, momentum.get('score', 0) * 0.25)
        else:
            momentum_score = 0

        score += momentum_score
        breakdown['momentum_detected'] = momentum_score

        # Factor 4: Ribbon Aligned (10 points) - reduced from 15
        ribbon_state = indicators.get('ribbon_state', 'unknown')
        if ribbon_state in ['all_green', 'all_red']:
            ribbon_score = 10  # Clear direction
        elif ribbon_state in ['mixed_green', 'mixed_red']:
            ribbon_score = 7  # Some direction
        else:
            ribbon_score = 3   # Mixed

        score += ribbon_score
        breakdown['ribbon_aligned'] = ribbon_score

        # Factor 5: TIMEFRAME ALIGNMENT (25 points) - NEW!
        alignment_score = timeframe_alignment['score'] * 0.25  # Scale to 25 points max
        score += alignment_score
        breakdown['timeframe_alignment'] = alignment_score

        # Factor 6: Volatility Spike (5 points) - reduced from 10
        # Placeholder - would need vol calculation
        volatility_score = 3  # Default medium
        score += volatility_score
        breakdown['volatility_spike'] = volatility_score

        return {
            'total_score': score,
            'breakdown': breakdown,
            'passed': score >= self.rules['quality_filter']['min_score']
        }

    def get_trade_decision(self, indicators_5min: Dict, indicators_15min: Dict,
                          current_price: float, df_recent: pd.DataFrame,
                          current_idx: int, recent_trades: list) -> Dict:
        """
        Main trading decision logic with DUAL TIMEFRAME ANALYSIS
        Returns entry/exit recommendations
        """

        # Check trade frequency limits
        if not self.check_frequency_limits(recent_trades):
            return {'entry_recommended': False, 'reason': 'frequency_limit'}

        # STEP 1: Check timeframe alignment FIRST (critical filter)
        timeframe_alignment = self.check_timeframe_alignment(indicators_5min, indicators_15min)

        # BLOCK trades with conflicting or weak timeframes
        if not timeframe_alignment['should_trade']:
            return {
                'entry_recommended': False,
                'reason': f"timeframe_alignment_{timeframe_alignment['alignment'].lower()}",
                'timeframe_alignment': timeframe_alignment['alignment'],
                'alignment_description': timeframe_alignment['description']
            }

        # STEP 2: Detect momentum
        momentum = self.detect_momentum(df_recent, current_idx)

        # Extract 5min indicators
        indicators = {
            'compression': indicators_5min.get('compression', 0),
            'light_emas': indicators_5min.get('light_emas', 0),
            'ribbon_state': indicators_5min.get('ribbon_state', 'unknown'),
            'price': current_price
        }

        # STEP 3: Calculate quality score (now includes timeframe alignment)
        quality = self.calculate_quality_score(indicators_5min, indicators_15min, momentum, timeframe_alignment)

        # CRITICAL: Require momentum if enabled
        if self.rules['momentum']['required'] and not momentum.get('detected', False):
            return {
                'entry_recommended': False,
                'reason': 'no_momentum_detected',
                'timeframe_alignment': timeframe_alignment['alignment']
            }

        # STEP 4: Entry decision
        if quality['passed']:
            # Use timeframe alignment direction if available, otherwise use momentum
            if 'direction' in timeframe_alignment:
                direction = timeframe_alignment['direction']
            elif momentum.get('detected', False):
                direction = 'LONG' if momentum['direction'] == 'UP' else 'SHORT'
            else:
                # Fallback to ribbon state
                ribbon = indicators['ribbon_state']
                if ribbon in ['all_green', 'mixed_green']:
                    direction = 'LONG'
                elif ribbon in ['all_red', 'mixed_red']:
                    direction = 'SHORT'
                else:
                    return {
                        'entry_recommended': False,
                        'reason': 'no_clear_direction',
                        'timeframe_alignment': timeframe_alignment['alignment']
                    }

            return {
                'entry_recommended': True,
                'direction': direction,
                'confidence': quality['total_score'] / 100,
                'quality_score': quality['total_score'],
                'quality_breakdown': quality['breakdown'],
                'momentum': momentum,
                'timeframe_alignment': timeframe_alignment['alignment'],
                'alignment_description': timeframe_alignment['description'],
                'reason': f"Quality {quality['total_score']}/100 | {timeframe_alignment['alignment']} alignment"
            }

        return {
            'entry_recommended': False,
            'reason': f"Low quality: {quality['total_score']}/100 (need {self.rules['quality_filter']['min_score']})",
            'timeframe_alignment': timeframe_alignment['alignment']
        }

    def check_frequency_limits(self, recent_trades: list) -> bool:
        """Check if we're trading too frequently"""
        if not recent_trades:
            return True

        now = datetime.now()
        freq_rules = self.rules['frequency']

        # Count recent trades
        last_hour = [t for t in recent_trades if (now - datetime.fromisoformat(t['time'])).total_seconds() < 3600]
        last_4_hours = [t for t in recent_trades if (now - datetime.fromisoformat(t['time'])).total_seconds() < 14400]
        last_day = [t for t in recent_trades if (now - datetime.fromisoformat(t['time'])).total_seconds() < 86400]

        if len(last_hour) >= freq_rules['max_trades_per_hour']:
            return False
        if len(last_4_hours) >= freq_rules['max_trades_per_4_hours']:
            return False
        if len(last_day) >= freq_rules['max_trades_per_day']:
            return False

        # Check min time between trades
        if recent_trades:
            last_trade_time = datetime.fromisoformat(recent_trades[-1]['time'])
            minutes_since = (now - last_trade_time).total_seconds() / 60
            if minutes_since < freq_rules['min_time_between_trades_min']:
                return False

        return True


if __name__ == '__main__':
    # Create and save default rules
    trader = UserPatternTrader()
    print("✅ User Pattern Trader initialized")
    print(f"📋 Rules saved to: trading_rules_user_pattern.json")
    print(f"\n📊 Quality Filter: Min score {trader.rules['quality_filter']['min_score']}/100")
    print(f"🎯 Compression: Tight (0.05-0.15%) OR Wide (0.25-0.60%)")
    print(f"🎯 Light EMAs: Strong (0-2) OR Transition (5+)")
    print(f"🎯 Momentum: Enabled with 0.3% threshold")
    print(f"🎯 Max Trades: 1/hour, 2/4hours, 12/day")
