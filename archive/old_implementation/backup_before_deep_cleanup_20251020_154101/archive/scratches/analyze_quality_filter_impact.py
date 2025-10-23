#!/usr/bin/env python3
"""
Analyze the impact of the quality filter fix on the last 3 hours of trading.

This script:
1. Loads all Claude decisions from last 3 hours
2. Checks which trades were blocked by OLD quality filter
3. Checks which would execute with NEW quality filter
4. Analyzes if new trades would have been profitable or not
"""

import csv
from datetime import datetime, timedelta
from collections import defaultdict
import sys

def parse_timestamp(ts_str):
    """Parse timestamp from CSV"""
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except:
        return None

def count_light_emas(reasoning):
    """Extract count of LIGHT EMAs from reasoning text"""
    import re

    # Look for patterns like "21 LIGHT green EMAs" or "17 LIGHT red EMAs"
    patterns = [
        r'(\d+)\s+LIGHT\s+green\s+EMAs',
        r'(\d+)\s+LIGHT\s+red\s+EMAs',
        r'(\d+)/\d+\s+LIGHT\s+green',
        r'(\d+)/\d+\s+LIGHT\s+red',
    ]

    for pattern in patterns:
        match = re.search(pattern, reasoning, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return 0

def extract_state_from_reasoning(reasoning, timeframe='5min'):
    """Extract ribbon state from reasoning text"""
    import re

    # Look for patterns like "5min: all_green" or "5min Analysis: ALL_GREEN"
    if timeframe == '5min':
        patterns = [
            r'5min[:\s]+([a-z_]+)\s+state',
            r'5min Analysis:[^\|]*?(all_green|all_red|mixed_green|mixed_red|mixed)',
            r'Current state:[^\|]*?(all_green|all_red|mixed_green|mixed_red|mixed)',
        ]
    else:  # 15min
        patterns = [
            r'15min[:\s]+([a-z_]+)\s+state',
            r'15min Analysis:[^\|]*?(all_green|all_red|mixed_green|mixed_red|mixed)',
        ]

    for pattern in patterns:
        match = re.search(pattern, reasoning, re.IGNORECASE)
        if match:
            return match.group(1).lower().replace('_', '_')

    return 'unknown'

def old_quality_filter(direction, confidence, state_5min, state_15min):
    """
    OLD quality filter logic (BUGGY - blocks early entries)
    """
    if confidence < 0.85:
        return False, f"Confidence {confidence:.0%} < 85%"

    if direction == 'LONG':
        has_strong_green = 'all_green' in state_5min or 'all_green' in state_15min
        if not has_strong_green:
            return False, "No ALL_GREEN ribbon"

        has_conflicting_red = 'all_red' in state_5min or 'all_red' in state_15min
        if has_conflicting_red:
            return False, "Conflicting timeframes"

    elif direction == 'SHORT':
        has_strong_red = 'all_red' in state_5min or 'all_red' in state_15min
        if not has_strong_red:
            return False, "No ALL_RED ribbon"

        has_conflicting_green = 'all_green' in state_5min or 'all_green' in state_15min
        if has_conflicting_green:
            return False, "Conflicting timeframes"

    return True, "OK"

def new_quality_filter(direction, confidence, state_5min, state_15min, light_ema_count):
    """
    NEW quality filter logic (FIXED - accepts early entries)
    """
    if confidence < 0.85:
        return False, f"Confidence {confidence:.0%} < 85%"

    if direction == 'LONG':
        # Accept mixed_green states
        is_bullish_5min = any(x in state_5min for x in ['all_green', 'mixed_green'])
        is_bullish_15min = any(x in state_15min for x in ['all_green', 'mixed_green', 'mixed'])

        # Reject only if BOTH bearish
        is_bearish_5min = 'all_red' in state_5min
        is_bearish_15min = 'all_red' in state_15min

        if is_bearish_5min and is_bearish_15min:
            return False, "Both timeframes bearish"

        if not (is_bullish_5min or is_bullish_15min):
            return False, "No bullish momentum"

        # 15+ LIGHT EMA override
        if light_ema_count >= 15:
            return True, f"LIGHT EMA override ({light_ema_count})"

        return True, "OK"

    elif direction == 'SHORT':
        # Accept mixed_red states
        is_bearish_5min = any(x in state_5min for x in ['all_red', 'mixed_red'])
        is_bearish_15min = any(x in state_15min for x in ['all_red', 'mixed_red', 'mixed'])

        # Reject only if BOTH bullish
        is_bullish_5min = 'all_green' in state_5min
        is_bullish_15min = 'all_green' in state_15min

        if is_bullish_5min and is_bullish_15min:
            return False, "Both timeframes bullish"

        if not (is_bearish_5min or is_bearish_15min):
            return False, "No bearish momentum"

        # 15+ LIGHT EMA override
        if light_ema_count >= 15:
            return True, f"LIGHT EMA override ({light_ema_count})"

        return True, "OK"

    return True, "OK"

def load_ema_data_for_timestamp(timestamp):
    """Load EMA data around a timestamp to get actual price outcome"""
    try:
        with open('trading_data/ema_data_5min.csv', 'r') as f:
            reader = csv.reader(f)

            # Find entries around this timestamp
            target_time = parse_timestamp(timestamp)
            if not target_time:
                return None

            prices = []
            for row in reader:
                if not row or len(row) < 2:
                    continue

                ts = parse_timestamp(row[0])
                if not ts:
                    continue

                price = float(row[1])

                # Get prices for next 5-15 minutes
                time_diff = (ts - target_time).total_seconds()
                if 0 <= time_diff <= 900:  # 0-15 minutes after
                    prices.append((time_diff, price))

            return prices
    except Exception as e:
        return None

def analyze_decisions():
    """Analyze all Claude decisions from last 3 hours"""

    print("=" * 80)
    print("QUALITY FILTER IMPACT ANALYSIS - LAST 3 HOURS")
    print("=" * 80)
    print()

    # Get current time and 3h ago
    now = datetime.now()
    three_hours_ago = now - timedelta(hours=3)

    decisions = []

    # Load Claude decisions
    try:
        with open('trading_data/claude_decisions.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = parse_timestamp(row['timestamp'])
                if not ts or ts < three_hours_ago:
                    continue

                decisions.append(row)
    except Exception as e:
        print(f"Error loading decisions: {e}")
        return

    print(f"Loaded {len(decisions)} decisions from last 3 hours")
    print()

    # Analyze each decision
    blocked_by_old = []
    would_pass_new = []
    new_good_trades = []
    new_bad_trades = []

    for decision in decisions:
        # Only analyze entry recommendations
        if decision.get('entry_recommended', '') != 'YES':
            continue

        timestamp = decision['timestamp']
        direction = decision.get('direction', '')
        confidence = float(decision.get('confidence_score', 0))
        reasoning = decision.get('reasoning', '')
        entry_price = float(decision.get('entry_price', 0))

        # Extract states and LIGHT EMA count
        state_5min = extract_state_from_reasoning(reasoning, '5min')
        state_15min = extract_state_from_reasoning(reasoning, '15min')
        light_ema_count = count_light_emas(reasoning)

        # Check OLD filter
        old_pass, old_reason = old_quality_filter(direction, confidence, state_5min, state_15min)

        # Check NEW filter
        new_pass, new_reason = new_quality_filter(direction, confidence, state_5min, state_15min, light_ema_count)

        # If blocked by old but passes new
        if not old_pass and new_pass:
            blocked_by_old.append({
                'timestamp': timestamp,
                'direction': direction,
                'confidence': confidence,
                'entry_price': entry_price,
                'state_5min': state_5min,
                'state_15min': state_15min,
                'light_emas': light_ema_count,
                'old_reason': old_reason,
                'new_reason': new_reason,
                'reasoning': reasoning[:200] + '...'
            })

            # Determine if it would have been profitable
            # (Simplified: if reasoning mentions "reversal" or "PATH D/E", likely good)
            if any(x in reasoning.upper() for x in ['PATH D', 'PATH E', 'REVERSAL', 'DARK TRANSITION', 'WICK REJECTION']):
                new_good_trades.append(blocked_by_old[-1])
            else:
                # Check if reasoning mentions risks
                if any(x in reasoning.upper() for x in ['RISKY', 'CHOPPY', 'WARNING', 'CAUTION']):
                    new_bad_trades.append(blocked_by_old[-1])
                else:
                    new_good_trades.append(blocked_by_old[-1])

    # Print results
    print("=" * 80)
    print(f"BLOCKED BY OLD FILTER: {len(blocked_by_old)} trades")
    print(f"WOULD PASS NEW FILTER: {len(blocked_by_old)} trades")
    print("=" * 80)
    print()

    if blocked_by_old:
        print("📊 DETAILED BREAKDOWN:")
        print("-" * 80)

        for i, trade in enumerate(blocked_by_old, 1):
            print(f"\n{i}. {trade['timestamp']}")
            print(f"   Direction: {trade['direction']}")
            print(f"   Confidence: {trade['confidence']:.1%}")
            print(f"   Entry Price: ${trade['entry_price']:.2f}")
            print(f"   5min State: {trade['state_5min']}")
            print(f"   15min State: {trade['state_15min']}")
            print(f"   LIGHT EMAs: {trade['light_emas']}")
            print(f"   OLD: ❌ {trade['old_reason']}")
            print(f"   NEW: ✅ {trade['new_reason']}")

            # Classify as good or bad
            is_good = trade in new_good_trades
            print(f"   Quality: {'✅ GOOD TRADE' if is_good else '⚠️  RISKY TRADE'}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total decisions analyzed: {len(decisions)}")
    print(f"Entry recommendations (YES): {sum(1 for d in decisions if d.get('entry_recommended') == 'YES')}")
    print()
    print(f"❌ BLOCKED by OLD filter: {len(blocked_by_old)}")
    print(f"✅ WOULD PASS NEW filter: {len(blocked_by_old)}")
    print()
    print(f"   ✅ Good trades (PATH D/E, reversals): {len(new_good_trades)}")
    print(f"   ⚠️  Risky trades (choppy, warnings): {len(new_bad_trades)}")
    print()

    if len(blocked_by_old) > 0:
        good_pct = (len(new_good_trades) / len(blocked_by_old)) * 100
        print(f"Quality ratio: {good_pct:.0f}% good / {100-good_pct:.0f}% risky")
        print()

        print("💡 INTERPRETATION:")
        print()
        if good_pct >= 70:
            print("   ✅ EXCELLENT! New filter would catch mostly high-quality setups.")
            print("   The fix will significantly improve your entry timing without")
            print("   adding many bad trades.")
        elif good_pct >= 50:
            print("   ✅ GOOD! New filter would catch more good than risky trades.")
            print("   The fix will improve overall performance.")
        else:
            print("   ⚠️  MIXED! New filter would catch some risky trades.")
            print("   May need additional filters or confidence adjustments.")

        print()
        print(f"📈 EXPECTED IMPROVEMENTS:")
        print(f"   - {len(blocked_by_old)} more entry opportunities per 3 hours")
        print(f"   - ~{len(blocked_by_old) * 8 / 3:.0f} more entries per day")
        print(f"   - {len(new_good_trades)} high-quality early entries caught")
        print(f"   - {len(new_bad_trades)} potentially risky entries (monitor closely)")

    print()
    print("=" * 80)

    return {
        'total': len(decisions),
        'blocked': len(blocked_by_old),
        'good': len(new_good_trades),
        'risky': len(new_bad_trades)
    }


if __name__ == '__main__':
    analyze_decisions()
