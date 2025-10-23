# Candlestick Analysis with Claude AI

This document explains the new candlestick analysis features added to the EMA backtesting system.

## Overview

The system now generates enhanced candlestick CSVs and can use Claude AI to analyze patterns. Here's what's new:

1. **Enhanced Candlestick CSVs** - OHLC data for both price AND all 28 EMAs with colors/intensities
2. **Profitable Trades Export** - CSV of all winning trades from last N hours
3. **Claude AI Pattern Analysis** - AI-powered analysis of candlestick patterns with EMA context

## Generated Files

### 1. `candlesticks_5min.csv` and `candlesticks_15min.csv`

These files contain candlestick data with:
- **Price OHLC**: `price_open`, `price_high`, `price_low`, `price_close`
- **Ribbon States**: `ribbon_state_open`, `ribbon_state_close`
- **EMA OHLC**: For each of the 28 EMAs (MMA5, MMA10, ..., MMA145):
  - `MMA{X}_open` - EMA value at candle open
  - `MMA{X}_high` - Highest EMA value during candle
  - `MMA{X}_low` - Lowest EMA value during candle
  - `MMA{X}_close` - EMA value at candle close
  - `MMA{X}_color` - EMA color at close (green/red/yellow/gray)
  - `MMA{X}_intensity` - EMA intensity at close (light/dark/normal)

**Example Row:**
```csv
timestamp,price_open,price_high,price_low,price_close,ribbon_state_open,ribbon_state_close,num_points,MMA5_open,MMA5_high,MMA5_low,MMA5_close,MMA5_color,MMA5_intensity,...
2025-10-17 15:15:00,3765.50,3768.20,3763.10,3766.80,all_red,all_red,30,3766.25,3769.15,3764.50,3767.45,red,light,...
```

### 2. `profitable_trades_last_30h.csv`

Contains all profitable trades (P&L > 0.3%) from the last 30 hours:
- Entry/exit timestamps and prices
- Direction (LONG/SHORT)
- Hold duration
- P&L in % and dollars
- Quality score
- Market conditions at entry
- Ribbon states

**Use Case:** Study what made these trades successful!

### 3. `candlestick_analysis.json`

Output from Claude AI analysis containing:
- Current trend and strength
- Candlestick patterns identified on both timeframes
- EMA ribbon behavior
- Support/Resistance levels
- High-probability setups with entry triggers
- Overall market assessment

## Usage

### Step 1: Run Backtest to Generate CSVs

```bash
python3 backtest_ema_strategy.py
```

This will:
1. Analyze historical EMA data
2. Detect entry opportunities
3. Simulate trades
4. Generate performance report
5. **Export candlestick CSVs with full EMA data**
6. **Export profitable trades CSV**

### Step 2: Analyze Patterns with Claude AI

```bash
python3 claude_candlestick_analyzer.py
```

This will:
1. Load the candlestick CSVs
2. Send last 50 (5min) and 30 (15min) candles to Claude
3. Get AI analysis of patterns and setups
4. Print formatted analysis
5. Save results to `candlestick_analysis.json`

**Cost:** Approximately $0.01-0.03 per analysis

## Example Output

### Candlestick Analysis Output:

```
================================================================================
CLAUDE CANDLESTICK PATTERN ANALYSIS
================================================================================

📊 TREND: BULLISH (STRONG)

📈 5-MINUTE TIMEFRAME:
   Ribbon State: all_green
   Patterns: Bullish Engulfing, Hammer
   Observations: Strong bullish momentum with ribbon fully aligned green...
   Support Levels: 3760 (MMA40), 3755 (MMA100)

📈 15-MINUTE TIMEFRAME:
   Ribbon State: all_green
   Patterns: Inside Bar, Bullish Flag
   Observations: Consolidation after strong move up...

🎯 HIGH-PROBABILITY SETUPS (2 found):

   Setup 1: Bullish Engulfing + Ribbon Flip
   Timeframe: 5min
   Direction: LONG
   Confidence: HIGH
   Description: Price formed bullish engulfing candle as ribbon flipped to all_green
   Entry Trigger: Break above 3770 with volume
   Invalidation: Close below 3760 (MMA40 support)

💡 OVERALL ASSESSMENT:
   Strong bullish trend confirmed on both timeframes. Ribbon fully aligned green
   with light intensity indicating committed momentum. Look for pullbacks to
   MMA40 (3760) for low-risk long entries. Avoid chasing at current levels.
```

## Understanding the Data

### Why OHLC for EMAs?

EMAs are traditionally shown as lines, but calculating OHLC for them reveals:
- **EMA volatility** - How much the EMA moved during the candle period
- **EMA momentum** - Fast-moving EMAs will show larger OHLC ranges
- **Support/Resistance strength** - EMAs that stayed flat (low range) are stronger S/R

### EMA Color Meanings

- **Green** = Price above EMA (bullish)
- **Red** = Price below EMA (bearish)
- **Yellow** = Critical support/resistance EMA (typically MMA40, MMA100)
- **Gray** = Neutral/transitioning

### EMA Intensity Meanings

- **Light** = Strong commitment (bright saturated color, RGB ≥ 150)
  - Light green = Strong bullish momentum
  - Light red = Strong bearish momentum
- **Dark** = Early transition (dim color, RGB < 150)
  - Dark green = Starting to turn bullish
  - Dark red = Starting to turn bearish
- **Normal** = Standard state

## Advanced Analysis Ideas

### 1. Candlestick Pattern + Ribbon Confluence

Look for candlestick patterns (hammer, engulfing, etc.) that occur **exactly when** ribbon flips:
```python
# In candlestick CSV, check:
if ribbon_state_open == "all_red" and ribbon_state_close == "mixed_red":
    # Ribbon starting to flip
    if price_close > price_open:  # Bullish candle
        # HIGH-PROBABILITY LONG SETUP!
```

### 2. EMA Support/Resistance Testing

Track when price bounces off specific EMAs:
```python
# Did price reject from MMA40?
if price_low <= MMA40_close <= price_high:
    if price_close > MMA40_close:
        # Bounced off EMA40 support!
```

### 3. Multi-Timeframe Confirmation

Compare 5min and 15min candles at same timestamp:
- Both green = Strong bullish
- Both red = Strong bearish
- Conflicting = Wait for alignment

## API Costs

- **Backtest**: $0.00 (no Claude calls, pure math)
- **Candlestick Analysis**: ~$0.01-0.03 per run
  - 50 candles on 5min + 30 candles on 15min
  - Simplified CSV format to reduce tokens
  - Full EMA data available but not sent to reduce costs

## Tips

1. **Run backtest first** to generate CSVs with latest data
2. **Use Claude analysis** when you want pattern insights, not for every tick
3. **Study profitable_trades CSV** to learn what worked in the past
4. **Look for confluences** between candlestick patterns and ribbon states
5. **Compare timeframes** - setups appearing on both 5min and 15min are stronger

## Customization

### Analyze Different Time Ranges

Edit `claude_candlestick_analyzer.py`:
```python
# Load more/fewer candles
candles_5min = analyzer.load_candlestick_csv('candlesticks_5min.csv', limit=200)  # More history
```

### Change Profitable Trades Time Window

Edit `backtest_ema_strategy.py` in `main()`:
```python
# Export last 48 hours instead of 30
backtester.export_profitable_trades_csv(
    output_file='profitable_trades_last_48h.csv',
    hours=48
)
```

### Include Full EMA Data in Claude Analysis

Edit `claude_candlestick_analyzer.py` in `analyze_patterns()`:
```python
# Pass include_all_emas=True for full data (higher cost!)
csv_5min = self.format_candlesticks_for_claude(candles_5min[-50:], include_all_emas=True)
```

## Questions?

Check the main trading strategy documentation in `claude_trader.py` for the full EMA ribbon logic and decision-making process.
