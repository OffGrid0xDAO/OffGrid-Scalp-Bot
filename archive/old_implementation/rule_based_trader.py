"""
Rule-Based Trader - User Pattern Matching System
Wrapper around UserPatternTrader to maintain interface compatibility
NOW USING: Ultra-selective momentum-based pattern matching (99.8% trade reduction)
"""

import json
import pandas as pd
from datetime import datetime
from user_pattern_trader import UserPatternTrader


class RuleBasedTrader:
    """
    Rule-based trader using user pattern matching system

    This is a wrapper that provides the same interface as the old RuleBasedTrader
    but uses the new UserPatternTrader under the hood.

    Key Differences from Old System:
    - 99.8% fewer trades (quality over quantity)
    - Momentum detection required
    - Multi-factor quality scoring
    - Pattern matching based on user's 9 profitable trades
    """

    def __init__(self):
        self.pattern_trader = UserPatternTrader()
        self.recent_trades = []
        self.version = "user_pattern_1.0"

        print("⚡ Rule-Based Trader (User Pattern Matching) initialized")
        print(f"📋 Version: {self.version}")
        print(f"🎯 Quality Threshold: {self.pattern_trader.rules['quality_filter']['min_score']}/100")
        print(f"🚀 Momentum Required: {self.pattern_trader.rules['momentum']['required']}")

    def get_trading_decision(self, indicators_5min: dict, indicators_15min: dict,
                            current_price: float, current_position: dict = None,
                            df_recent: pd.DataFrame = None) -> dict:
        """
        Get trading decision using user pattern matching

        Returns dict with:
        - entry_recommended: bool
        - exit_recommended: bool (if in position)
        - direction: 'LONG' or 'SHORT'
        - confidence: 0-1
        - reason: explanation
        """

        # Extract indicators with safe defaults
        compression = indicators_5min.get('compression', 0)
        if compression == 0:
            # Calculate from EMA values if not provided
            compression = self._calculate_compression(indicators_5min)

        light_emas = indicators_5min.get('light_emas', 0)
        if light_emas == 0 and 'MMA5' in indicators_5min:
            # Calculate if not provided
            light_emas = self._count_light_emas(indicators_5min)

        ribbon_state = indicators_5min.get('ribbon_state', 'unknown')

        # Build 5min indicators dict
        indicators = {
            'compression': compression,
            'light_emas': light_emas,
            'ribbon_state': ribbon_state,
            'price': current_price
        }

        # Build 15min indicators dict (extract ribbon state)
        indicators_15min_processed = {
            'ribbon_state': indicators_15min.get('ribbon_state', 'unknown'),
            'price': indicators_15min.get('price', current_price)
        }

        # Create minimal df_recent if not provided
        if df_recent is None:
            df_recent = pd.DataFrame([{'price': current_price, 'timestamp': datetime.now()}])
            current_idx = 0
        else:
            current_idx = len(df_recent) - 1

        # Check if we should exit current position
        if current_position:
            exit_decision = self._check_exit(current_position, current_price, indicators_5min)
            if exit_decision['exit_recommended']:
                return exit_decision

        # Get entry decision from pattern trader (NOW WITH DUAL TIMEFRAME ANALYSIS!)
        decision = self.pattern_trader.get_trade_decision(
            indicators_5min=indicators,
            indicators_15min=indicators_15min_processed,
            current_price=current_price,
            df_recent=df_recent,
            current_idx=current_idx,
            recent_trades=self.recent_trades
        )

        # Track if we took a trade
        if decision.get('entry_recommended', False):
            self.recent_trades.append({
                'time': datetime.now().isoformat(),
                'direction': decision.get('direction'),
                'price': current_price
            })
            # Keep only last 20 trades
            self.recent_trades = self.recent_trades[-20:]

        return decision

    def _calculate_compression(self, indicators: dict) -> float:
        """Calculate compression from EMA values"""
        ema_values = []
        for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
            key = f'MMA{ema}'
            if key in indicators and isinstance(indicators[key], dict):
                val = indicators[key].get('value', 0)
                if val > 0:
                    ema_values.append(val)

        if len(ema_values) >= 3:
            ema_min = min(ema_values)
            ema_max = max(ema_values)
            return (ema_max - ema_min) / ema_min if ema_min > 0 else 0
        return 0

    def _count_light_emas(self, indicators: dict) -> int:
        """Count light green EMAs"""
        count = 0
        for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60]:
            key = f'MMA{ema}'
            if key in indicators and isinstance(indicators[key], dict):
                if indicators[key].get('color') == 'green' and indicators[key].get('intensity') == 'light':
                    count += 1
        return count

    def _check_exit(self, position: dict, current_price: float, indicators: dict) -> dict:
        """Check if we should exit current position"""
        entry_price = position.get('entry_price', current_price)
        direction = position.get('direction', 'LONG')
        entry_time = position.get('entry_time', datetime.now())

        # Calculate PnL
        if direction == 'LONG':
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price

        # Get exit rules
        exit_rules = self.pattern_trader.rules['exit']

        # Calculate hold time
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)
        hold_minutes = (datetime.now() - entry_time).total_seconds() / 60

        # Exit conditions
        exit_reason = None

        # 1. Stop loss
        if pnl_pct < -exit_rules['stop_loss']:
            exit_reason = f"stop_loss ({pnl_pct*100:.2f}%)"

        # 2. Profit targets (adaptive based on hold time)
        elif hold_minutes < exit_rules['quick_exit_minutes']:
            if pnl_pct > exit_rules['profit_target_quick']:
                exit_reason = f"quick_profit_target ({pnl_pct*100:.2f}%)"
        elif hold_minutes < exit_rules['medium_exit_minutes']:
            if pnl_pct > exit_rules['profit_target_medium']:
                exit_reason = f"medium_profit_target ({pnl_pct*100:.2f}%)"
        elif hold_minutes >= exit_rules['long_exit_minutes']:
            if pnl_pct > exit_rules['profit_target_long']:
                exit_reason = f"long_profit_target ({pnl_pct*100:.2f}%)"

        # 3. Max hold time
        if hold_minutes > exit_rules['long_exit_minutes'] and pnl_pct > 0:
            exit_reason = f"max_hold_time ({hold_minutes:.1f}min)"

        # 4. Ribbon flip (momentum reversal)
        ribbon_state = indicators.get('ribbon_state', 'unknown')
        if direction == 'LONG' and ribbon_state in ['all_red', 'mixed_red']:
            if pnl_pct > 0:  # Only exit on ribbon flip if profitable
                exit_reason = f"ribbon_flip_to_red"
        elif direction == 'SHORT' and ribbon_state in ['all_green', 'mixed_green']:
            if pnl_pct > 0:
                exit_reason = f"ribbon_flip_to_green"

        if exit_reason:
            return {
                'entry_recommended': False,
                'exit_recommended': True,
                'reason': exit_reason,
                'pnl_pct': pnl_pct * 100
            }

        return {'exit_recommended': False}

    def get_cost_summary(self) -> dict:
        """
        Return cost summary for compatibility with dashboard
        User pattern system doesn't use Claude API for trading decisions
        """
        return {
            'session_cost_usd': 0.0,
            'total_calls': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cached_tokens': 0,
            'total_cost': 0.0,
            'avg_cost_per_decision': 0.0,
            'decisions_count': 0
        }


if __name__ == '__main__':
    # Test initialization
    trader = RuleBasedTrader()
    print(f"\n✅ Trader ready!")
    print(f"   Version: {trader.version}")
    print(f"   Quality threshold: {trader.pattern_trader.rules['quality_filter']['min_score']}/100")
