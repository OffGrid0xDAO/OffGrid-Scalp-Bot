#!/usr/bin/env python3
"""
Generate Comparison Charts

Visualize:
1. User's 22 optimal trades (green markers)
2. Bot's matched trades (blue markers)
3. Bot's false signals (red markers)
4. Bot's missed trades (yellow markers)

Shows price action + key indicators during October 5-21 period
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from datetime import datetime


class ComparisonChartGenerator:
    """Generate comparison charts for user vs bot trades"""

    def __init__(self):
        """Initialize chart generator"""
        self.data_dir = Path(__file__).parent / 'trading_data'
        self.output_dir = self.data_dir / 'charts' / 'comparison'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load data
        self.df = pd.read_csv(self.data_dir / 'indicators' / 'eth_1h_full.csv')
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

        # Filter to analysis period
        self.df = self.df[(self.df['timestamp'] >= '2025-10-05') &
                         (self.df['timestamp'] < '2025-10-22')].copy()

        # Load user trades
        with open(self.data_dir / 'optimal_trades.json', 'r') as f:
            user_data = json.load(f)
        self.user_trades = user_data['optimal_entries']

        # Load overlap analysis
        if (self.data_dir / 'overlap_analysis.json').exists():
            with open(self.data_dir / 'overlap_analysis.json', 'r') as f:
                self.overlap = json.load(f)
        else:
            print("⚠️  Overlap analysis not found. Run analyze_trade_overlap.py first")
            self.overlap = None

    def generate_overview_chart(self):
        """Generate overview chart with all trades marked"""
        print("\n📊 Generating overview chart...")

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(20, 14), sharex=True)

        # Main price chart
        ax1.plot(self.df['timestamp'], self.df['close'], 'k-', linewidth=1, label='ETH Price', alpha=0.7)

        # Mark USER trades
        for trade in self.user_trades:
            trade_time = pd.to_datetime(trade['timestamp'])
            trade_price = trade['market_state']['ohlcv']['close']
            direction = trade['direction']

            if direction == 'long':
                ax1.scatter(trade_time, trade_price, color='green', s=200, marker='^',
                           edgecolors='darkgreen', linewidths=2, zorder=5,
                           label='User LONG' if trade == self.user_trades[0] else '')
            else:
                ax1.scatter(trade_time, trade_price, color='red', s=200, marker='v',
                           edgecolors='darkred', linewidths=2, zorder=5,
                           label='User SHORT' if trade == self.user_trades[0] else '')

        ax1.set_ylabel('Price (USD)', fontsize=12, fontweight='bold')
        ax1.set_title('ETH Price Action with User Trades (Oct 5-21, 2025)', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # RSI chart
        ax2.plot(self.df['timestamp'], self.df['rsi_14'], 'purple', linewidth=1.5, label='RSI(14)')
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.5, label='Overbought (70)')
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.5, label='Oversold (30)')
        ax2.fill_between(self.df['timestamp'], 30, 70, alpha=0.1, color='gray')

        # Mark RSI at user trades
        for trade in self.user_trades:
            trade_time = pd.to_datetime(trade['timestamp'])
            rsi = trade['market_state']['indicators'].get('rsi_14')
            if rsi:
                ax2.scatter(trade_time, rsi, color='orange', s=100, marker='o',
                           edgecolors='darkorange', linewidths=1.5, zorder=5)

        ax2.set_ylabel('RSI', fontsize=12, fontweight='bold')
        ax2.set_ylim(0, 100)
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)

        # Volume chart
        colors = ['green' if self.df.iloc[i]['close'] >= self.df.iloc[i]['open']
                 else 'red' for i in range(len(self.df))]
        ax3.bar(self.df['timestamp'], self.df['volume'], color=colors, alpha=0.5, width=0.03)

        ax3.set_ylabel('Volume', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # Format x-axis
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax3.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()

        output_file = self.output_dir / 'overview_user_trades.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"   ✅ Saved: {output_file}")
        plt.close()

    def generate_bot_comparison_chart(self):
        """Generate chart comparing bot trades vs user trades"""
        print("\n📊 Generating bot comparison chart...")

        # Get bot signals
        import sys
        sys.path.append(str(Path(__file__).parent / 'src'))
        from strategy.entry_detector_user_pattern import EntryDetector

        detector = EntryDetector()
        df_signals = detector.scan_historical_signals(self.df.copy())

        bot_signals = df_signals[df_signals['entry_signal'] == True].copy()

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(20, 16), sharex=True)

        # Main price chart
        ax1.plot(self.df['timestamp'], self.df['close'], 'k-', linewidth=1, label='ETH Price', alpha=0.7)

        # Mark USER trades (ground truth)
        for trade in self.user_trades:
            trade_time = pd.to_datetime(trade['timestamp'])
            trade_price = trade['market_state']['ohlcv']['close']
            direction = trade['direction']

            if direction == 'long':
                ax1.scatter(trade_time, trade_price, color='lime', s=250, marker='^',
                           edgecolors='darkgreen', linewidths=3, zorder=10, alpha=0.8,
                           label='✅ User LONG' if trade == self.user_trades[0] else '')
            else:
                ax1.scatter(trade_time, trade_price, color='orangered', s=250, marker='v',
                           edgecolors='darkred', linewidths=3, zorder=10, alpha=0.8,
                           label='✅ User SHORT' if trade == self.user_trades[0] else '')

        # Mark BOT trades
        bot_long_count = 0
        bot_short_count = 0
        for _, bot_trade in bot_signals.iterrows():
            if bot_trade['entry_direction'] == 'long':
                ax1.scatter(bot_trade['timestamp'], bot_trade['close'], color='cyan', s=80, marker='^',
                           edgecolors='blue', linewidths=1, zorder=5, alpha=0.5,
                           label='Bot LONG' if bot_long_count == 0 else '')
                bot_long_count += 1
            else:
                ax1.scatter(bot_trade['timestamp'], bot_trade['close'], color='pink', s=80, marker='v',
                           edgecolors='purple', linewidths=1, zorder=5, alpha=0.5,
                           label='Bot SHORT' if bot_short_count == 0 else '')
                bot_short_count += 1

        ax1.set_ylabel('Price (USD)', fontsize=12, fontweight='bold')
        ax1.set_title('ETH Price: User Trades (✅ large) vs Bot Trades (small) - Oct 5-21, 2025',
                     fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3)

        # RSI with trade markers
        ax2.plot(self.df['timestamp'], self.df['rsi_14'], 'purple', linewidth=1.5, label='RSI(14)')
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.5)
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.5)
        ax2.fill_between(self.df['timestamp'], 30, 70, alpha=0.1, color='gray')

        for trade in self.user_trades:
            trade_time = pd.to_datetime(trade['timestamp'])
            rsi = trade['market_state']['indicators'].get('rsi_14')
            if rsi:
                ax2.scatter(trade_time, rsi, color='yellow', s=150, marker='*',
                           edgecolors='orange', linewidths=2, zorder=10)

        ax2.set_ylabel('RSI', fontsize=12, fontweight='bold')
        ax2.set_ylim(0, 100)
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)

        # Stochastic
        if 'stoch_k' in self.df.columns:
            ax3.plot(self.df['timestamp'], self.df['stoch_k'], 'blue', linewidth=1.5, label='Stoch K')
            ax3.plot(self.df['timestamp'], self.df['stoch_d'], 'red', linewidth=1, alpha=0.7, label='Stoch D')
            ax3.axhline(y=80, color='r', linestyle='--', alpha=0.5)
            ax3.axhline(y=20, color='g', linestyle='--', alpha=0.5)

            for trade in self.user_trades:
                trade_time = pd.to_datetime(trade['timestamp'])
                stoch = trade['market_state']['indicators'].get('stoch_k')
                if stoch:
                    ax3.scatter(trade_time, stoch, color='yellow', s=150, marker='*',
                               edgecolors='orange', linewidths=2, zorder=10)

            ax3.set_ylabel('Stochastic', fontsize=12, fontweight='bold')
            ax3.set_ylim(0, 100)
            ax3.legend(loc='upper left')
            ax3.grid(True, alpha=0.3)

        # Confluence scores
        ax4.plot(self.df['timestamp'], self.df['confluence_score_long'], 'green',
                linewidth=1.5, alpha=0.7, label='Confluence Long')
        ax4.plot(self.df['timestamp'], self.df['confluence_score_short'], 'red',
                linewidth=1.5, alpha=0.7, label='Confluence Short')

        for trade in self.user_trades:
            trade_time = pd.to_datetime(trade['timestamp'])
            conf_long = trade['market_state']['indicators'].get('confluence_score_long')
            conf_short = trade['market_state']['indicators'].get('confluence_score_short')

            if trade['direction'] == 'long' and conf_long:
                ax4.scatter(trade_time, conf_long, color='lime', s=150, marker='^',
                           edgecolors='darkgreen', linewidths=2, zorder=10)
            elif trade['direction'] == 'short' and conf_short:
                ax4.scatter(trade_time, conf_short, color='orangered', s=150, marker='v',
                           edgecolors='darkred', linewidths=2, zorder=10)

        ax4.set_ylabel('Confluence Score', fontsize=12, fontweight='bold')
        ax4.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax4.legend(loc='upper left')
        ax4.grid(True, alpha=0.3)

        # Format x-axis
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax4.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()

        output_file = self.output_dir / 'bot_vs_user_comparison.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"   ✅ Saved: {output_file}")
        plt.close()

        print(f"\n📈 Bot took {len(bot_signals)} trades vs User's {len(self.user_trades)} trades")
        print(f"   Ratio: {len(bot_signals) / len(self.user_trades):.1f}x more trades")

    def generate_individual_trade_charts(self, max_trades: int = 5):
        """Generate detailed chart for each user trade"""
        print(f"\n📊 Generating individual trade charts (first {max_trades})...")

        for i, trade in enumerate(self.user_trades[:max_trades], 1):
            trade_time = pd.to_datetime(trade['timestamp'])

            # Get window around trade (12 hours before, 24 hours after)
            start_time = trade_time - pd.Timedelta(hours=12)
            end_time = trade_time + pd.Timedelta(hours=24)

            df_window = self.df[(self.df['timestamp'] >= start_time) &
                               (self.df['timestamp'] <= end_time)].copy()

            if len(df_window) == 0:
                continue

            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)

            # Price chart
            ax1.plot(df_window['timestamp'], df_window['close'], 'k-', linewidth=2)

            # Mark entry
            trade_price = trade['market_state']['ohlcv']['close']
            direction = trade['direction']

            if direction == 'long':
                ax1.scatter(trade_time, trade_price, color='green', s=400, marker='^',
                           edgecolors='darkgreen', linewidths=3, zorder=10, label='LONG Entry')
                ax1.axhline(y=trade_price, color='green', linestyle='--', alpha=0.3)
            else:
                ax1.scatter(trade_time, trade_price, color='red', s=400, marker='v',
                           edgecolors='darkred', linewidths=3, zorder=10, label='SHORT Entry')
                ax1.axhline(y=trade_price, color='red', linestyle='--', alpha=0.3)

            ax1.axvline(x=trade_time, color='blue', linestyle='--', alpha=0.5, linewidth=2)

            ax1.set_ylabel('Price (USD)', fontsize=12, fontweight='bold')
            ax1.set_title(f'Trade #{i}: {direction.upper()} at {trade_time} - ${trade_price:.2f}',
                         fontsize=14, fontweight='bold')
            ax1.legend(loc='upper left', fontsize=10)
            ax1.grid(True, alpha=0.3)

            # RSI
            ax2.plot(df_window['timestamp'], df_window['rsi_14'], 'purple', linewidth=2)
            ax2.axhline(y=70, color='r', linestyle='--', alpha=0.5)
            ax2.axhline(y=30, color='g', linestyle='--', alpha=0.5)

            rsi_val = trade['market_state']['indicators'].get('rsi_14')
            if rsi_val:
                ax2.scatter(trade_time, rsi_val, color='orange', s=300, marker='o',
                           edgecolors='darkorange', linewidths=3, zorder=10)
                ax2.text(trade_time, rsi_val + 5, f'RSI: {rsi_val:.1f}',
                        ha='center', fontsize=10, fontweight='bold')

            ax2.axvline(x=trade_time, color='blue', linestyle='--', alpha=0.5, linewidth=2)
            ax2.set_ylabel('RSI', fontsize=12, fontweight='bold')
            ax2.set_ylim(0, 100)
            ax2.grid(True, alpha=0.3)

            # Stochastic
            if 'stoch_k' in df_window.columns:
                ax3.plot(df_window['timestamp'], df_window['stoch_k'], 'blue', linewidth=2, label='Stoch K')
                ax3.plot(df_window['timestamp'], df_window['stoch_d'], 'red', linewidth=1.5, label='Stoch D')
                ax3.axhline(y=80, color='r', linestyle='--', alpha=0.5)
                ax3.axhline(y=20, color='g', linestyle='--', alpha=0.5)

                stoch_val = trade['market_state']['indicators'].get('stoch_k')
                if stoch_val:
                    ax3.scatter(trade_time, stoch_val, color='cyan', s=300, marker='o',
                               edgecolors='blue', linewidths=3, zorder=10)
                    ax3.text(trade_time, stoch_val + 5, f'Stoch: {stoch_val:.1f}',
                            ha='center', fontsize=10, fontweight='bold')

                ax3.axvline(x=trade_time, color='blue', linestyle='--', alpha=0.5, linewidth=2)
                ax3.set_ylabel('Stochastic', fontsize=12, fontweight='bold')
                ax3.set_xlabel('Time', fontsize=12, fontweight='bold')
                ax3.set_ylim(0, 100)
                ax3.legend(loc='upper left')
                ax3.grid(True, alpha=0.3)

            # Format x-axis
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')

            plt.tight_layout()

            output_file = self.output_dir / f'trade_{i:02d}_{direction}_{trade_time.strftime("%m%d_%H%M")}.png'
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"   ✅ Saved: {output_file}")
            plt.close()


if __name__ == '__main__':
    print("\n" + "="*80)
    print("📊 GENERATING COMPARISON CHARTS")
    print("="*80)

    generator = ComparisonChartGenerator()

    # Generate overview
    generator.generate_overview_chart()

    # Generate bot comparison
    generator.generate_bot_comparison_chart()

    # Generate individual trade charts
    generator.generate_individual_trade_charts(max_trades=10)

    print("\n" + "="*80)
    print("✅ CHARTS GENERATED!")
    print("="*80)
    print(f"\nCharts saved to: {generator.output_dir}")
    print("\nGenerated:")
    print("  1. overview_user_trades.png - Overview of all user trades")
    print("  2. bot_vs_user_comparison.png - Bot vs User comparison")
    print("  3. trade_XX_*.png - Individual trade detail charts")

    print("\n📊 Next: Refine strategy based on findings")
    print("   Key insight: Bot has 81.3% FALSE SIGNAL RATE!")
    print("   Need to add filters to reduce false positives")
