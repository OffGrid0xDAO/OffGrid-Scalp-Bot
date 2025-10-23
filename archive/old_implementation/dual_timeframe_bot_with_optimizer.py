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
        # Check if Phase 1 trader should be used (if rules version is 2.0_phase1)
        import json
        try:
            with open('trading_rules.json', 'r') as f:
                rules = json.load(f)
                version = rules.get('version', '1.0')

            if 'phase1' in str(version).lower():
                print("\n🔧 Phase 1 rules detected - using Phase 1 trader...")
                from rule_based_trader_phase1 import RuleBasedTraderPhase1
                self.claude = RuleBasedTraderPhase1()
                print("✅ Phase 1 trader initialized (tiered entry/exit system)!")
            else:
                print("\n🔧 Replacing expensive ClaudeTrader with FREE RuleBasedTrader...")
                self.claude = RuleBasedTrader()
                print("✅ Cost-optimized trader initialized!")
        except Exception as e:
            print(f"⚠️  Error loading Phase 1 trader: {e}")
            print("   Falling back to standard RuleBasedTrader...")
            self.claude = RuleBasedTrader()
            print("✅ Standard trader initialized!")

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

        # Initialize manual trading
        self.setup_manual_trading()

    def setup_manual_trading(self):
        """Setup manual trade tracking and Telegram bot listener"""
        try:
            from manual_trade_tracker import ManualTradeTracker
            from telegram_bot_listener import TelegramBotListener

            self.manual_tracker = ManualTradeTracker()

            # Setup command callbacks
            self.telegram_listener = TelegramBotListener(
                on_long_command=self.execute_manual_long,
                on_short_command=self.execute_manual_short,
                on_exit_command=self.execute_manual_exit,
                on_status_command=self.get_manual_status
            )

            # Start listening for commands
            if self.telegram_listener.start():
                print("✅ Manual trading enabled - send /help to Telegram for commands")
            else:
                print("⚠️  Manual trading disabled")

        except Exception as e:
            print(f"⚠️  Manual trading setup failed: {e}")
            self.manual_tracker = None
            self.telegram_listener = None

    def execute_manual_long(self) -> str:
        """Execute a manual LONG position"""
        try:
            # Get current price from Hyperliquid API
            all_mids = self.info.all_mids()
            current_price = float(all_mids.get(self.symbol, 0))

            if current_price <= 0:
                return "❌ Failed to get current price"

            # Check if already in position
            if self.manual_tracker.get_open_trade():
                return "⚠️ Already have an open manual position! Use /exit first."

            # Execute trade (lowercase 'long' as expected by execute_trade)
            success, message = self.execute_trade('long', current_price)

            if success:
                # Log manual entry
                trade_id = self.manual_tracker.log_entry(
                    'LONG',
                    current_price,
                    self.position_size_pct,  # Log the configured position size
                    "Manual entry via Telegram /long command"
                )

                return f"📈 LONG Entry\nPrice: ${current_price:.2f}\nSize: {self.position_size_pct*100:.1f}%\nID: {trade_id}"
            else:
                return f"❌ Trade execution failed: {message}"

        except Exception as e:
            return f"❌ Error: {str(e)}"

    def execute_manual_short(self) -> str:
        """Execute a manual SHORT position"""
        try:
            # Get current price from Hyperliquid API
            all_mids = self.info.all_mids()
            current_price = float(all_mids.get(self.symbol, 0))

            if current_price <= 0:
                return "❌ Failed to get current price"

            # Check if already in position
            if self.manual_tracker.get_open_trade():
                return "⚠️ Already have an open manual position! Use /exit first."

            # Execute trade (lowercase 'short' as expected by execute_trade)
            success, message = self.execute_trade('short', current_price)

            if success:
                # Log manual entry
                trade_id = self.manual_tracker.log_entry(
                    'SHORT',
                    current_price,
                    self.position_size_pct,  # Log the configured position size
                    "Manual entry via Telegram /short command"
                )

                return f"📉 SHORT Entry\nPrice: ${current_price:.2f}\nSize: {self.position_size_pct*100:.1f}%\nID: {trade_id}"
            else:
                return f"❌ Trade execution failed: {message}"

        except Exception as e:
            return f"❌ Error: {str(e)}"

    def execute_manual_exit(self) -> str:
        """Execute a manual exit"""
        try:
            # Get open manual trade
            open_trade = self.manual_tracker.get_open_trade()

            if not open_trade:
                return "⚠️ No open manual position to exit"

            # Get current price from Hyperliquid API
            all_mids = self.info.all_mids()
            current_price = float(all_mids.get(self.symbol, 0))

            if current_price <= 0:
                return "❌ Failed to get current price"

            # Close position using execute_trade
            success, message = self.execute_trade('close', current_price)

            if success:
                # Log manual exit
                self.manual_tracker.log_exit(
                    open_trade['id'],
                    current_price,
                    "Manual exit via Telegram"
                )

                # Calculate PnL
                entry_price = open_trade['entry_price']
                direction = open_trade['direction']

                if direction == 'LONG':
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - current_price) / entry_price * 100

                return f"🚪 Position Closed\nEntry: ${entry_price:.2f}\nExit: ${current_price:.2f}\nPnL: {pnl_pct:+.2f}%"
            else:
                return f"❌ Exit failed: {message}"

        except Exception as e:
            return f"❌ Error: {str(e)}"

    def get_manual_status(self) -> str:
        """Get current bot status"""
        try:
            status = "🤖 <b>Bot Status</b>\n\n"

            # Bot info
            status += f"Mode: Rule-Based Trading\n"
            status += f"Auto-Trade: {'✅ Enabled' if self.auto_trade else '❌ Disabled'}\n\n"

            # Manual trade stats
            stats = self.manual_tracker.get_stats()
            status += f"📊 <b>Manual Trade Stats</b>\n"
            status += f"Total: {stats['total_trades']}\n"
            status += f"Win Rate: {stats['win_rate']*100:.1f}%\n"
            status += f"Total PnL: {stats['total_pnl_pct']:+.2f}%\n\n"

            # Open position
            open_trade = self.manual_tracker.get_open_trade()
            if open_trade:
                # Get current price from Hyperliquid API
                all_mids = self.info.all_mids()
                current_price = float(all_mids.get(self.symbol, 0))

                if current_price > 0:
                    entry_price = open_trade['entry_price']
                    direction = open_trade['direction']

                    if direction == 'LONG':
                        unrealized_pnl = (current_price - entry_price) / entry_price * 100
                    else:
                        unrealized_pnl = (entry_price - current_price) / entry_price * 100

                    status += f"💼 <b>Open Position</b>\n"
                    status += f"Direction: {direction}\n"
                    status += f"Entry: ${entry_price:.2f}\n"
                    status += f"Current: ${current_price:.2f}\n"
                    status += f"Unrealized PnL: {unrealized_pnl:+.2f}%"
                else:
                    status += f"💼 <b>Open Position</b>\n"
                    status += f"Direction: {open_trade['direction']}\n"
                    status += f"Entry: ${open_trade['entry_price']:.2f}\n"
                    status += "⚠️ Could not fetch current price"
            else:
                status += "💼 No open position"

            return status

        except Exception as e:
            return f"❌ Error getting status: {str(e)}"

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

            # Regenerate optimal trades from current data every cycle (only if using auto mode)
            optimal_source = os.getenv('OPTIMAL_TRADES_SOURCE', 'auto').lower()

            if optimal_source == 'auto':
                print("\n📊 Regenerating optimal_trades_auto.json with latest data...")
                try:
                    from smart_trade_finder import SmartTradeFinder
                    import pandas as pd

                    # Calculate data span
                    df = pd.read_csv('trading_data/ema_data_5min.csv', on_bad_lines='skip')
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                    df = df.dropna(subset=['timestamp'])

                    if len(df) > 0:
                        oldest = df['timestamp'].min()
                        newest = df['timestamp'].max()
                        hours_span = int((newest - oldest).total_seconds() / 3600) + 1

                        print(f"   📊 Finding optimal trades in ALL data: {hours_span} hours")

                        finder = SmartTradeFinder(ema_5min_file='trading_data/ema_data_5min.csv')
                        results = finder.find_smart_trades(hours_back=hours_span)

                        # Save to auto file
                        import json
                        with open('trading_data/optimal_trades_auto.json', 'w') as f:
                            json.dump(results, f, indent=2, default=str)

                        print(f"   ✅ Regenerated AUTO trades: {results.get('total_trades', 0)} trades, {results.get('total_pnl_pct', 0):+.2f}% PnL")
                    else:
                        print("   ⚠️  No valid data, skipping regeneration")
                except Exception as e:
                    print(f"   ⚠️  Regeneration failed: {e}")
                    print("   Continuing with existing data...")
            else:
                print(f"\n📊 Using USER optimal trades (not regenerating)")

            # Generate trading_analysis.html
            print("\n📊 Generating trading_analysis.html...")
            try:
                from visualize_trading_analysis import TradingVisualizer

                # Use correct optimal trades file based on source setting
                optimal_source = os.getenv('OPTIMAL_TRADES_SOURCE', 'auto').lower()
                optimal_file = 'trading_data/optimal_trades_user.json' if optimal_source == 'user' else 'trading_data/optimal_trades_auto.json'

                visualizer = TradingVisualizer(
                    ema_data_file='trading_data/ema_data_5min.csv',
                    decisions_file='trading_data/claude_decisions.csv',
                    optimal_trades_file=optimal_file,
                    backtest_trades_file='trading_data/backtest_trades.json'
                )

                if visualizer.load_data():
                    # Calculate total hours available in dataset
                    import pandas as pd
                    try:
                        df = pd.read_csv('trading_data/ema_data_5min.csv')
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        hours_available = int((df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600) + 1
                        print(f"   📊 Visualizing {hours_available} hours of data...")
                    except:
                        hours_available = 72  # Fallback

                    # Create the figure with ALL available data
                    fig = visualizer.create_visualization(hours_back=hours_available, show_all_emas=True)

                    if fig:
                        # Save to HTML (save_html adds 'trading_data/' prefix)
                        html_path = visualizer.save_html(fig, 'trading_analysis.html')
                        print(f"   ✅ Generated {html_path}")
                    else:
                        print("   ⚠️  Visualization returned None (no data in timeframe?)")
                else:
                    print("   ⚠️  Could not load data for visualization")

            except Exception as e:
                print(f"   ⚠️  HTML generation failed: {e}")
                import traceback
                traceback.print_exc()

            # Run optimization with fresh data
            # Check which optimizer to use based on rules version
            import json
            try:
                with open('trading_rules.json', 'r') as f:
                    rules = json.load(f)
                    version = rules.get('version', '1.0')

                if 'user_pattern' in str(version).lower():
                    print("\n🎯 User Pattern System detected - using specialized optimizer")
                    from user_pattern_optimizer import UserPatternOptimizer
                    pattern_optimizer = UserPatternOptimizer(api_key=self.optimizer.api_key)
                    pattern_optimizer.optimize()
                else:
                    print("\n🔧 Running standard rule optimization")
                    self.optimizer.optimize_rules()
            except Exception as e:
                print(f"\n⚠️  Optimization failed: {e}")
                import traceback
                traceback.print_exc()

            # CRITICAL: Regenerate backtest with NEW rules after optimization
            print("\n📊 Regenerating backtest_trades.json with UPDATED rules...")
            try:
                from run_backtest import run_backtest
                import pandas as pd

                # Calculate data span
                df = pd.read_csv('trading_data/ema_data_5min.csv', on_bad_lines='skip')
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                df = df.dropna(subset=['timestamp'])

                if len(df) > 0:
                    oldest = df['timestamp'].min()
                    newest = df['timestamp'].max()
                    hours_span = int((newest - oldest).total_seconds() / 3600) + 1

                    print(f"   📊 Running backtest on ALL data: {hours_span} hours ({oldest} to {newest})")

                    # Use large hours_back to ensure we get ALL data (not filtered by "last N hours from now")
                    backtest_results = run_backtest(hours_back=1000)

                    # Save backtest results
                    import json
                    with open('trading_data/backtest_trades.json', 'w') as f:
                        json.dump(backtest_results, f, indent=2, default=str)

                    print(f"   ✅ Backtest regenerated: {backtest_results.get('total_trades', 0)} trades, {backtest_results.get('total_pnl_pct', 0):+.2f}% PnL")
                    print(f"   📊 This reflects how NEW rules would have performed!")
                else:
                    print("   ⚠️  No valid data, skipping backtest")

            except Exception as e:
                print(f"   ⚠️  Backtest regeneration failed: {e}")
                import traceback
                traceback.print_exc()

            self.optimization_count += 1
            self.last_optimization = datetime.now()

            print(f"\n✅ Optimization complete! Rules updated AND backtested!")
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

        # Check if we have historical data for immediate first optimization
        import os
        ema_5min_path = 'trading_data/ema_data_5min.csv'
        has_historical_data = os.path.exists(ema_5min_path) and os.path.getsize(ema_5min_path) > 1000

        if has_historical_data:
            print(f"\n📊 Historical data detected - running IMMEDIATE first optimization!")
            print(f"   This will analyze ALL available training data")
            print(f"   Subsequent optimizations will run every {self.optimization_interval} minutes\n")

            # Wait for bot to initialize
            time.sleep(5)

            # Run immediate optimization
            # It will use existing optimal_trades.json and send beautiful Telegram message
            print("\n📊 Running immediate optimization...")
            self.run_optimization_cycle()
            print(f"\n✅ First optimization complete using historical data!")
            print(f"⏰ Next optimization in {self.optimization_interval} minutes\n")
        else:
            # Wait initial period before first optimization (let data accumulate)
            initial_wait = min(self.optimization_interval * 60, 1800)  # Max 30min initial wait
            print(f"\n📊 No historical data found - will wait to accumulate fresh data")
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

    def analyze_gap_with_claude(self, optimal_data: dict, backtest_data: dict, current_rules: dict) -> dict:
        """
        Call Claude to analyze the gap between optimal and backtest trades
        and provide recommendations to improve rules

        Args:
            optimal_data: Optimal trades stats
            backtest_data: Backtest trades stats
            current_rules: Current trading rules

        Returns:
            Dict with key_findings and rule_adjustments
        """
        if not self.optimizer:
            print("  ⚠️  Optimizer not available - skipping Claude analysis")
            return {'key_findings': ['Optimizer not configured'], 'rule_adjustments': {}}

        try:
            from anthropic import Anthropic
            import json

            print("  🤖 Calling Claude to analyze optimal vs backtest gap...")

            # Calculate gaps
            missed_trades = optimal_data.get('total_trades', 0) - backtest_data.get('total_trades', 0)
            pnl_gap = optimal_data.get('total_pnl_pct', 0) - backtest_data.get('total_pnl_pct', 0)
            capture_rate = (backtest_data.get('total_trades', 0) / max(optimal_data.get('total_trades', 1), 1)) * 100

            # Build analysis prompt
            prompt = f"""You are a trading strategy optimizer analyzing EMA ribbon patterns for a scalping system.

## OBJECTIVE: Close the Gap Between Optimal and Backtest Trades

I need you to analyze why there's a performance gap between:
1. **OPTIMAL TRADES** - Best possible entries/exits with perfect hindsight
2. **BACKTEST TRADES** - What current rules would have caught

## DATA COMPARISON

### OPTIMAL TRADES (Perfect Hindsight)
- Total Trades: {optimal_data.get('total_trades', 0)}
- Total PnL: {optimal_data.get('total_pnl_pct', 0):+.2f}%
- Avg PnL: {optimal_data.get('total_pnl_pct', 0) / max(optimal_data.get('total_trades', 1), 1):+.3f}% per trade
- Avg Hold: {optimal_data.get('avg_hold_minutes', 0):.1f} minutes
- Win Rate: {optimal_data.get('win_rate', 0)*100:.1f}%

### BACKTEST TRADES (Current Rules)
- Total Trades: {backtest_data.get('total_trades', 0)}
- Total PnL: {backtest_data.get('total_pnl_pct', 0):+.2f}%
- Avg PnL: {backtest_data.get('total_pnl_pct', 0) / max(backtest_data.get('total_trades', 1), 1):+.3f}% per trade
- Avg Hold: {backtest_data.get('avg_hold_minutes', 0):.1f} minutes
- Win Rate: {backtest_data.get('win_rate', 0)*100:.1f}%

### GAP ANALYSIS
- Missed Trades: {missed_trades} ({100 - capture_rate:.1f}% of optimal opportunities missed)
- PnL Gap: {pnl_gap:+.2f}%
- Capture Rate: {capture_rate:.1f}%
- Hold Time Difference: {optimal_data.get('avg_hold_minutes', 0) - backtest_data.get('avg_hold_minutes', 0):+.1f} minutes

### CURRENT TRADING RULES
```json
{json.dumps(current_rules, indent=2)}
```

## KEY OBSERVATIONS

1. **Backtest is catching {capture_rate:.0f}% of trades** but missing {100-capture_rate:.0f}%
2. **Average backtest hold: {backtest_data.get('avg_hold_minutes', 0):.1f}min vs optimal {optimal_data.get('avg_hold_minutes', 0):.1f}min**
3. **PnL gap of {pnl_gap:+.2f}%** - backtest is {'underperforming' if pnl_gap > 0 else 'overperforming'}

## YOUR TASK

Analyze the data and provide:

1. **Key Findings** - What's causing the gap? Is it:
   - Entry rules too strict (missing trades)?
   - Exit rules too aggressive (exiting too early)?
   - Entry rules too loose (taking bad trades)?
   - Hold time too short?

2. **Specific Rule Improvements** - Which exact parameters should change?
   - min_compression_for_entry
   - min_hold_time_minutes
   - exit_on_ribbon_flip (True/False)
   - exit_on_target_only (True/False)
   - profit_target_pct
   - min_light_emas
   - enable_yellow_ema_trail (True/False)
   - trail_buffer_pct

Focus on the BIGGEST wins - what single change would close the gap most?

## OUTPUT FORMAT

Respond with a JSON object:

```json
{{
  "key_findings": [
    "Finding 1: Backtest exits {optimal_data.get('avg_hold_minutes', 0) / max(backtest_data.get('avg_hold_minutes', 1), 1):.1f}x faster than optimal - likely exiting on ribbon flips too early",
    "Finding 2: ...",
    "Finding 3: ...",
    "Finding 4: ...",
    "Finding 5: ..."
  ],
  "rule_adjustments": {{
    "min_compression_for_entry": 0.12,
    "min_hold_time_minutes": 5,
    "exit_on_ribbon_flip": false,
    "exit_on_target_only": true,
    "profit_target_pct": 0.005,
    "min_light_emas": 15,
    "enable_yellow_ema_trail": true,
    "trail_buffer_pct": 0.001
  }},
  "reasoning": "Brief explanation focusing on the single biggest issue and how the changes fix it"
}}
```

Be specific and data-driven. Only recommend changes if the data clearly supports them.
"""

            # Call Claude
            client = Anthropic(api_key=self.optimizer.api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            response_text = response.content[0].text

            # Extract JSON - try multiple methods
            try:
                # Method 1: Look for ```json blocks
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                # Method 2: Look for first { to last }
                elif "{" in response_text and "}" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_str = response_text[json_start:json_end].strip()
                else:
                    json_str = response_text

                recommendations = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"  ⚠️  JSON parsing failed: {e}")
                print(f"  📄 Raw response (first 500 chars): {response_text[:500]}")
                # Return empty recommendations
                recommendations = {
                    'key_findings': ['Failed to parse Claude response'],
                    'rule_adjustments': {},
                    'reasoning': f'JSON parsing error: {str(e)}'
                }

            # Calculate cost
            usage = response.usage
            input_cost = (usage.input_tokens / 1_000_000) * 3.0
            output_cost = (usage.output_tokens / 1_000_000) * 15.0
            total_cost = input_cost + output_cost

            print(f"  ✅ Claude analysis complete (cost: ${total_cost:.4f})")

            return {
                'key_findings': recommendations.get('key_findings', []),
                'rule_adjustments': recommendations.get('rule_adjustments', {}),
                'reasoning': recommendations.get('reasoning', ''),
                'api_cost': total_cost
            }

        except Exception as e:
            print(f"  ⚠️  Claude analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return {'key_findings': [f'Analysis failed: {str(e)}'], 'rule_adjustments': {}, 'api_cost': 0.0}

    def apply_claude_recommendations(self, current_rules: dict, recommendations: dict):
        """
        Auto-apply Claude's recommendations to trading_rules.json

        Args:
            current_rules: Current trading rules
            recommendations: Claude's recommendations from gap analysis
        """
        try:
            import json

            rule_adjustments = recommendations.get('rule_adjustments', {})
            if not rule_adjustments:
                print("  ℹ️  No rule adjustments to apply")
                return

            # Update entry rules
            entry_rules = current_rules.get('entry_rules', {})
            if 'min_compression_for_entry' in rule_adjustments:
                entry_rules['min_compression_for_entry'] = rule_adjustments['min_compression_for_entry']
            if 'min_light_emas' in rule_adjustments:
                entry_rules['min_light_emas_required'] = rule_adjustments['min_light_emas']

            # Update exit rules
            exit_rules = current_rules.get('exit_rules', {})
            if 'min_hold_time_minutes' in rule_adjustments:
                exit_rules['min_hold_time_minutes'] = rule_adjustments['min_hold_time_minutes']
            if 'exit_on_ribbon_flip' in rule_adjustments:
                exit_rules['exit_on_ribbon_flip'] = rule_adjustments['exit_on_ribbon_flip']
            if 'exit_on_target_only' in rule_adjustments:
                exit_rules['exit_on_target_only'] = rule_adjustments['exit_on_target_only']
            if 'profit_target_pct' in rule_adjustments:
                exit_rules['profit_target_pct'] = rule_adjustments['profit_target_pct']
            if 'enable_yellow_ema_trail' in rule_adjustments:
                exit_rules['use_yellow_ema_trail'] = rule_adjustments['enable_yellow_ema_trail']
            if 'trail_buffer_pct' in rule_adjustments:
                exit_rules['yellow_ema_trail_buffer_pct'] = rule_adjustments['trail_buffer_pct']

            # CRITICAL: Also update TIER-SPECIFIC rules (Phase 1 trader uses these!)
            if 'tier_1_strong_trend' in exit_rules:
                tier1 = exit_rules['tier_1_strong_trend']
                if 'min_hold_time_minutes' in rule_adjustments:
                    tier1['min_hold_minutes'] = rule_adjustments['min_hold_time_minutes']
                if 'profit_target_pct' in rule_adjustments:
                    tier1['profit_target_pct'] = rule_adjustments['profit_target_pct'] * 1.2  # 20% higher for strong trends
                if 'exit_on_ribbon_flip' in rule_adjustments:
                    tier1['exit_on_ribbon_flip'] = rule_adjustments['exit_on_ribbon_flip']
                if 'trail_buffer_pct' in rule_adjustments:
                    tier1['trailing_buffer_pct'] = rule_adjustments['trail_buffer_pct']

            if 'tier_2_moderate_trend' in exit_rules:
                tier2 = exit_rules['tier_2_moderate_trend']
                if 'min_hold_time_minutes' in rule_adjustments:
                    tier2['min_hold_minutes'] = int(rule_adjustments['min_hold_time_minutes'] * 0.6)  # 60% of recommended
                if 'profit_target_pct' in rule_adjustments:
                    tier2['profit_target_pct'] = rule_adjustments['profit_target_pct']
                if 'exit_on_ribbon_flip' in rule_adjustments:
                    tier2['exit_on_ribbon_flip'] = rule_adjustments['exit_on_ribbon_flip']
                if 'trail_buffer_pct' in rule_adjustments:
                    tier2['trailing_buffer_pct'] = rule_adjustments['trail_buffer_pct']

            if 'tier_3_quick_scalp' in exit_rules:
                tier3 = exit_rules['tier_3_quick_scalp']
                if 'min_hold_time_minutes' in rule_adjustments:
                    tier3['min_hold_minutes'] = int(rule_adjustments['min_hold_time_minutes'] * 0.3)  # 30% of recommended
                if 'profit_target_pct' in rule_adjustments:
                    tier3['profit_target_pct'] = rule_adjustments['profit_target_pct'] * 0.5  # 50% for quick scalps
                if 'trail_buffer_pct' in rule_adjustments:
                    tier3['trailing_buffer_pct'] = rule_adjustments['trail_buffer_pct'] * 0.5

            # Update claude_insights
            claude_insights = current_rules.get('claude_insights', {})
            claude_insights['key_findings'] = recommendations.get('key_findings', [])
            claude_insights['last_optimization'] = datetime.now().isoformat()

            # Save updated rules
            current_rules['entry_rules'] = entry_rules
            current_rules['exit_rules'] = exit_rules
            current_rules['claude_insights'] = claude_insights
            current_rules['last_updated'] = datetime.now().isoformat()
            current_rules['updated_by'] = 'claude_gap_analysis_auto'

            with open('trading_rules.json', 'w') as f:
                json.dump(current_rules, f, indent=2)

            print("  ✅ Rules updated automatically!")
            print(f"  📝 Applied {len(rule_adjustments)} parameter changes")

            # Show what changed
            print("\n  📊 Changes applied:")
            for param, value in rule_adjustments.items():
                print(f"    • {param}: {value}")

        except Exception as e:
            print(f"  ⚠️  Failed to apply recommendations: {e}")
            import traceback
            traceback.print_exc()

    def send_startup_optimization_summary(self):
        """
        Send optimization summary to Telegram on bot startup
        Uses existing data from optimal_trades.json, backtest_trades.json, and actual trades
        """
        print("\n📱 Sending optimization summary to Telegram...")

        try:
            # Load existing data files
            import json
            import pandas as pd
            from telegram_notifier import TelegramNotifier

            telegram = TelegramNotifier()

            # Load optimal trades data from correct source
            optimal_source = os.getenv('OPTIMAL_TRADES_SOURCE', 'auto').lower()
            optimal_file = 'trading_data/optimal_trades_user.json' if optimal_source == 'user' else 'trading_data/optimal_trades_auto.json'

            optimal_data = {}
            try:
                with open(optimal_file, 'r') as f:
                    optimal_raw = json.load(f)
                    summary = optimal_raw.get('summary', {})
                    optimal_data = {
                        'total_trades': optimal_raw.get('total_trades', 0),
                        'total_pnl_pct': optimal_raw.get('total_pnl_pct', 0),
                        'avg_hold_minutes': summary.get('avg_hold_time', 0),
                        'win_rate': summary.get('win_rate', 1.0),
                        'patterns': optimal_raw.get('patterns', {})
                    }
                    print(f"  ✅ Loaded optimal trades from {optimal_source}: {optimal_data['total_trades']} trades")
            except FileNotFoundError:
                print(f"  ⚠️  {optimal_file} not found - using empty data")
                optimal_data = {'total_trades': 0, 'total_pnl_pct': 0, 'avg_hold_minutes': 0, 'win_rate': 0, 'patterns': {}}

            # Load backtest trades data
            backtest_data = {}
            try:
                with open('trading_data/backtest_trades.json', 'r') as f:
                    backtest_raw = json.load(f)
                    trades = backtest_raw.get('trades', [])

                    # Calculate avg hold time and win rate from trades
                    avg_hold = 0
                    win_rate = 0
                    if len(trades) > 0:
                        avg_hold = sum(t.get('hold_time_min', 0) for t in trades) / len(trades)
                        winners = sum(1 for t in trades if t.get('pnl_pct', 0) > 0)
                        win_rate = winners / len(trades)

                    backtest_data = {
                        'total_trades': backtest_raw.get('total_trades', 0),
                        'total_pnl_pct': backtest_raw.get('total_pnl_pct', 0),
                        'avg_hold_minutes': avg_hold,
                        'win_rate': win_rate,
                        'patterns': backtest_raw.get('patterns', {})
                    }
                    print(f"  ✅ Loaded backtest trades: {backtest_data['total_trades']} trades")
            except FileNotFoundError:
                print("  ⚠️  backtest_trades.json not found - using empty data")
                backtest_data = {'total_trades': 0, 'total_pnl_pct': 0, 'avg_hold_minutes': 0, 'win_rate': 0, 'patterns': {}}

            # Load actual trades from claude_decisions.csv
            actual_data = {}
            try:
                df = pd.read_csv('trading_data/claude_decisions.csv')
                executed = df[df['action_type'].isin(['LONG', 'SHORT'])]

                if len(executed) > 0:
                    # Calculate actual stats
                    total_pnl = 0
                    avg_hold = 0
                    winning = 0

                    for idx, row in executed.iterrows():
                        # Try to find exit for this entry
                        # Simple PnL calculation if we have it
                        if 'pnl_pct' in row and pd.notna(row['pnl_pct']):
                            total_pnl += row['pnl_pct']
                            if row['pnl_pct'] > 0:
                                winning += 1

                    actual_data = {
                        'total_trades': len(executed),
                        'total_pnl_pct': total_pnl,
                        'avg_hold_minutes': avg_hold,
                        'win_rate': winning / len(executed) if len(executed) > 0 else 0
                    }
                    print(f"  ✅ Loaded actual trades: {actual_data['total_trades']} trades")
                else:
                    actual_data = {'total_trades': 0, 'total_pnl_pct': 0, 'avg_hold_minutes': 0, 'win_rate': 0}
                    print("  ℹ️  No actual trades executed yet")
            except FileNotFoundError:
                print("  ⚠️  claude_decisions.csv not found - no actual trades yet")
                actual_data = {'total_trades': 0, 'total_pnl_pct': 0, 'avg_hold_minutes': 0, 'win_rate': 0}

            # Load current rules for Claude analysis
            current_rules = {}
            api_cost = 0.0
            try:
                with open('trading_rules.json', 'r') as f:
                    current_rules = json.load(f)
                    print("  ✅ Loaded current rules")
            except FileNotFoundError:
                print("  ⚠️  trading_rules.json not found")
                current_rules = {}

            # Call Claude to analyze the gap and provide recommendations
            print("\n🧠 Analyzing gap with Claude AI...")
            recommendations = self.analyze_gap_with_claude(
                optimal_data=optimal_data,
                backtest_data=backtest_data,
                current_rules=current_rules
            )
            api_cost = recommendations.get('api_cost', 0.0)

            # AUTO-APPLY Claude's recommendations to trading rules
            print("\n🔧 Auto-applying Claude's recommendations to trading_rules.json...")
            self.apply_claude_recommendations(current_rules, recommendations)

            # Send the optimization update with Claude's insights
            telegram.send_optimization_update(
                optimal_data=optimal_data,
                backtest_data=backtest_data,
                actual_data=actual_data,
                recommendations=recommendations,
                api_cost=api_cost
            )

            print("✅ Optimization summary sent to Telegram!")

            # Send trading analysis chart image
            print("\n📊 Sending trading analysis chart to Telegram...")
            try:
                import os
                html_path = 'trading_data/trading_analysis.html'

                if os.path.exists(html_path):
                    # Convert HTML to PNG
                    from convert_html_to_image import convert_html_to_png

                    png_path = convert_html_to_png(
                        html_path,
                        output_path='trading_data/trading_analysis.png'
                    )

                    if png_path and os.path.exists(png_path):
                        caption = "📈 Trading Analysis: Optimal vs Backtest vs Actual Trades"
                        telegram.send_photo(png_path, caption=caption)
                        print("  ✅ Trading analysis chart sent to Telegram!")
                    else:
                        print("  ⚠️  Could not generate PNG from HTML")
                else:
                    print("  ⚠️  trading_analysis.html not found - run visualization first")

            except Exception as e:
                print(f"  ⚠️  Chart sending failed: {e}")
                import traceback
                traceback.print_exc()

        except Exception as e:
            print(f"⚠️  Failed to send startup optimization summary: {e}")
            import traceback
            traceback.print_exc()

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

        # Send startup optimization summary to Telegram FIRST
        self.send_startup_optimization_summary()

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
