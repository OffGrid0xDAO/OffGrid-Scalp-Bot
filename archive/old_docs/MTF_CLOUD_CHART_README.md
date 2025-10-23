# Multi-Timeframe EMA Ribbon Cloud Chart

## Overview

A professional **gradient cloud visualization** that combines EMA ribbons from **9 different timeframes** into a single unified chart with smooth color transitions from green to red based on the positioning of 315 EMA lines relative to price.

## Features

### 📊 Multi-Timeframe Analysis
- **9 Timeframes**: 1min, 2min, 3min, 5min, 8min, 13min, 21min, 34min, 55min
- **35 EMA Periods per Timeframe**: 5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 200
- **Total: 315 EMA Lines** (9 timeframes × 35 EMAs)

### 🎨 Gradient Cloud Visualization
- **Layered Cloud Effect**: Each timeframe gets its own semi-transparent cloud layer
- **Opacity Gradient**: Shorter timeframes (closer to price) have higher opacity
- **Color Gradient**:
  - **Green**: Price above EMAs (bullish - EMAs acting as support)
  - **Yellow**: Neutral (mixed signals)
  - **Red**: Price below EMAs (bearish - EMAs acting as resistance)

### 📈 Cloud Strength Indicator
- **0-100 Score**: Measures conviction of trend across all timeframes
- **Color-Coded Bar Chart**: Visual strength indicator
  - 70-100: Strong Bullish (green)
  - 55-70: Weak Bullish (light green)
  - 45-55: Neutral (yellow)
  - 30-45: Weak Bearish (orange)
  - 0-30: Strong Bearish (red)

### 🔧 Technical Features
- Real Hyperliquid data fetching
- Custom timeframe resampling (2min, 8min, 13min, 21min, 34min, 55min from 1min base)
- Boundary smoothing to reduce noise
- Interactive Plotly charts with hover information
- Configurable via JSON

## Quick Start

### Installation

No additional dependencies needed beyond your existing setup:
```bash
# Already installed in your project:
# - pandas, numpy, plotly
# - hyperliquid API
```

### Generate Chart

```bash
python3 generate_mtf_cloud_chart.py
```

This will:
1. Fetch 30 days of historical data from Hyperliquid
2. Calculate 315 EMA lines across 9 timeframes
3. Aggregate into unified cloud data
4. Generate interactive HTML chart

**Output**: `charts/mtf_cloud/mtf_cloud_ETH_YYYYMMDD_HHMMSS.html`

### View Chart

The chart automatically opens in your browser, or you can manually open it:
```bash
open charts/mtf_cloud/mtf_cloud_ETH_20251023_003152.html
```

## Configuration

All settings are in `src/strategy/strategy_params.json` under `mtf_ribbon_cloud`:

```json
{
  "mtf_ribbon_cloud": {
    "enabled": true,
    "timeframes": [1, 2, 3, 5, 8, 13, 21, 34, 55],
    "ema_periods": [5, 8, 9, 10, 12, 15, 20, 21, ...],
    "days_back": 30,
    "cloud_opacity_base": 0.15,
    "smoothing_window": 3,
    "boundary_method": "minmax",
    "show_individual_layers": true,
    "show_strength_subplot": true,
    "auto_open": false
  }
}
```

### Key Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `timeframes` | List of timeframes in minutes | `[1,2,3,5,8,13,21,34,55]` |
| `days_back` | Historical data period | `30` |
| `cloud_opacity_base` | Base transparency (0.0-1.0) | `0.15` |
| `smoothing_window` | Noise reduction window | `3` |
| `boundary_method` | `"minmax"` or `"percentile"` | `"minmax"` |
| `show_individual_layers` | Show per-timeframe layers | `true` |
| `auto_open` | Open chart automatically | `false` |

## File Structure

```
TradingScalper/
├── generate_mtf_cloud_chart.py          # Main script to run
├── src/
│   ├── data/
│   │   └── mtf_ribbon_fetcher.py        # Multi-timeframe data fetcher
│   ├── strategy/
│   │   ├── mtf_ribbon_aggregator.py     # Cloud aggregation logic
│   │   └── strategy_params.json         # Configuration
│   ├── indicators/
│   │   └── gradient_mapper.py           # Color gradient calculator
│   └── reporting/
│       └── mtf_cloud_chart.py           # Plotly chart generator
└── charts/
    └── mtf_cloud/                       # Generated charts
```

## How It Works

### 1. Data Fetching (`mtf_ribbon_fetcher.py`)
- Fetches native 1m, 3m, 5m data from Hyperliquid API
- Resamples 1m data to create 2min, 8min, 13min, 21min, 34min, 55min timeframes
- Calculates 35 EMAs for each timeframe
- Returns 9 DataFrames with EMA data

### 2. Cloud Aggregation (`mtf_ribbon_aggregator.py`)
- Aligns all timeframes to 1-minute base resolution
- Calculates cloud boundaries (upper = max EMA, lower = min EMA across all 315 lines)
- Computes gradient colors based on EMA position relative to price
- Generates cloud strength score (0-100)

### 3. Visualization (`mtf_cloud_chart.py`)
- Creates layered Plotly chart
- Each timeframe gets a semi-transparent cloud layer
- Opacity gradient: shorter TFs = higher opacity
- Color gradient: green (bullish) → yellow (neutral) → red (bearish)
- Strength indicator subplot

### 4. Color Logic

The gradient color is determined by the **ratio of EMAs below price**:

| EMAs Below Price | Color | Interpretation |
|------------------|-------|----------------|
| 90-100% | Bright Green | Strong bullish (price far above all EMAs) |
| 70-90% | Green | Bullish (most EMAs as support) |
| 50-70% | Yellow-Green | Slightly bullish |
| 30-50% | Yellow-Orange | Slightly bearish |
| 10-30% | Orange-Red | Bearish |
| 0-10% | Red | Strong bearish (price far below all EMAs) |

## Use Cases

### 1. Trend Confirmation
- **Green cloud expanding**: Strong uptrend across all timeframes
- **Red cloud expanding**: Strong downtrend across all timeframes
- **Cloud narrowing**: Trend exhaustion or consolidation

### 2. Multi-Timeframe Alignment
- **All layers green**: Bullish alignment from 1min to 55min
- **Mixed colors**: Disagreement between timeframes (caution)
- **Color transition**: Potential trend change

### 3. Support/Resistance Zones
- **Cloud upper boundary**: Dynamic resistance
- **Cloud lower boundary**: Dynamic support
- **Cloud width**: Volatility measure

### 4. Entry Timing
- **High cloud strength (>70)**: Strong trend, wait for pullback to cloud
- **Cloud color flip**: Potential entry signal when cloud turns green
- **Narrow cloud + green**: Tight consolidation before breakout

## Performance Stats

From the test run:
- **Data Points**: 5,163 candles (1-minute resolution)
- **EMA Lines**: 315 total (9 TFs × 35 EMAs)
- **Sentiment Distribution**:
  - Bullish: 35.3%
  - Neutral: 15.0%
  - Bearish: 49.8%
- **Average Cloud Strength**: 43.9/100
- **Average Cloud Width**: $100 (2.54% of price)
- **Chart File Size**: 4.5 MB (interactive HTML)

## Customization Examples

### More Conservative (Fewer False Signals)
```json
{
  "smoothing_window": 5,          // More smoothing
  "boundary_method": "percentile", // Use 10th-90th percentile
  "percentile_lower": 20,
  "percentile_upper": 80
}
```

### Faster Response (Less Lag)
```json
{
  "timeframes": [1, 2, 3, 5, 8],  // Only shorter timeframes
  "smoothing_window": 1,           // No smoothing
  "ema_periods": [5, 8, 9, 12, 15, 20, 21, 26, 30, 35, 50, 55, 200]  // Fewer EMAs
}
```

### Higher Opacity (More Visible)
```json
{
  "cloud_opacity_base": 0.3,       // Increase from 0.15
  "show_individual_layers": false  // Single unified cloud
}
```

## Integration with Trading Bot

The cloud chart can be generated alongside your existing backtest/optimization reports:

```python
from src.data.mtf_ribbon_fetcher import MTFRibbonFetcher
from src.strategy.mtf_ribbon_aggregator import MTFRibbonAggregator
from src.reporting.mtf_cloud_chart import MTFCloudChartGenerator

# Fetch data
fetcher = MTFRibbonFetcher(symbol='ETH')
mtf_data = fetcher.fetch_and_calculate_all(days_back=30)

# Aggregate
aggregator = MTFRibbonAggregator()
cloud_df = aggregator.aggregate_full(mtf_data)

# Generate chart
chart_gen = MTFCloudChartGenerator()
chart_gen.create_and_save(cloud_df, timeframes=[1,2,3,5,8,13,21,34,55], ema_periods=[...])
```

## Troubleshooting

### Chart Not Generated
```bash
# Check if data fetch was successful
python3 generate_mtf_cloud_chart.py 2>&1 | grep "✅"
```

### Empty Chart
- Ensure Hyperliquid API is accessible
- Try reducing `days_back` to 7 or 14
- Check internet connection

### Performance Issues
- Reduce number of timeframes (e.g., use only [1, 5, 13, 34, 55])
- Reduce `days_back` to 7 or 14 days
- Use `boundary_method: "percentile"` for faster calculation

### Color Gradient Not Smooth
- Increase `smoothing_window` (e.g., 5 or 7)
- Use `show_individual_layers: false` for unified cloud

## Technical Details

### Resampling Strategy
- **Native Timeframes**: 1m, 3m, 5m (from Hyperliquid API)
- **Resampled Timeframes**: 2m, 8m, 13m, 21m, 34m, 55m (from 1m data)
- **Resampling Rules**:
  - Open: First price in period
  - High: Maximum price in period
  - Low: Minimum price in period
  - Close: Last price in period
  - Volume: Sum of volume in period

### EMA Calculation
Uses pandas `.ewm(span=period, adjust=False).mean()` for each timeframe independently.

### Cloud Boundaries
- **Upper**: `max(all 315 EMAs)` at each timestamp
- **Lower**: `min(all 315 EMAs)` at each timestamp
- Optional percentile mode: 10th-90th percentile to reduce outlier impact

### Color Calculation
For each candle:
1. Count EMAs below current price
2. Calculate ratio: `emas_below / total_emas`
3. Map ratio to RGB:
   - ratio ≥ 0.5: Interpolate Yellow → Green
   - ratio < 0.5: Interpolate Red → Yellow
4. Apply opacity based on timeframe layer

## Future Enhancements

Potential improvements:
- [ ] Real-time updates (live streaming data)
- [ ] Custom color schemes (blue/purple, grayscale, etc.)
- [ ] Volume-weighted cloud boundaries
- [ ] Divergence detection between price and cloud
- [ ] Cloud flip alerts (green to red or vice versa)
- [ ] Export to TradingView Pine Script
- [ ] Mobile-optimized responsive charts

## Credits

Built for the TradingScalper project using:
- **Hyperliquid API** for real market data
- **Plotly** for interactive visualizations
- **Pandas/NumPy** for data processing
- **Fibonacci-inspired timeframes** (1, 2, 3, 5, 8, 13, 21, 34, 55)

---

**Questions or Issues?**
Edit `src/strategy/strategy_params.json` to customize settings, or modify the source files in `src/data/`, `src/strategy/`, `src/indicators/`, and `src/reporting/`.
