# Trading Scalper Bot - Hyperliquid Mainnet

Automated trading bot for Hyperliquid DEX using the proven **Iteration 10 strategy** (2.19% backtest profit, 41% win rate).

## Quick Start

```bash
python3 main.py
```

That's it! The bot will start trading on Hyperliquid mainnet.

## Your Bot is Ready!

✅ **Account Connected:** $9.76 balance  
✅ **Position Size:** $0.98 per trade (10% of account)  
✅ **Leverage:** 25x ($24.41 exposure per trade)  
✅ **All systems operational**

⚠️ **Recommended:** Fund account to $200-500 for better position sizing

## How to Start

```bash
python3 main.py
```

The bot will:
- Check for trading signals every 60 seconds
- Enter trades automatically when quality score ≥ 50
- Set stop loss at -0.75% and take profit at +5.0%
- Send Telegram notifications for all trades

## Configuration

All settings are in `.env` file (already configured):
- `HYPERLIQUID_PRIVATE_KEY` - Your wallet private key ✅
- `TELEGRAM_BOT_TOKEN` - For notifications ✅
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID ✅

## Documentation

- **Setup Guide:** `MAINNET_SETUP.md` - Detailed configuration
- **Strategy Info:** `LIVE_TRADING_README.md` - How the strategy works
- **Check Setup:** Run `python3 check_setup.py` to verify everything

## Safety Features

- **Stop Loss:** -0.75% per trade
- **Profit Lock:** Once +1.5% profit, trade won't go negative
- **Quality Filter:** Only trades high-quality signals (score ≥50)
- **Single Position:** Max 1 trade at a time

## Emergency Stop

Press `Ctrl+C` to stop the bot. Existing positions will remain open.

---

**Status:** Ready to trade! 🚀  
**Mode:** LIVE on Hyperliquid Mainnet  
**Position Sizing:** 10% of account (adjustable in `main.py`)
