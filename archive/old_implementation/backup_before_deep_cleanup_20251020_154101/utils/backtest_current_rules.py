"""
Backtest Current Trading Rules
Simulates what trades would have been executed using the current algorithm rules
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


class TradingRulesBacktest:
    """Simulate trades using current bot's trading rules"""

    def __init__(self, ema_data_file='trading_data/ema_data_5min.csv'):
        self.ema_data_file = ema_data_file
        self.df = None
        self.trades = []
        self.last_trade_time = None
        self.trade_cooldown_minutes = 30

    def load_data(self, hours_back=24):
        """Load EMA data"""
        print(f"📂 Loading EMA data from {self.ema_data_file}...")

        self.df = pd.read_csv(self.ema_data_file)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        # Filter to recent data
        cutoff = datetime.now() - timedelta(hours=hours_back)
        self.df = self.df[self.df['timestamp'] >= cutoff].copy()

        print(f"✅ Loaded {len(self.df)} snapshots (last {hours_back} hours)")

        return len(self.df) > 0

    def count_light_emas(self, row, color):
        """
        Count EMAs with specified color and 'light' intensity

        Args:
            row: DataFrame row
            color: 'green' or 'red'

        Returns:
            int: Count of light EMAs
        """
        count = 0
        for ema_num in range(5, 150, 5):  # 5, 10, 15, ..., 145
            color_col = f'MMA{ema_num}_color'
            intensity_col = f'MMA{ema_num}_intensity'

            if color_col in row.index and intensity_col in row.index:
                if row[color_col] == color and row[intensity_col] == 'light':
                    count += 1

        return count

    def is_high_quality_setup(self, row, direction, confidence=0.85):
        """
        Apply current bot's quality filters

        Rules from dual_timeframe_bot.py:is_high_quality_setup():
        1. High confidence (85%+ or 90%+ without wick)
        2. Timeframe alignment (both trending same direction)
        3. Accept mixed_green/mixed_red for early entries
        4. Special case: 15+ light EMAs = strong early reversal
        5. Wick signal preferred

        Args:
            row: DataFrame row with EMA data
            direction: 'LONG' or 'SHORT'
            confidence: Simulated confidence score (0-1)

        Returns:
            tuple: (bool, str) - (is_quality, reason)
        """
        state = row['ribbon_state'].lower()

        # Require high confidence
        if confidence < 0.85:
            return False, f"⛔ Confidence {confidence:.0%} < 85% minimum"

        # Direction-specific checks
        if direction == 'LONG':
            # Accept mixed_green or all_green
            is_bullish = any(x in state for x in ['all_green', 'mixed_green'])

            # REJECT if clearly bearish
            is_bearish = 'all_red' in state

            if is_bearish:
                return False, "⛔ State is all_red (bearish)"

            # If no bullish momentum, reject
            if not is_bullish:
                return False, "⛔ No bullish momentum detected"

            # SPECIAL CASE: Early Reversal
            # If 15+ LIGHT green EMAs, override state check
            light_green_count = self.count_light_emas(row, 'green')

            if light_green_count >= 15:
                return True, f"✅ STRONG EARLY REVERSAL: {light_green_count} LIGHT green EMAs"

        elif direction == 'SHORT':
            # Accept mixed_red or all_red
            is_bearish = any(x in state for x in ['all_red', 'mixed_red'])

            # REJECT if clearly bullish
            is_bullish = 'all_green' in state

            if is_bullish:
                return False, "⛔ State is all_green (bullish)"

            # If no bearish momentum, reject
            if not is_bearish:
                return False, "⛔ No bearish momentum detected"

            # SPECIAL CASE: Early Reversal
            # If 15+ LIGHT red EMAs, override state check
            light_red_count = self.count_light_emas(row, 'red')

            if light_red_count >= 15:
                return True, f"✅ STRONG EARLY REVERSAL: {light_red_count} LIGHT red EMAs"

        # All checks passed
        return True, f"✅ High-quality setup: {confidence:.0%} confidence"

    def detect_entry_signal(self, row, prev_row):
        """
        Detect if this snapshot represents an entry signal

        Entry signals occur when:
        1. Ribbon state transitions (e.g., mixed -> all_green, all_red -> mixed_red)
        2. Strong light EMA formation (15+ light EMAs)

        Args:
            row: Current row
            prev_row: Previous row

        Returns:
            tuple: (direction, confidence, reason) or (None, 0, "")
        """
        if prev_row is None:
            return None, 0, ""

        curr_state = row['ribbon_state'].lower()
        prev_state = prev_row['ribbon_state'].lower()

        # No transition = no signal
        if curr_state == prev_state:
            return None, 0, ""

        # LONG signals
        if any(x in curr_state for x in ['all_green', 'mixed_green']):
            # Transitioning to bullish state
            if 'red' in prev_state or 'mixed' in prev_state:
                # Stronger signal if going from all_red to green
                confidence = 0.90 if 'all_red' in prev_state else 0.87

                # Check for light EMA boost
                light_green = self.count_light_emas(row, 'green')
                if light_green >= 15:
                    confidence = min(0.95, confidence + 0.05)

                reason = f"Ribbon flip: {prev_state} → {curr_state}"
                if light_green >= 15:
                    reason += f" ({light_green} light green EMAs)"

                return 'LONG', confidence, reason

        # SHORT signals
        if any(x in curr_state for x in ['all_red', 'mixed_red']):
            # Transitioning to bearish state
            if 'green' in prev_state or 'mixed' in prev_state:
                # Stronger signal if going from all_green to red
                confidence = 0.90 if 'all_green' in prev_state else 0.87

                # Check for light EMA boost
                light_red = self.count_light_emas(row, 'red')
                if light_red >= 15:
                    confidence = min(0.95, confidence + 0.05)

                reason = f"Ribbon flip: {prev_state} → {curr_state}"
                if light_red >= 15:
                    reason += f" ({light_red} light red EMAs)"

                return 'SHORT', confidence, reason

        return None, 0, ""

    def can_enter_trade(self, timestamp):
        """Check if trade cooldown allows entry"""
        if self.last_trade_time is None:
            return True

        time_diff = (timestamp - self.last_trade_time).total_seconds() / 60

        return time_diff >= self.trade_cooldown_minutes

    def find_exit(self, entry_idx, direction, entry_price, max_hold_minutes=60):
        """
        Find optimal exit point for a trade

        Exit conditions:
        1. Ribbon state flips back (main exit)
        2. Hit target profit (0.5%+)
        3. Max hold time reached

        Args:
            entry_idx: Index of entry
            direction: 'LONG' or 'SHORT'
            entry_price: Entry price
            max_hold_minutes: Max hold time

        Returns:
            dict: Exit info
        """
        entry_time = self.df.iloc[entry_idx]['timestamp']
        entry_state = self.df.iloc[entry_idx]['ribbon_state'].lower()

        max_idx = min(entry_idx + (max_hold_minutes * 6), len(self.df))

        for exit_idx in range(entry_idx + 1, max_idx):
            exit_time = self.df.iloc[exit_idx]['timestamp']
            exit_price = self.df.iloc[exit_idx]['price']
            exit_state = self.df.iloc[exit_idx]['ribbon_state'].lower()

            # Calculate PnL
            if direction == 'LONG':
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100

            # Exit if ribbon flips
            if exit_state != entry_state:
                hold_time = (exit_time - entry_time).total_seconds()
                return {
                    'exit_idx': exit_idx,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'exit_reason': f'Ribbon flip to {exit_state}',
                    'pnl_pct': pnl_pct,
                    'hold_time_sec': hold_time,
                    'hold_time_min': hold_time / 60
                }

            # Exit if hit target
            if pnl_pct >= 0.5:
                hold_time = (exit_time - entry_time).total_seconds()
                return {
                    'exit_idx': exit_idx,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'exit_reason': 'Hit target (0.5%+)',
                    'pnl_pct': pnl_pct,
                    'hold_time_sec': hold_time,
                    'hold_time_min': hold_time / 60
                }

        # Max hold time reached
        exit_idx = max_idx - 1
        exit_time = self.df.iloc[exit_idx]['timestamp']
        exit_price = self.df.iloc[exit_idx]['price']

        if direction == 'LONG':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        hold_time = (exit_time - entry_time).total_seconds()

        return {
            'exit_idx': exit_idx,
            'exit_time': exit_time,
            'exit_price': exit_price,
            'exit_reason': f'Max hold time ({max_hold_minutes}min)',
            'pnl_pct': pnl_pct,
            'hold_time_sec': hold_time,
            'hold_time_min': hold_time / 60
        }

    def run_backtest(self, max_hold_minutes=60):
        """
        Run backtest simulation

        Args:
            max_hold_minutes: Maximum hold time for trades
        """
        print(f"\n🔄 Running backtest with current trading rules...")
        print(f"   Cooldown: {self.trade_cooldown_minutes} minutes")
        print(f"   Max hold: {max_hold_minutes} minutes")

        self.trades = []
        prev_row = None

        for i in range(len(self.df)):
            row = self.df.iloc[i]
            timestamp = row['timestamp']

            # Detect entry signal
            direction, confidence, reason = self.detect_entry_signal(row, prev_row)

            if direction:
                # Check cooldown
                if not self.can_enter_trade(timestamp):
                    prev_row = row
                    continue

                # Check quality filters
                is_quality, quality_reason = self.is_high_quality_setup(row, direction, confidence)

                if is_quality:
                    # ENTRY!
                    entry_price = row['price']

                    # Find exit
                    exit_info = self.find_exit(i, direction, entry_price, max_hold_minutes)

                    # Record trade
                    trade = {
                        'entry_time': timestamp.isoformat(),
                        'entry_price': float(entry_price),
                        'entry_state': row['ribbon_state'],
                        'direction': direction,
                        'confidence': confidence,
                        'entry_reason': reason,
                        'quality_reason': quality_reason,
                        **exit_info
                    }

                    # Convert timestamps to ISO format
                    if 'exit_time' in trade:
                        trade['exit_time'] = trade['exit_time'].isoformat()

                    self.trades.append(trade)
                    self.last_trade_time = timestamp

                    print(f"   ✅ {direction} @ {timestamp.strftime('%H:%M:%S')} - {reason}")

            prev_row = row

        print(f"\n✅ Backtest complete: {len(self.trades)} trades found")

        return self.trades

    def analyze_results(self):
        """Analyze backtest results"""
        if not self.trades:
            print("\n⚠️  No trades to analyze")
            return

        print("\n" + "="*80)
        print("📊 BACKTEST RESULTS - CURRENT TRADING RULES")
        print("="*80)

        df_trades = pd.DataFrame(self.trades)

        # Overall stats
        total_trades = len(df_trades)
        total_pnl = df_trades['pnl_pct'].sum()
        avg_pnl = df_trades['pnl_pct'].mean()
        avg_hold_time = df_trades['hold_time_min'].mean()

        # Win/loss stats
        winners = df_trades[df_trades['pnl_pct'] > 0]
        losers = df_trades[df_trades['pnl_pct'] <= 0]
        win_rate = len(winners) / total_trades * 100

        print(f"\n📈 OVERALL STATISTICS:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Average PnL per Trade: {avg_pnl:+.2f}%")
        print(f"   Average Hold Time: {avg_hold_time:.1f} minutes")
        print(f"   Win Rate: {win_rate:.1f}% ({len(winners)} wins, {len(losers)} losses)")

        # By direction
        print(f"\n📊 BY DIRECTION:")
        for direction in ['LONG', 'SHORT']:
            dir_trades = df_trades[df_trades['direction'] == direction]
            if len(dir_trades) > 0:
                dir_winners = dir_trades[dir_trades['pnl_pct'] > 0]
                dir_win_rate = len(dir_winners) / len(dir_trades) * 100

                print(f"\n   {direction}:")
                print(f"      Count: {len(dir_trades)}")
                print(f"      Total PnL: {dir_trades['pnl_pct'].sum():+.2f}%")
                print(f"      Avg PnL: {dir_trades['pnl_pct'].mean():+.2f}%")
                print(f"      Best Trade: {dir_trades['pnl_pct'].max():+.2f}%")
                print(f"      Worst Trade: {dir_trades['pnl_pct'].min():+.2f}%")
                print(f"      Win Rate: {dir_win_rate:.1f}%")
                print(f"      Avg Hold: {dir_trades['hold_time_min'].mean():.1f} min")

        # Top trades
        print(f"\n🏆 TOP 5 PROFITABLE TRADES:")
        top_trades = df_trades.nlargest(5, 'pnl_pct')
        for idx, trade in top_trades.iterrows():
            print(f"\n   {trade['direction']} @ {trade['entry_time'][:19]}")
            print(f"      Entry: ${trade['entry_price']:.2f} -> Exit: ${trade['exit_price']:.2f}")
            print(f"      PnL: {trade['pnl_pct']:+.2f}% | Hold: {trade['hold_time_min']:.1f} min")
            print(f"      Reason: {trade['entry_reason']}")

        # Worst trades
        print(f"\n💔 WORST 5 TRADES:")
        worst_trades = df_trades.nsmallest(5, 'pnl_pct')
        for idx, trade in worst_trades.iterrows():
            print(f"\n   {trade['direction']} @ {trade['entry_time'][:19]}")
            print(f"      Entry: ${trade['entry_price']:.2f} -> Exit: ${trade['exit_price']:.2f}")
            print(f"      PnL: {trade['pnl_pct']:+.2f}% | Hold: {trade['hold_time_min']:.1f} min")
            print(f"      Reason: {trade['entry_reason']}")

        return df_trades

    def save_results(self, filename='backtest_trades.json'):
        """Save backtest results to JSON"""
        output_path = f'trading_data/{filename}'

        data = {
            'generated_at': datetime.now().isoformat(),
            'backtest_params': {
                'trade_cooldown_minutes': self.trade_cooldown_minutes,
                'confidence_threshold': 0.85
            },
            'total_trades': len(self.trades),
            'total_pnl_pct': sum(t['pnl_pct'] for t in self.trades),
            'avg_pnl_pct': np.mean([t['pnl_pct'] for t in self.trades]) if self.trades else 0,
            'trades': self.trades
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n💾 Saved backtest results to: {output_path}")

        return output_path


def main():
    """Run backtest"""
    print("="*80)
    print("🔄 BACKTEST - CURRENT TRADING RULES")
    print("="*80)

    backtest = TradingRulesBacktest()

    # Load data (last 24 hours)
    if not backtest.load_data(hours_back=24):
        print("❌ No data available")
        return

    # Run backtest
    trades = backtest.run_backtest(max_hold_minutes=60)

    # Analyze
    backtest.analyze_results()

    # Save
    backtest.save_results()

    print("\n" + "="*80)
    print("✅ BACKTEST COMPLETE!")
    print("="*80)

    print("""
NEXT STEPS:
1. Run visualize_trading_analysis.py to see backtest trades on the chart
2. Compare: Optimal trades vs Backtest trades vs Actual trades
3. Identify: Where did rules miss opportunities? Where did rules fail?
4. Adjust: Refine entry/exit rules based on analysis
    """)


if __name__ == '__main__':
    main()
