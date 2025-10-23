"""
Manual Optimal Trades Input
Allows you to manually specify what trades you think the bot SHOULD have taken
"""

import json
from datetime import datetime
import pandas as pd


def input_manual_optimal_trades():
    """Interactive input for manual optimal trades"""

    print("="*70)
    print("MANUAL OPTIMAL TRADES INPUT")
    print("="*70)
    print("Enter the trades you believe the bot should have executed.")
    print("This will create the 'optimal' benchmark for the optimizer to target.")
    print()

    trades = []

    while True:
        print(f"\n--- Trade #{len(trades) + 1} ---")

        # Entry details
        entry_time_str = input("Entry time (YYYY-MM-DD HH:MM:SS) [or 'done' to finish]: ").strip()
        if entry_time_str.lower() == 'done':
            break

        try:
            entry_time = datetime.fromisoformat(entry_time_str)
        except:
            print("❌ Invalid datetime format. Use: 2025-10-21 14:30:00")
            continue

        direction = input("Direction (LONG/SHORT): ").strip().upper()
        if direction not in ['LONG', 'SHORT']:
            print("❌ Direction must be LONG or SHORT")
            continue

        entry_price = float(input("Entry price: "))

        # Exit details
        exit_time_str = input("Exit time (YYYY-MM-DD HH:MM:SS): ").strip()
        try:
            exit_time = datetime.fromisoformat(exit_time_str)
        except:
            print("❌ Invalid datetime format")
            continue

        exit_price = float(input("Exit price: "))

        # Calculate PnL
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        # Optional: EMA pattern details
        print("\nOptional EMA pattern details (press Enter to skip):")
        light_emas = input("Number of light EMAs at entry: ").strip()
        light_emas = int(light_emas) if light_emas else 0

        compression = input("Compression at entry (e.g., 0.16 for 0.16%): ").strip()
        compression = float(compression) / 100 if compression else 0

        # Calculate hold time
        hold_time_minutes = (exit_time - entry_time).total_seconds() / 60

        trade = {
            'entry_time': entry_time.isoformat(),
            'exit_time': exit_time.isoformat(),
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'hold_time_minutes': hold_time_minutes,
            'winner': pnl_pct > 0,
            'compression': compression,
            'light_emas': light_emas,
            'source': 'manual_input'
        }

        trades.append(trade)
        print(f"✅ Trade added: {direction} @ ${entry_price:.2f} → ${exit_price:.2f} = {pnl_pct:+.2f}% ({hold_time_minutes:.1f}min)")

    if not trades:
        print("\n❌ No trades entered. Exiting.")
        return

    # Calculate summary statistics
    total_trades = len(trades)
    winners = [t for t in trades if t['winner']]
    losers = [t for t in trades if not t['winner']]

    total_pnl_pct = sum(t['pnl_pct'] for t in trades)
    avg_pnl_pct = total_pnl_pct / total_trades
    win_rate = len(winners) / total_trades

    avg_compression = sum(t['compression'] for t in trades) / total_trades if trades else 0
    avg_light_emas = sum(t['light_emas'] for t in trades) / total_trades if trades else 0
    avg_hold_time = sum(t['hold_time_minutes'] for t in trades) / total_trades if trades else 0

    # Create summary
    summary = {
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
        }
    }

    # Create full data structure
    optimal_data = {
        'analysis_timestamp': datetime.now().isoformat(),
        'source': 'manual_user_input',
        'description': 'Manually specified optimal trades based on user judgment',
        **summary,
        'trades': trades
    }

    # Save to file
    output_path = 'trading_data/optimal_trades.json'
    with open(output_path, 'w') as f:
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
    print(f"\n✅ Saved to {output_path}")
    print("\nYou can now run the optimizer to tune rules toward these trades:")
    print("  python3 run_multiple_optimizations.py 5 24")


if __name__ == '__main__':
    input_manual_optimal_trades()
