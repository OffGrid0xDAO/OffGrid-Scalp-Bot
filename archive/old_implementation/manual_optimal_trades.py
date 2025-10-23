"""
Manual Optimal Trades Input Tool
Allows you to manually input optimal trade entries/exits from the Claude terminal
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


class ManualOptimalTradesInput:
    """Interactive tool for manually adding optimal trades"""

    def __init__(self):
        self.optimal_trades_path = 'trading_data/optimal_trades.json'
        self.ema_data_path = 'trading_data/ema_data_5min.csv'

        # Load existing data
        self.load_existing_trades()
        self.load_ema_data()

    def load_existing_trades(self):
        """Load existing optimal trades if they exist"""
        try:
            if Path(self.optimal_trades_path).exists():
                with open(self.optimal_trades_path, 'r') as f:
                    data = json.load(f)
                    self.trades = data.get('trades', [])
                    print(f"✅ Loaded {len(self.trades)} existing optimal trades")
            else:
                self.trades = []
                print("📝 Starting with empty optimal trades list")
        except Exception as e:
            print(f"⚠️  Error loading existing trades: {e}")
            self.trades = []

    def load_ema_data(self):
        """Load EMA data to get price information"""
        try:
            if Path(self.ema_data_path).exists():
                self.df = pd.read_csv(self.ema_data_path)
                self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
                print(f"✅ Loaded EMA data: {len(self.df)} rows")
                print(f"   Date range: {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
            else:
                print("⚠️  No EMA data found - you'll need to enter prices manually")
                self.df = None
        except Exception as e:
            print(f"⚠️  Error loading EMA data: {e}")
            self.df = None

    def parse_datetime_input(self, prompt: str) -> datetime:
        """Parse user datetime input in various formats"""
        print(f"\n{prompt}")
        print("Formats accepted:")
        print("  1. 'YYYY-MM-DD HH:MM' (e.g., '2025-10-20 14:30')")
        print("  2. 'MM-DD HH:MM' (assumes current year, e.g., '10-20 14:30')")
        print("  3. 'DD HH:MM' (assumes current month/year, e.g., '20 14:30')")
        print("  4. 'HH:MM' (assumes today, e.g., '14:30')")
        print("  5. '1d 14:30' (1 day ago at 14:30)")
        print("  6. '2h' (2 hours ago)")

        while True:
            user_input = input("\nEnter time: ").strip()

            try:
                now = datetime.now()

                # Format 1: Full datetime
                if len(user_input.split()) == 2 and '-' in user_input.split()[0]:
                    date_part, time_part = user_input.split()
                    if date_part.count('-') == 2:  # YYYY-MM-DD
                        dt = datetime.strptime(user_input, '%Y-%m-%d %H:%M')
                    elif date_part.count('-') == 1:  # MM-DD
                        dt = datetime.strptime(f"{now.year}-{user_input}", '%Y-%m-%d %H:%M')
                    return dt

                # Format 2: DD HH:MM
                elif len(user_input.split()) == 2 and user_input.split()[0].isdigit():
                    day, time_part = user_input.split()
                    dt = datetime.strptime(f"{now.year}-{now.month:02d}-{day} {time_part}", '%Y-%m-%d %H:%M')
                    return dt

                # Format 3: HH:MM (today)
                elif ':' in user_input and len(user_input.split()) == 1:
                    dt = datetime.strptime(f"{now.year}-{now.month:02d}-{now.day:02d} {user_input}", '%Y-%m-%d %H:%M')
                    return dt

                # Format 4: Relative time (e.g., "1d 14:30" or "2h")
                elif 'd' in user_input or 'h' in user_input:
                    if 'd' in user_input:
                        parts = user_input.split()
                        days = int(parts[0].replace('d', ''))
                        if len(parts) == 2:
                            time_part = parts[1]
                            dt = now - timedelta(days=days)
                            dt = datetime.strptime(f"{dt.year}-{dt.month:02d}-{dt.day:02d} {time_part}", '%Y-%m-%d %H:%M')
                        else:
                            dt = now - timedelta(days=days)
                        return dt
                    elif 'h' in user_input:
                        hours = int(user_input.replace('h', ''))
                        return now - timedelta(hours=hours)

                else:
                    print("❌ Invalid format. Please try again.")

            except Exception as e:
                print(f"❌ Error parsing time: {e}. Please try again.")

    def get_price_at_time(self, dt: datetime, fallback_prompt: str) -> float:
        """Get price at a specific time from EMA data or user input"""
        if self.df is not None:
            # Find closest timestamp in data
            time_diff = abs(self.df['timestamp'] - dt)
            if time_diff.min() < pd.Timedelta(minutes=5):
                closest_idx = time_diff.idxmin()
                price = self.df.loc[closest_idx, 'price']
                closest_time = self.df.loc[closest_idx, 'timestamp']
                print(f"   📊 Price at {closest_time}: ${price:.2f}")

                use_price = input("   Use this price? (y/n): ").strip().lower()
                if use_price == 'y':
                    return float(price)

        # Manual input
        while True:
            try:
                price_input = input(f"   {fallback_prompt}: $").strip()
                return float(price_input)
            except ValueError:
                print("   ❌ Invalid price. Please enter a number.")

    def add_trade(self):
        """Interactive prompt to add a single trade"""
        print("\n" + "="*70)
        print("📝 ADD NEW OPTIMAL TRADE")
        print("="*70)

        # Direction
        while True:
            direction = input("\nDirection (LONG/SHORT): ").strip().upper()
            if direction in ['LONG', 'SHORT']:
                break
            print("❌ Please enter LONG or SHORT")

        # Entry time
        entry_time = self.parse_datetime_input("📅 ENTRY TIME")
        entry_price = self.get_price_at_time(entry_time, "Enter entry price")

        # Exit time
        exit_time = self.parse_datetime_input("📅 EXIT TIME")
        exit_price = self.get_price_at_time(exit_time, "Enter exit price")

        # Calculate metrics
        hold_time = (exit_time - entry_time).total_seconds() / 60

        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        # Create trade
        trade = {
            'entry_time': entry_time.isoformat(),
            'exit_time': exit_time.isoformat(),
            'direction': direction,
            'entry_price': float(entry_price),
            'exit_price': float(exit_price),
            'hold_time_minutes': float(hold_time),
            'pnl_pct': float(pnl_pct),
            'manual_input': True
        }

        # Show summary
        print("\n" + "─"*70)
        print("📊 TRADE SUMMARY")
        print("─"*70)
        print(f"Direction: {direction}")
        print(f"Entry: {entry_time.strftime('%Y-%m-%d %H:%M')} @ ${entry_price:.2f}")
        print(f"Exit:  {exit_time.strftime('%Y-%m-%d %H:%M')} @ ${exit_price:.2f}")
        print(f"Hold Time: {hold_time:.1f} minutes")
        print(f"PnL: {pnl_pct:+.2f}%")
        print("─"*70)

        # Confirm
        confirm = input("\n✅ Add this trade? (y/n): ").strip().lower()
        if confirm == 'y':
            self.trades.append(trade)
            print(f"✅ Trade added! Total optimal trades: {len(self.trades)}")
            return True
        else:
            print("❌ Trade cancelled")
            return False

    def save_trades(self):
        """Save all trades to JSON file"""
        # Calculate summary stats
        if self.trades:
            total_pnl = sum(t['pnl_pct'] for t in self.trades)
            avg_pnl = total_pnl / len(self.trades)
            avg_hold = sum(t['hold_time_minutes'] for t in self.trades) / len(self.trades)
            winners = [t for t in self.trades if t['pnl_pct'] > 0]
            win_rate = len(winners) / len(self.trades) if self.trades else 0
        else:
            total_pnl = 0
            avg_pnl = 0
            avg_hold = 0
            win_rate = 0

        data = {
            'status': 'success',
            'trades': self.trades,
            'total_trades': len(self.trades),
            'total_pnl_pct': total_pnl,
            'avg_pnl_pct': avg_pnl,
            'avg_hold_minutes': avg_hold,
            'win_rate': win_rate,
            'last_updated': datetime.now().isoformat(),
            'source': 'manual_input'
        }

        # Ensure directory exists
        Path(self.optimal_trades_path).parent.mkdir(parents=True, exist_ok=True)

        # Save
        with open(self.optimal_trades_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n✅ Saved {len(self.trades)} trades to {self.optimal_trades_path}")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Avg PnL: {avg_pnl:+.2f}%")
        print(f"   Win Rate: {win_rate*100:.1f}%")

    def run_interactive(self):
        """Main interactive loop"""
        print("\n" + "="*70)
        print("🎯 MANUAL OPTIMAL TRADES INPUT TOOL")
        print("="*70)
        print("\nThis tool allows you to manually input optimal trades that you")
        print("identified through chart analysis or historical review.")
        print("\nThese trades will be used as the 'perfect' baseline for comparing")
        print("your trading rules performance.\n")

        while True:
            print("\n" + "─"*70)
            print("OPTIONS:")
            print("  [1] Add a new trade")
            print("  [2] View all trades")
            print("  [3] Remove a trade")
            print("  [4] Save and exit")
            print("  [5] Exit without saving")
            print("─"*70)

            choice = input("\nYour choice: ").strip()

            if choice == '1':
                self.add_trade()

            elif choice == '2':
                self.view_trades()

            elif choice == '3':
                self.remove_trade()

            elif choice == '4':
                self.save_trades()
                print("\n👋 Goodbye!")
                break

            elif choice == '5':
                confirm = input("⚠️  Exit without saving? (y/n): ").strip().lower()
                if confirm == 'y':
                    print("\n👋 Goodbye!")
                    break

            else:
                print("❌ Invalid choice")

    def view_trades(self):
        """Display all trades"""
        if not self.trades:
            print("\n📭 No trades yet")
            return

        print("\n" + "="*70)
        print(f"📊 ALL OPTIMAL TRADES ({len(self.trades)} total)")
        print("="*70)

        for i, trade in enumerate(self.trades, 1):
            entry_dt = datetime.fromisoformat(trade['entry_time'])
            exit_dt = datetime.fromisoformat(trade['exit_time'])
            print(f"\n[{i}] {trade['direction']}")
            print(f"    Entry: {entry_dt.strftime('%Y-%m-%d %H:%M')} @ ${trade['entry_price']:.2f}")
            print(f"    Exit:  {exit_dt.strftime('%Y-%m-%d %H:%M')} @ ${trade['exit_price']:.2f}")
            print(f"    Hold: {trade['hold_time_minutes']:.1f}min | PnL: {trade['pnl_pct']:+.2f}%")

    def remove_trade(self):
        """Remove a trade by index"""
        if not self.trades:
            print("\n📭 No trades to remove")
            return

        self.view_trades()

        try:
            idx = int(input("\nEnter trade number to remove (0 to cancel): ").strip())
            if idx == 0:
                return
            if 1 <= idx <= len(self.trades):
                removed = self.trades.pop(idx - 1)
                print(f"✅ Removed trade: {removed['direction']} @ {removed['entry_time']}")
            else:
                print("❌ Invalid trade number")
        except ValueError:
            print("❌ Please enter a valid number")


def main():
    """Run the manual optimal trades input tool"""
    tool = ManualOptimalTradesInput()
    tool.run_interactive()


if __name__ == '__main__':
    main()
