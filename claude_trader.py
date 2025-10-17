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

    def format_ema_data(self, timeframe: str, indicators: Dict, state: str,
                       ema_groups: Dict, current_price: float) -> str:
        """
        Format EMA data for Claude prompt

        Args:
            timeframe: "5min" or "15min"
            indicators: Raw indicator data
            state: Ribbon state (all_green, all_red, mixed)
            ema_groups: Categorized EMAs by color
            current_price: Current asset price

        Returns:
            Formatted string for Claude
        """
        # Extract MMA indicators
        mma_indicators = {k: v for k, v in indicators.items() if k.startswith('MMA')}

        # Sort by EMA period
        def get_num(key):
            import re
            m = re.search(r'\d+', key)
            return int(m.group()) if m else 0

        sorted_mmas = sorted(mma_indicators.items(), key=lambda x: get_num(x[0]))

        # Format EMA list
        ema_list = []
        for name, data in sorted_mmas:
            ema_num = get_num(name)
            color = data.get('color', 'unknown')
            value = data.get('value', 'N/A')
            intensity = data.get('intensity', 'normal')

            ema_list.append(f"  EMA{ema_num}: {value} ({color}, {intensity})")

        # Count EMAs
        green_count = len(ema_groups.get('green', []))
        red_count = len(ema_groups.get('red', []))
        yellow_count = len(ema_groups.get('yellow', []))
        gray_count = len(ema_groups.get('gray', []))
        dark_green_count = len(ema_groups.get('dark_green', []))
        dark_red_count = len(ema_groups.get('dark_red', []))

        # NEW: Get entry strength indicator
        entry_strength = ema_groups.get('entry_strength', 'unknown')

        total = green_count + red_count
        green_pct = (green_count / total * 100) if total > 0 else 0
        red_pct = (red_count / total * 100) if total > 0 else 0

        formatted = f"""
**{timeframe.upper()} TIMEFRAME**
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Current Price: ${current_price:.2f}
Ribbon State: {state.upper().replace('_', ' ')}
Entry Strength: {entry_strength.upper()} ⚠️ IMPORTANT: 'BUILDING' = watching only, 'STRONG' = consider entry

EMA Alignment:
- Green EMAs: {green_count} ({green_pct:.1f}%) | Dark Green: {dark_green_count}
- Red EMAs: {red_count} ({red_pct:.1f}%) | Dark Red: {dark_red_count}
- Yellow EMAs: {yellow_count}
- Gray EMAs: {gray_count}

Individual EMAs:
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

    def make_trading_decision(
        self,
        data_5min: Dict,
        data_15min: Dict,
        current_position: Optional[Dict] = None,
        account_info: Optional[Dict] = None
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
        # Format both timeframes
        formatted_5min = self.format_ema_data(
            "5min",
            data_5min['indicators'],
            data_5min['state'],
            data_5min['ema_groups'],
            data_5min['price']
        )

        formatted_15min = self.format_ema_data(
            "15min",
            data_15min['indicators'],
            data_15min['state'],
            data_15min['ema_groups'],
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
            # Format historical data (up to 200 sampled snapshots covering 3-4 hours)
            history_5min_csv = self.format_history_csv(data_5min, "5min", limit=200)
            history_15min_csv = self.format_history_csv(data_15min, "15min", limit=200)

            # Call Claude API with prompt caching
            # Split prompt into cacheable (static) and dynamic parts
            system_prompt = """You are an expert trading analyst specializing in Annii's EMA Ribbon Strategy.

ANNII'S RIBBON STRATEGY (5-15min Scalping):

**IMPORTANT: TWO-TIER THRESHOLD SYSTEM**

The system uses two detection thresholds:
1. **50% Threshold (BUILDING)** = "Start watching" - State shows 'all_green' or 'all_red' but Entry Strength: BUILDING
   - This triggers monitoring but NOT entry
   - 6+ out of 12 EMAs have flipped to same color
   - You should analyze and provide commentary but DO NOT recommend entry yet

2. **85% Threshold (STRONG)** = "Consider entering" - Entry Strength: STRONG
   - This signals the ribbon is nearly complete
   - 10+ out of 12 EMAs have flipped to same color
   - Now you can recommend entry IF other conditions are met (fresh transition, proper momentum, etc.)

**DIRECTION DETERMINATION (ALWAYS REQUIRED):**

You MUST always determine a direction (LONG or SHORT) based on the dominant ribbon state:

🚨 CRITICAL - DIRECTION RULES (FOLLOW EXACTLY):
- If 5min shows predominantly RED EMAs (>50%) → Direction: SHORT (NOT LONG!)
- If 5min shows predominantly GREEN EMAs (>50%) → Direction: LONG (NOT SHORT!)
- If 15min shows predominantly RED EMAs (>50%) → Direction: SHORT (NOT LONG!)
- If 15min shows predominantly GREEN EMAs (>50%) → Direction: LONG (NOT SHORT!)
- RED ribbon = SHORT direction = bearish
- GREEN ribbon = LONG direction = bullish
- If mixed/unclear, choose based on 15min timeframe (higher timeframe = trend direction)

DOUBLE CHECK YOUR DECISION:
- Before outputting, verify that if you see "all_red" or "red alignment 90%+", your DECISION is "SHORT"
- Before outputting, verify that if you see "all_green" or "green alignment 90%+", your DECISION is "LONG"

**ENTRY RECOMMENDATION RULES:**

After determining direction, decide whether to recommend entry (YES/NO):

Recommend ENTRY: YES when ALL of these conditions are met:
- Entry Strength is "STRONG" (85%+ alignment, not just "BUILDING")
- Wait for near-complete ribbon (10-12 EMAs of same color out of 12)
- Price breaks above/below the band OR retests yellow EMAs after breakout
- FRESH transition confirmed in historical data (not hours into a trend)
- Both timeframes ideally aligned (or 15min aligned + 5min transitioning)

Recommend ENTRY: NO when:
- Entry Strength is only "BUILDING" (50-84% alignment - not enough yet)
- Ribbon is mixed or conflicting between timeframes (TIMEFRAME_ALIGNMENT: "CONFLICTING")
- Transition is STALE (been in this state for 3+ hours)
- Already in a position
- Setup is unclear or low confidence
- Price already far from yellow EMA (late entry)
- 🚨 CRITICAL: If TIMEFRAME_ALIGNMENT is "CONFLICTING", you MUST set ENTRY_RECOMMENDED: "NO"

**EXIT RULES (CRITICAL):**

For LONG positions:
1. **Outer Band Spreading**: Watch outer 3 EMAs (fastest/darkest). If they start spreading AWAY from others = pullback coming
   - Action: Exit or move stop to breakeven/profit
2. **Yellow EMA Support**: Price must stay ABOVE yellow EMAs
   - If price bounces off yellow = stay in trade
   - If price crosses BELOW yellow = EXIT (reversal signal)
3. **Trailing Stop**: Use yellow EMA as trailing stop (place stop just below yellow)
4. **Historical Support**: Check which yellow EMA (there are 2) has been acting as support for past few hours

For SHORT positions (reverse):
1. Outer bands spreading = exit/protect
2. Price must stay BELOW yellow EMAs
3. Yellow EMA as trailing stop (above yellow)
4. Cross above yellow = EXIT

**WHAT NOT TO DO:**
- Do NOT recommend entry when only 1-2 EMAs change color (could be just a pullback, not reversal)
- Do NOT recommend entry trying to pick early reversals
- Do NOT recommend entry if ribbon has been green/red for hours (LATE entry)
- But ALWAYS provide a direction (LONG or SHORT) regardless of entry recommendation

**ANALYSIS REQUIRED:**
1. Evaluate ribbon state on both timeframes
2. Check if transition is FRESH (just happened) or STALE (hours old)
3. Identify which yellow EMA has been support/resistance over past hours
4. Detect outer band spreading patterns in historical data
5. Verify dark EMAs are BUILDING (not fading)
6. Check for price bounces off yellow EMAs in history

**DECISION CRITERIA:**

HIGH CONFIDENCE Entry:
- 100% ribbon green/red on BOTH timeframes
- FRESH transition visible in history (was opposite color within last 30-60 min)
- Dark EMAs present and increasing
- Price broke above/below band or successfully retested yellow EMA
- Historical data shows yellow EMA held as support/resistance

MEDIUM CONFIDENCE:
- 15min aligned, 5min transitioning (90%+)
- Transition somewhat recent (1-2 hours)
- Yellow EMA support visible but not strongly tested

LOW CONFIDENCE (Do NOT recommend entry):
- Mixed ribbons or conflicting timeframes
- Transition is STALE (been green/red for 3+ hours)
- Outer bands already spreading
- No clear yellow EMA support pattern
- Already in position
- Price already far from yellow EMA (late entry)
- NOTE: Even with low confidence, you must still provide a LONG or SHORT direction

**EXIT SIGNALS (for existing positions):**
- Outer 3 bands spreading away from others
- Price crossed yellow EMA (wrong direction)
- Dark EMAs fading (count decreasing)
- Opposite color EMAs appearing (1-2 is OK, but 3+ means exit)

**OUTPUT FORMAT:**
Provide JSON with entry/exit decision AND yellow EMA levels for stop placement"""

            user_message = f"""CURRENT MARKET DATA (REAL-TIME):

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

ANALYSIS INSTRUCTIONS:
1. Look at HISTORICAL DATA first (even if limited early in session) to understand the trend
2. Check if current state is FRESH (just transitioned) or LATE (been same state for extended period)
3. Verify dark green/red EMAs are BUILDING (increasing count) not FADING (decreasing count)
4. Identify support/resistance levels from price action over the historical period
5. Confirm this isn't the tail-end of a move (price already moved significantly from earliest history)
6. Look for patterns: V-bottoms, failed breakouts, momentum acceleration

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
- 5min Analysis: [ribbon state, % green/red EMAs, dark EMAs count, outer band spreading?]
- 15min Analysis: [ribbon state, % green/red EMAs, dark EMAs count]
- Historical Context: [how long in current state, yellow EMA support pattern, entry timing quality]
- Signal Quality: [FRESH vs STALE, alignment strength, momentum building/fading]
- Exit Signals: [outer bands spreading, yellow EMA status, reversal signs]
- Risk Factors: [concerns, cautions, why waiting/exiting might be better]",
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

   Set ENTRY_RECOMMENDED: "YES" when:
   - Entry Strength is "STRONG" (85%+ threshold met)
   - FRESH transition confirmed in history
   - Timeframes aligned or 15min aligned with 5min transitioning
   - High confidence (typically 0.75+)

   Set ENTRY_RECOMMENDED: "NO" when:
   - Entry Strength is only "BUILDING" (50-84%)
   - Transition is STALE (hours old)
   - Already in a position
   - Low confidence or unclear setup
   - Late entry (price already moved far)

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

IMPORTANT:
- Be conservative. Only recommend entry (ENTRY_RECOMMENDED: YES) when confidence is HIGH
- Prefer 15min timeframe for trend direction, 5min for entry timing
- If EMAs are mixed or in transition (gray), set ENTRY_RECOMMENDED: NO (but still provide LONG or SHORT)
- If already in position, set ENTRY_RECOMMENDED: NO unless there's a clear exit signal
- Provide specific entry, stop loss, and take profit prices based on current price
- In your REASONING, clearly explain the state of BOTH timeframes

Respond with ONLY the JSON object, no additional text."""

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
                # Infer direction from ribbon state
                if data_5min.get('state') == 'all_green' or data_15min.get('state') == 'all_green':
                    direction = 'LONG'
                    print(f"   → Setting DECISION to LONG (ribbon is green)")
                elif data_5min.get('state') == 'all_red' or data_15min.get('state') == 'all_red':
                    direction = 'SHORT'
                    print(f"   → Setting DECISION to SHORT (ribbon is red)")
                else:
                    # Default to 15min state if both are mixed
                    if data_15min.get('state') == 'all_green':
                        direction = 'LONG'
                    elif data_15min.get('state') == 'all_red':
                        direction = 'SHORT'
                    else:
                        # Last resort: check which has more green/red EMAs
                        green_5min = len(data_5min.get('ema_groups', {}).get('green', []))
                        red_5min = len(data_5min.get('ema_groups', {}).get('red', []))
                        direction = 'LONG' if green_5min > red_5min else 'SHORT'
                    print(f"   → Defaulting DECISION to {direction} based on EMA counts")

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
            fallback_direction = 'LONG'
            if data_5min.get('state') == 'all_red' or data_15min.get('state') == 'all_red':
                fallback_direction = 'SHORT'
            elif data_5min.get('state') == 'all_green' or data_15min.get('state') == 'all_green':
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
        # Format both timeframes (reuse existing method)
        formatted_5min = self.format_ema_data(
            "5min",
            data_5min['indicators'],
            data_5min['state'],
            data_5min['ema_groups'],
            data_5min['price']
        )

        formatted_15min = self.format_ema_data(
            "15min",
            data_15min['indicators'],
            data_15min['state'],
            data_15min['ema_groups'],
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
