#!/usr/bin/env python3
"""
Pattern-Based Backtest - Compare Three Strategies

1. OLD Strategy: Enter on all_green/all_red (late entries)
2. NEW Strategy: Pattern-based (mixed_green + 20+ LIGHT EMAs)
3. OPTIMAL Strategy: Perfect hindsight (enter at all significant moves)

This will show:
- How much better NEW is than OLD
- How close NEW gets to OPTIMAL
"""

import csv
from datetime import datetime, timedelta
from collections import defaultdict
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
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        print(f"Error loading data: {e}")

    return data

def analyze_emas(emas):
    """Analyze EMA colors and intensities"""
    colors = {'green': 0, 'red': 0, 'yellow': 0, 'gray': 0}
    intensities = {'light': 0, 'dark': 0, 'normal': 0}

    for ema in emas:
        color = ema['color']
        intensity = ema['intensity']

        if color in colors:
            colors[color] += 1
        if intensity in intensities:
            intensities[intensity] += 1

    return colors, intensities

def calculate_compression(emas):
    """Calculate EMA compression percentage"""
    values = [e['value'] for e in emas if e['value'] > 0]
    if len(values) < 2:
        return 0

    ema_range = max(values) - min(values)
    avg_value = sum(values) / len(values)

    return (ema_range / avg_value) * 100 if avg_value > 0 else 0

def calculate_price_position(price, emas):
    """Calculate where price is relative to EMAs"""
    values = [e['value'] for e in emas if e['value'] > 0]
    if len(values) < 2:
        return 50

    highest = max(values)
    lowest = min(values)

    if highest == lowest:
        return 50

    return ((price - lowest) / (highest - lowest)) * 100

def get_future_peak(data, start_idx, direction, window=60):
    """Get peak profit in next window (5-10 minutes)"""
    if start_idx + window > len(data):
        window = len(data) - start_idx - 1

    if window <= 0:
        return 0, data[start_idx]['price']

    start_price = data[start_idx]['price']
    future_window = data[start_idx+1:start_idx+window+1]

    if direction == 'LONG':
        peak_price = max((d['price'] for d in future_window), default=start_price)
        profit = peak_price - start_price
    else:  # SHORT
        peak_price = min((d['price'] for d in future_window), default=start_price)
        profit = start_price - peak_price

    return profit, peak_price

# ============================================================================
# STRATEGY IMPLEMENTATIONS
# ============================================================================

def old_strategy_signal(snapshot, prev_snapshot):
    """
    OLD Strategy: Enter on state change to all_green/all_red
    This is the traditional "wait for confirmation" approach
    """
    if not prev_snapshot:
        return None

    current_state = snapshot['state']
    prev_state = prev_snapshot['state']

    # LONG: Enter when state becomes all_green
    if current_state == 'all_green' and prev_state != 'all_green':
        return 'LONG'

    # SHORT: Enter when state becomes all_red
    if current_state == 'all_red' and prev_state != 'all_red':
        return 'SHORT'

    return None

def new_strategy_signal(snapshot, prev_snapshot):
    """
    NEW Strategy: Pattern-based entry using our discoveries

    LONG Entry:
    - State: mixed_green (transitioning)
    - LIGHT EMAs: 20+
    - DARK EMAs: 0-3
    - Compression: <0.4%
    - Green EMAs: 9-15

    SHORT Entry:
    - State: all_green (overextended)
    - LIGHT EMAs: 20+
    - Green EMAs: 20+
    - Price position: >55%
    """
    if not prev_snapshot:
        return None

    current_state = snapshot['state']
    colors, intensities = analyze_emas(snapshot['emas'])
    compression = calculate_compression(snapshot['emas'])
    price_pos = calculate_price_position(snapshot['price'], snapshot['emas'])

    light_count = intensities['light']
    dark_count = intensities['dark']
    green_count = colors['green']
    red_count = colors['red']

    # LONG Pattern: mixed_green with strong momentum
    if (current_state == 'mixed_green' and
        light_count >= 20 and
        dark_count <= 3 and
        compression < 0.4 and
        green_count >= 9 and green_count <= 15):

        # Check if this is a fresh signal (state just changed)
        if prev_snapshot['state'] != 'mixed_green':
            return 'LONG'

    # SHORT Pattern: all_green overextended (fade the top)
    if (current_state == 'all_green' and
        light_count >= 20 and
        green_count >= 20 and
        price_pos > 55):

        # Check if ribbon has been all_green for 1-3 snapshots (fresh but established)
        prev_state = prev_snapshot['state']
        if prev_state == 'all_green' or prev_state == 'mixed_green':
            return 'SHORT'

    return None

def optimal_strategy_signal(data, idx):
    """
    OPTIMAL Strategy: Perfect hindsight
    Enter at every significant move (>0.5%)
    This is the theoretical maximum performance
    """
    # Look ahead to see if there's a profitable move
    long_profit, _ = get_future_peak(data, idx, 'LONG', window=60)
    short_profit, _ = get_future_peak(data, idx, 'SHORT', window=60)

    entry_price = data[idx]['price']
    long_pct = (long_profit / entry_price) * 100
    short_pct = (short_profit / entry_price) * 100

    # Enter if move is >= 0.5%
    if long_pct >= 0.5 and long_pct > short_pct:
        return 'LONG'
    elif short_pct >= 0.5:
        return 'SHORT'

    return None

# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

def backtest_strategy(data, strategy_func, strategy_name, is_optimal=False):
    """
    Run backtest for a strategy

    Returns:
    - List of trades
    - Performance metrics
    """
    print(f"\n{'='*80}")
    print(f"BACKTESTING: {strategy_name}")
    print(f"{'='*80}\n")

    trades = []
    in_position = False
    position_direction = None
    entry_idx = None
    entry_price = None

    for i in range(1, len(data)):
        snapshot = data[i]
        prev_snapshot = data[i-1]

        # Get signal from strategy
        if is_optimal:
            signal = strategy_func(data, i)
        else:
            signal = strategy_func(snapshot, prev_snapshot)

        # If not in position, check for entry
        if not in_position and signal:
            in_position = True
            position_direction = signal
            entry_idx = i
            entry_price = snapshot['price']
            entry_time = snapshot['timestamp']

        # If in position, check for exit
        elif in_position:
            # Simple exit: opposite signal or 10 minutes passed
            time_in_position = i - entry_idx
            current_price = snapshot['price']

            # Calculate current P&L
            if position_direction == 'LONG':
                pnl = current_price - entry_price
            else:
                pnl = entry_price - current_price

            pnl_pct = (pnl / entry_price) * 100

            # Exit conditions
            exit_trade = False
            exit_reason = ""

            # 1. Time-based exit (10 minutes = 60 snapshots)
            if time_in_position >= 60:
                exit_trade = True
                exit_reason = "Time limit (10 min)"

            # 2. Profit target (+1.5%)
            elif pnl_pct >= 1.5:
                exit_trade = True
                exit_reason = "Profit target (+1.5%)"

            # 3. Stop loss (-0.8%)
            elif pnl_pct <= -0.8:
                exit_trade = True
                exit_reason = "Stop loss (-0.8%)"

            # 4. State-based exit (move complete)
            elif position_direction == 'LONG' and snapshot['state'] == 'all_green':
                # Exit LONG when reaches all_green (move complete)
                colors, intensities = analyze_emas(snapshot['emas'])
                if intensities['light'] > 24:  # Overextended
                    exit_trade = True
                    exit_reason = "Overextended (all_green + 24+ LIGHT)"

            elif position_direction == 'SHORT' and snapshot['state'] == 'all_red':
                # Exit SHORT when reaches all_red (move complete)
                colors, intensities = analyze_emas(snapshot['emas'])
                if intensities['light'] > 24:  # Oversold
                    exit_trade = True
                    exit_reason = "Oversold (all_red + 24+ LIGHT)"

            if exit_trade:
                # Record trade
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': snapshot['timestamp'],
                    'exit_price': current_price,
                    'direction': position_direction,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'duration_seconds': time_in_position * 10,
                    'exit_reason': exit_reason
                })

                # Reset position
                in_position = False
                position_direction = None
                entry_idx = None
                entry_price = None

    # Calculate metrics
    if not trades:
        print("⚠️  No trades executed!")
        return [], {}

    total_trades = len(trades)
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]

    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0

    total_pnl = sum(t['pnl'] for t in trades)
    total_pnl_pct = sum(t['pnl_pct'] for t in trades)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
    avg_pnl_pct = total_pnl_pct / total_trades if total_trades > 0 else 0

    avg_winner = statistics.mean(t['pnl_pct'] for t in winning_trades) if winning_trades else 0
    avg_loser = statistics.mean(t['pnl_pct'] for t in losing_trades) if losing_trades else 0

    metrics = {
        'total_trades': total_trades,
        'winners': len(winning_trades),
        'losers': len(losing_trades),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'avg_pnl': avg_pnl,
        'avg_pnl_pct': avg_pnl_pct,
        'avg_winner_pct': avg_winner,
        'avg_loser_pct': avg_loser,
        'best_trade_pct': max(t['pnl_pct'] for t in trades),
        'worst_trade_pct': min(t['pnl_pct'] for t in trades)
    }

    # Print results
    print(f"📊 RESULTS:")
    print(f"   Total trades: {total_trades}")
    print(f"   Winners: {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"   Losers: {len(losing_trades)} ({100-win_rate:.1f}%)")
    print()
    print(f"💰 PROFITABILITY:")
    print(f"   Total P&L: ${total_pnl:.2f} ({total_pnl_pct:+.2f}%)")
    print(f"   Average per trade: ${avg_pnl:.2f} ({avg_pnl_pct:+.2f}%)")
    print(f"   Average winner: {avg_winner:+.2f}%")
    print(f"   Average loser: {avg_loser:+.2f}%")
    print(f"   Best trade: {max(t['pnl_pct'] for t in trades):+.2f}%")
    print(f"   Worst trade: {min(t['pnl_pct'] for t in trades):+.2f}%")
    print()

    return trades, metrics

# ============================================================================
# COMPARISON AND ANALYSIS
# ============================================================================

def compare_strategies(old_metrics, new_metrics, optimal_metrics):
    """Compare the three strategies"""
    print()
    print("=" * 80)
    print("📊 STRATEGY COMPARISON")
    print("=" * 80)
    print()

    # Comparison table
    print(f"{'Metric':<25} {'OLD':<15} {'NEW':<15} {'OPTIMAL':<15}")
    print("-" * 80)

    metrics_to_compare = [
        ('Total Trades', 'total_trades', ''),
        ('Win Rate', 'win_rate', '%'),
        ('Avg P&L per trade', 'avg_pnl_pct', '%'),
        ('Total P&L', 'total_pnl_pct', '%'),
        ('Avg Winner', 'avg_winner_pct', '%'),
        ('Avg Loser', 'avg_loser_pct', '%'),
        ('Best Trade', 'best_trade_pct', '%'),
        ('Worst Trade', 'worst_trade_pct', '%'),
    ]

    for label, key, suffix in metrics_to_compare:
        old_val = old_metrics.get(key, 0)
        new_val = new_metrics.get(key, 0)
        opt_val = optimal_metrics.get(key, 0)

        print(f"{label:<25} {old_val:>10.2f}{suffix:<4} {new_val:>10.2f}{suffix:<4} {opt_val:>10.2f}{suffix:<4}")

    print()
    print("=" * 80)
    print("💡 IMPROVEMENT ANALYSIS")
    print("=" * 80)
    print()

    # Calculate improvements
    if old_metrics.get('avg_pnl_pct', 0) != 0:
        profit_improvement = ((new_metrics.get('avg_pnl_pct', 0) - old_metrics.get('avg_pnl_pct', 0))
                             / abs(old_metrics.get('avg_pnl_pct', 1))) * 100
    else:
        profit_improvement = 0

    if old_metrics.get('win_rate', 0) != 0:
        win_rate_improvement = new_metrics.get('win_rate', 0) - old_metrics.get('win_rate', 0)
    else:
        win_rate_improvement = 0

    print(f"NEW vs OLD:")
    print(f"   Profit per trade: {profit_improvement:+.1f}% improvement")
    print(f"   Win rate: {win_rate_improvement:+.1f}% improvement")
    print(f"   Total trades: {new_metrics.get('total_trades', 0) - old_metrics.get('total_trades', 0):+d} more opportunities")
    print()

    # How close to optimal?
    if optimal_metrics.get('avg_pnl_pct', 0) != 0:
        old_efficiency = (old_metrics.get('avg_pnl_pct', 0) / optimal_metrics.get('avg_pnl_pct', 1)) * 100
        new_efficiency = (new_metrics.get('avg_pnl_pct', 0) / optimal_metrics.get('avg_pnl_pct', 1)) * 100
    else:
        old_efficiency = 0
        new_efficiency = 0

    print(f"Efficiency (vs OPTIMAL):")
    print(f"   OLD Strategy: {old_efficiency:.1f}% of optimal")
    print(f"   NEW Strategy: {new_efficiency:.1f}% of optimal")
    print(f"   Improvement: {new_efficiency - old_efficiency:+.1f}%")
    print()

    print("=" * 80)

    return {
        'profit_improvement': profit_improvement,
        'win_rate_improvement': win_rate_improvement,
        'old_efficiency': old_efficiency,
        'new_efficiency': new_efficiency
    }

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("PATTERN-BASED BACKTEST")
    print("Comparing: OLD vs NEW vs OPTIMAL Strategies")
    print("=" * 80)
    print()

    # Load data
    print("Loading EMA data from last 4 hours...")
    data = load_ema_data(hours=4)
    print(f"Loaded {len(data)} snapshots")
    print(f"Time range: {data[0]['timestamp']} to {data[-1]['timestamp']}")
    print()

    # Run backtests
    print("Running backtests...")
    print()

    # 1. OLD Strategy
    old_trades, old_metrics = backtest_strategy(data, old_strategy_signal, "OLD Strategy (all_green/all_red)")

    # 2. NEW Strategy
    new_trades, new_metrics = backtest_strategy(data, new_strategy_signal, "NEW Strategy (Pattern-Based)")

    # 3. OPTIMAL Strategy
    optimal_trades, optimal_metrics = backtest_strategy(data, optimal_strategy_signal, "OPTIMAL Strategy (Perfect Hindsight)", is_optimal=True)

    # Compare results
    comparison = compare_strategies(old_metrics, new_metrics, optimal_metrics)

    # Final verdict
    print()
    print("=" * 80)
    print("✅ FINAL VERDICT")
    print("=" * 80)
    print()

    if comparison['profit_improvement'] > 50:
        print("🏆 EXCELLENT! NEW strategy is >50% better than OLD!")
    elif comparison['profit_improvement'] > 20:
        print("✅ GOOD! NEW strategy is significantly better than OLD!")
    elif comparison['profit_improvement'] > 0:
        print("✅ BETTER! NEW strategy improves on OLD!")
    else:
        print("⚠️  NEW strategy needs refinement")

    print()

    if comparison['new_efficiency'] > 80:
        print("🎯 OUTSTANDING! NEW strategy captures >80% of optimal performance!")
    elif comparison['new_efficiency'] > 60:
        print("🎯 GREAT! NEW strategy captures >60% of optimal performance!")
    elif comparison['new_efficiency'] > 40:
        print("🎯 GOOD! NEW strategy captures >40% of optimal performance!")
    else:
        print("⚠️  There's still room for improvement vs optimal")

    print()
    print("=" * 80)
    print(f"💡 With 10x leverage:")
    print(f"   OLD: {old_metrics.get('total_pnl_pct', 0) * 10:+.1f}%")
    print(f"   NEW: {new_metrics.get('total_pnl_pct', 0) * 10:+.1f}%")
    print(f"   OPTIMAL: {optimal_metrics.get('total_pnl_pct', 0) * 10:+.1f}%")
    print("=" * 80)
