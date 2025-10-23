"""
Test the optimization Telegram notification with sample data
"""

from telegram_notifier import TelegramNotifier

# Create sample data matching the expected structure
optimal_data = {
    'total_trades': 37,
    'total_pnl_pct': 29.89,
    'avg_pnl_pct': 0.81,
    'patterns': {
        'avg_compression': 0.15,
        'avg_light_emas': 18,
        'total_analyzed': 37
    }
}

backtest_data = {
    'total_trades': 35,
    'total_pnl_pct': -0.14,
    'avg_pnl_pct': -0.004,
    'patterns': {
        'avg_compression': 0.10,
        'avg_light_emas': 15,
        'total_analyzed': 35
    }
}

actual_data = {
    'total_trades': 0,
    'total_pnl_pct': 0,
    'avg_pnl_pct': 0
}

recommendations = {
    'key_findings': [
        "Backtest catching 95% of trades (35/37) but exiting too early",
        "Average backtest hold: 3.5min vs optimal 33min",
        "Gap is exit strategy, not entry detection",
        "Backtest trades at slightly lower compression (0.10 vs 0.15)",
        "Exit strategy is the problem: ribbon flips back too quickly"
    ],
    'rule_adjustments': {
        'min_compression_for_entry': 0.12,
        'min_hold_time_minutes': 5,
        'exit_on_ribbon_flip': False,
        'exit_on_target_only': True,
        'profit_target_pct': 0.005,
        'min_light_emas': 15,
        'enable_yellow_ema_trail': True,
        'trail_buffer_pct': 0.001
    }
}

# Initialize and send
print("🧪 Testing Telegram optimization notification...\n")
notifier = TelegramNotifier()

if notifier.enabled:
    print("📱 Sending test optimization update...")
    success = notifier.send_optimization_update(
        optimal_data=optimal_data,
        backtest_data=backtest_data,
        actual_data=actual_data,
        recommendations=recommendations,
        api_cost=0.0234
    )

    if success:
        print("✅ Test notification sent successfully!")
        print("\nCheck your Telegram to see the formatted message with:")
        print("  - 3-way comparison (optimal, backtest, actual)")
        print("  - Gap analysis (missed trades, PnL gap, capture rate)")
        print("  - Key findings (5 findings)")
        print("  - Rule improvements (8 changes)")
        print("  - API cost and next cycle info")
    else:
        print("❌ Failed to send notification")
else:
    print("❌ Telegram not configured. Add to .env:")
    print("   TELEGRAM_BOT_TOKEN=your_bot_token")
    print("   TELEGRAM_CHAT_ID=your_chat_id")
