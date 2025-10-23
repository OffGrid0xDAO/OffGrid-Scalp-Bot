# 🤖 Automated EMA Data Backfill Guide

## What It Does

Fully automated script that:
1. Opens TradingView in browser
2. Logs in automatically
3. Navigates to the gap time period
4. **Automatically moves mouse** across chart bars
5. Captures EMA values at each bar
6. Saves to CSV
7. Merges with existing dataset

**No manual hovering required!**

## Current Gaps to Fill

### Gap #1: Oct 19, 14:04 to 15:02 (1 hour)
### Gap #2: Oct 20, 12:45 to NOW (~15+ hours)

## Quick Start

### Step 1: Backfill Recent Data (Oct 20 onwards)

```bash
# Fill from Oct 20 12:45 to now
python3 auto_backfill_ema.py
```

**What happens:**
1. Browser opens and logs into TradingView
2. Chart loads with your EMAs
3. Script sets timeframe to 1-minute
4. Navigates to Oct 20, 12:45
5. You verify the chart position (press Enter)
6. **Mouse automatically hovers** across all bars
7. Captures ~900+ bars (15 hours × 60 bars/hour)
8. Saves to `trading_data/ema_backfill.csv`

### Step 2: Merge with Existing Data

```bash
# Merge backfilled data with main dataset
python3 merge_backfill.py
```

**What happens:**
1. Creates backup of original data
2. Loads backfill data
3. Combines and sorts by timestamp
4. Removes duplicates
5. Analyzes remaining gaps
6. Saves merged dataset

## Custom Time Range

Fill specific gap:

```bash
# Syntax: python3 auto_backfill_ema.py "START" "END"

# Fill the 1-hour gap from Oct 19
python3 auto_backfill_ema.py "2025-10-19 14:04" "2025-10-19 15:02"

# Fill from Oct 20 to specific time
python3 auto_backfill_ema.py "2025-10-20 12:45" "2025-10-21 04:00"
```

## How It Works

### Automated Mouse Control

The script uses `pyautogui` to control the mouse:

1. **Finds chart area** - Detects canvas element boundaries
2. **Calculates pixels per bar** - Based on visible bars (~150 on screen)
3. **Moves left to right** - Hovers at calculated intervals
4. **Detects new bars** - Captures when price changes
5. **Reads EMA tooltips** - Scrapes values, colors, intensities

### Safety Features

- ✅ **Failsafe**: Move mouse to top-left corner to abort
- ✅ **Ctrl+C**: Keyboard interrupt to stop
- ✅ **Smooth movement**: 0.05s duration per move (natural)
- ✅ **Verification step**: You confirm chart position before capture
- ✅ **Progress display**: Shows bars captured in real-time

### Expected Capture Rate

| Timeframe | Bars/Hour | 1 Hour | 10 Hours | 24 Hours |
|-----------|-----------|--------|----------|----------|
| 1-minute  | 60        | 60     | 600      | 1,440    |
| 3-minute  | 20        | 20     | 200      | 480      |
| 5-minute  | 12        | 12     | 120      | 288      |

**Recommendation:** Use 1-minute for accuracy, takes longer but more complete.

## Monitoring Progress

While script runs, you'll see:

```
🖱️  Moving mouse to start position...
📸 Starting capture (press Ctrl+C to stop)...

  ✅ Bar 1/900 (0.1%) | Price: 4042.50 | all_green
  ✅ Bar 2/900 (0.2%) | Price: 4042.75 | all_green
  ✅ Bar 3/900 (0.3%) | Price: 4043.00 | all_green
  ...
  ✅ Bar 900/900 (100.0%) | Price: 4150.25 | mixed_green

📊 Capture complete!
   Total bars captured: 900
   Expected: 900
   Coverage: 100.0%
```

## Troubleshooting

### Issue: Mouse moves too fast / misses bars

**Solution:** Edit `auto_backfill_ema.py` line ~340:
```python
# Change from:
current_x += max(1, pixels_per_bar * 0.5)

# To (slower):
current_x += max(1, pixels_per_bar * 0.3)
```

### Issue: Chart not at correct position

**Solution:** After script navigates:
1. Manually adjust chart position
2. Zoom to show ~100-150 bars
3. Then press Enter to start capture

### Issue: Wrong timeframe

**Solution:**
1. Script tries to set 1min automatically
2. If it fails, manually set to 1min before pressing Enter
3. Or edit line 115 to use different timeframe

### Issue: Browser not maximized

**Solution:** Script maximizes automatically, but if issues:
```python
# Ensure these lines are in init_browser():
chrome_options.add_argument('--start-maximized')
driver.maximize_window()
```

## Data Quality Checks

After merge, verify:

```bash
# Check merged dataset
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('trading_data/ema_data_5min.csv', on_bad_lines='skip')
df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
df = df.dropna(subset=['timestamp'])
df = df.sort_values('timestamp')

print(f"Total rows: {len(df)}")
print(f"Start: {df['timestamp'].min()}")
print(f"End: {df['timestamp'].max()}")
print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600:.1f} hours")

# Check for gaps
gaps = 0
for i in range(1, len(df)):
    diff = (df.iloc[i]['timestamp'] - df.iloc[i-1]['timestamp']).total_seconds() / 60
    if diff > 15:
        gaps += 1
        print(f"Gap: {df.iloc[i-1]['timestamp']} to {df.iloc[i]['timestamp']} ({diff/60:.1f}h)")

print(f"\nTotal gaps > 15min: {gaps}")
EOF
```

## Complete Workflow

### Fill All Gaps

```bash
# 1. Fill Oct 19 gap (1 hour)
python3 auto_backfill_ema.py "2025-10-19 14:04" "2025-10-19 15:02"
python3 merge_backfill.py

# 2. Fill Oct 20 onwards (15+ hours)
python3 auto_backfill_ema.py "2025-10-20 12:45" "2025-10-21 04:00"
python3 merge_backfill.py

# 3. Verify no gaps remain
python3 -c "import pandas as pd; df = pd.read_csv('trading_data/ema_data_5min.csv', on_bad_lines='skip'); df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce'); print(f'Dataset: {df[\"timestamp\"].min()} to {df[\"timestamp\"].max()}')"
```

## Files Created

- `auto_backfill_ema.py` - Automated capture script
- `merge_backfill.py` - Merge script
- `trading_data/ema_backfill.csv` - Captured data (temporary)
- `trading_data/ema_data_5min_backup_*.csv` - Automatic backups

## Performance

**Estimated time to backfill:**
- 1 hour gap (60 bars): ~2-3 minutes
- 10 hour gap (600 bars): ~15-20 minutes
- 24 hour gap (1440 bars): ~30-40 minutes

**Accuracy:**
- Should capture 95-100% of bars
- Minor gaps may occur if mouse moves too fast
- Re-run on any remaining gaps

## Tips

1. **Don't touch mouse** during capture (failsafe will abort)
2. **Maximize browser** for best bar detection
3. **Good internet** ensures tooltips load quickly
4. **Start with small gap** to test (like 1-hour gap)
5. **Check coverage %** - should be >95%

## Next Steps

After successful backfill:
1. Run `python3 regenerate_backtest.py` - Test on full dataset
2. Run `python3 user_pattern_optimizer.py` - Optimize on complete data
3. Generate new charts with full timeline

---

**Ready to fill your gaps automatically!** 🚀

No manual hovering, no risk of errors, fully automated capture.
