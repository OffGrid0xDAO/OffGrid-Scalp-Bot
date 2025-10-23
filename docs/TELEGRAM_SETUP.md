# 📱 Telegram Reporting Setup Guide

Get beautiful optimization reports sent directly to your Telegram!

## 🎯 Why Telegram?

**Real-time notifications** showing:
- ✅ 3-way comparison (Optimal vs Backtest vs Actual)
- ✅ Performance gap analysis
- ✅ Key findings and insights
- ✅ Planned rule improvements
- ✅ Charts with entry/exit points

**Perfect for:**
- Monitoring optimization while you sleep
- Getting alerts on your phone
- Sharing results with team
- Keeping optimization history

---

## 🚀 Setup (5 minutes)

### Step 1: Create Telegram Bot

1. Open Telegram app
2. Search for `@BotFather`
3. Send `/newbot`
4. Choose a name (e.g., "My Trading Bot")
5. Choose a username (e.g., "my_trading_bot_123")
6. **Copy the token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

1. Search for `@userinfobot`
2. Send `/start`
3. **Copy your ID** (looks like: `123456789`)

### Step 3: Configure .env

```bash
# Edit .env file
nano .env

# Add these lines:
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### Step 4: Test Connection

```bash
python3 src/reporting/telegram_reporter.py
```

Expected output:
```
Telegram Reporter - Testing
✅ Telegram configured
✅ Test message sent successfully
```

You should receive: **"🤖 Trading Bot Test - Telegram connection working!"**

---

## 📊 Report Format

### What You'll Receive After Each Optimization:

```
🔧 OPTIMIZATION CYCLE 1 COMPLETE 🔧

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 3-WAY PERFORMANCE COMPARISON

🥇 OPTIMAL TRADES (Perfect Hindsight)
├ Trades: 450
├ PnL: +112.34%
├ Avg Hold: 8.5 candles
└ Avg Profit: 2.49%

🥈 BACKTEST TRADES (Current Rules)
├ Trades: 123
├ PnL: +18.67%
├ Win Rate: 57.8%
├ Profit Factor: 2.1
└ Max Drawdown: 8.4%

🥉 ACTUAL TRADES (Live Execution)
├ Trades: 0
├ PnL: +0.00%
└ Win Rate: 0.0%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 GAP ANALYSIS

📉 Optimal → Backtest Gap
├ Trade Difference: -327
├ PnL Gap: +93.67%
└ Capture Rate: 16.6%

⚠️ Backtest → Actual Gap
├ Execution Diff: +123 trades
└ Status: ⚠️ Needs attention

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 KEY FINDINGS
1. ✅ Good win rate: 57.8% is solid. Optimize for 65%+ target.
2. 🟡 Moderate capture: 16.6% of optimal profit. Room for improvement.
3. 🔴 LOW CAPTURE RATE: Only 16.6% of optimal profit captured.
   Missing best setups or exiting too early.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛠️ RULE IMPROVEMENTS PLANNED

• confluence_gap_min: 30 → 27
• volume_requirement: ["elevated", "spike"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ Generated: 2025-01-21 14:35:22
```

---

## 📈 Charts Generated

### 3-Way Comparison Chart

**Saved to:** `charts/optimization/ETH_1h_3way_comparison.html`

**Shows:**
- 🟢 **Green triangles**: Optimal trade entries (perfect hindsight)
- 🟢 **Green inverted triangles**: Optimal exits
- 🟡 **Yellow circles**: Backtest entries (current strategy)
- 🟡 **Yellow X's**: Backtest partial exits
- 🔵 **Cyan stars**: Actual live trades (when available)

**4 Panels:**
1. **Price Chart**: All trades overlaid on candlesticks with EMA20
2. **Confluence Scores**: Long vs Short scores
3. **Volume**: Color-coded by status (spike/elevated/normal/low)
4. **Win Rate Bars**: Visual comparison of performance

### Equity Curve Chart

**Saved to:** `charts/optimization/ETH_1h_equity_curve.html`

**Shows:**
- 🟡 **Yellow line**: Backtest equity growth
- 🔵 **Cyan line**: Actual live equity (when available)

---

## 🎯 Usage

### With Optimization Script

Telegram reports are **automatically sent** during optimization:

```bash
python3 scripts/optimize_strategy.py --iterations 5 --timeframe 1h
```

**Output:**
```
GENERATING REPORTS
   ✅ Chart saved: charts/optimization/ETH_1h_3way_comparison.html
   ✅ Report sent to Telegram
```

### Manual Reporting

Send custom reports:

```python
from reporting.telegram_reporter import TelegramReporter

telegram = TelegramReporter()

# Send simple message
telegram.send_simple_message("🚀 Starting optimization run!")

# Send full report (after backtest)
telegram.send_optimization_report(
    optimal_results=optimal_trades,
    backtest_results=backtest_results,
    gap_analysis=gap_analysis,
    iteration=1
)
```

---

## 🔧 Troubleshooting

### "Telegram reporting disabled"

**Check environment variables:**
```bash
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID
```

**If empty, set them:**
```bash
export TELEGRAM_BOT_TOKEN='your_token_here'
export TELEGRAM_CHAT_ID='your_chat_id_here'
```

**Or use .env file:**
```bash
cp .env.example .env
nano .env  # Add your credentials
```

### "Failed to send to Telegram: 401"

**Invalid bot token.** Get a new one from @BotFather:
```
/newbot
```

### "Failed to send to Telegram: 400"

**Invalid chat ID.** Get yours from @userinfobot:
```
/start
```

### "Chat not found"

**You haven't started the bot yet!**
1. Search for your bot username (e.g., @my_trading_bot_123)
2. Click **Start**
3. Now try sending again

### Message too long

If reports are too long, they'll be truncated. This is normal.

---

## 🎨 Customizing Reports

### Change Report Format

Edit `src/reporting/telegram_reporter.py`:

```python
def _format_optimization_report(...):
    # Customize the report template here
    report = f"""Your custom format..."""
```

### Add More Metrics

In `_generate_findings()`:

```python
# Add custom finding
findings.append(
    f"📊 Custom metric: {your_calculation}"
)
```

### Send to Multiple Chats

```python
telegram = TelegramReporter(
    bot_token='your_token',
    chat_id='123456789'  # Your chat
)

# Send to second chat
telegram2 = TelegramReporter(
    bot_token='your_token',
    chat_id='987654321'  # Team chat
)
```

---

## 📱 Advanced: Telegram Commands

### Future Feature: Control Bot via Telegram

**Planned commands:**
```
/status - Get current performance
/optimize - Start optimization run
/stop - Stop current run
/params - Show current parameters
/revert - Revert to last working params
/chart - Get latest comparison chart
```

**To implement:** Create `telegram_commands.py` handler (TODO)

---

## 🎯 Best Practices

### 1. Test First
Always test your Telegram connection:
```bash
python3 src/reporting/telegram_reporter.py
```

### 2. Set Up Notifications
Enable notifications for your bot on your phone to get real-time alerts.

### 3. Create Dedicated Channel
For team collaboration, create a Telegram channel and use its chat ID.

### 4. Backup Reports
Reports are also saved to `optimization_logs/` for permanent record.

### 5. Monitor While Away
Run overnight optimizations and check Telegram in the morning!

---

## 📊 Example Workflow

### Morning: Start Optimization
```bash
# Start 10-iteration optimization
python3 scripts/optimize_strategy.py --iterations 10 --auto-apply
```

**Telegram notification:**
```
🔧 OPTIMIZATION CYCLE 1 COMPLETE 🔧
...
```

### Throughout Day: Monitor Progress

Check Telegram on your phone between iterations.

### Evening: Review Results

1. Check final Telegram report
2. Open charts in browser: `charts/optimization/*.html`
3. Review logs: `optimization_logs/*.json`

### Deploy Best Parameters

If win rate improved:
```bash
# Parameters already applied automatically!
# Ready for paper/live trading
```

---

## ✅ Summary

**You now have:**
- ✅ Beautiful Telegram reports after each optimization
- ✅ Visual comparison charts with all trade types
- ✅ Real-time notifications on your phone
- ✅ Complete audit trail of all optimizations

**Next step:**
```bash
python3 scripts/optimize_strategy.py --iterations 5 --timeframe 1h
```

**Watch your Telegram for:**
- Performance improvements
- Key insights
- Rule changes applied
- Charts generated

**Enjoy automated optimization with real-time updates! 🚀📱**
