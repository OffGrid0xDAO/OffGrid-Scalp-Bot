"""
Dual-Timeframe Trading Bot with Claude AI
Monitors 5min and 15min charts simultaneously for high-confidence trades
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from eth_account import Account
import time
import re
import threading
from datetime import datetime
from collections import deque
import os
import sys
from dotenv import load_dotenv
import csv
from pathlib import Path

# Import Claude trader
from claude_trader import ClaudeTrader

# Load environment variables
load_dotenv()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


class DualTimeframeBot:
    """
    Dual-timeframe trading bot with Claude AI decision making
    Monitors both 5min and 15min charts simultaneously
    """

    def __init__(self, private_key, use_testnet=True, auto_trade=True,
                 position_size_pct=0.10, leverage=25, min_confidence=0.75):
        """Initialize dual-timeframe bot"""
        self.private_key = private_key
        self.use_testnet = use_testnet
        self.auto_trade = auto_trade
        self.symbol = 'ETH'
        self.leverage = leverage
        self.position_size_pct = position_size_pct
        self.min_confidence = min_confidence

        # Browsers (one for each timeframe)
        self.driver_5min = None
        self.driver_15min = None

        # Data storage for each timeframe
        # Data storage for each timeframe
        # 5min: 4 hours = 240 minutes = ~1440 snapshots (10 sec intervals)
        # 15min: 4 hours = 240 minutes = ~1440 snapshots (10 sec intervals)
        self.data_5min = {
            'indicators': {},
            'state': 'unknown',
            'ema_groups': {},
            'price': None,
            'last_update': None,
            'history': deque(maxlen=1440)  # 4 hours of history (10 sec snapshots)
        }

        self.data_15min = {
            'indicators': {},
            'state': 'unknown',
            'ema_groups': {},
            'price': None,
            'last_update': None,
            'history': deque(maxlen=1440)  # 4 hours of history (10 sec snapshots)
        }

        # State
        self.paused = False
        self.running = True
        self.trades = []
        self.last_signal = None
        self.last_warning = None

        # Transition detection
        self.last_solid_state_5min = None
        self.last_solid_state_15min = None
        self.warmup_complete = False  # Wait for first state transition before trading

        # Order tracking for TP/SL management
        self.active_tp_order = None  # Take profit order ID
        self.active_sl_order = None  # Stop loss order ID
        self.last_sl_price = None    # Track last stop loss price to avoid unnecessary updates

        # Commentary tracking
        self.last_commentary_time = None
        self.commentary_interval = 600  # 10 minutes in seconds
        self.last_commentary = None

        # API call optimization
        self.last_api_call_time = None
        self.min_api_call_interval = 60  # Minimum 60 seconds between Claude calls
        self.last_check_state = {'5min': None, '15min': None}  # Track state changes

        # Data logging
        self.setup_data_logging()

        # Initialize Claude trader
        try:
            self.claude = ClaudeTrader()
            print("✅ Claude AI trader initialized")
        except Exception as e:
            print(f"⚠️  Claude initialization failed: {e}")
            self.claude = None

        # Initialize Hyperliquid connection
        self.reconnect_hyperliquid()

    def setup_data_logging(self):
        """Setup CSV logging for both timeframes"""
        self.data_dir = Path("trading_data")
        self.data_dir.mkdir(exist_ok=True)

        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.data_dir / f"dual_session_{session_timestamp}"
        self.session_dir.mkdir(exist_ok=True)

        # CSV files for each timeframe
        self.ema_data_5min_file = self.session_dir / "ema_data_5min.csv"
        self.ema_data_15min_file = self.session_dir / "ema_data_15min.csv"
        self.trading_decisions_file = self.session_dir / "claude_decisions.csv"

        # Initialize CSV headers
        for file_path in [self.ema_data_5min_file, self.ema_data_15min_file]:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'price', 'ribbon_state'])

        # Trading decisions CSV
        with open(self.trading_decisions_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'direction', 'entry_recommended', 'confidence_score',
                'reasoning', 'entry_price', 'stop_loss', 'take_profit',
                'timeframe_alignment', 'executed'
            ])

        print(f"📁 Data logging initialized: {self.session_dir}")

    def reconnect_hyperliquid(self):
        """Connect to Hyperliquid"""
        api_url = constants.TESTNET_API_URL if self.use_testnet else constants.MAINNET_API_URL

        private_key = self.private_key
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key

        account = Account.from_key(private_key)

        self.info = Info(api_url, skip_ws=True)
        self.exchange = Exchange(account, api_url)
        self.wallet_address = account.address

        print(f"✅ Connected to Hyperliquid")
        print(f"   Wallet: {self.wallet_address}")
        print(f"   Network: {'TESTNET' if self.use_testnet else 'MAINNET'}")
        print(f"   Symbol: {self.symbol}")
        print(f"   Leverage: {self.leverage}x")
        print(f"   Min Confidence: {self.min_confidence:.0%}")

    def setup_browsers(self):
        """Setup two Chrome browsers for dual timeframe monitoring"""
        clear_screen()
        print("="*80)
        print(" "*20 + "DUAL TIMEFRAME BOT SETUP")
        print("="*80)
        print(f"\n💼 Wallet: {self.wallet_address[:10]}...{self.wallet_address[-8:]}")
        print(f"🤖 Auto-Trading: {'ENABLED ✅' if self.auto_trade else 'DISABLED ❌'}")
        print(f"🧠 Claude AI: {'ENABLED ✅' if self.claude else 'DISABLED ❌'}")
        print("\n" + "="*80)
        print("\nTradingView Setup Instructions:")
        print("  1. Log in to TradingView in BOTH browsers")
        print("  2. BROWSER 1: Open 5-minute chart with Annii's Ribbon")
        print("  3. BROWSER 2: Open 15-minute chart with Annii's Ribbon")
        print("  4. Make sure ALL EMAs are visible on both charts")
        print("  5. Press ENTER when both charts are ready")
        print("="*80 + "\n")

        # Setup 5min browser
        print("🔷 Opening Browser 1 (5-minute chart)...")
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_argument('--window-position=0,0')
        chrome_options.add_argument('--window-size=960,1080')

        self.driver_5min = webdriver.Chrome(options=chrome_options)
        self.driver_5min.get('https://www.tradingview.com/')
        time.sleep(2)

        # Setup 15min browser
        print("🔶 Opening Browser 2 (15-minute chart)...")
        chrome_options_15 = Options()
        chrome_options_15.add_argument('--no-sandbox')
        chrome_options_15.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options_15.add_argument('--window-position=960,0')
        chrome_options_15.add_argument('--window-size=960,1080')

        self.driver_15min = webdriver.Chrome(options=chrome_options_15)
        self.driver_15min.get('https://www.tradingview.com/')
        time.sleep(2)

        input("👉 Press ENTER when both charts are ready: ")
        print("\n✅ Both browsers ready!")

    def read_indicators(self, driver):
        """Read indicators from TradingView"""
        try:
            value_items = driver.find_elements(By.CSS_SELECTOR, 'div.valueItem-l31H9iuA')
            indicators = {}

            for item in value_items:
                try:
                    title = item.get_attribute('data-test-id-value-title')
                    if not title:
                        continue

                    value_elem = item.find_element(By.CSS_SELECTOR, 'div.valueValue-l31H9iuA')
                    style = value_elem.get_attribute('style')
                    value = value_elem.text.replace(',', '')

                    try:
                        price = float(value)
                    except:
                        price = None

                    # Parse RGB and classify color
                    rgb_match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', style)
                    if rgb_match:
                        r, g, b = map(int, rgb_match.groups())

                        # Color detection logic
                        if r > 150 and g > 150 and r + g > 300:
                            color = 'yellow'
                            intensity = 'normal'
                        elif g > 150 and g > r * 1.3:
                            if g >= 200 and r < 100 and b < 100:
                                color = 'green'
                                intensity = 'dark'
                            else:
                                color = 'green'
                                intensity = 'light' if g < 180 else 'normal'
                        elif r > 150 and r > g * 1.3:
                            if r >= 200 and g < 100 and b < 100:
                                color = 'red'
                                intensity = 'dark'
                            else:
                                color = 'red'
                                intensity = 'light' if r < 180 else 'normal'
                        elif 100 < r < 150 and 100 < g < 150 and 100 < b < 150 and abs(r-g) < 20 and abs(g-b) < 20:
                            color = 'gray'
                            intensity = 'normal'
                        else:
                            color = 'neutral'
                            intensity = 'normal'

                        indicators[title] = {
                            'value': value,
                            'price': price,
                            'color': color,
                            'intensity': intensity
                        }
                except:
                    continue

            return indicators
        except:
            return {}

    def analyze_ribbon(self, indicators):
        """Analyze ribbon state"""
        mma_indicators = {k: v for k, v in indicators.items() if k.startswith('MMA')}

        if not mma_indicators:
            return None, {}, []

        green_emas = []
        red_emas = []
        yellow_emas = []
        gray_emas = []
        dark_green_emas = []
        dark_red_emas = []

        for name, data in mma_indicators.items():
            ema_info = {
                'name': name,
                'price': data['price'],
                'value': data['value'],
                'intensity': data.get('intensity', 'normal')
            }

            if data['color'] == 'green':
                green_emas.append(ema_info)
                if data.get('intensity') == 'dark':
                    dark_green_emas.append(ema_info)
            elif data['color'] == 'red':
                red_emas.append(ema_info)
                if data.get('intensity') == 'dark':
                    dark_red_emas.append(ema_info)
            elif data['color'] == 'yellow':
                yellow_emas.append(ema_info)
            elif data['color'] == 'gray':
                gray_emas.append(ema_info)

        non_yellow_total = len(green_emas) + len(red_emas)

        # Two-tier threshold system:
        # - 50% threshold: "start watching" (triggers state label)
        # - 85% threshold: "consider entering" (strong alignment for trading)
        if non_yellow_total == 0:
            state = 'unknown'
            entry_strength = 'none'
        elif len(green_emas) >= non_yellow_total * 0.5:  # 50% = start watching
            state = 'all_green'
            # Check if it's strong enough for entry (85%+)
            if len(green_emas) >= non_yellow_total * 0.85:
                entry_strength = 'strong'  # Ready for entry
            else:
                entry_strength = 'building'  # Watching, not ready
        elif len(red_emas) >= non_yellow_total * 0.5:  # 50% = start watching
            state = 'all_red'
            # Check if it's strong enough for entry (85%+)
            if len(red_emas) >= non_yellow_total * 0.85:
                entry_strength = 'strong'  # Ready for entry
            else:
                entry_strength = 'building'  # Watching, not ready
        else:
            state = 'mixed'
            entry_strength = 'weak'

        ema_groups = {
            'yellow': yellow_emas,
            'green': green_emas,
            'red': red_emas,
            'gray': gray_emas,
            'dark_green': dark_green_emas,
            'dark_red': dark_red_emas,
            'entry_strength': entry_strength  # NEW: tells Claude if alignment is strong enough
        }

        return state, ema_groups, mma_indicators

    def detect_fresh_transition(self):
        """
        Detect if we have a FRESH transition (state flip) on either timeframe.
        Returns: (has_transition, transition_info)
        """
        state_5min = self.data_5min['state']
        state_15min = self.data_15min['state']

        transition_5min = None
        transition_15min = None

        # Check 5min transition
        if state_5min in ['all_green', 'all_red']:
            if self.last_solid_state_5min is None:
                # First time seeing a solid state - just record it, don't trade yet
                self.last_solid_state_5min = state_5min
            elif self.last_solid_state_5min != state_5min:
                # State changed! This is a transition
                transition_5min = f"{self.last_solid_state_5min} → {state_5min}"
                self.last_solid_state_5min = state_5min
                self.warmup_complete = True

        # Check 15min transition
        if state_15min in ['all_green', 'all_red']:
            if self.last_solid_state_15min is None:
                # First time seeing a solid state - just record it, don't trade yet
                self.last_solid_state_15min = state_15min
            elif self.last_solid_state_15min != state_15min:
                # State changed! This is a transition
                transition_15min = f"{self.last_solid_state_15min} → {state_15min}"
                self.last_solid_state_15min = state_15min
                self.warmup_complete = True

        # Return transition info
        has_transition = (transition_5min is not None) or (transition_15min is not None)

        transition_info = {
            '5min': transition_5min,
            '15min': transition_15min,
            'warmup_complete': self.warmup_complete
        }

        return has_transition, transition_info

    def get_current_price(self, driver):
        """Get current price from TradingView"""
        try:
            price_wrapper = driver.find_elements(By.CSS_SELECTOR, 'div[class*="priceWrapper"]')

            for wrapper in price_wrapper:
                try:
                    text = wrapper.text.replace(',', '').strip()
                    if text:
                        match = re.search(r'(\d{4,5}\.\d{1,2})', text)
                        if match:
                            price = float(match.group(1))
                            if 1000 < price < 100000:
                                return price
                except:
                    continue

            # Fallback to Hyperliquid
            all_mids = self.info.all_mids()
            price = float(all_mids.get(self.symbol, 0))
            if price > 0:
                return price
        except:
            pass

        return None

    def update_timeframe_data(self, timeframe: str):
        """Update data for specific timeframe (runs in thread)"""
        driver = self.driver_5min if timeframe == '5min' else self.driver_15min
        data_store = self.data_5min if timeframe == '5min' else self.data_15min
        log_file = self.ema_data_5min_file if timeframe == '5min' else self.ema_data_15min_file
        update_interval = 10  # Update every 10 seconds for both timeframes

        while self.running:
            try:
                # Read indicators
                indicators = self.read_indicators(driver)

                if not indicators:
                    time.sleep(update_interval)
                    continue

                # Analyze ribbon
                state, ema_groups, mma_indicators = self.analyze_ribbon(indicators)

                # Get price
                current_price = self.get_current_price(driver)

                # Update data store
                data_store['indicators'] = indicators
                data_store['state'] = state
                data_store['ema_groups'] = ema_groups
                data_store['price'] = current_price
                data_store['last_update'] = datetime.now()

                # Add to history
                data_store['history'].append({
                    'timestamp': time.time(),
                    'price': current_price,
                    'state': state,
                    'ema_groups': ema_groups
                })

                # Log to CSV
                self.log_ema_data(indicators, current_price, state, log_file)

                print(f"✅ {timeframe} updated: {state.upper()} @ ${current_price:.2f}" if current_price else f"✅ {timeframe} updated: {state.upper()}")

            except Exception as e:
                print(f"⚠️  Error updating {timeframe}: {e}")

            time.sleep(update_interval)

    def log_ema_data(self, indicators, current_price, state, log_file):
        """Log EMA data to CSV"""
        try:
            timestamp = datetime.now().isoformat()
            mma_indicators = {k: v for k, v in indicators.items() if k.startswith('MMA')}

            def get_num(key):
                m = re.search(r'\d+', key)
                return int(m.group()) if m else 0

            sorted_mma = sorted(mma_indicators.items(), key=lambda x: get_num(x[0]))

            row = [timestamp, current_price, state]

            for name, data in sorted_mma:
                row.extend([
                    data.get('value', 'N/A'),
                    data.get('color', 'unknown'),
                    data.get('intensity', 'normal')
                ])

            with open(log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

            # Update headers if first data row
            with open(log_file, 'r') as f:
                lines = f.readlines()
                if len(lines) == 2:
                    header = ['timestamp', 'price', 'ribbon_state']
                    for name, _ in sorted_mma:
                        ema_num = get_num(name)
                        header.extend([f'MMA{ema_num}_value', f'MMA{ema_num}_color', f'MMA{ema_num}_intensity'])

                    with open(log_file, 'r') as f:
                        all_rows = list(csv.reader(f))

                    with open(log_file, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        for row in all_rows[1:]:
                            writer.writerow(row)

        except Exception as e:
            print(f"⚠️  Error logging EMA data: {e}")

    def log_claude_decision(self, direction, entry_recommended, confidence_score,
                           reasoning, targets, executed):
        """Log Claude's trading decision"""
        try:
            with open(self.trading_decisions_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    direction,
                    entry_recommended,
                    confidence_score,
                    reasoning[:200],  # Truncate long reasoning
                    targets.get('entry_price', 0),
                    targets.get('stop_loss', 0),
                    targets.get('take_profit', 0),
                    targets.get('timeframe_alignment', 'UNKNOWN'),
                    executed
                ])
        except Exception as e:
            print(f"⚠️  Error logging decision: {e}")

    def get_position(self):
        """Get current position"""
        try:
            user_state = self.info.user_state(self.wallet_address)

            for pos in user_state.get('assetPositions', []):
                position = pos.get('position', {})
                coin = position.get('coin', '')
                size = float(position.get('szi', 0))

                if coin == self.symbol and size != 0:
                    return {
                        'side': 'long' if size > 0 else 'short',
                        'size': abs(size),
                        'entry_price': float(position.get('entryPx', 0)),
                        'unrealized_pnl': float(position.get('unrealizedPnl', 0)),
                        'margin_used': float(position.get('marginUsed', 0))
                    }

            return None
        except Exception as e:
            return None

    def get_account_info(self):
        """Get account info"""
        try:
            user_state = self.info.user_state(self.wallet_address)
            margin_summary = user_state.get('marginSummary', {})
            return {
                'account_value': float(margin_summary.get('accountValue', 0)),
                'margin_used': float(margin_summary.get('totalMarginUsed', 0)),
                'unrealized_pnl': float(margin_summary.get('totalUnrealizedPnl', 0))
            }
        except Exception as e:
            return None

    def place_tp_sl_orders(self, position_side, entry_price, yellow_ema_stop):
        """
        Place TP and SL limit orders on Hyperliquid

        Args:
            position_side: 'long' or 'short'
            entry_price: Entry price of position
            yellow_ema_stop: Yellow EMA stop loss level from Claude

        Returns:
            Tuple of (tp_success, sl_success, messages)
        """
        if not self.auto_trade:
            return False, False, "Auto-trading disabled"

        try:
            pos = self.get_position()
            if not pos:
                return False, False, "No position found"

            size = pos['size']

            # Calculate TP/SL prices based on position side
            if position_side == 'long':
                # LONG: TP above entry, SL at yellow EMA (below entry)
                tp_price = entry_price * 1.015  # 1.5% TP
                sl_price = yellow_ema_stop if yellow_ema_stop > 0 else entry_price * 0.995  # Use yellow EMA or 0.5% SL

                # Place TP (reduce-only sell limit)
                tp_result = self.exchange.order(self.symbol, False, size, tp_price, {"limit": {"tif": "Gtc"}}, reduce_only=True)

                # Place SL (reduce-only sell stop-market at yellow EMA)
                sl_result = self.exchange.order(self.symbol, False, size, sl_price, {"trigger": {"triggerPx": sl_price, "isMarket": True, "tpsl": "sl"}}, reduce_only=True)

            else:  # short
                # SHORT: TP below entry, SL at yellow EMA (above entry)
                tp_price = entry_price * 0.985  # 1.5% TP
                sl_price = yellow_ema_stop if yellow_ema_stop > 0 else entry_price * 1.005  # Use yellow EMA or 0.5% SL

                # Place TP (reduce-only buy limit)
                tp_result = self.exchange.order(self.symbol, True, size, tp_price, {"limit": {"tif": "Gtc"}}, reduce_only=True)

                # Place SL (reduce-only buy stop-market at yellow EMA)
                sl_result = self.exchange.order(self.symbol, True, size, sl_price, {"trigger": {"triggerPx": sl_price, "isMarket": True, "tpsl": "sl"}}, reduce_only=True)

            # Store order IDs if successful
            if tp_result and tp_result.get('status') == 'ok':
                self.active_tp_order = tp_result.get('response', {}).get('data', {}).get('statuses', [{}])[0].get('resting', {}).get('oid')

            if sl_result and sl_result.get('status') == 'ok':
                self.active_sl_order = sl_result.get('response', {}).get('data', {}).get('statuses', [{}])[0].get('resting', {}).get('oid')
                self.last_sl_price = sl_price

            return True, True, f"TP @ ${tp_price:.2f}, SL @ ${sl_price:.2f}"

        except Exception as e:
            return False, False, f"Error placing TP/SL: {str(e)}"

    def update_trailing_stop(self, position_side, yellow_ema_stop):
        """
        Update trailing stop loss based on new yellow EMA level
        Only updates if new stop is more favorable than current

        Args:
            position_side: 'long' or 'short'
            yellow_ema_stop: New yellow EMA stop level from Claude

        Returns:
            Tuple of (success, message)
        """
        if not self.auto_trade or not yellow_ema_stop or yellow_ema_stop == 0:
            return False, "Cannot update trailing stop"

        try:
            # Check if we should update (only trail in favorable direction)
            should_update = False

            if position_side == 'long':
                # For LONG: Only update if new SL is HIGHER (trailing up)
                if self.last_sl_price is None or yellow_ema_stop > self.last_sl_price:
                    should_update = True
            else:  # short
                # For SHORT: Only update if new SL is LOWER (trailing down)
                if self.last_sl_price is None or yellow_ema_stop < self.last_sl_price:
                    should_update = True

            if not should_update:
                return False, f"SL not improved (current: ${self.last_sl_price:.2f}, new: ${yellow_ema_stop:.2f})"

            # Cancel old SL order
            if self.active_sl_order:
                try:
                    self.exchange.cancel(self.symbol, self.active_sl_order)
                except:
                    pass  # Order might already be filled

            # Place new SL order
            pos = self.get_position()
            if not pos:
                self.active_sl_order = None
                self.last_sl_price = None
                return False, "Position already closed"

            size = pos['size']
            is_buy = (position_side == 'short')  # SHORT covers with BUY

            sl_result = self.exchange.order(
                self.symbol, is_buy, size, yellow_ema_stop,
                {"trigger": {"triggerPx": yellow_ema_stop, "isMarket": True, "tpsl": "sl"}},
                reduce_only=True
            )

            if sl_result and sl_result.get('status') == 'ok':
                self.active_sl_order = sl_result.get('response', {}).get('data', {}).get('statuses', [{}])[0].get('resting', {}).get('oid')
                old_sl = self.last_sl_price
                self.last_sl_price = yellow_ema_stop
                return True, f"SL trailed: ${old_sl:.2f} → ${yellow_ema_stop:.2f}"
            else:
                return False, "Failed to place new SL order"

        except Exception as e:
            return False, f"Error updating trailing stop: {str(e)}"

    def cancel_all_orders(self):
        """Cancel all active TP/SL orders"""
        try:
            if self.active_tp_order:
                self.exchange.cancel(self.symbol, self.active_tp_order)
            if self.active_sl_order:
                self.exchange.cancel(self.symbol, self.active_sl_order)

            self.active_tp_order = None
            self.active_sl_order = None
            self.last_sl_price = None
        except Exception as e:
            print(f"⚠️  Error canceling orders: {e}")

    def check_yellow_ema_violation(self, position_side, current_price, yellow_ema_stop):
        """
        Check if price is truly breaking through yellow EMA or just touching

        Strategy:
        - TOUCH: Price within 0.3% of yellow EMA = stay in, it's support/resistance
        - BREAK: Price closed BEYOND yellow EMA by >0.3% = exit, reversal confirmed

        Args:
            position_side: 'long' or 'short'
            current_price: Current market price
            yellow_ema_stop: Yellow EMA level

        Returns:
            Tuple of (should_exit, reason)
        """
        if not yellow_ema_stop or yellow_ema_stop == 0:
            return False, "No yellow EMA level"

        # Calculate distance from yellow EMA
        distance_pct = abs((current_price - yellow_ema_stop) / yellow_ema_stop) * 100

        if position_side == 'long':
            # LONG: Check if price closed BELOW yellow EMA
            if current_price < yellow_ema_stop:
                # Check if it's a BREAK (>0.3% below) or just a TOUCH
                if distance_pct > 0.3:
                    return True, f"Yellow EMA BROKEN: Price ${current_price:.2f} is {distance_pct:.2f}% below yellow ${yellow_ema_stop:.2f}"
                else:
                    return False, f"Yellow EMA touched but holding (only {distance_pct:.2f}% below)"
            else:
                # Price still above yellow EMA - all good
                return False, f"Price ${current_price:.2f} above yellow ${yellow_ema_stop:.2f}"

        else:  # short
            # SHORT: Check if price closed ABOVE yellow EMA
            if current_price > yellow_ema_stop:
                # Check if it's a BREAK (>0.3% above) or just a TOUCH
                if distance_pct > 0.3:
                    return True, f"Yellow EMA BROKEN: Price ${current_price:.2f} is {distance_pct:.2f}% above yellow ${yellow_ema_stop:.2f}"
                else:
                    return False, f"Yellow EMA touched but holding (only {distance_pct:.2f}% above)"
            else:
                # Price still below yellow EMA - all good
                return False, f"Price ${current_price:.2f} below yellow ${yellow_ema_stop:.2f}"

    def execute_trade(self, action, price, yellow_ema_stop=None):
        """
        Execute trade with automatic TP/SL orders

        Args:
            action: 'long', 'short', or 'close'
            price: Current market price
            yellow_ema_stop: Yellow EMA stop level for SL placement

        Returns:
            Tuple of (success, message)
        """
        if not self.auto_trade:
            return False, "Auto-trading disabled"

        try:
            if action == 'close':
                # Cancel all active orders before closing
                self.cancel_all_orders()

                pos = self.get_position()
                if pos:
                    result = self.exchange.market_close(self.symbol, pos['size'])
                    return True, f"Closed {pos['side'].upper()}: {pos['size']:.4f} {self.symbol}"
                else:
                    return False, "No position to close"

            # ENTRY: long or short
            account_info = self.get_account_info()

            if not account_info or account_info['account_value'] == 0:
                return False, "Could not get account value"

            position_usd = account_info['account_value'] * self.position_size_pct * self.leverage
            size = position_usd / price

            if self.symbol in ['ETH', 'BTC']:
                size = round(size, 3)
            else:
                size = round(size, 2)

            if action == 'long':
                result = self.exchange.market_open(self.symbol, True, size, None, 0.01)
                time.sleep(0.5)  # Wait for position to open

                # Place TP/SL orders
                tp_success, sl_success, tp_sl_msg = self.place_tp_sl_orders('long', price, yellow_ema_stop)
                return True, f"LONG opened: {size:.4f} {self.symbol} | {tp_sl_msg}"

            elif action == 'short':
                result = self.exchange.market_open(self.symbol, False, size, None, 0.01)
                time.sleep(0.5)  # Wait for position to open

                # Place TP/SL orders
                tp_success, sl_success, tp_sl_msg = self.place_tp_sl_orders('short', price, yellow_ema_stop)
                return True, f"SHORT opened: {size:.4f} {self.symbol} | {tp_sl_msg}"

            return False, "Unknown action"

        except Exception as e:
            return False, f"Error: {str(e)}"

    def display_dashboard(self, check_num, last_decision=None):
        """Display dashboard"""
        clear_screen()

        print("╔" + "="*78 + "╗")
        print("║" + " "*18 + "DUAL TIMEFRAME TRADING BOT" + " "*33 + "║")
        print("║" + f" {self.leverage}x Leverage | {self.position_size_pct*100:.0f}% Position | Min Conf: {self.min_confidence:.0%} ".center(78) + "║")
        print("╚" + "="*78 + "╝")

        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"\n⏰ {timestamp} | Check #{check_num}")

        # Position info
        pos = self.get_position()
        account = self.get_account_info()

        print("\n" + "─"*80)

        if pos:
            side_emoji = "📈" if pos['side'] == 'long' else "📉"
            pnl_emoji = "🟢" if pos['unrealized_pnl'] > 0 else "🔴"
            pnl_pct = (pos['unrealized_pnl'] / pos['margin_used'] * 100) if pos['margin_used'] > 0 else 0

            print(f"{side_emoji} POSITION: {pos['side'].upper()} | {pos['size']:.4f} {self.symbol}")
            print(f"   Entry: ${pos['entry_price']:.2f} | {pnl_emoji} PnL: ${pos['unrealized_pnl']:+.2f} ({pnl_pct:+.2f}%)")
        else:
            print("📊 POSITION: NONE")

        # Timeframe data
        print("\n" + "─"*80)
        print("📊 TIMEFRAME DATA:")

        # 5min
        state_5min = self.data_5min['state']
        price_5min = self.data_5min['price']
        ema_5min = self.data_5min['ema_groups']
        state_emoji_5min = "🟢" if state_5min == 'all_green' else "🔴" if state_5min == 'all_red' else "⚪"

        print(f"\n🔷 5-MINUTE:")
        print(f"   {state_emoji_5min} State: {state_5min.upper()}")
        print(f"   💰 Price: ${price_5min:.2f}" if price_5min else "   💰 Price: N/A")
        print(f"   🟢 {len(ema_5min.get('green', []))} | 🔴 {len(ema_5min.get('red', []))} | ⚪ {len(ema_5min.get('gray', []))}")
        # Show entry strength indicator
        entry_strength_5min = ema_5min.get('entry_strength', 'unknown')
        strength_emoji = "💪" if entry_strength_5min == 'strong' else "👀" if entry_strength_5min == 'building' else "⚠️"
        if entry_strength_5min in ['strong', 'building']:
            print(f"   {strength_emoji} Entry Strength: {entry_strength_5min.upper()}")
        if ema_5min.get('dark_green') or ema_5min.get('dark_red'):
            print(f"   💎 Dark: {len(ema_5min.get('dark_green', []))} green | {len(ema_5min.get('dark_red', []))} red")

        # 15min
        state_15min = self.data_15min['state']
        price_15min = self.data_15min['price']
        ema_15min = self.data_15min['ema_groups']
        state_emoji_15min = "🟢" if state_15min == 'all_green' else "🔴" if state_15min == 'all_red' else "⚪"

        print(f"\n🔶 15-MINUTE:")
        print(f"   {state_emoji_15min} State: {state_15min.upper()}")
        print(f"   💰 Price: ${price_15min:.2f}" if price_15min else "   💰 Price: N/A")
        print(f"   🟢 {len(ema_15min.get('green', []))} | 🔴 {len(ema_15min.get('red', []))} | ⚪ {len(ema_15min.get('gray', []))}")
        # Show entry strength indicator
        entry_strength_15min = ema_15min.get('entry_strength', 'unknown')
        strength_emoji = "💪" if entry_strength_15min == 'strong' else "👀" if entry_strength_15min == 'building' else "⚠️"
        if entry_strength_15min in ['strong', 'building']:
            print(f"   {strength_emoji} Entry Strength: {entry_strength_15min.upper()}")
        if ema_15min.get('dark_green') or ema_15min.get('dark_red'):
            print(f"   💎 Dark: {len(ema_15min.get('dark_green', []))} green | {len(ema_15min.get('dark_red', []))} red")

        # Warmup status
        if not self.warmup_complete:
            print("\n" + "🔄"*20)
            print("🔄 WARMUP MODE: Waiting for first state transition...")
            print(f"🔄 5min last state: {self.last_solid_state_5min or 'Not yet recorded'}")
            print(f"🔄 15min last state: {self.last_solid_state_15min or 'Not yet recorded'}")
            print("🔄 Bot will trade on the NEXT state flip (fresh transition)")
            print("🔄"*20)

        # Claude decision
        if last_decision:
            print("\n" + "─"*80)
            print("🧠 CLAUDE AI DECISION:")
            print(f"   Direction: {last_decision['direction']}")
            print(f"   Entry: {last_decision['entry_recommended']}")
            print(f"   Confidence: {last_decision['confidence_score']:.0%}")
            print(f"   Alignment: {last_decision['targets'].get('timeframe_alignment', 'UNKNOWN')}")
            print(f"   Reasoning: {last_decision['reasoning'][:100]}...")

        # Last signal
        if self.last_signal:
            print(f"\n⚡ LAST SIGNAL: {self.last_signal}")

        # Claude commentary
        if self.last_commentary:
            print(f"\n💬 CLAUDE'S THOUGHTS:")
            print(f"   {self.last_commentary}")

        # Account info
        if account:
            available = account['account_value'] - account['margin_used']
            pnl_emoji = "🟢" if account['unrealized_pnl'] > 0 else "🔴" if account['unrealized_pnl'] < 0 else "⚪"
            print(f"\n💼 ACCOUNT: ${account['account_value']:,.2f} | Available: ${available:,.2f}")
            print(f"   {pnl_emoji} Total PnL: ${account['unrealized_pnl']:+,.2f}")

        # Trade count
        if self.trades:
            print(f"\n📈 TRADES TODAY: {len(self.trades)}")

        # Claude API cost tracking
        if self.claude:
            cost_stats = self.claude.get_cost_summary()
            print(f"\n💰 API COSTS: ${cost_stats['session_cost_usd']:.4f} ({cost_stats['total_calls']} calls)")
            if cost_stats['total_calls'] > 0:
                calls_per_hour = (cost_stats['total_calls'] / check_num) * 120 if check_num > 0 else 0
                estimated_hourly = cost_stats['session_cost_usd'] / (check_num / 120) if check_num > 0 else 0
                print(f"   Est. hourly: ${estimated_hourly:.2f} | Cached: {cost_stats['total_cached_tokens']:,} tokens")

        # Footer
        print("\n" + "─"*80)
        auto_status = "🤖 AUTO-TRADING: ACTIVE ✅" if self.auto_trade else "⚠️  AUTO-TRADING: DISABLED"
        print(f"{auto_status} | Network: {'TESTNET' if self.use_testnet else 'MAINNET'}")
        print(f"📁 Data Logging: {self.session_dir.name}")
        print("Press Ctrl+C to stop")
        print("─"*80)

    def monitor(self):
        """Main monitoring loop with Claude decision making"""
        self.setup_browsers()

        clear_screen()
        print("🚀 Starting dual-timeframe trading system...")
        print("🧠 Claude AI decision engine active")
        time.sleep(3)

        # Start data collection threads
        thread_5min = threading.Thread(target=self.update_timeframe_data, args=('5min',), daemon=True)
        thread_15min = threading.Thread(target=self.update_timeframe_data, args=('15min',), daemon=True)

        thread_5min.start()
        thread_15min.start()

        print("✅ Data collection threads started")
        time.sleep(5)  # Wait for initial data

        check_num = 0
        last_decision = None

        try:
            while self.running:
                check_num += 1

                # Wait for both timeframes to have data
                if not self.data_5min['price'] or not self.data_15min['price']:
                    print("⏳ Waiting for data from both timeframes...")
                    time.sleep(10)
                    continue

                # Get current position
                pos = self.get_position()
                account = self.get_account_info()

                # Detect transitions
                has_transition, transition_info = self.detect_fresh_transition()

                # Only trade if:
                # 1. Warmup is complete (we've seen at least one state change), OR
                # 2. We detected a fresh transition right now
                should_check_entry = self.warmup_complete or has_transition

                # Smart API call logic to reduce costs
                current_time = time.time()
                time_since_last_call = (current_time - self.last_api_call_time) if self.last_api_call_time else 999
                state_changed = (self.data_5min['state'] != self.last_check_state['5min'] or
                               self.data_15min['state'] != self.last_check_state['15min'])

                # Determine if we should ask Claude for decision
                # Cost optimization: Only call Claude when necessary
                should_ask_claude = False

                if pos:
                    # In position: Check every 60 seconds OR if state changed
                    if time_since_last_call >= self.min_api_call_interval or state_changed:
                        should_ask_claude = True
                elif should_check_entry:
                    # No position: Only check on transitions AND if enough time passed
                    if (has_transition or state_changed) and time_since_last_call >= self.min_api_call_interval:
                        should_ask_claude = True

                # Update last check states
                self.last_check_state['5min'] = self.data_5min['state']
                self.last_check_state['15min'] = self.data_15min['state']

                # Make Claude decision if we have Claude and conditions met
                if self.claude and should_ask_claude:
                    self.last_api_call_time = current_time  # Update call time
                    try:
                        direction, entry_recommended, confidence_score, reasoning, targets = \
                            self.claude.make_trading_decision(
                                self.data_5min,
                                self.data_15min,
                                pos,
                                account
                            )

                        last_decision = {
                            'direction': direction,
                            'entry_recommended': entry_recommended,
                            'confidence_score': confidence_score,
                            'reasoning': reasoning,
                            'targets': targets
                        }

                        # Log decision
                        executed = False
                        current_price = self.data_5min['price']
                        exit_recommended = targets.get('exit_recommended', 'NO').upper()

                        # Build transition context
                        transition_context = ""
                        if has_transition:
                            if transition_info['5min']:
                                transition_context += f" | 5min: {transition_info['5min']}"
                            if transition_info['15min']:
                                transition_context += f" | 15min: {transition_info['15min']}"

                        # CASE 1: We have a position - check for EXIT signals
                        if pos:
                            position_side = pos['side']  # 'long' or 'short'
                            yellow_ema_stop = targets.get('yellow_ema_stop', 0)

                            # Check if we should exit
                            should_exit = False
                            exit_reason = ""

                            # Check yellow EMA violation (BREAK vs TOUCH)
                            yellow_violated, yellow_msg = self.check_yellow_ema_violation(
                                position_side, current_price, yellow_ema_stop
                            )
                            if yellow_violated:
                                should_exit = True
                                exit_reason = yellow_msg

                            # Exit signal from Claude
                            if exit_recommended == 'YES':
                                should_exit = True
                                exit_reason = "Claude EXIT signal"

                            # Position management: EXIT_NOW
                            if targets.get('position_management') == 'EXIT_NOW':
                                should_exit = True
                                exit_reason = "Position management: EXIT_NOW"

                            # Outer bands spreading (pullback warning)
                            if targets.get('outer_bands_spreading', False):
                                should_exit = True
                                exit_reason = "Outer bands spreading (pullback)"

                            # Reversal detection: opposite direction with high confidence
                            opposite_direction = 'SHORT' if position_side == 'long' else 'LONG'
                            if (direction == opposite_direction and
                                entry_recommended == 'YES' and
                                confidence_score >= self.min_confidence):
                                should_exit = True
                                exit_reason = f"Reversal to {direction}"

                            # Execute exit
                            if should_exit and self.auto_trade:
                                success, message = self.execute_trade('close', current_price)

                                if success:
                                    self.last_signal = f"🚪 EXIT {position_side.upper()} @ ${current_price:.2f} | {exit_reason} | {message}"
                                    executed = True
                                    self.trades.append({
                                        'time': datetime.now(),
                                        'action': f'exit_{position_side}',
                                        'price': current_price,
                                        'confidence': confidence_score,
                                        'reasoning': f"{exit_reason}: {reasoning[:100]}"
                                    })

                                    # After closing, check if we should immediately reverse
                                    if exit_reason.startswith("Reversal"):
                                        time.sleep(1)  # Brief pause
                                        reverse_action = opposite_direction.lower()
                                        # Pass yellow_ema_stop for the reverse entry
                                        success_reverse, message_reverse = self.execute_trade(reverse_action, current_price, yellow_ema_stop)

                                        if success_reverse:
                                            self.last_signal += f" → ✅ {opposite_direction} @ ${current_price:.2f} | {message_reverse}{transition_context}"
                                            self.trades.append({
                                                'time': datetime.now(),
                                                'action': reverse_action,
                                                'price': current_price,
                                                'confidence': confidence_score,
                                                'reasoning': reasoning
                                            })
                                        else:
                                            self.last_signal += f" → ❌ Failed to reverse: {message_reverse}"
                                else:
                                    self.last_signal = f"❌ Exit failed: {message}"
                            elif should_exit:
                                self.last_signal = f"📊 EXIT SIGNAL: {position_side.upper()} | {exit_reason} (Auto-trade OFF)"
                            else:
                                # NOT exiting - check if we should trail the stop
                                # Continuous trailing: Update stop loss if yellow EMA has moved favorably
                                position_management = targets.get('position_management', 'HOLD')

                                if position_management in ['TRAIL_YELLOW_EMA', 'HOLD'] and yellow_ema_stop > 0:
                                    trail_success, trail_msg = self.update_trailing_stop(position_side, yellow_ema_stop)
                                    if trail_success:
                                        print(f"📈 Trailing Stop Updated: {trail_msg}")
                                        # Don't update last_signal for trailing - too noisy, just print

                        # CASE 2: No position - check for ENTRY signals
                        elif self.claude.should_execute_trade(direction, entry_recommended, confidence_score, self.min_confidence):
                            action = direction.lower()
                            yellow_ema_stop = targets.get('yellow_ema_stop', 0)

                            if self.auto_trade:
                                success, message = self.execute_trade(action, current_price, yellow_ema_stop)

                                if success:
                                    self.last_signal = f"✅ {direction} @ ${current_price:.2f} | {message} | Conf: {confidence_score:.0%}{transition_context}"
                                    executed = True

                                    self.trades.append({
                                        'time': datetime.now(),
                                        'action': action,
                                        'price': current_price,
                                        'confidence': confidence_score,
                                        'reasoning': reasoning
                                    })
                                else:
                                    self.last_signal = f"❌ {direction} @ ${current_price:.2f} | {message}"
                            else:
                                self.last_signal = f"📊 SIGNAL: {direction} @ ${current_price:.2f} | Conf: {confidence_score:.0%} (Auto-trade OFF)"

                        # Log decision to CSV
                        self.log_claude_decision(direction, entry_recommended, confidence_score,
                                               reasoning, targets, executed)

                    except Exception as e:
                        print(f"⚠️  Claude decision error: {e}")

                # Periodic commentary (every 10 minutes)
                current_time_commentary = time.time()
                if self.claude and (self.last_commentary_time is None or
                                   current_time_commentary - self.last_commentary_time >= self.commentary_interval):
                    try:
                        commentary = self.claude.get_market_commentary(
                            self.data_5min,
                            self.data_15min,
                            pos
                        )
                        self.last_commentary = commentary
                        self.last_commentary_time = current_time_commentary
                        print(f"\n💬 Claude: {commentary}")
                    except Exception as e:
                        print(f"⚠️  Commentary error: {e}")

                # Display dashboard
                self.display_dashboard(check_num, last_decision)

                time.sleep(30)  # Check every 30 seconds

        except KeyboardInterrupt:
            clear_screen()
            print("\n✓ System stopped by user")
            print(f"\nTrades executed: {len(self.trades)}")
            if self.trades:
                for i, trade in enumerate(self.trades, 1):
                    print(f"  {i}. {trade['time'].strftime('%H:%M:%S')} - {trade['action'].upper()} @ ${trade['price']:.2f} (Conf: {trade['confidence']:.0%})")

            # Print Claude API cost summary
            if self.claude:
                self.claude.print_cost_summary()

        finally:
            self.running = False
            if self.driver_5min:
                self.driver_5min.quit()
            if self.driver_15min:
                self.driver_15min.quit()


def main():
    clear_screen()
    print("╔" + "="*78 + "╗")
    print("║" + " "*16 + "DUAL TIMEFRAME TRADING BOT SETUP" + " "*30 + "║")
    print("╚" + "="*78 + "╝")

    # Get config
    print("\n📋 Configuration:")
    print("─"*80)

    # Load private key
    private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')

    if private_key:
        print(f"\n🔑 Private Key: Loaded from .env file ✅")
        print(f"   Address: {Account.from_key('0x' + private_key if not private_key.startswith('0x') else private_key).address[:10]}...")
    else:
        print("\n💡 TIP: Add HYPERLIQUID_PRIVATE_KEY to .env file")
        private_key = input("\n🔑 Hyperliquid Private Key: ").strip()

    # Testnet
    default_testnet = os.getenv('USE_TESTNET', 'true').lower() == 'true'
    use_testnet_input = input(f"🌐 Use Testnet? (yes/no, default: {'yes' if default_testnet else 'no'}): ").strip().lower()

    if use_testnet_input:
        use_testnet = use_testnet_input != 'no'
    else:
        use_testnet = default_testnet

    if not use_testnet:
        print("\n" + "⚠️ "*20)
        print("WARNING: YOU ARE USING MAINNET WITH REAL MONEY!")
        print("⚠️ "*20)
        confirm = input("\nType 'I UNDERSTAND' to continue: ").strip()
        if confirm != 'I UNDERSTAND':
            print("\n✓ Cancelled")
            return

    # Auto-trade
    default_auto_trade = os.getenv('AUTO_TRADE', 'true').lower() == 'true'
    auto_trade_input = input(f"\n🤖 Enable Auto-Trading? (yes/no, default: {'yes' if default_auto_trade else 'no'}): ").strip().lower()

    if auto_trade_input:
        auto_trade = auto_trade_input in ['yes', 'y']
    else:
        auto_trade = default_auto_trade

    # Position size
    default_position_size = float(os.getenv('POSITION_SIZE_PCT', '10'))
    position_size_input = input(f"\n💰 Position size % (default: {default_position_size:.0f}): ").strip()
    try:
        position_size_pct = float(position_size_input) / 100 if position_size_input else default_position_size / 100
    except:
        position_size_pct = default_position_size / 100

    # Leverage
    default_leverage = int(os.getenv('LEVERAGE', '25'))
    leverage_input = input(f"📊 Leverage (default: {default_leverage}): ").strip()
    try:
        leverage = int(leverage_input) if leverage_input else default_leverage
    except:
        leverage = default_leverage

    # Min confidence
    default_min_conf = float(os.getenv('MIN_CONFIDENCE', '0.75'))
    conf_input = input(f"\n🎯 Minimum confidence threshold 0-1 (default: {default_min_conf}): ").strip()
    try:
        min_confidence = float(conf_input) if conf_input else default_min_conf
    except:
        min_confidence = default_min_conf

    # Summary
    print("\n" + "="*80)
    print("📊 CONFIGURATION SUMMARY:")
    print("="*80)
    print(f"  Network: {'TESTNET' if use_testnet else '⚠️  MAINNET ⚠️'}")
    print(f"  Auto-Trading: {'✅ ENABLED' if auto_trade else '❌ DISABLED'}")
    print(f"  Position Size: {position_size_pct*100:.1f}%")
    print(f"  Leverage: {leverage}x")
    print(f"  Min Confidence: {min_confidence:.0%}")
    print(f"  Timeframes: 5min + 15min")
    print(f"  AI: Claude Sonnet 4.5")
    print("="*80)

    confirm = input("\n✅ Start bot? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("\n✓ Cancelled")
        return

    print("\n" + "="*80)
    print("Starting dual-timeframe bot...")
    print("="*80 + "\n")

    # Create and run bot
    bot = DualTimeframeBot(
        private_key=private_key,
        use_testnet=use_testnet,
        auto_trade=auto_trade,
        position_size_pct=position_size_pct,
        leverage=leverage,
        min_confidence=min_confidence
    )
    bot.monitor()


if __name__ == "__main__":
    main()
