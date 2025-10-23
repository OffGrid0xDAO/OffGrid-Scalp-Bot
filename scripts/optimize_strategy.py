#!/usr/bin/env python3
"""
Automated Strategy Optimization with Claude AI

Runs complete optimization loop:
1. Backtest current strategy
2. Find optimal trades
3. Analyze performance gap
4. Ask Claude for improvements
5. Validate suggestions
6. Apply if better
7. Repeat!

Usage:
    python3 scripts/optimize_strategy.py --iterations 5 --timeframe 1h
    python3 scripts/optimize_strategy.py --iterations 10 --timeframe 15m --auto-apply
"""

import sys
from pathlib import Path
import pandas as pd
import argparse
import json
import os
from datetime import datetime
import anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / '.env')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategy.entry_detector import EntryDetector
from strategy.exit_manager import ExitManager
from strategy.ribbon_analyzer import RibbonAnalyzer
from backtest.backtest_engine import BacktestEngine
from backtest.performance_metrics import PerformanceMetrics
from analysis.optimal_trade_finder import OptimalTradeFinder
from optimization.claude_optimizer import ClaudeOptimizer
from reporting.telegram_reporter import TelegramReporter
from reporting.chart_generator import ChartGenerator


class AutomatedOptimizer:
    """
    Fully automated strategy optimization with Claude AI
    """

    def __init__(
        self,
        api_key: str,
        timeframe: str = '1h',
        symbol: str = 'eth',
        max_param_change_pct: float = 20.0,
        min_improvement_pct: float = 2.0
    ):
        """
        Initialize automated optimizer

        Args:
            api_key: Anthropic API key
            timeframe: Trading timeframe
            symbol: Trading symbol
            max_param_change_pct: Max % change per parameter
            min_improvement_pct: Minimum improvement to accept changes
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.timeframe = timeframe
        self.symbol = symbol
        self.max_param_change_pct = max_param_change_pct
        self.min_improvement_pct = min_improvement_pct

        # Paths
        self.data_file = Path(__file__).parent.parent / 'trading_data' / 'indicators' / f'{symbol}_{timeframe}_full.csv'
        self.params_file = Path(__file__).parent.parent / 'src' / 'strategy' / 'strategy_params.json'
        self.backup_dir = Path(__file__).parent.parent / 'optimization_logs' / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Components
        self.entry_detector = None
        self.exit_manager = None
        self.ribbon_analyzer = None
        self.backtest_engine = None
        self.optimal_finder = None
        self.optimizer = None
        self.telegram = None
        self.chart_generator = None
        self.performance_metrics = None

        # State
        self.iteration_history = []
        self.best_win_rate = 0
        self.best_params = None

    def initialize_components(self):
        """Initialize all trading components"""
        print("\n🔧 Initializing components...")

        self.entry_detector = EntryDetector()
        self.exit_manager = ExitManager()
        self.ribbon_analyzer = RibbonAnalyzer()
        self.backtest_engine = BacktestEngine(
            initial_capital=10000,
            commission_pct=0.05,
            slippage_pct=0.02,
            position_size_pct=10.0,
            max_concurrent_trades=3
        )
        self.optimal_finder = OptimalTradeFinder(min_profit_pct=1.0, max_hold_candles=24)  # 24h = 1 day for 1h timeframe
        self.optimizer = ClaudeOptimizer()
        self.telegram = TelegramReporter()
        self.chart_generator = ChartGenerator()
        self.performance_metrics = PerformanceMetrics()

        print("   ✅ All components initialized")
        if self.telegram.enabled:
            print("   ✅ Telegram reporting enabled")
        else:
            print("   ⚠️  Telegram reporting disabled (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")

    def load_data(self) -> pd.DataFrame:
        """Load historical data"""
        if not self.data_file.exists():
            print(f"\n❌ Data file not found: {self.data_file}")
            print(f"   Run: python3 scripts/process_indicators.py")
            sys.exit(1)

        print(f"\n📊 Loading data: {self.data_file}")
        df = pd.read_csv(self.data_file)
        print(f"   Loaded {len(df)} candles")

        # Add ribbon analysis if needed
        if 'compression_score' not in df.columns:
            print("   Adding ribbon analysis...")
            df = self.ribbon_analyzer.analyze_all(df)

        return df

    def run_evaluation(self, df: pd.DataFrame) -> dict:
        """
        Run complete evaluation: backtest + optimal + gap analysis

        Returns:
            dict with results
        """
        # Reinitialize detectors with current params
        self.entry_detector = EntryDetector()
        self.exit_manager = ExitManager()

        # Run backtest
        print("\n" + "="*80)
        print("RUNNING BACKTEST")
        print("="*80)
        backtest_results = self.backtest_engine.run_backtest(
            df=df,
            entry_detector=self.entry_detector,
            exit_manager=self.exit_manager,
            ribbon_analyzer=None,
            verbose=False
        )

        # Find optimal trades
        print("\n" + "="*80)
        print("FINDING OPTIMAL TRADES")
        print("="*80)
        optimal_trades = self.optimal_finder.scan_all_optimal_trades(df)

        # Analyze gap
        print("\n" + "="*80)
        print("ANALYZING PERFORMANCE GAP")
        print("="*80)
        gap_analysis = self.optimizer.analyze_performance_gap(backtest_results, optimal_trades)

        # Generate detailed performance comparison
        print("\n" + "="*80)
        print("PERFORMANCE METRICS COMPARISON")
        print("="*80)
        performance_comparison = self.performance_metrics.compare_all_three(
            optimal_trades=optimal_trades,
            backtest_trades=backtest_results['trades'],
            actual_trades=None  # TODO: integrate live trades
        )

        # Print summary
        print(performance_comparison['summary'])

        return {
            'backtest': backtest_results,
            'optimal': optimal_trades,
            'gap_analysis': gap_analysis,
            'performance_comparison': performance_comparison
        }

    def ask_claude(self, gap_analysis: dict, current_params: dict) -> dict:
        """
        Ask Claude for optimization suggestions

        Returns:
            dict with suggested_changes and reasoning
        """
        print("\n" + "="*80)
        print("ASKING CLAUDE AI FOR SUGGESTIONS")
        print("="*80)

        # Generate prompt
        prompt = self.optimizer.generate_optimization_prompt(gap_analysis, current_params['entry_filters'])

        # Call Claude API
        print("   🤖 Calling Claude API...")
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            print(f"\n📝 Claude's Response:\n{response_text}\n")

            # Extract JSON from response
            # Look for ```json ... ``` block
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)

            if json_match:
                suggestions_json = json_match.group(1)
                suggestions = json.loads(suggestions_json)

                print("\n✅ Parsed Suggestions:")
                print(json.dumps(suggestions, indent=2))

                return suggestions
            else:
                print("\n⚠️  No JSON found in response, trying to parse entire response...")
                # Try parsing entire response
                suggestions = json.loads(response_text)
                return suggestions

        except Exception as e:
            print(f"\n❌ Error calling Claude API: {e}")
            print(f"   Response: {response_text if 'response_text' in locals() else 'No response'}")
            return None

    def backup_params(self):
        """Backup current parameters"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f'params_backup_{timestamp}.json'

        with open(self.params_file, 'r') as f:
            params = json.load(f)

        with open(backup_file, 'w') as f:
            json.dump(params, f, indent=2)

        print(f"\n💾 Backed up params: {backup_file}")
        return backup_file

    def apply_suggestions(self, suggestions: dict) -> bool:
        """
        Apply Claude's suggestions to parameters

        Returns:
            bool: True if applied successfully
        """
        if not suggestions or 'suggested_changes' not in suggestions:
            print("\n⚠️  No valid suggestions to apply")
            return False

        print("\n" + "="*80)
        print("APPLYING SUGGESTIONS")
        print("="*80)

        # Backup current params
        self.backup_params()

        # Load current params
        with open(self.params_file, 'r') as f:
            params = json.load(f)

        old_params = params['entry_filters'].copy()
        suggested_changes = suggestions['suggested_changes']

        # Apply changes with limits
        changes_applied = []
        for key, new_value in suggested_changes.items():
            if key in params['entry_filters']:
                old_value = params['entry_filters'][key]

                # For numeric values, limit change
                if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                    max_change = abs(old_value * (self.max_param_change_pct / 100))

                    if old_value == 0:
                        limited_value = new_value
                    else:
                        if new_value > old_value:
                            limited_value = min(new_value, old_value + max_change)
                        else:
                            limited_value = max(new_value, old_value - max_change)

                    params['entry_filters'][key] = limited_value
                    changes_applied.append(f"{key}: {old_value} → {limited_value}")
                    print(f"   ✅ {key}: {old_value} → {limited_value} (suggested: {new_value})")
                else:
                    params['entry_filters'][key] = new_value
                    changes_applied.append(f"{key}: {old_value} → {new_value}")
                    print(f"   ✅ {key}: {old_value} → {new_value}")

            elif key in params['exit_strategy']:
                old_value = params['exit_strategy'][key]
                params['exit_strategy'][key] = new_value
                changes_applied.append(f"{key}: {old_value} → {new_value}")
                print(f"   ✅ {key}: {old_value} → {new_value}")

        # Save updated params
        with open(self.params_file, 'w') as f:
            json.dump(params, f, indent=2)

        print(f"\n✅ Applied {len(changes_applied)} changes")
        return True

    def revert_params(self, backup_file: Path):
        """Revert to backup parameters"""
        print(f"\n↩️  Reverting to backup: {backup_file}")

        with open(backup_file, 'r') as f:
            params = json.load(f)

        with open(self.params_file, 'w') as f:
            json.dump(params, f, indent=2)

        print("   ✅ Parameters reverted")

    def run_optimization_loop(self, df: pd.DataFrame, iterations: int, auto_apply: bool = False):
        """
        Run complete optimization loop

        Args:
            df: Historical data
            iterations: Number of optimization iterations
            auto_apply: Automatically apply improvements (no confirmation)
        """
        print("\n" + "="*80)
        print("AUTOMATED OPTIMIZATION LOOP")
        print("="*80)
        print(f"   Iterations: {iterations}")
        print(f"   Timeframe: {self.timeframe}")
        print(f"   Symbol: {self.symbol}")
        print(f"   Auto-apply: {auto_apply}")

        # Initial evaluation
        print("\n" + "="*80)
        print("ITERATION 0: BASELINE")
        print("="*80)

        baseline = self.run_evaluation(df)
        baseline_win_rate = baseline['gap_analysis']['backtest_metrics']['win_rate']
        self.best_win_rate = baseline_win_rate

        with open(self.params_file, 'r') as f:
            self.best_params = json.load(f)

        print(f"\n📊 Baseline Win Rate: {baseline_win_rate:.2f}%")

        # Optimization iterations
        for i in range(1, iterations + 1):
            print("\n" + "="*80)
            print(f"ITERATION {i}/{iterations}")
            print("="*80)

            # Current evaluation
            current = self.run_evaluation(df)
            current_metrics = current['gap_analysis']['backtest_metrics']

            # Ask Claude for suggestions
            with open(self.params_file, 'r') as f:
                current_params = json.load(f)

            suggestions = self.ask_claude(current['gap_analysis'], current_params)

            if not suggestions:
                print("\n⚠️  No suggestions from Claude, skipping iteration")
                continue

            # Show reasoning
            if 'reasoning' in suggestions:
                print(f"\n💡 Claude's Reasoning:\n{suggestions['reasoning']}\n")

            # Apply suggestions
            backup_file = self.backup_params()

            if not self.apply_suggestions(suggestions):
                continue

            # Test new parameters
            print("\n" + "="*80)
            print("TESTING NEW PARAMETERS")
            print("="*80)

            new_eval = self.run_evaluation(df)
            new_metrics = new_eval['gap_analysis']['backtest_metrics']
            new_win_rate = new_metrics['win_rate']

            # Compare results
            print("\n" + "="*80)
            print("COMPARISON")
            print("="*80)
            print(f"   Old Win Rate: {current_metrics['win_rate']:.2f}%")
            print(f"   New Win Rate: {new_win_rate:.2f}%")
            print(f"   Change: {new_win_rate - current_metrics['win_rate']:+.2f}%")

            improvement = ((new_win_rate - current_metrics['win_rate']) / current_metrics['win_rate'] * 100
                          if current_metrics['win_rate'] > 0 else 0)

            # Decide whether to keep changes
            if new_win_rate > current_metrics['win_rate'] and improvement >= self.min_improvement_pct:
                print(f"\n✅ IMPROVEMENT DETECTED! (+{improvement:.2f}%)")

                if new_win_rate > self.best_win_rate:
                    self.best_win_rate = new_win_rate
                    with open(self.params_file, 'r') as f:
                        self.best_params = json.load(f)
                    print(f"   🎯 New best win rate: {self.best_win_rate:.2f}%")

                keep = True
                if not auto_apply:
                    response = input("\n   Keep these changes? [Y/n]: ")
                    keep = response.lower() != 'n'

                if keep:
                    print("   ✅ Keeping changes")
                else:
                    print("   ❌ Reverting changes")
                    self.revert_params(backup_file)
            else:
                if improvement < 0:
                    print(f"\n❌ PERFORMANCE DEGRADED ({improvement:.2f}%)")
                else:
                    print(f"\n⚠️  Improvement too small ({improvement:.2f}% < {self.min_improvement_pct}%)")

                print("   Reverting changes...")
                self.revert_params(backup_file)

            # Generate charts and send report
            print("\n" + "="*80)
            print("GENERATING REPORTS")
            print("="*80)

            # Create comparison chart
            try:
                chart_file = self.chart_generator.create_3way_comparison_chart(
                    df=df,
                    optimal_trades=new_eval['optimal'],
                    backtest_trades=new_eval['backtest']['trades'],
                    actual_trades=None,  # TODO: integrate live trades
                    timeframe=self.timeframe,
                    symbol=self.symbol.upper()
                )
                print(f"   ✅ Chart saved: {chart_file}")
            except Exception as e:
                print(f"   ⚠️  Chart generation failed: {e}")

            # Send Telegram report
            try:
                self.telegram.send_optimization_report(
                    optimal_results=new_eval['optimal'],
                    backtest_results=new_eval['backtest'],
                    actual_results=None,  # TODO: integrate live trades
                    gap_analysis=new_eval['gap_analysis'],
                    iteration=i,
                    planned_changes=suggestions.get('suggested_changes') if suggestions else None
                )
            except Exception as e:
                print(f"   ⚠️  Telegram report failed: {e}")

            # Log iteration
            self.iteration_history.append({
                'iteration': i,
                'timestamp': datetime.now().isoformat(),
                'old_win_rate': current_metrics['win_rate'],
                'new_win_rate': new_win_rate,
                'improvement_pct': improvement,
                'kept': new_win_rate > current_metrics['win_rate'],
                'suggestions': suggestions
            })

        # Final summary
        print("\n" + "="*80)
        print("OPTIMIZATION COMPLETE")
        print("="*80)
        print(f"\n📊 Results:")
        print(f"   Baseline win rate: {baseline_win_rate:.2f}%")
        print(f"   Best win rate: {self.best_win_rate:.2f}%")
        print(f"   Total improvement: {self.best_win_rate - baseline_win_rate:+.2f}%")
        print(f"   Iterations completed: {iterations}")

        # Save iteration history
        history_file = Path(__file__).parent.parent / 'optimization_logs' / f'optimization_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(history_file, 'w') as f:
            json.dump({
                'baseline_win_rate': baseline_win_rate,
                'best_win_rate': self.best_win_rate,
                'total_improvement': self.best_win_rate - baseline_win_rate,
                'iterations': self.iteration_history
            }, f, indent=2)

        print(f"\n💾 History saved: {history_file}")

        # Restore best params if current isn't best
        with open(self.params_file, 'r') as f:
            current_final = json.load(f)

        if current_final != self.best_params:
            print("\n🔄 Restoring best parameters...")
            with open(self.params_file, 'w') as f:
                json.dump(self.best_params, f, indent=2)
            print("   ✅ Best parameters restored")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Automated strategy optimization with Claude AI')
    parser.add_argument('--iterations', type=int, default=5, help='Number of optimization iterations')
    parser.add_argument('--timeframe', default='1h', help='Timeframe (1m, 3m, 5m, 15m, 30m, 1h)')
    parser.add_argument('--symbol', default='eth', help='Trading symbol')
    parser.add_argument('--auto-apply', action='store_true', help='Automatically apply improvements without confirmation')
    parser.add_argument('--max-change', type=float, default=20.0, help='Max %% change per parameter')
    parser.add_argument('--min-improvement', type=float, default=2.0, help='Minimum %% improvement to keep changes')
    args = parser.parse_args()

    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("\n❌ ANTHROPIC_API_KEY not found in environment")
        print("   Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("   Or add to .env file")
        sys.exit(1)

    print("="*80)
    print("AUTOMATED STRATEGY OPTIMIZATION")
    print("="*80)
    print(f"Using Claude AI (Sonnet 4)")
    print(f"Timeframe: {args.timeframe}")
    print(f"Iterations: {args.iterations}")

    # Initialize optimizer
    optimizer = AutomatedOptimizer(
        api_key=api_key,
        timeframe=args.timeframe,
        symbol=args.symbol,
        max_param_change_pct=args.max_change,
        min_improvement_pct=args.min_improvement
    )

    # Initialize components first (needed for load_data)
    optimizer.initialize_components()

    # Load data
    df = optimizer.load_data()

    # Run optimization loop
    optimizer.run_optimization_loop(df, args.iterations, args.auto_apply)

    print("\n✅ Done! Strategy optimized.")


if __name__ == '__main__':
    main()
