#!/usr/bin/env python3
"""
Production Execution Engine for Live Trading

Handles:
- Order execution with risk checks
- Position tracking and PnL calculation
- Stop loss and take profit management
- Slippage and fee modeling
- Paper trading mode
- State persistence

Risk Management:
- Max position size limits
- Daily loss limits
- Max drawdown stops
- Concurrent position limits
"""

import asyncio
import time
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Order representation"""
    id: str
    symbol: str
    side: OrderSide
    size: float
    price: Optional[float] = None  # None for market orders
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_size: float = 0.0
    timestamp: int = 0
    fill_timestamp: Optional[int] = None


@dataclass
class Position:
    """Position representation"""
    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    entry_timestamp: int = 0

    def update_pnl(self, current_price: float):
        """Update unrealized PnL"""
        self.current_price = current_price

        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
            self.unrealized_pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size
            self.unrealized_pnl_pct = (self.entry_price - current_price) / self.entry_price


class ExecutionEngine:
    """
    Production execution engine with comprehensive risk management
    """

    def __init__(
        self,
        hyperliquid_client,
        initial_capital: float = 10000.0,
        max_position_size: float = 0.3,  # 30% of capital
        max_daily_loss: float = 0.05,  # 5% daily loss limit
        max_drawdown: float = 0.15,  # 15% max drawdown
        max_concurrent_positions: int = 3,
        commission_rate: float = 0.0003,  # 0.03% taker fee
        slippage_bps: float = 2.0,  # 2 bps slippage
        paper_trading: bool = True,
        state_file: str = 'trading_state.json'
    ):
        """
        Initialize execution engine

        Args:
            hyperliquid_client: Hyperliquid API client
            initial_capital: Starting capital
            max_position_size: Max position as fraction of capital
            max_daily_loss: Daily loss limit as fraction
            max_drawdown: Max drawdown as fraction
            max_concurrent_positions: Max number of open positions
            commission_rate: Exchange commission rate
            slippage_bps: Expected slippage in basis points
            paper_trading: If True, simulate orders without real execution
            state_file: File to persist state
        """
        self.client = hyperliquid_client
        self.initial_capital = initial_capital
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.max_concurrent_positions = max_concurrent_positions
        self.commission_rate = commission_rate
        self.slippage_bps = slippage_bps / 10000  # Convert to decimal
        self.paper_trading = paper_trading
        self.state_file = Path(state_file)

        # State
        self.capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.closed_positions: List[Dict] = []

        # Performance tracking
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        self.peak_capital = initial_capital
        self.daily_reset_time = 0

        # Load state if exists
        self._load_state()

        logger.info(
            f"Initialized ExecutionEngine (capital=${initial_capital}, "
            f"paper={paper_trading})"
        )

    def _load_state(self):
        """Load state from file"""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)

            self.capital = state.get('capital', self.initial_capital)
            self.total_pnl = state.get('total_pnl', 0.0)
            self.peak_capital = state.get('peak_capital', self.initial_capital)

            # Restore positions
            for pos_dict in state.get('positions', []):
                pos = Position(**pos_dict)
                self.positions[pos.symbol] = pos

            logger.info(f"Loaded state: capital=${self.capital:.2f}, positions={len(self.positions)}")
        except Exception as e:
            logger.error(f"Error loading state: {e}", exc_info=True)

    def _save_state(self):
        """Save state to file"""
        try:
            state = {
                'capital': self.capital,
                'total_pnl': self.total_pnl,
                'peak_capital': self.peak_capital,
                'positions': [asdict(pos) for pos in self.positions.values()],
                'timestamp': int(time.time() * 1000)
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving state: {e}", exc_info=True)

    def check_risk_limits(self, symbol: str, size: float) -> Tuple[bool, Optional[str]]:
        """
        Check if order passes risk limits

        Returns:
            (allowed, reason): allowed=True if OK, reason if rejected
        """
        # Check concurrent positions
        if len(self.positions) >= self.max_concurrent_positions:
            return False, f"Max concurrent positions ({self.max_concurrent_positions}) reached"

        # Check daily loss
        current_time = time.time()
        if current_time - self.daily_reset_time > 86400:  # 24 hours
            self.daily_pnl = 0.0
            self.daily_reset_time = current_time

        if self.daily_pnl < -self.max_daily_loss * self.initial_capital:
            return False, f"Daily loss limit reached (${abs(self.daily_pnl):.2f})"

        # Check max drawdown
        current_capital = self.capital + sum(p.unrealized_pnl for p in self.positions.values())
        drawdown = (self.peak_capital - current_capital) / self.peak_capital

        if drawdown > self.max_drawdown:
            return False, f"Max drawdown exceeded ({drawdown:.2%})"

        # Check position size
        position_value = size  # Approximate
        if position_value > self.capital * self.max_position_size:
            return False, f"Position size exceeds limit ({self.max_position_size:.1%} of capital)"

        return True, None

    async def execute_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        current_price: Optional[float] = None
    ) -> Optional[Order]:
        """
        Execute market order with risk checks

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            size: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
            current_price: Current market price (for paper trading)

        Returns:
            Order object if successful, None if rejected
        """
        # Risk checks
        allowed, reason = self.check_risk_limits(symbol, size)
        if not allowed:
            logger.warning(f"Order rejected: {reason}")
            return None

        # Create order
        order = Order(
            id=f"order_{int(time.time() * 1000)}",
            symbol=symbol,
            side=side,
            size=size,
            status=OrderStatus.PENDING,
            timestamp=int(time.time() * 1000)
        )

        self.orders[order.id] = order

        try:
            if self.paper_trading:
                # Paper trading: simulate execution
                if current_price is None:
                    logger.error("Paper trading requires current_price")
                    order.status = OrderStatus.REJECTED
                    return None

                # Simulate slippage
                if side == OrderSide.BUY:
                    fill_price = current_price * (1 + self.slippage_bps)
                else:
                    fill_price = current_price * (1 - self.slippage_bps)

                # Fill order
                order.filled_price = fill_price
                order.filled_size = size
                order.status = OrderStatus.FILLED
                order.fill_timestamp = int(time.time() * 1000)

                logger.info(f"Paper order filled: {side.value} {size} {symbol} @ ${fill_price:.2f}")

            else:
                # Real trading
                result = await self._execute_real_order(symbol, side, size)
                if not result:
                    order.status = OrderStatus.REJECTED
                    return None

                order.filled_price = result['price']
                order.filled_size = result['size']
                order.status = OrderStatus.FILLED
                order.fill_timestamp = int(time.time() * 1000)

            # Create position
            position = Position(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=order.filled_price,
                current_price=order.filled_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                entry_timestamp=order.fill_timestamp
            )

            self.positions[symbol] = position

            # Deduct commission
            commission = order.filled_price * size * self.commission_rate
            self.capital -= commission
            self.daily_pnl -= commission

            # Save state
            self._save_state()

            logger.info(
                f"Position opened: {side.value} {size} {symbol} @ ${order.filled_price:.2f} "
                f"(SL=${stop_loss}, TP=${take_profit})"
            )

            return order

        except Exception as e:
            logger.error(f"Error executing order: {e}", exc_info=True)
            order.status = OrderStatus.REJECTED
            return None

    async def _execute_real_order(self, symbol: str, side: OrderSide, size: float) -> Optional[Dict]:
        """Execute real order via Hyperliquid API"""
        try:
            if not hasattr(self.client, 'enabled') or not self.client.enabled:
                logger.error("Hyperliquid client not enabled")
                return None

            # Place market order
            is_buy = (side == OrderSide.BUY)
            result = self.client.market_order(symbol, is_buy, size)

            if result and 'status' in result and result['status'] == 'ok':
                return {
                    'price': result.get('filled_price', 0.0),
                    'size': size
                }

            return None

        except Exception as e:
            logger.error(f"Error in real order execution: {e}", exc_info=True)
            return None

    async def update_positions(self, current_prices: Dict[str, float]):
        """
        Update positions with current prices and check SL/TP

        Args:
            current_prices: Dict of symbol -> current_price
        """
        positions_to_close = []

        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            position.update_pnl(current_price)

            # Check stop loss
            if position.stop_loss:
                if position.side == OrderSide.BUY and current_price <= position.stop_loss:
                    logger.warning(f"Stop loss hit for {symbol}: ${current_price:.2f} <= ${position.stop_loss:.2f}")
                    positions_to_close.append((symbol, "stop_loss"))
                elif position.side == OrderSide.SELL and current_price >= position.stop_loss:
                    logger.warning(f"Stop loss hit for {symbol}: ${current_price:.2f} >= ${position.stop_loss:.2f}")
                    positions_to_close.append((symbol, "stop_loss"))

            # Check take profit
            if position.take_profit:
                if position.side == OrderSide.BUY and current_price >= position.take_profit:
                    logger.info(f"Take profit hit for {symbol}: ${current_price:.2f} >= ${position.take_profit:.2f}")
                    positions_to_close.append((symbol, "take_profit"))
                elif position.side == OrderSide.SELL and current_price <= position.take_profit:
                    logger.info(f"Take profit hit for {symbol}: ${current_price:.2f} <= ${position.take_profit:.2f}")
                    positions_to_close.append((symbol, "take_profit"))

        # Close positions
        for symbol, reason in positions_to_close:
            await self.close_position(symbol, reason=reason)

        # Update peak capital
        current_capital = self.capital + sum(p.unrealized_pnl for p in self.positions.values())
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital

    async def close_position(self, symbol: str, reason: str = "manual") -> bool:
        """
        Close position

        Args:
            symbol: Symbol to close
            reason: Reason for closing

        Returns:
            True if successful
        """
        if symbol not in self.positions:
            logger.warning(f"No position to close for {symbol}")
            return False

        position = self.positions[symbol]

        try:
            # Reverse side for closing
            close_side = OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY

            # Execute close order
            order = await self.execute_order(
                symbol=symbol,
                side=close_side,
                size=position.size,
                current_price=position.current_price
            )

            if not order or order.status != OrderStatus.FILLED:
                logger.error(f"Failed to close position for {symbol}")
                return False

            # Calculate realized PnL
            realized_pnl = position.unrealized_pnl
            self.capital += realized_pnl
            self.total_pnl += realized_pnl
            self.daily_pnl += realized_pnl

            # Store closed position
            self.closed_positions.append({
                'symbol': symbol,
                'side': position.side.value,
                'size': position.size,
                'entry_price': position.entry_price,
                'exit_price': position.current_price,
                'pnl': realized_pnl,
                'pnl_pct': position.unrealized_pnl_pct,
                'entry_timestamp': position.entry_timestamp,
                'exit_timestamp': int(time.time() * 1000),
                'reason': reason
            })

            # Remove position
            del self.positions[symbol]

            # Save state
            self._save_state()

            logger.info(
                f"Position closed: {symbol} PnL=${realized_pnl:.2f} ({position.unrealized_pnl_pct:.2%}) - {reason}"
            )

            return True

        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)
            return False

    def get_status(self) -> Dict:
        """Get current status"""
        total_position_value = sum(
            p.entry_price * p.size for p in self.positions.values()
        )
        unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        current_capital = self.capital + unrealized_pnl

        return {
            'capital': self.capital,
            'current_capital': current_capital,
            'total_pnl': self.total_pnl,
            'unrealized_pnl': unrealized_pnl,
            'daily_pnl': self.daily_pnl,
            'num_positions': len(self.positions),
            'total_position_value': total_position_value,
            'num_closed_trades': len(self.closed_positions),
            'peak_capital': self.peak_capital,
            'drawdown': (self.peak_capital - current_capital) / self.peak_capital,
            'paper_trading': self.paper_trading
        }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Test with paper trading
    async def test():
        engine = ExecutionEngine(
            hyperliquid_client=None,
            paper_trading=True,
            initial_capital=10000
        )

        # Execute buy order
        order = await engine.execute_order(
            symbol='ETH',
            side=OrderSide.BUY,
            size=0.1,
            current_price=4000.0,
            stop_loss=3900.0,
            take_profit=4200.0
        )

        print(f"\nOrder: {order}")
        print(f"Status: {engine.get_status()}")

        # Update with new price
        await engine.update_positions({'ETH': 4100.0})
        print(f"\nAfter price update: {engine.get_status()}")

        # Close position
        await engine.close_position('ETH', reason='test')
        print(f"\nAfter close: {engine.get_status()}")

    asyncio.run(test())
