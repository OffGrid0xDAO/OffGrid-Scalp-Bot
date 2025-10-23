"""
Big Movement EMA Analyzer
Analyzes historical EMA data to find patterns that predict BIG movements
Focuses on: EMA colors, compression, alignment, transitions
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json
from collections import defaultdict


class BigMovementEMAAnalyzer:
    """Finds EMA patterns that precede big price movements"""

    def __init__(self, ema_5min_path: str = 'trading_data/ema_data_5min.csv',
                 ema_15min_path: str = 'trading_data/ema_data_15min.csv'):
        self.ema_5min_path = ema_5min_path
        self.ema_15min_path = ema_15min_path

        # What defines a "BIG" movement
        self.big_move_threshold = 0.005  # 0.5% in 5 minutes

        # EMA columns to analyze
        self.ema_periods = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70,
                           75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]

    def load_data(self) -> pd.DataFrame:
        """Load EMA data"""
        df = pd.read_csv(self.ema_5min_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df

    def calculate_ema_compression(self, row: pd.Series) -> Dict:
        """
        Calculate EMA ribbon compression/expansion

        Compression = EMAs are close together (ranging market)
        Expansion = EMAs spreading apart (trending market)
        """
        ema_values = []

        for period in self.ema_periods:
            col_name = f'MMA{period}_value'
            if col_name in row.index and pd.notna(row[col_name]):
                ema_values.append(float(row[col_name]))

        if len(ema_values) < 2:
            return {'compression': 0, 'spread_pct': 0, 'state': 'unknown'}

        # Calculate spread between fastest and slowest EMA
        ema_min = min(ema_values)
        ema_max = max(ema_values)
        spread = ema_max - ema_min
        spread_pct = (spread / ema_min) * 100 if ema_min > 0 else 0

        # Calculate compression score (lower = more compressed)
        # Use standard deviation of EMA values
        ema_std = np.std(ema_values)
        ema_mean = np.mean(ema_values)
        compression = (ema_std / ema_mean) * 100 if ema_mean > 0 else 0

        # Determine state
        if compression < 0.1:
            state = 'highly_compressed'
        elif compression < 0.2:
            state = 'compressed'
        elif compression < 0.4:
            state = 'normal'
        elif compression < 0.8:
            state = 'expanding'
        else:
            state = 'highly_expanded'

        return {
            'compression': compression,
            'spread_pct': spread_pct,
            'spread_absolute': spread,
            'state': state,
            'ema_min': ema_min,
            'ema_max': ema_max
        }

    def analyze_ema_colors(self, row: pd.Series) -> Dict:
        """
        Analyze EMA color distribution and patterns

        Returns:
        - Total count by color
        - Light vs dark intensity
        - Color transitions
        - Alignment strength
        """
        colors = {
            'green': 0, 'red': 0, 'yellow': 0, 'gray': 0,
            'light_green': 0, 'dark_green': 0,
            'light_red': 0, 'dark_red': 0,
            'total_emas': 0
        }

        for period in self.ema_periods:
            color_col = f'MMA{period}_color'
            intensity_col = f'MMA{period}_intensity'

            if color_col not in row.index:
                continue

            color = row[color_col]
            intensity = row.get(intensity_col, 'normal')

            colors['total_emas'] += 1

            if color == 'green':
                colors['green'] += 1
                if intensity == 'light':
                    colors['light_green'] += 1
                elif intensity == 'dark':
                    colors['dark_green'] += 1
            elif color == 'red':
                colors['red'] += 1
                if intensity == 'light':
                    colors['light_red'] += 1
                elif intensity == 'dark':
                    colors['dark_red'] += 1
            elif color == 'yellow':
                colors['yellow'] += 1
            elif color == 'gray':
                colors['gray'] += 1

        # Calculate percentages
        total_non_yellow = colors['green'] + colors['red'] + colors['gray']
        if total_non_yellow > 0:
            colors['green_pct'] = colors['green'] / total_non_yellow
            colors['red_pct'] = colors['red'] / total_non_yellow
            colors['gray_pct'] = colors['gray'] / total_non_yellow
        else:
            colors['green_pct'] = 0
            colors['red_pct'] = 0
            colors['gray_pct'] = 0

        # Determine alignment strength
        if colors['green_pct'] >= 0.90:
            colors['alignment'] = 'strong_bullish'
        elif colors['green_pct'] >= 0.75:
            colors['alignment'] = 'moderate_bullish'
        elif colors['red_pct'] >= 0.90:
            colors['alignment'] = 'strong_bearish'
        elif colors['red_pct'] >= 0.75:
            colors['alignment'] = 'moderate_bearish'
        else:
            colors['alignment'] = 'mixed'

        return colors

    def detect_color_transition(self, df: pd.DataFrame, idx: int, lookback: int = 3) -> Dict:
        """
        Detect how colors are transitioning

        Are EMAs rapidly turning from red→green or green→red?
        This indicates momentum building!
        """
        if idx < lookback:
            return {'transition': 'insufficient_data'}

        # Get current colors
        current = self.analyze_ema_colors(df.iloc[idx])

        # Get colors from N minutes ago
        past = self.analyze_ema_colors(df.iloc[idx - lookback])

        # Calculate transition
        green_change = current['green'] - past['green']
        red_change = current['red'] - past['red']
        light_green_change = current['light_green'] - past['light_green']
        light_red_change = current['light_red'] - past['light_red']

        transition = {
            'green_change': green_change,
            'red_change': red_change,
            'light_green_change': light_green_change,
            'light_red_change': light_red_change,
            'direction': None,
            'speed': None
        }

        # Determine transition direction and speed
        if green_change >= 5:
            transition['direction'] = 'turning_bullish'
            if light_green_change >= 3:
                transition['speed'] = 'fast'
            else:
                transition['speed'] = 'slow'
        elif red_change >= 5:
            transition['direction'] = 'turning_bearish'
            if light_red_change >= 3:
                transition['speed'] = 'fast'
            else:
                transition['speed'] = 'slow'
        else:
            transition['direction'] = 'stable'
            transition['speed'] = 'none'

        return transition

    def find_big_movements(self, df: pd.DataFrame) -> List[Dict]:
        """
        Find all BIG price movements in the data
        A big movement = price change >= threshold in 5 minutes (5 rows)
        """
        big_movements = []

        # Check every 5-minute window
        for i in range(5, len(df)):
            price_start = df.iloc[i-5]['price']
            price_end = df.iloc[i]['price']

            if price_start == 0:
                continue

            price_change_pct = (price_end - price_start) / price_start

            if abs(price_change_pct) >= self.big_move_threshold:
                big_movements.append({
                    'index': i,
                    'timestamp': df.iloc[i]['timestamp'],
                    'direction': 'UP' if price_change_pct > 0 else 'DOWN',
                    'magnitude_pct': price_change_pct * 100,
                    'price_start': price_start,
                    'price_end': price_end,
                    'duration_minutes': 5
                })

        return big_movements

    def analyze_pattern_before_big_move(self, df: pd.DataFrame, big_move: Dict,
                                       lookback_minutes: int = 5) -> Dict:
        """
        Analyze the EMA pattern BEFORE a big movement happened

        This is the KEY function - finds what signals appeared before the move!
        """
        move_idx = big_move['index']

        # Look at pattern from 5 minutes before to 1 minute before
        pattern_timeline = []

        for minutes_before in range(lookback_minutes, 0, -1):
            idx = move_idx - minutes_before
            if idx < 0:
                continue

            row = df.iloc[idx]

            # Get EMA colors at this point
            colors = self.analyze_ema_colors(row)

            # Get EMA compression at this point
            compression = self.calculate_ema_compression(row)

            # Get color transition
            transition = self.detect_color_transition(df, idx, lookback=3)

            pattern_timeline.append({
                'minutes_before_move': minutes_before,
                'timestamp': row['timestamp'],
                'price': row['price'],
                'colors': colors,
                'compression': compression,
                'transition': transition,
                'ribbon_state': row.get('ribbon_state', 'unknown')
            })

        # Identify key pattern characteristics
        pattern_summary = self.summarize_pattern(pattern_timeline, big_move['direction'])

        return {
            'timeline': pattern_timeline,
            'summary': pattern_summary
        }

    def summarize_pattern(self, timeline: List[Dict], move_direction: str) -> Dict:
        """
        Summarize the pattern that led to the big movement

        Finds:
        - When did light EMAs start appearing?
        - How fast did compression change?
        - When did ribbon flip?
        - What was the earliest signal?
        """
        summary = {
            'earliest_signal_minutes': None,
            'light_ema_appearance': [],
            'compression_trend': None,
            'ribbon_flip_timing': None,
            'transition_speed': None,
            'key_signals': []
        }

        if not timeline:
            return summary

        # Track when light EMAs appeared
        for entry in timeline:
            minutes_before = entry['minutes_before_move']
            colors = entry['colors']

            if move_direction == 'UP':
                light_count = colors['light_green']
                if light_count >= 2:
                    summary['light_ema_appearance'].append({
                        'minutes_before': minutes_before,
                        'count': light_count
                    })
                    if summary['earliest_signal_minutes'] is None:
                        summary['earliest_signal_minutes'] = minutes_before
            else:  # DOWN
                light_count = colors['light_red']
                if light_count >= 2:
                    summary['light_ema_appearance'].append({
                        'minutes_before': minutes_before,
                        'count': light_count
                    })
                    if summary['earliest_signal_minutes'] is None:
                        summary['earliest_signal_minutes'] = minutes_before

        # Analyze compression trend
        compressions = [e['compression']['compression'] for e in timeline]
        if len(compressions) >= 2:
            if compressions[-1] > compressions[0] * 1.5:
                summary['compression_trend'] = 'expanding'
            elif compressions[-1] < compressions[0] * 0.7:
                summary['compression_trend'] = 'compressing'
            else:
                summary['compression_trend'] = 'stable'

        # Find when ribbon flipped
        for i, entry in enumerate(timeline):
            if i == 0:
                continue
            prev_state = timeline[i-1]['ribbon_state']
            curr_state = entry['ribbon_state']

            if move_direction == 'UP' and prev_state != curr_state and 'green' in curr_state:
                summary['ribbon_flip_timing'] = entry['minutes_before_move']
            elif move_direction == 'DOWN' and prev_state != curr_state and 'red' in curr_state:
                summary['ribbon_flip_timing'] = entry['minutes_before_move']

        # Determine transition speed
        transitions = [e['transition'] for e in timeline]
        fast_transitions = sum(1 for t in transitions if t.get('speed') == 'fast')
        if fast_transitions >= 2:
            summary['transition_speed'] = 'fast'
        else:
            summary['transition_speed'] = 'slow'

        # Generate key signals
        if summary['earliest_signal_minutes']:
            summary['key_signals'].append(
                f"Light EMAs appeared {summary['earliest_signal_minutes']}min before move"
            )
        if summary['compression_trend'] == 'expanding':
            summary['key_signals'].append("EMAs were expanding (trend building)")
        if summary['ribbon_flip_timing']:
            summary['key_signals'].append(
                f"Ribbon flipped {summary['ribbon_flip_timing']}min before move"
            )
        if summary['transition_speed'] == 'fast':
            summary['key_signals'].append("Fast color transition (strong momentum)")

        return summary

    def find_common_patterns(self, all_patterns: List[Dict]) -> Dict:
        """
        Find COMMON patterns across all big movements

        This tells us: What ALWAYS happens before a big move?
        """
        common = {
            'avg_earliest_signal_minutes': 0,
            'avg_light_emas_at_signal': 0,
            'compression_trend_distribution': defaultdict(int),
            'avg_ribbon_flip_timing': 0,
            'transition_speed_distribution': defaultdict(int),
            'most_common_signals': []
        }

        earliest_signals = []
        light_ema_counts = []
        ribbon_flip_timings = []

        for pattern in all_patterns:
            summary = pattern['summary']

            if summary['earliest_signal_minutes']:
                earliest_signals.append(summary['earliest_signal_minutes'])

                # Find light EMA count at earliest signal
                for appearance in summary['light_ema_appearance']:
                    if appearance['minutes_before'] == summary['earliest_signal_minutes']:
                        light_ema_counts.append(appearance['count'])

            if summary['compression_trend']:
                common['compression_trend_distribution'][summary['compression_trend']] += 1

            if summary['ribbon_flip_timing']:
                ribbon_flip_timings.append(summary['ribbon_flip_timing'])

            if summary['transition_speed']:
                common['transition_speed_distribution'][summary['transition_speed']] += 1

        # Calculate averages
        if earliest_signals:
            common['avg_earliest_signal_minutes'] = np.mean(earliest_signals)
        if light_ema_counts:
            common['avg_light_emas_at_signal'] = np.mean(light_ema_counts)
        if ribbon_flip_timings:
            common['avg_ribbon_flip_timing'] = np.mean(ribbon_flip_timings)

        # Find most common signals
        signal_counts = defaultdict(int)
        for pattern in all_patterns:
            for signal in pattern['summary']['key_signals']:
                signal_counts[signal] += 1

        common['most_common_signals'] = sorted(
            signal_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return common

    def analyze_all_big_movements(self) -> Dict:
        """
        Main analysis function:
        1. Find all big movements
        2. Analyze EMA pattern before each
        3. Find common patterns
        4. Generate trading rules
        """
        print("\n" + "="*70)
        print("BIG MOVEMENT EMA PATTERN ANALYSIS")
        print("="*70)

        # Load data
        print("\n[1/5] Loading EMA data...")
        df = self.load_data()
        print(f"✅ Loaded {len(df):,} EMA snapshots")

        # Find big movements
        print("\n[2/5] Finding big movements...")
        big_movements = self.find_big_movements(df)
        print(f"✅ Found {len(big_movements)} big movements (>{self.big_move_threshold*100}%)")

        if len(big_movements) == 0:
            return {'error': 'No big movements found in data'}

        # Show some examples
        print(f"\nExample big movements:")
        for i, move in enumerate(big_movements[:3]):
            print(f"  {i+1}. {move['timestamp']} - {move['direction']} {move['magnitude_pct']:.2f}%")

        # Analyze pattern before each big movement
        print("\n[3/5] Analyzing EMA patterns before each big movement...")
        all_patterns = []

        for move in big_movements:
            pattern = self.analyze_pattern_before_big_move(df, move, lookback_minutes=5)
            all_patterns.append({
                'big_move': move,
                'pattern': pattern['timeline'],
                'summary': pattern['summary']
            })

        print(f"✅ Analyzed {len(all_patterns)} patterns")

        # Find common patterns
        print("\n[4/5] Finding common patterns...")
        common_patterns = self.find_common_patterns(all_patterns)
        print("✅ Common patterns identified")

        # Generate insights
        print("\n[5/5] Generating insights...")
        insights = self.generate_insights(common_patterns, all_patterns)

        # Compile results
        results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_big_movements': len(big_movements),
            'big_movements_up': len([m for m in big_movements if m['direction'] == 'UP']),
            'big_movements_down': len([m for m in big_movements if m['direction'] == 'DOWN']),
            'avg_magnitude': np.mean([abs(m['magnitude_pct']) for m in big_movements]),
            'common_patterns': common_patterns,
            'insights': insights,
            'detailed_patterns': all_patterns[:10]  # Include first 10 for detailed review
        }

        return results

    def generate_insights(self, common_patterns: Dict, all_patterns: List[Dict]) -> Dict:
        """
        Generate actionable insights for trading rules
        """
        insights = {
            'earliest_warning_signal': None,
            'optimal_entry_timing': None,
            'key_indicators': [],
            'recommended_rules': {}
        }

        # Earliest warning signal
        if common_patterns['avg_earliest_signal_minutes'] > 0:
            insights['earliest_warning_signal'] = f"{common_patterns['avg_earliest_signal_minutes']:.1f} minutes before move"
            insights['key_indicators'].append(
                f"Watch for {common_patterns['avg_light_emas_at_signal']:.1f} light EMAs appearing"
            )

        # Optimal entry timing
        if common_patterns['avg_ribbon_flip_timing'] > 0:
            insights['optimal_entry_timing'] = f"{common_patterns['avg_ribbon_flip_timing']:.1f} minutes before peak"

        # Key indicators
        for signal, count in common_patterns['most_common_signals']:
            if count >= len(all_patterns) * 0.5:  # Appears in 50%+ of cases
                insights['key_indicators'].append(f"{signal} (in {count}/{len(all_patterns)} cases)")

        # Recommended rules
        insights['recommended_rules'] = {
            'min_light_emas_required': int(common_patterns['avg_light_emas_at_signal']) if common_patterns['avg_light_emas_at_signal'] > 0 else 3,
            'watch_for_expansion': common_patterns['compression_trend_distribution'].get('expanding', 0) > common_patterns['compression_trend_distribution'].get('compressing', 0),
            'prefer_fast_transitions': common_patterns['transition_speed_distribution'].get('fast', 0) > common_patterns['transition_speed_distribution'].get('slow', 0),
            'entry_window_minutes': int(common_patterns['avg_ribbon_flip_timing']) if common_patterns['avg_ribbon_flip_timing'] > 0 else 3
        }

        return insights


def main():
    """Run the analyzer"""
    analyzer = BigMovementEMAAnalyzer()
    results = analyzer.analyze_all_big_movements()

    if 'error' in results:
        print(f"\n❌ {results['error']}")
        return

    # Display results
    print("\n" + "="*70)
    print("ANALYSIS RESULTS")
    print("="*70)

    print(f"\n📊 Big Movements Summary:")
    print(f"   Total: {results['total_big_movements']}")
    print(f"   UP: {results['big_movements_up']}")
    print(f"   DOWN: {results['big_movements_down']}")
    print(f"   Avg magnitude: {results['avg_magnitude']:.2f}%")

    print(f"\n🔍 Common Patterns Found:")
    common = results['common_patterns']
    print(f"   Earliest signal: {common['avg_earliest_signal_minutes']:.1f} minutes before")
    print(f"   Light EMAs at signal: {common['avg_light_emas_at_signal']:.1f}")
    print(f"   Ribbon flip timing: {common['avg_ribbon_flip_timing']:.1f} minutes before peak")
    print(f"   Compression trend: {dict(common['compression_trend_distribution'])}")
    print(f"   Transition speed: {dict(common['transition_speed_distribution'])}")

    print(f"\n💡 Key Insights:")
    insights = results['insights']
    if insights['earliest_warning_signal']:
        print(f"   ⚡ Earliest warning: {insights['earliest_warning_signal']}")
    if insights['optimal_entry_timing']:
        print(f"   ⏰ Optimal entry: {insights['optimal_entry_timing']}")

    print(f"\n   📌 Key Indicators (appear in 50%+ of big moves):")
    for indicator in insights['key_indicators']:
        print(f"      • {indicator}")

    print(f"\n🎯 Recommended Trading Rules:")
    rules = insights['recommended_rules']
    print(f"   • Require {rules['min_light_emas_required']}+ light EMAs")
    print(f"   • Watch for expansion: {rules['watch_for_expansion']}")
    print(f"   • Prefer fast transitions: {rules['prefer_fast_transitions']}")
    print(f"   • Entry window: {rules['entry_window_minutes']} minutes")

    # Save results
    output_file = 'trading_data/big_movement_ema_patterns.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Full results saved to: {output_file}")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
