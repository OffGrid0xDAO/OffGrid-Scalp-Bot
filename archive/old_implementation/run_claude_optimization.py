"""
Claude-Based Multi-Iteration Optimization
Uses the Claude API to intelligently optimize trading rules based on gap analysis
"""

import os
import json
import time
from datetime import datetime
from smart_trade_finder import SmartTradeFinder
from run_backtest import run_backtest
from rule_optimizer import RuleOptimizer


def print_comparison(iteration, opt_data, bt_data):
    """Print comparison between optimal and backtest"""
    print(f"\n{'='*70}")
    print(f"ITERATION {iteration} RESULTS")
    print(f"{'='*70}")

    opt_trades = opt_data.get('total_trades', 0)
    bt_trades = bt_data.get('total_trades', 0)

    opt_pnl = opt_data.get('total_pnl_pct', 0)
    bt_pnl = bt_data.get('total_pnl_pct', 0)

    opt_comp = opt_data.get('patterns', {}).get('avg_compression', 0) * 100
    bt_comp = bt_data.get('patterns', {}).get('avg_compression', 0) * 100

    opt_emas = opt_data.get('patterns', {}).get('avg_light_emas', 0)
    bt_emas = bt_data.get('patterns', {}).get('avg_light_emas', 0)

    print(f"\n{'Metric':<20} {'Optimal':<15} {'Backtest':<15} {'Gap':<15}")
    print(f"{'-'*70}")
    print(f"{'Trades':<20} {opt_trades:<15} {bt_trades:<15} {bt_trades-opt_trades:+}")
    print(f"{'PnL':<20} {opt_pnl:+.2f}%{'':<10} {bt_pnl:+.2f}%{'':<10} {bt_pnl-opt_pnl:+.2f}%")
    print(f"{'Compression':<20} {opt_comp:.2f}%{'':<10} {bt_comp:.2f}%{'':<10} {bt_comp-opt_comp:+.2f}%")
    print(f"{'Light EMAs':<20} {opt_emas:.1f}{'':<12} {bt_emas:.1f}{'':<12} {bt_emas-opt_emas:+.1f}")

    # Calculate capture rate
    capture_rate = (bt_trades / max(opt_trades, 1)) * 100
    print(f"\n📊 Capture Rate: {capture_rate:.1f}%")

    if bt_trades > opt_trades * 2.5:
        print("⚠️  SEVERE OVER-TRADING - Rules way too loose!")
    elif bt_trades > opt_trades * 1.5:
        print("⚠️  OVER-TRADING - Rules too loose!")
    elif bt_trades < opt_trades * 0.5:
        print("⚠️  UNDER-TRADING - Rules too strict!")
    else:
        print("✅ Trade count in reasonable range")

    return {
        'trade_gap': abs(bt_trades - opt_trades),
        'pnl_gap': abs(bt_pnl - opt_pnl),
        'capture_rate': capture_rate
    }


def run_claude_optimization_iterations(num_iterations=5, hours_back=24):
    """
    Run multiple optimization iterations using Claude API
    """
    print("="*70)
    print("CLAUDE-POWERED MULTI-ITERATION OPTIMIZATION")
    print("="*70)
    print(f"Iterations: {num_iterations}")
    print(f"Data window: {hours_back} hours")
    print(f"Using Claude API for intelligent rule updates")
    print("="*70)

    # Check which optimal trades source to use
    optimal_source = os.getenv('OPTIMAL_TRADES_SOURCE', 'auto').lower()
    print(f"📊 Optimal trades source: {optimal_source}")

    # Initialize Claude optimizer
    optimizer = RuleOptimizer()

    for iteration in range(1, num_iterations + 1):
        print(f"\n\n{'#'*70}")
        print(f"ITERATION {iteration}/{num_iterations}")
        print(f"{'#'*70}")

        # Step 1: Load or generate optimal trades
        if optimal_source == 'user':
            # Use user-specified trades
            print(f"\n[{iteration}/3] Loading user-specified optimal trades...")
            user_trades_path = 'trading_data/optimal_user_trades.json'

            if not os.path.exists(user_trades_path):
                print(f"❌ {user_trades_path} not found!")
                print("   Run: python3 create_user_optimal_trades.py")
                return

            with open(user_trades_path, 'r') as f:
                opt_results = json.load(f)

            print(f"  ✅ Loaded {opt_results['total_trades']} user-specified trades")
        else:
            # Auto-generate optimal trades
            print(f"\n[{iteration}/3] Generating optimal trades...")
            finder = SmartTradeFinder()
            opt_results = finder.find_smart_trades(hours_back=hours_back)

            with open('trading_data/optimal_trades.json', 'w') as f:
                json.dump(opt_results, f, indent=2, default=str)

            print(f"  ✅ {opt_results['total_trades']} optimal trades found")

        # Step 2: Run backtest with current rules
        print(f"\n[{iteration}/3] Running backtest with current rules...")
        bt_results = run_backtest(hours_back=hours_back)

        with open('trading_data/backtest_trades.json', 'w') as f:
            json.dump(bt_results, f, indent=2, default=str)

        print(f"  ✅ {bt_results['total_trades']} backtest trades executed")

        # Step 3: Show comparison
        print(f"\n[{iteration}/3] Analyzing gap and asking Claude for rule adjustments...")
        gaps = print_comparison(iteration, opt_results, bt_results)

        # Check if we've converged
        if gaps['trade_gap'] < 50 and gaps['pnl_gap'] < 1.0:
            print(f"\n{'='*70}")
            print("🎯 EXCELLENT CONVERGENCE ACHIEVED!")
            print(f"   Trade gap: {gaps['trade_gap']} trades")
            print(f"   PnL gap: {gaps['pnl_gap']:.2f}%")
            print(f"   Stopping after {iteration} iterations")
            print(f"{'='*70}")
            break

        # Step 4: Use Claude to optimize rules (only if not last iteration)
        if iteration < num_iterations:
            print("\n🤖 Calling Claude API to analyze gap and update rules...")

            # Dummy performance data
            performance = {'total_trades': 0}

            # Call Claude to optimize using the existing method
            try:
                # Load current rules
                current_rules = optimizer.load_current_rules()

                # Build the prompt with 3-way comparison
                prompt = optimizer.build_optimization_prompt(
                    optimal_data=opt_results,
                    backtest_data=bt_results,
                    actual_data={'total_trades': 0},  # No live trades yet
                    current_rules=current_rules,
                    performance=performance,
                    big_movement_analysis=None
                )

                # Call Claude
                print("   Sending request to Claude...")
                response = optimizer.client.messages.create(
                    model=optimizer.model,
                    max_tokens=4096,
                    temperature=0.3,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )

                # Track costs
                optimizer.total_input_tokens += response.usage.input_tokens
                optimizer.total_output_tokens += response.usage.output_tokens
                cost = (response.usage.input_tokens * 3 / 1_000_000 +
                       response.usage.output_tokens * 15 / 1_000_000)
                optimizer.session_cost += cost

                print(f"\n✅ Claude responded successfully!")
                print(f"   Input tokens: {response.usage.input_tokens}")
                print(f"   Output tokens: {response.usage.output_tokens}")
                print(f"   Cost: ${cost:.4f}")

                # Parse Claude's response
                response_text = response.content[0].text

                # Extract JSON from Claude's response
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    updated_rules = json.loads(json_match.group(1))

                    # Save updated rules
                    optimizer.save_updated_rules(updated_rules)

                    # Save to version history
                    optimizer.version_manager.save_version(updated_rules, {
                        'iteration': iteration,
                        'trade_gap': gaps['trade_gap'],
                        'pnl_gap': gaps['pnl_gap']
                    })

                    print(f"\n✅ Rules updated successfully!")
                else:
                    print(f"\n⚠️  Claude provided recommendations but no JSON rules")
                    print("   Response:")
                    print(response_text[:500])

            except Exception as e:
                print(f"\n❌ Error calling Claude: {e}")
                import traceback
                traceback.print_exc()
                print("   Continuing without rule update...")

            print("\nWaiting 3 seconds before next iteration...")
            time.sleep(3)

        else:
            # Last iteration - just show final results
            print(f"\n{'='*70}")
            print("FINAL RESULTS")
            print(f"{'='*70}")
            print(f"✅ Completed {num_iterations} iterations")
            print(f"   Final trade gap: {gaps['trade_gap']} trades")
            print(f"   Final PnL gap: {gaps['pnl_gap']:.2f}%")
            print(f"   Final capture rate: {gaps['capture_rate']:.1f}%")

    print(f"\n{'='*70}")
    print("OPTIMIZATION COMPLETE!")
    print(f"{'='*70}")
    print("\n✅ Rules have been optimized by Claude AI")
    print("   Check trading_rules.json for updated parameters")
    print("\nYou can now start the bot with these optimized rules:")
    print("   python3 main.py")
    print("\nCost Summary:")
    print(f"   Total API cost: ${optimizer.session_cost:.4f}")


if __name__ == '__main__':
    import sys

    # Allow custom iteration count
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24

    run_claude_optimization_iterations(num_iterations=iterations, hours_back=hours)
