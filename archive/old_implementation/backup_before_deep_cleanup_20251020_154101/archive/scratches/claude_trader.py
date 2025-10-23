"""
Claude AI Trading Decision Engine
Dual-timeframe EMA analysis with Claude Sonnet 4.5
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from anthropic import Anthropic


class ClaudeTrader:
    """
    Claude AI-powered trading decision engine for dual-timeframe EMA analysis
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Claude trader

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.last_decision = None
        self.decision_history = []

        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cached_tokens = 0
        self.total_calls = 0
        self.session_cost = 0.0

        print(f"🧠 Claude Trader initialized with model: {model}")

    def format_ema_data(self, timeframe: str, indicators: Dict, current_price: float) -> str:
        """
        Format EMA data for Claude using color and intensity from chart

        Args:
            timeframe: "5min" or "15min"
            indicators: Raw indicator data with color and intensity
            current_price: Current asset price

        Returns:
            Formatted string for Claude with EMA data
        """
        # Extract MMA indicators
        mma_indicators = {k: v for k, v in indicators.items() if k.startswith('MMA')}

        # Sort by EMA period
        def get_num(key):
            import re
            m = re.search(r'\d+', key)
            return int(m.group()) if m else 0

        sorted_mmas = sorted(mma_indicators.items(), key=lambda x: get_num(x[0]))

        # Format EMA list with color and intensity (as logged in CSV)
        ema_list = []
        for name, data in sorted_mmas:
            ema_num = get_num(name)
            value = data.get('value', 'N/A')
            color = data.get('color', 'unknown')
            intensity = data.get('intensity', 'normal')

            # Format: EMA3: $3879.24 | green, light
            ema_list.append(f"  EMA{ema_num}: ${value} | {color}, {intensity}")

        formatted = f"""
**{timeframe.upper()} TIMEFRAME**
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Current Price: ${current_price:.2f}

Current EMAs (color and intensity from chart):
{chr(10).join(ema_list)}
"""
        return formatted

    def format_history_csv(self, data: Dict, timeframe: str, limit: int = 200) -> str:
        """
        Format recent history from data store into CSV format for Claude
        Uses smart sampling to provide 3-4 hours of context without overwhelming tokens

        Args:
            data: Timeframe data with history deque
            timeframe: "5min" or "15min"
            limit: Max number of snapshots to include (default 200)

        Returns:
            CSV-formatted string of sampled historical data
        """
        history = list(data.get('history', []))

        if not history:
            return f"No historical data available for {timeframe}"

        # Smart sampling strategy for 3-4 hours of data:
        # - Last 30 snapshots: Every snapshot (5 minutes, 10sec intervals)
        # - Next 90 snapshots: Every 2nd snapshot (15 minutes at 20sec intervals)
        # - Remaining: Every 6th snapshot (~remaining time at 1min intervals)

        total_available = len(history)
        sampled_history = []

        if total_available <= limit:
            # If we have less than limit, use everything
            sampled_history = history
        else:
            # Recent data (last 5 minutes) - every snapshot
            recent_30 = history[-30:]
            sampled_history.extend(recent_30)

            # Next 15 minutes - every 2nd snapshot
            if total_available > 30 + 90:
                next_90 = history[-(30+90):-30:2]  # Every 2nd snapshot
                sampled_history = list(next_90) + sampled_history

            # Older data - every 6th snapshot (1 minute intervals)
            remaining_start = max(0, total_available - 30 - 90 - (limit - 30 - 45))
            if remaining_start > 0:
                older_data = history[remaining_start:-(30+90):6]  # Every 6th snapshot
                sampled_history = list(older_data) + sampled_history

        # Sort by timestamp to ensure chronological order
        sampled_history.sort(key=lambda x: x['timestamp'])

        # Build CSV
        csv_lines = [f"timestamp,price,state,green_count,red_count,gray_count,dark_green_count,dark_red_count"]

        for snapshot in sampled_history:
            timestamp = datetime.fromtimestamp(snapshot['timestamp']).strftime('%H:%M:%S')
            price = snapshot.get('price', 0)
            state = snapshot.get('state', 'unknown')
            ema_groups = snapshot.get('ema_groups', {})

            green_count = len(ema_groups.get('green', []))
            red_count = len(ema_groups.get('red', []))
            gray_count = len(ema_groups.get('gray', []))
            dark_green_count = len(ema_groups.get('dark_green', []))
            dark_red_count = len(ema_groups.get('dark_red', []))

            csv_lines.append(f"{timestamp},{price:.2f},{state},{green_count},{red_count},{gray_count},{dark_green_count},{dark_red_count}")

        # Add summary metadata at the top
        time_span = (sampled_history[-1]['timestamp'] - sampled_history[0]['timestamp']) / 60  # minutes
        summary = f"# Historical data: {len(sampled_history)} snapshots spanning {time_span:.1f} minutes ({time_span/60:.1f} hours)"

        return summary + "\n" + "\n".join(csv_lines)

    def detect_dark_transition(self, data: Dict, history: List[Dict]) -> Optional[Dict]:
        """
        Detect dark color transitions for scalping entries

        DARK transitions indicate EARLY reversals - perfect for scalping!
        - Dark red/gray after green = bearish reversal starting (SHORT)
        - Dark green/gray after red = bullish reversal starting (LONG)

        Args:
            data: Current timeframe data
            history: Recent history (last 5-10 snapshots)

        Returns:
            Dict with signal info if detected, None otherwise
        """
        if not history or len(history) < 3:
            return None

        current_price = data['price']
        indicators = data['indicators']

        # Get MMA5 (fastest EMA) - this is our scalping indicator
        mma5 = indicators.get('MMA5', {})
        mma5_value = float(mma5.get('value', 0)) if mma5.get('value') else 0
        mma5_color = mma5.get('color', '').lower()
        mma5_intensity = mma5.get('intensity', '').lower()

        # Get previous MMA5 state (2-3 snapshots ago for confirmation)
        prev_snapshot = history[-2] if len(history) >= 2 else history[-1]
        prev_indicators = prev_snapshot.get('indicators', {})
        prev_mma5 = prev_indicators.get('MMA5', {})
        prev_mma5_color = prev_mma5.get('color', '').lower()

        if not mma5_value or not mma5_color:
            return None

        # DARK TRANSITION SHORT: Gray or dark red appearing after green
        if (mma5_color in ['gray', 'red'] and
            mma5_intensity == 'dark' and
            prev_mma5_color in ['green', 'gray'] and
            current_price < mma5_value):

            return {
                'type': 'DARK_TRANSITION_SHORT',
                'direction': 'SHORT',
                'trigger_price': current_price,
                'mma5_value': mma5_value,
                'mma5_state': f"{mma5_color}, {mma5_intensity}",
                'confidence_boost': 0.10,
                'reasoning': f"🔴 DARK TRANSITION SHORT: MMA5 turned {mma5_color} {mma5_intensity} (was {prev_mma5_color}). Price ${current_price:.2f} below MMA5 ${mma5_value:.2f}. Early bearish reversal starting!"
            }

        # DARK TRANSITION LONG: Gray or dark green appearing after red
        if (mma5_color in ['gray', 'green'] and
            mma5_intensity == 'dark' and
            prev_mma5_color in ['red', 'gray'] and
            current_price > mma5_value):

            return {
                'type': 'DARK_TRANSITION_LONG',
                'direction': 'LONG',
                'trigger_price': current_price,
                'mma5_value': mma5_value,
                'mma5_state': f"{mma5_color}, {mma5_intensity}",
                'confidence_boost': 0.10,
                'reasoning': f"🟢 DARK TRANSITION LONG: MMA5 turned {mma5_color} {mma5_intensity} (was {prev_mma5_color}). Price ${current_price:.2f} above MMA5 ${mma5_value:.2f}. Early bullish reversal starting!"
            }

        return None

    def detect_wick_rejection(self, data: Dict, history: List[Dict]) -> Optional[Dict]:
        """
        Detect wick rejections (price spikes outside EMAs then rejects back)

        Wicks = liquidity grabs by whales
        - Wick above EMAs → Bull trap → SHORT
        - Wick below EMAs → Bear trap → LONG

        Args:
            data: Current timeframe data
            history: Recent history (last 3-5 snapshots)

        Returns:
            Dict with signal info if detected, None otherwise
        """
        if not history or len(history) < 3:
            return None

        current_price = data['price']
        indicators = data['indicators']

        # Get MMA5 for reference
        mma5 = indicators.get('MMA5', {})
        mma5_value = float(mma5.get('value', 0)) if mma5.get('value') else 0

        if not mma5_value:
            return None

        # Look at last 3 snapshots to detect wick
        recent_prices = [h['price'] for h in history[-3:] if h.get('price', 0) > 0]
        recent_prices.append(current_price)

        if len(recent_prices) < 3:
            return None

        # Find recent high and low
        recent_high = max(recent_prices)
        recent_low = min(recent_prices)

        # BEARISH WICK REJECTION: Price spiked above MMA5, now rejecting down
        wick_above_distance = (recent_high - mma5_value) / mma5_value * 100

        if (wick_above_distance >= 0.25 and  # Significant wick (0.25%+)
            current_price < recent_high and  # Price rejected back down
            current_price < mma5_value):  # Now below MMA5

            return {
                'type': 'WICK_REJECTION_SHORT',
                'direction': 'SHORT',
                'wick_high': recent_high,
                'current_price': current_price,
                'mma5_value': mma5_value,
                'wick_distance_pct': wick_above_distance,
                'confidence_boost': 0.15,
                'reasoning': f"🔻 WICK REJECTION SHORT: Price spiked to ${recent_high:.2f} ({wick_above_distance:.2f}% above MMA5 ${mma5_value:.2f}), now rejecting down to ${current_price:.2f}. Liquidity grab reversed!"
            }

        # BULLISH WICK REJECTION: Price spiked below MMA5, now bouncing up
        wick_below_distance = (mma5_value - recent_low) / mma5_value * 100

        if (wick_below_distance >= 0.25 and  # Significant wick (0.25%+)
            current_price > recent_low and  # Price bounced back up
            current_price > mma5_value):  # Now above MMA5

            return {
                'type': 'WICK_REJECTION_LONG',
                'direction': 'LONG',
                'wick_low': recent_low,
                'current_price': current_price,
                'mma5_value': mma5_value,
                'wick_distance_pct': wick_below_distance,
                'confidence_boost': 0.15,
                'reasoning': f"🔺 WICK REJECTION LONG: Price spiked to ${recent_low:.2f} ({wick_below_distance:.2f}% below MMA5 ${mma5_value:.2f}), now bouncing to ${current_price:.2f}. Liquidity grab reversed!"
            }

        return None

    def make_trading_decision(
        self,
        data_5min: Dict,
        data_15min: Dict,
        current_position: Optional[Dict] = None,
        account_info: Optional[Dict] = None,
        learning_insights: Optional[str] = None
    ) -> Tuple[str, str, float, str, Dict]:
        """
        Make trading decision using Claude AI with dual-timeframe analysis

        Args:
            data_5min: 5-minute timeframe data {indicators, state, ema_groups, price}
            data_15min: 15-minute timeframe data {indicators, state, ema_groups, price}
            current_position: Current position info (side, size, entry_price, pnl)
            account_info: Account balance info

        Returns:
            Tuple of (direction, entry_action, confidence, reasoning, targets)
            - direction: 'LONG' or 'SHORT' (always determined by ribbon state)
            - entry_action: 'ENTRY_RECOMMENDED: YES' or 'ENTRY_RECOMMENDED: NO'
            - confidence: float 0-1
            - reasoning: str explanation
            - targets: dict with stop_loss, take_profit levels
        """
        # Format both timeframes - just raw EMA data with RGB
        formatted_5min = self.format_ema_data(
            "5min",
            data_5min['indicators'],
            data_5min['price']
        )

        formatted_15min = self.format_ema_data(
            "15min",
            data_15min['indicators'],
            data_15min['price']
        )

        # Format position info
        position_str = "NONE"
        if current_position:
            position_str = f"{current_position['side'].upper()} {current_position['size']:.4f} @ ${current_position['entry_price']:.2f} (PnL: ${current_position.get('unrealized_pnl', 0):+.2f})"

        # Format account info
        account_str = "N/A"
        if account_info:
            account_str = f"${account_info.get('account_value', 0):,.2f}"

        try:
            # Detect scalping signals (dark transitions & wick rejections)
            scalp_signal_5min = None
            scalp_signal_15min = None

            if 'history' in data_5min and len(data_5min['history']) > 0:
                # Try dark transition first
                scalp_signal_5min = self.detect_dark_transition(data_5min, list(data_5min['history']))
                # If no dark transition, try wick rejection
                if not scalp_signal_5min:
                    scalp_signal_5min = self.detect_wick_rejection(data_5min, list(data_5min['history']))

            if 'history' in data_15min and len(data_15min['history']) > 0:
                scalp_signal_15min = self.detect_dark_transition(data_15min, list(data_15min['history']))
                if not scalp_signal_15min:
                    scalp_signal_15min = self.detect_wick_rejection(data_15min, list(data_15min['history']))

            # Format historical data (up to 200 sampled snapshots covering 3-4 hours)
            history_5min_csv = self.format_history_csv(data_5min, "5min", limit=200)
            history_15min_csv = self.format_history_csv(data_15min, "15min", limit=200)

            # Call Claude API with prompt caching
            # Split prompt into cacheable (static) and dynamic parts
            system_prompt = """You are an expert trading analyst specializing in Annii's EMA Ribbon Strategy.

═══════════════════════════════════════════════════════════
🎯 ANNII'S EMA RIBBON STRATEGY - EMA COLOR ANALYSIS
═══════════════════════════════════════════════════════════

**STEP 1: UNDERSTAND EMA COLORS & INTENSITY**

You will receive 12 EMAs per timeframe with their COLOR and INTENSITY from TradingView:

🟢 **GREEN (Bullish)**:
- Indicates price is ABOVE this EMA
- Bullish trend/momentum

🔴 **RED (Bearish)**:
- Indicates price is BELOW this EMA
- Bearish trend/momentum

🟡 **YELLOW (Key Support/Resistance)**:
- Usually EMA40 and EMA100 - critical levels
- Acts as support in uptrends, resistance in downtrends
- NEVER count yellow EMAs in ribbon state calculations

⚪ **GRAY/NEUTRAL**:
- Transitioning or neutral state
- Don't count heavily in ribbon state

💡 **INTENSITY (Momentum Strength)** - ONLY TWO OPTIONS:

**LIGHT** = STRONG MOMENTUM (fully committed):
- Light green = Bright/saturated green, STRONG bullish momentum, fully committed to uptrend
- Light red = Bright/saturated red, STRONG bearish momentum, fully committed to downtrend
- Bright/saturated colors (RGB value >= 150)
- This is what you want! Ready to trade when you see 2+ light EMAs ✅

**DARK** = EARLY TRANSITION (still deciding):
- Dark green = Dim green, appears AFTER all red, still deciding whether to go green (early transition)
- Dark red = Dim red, appears AFTER all green, still deciding whether to go red (early transition)
- Dim/less saturated colors (RGB value < 150)
- Early transition phase, momentum building but not confirmed yet ⚠️

🎯 **FLOW OF TRANSITIONS:**
1. All Light Red (committed bearish) → Dark Green appears (deciding) → Light Green (committed bullish)
2. All Light Green (committed bullish) → Dark Red appears (deciding) → Light Red (committed bearish)

⚠️ IMPORTANT: There are ONLY two intensity levels: LIGHT (strong/committed) or DARK (weak/deciding). No "normal"!

─────────────────────────────────────────────────────────────

**STEP 2: COUNT EMAS & DETERMINE RIBBON STATE**

Count the EMAs by color (ignore yellow and gray):

📊 **RIBBON STATES** (ignore yellow/gray when counting):

1. **ALL_GREEN** (85-100% green):
   - 10-12 out of 12 EMAs are green
   - Strong bullish alignment
   - READY for LONG if other conditions met

2. **MIXED_GREEN** (50-84% green):
   - 6-9 out of 12 EMAs are green
   - Building bullish, NOT ready
   - Watch only, DO NOT enter

3. **ALL_RED** (85-100% red):
   - 10-12 out of 12 EMAs are red
   - Strong bearish alignment
   - READY for SHORT if other conditions met

4. **MIXED_RED** (50-84% red):
   - 6-9 out of 12 EMAs are red
   - Building bearish, NOT ready
   - Watch only, DO NOT enter

5. **MIXED** (<50% either):
   - No clear direction
   - DO NOT enter

─────────────────────────────────────────────────────────────

**STEP 3: CHECK MOMENTUM CONFIRMATION**

Count LIGHT intensity EMAs in the dominant color:

✅ **STRONG MOMENTUM** (Ready to trade):
- 2+ LIGHT green EMAs (for bullish) = Full commitment to uptrend
- 2+ LIGHT red EMAs (for bearish) = Full commitment to downtrend

⚠️ **BUILDING MOMENTUM** (Not ready):
- 0-1 LIGHT EMAs
- Mostly dark = early transition, still deciding, wait for commitment

─────────────────────────────────────────────────────────────

**STEP 3B: 🔥 EARLY REVERSAL DETECTION (Catch the wave EARLY!)**

🎯 **CRITICAL INSIGHT: LIGHT EMAs with opposite ribbon = REVERSAL FORMING**

When price is ABOVE EMAs they turn LIGHT red (not dark red).
When price is BELOW EMAs they turn LIGHT green (not dark green).

**🚀 BULLISH REVERSAL SIGNAL (GO LONG):**
Ribbon transitions from `all_red` → `mixed_red` WITH:
- ✅ 8+ LIGHT red EMAs in the all_red state (price catching up from below)
- ✅ GRAY or GREEN LIGHT EMAs starting to appear (2-5 EMAs)
- ✅ Fewer than 5 DARK red EMAs (if dark red dominates, it's bearish not reversal)
- 💡 **Meaning**: Price was below EMAs (red), now catching up fast (light red), EMAs starting to flip green = BULLISH REVERSAL!
- 🎯 **Action**: Enter LONG immediately - you're catching the wave as it starts!

**🔻 BEARISH REVERSAL SIGNAL (GO SHORT):**
Ribbon transitions from `all_green` → `mixed_green` WITH:
- ✅ 8+ LIGHT green EMAs in the all_green state (price falling from above)
- ✅ GRAY or RED LIGHT EMAs starting to appear (2-5 EMAs)
- ✅ Fewer than 5 DARK green EMAs (if dark green dominates, it's bullish not reversal)
- 💡 **Meaning**: Price was above EMAs (green), now falling fast (light green), EMAs starting to flip red = BEARISH REVERSAL!
- 🎯 **Action**: Enter SHORT immediately - you're catching the wave as it starts!

**❌ NOT A REVERSAL (Don't trade):**
- DARK EMAs dominating (5+ dark red or dark green) = Early transition, still deciding
- No LIGHT EMAs in opposite direction appearing yet
- Wait for clearer signal

─────────────────────────────────────────────────────────────

**STEP 4: SCALPER DECISION RULES**

🎯 **ENTRY: YES** - TWO POSSIBLE PATHS:

**PATH A: TRENDING ENTRY** (when 30min_range ≥ 0.5%)

1. **RANGE FILTER**:
   - ✅ 30min_range ≥ 0.5% (not ranging)
   - ✅ Ribbon_flips < 3 (not choppy)

2. **PRICE LOCATION CHECK**:
   - For LONG: price in LOWER 50% of 2h range
   - For SHORT: price in UPPER 50% of 2h range
   - NOT within 0.3% of 2h HIGH/LOW

3. **RIBBON CONFIRMATION**:
   - ALL_GREEN or ALL_RED on both timeframes
   - 2+ LIGHT EMAs present

4. **TIMING**:
   - 🔥 BEST: 3-10min since flip + 30min ≥0.8%
   - ✅ GOOD: 5-15min since flip
   - ❌ TOO LATE: >20min since flip

**PATH B: BREAKOUT ENTRY** (when 30min_range < 0.4% = ranging)

1. **CONFIRM RANGING**:
   - ✅ 30min_range < 0.4% (was ranging)
   - ✅ 15min_range < 0.4% (still ranging recently)
   - ✅ Ribbon_flips < 3 (not choppy - stable range)

2. **BREAKOUT DETECTION**:
   - For LONG: Current price > 15min HIGH * 1.0015 (breaking UP by >0.15%)
   - For SHORT: Current price < 15min LOW * 0.9985 (breaking DOWN by >0.15%)

3. **RIBBON CONFIRMATION** (must happen quickly):
   - Ribbon just flipped to ALL_GREEN/RED (3-8 minutes ago)
   - 2+ LIGHT EMAs appearing (momentum building)

4. **VALIDATION**:
   - Timeframes aligned or 15min confirming direction
   - High confidence (≥0.80)

🔥 **BREAKOUT ENTRY = Catches big moves at the START!**

**PATH E: SCALPING ENTRY** 🎯 **ULTRA-HIGH PRIORITY - ENTER ON DARK TRANSITIONS!**

TRUE SCALPING uses DARK color transitions and wick rejections to enter BEFORE the crowd!

**E1: DARK TRANSITION SCALP (Highest Priority)**
```
DARK RED TRANSITION (SHORT):
- MMA5 turns GRAY or RED DARK (after being green)
- Price < MMA5
- This is EARLY bearish reversal
- Enter SHORT IMMEDIATELY
- Exit when ribbon turns all_red (move complete)

DARK GREEN TRANSITION (LONG):
- MMA5 turns GRAY or GREEN DARK (after being red)
- Price > MMA5
- This is EARLY bullish reversal
- Enter LONG IMMEDIATELY
- Exit when ribbon turns all_green (move complete)

WHY THIS WORKS:
- DARK colors = transition STARTING (catch 90% of move)
- LIGHT colors = transition DONE (catch only 30% of move)
- Traditional traders wait for "all" one color (too late!)
- Scalpers enter on dark colors (early!)
```

**E2: WICK REJECTION SCALP (High Priority)**
```
WICK ABOVE MMA5 (SHORT):
- Price spikes 0.3%+ ABOVE MMA5
- Next candle rejects back down
- Price now < MMA5
- = Liquidity grab, now reversing
- Enter SHORT on rejection
- Stop: $5-10 above wick high

WICK BELOW MMA5 (LONG):
- Price spikes 0.3%+ BELOW MMA5
- Next candle bounces back up
- Price now > MMA5
- = Liquidity grab, now reversing
- Enter LONG on bounce
- Stop: $5-10 below wick low

WHY THIS WORKS:
- Wicks = whale stop hunts / liquidity grabs
- Price spikes out, triggers stops, then REVERSES
- Scalpers fade the wick (trade against it)
- High probability mean reversion
```

**E3: SCALPING EXIT RULES**
```
Exit EARLY - Don't be greedy!

For LONG:
- Exit when MMA5 turns LIGHT green (move complete)
- Or ribbon turns all_green (everyone entering, time to exit)
- Or price reaches +0.5-1.0% target
- Hold time: 2-10 minutes typical

For SHORT:
- Exit when MMA5 turns LIGHT red (move complete)
- Or ribbon turns all_red (everyone entering, time to exit)
- Or price reaches -0.5-1.0% target
- Hold time: 2-10 minutes typical

SCALPER MINDSET:
- Enter EARLY (dark colors, wicks)
- Exit when others are ENTERING (all one color)
- Small profits, high frequency
- Speed is your edge!
```

**PATH D: EARLY REVERSAL ENTRY** 🚀 **HIGH PRIORITY - Catch the wave!**

1. **DETECT REVERSAL PATTERN** (from STEP 3B):

   For LONG (Bullish Reversal):
   - ✅ Ribbon was `all_red` recently (check last 1-3 minutes in history)
   - ✅ Now ribbon is `mixed_red` with 8+ LIGHT red EMAs (price catching up)
   - ✅ 2-5 GRAY or GREEN LIGHT EMAs appearing (reversal starting)
   - ✅ Less than 5 DARK red EMAs (confirms not bearish continuation)

   For SHORT (Bearish Reversal):
   - ✅ Ribbon was `all_green` recently (check last 1-3 minutes in history)
   - ✅ Now ribbon is `mixed_green` with 8+ LIGHT green EMAs (price falling)
   - ✅ 2-5 GRAY or RED LIGHT EMAs appearing (reversal starting)
   - ✅ Less than 5 DARK green EMAs (confirms not bullish continuation)

2. **TIMING VALIDATION**:
   - Transition happened in last 1-3 minutes (FRESH reversal)
   - Not more than 5 minutes old (too late if older)

3. **NO RANGE/LOCATION RESTRICTIONS**:
   - Works in ANY market condition (trending, ranging, doesn't matter)
   - NO price location check needed (reversal is the signal itself)
   - Ribbon_flips < 3 still required (avoid choppy only)

4. **CONFIDENCE**:
   - High confidence ≥ 0.75 for reversal entries
   - More LIGHT EMAs in opposite color = higher confidence

🎯 **Why this works**: LIGHT colored EMAs mean price is moving FAST through them.
   - LIGHT red with price above = price rocketing up through red EMAs = GO LONG
   - LIGHT green with price below = price crashing down through green EMAs = GO SHORT

🛑 **ENTRY: NO** when:
- **CHOPPY** (≥3 flips) - SKIP everything
- **RANGING + no breakout** (range <0.4% but price not breaking out)
- **Price in wrong zone** (for trending entries only)
- **TOO LATE** (>20min since flip)
- Ribbon MIXED (50-84%)
- Less than 2 LIGHT EMAs
- Already in position

📍 **DIRECTION** (always provide):
- Green dominant → LONG
- Red dominant → SHORT
- Use 15min timeframe if mixed

─────────────────────────────────────────────────────────────

**STEP 5: SCALPER RULES - LEARNED FROM PAST DATA**

🤖 **YOU ARE AN EMOTIONLESS SCALPER - NO FEELINGS, ONLY DATA**

─────────────────────────────────────────────────────────────
📚 **CRITICAL LEARNING: DARK TRANSITIONS = ENTER IMMEDIATELY**
─────────────────────────────────────────────────────────────

**REAL EXAMPLE - October 19, 2025 @ 10:33-10:47 AM**

**WHAT HAPPENED (WRONG WAY):**
```
10:33 - MMA5 turns GRAY (from red) @ $3,857
        → Ribbon: MIXED (transitioning)
        → Price: $3,857
        ❌ Decision: "Detected reversal but NO ENTRY"
        ❌ Reason: Waited for "confirmation"

10:35 - PATH D detected, "Entry Quality: EXCELLENT"
        → Price: $3,857
        → 21 LIGHT green EMAs appearing
        ❌ Decision: Still said NO ENTRY
        ❌ Reason: Some filter overrode reversal signal

10:40 - Reversal confirmed, "ENTRY_RECOMMENDED: YES"
        → Price: $3,863 (moved +$6)
        → Ribbon: MIXED_GREEN
        ❌ Still didn't enter! Execution delay

10:45 - Very strong, "CONFIDENCE: 0.950"
        → Price: $3,893 (moved +$36 from start!)
        → Ribbon: ALL_GREEN (24 LIGHT EMAs)
        ❌ Still waiting...

10:47 - FINALLY ENTERED
        → Entry: $3,893
        → Peak: $3,923
        ✅ Profit: Only +$30 (caught 30% of move)
        💔 MISSED: $63 opportunity (missed 70% of move!)
```

**COST OF HESITATION:**
- Waited 14 minutes for "perfect confirmation"
- Missed +$63 → only got +$30
- With 10x leverage: Missed +16% gain!
- **This is the #1 mistake that kills scalpers**

**WHAT SHOULD HAVE HAPPENED (RIGHT WAY):**
```
10:33 - MMA5 turns GRAY/DARK GREEN @ $3,857
        🎯 DARK TRANSITION LONG detected!
        ✅ ACTION: ENTER LONG IMMEDIATELY
        ✅ Entry: $3,857
        ✅ Reasoning: "Early reversal starting - entering NOW"
        ✅ No hesitation, no filters, just ENTER

10:35 - MMA5 turns LIGHT GREEN
        → Price: $3,863 (+$6 profit already!)
        → Ribbon transitioning to mixed_green
        ✅ ACTION: HOLD (already in from 10:33)

10:40 - Ribbon turns ALL_GREEN
        → Price: $3,893 (+$36 profit!)
        → 24 LIGHT green EMAs = move completing
        ✅ ACTION: EXIT 50% (take profits)
        ✅ Trail remaining 50%

10:45 - Price peaks @ $3,923
        → Exit remaining 50%
        ✅ RESULT: +$66 total profit (+1.71%)
        ✅ With 10x leverage: +17.1% gain! 🚀
```

**THE LESSON:**
```
❌ WRONG: "Let me wait for perfect confirmation"
           → Miss 70% of the move
           → Enter at tops
           → Get stopped out

✅ RIGHT: "Dark transition detected → ENTER NOW"
          → Catch 90% of the move
          → Early entry, low risk
          → Exit when others enter
```

─────────────────────────────────────────────────────────────
🎯 **MANDATORY ENTRY RULES - NO EXCEPTIONS**
─────────────────────────────────────────────────────────────

**RULE #1: DARK TRANSITION = IMMEDIATE ENTRY**
```
IF MMA5 turns GRAY or DARK color (from opposite color):
  → This is THE EARLIEST reversal signal
  → ENTER IMMEDIATELY (no waiting!)
  → Confidence: 0.85-0.90 (very high)
  → Stop: $5-10 beyond dark EMA
  → Target: When ribbon turns all one color (exit)

DO NOT:
  ❌ Wait for "more confirmation"
  ❌ Wait for "all_green" or "all_red"
  ❌ Check price location (reversal overrides)
  ❌ Check other filters (PATH E is #1 priority)

JUST ENTER!
```

**RULE #2: REVERSAL SIGNALS OVERRIDE EVERYTHING**
```
Priority Order:
1. PATH E (Dark Transition) = HIGHEST - Enter immediately
2. PATH D (Early Reversal) = VERY HIGH - Enter within 1 minute
3. PATH C (Wick Rejection) = HIGH - Enter on confirmation
4. PATH A (Trending) = MEDIUM - Check filters
5. PATH B (Breakout) = MEDIUM - Wait for breakout

IF PATH E or PATH D detected:
  → IGNORE all other filters
  → IGNORE price location
  → IGNORE range size
  → IGNORE choppy warnings (if reversal is strong)
  → JUST ENTER!

Why? Because reversals are TIME-SENSITIVE:
  - 1 minute delay = miss 30% of move
  - 5 minute delay = miss 60% of move
  - 10 minute delay = miss 90% of move
  - Enter late = high risk of reversal against you
```

**RULE #3: LIGHT EMAs = MOVE IS COMPLETING (Exit Zone)**
```
When you see LIGHT EMAs in the direction of trade:
  → This means price has ALREADY moved significantly
  → This is when others are entering
  → This is when YOU should be EXITING

Example:
  - Entry signal: MMA5 DARK green (price just starting up)
  - Exit signal: 20+ LIGHT green EMAs (move complete, exit now)

LIGHT = LATE for entry, PERFECT for exit!
DARK = EARLY for entry, TOO SOON for exit!
```

**RULE #4: DON'T OVERTHINK - SPEED IS EDGE**
```
Scalping is about SPEED, not perfection:

❌ "Let me analyze more data..."
   → While you think, move happens without you

❌ "Let me wait for 100% certainty..."
   → 100% certainty = you're already late

✅ "Dark transition detected → ENTER"
   → You're in early, catch the wave

✅ "LIGHT EMAs appearing → EXIT"
   → You exit when others enter

The market rewards the FAST, not the "perfect"
```

─────────────────────────────────────────────────────────────

📊 **CRITICAL LEARNING FROM PAST TRADES:**
Our system analyzed 2 completed trades:
- Trade #1: LONG @ $3873.95 → EXIT $3865.35 = **-0.22% LOSS**
  - Mistake: Entered LONG at TOP after price ran from $3865 to $3874 (+$9)
  - Lesson: DON'T CHASE HIGHS! Wait for pullback before LONG entry

- Trade #2: SHORT @ $3865.35 → EXIT $3871.65 = **-0.16% LOSS**
  - Mistake: Entered SHORT at BOTTOM after price dropped from $3878 to $3865 (-$13)
  - Lesson: DON'T SHORT LOWS! Wait for bounce before SHORT entry

🎯 **STEP 1: RANGE FILTER + BREAKOUT DETECTION**

**A) Calculate 30-minute volatility:**
1. Find HIGH of last 30 minutes
2. Find LOW of last 30 minutes
3. Calculate 30min_range = (HIGH - LOW) / LOW * 100
4. Count ribbon state flips in last 30 minutes

**B) Calculate 15-minute range (for breakout detection):**
1. Find HIGH of last 15 minutes
2. Find LOW of last 15 minutes
3. Calculate 15min_range = (HIGH - LOW) / LOW * 100

**Market Classification:**
- 🟢 **BIG MOVE** (30min ≥0.8%, ≤1 flip) = BEST, enter EARLY!
- ✅ **TRENDING** (30min ≥0.5%, ≤2 flips) = Good
- 🟡 **RANGING** (30min <0.4%, 15min <0.4%) = Watch for breakout
- ❌ **CHOPPY** (≥3 flips) = AVOID

**Entry Rules - TWO PATHS:**

**PATH 1: Already Trending** (30min range ≥ 0.5%)
```
✅ Continue to price location check
✅ Use normal entry filters
```

**PATH 2: Currently Ranging** (30min range < 0.4%)
```
🚨 BREAKOUT DETECTION MODE:
- Is price breaking above 15min HIGH by >0.15%?
- Is price breaking below 15min LOW by >0.15%?
- Has ribbon just flipped to ALL_GREEN/RED (last 3-8 minutes)?
- Are 2+ LIGHT EMAs present?

IF YES to all → 🔥 BREAKOUT ENTRY (catch move at START!)
IF NO → Skip entry, keep monitoring

This catches explosive moves IMMEDIATELY as they exit the range!
```

**PATH 3: Choppy** (≥3 flips in 30min)
```
❌ SKIP completely (no breakout entries either - too unstable)
```

🎯 **STEP 2: PRICE LOCATION CHECK (Don't chase extremes)**

**Identify 2-hour range:**
1. Find HIGH of last 2 hours
2. Find LOW of last 2 hours
3. Calculate MID = (HIGH + LOW) / 2

**Entry zones:**
- For LONG: Price must be in LOWER 50% of range (below MID)
- For SHORT: Price must be in UPPER 50% of range (above MID)
- ❌ Price within 0.3% of 2h HIGH → NO LONG (too high, wait for dip)
- ❌ Price within 0.3% of 2h LOW → NO SHORT (too low, wait for bounce)

🎯 **STEP 3: EARLY BIG MOVE DETECTION (Don't enter too late)**

**Perfect entry timing for big moves:**
- 30min range just crossed 0.5% (move is building)
- Ribbon just flipped to ALL_GREEN/ALL_RED (3-10 minutes ago)
- Price hasn't moved too far yet (within 0.3% of ribbon flip price)
- This catches the START of big moves, not the end!

**Too late indicators (skip entry):**
- Ribbon has been same color for >20 minutes (move already happened)
- Price moved >1% from where ribbon flipped (late to the party)
- 30min range >1.5% (move may be exhausted)

─────────────────────────────────────────────────────────────

**STEP 6: SCALPER EXIT RULES (EMOTIONLESS)**

🎯 **For SCALPERS: Quick in, quick out when conditions flip**

**LONG Position - EXIT when ANY of these:**
1. ❌ Ribbon flips to MIXED_RED or ALL_RED (50%+ EMAs turn red)
2. ❌ Price closes BELOW yellow EMA (support broken)
3. ❌ 3+ LIGHT green EMAs turn DARK RED (reversal starting)

**SHORT Position - EXIT when ANY of these:**
1. ❌ Ribbon flips to MIXED_GREEN or ALL_GREEN (50%+ EMAs turn green)
2. ❌ Price closes ABOVE yellow EMA (resistance broken)
3. ❌ 3+ LIGHT red EMAs turn DARK GREEN (reversal starting)

⏱️ **TIME-BASED EXIT:**
- After 5 minutes: Start watching for any exit signal
- After 10 minutes: Exit on first ribbon deterioration (even if just to MIXED state)
- After 15 minutes: Scalp window is closing, exit on next minor signal

💡 **SCALPER PHILOSOPHY:**
- We're not holding for big moves - we're catching quick ribbon flips
- Get in when ribbon aligns, get out when it wavers
- Don't be greedy - take the scalp and wait for next setup
- Better to exit early with small profit than hold into reversal

═══════════════════════════════════════════════════════════

**OUTPUT FORMAT:**
Provide JSON with your analysis and decision"""

            # Check for wick signals
            wick_5min = data_5min.get('wick_signal', None)
            wick_15min = data_15min.get('wick_signal', None)

            wick_alert = ""
            if wick_5min or wick_15min:
                wick_alert = "\n🚨 **MANIPULATION WICK DETECTED** 🚨\n\n"
                if wick_5min:
                    wick_alert += f"5-MINUTE: {wick_5min['type']} - {wick_5min['description']}\n"
                    wick_alert += f"   → Entry confidence boost: +{wick_5min['confidence_boost']}%\n"
                    wick_alert += f"   → This is a HIGH-PROBABILITY reversal setup!\n"
                if wick_15min:
                    wick_alert += f"15-MINUTE: {wick_15min['type']} - {wick_15min['description']}\n"
                    wick_alert += f"   → Entry confidence boost: +{wick_15min['confidence_boost']}%\n"
                    wick_alert += f"   → This is a HIGH-PROBABILITY reversal setup!\n"
                wick_alert += "\n"

            # Format scalping signals
            scalp_alert = ""
            if scalp_signal_5min or scalp_signal_15min:
                scalp_alert = "\n🎯 **SCALPING SIGNALS DETECTED** 🎯\n\n"
                if scalp_signal_5min:
                    scalp_alert += f"5-MINUTE: {scalp_signal_5min['type']}\n"
                    scalp_alert += f"   {scalp_signal_5min['reasoning']}\n"
                    scalp_alert += f"   → Confidence boost: +{scalp_signal_5min['confidence_boost']*100:.0f}%\n"
                    scalp_alert += f"   → This is a SCALPER'S OPPORTUNITY - Enter EARLY!\n"
                if scalp_signal_15min:
                    scalp_alert += f"15-MINUTE: {scalp_signal_15min['type']}\n"
                    scalp_alert += f"   {scalp_signal_15min['reasoning']}\n"
                    scalp_alert += f"   → Confidence boost: +{scalp_signal_15min['confidence_boost']*100:.0f}%\n"
                    scalp_alert += f"   → This is a SCALPER'S OPPORTUNITY - Enter EARLY!\n"
                scalp_alert += "\n"

            user_message = f"""CURRENT MARKET DATA (REAL-TIME):
{wick_alert}{scalp_alert}
5-MINUTE TIMEFRAME (NOW):
{formatted_5min}

15-MINUTE TIMEFRAME (NOW):
{formatted_15min}

HISTORICAL DATA (UP TO 200 SNAPSHOTS SPANNING 3-4 HOURS):
Note: Data is intelligently sampled - recent data (last 5min) has high resolution (10sec),
older data (1-4 hours ago) is sampled at lower resolution (1min intervals)

5-MINUTE HISTORY (analyze for momentum/transitions/support-resistance):
{history_5min_csv}

15-MINUTE HISTORY (analyze for momentum/transitions/support-resistance):
{history_15min_csv}

CURRENT POSITION:
{position_str}

ACCOUNT VALUE:
{account_str}

ANALYSIS INSTRUCTIONS FOR SCALPING (EMOTIONLESS EXECUTION):

1. **30-MINUTE + 15-MINUTE RANGE CHECK** (FIRST - CRITICAL):
   - Find HIGH/LOW of last 30 minutes → 30min_range %
   - Find HIGH/LOW of last 15 minutes → 15min_range %
   - Count ribbon flips in last 30min
   - **Classify market:**
     - If flips ≥ 3 → ❌ CHOPPY, skip everything
     - If 30min range ≥ 0.8% → 🔥 BIG MOVE (use PATH A)
     - If 30min range ≥ 0.5% → ✅ TRENDING (use PATH A)
     - If 30min range < 0.4% AND 15min < 0.4% → 🟡 RANGING (check PATH B for breakout)

2. **CHOOSE ENTRY PATH**:

   **PATH A (Trending)**: If 30min_range ≥ 0.5%
   - Calculate 2h HIGH/LOW/MID for price location
   - Check if price in correct zone
   - Check timing (3-20min since flip)
   - Use normal entry filters

   **PATH B (Breakout)**: If 30min_range < 0.4%
   - Calculate 15min HIGH/LOW
   - Is current price > 15min HIGH * 1.0015? (UP breakout)
   - Is current price < 15min LOW * 0.9985? (DOWN breakout)
   - Has ribbon just flipped (3-8min ago)?
   - Are 2+ LIGHT EMAs present?
   - **If YES to all → BREAKOUT ENTRY!**

   **PATH C (Wick Reversal) 🔥 HIGHEST PRIORITY**: If MANIPULATION WICK DETECTED
   - Price wicked 0.3-0.8% outside EMA ribbon (liquidity grab)
   - Price is now recovering back toward ribbon
   - Ribbon aligned in reversal direction (ALL_GREEN for LONG, ALL_RED for SHORT)
   - **This is the BEST entry - whale manipulation reversed!**
   - Add +20% to confidence score
   - **If detected → ENTER IMMEDIATELY (overrides other paths)**

   **PATH D (Early Reversal) 🚀 HIGHEST PRIORITY**: Check BEFORE other paths!
   - Look at history: Was ribbon `all_red` 1-3 minutes ago?
   - Now: Is ribbon `mixed_red` with 8+ LIGHT red EMAs?
   - Are 2-5 GRAY/GREEN LIGHT EMAs appearing?
   - Less than 5 DARK red EMAs?
   - **If YES → BULLISH REVERSAL - Enter LONG immediately!**

   - Or reverse: Was ribbon `all_green` 1-3 minutes ago?
   - Now: Is ribbon `mixed_green` with 8+ LIGHT green EMAs?
   - Are 2-5 GRAY/RED LIGHT EMAs appearing?
   - Less than 5 DARK green EMAs?
   - **If YES → BEARISH REVERSAL - Enter SHORT immediately!**

   - This catches the wave RIGHT as it starts forming!
   - Works in ANY market condition (no range/location restrictions)
   - **If detected → ENTER IMMEDIATELY (overrides PATH A/B, same priority as PATH C)**

3. **RIBBON STATE CHECK**:
   - Count green vs red EMAs (ignore yellow/gray)
   - ALL_GREEN (85%+) or ALL_RED (85%+) = Ready
   - MIXED (50-84%) = Not ready
   - Count LIGHT intensity EMAs (need 2+)

4. **TIMING CHECK**:
   - When did ribbon flip?
   - 🔥 3-10min ago = EARLY (perfect!)
   - ✅ 5-15min ago = GOOD
   - ⚠️ <3min = TOO FRESH (wait)
   - ❌ >20min = TOO LATE (skip)

5. **EXIT MONITORING** (if in position):
   - Time in position?
   - Ribbon deteriorating?
   - Price crossed yellow EMA?
   - Exit quickly on deterioration

**PRICE TARGETS CALCULATION:**

You MUST provide specific numerical values for ENTRY_PRICE, STOP_LOSS, and TAKE_PROFIT:

1. **ENTRY_PRICE**: Use the current market price from the 5min timeframe

2. **STOP_LOSS**:
   - For LONG: Place stop loss at the identified yellow EMA level (below current price)
   - For SHORT: Place stop loss at the identified yellow EMA level (above current price)
   - If yellow EMA is unclear, use a 0.5-1% stop loss from entry
   - Example: Current price $2650, LONG → Stop Loss at $2640 (yellow EMA or -0.5%)

3. **TAKE_PROFIT**:
   - For LONG: Set take profit 1.5-2% above entry price
   - For SHORT: Set take profit 1.5-2% below entry price
   - Adjust based on recent price volatility and support/resistance levels
   - Example: Current price $2650, LONG → Take Profit at $2690 (+1.5%)

4. **YELLOW_EMA_STOP**: Identify which yellow EMA (there are typically 2) has been acting as support/resistance in the historical data. This is used for trailing stops.

IMPORTANT: All price fields must contain actual numeric values (not 0000.00 or 0). Calculate these based on current price.

PROVIDE YOUR DECISION IN THIS EXACT JSON FORMAT:

```json
{{
  "DECISION": "LONG" | "SHORT",
  "CONFIDENCE": "HIGH" | "MEDIUM" | "LOW",
  "CONFIDENCE_SCORE": 0.0-1.0,
  "TIMEFRAME_ALIGNMENT": "STRONG" | "MODERATE" | "WEAK" | "CONFLICTING",
  "ENTRY_RECOMMENDED": "YES" | "NO",
  "EXIT_RECOMMENDED": "YES" | "NO",
  "REASONING": "Detailed multi-line explanation covering:
- 30MIN + 15MIN RANGE CHECK: [30min: HIGH/LOW/range%, 15min: HIGH/LOW/range%, ribbon flips count]
- MARKET CLASSIFICATION: [CHOPPY/RANGING/TRENDING/BIG MOVE? Which PATH to use?]
- EARLY REVERSAL CHECK (PATH D): [Was ribbon all_red→mixed_red or all_green→mixed_green in last 1-3min? Count LIGHT EMAs in each color. Reversal pattern detected?]
- PATH SELECTION: [PATH D (reversal) or PATH A (trending) or PATH B (breakout) or PATH C (wick)? Why?]
- BREAKOUT DETECTION (if ranging): [Is price > 15min HIGH by >0.15%? or < 15min LOW by >0.15%? Breakout happening NOW?]
- 2H RANGE (if PATH A): [2h HIGH, LOW, MID, price location in range]
- PRICE LOCATION (if PATH A): [In correct zone? Near extreme?]
- 5min Analysis: [ribbon state, % green/red EMAs, LIGHT EMAs count, DARK EMAs count]
- 15min Analysis: [ribbon state, % green/red EMAs, LIGHT EMAs count, DARK EMAs count]
- Transition Timing: [When did ribbon flip? EARLY/GOOD/TOO LATE?]
- Entry Quality: [All conditions met? Filters passed? Type: Reversal/Trending/Breakout/Wick?]
- Exit Signals: [if in position: time?, ribbon deteriorating?, yellow EMA crossed?]
- Learning: [Catch reversals with LIGHT EMAs in opposite colors, Don't LONG at highs, Don't SHORT at lows]",
  "ENTRY_PRICE": 0000.00,
  "STOP_LOSS": 0000.00,
  "TAKE_PROFIT": 0000.00,
  "YELLOW_EMA_STOP": 0000.00,
  "YELLOW_EMA_IDENTIFIED": "EMA_XX",
  "OUTER_BANDS_SPREADING": true | false,
  "POSITION_MANAGEMENT": "HOLD" | "MOVE_STOP_TO_BREAKEVEN" | "TRAIL_YELLOW_EMA" | "EXIT_NOW"
}}
```

🚨 CRITICAL LOGIC RULES - MUST FOLLOW EXACTLY:

1. **ALWAYS PROVIDE A DIRECTION:**
   - You MUST always choose either "LONG" or "SHORT" based on the dominant ribbon state
   - There is NO "WAIT" option anymore
   - Direction is determined by ribbon color, not by whether you want to enter

2. **DIRECTION DETERMINATION:**
   - If 5min or 15min shows predominantly GREEN EMAs → DECISION: "LONG"
   - If 5min or 15min shows predominantly RED EMAs → DECISION: "SHORT"
   - If mixed/unclear, use 15min timeframe to determine direction
   - Even if both are mixed, you MUST still choose LONG or SHORT (prefer 15min state)

3. **ENTRY RECOMMENDATION (SEPARATE FROM DIRECTION):**
   - ENTRY_RECOMMENDED: "YES" = Setup is good, conditions met, recommend entering
   - ENTRY_RECOMMENDED: "NO" = Setup is not ideal, do NOT enter yet (but direction is still provided)

   Set ENTRY_RECOMMENDED: "YES" for ONE of five paths (in priority order):

   **PATH E (Dark Transition) 🎯 ULTRA-HIGH PRIORITY** - when SCALPING SIGNAL DETECTED:
   - ✅ SCALPING SIGNAL ALERT: See "🎯 SCALPING SIGNALS DETECTED" at top
   - ✅ DARK TRANSITION: MMA5 turned GRAY or DARK color (early reversal!)
   - ✅ WICK REJECTION: Price spiked outside EMAs then rejected back
   - ✅ CONFIDENCE BOOST: +10-15% from signal detection
   - ⚠️ OVERRIDE ALL FILTERS: PATH E overrides price location, choppy warnings, range checks
   - 🔥 This is THE EARLIEST entry signal - catches 90% of move!
   - ⏰ TIME-SENSITIVE: Must enter IMMEDIATELY (10 second window)
   - 📋 IF PATH E DETECTED → ENTRY_RECOMMENDED: "YES" (no questions asked!)

   **PATH C (Wick Reversal) 🔥 HIGHEST PRIORITY** - when MANIPULATION WICK DETECTED:
   - ✅ WICK SIGNAL: See alert at top of message
   - ✅ LIQUIDITY GRAB: Price wicked 0.3-0.8% outside ribbon
   - ✅ RECOVERY: Price recovering back toward ribbon
   - ✅ ALIGNMENT: Ribbon is ALL_GREEN (LONG) or ALL_RED (SHORT)
   - ✅ Automatic +20% confidence boost
   - 🚨 **ENTER IMMEDIATELY - This is a whale manipulation reversal!**
   - **Overrides PATH A and PATH B** - take this entry first!

   **PATH D (Early Reversal) 🚀 HIGHEST PRIORITY** - Check BEFORE PATH A/B:
   - ✅ REVERSAL DETECTED: Check history for pattern from STEP 3B
   - For LONG: Ribbon was `all_red` 1-3min ago, now `mixed_red` with:
     - 8+ LIGHT red EMAs (price rocketing up through red EMAs)
     - 2-5 GRAY/GREEN LIGHT EMAs appearing (flip starting)
     - <5 DARK red EMAs (confirms not bearish continuation)
   - For SHORT: Ribbon was `all_green` 1-3min ago, now `mixed_green` with:
     - 8+ LIGHT green EMAs (price crashing down through green EMAs)
     - 2-5 GRAY/RED LIGHT EMAs appearing (flip starting)
     - <5 DARK green EMAs (confirms not bullish continuation)
   - ✅ TIMING: Transition in last 1-3 minutes (FRESH)
   - ✅ NOT CHOPPY: ribbon flips < 3
   - ✅ High confidence (0.75+)
   - 🚨 **ENTER IMMEDIATELY - This catches the wave RIGHT as it forms!**
   - **Overrides PATH A and PATH B** - same priority as PATH C!
   - **NO range/location restrictions** - reversal IS the signal!

   **PATH A (Trending Entry)** - when 30min range ≥ 0.5%:
   - ✅ NOT CHOPPY: ribbon flips < 3
   - ✅ PRICE LOCATION: LONG in lower 50%, SHORT in upper 50% of 2h range
   - ✅ NOT AT EXTREME: Not within 0.3% of 2h HIGH/LOW
   - ✅ Entry Strength "STRONG" (85%+ on both timeframes)
   - ✅ TIMING: Ribbon flipped 3-15 minutes ago
   - ✅ 2+ LIGHT EMAs present
   - ✅ High confidence (0.75+)
   - 🔥 BONUS: If 30min range ≥ 0.8% + fresh flip = BIG MOVE priority!

   **PATH B (Breakout Entry)** - when 30min range < 0.4%:
   - ✅ RANGING CONFIRMED: 30min < 0.4% AND 15min < 0.4%
   - ✅ NOT CHOPPY: ribbon flips < 3 (stable range)
   - ✅ BREAKOUT DETECTED:
     - For LONG: price > 15min HIGH * 1.0015 (breaking UP >0.15%)
     - For SHORT: price < 15min LOW * 0.9985 (breaking DOWN >0.15%)
   - ✅ RIBBON JUST FLIPPED: 3-8 minutes ago to ALL_GREEN/RED
   - ✅ 2+ LIGHT EMAs appearing (momentum building fast)
   - ✅ High confidence (0.80+)
   - 🔥 This catches explosive moves RIGHT as they exit the range!

   Set ENTRY_RECOMMENDED: "NO" when:
   - **CHOPPY**: ≥3 flips (automatic NO for both paths)
   - **RANGING + no breakout**: 30min <0.4% but no breakout detected
   - **WRONG PRICE ZONE** (PATH A only): LONG at top or SHORT at bottom
   - **AT EXTREME** (PATH A only): Within 0.3% of 2h HIGH/LOW
   - **TOO LATE**: >20min since flip
   - **TOO FRESH**: <3min since flip
   - Entry Strength only "BUILDING" (50-84%)
   - Less than 2 LIGHT EMAs
   - Already in a position

4. **CORRECT EXAMPLES:**
   ✅ DECISION: "LONG", ENTRY_RECOMMENDED: "YES", CONFIDENCE_SCORE: 0.85
      → Ribbon is green, setup is good, enter long

   ✅ DECISION: "LONG", ENTRY_RECOMMENDED: "NO", CONFIDENCE_SCORE: 0.45
      → Ribbon is green (so direction is LONG), but setup is weak, do NOT enter

   ✅ DECISION: "SHORT", ENTRY_RECOMMENDED: "YES", CONFIDENCE_SCORE: 0.90
      → Ribbon is red, setup is excellent, enter short

   ✅ DECISION: "SHORT", ENTRY_RECOMMENDED: "NO", CONFIDENCE_SCORE: 0.50
      → Ribbon is red (so direction is SHORT), but conditions not met, do NOT enter

5. **KEY POINT:**
   - DECISION (LONG/SHORT) = What direction the ribbon is pointing
   - ENTRY_RECOMMENDED (YES/NO) = Whether the setup is good enough to actually trade
   - These are now INDEPENDENT fields - direction is always determined by ribbon state

6. **SCALPER EXIT DISCIPLINE (WHEN IN POSITION):**
   Set EXIT_RECOMMENDED: "YES" when:
   - Ribbon flips to MIXED (50-84%) or opposite state
   - Price closes beyond yellow EMA
   - 3+ LIGHT EMAs turn to opposite color (reversal starting)
   - Time in position >10 minutes AND ribbon showing any deterioration
   - Time in position >15 minutes (scalp window closed, exit on next signal)

   Set EXIT_RECOMMENDED: "NO" (HOLD position) when:
   - Only 1-2 EMAs changed color (noise)
   - Position < 5 minutes old (too early)
   - Ribbon still strongly aligned (ALL_GREEN or ALL_RED)
   - No opposite color EMAs appearing yet

   Set POSITION_MANAGEMENT:
   - "HOLD" = Default, position safe, no deterioration yet
   - "TRAIL_YELLOW_EMA" = Profitable + time >8 minutes, trail stop
   - "EXIT_NOW" = Ribbon deteriorating or time >15 minutes

IMPORTANT SCALPER RULES:
- **TWO ENTRY PATHS**: Trending (PATH A) or Breakout (PATH B) - choose based on 30min range
- **RANGE FILTER FIRST**: Check 30min + 15min range BEFORE anything else
- **BREAKOUT PRIORITY**: If ranging (<0.4%), watch for breakouts - catch moves at START!
- **ENTRIES**: Be VERY selective - must pass ALL filters for chosen path
- **EXITS**: Be quick - exit on first ribbon deterioration
- **CATCH BIG MOVES EARLY**:
  - PATH A: 30min ≥0.8% + fresh flip = BIG MOVE priority
  - PATH B: Breakout from range = catch explosive move immediately!
- **AVOID CHOPPY**: ≥3 flips = skip everything (both paths)
- Calculate 30min + 15min range in EVERY analysis
- Calculate 2h HIGH/LOW/MID for PATH A (trending entries)
- Calculate 15min HIGH/LOW for PATH B (breakout detection)
- Reference past losses: Don't LONG at highs, Don't SHORT at lows, Avoid choppy periods
- If EMAs mixed, set ENTRY_RECOMMENDED: NO
- If already in position, set ENTRY_RECOMMENDED: NO and focus on exit signals
- Provide specific entry, stop loss, and take profit prices
- In REASONING: Show 30min+15min range FIRST, then PATH selection, then filters
"""

            # Add dynamic learning insights if available
            if learning_insights:
                system_prompt += learning_insights

            system_prompt += "\nRespond with ONLY the JSON object, no additional text."

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.3,  # Lower temperature for more consistent trading decisions
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )

            # Log cache usage and track costs
            usage = response.usage

            # Track token usage
            input_tokens = getattr(usage, 'input_tokens', 0)
            output_tokens = getattr(usage, 'output_tokens', 0)
            cache_read_tokens = getattr(usage, 'cache_read_input_tokens', 0)
            cache_creation_tokens = getattr(usage, 'cache_creation_input_tokens', 0)

            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cached_tokens += cache_read_tokens
            self.total_calls += 1

            # Calculate cost (Claude Sonnet 4 pricing)
            # Input: $3 per million tokens
            # Output: $15 per million tokens
            # Cached: $0.30 per million tokens (90% discount)
            input_cost = (input_tokens / 1_000_000) * 3.0
            output_cost = (output_tokens / 1_000_000) * 15.0
            cached_cost = (cache_read_tokens / 1_000_000) * 0.30
            call_cost = input_cost + output_cost + cached_cost
            self.session_cost += call_cost

            if cache_creation_tokens:
                print(f"💾 Cache created: {cache_creation_tokens} tokens")
            if cache_read_tokens:
                cache_savings = (cache_read_tokens / 1_000_000) * (3.0 - 0.30)  # Savings vs non-cached
                print(f"💰 Cache hit! {cache_read_tokens} tokens (saved ${cache_savings:.4f})")

            print(f"💵 Call cost: ${call_cost:.4f} | Session total: ${self.session_cost:.4f} ({self.total_calls} calls)")

            # Extract response
            response_text = response.content[0].text.strip()

            # Parse JSON (handle markdown code blocks if present)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            decision = json.loads(response_text)

            # Extract fields
            direction = decision.get('DIRECTION', '').upper()
            entry_recommended = decision.get('ENTRY_RECOMMENDED', 'NO').upper()
            exit_recommended = decision.get('EXIT_RECOMMENDED', 'NO').upper()
            confidence_score = float(decision.get('CONFIDENCE_SCORE', 0.5))
            reasoning = decision.get('REASONING', 'No reasoning provided')

            # VALIDATE: Direction must be LONG or SHORT
            if direction not in ['LONG', 'SHORT']:
                print(f"⚠️  WARNING: Claude returned invalid direction: '{direction}'")
                print("   Inferring direction from ribbon state...")
                # Infer direction from ribbon state (including new mixed states)
                state_5min = data_5min.get('state', '')
                state_15min = data_15min.get('state', '')

                if state_5min in ['all_green', 'mixed_green'] or state_15min in ['all_green', 'mixed_green']:
                    direction = 'LONG'
                    print(f"   → Setting DECISION to LONG (ribbon is green/mixed_green)")
                elif state_5min in ['all_red', 'mixed_red'] or state_15min in ['all_red', 'mixed_red']:
                    direction = 'SHORT'
                    print(f"   → Setting DECISION to SHORT (ribbon is red/mixed_red)")
                else:
                    # Default to 15min state if both are mixed
                    if state_15min in ['all_green', 'mixed_green']:
                        direction = 'LONG'
                    elif state_15min in ['all_red', 'mixed_red']:
                        direction = 'SHORT'
                    else:
                        # Last resort: check which has more green/red EMAs
                        green_5min = len(data_5min.get('ema_groups', {}).get('green', []))
                        red_5min = len(data_5min.get('ema_groups', {}).get('red', []))
                        direction = 'LONG' if green_5min > red_5min else 'SHORT'
                    print(f"   → Defaulting DECISION to {direction} based on timeframe states")

            # SAFETY CHECK: Validate direction matches ribbon state
            # If ribbon is clearly red (>80% red), direction MUST be SHORT
            # If ribbon is clearly green (>80% green), direction MUST be LONG
            green_5min = len(data_5min.get('ema_groups', {}).get('green', []))
            red_5min = len(data_5min.get('ema_groups', {}).get('red', []))
            total_5min = green_5min + red_5min

            green_15min = len(data_15min.get('ema_groups', {}).get('green', []))
            red_15min = len(data_15min.get('ema_groups', {}).get('red', []))
            total_15min = green_15min + red_15min

            # Check 5min ribbon
            if total_5min > 0:
                red_pct_5min = (red_5min / total_5min) * 100
                green_pct_5min = (green_5min / total_5min) * 100

                if red_pct_5min > 80 and direction == 'LONG':
                    print(f"🚨 CRITICAL ERROR: Claude returned LONG but 5min ribbon is {red_pct_5min:.1f}% RED!")
                    print(f"   5min: {red_5min} red EMAs vs {green_5min} green EMAs")
                    print(f"   FORCING direction to SHORT")
                    direction = 'SHORT'
                    entry_recommended = 'NO'  # Don't trust this decision

                elif green_pct_5min > 80 and direction == 'SHORT':
                    print(f"🚨 CRITICAL ERROR: Claude returned SHORT but 5min ribbon is {green_pct_5min:.1f}% GREEN!")
                    print(f"   5min: {green_5min} green EMAs vs {red_5min} red EMAs")
                    print(f"   FORCING direction to LONG")
                    direction = 'LONG'
                    entry_recommended = 'NO'  # Don't trust this decision

            # Check 15min ribbon
            if total_15min > 0:
                red_pct_15min = (red_15min / total_15min) * 100
                green_pct_15min = (green_15min / total_15min) * 100

                if red_pct_15min > 80 and direction == 'LONG':
                    print(f"🚨 CRITICAL ERROR: Claude returned LONG but 15min ribbon is {red_pct_15min:.1f}% RED!")
                    print(f"   15min: {red_15min} red EMAs vs {green_15min} green EMAs")
                    print(f"   FORCING direction to SHORT")
                    direction = 'SHORT'
                    entry_recommended = 'NO'  # Don't trust this decision

                elif green_pct_15min > 80 and direction == 'SHORT':
                    print(f"🚨 CRITICAL ERROR: Claude returned SHORT but 15min ribbon is {green_pct_15min:.1f}% GREEN!")
                    print(f"   15min: {green_15min} green EMAs vs {red_15min} red EMAs")
                    print(f"   FORCING direction to LONG")
                    direction = 'LONG'
                    entry_recommended = 'NO'  # Don't trust this decision

            # Extract targets and Annii's Ribbon exit management
            targets = {
                'entry_price': float(decision.get('ENTRY_PRICE', data_5min['price'])),
                'stop_loss': float(decision.get('STOP_LOSS', 0)),
                'take_profit': float(decision.get('TAKE_PROFIT', 0)),
                'yellow_ema_stop': float(decision.get('YELLOW_EMA_STOP', 0)),
                'yellow_ema_identified': decision.get('YELLOW_EMA_IDENTIFIED', 'Unknown'),
                'outer_bands_spreading': decision.get('OUTER_BANDS_SPREADING', False),
                'position_management': decision.get('POSITION_MANAGEMENT', 'HOLD'),
                'timeframe_alignment': decision.get('TIMEFRAME_ALIGNMENT', 'UNKNOWN'),
                'exit_recommended': exit_recommended
            }

            # Store decision
            self.last_decision = {
                'timestamp': datetime.now().isoformat(),
                'direction': direction,
                'entry_recommended': entry_recommended,
                'confidence_score': confidence_score,
                'reasoning': reasoning,
                'targets': targets,
                'data_5min': data_5min,
                'data_15min': data_15min
            }

            self.decision_history.append(self.last_decision)

            # Trim history to last 100 decisions
            if len(self.decision_history) > 100:
                self.decision_history = self.decision_history[-100:]

            return direction, entry_recommended, confidence_score, reasoning, targets

        except Exception as e:
            print(f"⚠️  Claude API error: {str(e)}")
            # Fallback: Infer direction from ribbon state, but don't recommend entry
            state_5min = data_5min.get('state', '')
            state_15min = data_15min.get('state', '')

            fallback_direction = 'LONG'
            if state_5min in ['all_red', 'mixed_red'] or state_15min in ['all_red', 'mixed_red']:
                fallback_direction = 'SHORT'
            elif state_5min in ['all_green', 'mixed_green'] or state_15min in ['all_green', 'mixed_green']:
                fallback_direction = 'LONG'

            return fallback_direction, 'NO', 0.0, f"API Error: {str(e)}", {
                'entry_price': data_5min['price'],
                'stop_loss': 0,
                'take_profit': 0,
                'timeframe_alignment': 'ERROR'
            }

    def should_execute_trade(self, direction: str, entry_recommended: str,
                            confidence_score: float, min_confidence: float = 0.75,
                            timeframe_alignment: str = 'UNKNOWN') -> bool:
        """
        Determine if trade should be executed based on decision

        Args:
            direction: LONG or SHORT (always provided)
            entry_recommended: YES or NO
            confidence_score: 0-1 confidence score
            min_confidence: Minimum confidence threshold (default 0.75)
            timeframe_alignment: STRONG, MODERATE, WEAK, or CONFLICTING

        Returns:
            bool: True if trade should be executed
        """
        # NEVER trade when timeframes are conflicting
        if timeframe_alignment == 'CONFLICTING':
            print(f"⚠️  BLOCKING TRADE: Timeframe alignment is CONFLICTING")
            return False

        return (
            direction in ['LONG', 'SHORT'] and
            entry_recommended == 'YES' and
            confidence_score >= min_confidence
        )

    def get_market_commentary(
        self,
        data_5min: Dict,
        data_15min: Dict,
        current_position: Optional[Dict] = None
    ) -> str:
        """
        Get Claude's sporadic commentary on market state and trading conditions.
        This is a lighter-weight call than full trading decisions, focused on
        narrative observations rather than trade execution.

        Args:
            data_5min: 5-minute timeframe data
            data_15min: 15-minute timeframe data
            current_position: Current position info

        Returns:
            Commentary string from Claude
        """
        # Format both timeframes - just raw EMA data with RGB
        formatted_5min = self.format_ema_data(
            "5min",
            data_5min['indicators'],
            data_5min['price']
        )

        formatted_15min = self.format_ema_data(
            "15min",
            data_15min['indicators'],
            data_15min['price']
        )

        # Format position info
        position_str = "No position"
        if current_position:
            position_str = f"{current_position['side'].upper()} {current_position['size']:.4f} @ ${current_position['entry_price']:.2f} (PnL: ${current_position.get('unrealized_pnl', 0):+.2f})"

        try:
            # Create a lightweight prompt for commentary
            commentary_prompt = f"""You're a trading analyst providing brief, sporadic commentary on the market state.

CURRENT MARKET STATE:

5-MINUTE TIMEFRAME:
{formatted_5min}

15-MINUTE TIMEFRAME:
{formatted_15min}

CURRENT POSITION: {position_str}

Provide a brief (2-3 sentences) commentary about what you're observing. Be conversational and insightful.
Focus on:
- Overall market momentum and ribbon state
- Interesting patterns or transitions you notice
- Brief risk/opportunity observations
- If there's a position, comment on how it's looking

Keep it casual and natural, like you're thinking out loud. Don't make specific recommendations, just observations.

Respond with ONLY your commentary text, no JSON or formatting."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                temperature=0.7,  # Higher temperature for more natural, varied commentary
                messages=[
                    {
                        "role": "user",
                        "content": commentary_prompt
                    }
                ]
            )

            commentary = response.content[0].text.strip()
            return commentary

        except Exception as e:
            return f"[Commentary unavailable: {str(e)}]"

    def get_cost_summary(self) -> Dict:
        """Get cost tracking summary"""
        return {
            'total_calls': self.total_calls,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_cached_tokens': self.total_cached_tokens,
            'session_cost_usd': self.session_cost,
            'avg_cost_per_call': self.session_cost / max(self.total_calls, 1)
        }

    def print_cost_summary(self):
        """Print formatted cost summary"""
        stats = self.get_cost_summary()
        print(f"\n{'='*80}")
        print("💰 CLAUDE API COST SUMMARY")
        print(f"{'='*80}")
        print(f"Total API Calls: {stats['total_calls']}")
        print(f"Input Tokens: {stats['total_input_tokens']:,}")
        print(f"Output Tokens: {stats['total_output_tokens']:,}")
        print(f"Cached Tokens: {stats['total_cached_tokens']:,}")
        print(f"Session Cost: ${stats['session_cost_usd']:.4f}")
        print(f"Avg Cost/Call: ${stats['avg_cost_per_call']:.4f}")

        # Estimate hourly and daily costs
        if stats['total_calls'] > 0:
            print(f"\n📊 PROJECTIONS:")
            hourly_cost = stats['session_cost_usd'] / (stats['total_calls'] / 120)  # Assuming 30sec intervals
            print(f"Estimated Hourly: ${hourly_cost:.2f}")
            print(f"Estimated Daily (8 hours): ${hourly_cost * 8:.2f}")
        print(f"{'='*80}\n")

    def get_decision_summary(self) -> str:
        """Get formatted summary of last decision"""
        if not self.last_decision:
            return "No decisions made yet"

        d = self.last_decision
        targets = d['targets']

        # Format exit management section
        exit_info = ""
        if targets.get('yellow_ema_stop', 0) > 0:
            exit_info = f"""
📍 ANNII'S RIBBON EXIT MANAGEMENT:
   Yellow EMA Stop: ${targets['yellow_ema_stop']:.2f} ({targets['yellow_ema_identified']})
   Outer Bands Spreading: {'YES ⚠️' if targets['outer_bands_spreading'] else 'NO'}
   Position Management: {targets['position_management']}
   Exit Recommended: {targets['exit_recommended']}
"""

        summary = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         CLAUDE AI TRADING DECISION                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 DIRECTION: {d['direction']}
✅ ENTRY: {d['entry_recommended']}
🎯 CONFIDENCE: {d['confidence_score']:.1%}
🔄 ALIGNMENT: {targets['timeframe_alignment']}

💭 REASONING:
{d['reasoning']}

💰 TARGETS:
   Entry: ${targets['entry_price']:.2f}
   Stop Loss: ${targets['stop_loss']:.2f}
   Take Profit: ${targets['take_profit']:.2f}
{exit_info}
⏰ Timestamp: {d['timestamp']}
"""
        return summary


def test_claude_trader():
    """Test Claude trader with sample data"""
    trader = ClaudeTrader()

    # Sample 5min data
    data_5min = {
        'indicators': {
            'MMA5': {'value': '2650.50', 'color': 'green', 'intensity': 'dark', 'price': 2650.50},
            'MMA10': {'value': '2648.20', 'color': 'green', 'intensity': 'dark', 'price': 2648.20},
            'MMA20': {'value': '2645.00', 'color': 'green', 'intensity': 'normal', 'price': 2645.00},
        },
        'state': 'all_green',
        'ema_groups': {
            'green': [{'name': 'MMA5'}, {'name': 'MMA10'}, {'name': 'MMA20'}],
            'red': [],
            'yellow': [],
            'gray': [],
            'dark_green': [{'name': 'MMA5'}, {'name': 'MMA10'}],
            'dark_red': []
        },
        'price': 2651.00
    }

    # Sample 15min data
    data_15min = {
        'indicators': {
            'MMA5': {'value': '2652.00', 'color': 'green', 'intensity': 'dark', 'price': 2652.00},
            'MMA10': {'value': '2649.50', 'color': 'green', 'intensity': 'normal', 'price': 2649.50},
            'MMA20': {'value': '2647.00', 'color': 'green', 'intensity': 'normal', 'price': 2647.00},
        },
        'state': 'all_green',
        'ema_groups': {
            'green': [{'name': 'MMA5'}, {'name': 'MMA10'}, {'name': 'MMA20'}],
            'red': [],
            'yellow': [],
            'gray': [],
            'dark_green': [{'name': 'MMA5'}],
            'dark_red': []
        },
        'price': 2651.00
    }

    direction, entry, confidence, reasoning, targets = trader.make_trading_decision(
        data_5min, data_15min
    )

    print(trader.get_decision_summary())
    print(f"\n{'='*80}")
    print(f"Should execute: {trader.should_execute_trade(direction, entry, confidence)}")


if __name__ == "__main__":
    test_claude_trader()
