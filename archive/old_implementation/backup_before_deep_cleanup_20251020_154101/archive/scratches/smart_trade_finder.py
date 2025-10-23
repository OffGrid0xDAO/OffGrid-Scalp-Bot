#!/usr/bin/env python3
"""
Smart Trade Finder - Backtests EMA Ribbon Strategy
Finds actual profitable entry/exit points minute-by-minute
"""

import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class Trade:
    """Represents a complete trade"""
    entry_time: str
    entry_price: float
    entry_ribbon_5min: str
    entry_ribbon_15min: str
    exit_time: str = None
    exit_price: float = None
    exit_ribbon_5min: str = None
    exit_ribbon_15min: str = None
    direction: str = None  # LONG or SHORT
    hold_minutes: int = 0
    pnl_dollars: float = 0.0
    pnl_percent: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    exit_reason: str = None

    def to_dict(self):
        return asdict(self)


class SmartTradeFinder:
    """
    Backtests EMA ribbon strategy to find actual profitable trades
    """

    def __init__(self,
                 profit_target_pct: float = 0.3,  # 0.3% profit target
                 stop_loss_pct: float = 0.15,     # 0.15% stop loss
                 max_hold_minutes: int = 45,      # Max 45 min hold
                 min_trade_spacing_minutes: int = 20):  # Min 20 min between trades
        """
        Initialize trade finder with strategy parameters

        Args:
            profit_target_pct: Profit target percentage
            stop_loss_pct: Stop loss percentage
            max_hold_minutes: Maximum hold time in minutes
            min_trade_spacing_minutes: Minimum time between trades
        """
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_hold_minutes = max_hold_minutes
        self.min_trade_spacing_minutes = min_trade_spacing_minutes

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

    def get_15min_ribbon_state(self, timestamp: str, candles_15min: List[Dict]) -> str:
        """Get 15min ribbon state for a given timestamp"""
        # Find the 15min candle that contains this timestamp
        target_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        for candle in candles_15min:
            candle_time = datetime.fromisoformat(candle['timestamp'].replace('Z', '+00:00'))
            # Check if timestamp falls within this 15min candle (within 15 min window)
            if abs((target_time - candle_time).total_seconds()) < 900:  # 15 min = 900 sec
                return candle.get('ribbon_state_close', 'unknown')

        return 'unknown'

    def is_bullish_entry(self, candle: Dict, prev_candle: Dict = None, ribbon_15min: str = None) -> bool:
        """
        Check if current candle is a bullish entry signal

        Strategy: Enter LONG when:
        - 5min ribbon flips to all_green OR is all_green
        - 15min ribbon is also all_green or mixed_green (multi-timeframe confirmation)
        - Price closes above key EMAs (MMA5, MMA10)
        - Strong bullish candle (close > open)
        """
        ribbon_state_5min = candle.get('ribbon_state_close', '')

        # Must have all_green ribbon on 5min
        if ribbon_state_5min != 'all_green':
            return False

        # Multi-timeframe confirmation: 15min should be bullish or neutral
        if ribbon_15min:
            if ribbon_15min not in ['all_green', 'mixed_green', 'mixed']:
                return False  # Don't enter long if 15min is bearish

        # Check if this is a fresh flip (previous was not all_green)
        if prev_candle:
            prev_ribbon = prev_candle.get('ribbon_state_close', '')
            is_flip = prev_ribbon != 'all_green'
        else:
            is_flip = True

        # Bullish candle
        is_bullish_candle = candle['price_close'] > candle['price_open']

        # Price above MMA5
        mma5_close = float(candle.get('MMA5_close', 0))
        price_above_mma5 = candle['price_close'] > mma5_close if mma5_close > 0 else False

        # Strong signal if flip + bullish candle + above MMA5
        return (is_flip or is_bullish_candle) and price_above_mma5

    def is_bearish_entry(self, candle: Dict, prev_candle: Dict = None, ribbon_15min: str = None) -> bool:
        """
        Check if current candle is a bearish entry signal

        Strategy: Enter SHORT when:
        - 5min ribbon flips to all_red OR is all_red
        - 15min ribbon is also all_red or mixed_red (multi-timeframe confirmation)
        - Price closes below key EMAs (MMA5, MMA10)
        - Strong bearish candle (close < open)
        """
        ribbon_state_5min = candle.get('ribbon_state_close', '')

        # Must have all_red ribbon on 5min
        if ribbon_state_5min != 'all_red':
            return False

        # Multi-timeframe confirmation: 15min should be bearish or neutral
        if ribbon_15min:
            if ribbon_15min not in ['all_red', 'mixed_red', 'mixed']:
                return False  # Don't enter short if 15min is bullish

        # Check if this is a fresh flip
        if prev_candle:
            prev_ribbon = prev_candle.get('ribbon_state_close', '')
            is_flip = prev_ribbon != 'all_red'
        else:
            is_flip = True

        # Bearish candle
        is_bearish_candle = candle['price_close'] < candle['price_open']

        # Price below MMA5
        mma5_close = float(candle.get('MMA5_close', 0))
        price_below_mma5 = candle['price_close'] < mma5_close if mma5_close > 0 else False

        return (is_flip or is_bearish_candle) and price_below_mma5

    def should_exit_long(self, trade: Trade, candle: Dict, minutes_held: int) -> Tuple[bool, str]:
        """
        Check if LONG trade should exit

        Exit conditions:
        - Take profit hit
        - Stop loss hit
        - Max hold time reached
        - Ribbon flips to all_red (reversal)
        """
        current_price = candle['price_close']
        pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100

        # Take profit
        if pnl_pct >= self.profit_target_pct:
            return True, "PROFIT_TARGET"

        # Stop loss
        if pnl_pct <= -self.stop_loss_pct:
            return True, "STOP_LOSS"

        # Max hold time
        if minutes_held >= self.max_hold_minutes:
            return True, "MAX_HOLD_TIME"

        # Ribbon reversal
        if candle.get('ribbon_state_close') == 'all_red':
            return True, "RIBBON_REVERSAL"

        return False, None

    def should_exit_short(self, trade: Trade, candle: Dict, minutes_held: int) -> Tuple[bool, str]:
        """
        Check if SHORT trade should exit

        Exit conditions:
        - Take profit hit
        - Stop loss hit
        - Max hold time reached
        - Ribbon flips to all_green (reversal)
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
        if minutes_held >= self.max_hold_minutes:
            return True, "MAX_HOLD_TIME"

        # Ribbon reversal
        if candle.get('ribbon_state_close') == 'all_green':
            return True, "RIBBON_REVERSAL"

        return False, None

    def backtest_strategy(self, candles_5min: List[Dict], candles_15min: List[Dict]) -> List[Trade]:
        """
        Run backtest to find all profitable trades

        Returns:
            List of completed trades
        """
        if not candles_5min:
            print("❌ No 5min candles to backtest")
            return []

        trades = []
        active_trade = None
        last_trade_time = None

        print(f"\n🔍 Backtesting {len(candles_5min)} candles...")
        print(f"Strategy: Profit={self.profit_target_pct}%, SL={self.stop_loss_pct}%, MaxHold={self.max_hold_minutes}min\n")

        for i, candle in enumerate(candles_5min):
            candle_time = datetime.fromisoformat(candle['timestamp'].replace('Z', '+00:00'))
            prev_candle = candles_5min[i-1] if i > 0 else None

            # If we have an active trade, check for exit
            if active_trade:
                minutes_held = i - active_trade.entry_index
                should_exit = False
                exit_reason = None

                if active_trade.direction == "LONG":
                    should_exit, exit_reason = self.should_exit_long(active_trade, candle, minutes_held)
                elif active_trade.direction == "SHORT":
                    should_exit, exit_reason = self.should_exit_short(active_trade, candle, minutes_held)

                # Track max profit/loss during trade
                current_price = candle['price_close']
                if active_trade.direction == "LONG":
                    profit = current_price - active_trade.entry_price
                else:  # SHORT
                    profit = active_trade.entry_price - current_price

                active_trade.max_profit = max(active_trade.max_profit, profit)
                active_trade.max_loss = min(active_trade.max_loss, profit)

                if should_exit:
                    # Close the trade
                    active_trade.exit_time = candle['timestamp']
                    active_trade.exit_price = candle['price_close']
                    active_trade.exit_ribbon_5min = candle.get('ribbon_state_close', 'unknown')
                    active_trade.exit_ribbon_15min = self.get_15min_ribbon_state(candle['timestamp'], candles_15min)
                    active_trade.hold_minutes = minutes_held
                    active_trade.exit_reason = exit_reason

                    # Calculate final P&L
                    if active_trade.direction == "LONG":
                        active_trade.pnl_dollars = active_trade.exit_price - active_trade.entry_price
                    else:  # SHORT
                        active_trade.pnl_dollars = active_trade.entry_price - active_trade.exit_price

                    active_trade.pnl_percent = (active_trade.pnl_dollars / active_trade.entry_price) * 100

                    trades.append(active_trade)
                    last_trade_time = candle_time
                    active_trade = None

                    print(f"{'✅' if trades[-1].pnl_dollars > 0 else '❌'} {trades[-1].direction} | Entry: ${trades[-1].entry_price:.2f} → Exit: ${trades[-1].exit_price:.2f} | "
                          f"P&L: ${trades[-1].pnl_dollars:.2f} ({trades[-1].pnl_percent:.3f}%) | {trades[-1].exit_reason}")

                continue

            # No active trade - look for entry signal
            # Check if enough time has passed since last trade
            if last_trade_time:
                time_since_last = (candle_time - last_trade_time).total_seconds() / 60
                if time_since_last < self.min_trade_spacing_minutes:
                    continue

            # Get 15min ribbon state for multi-timeframe confirmation
            ribbon_15min = self.get_15min_ribbon_state(candle['timestamp'], candles_15min)

            # Check for bullish entry
            if self.is_bullish_entry(candle, prev_candle, ribbon_15min):
                active_trade = Trade(
                    entry_time=candle['timestamp'],
                    entry_price=candle['price_close'],
                    entry_ribbon_5min=candle.get('ribbon_state_close', 'unknown'),
                    entry_ribbon_15min=ribbon_15min,
                    direction="LONG"
                )
                active_trade.entry_index = i  # Track index for calculating hold time
                print(f"📈 LONG ENTRY at ${candle['price_close']:.2f} | 5m:{candle.get('ribbon_state_close')} 15m:{ribbon_15min} | {candle['timestamp']}")

            # Check for bearish entry
            elif self.is_bearish_entry(candle, prev_candle, ribbon_15min):
                active_trade = Trade(
                    entry_time=candle['timestamp'],
                    entry_price=candle['price_close'],
                    entry_ribbon_5min=candle.get('ribbon_state_close', 'unknown'),
                    entry_ribbon_15min=ribbon_15min,
                    direction="SHORT"
                )
                active_trade.entry_index = i
                print(f"📉 SHORT ENTRY at ${candle['price_close']:.2f} | 5m:{candle.get('ribbon_state_close')} 15m:{ribbon_15min} | {candle['timestamp']}")

        return trades

    def analyze_results(self, trades: List[Trade]) -> Dict:
        """Analyze backtest results and generate statistics"""
        if not trades:
            return {
                "total_trades": 0,
                "profitable_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl_dollars": 0.0,
                "avg_profit_per_trade": 0.0,
                "best_trade": None,
                "worst_trade": None
            }

        profitable = [t for t in trades if t.pnl_dollars > 0]
        losing = [t for t in trades if t.pnl_dollars <= 0]

        total_pnl = sum(t.pnl_dollars for t in trades)
        win_rate = (len(profitable) / len(trades)) * 100 if trades else 0

        best_trade = max(trades, key=lambda t: t.pnl_dollars)
        worst_trade = min(trades, key=lambda t: t.pnl_dollars)

        # Analyze by exit reason
        exit_reasons = {}
        for trade in trades:
            reason = trade.exit_reason or "UNKNOWN"
            if reason not in exit_reasons:
                exit_reasons[reason] = {"count": 0, "profitable": 0}
            exit_reasons[reason]["count"] += 1
            if trade.pnl_dollars > 0:
                exit_reasons[reason]["profitable"] += 1

        return {
            "total_trades": len(trades),
            "profitable_trades": len(profitable),
            "losing_trades": len(losing),
            "win_rate": win_rate,
            "total_pnl_dollars": total_pnl,
            "avg_profit_per_trade": total_pnl / len(trades),
            "avg_hold_time": sum(t.hold_minutes for t in trades) / len(trades),
            "best_trade": best_trade.to_dict(),
            "worst_trade": worst_trade.to_dict(),
            "exit_reasons": exit_reasons,
            "long_trades": len([t for t in trades if t.direction == "LONG"]),
            "short_trades": len([t for t in trades if t.direction == "SHORT"]),
        }

    def save_results(self, trades: List[Trade], analysis: Dict, output_file: str = 'smart_trades_found.json'):
        """Save all trades and analysis to JSON file"""
        output = {
            "timestamp": datetime.now().isoformat(),
            "strategy_parameters": {
                "profit_target_pct": self.profit_target_pct,
                "stop_loss_pct": self.stop_loss_pct,
                "max_hold_minutes": self.max_hold_minutes,
                "min_trade_spacing_minutes": self.min_trade_spacing_minutes
            },
            "analysis": analysis,
            "trades": [t.to_dict() for t in trades]
        }

        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n💾 Results saved to {output_file}")

    def print_summary(self, analysis: Dict):
        """Print backtest summary"""
        print("\n" + "="*80)
        print("BACKTEST RESULTS SUMMARY")
        print("="*80)
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   Total Trades: {analysis['total_trades']}")
        print(f"   Profitable: {analysis['profitable_trades']} ✅")
        print(f"   Losing: {analysis['losing_trades']} ❌")
        print(f"   Win Rate: {analysis['win_rate']:.2f}%")
        print(f"   Total P&L: ${analysis['total_pnl_dollars']:.2f}")
        print(f"   Avg P&L per Trade: ${analysis['avg_profit_per_trade']:.2f}")
        print(f"   Avg Hold Time: {analysis['avg_hold_time']:.1f} minutes")

        print(f"\n📈 TRADE BREAKDOWN:")
        print(f"   Long Trades: {analysis['long_trades']}")
        print(f"   Short Trades: {analysis['short_trades']}")

        print(f"\n🎯 EXIT REASONS:")
        for reason, stats in analysis['exit_reasons'].items():
            win_rate = (stats['profitable'] / stats['count'] * 100) if stats['count'] > 0 else 0
            print(f"   {reason}: {stats['count']} trades ({stats['profitable']} profitable, {win_rate:.1f}% win rate)")

        if analysis['best_trade']:
            best = analysis['best_trade']
            print(f"\n🏆 BEST TRADE:")
            print(f"   {best['direction']} | ${best['entry_price']:.2f} → ${best['exit_price']:.2f}")
            print(f"   P&L: ${best['pnl_dollars']:.2f} ({best['pnl_percent']:.3f}%)")
            print(f"   Time: {best['entry_time']} → {best['exit_time']}")

        if analysis['worst_trade']:
            worst = analysis['worst_trade']
            print(f"\n💔 WORST TRADE:")
            print(f"   {worst['direction']} | ${worst['entry_price']:.2f} → ${worst['exit_price']:.2f}")
            print(f"   P&L: ${worst['pnl_dollars']:.2f} ({worst['pnl_percent']:.3f}%)")
            print(f"   Time: {worst['entry_time']} → {worst['exit_time']}")

        print("\n" + "="*80)


def main():
    """Main execution"""
    print("🚀 Smart Trade Finder - EMA Ribbon Strategy Backtester")
    print("="*80)

    # Initialize finder
    finder = SmartTradeFinder(
        profit_target_pct=0.3,      # 0.3% profit target
        stop_loss_pct=0.15,         # 0.15% stop loss
        max_hold_minutes=45,        # Max 45 min hold
        min_trade_spacing_minutes=20  # Min 20 min between trades
    )

    # Load data
    print("\n📂 Loading candlestick data...")
    candles_5min = finder.load_candlestick_data('candlesticks_5min.csv')
    candles_15min = finder.load_candlestick_data('candlesticks_15min.csv')

    if not candles_5min:
        print("❌ No 5min data found. Cannot proceed.")
        return

    # Run backtest
    trades = finder.backtest_strategy(candles_5min, candles_15min)

    # Analyze results
    analysis = finder.analyze_results(trades)

    # Print summary
    finder.print_summary(analysis)

    # Save results
    finder.save_results(trades, analysis)

    print(f"\n✅ Backtest complete! Found {len(trades)} trades")


if __name__ == "__main__":
    main()
