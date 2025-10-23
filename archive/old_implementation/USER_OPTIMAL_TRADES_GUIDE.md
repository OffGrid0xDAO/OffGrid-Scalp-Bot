# User Optimal Trades Guide

## Overview

You can now specify EXACTLY which trades you want the bot to target, and I'll automatically fetch all the technical details (prices, EMA states, compression, etc.) from historical data.

## Quick Start

### Step 1: Create Your Optimal Trades

```bash
python3 create_user_optimal_trades.py
```

This will ask you interactively:

**For each trade:**
- **Entry time**: When to enter (you specify, I fetch the price)
- **Direction**: LONG or SHORT
- **Exit time**: When to exit (you specify, I fetch the price)

**I automatically calculate:**
- Entry/exit prices from historical data
- PnL percentage
- Ribbon state at entry
- Number of light EMAs
- Compression percentage
- EMA color distribution
- Hold time

### Step 2: Configure to Use Your Trades

Edit `.env` file:
```bash
OPTIMAL_TRADES_SOURCE=user
```

### Step 3: Run Optimization

```bash
# Claude-powered (recommended)
python3 run_claude_optimization.py 5 24

# OR simple math-based
python3 run_multiple_optimizations.py 5 24
```

The optimizer will now tune the rules to match YOUR specified trades!

## Time Format Options

The script accepts multiple time formats:

### Option 1: Absolute Time
```
Entry time: 2025-10-21 14:30:00
Exit time: 2025-10-21 15:45:00
```

### Option 2: Relative Time (Much Easier!)
```
Entry time: 2h30m ago
Exit time: 1h45m ago
```

Supported units:
- `d` = days
- `h` = hours
- `m` = minutes

Examples:
- `3h ago` = 3 hours ago
- `45m ago` = 45 minutes ago
- `1d ago` = 1 day ago
- `2h30m ago` = 2.5 hours ago

## Example Session

```bash
$ python3 create_user_optimal_trades.py

======================================================================
USER OPTIMAL TRADES CREATOR
======================================================================
Specify WHEN to enter/exit, I'll fetch prices and technical details

Time format options:
  1. Absolute: 2025-10-21 14:30:00
  2. Relative: 2h30m ago, 1d ago, 45m ago
======================================================================

📊 Loading historical EMA data...
✅ Loaded 8,452 5min candles
✅ Loaded 2,817 15min candles
📅 Data range: 2025-10-15 00:00:00 to 2025-10-21 14:30:00

======================================================================
TRADE #1
======================================================================

Entry time [or 'done' to finish]: 3h ago
Direction (LONG/SHORT): LONG
Exit time: 2h15m ago

🔍 Looking up data for LONG trade...
   Entry: 2025-10-21 11:30:00
   Exit: 2025-10-21 12:15:00

✅ Trade created:
   Actual Entry: 2025-10-21 11:32:00 @ $3,245.50
   Actual Exit:  2025-10-21 12:17:00 @ $3,261.20
   PnL: +0.48% (WIN)
   Hold Time: 45.0 minutes
   Ribbon State: all_green
   Light EMAs: 11
   Compression: 0.14%
   EMA Colors: 24 green, 2 red

✅ Add this trade? (y/n): y

======================================================================
TRADE #2
======================================================================

Entry time [or 'done' to finish]: 5h30m ago
Direction (LONG/SHORT): SHORT
Exit time: 4h ago

🔍 Looking up data for SHORT trade...
   Entry: 2025-10-21 09:00:00
   Exit: 2025-10-21 10:30:00

✅ Trade created:
   Actual Entry: 2025-10-21 09:02:00 @ $3,289.75
   Actual Exit:  2025-10-21 10:32:00 @ $3,273.10
   PnL: +0.51% (WIN)
   Hold Time: 90.0 minutes
   Ribbon State: all_red
   Light EMAs: 9
   Compression: 0.18%
   EMA Colors: 3 green, 23 red

✅ Add this trade? (y/n): y

======================================================================
TRADE #3
======================================================================

Entry time [or 'done' to finish]: done

======================================================================
SUMMARY
======================================================================
Total Trades: 2
Win Rate: 100.0%
Total PnL: +0.99%
Avg PnL per Trade: +0.49%
Avg Hold Time: 67.5 minutes
Avg Compression: 0.16%
Avg Light EMAs: 10.0
======================================================================

✅ Saved to trading_data/optimal_user_trades.json

📝 To use these as your optimization target:
   1. Add to .env: OPTIMAL_TRADES_SOURCE=user
   2. Run: python3 run_claude_optimization.py 5 24
```

## What Gets Saved

The script creates `trading_data/optimal_user_trades.json` with:

```json
{
  "analysis_timestamp": "2025-10-21T14:30:00",
  "source": "user_specified_times",
  "description": "User-specified optimal trades with auto-fetched technical details",
  "total_trades": 2,
  "winning_trades": 2,
  "losing_trades": 0,
  "win_rate": 1.0,
  "total_pnl_pct": 0.99,
  "avg_pnl_pct": 0.49,
  "patterns": {
    "avg_compression": 0.0016,
    "avg_light_emas": 10.0
  },
  "trades": [
    {
      "entry_time": "2025-10-21T11:32:00",
      "exit_time": "2025-10-21T12:17:00",
      "direction": "LONG",
      "entry_price": 3245.50,
      "exit_price": 3261.20,
      "pnl_pct": 0.48,
      "hold_time_minutes": 45.0,
      "winner": true,
      "compression": 0.0014,
      "light_emas": 11,
      "ribbon_state": "all_green",
      "ema_pattern": {
        "green_count": 24,
        "red_count": 2,
        "yellow_count": 0,
        "gray_count": 2,
        "dark_emas": 13
      }
    }
  ]
}
```

## Environment Variable

In `.env`:

```bash
# Optimization Settings
# Which optimal trades to use as benchmark: 'auto' (smart_trade_finder) or 'user' (optimal_user_trades.json)
OPTIMAL_TRADES_SOURCE=auto
```

**Options:**
- `auto` (default): Uses SmartTradeFinder to automatically find optimal trades from historical data
- `user`: Uses your manually specified trades from `optimal_user_trades.json`

## Use Cases

### Use Case 1: You Have Better Judgment
You spotted some perfect trade setups that the automatic finder missed. Specify them manually so the bot learns to catch them.

### Use Case 2: Conservative Strategy
The automatic finder takes too many trades. You specify only the absolute best setups, and the bot learns to be more selective.

### Use Case 3: Specific Pattern Focus
You noticed a specific EMA pattern that works well. Enter trades with that pattern, and the bot will optimize toward it.

### Use Case 4: Testing a Theory
You have a theory about when to trade. Input trades following your theory, run optimization, and see if the bot converges.

## Workflow Comparison

### Automatic (Default)
```bash
# Just run optimization
python3 run_claude_optimization.py 5 24
```
**Pros:** Fast, no manual work
**Cons:** May include suboptimal trades

### User-Specified (Manual)
```bash
# Step 1: Create your trades
python3 create_user_optimal_trades.py

# Step 2: Edit .env
# OPTIMAL_TRADES_SOURCE=user

# Step 3: Run optimization
python3 run_claude_optimization.py 5 24
```
**Pros:** Perfect control, bot learns YOUR strategy
**Cons:** Requires manual input

## Tips

1. **Look at recent history**: Use relative times like "2h ago" to specify recent trades you observed

2. **Be realistic**: Only specify trades you genuinely would have taken in real-time

3. **Include both wins and losses**: If you specify only winners, the bot will overfit

4. **Check the data range**: The script shows the available data range at startup

5. **Review the summary**: Before saving, check if the avg compression and light EMAs make sense

6. **Start small**: Create 5-10 trades first, run optimization, see results

7. **Iterate**: After optimization, check if the bot's behavior matches your expectations

## Switching Between Auto and User

You can easily switch:

```bash
# Use automatic optimal finder
export OPTIMAL_TRADES_SOURCE=auto
python3 run_claude_optimization.py 5 24

# Use your manual trades
export OPTIMAL_TRADES_SOURCE=user
python3 run_claude_optimization.py 5 24
```

Or edit `.env` and restart.

## Troubleshooting

**Q: "No data at that time"**
- Check the data range shown at startup
- Use more recent times
- Run the bot to collect more historical data

**Q: "Trade shows as loss but I think it's a win"**
- Check the actual prices fetched
- The script finds the CLOSEST candle to your time
- May need to adjust your time slightly

**Q: "Compression/Light EMAs seem wrong"**
- These are calculated from actual EMA data at that timestamp
- Check `ema_data_5min.csv` to verify the data
- May indicate data quality issues

**Q: "Bot not converging to my trades"**
- Check if your trades are realistic (is the bot capable of detecting those setups?)
- May need more iterations
- Check if EMA patterns at entry are consistent

## Advanced: Collaborative Trade Input

You can also work with me (Claude) to create trades:

**You:** "I want a LONG entry at 2h30m ago"
**Me:** *Fetches data* "Entry at $3,245.50, ribbon state: all_green, 11 light EMAs, compression 0.14%"
**You:** "Perfect, exit at 1h45m ago"
**Me:** *Fetches exit* "Exit at $3,261.20, PnL: +0.48%"
**You:** "Add it"

This allows you to review technical details before committing each trade.

---

**Ready to create your optimal trades?**

```bash
python3 create_user_optimal_trades.py
```
