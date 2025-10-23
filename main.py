#!/usr/bin/env python3
"""
MAIN ENTRY POINT - Live Trading Bot

Simply run: python3 main.py

This will start the live trading bot on Hyperliquid mainnet with:
- 10% position sizing
- 25x leverage
- Real-time monitoring
- Telegram notifications
- Iteration 10 strategy (2.19% proven profit)
"""

import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

print("="*80)
print("  🔴 LIVE TRADING BOT - HYPERLIQUID MAINNET")
print("  Iteration 10 Strategy with Real Fees & Slippage")
print("="*80)
print()
print("⚠️  WARNING: REAL MONEY TRADING MODE")
print("    This bot will trade on Hyperliquid mainnet with real funds")
print("    Position size: 10% of account per trade (25x leverage = 250% exposure)")
print()
print("Strategy Performance (Backtest):")
print("  • Return: +2.19%")
print("  • Win Rate: 41%")
print("  • Total Trades: 39")
print("  • Avg Win: +2.85%")
print("  • Avg Loss: -1.03%")
print()
print("Strategy Settings:")
print("  • Timeframe: 15min")
print("  • Quality Score Min: 50")
print("  • Stop Loss: 0.75%")
print("  • Profit Lock: 1.5% (won't let trade go negative after +1.5%)")
print("  • Take Profit: 5.0%")
print()
print("Real Trading Costs:")
print("  • Trading Fee: 0.05% (Hyperliquid taker fee)")
print("  • Estimated Slippage: ~0.02%")
print("  • Total Cost per Trade: ~0.07%")
print()
print("="*80)
print()

# Check environment variables
print("🔍 Checking environment...")
print()

checks_passed = True

if not os.getenv('HYPERLIQUID_PRIVATE_KEY'):
    print("❌ HYPERLIQUID_PRIVATE_KEY not set - bot cannot trade!")
    checks_passed = False
else:
    print("✅ HYPERLIQUID_PRIVATE_KEY is set")

if not os.getenv('TELEGRAM_BOT_TOKEN'):
    print("⚠️  TELEGRAM_BOT_TOKEN not set - Telegram reporting will be disabled")
else:
    print("✅ TELEGRAM_BOT_TOKEN is set")

if not os.getenv('TELEGRAM_CHAT_ID'):
    print("⚠️  TELEGRAM_CHAT_ID not set - Telegram notifications may fail")
else:
    print("✅ TELEGRAM_CHAT_ID is set")

print()

if not checks_passed:
    print("❌ Cannot start bot - missing required environment variables!")
    print()
    print("Please set the following in your .env file:")
    print("  HYPERLIQUID_PRIVATE_KEY=your_private_key_here")
    print("  TELEGRAM_BOT_TOKEN=your_bot_token")
    print("  TELEGRAM_CHAT_ID=your_chat_id")
    print()
    exit(1)

print("="*80)
print("  Starting bot in 3 seconds...")
print("  Press Ctrl+C to cancel")
print("="*80)
print()

import time
time.sleep(3)

# Import and run the bot
from live_trading_bot import LiveTradingBot

if __name__ == "__main__":
    try:
        # Initialize bot in LIVE mode with 10% position sizing
        bot = LiveTradingBot(mode='LIVE', position_size_pct=10.0)

        # Start trading loop
        bot.run()

    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("  Bot stopped by user (Ctrl+C)")
        print("="*80)

    except Exception as e:
        print("\n\n" + "="*80)
        print(f"  ❌ Bot crashed: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
