"""
Quick User Trade Addition Helper
Add trades directly via command line arguments or Claude can call this
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path


def add_user_trade(direction: str, entry_time: str, exit_time: str,
                   entry_price: float, exit_price: float):
    """
    Add a user-specified optimal trade

    Args:
        direction: 'LONG' or 'SHORT'
        entry_time: ISO format datetime or parseable string
        exit_time: ISO format datetime or parseable string
        entry_price: Entry price in dollars
        exit_price: Exit price in dollars
    """
    user_trades_path = 'trading_data/optimal_trades_user.json'

    # Parse times
    try:
        entry_dt = pd.to_datetime(entry_time)
        exit_dt = pd.to_datetime(exit_time)
    except Exception as e:
        print(f"❌ Error parsing times: {e}")
        return False

    # Calculate metrics
    hold_time = (exit_dt - entry_dt).total_seconds() / 60

    if direction.upper() == 'LONG':
        pnl_pct = (exit_price - entry_price) / entry_price * 100
    else:
        pnl_pct = (entry_price - exit_price) / entry_price * 100

    # Create trade
    trade = {
        'entry_time': entry_dt.isoformat(),
        'exit_time': exit_dt.isoformat(),
        'direction': direction.upper(),
        'entry_price': float(entry_price),
        'exit_price': float(exit_price),
        'hold_time_minutes': float(hold_time),
        'pnl_pct': float(pnl_pct),
        'manual_input': True,
        'added_at': datetime.now().isoformat()
    }

    # Load existing trades
    try:
        if Path(user_trades_path).exists():
            with open(user_trades_path, 'r') as f:
                data = json.load(f)
                trades = data.get('trades', [])
        else:
            trades = []
    except Exception as e:
        print(f"⚠️  Error loading existing trades: {e}")
        trades = []

    # Add new trade
    trades.append(trade)

    # Calculate summary
    total_pnl = sum(t['pnl_pct'] for t in trades)
    avg_pnl = total_pnl / len(trades) if trades else 0
    avg_hold = sum(t['hold_time_minutes'] for t in trades) / len(trades) if trades else 0
    winners = [t for t in trades if t['pnl_pct'] > 0]
    win_rate = len(winners) / len(trades) if trades else 0

    # Save
    data = {
        'status': 'success',
        'trades': trades,
        'total_trades': len(trades),
        'total_pnl_pct': total_pnl,
        'avg_pnl_pct': avg_pnl,
        'avg_hold_minutes': avg_hold,
        'win_rate': win_rate,
        'patterns': {
            'avg_compression': 0,  # User doesn't specify compression
            'avg_light_emas': 0    # User doesn't specify light EMAs
        },
        'source': 'user_input',
        'last_updated': datetime.now().isoformat()
    }

    Path(user_trades_path).parent.mkdir(parents=True, exist_ok=True)

    with open(user_trades_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Print summary
    print(f"\n✅ Added {direction} trade!")
    print(f"   Entry:  {entry_dt.strftime('%Y-%m-%d %H:%M')} @ ${entry_price:.2f}")
    print(f"   Exit:   {exit_dt.strftime('%Y-%m-%d %H:%M')} @ ${exit_price:.2f}")
    print(f"   Hold:   {hold_time:.1f} minutes")
    print(f"   PnL:    {pnl_pct:+.2f}%")
    print(f"\n📊 Total user trades: {len(trades)}")
    print(f"   Total PnL: {total_pnl:+.2f}%")
    print(f"   Avg PnL:   {avg_pnl:+.2f}%")
    print(f"   Win Rate:  {win_rate*100:.1f}%")

    return True


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 6:
        print("Usage: python3 add_user_trade.py DIRECTION ENTRY_TIME EXIT_TIME ENTRY_PRICE EXIT_PRICE")
        print("\nExample:")
        print("  python3 add_user_trade.py LONG '2025-10-20 14:30' '2025-10-20 15:15' 4050.25 4055.50")
        sys.exit(1)

    direction = sys.argv[1]
    entry_time = sys.argv[2]
    exit_time = sys.argv[3]
    entry_price = float(sys.argv[4])
    exit_price = float(sys.argv[5])

    add_user_trade(direction, entry_time, exit_time, entry_price, exit_price)
