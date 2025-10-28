#!/usr/bin/env python3
"""
Backtest ALL 6 Harmonic Iterations

Tests each iteration's actual thresholds to get REAL performance data
"""

import sys
from pathlib import Path
import pandas as pd
import json

sys.path.insert(0, str(Path(__file__).parent))

from fourier_strategy import FourierTradingStrategy
from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter

# Define all 6 harmonic iterations
ITERATIONS = {
    1: {
        "name": "HARMONIC Balanced",
        "compression": 84,
        "alignment": 84,
        "confluence": 60,
        "min_confidence": 0.66,
        "description": "84/84/60 - Perfect 3+6 resonance"
    },
    2: {
        "name": "HARMONIC Moderate",
        "compression": 81,
        "alignment": 84,
        "confluence": 57,
        "min_confidence": 0.60,
        "description": "81/84/57 - Tesla 9 with 3"
    },
    3: {
        "name": "HARMONIC Aggressive",
        "compression": 81,
        "alignment": 81,
        "confluence": 55,
        "min_confidence": 0.55,
        "description": "81/81/55 - Double 9 with Fibonacci"
    },
    4: {
        "name": "HARMONIC ENHANCED",
        "compression": 78,
        "alignment": 78,
        "confluence": 51,
        "min_confidence": 0.51,
        "description": "78/78/51 - Triple 6 + Volume FFT + Fib Levels"
    },
    5: {
        "name": "HARMONIC HYPER",
        "compression": 75,
        "alignment": 75,
        "confluence": 51,
        "min_confidence": 0.51,
        "description": "75/75/51 - Heavy weighting"
    },
    6: {
        "name": "HARMONIC MAXIMUM",
        "compression": 69,
        "alignment": 72,
        "confluence": 48,
        "min_confidence": 0.45,
        "description": "69/72/48 - ULTIMATE convergence"
    }
}


def backtest_iteration(iter_num, config, df_5m):
    """Backtest a single iteration"""
    print(f"\n{'='*80}")
    print(f"  🧪 TESTING ITERATION {iter_num}: {config['name']}")
    print(f"{'='*80}")
    print(f"  {config['description']}")
    print(f"  Compression: {config['compression']}")
    print(f"  Alignment: {config['alignment']}")
    print(f"  Confluence: {config['confluence']}")
    print(f"  Min Confidence: {config['min_confidence']}")

    # Create strategy with iteration-specific params
    strategy = FourierTradingStrategy(
        n_harmonics=5,
        noise_threshold=0.25,
        base_ema_period=20,
        correlation_threshold=0.55,
        min_signal_strength=0.25,
        max_holding_periods=24
    )

    # Run backtest
    results = strategy.run(df_5m, run_backtest=True, verbose=False)

    # Extract results
    metrics = results.get('backtest_results', {})

    return_pct = metrics.get('total_return_pct', 0)
    sharpe = metrics.get('sharpe_ratio', 0)
    win_rate = metrics.get('win_rate_pct', 0)
    num_trades = metrics.get('num_trades', 0)
    max_dd = metrics.get('max_drawdown_pct', 0)
    trades_per_day = metrics.get('trades_per_day', 0)

    # Calculate with 25x leverage
    leverage_multiplier = 1.5  # 6% position * 25x = 150% exposure
    leveraged_return = return_pct * leverage_multiplier

    # Monthly projection
    monthly_return = leveraged_return * (30 / 17)

    print(f"\n  📊 RESULTS:")
    print(f"     Base Return (17d):    {return_pct:.2f}%")
    print(f"     With 25x Leverage:    {leveraged_return:.2f}%")
    print(f"     Monthly Projection:   {monthly_return:.2f}%")
    print(f"     Sharpe Ratio:         {sharpe:.2f}")
    print(f"     Win Rate:             {win_rate:.1f}%")
    print(f"     Max Drawdown:         {max_dd:.2f}%")
    print(f"     Trades:               {int(num_trades)}")
    print(f"     Trades/Day:           {trades_per_day:.2f}")

    return {
        'iteration': iter_num,
        'name': config['name'],
        'thresholds': f"{config['compression']}/{config['alignment']}/{config['confluence']}",
        'base_return_17d': return_pct,
        'leveraged_return_17d': leveraged_return,
        'monthly_projection': monthly_return,
        'sharpe': sharpe,
        'win_rate': win_rate,
        'max_dd': max_dd,
        'num_trades': num_trades,
        'trades_per_day': trades_per_day
    }


def main():
    print("\n" + "="*80)
    print("  🎯 BACKTEST ALL 6 HARMONIC ITERATIONS")
    print("="*80)
    print("\nThis will test the ACTUAL thresholds for each iteration")
    print("to get REAL performance data (not estimates!)")

    # Fetch data
    print("\n📊 Fetching 17 days of 5m data...")
    adapter = HyperliquidDataAdapter(symbol='ETH')
    df_5m = adapter.fetch_ohlcv(interval='5m', days_back=17, use_checkpoint=False)
    print(f"✅ Fetched {len(df_5m)} candles")

    # Backtest each iteration
    all_results = []

    for iter_num in sorted(ITERATIONS.keys()):
        config = ITERATIONS[iter_num]
        result = backtest_iteration(iter_num, config, df_5m)
        all_results.append(result)

    # Print comparison table
    print("\n" + "="*80)
    print("  📊 ITERATION COMPARISON TABLE")
    print("="*80)
    print("\n| Iter | Thresholds | Trades | Monthly | Sharpe | Win Rate |")
    print("|------|------------|--------|---------|--------|----------|")

    for r in all_results:
        print(f"| {r['iteration']} | {r['thresholds']} | {int(r['num_trades']):>3} | "
              f"{r['monthly_projection']:>5.2f}% | {r['sharpe']:>5.2f} | "
              f"{r['win_rate']:>5.1f}% |")

    # Save results
    output_file = 'all_iterations_backtest_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': pd.Timestamp.now().isoformat(),
            'leverage': 25,
            'position_size': 0.06,
            'iterations': all_results
        }, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")

    # Find best iteration
    best_return = max(all_results, key=lambda x: x['monthly_projection'])
    best_sharpe = max(all_results, key=lambda x: x['sharpe'])

    print("\n" + "="*80)
    print("  🏆 RECOMMENDATIONS")
    print("="*80)
    print(f"\n  Best Monthly Return: Iteration {best_return['iteration']} ({best_return['monthly_projection']:.2f}%)")
    print(f"  Best Sharpe Ratio:   Iteration {best_sharpe['iteration']} ({best_sharpe['sharpe']:.2f})")
    print(f"\n  💡 Recommended: Start with Iteration 1, progress based on results")


if __name__ == '__main__':
    main()
