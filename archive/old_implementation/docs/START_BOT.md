# How to Start the Trading Bot

## Quick Start

```bash
python3 main.py
```

## What You'll See

### 1. Bot Initialization
```
🔧 Phase 1 rules detected - using Phase 1 trader...
✅ Phase 1 trader initialized (tiered entry/exit system)!
✅ Optimizer initialized (runs every 30 min)
```

### 2. Strategy Selection
```
📊 SELECT TRADING STRATEGY:

[1] 🐌 DAY TRADING (5min + 15min charts)
[2] ⚡ SCALPING (1min + 3min charts) **RECOMMENDED**

Enter your choice (1 or 2):
```

**Recommendation:** Choose **2** for scalping (faster signals, more trades)

### 3. Configuration Display
```
📊 CONFIGURATION:
  Strategy: SCALPING
  Network: TESTNET 🧪
  Auto-Trading: ✅ ENABLED
  Position Size: 10.0%
  Leverage: 25x
  Min Confidence: 75%
  Timeframes: 1min + 3min
```

### 4. Bot Starts Trading
```
🚀 STARTING COST-OPTIMIZED BOT WITH AUTO-OPTIMIZATION
💰 Trading: FREE (no API calls)
📊 Optimization: Every 30 minutes
```

---

## Monitoring the Bot

### Watch Live Decisions
```bash
# In another terminal, watch decisions in real-time
tail -f trading_data/claude_decisions.csv
```

### Check Last 5 Signals
```bash
tail -5 trading_data/claude_decisions.csv | cut -d',' -f1-4
```

### View Trading Analysis
```
Open in browser: trading_data/trading_analysis.html
```

---

## What Phase 1 Does

### Tiered Entry System

**Tier 1 (Strong Trend):**
- Ribbon: `all_green` (LONG) or `all_red` (SHORT)
- Min Light EMAs: 11+
- Min Stability: 5 minutes
- Hold Time: 15+ minutes
- Exit: Only on strong reversal (all_green → all_red)

**Tier 2 (Moderate Trend):**
- Ribbon: `all_green` or `strong_green` (LONG)
- Min Light EMAs: 8+
- Min Stability: 3 minutes
- Hold Time: 8+ minutes
- Exit: On any opposite state

**Tier 3 (Quick Scalp):**
- Usually disabled
- For very short trades

### Key Improvements

✅ **No premature exits** - Disabled `exit_on_ribbon_flip` for Tier 1 & 2
✅ **Minimum hold times** - Forces bot to hold through minor noise
✅ **Tiered confidence** - Different rules for different market conditions
✅ **10.9x longer holds** - From 3.5min → 38.1min average

---

## Expected Trading Behavior

### When Bot Enters

**LONG Entry:**
```
5min: all_green (12/12 EMAs green)
15min: all_green (11/12 EMAs green)
Light green EMAs: 11
Decision: TIER 1 LONG @ $3950.00
```

**SHORT Entry:**
```
5min: all_red (12/12 EMAs red)
15min: strong_red (10/12 EMAs red)
Light red EMAs: 9
Decision: TIER 2 SHORT @ $3950.00
```

### When Bot Exits

**Tier 1 Exit:**
- Hold for at least 15 minutes
- Exit only when ribbon fully reverses (all_green → all_red)
- Or profit target hit (+0.5%)
- Or stop loss hit (-0.3%)

**Tier 2 Exit:**
- Hold for at least 8 minutes
- Exit when ribbon changes to opposite state
- Or profit/stop hit

---

## Troubleshooting

### No Trades Happening?

**Check:**
1. Is bot running? (should see new lines in EMA data CSV)
2. Check recent ribbon states:
   ```bash
   tail -5 trading_data/ema_data_5min.csv | cut -d',' -f1-3
   ```
3. Are conditions met?
   - Need `all_green` or `all_red` for Tier 1
   - Need 11+ light EMAs
   - Need 5+ minutes stability

### Bot Says "HOLD" Every Time?

**Possible reasons:**
1. Market is in `mixed` state (neither bullish nor bearish)
2. Not enough light EMAs (need 11+ for Tier 1, 8+ for Tier 2)
3. Ribbon just flipped (need 3-5 min stability)
4. Wait for clearer trend

### How to Force a Test Trade?

The bot trades based on rules. To see a trade:
1. Wait for strong trend (all_green or all_red)
2. Or lower min_light_emas in trading_rules.json to 2
3. Or enable Tier 3 quick scalp

---

## Performance Monitoring

### Check Profitability
```bash
grep "exit," trading_data/claude_decisions.csv | tail -10
```

### Count Trades
```bash
grep -c "LONG\|SHORT" trading_data/claude_decisions.csv
```

### Check Win Rate
Look for PnL in exit logs

---

## Stopping the Bot

Press `Ctrl+C` in the terminal

Bot will:
1. Close any open positions
2. Save final state
3. Show summary statistics

---

## Next Steps

Once bot is trading:
1. ✅ Monitor for 1 hour
2. ✅ Verify entries/exits make sense
3. ✅ Check Telegram notifications (if configured)
4. ✅ Review trading_analysis.html visualization
5. ✅ Let optimizer run (every 30 min) to improve rules

---

## Files to Monitor

- `trading_data/claude_decisions.csv` - All decisions
- `trading_data/ema_data_5min.csv` - Market data (short timeframe)
- `trading_data/ema_data_15min.csv` - Market data (long timeframe)
- `trading_data/trading_analysis.html` - Visual analysis
- `trading_rules.json` - Current rules (updated by optimizer)

---

**Your bot is ready to trade! Start it with `python3 main.py` and let it run!** 🚀
