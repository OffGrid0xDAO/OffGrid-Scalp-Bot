#!/usr/bin/env python3
"""
Optimal Trades Data Collection System

Interactive script to collect YOUR expert trade examples.
These become the ground truth for discovering winning patterns.

Usage:
    python regenerate_optimal_trades.py

Process:
    1. You describe optimal entry opportunities (timestamp, direction, reason)
    2. Script captures complete market state at that moment
    3. Calculates ALL indicators at entry point
    4. Detects support/resistance levels
    5. Stores everything for pattern analysis

This creates the training data for reverse-engineering your expertise!
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from indicators.indicator_pipeline import IndicatorPipeline


class OptimalTradesCollector:
    """
    Collect optimal trade examples and capture market state
    """

    def __init__(self):
        """Initialize collector"""
        self.data_dir = Path(__file__).parent / 'trading_data'
        self.output_file = self.data_dir / 'optimal_trades.json'
        self.indicator_pipeline = IndicatorPipeline()

        # Load existing optimal trades if any
        self.optimal_trades = self._load_existing_trades()

    def _load_existing_trades(self) -> dict:
        """Load existing optimal trades from file"""
        if self.output_file.exists():
            with open(self.output_file, 'r') as f:
                return json.load(f)
        else:
            return {
                'optimal_entries': [],
                'missed_opportunities': [],
                'false_signals_bot_took': [],
                'metadata': {
                    'created': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'total_examples': 0
                }
            }

    def _save_trades(self):
        """Save optimal trades to file"""
        self.optimal_trades['metadata']['last_updated'] = datetime.now().isoformat()
        self.optimal_trades['metadata']['total_examples'] = (
            len(self.optimal_trades['optimal_entries']) +
            len(self.optimal_trades['missed_opportunities']) +
            len(self.optimal_trades['false_signals_bot_took'])
        )

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, 'w') as f:
            json.dump(self.optimal_trades, f, indent=2)

        print(f"\n💾 Saved to: {self.output_file}")
        print(f"   Total examples: {self.optimal_trades['metadata']['total_examples']}")

    def load_historical_data(self, symbol: str = 'ETH', timeframe: str = '1h') -> pd.DataFrame:
        """
        Load historical data with indicators

        Args:
            symbol: Trading symbol (default ETH)
            timeframe: Timeframe (default 1h)

        Returns:
            DataFrame with OHLCV + all indicators
        """
        # Try to load pre-calculated indicators first
        indicator_file = self.data_dir / 'indicators' / f'{symbol.lower()}_{timeframe}_full.csv'

        if indicator_file.exists():
            print(f"📊 Loading data with indicators: {indicator_file}")
            df = pd.read_csv(indicator_file)

            # Convert timestamp to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            print(f"   Loaded {len(df)} candles")
            print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            return df
        else:
            print(f"❌ Indicator file not found: {indicator_file}")
            print("   Please run: python scripts/process_indicators.py first")
            sys.exit(1)

    def find_candle_by_timestamp(self, df: pd.DataFrame, timestamp_str: str) -> tuple:
        """
        Find candle closest to given timestamp

        Args:
            df: DataFrame with timestamp column
            timestamp_str: Timestamp string (various formats accepted)

        Returns:
            (index, row) tuple of closest candle, or (None, None) if not found
        """
        try:
            # Parse timestamp (flexible formats)
            target_time = pd.to_datetime(timestamp_str)

            # Find closest timestamp
            time_diff = abs(df['timestamp'] - target_time)
            closest_idx = time_diff.idxmin()
            closest_row = df.loc[closest_idx]

            time_delta = time_diff.min()

            print(f"\n🎯 Found candle at: {closest_row['timestamp']}")
            print(f"   Time difference: {time_delta}")
            print(f"   Price: ${closest_row['close']:.2f}")

            return closest_idx, closest_row

        except Exception as e:
            print(f"❌ Error parsing timestamp '{timestamp_str}': {e}")
            return None, None

    def capture_market_state(self, df: pd.DataFrame, idx: int, window_before: int = 50) -> dict:
        """
        Capture complete market state at a specific moment

        Args:
            df: Full DataFrame with indicators
            idx: Index of the entry candle
            window_before: How many candles before to include in context

        Returns:
            Dictionary with complete market state snapshot
        """
        if idx < window_before:
            print(f"⚠️  Warning: Only {idx} candles before this point, using all available")
            window_before = idx

        # Get the specific candle
        candle = df.loc[idx]

        # Get context window (candles before)
        context_start = max(0, idx - window_before)
        context_df = df.loc[context_start:idx]

        # Capture all available indicators at this moment
        state = {
            'timestamp': str(candle['timestamp']),
            'candle_index': int(idx),

            # Price action
            'ohlcv': {
                'open': float(candle['open']),
                'high': float(candle['high']),
                'low': float(candle['low']),
                'close': float(candle['close']),
                'volume': float(candle['volume'])
            },

            # All indicator values at this moment
            'indicators': {},

            # Context: recent price action
            'context': {
                'recent_high_50': float(context_df['high'].max()),
                'recent_low_50': float(context_df['low'].min()),
                'price_range_50': float((context_df['high'].max() - context_df['low'].min()) / context_df['low'].min() * 100),
                'avg_volume_20': float(context_df['volume'].tail(20).mean()),
            },

            # Support/Resistance levels (will add this)
            'support_resistance': self._detect_support_resistance(context_df, candle['close'])
        }

        # Capture ALL indicator columns
        for col in df.columns:
            if col not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
                value = candle.get(col)
                if pd.notna(value):  # Only include non-NaN values
                    state['indicators'][col] = float(value) if isinstance(value, (int, float, np.number)) else str(value)

        return state

    def _detect_support_resistance(self, context_df: pd.DataFrame, current_price: float) -> dict:
        """
        Detect support and resistance levels from recent price action

        Simple method:
        1. Find local highs (resistance)
        2. Find local lows (support)
        3. Calculate distance from current price
        4. Count how many times levels were tested

        Args:
            context_df: DataFrame of recent candles
            current_price: Current price to measure distance from

        Returns:
            Dictionary with support/resistance analysis
        """
        if len(context_df) < 10:
            return {'support_levels': [], 'resistance_levels': [], 'nearest_support': None, 'nearest_resistance': None}

        # Find local lows (support) - price lower than neighbors
        support_levels = []
        for i in range(5, len(context_df) - 5):
            low = context_df.iloc[i]['low']

            # Check if local minimum
            is_local_min = True
            for j in range(i-5, i+5):
                if j != i and context_df.iloc[j]['low'] < low:
                    is_local_min = False
                    break

            if is_local_min:
                support_levels.append({
                    'price': float(low),
                    'distance_pct': float((current_price - low) / low * 100),
                    'timestamp': str(context_df.iloc[i]['timestamp'])
                })

        # Find local highs (resistance) - price higher than neighbors
        resistance_levels = []
        for i in range(5, len(context_df) - 5):
            high = context_df.iloc[i]['high']

            # Check if local maximum
            is_local_max = True
            for j in range(i-5, i+5):
                if j != i and context_df.iloc[j]['high'] > high:
                    is_local_max = False
                    break

            if is_local_max:
                resistance_levels.append({
                    'price': float(high),
                    'distance_pct': float((high - current_price) / current_price * 100),
                    'timestamp': str(context_df.iloc[i]['timestamp'])
                })

        # Find nearest support and resistance
        nearest_support = None
        if support_levels:
            # Support below current price
            below_supports = [s for s in support_levels if s['price'] < current_price]
            if below_supports:
                nearest_support = max(below_supports, key=lambda x: x['price'])

        nearest_resistance = None
        if resistance_levels:
            # Resistance above current price
            above_resistances = [r for r in resistance_levels if r['price'] > current_price]
            if above_resistances:
                nearest_resistance = min(above_resistances, key=lambda x: x['price'])

        return {
            'support_levels': support_levels[-5:] if len(support_levels) > 5 else support_levels,  # Keep last 5
            'resistance_levels': resistance_levels[-5:] if len(resistance_levels) > 5 else resistance_levels,
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'at_support': nearest_support and abs(nearest_support['distance_pct']) < 0.5 if nearest_support else False,
            'at_resistance': nearest_resistance and abs(nearest_resistance['distance_pct']) < 0.5 if nearest_resistance else False
        }

    def add_optimal_entry(self, timestamp: str, direction: str, reason: str,
                          exit_timestamp: str = None, profit_achieved: float = None):
        """
        Add an optimal entry trade to the dataset

        Args:
            timestamp: When you would have entered (e.g., "2025-01-15 14:30")
            direction: 'long' or 'short'
            reason: Why this was a great trade
            exit_timestamp: Optional - when you would have exited
            profit_achieved: Optional - what profit % was achieved
        """
        print("\n" + "="*80)
        print(f"📝 Adding OPTIMAL {direction.upper()} ENTRY")
        print("="*80)

        # Load data
        df = self.load_historical_data()

        # Find candle
        idx, candle = self.find_candle_by_timestamp(df, timestamp)
        if idx is None:
            print("❌ Could not find candle, skipping")
            return

        # Capture market state
        market_state = self.capture_market_state(df, idx)

        # Create trade record
        trade_record = {
            'timestamp': timestamp,
            'direction': direction,
            'reason': reason,
            'exit_timestamp': exit_timestamp,
            'profit_achieved': profit_achieved,
            'market_state': market_state,
            'added_on': datetime.now().isoformat()
        }

        # Add to collection
        self.optimal_trades['optimal_entries'].append(trade_record)

        # Show summary
        print(f"\n✅ Captured optimal {direction} entry")
        print(f"   Price: ${market_state['ohlcv']['close']:.2f}")
        print(f"   Reason: {reason}")

        # Show key indicators
        print(f"\n📊 Key indicators at entry:")
        indicators = market_state['indicators']

        # Show most relevant ones
        relevant = ['confluence_score_long', 'confluence_score_short', 'rsi_14',
                   'macd_fast_trend', 'volume_status', 'stoch_k', 'vwap']
        for key in relevant:
            if key in indicators:
                print(f"   {key}: {indicators[key]}")

        # Support/Resistance
        sr = market_state['support_resistance']
        if sr['nearest_support']:
            print(f"   Nearest support: ${sr['nearest_support']['price']:.2f} ({sr['nearest_support']['distance_pct']:.2f}% away)")
        if sr['nearest_resistance']:
            print(f"   Nearest resistance: ${sr['nearest_resistance']['price']:.2f} ({sr['nearest_resistance']['distance_pct']:.2f}% away)")
        if sr['at_support']:
            print(f"   🎯 AT SUPPORT LEVEL!")
        if sr['at_resistance']:
            print(f"   🎯 AT RESISTANCE LEVEL!")

        # Save
        self._save_trades()

    def add_missed_opportunity(self, timestamp: str, direction: str, reason: str):
        """
        Add a missed opportunity (trade bot should have taken but didn't)

        Args:
            timestamp: When the opportunity occurred
            direction: 'long' or 'short'
            reason: Why this was a missed opportunity
        """
        print("\n" + "="*80)
        print(f"⚠️  Adding MISSED {direction.upper()} OPPORTUNITY")
        print("="*80)

        # Load data
        df = self.load_historical_data()

        # Find candle
        idx, candle = self.find_candle_by_timestamp(df, timestamp)
        if idx is None:
            print("❌ Could not find candle, skipping")
            return

        # Capture market state
        market_state = self.capture_market_state(df, idx)

        # Create record
        record = {
            'timestamp': timestamp,
            'direction': direction,
            'reason': reason,
            'market_state': market_state,
            'added_on': datetime.now().isoformat()
        }

        # Add to collection
        self.optimal_trades['missed_opportunities'].append(record)

        print(f"✅ Captured missed {direction} opportunity")
        self._save_trades()

    def add_false_signal(self, timestamp: str, direction: str, reason: str, loss_pct: float = None):
        """
        Add a false signal (trade bot took but shouldn't have)

        Args:
            timestamp: When bot entered
            direction: 'long' or 'short'
            reason: Why this was a bad trade
            loss_pct: Optional - what loss % was incurred
        """
        print("\n" + "="*80)
        print(f"❌ Adding FALSE {direction.upper()} SIGNAL")
        print("="*80)

        # Load data
        df = self.load_historical_data()

        # Find candle
        idx, candle = self.find_candle_by_timestamp(df, timestamp)
        if idx is None:
            print("❌ Could not find candle, skipping")
            return

        # Capture market state
        market_state = self.capture_market_state(df, idx)

        # Create record
        record = {
            'timestamp': timestamp,
            'direction': direction,
            'reason': reason,
            'loss_pct': loss_pct,
            'market_state': market_state,
            'added_on': datetime.now().isoformat()
        }

        # Add to collection
        self.optimal_trades['false_signals_bot_took'].append(record)

        print(f"✅ Captured false {direction} signal")
        self._save_trades()

    def show_summary(self):
        """Display summary of collected trades"""
        print("\n" + "="*80)
        print("📊 OPTIMAL TRADES DATASET SUMMARY")
        print("="*80)

        print(f"\n✅ Optimal Entries: {len(self.optimal_trades['optimal_entries'])}")
        for i, trade in enumerate(self.optimal_trades['optimal_entries'][-5:], 1):
            print(f"   {i}. {trade['timestamp']} - {trade['direction'].upper()} - {trade['reason'][:50]}...")

        print(f"\n⚠️  Missed Opportunities: {len(self.optimal_trades['missed_opportunities'])}")
        for i, trade in enumerate(self.optimal_trades['missed_opportunities'][-5:], 1):
            print(f"   {i}. {trade['timestamp']} - {trade['direction'].upper()} - {trade['reason'][:50]}...")

        print(f"\n❌ False Signals: {len(self.optimal_trades['false_signals_bot_took'])}")
        for i, trade in enumerate(self.optimal_trades['false_signals_bot_took'][-5:], 1):
            print(f"   {i}. {trade['timestamp']} - {trade['direction'].upper()} - {trade['reason'][:50]}...")

        print(f"\n💾 Saved to: {self.output_file}")
        print(f"📅 Last updated: {self.optimal_trades['metadata']['last_updated']}")


def interactive_mode():
    """
    Interactive mode for adding trades via conversation with Claude
    """
    collector = OptimalTradesCollector()

    print("\n" + "="*80)
    print("🎯 OPTIMAL TRADES DATA COLLECTION")
    print("="*80)
    print("\nThis script helps you build a dataset of YOUR expert trade examples.")
    print("These examples will be used to discover winning patterns in the data.")
    print("\nNow let's start collecting optimal trades!")
    print("\n" + "="*80)

    # Show current summary
    collector.show_summary()

    print("\n\nReady to add trades! In the chat above, describe optimal trades like:")
    print('  "Add optimal long entry on Jan 15 2:30 PM - perfect support bounce"')
    print('  "Add missed opportunity Jan 16 9:15 AM short - resistance rejection"')
    print('  "Add false signal Jan 14 11:00 AM long - ranging market, lost 2%"')

    return collector


if __name__ == '__main__':
    # Run in interactive mode
    collector = interactive_mode()

    print("\n✅ Collector initialized and ready!")
    print("Now describe your optimal trades in the conversation above.")
