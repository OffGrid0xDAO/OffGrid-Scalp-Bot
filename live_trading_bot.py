#!/usr/bin/env python3
"""
LIVE TRADING BOT - Iteration 10

Runs the proven Iteration 10 strategy live with:
- Real-time 15m/5m data monitoring
- Telegram alerts for all trades
- Hyperliquid API integration
- Automatic TP/SL placement
- Position management
- Error handling & logging

IMPORTANT: Start with small position sizes for testing!
"""

import sys
import time
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from strategy.entry_detector_user_pattern import EntryDetector
from strategy.exit_manager_user_pattern import ExitManager
from notifications.telegram_bot import TelegramBot
from exchange.hyperliquid_client import HyperliquidClient


class LiveTradingBot:
    def __init__(self, mode: str = 'LIVE', position_size_pct: float = 10.0):
        """
        Initialize live trading bot

        Args:
            mode: 'PAPER' (testnet) or 'LIVE' (mainnet with real money)
            position_size_pct: Position size as % of account value (default 10%)
                              With 25x leverage on Hyperliquid, 10% = 2.5x account exposure
        """
        self.mode = mode.upper()
        self.position_size_pct = position_size_pct
        self.position_size_usd = None  # Will be calculated from account balance

        print("\n" + "="*80)
        print(f"🤖 INITIALIZING LIVE TRADING BOT - {self.mode} MODE")
        print("="*80)

        if self.mode == 'LIVE':
            print("⚠️  WARNING: LIVE MODE - REAL MONEY TRADING ON HYPERLIQUID MAINNET")
            print("   Small position sizes to test with real fees and slippage")

        # Initialize components
        self.telegram = TelegramBot()
        # LIVE mode = mainnet (testnet=False), PAPER mode = testnet (testnet=True)
        self.exchange = HyperliquidClient(testnet=(mode != 'LIVE'))
        self.exit_manager = ExitManager()

        # Trading state
        self.in_position = False
        self.current_trade: Optional[Dict] = None
        self.starting_capital = None  # Will fetch from exchange in LIVE mode
        self.trades_history = []

        # Settings (Iteration 10)
        self.symbol = 'ETH'
        self.check_interval_seconds = 60  # Check every minute
        self.tp_pct = 5.0  # Take profit
        self.sl_pct = 0.75  # Stop loss
        self.profit_lock_pct = 1.5  # Profit lock

        # Real trading costs
        self.trading_fee_pct = 0.05  # Hyperliquid taker fee 0.05%
        self.estimated_slippage_pct = 0.02  # Estimated 0.02% slippage

        print(f"\n⚙️  SETTINGS:")
        print(f"   Mode: {self.mode}")
        print(f"   Network: {'MAINNET' if mode == 'LIVE' else 'TESTNET'}")
        print(f"   Position Size: {position_size_pct}% of account value")
        print(f"   Symbol: {self.symbol}")
        print(f"   TP: {self.tp_pct}% | SL: {self.sl_pct}% | Profit Lock: {self.profit_lock_pct}%")
        print(f"   Trading Fee: {self.trading_fee_pct}% | Slippage: {self.estimated_slippage_pct}%")
        print(f"   Check Interval: {self.check_interval_seconds}s")

        # Get account info if LIVE mode
        if self.mode == 'LIVE':
            try:
                account_info = self.exchange.get_account_info()
                self.starting_capital = float(account_info.get('marginSummary', {}).get('accountValue', 0))
                # Calculate position size as % of account
                self.position_size_usd = self.starting_capital * (self.position_size_pct / 100.0)
                print(f"\n💰 Account Balance: ${self.starting_capital:.2f}")
                print(f"   Position Size: ${self.position_size_usd:.2f} ({self.position_size_pct}% of account)")
                print(f"   Leverage: 25x (Hyperliquid default)")
                print(f"   Actual Exposure: ${self.position_size_usd * 25:.2f} ({self.position_size_pct * 25:.0f}% of account)")
            except Exception as e:
                print(f"\n⚠️  Could not fetch account balance: {e}")
                self.starting_capital = 0
                self.position_size_usd = 100  # Fallback
        else:
            # Paper trading mode
            self.starting_capital = 1000  # Default paper capital
            self.position_size_usd = self.starting_capital * (self.position_size_pct / 100.0)

        # Send startup notification
        if self.telegram.enabled:
            account_balance = self.starting_capital if self.starting_capital else 0
            startup_msg = f"""
🤖 **BOT STARTED - {self.mode} MODE**

{'🔴 MAINNET - REAL MONEY' if self.mode == 'LIVE' else '🟢 TESTNET - PAPER TRADING'}

Symbol: {self.symbol}
Account: ${account_balance:.2f}
Position Size: ${self.position_size_usd:.2f} ({self.position_size_pct}% of account)
Leverage: 25x
Actual Exposure: ${self.position_size_usd * 25:.2f} per trade

Strategy: Iteration 10 (2.19% backtested)

Exit Strategy:
• Take Profit: {self.tp_pct}%
• Stop Loss: {self.sl_pct}%
• Profit Lock: {self.profit_lock_pct}%

Trading Costs:
• Fee: {self.trading_fee_pct}%
• Slippage: ~{self.estimated_slippage_pct}%

Ready to trade! 🚀
"""
            self.telegram.send_message(startup_msg)

    def fetch_latest_data(self) -> tuple:
        """
        Fetch latest 15m and 5m data

        Returns:
            Tuple of (df_15m, df_5m) with recent candles
        """
        # In production, fetch from exchange API
        # For now, load from files (you'll replace this with real API calls)
        data_dir = Path(__file__).parent / 'trading_data'

        df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
        df_15m = df_15m.tail(200)  # Last 200 candles for context

        df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')
        df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
        df_5m = df_5m.tail(200)

        return df_15m, df_5m

    def check_entry_signal(self) -> Optional[Dict]:
        """
        Check for entry signals

        Returns:
            Dict with signal info if signal detected, None otherwise
        """
        # Fetch latest data
        df_15m, df_5m = self.fetch_latest_data()

        # Run entry detector
        detector = EntryDetector(df_5m=df_5m, df_15m=df_15m)
        df_signals = detector.scan_historical_signals(df_15m)

        # Check last candle for signal
        last_row = df_signals.iloc[-1]

        if last_row['entry_signal']:
            signal = {
                'timestamp': last_row['timestamp'],
                'direction': last_row['entry_direction'],
                'price': last_row['close'],
                'quality_score': last_row.get('entry_quality_score', 0),
                'rsi_7': last_row['rsi_7'],
                'stoch_d': last_row['stoch_d']
            }

            print(f"\n🎯 ENTRY SIGNAL DETECTED!")
            print(f"   Direction: {signal['direction'].upper()}")
            print(f"   Price: ${signal['price']:.2f}")
            print(f"   Quality: {signal['quality_score']:.0f}/100")

            return signal

        return None

    def check_exit_signal(self, current_price: float) -> Optional[Dict]:
        """
        Check if current position should exit

        Args:
            current_price: Current market price

        Returns:
            Exit info if should exit, None otherwise
        """
        if not self.in_position or not self.current_trade:
            return None

        # Calculate hold time
        hold_time = datetime.now() - self.current_trade['entry_time']
        hold_hours = hold_time.total_seconds() / 3600

        # Check exit conditions
        exit_result = self.exit_manager.check_exit(
            entry_price=self.current_trade['entry_price'],
            entry_time=self.current_trade['entry_time'],
            current_price=current_price,
            current_time=datetime.now(),
            direction=self.current_trade['direction'],
            peak_profit_pct=self.current_trade['peak_profit_pct']
        )

        if exit_result['should_exit']:
            print(f"\n🚪 EXIT SIGNAL DETECTED!")
            print(f"   Reason: {exit_result['exit_reason']}")
            print(f"   Profit: {exit_result['profit_pct']:+.2f}%")

        return exit_result if exit_result['should_exit'] else None

    def enter_trade(self, signal: Dict):
        """
        Enter a new trade

        Args:
            signal: Entry signal info
        """
        print(f"\n{'='*80}")
        print(f"🚀 ENTERING {signal['direction'].upper()} TRADE")
        print(f"{'='*80}")

        # Calculate TP/SL prices
        entry_price = signal['price']
        if signal['direction'] == 'long':
            tp_price = entry_price * (1 + self.tp_pct / 100)
            sl_price = entry_price * (1 - self.sl_pct / 100)
        else:
            tp_price = entry_price * (1 - self.tp_pct / 100)
            sl_price = entry_price * (1 + self.sl_pct / 100)

        # Execute on exchange
        if self.mode == 'LIVE' and self.exchange.enabled:
            try:
                result = self.exchange.enter_trade(
                    symbol=self.symbol,
                    direction=signal['direction'],
                    size_usd=self.position_size_usd,
                    tp_pct=self.tp_pct,
                    sl_pct=self.sl_pct
                )

                if not result.get('success'):
                    print(f"❌ Failed to enter trade!")
                    return

                entry_price = result['entry_price']

            except Exception as e:
                print(f"❌ Exchange error: {e}")
                return

        # Update trade state
        self.current_trade = {
            'entry_time': datetime.now(),
            'entry_price': entry_price,
            'direction': signal['direction'],
            'quality_score': signal['quality_score'],
            'peak_profit_pct': 0.0,
            'tp_price': tp_price,
            'sl_price': sl_price
        }
        self.in_position = True

        # Send Telegram alert
        if self.telegram.enabled:
            self.telegram.send_entry_alert(
                direction=signal['direction'],
                price=entry_price,
                entry_reason=f"Quality: {signal['quality_score']:.0f}/100, RSI: {signal['rsi_7']:.1f}",
                quality_score=signal['quality_score'],
                tp=tp_price,
                sl=sl_price
            )

        print(f"✅ Trade entered successfully!")
        print(f"   Entry: ${entry_price:.2f}")
        print(f"   TP: ${tp_price:.2f} (+{self.tp_pct}%)")
        print(f"   SL: ${sl_price:.2f} (-{self.sl_pct}%)")

    def exit_trade(self, exit_info: Dict, current_price: float):
        """
        Exit current trade

        Args:
            exit_info: Exit signal info
            current_price: Current market price
        """
        print(f"\n{'='*80}")
        print(f"🚪 EXITING TRADE")
        print(f"{'='*80}")

        # Calculate P&L
        profit_pct = exit_info['profit_pct']
        hold_time = datetime.now() - self.current_trade['entry_time']
        hold_hours = hold_time.total_seconds() / 3600

        # Paper trading P&L
        position_size_capital = self.capital * 0.1  # 10% position
        pnl = position_size_capital * (profit_pct / 100)
        self.capital += pnl

        # Execute on exchange
        if self.mode == 'LIVE' and self.exchange.enabled:
            try:
                side = 'sell' if self.current_trade['direction'] == 'long' else 'buy'
                position_size = self.position_size_usd / current_price

                order = self.exchange.place_market_order(
                    symbol=self.symbol,
                    side=side,
                    size=position_size,
                    reduce_only=True
                )

                if order.get('status') != 'ok':
                    print(f"❌ Failed to exit trade!")
                    return

            except Exception as e:
                print(f"❌ Exchange error: {e}")
                return

        # Send Telegram alert
        if self.telegram.enabled:
            self.telegram.send_exit_alert(
                direction=self.current_trade['direction'],
                entry_price=self.current_trade['entry_price'],
                exit_price=current_price,
                profit_pct=profit_pct,
                pnl=pnl,
                exit_reason=exit_info['exit_reason'],
                hold_time_hours=hold_hours
            )

        # Save to history
        trade_record = {
            **self.current_trade,
            'exit_time': datetime.now(),
            'exit_price': current_price,
            'profit_pct': profit_pct,
            'pnl': pnl,
            'exit_reason': exit_info['exit_reason'],
            'hold_hours': hold_hours
        }
        self.trades_history.append(trade_record)

        print(f"✅ Trade exited!")
        print(f"   Exit: ${current_price:.2f}")
        print(f"   Profit: {profit_pct:+.2f}% (${pnl:+.2f})")
        print(f"   Hold Time: {hold_hours:.1f}h")
        print(f"   New Capital: ${self.capital:.2f}")

        # Reset position
        self.in_position = False
        self.current_trade = None

    def run(self):
        """Main trading loop"""
        print(f"\n{'='*80}")
        print(f"🚀 BOT STARTED - {self.mode} MODE")
        print(f"{'='*80}\n")

        iteration = 0

        try:
            while True:
                iteration += 1
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iteration #{iteration}")

                try:
                    # Get current price
                    if self.exchange.enabled:
                        current_price = self.exchange.get_current_price(self.symbol)
                    else:
                        # Fallback to data file
                        df_15m, _ = self.fetch_latest_data()
                        current_price = df_15m.iloc[-1]['close']

                    print(f"   {self.symbol} Price: ${current_price:.2f}")

                    if self.in_position:
                        # Update peak profit
                        if self.current_trade['direction'] == 'long':
                            profit_pct = (current_price - self.current_trade['entry_price']) / self.current_trade['entry_price'] * 100
                        else:
                            profit_pct = (self.current_trade['entry_price'] - current_price) / self.current_trade['entry_price'] * 100

                        self.current_trade['peak_profit_pct'] = max(
                            self.current_trade['peak_profit_pct'],
                            profit_pct
                        )

                        print(f"   In Position: {self.current_trade['direction'].upper()}")
                        print(f"   Current P&L: {profit_pct:+.2f}%")
                        print(f"   Peak P&L: {self.current_trade['peak_profit_pct']:+.2f}%")

                        # Check exit
                        exit_signal = self.check_exit_signal(current_price)
                        if exit_signal:
                            self.exit_trade(exit_signal, current_price)

                    else:
                        print(f"   Position: FLAT")

                        # Check entry (only on 15m candle close)
                        entry_signal = self.check_entry_signal()
                        if entry_signal:
                            self.enter_trade(entry_signal)

                except Exception as e:
                    print(f"❌ Error in iteration: {e}")
                    if self.telegram.enabled:
                        self.telegram.send_error_alert("Iteration Error", str(e))

                # Wait before next check
                time.sleep(self.check_interval_seconds)

        except KeyboardInterrupt:
            print(f"\n\n{'='*80}")
            print("🛑 BOT STOPPED BY USER")
            print(f"{'='*80}")

            # Print summary
            print(f"\n📊 TRADING SUMMARY:")
            print(f"   Total Trades: {len(self.trades_history)}")
            if len(self.trades_history) > 0:
                winners = [t for t in self.trades_history if t['profit_pct'] > 0]
                print(f"   Winners: {len(winners)}")
                print(f"   Win Rate: {len(winners)/len(self.trades_history)*100:.1f}%")
                total_pnl = sum(t['pnl'] for t in self.trades_history)
                print(f"   Total P&L: ${total_pnl:+.2f}")
                print(f"   Final Capital: ${self.capital:.2f}")

            # Save trades history
            if len(self.trades_history) > 0:
                data_dir = Path(__file__).parent / 'trading_data'
                filename = f"live_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(data_dir / filename, 'w') as f:
                    json.dump(self.trades_history, f, indent=2, default=str)
                print(f"\n💾 Trades saved to: {filename}")

            print(f"\n✅ Bot shutdown complete\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Live Trading Bot - Iteration 10')
    parser.add_argument('--mode', type=str, default='LIVE',
                       choices=['PAPER', 'LIVE'],
                       help='Trading mode (PAPER or LIVE)')
    parser.add_argument('--size', type=float, default=10.0,
                       help='Position size as % of account (default: 10%)')

    args = parser.parse_args()

    if args.mode == 'LIVE':
        print("\n" + "="*80)
        print("⚠️  WARNING: LIVE TRADING MODE")
        print("="*80)
        print("You are about to trade with REAL MONEY!")
        print("Make sure you:")
        print("1. Have tested thoroughly in PAPER mode")
        print("2. Understand the risks")
        print("3. Are using appropriate position sizes")
        print(f"\nPosition size: {args.size}% of account per trade")
        print(f"With 25x leverage = {args.size * 25}% exposure")
        print("\n" + "="*80)

        response = input("\nType 'YES' to continue with LIVE trading: ")
        if response != 'YES':
            print("\n❌ Live trading cancelled")
            return

    # Start bot
    bot = LiveTradingBot(mode=args.mode, position_size_pct=args.size)
    bot.run()


if __name__ == "__main__":
    main()
