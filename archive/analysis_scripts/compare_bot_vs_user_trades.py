#!/usr/bin/env python3
"""
Compare Bot's Trades vs User's 22 Trades
Find which user trades the bot caught vs missed
"""

import pandas as pd
import json
from pathlib import Path
from datetime import timedelta

data_dir = Path(__file__).parent / 'trading_data'

# Load user's 22 trades
with open(data_dir / 'user_trades_profit.json', 'r') as f:
    user_data = json.load(f)
user_trades = pd.DataFrame(user_data['trades'])
user_trades['entry_time'] = pd.to_datetime(user_trades['entry_time'])

# Load bot's trades from Iteration 11
with open(data_dir / 'iteration_11_results.json', 'r') as f:
    bot_data = json.load(f)
bot_trades = pd.DataFrame(bot_data['trades'])
bot_trades['entry_time'] = pd.to_datetime(bot_trades['entry_time'])

print("\n" + "="*80)
print("🔍 BOT VS USER TRADE COMPARISON")
print("="*80)

print(f"\n📊 Trade Counts:")
print(f"   User: {len(user_trades)} trades")
print(f"   Bot (Iter 11): {len(bot_trades)} trades")

# Match user trades to bot trades (within 2 hours tolerance)
tolerance = timedelta(hours=2)
matches = []
matched_bot_indices = set()

for idx, user_trade in user_trades.iterrows():
    user_entry = user_trade['entry_time']
    user_dir = user_trade['direction']

    # Find bot trades within time window and same direction
    candidates = bot_trades[
        (bot_trades['entry_time'] >= user_entry - tolerance) &
        (bot_trades['entry_time'] <= user_entry + tolerance) &
        (bot_trades['direction'] == user_dir)
    ]

    if len(candidates) > 0:
        # Take closest match
        candidates['time_diff'] = abs((candidates['entry_time'] - user_entry).dt.total_seconds())
        best_match = candidates.iloc[candidates['time_diff'].argmin()]

        matches.append({
            'user_trade_num': user_trade['trade_num'],
            'user_entry': user_entry,
            'user_direction': user_dir,
            'user_profit': user_trade['profit_pct'],
            'bot_entry': best_match['entry_time'],
            'bot_profit': best_match['profit_pct'],
            'bot_trade_idx': best_match.name,
            'time_diff_mins': best_match['time_diff'] / 60
        })
        matched_bot_indices.add(best_match.name)

matches_df = pd.DataFrame(matches)

print(f"\n✅ MATCHED TRADES:")
print(f"   Bot caught {len(matches)}/{len(user_trades)} user trades ({len(matches)/len(user_trades)*100:.1f}%)")

print(f"\n📋 Matched Trade Details:")
for _, match in matches_df.iterrows():
    print(f"\n   User Trade #{int(match['user_trade_num'])}: {match['user_direction'].upper()}")
    print(f"      User: {match['user_entry']} → {match['user_profit']:+.2f}%")
    print(f"      Bot:  {match['bot_entry']} → {match['bot_profit']:+.2f}%")
    print(f"      Time diff: {match['time_diff_mins']:.0f} mins")

# Find MISSED user trades
missed_trades = user_trades[~user_trades['trade_num'].isin(matches_df['user_trade_num'])]

print(f"\n❌ MISSED USER TRADES:")
print(f"   Bot missed {len(missed_trades)}/{len(user_trades)} user trades ({len(missed_trades)/len(user_trades)*100:.1f}%)")

if len(missed_trades) > 0:
    print(f"\n📋 Missed Trade Details:")
    for _, trade in missed_trades.iterrows():
        print(f"\n   User Trade #{int(trade['trade_num'])}: {trade['direction'].upper()}")
        print(f"      Entry: {trade['entry_time']}")
        print(f"      Profit: {trade['profit_pct']:+.2f}%")
        print(f"      Peak: {trade['peak_profit']:.2f}%")

# Find FALSE SIGNALS (bot trades that don't match user)
false_signals = bot_trades[~bot_trades.index.isin(matched_bot_indices)]

print(f"\n⚠️  FALSE SIGNALS (Bot's extra trades):")
print(f"   Bot took {len(false_signals)} trades that user didn't ({len(false_signals)/len(bot_trades)*100:.1f}%)")

# Analyze false signals
false_winners = false_signals[false_signals['profit_pct'] > 0]
false_losers = false_signals[false_signals['profit_pct'] <= 0]

print(f"\n   False signal breakdown:")
print(f"      Winners: {len(false_winners)} ({len(false_winners)/len(false_signals)*100:.1f}%)")
print(f"      Losers: {len(false_losers)} ({len(false_losers)/len(false_signals)*100:.1f}%)")

if len(false_losers) > 0:
    avg_false_loss = false_losers['profit_pct'].mean()
    total_false_loss = false_losers['profit_pct'].sum()
    print(f"      Avg loss on false signals: {avg_false_loss:.2f}%")
    print(f"      Total loss from false signals: {total_false_loss:.2f}%")

# Calculate impact
user_pnl = user_trades['profit_pct'].sum()
matched_bot_pnl = matches_df['bot_profit'].sum() if len(matches_df) > 0 else 0
false_signal_pnl = false_signals['profit_pct'].sum()

print(f"\n💰 PNL BREAKDOWN:")
print(f"   User total PnL: {user_pnl:.2f}%")
print(f"   Bot PnL on matched trades: {matched_bot_pnl:.2f}%")
print(f"   Bot PnL on false signals: {false_signal_pnl:.2f}%")
print(f"   Bot total PnL: {matched_bot_pnl + false_signal_pnl:.2f}%")

print(f"\n🎯 KEY INSIGHT:")
if false_signal_pnl < 0:
    print(f"   ❌ False signals DESTROYED profits ({false_signal_pnl:.2f}%)")
    print(f"   If we ONLY took user's trades: {matched_bot_pnl:.2f}% return")
    print(f"   With false signals: {matched_bot_pnl + false_signal_pnl:.2f}% return")
    print(f"\n💡 SOLUTION: Need filters to REJECT false signals!")
else:
    print(f"   ✅ False signals were profitable (+{false_signal_pnl:.2f}%)")
    print(f"   But still underperforming user's selectivity")

# Save analysis
results = {
    'matched_trades': len(matches),
    'missed_user_trades': len(missed_trades),
    'false_signals': len(false_signals),
    'false_signal_win_rate': len(false_winners) / len(false_signals) * 100 if len(false_signals) > 0 else 0,
    'matched_pnl': float(matched_bot_pnl),
    'false_signal_pnl': float(false_signal_pnl),
    'matches': matches,
    'missed_trades': missed_trades.to_dict('records'),
}

with open(data_dir / 'trade_comparison.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)

print(f"\n💾 Analysis saved to: {data_dir / 'trade_comparison.json'}")
print("="*80 + "\n")
