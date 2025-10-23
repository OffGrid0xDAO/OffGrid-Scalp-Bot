#!/usr/bin/env python3
"""
Claude LLM Optimizer

Uses Claude AI to continuously improve trading strategy by:
1. Analyzing backtest vs optimal performance gap
2. Identifying what conditions led to best trades
3. Suggesting parameter adjustments
4. Validating improvements before applying

This is the BRAIN that makes the strategy better over time!
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class ClaudeOptimizer:
    """
    Claude LLM-powered strategy optimizer

    Optimization Loop:
    1. Run backtest with current parameters
    2. Find optimal trades (perfect hindsight)
    3. Calculate performance gap
    4. Generate analysis report for Claude
    5. Claude suggests improvements
    6. Validate on separate data
    7. Apply if better
    8. Log everything
    """

    def __init__(self, log_dir: str = None):
        """
        Initialize Claude optimizer

        Args:
            log_dir: Directory to save optimization logs
        """
        if log_dir is None:
            log_dir = Path(__file__).parent.parent.parent / 'optimization_logs'

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.optimization_history = []

    def analyze_performance_gap(
        self,
        backtest_results: Dict,
        optimal_trades: List[Dict]
    ) -> Dict:
        """
        Analyze gap between backtest and optimal performance

        This is what we show Claude to help it improve!

        Args:
            backtest_results: Results from BacktestEngine
            optimal_trades: Results from OptimalTradeFinder

        Returns:
            dict with gap analysis:
                - missed_trades: trades we didn't take
                - early_exits: trades we exited too early
                - late_entries: trades we entered too late
                - parameter_insights: what needs adjustment
        """
        print("\n" + "="*80)
        print("ANALYZING PERFORMANCE GAP")
        print("="*80)

        backtest_trades = backtest_results['trades']
        metrics = backtest_results['metrics']

        # Calculate optimal performance
        optimal_total_profit = sum(t['profit_pct'] for t in optimal_trades)
        optimal_avg_profit = np.mean([t['profit_pct'] for t in optimal_trades])

        # Calculate backtest performance
        backtest_total_profit = metrics.get('total_return', 0)
        backtest_avg_profit = metrics.get('avg_win', 0)

        # Gap analysis
        profit_gap = optimal_total_profit - backtest_total_profit
        profit_gap_pct = profit_gap / optimal_total_profit * 100 if optimal_total_profit > 0 else 0

        print(f"\n📊 Performance Comparison:")
        print(f"   Optimal total profit: {optimal_total_profit:.2f}%")
        print(f"   Backtest total profit: {backtest_total_profit:.2f}%")
        print(f"   Gap: {profit_gap:.2f}% ({profit_gap_pct:.1f}% of optimal)")

        # Analyze missed trades
        backtest_entry_times = [t['entry_time'] for t in backtest_trades]
        optimal_entry_times = [t['entry_time'] for t in optimal_trades]

        missed_trades = [t for t in optimal_trades if t['entry_time'] not in backtest_entry_times]
        missed_profit = sum(t['profit_pct'] for t in missed_trades)

        print(f"\n❌ Missed Trades:")
        print(f"   Count: {len(missed_trades)}")
        print(f"   Missed profit: {missed_profit:.2f}%")

        # Analyze why we missed them
        if missed_trades:
            missed_conditions = self._analyze_trade_conditions(missed_trades)
            print(f"\n🔍 Conditions in Missed Trades:")
            print(f"   Avg confluence gap: {missed_conditions['avg_confluence_gap']:.1f}")
            print(f"   Volume elevated/spike: {missed_conditions['volume_high_pct']:.1f}%")
            print(f"   Avg compression: {missed_conditions['avg_compression']:.1f}")

        # Analyze early exits (MFE > realized profit)
        early_exits = []
        for trade in backtest_trades:
            if trade['mfe'] > trade['total_pnl_pct'] + 0.5:  # At least 0.5% left on table
                early_exits.append({
                    'trade': trade,
                    'mfe': trade['mfe'],
                    'realized': trade['total_pnl_pct'],
                    'gap': trade['mfe'] - trade['total_pnl_pct']
                })

        if early_exits:
            avg_early_exit_gap = np.mean([e['gap'] for e in early_exits])
            print(f"\n⏰ Early Exits:")
            print(f"   Count: {len(early_exits)}")
            print(f"   Avg profit left on table: {avg_early_exit_gap:.2f}%")

        # Compile analysis
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'optimal_trades': len(optimal_trades),
            'backtest_trades': len(backtest_trades),
            'optimal_total_profit': optimal_total_profit,
            'backtest_total_profit': backtest_total_profit,
            'profit_gap': profit_gap,
            'profit_gap_pct': profit_gap_pct,
            'missed_trades': {
                'count': len(missed_trades),
                'missed_profit': missed_profit,
                'conditions': missed_conditions if missed_trades else {}
            },
            'early_exits': {
                'count': len(early_exits),
                'avg_gap': avg_early_exit_gap if early_exits else 0
            },
            'backtest_metrics': metrics
        }

        return analysis

    def _analyze_trade_conditions(self, trades: List[Dict]) -> Dict:
        """Analyze conditions present in a set of trades"""
        if not trades:
            return {}

        confluence_gaps = []
        volume_high = 0
        compression_scores = []

        for trade in trades:
            ind = trade['indicators_at_entry']
            confluence_gaps.append(ind['confluence_gap'])
            if ind['volume_status'] in ['elevated', 'spike']:
                volume_high += 1
            compression_scores.append(ind['compression_score'])

        return {
            'avg_confluence_gap': np.mean(confluence_gaps),
            'volume_high_pct': volume_high / len(trades) * 100,
            'avg_compression': np.mean(compression_scores)
        }

    def generate_optimization_prompt(self, gap_analysis: Dict, current_params: Dict) -> str:
        """
        Generate prompt for Claude LLM

        Args:
            gap_analysis: Performance gap analysis
            current_params: Current strategy parameters

        Returns:
            str: Prompt to send to Claude
        """
        prompt = f"""
# Trading Strategy Optimization Request

I'm running a cryptocurrency trading bot and need help optimizing the strategy parameters.

## Current Performance

**Backtest Results:**
- Total trades: {gap_analysis['backtest_metrics']['total_trades']}
- Win rate: {gap_analysis['backtest_metrics']['win_rate']:.1f}%
- Total return: {gap_analysis['backtest_total_profit']:.2f}%
- Profit factor: {gap_analysis['backtest_metrics']['profit_factor']:.2f}
- Max drawdown: {gap_analysis['backtest_metrics']['max_drawdown']:.2f}%

**Optimal Performance (Perfect Hindsight):**
- Potential trades: {gap_analysis['optimal_trades']}
- Potential return: {gap_analysis['optimal_total_profit']:.2f}%

**Performance Gap:**
- We're capturing {100 - gap_analysis['profit_gap_pct']:.1f}% of available profit
- Missed {gap_analysis['missed_trades']['count']} trades worth {gap_analysis['missed_trades']['missed_profit']:.2f}%
- Exited {gap_analysis['early_exits']['count']} trades too early, leaving {gap_analysis['early_exits']['avg_gap']:.2f}% avg on table

## Missed Trade Analysis

Conditions in missed profitable trades:
- Average confluence gap: {gap_analysis['missed_trades']['conditions'].get('avg_confluence_gap', 0):.1f}
- High volume %: {gap_analysis['missed_trades']['conditions'].get('volume_high_pct', 0):.1f}%
- Average compression: {gap_analysis['missed_trades']['conditions'].get('avg_compression', 0):.1f}

## Current Parameters

```json
{json.dumps(current_params, indent=2)}
```

## Question

Based on this data, what parameter adjustments would you suggest to:
1. Capture more of the missed profitable trades
2. Reduce early exits (hold winners longer)
3. Improve overall win rate and profit factor

Please provide specific numerical suggestions in this JSON format:

```json
{{
  "suggested_changes": {{
    "confluence_gap_min": <number>,
    "confluence_score_min": <number>,
    "volume_requirement": [<list of strings>],
    "take_profit_levels": [<list of numbers>],
    "stop_loss_pct": <number>
  }},
  "reasoning": "Brief explanation of why these changes should help"
}}
```
"""
        return prompt

    def save_optimization_log(self, analysis: Dict, params_before: Dict, params_after: Dict = None):
        """
        Save optimization attempt to log

        Args:
            analysis: Gap analysis
            params_before: Parameters before optimization
            params_after: Parameters after optimization (if applied)
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis,
            'params_before': params_before,
            'params_after': params_after
        }

        self.optimization_history.append(log_entry)

        # Save to file
        log_file = self.log_dir / f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)

        print(f"\n💾 Optimization log saved: {log_file}")

    def apply_parameter_changes(
        self,
        suggested_changes: Dict,
        params_file: str,
        max_change_pct: float = 20.0
    ) -> Dict:
        """
        Apply suggested parameter changes with safety limits

        Args:
            suggested_changes: Changes suggested by Claude
            params_file: Path to strategy_params.json
            max_change_pct: Maximum % change allowed per parameter

        Returns:
            dict with updated parameters
        """
        # Load current params
        with open(params_file, 'r') as f:
            params = json.load(f)

        old_params = params['entry_filters'].copy()

        # Apply changes with limits
        for key, new_value in suggested_changes.items():
            if key in params['entry_filters']:
                old_value = params['entry_filters'][key]

                # For numeric values, limit change
                if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                    max_change = old_value * (max_change_pct / 100)
                    limited_value = np.clip(new_value, old_value - max_change, old_value + max_change)

                    params['entry_filters'][key] = limited_value
                    print(f"   {key}: {old_value} → {limited_value} (suggested: {new_value})")
                else:
                    params['entry_filters'][key] = new_value
                    print(f"   {key}: {old_value} → {new_value}")

        # Save updated params
        with open(params_file, 'w') as f:
            json.dump(params, f, indent=2)

        print(f"\n✅ Parameters updated: {params_file}")

        return params


if __name__ == '__main__':
    """Test optimizer"""
    print("Claude Optimizer - Ready for integration with Claude API")
    print("\nThis module generates optimization prompts based on performance gap analysis.")
    print("Integration with actual Claude API calls will be in the main execution script.")
