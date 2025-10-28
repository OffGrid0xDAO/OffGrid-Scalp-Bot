#!/usr/bin/env python3
"""
Fourier Strategy Iterative Optimizer with Claude AI

Continuously improves the Fourier strategy by:
1. Running backtests with current parameters
2. Analyzing performance and generating charts
3. Using Claude AI to suggest improvements
4. Validating improvements before applying
5. Logging all iterations for comparison

This creates a feedback loop that makes the strategy better over time!
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Tuple
import os

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fourier_strategy import FourierTradingStrategy
from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter
from src.reporting.chart_generator import ChartGenerator


class FourierIterativeOptimizer:
    """
    Iterative optimizer for Fourier Trading Strategy

    Uses Claude AI to analyze performance and suggest improvements
    """

    def __init__(self,
                 symbol: str = 'ETH',
                 initial_capital: float = 10000.0,
                 iterations_dir: str = None):
        """
        Initialize optimizer

        Args:
            symbol: Trading symbol
            initial_capital: Starting capital for backtests
            iterations_dir: Directory to save iteration results
        """
        self.symbol = symbol
        self.initial_capital = initial_capital

        if iterations_dir is None:
            iterations_dir = Path(__file__).parent / 'trading_data' / 'fourier_iterations'

        self.iterations_dir = Path(iterations_dir)
        self.iterations_dir.mkdir(parents=True, exist_ok=True)

        # Load iterations log
        self.log_file = self.iterations_dir / 'iterations_log.json'
        self.iterations_history = self._load_iterations_log()

        # Get next iteration number
        self.current_iteration = len(self.iterations_history) + 1

        # Default baseline parameters (from your current best)
        self.current_params = {
            'n_harmonics': 5,
            'noise_threshold': 0.3,
            'base_ema_period': 28,
            'correlation_threshold': 0.6,
            'min_signal_strength': 0.3,
            'max_holding_periods': 168,
            'initial_capital': initial_capital,
            'commission': 0.001
        }

    def _load_iterations_log(self) -> List[Dict]:
        """Load iterations log from file"""
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def _save_iterations_log(self):
        """Save iterations log to file"""
        with open(self.log_file, 'w') as f:
            json.dump(self.iterations_history, f, indent=2, default=str)

        # Also save CSV summary
        summary_file = self.iterations_dir / 'optimization_summary.csv'
        summary_data = []
        for iteration in self.iterations_history:
            summary_data.append({
                'Iteration': iteration['iteration_name'],
                'Return (%)': iteration['metrics'].get('total_return_pct', 'N/A'),
                'Sharpe': iteration['metrics'].get('sharpe_ratio', 'N/A'),
                'Max DD (%)': iteration['metrics'].get('max_drawdown_pct', 'N/A'),
                'Win Rate (%)': iteration['metrics'].get('win_rate_pct', 'N/A'),
                'Profit Factor': iteration['metrics'].get('profit_factor', 'N/A'),
                'Trades': iteration['metrics'].get('num_trades', 0)
            })

        pd.DataFrame(summary_data).to_csv(summary_file, index=False)
        print(f"   💾 Summary saved: {summary_file}")

    def run_iteration(self,
                     days_back: int = 50,
                     candles_to_show: int = 1000,
                     verbose: bool = True) -> Dict:
        """
        Run one optimization iteration

        Args:
            days_back: Days of historical data to fetch
            candles_to_show: Number of candles to show on chart
            verbose: Print progress

        Returns:
            dict with iteration results
        """
        iteration_name = f"iteration_{self.current_iteration:02d}"
        iteration_dir = self.iterations_dir / iteration_name
        iteration_dir.mkdir(parents=True, exist_ok=True)

        if verbose:
            print("\n" + "="*80)
            print(f"🚀 ITERATION {self.current_iteration}: {iteration_name}")
            print("="*80)

        # Step 1: Fetch data
        if verbose:
            print(f"\n1️⃣  Fetching {days_back} days of {self.symbol} data...")

        adapter = HyperliquidDataAdapter(symbol=self.symbol)
        df = adapter.fetch_ohlcv(interval='1h', days_back=days_back, use_checkpoint=False)

        if verbose:
            print(f"   ✅ Fetched {len(df)} candles ({df.index[0]} to {df.index[-1]})")

        # Step 2: Run strategy with current parameters
        if verbose:
            print(f"\n2️⃣  Running Fourier strategy with current parameters...")
            print(f"   Parameters: {json.dumps(self.current_params, indent=6)}")

        strategy = FourierTradingStrategy(**self.current_params)
        results = strategy.run(df, run_backtest=True, verbose=False)

        output_df = results['output_df']
        trade_log = results['trade_log']
        metrics = results['metrics']

        if verbose:
            print(f"\n   ✅ Strategy completed:")
            print(f"      Total Return:     {metrics['total_return_pct']:.2f}%")
            print(f"      Sharpe Ratio:     {metrics['sharpe_ratio']:.2f}")
            print(f"      Max Drawdown:     {metrics['max_drawdown_pct']:.2f}%")
            print(f"      Win Rate:         {metrics['win_rate_pct']:.2f}%")
            print(f"      Profit Factor:    {metrics['profit_factor']:.2f}")
            print(f"      Number of Trades: {metrics['num_trades']}")

        # Step 3: Prepare data for visualization
        if verbose:
            print(f"\n3️⃣  Preparing visualization data...")

        output_df['timestamp'] = pd.to_datetime(output_df.index)

        # Add indicators for charting
        output_df['bb_middle'] = output_df['close'].rolling(window=20).mean()
        bb_std = output_df['close'].rolling(window=20).std()
        output_df['bb_upper'] = output_df['bb_middle'] + (bb_std * 2)
        output_df['bb_lower'] = output_df['bb_middle'] - (bb_std * 2)

        typical_price = (output_df['high'] + output_df['low'] + output_df['close']) / 3
        output_df['vwap'] = (typical_price * output_df['volume']).cumsum() / output_df['volume'].cumsum()

        output_df['rsi_14'] = output_df['rsi_filtered']
        output_df['stoch_k'] = output_df['stoch_k_filtered']
        output_df['stoch_d'] = output_df['stoch_d_filtered']

        output_df['confluence_score_long'] = output_df['composite_signal'].apply(
            lambda x: max(0, x * 100) if x > 0 else 0
        )
        output_df['confluence_score_short'] = output_df['composite_signal'].apply(
            lambda x: abs(min(0, x * 100)) if x < 0 else 0
        )

        volume_ma = output_df['volume'].rolling(window=20).mean()
        volume_std = output_df['volume'].rolling(window=20).std()
        output_df['volume_status'] = 'normal'
        output_df.loc[output_df['volume'] > volume_ma + (2 * volume_std), 'volume_status'] = 'spike'
        output_df.loc[output_df['volume'] > volume_ma + volume_std, 'volume_status'] = 'elevated'
        output_df.loc[output_df['volume'] < volume_ma - volume_std, 'volume_status'] = 'low'

        # Step 4: Convert trades to chart format with TP/SL zones
        if verbose:
            print(f"\n4️⃣  Converting {len(trade_log)} trades to chart format...")

        backtest_trades = []
        for idx, trade in trade_log.iterrows():
            entry_time = pd.to_datetime(trade['entry_time'])
            exit_time = pd.to_datetime(trade['exit_time'])

            try:
                entry_idx = output_df.index.get_loc(entry_time)
                exit_idx = output_df.index.get_loc(exit_time)

                direction = trade['direction'].lower()
                entry_price = trade['entry_price']

                # Calculate TP/SL (2% SL, 4% TP for 1:2 risk/reward)
                if direction == 'long':
                    sl_price = entry_price * 0.98
                    tp_price = entry_price * 1.04
                else:
                    sl_price = entry_price * 1.02
                    tp_price = entry_price * 0.96

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
                if verbose:
                    print(f"   ⚠️  Could not process trade: {e}")
                continue

        # Step 5: Generate chart
        if verbose:
            print(f"\n5️⃣  Generating interactive chart...")

        generator = ChartGenerator(output_dir=str(iteration_dir / 'charts'))
        chart_path = generator.create_3way_comparison_chart(
            df=output_df,
            optimal_trades=[],
            backtest_trades=backtest_trades,
            actual_trades=[],
            timeframe='1h',
            symbol=self.symbol,
            candles_to_show=candles_to_show
        )

        if verbose:
            print(f"   ✅ Chart saved: {chart_path}")

        # Step 6: Save iteration results
        if verbose:
            print(f"\n6️⃣  Saving iteration results...")

        # Save trade log
        trade_log_path = iteration_dir / 'trade_log.csv'
        trade_log.to_csv(trade_log_path, index=False)

        # Save full results
        results_path = iteration_dir / 'results.csv'
        output_df.to_csv(results_path)

        # Save metadata
        metadata = {
            'iteration_name': iteration_name,
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'days_back': days_back,
            'data_points': len(df),
            'parameters': self.current_params.copy(),
            'metrics': {k: float(v) if isinstance(v, (int, float, np.number)) else str(v)
                       for k, v in metrics.items()},
            'output_path': str(iteration_dir),
            'chart_path': str(chart_path)
        }

        metadata_path = iteration_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        if verbose:
            print(f"   ✅ Results saved to: {iteration_dir}")

        # Step 7: Add to history
        self.iterations_history.append(metadata)
        self._save_iterations_log()

        if verbose:
            print(f"\n✅ Iteration {self.current_iteration} complete!")

        return {
            'iteration_name': iteration_name,
            'iteration_dir': iteration_dir,
            'chart_path': chart_path,
            'metadata': metadata,
            'metrics': metrics,
            'trade_log': trade_log
        }

    def generate_claude_analysis_prompt(self, iteration_result: Dict) -> str:
        """
        Generate prompt for Claude AI analysis

        Args:
            iteration_result: Results from run_iteration

        Returns:
            str: Prompt for Claude
        """
        metrics = iteration_result['metrics']
        params = self.current_params

        # Get comparison with previous iteration if exists
        comparison_text = ""
        if len(self.iterations_history) > 1:
            prev_metrics = self.iterations_history[-2]['metrics']
            comparison_text = f"""
## Comparison with Previous Iteration

| Metric | Previous | Current | Change |
|--------|----------|---------|--------|
| Return | {prev_metrics.get('total_return_pct', 0):.2f}% | {metrics['total_return_pct']:.2f}% | {metrics['total_return_pct'] - prev_metrics.get('total_return_pct', 0):.2f}% |
| Sharpe | {prev_metrics.get('sharpe_ratio', 0):.2f} | {metrics['sharpe_ratio']:.2f} | {metrics['sharpe_ratio'] - prev_metrics.get('sharpe_ratio', 0):.2f} |
| Win Rate | {prev_metrics.get('win_rate_pct', 0):.2f}% | {metrics['win_rate_pct']:.2f}% | {metrics['win_rate_pct'] - prev_metrics.get('win_rate_pct', 0):.2f}% |
| Trades | {prev_metrics.get('num_trades', 0)} | {metrics['num_trades']} | {metrics['num_trades'] - prev_metrics.get('num_trades', 0)} |
"""

        prompt = f"""# Fourier Trading Strategy Optimization - Iteration {self.current_iteration}

I'm optimizing a Fourier Transform-based cryptocurrency trading strategy. I need your help analyzing the current performance and suggesting parameter improvements.

## Current Performance Metrics

- **Total Return:** {metrics['total_return_pct']:.2f}%
- **Sharpe Ratio:** {metrics['sharpe_ratio']:.2f}
- **Max Drawdown:** {metrics['max_drawdown_pct']:.2f}%
- **Win Rate:** {metrics['win_rate_pct']:.2f}%
- **Profit Factor:** {metrics['profit_factor']:.2f}
- **Number of Trades:** {metrics['num_trades']}
- **Average Win:** ${metrics['avg_win']:.2f}
- **Average Loss:** ${metrics['avg_loss']:.2f}
{comparison_text}

## Current Strategy Parameters

```json
{json.dumps(params, indent=2)}
```

## Parameter Descriptions

- **n_harmonics** (3-11): Number of Fourier harmonics to use for filtering noise. Higher = smoother but more lag.
- **noise_threshold** (0.1-0.5): Threshold for removing noise components. Higher = more aggressive filtering.
- **base_ema_period** (14-50): Base EMA period for trend detection. Higher = longer-term trends.
- **correlation_threshold** (0.5-0.9): Minimum correlation between indicators to generate signal. Higher = more strict.
- **min_signal_strength** (0.2-0.8): Minimum signal strength required for entry. Higher = fewer but stronger signals.
- **max_holding_periods** (24-336): Maximum hours to hold a position (1 day to 2 weeks).

## Analysis Request

Please analyze these results and suggest specific parameter changes to improve:

1. **Sharpe Ratio** - Better risk-adjusted returns
2. **Win Rate** - More accurate entry signals
3. **Profit Factor** - Better win/loss ratio
4. **Drawdown** - Reduced maximum drawdown

Provide your response in this EXACT JSON format (no extra text):

```json
{{
  "analysis": "Brief analysis of current performance (2-3 sentences)",
  "suggested_changes": {{
    "n_harmonics": <number 3-11>,
    "noise_threshold": <number 0.1-0.5>,
    "base_ema_period": <number 14-50>,
    "correlation_threshold": <number 0.5-0.9>,
    "min_signal_strength": <number 0.2-0.8>,
    "max_holding_periods": <number 24-336>
  }},
  "reasoning": "Detailed explanation of why these changes should improve performance (3-5 sentences)",
  "expected_improvements": {{
    "sharpe_ratio": "expected change",
    "win_rate": "expected change",
    "profit_factor": "expected change"
  }}
}}
```

**Important:** Only output the JSON, nothing else.
"""

        return prompt

    def compare_iterations(self, n: int = 5) -> pd.DataFrame:
        """
        Compare last N iterations

        Args:
            n: Number of iterations to compare

        Returns:
            DataFrame with comparison
        """
        recent_iterations = self.iterations_history[-n:]

        comparison_data = []
        for iteration in recent_iterations:
            metrics = iteration['metrics']
            params = iteration['parameters']

            comparison_data.append({
                'Iteration': iteration['iteration_name'],
                'Return (%)': metrics.get('total_return_pct', 0),
                'Sharpe': metrics.get('sharpe_ratio', 0),
                'Max DD (%)': metrics.get('max_drawdown_pct', 0),
                'Win Rate (%)': metrics.get('win_rate_pct', 0),
                'Profit Factor': metrics.get('profit_factor', 0),
                'Trades': metrics.get('num_trades', 0),
                'n_harmonics': params.get('n_harmonics', 0),
                'noise_threshold': params.get('noise_threshold', 0),
                'correlation_threshold': params.get('correlation_threshold', 0),
                'min_signal_strength': params.get('min_signal_strength', 0)
            })

        return pd.DataFrame(comparison_data)


if __name__ == '__main__':
    """Test run of optimizer"""
    print("\n" + "╔" + "═"*78 + "╗")
    print("║" + " "*20 + "FOURIER ITERATIVE OPTIMIZER" + " "*31 + "║")
    print("╚" + "═"*78 + "╝\n")

    # Initialize optimizer
    optimizer = FourierIterativeOptimizer(symbol='ETH', initial_capital=10000.0)

    print(f"📊 Current iteration: {optimizer.current_iteration}")
    print(f"📁 Iterations directory: {optimizer.iterations_dir}")
    print(f"📈 Previous iterations: {len(optimizer.iterations_history)}")

    # Run one iteration
    result = optimizer.run_iteration(days_back=50, candles_to_show=1000, verbose=True)

    print("\n" + "="*80)
    print("CLAUDE AI ANALYSIS PROMPT")
    print("="*80)

    # Generate Claude prompt
    prompt = optimizer.generate_claude_analysis_prompt(result)
    print(prompt)

    print("\n" + "="*80)
    print("ITERATIONS COMPARISON")
    print("="*80)

    # Compare recent iterations
    if len(optimizer.iterations_history) > 1:
        comparison = optimizer.compare_iterations(n=5)
        print(comparison.to_string(index=False))

    print("\n✅ Optimizer ready! Use this with Claude AI to improve the strategy.")
    print(f"\n📊 View chart: open {result['chart_path']}")
