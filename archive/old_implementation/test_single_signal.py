#!/usr/bin/env python3
"""
Test why backtest finds 1 trade but signal scanner finds 179
"""

import pandas as pd
from rule_based_trader import RuleBasedTrader

# Load data
df = pd.read_csv('trading_data/ema_data_5min.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Initialize trader
trader = RuleBasedTrader()

# Test the first signal from compare_trading_systems.py
# Signal #1 was at: 2025-10-17 15:13:25.910238: LONG Q:88 P:3778.8

# Find this timestamp in our data
target_time = pd.Timestamp('2025-10-17 15:13:25.910238')
time_diff = abs(df['timestamp'] - target_time)
closest_idx = time_diff.idxmin()

print(f"Testing signal at index {closest_idx}")
print(f"Timestamp: {df.iloc[closest_idx]['timestamp']}")
print(f"Price: {df.iloc[closest_idx]['price']}")

# Build indicators like the backtest does
row = df.iloc[closest_idx]
indicators_5min = {'ribbon_state': row.get('ribbon_state', 'unknown'), 'price': row.get('price', 0)}

for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60]:
    val_col = f'MMA{ema}_value'
    color_col = f'MMA{ema}_color'
    intensity_col = f'MMA{ema}_intensity'
    if val_col in row.index:
        indicators_5min[f'MMA{ema}'] = {
            'value': row[val_col],
            'color': row[color_col],
            'intensity': row[intensity_col]
        }

# Get decision
df_recent = df.iloc[:closest_idx+1]
decision = trader.get_trading_decision(
    indicators_5min=indicators_5min,
    indicators_15min=indicators_5min,
    current_price=row['price'],
    current_position=None,
    df_recent=df_recent
)

print(f"\nDecision: {decision.get('entry_recommended', False)}")
print(f"Reason: {decision.get('reason', 'no reason')}")
if 'quality_score' in decision:
    print(f"Quality Score: {decision['quality_score']}")
if 'confidence' in decision:
    print(f"Confidence: {decision['confidence']}")
