#!/usr/bin/env python3
"""
🚀 LIVE TRADING BOT - START MANIFEST

This is your production trading bot entry point.

Usage:
    python start_manifest.py              # Interactive mode (asks for confirmation)
    python start_manifest.py --live       # Direct LIVE trading (no confirmation)
    python start_manifest.py --config custom.json  # Use custom config

Environment Variables Required:
    HYPERLIQUID_PRIVATE_KEY    - Your Hyperliquid wallet private key
    TELEGRAM_BOT_TOKEN         - Your Telegram bot token (optional)
    TELEGRAM_CHAT_ID           - Your Telegram chat ID (optional)

⚠️  WARNING: This will trade REAL MONEY on Hyperliquid mainnet!
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.live.trading_orchestrator import TradingOrchestrator


# Configuration
DEFAULT_CONFIG = {
    "symbol": "ETH",
    "initial_capital": 10000.0,
    "max_position_size": 0.3,  # 30% of capital
    "max_daily_loss": 0.05,    # 5% daily loss limit
    "max_drawdown": 0.15,      # 15% max drawdown
    "enable_telegram": True,
    "live_trading": True,      # THIS IS LIVE TRADING!
}


def load_config(config_path: str = None) -> dict:
    """Load configuration"""
    config = DEFAULT_CONFIG.copy()

    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            custom_config = json.load(f)
            config.update(custom_config)
            print(f"✅ Loaded config from {config_path}")

    return config


def check_environment() -> bool:
    """Check that required environment variables are set"""
    print("\n" + "="*60)
    print("🔍 ENVIRONMENT CHECK")
    print("="*60)

    all_ok = True

    # Check Hyperliquid private key
    if os.getenv('HYPERLIQUID_PRIVATE_KEY'):
        print("✅ HYPERLIQUID_PRIVATE_KEY is set")
    else:
        print("❌ HYPERLIQUID_PRIVATE_KEY not set!")
        print("   Add to .env file: HYPERLIQUID_PRIVATE_KEY=your_key_here")
        all_ok = False

    # Check Telegram (optional)
    if os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'):
        print("✅ TELEGRAM_BOT_TOKEN is set")
        print("✅ TELEGRAM_CHAT_ID is set")
    else:
        print("⚠️  Telegram not configured (optional)")
        print("   Add to .env: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")

    print("="*60 + "\n")
    return all_ok


def print_banner():
    """Print startup banner"""
    print("\n" + "="*60)
    print("🚀 LIVE TRADING BOT - PRODUCTION MODE")
    print("="*60)
    print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Exchange: Hyperliquid Mainnet")
    print(f"💰 Real Money Trading: ENABLED")
    print("="*60 + "\n")


def print_config(config: dict):
    """Print configuration"""
    print("📋 CONFIGURATION:")
    print("="*60)
    print(f"Symbol: {config['symbol']}")
    print(f"Initial Capital: ${config['initial_capital']:,.2f}")
    print(f"Max Position Size: {config['max_position_size']:.1%} of capital")
    print(f"Max Daily Loss: {config['max_daily_loss']:.1%}")
    print(f"Max Drawdown: {config['max_drawdown']:.1%}")
    print(f"Telegram Notifications: {'Enabled' if config['enable_telegram'] else 'Disabled'}")
    print(f"Trading Mode: {'🔴 LIVE' if config['live_trading'] else '📄 Paper'}")
    print("="*60 + "\n")


def confirm_start() -> bool:
    """Ask user for confirmation before starting"""
    print("⚠️  WARNING: You are about to start LIVE TRADING with REAL MONEY!")
    print("")
    print("This bot will:")
    print("  • Connect to Hyperliquid mainnet")
    print("  • Execute REAL market orders")
    print("  • Use REAL capital from your wallet")
    print("  • Automatically manage positions")
    print("")
    print("Risk Management:")
    print("  • Max position size: 30% of capital")
    print("  • Daily loss limit: 5%")
    print("  • Max drawdown: 15%")
    print("  • Automatic stop losses")
    print("")

    response = input("Type 'YES' (in caps) to confirm and start trading: ")

    return response == "YES"


async def main():
    """Main entry point"""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Live Trading Bot')
    parser.add_argument('--live', action='store_true',
                        help='Start immediately without confirmation')
    parser.add_argument('--config', type=str,
                        help='Path to custom config JSON file')
    parser.add_argument('--symbol', type=str, default='ETH',
                        help='Trading symbol (default: ETH)')
    parser.add_argument('--capital', type=float,
                        help='Initial capital (overrides config)')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Logging level')

    args = parser.parse_args()

    # Setup logging
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'trading_bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)

    # Load environment variables
    load_dotenv()

    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed!")
        print("Please configure required environment variables in .env file")
        sys.exit(1)

    # Load configuration
    config = load_config(args.config)

    # Override with command-line arguments
    if args.symbol:
        config['symbol'] = args.symbol
    if args.capital:
        config['initial_capital'] = args.capital

    # Print banner and config
    print_banner()
    print_config(config)

    # Confirmation (unless --live flag is used)
    if not args.live:
        if not confirm_start():
            print("\n❌ Start cancelled by user")
            sys.exit(0)

    print("\n✅ Starting trading bot...\n")

    # Extract optimized thresholds if available
    thresholds = config.get('optimized_thresholds', {})

    # Create orchestrator with ENHANCED parameters (supports Iterations 1-6)
    orchestrator = TradingOrchestrator(
        symbol=config['symbol'],
        initial_capital=config['initial_capital'],
        max_position_size=config['max_position_size'],
        enable_telegram=config['enable_telegram'],
        live_trading=config['live_trading'],
        # Iteration parameters
        compression_threshold=thresholds.get('compression_threshold', 80),
        alignment_threshold=thresholds.get('alignment_threshold', 80),
        confluence_threshold=thresholds.get('confluence_threshold', 55),
        n_harmonics=thresholds.get('n_harmonics', 5),
        max_holding_periods=thresholds.get('max_holding_periods', 24),
        min_confidence=thresholds.get('min_confidence', 0.65),
        min_coherence=thresholds.get('min_coherence', 0.6),
        # ENHANCED features (Iterations 4-6)
        use_volume_fft=thresholds.get('use_volume_fft', True),
        use_fib_levels=thresholds.get('use_fib_levels', True),
        volume_confirmation_weight=thresholds.get('volume_confirmation_weight', 0.15),
        fib_level_weight=thresholds.get('fib_level_weight', 0.1)
    )

    logger.info("="*60)
    logger.info("🚀 TRADING BOT STARTED")
    logger.info("="*60)

    try:
        # Start trading
        await orchestrator.start()

    except KeyboardInterrupt:
        logger.info("\n⚠️  Received shutdown signal (Ctrl+C)")
        print("\n🛑 Shutting down gracefully...")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error occurred: {e}")

    finally:
        # Always stop gracefully
        await orchestrator.stop()

        # Print final summary
        print("\n" + "="*60)
        print("📊 FINAL SUMMARY")
        print("="*60)

        status = orchestrator.execution.get_status()
        print(f"Final Capital: ${status['current_capital']:,.2f}")
        print(f"Total PnL: ${status['total_pnl']:,.2f}")
        print(f"Unrealized PnL: ${status['unrealized_pnl']:,.2f}")
        print(f"Closed Trades: {status['num_closed_trades']}")
        print(f"Open Positions: {status['num_positions']}")
        print("="*60)

        logger.info("Trading bot shutdown complete")
        print("\n✅ Bot stopped successfully\n")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted during startup")
        sys.exit(130)
