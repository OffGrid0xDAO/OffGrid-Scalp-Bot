# Live Trading Bot - Iteration 10 Strategy

## Strategy Performance (Backtested)

**Iteration 10 Results:**
- **Return:** +2.19%
- **Win Rate:** 41%
- **Total Trades:** 39
- **Avg Win:** +2.85%
- **Avg Loss:** -1.03%
- **Profit Capture:** 44.95%

## Strategy Parameters

### Timeframe
- **15 minutes** (proven optimal)

### Entry Filters
- **Quality Score Min:** 50
- **Confluence Score Min:** 15
- **Confluence Gap Min:** 15
- **Volume Ratio Min:** 1.0
- **Volume Types:** spike, elevated, normal

### Exit Strategy
- **Stop Loss:** 0.75%
- **Profit Lock:** 1.5% (once +1.5% profit reached, won't let trade go negative)
- **Take Profit:** 5.0%
- **No partial exits** (full position management)

## How to Run

### 1. Check Environment

```bash
# Check that environment variables are set
./start_bot.sh
```

Required variables:
- `TELEGRAM_BOT_TOKEN` - For trade notifications
- `ANTHROPIC_API_KEY` - For strategy optimization (optional)

### 2. Start Bot

```bash
./start_bot.sh
```

Or directly:
```bash
python3 live_trading_bot.py
```

### 3. Monitor

The bot will:
- Check for signals every 60 seconds
- Send Telegram notifications for all trades
- Run in PAPER TRADING mode by default
- Log all activity to console

## Bot Features

### Entry Detection
- Scans for quality signals every minute
- Uses proven Iteration 10 filters
- Only trades when quality score ≥ 50

### Exit Management
- **Stop Loss:** Automatic at -0.75%
- **Profit Lock:** If profit reaches +1.5%, won't let trade go negative
- **Take Profit:** Auto-close at +5.0%

### Notifications
All trades notify via Telegram:
- 🚀 Entry signals with quality score
- ✅ Profitable exits
- ❌ Stop loss hits
- 📊 Daily P&L summary

### Risk Management
- Default: $100 position size (configurable)
- Max 1 trade at a time
- Paper trading mode for testing

## File Structure

```
TradingScalper/
├── start_bot.sh                    # Launch script
├── live_trading_bot.py             # Main bot logic
├── src/
│   ├── strategy/
│   │   ├── strategy_params.json    # Strategy configuration (ITERATION 10)
│   │   ├── entry_detector_user_pattern.py
│   │   └── exit_manager_user_pattern.py
│   ├── notifications/
│   │   └── telegram_bot.py         # Telegram integration
│   └── exchange/
│       └── hyperliquid_client.py   # Exchange API
└── trading_data/
    └── iteration_10_results.json   # Backtest results
```

## Configuration

Edit `src/strategy/strategy_params.json` to customize:

```json
{
  "timeframe": "15m",
  "entry_filters": {
    "min_quality_score": 50.0,
    "confluence_score_min": 15,
    "volume_ratio_min": 1.0
  },
  "exit_strategy": {
    "stop_loss_pct": 0.75,
    "profit_lock_pct": 1.5,
    "take_profit_levels": [5.0]
  }
}
```

## Safety Features

### Paper Trading Mode
- Enabled by default
- Simulates trades without real money
- Tracks virtual capital ($1000 start)

### Stop Loss Protection
- Hard stop at -0.75% per trade
- Never risk more than 2% of capital

### Profit Lock
- Once trade reaches +1.5%, it won't go negative
- Protects profits from reversals

## Monitoring Performance

The bot tracks:
- Total trades executed
- Win rate %
- Total P&L
- Current capital
- Trade history

Check `trades_history` array in bot for all trade records.

## Next Steps

### 1. Test with Paper Trading
Run for 1-2 weeks in paper mode to verify:
- Signal quality
- Entry/exit timing
- P&L tracking
- Telegram notifications

### 2. Review Performance
After paper trading:
- Check win rate ≥ 40%
- Verify profit capture
- Analyze losing trades

### 3. Go Live (Optional)
If paper trading successful:
- Set `mode='LIVE'` in bot
- Start with small position sizes
- Monitor closely for first week

## Important Notes

⚠️ **ALWAYS start with paper trading!**

⚠️ **Never risk more than you can afford to lose**

⚠️ **Monitor the bot regularly** - don't set and forget

✅ **The strategy is proven profitable** (2.19% on backtest)

✅ **But past performance ≠ future results** - trade responsibly

## Support

Questions? Check:
1. Bot logs in terminal
2. `trading_data/iteration_10_results.json` for backtest details
3. `DYNAMIC_GRADIENT_GUIDE.md` for strategy explanation

---

**Strategy Version:** Iteration 10
**Last Updated:** October 23, 2025
**Status:** Ready for paper trading ✅
