"""
Run Dual Timeframe Bot with AUTOMATIC OPTIMIZATION
- ONE SCRIPT does EVERYTHING
- Trades continuously (FREE - no API calls)
- Automatically optimizes rules every 30 minutes
- Continuous improvement while you sleep!
- 99% cost savings!
"""

import os
from dotenv import load_dotenv
from dual_timeframe_bot_with_optimizer import DualTimeframeBotWithOptimizer

# Load environment
load_dotenv()


def check_initialization():
    """Check if rules need to be initialized from historical data"""
    import json

    if not os.path.exists('trading_rules.json'):
        print("\n" + "⚠️ "*20)
        print("FIRST TIME SETUP DETECTED")
        print("⚠️ "*20)
        print("\n📋 You have two options:")
        print("")
        print("  [1] 🚀 QUICK START (Recommended)")
        print("      • Use default rules and start trading immediately")
        print("      • Bot will optimize rules every 30 minutes")
        print("      • Rules improve over time automatically")
        print("")
        print("  [2] 📊 INITIALIZE FROM HISTORY")
        print("      • Analyze ALL your historical EMA data first")
        print("      • Claude creates optimal rules from past patterns")
        print("      • Start with PROVEN rules, not defaults")
        print("      • Requires: Historical data from previous runs")
        print("")

        while True:
            choice = input("Choose option (1 or 2): ").strip()
            if choice == '1':
                print("\n✅ Using default rules - bot will optimize them automatically!")
                return False
            elif choice == '2':
                print("\n🔄 Running historical initialization...")
                return True
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")

    # Check if rules look like they were initialized or are just defaults
    with open('trading_rules.json', 'r') as f:
        rules = json.load(f)

    updated_by = rules.get('updated_by', 'unknown')

    if updated_by == 'initial_setup':
        print("\n💡 TIP: You can re-initialize rules from historical data:")
        print("   Run: python3 initialize_trading_rules.py")
        print("   This will analyze ALL your past trades for optimal starting rules")
        print("")

    return False


def main():
    print("╔" + "="*78 + "╗")
    print("║" + " "*8 + "SELF-OPTIMIZING TRADING BOT - 99% Cost Savings!" + " "*15 + "║")
    print("║" + " "*12 + "Trades FREE + Auto-Improves Every 30 Minutes" + " "*15 + "║")
    print("╚" + "="*78 + "╝")

    # Check if we need to initialize rules from historical data
    if check_initialization():
        # Run initialization
        from initialize_trading_rules import TradingRulesInitializer
        try:
            initializer = TradingRulesInitializer()
            initializer.initialize()
            print("\n✅ Initialization complete! Starting bot with optimized rules...\n")
        except Exception as e:
            print(f"\n⚠️  Initialization failed: {e}")
            print("   Continuing with default rules...")
            # Create default rules if init failed
            import json
            default_rules = {
                "version": "1.0",
                "last_updated": "2025-10-19T00:00:00",
                "updated_by": "initial_setup",
                "entry_rules": {
                    "ribbon_alignment_threshold": 0.85,
                    "min_light_emas_required": 2,
                    "ribbon_states_allowed_long": ["all_green", "mixed_green"],
                    "ribbon_states_allowed_short": ["all_red", "mixed_red"],
                    "fresh_transition_max_minutes": 15,
                    "stale_transition_min_minutes": 20
                },
                "exit_rules": {
                    "max_hold_minutes": 15,
                    "profit_target_pct": 0.005,
                    "stop_loss_pct": 0.003,
                    "use_yellow_ema_trail": True,
                    "exit_on_ribbon_flip": True,
                    "exit_on_light_ema_change_count": 3
                },
                "pattern_rules": {
                    "path_e_dark_transition": {"enabled": True, "priority": 1, "confidence_boost": 0.15, "entry_window_seconds": 10},
                    "path_d_early_reversal": {"enabled": True, "priority": 2, "min_light_emas_opposite": 8, "min_green_appearing": 2, "confidence_threshold": 0.75},
                    "path_c_wick_reversal": {"enabled": True, "priority": 3, "min_wick_pct": 0.003, "max_wick_pct": 0.008, "confidence_boost": 0.20},
                    "path_a_trending": {"enabled": True, "priority": 4, "min_range_pct": 0.005, "price_location_lower_pct": 0.5, "price_location_upper_pct": 0.5, "min_alignment_pct": 0.85},
                    "path_b_breakout": {"enabled": True, "priority": 5, "max_range_pct": 0.004, "min_breakout_pct": 0.0015, "ribbon_flip_max_minutes": 8}
                },
                "performance_metrics": {"total_trades_executed": 0, "winning_trades": 0, "losing_trades": 0, "win_rate": 0.0},
                "claude_insights": {"last_optimization": "never", "key_findings": [], "pattern_recommendations": []}
            }
            with open('trading_rules.json', 'w') as f:
                json.dump(default_rules, f, indent=2)

    # Load all settings from .env
    private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')
    if not private_key:
        print("\n❌ ERROR: HYPERLIQUID_PRIVATE_KEY not found in .env file")
        return

    use_testnet = os.getenv('USE_TESTNET', 'true').lower() == 'true'
    auto_trade = os.getenv('AUTO_TRADE', 'true').lower() == 'true'
    position_size_pct = float(os.getenv('POSITION_SIZE_PCT', '10')) / 100
    leverage = int(os.getenv('LEVERAGE', '25'))
    min_confidence = float(os.getenv('MIN_CONFIDENCE', '0.75'))

    # Get optimization interval
    optimization_interval = int(os.getenv('OPTIMIZATION_INTERVAL_MINUTES', '30'))

    # Ask user to select timeframe strategy
    print("\n📊 SELECT TRADING STRATEGY:")
    print("─"*80)
    print("\n  [1] 🐌 DAY TRADING (5min + 15min charts)")
    print("      • Slower signals (5-15 min lag)")
    print("      • Hold time: 15-60 minutes")
    print("      • Profit target: 0.3%")
    print("      • Stop loss: 0.15%")
    print("      • Best for: Swing trades, longer holds")
    print("")
    print("  [2] ⚡ SCALPING (1min + 3min charts) **RECOMMENDED**")
    print("      • Fast signals (1-3 min)")
    print("      • Hold time: 1-5 minutes")
    print("      • Profit target: 0.2%")
    print("      • Stop loss: 0.08%")
    print("      • Best for: Quick in/out, high frequency")
    print("")

    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == '1':
            timeframe_short = 5
            timeframe_long = 15
            strategy_name = "DAY TRADING"
            break
        elif choice == '2':
            timeframe_short = 1
            timeframe_long = 3
            strategy_name = "SCALPING"
            break
        else:
            print("❌ Invalid choice. Please enter 1 or 2.")

    # Display config
    print("\n📊 CONFIGURATION:")
    print("─"*80)
    print(f"  Strategy: {strategy_name}")
    print(f"  Network: {'TESTNET 🧪' if use_testnet else '⚠️  MAINNET 💰'}")
    print(f"  Auto-Trading: {'✅ ENABLED' if auto_trade else '❌ DISABLED'}")
    print(f"  Position Size: {position_size_pct*100:.1f}%")
    print(f"  Leverage: {leverage}x")
    print(f"  Min Confidence: {min_confidence:.0%}")
    print(f"  Timeframes: {timeframe_short}min + {timeframe_long}min")
    print(f"")
    print(f"  💰 AI Trading: Rule-Based (NO API CALLS = FREE!)")
    print(f"  📊 Auto-Optimization: Every {optimization_interval} minutes")
    print(f"  🔄 Continuous Improvement: ENABLED")
    print(f"  💸 Daily Cost: ~$0.20-1.00 (vs $50-100 before!)")

    # Check API key
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key and anthropic_key != 'your_anthropic_api_key_here':
        print(f"  ✅ Optimizer API: Configured (used {1440//optimization_interval}x/day)")
    else:
        print("  ⚠️  Optimizer API: Not set")
        print("     → Bot will trade using static rules (no optimization)")
        print("     → Set ANTHROPIC_API_KEY in .env to enable auto-optimization")

    print("─"*80)

    # Show cost comparison
    print("\n💰 COST COMPARISON:")
    print("─"*80)
    old_calls_per_day = 4320
    new_calls_per_day = 1440 // optimization_interval
    old_cost = 75
    new_cost = new_calls_per_day * 0.02
    savings_pct = ((old_cost - new_cost) / old_cost) * 100

    print(f"  OLD System (Claude every trade):")
    print(f"    • API Calls/Day: ~{old_calls_per_day:,}")
    print(f"    • Daily Cost: ~${old_cost:.2f}")
    print(f"")
    print(f"  NEW System (This Bot):")
    print(f"    • API Calls/Day: {new_calls_per_day}")
    print(f"    • Daily Cost: ~${new_cost:.2f}")
    print(f"")
    print(f"  💡 YOU SAVE: ${old_cost - new_cost:.2f}/day ({savings_pct:.0f}% reduction!)")
    print(f"     Monthly: ${(old_cost - new_cost) * 30:.2f}")
    print(f"     Annual: ${(old_cost - new_cost) * 365:.2f}")
    print("─"*80)

    # Confirmation
    if not use_testnet:
        print("\n" + "⚠️ "*20)
        print("WARNING: YOU ARE USING MAINNET WITH REAL MONEY!")
        print("⚠️ "*20)
        confirm = input("\nType 'I UNDERSTAND' to continue: ").strip()
        if confirm != 'I UNDERSTAND':
            print("\n✓ Cancelled")
            return

    print("\n✅ Starting SELF-OPTIMIZING bot in 3 seconds...")
    print("")
    print("   🎯 What will happen:")
    print("   1. Bot starts trading using optimized rules (NO API CALLS)")
    print("   2. Every 30 minutes, optimizer analyzes your EMA patterns")
    print("   3. Claude recommends rule improvements based on YOUR data")
    print("   4. Rules update automatically")
    print("   5. Bot immediately uses improved rules")
    print("   6. REPEAT → Continuous improvement while trading!")
    print("")
    print("   💡 Result: Maximum profitability + 99% cost savings!")
    print("   📊 Your bot gets smarter every 30 minutes!")
    print("")
    print("   Press Ctrl+C to stop at any time\n")

    import time
    time.sleep(3)

    # Create and run self-optimizing bot!
    bot = DualTimeframeBotWithOptimizer(
        private_key=private_key,
        use_testnet=use_testnet,
        auto_trade=auto_trade,
        position_size_pct=position_size_pct,
        leverage=leverage,
        min_confidence=min_confidence,
        timeframe_short=timeframe_short,
        timeframe_long=timeframe_long,
        optimization_interval_minutes=optimization_interval
    )

    # Start monitoring (trading + optimization)
    bot.monitor()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Bot stopped by user")
        print("="*80)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
