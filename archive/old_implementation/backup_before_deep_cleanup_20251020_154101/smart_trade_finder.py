"""
Smart Trade Finder - Realistic backtest with profit targets and stop losses
Simulates actual trading with realistic exits (not just ribbon flips)
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class SmartTradeFinder:
    """
    Find profitable trade setups with realistic profit targets and risk management
    More realistic than simple ribbon flip analysis
    """

    def __init__(self,
                 ema_5min_file='trading_data/ema_data_5min.csv',
                 profit_target_pct=0.008,  # 0.8%
                 stop_loss_pct=0.005):     # 0.5%

        self.ema_5min_file = ema_5min_file
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.trades = []

    def load_data(self, hours_back: int = 24) -> pd.DataFrame:
        """Load EMA data"""

        if not Path(self.ema_5min_file).exists():
            print(f"⚠️  EMA data file not found: {self.ema_5min_file}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(self.ema_5min_file)

            if df.empty:
                return df

            # Convert timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Filter to recent
            cutoff = datetime.now() - timedelta(hours=hours_back)
            df = df[df['timestamp'] >= cutoff]

            # Sort by time
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"⚠️  Error loading EMA data: {e}")
            return pd.DataFrame()

    def count_light_emas(self, row: pd.Series, color: str = 'green') -> int:
        """Count how many light EMAs of given color"""

        count = 0
        for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
            intensity_col = f'ema_{ema}_color_intensity'
            color_col = f'ema_{ema}_color'

            if intensity_col in row and color_col in row:
                if row[color_col] == color and row[intensity_col] == 'light':
                    count += 1

        return count

    def find_smart_trades(self, hours_back: int = 24) -> Dict:
        """
        Find profitable trades using realistic exit strategy
        """

        df = self.load_data(hours_back)

        if df.empty:
            return {
                'status': 'no_data',
                'trades': [],
                'summary': {}
            }

        self.trades = []
        in_position = False
        entry_idx = None
        entry_direction = None
        entry_price = None
        entry_state = None

        for idx in range(len(df) - 1):
            current = df.iloc[idx]
            next_candle = df.iloc[idx + 1]

            current_state = current.get('ribbon_state', '').lower()
            current_price = current.get('close', 0)
            next_high = next_candle.get('high', current_price)
            next_low = next_candle.get('low', current_price)

            # If not in position, look for entry
            if not in_position:
                # LONG entry: ribbon turns green
                if 'green' in current_state:
                    light_green = self.count_light_emas(current, 'green')

                    if light_green >= 8:  # Strong signal
                        in_position = True
                        entry_idx = idx
                        entry_direction = 'LONG'
                        entry_price = current_price
                        entry_state = current_state

                # SHORT entry: ribbon turns red
                elif 'red' in current_state:
                    light_red = self.count_light_emas(current, 'red')

                    if light_red >= 8:  # Strong signal
                        in_position = True
                        entry_idx = idx
                        entry_direction = 'SHORT'
                        entry_price = current_price
                        entry_state = current_state

            # If in position, look for exit
            else:
                exit_triggered = False
                exit_price = None
                exit_reason = None

                if entry_direction == 'LONG':
                    # Check profit target (use high of next candle)
                    if next_high >= entry_price * (1 + self.profit_target_pct):
                        exit_triggered = True
                        exit_price = entry_price * (1 + self.profit_target_pct)
                        exit_reason = 'profit_target'

                    # Check stop loss (use low of next candle)
                    elif next_low <= entry_price * (1 - self.stop_loss_pct):
                        exit_triggered = True
                        exit_price = entry_price * (1 - self.stop_loss_pct)
                        exit_reason = 'stop_loss'

                    # Check ribbon flip
                    elif 'red' in current_state:
                        exit_triggered = True
                        exit_price = current_price
                        exit_reason = 'ribbon_flip'

                elif entry_direction == 'SHORT':
                    # Check profit target (use low of next candle)
                    if next_low <= entry_price * (1 - self.profit_target_pct):
                        exit_triggered = True
                        exit_price = entry_price * (1 - self.profit_target_pct)
                        exit_reason = 'profit_target'

                    # Check stop loss (use high of next candle)
                    elif next_high >= entry_price * (1 + self.stop_loss_pct):
                        exit_triggered = True
                        exit_price = entry_price * (1 + self.stop_loss_pct)
                        exit_reason = 'stop_loss'

                    # Check ribbon flip
                    elif 'green' in current_state:
                        exit_triggered = True
                        exit_price = current_price
                        exit_reason = 'ribbon_flip'

                # Record trade if exit triggered
                if exit_triggered:
                    entry_time = df.iloc[entry_idx]['timestamp']
                    exit_time = current['timestamp']
                    hold_time = (exit_time - entry_time).total_seconds() / 60

                    if entry_direction == 'LONG':
                        pnl_pct = (exit_price - entry_price) / entry_price * 100
                    else:
                        pnl_pct = (entry_price - exit_price) / entry_price * 100

                    self.trades.append({
                        'entry_time': entry_time.isoformat(),
                        'exit_time': exit_time.isoformat(),
                        'direction': entry_direction,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'entry_state': entry_state,
                        'exit_reason': exit_reason,
                        'hold_time_minutes': hold_time,
                        'pnl_pct': pnl_pct,
                        'winner': pnl_pct > 0
                    })

                    # Reset
                    in_position = False
                    entry_idx = None
                    entry_direction = None
                    entry_price = None

        # Calculate summary
        summary = self._calculate_summary()

        return {
            'status': 'success',
            'trades': self.trades,
            'summary': summary
        }

    def _calculate_summary(self) -> Dict:
        """Calculate summary statistics"""

        if not self.trades:
            return {
                'total_trades': 0,
                'winners': 0,
                'losers': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_winner': 0,
                'avg_loser': 0,
                'avg_hold_time': 0
            }

        winners = [t for t in self.trades if t['winner']]
        losers = [t for t in self.trades if not t['winner']]

        return {
            'total_trades': len(self.trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': len(winners) / len(self.trades) if self.trades else 0,
            'total_pnl': sum(t['pnl_pct'] for t in self.trades),
            'avg_winner': sum(t['pnl_pct'] for t in winners) / len(winners) if winners else 0,
            'avg_loser': sum(t['pnl_pct'] for t in losers) / len(losers) if losers else 0,
            'avg_hold_time': sum(t['hold_time_minutes'] for t in self.trades) / len(self.trades),
            'profit_target_hits': len([t for t in self.trades if t['exit_reason'] == 'profit_target']),
            'stop_loss_hits': len([t for t in self.trades if t['exit_reason'] == 'stop_loss']),
            'ribbon_flip_exits': len([t for t in self.trades if t['exit_reason'] == 'ribbon_flip'])
        }

    def get_summary_text(self) -> str:
        """Get formatted summary"""

        if not self.trades:
            return "No smart trades found in the analyzed period."

        summary = self._calculate_summary()

        text = f"""
SMART TRADE FINDER RESULTS
==========================

Configuration:
- Profit Target: {self.profit_target_pct*100:.1f}%
- Stop Loss: {self.stop_loss_pct*100:.1f}%

Performance:
- Total Trades: {summary['total_trades']}
- Winners: {summary['winners']} ({summary['win_rate']*100:.1f}%)
- Losers: {summary['losers']}
- Total PnL: {summary['total_pnl']:.2f}%
- Avg Winner: +{summary['avg_winner']:.2f}%
- Avg Loser: {summary['avg_loser']:.2f}%
- Avg Hold Time: {summary['avg_hold_time']:.1f} minutes

Exit Breakdown:
- Profit Targets Hit: {summary['profit_target_hits']}
- Stop Losses Hit: {summary['stop_loss_hits']}
- Ribbon Flip Exits: {summary['ribbon_flip_exits']}

Best Trades:
"""
        # Show top 5 trades
        sorted_trades = sorted(self.trades, key=lambda x: x['pnl_pct'], reverse=True)[:5]
        for i, trade in enumerate(sorted_trades, 1):
            text += f"{i}. {trade['direction']} +{trade['pnl_pct']:.2f}% | "
            text += f"Hold: {trade['hold_time_minutes']:.0f}min | Exit: {trade['exit_reason']}\n"

        return text.strip()


if __name__ == '__main__':
    # Test the smart trade finder
    finder = SmartTradeFinder(
        profit_target_pct=0.008,  # 0.8%
        stop_loss_pct=0.005       # 0.5%
    )

    result = finder.find_smart_trades(hours_back=24)
    print(finder.get_summary_text())

    # Save trades to JSON
    if result['trades']:
        with open('trading_data/smart_trades.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("\n✅ Trades saved to trading_data/smart_trades.json")
