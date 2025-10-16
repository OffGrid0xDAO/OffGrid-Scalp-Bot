"""
Quick-start script for dual timeframe bot
Uses all settings from .env file (no interactive prompts)
"""

import os
from dotenv import load_dotenv
from eth_account import Account
from dual_timeframe_bot import DualTimeframeBot

# Load environment
load_dotenv()

def main():
    print("╔" + "="*78 + "╗")
    print("║" + " "*16 + "DUAL TIMEFRAME BOT - QUICK START" + " "*31 + "║")
    print("╚" + "="*78 + "╝")

    # Load all settings from .env
    private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')
    if not private_key:
        print("\n❌ ERROR: HYPERLIQUID_PRIVATE_KEY not found in .env file")
        return

    use_testnet = os.getenv('USE_TESTNET', 'true').lower() == 'true'
    auto_trade = os.getenv('AUTO_TRADE', 'true').lower() == 'true'
    position_size_pct = float(os.getenv('POSITION_SIZE_PCT', '10')) / 100
    leverage = int(os.getenv('LEVERAGE', '25'))
    min_confidence = float(os.getenv('MIN_CONFIDENCE', '0.75'))

    # Display config
    print("\n📊 CONFIGURATION (from .env):")
    print("─"*80)
    print(f"  Network: {'TESTNET 🧪' if use_testnet else '⚠️  MAINNET 💰'}")
    print(f"  Auto-Trading: {'✅ ENABLED' if auto_trade else '❌ DISABLED'}")
    print(f"  Position Size: {position_size_pct*100:.1f}%")
    print(f"  Leverage: {leverage}x")
    print(f"  Min Confidence: {min_confidence:.0%}")
    print(f"  Timeframes: 5min + 15min")
    print(f"  AI: Claude Sonnet 4.5")

    # Check API key
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_key or anthropic_key == 'your_anthropic_api_key_here':
        print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set!")
        print("   Add your Claude API key to .env file")
        print("   Get one at: https://console.anthropic.com/")
        response = input("\n   Continue without Claude AI? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("\n✓ Cancelled - Add API key and try again")
            return
    else:
        print(f"  Claude API: ✅ Configured")

    print("─"*80)

    # Confirmation
    if not use_testnet:
        print("\n" + "⚠️ "*20)
        print("WARNING: YOU ARE USING MAINNET WITH REAL MONEY!")
        print("⚠️ "*20)
        confirm = input("\nType 'I UNDERSTAND' to continue: ").strip()
        if confirm != 'I UNDERSTAND':
            print("\n✓ Cancelled")
            return

    print("\n✅ Starting bot in 3 seconds...")
    print("   Press Ctrl+C to stop at any time\n")

    import time
    time.sleep(3)

    # Create and run bot
    bot = DualTimeframeBot(
        private_key=private_key,
        use_testnet=use_testnet,
        auto_trade=auto_trade,
        position_size_pct=position_size_pct,
        leverage=leverage,
        min_confidence=min_confidence
    )
    bot.monitor()


if __name__ == "__main__":
    main()
