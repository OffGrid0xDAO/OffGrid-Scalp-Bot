#!/usr/bin/env python3
"""
Optimal Trade Finder - MFE/MAE Analysis

Uses perfect hindsight to find the absolute best possible trades.
This tells us:
- What was the maximum profit available?
- What conditions led to the best setups?
- How much profit are we leaving on the table?

This is CRITICAL for Claude LLM optimization - we need to know
what's possible before we can improve!
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path


class OptimalTradeFinder:
    """
    Find optimal trades using Maximum Favorable Excursion (MFE) analysis

    MFE = The best price reached after entry (with hindsight)
    MAE = The worst price reached after entry (with hindsight)

    By analyzing perfect trades, we can:
    1. Know the theoretical maximum profit
    2. Identify what indicators predicted the best moves
    3. Compare backtest vs optimal to find improvement areas
    """

    def __init__(self, min_profit_pct: float = 1.0, max_hold_candles: int = 24):
        """
        Initialize optimal trade finder

        Args:
            min_profit_pct: Minimum profit to consider a trade (default 1%)
            max_hold_candles: Maximum candles to hold (default 24 for 1h = 1 day)
                             For day trading: 1h timeframe = 24 candles = 1 day
                                            15m timeframe = 96 candles = 1 day
                                             5m timeframe = 288 candles = 1 day
        """
        self.min_profit_pct = min_profit_pct
        self.max_hold_candles = max_hold_candles

    def find_optimal_entry(self, df: pd.DataFrame, start_idx: int) -> Dict:
        """
        Find optimal entry at given candle using hindsight

        Looks forward to see what happens next, determines if it was
        a good entry point.

        Args:
            df: Full DataFrame
            start_idx: Index to check as entry

        Returns:
            dict with:
                - is_optimal: bool
                - direction: 'long' or 'short'
                - entry_price: float
                - optimal_exit_price: float
                - optimal_exit_idx: int
                - mfe: float (maximum favorable excursion %)
                - mae: float (maximum adverse excursion %)
                - profit_pct: float
                - candles_held: int
                - indicators_at_entry: dict
        """
        if start_idx >= len(df) - self.max_hold_candles:
            return {'is_optimal': False}

        entry_candle = df.iloc[start_idx]
        entry_price = entry_candle['close']

        # Look forward to find best profit opportunity
        future_candles = df.iloc[start_idx + 1:start_idx + 1 + self.max_hold_candles]

        # Calculate max/min prices in future
        max_price = future_candles['high'].max()
        min_price = future_candles['low'].min()

        # Calculate potential profit for both directions
        long_profit_pct = (max_price - entry_price) / entry_price * 100
        short_profit_pct = (entry_price - min_price) / entry_price * 100

        # Choose direction with better profit
        if long_profit_pct >= short_profit_pct and long_profit_pct >= self.min_profit_pct:
            direction = 'long'
            profit_pct = long_profit_pct
            optimal_exit_price = max_price

            # Find when max was hit
            exit_idx_relative = future_candles['high'].idxmax()
            exit_idx = df.index.get_loc(exit_idx_relative)

            # Calculate MAE (worst drawdown)
            mae_price = future_candles.loc[:exit_idx_relative, 'low'].min()
            mae = (mae_price - entry_price) / entry_price * 100

        elif short_profit_pct >= self.min_profit_pct:
            direction = 'short'
            profit_pct = short_profit_pct
            optimal_exit_price = min_price

            # Find when min was hit
            exit_idx_relative = future_candles['low'].idxmin()
            exit_idx = df.index.get_loc(exit_idx_relative)

            # Calculate MAE (worst drawdown)
            mae_price = future_candles.loc[:exit_idx_relative, 'high'].max()
            mae = (entry_price - mae_price) / entry_price * 100

        else:
            # Not profitable enough
            return {'is_optimal': False}

        # Collect indicators at entry
        indicators_at_entry = {
            'confluence_long': entry_candle.get('confluence_score_long', 0),
            'confluence_short': entry_candle.get('confluence_score_short', 0),
            'confluence_gap': abs(entry_candle.get('confluence_score_long', 0) -
                                 entry_candle.get('confluence_score_short', 0)),
            'volume_status': entry_candle.get('volume_status', 'normal'),
            'alignment_pct': entry_candle.get('alignment_pct', 0.5),
            'compression_score': entry_candle.get('compression_score', 0),
            'expansion_rate': entry_candle.get('expansion_rate', 0),
            'ribbon_flip': entry_candle.get('ribbon_flip', 'none'),
            'rsi_14': entry_candle.get('rsi_14', 50),
            'macd_fast_trend': entry_candle.get('macd_fast_trend', 'neutral'),
        }

        return {
            'is_optimal': True,
            'direction': direction,
            'entry_price': entry_price,
            'entry_time': entry_candle['timestamp'],
            'entry_idx': start_idx,
            'optimal_exit_price': optimal_exit_price,
            'optimal_exit_idx': exit_idx,
            'mfe': profit_pct,
            'mae': mae,
            'profit_pct': profit_pct,
            'candles_held': exit_idx - start_idx,
            'indicators_at_entry': indicators_at_entry
        }

    def scan_all_optimal_trades(self, df: pd.DataFrame) -> List[Dict]:
        """
        Scan entire history to find all optimal trade opportunities

        IMPORTANT: Only finds NON-OVERLAPPING trades (realistic scenario)

        Args:
            df: Full DataFrame with indicators

        Returns:
            List of optimal trade dicts
        """
        print("\n" + "="*80)
        print("FINDING OPTIMAL TRADES (Perfect Hindsight)")
        print("="*80)
        print(f"   Min profit: {self.min_profit_pct}%")
        print(f"   Max hold: {self.max_hold_candles} candles")

        optimal_trades = []
        i = 50  # Start after indicators are stable

        # Scan for non-overlapping trades only
        while i < len(df) - self.max_hold_candles:
            trade = self.find_optimal_entry(df, i)

            if trade['is_optimal']:
                optimal_trades.append(trade)
                # Skip to after this trade exits (no overlapping trades)
                i = trade['optimal_exit_idx'] + 1
            else:
                # Move to next candle
                i += 1

        print(f"\n📊 Optimal Trade Summary (Non-Overlapping):")
        print(f"   Total optimal trades: {len(optimal_trades)}")

        if optimal_trades:
            long_trades = [t for t in optimal_trades if t['direction'] == 'long']
            short_trades = [t for t in optimal_trades if t['direction'] == 'short']

            print(f"   Long trades: {len(long_trades)}")
            print(f"   Short trades: {len(short_trades)}")

            profits = [t['profit_pct'] for t in optimal_trades]
            print(f"   Average profit: {np.mean(profits):.2f}%")
            print(f"   Median profit: {np.median(profits):.2f}%")
            print(f"   Best trade: {np.max(profits):.2f}%")
            print(f"   Total potential profit: {np.sum(profits):.2f}%")

            # Show price range for validation
            entry_prices = [t['entry_price'] for t in optimal_trades]
            print(f"\n💰 Entry Price Range:")
            print(f"   Min: ${np.min(entry_prices):.2f}")
            print(f"   Max: ${np.max(entry_prices):.2f}")
            print(f"   Median: ${np.median(entry_prices):.2f}")

        return optimal_trades

    def analyze_optimal_conditions(self, optimal_trades: List[Dict]) -> Dict:
        """
        Analyze what indicators were present in optimal trades

        This tells Claude what to optimize for!

        Args:
            optimal_trades: List of optimal trade dicts

        Returns:
            dict with statistics on optimal conditions
        """
        if not optimal_trades:
            return {}

        print("\n" + "="*80)
        print("ANALYZING OPTIMAL TRADE CONDITIONS")
        print("="*80)

        # Collect all indicator values
        confluence_gaps = []
        volume_statuses = []
        compression_scores = []
        expansion_rates = []
        alignment_pcts = []
        rsi_values = []

        for trade in optimal_trades:
            ind = trade['indicators_at_entry']
            confluence_gaps.append(ind['confluence_gap'])
            volume_statuses.append(ind['volume_status'])
            compression_scores.append(ind['compression_score'])
            expansion_rates.append(ind['expansion_rate'])
            alignment_pcts.append(ind['alignment_pct'])
            rsi_values.append(ind['rsi_14'])

        # Calculate statistics
        analysis = {
            'total_trades': len(optimal_trades),
            'confluence_gap': {
                'mean': np.mean(confluence_gaps),
                'median': np.median(confluence_gaps),
                'min': np.min(confluence_gaps),
                'max': np.max(confluence_gaps),
                'pct_above_30': sum(1 for x in confluence_gaps if x > 30) / len(confluence_gaps) * 100,
                'pct_above_40': sum(1 for x in confluence_gaps if x > 40) / len(confluence_gaps) * 100,
            },
            'volume_status': {
                'spike': sum(1 for x in volume_statuses if x == 'spike') / len(volume_statuses) * 100,
                'elevated': sum(1 for x in volume_statuses if x == 'elevated') / len(volume_statuses) * 100,
                'normal': sum(1 for x in volume_statuses if x == 'normal') / len(volume_statuses) * 100,
                'low': sum(1 for x in volume_statuses if x == 'low') / len(volume_statuses) * 100,
            },
            'compression': {
                'mean': np.mean(compression_scores),
                'median': np.median(compression_scores),
                'pct_above_60': sum(1 for x in compression_scores if x > 60) / len(compression_scores) * 100,
            },
            'expansion_rate': {
                'mean': np.mean(expansion_rates),
                'median': np.median(expansion_rates),
                'pct_above_5': sum(1 for x in expansion_rates if x > 5) / len(expansion_rates) * 100,
            },
            'alignment': {
                'mean': np.mean(alignment_pcts),
                'median': np.median(alignment_pcts),
            },
            'rsi': {
                'mean': np.mean(rsi_values),
                'median': np.median(rsi_values),
            }
        }

        # Print analysis
        print(f"\n📊 Confluence Gap in Optimal Trades:")
        print(f"   Mean: {analysis['confluence_gap']['mean']:.1f}")
        print(f"   Median: {analysis['confluence_gap']['median']:.1f}")
        print(f"   Range: {analysis['confluence_gap']['min']:.1f} - {analysis['confluence_gap']['max']:.1f}")
        print(f"   % with gap > 30: {analysis['confluence_gap']['pct_above_30']:.1f}%")
        print(f"   % with gap > 40: {analysis['confluence_gap']['pct_above_40']:.1f}%")

        print(f"\n📊 Volume Status in Optimal Trades:")
        print(f"   Spike: {analysis['volume_status']['spike']:.1f}%")
        print(f"   Elevated: {analysis['volume_status']['elevated']:.1f}%")
        print(f"   Normal: {analysis['volume_status']['normal']:.1f}%")
        print(f"   Low: {analysis['volume_status']['low']:.1f}%")

        print(f"\n📊 Compression in Optimal Trades:")
        print(f"   Mean: {analysis['compression']['mean']:.1f}")
        print(f"   % with compression > 60: {analysis['compression']['pct_above_60']:.1f}%")

        print(f"\n📊 Expansion Rate in Optimal Trades:")
        print(f"   Mean: {analysis['expansion_rate']['mean']:.1f}")
        print(f"   % with expansion > 5: {analysis['expansion_rate']['pct_above_5']:.1f}%")

        return analysis

    def save_optimal_trades(self, optimal_trades: List[Dict], output_file: str):
        """
        Save optimal trades to CSV for analysis

        Args:
            optimal_trades: List of optimal trade dicts
            output_file: Output file path
        """
        if not optimal_trades:
            print("⚠️  No optimal trades to save")
            return

        # Convert to DataFrame
        rows = []
        for trade in optimal_trades:
            ind = trade['indicators_at_entry']
            row = {
                'entry_time': trade['entry_time'],
                'direction': trade['direction'],
                'entry_price': trade['entry_price'],
                'exit_price': trade['optimal_exit_price'],
                'profit_pct': trade['profit_pct'],
                'candles_held': trade['candles_held'],
                'mfe': trade['mfe'],
                'mae': trade['mae'],
                **ind  # Spread all indicators
            }
            rows.append(row)

        df = pd.DataFrame(rows)

        # Save
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        print(f"\n💾 Optimal trades saved: {output_file}")
        print(f"   Rows: {len(df)}")


if __name__ == '__main__':
    """Test optimal trade finder"""
    import sys

    # Load test data
    data_file = Path(__file__).parent.parent.parent / 'trading_data' / 'indicators' / 'eth_1h_full.csv'

    if not data_file.exists():
        print(f"❌ Test data not found: {data_file}")
        sys.exit(1)

    print(f"📊 Loading test data: {data_file}")
    df = pd.read_csv(data_file)
    print(f"   Loaded {len(df)} candles")

    # Create finder
    finder = OptimalTradeFinder(min_profit_pct=1.0, max_hold_candles=10)

    # Find optimal trades
    optimal_trades = finder.scan_all_optimal_trades(df)

    # Analyze conditions
    analysis = finder.analyze_optimal_conditions(optimal_trades)

    # Save results
    output_file = Path(__file__).parent.parent.parent / 'trading_data' / 'analysis' / 'eth_1h_optimal_trades.csv'
    finder.save_optimal_trades(optimal_trades, str(output_file))

    print("\n✅ Optimal trade analysis complete!")
