#!/usr/bin/env python3
"""
Exit Manager - ML-LEARNED from User's Actual Exits
Based on analysis of 22 user trades with 90.9% WR and +4.86% return

Key Learnings:
- TP at 2.51% (median of 17 TP exits)
- SL at 0.60% (median of 2 losses)
- Trailing width: 0.92% (median giveback on trailing wins)
- Profit lock: 0.69% (prevent reversals like Trade #8, #18)
"""

import pandas as pd
from typing import Dict, Optional


class ExitManager:
    """Exit Manager with ML-learned parameters from user's actual trades"""

    def __init__(self):
        """Initialize with ML-discovered optimal parameters"""
        # LEARNED FROM USER DATA
        self.take_profit_pct = 2.5  # User's median TP (2.51% rounded)
        self.stop_loss_pct = 0.6    # User's median loss (exact!)
        self.trailing_stop_width = 0.9  # User's median giveback (0.92% rounded)
        self.profit_lock_threshold = 0.7  # User locked at 0.69% (rounded)
        self.max_hold_hours = 48

    def check_exit(self, entry_price: float, entry_time: pd.Timestamp,
                   current_price: float, current_time: pd.Timestamp,
                   direction: str, peak_profit_pct: float = 0.0) -> Dict:
        """
        Check if trade should exit using ML-learned rules

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

        # Exit 1: Take profit (USER: 77% exits at TP, median 2.51%)
        if profit_pct >= self.take_profit_pct:
            result['should_exit'] = True
            result['exit_reason'] = f'Take profit at +{profit_pct:.2f}%'
            return result

        # Exit 2: Stop loss (USER: median -0.60%, max -1.13%)
        if profit_pct <= -self.stop_loss_pct:
            result['should_exit'] = True
            result['exit_reason'] = f'Stop loss at {profit_pct:.2f}%'
            return result

        # Exit 3: PROFIT LOCK (USER: locks at 0.69% peak, prevents reversals)
        # User's Trades #8 and #18 peaked at 1.4% then reversed to losses
        # Lock profit if peaked above threshold and now drops to breakeven/negative
        if peak_profit_pct >= self.profit_lock_threshold and profit_pct <= 0:
            result['should_exit'] = True
            result['exit_reason'] = f'Profit lock: peaked at +{peak_profit_pct:.2f}%, now {profit_pct:.2f}%'
            return result

        # Exit 4: Trailing stop (USER: 23% exits via trail, median giveback 0.92%)
        # User gave back 0.82-1.55% from peak (median 0.92%)
        # Only activate trailing if we've been in decent profit
        if peak_profit_pct > 0.5:  # Start trailing after +0.5%
            # Use learned trailing width
            if profit_pct < peak_profit_pct - self.trailing_stop_width:
                result['should_exit'] = True
                result['exit_reason'] = f'Trailing stop: profit {profit_pct:.2f}% < peak {peak_profit_pct:.2f}% (trail={self.trailing_stop_width:.1f}%)'
                return result

        # Exit 5: Time-based exit (fallback)
        hours_held = (current_time - entry_time).total_seconds() / 3600
        if hours_held >= self.max_hold_hours:
            result['should_exit'] = True
            result['exit_reason'] = f'Time exit after {hours_held:.1f}h at {profit_pct:.2f}%'
            return result

        return result


if __name__ == '__main__':
    """Test exit manager with user's actual trade scenarios"""
    from datetime import datetime, timedelta

    exit_mgr = ExitManager()
    print("🤖 ML-Learned Exit Manager Test")
    print("="*60)

    # Test 1: Should hit TP at 2.5%
    result = exit_mgr.check_exit(
        entry_price=4000,
        entry_time=pd.Timestamp('2025-10-15 10:00:00'),
        current_price=4100,  # +2.5%
        current_time=pd.Timestamp('2025-10-15 14:00:00'),
        direction='long'
    )
    print(f"Test 1 (TP at 2.5%): {result}")
    assert result['should_exit'] == True
    assert 'Take profit' in result['exit_reason']

    # Test 2: Should hit SL at -0.6%
    result = exit_mgr.check_exit(
        entry_price=4000,
        entry_time=pd.Timestamp('2025-10-15 10:00:00'),
        current_price=3976,  # -0.6%
        current_time=pd.Timestamp('2025-10-15 14:00:00'),
        direction='long'
    )
    print(f"Test 2 (SL at -0.6%): {result}")
    assert result['should_exit'] == True
    assert 'Stop loss' in result['exit_reason']

    # Test 3: Profit lock (peaked 1.4%, now at 0%)
    # Simulates user's Trade #8 and #18
    result = exit_mgr.check_exit(
        entry_price=4000,
        entry_time=pd.Timestamp('2025-10-15 10:00:00'),
        current_price=4000,  # Back to 0%
        current_time=pd.Timestamp('2025-10-15 14:00:00'),
        direction='long',
        peak_profit_pct=1.4  # Had peaked at 1.4%
    )
    print(f"Test 3 (Profit lock, peaked 1.4%): {result}")
    assert result['should_exit'] == True
    assert 'Profit lock' in result['exit_reason']

    # Test 4: Trailing stop (peaked 1.7%, now at 0.75%)
    # Simulates user's Trade #2
    result = exit_mgr.check_exit(
        entry_price=4000,
        entry_time=pd.Timestamp('2025-10-15 10:00:00'),
        current_price=4030,  # +0.75%
        current_time=pd.Timestamp('2025-10-15 14:00:00'),
        direction='long',
        peak_profit_pct=1.67  # Had peaked at 1.67%
    )
    print(f"Test 4 (Trail, peaked 1.67%, at 0.75%): {result}")
    assert result['should_exit'] == True
    assert 'Trailing stop' in result['exit_reason']

    print("\n✅ All tests passed! ML-learned exit manager working correctly.")
