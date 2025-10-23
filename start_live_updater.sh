#!/bin/bash
#
# Start Live Data Updater
#
# This script starts the continuous data updater for live trading bot.
# It will:
# - Fetch new candles from Hyperliquid every 5 minutes
# - Recalculate indicators automatically
# - Optionally regenerate charts
#
# Usage:
#   ./start_live_updater.sh              # Update data + indicators (no charts)
#   ./start_live_updater.sh --charts     # Update data + indicators + charts
#   ./start_live_updater.sh --interval 15 --charts  # Custom interval with charts
#

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 STARTING LIVE DATA UPDATER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will continuously update trading data from Hyperliquid"
echo "Press Ctrl+C to stop"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Default settings
INTERVAL=5
CHARTS_FLAG=""

# Parse arguments
for arg in "$@"; do
    case $arg in
        --charts)
            CHARTS_FLAG="--charts"
            echo "📈 Chart regeneration: ENABLED"
            ;;
        --interval)
            shift
            INTERVAL=$1
            shift
            ;;
        --interval=*)
            INTERVAL="${arg#*=}"
            ;;
    esac
done

echo "⏱️  Update interval: ${INTERVAL} minutes"
echo ""

# Run the updater
python3 scripts/update_from_hyperliquid.py --continuous --interval ${INTERVAL} ${CHARTS_FLAG}
