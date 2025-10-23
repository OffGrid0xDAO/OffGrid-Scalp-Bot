# 📊 Quick Start - EMA Charts with Dynamic Colors

## ✅ What You Now Have

### Chart Features
- **All 28 EMAs** plotted automatically
- **Dynamic color changing EMAs**:
  - 🟢 **GREEN** when price is ABOVE the EMA (bullish)
  - 🔴 **RED** when price is BELOW the EMA (bearish)
- **EMA40 & EMA100** always in 🟡 **YELLOW** (reference lines)
- **ALL historical data** shown by default (no time limit)
- **Crossover markers** (golden/death crosses)
- **Volume panel**
- **Ribbon state panel**

### File Sizes
- `eth_5m_all_emas_dynamic.html` - **14MB** (5,008 candles, 17 days, all 28 EMAs)
- `eth_15m_all_emas_dynamic.html` - **~10MB** (2,881 candles, 30 days, all 28 EMAs)

---

## 🚀 Usage

### Generate New Charts
```bash
# 5-minute timeframe (all data, all 28 EMAs)
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv

# 15-minute timeframe (all data, all 28 EMAs)  
python3 plot_ema_chart.py trading_data/eth_historical_15m.csv

# Custom output location
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --output my_chart.html

# Don't open browser (just save file)
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --no-show
```

### Limit Data Range (Optional)
```bash
# Show only last 500 candles
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --window 500

# Show only last 100 candles
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --window 100
```

### Select Specific EMAs (Optional)
```bash
# Just fast EMAs (5, 10, 20)
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas fast

# Custom selection
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas 5,10,20,40,50,100
```

---

## 📁 Generated Files

```
charts/
├── eth_5m_all_emas_dynamic.html    (14MB - 17 days, 5min candles)
├── eth_15m_all_emas_dynamic.html   (10MB - 30 days, 15min candles)
```

---

## 🎨 How to Read the Chart

### EMA Colors
Each EMA line changes color dynamically:
- **Bright Green** = Price trading ABOVE this EMA (bullish for this timeframe)
- **Bright Red** = Price trading BELOW this EMA (bearish for this timeframe)
- **Yellow (EMA40 & EMA100)** = Fixed reference lines (never change color)

### What It Means
- **All EMAs green** = Strong uptrend (price above all EMAs)
- **All EMAs red** = Strong downtrend (price below all EMAs)
- **Mixed colors** = Price in consolidation/transition
- **EMA40 & EMA100 (yellow)** = Key support/resistance levels

### Trading Interpretation
```
Price > EMA5 > EMA10 > EMA20 > ... (all green)
└─> STRONG UPTREND - Consider longs only

Price < EMA5 < EMA10 < EMA20 < ... (all red)
└─> STRONG DOWNTREND - Consider shorts only

Price between EMAs (mixed green/red)
└─> CHOPPY/CONSOLIDATION - Wait for clarity
```

---

## 🔀 Crossover Markers

- 🟢 **Green Triangle Up** = Golden Cross (bullish crossover)
- 🔴 **Red Triangle Down** = Death Cross (bearish crossover)

Tracked pairs:
- EMA 5/10 (ultra-fast)
- EMA 10/20 (fast)
- EMA 20/50 (medium)
- EMA 50/100 (slow)

---

## 💡 Quick Trading Ideas

### Trend Following Strategy
1. Wait for price to cross above ALL EMAs (all turn green)
2. Enter long when you see first EMA 5/10 golden cross
3. Exit when EMAs start turning red (price falls below)

### Scalping Strategy  
1. Use EMA40 (yellow) as your baseline
2. Only trade in direction of EMA40:
   - If price > EMA40: Look for EMA 5/10 golden crosses (longs only)
   - If price < EMA40: Look for EMA 5/10 death crosses (shorts only)
3. Quick in, quick out

### Support/Resistance Strategy
- **EMA100 (thick yellow line)** = Major support/resistance
- Price bouncing off EMA100 = Strong level, potential reversal
- Price breaking through EMA100 = Major trend change

---

## 🔄 Update Data & Regenerate

```bash
# 1. Fetch latest data from Hyperliquid
python3 fetch_hyperliquid_history.py

# 2. Regenerate charts
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --output charts/latest_5m.html
python3 plot_ema_chart.py trading_data/eth_historical_15m.csv --output charts/latest_15m.html
```

---

## 📊 Chart Interaction

The HTML charts are fully interactive:
- **Zoom**: Click and drag
- **Pan**: Hold Shift + drag
- **Hover**: See exact values
- **Toggle EMAs**: Click legend items to show/hide
- **Reset**: Double-click
- **Download**: Camera icon (top right)

---

## ⚡ Performance Tips

If charts are loading slowly:
```bash
# Reduce number of candles
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --window 1000

# Or use fewer EMAs
python3 plot_ema_chart.py trading_data/eth_historical_5m.csv --emas 5,10,20,40,50,100
```

---

## 🎯 What's Next?

1. ✅ Open `charts/eth_5m_all_emas_dynamic.html` in your browser
2. ✅ Study the dynamic color changes
3. ✅ Identify patterns (when all green, all red, etc.)
4. ✅ Look for crossover signals
5. Test strategies based on what you see!

**Happy trading!** 🚀📈
