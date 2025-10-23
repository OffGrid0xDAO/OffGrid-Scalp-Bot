# Live Trading Bot Architecture

## Overview

The live trading bot executes trades automatically based on the professional day trading strategy using EMA ribbons, Stochastic, Bollinger Bands, VWAP, and other indicators.

## Design Philosophy

- **Fully Automated** - No Claude in the live trading loop (too slow/expensive)
- **Quality Over Quantity** - Target 2-3 high-quality trades per day
- **Fast Execution** - Sub-second decision making
- **Robust Risk Management** - Automatic stop-loss and take-profit
- **Continuous Operation** - Runs 24/7 with automatic data updates

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LIVE TRADING BOT                         │
│                      (main.py)                              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Data Update Loop (every 1 minute)                │  │
│  │     - Fetch latest candles from Hyperliquid          │  │
│  │     - Update local CSV files                         │  │
│  │     - Recalculate indicators                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  2. Signal Detection                                 │  │
│  │     - Read latest indicators                         │  │
│  │     - Run entry_detector.py                          │  │
│  │     - Filter by quality score (>70)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  3. Trade Execution (if signal found)                │  │
│  │     - Check position limits                          │  │
│  │     - Calculate position size                        │  │
│  │     - Execute market order via Hyperliquid           │  │
│  │     - Place TP/SL orders                             │  │
│  │     - Record trade in database                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  4. Position Management                              │  │
│  │     - Monitor open positions                         │  │
│  │     - Run exit_manager.py                            │  │
│  │     - Update trailing stops                          │  │
│  │     - Close positions when exit signal               │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  5. Logging & Reporting                              │  │
│  │     - Log all trades to CSV                          │  │
│  │     - Send Telegram notifications                    │  │
│  │     - Update performance metrics                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Loop back to step 1 (sleep 60 seconds)                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              OPTIMIZATION LOOP (SEPARATE PROCESS)            │
│                  (runs daily via cron)                       │
│                                                              │
│  1. Find optimal trades (perfect hindsight)                 │
│  2. Run backtest with current rules                         │
│  3. Compare optimal vs backtest (gap analysis)              │
│  4. Send Telegram report                                    │
│  5. Sleep until next day                                    │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. **src/main.py** - Main Trading Loop
- Entry point for live bot
- Orchestrates all components
- Runs infinite loop with 1-minute cycles
- Handles errors and reconnections

### 2. **src/exchange/hyperliquid_client.py** - Exchange Interface
- Wraps Hyperliquid API
- Market orders (open/close positions)
- Limit orders (TP/SL)
- Position queries
- Account info

### 3. **src/strategy/entry_detector.py** - Entry Signal Detection
- Already implemented ✅
- Reads indicators from CSV
- Applies filters (Stochastic, Bollinger, VWAP, etc.)
- Calculates quality score
- Returns trade signals with confidence

### 4. **src/strategy/exit_manager.py** - Exit Signal Detection
- Already implemented ✅
- Monitors open positions
- Checks exit conditions (TP, SL, indicator reversals)
- Returns exit signals

### 5. **src/position/position_manager.py** - Position Tracking
- Tracks active positions
- Manages TP/SL orders
- Updates trailing stops
- Syncs with exchange

### 6. **src/utils/trade_logger.py** - Trade Recording
- Logs all trades to CSV
- Tracks P&L
- Generates performance reports

### 7. **src/reporting/telegram_notifier.py** - Notifications
- Trade alerts (entry/exit)
- Daily summaries
- Error notifications

## Detailed Flow

### Startup Sequence

```python
1. Load configuration (strategy_params.json)
2. Initialize Hyperliquid connection
3. Load existing positions from exchange
4. Sync local state with exchange
5. Start main loop
```

### Main Loop (Every 60 seconds)

```python
while True:
    # 1. Update data
    fetch_latest_candles()           # From Hyperliquid
    append_to_csv()                  # Update local files
    recalculate_indicators()         # Run indicator pipeline

    # 2. Check for exits (priority over entries)
    for position in open_positions:
        latest_candle = get_latest_candle(position.timeframe)
        exit_signal = exit_manager.check_exit(position, latest_candle)

        if exit_signal:
            close_position(position)
            log_trade(position, 'exit')
            send_telegram_alert('EXIT', position)

    # 3. Check for entries (only if no position)
    if not has_open_position():
        latest_candle = get_latest_candle('5m')  # Primary timeframe
        entry_signal = entry_detector.check_signals(latest_candle)

        if entry_signal and entry_signal.quality_score >= 70:
            # Double-check we can trade
            if cooldown_expired() and within_trading_hours():
                position = open_position(entry_signal)
                log_trade(position, 'entry')
                send_telegram_alert('ENTRY', position)

    # 4. Update metrics
    update_performance_metrics()

    # 5. Sleep
    time.sleep(60)
```

### Trade Execution Flow

```python
def open_position(signal):
    # 1. Calculate position size
    account_value = exchange.get_account_value()
    position_size_usd = account_value * position_size_pct * leverage
    size_in_eth = position_size_usd / signal.price

    # 2. Place market order
    if signal.direction == 'long':
        result = exchange.market_open(symbol, is_buy=True, size=size_in_eth)
    else:
        result = exchange.market_open(symbol, is_buy=False, size=size_in_eth)

    # 3. Get actual fill price
    position = exchange.get_position(symbol)
    entry_price = position.entry_price

    # 4. Place TP/SL orders
    if signal.direction == 'long':
        tp_price = entry_price * (1 + take_profit_pct)
        sl_price = min(entry_price * (1 - stop_loss_pct), signal.sl_price)
    else:
        tp_price = entry_price * (1 - take_profit_pct)
        sl_price = max(entry_price * (1 + stop_loss_pct), signal.sl_price)

    exchange.place_limit_order(symbol, not is_buy, size, tp_price, 'TP')
    exchange.place_limit_order(symbol, not is_buy, size, sl_price, 'SL')

    # 5. Track position
    position_manager.add_position(position, tp_price, sl_price)

    return position
```

## Configuration

### Environment Variables (.env)

```bash
# Hyperliquid
HYPERLIQUID_PRIVATE_KEY=0x...
HYPERLIQUID_USE_TESTNET=true

# Trading Parameters
SYMBOL=ETH
LEVERAGE=25
POSITION_SIZE_PCT=0.10          # 10% of account per trade
MIN_QUALITY_SCORE=70            # Minimum quality score for entry

# Risk Management
TAKE_PROFIT_PCT=0.02            # 2% TP
STOP_LOSS_PCT=0.01              # 1% SL
MAX_DAILY_TRADES=3              # Max trades per day
TRADE_COOLDOWN_MINUTES=60       # 1 hour between trades

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/trading_bot.log
```

### Strategy Configuration (strategy_params.json)

Already exists - used by entry_detector and exit_manager.

## Risk Management

### Position Sizing
- Fixed % of account value (default: 10%)
- Leveraged (default: 25x)
- Example: $1000 account → $100 position → $2500 leveraged position → ~0.625 ETH @ $4000

### Stop Loss
- Initial SL: 1% of entry price (default)
- Indicator-based SL: Yellow EMA or Bollinger Band
- Trailing SL: Update when price moves favorably

### Take Profit
- Initial TP: 2% of entry price (default)
- Can be updated based on exit_manager signals

### Trade Limits
- Max 3 trades per day (configurable)
- 60-minute cooldown between trades (configurable)
- No trading outside configured hours (optional)

## Error Handling

### Network Errors
- Retry with exponential backoff
- Log error and continue
- Send Telegram alert if persistent

### API Errors
- Log error details
- Skip current cycle
- Send Telegram alert

### Position Sync Errors
- Re-fetch from exchange
- Compare with local state
- Reconcile differences
- Log discrepancies

### Indicator Calculation Errors
- Log error
- Use cached indicators from previous cycle
- Send Telegram alert

## Logging

### Trade Log (CSV)
```csv
timestamp,direction,entry_price,exit_price,size,pnl,pnl_pct,quality_score,hold_time,exit_reason
2025-10-22 10:30:00,long,4000.5,4080.2,0.625,49.81,1.99,85,45min,take_profit
```

### Application Log (File)
```
2025-10-22 10:29:58 [INFO] Starting trading cycle 1234
2025-10-22 10:30:00 [INFO] Fetched 1 new candle for 5m
2025-10-22 10:30:01 [INFO] Indicators recalculated
2025-10-22 10:30:02 [INFO] Entry signal detected: LONG quality=85
2025-10-22 10:30:03 [INFO] Opened LONG 0.625 ETH @ $4000.50
2025-10-22 10:30:04 [INFO] TP order placed @ $4080.51
2025-10-22 10:30:04 [INFO] SL order placed @ $3960.50
```

## Telegram Notifications

### Trade Alerts
```
🟢 LONG ENTRY
Symbol: ETH
Entry: $4000.50
Size: 0.625 ETH ($2500)
Quality Score: 85/100
TP: $4080.51 (+2.0%)
SL: $3960.50 (-1.0%)
```

### Daily Summary
```
📊 DAILY TRADING SUMMARY

Trades: 2
Wins: 1 (50%)
Losses: 1 (50%)
Total P&L: +$45.20 (+1.8%)

Best Trade: +$78.50 (+3.1%)
Worst Trade: -$33.30 (-1.3%)

Quality Score Avg: 82/100
```

## Monitoring & Maintenance

### Health Checks
- API connection status
- Data freshness (last candle < 2 minutes old)
- Position sync (local == exchange)
- Order sync (TP/SL active)

### Daily Tasks
- Review trade log
- Check Telegram alerts
- Verify data integrity
- Monitor P&L

### Weekly Tasks
- Run optimization cycle
- Update strategy_params if needed
- Review performance metrics
- Adjust risk parameters if needed

## Testing Strategy

### 1. Paper Trading Mode
- Set `PAPER_TRADING=true` in .env
- Simulate trades without real execution
- Log everything as if real
- Compare with backtest results

### 2. Testnet Trading
- Set `HYPERLIQUID_USE_TESTNET=true`
- Use Hyperliquid testnet
- Test with test funds
- Validate all functionality

### 3. Live Trading (Small Size)
- Start with minimal position size (1% instead of 10%)
- Monitor closely for 1 week
- Gradually increase to full size

## Performance Targets

Based on backtesting and optimization:

- **Win Rate:** 65%+
- **Average Profit per Trade:** 1.5%+
- **Trades per Day:** 2-3
- **Daily Return:** 3-5%
- **Max Drawdown:** <10%
- **Profit Factor:** >2.0

## Next Steps

1. ✅ Create architecture document (this file)
2. ⏳ Implement `src/exchange/hyperliquid_client.py`
3. ⏳ Implement `src/position/position_manager.py`
4. ⏳ Implement `src/utils/trade_logger.py`
5. ⏳ Implement `src/main.py`
6. ⏳ Test in paper trading mode
7. ⏳ Test on testnet
8. ⏳ Deploy to live (small size)
9. ⏳ Monitor and optimize

## Files to Create

```
src/
├── main.py                          # Main trading bot
├── exchange/
│   ├── __init__.py
│   └── hyperliquid_client.py       # Exchange wrapper
├── position/
│   ├── __init__.py
│   └── position_manager.py         # Position tracking
└── utils/
    ├── __init__.py
    └── trade_logger.py             # Trade logging

.env                                 # Environment config
```

## Estimated Development Time

- Exchange wrapper: 2 hours
- Position manager: 2 hours
- Trade logger: 1 hour
- Main loop: 3 hours
- Testing: 4 hours
- **Total: ~12 hours**

Ready to build! 🚀
