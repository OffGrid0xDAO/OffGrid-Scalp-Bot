# Data Management Module

Handles fetching, storing, and validating historical market data from Hyperliquid API.

## Features

### HyperliquidFetcher
- ✅ Fetch 1 year of historical OHLCV data
- ✅ Support for 6 timeframes: 1m, 3m, 5m, 15m, 30m, 1h
- ✅ Batch fetching (overcomes 5000 candle API limit)
- ✅ Resume capability with checkpoints
- ✅ Calculate 28 EMAs with colors
- ✅ Detect EMA crossovers (golden/death crosses)
- ✅ Analyze ribbon state
- ✅ Progress tracking and error handling

## Usage

### Quick Start

From project root:

```bash
# Copy .env.example to .env and configure
cp .env.example .env

# Edit .env with your settings
# SYMBOL=ETH
# DAYS_BACK=365
# TIMEFRAMES=1m,3m,5m,15m,30m,1h

# Run data fetcher
python3 fetch_data.py
```

### Programmatic Usage

```python
from src.data import HyperliquidFetcher

# Initialize
fetcher = HyperliquidFetcher(symbol='ETH')

# Fetch 1 year of 5min data
candles = fetcher.fetch_historical_data(
    interval='5m',
    days_back=365,
    use_checkpoint=True
)

# Calculate EMAs
df = fetcher.calculate_emas(candles)

# Add EMA colors
df = fetcher.determine_ema_colors(df)

# Analyze ribbon
df = fetcher.analyze_ribbon_state(df)

# Detect crossovers
df = fetcher.detect_ema_crossovers(df)

# Save to CSV
fetcher.save_to_csv(df, 'trading_data/raw/eth_5m.csv')
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYMBOL` | ETH | Trading symbol |
| `DAYS_BACK` | 365 | Days of history to fetch |
| `TIMEFRAMES` | 1m,3m,5m,15m,30m,1h | Comma-separated timeframes |

### Timeframe Support

| Timeframe | Candles/Year | Storage (CSV) | Fetch Time |
|-----------|--------------|---------------|------------|
| 1m | 525,600 | ~50 MB | ~15 min |
| 3m | 175,200 | ~17 MB | ~5 min |
| 5m | 105,120 | ~10 MB | ~3 min |
| 15m | 35,040 | ~3 MB | ~1 min |
| 30m | 17,520 | ~1.5 MB | ~30 sec |
| 1h | 8,760 | ~800 KB | ~15 sec |

**Total for all 6 timeframes: ~82 MB raw, ~600 MB with indicators**

## Output Format

### CSV Structure

```
timestamp,open,high,low,close,volume,price,ribbon_state,
MMA5_value,MMA5_color,MMA5_intensity,
MMA10_value,MMA10_color,MMA10_intensity,
... (all 28 EMAs) ...
MMA145_value,MMA145_color,MMA145_intensity,
ema_cross_5_10,ema_cross_10_20,ema_cross_20_50,ema_cross_50_100
```

### Data Columns

**OHLCV (Base)**:
- `timestamp`: ISO format (2025-01-01T12:34:56)
- `open`, `high`, `low`, `close`: Price data
- `volume`: Trading volume
- `price`: Current price (same as close)

**EMA Ribbon (28 × 3 = 84 columns)**:
- `MMA{period}_value`: EMA value
- `MMA{period}_color`: green/red/neutral (price vs EMA)
- `MMA{period}_intensity`: normal (placeholder)

**Ribbon State**:
- `ribbon_state`: all_green, mixed_green, mixed, mixed_red, all_red
- `green_count`: Number of green EMAs
- `alignment_pct`: Percentage of green EMAs

**EMA Crossovers (4 columns)**:
- `ema_cross_5_10`: golden_cross/death_cross/none
- `ema_cross_10_20`: golden_cross/death_cross/none
- `ema_cross_20_50`: golden_cross/death_cross/none
- `ema_cross_50_100`: golden_cross/death_cross/none

## Resume Capability

The fetcher automatically saves checkpoints every 10 batches:

```
trading_data/.checkpoints/ETH_5m_checkpoint.json
```

If interrupted, simply re-run and it will resume from the last checkpoint.

## Error Handling

- **API Failures**: Automatically retries with exponential backoff
- **Rate Limiting**: 1 second delay between batches
- **Missing Data**: Continues with warning, doesn't fail entire fetch
- **Checkpoints**: Saves progress every 10 batches

## Next Steps

After fetching data:

1. **Add additional indicators** (RSI, MACD, VWAP, Volume) → `src/indicators/`
2. **Convert to Parquet + SQLite** for better performance
3. **Validate data** (check gaps, duplicates) → `src/data/data_validator.py`
4. **Generate metadata** → `trading_data/metadata.json`
5. **Begin optimal trade detection** → `src/analysis/`
