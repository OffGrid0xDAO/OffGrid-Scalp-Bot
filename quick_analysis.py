#!/usr/bin/env python3
"""
Quick Backtest Results Analysis
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path('.')))
sys.path.insert(0, str(Path('.') / 'src'))
sys.path.insert(0, str(Path('.') / 'fourier_strategy'))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime
import json

# Set style
plt.style.use('dark_background')
sns.set_palette("husl")

def run_quick_analysis():
    """Run a quick analysis using the original backtest"""

    print("🚀 Quick Backtest Analysis")
    print("="*50)

    # Import here
    from backtest_COMPLETE_PIPELINE import ITERATIONS, run_complete_pipeline_backtest
    from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter

    # Fetch data once
    print("📊 Fetching market data...")
    adapter = HyperliquidDataAdapter()
    df = adapter.fetch_ohlcv(interval='5m', days_back=17)
    print(f"✅ Fetched {len(df)} candles")

    # Run all iterations
    results = []
    for iter_num, iter_config in ITERATIONS.items():
        print(f"\n🧪 Running {iter_config['name']}")
        result = run_complete_pipeline_backtest(df, iter_config)
        results.append(result)
        print(f"   📊 {result['num_trades']} trades, {result['return_17d']:.2f}% return, {result['win_rate']:.1f}% win rate")

    # Create summary
    print("\n" + "="*50)
    print("📊 RESULTS SUMMARY")
    print("="*50)

    print(f"{'Iteration':<25} {'Return':<10} {'Win Rate':<12} {'Sharpe':<8} {'Trades':<8}")
    print("-" * 50)

    for i, result in enumerate(results, 1):
        config = ITERATIONS[i]
        print(f"{result['iteration']:<25} {result['return_17d']:>8.2f}%  {result['win_rate']:>10.1f}%  {result['sharpe']:>6.2f}  {result['num_trades']:>6}")
        print(f"{'  Expected: ' + config['expected_return'] + ', ' + config['expected_win_rate']:<38}")

    print("-" * 50)

    # Calculate totals
    total_trades = sum(r['num_trades'] for r in results)
    avg_return = np.mean([r['return_17d'] for r in results])
    avg_win_rate = np.mean([r['win_rate'] for r in results])
    avg_sharpe = np.mean([r['sharpe'] for r in results])

    print(f"\n🎯 OVERALL PERFORMANCE:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Average Return: {avg_return:.2f}%")
    print(f"   Average Win Rate: {avg_win_rate:.1f}%")
    print(f"   Average Sharpe: {avg_sharpe:.2f}")

    # Create simple chart
    create_performance_chart(results, ITERATIONS)

    # Save results
    save_results(results, ITERATIONS)

    print(f"\n✅ Analysis complete!")

def create_performance_chart(results, iterations):
    """Create a performance chart"""

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Backtest Performance Analysis', fontsize=16, fontweight='bold')

    # Data
    iter_names = [f"Iteration {i}" for i in range(1, len(results)+1)]
    returns = [r['return_17d'] for r in results]
    win_rates = [r['win_rate'] for r in results]
    trades = [r['num_trades'] for r in results]

    # Expected values (midpoints)
    expected_returns = [3.5, 5.5, 7.25]
    expected_win_rates = [83.5, 80, 77.5]

    colors = ['#4ecdc4', '#f7b731', '#5f27cd']

    # Returns chart
    x = np.arange(len(iter_names))
    width = 0.35

    bars1 = ax1.bar(x - width/2, returns, width, label='Actual', color='#00ff88', alpha=0.8)
    bars2 = ax1.bar(x + width/2, expected_returns, width, label='Expected', color='#ff6b6b', alpha=0.8)

    ax1.set_title('Returns vs Expected', fontweight='bold')
    ax1.set_ylabel('Return (%)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(iter_names)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')

    # Win rates chart
    bars1 = ax2.bar(x - width/2, win_rates, width, label='Actual', color='#00ff88', alpha=0.8)
    bars2 = ax2.bar(x + width/2, expected_win_rates, width, label='Expected', color='#ff6b6b', alpha=0.8)

    ax2.set_title('Win Rates vs Expected', fontweight='bold')
    ax2.set_ylabel('Win Rate (%)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(iter_names)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')

    # Trade count chart
    bars = ax3.bar(iter_names, trades, color=colors, alpha=0.8)
    ax3.set_title('Number of Trades', fontweight='bold')
    ax3.set_ylabel('Number of Trades')
    ax3.grid(True, alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig('backtest_performance.png', dpi=300, bbox_inches='tight')
    print(f"📈 Chart saved as: backtest_performance.png")

    # Create detailed analysis
    create_detailed_analysis(results, iterations)

def create_detailed_analysis(results, iterations):
    """Create detailed analysis text"""

    print("\n" + "="*60)
    print("📈 DETAILED PERFORMANCE ANALYSIS")
    print("="*60)

    # Performance assessment
    print("\n🎯 PERFORMANCE ASSESSMENT:")

    for i, result in enumerate(results, 1):
        config = iterations[i]
        actual_return = result['return_17d']
        actual_win_rate = result['win_rate']

        # Parse expected ranges
        exp_return_range = config['expected_return'].replace('%', '').split('-')
        exp_return_min, exp_return_max = float(exp_return_range[0]), float(exp_return_range[1])

        exp_win_rate_range = config['expected_win_rate'].replace('%', '').split('-')
        exp_win_rate_min, exp_win_rate_max = float(exp_win_rate_range[0]), float(exp_win_rate_range[1])

        # Assess performance
        return_status = "✅ MEETS" if exp_return_min <= actual_return <= exp_return_max else "❌ BELOW" if actual_return < exp_return_min else "🚀 EXCEEDS"
        win_rate_status = "✅ MEETS" if exp_win_rate_min <= actual_win_rate <= exp_win_rate_max else "❌ BELOW" if actual_win_rate < exp_win_rate_min else "🚀 EXCEEDS"

        print(f"\n{config['name']}:")
        print(f"  Return: {actual_return:.2f}% (Expected: {config['expected_return']}) {return_status}")
        print(f"  Win Rate: {actual_win_rate:.1f}% (Expected: {config['expected_win_rate']}) {win_rate_status}")
        print(f"  Trades: {result['num_trades']} ({result['trades_per_day']:.2f} per day)")
        print(f"  Sharpe: {result['sharpe']:.2f}")

    # Overall assessment
    print(f"\n🏆 OVERALL ASSESSMENT:")

    total_trades = sum(r['num_trades'] for r in results)
    avg_return = np.mean([r['return_17d'] for r in results])
    avg_win_rate = np.mean([r['win_rate'] for r in results])

    if total_trades > 0:
        print(f"  ✅ Pipeline Status: WORKING")
        print(f"  📊 Total Signals Generated: {total_trades}")
        print(f"  💰 Average Return: {avg_return:.2f}%")
        print(f"  🎯 Average Win Rate: {avg_win_rate:.1f}%")

        if avg_win_rate > 70:
            print(f"  🔥 Win Rate Quality: EXCELLENT")
        elif avg_win_rate > 60:
            print(f"  👍 Win Rate Quality: GOOD")
        else:
            print(f"  ⚠️  Win Rate Quality: NEEDS IMPROVEMENT")

        if avg_return > 5:
            print(f"  💵 Return Quality: EXCELLENT")
        elif avg_return > 2:
            print(f"  💵 Return Quality: GOOD")
        else:
            print(f"  ⚠️  Return Quality: NEEDS IMPROVEMENT")
    else:
        print(f"  ❌ Pipeline Status: NO TRADES GENERATED")

def save_results(results, iterations):
    """Save results to JSON"""

    save_data = {
        'analysis_date': datetime.now().isoformat(),
        'period_days': 17,
        'starting_capital': 1000.0,
        'iterations': []
    }

    for i, result in enumerate(results, 1):
        config = iterations[i]

        iteration_data = {
            'iteration': i,
            'name': config['name'],
            'parameters': {
                'compression': config['compression'],
                'alignment': config['alignment'],
                'confluence': config['confluence'],
                'min_confidence': config['min_confidence'],
                'min_coherence': config['min_coherence']
            },
            'expected': {
                'return': config['expected_return'],
                'win_rate': config['expected_win_rate']
            },
            'actual': {
                'return_17d_pct': round(result['return_17d'], 2),
                'win_rate_pct': round(result['win_rate'], 1),
                'sharpe_ratio': round(result['sharpe'], 3),
                'num_trades': result['num_trades'],
                'trades_per_day': round(result['trades_per_day'], 2)
            }
        }

        save_data['iterations'].append(iteration_data)

    # Save to file
    with open('backtest_analysis_results.json', 'w') as f:
        json.dump(save_data, f, indent=2, default=str)

    print(f"💾 Results saved to: backtest_analysis_results.json")

if __name__ == '__main__':
    run_quick_analysis()