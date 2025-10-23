#!/usr/bin/env python3
"""
Run Complete Backtest

Tests the trading strategy on historical data and compares to optimal performance.

Usage:
    python3 scripts/run_backtest.py
    python3 scripts/run_backtest.py --timeframe 1h --symbol eth
"""

import sys
from pathlib import Path
import pandas as pd
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategy.entry_detector import EntryDetector
from strategy.exit_manager import ExitManager
from strategy.ribbon_analyzer import RibbonAnalyzer
from backtest.backtest_engine import BacktestEngine
from analysis.optimal_trade_finder import OptimalTradeFinder
from optimization.claude_optimizer import ClaudeOptimizer


def main():
    """Run complete backtest analysis"""
    parser = argparse.ArgumentParser(description='Run trading strategy backtest')
    parser.add_argument('--timeframe', default='1h', help='Timeframe (1m, 3m, 5m, 15m, 30m, 1h)')
    parser.add_argument('--symbol', default='eth', help='Trading symbol')
    parser.add_argument('--save-trades', action='store_true', help='Save trade details to CSV')
    args = parser.parse_args()

    print("="*80)
    print("COMPLETE BACKTEST ANALYSIS")
    print("="*80)
    print(f"Symbol: {args.symbol.upper()}")
    print(f"Timeframe: {args.timeframe}")

    # Load data
    data_file = Path(__file__).parent.parent / 'trading_data' / 'indicators' / f'{args.symbol}_{args.timeframe}_full.csv'

    if not data_file.exists():
        print(f"\n❌ Data file not found: {data_file}")
        print(f"   Run: python3 scripts/process_indicators.py")
        sys.exit(1)

    print(f"\n📊 Loading data: {data_file}")
    df = pd.read_csv(data_file)
    print(f"   Loaded {len(df)} candles")

    # Initialize components
    print("\n🔧 Initializing components...")
    entry_detector = EntryDetector()
    exit_manager = ExitManager()
    ribbon_analyzer = RibbonAnalyzer()
    backtest_engine = BacktestEngine(
        initial_capital=10000,
        commission_pct=0.05,
        slippage_pct=0.02,
        position_size_pct=10.0,
        max_concurrent_trades=3
    )
    optimal_finder = OptimalTradeFinder(min_profit_pct=1.0, max_hold_candles=24)  # 24h = 1 day for 1h timeframe
    optimizer = ClaudeOptimizer()

    # Add ribbon analysis if not present
    if 'compression_score' not in df.columns:
        print("\n🎀 Adding ribbon analysis...")
        df = ribbon_analyzer.analyze_all(df)

    # Run backtest
    print("\n" + "="*80)
    print("STEP 1: RUNNING BACKTEST")
    print("="*80)
    backtest_results = backtest_engine.run_backtest(
        df=df,
        entry_detector=entry_detector,
        exit_manager=exit_manager,
        ribbon_analyzer=None,  # Already added
        verbose=True
    )

    # Find optimal trades
    print("\n" + "="*80)
    print("STEP 2: FINDING OPTIMAL TRADES")
    print("="*80)
    optimal_trades = optimal_finder.scan_all_optimal_trades(df)

    if optimal_trades:
        optimal_analysis = optimal_finder.analyze_optimal_conditions(optimal_trades)

    # Analyze performance gap
    print("\n" + "="*80)
    print("STEP 3: PERFORMANCE GAP ANALYSIS")
    print("="*80)
    gap_analysis = optimizer.analyze_performance_gap(backtest_results, optimal_trades)

    # Generate Claude optimization prompt
    print("\n" + "="*80)
    print("STEP 4: GENERATING OPTIMIZATION PROMPT")
    print("="*80)

    # Load current params
    params_file = Path(__file__).parent.parent / 'src' / 'strategy' / 'strategy_params.json'
    import json
    with open(params_file, 'r') as f:
        current_params = json.load(f)

    prompt = optimizer.generate_optimization_prompt(gap_analysis, current_params['entry_filters'])

    # Save prompt for review
    prompt_file = Path(__file__).parent.parent / 'optimization_logs' / 'latest_optimization_prompt.txt'
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    with open(prompt_file, 'w') as f:
        f.write(prompt)

    print(f"\n💾 Optimization prompt saved: {prompt_file}")
    print("\n📋 NEXT STEPS:")
    print("   1. Review the optimization prompt above")
    print("   2. Send it to Claude API for suggestions")
    print("   3. Apply suggested changes to strategy_params.json")
    print("   4. Re-run backtest to validate improvements")

    # Save results
    if args.save_trades:
        # Save backtest trades
        if backtest_results['trades']:
            trades_df = pd.DataFrame([
                {
                    'entry_time': t['entry_time'],
                    'direction': t['direction'],
                    'entry_price': t['entry_price'],
                    'total_pnl_usd': t['total_pnl_usd'],
                    'total_pnl_pct': t['total_pnl_pct'],
                    'mfe': t['mfe'],
                    'mae': t['mae'],
                    'confidence': t['confidence']
                }
                for t in backtest_results['trades']
            ])

            trades_file = Path(__file__).parent.parent / 'trading_data' / 'backtest' / f'{args.symbol}_{args.timeframe}_backtest_trades.csv'
            trades_file.parent.mkdir(parents=True, exist_ok=True)
            trades_df.to_csv(trades_file, index=False)
            print(f"\n💾 Backtest trades saved: {trades_file}")

        # Save optimal trades
        optimal_file = Path(__file__).parent.parent / 'trading_data' / 'backtest' / f'{args.symbol}_{args.timeframe}_optimal_trades.csv'
        optimal_finder.save_optimal_trades(optimal_trades, str(optimal_file))

    # Save optimization log
    optimizer.save_optimization_log(gap_analysis, current_params['entry_filters'])

    print("\n" + "="*80)
    print("✅ BACKTEST ANALYSIS COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
