"""
Simple Backtest Runner
Backtests current trading rules against historical data
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path


def run_backtest(hours_back: int = 24) -> dict:
    """
    Run backtest using current trading rules

    Args:
        hours_back: Hours of historical data to backtest

    Returns:
        Dict with backtest results
    """

    try:
        # Load rules to determine which trader to use
        with open('trading_rules.json', 'r') as f:
            rules = json.load(f)
            version = rules.get('version', '1.0')

        # Import appropriate trader
        if 'phase1' in str(version).lower():
            from rule_based_trader_phase1 import RuleBasedTraderPhase1
            trader = RuleBasedTraderPhase1()
        else:
            from rule_based_trader import RuleBasedTrader
            trader = RuleBasedTrader()

        # Load EMA data
        ema_file = 'trading_data/ema_data_5min.csv'
        if not Path(ema_file).exists():
            return {
                'status': 'no_data',
                'trades': [],
                'summary': {},
                'patterns': {}
            }

        df = pd.read_csv(ema_file, on_bad_lines='skip')
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])

        # Filter to time range
        cutoff = datetime.now() - timedelta(hours=hours_back)
        df = df[df['timestamp'] >= cutoff]
        df = df.sort_values('timestamp').reset_index(drop=True)

        if len(df) < 10:
            return {
                'status': 'insufficient_data',
                'trades': [],
                'summary': {},
                'patterns': {}
            }

        # Run backtest
        trades = []
        in_position = False
        entry_idx = None
        entry_direction = None
        entry_price = None
        entry_compression = 0
        entry_light_emas = 0

        # Debug counters
        signal_count = 0
        blocked_by_position_count = 0

        # Track ribbon transitions
        last_ribbon_state = None
        ribbon_transition_time = None

        for idx in range(len(df) - 1):
            current = df.iloc[idx]

            # Track ribbon state transitions
            current_ribbon_state = current.get('ribbon_state', 'unknown')
            if last_ribbon_state != current_ribbon_state:
                ribbon_transition_time = current['timestamp']
                last_ribbon_state = current_ribbon_state

            # Extract and structure indicators properly for Phase1 trader
            indicators_5min = {}

            # Add basic fields
            indicators_5min['ribbon_state'] = current.get('ribbon_state', 'unknown')
            indicators_5min['price'] = current.get('price', 0)
            indicators_5min['close'] = current.get('close', current.get('price', 0))

            # Structure EMA data as nested dicts
            for ema in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]:
                val_col = f'MMA{ema}_value'
                color_col = f'MMA{ema}_color'
                intensity_col = f'MMA{ema}_intensity'

                if val_col in current.index and color_col in current.index and intensity_col in current.index:
                    indicators_5min[f'MMA{ema}'] = {
                        'value': current[val_col],
                        'color': current[color_col],
                        'intensity': current[intensity_col]
                    }

            # Dummy 15min indicators (using 5min for simplicity in backtest)
            indicators_15min = indicators_5min.copy()

            current_price = current.get('close', current.get('price', 0))

            # Build current position if in one
            current_position = None
            if in_position:
                entry_time = df.iloc[entry_idx]['timestamp']
                current_position = {
                    'direction': entry_direction,
                    'entry_price': entry_price,
                    'entry_time': entry_time,
                    'entry_tier': 1  # Default tier
                }

            # Get trading decision (handle both method names)
            if hasattr(trader, 'get_trading_decision'):
                # Pass df_recent for momentum detection (user pattern trader needs this)
                df_recent = df.iloc[:idx+1]  # All data up to current point
                decision = trader.get_trading_decision(
                    indicators_5min=indicators_5min,
                    indicators_15min=indicators_15min,
                    current_price=current_price,
                    current_position=current_position,
                    df_recent=df_recent
                )
            else:
                # Phase1 trader uses get_trade_decision and needs ribbon_transition_time
                decision = trader.get_trade_decision(
                    indicators_5min=indicators_5min,
                    indicators_15min=indicators_15min,
                    current_price=current_price,
                    ribbon_transition_time=ribbon_transition_time,
                    current_position=current_position
                )

            # Handle entry
            if decision.get('entry_recommended', False):
                signal_count += 1
                if in_position:
                    blocked_by_position_count += 1
                else:
                    in_position = True
                    entry_idx = idx
                    entry_direction = decision.get('direction')
                    entry_price = current_price

                # Calculate compression at entry
                entry_compression = current.get('ribbon_compression', None)
                if entry_compression is None or pd.isna(entry_compression):
                    # Calculate compression from EMA values
                    ema_values = []
                    for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
                        val_col = f'MMA{ema}_value'
                        if val_col in current.index and pd.notna(current[val_col]):
                            ema_values.append(float(current[val_col]))

                    if len(ema_values) >= 3:
                        ema_min = min(ema_values)
                        ema_max = max(ema_values)
                        entry_compression = (ema_max - ema_min) / ema_min if ema_min > 0 else 0
                    else:
                        entry_compression = 0

                # Count light EMAs at entry
                entry_light_emas = 0
                for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60]:
                    intensity_col = f'MMA{ema}_intensity'
                    color_col = f'MMA{ema}_color'
                    if intensity_col in current.index and color_col in current.index:
                        if entry_direction == 'LONG':
                            if current[color_col] == 'green' and current[intensity_col] == 'light':
                                entry_light_emas += 1
                        else:
                            if current[color_col] == 'red' and current[intensity_col] == 'light':
                                entry_light_emas += 1

            # Handle exit
            elif in_position and decision.get('exit_recommended', False):
                exit_time = current['timestamp']
                entry_time = df.iloc[entry_idx]['timestamp']
                hold_time = (exit_time - entry_time).total_seconds() / 60

                if entry_direction == 'LONG':
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - current_price) / entry_price * 100

                trades.append({
                    'entry_time': entry_time.isoformat(),
                    'exit_time': exit_time.isoformat(),
                    'direction': entry_direction,
                    'entry_price': float(entry_price),
                    'exit_price': float(current_price),
                    'hold_time_minutes': float(hold_time),
                    'pnl_pct': float(pnl_pct),
                    'winner': bool(pnl_pct > 0),
                    'compression': float(entry_compression),
                    'light_emas': int(entry_light_emas)
                })

                in_position = False
                entry_idx = None
                entry_direction = None
                entry_price = None

        # Calculate summary (handling NaN values properly)
        if trades:
            import math

            # Filter out NaN values when calculating
            valid_trades = [t for t in trades if not math.isnan(t.get('pnl_pct', 0))]
            winners = [t for t in valid_trades if t['winner']]
            losers = [t for t in valid_trades if not t['winner']]

            # Calculate total PnL from valid trades only
            total_pnl = sum(t['pnl_pct'] for t in valid_trades) if valid_trades else 0

            summary = {
                'total_trades': len(trades),
                'valid_trades': len(valid_trades),
                'winners': len(winners),
                'losers': len(losers),
                'win_rate': len(winners) / len(valid_trades) if valid_trades else 0,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / len(valid_trades) if valid_trades else 0,
                'avg_winner': sum(t['pnl_pct'] for t in winners) / len(winners) if winners else 0,
                'avg_loser': sum(t['pnl_pct'] for t in losers) / len(losers) if losers else 0,
                'avg_hold_time': sum(t['hold_time_minutes'] for t in trades) / len(trades)
            }

            patterns = {
                'avg_compression': sum(t['compression'] for t in trades) / len(trades),
                'avg_light_emas': sum(t['light_emas'] for t in trades) / len(trades)
            }
        else:
            summary = {
                'total_trades': 0,
                'winners': 0,
                'losers': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_winner': 0,
                'avg_loser': 0,
                'avg_hold_time': 0
            }
            patterns = {
                'avg_compression': 0,
                'avg_light_emas': 0
            }

        return {
            'status': 'success',
            'trades': trades,
            'summary': summary,
            'patterns': patterns,
            'total_trades': len(trades),
            'total_pnl_pct': summary['total_pnl'],
            'avg_pnl_pct': summary.get('avg_pnl', 0),
            'avg_hold_minutes': summary.get('avg_hold_time', 0),
            'win_rate': summary.get('win_rate', 0),
            'avg_compression': patterns.get('avg_compression', 0),
            'avg_light_emas': patterns.get('avg_light_emas', 0),
            'debug': {
                'total_signals': signal_count,
                'blocked_by_position': blocked_by_position_count
            }
        }

    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'error': str(e),
            'trades': [],
            'summary': {},
            'patterns': {}
        }


if __name__ == '__main__':
    results = run_backtest(hours_back=24)
    print(f"\n📊 Backtest Results:")
    print(f"   Trades: {results['total_trades']}")
    print(f"   PnL: {results['total_pnl_pct']:+.2f}%")
    print(f"   Avg Compression: {results['patterns'].get('avg_compression', 0):.4f}")
    print(f"   Avg Light EMAs: {results['patterns'].get('avg_light_emas', 0):.1f}")
