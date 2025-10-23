#!/bin/bash

# Move old Python files (keep fetch_hyperliquid_history.py and plot_ema_chart.py)
mv actual_trade_learner.py old_implementation/
mv add_user_trade.py old_implementation/
mv auto_backfill_ema.py old_implementation/
mv backfill_ema_data.py old_implementation/
mv big_movement_ema_analyzer.py old_implementation/
mv claude_optimal_trade_finder.py old_implementation/
mv claude_trader.py old_implementation/
mv compare_trading_systems.py old_implementation/
mv continuous_learning.py old_implementation/
mv convert_html_to_image.py old_implementation/
mv create_optimization_chart.py old_implementation/
mv create_user_optimal_trades.py old_implementation/
mv dual_timeframe_bot.py old_implementation/
mv dual_timeframe_bot_with_optimizer.py old_implementation/
mv ema_derivative_analyzer.py old_implementation/
mv enrich_user_trades.py old_implementation/
mv generate_full_historical_analysis.py old_implementation/
mv initialize_trading_rules.py old_implementation/
mv main.py old_implementation/
mv manual_optimal_trades.py old_implementation/
mv manual_optimal_trades_input.py old_implementation/
mv manual_trade_tracker.py old_implementation/
mv merge_backfill.py old_implementation/
mv optimal_trade_finder_30min.py old_implementation/
mv optimal_vs_actual_analyzer.py old_implementation/
mv regenerate_backtest.py old_implementation/
mv regenerate_optimal_trades.py old_implementation/
mv rule_based_trader.py old_implementation/
mv rule_based_trader_OLD_BACKUP.py old_implementation/ 2>/dev/null
mv simple_backfill.py old_implementation/
mv telegram_notifier.py old_implementation/
mv test_bot_live.py old_implementation/
mv test_derivative_integration.py old_implementation/
mv visualize_trading_analysis.py old_implementation/

# Move old MD files (keep the new planning docs)
mv ALL_DATA_NOW_USED.md old_implementation/
mv AUTO_BACKFILL_GUIDE.md old_implementation/
mv AUTO_LOGIN_FIXES.md old_implementation/
mv BACKFILL_GUIDE.md old_implementation/
mv INTEGRATION_COMPLETE.md old_implementation/
mv NEW_SYSTEM_SUMMARY.md old_implementation/
mv NEW_SYSTEM_TUNING.md old_implementation/
mv OPTIMIZATION_GUIDE.md old_implementation/
mv OPTIMIZER_WORKING_NEXT_STEPS.md old_implementation/
mv SESSION_COMPLETE_SUMMARY.md old_implementation/
mv SETUP_COMPLETE.md old_implementation/
mv SYSTEM_FULLY_INTEGRATED.md old_implementation/
mv TELEGRAM_MESSAGE_FIX.md old_implementation/
mv USER_OPTIMAL_TRADES_GUIDE.md old_implementation/

# Move backup folders
mv backup_before_deep_cleanup_20251020_154101 old_implementation/

# Move shell scripts
mv start_bot.sh old_implementation/ 2>/dev/null

echo "✅ Moved old implementation files to old_implementation/"
