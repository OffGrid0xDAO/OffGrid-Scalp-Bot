"""
Rule Optimizer - Calls Claude every 30 minutes to optimize trading rules
This dramatically reduces API costs by using Claude for strategy optimization,
not individual trade decisions.
"""

import os
import json
from datetime import datetime, timedelta
from anthropic import Anthropic
from optimal_trade_finder_30min import OptimalTradeFinder
from big_movement_ema_analyzer import BigMovementEMAAnalyzer
from rule_version_manager import RuleVersionManager
from telegram_notifier import TelegramNotifier
import pandas as pd


class RuleOptimizer:
    """Optimizes trading rules using Claude AI every 30 minutes"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

        # Paths
        self.rules_path = 'trading_rules.json'
        self.optimal_trades_path = 'trading_data/optimal_trades_last_30min.json'
        self.optimal_trades_full_path = 'trading_data/optimal_trades.json'  # Full history
        self.backtest_trades_path = 'trading_data/backtest_trades.json'  # Current rules simulation
        self.decisions_log_path = 'trading_data/claude_decisions.csv'
        self.ema_5min_path = 'trading_data/ema_data_5min.csv'
        self.ema_15min_path = 'trading_data/ema_data_15min.csv'

        # Version manager
        self.version_manager = RuleVersionManager()

        # Telegram notifier
        self.telegram = TelegramNotifier()

        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
        self.session_cost = 0.0

        print("🔧 Rule Optimizer initialized")
        print(f"📦 Rule versioning enabled ({len(self.version_manager.history)} versions tracked)")

    def load_current_rules(self) -> dict:
        """Load current trading rules from JSON"""
        with open(self.rules_path, 'r') as f:
            return json.load(f)

    def save_updated_rules(self, rules: dict):
        """Save updated trading rules to JSON"""
        rules['last_updated'] = datetime.now().isoformat()
        rules['updated_by'] = 'claude_optimizer'

        with open(self.rules_path, 'w') as f:
            json.dump(rules, f, indent=2)

        print(f"✅ Rules updated and saved to {self.rules_path}")

    def load_optimal_trades(self) -> dict:
        """Load optimal trades for comparison"""
        try:
            with open(self.optimal_trades_full_path, 'r') as f:
                data = json.load(f)
                return {
                    'total_trades': data.get('total_trades', 0),
                    'total_pnl_pct': data.get('total_pnl_pct', 0),
                    'avg_pnl_pct': data.get('avg_pnl_pct', 0),
                    'trades': data.get('trades', [])
                }
        except FileNotFoundError:
            print("⚠️  No optimal trades file found - run find_optimal_trades.py first")
            return {'total_trades': 0, 'trades': []}
        except Exception as e:
            print(f"⚠️  Error loading optimal trades: {e}")
            return {'total_trades': 0, 'trades': []}

    def load_backtest_trades(self) -> dict:
        """Load backtest trades (current rules simulation)"""
        try:
            with open(self.backtest_trades_path, 'r') as f:
                data = json.load(f)
                return {
                    'total_trades': data.get('total_trades', 0),
                    'total_pnl_pct': data.get('total_pnl_pct', 0),
                    'avg_pnl_pct': data.get('avg_pnl_pct', 0),
                    'trades': data.get('trades', [])
                }
        except FileNotFoundError:
            print("⚠️  No backtest trades file found - run backtest_current_rules.py first")
            return {'total_trades': 0, 'trades': []}
        except Exception as e:
            print(f"⚠️  Error loading backtest trades: {e}")
            return {'total_trades': 0, 'trades': []}

    def analyze_ema_patterns_at_entries(self, trades: list, ema_data_path: str) -> dict:
        """Analyze EMA patterns (colors, compression, slopes) at trade entry points"""
        try:
            df = pd.read_csv(ema_data_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            patterns = {
                'colors': [],
                'compression': [],
                'slopes': [],
                'light_ema_counts': []
            }

            for trade in trades[:50]:  # Analyze up to 50 trades
                entry_time = pd.to_datetime(trade['entry_time'])

                # Find closest timestamp in EMA data
                time_diff = abs(df['timestamp'] - entry_time)
                if time_diff.min() < pd.Timedelta(minutes=2):
                    closest_idx = time_diff.idxmin()
                    row = df.loc[closest_idx]

                    # Extract pattern info
                    pattern = {
                        'ribbon_state': row.get('ribbon_state', 'unknown'),
                        'compression': row.get('compression_value', 0),
                        'light_green_emas': 0,
                        'light_red_emas': 0,
                        'slopes': {}
                    }

                    # Count light EMAs
                    for ema_num in [5, 10, 15, 20, 25, 30]:
                        color_col = f'MMA{ema_num}_color'
                        intensity_col = f'MMA{ema_num}_intensity'
                        slope_col = f'MMA{ema_num}_slope'

                        if color_col in row.index and intensity_col in row.index:
                            if row[color_col] == 'green' and row[intensity_col] == 'light':
                                pattern['light_green_emas'] += 1
                            elif row[color_col] == 'red' and row[intensity_col] == 'light':
                                pattern['light_red_emas'] += 1

                        if slope_col in row.index:
                            pattern['slopes'][f'MMA{ema_num}'] = row[slope_col]

                    patterns['colors'].append(pattern['ribbon_state'])
                    patterns['compression'].append(pattern['compression'])
                    patterns['light_ema_counts'].append({
                        'green': pattern['light_green_emas'],
                        'red': pattern['light_red_emas']
                    })
                    patterns['slopes'].append(pattern['slopes'])

            # Summarize patterns
            summary = {
                'total_analyzed': len(patterns['colors']),
                'common_ribbon_states': {},
                'avg_compression': sum(patterns['compression']) / max(len(patterns['compression']), 1),
                'avg_light_green_emas': sum(p['green'] for p in patterns['light_ema_counts']) / max(len(patterns['light_ema_counts']), 1),
                'avg_light_red_emas': sum(p['red'] for p in patterns['light_ema_counts']) / max(len(patterns['light_ema_counts']), 1),
            }

            # Count ribbon states
            for state in patterns['colors']:
                summary['common_ribbon_states'][state] = summary['common_ribbon_states'].get(state, 0) + 1

            return summary

        except Exception as e:
            print(f"⚠️  Error analyzing EMA patterns: {e}")
            return {}

    def analyze_recent_performance(self) -> dict:
        """Analyze actual trades from the last 30 minutes"""
        try:
            df = pd.read_csv(self.decisions_log_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Last 30 minutes
            cutoff = datetime.now() - timedelta(minutes=30)
            recent = df[df['timestamp'] >= cutoff].copy()

            # Filter to actual executions
            executed = recent[recent['executed'] == True].copy()

            if len(executed) == 0:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0.0,
                    'avg_confidence': 0.0
                }

            # Calculate performance (simplified - would need exit data for real P&L)
            return {
                'total_trades': len(executed),
                'long_trades': len(executed[executed['direction'] == 'LONG']),
                'short_trades': len(executed[executed['direction'] == 'SHORT']),
                'avg_confidence': executed['confidence_score'].mean(),
                'entries_recommended': len(recent[recent['entry_recommended'] == 'YES']),
                'exits_recommended': len(recent[recent['exit_recommended'] == 'YES'])
            }

        except Exception as e:
            print(f"⚠️  Error analyzing recent performance: {e}")
            return {'error': str(e)}

    def build_optimization_prompt(self, optimal_data: dict, backtest_data: dict, actual_data: dict,
                                  current_rules: dict, performance: dict, big_movement_analysis: dict = None) -> str:
        """Build the prompt for Claude to optimize trading rules with 3-way comparison"""

        # Extract pattern summaries from optimal trades
        optimal_patterns = optimal_data.get('patterns', {})
        backtest_patterns = backtest_data.get('patterns', {})

        prompt = f"""You are a trading strategy optimizer analyzing EMA ribbon patterns for a scalping system.

## CRITICAL OBJECTIVE: 3-WAY TRADE COMPARISON

Your goal is to analyze the GAP between three types of trades and close that gap:

1. **OPTIMAL TRADES** - Best possible entries/exits with perfect hindsight
2. **BACKTEST TRADES** - What current rules would have caught (simulation)
3. **ACTUAL TRADES** - What the bot actually executed

By comparing these three, we can identify:
- What patterns optimal trades have that backtest missed → Improve entry rules
- What caused backtest to take bad trades → Improve quality filters
- Why actual trades differ from backtest → Improve execution logic

## THREE-WAY COMPARISON DATA

### 1️⃣ OPTIMAL TRADES (Perfect Hindsight - The Goal)
**Performance:**
- Total Trades: {optimal_data.get('total_trades', 0)}
- Total PnL: {optimal_data.get('total_pnl_pct', 0):+.2f}%
- Average PnL: {optimal_data.get('avg_pnl_pct', 0):+.2f}%
- Win Rate: 100% (by definition - optimal timing)

**EMA Patterns at Entry:**
{json.dumps(optimal_patterns, indent=2)}

### 2️⃣ BACKTEST TRADES (Current Rules Simulation)
**Performance:**
- Total Trades: {backtest_data.get('total_trades', 0)}
- Total PnL: {backtest_data.get('total_pnl_pct', 0):+.2f}%
- Average PnL: {backtest_data.get('avg_pnl_pct', 0):+.2f}%
- Capture Rate: {(backtest_data.get('total_trades', 0) / max(optimal_data.get('total_trades', 1), 1) * 100):.1f}% of optimal trades

**EMA Patterns at Entry:**
{json.dumps(backtest_patterns, indent=2)}

**GAP FROM OPTIMAL:**
- Missed Trades: {optimal_data.get('total_trades', 0) - backtest_data.get('total_trades', 0)}
- PnL Gap: {optimal_data.get('total_pnl_pct', 0) - backtest_data.get('total_pnl_pct', 0):+.2f}%

### 3️⃣ ACTUAL TRADES (Live Bot Execution)
**Performance:**
{json.dumps(actual_data, indent=2)}

**GAP FROM BACKTEST:**
- Shows execution issues, timing differences, or parameter mismatches

### BIG MOVEMENT ANALYSIS
{self._format_big_movement_analysis(big_movement_analysis)}

### RULE OPTIMIZATION HISTORY & LEARNINGS
{self.version_manager.get_learning_summary_for_claude()}

### Current Trading Rules
{json.dumps(current_rules, indent=2)}

## YOUR TASK

1. **BIG MOVEMENT ANALYSIS** (HIGHEST PRIORITY):
   - What EMA patterns consistently appear BEFORE big movements?
   - How early can we detect these patterns? (earliest warning signal)
   - Should we create special rules to catch big movements even if they violate normal filters?
   - Are we missing any big movements? If so, why?

2. **Pattern Analysis**: What EMA patterns are most profitable? What should we avoid?

3. **Rule Optimization**: Should we adjust:
   - Ribbon alignment threshold (currently {current_rules['entry_rules']['ribbon_alignment_threshold']})
   - Minimum light EMAs required (currently {current_rules['entry_rules']['min_light_emas_required']})
   - Max hold time (currently {current_rules['exit_rules']['max_hold_minutes']} minutes)
   - Profit targets or stop losses?
   - **NEW:** Big movement detection thresholds (if supported in rules)

4. **Pattern Priorities**: Which entry paths (A-F) should have higher priority based on the data?
   - Should path_f_momentum_surge have highest priority for big movements?

5. **New Insights**: Any new patterns noticed that we should incorporate?

6. **Advanced Parameters Available**:
   You can add these NEW parameters to the rules if they would help catch big movements:

   **Big Movement Detection:**
   - `NEW_big_movement_detection.enabled`: Enable special big movement rules
   - `NEW_big_movement_detection.volume_surge_threshold`: Detect volume spikes
   - `NEW_big_movement_detection.min_price_move_pct`: Threshold for "big" move
   - `NEW_big_movement_detection.ignore_stale_on_big_move`: Override stale filter for big moves

   **Momentum Filters:**
   - `NEW_momentum_filters.min_ema_spread_pct`: Require EMA expansion
   - `NEW_momentum_filters.dark_to_light_transition_boost`: Bonus confidence for transitions

   **Path F - Momentum Surge (for BIG movements):**
   - `NEW_path_f_momentum_surge.enabled`: Enable dedicated big movement path
   - `NEW_path_f_momentum_surge.priority`: 1 (highest)
   - `NEW_path_f_momentum_surge.min_light_emas`: Minimum light EMAs to trigger
   - `NEW_path_f_momentum_surge.ignore_all_other_filters`: Skip normal filters

   **Big Movement Priority Overrides:**
   - `NEW_big_movement_priority.enabled`: Enable override rules
   - `NEW_big_movement_priority.entry_overrides.ignore_stale_filter`: Enter even if stale
   - `NEW_big_movement_priority.entry_overrides.ignore_position_location_filter`: Enter anywhere

   You can add ANY of these to `entry_rules`, `exit_rules`, or `pattern_rules` if data shows they would help.

   See `trading_rules_EXPANDED.json` for complete list of available parameters.

## OUTPUT FORMAT

Respond with a JSON object containing your recommendations:

```json
{{
  "key_findings": [
    "Finding 1: ...",
    "Finding 2: ..."
  ],
  "pattern_recommendations": [
    "Pattern recommendation 1",
    "Pattern recommendation 2"
  ],
  "rule_adjustments": {{
    "ribbon_alignment_threshold": 0.85,
    "min_light_emas_required": 2,
    "max_hold_minutes": 15,
    "profit_target_pct": 0.005,
    "stop_loss_pct": 0.003,
    "path_priorities": {{
      "path_e_dark_transition": 1,
      "path_d_early_reversal": 2,
      "path_c_wick_reversal": 3,
      "path_a_trending": 4,
      "path_b_breakout": 5
    }}
  }},
  "reasoning": "Brief explanation of why you're making these recommendations based on the data..."
}}
```

Focus on DATA-DRIVEN insights. Only recommend changes if the data supports them.
"""

        return prompt

    def _summarize_patterns(self, patterns: list) -> str:
        """Summarize a list of EMA patterns"""
        if not patterns:
            return "No patterns available"

        # Aggregate stats
        total = len(patterns)
        avg_green_pct = sum(p.get('green_pct', 0) for p in patterns) / max(total, 1)
        avg_red_pct = sum(p.get('red_pct', 0) for p in patterns) / max(total, 1)
        avg_light_green = sum(p.get('light_green_count', 0) for p in patterns) / max(total, 1)
        avg_light_red = sum(p.get('light_red_count', 0) for p in patterns) / max(total, 1)

        ribbon_states = {}
        for p in patterns:
            state = p.get('ribbon_state', 'unknown')
            ribbon_states[state] = ribbon_states.get(state, 0) + 1

        summary = f"""
- Total Patterns: {total}
- Avg Green EMAs: {avg_green_pct*100:.1f}%
- Avg Red EMAs: {avg_red_pct*100:.1f}%
- Avg Light Green EMAs: {avg_light_green:.1f}
- Avg Light Red EMAs: {avg_light_red:.1f}
- Ribbon States: {json.dumps(ribbon_states, indent=2)}
"""
        return summary

    def _format_big_movement_analysis(self, analysis: dict) -> str:
        """Format big movement analysis for the prompt"""
        if not analysis or 'error' in analysis:
            return "No big movement analysis available (not enough data or analysis not run)"

        common = analysis.get('common_patterns', {})
        insights = analysis.get('insights', {})

        formatted = f"""
**Total Big Movements Found:** {analysis.get('total_big_movements', 0)}
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

**CRITICAL:** These patterns represent BIG profitable movements. Prioritize catching these!
"""
        return formatted

    def call_claude_optimizer(self, optimal_trades: dict, current_rules: dict, performance: dict, big_movement_analysis: dict = None) -> dict:
        """Call Claude to get optimization recommendations"""

        prompt = self.build_optimization_prompt(optimal_trades, current_rules, performance, big_movement_analysis)

        print("🤖 Calling Claude for rule optimization...")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.3,
                system=[{
                    "type": "text",
                    "text": "You are an expert trading strategy optimizer specializing in EMA ribbon pattern analysis.",
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Track usage
            usage = response.usage
            self.total_input_tokens += usage.input_tokens
            self.total_output_tokens += usage.output_tokens

            # Calculate costs (Sonnet 4.5 pricing)
            input_cost = (usage.input_tokens / 1_000_000) * 3.0
            output_cost = (usage.output_tokens / 1_000_000) * 15.0

            # Check for cached tokens
            cached_cost = 0
            if hasattr(usage, 'cache_read_input_tokens') and usage.cache_read_input_tokens:
                self.total_cached_tokens += usage.cache_read_input_tokens
                cached_cost = (usage.cache_read_input_tokens / 1_000_000) * 0.30

            self.session_cost = input_cost + output_cost + cached_cost

            print(f"💰 API Call Cost: ${self.session_cost:.4f}")
            print(f"   Input tokens: {usage.input_tokens:,}")
            print(f"   Output tokens: {usage.output_tokens:,}")
            if hasattr(usage, 'cache_read_input_tokens'):
                print(f"   Cached tokens: {usage.cache_read_input_tokens:,}")

            # Extract Claude's response
            response_text = response.content[0].text

            # Parse JSON from response
            # Claude might wrap it in ```json blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text

            recommendations = json.loads(json_str)

            return recommendations

        except Exception as e:
            print(f"❌ Error calling Claude: {e}")
            return {'error': str(e)}

    def apply_recommendations(self, current_rules: dict, recommendations: dict) -> dict:
        """Apply Claude's recommendations to the rules"""

        if 'error' in recommendations:
            print(f"⚠️  Cannot apply recommendations due to error: {recommendations['error']}")
            return current_rules

        # Update entry rules
        if 'rule_adjustments' in recommendations:
            adjustments = recommendations['rule_adjustments']

            if 'ribbon_alignment_threshold' in adjustments:
                current_rules['entry_rules']['ribbon_alignment_threshold'] = adjustments['ribbon_alignment_threshold']

            if 'min_light_emas_required' in adjustments:
                current_rules['entry_rules']['min_light_emas_required'] = adjustments['min_light_emas_required']

            if 'max_hold_minutes' in adjustments:
                current_rules['exit_rules']['max_hold_minutes'] = adjustments['max_hold_minutes']

            if 'profit_target_pct' in adjustments:
                current_rules['exit_rules']['profit_target_pct'] = adjustments['profit_target_pct']

            if 'stop_loss_pct' in adjustments:
                current_rules['exit_rules']['stop_loss_pct'] = adjustments['stop_loss_pct']

            # Update path priorities
            if 'path_priorities' in adjustments:
                for path_name, priority in adjustments['path_priorities'].items():
                    if path_name in current_rules['pattern_rules']:
                        current_rules['pattern_rules'][path_name]['priority'] = priority

        # Store Claude's insights
        current_rules['claude_insights'] = {
            'last_optimization': datetime.now().isoformat(),
            'key_findings': recommendations.get('key_findings', []),
            'pattern_recommendations': recommendations.get('pattern_recommendations', []),
            'rule_adjustments': recommendations.get('rule_adjustments', {}),
            'reasoning': recommendations.get('reasoning', 'No reasoning provided')
        }

        return current_rules

    def optimize_rules(self):
        """Main function: Run the full optimization cycle"""

        print("\n" + "="*70)
        print("🔧 RULE OPTIMIZATION CYCLE - 30 MINUTE WINDOW")
        print("="*70)
        print(f"⏰ Cycle Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Step 1: Find optimal trades from last 30 minutes
        print("\n[1/6] Analyzing optimal trades from last 30 minutes...")
        finder = OptimalTradeFinder(self.ema_5min_path, self.ema_15min_path)
        optimal_trades = finder.analyze_optimal_setups()

        # Save optimal trades
        with open(self.optimal_trades_path, 'w') as f:
            json.dump(optimal_trades, f, indent=2, default=str)

        print(f"✅ Found {optimal_trades.get('total_ribbon_flips', 0)} ribbon flips")
        print(f"   Win Rate: {optimal_trades.get('win_rate', 0)*100:.1f}%")

        # Step 2: Analyze recent actual performance
        print("\n[2/6] Analyzing recent trading performance...")
        performance = self.analyze_recent_performance()
        print(f"✅ Analyzed {performance.get('total_trades', 0)} actual trades")

        # Step 3: Analyze BIG MOVEMENT patterns
        print("\n[3/6] 🎯 Analyzing BIG MOVEMENT EMA patterns...")
        big_movement_analysis = None
        try:
            analyzer = BigMovementEMAAnalyzer(self.ema_5min_path, self.ema_15min_path)
            big_movement_analysis = analyzer.analyze_all_big_movements()

            print(f"✅ Found {big_movement_analysis.get('total_big_movements', 0)} BIG movements")
            if big_movement_analysis.get('total_big_movements', 0) > 0:
                common = big_movement_analysis.get('common_patterns', {})
                print(f"   📊 Pattern: {common.get('avg_light_emas_at_signal', 0):.1f} light EMAs appear {common.get('avg_earliest_signal_minutes', 0):.1f}min before")

                # Save big movement analysis
                with open('trading_data/big_movement_analysis.json', 'w') as f:
                    json.dump(big_movement_analysis, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️  Big movement analysis failed: {e}")
            print("   Continuing with optimization without big movement data...")

        # Step 4: Load current rules
        print("\n[4/6] Loading current trading rules...")
        current_rules = self.load_current_rules()
        print("✅ Current rules loaded")

        # Step 5: Load and analyze backtest data for 3-way comparison
        print("\n[5/8] Loading backtest trades for comparison...")
        backtest_data = self.load_backtest_trades()
        if backtest_data and backtest_data.get('total_trades', 0) > 0:
            print(f"✅ Loaded {backtest_data['total_trades']} backtest trades")
        else:
            print("⚠️  No backtest trades found - run backtest_current_rules.py first")
            backtest_data = {'total_trades': 0, 'total_pnl_pct': 0, 'trades': []}

        # Step 6: Analyze EMA patterns for optimal and backtest trades
        print("\n[6/8] Analyzing EMA patterns at entry points...")
        optimal_full = self.load_optimal_trades()

        # Analyze patterns for optimal trades
        if optimal_full.get('trades'):
            optimal_patterns = self.analyze_ema_patterns_at_entries(
                optimal_full['trades'][:50],  # Limit to 50 for performance
                self.ema_5min_path
            )
            optimal_full['patterns'] = optimal_patterns
            print(f"✅ Analyzed {optimal_patterns.get('total_analyzed', 0)} optimal trade entries")
        else:
            optimal_full['patterns'] = {}
            print("⚠️  No optimal trades to analyze patterns")

        # Analyze patterns for backtest trades
        if backtest_data.get('trades'):
            backtest_patterns = self.analyze_ema_patterns_at_entries(
                backtest_data['trades'][:50],  # Limit to 50 for performance
                self.ema_5min_path
            )
            backtest_data['patterns'] = backtest_patterns
            print(f"✅ Analyzed {backtest_patterns.get('total_analyzed', 0)} backtest trade entries")
        else:
            backtest_data['patterns'] = {}

        # Step 7: Call Claude for optimization
        print("\n[7/8] Calling Claude AI for optimization recommendations...")
        recommendations = self.call_claude_optimizer(optimal_trades, current_rules, performance, big_movement_analysis)

        if 'error' not in recommendations:
            print("✅ Claude recommendations received")
            print(f"\n📊 Key Findings:")
            for finding in recommendations.get('key_findings', []):
                print(f"   - {finding}")
        else:
            print(f"❌ Error getting recommendations: {recommendations['error']}")
            return

        # Send Telegram notification with 3-way comparison
        print("\n📱 Sending optimization update to Telegram...")
        try:
            self.telegram.send_optimization_update(
                optimal_data=optimal_full,
                backtest_data=backtest_data,
                actual_data=performance,
                recommendations=recommendations,
                api_cost=self.session_cost
            )
            print("✅ Telegram notification sent")
        except Exception as e:
            print(f"⚠️  Telegram notification failed: {e}")

        # Step 8: Apply recommendations and save
        print("\n[8/8] Applying recommendations to trading rules...")

        # SAVE VERSION BEFORE UPDATING
        version_id = self.version_manager.save_version_before_update(reason="30min_optimization")

        updated_rules = self.apply_recommendations(current_rules, recommendations)

        # Store big movement analysis results in insights
        if big_movement_analysis and 'claude_insights' in updated_rules:
            if 'NEW_big_movement_analysis' not in updated_rules['claude_insights']:
                updated_rules['claude_insights']['NEW_big_movement_analysis'] = {}

            updated_rules['claude_insights']['NEW_big_movement_analysis'] = {
                'last_analyzed': datetime.now().isoformat(),
                'big_moves_in_period': big_movement_analysis.get('total_big_movements', 0),
                'catch_rate_pct': 0.0,  # To be calculated by bot
                'recommendations': big_movement_analysis.get('insights', {}).get('key_indicators', [])
            }

        self.save_updated_rules(updated_rules)

        print(f"💾 Previous rules saved as: {version_id}")

        print("\n" + "="*70)
        print("✅ OPTIMIZATION CYCLE COMPLETE")
        print(f"💰 Total Cost This Cycle: ${self.session_cost:.4f}")
        print(f"📈 Next optimization in 30 minutes")
        print("="*70 + "\n")


def main():
    """Run a single optimization cycle (to be called every 30 minutes)"""
    optimizer = RuleOptimizer()
    optimizer.optimize_rules()


if __name__ == '__main__':
    main()
