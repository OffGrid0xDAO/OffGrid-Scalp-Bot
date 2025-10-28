#!/usr/bin/env python3
"""
Adaptive Take Profit / Stop Loss System

Dynamically calculates TP/SL based on:
- Signal strength & confidence
- Market regime (trending/volatile/stable)
- Fibonacci levels
- ATR (Average True Range)
- Multi-timeframe coherence
- Historical win rate
- Risk-reward optimization

Production-ready with:
- Real-time adaptation
- Fibonacci-based profit targets
- Regime-specific stop losses
- Dynamic risk-reward ratios
"""

import numpy as np
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TPSLStrategy(Enum):
    """TP/SL calculation strategy"""
    FIXED = "fixed"                    # Fixed percentage
    FIBONACCI = "fibonacci"            # Fibonacci levels
    ATR_BASED = "atr_based"           # ATR multiples
    ADAPTIVE = "adaptive"              # Full adaptive (recommended)


@dataclass
class TPSLLevels:
    """Take profit and stop loss levels"""
    stop_loss: float
    take_profit: float
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float
    strategy_used: str
    confidence_adjusted: bool


class AdaptiveTPSL:
    """
    Adaptive Take Profit / Stop Loss Calculator

    Dynamically adjusts TP/SL based on market conditions and signal quality
    """

    # Fibonacci retracement/extension levels
    FIBONACCI_LEVELS = {
        'retracement': [0.236, 0.382, 0.5, 0.618, 0.786],
        'extension': [1.0, 1.272, 1.618, 2.0, 2.618]
    }

    # Risk-reward ratios by regime
    REGIME_RR_RATIOS = {
        'trending': 2.5,      # Higher RR in trends
        'volatile': 1.5,      # Lower RR in volatility
        'stable': 2.0,        # Moderate RR
        'mean_reverting': 1.8
    }

    def __init__(
        self,
        base_sl_pct: float = 0.02,       # 2% base stop loss
        min_rr_ratio: float = 1.5,       # Minimum risk-reward
        max_rr_ratio: float = 4.0,       # Maximum risk-reward
        use_fibonacci: bool = True,
        use_atr: bool = True,
        atr_period: int = 14
    ):
        """
        Initialize adaptive TP/SL calculator

        Args:
            base_sl_pct: Base stop loss percentage
            min_rr_ratio: Minimum risk-reward ratio
            max_rr_ratio: Maximum risk-reward ratio
            use_fibonacci: Use Fibonacci levels
            use_atr: Use ATR for volatility adjustment
            atr_period: ATR calculation period
        """
        self.base_sl_pct = base_sl_pct
        self.min_rr_ratio = min_rr_ratio
        self.max_rr_ratio = max_rr_ratio
        self.use_fibonacci = use_fibonacci
        self.use_atr = use_atr
        self.atr_period = atr_period

        # Track recent win rate for adaptation
        self.recent_trades = []
        self.max_trade_history = 50

        logger.info(
            f"Initialized AdaptiveTPSL (base_sl={base_sl_pct:.2%}, "
            f"rr_range={min_rr_ratio:.1f}-{max_rr_ratio:.1f})"
        )

    def calculate(
        self,
        entry_price: float,
        side: str,  # 'buy' or 'sell'
        signal_confidence: float,
        signal_strength: float,
        coherence: float,
        regime: str,
        current_atr: Optional[float] = None,
        price_history: Optional[np.ndarray] = None
    ) -> TPSLLevels:
        """
        Calculate adaptive TP/SL levels

        Args:
            entry_price: Entry price
            side: 'buy' or 'sell'
            signal_confidence: Signal confidence [0, 1]
            signal_strength: Signal strength [0, 1]
            coherence: Multi-timeframe coherence [0, 1]
            regime: Market regime
            current_atr: Current ATR value (optional)
            price_history: Recent price history for calculations

        Returns:
            TPSLLevels with calculated levels
        """
        is_long = (side.lower() == 'buy')

        # 1. Calculate base stop loss
        base_sl = self._calculate_base_stop_loss(
            entry_price=entry_price,
            regime=regime,
            signal_confidence=signal_confidence,
            current_atr=current_atr
        )

        # 2. Calculate optimal risk-reward ratio
        rr_ratio = self._calculate_risk_reward_ratio(
            signal_confidence=signal_confidence,
            signal_strength=signal_strength,
            coherence=coherence,
            regime=regime
        )

        # 3. Calculate take profit
        base_tp = base_sl * rr_ratio

        # 4. Apply Fibonacci adjustment if enabled
        if self.use_fibonacci:
            base_sl, base_tp = self._apply_fibonacci_levels(
                entry_price=entry_price,
                base_sl=base_sl,
                base_tp=base_tp,
                is_long=is_long,
                price_history=price_history
            )

        # 5. Calculate actual price levels
        if is_long:
            stop_loss_price = entry_price * (1 - base_sl)
            take_profit_price = entry_price * (1 + base_tp)
        else:
            stop_loss_price = entry_price * (1 + base_sl)
            take_profit_price = entry_price * (1 - base_tp)

        # Calculate amounts
        risk_amount = abs(entry_price - stop_loss_price)
        reward_amount = abs(take_profit_price - entry_price)
        actual_rr = reward_amount / risk_amount if risk_amount > 0 else 0

        levels = TPSLLevels(
            stop_loss=stop_loss_price,
            take_profit=take_profit_price,
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            risk_reward_ratio=actual_rr,
            strategy_used='adaptive',
            confidence_adjusted=True
        )

        logger.debug(
            f"Adaptive TP/SL: Entry=${entry_price:.2f}, "
            f"SL=${stop_loss_price:.2f} ({base_sl:.2%}), "
            f"TP=${take_profit_price:.2f} ({base_tp:.2%}), "
            f"RR={actual_rr:.2f}"
        )

        return levels

    def _calculate_base_stop_loss(
        self,
        entry_price: float,
        regime: str,
        signal_confidence: float,
        current_atr: Optional[float] = None
    ) -> float:
        """
        Calculate base stop loss percentage

        Factors:
        - Market regime (wider in volatile markets)
        - Signal confidence (tighter with high confidence)
        - ATR (volatility-adjusted)
        """
        # Start with base
        sl = self.base_sl_pct

        # Adjust for regime
        regime_multipliers = {
            'stable': 0.5,         # Tight SL in stable markets
            'mean_reverting': 0.7,
            'trending': 1.0,       # Normal SL in trends
            'volatile': 1.5        # Wide SL in volatility
        }
        sl *= regime_multipliers.get(regime, 1.0)

        # Adjust for confidence (higher confidence = tighter SL)
        confidence_factor = 1.5 - signal_confidence  # 0.5 to 1.5
        sl *= confidence_factor

        # ATR adjustment if available
        if self.use_atr and current_atr is not None and current_atr > 0:
            atr_pct = current_atr / entry_price
            # Use ATR as floor (don't go tighter than 1.5x ATR)
            min_sl = atr_pct * 1.5
            sl = max(sl, min_sl)

        # Bounds check
        sl = np.clip(sl, 0.005, 0.05)  # 0.5% to 5%

        return sl

    def _calculate_risk_reward_ratio(
        self,
        signal_confidence: float,
        signal_strength: float,
        coherence: float,
        regime: str
    ) -> float:
        """
        Calculate optimal risk-reward ratio

        Higher quality signals deserve higher RR ratios
        """
        # Base RR from regime
        base_rr = self.REGIME_RR_RATIOS.get(regime, 2.0)

        # Quality score from signal metrics
        quality_score = (
            signal_confidence * 0.4 +
            signal_strength * 0.3 +
            coherence * 0.3
        )

        # Adjust RR based on quality
        # High quality (0.8-1.0) → increase RR by up to 50%
        # Low quality (0.5-0.8) → decrease RR
        quality_multiplier = 0.5 + quality_score

        rr = base_rr * quality_multiplier

        # Consider recent win rate
        if len(self.recent_trades) >= 10:
            win_rate = np.mean(self.recent_trades)
            # If win rate high, can be more aggressive
            if win_rate > 0.75:
                rr *= 1.2
            elif win_rate < 0.5:
                rr *= 0.8

        # Bounds
        rr = np.clip(rr, self.min_rr_ratio, self.max_rr_ratio)

        return rr

    def _apply_fibonacci_levels(
        self,
        entry_price: float,
        base_sl: float,
        base_tp: float,
        is_long: bool,
        price_history: Optional[np.ndarray] = None
    ) -> Tuple[float, float]:
        """
        Adjust TP/SL to align with Fibonacci levels

        If price history available, calculates swing high/low and
        places TP at Fibonacci extension levels
        """
        if price_history is None or len(price_history) < 50:
            return base_sl, base_tp

        # Find recent swing high and low
        lookback = min(100, len(price_history))
        recent_prices = price_history[-lookback:]

        swing_high = np.max(recent_prices)
        swing_low = np.min(recent_prices)
        swing_range = swing_high - swing_low

        if swing_range == 0:
            return base_sl, base_tp

        # Calculate Fibonacci levels from swing
        fib_levels = {}

        if is_long:
            # For longs, TP at Fibonacci extensions above entry
            for level in self.FIBONACCI_LEVELS['extension']:
                fib_price = swing_low + (swing_range * level)
                fib_levels[level] = fib_price

            # Find closest Fibonacci level to our target TP
            target_tp_price = entry_price * (1 + base_tp)
            closest_fib = min(
                [lv for lv in fib_levels.values() if lv > entry_price],
                key=lambda x: abs(x - target_tp_price),
                default=target_tp_price
            )

            # Adjust TP to Fibonacci level if within 20% of target
            if abs(closest_fib - target_tp_price) / target_tp_price < 0.2:
                adjusted_tp = (closest_fib - entry_price) / entry_price
                logger.debug(f"TP adjusted to Fibonacci level: {closest_fib:.2f}")
                return base_sl, adjusted_tp

        else:
            # For shorts, TP at Fibonacci extensions below entry
            for level in self.FIBONACCI_LEVELS['extension']:
                fib_price = swing_high - (swing_range * level)
                fib_levels[level] = fib_price

            target_tp_price = entry_price * (1 - base_tp)
            closest_fib = min(
                [lv for lv in fib_levels.values() if lv < entry_price],
                key=lambda x: abs(x - target_tp_price),
                default=target_tp_price
            )

            if abs(closest_fib - target_tp_price) / target_tp_price < 0.2:
                adjusted_tp = (entry_price - closest_fib) / entry_price
                logger.debug(f"TP adjusted to Fibonacci level: {closest_fib:.2f}")
                return base_sl, adjusted_tp

        return base_sl, base_tp

    def record_trade_result(self, won: bool):
        """Record trade result for adaptive learning"""
        self.recent_trades.append(1.0 if won else 0.0)
        if len(self.recent_trades) > self.max_trade_history:
            self.recent_trades.pop(0)

    def get_current_win_rate(self) -> float:
        """Get current win rate"""
        if not self.recent_trades:
            return 0.5
        return np.mean(self.recent_trades)

    def get_stats(self) -> Dict:
        """Get statistics"""
        return {
            'recent_win_rate': self.get_current_win_rate(),
            'num_trades_tracked': len(self.recent_trades),
            'base_sl_pct': self.base_sl_pct,
            'min_rr_ratio': self.min_rr_ratio,
            'max_rr_ratio': self.max_rr_ratio
        }


# Testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # Create adaptive TP/SL calculator
    tpsl = AdaptiveTPSL(
        base_sl_pct=0.02,
        min_rr_ratio=1.5,
        max_rr_ratio=4.0,
        use_fibonacci=True
    )

    # Test scenario 1: High quality signal in trending market
    print("\n" + "="*60)
    print("Scenario 1: High Quality Signal (Trending Market)")
    print("="*60)

    levels = tpsl.calculate(
        entry_price=4000.0,
        side='buy',
        signal_confidence=0.85,
        signal_strength=0.80,
        coherence=0.75,
        regime='trending',
        current_atr=50.0
    )

    print(f"Entry: $4000.00")
    print(f"Stop Loss: ${levels.stop_loss:.2f} (${levels.risk_amount:.2f} risk)")
    print(f"Take Profit: ${levels.take_profit:.2f} (${levels.reward_amount:.2f} reward)")
    print(f"Risk-Reward: {levels.risk_reward_ratio:.2f}")

    # Test scenario 2: Lower quality signal in volatile market
    print("\n" + "="*60)
    print("Scenario 2: Lower Quality Signal (Volatile Market)")
    print("="*60)

    levels = tpsl.calculate(
        entry_price=4000.0,
        side='buy',
        signal_confidence=0.60,
        signal_strength=0.65,
        coherence=0.55,
        regime='volatile',
        current_atr=80.0
    )

    print(f"Entry: $4000.00")
    print(f"Stop Loss: ${levels.stop_loss:.2f} (${levels.risk_amount:.2f} risk)")
    print(f"Take Profit: ${levels.take_profit:.2f} (${levels.reward_amount:.2f} reward)")
    print(f"Risk-Reward: {levels.risk_reward_ratio:.2f}")

    # Test scenario 3: Excellent signal in stable market
    print("\n" + "="*60)
    print("Scenario 3: Excellent Signal (Stable Market)")
    print("="*60)

    levels = tpsl.calculate(
        entry_price=4000.0,
        side='buy',
        signal_confidence=0.95,
        signal_strength=0.90,
        coherence=0.88,
        regime='stable',
        current_atr=30.0
    )

    print(f"Entry: $4000.00")
    print(f"Stop Loss: ${levels.stop_loss:.2f} (${levels.risk_amount:.2f} risk)")
    print(f"Take Profit: ${levels.take_profit:.2f} (${levels.reward_amount:.2f} reward)")
    print(f"Risk-Reward: {levels.risk_reward_ratio:.2f}")

    print("\n" + "="*60)
    print("Win Rate Adaptation Test")
    print("="*60)

    # Simulate trades
    for i in range(10):
        tpsl.record_trade_result(i % 5 != 0)  # 80% win rate

    print(f"Current win rate: {tpsl.get_current_win_rate():.1%}")
    print(f"Stats: {tpsl.get_stats()}")
