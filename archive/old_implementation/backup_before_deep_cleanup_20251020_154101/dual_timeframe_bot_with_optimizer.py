"""
Dual Timeframe Bot with Integrated Optimizer
- Trades continuously using RuleBasedTrader (FREE, no API calls)
- Runs optimizer every 30 minutes in background thread
- Continuously improves trading rules based on actual performance
- Maximum profitability with 99% cost savings!
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
from dual_timeframe_bot import DualTimeframeBot
from rule_based_trader import RuleBasedTrader
from rule_optimizer import RuleOptimizer


class DualTimeframeBotWithOptimizer(DualTimeframeBot):
    """
    Enhanced bot that automatically optimizes its own trading rules
    Uses RuleBasedTrader instead of ClaudeTrader for FREE trading
    Runs optimizer every 30 minutes in background
    """

    def __init__(self, *args, optimization_interval_minutes: int = 30, **kwargs):
        """
        Initialize bot with automatic optimization

        Args:
            optimization_interval_minutes: How often to run optimization (default 30)
            *args, **kwargs: Same as DualTimeframeBot
        """
        super().__init__(*args, **kwargs)

        self.optimization_interval = optimization_interval_minutes
        self.last_optimization = datetime.now()
        self.optimizer = None
        self.optimizer_thread = None
        self.should_optimize = True
        self.optimization_count = 0

        # Replace ClaudeTrader with RuleBasedTrader
        print("\n🔧 Replacing expensive ClaudeTrader with FREE RuleBasedTrader...")
        self.claude = RuleBasedTrader()
        print("✅ Cost-optimized trader initialized!")

        # Initialize optimizer
        try:
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key and anthropic_key != 'your_anthropic_api_key_here':
                self.optimizer = RuleOptimizer(api_key=anthropic_key)
                print(f"✅ Optimizer initialized (runs every {optimization_interval_minutes} min)")
                print("💡 Your bot will continuously improve its trading rules!")
            else:
                print("⚠️  ANTHROPIC_API_KEY not set - optimizer disabled")
                print("   Bot will still trade using default rules")
                self.should_optimize = False
        except Exception as e:
            print(f"⚠️  Optimizer initialization failed: {e}")
            print("   Bot will still trade using default rules")
            self.should_optimize = False

    def get_trading_decision_optimized(self, indicators_5min: dict, indicators_15min: dict,
                                       current_price: float, current_position: Optional[dict] = None):
        """
        Get trading decision using RuleBasedTrader (FREE - no API calls!)

        Args:
            indicators_5min: 5-minute timeframe indicators
            indicators_15min: 15-minute timeframe indicators
            current_price: Current price
            current_position: Current position if any

        Returns:
            Decision dict from RuleBasedTrader
        """
        # Use 5min transition time (faster timeframe for scalping)
        # FIXED: Now passing ribbon_transition_time for freshness check
        ribbon_transition_time = getattr(self, 'ribbon_transition_time_5min', None)

        # Get decision from rule-based trader (NO API CALL!)
        decision = self.claude.get_trade_decision(
            indicators_5min=indicators_5min,
            indicators_15min=indicators_15min,
            current_price=current_price,
            ribbon_transition_time=ribbon_transition_time,
            current_position=current_position
        )

        return decision

    def run_optimization_cycle(self):
        """Run one optimization cycle (called every 30 minutes)"""
        try:
            print("\n" + "="*70)
            print("🔄 AUTOMATIC OPTIMIZATION CYCLE STARTING")
            print("="*70)
            print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 Cycle #{self.optimization_count + 1}")

            if not self.optimizer:
                print("⚠️  Optimizer not available - skipping")
                return

            # Run optimization
            self.optimizer.optimize_rules()

            self.optimization_count += 1
            self.last_optimization = datetime.now()

            print(f"✅ Optimization complete! Rules updated.")
            print(f"💡 Your bot is now smarter!")
            print(f"⏰ Next optimization in {self.optimization_interval} minutes")
            print("="*70 + "\n")

        except Exception as e:
            print(f"❌ Optimization cycle failed: {e}")
            import traceback
            traceback.print_exc()

    def optimization_scheduler(self):
        """Background thread that runs optimizer every N minutes"""
        print(f"\n🤖 Optimization scheduler started")
        print(f"   Running every {self.optimization_interval} minutes")

        # Wait initial period before first optimization (let data accumulate)
        initial_wait = min(self.optimization_interval * 60, 1800)  # Max 30min initial wait
        print(f"   First optimization in {initial_wait/60:.0f} minutes (accumulating data...)\n")
        time.sleep(initial_wait)

        while self.should_optimize:
            try:
                # Run optimization
                self.run_optimization_cycle()

                # Wait for next cycle
                time.sleep(self.optimization_interval * 60)

            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                time.sleep(60)  # Wait 1 minute before retry

    def start_optimizer_background(self):
        """Start the optimizer in a background thread"""
        if not self.should_optimize:
            print("⚠️  Optimizer disabled - trading with static rules")
            return

        self.optimizer_thread = threading.Thread(
            target=self.optimization_scheduler,
            daemon=True,
            name="OptimizerThread"
        )
        self.optimizer_thread.start()
        print("✅ Background optimizer thread started!")

    def monitor(self):
        """
        Main monitoring loop - trades continuously and optimizes in background
        """
        print("\n" + "="*70)
        print("🚀 STARTING COST-OPTIMIZED BOT WITH AUTO-OPTIMIZATION")
        print("="*70)
        print(f"💰 Trading: FREE (no API calls)")
        print(f"📊 Optimization: Every {self.optimization_interval} minutes")
        print(f"🎯 Result: Continuous improvement + 99% cost savings!")
        print("="*70 + "\n")

        # Start background optimizer
        self.start_optimizer_background()

        # Run the normal monitoring loop
        # The parent class will handle all the trading
        # Our RuleBasedTrader will be called instead of ClaudeTrader
        try:
            super().monitor()
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping bot...")
            self.should_optimize = False
            print("✅ Bot stopped")
            print(f"📊 Total optimizations performed: {self.optimization_count}")

    def get_decision_from_claude(self, *args, **kwargs):
        """
        Override parent's Claude decision method
        Now uses RuleBasedTrader instead!
        """
        # This gets called by the parent class
        # We redirect it to our rule-based trader

        # Extract the necessary data from args/kwargs
        # The parent class passes different formats, so we handle both

        if len(args) >= 3:
            # Called with positional args
            timeframe_data = args[0] if args else kwargs.get('timeframe_data')
            price = args[1] if len(args) > 1 else kwargs.get('price')
            position = args[2] if len(args) > 2 else kwargs.get('position')
        else:
            # Called with kwargs
            timeframe_data = kwargs.get('timeframe_data', {})
            price = kwargs.get('price', 0)
            position = kwargs.get('position', None)

        # Extract 5min and 15min indicators
        indicators_5min = timeframe_data.get('5min', {}).get('indicators', {})
        indicators_15min = timeframe_data.get('15min', {}).get('indicators', {})

        # Get decision from RuleBasedTrader (FREE!)
        decision = self.get_trading_decision_optimized(
            indicators_5min=indicators_5min,
            indicators_15min=indicators_15min,
            current_price=price,
            current_position=position
        )

        # Convert to format expected by parent class
        # RuleBasedTrader returns different format than ClaudeTrader
        # Map it to what the bot expects

        formatted_decision = {
            'action_type': decision.get('action', 'HOLD'),
            'direction': decision.get('direction', None),
            'entry_recommended': decision.get('entry_recommended', False),
            'exit_recommended': decision.get('exit_recommended', False),
            'confidence_score': decision.get('confidence', 0.0),
            'reasoning': decision.get('reasoning', ''),
            'entry_price': decision.get('entry_price', price),
            'stop_loss': decision.get('stop_loss', price * 0.997),
            'take_profit': decision.get('take_profit', price * 1.005),
            'position_management': 'HOLD',
            'timestamp': decision.get('timestamp', datetime.now().isoformat())
        }

        return formatted_decision


def main():
    """Test the integrated bot"""
    print("This file should be imported and used via run_dual_bot_optimized.py")
    print("See INTEGRATION_INSTRUCTIONS.md for usage details")


if __name__ == '__main__':
    main()
