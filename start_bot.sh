#!/bin/bash
###############################################################################
# START LIVE TRADING BOT - Iteration 10 Strategy (2.19% Proven Profit)
# HYPERLIQUID MAINNET - REAL MONEY TRADING WITH SMALL POSITIONS
###############################################################################

echo "================================================================================"
echo "  🔴 LIVE TRADING BOT - HYPERLIQUID MAINNET"
echo "  Iteration 10 Strategy with Real Fees & Slippage"
echo "================================================================================"
echo ""
echo "⚠️  WARNING: REAL MONEY TRADING MODE"
echo "    This bot will trade on Hyperliquid mainnet with real funds"
echo "    Position size: 10% of account per trade (25x leverage = 250% exposure)"
echo ""
echo "Strategy Performance (Backtest):"
echo "  • Return: +2.19%"
echo "  • Win Rate: 41%"
echo "  • Total Trades: 39"
echo "  • Avg Win: +2.85%"
echo "  • Avg Loss: -1.03%"
echo ""
echo "Strategy Settings:"
echo "  • Timeframe: 15min"
echo "  • Quality Score Min: 50"
echo "  • Stop Loss: 0.75%"
echo "  • Profit Lock: 1.5% (won't let trade go negative after +1.5%)"
echo "  • Take Profit: 5.0%"
echo ""
echo "Real Trading Costs:"
echo "  • Trading Fee: 0.05% (Hyperliquid taker fee)"
echo "  • Estimated Slippage: ~0.02%"
echo "  • Total Cost per Trade: ~0.07%"
echo ""
echo "================================================================================"
echo ""

# Check environment variables
echo "🔍 Checking environment..."

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "⚠️  ANTHROPIC_API_KEY not set - will fail during optimization"
else
  echo "✅ ANTHROPIC_API_KEY is set"
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "⚠️  TELEGRAM_BOT_TOKEN not set - Telegram reporting will be disabled"
else
  echo "✅ TELEGRAM_BOT_TOKEN is set"
fi

if [ -f .env ]; then
  echo "✅ .env file exists"
else
  echo "❌ No .env file found"
fi

echo ""
echo "================================================================================"
echo "  Starting bot in 5 seconds..."
echo "  Press Ctrl+C to cancel"
echo "================================================================================"
echo ""

sleep 5

# Run the bot
python3 live_trading_bot.py

# If bot exits, show message
echo ""
echo "================================================================================"
echo "  Bot stopped"
echo "================================================================================"
