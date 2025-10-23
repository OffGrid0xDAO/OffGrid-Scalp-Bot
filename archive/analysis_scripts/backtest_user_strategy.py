#!/usr/bin/env python3
"""
Backtest User Pattern Strategy

Compares:
1. OLD strategy (current bot)
2. NEW strategy (based on user's patterns)
3. USER's actual trades

On the period October 5-21, 2025 (your optimal trades period)
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from strategy.entry_detector import EntryDetector as OldEntryDetector
from strategy.entry_detector_user_pattern import EntryDetector as NewEntryDetector
from strategy.exit_manager_user_pattern import ExitManager


class BacktestEngine:
    """Simple backtest engine to compare strategies"""

    def __init__(self, initial_capital: float = 1000.0):
        """Initialize backtest"""
        self.initial_capital = initial_capital
        self.exit_manager = ExitManager()

    def backtest_strategy(self, df: pd.DataFrame, detector, strategy_name: str) -> Dict:
        """
        Run backtest with given entry detector

        Args:
            df: DataFrame with indicators
            detector: Entry detector instance
            strategy_name: Name for logging

        Returns:
            Dictionary with backtest results
        """
        print(f"\n{'='*80}")
        print(f"🔬 BACKTESTING: {strategy_name}")
        print(f"{'='*80}")

        # Scan for signals
        df_signals = detector.scan_historical_signals(df.copy())

        # Simulate trades
        trades = []
        in_position = False
        current_trade = None
        capital = self.initial_capital

        for i in range(len(df_signals)):
            row = df_signals.iloc[i]

            # Check for entry signal
            if not in_position and row['entry_signal']:
                # Enter trade
                current_trade = {
                    'entry_time': row['timestamp'],
                    'entry_price': row['close'],
                    'direction': row['entry_direction'],
                    'entry_confidence': row['entry_confidence'],
                    'quality_score': row.get('entry_quality_score', 0),
                    'peak_profit_pct': 0.0
                }
                in_position = True

                print(f"\n📍 ENTRY: {current_trade['direction'].upper()} at ${current_trade['entry_price']:.2f}")
                print(f"   Time: {current_trade['entry_time']}")
                print(f"   Quality: {current_trade['quality_score']:.1f}")

            # Check for exit if in position
            elif in_position and current_trade:
                # Update peak profit
                if current_trade['direction'] == 'long':
                    profit_pct = (row['close'] - current_trade['entry_price']) / current_trade['entry_price'] * 100
                else:
                    profit_pct = (current_trade['entry_price'] - row['close']) / current_trade['entry_price'] * 100

                current_trade['peak_profit_pct'] = max(current_trade['peak_profit_pct'], profit_pct)

                # Check exit conditions
                exit_result = self.exit_manager.check_exit(
                    current_trade['entry_price'],
                    current_trade['entry_time'],
                    row['close'],
                    row['timestamp'],
                    current_trade['direction'],
                    current_trade['peak_profit_pct']
                )

                if exit_result['should_exit']:
                    # Exit trade
                    current_trade['exit_time'] = row['timestamp']
                    current_trade['exit_price'] = exit_result['exit_price']
                    current_trade['profit_pct'] = exit_result['profit_pct']
                    current_trade['exit_reason'] = exit_result['exit_reason']

                    # Calculate P&L
                    position_size = capital * 0.1  # 10% of capital per trade
                    pnl = position_size * (exit_result['profit_pct'] / 100)
                    current_trade['pnl'] = pnl
                    capital += pnl

                    trades.append(current_trade)

                    print(f"🚪 EXIT: {current_trade['exit_reason']}")
                    print(f"   Exit price: ${current_trade['exit_price']:.2f}")
                    print(f"   Profit: {current_trade['profit_pct']:.2f}%")
                    print(f"   P&L: ${pnl:.2f}")
                    print(f"   Capital: ${capital:.2f}")

                    in_position = False
                    current_trade = None

        # Close any open position at end
        if in_position and current_trade:
            last_row = df_signals.iloc[-1]
            if current_trade['direction'] == 'long':
                profit_pct = (last_row['close'] - current_trade['entry_price']) / current_trade['entry_price'] * 100
            else:
                profit_pct = (current_trade['entry_price'] - last_row['close']) / current_trade['entry_price'] * 100

            current_trade['exit_time'] = last_row['timestamp']
            current_trade['exit_price'] = last_row['close']
            current_trade['profit_pct'] = profit_pct
            current_trade['exit_reason'] = 'End of backtest'

            position_size = capital * 0.1
            pnl = position_size * (profit_pct / 100)
            current_trade['pnl'] = pnl
            capital += pnl

            trades.append(current_trade)

        # Calculate statistics
        results = self._calculate_statistics(trades, capital, strategy_name)

        return results

    def _calculate_statistics(self, trades: list, final_capital: float, strategy_name: str) -> Dict:
        """Calculate backtest statistics"""
        if not trades:
            return {
                'strategy': strategy_name,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'final_capital': final_capital,
                'return_pct': 0,
                'trades': []
            }

        total_trades = len(trades)
        winning_trades = [t for t in trades if t['profit_pct'] > 0]
        losing_trades = [t for t in trades if t['profit_pct'] <= 0]

        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        profits = [t['profit_pct'] for t in winning_trades]
        losses = [t['profit_pct'] for t in losing_trades]

        total_pnl = sum(t['pnl'] for t in trades)
        return_pct = (final_capital - self.initial_capital) / self.initial_capital * 100

        results = {
            'strategy': strategy_name,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_profit': np.mean(profits) if profits else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'largest_win': max(profits) if profits else 0,
            'largest_loss': min(losses) if losses else 0,
            'final_capital': final_capital,
            'return_pct': return_pct,
            'trades': trades
        }

        return results

    def print_comparison(self, old_results: Dict, new_results: Dict, user_trades_count: int):
        """Print comparison between strategies"""
        print("\n" + "="*80)
        print("📊 STRATEGY COMPARISON")
        print("="*80)

        print(f"\n{'Metric':<25} {'Old Strategy':<20} {'New Strategy':<20} {'Improvement':<15}")
        print("-" * 80)

        # Total trades
        old_trades = old_results['total_trades']
        new_trades = new_results['total_trades']
        print(f"{'Total Trades':<25} {old_trades:<20} {new_trades:<20} {new_trades - old_trades:+d}")

        # Win rate
        old_wr = old_results['win_rate']
        new_wr = new_results['win_rate']
        print(f"{'Win Rate':<25} {old_wr:<20.1f}% {new_wr:<20.1f}% {new_wr - old_wr:+.1f}%")

        # Total P&L
        old_pnl = old_results['total_pnl']
        new_pnl = new_results['total_pnl']
        print(f"{'Total P&L':<25} ${old_pnl:<19.2f} ${new_pnl:<19.2f} ${new_pnl - old_pnl:+.2f}")

        # Return %
        old_ret = old_results['return_pct']
        new_ret = new_results['return_pct']
        print(f"{'Return %':<25} {old_ret:<20.2f}% {new_ret:<20.2f}% {new_ret - old_ret:+.2f}%")

        # Average profit
        old_avg = old_results['avg_profit']
        new_avg = new_results['avg_profit']
        print(f"{'Avg Win':<25} {old_avg:<20.2f}% {new_avg:<20.2f}% {new_avg - old_avg:+.2f}%")

        # Average loss
        old_loss = old_results['avg_loss']
        new_loss = new_results['avg_loss']
        print(f"{'Avg Loss':<25} {old_loss:<20.2f}% {new_loss:<20.2f}% {new_loss - old_loss:+.2f}%")

        print("\n" + "="*80)
        print("🎯 USER REFERENCE")
        print("="*80)
        print(f"User took {user_trades_count} trades in this period")
        print(f"Old strategy took {old_trades} trades ({abs(old_trades - user_trades_count)} difference)")
        print(f"New strategy took {new_trades} trades ({abs(new_trades - user_trades_count)} difference)")

        if new_trades > old_trades:
            print(f"\n✅ New strategy is MORE ACTIVE (closer to your trading frequency!)")
        else:
            print(f"\n⚠️  New strategy is LESS ACTIVE than old")

        print("\n" + "="*80)


def main():
    """Run backtest comparison"""
    print("\n" + "="*80)
    print("🚀 BACKTEST: OLD vs NEW STRATEGY")
    print("="*80)
    print("\nPeriod: October 5-21, 2025 (your optimal trades period)")

    # Load data
    data_file = Path(__file__).parent / 'trading_data' / 'indicators' / 'eth_1h_full.csv'

    print(f"\n📊 Loading data: {data_file}")
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Filter to October 5-21 period
    start_date = pd.Timestamp('2025-10-05')
    end_date = pd.Timestamp('2025-10-22')

    df_period = df[(df['timestamp'] >= start_date) & (df['timestamp'] < end_date)].copy()
    df_period = df_period.reset_index(drop=True)

    print(f"   Filtered to {len(df_period)} candles in period")
    print(f"   Date range: {df_period['timestamp'].min()} to {df_period['timestamp'].max()}")

    # Initialize backtester
    backtester = BacktestEngine(initial_capital=1000.0)

    # Test OLD strategy
    print("\n" + "="*80)
    print("Testing OLD Strategy (current bot)...")
    print("="*80)
    old_detector = OldEntryDetector()
    old_results = backtester.backtest_strategy(df_period, old_detector, "Old Strategy (Current Bot)")

    # Reset capital for fair comparison
    backtester = BacktestEngine(initial_capital=1000.0)

    # Test NEW strategy
    print("\n" + "="*80)
    print("Testing NEW Strategy (user pattern based)...")
    print("="*80)
    new_detector = NewEntryDetector()
    new_results = backtester.backtest_strategy(df_period, new_detector, "New Strategy (User Pattern)")

    # Load user trades for reference
    trades_file = Path(__file__).parent / 'trading_data' / 'optimal_trades.json'
    with open(trades_file, 'r') as f:
        user_data = json.load(f)
    user_trades_count = len(user_data['optimal_entries'])

    # Print comparison
    backtester.print_comparison(old_results, new_results, user_trades_count)

    # Save results
    results_file = Path(__file__).parent / 'trading_data' / 'backtest_comparison.json'
    comparison = {
        'period': {
            'start': str(start_date),
            'end': str(end_date),
            'candles': len(df_period)
        },
        'user_trades': user_trades_count,
        'old_strategy': old_results,
        'new_strategy': new_results,
        'generated_at': datetime.now().isoformat()
    }

    # Remove trades list for cleaner JSON
    comparison['old_strategy']['trades'] = len(old_results['trades'])
    comparison['new_strategy']['trades'] = len(new_results['trades'])

    with open(results_file, 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}")

    print("\n" + "="*80)
    print("✅ BACKTEST COMPLETE!")
    print("="*80)


if __name__ == '__main__':
    main()
