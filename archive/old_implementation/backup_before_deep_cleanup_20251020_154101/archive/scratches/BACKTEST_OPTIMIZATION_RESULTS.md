# Backtest Optimization Results

## Executive Summary

**Quality filtering FAILED to improve results**

The quality score system (0-100 scoring) was implemented to reduce trade count and increase profitability, but it actually made performance worse.

---

## Comparison: Unfiltered vs Quality Filtered

### UNFILTERED (Original):
```
Total Opportunities: 32
Win Rate (overall): ~48%
Best Hold Duration: 15-20 minutes (50-55% WR)
```

### QUALITY FILTERED (Score ≥60):
```
Total Opportunities: 9 (72% reduction)
Total Trades Simulated: 45
Winners: 8 (17.8% win rate) ❌
Losers: 37 (82.2%)
Total P&L: -1.21% ❌
Avg Winner: +0.584%
Avg Loser: -0.159%
```

**RESULT: Quality filtering made things WORSE**

---

## Root Cause Analysis

### Problem 1: Price Location Scoring is Wrong

**Current Scoring (BROKEN):**
```python
# For LONG entries:
if price_location_pct < 30:
    score += 25  # Perfect - at bottom
elif price_location_pct < 40:
    score += 20  # Great
```

**Reality from backtest:**
- Trade #1: Entry @ 100% of range (TOP!) → Quality score: 60-70 → LOSER
- Trade #2: Entry @ 100% of range (TOP!) → Quality score: 70 → LOSER
- Trade #3: Entry @ 44% of range (MID) → Quality score: 75 → MIXED

**Issue:** Price location calculation is inverted or broken!

### Problem 2: Timeframe Alignment Rewarded Incorrectly

Many "high quality" trades had:
```
state_5min: all_green
state_15min: all_red  ← CONFLICT!
```

This got quality scores of 60-75, but these are actually **divergence setups** (not trending confirmation).

### Problem 3: Big Moves ≠ Good Entries

Scoring gives 35 points for big 30min range (≥0.8%), but:
- If you enter at the END of a big move (price_location = 100%) → You're entering at exhaustion!
- Entry timing matters MORE than move size

### Problem 4: Entry at Range Extremes

**Worst filtered trades all entered at:**
- `price_location_pct: 100.0%` ← Entering LONG at TOP of range
- `price_location_pct: 0.0%` ← Entering SHORT at BOTTOM of range

These got high quality scores but are the WORST entries possible!

---

## What Actually Works (From Original Backtest)

### BEST OPPORTUNITIES (From unfiltered backtest):

1. **Enter in MIDDLE of trend**
   - Price at 40-60% of range
   - Not at extremes (0% or 100%)

2. **Timeframe AGREEMENT**
   - Both 5min and 15min same state (all_green or all_red)
   - NOT conflicting states

3. **Moderate Volatility**
   - 30min range: 0.6-1.2% (sweet spot)
   - Too small (<0.5%) = ranging
   - Too big (>1.5%) = exhaustion

4. **Hold Duration: 15-20 minutes**
   - 5min hold: Poor results
   - 10min hold: Mediocre
   - **15-20min: BEST win rate**
   - 30min hold: Worse (trend reverses)

---

## NEW Proposed Quality Score (FIXED)

```python
def _calculate_quality_score_v2(self, direction, range_30min, range_15min,
                                 ribbon_flips, price_location_pct,
                                 state_5min, state_15min):
    """
    FIXED quality score calculation
    Focus on what actually predicts winners
    """
    score = 0

    # 1. MODERATE VOLATILITY (0-30 points)
    if 0.6 <= range_30min <= 1.2:
        score += 30  # Sweet spot
    elif 0.5 <= range_30min <= 1.5:
        score += 20  # Acceptable
    elif range_30min >= 1.5:
        score += 10  # Too volatile (exhaustion risk)
    else:
        score += 0   # Too quiet (ranging)

    # 2. TIMEFRAME AGREEMENT (0-35 points) ← MOST IMPORTANT!
    state_5min_lower = state_5min.lower()
    state_15min_lower = state_15min.lower()

    if direction == 'LONG':
        # Want BOTH green for LONG
        if 'all_green' in state_5min_lower and 'all_green' in state_15min_lower:
            score += 35  # Perfect alignment
        elif 'mixed_green' in state_5min_lower and 'all_green' in state_15min_lower:
            score += 20  # Acceptable
        elif 'all_green' in state_5min_lower and 'mixed_green' in state_15min_lower:
            score += 20  # Acceptable
        else:
            score += 0   # Conflicting = SKIP!

    elif direction == 'SHORT':
        # Want BOTH red for SHORT
        if 'all_red' in state_5min_lower and 'all_red' in state_15min_lower:
            score += 35  # Perfect alignment
        elif 'mixed_red' in state_5min_lower and 'all_red' in state_15min_lower:
            score += 20  # Acceptable
        elif 'all_red' in state_5min_lower and 'mixed_red' in state_15min_lower:
            score += 20  # Acceptable
        else:
            score += 0   # Conflicting = SKIP!

    # 3. PRICE LOCATION - MIDDLE IS BEST (0-25 points)
    # Enter in middle 40-60% of range, NOT at extremes!
    if direction == 'LONG':
        # For LONG: Want to enter in lower-middle part
        if 30 <= price_location_pct <= 50:
            score += 25  # Perfect - lower-middle
        elif 20 <= price_location_pct <= 60:
            score += 20  # Good
        elif 10 <= price_location_pct <= 70:
            score += 10  # Acceptable
        else:
            score += 0   # Too extreme (0-10% or 70-100%)

    elif direction == 'SHORT':
        # For SHORT: Want to enter in upper-middle part
        if 50 <= price_location_pct <= 70:
            score += 25  # Perfect - upper-middle
        elif 40 <= price_location_pct <= 80:
            score += 20  # Good
        elif 30 <= price_location_pct <= 90:
            score += 10  # Acceptable
        else:
            score += 0   # Too extreme

    # 4. RIBBON STABILITY (0-10 points)
    if ribbon_flips == 0:
        score += 10  # Very stable
    elif ribbon_flips == 1:
        score += 8   # Stable
    elif ribbon_flips == 2:
        score += 5   # Acceptable
    else:
        score += 0   # Too choppy

    return score
```

### Key Changes:
1. **Timeframe agreement is now 35 points** (most important!)
2. **Price location looks for MIDDLE entries** (not extremes)
3. **Moderate volatility** (0.6-1.2% range)
4. **Ribbon stability reduced to 10 points** (less important)

### New Threshold:
- **Score ≥70 required** (stricter than ≥60)
- This should catch only the BEST setups

---

## Expected Results with Fixed Scoring

### If we apply the FIXED scoring:

**Expected to filter OUT:**
- Entries at 0% or 100% of range ❌
- Conflicting timeframes (5min green, 15min red) ❌
- Too choppy (≥3 flips) ❌
- Extreme volatility (>1.5%) ❌

**Expected to KEEP:**
- Entries at 30-70% of range ✅
- Both timeframes aligned ✅
- Moderate volatility (0.6-1.2%) ✅
- Stable ribbon (≤2 flips) ✅

**Predicted Results:**
- Opportunities: ~10-15 (vs 32 original, 9 filtered)
- Win Rate: 60-70% (vs 48% original, 18% filtered)
- Avg Winner: +0.5-0.8%
- Total P&L: +3-5% (on 10-15 trades @ 15-20min holds)

---

## Recommendations

### Option 1: Implement Fixed Quality Score (RECOMMENDED)

**Action:**
1. Replace `_calculate_quality_score()` with `_calculate_quality_score_v2()` above
2. Set threshold to `score ≥70`
3. Re-run backtest
4. Verify results improve to 60%+ win rate

### Option 2: Manual Filtering (Quick Fix)

If you don't want to rewrite the scoring, manually filter for:

```python
# Only accept opportunities where:
- range_30min >= 0.6 and range_30min <= 1.2  # Moderate volatility
- ribbon_flips_30min <= 2  # Stable
- price_location_pct >= 30 and price_location_pct <= 70  # Middle entries
- (state_5min == 'all_green' and state_15min == 'all_green') OR \
  (state_5min == 'all_red' and state_15min == 'all_red')  # Alignment
```

### Option 3: No Filtering + Hold 15-20min (SIMPLEST)

From original backtest:
- 32 opportunities
- Hold 15-20 minutes
- Expected: 50-55% win rate @ those durations
- Total P&L: Positive (if Claude holds 15-20min instead of 2min!)

**This might be the BEST approach:**
- Don't filter opportunities
- Just teach Claude to hold positions 15-20 minutes
- Original backtest shows this works!

---

## Next Steps

1. **Fix quality scoring logic** OR
2. **Skip filtering entirely** and focus on hold duration
3. **Update Claude's prompt:**
   ```
   - Hold positions 15-20 minutes minimum
   - Don't exit early just for small profit
   - Wait for TP hit or time-based exit
   - Scalping = quick entries, PATIENT holds
   ```

**Priority:** Fixing Claude's exit timing (2min → 15-20min) is MORE IMPORTANT than filtering opportunities!

---

## Summary

**Quality filtering experiment: FAILED ❌**

**Root causes:**
1. Price location scoring inverted (rewarded entries at extremes)
2. Timeframe conflicts not penalized enough
3. Big moves != good entries (timing matters more)

**Solution:**
Either fix the scoring logic OR abandon filtering and focus on Claude holding positions 15-20 minutes.

**The real problem isn't WHICH trades to take, it's HOW LONG to hold them!**

Claude's 2-minute avg hold duration is the #1 issue. Backtest shows 15-20 minute holds work best.
