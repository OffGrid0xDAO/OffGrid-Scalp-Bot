"""
Rule-Based Trader - Executes trades using optimized rules from trading_rules.json
NO Claude API calls - runs fast and free between optimization cycles
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


class RuleBasedTrader:
    """Fast rule-based trader that uses optimized rules (no API calls)"""

    def __init__(self, rules_path: str = 'trading_rules.json'):
        self.rules_path = rules_path
        self.rules = self.load_rules()
        self.last_rules_reload = datetime.now()

        print(f"⚡ Rule-Based Trader initialized")
        print(f"📋 Rules version: {self.rules.get('version', 'unknown')}")
        print(f"🕐 Last updated: {self.rules.get('last_updated', 'unknown')}")

    def load_rules(self) -> dict:
        """Load trading rules from JSON"""
        with open(self.rules_path, 'r') as f:
            return json.load(f)

    def reload_rules_if_updated(self):
        """Reload rules if they've been updated (check every minute)"""
        if (datetime.now() - self.last_rules_reload).total_seconds() > 60:
            try:
                new_rules = self.load_rules()
                if new_rules.get('last_updated') != self.rules.get('last_updated'):
                    self.rules = new_rules
                    print(f"🔄 Rules reloaded! Updated: {self.rules.get('last_updated')}")
                self.last_rules_reload = datetime.now()
            except Exception as e:
                print(f"⚠️  Error reloading rules: {e}")

    def extract_ema_pattern(self, indicators: dict) -> dict:
        """Extract EMA color pattern from indicators"""
        pattern = {
            'green_count': 0,
            'red_count': 0,
            'gray_count': 0,
            'yellow_count': 0,
            'light_green_count': 0,
            'light_red_count': 0,
            'dark_green_count': 0,
            'dark_red_count': 0,
            'total_emas': 0
        }

        # Count EMAs by color and intensity
        for ema_name, ema_data in indicators.items():
            if not ema_name.startswith('MMA'):
                continue

            color = ema_data.get('color', 'unknown')
            intensity = ema_data.get('intensity', 'normal')

            pattern['total_emas'] += 1

            if color == 'green':
                pattern['green_count'] += 1
                if intensity == 'light':
                    pattern['light_green_count'] += 1
                elif intensity == 'dark':
                    pattern['dark_green_count'] += 1

            elif color == 'red':
                pattern['red_count'] += 1
                if intensity == 'light':
                    pattern['light_red_count'] += 1
                elif intensity == 'dark':
                    pattern['dark_red_count'] += 1

            elif color == 'yellow':
                pattern['yellow_count'] += 1

            elif color == 'gray':
                pattern['gray_count'] += 1

        # Calculate percentages
        total_non_yellow = pattern['green_count'] + pattern['red_count'] + pattern['gray_count']
        if total_non_yellow > 0:
            pattern['green_pct'] = pattern['green_count'] / total_non_yellow
            pattern['red_pct'] = pattern['red_count'] / total_non_yellow
        else:
            pattern['green_pct'] = 0
            pattern['red_pct'] = 0

        return pattern

    def determine_ribbon_state(self, pattern: dict) -> str:
        """Determine ribbon state based on EMA pattern"""
        threshold = self.rules['entry_rules']['ribbon_alignment_threshold']

        green_pct = pattern['green_pct']
        red_pct = pattern['red_pct']

        if green_pct >= threshold:
            return 'all_green'
        elif red_pct >= threshold:
            return 'all_red'
        elif green_pct > red_pct and green_pct >= 0.5:
            return 'mixed_green'
        elif red_pct > green_pct and red_pct >= 0.5:
            return 'mixed_red'
        else:
            return 'mixed'

    def check_entry_signal(
        self,
        indicators_5min: dict,
        indicators_15min: dict,
        current_price: float,
        ribbon_transition_time: Optional[datetime] = None
    ) -> Tuple[bool, str, float, str]:
        """
        Check if current conditions meet entry criteria based on rules

        Returns:
            (should_enter, direction, confidence, reasoning)
        """

        # Reload rules if updated
        self.reload_rules_if_updated()

        # Extract patterns
        pattern_5min = self.extract_ema_pattern(indicators_5min)
        pattern_15min = self.extract_ema_pattern(indicators_15min)

        # Determine ribbon states
        state_5min = self.determine_ribbon_state(pattern_5min)
        state_15min = self.determine_ribbon_state(pattern_15min)

        # Check if transition is fresh or stale
        is_fresh = False
        is_stale = False
        if ribbon_transition_time:
            minutes_since_flip = (datetime.now() - ribbon_transition_time).total_seconds() / 60
            is_fresh = minutes_since_flip <= self.rules['entry_rules']['fresh_transition_max_minutes']
            is_stale = minutes_since_flip >= self.rules['entry_rules']['stale_transition_min_minutes']

        # Get rules
        min_light_emas = self.rules['entry_rules']['min_light_emas_required']
        allowed_long_states = self.rules['entry_rules']['ribbon_states_allowed_long']
        allowed_short_states = self.rules['entry_rules']['ribbon_states_allowed_short']

        # Initialize
        should_enter = False
        direction = None
        confidence = 0.0
        reasoning = []

        # SIMPLIFIED: Check LONG conditions (matching backtest logic)
        # Primary check on 5min, 15min adds confidence
        if (state_5min in allowed_long_states and
            pattern_5min['light_green_count'] >= min_light_emas and
            not is_stale):

            should_enter = True
            direction = 'LONG'
            confidence = pattern_5min['green_pct']

            # 15min alignment adds confidence boost
            if state_15min in allowed_long_states and pattern_15min['light_green_count'] >= min_light_emas:
                confidence += 0.10
                reasoning.append(f"Both timeframes aligned bullish")
            else:
                reasoning.append(f"5min bullish signal (15min: {state_15min})")

            if is_fresh:
                confidence += 0.15  # Fresh transition boost
                reasoning.append("Fresh bullish transition")

            reasoning.append(f"5min: {state_5min} ({pattern_5min['light_green_count']} light green EMAs)")
            reasoning.append(f"15min: {state_15min} ({pattern_15min['light_green_count']} light green EMAs)")
            reasoning.append(f"Bullish momentum detected")

        # SIMPLIFIED: Check SHORT conditions (matching backtest logic)
        # Primary check on 5min, 15min adds confidence
        elif (state_5min in allowed_short_states and
              pattern_5min['light_red_count'] >= min_light_emas and
              not is_stale):

            should_enter = True
            direction = 'SHORT'
            confidence = pattern_5min['red_pct']

            # 15min alignment adds confidence boost
            if state_15min in allowed_short_states and pattern_15min['light_red_count'] >= min_light_emas:
                confidence += 0.10
                reasoning.append(f"Both timeframes aligned bearish")
            else:
                reasoning.append(f"5min bearish signal (15min: {state_15min})")

            if is_fresh:
                confidence += 0.15  # Fresh transition boost
                reasoning.append("Fresh bearish transition")

            reasoning.append(f"5min: {state_5min} ({pattern_5min['light_red_count']} light red EMAs)")
            reasoning.append(f"15min: {state_15min} ({pattern_15min['light_red_count']} light red EMAs)")
            reasoning.append(f"Bearish momentum detected")

        else:
            # No entry signal
            reasoning.append(f"5min: {state_5min}, 15min: {state_15min}")
            reasoning.append(f"Light EMAs: 5min G:{pattern_5min['light_green_count']} R:{pattern_5min['light_red_count']}, "
                           f"15min G:{pattern_15min['light_green_count']} R:{pattern_15min['light_red_count']}")
            reasoning.append(f"Conditions not met for entry (need {min_light_emas}+ light EMAs)")

            if is_stale:
                reasoning.append("Setup is STALE - ribbon has been in this state too long")

        reasoning_text = " | ".join(reasoning)

        return should_enter, direction, confidence, reasoning_text

    def check_exit_signal(
        self,
        indicators_5min: dict,
        indicators_15min: dict,
        entry_direction: str,
        entry_price: float,
        current_price: float,
        entry_time: datetime
    ) -> Tuple[bool, str, str]:
        """
        Check if current conditions meet exit criteria

        Returns:
            (should_exit, exit_reason, reasoning)
        """

        # Reload rules if updated
        self.reload_rules_if_updated()

        # Extract patterns
        pattern_5min = self.extract_ema_pattern(indicators_5min)
        pattern_15min = self.extract_ema_pattern(indicators_15min)

        # Determine ribbon states
        state_5min = self.determine_ribbon_state(pattern_5min)
        state_15min = self.determine_ribbon_state(pattern_15min)

        # Get exit rules
        max_hold_minutes = self.rules['exit_rules']['max_hold_minutes']
        profit_target_pct = self.rules['exit_rules']['profit_target_pct']
        stop_loss_pct = self.rules['exit_rules']['stop_loss_pct']
        exit_on_ribbon_flip = self.rules['exit_rules']['exit_on_ribbon_flip']

        # Calculate P&L
        if entry_direction == 'LONG':
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # SHORT
            pnl_pct = (entry_price - current_price) / entry_price

        # Time in position
        hold_time_minutes = (datetime.now() - entry_time).total_seconds() / 60

        # Check exit conditions

        # 1. Profit target hit
        if pnl_pct >= profit_target_pct:
            return True, 'profit_target', f"Profit target reached: {pnl_pct*100:.2f}%"

        # 2. Stop loss hit
        if pnl_pct <= -stop_loss_pct:
            return True, 'stop_loss', f"Stop loss triggered: {pnl_pct*100:.2f}%"

        # 3. Max hold time reached
        if hold_time_minutes >= max_hold_minutes:
            return True, 'max_hold_time', f"Max hold time reached: {hold_time_minutes:.1f} min"

        # 4. Ribbon flipped
        if exit_on_ribbon_flip:
            if entry_direction == 'LONG' and state_5min in ['all_red', 'mixed_red']:
                return True, 'ribbon_flip', f"Ribbon flipped bearish: {state_5min}"

            if entry_direction == 'SHORT' and state_5min in ['all_green', 'mixed_green']:
                return True, 'ribbon_flip', f"Ribbon flipped bullish: {state_5min}"

        # No exit signal
        return False, None, f"Position held (P&L: {pnl_pct*100:.2f}%, Hold: {hold_time_minutes:.1f}min)"

    def get_trade_decision(
        self,
        indicators_5min: dict,
        indicators_15min: dict,
        current_price: float,
        ribbon_transition_time: Optional[datetime] = None,
        current_position: Optional[dict] = None
    ) -> dict:
        """
        Main function: Get trading decision based on current rules

        Args:
            indicators_5min: 5-minute timeframe indicators
            indicators_15min: 15-minute timeframe indicators
            current_price: Current asset price
            ribbon_transition_time: When ribbon last flipped (optional)
            current_position: Current position details (optional) with keys:
                - direction: 'LONG' or 'SHORT'
                - entry_price: float
                - entry_time: datetime

        Returns:
            Decision dictionary with action, direction, confidence, reasoning
        """

        decision = {
            'timestamp': datetime.now().isoformat(),
            'action': 'HOLD',
            'direction': None,
            'confidence': 0.0,
            'reasoning': '',
            'entry_recommended': False,
            'exit_recommended': False,
            'current_price': current_price
        }

        # If in position, check exit first
        if current_position:
            should_exit, exit_reason, reasoning = self.check_exit_signal(
                indicators_5min,
                indicators_15min,
                current_position['direction'],
                current_position['entry_price'],
                current_price,
                current_position['entry_time']
            )

            if should_exit:
                decision['action'] = 'EXIT'
                decision['direction'] = current_position['direction']
                decision['exit_recommended'] = True
                decision['exit_reason'] = exit_reason
                decision['reasoning'] = reasoning
                return decision
            else:
                decision['reasoning'] = reasoning
                return decision

        # Not in position - check for entry
        should_enter, direction, confidence, reasoning = self.check_entry_signal(
            indicators_5min,
            indicators_15min,
            current_price,
            ribbon_transition_time
        )

        if should_enter:
            decision['action'] = 'ENTER'
            decision['direction'] = direction
            decision['confidence'] = confidence
            decision['entry_recommended'] = True
            decision['reasoning'] = reasoning

            # Calculate entry levels
            if direction == 'LONG':
                decision['entry_price'] = current_price
                decision['stop_loss'] = current_price * (1 - self.rules['exit_rules']['stop_loss_pct'])
                decision['take_profit'] = current_price * (1 + self.rules['exit_rules']['profit_target_pct'])
            else:  # SHORT
                decision['entry_price'] = current_price
                decision['stop_loss'] = current_price * (1 + self.rules['exit_rules']['stop_loss_pct'])
                decision['take_profit'] = current_price * (1 - self.rules['exit_rules']['profit_target_pct'])

        else:
            decision['reasoning'] = reasoning

        return decision

    # ========================================================================
    # COMPATIBILITY METHODS for DualTimeframeBot
    # These make RuleBasedTrader work as drop-in replacement for ClaudeTrader
    # ========================================================================

    def make_trading_decision(self, data_5min: dict, data_15min: dict, current_price: float = None):
        """
        Compatibility method for DualTimeframeBot
        Matches ClaudeTrader.make_trading_decision() interface

        Returns: (direction, entry_recommended, confidence, reasoning, targets)
        """
        # Extract indicators from data structures
        indicators_5min = data_5min.get('indicators', {})
        indicators_15min = data_15min.get('indicators', {})

        # Get current price from data if not provided
        if current_price is None:
            current_price = data_5min.get('price', 0)

        # Get decision from our rule-based system
        decision = self.get_trade_decision(
            indicators_5min=indicators_5min,
            indicators_15min=indicators_15min,
            current_price=current_price
        )

        # Convert to format expected by DualTimeframeBot
        direction = decision.get('direction', None)
        entry_recommended = decision.get('entry_recommended', False)
        confidence = decision.get('confidence', 0.0)
        reasoning = decision.get('reasoning', '')

        # Build targets dict
        targets = {
            'entry_price': decision.get('entry_price', current_price),
            'stop_loss': decision.get('stop_loss', current_price * 0.997),
            'take_profit': decision.get('take_profit', current_price * 1.005),
            'timeframe_alignment': 'STRONG' if confidence > 0.75 else 'MODERATE' if confidence > 0.5 else 'WEAK'
        }

        return direction, entry_recommended, confidence, reasoning, targets

    def should_execute_trade(self, direction, entry_recommended, confidence, min_confidence, timeframe_alignment):
        """
        Compatibility method - decides if trade should be executed
        Matches ClaudeTrader.should_execute_trade() interface
        """
        # Execute if entry is recommended and confidence meets threshold
        return entry_recommended and confidence >= min_confidence

    def get_market_commentary(self, data_5min: dict, data_15min: dict):
        """
        Compatibility method - provides market commentary
        Returns simple text commentary based on current ribbon states
        """
        indicators_5min = data_5min.get('indicators', {})
        indicators_15min = data_15min.get('indicators', {})

        pattern_5min = self.extract_ema_pattern(indicators_5min)
        pattern_15min = self.extract_ema_pattern(indicators_15min)

        state_5min = self.determine_ribbon_state(pattern_5min)
        state_15min = self.determine_ribbon_state(pattern_15min)

        commentary = f"5min: {state_5min} ({pattern_5min['green_count']}G/{pattern_5min['red_count']}R), "
        commentary += f"15min: {state_15min} ({pattern_15min['green_count']}G/{pattern_15min['red_count']}R). "
        commentary += f"Using optimized rules from {self.rules.get('last_updated', 'unknown')}."

        return commentary

    def get_cost_summary(self):
        """
        Compatibility method - returns cost summary
        RuleBasedTrader has NO costs, but returns compatible dict
        """
        return {
            'session_cost_usd': 0.00,  # FREE!
            'total_calls': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0
        }

    def print_cost_summary(self):
        """
        Compatibility method - prints cost summary
        """
        print("\n💰 API COSTS: $0.00 (0 calls) - Rule-based trading is FREE! ✅")


def main():
    """Test the rule-based trader"""
    trader = RuleBasedTrader()

    # Mock indicators for testing
    indicators_5min = {
        'MMA5': {'value': 3875.0, 'color': 'green', 'intensity': 'light'},
        'MMA10': {'value': 3874.5, 'color': 'green', 'intensity': 'light'},
        'MMA15': {'value': 3874.0, 'color': 'green', 'intensity': 'light'},
        'MMA20': {'value': 3873.5, 'color': 'green', 'intensity': 'normal'},
        # ... more EMAs
    }

    indicators_15min = {
        'MMA5': {'value': 3876.0, 'color': 'green', 'intensity': 'light'},
        'MMA10': {'value': 3875.5, 'color': 'green', 'intensity': 'light'},
        # ... more EMAs
    }

    current_price = 3875.25

    decision = trader.get_trade_decision(indicators_5min, indicators_15min, current_price)

    print("\n" + "="*60)
    print("RULE-BASED TRADING DECISION")
    print("="*60)
    print(f"Timestamp: {decision['timestamp']}")
    print(f"Action: {decision['action']}")
    print(f"Direction: {decision['direction']}")
    print(f"Confidence: {decision['confidence']:.2f}")
    print(f"Entry Recommended: {decision['entry_recommended']}")
    print(f"Reasoning: {decision['reasoning']}")
    print("="*60)


if __name__ == '__main__':
    main()
