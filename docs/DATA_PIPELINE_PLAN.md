# Data Pipeline Implementation Plan

## Overview
This document outlines the complete vision for the data gathering and indicator calculation pipeline. The system will fetch 1 year of historical data across 6 timeframes, calculate all technical indicators, and provide plotting capabilities callable from a Telegram bot.

---

## 1. Data Fetching Architecture

### 1.1 Timeframes to Support
```
1min  - 525,600 candles/year - High granularity for scalping
3min  - 175,200 candles/year - Medium-fast scalping
5min  - 105,120 candles/year - Standard scalping timeframe
15min - 35,040 candles/year  - Trend confirmation
30min - 17,520 candles/year  - Higher timeframe context
1hour - 8,760 candles/year   - Major trend direction
```

### 1.2 API Limitations & Batch Strategy

**Hyperliquid API Constraints:**
- Max 5,000 candles per request
- Rate limiting considerations (need to add delays between batches)

**Batch Fetching Strategy:**
```python
# For 1 year of 1min data: 525,600 candles
# Number of batches needed: 525,600 / 5,000 = 106 batches

# Approach:
1. Calculate total candles needed for timeframe
2. Split into 5,000 candle chunks
3. Fetch backwards from current time
4. Add 1-2 second delay between batches to avoid rate limits
5. Merge batches and remove duplicates at boundaries
6. Save intermediate progress every 10 batches (resume capability)
```

**Resume Capability:**
- Save checkpoint files: `trading_data/.checkpoints/eth_1m_checkpoint_batch_45.json`
- If fetch fails, resume from last checkpoint
- Verify data continuity (no gaps in timestamps)

### 1.3 Data Storage Strategy

**File Structure:**
```
trading_data/
├── raw/                          # Raw OHLCV data
│   ├── eth_1m_raw.csv
│   ├── eth_3m_raw.csv
│   ├── eth_5m_raw.csv
│   ├── eth_15m_raw.csv
│   ├── eth_30m_raw.csv
│   └── eth_1h_raw.csv
├── indicators/                   # Processed with indicators
│   ├── eth_1m_full.csv
│   ├── eth_3m_full.csv
│   ├── eth_5m_full.csv
│   ├── eth_15m_full.csv
│   ├── eth_30m_full.csv
│   └── eth_1h_full.csv
├── .checkpoints/                 # Resume points
└── metadata.json                 # Data info (date ranges, candle counts)
```

**metadata.json format:**
```json
{
  "eth_1m": {
    "start_timestamp": 1704067200000,
    "end_timestamp": 1735689600000,
    "total_candles": 525600,
    "last_updated": "2025-10-21T10:30:00Z",
    "indicators_calculated": true
  }
}
```

---

## 2. Indicator Calculation Pipeline

### 2.1 All Indicators to Calculate

#### EMA Ribbon (28 lines)
```
Periods: 5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,100,105,110,115,120,125,130,135,140,145

For each EMA:
- ema_{period}_value: The actual EMA value
- ema_{period}_color: 'green' if close > EMA, 'red' if close < EMA
- ema_{period}_intensity: Distance from price (for gradient visualization)

Special EMAs:
- EMA40: Yellow reference line (support/resistance)
- EMA100: Yellow reference line (major trend)
```

#### EMA Crossovers (4 pairs)
```
Pairs:
- 5/10:   Very fast scalping signals
- 10/20:  Fast trend changes
- 20/50:  Medium trend confirmation
- 50/100: Golden/Death cross (major trend)

Values:
- 1:  Bullish crossover (golden cross)
- -1: Bearish crossover (death cross)
- 0:  No crossover
```

#### RSI - Relative Strength Index (2 periods)
```
RSI_7:  Fast momentum for scalping
RSI_14: Standard momentum indicator

Calculation:
- RS = Average Gain / Average Loss (over period)
- RSI = 100 - (100 / (1 + RS))

Zones:
- > 70: Overbought
- < 30: Oversold
- 50: Neutral momentum
```

#### MACD - Moving Average Convergence Divergence (2 settings)
```
Fast MACD (5/13/5):    For scalping
Standard MACD (12/26/9): Traditional settings

Components:
- macd_line: Fast EMA - Slow EMA
- signal_line: EMA of MACD line
- histogram: MACD - Signal
- crossover: 1 (bullish), -1 (bearish), 0 (none)

Signals:
- MACD > Signal: Bullish momentum
- MACD < Signal: Bearish momentum
- Histogram growing: Momentum increasing
```

#### VWAP - Volume Weighted Average Price
```
VWAP = Σ(Price × Volume) / Σ(Volume)

Use typical price: (High + Low + Close) / 3

Reset points:
- Daily VWAP: Reset at 00:00 UTC
- Session VWAP: No reset (continuous)

Signals:
- Price > VWAP: Bullish, buyers in control
- Price < VWAP: Bearish, sellers in control
- Distance from VWAP: Potential mean reversion
```

#### Volume Analysis
```
Current volume
Volume EMA (20 periods): Average volume
Volume ratio: Current / Average

Volume spikes:
- > 2.0x average: High volume spike
- > 1.5x average: Elevated volume
- < 0.5x average: Low volume
```

#### Ribbon State (Composite)
```
bullish_trend: Count of green EMAs / 28
bearish_trend: Count of red EMAs / 28
compression: Measure of EMA spacing (volatility)
slope: Average angle of EMAs (trend strength)

States:
- strong_bullish: > 80% green, expanding, positive slope
- bullish: > 60% green
- neutral: 40-60% mixed
- bearish: > 60% red
- strong_bearish: > 80% red, expanding, negative slope
```

### 2.2 Calculation Order (Dependencies)

```
Step 1: Calculate all 28 EMAs
  └─> Required for: EMA crossovers, ribbon state, EMA colors

Step 2: Calculate EMA-dependent indicators
  ├─> EMA crossovers (needs EMAs)
  ├─> EMA colors (needs EMAs + close price)
  └─> Ribbon state (needs all EMAs)

Step 3: Calculate price-based indicators (parallel)
  ├─> RSI (needs close prices)
  ├─> MACD (needs close prices, but calculates own EMAs)
  └─> Volume analysis (needs volume data)

Step 4: Calculate VWAP
  └─> Needs high, low, close, volume

Step 5: Generate composite signals
  └─> Confluence score (needs all indicators)
```

### 2.3 Module Structure

```
src/indicators/
├── __init__.py
├── ema_calculator.py          # All EMA calculations
├── rsi_calculator.py          # RSI 7 & 14
├── macd_calculator.py         # Fast & Standard MACD
├── vwap_calculator.py         # VWAP calculation
├── volume_analyzer.py         # Volume metrics
├── ribbon_analyzer.py         # Ribbon state analysis
└── indicator_pipeline.py      # Orchestrates all calculations
```

**indicator_pipeline.py pseudocode:**
```python
class IndicatorPipeline:
    def __init__(self, df):
        self.df = df

    def calculate_all(self):
        # Step 1: EMAs
        self.df = EMACalculator.calculate_all_emas(self.df)
        self.df = EMACalculator.determine_colors(self.df)
        self.df = EMACalculator.detect_crossovers(self.df)

        # Step 2: Parallel calculations
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            futures.append(executor.submit(RSICalculator.calculate, self.df))
            futures.append(executor.submit(MACDCalculator.calculate, self.df))
            futures.append(executor.submit(VWAPCalculator.calculate, self.df))
            futures.append(executor.submit(VolumeAnalyzer.analyze, self.df))

            # Wait for all to complete
            results = [f.result() for f in futures]

        # Step 3: Ribbon analysis (needs EMAs)
        self.df = RibbonAnalyzer.analyze(self.df)

        return self.df
```

---

## 3. Chart Plotting System

### 3.1 Chart Layouts

**Multi-Panel Layout:**
```
Panel 1 (60% height): Price + EMA Ribbon
├─> Candlesticks
├─> All 28 EMAs with dynamic colors
├─> EMA40 & EMA100 in yellow
├─> VWAP line
├─> Crossover markers (triangles)
└─> Trade entry/exit markers (future)

Panel 2 (15% height): Volume
├─> Volume bars (green/red based on price direction)
├─> Volume EMA overlay
└─> Volume spike highlighting

Panel 3 (10% height): RSI
├─> RSI_7 (blue line)
├─> RSI_14 (orange line)
├─> Overbought line (70)
├─> Oversold line (30)
└─> Neutral line (50)

Panel 4 (15% height): MACD
├─> MACD line (blue)
├─> Signal line (orange)
├─> Histogram (green/red bars)
└─> Zero line

Bottom: Shared time axis
```

### 3.2 Interactive Features

**Zoom & Pan:**
- Linked x-axis across all panels
- Independent y-axis per panel
- Range selector: 1H, 4H, 1D, 1W, 1M, ALL

**Hover Information:**
```
When hovering over candle, show:
- Timestamp
- OHLCV data
- All 28 EMA values
- RSI values
- MACD values
- VWAP value
- Volume data
- Ribbon state
```

**Toggle Visibility:**
- Toggle EMA groups: Fast (5-40), Medium (45-90), Slow (100-145)
- Toggle individual indicators
- Toggle crossover markers
- Toggle volume panel

### 3.3 Chart Generation Modes

```python
# Mode 1: Quick chart (last 100 candles)
plot_chart(timeframe='5m', mode='quick', candles=100)

# Mode 2: Recent (last 24 hours)
plot_chart(timeframe='5m', mode='recent')

# Mode 3: Date range
plot_chart(timeframe='5m', start='2024-01-01', end='2024-12-31')

# Mode 4: Full dataset
plot_chart(timeframe='5m', mode='all')

# Mode 5: Around timestamp (for trade analysis)
plot_chart(timeframe='5m', center_time='2024-06-15T14:30:00', window=200)
```

### 3.4 Chart Saving Strategy

```
charts/
├── quick/                    # Temporary quick views
│   └── eth_5m_latest.html
├── analysis/                 # Saved analysis charts
│   ├── eth_5m_2024_Q1.html
│   └── eth_1h_full_year.html
└── trades/                   # Charts for specific trades
    └── trade_12345_context.html
```

---

## 4. Telegram Bot Integration

### 4.1 Bot Commands for Charts

```
/chart {timeframe} [options]

Examples:
/chart 5m                          # Last 100 candles on 5min
/chart 5m last_500                 # Last 500 candles
/chart 1h today                    # Today's 1h candles
/chart 15m 2024-10-15              # Specific date
/chart 5m 2024-10-15_14:30 +200    # 200 candles around timestamp

Options:
--no-emas          # Hide EMAs
--indicators rsi   # Show only RSI
--full            # Full dataset
```

### 4.2 Architecture for Bot Integration

```python
# src/telegram/chart_handler.py

class ChartHandler:
    def __init__(self):
        self.plotter = PlotGenerator()

    async def handle_chart_command(self, message):
        # Parse command
        params = self.parse_chart_params(message.text)

        # Validate
        if not self.validate_params(params):
            await message.reply("Invalid parameters")
            return

        # Generate chart
        await message.reply("Generating chart...")
        chart_path = self.plotter.generate(
            timeframe=params['timeframe'],
            mode=params['mode'],
            **params['options']
        )

        # Upload to Telegram
        with open(chart_path, 'rb') as f:
            await message.reply_document(
                f,
                caption=f"Chart: {params['timeframe']} - {params['mode']}"
            )

        # Cleanup temporary file
        os.remove(chart_path)
```

### 4.3 Performance Considerations

**Large Charts:**
- 1 year of 1min data = massive HTML file
- Solution: Downsample for display, keep full data available

**Downsampling Strategy:**
```python
if total_candles > 5000:
    # Show every Nth candle
    display_interval = total_candles // 5000
    df_display = df[::display_interval]

    # But keep full resolution for recent data
    recent_candles = 500
    df_display = pd.concat([
        df_display[:-recent_candles],
        df[-recent_candles:]
    ])
```

**File Upload Limits:**
- Telegram max file size: 50MB
- If chart > 50MB, generate static image instead
- Use plotly.io.to_image() to create PNG

---

## 5. Implementation Steps

### Phase 1: Extend Data Fetching (Week 1)
```
Task 1.1: Update fetch_hyperliquid_history.py
├─> Add 30min and 1hour timeframes
├─> Extend date range to 1 year
├─> Implement batch fetching with resume capability
├─> Add progress tracking
└─> Add data validation (gap detection)

Task 1.2: Create data fetcher script
├─> src/data/historical_fetcher.py
├─> Orchestrate fetching for all 6 timeframes
├─> Generate metadata.json
└─> Verify data integrity

Task 1.3: Test full data fetch
├─> Run for all timeframes
├─> Verify candle counts
├─> Check for gaps
└─> Validate timestamps
```

### Phase 2: Implement New Indicators (Week 1-2)
```
Task 2.1: RSI Calculator
├─> src/indicators/rsi_calculator.py
├─> Implement RSI_7 and RSI_14
├─> Add overbought/oversold flags
└─> Unit tests

Task 2.2: MACD Calculator
├─> src/indicators/macd_calculator.py
├─> Implement fast (5/13/5) and standard (12/26/9)
├─> Add crossover detection
├─> Add histogram calculations
└─> Unit tests

Task 2.3: VWAP Calculator
├─> src/indicators/vwap_calculator.py
├─> Implement daily and session VWAP
├─> Add distance metrics
└─> Unit tests

Task 2.4: Volume Analyzer
├─> src/indicators/volume_analyzer.py
├─> Calculate volume EMAs
├─> Detect volume spikes
└─> Unit tests

Task 2.5: Indicator Pipeline
├─> src/indicators/indicator_pipeline.py
├─> Orchestrate all calculations
├─> Implement parallel processing
├─> Add caching for performance
└─> Integration tests
```

### Phase 3: Update Plotting System (Week 2)
```
Task 3.1: Extend plot_ema_chart.py
├─> Add RSI panel
├─> Add MACD panel
├─> Add VWAP to price panel
├─> Improve volume visualization
└─> Add toggle controls

Task 3.2: Create plotting modes
├─> Implement 'quick', 'recent', 'range', 'all' modes
├─> Add downsampling for large datasets
├─> Optimize HTML file size
└─> Add static image generation (PNG fallback)

Task 3.3: Chart utilities
├─> src/utils/chart_generator.py
├─> Standardized interface for chart generation
├─> Template system for different chart types
└─> Performance optimizations
```

### Phase 4: Telegram Bot Preparation (Week 3)
```
Task 4.1: Design bot interface
├─> Define all chart commands
├─> Create command parser
├─> Design response format
└─> Error handling

Task 4.2: Create chart handler module
├─> src/telegram/chart_handler.py
├─> Integrate with PlotGenerator
├─> File upload logic
├─> Size optimization for Telegram
└─> Rate limiting

Task 4.3: Testing harness
├─> Simulate bot commands locally
├─> Test file generation
├─> Test upload logic
└─> Performance benchmarks
```

---

## 6. Data Processing Pipeline Flow

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: Fetch Historical Data                          │
│ ├─> Hyperliquid API (6 timeframes)                    │
│ ├─> Batch fetching with resume capability             │
│ └─> Save raw OHLCV to trading_data/raw/               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Step 2: Calculate EMAs                                  │
│ ├─> 28 EMA values                                      │
│ ├─> EMA colors (green/red based on price)             │
│ ├─> EMA crossovers (4 pairs)                          │
│ └─> Ribbon state (compression, slope, trend)          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Step 3: Calculate Additional Indicators (Parallel)     │
│ ├─> RSI (7 & 14)                                       │
│ ├─> MACD (fast & standard)                            │
│ ├─> VWAP (daily & session)                            │
│ └─> Volume analysis                                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Step 4: Save Processed Data                            │
│ └─> Save to trading_data/indicators/                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Step 5: Generate Charts (On Demand)                    │
│ ├─> Load processed data                                │
│ ├─> Apply filters (timerange, indicators)             │
│ ├─> Generate interactive Plotly chart                 │
│ └─> Save to charts/ or return to Telegram bot         │
└─────────────────────────────────────────────────────────┘
```

---

## 7. File Size & Performance Estimates

### Raw Data Sizes (1 year)
```
1min:  525,600 candles × 6 columns (OHLCV+time) ≈ 50 MB
3min:  175,200 candles × 6 columns ≈ 17 MB
5min:  105,120 candles × 6 columns ≈ 10 MB
15min: 35,040 candles × 6 columns ≈ 3 MB
30min: 17,520 candles × 6 columns ≈ 1.5 MB
1hour: 8,760 candles × 6 columns ≈ 0.8 MB

Total raw: ~82 MB
```

### Processed Data Sizes (with all indicators)
```
Columns per row:
- OHLCV: 6
- 28 EMAs × 3 (value, color, intensity): 84
- EMA crossovers: 4
- Ribbon state: 4
- RSI: 4 (RSI_7, RSI_14, zones)
- MACD: 8 (2 sets × 4 values)
- VWAP: 3
- Volume: 4

Total columns: ~117 per row

1min processed: 525,600 rows × 117 columns ≈ 400 MB
Total all timeframes: ~600 MB
```

### Chart Sizes
```
Quick mode (100 candles): ~500 KB HTML
Recent mode (288 candles = 24h on 5m): ~2 MB HTML
Full year 5min (105,120 candles): ~150 MB HTML (needs downsampling!)
```

### Processing Time Estimates
```
Fetch 1 year of 1min data: ~10-15 minutes (106 batches × 5-10s each)
Calculate all indicators: ~30 seconds for 1min, ~5 seconds for 1hour
Generate quick chart: ~2 seconds
Generate full year chart (downsampled): ~15 seconds
```

---

## 8. Error Handling & Validation

### Data Fetching Errors
```python
try:
    data = fetch_batch(start_time, end_time)
except APIRateLimitError:
    # Wait and retry
    time.sleep(10)
    data = fetch_batch(start_time, end_time)
except APIConnectionError:
    # Save checkpoint and exit
    save_checkpoint(current_batch)
    raise
```

### Data Validation
```python
def validate_data(df):
    # Check for gaps in timestamps
    time_diff = df['timestamp'].diff()
    expected_diff = timeframe_to_ms(timeframe)
    gaps = time_diff[time_diff != expected_diff]

    if len(gaps) > 0:
        logging.warning(f"Found {len(gaps)} gaps in data")

    # Check for missing values
    null_counts = df.isnull().sum()
    if null_counts.any():
        logging.error(f"Missing values: {null_counts}")

    # Check for duplicates
    duplicates = df.duplicated(subset=['timestamp'])
    if duplicates.any():
        logging.error(f"Found {duplicates.sum()} duplicate timestamps")
        df = df.drop_duplicates(subset=['timestamp'])

    return df
```

### Indicator Calculation Errors
```python
def safe_calculate_indicator(func, df, *args, **kwargs):
    try:
        return func(df, *args, **kwargs)
    except Exception as e:
        logging.error(f"Failed to calculate {func.__name__}: {e}")
        # Return df with NaN columns for failed indicator
        return df
```

---

## 9. Configuration Management

### config.yaml
```yaml
data:
  symbol: "ETH"
  timeframes: ["1m", "3m", "5m", "15m", "30m", "1h"]
  history_days: 365
  batch_size: 5000
  batch_delay_seconds: 2

indicators:
  emas:
    periods: [5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,100,105,110,115,120,125,130,135,140,145]
    special_colors:
      40: "yellow"
      100: "yellow"

  rsi:
    periods: [7, 14]
    overbought: 70
    oversold: 30

  macd:
    fast:
      fast_period: 5
      slow_period: 13
      signal_period: 5
    standard:
      fast_period: 12
      slow_period: 26
      signal_period: 9

  vwap:
    types: ["daily", "session"]

  volume:
    ema_period: 20
    spike_threshold: 2.0

paths:
  raw_data: "trading_data/raw"
  processed_data: "trading_data/indicators"
  checkpoints: "trading_data/.checkpoints"
  charts: "charts"

plotting:
  default_mode: "recent"
  quick_candles: 100
  recent_hours: 24
  max_candles_full_resolution: 5000
  downsample_threshold: 10000

telegram:
  max_file_size_mb: 50
  chart_timeout_seconds: 60
  rate_limit_charts_per_minute: 5
```

---

## 10. Testing Strategy

### Unit Tests
```
tests/
├── test_ema_calculator.py      # Test EMA calculations
├── test_rsi_calculator.py      # Test RSI calculations
├── test_macd_calculator.py     # Test MACD calculations
├── test_vwap_calculator.py     # Test VWAP calculations
├── test_volume_analyzer.py     # Test volume analysis
└── test_indicator_pipeline.py  # Test full pipeline
```

### Integration Tests
```
tests/integration/
├── test_data_fetch.py          # Test full data fetching
├── test_indicator_flow.py      # Test indicator calculation flow
└── test_chart_generation.py    # Test chart generation
```

### Validation Tests
```
tests/validation/
├── test_data_integrity.py      # Check for gaps, duplicates
├── test_indicator_accuracy.py  # Compare with known values
└── test_crossover_detection.py # Verify crossover logic
```

---

## 11. Next Steps Summary

### Immediate Actions (This Week):
1. **Extend data fetching to 1 year**
   - Modify fetch_hyperliquid_history.py
   - Add 30min and 1hour timeframes
   - Implement batch fetching with checkpoints
   - Run full fetch for all 6 timeframes

2. **Implement RSI, MACD, VWAP calculators**
   - Create individual calculator modules
   - Add unit tests for each
   - Integrate into indicator pipeline

3. **Update plotting system**
   - Add RSI and MACD panels
   - Add VWAP to price panel
   - Implement chart generation modes
   - Test with full year data (downsampling)

### Medium Term (Next 2 Weeks):
4. **Design Telegram bot interface**
   - Define command structure
   - Create chart handler module
   - Implement file upload logic
   - Test locally before bot integration

5. **Optimize performance**
   - Parallel indicator calculations
   - Caching mechanisms
   - Chart downsampling for large datasets
   - Database migration (SQLite) for faster queries

### Long Term (3-4 Weeks):
6. **Build optimal trades detector**
   - Analyze historical data for best possible trades
   - Create ground truth dataset
   - Compare strategy performance vs optimal

7. **Build backtesting framework**
   - Test trading rules on historical data
   - Calculate win rate, profit factor, drawdown
   - Visualize trades on charts

8. **Build parameter optimizer**
   - Grid search for best parameters
   - Walk-forward testing
   - Adaptive parameter adjustment

---

## Conclusion

This pipeline will provide:
- **1 year of historical data** across 6 timeframes
- **All technical indicators** (EMAs, RSI, MACD, VWAP, Volume)
- **Interactive charts** with full indicator visualization
- **Telegram bot integration** ready architecture
- **Scalable foundation** for backtesting and optimization

The system is designed to be modular, testable, and performant, with clear separation of concerns between data fetching, indicator calculation, and visualization.

**Total estimated implementation time: 3-4 weeks**

Ready to proceed with Phase 1 implementation when you give the go-ahead!
