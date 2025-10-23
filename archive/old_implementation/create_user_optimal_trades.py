"""
Interactive User Optimal Trades Creator
You specify WHEN to enter/exit, we fetch prices and technical details from historical data
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


class UserOptimalTradesCreator:
    """Create optimal trades from user-specified times with automatic data lookup"""

    def __init__(self):
        self.ema_5min_path = 'trading_data/ema_data_5min.csv'
        self.ema_15min_path = 'trading_data/ema_data_15min.csv'
        self.output_path = 'trading_data/optimal_user_trades.json'

        # Load EMA data
        print("📊 Loading historical EMA data...")
        self.df_5min = pd.read_csv(self.ema_5min_path, on_bad_lines='skip')
        self.df_5min['timestamp'] = pd.to_datetime(self.df_5min['timestamp'], errors='coerce')
        self.df_5min = self.df_5min.dropna(subset=['timestamp']).sort_values('timestamp')

        self.df_15min = pd.read_csv(self.ema_15min_path, on_bad_lines='skip')
        self.df_15min['timestamp'] = pd.to_datetime(self.df_15min['timestamp'], errors='coerce')
        self.df_15min = self.df_15min.dropna(subset=['timestamp']).sort_values('timestamp')

        print(f"✅ Loaded {len(self.df_5min)} 5min candles")
        print(f"✅ Loaded {len(self.df_15min)} 15min candles")

        # Show date range
        if len(self.df_5min) > 0:
            print(f"📅 Data range: {self.df_5min['timestamp'].min()} to {self.df_5min['timestamp'].max()}")

    def find_closest_candle(self, target_time: datetime, timeframe='5min'):
        """Find the closest candle to the target time"""
        df = self.df_5min if timeframe == '5min' else self.df_15min

        # Find closest timestamp
        time_diffs = (df['timestamp'] - target_time).abs()
        closest_idx = time_diffs.idxmin()

        return df.loc[closest_idx]

    def extract_ema_details(self, candle, direction):
        """Extract EMA pattern details from a candle"""

        # Count EMAs by color and intensity
        light_emas = 0
        dark_emas = 0
        green_count = 0
        red_count = 0
        yellow_count = 0
        gray_count = 0

        for ema in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]:
            color_col = f'MMA{ema}_color'
            intensity_col = f'MMA{ema}_intensity'

            if color_col in candle.index and intensity_col in candle.index:
                color = candle[color_col]
                intensity = candle[intensity_col]

                # Count by color
                if color == 'green':
                    green_count += 1
                    if intensity == 'light' and direction == 'LONG':
                        light_emas += 1
                    elif intensity == 'dark':
                        dark_emas += 1
                elif color == 'red':
                    red_count += 1
                    if intensity == 'light' and direction == 'SHORT':
                        light_emas += 1
                    elif intensity == 'dark':
                        dark_emas += 1
                elif color == 'yellow':
                    yellow_count += 1
                elif color == 'gray':
                    gray_count += 1

        # Calculate compression
        ema_values = []
        for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
            val_col = f'MMA{ema}_value'
            if val_col in candle.index and pd.notna(candle[val_col]):
                ema_values.append(float(candle[val_col]))

        if len(ema_values) >= 3:
            ema_min = min(ema_values)
            ema_max = max(ema_values)
            compression = (ema_max - ema_min) / ema_min if ema_min > 0 else 0
        else:
            compression = 0

        return {
            'light_emas': light_emas,
            'dark_emas': dark_emas,
            'green_count': green_count,
            'red_count': red_count,
            'yellow_count': yellow_count,
            'gray_count': gray_count,
            'compression': compression,
            'ribbon_state': candle.get('ribbon_state', 'unknown'),
            'price': candle.get('price', candle.get('close', 0))
        }

    def create_trade_from_times(self, entry_time: datetime, exit_time: datetime, direction: str):
        """Create a trade entry by looking up historical data at specified times"""

        print(f"\n🔍 Looking up data for {direction} trade...")
        print(f"   Entry: {entry_time}")
        print(f"   Exit: {exit_time}")

        # Find closest candles
        entry_candle = self.find_closest_candle(entry_time, '5min')
        exit_candle = self.find_closest_candle(exit_time, '5min')

        actual_entry_time = entry_candle['timestamp']
        actual_exit_time = exit_candle['timestamp']

        entry_price = entry_candle.get('price', entry_candle.get('close', 0))
        exit_price = exit_candle.get('price', exit_candle.get('close', 0))

        # Calculate PnL
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        # Extract EMA details at entry
        ema_details = self.extract_ema_details(entry_candle, direction)

        # Calculate hold time
        hold_time_minutes = (actual_exit_time - actual_entry_time).total_seconds() / 60

        trade = {
            'entry_time': actual_entry_time.isoformat(),
            'exit_time': actual_exit_time.isoformat(),
            'direction': direction,
            'entry_price': float(entry_price),
            'exit_price': float(exit_price),
            'pnl_pct': float(pnl_pct),
            'hold_time_minutes': float(hold_time_minutes),
            'winner': pnl_pct > 0,
            'compression': float(ema_details['compression']),
            'light_emas': int(ema_details['light_emas']),
            'ribbon_state': str(ema_details['ribbon_state']),
            'ema_pattern': {
                'green_count': int(ema_details['green_count']),
                'red_count': int(ema_details['red_count']),
                'yellow_count': int(ema_details['yellow_count']),
                'gray_count': int(ema_details['gray_count']),
                'dark_emas': int(ema_details['dark_emas'])
            },
            'source': 'user_specified'
        }

        # Print summary
        print(f"\n✅ Trade created:")
        print(f"   Actual Entry: {actual_entry_time} @ ${entry_price:.2f}")
        print(f"   Actual Exit:  {actual_exit_time} @ ${exit_price:.2f}")
        print(f"   PnL: {pnl_pct:+.2f}% ({'WIN' if pnl_pct > 0 else 'LOSS'})")
        print(f"   Hold Time: {hold_time_minutes:.1f} minutes")
        print(f"   Ribbon State: {ema_details['ribbon_state']}")
        print(f"   Light EMAs: {ema_details['light_emas']}")
        print(f"   Compression: {ema_details['compression']*100:.2f}%")
        print(f"   EMA Colors: {ema_details['green_count']} green, {ema_details['red_count']} red")

        return trade

    def interactive_input(self):
        """Interactive mode for creating trades"""

        print("\n" + "="*70)
        print("USER OPTIMAL TRADES CREATOR")
        print("="*70)
        print("Specify WHEN to enter/exit, I'll fetch prices and technical details")
        print()
        print("Time format options:")
        print("  1. Absolute: 2025-10-21 14:30:00")
        print("  2. Relative: 2h30m ago, 1d ago, 45m ago")
        print("="*70)

        trades = []

        while True:
            print(f"\n{'='*70}")
            print(f"TRADE #{len(trades) + 1}")
            print(f"{'='*70}")

            # Entry time
            entry_input = input("\nEntry time [or 'done' to finish]: ").strip()
            if entry_input.lower() == 'done':
                break

            entry_time = self.parse_time(entry_input)
            if not entry_time:
                print("❌ Invalid time format")
                continue

            # Direction
            direction = input("Direction (LONG/SHORT): ").strip().upper()
            if direction not in ['LONG', 'SHORT']:
                print("❌ Direction must be LONG or SHORT")
                continue

            # Exit time
            exit_input = input("Exit time: ").strip()
            exit_time = self.parse_time(exit_input)
            if not exit_time:
                print("❌ Invalid time format")
                continue

            # Validate times
            if exit_time <= entry_time:
                print("❌ Exit time must be after entry time")
                continue

            # Create trade
            try:
                trade = self.create_trade_from_times(entry_time, exit_time, direction)
                trades.append(trade)

                confirm = input("\n✅ Add this trade? (y/n): ").strip().lower()
                if confirm != 'y':
                    trades.pop()
                    print("❌ Trade discarded")
            except Exception as e:
                print(f"❌ Error creating trade: {e}")
                import traceback
                traceback.print_exc()

        return trades

    def parse_time(self, time_str: str) -> datetime:
        """Parse time from various formats"""

        time_str = time_str.strip()

        # Try absolute format first
        try:
            return datetime.fromisoformat(time_str)
        except:
            pass

        # Try relative format (e.g., "2h30m ago", "1d ago")
        if 'ago' in time_str.lower():
            time_str = time_str.lower().replace('ago', '').strip()

            total_minutes = 0

            # Parse days
            if 'd' in time_str:
                days = int(time_str.split('d')[0])
                total_minutes += days * 24 * 60
                time_str = time_str.split('d', 1)[1] if 'd' in time_str else ''

            # Parse hours
            if 'h' in time_str:
                hours = int(time_str.split('h')[0])
                total_minutes += hours * 60
                time_str = time_str.split('h', 1)[1] if 'h' in time_str else ''

            # Parse minutes
            if 'm' in time_str:
                minutes = int(time_str.split('m')[0])
                total_minutes += minutes

            return datetime.now() - timedelta(minutes=total_minutes)

        return None

    def save_trades(self, trades):
        """Save trades to JSON file"""

        if not trades:
            print("\n❌ No trades to save")
            return

        # Calculate summary statistics
        total_trades = len(trades)
        winners = [t for t in trades if t['winner']]
        losers = [t for t in trades if not t['winner']]

        total_pnl_pct = sum(t['pnl_pct'] for t in trades)
        avg_pnl_pct = total_pnl_pct / total_trades
        win_rate = len(winners) / total_trades

        avg_compression = sum(t['compression'] for t in trades) / total_trades
        avg_light_emas = sum(t['light_emas'] for t in trades) / total_trades
        avg_hold_time = sum(t['hold_time_minutes'] for t in trades) / total_trades

        # Create full data structure
        optimal_data = {
            'analysis_timestamp': datetime.now().isoformat(),
            'source': 'user_specified_times',
            'description': 'User-specified optimal trades with auto-fetched technical details',
            'total_trades': total_trades,
            'winning_trades': len(winners),
            'losing_trades': len(losers),
            'win_rate': win_rate,
            'total_pnl_pct': total_pnl_pct,
            'avg_pnl_pct': avg_pnl_pct,
            'avg_winner_pct': sum(t['pnl_pct'] for t in winners) / len(winners) if winners else 0,
            'avg_loser_pct': sum(t['pnl_pct'] for t in losers) / len(losers) if losers else 0,
            'avg_hold_time_minutes': avg_hold_time,
            'patterns': {
                'avg_compression': avg_compression,
                'avg_light_emas': avg_light_emas
            },
            'trades': trades
        }

        # Save to file
        with open(self.output_path, 'w') as f:
            json.dump(optimal_data, f, indent=2)

        # Print summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate: {win_rate*100:.1f}%")
        print(f"Total PnL: {total_pnl_pct:+.2f}%")
        print(f"Avg PnL per Trade: {avg_pnl_pct:+.2f}%")
        print(f"Avg Hold Time: {avg_hold_time:.1f} minutes")
        print(f"Avg Compression: {avg_compression*100:.2f}%")
        print(f"Avg Light EMAs: {avg_light_emas:.1f}")
        print("="*70)
        print(f"\n✅ Saved to {self.output_path}")
        print("\n📝 To use these as your optimization target:")
        print("   1. Add to .env: OPTIMAL_TRADES_SOURCE=user")
        print("   2. Run: python3 run_claude_optimization.py 5 24")


def main():
    """Main function"""
    creator = UserOptimalTradesCreator()
    trades = creator.interactive_input()
    creator.save_trades(trades)


if __name__ == '__main__':
    main()
