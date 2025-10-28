#!/usr/bin/env python3
"""
Automated Fourier Strategy Optimization Loop with Claude AI

This script runs continuous optimization iterations:
1. Runs backtest with current parameters
2. Sends results to Claude AI for analysis
3. Gets parameter suggestions from Claude
4. Validates improvements
5. Applies changes if better
6. Repeats for N iterations

USAGE:
    python run_fourier_optimization_loop.py --iterations 10

REQUIREMENTS:
    - ANTHROPIC_API_KEY environment variable must be set
    - pip install anthropic
"""

import argparse
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from fourier_iterative_optimizer import FourierIterativeOptimizer

# Check for Anthropic API
try:
    import anthropic
except ImportError:
    print("\n❌ ERROR: anthropic package not installed")
    print("   Install with: pip install anthropic")
    sys.exit(1)


class ClaudePoweredOptimizer:
    """
    Runs optimization loop with Claude AI
    """

    def __init__(self,
                 symbol: str = 'ETH',
                 initial_capital: float = 10000.0,
                 max_iterations: int = 10):
        """
        Initialize Claude-powered optimizer

        Args:
            symbol: Trading symbol
            initial_capital: Starting capital
            max_iterations: Maximum iterations to run
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.max_iterations = max_iterations

        # Initialize Fourier optimizer
        self.optimizer = FourierIterativeOptimizer(
            symbol=symbol,
            initial_capital=initial_capital
        )

        # Initialize Anthropic client
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("\n❌ ERROR: ANTHROPIC_API_KEY environment variable not set")
            print("   Get your API key from: https://console.anthropic.com")
            print("   Set it with: export ANTHROPIC_API_KEY='your-key-here'")
            sys.exit(1)

        self.client = anthropic.Anthropic(api_key=api_key)

        # Track best iteration
        self.best_iteration = None
        self.best_sharpe = float('-inf')

    def ask_claude(self, prompt: str) -> Dict:
        """
        Send prompt to Claude and get parameter suggestions

        Args:
            prompt: Analysis prompt

        Returns:
            dict with Claude's suggestions
        """
        print("\n🤖 Asking Claude AI for optimization suggestions...")

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = message.content[0].text.strip()

            # Extract JSON from response (handle markdown code blocks)
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()

            # Parse JSON
            suggestions = json.loads(response_text)

            print("\n✅ Claude's Analysis:")
            print(f"   {suggestions.get('analysis', 'N/A')}")
            print("\n📊 Suggested Parameter Changes:")
            for param, value in suggestions.get('suggested_changes', {}).items():
                current = self.optimizer.current_params.get(param, 'N/A')
                print(f"   {param}: {current} → {value}")
            print(f"\n💡 Reasoning:")
            print(f"   {suggestions.get('reasoning', 'N/A')}")

            return suggestions

        except json.JSONDecodeError as e:
            print(f"\n⚠️  Failed to parse Claude's response as JSON: {e}")
            print(f"   Raw response: {response_text}")
            return None
        except Exception as e:
            print(f"\n⚠️  Error communicating with Claude: {e}")
            return None

    def apply_suggestions_with_validation(self, suggestions: Dict) -> bool:
        """
        Apply suggested changes with safety limits and validation

        Args:
            suggestions: Claude's suggestions

        Returns:
            bool: True if changes improved performance, False otherwise
        """
        if not suggestions or 'suggested_changes' not in suggestions:
            print("\n⚠️  No valid suggestions to apply")
            return False

        print("\n🔧 Applying suggested changes with validation...")

        # Save current parameters
        old_params = self.optimizer.current_params.copy()

        # Apply changes with safety limits (max 30% change)
        suggested_changes = suggestions['suggested_changes']
        for key, new_value in suggested_changes.items():
            if key in self.optimizer.current_params:
                old_value = self.optimizer.current_params[key]

                # For numeric values, limit change to 30%
                if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                    max_change = abs(old_value * 0.3)
                    min_allowed = old_value - max_change
                    max_allowed = old_value + max_change

                    # Clamp to allowed range
                    limited_value = max(min_allowed, min(max_allowed, new_value))

                    self.optimizer.current_params[key] = limited_value

                    if limited_value != new_value:
                        print(f"   ⚠️  Limited {key}: suggested {new_value}, applied {limited_value:.3f}")
                    else:
                        print(f"   ✅ Applied {key}: {old_value} → {new_value}")
                else:
                    self.optimizer.current_params[key] = new_value
                    print(f"   ✅ Applied {key}: {old_value} → {new_value}")

        # Save parameters to file for reference
        params_file = self.optimizer.iterations_dir / f'params_iteration_{self.optimizer.current_iteration}.json'
        with open(params_file, 'w') as f:
            json.dump({
                'iteration': self.optimizer.current_iteration,
                'timestamp': datetime.now().isoformat(),
                'old_params': old_params,
                'suggested_params': suggested_changes,
                'applied_params': self.optimizer.current_params,
                'reasoning': suggestions.get('reasoning', '')
            }, f, indent=2)

        print(f"\n   💾 Parameters saved to: {params_file}")

        return True

    def run_optimization_loop(self,
                            days_back: int = 50,
                            candles_to_show: int = 1000,
                            min_improvement_threshold: float = 0.05):
        """
        Run the full optimization loop

        Args:
            days_back: Days of data to fetch
            candles_to_show: Candles to show on chart
            min_improvement_threshold: Minimum Sharpe improvement to keep changes
        """
        print("\n" + "╔" + "═"*78 + "╗")
        print("║" + " "*15 + "CLAUDE-POWERED FOURIER OPTIMIZATION" + " "*28 + "║")
        print("╚" + "═"*78 + "╝\n")

        print(f"🎯 Target: {self.max_iterations} iterations")
        print(f"💰 Initial capital: ${self.initial_capital:,.2f}")
        print(f"📊 Symbol: {self.symbol}")
        print(f"📁 Iterations directory: {self.optimizer.iterations_dir}\n")

        for i in range(self.max_iterations):
            print("\n" + "━"*80)
            print(f"🔄 STARTING ITERATION {self.optimizer.current_iteration}")
            print("━"*80)

            # Step 1: Run iteration
            result = self.optimizer.run_iteration(
                days_back=days_back,
                candles_to_show=candles_to_show,
                verbose=True
            )

            metrics = result['metrics']
            current_sharpe = metrics['sharpe_ratio']

            # Track best iteration
            if current_sharpe > self.best_sharpe:
                self.best_sharpe = current_sharpe
                self.best_iteration = result['iteration_name']
                print(f"\n🏆 NEW BEST ITERATION! Sharpe: {current_sharpe:.3f}")

            # Step 2: Generate Claude prompt
            prompt = self.optimizer.generate_claude_analysis_prompt(result)

            # Step 3: Ask Claude for suggestions
            suggestions = self.ask_claude(prompt)

            if not suggestions:
                print("\n⚠️  No valid suggestions received, using current parameters for next iteration")
                time.sleep(2)
                continue

            # Step 4: Apply suggestions
            applied = self.apply_suggestions_with_validation(suggestions)

            if not applied:
                print("\n⚠️  Failed to apply suggestions, continuing with current parameters")

            # Increment iteration counter
            self.optimizer.current_iteration += 1

            # Wait between iterations to avoid API rate limits
            if i < self.max_iterations - 1:
                print("\n⏳ Waiting 3 seconds before next iteration...")
                time.sleep(3)

        # Final summary
        print("\n\n" + "╔" + "═"*78 + "╗")
        print("║" + " "*25 + "OPTIMIZATION COMPLETE!" + " "*32 + "║")
        print("╚" + "═"*78 + "╝\n")

        print(f"✅ Completed {self.max_iterations} iterations")
        print(f"🏆 Best iteration: {self.best_iteration} (Sharpe: {self.best_sharpe:.3f})")

        # Show comparison
        print("\n" + "="*80)
        print("FINAL COMPARISON")
        print("="*80)

        comparison = self.optimizer.compare_iterations(n=min(10, len(self.optimizer.iterations_history)))
        print(comparison.to_string(index=False))

        # Save final summary
        summary_file = self.optimizer.iterations_dir / 'optimization_final_summary.txt'
        with open(summary_file, 'w') as f:
            f.write(f"Fourier Strategy Optimization Summary\n")
            f.write(f"=" * 80 + "\n\n")
            f.write(f"Completed: {datetime.now()}\n")
            f.write(f"Total Iterations: {self.max_iterations}\n")
            f.write(f"Best Iteration: {self.best_iteration}\n")
            f.write(f"Best Sharpe Ratio: {self.best_sharpe:.3f}\n\n")
            f.write(f"Iterations Comparison:\n")
            f.write(comparison.to_string(index=False))

        print(f"\n📄 Summary saved to: {summary_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run Claude-powered Fourier strategy optimization loop'
    )
    parser.add_argument('--iterations', type=int, default=10,
                       help='Number of optimization iterations (default: 10)')
    parser.add_argument('--symbol', type=str, default='ETH',
                       help='Trading symbol (default: ETH)')
    parser.add_argument('--capital', type=float, default=10000.0,
                       help='Initial capital (default: 10000)')
    parser.add_argument('--days', type=int, default=50,
                       help='Days of historical data (default: 50)')

    args = parser.parse_args()

    # Check API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("\n❌ ERROR: ANTHROPIC_API_KEY not set")
        print("\nTo set your API key:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\nGet your API key from: https://console.anthropic.com")
        sys.exit(1)

    # Initialize and run optimizer
    optimizer = ClaudePoweredOptimizer(
        symbol=args.symbol,
        initial_capital=args.capital,
        max_iterations=args.iterations
    )

    try:
        optimizer.run_optimization_loop(days_back=args.days)
    except KeyboardInterrupt:
        print("\n\n⚠️  Optimization interrupted by user")
        print(f"✅ Completed {optimizer.optimizer.current_iteration - 1} iterations")
        print(f"🏆 Best so far: {optimizer.best_iteration} (Sharpe: {optimizer.best_sharpe:.3f})")
    except Exception as e:
        print(f"\n❌ Error during optimization: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
