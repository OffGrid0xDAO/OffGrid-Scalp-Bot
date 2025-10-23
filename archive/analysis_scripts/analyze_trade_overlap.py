#!/usr/bin/env python3
"""
Trade Overlap Analysis

Compare:
1. User's 22 optimal trades
2. New bot's 42 trades
3. Old bot's 9 trades

Find:
- Which user trades did the bot catch?
- Which user trades did the bot miss?
- Which bot trades were FALSE (user didn't take them)?
- What indicators differentiate good trades from false signals?
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class TradeOverlapAnalyzer:
    """Analyze overlap between user trades and bot trades"""

    def __init__(self):
        """Initialize analyzer"""
        self.data_dir = Path(__file__).parent / 'trading_data'

        # Load user's optimal trades
        with open(self.data_dir / 'optimal_trades.json', 'r') as f:
            user_data = json.load(f)
        self.user_trades = user_data['optimal_entries']

        # Load backtest results
        with open(self.data_dir / 'backtest_comparison.json', 'r') as f:
            self.backtest_data = json.load(f)

        # Load historical data with indicators
        self.df = pd.read_csv(self.data_dir / 'indicators' / 'eth_1h_full.csv')
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

    def find_trade_matches(self, user_trade: Dict, bot_trades: List[Dict],
                          tolerance_hours: int = 2) -> Tuple[bool, Dict]:
        """
        Find if user trade matches any bot trade within time tolerance

        Args:
            user_trade: User's trade
            bot_trades: List of bot's trades
            tolerance_hours: How close trades need to be (default 2 hours)

        Returns:
            (matched, bot_trade or None)
        """
        user_time = pd.to_datetime(user_trade['timestamp'])
        user_direction = user_trade['direction']

        for bot_trade in bot_trades:
            bot_time = pd.to_datetime(bot_trade.get('entry_time', bot_trade.get('timestamp')))
            bot_direction = bot_trade.get('direction', bot_trade.get('entry_direction'))

            # Check if within time tolerance and same direction
            time_diff = abs((user_time - bot_time).total_seconds() / 3600)

            if time_diff <= tolerance_hours and user_direction == bot_direction:
                return True, bot_trade

        return False, None

    def analyze_overlap(self):
        """Analyze overlap between user and bot trades"""
        print("\n" + "="*80)
        print("🔍 TRADE OVERLAP ANALYSIS")
        print("="*80)

        # We'll need to extract bot trades from backtest
        # For now, let's scan the new strategy signals
        print("\nScanning new strategy signals...")

        df_period = self.df[(self.df['timestamp'] >= '2025-10-05') &
                            (self.df['timestamp'] < '2025-10-22')].copy()

        # Import new detector
        import sys
        sys.path.append(str(Path(__file__).parent / 'src'))
        from strategy.entry_detector_user_pattern import EntryDetector

        detector = EntryDetector()
        df_signals = detector.scan_historical_signals(df_period)

        # Extract bot signals
        bot_signals = df_signals[df_signals['entry_signal'] == True].copy()
        bot_trades = bot_signals[['timestamp', 'close', 'entry_direction',
                                  'entry_confidence', 'entry_quality_score']].to_dict('records')

        print(f"\nFound {len(bot_trades)} bot signals")
        print(f"User took {len(self.user_trades)} trades")

        # Categorize trades
        matched_trades = []
        missed_trades = []
        false_signals = []

        # Find matches
        for user_trade in self.user_trades:
            matched, bot_trade = self.find_trade_matches(user_trade, bot_trades)

            if matched:
                matched_trades.append({
                    'user_trade': user_trade,
                    'bot_trade': bot_trade
                })
            else:
                missed_trades.append(user_trade)

        # Find false signals (bot took but user didn't)
        for bot_trade in bot_trades:
            # Check if this bot trade matches any user trade
            is_false = True
            bot_time = pd.to_datetime(bot_trade['timestamp'])

            for user_trade in self.user_trades:
                user_time = pd.to_datetime(user_trade['timestamp'])
                time_diff = abs((user_time - bot_time).total_seconds() / 3600)

                if time_diff <= 2 and bot_trade['entry_direction'] == user_trade['direction']:
                    is_false = False
                    break

            if is_false:
                false_signals.append(bot_trade)

        # Print results
        print("\n" + "="*80)
        print("📊 OVERLAP RESULTS")
        print("="*80)

        print(f"\n✅ MATCHED: {len(matched_trades)}/{len(self.user_trades)} user trades")
        print(f"⚠️  MISSED: {len(missed_trades)}/{len(self.user_trades)} user trades")
        print(f"❌ FALSE SIGNALS: {len(false_signals)} trades bot took but user didn't")

        # Analyze matched trades
        print("\n" + "="*80)
        print("✅ MATCHED TRADES (Bot caught these!)")
        print("="*80)

        for i, match in enumerate(matched_trades[:10], 1):  # Show first 10
            user_trade = match['user_trade']
            bot_trade = match['bot_trade']
            print(f"\n{i}. {user_trade['timestamp']} - {user_trade['direction'].upper()}")
            print(f"   User: ${user_trade['market_state']['ohlcv']['close']:.2f}")
            print(f"   Bot:  ${bot_trade['close']:.2f} (quality: {bot_trade['entry_quality_score']:.1f})")

        # Analyze missed trades
        print("\n" + "="*80)
        print("⚠️  MISSED TRADES (Bot should have taken these!)")
        print("="*80)

        for i, missed in enumerate(missed_trades, 1):
            print(f"\n{i}. {missed['timestamp']} - {missed['direction'].upper()}")
            print(f"   Price: ${missed['market_state']['ohlcv']['close']:.2f}")

            # Get indicator values at this time
            indicators = missed['market_state']['indicators']
            print(f"   RSI: {indicators.get('rsi_14', 'N/A'):.1f}")
            print(f"   Stoch K: {indicators.get('stoch_k', 'N/A'):.1f}")
            print(f"   Volume: {indicators.get('volume_status', 'N/A')}")
            print(f"   Confluence Long: {indicators.get('confluence_score_long', 'N/A'):.1f}")
            print(f"   Confluence Short: {indicators.get('confluence_score_short', 'N/A'):.1f}")

        # Analyze false signals
        print("\n" + "="*80)
        print("❌ FALSE SIGNALS (Bot took these, but user didn't)")
        print("="*80)
        print(f"\nTotal false signals: {len(false_signals)}")
        print("\nShowing first 10...")

        for i, false in enumerate(false_signals[:10], 1):
            print(f"\n{i}. {false['timestamp']} - {false['entry_direction'].upper()}")
            print(f"   Price: ${false['close']:.2f}")
            print(f"   Quality: {false['entry_quality_score']:.1f}")

        # Return categorized trades for further analysis
        return {
            'matched': matched_trades,
            'missed': missed_trades,
            'false_signals': false_signals,
            'bot_trades': bot_trades
        }

    def deep_indicator_analysis(self, overlap_data: Dict):
        """
        Deep dive into ALL indicators to find discriminators

        Compare indicator values between:
        1. MATCHED trades (good - bot found them)
        2. MISSED trades (bot should have found them)
        3. FALSE signals (bot shouldn't have taken them)
        """
        print("\n" + "="*80)
        print("🔬 DEEP INDICATOR ANALYSIS")
        print("="*80)

        matched = overlap_data['matched']
        missed = overlap_data['missed']
        false_signals = overlap_data['false_signals']

        print(f"\nAnalyzing {len(matched)} matched, {len(missed)} missed, {len(false_signals)} false signals")

        # Extract all indicator values for each category
        def extract_indicators(trades, source='user'):
            """Extract indicator values from trades"""
            indicators_list = []

            for trade in trades:
                if source == 'user':
                    ind = trade['market_state']['indicators'] if 'market_state' in trade else trade['user_trade']['market_state']['indicators']
                else:
                    # Get indicators from dataframe
                    timestamp = pd.to_datetime(trade['timestamp'])
                    row = self.df[self.df['timestamp'] == timestamp]
                    if len(row) > 0:
                        ind = row.iloc[0].to_dict()
                    else:
                        continue

                indicators_list.append(ind)

            return indicators_list

        # Get indicators for each category
        matched_indicators = []
        for match in matched:
            matched_indicators.append(match['user_trade']['market_state']['indicators'])

        missed_indicators = [t['market_state']['indicators'] for t in missed]

        false_indicators = extract_indicators(false_signals, source='bot')

        # Compare key indicators
        key_indicators = [
            'rsi_14', 'rsi_7',
            'stoch_k', 'stoch_d',
            'macd_histogram', 'macd_fast_value',
            'confluence_score_long', 'confluence_score_short',
            'volume_ratio', 'volume_ma_ratio',
            'bb_width', 'bb_position',
            'adx_14', 'adx_trend_strength'
        ]

        print("\n" + "="*80)
        print("📊 INDICATOR COMPARISON: MATCHED vs MISSED vs FALSE")
        print("="*80)

        for indicator in key_indicators:
            # Get values for each category
            matched_vals = [ind.get(indicator) for ind in matched_indicators
                           if indicator in ind and isinstance(ind.get(indicator), (int, float))]
            missed_vals = [ind.get(indicator) for ind in missed_indicators
                          if indicator in ind and isinstance(ind.get(indicator), (int, float))]
            false_vals = [ind.get(indicator) for ind in false_indicators
                         if indicator in ind and isinstance(ind.get(indicator), (int, float))]

            if matched_vals or missed_vals or false_vals:
                print(f"\n{indicator}:")

                if matched_vals:
                    print(f"  MATCHED (good):  avg={np.mean(matched_vals):.2f}, "
                          f"range=[{np.min(matched_vals):.2f}, {np.max(matched_vals):.2f}]")
                if missed_vals:
                    print(f"  MISSED (wanted): avg={np.mean(missed_vals):.2f}, "
                          f"range=[{np.min(missed_vals):.2f}, {np.max(missed_vals):.2f}]")
                if false_vals:
                    print(f"  FALSE (avoid):   avg={np.mean(false_vals):.2f}, "
                          f"range=[{np.min(false_vals):.2f}, {np.max(false_vals):.2f}]")

                # Calculate discrimination power
                if matched_vals and false_vals:
                    matched_avg = np.mean(matched_vals)
                    false_avg = np.mean(false_vals)
                    diff = abs(matched_avg - false_avg)

                    if diff > 5:  # Significant difference
                        print(f"  🎯 DISCRIMINATOR! Difference: {diff:.2f}")

        # Analyze categorical indicators
        print("\n" + "="*80)
        print("📊 CATEGORICAL INDICATORS")
        print("="*80)

        # Volume status
        print("\nVolume Status:")
        matched_vol = [ind.get('volume_status') for ind in matched_indicators if 'volume_status' in ind]
        missed_vol = [ind.get('volume_status') for ind in missed_indicators if 'volume_status' in ind]
        false_vol = [ind.get('volume_status') for ind in false_indicators if 'volume_status' in ind]

        if matched_vol:
            from collections import Counter
            print(f"  MATCHED: {Counter(matched_vol)}")
        if missed_vol:
            print(f"  MISSED:  {Counter(missed_vol)}")
        if false_vol:
            print(f"  FALSE:   {Counter(false_vol)}")

        # MACD trend
        print("\nMACD Trend:")
        matched_macd = [ind.get('macd_fast_trend') for ind in matched_indicators if 'macd_fast_trend' in ind]
        missed_macd = [ind.get('macd_fast_trend') for ind in missed_indicators if 'macd_fast_trend' in ind]
        false_macd = [ind.get('macd_fast_trend') for ind in false_indicators if 'macd_fast_trend' in ind]

        if matched_macd:
            from collections import Counter
            print(f"  MATCHED: {Counter(matched_macd)}")
        if missed_macd:
            print(f"  MISSED:  {Counter(missed_macd)}")
        if false_macd:
            print(f"  FALSE:   {Counter(false_macd)}")

        return {
            'matched_indicators': matched_indicators,
            'missed_indicators': missed_indicators,
            'false_indicators': false_indicators
        }


if __name__ == '__main__':
    analyzer = TradeOverlapAnalyzer()

    # Run overlap analysis
    overlap_data = analyzer.analyze_overlap()

    # Run deep indicator analysis
    indicator_analysis = analyzer.deep_indicator_analysis(overlap_data)

    # Save results
    results_file = Path(__file__).parent / 'trading_data' / 'overlap_analysis.json'

    results = {
        'summary': {
            'total_user_trades': len(analyzer.user_trades),
            'total_bot_trades': len(overlap_data['bot_trades']),
            'matched_count': len(overlap_data['matched']),
            'missed_count': len(overlap_data['missed']),
            'false_signals_count': len(overlap_data['false_signals'])
        },
        'match_rate': len(overlap_data['matched']) / len(analyzer.user_trades) * 100,
        'false_signal_rate': len(overlap_data['false_signals']) / len(overlap_data['bot_trades']) * 100,
        'generated_at': datetime.now().isoformat()
    }

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}")

    print("\n" + "="*80)
    print("✅ OVERLAP ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nMatch Rate: {results['match_rate']:.1f}% of user trades")
    print(f"False Signal Rate: {results['false_signal_rate']:.1f}% of bot trades")

    print("\n📊 Next step: Generate comparison charts")
    print("   Run: python generate_comparison_charts.py")
