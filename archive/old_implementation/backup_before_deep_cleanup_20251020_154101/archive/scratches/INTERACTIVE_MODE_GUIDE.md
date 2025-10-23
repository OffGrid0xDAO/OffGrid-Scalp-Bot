# 🎮 Interactive Manual Trading Mode

## Overview

The Interactive Mode lets you **chat with Claude** about market conditions and **manually execute trades** based on the AI's insights. Perfect for learning, testing strategies, or maintaining full control over your trading decisions.

---

## Quick Start

```bash
python interactive_mode.py
```

The bot will:
1. Open two TradingView browsers (5min + 15min charts)
2. Monitor market conditions in real-time
3. Provide commentary every 10 minutes
4. Wait for your commands

---

## Commands

### Chat with Claude
```
>>> chat <your question>
```

Ask Claude anything about the market:
- `chat should I enter long here?`
- `chat what's the risk if I short now?`
- `chat explain what you see in the 5min chart`
- `chat is this a good stop loss level?`
- `chat when should I exit this position?`

**Cost:** ~$0.01-0.02 per question

### Manual Trading
```
>>> long       # Open a LONG position
>>> short      # Open a SHORT position
>>> close      # Close current position
```

Trades are executed immediately with:
- Automatic TP/SL orders
- Yellow EMA as trailing stop
- Position size from your .env settings

### Status & Info
```
>>> status     # Show current market state
>>> cost       # Show API cost summary
>>> help       # Show all commands
>>> exit       # Stop the bot
```

---

## Example Session

```bash
$ python interactive_mode.py

╔══════════════════════════════════════════════════════════════════════════════╗
║                      INTERACTIVE TRADING MODE                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 CONFIGURATION:
  Network: TESTNET 🧪
  Trading Mode: 🎮 MANUAL (Interactive)
  Position Size: 10.0%
  Leverage: 25x
  AI: Claude Sonnet 4.5

✅ Starting interactive mode in 3 seconds...

[Browsers open, data collection starts...]

================================================================================
📊 MARKET STATUS - 14:32:15
================================================================================

💼 POSITION: None

🔷 5min:  🟢 ALL_GREEN     @ $2651.23
🔶 15min: 🟢 ALL_GREEN     @ $2651.00

💰 Session cost: $0.0000 (0 calls)
================================================================================

>>> chat should I enter long here?

🤔 Asking Claude: 'should I enter long here?'...

────────────────────────────────────────────────────────────────────────────────
🧠 CLAUDE'S RESPONSE:
────────────────────────────────────────────────────────────────────────────────
Looking at the current setup, I see a clean long opportunity forming:

**5-Minute Chart:**
- Ribbon just flipped 100% green with 3 dark green EMAs building
- Price broke above the yellow EMA band at $2645 and is holding
- This appears to be a fresh transition (not hours into the move)

**15-Minute Chart:**
- Also showing full green alignment, confirming the bullish bias
- Outer bands are tight and building, not spreading yet

**Entry Recommendation:**
YES, this looks like a solid long entry. The yellow EMA around $2638-2640 would be
your stop loss level. Target the upper end of the band or watch for outer band
spreading as an exit signal.

**Risk:** If price falls back below $2640 (yellow EMA), that would invalidate the
setup and you should exit immediately.
────────────────────────────────────────────────────────────────────────────────
💵 Chat cost: $0.0128

>>> long

🤔 Executing LONG trade...
✅ LONG opened: 0.0500 ETH @ $2651.00 | TP @ $2690.78, SL @ $2638.49

================================================================================
📊 MARKET STATUS - 14:33:42
================================================================================

💼 POSITION: LONG 0.0500 @ $2651.00
   🟢 PnL: $+2.35

🔷 5min:  🟢 ALL_GREEN     @ $2652.70
🔶 15min: 🟢 ALL_GREEN     @ $2652.50

💰 Session cost: $0.0263 (2 calls)
================================================================================

>>> chat when should I exit?

🤔 Asking Claude: 'when should I exit?'...

────────────────────────────────────────────────────────────────────────────────
🧠 CLAUDE'S RESPONSE:
────────────────────────────────────────────────────────────────────────────────
Great entry! Here are the exit signals to watch for:

**Exit Signal #1 - Take Profit:**
Your TP is set at $2690.78 (1.5% gain). This is reasonable for a scalp trade.

**Exit Signal #2 - Yellow EMA Break:**
If price closes below $2638 (your stop loss), the yellow EMA support has failed
and the trade is invalidated. Your stop should handle this automatically.

**Exit Signal #3 - Outer Bands Spreading:**
Watch the 3 fastest EMAs (dark green ones). If they start spreading AWAY from
the pack, that's a warning sign of a pullback coming. Consider taking profit
or moving your stop to breakeven.

**Exit Signal #4 - Red EMAs Appearing:**
If 1-2 red EMAs appear, it's just noise. But if 3+ EMAs flip red, that's a
reversal signal and you should exit.

**Recommendation:** Let it run toward your TP target, but watch for outer band
spreading as an early exit signal if you want to lock in profit.
────────────────────────────────────────────────────────────────────────────────
💵 Chat cost: $0.0142

>>> status

================================================================================
📊 MARKET STATUS - 14:35:18
================================================================================

💼 POSITION: LONG 0.0500 @ $2651.00
   🟢 PnL: $+4.50

🔷 5min:  🟢 ALL_GREEN     @ $2655.00
🔶 15min: 🟢 ALL_GREEN     @ $2654.80

💬 Last Claude comment: Both timeframes strongly aligned green. Price momentum...

💰 Session cost: $0.0405 (3 calls)
================================================================================

[10 minutes later...]

────────────────────────────────────────────────────────────────────────────────
💬 CLAUDE'S THOUGHTS:
   Strong bullish momentum continues on both timeframes with tight outer bands.
   Your long position looks healthy, but start watching for outer band spreading
   as we approach the upper resistance zone around $2690.
────────────────────────────────────────────────────────────────────────────────

>>> close

🤔 Closing position...
✅ Closed LONG: 0.0500 ETH @ $2687.50 | Profit: $+1.83

>>> cost

================================================================================
💰 CLAUDE API COST SUMMARY
================================================================================
Total API Calls: 5
Input Tokens: 15,240
Output Tokens: 890
Cached Tokens: 8,120
Session Cost: $0.0582
Avg Cost/Call: $0.0116

📊 PROJECTIONS:
Estimated Hourly: $0.35
Estimated Daily (8 hours): $2.80
================================================================================

>>> exit

👋 Exiting interactive mode...
```

---

## Features

### 1. Real-Time Market Monitoring
- Both 5min and 15min charts monitored continuously
- Automatic state detection (all_green, all_red, mixed)
- EMA color classification (green, red, yellow, dark)

### 2. Claude AI Assistance
- Ask questions in natural language
- Get detailed market analysis
- Receive actionable trading advice
- Context-aware responses based on current charts

### 3. Manual Trade Execution
- One-command trading: `long`, `short`, `close`
- Automatic TP/SL placement
- Yellow EMA trailing stops
- Position size from .env settings

### 4. Periodic Commentary
- Claude provides updates every 10 minutes
- Highlights important patterns
- Warns of potential reversals
- Tracks momentum shifts

### 5. Cost Tracking
- Real-time cost display
- Per-call breakdown
- Session total
- Hourly/daily projections

---

## Cost Estimates

### Interactive Mode Costs

| Activity | Calls | Cost |
|----------|-------|------|
| **Background monitoring** | ~18/3hr | ~$0.25 |
| **Chat messages** | Variable | ~$0.01-0.02 each |
| **Trade executions** | 0 (free) | $0.00 |

**Example session (3 hours):**
- Monitoring: 18 calls = $0.25
- 10 chat questions = $0.15
- **Total: ~$0.40**

**Compared to auto mode:**
- Auto mode (active): $2.05 per 3 hours
- Interactive mode: $0.25 + chat costs
- **Interactive is cheaper if you chat <120 times per 3 hours!**

---

## Tips for Using Interactive Mode

### 1. Strategic Questions
Good questions to ask:
- `chat is this a fresh transition or late entry?`
- `chat which yellow EMA is acting as support?`
- `chat are the outer bands spreading?`
- `chat should I move my stop to breakeven?`

### 2. Learning Tool
Use interactive mode to:
- Understand how Claude analyzes charts
- Learn to identify entry/exit signals
- Practice risk management
- Build confidence before going fully automated

### 3. Confirmation Bias
Remember:
- Claude sees what you see in the charts
- Don't ask leading questions
- Consider multiple viewpoints
- Trust the strategy, not emotions

### 4. Cost Management
- Each chat costs ~$0.01-0.02
- Use `status` command (free) for quick updates
- Commentary is automatic - don't need to ask "what's happening?"
- Batch your questions: "Should I enter long? What's the risk? Where's my stop?"

---

## Configuration

Interactive mode uses the same `.env` settings as auto mode:

```bash
# .env file
HYPERLIQUID_PRIVATE_KEY=your_key_here
ANTHROPIC_API_KEY=your_claude_key_here

USE_TESTNET=true
POSITION_SIZE_PCT=10
LEVERAGE=25
MIN_CONFIDENCE=0.75  # Not used in manual mode
```

**Note:** `AUTO_TRADE` is ignored in interactive mode (always manual).

---

## Switching Between Modes

### Automated Trading
```bash
python run_dual_bot.py
```
- Fully automated
- Claude makes decisions
- Executes trades automatically
- Cost: $1.15-2.05 per 3 hours

### Interactive Trading
```bash
python interactive_mode.py
```
- Manual control
- Chat with Claude
- You make final decision
- Cost: $0.25 + chat costs per 3 hours

---

## Troubleshooting

### "Cannot read stdin"
Interactive mode requires a terminal with stdin. Don't run in background or scripts.

### "No price data available"
Wait 5-10 seconds after starting for data collection to begin.

### "Claude not available"
Check your `ANTHROPIC_API_KEY` in `.env` file.

### Chat responses are slow
First call creates cache (~3-5 seconds). Subsequent calls are faster (~1-2 seconds).

---

## Safety Notes

1. **Test on testnet first** - Set `USE_TESTNET=true` in `.env`
2. **Start with small sizes** - Use 5-10% position size initially
3. **Monitor your stops** - SL orders are automatic but verify they're active
4. **Don't overtrade** - Quality over quantity
5. **Track your costs** - Use `cost` command regularly

---

## Advanced Usage

### Custom Commentary Interval
Edit `interactive_mode.py` line 96:
```python
self.commentary_interval = 600  # Change to 300 for 5min, 900 for 15min
```

### Disable Commentary
Comment out lines 140-150 in `interactive_mode.py` to disable automatic commentary.

### Verbose Mode
Add `print()` statements to see more details about EMA states, transitions, etc.

---

## Questions?

- Check `COST_OPTIMIZATION_SUMMARY.md` for cost details
- Check `COST_QUICK_REFERENCE.md` for settings
- Review `dual_timeframe_bot.py` for strategy details

**Happy trading! 🎮📈**
