# Quick Start: Multi-Timeframe EMA Cloud Chart

## Generate Your First Chart (30 seconds)

### 1. Run the generator
```bash
python3 generate_mtf_cloud_chart.py
```

### 2. Wait for completion (~60-90 seconds)
You'll see:
```
✅ Successfully fetched 9 timeframes
✅ EMA calculation complete
✅ Aggregation complete
✅ Chart saved: charts/mtf_cloud/mtf_cloud_ETH_20251023_003152.html
```

### 3. Open the chart
```bash
open charts/mtf_cloud/mtf_cloud_ETH_*.html
```

## What You're Looking At

### Chart Components

1. **Top Panel: Price + Cloud**
   - Candlesticks: ETH price action
   - Colored clouds: 9 layers (one per timeframe)
   - Each cloud = 35 EMAs combined

2. **Bottom Panel: Cloud Strength**
   - Bar chart showing 0-100 score
   - Green bars = bullish strength
   - Red bars = bearish strength

### Reading the Colors

| Color | Meaning | What It Tells You |
|-------|---------|-------------------|
| 🟢 **Bright Green** | Price is above 70%+ of all 315 EMAs | Strong uptrend across all timeframes |
| 🟡 **Yellow** | Price is in the middle of the cloud | Consolidation, no clear trend |
| 🔴 **Red** | Price is below 70%+ of all 315 EMAs | Strong downtrend across all timeframes |

### Cloud Strength Score

- **70-100**: Strong trend (good for trend-following)
- **45-70**: Moderate trend
- **30-45**: Weak trend (possible reversal)
- **0-30**: Opposite trend (consider counter-trend)

## Trading Signals

### 🟢 Bullish Setup
```
✓ Cloud is green
✓ Strength > 70
✓ Price pulls back to cloud upper boundary
→ BUY when price bounces off cloud
```

### 🔴 Bearish Setup
```
✓ Cloud is red
✓ Strength < 30
✓ Price rallies to cloud lower boundary
→ SELL when price rejects from cloud
```

### ⚠️ Avoid Trading When
```
✗ Cloud is yellow (neutral)
✗ Strength between 40-60
✗ Cloud is very wide (high volatility)
→ Wait for clear color/strength signal
```

## Common Questions

**Q: Why 9 timeframes?**
A: Fibonacci progression (1, 2, 3, 5, 8, 13, 21, 34, 55) captures short to medium-term trends.

**Q: Why 35 EMAs per timeframe?**
A: Same as your existing ribbon system - comprehensive coverage from fast (5) to slow (200) EMAs.

**Q: How do I change the symbol?**
A: Edit `generate_mtf_cloud_chart.py`, line 30: `symbol = 'BTC'` (or any Hyperliquid symbol)

**Q: How do I get more/less history?**
A: Edit `src/strategy/strategy_params.json`, change `"days_back": 30` to desired number.

**Q: Chart is too cluttered?**
A: Edit config, set `"show_individual_layers": false` for unified cloud instead of 9 layers.

**Q: Colors too subtle?**
A: Edit config, change `"cloud_opacity_base": 0.15` to `0.3` or higher.

## Next Steps

1. **Compare with your existing strategy**
   - Generate cloud chart for same date range as your backtests
   - Check if cloud color aligns with your entry signals
   - Use as confirmation filter

2. **Experiment with settings**
   - Try `"smoothing_window": 5` for smoother cloud
   - Try `"boundary_method": "percentile"` to reduce outliers
   - Try fewer timeframes: `[1, 5, 13, 34, 55]` for cleaner view

3. **Integrate into workflow**
   - Generate daily/weekly cloud charts
   - Use cloud strength > 70 as filter for your existing signals
   - Avoid trades when cloud is yellow (neutral)

## One-Liner Customizations

### Faster chart (fewer timeframes)
```bash
# Edit src/strategy/strategy_params.json
"timeframes": [1, 5, 13, 34, 55]  # Instead of all 9
```

### More visible cloud
```bash
"cloud_opacity_base": 0.3  # Instead of 0.15
```

### Less noise
```bash
"smoothing_window": 7  # Instead of 3
```

### Different symbol
```bash
# Edit generate_mtf_cloud_chart.py, line 30
symbol = 'BTC'  # Or 'SOL', 'DOGE', etc.
```

---

**Ready to generate your first chart?**
```bash
python3 generate_mtf_cloud_chart.py
```

That's it! 🚀
