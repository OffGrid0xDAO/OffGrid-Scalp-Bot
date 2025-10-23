#!/usr/bin/env python3
"""
TRUE SCALPING Strategy - 1min + 3min Timeframes
Designed for rapid entries/exits with tight risk management

Key Differences from 5min/15min:
- Much faster signals (1-3 min holds)
- Tighter stops (0.05-0.1%)
- Smaller profit targets (0.15-0.25%)
- More trades per session
- Requires both timeframes to STRONGLY align
"""

import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class ScalpTrade:
    """Represents a scalp trade"""
    entry_time: str
    entry_price: float
    entry_ribbon_1min: str
    entry_ribbon_3min: str
    exit_time: str = None
    exit_price: float = None
    exit_ribbon_1min: str = None
    exit_ribbon_3min: str = None
    direction: str = None  # LONG or SHORT
    hold_seconds: int = 0
    pnl_dollars: float = 0.0
    pnl_percent: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    exit_reason: str = None

    def to_dict(self):
        return asdict(self)


class ScalpingStrategy:
    """
    TRUE Scalping Strategy with 1min + 3min timeframes
    """

    def __init__(self,
                 profit_target_pct: float = 0.2,    # 0.2% profit target (smaller!)
                 stop_loss_pct: float = 0.08,       # 0.08% stop loss (tighter!)
                 max_hold_seconds: int = 300,       # Max 5 min hold (300 sec)
                 min_trade_spacing_seconds: int = 60):  # Min 1 min between trades
        """
        Initialize scalping strategy

        Args:
            profit_target_pct: Profit target percentage (smaller for scalping)
            stop_loss_pct: Stop loss percentage (tighter for scalping)
            max_hold_seconds: Maximum hold time in seconds
            min_trade_spacing_seconds: Minimum time between trades in seconds
        """
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_hold_seconds = max_hold_seconds
        self.min_trade_spacing_seconds = min_trade_spacing_seconds

    def load_candlestick_data(self, csv_path: str) -> List[Dict]:
        """Load candlestick CSV data"""
        candles = []
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert numeric fields
                    row['price_open'] = float(row['price_open'])
                    row['price_high'] = float(row['price_high'])
                    row['price_low'] = float(row['price_low'])
                    row['price_close'] = float(row['price_close'])
                    candles.append(row)
            print(f"✅ Loaded {len(candles)} candles from {csv_path}")
            return candles
        except Exception as e:
            print(f"❌ Error loading {csv_path}: {e}")
            return []

    def get_3min_ribbon_state(self, timestamp: str, candles_3min: List[Dict]) -> str:
        """Get 3min ribbon state for a given timestamp"""
        target_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        for candle in candles_3min:
            candle_time = datetime.fromisoformat(candle['timestamp'].replace('Z', '+00:00'))
            # Check if timestamp falls within this 3min candle (within 3 min window)
            if abs((target_time - candle_time).total_seconds()) < 180:  # 3 min = 180 sec
                return candle.get('ribbon_state_close', 'unknown')

        return 'unknown'

    def is_strong_bullish_entry(self, candle_1min: Dict, candle_3min_state: str,
                                 prev_candle_1min: Dict = None) -> bool:
        """
        SCALPING bullish entry - requires VERY strong alignment

        Rules:
        - 1min ribbon MUST be all_green
        - 3min ribbon MUST be all_green or mixed_green
        - Price MUST be above MMA5 (fastest EMA)
        - Strong bullish momentum (close > open)
        - Preferably a FRESH flip (within last 2-3 candles)
        """
        ribbon_1min = candle_1min.get('ribbon_state_close', '')

        # MUST have all_green on 1min
        if ribbon_1min != 'all_green':
            return False

        # 3min must be bullish or neutral
        if candle_3min_state not in ['all_green', 'mixed_green', 'mixed']:
            return False

        # Price above MMA5 (strong bullish position)
        mma5_close = float(candle_1min.get('MMA5_close', 0))
        if mma5_close <= 0 or candle_1min['price_close'] <= mma5_close:
            return False

        # Strong bullish candle
        is_bullish = candle_1min['price_close'] > candle_1min['price_open']

        # Check for fresh flip (optional but preferred)
        is_fresh = True
        if prev_candle_1min:
            prev_ribbon = prev_candle_1min.get('ribbon_state_close', '')
            is_fresh = prev_ribbon != 'all_green'

        return is_bullish and (is_fresh or ribbon_1min == 'all_green')

    def is_strong_bearish_entry(self, candle_1min: Dict, candle_3min_state: str,
                                 prev_candle_1min: Dict = None) -> bool:
        """
        SCALPING bearish entry - requires VERY strong alignment

        Rules:
        - 1min ribbon MUST be all_red
        - 3min ribbon MUST be all_red or mixed_red
        - Price MUST be below MMA5 (fastest EMA)
        - Strong bearish momentum (close < open)
        """
        ribbon_1min = candle_1min.get('ribbon_state_close', '')

        # MUST have all_red on 1min
        if ribbon_1min != 'all_red':
            return False

        # 3min must be bearish or neutral
        if candle_3min_state not in ['all_red', 'mixed_red', 'mixed']:
            return False

        # Price below MMA5 (strong bearish position)
        mma5_close = float(candle_1min.get('MMA5_close', 0))
        if mma5_close <= 0 or candle_1min['price_close'] >= mma5_close:
            return False

        # Strong bearish candle
        is_bearish = candle_1min['price_close'] < candle_1min['price_open']

        # Check for fresh flip
        is_fresh = True
        if prev_candle_1min:
            prev_ribbon = prev_candle_1min.get('ribbon_state_close', '')
            is_fresh = prev_ribbon != 'all_red'

        return is_bearish and (is_fresh or ribbon_1min == 'all_red')

    def should_exit_long(self, trade: ScalpTrade, candle: Dict, hold_seconds: int) -> Tuple[bool, str]:
        """
        Check if LONG scalp should exit (TIGHTER rules)
        """
        current_price = candle['price_close']
        pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100

        # Take profit (smaller target)
        if pnl_pct >= self.profit_target_pct:
            return True, "PROFIT_TARGET"

        # Stop loss (tighter)
        if pnl_pct <= -self.stop_loss_pct:
            return True, "STOP_LOSS"

        # Max hold time (shorter)
        if hold_seconds >= self.max_hold_seconds:
            return True, "MAX_HOLD_TIME"

        # Ribbon reversal (immediate exit)
        if candle.get('ribbon_state_close') == 'all_red':
            return True, "RIBBON_REVERSAL"

        # Exit if ribbon weakens to mixed
        if candle.get('ribbon_state_close') in ['mixed_red', 'mixed']:
            if hold_seconds > 60:  # Only after 1 min
                return True, "RIBBON_WEAKENING"

        return False, None

    def should_exit_short(self, trade: ScalpTrade, candle: Dict, hold_seconds: int) -> Tuple[bool, str]:
        """
        Check if SHORT scalp should exit (TIGHTER rules)
        """
        current_price = candle['price_close']
        pnl_pct = ((trade.entry_price - current_price) / trade.entry_price) * 100

        # Take profit
        if pnl_pct >= self.profit_target_pct:
            return True, "PROFIT_TARGET"

        # Stop loss
        if pnl_pct <= -self.stop_loss_pct:
            return True, "STOP_LOSS"

        # Max hold time
        if hold_seconds >= self.max_hold_seconds:
            return True, "MAX_HOLD_TIME"

        # Ribbon reversal
        if candle.get('ribbon_state_close') == 'all_green':
            return True, "RIBBON_REVERSAL"

        # Ribbon weakening
        if candle.get('ribbon_state_close') in ['mixed_green', 'mixed']:
            if hold_seconds > 60:
                return True, "RIBBON_WEAKENING"

        return False, None

    def backtest_scalping(self, candles_1min: List[Dict], candles_3min: List[Dict]) -> List[ScalpTrade]:
        """
        Run scalping backtest on 1min + 3min data
        """
        if not candles_1min:
            print("❌ No 1min candles to backtest")
            return []

        trades = []
        active_trade = None
        last_trade_time = None

        print(f"\n🔍 Backtesting {len(candles_1min)} 1-minute candles...")
        print(f"Strategy: Profit={self.profit_target_pct}%, SL={self.stop_loss_pct}%, MaxHold={self.max_hold_seconds}sec\n")

        for i, candle in enumerate(candles_1min):
            candle_time = datetime.fromisoformat(candle['timestamp'].replace('Z', '+00:00'))
            prev_candle = candles_1min[i-1] if i > 0 else None

            # If we have an active trade, check for exit
            if active_trade:
                hold_seconds = (i - active_trade.entry_index) * 60  # Assuming 1min candles
                should_exit = False
                exit_reason = None

                if active_trade.direction == "LONG":
                    should_exit, exit_reason = self.should_exit_long(active_trade, candle, hold_seconds)
                elif active_trade.direction == "SHORT":
                    should_exit, exit_reason = self.should_exit_short(active_trade, candle, hold_seconds)

                # Track max profit/loss
                current_price = candle['price_close']
                if active_trade.direction == "LONG":
                    profit = current_price - active_trade.entry_price
                else:
                    profit = active_trade.entry_price - current_price

                active_trade.max_profit = max(active_trade.max_profit, profit)
                active_trade.max_loss = min(active_trade.max_loss, profit)

                if should_exit:
                    # Close the trade
                    active_trade.exit_time = candle['timestamp']
                    active_trade.exit_price = candle['price_close']
                    active_trade.exit_ribbon_1min = candle.get('ribbon_state_close', 'unknown')
                    active_trade.exit_ribbon_3min = self.get_3min_ribbon_state(candle['timestamp'], candles_3min)
                    active_trade.hold_seconds = hold_seconds
                    active_trade.exit_reason = exit_reason

                    # Calculate final P&L
                    if active_trade.direction == "LONG":
                        active_trade.pnl_dollars = active_trade.exit_price - active_trade.entry_price
                    else:
                        active_trade.pnl_dollars = active_trade.entry_price - active_trade.exit_price

                    active_trade.pnl_percent = (active_trade.pnl_dollars / active_trade.entry_price) * 100

                    trades.append(active_trade)
                    last_trade_time = candle_time
                    active_trade = None

                    emoji = '✅' if trades[-1].pnl_dollars > 0 else '❌'
                    print(f"{emoji} {trades[-1].direction} | ${trades[-1].entry_price:.2f} → ${trades[-1].exit_price:.2f} | "
                          f"P&L: ${trades[-1].pnl_dollars:.2f} ({trades[-1].pnl_percent:.3f}%) | {trades[-1].hold_seconds}sec | {trades[-1].exit_reason}")

                continue

            # No active trade - look for entry
            if last_trade_time:
                time_since_last = (candle_time - last_trade_time).total_seconds()
                if time_since_last < self.min_trade_spacing_seconds:
                    continue

            # Get 3min ribbon state
            ribbon_3min = self.get_3min_ribbon_state(candle['timestamp'], candles_3min)

            # Check for bullish entry
            if self.is_strong_bullish_entry(candle, ribbon_3min, prev_candle):
                active_trade = ScalpTrade(
                    entry_time=candle['timestamp'],
                    entry_price=candle['price_close'],
                    entry_ribbon_1min=candle.get('ribbon_state_close', 'unknown'),
                    entry_ribbon_3min=ribbon_3min,
                    direction="LONG"
                )
                active_trade.entry_index = i
                print(f"📈 LONG @ ${candle['price_close']:.2f} | 1m:{candle.get('ribbon_state_close')} 3m:{ribbon_3min}")

            # Check for bearish entry
            elif self.is_strong_bearish_entry(candle, ribbon_3min, prev_candle):
                active_trade = ScalpTrade(
                    entry_time=candle['timestamp'],
                    entry_price=candle['price_close'],
                    entry_ribbon_1min=candle.get('ribbon_state_close', 'unknown'),
                    entry_ribbon_3min=ribbon_3min,
                    direction="SHORT"
                )
                active_trade.entry_index = i
                print(f"📉 SHORT @ ${candle['price_close']:.2f} | 1m:{candle.get('ribbon_state_close')} 3m:{ribbon_3min}")

        return trades

    def analyze_results(self, trades: List[ScalpTrade]) -> Dict:
        """Analyze scalping results"""
        if not trades:
            return {"total_trades": 0}

        profitable = [t for t in trades if t.pnl_dollars > 0]
        losing = [t for t in trades if t.pnl_dollars <= 0]

        total_pnl = sum(t.pnl_dollars for t in trades)
        win_rate = (len(profitable) / len(trades)) * 100

        return {
            "total_trades": len(trades),
            "profitable_trades": len(profitable),
            "losing_trades": len(losing),
            "win_rate": win_rate,
            "total_pnl_dollars": total_pnl,
            "avg_profit_per_trade": total_pnl / len(trades),
            "avg_hold_time_seconds": sum(t.hold_seconds for t in trades) / len(trades),
            "best_trade": max(trades, key=lambda t: t.pnl_dollars).to_dict() if trades else None,
            "worst_trade": min(trades, key=lambda t: t.pnl_dollars).to_dict() if trades else None,
        }


def main():
    """Main execution"""
    print("🚀 TRUE SCALPING Strategy - 1min + 3min Timeframes")
    print("="*80)

    # NOTE: You'll need to generate 1min and 3min candlestick CSVs first
    # This is just a template showing the improved strategy

    print("\n⚠️  To use this strategy, you need:")
    print("   1. Generate candlesticks_1min.csv from your data")
    print("   2. Generate candlesticks_3min.csv from your data")
    print("   3. Run this script")
    print("\n💡 The key improvements:")
    print("   - Much faster timeframes (1min + 3min vs 5min + 15min)")
    print("   - Tighter stops (0.08% vs 0.15%)")
    print("   - Smaller profit targets (0.2% vs 0.3%)")
    print("   - Faster exits (max 5min vs 45min)")
    print("   - More trades per session")


if __name__ == "__main__":
    main()
