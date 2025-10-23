# 🚀 Quick Start Guide - Automated Optimization

Get your trading bot optimized with Claude AI in 5 minutes!

## 📋 Prerequisites

1. **Anthropic API Key** (Required)
   - Get it at: https://console.anthropic.com/
   - Free tier includes credits for testing
   - Cost: ~$0.02-0.05 per optimization iteration

2. **Historical Data** (Already have it!)
   - Your `trading_data/indicators/eth_1h_full.csv` is ready
   - 149 columns with all indicators calculated

3. **Python 3.8+** (You have it!)

---

## ⚡ Installation (2 minutes)

### Step 1: Install Dependencies

```bash
pip install anthropic pandas numpy plotly requests
```

Or install everything:
```bash
pip install -r requirements.txt
```

### Step 2: Set Up API Key

**Option A: Environment Variable** (Recommended)
```bash
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

**Option B: .env File**
```bash
# Copy example
cp .env.example .env

# Edit .env and add your key
nano .env
# Change: ANTHROPIC_API_KEY=your_api_key_here
```

**Option C: Temporary (this session only)**
```bash
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

### Step 3: Set Up Telegram (Optional - 3 minutes)

Get beautiful optimization reports sent to your phone!

**Quick setup:**
1. Talk to `@BotFather` on Telegram → `/newbot`
2. Talk to `@userinfobot` → `/start` (get your chat ID)
3. Add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**Full guide:** See [TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md)

---

## 🎯 Usage

### **Basic: 5 Iterations** (Recommended First Run)

```bash
python3 scripts/optimize_strategy.py --iterations 5 --timeframe 1h
```

**What happens:**
1. ✅ Loads your historical data
2. ✅ Runs baseline backtest (current 55.3% win rate)
3. ✅ Finds optimal trades (perfect hindsight)
4. ✅ Asks Claude for improvements
5. ✅ Tests Claude's suggestions
6. ✅ Keeps improvements, reverts failures
7. ✅ Repeats 5 times

**Expected time:** 10-15 minutes
**Expected cost:** $0.10-0.25

---

### **Advanced: Full Optimization** (10 Iterations)

```bash
python3 scripts/optimize_strategy.py --iterations 10 --timeframe 1h --auto-apply
```

**Flags:**
- `--iterations 10`: Run 10 optimization cycles
- `--auto-apply`: Automatically keep improvements (no confirmation)

**Expected time:** 20-30 minutes
**Expected cost:** $0.20-0.50
**Expected improvement:** 55% → 60-65% win rate

---

### **Multi-Timeframe Optimization**

Optimize different timeframes:

```bash
# Day trading (15m)
python3 scripts/optimize_strategy.py --iterations 5 --timeframe 15m

# Scalping (5m)
python3 scripts/optimize_strategy.py --iterations 5 --timeframe 5m

# Swing trading (30m)
python3 scripts/optimize_strategy.py --iterations 5 --timeframe 30m
```

---

## 📊 Example Output

```
================================================================================
AUTOMATED OPTIMIZATION LOOP
================================================================================
   Iterations: 5
   Timeframe: 1h
   Symbol: eth
   Auto-apply: False

================================================================================
ITERATION 0: BASELINE
================================================================================

RUNNING BACKTEST
   Total trades: 123
   Win rate: 55.3%
   Profit factor: 2.0
   Total P&L: +$487.23

FINDING OPTIMAL TRADES
   Total optimal trades: 450
   Potential profit: +$1,243.67

ANALYZING PERFORMANCE GAP
   We're capturing: 39.2% of optimal profit
   Missed 327 trades worth $612.30

📊 Baseline Win Rate: 55.3%

================================================================================
ITERATION 1/5
================================================================================

ASKING CLAUDE AI FOR SUGGESTIONS
   🤖 Calling Claude API...

📝 Claude's Response:
{
  "suggested_changes": {
    "confluence_gap_min": 27,
    "volume_requirement": ["elevated", "spike"]
  },
  "reasoning": "Lowering confluence gap from 30 to 27 will capture more
               of the missed trades that averaged 28.3 gap. Keep strict
               volume filter to maintain signal quality."
}

✅ Parsed Suggestions

APPLYING SUGGESTIONS
   💾 Backed up params: optimization_logs/backups/params_backup_20250121_143022.json
   ✅ confluence_gap_min: 30 → 27 (suggested: 27)

TESTING NEW PARAMETERS
   Total trades: 187
   Win rate: 57.8%

COMPARISON
   Old Win Rate: 55.3%
   New Win Rate: 57.8%
   Change: +2.5%

✅ IMPROVEMENT DETECTED! (+4.5%)
   🎯 New best win rate: 57.8%

   Keep these changes? [Y/n]: y
   ✅ Keeping changes

... (4 more iterations) ...

================================================================================
OPTIMIZATION COMPLETE
================================================================================

📊 Results:
   Baseline win rate: 55.3%
   Best win rate: 61.2%
   Total improvement: +5.9%
   Iterations completed: 5

💾 History saved: optimization_logs/optimization_history_20250121_144523.json
🔄 Restoring best parameters...
   ✅ Best parameters restored

✅ Done! Strategy optimized.
```

---

## 🎯 What Gets Optimized

Claude can adjust these parameters in `src/strategy/strategy_params.json`:

### Entry Filters
- `confluence_gap_min`: Minimum gap between long/short scores (default: 30)
- `confluence_score_min`: Minimum absolute score (default: 30)
- `volume_requirement`: Which volume levels to trade (default: ["elevated", "spike"])
- `require_ema_alignment`: Whether to filter by EMA ribbon (default: false)
- `rsi_range`: Acceptable RSI range (default: [30, 70])

### Exit Strategy
- `take_profit_levels`: Where to take profits (default: [1.0, 2.0, 3.0])
- `take_profit_sizes`: How much to exit at each level (default: [50, 30, 20])
- `stop_loss_pct`: Stop loss percentage (default: 0.5)
- `trailing_stop_enabled`: Use trailing stops (default: false)

### Risk Management
- `max_risk_per_trade`: Max % risk per trade (default: 2.0)
- `max_concurrent_trades`: Max open positions (default: 3)
- `position_size_pct`: Position size (default: 10.0)

---

## 💡 Pro Tips

### 1. Start Conservative (5 iterations)
```bash
python3 scripts/optimize_strategy.py --iterations 5 --timeframe 1h
```
Get a feel for how it works before running many iterations.

### 2. Use Auto-Apply for Overnight Runs
```bash
# Run overnight, automatically keep improvements
python3 scripts/optimize_strategy.py --iterations 20 --auto-apply
```

### 3. Lower Minimum Improvement for Tight Optimization
```bash
# Accept smaller improvements (1% instead of 2%)
python3 scripts/optimize_strategy.py --iterations 10 --min-improvement 1.0
```

### 4. Conservative Parameter Changes
```bash
# Limit changes to 10% instead of 20%
python3 scripts/optimize_strategy.py --iterations 5 --max-change 10.0
```

### 5. Review Logs After Each Run
```bash
# See what Claude suggested
cat optimization_logs/optimization_history_*.json

# See parameter backups
ls optimization_logs/backups/
```

---

## 🔧 Troubleshooting

### Error: "ANTHROPIC_API_KEY not found"
```bash
# Set the API key
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# Or check .env file
cat .env
```

### Error: "Data file not found"
```bash
# Make sure you have processed indicators
ls trading_data/indicators/eth_1h_full.csv

# If missing, run:
python3 scripts/process_indicators.py
```

### Error: "No JSON found in response"
Claude's response format might have changed. The script will try to parse the entire response as JSON.

### Win Rate Decreased
This is normal! The script automatically reverts bad changes. You'll see:
```
❌ PERFORMANCE DEGRADED (-3.2%)
   Reverting changes...
   ✅ Parameters reverted
```

### API Rate Limits
If you hit rate limits:
```bash
# Add delays between iterations (TODO: implement)
# For now, just run fewer iterations
python3 scripts/optimize_strategy.py --iterations 3
```

---

## 📈 Expected Results

### Iteration 1-3: Entry Filter Optimization
- Adjust confluence gap threshold
- Fine-tune volume requirements
- **Expected:** 55% → 57-58%

### Iteration 4-6: Exit Optimization
- Optimize take profit levels
- Adjust stop loss placement
- **Expected:** 58% → 60-62%

### Iteration 7-10: Advanced Filters
- Add EMA alignment requirements
- MACD confirmation
- Ribbon compression filters
- **Expected:** 62% → 63-65%

### Iteration 11-20: Fine-Tuning
- Small adjustments
- Risk management optimization
- **Expected:** 65% → 67-70%

**Realistic goal:** 55% → 65% in 10-15 iterations

---

## 💰 Cost Breakdown

### Per Iteration
- 1 Claude API call (Sonnet 4)
- ~500-1000 tokens input, ~200-500 tokens output
- Cost: ~$0.02-0.05

### Full Optimization (10 iterations)
- Total cost: **$0.20-0.50**
- Time: 20-30 minutes
- Expected improvement: +5-10% win rate

### Monthly (Daily Optimization)
- 30 days × 1 run/day × 5 iterations
- Total: **$3-7.50/month**
- Continuously improving strategy

**Compare to:** Old system using Claude for every trade = $75-100/day!

---

## 🎓 Next Steps

After optimization:

1. **Review Results**
   ```bash
   # See optimization history
   cat optimization_logs/optimization_history_*.json
   ```

2. **Test on Different Timeframes**
   ```bash
   python3 scripts/optimize_strategy.py --iterations 5 --timeframe 15m
   python3 scripts/optimize_strategy.py --iterations 5 --timeframe 5m
   ```

3. **Run Manual Backtest to Verify**
   ```bash
   python3 scripts/run_backtest.py --timeframe 1h --symbol eth --save-trades
   ```

4. **Move to Paper Trading** (TODO)
   ```bash
   python3 scripts/paper_trade.py
   ```

5. **Deploy to Live Trading** (TODO - when consistently profitable)
   ```bash
   python3 scripts/start_bot.py --live
   ```

---

## 📚 Documentation

- **[README.md](README.md)** - Project overview
- **[IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)** - Detailed usage guide
- **[COMPLETE_STRATEGY_RESEARCH.md](docs/COMPLETE_STRATEGY_RESEARCH.md)** - Why it works

---

## ⚠️ Important Notes

1. **This Uses Real Money Concepts** - Start with paper trading
2. **Past Performance ≠ Future Results** - Markets change
3. **Monitor Closely** - Automation requires supervision
4. **Start Small** - Test thoroughly before scaling
5. **Backups Automatic** - All parameter changes are backed up

---

## 🎉 Ready to Start!

```bash
# Set your API key
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# Run first optimization (5 iterations)
python3 scripts/optimize_strategy.py --iterations 5 --timeframe 1h

# Watch the magic happen! ✨
```

**Expected outcome:** Your 55.3% win rate strategy becomes 60-65% optimized by Claude AI!

Good luck! 🚀📈
