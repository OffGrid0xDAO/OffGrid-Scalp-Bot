#!/usr/bin/env python3
"""
Manual Scalping Optimization

Tunes the Fourier strategy for SCALPING instead of swing trading:
- Shorter timeframes (5m instead of 1h)
- Lower signal thresholds (more trades)
- Shorter holding periods (quick in/out)
- Tighter TP/SL levels

Tests multiple configurations to find the best scalping setup!
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fourier_strategy import FourierTradingStrategy
from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter
from src.reporting.chart_generator import ChartGenerator


def print_header(title):
    """Print header"""
    print("\n" + "╔" + "═"*78 + "╗")
    print("║" + f" {title:^76} " + "║")
    print("╚" + "═"*78 + "╝")


def print_section(title):
    """Print section"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def test_scalping_config(df, config_name, params):
    """Test a scalping configuration"""
    print(f"\n🔬 Testing: {config_name}")
    print(f"   Timeframe: {params['timeframe']}")
    print(f"   Signal threshold: {params['min_signal_strength']}")
    print(f"   Max holding: {params['max_holding_periods']} periods")

    strategy = FourierTradingStrategy(
        n_harmonics=params['n_harmonics'],
        noise_threshold=params['noise_threshold'],
        base_ema_period=params['base_ema_period'],
        correlation_threshold=params['correlation_threshold'],
        min_signal_strength=params['min_signal_strength'],
        max_holding_periods=params['max_holding_periods'],
        initial_capital=10000.0,
        commission=0.001
    )

    results = strategy.run(df, run_backtest=True, verbose=False)
    metrics = results['metrics']

    print(f"\n   ✅ Results:")
    print(f"      Return:        {metrics['total_return_pct']:>8.2f}%")
    print(f"      Sharpe:        {metrics['sharpe_ratio']:>8.2f}")
    print(f"      Max DD:        {metrics['max_drawdown_pct']:>8.2f}%")
    print(f"      Win Rate:      {metrics['win_rate_pct']:>8.2f}%")
    print(f"      Profit Factor: {metrics['profit_factor']:>8.2f}")
    print(f"      Trades:        {metrics['num_trades']:>8}")

    # Calculate trades per day
    days = len(df) / (1440 / params.get('minutes_per_candle', 60))
    trades_per_day = metrics['num_trades'] / days if days > 0 else 0
    print(f"      Trades/day:    {trades_per_day:>8.1f}")

    return {
        'name': config_name,
        'params': params,
        'metrics': metrics,
        'results': results,
        'trades_per_day': trades_per_day
    }


def main():
    """Main scalping optimization"""
    print_header("MANUAL SCALPING OPTIMIZATION")

    print_section("📊 Fetching Scalping Timeframe Data")

    # Fetch SHORTER timeframe for scalping (5m instead of 1h)
    print("\n⚡ Fetching 5-minute data (better for scalping)...")
    adapter = HyperliquidDataAdapter(symbol='ETH')

    # Get 7 days of 5m data (2016 candles)
    df_5m = adapter.fetch_ohlcv(interval='5m', days_back=7, use_checkpoint=False)
    print(f"✅ Fetched {len(df_5m)} candles of 5m data")

    print_section("🎯 SCALPING CONFIGURATIONS TO TEST")

    # Define different scalping configurations
    configs = {
        'Ultra Aggressive': {
            'timeframe': '5m',
            'minutes_per_candle': 5,
            'n_harmonics': 3,                  # Fewer harmonics = more responsive
            'noise_threshold': 0.2,            # Less filtering = more signals
            'base_ema_period': 14,             # Shorter EMA = faster
            'correlation_threshold': 0.5,      # Lower = more trades
            'min_signal_strength': 0.2,        # Lower = more trades
            'max_holding_periods': 12          # 1 hour max (12 x 5min)
        },
        'Aggressive': {
            'timeframe': '5m',
            'minutes_per_candle': 5,
            'n_harmonics': 5,
            'noise_threshold': 0.25,
            'base_ema_period': 20,
            'correlation_threshold': 0.55,
            'min_signal_strength': 0.25,
            'max_holding_periods': 24          # 2 hours max
        },
        'Moderate Scalping': {
            'timeframe': '5m',
            'minutes_per_candle': 5,
            'n_harmonics': 5,
            'noise_threshold': 0.3,
            'base_ema_period': 28,
            'correlation_threshold': 0.6,
            'min_signal_strength': 0.3,
            'max_holding_periods': 36          # 3 hours max
        },
        'Conservative Scalping': {
            'timeframe': '5m',
            'minutes_per_candle': 5,
            'n_harmonics': 7,                  # More smoothing
            'noise_threshold': 0.35,           # More filtering
            'base_ema_period': 28,
            'correlation_threshold': 0.65,
            'min_signal_strength': 0.35,
            'max_holding_periods': 48          # 4 hours max
        }
    }

    # Test all configurations
    results = []
    for name, params in configs.items():
        result = test_scalping_config(df_5m, name, params)
        results.append(result)

    print_section("📊 SCALPING CONFIGURATION COMPARISON")

    # Create comparison table
    print(f"\n{'Configuration':<22} {'Return':>8} {'Sharpe':>8} {'Win%':>8} {'Trades':>8} {'T/Day':>8}")
    print("="*70)

    for result in results:
        m = result['metrics']
        print(f"{result['name']:<22} "
              f"{m['total_return_pct']:>8.2f}% "
              f"{m['sharpe_ratio']:>8.2f} "
              f"{m['win_rate_pct']:>8.2f}% "
              f"{m['num_trades']:>8} "
              f"{result['trades_per_day']:>8.1f}")

    # Find best configuration by different metrics
    print_section("🏆 BEST CONFIGURATIONS")

    best_return = max(results, key=lambda x: x['metrics']['total_return_pct'])
    best_sharpe = max(results, key=lambda x: x['metrics']['sharpe_ratio'])
    best_trades = max(results, key=lambda x: x['metrics']['num_trades'])
    best_winrate = max(results, key=lambda x: x['metrics']['win_rate_pct'])

    print(f"\n💰 Best Return:       {best_return['name']:<25} {best_return['metrics']['total_return_pct']:.2f}%")
    print(f"📈 Best Sharpe:       {best_sharpe['name']:<25} {best_sharpe['metrics']['sharpe_ratio']:.2f}")
    print(f"⚡ Most Trades:       {best_trades['name']:<25} {best_trades['metrics']['num_trades']} trades ({best_trades['trades_per_day']:.1f}/day)")
    print(f"🎯 Best Win Rate:     {best_winrate['name']:<25} {best_winrate['metrics']['win_rate_pct']:.2f}%")

    # Recommend best overall
    print_section("💡 RECOMMENDATION FOR SCALPING")

    # Score each config (weighted)
    for result in results:
        m = result['metrics']
        # Scalping score: prioritize trades/day and win rate
        score = (
            (result['trades_per_day'] / 10) * 0.3 +  # 30% weight on trade frequency
            (m['win_rate_pct'] / 100) * 0.3 +        # 30% weight on win rate
            (m['sharpe_ratio'] / 3) * 0.25 +         # 25% weight on Sharpe
            (m['total_return_pct'] / 10) * 0.15      # 15% weight on return
        )
        result['scalping_score'] = score

    best_overall = max(results, key=lambda x: x['scalping_score'])

    print(f"\n🏆 BEST OVERALL SCALPING SETUP: {best_overall['name']}")
    print(f"\n   Scalping Score: {best_overall['scalping_score']:.3f}")
    print(f"\n   📊 Performance:")
    print(f"      Return:        {best_overall['metrics']['total_return_pct']:.2f}%")
    print(f"      Sharpe:        {best_overall['metrics']['sharpe_ratio']:.2f}")
    print(f"      Win Rate:      {best_overall['metrics']['win_rate_pct']:.2f}%")
    print(f"      Trades:        {best_overall['metrics']['num_trades']}")
    print(f"      Trades/day:    {best_overall['trades_per_day']:.1f}")
    print(f"      Max Drawdown:  {best_overall['metrics']['max_drawdown_pct']:.2f}%")

    print(f"\n   ⚙️  Parameters:")
    for key, value in best_overall['params'].items():
        if key not in ['timeframe', 'minutes_per_candle']:
            print(f"      {key:<25} {value}")

    # Generate chart for best config
    print_section("📈 Generating Chart for Best Configuration")

    print(f"\nGenerating chart for: {best_overall['name']}")

    # Prepare data for chart
    output_df = best_overall['results']['output_df']
    trade_log = best_overall['results']['trade_log']

    # Add required columns for chart
    output_df['timestamp'] = pd.to_datetime(output_df.index)

    # Add Bollinger Bands
    output_df['bb_middle'] = output_df['close'].rolling(window=20).mean()
    bb_std = output_df['close'].rolling(window=20).std()
    output_df['bb_upper'] = output_df['bb_middle'] + (bb_std * 2)
    output_df['bb_lower'] = output_df['bb_middle'] - (bb_std * 2)

    # Add VWAP
    typical_price = (output_df['high'] + output_df['low'] + output_df['close']) / 3
    output_df['vwap'] = (typical_price * output_df['volume']).cumsum() / output_df['volume'].cumsum()

    # Rename indicators
    output_df['rsi_14'] = output_df['rsi_filtered']
    output_df['stoch_k'] = output_df['stoch_k_filtered']
    output_df['stoch_d'] = output_df['stoch_d_filtered']

    # Confluence scores
    output_df['confluence_score_long'] = output_df['composite_signal'].apply(
        lambda x: max(0, x * 100) if x > 0 else 0
    )
    output_df['confluence_score_short'] = output_df['composite_signal'].apply(
        lambda x: abs(min(0, x * 100)) if x < 0 else 0
    )

    # Volume status
    volume_ma = output_df['volume'].rolling(window=20).mean()
    volume_std = output_df['volume'].rolling(window=20).std()
    output_df['volume_status'] = 'normal'
    output_df.loc[output_df['volume'] > volume_ma + (2 * volume_std), 'volume_status'] = 'spike'
    output_df.loc[output_df['volume'] > volume_ma + volume_std, 'volume_status'] = 'elevated'
    output_df.loc[output_df['volume'] < volume_ma - volume_std, 'volume_status'] = 'low'

    # Convert trades to chart format
    backtest_trades = []
    for idx, trade in trade_log.iterrows():
        entry_time = pd.to_datetime(trade['entry_time'])
        exit_time = pd.to_datetime(trade['exit_time'])

        try:
            entry_idx = output_df.index.get_loc(entry_time)
            exit_idx = output_df.index.get_loc(exit_time)

            direction = trade['direction'].lower()
            entry_price = trade['entry_price']

            # Scalping TP/SL (tighter: 1% SL, 2% TP)
            if direction == 'long':
                sl_price = entry_price * 0.99  # 1% SL
                tp_price = entry_price * 1.02  # 2% TP
            else:
                sl_price = entry_price * 1.01
                tp_price = entry_price * 0.98

            backtest_trades.append({
                'entry_idx': entry_idx,
                'entry_price': entry_price,
                'direction': direction,
                'entry_time': entry_time,
                'total_pnl_pct': trade['pnl_pct'],
                'tp_price': tp_price,
                'sl_price': sl_price,
                'partial_exits': [{
                    'exit_idx': exit_idx,
                    'exit_price': trade['exit_price'],
                    'exit_type': 'signal',
                    'exit_time': exit_time
                }]
            })
        except Exception as e:
            continue

    # Generate chart
    generator = ChartGenerator(output_dir='charts/scalping')
    chart_path = generator.create_3way_comparison_chart(
        df=output_df,
        optimal_trades=[],
        backtest_trades=backtest_trades,
        actual_trades=[],
        timeframe='5m',
        symbol='ETH',
        candles_to_show=1000
    )

    print(f"\n✅ Chart saved: {chart_path}")

    # Save parameters to file
    params_file = Path('scalping_best_params.json')
    import json
    with open(params_file, 'w') as f:
        json.dump({
            'configuration': best_overall['name'],
            'scalping_score': best_overall['scalping_score'],
            'parameters': best_overall['params'],
            'performance': {
                'return_pct': best_overall['metrics']['total_return_pct'],
                'sharpe_ratio': best_overall['metrics']['sharpe_ratio'],
                'win_rate_pct': best_overall['metrics']['win_rate_pct'],
                'num_trades': best_overall['metrics']['num_trades'],
                'trades_per_day': best_overall['trades_per_day'],
                'max_drawdown_pct': best_overall['metrics']['max_drawdown_pct']
            }
        }, f, indent=2)

    print(f"\n💾 Best parameters saved to: {params_file}")

    print_section("✅ SCALPING OPTIMIZATION COMPLETE")

    print(f"\n📊 Summary:")
    print(f"   Tested {len(configs)} scalping configurations")
    print(f"   Best setup: {best_overall['name']}")
    print(f"   Trades per day: {best_overall['trades_per_day']:.1f}")
    print(f"   Win rate: {best_overall['metrics']['win_rate_pct']:.2f}%")
    print(f"\n🚀 Next Steps:")
    print(f"   1. Review the chart: {chart_path}")
    print(f"   2. Check parameters: scalping_best_params.json")
    print(f"   3. Run Claude optimization with these as baseline")
    print(f"   4. Test on live data before trading!")

    print(f"\n💡 To use these parameters in your strategy:")
    print(f"   strategy = FourierTradingStrategy(")
    for key, value in best_overall['params'].items():
        if key not in ['timeframe', 'minutes_per_candle']:
            print(f"       {key}={value},")
    print(f"   )")

    return best_overall


if __name__ == '__main__':
    best_config = main()
    print(f"\n🎉 Ready to scalp! Your optimal config is saved.\n")
