#!/usr/bin/env python3
"""
Hyperliquid WebSocket Integration

Handles real-time data streaming from Hyperliquid:
- Trade streams
- Orderbook updates
- User fills
- Account updates

Uses official Hyperliquid WebSocket SDK
"""

import asyncio
import logging
import json
import ssl
from typing import Callable, Optional, Dict, List
from hyperliquid.info import Info
from hyperliquid.utils import constants
import websockets
import certifi

logger = logging.getLogger(__name__)


class HyperliquidWebSocket:
    """
    WebSocket client for Hyperliquid real-time data

    Handles:
    - Trade streaming
    - Automatic reconnection
    - Message processing
    - Error handling
    """

    def __init__(self, testnet: bool = False):
        """
        Initialize WebSocket client

        Args:
            testnet: Use testnet (default: False = MAINNET)
        """
        self.testnet = testnet

        # Determine WebSocket URL
        if testnet:
            self.ws_url = "wss://api.hyperliquid-testnet.xyz/ws"
        else:
            self.ws_url = "wss://api.hyperliquid.xyz/ws"

        self.websocket = None
        self.is_running = False
        self.subscriptions = {}
        self.message_handlers = {}

        logger.info(f"Initialized Hyperliquid WebSocket ({'testnet' if testnet else 'mainnet'})")

    async def connect(self):
        """Establish WebSocket connection"""
        try:
            logger.info(f"Connecting to {self.ws_url}...")

            # Create SSL context with certifi certificates
            ssl_context = ssl.create_default_context(cafile=certifi.where())

            # Connect with SSL context
            self.websocket = await websockets.connect(self.ws_url, ssl=ssl_context)
            self.is_running = True
            logger.info("✅ WebSocket connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            return False

    async def disconnect(self):
        """Close WebSocket connection"""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket disconnected")

    async def subscribe_trades(self, symbol: str, callback: Callable):
        """
        Subscribe to trade stream for symbol

        Args:
            symbol: Trading symbol (e.g., 'ETH')
            callback: Async function to call with trade data
        """
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "trades",
                "coin": symbol
            }
        }

        sub_key = f"trades_{symbol}"
        self.subscriptions[sub_key] = subscription
        self.message_handlers[sub_key] = callback

        if self.websocket:
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"Subscribed to trades for {symbol}")

    async def subscribe_orderbook(self, symbol: str, callback: Callable):
        """
        Subscribe to orderbook updates

        Args:
            symbol: Trading symbol
            callback: Async function to call with orderbook data
        """
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": symbol
            }
        }

        sub_key = f"orderbook_{symbol}"
        self.subscriptions[sub_key] = subscription
        self.message_handlers[sub_key] = callback

        if self.websocket:
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"Subscribed to orderbook for {symbol}")

    async def subscribe_user_fills(self, address: str, callback: Callable):
        """
        Subscribe to user fill events

        Args:
            address: Wallet address
            callback: Async function to call with fill data
        """
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "userFills",
                "user": address
            }
        }

        sub_key = f"fills_{address}"
        self.subscriptions[sub_key] = subscription
        self.message_handlers[sub_key] = callback

        if self.websocket:
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"Subscribed to user fills for {address[:6]}...{address[-4:]}")

    async def _process_message(self, message):
        """Process incoming WebSocket message"""
        try:
            # Handle two possible formats from Hyperliquid:
            # 1. List of trades directly: [{"coin": "ETH", "side": "B", "px": "2500", ...}]
            # 2. Dict with channel: {"channel": "trades", "data": [...]}

            if isinstance(message, list):
                # Direct list of trades - Hyperliquid format
                for trade in message:
                    if isinstance(trade, dict):
                        coin = trade.get('coin')
                        if coin:
                            handler = self.message_handlers.get(f"trades_{coin}")
                            if handler:
                                trade_data = {
                                    'symbol': coin,
                                    'price': float(trade.get('px', 0)),
                                    'quantity': float(trade.get('sz', 0)),
                                    'side': trade.get('side'),
                                    'timestamp': int(trade.get('time', 0))
                                }
                                await handler(trade_data)
                return

            # Handle dict format
            if not isinstance(message, dict):
                return

            channel = message.get('channel')
            data = message.get('data')

            if not channel or not data:
                return

            # Route message to appropriate handler
            if channel == 'trades':
                # Trade data
                if isinstance(data, list):
                    # List of trades
                    for trade in data:
                        coin = trade.get('coin')
                        if coin:
                            handler = self.message_handlers.get(f"trades_{coin}")
                            if handler:
                                trade_data = {
                                    'symbol': coin,
                                    'price': float(trade.get('px', 0)),
                                    'quantity': float(trade.get('sz', 0)),
                                    'side': trade.get('side'),
                                    'timestamp': int(trade.get('time', 0))
                                }
                                await handler(trade_data)
                elif isinstance(data, dict):
                    # Single trade or dict with trades
                    coin = data.get('coin')
                    if coin:
                        handler = self.message_handlers.get(f"trades_{coin}")
                        if handler:
                            # Extract trade info
                            for trade in data.get('trades', []):
                                trade_data = {
                                    'symbol': coin,
                                    'price': float(trade.get('px', 0)),
                                    'quantity': float(trade.get('sz', 0)),
                                    'side': trade.get('side'),
                                    'timestamp': int(trade.get('time', 0))
                                }
                                await handler(trade_data)

            elif channel == 'l2Book':
                # Orderbook data
                coin = data.get('coin')
                if coin:
                    handler = self.message_handlers.get(f"orderbook_{coin}")
                    if handler:
                        await handler(data)

            elif channel == 'userFills':
                # User fill data
                for fill in data.get('fills', []):
                    user = fill.get('user')
                    if user:
                        handler = self.message_handlers.get(f"fills_{user}")
                        if handler:
                            await handler(fill)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    async def message_loop(self):
        """Main message processing loop"""
        while self.is_running:
            try:
                if not self.websocket:
                    logger.warning("WebSocket not connected, reconnecting...")
                    await self.connect()

                    # Re-subscribe to all channels
                    for sub_key, subscription in self.subscriptions.items():
                        await self.websocket.send(json.dumps(subscription))
                        logger.info(f"Re-subscribed: {sub_key}")

                    await asyncio.sleep(1)
                    continue

                # Receive message
                message_str = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=30.0
                )

                message = json.loads(message_str)
                await self._process_message(message)

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                if self.websocket:
                    await self.websocket.ping()

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                self.websocket = None
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in message loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def start(self):
        """Start WebSocket client"""
        await self.connect()
        asyncio.create_task(self.message_loop())

    async def stop(self):
        """Stop WebSocket client"""
        await self.disconnect()


# Simplified integration for trading orchestrator
class HyperliquidDataStream:
    """
    Simplified WebSocket wrapper for trading orchestrator

    Provides easy interface for subscribing to trade data
    """

    def __init__(self, testnet: bool = False):
        self.ws = HyperliquidWebSocket(testnet=testnet)
        self.trade_callbacks = {}

    async def start(self):
        """Start WebSocket connection"""
        await self.ws.start()

    async def stop(self):
        """Stop WebSocket connection"""
        await self.ws.stop()

    async def subscribe_trades(self, symbol: str, callback: Callable):
        """
        Subscribe to trade stream

        Args:
            symbol: Trading symbol
            callback: Async function(trade_data: dict)
                trade_data format: {
                    'symbol': str,
                    'price': float,
                    'quantity': float,
                    'side': 'buy'/'sell',
                    'timestamp': int (ms)
                }
        """
        self.trade_callbacks[symbol] = callback
        await self.ws.subscribe_trades(symbol, self._handle_trade)

    async def _handle_trade(self, trade_data: dict):
        """Internal trade handler"""
        symbol = trade_data.get('symbol')
        if symbol in self.trade_callbacks:
            await self.trade_callbacks[symbol](trade_data)


# Testing
if __name__ == '__main__':
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_websocket():
        """Test WebSocket connection"""

        async def on_trade(trade_data):
            print(f"Trade: {trade_data['symbol']} {trade_data['side']} "
                  f"{trade_data['quantity']} @ ${trade_data['price']:.2f}")

        # Create WebSocket client
        stream = HyperliquidDataStream(testnet=False)  # Use mainnet for testing

        # Start connection
        await stream.start()

        # Subscribe to ETH trades
        await stream.subscribe_trades('ETH', on_trade)

        print("\n✅ WebSocket connected and subscribed to ETH trades")
        print("Listening for trades... (Ctrl+C to stop)\n")

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            await stream.stop()

    # Run test
    asyncio.run(test_websocket())
