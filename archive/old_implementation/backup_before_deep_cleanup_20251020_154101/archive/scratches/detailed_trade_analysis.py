#!/usr/bin/env python3
"""
Detailed analysis of the 5 blocked trades - what happened to price after?
"""

import csv
from datetime import datetime, timedelta

def parse_timestamp(ts_str):
    """Parse timestamp from CSV"""
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except:
        return None

def get_price_movement(entry_time, entry_price, direction):
    """Get price movement for 5, 10, and 15 minutes after entry"""
    try:
        with open('trading_data/ema_data_5min.csv', 'r') as f:
            reader = csv.reader(f)

            prices = []
            entry_ts = parse_timestamp(entry_time)
            if not entry_ts:
                return None

            for row in reader:
                if not row or len(row) < 2:
                    continue

                ts = parse_timestamp(row[0])
                if not ts:
                    continue

                price = float(row[1])
                time_diff = (ts - entry_ts).total_seconds()

                # Get prices for 0-15 minutes after
                if 0 <= time_diff <= 900:
                    prices.append((time_diff / 60, price))  # minutes, price

            if not prices:
                return None

            # Find peak profit and max drawdown
            peak_profit = 0
            max_drawdown = 0
            price_5min = None
            price_10min = None
            price_15min = None

            for mins, price in prices:
                if direction == 'LONG':
                    pnl = price - entry_price
                else:  # SHORT
                    pnl = entry_price - price

                peak_profit = max(peak_profit, pnl)
                max_drawdown = min(max_drawdown, pnl)

                # Get prices at 5, 10, 15 min marks
                if 4.5 <= mins <= 5.5 and price_5min is None:
                    price_5min = price
                if 9.5 <= mins <= 10.5 and price_10min is None:
                    price_10min = price
                if 14.5 <= mins <= 15.5 and price_15min is None:
                    price_15min = price

            return {
                'peak_profit': peak_profit,
                'max_drawdown': max_drawdown,
                'price_5min': price_5min,
                'price_10min': price_10min,
                'price_15min': price_15min,
                'all_prices': prices[:30]  # First 30 entries
            }
    except Exception as e:
        print(f"Error: {e}")
        return None

# The 5 blocked trades
trades = [
    {
        'time': '2025-10-19T09:55:37.297636',
        'direction': 'SHORT',
        'confidence': 0.850,
        'entry_price': 3865.95,
        'state_5min': 'mixed',
        'state_15min': 'mixed_red',
        'light_emas': 9,
        'reasoning': 'PATH D/E early reversal'
    },
    {
        'time': '2025-10-19T10:20:31.131310',
        'direction': 'LONG',
        'confidence': 0.880,
        'entry_price': 3861.65,
        'state_5min': 'mixed_green',
        'state_15min': 'mixed_red',
        'light_emas': 14,
        'reasoning': 'PATH D early reversal'
    },
    {
        'time': '2025-10-19T10:40:25.705364',
        'direction': 'LONG',
        'confidence': 0.880,
        'entry_price': 3863.95,
        'state_5min': 'mixed_green',
        'state_15min': 'mixed_red',
        'light_emas': 21,
        'reasoning': 'PATH D early reversal - 21 LIGHT green EMAs!'
    },
    {
        'time': '2025-10-19T11:06:09.705472',
        'direction': 'LONG',
        'confidence': 0.880,
        'entry_price': 3901.70,
        'state_5min': 'mixed_green',
        'state_15min': 'mixed_green',
        'light_emas': 11,
        'reasoning': 'PATH D early reversal'
    },
    {
        'time': '2025-10-19T12:40:35.491580',
        'direction': 'LONG',
        'confidence': 0.880,
        'entry_price': 3925.65,
        'state_5min': 'mixed_red',
        'state_15min': 'mixed_green',
        'light_emas': 0,
        'reasoning': 'Breakout/reversal'
    },
]

print("=" * 80)
print("DETAILED TRADE OUTCOME ANALYSIS")
print("What happened to price after these 5 blocked trades?")
print("=" * 80)
print()

total_peak_profit = 0
total_peak_pct = 0
winners = 0
losers = 0

for i, trade in enumerate(trades, 1):
    print(f"\n{'=' * 80}")
    print(f"TRADE #{i}: {trade['time']}")
    print(f"{'=' * 80}")
    print(f"Direction: {trade['direction']}")
    print(f"Entry Price: ${trade['entry_price']:.2f}")
    print(f"Confidence: {trade['confidence']:.1%}")
    print(f"5min State: {trade['state_5min']}")
    print(f"15min State: {trade['state_15min']}")
    print(f"LIGHT EMAs: {trade['light_emas']}")
    print(f"Reason: {trade['reasoning']}")
    print()

    movement = get_price_movement(trade['time'], trade['entry_price'], trade['direction'])

    if movement:
        peak_profit = movement['peak_profit']
        max_drawdown = movement['max_drawdown']
        peak_pct = (peak_profit / trade['entry_price']) * 100
        dd_pct = (max_drawdown / trade['entry_price']) * 100

        print(f"📊 PRICE MOVEMENT:")
        print(f"-" * 80)

        if movement['price_5min']:
            pnl_5min = movement['price_5min'] - trade['entry_price'] if trade['direction'] == 'LONG' else trade['entry_price'] - movement['price_5min']
            pct_5min = (pnl_5min / trade['entry_price']) * 100
            print(f"   5 minutes:  ${movement['price_5min']:.2f} ({pnl_5min:+.2f} = {pct_5min:+.2f}%)")

        if movement['price_10min']:
            pnl_10min = movement['price_10min'] - trade['entry_price'] if trade['direction'] == 'LONG' else trade['entry_price'] - movement['price_10min']
            pct_10min = (pnl_10min / trade['entry_price']) * 100
            print(f"   10 minutes: ${movement['price_10min']:.2f} ({pnl_10min:+.2f} = {pct_10min:+.2f}%)")

        if movement['price_15min']:
            pnl_15min = movement['price_15min'] - trade['entry_price'] if trade['direction'] == 'LONG' else trade['entry_price'] - movement['price_15min']
            pct_15min = (pnl_15min / trade['entry_price']) * 100
            print(f"   15 minutes: ${movement['price_15min']:.2f} ({pnl_15min:+.2f} = {pct_15min:+.2f}%)")

        print()
        print(f"   Peak Profit:    ${peak_profit:+.2f} ({peak_pct:+.2f}%)")
        print(f"   Max Drawdown:   ${max_drawdown:+.2f} ({dd_pct:+.2f}%)")
        print()

        # With leverage
        print(f"   💰 With 10x leverage:")
        print(f"      Peak: {peak_pct * 10:+.1f}%")
        print(f"      Drawdown: {dd_pct * 10:+.1f}%")

        # Verdict
        if peak_profit > 0 and peak_profit > abs(max_drawdown):
            print(f"\n   ✅ GOOD TRADE: Peak profit ${peak_profit:.2f} > max drawdown ${abs(max_drawdown):.2f}")
            winners += 1
        elif peak_profit > 5:  # At least $5 profit
            print(f"\n   ✅ PROFITABLE: Peak profit ${peak_profit:.2f}")
            winners += 1
        elif max_drawdown < -10:  # More than $10 loss
            print(f"\n   ❌ BAD TRADE: Max drawdown ${max_drawdown:.2f}")
            losers += 1
        else:
            print(f"\n   ⚠️  MARGINAL: Small move, could go either way")

        total_peak_profit += peak_profit
        total_peak_pct += peak_pct

    else:
        print("   ⚠️  No price data found for this period")

print()
print()
print("=" * 80)
print("OVERALL SUMMARY")
print("=" * 80)
print()
print(f"Total trades analyzed: {len(trades)}")
print(f"Winners: {winners} ✅")
print(f"Losers: {losers} ❌")
print(f"Marginal: {len(trades) - winners - losers} ⚠️")
print()
print(f"Win rate: {(winners / len(trades)) * 100:.0f}%")
print()
print(f"Total peak profit: ${total_peak_profit:.2f}")
print(f"Average peak profit per trade: ${total_peak_profit / len(trades):.2f}")
print(f"Average peak % per trade: {total_peak_pct / len(trades):.2f}%")
print()
print(f"💰 With 10x leverage:")
print(f"   Average gain per trade: {(total_peak_pct / len(trades)) * 10:.1f}%")
print(f"   Total if all trades taken: {total_peak_pct * 10:.1f}%")
print()
print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print()

if winners >= 4:
    print("✅ EXCELLENT! The new quality filter would have caught mostly winners.")
    print("   These are high-quality early entry signals that were being blocked.")
    print("   The fix will significantly improve your profitability!")
elif winners >= 3:
    print("✅ GOOD! The new quality filter would have caught more winners than losers.")
    print("   These early entry signals are worth taking.")
elif winners >= 2:
    print("⚠️  MIXED! Win rate around 40-60%, typical for early entries.")
    print("   Consider adding stop losses and position sizing.")
else:
    print("❌ POOR! These blocked trades were mostly losers.")
    print("   The old filter may have been protecting you.")

print()
print("💡 Remember:")
print("   - Peak profit assumes perfect exit timing")
print("   - Real trades need stop losses (usually at -0.5% to -1%)")
print("   - Position sizing matters (15-25% per trade)")
print("   - Early entries have better R:R but need quick exits")
print()
print("=" * 80)
