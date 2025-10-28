# Fourier Strategy Optimization Guide 🤖

Complete guide for using Claude AI to continuously improve the Fourier trading strategy through iterative optimization.

---

## 🎯 Overview

The Fourier optimization system uses Claude AI to analyze strategy performance and suggest parameter improvements in a continuous feedback loop:

```
┌─────────────────────────────────────────────────┐
│  1. Run Strategy → Get Results                  │
│  2. Analyze Performance → Generate Charts       │
│  3. Ask Claude AI → Get Suggestions             │
│  4. Apply Changes → Validate Improvement        │
│  5. Repeat → Strategy Gets Better!              │
└─────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

### 1. Install Required Packages

```bash
pip install anthropic
```

### 2. Set Up Anthropic API Key

Get your API key from [Anthropic Console](https://console.anthropic.com)

```bash
# Set environment variable
export ANTHROPIC_API_KEY='your-api-key-here'

# Or add to .env file
echo "ANTHROPIC_API_KEY=your-api-key-here" >> .env
```

### 3. Verify Setup

```bash
# Check API key is set
python -c "import os; print('✅ API key set!' if os.environ.get('ANTHROPIC_API_KEY') else '❌ API key not set')"
```

---

## 🚀 Quick Start

### Run Automatic Optimization (Recommended)

This runs N iterations automatically, with Claude analyzing and improving after each one:

```bash
# Run 10 iterations (default)
python run_fourier_optimization_loop.py

# Run custom number of iterations
python run_fourier_optimization_loop.py --iterations 20

# Custom symbol and capital
python run_fourier_optimization_loop.py --iterations 15 --symbol BTC --capital 50000

# More historical data
python run_fourier_optimization_loop.py --iterations 10 --days 100
```

**What it does:**
1. Fetches 50 days of ETH data (configurable)
2. Runs Fourier strategy with current parameters
3. Generates interactive chart with TP/SL zones
4. Sends results to Claude for analysis
5. Gets parameter suggestions back
6. Applies suggestions (with safety limits)
7. Repeats for N iterations

---

## 📊 Manual Optimization (Step-by-Step)

If you want more control, run iterations manually:

### Step 1: Run One Iteration

```bash
python fourier_iterative_optimizer.py
```

This will:
- Run the strategy
- Generate charts
- Print Claude analysis prompt
- Save results to `trading_data/fourier_iterations/iteration_XX/`

### Step 2: Analyze with Claude

Copy the generated prompt and paste it into [Claude.ai](https://claude.ai) or use the API directly.

### Step 3: Apply Suggestions

Edit the parameters in `fourier_iterative_optimizer.py`:

```python
self.current_params = {
    'n_harmonics': 7,  # Changed from 5
    'noise_threshold': 0.25,  # Changed from 0.3
    # ... apply other suggestions
}
```

### Step 4: Run Next Iteration

```bash
python fourier_iterative_optimizer.py
```

---

## 📁 Output Structure

Each iteration creates a directory with complete results:

```
trading_data/fourier_iterations/
├── iteration_01/
│   ├── metadata.json          # Parameters & metrics
│   ├── results.csv            # Full price data with indicators
│   ├── trade_log.csv          # All trades with entry/exit
│   └── charts/
│       └── ETH_1h_3way_comparison.html  # Interactive chart
├── iteration_02/
│   └── ...
├── iterations_log.json         # All iterations history
└── optimization_summary.csv    # Quick comparison table
```

---

## 📈 Understanding the Results

### Metrics to Track

| Metric | What It Means | Good Value |
|--------|---------------|------------|
| **Total Return** | Profit/loss over period | > 5% |
| **Sharpe Ratio** | Risk-adjusted returns | > 1.0 |
| **Max Drawdown** | Largest peak-to-trough drop | < -10% |
| **Win Rate** | % of profitable trades | > 60% |
| **Profit Factor** | Gross profit / gross loss | > 2.0 |
| **# Trades** | Total trades taken | 5-15 for 50 days |

### Parameter Effects

| Parameter | Low Value → High Value |
|-----------|------------------------|
| **n_harmonics** (3-11) | More responsive ↔ Smoother (more lag) |
| **noise_threshold** (0.1-0.5) | Keep more signal ↔ Filter more noise |
| **base_ema_period** (14-50) | Short-term ↔ Long-term trends |
| **correlation_threshold** (0.5-0.9) | More trades ↔ Higher quality trades |
| **min_signal_strength** (0.2-0.8) | More entries ↔ Stronger signals only |
| **max_holding_periods** (24-336) | Quick exits ↔ Let winners run |

---

## 🎨 Viewing Charts

Charts are saved as interactive HTML files with:

✅ **Price candlesticks** with Bollinger Bands & VWAP
✅ **Entry/Exit markers** clearly visible on top
✅ **TP/SL zones** with green (profit) and red (loss) rectangles
✅ **RSI & Stochastic** indicators
✅ **Volume analysis** with color coding
✅ **Confluence scores** for long/short

Open any chart:

```bash
# Open latest iteration
open trading_data/fourier_iterations/iteration_01/charts/ETH_1h_3way_comparison.html

# Or from Python
python -c "import webbrowser; webbrowser.open('trading_data/fourier_iterations/iteration_01/charts/ETH_1h_3way_comparison.html')"
```

---

## 🔧 Advanced Usage

### Compare All Iterations

```python
from fourier_iterative_optimizer import FourierIterativeOptimizer

optimizer = FourierIterativeOptimizer()
comparison = optimizer.compare_iterations(n=10)  # Last 10
print(comparison)
```

### Export Best Parameters

```bash
# Find best iteration by Sharpe ratio
python -c "
import json
from pathlib import Path

log = json.load(open('trading_data/fourier_iterations/iterations_log.json'))
best = max(log, key=lambda x: x['metrics'].get('sharpe_ratio', -999))

print(f\"Best Iteration: {best['iteration_name']}\")
print(f\"Sharpe Ratio: {best['metrics']['sharpe_ratio']:.3f}\")
print(f\"Parameters: {json.dumps(best['parameters'], indent=2)}\")
"
```

### Resume from Specific Iteration

Edit the optimizer to start from a specific set of parameters:

```python
# In fourier_iterative_optimizer.py
self.current_params = {
    # Copy parameters from best iteration
}
```

---

## 🛡️ Safety Features

### Parameter Change Limits

The system automatically limits parameter changes to **30% per iteration** to prevent:
- Extreme jumps that break the strategy
- Overfitting to recent data
- Unstable parameter combinations

### Validation

Each suggested change is:
1. ✅ Validated to be within allowed ranges
2. ✅ Limited to max 30% change from current value
3. ✅ Logged for review
4. ✅ Tested before being applied

---

## 📝 Example Workflow

### Full Optimization Session

```bash
# 1. Set API key
export ANTHROPIC_API_KEY='your-key'

# 2. Run 15 iterations
python run_fourier_optimization_loop.py --iterations 15 --days 50

# 3. Wait for completion (takes ~30-45 minutes)
# The script will:
#   - Run iteration
#   - Ask Claude for improvements
#   - Apply suggestions
#   - Repeat

# 4. Review results
cat trading_data/fourier_iterations/optimization_summary.csv

# 5. View best iteration chart
# (Check the summary for best iteration number)
open trading_data/fourier_iterations/iteration_XX/charts/ETH_1h_3way_comparison.html

# 6. Use best parameters for live trading
# Copy parameters from best iteration's metadata.json
```

---

## 🎯 Optimization Strategies

### Strategy 1: Quick Optimization (10 iterations)

Good for testing and rapid feedback:

```bash
python run_fourier_optimization_loop.py --iterations 10 --days 30
```

### Strategy 2: Deep Optimization (20-30 iterations)

For thorough parameter tuning:

```bash
python run_fourier_optimization_loop.py --iterations 30 --days 50
```

### Strategy 3: Robustness Testing (50+ iterations)

Test across different market conditions:

```bash
# Run multiple optimization sessions with different data periods
python run_fourier_optimization_loop.py --iterations 20 --days 30
python run_fourier_optimization_loop.py --iterations 20 --days 60
python run_fourier_optimization_loop.py --iterations 20 --days 90
```

---

## 🐛 Troubleshooting

### Issue: "ANTHROPIC_API_KEY not set"

**Solution:**
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### Issue: "anthropic package not installed"

**Solution:**
```bash
pip install anthropic
```

### Issue: Charts not showing TP/SL zones

**Solution:**
Make sure you're using the latest visualize_fourier_trades.py. The zones should appear as semi-transparent green (TP) and red (SL) rectangles.

### Issue: Too many/too few trades

**Solution:**
Adjust `min_signal_strength` and `correlation_threshold`:
- **More trades:** Lower both parameters
- **Fewer trades:** Raise both parameters

### Issue: Strategy holding too long

**Solution:**
Reduce `max_holding_periods` (default: 168 hours = 7 days):
```python
'max_holding_periods': 72  # 3 days instead of 7
```

---

## 📚 Next Steps

After optimization:

1. ✅ **Review best iteration** - Check charts and metrics
2. ✅ **Validate on different periods** - Test on new data
3. ✅ **Paper trade** - Test with small amounts first
4. ✅ **Monitor live performance** - Track vs backtest
5. ✅ **Re-optimize monthly** - Markets change over time

---

## 💡 Pro Tips

1. **Run overnight** - Let it optimize while you sleep
2. **Save good parameters** - Copy metadata.json from best iterations
3. **Compare across symbols** - Try BTC, SOL, etc.
4. **Watch for overfitting** - Best iteration should be stable, not random
5. **Use longer periods** - 50+ days gives more reliable results
6. **Track Sharpe, not returns** - Risk-adjusted performance matters most

---

## 🤝 Need Help?

- Check `iterations_log.json` for full history
- Review `optimization_summary.csv` for quick comparison
- Look at `metadata.json` in each iteration folder
- Compare charts visually to see what changed

---

## 🎉 Happy Optimizing!

Remember: The goal is **consistent risk-adjusted returns**, not just high returns. Watch Sharpe ratio and max drawdown carefully!

**Target Metrics:**
- Sharpe Ratio: > 1.5
- Max Drawdown: < -8%
- Win Rate: > 65%
- Profit Factor: > 2.5
