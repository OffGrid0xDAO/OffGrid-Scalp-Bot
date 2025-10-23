#!/usr/bin/env python3
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
        """Initialize exit manager (ITERATION 10 - PROVEN WINNER +2.19%)"""
        self.take_profit_pct = 5.0  # 5% TP (prevents overtrading)
        self.stop_loss_pct = 0.75   # 0.75% SL (tight)
        self.trailing_stop_pct = 1.5  # 1.5% trailing
        self.max_hold_hours = 48  # 48h max
        self.profit_lock_threshold = 1.5  # Lock profit if peaked +1.5%

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

        # Exit 2.5: PROFIT LOCK (NEW!) - Don't let +1.5% winners become losers
        if peak_profit_pct >= self.profit_lock_threshold and profit_pct <= 0:
            result['should_exit'] = True
            result['exit_reason'] = f'Profit lock: peaked at +{peak_profit_pct:.2f}%, now {profit_pct:.2f}%'
            return result

        # Exit 3: Dynamic trailing stop (WIDER - let winners run)
        if peak_profit_pct > 1.0:  # If we've been in profit (raised threshold)
            # Dynamic trailing: wider for larger profits
            if peak_profit_pct < 2.0:
                trailing_width = 1.5  # Wide even for small profits
            elif peak_profit_pct < 4.0:
                trailing_width = 2.0  # Wider for medium profits
            else:
                trailing_width = 2.5  # Very wide for large profits

            if profit_pct < peak_profit_pct - trailing_width:
                result['should_exit'] = True
                result['exit_reason'] = f'Trailing stop: profit {profit_pct:.2f}% < peak {peak_profit_pct:.2f}% (trail={trailing_width:.1f}%)'
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
