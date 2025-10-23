"""
Optimal vs Actual Analyzer - Compares optimal trades with actual trades
Identifies gaps and missed opportunities
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path


class OptimalVsActualAnalyzer:
    """
    Compares optimal trades (from optimal_trades.json) with actual trades
    Identifies what we're missing and why
    """

    def __init__(self,
                 optimal_trades_file='trading_data/optimal_trades.json',
                 decisions_file='trading_data/claude_decisions.csv'):
        self.optimal_trades_file = optimal_trades_file
        self.decisions_file = decisions_file

    def load_optimal_trades(self) -> List[Dict]:
        """Load optimal trades from JSON"""

        if not Path(self.optimal_trades_file).exists():
            print(f"⚠️  Optimal trades file not found: {self.optimal_trades_file}")
            return []

        try:
            with open(self.optimal_trades_file, 'r') as f:
                data = json.load(f)
                return data.get('trades', [])
        except Exception as e:
            print(f"⚠️  Error loading optimal trades: {e}")
            return []

    def load_actual_trades(self) -> List[Dict]:
        """Load actual trades from decisions CSV"""

        if not Path(self.decisions_file).exists():
            print(f"⚠️  Decisions file not found: {self.decisions_file}")
            return []

        try:
            df = pd.read_csv(self.decisions_file)

            if df.empty:
                return []

            # Extract entries only
            entries = df[df['action'] == 'ENTER']

            trades = []
            for _, row in entries.iterrows():
                trades.append({
                    'entry_time': row.get('timestamp', ''),
                    'direction': row.get('direction', ''),
                    'entry_price': row.get('current_price', 0),
                    'confidence': row.get('confidence', 0),
                    'reasoning': row.get('reasoning', '')
                })

            return trades

        except Exception as e:
            print(f"⚠️  Error loading actual trades: {e}")
            return []

    def analyze_gaps(self, time_window_hours: int = 24) -> Dict:
        """
        Compare optimal vs actual trades and identify gaps
        """

        optimal_trades = self.load_optimal_trades()
        actual_trades = self.load_actual_trades()

        # Filter to time window
        cutoff = datetime.now() - timedelta(hours=time_window_hours)

        optimal_recent = [
            t for t in optimal_trades
            if pd.to_datetime(t.get('entry_time', '')) >= cutoff
        ]

        actual_recent = [
            t for t in actual_trades
            if pd.to_datetime(t.get('entry_time', '')) >= cutoff
        ]

        # Calculate statistics
        optimal_count = len(optimal_recent)
        actual_count = len(actual_recent)
        capture_rate = (actual_count / optimal_count * 100) if optimal_count > 0 else 0

        # Calculate PnL
        optimal_pnl = sum(t.get('pnl_pct', 0) for t in optimal_recent)
        missed_pnl = optimal_pnl  # Simplified - actual PnL calculation needs exit data

        # Identify missed opportunities
        missed_opportunities = []
        if optimal_count > actual_count:
            # Find optimal trades that weren't taken
            actual_times = set(t['entry_time'] for t in actual_recent)

            for optimal in optimal_recent:
                opt_time = optimal.get('entry_time')
                if opt_time not in actual_times:
                    missed_opportunities.append({
                        'time': opt_time,
                        'direction': optimal.get('direction', ''),
                        'potential_pnl': optimal.get('pnl_pct', 0),
                        'ribbon_state': optimal.get('ribbon_state', ''),
                        'reason_missed': self._diagnose_miss(optimal, actual_recent)
                    })

        # Sort by potential PnL
        missed_opportunities = sorted(
            missed_opportunities,
            key=lambda x: x['potential_pnl'],
            reverse=True
        )[:10]  # Top 10 missed

        return {
            'time_window_hours': time_window_hours,
            'optimal_trades_count': optimal_count,
            'actual_trades_count': actual_count,
            'capture_rate_pct': capture_rate,
            'missed_opportunities_count': len(missed_opportunities),
            'optimal_total_pnl': optimal_pnl,
            'missed_potential_pnl': missed_pnl,
            'top_missed_opportunities': missed_opportunities,
            'analysis': self._generate_analysis(
                optimal_count,
                actual_count,
                capture_rate,
                missed_opportunities
            )
        }

    def _diagnose_miss(self, optimal_trade: Dict, actual_trades: List[Dict]) -> str:
        """Diagnose why an optimal trade was missed"""

        # Check if there were any trades around the same time
        opt_time = pd.to_datetime(optimal_trade.get('entry_time'))

        nearby_trades = [
            t for t in actual_trades
            if abs((pd.to_datetime(t['entry_time']) - opt_time).total_seconds()) < 300  # 5 min
        ]

        if nearby_trades:
            return "Bot was active but chose different setup"

        # Check ribbon state
        ribbon_state = optimal_trade.get('ribbon_state', '')
        if 'mixed' in ribbon_state.lower():
            return "Mixed ribbon state - may have been filtered out"

        # Check time since transition
        if optimal_trade.get('minutes_since_transition', 0) > 15:
            return "Stale transition - exceeded freshness threshold"

        return "Unknown - bot may not have been checking or all filters blocked"

    def _generate_analysis(self,
                          optimal_count: int,
                          actual_count: int,
                          capture_rate: float,
                          missed: List[Dict]) -> str:
        """Generate human-readable analysis"""

        if optimal_count == 0:
            return "No optimal trades found in this period."

        analysis = f"""
OPTIMAL vs ACTUAL GAP ANALYSIS
==============================

Capture Rate: {capture_rate:.1f}%
- Optimal Opportunities: {optimal_count}
- Actually Taken: {actual_count}
- Missed: {optimal_count - actual_count}

"""

        if capture_rate >= 80:
            analysis += "✅ EXCELLENT - Catching most opportunities!\n"
        elif capture_rate >= 60:
            analysis += "⚠️  GOOD - But missing some opportunities\n"
        elif capture_rate >= 40:
            analysis += "⚠️  MODERATE - Missing significant opportunities\n"
        else:
            analysis += "🚨 POOR - Missing most optimal setups!\n"

        if missed:
            analysis += "\nTop Missed Opportunities:\n"
            for i, miss in enumerate(missed[:5], 1):
                analysis += f"{i}. {miss['direction']} @ {miss['time']} - Potential: {miss['potential_pnl']:.2f}%\n"
                analysis += f"   Reason: {miss['reason_missed']}\n"

            # Common patterns
            miss_reasons = {}
            for m in missed:
                reason = m['reason_missed']
                miss_reasons[reason] = miss_reasons.get(reason, 0) + 1

            analysis += "\nCommon Reasons for Misses:\n"
            for reason, count in sorted(miss_reasons.items(), key=lambda x: x[1], reverse=True):
                analysis += f"- {reason}: {count} times\n"

        return analysis.strip()

    def get_summary(self, hours: int = 24) -> str:
        """Get a formatted summary of the analysis"""

        result = self.analyze_gaps(time_window_hours=hours)
        return result['analysis']


if __name__ == '__main__':
    # Test the analyzer
    analyzer = OptimalVsActualAnalyzer()
    print(analyzer.get_summary(hours=24))
