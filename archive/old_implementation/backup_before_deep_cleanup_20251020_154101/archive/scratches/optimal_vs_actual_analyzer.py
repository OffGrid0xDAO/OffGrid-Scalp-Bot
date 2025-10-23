#!/usr/bin/env python3
"""
Optimal vs Actual Trade Analyzer
Finds the BEST possible trades from candlestick data and compares to actual trades
Shows what patterns YOU missed and what patterns you should focus on
"""

import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict, Counter


class OptimalVsActualAnalyzer:
    """
    Compares optimal trades (from candlestick analysis) vs actual trades (executed)
    """

    def __init__(self,
                 candlestick_csv='candlesticks_5min.csv',
                 decisions_csv='trading_data/claude_decisions.csv'):
        self.candlestick_csv = candlestick_csv
        self.decisions_csv = decisions_csv
        self.optimal_trades = []
        self.actual_trades = []

    def load_candlestick_data(self) -> List[Dict]:
        """Load candlestick data"""
        candles = []
        try:
            with open(self.candlestick_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row['price_open'] = float(row['price_open'])
                    row['price_high'] = float(row['price_high'])
                    row['price_low'] = float(row['price_low'])
                    row['price_close'] = float(row['price_close'])
                    candles.append(row)
            print(f"✅ Loaded {len(candles)} candles from candlestick data")
            return candles
        except Exception as e:
            print(f"❌ Error loading candlesticks: {e}")
            return []

    def load_actual_trades(self) -> List[Dict]:
        """Load actual executed trades"""
        trades = []
        current_position = None

        try:
            with open(self.decisions_csv, 'r') as f:
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
                                'reasoning': reasoning
                            }

                    # Check for exit
                    elif action_type == 'exit' and executed == 'True':
                        if current_position:
                            exit_price = entry_price

                            if current_position['direction'] == 'LONG':
                                pnl = exit_price - current_position['entry_price']
                            else:
                                pnl = current_position['entry_price'] - exit_price

                            pnl_pct = (pnl / current_position['entry_price']) * 100

                            entry_dt = datetime.fromisoformat(current_position['entry_time'])
                            exit_dt = datetime.fromisoformat(timestamp)
                            hold_minutes = (exit_dt - entry_dt).total_seconds() / 60

                            trade = {
                                'entry_time': current_position['entry_time'],
                                'entry_price': current_position['entry_price'],
                                'exit_time': timestamp,
                                'exit_price': exit_price,
                                'direction': current_position['direction'],
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'hold_minutes': hold_minutes,
                                'profitable': pnl > 0,
                                'reasoning': current_position['reasoning']
                            }

                            trades.append(trade)
                            current_position = None

            print(f"✅ Loaded {len(trades)} actual executed trades")
            return trades

        except Exception as e:
            print(f"❌ Error loading actual trades: {e}")
            return []

    def find_optimal_trades(self, candles: List[Dict]) -> List[Dict]:
        """
        Find the OPTIMAL trades - best possible entries/exits
        Uses perfect hindsight to find what SHOULD have been done
        """
        optimal_trades = []

        print(f"\n🔍 Finding OPTIMAL trades (with perfect hindsight)...")

        for i in range(len(candles) - 45):  # Need at least 45 candles ahead for exit
            candle = candles[i]
            ribbon_state = candle.get('ribbon_state_close', '')

            # Check previous candle for flip
            if i == 0:
                continue

            prev_ribbon = candles[i-1].get('ribbon_state_close', '')

            # Detect ribbon flip
            direction = None
            if ribbon_state == 'all_green' and prev_ribbon != 'all_green':
                direction = 'LONG'
            elif ribbon_state == 'all_red' and prev_ribbon != 'all_red':
                direction = 'SHORT'

            if direction:
                # Look ahead to find BEST exit within next 45 candles
                entry_price = candle['price_close']
                best_exit = self._find_best_exit(candles, i, direction, entry_price)

                if best_exit:
                    optimal_trades.append({
                        'entry_index': i,
                        'entry_time': candle['timestamp'],
                        'entry_price': entry_price,
                        'direction': direction,
                        'entry_ribbon': ribbon_state,
                        'entry_ema_signature': self._get_ema_signature(candle),
                        'entry_intensity': self._get_intensity_signature(candle),
                        'exit_index': best_exit['exit_index'],
                        'exit_time': best_exit['exit_time'],
                        'exit_price': best_exit['exit_price'],
                        'hold_candles': best_exit['hold_candles'],
                        'pnl': best_exit['pnl'],
                        'pnl_pct': best_exit['pnl_pct'],
                        'exit_reason': best_exit['exit_reason']
                    })

        # Filter to only profitable optimal trades
        profitable_optimal = [t for t in optimal_trades if t['pnl'] > 0]

        print(f"   Found {len(optimal_trades)} total setups")
        print(f"   {len(profitable_optimal)} would have been profitable ({len(profitable_optimal)/len(optimal_trades)*100:.1f}% hit rate)")

        return profitable_optimal

    def _find_best_exit(self, candles: List[Dict], entry_index: int,
                        direction: str, entry_price: float) -> Dict:
        """Find the best exit point with perfect hindsight"""

        max_pnl = -999999
        best_exit = None

        # Look ahead up to 45 candles
        for j in range(entry_index + 1, min(entry_index + 46, len(candles))):
            exit_candle = candles[j]
            exit_price = exit_candle['price_close']

            # Calculate P&L
            if direction == 'LONG':
                pnl = exit_price - entry_price
            else:
                pnl = entry_price - exit_price

            pnl_pct = (pnl / entry_price) * 100

            # Track best exit
            if pnl > max_pnl:
                max_pnl = pnl
                best_exit = {
                    'exit_index': j,
                    'exit_time': exit_candle['timestamp'],
                    'exit_price': exit_price,
                    'hold_candles': j - entry_index,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'exit_reason': 'OPTIMAL'
                }

        return best_exit if best_exit and best_exit['pnl'] > 0 else None

    def _get_ema_signature(self, candle: Dict) -> str:
        """Get EMA color signature"""
        green, red, yellow, gray = 0, 0, 0, 0

        for i in range(5, 150, 5):
            color_key = f'MMA{i}_color'
            if color_key in candle:
                color = candle[color_key]
                if color == 'green':
                    green += 1
                elif color == 'red':
                    red += 1
                elif color == 'yellow':
                    yellow += 1
                elif color == 'gray':
                    gray += 1

        return f"G{green}_R{red}_Y{yellow}_Gr{gray}"

    def _get_intensity_signature(self, candle: Dict) -> str:
        """Get EMA intensity signature"""
        light_green, dark_green, light_red, dark_red = 0, 0, 0, 0

        for i in range(5, 150, 5):
            color_key = f'MMA{i}_color'
            intensity_key = f'MMA{i}_intensity'

            if color_key in candle and intensity_key in candle:
                color = candle[color_key]
                intensity = candle[intensity_key]

                if color == 'green':
                    if intensity == 'light':
                        light_green += 1
                    elif intensity == 'dark':
                        dark_green += 1
                elif color == 'red':
                    if intensity == 'light':
                        light_red += 1
                    elif intensity == 'dark':
                        dark_red += 1

        return f"LG{light_green}_DG{dark_green}_LR{light_red}_DR{dark_red}"

    def compare_trades(self, optimal: List[Dict], actual: List[Dict]) -> Dict:
        """
        Compare optimal vs actual trades to find what you're missing
        """
        print(f"\n📊 COMPARING OPTIMAL VS ACTUAL TRADES...")

        # Calculate stats
        optimal_pnl = sum(t['pnl'] for t in optimal)
        actual_pnl = sum(t['pnl'] for t in actual)

        optimal_win_rate = len([t for t in optimal if t['pnl'] > 0]) / len(optimal) * 100 if optimal else 0
        actual_win_rate = len([t for t in actual if t['profitable']]) / len(actual) * 100 if actual else 0

        # Analyze EMA patterns in optimal trades
        optimal_patterns = defaultdict(lambda: {'count': 0, 'total_pnl': 0})

        for trade in optimal:
            sig = trade['entry_intensity']
            optimal_patterns[sig]['count'] += 1
            optimal_patterns[sig]['total_pnl'] += trade['pnl']

        optimal_pattern_list = []
        for sig, stats in optimal_patterns.items():
            if stats['count'] >= 2:
                optimal_pattern_list.append({
                    'signature': sig,
                    'count': stats['count'],
                    'avg_pnl': stats['total_pnl'] / stats['count'],
                    'total_pnl': stats['total_pnl']
                })

        optimal_pattern_list.sort(key=lambda x: x['avg_pnl'], reverse=True)

        # Find what actual trades missed
        missed_opportunities = len(optimal) - len(actual)
        missed_pnl = optimal_pnl - actual_pnl

        return {
            'optimal_trades': len(optimal),
            'actual_trades': len(actual),
            'optimal_pnl': optimal_pnl,
            'actual_pnl': actual_pnl,
            'optimal_win_rate': optimal_win_rate,
            'actual_win_rate': actual_win_rate,
            'missed_opportunities': missed_opportunities,
            'missed_pnl': missed_pnl,
            'optimal_patterns': optimal_pattern_list,
            'avg_optimal_pnl': optimal_pnl / len(optimal) if optimal else 0,
            'avg_actual_pnl': actual_pnl / len(actual) if actual else 0
        }

    def generate_report(self, comparison: Dict, optimal_trades: List[Dict]):
        """Generate comprehensive comparison report"""

        print("\n" + "="*100)
        print("OPTIMAL VS ACTUAL TRADE ANALYSIS")
        print("="*100)

        print(f"\n📊 PERFORMANCE COMPARISON:")
        print(f"   Optimal Trades (Perfect Hindsight): {comparison['optimal_trades']}")
        print(f"   Actual Trades (What You Did): {comparison['actual_trades']}")
        print(f"   Missed Opportunities: {comparison['missed_opportunities']}")

        print(f"\n💰 P&L COMPARISON:")
        print(f"   Optimal P&L: ${comparison['optimal_pnl']:.2f} ({comparison['optimal_win_rate']:.1f}% win rate)")
        print(f"   Actual P&L: ${comparison['actual_pnl']:.2f} ({comparison['actual_win_rate']:.1f}% win rate)")
        print(f"   Missed P&L: ${comparison['missed_pnl']:.2f}")

        print(f"\n📈 PER-TRADE COMPARISON:")
        print(f"   Avg Optimal Trade: ${comparison['avg_optimal_pnl']:.2f}")
        print(f"   Avg Actual Trade: ${comparison['avg_actual_pnl']:.2f}")
        print(f"   Gap: ${comparison['avg_optimal_pnl'] - comparison['avg_actual_pnl']:.2f} per trade")

        print(f"\n🎨 TOP EMA PATTERNS IN OPTIMAL TRADES:")
        print("-"*100)
        print(f"{'Signature':<35} {'Count':<10} {'Avg P&L':<15} {'Total P&L':<15}")
        print("-"*100)

        for pattern in comparison['optimal_patterns'][:10]:
            sig = pattern['signature']
            count = pattern['count']
            avg_pnl = pattern['avg_pnl']
            total_pnl = pattern['total_pnl']

            emoji = "🟢" if avg_pnl >= 5 else "🟡" if avg_pnl >= 2 else "⚪"
            print(f"{emoji} {sig:<33} {count:<10} ${avg_pnl:>8.2f}       ${total_pnl:>8.2f}")

        print(f"\n💡 KEY INSIGHTS:")

        if comparison['missed_opportunities'] > 0:
            print(f"   ⚠️  You missed {comparison['missed_opportunities']} profitable opportunities")
            print(f"   💸 That's ${comparison['missed_pnl']:.2f} in potential profit!")

        if comparison['optimal_win_rate'] > comparison['actual_win_rate']:
            gap = comparison['optimal_win_rate'] - comparison['actual_win_rate']
            print(f"   📊 Optimal win rate is {gap:.1f}% higher than your actual")

        print(f"\n🎯 WHAT TO FOCUS ON:")
        if comparison['optimal_patterns']:
            top_pattern = comparison['optimal_patterns'][0]
            print(f"   ✅ Pattern: {top_pattern['signature']}")
            print(f"   ✅ Average P&L: ${top_pattern['avg_pnl']:.2f}")
            print(f"   ✅ Appeared {top_pattern['count']} times in optimal trades")
            print(f"   ✅ ACTION: Look for this pattern in your entries!")

        print("\n" + "="*100)

    def save_analysis(self, comparison: Dict, optimal_trades: List[Dict],
                      output_file='optimal_vs_actual_analysis.json'):
        """Save analysis to JSON"""
        output = {
            'timestamp': datetime.now().isoformat(),
            'comparison': comparison,
            'optimal_trades': optimal_trades[:20],  # Save top 20
            'recommendations': self._generate_recommendations(comparison)
        }

        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        print(f"\n💾 Analysis saved to {output_file}")

    def _generate_recommendations(self, comparison: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Win rate recommendation
        if comparison['actual_win_rate'] < comparison['optimal_win_rate'] - 10:
            recommendations.append(
                f"IMPROVE ENTRY SELECTION: Optimal trades have {comparison['optimal_win_rate']:.0f}% win rate vs your {comparison['actual_win_rate']:.0f}%. "
                f"Focus on the top EMA patterns shown above."
            )

        # Missed opportunities
        if comparison['missed_opportunities'] > comparison['actual_trades']:
            recommendations.append(
                f"INCREASE TRADE FREQUENCY: You missed {comparison['missed_opportunities']} profitable setups. "
                f"Consider taking more trades that match the optimal patterns."
            )

        # Pattern focus
        if comparison['optimal_patterns']:
            top = comparison['optimal_patterns'][0]
            recommendations.append(
                f"FOCUS ON PATTERN: {top['signature']} averaged ${top['avg_pnl']:.2f} per trade. "
                f"This should be your PRIMARY setup to look for."
            )

        # Per-trade improvement
        gap = comparison['avg_optimal_pnl'] - comparison['avg_actual_pnl']
        if gap > 2:
            recommendations.append(
                f"IMPROVE EXIT TIMING: Each optimal trade made ${gap:.2f} more than your actual trades on average. "
                f"Consider holding winners longer or exiting losers faster."
            )

        return recommendations


def main():
    """Run optimal vs actual analysis"""
    print("🔬 Optimal vs Actual Trade Analyzer\n")

    analyzer = OptimalVsActualAnalyzer()

    # Load data
    candles = analyzer.load_candlestick_data()
    actual_trades = analyzer.load_actual_trades()

    if not candles:
        print("❌ No candlestick data available")
        return

    # Find optimal trades
    optimal_trades = analyzer.find_optimal_trades(candles)

    if not optimal_trades:
        print("❌ Could not find optimal trades")
        return

    # Compare
    comparison = analyzer.compare_trades(optimal_trades, actual_trades)

    # Generate report
    analyzer.generate_report(comparison, optimal_trades)

    # Save
    analyzer.save_analysis(comparison, optimal_trades)

    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
