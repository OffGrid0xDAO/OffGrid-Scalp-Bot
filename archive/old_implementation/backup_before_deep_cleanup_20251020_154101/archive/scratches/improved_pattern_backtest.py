#!/usr/bin/env python3
"""
IMPROVED Pattern-Based Backtest

Issues with first version:
- Too strict on compression (<0.4% caught very few)
- Too strict on green count (9-15 was too narrow)
- Didn't account for state transitions properly

Improvements:
- Relax compression to <0.6%
- Widen green range to 8-18
- Add more entry patterns (mixed, early reversals)
- Better exit logic (trailing stops)
"""

import csv
from datetime import datetime, timedelta
import statistics

def parse_timestamp(ts_str):
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except:
        return None

def load_ema_data(hours=4):
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
    colors = {'green': 0, 'red': 0, 'yellow': 0, 'gray': 0}
    intensities = {'light': 0, 'dark': 0, 'normal': 0}

    for ema in emas:
        if ema['color'] in colors:
            colors[ema['color']] += 1
        if ema['intensity'] in intensities:
            intensities[ema['intensity']] += 1

    return colors, intensities

def calculate_compression(emas):
    values = [e['value'] for e in emas if e['value'] > 0]
    if len(values) < 2:
        return 0

    ema_range = max(values) - min(values)
    avg_value = sum(values) / len(values)

    return (ema_range / avg_value) * 100 if avg_value > 0 else 0

def calculate_price_position(price, emas):
    values = [e['value'] for e in emas if e['value'] > 0]
    if len(values) < 2:
        return 50

    highest = max(values)
    lowest = min(values)

    if highest == lowest:
        return 50

    return ((price - lowest) / (highest - lowest)) * 100

# ============================================================================
# IMPROVED STRATEGIES
# ============================================================================

def old_strategy_signal(snapshot, prev_snapshot, history=None):
    """OLD: Enter on all_green/all_red"""
    if not prev_snapshot:
        return None

    current = snapshot['state']
    prev = prev_snapshot['state']

    if current == 'all_green' and prev != 'all_green':
        return 'LONG'
    if current == 'all_red' and prev != 'all_red':
        return 'SHORT'

    return None

def improved_pattern_signal(snapshot, prev_snapshot, history):
    """
    IMPROVED Pattern Strategy

    Based on data but relaxed constraints:
    - LONG: mixed_green OR mixed with bullish bias
    - SHORT: all_green (overextended) OR mixed_red with bearish bias
    - LIGHT EMAs: 18+ (relaxed from 20)
    - Compression: <0.6% (relaxed from 0.4%)
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

    # ==============================================
    # LONG PATTERNS
    # ==============================================

    # Pattern 1: mixed_green (transitioning) - PRIMARY PATTERN
    if (current_state == 'mixed_green' and
        light_count >= 18 and  # Relaxed from 20
        dark_count <= 5 and  # Relaxed from 3
        compression < 0.6 and  # Relaxed from 0.4
        green_count >= 8 and green_count <= 20):  # Widened from 9-15

        # Fresh signal check
        if prev_snapshot['state'] not in ['mixed_green']:
            return 'LONG'

    # Pattern 2: mixed (neutral transitioning to bullish)
    if (current_state == 'mixed' and
        light_count >= 18 and
        green_count > red_count and  # More green than red
        compression < 0.5):

        # Check if transitioning from red
        prev_colors, _ = analyze_emas(prev_snapshot['emas'])
        if prev_colors['red'] > prev_colors['green']:
            return 'LONG'

    # Pattern 3: Early reversal (was all_red, now transitioning)
    if (current_state in ['mixed', 'mixed_green'] and
        prev_snapshot['state'] in ['all_red', 'mixed_red'] and
        light_count >= 15):  # Lower threshold for reversals
        return 'LONG'

    # ==============================================
    # SHORT PATTERNS
    # ==============================================

    # Pattern 1: all_green overextended (fade the top)
    if (current_state == 'all_green' and
        light_count >= 18 and
        green_count >= 20 and
        price_pos > 50):  # Relaxed from 55

        # Check if been green for a bit (not just flipped)
        if prev_snapshot['state'] in ['all_green', 'mixed_green']:
            return 'SHORT'

    # Pattern 2: mixed_red (transitioning downward)
    if (current_state == 'mixed_red' and
        light_count >= 18 and
        red_count >= 12 and
        compression < 0.6):

        # Fresh signal
        if prev_snapshot['state'] not in ['mixed_red', 'all_red']:
            return 'SHORT'

    return None

def optimal_strategy_signal(data, idx):
    """OPTIMAL: Perfect hindsight"""
    if idx + 60 >= len(data):
        return None

    entry_price = data[idx]['price']
    future = data[idx+1:idx+61]

    long_peak = max(d['price'] for d in future)
    short_peak = min(d['price'] for d in future)

    long_profit_pct = ((long_peak - entry_price) / entry_price) * 100
    short_profit_pct = ((entry_price - short_peak) / entry_price) * 100

    if long_profit_pct >= 0.5 and long_profit_pct > short_profit_pct:
        return 'LONG'
    elif short_profit_pct >= 0.5:
        return 'SHORT'

    return None

# ============================================================================
# IMPROVED BACKTESTING ENGINE
# ============================================================================

def backtest_strategy(data, strategy_func, strategy_name, is_optimal=False):
    """Backtest with improved exit logic"""
    print(f"\n{'='*80}")
    print(f"BACKTESTING: {strategy_name}")
    print(f"{'='*80}\n")

    trades = []
    in_position = False
    position_direction = None
    entry_idx = None
    entry_price = None
    peak_profit = 0

    history = []  # Keep history for pattern matching

    for i in range(1, len(data)):
        snapshot = data[i]
        prev_snapshot = data[i-1]

        history.append(prev_snapshot)
        if len(history) > 10:
            history.pop(0)

        # Get signal
        if is_optimal:
            signal = strategy_func(data, i)
        else:
            signal = strategy_func(snapshot, prev_snapshot, history)

        # Entry logic
        if not in_position and signal:
            in_position = True
            position_direction = signal
            entry_idx = i
            entry_price = snapshot['price']
            entry_time = snapshot['timestamp']
            peak_profit = 0

        # Exit logic
        elif in_position:
            time_in_position = i - entry_idx
            current_price = snapshot['price']

            # Calculate P&L
            if position_direction == 'LONG':
                pnl = current_price - entry_price
            else:
                pnl = entry_price - current_price

            pnl_pct = (pnl / entry_price) * 100

            # Track peak profit for trailing stop
            peak_profit = max(peak_profit, pnl_pct)

            exit_trade = False
            exit_reason = ""

            # Exit conditions (improved)

            # 1. Profit target (+1.2% - more realistic)
            if pnl_pct >= 1.2:
                exit_trade = True
                exit_reason = "Profit target (+1.2%)"

            # 2. Trailing stop (if profit > 0.5%, trail at -0.3% from peak)
            elif peak_profit > 0.5 and pnl_pct < peak_profit - 0.3:
                exit_trade = True
                exit_reason = f"Trailing stop (peak {peak_profit:.2f}%)"

            # 3. Hard stop loss (-0.6% - tighter)
            elif pnl_pct <= -0.6:
                exit_trade = True
                exit_reason = "Stop loss (-0.6%)"

            # 4. Time limit (8 minutes = 48 snapshots, reduced from 10)
            elif time_in_position >= 48:
                exit_trade = True
                exit_reason = "Time limit (8 min)"

            # 5. State-based exit (move complete)
            else:
                colors, intensities = analyze_emas(snapshot['emas'])

                if position_direction == 'LONG':
                    # Exit LONG when all_green + overextended
                    if (snapshot['state'] == 'all_green' and
                        intensities['light'] >= 22 and
                        pnl_pct > 0.3):  # At least small profit
                        exit_trade = True
                        exit_reason = "Move complete (all_green)"

                elif position_direction == 'SHORT':
                    # Exit SHORT when all_red + oversold
                    if (snapshot['state'] == 'all_red' and
                        intensities['light'] >= 22 and
                        pnl_pct > 0.3):
                        exit_trade = True
                        exit_reason = "Move complete (all_red)"

            if exit_trade:
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': snapshot['timestamp'],
                    'exit_price': current_price,
                    'direction': position_direction,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'duration_seconds': time_in_position * 10,
                    'exit_reason': exit_reason,
                    'peak_profit': peak_profit
                })

                in_position = False
                position_direction = None
                entry_idx = None
                entry_price = None
                peak_profit = 0

    # Calculate metrics
    if not trades:
        print("⚠️  No trades executed!")
        return [], {}

    total_trades = len(trades)
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]

    win_rate = (len(winning_trades) / total_trades) * 100

    total_pnl = sum(t['pnl'] for t in trades)
    total_pnl_pct = sum(t['pnl_pct'] for t in trades)
    avg_pnl_pct = total_pnl_pct / total_trades

    avg_winner = statistics.mean(t['pnl_pct'] for t in winning_trades) if winning_trades else 0
    avg_loser = statistics.mean(t['pnl_pct'] for t in losing_trades) if losing_trades else 0

    metrics = {
        'total_trades': total_trades,
        'winners': len(winning_trades),
        'losers': len(losing_trades),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'avg_pnl_pct': avg_pnl_pct,
        'avg_winner_pct': avg_winner,
        'avg_loser_pct': avg_loser,
        'best_trade_pct': max(t['pnl_pct'] for t in trades),
        'worst_trade_pct': min(t['pnl_pct'] for t in trades),
        'avg_peak_profit': statistics.mean(t['peak_profit'] for t in trades)
    }

    # Print results
    print(f"📊 RESULTS:")
    print(f"   Total trades: {total_trades}")
    print(f"   Winners: {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"   Losers: {len(losing_trades)} ({100-win_rate:.1f}%)")
    print()
    print(f"💰 PROFITABILITY:")
    print(f"   Total P&L: ${total_pnl:.2f} ({total_pnl_pct:+.2f}%)")
    print(f"   Average per trade: {avg_pnl_pct:+.2f}%")
    print(f"   Average winner: {avg_winner:+.2f}%")
    print(f"   Average loser: {avg_loser:+.2f}%")
    print(f"   Best trade: {max(t['pnl_pct'] for t in trades):+.2f}%")
    print(f"   Worst trade: {min(t['pnl_pct'] for t in trades):+.2f}%")
    print(f"   Avg peak profit: {metrics['avg_peak_profit']:+.2f}%")
    print()

    return trades, metrics

def compare_strategies(old_metrics, new_metrics, optimal_metrics):
    print()
    print("=" * 80)
    print("📊 STRATEGY COMPARISON")
    print("=" * 80)
    print()

    print(f"{'Metric':<25} {'OLD':<15} {'IMPROVED':<15} {'OPTIMAL':<15}")
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

    # Improvements
    profit_diff = new_metrics.get('avg_pnl_pct', 0) - old_metrics.get('avg_pnl_pct', 0)
    win_rate_diff = new_metrics.get('win_rate', 0) - old_metrics.get('win_rate', 0)
    trade_diff = new_metrics.get('total_trades', 0) - old_metrics.get('total_trades', 0)

    print(f"IMPROVED vs OLD:")
    print(f"   Avg P&L per trade: {profit_diff:+.3f}%")
    print(f"   Win rate: {win_rate_diff:+.1f}%")
    print(f"   Total trades: {trade_diff:+d}")
    print()

    # Efficiency
    if optimal_metrics.get('avg_pnl_pct', 0) != 0:
        old_eff = (old_metrics.get('avg_pnl_pct', 0) / optimal_metrics.get('avg_pnl_pct', 1)) * 100
        new_eff = (new_metrics.get('avg_pnl_pct', 0) / optimal_metrics.get('avg_pnl_pct', 1)) * 100
    else:
        old_eff = 0
        new_eff = 0

    print(f"Efficiency (vs OPTIMAL):")
    print(f"   OLD: {old_eff:.1f}%")
    print(f"   IMPROVED: {new_eff:.1f}%")
    print(f"   Improvement: {new_eff - old_eff:+.1f}%")
    print()

    print("=" * 80)
    print()
    print("💡 With 10x leverage:")
    print(f"   OLD: {old_metrics.get('total_pnl_pct', 0) * 10:+.1f}%")
    print(f"   IMPROVED: {new_metrics.get('total_pnl_pct', 0) * 10:+.1f}%")
    print(f"   OPTIMAL: {optimal_metrics.get('total_pnl_pct', 0) * 10:+.1f}%")
    print("=" * 80)

    return {
        'profit_diff': profit_diff,
        'win_rate_diff': win_rate_diff,
        'old_eff': old_eff,
        'new_eff': new_eff
    }

if __name__ == '__main__':
    print("=" * 80)
    print("IMPROVED PATTERN-BASED BACKTEST")
    print("=" * 80)
    print()

    data = load_ema_data(hours=4)
    print(f"Loaded {len(data)} snapshots")
    print(f"Time: {data[0]['timestamp']} to {data[-1]['timestamp']}")
    print()

    old_trades, old_metrics = backtest_strategy(data, old_strategy_signal, "OLD Strategy")
    new_trades, new_metrics = backtest_strategy(data, improved_pattern_signal, "IMPROVED Pattern Strategy")
    opt_trades, opt_metrics = backtest_strategy(data, optimal_strategy_signal, "OPTIMAL Strategy", is_optimal=True)

    comparison = compare_strategies(old_metrics, new_metrics, opt_metrics)

    print()
    print("=" * 80)
    print("✅ FINAL VERDICT")
    print("=" * 80)
    print()

    if comparison['profit_diff'] > 0:
        print("✅ IMPROVED strategy is BETTER than OLD!")
    else:
        print("⚠️  IMPROVED strategy needs more work")

    if comparison['new_eff'] > 50:
        print("🎯 IMPROVED captures >50% of optimal!")
    elif comparison['new_eff'] > 30:
        print("🎯 IMPROVED captures >30% of optimal")

    print()
    print("=" * 80)
