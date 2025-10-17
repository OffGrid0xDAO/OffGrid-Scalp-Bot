# OffGrid Scalp Bot - Hyperliquid Auto Trading System

An automated trading bot that monitors TradingView's EMA ribbon indicator and executes trades on Hyperliquid exchange.

---

## 📋 Table of Contents
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [TradingView Auto-Login](#-tradingview-auto-login--persistent-sessions)
- [Trading Strategies](#-trading-strategies)
- [Risk Management](#-risk-management)
- [Dashboard](#-dashboard)
- [Troubleshooting](#-troubleshooting)
- [Security](#-security)

---

## 📋 Prerequisites

1. **Python 3.8+** installed
2. **Google Chrome** browser
3. **TradingView** account with "Annii's Ribbon" indicator
4. **Hyperliquid** account with wallet and private key

---

## 🔧 Installation

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Create `.env` File

Create a file named `.env` in the project directory:

```env
# Hyperliquid Settings
HYPERLIQUID_PRIVATE_KEY=your_private_key_here

# Network Settings
USE_TESTNET=true

# Trading Settings
AUTO_TRADE=true
POSITION_SIZE_PCT=10
LEVERAGE=25
TAKE_PROFIT_PCT=35
PROFIT_TRIGGER_PCT=0.3
SECURE_PROFIT_PCT=0.08

# Scalping Mode (conservative or aggressive_5m)
SCALPING_MODE=conservative

# TradingView Auto-Login (Optional)
TRADINGVIEW_USERNAME=your_email@example.com
TRADINGVIEW_PASSWORD=your_password_here
TRADINGVIEW_CHART_URL=https://www.tradingview.com/chart/xyz123/
```

**⚠️ SECURITY:** Never commit your `.env` file to Git! It's already in `.gitignore`.

---

## 🚀 Quick Start

### 1. Start the Bot

```bash
python manifest_bot.py
```

### 2. Configuration

The bot will prompt you (press Enter to use defaults):
- Private Key (if not in .env)
- Network (testnet/mainnet) - **Default: YES for testnet**
- Auto-trading (yes/no) - **Default: YES**
- Scalping Mode (1=conservative, 2=aggressive)
- Position Size (% of account)
- Leverage (1-50x)

### 3. TradingView Setup

**If you have auto-login configured:**
- Bot logs in automatically ✅
- Opens your chart ✅
- Starts monitoring immediately ✅

**If manual login:**
- Bot opens Chrome browser
- Log into TradingView
- Open chart with **Annii's Ribbon** indicator
- Ensure **ALL EMAs are visible**
- Press **ENTER** in terminal

### 4. Monitor

Bot will:
- Read EMA colors every 10 seconds
- Display live dashboard
- Execute trades automatically (if enabled)
- Show real-time profit/loss

---

## 🔐 TradingView Auto-Login & Persistent Sessions

### 💾 Session Persistence (Built-in!)

**Your login is automatically saved!** You only need to log in once.

#### How It Works

The bot uses a dedicated Chrome profile that stores:
- 🍪 **Cookies** - Keeps you logged in
- 📝 **Session data** - Your TradingView preferences
- 🔐 **Authentication tokens**

**First Run:**
```
🔍 Checking for saved login session...
❌ No session found
🔐 Logging in... (auto or manual)
💾 Session saved!
```

**All Future Runs:**
```
🔍 Checking for saved login session...
✅ Already logged in from previous session!
💾 Using saved cookies - no login needed!
🚀 Starting immediately!
```

**Time saved:** 10-15 seconds per run! ⚡

#### Setup Options

**Option A: Auto-Login (Recommended)**

Add to `.env`:
```env
TRADINGVIEW_USERNAME=your_email@example.com
TRADINGVIEW_PASSWORD=your_password
TRADINGVIEW_CHART_URL=https://www.tradingview.com/chart/xyz/
```

- First run: Logs in automatically, saves session
- Future runs: Uses saved session, skips login entirely!

**Option B: Manual Login**

- Don't add credentials to `.env`
- Log in manually **once**
- Session is saved automatically
- All future runs use saved session!

**Either way, you only log in once!** 🎉

#### What Gets Saved

```
OffGrid-Scalp-Bot/
├── chrome_profile/        ← All session data here (ignored by Git)
│   ├── TradingBot/       ← Your bot's profile
│   │   ├── Cookies       ← Login cookies
│   │   └── Preferences   ← Settings
```

**Already Protected:**
- ✅ In `.gitignore` - Won't be committed
- ✅ Stays on your local machine only
- ✅ Separate from your main Chrome

#### Clearing Session Data

**To reset login or switch accounts:**

Windows:
```bash
rmdir /s chrome_profile
```

Mac/Linux:
```bash
rm -rf chrome_profile/
```

Next run will create fresh profile and log in again.

#### Session Expiry

TradingView sessions last **weeks to months**. If it expires:
- With auto-login: Logs in automatically again
- Without auto-login: Prompts you to log in
- Session is saved again

---

## 🎮 Runtime Controls

While running:
- Type **`M`** + Enter → Open settings menu
- **Ctrl+C** → Stop bot

**Settings Menu:**
1. Switch network (testnet/mainnet)
2. Toggle auto-trading
3. Adjust position size
4. Change leverage
5. Modify take profit target
6. Adjust profit protection

---

## 📊 Trading Strategies

### Conservative Mode (15min timeframe)
- **Entry:** 90% ribbon alignment required
- **Exit:** Take profit at 35% account (default)
- **Protection:** Activates at +0.3% price move
- **Best for:** Swing trades, lower risk

### Aggressive Mode (5min timeframe)
- **Entry:** 60% ribbon alignment, early gray entries
- **TP1:** 10% account (close 50% position)
- **TP2:** 20% account (close remaining)
- **Stop Loss:** -0.15% price (-3.75% account)
- **Best for:** Fast scalping, higher frequency

---

## 🛡️ Risk Management

### Features:
1. **Take Profit Targets** - Automatic profit taking
2. **Profit Protection** - Trailing stop after trigger
3. **Hard Stop Loss** - Fixed stop (aggressive mode)
4. **Position Sizing** - Configurable % of account
5. **Leverage Control** - Adjustable 1-50x

### Pattern Detection:
- **V-Bottom Reversals** - Rapid trend changes
- **Momentum Acceleration** - Building strength
- **Dark EMA Detection** - Strong momentum
- **Gray EMA Warnings** - Early transition alerts

---

## 📈 Dashboard

```
╔══════════════════════════════════════════════════════════════════╗
║              AUTO-TRADING SYSTEM (LIVE)                          ║
║           25x Leverage | 10% Position | TP: 35%                  ║
╚══════════════════════════════════════════════════════════════════╝

⏰ 14:30:25 | Check #42

────────────────────────────────────────────────────────────────────
💰 PRICE: $2651.50  |  🟢 STATE: ALL GREEN
💎 DARK EMAs: 3 Green | 0 Red

📈 POSITION: LONG | 0.125 ETH
   Entry: $2640.50 | 🟢 PnL: +$125.50 (+2.5%)
   🛡️ PROTECTION: ACTIVE | Stop @ $2645.50 (+0.19% price / 4.75% account)
   🎯 Take Profit: $2738.27 (35% account) | 3.27% away

────────────────────────────────────────────────────────────────────
📊 28 EMAs | 🟢 28 | 🔴 0 | 🟡 0 | ⚪ 0

⚡ LAST SIGNAL: 🚀 LONG @ $2640.50 ✅ LONG opened: 0.125 ETH

💼 ACCOUNT: $10,000.00 | Available: $7,500.00
   🟢 Total PnL: +$125.50

📈 TRADES TODAY: 3

────────────────────────────────────────────────────────────────────
🤖 AUTO-TRADING: ACTIVE ✅ | Network: TESTNET
Press 'M' + Enter for menu | Ctrl+C to stop
────────────────────────────────────────────────────────────────────
```

### Dashboard Elements:
- **💰 PRICE:** Current market price
- **🟢/🔴/⚪ STATE:** Ribbon state (green/red/mixed)
- **💎 DARK EMAs:** Strong momentum indicators
- **📈 POSITION:** Current trade details
- **🛡️ PROTECTION:** Profit protection status
- **🎯 Take Profit:** Target and distance

---

## 📝 Trading Signals

### Entry Signals:
- **💥 EXPLOSIVE LONG** - V-bottom + dark EMAs + acceleration
- **🚀 V-BOTTOM LONG** - Rapid reversal from red to green
- **⚡ ACCELERATION LONG** - Strong momentum building
- **💎 ULTRA-EARLY LONG** - Dark EMAs + gray transition (aggressive)
- **🚀 LONG** - Standard ribbon flip (red → green)
- **🚀 SHORT** - Standard ribbon flip (green → red)

### Exit Signals:
- **🎯 TAKE PROFIT** - Target reached
- **🛡️ PROFIT SECURED** - Protection stop triggered
- **❌ STOP LOSS** - Hard stop hit (aggressive mode)

### Warnings:
- **⚠️ GRAY EMAs** - Transition starting, trade signal coming
- **⚠️ Failed Breakout** - Dark EMAs fading, skip entry

---

## 🔍 Troubleshooting

### "No indicators found"
**Problem:** Bot can't read TradingView indicators  
**Fix:**
- Ensure **ALL EMAs** are visible on TradingView
- Check indicator names start with "**MMA**"
- Don't minimize browser window
- Refresh chart if needed

### ChromeDriver errors
**Problem:** Browser won't open  
**Fix:**
- Update Chrome to latest version
- Download matching ChromeDriver
- Or: `pip install chromedriver-autoinstaller`

### Auto-login fails
**Problem:** Can't log into TradingView automatically  
**Fix:**
- Check username/password in `.env`
- Disable 2FA if enabled
- Try manual login once (session will be saved)

### Trade not executing
**Problem:** Bot sees signal but doesn't trade  
**Fix:**
- Check auto-trading is **ENABLED** ✅
- Verify sufficient account balance
- Check position size settings
- Review Hyperliquid connection

### Session not persisting
**Problem:** Must log in every time  
**Fix:**
- Check `chrome_profile/` folder exists
- Verify bot has write permissions
- Delete and recreate: `rmdir /s chrome_profile`

---

## 🔐 Security Best Practices

### Credentials:
1. ✅ **Never share your private key**
2. ✅ Use `.env` file for all credentials
3. ✅ `.env` is in `.gitignore` (won't be committed)
4. ✅ Keep your `.env` file private
5. ✅ Use testnet for testing

### Session Data:
- ✅ `chrome_profile/` stored locally only
- ✅ Never uploaded to Git
- ✅ Isolated from main Chrome browser
- ✅ Can be deleted anytime

### Trading Safety:
1. **Start on TESTNET** - Never start with real money
2. **Small positions** - Begin with 5-10% size
3. **Low leverage** - Start at 10-15x, not 50x
4. **Monitor actively** - Watch first few trades
5. **Stable connection** - Reliable internet required

---

## ⚠️ Important Warnings

### TESTNET FIRST
**Always test on testnet before mainnet!**
- Get testnet funds from Hyperliquid faucet
- Test for at least 1-2 weeks
- Verify all features work correctly

### Real Money Risk
- Trading crypto is **extremely risky**
- You can **lose all your money**
- Start with **small position sizes**
- Never trade money you can't afford to lose

### Technical Requirements
- ✅ Stable internet connection
- ✅ TradingView chart must stay visible
- ✅ Don't minimize or close browser
- ✅ All EMAs must be visible

---

## 💡 Tips for Success

1. **Start Small** - 5-10% position size initially
2. **Test First** - Run testnet for 1-2 weeks minimum
3. **Monitor Actively** - Don't leave completely unattended
4. **Check Settings** - Review targets regularly
5. **Stable Setup** - Reliable internet and power
6. **Keep Chrome Visible** - Browser must stay open
7. **Use Auto-Login** - Saves time and reduces errors
8. **Review Logs** - Check `trading_data/` for analysis

---

## 📊 Data Logging

### Files Created:

```
trading_data/
└── session_20231016_143025/
    ├── ema_data.csv          # EMA values, colors, states
    └── trading_data.csv      # All trades executed
```

### EMA Data Format:
```csv
timestamp,price,ribbon_state,MMA5_value,MMA5_color,MMA5_intensity,...
2023-10-16T14:30:00,2651.50,all_green,2650.50,green,dark,...
```

### Trading Data Format:
```csv
timestamp,action,price,size,side,pnl,account_value
2023-10-16T14:30:00,open,2651.50,0.125,long,0.00,10000.00
```

---

## 🎓 Recommended Settings for Beginners

### TESTNET PRACTICE:
```env
USE_TESTNET=true
AUTO_TRADE=true
SCALPING_MODE=conservative
POSITION_SIZE_PCT=10
LEVERAGE=10
TAKE_PROFIT_PCT=35
```

### After 1-2 Weeks Success on Testnet:
```env
USE_TESTNET=false  # ⚠️ REAL MONEY!
POSITION_SIZE_PCT=5-10
LEVERAGE=15-25
```

---

## 📁 Project Structure

```
OffGrid-Scalp-Bot/
├── manifest_bot.py              # Main trading bot
├── tradingview_auto_login.py    # Auto-login module
├── requirements.txt             # Python dependencies
├── .env                         # Configuration (DO NOT COMMIT)
├── .gitignore                   # Protects sensitive files
├── chrome_profile/              # Saved login session
└── trading_data/                # Trade logs and EMA data
```

---

## 🆘 Emergency Procedures

### Stop Bot Immediately:
1. Press **Ctrl+C** in terminal
2. Or close terminal window
3. Browser will close automatically

### Close Position Manually:
1. Stop the bot (Ctrl+C)
2. Log into Hyperliquid directly
3. Close position manually
4. Or use bot menu (M) to close

### Reset Everything:
```bash
# Stop bot
Ctrl+C

# Clear session
rmdir /s chrome_profile  # Windows
rm -rf chrome_profile/   # Mac/Linux

# Check .env settings
notepad .env  # Windows
nano .env     # Mac/Linux
```

---

## 📞 Support

### Before Asking for Help:
1. ✅ Read this entire README
2. ✅ Check Troubleshooting section
3. ✅ Review `.env` configuration
4. ✅ Verify testnet vs mainnet
5. ✅ Check browser console for errors

### Debug Checklist:
- [ ] All dependencies installed?
- [ ] `.env` file configured correctly?
- [ ] TradingView logged in?
- [ ] All EMAs visible on chart?
- [ ] Internet connection stable?
- [ ] Hyperliquid API accessible?

---

## 🎯 Success Criteria

Your bot is working correctly when:
- ✅ Browser opens and logs in (auto or manual)
- ✅ Dashboard updates every 10 seconds
- ✅ EMAs are being read correctly
- ✅ Signals appear when ribbon changes
- ✅ Trades execute when conditions met
- ✅ Data logs to `trading_data/` folder

---

## 📄 License & Disclaimer

**Disclaimer:** This bot is for educational purposes only. Trading cryptocurrency involves substantial risk of loss. Use at your own risk. The author is not responsible for any financial losses.

**License:** Use freely, but trade responsibly! 

---

## 🎉 Quick Reference

| Command | Action |
|---------|--------|
| `python manifest_bot.py` | Start bot |
| Press `M` + Enter | Open settings menu |
| Press `Ctrl+C` | Stop bot |
| `rmdir /s chrome_profile` | Reset login session |

| Setting | Safe Value | Aggressive Value |
|---------|-----------|------------------|
| Position Size | 5-10% | 15-20% |
| Leverage | 10-15x | 25-50x |
| Mode | Conservative | Aggressive |
| Network | TESTNET ✅ | MAINNET ⚠️ |

---

**Happy Trading! 🚀** Remember: Test on testnet first, start small, and never risk more than you can afford to lose!
