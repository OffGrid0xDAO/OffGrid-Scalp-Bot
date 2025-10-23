"""
Compare Trading Systems
OLD: Current over-trading system (1078 trades)
NEW: User pattern matching system
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from user_pattern_trader import UserPatternTrader


def load_ema_data():
    """Load EMA data"""
    df = pd.read_csv('trading_data/ema_data_5min.csv', on_bad_lines='skip')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def calculate_indicators(row):
    """Calculate indicators from row"""
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

    # Count light EMAs
    light_emas = 0
    for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60]:
        color_col = f'MMA{ema}_color'
        intensity_col = f'MMA{ema}_intensity'

        if color_col in row.index and intensity_col in row.index:
            if row[color_col] == 'green' and row[intensity_col] == 'light':
                light_emas += 1

    return {
        'compression': compression,
        'light_emas': light_emas,
        'ribbon_state': row.get('ribbon_state', 'unknown'),
        'price': row.get('price', 0)
    }


def test_new_system(hours_back=None):
    """Test new user pattern matching system"""
    print("="*80)
    print("🧪 TESTING NEW USER PATTERN MATCHING SYSTEM")
    print("="*80)

    # Load data
    df = load_ema_data()

    # Filter to time range (if specified)
    if hours_back:
        cutoff = datetime.now() - timedelta(hours=hours_back)
        df = df[df['timestamp'] >= cutoff].reset_index(drop=True)
        duration_label = f"last {hours_back} hours"
    else:
        duration_label = "ALL historical data"
        hours_back = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600

    print(f"\n📊 Data: {len(df)} rows from {duration_label}")
    print(f"   From: {df['timestamp'].min()}")
    print(f"   To:   {df['timestamp'].max()}")
    print(f"   Duration: {hours_back:.1f} hours ({hours_back/24:.1f} days)")

    # Initialize trader
    trader = UserPatternTrader()

    # Track signals
    signals = []
    recent_trades = []

    print("\n🔍 Scanning for quality setups...")

    for idx in range(10, len(df)):
        row = df.iloc[idx]

        # Calculate indicators
        indicators = calculate_indicators(row)

        # Get decision
        decision = trader.get_trade_decision(
            indicators_5min=indicators,
            indicators_15min=indicators,
            current_price=indicators['price'],
            df_recent=df.iloc[:idx+1],
            current_idx=idx,
            recent_trades=recent_trades
        )

        if decision.get('entry_recommended', False):
            signal = {
                'time': row['timestamp'].isoformat(),
                'direction': decision['direction'],
                'price': indicators['price'],
                'confidence': decision['confidence'],
                'quality_score': decision['quality_score'],
                'quality_breakdown': decision['quality_breakdown'],
                'momentum': decision.get('momentum', {}),
                'compression': indicators['compression'],
                'light_emas': indicators['light_emas'],
                'ribbon_state': indicators['ribbon_state']
            }
            signals.append(signal)
            recent_trades.append({'time': row['timestamp'].isoformat()})

            print(f"\n✅ SIGNAL #{len(signals)}")
            print(f"   Time: {row['timestamp']}")
            print(f"   Direction: {decision['direction']}")
            print(f"   Quality Score: {decision['quality_score']}/100")
            print(f"   Confidence: {decision['confidence']:.0%}")
            print(f"   Compression: {indicators['compression']*100:.2f}%")
            print(f"   Light EMAs: {indicators['light_emas']}")
            if decision.get('momentum', {}).get('detected'):
                print(f"   🚀 MOMENTUM: {decision['momentum']['direction']} {decision['momentum']['magnitude']:.2f}%")

    print("\n" + "="*80)
    print("📊 NEW SYSTEM RESULTS")
    print("="*80)
    print(f"Total Signals: {len(signals)}")
    print(f"Avg Quality Score: {sum(s['quality_score'] for s in signals)/len(signals) if signals else 0:.1f}/100")
    print(f"Avg Confidence: {sum(s['confidence'] for s in signals)/len(signals) if signals else 0:.0%}")
    print(f"Signals per Hour: {len(signals)/hours_back:.2f}")

    # Compare to old system
    try:
        with open('trading_data/backtest_trades.json', 'r') as f:
            old_data = json.load(f)
            old_trades = old_data.get('total_trades', 0)

        print("\n" + "="*80)
        print("⚖️  COMPARISON")
        print("="*80)
        print(f"OLD System: {old_trades} trades")
        print(f"NEW System: {len(signals)} signals")
        print(f"Reduction: {(1 - len(signals)/max(old_trades, 1))*100:.1f}%")
        print(f"\n💡 Trading Frequency:")
        print(f"   OLD: {old_trades/hours_back:.1f} trades/hour")
        print(f"   NEW: {len(signals)/hours_back:.2f} signals/hour")
        print(f"   YOUR ACTUAL: 9 trades / 24 hours = 0.37 trades/hour")
    except:
        pass

    # Save signals
    with open('trading_data/new_system_signals.json', 'w') as f:
        json.dump({
            'signals': signals,
            'total_signals': len(signals),
            'hours_analyzed': hours_back,
            'signals_per_hour': len(signals)/hours_back,
            'avg_quality_score': sum(s['quality_score'] for s in signals)/len(signals) if signals else 0
        }, f, indent=2, default=str)

    print(f"\n✅ Signals saved to: trading_data/new_system_signals.json")

    return signals


if __name__ == '__main__':
    import sys
    # Use ALL data if no argument, otherwise use specified hours
    hours = None if len(sys.argv) < 2 else int(sys.argv[1])
    test_new_system(hours_back=hours)
