#!/bin/bash
# Quick setup script for Trading Bot

echo "=========================================="
echo "Trading Bot - Quick Setup"
echo "=========================================="

# Check Python version
echo ""
echo "Checking Python version..."
python3 --version

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install anthropic pandas numpy plotly requests python-dotenv

# Create .env if doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"
    echo "   Get your key at: https://console.anthropic.com/"
else
    echo ""
    echo "✅ .env file already exists"
fi

# Check for data
echo ""
echo "Checking for historical data..."
if [ -f "trading_data/indicators/eth_1h_full.csv" ]; then
    echo "✅ Historical data found (eth_1h_full.csv)"
else
    echo "⚠️  Historical data not found"
    echo "   You'll need to fetch and process data first"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your ANTHROPIC_API_KEY"
echo "2. Run optimization:"
echo "   python3 scripts/optimize_strategy.py --iterations 5 --timeframe 1h"
echo ""
echo "Or read QUICKSTART.md for detailed instructions."
echo ""
