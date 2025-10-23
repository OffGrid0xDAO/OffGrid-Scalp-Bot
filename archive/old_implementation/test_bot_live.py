#!/usr/bin/env python3
"""
Quick test to see if bot executes trades with current market data
"""
import os
from dotenv import load_dotenv

load_dotenv()

from dual_timeframe_bot_with_optimizer import DualTimeframeBotWithOptimizer

print("="*70)
print("TESTING BOT WITH LIVE MARKET DATA")
print("="*70)
print("\nThis will connect to live market and check for trade opportunities")
print("Auto-trade is DISABLED - will only show what it would do\n")

# Create bot with auto-trade DISABLED
bot = DualTimeframeBotWithOptimizer(
    private_key=os.getenv('HYPERLIQUID_PRIVATE_KEY'),
    use_testnet=True,
    auto_trade=False,  # DISABLED - just testing
    position_size_pct=0.1,
    leverage=25,
    min_confidence=0.70,  # Lower threshold to see more opportunities
    timeframe_short=1,
    timeframe_long=3,
    optimization_interval_minutes=30
)

print("\n" + "="*70)
print("Bot initialized - checking current market conditions...")
print("="*70 + "\n")
