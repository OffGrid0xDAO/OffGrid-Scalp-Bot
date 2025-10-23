"""
Actual Trade Learner - Analyzes real trades from claude_decisions.csv
Learns from actual bot execution to improve future decisions
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path


class ActualTradeLearner:
    """
    Analyzes actual trades executed by the bot to learn patterns
    """

    def __init__(self, decisions_file='trading_data/claude_decisions.csv'):
        self.decisions_file = decisions_file
        self.insights = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_winner_pnl': 0.0,
            'avg_loser_pnl': 0.0,
            'avg_hold_time_minutes': 0.0,
            'best_entry_conditions': [],
            'worst_entry_conditions': [],
            'common_mistakes': []
        }

    def load_actual_trades(self, hours_back: int = 24) -> pd.DataFrame:
        """Load actual trades from decisions log"""

        if not Path(self.decisions_file).exists():
            print(f"⚠️  No decisions file found at {self.decisions_file}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(self.decisions_file)

            if df.empty:
                return df

            # Convert timestamp
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

                # Filter to recent trades
                cutoff = datetime.now() - timedelta(hours=hours_back)
                df = df[df['timestamp'] >= cutoff]

            return df

        except Exception as e:
            print(f"⚠️  Error loading decisions file: {e}")
            return pd.DataFrame()

    def analyze_trades(self, hours_back: int = 24) -> Dict:
        """Analyze actual trades and extract learnings"""

        df = self.load_actual_trades(hours_back)

        if df.empty:
            return {
                'status': 'no_data',
                'message': 'No actual trades found to analyze',
                'insights': self.insights
            }

        # Separate entries and exits
        entries = df[df['action'] == 'ENTER']
        exits = df[df['action'] == 'EXIT']

        if len(entries) == 0:
            return {
                'status': 'no_trades',
                'message': f'No trades executed in last {hours_back} hours',
                'insights': self.insights
            }

        # Match entries with exits to calculate performance
        trades = []
        for _, entry in entries.iterrows():
            # Find corresponding exit
            matching_exit = exits[
                (exits['timestamp'] > entry['timestamp']) &
                (exits.get('direction', '') == entry.get('direction', ''))
            ].head(1)

            if not matching_exit.empty:
                exit_row = matching_exit.iloc[0]

                # Calculate trade metrics
                entry_price = entry.get('current_price', 0)
                exit_price = exit_row.get('current_price', 0)

                if entry_price > 0 and exit_price > 0:
                    if entry.get('direction') == 'LONG':
                        pnl_pct = (exit_price - entry_price) / entry_price
                    else:  # SHORT
                        pnl_pct = (entry_price - exit_price) / entry_price

                    hold_time = (exit_row['timestamp'] - entry['timestamp']).total_seconds() / 60

                    trades.append({
                        'entry_time': entry['timestamp'],
                        'exit_time': exit_row['timestamp'],
                        'direction': entry.get('direction', 'UNKNOWN'),
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct * 100,
                        'hold_time_minutes': hold_time,
                        'entry_confidence': entry.get('confidence', 0),
                        'entry_reasoning': entry.get('reasoning', ''),
                        'exit_reason': exit_row.get('exit_reason', 'unknown'),
                        'winner': pnl_pct > 0
                    })

        if not trades:
            return {
                'status': 'incomplete_trades',
                'message': 'Trades opened but not yet closed',
                'insights': self.insights
            }

        # Calculate statistics
        winners = [t for t in trades if t['winner']]
        losers = [t for t in trades if not t['winner']]

        self.insights = {
            'total_trades': len(trades),
            'winning_trades': len(winners),
            'losing_trades': len(losers),
            'win_rate': len(winners) / len(trades) if trades else 0,
            'avg_winner_pnl': sum(t['pnl_pct'] for t in winners) / len(winners) if winners else 0,
            'avg_loser_pnl': sum(t['pnl_pct'] for t in losers) / len(losers) if losers else 0,
            'avg_hold_time_minutes': sum(t['hold_time_minutes'] for t in trades) / len(trades),
            'total_pnl': sum(t['pnl_pct'] for t in trades),
            'trades': trades
        }

        # Analyze best and worst setups
        trades_sorted = sorted(trades, key=lambda x: x['pnl_pct'], reverse=True)

        best_trades = trades_sorted[:min(5, len(trades))]
        worst_trades = trades_sorted[-min(5, len(trades)):]

        self.insights['best_entry_conditions'] = [
            {
                'reasoning': t['entry_reasoning'][:200],
                'confidence': t['entry_confidence'],
                'pnl': t['pnl_pct'],
                'hold_time': t['hold_time_minutes']
            }
            for t in best_trades
        ]

        self.insights['worst_entry_conditions'] = [
            {
                'reasoning': t['entry_reasoning'][:200],
                'confidence': t['entry_confidence'],
                'pnl': t['pnl_pct'],
                'exit_reason': t['exit_reason']
            }
            for t in worst_trades
        ]

        # Identify common mistakes
        self.insights['common_mistakes'] = self._identify_mistakes(trades)

        return {
            'status': 'success',
            'message': f'Analyzed {len(trades)} completed trades',
            'insights': self.insights
        }

    def _identify_mistakes(self, trades: List[Dict]) -> List[str]:
        """Identify common patterns in losing trades"""

        losers = [t for t in trades if not t['winner']]
        if not losers:
            return []

        mistakes = []

        # Check for common exit reasons
        exit_reasons = {}
        for trade in losers:
            reason = trade['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        most_common_exit = max(exit_reasons.items(), key=lambda x: x[1]) if exit_reasons else None
        if most_common_exit and most_common_exit[1] >= 2:
            mistakes.append(f"Most losses from {most_common_exit[0]} ({most_common_exit[1]} times)")

        # Check for short hold times in losers
        short_holds = [t for t in losers if t['hold_time_minutes'] < 5]
        if len(short_holds) >= len(losers) * 0.5:
            mistakes.append(f"50%+ of losses held <5 minutes - possibly entering too early")

        # Check confidence correlation
        low_confidence_losers = [t for t in losers if t['entry_confidence'] < 0.75]
        if len(low_confidence_losers) >= len(losers) * 0.6:
            mistakes.append(f"60%+ of losses had confidence <75% - need higher conviction")

        return mistakes

    def get_learning_summary(self) -> str:
        """Generate a human-readable summary of learnings"""

        if self.insights['total_trades'] == 0:
            return "No actual trades to learn from yet."

        summary = f"""
ACTUAL TRADE ANALYSIS
=====================

Performance:
- Total Trades: {self.insights['total_trades']}
- Win Rate: {self.insights['win_rate']*100:.1f}%
- Total PnL: {self.insights.get('total_pnl', 0):.2f}%
- Avg Winner: +{self.insights['avg_winner_pnl']:.2f}%
- Avg Loser: {self.insights['avg_loser_pnl']:.2f}%
- Avg Hold Time: {self.insights['avg_hold_time_minutes']:.1f} minutes

Best Setups:
"""
        for i, setup in enumerate(self.insights['best_entry_conditions'][:3], 1):
            summary += f"{i}. PnL: +{setup['pnl']:.2f}% | Confidence: {setup['confidence']*100:.0f}% | {setup['reasoning'][:100]}\n"

        summary += "\nWorst Setups:\n"
        for i, setup in enumerate(self.insights['worst_entry_conditions'][:3], 1):
            summary += f"{i}. PnL: {setup['pnl']:.2f}% | Exit: {setup['exit_reason']} | {setup['reasoning'][:100]}\n"

        if self.insights['common_mistakes']:
            summary += "\nCommon Mistakes:\n"
            for mistake in self.insights['common_mistakes']:
                summary += f"- {mistake}\n"

        return summary.strip()


if __name__ == '__main__':
    # Test the learner
    learner = ActualTradeLearner()
    result = learner.analyze_trades(hours_back=48)

    print(result['message'])
    print("\n" + learner.get_learning_summary())
