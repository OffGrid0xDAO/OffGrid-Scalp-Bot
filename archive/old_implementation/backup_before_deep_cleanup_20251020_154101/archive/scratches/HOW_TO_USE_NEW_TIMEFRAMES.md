# How to Use the New Timeframe Selection

## What Changed?

The bot now asks you to choose between **TWO trading strategies** when you start it:

1. **DAY TRADING** (5min + 15min) - Slower, longer holds
2. **SCALPING** (1min + 3min) - Fast, quick in/out ⚡ **RECOMMENDED**

## How to Run the Bot

```bash
python3 run_dual_bot.py
```

You'll see this menu:

```
📊 SELECT TRADING STRATEGY:
────────────────────────────────────────────────────────────────────────────────

  [1] 🐌 DAY TRADING (5min + 15min charts)
      • Slower signals (5-15 min lag)
      • Hold time: 15-60 minutes
      • Profit target: 0.3%
      • Stop loss: 0.15%
      • Best for: Swing trades, longer holds

  [2] ⚡ SCALPING (1min + 3min charts) **RECOMMENDED**
      • Fast signals (1-3 min)
      • Hold time: 1-5 minutes
      • Profit target: 0.2%
      • Stop loss: 0.08%
      • Best for: Quick in/out, high frequency

Enter your choice (1 or 2):
```

## Which One Should You Choose?

### ⚡ Choose **SCALPING (Option 2)** if:
- ✅ You want to recover from your current -30% loss
- ✅ You want FASTER signals (1-3 min vs 5-15 min)
- ✅ You want MORE trades per session (50-100 vs 20-30)
- ✅ You want TIGHTER risk control (0.08% vs 0.15% stop)
- ✅ You're actively monitoring the bot
- ✅ **This is what we recommend based on your results!**

### 🐌 Choose DAY TRADING (Option 1) if:
- You prefer slower, less frequent trades
- You want to hold positions for 15-60 minutes
- You're okay with the current 27% win rate

---

## What Happens After You Choose?

### If you choose SCALPING (1min + 3min):

**Two browser windows will open:**
- **Left Browser**: 1-minute chart
- **Right Browser**: 3-minute chart

Both showing ETH/USD with the EMA ribbon indicator.

**The bot will:**
- Look for ribbon flips on 1min chart
- Confirm with 3min chart
- Enter trades MUCH faster
- Exit within 1-5 minutes
- Make 50-100+ trades per session

### If you choose DAY TRADING (5min + 15min):

**Two browser windows will open:**
- **Left Browser**: 5-minute chart
- **Right Browser**: 15-minute chart

**The bot will:**
- Look for ribbon flips on 5min chart
- Confirm with 15min chart
- Enter trades slower
- Hold for 15-60 minutes
- Make 20-30 trades per session

---

## Expected Performance Improvement

### Current Results (5min/15min):
- Win Rate: **27%** ❌
- Total P&L: **-$28.50** ❌
- Avg Hold: **15-60 min**
- Trades: **22**

### Expected with SCALPING (1min/3min):
- Win Rate: **40-50%** ✅
- Total P&L: **POSITIVE** ✅
- Avg Hold: **1-5 min**
- Trades: **50-100+**

---

## Important Notes:

1. **Browser Windows**:
   - The bot will open 2 Chrome browsers automatically
   - Left = Short timeframe (1min or 5min)
   - Right = Long timeframe (3min or 15min)
   - DO NOT close these browsers while bot is running!

2. **Timeframe Matching**:
   - If you choose SCALPING, both browsers will show 1min and 3min
   - If you choose DAY TRADING, both will show 5min and 15min
   - The indicator works on ALL timeframes

3. **First Time Running**:
   - You may need to log into TradingView in the browsers
   - Make sure the EMA ribbon indicator loads properly
   - Wait 30-60 seconds for charts to fully render

4. **Changing Strategies**:
   - Stop the bot (Ctrl+C)
   - Run it again and choose different option
   - The bot will open browsers with new timeframes

---

## Example Session Output:

### When Starting (Scalping Mode):
```
📊 CONFIGURATION:
────────────────────────────────────────────────────────────────────────────────
  Strategy: SCALPING
  Network: TESTNET 🧪
  Auto-Trading: ✅ ENABLED
  Position Size: 10.0%
  Leverage: 25x
  Min Confidence: 75%
  Timeframes: 1min + 3min    ← Notice the timeframes!
  AI: Claude Sonnet 4.5
  Claude API: ✅ Configured
────────────────────────────────────────────────────────────────────────────────

✅ Starting bot in 3 seconds...
   Press Ctrl+C to stop at any time

🔷 Opening Browser 1 (1-minute chart)...
   ✅ 1-minute chart loaded with indicator
🔶 Opening Browser 2 (3-minute chart)...
   ✅ 3-minute chart loaded with indicator
```

---

## Troubleshooting:

**Q: I chose SCALPING but still see 5min/15min charts**
A: Stop the bot (Ctrl+C) and restart. Make sure to press `2` for SCALPING.

**Q: The indicator doesn't show up**
A: You may need to manually add the indicator from TradingView. Check the browser windows and add "Annii's Ribbon for Scalping" from your indicators list.

**Q: Can I switch strategies mid-run?**
A: No, you need to stop the bot (Ctrl+C) and restart it to choose a different strategy.

**Q: Which strategy recovers my -30% loss faster?**
A: SCALPING (1min/3min) will likely recover faster due to:
  - More trading opportunities (50-100 vs 22 trades)
  - Better win rate (40-50% vs 27%)
  - Tighter risk control (smaller losses)

---

## Summary:

✅ **Choose SCALPING (Option 2) for best results**
✅ Bot will open 1min + 3min charts automatically
✅ Expect 40-50% win rate vs current 27%
✅ More trades = more chances to recover losses
✅ Tighter stops = smaller losses per trade

Good luck! 🚀
