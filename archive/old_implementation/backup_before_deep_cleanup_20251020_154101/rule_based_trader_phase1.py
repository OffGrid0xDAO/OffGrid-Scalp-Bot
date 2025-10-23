"""
Rule-Based Trader - Phase 1 Enhancement
Implements tiered entry/exit system for trend holding
NO Claude API calls - runs fast and free between optimization cycles
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


class RuleBasedTraderPhase1:
    """Enhanced rule-based trader with tiered entries and dynamic exits"""

    def __init__(self, rules_path: str = 'trading_rules_phase1.json'):
        self.rules_path = rules_path
        self.rules = self.load_rules()
        self.last_rules_reload = datetime.now()

        # Track ribbon state history for stability calculation
        self.ribbon_state_history_5min = []
        self.ribbon_state_history_15min = []

        print(f"⚡ Rule-Based Trader Phase 1 initialized")
        print(f"📋 Rules version: {self.rules.get('version', 'unknown')}")
        print(f"🔥 Phase: Trend Holding Enhancement")

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
                else:
                    pattern['dark_green_count'] += 1
            elif color == 'red':
                pattern['red_count'] += 1
                if intensity == 'light':
                    pattern['light_red_count'] += 1
                else:
                    pattern['dark_red_count'] += 1

        # Calculate percentages
        if pattern['total_emas'] > 0:
            pattern['green_pct'] = pattern['green_count'] / pattern['total_emas']
            pattern['red_pct'] = pattern['red_count'] / pattern['total_emas']
        else:
            pattern['green_pct'] = 0
            pattern['red_pct'] = 0

        return pattern

    def determine_ribbon_state(self, pattern: dict) -> str:
        """
        Determine enhanced ribbon state with granular classification
        Returns: all_green, strong_green, weak_green, mixed, weak_red, strong_red, all_red
        """
        thresholds = self.rules.get('ribbon_state_thresholds', {})

        green_pct = pattern['green_pct']
        red_pct = pattern['red_pct']

        # GREEN states
        if green_pct >= thresholds.get('all_green', 0.92):
            return 'all_green'
        elif green_pct >= thresholds.get('strong_green', 0.75):
            return 'strong_green'
        elif green_pct >= thresholds.get('weak_green', 0.50):
            return 'weak_green'

        # RED states
        elif red_pct >= thresholds.get('all_red', 0.92):
            return 'all_red'
        elif red_pct >= thresholds.get('strong_red', 0.75):
            return 'strong_red'
        elif red_pct >= thresholds.get('weak_red', 0.50):
            return 'weak_red'

        # MIXED state
        else:
            return 'mixed'

    def classify_entry_tier(self, state_5min: str, pattern_5min: dict,
                           state_15min: str, pattern_15min: dict,
                           ribbon_transition_time: Optional[datetime]) -> Tuple[Optional[int], str, str]:
        """
        Classify entry into tier (1=strong, 2=moderate, 3=scalp, None=no entry)
        Returns: (tier_number, direction, reasoning)
        """

        entry_tiers = self.rules['entry_rules']['entry_tiers']

        # Calculate ribbon stability
        stability_minutes = 0
        if ribbon_transition_time:
            stability_minutes = (datetime.now() - ribbon_transition_time).total_seconds() / 60

        # Try Tier 1: Strong Trend
        tier_1 = entry_tiers['tier_1_strong_trend']
        if tier_1['enabled']:
            # Check LONG
            if (state_5min in tier_1['ribbon_states_long'] and
                pattern_5min['light_green_count'] >= tier_1['min_light_emas'] and
                stability_minutes >= tier_1['min_ribbon_stability_minutes']):

                reasoning = f"TIER 1 LONG: {state_5min} with {pattern_5min['light_green_count']} light green EMAs"
                return 1, 'LONG', reasoning

            # Check SHORT
            if (state_5min in tier_1['ribbon_states_short'] and
                pattern_5min['light_red_count'] >= tier_1['min_light_emas'] and
                stability_minutes >= tier_1['min_ribbon_stability_minutes']):

                reasoning = f"TIER 1 SHORT: {state_5min} with {pattern_5min['light_red_count']} light red EMAs"
                return 1, 'SHORT', reasoning

        # Try Tier 2: Moderate Trend
        tier_2 = entry_tiers['tier_2_moderate_trend']
        if tier_2['enabled']:
            # Check LONG
            if (state_5min in tier_2['ribbon_states_long'] and
                pattern_5min['light_green_count'] >= tier_2['min_light_emas'] and
                stability_minutes >= tier_2['min_ribbon_stability_minutes']):

                reasoning = f"TIER 2 LONG: {state_5min} with {pattern_5min['light_green_count']} light green EMAs"
                return 2, 'LONG', reasoning

            # Check SHORT
            if (state_5min in tier_2['ribbon_states_short'] and
                pattern_5min['light_red_count'] >= tier_2['min_light_emas'] and
                stability_minutes >= tier_2['min_ribbon_stability_minutes']):

                reasoning = f"TIER 2 SHORT: {state_5min} with {pattern_5min['light_red_count']} light red EMAs"
                return 2, 'SHORT', reasoning

        # Try Tier 3: Quick Scalp (usually disabled)
        tier_3 = entry_tiers['tier_3_quick_scalp']
        if tier_3['enabled']:
            # Check LONG
            if (state_5min in tier_3['ribbon_states_long'] and
                pattern_5min['light_green_count'] >= tier_3['min_light_emas']):

                reasoning = f"TIER 3 LONG: {state_5min} with {pattern_5min['light_green_count']} light green EMAs"
                return 3, 'LONG', reasoning

            # Check SHORT
            if (state_5min in tier_3['ribbon_states_short'] and
                pattern_5min['light_red_count'] >= tier_3['min_light_emas']):

                reasoning = f"TIER 3 SHORT: {state_5min} with {pattern_5min['light_red_count']} light red EMAs"
                return 3, 'SHORT', reasoning

        # No tier matched
        return None, None, f"No tier matched: 5min={state_5min}, light_green={pattern_5min['light_green_count']}, light_red={pattern_5min['light_red_count']}"

    def check_entry_signal(self,
                          indicators_5min: dict,
                          indicators_15min: dict,
                          current_price: float,
                          ribbon_transition_time: Optional[datetime] = None) -> Tuple[bool, str, float, str, Optional[int]]:
        """
        Check if current conditions meet entry criteria

        Returns:
            (should_enter, direction, confidence, reasoning, entry_tier)
        """

        # Reload rules if updated
        self.reload_rules_if_updated()

        # Extract patterns
        pattern_5min = self.extract_ema_pattern(indicators_5min)
        pattern_15min = self.extract_ema_pattern(indicators_15min)

        # Determine ribbon states
        state_5min = self.determine_ribbon_state(pattern_5min)
        state_15min = self.determine_ribbon_state(pattern_15min)

        # Classify entry tier
        tier, direction, reasoning = self.classify_entry_tier(
            state_5min, pattern_5min,
            state_15min, pattern_15min,
            ribbon_transition_time
        )

        if tier is None:
            return False, None, 0.0, reasoning, None

        # Get tier config
        tier_key = f"tier_{tier}_{['strong_trend', 'moderate_trend', 'quick_scalp'][tier-1]}"
        tier_config = self.rules['entry_rules']['entry_tiers'][tier_key]

        # Base confidence from tier
        confidence = tier_config['entry_confidence_base']

        # Add 15min alignment bonus
        if direction == 'LONG' and 'green' in state_15min:
            confidence += 0.10
            reasoning += f" | 15min aligned: {state_15min}"
        elif direction == 'SHORT' and 'red' in state_15min:
            confidence += 0.10
            reasoning += f" | 15min aligned: {state_15min}"
        else:
            reasoning += f" | 15min: {state_15min}"

        # Fresh transition bonus
        if ribbon_transition_time:
            minutes_ago = (datetime.now() - ribbon_transition_time).total_seconds() / 60
            if minutes_ago <= 10:
                confidence += 0.10
                reasoning += f" | Fresh ({minutes_ago:.1f}min ago)"

        return True, direction, confidence, reasoning, tier

    def check_exit_signal(self,
                         indicators_5min: dict,
                         indicators_15min: dict,
                         entry_direction: str,
                         entry_price: float,
                         current_price: float,
                         entry_time: datetime,
                         entry_tier: int) -> Tuple[bool, str, str]:
        """
        Check if current conditions meet exit criteria based on entry tier

        Returns:
            (should_exit, exit_reason, reasoning)
        """

        # Reload rules if updated
        self.reload_rules_if_updated()

        # Extract patterns
        pattern_5min = self.extract_ema_pattern(indicators_5min)

        # Determine ribbon state
        state_5min = self.determine_ribbon_state(pattern_5min)

        # Get tier-specific exit rules
        tier_keys = {
            1: 'tier_1_strong_trend',
            2: 'tier_2_moderate_trend',
            3: 'tier_3_quick_scalp'
        }
        tier_key = tier_keys.get(entry_tier, 'tier_2_moderate_trend')
        exit_rules = self.rules['exit_rules'][tier_key]

        # Calculate P&L
        if entry_direction == 'LONG':
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # SHORT
            pnl_pct = (entry_price - current_price) / entry_price

        # Time in position
        hold_time_minutes = (datetime.now() - entry_time).total_seconds() / 60

        # CHECK 1: Minimum hold time
        if hold_time_minutes < exit_rules['min_hold_minutes']:
            return False, None, f"Min hold ({exit_rules['min_hold_minutes']}min) not reached - HOLDING"

        # CHECK 2: Profit target hit
        if pnl_pct >= exit_rules['profit_target_pct']:
            return True, 'profit_target', f"Profit target reached: {pnl_pct*100:.2f}%"

        # CHECK 3: Stop loss hit
        if pnl_pct <= -exit_rules['stop_loss_pct']:
            return True, 'stop_loss', f"Stop loss triggered: {pnl_pct*100:.2f}%"

        # CHECK 4: Max hold time reached
        max_hold = self.rules['exit_rules']['max_hold_minutes']
        if hold_time_minutes >= max_hold:
            return True, 'max_hold_time', f"Max hold time reached: {hold_time_minutes:.1f} min"

        # CHECK 5: Ribbon-based exits (tier-specific logic)
        if entry_tier == 1:
            # Tier 1: Only exit on OPPOSITE STRONG state
            if entry_direction == 'LONG' and state_5min == 'all_red':
                return True, 'strong_reversal', f"Strong reversal: {state_5min}"
            elif entry_direction == 'SHORT' and state_5min == 'all_green':
                return True, 'strong_reversal', f"Strong reversal: {state_5min}"

            # Or if light EMAs drop too low
            if entry_direction == 'LONG' and pattern_5min['light_green_count'] < exit_rules.get('min_light_emas_to_hold', 8):
                return True, 'trend_weakening', f"Light green EMAs dropped to {pattern_5min['light_green_count']}"
            elif entry_direction == 'SHORT' and pattern_5min['light_red_count'] < exit_rules.get('min_light_emas_to_hold', 8):
                return True, 'trend_weakening', f"Light red EMAs dropped to {pattern_5min['light_red_count']}"

        elif entry_tier == 2:
            # Tier 2: Exit on any opposite state
            if entry_direction == 'LONG' and ('red' in state_5min or state_5min == 'mixed'):
                return True, 'ribbon_reversal', f"Ribbon reversed: {state_5min}"
            elif entry_direction == 'SHORT' and ('green' in state_5min or state_5min == 'mixed'):
                return True, 'ribbon_reversal', f"Ribbon reversed: {state_5min}"

        elif entry_tier == 3:
            # Tier 3: Exit on any ribbon flip
            if exit_rules['exit_on_ribbon_flip']:
                if entry_direction == 'LONG' and state_5min != 'weak_green':
                    return True, 'ribbon_flip', f"Ribbon flipped: {state_5min}"
                elif entry_direction == 'SHORT' and state_5min != 'weak_red':
                    return True, 'ribbon_flip', f"Ribbon flipped: {state_5min}"

        # No exit signal
        return False, None, f"HOLDING (T{entry_tier}) | P&L: {pnl_pct*100:.2f}% | Hold: {hold_time_minutes:.1f}min | State: {state_5min}"

    def get_trade_decision(self,
                          indicators_5min: dict,
                          indicators_15min: dict,
                          current_price: float,
                          ribbon_transition_time: Optional[datetime] = None,
                          current_position: Optional[dict] = None) -> dict:
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
                - entry_tier: int (1, 2, or 3)

        Returns:
            Decision dictionary with action, direction, confidence, reasoning, tier
        """

        decision = {
            'timestamp': datetime.now().isoformat(),
            'action': 'HOLD',
            'direction': None,
            'confidence': 0.0,
            'reasoning': '',
            'entry_recommended': False,
            'exit_recommended': False,
            'current_price': current_price,
            'entry_tier': None
        }

        # If in position, check exit first
        if current_position:
            should_exit, exit_reason, reasoning = self.check_exit_signal(
                indicators_5min,
                indicators_15min,
                current_position['direction'],
                current_position['entry_price'],
                current_price,
                current_position['entry_time'],
                current_position.get('entry_tier', 2)  # Default to tier 2 if not specified
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
        should_enter, direction, confidence, reasoning, tier = self.check_entry_signal(
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
            decision['entry_tier'] = tier

        return decision


if __name__ == '__main__':
    # Test the enhanced trader
    trader = RuleBasedTraderPhase1()
    print("\n✅ Phase 1 Rule-Based Trader loaded successfully")
    print(f"📊 Ribbon states: {list(trader.rules.get('ribbon_state_thresholds', {}).keys())}")
    print(f"🎯 Entry tiers enabled: ", end="")
    for tier_name, tier_config in trader.rules['entry_rules']['entry_tiers'].items():
        if tier_config['enabled']:
            print(f"{tier_name} ", end="")
    print()
