"""
Enrich User Trades with EMA Pattern Data
Analyzes EMA states, compression, and light EMA counts at entry/exit points
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path


def analyze_ema_state_at_time(df: pd.DataFrame, target_time: datetime) -> dict:
    """Analyze EMA state at a specific time"""

    # Find closest timestamp
    time_diff = abs(df['timestamp'] - target_time)
    if time_diff.min() > pd.Timedelta(minutes=5):
        return None

    closest_idx = time_diff.idxmin()
    row = df.iloc[closest_idx]

    # Get price
    price = row.get('price', 0)

    # Calculate compression
    ema_values = []
    for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
        val_col = f'MMA{ema}_value'
        if val_col in row.index and pd.notna(row[val_col]):
            ema_values.append(float(row[val_col]))

    if len(ema_values) >= 3:
        ema_min = min(ema_values)
        ema_max = max(ema_values)
        compression = (ema_max - ema_min) / ema_min if ema_min > 0 else 0
    else:
        compression = 0

    # Count light EMAs (for both directions)
    light_green = 0
    light_red = 0
    dark_green = 0
    dark_red = 0

    for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60]:
        color_col = f'MMA{ema}_color'
        intensity_col = f'MMA{ema}_intensity'

        if color_col in row.index and intensity_col in row.index:
            color = row[color_col]
            intensity = row[intensity_col]

            if color == 'green' and intensity == 'light':
                light_green += 1
            elif color == 'green' and intensity == 'dark':
                dark_green += 1
            elif color == 'red' and intensity == 'light':
                light_red += 1
            elif color == 'red' and intensity == 'dark':
                dark_red += 1

    # Get ribbon state
    ribbon_state = row.get('ribbon_state', 'unknown')

    return {
        'timestamp': row['timestamp'].isoformat(),
        'price': price,
        'compression': compression,
        'light_green_emas': light_green,
        'light_red_emas': light_red,
        'dark_green_emas': dark_green,
        'dark_red_emas': dark_red,
        'ribbon_state': ribbon_state
    }


def enrich_user_trades():
    """Load user trades and enrich with EMA pattern data"""

    print("="*70)
    print("📊 ENRICHING USER TRADES WITH EMA PATTERN DATA")
    print("="*70)

    # Load user trades
    user_trades_path = 'trading_data/optimal_trades_user.json'

    try:
        with open(user_trades_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ User trades file not found")
        return

    trades = data.get('trades', [])
    print(f"\n📋 Found {len(trades)} user trades")

    # Load EMA data
    ema_file = 'trading_data/ema_data_5min.csv'

    try:
        df = pd.read_csv(ema_file, on_bad_lines='skip')
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        print(f"✅ Loaded EMA data: {len(df)} rows")
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    except Exception as e:
        print(f"❌ Error loading EMA data: {e}")
        return

    # Enrich each trade
    enriched_trades = []
    total_compression = 0
    total_light_emas = 0
    valid_trades = 0

    print("\n" + "="*70)
    print("ANALYZING TRADES")
    print("="*70)

    for i, trade in enumerate(trades, 1):
        print(f"\n[{i}/{len(trades)}] {trade['direction']}")

        entry_time = pd.to_datetime(trade['entry_time'])
        exit_time = pd.to_datetime(trade['exit_time'])

        print(f"  Entry: {entry_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Exit:  {exit_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  PnL:   {trade['pnl_pct']:+.2f}%")

        # Analyze entry state
        entry_state = analyze_ema_state_at_time(df, entry_time)

        if entry_state:
            # Add to trade
            enriched_trade = trade.copy()
            enriched_trade['entry_compression'] = entry_state['compression']
            enriched_trade['entry_ribbon_state'] = entry_state['ribbon_state']

            # For LONG trades, count light green EMAs
            # For SHORT trades, count light red EMAs
            if trade['direction'] == 'LONG':
                light_emas_count = entry_state['light_green_emas']
                enriched_trade['entry_light_emas'] = light_emas_count
                enriched_trade['entry_dark_emas'] = entry_state['dark_green_emas']
            else:
                light_emas_count = entry_state['light_red_emas']
                enriched_trade['entry_light_emas'] = light_emas_count
                enriched_trade['entry_dark_emas'] = entry_state['dark_red_emas']

            print(f"  ✅ Compression: {entry_state['compression']:.4f} ({entry_state['compression']*100:.2f}%)")
            print(f"  ✅ Light EMAs: {light_emas_count}")
            print(f"  ✅ Ribbon: {entry_state['ribbon_state']}")

            enriched_trades.append(enriched_trade)
            total_compression += entry_state['compression']
            total_light_emas += light_emas_count
            valid_trades += 1
        else:
            print(f"  ⚠️  No EMA data found (too far from data)")
            enriched_trades.append(trade)

    # Calculate averages
    if valid_trades > 0:
        avg_compression = total_compression / valid_trades
        avg_light_emas = total_light_emas / valid_trades
    else:
        avg_compression = 0
        avg_light_emas = 0

    # Update data structure
    data['trades'] = enriched_trades
    data['patterns'] = {
        'avg_compression': avg_compression,
        'avg_light_emas': avg_light_emas
    }
    data['last_updated'] = datetime.now().isoformat()
    data['enriched'] = True

    # Save
    with open(user_trades_path, 'w') as f:
        json.dump(data, f, indent=2)

    print("\n" + "="*70)
    print("📊 ENRICHMENT SUMMARY")
    print("="*70)
    print(f"Total trades: {len(trades)}")
    print(f"Enriched: {valid_trades}")
    print(f"Avg Compression: {avg_compression:.4f} ({avg_compression*100:.2f}%)")
    print(f"Avg Light EMAs: {avg_light_emas:.1f}")
    print(f"\n✅ User trades file updated with EMA pattern data!")
    print(f"   File: {user_trades_path}")


if __name__ == '__main__':
    enrich_user_trades()
