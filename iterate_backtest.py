#!/usr/bin/env python3
"""
Automated Backtest Iteration with Claude Analysis

Continuously improves trading strategy by:
1. Running backtest with current parameters
2. Analyzing results with Claude
3. Implementing Claude's suggestions
4. Running new backtest
5. Repeat until optimal performance

Usage:
    python iterate_backtest.py --iterations 10 --target-sharpe 12.0
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Optional
import re
import os
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.optimization.claude_iteration_optimizer import ClaudeIterationOptimizer, IterationMetrics

logger = logging.getLogger(__name__)


class BacktestIterator:
    """
    Automated backtest iteration system with Claude optimization

    Runs backtest → Claude analyzes → Apply improvements → Repeat
    """

    def __init__(
        self,
        initial_params: Dict,
        target_sharpe: float = 12.0,
        target_return: float = 5.0,
        max_iterations: int = 20,
        results_dir: str = 'iteration_results'
    ):
        """
        Initialize backtest iterator

        Args:
            initial_params: Starting parameter configuration
            target_sharpe: Target Sharpe ratio
            target_return: Target return percentage (in 17 days)
            max_iterations: Maximum iterations
            results_dir: Directory to save results
        """
        self.current_params = initial_params.copy()
        self.target_sharpe = target_sharpe
        self.target_return = target_return
        self.max_iterations = max_iterations
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)

        # Initialize Claude optimizer
        self.optimizer = ClaudeIterationOptimizer(
            results_dir=str(self.results_dir)
        )

        # Track all iterations
        self.iterations: List[Dict] = []
        self.best_iteration = None
        self.best_sharpe = 0.0
        self.best_return = 0.0

        logger.info(
            f"Initialized BacktestIterator (target_sharpe={target_sharpe}, "
            f"target_return={target_return}%, max_iterations={max_iterations})"
        )

    async def run_backtest(self, params: Dict, iteration: int) -> Dict:
        """
        Run backtest with given parameters

        Args:
            params: Parameter configuration
            iteration: Iteration number

        Returns:
            Backtest results dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"RUNNING BACKTEST - Iteration {iteration}")
        logger.info(f"{'='*60}")
        logger.info(f"Parameters: {json.dumps(params, indent=2)}")

        try:
            # Import backtest modules
            sys.path.insert(0, str(project_root / 'fourier_strategy'))
            from fibonacci_ribbon_fine_tuner import run_fibonacci_backtest

            # Run backtest
            results = run_fibonacci_backtest(
                symbol='ETH',
                timeframe='5m',
                compression_threshold=params.get('compression_threshold', 85),
                alignment_threshold=params.get('alignment_threshold', 85),
                confluence_threshold=params.get('confluence_threshold', 60),
                n_harmonics=params.get('n_harmonics', 5),
                max_holding_periods=params.get('max_holding_periods', 24)
            )

            logger.info(f"\n✅ Backtest completed!")
            logger.info(f"Return: {results['total_return_pct']:.2f}%")
            logger.info(f"Sharpe: {results['sharpe_ratio']:.2f}")
            logger.info(f"Win Rate: {results['win_rate_pct']:.1f}%")
            logger.info(f"Trades: {int(results['num_trades'])}")

            return results

        except Exception as e:
            logger.error(f"Backtest failed: {e}", exc_info=True)
            return None

    async def analyze_with_claude(
        self,
        results: Dict,
        iteration: int,
        previous_results: Optional[Dict] = None
    ) -> str:
        """
        Analyze backtest results with Claude

        Args:
            results: Current backtest results
            iteration: Iteration number
            previous_results: Previous iteration results

        Returns:
            Claude's recommendations
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"ANALYZING WITH CLAUDE - Iteration {iteration}")
        logger.info(f"{'='*60}")

        # Create metrics object
        metrics = IterationMetrics(
            iteration_id=iteration,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_trades=int(results.get('num_trades', 0)),
            winning_trades=int(results.get('num_trades', 0) * results.get('win_rate_pct', 0) / 100),
            losing_trades=int(results.get('num_trades', 0) * (1 - results.get('win_rate_pct', 0) / 100)),
            win_rate=results.get('win_rate_pct', 0) / 100,
            total_pnl=results.get('total_return_pct', 0) * 100,  # Assuming $10k capital
            total_pnl_pct=results.get('total_return_pct', 0),
            sharpe_ratio=results.get('sharpe_ratio', 0),
            max_drawdown=abs(results.get('max_drawdown_pct', 0)),
            profit_factor=results.get('profit_factor', 0),
            avg_win=0,  # Not available from backtest
            avg_loss=0,
            avg_holding_time=results.get('avg_holding_periods', 0) * 5,  # 5m timeframe
            best_trade_pnl=0,
            worst_trade_pnl=0
        )

        # Create previous metrics if available
        prev_metrics = None
        if previous_results:
            prev_metrics = IterationMetrics(
                iteration_id=iteration - 1,
                start_time=datetime.now(),
                end_time=datetime.now(),
                total_trades=int(previous_results.get('num_trades', 0)),
                winning_trades=int(previous_results.get('num_trades', 0) * previous_results.get('win_rate_pct', 0) / 100),
                losing_trades=int(previous_results.get('num_trades', 0) * (1 - previous_results.get('win_rate_pct', 0) / 100)),
                win_rate=previous_results.get('win_rate_pct', 0) / 100,
                total_pnl=previous_results.get('total_return_pct', 0) * 100,
                total_pnl_pct=previous_results.get('total_return_pct', 0),
                sharpe_ratio=previous_results.get('sharpe_ratio', 0),
                max_drawdown=abs(previous_results.get('max_drawdown_pct', 0)),
                profit_factor=previous_results.get('profit_factor', 0),
                avg_win=0,
                avg_loss=0,
                avg_holding_time=previous_results.get('avg_holding_periods', 0) * 5,
                best_trade_pnl=0,
                worst_trade_pnl=0
            )

        # Generate optimization prompt
        prompt = self.optimizer.generate_optimization_prompt(
            current_metrics=metrics,
            previous_metrics=prev_metrics,
            current_params=self.current_params
        )

        # Add iteration-specific context
        prompt += f"""

---

## 🎯 ITERATION {iteration} SPECIFIC CONTEXT

### Current Parameters:
```json
{json.dumps(self.current_params, indent=2)}
```

### Target Goals:
- **Target Sharpe**: {self.target_sharpe}
- **Target Return**: {self.target_return}%
- **Current Gap**: Sharpe {self.target_sharpe - results.get('sharpe_ratio', 0):.2f} away, Return {self.target_return - results.get('total_return_pct', 0):.2f}% away

### Best Iteration So Far:
{f"Iteration {self.best_iteration}: Sharpe {self.best_sharpe:.2f}, Return {self.best_return:.2f}%" if self.best_iteration else "This is the first iteration"}

### What to Focus On:

1. **If Sharpe is too high but returns too low** → Suggest relaxing thresholds slightly
2. **If returns are good but Sharpe is low** → Suggest tightening risk management
3. **If both are good** → Suggest fine-tuning for optimal balance
4. **Provide SPECIFIC numeric parameter changes** (not just "increase" or "decrease")

### Output Format Required:

Please respond with:

1. **Analysis Section** - What's working, what's not
2. **Recommended Parameter Changes** in this EXACT format:

```json
{{
  "compression_threshold": 85,
  "alignment_threshold": 85,
  "confluence_threshold": 60,
  "n_harmonics": 5,
  "max_holding_periods": 24
}}
```

3. **Rationale** - Why these changes will improve performance
4. **Expected Impact** - Predicted Sharpe and Return after changes

IMPORTANT: Include the JSON block with exact parameter values!
"""

        # Save prompt
        self.optimizer.save_optimization_prompt(iteration, prompt)

        # Get Claude recommendations
        logger.info("Requesting Claude analysis...")
        recommendations = await self.optimizer.get_claude_recommendations(prompt)

        # Save recommendations
        self.optimizer.save_recommendations(iteration, recommendations)

        logger.info(f"✅ Claude analysis complete")
        logger.info(f"Saved to: {self.results_dir}/iteration_{iteration}_recommendations.md")

        return recommendations

    def extract_parameters_from_recommendations(self, recommendations: str) -> Optional[Dict]:
        """
        Extract parameter recommendations from Claude's response

        Args:
            recommendations: Claude's text response

        Returns:
            Dictionary of parameters or None if can't parse
        """
        logger.info("Extracting parameters from Claude recommendations...")

        # Try to find JSON block in recommendations
        json_pattern = r'```json\s*(\{[^`]+\})\s*```'
        matches = re.findall(json_pattern, recommendations, re.DOTALL)

        if matches:
            try:
                params = json.loads(matches[0])
                logger.info(f"✅ Extracted parameters: {params}")
                return params
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")

        # Fallback: Try to parse key-value pairs
        logger.warning("No JSON block found, attempting to parse text...")

        params = {}
        patterns = {
            'compression_threshold': r'compression[_\s]*threshold[:\s]+(\d+)',
            'alignment_threshold': r'alignment[_\s]*threshold[:\s]+(\d+)',
            'confluence_threshold': r'confluence[_\s]*threshold[:\s]+(\d+)',
            'n_harmonics': r'n[_\s]*harmonics[:\s]+(\d+)',
            'max_holding_periods': r'max[_\s]*holding[_\s]*periods[:\s]+(\d+)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, recommendations, re.IGNORECASE)
            if match:
                params[key] = int(match.group(1))

        if params:
            logger.info(f"✅ Extracted from text: {params}")
            return params

        logger.error("❌ Could not extract parameters from recommendations")
        return None

    def apply_recommendations(self, new_params: Dict):
        """
        Apply recommended parameters

        Args:
            new_params: New parameter values
        """
        logger.info(f"\n{'='*60}")
        logger.info("APPLYING RECOMMENDATIONS")
        logger.info(f"{'='*60}")

        logger.info("Before:")
        logger.info(json.dumps(self.current_params, indent=2))

        # Update parameters
        for key, value in new_params.items():
            if key in self.current_params:
                old_value = self.current_params[key]
                self.current_params[key] = value
                logger.info(f"  {key}: {old_value} → {value}")

        logger.info("\nAfter:")
        logger.info(json.dumps(self.current_params, indent=2))

    async def run_iterations(self):
        """
        Run the full iteration loop

        Returns:
            Final best parameters and results
        """
        logger.info("\n" + "="*60)
        logger.info("🚀 STARTING AUTOMATED BACKTEST ITERATION")
        logger.info("="*60)
        logger.info(f"Target: Sharpe {self.target_sharpe}, Return {self.target_return}%")
        logger.info(f"Max Iterations: {self.max_iterations}")
        logger.info("="*60 + "\n")

        previous_results = None

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"\n{'#'*60}")
            logger.info(f"# ITERATION {iteration}/{self.max_iterations}")
            logger.info(f"{'#'*60}\n")

            # 1. Run backtest
            results = await self.run_backtest(self.current_params, iteration)

            if not results:
                logger.error(f"Iteration {iteration} failed - skipping")
                continue

            # Track results
            self.iterations.append({
                'iteration': iteration,
                'params': self.current_params.copy(),
                'results': results
            })

            # Check if this is the best so far
            sharpe = results.get('sharpe_ratio', 0)
            ret = results.get('total_return_pct', 0)

            if sharpe > self.best_sharpe:
                self.best_sharpe = sharpe
                self.best_return = ret
                self.best_iteration = iteration
                logger.info(f"🏆 NEW BEST ITERATION! Sharpe: {sharpe:.2f}, Return: {ret:.2f}%")

            # Check if we've reached targets
            if sharpe >= self.target_sharpe and ret >= self.target_return:
                logger.info(f"\n🎉 TARGET ACHIEVED!")
                logger.info(f"Sharpe: {sharpe:.2f} (target: {self.target_sharpe})")
                logger.info(f"Return: {ret:.2f}% (target: {self.target_return}%)")
                break

            # 2. Analyze with Claude
            recommendations = await self.analyze_with_claude(
                results,
                iteration,
                previous_results
            )

            if not recommendations or "error" in recommendations.lower():
                logger.error("Claude analysis failed - stopping iterations")
                break

            # 3. Extract new parameters
            new_params = self.extract_parameters_from_recommendations(recommendations)

            if not new_params:
                logger.warning("Could not extract parameters - using manual adjustment")
                # Fallback: Small manual adjustment
                if sharpe > self.target_sharpe and ret < self.target_return:
                    # Sharpe too high, returns too low → relax thresholds
                    new_params = {
                        'compression_threshold': max(70, self.current_params['compression_threshold'] - 3),
                        'alignment_threshold': max(70, self.current_params['alignment_threshold'] - 3),
                        'confluence_threshold': max(55, self.current_params['confluence_threshold'] - 3)
                    }
                elif ret > self.target_return and sharpe < self.target_sharpe:
                    # Returns good, Sharpe low → tighten risk
                    new_params = {
                        'compression_threshold': min(95, self.current_params['compression_threshold'] + 2),
                        'alignment_threshold': min(95, self.current_params['alignment_threshold'] + 2),
                        'confluence_threshold': min(80, self.current_params['confluence_threshold'] + 2)
                    }
                else:
                    logger.error("Cannot determine adjustment direction - stopping")
                    break

            # 4. Apply recommendations
            self.apply_recommendations(new_params)

            # Store previous results
            previous_results = results

            # Save iteration summary
            self._save_iteration_summary()

        # Final summary
        self._print_final_summary()

        return self.current_params, self.iterations

    def _save_iteration_summary(self):
        """Save summary of all iterations"""
        summary_file = self.results_dir / 'iteration_summary.json'

        summary = {
            'timestamp': datetime.now().isoformat(),
            'target_sharpe': self.target_sharpe,
            'target_return': self.target_return,
            'best_iteration': self.best_iteration,
            'best_sharpe': self.best_sharpe,
            'best_return': self.best_return,
            'iterations': self.iterations,
            'final_params': self.current_params
        }

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"Saved iteration summary to {summary_file}")

    def _print_final_summary(self):
        """Print final summary"""
        logger.info("\n" + "="*60)
        logger.info("📊 FINAL SUMMARY")
        logger.info("="*60)

        logger.info(f"\nTotal Iterations: {len(self.iterations)}")
        logger.info(f"Best Iteration: {self.best_iteration}")
        logger.info(f"Best Sharpe: {self.best_sharpe:.2f}")
        logger.info(f"Best Return: {self.best_return:.2f}%")

        logger.info("\n📈 ITERATION PROGRESSION:")
        for iter_data in self.iterations:
            it = iter_data['iteration']
            res = iter_data['results']
            marker = "🏆" if it == self.best_iteration else "  "
            logger.info(
                f"{marker} Iter {it}: Sharpe {res.get('sharpe_ratio', 0):.2f}, "
                f"Return {res.get('total_return_pct', 0):.2f}%, "
                f"Trades {int(res.get('num_trades', 0))}"
            )

        logger.info(f"\n🎯 FINAL PARAMETERS:")
        logger.info(json.dumps(self.current_params, indent=2))

        logger.info("\n✅ Iteration complete!")
        logger.info(f"Results saved to: {self.results_dir}/")
        logger.info("="*60 + "\n")


async def main():
    parser = argparse.ArgumentParser(description='Automated Backtest Iteration with Claude')
    parser.add_argument('--iterations', type=int, default=10,
                        help='Maximum number of iterations')
    parser.add_argument('--target-sharpe', type=float, default=12.0,
                        help='Target Sharpe ratio')
    parser.add_argument('--target-return', type=float, default=5.0,
                        help='Target return percentage (17 days)')
    parser.add_argument('--start-params', type=str,
                        help='Path to initial parameters JSON file')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'iterate_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )

    # Load environment
    load_dotenv()

    if not os.getenv('ANTHROPIC_API_KEY'):
        logger.error("ANTHROPIC_API_KEY not set in .env file!")
        logger.error("Claude optimization requires API key")
        sys.exit(1)

    # Load initial parameters
    if args.start_params and Path(args.start_params).exists():
        with open(args.start_params, 'r') as f:
            initial_params = json.load(f)
        logger.info(f"Loaded initial parameters from {args.start_params}")
    else:
        # Default starting parameters (current optimized)
        initial_params = {
            'compression_threshold': 90,
            'alignment_threshold': 90,
            'confluence_threshold': 65,
            'n_harmonics': 5,
            'max_holding_periods': 24
        }
        logger.info("Using default initial parameters")

    # Create iterator
    iterator = BacktestIterator(
        initial_params=initial_params,
        target_sharpe=args.target_sharpe,
        target_return=args.target_return,
        max_iterations=args.iterations
    )

    # Run iterations
    final_params, iterations = await iterator.run_iterations()

    logger.info("\n🎉 DONE!")
    logger.info(f"Final parameters: {json.dumps(final_params, indent=2)}")


if __name__ == '__main__':
    asyncio.run(main())
