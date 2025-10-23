"""
Initialize Trading Rules - First Time Setup
Analyzes ALL your historical EMA data to create optimal starting rules
This runs ONCE before starting the bot for the first time

This will:
1. Load ALL historical EMA data (not just 30 minutes)
2. Find ALL profitable ribbon flip patterns
3. Analyze EMA color combinations that won vs lost
4. Call Claude to create optimal initial rules
5. Save to trading_rules.json
6. Your bot starts with PROVEN rules, not defaults!
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from anthropic import Anthropic
from optimal_trade_finder_30min import OptimalTradeFinder
from big_movement_ema_analyzer import BigMovementEMAAnalyzer


class TradingRulesInitializer:
    """Creates optimal trading rules from ALL historical data"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

        # Paths
        self.rules_path = 'trading_rules.json'
        self.ema_5min_path = 'trading_data/ema_data_5min.csv'
        self.ema_15min_path = 'trading_data/ema_data_15min.csv'
        self.decisions_log_path = 'trading_data/claude_decisions.csv'

        # Cost tracking
        self.total_cost = 0.0

        print("🔧 Trading Rules Initializer")
        print("   Analyzes ALL historical data for optimal starting rules")

    def analyze_all_historical_data(self) -> dict:
        """Analyze ALL available historical data (not just 30 minutes)"""
        print("\n" + "="*70)
        print("📊 ANALYZING ALL HISTORICAL DATA")
        print("="*70)

        try:
            # Load full datasets
            df_5min = pd.read_csv(self.ema_5min_path)
            df_15min = pd.read_csv(self.ema_15min_path)

            df_5min['timestamp'] = pd.to_datetime(df_5min['timestamp'])
            df_15min['timestamp'] = pd.to_datetime(df_15min['timestamp'])

            total_hours = (df_5min['timestamp'].max() - df_5min['timestamp'].min()).total_seconds() / 3600

            print(f"✅ Loaded 5min data: {len(df_5min):,} snapshots ({total_hours:.1f} hours)")
            print(f"✅ Loaded 15min data: {len(df_15min):,} snapshots")
            print(f"📅 Date range: {df_5min['timestamp'].min()} to {df_5min['timestamp'].max()}")

            # Use the optimal trade finder but on ALL data
            finder = OptimalTradeFinder(self.ema_5min_path, self.ema_15min_path)

            # Override to use all data instead of last 30 min
            finder.load_last_30min = lambda: (df_5min, df_15min)

            results = finder.analyze_optimal_setups()

            print(f"\n📈 HISTORICAL ANALYSIS RESULTS:")
            print(f"   Total ribbon flips found: {results['total_ribbon_flips']}")
            print(f"   Winning trades: {results['winning_trades']}")
            print(f"   Losing trades: {results['losing_trades']}")
            print(f"   Win rate: {results['win_rate']*100:.1f}%")
            print(f"   Avg winner P&L: {results.get('avg_winner_pnl_pct', 0):.2f}%")
            print(f"   Avg loser P&L: {results.get('avg_loser_pnl_pct', 0):.2f}%")

            return results

        except FileNotFoundError as e:
            print(f"❌ Error: EMA data files not found")
            print(f"   Make sure your bot has run and collected data first!")
            print(f"   Looking for: {self.ema_5min_path}")
            raise

    def build_initialization_prompt(self, historical_results: dict, big_movement_analysis: dict = None) -> str:
        """Build comprehensive prompt for Claude to create initial rules"""

        winning_patterns = historical_results.get('winning_patterns', [])
        losing_patterns = historical_results.get('losing_patterns', [])

        # Deep pattern analysis
        winning_analysis = self._deep_pattern_analysis(winning_patterns)
        losing_analysis = self._deep_pattern_analysis(losing_patterns)

        prompt = f"""You are initializing a trading bot's rules based on comprehensive historical analysis.

## CRITICAL PRIORITY: CATCH BIG MOVEMENTS!

Your #1 goal is to create rules that ensure we NEVER miss a big price movement (>0.5% in 5min).
These big movements are the most profitable trades. The rules you create should prioritize catching ALL of them.

## MISSION
Analyze ALL historical EMA ribbon pattern data and create the OPTIMAL initial trading rules.
These rules will be the starting point for continuous optimization.

## HISTORICAL DATA ANALYSIS

### Overall Performance
- Total Ribbon Flips Analyzed: {historical_results.get('total_ribbon_flips', 0)}
- Winning Trades: {historical_results.get('winning_trades', 0)}
- Losing Trades: {historical_results.get('losing_trades', 0)}
- Historical Win Rate: {historical_results.get('win_rate', 0)*100:.1f}%
- Avg Winner P&L: {historical_results.get('avg_winner_pnl_pct', 0):.2f}%
- Avg Loser P&L: {historical_results.get('avg_loser_pnl_pct', 0):.2f}%

### WINNING PATTERN CHARACTERISTICS
{winning_analysis}

### LOSING PATTERN CHARACTERISTICS
{losing_analysis}

### BIG MOVEMENT ANALYSIS (ALL HISTORICAL DATA)
{self._format_big_movement_analysis(big_movement_analysis)}

## YOUR TASK

Based on this historical data, create OPTIMAL trading rules that:

1. **EMA Color Pattern Rules:**
   - What % of green/red EMAs indicates best entry? (85%? 90%? 95%?)
   - How many LIGHT EMAs are needed for strong momentum?
   - Should we require dark EMAs to be transitioning?
   - What ribbon states (all_green, mixed_green, etc) work best?

2. **Entry Timing Rules:**
   - How fresh should a transition be? (5min? 10min? 15min?)
   - When is a setup too stale to enter?
   - Which entry paths (dark transition, wick reversal, etc) have highest win rate?

3. **Exit Rules:**
   - Optimal profit target based on historical avg winner?
   - Optimal stop loss based on historical avg loser?
   - Best max hold time before forced exit?
   - Should we use yellow EMA trailing stops?

4. **Pattern Priorities:**
   - Rank the 5 entry paths (A-E) by historical success
   - Which patterns should get confidence boosts?
   - Which patterns should be disabled initially?

## OUTPUT FORMAT

Respond with a JSON object containing the complete optimized trading rules:

```json
{{
  "version": "1.0_historical_optimized",
  "last_updated": "{datetime.now().isoformat()}",
  "updated_by": "claude_initialization",

  "entry_rules": {{
    "ribbon_alignment_threshold": 0.85,
    "min_light_emas_required": 2,
    "ribbon_states_allowed_long": ["all_green", "mixed_green"],
    "ribbon_states_allowed_short": ["all_red", "mixed_red"],
    "fresh_transition_max_minutes": 15,
    "stale_transition_min_minutes": 20
  }},

  "exit_rules": {{
    "max_hold_minutes": 15,
    "profit_target_pct": 0.005,
    "stop_loss_pct": 0.003,
    "use_yellow_ema_trail": true,
    "exit_on_ribbon_flip": true,
    "exit_on_light_ema_change_count": 3
  }},

  "pattern_rules": {{
    "path_e_dark_transition": {{
      "enabled": true,
      "priority": 1,
      "confidence_boost": 0.15,
      "entry_window_seconds": 10
    }},
    "path_d_early_reversal": {{
      "enabled": true,
      "priority": 2,
      "min_light_emas_opposite": 8,
      "min_green_appearing": 2,
      "confidence_threshold": 0.75
    }},
    "path_c_wick_reversal": {{
      "enabled": true,
      "priority": 3,
      "min_wick_pct": 0.003,
      "max_wick_pct": 0.008,
      "confidence_boost": 0.20
    }},
    "path_a_trending": {{
      "enabled": true,
      "priority": 4,
      "min_range_pct": 0.005,
      "price_location_lower_pct": 0.5,
      "price_location_upper_pct": 0.5,
      "min_alignment_pct": 0.85
    }},
    "path_b_breakout": {{
      "enabled": true,
      "priority": 5,
      "max_range_pct": 0.004,
      "min_breakout_pct": 0.0015,
      "ribbon_flip_max_minutes": 8
    }}
  }},

  "performance_metrics": {{
    "historical_win_rate": {historical_results.get('win_rate', 0)},
    "historical_total_trades": {historical_results.get('total_ribbon_flips', 0)},
    "avg_winner_pnl_pct": {historical_results.get('avg_winner_pnl_pct', 0)},
    "avg_loser_pnl_pct": {historical_results.get('avg_loser_pnl_pct', 0)}
  }},

  "claude_insights": {{
    "initialization_date": "{datetime.now().isoformat()}",
    "key_findings": [
      "Finding 1 from historical data",
      "Finding 2 from patterns"
    ],
    "pattern_recommendations": [
      "Recommendation 1",
      "Recommendation 2"
    ],
    "optimization_strategy": "Detailed explanation of why you chose these specific values based on the historical data"
  }}
}}
```

**IMPORTANT:**
- Use the ACTUAL historical data to inform your decisions
- If winners avg 0.7% profit, set profit_target_pct accordingly
- If losers avg -0.4% loss, set stop_loss_pct accordingly
- If light EMAs correlate with wins, require more light EMAs
- Disable patterns that have low win rates
- Prioritize patterns with highest historical success

Your goal: Create rules that would have maximized profitability on this historical data.
"""

        return prompt

    def _deep_pattern_analysis(self, patterns: list) -> str:
        """Perform deep analysis on pattern list"""
        if not patterns:
            return "No patterns available"

        total = len(patterns)

        # Aggregate statistics
        avg_green_pct = sum(p.get('green_pct', 0) for p in patterns) / max(total, 1)
        avg_red_pct = sum(p.get('red_pct', 0) for p in patterns) / max(total, 1)
        avg_light_green = sum(p.get('light_green_count', 0) for p in patterns) / max(total, 1)
        avg_light_red = sum(p.get('light_red_count', 0) for p in patterns) / max(total, 1)
        avg_dark_green = sum(p.get('dark_green_count', 0) for p in patterns) / max(total, 1)
        avg_dark_red = sum(p.get('dark_red_count', 0) for p in patterns) / max(total, 1)

        # Ribbon state distribution
        ribbon_states = {}
        for p in patterns:
            state = p.get('ribbon_state', 'unknown')
            ribbon_states[state] = ribbon_states.get(state, 0) + 1

        analysis = f"""
Total Patterns: {total}

EMA Color Distribution:
- Avg Green %: {avg_green_pct*100:.1f}%
- Avg Red %: {avg_red_pct*100:.1f}%

EMA Intensity Analysis:
- Avg Light Green EMAs: {avg_light_green:.1f}
- Avg Light Red EMAs: {avg_light_red:.1f}
- Avg Dark Green EMAs: {avg_dark_green:.1f}
- Avg Dark Red EMAs: {avg_dark_red:.1f}

Ribbon State Distribution:
{json.dumps(ribbon_states, indent=2)}

Key Insights:
- Light EMA correlation: {"HIGH" if avg_light_green > 3 or avg_light_red > 3 else "MEDIUM" if avg_light_green > 2 or avg_light_red > 2 else "LOW"}
- Momentum strength: {"STRONG" if (avg_light_green + avg_light_red) > 4 else "MODERATE"}
- Pattern clarity: {"CLEAR" if avg_green_pct > 0.8 or avg_red_pct > 0.8 else "MIXED"}
"""
        return analysis

    def _format_big_movement_analysis(self, analysis: dict) -> str:
        """Format big movement analysis for the prompt"""
        if not analysis or 'error' in analysis:
            return "No big movement analysis available (not enough data or analysis not run)"

        common = analysis.get('common_patterns', {})
        insights = analysis.get('insights', {})

        formatted = f"""
**Total Big Movements Found (ALL HISTORY):** {analysis.get('total_big_movements', 0)}
- Upward movements: {analysis.get('big_movements_up', 0)}
- Downward movements: {analysis.get('big_movements_down', 0)}
- Average magnitude: {analysis.get('avg_magnitude', 0):.2f}%

**Common EMA Patterns Before Big Movements:**
- Earliest warning signal: {common.get('avg_earliest_signal_minutes', 0):.1f} minutes before move
- Average light EMAs at signal: {common.get('avg_light_emas_at_signal', 0):.1f}
- Average ribbon flip timing: {common.get('avg_ribbon_flip_timing', 0):.1f} minutes before peak
- Compression trend: {dict(common.get('compression_trend_distribution', {}))}
- Transition speed: {dict(common.get('transition_speed_distribution', {}))}

**Key Insights:**
- Earliest warning signal: {insights.get('earliest_warning_signal', 'N/A')}
- Optimal entry timing: {insights.get('optimal_entry_timing', 'N/A')}
- Key indicators:
{chr(10).join(f'  * {indicator}' for indicator in insights.get('key_indicators', []))}

**Recommended Rule Adjustments (from pattern analysis):**
{json.dumps(insights.get('recommended_rules', {}), indent=2)}

**CRITICAL:** These patterns represent BIG profitable movements across ALL your historical data.
The rules you create MUST prioritize catching these patterns!
"""
        return formatted

    def call_claude_initialization(self, historical_results: dict, big_movement_analysis: dict = None) -> dict:
        """Call Claude to create initial optimized rules"""
        print("\n" + "="*70)
        print("🤖 CALLING CLAUDE FOR RULE INITIALIZATION")
        print("="*70)

        prompt = self.build_initialization_prompt(historical_results, big_movement_analysis)

        print("📤 Sending comprehensive historical analysis to Claude...")
        if big_movement_analysis:
            print(f"   Including BIG MOVEMENT analysis ({big_movement_analysis.get('total_big_movements', 0)} movements)")
        print(f"   Historical trades: {historical_results.get('total_ribbon_flips', 0)}")
        print(f"   Win rate: {historical_results.get('win_rate', 0)*100:.1f}%")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # More tokens for comprehensive analysis
                temperature=0.2,  # Low temp for analytical precision
                system=[{
                    "type": "text",
                    "text": "You are an expert quantitative trading strategist specializing in EMA ribbon pattern analysis and rule optimization.",
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Track usage and cost
            usage = response.usage
            input_cost = (usage.input_tokens / 1_000_000) * 3.0
            output_cost = (usage.output_tokens / 1_000_000) * 15.0
            cached_cost = 0

            if hasattr(usage, 'cache_read_input_tokens') and usage.cache_read_input_tokens:
                cached_cost = (usage.cache_read_input_tokens / 1_000_000) * 0.30

            self.total_cost = input_cost + output_cost + cached_cost

            print(f"\n💰 Initialization Cost: ${self.total_cost:.4f}")
            print(f"   Input tokens: {usage.input_tokens:,}")
            print(f"   Output tokens: {usage.output_tokens:,}")
            if hasattr(usage, 'cache_read_input_tokens'):
                print(f"   Cached tokens: {usage.cache_read_input_tokens:,}")

            # Parse response
            response_text = response.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text

            optimized_rules = json.loads(json_str)

            print("\n✅ Claude created optimized trading rules!")
            print(f"\n📊 Key Optimizations:")
            print(f"   Ribbon threshold: {optimized_rules['entry_rules']['ribbon_alignment_threshold']}")
            print(f"   Min light EMAs: {optimized_rules['entry_rules']['min_light_emas_required']}")
            print(f"   Profit target: {optimized_rules['exit_rules']['profit_target_pct']*100:.2f}%")
            print(f"   Stop loss: {optimized_rules['exit_rules']['stop_loss_pct']*100:.2f}%")
            print(f"   Max hold time: {optimized_rules['exit_rules']['max_hold_minutes']} min")

            return optimized_rules

        except Exception as e:
            print(f"❌ Error calling Claude: {e}")
            raise

    def save_optimized_rules(self, rules: dict, big_movement_analysis: dict = None):
        """Save optimized rules to JSON file"""
        # Add big movement insights if available
        if big_movement_analysis and 'claude_insights' in rules:
            if 'NEW_big_movement_analysis' not in rules['claude_insights']:
                rules['claude_insights']['NEW_big_movement_analysis'] = {}

            rules['claude_insights']['NEW_big_movement_analysis'] = {
                'last_analyzed': datetime.now().isoformat(),
                'big_moves_in_period': big_movement_analysis.get('total_big_movements', 0),
                'catch_rate_pct': 0.0,  # To be calculated by bot
                'recommendations': big_movement_analysis.get('insights', {}).get('key_indicators', [])
            }

        with open(self.rules_path, 'w') as f:
            json.dump(rules, f, indent=2)

        print(f"\n✅ Optimized rules saved to: {self.rules_path}")

    def initialize(self):
        """Main initialization process"""
        print("\n" + "="*70)
        print("🎯 TRADING RULES INITIALIZATION - FIRST TIME SETUP")
        print("="*70)
        print("This will analyze ALL your historical data to create optimal rules")
        print("="*70)

        # Step 1: Analyze all historical data
        print("\n[1/4] Analyzing all historical EMA data...")
        historical_results = self.analyze_all_historical_data()

        # Step 2: Analyze BIG MOVEMENT patterns in ALL historical data
        print("\n[2/4] 🎯 Analyzing BIG MOVEMENT patterns in ALL historical data...")
        big_movement_analysis = None
        try:
            analyzer = BigMovementEMAAnalyzer(self.ema_5min_path, self.ema_15min_path)
            big_movement_analysis = analyzer.analyze_all_big_movements()

            print(f"✅ Found {big_movement_analysis.get('total_big_movements', 0)} BIG movements in historical data")
            if big_movement_analysis.get('total_big_movements', 0) > 0:
                common = big_movement_analysis.get('common_patterns', {})
                insights = big_movement_analysis.get('insights', {})
                print(f"   📊 Pattern: {common.get('avg_light_emas_at_signal', 0):.1f} light EMAs appear {common.get('avg_earliest_signal_minutes', 0):.1f}min before")
                print(f"   🎯 Earliest warning: {insights.get('earliest_warning_signal', 'N/A')}")
                print(f"   ⏰ Optimal entry: {insights.get('optimal_entry_timing', 'N/A')}")

                # Save big movement analysis
                with open('trading_data/big_movement_analysis_historical.json', 'w') as f:
                    json.dump(big_movement_analysis, f, indent=2, default=str)
                print("   💾 Saved to: trading_data/big_movement_analysis_historical.json")
        except Exception as e:
            print(f"⚠️  Big movement analysis failed: {e}")
            print("   Continuing with initialization without big movement data...")

        # Step 3: Call Claude for optimization (with big movement data!)
        print("\n[3/4] Calling Claude to create optimal rules...")
        optimized_rules = self.call_claude_initialization(historical_results, big_movement_analysis)

        # Step 4: Save rules
        print("\n[4/4] Saving optimized trading rules...")
        self.save_optimized_rules(optimized_rules, big_movement_analysis)

        # Summary
        print("\n" + "="*70)
        print("✅ INITIALIZATION COMPLETE!")
        print("="*70)
        print(f"💰 Total Cost: ${self.total_cost:.4f}")
        print(f"📊 Rules based on {historical_results.get('total_ribbon_flips', 0)} historical trades")
        print(f"🎯 Historical win rate: {historical_results.get('win_rate', 0)*100:.1f}%")
        print(f"\n📋 Next Steps:")
        print(f"   1. Review trading_rules.json")
        print(f"   2. Start your bot: python3 run_dual_bot_optimized.py")
        print(f"   3. Bot will use these PROVEN rules from the start!")
        print(f"   4. Rules will continue optimizing every 30 minutes")
        print("="*70 + "\n")


def main():
    """Run initialization"""
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "TRADING RULES INITIALIZATION" + " "*35 + "║")
    print("╚" + "="*78 + "╝")

    # Check if data exists
    if not os.path.exists('trading_data/ema_data_5min.csv'):
        print("\n❌ ERROR: No historical EMA data found!")
        print("\n📋 To initialize rules, you need historical data first:")
        print("   1. Run your bot for a few hours to collect data:")
        print("      python3 run_dual_bot.py")
        print("   2. Stop it (Ctrl+C)")
        print("   3. Then run this initialization:")
        print("      python3 initialize_trading_rules.py")
        print("\n💡 OR: Use default rules and let optimization improve them:")
        print("      python3 run_dual_bot_optimized.py (starts with defaults)")
        return

    # Check if rules already exist
    if os.path.exists('trading_rules.json'):
        print("\n⚠️  WARNING: trading_rules.json already exists!")
        response = input("   Overwrite with new initialization? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("\n✓ Cancelled - Using existing rules")
            return
        print("\n🔄 Re-initializing rules from historical data...")

    # Run initialization
    try:
        initializer = TradingRulesInitializer()
        initializer.initialize()

        print("🎉 SUCCESS! Your bot now has optimized rules based on ALL your historical data!")
        print("   Start trading: python3 run_dual_bot_optimized.py")

    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 You can still run the bot with default rules:")
        print("   python3 run_dual_bot_optimized.py")


if __name__ == '__main__':
    main()
