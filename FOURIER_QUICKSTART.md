# Fourier Strategy - Quick Start Guide

## 📥 Installation

```bash
# 1. Navigate to the project directory
cd /Users/0x0010110/Documents/GitHub/TradingScalper

# 2. Install required dependencies
pip install -r requirements_fourier.txt
```

## 🚀 Running the Strategy

### Option 1: Basic Example (Recommended for First Run)

```bash
# Run the basic example with BTC-USD data
python example_fourier_strategy.py
```

This will:
- Fetch 1 year of BTC-USD data
- Run the Fourier strategy with default parameters
- Generate backtest results and performance metrics
- Create visualization plots
- Export results to CSV

**Output files:**
- `fourier_strategy_results.csv` - Complete results DataFrame
- `fourier_strategy_analysis.png` - Comprehensive analysis chart
- `fourier_strategy_performance.png` - Performance summary

---

### Option 2: Custom Interactive Usage

Create a Python script or use Python REPL:

```python
# Start Python
python

# Then run:
from fourier_strategy import FourierTradingStrategy
import yfinance as yf

# Fetch your preferred data
df = yf.download('BTC-USD', period='1y', interval='1d')
df.columns = [col.lower() for col in df.columns]

# Run strategy
strategy = FourierTradingStrategy()
results = strategy.run(df, run_backtest=True, verbose=True)

# Get summary
print(strategy.get_summary())

# Get current signal
signal = strategy.get_current_signal()
print(f"Current Signal: {signal['composite_signal']:.2f}")
print(f"Confidence: {signal['confidence']:.1f}%")

# Visualize
strategy.visualize('comprehensive', save_path='my_analysis.png')

# Export
strategy.export_results('my_results.csv')
```

---

### Option 3: Parameter Optimization

```bash
# Run parameter optimization (grid search + sensitivity analysis)
python optimize_fourier_parameters.py
```

This will:
- Test multiple parameter combinations
- Perform sensitivity analysis
- Generate optimization plots
- Save best parameters to CSV

**Output files:**
- `fourier_grid_search_results.csv` - All tested combinations
- `sensitivity_*.png` - Sensitivity analysis plots

---

### Option 4: Compare Fourier vs Traditional Strategy

```bash
# Compare Fourier strategy with traditional indicators
python compare_fourier_vs_raw.py
```

This will:
- Run both Fourier and traditional strategies
- Compare performance metrics
- Generate side-by-side comparison charts
- Test on multiple tickers

**Output files:**
- `fourier_vs_traditional_comparison.png` - Comparison charts
- `multi_ticker_comparison.csv` - Multi-asset results

---

## 🎯 Customization Examples

### Example 1: Different Asset

```python
python -c "
from fourier_strategy import FourierTradingStrategy
import yfinance as yf

# Try ETH instead of BTC
df = yf.download('ETH-USD', period='6mo', interval='1d')
df.columns = [col.lower() for col in df.columns]

strategy = FourierTradingStrategy()
results = strategy.run(df, run_backtest=True)
print(strategy.get_summary())
"
```

### Example 2: Shorter Timeframe (Intraday)

```python
python -c "
from fourier_strategy import FourierTradingStrategy
import yfinance as yf

# 1-hour data for day trading
df = yf.download('SPY', period='1mo', interval='1h')
df.columns = [col.lower() for col in df.columns]

strategy = FourierTradingStrategy(
    base_ema_period=21,  # Faster for intraday
    min_signal_strength=0.4
)
results = strategy.run(df, run_backtest=True)
print(strategy.get_summary())
"
```

### Example 3: Custom Parameters

```python
python -c "
from fourier_strategy import FourierTradingStrategy
import yfinance as yf

df = yf.download('BTC-USD', period='1y', interval='1d')
df.columns = [col.lower() for col in df.columns]

strategy = FourierTradingStrategy(
    n_harmonics=7,              # More detail
    noise_threshold=0.2,        # Less filtering
    correlation_threshold=0.6,  # Lower threshold
    min_signal_strength=0.4     # More signals
)

results = strategy.run(df, run_backtest=True)
print(strategy.get_summary())
"
```

---

## 📊 Understanding the Output

### Console Output

When you run the strategy, you'll see:

```
======================================================================
FOURIER TRADING STRATEGY - PROCESSING
======================================================================

[1/7] Applying Fourier Transform to price...
[2/7] Analyzing Multi-Timeframe EMAs with Fourier...
[3/7] Processing Technical Indicators with Fourier...
[4/7] Analyzing Cross-Indicator Correlations...
[5/7] Generating Trading Signals...
[6/7] Running Backtest...

╔══════════════════════════════════════════════════════════════╗
║            FOURIER STRATEGY BACKTEST RESULTS                 ║
╚══════════════════════════════════════════════════════════════╝

PERFORMANCE METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Initial Capital:        $10,000.00
Final Capital:          $15,234.56
Total Return:           52.35%
Annualized Return:      45.23%
...
```

### CSV Output

The CSV file contains all data including:
- Raw and filtered prices
- All indicators (raw and filtered)
- EMA alignment scores
- Signal strength and confidence
- Trade signals
- Equity curve

### Visualization Output

PNG files with multi-panel charts showing:
- Price with trade markers
- EMA ribbons
- Indicators (RSI, MACD, Volume, etc.)
- Correlation heatmap
- Equity curve
- Performance metrics

---

## 🔧 Troubleshooting

### Issue: ModuleNotFoundError

```bash
# Make sure you installed dependencies
pip install -r requirements_fourier.txt

# Or install individually
pip install numpy pandas scipy matplotlib seaborn yfinance scikit-learn
```

### Issue: No data fetched

```bash
# Check internet connection
# Try different ticker or period
# Example with guaranteed data:
python -c "
import yfinance as yf
df = yf.download('SPY', period='1mo', interval='1d')
print(df.head())
"
```

### Issue: Import errors

```bash
# Make sure you're in the correct directory
cd /Users/0x0010110/Documents/GitHub/TradingScalper

# Check Python path
python -c "import sys; print(sys.path)"

# Run from correct location
python example_fourier_strategy.py
```

---

## 📈 Next Steps

1. **Start Simple**: Run `example_fourier_strategy.py` first
2. **Understand Output**: Read the generated CSV and look at visualizations
3. **Experiment**: Try different assets and timeframes
4. **Optimize**: Run `optimize_fourier_parameters.py` to find best settings
5. **Compare**: Run `compare_fourier_vs_raw.py` to see Fourier benefits
6. **Customize**: Modify parameters for your trading style

---

## 💡 Pro Tips

1. **Start with longer timeframes** (1d) before trying intraday
2. **Use at least 6 months of data** for reliable backtests
3. **Compare multiple assets** to validate strategy robustness
4. **Optimize on training data, test on validation data**
5. **Always check the correlation_score** - low correlation means weak signals
6. **Monitor signal_confidence** - only trade high confidence signals (>50%)

---

## 📞 Need Help?

Check the main README: `FOURIER_STRATEGY_README.md`

Common questions:
- How does Fourier filtering work? → See README "Architecture" section
- What do the parameters mean? → See README "Parameters" section
- How to interpret signals? → See README "Signal Generation Logic" section

---

**Happy Trading! 🚀**
