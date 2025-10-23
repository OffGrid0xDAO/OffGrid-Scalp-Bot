#!/bin/bash

# Trading Bot Startup Script
# Ensures clean start with proper logging

echo "🚀 Starting Trading Bot..."
echo ""

# Check if bot is already running
if pgrep -f "python3 main.py" > /dev/null; then
    echo "⚠️  Bot is already running!"
    echo "   Kill it first with: pkill -f 'python3 main.py'"
    read -p "   Kill and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   Stopping existing bot..."
        pkill -f "python3 main.py"
        sleep 2
        echo "   ✅ Stopped"
    else
        echo "   Exiting..."
        exit 1
    fi
fi

# Check for required files
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found!"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Check for historical data
if [ -f "trading_data/ema_data_5min.csv" ]; then
    file_size=$(stat -f%z "trading_data/ema_data_5min.csv" 2>/dev/null || stat -c%s "trading_data/ema_data_5min.csv" 2>/dev/null)
    echo "📊 Historical data found: $(echo "scale=1; $file_size/1048576" | bc)MB"
    echo "   Bot will run IMMEDIATE optimization with all data!"
    echo ""
fi

# Start the bot
echo "🎯 Starting bot with auto-optimization..."
echo "   - Trading: FREE (rule-based)"
echo "   - Optimization: Every 30 minutes"
echo "   - Press Ctrl+C to stop"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Use caffeinate to prevent sleep (macOS)
if command -v caffeinate &> /dev/null; then
    caffeinate -i python3 main.py
else
    python3 main.py
fi
