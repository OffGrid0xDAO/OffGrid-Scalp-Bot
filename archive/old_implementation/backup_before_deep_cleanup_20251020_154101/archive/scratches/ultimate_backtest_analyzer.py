#!/usr/bin/env python3
"""
Ultimate Backtester + Strategy Optimizer

Combines:
1. Historical EMA backtest
2. Claude decision analysis
3. EMA correlation with price movements
4. Wick detection optimization
5. Market regime detection (bullish/bearish/ranging)
6. Automatic prompt generation

Output: Optimal trading prompt based on ALL learned patterns
"""

import pandas as pd
import json
import csv
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from typing import Dict, List, Tuple, Optional


class UltimateStrategyAnalyzer:
    def __init__(self,
                 data_5min_file='trading_data/ema_data_5min.csv',
                 data_15min_file='trading_data/ema_data_15min.csv',
                 claude_decisions_file='trading_data/claude_decisions.csv'):

        self.data_5min_file = data_5min_file
        self.data_15min_file = data_15min_file
        self.claude_decisions_file = claude_decisions_file

        # Data storage
        self.df_5min = None
        self.df_15min = None
        self.claude_decisions = []

        # Analysis results
        self.market_regimes = []  # Bullish, bearish, ranging periods
        self.ema_correlations = {}
        self.wick_patterns = []
        self.winning_patterns = []
        self.losing_patterns = []

        # Strategy recommendations
        self.optimal_filters = {}
        self.optimal_hold_times = {}
        self.regime_specific_rules = {}

    def load_all_data(self):
        """Load all data sources"""
        print("📊 Loading data...")

        # Load EMA data
        self.df_5min = pd.read_csv(self.data_5min_file)
        self.df_5min['timestamp'] = pd.to_datetime(self.df_5min['timestamp'])

        self.df_15min = pd.read_csv(self.data_15min_file)
        self.df_15min['timestamp'] = pd.to_datetime(self.df_15min['timestamp'])

        print(f"✅ Loaded {len(self.df_5min)} rows from 5min data")
        print(f"✅ Loaded {len(self.df_15min)} rows from 15min data")

        # Load Claude decisions if available
        try:
            with open(self.claude_decisions_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.claude_decisions.append({
                        'timestamp': datetime.fromisoformat(row['timestamp']),
                        'direction': row.get('direction', ''),
                        'entry_recommended': row.get('entry_recommended', ''),
                        'confidence': float(row.get('confidence', 0)),
                        'entry_price': float(row.get('entry_price', 0)),
                        'executed': row.get('executed', 'False').lower() == 'true',
                        'reasoning': row.get('reasoning', '')
                    })
            print(f"✅ Loaded {len(self.claude_decisions)} Claude decisions")
        except FileNotFoundError:
            print("⚠️  No Claude decisions found, skipping that analysis")

    def detect_market_regimes(self):
        """
        Detect market regimes: bullish trend, bearish trend, ranging

        Key insight: Strategy changes based on regime!
        - Bullish: Look for dips (wicks down) for LONG
        - Bearish: Look for pumps (wicks up) for SHORT
        - Ranging: Avoid or use mean reversion
        """
        print("\n🔍 Detecting market regimes...")

        regimes = []

        # Analyze 30-minute windows
        for i in range(30, len(self.df_5min)):
            window = self.df_5min.iloc[i-30:i]

            current_price = window.iloc[-1]['price']
            start_price = window.iloc[0]['price']

            high_price = window['price'].max()
            low_price = window['price'].min()

            # Calculate move
            pct_change = ((current_price - start_price) / start_price * 100)
            range_pct = ((high_price - low_price) / low_price * 100)

            # Determine regime
            regime = None
            if pct_change > 0.5 and range_pct > 0.8:
                regime = 'BULLISH_TRENDING'
            elif pct_change < -0.5 and range_pct > 0.8:
                regime = 'BEARISH_TRENDING'
            elif range_pct > 0.8:
                regime = 'RANGING_VOLATILE'
            else:
                regime = 'RANGING_QUIET'

            regimes.append({
                'timestamp': window.iloc[-1]['timestamp'],
                'regime': regime,
                'pct_change': pct_change,
                'range_pct': range_pct,
                'price': current_price
            })

        self.market_regimes = regimes

        # Summary
        regime_counts = defaultdict(int)
        for r in regimes:
            regime_counts[r['regime']] += 1

        print(f"📊 Market Regime Distribution:")
        for regime, count in regime_counts.items():
            pct = count / len(regimes) * 100
            print(f"   {regime}: {count} periods ({pct:.1f}%)")

        return regimes

    def analyze_wick_patterns(self):
        """
        Analyze wick patterns in different market regimes

        Key insight from user: "In bullish movement, wicks DOWN below all EMAs = perfect LONG entry"
        """
        print("\n🕯️  Analyzing wick patterns by market regime...")

        wick_opportunities = []

        for i in range(1, len(self.df_5min) - 20):  # Need 20 candles ahead to see result
            current = self.df_5min.iloc[i]
            previous = self.df_5min.iloc[i-1]

            # Get EMA values
            ema_values = []
            for col in current.index:
                if col.startswith('MMA') and col != 'timestamp' and col != 'price' and col != 'state':
                    try:
                        val = float(current[col])
                        if val > 0:
                            ema_values.append(val)
                    except:
                        continue

            if len(ema_values) < 5:
                continue

            price = current['price']
            lowest_ema = min(ema_values)
            highest_ema = max(ema_values)

            # Detect wick BELOW all EMAs (price dropped below lowest EMA)
            wick_below_pct = ((lowest_ema - price) / lowest_ema * 100) if price < lowest_ema else 0

            # Detect wick ABOVE all EMAs (price pumped above highest EMA)
            wick_above_pct = ((price - highest_ema) / highest_ema * 100) if price > highest_ema else 0

            # Find current market regime
            regime_now = None
            for regime in self.market_regimes:
                if abs((regime['timestamp'] - current['timestamp']).total_seconds()) < 300:  # Within 5 min
                    regime_now = regime['regime']
                    break

            # USER INSIGHT: "In bullish movement, when we wick DOWN below all EMAs, that's perfect LONG entry"
            # This is a liquidity grab/stop hunt that reverses quickly

            # Check if significant wick (0.2-1.2% for better detection)
            if wick_below_pct >= 0.2 and wick_below_pct <= 1.2:
                # Wick DOWN detected
                # Check recovery
                prev_price = previous['price']
                recovering = price > prev_price

                if recovering:
                    # Simulate LONG entry
                    entry_price = price

                    # Check what happened in next 20 candles (20 minutes)
                    future_prices = []
                    for j in range(i+1, min(i+21, len(self.df_5min))):
                        future_prices.append(self.df_5min.iloc[j]['price'])

                    if future_prices:
                        max_profit = max([(p - entry_price) / entry_price * 100 for p in future_prices])
                        min_profit = min([(p - entry_price) / entry_price * 100 for p in future_prices])

                        # Check profit at different hold times
                        profit_5min = (future_prices[4] - entry_price) / entry_price * 100 if len(future_prices) > 4 else 0
                        profit_10min = (future_prices[9] - entry_price) / entry_price * 100 if len(future_prices) > 9 else 0
                        profit_15min = (future_prices[14] - entry_price) / entry_price * 100 if len(future_prices) > 14 else 0
                        profit_20min = (future_prices[19] - entry_price) / entry_price * 100 if len(future_prices) > 19 else 0

                        wick_opportunities.append({
                            'timestamp': current['timestamp'],
                            'type': 'WICK_DOWN_LONG',
                            'regime': regime_now,
                            'wick_size': wick_below_pct,
                            'entry_price': entry_price,
                            'max_profit_20min': max_profit,
                            'max_loss_20min': min_profit,
                            'profit_5min': profit_5min,
                            'profit_10min': profit_10min,
                            'profit_15min': profit_15min,
                            'profit_20min': profit_20min,
                            'winner': max_profit > 0.3
                        })

            elif wick_above_pct >= 0.2 and wick_above_pct <= 1.2:
                # Wick UP detected
                prev_price = previous['price']
                recovering = price < prev_price

                if recovering:
                    # Simulate SHORT entry
                    entry_price = price

                    future_prices = []
                    for j in range(i+1, min(i+21, len(self.df_5min))):
                        future_prices.append(self.df_5min.iloc[j]['price'])

                    if future_prices:
                        max_profit = max([(entry_price - p) / entry_price * 100 for p in future_prices])
                        min_profit = min([(entry_price - p) / entry_price * 100 for p in future_prices])

                        profit_5min = (entry_price - future_prices[4]) / entry_price * 100 if len(future_prices) > 4 else 0
                        profit_10min = (entry_price - future_prices[9]) / entry_price * 100 if len(future_prices) > 9 else 0
                        profit_15min = (entry_price - future_prices[14]) / entry_price * 100 if len(future_prices) > 14 else 0
                        profit_20min = (entry_price - future_prices[19]) / entry_price * 100 if len(future_prices) > 19 else 0

                        wick_opportunities.append({
                            'timestamp': current['timestamp'],
                            'type': 'WICK_UP_SHORT',
                            'regime': regime_now,
                            'wick_size': wick_above_pct,
                            'entry_price': entry_price,
                            'max_profit_20min': max_profit,
                            'max_loss_20min': min_profit,
                            'profit_5min': profit_5min,
                            'profit_10min': profit_10min,
                            'profit_15min': profit_15min,
                            'profit_20min': profit_20min,
                            'winner': max_profit > 0.3
                        })

        self.wick_patterns = wick_opportunities

        # Analyze by regime
        print(f"\n🕯️  Found {len(wick_opportunities)} wick opportunities")

        regime_performance = defaultdict(lambda: {'count': 0, 'winners': 0, 'total_profit': 0})

        for opp in wick_opportunities:
            regime = opp['regime'] or 'UNKNOWN'
            regime_performance[regime]['count'] += 1
            if opp['winner']:
                regime_performance[regime]['winners'] += 1
            regime_performance[regime]['total_profit'] += opp['max_profit_20min']

        print(f"\n📊 Wick Performance by Market Regime:")
        for regime, stats in regime_performance.items():
            wr = (stats['winners'] / stats['count'] * 100) if stats['count'] > 0 else 0
            avg_profit = (stats['total_profit'] / stats['count']) if stats['count'] > 0 else 0
            print(f"   {regime}:")
            print(f"      Opportunities: {stats['count']}")
            print(f"      Win Rate: {wr:.1f}%")
            print(f"      Avg Max Profit: {avg_profit:+.3f}%")

        return wick_opportunities

    def analyze_ema_correlations(self):
        """
        Analyze correlation between EMA states and price movements

        Find: Which EMA combinations predict profitable moves?
        """
        print("\n📈 Analyzing EMA correlations with price movements...")

        correlations = {
            'all_green_then_rise': [],
            'all_red_then_fall': [],
            'mixed_green_performance': [],
            'mixed_red_performance': [],
            'ema_spread_vs_momentum': []
        }

        for i in range(0, len(self.df_5min) - 20):
            current = self.df_5min.iloc[i]
            state = current.get('state', '')
            price_now = current['price']

            # Get future price (20 minutes ahead)
            future = self.df_5min.iloc[min(i+20, len(self.df_5min)-1)]
            price_future = future['price']

            pct_change = (price_future - price_now) / price_now * 100

            # Track by state
            if 'all_green' in state.lower():
                correlations['all_green_then_rise'].append(pct_change)
            elif 'all_red' in state.lower():
                correlations['all_red_then_fall'].append(pct_change)
            elif 'mixed_green' in state.lower():
                correlations['mixed_green_performance'].append(pct_change)
            elif 'mixed_red' in state.lower():
                correlations['mixed_red_performance'].append(pct_change)

        self.ema_correlations = correlations

        # Print analysis
        print(f"\n📊 EMA State → Price Movement Correlation:")
        print(f"\n   ALL_GREEN → Future 20min:")
        if correlations['all_green_then_rise']:
            avg = statistics.mean(correlations['all_green_then_rise'])
            positive_pct = len([x for x in correlations['all_green_then_rise'] if x > 0]) / len(correlations['all_green_then_rise']) * 100
            print(f"      Avg change: {avg:+.3f}%")
            print(f"      Positive rate: {positive_pct:.1f}%")

        print(f"\n   ALL_RED → Future 20min:")
        if correlations['all_red_then_fall']:
            avg = statistics.mean(correlations['all_red_then_fall'])
            negative_pct = len([x for x in correlations['all_red_then_fall'] if x < 0]) / len(correlations['all_red_then_fall']) * 100
            print(f"      Avg change: {avg:+.3f}%")
            print(f"      Negative rate: {negative_pct:.1f}%")

        print(f"\n   MIXED_GREEN → Future 20min:")
        if correlations['mixed_green_performance']:
            avg = statistics.mean(correlations['mixed_green_performance'])
            positive_pct = len([x for x in correlations['mixed_green_performance'] if x > 0]) / len(correlations['mixed_green_performance']) * 100
            print(f"      Avg change: {avg:+.3f}%")
            print(f"      Positive rate: {positive_pct:.1f}%")

        return correlations

    def analyze_claude_decisions(self):
        """
        Analyze Claude's actual decisions against optimal patterns
        """
        if not self.claude_decisions:
            print("\n⚠️  No Claude decisions to analyze")
            return

        print(f"\n🤖 Analyzing {len(self.claude_decisions)} Claude decisions...")

        executed_trades = [d for d in self.claude_decisions if d['executed']]

        if not executed_trades:
            print("⚠️  No executed trades found")
            return

        print(f"✅ {len(executed_trades)} trades executed")

        # Match trades with market regimes
        regime_matched_trades = []
        for trade in executed_trades:
            regime = None
            for r in self.market_regimes:
                if abs((r['timestamp'] - trade['timestamp']).total_seconds()) < 300:
                    regime = r['regime']
                    break

            regime_matched_trades.append({
                **trade,
                'regime': regime
            })

        # Analyze by regime
        regime_performance = defaultdict(lambda: {'count': 0, 'total': 0})

        for trade in regime_matched_trades:
            regime = trade['regime'] or 'UNKNOWN'
            regime_performance[regime]['count'] += 1
            regime_performance[regime]['total'] += 1

        print(f"\n📊 Claude's Trading by Market Regime:")
        for regime, stats in regime_performance.items():
            print(f"   {regime}: {stats['count']} trades")

        return regime_matched_trades

    def generate_optimal_strategy(self):
        """
        Generate optimal trading strategy based on ALL analysis
        """
        print("\n🎯 Generating optimal strategy...")

        strategy = {
            'market_regime_rules': {},
            'wick_rules': {},
            'ema_rules': {},
            'risk_management': {},
            'hold_times': {}
        }

        # Analyze wick performance by regime
        wick_by_regime = defaultdict(lambda: {'long': [], 'short': []})

        for wick in self.wick_patterns:
            regime = wick['regime'] or 'UNKNOWN'
            if wick['type'] == 'WICK_DOWN_LONG':
                wick_by_regime[regime]['long'].append(wick)
            else:
                wick_by_regime[regime]['short'].append(wick)

        # Generate regime-specific rules
        for regime, wicks in wick_by_regime.items():
            long_wicks = wicks['long']
            short_wicks = wicks['short']

            long_wr = (len([w for w in long_wicks if w['winner']]) / len(long_wicks) * 100) if long_wicks else 0
            short_wr = (len([w for w in short_wicks if w['winner']]) / len(short_wicks) * 100) if short_wicks else 0

            strategy['market_regime_rules'][regime] = {
                'long_wick_winrate': long_wr,
                'short_wick_winrate': short_wr,
                'long_sample_size': len(long_wicks),
                'short_sample_size': len(short_wicks),
                'recommendation': self._get_regime_recommendation(regime, long_wr, short_wr)
            }

        # Optimal hold times
        hold_time_analysis = self._analyze_optimal_hold_times()
        strategy['hold_times'] = hold_time_analysis

        # EMA rules
        strategy['ema_rules'] = self._generate_ema_rules()

        self.optimal_filters = strategy
        return strategy

    def _get_regime_recommendation(self, regime: str, long_wr: float, short_wr: float) -> str:
        """
        Generate regime-specific recommendation

        KEY INSIGHT FROM USER:
        "In bullish movement, when price wicks DOWN below all EMAs with great percentage,
         that's the PERFECT entry for LONG. Once tendency changes, this is no longer valid."
        """
        if 'BULLISH' in regime:
            if long_wr > 60:
                return ("STRONG: In BULLISH regime, wicks DOWN below all EMAs are BEST LONG entries! "
                        "This is whales grabbing liquidity before continuing up. "
                        "AVOID SHORT entirely. Win rate: " + f"{long_wr:.1f}%")
            elif long_wr > 50:
                return ("MODERATE: LONG entries on wick downs work well in bullish. "
                        "Be cautious with SHORT (counter-trend). Win rate: " + f"{long_wr:.1f}%")
            elif long_wr > 0:
                return ("WEAK: LONG wick entries underperforming even in bullish. "
                        "Wait for stronger signals or regime confirmation. Win rate: " + f"{long_wr:.1f}%")
            else:
                return ("NO DATA: No LONG wick samples in BULLISH regime. "
                        "Monitor and take first clear wick down opportunity.")

        elif 'BEARISH' in regime:
            if short_wr > 60:
                return ("STRONG: In BEARISH regime, wicks UP above all EMAs are BEST SHORT entries! "
                        "This is whales grabbing liquidity before continuing down. "
                        "AVOID LONG entirely. Win rate: " + f"{short_wr:.1f}%")
            elif short_wr > 50:
                return ("MODERATE: SHORT entries on wick ups work well in bearish. "
                        "Be cautious with LONG (counter-trend). Win rate: " + f"{short_wr:.1f}%")
            elif short_wr > 0:
                return ("WEAK: SHORT wick entries underperforming even in bearish. "
                        "Wait for stronger signals or regime confirmation. Win rate: " + f"{short_wr:.1f}%")
            else:
                return ("NO DATA: No SHORT wick samples in BEARISH regime. "
                        "Monitor and take first clear wick up opportunity.")

        else:  # RANGING
            if long_wr > 55 and short_wr > 55:
                return ("BOTH: Ranging market - take wick reversals in both directions. "
                        "LONG: " + f"{long_wr:.1f}%, SHORT: {short_wr:.1f}%")
            elif long_wr > short_wr + 10:
                return ("LONG BIAS: Favor LONG entries on wicks down in ranging market. "
                        "LONG: " + f"{long_wr:.1f}% vs SHORT: {short_wr:.1f}%")
            elif short_wr > long_wr + 10:
                return ("SHORT BIAS: Favor SHORT entries on wicks up in ranging market. "
                        "SHORT: " + f"{short_wr:.1f}% vs LONG: {long_wr:.1f}%")
            else:
                return ("CAUTION: Low win rates in ranging market. "
                        "LONG: " + f"{long_wr:.1f}%, SHORT: {short_wr:.1f}%. "
                        "Reduce size or skip until clear trend emerges.")

    def _analyze_optimal_hold_times(self) -> Dict:
        """Analyze which hold times work best"""
        hold_times = {
            '5min': [],
            '10min': [],
            '15min': [],
            '20min': []
        }

        for wick in self.wick_patterns:
            hold_times['5min'].append(wick['profit_5min'])
            hold_times['10min'].append(wick['profit_10min'])
            hold_times['15min'].append(wick['profit_15min'])
            hold_times['20min'].append(wick['profit_20min'])

        results = {}
        for duration, profits in hold_times.items():
            if profits:
                avg_profit = statistics.mean(profits)
                win_rate = len([p for p in profits if p > 0.3]) / len(profits) * 100
                results[duration] = {
                    'avg_profit': avg_profit,
                    'win_rate': win_rate
                }

        return results

    def _generate_ema_rules(self) -> Dict:
        """Generate EMA-based rules"""
        rules = {}

        # Analyze ALL_GREEN performance
        if self.ema_correlations.get('all_green_then_rise'):
            changes = self.ema_correlations['all_green_then_rise']
            avg = statistics.mean(changes)
            positive_rate = len([x for x in changes if x > 0]) / len(changes) * 100

            rules['all_green'] = {
                'avg_future_change': avg,
                'positive_rate': positive_rate,
                'recommendation': 'STRONG LONG' if positive_rate > 60 else 'MODERATE LONG' if positive_rate > 50 else 'WEAK'
            }

        # Analyze ALL_RED performance
        if self.ema_correlations.get('all_red_then_fall'):
            changes = self.ema_correlations['all_red_then_fall']
            avg = statistics.mean(changes)
            negative_rate = len([x for x in changes if x < 0]) / len(changes) * 100

            rules['all_red'] = {
                'avg_future_change': avg,
                'negative_rate': negative_rate,
                'recommendation': 'STRONG SHORT' if negative_rate > 60 else 'MODERATE SHORT' if negative_rate > 50 else 'WEAK'
            }

        return rules

    def generate_prompt(self) -> str:
        """
        Generate optimal Claude prompt based on all analysis
        """
        print("\n✍️  Generating optimal Claude prompt...")

        prompt = """# OPTIMAL TRADING STRATEGY - Data-Driven & Regime-Adaptive

## 🚨 CRITICAL INSIGHT: REGIME-ADAPTIVE STRATEGY

**THE STRATEGY CHANGES COMPLETELY BASED ON MARKET REGIME!**

### KEY PRINCIPLE (FROM REAL TRADING DATA):

**BULLISH REGIME:**
- When market is trending UP, wicks DOWN below all EMAs = PERFECT LONG entry
- This is whales/smart money grabbing liquidity (stop hunting) before continuing up
- Price recovers FAST → Great scalping opportunity
- **AVOID SHORT in bullish** (counter-trend = low win rate)

**BEARISH REGIME:**
- When market is trending DOWN, wicks UP above all EMAs = PERFECT SHORT entry
- This is whales grabbing liquidity (stop hunting) before continuing down
- Price reverses FAST → Great scalping opportunity
- **AVOID LONG in bearish** (counter-trend = low win rate)

**RANGING REGIME:**
- Both directions can work (mean reversion)
- BUT: Win rates typically lower
- Reduce position size or wait for clear trend

**ONCE TENDENCY CHANGES, THE STRATEGY CHANGES!** ← Monitor regime constantly

---

## 📊 YOUR DATA - MARKET REGIME PERFORMANCE

"""

        # Add regime-specific rules
        for regime, rules in self.optimal_filters['market_regime_rules'].items():
            prompt += f"\n### {regime}:\n"
            prompt += f"- LONG wick win rate: {rules['long_wick_winrate']:.1f}% ({rules['long_sample_size']} samples)\n"
            prompt += f"- SHORT wick win rate: {rules['short_wick_winrate']:.1f}% ({rules['short_sample_size']} samples)\n"
            prompt += f"- **STRATEGY: {rules['recommendation']}**\n"

        prompt += "\n## 🕯️  WICK-BASED ENTRIES (HIGHEST PRIORITY!)\n\n"
        prompt += "**Wick detection is your BEST edge:**\n\n"

        # Add hold time recommendations
        prompt += "\n## ⏱️  OPTIMAL HOLD TIMES\n\n"
        prompt += "Based on backtest analysis:\n\n"

        for duration, stats in self.optimal_filters['hold_times'].items():
            prompt += f"- **{duration}**: {stats['win_rate']:.1f}% WR | Avg P&L: {stats['avg_profit']:+.3f}%\n"

        # Find best hold time
        best_hold = max(self.optimal_filters['hold_times'].items(),
                       key=lambda x: x[1]['win_rate'])

        prompt += f"\n**RECOMMENDED HOLD TIME: {best_hold[0]}** (highest win rate: {best_hold[1]['win_rate']:.1f}%)\n"

        prompt += "\n## 📈 EMA STATE RULES\n\n"

        for state, rules in self.optimal_filters['ema_rules'].items():
            prompt += f"\n### {state.upper()}:\n"
            prompt += f"- Future 20min avg change: {rules['avg_future_change']:+.3f}%\n"
            if 'positive_rate' in rules:
                prompt += f"- Positive rate: {rules['positive_rate']:.1f}%\n"
            if 'negative_rate' in rules:
                prompt += f"- Negative rate: {rules['negative_rate']:.1f}%\n"
            prompt += f"- **Action: {rules['recommendation']}**\n"

        prompt += "\n## 🎯 ENTRY CHECKLIST\n\n"
        prompt += "**Before entering ANY trade:**\n\n"
        prompt += "1. ✅ Identify current market regime (bullish/bearish/ranging)\n"
        prompt += "2. ✅ Check for wick signal (0.3-0.8% outside ribbon)\n"
        prompt += "3. ✅ Confirm wick direction matches regime strategy\n"
        prompt += "4. ✅ Verify EMA state aligns with direction\n"
        prompt += "5. ✅ Ensure timeframes agree (5min + 15min)\n"
        prompt += f"6. ✅ Plan to hold {best_hold[0]} (don't exit early!)\n"

        prompt += "\n## 🚫 AVOID THESE MISTAKES\n\n"
        prompt += "❌ Entering without wick signal in trending markets\n"
        prompt += "❌ Going LONG in bearish regime (or SHORT in bullish)\n"
        prompt += f"❌ Exiting before {best_hold[0]} unless TP/SL hit\n"
        prompt += "❌ Trading with conflicting timeframes\n"
        prompt += "❌ Ignoring market regime changes\n"

        prompt += "\n## 💰 RISK MANAGEMENT\n\n"
        prompt += "- **Take Profit:** 1.5% minimum\n"
        prompt += "- **Stop Loss:** 0.8-1.0% (based on volatility)\n"
        prompt += f"- **Hold Duration:** {best_hold[0]} target\n"
        prompt += "- **Position Size:** Conservative until 60%+ WR proven\n"

        return prompt

    def run_complete_analysis(self):
        """Run all analysis steps"""
        print("="*80)
        print("🚀 ULTIMATE STRATEGY ANALYZER")
        print("="*80)

        # Load data
        self.load_all_data()

        # Run analyses
        self.detect_market_regimes()
        self.analyze_wick_patterns()
        self.analyze_ema_correlations()
        self.analyze_claude_decisions()

        # Generate strategy
        strategy = self.generate_optimal_strategy()

        # Generate prompt
        optimal_prompt = self.generate_prompt()

        # Save results
        self.save_results(strategy, optimal_prompt)

        print("\n" + "="*80)
        print("✅ ANALYSIS COMPLETE!")
        print("="*80)

        return strategy, optimal_prompt

    def save_results(self, strategy: Dict, prompt: str):
        """Save all results to files"""

        # Save strategy JSON
        with open('optimal_strategy.json', 'w') as f:
            # Convert to JSON-serializable format
            strategy_json = {}
            for key, value in strategy.items():
                strategy_json[key] = value
            json.dump(strategy_json, f, indent=2)

        print(f"\n💾 Saved optimal_strategy.json")

        # Save optimal prompt
        with open('OPTIMAL_CLAUDE_PROMPT.md', 'w') as f:
            f.write(prompt)

        print(f"💾 Saved OPTIMAL_CLAUDE_PROMPT.md")

        # Save detailed report
        self.generate_detailed_report()

    def generate_detailed_report(self):
        """Generate comprehensive analysis report"""

        report = "# Ultimate Strategy Analysis Report\n\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        report += "## 📊 Data Summary\n\n"
        report += f"- 5-minute candles: {len(self.df_5min)}\n"
        report += f"- 15-minute candles: {len(self.df_15min)}\n"
        report += f"- Market regimes detected: {len(self.market_regimes)}\n"
        report += f"- Wick opportunities found: {len(self.wick_patterns)}\n"
        report += f"- Claude decisions analyzed: {len(self.claude_decisions)}\n"

        report += "\n## 🕯️  Wick Pattern Analysis\n\n"

        # Group wicks by type and regime
        wick_groups = defaultdict(list)
        for wick in self.wick_patterns:
            key = f"{wick['type']}_{wick['regime']}"
            wick_groups[key].append(wick)

        report += "### Performance by Wick Type and Market Regime:\n\n"
        for key, wicks in sorted(wick_groups.items()):
            winners = [w for w in wicks if w['winner']]
            wr = len(winners) / len(wicks) * 100 if wicks else 0
            avg_profit = statistics.mean([w['max_profit_20min'] for w in wicks]) if wicks else 0

            report += f"#### {key}:\n"
            report += f"- Opportunities: {len(wicks)}\n"
            report += f"- Win Rate: {wr:.1f}%\n"
            report += f"- Avg Max Profit (20min): {avg_profit:+.3f}%\n"
            report += f"- Winners: {len(winners)}\n"
            report += f"- Losers: {len(wicks) - len(winners)}\n\n"

        report += "\n## 📈 EMA Correlation Analysis\n\n"

        for state, changes in self.ema_correlations.items():
            if changes:
                avg = statistics.mean(changes)
                median = statistics.median(changes)
                positive_pct = len([x for x in changes if x > 0]) / len(changes) * 100

                report += f"### {state}:\n"
                report += f"- Sample size: {len(changes)}\n"
                report += f"- Avg 20min change: {avg:+.3f}%\n"
                report += f"- Median 20min change: {median:+.3f}%\n"
                report += f"- Positive rate: {positive_pct:.1f}%\n\n"

        report += "\n## 🎯 Key Insights\n\n"

        # Find best performing patterns
        best_wick_pattern = max(wick_groups.items(),
                               key=lambda x: len([w for w in x[1] if w['winner']]) / len(x[1]) if x[1] else 0)

        report += f"### Best Wick Pattern:\n"
        report += f"**{best_wick_pattern[0]}**\n"
        wr = len([w for w in best_wick_pattern[1] if w['winner']]) / len(best_wick_pattern[1]) * 100
        report += f"- Win Rate: {wr:.1f}%\n"
        report += f"- Sample Size: {len(best_wick_pattern[1])}\n"

        # Save report
        with open('ULTIMATE_ANALYSIS_REPORT.md', 'w') as f:
            f.write(report)

        print(f"💾 Saved ULTIMATE_ANALYSIS_REPORT.md")


def main():
    analyzer = UltimateStrategyAnalyzer()
    strategy, prompt = analyzer.run_complete_analysis()

    print("\n" + "="*80)
    print("📄 OPTIMAL PROMPT PREVIEW:")
    print("="*80)
    print(prompt[:500] + "...\n")
    print("(Full prompt saved to OPTIMAL_CLAUDE_PROMPT.md)")
    print("="*80)


if __name__ == "__main__":
    main()
