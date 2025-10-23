# Trading Bot Quick Start Guide

**Last Updated:** October 20, 2025

---

## 🚀 START THE BOT (One Command)

```bash
python3 main.py
```

**Then choose:** `2` for SCALPING (recommended)

---

## ✅ WHAT HAPPENS NEXT

### With Historical Data (You Have This!)

```
T+0 sec:   🚀 Bot starts and detects historical data
T+5 sec:   📊 IMMEDIATE optimization begins (analyzes ALL history)
T+30 sec:  📱 Telegram message with 3-way performance analysis
T+60 sec:  ✅ Bot starts trading with optimized rules!

Then every 30 minutes:
           🔄 Optimization cycle
           📱 Telegram update
           📊 Chart image
```

### What You'll See in Console

```
🔧 Phase 1 rules detected - using Phase 1 trader...
✅ Phase 1 trader initialized (tiered entry/exit system)!
✅ Optimizer initialized (runs every 30 min)

🚀 STARTING COST-OPTIMIZED BOT WITH AUTO-OPTIMIZATION
💰 Trading: FREE (no API calls)
📊 Optimization: Every 30 minutes

🤖 Optimization scheduler started
   Running every 30 minutes

📊 Historical data detected - running IMMEDIATE first optimization!
   This will analyze ALL available training data

[5 seconds later...]

🔄 AUTOMATIC OPTIMIZATION CYCLE STARTING
⏰ Time: 2025-10-20 21:30:00
📊 Cycle #1

[Analysis happens...]

📱 Sending optimization update to Telegram...
✅ Telegram message sent!
📊 Sending optimization chart...
✅ Chart sent!

✅ First optimization complete using historical data!
⏰ Next optimization in 30 minutes
```

---

## 📱 TELEGRAM MESSAGES YOU'LL GET

### Message 1: Performance Analysis (Every 30 min)

```
🔧 OPTIMIZATION CYCLE COMPLETE 🔧

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 3-WAY PERFORMANCE COMPARISON

🥇 OPTIMAL TRADES (Perfect Hindsight)
├ Trades: 37
├ PnL: +29.89%
├ Avg Hold: 33.0min
├ Avg Compression: 0.15%
└ Avg Light EMAs: 18

🥈 BACKTEST TRADES (Current Rules)
├ Trades: 28
├ PnL: +2.61%
├ Avg Hold: 38.1min
├ Win Rate: 60.7%
├ Avg Compression: 0.10%
└ Avg Light EMAs: 15

🥉 ACTUAL TRADES (Live Execution)
├ Trades: 5
├ PnL: +0.80%
├ Avg Hold: 42.3min
└ Win Rate: 80.0%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 GAP ANALYSIS
...

🔍 KEY FINDINGS
...

🛠️ RULE IMPROVEMENTS PLANNED
...

💰 API Cost: $0.0234
⏰ 2025-10-20 21:30:15
🔄 Next optimization in 30 minutes
```

### Message 2: Visual Chart

4-panel comparison chart showing:
- Total trades
- Total PnL
- Avg PnL per trade
- Win rate

---

## 📊 CURRENT MARKET CONDITIONS

Based on latest EMA data (20:49):
- **Ribbon:** ALL_GREEN ✅ (28/28 light EMAs)
- **Price:** $3,984
- **Condition:** Perfect for Tier 1 LONG

**Expected behavior:** Bot should enter TIER 1 LONG within 30-60 seconds!

---

## 🎯 PHASE 1 TRADING RULES

### Tier 1 (Strong Trend)
- **Entry:** all_green/all_red + 11+ light EMAs + 5min stability
- **Hold:** 15+ minutes minimum
- **Exit:** Only on profit target (+1.2%), stop loss (-0.6%), or strong reversal
- **Strategy:** Aggressive - hold through minor reversals

### Tier 2 (Moderate Trend)
- **Entry:** strong_green/strong_red + 8+ light EMAs + 3min stability
- **Hold:** 8+ minutes minimum
- **Exit:** Profit target (+0.8%), stop loss (-0.5%), or opposite state
- **Strategy:** Moderate holds

### Tier 3 (Quick Scalp)
- **Status:** DISABLED (too risky for current conditions)

---

## 📁 IMPORTANT FILES

### Documentation (All in `docs/`)
- `QUICK_START.md` - This file
- `START_BOT.md` - Detailed startup instructions
- `FIRST_RUN_OPTIMIZATION.md` - How first optimization works
- `OPTIMIZATION_TELEGRAM_PLAN.md` - Complete optimization details
- `COMPREHENSIVE_ANALYSIS_AND_ACTION_PLAN.md` - Full codebase analysis
- `BOT_NOT_TRADING_DIAGNOSIS.md` - Troubleshooting guide

### Code Files
- `main.py` - Entry point (start here!)
- `dual_timeframe_bot_with_optimizer.py` - Main bot with optimizer
- `rule_based_trader_phase1.py` - Phase 1 tiered trading logic
- `rule_optimizer.py` - 30-minute optimization engine
- `telegram_notifier.py` - Telegram message formatting

### Data Files
- `trading_rules.json` - Current Phase 1 rules
- `trading_data/ema_data_5min.csv` - Market data (updated every 10sec)
- `trading_data/claude_decisions.csv` - All trading decisions
- `trading_data/optimal_trades.json` - Perfect hindsight trades

---

## 🛠️ TROUBLESHOOTING

### Bot Won't Start

**Error:** `'RuleBasedTraderPhase1' object has no attribute 'get_cost_summary'`
- **Status:** ✅ FIXED
- **Solution:** Added all compatibility methods

**Error:** `KeyError: 'session_cost_usd'`
- **Status:** ✅ FIXED
- **Solution:** Updated cost summary dict

### No Trades Happening

**Check:**
1. Is bot showing EMA data updates? (Check console)
2. Is bot making decisions? (Check `trading_data/claude_decisions.csv`)
3. Current market conditions meet entry criteria?

**Quick Test:**
```bash
# Check if bot is recording data (should see recent timestamps)
tail -5 trading_data/ema_data_5min.csv

# Check last trading decision (should be recent)
tail -1 trading_data/claude_decisions.csv
```

### No Telegram Messages

**Check:**
1. `.env` file has `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
2. Bot console shows: "✅ Telegram notifications enabled"
3. Not: "⚠️  Telegram notifications disabled"

**Quick Test:**
```python
python3 << EOF
from telegram_notifier import TelegramNotifier
telegram = TelegramNotifier()
if telegram.enabled:
    telegram.send_message("🤖 Test message!")
    print("✅ Message sent!")
else:
    print("❌ Telegram not configured - check .env file")
EOF
```

---

## 🎮 MONITORING THE BOT

### Watch Live Decisions
```bash
tail -f trading_data/claude_decisions.csv
```

### Check Last 5 Signals
```bash
tail -5 trading_data/claude_decisions.csv | cut -d',' -f1-4
```

### View Trading Analysis
```bash
open trading_data/trading_analysis.html
# Or just open in browser: file:///path/to/trading_data/trading_analysis.html
```

### Check Bot Status
```bash
ps aux | grep "python.*main.py"
```

---

## 🛑 STOPPING THE BOT

**Press:** `Ctrl+C` in the terminal

The bot will:
1. Close any open positions
2. Save final state
3. Show summary statistics
4. Stop gracefully

---

## 📊 WHAT TO EXPECT

### First Hour
- ✅ Immediate optimization (if historical data exists)
- ✅ Telegram message within 30 seconds
- ✅ Bot starts trading with optimized rules
- ✅ First trades within minutes (if market conditions right)

### After First Hour
- 🔄 Optimization every 30 minutes
- 📱 Telegram updates every 30 minutes
- 📊 Rules continuously improve
- 💰 All for FREE (no API calls for trading)

### Expected Performance (Phase 1 Backtest)
- **Trades:** 28 trades in test period
- **PnL:** +2.61%
- **Avg Hold:** 38.1 minutes
- **Win Rate:** 60.7%
- **Improvement:** 10.9x longer holds vs old rules

---

## 🎯 SUCCESS INDICATORS

### Bot is Working If:
- [x] New EMA data every 10 seconds
- [x] New decisions every 30-60 seconds
- [x] Telegram messages every 30 minutes
- [x] Trades being executed when conditions met
- [x] No errors in console

---

## 🆘 NEED HELP?

### Check These Docs:
1. `docs/START_BOT.md` - Detailed startup guide
2. `docs/BOT_NOT_TRADING_DIAGNOSIS.md` - Why no trades?
3. `docs/COMPREHENSIVE_ANALYSIS_AND_ACTION_PLAN.md` - Full analysis

### Common Issues:
- **Bot not trading:** See `BOT_NOT_TRADING_DIAGNOSIS.md`
- **API errors:** Check `.env` file configuration
- **No Telegram:** Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

---

## 🚀 READY TO GO!

Your bot is configured and ready to trade. Just run:

```bash
python3 main.py
```

Choose `2` for SCALPING, and watch the magic happen! 🎉

---

**All documentation now organized in `docs/` folder!** 📁
