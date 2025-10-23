"""
Manual Trade Tracker
Logs manual trades separately from automated trades
Used by Claude to compare human intuition vs bot rules
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class ManualTradeTracker:
    """Track manual trades initiated via Telegram commands"""

    def __init__(self, log_file: str = 'trading_data/manual_trades.json'):
        self.log_file = log_file
        self.trades = []
        self.load_trades()

    def load_trades(self):
        """Load existing manual trades"""
        try:
            if Path(self.log_file).exists():
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    self.trades = data.get('trades', [])
            else:
                self.trades = []
        except Exception as e:
            print(f"⚠️  Error loading manual trades: {e}")
            self.trades = []

    def save_trades(self):
        """Save manual trades to file"""
        try:
            Path(self.log_file).parent.mkdir(exist_ok=True)

            data = {
                'last_updated': datetime.now().isoformat(),
                'total_trades': len(self.trades),
                'trades': self.trades
            }

            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            print(f"⚠️  Error saving manual trades: {e}")

    def log_entry(self, direction: str, price: float, size: float,
                  reasoning: str = "Manual gut feeling") -> str:
        """
        Log a manual entry

        Args:
            direction: 'LONG' or 'SHORT'
            price: Entry price
            size: Position size
            reasoning: Why you entered (optional)

        Returns:
            Trade ID
        """
        trade_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        trade = {
            'id': trade_id,
            'type': 'entry',
            'direction': direction,
            'entry_time': datetime.now().isoformat(),
            'entry_price': price,
            'size': size,
            'reasoning': reasoning,
            'status': 'open',
            'exit_time': None,
            'exit_price': None,
            'exit_reason': None,
            'pnl_pct': 0,
            'pnl_usd': 0
        }

        self.trades.append(trade)
        self.save_trades()

        print(f"📝 Manual {direction} logged: {trade_id}")
        return trade_id

    def log_exit(self, trade_id: str, price: float, reason: str = "Manual exit") -> bool:
        """
        Log a manual exit

        Args:
            trade_id: ID of the trade to close
            price: Exit price
            reason: Exit reason

        Returns:
            Success status
        """
        for trade in self.trades:
            if trade['id'] == trade_id and trade['status'] == 'open':
                # Calculate PnL
                entry_price = trade['entry_price']
                direction = trade['direction']

                if direction == 'LONG':
                    pnl_pct = (price - entry_price) / entry_price * 100
                else:  # SHORT
                    pnl_pct = (entry_price - price) / entry_price * 100

                pnl_usd = (pnl_pct / 100) * (trade['size'] * entry_price)

                # Update trade
                trade['exit_time'] = datetime.now().isoformat()
                trade['exit_price'] = price
                trade['exit_reason'] = reason
                trade['status'] = 'closed'
                trade['pnl_pct'] = pnl_pct
                trade['pnl_usd'] = pnl_usd

                self.save_trades()

                print(f"📝 Manual exit logged: {trade_id} ({pnl_pct:+.2f}%)")
                return True

        print(f"⚠️  Trade not found or already closed: {trade_id}")
        return False

    def get_open_trade(self) -> Dict:
        """Get the currently open manual trade"""
        for trade in reversed(self.trades):  # Check most recent first
            if trade['status'] == 'open':
                return trade
        return None

    def get_stats(self) -> Dict:
        """Get statistics for manual trades"""
        closed_trades = [t for t in self.trades if t['status'] == 'closed']

        if not closed_trades:
            return {
                'total_trades': 0,
                'winners': 0,
                'losers': 0,
                'win_rate': 0,
                'total_pnl_pct': 0,
                'avg_pnl_pct': 0
            }

        winners = [t for t in closed_trades if t['pnl_pct'] > 0]
        losers = [t for t in closed_trades if t['pnl_pct'] <= 0]

        total_pnl = sum(t['pnl_pct'] for t in closed_trades)

        return {
            'total_trades': len(closed_trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': len(winners) / len(closed_trades) if closed_trades else 0,
            'total_pnl_pct': total_pnl,
            'avg_pnl_pct': total_pnl / len(closed_trades) if closed_trades else 0
        }

    def export_for_claude_analysis(self) -> Dict:
        """
        Export manual trades in format suitable for Claude analysis

        Returns:
            Dict with manual trade performance data
        """
        stats = self.get_stats()
        closed_trades = [t for t in self.trades if t['status'] == 'closed']

        # Calculate average hold time
        hold_times = []
        for trade in closed_trades:
            try:
                entry_dt = datetime.fromisoformat(trade['entry_time'])
                exit_dt = datetime.fromisoformat(trade['exit_time'])
                hold_minutes = (exit_dt - entry_dt).total_seconds() / 60
                hold_times.append(hold_minutes)
            except:
                pass

        avg_hold = sum(hold_times) / len(hold_times) if hold_times else 0

        return {
            'total_trades': stats['total_trades'],
            'total_pnl_pct': stats['total_pnl_pct'],
            'avg_pnl_pct': stats['avg_pnl_pct'],
            'win_rate': stats['win_rate'],
            'avg_hold_minutes': avg_hold,
            'trades': closed_trades
        }


if __name__ == '__main__':
    # Test the tracker
    tracker = ManualTradeTracker()

    # Log a manual long
    trade_id = tracker.log_entry('LONG', 3985.50, 0.1, "Strong bullish setup, gut feeling")

    print(f"\nOpen trade: {tracker.get_open_trade()}")

    # Simulate exit
    import time
    time.sleep(2)
    tracker.log_exit(trade_id, 4005.30, "Profit target reached")

    print(f"\nStats: {tracker.get_stats()}")
