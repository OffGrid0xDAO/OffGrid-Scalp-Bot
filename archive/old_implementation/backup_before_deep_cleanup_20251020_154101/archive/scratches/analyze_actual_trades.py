#!/usr/bin/env python3
"""
Analyze actual trades from claude_decisions.csv
Extract all ENTRY_RECOMMENDED=YES and EXIT_RECOMMENDED=YES to calculate P&L
"""

import csv
import json
from datetime import datetime
from typing import List, Dict

def analyze_actual_trades(csv_path: str):
    """Analyze actual trades from Claude decisions"""

    trades = []
    current_position = None

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            timestamp = row['timestamp']
            action_type = row['action_type']
            direction = row['direction']
            entry_recommended = row['entry_recommended']
            entry_price = float(row['entry_price'])
            executed = row['executed']

            # Check for entry
            if entry_recommended == 'YES' and executed == 'True':
                if current_position is None:
                    current_position = {
                        'entry_time': timestamp,
                        'entry_price': entry_price,
                        'direction': direction
                    }
                    print(f"📊 {direction} ENTRY @ ${entry_price:.2f} | {timestamp}")

            # Check for exit
            elif action_type == 'exit' and executed == 'True':
                if current_position:
                    exit_price = entry_price  # In exit rows, entry_price is current price

                    # Calculate P&L
                    if current_position['direction'] == 'LONG':
                        pnl = exit_price - current_position['entry_price']
                    else:  # SHORT
                        pnl = current_position['entry_price'] - exit_price

                    pnl_pct = (pnl / current_position['entry_price']) * 100

                    trade = {
                        'entry_time': current_position['entry_time'],
                        'entry_price': current_position['entry_price'],
                        'exit_time': timestamp,
                        'exit_price': exit_price,
                        'direction': current_position['direction'],
                        'pnl_dollars': pnl,
                        'pnl_percent': pnl_pct
                    }

                    trades.append(trade)
                    emoji = "✅" if pnl > 0 else "❌"
                    print(f"{emoji} {current_position['direction']} EXIT @ ${exit_price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:.3f}%)")

                    current_position = None

    # Calculate stats
    if not trades:
        print("\n❌ No completed trades found!")
        return

    profitable = [t for t in trades if t['pnl_dollars'] > 0]
    losing = [t for t in trades if t['pnl_dollars'] <= 0]

    total_pnl = sum(t['pnl_dollars'] for t in trades)
    win_rate = (len(profitable) / len(trades)) * 100

    print("\n" + "="*80)
    print("ACTUAL TRADING PERFORMANCE")
    print("="*80)
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Total Trades: {len(trades)}")
    print(f"   Profitable: {len(profitable)} ✅")
    print(f"   Losing: {len(losing)} ❌")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"   Total P&L: ${total_pnl:.2f}")
    print(f"   Avg P&L per Trade: ${total_pnl/len(trades):.2f}")

    if profitable:
        avg_win = sum(t['pnl_dollars'] for t in profitable) / len(profitable)
        print(f"   Avg Win: ${avg_win:.2f}")

    if losing:
        avg_loss = sum(t['pnl_dollars'] for t in losing) / len(losing)
        print(f"   Avg Loss: ${avg_loss:.2f}")

    print(f"\n📈 TRADE BREAKDOWN:")
    long_trades = [t for t in trades if t['direction'] == 'LONG']
    short_trades = [t for t in trades if t['direction'] == 'SHORT']
    print(f"   Long Trades: {len(long_trades)}")
    print(f"   Short Trades: {len(short_trades)}")

    if long_trades:
        long_pnl = sum(t['pnl_dollars'] for t in long_trades)
        print(f"   Long P&L: ${long_pnl:.2f}")

    if short_trades:
        short_pnl = sum(t['pnl_dollars'] for t in short_trades)
        print(f"   Short P&L: ${short_pnl:.2f}")

    # Show all trades
    print(f"\n📋 ALL TRADES:")
    for i, trade in enumerate(trades, 1):
        emoji = "✅" if trade['pnl_dollars'] > 0 else "❌"
        print(f"\n   Trade {i}: {emoji} {trade['direction']}")
        print(f"   Entry: {trade['entry_time']} @ ${trade['entry_price']:.2f}")
        print(f"   Exit: {trade['exit_time']} @ ${trade['exit_price']:.2f}")
        print(f"   P&L: ${trade['pnl_dollars']:.2f} ({trade['pnl_percent']:.3f}%)")

    # Save to JSON
    output = {
        'timestamp': datetime.now().isoformat(),
        'total_trades': len(trades),
        'profitable_trades': len(profitable),
        'losing_trades': len(losing),
        'win_rate': win_rate,
        'total_pnl_dollars': total_pnl,
        'avg_pnl_per_trade': total_pnl / len(trades),
        'trades': trades
    }

    with open('actual_trades_analysis.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Analysis saved to actual_trades_analysis.json")
    print("="*80)


if __name__ == "__main__":
    analyze_actual_trades('trading_data/claude_decisions.csv')
