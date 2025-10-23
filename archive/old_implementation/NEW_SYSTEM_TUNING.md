# 🎯 User Pattern System Tuning Guide

## Current Status

The system is now using **User Pattern Matching** instead of the old rule-based system.

- **Old System:** 1,078 trades (over-trading)
- **New System:** 1 trade in 70 hours (ultra-selective)
- **Your Manual Trading:** 9 trades in 24 hours (~0.37/hour)

## ⚖️ The Selectivity Spectrum

```
TOO FEW TRADES ←→ TOO MANY TRADES
(missing opportunities)   (over-trading, fees kill profits)

Current:            Target:         Old System:
1 trade/70hrs       9 trades/24hrs  1078 trades/24hrs
0.014/hr           0.37/hr         44.9/hr
```

## 🎛️ Main Tuning Parameters

Edit `trading_rules.json` to adjust:

### 1. Quality Threshold (Most Important)
```json
"quality_filter": {
  "min_score": 75  // 0-100 scale
}
```

**Impact:**
- Lower = More trades (less selective)
- Higher = Fewer trades (more selective)

**Recommended Range:**
- 60-70: Moderately selective (~10-20 trades/day)
- 70-75: Selective (~3-10 trades/day) ← **Current: 75**
- 75-80: Highly selective (~1-5 trades/day)
- 80+: Ultra selective (~<1 trade/day)

### 2. Momentum Requirement
```json
"momentum": {
  "required": true,  // Must have momentum to trade?
  "big_move_threshold": 0.004  // 0.4% move in 10min
}
```

**Impact:**
- `required: false` = Allow non-momentum trades (more signals)
- `required: true` = Only momentum moves (fewer, higher quality)
- Lower threshold = More signals (catch smaller moves)
- Higher threshold = Fewer signals (only big moves)

**Recommended:**
- For MORE trades: `"required": false` or lower threshold to `0.003`
- For FEWER trades: Keep as is or raise to `0.005`

### 3. Frequency Limits
```json
"frequency": {
  "max_trades_per_hour": 1,
  "max_trades_per_4_hours": 2,
  "max_trades_per_day": 12
}
```

**Impact:**
- These are CAPS, not targets
- Prevents over-trading even if quality signals appear
- Adjust based on your risk tolerance

## 🎯 Recommended Tuning Steps

### Step 1: Find the Right Quality Score

Start by testing different `min_score` values:

```bash
# Test with lower threshold (more trades)
# Edit trading_rules.json: "min_score": 70
python3 regenerate_backtest.py

# Check results
cat trading_data/backtest_trades.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Trades: {d['summary']['total_trades']}, Win Rate: {d['summary']['win_rate']*100:.1f}%, PnL: {d['summary']['total_pnl']:+.2f}%\")"

# If too few trades, lower to 65
# If too many trades, raise to 75
# Repeat until you find sweet spot
```

### Step 2: Adjust Momentum Settings

Once you have the right trade frequency, tune momentum:

```json
{
  "momentum": {
    "required": true,  // Try false if you want more trades
    "big_move_threshold": 0.003,  // Lower from 0.004
    "acceleration_threshold": 1.5  // Keep as is
  }
}
```

### Step 3: Set Frequency Caps

Based on your risk tolerance:

```json
{
  "frequency": {
    "max_trades_per_hour": 2,  // Your style: ~0.5/hour
    "max_trades_per_4_hours": 5,
    "max_trades_per_day": 15
  }
}
```

## 📊 Quick Test Commands

```bash
# Regenerate backtest with current rules
python3 regenerate_backtest.py

# Compare new vs old system
python3 compare_trading_systems.py

# View detailed signals (not just trades)
python3 compare_trading_systems.py | grep "SIGNAL #"

# Check backtest summary
cat trading_data/backtest_trades.json | python3 -c "import json,sys; d=json.load(sys.stdin)['summary']; print(f\"Trades: {d['total_trades']}\\nWin Rate: {d['win_rate']*100:.1f}%\\nPnL: {d['total_pnl']:+.2f}%\\nAvg Trade: {d.get('avg_pnl',0):+.2f}%\")"
```

## 🎪 Current Configuration

```json
{
  "version": "user_pattern_1.0",
  "quality_filter": {
    "min_score": 75  // ← TUNE THIS FIRST
  },
  "momentum": {
    "required": true,  // ← Set false for more trades
    "big_move_threshold": 0.004  // ← Lower for more trades
  },
  "frequency": {
    "max_trades_per_hour": 1,
    "max_trades_per_4_hours": 2,
    "max_trades_per_day": 12
  }
}
```

## ✅ Integration Status

**Files Updated:**
- ✅ `trading_rules.json` → User pattern version (active)
- ✅ `rule_based_trader.py` → Wrapper for user pattern system
- ✅ `run_backtest.py` → Updated to pass df_recent for momentum detection
- ✅ `backtest_trades.json` → Regenerated with new system (1 trade)

**Backups:**
- `trading_rules_OLD_PHASE1_BACKUP.json` ← Old rules
- `rule_based_trader_OLD_BACKUP.py` ← Old trader

## ⚠️ About the Optimizer

The Claude optimizer (`rule_optimizer.py`) was designed for the OLD rule structure. It can still run, but it will try to optimize parameters that don't exist in the new system.

**Instead of automated optimization, use manual tuning:**

1. Adjust `min_score` in `trading_rules.json`
2. Run `python3 regenerate_backtest.py`
3. Check if trade frequency matches your style (~0.37/hour)
4. Repeat until satisfied

The new system is based on YOUR profitable trades, so it's already optimized for your edge. You just need to find the right selectivity level.

## 🚀 Next Steps

1. **Adjust Quality Score:** Start at 70, regenerate backtest, check results
2. **Monitor Live:** Run `python3 main.py` and watch for signals
3. **Add More User Trades:** Tell me more manual trades to improve pattern matching
4. **Fine-tune Exits:** Profit targets are in trading_rules.json under "exit"

---

**Remember:** The goal is ~9 trades/24hrs like your manual trading, not 1 trade/70hrs!

Current setting (min_score: 75) is TOO SELECTIVE. Try 65-70 to get closer to your style.
