"""
Run Multiple Optimization Cycles
Iterates the optimization process to converge rules toward optimal performance
"""

import os
import json
import time
from datetime import datetime
from smart_trade_finder import SmartTradeFinder
from run_backtest import run_backtest


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

    if bt_trades > opt_trades * 2:
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


def adjust_rules_simple(opt_data, bt_data, current_rules):
    """
    Simple rule adjustment based on gap analysis
    """
    opt_trades = opt_data.get('total_trades', 0)
    bt_trades = bt_data.get('total_trades', 0)

    opt_comp = opt_data.get('patterns', {}).get('avg_compression', 0)
    bt_comp = bt_data.get('patterns', {}).get('avg_compression', 0)

    opt_emas = opt_data.get('patterns', {}).get('avg_light_emas', 0)
    bt_emas = bt_data.get('patterns', {}).get('avg_light_emas', 0)

    entry_rules = current_rules['entry_rules']
    entry_tiers = entry_rules['entry_tiers']

    changes = []

    # Adjust based on over/under trading
    if bt_trades > opt_trades * 2:
        # Over-trading - make rules MORE strict
        for tier_name in ['tier_1_strong_trend', 'tier_2_moderate_trend', 'tier_3_quick_scalp']:
            if tier_name in entry_tiers:
                old_emas = entry_tiers[tier_name]['min_light_emas']
                entry_tiers[tier_name]['min_light_emas'] = min(old_emas + 1, 12)
                changes.append(f"{tier_name}: {old_emas} → {entry_tiers[tier_name]['min_light_emas']} light EMAs")

        # Decrease max allowed compression (stricter - EMAs must be tighter)
        old_comp = entry_rules.get('min_compression_for_entry', 0.002)
        entry_rules['min_compression_for_entry'] = max(old_comp * 0.8, 0.0005)
        changes.append(f"max_compression: {old_comp:.4f} → {entry_rules['min_compression_for_entry']:.4f} (stricter)")

    elif bt_trades < opt_trades * 0.5:
        # Under-trading - make rules MORE loose
        for tier_name in ['tier_1_strong_trend', 'tier_2_moderate_trend', 'tier_3_quick_scalp']:
            if tier_name in entry_tiers:
                old_emas = entry_tiers[tier_name]['min_light_emas']
                entry_tiers[tier_name]['min_light_emas'] = max(old_emas - 1, 3)
                changes.append(f"{tier_name}: {old_emas} → {entry_tiers[tier_name]['min_light_emas']} light EMAs")

        # Increase max allowed compression (looser - EMAs can be wider)
        old_comp = entry_rules.get('min_compression_for_entry', 0.002)
        entry_rules['min_compression_for_entry'] = min(old_comp * 1.2, 0.01)
        changes.append(f"max_compression: {old_comp:.4f} → {entry_rules['min_compression_for_entry']:.4f} (looser)")

    else:
        # Fine-tune toward optimal values
        # Adjust light EMAs toward optimal
        target_emas = int(opt_emas)
        for tier_name in ['tier_1_strong_trend', 'tier_2_moderate_trend']:
            if tier_name in entry_tiers:
                old_emas = entry_tiers[tier_name]['min_light_emas']
                if tier_name == 'tier_1_strong_trend':
                    new_emas = target_emas
                else:
                    new_emas = max(target_emas - 2, 5)

                if old_emas != new_emas:
                    entry_tiers[tier_name]['min_light_emas'] = new_emas
                    changes.append(f"{tier_name}: {old_emas} → {new_emas} light EMAs")

        # Adjust max compression toward optimal (with small buffer)
        if opt_comp > 0:
            target_comp = opt_comp * 1.15  # Allow only 15% higher than optimal
            old_comp = entry_rules.get('min_compression_for_entry', 0.002)
            if abs(old_comp - target_comp) > 0.0003:
                entry_rules['min_compression_for_entry'] = target_comp
                changes.append(f"max_compression: {old_comp:.4f} → {target_comp:.4f} (targeting optimal)")

    if changes:
        print("\n🔧 RULE ADJUSTMENTS:")
        for change in changes:
            print(f"  • {change}")

        current_rules['last_updated'] = datetime.now().isoformat()
        current_rules['updated_by'] = 'multi_optimization_script'

        with open('trading_rules.json', 'w') as f:
            json.dump(current_rules, f, indent=2)

        return True
    else:
        print("\n✅ Rules already optimal - no changes needed")
        return False


def run_optimization_iterations(num_iterations=5, hours_back=24):
    """
    Run multiple optimization iterations
    """
    print("="*70)
    print("MULTI-ITERATION OPTIMIZATION")
    print("="*70)
    print(f"Iterations: {num_iterations}")
    print(f"Data window: {hours_back} hours")
    print("="*70)

    # Check which optimal trades source to use
    optimal_source = os.getenv('OPTIMAL_TRADES_SOURCE', 'auto').lower()
    print(f"📊 Optimal trades source: {optimal_source}")
    print("="*70)

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

        # Step 3: Analyze and adjust
        print(f"\n[{iteration}/3] Analyzing gap and adjusting rules...")
        gaps = print_comparison(iteration, opt_results, bt_results)

        # Load current rules
        with open('trading_rules.json', 'r') as f:
            current_rules = json.load(f)

        # Adjust rules
        if iteration < num_iterations:
            rules_changed = adjust_rules_simple(opt_results, bt_results, current_rules)

            if not rules_changed and gaps['trade_gap'] < 100 and gaps['pnl_gap'] < 1.0:
                print(f"\n{'='*70}")
                print("✅ CONVERGENCE ACHIEVED!")
                print(f"   Trade gap: {gaps['trade_gap']} trades")
                print(f"   PnL gap: {gaps['pnl_gap']:.2f}%")
                print(f"   Stopping after {iteration} iterations")
                print(f"{'='*70}")
                break

            print("\nWaiting 2 seconds before next iteration...")
            time.sleep(2)
        else:
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
    print("\nYou can now start the bot with these optimized rules!")
    print("Run: python3 main.py")


if __name__ == '__main__':
    import sys

    # Allow custom iteration count
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24

    run_optimization_iterations(num_iterations=iterations, hours_back=hours)
