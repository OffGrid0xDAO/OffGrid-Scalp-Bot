#!/usr/bin/env python3
"""
Pre-flight Check - Verify bot is ready for live trading
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("="*80)
print("🔍 PRE-FLIGHT CHECK - Live Trading Bot")
print("="*80)
print()

# Check 1: Environment variables
print("1. Environment Variables:")
checks_passed = 0
checks_total = 0

checks_total += 1
if os.getenv('HYPERLIQUID_PRIVATE_KEY'):
    print("   ✅ HYPERLIQUID_PRIVATE_KEY is set")
    checks_passed += 1
else:
    print("   ❌ HYPERLIQUID_PRIVATE_KEY not set - bot cannot trade!")

checks_total += 1
if os.getenv('TELEGRAM_BOT_TOKEN'):
    print("   ✅ TELEGRAM_BOT_TOKEN is set")
    checks_passed += 1
else:
    print("   ⚠️  TELEGRAM_BOT_TOKEN not set - notifications disabled")
    checks_passed += 0.5

checks_total += 1
if os.getenv('TELEGRAM_CHAT_ID'):
    print("   ✅ TELEGRAM_CHAT_ID is set")
    checks_passed += 1
else:
    print("   ⚠️  TELEGRAM_CHAT_ID not set - notifications may fail")
    checks_passed += 0.5

print()

# Check 2: Required files
print("2. Required Files:")
required_files = [
    'live_trading_bot.py',
    'src/exchange/hyperliquid_client.py',
    'src/notifications/telegram_bot.py',
    'src/strategy/strategy_params.json',
    'src/strategy/entry_detector_user_pattern.py',
    'src/strategy/exit_manager_user_pattern.py',
]

for file in required_files:
    checks_total += 1
    if Path(file).exists():
        print(f"   ✅ {file}")
        checks_passed += 1
    else:
        print(f"   ❌ {file} - MISSING!")

print()

# Check 3: Exchange connection
print("3. Hyperliquid Connection:")
try:
    sys.path.insert(0, str(Path(__file__).parent / 'src'))
    from exchange.hyperliquid_client import HyperliquidClient

    # Test mainnet connection
    client = HyperliquidClient(testnet=False)
    checks_total += 1
    print("   ✅ Hyperliquid client initialized")
    checks_passed += 1

    # Try to get account info
    try:
        info = client.get_account_info()
        balance = float(info.get('marginSummary', {}).get('accountValue', 0))
        checks_total += 1
        if balance > 100:
            print(f"   ✅ Account connected - Balance: ${balance:.2f}")
            checks_passed += 1
        else:
            print(f"   ⚠️  Low balance: ${balance:.2f} - Recommend at least $200")
            checks_passed += 0.5
    except Exception as e:
        checks_total += 1
        print(f"   ❌ Cannot fetch account info: {e}")

except Exception as e:
    checks_total += 2
    print(f"   ❌ Hyperliquid client error: {e}")

print()

# Check 4: Telegram
print("4. Telegram Bot:")
try:
    from notifications.telegram_bot import TelegramBot
    telegram = TelegramBot()
    checks_total += 1

    if telegram.enabled:
        print("   ✅ Telegram bot initialized")
        checks_passed += 1

        # Try to send test message
        try:
            telegram.send_message("🧪 Test message from pre-flight check")
            checks_total += 1
            print("   ✅ Test message sent successfully")
            checks_passed += 1
        except Exception as e:
            checks_total += 1
            print(f"   ❌ Cannot send message: {e}")
    else:
        print("   ⚠️  Telegram disabled - notifications won't work")
        checks_passed += 0

except Exception as e:
    checks_total += 2
    print(f"   ❌ Telegram error: {e}")

print()

# Check 5: Strategy configuration
print("5. Strategy Configuration:")
try:
    import json
    with open('src/strategy/strategy_params.json') as f:
        params = json.load(f)

    checks_total += 1
    print(f"   ✅ Timeframe: {params.get('timeframe', 'N/A')}")
    checks_passed += 1

    checks_total += 1
    quality_min = params.get('entry_filters', {}).get('min_quality_score', 0)
    print(f"   ✅ Quality Score Min: {quality_min}")
    checks_passed += 1

    checks_total += 1
    sl = params.get('exit_strategy', {}).get('stop_loss_pct', 0)
    print(f"   ✅ Stop Loss: {sl}%")
    checks_passed += 1

    checks_total += 1
    tp = params.get('exit_strategy', {}).get('take_profit_levels', [0])[0]
    print(f"   ✅ Take Profit: {tp}%")
    checks_passed += 1

except Exception as e:
    checks_total += 4
    print(f"   ❌ Cannot read strategy params: {e}")

print()
print("="*80)

# Summary
pass_rate = (checks_passed / checks_total) * 100
print(f"Results: {checks_passed:.1f}/{checks_total} checks passed ({pass_rate:.0f}%)")

if pass_rate >= 90:
    print("✅ READY TO TRADE!")
    print()
    print("Start bot with: ./start_bot.sh")
elif pass_rate >= 70:
    print("⚠️  MOSTLY READY - Some issues detected")
    print("Review warnings above before starting")
else:
    print("❌ NOT READY - Critical issues detected")
    print("Fix errors above before starting bot")

print("="*80)
