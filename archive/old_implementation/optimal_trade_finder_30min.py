"""
Optimal Trade Finder - 30 Minute Window
Analyzes the last 30 minutes of EMA data to find what WOULD have been profitable trades.
Used by the rule optimizer to identify winning patterns.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json


class OptimalTradeFinder:
    """Finds optimal trade setups from historical EMA data"""

    def __init__(self, ema_data_path_5min: str, ema_data_path_15min: str):
        self.ema_data_path_5min = ema_data_path_5min
        self.ema_data_path_15min = ema_data_path_15min
        self.profit_target_pct = 0.005  # 0.5% profit target
        self.stop_loss_pct = 0.003  # 0.3% stop loss
        self.max_hold_minutes = 15  # Maximum hold time

    def load_last_30min(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load last 30 minutes of EMA data from both timeframes"""
        # Use on_bad_lines='skip' to handle corrupted CSV lines
        df_5min = pd.read_csv(self.ema_data_path_5min, on_bad_lines='skip')
        df_15min = pd.read_csv(self.ema_data_path_15min, on_bad_lines='skip')

        # Convert timestamp to datetime
        df_5min['timestamp'] = pd.to_datetime(df_5min['timestamp'], errors='coerce')
        df_15min['timestamp'] = pd.to_datetime(df_15min['timestamp'], errors='coerce')

        # Drop rows with invalid timestamps
        df_5min = df_5min.dropna(subset=['timestamp'])
        df_15min = df_15min.dropna(subset=['timestamp'])

        # Get last 30 minutes
        cutoff_time = datetime.now() - timedelta(minutes=30)
        df_5min = df_5min[df_5min['timestamp'] >= cutoff_time].copy()
        df_15min = df_15min[df_15min['timestamp'] >= cutoff_time].copy()

        return df_5min, df_15min

    def extract_ema_pattern(self, row: pd.Series) -> Dict:
        """Extract EMA color pattern from a data row"""
        pattern = {
            'green_count': 0,
            'red_count': 0,
            'gray_count': 0,
            'yellow_count': 0,
            'light_green_count': 0,
            'light_red_count': 0,
            'dark_green_count': 0,
            'dark_red_count': 0,
            'ribbon_state': row['ribbon_state'],
            'price': row['price']
        }

        # Count EMAs by color and intensity
        ema_cols = [col for col in row.index if col.startswith('MMA') and col.endswith('_color')]

        for ema_col in ema_cols:
            color = row[ema_col]
            intensity_col = ema_col.replace('_color', '_intensity')
            intensity = row.get(intensity_col, 'normal')

            if color == 'green':
                pattern['green_count'] += 1
                if intensity == 'light':
                    pattern['light_green_count'] += 1
                elif intensity == 'dark':
                    pattern['dark_green_count'] += 1
            elif color == 'red':
                pattern['red_count'] += 1
                if intensity == 'light':
                    pattern['light_red_count'] += 1
                elif intensity == 'dark':
                    pattern['dark_red_count'] += 1
            elif color == 'yellow':
                pattern['yellow_count'] += 1
            elif color == 'gray':
                pattern['gray_count'] += 1

        # Calculate percentages
        total_non_yellow = pattern['green_count'] + pattern['red_count'] + pattern['gray_count']
        if total_non_yellow > 0:
            pattern['green_pct'] = pattern['green_count'] / total_non_yellow
            pattern['red_pct'] = pattern['red_count'] / total_non_yellow
        else:
            pattern['green_pct'] = 0
            pattern['red_pct'] = 0

        return pattern

    def find_ribbon_flips(self, df: pd.DataFrame) -> List[Dict]:
        """Find all ribbon flip points in the dataframe"""
        flips = []

        for i in range(1, len(df)):
            prev_state = df.iloc[i-1]['ribbon_state']
            curr_state = df.iloc[i]['ribbon_state']

            # Detect flip to bullish
            if prev_state in ['all_red', 'mixed_red', 'mixed'] and curr_state in ['all_green', 'mixed_green']:
                flips.append({
                    'index': i,
                    'timestamp': df.iloc[i]['timestamp'],
                    'direction': 'LONG',
                    'prev_state': prev_state,
                    'curr_state': curr_state,
                    'entry_price': df.iloc[i]['price'],
                    'pattern_5min': self.extract_ema_pattern(df.iloc[i])
                })

            # Detect flip to bearish
            elif prev_state in ['all_green', 'mixed_green', 'mixed'] and curr_state in ['all_red', 'mixed_red']:
                flips.append({
                    'index': i,
                    'timestamp': df.iloc[i]['timestamp'],
                    'direction': 'SHORT',
                    'prev_state': prev_state,
                    'curr_state': curr_state,
                    'entry_price': df.iloc[i]['price'],
                    'pattern_5min': self.extract_ema_pattern(df.iloc[i])
                })

        return flips

    def simulate_trade(self, entry_idx: int, entry_price: float, direction: str, df: pd.DataFrame) -> Dict:
        """Simulate a trade from entry point to see if it would have been profitable"""
        result = {
            'profitable': False,
            'pnl': 0,
            'pnl_pct': 0,
            'exit_reason': None,
            'hold_minutes': 0,
            'peak_profit_pct': 0,
            'max_drawdown_pct': 0
        }

        entry_time = df.iloc[entry_idx]['timestamp']
        max_exit_time = entry_time + timedelta(minutes=self.max_hold_minutes)

        peak_profit_pct = 0
        max_drawdown_pct = 0

        # Simulate forward from entry
        for i in range(entry_idx + 1, len(df)):
            row = df.iloc[i]
            current_price = row['price']
            current_time = row['timestamp']

            # Calculate PnL
            if direction == 'LONG':
                pnl_pct = (current_price - entry_price) / entry_price
            else:  # SHORT
                pnl_pct = (entry_price - current_price) / entry_price

            # Track peak and drawdown
            peak_profit_pct = max(peak_profit_pct, pnl_pct)
            max_drawdown_pct = min(max_drawdown_pct, pnl_pct)

            hold_minutes = (current_time - entry_time).total_seconds() / 60

            # Check profit target
            if pnl_pct >= self.profit_target_pct:
                result['profitable'] = True
                result['pnl_pct'] = pnl_pct
                result['exit_reason'] = 'profit_target'
                result['hold_minutes'] = hold_minutes
                result['peak_profit_pct'] = peak_profit_pct
                result['max_drawdown_pct'] = max_drawdown_pct
                return result

            # Check stop loss
            if pnl_pct <= -self.stop_loss_pct:
                result['profitable'] = False
                result['pnl_pct'] = pnl_pct
                result['exit_reason'] = 'stop_loss'
                result['hold_minutes'] = hold_minutes
                result['peak_profit_pct'] = peak_profit_pct
                result['max_drawdown_pct'] = max_drawdown_pct
                return result

            # Check ribbon flip (exit signal)
            if direction == 'LONG' and row['ribbon_state'] in ['all_red', 'mixed_red']:
                result['profitable'] = pnl_pct > 0
                result['pnl_pct'] = pnl_pct
                result['exit_reason'] = 'ribbon_flip'
                result['hold_minutes'] = hold_minutes
                result['peak_profit_pct'] = peak_profit_pct
                result['max_drawdown_pct'] = max_drawdown_pct
                return result

            if direction == 'SHORT' and row['ribbon_state'] in ['all_green', 'mixed_green']:
                result['profitable'] = pnl_pct > 0
                result['pnl_pct'] = pnl_pct
                result['exit_reason'] = 'ribbon_flip'
                result['hold_minutes'] = hold_minutes
                result['peak_profit_pct'] = peak_profit_pct
                result['max_drawdown_pct'] = max_drawdown_pct
                return result

            # Check max hold time
            if current_time >= max_exit_time:
                result['profitable'] = pnl_pct > 0
                result['pnl_pct'] = pnl_pct
                result['exit_reason'] = 'max_hold_time'
                result['hold_minutes'] = hold_minutes
                result['peak_profit_pct'] = peak_profit_pct
                result['max_drawdown_pct'] = max_drawdown_pct
                return result

        # Reached end of data
        if len(df) > entry_idx + 1:
            last_row = df.iloc[-1]
            last_price = last_row['price']
            if direction == 'LONG':
                pnl_pct = (last_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - last_price) / entry_price

            result['profitable'] = pnl_pct > 0
            result['pnl_pct'] = pnl_pct
            result['exit_reason'] = 'end_of_data'
            result['hold_minutes'] = (last_row['timestamp'] - entry_time).total_seconds() / 60
            result['peak_profit_pct'] = peak_profit_pct
            result['max_drawdown_pct'] = max_drawdown_pct

        return result

    def analyze_optimal_setups(self) -> Dict:
        """Main function: Find all optimal trade setups from last 30 minutes"""
        df_5min, df_15min = self.load_last_30min()

        if len(df_5min) == 0:
            return {
                'error': 'No data in last 30 minutes',
                'optimal_trades': [],
                'winning_patterns': [],
                'losing_patterns': []
            }

        # Find all ribbon flips
        flips = self.find_ribbon_flips(df_5min)

        # Simulate each trade
        optimal_trades = []
        winning_patterns = []
        losing_patterns = []

        for flip in flips:
            trade_result = self.simulate_trade(
                flip['index'],
                flip['entry_price'],
                flip['direction'],
                df_5min
            )

            trade = {
                **flip,
                **trade_result
            }

            optimal_trades.append(trade)

            if trade_result['profitable']:
                winning_patterns.append(flip['pattern_5min'])
            else:
                losing_patterns.append(flip['pattern_5min'])

        # Calculate summary statistics
        total_trades = len(optimal_trades)
        winning_trades = sum(1 for t in optimal_trades if t['profitable'])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        avg_winner_pnl = sum(t['pnl_pct'] for t in optimal_trades if t['profitable']) / max(winning_trades, 1)
        avg_loser_pnl = sum(t['pnl_pct'] for t in optimal_trades if not t['profitable']) / max(total_trades - winning_trades, 1)

        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'data_window_minutes': 30,
            'total_ribbon_flips': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'avg_winner_pnl_pct': avg_winner_pnl * 100,
            'avg_loser_pnl_pct': avg_loser_pnl * 100,
            'optimal_trades': optimal_trades,
            'winning_patterns': winning_patterns,
            'losing_patterns': losing_patterns
        }


def main():
    """Test the optimal trade finder"""
    finder = OptimalTradeFinder(
        ema_data_path_5min='trading_data/ema_data_5min.csv',
        ema_data_path_15min='trading_data/ema_data_15min.csv'
    )

    results = finder.analyze_optimal_setups()

    print("\n" + "="*60)
    print("OPTIMAL TRADE ANALYSIS - LAST 30 MINUTES")
    print("="*60)
    print(f"Analysis Time: {results['analysis_timestamp']}")
    print(f"Total Ribbon Flips Found: {results['total_ribbon_flips']}")
    print(f"Winning Trades: {results['winning_trades']}")
    print(f"Losing Trades: {results['losing_trades']}")
    print(f"Win Rate: {results['win_rate']*100:.1f}%")
    print(f"Avg Winner P&L: {results['avg_winner_pnl_pct']:.2f}%")
    print(f"Avg Loser P&L: {results['avg_loser_pnl_pct']:.2f}%")
    print("="*60)

    # Show details of each optimal trade
    for i, trade in enumerate(results['optimal_trades'], 1):
        print(f"\n Trade #{i}:")
        print(f"   Direction: {trade['direction']}")
        print(f"   Entry: ${trade['entry_price']:.2f}")
        print(f"   P&L: {trade['pnl_pct']*100:.2f}%")
        print(f"   Hold Time: {trade['hold_minutes']:.1f} min")
        print(f"   Exit Reason: {trade['exit_reason']}")
        print(f"   Pattern: {trade['pattern_5min']['ribbon_state']}")
        print(f"   Green EMAs: {trade['pattern_5min']['green_count']} (Light: {trade['pattern_5min']['light_green_count']})")
        print(f"   Red EMAs: {trade['pattern_5min']['red_count']} (Light: {trade['pattern_5min']['light_red_count']})")

    # Save to JSON for rule optimizer
    with open('trading_data/optimal_trades_last_30min.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print("\n Results saved to trading_data/optimal_trades_last_30min.json")


if __name__ == '__main__':
    main()
