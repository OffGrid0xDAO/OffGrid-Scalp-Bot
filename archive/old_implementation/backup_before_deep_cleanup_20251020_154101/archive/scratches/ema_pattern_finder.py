#!/usr/bin/env python3
"""
EMA Pattern Finder - Find the BEST trade setups from candlestick data
Analyzes EMA color patterns, ribbon states, and finds most profitable combinations
"""

import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict, Counter


class EMAPatternFinder:
    """
    Analyzes candlestick data to find the most profitable EMA patterns
    """

    def __init__(self, csv_5min='candlesticks_5min.csv', csv_15min='candlesticks_15min.csv'):
        self.csv_5min = csv_5min
        self.csv_15min = csv_15min
        self.patterns = []
        self.profitable_patterns = []

    def load_candlestick_data(self, csv_path: str) -> List[Dict]:
        """Load candlestick data from CSV"""
        candles = []
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert numeric fields
                    row['price_open'] = float(row['price_open'])
                    row['price_high'] = float(row['price_high'])
                    row['price_low'] = float(row['price_low'])
                    row['price_close'] = float(row['price_close'])
                    candles.append(row)
            print(f"✅ Loaded {len(candles)} candles from {csv_path}")
            return candles
        except Exception as e:
            print(f"❌ Error loading {csv_path}: {e}")
            return []

    def get_ema_color_signature(self, candle: Dict) -> str:
        """
        Get the EMA color signature for a candle
        Format: "G24_R0_Y2" = 24 green, 0 red, 2 yellow
        """
        green_count = 0
        red_count = 0
        yellow_count = 0
        gray_count = 0

        # Count each MMA color
        for i in range(5, 150, 5):  # MMA5 to MMA145
            ema_key = f'MMA{i}_color'
            if ema_key in candle:
                color = candle[ema_key]
                if color == 'green':
                    green_count += 1
                elif color == 'red':
                    red_count += 1
                elif color == 'yellow':
                    yellow_count += 1
                elif color == 'gray':
                    gray_count += 1

        return f"G{green_count}_R{red_count}_Y{yellow_count}_Gr{gray_count}"

    def get_ema_intensity_signature(self, candle: Dict) -> str:
        """
        Get EMA intensity signature
        Format: "LG10_DG5_LR3_DR2" = 10 light green, 5 dark green, etc.
        """
        light_green = 0
        dark_green = 0
        light_red = 0
        dark_red = 0

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

    def simulate_trades(self, candles: List[Dict], timeframe: str = '5min') -> List[Dict]:
        """
        Simulate all possible trades from the candlestick data
        Entry: When ribbon flips to all_green or all_red
        Exit: Profit target, stop loss, or ribbon reversal
        """
        trades = []
        in_position = False
        position = None

        print(f"\n🔍 Simulating trades on {timeframe} data...")

        for i, candle in enumerate(candles):
            ribbon_state = candle.get('ribbon_state_close', '')

            # Entry logic
            if not in_position:
                # Look for ribbon flip
                if i > 0:
                    prev_ribbon = candles[i-1].get('ribbon_state_close', '')

                    # LONG entry: Ribbon flips to all_green
                    if ribbon_state == 'all_green' and prev_ribbon != 'all_green':
                        position = {
                            'entry_index': i,
                            'entry_time': candle['timestamp'],
                            'entry_price': candle['price_close'],
                            'direction': 'LONG',
                            'entry_ribbon': ribbon_state,
                            'entry_ema_signature': self.get_ema_color_signature(candle),
                            'entry_intensity': self.get_ema_intensity_signature(candle),
                            'max_profit': 0,
                            'max_loss': 0
                        }
                        in_position = True

                    # SHORT entry: Ribbon flips to all_red
                    elif ribbon_state == 'all_red' and prev_ribbon != 'all_red':
                        position = {
                            'entry_index': i,
                            'entry_time': candle['timestamp'],
                            'entry_price': candle['price_close'],
                            'direction': 'SHORT',
                            'entry_ribbon': ribbon_state,
                            'entry_ema_signature': self.get_ema_color_signature(candle),
                            'entry_intensity': self.get_ema_intensity_signature(candle),
                            'max_profit': 0,
                            'max_loss': 0
                        }
                        in_position = True

            # Exit logic
            if in_position and position:
                current_price = candle['price_close']

                # Calculate P&L
                if position['direction'] == 'LONG':
                    pnl = current_price - position['entry_price']
                else:  # SHORT
                    pnl = position['entry_price'] - current_price

                pnl_pct = (pnl / position['entry_price']) * 100

                # Track max profit/loss
                position['max_profit'] = max(position['max_profit'], pnl)
                position['max_loss'] = min(position['max_loss'], pnl)

                # Exit conditions
                should_exit = False
                exit_reason = None

                # Profit target: 0.3%
                if pnl_pct >= 0.3:
                    should_exit = True
                    exit_reason = 'PROFIT_TARGET'

                # Stop loss: -0.15%
                elif pnl_pct <= -0.15:
                    should_exit = True
                    exit_reason = 'STOP_LOSS'

                # Max hold: 45 candles (45 min for 1min, 225 min for 5min)
                elif i - position['entry_index'] >= 45:
                    should_exit = True
                    exit_reason = 'MAX_HOLD'

                # Ribbon reversal
                elif (position['direction'] == 'LONG' and ribbon_state == 'all_red') or \
                     (position['direction'] == 'SHORT' and ribbon_state == 'all_green'):
                    should_exit = True
                    exit_reason = 'RIBBON_REVERSAL'

                if should_exit:
                    position['exit_index'] = i
                    position['exit_time'] = candle['timestamp']
                    position['exit_price'] = current_price
                    position['exit_ribbon'] = ribbon_state
                    position['exit_ema_signature'] = self.get_ema_color_signature(candle)
                    position['exit_reason'] = exit_reason
                    position['hold_candles'] = i - position['entry_index']
                    position['pnl'] = pnl
                    position['pnl_pct'] = pnl_pct
                    position['profitable'] = pnl > 0

                    trades.append(position)
                    in_position = False
                    position = None

        print(f"   Found {len(trades)} completed trades")
        profitable = len([t for t in trades if t['profitable']])
        print(f"   Profitable: {profitable} ({profitable/len(trades)*100:.1f}% win rate)")

        return trades

    def analyze_ema_patterns(self, trades: List[Dict]) -> Dict:
        """
        Analyze which EMA color patterns lead to most profitable trades
        """
        profitable = [t for t in trades if t['profitable']]
        losing = [t for t in trades if not t['profitable']]

        # Analyze entry patterns
        entry_signatures = defaultdict(lambda: {'total': 0, 'profitable': 0, 'total_pnl': 0, 'trades': []})

        for trade in trades:
            sig = trade['entry_ema_signature']
            entry_signatures[sig]['total'] += 1
            entry_signatures[sig]['total_pnl'] += trade['pnl']
            entry_signatures[sig]['trades'].append(trade)
            if trade['profitable']:
                entry_signatures[sig]['profitable'] += 1

        # Calculate win rates
        pattern_stats = []
        for sig, stats in entry_signatures.items():
            if stats['total'] >= 3:  # Minimum 3 trades to be significant
                win_rate = (stats['profitable'] / stats['total']) * 100
                avg_pnl = stats['total_pnl'] / stats['total']

                pattern_stats.append({
                    'signature': sig,
                    'total_trades': stats['total'],
                    'profitable': stats['profitable'],
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'total_pnl': stats['total_pnl'],
                    'example_trades': stats['trades'][:3]  # First 3 examples
                })

        # Sort by win rate
        pattern_stats.sort(key=lambda x: x['win_rate'], reverse=True)

        # Analyze intensity patterns
        intensity_patterns = defaultdict(lambda: {'total': 0, 'profitable': 0, 'total_pnl': 0})

        for trade in trades:
            intensity = trade['entry_intensity']
            intensity_patterns[intensity]['total'] += 1
            intensity_patterns[intensity]['total_pnl'] += trade['pnl']
            if trade['profitable']:
                intensity_patterns[intensity]['profitable'] += 1

        intensity_stats = []
        for sig, stats in intensity_patterns.items():
            if stats['total'] >= 3:
                win_rate = (stats['profitable'] / stats['total']) * 100
                avg_pnl = stats['total_pnl'] / stats['total']

                intensity_stats.append({
                    'signature': sig,
                    'total_trades': stats['total'],
                    'profitable': stats['profitable'],
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl
                })

        intensity_stats.sort(key=lambda x: x['win_rate'], reverse=True)

        return {
            'total_trades': len(trades),
            'profitable_trades': len(profitable),
            'win_rate': len(profitable) / len(trades) * 100 if trades else 0,
            'ema_color_patterns': pattern_stats,
            'ema_intensity_patterns': intensity_stats
        }

    def find_best_patterns(self, analysis: Dict) -> List[Dict]:
        """Find the best EMA patterns (>50% win rate)"""
        best_patterns = []

        for pattern in analysis['ema_color_patterns']:
            if pattern['win_rate'] >= 50 and pattern['total_trades'] >= 5:
                best_patterns.append({
                    'type': 'EMA_COLOR',
                    'signature': pattern['signature'],
                    'win_rate': pattern['win_rate'],
                    'total_trades': pattern['total_trades'],
                    'avg_pnl': pattern['avg_pnl']
                })

        for pattern in analysis['ema_intensity_patterns']:
            if pattern['win_rate'] >= 50 and pattern['total_trades'] >= 5:
                best_patterns.append({
                    'type': 'EMA_INTENSITY',
                    'signature': pattern['signature'],
                    'win_rate': pattern['win_rate'],
                    'total_trades': pattern['total_trades'],
                    'avg_pnl': pattern['avg_pnl']
                })

        best_patterns.sort(key=lambda x: x['win_rate'], reverse=True)
        return best_patterns

    def generate_report(self, trades: List[Dict], analysis: Dict):
        """Generate comprehensive pattern analysis report"""
        print("\n" + "="*100)
        print("EMA PATTERN ANALYSIS - BEST TRADE SETUPS")
        print("="*100)

        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   Total Trades Simulated: {analysis['total_trades']}")
        print(f"   Profitable: {analysis['profitable_trades']} ({analysis['win_rate']:.1f}% win rate)")

        print(f"\n🎯 TOP 10 MOST PROFITABLE EMA COLOR PATTERNS:")
        print("-"*100)
        print(f"{'Signature':<25} {'Trades':<10} {'Win Rate':<12} {'Avg P&L':<15} {'Total P&L':<15}")
        print("-"*100)

        for i, pattern in enumerate(analysis['ema_color_patterns'][:10], 1):
            sig = pattern['signature']
            total = pattern['total_trades']
            win_rate = pattern['win_rate']
            avg_pnl = pattern['avg_pnl']
            total_pnl = pattern['total_pnl']

            emoji = "🟢" if win_rate >= 60 else "🟡" if win_rate >= 50 else "🔴"
            print(f"{emoji} {sig:<23} {total:<10} {win_rate:>6.1f}%      ${avg_pnl:>8.2f}       ${total_pnl:>8.2f}")

        print(f"\n💪 TOP 10 EMA INTENSITY PATTERNS:")
        print("-"*100)
        print(f"{'Signature':<30} {'Trades':<10} {'Win Rate':<12} {'Avg P&L':<15}")
        print("-"*100)

        for i, pattern in enumerate(analysis['ema_intensity_patterns'][:10], 1):
            sig = pattern['signature']
            total = pattern['total_trades']
            win_rate = pattern['win_rate']
            avg_pnl = pattern['avg_pnl']

            emoji = "🟢" if win_rate >= 60 else "🟡" if win_rate >= 50 else "🔴"
            print(f"{emoji} {sig:<28} {total:<10} {win_rate:>6.1f}%      ${avg_pnl:>8.2f}")

        # Find best patterns
        best_patterns = self.find_best_patterns(analysis)

        if best_patterns:
            print(f"\n✅ WINNING PATTERNS (>50% Win Rate, >5 Trades):")
            print("-"*100)
            for pattern in best_patterns:
                print(f"   🏆 {pattern['type']}: {pattern['signature']}")
                print(f"      Win Rate: {pattern['win_rate']:.1f}% | Trades: {pattern['total_trades']} | Avg P&L: ${pattern['avg_pnl']:.2f}")
        else:
            print(f"\n⚠️  No patterns with >50% win rate and >5 trades found")

        print("\n" + "="*100)

    def save_analysis(self, analysis: Dict, output_file='ema_pattern_analysis.json'):
        """Save analysis to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\n💾 Analysis saved to {output_file}")


def main():
    """Run EMA pattern analysis"""
    print("🔬 EMA Pattern Finder - Analyzing Candlestick Data\n")

    finder = EMAPatternFinder()

    # Load data
    candles_5min = finder.load_candlestick_data('candlesticks_5min.csv')

    if not candles_5min:
        print("❌ No candlestick data found!")
        return

    # Simulate trades
    trades = finder.simulate_trades(candles_5min, '5min')

    if not trades:
        print("❌ No trades generated!")
        return

    # Analyze patterns
    analysis = finder.analyze_ema_patterns(trades)

    # Generate report
    finder.generate_report(trades, analysis)

    # Save results
    finder.save_analysis(analysis)

    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
