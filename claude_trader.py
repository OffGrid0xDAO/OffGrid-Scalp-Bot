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

        total = green_count + red_count
        green_pct = (green_count / total * 100) if total > 0 else 0
        red_pct = (red_count / total * 100) if total > 0 else 0

        formatted = f"""
**{timeframe.upper()} TIMEFRAME**
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Current Price: ${current_price:.2f}
Ribbon State: {state.upper().replace('_', ' ')}

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
            - direction: 'LONG', 'SHORT', or 'WAIT'
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

**ENTRY RULES:**

LONG Entry:
- Wait for ENTIRE ribbon to turn green (100% green alignment)
- Enter when price breaks above the band OR retests yellow EMAs after breakout
- Confirm with historical data: This should be a FRESH transition, not hours into a trend
- Both 5min and 15min should ideally align (or 15min green + 5min transitioning)

SHORT Entry:
- Wait for ENTIRE ribbon to turn red (100% red alignment)
- Enter when price breaks below the band OR retests yellow EMAs after breakout
- Confirm with historical data: This should be a FRESH transition, not hours into a trend

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
- Do NOT enter when only 1-2 EMAs change color (could be just a pullback, not reversal)
- Do NOT try to pick early reversals
- Do NOT enter if ribbon has been green/red for hours (LATE entry)

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

LOW CONFIDENCE (WAIT):
- Mixed ribbons or conflicting timeframes
- Transition is STALE (been green/red for 3+ hours)
- Outer bands already spreading
- No clear yellow EMA support pattern
- Already in position
- Price already far from yellow EMA (late entry)

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

PROVIDE YOUR DECISION IN THIS EXACT JSON FORMAT:

```json
{{
  "DECISION": "LONG" | "SHORT" | "WAIT" | "EXIT",
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
  "YELLOW_EMA_STOP": 0000.00,
  "YELLOW_EMA_IDENTIFIED": "EMA_XX",
  "OUTER_BANDS_SPREADING": true | false,
  "POSITION_MANAGEMENT": "HOLD" | "MOVE_STOP_TO_BREAKEVEN" | "TRAIL_YELLOW_EMA" | "EXIT_NOW"
}}
```

IMPORTANT:
- Be conservative. Only recommend entry (ENTRY_RECOMMENDED: YES) when confidence is HIGH
- Prefer 15min timeframe for trend direction, 5min for entry timing
- If EMAs are mixed or in transition (gray), recommend WAIT
- If already in position, recommend WAIT unless there's a clear exit signal
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

            # Log cache usage for cost tracking
            usage = response.usage
            if hasattr(usage, 'cache_creation_input_tokens') and usage.cache_creation_input_tokens:
                print(f"💾 Cache created: {usage.cache_creation_input_tokens} tokens")
            if hasattr(usage, 'cache_read_input_tokens') and usage.cache_read_input_tokens:
                cache_savings = usage.cache_read_input_tokens * 0.9  # 90% savings
                print(f"💰 Cache hit! Read {usage.cache_read_input_tokens} tokens from cache (saved ~{cache_savings:.0f} tokens = 90% cost)")

            # Extract response
            response_text = response.content[0].text.strip()

            # Parse JSON (handle markdown code blocks if present)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            decision = json.loads(response_text)

            # Extract fields
            direction = decision.get('DIRECTION', 'WAIT').upper()
            entry_recommended = decision.get('ENTRY_RECOMMENDED', 'NO').upper()
            exit_recommended = decision.get('EXIT_RECOMMENDED', 'NO').upper()
            confidence_score = float(decision.get('CONFIDENCE_SCORE', 0.5))
            reasoning = decision.get('REASONING', 'No reasoning provided')

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
            # Fallback to conservative decision
            return 'WAIT', 'NO', 0.0, f"API Error: {str(e)}", {
                'entry_price': data_5min['price'],
                'stop_loss': 0,
                'take_profit': 0,
                'timeframe_alignment': 'ERROR'
            }

    def should_execute_trade(self, direction: str, entry_recommended: str,
                            confidence_score: float, min_confidence: float = 0.75) -> bool:
        """
        Determine if trade should be executed based on decision

        Args:
            direction: LONG, SHORT, or WAIT
            entry_recommended: YES or NO
            confidence_score: 0-1 confidence score
            min_confidence: Minimum confidence threshold (default 0.75)

        Returns:
            bool: True if trade should be executed
        """
        return (
            direction in ['LONG', 'SHORT'] and
            entry_recommended == 'YES' and
            confidence_score >= min_confidence
        )

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
