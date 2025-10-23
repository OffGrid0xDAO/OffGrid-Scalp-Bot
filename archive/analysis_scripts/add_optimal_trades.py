#!/usr/bin/env python3
"""
Add the user's optimal trades to the dataset
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from regenerate_optimal_trades import OptimalTradesCollector

# Initialize collector
collector = OptimalTradesCollector()

print("Adding 22 optimal trades from October 5-21, 2025...")
print("="*80)

# List of optimal trades provided by user
optimal_trades = [
    # (entry_time, exit_time, direction, reason)
    ("2025-10-05 18:30", "2025-10-06 21:00", "long", "User identified optimal long entry"),
    ("2025-10-07 08:20", "2025-10-07 13:30", "long", "User identified optimal long entry"),
    ("2025-10-07 13:45", "2025-10-08 05:35", "short", "User identified optimal short entry"),
    ("2025-10-08 21:15", "2025-10-09 18:30", "short", "User identified optimal short entry"),
    ("2025-10-10 14:30", "2025-10-10 21:15", "short", "User identified optimal short entry"),
    ("2025-10-11 21:30", "2025-10-12 09:20", "long", "User identified optimal long entry"),
    ("2025-10-12 14:15", "2025-10-13 09:45", "long", "User identified optimal long entry"),
    ("2025-10-13 11:45", "2025-10-13 23:30", "long", "User identified optimal long entry"),
    ("2025-10-14 01:45", "2025-10-14 11:30", "short", "User identified optimal short entry"),
    ("2025-10-14 14:15", "2025-10-14 19:00", "long", "User identified optimal long entry"),
    ("2025-10-15 05:00", "2025-10-15 09:00", "long", "User identified optimal long entry"),
    ("2025-10-15 09:15", "2025-10-15 18:45", "short", "User identified optimal short entry"),
    ("2025-10-15 22:10", "2025-10-16 07:15", "long", "User identified optimal long entry"),
    ("2025-10-16 14:05", "2025-10-16 21:30", "short", "User identified optimal short entry"),
    ("2025-10-17 05:15", "2025-10-17 09:30", "short", "User identified optimal short entry"),
    ("2025-10-17 15:45", "2025-10-18 08:30", "long", "User identified optimal long entry"),
    ("2025-10-19 09:30", "2025-10-19 17:15", "long", "User identified optimal long entry"),
    ("2025-10-19 23:15", "2025-10-20 00:45", "short", "User identified optimal short entry"),
    ("2025-10-20 02:30", "2025-10-20 07:15", "long", "User identified optimal long entry"),
    ("2025-10-20 16:00", "2025-10-20 18:00", "short", "User identified optimal short entry"),
    ("2025-10-21 01:00", "2025-10-21 06:00", "short", "User identified optimal short entry"),
    ("2025-10-21 12:00", "2025-10-21 15:00", "long", "User identified optimal long entry"),
]

# Add each trade
for i, (entry_time, exit_time, direction, reason) in enumerate(optimal_trades, 1):
    print(f"\n[{i}/22] Processing {direction.upper()} entry at {entry_time}...")

    try:
        collector.add_optimal_entry(
            timestamp=entry_time,
            direction=direction,
            reason=reason,
            exit_timestamp=exit_time
        )
        print(f"✅ Trade {i} added successfully")
    except Exception as e:
        print(f"❌ Error adding trade {i}: {e}")
        continue

print("\n" + "="*80)
print("🎉 FINISHED ADDING OPTIMAL TRADES")
print("="*80)

# Show final summary
collector.show_summary()

print("\n✅ Next step: Run pattern analysis to discover what these trades have in common!")
print("   Command: python analyze_optimal_patterns.py")
