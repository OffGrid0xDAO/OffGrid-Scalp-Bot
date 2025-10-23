#!/usr/bin/env python3
"""
Telegram Bot for Trading Alerts

Sends notifications for:
- New trade entries
- Trade exits
- Daily PnL summaries
- System errors

Setup:
1. Create a bot via @BotFather on Telegram
2. Get your bot token
3. Get your chat ID (send /start to your bot, then check updates)
4. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
"""

import os
import requests
from typing import Optional
from datetime import datetime


class TelegramBot:
    def __init__(self):
        """Initialize Telegram bot"""
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not self.token or not self.chat_id:
            print("⚠️  WARNING: Telegram credentials not set!")
            print("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
            self.enabled = False
        else:
            self.enabled = True
            print("✅ Telegram bot initialized")

    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Send a message via Telegram

        Args:
            message: Message text (supports HTML formatting)
            parse_mode: 'HTML' or 'Markdown'

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            print(f"📱 [Telegram disabled] {message}")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            return True

        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False

    def send_entry_alert(self, direction: str, price: float,
                        entry_reason: str, quality_score: float,
                        tp: float, sl: float) -> bool:
        """
        Send trade entry alert

        Args:
            direction: 'long' or 'short'
            price: Entry price
            entry_reason: Why we entered
            quality_score: Signal quality
            tp: Take profit price
            sl: Stop loss price
        """
        emoji = "🟢" if direction == "long" else "🔴"
        direction_upper = direction.upper()

        message = f"""
{emoji} <b>NEW {direction_upper} ENTRY</b> {emoji}

📊 <b>Entry Price:</b> ${price:.2f}
📈 <b>Take Profit:</b> ${tp:.2f} (+5.0%)
🛑 <b>Stop Loss:</b> ${sl:.2f} (-0.75%)

⭐ <b>Quality Score:</b> {quality_score:.0f}/100
💡 <b>Reason:</b> {entry_reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message)

    def send_exit_alert(self, direction: str, entry_price: float,
                       exit_price: float, profit_pct: float,
                       pnl: float, exit_reason: str,
                       hold_time_hours: float) -> bool:
        """
        Send trade exit alert

        Args:
            direction: 'long' or 'short'
            entry_price: Entry price
            exit_price: Exit price
            profit_pct: Profit percentage
            pnl: Dollar P&L
            exit_reason: Why we exited
            hold_time_hours: How long we held the position
        """
        emoji = "✅" if profit_pct > 0 else "❌"
        direction_upper = direction.upper()

        message = f"""
{emoji} <b>{direction_upper} EXIT</b> {emoji}

📊 <b>Entry:</b> ${entry_price:.2f}
📊 <b>Exit:</b> ${exit_price:.2f}

💰 <b>Profit:</b> {profit_pct:+.2f}% (${pnl:+.2f})
⏱️ <b>Hold Time:</b> {hold_time_hours:.1f}h

💡 <b>Exit Reason:</b> {exit_reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message)

    def send_daily_summary(self, date: str, trades_today: int,
                          winners: int, losers: int,
                          daily_pnl: float, total_capital: float) -> bool:
        """
        Send daily performance summary

        Args:
            date: Date string
            trades_today: Number of trades
            winners: Number of winning trades
            losers: Number of losing trades
            daily_pnl: Daily P&L
            total_capital: Current total capital
        """
        emoji = "📈" if daily_pnl > 0 else "📉"

        message = f"""
{emoji} <b>DAILY SUMMARY - {date}</b> {emoji}

📊 <b>Trades:</b> {trades_today} ({winners}W / {losers}L)
💰 <b>Daily P&L:</b> ${daily_pnl:+.2f}
💵 <b>Total Capital:</b> ${total_capital:.2f}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message)

    def send_error_alert(self, error_type: str, error_message: str) -> bool:
        """
        Send error alert

        Args:
            error_type: Type of error
            error_message: Error details
        """
        message = f"""
🚨 <b>ERROR ALERT</b> 🚨

⚠️ <b>Type:</b> {error_type}
📝 <b>Details:</b> {error_message}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>Please check the logs and take action if needed.</i>
"""
        return self.send_message(message)

    def send_startup_message(self, mode: str, capital: float) -> bool:
        """
        Send bot startup notification

        Args:
            mode: 'LIVE' or 'PAPER'
            capital: Starting capital
        """
        message = f"""
🤖 <b>TRADING BOT STARTED</b> 🤖

🔧 <b>Mode:</b> {mode}
💵 <b>Starting Capital:</b> ${capital:.2f}
📊 <b>Strategy:</b> Iteration 10
⏱️ <b>Timeframe:</b> 15m

⚙️ <b>Settings:</b>
   • Take Profit: 5.0%
   • Stop Loss: 0.75%
   • Position Size: 10%
   • Max Hold: 48h

✅ Bot is ready to trade!

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message)

    def send_test_message(self) -> bool:
        """Send a test message to verify connection"""
        message = """
🧪 <b>TEST MESSAGE</b> 🧪

✅ Telegram bot connection successful!

If you see this, your bot is configured correctly.
"""
        return self.send_message(message)


def test_telegram():
    """Test Telegram bot connection"""
    print("\n" + "="*60)
    print("🧪 TESTING TELEGRAM BOT")
    print("="*60)

    bot = TelegramBot()

    if not bot.enabled:
        print("\n❌ Telegram bot not configured!")
        print("\nTo set up Telegram notifications:")
        print("1. Message @BotFather on Telegram")
        print("2. Create a new bot with /newbot")
        print("3. Copy your bot token")
        print("4. Start a chat with your bot")
        print("5. Get your chat ID from: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
        print("6. Add to .env file:")
        print("   TELEGRAM_BOT_TOKEN=your_token_here")
        print("   TELEGRAM_CHAT_ID=your_chat_id_here")
        return

    print("\n📱 Sending test message...")
    if bot.send_test_message():
        print("✅ Test message sent successfully!")
        print("\n📱 Check your Telegram to confirm!")
    else:
        print("❌ Failed to send test message")
        print("   Check your token and chat ID")

    print("\n" + "="*60)


if __name__ == "__main__":
    test_telegram()
