# OffGrid Scalp Bot - Hyperliquid Auto Trading System

An automated trading bot that monitors TradingView's EMA ribbon indicator and executes trades on Hyperliquid exchange.

## 📋 Prerequisites

1. **Python 3.8+** installed
2. **Google Chrome** browser
3. **ChromeDriver** (matching your Chrome version)
4. **TradingView** account with "Annii's Ribbon" indicator
5. **Hyperliquid** account with wallet and private key

## 🔧 Installation

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Install ChromeDriver

**Windows:**
1. Check your Chrome version: `chrome://version`
2. Download matching ChromeDriver from: https://chromedriver.chromium.org/downloads
3. Extract and add to PATH or place in project folder

**Alternative:** Use `chromedriver-autoinstaller`:
```bash
pip install chromedriver-autoinstaller
```

### Step 3: Create `.env` File (Optional but Recommended)

Create a file named `.env` in the project directory:

```env
# Hyperliquid Settings
HYPERLIQUID_PRIVATE_KEY=your_private_key_here

# Network (true/false)
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
```

**⚠️ SECURITY WARNING:** Never share your `.env` file or commit it to version control!

## 🎯 Running the Bot

### Step 1: Start the Bot

```bash
python manifest_bot.py
```

### Step 2: Initial Configuration

The bot will prompt you for:
1. **Private Key** (if not in .env)
2. **Network** (testnet/mainnet)
3. **Auto-trading** (yes/no)
4. **Scalping Mode** (conservative/aggressive)
5. **Position Size** (% of account per trade)
6. **Leverage** (1-50x)
7. **Take Profit Target** (% account profit)
8. **Profit Protection Settings**

### Step 3: TradingView Setup

1. Bot opens Chrome browser
2. Log into TradingView
3. Open your chart with **Annii's Ribbon** indicator
4. Ensure **ALL EMAs are visible** on the indicator panel
5. Press **ENTER** in the terminal

### Step 4: Monitor

The bot will:
- Read EMA colors every 10 seconds
- Display live dashboard
- Execute trades automatically (if enabled)
- Show profit/loss in real-time

## 🎮 Runtime Controls

While the bot is running:

- Type **`M`** + Enter → Open settings menu
- **Ctrl+C** → Stop the bot

### Settings Menu Options:
1. Switch network (testnet/mainnet)
2. Toggle auto-trading
3. Adjust position size
4. Change leverage
5. Modify take profit target
6. Adjust profit protection

## 📊 Trading Strategies

### Conservative Mode (15min timeframe)
- Entry: 90% ribbon alignment required
- Exit: Take profit at 35% account (default)
- Protection: Activates at +0.3% price move
- Best for: Swing trades, lower risk

### Aggressive Mode (5min timeframe)
- Entry: 60% ribbon alignment, early gray entries
- TP1: 10% account (close 50% position)
- TP2: 20% account (close remaining)
- Stop Loss: -0.15% price (-3.75% account)
- Best for: Fast scalping, higher frequency

## 🛡️ Risk Management Features

1. **Take Profit Targets** - Automatic profit taking
2. **Profit Protection** - Trailing stop after reaching trigger
3. **Hard Stop Loss** - Fixed stop in aggressive mode
4. **Position Sizing** - Configurable % of account
5. **Leverage Control** - Adjustable 1-50x

## ⚠️ Important Warnings

### TESTNET FIRST
**Always test on testnet before using mainnet!** Get testnet funds from Hyperliquid faucet.

### Real Money Risk
- Trading crypto is **extremely risky**
- You can **lose all your money**
- Start with **small position sizes**
- Never trade money you can't afford to lose

### Technical Requirements
- Stable internet connection required
- TradingView chart must remain visible
- Don't minimize or close the browser
- All EMAs must be visible in the indicator panel

## 🔍 Troubleshooting

### "No indicators found"
- Ensure all EMAs are visible on TradingView
- Check that indicator names start with "MMA"
- Refresh the chart

### ChromeDriver errors
- Update Chrome to latest version
- Download matching ChromeDriver version
- Install `chromedriver-autoinstaller`

### Connection errors
- Check internet connection
- Verify Hyperliquid API is accessible
- Ensure private key is correct

### Trade not executing
- Check if auto-trading is enabled (should show "✅ ENABLED")
- Verify sufficient account balance
- Check position size settings
- Review Hyperliquid API status

## 📈 Dashboard Explained

```
💰 PRICE: Current market price
🟢/🔴/⚪ STATE: Ribbon state (all green/all red/mixed)
💎 DARK EMAs: Count of dark-colored EMAs (strong momentum)
📈 POSITION: Current open position details
🛡️ PROTECTION: Profit protection status
🎯 Take Profit: TP target price and distance
```

## 🔐 Security Best Practices

1. **Never share your private key**
2. Use `.env` file for credentials
3. Add `.env` to `.gitignore`
4. Use testnet for testing
5. Start with small position sizes
6. Monitor the bot regularly

## 📝 Trading Signals

### Entry Signals:
- 💥 **EXPLOSIVE LONG** - V-bottom + dark EMAs + acceleration
- 🚀 **V-BOTTOM LONG** - Rapid reversal from red to green
- ⚡ **ACCELERATION LONG** - Strong momentum building
- 💎 **ULTRA-EARLY LONG** - Dark EMAs + gray transition (aggressive mode)
- 🚀 **LONG** - Standard ribbon flip (red → green)

### Exit Signals:
- 🎯 **TAKE PROFIT** - Target reached
- 🛡️ **PROFIT SECURED** - Protection stop triggered
- ❌ **STOP LOSS** - Hard stop hit (aggressive mode)

## 💡 Tips for Success

1. **Start Small** - Use 5-10% position size initially
2. **Test First** - Run on testnet for at least a week
3. **Monitor Actively** - Don't leave bot completely unattended
4. **Check Settings** - Review profit targets and stops regularly
5. **Stable Setup** - Use reliable internet and power
6. **Keep Chrome Visible** - Don't minimize or close the browser

## 📞 Support

- Review code comments for detailed functionality
- Check TradingView chart setup if no signals appear
- Test connections before live trading
- Keep Python and dependencies updated

---

**Disclaimer:** This bot is for educational purposes. Trading cryptocurrency involves substantial risk of loss. Use at your own risk. The author is not responsible for any financial losses.

