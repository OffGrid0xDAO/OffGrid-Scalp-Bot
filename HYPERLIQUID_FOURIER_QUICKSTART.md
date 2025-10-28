# Fourier Strategy with Hyperliquid - Quick Start

This guide shows how to run the Fourier Transform trading strategy with data fetched directly from Hyperliquid.

## 🚀 Quick Commands

### 1. Install Dependencies

```bash
cd /Users/0x0010110/Documents/GitHub/TradingScalper
pip install -r requirements_fourier.txt
```

### 2. Run Complete Pipeline (RECOMMENDED)

This fetches data from Hyperliquid, runs backtests, generates visualizations, and uses Claude AI to analyze results:

```bash
python run_fourier_with_hyperliquid.py
```

**What this does:**
- ✅ Fetches 90 days of 1-hour OHLCV data from Hyperliquid
- ✅ Runs 4 different parameter configurations
- ✅ Performs complete backtesting for each
- ✅ Generates comprehensive charts and visualizations
- ✅ Uses Claude AI to analyze performance and suggest improvements
- ✅ Saves all results to `trading_data/fourier_iterations/`

**Output:**
```
trading_data/fourier_iterations/
├── iteration_01/
│   ├── results.csv              # Complete data with indicators and signals
│   ├── analysis.png            # Multi-panel comprehensive analysis
│   ├── performance.png         # Performance metrics and equity curve
│   └── metadata.json           # Parameters and metrics
├── iteration_02/
│   └── ...
├── iteration_03/
│   └── ...
├── iteration_04/
│   └── ...
├── optimization_summary.csv     # Comparison of all iterations
├── iterations_log.json          # Complete log
└── claude_analysis_*.md         # AI-generated insights
```

---

### 3. Customize Settings

Edit environment variables or run with custom parameters:

```bash
# Set symbol and timeframe
export SYMBOL=BTC
export INTERVAL=1h
export DAYS_BACK=180

python run_fourier_with_hyperliquid.py
```

Or modify directly in the script for more control.

---

### 4. Test Single Configuration (Quick Test)

Create a simple test script:

```python
# test_fourier_hyperliquid.py
from fourier_strategy import FourierTradingStrategy
from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter

# Fetch data
adapter = HyperliquidDataAdapter(symbol='ETH')
df = adapter.fetch_ohlcv(interval='1h', days_back=60)

# Run strategy with backtest
strategy = FourierTradingStrategy()
results = strategy.run(df, run_backtest=True, verbose=True)

# Print results
print(strategy.get_summary())

# Save outputs
strategy.export_results('test_results.csv')
strategy.visualize('comprehensive', save_path='test_analysis.png')
```

Run it:
```bash
python test_fourier_hyperliquid.py
```

---

## 📊 What Gets Backtested

The backtest includes:

### Performance Metrics
- **Total Return** - Cumulative profit/loss
- **Sharpe Ratio** - Risk-adjusted returns
- **Max Drawdown** - Largest peak-to-trough decline
- **Win Rate** - Percentage of profitable trades
- **Profit Factor** - Gross profit / gross loss
- **Number of Trades** - Total trades executed

### Trade Details
- Entry/exit timestamps
- Entry/exit prices
- P&L per trade
- Holding period
- Signal reasons

### Risk Metrics
- Calmar Ratio
- Annualized return
- Volatility
- Expectancy per trade

---

## 📈 Visualizations Generated

### 1. Comprehensive Analysis Chart (analysis.png)

Multi-panel chart with:
- **Panel 1**: Price (raw vs Fourier-filtered) with trade markers
- **Panel 2**: Multi-timeframe EMA ribbon (Fourier-filtered)
- **Panel 3**: RSI (raw vs filtered)
- **Panel 4**: MACD (filtered)
- **Panel 5**: Volume (raw vs filtered)
- **Panel 6**: Stochastic (filtered)
- **Panel 7**: Correlation heatmap of all indicators
- **Panel 8**: Equity curve with drawdown
- **Panel 9**: Signal strength over time

### 2. Performance Summary (performance.png)

- Equity curve
- Drawdown chart
- Returns distribution
- Key metrics table

---

## 🤖 Claude AI Analysis

The system uses Claude AI to:

1. **Analyze Performance**: Evaluate which parameter configurations work best
2. **Identify Patterns**: Find what makes successful trades
3. **Suggest Improvements**: Recommend specific parameter changes
4. **Risk Assessment**: Identify potential risks and issues

Example Claude analysis output:
```markdown
# Performance Assessment

Iteration 2 shows the best risk-adjusted returns with a Sharpe ratio of 2.45.

# Best Parameters

- n_harmonics: 7 (captures more market cycles)
- noise_threshold: 0.2 (less aggressive filtering)
- correlation_threshold: 0.6 (more signals)

# Recommended Next Tests

1. Try n_harmonics: 9 with noise_threshold: 0.25
2. Test base_ema_period: 25 (slightly faster than 28)
3. Increase min_signal_strength to 0.55 for quality

# Key Insights

Higher harmonics (7-9) perform better in trending markets...
```

---

## 🎛️ Parameter Configurations Tested

The default optimization tests these configurations:

### Configuration 1: Baseline
```python
{
    'n_harmonics': 5,
    'noise_threshold': 0.3,
    'base_ema_period': 28,
    'correlation_threshold': 0.7,
    'min_signal_strength': 0.5
}
```

### Configuration 2: Aggressive
```python
{
    'n_harmonics': 7,
    'noise_threshold': 0.2,
    'base_ema_period': 21,
    'correlation_threshold': 0.6,
    'min_signal_strength': 0.4
}
```

### Configuration 3: Conservative
```python
{
    'n_harmonics': 3,
    'noise_threshold': 0.4,
    'base_ema_period': 35,
    'correlation_threshold': 0.8,
    'min_signal_strength': 0.6
}
```

### Configuration 4: High Harmonics
```python
{
    'n_harmonics': 9,
    'noise_threshold': 0.25,
    'base_ema_period': 28,
    'correlation_threshold': 0.7,
    'min_signal_strength': 0.5
}
```

---

## 📂 Output Files Explained

### results.csv
Complete DataFrame with:
- Raw OHLCV data
- All Fourier-filtered indicators
- EMA ribbons (raw and filtered)
- Signal strengths
- Trade signals
- Equity curve
- Returns

### metadata.json
```json
{
  "iteration_name": "iteration_01",
  "timestamp": "2025-01-28T10:30:00",
  "symbol": "ETH",
  "parameters": {...},
  "metrics": {
    "total_return_pct": 45.23,
    "sharpe_ratio": 2.15,
    "max_drawdown_pct": -12.34,
    "win_rate_pct": 65.5,
    "profit_factor": 1.85,
    "num_trades": 42
  }
}
```

### optimization_summary.csv
Comparison table of all iterations:
```
Iteration    Return (%)  Sharpe  Max DD (%)  Win Rate (%)  Profit Factor  Trades
iteration_01      45.23    2.15      -12.34         65.50           1.85      42
iteration_02      52.18    2.45       -9.87         68.20           2.10      38
iteration_03      38.90    1.95      -15.20         62.10           1.65      35
iteration_04      48.76    2.30      -11.05         66.80           1.92      40
```

---

## 🔧 Troubleshooting

### No data fetched
```bash
# Check Hyperliquid connection
python -c "
from src.data.hyperliquid_fetcher import HyperliquidFetcher
fetcher = HyperliquidFetcher(symbol='ETH')
candles = fetcher.fetch_candles('1h',
    start_time=1704067200000,  # Jan 1, 2024
    end_time=1704153600000)     # Jan 2, 2024
print(f'Fetched {len(candles)} candles')
"
```

### Claude API not working
```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Or check .env file
cat .env | grep ANTHROPIC_API_KEY
```

### Import errors
```bash
# Make sure you're in the right directory
pwd  # Should be /Users/0x0010110/Documents/GitHub/TradingScalper

# Install dependencies
pip install -r requirements_fourier.txt
pip install anthropic
```

---

## 📊 Reading Backtest Results

### Good Performance Indicators:
- ✅ Sharpe Ratio > 2.0
- ✅ Win Rate > 60%
- ✅ Profit Factor > 1.5
- ✅ Max Drawdown < 15%
- ✅ Positive total return

### Warning Signs:
- ⚠️ Sharpe Ratio < 1.0
- ⚠️ Win Rate < 50%
- ⚠️ Profit Factor < 1.2
- ⚠️ Max Drawdown > 25%
- ⚠️ Too many trades (>100) or too few (<10)

---

## 🎯 Next Steps After Backtesting

1. **Review Best Configuration**
   - Check `optimization_summary.csv` for best Sharpe ratio
   - Review corresponding visualizations

2. **Read Claude's Analysis**
   - Open `claude_analysis_*.md`
   - Follow recommended parameter changes

3. **Test Recommendations**
   - Modify parameters based on Claude's suggestions
   - Run another optimization cycle

4. **Paper Trade**
   - Test best configuration with paper trading
   - Monitor for 1-2 weeks

5. **Go Live**
   - Deploy to production with small position size
   - Monitor and adjust

---

## 💡 Tips

1. **Start with 60-90 days** of data for backtesting
2. **Use 1h or 4h timeframes** for better signal quality
3. **Run optimization on weekends** when you can review results
4. **Always paper trade first** before live trading
5. **Monitor correlation scores** - low correlation = weak signals
6. **Check signal confidence** - only trade high confidence (>50%)

---

## 📞 Need Help?

Check the main documentation:
- `FOURIER_STRATEGY_README.md` - Complete strategy documentation
- `FOURIER_QUICKSTART.md` - Basic usage guide

---

**Ready to start? Run this:**

```bash
python run_fourier_with_hyperliquid.py
```

🚀 **Happy Trading!**
