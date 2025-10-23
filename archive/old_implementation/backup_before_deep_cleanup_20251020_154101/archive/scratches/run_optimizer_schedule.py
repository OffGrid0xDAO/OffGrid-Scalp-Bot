"""
Scheduler - Runs rule optimizer every 30 minutes
This is the script you keep running in the background
"""

import time
import schedule
from datetime import datetime
from rule_optimizer import RuleOptimizer


def run_optimization_cycle():
    """Run a single optimization cycle"""
    print(f"\n{'='*70}")
    print(f"🕐 Scheduled Optimization Cycle Starting")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    try:
        optimizer = RuleOptimizer()
        optimizer.optimize_rules()
    except Exception as e:
        print(f"❌ Error during optimization: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n⏳ Next optimization cycle in 30 minutes...\n")


def main():
    """Run scheduler"""
    print("\n" + "="*70)
    print("🚀 RULE OPTIMIZER SCHEDULER STARTED")
    print("="*70)
    print(f"⏰ Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Schedule: Every 30 minutes")
    print(f"💰 Expected Cost: ~48 API calls/day = ~$0.20-$1.00/day (vs $50-100/day)")
    print(f"💡 Your bot trades using FREE rules between cycles!")
    print("="*70)

    # Run immediately on start
    print("\n🔥 Running first optimization cycle now...")
    run_optimization_cycle()

    # Schedule every 30 minutes
    schedule.every(30).minutes.do(run_optimization_cycle)

    print("✅ Scheduler running. Press Ctrl+C to stop.")

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Scheduler stopped by user")
        print("="*70)
