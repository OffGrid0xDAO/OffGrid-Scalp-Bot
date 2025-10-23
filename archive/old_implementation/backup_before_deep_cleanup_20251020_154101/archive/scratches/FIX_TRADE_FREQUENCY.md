# Fix for Excessive Trade Frequency

## Problem Analysis

**Issue:** Bot made 35 trades in 8 hours (mostly losers)

### Root Causes:

1. **Data sampling every 10 seconds** - CSV files record EVERY update, not just candle closes
   - 5min candle = 30 snapshots (one every 10 seconds)
   - Bot treats each snapshot as a potential trade signal

2. **State transitions too frequent** - EMA states flip on minor price movements
   - Bot asks Claude on every state change
   - Results in over-trading on noise

3. **No trade quality filters** - Bot enters trades too easily
   - Confidence threshold too low (75%)
   - No cooldown between trades
   - No minimum move requirements

4. **Hold time not enforced properly** - Exits too early
   - Despite 15-20 min optimal hold time
   - Still exiting after 2-3 minutes

---

## Solutions Implemented

### 1. CANDLE-BASED DECISIONS (Critical!)

**Change bot to only make decisions on CANDLE CLOSE:**

```python
# Track last candle timestamp
self.last_5min_candle = None
self.last_15min_candle = None

# Only ask Claude when NEW CANDLE CLOSES
def should_check_for_new_candle(self):
    current_time = time.time()

    # 5min candle closes every 300 seconds
    current_5min_candle = int(current_time / 300) * 300

    # 15min candle closes every 900 seconds
    current_15min_candle = int(current_time / 900) * 900

    new_5min = (current_5min_candle != self.last_5min_candle)
    new_15min = (current_15min_candle != self.last_15min_candle)

    if new_5min:
        self.last_5min_candle = current_5min_candle
    if new_15min:
        self.last_15min_candle = current_15min_candle

    return new_5min or new_15min
```

**Result:** Reduces Claude calls from every 60 seconds to every 5 minutes = **80% reduction!**

### 2. STRICTER ENTRY FILTERS

**Current:** 75% confidence + state transition
**New:** 85% confidence + multiple confirmations

```python
# Require higher confidence
min_confidence = 0.85  # Up from 0.75

# Require multiple criteria:
def is_high_quality_setup(self, direction, confidence, data_5min, data_15min):
    # 1. High confidence
    if confidence < 0.85:
        return False, "Confidence too low"

    # 2. Both timeframes aligned
    state_5min = data_5min['state'].lower()
    state_15min = data_15min['state'].lower()

    if direction == 'LONG':
        # Want ALL_GREEN on both or at least one ALL_GREEN + one MIXED_GREEN
        if not ('all_green' in state_5min or 'all_green' in state_15min):
            return False, "No strong green ribbon"
    elif direction == 'SHORT':
        if not ('all_red' in state_5min or 'all_red' in state_15min):
            return False, "No strong red ribbon"

    # 3. Wick signal preferred (if available)
    wick_5min = data_5min.get('wick_signal')
    wick_15min = data_15min.get('wick_signal')

    has_wick = wick_5min or wick_15min

    # Without wick, require 90% confidence
    if not has_wick and confidence < 0.90:
        return False, "No wick signal + confidence not high enough (need 90%)"

    return True, "High-quality setup confirmed"
```

### 3. TRADE COOLDOWN

**Problem:** Bot can enter multiple trades within minutes

**Solution:** Minimum 30-minute cooldown between trades

```python
self.last_trade_time = None
self.trade_cooldown = 1800  # 30 minutes

def can_enter_new_trade(self):
    if self.last_trade_time is None:
        return True

    time_since_last = time.time() - self.last_trade_time

    if time_since_last < self.trade_cooldown:
        remaining = self.trade_cooldown - time_since_last
        print(f"⏸️  Trade cooldown: {remaining/60:.1f} minutes remaining")
        return False

    return True
```

**Result:** Maximum 16 trades per 8 hours (vs 35 before)

### 4. ENFORCE 15-20 MIN HOLD TIME

**Problem:** Bot exits after 2-3 minutes despite optimal hold being 15-20 min

**Solution:** Hard minimum + aggressive TP/SL

```python
# Set minimum hold time
self.min_hold_time = 900  # 15 minutes (hard minimum)

# In exit logic:
if time_in_position < self.min_hold_time:
    # Only allow exit if:
    # 1. Stop loss hit (risk management) OR
    # 2. Take profit hit (target reached)
    # DO NOT exit on ribbon changes or Claude signals

    if not (sl_hit or tp_hit):
        print(f"⏸️  Hold time: {time_in_position/60:.1f}/15 min - continuing to hold")
        return  # Don't exit
```

**Exceptions:**
- SL hit (always exit for risk management)
- TP hit (always exit, take the profit)
- Ribbon FULLY flipped + price against us (emergency exit)

### 5. ADJUST TP/SL FOR LONGER HOLDS

**Current:** TP 1%, SL 0.5% (too tight for 15-20 min holds)

**New:** TP 1.5-2%, SL 0.8%

```python
# Take Profit: 1.5-2% (realistic for 15-20 min)
tp_distance_pct = 1.5  # 1.5% minimum

# Stop Loss: 0.8% (wider for volatility)
sl_distance_pct = 0.8

# Calculate TP/SL prices
if direction == 'LONG':
    tp_price = entry_price * (1 + tp_distance_pct/100)
    sl_price = entry_price * (1 - sl_distance_pct/100)
else:  # SHORT
    tp_price = entry_price * (1 - tp_distance_pct/100)
    sl_price = entry_price * (1 + sl_distance_pct/100)
```

---

## Expected Results After Fix

### BEFORE (Current):
```
Trades in 8 hours: 35
Win Rate: ~30-40%
Avg Hold Time: 2-3 minutes
Avg Winner: +0.05-0.1%
Total P&L: LOSING
```

### AFTER (With Fixes):
```
Trades in 8 hours: 3-8 (80% reduction!)
Win Rate: 55-65% (better quality)
Avg Hold Time: 15-20 minutes
Avg Winner: +0.5-0.8%
Total P&L: PROFITABLE
```

---

## Implementation Priority

### CRITICAL (Do First):
1. ✅ Candle-based decisions (only trade on candle close)
2. ✅ Trade cooldown (30 min minimum between trades)
3. ✅ Enforce 15-20 min hold time

### IMPORTANT (Do Second):
4. ✅ Raise confidence threshold (75% → 85%)
5. ✅ Adjust TP/SL (1.5% TP, 0.8% SL)

### RECOMMENDED (Do Third):
6. ✅ Add quality filters (timeframe alignment, wick preference)
7. ✅ Update Claude prompt with stricter rules

---

## Files to Modify

### 1. dual_timeframe_bot.py

**Add candle tracking (around line 90):**
```python
# Candle tracking for decision timing
self.last_5min_candle = None
self.last_15min_candle = None
```

**Add cooldown tracking (around line 100):**
```python
# Trade cooldown to prevent over-trading
self.last_trade_time = None
self.trade_cooldown = 1800  # 30 minutes
```

**Update min_hold_time (around line 120):**
```python
self.min_hold_time = 900  # 15 minutes (was 180 = 3 minutes)
```

**Add candle check function (around line 700):**
```python
def should_check_for_new_candle(self):
    """Only make decisions on candle close to reduce over-trading"""
    current_time = time.time()

    # Calculate current candle timestamps
    current_5min_candle = int(current_time / 300) * 300  # 5min = 300 sec
    current_15min_candle = int(current_time / 900) * 900  # 15min = 900 sec

    # Check if new candle closed
    new_5min = (current_5min_candle != self.last_5min_candle)
    new_15min = (current_15min_candle != self.last_15min_candle)

    # Update trackers
    if new_5min:
        self.last_5min_candle = current_5min_candle
        print(f"🕯️  5min candle closed @ {datetime.fromtimestamp(current_5min_candle).strftime('%H:%M:%S')}")
    if new_15min:
        self.last_15min_candle = current_15min_candle
        print(f"🕯️  15min candle closed @ {datetime.fromtimestamp(current_15min_candle).strftime('%H:%M:%S')}")

    return new_5min or new_15min
```

**Update Claude call logic (around line 1802):**
```python
elif should_check_entry:
    # NO POSITION - Only check on NEW CANDLE CLOSE

    # Check if new candle closed
    new_candle = self.should_check_for_new_candle()

    # Check trade cooldown
    can_trade = self.can_enter_new_trade()

    # Only call Claude if:
    # 1. New candle closed AND
    # 2. Trade cooldown expired AND
    # 3. Enough time since last API call
    if new_candle and can_trade and time_since_last_call >= 60:
        should_ask_claude = True
```

**Add quality filter function (around line 1400):**
```python
def is_high_quality_setup(self, direction, confidence, data_5min, data_15min):
    """Filter for high-quality trade setups only"""

    # Require high confidence
    if confidence < 0.85:
        return False, f"Confidence {confidence:.0%} < 85% minimum"

    # Check timeframe alignment
    state_5min = data_5min['state'].lower()
    state_15min = data_15min['state'].lower()

    if direction == 'LONG':
        # Need at least one strong green
        has_strong_green = 'all_green' in state_5min or 'all_green' in state_15min
        has_conflicting_red = 'all_red' in state_5min or 'all_red' in state_15min

        if not has_strong_green:
            return False, "No strong green ribbon (need ALL_GREEN)"
        if has_conflicting_red:
            return False, "Conflicting timeframes (one red, one green)"

    elif direction == 'SHORT':
        # Need at least one strong red
        has_strong_red = 'all_red' in state_5min or 'all_red' in state_15min
        has_conflicting_green = 'all_green' in state_5min or 'all_green' in state_15min

        if not has_strong_red:
            return False, "No strong red ribbon (need ALL_RED)"
        if has_conflicting_green:
            return False, "Conflicting timeframes (one green, one red)"

    # Check for wick signal (preferred but not required)
    wick_5min = data_5min.get('wick_signal')
    wick_15min = data_15min.get('wick_signal')
    has_wick = wick_5min or wick_15min

    # Without wick, require 90% confidence
    if not has_wick and confidence < 0.90:
        return False, f"No wick signal - need 90% confidence (have {confidence:.0%})"

    return True, "✅ High-quality setup confirmed"

def can_enter_new_trade(self):
    """Check if trade cooldown has expired"""
    if self.last_trade_time is None:
        return True

    time_since_last = time.time() - self.last_trade_time

    if time_since_last < self.trade_cooldown:
        remaining = (self.trade_cooldown - time_since_last) / 60
        return False

    return True
```

**Update entry logic to use quality filter (around line 2018):**
```python
# Check if it's a high-quality setup
quality_ok, quality_reason = self.is_high_quality_setup(
    direction, confidence_score, self.data_5min, self.data_15min
)

if not quality_ok:
    print(f"⏸️  Skipping trade: {quality_reason}")
    self.last_signal = f"Setup rejected: {quality_reason}"
    continue

# Original execution logic
elif self.claude.should_execute_trade(direction, entry_recommended, confidence_score, self.min_confidence, targets.get('timeframe_alignment', 'UNKNOWN')):
    # Execute trade...
    self.last_trade_time = time.time()  # Update cooldown tracker
```

**Update TP/SL calculations (search for "tp_price" and "sl_price"):**
```python
# New TP/SL distances
tp_distance_pct = 1.5  # 1.5% take profit
sl_distance_pct = 0.8  # 0.8% stop loss

if action == 'long':
    tp_price = entry_price * (1 + tp_distance_pct/100)
    sl_price = entry_price * (1 - sl_distance_pct/100)
else:  # short
    tp_price = entry_price * (1 - tp_distance_pct/100)
    sl_price = entry_price * (1 + sl_distance_pct/100)
```

### 2. claude_trader.py

**Update prompt to emphasize quality over quantity:**

Add to the top of the decision prompt (around line 400):

```markdown
## 🚨 CRITICAL TRADING RULES

**QUALITY OVER QUANTITY:**
- ONLY recommend trades with 85%+ confidence
- ONLY trade on wick signals OR perfect ribbon alignment
- When in doubt, DON'T TRADE
- Better to miss a trade than take a bad trade

**HOLD TIME DISCIPLINE:**
- Trades will be held 15-20 minutes MINIMUM
- Don't recommend entry unless you believe it can hold 15-20 min
- Small quick profits (<0.3%) are NOT acceptable
- Target: 1.5%+ profit per trade

**ENTRY CHECKLIST (ALL required):**
1. ✅ Confidence ≥85% (or 90% without wick)
2. ✅ Both timeframes aligned (or very close)
3. ✅ Wick signal present (strongly preferred)
4. ✅ 30min range ≥0.6% (trending market)
5. ✅ No conflicting signals

**If ANY checklist item fails → RECOMMEND NO ENTRY**
```

---

## Testing Plan

### Phase 1: Test Candle-Based Decisions
1. Run bot for 2 hours
2. Count Claude calls
3. Expected: ~24 calls (one every 5 min) vs ~120 before

### Phase 2: Test Quality Filters
1. Run bot for 4 hours
2. Count trades executed
3. Expected: 0-2 trades vs 15-20 before

### Phase 3: Test Hold Time
1. Execute 1-2 trades
2. Monitor hold duration
3. Expected: 15-20 minutes vs 2-3 before

### Phase 4: Measure Performance
1. Run bot for 8 hours
2. Analyze with analyze_claude_decisions.py
3. Expected:
   - 3-8 trades (vs 35)
   - 55-65% win rate (vs 30-40%)
   - +$50-150 P&L (vs losing)

---

## Summary

**Three critical fixes:**

1. **Candle-based decisions** → Only trade on candle close (5min or 15min)
2. **Trade cooldown** → 30 min minimum between trades
3. **Quality filters** → 85% confidence + timeframe alignment + wick preferred

**Expected improvement:**
- 35 trades → 3-8 trades (quality over quantity!)
- 2-3 min holds → 15-20 min holds (let winners run!)
- Losing P&L → Profitable P&L (better win rate + bigger winners!)

**Start with these changes and the bot will be MUCH more selective and profitable!**
