#!/usr/bin/env python3
"""
Machine Learning Analysis of USER's EXIT Strategy
Analyze the 22 trades to discover exit patterns and optimize exit_manager
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

print("\n" + "="*80)
print("🤖 ML ANALYSIS: USER EXIT STRATEGY")
print("="*80)

# Load user trades with actual exits
data_dir = Path(__file__).parent / 'trading_data'
with open(data_dir / 'user_trades_profit.json', 'r') as f:
    user_data = json.load(f)

trades = user_data['trades']
df = pd.DataFrame(trades)

print(f"\n📊 Loaded {len(df)} user trades")
print(f"   Total PnL: ${user_data['total_pnl']:.2f}")
print(f"   Win Rate: {user_data['win_rate']:.1f}%")
print(f"   Return: {user_data['return_pct']:.2f}%")

# Separate winners and losers
df['is_winner'] = df['profit_pct'] > 0
winners = df[df['is_winner']].copy()
losers = df[~df['is_winner']].copy()

print(f"\n✅ Winners: {len(winners)} trades")
print(f"❌ Losers: {len(losers)} trades")

# Analyze exit reasons
print("\n" + "="*80)
print("🔍 EXIT REASON BREAKDOWN")
print("="*80)

exit_reasons = df['exit_reason'].value_counts()
print(f"\n📋 Exit Reason Distribution:")
for reason, count in exit_reasons.items():
    pct = count / len(df) * 100
    reason_short = reason.split(':')[0] if ':' in reason else reason
    print(f"   {reason_short:<30} {count:>2} ({pct:>5.1f}%)")

# Categorize exits
def categorize_exit(reason):
    if 'Take profit' in reason:
        return 'Take Profit'
    elif 'Trailing stop' in reason:
        return 'Trailing Stop'
    elif 'Stop loss' in reason:
        return 'Stop Loss'
    elif 'Time' in reason:
        return 'Time Exit'
    else:
        return 'Other'

df['exit_category'] = df['exit_reason'].apply(categorize_exit)
winners['exit_category'] = winners['exit_reason'].apply(categorize_exit)
losers['exit_category'] = losers['exit_reason'].apply(categorize_exit)

print("\n📊 Exit Category Summary:")
for category in df['exit_category'].unique():
    count = len(df[df['exit_category'] == category])
    pct = count / len(df) * 100
    print(f"   {category:<20} {count:>2} ({pct:>5.1f}%)")

# Analyze WINNERS' exit behavior
print("\n" + "="*80)
print("✅ WINNER EXIT ANALYSIS")
print("="*80)

print(f"\n📈 Profit Statistics (Winners only):")
print(f"   Avg Profit: {winners['profit_pct'].mean():.2f}%")
print(f"   Median Profit: {winners['profit_pct'].median():.2f}%")
print(f"   Min Profit: {winners['profit_pct'].min():.2f}%")
print(f"   Max Profit: {winners['profit_pct'].max():.2f}%")

print(f"\n🎯 Peak Profit (Winners):")
print(f"   Avg Peak: {winners['peak_profit'].mean():.2f}%")
print(f"   Median Peak: {winners['peak_profit'].median():.2f}%")
print(f"   Min Peak: {winners['peak_profit'].min():.2f}%")
print(f"   Max Peak: {winners['peak_profit'].max():.2f}%")

# Calculate "profit capture ratio" = exit_profit / peak_profit
winners['capture_ratio'] = winners['profit_pct'] / winners['peak_profit']
print(f"\n💎 Profit Capture Ratio (exit_profit / peak_profit):")
print(f"   Avg: {winners['capture_ratio'].mean():.2%}")
print(f"   Median: {winners['capture_ratio'].median():.2%}")
print(f"   Range: {winners['capture_ratio'].min():.2%} - {winners['capture_ratio'].max():.2%}")

# Breakdown by exit type
print(f"\n📋 Winners by Exit Type:")
for category in winners['exit_category'].unique():
    subset = winners[winners['exit_category'] == category]
    count = len(subset)
    avg_profit = subset['profit_pct'].mean()
    avg_peak = subset['peak_profit'].mean()
    avg_capture = subset['capture_ratio'].mean()
    print(f"\n   {category}:")
    print(f"      Count: {count}")
    print(f"      Avg Exit Profit: {avg_profit:.2f}%")
    print(f"      Avg Peak Profit: {avg_peak:.2f}%")
    print(f"      Avg Capture: {avg_capture:.2%}")

# Analyze Take Profit levels
tp_winners = winners[winners['exit_category'] == 'Take Profit']
if len(tp_winners) > 0:
    print(f"\n🎯 TAKE PROFIT ANALYSIS ({len(tp_winners)} trades):")
    print(f"   TP levels used:")
    tp_levels = tp_winners['profit_pct'].values
    for i, tp in enumerate(sorted(tp_levels), 1):
        print(f"      {i}. {tp:.2f}%")

    print(f"\n   Recommended TP levels:")
    print(f"      TP1: {np.percentile(tp_levels, 25):.2f}% (25th percentile)")
    print(f"      TP2: {np.median(tp_levels):.2f}% (median)")
    print(f"      TP3: {np.percentile(tp_levels, 75):.2f}% (75th percentile)")
    print(f"      TP4: {np.max(tp_levels):.2f}% (max)")

# Analyze Trailing Stop behavior
trailing_winners = winners[winners['exit_category'] == 'Trailing Stop']
if len(trailing_winners) > 0:
    trailing_winners['giveback'] = trailing_winners['peak_profit'] - trailing_winners['profit_pct']
    print(f"\n🔄 TRAILING STOP ANALYSIS ({len(trailing_winners)} trades):")
    print(f"   Avg Giveback: {trailing_winners['giveback'].mean():.2f}%")
    print(f"   Median Giveback: {trailing_winners['giveback'].median():.2f}%")
    print(f"   Max Giveback: {trailing_winners['giveback'].max():.2f}%")
    print(f"   Avg Capture: {trailing_winners['capture_ratio'].mean():.2%}")

    print(f"\n   Individual Trailing Stops:")
    for _, trade in trailing_winners.iterrows():
        print(f"      Trade #{int(trade['trade_num'])}: Peaked {trade['peak_profit']:.2f}%, exited {trade['profit_pct']:.2f}% (gave back {trade['giveback']:.2f}%)")

# Analyze LOSERS' exit behavior
print("\n" + "="*80)
print("❌ LOSER EXIT ANALYSIS")
print("="*80)

print(f"\n📉 Loss Statistics:")
print(f"   Avg Loss: {losers['profit_pct'].mean():.2f}%")
print(f"   Median Loss: {losers['profit_pct'].median():.2f}%")
print(f"   Min Loss: {losers['profit_pct'].min():.2f}%")
print(f"   Max Loss: {losers['profit_pct'].max():.2f}%")

print(f"\n🎯 Peak Profit on Losers (before reversal):")
print(f"   Avg Peak: {losers['peak_profit'].mean():.2f}%")
print(f"   Median Peak: {losers['peak_profit'].median():.2f}%")
print(f"   Range: {losers['peak_profit'].min():.2f}% - {losers['peak_profit'].max():.2f}%")

# Calculate total giveback on losers
losers['total_giveback'] = losers['peak_profit'] - losers['profit_pct']
print(f"\n💸 Total Giveback on Losers:")
print(f"   Avg Giveback: {losers['total_giveback'].mean():.2f}%")
print(f"   Total Giveback: {losers['total_giveback'].sum():.2f}%")

print(f"\n📋 Loser Breakdown:")
for category in losers['exit_category'].unique():
    subset = losers[losers['exit_category'] == category]
    count = len(subset)
    avg_loss = subset['profit_pct'].mean()
    avg_peak = subset['peak_profit'].mean()
    avg_giveback = subset['total_giveback'].mean()
    print(f"\n   {category}:")
    print(f"      Count: {count}")
    print(f"      Avg Loss: {avg_loss:.2f}%")
    print(f"      Avg Peak: {avg_peak:.2f}%")
    print(f"      Avg Giveback: {avg_giveback:.2f}%")

# Individual loser analysis
print(f"\n   Individual Losers:")
for _, trade in losers.iterrows():
    print(f"      Trade #{int(trade['trade_num'])}: Peaked {trade['peak_profit']:.2f}%, exited {trade['profit_pct']:.2f}% ({trade['exit_category']})")

# OPTIMAL EXIT RULES DISCOVERY
print("\n" + "="*80)
print("🤖 ML-DISCOVERED EXIT RULES")
print("="*80)

# Rule 1: Take Profit Threshold
print(f"\n1️⃣  TAKE PROFIT RULE:")
if len(tp_winners) > 0:
    median_tp = np.median(tp_winners['profit_pct'].values)
    q1_tp = np.percentile(tp_winners['profit_pct'].values, 25)
    q3_tp = np.percentile(tp_winners['profit_pct'].values, 75)

    print(f"   User's TP range: {q1_tp:.2f}% - {q3_tp:.2f}%")
    print(f"   Median TP: {median_tp:.2f}%")
    print(f"   Recommended: Use {median_tp:.2f}% as primary TP")

# Rule 2: Trailing Stop Width
print(f"\n2️⃣  TRAILING STOP RULE:")
if len(trailing_winners) > 0:
    avg_trail_width = trailing_winners['giveback'].mean()
    median_trail_width = trailing_winners['giveback'].median()

    print(f"   User's trailing giveback: {avg_trail_width:.2f}% avg, {median_trail_width:.2f}% median")
    print(f"   Recommended: Trail width = {median_trail_width:.2f}%")
    print(f"   (Lock profit once it drops {median_trail_width:.2f}% from peak)")

# Rule 3: Stop Loss
print(f"\n3️⃣  STOP LOSS RULE:")
if len(losers) > 0:
    max_loss = abs(losers['profit_pct'].min())
    avg_loss = abs(losers['profit_pct'].mean())
    median_loss = abs(losers['profit_pct'].median())

    print(f"   User's losses: {avg_loss:.2f}% avg, {median_loss:.2f}% median, {max_loss:.2f}% max")
    print(f"   Recommended: Stop loss = {median_loss:.2f}%")
    print(f"   (Tighter than max loss of {max_loss:.2f}% to avoid worst cases)")

# Rule 4: Profit Lock (prevent winners becoming losers)
print(f"\n4️⃣  PROFIT LOCK RULE:")
# Find trades that peaked above certain threshold
profit_lock_candidates = df[df['peak_profit'] >= 1.0]
locked_trades = profit_lock_candidates[profit_lock_candidates['profit_pct'] > 0]
unlocked_trades = profit_lock_candidates[profit_lock_candidates['profit_pct'] <= 0]

print(f"   Trades that peaked >1%: {len(profit_lock_candidates)}")
print(f"   Still exited positive: {len(locked_trades)} ({len(locked_trades)/len(profit_lock_candidates)*100:.1f}%)")
print(f"   Reversed to negative: {len(unlocked_trades)} ({len(unlocked_trades)/len(profit_lock_candidates)*100:.1f}%)")

if len(unlocked_trades) > 0:
    avg_lost_profit = unlocked_trades['peak_profit'].mean()
    print(f"\n   Lost profit on reversals:")
    for _, trade in unlocked_trades.iterrows():
        print(f"      Trade #{int(trade['trade_num'])}: Peaked {trade['peak_profit']:.2f}%, ended {trade['profit_pct']:.2f}%")

    print(f"\n   Recommended: Lock profit if peaked >{avg_lost_profit/2:.2f}% and drops to 0%")
    print(f"   (Half of avg peak that reversed)")

# GENERATE OPTIMIZED EXIT PARAMETERS
print("\n" + "="*80)
print("⚙️  OPTIMIZED EXIT MANAGER PARAMETERS")
print("="*80)

optimized_params = {
    'take_profit_pct': round(np.median(tp_winners['profit_pct'].values), 2) if len(tp_winners) > 0 else 2.5,
    'stop_loss_pct': round(abs(losers['profit_pct'].median()), 2) if len(losers) > 0 else 1.0,
    'trailing_stop_width': round(trailing_winners['giveback'].median(), 2) if len(trailing_winners) > 0 else 1.0,
    'profit_lock_threshold': round(unlocked_trades['peak_profit'].mean() / 2, 2) if len(unlocked_trades) > 0 else 1.0,
}

print(f"\n```python")
print(f"class OptimizedExitManager:")
print(f"    def __init__(self):")
print(f"        self.take_profit_pct = {optimized_params['take_profit_pct']}  # User's median TP")
print(f"        self.stop_loss_pct = {optimized_params['stop_loss_pct']}  # User's median loss")
print(f"        self.trailing_stop_width = {optimized_params['trailing_stop_width']}  # User's median giveback")
print(f"        self.profit_lock_threshold = {optimized_params['profit_lock_threshold']}  # Prevent reversals")
print(f"        self.max_hold_hours = 48")
print(f"```")

# Compare to current bot settings
print(f"\n📊 COMPARISON: Current Bot vs Optimized (User Pattern)")
print(f"\n{'Parameter':<25} {'Current Bot':<15} {'User Pattern':<15} {'Difference'}")
print(f"{'-'*75}")

tp_user = optimized_params['take_profit_pct']
sl_user = optimized_params['stop_loss_pct']
trail_user = optimized_params['trailing_stop_width']
lock_user = optimized_params['profit_lock_threshold']

print(f"{'Take Profit':<25} {'5.0%':<15} {tp_user}%{'':<10} {tp_user - 5.0:+.2f}%")
print(f"{'Stop Loss':<25} {'0.75%':<15} {sl_user}%{'':<10} {sl_user - 0.75:+.2f}%")
print(f"{'Trailing Width':<25} {'1.5-2.5%':<15} {trail_user}%{'':<10} {'Variable'}")
print(f"{'Profit Lock':<25} {'1.5%':<15} {lock_user}%{'':<10} {lock_user - 1.5:+.2f}%")

# Expected improvement
print(f"\n💡 EXPECTED IMPROVEMENTS:")
print(f"   1. Lower TP ({optimized_params['take_profit_pct']}% vs 5%) → Capture profits faster")
print(f"   2. Tighter SL ({optimized_params['stop_loss_pct']}% vs 0.75%) → Cut losses at exact user level")
print(f"   3. Optimized trailing ({optimized_params['trailing_stop_width']}%) → Match user's giveback tolerance")
print(f"   4. Profit lock ({optimized_params['profit_lock_threshold']}%) → Prevent winner reversals")

# Save results
results = {
    'total_trades': len(df),
    'winners': len(winners),
    'losers': len(losers),
    'exit_categories': df['exit_category'].value_counts().to_dict(),
    'winner_stats': {
        'avg_profit': float(winners['profit_pct'].mean()),
        'median_profit': float(winners['profit_pct'].median()),
        'avg_peak': float(winners['peak_profit'].mean()),
        'avg_capture_ratio': float(winners['capture_ratio'].mean())
    },
    'loser_stats': {
        'avg_loss': float(losers['profit_pct'].mean()),
        'median_loss': float(losers['profit_pct'].median()),
        'avg_peak': float(losers['peak_profit'].mean()),
        'avg_giveback': float(losers['total_giveback'].mean())
    },
    'optimized_params': optimized_params
}

output_file = data_dir / 'ml_exit_analysis.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n💾 Analysis saved to: {output_file}")
print("="*80 + "\n")
