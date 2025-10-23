# Live Data Updater - Hyperliquid Integration

## Overview

The Live Data Updater automatically fetches the latest candle data from Hyperliquid API to keep your trading indicators and charts current. Perfect for live trading bots that need continuous data updates.

## Features

✅ **Automatic Gap Filling** - Fetches only missing candles since last update
✅ **Multi-Timeframe Support** - Updates 1m, 3m, 5m, 15m, 30m, 1h simultaneously
✅ **Indicator Recalculation** - Automatically recalculates all indicators after fetching
✅ **Chart Regeneration** - Optionally regenerates comprehensive charts
✅ **Continuous Mode** - Runs indefinitely with configurable update intervals
✅ **One-Shot Mode** - Run once for manual updates
✅ **Duplicate Prevention** - Intelligently merges new data without duplicates

## Quick Start

### Run Once (Recommended for Testing)

```bash
# Fetch latest data + recalculate indicators
python3 scripts/update_from_hyperliquid.py

# Fetch data + indicators + regenerate charts
python3 scripts/update_from_hyperliquid.py --charts
```

### Run Continuously (For Live Bot)

```bash
# Start with default 5-minute interval
./start_live_updater.sh

# Start with 15-minute interval
./start_live_updater.sh --interval 15

# Start with chart regeneration (resource intensive!)
./start_live_updater.sh --charts

# Custom interval with charts
./start_live_updater.sh --interval 30 --charts
```

## Usage Examples

### 1. Basic One-Time Update

```bash
python3 scripts/update_from_hyperliquid.py
```

**Output:**
```
🔧 Hyperliquid Data Updater
   Symbol: ETH
   Timeframes: 1m, 3m, 5m, 15m, 30m, 1h
   Data dir: trading_data/raw

📡 Fetching 1m candles from Hyperliquid...
   ✅ Fetched 1111 candles
   ✅ Appended 1111 new candles to trading_data/raw/eth_historical_1m.csv
   📊 Total candles: 6215

📊 RECALCULATING INDICATORS
   ✅ Indicators recalculated successfully
```

### 2. Update Specific Timeframes

```bash
# Update only 5m and 15m
python3 scripts/update_from_hyperliquid.py --timeframes 5m 15m
```

### 3. Skip Indicator Recalculation

```bash
# Just fetch data, don't recalculate
python3 scripts/update_from_hyperliquid.py --no-indicators
```

### 4. Full Pipeline (Data + Indicators + Charts)

```bash
python3 scripts/update_from_hyperliquid.py --charts
```

**Warning:** Chart generation can take 5-10 minutes for all timeframes!

### 5. Continuous Updates for Live Trading

```bash
# Check every 5 minutes (default)
python3 scripts/update_from_hyperliquid.py --continuous

# Check every 1 minute (aggressive)
python3 scripts/update_from_hyperliquid.py --continuous --interval 1

# Check every 30 minutes with full pipeline
python3 scripts/update_from_hyperliquid.py --continuous --interval 30 --charts
```

Press `Ctrl+C` to stop continuous mode.

## Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--symbol` | string | `ETH` | Trading symbol |
| `--timeframes` | list | All | Specific timeframes to update |
| `--continuous` | flag | false | Run continuously instead of once |
| `--interval` | int | `5` | Minutes between updates (continuous mode) |
| `--no-indicators` | flag | false | Skip indicator recalculation |
| `--charts` | flag | false | Regenerate charts after updates |

## How It Works

### 1. Data Fetching

```python
# For each timeframe:
1. Read last timestamp from CSV file
2. Calculate time gap to present
3. Fetch missing candles from Hyperliquid API
4. Convert API response to DataFrame
5. Merge with existing data (remove duplicates)
6. Save back to CSV
```

### 2. Indicator Recalculation

```bash
# Automatically runs:
python3 scripts/process_indicators.py
```

This recalculates:
- EMA Ribbon (35 EMAs)
- RSI (7 & 14)
- MACD (Fast & Standard)
- Stochastic Oscillator (5-3-3)
- Bollinger Bands (20, 2σ)
- VWAP
- Volume analysis
- Confluence scores

### 3. Chart Regeneration (Optional)

```bash
# Automatically runs:
python3 scripts/create_charts.py
```

Generates 6-panel comprehensive charts for all timeframes.

## Hyperliquid API Details

**Endpoint:** `https://api.hyperliquid.xyz/info`

**Request Format:**
```json
{
  "type": "candleSnapshot",
  "req": {
    "coin": "ETH",
    "interval": "1m",
    "startTime": 1729551600000,
    "endTime": 1729638000000
  }
}
```

**Response Format:**
```json
[
  {
    "T": 1729551600000,
    "o": "3850.1",
    "h": "3852.4",
    "l": "3848.5",
    "c": "3851.2",
    "v": "125.45"
  }
]
```

**Limitations:**
- Max 5000 candles per request
- Supported intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 3d, 1w, 1M

## Integration with Live Bot

### Option 1: Run as Separate Process

```bash
# Terminal 1: Start live bot
python3 src/main.py

# Terminal 2: Start data updater
./start_live_updater.sh
```

### Option 2: Scheduled Updates (Cron)

```bash
# Edit crontab
crontab -e

# Add this line (update every 5 minutes)
*/5 * * * * cd /path/to/TradingScalper && python3 scripts/update_from_hyperliquid.py >> logs/updater.log 2>&1

# For hourly updates with charts
0 * * * * cd /path/to/TradingScalper && python3 scripts/update_from_hyperliquid.py --charts >> logs/updater.log 2>&1
```

### Option 3: Systemd Service (Linux)

Create `/etc/systemd/system/trading-updater.service`:

```ini
[Unit]
Description=Trading Bot Data Updater
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/TradingScalper
ExecStart=/usr/bin/python3 scripts/update_from_hyperliquid.py --continuous --interval 5
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable trading-updater
sudo systemctl start trading-updater
sudo systemctl status trading-updater
```

## Performance Notes

### Resource Usage

| Operation | Time | CPU | Memory |
|-----------|------|-----|--------|
| Fetch 1m data (1000 candles) | ~2s | Low | <50MB |
| Fetch all timeframes | ~10s | Low | <100MB |
| Recalculate indicators | ~30s | Medium | ~500MB |
| Regenerate all charts | ~300s | High | ~2GB |

### Recommendations

- **For live trading:** Update every 5 minutes without charts
- **For analysis:** Update every 30 minutes with charts
- **For backtesting:** Update once per day with full pipeline

## Troubleshooting

### Problem: API connection timeout

```bash
# Increase timeout in script (line 102)
response = requests.post(self.api_url, json=payload, timeout=60)
```

### Problem: Missing candles after update

```bash
# Verify timestamp ranges
python3 -c "
import pandas as pd
df = pd.read_csv('trading_data/raw/eth_historical_1m.csv', usecols=['timestamp'])
print('First:', df['timestamp'].iloc[0])
print('Last:', df['timestamp'].iloc[-1])
print('Total:', len(df))
"
```

### Problem: Indicators not recalculating

```bash
# Run manually to see errors
python3 scripts/process_indicators.py
```

### Problem: Charts not regenerating

```bash
# Run manually to see errors
python3 scripts/create_charts.py
```

## File Structure

```
TradingScalper/
├── scripts/
│   ├── update_from_hyperliquid.py    # Main updater script
│   ├── process_indicators.py         # Indicator calculator
│   └── create_charts.py              # Chart generator
├── trading_data/
│   ├── raw/                          # OHLCV data (updated by fetcher)
│   └── indicators/                   # Calculated indicators
├── charts/
│   └── comprehensive/                # Generated charts
├── start_live_updater.sh            # Quick start script
└── docs/
    └── LIVE_DATA_UPDATER.md         # This file
```

## API Rate Limits

Hyperliquid API has no documented rate limits, but be respectful:

- ✅ **Good:** 1 request per minute per timeframe (6 req/min total)
- ⚠️ **Moderate:** 12 requests per minute
- ❌ **Bad:** Hundreds of requests per minute

Our default 5-minute interval = 6 requests every 5 minutes = **safe and respectful**

## Future Enhancements

Potential improvements:

1. **WebSocket Integration** - Real-time updates instead of polling
2. **Multi-Symbol Support** - Fetch multiple coins simultaneously
3. **Gap Detection** - Identify and fill historical data gaps
4. **Health Monitoring** - Track API uptime and response times
5. **Data Validation** - Verify candle integrity (no gaps, correct prices)
6. **Compression** - Store older data in compressed format
7. **Cloud Backup** - Automatic backups to S3/GCS

## Support

For issues or questions:

1. Check logs: `logs/updater.log`
2. Test API manually: `curl -X POST https://api.hyperliquid.xyz/info -d '{"type":"candleSnapshot","req":{"coin":"ETH","interval":"1h","startTime":1729551600000,"endTime":1729638000000}}'`
3. Verify data files: `ls -lh trading_data/raw/`
4. Review script output for errors

## License

Part of TradingScalper project.
