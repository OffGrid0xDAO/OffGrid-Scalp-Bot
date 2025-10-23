#!/usr/bin/env python3
"""
Apply Strategy Refinements Based on Overlap Analysis

Key Changes:
1. REJECT if volume_status == 'low' (eliminates 36% of false signals!)
2. Require volume_ratio > 1.0x (user avg 1.51x vs false 0.80x)
3. Tighten RSI-7 range (user avg 39.8 vs false 45.0)
4. Add Stoch D filter > 40 (user avg 50.8 vs false 45.7)
5. Increase min confluence score from 10 to 20
6. Add small confluence gap requirement (10 points minimum)
7. Increase quality score threshold from 30 to 50
"""

import json
from pathlib import Path

# Load current strategy params
params_file = Path(__file__).parent / 'src' / 'strategy' / 'strategy_params_user.json'

with open(params_file, 'r') as f:
    params = json.load(f)

print("🔧 APPLYING STRATEGY REFINEMENTS")
print("="*80)

# Show current settings
print("\n📋 Current Settings:")
print(f"  Min confluence score: {params['entry_filters']['confluence_score_min']}")
print(f"  Min confluence gap: {params['entry_filters']['confluence_gap_min']}")
print(f"  Volume requirement: {params['entry_filters']['volume_requirement']}")
print(f"  Min quality score: {params['entry_filters']['min_quality_score']}")

# Apply refinements
print("\n✨ Applying Refinements...")

# 1. Volume filters
params['entry_filters']['volume_requirement'] = ["spike", "elevated", "normal"]  # Remove 'low'
print("  ✅ 1. REJECT LOW volume (was allowing low)")

# 2. Add volume ratio requirement
params['entry_filters']['min_volume_ratio'] = 1.0
print("  ✅ 2. Require volume_ratio > 1.0x (was no requirement)")

# 3. Tighten RSI-7 range
params['entry_filters']['rsi_7_range'] = [25, 50]
print("  ✅ 3. Add RSI-7 range [25, 50] (was not filtered)")

# 4. Add Stoch D filter
params['entry_filters']['min_stoch_d'] = 35
print("  ✅ 4. Require Stoch D > 35 (was not filtered)")

# 5. Increase min confluence
params['entry_filters']['confluence_score_min'] = 20
print("  ✅ 5. Min confluence score: 10 → 20")

# 6. Add confluence gap
params['entry_filters']['confluence_gap_min'] = 10
print("  ✅ 6. Min confluence gap: 0 → 10")

# 7. Increase quality threshold
params['entry_filters']['min_quality_score'] = 50
print("  ✅ 7. Min quality score: 30 → 50")

# Save refined params
with open(params_file, 'w') as f:
    json.dump(params, f, indent=2)

print("\n💾 Refined parameters saved to: {params_file}")

print("\n📊 Expected Impact:")
print("  Current: 241 signals (11x too many)")
print("  Target: ~40-50 signals (2x user's 22)")
print("  False positive rate: 81.3% → ~50-60% (expected)")

print("\n✅ REFINEMENTS APPLIED!")
print("="*80)
print("\n📈 Next: Re-run backtest to see improvement")
print("   Run: python backtest_user_strategy.py")

