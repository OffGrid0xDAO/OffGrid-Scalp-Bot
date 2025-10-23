#!/usr/bin/env python3
"""
Iterative Strategy Optimizer
Runs multiple iterations, analyzes winning trades, and improves strategy
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent / 'src'))
from strategy.entry_detector_user_pattern import EntryDetector
from strategy.exit_manager_user_pattern import ExitManager

class IterativeOptimizer:
    def __init__(self, start_iteration=5):
        self.data_dir = Path(__file__).parent / 'trading_data'
        self.current_iteration = start_iteration
        self.results_history = []

        # Load data
        self.df_1h = pd.read_csv(self.data_dir / 'indicators' / 'eth_1h_full.csv')
        self.df_15m = pd.read_csv(self.data_dir / 'indicators' / 'eth_15m_full.csv')
        self.df_5m = pd.read_csv(self.data_dir / 'indicators' / 'eth_5m_full.csv')

        for df in [self.df_1h, self.df_15m, self.df_5m]:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Filter to period
        self.start_date = pd.Timestamp('2025-09-21')
        self.end_date = pd.Timestamp('2025-10-22')
        self.df_1h_period = self.df_1h[(self.df_1h['timestamp'] >= self.start_date) &
                                        (self.df_1h['timestamp'] < self.end_date)].copy()
        self.df_15m_period = self.df_15m[(self.df_15m['timestamp'] >= self.start_date) &
                                          (self.df_15m['timestamp'] < self.end_date)].copy()
        self.df_5m_period = self.df_5m[(self.df_5m['timestamp'] >= self.start_date) &
                                         (self.df_5m['timestamp'] < self.end_date)].copy()

    def run_backtest(self):
        """Run backtest with current parameters"""
        print(f"\n{'='*80}")
        print(f"🚀 ITERATION {self.current_iteration} BACKTEST")
        print(f"{'='*80}")

        # Initialize detector
        detector = EntryDetector(df_5m=self.df_5m_period, df_15m=self.df_15m_period)

        # Scan for signals
        df_signals = detector.scan_historical_signals(self.df_1h_period)

        # Run backtest
        exit_manager = ExitManager()
        initial_capital = 1000.0
        capital = initial_capital
        trades = []

        in_position = False
        current_trade = None

        for i in range(len(df_signals)):
            row = df_signals.iloc[i]

            if not in_position and row['entry_signal']:
                current_trade = {
                    'entry_time': row['timestamp'],
                    'entry_price': row['close'],
                    'direction': row['entry_direction'],
                    'quality_score': row.get('entry_quality_score', 0),
                    'peak_profit_pct': 0.0,
                    'entry_index': i,
                    # Capture entry indicators
                    'entry_alignment': row.get('alignment_pct', 0),
                    'entry_compression': row.get('compression_score', 0),
                    'entry_expansion': row.get('expansion_rate', 0),
                    'entry_confluence_long': row.get('confluence_score_long', 0),
                    'entry_confluence_short': row.get('confluence_score_short', 0),
                    'entry_rsi_14': row.get('rsi_14', 0),
                    'entry_rsi_7': row.get('rsi_7', 0),
                    'entry_volume_status': row.get('volume_status', 'unknown'),
                    'entry_volume_ratio': row.get('volume_ratio', 0),
                    'entry_stoch_k': row.get('stoch_k', 0),
                    'entry_stoch_d': row.get('stoch_d', 0)
                }
                in_position = True

            elif in_position and current_trade:
                if current_trade['direction'] == 'long':
                    profit_pct = (row['close'] - current_trade['entry_price']) / current_trade['entry_price'] * 100
                else:
                    profit_pct = (current_trade['entry_price'] - row['close']) / current_trade['entry_price'] * 100

                current_trade['peak_profit_pct'] = max(current_trade['peak_profit_pct'], profit_pct)

                exit_result = exit_manager.check_exit(
                    current_trade['entry_price'],
                    current_trade['entry_time'],
                    row['close'],
                    row['timestamp'],
                    current_trade['direction'],
                    current_trade['peak_profit_pct']
                )

                if exit_result['should_exit']:
                    current_trade['exit_time'] = row['timestamp']
                    current_trade['exit_price'] = exit_result['exit_price']
                    current_trade['profit_pct'] = exit_result['profit_pct']
                    current_trade['exit_reason'] = exit_result['exit_reason']
                    current_trade['exit_index'] = i

                    position_size = capital * 0.1
                    pnl = position_size * (exit_result['profit_pct'] / 100)
                    current_trade['pnl'] = pnl
                    capital += pnl

                    trades.append(current_trade)
                    in_position = False
                    current_trade = None

        # Close any open position
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
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['profit_pct'] > 0]
        losing_trades = [t for t in trades if t['profit_pct'] <= 0]
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        return_pct = (capital - initial_capital) / initial_capital * 100

        results = {
            'iteration': self.current_iteration,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'return_pct': return_pct,
            'capital': capital,
            'pnl': capital - initial_capital,
            'trades': trades
        }

        print(f"\n📊 Results: {total_trades} trades | {win_rate:.1f}% win rate | {return_pct:+.2f}% return")

        return results

    def analyze_winning_trades(self, results):
        """Analyze winning trades to find patterns"""
        print(f"\n{'='*80}")
        print(f"🔍 ANALYZING WINNING TRADES")
        print(f"{'='*80}")

        winning_trades = [t for t in results['trades'] if t['profit_pct'] > 0]

        if len(winning_trades) == 0:
            print("❌ No winning trades to analyze!")
            return {}

        df_winners = pd.DataFrame(winning_trades)

        # Separate by direction
        long_winners = df_winners[df_winners['direction'] == 'long']
        short_winners = df_winners[df_winners['direction'] == 'short']

        patterns = {}

        print(f"\n✅ Analyzed {len(winning_trades)} winning trades")
        print(f"   {len(long_winners)} LONG | {len(short_winners)} SHORT")

        # Analyze alignment
        if len(long_winners) > 0:
            patterns['long_alignment_min'] = long_winners['entry_alignment'].quantile(0.25)
            patterns['long_alignment_max'] = long_winners['entry_alignment'].quantile(0.75)
            print(f"\n📈 LONG Winners Alignment: {patterns['long_alignment_min']:.3f} - {patterns['long_alignment_max']:.3f}")

        if len(short_winners) > 0:
            patterns['short_alignment_min'] = short_winners['entry_alignment'].quantile(0.25)
            patterns['short_alignment_max'] = short_winners['entry_alignment'].quantile(0.75)
            print(f"📉 SHORT Winners Alignment: {patterns['short_alignment_min']:.3f} - {patterns['short_alignment_max']:.3f}")

        # Analyze confluence
        patterns['confluence_min'] = df_winners['entry_confluence_long'].quantile(0.25) if len(long_winners) > 0 else 0
        patterns['confluence_min'] = max(patterns['confluence_min'],
                                         df_winners['entry_confluence_short'].quantile(0.25) if len(short_winners) > 0 else 0)
        print(f"\n💎 Winners Confluence: min {patterns['confluence_min']:.1f}")

        # Analyze RSI-7
        patterns['rsi_7_min'] = df_winners['entry_rsi_7'].quantile(0.1)
        patterns['rsi_7_max'] = df_winners['entry_rsi_7'].quantile(0.9)
        print(f"📉 Winners RSI-7: {patterns['rsi_7_min']:.1f} - {patterns['rsi_7_max']:.1f}")

        # Analyze volume
        patterns['volume_ratio_min'] = df_winners['entry_volume_ratio'].quantile(0.25)
        print(f"📦 Winners Volume ratio: min {patterns['volume_ratio_min']:.2f}")

        # Analyze stoch D
        patterns['stoch_d_min'] = df_winners['entry_stoch_d'].quantile(0.25)
        print(f"📊 Winners Stoch D: min {patterns['stoch_d_min']:.1f}")

        return patterns

    def update_parameters(self, patterns):
        """Update strategy parameters based on patterns"""
        print(f"\n{'='*80}")
        print(f"⚙️  UPDATING PARAMETERS FOR ITERATION {self.current_iteration + 1}")
        print(f"{'='*80}")

        params_file = Path(__file__).parent / 'src' / 'strategy' / 'strategy_params_user.json'
        with open(params_file, 'r') as f:
            params = json.load(f)

        # Update based on winning patterns
        if 'confluence_min' in patterns:
            old_val = params['entry_filters']['confluence_score_min']
            params['entry_filters']['confluence_score_min'] = max(5, patterns['confluence_min'] * 0.8)
            print(f"   Confluence min: {old_val} → {params['entry_filters']['confluence_score_min']:.1f}")

        if 'rsi_7_min' in patterns and 'rsi_7_max' in patterns:
            old_range = params['entry_filters']['rsi_7_range']
            params['entry_filters']['rsi_7_range'] = [
                max(5, patterns['rsi_7_min'] - 5),
                min(95, patterns['rsi_7_max'] + 5)
            ]
            print(f"   RSI-7 range: {old_range} → {params['entry_filters']['rsi_7_range']}")

        if 'volume_ratio_min' in patterns:
            old_val = params['entry_filters']['min_volume_ratio']
            params['entry_filters']['min_volume_ratio'] = max(0.3, patterns['volume_ratio_min'] * 0.8)
            print(f"   Volume ratio min: {old_val:.2f} → {params['entry_filters']['min_volume_ratio']:.2f}")

        if 'stoch_d_min' in patterns:
            old_val = params['entry_filters']['min_stoch_d']
            params['entry_filters']['min_stoch_d'] = max(10, patterns['stoch_d_min'] * 0.9)
            print(f"   Stoch D min: {old_val} → {params['entry_filters']['min_stoch_d']:.1f}")

        # Save updated parameters
        with open(params_file, 'w') as f:
            json.dump(params, f, indent=2)

        print(f"\n✅ Parameters updated for Iteration {self.current_iteration + 1}")

    def run_iteration(self):
        """Run one complete iteration"""
        results = self.run_backtest()
        self.results_history.append(results)

        # Analyze winners
        patterns = self.analyze_winning_trades(results)

        # Update parameters for next iteration
        if patterns:
            self.update_parameters(patterns)

        # Save iteration results
        output_file = self.data_dir / f'iteration_{self.current_iteration}_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Saved to: {output_file}")

        return results

if __name__ == '__main__':
    optimizer = IterativeOptimizer(start_iteration=5)

    print("\n" + "="*80)
    print("🤖 ITERATIVE STRATEGY OPTIMIZER")
    print("="*80)
    print("\nRunning 5 more iterations (5-9)")
    print("Each iteration learns from winning trades")

    for i in range(5):
        results = optimizer.run_iteration()
        optimizer.current_iteration += 1

        print(f"\n{'='*80}")
        print(f"✅ ITERATION {results['iteration']} COMPLETE")
        print(f"   Return: {results['return_pct']:+.2f}% | Trades: {results['total_trades']} | Win Rate: {results['win_rate']:.1f}%")
        print(f"{'='*80}\n")

    # Summary
    print("\n" + "="*80)
    print("📊 ALL ITERATIONS SUMMARY")
    print("="*80)

    for r in optimizer.results_history:
        print(f"Iteration {r['iteration']}: {r['return_pct']:+.2f}% | {r['total_trades']} trades | {r['win_rate']:.1f}% WR")

    best = max(optimizer.results_history, key=lambda x: x['return_pct'])
    print(f"\n🏆 Best: Iteration {best['iteration']} with {best['return_pct']:+.2f}% return")
