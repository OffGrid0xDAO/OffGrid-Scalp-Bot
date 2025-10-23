"""
Analyze Claude's Trading Decisions
Compare his decisions against actual market data and backtest results
"""

import csv
import json
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd


class ClaudeDecisionAnalyzer:
    """
    Analyzes Claude's trading decisions to identify:
    - What he did right
    - What he did wrong
    - How to improve his decision-making
    """

    def __init__(self, decisions_file='trading_data/claude_decisions.csv',
                 ema_5min_file='trading_data/ema_data_5min.csv',
                 ema_15min_file='trading_data/ema_data_15min.csv'):
        self.decisions_file = decisions_file
        self.ema_5min_file = ema_5min_file
        self.ema_15min_file = ema_15min_file
        self.decisions = []
        self.ema_data_5min = []
        self.ema_data_15min = []
        self.analyzed_trades = []

    def load_data(self):
        """Load Claude's decisions and EMA data"""
        print("📊 Loading Claude's trading decisions...")

        # Load decisions
        try:
            with open(self.decisions_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        self.decisions.append({
                            'timestamp': datetime.fromisoformat(row['timestamp']),
                            'action_type': row.get('action_type', 'decision'),
                            'direction': row.get('direction', ''),
                            'entry_recommended': row.get('entry_recommended', ''),
                            'confidence': float(row.get('confidence', 0)),
                            'reasoning': row.get('reasoning', ''),
                            'entry_price': float(row.get('entry_price', 0)),
                            'stop_loss': float(row.get('stop_loss', 0)),
                            'take_profit': float(row.get('take_profit', 0)),
                            'executed': row.get('executed', 'False').lower() == 'true'
                        })
                    except Exception as e:
                        continue

            print(f"✅ Loaded {len(self.decisions)} Claude decisions")

        except FileNotFoundError:
            print(f"⚠️  No decisions file found at {self.decisions_file}")
            return False

        # Load EMA data
        try:
            df_5min = pd.read_csv(self.ema_5min_file)
            df_15min = pd.read_csv(self.ema_15min_file)

            for _, row in df_5min.iterrows():
                try:
                    self.ema_data_5min.append({
                        'timestamp': datetime.fromisoformat(row['timestamp']),
                        'price': float(row['price']),
                        'state': row['ribbon_state']
                    })
                except:
                    continue

            for _, row in df_15min.iterrows():
                try:
                    self.ema_data_15min.append({
                        'timestamp': datetime.fromisoformat(row['timestamp']),
                        'price': float(row['price']),
                        'state': row['ribbon_state']
                    })
                except:
                    continue

            print(f"✅ Loaded {len(self.ema_data_5min)} 5min data points")
            print(f"✅ Loaded {len(self.ema_data_15min)} 15min data points")

        except FileNotFoundError:
            print(f"⚠️  EMA data files not found")
            return False

        return True

    def analyze_trades(self):
        """Analyze each trade Claude executed"""
        print("\n🔍 Analyzing Claude's executed trades...")

        executed_entries = [d for d in self.decisions if d['executed'] and d['entry_recommended'].upper() == 'YES']

        print(f"Found {len(executed_entries)} executed trades")

        for entry in executed_entries:
            # Find exit decision
            exit_decision = self._find_exit(entry)

            # Calculate what actually happened
            actual_result = self._simulate_trade(entry, exit_decision)

            self.analyzed_trades.append({
                'entry': entry,
                'exit': exit_decision,
                'result': actual_result
            })

        print(f"✅ Analyzed {len(self.analyzed_trades)} complete trades")

    def _find_exit(self, entry: Dict) -> Dict:
        """Find the exit decision for an entry"""
        entry_time = entry['timestamp']

        # Look for exit within next 30 minutes
        for decision in self.decisions:
            if decision['timestamp'] > entry_time:
                # Check if it's an exit signal
                if decision['action_type'] == 'exit' or \
                   (decision['entry_recommended'].upper() == 'NO' and decision['executed']):
                    # Check if within reasonable timeframe (30 min)
                    if (decision['timestamp'] - entry_time).total_seconds() <= 1800:
                        return decision

        return None

    def _simulate_trade(self, entry: Dict, exit_decision: Dict = None) -> Dict:
        """Simulate what happened with the trade"""
        entry_time = entry['timestamp']
        entry_price = entry['entry_price']
        direction = entry['direction']

        # Find price data after entry
        prices_after = [p for p in self.ema_data_5min if p['timestamp'] > entry_time]

        if not prices_after:
            return {'status': 'incomplete', 'pnl_pct': 0}

        # If we have exit decision, use it
        if exit_decision:
            exit_time = exit_decision['timestamp']
            hold_duration = (exit_time - entry_time).total_seconds() / 60  # minutes

            # Find closest price to exit time
            closest_exit_price = min(prices_after,
                                     key=lambda p: abs((p['timestamp'] - exit_time).total_seconds()))
            exit_price = closest_exit_price['price']

        else:
            # Assume held for 15 minutes (typical scalp)
            hold_duration = 15
            exit_time = entry_time + timedelta(minutes=15)

            # Find price at 15 min mark
            prices_at_15min = [p for p in prices_after
                              if abs((p['timestamp'] - exit_time).total_seconds()) < 60]

            if prices_at_15min:
                exit_price = prices_at_15min[0]['price']
            else:
                exit_price = prices_after[min(len(prices_after)-1, 90)]['price']  # ~15min worth of data

        # Calculate P&L
        if direction.upper() == 'LONG':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        # Check if TP or SL was hit
        tp_hit = False
        sl_hit = False
        max_profit = 0
        max_loss = 0

        for price_point in prices_after[:180]:  # Check next 30 min
            if price_point['timestamp'] > exit_time:
                break

            price = price_point['price']

            if direction.upper() == 'LONG':
                profit = ((price - entry_price) / entry_price) * 100
                max_profit = max(max_profit, profit)
                max_loss = min(max_loss, profit)

                if entry['take_profit'] > 0 and price >= entry['take_profit']:
                    tp_hit = True
                if entry['stop_loss'] > 0 and price <= entry['stop_loss']:
                    sl_hit = True
            else:
                profit = ((entry_price - price) / entry_price) * 100
                max_profit = max(max_profit, profit)
                max_loss = min(max_loss, profit)

                if entry['take_profit'] > 0 and price <= entry['take_profit']:
                    tp_hit = True
                if entry['stop_loss'] > 0 and price >= entry['stop_loss']:
                    sl_hit = True

        return {
            'status': 'complete',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'hold_duration_min': hold_duration,
            'is_winner': pnl_pct > 0,
            'tp_hit': tp_hit,
            'sl_hit': sl_hit,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'exit_type': 'TP' if tp_hit else ('SL' if sl_hit else 'Manual')
        }

    def generate_report(self):
        """Generate comprehensive analysis report"""
        if not self.analyzed_trades:
            return "No trades to analyze"

        report = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    CLAUDE TRADING DECISIONS ANALYSIS                        ║
║                         What Worked, What Didn't                            ║
╚════════════════════════════════════════════════════════════════════════════╝

"""

        # Overall stats
        total_trades = len(self.analyzed_trades)
        winners = [t for t in self.analyzed_trades if t['result']['is_winner']]
        losers = [t for t in self.analyzed_trades if not t['result']['is_winner']]
        win_rate = (len(winners) / total_trades * 100) if total_trades > 0 else 0

        avg_winner = sum(w['result']['pnl_pct'] for w in winners) / len(winners) if winners else 0
        avg_loser = sum(l['result']['pnl_pct'] for l in losers) / len(losers) if losers else 0
        total_pnl = sum(t['result']['pnl_pct'] for t in self.analyzed_trades)

        report += f"""📊 OVERALL PERFORMANCE:
   Total Trades: {total_trades}
   Winners: {len(winners)} ({win_rate:.1f}%)
   Losers: {len(losers)} ({100-win_rate:.1f}%)
   Avg Winner: +{avg_winner:.3f}%
   Avg Loser: {avg_loser:.3f}%
   Total P&L: {total_pnl:+.2f}%

"""

        # Direction analysis
        long_trades = [t for t in self.analyzed_trades if t['entry']['direction'].upper() == 'LONG']
        short_trades = [t for t in self.analyzed_trades if t['entry']['direction'].upper() == 'SHORT']

        long_winners = [t for t in long_trades if t['result']['is_winner']]
        short_winners = [t for t in short_trades if t['result']['is_winner']]

        long_wr = (len(long_winners) / len(long_trades) * 100) if long_trades else 0
        short_wr = (len(short_winners) / len(short_trades) * 100) if short_trades else 0

        report += f"""📈 DIRECTION PERFORMANCE:
   LONG:  {len(long_trades)} trades | {long_wr:.1f}% win rate
   SHORT: {len(short_trades)} trades | {short_wr:.1f}% win rate

"""

        # Confidence analysis
        high_conf_trades = [t for t in self.analyzed_trades if t['entry']['confidence'] >= 0.80]
        med_conf_trades = [t for t in self.analyzed_trades if 0.65 <= t['entry']['confidence'] < 0.80]
        low_conf_trades = [t for t in self.analyzed_trades if t['entry']['confidence'] < 0.65]

        high_conf_winners = [t for t in high_conf_trades if t['result']['is_winner']]
        med_conf_winners = [t for t in med_conf_trades if t['result']['is_winner']]
        low_conf_winners = [t for t in low_conf_trades if t['result']['is_winner']]

        high_conf_wr = (len(high_conf_winners)/len(high_conf_trades)*100) if high_conf_trades else 0
        med_conf_wr = (len(med_conf_winners)/len(med_conf_trades)*100) if med_conf_trades else 0
        low_conf_wr = (len(low_conf_winners)/len(low_conf_trades)*100) if low_conf_trades else 0

        report += f"""🎯 CONFIDENCE ACCURACY:
   High (≥80%): {len(high_conf_trades)} trades | {high_conf_wr:.1f}% win rate
   Med (65-79%): {len(med_conf_trades)} trades | {med_conf_wr:.1f}% win rate
   Low (<65%): {len(low_conf_trades)} trades | {low_conf_wr:.1f}% win rate

"""

        # Hold duration analysis
        avg_hold_winners = sum(w['result']['hold_duration_min'] for w in winners) / len(winners) if winners else 0
        avg_hold_losers = sum(l['result']['hold_duration_min'] for l in losers) / len(losers) if losers else 0

        report += f"""⏱️  HOLD DURATION:
   Winners held avg: {avg_hold_winners:.1f} minutes
   Losers held avg: {avg_hold_losers:.1f} minutes

"""

        # Exit analysis
        tp_hits = [t for t in self.analyzed_trades if t['result']['tp_hit']]
        sl_hits = [t for t in self.analyzed_trades if t['result']['sl_hit']]
        manual_exits = [t for t in self.analyzed_trades if not t['result']['tp_hit'] and not t['result']['sl_hit']]

        report += f"""🎯 EXIT TYPES:
   TP Hit: {len(tp_hits)} trades
   SL Hit: {len(sl_hits)} trades
   Manual: {len(manual_exits)} trades

"""

        # Missed profits analysis (exited too early)
        missed_profits = []
        for trade in winners:
            actual_pnl = trade['result']['pnl_pct']
            max_profit = trade['result']['max_profit']
            if max_profit > actual_pnl * 1.5:  # Could have made 50% more
                missed_profits.append({
                    'actual': actual_pnl,
                    'max': max_profit,
                    'missed': max_profit - actual_pnl
                })

        if missed_profits:
            avg_missed = sum(m['missed'] for m in missed_profits) / len(missed_profits)
            report += f"""⚠️  EXITED TOO EARLY:
   {len(missed_profits)} trades could have made 50%+ more profit
   Avg missed profit: +{avg_missed:.3f}%

"""

        # Bad trades analysis (should not have entered)
        bad_trades = []
        for trade in losers:
            if trade['result']['max_loss'] < -0.5:  # Lost more than 0.5%
                bad_trades.append(trade)

        report += f"""❌ BAD TRADES (>0.5% loss):
   {len(bad_trades)} trades with significant losses
   These should have been avoided

"""

        # Sample bad trades
        if bad_trades:
            report += "\n📋 WORST TRADES:\n"
            for i, trade in enumerate(sorted(bad_trades, key=lambda t: t['result']['pnl_pct'])[:5], 1):
                entry = trade['entry']
                result = trade['result']
                report += f"""   {i}. {entry['direction']} @ ${entry['entry_price']:.2f} → ${result['exit_price']:.2f}
      Loss: {result['pnl_pct']:.3f}% | Hold: {result['hold_duration_min']:.1f}min
      Confidence: {entry['confidence']:.0%}
      Reasoning: {entry['reasoning'][:100]}...

"""

        # Sample best trades
        report += "\n✅ BEST TRADES:\n"
        best_trades = sorted(winners, key=lambda t: t['result']['pnl_pct'], reverse=True)[:5]
        for i, trade in enumerate(best_trades, 1):
            entry = trade['entry']
            result = trade['result']
            report += f"""   {i}. {entry['direction']} @ ${entry['entry_price']:.2f} → ${result['exit_price']:.2f}
      Profit: {result['pnl_pct']:.3f}% | Hold: {result['hold_duration_min']:.1f}min
      Confidence: {entry['confidence']:.0%}
      Reasoning: {entry['reasoning'][:100]}...

"""

        # Recommendations
        report += "\n" + "="*80 + "\n"
        report += "💡 RECOMMENDATIONS TO IMPROVE CLAUDE:\n"
        report += "="*80 + "\n\n"

        recommendations = []

        if long_wr > short_wr * 1.3:
            recommendations.append(f"✅ BIAS TOWARD LONG: {long_wr:.1f}% vs {short_wr:.1f}% - increase LONG preference")

        if short_wr > long_wr * 1.3:
            recommendations.append(f"✅ BIAS TOWARD SHORT: {short_wr:.1f}% vs {long_wr:.1f}% - increase SHORT preference")

        if win_rate < 50:
            recommendations.append(f"🔧 TIGHTEN ENTRY FILTERS: {win_rate:.1f}% win rate is too low - be more selective")

        if len(missed_profits) > len(winners) * 0.5:
            recommendations.append(f"🔧 HOLD LONGER: {len(missed_profits)} trades exited too early - extend hold time")

        if avg_hold_winners < 10:
            recommendations.append(f"🔧 TOO FAST: Winners held only {avg_hold_winners:.1f}min - allow more time to run")

        if len(high_conf_trades) > 0:
            high_conf_wr = len(high_conf_winners) / len(high_conf_trades) * 100
            if high_conf_wr < 70:
                recommendations.append(f"🔧 HIGH CONFIDENCE NOT RELIABLE: {high_conf_wr:.1f}% win rate - recalibrate confidence scoring")

        if len(sl_hits) > len(tp_hits):
            recommendations.append(f"🔧 TOO MANY STOP OUTS: {len(sl_hits)} SL hits vs {len(tp_hits)} TP hits - adjust SL placement")

        if not recommendations:
            recommendations.append("✅ Performance looks good! Keep refining based on patterns above.")

        for rec in recommendations:
            report += f"{rec}\n"

        report += "\n" + "="*80 + "\n"

        return report

    def save_analysis(self, output_file='claude_decision_analysis.json'):
        """Save detailed analysis to JSON"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'total_trades': len(self.analyzed_trades),
            'winners': len([t for t in self.analyzed_trades if t['result']['is_winner']]),
            'losers': len([t for t in self.analyzed_trades if not t['result']['is_winner']]),
            'trades': []
        }

        for trade in self.analyzed_trades:
            analysis['trades'].append({
                'entry_time': trade['entry']['timestamp'].isoformat(),
                'direction': trade['entry']['direction'],
                'entry_price': trade['entry']['entry_price'],
                'exit_price': trade['result']['exit_price'],
                'pnl_pct': trade['result']['pnl_pct'],
                'hold_duration': trade['result']['hold_duration_min'],
                'confidence': trade['entry']['confidence'],
                'is_winner': trade['result']['is_winner'],
                'exit_type': trade['result']['exit_type']
            })

        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)

        print(f"\n💾 Detailed analysis saved to {output_file}")


def main():
    analyzer = ClaudeDecisionAnalyzer()

    if not analyzer.load_data():
        print("❌ Failed to load data")
        return

    analyzer.analyze_trades()

    report = analyzer.generate_report()
    print(report)

    analyzer.save_analysis()

    print("\n✅ Analysis complete!")
    print("Review the recommendations above to improve Claude's decision-making.")


if __name__ == "__main__":
    main()
