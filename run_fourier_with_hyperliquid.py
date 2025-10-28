"""
Run Fourier Strategy with Hyperliquid Data

Complete pipeline that:
1. Fetches data from Hyperliquid
2. Runs Fourier strategy with backtesting
3. Generates comprehensive visualizations
4. Saves iteration results
5. Uses Claude API to analyze performance and suggest improvements
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import anthropic

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fourier_strategy import FourierTradingStrategy
from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter

load_dotenv()


class FourierHyperliquidRunner:
    """
    Complete runner for Fourier strategy with Hyperliquid data.

    Features:
    - Fetches data from Hyperliquid
    - Runs strategy with multiple parameter sets
    - Generates visualizations
    - Saves iteration results
    - Uses Claude to analyze and optimize
    """

    def __init__(self,
                 symbol: str = 'ETH',
                 output_dir: str = 'trading_data/fourier_iterations'):
        """
        Initialize runner.

        Args:
            symbol: Trading symbol
            output_dir: Directory for saving results
        """
        self.symbol = symbol
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize adapter
        self.adapter = HyperliquidDataAdapter(symbol=symbol)

        # Store iteration results
        self.iterations = []

    def fetch_data(self,
                  interval: str = '1h',
                  days_back: int = 90) -> pd.DataFrame:
        """
        Fetch OHLCV data from Hyperliquid.

        Args:
            interval: Timeframe
            days_back: Days of history

        Returns:
            DataFrame with OHLCV data
        """
        print("\n" + "=" * 70)
        print(f"FETCHING DATA FROM HYPERLIQUID")
        print("=" * 70)

        df = self.adapter.fetch_ohlcv(
            interval=interval,
            days_back=days_back,
            use_checkpoint=True
        )

        print(f"\n✅ Data fetched successfully!")
        print(f"   Symbol: {self.symbol}")
        print(f"   Timeframe: {interval}")
        print(f"   Candles: {len(df)}")
        print(f"   Period: {df.index[0]} to {df.index[-1]}")

        return df

    def run_strategy(self,
                    df: pd.DataFrame,
                    params: dict = None,
                    iteration_name: str = None) -> dict:
        """
        Run Fourier strategy on data.

        Args:
            df: OHLCV DataFrame
            params: Strategy parameters
            iteration_name: Name for this iteration

        Returns:
            Results dictionary
        """
        if params is None:
            params = {}

        if iteration_name is None:
            iteration_name = f"iteration_{len(self.iterations) + 1}"

        print("\n" + "=" * 70)
        print(f"RUNNING FOURIER STRATEGY: {iteration_name}")
        print("=" * 70)

        # Initialize strategy
        strategy = FourierTradingStrategy(**params)

        # Run strategy
        results = strategy.run(df, run_backtest=True, verbose=True)

        # Save outputs
        output_path = self.output_dir / iteration_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Export CSV
        strategy.export_results(str(output_path / 'results.csv'))

        # Generate visualizations
        try:
            print("   Generating comprehensive analysis chart...")
            strategy.visualize('comprehensive',
                              save_path=str(output_path / 'analysis.png'))
            print("   ✅ Comprehensive chart saved")
        except Exception as e:
            print(f"   ⚠️  Could not generate comprehensive chart: {e}")

        try:
            print("   Generating performance chart...")
            strategy.visualize('performance',
                              save_path=str(output_path / 'performance.png'))
            print("   ✅ Performance chart saved")
        except Exception as e:
            print(f"   ⚠️  Could not generate performance chart: {e}")

        # Save metadata
        metadata = {
            'iteration_name': iteration_name,
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'data_points': len(df),
            'parameters': params,
            'metrics': results['metrics'],
            'output_path': str(output_path)
        }

        with open(output_path / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        # Store iteration
        self.iterations.append(metadata)

        # Save iterations log
        with open(self.output_dir / 'iterations_log.json', 'w') as f:
            json.dump(self.iterations, f, indent=2, default=str)

        print(f"\n✅ Results saved to: {output_path}")

        return results

    def analyze_with_claude(self, max_iterations: int = 3) -> dict:
        """
        Use Claude API to analyze results and suggest improvements.

        Args:
            max_iterations: Maximum iterations to analyze

        Returns:
            Dictionary with Claude's analysis and suggestions
        """
        print("\n" + "=" * 70)
        print("ANALYZING WITH CLAUDE API")
        print("=" * 70)

        # Get API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("⚠️  ANTHROPIC_API_KEY not set, skipping Claude analysis")
            return None

        # Get recent iterations
        recent = self.iterations[-max_iterations:]

        # Format for Claude
        analysis_prompt = self._create_analysis_prompt(recent)

        # Call Claude
        try:
            client = anthropic.Anthropic(api_key=api_key)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": analysis_prompt
                }]
            )

            analysis = message.content[0].text

            print("\n" + "=" * 70)
            print("CLAUDE'S ANALYSIS")
            print("=" * 70)
            print(analysis)

            # Save analysis
            analysis_file = self.output_dir / f'claude_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
            with open(analysis_file, 'w') as f:
                f.write(f"# Claude Analysis - {datetime.now().isoformat()}\n\n")
                f.write(analysis)

            print(f"\n✅ Analysis saved to: {analysis_file}")

            return {
                'analysis': analysis,
                'file': str(analysis_file)
            }

        except Exception as e:
            print(f"❌ Error calling Claude API: {e}")
            return None

    def _create_analysis_prompt(self, iterations: list) -> str:
        """Create prompt for Claude analysis."""
        prompt = """Analyze these Fourier trading strategy backtest results and provide:

1. **Performance Assessment**: Evaluate the overall performance
2. **Parameter Insights**: What parameter combinations work best?
3. **Optimization Suggestions**: Specific parameter changes to try next
4. **Risk Analysis**: Identify risks and suggest improvements

Here are the iteration results:

"""
        for i, iteration in enumerate(iterations, 1):
            metrics = iteration['metrics']
            params = iteration['parameters']

            prompt += f"\n## Iteration {i}: {iteration['iteration_name']}\n\n"
            prompt += f"**Parameters:**\n"
            for key, value in params.items():
                prompt += f"- {key}: {value}\n"

            prompt += f"\n**Performance Metrics:**\n"
            prompt += f"- Total Return: {metrics['total_return_pct']:.2f}%\n"
            prompt += f"- Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n"
            prompt += f"- Max Drawdown: {metrics['max_drawdown_pct']:.2f}%\n"
            prompt += f"- Win Rate: {metrics['win_rate_pct']:.2f}%\n"
            prompt += f"- Profit Factor: {metrics['profit_factor']:.2f}\n"
            prompt += f"- Number of Trades: {metrics['num_trades']}\n"

        prompt += """

Provide a concise analysis with:
1. Best performing configuration and why
2. 3-5 specific parameter recommendations to test next
3. Key insights about what makes this strategy successful
4. Risk warnings or concerns

Format as markdown.
"""
        return prompt

    def run_optimization_cycle(self,
                              df: pd.DataFrame,
                              param_sets: list = None,
                              use_claude: bool = True):
        """
        Run optimization cycle with multiple parameter sets.

        Args:
            df: OHLCV DataFrame
            param_sets: List of parameter dictionaries to test
            use_claude: Use Claude for analysis
        """
        if param_sets is None:
            # Default parameter sets to test (with max holding period for day trading)
            param_sets = [
                # Baseline - Balanced
                {
                    'n_harmonics': 5,
                    'noise_threshold': 0.3,
                    'base_ema_period': 28,
                    'correlation_threshold': 0.6,
                    'min_signal_strength': 0.35,  # Reasonable threshold
                    'max_holding_periods': 168  # 1 week max for hourly
                },
                # Aggressive - More trades
                {
                    'n_harmonics': 7,
                    'noise_threshold': 0.2,
                    'base_ema_period': 21,
                    'correlation_threshold': 0.5,
                    'min_signal_strength': 0.25,  # Lower for more signals
                    'max_holding_periods': 120  # 5 days
                },
                # Conservative - Quality over quantity
                {
                    'n_harmonics': 3,
                    'noise_threshold': 0.4,
                    'base_ema_period': 35,
                    'correlation_threshold': 0.7,
                    'min_signal_strength': 0.45,  # Higher for quality
                    'max_holding_periods': 336  # 2 weeks
                },
                # High Harmonics - Trend following
                {
                    'n_harmonics': 9,
                    'noise_threshold': 0.25,
                    'base_ema_period': 28,
                    'correlation_threshold': 0.6,
                    'min_signal_strength': 0.3,
                    'max_holding_periods': 168
                }
            ]

        print("\n" + "╔" + "═" * 68 + "╗")
        print("║" + " " * 15 + "OPTIMIZATION CYCLE" + " " * 32 + "║")
        print("╚" + "═" * 68 + "╝")

        print(f"\nTesting {len(param_sets)} parameter configurations...")

        # Run each configuration
        for i, params in enumerate(param_sets, 1):
            iteration_name = f"iteration_{i:02d}"
            print(f"\n{'='*70}")
            print(f"Configuration {i}/{len(param_sets)}")
            print(f"{'='*70}")

            self.run_strategy(df, params, iteration_name)

        # Analyze with Claude
        if use_claude:
            self.analyze_with_claude(max_iterations=len(param_sets))

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print summary of all iterations."""
        print("\n" + "=" * 70)
        print("OPTIMIZATION SUMMARY")
        print("=" * 70)

        if not self.iterations:
            print("No iterations completed.")
            return

        # Create summary DataFrame
        summary = []
        for iteration in self.iterations:
            metrics = iteration['metrics']
            summary.append({
                'Iteration': iteration['iteration_name'],
                'Return (%)': metrics['total_return_pct'],
                'Sharpe': metrics['sharpe_ratio'],
                'Max DD (%)': metrics['max_drawdown_pct'],
                'Win Rate (%)': metrics['win_rate_pct'],
                'Profit Factor': metrics['profit_factor'],
                'Trades': metrics['num_trades']
            })

        df_summary = pd.DataFrame(summary)

        print("\n" + df_summary.to_string(index=False))

        # Best iteration
        best_idx = df_summary['Sharpe'].idxmax()
        best = df_summary.loc[best_idx]

        print(f"\n🏆 Best Iteration: {best['Iteration']}")
        print(f"   Sharpe Ratio: {best['Sharpe']:.2f}")
        print(f"   Total Return: {best['Return (%)']:.2f}%")
        print(f"   Win Rate: {best['Win Rate (%)']:.2f}%")

        # Save summary
        summary_file = self.output_dir / 'optimization_summary.csv'
        df_summary.to_csv(summary_file, index=False)
        print(f"\n💾 Summary saved to: {summary_file}")


def main():
    """Main execution"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "FOURIER STRATEGY WITH HYPERLIQUID" + " " * 23 + "║")
    print("╚" + "═" * 68 + "╝\n")

    # Configuration
    symbol = os.getenv('SYMBOL', 'ETH')
    interval = os.getenv('INTERVAL', '1h')
    days_back = int(os.getenv('DAYS_BACK', '90'))

    # Initialize runner
    runner = FourierHyperliquidRunner(symbol=symbol)

    # Fetch data
    df = runner.fetch_data(interval=interval, days_back=days_back)

    # Run optimization cycle
    runner.run_optimization_cycle(df, use_claude=True)

    print("\n" + "=" * 70)
    print("COMPLETE!")
    print("=" * 70)
    print(f"\n📂 All results saved to: {runner.output_dir}")
    print(f"\n📋 Next steps:")
    print(f"   1. Review visualizations in {runner.output_dir}")
    print(f"   2. Check Claude's analysis for insights")
    print(f"   3. Test recommended parameters")
    print(f"   4. Deploy best configuration to live trading")


if __name__ == '__main__':
    main()
