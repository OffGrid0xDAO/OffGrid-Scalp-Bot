#!/usr/bin/env python3
"""
Hyperliquid API Client

Handles:
- Placing market orders
- Setting TP/SL orders
- Getting account info
- Getting positions
- Fetching latest prices

API Docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api

Setup:
1. Create Hyperliquid account
2. Export your private key from MetaMask/wallet
3. Set HYPERLIQUID_PRIVATE_KEY in .env (without 0x prefix)
"""

import os
import time
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


class HyperliquidClient:
    def __init__(self, testnet: bool = False):
        """
        Initialize Hyperliquid API client using the official SDK

        Args:
            testnet: Use testnet (default: False = MAINNET)
        """
        # Get private key from environment
        private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')

        if not private_key:
            print("⚠️  WARNING: HYPERLIQUID_PRIVATE_KEY not set!")
            print("   Set HYPERLIQUID_PRIVATE_KEY in .env (without 0x prefix)")
            self.enabled = False
            self.testnet = testnet
            return

        # Add 0x prefix if not present
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key

        self.testnet = testnet
        self.private_key = private_key

        # Get account address from private key
        account = Account.from_key(private_key)
        self.address = account.address

        # Determine base URL
        if testnet:
            base_url = constants.TESTNET_API_URL
            print("✅ Using Hyperliquid TESTNET")
        else:
            base_url = constants.MAINNET_API_URL
            print("✅ Using Hyperliquid MAINNET")

        # Initialize SDK clients
        self.info = Info(base_url, skip_ws=True)
        self.exchange = Exchange(account, base_url)

        self.enabled = True
        print(f"✅ Hyperliquid client initialized for address: {self.address[:6]}...{self.address[-4:]}")

    def get_account_info(self) -> Dict:
        """Get account information including balance"""
        if not self.enabled:
            raise Exception("Hyperliquid client not configured!")

        return self.info.user_state(self.address)

    def get_positions(self) -> List[Dict]:
        """Get current open positions"""
        user_state = self.get_account_info()
        return user_state.get('assetPositions', [])

    def get_balance(self) -> float:
        """Get available balance in USD"""
        user_state = self.get_account_info()
        return float(user_state.get('marginSummary', {}).get('accountValue', 0))

    def get_ticker(self, symbol: str = 'ETH') -> Dict:
        """
        Get current ticker info for symbol

        Args:
            symbol: Trading symbol (e.g., 'ETH', 'BTC')

        Returns:
            Dict with price info
        """
        all_mids = self.info.all_mids()
        return {'markPx': all_mids.get(symbol, 0)}

    def get_current_price(self, symbol: str = 'ETH') -> float:
        """
        Get current market price

        Args:
            symbol: Trading symbol

        Returns:
            Current price
        """
        ticker = self.get_ticker(symbol)
        return float(ticker.get('markPx', 0))

    def place_market_order(self, symbol: str, side: str, size: float,
                          reduce_only: bool = False) -> Dict:
        """
        Place a market order

        Args:
            symbol: Trading symbol (e.g., 'ETH')
            side: 'buy' or 'sell'
            size: Order size in base currency
            reduce_only: Only reduce existing position

        Returns:
            Order response
        """
        is_buy = side.lower() == 'buy'

        print(f"📤 Placing {side.upper()} market order: {size} {symbol}")

        # Use market order with slippage tolerance
        response = self.exchange.market_open(
            coin=symbol,
            is_buy=is_buy,
            sz=size,
            reduce_only=reduce_only
        )

        if response.get('status') == 'ok':
            print(f"✅ Order placed successfully!")
        else:
            print(f"❌ Order failed: {response}")

        return response

    def place_limit_order(self, symbol: str, side: str, size: float,
                         price: float, reduce_only: bool = False) -> Dict:
        """
        Place a limit order

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Order size
            price: Limit price
            reduce_only: Only reduce existing position

        Returns:
            Order response
        """
        is_buy = side.lower() == 'buy'

        print(f"📤 Placing {side.upper()} limit order: {size} {symbol} @ ${price:.2f}")

        response = self.exchange.order(
            coin=symbol,
            is_buy=is_buy,
            sz=size,
            limit_px=price,
            order_type={"limit": {"tif": "Gtc"}},
            reduce_only=reduce_only
        )

        if response.get('status') == 'ok':
            print(f"✅ Limit order placed!")
        else:
            print(f"❌ Order failed: {response}")

        return response

    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel an order"""
        response = self.exchange.cancel(coin=symbol, oid=order_id)
        return response

    def place_tp_sl_orders(self, symbol: str, direction: str,
                          position_size: float, entry_price: float,
                          tp_pct: float = 5.0, sl_pct: float = 0.75) -> Tuple[Dict, Dict]:
        """
        Place Take Profit and Stop Loss orders

        Args:
            symbol: Trading symbol
            direction: 'long' or 'short'
            position_size: Size of position to close
            entry_price: Entry price
            tp_pct: Take profit percentage
            sl_pct: Stop loss percentage

        Returns:
            Tuple of (tp_order, sl_order) responses
        """
        if direction == 'long':
            tp_price = entry_price * (1 + tp_pct / 100)
            sl_price = entry_price * (1 - sl_pct / 100)
            tp_side = 'sell'
            sl_side = 'sell'
            is_buy = False
        else:
            tp_price = entry_price * (1 - tp_pct / 100)
            sl_price = entry_price * (1 + sl_pct / 100)
            tp_side = 'buy'
            sl_side = 'buy'
            is_buy = True

        print(f"\n📊 Setting TP/SL for {direction.upper()} position:")
        print(f"   Entry: ${entry_price:.2f}")
        print(f"   TP: ${tp_price:.2f} (+{tp_pct}%)")
        print(f"   SL: ${sl_price:.2f} (-{sl_pct}%)")

        # Place TP order (limit order to close at profit)
        tp_order = self.place_limit_order(
            symbol=symbol,
            side=tp_side,
            size=position_size,
            price=tp_price,
            reduce_only=True
        )

        # Place SL order (stop market order using trigger)
        print(f"📤 Placing SL trigger order @ ${sl_price:.2f}")
        sl_order = self.exchange.order(
            coin=symbol,
            is_buy=is_buy,
            sz=position_size,
            limit_px=sl_price,
            order_type={
                "trigger": {
                    "triggerPx": sl_price,
                    "isMarket": True,
                    "tpsl": "sl"
                }
            },
            reduce_only=True
        )

        if sl_order.get('status') == 'ok':
            print(f"✅ Stop loss set!")
        else:
            print(f"❌ Stop loss failed: {sl_order}")

        return tp_order, sl_order

    def enter_trade(self, symbol: str, direction: str, size_usd: float,
                   tp_pct: float = 5.0, sl_pct: float = 0.75) -> Dict:
        """
        Enter a trade with TP and SL

        Args:
            symbol: Trading symbol
            direction: 'long' or 'short'
            size_usd: Position size in USD
            tp_pct: Take profit percentage
            sl_pct: Stop loss percentage

        Returns:
            Dict with entry info
        """
        # Get current price
        current_price = self.get_current_price(symbol)

        # Calculate position size
        position_size = size_usd / current_price

        # Round to appropriate precision (e.g., 3 decimals for ETH)
        position_size = round(position_size, 3)

        print(f"\n{'='*60}")
        print(f"🚀 ENTERING {direction.upper()} TRADE")
        print(f"{'='*60}")
        print(f"   Symbol: {symbol}")
        print(f"   Size: {position_size} {symbol} (${size_usd:.2f})")
        print(f"   Entry Price: ${current_price:.2f}")

        # Place market order
        side = 'buy' if direction == 'long' else 'sell'
        entry_order = self.place_market_order(symbol, side, position_size)

        if entry_order.get('status') != 'ok':
            print(f"❌ Entry order failed!")
            return {'success': False, 'error': entry_order}

        # Get filled price (use current price as approximation)
        filled_price = current_price

        # Place TP/SL orders
        tp_order, sl_order = self.place_tp_sl_orders(
            symbol=symbol,
            direction=direction,
            position_size=position_size,
            entry_price=filled_price,
            tp_pct=tp_pct,
            sl_pct=sl_pct
        )

        result = {
            'success': True,
            'symbol': symbol,
            'direction': direction,
            'size': position_size,
            'entry_price': filled_price,
            'entry_order': entry_order,
            'tp_order': tp_order,
            'sl_order': sl_order,
            'timestamp': time.time()
        }

        print(f"\n✅ Trade entered successfully!")
        print(f"{'='*60}\n")

        return result


def test_hyperliquid():
    """Test Hyperliquid API connection"""
    print("\n" + "="*60)
    print("🧪 TESTING HYPERLIQUID API")
    print("="*60)

    client = HyperliquidClient(testnet=True)  # Use testnet for testing

    if not client.enabled:
        print("\n❌ Hyperliquid client not configured!")
        print("\nTo set up Hyperliquid API:")
        print("1. Get your wallet private key (from MetaMask/wallet)")
        print("2. Add to .env file:")
        print("   HYPERLIQUID_PRIVATE_KEY=your_private_key_here")
        print("   (without 0x prefix)")
        return

    try:
        print("\n📊 Getting account info...")
        info = client.get_account_info()
        balance = client.get_balance()
        print(f"✅ Account balance: ${balance:.2f}")

        print("\n📊 Getting ETH price...")
        price = client.get_current_price('ETH')
        print(f"✅ ETH price: ${price:.2f}")

        print("\n📊 Getting positions...")
        positions = client.get_positions()
        print(f"✅ Open positions: {len(positions)}")

        print("\n✅ All tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    test_hyperliquid()
