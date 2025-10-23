#!/usr/bin/env python3
"""
Actual Trade Learner - Learn from Real Executed Trades
Uses claude_decisions.csv to analyze what works and what doesn't
"""

import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from pathlib import Path
from collections import defaultdict


class ActualTradeLearner:
    """
    Analyzes actual executed trades from claude_decisions.csv
    Generates insights about what's working and what's not
    """

    def __init__(self, decisions_file='trading_data/claude_decisions.csv'):
        self.decisions_file = decisions_file
        self.trades = []
        self.insights = {}

    def load_actual_trades(self) -> List[Dict]:
        """Load all executed trades from claude_decisions.csv"""
        trades = []
        current_position = None

        try:
            with open(self.decisions_file, 'r') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    timestamp = row['timestamp']
                    action_type = row['action_type']
                    direction = row['direction']
                    entry_recommended = row['entry_recommended']
                    entry_price = float(row['entry_price'])
                    executed = row['executed']
                    confidence = float(row['confidence_score'])
                    reasoning = row['reasoning']

                    # Check for entry
                    if entry_recommended == 'YES' and executed == 'True':
                        if current_position is None:
                            current_position = {
                                'entry_time': timestamp,
                                'entry_price': entry_price,
                                'direction': direction,
                                'confidence': confidence,
                                'entry_reasoning': reasoning
                            }

                    # Check for exit
                    elif action_type == 'exit' and executed == 'True':
                        if current_position:
                            exit_price = entry_price  # In exit rows, entry_price is current price

                            # Calculate P&L
                            if current_position['direction'] == 'LONG':
                                pnl = exit_price - current_position['entry_price']
                            else:  # SHORT
                                pnl = current_position['entry_price'] - exit_price

                            pnl_pct = (pnl / current_position['entry_price']) * 100

                            # Calculate hold time
                            entry_dt = datetime.fromisoformat(current_position['entry_time'])
                            exit_dt = datetime.fromisoformat(timestamp)
                            hold_minutes = (exit_dt - entry_dt).total_seconds() / 60

                            trade = {
                                'entry_time': current_position['entry_time'],
                                'entry_price': current_position['entry_price'],
                                'exit_time': timestamp,
                                'exit_price': exit_price,
                                'direction': current_position['direction'],
                                'confidence': current_position['confidence'],
                                'pnl_dollars': pnl,
                                'pnl_percent': pnl_pct,
                                'hold_minutes': hold_minutes,
                                'profitable': pnl > 0,
                                'entry_reasoning': current_position['entry_reasoning'],
                                'exit_reasoning': reasoning
                            }

                            trades.append(trade)
                            current_position = None

            print(f"✅ Loaded {len(trades)} actual executed trades")
            return trades

        except Exception as e:
            print(f"❌ Error loading trades: {e}")
            return []

    def get_ema_pattern_from_reasoning(self, reasoning: str) -> Dict:
        """Extract EMA pattern info from reasoning text"""
        # Look for EMA counts in reasoning
        import re

        pattern = {
            'light_green': 0,
            'dark_green': 0,
            'light_red': 0,
            'dark_red': 0,
            'ribbon_state': 'unknown'
        }

        # Extract ribbon state
        if 'all_green' in reasoning.lower():
            pattern['ribbon_state'] = 'all_green'
        elif 'all_red' in reasoning.lower():
            pattern['ribbon_state'] = 'all_red'
        elif 'mixed_green' in reasoning.lower():
            pattern['ribbon_state'] = 'mixed_green'
        elif 'mixed_red' in reasoning.lower():
            pattern['ribbon_state'] = 'mixed_red'

        # Extract LIGHT EMA counts
        light_match = re.search(r'(\d+)\+?\s*LIGHT\s+(green|red)', reasoning, re.IGNORECASE)
        if light_match:
            count = int(light_match.group(1))
            color = light_match.group(2).lower()
            if color == 'green':
                pattern['light_green'] = count
            else:
                pattern['light_red'] = count

        # Extract DARK EMA counts
        dark_match = re.search(r'(\d+)\s*DARK\s+(green|red)', reasoning, re.IGNORECASE)
        if dark_match:
            count = int(dark_match.group(1))
            color = dark_match.group(2).lower()
            if color == 'green':
                pattern['dark_green'] = count
            else:
                pattern['dark_red'] = count

        return pattern

    def analyze_trades(self, trades: List[Dict]) -> Dict:
        """Analyze trades to find patterns of success and failure"""
        if not trades:
            return {}

        profitable = [t for t in trades if t['profitable']]
        losing = [t for t in trades if not t['profitable']]

        # Basic stats
        total_pnl = sum(t['pnl_dollars'] for t in trades)
        win_rate = (len(profitable) / len(trades)) * 100

        # Analyze EMA patterns
        ema_patterns = defaultdict(lambda: {'total': 0, 'profitable': 0, 'total_pnl': 0})

        for trade in trades:
            pattern = self.get_ema_pattern_from_reasoning(trade['entry_reasoning'])

            # Create signature
            sig = f"{pattern['ribbon_state']}_LG{pattern['light_green']}_DG{pattern['dark_green']}_LR{pattern['light_red']}_DR{pattern['dark_red']}"

            ema_patterns[sig]['total'] += 1
            ema_patterns[sig]['total_pnl'] += trade['pnl_dollars']
            if trade['profitable']:
                ema_patterns[sig]['profitable'] += 1

        # Calculate EMA pattern win rates
        ema_pattern_stats = []
        for sig, stats in ema_patterns.items():
            if stats['total'] >= 2:  # At least 2 trades
                win_rate_pattern = (stats['profitable'] / stats['total']) * 100
                ema_pattern_stats.append({
                    'signature': sig,
                    'total': stats['total'],
                    'profitable': stats['profitable'],
                    'win_rate': win_rate_pattern,
                    'avg_pnl': stats['total_pnl'] / stats['total']
                })

        ema_pattern_stats.sort(key=lambda x: x['win_rate'], reverse=True)

        # Analyze by direction
        long_trades = [t for t in trades if t['direction'] == 'LONG']
        short_trades = [t for t in trades if t['direction'] == 'SHORT']

        long_winners = [t for t in long_trades if t['profitable']]
        short_winners = [t for t in short_trades if t['profitable']]

        # Analyze by confidence level
        high_conf_trades = [t for t in trades if t['confidence'] >= 0.85]
        med_conf_trades = [t for t in trades if 0.75 <= t['confidence'] < 0.85]
        low_conf_trades = [t for t in trades if t['confidence'] < 0.75]

        # Analyze hold times
        winner_hold_times = [t['hold_minutes'] for t in profitable] if profitable else [0]
        loser_hold_times = [t['hold_minutes'] for t in losing] if losing else [0]

        # Extract key lessons from reasoning
        lessons = self._extract_lessons(trades)

        insights = {
            'total_trades': len(trades),
            'profitable_trades': len(profitable),
            'losing_trades': len(losing),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl_per_trade': total_pnl / len(trades),

            # Direction analysis
            'long_stats': {
                'total': len(long_trades),
                'winners': len(long_winners),
                'win_rate': (len(long_winners) / len(long_trades) * 100) if long_trades else 0,
                'total_pnl': sum(t['pnl_dollars'] for t in long_trades)
            },
            'short_stats': {
                'total': len(short_trades),
                'winners': len(short_winners),
                'win_rate': (len(short_winners) / len(short_trades) * 100) if short_trades else 0,
                'total_pnl': sum(t['pnl_dollars'] for t in short_trades)
            },

            # Confidence analysis
            'high_conf_performance': {
                'total': len(high_conf_trades),
                'win_rate': (len([t for t in high_conf_trades if t['profitable']]) / len(high_conf_trades) * 100) if high_conf_trades else 0
            },
            'med_conf_performance': {
                'total': len(med_conf_trades),
                'win_rate': (len([t for t in med_conf_trades if t['profitable']]) / len(med_conf_trades) * 100) if med_conf_trades else 0
            },
            'low_conf_performance': {
                'total': len(low_conf_trades),
                'win_rate': (len([t for t in low_conf_trades if t['profitable']]) / len(low_conf_trades) * 100) if low_conf_trades else 0
            },

            # Hold time analysis
            'avg_winner_hold_time': sum(winner_hold_times) / len(winner_hold_times) if winner_hold_times else 0,
            'avg_loser_hold_time': sum(loser_hold_times) / len(loser_hold_times) if loser_hold_times else 0,

            # Best/worst trades
            'best_trade': max(trades, key=lambda t: t['pnl_dollars']),
            'worst_trade': min(trades, key=lambda t: t['pnl_dollars']),

            # EMA pattern analysis
            'ema_patterns': ema_pattern_stats,

            # Lessons learned
            'key_lessons': lessons
        }

        return insights

    def _extract_lessons(self, trades: List[Dict]) -> List[str]:
        """Extract key lessons from trade reasoning"""
        lessons = []

        profitable = [t for t in trades if t['profitable']]
        losing = [t for t in trades if not t['profitable']]

        # Analyze common patterns in winners
        if profitable:
            # Check if winners had certain keywords
            winner_reasons = [t['entry_reasoning'].lower() for t in profitable]

            # Common success patterns
            if sum('all_green' in r or 'all_red' in r for r in winner_reasons) / len(winner_reasons) > 0.6:
                lessons.append("WINNING PATTERN: Strong ribbon alignment (all_green/all_red) on both timeframes has 60%+ success rate")

            if sum('fresh' in r or 'flip' in r for r in winner_reasons) / len(winner_reasons) > 0.5:
                lessons.append("WINNING PATTERN: Fresh ribbon flips (not stale) lead to better entries")

        # Analyze common patterns in losers
        if losing:
            loser_reasons = [t['entry_reasoning'].lower() for t in losing]

            # Common failure patterns
            if sum('mixed' in r or 'choppy' in r for r in loser_reasons) / len(loser_reasons) > 0.5:
                lessons.append("LOSING PATTERN: AVOID mixed/choppy conditions - over 50% of losses occur here")

            if sum('conflicting' in r for r in loser_reasons) / len(loser_reasons) > 0.4:
                lessons.append("LOSING PATTERN: AVOID conflicting timeframe signals - high failure rate")

            # Check for ranging markets
            if sum('ranging' in r for r in loser_reasons) / len(loser_reasons) > 0.3:
                lessons.append("LOSING PATTERN: Ranging markets (<0.4% range) produce many losses - need breakout confirmation")

        # Direction bias lessons
        long_trades = [t for t in trades if t['direction'] == 'LONG']
        short_trades = [t for t in trades if t['direction'] == 'SHORT']

        if long_trades and short_trades:
            long_win_rate = len([t for t in long_trades if t['profitable']]) / len(long_trades) * 100
            short_win_rate = len([t for t in short_trades if t['profitable']]) / len(short_trades) * 100

            if abs(long_win_rate - short_win_rate) > 20:
                if long_win_rate > short_win_rate:
                    lessons.append(f"BIAS: LONG trades performing better ({long_win_rate:.0f}% vs {short_win_rate:.0f}%) - may be in bullish market phase")
                else:
                    lessons.append(f"BIAS: SHORT trades performing better ({short_win_rate:.0f}% vs {long_win_rate:.0f}%) - may be in bearish market phase")

        # Hold time lessons
        profitable = [t for t in trades if t['profitable']]
        losing = [t for t in trades if not t['profitable']]

        if profitable and losing:
            avg_winner_hold = sum(t['hold_minutes'] for t in profitable) / len(profitable)
            avg_loser_hold = sum(t['hold_minutes'] for t in losing) / len(losing)

            if avg_loser_hold > avg_winner_hold * 1.5:
                lessons.append(f"TIMING: Losing trades held too long (avg {avg_loser_hold:.0f}min vs winners {avg_winner_hold:.0f}min) - exit faster on losers")

        return lessons

    def generate_training_summary(self) -> str:
        """Generate a training summary for Claude AI"""
        trades = self.load_actual_trades()

        if not trades:
            return "No actual trade data available for learning."

        insights = self.analyze_trades(trades)
        self.insights = insights

        # Build training summary
        summary = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   ACTUAL TRADE PERFORMANCE ANALYSIS                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 OVERALL PERFORMANCE:
   Total Trades: {insights['total_trades']}
   Profitable: {insights['profitable_trades']} ✅ ({insights['win_rate']:.1f}% win rate)
   Losing: {insights['losing_trades']} ❌
   Total P&L: ${insights['total_pnl']:.2f}
   Avg P&L/Trade: ${insights['avg_pnl_per_trade']:.2f}

📈 DIRECTION ANALYSIS:
   LONG Trades: {insights['long_stats']['total']} trades, {insights['long_stats']['win_rate']:.1f}% win rate
      → P&L: ${insights['long_stats']['total_pnl']:.2f}

   SHORT Trades: {insights['short_stats']['total']} trades, {insights['short_stats']['win_rate']:.1f}% win rate
      → P&L: ${insights['short_stats']['total_pnl']:.2f}

🎯 CONFIDENCE LEVEL PERFORMANCE:
   High Confidence (≥85%): {insights['high_conf_performance']['total']} trades, {insights['high_conf_performance']['win_rate']:.1f}% win rate
   Medium Confidence (75-85%): {insights['med_conf_performance']['total']} trades, {insights['med_conf_performance']['win_rate']:.1f}% win rate
   Low Confidence (<75%): {insights['low_conf_performance']['total']} trades, {insights['low_conf_performance']['win_rate']:.1f}% win rate

⏱️  HOLD TIME ANALYSIS:
   Winners avg hold: {insights['avg_winner_hold_time']:.1f} minutes
   Losers avg hold: {insights['avg_loser_hold_time']:.1f} minutes

🏆 BEST TRADE:
   {insights['best_trade']['direction']} @ ${insights['best_trade']['entry_price']:.2f}
   P&L: ${insights['best_trade']['pnl_dollars']:.2f} ({insights['best_trade']['pnl_percent']:.3f}%)

💔 WORST TRADE:
   {insights['worst_trade']['direction']} @ ${insights['worst_trade']['entry_price']:.2f}
   P&L: ${insights['worst_trade']['pnl_dollars']:.2f} ({insights['worst_trade']['pnl_percent']:.3f}%)

════════════════════════════════════════════════════════════════════════════════
🎨 EMA PATTERN ANALYSIS (From Actual Trades):
════════════════════════════════════════════════════════════════════════════════
"""

        if insights.get('ema_patterns'):
            for i, pattern in enumerate(insights['ema_patterns'][:5], 1):  # Top 5 patterns
                emoji = "✅" if pattern['win_rate'] >= 50 else "⚠️" if pattern['win_rate'] >= 35 else "❌"
                summary += f"{emoji} {pattern['signature']}\n"
                summary += f"   {pattern['total']} trades | {pattern['win_rate']:.0f}% win rate | Avg P&L: ${pattern['avg_pnl']:.2f}\n"
        else:
            summary += "   Not enough data to analyze EMA patterns yet\n"

        summary += f"""
════════════════════════════════════════════════════════════════════════════════
🎓 KEY LESSONS LEARNED FROM ACTUAL TRADES:
════════════════════════════════════════════════════════════════════════════════
"""

        for i, lesson in enumerate(insights['key_lessons'], 1):
            summary += f"{i}. {lesson}\n"

        summary += f"""
════════════════════════════════════════════════════════════════════════════════
💡 RECOMMENDATIONS FOR FUTURE TRADES:
════════════════════════════════════════════════════════════════════════════════
"""

        # Generate recommendations based on insights
        recommendations = []

        if insights['win_rate'] < 40:
            recommendations.append("⚠️  Win rate is LOW (<40%). Focus on QUALITY over QUANTITY - only take highest confidence setups")

        if insights['short_stats']['win_rate'] < insights['long_stats']['win_rate'] - 20:
            recommendations.append("⚠️  SHORT trades underperforming - be more selective with SHORT entries or avoid in bullish markets")

        if insights['long_stats']['win_rate'] < insights['short_stats']['win_rate'] - 20:
            recommendations.append("⚠️  LONG trades underperforming - be more selective with LONG entries or avoid in bearish markets")

        if insights['high_conf_performance']['win_rate'] > insights['med_conf_performance']['win_rate'] + 15:
            recommendations.append(f"✅ High confidence trades performing {insights['high_conf_performance']['win_rate'] - insights['med_conf_performance']['win_rate']:.0f}% better - ONLY take ≥85% confidence setups")

        if insights['avg_loser_hold_time'] > insights['avg_winner_hold_time'] * 1.5:
            recommendations.append(f"⏱️  Exit losing trades FASTER - losers held {insights['avg_loser_hold_time']:.0f}min vs winners {insights['avg_winner_hold_time']:.0f}min")

        if not recommendations:
            recommendations.append("✅ Overall strategy is working - keep following current approach")

        for i, rec in enumerate(recommendations, 1):
            summary += f"{i}. {rec}\n"

        return summary

    def save_insights(self, output_file='actual_trade_insights.json'):
        """Save insights to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(self.insights, f, indent=2, default=str)
        print(f"💾 Insights saved to {output_file}")


def main():
    """Run actual trade analysis"""
    learner = ActualTradeLearner()

    print("🔬 Analyzing actual executed trades...\n")

    summary = learner.generate_training_summary()
    print(summary)

    learner.save_insights()


if __name__ == "__main__":
    main()
