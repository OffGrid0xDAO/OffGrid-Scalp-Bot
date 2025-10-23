# 🤖 Self-Learning Crypto Scalping Bot

## 📋 Project Overview

An intelligent crypto scalping bot that learns from optimal trades in historical data and continuously optimizes its parameters to maximize profitability.

### Core Innovation
Instead of manually tuning parameters, the bot:
1. Analyzes historical data to find **optimal trades** (theoretical maximum profit)
2. Backtests strategies and measures **efficiency** vs optimal
3. Learns from **missed opportunities** and adjusts parameters automatically
4. Continuously improves through **iterative optimization**

---

## 🏗️ Project Structure

```
TradingScalper/
├── src/
│   ├── data/              # Data fetching and management
│   ├── indicators/        # Technical indicators (EMAs, RSI, MACD, VWAP, etc.)
│   ├── analysis/          # Optimal trade detection, pattern analysis
│   ├── strategy/          # Trading strategy rules and logic
│   ├── backtest/          # Backtesting engine
│   ├── optimization/      # Parameter optimization algorithms
│   ├── live/              # Live trading execution
│   └── utils/             # Utility functions
│
├── trading_data/          # Historical & live market data
├── charts/                # Generated analysis charts
├── configs/               # Configuration files
│   └── strategy_params.json
├── logs/                  # Trading logs
│
├── tests/                 # Unit tests
│
├── old_implementation/    # Previous version (reference)
│
├── docs/                  # Documentation
│   ├── BOT_ARCHITECTURE_PLAN.md
│   ├── STRATEGY_PLAN.md
│   ├── HYPERLIQUID_INDICATORS.md
│   └── CHART_USAGE.md
│
├── fetch_hyperliquid_history.py  # Data fetcher (working)
├── plot_ema_chart.py             # Chart generator (working)
│
└── README.md
```

---

## 🎯 Key Features

### 1. Pure API-Based (No TradingView Scraping)
- Real-time data from Hyperliquid API
- Reliable and fast
- No browser automation bugs

### 2. Comprehensive Indicators
- 28 EMAs with dynamic colors (green/red based on price)
- RSI (7, 14 periods)
- MACD (multiple settings)
- VWAP (institutional levels)
- Volume analysis
- Bollinger Bands
- EMA slopes & compression

### 3. Optimal Trade Detection
- Finds perfect trades in historical data (hindsight analysis)
- Creates "ground truth" dataset
- Shows theoretical maximum profit
- Identifies common winning patterns

### 4. Confluence-Based Strategy
- 5-point scoring system
- Requires 4/5 indicators agreeing
- Entry only on high-confidence setups
- **Target: 70%+ win rate**

### 5. Systematic Backtesting
- Replay historical market data
- Track all trades and metrics
- Compare vs optimal trades
- Measure efficiency (% of theoretical max captured)

### 6. Auto-Optimization
- Grid search through parameter space
- Genetic algorithms
- Walk-forward testing (prevents overfitting)
- Finds best parameter combinations

### 7. Continuous Learning
- Analyzes missed opportunities
- Suggests parameter adjustments
- Auto-adapts when performance degrades
- Tracks what's working vs not working

---

## 📊 Current Status

### ✅ Completed
- [x] Data fetching from Hyperliquid API
- [x] 28 EMAs with dynamic color calculation
- [x] EMA crossover detection
- [x] Interactive chart visualization
- [x] Complete architecture design
- [x] Strategy planning document
- [x] Project structure setup

### 🔨 In Progress
- [ ] Add RSI, MACD, VWAP indicators
- [ ] Build optimal trades detector
- [ ] Implement strategy engine
- [ ] Create backtesting framework
- [ ] Build optimization engine
- [ ] Implement learning system

---

## 🚀 Quick Start

### 1. Fetch Historical Data
```bash
python3 fetch_hyperliquid_history.py
```

### 2. View Charts
```bash
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv
```

### 3. Run Backtest (Coming Soon)
```bash
python3 -m src.backtest.run --timeframe 5m --days 30
```

### 4. Optimize Parameters (Coming Soon)
```bash
python3 -m src.optimization.optimize --method grid_search
```

### 5. Live Trading (Coming Soon)
```bash
python3 -m src.live.bot --paper-trading
```

---

## 📈 Expected Performance

### After Optimization
- **Win Rate:** 65-75%
- **Efficiency vs Optimal:** 40-60%
- **Sharpe Ratio:** >1.5
- **Max Drawdown:** <12%
- **Monthly Return:** 15-25%

---

## 🛠️ Technology Stack

- **Python 3.12**
- **pandas** - Data manipulation
- **numpy** - Numerical calculations
- **plotly** - Interactive charts
- **hyperliquid-python-sdk** - API access
- **SQLite** - Local database
- **scipy** - Optimization algorithms

---

## 📚 Documentation

See the `docs/` folder for detailed documentation:
- `BOT_ARCHITECTURE_PLAN.md` - Complete system architecture
- `STRATEGY_PLAN.md` - Trading strategy & indicators
- `HYPERLIQUID_INDICATORS.md` - Available indicators guide
- `CHART_USAGE.md` - Chart visualization guide

---

## 🔄 Development Workflow

1. **Data Collection**: Fetch OHLCV from Hyperliquid
2. **Indicator Calculation**: Add all technical indicators
3. **Optimal Trade Detection**: Find best possible trades
4. **Strategy Development**: Define entry/exit rules
5. **Backtesting**: Test on historical data
6. **Optimization**: Find best parameters
7. **Learning**: Analyze and improve
8. **Live Trading**: Deploy optimized strategy

---

## ⚠️ Important Notes

- **Paper trading first!** Always test with paper trading before going live
- **Risk management:** Never risk more than 1% per trade
- **Market conditions:** Strategy works best in trending markets
- **Continuous monitoring:** Check performance daily
- **Adaptation:** Re-optimize monthly or when performance degrades

---

## 🤝 Contributing

This is a personal trading project. The old implementation is in `old_implementation/` for reference.

---

## 📄 License

Private project for personal use.

---

**Built with ❤️ and lots of backtesting**
