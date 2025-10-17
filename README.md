# 🤖 Dual-Timeframe Trading Bot with Claude AI

Automated cryptocurrency trading bot using Annii's EMA Ribbon Strategy with Claude AI decision-making.

## 🚀 Quick Start

### Automated Trading
```bash
python run_dual_bot.py
```
Fully automated with Claude AI making trading decisions.

### Interactive Manual Mode
```bash
python interactive_mode.py
```
Chat with Claude and manually execute trades.

---

## 📊 Features

- **Dual-Timeframe Analysis** - Monitors 5min + 15min charts simultaneously
- **Claude AI Decision Making** - Uses Claude Sonnet 4.5 for trade analysis
- **Annii's EMA Ribbon Strategy** - Proven scalping strategy
- **Automatic TP/SL** - Smart take-profit and stop-loss management
- **Yellow EMA Trailing Stops** - Dynamic stop-loss based on support/resistance
- **Cost Optimized** - 62-78% cost reduction vs original
- **Interactive Mode** - Chat with Claude for manual trading
- **Real-Time Cost Tracking** - Monitor API costs live

---

## 💰 Cost Summary

### Optimized Costs (After Updates)

| Mode | Cost/3hr | Cost/8hr | Monthly (22 days) |
|------|----------|----------|-------------------|
| **Automated** | $1.15-2.05 | $3.07-5.47 | $67-120 |
| **Interactive** | $0.25 + chat | $0.67 + chat | $15 + chat |

**Original cost:** $5.40 per 3 hours → **Savings: 62-78%** 🎉

---

## 📁 Documentation

- **[UPDATES_SUMMARY.md](UPDATES_SUMMARY.md)** - What changed, quick start
- **[COST_OPTIMIZATION_SUMMARY.md](COST_OPTIMIZATION_SUMMARY.md)** - Full cost analysis
- **[COST_QUICK_REFERENCE.md](COST_QUICK_REFERENCE.md)** - Quick settings guide
- **[INTERACTIVE_MODE_GUIDE.md](INTERACTIVE_MODE_GUIDE.md)** - Interactive mode tutorial
- **[TWO_TIER_THRESHOLD_EXPLAINED.md](TWO_TIER_THRESHOLD_EXPLAINED.md)** - 50%/85% threshold system

---

## ⚙️ Setup

### 1. Install Dependencies
```bash
pip install anthropic selenium hyperliquid-python-sdk eth-account python-dotenv
```

### 2. Configure .env File
```bash
# Trading
HYPERLIQUID_PRIVATE_KEY=your_key_here
USE_TESTNET=true
AUTO_TRADE=true
POSITION_SIZE_PCT=10
LEVERAGE=25
MIN_CONFIDENCE=0.75

# Claude AI
ANTHROPIC_API_KEY=your_claude_api_key_here
```

### 3. Setup TradingView
1. Open TradingView and log in
2. Add Annii's EMA Ribbon indicator to chart
3. Configure 5min and 15min timeframes

### 4. Run Bot
```bash
# Automated mode
python run_dual_bot.py

# Interactive mode
python interactive_mode.py
```

---

## 🎮 Interactive Mode

New feature! Chat with Claude and manually execute trades.

```bash
>>> chat should I enter long here?
🧠 Both timeframes show strong green alignment. Fresh transition detected.
   Price holding above yellow EMA support. Good long setup with stop at $2638.

>>> long
✅ LONG opened: 0.0500 ETH @ $2651.00 | TP @ $2690.78, SL @ $2638.49

>>> status
💼 POSITION: LONG 0.0500 @ $2651.00
   🟢 PnL: $+4.50
```

**Commands:**
- `chat <question>` - Ask Claude about market
- `long` - Open long position
- `short` - Open short position
- `close` - Close position
- `status` - Show market status
- `cost` - Show API costs
- `exit` - Stop bot

---

## 📈 Strategy

### Annii's EMA Ribbon Strategy

**Entry Rules:**
- **LONG**: Wait for 100% green ribbon, enter on breakout or yellow EMA retest
- **SHORT**: Wait for 100% red ribbon, enter on breakdown or yellow EMA retest

**Exit Rules:**
- **Outer Bands Spreading**: Warning sign of pullback
- **Yellow EMA Break**: Price crosses yellow EMA (wrong direction) = EXIT
- **Take Profit**: 1.5% target (auto-set)
- **Stop Loss**: Yellow EMA level (dynamic trailing)

**Dual-Timeframe Confirmation:**
- 15min = Trend direction
- 5min = Entry timing
- Both aligned = HIGH confidence
- Conflicting = WAIT

---

## 🛠️ Configuration

### Two-Tier Threshold System (NEW!)
**File:** `dual_timeframe_bot.py` lines 322-333

The bot uses two detection thresholds:
- **50% threshold** = "Start watching" (6+ EMAs flipped)
  - Triggers Claude analysis and commentary
  - Entry Strength shows: BUILDING 👀
  - Does NOT enter trades yet

- **85% threshold** = "Consider entering" (10+ EMAs flipped)
  - Ribbon nearly complete
  - Entry Strength shows: STRONG 💪
  - Claude can recommend entry if conditions met

```python
elif len(green_emas) >= non_yellow_total * 0.5:  # 50% = start watching
    state = 'all_green'
    if len(green_emas) >= non_yellow_total * 0.85:  # 85% = consider entry
        entry_strength = 'strong'
    else:
        entry_strength = 'building'
```

**See [TWO_TIER_THRESHOLD_EXPLAINED.md](TWO_TIER_THRESHOLD_EXPLAINED.md) for full details**

### Adjust API Call Frequency
**File:** `dual_timeframe_bot.py` line 101
```python
self.min_api_call_interval = 60  # seconds
```
- `60` = Current (balanced)
- `90` = More conservative (save 33%)
- `120` = Very conservative (save 50%)

### Adjust Commentary
**File:** `dual_timeframe_bot.py` line 96
```python
self.commentary_interval = 600  # 10 minutes
```
- `600` = Current (10 min)
- `900` = Less frequent (15 min)
- `300` = More frequent (5 min)

### Reduce Historical Data
**File:** `claude_trader.py` line 226
```python
limit=200  # snapshots
```
- `200` = 4 hours context (current)
- `150` = 3 hours (save 25%)
- `100` = 2 hours (save 50%)

---

## 💡 Tips

1. **Test on testnet first** - Set `USE_TESTNET=true`
2. **Start small** - Use 5-10% position size initially
3. **Monitor costs** - Check dashboard regularly
4. **Use interactive mode** - Great for learning the strategy
5. **Adjust settings** - Fine-tune based on your needs

---

## 📊 Cost Tracking

### Live Dashboard
```
💰 API COSTS: $0.0425 (3 calls)
   Est. hourly: $0.85 | Cached: 6,000 tokens
```

### Exit Summary
```
===============================================================================
💰 CLAUDE API COST SUMMARY
===============================================================================
Total API Calls: 95
Session Cost: $1.7850
Estimated Hourly: $0.60
Estimated Daily (8 hours): $4.80
===============================================================================
```

---

## 🔧 Files

### Main Files
- `dual_timeframe_bot.py` - Core bot logic
- `claude_trader.py` - Claude AI integration
- `run_dual_bot.py` - Automated mode entry
- `interactive_mode.py` - Interactive mode entry
- `.env` - Configuration file

### Documentation
- `README.md` - This file
- `UPDATES_SUMMARY.md` - Recent changes
- `COST_OPTIMIZATION_SUMMARY.md` - Full cost details
- `COST_QUICK_REFERENCE.md` - Quick settings
- `INTERACTIVE_MODE_GUIDE.md` - Interactive tutorial

---

## ⚠️ Safety Notes

1. **Testnet First** - Always test on testnet before mainnet
2. **Start Small** - Use conservative position sizes
3. **Monitor Closely** - Especially during first few trades
4. **Set Limits** - Consider daily loss limits
5. **Track Costs** - Monitor API costs regularly

---

## 🎯 Example Results

### Automated Mode (3 hours)
- API Calls: 108
- Cost: $1.60
- Trades: 3
- Commentary: 18 updates

### Interactive Mode (3 hours)
- API Calls: 30
- Cost: $0.45 (18 monitoring + 12 chat)
- Trades: 2 (manual)
- Commentary: 18 updates

---

## 📝 Changelog

### Latest Updates
- ✅ **Two-tier threshold system** (50% watch / 85% enter) for better entries
- ✅ Reduced API costs by 62-78%
- ✅ Added smart call logic (only on state changes)
- ✅ Re-enabled commentary every 10 minutes
- ✅ Added interactive manual trading mode
- ✅ Added real-time cost tracking
- ✅ Added exit cost summary

---

## 🤝 Support

Having issues?
1. Check documentation files
2. Review cost tracking in dashboard
3. Test settings on testnet first
4. Start with conservative intervals

---

## 📜 License

MIT License - Trade at your own risk

---

**Built with ❤️ and Claude AI**

*Happy Trading! 📈💰*
