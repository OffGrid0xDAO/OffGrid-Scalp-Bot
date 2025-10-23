#!/usr/bin/env python3
"""
Pattern Discovery Analysis
Find correlations between EMA states, colors, compressions and profitable trades

This script analyzes:
1. What EMA states appear before profitable moves
2. What color/intensity patterns predict reversals
3. What compression levels signal breakouts
4. Price position relative to EMAs
5. Optimal entry and exit patterns
"""

import csv
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

def parse_timestamp(ts_str):
    """Parse timestamp from CSV"""
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except:
        return None

def load_ema_data(hours=4):
    """Load EMA data from last N hours"""
    data = []
    now = datetime.now()
    cutoff = now - timedelta(hours=hours)

    try:
        with open('trading_data/ema_data_5min.csv', 'r') as f:
            reader = csv.reader(f)

            for row in reader:
                if not row or len(row) < 80:
                    continue

                ts = parse_timestamp(row[0])
                if not ts or ts < cutoff:
                    continue

                # Parse row: timestamp, price, state, then 28 EMAs (name, value, color, intensity)
                try:
                    price = float(row[1])
                    state = row[2]

                    # Parse all 28 EMAs
                    emas = []
                    idx = 3
                    for i in range(28):
                        if idx + 3 < len(row):
                            ema_value = float(row[idx]) if row[idx] else 0
                            ema_color = row[idx + 1] if idx + 1 < len(row) else ''
                            ema_intensity = row[idx + 2] if idx + 2 < len(row) else ''

                            emas.append({
                                'index': i,
                                'name': ['MMA5', 'MMA8', 'MMA13', 'MMA21', 'MMA34', 'MMA55', 'MMA89', 'MMA144',
                                        'EMA5', 'EMA8', 'EMA13', 'EMA21', 'EMA34', 'EMA55', 'EMA89', 'EMA144',
                                        'WMA5', 'WMA8', 'WMA13', 'WMA21', 'WMA34', 'WMA55', 'WMA89', 'WMA144',
                                        'ALMA', 'TRIMA', 'HMA', 'VWMA'][i],
                                'value': ema_value,
                                'color': ema_color,
                                'intensity': ema_intensity
                            })
                            idx += 3

                    data.append({
                        'timestamp': ts,
                        'price': price,
                        'state': state,
                        'emas': emas
                    })
                except (ValueError, IndexError) as e:
                    continue
    except Exception as e:
        print(f"Error loading data: {e}")

    return data

def analyze_ema_colors(snapshot):
    """Analyze EMA color distribution"""
    colors = {'green': 0, 'red': 0, 'yellow': 0, 'gray': 0}
    intensities = {'light': 0, 'dark': 0, 'normal': 0}

    for ema in snapshot['emas']:
        color = ema['color']
        intensity = ema['intensity']

        if color in colors:
            colors[color] += 1
        if intensity in intensities:
            intensities[intensity] += 1

    return colors, intensities

def calculate_ema_compression(emas):
    """Calculate how compressed/spread EMAs are"""
    if not emas or len(emas) < 2:
        return 0

    # Get all EMA values
    values = [e['value'] for e in emas if e['value'] > 0]
    if len(values) < 2:
        return 0

    # Calculate range (highest - lowest)
    ema_range = max(values) - min(values)

    # Calculate average value
    avg_value = sum(values) / len(values)

    # Compression as percentage of price
    compression_pct = (ema_range / avg_value) * 100 if avg_value > 0 else 0

    return compression_pct

def calculate_price_position(price, emas):
    """Calculate where price is relative to EMAs"""
    if not emas:
        return 0, 0

    values = [e['value'] for e in emas if e['value'] > 0]
    if not values:
        return 0, 0

    highest_ema = max(values)
    lowest_ema = min(values)

    if highest_ema == lowest_ema:
        return 0, 0

    # Position within EMA range (0 = at lowest, 100 = at highest)
    position_pct = ((price - lowest_ema) / (highest_ema - lowest_ema)) * 100

    # Count EMAs above/below price
    above = sum(1 for v in values if v > price)
    below = sum(1 for v in values if v < price)

    return position_pct, (above, below)

def find_price_moves(data, min_move_pct=0.5):
    """Find significant price moves (up or down)"""
    moves = []

    for i in range(len(data) - 60):  # Look ahead 10 minutes (60 snapshots)
        start = data[i]

        # Look at next 5-10 minutes
        end_window = data[i+30:i+60]  # 5-10 minutes ahead

        if not end_window:
            continue

        # Find peak profit within window
        peak_up = max((d['price'] for d in end_window), default=start['price'])
        peak_down = min((d['price'] for d in end_window), default=start['price'])

        move_up_pct = ((peak_up - start['price']) / start['price']) * 100
        move_down_pct = ((start['price'] - peak_down) / start['price']) * 100

        # If significant move, record it
        if move_up_pct >= min_move_pct:
            moves.append({
                'timestamp': start['timestamp'],
                'direction': 'UP',
                'entry_price': start['price'],
                'peak_price': peak_up,
                'move_pct': move_up_pct,
                'state': start['state'],
                'colors': analyze_ema_colors(start)[0],
                'intensities': analyze_ema_colors(start)[1],
                'compression': calculate_ema_compression(start['emas']),
                'price_position': calculate_price_position(start['price'], start['emas'])[0],
                'emas_above_below': calculate_price_position(start['price'], start['emas'])[1]
            })
        elif move_down_pct >= min_move_pct:
            moves.append({
                'timestamp': start['timestamp'],
                'direction': 'DOWN',
                'entry_price': start['price'],
                'peak_price': peak_down,
                'move_pct': move_down_pct,
                'state': start['state'],
                'colors': analyze_ema_colors(start)[0],
                'intensities': analyze_ema_colors(start)[1],
                'compression': calculate_ema_compression(start['emas']),
                'price_position': calculate_price_position(start['price'], start['emas'])[0],
                'emas_above_below': calculate_price_position(start['price'], start['emas'])[1]
            })

    return moves

def analyze_patterns(moves):
    """Analyze patterns in profitable moves"""

    # Separate by direction
    up_moves = [m for m in moves if m['direction'] == 'UP']
    down_moves = [m for m in moves if m['direction'] == 'DOWN']

    print("=" * 80)
    print("PATTERN DISCOVERY ANALYSIS")
    print("=" * 80)
    print()

    print(f"Total significant moves found: {len(moves)}")
    print(f"  UP moves (LONG opportunities): {len(up_moves)}")
    print(f"  DOWN moves (SHORT opportunities): {len(down_moves)}")
    print()

    # Analyze UP moves (LONG entries)
    if up_moves:
        print("=" * 80)
        print("📈 UP MOVE PATTERNS (LONG Entry Signals)")
        print("=" * 80)
        print()

        # States before UP moves
        states = Counter(m['state'] for m in up_moves)
        print("🎯 BEST STATES FOR LONG ENTRY:")
        for state, count in states.most_common(5):
            pct = (count / len(up_moves)) * 100
            avg_move = statistics.mean(m['move_pct'] for m in up_moves if m['state'] == state)
            print(f"   {state:15} - {count:3} times ({pct:5.1f}%) | Avg move: {avg_move:.2f}%")

        print()

        # Color patterns
        print("🎨 COLOR PATTERNS BEFORE UP MOVES:")

        # Average colors
        avg_green = statistics.mean(m['colors']['green'] for m in up_moves)
        avg_red = statistics.mean(m['colors']['red'] for m in up_moves)
        avg_gray = statistics.mean(m['colors']['gray'] for m in up_moves)

        print(f"   Average green EMAs: {avg_green:.1f} / 28")
        print(f"   Average red EMAs:   {avg_red:.1f} / 28")
        print(f"   Average gray EMAs:  {avg_gray:.1f} / 28")
        print()

        # Intensity patterns
        print("✨ INTENSITY PATTERNS BEFORE UP MOVES:")
        avg_light = statistics.mean(m['intensities']['light'] for m in up_moves)
        avg_dark = statistics.mean(m['intensities']['dark'] for m in up_moves)

        print(f"   Average LIGHT EMAs: {avg_light:.1f} / 28")
        print(f"   Average DARK EMAs:  {avg_dark:.1f} / 28")
        print()

        # Compression patterns
        print("🔄 COMPRESSION BEFORE UP MOVES:")
        avg_compression = statistics.mean(m['compression'] for m in up_moves)
        print(f"   Average compression: {avg_compression:.2f}%")

        # Find best compression range
        tight = [m for m in up_moves if m['compression'] < 0.5]
        medium = [m for m in up_moves if 0.5 <= m['compression'] < 1.0]
        wide = [m for m in up_moves if m['compression'] >= 1.0]

        print(f"   Tight (<0.5%):   {len(tight)} moves | Avg: {statistics.mean(m['move_pct'] for m in tight) if tight else 0:.2f}%")
        print(f"   Medium (0.5-1%): {len(medium)} moves | Avg: {statistics.mean(m['move_pct'] for m in medium) if medium else 0:.2f}%")
        print(f"   Wide (>1%):      {len(wide)} moves | Avg: {statistics.mean(m['move_pct'] for m in wide) if wide else 0:.2f}%")
        print()

        # Price position patterns
        print("📍 PRICE POSITION BEFORE UP MOVES:")
        avg_position = statistics.mean(m['price_position'] for m in up_moves)
        print(f"   Average position: {avg_position:.1f}% (0=lowest EMA, 100=highest EMA)")

        # Categorize
        bottom = [m for m in up_moves if m['price_position'] < 33]
        middle = [m for m in up_moves if 33 <= m['price_position'] < 67]
        top = [m for m in up_moves if m['price_position'] >= 67]

        print(f"   Bottom third (<33%):  {len(bottom)} moves | Avg: {statistics.mean(m['move_pct'] for m in bottom) if bottom else 0:.2f}%")
        print(f"   Middle third (33-67%): {len(middle)} moves | Avg: {statistics.mean(m['move_pct'] for m in middle) if middle else 0:.2f}%")
        print(f"   Top third (>67%):     {len(top)} moves | Avg: {statistics.mean(m['move_pct'] for m in top) if top else 0:.2f}%")
        print()

        # EMAs above/below price
        print("📊 EMAs RELATIVE TO PRICE BEFORE UP MOVES:")
        avg_above = statistics.mean(m['emas_above_below'][0] for m in up_moves)
        avg_below = statistics.mean(m['emas_above_below'][1] for m in up_moves)
        print(f"   Average EMAs above price: {avg_above:.1f} / 28")
        print(f"   Average EMAs below price: {avg_below:.1f} / 28")
        print()

    # Analyze DOWN moves (SHORT entries)
    if down_moves:
        print()
        print("=" * 80)
        print("📉 DOWN MOVE PATTERNS (SHORT Entry Signals)")
        print("=" * 80)
        print()

        # States before DOWN moves
        states = Counter(m['state'] for m in down_moves)
        print("🎯 BEST STATES FOR SHORT ENTRY:")
        for state, count in states.most_common(5):
            pct = (count / len(down_moves)) * 100
            avg_move = statistics.mean(m['move_pct'] for m in down_moves if m['state'] == state)
            print(f"   {state:15} - {count:3} times ({pct:5.1f}%) | Avg move: {avg_move:.2f}%")

        print()

        # Color patterns
        print("🎨 COLOR PATTERNS BEFORE DOWN MOVES:")

        avg_green = statistics.mean(m['colors']['green'] for m in down_moves)
        avg_red = statistics.mean(m['colors']['red'] for m in down_moves)
        avg_gray = statistics.mean(m['colors']['gray'] for m in down_moves)

        print(f"   Average green EMAs: {avg_green:.1f} / 28")
        print(f"   Average red EMAs:   {avg_red:.1f} / 28")
        print(f"   Average gray EMAs:  {avg_gray:.1f} / 28")
        print()

        # Intensity patterns
        print("✨ INTENSITY PATTERNS BEFORE DOWN MOVES:")
        avg_light = statistics.mean(m['intensities']['light'] for m in down_moves)
        avg_dark = statistics.mean(m['intensities']['dark'] for m in down_moves)

        print(f"   Average LIGHT EMAs: {avg_light:.1f} / 28")
        print(f"   Average DARK EMAs:  {avg_dark:.1f} / 28")
        print()

        # Compression patterns
        print("🔄 COMPRESSION BEFORE DOWN MOVES:")
        avg_compression = statistics.mean(m['compression'] for m in down_moves)
        print(f"   Average compression: {avg_compression:.2f}%")

        tight = [m for m in down_moves if m['compression'] < 0.5]
        medium = [m for m in down_moves if 0.5 <= m['compression'] < 1.0]
        wide = [m for m in down_moves if m['compression'] >= 1.0]

        print(f"   Tight (<0.5%):   {len(tight)} moves | Avg: {statistics.mean(m['move_pct'] for m in tight) if tight else 0:.2f}%")
        print(f"   Medium (0.5-1%): {len(medium)} moves | Avg: {statistics.mean(m['move_pct'] for m in medium) if medium else 0:.2f}%")
        print(f"   Wide (>1%):      {len(wide)} moves | Avg: {statistics.mean(m['move_pct'] for m in wide) if wide else 0:.2f}%")
        print()

        # Price position patterns
        print("📍 PRICE POSITION BEFORE DOWN MOVES:")
        avg_position = statistics.mean(m['price_position'] for m in down_moves)
        print(f"   Average position: {avg_position:.1f}% (0=lowest EMA, 100=highest EMA)")

        bottom = [m for m in down_moves if m['price_position'] < 33]
        middle = [m for m in down_moves if 33 <= m['price_position'] < 67]
        top = [m for m in down_moves if m['price_position'] >= 67]

        print(f"   Bottom third (<33%):  {len(bottom)} moves | Avg: {statistics.mean(m['move_pct'] for m in bottom) if bottom else 0:.2f}%")
        print(f"   Middle third (33-67%): {len(middle)} moves | Avg: {statistics.mean(m['move_pct'] for m in middle) if middle else 0:.2f}%")
        print(f"   Top third (>67%):     {len(top)} moves | Avg: {statistics.mean(m['move_pct'] for m in top) if top else 0:.2f}%")
        print()

        # EMAs above/below price
        print("📊 EMAs RELATIVE TO PRICE BEFORE DOWN MOVES:")
        avg_above = statistics.mean(m['emas_above_below'][0] for m in down_moves)
        avg_below = statistics.mean(m['emas_above_below'][1] for m in down_moves)
        print(f"   Average EMAs above price: {avg_above:.1f} / 28")
        print(f"   Average EMAs below price: {avg_below:.1f} / 28")
        print()

    return up_moves, down_moves

def find_optimal_patterns(up_moves, down_moves):
    """Find the most profitable pattern combinations"""
    print()
    print("=" * 80)
    print("🏆 OPTIMAL ENTRY PATTERNS")
    print("=" * 80)
    print()

    # Find best LONG entry patterns
    if up_moves:
        print("📈 BEST LONG ENTRY PATTERN:")
        print("-" * 80)

        # Filter for best moves (>1% move)
        best_up = [m for m in up_moves if m['move_pct'] >= 1.0]

        if best_up:
            # Find common characteristics
            best_states = Counter(m['state'] for m in best_up).most_common(3)
            avg_green = statistics.mean(m['colors']['green'] for m in best_up)
            avg_red = statistics.mean(m['colors']['red'] for m in best_up)
            avg_light = statistics.mean(m['intensities']['light'] for m in best_up)
            avg_dark = statistics.mean(m['intensities']['dark'] for m in best_up)
            avg_compression = statistics.mean(m['compression'] for m in best_up)
            avg_position = statistics.mean(m['price_position'] for m in best_up)
            avg_emas_above = statistics.mean(m['emas_above_below'][0] for m in best_up)
            avg_move = statistics.mean(m['move_pct'] for m in best_up)

            print(f"Sample size: {len(best_up)} moves (>1% profit)")
            print(f"Average profit: {avg_move:.2f}%")
            print()
            print("Characteristics:")
            print(f"  1. State: {best_states[0][0]} (most common)")
            print(f"  2. Green EMAs: {avg_green:.0f} / 28")
            print(f"  3. Red EMAs: {avg_red:.0f} / 28")
            print(f"  4. LIGHT intensity: {avg_light:.0f} / 28")
            print(f"  5. DARK intensity: {avg_dark:.0f} / 28")
            print(f"  6. Compression: {avg_compression:.2f}%")
            print(f"  7. Price position: {avg_position:.0f}% (within EMA range)")
            print(f"  8. EMAs above price: {avg_emas_above:.0f} / 28")
            print()

            print("💡 OPTIMAL LONG ENTRY RULE:")
            print(f"   - State: {best_states[0][0]} or mixed_green")
            print(f"   - Green EMAs: {avg_green-3:.0f}-{avg_green+3:.0f} (around {avg_green:.0f})")
            print(f"   - LIGHT EMAs: {avg_light-3:.0f}+ (momentum building)")
            print(f"   - Compression: <{avg_compression+0.2:.1f}% (EMAs not too spread)")
            print(f"   - Price: {avg_position-15:.0f}-{avg_position+15:.0f}% within EMA range")
            print()

    # Find best SHORT entry patterns
    if down_moves:
        print("=" * 80)
        print("📉 BEST SHORT ENTRY PATTERN:")
        print("-" * 80)

        best_down = [m for m in down_moves if m['move_pct'] >= 1.0]

        if best_down:
            best_states = Counter(m['state'] for m in best_down).most_common(3)
            avg_green = statistics.mean(m['colors']['green'] for m in best_down)
            avg_red = statistics.mean(m['colors']['red'] for m in best_down)
            avg_light = statistics.mean(m['intensities']['light'] for m in best_down)
            avg_dark = statistics.mean(m['intensities']['dark'] for m in best_down)
            avg_compression = statistics.mean(m['compression'] for m in best_down)
            avg_position = statistics.mean(m['price_position'] for m in best_down)
            avg_emas_below = statistics.mean(m['emas_above_below'][1] for m in best_down)
            avg_move = statistics.mean(m['move_pct'] for m in best_down)

            print(f"Sample size: {len(best_down)} moves (>1% profit)")
            print(f"Average profit: {avg_move:.2f}%")
            print()
            print("Characteristics:")
            print(f"  1. State: {best_states[0][0]} (most common)")
            print(f"  2. Green EMAs: {avg_green:.0f} / 28")
            print(f"  3. Red EMAs: {avg_red:.0f} / 28")
            print(f"  4. LIGHT intensity: {avg_light:.0f} / 28")
            print(f"  5. DARK intensity: {avg_dark:.0f} / 28")
            print(f"  6. Compression: {avg_compression:.2f}%")
            print(f"  7. Price position: {avg_position:.0f}% (within EMA range)")
            print(f"  8. EMAs below price: {avg_emas_below:.0f} / 28")
            print()

            print("💡 OPTIMAL SHORT ENTRY RULE:")
            print(f"   - State: {best_states[0][0]} or mixed_red")
            print(f"   - Red EMAs: {avg_red-3:.0f}-{avg_red+3:.0f} (around {avg_red:.0f})")
            print(f"   - LIGHT EMAs: {avg_light-3:.0f}+ (momentum building)")
            print(f"   - Compression: <{avg_compression+0.2:.1f}% (EMAs not too spread)")
            print(f"   - Price: {avg_position-15:.0f}-{avg_position+15:.0f}% within EMA range")
            print()

    print("=" * 80)


if __name__ == '__main__':
    print("Loading EMA data from last 4 hours...")
    data = load_ema_data(hours=4)
    print(f"Loaded {len(data)} snapshots")
    print()

    print("Finding significant price moves...")
    moves = find_price_moves(data, min_move_pct=0.5)
    print(f"Found {len(moves)} moves ≥ 0.5%")
    print()

    print("Analyzing patterns...")
    up_moves, down_moves = analyze_patterns(moves)

    print("Finding optimal entry patterns...")
    find_optimal_patterns(up_moves, down_moves)

    print()
    print("=" * 80)
    print("✅ ANALYSIS COMPLETE!")
    print("=" * 80)
