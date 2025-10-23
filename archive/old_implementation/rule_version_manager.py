"""
Rule Version Manager
Tracks all rule changes, compares performance, and learns what works
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import shutil


class RuleVersionManager:
    """Manages rule versions and tracks performance of each version"""

    def __init__(self, rules_path: str = 'trading_rules.json',
                 versions_dir: str = 'rule_versions'):
        self.rules_path = rules_path
        self.versions_dir = versions_dir
        self.history_path = os.path.join(versions_dir, 'version_history.json')

        # Create versions directory if it doesn't exist
        os.makedirs(versions_dir, exist_ok=True)

        # Load or create version history
        self.history = self._load_history()

    def _load_history(self) -> List[Dict]:
        """Load version history"""
        if os.path.exists(self.history_path):
            with open(self.history_path, 'r') as f:
                return json.load(f)
        return []

    def _save_history(self):
        """Save version history"""
        with open(self.history_path, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)

    def save_version_before_update(self, reason: str = "optimization") -> str:
        """
        Save current rules as a versioned backup before updating
        Returns the version number
        """
        if not os.path.exists(self.rules_path):
            print("⚠️  No current rules to version")
            return None

        # Load current rules
        with open(self.rules_path, 'r') as f:
            current_rules = json.load(f)

        # Generate version number
        version_num = len(self.history) + 1
        timestamp = datetime.now().isoformat()
        version_id = f"v{version_num:04d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Save versioned copy
        version_path = os.path.join(self.versions_dir, f"{version_id}.json")
        with open(version_path, 'w') as f:
            json.dump(current_rules, f, indent=2)

        # Extract key metrics from current rules
        version_record = {
            'version_id': version_id,
            'version_num': version_num,
            'timestamp': timestamp,
            'reason': reason,
            'file_path': version_path,
            'key_parameters': self._extract_key_parameters(current_rules),
            'performance_snapshot': self._extract_performance(current_rules),
            'claude_insights': current_rules.get('claude_insights', {})
        }

        # Add to history
        self.history.append(version_record)
        self._save_history()

        print(f"📦 Saved rules version: {version_id}")
        return version_id

    def _extract_key_parameters(self, rules: dict) -> dict:
        """Extract key parameters for easy comparison"""
        entry = rules.get('entry_rules', {})
        exit_ = rules.get('exit_rules', {})

        return {
            'ribbon_alignment_threshold': entry.get('ribbon_alignment_threshold'),
            'min_light_emas_required': entry.get('min_light_emas_required'),
            'fresh_transition_max_minutes': entry.get('fresh_transition_max_minutes'),
            'max_hold_minutes': exit_.get('max_hold_minutes'),
            'profit_target_pct': exit_.get('profit_target_pct'),
            'stop_loss_pct': exit_.get('stop_loss_pct')
        }

    def _extract_performance(self, rules: dict) -> dict:
        """Extract performance metrics"""
        perf = rules.get('performance_metrics', {})

        return {
            'total_trades': perf.get('total_trades_executed', 0),
            'winning_trades': perf.get('winning_trades', 0),
            'losing_trades': perf.get('losing_trades', 0),
            'win_rate': perf.get('win_rate', 0.0),
            'avg_winner_pnl_pct': perf.get('avg_winner_pnl_pct', 0.0),
            'avg_loser_pnl_pct': perf.get('avg_loser_pnl_pct', 0.0)
        }

    def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict:
        """
        Compare two rule versions
        Returns what changed and how performance differed
        """
        v1 = self._get_version_by_id(version_id_1)
        v2 = self._get_version_by_id(version_id_2)

        if not v1 or not v2:
            return {'error': 'Version not found'}

        comparison = {
            'version_1': version_id_1,
            'version_2': version_id_2,
            'parameter_changes': {},
            'performance_changes': {}
        }

        # Compare parameters
        params1 = v1['key_parameters']
        params2 = v2['key_parameters']

        for key in params1.keys():
            if params1.get(key) != params2.get(key):
                val1 = params1.get(key)
                val2 = params2.get(key)

                # Calculate change only if BOTH values are numeric
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)) and val1 is not None and val2 is not None:
                    change = val2 - val1
                else:
                    change = 'N/A'

                comparison['parameter_changes'][key] = {
                    'from': val1,
                    'to': val2,
                    'change': change
                }

        # Compare performance
        perf1 = v1['performance_snapshot']
        perf2 = v2['performance_snapshot']

        for key in ['win_rate', 'avg_winner_pnl_pct', 'avg_loser_pnl_pct']:
            if key in perf1 and key in perf2:
                comparison['performance_changes'][key] = {
                    'from': perf1[key],
                    'to': perf2[key],
                    'change': perf2[key] - perf1[key]
                }

        return comparison

    def _get_version_by_id(self, version_id: str) -> Optional[Dict]:
        """Get version record by ID"""
        for v in self.history:
            if v['version_id'] == version_id:
                return v
        return None

    def analyze_what_worked(self) -> Dict:
        """
        Analyze all versions to determine what changes improved performance
        and what made it worse
        """
        if len(self.history) < 2:
            return {'message': 'Not enough versions to analyze (need at least 2)'}

        improvements = []
        regressions = []

        for i in range(1, len(self.history)):
            prev = self.history[i-1]
            curr = self.history[i]

            comparison = self.compare_versions(prev['version_id'], curr['version_id'])

            if 'performance_changes' in comparison and 'win_rate' in comparison['performance_changes']:
                win_rate_change = comparison['performance_changes']['win_rate']['change']

                if win_rate_change > 0:
                    improvements.append({
                        'from_version': prev['version_id'],
                        'to_version': curr['version_id'],
                        'win_rate_improvement': win_rate_change,
                        'parameter_changes': comparison['parameter_changes'],
                        'claude_reasoning': curr.get('claude_insights', {}).get('reasoning', 'N/A')
                    })
                elif win_rate_change < 0:
                    regressions.append({
                        'from_version': prev['version_id'],
                        'to_version': curr['version_id'],
                        'win_rate_decline': win_rate_change,
                        'parameter_changes': comparison['parameter_changes'],
                        'claude_reasoning': curr.get('claude_insights', {}).get('reasoning', 'N/A')
                    })

        analysis = {
            'total_versions': len(self.history),
            'improvements': improvements,
            'regressions': regressions,
            'patterns': self._identify_patterns(improvements, regressions)
        }

        return analysis

    def _identify_patterns(self, improvements: List[Dict], regressions: List[Dict]) -> Dict:
        """Identify what parameter changes tend to improve/worsen performance"""
        patterns = {
            'parameters_that_helped': {},
            'parameters_that_hurt': {}
        }

        # Analyze improvements
        for imp in improvements:
            for param, change_info in imp.get('parameter_changes', {}).items():
                if param not in patterns['parameters_that_helped']:
                    patterns['parameters_that_helped'][param] = []
                patterns['parameters_that_helped'][param].append({
                    'change': change_info,
                    'win_rate_improvement': imp['win_rate_improvement']
                })

        # Analyze regressions
        for reg in regressions:
            for param, change_info in reg.get('parameter_changes', {}).items():
                if param not in patterns['parameters_that_hurt']:
                    patterns['parameters_that_hurt'][param] = []
                patterns['parameters_that_hurt'][param].append({
                    'change': change_info,
                    'win_rate_decline': reg['win_rate_decline']
                })

        return patterns

    def get_learning_summary_for_claude(self) -> str:
        """
        Generate a summary of what we've learned from past rule changes
        This is sent to Claude to inform future optimization decisions
        """
        analysis = self.analyze_what_worked()

        if 'message' in analysis:
            return analysis['message']

        summary = f"""
## RULE OPTIMIZATION HISTORY & LEARNINGS

**Total Rule Versions:** {analysis['total_versions']}
**Successful Improvements:** {len(analysis['improvements'])}
**Performance Regressions:** {len(analysis['regressions'])}

### What Changes IMPROVED Performance:

"""
        if analysis['improvements']:
            for imp in analysis['improvements'][-3:]:  # Last 3 improvements
                summary += f"""
**Version: {imp['to_version']}**
- Win Rate Improvement: +{imp['win_rate_improvement']*100:.2f}%
- Parameter Changes:
{self._format_param_changes(imp['parameter_changes'])}
- Claude's Reasoning: {imp['claude_reasoning'][:200]}...
"""
        else:
            summary += "No improvements yet\n"

        summary += """
### What Changes HURT Performance:

"""
        if analysis['regressions']:
            for reg in analysis['regressions'][-2:]:  # Last 2 regressions
                summary += f"""
**Version: {reg['to_version']}**
- Win Rate Decline: {reg['win_rate_decline']*100:.2f}%
- Parameter Changes:
{self._format_param_changes(reg['parameter_changes'])}
- Claude's Reasoning: {reg['claude_reasoning'][:200]}...

⚠️ AVOID REPEATING THESE CHANGES!
"""
        else:
            summary += "No regressions (good!)\n"

        summary += """
### Identified Patterns:

"""
        patterns = analysis['patterns']

        if patterns['parameters_that_helped']:
            summary += "**Parameters that tend to IMPROVE performance when changed:**\n"
            for param, changes in patterns['parameters_that_helped'].items():
                avg_improvement = sum(c['win_rate_improvement'] for c in changes) / len(changes)
                summary += f"  - {param}: Avg improvement +{avg_improvement*100:.2f}%\n"

        if patterns['parameters_that_hurt']:
            summary += "\n**Parameters that tend to HURT performance when changed:**\n"
            for param, changes in patterns['parameters_that_hurt'].items():
                avg_decline = sum(c['win_rate_decline'] for c in changes) / len(changes)
                summary += f"  - {param}: Avg decline {avg_decline*100:.2f}%\n"

        summary += """
## RECOMMENDATION:
Learn from successful changes and avoid repeating regressions.
Focus on parameters that have historically improved performance.
"""

        return summary

    def _format_param_changes(self, changes: dict) -> str:
        """Format parameter changes for display"""
        if not changes:
            return "  No parameter changes"

        formatted = ""
        for param, change_info in changes.items():
            formatted += f"  - {param}: {change_info['from']} → {change_info['to']}"
            if isinstance(change_info.get('change'), (int, float)):
                sign = '+' if change_info['change'] > 0 else ''
                formatted += f" ({sign}{change_info['change']})"
            formatted += "\n"

        return formatted

    def get_latest_version(self) -> Optional[Dict]:
        """Get the most recent version"""
        if self.history:
            return self.history[-1]
        return None

    def get_all_versions(self) -> List[Dict]:
        """Get all version records"""
        return self.history
