#!/usr/bin/env python3
"""
EMA Ribbon Strategy Backtester

Analyzes historical EMA data to:
1. Find all entry opportunities (ribbon flips to ALL_GREEN/ALL_RED)
2. Simulate trades with multiple hold durations
3. Calculate P&L for each trade
4. Identify winning vs losing patterns
5. Generate training data for Claude

Usage:
    python3 backtest_ema_strategy.py
"""

import csv
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple
import statistics


class EMABacktester:
    """
    Backtest EMA ribbon strategy on historical data
    """

    def __init__(self, csv_5min_path: str, csv_15min_path: str):
        self.csv_5min = csv_5min_path
        self.csv_15min = csv_15min_path
        self.data_5min = []
        self.data_15min = []
        self.opportunities = []
        self.trades = []

    def load_data(self):
        """Load historical EMA data from CSV files"""
        print("Loading historical EMA data...")

        # Load 5-minute data
        with open(self.csv_5min, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self.data_5min.append({
                        'timestamp': datetime.fromisoformat(row['timestamp']),
                        'price': float(row.get('price', 0)),
                        'state': row.get('ribbon_state', ''),
                        'raw_row': row  # Keep all data
                    })
                except Exception as e:
                    continue

        # Load 15-minute data
        with open(self.csv_15min, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self.data_15min.append({
                        'timestamp': datetime.fromisoformat(row['timestamp']),
                        'price': float(row.get('price', 0)),
                        'state': row.get('ribbon_state', ''),
                        'raw_row': row
                    })
                except Exception as e:
                    continue

        print(f"✅ Loaded {len(self.data_5min)} data points from 5min")
        print(f"✅ Loaded {len(self.data_15min)} data points from 15min")

        # Calculate time range
        if self.data_5min:
            start_time = self.data_5min[0]['timestamp']
            end_time = self.data_5min[-1]['timestamp']
            duration = end_time - start_time
            print(f"📊 Data range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"📊 Duration: {duration.total_seconds() / 3600:.1f} hours")

    def calculate_range(self, data: List[Dict], index: int, minutes: int) -> float:
        """
        Calculate price range % for given time window

        Args:
            data: List of data points
            index: Current index
            minutes: Time window in minutes

        Returns:
            Range percentage
        """
        # Calculate how many data points = minutes (10sec intervals)
        points_needed = minutes * 6

        start_idx = max(0, index - points_needed)
        window = data[start_idx:index + 1]

        if len(window) < 2:
            return 0

        prices = [d['price'] for d in window if d['price'] > 0]
        if not prices:
            return 0

        high = max(prices)
        low = min(prices)

        if low == 0:
            return 0

        return ((high - low) / low) * 100

    def count_ribbon_flips(self, data: List[Dict], index: int, minutes: int) -> int:
        """
        Count how many times ribbon flipped between green/red in time window
        """
        points_needed = minutes * 6
        start_idx = max(0, index - points_needed)
        window = data[start_idx:index + 1]

        flips = 0
        last_direction = None

        for point in window:
            state = point['state'].lower()

            # Determine direction
            if 'green' in state:
                direction = 'green'
            elif 'red' in state:
                direction = 'red'
            else:
                continue

            # Count flip if direction changed
            if last_direction and last_direction != direction:
                flips += 1

            last_direction = direction

        return flips

    def _calculate_quality_score(self, direction, range_30min, range_15min,
                                  ribbon_flips, price_location_pct,
                                  state_5min, state_15min):
        """
        Calculate quality score for entry opportunity (0-100)
        Higher score = better setup

        Scoring criteria:
        - Trending market (30min range)
        - Stable ribbon (low flips)
        - Good price location
        - Strong alignment (both timeframes)
        """
        score = 0

        # 1. TRENDING MARKET (0-35 points)
        if range_30min >= 0.8:
            score += 35  # Big move - best!
        elif range_30min >= 0.6:
            score += 30  # Strong trending
        elif range_30min >= 0.5:
            score += 20  # Trending
        elif range_30min >= 0.4:
            score += 10  # Weak trending
        else:
            score += 0   # Ranging - skip

        # 2. RIBBON STABILITY (0-25 points)
        if ribbon_flips == 0:
            score += 25  # Perfect stability
        elif ribbon_flips == 1:
            score += 20  # Excellent
        elif ribbon_flips == 2:
            score += 10  # Good
        elif ribbon_flips == 3:
            score += 5   # Acceptable
        else:
            score += 0   # Too choppy

        # 3. PRICE LOCATION (0-25 points)
        if direction == 'LONG':
            # Want LONG entries in lower part of range
            if price_location_pct < 30:
                score += 25  # Perfect - at bottom
            elif price_location_pct < 40:
                score += 20  # Great
            elif price_location_pct < 50:
                score += 15  # Good
            elif price_location_pct < 60:
                score += 10  # Acceptable
            else:
                score += 0   # Too high - chasing
        else:  # SHORT
            # Want SHORT entries in upper part of range
            if price_location_pct > 70:
                score += 25  # Perfect - at top
            elif price_location_pct > 60:
                score += 20  # Great
            elif price_location_pct > 50:
                score += 15  # Good
            elif price_location_pct > 40:
                score += 10  # Acceptable
            else:
                score += 0   # Too low - chasing

        # 4. TIMEFRAME ALIGNMENT (0-15 points)
        state_5min_lower = state_5min.lower()
        state_15min_lower = state_15min.lower() if state_15min else ''

        # Both timeframes aligned?
        if direction == 'LONG':
            if 'all_green' in state_5min_lower and 'all_green' in state_15min_lower:
                score += 15  # Perfect alignment
            elif 'all_green' in state_5min_lower:
                score += 10  # 5min good
            else:
                score += 5   # Weak
        else:  # SHORT
            if 'all_red' in state_5min_lower and 'all_red' in state_15min_lower:
                score += 15  # Perfect alignment
            elif 'all_red' in state_5min_lower:
                score += 10  # 5min good
            else:
                score += 5   # Weak

        return score

    def detect_entry_opportunities(self):
        """
        Scan historical data for all entry opportunities
        (ribbon flips to ALL_GREEN or ALL_RED)
        """
        print("\n🔍 Detecting entry opportunities...")

        last_valid_state_5min = None

        for i in range(len(self.data_5min)):
            current = self.data_5min[i]
            state_5min = current['state']

            # Skip if no state or price
            if not state_5min or current['price'] == 0:
                continue

            # Skip unknown/mixed states for entry detection
            state_lower = state_5min.lower()
            if 'unknown' in state_lower or ('mixed' in state_lower and 'all' not in state_lower):
                continue

            # Detect ribbon flip to ALL_GREEN or ALL_RED
            direction = None
            is_entry_signal = False

            if 'all_green' in state_lower:
                # Check if this is a NEW flip (wasn't all_green before)
                if last_valid_state_5min is None or 'all_green' not in last_valid_state_5min.lower():
                    direction = 'LONG'
                    is_entry_signal = True
            elif 'all_red' in state_lower:
                # Check if this is a NEW flip (wasn't all_red before)
                if last_valid_state_5min is None or 'all_red' not in last_valid_state_5min.lower():
                    direction = 'SHORT'
                    is_entry_signal = True

            if is_entry_signal:
                # Find matching 15min data
                state_15min = self.get_15min_state_at_time(current['timestamp'])

                # Calculate entry conditions
                range_30min = self.calculate_range(self.data_5min, i, 30)
                range_15min = self.calculate_range(self.data_5min, i, 15)
                range_2h = self.calculate_range(self.data_5min, i, 120)

                ribbon_flips_30min = self.count_ribbon_flips(self.data_5min, i, 30)

                # Calculate price location in 2h range
                if range_2h > 0:
                    prices_2h = [d['price'] for d in self.data_5min[max(0, i-720):i+1] if d['price'] > 0]
                    if prices_2h:
                        high_2h = max(prices_2h)
                        low_2h = min(prices_2h)
                        if high_2h != low_2h:
                            price_location_pct = ((current['price'] - low_2h) / (high_2h - low_2h)) * 100
                        else:
                            price_location_pct = 50
                    else:
                        price_location_pct = 50
                else:
                    price_location_pct = 50

                # Calculate quality score (0-100)
                quality_score = self._calculate_quality_score(
                    direction, range_30min, range_15min, ribbon_flips_30min,
                    price_location_pct, state_5min, state_15min
                )

                opportunity = {
                    'index': i,
                    'timestamp': current['timestamp'],
                    'direction': direction,
                    'entry_price': current['price'],
                    'state_5min': state_5min,
                    'state_15min': state_15min,
                    'range_30min': range_30min,
                    'range_15min': range_15min,
                    'range_2h': range_2h,
                    'price_location_pct': price_location_pct,
                    'ribbon_flips_30min': ribbon_flips_30min,
                    'quality_score': quality_score
                }

                # FILTER: Only accept high-quality setups (score ≥ 60)
                if quality_score >= 60:
                    self.opportunities.append(opportunity)

            # Update last valid state (only if it's all_green or all_red)
            if 'all_green' in state_lower or 'all_red' in state_lower:
                last_valid_state_5min = state_5min

        print(f"✅ Found {len(self.opportunities)} entry opportunities")

        # Count by direction
        long_count = len([o for o in self.opportunities if o['direction'] == 'LONG'])
        short_count = len([o for o in self.opportunities if o['direction'] == 'SHORT'])
        print(f"   📈 LONG opportunities: {long_count}")
        print(f"   📉 SHORT opportunities: {short_count}")

    def get_15min_state_at_time(self, timestamp: datetime) -> str:
        """Get 15min state at given time"""
        # Find closest 15min data point
        for data in self.data_15min:
            if abs((data['timestamp'] - timestamp).total_seconds()) < 30:
                return data['state']
        return 'unknown'

    def simulate_trade(self, opportunity: Dict, hold_minutes: int) -> Dict:
        """
        Simulate a trade from entry opportunity

        Args:
            opportunity: Entry opportunity data
            hold_minutes: How long to hold position

        Returns:
            Trade result with P&L
        """
        entry_index = opportunity['index']
        entry_price = opportunity['entry_price']
        direction = opportunity['direction']

        # Calculate exit index (6 points per minute for 10sec intervals)
        points_to_hold = hold_minutes * 6
        exit_index = entry_index + points_to_hold

        # Check if we have data for this exit
        if exit_index >= len(self.data_5min):
            return None

        exit_data = self.data_5min[exit_index]
        exit_price = exit_data['price']

        if exit_price == 0:
            return None

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        pnl_dollars = (pnl_pct / 100) * entry_price  # Approximate for 1 unit

        # Check what happened during the hold
        ribbon_stayed_aligned = self.check_ribbon_stability(
            entry_index, exit_index, direction
        )

        return {
            'opportunity': opportunity,
            'direction': direction,
            'entry_price': entry_price,
            'entry_time': opportunity['timestamp'],
            'hold_minutes': hold_minutes,
            'exit_price': exit_price,
            'exit_time': exit_data['timestamp'],
            'pnl_pct': pnl_pct,
            'pnl_dollars': pnl_dollars,
            'ribbon_stayed_aligned': ribbon_stayed_aligned,
            'winner': pnl_pct > 0.3,  # >0.3% = winner
            'entry_conditions': {
                'range_30min': opportunity['range_30min'],
                'range_15min': opportunity['range_15min'],
                'price_location_pct': opportunity['price_location_pct'],
                'ribbon_flips_30min': opportunity['ribbon_flips_30min'],
                'state_5min': opportunity['state_5min'],
                'state_15min': opportunity['state_15min'],
            }
        }

    def check_ribbon_stability(self, start_idx: int, end_idx: int, direction: str) -> bool:
        """
        Check if ribbon stayed aligned during hold period
        """
        for i in range(start_idx, min(end_idx + 1, len(self.data_5min))):
            state = self.data_5min[i]['state'].lower()

            if direction == 'LONG':
                # For LONG, ribbon should stay green (all_green or mixed_green acceptable)
                if 'red' in state and 'all_red' in state:
                    return False  # Flipped to bearish
            else:  # SHORT
                # For SHORT, ribbon should stay red
                if 'green' in state and 'all_green' in state:
                    return False  # Flipped to bullish

        return True

    def run_backtest(self, hold_durations=[5, 10, 15, 20, 30]):
        """
        Run backtest on all opportunities with multiple hold durations
        """
        print(f"\n📊 Simulating trades with hold times: {hold_durations} minutes")

        total_sims = len(self.opportunities) * len(hold_durations)
        print(f"   Total simulations: {total_sims}")

        for opportunity in self.opportunities:
            for hold_minutes in hold_durations:
                trade = self.simulate_trade(opportunity, hold_minutes)
                if trade:
                    self.trades.append(trade)

        print(f"✅ Completed {len(self.trades)} trade simulations")

    def generate_report(self):
        """
        Generate comprehensive performance report
        """
        if not self.trades:
            print("❌ No trades to analyze")
            return

        print("\n" + "="*80)
        print("BACKTEST PERFORMANCE REPORT")
        print("="*80)

        # Overall stats
        winners = [t for t in self.trades if t['winner']]
        losers = [t for t in self.trades if not t['winner']]

        win_rate = (len(winners) / len(self.trades)) * 100 if self.trades else 0
        avg_winner_pnl = statistics.mean([t['pnl_pct'] for t in winners]) if winners else 0
        avg_loser_pnl = statistics.mean([t['pnl_pct'] for t in losers]) if losers else 0

        total_pnl = sum([t['pnl_pct'] for t in self.trades])

        # Quality score analysis
        avg_quality_winners = statistics.mean([t['opportunity']['quality_score'] for t in winners]) if winners else 0
        avg_quality_losers = statistics.mean([t['opportunity']['quality_score'] for t in losers]) if losers else 0

        print(f"\n📊 OVERALL STATISTICS (HIGH-QUALITY SETUPS ONLY):")
        print(f"   Total Opportunities Filtered: {len(self.opportunities)}")
        print(f"   Total Trades: {len(self.trades)}")
        print(f"   Winners: {len(winners)} ({win_rate:.1f}%)")
        print(f"   Losers: {len(losers)} ({100-win_rate:.1f}%)")
        print(f"   Avg Winner: {avg_winner_pnl:+.3f}%")
        print(f"   Avg Loser: {avg_loser_pnl:+.3f}%")
        print(f"   Total P&L: {total_pnl:+.2f}%")
        print(f"\n🎯 QUALITY SCORES:")
        print(f"   Winners avg quality: {avg_quality_winners:.1f}/100")
        print(f"   Losers avg quality: {avg_quality_losers:.1f}/100")

        # Stats by hold duration
        print(f"\n⏱️  PERFORMANCE BY HOLD DURATION:")
        for hold_min in sorted(set([t['hold_minutes'] for t in self.trades])):
            trades_for_duration = [t for t in self.trades if t['hold_minutes'] == hold_min]
            winners_for_duration = [t for t in trades_for_duration if t['winner']]

            wr = (len(winners_for_duration) / len(trades_for_duration) * 100) if trades_for_duration else 0
            avg_pnl = statistics.mean([t['pnl_pct'] for t in trades_for_duration])

            print(f"   {hold_min:2d} minutes: {wr:5.1f}% win rate | Avg P&L: {avg_pnl:+.3f}%")

        # Stats by direction
        print(f"\n📈📉 PERFORMANCE BY DIRECTION:")
        for direction in ['LONG', 'SHORT']:
            trades_dir = [t for t in self.trades if t['direction'] == direction]
            winners_dir = [t for t in trades_dir if t['winner']]

            if trades_dir:
                wr = (len(winners_dir) / len(trades_dir)) * 100
                avg_pnl = statistics.mean([t['pnl_pct'] for t in trades_dir])
                print(f"   {direction:5s}: {wr:5.1f}% win rate | Avg P&L: {avg_pnl:+.3f}%")

        # Pattern analysis
        self.analyze_winning_patterns()
        self.analyze_losing_patterns()

    def analyze_winning_patterns(self):
        """Analyze characteristics of winning trades"""
        winners = [t for t in self.trades if t['winner']]

        if not winners:
            return

        print(f"\n🏆 WINNING TRADE PATTERNS (n={len(winners)}):")

        # Average conditions
        avg_range_30min = statistics.mean([t['entry_conditions']['range_30min'] for t in winners])
        avg_price_loc = statistics.mean([t['entry_conditions']['price_location_pct'] for t in winners])
        avg_flips = statistics.mean([t['entry_conditions']['ribbon_flips_30min'] for t in winners])

        print(f"   Avg 30min range: {avg_range_30min:.3f}%")
        print(f"   Avg price location: {avg_price_loc:.1f}% of 2h range")
        print(f"   Avg ribbon flips (30min): {avg_flips:.1f}")

        # Best setups (highest win rate)
        print(f"\n✅ BEST SETUPS:")

        # High range
        high_range_winners = [t for t in winners if t['entry_conditions']['range_30min'] >= 0.8]
        if high_range_winners:
            print(f"   • Big moves (30min ≥0.8%): {len(high_range_winners)} winners")

        # Low location
        low_loc_winners = [t for t in winners if t['entry_conditions']['price_location_pct'] < 40]
        if low_loc_winners:
            print(f"   • Lower 40% of range: {len(low_loc_winners)} winners")

        # Stable (low flips)
        stable_winners = [t for t in winners if t['entry_conditions']['ribbon_flips_30min'] <= 1]
        if stable_winners:
            print(f"   • Stable (≤1 flip): {len(stable_winners)} winners")

    def analyze_losing_patterns(self):
        """Analyze characteristics of losing trades"""
        losers = [t for t in self.trades if not t['winner']]

        if not losers:
            return

        print(f"\n❌ LOSING TRADE PATTERNS (n={len(losers)}):")

        # Average conditions
        avg_range_30min = statistics.mean([t['entry_conditions']['range_30min'] for t in losers])
        avg_price_loc = statistics.mean([t['entry_conditions']['price_location_pct'] for t in losers])
        avg_flips = statistics.mean([t['entry_conditions']['ribbon_flips_30min'] for t in losers])

        print(f"   Avg 30min range: {avg_range_30min:.3f}%")
        print(f"   Avg price location: {avg_price_loc:.1f}% of 2h range")
        print(f"   Avg ribbon flips (30min): {avg_flips:.1f}")

        # Worst setups
        print(f"\n🚫 WORST SETUPS:")

        # Low range (ranging)
        low_range_losers = [t for t in losers if t['entry_conditions']['range_30min'] < 0.4]
        if low_range_losers:
            print(f"   • Ranging (30min <0.4%): {len(low_range_losers)} losers")

        # High location (chasing)
        high_loc_losers = [t for t in losers if t['entry_conditions']['price_location_pct'] > 75]
        if high_loc_losers:
            print(f"   • Upper 25% of range: {len(high_loc_losers)} losers")

        # Choppy
        choppy_losers = [t for t in losers if t['entry_conditions']['ribbon_flips_30min'] >= 3]
        if choppy_losers:
            print(f"   • Choppy (≥3 flips): {len(choppy_losers)} losers")

    def save_results(self, output_file='backtest_results.json'):
        """Save detailed results to JSON"""
        results = {
            'summary': {
                'total_trades': len(self.trades),
                'winners': len([t for t in self.trades if t['winner']]),
                'losers': len([t for t in self.trades if not t['winner']]),
            },
            'trades': self.trades
        }

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n💾 Results saved to {output_file}")

    def export_profitable_trades_csv(self, output_file='profitable_trades_last_30h.csv', hours=30):
        """
        Export profitable trades from the last N hours to CSV

        Args:
            output_file: Output CSV filename
            hours: Number of hours to look back (default 30)
        """
        if not self.trades:
            print("❌ No trades to export")
            return

        # Find the most recent timestamp in the data
        if self.data_5min:
            latest_time = self.data_5min[-1]['timestamp']
            cutoff_time = latest_time - timedelta(hours=hours)

            # Filter profitable trades from last N hours
            recent_profitable_trades = [
                t for t in self.trades
                if t['winner'] and t['entry_time'] >= cutoff_time
            ]

            if not recent_profitable_trades:
                print(f"❌ No profitable trades found in the last {hours} hours")
                return

            # Sort by entry time
            recent_profitable_trades.sort(key=lambda x: x['entry_time'])

            # Write to CSV
            with open(output_file, 'w', newline='') as f:
                fieldnames = [
                    'entry_time', 'exit_time', 'direction', 'entry_price', 'exit_price',
                    'hold_minutes', 'pnl_pct', 'pnl_dollars', 'quality_score',
                    'range_30min', 'range_15min', 'price_location_pct', 'ribbon_flips_30min',
                    'state_5min', 'state_15min', 'ribbon_stayed_aligned'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for trade in recent_profitable_trades:
                    writer.writerow({
                        'entry_time': trade['entry_time'].strftime('%Y-%m-%d %H:%M:%S'),
                        'exit_time': trade['exit_time'].strftime('%Y-%m-%d %H:%M:%S'),
                        'direction': trade['direction'],
                        'entry_price': f"{trade['entry_price']:.2f}",
                        'exit_price': f"{trade['exit_price']:.2f}",
                        'hold_minutes': trade['hold_minutes'],
                        'pnl_pct': f"{trade['pnl_pct']:.3f}",
                        'pnl_dollars': f"{trade['pnl_dollars']:.2f}",
                        'quality_score': trade['opportunity']['quality_score'],
                        'range_30min': f"{trade['entry_conditions']['range_30min']:.3f}",
                        'range_15min': f"{trade['entry_conditions']['range_15min']:.3f}",
                        'price_location_pct': f"{trade['entry_conditions']['price_location_pct']:.1f}",
                        'ribbon_flips_30min': trade['entry_conditions']['ribbon_flips_30min'],
                        'state_5min': trade['entry_conditions']['state_5min'],
                        'state_15min': trade['entry_conditions']['state_15min'],
                        'ribbon_stayed_aligned': trade['ribbon_stayed_aligned']
                    })

            print(f"\n💾 Exported {len(recent_profitable_trades)} profitable trades to {output_file}")
            print(f"   Time range: {cutoff_time.strftime('%Y-%m-%d %H:%M')} to {latest_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            print("❌ No data available to determine time range")

    def create_candlesticks_from_data(self, data_list: List[Dict], candle_minutes: int,
                                       output_file: str):
        """
        Create candlestick data from 10-second interval EMA data
        Includes OHLC for price AND for each EMA, plus their colors/intensities

        Args:
            data_list: List of data points (5min or 15min data)
            candle_minutes: Candle size in minutes (5 or 15)
            output_file: Output CSV filename
        """
        if not data_list:
            print(f"❌ No data to create candlesticks")
            return

        # Define all EMA periods we track
        ema_periods = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75,
                       80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]

        # 10-second intervals, so 6 points per minute
        points_per_candle = candle_minutes * 6

        candles = []
        i = 0

        while i < len(data_list):
            # Gather points for this candle
            candle_data = []

            for j in range(points_per_candle):
                if i + j < len(data_list):
                    point = data_list[i + j]
                    if point['price'] > 0:  # Only include valid prices
                        candle_data.append(point)

            if candle_data:
                # Calculate OHLC for price
                prices = [p['price'] for p in candle_data]

                candle = {
                    'timestamp': candle_data[0]['timestamp'],
                    'price_open': candle_data[0]['price'],
                    'price_high': max(prices),
                    'price_low': min(prices),
                    'price_close': candle_data[-1]['price'],
                    'num_points': len(candle_data),
                    'ribbon_state_open': candle_data[0].get('raw_row', {}).get('ribbon_state', ''),
                    'ribbon_state_close': candle_data[-1].get('raw_row', {}).get('ribbon_state', '')
                }

                # Calculate OHLC for each EMA
                for period in ema_periods:
                    ema_key = f'MMA{period}'
                    ema_values = []
                    ema_colors = []
                    ema_intensities = []

                    for point in candle_data:
                        raw_row = point.get('raw_row', {})
                        ema_val = raw_row.get(f'{ema_key}_value', '')
                        if ema_val and ema_val != '':
                            try:
                                ema_values.append(float(ema_val))
                                ema_colors.append(raw_row.get(f'{ema_key}_color', ''))
                                ema_intensities.append(raw_row.get(f'{ema_key}_intensity', ''))
                            except (ValueError, TypeError):
                                pass

                    if ema_values:
                        # OHLC for this EMA
                        candle[f'{ema_key}_open'] = ema_values[0]
                        candle[f'{ema_key}_high'] = max(ema_values)
                        candle[f'{ema_key}_low'] = min(ema_values)
                        candle[f'{ema_key}_close'] = ema_values[-1]
                        # Color and intensity at close of candle
                        candle[f'{ema_key}_color'] = ema_colors[-1] if ema_colors else ''
                        candle[f'{ema_key}_intensity'] = ema_intensities[-1] if ema_intensities else ''
                    else:
                        candle[f'{ema_key}_open'] = ''
                        candle[f'{ema_key}_high'] = ''
                        candle[f'{ema_key}_low'] = ''
                        candle[f'{ema_key}_close'] = ''
                        candle[f'{ema_key}_color'] = ''
                        candle[f'{ema_key}_intensity'] = ''

                candles.append(candle)

            # Move to next candle
            i += points_per_candle

        # Write to CSV
        if candles:
            with open(output_file, 'w', newline='') as f:
                # Build fieldnames dynamically
                fieldnames = ['timestamp', 'price_open', 'price_high', 'price_low', 'price_close',
                             'ribbon_state_open', 'ribbon_state_close', 'num_points']

                # Add EMA fields
                for period in ema_periods:
                    ema_key = f'MMA{period}'
                    fieldnames.extend([
                        f'{ema_key}_open', f'{ema_key}_high', f'{ema_key}_low', f'{ema_key}_close',
                        f'{ema_key}_color', f'{ema_key}_intensity'
                    ])

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for candle in candles:
                    row = {
                        'timestamp': candle['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        'price_open': f"{candle['price_open']:.2f}",
                        'price_high': f"{candle['price_high']:.2f}",
                        'price_low': f"{candle['price_low']:.2f}",
                        'price_close': f"{candle['price_close']:.2f}",
                        'ribbon_state_open': candle['ribbon_state_open'],
                        'ribbon_state_close': candle['ribbon_state_close'],
                        'num_points': candle['num_points']
                    }

                    # Add EMA data
                    for period in ema_periods:
                        ema_key = f'MMA{period}'
                        for suffix in ['_open', '_high', '_low', '_close']:
                            val = candle.get(f'{ema_key}{suffix}', '')
                            if val != '':
                                try:
                                    row[f'{ema_key}{suffix}'] = f"{float(val):.2f}"
                                except (ValueError, TypeError):
                                    row[f'{ema_key}{suffix}'] = ''
                            else:
                                row[f'{ema_key}{suffix}'] = ''

                        row[f'{ema_key}_color'] = candle.get(f'{ema_key}_color', '')
                        row[f'{ema_key}_intensity'] = candle.get(f'{ema_key}_intensity', '')

                    writer.writerow(row)

            print(f"\n💾 Created {len(candles)} {candle_minutes}-minute candlesticks with EMA data in {output_file}")
            if candles:
                print(f"   Time range: {candles[0]['timestamp'].strftime('%Y-%m-%d %H:%M')} to {candles[-1]['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                print(f"   Includes OHLC for price + {len(ema_periods)} EMAs with colors/intensities")
        else:
            print(f"❌ No valid candlesticks created")

    def export_candlestick_csvs(self):
        """
        Export candlestick CSVs for both 5min and 15min timeframes
        """
        print("\n📊 Creating candlestick CSVs from EMA data...")

        # Create 5-minute candlesticks
        self.create_candlesticks_from_data(
            self.data_5min,
            candle_minutes=5,
            output_file='candlesticks_5min.csv'
        )

        # Create 15-minute candlesticks
        self.create_candlesticks_from_data(
            self.data_15min,
            candle_minutes=15,
            output_file='candlesticks_15min.csv'
        )


def main():
    """Main execution"""
    print("🚀 EMA Ribbon Strategy Backtester")
    print("="*80)

    # Initialize backtester
    backtester = EMABacktester(
        csv_5min_path='trading_data/ema_data_5min.csv',
        csv_15min_path='trading_data/ema_data_15min.csv'
    )

    # Run analysis
    backtester.load_data()
    backtester.detect_entry_opportunities()
    backtester.run_backtest(hold_durations=[5, 10, 15, 20, 30])
    backtester.generate_report()
    backtester.save_results()

    # Export additional CSV files
    print("\n" + "="*80)
    print("EXPORTING ADDITIONAL CSV FILES")
    print("="*80)

    # Export profitable trades from last 30 hours
    backtester.export_profitable_trades_csv(
        output_file='profitable_trades_last_30h.csv',
        hours=30
    )

    # Export candlestick CSVs
    backtester.export_candlestick_csvs()

    print("\n✅ Backtest complete!")


if __name__ == "__main__":
    main()
