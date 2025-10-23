"""
Telegram Notification System for Trading Bot
Sends beautiful formatted messages for trade entries, exits, and updates
"""

import requests
from datetime import datetime
from typing import Optional, Dict
import os
from dotenv import load_dotenv

load_dotenv()


class TelegramNotifier:
    """
    Send rich formatted trade notifications to Telegram
    """

    def __init__(self):
        """Initialize Telegram notifier"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            print("⚠️  Telegram notifications disabled - set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        else:
            print(f"✅ Telegram notifications enabled - Chat ID: {self.chat_id[:8]}...")

    def send_message(self, text: str, parse_mode: str = 'HTML') -> bool:
        """
        Send a message to Telegram

        Args:
            text: Message text (supports HTML or Markdown)
            parse_mode: 'HTML' or 'Markdown'

        Returns:
            bool: Success status
        """
        if not self.enabled:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }

            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            print(f"⚠️  Telegram send error: {e}")
            return False

    def format_entry_notification(self, direction: str, price: float, size: float,
                                   confidence: float, reasoning: str,
                                   entry_price: float, stop_loss: float,
                                   take_profit: float, yellow_ema_stop: float,
                                   timeframe_5min: str, timeframe_15min: str,
                                   light_green: int = 0, dark_green: int = 0,
                                   light_red: int = 0, dark_red: int = 0) -> str:
        """
        Create beautiful HTML formatted entry notification

        Args:
            direction: LONG or SHORT
            price: Entry price
            size: Position size
            confidence: Confidence score (0-1)
            reasoning: Claude's reasoning
            entry_price: Target entry price
            stop_loss: Stop loss level
            take_profit: Take profit level
            yellow_ema_stop: Yellow EMA stop level
            timeframe_5min: 5min ribbon state
            timeframe_15min: 15min ribbon state
            light_green/dark_green: Green EMA intensity counts
            light_red/dark_red: Red EMA intensity counts

        Returns:
            Formatted HTML message
        """
        # Emojis based on direction
        direction_emoji = "🚀" if direction == "LONG" else "🔻"
        state_emoji = "📈" if direction == "LONG" else "📉"

        # Calculate risk/reward
        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        rr_ratio = reward / risk if risk > 0 else 0

        # Format reasoning (truncate if too long for Telegram)
        short_reasoning = reasoning[:300] + "..." if len(reasoning) > 300 else reasoning

        # Momentum indicator
        if direction == "LONG":
            momentum = f"💚 {light_green} light | {dark_green} dark"
        else:
            momentum = f"❤️ {light_red} light | {dark_red} dark"

        message = f"""
{direction_emoji} <b>TRADE ENTRY: {direction}</b> {direction_emoji}

{state_emoji} <b>Position Details</b>
├ Entry Price: <code>${price:.2f}</code>
├ Position Size: <code>{size:.4f} ETH</code>
└ Confidence: <code>{confidence:.0%}</code>

📊 <b>Targets</b>
├ 🛡 Stop Loss: <code>${stop_loss:.2f}</code> ({abs((stop_loss-price)/price*100):.2f}%)
├ 🎯 Take Profit: <code>${take_profit:.2f}</code> ({abs((take_profit-price)/price*100):.2f}%)
├ 🟡 Yellow EMA: <code>${yellow_ema_stop:.2f}</code>
└ 📈 Risk/Reward: <code>1:{rr_ratio:.2f}</code>

🌈 <b>Ribbon Analysis</b>
├ 5min: <code>{timeframe_5min.upper()}</code>
├ 15min: <code>{timeframe_15min.upper()}</code>
└ Momentum: {momentum}

🧠 <b>EMA's Analysis</b>
<i>{short_reasoning}</i>

⏰ <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>
"""
        return message.strip()

    def format_exit_notification(self, direction: str, entry_price: float,
                                  exit_price: float, size: float, pnl: float,
                                  pnl_pct: float, hold_duration: float,
                                  exit_reason: str, reasoning: str) -> str:
        """
        Create beautiful HTML formatted exit notification

        Args:
            direction: LONG or SHORT
            entry_price: Original entry price
            exit_price: Exit price
            size: Position size
            pnl: Profit/Loss in USD
            pnl_pct: Profit/Loss percentage
            hold_duration: How long position was held (seconds)
            exit_reason: Why we exited
            reasoning: Exit reasoning

        Returns:
            Formatted HTML message
        """
        # Emojis based on PnL
        if pnl > 0:
            result_emoji = "✅ 💰"
            pnl_emoji = "🟢"
        else:
            result_emoji = "❌ 📉"
            pnl_emoji = "🔴"

        # Convert duration to readable format
        minutes = hold_duration / 60
        if minutes < 60:
            duration_str = f"{minutes:.1f} minutes"
        else:
            hours = minutes / 60
            duration_str = f"{hours:.1f} hours"

        # Format reasoning
        short_reasoning = reasoning[:300] + "..." if len(reasoning) > 300 else reasoning

        message = f"""
{result_emoji} <b>TRADE CLOSED: {direction}</b> {result_emoji}

{pnl_emoji} <b>Performance</b>
├ Entry: <code>${entry_price:.2f}</code>
├ Exit: <code>${exit_price:.2f}</code>
├ Size: <code>{size:.4f} ETH</code>
├ PnL: <code>${pnl:+.2f}</code> ({pnl_pct:+.2f}%)
└ Duration: <code>{duration_str}</code>

🚪 <b>Exit Reason</b>
<code>{exit_reason}</code>

🧠 <b>EMA's Analysis</b>
<i>{short_reasoning}</i>

⏰ <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>
"""
        return message.strip()

    def format_update_notification(self, title: str, message: str) -> str:
        """
        Create formatted update notification

        Args:
            title: Update title
            message: Update message

        Returns:
            Formatted HTML message
        """
        formatted = f"""
ℹ️ <b>{title}</b>

{message}

⏰ <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>
"""
        return formatted.strip()

    def send_entry(self, **kwargs) -> bool:
        """
        Send trade entry notification

        Args:
            **kwargs: All arguments for format_entry_notification

        Returns:
            bool: Success status
        """
        message = self.format_entry_notification(**kwargs)
        return self.send_message(message)

    def send_exit(self, **kwargs) -> bool:
        """
        Send trade exit notification

        Args:
            **kwargs: All arguments for format_exit_notification

        Returns:
            bool: Success status
        """
        message = self.format_exit_notification(**kwargs)
        return self.send_message(message)

    def send_update(self, title: str, message: str) -> bool:
        """
        Send update notification

        Args:
            title: Update title
            message: Update message

        Returns:
            bool: Success status
        """
        formatted = self.format_update_notification(title, message)
        return self.send_message(formatted)

    def send_error(self, error_message: str) -> bool:
        """
        Send error notification

        Args:
            error_message: Error description

        Returns:
            bool: Success status
        """
        message = f"""
🚨 <b>ERROR</b>

<code>{error_message}</code>

⏰ <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>
"""
        return self.send_message(message.strip())

    def format_market_analysis(self, current_price: float,
                                timeframe_5min: str, timeframe_15min: str,
                                tf_5min_light_green: int, tf_5min_dark_green: int,
                                tf_5min_light_red: int, tf_5min_dark_red: int,
                                tf_15min_light_green: int, tf_15min_dark_green: int,
                                tf_15min_light_red: int, tf_15min_dark_red: int,
                                yellow_ema_5min: float, yellow_ema_15min: float,
                                claude_analysis: str, trade_setup: str,
                                setup_confidence: float = 0.0) -> str:
        """
        Create beautiful market analysis notification

        Args:
            current_price: Current ETH price
            timeframe_5min: 5min ribbon state
            timeframe_15min: 15min ribbon state
            tf_5min_light_green/dark_green/light_red/dark_red: 5min EMA intensity counts
            tf_15min_light_green/dark_green/light_red/dark_red: 15min EMA intensity counts
            yellow_ema_5min: Yellow EMA on 5min chart
            yellow_ema_15min: Yellow EMA on 15min chart
            claude_analysis: Detailed market analysis
            trade_setup: "LONG_BUILDING", "SHORT_BUILDING", "LONG_READY", "SHORT_READY", "NO_SETUP", "NEUTRAL"
            setup_confidence: Confidence in potential setup (0-1)

        Returns:
            Formatted HTML message
        """
        # Determine overall market sentiment
        if "ALL_GREEN" in timeframe_5min.upper() and "ALL_GREEN" in timeframe_15min.upper():
            sentiment = "🟢 <b>STRONG BULLISH</b>"
            sentiment_emoji = "🚀"
        elif "ALL_RED" in timeframe_5min.upper() and "ALL_RED" in timeframe_15min.upper():
            sentiment = "🔴 <b>STRONG BEARISH</b>"
            sentiment_emoji = "📉"
        elif "GREEN" in timeframe_5min.upper() or "GREEN" in timeframe_15min.upper():
            sentiment = "🟡 <b>BULLISH BIAS</b>"
            sentiment_emoji = "📈"
        elif "RED" in timeframe_5min.upper() or "RED" in timeframe_15min.upper():
            sentiment = "🟡 <b>BEARISH BIAS</b>"
            sentiment_emoji = "📉"
        else:
            sentiment = "⚪ <b>NEUTRAL</b>"
            sentiment_emoji = "〰️"

        # Setup status
        if trade_setup == "LONG_READY":
            setup_status = f"🎯 <b>LONG SETUP READY</b> ({setup_confidence:.0%})"
            setup_emoji = "✅"
        elif trade_setup == "SHORT_READY":
            setup_status = f"🎯 <b>SHORT SETUP READY</b> ({setup_confidence:.0%})"
            setup_emoji = "✅"
        elif trade_setup == "LONG_BUILDING":
            setup_status = f"⏳ <b>LONG BUILDING</b> ({setup_confidence:.0%})"
            setup_emoji = "🔨"
        elif trade_setup == "SHORT_BUILDING":
            setup_status = f"⏳ <b>SHORT BUILDING</b> ({setup_confidence:.0%})"
            setup_emoji = "🔨"
        elif trade_setup == "NO_SETUP":
            setup_status = "⛔ <b>NO SETUP</b>"
            setup_emoji = "⏸️"
        else:
            setup_status = "〰️ <b>NEUTRAL</b>"
            setup_emoji = "⏸️"

        # Format 5min momentum
        if tf_5min_light_green > 0 or tf_5min_dark_green > 0:
            momentum_5min = f"💚 {tf_5min_light_green} light | {tf_5min_dark_green} dark"
        elif tf_5min_light_red > 0 or tf_5min_dark_red > 0:
            momentum_5min = f"❤️ {tf_5min_light_red} light | {tf_5min_dark_red} dark"
        else:
            momentum_5min = "⚪ No clear momentum"

        # Format 15min momentum
        if tf_15min_light_green > 0 or tf_15min_dark_green > 0:
            momentum_15min = f"💚 {tf_15min_light_green} light | {tf_15min_dark_green} dark"
        elif tf_15min_light_red > 0 or tf_15min_dark_red > 0:
            momentum_15min = f"❤️ {tf_15min_light_red} light | {tf_15min_dark_red} dark"
        else:
            momentum_15min = "⚪ No clear momentum"

        # Format Claude's analysis (truncate if too long)
        short_analysis = claude_analysis[:400] + "..." if len(claude_analysis) > 400 else claude_analysis

        message = f"""
{sentiment_emoji} <b>MARKET ANALYSIS</b> {sentiment_emoji}

💰 <b>Current Price</b>
<code>${current_price:.2f}</code>

📊 <b>Market Sentiment</b>
{sentiment}

{setup_emoji} <b>Trade Setup Status</b>
{setup_status}

🌈 <b>5-Minute Timeframe</b>
├ State: <code>{timeframe_5min.upper()}</code>
├ Yellow EMA: <code>${yellow_ema_5min:.2f}</code>
└ Momentum: {momentum_5min}

🌈 <b>15-Minute Timeframe</b>
├ State: <code>{timeframe_15min.upper()}</code>
├ Yellow EMA: <code>${yellow_ema_15min:.2f}</code>
└ Momentum: {momentum_15min}

🧠 <b>Thoughts</b>
<i>{short_analysis}</i>

⏰ <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>
"""
        return message.strip()

    def send_market_analysis(self, **kwargs) -> bool:
        """
        Send market analysis notification

        Args:
            **kwargs: All arguments for format_market_analysis

        Returns:
            bool: Success status
        """
        message = self.format_market_analysis(**kwargs)
        return self.send_message(message)


# Test function
if __name__ == "__main__":
    notifier = TelegramNotifier()

    if notifier.enabled:
        print("\n📱 Testing Telegram notifications...")

        # Test entry notification
        print("\n1️⃣ Sending test ENTRY notification...")
        notifier.send_entry(
            direction="LONG",
            price=3850.25,
            size=1.0420,
            confidence=0.85,
            reasoning="5min: ALL_GREEN (11/12 EMAs, 6 light) - Strong bullish momentum confirmed. 15min: ALL_GREEN (12/12 EMAs, 8 light) - Perfect alignment. Fresh transition detected 45 minutes ago. Yellow EMA holding as support at $3843. High confidence entry.",
            entry_price=3850.25,
            stop_loss=3842.50,
            take_profit=3890.00,
            yellow_ema_stop=3843.75,
            timeframe_5min="all_green",
            timeframe_15min="all_green",
            light_green=6,
            dark_green=3,
            light_red=0,
            dark_red=0
        )

        print("\n2️⃣ Sending test EXIT notification...")
        notifier.send_exit(
            direction="LONG",
            entry_price=3850.25,
            exit_price=3875.50,
            size=1.0420,
            pnl=26.31,
            pnl_pct=2.15,
            hold_duration=450,
            exit_reason="Take Profit Hit",
            reasoning="Target reached at $3875. Ribbon still strong but taking profit as planned. Excellent trade execution."
        )

        print("\n3️⃣ Sending test UPDATE notification...")
        notifier.send_update(
            title="Trailing Stop Updated",
            message="Stop loss moved to breakeven at $3850.25\nYellow EMA now at $3848.50"
        )

        print("\n4️⃣ Sending test MARKET ANALYSIS notification...")
        notifier.send_market_analysis(
            current_price=3862.50,
            timeframe_5min="mixed_green",
            timeframe_15min="all_green",
            tf_5min_light_green=4,
            tf_5min_dark_green=3,
            tf_5min_light_red=0,
            tf_5min_dark_red=0,
            tf_15min_light_green=8,
            tf_15min_dark_green=3,
            tf_15min_light_red=0,
            tf_15min_dark_red=0,
            yellow_ema_5min=3858.75,
            yellow_ema_15min=3855.20,
            claude_analysis="5min: MIXED_GREEN (7/12 EMAs, 4 light green) - Bullish structure building but not fully committed yet. Price holding above yellow EMA which is critical. 15min: ALL_GREEN (11/12 EMAs, 8 light green) - Strong bullish alignment on higher timeframe provides solid foundation. Watching for 5min to complete transition to ALL_GREEN for high-probability long entry. If we get 2 more EMAs turning light green on 5min, we'll have excellent confluence.",
            trade_setup="LONG_BUILDING",
            setup_confidence=0.72
        )

        print("\n✅ Test notifications sent!")
    else:
        print("\n❌ Telegram not configured. Add to .env:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token")
        print("TELEGRAM_CHAT_ID=your_chat_id")
