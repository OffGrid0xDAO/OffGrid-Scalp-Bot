# ⚡ 25X LEVERAGE POSITION SIZING

## 🎯 The Problem

With **25x leverage** on Hyperliquid:
- Liquidation happens at ~**4% move** against position (100% / 25)
- If price moves 4% wrong way → **LIQUIDATED** → **100% loss**!
- Standard 30% position size would be **EXTREMELY DANGEROUS**

---

## 🧮 Safe Position Sizing Formula

### Risk Management Rule
**Risk maximum 3% of account per trade**

### The Math

```
Capital = $1000
Max Risk = 3% = $30
Stop Loss = 2% from entry
Leverage = 25x

Position Value = Risk / Stop Loss %
Position Value = $30 / 0.02 = $1500

Margin Required = Position Value / Leverage
Margin Required = $1500 / 25 = $60

Position Size (as % of capital) = Margin / Capital
Position Size = $60 / $1000 = 6% = 0.06
```

### Result
With 25x leverage and 3% max risk:
- **Max Position Size: 6% of capital** (0.06)
- This controls: 6% × 25 = **150% position value**
- With 2% stop loss: 150% × 2% = **3% loss** ✓
- Liquidation buffer: 4% - 2% = **2% safety margin**

---

## 📊 Position Size Examples

| Capital | Leverage | Max Risk | Stop Loss | Position Size | Margin Used | Position Value |
|---------|----------|----------|-----------|---------------|-------------|----------------|
| $1000 | 25x | 3% ($30) | 2% | **6%** ($60) | $60 | $1500 |
| $1000 | 25x | 3% ($30) | 1.5% | **8%** ($80) | $80 | $2000 |
| $1000 | 25x | 3% ($30) | 3% | **4%** ($40) | $40 | $1000 |

---

## ⚠️ Liquidation Risk

### Liquidation Price Calculation
```
For LONG:
Liquidation Price = Entry × (1 - 1/Leverage)
Liquidation Price = Entry × (1 - 1/25)
Liquidation Price = Entry × 0.96 (4% drop)

For SHORT:
Liquidation Price = Entry × (1 + 1/Leverage)
Liquidation Price = Entry × 1.04 (4% rise)
```

### Safety Margins
| Stop Loss | Liquidation Distance | Safety Buffer |
|-----------|---------------------|---------------|
| 1.5% | 4% | 2.5% ✓✓✓ |
| 2.0% | 4% | 2.0% ✓✓ |
| 2.5% | 4% | 1.5% ✓ |
| 3.0% | 4% | 1.0% ⚠️ |
| 3.5% | 4% | 0.5% ❌ |

**Recommended: Keep stop loss ≤ 2% for 2% safety buffer**

---

## 🔧 Updated Position Sizing for All Iterations

### Base Parameters (All Iterations)
```json
{
  "leverage": 25,
  "max_risk_per_trade": 0.03,
  "max_position_size": 0.06,
  "base_sl_pct": 0.02,
  "liquidation_buffer": 0.02
}
```

### Conservative (Iterations 1-3)
```json
{
  "max_position_size": 0.06,
  "base_sl_pct": 0.018,
  "max_concurrent_positions": 2
}
```
- Position: 6% margin (150% exposure with 25x)
- Risk per trade: 2.7% (150% × 1.8% SL)
- With 2 concurrent: 5.4% total risk
- Liquidation buffer: 2.2%

### Moderate (Iterations 4-5)
```json
{
  "max_position_size": 0.09,
  "base_sl_pct": 0.018,
  "max_concurrent_positions": 3
}
```
- Position: 9% margin (225% exposure with 25x)
- Risk per trade: 4.05% (225% × 1.8% SL) - slightly over 3%!
- Better: Use 0.06 position size with 3 concurrent

### Aggressive (Iteration 6)
```json
{
  "max_position_size": 0.06,
  "base_sl_pct": 0.021,
  "max_concurrent_positions": 5
}
```
- Position: 6% margin (150% exposure)
- Risk per trade: 3.15% (150% × 2.1% SL)
- With 5 concurrent: 15.75% max risk (acceptable for 1000X mode)

---

## 🎯 Recommended Configurations

### SAFEST (Recommended for 25x leverage):
```python
leverage = 25
max_position_size = 0.06  # 6% of capital
base_sl_pct = 0.018  # 1.8% stop loss
max_concurrent_positions = 2
max_daily_loss = 0.05  # 5% daily max
```
**Result**: 2.7% risk per trade, 5.4% max concurrent risk

### BALANCED:
```python
leverage = 25
max_position_size = 0.06  # 6% of capital
base_sl_pct = 0.021  # 2.1% stop loss
max_concurrent_positions = 3
max_daily_loss = 0.08  # 8% daily max
```
**Result**: 3.15% risk per trade, 9.45% max concurrent risk

### AGGRESSIVE (1000X Mode):
```python
leverage = 25
max_position_size = 0.06  # 6% of capital
base_sl_pct = 0.024  # 2.4% stop loss (close to liquidation!)
max_concurrent_positions = 5
max_daily_loss = 0.12  # 12% daily max
```
**Result**: 3.6% risk per trade, 18% max concurrent risk

---

## 💡 Key Insights

1. **Don't increase position_size above 6%** with 25x leverage
2. **Keep stop loss below 2.5%** to maintain liquidation buffer
3. **Control risk through concurrent positions** instead of larger sizes
4. **Monitor unrealized PnL** - if position goes 3% against you, consider manual exit
5. **Liquidation is NOT gradual** - you lose EVERYTHING at liquidation

---

## ✅ Updated Risk Formula

```python
def calculate_safe_position_size(
    capital: float,
    leverage: float,
    max_risk_pct: float,
    stop_loss_pct: float
) -> float:
    """
    Calculate safe position size for leverage trading

    Returns: position_size as fraction of capital (margin to use)
    """
    # Maximum dollar risk
    max_risk = capital * max_risk_pct

    # Position value needed to risk max_risk with given SL
    position_value = max_risk / stop_loss_pct

    # Margin required (as fraction of position value)
    margin_required = position_value / leverage

    # Position size as fraction of capital
    position_size = margin_required / capital

    # Safety check: ensure SL is well before liquidation
    liquidation_threshold = 1.0 / leverage
    safety_buffer = 0.01  # 1% minimum buffer

    if stop_loss_pct > (liquidation_threshold - safety_buffer):
        raise ValueError(
            f"Stop loss {stop_loss_pct:.1%} too close to "
            f"liquidation {liquidation_threshold:.1%}!"
        )

    return position_size

# Example
safe_size = calculate_safe_position_size(
    capital=1000,
    leverage=25,
    max_risk_pct=0.03,
    stop_loss_pct=0.02
)
# Returns: 0.06 (6% of capital)
```

---

## 🚨 CRITICAL RULES FOR 25X LEVERAGE

1. ❌ **NEVER** use more than 10% of capital as margin
2. ❌ **NEVER** set stop loss above 3%
3. ❌ **NEVER** let unrealized loss exceed 3%
4. ✅ **ALWAYS** maintain 1.5%+ liquidation buffer
5. ✅ **ALWAYS** use proper stop losses
6. ✅ **MONITOR** positions constantly (liquidation can happen in seconds!)

---

*With great leverage comes great responsibility!* ⚡
