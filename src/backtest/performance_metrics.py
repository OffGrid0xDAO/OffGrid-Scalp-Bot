#!/usr/bin/env python3
"""
Performance Metrics Module

Comprehensive comparison between:
- Optimal trades (perfect hindsight)
- Backtest trades (strategy rules)
- Actual trades (live execution)

Generates detailed metrics and insights for optimization
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime


class PerformanceMetrics:
    """
    Calculate comprehensive performance metrics and comparisons
    """

    def __init__(self):
        """Initialize performance metrics calculator"""
        pass

    def compare_all_three(
        self,
        optimal_trades: List[Dict],
        backtest_trades: List[Dict],
        actual_trades: List[Dict] = None
    ) -> Dict:
        """
        Complete 3-way comparison analysis

        Args:
            optimal_trades: Perfect hindsight trades
            backtest_trades: Strategy simulation trades
            actual_trades: Live execution trades (optional)

        Returns:
            dict with comprehensive comparison metrics
        """
        print("\n" + "="*80)
        print("COMPREHENSIVE 3-WAY PERFORMANCE COMPARISON")
        print("="*80)

        # Calculate individual metrics
        optimal_metrics = self.calculate_trade_metrics(optimal_trades, "Optimal")
        backtest_metrics = self.calculate_trade_metrics(backtest_trades, "Backtest")
        actual_metrics = self.calculate_trade_metrics(actual_trades, "Actual") if actual_trades else None

        # Gap analysis
        optimal_backtest_gap = self.calculate_gap(optimal_metrics, backtest_metrics)
        backtest_actual_gap = self.calculate_gap(backtest_metrics, actual_metrics) if actual_metrics else None

        # Entry timing comparison
        entry_comparison = self.compare_entry_timing(optimal_trades, backtest_trades, actual_trades)

        # Exit quality comparison
        exit_comparison = self.compare_exit_quality(optimal_trades, backtest_trades, actual_trades)

        # Compile full report
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'optimal': optimal_metrics,
            'backtest': backtest_metrics,
            'actual': actual_metrics,
            'gaps': {
                'optimal_vs_backtest': optimal_backtest_gap,
                'backtest_vs_actual': backtest_actual_gap
            },
            'entry_analysis': entry_comparison,
            'exit_analysis': exit_comparison,
            'summary': self._generate_summary(optimal_metrics, backtest_metrics, actual_metrics)
        }

        self._print_comparison_table(comparison)

        return comparison

    def calculate_trade_metrics(self, trades: List[Dict], label: str = "Trades") -> Dict:
        """
        Calculate comprehensive metrics for a set of trades

        Args:
            trades: List of trade dictionaries
            label: Label for this trade set

        Returns:
            dict with all metrics
        """
        if not trades:
            return {
                'label': label,
                'count': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_hold_time': 0,
                'max_profit': 0,
                'max_loss': 0,
                'mfe_avg': 0,
                'mae_avg': 0
            }

        # Basic counts
        count = len(trades)

        # PnL calculations
        pnls = []
        for trade in trades:
            if 'profit_pct' in trade:
                pnls.append(trade['profit_pct'])
            elif 'total_pnl_pct' in trade:
                pnls.append(trade['total_pnl_pct'])
            elif 'mfe' in trade:  # Optimal trades use MFE as realized profit
                pnls.append(trade['mfe'])

        total_pnl = sum(pnls)
        avg_pnl = total_pnl / count if count > 0 else 0

        # Win rate
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p <= 0]
        win_rate = len(winners) / count * 100 if count > 0 else 0

        # Profit factor
        gross_profit = sum(winners) if winners else 0
        gross_loss = abs(sum(losers)) if losers else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0)

        # Hold time
        hold_times = []
        for trade in trades:
            if 'candles_held' in trade:
                hold_times.append(trade['candles_held'])
        avg_hold_time = np.mean(hold_times) if hold_times else 0

        # Max profit/loss
        max_profit = max(pnls) if pnls else 0
        max_loss = min(pnls) if pnls else 0

        # MFE/MAE
        mfes = [trade.get('mfe', 0) for trade in trades]
        maes = [trade.get('mae', 0) for trade in trades]
        mfe_avg = np.mean(mfes) if mfes else 0
        mae_avg = np.mean(maes) if maes else 0

        return {
            'label': label,
            'count': count,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_hold_time': avg_hold_time,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'mfe_avg': mfe_avg,
            'mae_avg': mae_avg,
            'winners': len(winners),
            'losers': len(losers)
        }

    def calculate_gap(self, metrics1: Dict, metrics2: Dict) -> Dict:
        """
        Calculate performance gap between two metric sets

        Args:
            metrics1: First metrics (usually better performance)
            metrics2: Second metrics (usually worse performance)

        Returns:
            dict with gap analysis
        """
        if not metrics1 or not metrics2:
            return {}

        trade_gap = metrics1['count'] - metrics2['count']
        pnl_gap = metrics1['total_pnl'] - metrics2['total_pnl']
        win_rate_gap = metrics1['win_rate'] - metrics2['win_rate']

        # Capture rate (what % of optimal profit did we capture?)
        capture_rate = (metrics2['total_pnl'] / metrics1['total_pnl'] * 100) if metrics1['total_pnl'] > 0 else 0

        # Efficiency score
        efficiency = (metrics2['avg_pnl'] / metrics1['avg_pnl'] * 100) if metrics1['avg_pnl'] > 0 else 0

        return {
            'trade_count_gap': trade_gap,
            'pnl_gap': pnl_gap,
            'win_rate_gap': win_rate_gap,
            'capture_rate': capture_rate,
            'efficiency_score': efficiency,
            'interpretation': self._interpret_gap(trade_gap, pnl_gap, capture_rate)
        }

    def compare_entry_timing(
        self,
        optimal_trades: List[Dict],
        backtest_trades: List[Dict],
        actual_trades: List[Dict] = None
    ) -> Dict:
        """
        Compare entry timing between trade sets

        Analyzes:
        - Missed entries (optimal but not taken)
        - False entries (taken but not optimal)
        - Perfect matches (same entry points)
        - Early/late entries (close but different timing)
        """
        # Create entry timestamp sets
        optimal_entries = set()
        for trade in optimal_trades:
            if 'entry_time' in trade:
                optimal_entries.add(trade['entry_time'])

        backtest_entries = set()
        for trade in backtest_trades:
            if 'entry_time' in trade:
                backtest_entries.add(trade['entry_time'])

        # Calculate overlaps and misses
        perfect_matches = optimal_entries & backtest_entries
        missed_entries = optimal_entries - backtest_entries
        false_entries = backtest_entries - optimal_entries

        # Calculate missed profit
        missed_profit = sum(
            trade.get('profit_pct', trade.get('mfe', 0))
            for trade in optimal_trades
            if trade.get('entry_time') in missed_entries
        )

        # Calculate false signal cost
        false_cost = sum(
            trade.get('total_pnl_pct', 0)
            for trade in backtest_trades
            if trade.get('entry_time') in false_entries
        )

        return {
            'perfect_matches': len(perfect_matches),
            'missed_entries': len(missed_entries),
            'false_entries': len(false_entries),
            'missed_profit': missed_profit,
            'false_cost': false_cost,
            'match_rate': (len(perfect_matches) / len(optimal_entries) * 100) if optimal_entries else 0
        }

    def compare_exit_quality(
        self,
        optimal_trades: List[Dict],
        backtest_trades: List[Dict],
        actual_trades: List[Dict] = None
    ) -> Dict:
        """
        Compare exit quality

        Analyzes:
        - Early exits (exited before optimal)
        - Late exits (held too long)
        - MFE capture rate (% of max profit captured)
        """
        if not backtest_trades:
            return {}

        # Calculate MFE capture for each backtest trade
        mfe_captures = []
        early_exits = 0
        perfect_exits = 0

        for trade in backtest_trades:
            mfe = trade.get('mfe', 0)
            realized = trade.get('total_pnl_pct', 0)

            if mfe > 0:
                capture = (realized / mfe * 100)
                mfe_captures.append(capture)

                if capture < 80:  # Captured less than 80% of MFE
                    early_exits += 1
                elif capture >= 95:  # Captured 95%+ of MFE
                    perfect_exits += 1

        avg_mfe_capture = np.mean(mfe_captures) if mfe_captures else 0

        # Calculate profit left on table
        profit_left = sum(
            trade.get('mfe', 0) - trade.get('total_pnl_pct', 0)
            for trade in backtest_trades
        )

        return {
            'avg_mfe_capture': avg_mfe_capture,
            'early_exits': early_exits,
            'perfect_exits': perfect_exits,
            'profit_left_on_table': profit_left,
            'exit_efficiency': avg_mfe_capture
        }

    def _interpret_gap(self, trade_gap: int, pnl_gap: float, capture_rate: float) -> str:
        """Generate interpretation of performance gap"""
        if abs(trade_gap) < 10 and capture_rate > 80:
            return "✅ Excellent alignment - strategy closely matches optimal"
        elif trade_gap > 100:
            return "🔴 Massive over-trading - taking too many low-quality signals"
        elif trade_gap < -50:
            return "🟡 Under-trading - filters too strict, missing opportunities"
        elif capture_rate < 30:
            return "🔴 Very low capture rate - missing best setups or exiting too early"
        elif capture_rate < 60:
            return "🟡 Moderate capture - room for significant improvement"
        else:
            return "✅ Good performance - incremental optimization possible"

    def _generate_summary(
        self,
        optimal: Dict,
        backtest: Dict,
        actual: Dict = None
    ) -> Dict:
        """Generate executive summary"""
        return {
            'optimal_potential': f"+{optimal['total_pnl']:.2f}% ({optimal['count']} trades)",
            'backtest_achieved': f"+{backtest['total_pnl']:.2f}% ({backtest['count']} trades)",
            'capture_rate': f"{(backtest['total_pnl'] / optimal['total_pnl'] * 100):.1f}%" if optimal['total_pnl'] > 0 else "0%",
            'profit_gap': f"{optimal['total_pnl'] - backtest['total_pnl']:.2f}%",
            'key_issue': self._identify_key_issue(optimal, backtest)
        }

    def _identify_key_issue(self, optimal: Dict, backtest: Dict) -> str:
        """Identify the primary issue limiting performance"""
        trade_ratio = backtest['count'] / optimal['count'] if optimal['count'] > 0 else 0
        capture_rate = backtest['total_pnl'] / optimal['total_pnl'] * 100 if optimal['total_pnl'] > 0 else 0

        if trade_ratio > 5:
            return "Over-trading: Taking too many low-quality signals"
        elif trade_ratio < 0.3:
            return "Under-trading: Missing profitable setups due to strict filters"
        elif capture_rate < 30:
            return "Poor execution: Either missing best entries or exiting too early"
        elif backtest['win_rate'] < 45:
            return "Low win rate: Strategy not aligned with market conditions"
        else:
            return "Exit timing: Leaving profit on the table"

    def _print_comparison_table(self, comparison: Dict):
        """Print formatted comparison table"""
        print("\n" + "="*80)
        print("PERFORMANCE METRICS COMPARISON")
        print("="*80)

        opt = comparison['optimal']
        bt = comparison['backtest']
        act = comparison.get('actual')

        # Trade counts
        print(f"\n{'Metric':<25} {'Optimal':>15} {'Backtest':>15} {'Actual':>15}")
        print("-" * 80)

        print(f"{'Trade Count':<25} {opt['count']:>15} {bt['count']:>15} {act['count'] if act else 0:>15}")
        print(f"{'Win Rate':<25} {opt['win_rate']:>14.1f}% {bt['win_rate']:>14.1f}% {act['win_rate'] if act else 0:>14.1f}%")
        print(f"{'Total PnL':<25} {opt['total_pnl']:>14.2f}% {bt['total_pnl']:>14.2f}% {act['total_pnl'] if act else 0:>14.2f}%")
        print(f"{'Avg PnL/Trade':<25} {opt['avg_pnl']:>14.2f}% {bt['avg_pnl']:>14.2f}% {act['avg_pnl'] if act else 0:>14.2f}%")
        print(f"{'Profit Factor':<25} {opt['profit_factor']:>15.2f} {bt['profit_factor']:>15.2f} {act['profit_factor'] if act else 0:>15.2f}")
        print(f"{'Avg Hold Time':<25} {opt['avg_hold_time']:>14.1f}c {bt['avg_hold_time']:>14.1f}c {act['avg_hold_time'] if act else 0:>14.1f}c")

        # Gap analysis
        if 'gaps' in comparison:
            gap = comparison['gaps']['optimal_vs_backtest']
            print(f"\n{'GAP ANALYSIS (Optimal → Backtest)':<80}")
            print("-" * 80)
            print(f"Trade Gap: {gap['trade_count_gap']:+d} trades")
            print(f"PnL Gap: {gap['pnl_gap']:+.2f}%")
            print(f"Capture Rate: {gap['capture_rate']:.1f}%")
            print(f"Win Rate Gap: {gap['win_rate_gap']:+.1f}%")
            print(f"\n{gap['interpretation']}")

        # Entry analysis
        if 'entry_analysis' in comparison:
            entry = comparison['entry_analysis']
            print(f"\n{'ENTRY TIMING ANALYSIS':<80}")
            print("-" * 80)
            print(f"Perfect Matches: {entry['perfect_matches']} ({entry['match_rate']:.1f}%)")
            print(f"Missed Entries: {entry['missed_entries']} (lost {entry['missed_profit']:.2f}%)")
            print(f"False Signals: {entry['false_entries']} (cost {entry['false_cost']:.2f}%)")

        # Exit analysis
        if 'exit_analysis' in comparison:
            exit_a = comparison['exit_analysis']
            print(f"\n{'EXIT QUALITY ANALYSIS':<80}")
            print("-" * 80)
            print(f"Avg MFE Capture: {exit_a['avg_mfe_capture']:.1f}%")
            print(f"Early Exits: {exit_a['early_exits']}")
            print(f"Perfect Exits: {exit_a['perfect_exits']}")
            print(f"Profit Left on Table: {exit_a['profit_left_on_table']:.2f}%")

        # Summary
        if 'summary' in comparison:
            summary = comparison['summary']
            print(f"\n{'EXECUTIVE SUMMARY':<80}")
            print("-" * 80)
            print(f"Optimal Potential: {summary['optimal_potential']}")
            print(f"Backtest Achieved: {summary['backtest_achieved']}")
            print(f"Capture Rate: {summary['capture_rate']}")
            print(f"Profit Gap: {summary['profit_gap']}")
            print(f"\n🎯 Key Issue: {summary['key_issue']}")

        print("="*80)


if __name__ == '__main__':
    """Test performance metrics"""
    print("Performance Metrics - Test Mode")

    # Create sample trades
    optimal_trades = [
        {'entry_time': '2025-01-01 10:00', 'profit_pct': 2.5, 'mfe': 2.5, 'mae': -0.3, 'candles_held': 5},
        {'entry_time': '2025-01-01 14:00', 'profit_pct': 3.2, 'mfe': 3.2, 'mae': -0.2, 'candles_held': 8},
        {'entry_time': '2025-01-01 18:00', 'profit_pct': 1.8, 'mfe': 1.8, 'mae': -0.4, 'candles_held': 4},
    ]

    backtest_trades = [
        {'entry_time': '2025-01-01 10:00', 'total_pnl_pct': 1.5, 'mfe': 2.5, 'mae': -0.3, 'candles_held': 3},
        {'entry_time': '2025-01-01 16:00', 'total_pnl_pct': -0.5, 'mfe': 0.8, 'mae': -0.8, 'candles_held': 2},
    ]

    metrics = PerformanceMetrics()
    comparison = metrics.compare_all_three(optimal_trades, backtest_trades)

    print("\n✅ Performance metrics calculation complete!")
