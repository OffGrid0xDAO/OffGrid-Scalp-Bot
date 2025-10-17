"""
Interactive Manual Trading Mode
Chat with Claude about market conditions and manually execute trades
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from eth_account import Account

# Import bot components
from dual_timeframe_bot import DualTimeframeBot
from claude_trader import ClaudeTrader

load_dotenv()


class InteractiveTrader(DualTimeframeBot):
    """
    Interactive trading mode - chat with Claude and manually execute trades
    """

    def __init__(self, *args, **kwargs):
        # Force auto_trade to False for manual mode
        kwargs['auto_trade'] = False
        super().__init__(*args, **kwargs)
        self.interactive_mode = True

    def chat_with_claude(self, user_question: str):
        """
        Ask Claude a custom question about the market

        Args:
            user_question: Your question to Claude

        Returns:
            Claude's response
        """
        if not self.claude:
            return "Claude AI not available"

        # Format current market state
        formatted_5min = self.claude.format_ema_data(
            "5min",
            self.data_5min['indicators'],
            self.data_5min['state'],
            self.data_5min['ema_groups'],
            self.data_5min['price']
        )

        formatted_15min = self.claude.format_ema_data(
            "15min",
            self.data_15min['indicators'],
            self.data_15min['state'],
            self.data_15min['ema_groups'],
            self.data_15min['price']
        )

        # Format position info
        pos = self.get_position()
        position_str = "NONE"
        if pos:
            position_str = f"{pos['side'].upper()} {pos['size']:.4f} @ ${pos['entry_price']:.2f} (PnL: ${pos.get('unrealized_pnl', 0):+.2f})"

        try:
            prompt = f"""You are a trading analyst helping a trader understand the market.

CURRENT MARKET STATE:

5-MINUTE TIMEFRAME:
{formatted_5min}

15-MINUTE TIMEFRAME:
{formatted_15min}

CURRENT POSITION: {position_str}

TRADER'S QUESTION:
{user_question}

Provide a detailed, helpful answer. Be conversational and practical. If they ask about entry/exit,
give your honest assessment based on Annii's Ribbon Strategy (green ribbon = long bias, red ribbon = short bias,
yellow EMAs = support/resistance, outer bands spreading = potential pullback).

Answer their question directly and provide actionable insights."""

            response = self.claude.client.messages.create(
                model=self.claude.model,
                max_tokens=1024,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Track cost
            usage = response.usage
            input_tokens = getattr(usage, 'input_tokens', 0)
            output_tokens = getattr(usage, 'output_tokens', 0)
            self.claude.total_input_tokens += input_tokens
            self.claude.total_output_tokens += output_tokens
            self.claude.total_calls += 1

            call_cost = (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0
            self.claude.session_cost += call_cost

            print(f"💵 Chat cost: ${call_cost:.4f}")

            return response.content[0].text.strip()

        except Exception as e:
            return f"Error communicating with Claude: {str(e)}"

    def manual_trade(self, action: str):
        """
        Manually execute a trade

        Args:
            action: 'long', 'short', or 'close'

        Returns:
            Success message or error
        """
        current_price = self.data_5min['price'] or self.data_15min['price']

        if not current_price:
            return "❌ Cannot trade: No price data available"

        # Get yellow EMA for stop loss
        yellow_ema_stop = 0
        if action in ['long', 'short']:
            yellow_emas = self.data_5min['ema_groups'].get('yellow', [])
            if yellow_emas:
                # Use the highest yellow EMA for long, lowest for short
                yellow_prices = [ema.get('price', 0) for ema in yellow_emas if ema.get('price')]
                if yellow_prices:
                    yellow_ema_stop = max(yellow_prices) if action == 'long' else min(yellow_prices)

        # Temporarily enable auto_trade for execution
        self.auto_trade = True
        success, message = self.execute_trade(action, current_price, yellow_ema_stop)
        self.auto_trade = False

        if success:
            self.trades.append({
                'time': datetime.now(),
                'action': action,
                'price': current_price,
                'confidence': 1.0,  # Manual trade
                'reasoning': 'Manual execution via interactive mode'
            })
            return f"✅ {message}"
        else:
            return f"❌ {message}"

    def interactive_loop(self):
        """Main interactive loop - combines monitoring with chat interface"""
        self.setup_browsers()

        print("\n" + "="*80)
        print(" "*20 + "🎮 INTERACTIVE TRADING MODE")
        print("="*80)
        print("\n🤖 Chat with Claude about market conditions")
        print("💼 Manually execute trades when you're ready")
        print("\nCommands:")
        print("  'chat <question>' - Ask Claude about the market")
        print("  'long'            - Open a LONG position")
        print("  'short'           - Open a SHORT position")
        print("  'close'           - Close current position")
        print("  'status'          - Show current market status")
        print("  'cost'            - Show API cost summary")
        print("  'help'            - Show this help message")
        print("  'exit'            - Stop the bot")
        print("\nThe bot will monitor the market and provide commentary every 10 minutes.")
        print("="*80 + "\n")

        # Start data collection threads
        import threading
        thread_5min = threading.Thread(target=self.update_timeframe_data, args=('5min',), daemon=True)
        thread_15min = threading.Thread(target=self.update_timeframe_data, args=('15min',), daemon=True)

        thread_5min.start()
        thread_15min.start()

        print("✅ Data collection threads started")
        print("⏳ Waiting for initial data (5 seconds)...\n")
        time.sleep(5)

        check_num = 0
        last_dashboard_time = time.time()
        dashboard_interval = 30  # Update dashboard every 30 seconds in background

        try:
            # Show initial status
            self.show_quick_status()

            while self.running:
                # Background: Check for commentary
                current_time = time.time()
                if self.claude and (self.last_commentary_time is None or
                                   current_time - self.last_commentary_time >= self.commentary_interval):
                    try:
                        pos = self.get_position()
                        commentary = self.claude.get_market_commentary(
                            self.data_5min,
                            self.data_15min,
                            pos
                        )
                        self.last_commentary = commentary
                        self.last_commentary_time = current_time
                        print(f"\n{'─'*80}")
                        print(f"💬 CLAUDE'S THOUGHTS:")
                        print(f"   {commentary}")
                        print(f"{'─'*80}\n")
                        print(">>> ", end="", flush=True)
                    except Exception as e:
                        pass

                # Background: Periodic dashboard refresh
                if current_time - last_dashboard_time >= dashboard_interval:
                    last_dashboard_time = current_time
                    check_num += 1

                # Wait for user input (non-blocking with timeout)
                print(">>> ", end="", flush=True)

                # Simple input with timeout handling
                import select
                ready, _, _ = select.select([sys.stdin], [], [], 1.0)

                if ready:
                    user_input = sys.stdin.readline().strip()

                    if not user_input:
                        continue

                    command = user_input.lower()

                    # Handle commands
                    if command == 'exit' or command == 'quit':
                        print("\n👋 Exiting interactive mode...")
                        break

                    elif command == 'help':
                        print("\n" + "="*80)
                        print("COMMANDS:")
                        print("  chat <question> - Ask Claude about the market")
                        print("  long            - Open a LONG position")
                        print("  short           - Open a SHORT position")
                        print("  close           - Close current position")
                        print("  status          - Show current market status")
                        print("  cost            - Show API cost summary")
                        print("  help            - Show this help message")
                        print("  exit            - Stop the bot")
                        print("="*80 + "\n")

                    elif command == 'status':
                        self.show_quick_status()

                    elif command == 'cost':
                        if self.claude:
                            self.claude.print_cost_summary()
                        else:
                            print("❌ Claude not available")

                    elif command == 'long':
                        print(f"\n🤔 Executing LONG trade...")
                        result = self.manual_trade('long')
                        print(result)
                        time.sleep(1)
                        self.show_quick_status()

                    elif command == 'short':
                        print(f"\n🤔 Executing SHORT trade...")
                        result = self.manual_trade('short')
                        print(result)
                        time.sleep(1)
                        self.show_quick_status()

                    elif command == 'close':
                        print(f"\n🤔 Closing position...")
                        result = self.manual_trade('close')
                        print(result)
                        time.sleep(1)
                        self.show_quick_status()

                    elif command.startswith('chat '):
                        question = user_input[5:].strip()
                        if question:
                            print(f"\n🤔 Asking Claude: '{question}'...\n")
                            answer = self.chat_with_claude(question)
                            print(f"{'─'*80}")
                            print(f"🧠 CLAUDE'S RESPONSE:")
                            print(f"{'─'*80}")
                            print(answer)
                            print(f"{'─'*80}\n")
                        else:
                            print("❌ Please provide a question after 'chat'")

                    else:
                        print(f"❌ Unknown command: '{user_input}'")
                        print("   Type 'help' for available commands\n")

        except KeyboardInterrupt:
            print("\n\n👋 Interactive mode stopped by user")

        finally:
            self.running = False
            if self.claude:
                self.claude.print_cost_summary()
            if self.driver_5min:
                self.driver_5min.quit()
            if self.driver_15min:
                self.driver_15min.quit()

    def show_quick_status(self):
        """Show a quick status update without clearing screen"""
        print(f"\n{'='*80}")
        print(f"📊 MARKET STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}")

        # Position
        pos = self.get_position()
        if pos:
            pnl_emoji = "🟢" if pos['unrealized_pnl'] > 0 else "🔴"
            print(f"\n💼 POSITION: {pos['side'].upper()} {pos['size']:.4f} @ ${pos['entry_price']:.2f}")
            print(f"   {pnl_emoji} PnL: ${pos['unrealized_pnl']:+.2f}")
        else:
            print(f"\n💼 POSITION: None")

        # Timeframes
        state_5min = self.data_5min['state']
        price_5min = self.data_5min['price']
        emoji_5min = "🟢" if state_5min == 'all_green' else "🔴" if state_5min == 'all_red' else "⚪"

        state_15min = self.data_15min['state']
        price_15min = self.data_15min['price']
        emoji_15min = "🟢" if state_15min == 'all_green' else "🔴" if state_15min == 'all_red' else "⚪"

        print(f"\n🔷 5min:  {emoji_5min} {state_5min.upper():12} @ ${price_5min:.2f}" if price_5min else f"\n🔷 5min:  {emoji_5min} {state_5min.upper():12} @ N/A")
        print(f"🔶 15min: {emoji_15min} {state_15min.upper():12} @ ${price_15min:.2f}" if price_15min else f"🔶 15min: {emoji_15min} {state_15min.upper():12} @ N/A")

        # Last commentary
        if self.last_commentary:
            print(f"\n💬 Last Claude comment: {self.last_commentary[:100]}...")

        # Cost
        if self.claude:
            cost = self.claude.get_cost_summary()
            print(f"\n💰 Session cost: ${cost['session_cost_usd']:.4f} ({cost['total_calls']} calls)")

        print(f"{'='*80}\n")


def main():
    print("\n╔" + "="*78 + "╗")
    print("║" + " "*18 + "INTERACTIVE TRADING MODE" + " "*36 + "║")
    print("╚" + "="*78 + "╝")

    # Load settings from .env
    private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')
    if not private_key:
        print("\n❌ ERROR: HYPERLIQUID_PRIVATE_KEY not found in .env file")
        return

    use_testnet = os.getenv('USE_TESTNET', 'true').lower() == 'true'
    position_size_pct = float(os.getenv('POSITION_SIZE_PCT', '10')) / 100
    leverage = int(os.getenv('LEVERAGE', '25'))
    min_confidence = float(os.getenv('MIN_CONFIDENCE', '0.75'))

    # Display config
    print("\n📊 CONFIGURATION:")
    print("─"*80)
    print(f"  Network: {'TESTNET 🧪' if use_testnet else '⚠️  MAINNET 💰'}")
    print(f"  Trading Mode: 🎮 MANUAL (Interactive)")
    print(f"  Position Size: {position_size_pct*100:.1f}%")
    print(f"  Leverage: {leverage}x")
    print(f"  AI: Claude Sonnet 4.5")
    print("─"*80)

    # Check API key
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_key:
        print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set!")
        return

    print("\n✅ Starting interactive mode in 3 seconds...")
    time.sleep(3)

    # Create and run interactive bot
    bot = InteractiveTrader(
        private_key=private_key,
        use_testnet=use_testnet,
        auto_trade=False,  # Always manual in interactive mode
        position_size_pct=position_size_pct,
        leverage=leverage,
        min_confidence=min_confidence
    )

    bot.interactive_loop()


if __name__ == "__main__":
    main()
