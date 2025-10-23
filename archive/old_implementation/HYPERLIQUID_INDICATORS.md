# Hyperliquid API - Available Data & Indicators

## Raw Data Available from Hyperliquid API

### Candle (OHLCV) Data
The `candles_snapshot()` method returns:
- **t** - Start timestamp (milliseconds since epoch)
- **T** - End timestamp (milliseconds since epoch)
- **s** - Symbol (e.g., "ETH")
- **i** - Interval (e.g., "5m")
- **o** - Open price
- **c** - Close price
- **h** - High price
- **l** - Low price
- **v** - Volume
- **n** - Number of trades

### Supported Timeframes
- 1m, 3m, 5m, 15m, 30m
- 1h, 2h, 4h, 6h, 8h, 12h
- 1d, 1w, 1M

### Other Available Data
- Order book L2 snapshots (`l2_snapshot`)
- User fills/trades (`user_fills`, `user_fills_by_time`)
- Funding rates (`funding_history`, `user_funding_history`)
- Account state (`user_state`, `portfolio`)
- Open orders (`open_orders`, `frontend_open_orders`)
- Historical orders (`historical_orders`)
- User fees (`user_fees`)
- Price feeds (`all_mids`)

---

## Indicators We Can Calculate

### ✅ Already Implemented

#### 1. EMAs (Exponential Moving Averages)
- **Source**: Close price
- **Periods**: 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145
- **Color Logic**: Green if price > EMA, Red if price < EMA
- **Use Case**: Trend identification, ribbon analysis

#### 2. EMA Ribbon State
- **Source**: All 28 EMAs
- **States**: all_green, mixed_green, mixed, mixed_red, all_red
- **Logic**: Percentage of green vs red EMAs
- **Use Case**: Overall market trend strength

---

### 🔧 Can Be Easily Added

#### 3. EMA Crossovers ⭐ (Your Question!)
**What it is**: Detects when one EMA crosses above/below another EMA
**How to calculate**:
```python
# Golden Cross (bullish): Fast EMA crosses above Slow EMA
if ema_fast[i] > ema_slow[i] and ema_fast[i-1] <= ema_slow[i-1]:
    signal = "bullish_cross"

# Death Cross (bearish): Fast EMA crosses below Slow EMA
if ema_fast[i] < ema_slow[i] and ema_fast[i-1] >= ema_slow[i-1]:
    signal = "bearish_cross"
```

**Popular pairs**:
- EMA5/EMA10 (ultra fast scalping)
- EMA10/EMA20 (fast)
- EMA20/EMA50 (medium)
- EMA50/EMA100 (slow/swing)

**Data needed**: ✅ Already have it (EMAs calculated)

---

#### 4. RSI (Relative Strength Index)
**What it is**: Momentum oscillator (0-100) showing overbought/oversold
**How to calculate**:
```python
import pandas as pd

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

**Data needed**: ✅ Close prices (already have)
**Typical values**:
- RSI > 70 = Overbought
- RSI < 30 = Oversold

---

#### 5. MACD (Moving Average Convergence Divergence)
**What it is**: Trend-following momentum indicator
**How to calculate**:
```python
ema_12 = close.ewm(span=12).mean()
ema_26 = close.ewm(span=26).mean()
macd_line = ema_12 - ema_26
signal_line = macd_line.ewm(span=9).mean()
histogram = macd_line - signal_line
```

**Data needed**: ✅ Close prices (already have)
**Signals**:
- MACD crosses above signal = Bullish
- MACD crosses below signal = Bearish

---

#### 6. Bollinger Bands
**What it is**: Volatility bands around moving average
**How to calculate**:
```python
sma_20 = close.rolling(window=20).mean()
std_20 = close.rolling(window=20).std()
upper_band = sma_20 + (2 * std_20)
lower_band = sma_20 - (2 * std_20)
```

**Data needed**: ✅ Close prices (already have)
**Signals**:
- Price touching upper band = Overbought
- Price touching lower band = Oversold
- Squeeze = Low volatility (potential breakout)

---

#### 7. ATR (Average True Range)
**What it is**: Volatility indicator
**How to calculate**:
```python
high_low = high - low
high_close = abs(high - close.shift())
low_close = abs(low - close.shift())
true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
atr = true_range.rolling(window=14).mean()
```

**Data needed**: ✅ High, Low, Close (already have)
**Use Case**: Stop loss placement, position sizing

---

#### 8. Volume Indicators

##### Volume SMA
```python
volume_sma = volume.rolling(window=20).mean()
volume_spike = volume > (volume_sma * 1.5)  # 50% above average
```

##### Volume Weighted Average Price (VWAP)
```python
typical_price = (high + low + close) / 3
vwap = (typical_price * volume).cumsum() / volume.cumsum()
```

**Data needed**: ✅ Volume, OHLC (already have)
**Use Case**: Institutional price levels, liquidity detection

---

#### 9. Stochastic Oscillator
**What it is**: Momentum indicator comparing close to high-low range
**How to calculate**:
```python
lowest_low = low.rolling(window=14).min()
highest_high = high.rolling(window=14).max()
k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
d_percent = k_percent.rolling(window=3).mean()
```

**Data needed**: ✅ High, Low, Close (already have)
**Signals**:
- %K > 80 = Overbought
- %K < 20 = Oversold

---

#### 10. Price Action Patterns

##### Candlestick Patterns
```python
# Doji
is_doji = abs(open - close) < (high - low) * 0.1

# Hammer
body = abs(close - open)
lower_shadow = min(open, close) - low
is_hammer = (lower_shadow > body * 2) and (high - max(open, close) < body)

# Engulfing
bullish_engulfing = (open < close) and (open < prev_close) and (close > prev_open)
```

**Data needed**: ✅ OHLC (already have)

---

#### 11. Support/Resistance Levels
```python
# Find local highs/lows
window = 20
resistance = high.rolling(window=window).max()
support = low.rolling(window=window).min()
```

**Data needed**: ✅ High, Low (already have)

---

#### 12. Rate of Change (ROC)
```python
roc = ((close - close.shift(period)) / close.shift(period)) * 100
```

**Data needed**: ✅ Close (already have)

---

## ❌ What Hyperliquid DOESN'T Provide

These indicators require external data or calculations:
- Order flow data (tape reading)
- Market depth heatmaps
- Sentiment indicators (Fear & Greed)
- On-chain metrics (if applicable)
- News/social sentiment

---

## How to Add New Indicators

### Example: Adding EMA Crossover Detection

Edit `fetch_hyperliquid_history.py` and add:

```python
def detect_ema_crossovers(self, df, fast=5, slow=10):
    """Detect EMA crossovers"""
    fast_col = f'ema_{fast}'
    slow_col = f'ema_{slow}'

    # Current position
    df['ema_position'] = np.where(df[fast_col] > df[slow_col], 'above', 'below')

    # Previous position
    df['prev_ema_position'] = df['ema_position'].shift(1)

    # Detect crossovers
    df['ema_cross'] = 'none'
    df.loc[(df['ema_position'] == 'above') & (df['prev_ema_position'] == 'below'), 'ema_cross'] = 'golden_cross'
    df.loc[(df['ema_position'] == 'below') & (df['prev_ema_position'] == 'above'), 'ema_cross'] = 'death_cross'

    return df
```

Then call it in the main processing:
```python
df = fetcher.calculate_emas(candles)
df = fetcher.determine_ema_colors(df)
df = fetcher.detect_ema_crossovers(df, fast=5, slow=10)  # NEW!
df = fetcher.analyze_ribbon_state(df)
```

---

## Summary

### ✅ Available from API:
- OHLCV candles (all timeframes)
- Volume
- Number of trades per candle
- Timestamps

### ✅ Can Calculate from OHLCV:
- **EMAs** ✅ (already done - 28 periods)
- **EMA Crossovers** ⭐ (easy to add!)
- **RSI** (momentum)
- **MACD** (trend)
- **Bollinger Bands** (volatility)
- **ATR** (volatility)
- **Volume indicators** (VWAP, volume spikes)
- **Stochastic** (momentum)
- **Candlestick patterns**
- **Support/Resistance**
- **ROC** (rate of change)

### 📊 Best Additions for Your Strategy:
1. **EMA Crossovers** - Confirm ribbon signals
2. **RSI** - Avoid overbought/oversold entries
3. **Volume analysis** - Confirm breakouts
4. **ATR** - Dynamic stop loss placement

All of these can be calculated from the data we already fetch! 🎉
