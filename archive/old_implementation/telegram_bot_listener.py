"""
Telegram Bot Command Listener
Listens for manual trade commands like /long, /short, /exit
Runs in background thread alongside the trading bot
"""

import os
import time
import requests
import threading
from datetime import datetime
from typing import Optional, Callable, Dict
from dotenv import load_dotenv

load_dotenv()


class TelegramBotListener:
    """
    Listen for Telegram commands and trigger manual trades
    """

    def __init__(self, on_long_command: Callable = None,
                 on_short_command: Callable = None,
                 on_exit_command: Callable = None,
                 on_status_command: Callable = None,
                 authorized_username: str = "lana0xpepe"):
        """
        Initialize Telegram bot listener

        Args:
            on_long_command: Callback when /long received
            on_short_command: Callback when /short received
            on_exit_command: Callback when /exit received
            on_status_command: Callback when /status received
            authorized_username: Only this Telegram username can execute trades
        """
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.authorized_username = authorized_username.lower().strip('@')
        self.enabled = bool(self.bot_token and self.chat_id)

        self.on_long_command = on_long_command
        self.on_short_command = on_short_command
        self.on_exit_command = on_exit_command
        self.on_status_command = on_status_command

        self.last_update_id = 0
        self.running = False
        self.listener_thread = None

        if not self.enabled:
            print("⚠️  Telegram bot listener disabled - set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        else:
            print(f"✅ Telegram bot listener initialized")
            print(f"🔐 Authorized user: @{self.authorized_username}")

    def get_updates(self, timeout: int = 30) -> list:
        """
        Get new messages from Telegram

        Args:
            timeout: Long polling timeout

        Returns:
            List of updates
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': timeout,
                'allowed_updates': ['message']
            }

            response = requests.get(url, params=params, timeout=timeout + 5)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', [])

            return []

        except Exception as e:
            print(f"⚠️  Telegram getUpdates error: {e}")
            return []

    def send_reply(self, text: str) -> bool:
        """Send a reply message"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            print(f"⚠️  Telegram reply error: {e}")
            return False

    def process_command(self, command: str, text: str, username: str = None):
        """
        Process a received command

        Args:
            command: The command (e.g., '/long')
            text: Full message text
            username: Telegram username of sender
        """
        command = command.lower().strip()

        print(f"\n📱 Telegram command received: {command} from @{username}")

        # Check authorization for trading commands
        is_authorized = (username and username.lower().strip('@') == self.authorized_username)

        if command == '/long':
            if not is_authorized:
                self.send_reply(f"🚫 UNAUTHORIZED\nOnly @{self.authorized_username} can execute trades.\nYour username: @{username}")
                print(f"⚠️  Unauthorized /long attempt from @{username}")
                return

            if self.on_long_command:
                self.send_reply("🟢 MANUAL LONG ENTRY\nExecuting trade...")
                result = self.on_long_command()
                if result:
                    self.send_reply(f"✅ Long position opened!\n{result}")
                else:
                    self.send_reply("❌ Long entry failed - check bot logs")
            else:
                self.send_reply("⚠️ Long command handler not configured")

        elif command == '/short':
            if not is_authorized:
                self.send_reply(f"🚫 UNAUTHORIZED\nOnly @{self.authorized_username} can execute trades.\nYour username: @{username}")
                print(f"⚠️  Unauthorized /short attempt from @{username}")
                return

            if self.on_short_command:
                self.send_reply("🔴 MANUAL SHORT ENTRY\nExecuting trade...")
                result = self.on_short_command()
                if result:
                    self.send_reply(f"✅ Short position opened!\n{result}")
                else:
                    self.send_reply("❌ Short entry failed - check bot logs")
            else:
                self.send_reply("⚠️ Short command handler not configured")

        elif command == '/exit':
            if not is_authorized:
                self.send_reply(f"🚫 UNAUTHORIZED\nOnly @{self.authorized_username} can execute trades.\nYour username: @{username}")
                print(f"⚠️  Unauthorized /exit attempt from @{username}")
                return

            if self.on_exit_command:
                self.send_reply("🚪 MANUAL EXIT\nClosing position...")
                result = self.on_exit_command()
                if result:
                    self.send_reply(f"✅ Position closed!\n{result}")
                else:
                    self.send_reply("❌ Exit failed - check bot logs or no position open")
            else:
                self.send_reply("⚠️ Exit command handler not configured")

        elif command == '/status':
            if self.on_status_command:
                status = self.on_status_command()
                self.send_reply(status)
            else:
                self.send_reply("⚠️ Status command handler not configured")

        elif command == '/help':
            help_text = """
🤖 <b>Manual Trading Commands</b>

<b>Trade Commands:</b>
/long - Open LONG position manually
/short - Open SHORT position manually
/exit - Close current position

<b>Info Commands:</b>
/status - Show current position & bot status
/help - Show this help message

<b>Note:</b> Manual trades are logged separately and used by Claude AI to learn from your gut feeling trades!
"""
            self.send_reply(help_text)

        else:
            self.send_reply(f"❓ Unknown command: {command}\nSend /help for available commands")

    def listen_loop(self):
        """Main listening loop - runs in background thread"""
        print("🎧 Telegram bot listener started - waiting for commands...")
        print("   Send /help to see available commands")

        while self.running:
            try:
                updates = self.get_updates(timeout=30)

                for update in updates:
                    # Update last_update_id
                    update_id = update.get('update_id', 0)
                    if update_id > self.last_update_id:
                        self.last_update_id = update_id

                    # Check if message is from authorized chat
                    message = update.get('message', {})
                    chat_id = str(message.get('chat', {}).get('id', ''))

                    if chat_id != self.chat_id:
                        continue  # Ignore messages from other chats

                    # Extract username
                    from_user = message.get('from', {})
                    username = from_user.get('username', 'unknown')

                    # Extract command
                    text = message.get('text', '').strip()

                    if text.startswith('/'):
                        # Extract just the command (first word)
                        command = text.split()[0] if ' ' in text else text
                        self.process_command(command, text, username=username)

            except KeyboardInterrupt:
                print("\n🛑 Telegram listener stopping...")
                break
            except Exception as e:
                print(f"⚠️  Listener loop error: {e}")
                time.sleep(5)  # Wait before retry

        print("✅ Telegram listener stopped")

    def start(self):
        """Start listening in background thread"""
        if not self.enabled:
            print("⚠️  Telegram bot listener not enabled")
            return False

        if self.running:
            print("⚠️  Telegram bot listener already running")
            return False

        self.running = True
        self.listener_thread = threading.Thread(
            target=self.listen_loop,
            daemon=True,
            name="TelegramListener"
        )
        self.listener_thread.start()

        return True

    def stop(self):
        """Stop listening"""
        self.running = False
        if self.listener_thread:
            self.listener_thread.join(timeout=5)


# Test the listener
if __name__ == '__main__':
    def test_long():
        print("📈 LONG command received!")
        return "Opened LONG at $3985.50"

    def test_short():
        print("📉 SHORT command received!")
        return "Opened SHORT at $3985.50"

    def test_exit():
        print("🚪 EXIT command received!")
        return "Closed position with +0.5% PnL"

    def test_status():
        return "🤖 Bot Status: RUNNING\n💼 Position: None\n📊 Mode: Rule-based trading"

    listener = TelegramBotListener(
        on_long_command=test_long,
        on_short_command=test_short,
        on_exit_command=test_exit,
        on_status_command=test_status
    )

    listener.start()

    print("\n✅ Listener running! Send commands to your Telegram bot:")
    print("   /long - Test long entry")
    print("   /short - Test short entry")
    print("   /exit - Test exit")
    print("   /status - Test status")
    print("   /help - Show help")
    print("\nPress Ctrl+C to stop...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        listener.stop()
