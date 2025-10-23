"""
Find Optimal Trades from Historical Data
Analyzes EMA data to find the best possible entry/exit points
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


class OptimalTradeFinder:
    """Find optimal trade opportunities from historical data"""

    def __init__(self, ema_data_file='trading_data/ema_data_5min.csv'):
        self.ema_data_file = ema_data_file
        self.df = None

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

    def detect_ribbon_flips(self):
        """
        Detect when ribbon state flips (e.g., all_red -> all_green)
        These are potential entry points
        """
        print("\n🔍 Detecting ribbon state flips...")

        flips = []

        for i in range(1, len(self.df)):
            prev_state = self.df.iloc[i-1]['ribbon_state']
            curr_state = self.df.iloc[i]['ribbon_state']

            if prev_state != curr_state:
                # Ribbon flipped
                flip = {
                    'timestamp': self.df.iloc[i]['timestamp'],
                    'price': self.df.iloc[i]['price'],
                    'from_state': prev_state,
                    'to_state': curr_state,
                    'index': i
                }
                flips.append(flip)

        print(f"✅ Found {len(flips)} ribbon state flips")

        return flips

    def find_optimal_entries(self, flips, min_move_pct=0.3, max_hold_minutes=60):
        """
        Find optimal entry points based on ribbon flips
        and subsequent price movements

        Args:
            flips: List of ribbon flip events
            min_move_pct: Minimum price movement to consider (%)
            max_hold_minutes: Maximum time to hold position (minutes)

        Returns:
            List of optimal trades
        """
        print(f"\n📈 Finding optimal trades (min move: {min_move_pct}%, max hold: {max_hold_minutes}min)...")

        optimal_trades = []

        for flip in flips:
            entry_idx = flip['index']
            entry_time = flip['timestamp']
            entry_price = flip['price']
            entry_state = flip['to_state']

            # Determine direction based on new state
            if 'green' in entry_state.lower():
                direction = 'LONG'
                # Look for upward movement
                target_direction = 1
            elif 'red' in entry_state.lower():
                direction = 'SHORT'
                # Look for downward movement
                target_direction = -1
            else:
                # Mixed or unknown state, skip
                continue

            # Look ahead for best exit
            max_idx = min(entry_idx + (max_hold_minutes * 6), len(self.df))  # 6 snapshots per minute (10 sec intervals)

            best_exit_idx = None
            best_exit_price = entry_price
            best_pnl_pct = 0

            for exit_idx in range(entry_idx + 1, max_idx):
                exit_price = self.df.iloc[exit_idx]['price']

                # Calculate PnL
                if direction == 'LONG':
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100

                # Track best exit
                if pnl_pct > best_pnl_pct:
                    best_pnl_pct = pnl_pct
                    best_exit_idx = exit_idx
                    best_exit_price = exit_price

                # Early exit if ribbon flips back
                exit_state = self.df.iloc[exit_idx]['ribbon_state']
                if exit_state != entry_state and pnl_pct > 0:
                    # Ribbon flipped, exit with profit
                    break

            # Only include if move was significant
            if best_pnl_pct >= min_move_pct and best_exit_idx is not None:
                exit_time = self.df.iloc[best_exit_idx]['timestamp']
                hold_time_sec = (exit_time - entry_time).total_seconds()

                optimal_trades.append({
                    'entry_time': entry_time.isoformat(),
                    'entry_price': float(entry_price),
                    'entry_state': entry_state,
                    'direction': direction,
                    'exit_time': exit_time.isoformat(),
                    'exit_price': float(best_exit_price),
                    'pnl_pct': round(best_pnl_pct, 2),
                    'hold_time_sec': int(hold_time_sec),
                    'hold_time_min': round(hold_time_sec / 60, 1)
                })

        print(f"✅ Found {len(optimal_trades)} optimal trades")

        return optimal_trades

    def analyze_optimal_trades(self, trades):
        """Analyze optimal trade statistics"""
        if not trades:
            print("\n⚠️  No optimal trades to analyze")
            return

        print("\n" + "="*80)
        print("📊 OPTIMAL TRADE ANALYSIS")
        print("="*80)

        df_trades = pd.DataFrame(trades)

        # Overall stats
        total_trades = len(df_trades)
        total_pnl = df_trades['pnl_pct'].sum()
        avg_pnl = df_trades['pnl_pct'].mean()
        avg_hold_time = df_trades['hold_time_min'].mean()

        print(f"\n📈 OVERALL STATISTICS:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Average PnL per Trade: {avg_pnl:+.2f}%")
        print(f"   Average Hold Time: {avg_hold_time:.1f} minutes")

        # By direction
        print(f"\n📊 BY DIRECTION:")
        for direction in ['LONG', 'SHORT']:
            dir_trades = df_trades[df_trades['direction'] == direction]
            if len(dir_trades) > 0:
                print(f"\n   {direction}:")
                print(f"      Count: {len(dir_trades)}")
                print(f"      Total PnL: {dir_trades['pnl_pct'].sum():+.2f}%")
                print(f"      Avg PnL: {dir_trades['pnl_pct'].mean():+.2f}%")
                print(f"      Best Trade: {dir_trades['pnl_pct'].max():+.2f}%")
                print(f"      Avg Hold: {dir_trades['hold_time_min'].mean():.1f} min")

        # Top trades
        print(f"\n🏆 TOP 5 TRADES:")
        top_trades = df_trades.nlargest(5, 'pnl_pct')
        for idx, trade in top_trades.iterrows():
            print(f"\n   {trade['direction']} @ {trade['entry_time'][:19]}")
            print(f"      Entry: ${trade['entry_price']:.2f} -> Exit: ${trade['exit_price']:.2f}")
            print(f"      PnL: {trade['pnl_pct']:+.2f}% | Hold: {trade['hold_time_min']:.1f} min")

        return df_trades

    def save_optimal_trades(self, trades, filename='optimal_trades.json'):
        """Save optimal trades to JSON file"""
        output_path = f'trading_data/{filename}'

        data = {
            'generated_at': datetime.now().isoformat(),
            'total_trades': len(trades),
            'total_pnl_pct': sum(t['pnl_pct'] for t in trades),
            'avg_pnl_pct': np.mean([t['pnl_pct'] for t in trades]) if trades else 0,
            'trades': trades
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n💾 Saved optimal trades to: {output_path}")

        return output_path


def main():
    """Run optimal trade finder"""
    print("="*80)
    print("🔍 OPTIMAL TRADE FINDER")
    print("="*80)

    finder = OptimalTradeFinder()

    # Load data (last 24 hours)
    if not finder.load_data(hours_back=24):
        print("❌ No data available")
        return

    # Detect ribbon flips
    flips = finder.detect_ribbon_flips()

    if not flips:
        print("⚠️  No ribbon flips found in data")
        return

    # Find optimal entries
    optimal_trades = finder.find_optimal_entries(
        flips,
        min_move_pct=0.3,  # Minimum 0.3% move
        max_hold_minutes=60  # Max 1 hour hold
    )

    # Analyze
    finder.analyze_optimal_trades(optimal_trades)

    # Save
    finder.save_optimal_trades(optimal_trades)

    print("\n" + "="*80)
    print("✅ OPTIMAL TRADE ANALYSIS COMPLETE!")
    print("="*80)

    print("""
NEXT STEPS:
1. Run visualize_trading_analysis.py to see these trades on the chart
2. Compare optimal trades vs actual trades
3. Identify patterns in successful setups
4. Adjust trading rules to capture more optimal trades
    """)


if __name__ == '__main__':
    main()
