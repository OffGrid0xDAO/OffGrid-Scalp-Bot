# Trading Strategy Design - EMA Ribbon Intelligence

## 🎯 Core Philosophy

**The Ribbon Tells The Story**: Use EMA ribbon compression/expansion and color dynamics as the primary signal, confirmed by RSI, MACD, VWAP, and Volume.

---

## 📊 Research Findings

### Proven Strategy Results (2020-2025)

**EMA Ribbon Performance (Crypto)**:
- BTC: +75% (2020)
- ETH: +94% (2020)
- XMR: +67% (2020)
- LINK: +107% (2020)

**BTCUSDT Backtest (Aug 2017 - Oct 2025)**:
- H4 timeframe: +12,213% (40% win rate, 42 trades)
- 30M timeframe: +4,205% (27.74% win rate, 393 trades)
- H6 timeframe: +1,682% (40% win rate, 30 trades)

**Key Success Metrics**:
- Win Rate Target: 50-70% (our confluence approach should achieve this)
- Profit Factor Target: 2.0+ (excellent)
- Risk per Trade: Max 2% of equity

---

## 🧠 Strategy Components

### 1. **EMA Ribbon States** (Primary Signal)

#### A. Ribbon Compression (THE SETUP)
**Definition**: When EMAs are tightly packed together (distance < threshold)

**Market Meaning**: Consolidation, low volatility, energy building up

**Calculation**:
```python
# Compression Score (0-100)
def calculate_compression(df, ema_periods):
    """
    Higher score = More compression = Better setup
    """
    distances = []
    for i in range(len(ema_periods)-1):
        fast = f'MMA{ema_periods[i]}_value'
        slow = f'MMA{ema_periods[i+1]}_value'
        distance_pct = abs((df[fast] - df[slow]) / df[slow]) * 100
        distances.append(distance_pct)

    avg_distance = np.mean(distances)

    # Thresholds (tunable by Claude)
    if avg_distance < 0.1:  # Extreme compression
        return 100
    elif avg_distance < 0.3:  # Strong compression
        return 80
    elif avg_distance < 0.5:  # Moderate compression
        return 60
    else:
        return max(0, 60 - (avg_distance - 0.5) * 100)
```

#### B. Ribbon Expansion (THE MOVE)
**Definition**: EMAs spreading apart rapidly

**Market Meaning**: Strong trend, momentum, follow-through

**Calculation**:
```python
# Expansion Rate (candles/period)
def calculate_expansion_rate(df, lookback=5):
    """
    How fast is the ribbon expanding?
    """
    current_spread = df['MMA5_value'].iloc[-1] - df['MMA200_value'].iloc[-1]
    prev_spread = df['MMA5_value'].iloc[-lookback] - df['MMA200_value'].iloc[-lookback]

    expansion_rate = (current_spread - prev_spread) / prev_spread * 100
    return expansion_rate
```

#### C. Ribbon Color Flip (THE TRIGGER)
**Definition**: When ALL or MOST EMAs change from red → green (or vice versa)

**Market Meaning**: Trend reversal confirmed across multiple timeframes

**Entry Trigger**:
```python
def detect_ribbon_flip(df, threshold=0.85):
    """
    When 85%+ of EMAs flip color, that's our signal
    """
    # alignment_pct already calculated in data
    current_alignment = df['alignment_pct'].iloc[-1]
    prev_alignment = df['alignment_pct'].iloc[-2]

    # Bullish flip: red → green
    if prev_alignment < (1 - threshold) and current_alignment > threshold:
        return 'bullish_flip'

    # Bearish flip: green → red
    if prev_alignment > threshold and current_alignment < (1 - threshold):
        return 'bearish_flip'

    return 'none'
```

---

### 2. **The Trade Setup Pattern**

#### OPTIMAL ENTRY CONDITIONS (All must be true):

**Phase 1: Compression (Pre-breakout)**
1. ✅ Ribbon Compression Score > 60
2. ✅ Price consolidating near key EMA (20, 50, or 100)
3. ✅ Volume decreasing (status = 'low' or 'normal')
4. ✅ RSI 14 between 40-60 (neutral, not overbought/oversold)

**Phase 2: Breakout Signal**
1. ✅ Ribbon Color Flip detected (85%+ EMAs flip)
2. ✅ Volume spike (status = 'elevated' or 'spike')
3. ✅ MACD Fast crossover confirms direction
4. ✅ Price breaks above/below key EMA with momentum

**Phase 3: Confirmation (Enter on this bar)**
1. ✅ Confluence Score > 70 (4/5 indicators agree)
2. ✅ Ribbon Expansion Rate > 5% (momentum building)
3. ✅ Important EMA crossover (9/21, 12/26, 20/50, or 50/200)
4. ✅ VWAP position confirms (price above for long, below for short)

#### ENTRY EXECUTION:

**LONG Entry**:
```python
if (compression_score > 60 and
    ribbon_flip == 'bullish_flip' and
    volume_status in ['elevated', 'spike'] and
    confluence_score_long > 70 and
    expansion_rate > 5 and
    df['close'] > df['MMA20_value']):  # Above key EMA

    entry_price = df['close']
    stop_loss = df['MMA20_value'] * 0.995  # 0.5% below EMA20
    take_profit_1 = entry_price * 1.01  # 1% (partial exit 50%)
    take_profit_2 = entry_price * 1.02  # 2% (partial exit 30%)
    take_profit_3 = entry_price * 1.03  # 3% (final exit 20%)
```

**SHORT Entry**:
```python
if (compression_score > 60 and
    ribbon_flip == 'bearish_flip' and
    volume_status in ['elevated', 'spike'] and
    confluence_score_short > 70 and
    expansion_rate > 5 and
    df['close'] < df['MMA20_value']):  # Below key EMA

    entry_price = df['close']
    stop_loss = df['MMA20_value'] * 1.005  # 0.5% above EMA20
    take_profit_1 = entry_price * 0.99  # 1% (partial exit 50%)
    take_profit_2 = entry_price * 0.98  # 2% (partial exit 30%)
    take_profit_3 = entry_price * 0.97  # 3% (final exit 20%)
```

---

### 3. **Exit Strategy (MFE-Based)**

#### A. Partial Profit Taking (Ladder Out)
- **50% at TP1** (1% profit) - Lock in gains quickly
- **30% at TP2** (2% profit) - Let winners run
- **20% at TP3** (3% profit) - Maximum profit capture

#### B. Trailing Stop (For remaining position)
```python
def update_trailing_stop(entry_price, current_price, direction):
    """
    Trail stop using ribbon EMAs
    """
    if direction == 'long':
        # Trail stop to EMA 20, then EMA 50 as profit grows
        if current_price > entry_price * 1.02:
            return max(df['MMA50_value'], entry_price * 1.01)
        else:
            return df['MMA20_value'] * 0.995

    if direction == 'short':
        if current_price < entry_price * 0.98:
            return min(df['MMA50_value'], entry_price * 0.99)
        else:
            return df['MMA20_value'] * 1.005
```

#### C. Emergency Exits (Hard stops)
1. ❌ Ribbon color flips AGAINST position (all EMAs reverse)
2. ❌ Stop loss hit (0.5% below/above entry EMA)
3. ❌ Confluence score drops below 40
4. ❌ Major EMA crossover against position (50/200 death/golden cross)

---

### 4. **Optimal Trade Detection** (The "God Mode" Analysis)

**Purpose**: Find PERFECT entry/exit points using hindsight to train the strategy

```python
def find_optimal_trades(df, max_lookback=50):
    """
    Scan historical data for PERFECT setups

    For each setup:
    1. Find compression zones
    2. Find breakout with ribbon flip
    3. Calculate MFE (Maximum Favorable Excursion)
    4. Find optimal exit (70% of MFE)
    5. Record all conditions at entry
    """
    optimal_trades = []

    for i in range(len(df) - max_lookback):
        # Check if this was a compression zone
        compression_score = calculate_compression(df.iloc[i])

        if compression_score > 60:
            # Look for breakout in next 10 candles
            for j in range(i+1, min(i+10, len(df))):
                flip = detect_ribbon_flip(df.iloc[j])

                if flip in ['bullish_flip', 'bearish_flip']:
                    # Found a setup! Now find MFE
                    mfe_data = calculate_mfe(df, j, max_lookback, flip)

                    optimal_trades.append({
                        'entry_idx': j,
                        'entry_price': df['close'].iloc[j],
                        'direction': 'long' if flip == 'bullish_flip' else 'short',
                        'compression_score': compression_score,
                        'confluence_score': df['confluence_score_long' if flip == 'bullish_flip' else 'confluence_score_short'].iloc[j],
                        'volume_status': df['volume_status'].iloc[j],
                        'rsi_14': df['rsi_14'].iloc[j],
                        'macd_trend': df['macd_fast_trend'].iloc[j],
                        'mfe': mfe_data['mfe'],
                        'optimal_exit_idx': mfe_data['exit_idx'],
                        'optimal_profit_pct': mfe_data['profit_pct']
                    })

    return pd.DataFrame(optimal_trades)
```

---

## 🤖 Claude LLM Optimization Loop

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      OPTIMIZATION LOOP                          │
│                   (Every 30 minutes / Daily)                    │
└─────────────────────────────────────────────────────────────────┘
                                ↓
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        ↓                                               ↓
┌───────────────┐                              ┌────────────────┐
│  GATHER DATA  │                              │  FIND OPTIMAL  │
│               │                              │     TRADES     │
│ • New candles │                              │                │
│ • Indicators  │                              │ • MFE analysis │
│ • Since last  │                              │ • Perfect      │
│   update      │                              │   setups       │
└───────┬───────┘                              └────────┬───────┘
        │                                               │
        └───────────────────┬───────────────────────────┘
                           ↓
                  ┌─────────────────┐
                  │  RUN BACKTEST   │
                  │                 │
                  │ • Current rules │
                  │ • Performance   │
                  │ • Win rate      │
                  │ • Profit factor │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │  COMPARE TO     │
                  │  OPTIMAL        │
                  │                 │
                  │ • Gap analysis  │
                  │ • Missed trades │
                  │ • False signals │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │  ASK CLAUDE     │
                  │                 │
                  │ "What changes   │
                  │  will improve   │
                  │  performance?"  │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │  UPDATE RULES   │
                  │                 │
                  │ • Thresholds    │
                  │ • Weights       │
                  │ • Conditions    │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │  SAVE & LOG     │
                  │                 │
                  │ • New config    │
                  │ • Performance   │
                  │ • Reasoning     │
                  └─────────────────┘
```

### Claude Prompt Template

```python
OPTIMIZATION_PROMPT = """
You are a quantitative trading strategist optimizing an EMA ribbon compression/expansion strategy.

## CURRENT PERFORMANCE (Last {period}):
- Win Rate: {win_rate}%
- Profit Factor: {profit_factor}
- Total Trades: {total_trades}
- Avg Profit: {avg_profit}%
- Avg Loss: {avg_loss}%
- Max Drawdown: {max_drawdown}%

## OPTIMAL PERFORMANCE (Same period):
- Perfect Trades Identified: {optimal_trades}
- Average Optimal Profit: {optimal_avg_profit}%
- Opportunities Missed: {missed_trades}
- False Signals: {false_signals}

## CURRENT STRATEGY RULES:
```json
{current_rules_json}
```

## PERFORMANCE GAP ANALYSIS:
{gap_analysis}

## YOUR TASK:
Analyze why our strategy underperformed vs optimal trades and suggest precise parameter adjustments.

Focus on:
1. **Entry Timing**: Are we entering too early/late?
2. **Compression Threshold**: Should we require tighter compression?
3. **Confluence Score**: Is 70 too low/high?
4. **Exit Strategy**: Are we exiting too early and missing profit?
5. **Risk Management**: Stop loss placement optimal?

Provide SPECIFIC numeric adjustments in JSON format:
```json
{
  "reasoning": "...",
  "adjustments": {
    "compression_threshold": 65,  // from 60
    "confluence_score_min": 75,   // from 70
    "take_profit_1_pct": 1.2,     // from 1.0
    "trailing_stop_ema": 50,      // from 20
    ...
  },
  "expected_improvement": "+5% win rate, +0.3 profit factor"
}
```
"""
```

### Strategy Parameters (Tunable by Claude)

```python
STRATEGY_PARAMS = {
    # Compression Detection
    "compression_threshold": 60,  # Score 0-100
    "compression_lookback": 20,   # Candles

    # Entry Conditions
    "ribbon_flip_threshold": 0.85,  # % of EMAs that must flip
    "confluence_score_min": 70,     # Min score for entry
    "expansion_rate_min": 5,        # % per period
    "volume_requirement": ["elevated", "spike"],

    # RSI Filters
    "rsi_min": 40,
    "rsi_max": 60,
    "rsi_overbought": 70,
    "rsi_oversold": 30,

    # Exit Strategy
    "take_profit_1_pct": 1.0,   # % profit for 50% exit
    "take_profit_2_pct": 2.0,   # % profit for 30% exit
    "take_profit_3_pct": 3.0,   # % profit for 20% exit
    "stop_loss_pct": 0.5,       # % below entry EMA
    "trailing_stop_ema": 20,    # Which EMA to use for trailing

    # Risk Management
    "max_risk_per_trade_pct": 2.0,  # % of equity
    "max_daily_loss_pct": 5.0,
    "max_concurrent_trades": 3,

    # MFE Optimization
    "mfe_capture_target": 0.70,  # Capture 70% of max profit
    "mfe_lookback": 50,          # Candles to scan for MFE
}
```

---

## 📁 Implementation Files Structure

```
src/
├── strategy/
│   ├── __init__.py
│   ├── ribbon_analyzer.py       # Compression/expansion detection
│   ├── optimal_trades.py        # Find perfect setups (MFE)
│   ├── entry_conditions.py      # Trade setup detection
│   ├── exit_manager.py          # Partial exits, trailing stops
│   ├── risk_manager.py          # Position sizing, limits
│   └── strategy_params.json     # Current tunable parameters
│
├── backtesting/
│   ├── __init__.py
│   ├── backtest_engine.py       # Run historical simulation
│   ├── performance_metrics.py   # Win rate, profit factor, etc.
│   └── comparison.py            # Compare vs optimal
│
├── optimization/
│   ├── __init__.py
│   ├── claude_optimizer.py      # LLM optimization loop
│   ├── gap_analyzer.py          # Find performance gaps
│   └── parameter_updater.py     # Apply Claude suggestions
│
└── live/
    ├── __init__.py
    ├── dual_timeframe_trader.py # Execute trades
    ├── position_manager.py      # Track open positions
    └── execution_engine.py      # Order placement
```

---

## 🎯 Success Criteria

### Minimum Viable Performance (MVP)
- Win Rate: 50%+
- Profit Factor: 1.5+
- Max Drawdown: < 10%
- Capture 50%+ of optimal trades

### Target Performance (After Claude Optimization)
- Win Rate: 60%+
- Profit Factor: 2.0+
- Max Drawdown: < 7%
- Capture 70%+ of optimal trades

### Exceptional Performance (Goal)
- Win Rate: 70%+
- Profit Factor: 3.0+
- Max Drawdown: < 5%
- Capture 80%+ of optimal trades

---

## 🚀 Next Steps

1. ✅ Implement `ribbon_analyzer.py` - Detect compression/expansion
2. ✅ Implement `optimal_trades.py` - Find perfect setups with MFE
3. ✅ Implement `backtest_engine.py` - Run historical simulation
4. ✅ Implement `claude_optimizer.py` - LLM optimization loop
5. ✅ Test on 1h timeframe first (longest history)
6. ✅ Compare backtest vs optimal
7. ✅ Run first Claude optimization iteration
8. ✅ Deploy to lower timeframes (5m, 15m)
9. ✅ Go live with paper trading
10. ✅ Iterate and improve!

---

**Remember**: The ribbon tells the story. Compression = Setup. Expansion = Move. Color flip = Trigger. Everything else is confirmation.
