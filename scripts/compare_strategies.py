#!/usr/bin/env python3
"""
Compare Trading Strategies

Runs backtest on:
1. Current Confluence Strategy (confluence gap > 23, many filters)
2. New Ribbon Strategy (ribbon flip + alignment + volume)

Shows side-by-side comparison to see which performs better.
"""

import sys
from pathlib import Path
import pandas as pd
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategy.entry_detector import EntryDetector
from strategy.ribbon_day_trading_detector import RibbonDayTradingDetector
from strategy.exit_manager import ExitManager
from backtest.backtest_engine import BacktestEngine


def main():
    """Compare strategies"""
    print("="*80)
    print("STRATEGY COMPARISON: CONFLUENCE vs RIBBON")
    print("="*80)

    # Load data
    data_file = Path(__file__).parent.parent / 'trading_data' / 'indicators' / 'eth_1h_full.csv'

    if not data_file.exists():
        print(f"\n❌ Data file not found: {data_file}")
        sys.exit(1)

    print(f"\n📊 Loading data...")
    df = pd.read_csv(data_file)
    print(f"   {len(df)} candles loaded")

    # Initialize backtest engine
    backtest_engine = BacktestEngine(
        initial_capital=10000,
        commission_pct=0.05,
        slippage_pct=0.02,
        position_size_pct=10.0,
        max_concurrent_trades=3
    )

    # ========== STRATEGY 1: Current Confluence Strategy ==========
    print("\n" + "="*80)
    print("STRATEGY 1: CURRENT CONFLUENCE STRATEGY")
    print("="*80)

    confluence_detector = EntryDetector()
    exit_manager = ExitManager()

    print("\nRunning backtest...")
    confluence_results = backtest_engine.run_backtest(
        df=df,
        entry_detector=confluence_detector,
        exit_manager=exit_manager,
        verbose=False
    )

    confluence_metrics = confluence_results['metrics']

    print(f"\n📊 Confluence Strategy Results:")
    print(f"   Total Trades: {confluence_metrics['total_trades']}")
    print(f"   Win Rate: {confluence_metrics['win_rate']:.2f}%")
    print(f"   Total Return: {confluence_metrics['total_return']:.2f}%")
    print(f"   Profit Factor: {confluence_metrics['profit_factor']:.2f}")
    print(f"   Max Drawdown: {confluence_metrics['max_drawdown']:.2f}%")
    print(f"   Avg Win: {confluence_metrics['avg_win']:.2f}%")
    print(f"   Avg Loss: {confluence_metrics['avg_loss']:.2f}%")
    print(f"   Final Capital: ${confluence_metrics['final_capital']:.2f}")

    # ========== STRATEGY 2: New Ribbon Strategy ==========
    print("\n" + "="*80)
    print("STRATEGY 2: NEW RIBBON DAY TRADING STRATEGY")
    print("="*80)

    ribbon_detector = RibbonDayTradingDetector()
    exit_manager_ribbon = ExitManager()

    print("\nRunning backtest...")
    ribbon_results = backtest_engine.run_backtest(
        df=df,
        entry_detector=ribbon_detector,
        exit_manager=exit_manager_ribbon,
        verbose=False
    )

    ribbon_metrics = ribbon_results['metrics']

    print(f"\n📊 Ribbon Strategy Results:")
    print(f"   Total Trades: {ribbon_metrics['total_trades']}")
    print(f"   Win Rate: {ribbon_metrics['win_rate']:.2f}%")
    print(f"   Total Return: {ribbon_metrics['total_return']:.2f}%")
    print(f"   Profit Factor: {ribbon_metrics['profit_factor']:.2f}")
    print(f"   Max Drawdown: {ribbon_metrics['max_drawdown']:.2f}%")
    print(f"   Avg Win: {ribbon_metrics['avg_win']:.2f}%")
    print(f"   Avg Loss: {ribbon_metrics['avg_loss']:.2f}%")
    print(f"   Final Capital: ${ribbon_metrics['final_capital']:.2f}")

    # ========== COMPARISON ==========
    print("\n" + "="*80)
    print("SIDE-BY-SIDE COMPARISON")
    print("="*80)

    comparison = {
        'Metric': [],
        'Confluence': [],
        'Ribbon': [],
        'Winner': []
    }

    metrics_to_compare = [
        ('Total Trades', 'total_trades', 'lower'),
        ('Win Rate %', 'win_rate', 'higher'),
        ('Total Return %', 'total_return', 'higher'),
        ('Profit Factor', 'profit_factor', 'higher'),
        ('Max Drawdown %', 'max_drawdown', 'lower'),
        ('Avg Win %', 'avg_win', 'higher'),
        ('Avg Loss %', 'avg_loss', 'higher'),
        ('Final Capital', 'final_capital', 'higher'),
    ]

    for metric_name, metric_key, better in metrics_to_compare:
        conf_val = confluence_metrics[metric_key]
        rib_val = ribbon_metrics[metric_key]

        comparison['Metric'].append(metric_name)
        comparison['Confluence'].append(f"{conf_val:.2f}")
        comparison['Ribbon'].append(f"{rib_val:.2f}")

        if better == 'higher':
            winner = '✅ Ribbon' if rib_val > conf_val else '✅ Confluence' if conf_val > rib_val else '🤝 Tie'
        else:  # lower is better
            winner = '✅ Ribbon' if rib_val < conf_val else '✅ Confluence' if conf_val < rib_val else '🤝 Tie'

        comparison['Winner'].append(winner)

    # Print comparison table
    print(f"\n{'Metric':<20} {'Confluence':<15} {'Ribbon':<15} {'Winner':<15}")
    print("-" * 75)
    for i in range(len(comparison['Metric'])):
        print(f"{comparison['Metric'][i]:<20} {comparison['Confluence'][i]:<15} {comparison['Ribbon'][i]:<15} {comparison['Winner'][i]:<15}")

    # Overall winner
    print("\n" + "="*80)
    print("OVERALL VERDICT")
    print("="*80)

    ribbon_wins = sum(1 for w in comparison['Winner'] if 'Ribbon' in w)
    confluence_wins = sum(1 for w in comparison['Winner'] if 'Confluence' in w)

    print(f"\nRibbon Strategy: {ribbon_wins} wins")
    print(f"Confluence Strategy: {confluence_wins} wins")

    if ribbon_wins > confluence_wins:
        print(f"\n🏆 WINNER: RIBBON STRATEGY")
        print(f"   Better return with fewer trades = more selective, higher quality signals")
    elif confluence_wins > ribbon_wins:
        print(f"\n🏆 WINNER: CONFLUENCE STRATEGY")
        print(f"   Current strategy still performs better")
    else:
        print(f"\n🤝 TIE: Both strategies perform similarly")

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    if ribbon_metrics['total_return'] > confluence_metrics['total_return'] * 1.5:
        print("\n✅ SWITCH TO RIBBON STRATEGY")
        print("   Significantly better returns justify the change")
    elif ribbon_metrics['win_rate'] > confluence_metrics['win_rate'] + 10:
        print("\n✅ CONSIDER RIBBON STRATEGY")
        print("   Much higher win rate provides more consistent performance")
    elif ribbon_metrics['total_trades'] < confluence_metrics['total_trades'] / 2 and \
         ribbon_metrics['total_return'] > confluence_metrics['total_return']:
        print("\n✅ SWITCH TO RIBBON STRATEGY")
        print("   Same/better returns with MUCH fewer trades = better quality")
    else:
        print("\n⚠️  STICK WITH CONFLUENCE STRATEGY (for now)")
        print("   But consider combining both strategies:")
        print("   - Use ribbon flips as confirmation for confluence signals")
        print("   - Take trades only when BOTH strategies agree")

    # Save results
    results_file = Path(__file__).parent.parent / 'optimization_logs' / 'strategy_comparison.json'
    with open(results_file, 'w') as f:
        json.dump({
            'confluence': confluence_metrics,
            'ribbon': ribbon_metrics,
            'comparison': comparison,
            'winner': 'ribbon' if ribbon_wins > confluence_wins else 'confluence' if confluence_wins > ribbon_wins else 'tie'
        }, f, indent=2)

    print(f"\n💾 Results saved: {results_file}")
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
