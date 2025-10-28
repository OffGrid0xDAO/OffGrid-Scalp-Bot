# Fourier Transform Trading Strategy

A sophisticated algorithmic trading strategy that applies **Fourier Transform signal processing** to price data and technical indicators for noise-free signal generation.

## 🎯 Overview

This strategy combines advanced signal processing with multi-timeframe analysis to filter out market noise and identify high-probability trading opportunities. By applying Fast Fourier Transform (FFT) to price and ALL technical indicators, we extract the underlying market cycles and trends while eliminating random fluctuations.

## ✨ Key Features

### 1. **Fourier Transform Signal Processing**
- Decomposes price and indicators into frequency components
- Filters high-frequency noise while preserving trend signals
- Reconstructs clean signals using dominant harmonics
- Adaptive filtering based on market regime

### 2. **Multi-Timeframe EMA Ribbon Analysis**
- Analyzes EMAs across multiple timeframes (28, 56, 112, 224 periods by default)
- Applies Fourier filtering to each EMA for noise reduction
- Detects EMA alignment for trend confirmation
- Calculates momentum and price distance metrics

### 3. **Fourier-Filtered Technical Indicators**
All indicators are processed through FFT for clean signals:
- **RSI (Relative Strength Index)** - Filtered momentum oscillator
- **MACD** - Filtered MACD line and signal line
- **Volume** - Detects volume cycles and anomalies
- **ATR (Average True Range)** - Volatility cycle detection
- **Stochastic** - Filtered K and D lines
- **Bollinger Band Width** - Volatility expansion/contraction cycles

### 4. **Cross-Indicator Correlation Matrix**
- Calculates correlation between all filtered signals
- Identifies leading/lagging indicators using phase analysis
- Uses spectral coherence to measure frequency-domain relationships
- Generates composite correlation confidence score

### 5. **Advanced Signal Processing**
- **Spectral Coherence**: Frequency-domain correlation
- **Phase Difference Analysis**: Lead/lag relationship detection
- **Dominant Cycle Detection**: Automatic market cycle identification
- **Adaptive Filtering**: Adjusts harmonics based on volatility regime
- **Multi-Resolution Analysis**: Multiple time scale analysis

### 6. **Comprehensive Backtesting**
- Performance metrics (Sharpe ratio, profit factor, win rate)
- Trade-by-trade logging with entry/exit reasons
- Equity curve and drawdown analysis
- Rolling performance metrics
- Commission and slippage simulation

### 7. **Rich Visualization**
- Multi-panel comprehensive analysis charts
- Correlation heatmaps
- Performance summary plots
- Indicator comparison (raw vs filtered)
- Side-by-side strategy comparison

## 📦 Installation

```bash
# Clone the repository
git clone <repository-url>
cd TradingScalper

# Install dependencies
pip install -r requirements_fourier.txt
```

### Dependencies
- numpy >= 1.21.0
- pandas >= 1.3.0
- scipy >= 1.7.0
- matplotlib >= 3.4.0
- seaborn >= 0.11.0
- yfinance >= 0.1.70
- scikit-learn >= 0.24.0

## 🚀 Quick Start

### Basic Usage

```python
from fourier_strategy import FourierTradingStrategy
import yfinance as yf

# Fetch data
df = yf.download('BTC-USD', period='1y', interval='1d')
df.columns = [col.lower() for col in df.columns]

# Initialize strategy
strategy = FourierTradingStrategy()

# Run strategy
results = strategy.run(df, run_backtest=True, verbose=True)

# Print summary
print(strategy.get_summary())

# Visualize
strategy.visualize('comprehensive', save_path='analysis.png')
strategy.visualize('performance', save_path='performance.png')

# Export results
strategy.export_results('results.csv')
```

### Custom Parameters

```python
# Custom signal weights
custom_weights = {
    'price_trend': 0.25,
    'ema_alignment': 0.25,
    'rsi': 0.05,
    'macd': 0.20,
    'volume': 0.10,
    'stochastic': 0.05,
    'correlation': 0.05,
    'phase_momentum': 0.05
}

# Initialize with custom parameters
strategy = FourierTradingStrategy(
    n_harmonics=7,                    # More harmonics
    noise_threshold=0.2,              # Lower threshold
    base_ema_period=21,               # Faster EMA
    correlation_threshold=0.6,
    min_signal_strength=0.4,
    signal_weights=custom_weights
)

results = strategy.run(df, run_backtest=True)
```

### Get Current Signal

```python
# Get the most recent trading signal
current = strategy.get_current_signal()

print(f"Signal Strength: {current['composite_signal']:.3f}")
print(f"Confidence: {current['confidence']:.1f}%")
print(f"Position: {current['position']}")
print(f"Reason: {current['signal_reason']}")
```

## 📊 Examples

### Example 1: Run on Real Data

```bash
python example_fourier_strategy.py
```

This script demonstrates:
- Basic usage with default parameters
- Custom parameter configuration
- Analysis without backtesting
- Multi-ticker comparison

### Example 2: Parameter Optimization

```bash
python optimize_fourier_parameters.py
```

This script performs:
- Grid search over parameter space
- Sensitivity analysis for individual parameters
- 2D heatmap visualization
- Best parameter identification

### Example 3: Compare Fourier vs Traditional

```bash
python compare_fourier_vs_raw.py
```

This script compares:
- Fourier strategy vs traditional indicators
- Side-by-side performance metrics
- Equity curve comparison
- Multi-ticker analysis

## 🏗️ Architecture

### Module Structure

```
fourier_strategy/
├── __init__.py                  # Package initialization
├── fourier_processor.py         # Core FFT filtering
├── multi_timeframe_ema.py       # EMA ribbon analysis
├── fourier_indicators.py        # Technical indicators with FFT
├── correlation_analyzer.py      # Cross-indicator correlation
├── signal_generator.py          # Signal generation logic
├── backtester.py                # Backtesting engine
├── visualizer.py                # Visualization tools
└── strategy.py                  # Main strategy orchestrator
```

### Data Flow

```
OHLCV Data
    ↓
[Fourier Processor] → Filtered Price
    ↓
[Multi-Timeframe EMA] → EMA Alignment & Momentum
    ↓
[Fourier Indicators] → Filtered RSI, MACD, Volume, etc.
    ↓
[Correlation Analyzer] → Cross-indicator relationships
    ↓
[Signal Generator] → Composite Signal & Confidence
    ↓
[Backtester] → Performance Metrics
    ↓
[Visualizer] → Charts & Analysis
```

## 🎛️ Parameters

### Fourier Parameters
- `n_harmonics` (default: 5) - Number of dominant harmonics to keep
- `noise_threshold` (default: 0.3) - Threshold for noise filtering (0-1)

### EMA Parameters
- `base_ema_period` (default: 28) - Base EMA period
- `ema_timeframe_multipliers` (default: [1, 2, 4, 8]) - Timeframe multipliers

### Indicator Parameters
- `rsi_period` (default: 14)
- `macd_fast` (default: 12)
- `macd_slow` (default: 26)
- `macd_signal` (default: 9)
- `atr_period` (default: 14)

### Signal Parameters
- `correlation_threshold` (default: 0.7) - Minimum correlation for confirmation
- `min_signal_strength` (default: 0.5) - Minimum signal to trade
- `signal_weights` - Custom weights for signal components

### Backtest Parameters
- `initial_capital` (default: 10000.0)
- `commission` (default: 0.001) - 0.1% per trade
- `slippage` (default: 0.0005) - 0.05%

## 📈 Signal Generation Logic

### LONG Entry Conditions
1. Fourier filtered price shows upward trend
2. Fourier filtered EMAs are aligned bullish
3. Fourier filtered RSI trending up (not overbought)
4. Fourier filtered MACD shows bullish momentum
5. Fourier filtered volume confirms (above average)
6. High positive correlation (>0.7) between filtered indicators
7. Phase alignment suggests momentum continuation

### SHORT Entry Conditions
1. Fourier filtered price shows downward trend
2. Fourier filtered EMAs are aligned bearish
3. Fourier filtered RSI trending down (not oversold)
4. Fourier filtered MACD shows bearish momentum
5. Fourier filtered volume confirms
6. High correlation or divergence suggesting reversal
7. Phase alignment suggests momentum continuation

### Exit Conditions
- Signal reversal (composite signal crosses zero)
- Confidence drops below 30%
- Individual indicator divergence

## 📊 Output Structure

The strategy returns a comprehensive DataFrame with:

**Raw & Filtered Data:**
- Original OHLCV data
- Filtered price using Fourier
- All raw indicators
- All Fourier-filtered indicators

**EMA Analysis:**
- EMAs at all timeframes (raw and filtered)
- EMA alignment scores
- EMA momentum metrics
- Price distance from EMAs

**Signals:**
- Individual indicator signals
- Composite signal strength (-1 to 1)
- Signal confidence (0-100)
- Position recommendations
- Trade entry/exit signals

**Correlation:**
- Cross-indicator correlation matrix
- Correlation scores
- Leading/lagging indicators
- Spectral coherence measures

**Backtest Results:**
- Equity curve
- Returns
- Trade log with reasons
- Performance metrics

## 🔬 Performance Metrics

The backtester calculates:

- **Total Return** - Cumulative return
- **Annualized Return** - Yearly return rate
- **Sharpe Ratio** - Risk-adjusted return
- **Max Drawdown** - Largest peak-to-trough decline
- **Calmar Ratio** - Return to max drawdown ratio
- **Win Rate** - Percentage of profitable trades
- **Profit Factor** - Gross profit / gross loss
- **Expectancy** - Expected value per trade
- **Number of Trades** - Total trade count
- **Average Holding Period** - Average trade duration

## 🎨 Visualization

### Comprehensive Analysis Plot
Multi-panel chart including:
1. Price (raw + filtered) with entry/exit markers
2. EMA ribbon (filtered)
3. RSI (raw vs filtered)
4. MACD (filtered)
5. Volume (raw vs filtered)
6. Stochastic (filtered)
7. Correlation heatmap
8. Equity curve
9. Signal strength over time

### Performance Summary Plot
1. Equity curve
2. Drawdown chart
3. Returns distribution
4. Metrics summary table

### Comparison Plot (Fourier vs Traditional)
1. Side-by-side equity curves
2. Drawdown comparison
3. Returns distribution
4. Metrics bar chart
5. Cumulative returns
6. Trade count comparison

## 🧪 Testing & Validation

### Synthetic Data Testing
Generate controlled synthetic data with known cycles:

```python
from example_fourier_strategy import generate_synthetic_data

# Generate data with specific cycles
df = generate_synthetic_data(n_points=500)

# Test strategy
strategy = FourierTradingStrategy()
results = strategy.run(df, run_backtest=True)
```

### Parameter Sensitivity Analysis
Test sensitivity to individual parameters:

```python
from optimize_fourier_parameters import ParameterOptimizer

optimizer = ParameterOptimizer(df)

# Test n_harmonics
results = optimizer.sensitivity_analysis(
    param_name='n_harmonics',
    param_values=[3, 5, 7, 9, 11]
)

optimizer.plot_sensitivity(results, 'n_harmonics')
```

### Grid Search Optimization
Find optimal parameter combinations:

```python
param_grid = {
    'n_harmonics': [3, 5, 7],
    'noise_threshold': [0.2, 0.3, 0.4],
    'correlation_threshold': [0.6, 0.7, 0.8]
}

results = optimizer.grid_search(param_grid, metric='sharpe_ratio')
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

1. **Additional Indicators**: Add more Fourier-filtered indicators
2. **Machine Learning**: Integrate ML for parameter optimization
3. **Real-time Trading**: Add live trading integration
4. **Risk Management**: Enhanced position sizing and stop-loss
5. **Multi-asset**: Portfolio-level analysis
6. **Advanced Filters**: Wavelet transforms, Kalman filters

## ⚠️ Disclaimer

This strategy is for **educational and research purposes only**.

- Past performance does not guarantee future results
- Trading involves substantial risk of loss
- This is not financial advice
- Always test thoroughly before live trading
- Use proper risk management
- Never risk more than you can afford to lose

## 📝 License

MIT License - see LICENSE file for details

## 📧 Contact

For questions, issues, or suggestions:
- Open an issue on GitHub
- Submit a pull request
- Contact the development team

## 🙏 Acknowledgments

This strategy builds upon:
- Fourier Transform theory
- Technical analysis principles
- Signal processing techniques
- Quantitative trading research

## 📚 References

1. Fourier Analysis for Time Series
2. Technical Analysis of Financial Markets
3. Signal Processing in Trading
4. Quantitative Trading Strategies

---

**Made with ❤️ for algorithmic traders**

*Last Updated: 2025*
