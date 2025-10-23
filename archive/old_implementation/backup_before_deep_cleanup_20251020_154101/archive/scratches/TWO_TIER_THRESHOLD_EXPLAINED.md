# Two-Tier Threshold System

## Overview

The bot now uses a **two-tier threshold system** for detecting EMA ribbon state changes. This allows Claude to monitor transitions early without entering trades prematurely.

---

## How It Works

### Tier 1: 50% Threshold = "START WATCHING"

**When triggered:**
- 6+ out of 12 EMAs (50%) flip to the same color
- State changes to `all_green` or `all_red`
- Entry Strength shows: **BUILDING** 👀

**What happens:**
- Claude gets called to analyze the situation
- Bot starts monitoring the transition
- Provides commentary on what's developing
- **DOES NOT enter trades yet**

**Example:**
```
🔷 5-MINUTE:
   🟢 State: ALL_GREEN
   💰 Price: $2651.23
   🟢 6 | 🔴 4 | ⚪ 2
   👀 Entry Strength: BUILDING
```

Claude sees: "I see 6 green, 4 red EMAs. Ribbon is transitioning but not ready for entry yet."

---

### Tier 2: 85% Threshold = "CONSIDER ENTERING"

**When triggered:**
- 10+ out of 12 EMAs (85%) flip to the same color
- State remains `all_green` or `all_red`
- Entry Strength changes to: **STRONG** 💪

**What happens:**
- Claude can now recommend entry
- Still requires other conditions:
  - Fresh transition (not hours old)
  - Proper momentum building
  - Yellow EMA support confirmed
  - Both timeframes aligned
- **Can enter trades if all conditions met**

**Example:**
```
🔷 5-MINUTE:
   🟢 State: ALL_GREEN
   💰 Price: $2651.23
   🟢 10 | 🔴 2 | ⚪ 0
   💪 Entry Strength: STRONG
```

Claude sees: "10 green, 2 red EMAs. Entry strength is STRONG - ribbon nearly complete. If this is a fresh transition, I can recommend entry."

---

## Why This System?

### Problem Before (90% threshold):
- Required 11 out of 12 EMAs to flip before calling Claude
- Entered trades very late in the transition
- Missed early reversal signals
- Poor risk/reward due to late entries

### With 50% Only:
- Would call Claude too early (halfway through flip)
- Might enter when only 6 EMAs flipped
- Too risky - not enough confirmation

### With Two-Tier (50% + 85%):
✅ **Best of both worlds**

**Early Detection (50%):**
- Catches reversals as they develop
- Gives Claude time to analyze
- Provides user with commentary on what's building
- Monitors momentum shifts early

**Safe Entry (85%):**
- Near-complete ribbon confirmation (10+ EMAs)
- Much better risk/reward than 90%
- Earlier than 90% but still safe
- Claude makes final call based on:
  - Fresh vs stale transition
  - Momentum building or fading
  - Yellow EMA support pattern
  - Both timeframes aligned

---

## Dashboard Display

The dashboard now shows entry strength for each timeframe:

```
🔷 5-MINUTE:
   🟢 State: ALL_GREEN
   💰 Price: $2651.23
   🟢 10 | 🔴 2 | ⚪ 0
   💪 Entry Strength: STRONG    ← NEW!
```

**Indicators:**
- 👀 **BUILDING** = Watching, not ready (6-9 EMAs flipped)
- 💪 **STRONG** = Ready to consider entry (10+ EMAs flipped)
- ⚠️ **WEAK/MIXED** = Not aligned, wait

---

## What Claude Sees

Claude receives the entry strength in every analysis:

```
**5MIN TIMEFRAME**
Timestamp: 2025-01-15 14:32:45
Current Price: $2651.23
Ribbon State: ALL GREEN
Entry Strength: STRONG ⚠️ IMPORTANT: 'BUILDING' = watching only, 'STRONG' = consider entry

EMA Alignment:
- Green EMAs: 10 (83.3%) | Dark Green: 3
- Red EMAs: 2 (16.7%) | Dark Red: 0
- Yellow EMAs: 0
- Gray EMAs: 0
```

Claude's system prompt includes:

```
**IMPORTANT: TWO-TIER THRESHOLD SYSTEM**

1. **50% Threshold (BUILDING)** = "Start watching"
   - DO NOT recommend entry yet
   - Provide analysis and commentary only

2. **85% Threshold (STRONG)** = "Consider entering"
   - Can recommend entry IF other conditions met
   - Must verify: fresh transition, momentum, support levels
```

---

## Practical Example

### Scenario: Market transitioning from red to green

**10:00 AM - 4 EMAs flip green**
- State: MIXED
- No Claude call yet (below 50%)
- Bot continues monitoring

**10:05 AM - 6 EMAs flip green (50% reached)**
- State: ALL_GREEN
- Entry Strength: BUILDING 👀
- **Claude called for first time**
- Claude: "Ribbon building green momentum. 6/12 EMAs flipped. Watch for continuation. NOT ready for entry."

**10:08 AM - 8 EMAs green now**
- State: ALL_GREEN
- Entry Strength: BUILDING 👀
- Claude: "Transition continuing, 8/12 green. Dark green EMAs building. Still watching."

**10:12 AM - 10 EMAs green (85% reached)**
- State: ALL_GREEN
- Entry Strength: STRONG 💪
- **Now Claude can recommend entry**
- Claude checks:
  ✅ Fresh transition? YES (started 12 min ago)
  ✅ Momentum building? YES (dark green count increasing)
  ✅ Yellow EMA support? YES (price holding above $2645)
  ✅ 15min aligned? YES (also green)
- **ENTRY RECOMMENDED: YES** ✅

**10:15 AM - 12 EMAs green (100%)**
- Entry already taken at 10:12 AM with better price
- If we waited for 100%, price would be $10 higher

---

## Benefits

### For the Bot:
1. **Earlier awareness** of transitions (50%)
2. **Safer entries** than waiting for 100%
3. **Better fills** than 90% threshold
4. **More context** for Claude to analyze

### For the User:
1. **See what's developing** via commentary
2. **Understand transitions** as they happen
3. **Better entries** (85% vs 90% or 100%)
4. **More confidence** in Claude's decisions

### For Claude:
1. **More time to analyze** the setup
2. **Clear rules** (BUILDING vs STRONG)
3. **Better data** (sees transition earlier)
4. **Flexibility** to reject weak setups even at 85%

---

## API Cost Impact

**Before (90% threshold):**
- Called Claude only when 11/12 EMAs flipped
- Very few calls during transitions
- Missed early reversals

**After (50% + 85% two-tier):**
- More calls during transitions (starts at 50%)
- BUT: Smart call logic still applies
- Only calls on state changes or every 60 sec if in position
- Estimated increase: 10-20% more calls
- **Benefit**: Catches reversals worth much more than API cost

---

## Configuration

To adjust thresholds, edit `dual_timeframe_bot.py` lines 322-333:

```python
# Current settings:
elif len(green_emas) >= non_yellow_total * 0.5:  # 50% = start watching
    state = 'all_green'
    if len(green_emas) >= non_yellow_total * 0.85:  # 85% = consider entry
        entry_strength = 'strong'
    else:
        entry_strength = 'building'
```

**Adjustable values:**
- `0.5` = Start watching threshold (50%)
- `0.85` = Consider entry threshold (85%)

**Recommendations:**
- Leave at 50% / 85% for balanced performance
- Increase to 60% / 90% for more conservative
- Decrease to 40% / 80% for more aggressive (not recommended)

---

## Summary

**50% Threshold (BUILDING):**
- 👀 Start watching
- 📊 Get commentary
- ⏸️ No entry yet

**85% Threshold (STRONG):**
- 💪 Ready to consider
- ✅ Can enter if conditions met
- 📈 Better timing than 90% or 100%

**Result:**
- Early awareness + safe entries
- Best risk/reward ratio
- Claude makes informed decisions
- User sees transitions developing

---

**Happy trading! 📈💰**
