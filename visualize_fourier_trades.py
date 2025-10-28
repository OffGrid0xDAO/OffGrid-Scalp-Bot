#!/usr/bin/env python3
"""
Visualize Fourier Strategy Trades with ChartGenerator

Integrates Fourier strategy with existing professional chart infrastructure.
Shows buy/sell markers, indicators, and performance analysis.
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

print("=" * 70)
print("FOURIER STRATEGY VISUALIZATION WITH CHARTGENERATOR")
print("=" * 70)

# Step 1: Fetch data and run Fourier strategy
print("\n1. Fetching data from Hyperliquid...")
adapter = HyperliquidDataAdapter(symbol='ETH')
df = adapter.fetch_ohlcv(interval='1h', days_back=50, use_checkpoint=False)

print(f"\n✅ Fetched {len(df)} candles")
print(f"   Period: {df.index[0]} to {df.index[-1]}")

# Step 2: Run Fourier strategy
print("\n2. Running Fourier strategy...")
strategy = FourierTradingStrategy(
    n_harmonics=5,
    noise_threshold=0.3,
    base_ema_period=28,
    correlation_threshold=0.6,
    min_signal_strength=0.3,
    max_holding_periods=168,
    initial_capital=10000.0,
    commission=0.001
)

results = strategy.run(df, run_backtest=True, verbose=False)
output_df = results['output_df']
trade_log = results['trade_log']

print(f"\n✅ Strategy completed")
print(f"   Trades: {len(trade_log)}")
print(f"   Final Capital: ${results['metrics']['final_capital']:,.2f}")
print(f"   Total Return: {results['metrics']['total_return_pct']:.2f}%")

# Step 3: Prepare data for ChartGenerator
print("\n3. Preparing data for ChartGenerator...")

# Add timestamp column
output_df['timestamp'] = pd.to_datetime(output_df.index)

# Add Bollinger Bands (20-period, 2 std dev)
output_df['bb_middle'] = output_df['close'].rolling(window=20).mean()
bb_std = output_df['close'].rolling(window=20).std()
output_df['bb_upper'] = output_df['bb_middle'] + (bb_std * 2)
output_df['bb_lower'] = output_df['bb_middle'] - (bb_std * 2)

# Add VWAP
typical_price = (output_df['high'] + output_df['low'] + output_df['close']) / 3
output_df['vwap'] = (typical_price * output_df['volume']).cumsum() / output_df['volume'].cumsum()

# Rename Fourier indicators to ChartGenerator format
output_df['rsi_14'] = output_df['rsi_filtered']
output_df['stoch_k'] = output_df['stoch_k_filtered']
output_df['stoch_d'] = output_df['stoch_d_filtered']

# Convert composite signal to confluence scores
# Positive signal = long score, negative signal = short score
# Scale from [-1, 1] to [0, 100]
output_df['confluence_score_long'] = output_df['composite_signal'].apply(
    lambda x: max(0, x * 100) if x > 0 else 0
)
output_df['confluence_score_short'] = output_df['composite_signal'].apply(
    lambda x: abs(min(0, x * 100)) if x < 0 else 0
)

# Add volume status for coloring
volume_ma = output_df['volume'].rolling(window=20).mean()
volume_std = output_df['volume'].rolling(window=20).std()
output_df['volume_status'] = 'normal'
output_df.loc[output_df['volume'] > volume_ma + (2 * volume_std), 'volume_status'] = 'spike'
output_df.loc[output_df['volume'] > volume_ma + volume_std, 'volume_status'] = 'elevated'
output_df.loc[output_df['volume'] < volume_ma - volume_std, 'volume_status'] = 'low'

print(f"   ✅ Added indicators: BB, VWAP, RSI, Stoch, Confluence")

# Step 4: Convert Fourier trades to ChartGenerator format
print("\n4. Converting trades to ChartGenerator format...")

backtest_trades = []

for idx, trade in trade_log.iterrows():
    # Find entry and exit indices in the dataframe
    entry_time = pd.to_datetime(trade['entry_time'])
    exit_time = pd.to_datetime(trade['exit_time'])

    # Get index positions
    try:
        entry_idx = output_df.index.get_loc(entry_time)
        exit_idx = output_df.index.get_loc(exit_time)

        # Calculate TP/SL levels based on risk/reward ratio
        # Use 2% stop loss and 4% take profit (1:2 risk/reward)
        direction = trade['direction'].lower()
        entry_price = trade['entry_price']

        if direction == 'long':
            # For long: SL below entry, TP above entry
            sl_price = entry_price * 0.98  # 2% below
            tp_price = entry_price * 1.04  # 4% above
        else:
            # For short: SL above entry, TP below entry
            sl_price = entry_price * 1.02  # 2% above
            tp_price = entry_price * 0.96  # 4% below

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
        print(f"   ⚠️  Could not find index for trade: {e}")
        continue

print(f"   ✅ Converted {len(backtest_trades)} trades")

# Step 5: Generate chart
print("\n5. Generating interactive chart...")

generator = ChartGenerator(output_dir='charts/fourier')

chart_path = generator.create_3way_comparison_chart(
    df=output_df,
    optimal_trades=[],  # No optimal trades for now
    backtest_trades=backtest_trades,
    actual_trades=[],  # No live trades yet
    timeframe='1h',
    symbol='ETH',
    candles_to_show=1000  # Show last 1000 candles (more data to analyze)
)

print(f"\n✅ Chart generated: {chart_path}")

# Step 6: Show summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\n📊 Performance:")
print(f"   Total Return:     {results['metrics']['total_return_pct']:.2f}%")
print(f"   Sharpe Ratio:     {results['metrics']['sharpe_ratio']:.2f}")
print(f"   Max Drawdown:     {results['metrics']['max_drawdown_pct']:.2f}%")
print(f"   Win Rate:         {results['metrics']['win_rate_pct']:.2f}%")
print(f"   Profit Factor:    {results['metrics']['profit_factor']:.2f}")
print(f"   Number of Trades: {results['metrics']['num_trades']}")

print(f"\n📈 Chart Location:")
print(f"   {chart_path}")

print(f"\n💡 Next Steps:")
print(f"   1. Open the HTML chart in your browser")
print(f"   2. Inspect buy/sell markers on price chart")
print(f"   3. Analyze confluence scores and indicators")
print(f"   4. Review performance metrics")

print("\n" + "=" * 70)
print("COMPLETE!")
print("=" * 70)
