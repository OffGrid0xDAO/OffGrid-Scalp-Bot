# Hyperliquid Mainnet Live Trading Setup

## ⚠️ IMPORTANT: Real Money Trading

This bot is configured to trade on **Hyperliquid MAINNET** with **real money**. The position size is **10% of your account per trade** with **25x leverage** (250% exposure), allowing you to test profitability with real fees and slippage.

## Quick Start

### 1. Prerequisites

**You need:**
- Hyperliquid account with funds
- Private key configured in environment
- Telegram bot token for notifications
- Minimum $200-500 in account recommended

### 2. Environment Setup

Create `.env` file in project root:

```bash
# Hyperliquid API
HYPERLIQUID_PRIVATE_KEY=your_private_key_here

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional: Claude AI for optimization
ANTHROPIC_API_KEY=your_api_key
```

**Security:** Never commit `.env` file! Add to `.gitignore`.

### 3. Test Connection

```bash
python3 -c "
from src.exchange.hyperliquid_client import HyperliquidClient
client = HyperliquidClient(testnet=False)
info = client.get_account_info()
print(f'Account Balance: \${info[\"marginSummary\"][\"accountValue\"]:.2f}')
"
```

### 4. Start Bot

```bash
./start_bot.sh
```

## Configuration

### Position Size

Default: **10% of account per trade**

With 25x leverage on Hyperliquid, this means:
- 10% of account = **250% exposure** per trade
- Maximum 1 trade at a time

To adjust, edit `live_trading_bot.py:34`:

```python
def __init__(self, mode: str = 'LIVE', position_size_pct: float = 10.0):
```

**Recommended percentages:**
- Conservative: 5-10% (125-250% exposure)
- Moderate: 10-15% (250-375% exposure)
- Aggressive: 15-20% (375-500% exposure)

**Never exceed 20% as it risks liquidation with 25x leverage!**

### Trading Costs

**Hyperliquid Mainnet:**
- **Taker Fee:** 0.05%
- **Maker Fee:** 0.02% (rebate)
- **Estimated Slippage:** 0.02-0.05% (depends on market conditions)

**Total Cost per Trade:** ~0.07-0.10%

This means:
- Entry: -0.07%
- Exit: -0.07%
- **Round Trip Cost:** ~0.14%

The bot accounts for these costs in profit calculations.

### Leverage

Default: Spot trading (no leverage)

To enable leverage, modify in `HyperliquidClient`:
- Edit leverage settings in exchange client
- **NOT RECOMMENDED** for initial testing
- Higher risk, can amplify losses

## Strategy Details

### Iteration 10 Parameters

**Entry:**
- Quality Score Min: 50
- Confluence Min: 15
- Volume Ratio: 1.0+
- Checks every 60 seconds

**Exit:**
- Take Profit: 5.0%
- Stop Loss: 0.75%
- Profit Lock: 1.5%
  - Once profit reaches +1.5%, trade won't go negative
  - Protects against reversals

### Expected Performance

**Backtest Results (15m ETH):**
- Return: +2.19%
- Win Rate: 41%
- Avg Win: +2.85%
- Avg Loss: -1.03%
- Profit Factor: ~2.77

**With Real Costs (0.14% per round trip):**
- Net Win: +2.71% (2.85% - 0.14%)
- Net Loss: -1.17% (1.03% + 0.14%)
- Expected Return: ~1.9-2.0% (slightly lower than backtest)

## Safety Features

### Built-in Protection

1. **Stop Loss:** Hard stop at -0.75%
2. **Profit Lock:** Protects gains after +1.5%
3. **Single Position:** Max 1 trade at a time
4. **Small Positions:** $50 default = low risk
5. **Quality Filter:** Only high-quality signals (score ≥50)

### Monitoring

**Telegram Notifications:**
- 🚀 Entry signals with quality score
- ✅ Profitable exits
- ❌ Stop loss hits
- 📊 Trade summaries

**Console Logs:**
- Real-time price updates
- Signal detection
- Entry/exit reasons
- P&L tracking

### Emergency Stop

Press `Ctrl+C` to stop bot gracefully:
- Closes monitoring loop
- Keeps existing positions open
- Sends Telegram notification
- Logs final status

To force-close positions, use Hyperliquid web interface.

## Risk Management

### Per-Trade Risk

With 10% of account and 0.75% SL (at 25x leverage):
- **Max Loss:** 0.75% of position = **7.5% of account** (worst case)
- Stop loss protection limits downside
- Profit lock at +1.5% protects gains

### Daily Risk

Typical activity:
- ~2-3 trades per day (strategy avg)
- Max daily loss (3 bad trades): **~20-25% of account**
- Strategy has 41% win rate, so losses are expected

### Account Requirements

**Minimum:** $200
- 10% = $20 per trade ($500 exposure with leverage)
- Provides buffer for multiple trades

**Recommended:** $500-1000
- More comfortable margin
- Can handle losing streaks
- Better for risk management

**Important:** Start small to test the strategy with real market conditions!

## Monitoring Performance

### Metrics to Track

**Daily:**
- Number of trades
- Win rate %
- Net P&L
- Quality of signals

**Weekly:**
- Total return %
- vs. Backtest performance
- Fee impact
- Slippage impact

### Expected Results

**First Week:**
- 5-10 trades expected
- 40-45% win rate expected
- +1.5-2.5% target return
- Some variance is normal

**First Month:**
- 20-40 trades
- Should stabilize near 41% win rate
- Target +5-8% return
- Clear fee/slippage impact visible

## Troubleshooting

### Bot Won't Start

```bash
# Check environment variables
./start_bot.sh

# Test Hyperliquid connection
python3 -c "from src.exchange.hyperliquid_client import HyperliquidClient; print('OK')"

# Check Telegram
python3 -c "from src.notifications.telegram_bot import TelegramBot; TelegramBot().send_message('Test')"
```

### No Trades Executing

**Possible causes:**
1. No qualifying signals (quality < 50)
2. Market conditions don't meet filters
3. Already in position

**Check:**
- Console logs for "No qualifying entry signal"
- Quality scores in signals
- Current market volatility

### Unexpected Losses

**Review:**
1. Slippage higher than expected?
2. Stop loss triggers working?
3. Profit lock functioning?

**Normal behavior:**
- Some losing trades expected (59% lose on average)
- Losses should stay near -0.75%
- Wins should average +2.5-3.0%

## Advanced Configuration

### Adjust Quality Threshold

Edit `src/strategy/strategy_params.json`:

```json
{
  "entry_filters": {
    "min_quality_score": 50.0  // Increase to 60-70 for fewer, better trades
  }
}
```

**Higher = Fewer trades, potentially better quality**
**Lower = More trades, potentially lower quality**

### Change Timeframe

Current: 15min (proven optimal)

To try different timeframe:
1. Edit `strategy_params.json`
2. Update data fetching in `fetch_latest_data()`
3. Re-backtest first!

### Multiple Symbols

Currently: ETH only

To add more symbols:
- Modify bot to loop through symbols
- Maintain quality filters
- Watch position limits

## Performance Tracking

### Log Files

Bot creates:
- `trading_data/live_trades.json` - All trade records
- Console output - Real-time monitoring
- Telegram - Trade notifications

### Analysis

After 1-2 weeks, analyze:

```python
import json
with open('trading_data/live_trades.json') as f:
    trades = json.load(f)

wins = [t for t in trades if t['profit_pct'] > 0]
losses = [t for t in trades if t['profit_pct'] < 0]

print(f"Win Rate: {len(wins)/len(trades)*100:.1f}%")
print(f"Avg Win: {sum(t['profit_pct'] for t in wins)/len(wins):.2f}%")
print(f"Avg Loss: {sum(t['profit_pct'] for t in losses)/len(losses):.2f}%")
```

## Next Steps

1. **Run for 1-2 weeks** with $50 positions
2. **Monitor performance** vs. backtest (target: 2%+ return)
3. **Analyze real costs** (fees + slippage impact)
4. **Adjust if needed:**
   - Increase position size if profitable
   - Tweak quality threshold
   - Consider other symbols

## Support

**Issues?**
1. Check console logs
2. Review Telegram notifications
3. Test exchange connection
4. Verify environment variables

**Questions?**
- Review `LIVE_TRADING_README.md`
- Check `trading_data/iteration_10_results.json` for backtest
- Test in paper mode first if unsure

---

**Remember:**
- Start small ($50 positions)
- Monitor closely first week
- Expect some losing trades (normal)
- Target: 2%+ return over 2-4 weeks with real costs

**Ready to trade!** 🚀
