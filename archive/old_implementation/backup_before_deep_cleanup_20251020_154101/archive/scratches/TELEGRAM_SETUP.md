# 📱 Telegram Notifications Setup Guide

Get beautiful trade notifications sent directly to your Telegram!

## 📋 Prerequisites

- Telegram account
- 5 minutes of your time

## 🤖 Step 1: Create Your Bot

1. Open Telegram and search for `@BotFather`
2. Start a chat and send: `/newbot`
3. Follow the prompts:
   - **Bot name**: `My Trading Bot` (or any name you like)
   - **Username**: Must end in `bot`, e.g., `my_scalper_bot`
4. BotFather will give you a **Bot Token** that looks like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
5. **Save this token** - you'll need it in Step 3

## 💬 Step 2: Get Your Chat ID

### Option A: Using your bot directly

1. Find your new bot in Telegram (search for the username you chose)
2. Start a chat and send any message (e.g., "Hello")
3. Open this URL in your browser (replace `YOUR_BOT_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":` in the response
5. Your **Chat ID** will be a number like: `123456789` or `-123456789`

### Option B: Using @userinfobot

1. Search for `@userinfobot` in Telegram
2. Start a chat
3. It will tell you your **Chat ID**

## ⚙️ Step 3: Configure Your Bot

1. Open `.env` file in the TradingScalper directory
2. Find these lines:
   ```env
   TELEGRAM_BOT_TOKEN=
   TELEGRAM_CHAT_ID=
   ```
3. Fill in your values:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=123456789
   ```
4. Save the file

## ✅ Step 4: Test Your Setup

Run the test script:

```bash
python telegram_notifier.py
```

You should receive 3 test messages in Telegram:
1. 🚀 Entry notification
2. ✅ Exit notification
3. ℹ️ Update notification

## 📨 Message Examples

### Entry Notification:
```
🚀 TRADE ENTRY: LONG 🚀

📈 Position Details
├ Entry Price: $3850.25
├ Position Size: 1.0420 ETH
└ Confidence: 85%

📊 Targets
├ 🛡 Stop Loss: $3842.50 (0.20%)
├ 🎯 Take Profit: $3890.00 (1.03%)
├ 🟡 Yellow EMA: $3843.75
└ 📈 Risk/Reward: 1:5.12

🎀 Ribbon Analysis
├ 5min: ALL_GREEN
├ 15min: ALL_GREEN
└ Momentum: 💚 6 light | 3 dark

🧠 Claude's Analysis
5min: ALL_GREEN (11/12 EMAs, 6 light) - Strong bullish momentum...
```

### Exit Notification:
```
✅ 💰 TRADE CLOSED: LONG ✅

🟢 Performance
├ Entry: $3850.25
├ Exit: $3875.50
├ Size: 1.0420 ETH
├ PnL: +$26.31 (+2.15%)
└ Duration: 7.5 minutes

🚪 Exit Reason
Take Profit Hit

🧠 Claude's Analysis
Target reached. Ribbon still strong but taking profit as planned...
```

## 🔧 Troubleshooting

### "Telegram notifications disabled" message

**Problem**: Bot token or chat ID not set

**Solution**:
1. Check `.env` file has both values filled in
2. No quotes needed around values
3. No spaces after `=`

### "Telegram send error" message

**Problem**: Invalid token or chat ID

**Solution**:
1. Verify bot token from @BotFather
2. Make sure chat ID is correct (check with @userinfobot)
3. Ensure you've sent at least one message to your bot

### Not receiving messages

**Problem**: Haven't started conversation with bot

**Solution**:
1. Find your bot in Telegram
2. Click "Start" or send any message
3. Try again

### "Unauthorized" error

**Problem**: Bot token is wrong

**Solution**:
1. Go back to @BotFather
2. Send `/mybots`
3. Select your bot → API Token
4. Copy the token again

## 🎨 Customizing Messages

Edit `telegram_notifier.py` to customize:
- Message format
- Emojis
- Information displayed
- Message length

## 🔒 Security Notes

- **Never share your bot token** - it's like a password
- Add `.env` to `.gitignore` (already done)
- If token is exposed, revoke it via @BotFather:
  1. `/mybots` → your bot → API Token → Revoke current token

## 📱 Using with a Group Chat

Want notifications in a group?

1. Create a Telegram group
2. Add your bot to the group
3. Make it an admin (optional, for reliability)
4. Send a message in the group
5. Get the group's chat ID (will be negative, like `-123456789`)
6. Use the group chat ID in `.env`

## 🚀 That's It!

Your bot is now configured! Start the trading bot and watch the notifications roll in! 🎉

---

**Need help?** Check the main README or open an issue on GitHub.
