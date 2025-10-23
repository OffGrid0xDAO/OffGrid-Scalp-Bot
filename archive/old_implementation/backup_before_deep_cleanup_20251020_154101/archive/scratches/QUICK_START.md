# 🚀 Quick Start - Cost Optimization System

## Problem Solved
You were spending **$50-100/day** on Claude API calls. This new system reduces costs to **$0.20-1.00/day** (99% savings!).

---

## How It Works

### Before (Expensive 💸):
```
Your Bot → Claude API (every trade) → Decision
Cost: ~4,320 calls/day = $50-100/day
```

### After (Cheap ✅):
```
Scheduler → Claude API (every 30min) → Updates Rules
Your Bot → Reads Rules (NO API) → Fast Decision
Cost: ~48 calls/day = $0.20-1.00/day
```

---

## Installation (2 minutes)

### 1. Install Dependencies
```bash
pip3 install schedule
```
(You already have anthropic and pandas)

### 2. Set API Key
```bash
export ANTHROPIC_API_KEY='your-anthropic-api-key-here'
```

### 3. Test the System
```bash
# Run comprehensive tests
python3 test_cost_optimization.py
```

All tests should pass! ✅

---

## Running the System

### Option A: Test One Optimization Cycle First
```bash
# This calls Claude ONCE to optimize rules (~$0.02)
python3 rule_optimizer.py
```

You'll see:
- Optimal trades from last 30min analyzed
- Claude's recommendations
- Updated trading rules
- Cost of the API call

### Option B: Start the Scheduler (Production)
```bash
# This runs optimizer every 30 minutes automatically
python3 run_optimizer_schedule.py
```

Keep this running in background (screen/tmux/systemd).

---

## Integrate into Your Trading Bot

### Replace Your Current Code:

**OLD (Expensive):**
```python
from claude_trader import ClaudeTrader

trader = ClaudeTrader()
decision = trader.get_decision(...)  # Costs money every time!
```

**NEW (FREE):**
```python
from rule_based_trader import RuleBasedTrader

trader = RuleBasedTrader()  # Loads optimized rules
decision = trader.get_trade_decision(
    indicators_5min=your_5min_indicators,
    indicators_15min=your_15min_indicators,
    current_price=current_price,
    current_position=None  # or your current position dict
)

# Use the decision
if decision['entry_recommended']:
    print(f"ENTER {decision['direction']} at ${decision['entry_price']}")
    # Execute your trade...

if decision['exit_recommended']:
    print(f"EXIT: {decision['exit_reason']}")
    # Close your position...
```

---

## What You Get

### Every 30 Minutes (Automatically):
1. ✅ System analyzes last 30min of trades
2. ✅ Identifies winning EMA patterns
3. ✅ Claude optimizes trading rules
4. ✅ Rules saved to `trading_rules.json`
5. ✅ Your bot automatically uses new rules

### Between Cycles (FREE):
- Your bot makes fast decisions using optimized rules
- NO API calls
- NO costs
- Decisions in milliseconds

---

## Files Created

| File | What It Does |
|------|-------------|
| `rule_based_trader.py` | Your new trader (NO API calls) |
| `rule_optimizer.py` | Calls Claude every 30min |
| `run_optimizer_schedule.py` | Runs optimizer automatically |
| `optimal_trade_finder_30min.py` | Finds best trades from data |
| `trading_rules.json` | Your optimized trading rules |
| `test_cost_optimization.py` | Test everything works |
| `COST_OPTIMIZATION_GUIDE.md` | Full documentation |

---

## Monitoring

### View Current Rules:
```bash
cat trading_rules.json | grep -A 10 "claude_insights"
```

### View Optimal Trades Analysis:
```bash
cat trading_data/optimal_trades_last_30min.json
```

### Check Scheduler:
The scheduler prints detailed output showing:
- Win rate from last 30min
- Claude's key findings
- Rule adjustments made
- Cost per cycle

---

## Expected Costs

### Daily:
- **48 API calls** (1 every 30 minutes)
- **~$0.20-$1.00** total cost
- **98.9% savings** vs before

### Monthly:
- **~1,440 API calls**
- **~$6-$30** total cost
- **~$1,500-$2,970 saved**

### Annual:
- **~17,520 API calls**
- **~$72-$360** total cost
- **~$18,000-$35,000 saved** 🎉

---

## Troubleshooting

### "No data in last 30 minutes"
Wait for your bot to collect some trading data first (15-30 minutes).

### Rules not updating
1. Check scheduler is running
2. Check API key is set correctly
3. View scheduler output for errors

### Still seeing high costs
Make sure you're using `rule_based_trader.py` NOT `claude_trader.py` in your main bot!

---

## Next Steps

1. ✅ Run `python3 test_cost_optimization.py`
2. ✅ Run `python3 rule_optimizer.py` (test one cycle)
3. ✅ Start scheduler: `python3 run_optimizer_schedule.py`
4. ✅ Update your bot to use `RuleBasedTrader`
5. ✅ Monitor costs for 24 hours
6. ✅ Celebrate massive savings! 🎉

---

## Support

- Full docs: `COST_OPTIMIZATION_GUIDE.md`
- Test suite: `python3 test_cost_optimization.py`
- Your data: `trading_data/optimal_trades_last_30min.json`

**Happy Trading! 📈💰**
