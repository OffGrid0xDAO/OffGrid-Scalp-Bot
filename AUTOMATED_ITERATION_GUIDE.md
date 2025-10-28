# 🤖 AUTOMATED BACKTEST ITERATION WITH CLAUDE

## What This Does

Continuously improves your trading strategy by:
1. ✅ Running backtest with current parameters
2. 🧠 Claude analyzes the results
3. 💡 Claude suggests specific parameter improvements
4. 🔄 Script applies recommendations automatically
5. ✅ Runs new backtest with improved parameters
6. 🔁 Repeats until targets achieved

**FULLY AUTOMATED** - Claude iteratively optimizes your strategy!

---

## 🚀 Quick Start

### Goal: Increase Returns from 1.77% to 5-7% While Keeping Sharpe >8

```bash
# Run 10 iterations targeting Sharpe 10+ and Return 6%
python iterate_backtest.py --iterations 10 --target-sharpe 10.0 --target-return 6.0
```

That's it! The script will:
- Start with current parameters (90/90/65)
- Run backtest → Ask Claude → Apply improvements → Repeat
- Stop when targets achieved or max iterations reached
- Save all results and recommendations

---

## 📋 Usage

### Basic Usage:

```bash
python iterate_backtest.py
```

Default targets:
- Sharpe: 12.0
- Return: 5.0%
- Max Iterations: 10

### Custom Targets:

```bash
# Target: Sharpe 8.0, Return 7.0%
python iterate_backtest.py --target-sharpe 8.0 --target-return 7.0
```

### More Iterations:

```bash
# Run up to 20 iterations
python iterate_backtest.py --iterations 20 --target-sharpe 10.0 --target-return 8.0
```

### Custom Starting Parameters:

```bash
# Start from specific parameters
python iterate_backtest.py --start-params my_params.json
```

Where `my_params.json` contains:
```json
{
  "compression_threshold": 85,
  "alignment_threshold": 85,
  "confluence_threshold": 60,
  "n_harmonics": 5,
  "max_holding_periods": 24
}
```

---

## 📊 What Happens During Iteration

### Iteration 1:

```
🚀 STARTING AUTOMATED BACKTEST ITERATION
================================================
Target: Sharpe 10.0, Return 6.0%
Max Iterations: 10
================================================

############################################################
# ITERATION 1/10
############################################################

RUNNING BACKTEST - Iteration 1
================================================
Parameters:
{
  "compression_threshold": 90,
  "alignment_threshold": 90,
  "confluence_threshold": 65,
  "n_harmonics": 5,
  "max_holding_periods": 24
}

✅ Backtest completed!
Return: 1.77%
Sharpe: 10.13
Win Rate: 86.7%
Trades: 15

ANALYZING WITH CLAUDE - Iteration 1
================================================
Requesting Claude analysis...
✅ Claude analysis complete
Saved to: iteration_results/iteration_1_recommendations.md

APPLYING RECOMMENDATIONS
================================================
Before:
{
  "compression_threshold": 90,
  "alignment_threshold": 90,
  "confluence_threshold": 65
}
  compression_threshold: 90 → 85
  alignment_threshold: 90 → 85
  confluence_threshold: 65 → 60

After:
{
  "compression_threshold": 85,
  "alignment_threshold": 85,
  "confluence_threshold": 60
}
```

### Iteration 2:

```
############################################################
# ITERATION 2/10
############################################################

RUNNING BACKTEST - Iteration 2
================================================
...
Return: 3.45%
Sharpe: 9.21
Win Rate: 83.3%
Trades: 32

🏆 NEW BEST ITERATION! Sharpe: 9.21, Return: 3.45%
```

### Continue Until Target Reached:

```
############################################################
# ITERATION 7/10
############################################################

RUNNING BACKTEST - Iteration 7
================================================
Return: 6.12%
Sharpe: 10.35
Win Rate: 81.5%
Trades: 48

🏆 NEW BEST ITERATION! Sharpe: 10.35, Return: 6.12%

🎉 TARGET ACHIEVED!
Sharpe: 10.35 (target: 10.0)
Return: 6.12% (target: 6.0%)
```

---

## 📈 Example: Full Iteration Run

Let's say you want to optimize from current 1.77% to 6% returns:

```bash
python iterate_backtest.py --iterations 15 --target-sharpe 9.0 --target-return 6.0
```

**Typical progression:**

| Iteration | Params (C/A/C) | Sharpe | Return | Trades | Status |
|-----------|----------------|--------|--------|--------|--------|
| 1 | 90/90/65 | 10.13 | 1.77% | 15 | Starting point |
| 2 | 85/85/60 | 9.21 | 3.45% | 32 | Improvement! |
| 3 | 83/83/58 | 8.95 | 4.12% | 41 | Getting closer |
| 4 | 82/82/57 | 8.76 | 4.78% | 48 | Almost there |
| 5 | 80/82/56 | 9.02 | 5.34% | 52 | Better balance |
| 6 | 81/83/57 | 9.15 | 5.89% | 47 | Very close! |
| 7 | 81/83/58 | 9.23 | 6.05% | 46 | 🎉 TARGET! |

**Result**: Found optimal parameters in 7 iterations!

---

## 🧠 What Claude Analyzes

For each iteration, Claude examines:

### 1. Performance Metrics:
- Sharpe ratio vs target
- Return vs target
- Win rate
- Max drawdown
- Profit factor
- Number of trades

### 2. Comparison to Previous:
- Did metrics improve?
- Are we moving toward target?
- What changed?

### 3. Pattern Recognition:
- If Sharpe too high but returns low → Relax thresholds
- If returns good but Sharpe low → Tighten risk management
- If both off target → Suggest specific adjustments

### 4. Specific Recommendations:
```json
{
  "compression_threshold": 85,
  "alignment_threshold": 85,
  "confluence_threshold": 60,
  "n_harmonics": 5,
  "max_holding_periods": 24
}
```

### 5. Expected Impact:
- "These changes should increase trades by 2x"
- "Expect Sharpe to decrease slightly to 9.0"
- "Return should increase to ~3.5%"

---

## 📁 Output Files

After running, you'll find:

```
iteration_results/
├── iteration_1.json                      # Full iteration 1 data
├── iteration_1_prompt.md                 # Prompt sent to Claude
├── iteration_1_recommendations.md        # Claude's analysis
├── iteration_2.json
├── iteration_2_prompt.md
├── iteration_2_recommendations.md
├── ...
└── iteration_summary.json                # Summary of all iterations
```

### iteration_summary.json:

```json
{
  "timestamp": "2025-10-28T20:30:00",
  "target_sharpe": 10.0,
  "target_return": 6.0,
  "best_iteration": 7,
  "best_sharpe": 9.23,
  "best_return": 6.05,
  "iterations": [...],
  "final_params": {
    "compression_threshold": 81,
    "alignment_threshold": 83,
    "confluence_threshold": 58,
    "n_harmonics": 5,
    "max_holding_periods": 24
  }
}
```

---

## 🎯 Recommended Targets

### Conservative (Safety First):

```bash
python iterate_backtest.py --target-sharpe 12.0 --target-return 4.0
```
- Prioritize high Sharpe (ultra-safe)
- Moderate returns

### Balanced (Recommended):

```bash
python iterate_backtest.py --target-sharpe 9.0 --target-return 6.0
```
- Excellent Sharpe (TOP 1%)
- Good returns

### Aggressive (Higher Returns):

```bash
python iterate_backtest.py --target-sharpe 7.0 --target-return 8.0
```
- Still great Sharpe (better than most hedge funds)
- High returns

### Very Aggressive:

```bash
python iterate_backtest.py --target-sharpe 5.0 --target-return 10.0
```
- Good Sharpe
- Very high returns
- Higher risk

---

## ⚙️ Requirements

### Environment Setup:

1. **Anthropic API Key** (Required):
```bash
# Add to .env file
ANTHROPIC_API_KEY=your_key_here
```

2. **Historical Data**:
- Script will fetch from your existing data sources
- Requires data files in `data/` directory

3. **Dependencies**:
```bash
pip install anthropic python-dotenv
```

---

## 🔧 Advanced Usage

### Resume From Best Iteration:

If iteration stops early, resume from best parameters:

```bash
# Find best params in iteration_results/iteration_summary.json
# Copy final_params to custom_params.json
python iterate_backtest.py --start-params custom_params.json
```

### Manual Review Mode:

Want to review Claude's recommendations before applying?

Edit the script to add a confirmation prompt:

```python
# In apply_recommendations()
response = input("Apply these recommendations? (yes/no): ")
if response.lower() != 'yes':
    return False
```

### Different Optimization Strategies:

Edit targets during iterations:

```python
# Prioritize Sharpe first
python iterate_backtest.py --target-sharpe 12.0 --target-return 3.0

# Once Sharpe achieved, focus on returns
python iterate_backtest.py --target-sharpe 10.0 --target-return 7.0
```

---

## 📊 Understanding Results

### Good Iteration:

```
Iteration 5: Sharpe 9.21, Return 4.45%, Trades 42
```
- Sharpe >9 (excellent)
- Return >4% (good)
- Trades ~40 (healthy frequency)

### Warning Signs:

```
Iteration 3: Sharpe 3.21, Return 8.45%, Trades 125
```
- Sharpe <5 (too low)
- Too many trades (over-trading)
- High risk

### Perfect Balance:

```
Iteration 7: Sharpe 9.50, Return 6.12%, Trades 48
```
- High Sharpe (safe)
- Good returns
- Reasonable trade frequency

---

## 🚨 Troubleshooting

### "ANTHROPIC_API_KEY not set"

**Fix**: Add to `.env` file:
```env
ANTHROPIC_API_KEY=sk-ant-...
```

### "Backtest failed"

**Possible causes**:
- Missing data files
- Import errors
- Invalid parameters

**Fix**: Check logs, verify data files exist

### "Could not extract parameters"

Claude's response format unexpected.

**Fix**: Check `iteration_X_recommendations.md` manually, apply parameters yourself

### Iterations Not Improving

Hit local optimum.

**Fix**:
- Try different starting parameters
- Adjust target values
- Run more iterations

---

## 💡 Pro Tips

### 1. Start Conservative

Begin with tight parameters, let Claude relax them:
```bash
python iterate_backtest.py --start-params conservative_params.json
```

### 2. Monitor Progress

Watch the iteration_summary.json file:
```bash
# In another terminal
watch -n 5 cat iteration_results/iteration_summary.json
```

### 3. Multiple Runs

Run with different targets, compare results:
```bash
# Run 1: Safety focus
python iterate_backtest.py --target-sharpe 12.0 --target-return 4.0

# Run 2: Return focus
python iterate_backtest.py --target-sharpe 8.0 --target-return 7.0

# Compare results
```

### 4. Save Best Parameters

After finding optimal parameters:
```bash
# Copy from iteration_summary.json to config_live.json
# Use for live trading
```

---

## 🎉 Example Success Story

**Starting Point**:
- Sharpe: 10.13
- Return: 1.77%
- Trades: 15
- Problem: Too conservative

**After 8 Iterations**:
- Sharpe: 9.42
- Return: 6.21%
- Trades: 47
- Solution: Perfect balance!

**Improvement**:
- Return increased 3.5x
- Sharpe still exceptional (TOP 0.5%)
- Trade frequency healthy
- Ready for live trading

---

## 🚀 Ready to Iterate?

```bash
# START NOW - Find optimal parameters!
python iterate_backtest.py --iterations 15 --target-sharpe 9.0 --target-return 6.0
```

Let Claude optimize your strategy automatically! 🤖

---

*Created: October 28, 2025*
*Automated iteration with Claude Sonnet 4*
