# Dual-Timeframe Trading Bot with Claude AI

## 🎯 Overview

This trading bot monitors **5-minute and 15-minute** EMA ribbon charts simultaneously and uses **Claude Sonnet 4.5 AI** to make high-confidence trading decisions based on timeframe alignment.

## 📁 Files Created

1. **`claude_trader.py`** - Claude AI integration module for dual-timeframe analysis
2. **`dual_timeframe_bot.py`** - Main dual-timeframe bot with two browsers
3. **`.env`** - Updated with Claude API configuration

## 🚀 Features

### ✅ Dual Browser System
- **Browser 1**: Monitors 5-minute chart (faster signals, entry timing)
- **Browser 2**: Monitors 15-minute chart (trend reliability, direction)
- Both browsers run simultaneously with independent data collection

### ✅ Separate Data Logging
- `ema_data_5min.csv` - 5-minute EMA values, colors, and states
- `ema_data_15min.csv` - 15-minute EMA values, colors, and states
- `claude_decisions.csv` - AI trading decisions with confidence scores

### ✅ Claude AI Decision Engine
- Analyzes both timeframes together
- Returns structured decisions: LONG/SHORT/WAIT
- Provides confidence scores (0-1) and reasoning
- Only trades when confidence ≥ 75% (configurable)

### ✅ Smart Entry Logic
- **LONG**: 100% green alignment on both timeframes = HIGHEST confidence
- **SHORT**: 100% red alignment on both timeframes = HIGHEST confidence
- **WAIT**: Mixed signals, gray EMAs, or timeframes in conflict

## 📦 Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Make sure your `requirements.txt` includes:
```
anthropic>=0.18.0
```

### 2. Get Claude API Key

1. Go to https://console.anthropic.com/
2. Create an account or sign in
3. Navigate to API Keys
4. Create a new API key
5. Copy your key

### 3. Configure .env File

Edit `.env` and add your Claude API key:

```bash
# Claude AI Configuration
ANTHROPIC_API_KEY=sk-ant-api03-your_actual_key_here
MIN_CONFIDENCE=0.75  # Only trade when confidence ≥ 75%

# Trading Settings
USE_TESTNET=true
AUTO_TRADE=true
POSITION_SIZE_PCT=10
LEVERAGE=25
```

## 🎮 Usage

### Running the Bot

```bash
python dual_timeframe_bot.py
```

### Setup Process

1. **Configuration**: The bot will ask you to confirm settings
2. **Browser Launch**: Two Chrome windows will open side-by-side
3. **TradingView Setup**:
   - Log in to TradingView in **both browsers**
   - Browser 1 (left): Open your **5-minute** chart with Annii's Ribbon
   - Browser 2 (right): Open your **15-minute** chart with Annii's Ribbon
   - Make sure **ALL EMAs are visible** on both charts
4. **Press ENTER** when both charts are ready
5. **Data Collection**: Bot starts collecting data every 10 seconds
6. **AI Analysis**: Claude analyzes both timeframes every 30 seconds

### What Happens During Trading

1. **Data Collection**: Both timeframes update every 10 seconds
2. **AI Analysis**: Claude receives:
   - 5min EMA data (colors, alignment, price)
   - 15min EMA data (colors, alignment, price)
   - Current position and account info
3. **Decision Making**: Claude returns:
   - Direction (LONG/SHORT/WAIT)
   - Entry recommendation (YES/NO)
   - Confidence score (0-1)
   - Reasoning (explanation)
   - Price targets (entry, stop loss, take profit)
4. **Trade Execution**: If confidence ≥ MIN_CONFIDENCE, trade is executed
5. **Logging**: All decisions logged to CSV for analysis

## 📊 Data Files

### Location
```
trading_data/
└── dual_session_20231016_143025/
    ├── ema_data_5min.csv          # 5-minute EMA data
    ├── ema_data_15min.csv         # 15-minute EMA data
    └── claude_decisions.csv       # AI trading decisions
```

### EMA Data Format
```csv
timestamp,price,ribbon_state,MMA5_value,MMA5_color,MMA5_intensity,...
2023-10-16T14:30:00,2651.50,all_green,2650.50,green,dark,...
```

### Claude Decisions Format
```csv
timestamp,direction,entry_recommended,confidence_score,reasoning,entry_price,stop_loss,take_profit,timeframe_alignment,executed
2023-10-16T14:30:00,LONG,YES,0.85,"Strong bullish alignment on both timeframes...",2651.50,2638.27,2690.77,STRONG,True
```

## 🧠 Claude AI Trading Logic

### Decision Criteria

**LONG Signal (Highest Confidence)**:
- ✅ 100% green EMAs on 5min timeframe
- ✅ 100% green EMAs on 15min timeframe
- ✅ Dark green EMAs present (strong momentum)
- ✅ No gray EMAs (transition complete)

**SHORT Signal (Highest Confidence)**:
- ✅ 100% red EMAs on 5min timeframe
- ✅ 100% red EMAs on 15min timeframe
- ✅ Dark red EMAs present (strong momentum)
- ✅ No gray EMAs (transition complete)

**WAIT Conditions**:
- ❌ Mixed ribbon (neither fully green nor fully red)
- ❌ Timeframes in conflict (5min green, 15min red)
- ❌ Gray EMAs present (transition in progress)
- ❌ Already in position

### Example Claude Decision

```json
{
  "DIRECTION": "LONG",
  "ENTRY_RECOMMENDED": "YES",
  "CONFIDENCE": "HIGH",
  "CONFIDENCE_SCORE": 0.92,
  "REASONING": "Exceptional bullish alignment across both timeframes. 5-minute chart shows 100% green EMAs with 3 dark green indicators, suggesting strong upward momentum. 15-minute chart confirms with 100% green alignment and 2 dark green EMAs, validating the trend. No gray or yellow EMAs present, indicating clean bullish structure. This represents a high-probability long entry opportunity.",
  "ENTRY_PRICE": 2651.50,
  "STOP_LOSS": 2638.27,
  "TAKE_PROFIT": 2690.77,
  "TIMEFRAME_ALIGNMENT": "STRONG"
}
```

## 📈 Trading Rules

### Position Sizing
- Default: 10% of account per trade
- With 25x leverage = 250% exposure per trade

### Risk Management
- **Stop Loss**: 0.5% below entry (LONG) or above entry (SHORT)
- **Take Profit**: 1.5% above entry (LONG) or below entry (SHORT)

### Entry Requirements
- Confidence score ≥ 75% (MIN_CONFIDENCE in .env)
- ENTRY_RECOMMENDED = YES
- No existing position

## 🔍 Testing the Bot

### Test Mode (Without Trading)

Edit `.env`:
```bash
AUTO_TRADE=false  # Disable actual trading
USE_TESTNET=true  # Use testnet
```

This allows you to:
- See Claude's decisions without executing trades
- Verify both browsers are collecting data correctly
- Review decision logs in CSV files

### Testing Claude Trader Separately

```bash
python claude_trader.py
```

This runs a test with sample data and shows you an example Claude decision.

## 🐛 Troubleshooting

### Issue: "ANTHROPIC_API_KEY not found"
**Solution**: Add your API key to `.env` file

### Issue: Browsers not opening
**Solution**: Make sure Chrome is installed and chromedriver is in PATH

### Issue: No indicators found
**Solution**:
1. Make sure Annii's Ribbon is loaded on TradingView
2. Verify ALL EMAs are visible (not hidden)
3. Check that chart is fully loaded before pressing ENTER

### Issue: Claude always returns WAIT
**Solution**:
1. Check that EMAs are actually changing colors
2. Verify both timeframes have valid data
3. Wait for clear 100% green or 100% red alignment

### Issue: Data not logging
**Solution**: Check that `trading_data/` directory was created and you have write permissions

## 📊 Dashboard Display

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                      DUAL TIMEFRAME TRADING BOT                              ║
║                    25x Leverage | 10% Position | Min Conf: 75%               ║
╚══════════════════════════════════════════════════════════════════════════════╝

⏰ 14:30:25 | Check #42

────────────────────────────────────────────────────────────────────────────────
📊 POSITION: NONE

────────────────────────────────────────────────────────────────────────────────
📊 TIMEFRAME DATA:

🔷 5-MINUTE:
   🟢 State: ALL_GREEN
   💰 Price: $2651.50
   🟢 28 | 🔴 0 | ⚪ 2
   💎 Dark: 3 green | 0 red

🔶 15-MINUTE:
   🟢 State: ALL_GREEN
   💰 Price: $2651.50
   🟢 27 | 🔴 0 | ⚪ 3
   💎 Dark: 2 green | 0 red

────────────────────────────────────────────────────────────────────────────────
🧠 CLAUDE AI DECISION:
   Direction: LONG
   Entry: YES
   Confidence: 92%
   Alignment: STRONG
   Reasoning: Exceptional bullish alignment across both timeframes...

⚡ LAST SIGNAL: ✅ LONG @ $2651.50 | LONG opened: 0.125 ETH | Conf: 92%

💼 ACCOUNT: $10,000.00 | Available: $7,500.00
   🟢 Total PnL: +$125.50

📈 TRADES TODAY: 3

────────────────────────────────────────────────────────────────────────────────
🤖 AUTO-TRADING: ACTIVE ✅ | Network: TESTNET
📁 Data Logging: dual_session_20231016_143025
Press Ctrl+C to stop
────────────────────────────────────────────────────────────────────────────────
```

## 🎓 Best Practices

### 1. Start with Testnet
Always test with `USE_TESTNET=true` first

### 2. Monitor Both Browsers
Keep an eye on both charts to understand what the bot sees

### 3. Review Decision Logs
Check `claude_decisions.csv` to understand Claude's reasoning

### 4. Adjust Confidence Threshold
Start with `MIN_CONFIDENCE=0.85` for very conservative trading

### 5. Use Appropriate Leverage
25x leverage is aggressive. Consider 10x-15x for safer trading

## 🔄 Comparison with Original Bot

| Feature | Original Bot | Dual-Timeframe Bot |
|---------|-------------|-------------------|
| Timeframes | Single (15min) | Dual (5min + 15min) |
| Decision Making | Rule-based | Claude AI |
| Browsers | 1 | 2 |
| Data Files | 1 EMA CSV | 3 CSVs (5min, 15min, decisions) |
| Entry Timing | Manual rules | AI-optimized with 5min |
| Trend Validation | Single timeframe | Dual timeframe confirmation |
| Confidence Scoring | No | Yes (0-1) |

## 📝 Notes

- The bot updates data every **10 seconds** for both timeframes
- Claude analysis runs every **30 seconds** (to give data time to update)
- Only trades when **no position** exists (one trade at a time)
- All decisions are logged for training future ML models
- Browser windows are positioned side-by-side for easy monitoring

## 🚨 Safety Notes

1. **Start small**: Use small position sizes when testing
2. **Monitor closely**: Watch the bot for the first few trades
3. **Check API limits**: Claude API has rate limits, monitor usage
4. **Verify connectivity**: Ensure stable internet for both browsers
5. **Emergency stop**: Press Ctrl+C to stop the bot immediately

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the logs in `trading_data/` directory
3. Test Claude separately with `python claude_trader.py`
4. Verify your `.env` configuration

## 🎉 Success Criteria

Your bot is working correctly when you see:
- ✅ Both browsers open with different charts
- ✅ Data updates every 10 seconds for both timeframes
- ✅ Claude decisions appear every 30 seconds
- ✅ CSV files are being populated with data
- ✅ Trades execute when confidence ≥ threshold

Happy trading! 🚀
