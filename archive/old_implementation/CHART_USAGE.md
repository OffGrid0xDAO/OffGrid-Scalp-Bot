# Chart Visualization Guide

## 📊 Quick Start

### 1. Fetch Historical Data
```bash
python3 fetch_hyperliquid_history.py
```

This fetches:
- ✅ 1m, 3m, 5m, 15m timeframes
- ✅ Last 30 days of data
- ✅ All 28 EMAs calculated
- ✅ EMA colors (green/red vs price)
- ✅ EMA crossover detection
- ✅ Full OHLCV data

### 2. Create Charts
```bash
# Fast EMAs (5, 10, 20) - last 500 candles
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas fast --window 500

# Medium EMAs (20, 50, 100)
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas medium --window 300

# Custom EMAs
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas 5,10,20,50,100,145 --window 200

# All 28 EMAs (warning: very busy chart!)
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas all --window 100

# All data (no window limit)
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas fast

# Different timeframe
python3 plot_ema_chart.py trading_data/eth_historical_15m.csv --emas medium --window 200
```

### 3. Save Without Opening Browser
```bash
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas fast --output my_chart.html --no-show
```

---

## 📈 What's Included in Charts

### Main Chart (Top Panel)
- **Candlesticks** - Green (up) / Red (down)
- **EMA Lines** - Color-coded by period
  - Cyan/Blue = Fast EMAs (5-20)
  - Orange/Red = Medium EMAs (25-60)
  - Purple/Violet = Slow EMAs (65-120)
  - Gray = Slowest (145)
- **Crossover Markers**
  - 🟢 **Green Triangle Up** = Golden Cross (bullish)
  - 🔴 **Red Triangle Down** = Death Cross (bearish)

### Volume Panel (Middle)
- Green bars = Bullish candle (close > open)
- Red bars = Bearish candle (close < open)

### Ribbon State Panel (Bottom)
- Shows overall EMA ribbon trend
- +2 = all_green
- +1 = mixed_green
- 0 = mixed
- -1 = mixed_red
- -2 = all_red

---

## 🔀 EMA Crossovers Detected

The system tracks 4 key crossover pairs:

### 1. EMA 5/10 - Ultra Fast Scalping
- **Golden Cross**: EMA5 crosses above EMA10
- **Death Cross**: EMA5 crosses below EMA10
- **Use**: Quick scalp entries/exits
- **Frequency**: Very frequent (happens every few hours)

### 2. EMA 10/20 - Fast Trend Changes
- **Golden Cross**: EMA10 crosses above EMA20
- **Death Cross**: EMA10 crosses below EMA20
- **Use**: Confirm short-term trend reversals
- **Frequency**: Moderate (several times per day)

### 3. EMA 20/50 - Medium Trend
- **Golden Cross**: EMA20 crosses above EMA50
- **Death Cross**: EMA20 crosses below EMA50
- **Use**: Swing trading signals
- **Frequency**: Less frequent (every few days)

### 4. EMA 50/100 - Major Trend
- **Golden Cross**: EMA50 crosses above EMA100
- **Death Cross**: EMA50 crosses below EMA100
- **Use**: Major trend confirmation
- **Frequency**: Rare (weekly or longer)

---

## 📊 Crossover Stats (Last 17 Days - 5min Data)

From actual data analysis:

| Pair | Golden Crosses | Death Crosses | Avg per Day |
|------|---------------|---------------|-------------|
| 5/10 | 223 | 223 | ~26 |
| 10/20 | 116 | 116 | ~13 |
| 20/50 | 53 | 53 | ~6 |
| 50/100 | 26 | 26 | ~3 |

---

## 🎨 Interactive Features

The charts are fully interactive! You can:

- **Zoom**: Click and drag to zoom into specific time periods
- **Pan**: Shift + drag to move left/right
- **Hover**: See exact values at any point
- **Toggle**: Click legend items to show/hide EMAs
- **Reset**: Double-click to reset zoom
- **Download**: Camera icon to save as PNG

---

## 💡 Trading Strategy Ideas

### Conservative (Low Risk)
```
Entry: Wait for both 10/20 AND 20/50 golden crosses
Exit: When 10/20 death cross occurs
```

### Aggressive (High Risk)
```
Entry: 5/10 golden cross + ribbon turning green
Exit: 5/10 death cross
```

### Swing Trading
```
Entry: 20/50 golden cross + volume spike
Exit: 20/50 death cross OR 50/100 death cross
```

### Trend Following
```
Only take longs when 50/100 shows golden cross
Only take shorts when 50/100 shows death cross
Use faster crossovers for entries within major trend
```

---

## 🔄 Updating Data

To get fresh data:
```bash
# Fetch latest historical data
python3 fetch_hyperliquid_history.py

# Regenerate charts
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas fast --window 500
```

---

## 📁 File Structure

```
trading_data/
├── eth_historical_1m.csv   (5,037 rows - 3.5 days)
├── eth_historical_3m.csv   (5,012 rows - 10.4 days)
├── eth_historical_5m.csv   (5,008 rows - 17.4 days)
└── eth_historical_15m.csv  (2,881 rows - 30 days)

charts/
└── *.html  (Interactive Plotly charts)
```

---

## 🆘 Troubleshooting

### Chart doesn't open
```bash
# Manually open the HTML file
open charts/eth_5m_with_crossovers.html
# or on Windows:
start charts/eth_5m_with_crossovers.html
```

### Data looks old
```bash
# Refresh the data
python3 fetch_hyperliquid_history.py
```

### Too many EMAs (chart is messy)
```bash
# Use fewer EMAs
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas 5,10,20 --window 300
```

### Want different crossover pairs
Edit `fetch_hyperliquid_history.py` line 219:
```python
cross_pairs=[(5, 10), (10, 20), (20, 50), (50, 100)]  # Change these!
```

---

## 🎯 Next Steps

1. ✅ Review the generated charts
2. Identify patterns in crossovers
3. Backtest strategies based on crossover signals
4. Add more indicators (RSI, MACD, Bollinger Bands)
5. Automate trading signals based on crossovers

Happy trading! 🚀
