#!/usr/bin/env python3
"""
Production Trading Orchestrator - The Brain

Orchestrates the entire live trading pipeline:
1. RealtimeDataEngine → Receives WebSocket ticks from Hyperliquid
2. AdaptiveKalmanFilter → Filters price data, detects regime
3. Fourier/Fibonacci Strategies → Generate signals from clean data
4. SignalFusionEngine → Fuses multi-TF signals with constructive interference
5. ExecutionEngine → Executes trades with risk management
6. TelegramBot → Sends notifications

Production-ready:
- Sub-100ms latency pipeline
- Graceful error handling
- Automatic reconnection
- State persistence
- Circuit breakers
- Performance monitoring
"""

import asyncio
import time
import logging
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import json
import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.live.realtime_data_engine import RealtimeDataEngine, Candle
from src.live.adaptive_kalman_filter import MultiTimeframeKalman
from src.live.signal_fusion_engine import SignalFusionEngine, Signal, SignalType
from src.live.execution_engine import ExecutionEngine, OrderSide
from src.live.adaptive_tp_sl import AdaptiveTPSL
from src.live.fibonacci_signal_generator import FibonacciSignalGenerator
from src.exchange.hyperliquid_client import HyperliquidClient
from src.exchange.hyperliquid_websocket import HyperliquidDataStream
from src.notifications.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    """
    Main orchestrator for production trading system

    Connects all components and manages the trading pipeline
    """

    def __init__(
        self,
        symbol: str = 'ETH',
        initial_capital: float = 10000.0,
        max_position_size: float = 0.3,
        enable_telegram: bool = True,
        live_trading: bool = False,
        # Iteration parameters
        compression_threshold: float = 80,
        alignment_threshold: float = 80,
        confluence_threshold: float = 55,
        n_harmonics: int = 5,
        max_holding_periods: int = 24,
        min_confidence: float = 0.65,
        min_coherence: float = 0.6,
        # ENHANCED features (Iterations 4-6)
        use_volume_fft: bool = True,
        use_fib_levels: bool = True,
        volume_confirmation_weight: float = 0.15,
        fib_level_weight: float = 0.1
    ):
        """
        Initialize trading orchestrator

        Args:
            symbol: Trading symbol
            initial_capital: Starting capital
            max_position_size: Max position as fraction of capital
            enable_telegram: Enable Telegram notifications
            live_trading: If False, paper trade. If True, LIVE TRADING!
            compression_threshold: Fibonacci compression threshold (70-95)
            alignment_threshold: Fibonacci alignment threshold (70-95)
            confluence_threshold: Fibonacci confluence threshold (55-80)
            n_harmonics: FFT harmonics (3-10)
            max_holding_periods: Max holding periods (12-48)
            min_confidence: Minimum signal confidence (0.5-0.8)
            min_coherence: Minimum signal coherence (0.5-0.8)
            use_volume_fft: Apply FFT to volume for momentum detection
            use_fib_levels: Use Fibonacci price levels for entry/exit
            volume_confirmation_weight: Weight of volume signal (0.0-0.3)
            fib_level_weight: Weight of Fibonacci level proximity (0.0-0.2)
        """
        self.symbol = symbol
        self.enable_telegram = enable_telegram
        self.live_trading = live_trading

        # Store iteration parameters
        self.compression_threshold = compression_threshold
        self.alignment_threshold = alignment_threshold
        self.confluence_threshold = confluence_threshold
        self.n_harmonics = n_harmonics
        self.max_holding_periods = max_holding_periods

        # Store ENHANCED features
        self.use_volume_fft = use_volume_fft
        self.use_fib_levels = use_fib_levels
        self.volume_confirmation_weight = volume_confirmation_weight
        self.fib_level_weight = fib_level_weight

        # Initialize Hyperliquid client
        logger.info("Initializing Hyperliquid client...")
        self.hyperliquid = HyperliquidClient()

        # Fetch actual wallet balance if live trading
        if live_trading and self.hyperliquid.enabled:
            try:
                actual_balance = self.hyperliquid.get_balance()
                logger.info(f"📊 Fetched wallet balance: ${actual_balance:,.2f}")
                if actual_balance > 0:
                    initial_capital = actual_balance
                    logger.info(f"✅ Using actual wallet balance for position sizing")
                else:
                    logger.warning(f"⚠️  Wallet balance is $0, using configured capital ${initial_capital:,.2f}")
            except Exception as e:
                logger.warning(f"⚠️  Could not fetch wallet balance: {e}")
                logger.warning(f"   Using configured capital ${initial_capital:,.2f}")

        self.initial_capital = initial_capital

        # Initialize WebSocket data stream
        logger.info("Initializing WebSocket data stream...")
        self.data_stream = HyperliquidDataStream(testnet=False)

        # Initialize data engine
        logger.info("Initializing real-time data engine...")
        self.data_engine = RealtimeDataEngine(
            symbol=symbol,
            buffer_size=5000,
            enable_validation=True
        )

        # Bootstrap with historical data so we don't need to wait 17 hours
        logger.info("Loading historical data for immediate signal generation...")
        try:
            self.data_engine.bootstrap_from_historical_data('trading_data/indicators')
        except Exception as e:
            logger.warning(f"Could not load historical data: {e}")

        # Initialize Kalman filters for all timeframes
        logger.info("Initializing adaptive Kalman filters...")
        self.kalman = MultiTimeframeKalman(
            timeframes=['1m', '5m', '15m', '30m', '1h']
        )

        # Initialize signal fusion engine
        logger.info("Initializing signal fusion engine...")
        self.signal_fusion = SignalFusionEngine(
            min_confidence=min_confidence,
            min_coherence=min_coherence,
            enable_modulation=True
        )

        # Initialize execution engine
        logger.info("Initializing execution engine...")
        self.execution = ExecutionEngine(
            hyperliquid_client=self.hyperliquid,
            initial_capital=initial_capital,
            max_position_size=max_position_size,
            max_daily_loss=0.05,
            max_drawdown=0.15,
            max_concurrent_positions=3,
            paper_trading=not live_trading,
            state_file='trading_state.json'
        )

        # Initialize Fibonacci + FFT signal generator with ENHANCED features
        logger.info("Initializing ENHANCED Fibonacci + FFT signal generator...")
        self.fibonacci = FibonacciSignalGenerator(
            compression_threshold=compression_threshold,
            alignment_threshold=alignment_threshold,
            confluence_threshold=confluence_threshold,
            n_harmonics=n_harmonics,
            max_holding_periods=max_holding_periods,
            use_volume_fft=self.use_volume_fft,
            use_fib_levels=self.use_fib_levels,
            volume_confirmation_weight=self.volume_confirmation_weight,
            fib_level_weight=self.fib_level_weight
        )
        logger.info(
            f"✅ ENHANCED Fibonacci generator ready:\n"
            f"   Compression: {compression_threshold}, "
            f"Alignment: {alignment_threshold}, "
            f"Confluence: {confluence_threshold}\n"
            f"   Volume FFT: {'Enabled' if self.use_volume_fft else 'Disabled'}\n"
            f"   Fib Levels: {'Enabled' if self.use_fib_levels else 'Disabled'}"
        )

        # Initialize Adaptive TP/SL calculator
        logger.info("Initializing adaptive TP/SL calculator...")
        self.adaptive_tpsl = AdaptiveTPSL(
            base_sl_pct=0.02,
            min_rr_ratio=1.5,
            max_rr_ratio=4.0,
            use_fibonacci=True,
            use_atr=True
        )

        # Initialize Telegram bot
        self.telegram = None
        if enable_telegram:
            try:
                logger.info("Initializing Telegram bot...")
                self.telegram = TelegramBot()
            except Exception as e:
                logger.warning(f"Telegram initialization failed: {e}")

        # State
        self.is_running = False
        self.last_signal_time = {}
        self.signal_cooldown = 60000  # 1 minute cooldown between signals

        # Performance tracking
        self.pipeline_latencies = []
        self.total_signals_generated = 0
        self.total_trades_executed = 0

        # Register callbacks
        self._register_callbacks()

        mode = "🔴 LIVE TRADING" if live_trading else "📄 PAPER TRADING"
        logger.info(f"\n{'='*60}")
        logger.info(f"Trading Orchestrator Initialized - {mode}")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")
        logger.info(f"Max Position Size: {max_position_size:.1%}")
        logger.info(f"Telegram: {'Enabled' if enable_telegram else 'Disabled'}")
        logger.info(f"{'='*60}\n")

    def _register_callbacks(self):
        """Register callbacks for new candles on each timeframe"""
        for tf in ['1m', '5m', '15m', '30m', '1h']:
            self.data_engine.register_callback(tf, self._on_new_candle)

    async def _send_telegram_startup(self):
        """Send startup notification"""
        if not self.telegram:
            return

        mode = "🔴 LIVE TRADING" if self.live_trading else "📄 Paper Trading"
        message = (
            f"🚀 **Trading Bot Started**\n\n"
            f"Mode: {mode}\n"
            f"Symbol: {self.symbol}\n"
            f"Capital: ${self.initial_capital:,.2f}\n"
            f"Max Position: {self.execution.max_position_size:.1%}\n"
            f"Max Daily Loss: {self.execution.max_daily_loss:.1%}\n"
            f"Max Drawdown: {self.execution.max_drawdown:.1%}\n\n"
            f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            if asyncio.iscoroutinefunction(self.telegram.send_message):
                await self.telegram.send_message(message)
            else:
                self.telegram.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send Telegram startup message: {e}")

    async def _on_new_candle(self, candle: Candle, df: pd.DataFrame):
        """
        Called when a new candle is finalized

        This is the main trading pipeline entry point
        """
        start_time = time.time()

        try:
            # Get timeframe from candle interval
            timeframe = self._detect_timeframe(candle, df)

            logger.debug(f"New {timeframe} candle: {candle.close:.2f}")

            # Update Kalman filter for this timeframe
            kalman_state = self.kalman.update(timeframe, candle.close)

            # Only generate trading signals on 5m timeframe
            if timeframe == '5m' and len(df) >= 200:
                await self._generate_and_execute_signal(candle, df, kalman_state)

            # Track latency
            latency_ms = (time.time() - start_time) * 1000
            self.pipeline_latencies.append(latency_ms)
            if len(self.pipeline_latencies) > 1000:
                self.pipeline_latencies.pop(0)

            if latency_ms > 100:
                logger.warning(f"Pipeline latency HIGH: {latency_ms:.2f}ms")

        except Exception as e:
            logger.error(f"Error in candle callback: {e}", exc_info=True)

    def _detect_timeframe(self, candle: Candle, df: pd.DataFrame) -> str:
        """Detect timeframe from candle timestamps"""
        if len(df) < 2:
            return '1m'

        interval_ms = df.index[-1].timestamp() * 1000 - df.index[-2].timestamp() * 1000
        interval_minutes = interval_ms / 60000

        if interval_minutes <= 1:
            return '1m'
        elif interval_minutes <= 5:
            return '5m'
        elif interval_minutes <= 15:
            return '15m'
        elif interval_minutes <= 30:
            return '30m'
        elif interval_minutes <= 60:
            return '1h'
        else:
            return '4h'

    async def _generate_and_execute_signal(self, candle: Candle, df: pd.DataFrame, kalman_state):
        """
        Generate trading signal and execute if conditions met

        Pipeline:
        1. Get Fourier signal from price data
        2. Get Kalman filter signal
        3. Fuse signals across timeframes
        4. Execute if confidence high enough
        """
        try:
            # Check cooldown
            current_time = candle.timestamp
            last_signal = self.last_signal_time.get(self.symbol, 0)
            if current_time - last_signal < self.signal_cooldown:
                logger.debug(f"Signal cooldown active (last: {(current_time - last_signal)/1000:.1f}s ago)")
                return

            # Get current regime from Kalman
            regime = self.kalman.filters['5m'].get_regime()
            logger.debug(f"Current regime: {regime}")

            # Collect signals from all sources
            signals = []

            # 1. Fourier signal (from FFT-filtered price data)
            try:
                fourier_signal = self._generate_fourier_signal(df, candle.timestamp)
                if fourier_signal:
                    signals.append(fourier_signal)
                    logger.debug(f"Fourier signal: {fourier_signal.signal_type.name} (strength={fourier_signal.strength:.2f})")
            except Exception as e:
                logger.error(f"Fourier signal generation failed: {e}")

            # 2. Kalman filter signals (multi-timeframe)
            try:
                kalman_signals = self._generate_kalman_signals(candle.timestamp)
                signals.extend(kalman_signals)
                logger.debug(f"Kalman signals: {len(kalman_signals)} timeframes")
            except Exception as e:
                logger.error(f"Kalman signal generation failed: {e}")

            # 3. Get signals from other timeframes
            for tf in ['15m', '30m']:
                tf_df = self.data_engine.get_dataframe(tf, n_candles=200)
                if len(tf_df) >= 50:
                    try:
                        tf_signal = self._generate_fourier_signal(tf_df, candle.timestamp, timeframe=tf)
                        if tf_signal:
                            signals.append(tf_signal)
                    except Exception as e:
                        logger.error(f"Signal generation for {tf} failed: {e}")

            if not signals:
                logger.debug("No signals generated")
                return

            # Fuse signals
            fused = self.signal_fusion.fuse_signals(signals, current_regime=regime)

            if not fused:
                logger.debug("Signal fusion returned NEUTRAL")
                return

            if fused.signal_type == SignalType.NEUTRAL:
                logger.debug(f"Fused signal is NEUTRAL (confidence={fused.confidence:.2f}, coherence={fused.coherence:.2f})")
                return

            self.total_signals_generated += 1

            logger.info(
                f"🎯 FUSED SIGNAL: {fused.signal_type.name} | "
                f"Strength: {fused.strength:.2f} | "
                f"Confidence: {fused.confidence:.2f} | "
                f"Coherence: {fused.coherence:.2f} | "
                f"Position Size: {fused.max_position_size:.1%} | "
                f"SL: {fused.recommended_stop_loss:.2%}"
            )

            # Execute trade
            await self._execute_fused_signal(fused, candle.close)

            # Update last signal time
            self.last_signal_time[self.symbol] = current_time

        except Exception as e:
            logger.error(f"Error in signal generation/execution: {e}", exc_info=True)

    def _generate_fourier_signal(self, df: pd.DataFrame, timestamp: int, timeframe: str = '5m') -> Optional[Signal]:
        """Generate signal from Fibonacci + FFT analysis"""
        try:
            if len(df) < 200:
                logger.debug(f"Not enough data for Fibonacci analysis: {len(df)} < 200")
                return None

            # Use Fibonacci signal generator
            fib_signal = self.fibonacci.generate_signal(df)

            if fib_signal is None:
                return None

            # Convert to Signal object
            signal_type = SignalType.LONG if fib_signal['signal'] == 'LONG' else SignalType.SHORT

            return Signal(
                signal_type=signal_type,
                strength=fib_signal['strength'],
                confidence=fib_signal['confidence'],
                timeframe=timeframe,
                source='fibonacci_fft',
                timestamp=timestamp,
                metadata={
                    'compression': fib_signal['compression'],
                    'alignment': fib_signal['alignment'],
                    'confluence': fib_signal['confluence']
                }
            )

        except Exception as e:
            logger.error(f"Fibonacci signal error: {e}", exc_info=True)
            return None

    def _generate_kalman_signals(self, timestamp: int) -> list:
        """Generate signals from Kalman filters across timeframes"""
        signals = []

        for tf, filt in self.kalman.filters.items():
            try:
                direction = filt.get_trend_direction()
                confidence = filt.state.confidence
                velocity = abs(filt.get_velocity_estimate())

                if direction == 0 or confidence < 0.5:
                    continue

                signal_type = SignalType.LONG if direction > 0 else SignalType.SHORT
                strength = min(velocity * 100, 1.0)  # Scale velocity to [0, 1]

                signals.append(Signal(
                    signal_type=signal_type,
                    strength=strength,
                    confidence=confidence,
                    timeframe=tf,
                    source='kalman',
                    timestamp=timestamp
                ))

            except Exception as e:
                logger.error(f"Kalman signal error for {tf}: {e}")

        return signals

    async def _execute_fused_signal(self, fused_signal, current_price: float):
        """Execute trade based on fused signal"""
        try:
            # Check if we already have a position
            if self.symbol in self.execution.positions:
                logger.info(f"Already have position in {self.symbol}, skipping")
                return

            # Determine order side
            side = OrderSide.BUY if fused_signal.signal_type == SignalType.LONG else OrderSide.SELL

            # Get current regime
            regime = self.kalman.filters['5m'].get_regime()

            # Calculate adaptive TP/SL using all available data
            tp_sl_levels = self.adaptive_tpsl.calculate(
                entry_price=current_price,
                side=side.value,
                signal_confidence=fused_signal.confidence,
                signal_strength=fused_signal.strength,
                coherence=fused_signal.coherence,
                regime=regime,
                current_atr=None,  # Could calculate ATR from price history
                price_history=None  # Could pass recent prices for Fibonacci
            )

            stop_loss = tp_sl_levels.stop_loss
            take_profit = tp_sl_levels.take_profit

            # Calculate position size
            position_value = self.execution.capital * fused_signal.max_position_size
            size = position_value / current_price

            logger.info(
                f"📤 EXECUTING ORDER:\n"
                f"  Side: {side.value}\n"
                f"  Size: {size:.4f}\n"
                f"  Price: ${current_price:.2f}\n"
                f"  SL: ${stop_loss:.2f} (${tp_sl_levels.risk_amount:.2f} risk)\n"
                f"  TP: ${take_profit:.2f} (${tp_sl_levels.reward_amount:.2f} reward)\n"
                f"  RR Ratio: {tp_sl_levels.risk_reward_ratio:.2f}\n"
                f"  Regime: {regime}"
            )

            # Execute order
            order = await self.execution.execute_order(
                symbol=self.symbol,
                side=side,
                size=size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                current_price=current_price
            )

            if order:
                self.total_trades_executed += 1
                logger.info(f"✅ ORDER FILLED: {order.id}")

                # Send Telegram notification
                if self.telegram:
                    await self._send_telegram_trade_notification(order, fused_signal)
            else:
                logger.warning("❌ ORDER REJECTED")

        except Exception as e:
            logger.error(f"Error executing order: {e}", exc_info=True)

    async def _send_telegram_trade_notification(self, order, fused_signal):
        """Send trade notification via Telegram"""
        try:
            status = self.execution.get_status()

            message = (
                f"{'🟢' if order.side == OrderSide.BUY else '🔴'} **TRADE EXECUTED**\n\n"
                f"Symbol: {order.symbol}\n"
                f"Side: {order.side.value.upper()}\n"
                f"Size: {order.filled_size:.4f}\n"
                f"Price: ${order.filled_price:.2f}\n"
                f"Position Value: ${order.filled_price * order.filled_size:.2f}\n\n"
                f"**Signal Stats:**\n"
                f"Confidence: {fused_signal.confidence:.1%}\n"
                f"Coherence: {fused_signal.coherence:.1%}\n"
                f"Contributing Signals: {len(fused_signal.contributing_signals)}\n\n"
                f"**Account:**\n"
                f"Capital: ${status['capital']:.2f}\n"
                f"Open Positions: {status['num_positions']}\n"
                f"Daily PnL: ${status['daily_pnl']:.2f}\n"
                f"Total PnL: ${status['total_pnl']:.2f}\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            if asyncio.iscoroutinefunction(self.telegram.send_message):
                await self.telegram.send_message(message)
            else:
                self.telegram.send_message(message)

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    async def position_monitoring_loop(self):
        """Monitor positions and update with current prices"""
        while self.is_running:
            try:
                await asyncio.sleep(1)

                if not self.execution.positions:
                    continue

                # Get current price
                latest_candle = self.data_engine.aggregator.get_latest_candle('1m')
                if not latest_candle:
                    continue

                current_prices = {self.symbol: latest_candle.close}

                # Update positions (checks SL/TP)
                await self.execution.update_positions(current_prices)

            except Exception as e:
                logger.error(f"Error in position monitoring: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def status_reporting_loop(self):
        """Periodically report status"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes

                status = self.execution.get_status()
                metrics = self.data_engine.get_metrics()

                avg_latency = np.mean(self.pipeline_latencies) if self.pipeline_latencies else 0

                logger.info(
                    f"\n{'='*60}\n"
                    f"STATUS REPORT\n"
                    f"{'='*60}\n"
                    f"Capital: ${status['capital']:.2f} (Current: ${status['current_capital']:.2f})\n"
                    f"Total PnL: ${status['total_pnl']:.2f}\n"
                    f"Daily PnL: ${status['daily_pnl']:.2f}\n"
                    f"Unrealized PnL: ${status['unrealized_pnl']:.2f}\n"
                    f"Open Positions: {status['num_positions']}\n"
                    f"Closed Trades: {status['num_closed_trades']}\n"
                    f"Drawdown: {status['drawdown']:.2%}\n\n"
                    f"Signals Generated: {self.total_signals_generated}\n"
                    f"Trades Executed: {self.total_trades_executed}\n"
                    f"Avg Pipeline Latency: {avg_latency:.2f}ms\n"
                    f"Ticks Processed: {metrics['tick_count']}\n"
                    f"{'='*60}\n"
                )

                # Send Telegram status update
                if self.telegram:
                    message = (
                        f"📊 **Status Report**\n\n"
                        f"Capital: ${status['current_capital']:.2f}\n"
                        f"Total PnL: ${status['total_pnl']:.2f}\n"
                        f"Daily PnL: ${status['daily_pnl']:.2f}\n"
                        f"Open Positions: {status['num_positions']}\n"
                        f"Trades: {self.total_trades_executed}\n"
                        f"Latency: {avg_latency:.1f}ms"
                    )
                    if asyncio.iscoroutinefunction(self.telegram.send_message):
                        await self.telegram.send_message(message)
                    else:
                        self.telegram.send_message(message)

            except Exception as e:
                logger.error(f"Error in status reporting: {e}", exc_info=True)

    async def websocket_connection_loop(self):
        """Maintain WebSocket connection to Hyperliquid"""
        try:
            logger.info(f"Starting WebSocket connection for {self.symbol}...")

            # Start WebSocket data stream
            await self.data_stream.start()

            # Subscribe to trades for symbol
            await self.data_stream.subscribe_trades(
                symbol=self.symbol,
                callback=self._on_websocket_trade
            )

            logger.info(f"✅ Subscribed to {self.symbol} trades")

            # Keep connection alive
            while self.is_running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)

    async def _on_websocket_trade(self, trade_data: dict):
        """Handle incoming trade from WebSocket"""
        try:
            # Process trade through data engine
            await self.data_engine.process_trade_message(trade_data)
        except Exception as e:
            logger.error(f"Error processing WebSocket trade: {e}")

    async def start(self):
        """Start the trading orchestrator"""
        self.is_running = True

        logger.info("\n" + "="*60)
        logger.info("🚀 STARTING TRADING ORCHESTRATOR")
        logger.info("="*60 + "\n")

        # Start data engine
        await self.data_engine.start()

        # Start background tasks
        tasks = [
            asyncio.create_task(self.position_monitoring_loop()),
            asyncio.create_task(self.status_reporting_loop()),
            asyncio.create_task(self.websocket_connection_loop())
        ]

        logger.info("✅ All systems operational\n")

        # Send Telegram startup notification
        if self.telegram:
            await self._send_telegram_startup()

        # Keep running
        await asyncio.gather(*tasks)

    async def stop(self):
        """Stop the trading orchestrator"""
        logger.info("\n🛑 Stopping trading orchestrator...")

        self.is_running = False

        # Stop WebSocket
        await self.data_stream.stop()

        # Stop data engine
        await self.data_engine.stop()

        # Close all positions
        for symbol in list(self.execution.positions.keys()):
            await self.execution.close_position(symbol, reason="shutdown")

        # Send Telegram shutdown notification
        if self.telegram:
            status = self.execution.get_status()
            message = (
                f"🛑 **Trading Bot Stopped**\n\n"
                f"Final Capital: ${status['current_capital']:.2f}\n"
                f"Total PnL: ${status['total_pnl']:.2f}\n"
                f"Closed Trades: {status['num_closed_trades']}\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            if asyncio.iscoroutinefunction(self.telegram.send_message):
                await self.telegram.send_message(message)
            else:
                self.telegram.send_message(message)

        logger.info("✅ Shutdown complete")


# Example usage
if __name__ == '__main__':
    import os

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def main():
        # Create orchestrator
        orchestrator = TradingOrchestrator(
            symbol='ETH',
            initial_capital=10000.0,
            max_position_size=0.3,
            enable_telegram=True,
            live_trading=True  # Change to True for LIVE TRADING
        )

        try:
            await orchestrator.start()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await orchestrator.stop()

    asyncio.run(main())
