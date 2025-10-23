#!/usr/bin/env python3
"""
Optimal Trades Pattern Analysis Engine

Analyzes the dataset of optimal trades to discover:
1. Common indicator patterns across winning entries
2. Support/Resistance correlations
3. Indicator combinations that predict success
4. What separates good entries from bad ones

This reverse-engineers YOUR trading expertise into quantifiable rules!
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List


class PatternAnalyzer:
    """
    Discover patterns in optimal trades dataset
    """

    def __init__(self, trades_file: str = None):
        """Initialize analyzer"""
        if trades_file is None:
            trades_file = Path(__file__).parent / 'trading_data' / 'optimal_trades.json'

        with open(trades_file, 'r') as f:
            self.data = json.load(f)

        self.optimal_entries = self.data['optimal_entries']
        self.missed_opportunities = self.data.get('missed_opportunities', [])
        self.false_signals = self.data.get('false_signals_bot_took', [])

    def analyze_all(self):
        """Run complete pattern analysis"""
        print("\n" + "="*80)
        print("🔬 PATTERN ANALYSIS: DISCOVERING YOUR WINNING STRATEGY")
        print("="*80)

        print(f"\nAnalyzing {len(self.optimal_entries)} optimal trades...")

        # Separate by direction
        long_trades = [t for t in self.optimal_entries if t['direction'] == 'long']
        short_trades = [t for t in self.optimal_entries if t['direction'] == 'short']

        print(f"  - {len(long_trades)} LONG trades")
        print(f"  - {len(short_trades)} SHORT trades")

        # 1. Indicator Statistics
        print("\n" + "="*80)
        print("📊 INDICATOR ANALYSIS")
        print("="*80)

        long_patterns = self.analyze_indicator_patterns(long_trades, "LONG")
        short_patterns = self.analyze_indicator_patterns(short_trades, "SHORT")

        # 2. Support/Resistance Analysis
        print("\n" + "="*80)
        print("📍 SUPPORT/RESISTANCE ANALYSIS")
        print("="*80)

        self.analyze_support_resistance(long_trades, "LONG")
        self.analyze_support_resistance(short_trades, "SHORT")

        # 3. Volume Analysis
        print("\n" + "="*80)
        print("📈 VOLUME ANALYSIS")
        print("="*80)

        self.analyze_volume_patterns(long_trades, "LONG")
        self.analyze_volume_patterns(short_trades, "SHORT")

        # 4. Key Discriminators
        print("\n" + "="*80)
        print("🎯 KEY PATTERN DISCOVERIES")
        print("="*80)

        self.find_key_discriminators(long_trades, short_trades)

        # 5. Generate trading rules
        print("\n" + "="*80)
        print("📜 PROPOSED TRADING RULES (Based on Your Expert Trades)")
        print("="*80)

        rules = self.generate_trading_rules(long_patterns, short_patterns)

        return rules

    def analyze_indicator_patterns(self, trades: List[Dict], direction: str) -> Dict:
        """
        Analyze indicator values across trades

        Args:
            trades: List of trades
            direction: 'LONG' or 'SHORT'

        Returns:
            Dictionary of indicator statistics
        """
        print(f"\n{direction} Entries ({len(trades)} trades):")
        print("-" * 80)

        if not trades:
            return {}

        # Collect all indicator values
        indicator_values = defaultdict(list)

        for trade in trades:
            indicators = trade['market_state']['indicators']
            for key, value in indicators.items():
                if isinstance(value, (int, float)):
                    indicator_values[key].append(value)

        # Calculate statistics for key indicators
        key_indicators = [
            'confluence_score_long', 'confluence_score_short',
            'rsi_14', 'rsi_7',
            'stoch_k', 'stoch_d',
            'macd_histogram', 'macd_fast_value', 'macd_signal_value',
            'volume_ratio', 'volume_ma_ratio'
        ]

        patterns = {}

        for indicator in key_indicators:
            if indicator in indicator_values:
                values = indicator_values[indicator]
                patterns[indicator] = {
                    'mean': np.mean(values),
                    'median': np.median(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'std': np.std(values)
                }

                print(f"\n{indicator}:")
                print(f"  Mean: {patterns[indicator]['mean']:.2f}")
                print(f"  Range: [{patterns[indicator]['min']:.2f}, {patterns[indicator]['max']:.2f}]")
                print(f"  Median: {patterns[indicator]['median']:.2f}")

        # Analyze categorical indicators
        print("\n" + "-" * 40)
        print("Categorical Patterns:")

        # MACD trend
        macd_trends = []
        volume_statuses = []

        for trade in trades:
            indicators = trade['market_state']['indicators']
            if 'macd_fast_trend' in indicators:
                macd_trends.append(indicators['macd_fast_trend'])
            if 'volume_status' in indicators:
                volume_statuses.append(indicators['volume_status'])

        if macd_trends:
            macd_counter = Counter(macd_trends)
            print(f"\nMACD Trend Distribution:")
            for trend, count in macd_counter.most_common():
                pct = count / len(macd_trends) * 100
                print(f"  {trend}: {count} ({pct:.1f}%)")

        if volume_statuses:
            vol_counter = Counter(volume_statuses)
            print(f"\nVolume Status Distribution:")
            for status, count in vol_counter.most_common():
                pct = count / len(volume_statuses) * 100
                print(f"  {status}: {count} ({pct:.1f}%)")

        return patterns

    def analyze_support_resistance(self, trades: List[Dict], direction: str):
        """Analyze support/resistance patterns"""
        print(f"\n{direction} Entries - S/R Analysis:")
        print("-" * 80)

        if not trades:
            return

        at_support_count = 0
        at_resistance_count = 0
        near_support_count = 0
        near_resistance_count = 0

        support_distances = []
        resistance_distances = []

        for trade in trades:
            sr = trade['market_state']['support_resistance']

            if sr.get('at_support'):
                at_support_count += 1
            if sr.get('at_resistance'):
                at_resistance_count += 1

            if sr.get('nearest_support'):
                dist = abs(sr['nearest_support']['distance_pct'])
                support_distances.append(dist)
                if dist < 1.0:
                    near_support_count += 1

            if sr.get('nearest_resistance'):
                dist = abs(sr['nearest_resistance']['distance_pct'])
                resistance_distances.append(dist)
                if dist < 1.0:
                    near_resistance_count += 1

        total = len(trades)
        print(f"\nAt Key Levels:")
        print(f"  Exactly at support: {at_support_count}/{total} ({at_support_count/total*100:.1f}%)")
        print(f"  Exactly at resistance: {at_resistance_count}/{total} ({at_resistance_count/total*100:.1f}%)")
        print(f"  Near support (<1%): {near_support_count}/{total} ({near_support_count/total*100:.1f}%)")
        print(f"  Near resistance (<1%): {near_resistance_count}/{total} ({near_resistance_count/total*100:.1f}%)")

        if support_distances:
            print(f"\nDistance from Support:")
            print(f"  Mean: {np.mean(support_distances):.2f}%")
            print(f"  Median: {np.median(support_distances):.2f}%")

        if resistance_distances:
            print(f"\nDistance from Resistance:")
            print(f"  Mean: {np.mean(resistance_distances):.2f}%")
            print(f"  Median: {np.median(resistance_distances):.2f}%")

    def analyze_volume_patterns(self, trades: List[Dict], direction: str):
        """Analyze volume patterns"""
        print(f"\n{direction} Entries - Volume Analysis:")
        print("-" * 80)

        if not trades:
            return

        volume_statuses = []
        volume_ratios = []

        for trade in trades:
            indicators = trade['market_state']['indicators']

            if 'volume_status' in indicators:
                volume_statuses.append(indicators['volume_status'])

            if 'volume_ratio' in indicators:
                volume_ratios.append(indicators['volume_ratio'])

        if volume_statuses:
            counter = Counter(volume_statuses)
            print(f"\nVolume Status:")
            for status, count in counter.most_common():
                print(f"  {status}: {count}/{len(volume_statuses)} ({count/len(volume_statuses)*100:.1f}%)")

        if volume_ratios:
            print(f"\nVolume Ratio (vs MA):")
            print(f"  Mean: {np.mean(volume_ratios):.2f}x")
            print(f"  Median: {np.median(volume_ratios):.2f}x")
            print(f"  Range: [{np.min(volume_ratios):.2f}x, {np.max(volume_ratios):.2f}x]")

    def find_key_discriminators(self, long_trades: List[Dict], short_trades: List[Dict]):
        """Find patterns that discriminate between long and short entries"""
        print("\nDiscovering differences between LONG and SHORT setups...")
        print("-" * 80)

        # Compare key indicators
        long_rsi = [t['market_state']['indicators'].get('rsi_14') for t in long_trades
                    if 'rsi_14' in t['market_state']['indicators']]
        short_rsi = [t['market_state']['indicators'].get('rsi_14') for t in short_trades
                     if 'rsi_14' in t['market_state']['indicators']]

        if long_rsi and short_rsi:
            print(f"\nRSI (14):")
            print(f"  LONG avg: {np.mean(long_rsi):.1f}")
            print(f"  SHORT avg: {np.mean(short_rsi):.1f}")
            print(f"  Difference: {np.mean(long_rsi) - np.mean(short_rsi):.1f}")

        # Confluence gap
        long_gaps = []
        short_gaps = []

        for t in long_trades:
            ind = t['market_state']['indicators']
            if 'confluence_score_long' in ind and 'confluence_score_short' in ind:
                gap = ind['confluence_score_long'] - ind['confluence_score_short']
                long_gaps.append(gap)

        for t in short_trades:
            ind = t['market_state']['indicators']
            if 'confluence_score_long' in ind and 'confluence_score_short' in ind:
                gap = ind['confluence_score_short'] - ind['confluence_score_long']
                short_gaps.append(gap)

        if long_gaps:
            print(f"\nConfluence Gap (favoring direction):")
            print(f"  LONG gap avg: {np.mean(long_gaps):.1f}")
            print(f"  SHORT gap avg: {np.mean(short_gaps):.1f}")

        # Stochastic
        long_stoch = [t['market_state']['indicators'].get('stoch_k') for t in long_trades
                      if 'stoch_k' in t['market_state']['indicators']]
        short_stoch = [t['market_state']['indicators'].get('stoch_k') for t in short_trades
                       if 'stoch_k' in t['market_state']['indicators']]

        if long_stoch and short_stoch:
            print(f"\nStochastic K:")
            print(f"  LONG avg: {np.mean(long_stoch):.1f}")
            print(f"  SHORT avg: {np.mean(short_stoch):.1f}")

    def generate_trading_rules(self, long_patterns: Dict, short_patterns: Dict) -> Dict:
        """
        Generate concrete trading rules based on discovered patterns

        Returns:
            Dictionary with proposed entry rules
        """
        rules = {
            'long_entry_rules': [],
            'short_entry_rules': [],
            'support_resistance_rules': [],
            'volume_rules': [],
            'general_observations': []
        }

        # Analyze long patterns
        if long_patterns:
            print("\n🟢 LONG ENTRY RULES:")
            print("-" * 80)

            # RSI rules
            if 'rsi_14' in long_patterns:
                rsi = long_patterns['rsi_14']
                rule = f"RSI(14) typically between {rsi['min']:.0f}-{rsi['max']:.0f} (avg {rsi['mean']:.0f})"
                print(f"  ✓ {rule}")
                rules['long_entry_rules'].append(rule)

            # Confluence rules
            if 'confluence_score_long' in long_patterns:
                conf = long_patterns['confluence_score_long']
                rule = f"Confluence Long score avg {conf['mean']:.0f} (min {conf['min']:.0f})"
                print(f"  ✓ {rule}")
                rules['long_entry_rules'].append(rule)

            # Stochastic rules
            if 'stoch_k' in long_patterns:
                stoch = long_patterns['stoch_k']
                rule = f"Stochastic K between {stoch['min']:.0f}-{stoch['max']:.0f} (avg {stoch['mean']:.0f})"
                print(f"  ✓ {rule}")
                rules['long_entry_rules'].append(rule)

        # Analyze short patterns
        if short_patterns:
            print("\n🔴 SHORT ENTRY RULES:")
            print("-" * 80)

            # RSI rules
            if 'rsi_14' in short_patterns:
                rsi = short_patterns['rsi_14']
                rule = f"RSI(14) typically between {rsi['min']:.0f}-{rsi['max']:.0f} (avg {rsi['mean']:.0f})"
                print(f"  ✓ {rule}")
                rules['short_entry_rules'].append(rule)

            # Confluence rules
            if 'confluence_score_short' in short_patterns:
                conf = short_patterns['confluence_score_short']
                rule = f"Confluence Short score avg {conf['mean']:.0f} (min {conf['min']:.0f})"
                print(f"  ✓ {rule}")
                rules['short_entry_rules'].append(rule)

            # Stochastic rules
            if 'stoch_k' in short_patterns:
                stoch = short_patterns['stoch_k']
                rule = f"Stochastic K between {stoch['min']:.0f}-{stoch['max']:.0f} (avg {stoch['mean']:.0f})"
                print(f"  ✓ {rule}")
                rules['short_entry_rules'].append(rule)

        # S/R rules
        print("\n📍 SUPPORT/RESISTANCE RULES:")
        print("-" * 80)

        # Check how many entries were near S/R
        at_sr_count = sum(1 for t in self.optimal_entries
                          if t['market_state']['support_resistance'].get('at_support') or
                          t['market_state']['support_resistance'].get('at_resistance'))

        total = len(self.optimal_entries)
        sr_pct = at_sr_count / total * 100 if total > 0 else 0

        rule = f"{at_sr_count}/{total} ({sr_pct:.1f}%) entries at key S/R levels"
        print(f"  ✓ {rule}")
        rules['support_resistance_rules'].append(rule)

        if sr_pct > 30:
            rule = "CRITICAL: Support/Resistance levels are VERY important in your strategy!"
            print(f"  ⚠️  {rule}")
            rules['support_resistance_rules'].append(rule)

        # Volume rules
        print("\n📈 VOLUME RULES:")
        print("-" * 80)

        volume_statuses = [t['market_state']['indicators'].get('volume_status')
                          for t in self.optimal_entries
                          if 'volume_status' in t['market_state']['indicators']]

        if volume_statuses:
            counter = Counter(volume_statuses)
            for status, count in counter.most_common():
                pct = count / len(volume_statuses) * 100
                rule = f"{status}: {count}/{len(volume_statuses)} ({pct:.1f}%)"
                print(f"  ✓ {rule}")
                rules['volume_rules'].append(rule)

        # Save rules to file
        rules_file = Path(__file__).parent / 'trading_data' / 'discovered_rules.json'
        with open(rules_file, 'w') as f:
            json.dump(rules, f, indent=2)

        print(f"\n💾 Rules saved to: {rules_file}")

        return rules


if __name__ == '__main__':
    analyzer = PatternAnalyzer()
    rules = analyzer.analyze_all()

    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE!")
    print("="*80)
    print("\nNext steps:")
    print("  1. Review the discovered patterns above")
    print("  2. Run: python generate_new_strategy.py")
    print("     This will create new entry_detector.py based on YOUR patterns!")
