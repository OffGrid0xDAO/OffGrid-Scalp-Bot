#!/usr/bin/env python3
"""
Calculate profit from user's 22 optimal trades

Uses same exit rules as bot backtest for fair comparison:
- Take profit: +2%
- Stop loss: -1.5%
- Trailing stop: 0.8% from peak
- Max hold: 24 hours
"""

import pandas as pd
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from strategy.exit_manager_user_pattern import ExitManager


class UserTradeAnalyzer:
    """Calculate what user's trades would have earned"""

    def __init__(self):
        """Initialize analyzer"""
        self.data_dir = Path(__file__).parent / 'trading_data'
        self.exit_manager = ExitManager()

        # Load user trades
        with open(self.data_dir / 'optimal_trades.json', 'r') as f:
            user_data = json.load(f)
        self.user_trades = user_data['optimal_entries']

        # Load historical data
        self.df = pd.read_csv(self.data_dir / 'indicators' / 'eth_1h_full.csv')
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

    def simulate_user_trades(self):
        """Simulate user's 22 trades with bot's exit rules"""
        print("\n" + "="*80)
        print("💰 CALCULATING USER'S OPTIMAL TRADE PROFITS")
        print("="*80)
        print("\nSimulating 22 trades with same exit rules as bot:")
        print("  - Take Profit: +2%")
        print("  - Stop Loss: -1.5%")
        print("  - Trailing Stop: 0.8% from peak")
        print("  - Max Hold: 24 hours")

        initial_capital = 1000.0
        capital = initial_capital
        trades = []

        for i, user_trade in enumerate(self.user_trades, 1):
            entry_time = pd.to_datetime(user_trade['timestamp'])
            exit_time = pd.to_datetime(user_trade.get('exit_timestamp')) if user_trade.get('exit_timestamp') else None
            direction = user_trade['direction']
            entry_price = user_trade['market_state']['ohlcv']['close']

            print(f"\n{'='*80}")
            print(f"Trade {i}/22: {direction.upper()} at {entry_time}")
            print(f"{'='*80}")
            print(f"Entry Price: ${entry_price:.2f}")

            # Get candles after entry
            future_candles = self.df[self.df['timestamp'] > entry_time].copy()

            if len(future_candles) == 0:
                print("⚠️  No future data, skipping...")
                continue

            # Simulate trade with exit manager
            peak_profit_pct = 0.0
            exit_found = False

            for idx, candle in future_candles.iterrows():
                current_time = candle['timestamp']
                current_price = candle['close']

                # Calculate current profit
                if direction == 'long':
                    profit_pct = (current_price - entry_price) / entry_price * 100
                else:
                    profit_pct = (entry_price - current_price) / entry_price * 100

                peak_profit_pct = max(peak_profit_pct, profit_pct)

                # Check exit conditions
                exit_result = self.exit_manager.check_exit(
                    entry_price, entry_time,
                    current_price, current_time,
                    direction, peak_profit_pct
                )

                if exit_result['should_exit']:
                    # Exit trade
                    exit_price = exit_result['exit_price']
                    final_profit_pct = exit_result['profit_pct']
                    exit_reason = exit_result['exit_reason']

                    # Calculate P&L
                    position_size = capital * 0.1  # 10% of capital
                    pnl = position_size * (final_profit_pct / 100)
                    capital += pnl

                    trade_result = {
                        'trade_num': i,
                        'entry_time': str(entry_time),
                        'exit_time': str(current_time),
                        'direction': direction,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'profit_pct': final_profit_pct,
                        'pnl': pnl,
                        'capital': capital,
                        'exit_reason': exit_reason,
                        'peak_profit': peak_profit_pct
                    }
                    trades.append(trade_result)

                    # Print result
                    print(f"Exit: {exit_reason}")
                    print(f"Exit Price: ${exit_price:.2f}")
                    print(f"Profit: {final_profit_pct:+.2f}%")
                    print(f"P&L: ${pnl:+.2f}")
                    print(f"Capital: ${capital:.2f}")
                    print(f"Peak Profit: {peak_profit_pct:.2f}%")

                    exit_found = True
                    break

            if not exit_found:
                print("⚠️  No exit triggered (end of data)")

        return trades, capital, initial_capital

    def print_summary(self, trades, final_capital, initial_capital):
        """Print summary statistics"""
        if not trades:
            print("\n❌ No trades completed")
            return

        print("\n" + "="*80)
        print("📊 USER TRADES SUMMARY")
        print("="*80)

        # Calculate statistics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['profit_pct'] > 0]
        losing_trades = [t for t in trades if t['profit_pct'] <= 0]

        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        profits = [t['profit_pct'] for t in winning_trades]
        losses = [t['profit_pct'] for t in losing_trades]

        total_pnl = sum(t['pnl'] for t in trades)
        return_pct = (final_capital - initial_capital) / initial_capital * 100

        print(f"\n💼 Trading Statistics:")
        print(f"  Initial Capital: ${initial_capital:.2f}")
        print(f"  Final Capital: ${final_capital:.2f}")
        print(f"  Total P&L: ${total_pnl:+.2f}")
        print(f"  Return: {return_pct:+.2f}%")

        print(f"\n📈 Trade Breakdown:")
        print(f"  Total Trades: {total_trades}")
        print(f"  Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"  Losing Trades: {len(losing_trades)} ({100-win_rate:.1f}%)")

        if profits:
            print(f"\n✅ Winning Trades:")
            print(f"  Average Profit: {sum(profits)/len(profits):.2f}%")
            print(f"  Largest Win: {max(profits):.2f}%")
            print(f"  Total Wins: ${sum(t['pnl'] for t in winning_trades):.2f}")

        if losses:
            print(f"\n❌ Losing Trades:")
            print(f"  Average Loss: {sum(losses)/len(losses):.2f}%")
            print(f"  Largest Loss: {min(losses):.2f}%")
            print(f"  Total Losses: ${sum(t['pnl'] for t in losing_trades):.2f}")

        # Exit reasons
        print(f"\n🚪 Exit Reasons:")
        exit_reasons = {}
        for t in trades:
            reason = t['exit_reason'].split(' ')[0]  # Get first word
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count} ({count/total_trades*100:.1f}%)")

        # Compare with bot results
        print("\n" + "="*80)
        print("🔄 COMPARISON: USER vs BOT RESULTS")
        print("="*80)

        print(f"\n{'Metric':<25} {'USER Trades':<20} {'Bot (Refined)':<20} {'Difference':<15}")
        print("-" * 80)

        bot_trades = 13
        bot_win_rate = 53.8
        bot_return = 0.55
        bot_pnl = 5.47

        print(f"{'Total Trades':<25} {total_trades:<20} {bot_trades:<20} {total_trades - bot_trades:+d}")
        print(f"{'Win Rate':<25} {win_rate:<20.1f}% {bot_win_rate:<20.1f}% {win_rate - bot_win_rate:+.1f}%")
        print(f"{'Return %':<25} {return_pct:<20.2f}% {bot_return:<20.2f}% {return_pct - bot_return:+.2f}%")
        print(f"{'Total P&L':<25} ${total_pnl:<19.2f} ${bot_pnl:<19.2f} ${total_pnl - bot_pnl:+.2f}")

        if total_trades > bot_trades:
            print(f"\n✅ USER took {total_trades - bot_trades} MORE trades ({(total_trades/bot_trades - 1)*100:.1f}% more active)")
        else:
            print(f"\n⚠️  USER took {bot_trades - total_trades} FEWER trades ({(1 - total_trades/bot_trades)*100:.1f}% less active)")

        if win_rate > bot_win_rate:
            print(f"✅ USER had HIGHER win rate (+{win_rate - bot_win_rate:.1f}%)")
        else:
            print(f"❌ Bot had HIGHER win rate (+{bot_win_rate - win_rate:.1f}%)")

        if return_pct > bot_return:
            print(f"✅ USER had HIGHER return (+{return_pct - bot_return:.2f}%)")
        else:
            print(f"❌ Bot had HIGHER return (+{bot_return - return_pct:.2f}%)")

        # Save results
        results_file = self.data_dir / 'user_trades_profit.json'
        results = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'final_capital': final_capital,
            'trades': trades,
            'generated_at': datetime.now().isoformat()
        }

        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n💾 Results saved to: {results_file}")


if __name__ == '__main__':
    analyzer = UserTradeAnalyzer()
    trades, final_capital, initial_capital = analyzer.simulate_user_trades()
    analyzer.print_summary(trades, final_capital, initial_capital)

    print("\n" + "="*80)
    print("✅ CALCULATION COMPLETE!")
    print("="*80)
