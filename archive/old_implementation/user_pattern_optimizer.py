"""
User Pattern System Optimizer
Iteratively tunes user pattern parameters to match optimal trades
"""

import json
import os
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class UserPatternOptimizer:
    """
    Optimizer specifically designed for user_pattern trading system
    Tunes parameters to match user's profitable trading style
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.rules_path = 'trading_rules.json'
        self.optimal_trades_path = 'trading_data/optimal_trades_user.json'
        self.backtest_path = 'trading_data/backtest_trades.json'

    def load_current_rules(self) -> dict:
        """Load current user pattern rules"""
        with open(self.rules_path, 'r') as f:
            return json.load(f)

    def load_optimal_trades(self) -> dict:
        """Load user's optimal trades"""
        try:
            with open(self.optimal_trades_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️  No user optimal trades found. Using auto-generated.")
            with open('trading_data/optimal_trades_auto.json', 'r') as f:
                return json.load(f)

    def load_backtest_results(self) -> dict:
        """Load current backtest results"""
        with open(self.backtest_path, 'r') as f:
            return json.load(f)

    def analyze_performance_gap(self, optimal: dict, backtest: dict) -> dict:
        """
        Analyze gap between optimal trades and current backtest
        """
        opt_summary = optimal.get('summary', {})
        bt_summary = backtest.get('summary', {})

        # Extract key metrics
        opt_trades = opt_summary.get('total_trades', optimal.get('total_trades', 0))
        bt_trades = bt_summary.get('total_trades', backtest.get('total_trades', 0))

        opt_pnl = opt_summary.get('total_pnl', optimal.get('total_pnl_pct', 0))
        bt_pnl = bt_summary.get('total_pnl', backtest.get('total_pnl_pct', 0))

        opt_winrate = opt_summary.get('win_rate', 0)
        bt_winrate = bt_summary.get('win_rate', 0)

        opt_trades_per_hour = opt_summary.get('trades_per_hour', opt_trades / 24 if opt_trades else 0)
        bt_trades_per_hour = bt_summary.get('trades_per_hour', bt_trades / 24 if bt_trades else 0)

        gap = {
            'trade_frequency': {
                'optimal': opt_trades_per_hour,
                'current': bt_trades_per_hour,
                'gap': opt_trades_per_hour - bt_trades_per_hour,
                'gap_pct': ((opt_trades_per_hour - bt_trades_per_hour) / opt_trades_per_hour * 100) if opt_trades_per_hour > 0 else 0
            },
            'total_trades': {
                'optimal': opt_trades,
                'current': bt_trades,
                'gap': opt_trades - bt_trades
            },
            'profitability': {
                'optimal_pnl': opt_pnl,
                'current_pnl': bt_pnl,
                'gap': opt_pnl - bt_pnl
            },
            'win_rate': {
                'optimal': opt_winrate,
                'current': bt_winrate,
                'gap': opt_winrate - bt_winrate
            }
        }

        return gap

    def build_optimization_prompt(self, rules: dict, optimal: dict, backtest: dict, gap: dict) -> str:
        """
        Build Claude prompt for optimization recommendations
        """

        prompt = f"""You are optimizing a user pattern trading system. The system uses quality scoring and momentum detection to match a user's profitable trading style.

## CURRENT PERFORMANCE GAP

**Trade Frequency:**
- Optimal (user's style): {gap['trade_frequency']['optimal']:.2f} trades/hour
- Current system: {gap['trade_frequency']['current']:.2f} trades/hour
- Gap: {gap['trade_frequency']['gap']:+.2f} trades/hour ({gap['trade_frequency']['gap_pct']:+.1f}%)

**Total Trades:**
- Optimal: {gap['total_trades']['optimal']} trades
- Current: {gap['total_trades']['current']} trades
- Missing: {gap['total_trades']['gap']} trades

**Profitability:**
- Optimal: {gap['profitability']['optimal_pnl']:+.2f}%
- Current: {gap['profitability']['current_pnl']:+.2f}%
- Gap: {gap['profitability']['gap']:+.2f}%

**Win Rate:**
- Optimal: {gap['win_rate']['optimal']*100:.1f}%
- Current: {gap['win_rate']['current']*100:.1f}%
- Gap: {gap['win_rate']['gap']*100:+.1f}%

## CURRENT RULES

```json
{json.dumps(rules, indent=2)}
```

## TUNABLE PARAMETERS

### 1. Quality Filter (Most Important)
- `quality_filter.min_score`: 0-100 (current: {rules['quality_filter']['min_score']})
  * Lower = more trades (less selective)
  * Higher = fewer trades (more selective)
  * Recommended range: 60-80

### 2. Momentum Requirements
- `momentum.required`: true/false (current: {rules['momentum']['required']})
  * false = allow non-momentum trades (more signals)
  * true = only momentum moves (fewer, higher quality)

- `momentum.big_move_threshold`: 0.002-0.010 (current: {rules['momentum']['big_move_threshold']})
  * Lower = catch smaller moves (more trades)
  * Higher = only big moves (fewer trades)
  * Typical: 0.003-0.005 (0.3%-0.5%)

- `momentum.acceleration_threshold`: 1.0-2.0 (current: {rules['momentum']['acceleration_threshold']})
  * Lower = allow steady moves (more trades)
  * Higher = require strong acceleration (fewer trades)

### 3. Compression Ranges
- `compression.tight_min/max`: Define "tight compression" range (current: {rules['compression']['tight_min']}-{rules['compression']['tight_max']})
- `compression.wide_min/max`: Define "wide compression" range (current: {rules['compression']['wide_min']}-{rules['compression']['wide_max']})
- `compression.medium_allowed`: Allow middle range? (current: {rules['compression']['medium_allowed']})

### 4. Light EMA Ranges
- `light_emas.strong_trend_max`: Max light EMAs for "strong trend" (current: {rules['light_emas']['strong_trend_max']})
- `light_emas.transition_min`: Min light EMAs for "transition" (current: {rules['light_emas']['transition_min']})
- `light_emas.avoid_middle`: Skip 3-4 range? (current: {rules['light_emas']['avoid_middle']})

### 5. Exit Strategy
- `exit.profit_target_quick`: Quick profit target (current: {rules['exit']['profit_target_quick']})
- `exit.profit_target_medium`: Medium profit target (current: {rules['exit']['profit_target_medium']})
- `exit.profit_target_long`: Long hold profit target (current: {rules['exit']['profit_target_long']})
- `exit.stop_loss`: Maximum loss (current: {rules['exit']['stop_loss']})

### 6. Frequency Limits
- `frequency.max_trades_per_hour`: Cap per hour (current: {rules['frequency']['max_trades_per_hour']})
- `frequency.max_trades_per_4_hours`: Cap per 4 hours (current: {rules['frequency']['max_trades_per_4_hours']})
- `frequency.max_trades_per_day`: Daily cap (current: {rules['frequency']['max_trades_per_day']})

### 7. Quality Scoring Weights
- `quality_filter.factors.compression_match`: Weight 0-50 (current: {rules['quality_filter']['factors']['compression_match']})
- `quality_filter.factors.light_ema_match`: Weight 0-50 (current: {rules['quality_filter']['factors']['light_ema_match']})
- `quality_filter.factors.momentum_detected`: Weight 0-50 (current: {rules['quality_filter']['factors']['momentum_detected']})
- `quality_filter.factors.ribbon_aligned`: Weight 0-30 (current: {rules['quality_filter']['factors']['ribbon_aligned']})
- `quality_filter.factors.volatility_spike`: Weight 0-30 (current: {rules['quality_filter']['factors']['volatility_spike']})

## YOUR TASK

Analyze the performance gap and recommend SPECIFIC parameter changes to move the current system closer to optimal.

**Priority:**
1. If too few trades: Focus on relaxing entry criteria (lower min_score, lower momentum threshold, allow more patterns)
2. If too many trades: Focus on tightening criteria (raise min_score, require momentum, stricter patterns)
3. If wrong win rate: Adjust exit strategy
4. If wrong PnL: Adjust profit targets and stop loss

**Response Format:**

Return ONLY valid JSON in this exact format:
```json
{{
  "reasoning": "Brief explanation of why these changes will help",
  "priority_issue": "trade_frequency | profitability | win_rate",
  "recommended_changes": [
    {{
      "parameter": "quality_filter.min_score",
      "current_value": 75,
      "new_value": 65,
      "reason": "Lower threshold to increase trade frequency by ~30%",
      "expected_impact": "+3-5 trades"
    }},
    {{
      "parameter": "momentum.big_move_threshold",
      "current_value": 0.004,
      "new_value": 0.003,
      "reason": "Catch smaller momentum moves",
      "expected_impact": "+2-4 trades"
    }}
  ],
  "expected_results": {{
    "trades": 8,
    "trades_per_hour": 0.33,
    "improvement_pct": 700
  }}
}}
```

Be conservative: Make 2-4 changes at a time, not all at once. We iterate.
"""

        return prompt

    def get_claude_recommendations(self, prompt: str) -> dict:
        """
        Get optimization recommendations from Claude
        """
        client = Anthropic(api_key=self.api_key)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract JSON from response
        content = response.content[0].text

        # Find JSON block
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        else:
            # Try to parse entire response as JSON
            json_str = content.strip()

        return json.loads(json_str)

    def apply_recommendations(self, rules: dict, recommendations: dict) -> dict:
        """
        Apply recommended changes to rules
        """
        updated_rules = rules.copy()

        for change in recommendations['recommended_changes']:
            param_path = change['parameter'].split('.')

            # Navigate to the parameter
            current = updated_rules
            for key in param_path[:-1]:
                current = current[key]

            # Apply change
            old_value = current[param_path[-1]]
            new_value = change['new_value']
            current[param_path[-1]] = new_value

            print(f"  ✏️  {change['parameter']}: {old_value} → {new_value}")
            print(f"     {change['reason']}")

        # Update metadata
        updated_rules['last_updated'] = datetime.now().isoformat()
        updated_rules['updated_by'] = 'user_pattern_optimizer'

        return updated_rules

    def save_rules(self, rules: dict):
        """Save updated rules"""
        with open(self.rules_path, 'w') as f:
            json.dump(rules, f, indent=2)

    def optimize(self):
        """
        Main optimization loop
        """
        print("\n" + "="*80)
        print("🎯 USER PATTERN OPTIMIZER")
        print("="*80)

        # Load data
        print("\n[1/5] Loading current rules...")
        rules = self.load_current_rules()
        print(f"   ✅ Version: {rules.get('version')}")

        print("\n[2/5] Loading optimal trades (user's style)...")
        optimal = self.load_optimal_trades()
        print(f"   ✅ User trades: {optimal.get('total_trades', 0)}")

        print("\n[3/5] Loading backtest results...")
        backtest = self.load_backtest_results()
        print(f"   ✅ Backtest trades: {backtest.get('summary', {}).get('total_trades', 0)}")

        print("\n[4/5] Analyzing performance gap...")
        gap = self.analyze_performance_gap(optimal, backtest)

        print(f"\n   📊 PERFORMANCE GAP:")
        print(f"      Trade Frequency: {gap['trade_frequency']['current']:.2f}/hr vs {gap['trade_frequency']['optimal']:.2f}/hr target")
        print(f"      Gap: {gap['trade_frequency']['gap']:+.2f} trades/hr ({gap['trade_frequency']['gap_pct']:+.1f}%)")
        print(f"      Total Trades: {gap['total_trades']['current']} vs {gap['total_trades']['optimal']} optimal")
        print(f"      Missing: {gap['total_trades']['gap']} trades")

        # Determine if optimization is needed
        if abs(gap['trade_frequency']['gap_pct']) < 20:
            print(f"\n   ✅ System is well-tuned! Gap < 20%")
            print(f"      Current: {gap['trade_frequency']['current']:.2f} trades/hr")
            print(f"      Target: {gap['trade_frequency']['optimal']:.2f} trades/hr")
            return

        print("\n[5/5] Getting Claude's optimization recommendations...")
        prompt = self.build_optimization_prompt(rules, optimal, backtest, gap)

        try:
            recommendations = self.get_claude_recommendations(prompt)

            print(f"\n   💡 REASONING: {recommendations['reasoning']}")
            print(f"\n   🎯 PRIORITY: {recommendations['priority_issue']}")
            print(f"\n   📝 RECOMMENDED CHANGES:")

            # Apply recommendations
            updated_rules = self.apply_recommendations(rules, recommendations)

            print(f"\n   📈 EXPECTED RESULTS:")
            expected = recommendations['expected_results']
            print(f"      Trades: {expected.get('trades', 'unknown')}")
            print(f"      Trades/hr: {expected.get('trades_per_hour', 'unknown')}")
            print(f"      Improvement: {expected.get('improvement_pct', 'unknown')}%")

            # Save updated rules
            print(f"\n   💾 Saving updated rules...")
            self.save_rules(updated_rules)

            print(f"\n✅ Optimization complete!")
            print(f"   Rules updated: {self.rules_path}")
            print(f"   Next: Regenerate backtest to test changes")

        except Exception as e:
            print(f"\n   ❌ Optimization failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    optimizer = UserPatternOptimizer()
    optimizer.optimize()
