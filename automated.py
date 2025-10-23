"""
Integrated Trading System - Monitor + Hyperliquid Auto-Trading
With gray EMA detection and fixed signal detection
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
from datetime import datetime
import os
import sys
from dotenv import load_dotenv
import threading
from collections import deque
import csv
from pathlib import Path
from tv_auto_login import TradingViewLogin
from tv_indicator_setup import TradingViewIndicatorSetup

# Auto-install ChromeDriver
try:
    import chromedriver_autoinstaller
    chromedriver_autoinstaller.install()
except ImportError:
    print("⚠️  chromedriver-autoinstaller not found. Install it with: pip install chromedriver-autoinstaller")
    print("⚠️  Or manually install ChromeDriver from: https://chromedriver.chromium.org/downloads")

# Load environment variables from .env file
load_dotenv()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class AutoTradingSystem:
    def __init__(self, private_key, use_testnet=True, auto_trade=True,
                 position_size_pct=0.10, leverage=25, take_profit_pct=35,
                 profit_trigger=0.3, secure_profit=0.08, scalping_mode='conservative'):
        """Initialize auto-trading system"""
        self.private_key = private_key
        self.use_testnet = use_testnet
        self.auto_trade = auto_trade

        # Trading config
        self.symbol = 'ETH'
        self.leverage = leverage
        self.position_size_pct = position_size_pct

        # Scalping mode: 'conservative' or 'aggressive_5m'
        self.scalping_mode = scalping_mode

        # Mode-specific settings
        if scalping_mode == 'aggressive_5m':
            # Aggressive 5min scalping settings
            self.ribbon_threshold = 0.60  # 60% alignment (vs 90% conservative)
            self.take_profit_account_pct = 10  # 10% account = 0.4% price move
            self.take_profit_account_pct_2 = 20  # Second target 20% = 0.8% price
            self.stop_loss_pct = 0.15  # Tight 0.15% stop (3.75% account)
            self.profit_trigger_pct = 0.12  # Activate protection at 0.12% (3% account)
            self.secure_profit_pct = 0.05  # Secure 0.05% minimum (1.25% account)
            self.use_partial_exits = True
            self.allow_gray_entries = True  # Trade during transitions
            self.partial_exit_done = False
        else:
            # Conservative mode (original settings)
            self.ribbon_threshold = 0.90  # 90% alignment required
            self.take_profit_account_pct = take_profit_pct
            self.take_profit_account_pct_2 = None  # No second target
            self.stop_loss_pct = None  # No hard stop, use ribbon reversal
            self.profit_trigger_pct = profit_trigger
            self.secure_profit_pct = secure_profit
            self.use_partial_exits = False
            self.allow_gray_entries = False
            self.partial_exit_done = False

        # Profit protection settings
        self.profit_secured = False

        # Take profit settings
        self.take_profit_price_pct = self.take_profit_account_pct / self.leverage
        if self.take_profit_account_pct_2:
            self.take_profit_price_pct_2 = self.take_profit_account_pct_2 / self.leverage
        
        # State
        self.prev_state = None
        self.last_solid_state = None
        self.last_signal = None
        self.last_warning = None
        self.trades = []
        self.paused = False

        # State history tracking (time-aware)
        # 5min = 30 checks/candle, 15min = 90 checks/candle
        if scalping_mode == 'aggressive_5m':
            # 3 candles worth for 5min = 90 checks
            self.history_buffer_size = 120
            self.candle_checks = 30  # 300s / 10s
        else:
            # 3 candles worth for 15min = 270 checks
            self.history_buffer_size = 300
            self.candle_checks = 90  # 900s / 10s

        self.state_history = deque(maxlen=self.history_buffer_size)

        # Browser
        self.driver = None

        # Data logging setup
        self.setup_data_logging()

        # Initialize connection
        self.reconnect_hyperliquid()
    
    def reconnect_hyperliquid(self):
        """Connect or reconnect to Hyperliquid with current settings"""
        api_url = constants.TESTNET_API_URL if self.use_testnet else constants.MAINNET_API_URL
        
        private_key = self.private_key
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        account = Account.from_key(private_key)
        
        self.info = Info(api_url, skip_ws=True)
        self.exchange = Exchange(account, api_url)
        self.wallet_address = account.address
        
        # Recalculate take profit price %
        self.take_profit_price_pct = self.take_profit_account_pct / self.leverage
        if self.take_profit_account_pct_2:
            self.take_profit_price_pct_2 = self.take_profit_account_pct_2 / self.leverage

        print(f"✅ Connected to Hyperliquid")
        print(f"   Wallet: {self.wallet_address}")
        print(f"   Network: {'TESTNET' if self.use_testnet else 'MAINNET'}")
        print(f"   Symbol: {self.symbol}")
        print(f"   Leverage: {self.leverage}x")
        print(f"   Mode: {self.scalping_mode.upper()}")
        print(f"   Position Size: {self.position_size_pct*100:.1f}% per trade")
        print(f"\n🛡️ Profit Protection:")
        print(f"   Activates after: +{self.profit_trigger_pct}% price move (~{self.profit_trigger_pct * self.leverage:.1f}% account)")
        print(f"   Secures at least: +{self.secure_profit_pct}% price move (~{self.secure_profit_pct * self.leverage:.1f}% account)")
        print(f"\n🎯 Take Profit Target:")
        print(f"   {self.take_profit_account_pct}% account profit (+{self.take_profit_price_pct:.2f}% price move)")
        if self.take_profit_account_pct_2:
            print(f"   Secondary: {self.take_profit_account_pct_2}% account (+{self.take_profit_price_pct_2:.2f}% price move)")
    
    def setup_data_logging(self):
        """Setup data logging directories and files"""
        # Create data directory
        self.data_dir = Path("trading_data")
        self.data_dir.mkdir(exist_ok=True)

        # Create timestamped session directory
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.data_dir / f"session_{session_timestamp}"
        self.session_dir.mkdir(exist_ok=True)

        # File paths
        self.ema_data_file = self.session_dir / "ema_data.csv"
        self.trading_data_file = self.session_dir / "trading_data.csv"

        # Initialize EMA data CSV with headers
        with open(self.ema_data_file, 'w', newline='') as f:
            writer = csv.writer(f)
            # Will write headers dynamically based on EMAs found
            writer.writerow(['timestamp', 'price', 'ribbon_state'])  # Base headers, EMA columns added dynamically

        # Initialize trading data CSV with headers
        with open(self.trading_data_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'check_number', 'price', 'ribbon_state',
                'green_count', 'red_count', 'yellow_count', 'gray_count',
                'dark_green_count', 'dark_red_count',
                'position_side', 'position_size', 'position_entry', 'position_pnl',
                'account_value', 'margin_used', 'unrealized_pnl',
                'last_signal', 'last_warning', 'profit_secured'
            ])

        print(f"📁 Data logging initialized: {self.session_dir}")

    def log_ema_data(self, indicators, current_price, state):
        """Log EMA values and colors to CSV"""
        try:
            timestamp = datetime.now().isoformat()
            mma_indicators = {k: v for k, v in indicators.items() if k.startswith('MMA')}

            # Sort EMAs by number
            def get_num(key):
                m = re.search(r'\d+', key)
                return int(m.group()) if m else 0

            sorted_mma = sorted(mma_indicators.items(), key=lambda x: get_num(x[0]))

            # Prepare row data
            row = [timestamp, current_price, state]

            # Add each EMA's value and color
            for name, data in sorted_mma:
                ema_num = get_num(name)
                row.extend([
                    data.get('value', 'N/A'),
                    data.get('color', 'unknown'),
                    data.get('intensity', 'normal')
                ])

            # Write to CSV
            with open(self.ema_data_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

            # Update headers if this is the first data row
            with open(self.ema_data_file, 'r') as f:
                lines = f.readlines()
                if len(lines) == 2:  # Header + 1 data row
                    # Update header with EMA columns
                    header = ['timestamp', 'price', 'ribbon_state']
                    for name, _ in sorted_mma:
                        ema_num = get_num(name)
                        header.extend([f'MMA{ema_num}_value', f'MMA{ema_num}_color', f'MMA{ema_num}_intensity'])

                    # Rewrite file with proper header
                    with open(self.ema_data_file, 'r') as f:
                        all_rows = list(csv.reader(f))

                    with open(self.ema_data_file, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        for row in all_rows[1:]:  # Skip old header
                            writer.writerow(row)

        except Exception as e:
            print(f"⚠️  Error logging EMA data: {e}")

    def log_trading_data(self, check_num, current_price, state, ema_groups):
        """Log general trading data to CSV"""
        try:
            timestamp = datetime.now().isoformat()

            # Get position and account info
            pos = self.get_position()
            account = self.get_account_info()

            # Extract EMA counts
            green_count = len(ema_groups.get('green', []))
            red_count = len(ema_groups.get('red', []))
            yellow_count = len(ema_groups.get('yellow', []))
            gray_count = len(ema_groups.get('gray', []))
            dark_green_count = len(ema_groups.get('dark_green', []))
            dark_red_count = len(ema_groups.get('dark_red', []))

            # Prepare row
            row = [
                timestamp,
                check_num,
                current_price if current_price else 'N/A',
                state,
                green_count,
                red_count,
                yellow_count,
                gray_count,
                dark_green_count,
                dark_red_count,
                pos['side'] if pos else 'none',
                pos['size'] if pos else 0,
                pos['entry_price'] if pos else 0,
                pos['unrealized_pnl'] if pos else 0,
                account['account_value'] if account else 0,
                account['margin_used'] if account else 0,
                account['unrealized_pnl'] if account else 0,
                self.last_signal if self.last_signal else '',
                self.last_warning if self.last_warning else '',
                self.profit_secured
            ]

            # Write to CSV
            with open(self.trading_data_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

        except Exception as e:
            print(f"⚠️  Error logging trading data: {e}")

    def setup_browser(self):
        """Open Chrome for monitoring"""
        # Use persistent Chrome profile to save login session
        import time
        base_profile_dir = Path("chrome_profile")
        base_profile_dir.mkdir(exist_ok=True)

        # Try to start Chrome with automatic cleanup and stable flags
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🚀 Starting Chrome browser (attempt {attempt + 1}/{max_retries})...")

                # Build options fresh each attempt and vary profile dir if needed
                chrome_options = Options()
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
                chrome_options.add_experimental_option('useAutomationExtension', False)

                # Choose effective profile directory
                if attempt == 0:
                    effective_profile = base_profile_dir
                else:
                    effective_profile = base_profile_dir / f"run_{int(time.time())}_{attempt}"
                    effective_profile.mkdir(parents=True, exist_ok=True)

                chrome_options.add_argument(f"--user-data-dir={effective_profile.absolute()}")
                chrome_options.add_argument("--profile-directory=TradingBot")

                # Additional options to prevent crashes
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-first-run")
                chrome_options.add_argument("--disable-default-apps")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--no-default-browser-check")
                chrome_options.add_argument("--remote-debugging-port=0")
                chrome_options.add_argument("--start-maximized")

                self.driver = webdriver.Chrome(options=chrome_options)
                break
            except Exception as e:
                err_text = str(e)
                if "user data directory is already in use" in err_text:
                    print(f"   ⚠️  Chrome profile in use (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        print("   🔄 Auto-cleaning Chrome processes...")
                        try:
                            # Kill all Chrome processes automatically
                            import subprocess
                            subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], capture_output=True, text=True)
                            print("   ✅ Killed Chrome processes")

                            # Wait a moment for file locks to release
                            time.sleep(5)
                        except Exception as cleanup_error:
                            print(f"   ⚠️  Auto-cleanup failed: {cleanup_error}")

                        print("   🔄 Retrying with a fresh profile in 3 seconds...")
                        time.sleep(3)
                        continue
                    else:
                        print("\n❌ Chrome profile conflict after auto-cleanup!")
                        print("   🔧 Manual fix needed:")
                        print("   1. Close all Chrome windows manually")
                        print("   2. Delete chrome_profile folder: rmdir /s chrome_profile")
                        print("   3. Run the bot again")
                        raise Exception("Chrome profile directory is still in use after auto-cleanup")
                elif "DevToolsActivePort file doesn't exist" in err_text or "Chrome failed to start" in err_text:
                    print("   ⚠️  Chrome crashed on startup")
                    if attempt < max_retries - 1:
                        print("   🔄 Retrying with adjusted profile in 3 seconds...")
                        time.sleep(3)
                        continue
                    else:
                        raise
                else:
                    raise
        
        # Try to maximize window, but don't fail if already maximized
        try:
            self.driver.maximize_window()
        except Exception:
            # Window might already be maximized, that's okay
            pass
        
        print("\n" + "="*80)
        print("="*80)
        print(" "*20 + "AUTO-TRADING SYSTEM SETUP")
        print("="*80)
        print(f"\n💼 Wallet: {self.wallet_address[:10]}...{self.wallet_address[-8:]}")
        print(f"🤖 Auto-Trading: {'ENABLED ✅' if self.auto_trade else 'DISABLED ❌'}")
        print("\n" + "="*80)
        
        # Check for auto-login credentials
        tv_username = os.getenv('TRADINGVIEW_USERNAME')
        tv_password = os.getenv('TRADINGVIEW_PASSWORD')
        tv_chart_url = os.getenv('TRADINGVIEW_CHART_URL') or 'https://www.tradingview.com/chart/8om7a56p/?symbol=CRYPTO%3AETHUSD&interval=5'
        
        login_handler = TradingViewLogin(self.driver)
        
        # CHECK INDICATORS FIRST: Only login if indicators are not present
        print("\n🔍 Checking if indicators are already loaded...")
        self.driver.get(tv_chart_url)
        time.sleep(3)
        
        # SET ZOOM TO 80% FIRST - before checking indicators
        print("\n🔍 Setting zoom to 80% for better indicator visibility...")
        try:
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains
            
            # Focus on the page first
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
            
            # Use Chrome's built-in zoom via keyboard shortcuts
            # Press Ctrl + - (minus) twice to go from 100% → 90% → 80%
            actions = ActionChains(self.driver)
            
            # First zoom: 100% → 90%
            actions.key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
            time.sleep(0.8)
            
            # Second zoom: 90% → 80%
            actions.key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
            time.sleep(0.8)
            
            print("   ✅ Zoom set to 80% using Chrome keyboard shortcuts")
        except Exception as e:
            print(f"   ⚠️  Could not set zoom: {e}")
            print("   💡 You may need to manually zoom to 80% in the browser")
            print("   🔧 Press Ctrl + - (minus) twice to zoom to 80%")
        
        # Check for indicators first
        indicator_setup = TradingViewIndicatorSetup(self.driver)
        indicators_present = indicator_setup.wait_for_indicators(timeout=5)
        
        if indicators_present:
            print("   ✅ Indicators already present - no login needed!")
            print("   🚀 Proceeding directly to monitoring...")
        else:
            print("   ❌ No indicators found - login required")
            
            # LOGIN ONLY IF NEEDED
            if tv_username and tv_password:
                # AUTO-LOGIN PATH
                print("\n🔐 Auto-login enabled!")
                print("   🔐 Performing auto-login...")
                if login_handler.login(tv_username, tv_password):
                    print("   ✅ Auto-login successful!")
                    # Wait for page to fully load after login
                    time.sleep(3)
                    # Navigate to chart page to ensure we're on the right page
                    self.driver.get(tv_chart_url)
                    time.sleep(2)
                else:
                    print("   ❌ Auto-login failed - please login manually")
                    input("👉 Press ENTER after manual login: ")
            else:
                # MANUAL LOGIN PATH
                print("\n🔐 Manual login required")
                print("💡 TIP: Set TRADINGVIEW_USERNAME and TRADINGVIEW_PASSWORD in .env for auto-login")
                input("👉 Please login to TradingView manually, then press ENTER: ")

        # Setup indicators only if not already present
        if not indicators_present:
            print("\n📊 Setting up indicators...")
            if indicator_setup.setup_ribbon_indicator():
                print("   ✅ Indicator setup completed!")
                if indicator_setup.wait_for_indicators(timeout=15):
                    print("   ✅ Chart ready! Starting bot in 3 seconds...")
                    time.sleep(3)
                else:
                    print("\n⚠️  Indicators not detected automatically")
                    print("   🔍 Please verify indicators are visible in values panel")
                    print("   📊 Values should look like: MMA 8: 3896.50")
                    print("="*80 + "\n")
                    input("👉 Press ENTER when ready: ")
            else:
                print("\n⚠️  Automatic setup failed - manual setup needed")
                print("   🔍 Please click 'Indicators' → Search 'RIBBON FOR SCALPING' → Add to chart")
                print("   📊 Make sure ALL EMAs show in values panel (left side)")
                print("="*80 + "\n")
                input("👉 Press ENTER when ready: ")
        else:
            print("\n📊 Indicators already present - skipping setup!")
            print("   ✅ Chart ready! Starting bot in 3 seconds...")
            time.sleep(3)

        return
    
    # Hyperliquid functions
    def get_account_info(self):
        """Get account balance"""
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
    
    def get_position(self):
        """Get current Hyperliquid position"""
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
    
    def execute_trade(self, action, price):
        """Execute trade on Hyperliquid"""
        if not self.auto_trade:
            return False, "Auto-trading disabled"

        try:
            account_info = self.get_account_info()

            if not account_info or account_info['account_value'] == 0:
                return False, "Could not get account value"

            # Calculate position size
            position_usd = account_info['account_value'] * self.position_size_pct * self.leverage
            size = position_usd / price

            if self.symbol in ['ETH', 'BTC']:
                size = round(size, 3)
            else:
                size = round(size, 2)

            if action == 'long':
                result = self.exchange.market_open(self.symbol, True, size, None, 0.01)
                self.partial_exit_done = False  # Reset on new position
                return True, f"LONG opened: {size:.4f} {self.symbol}"

            elif action == 'short':
                result = self.exchange.market_open(self.symbol, False, size, None, 0.01)
                self.partial_exit_done = False  # Reset on new position
                return True, f"SHORT opened: {size:.4f} {self.symbol}"

            elif action == 'close':
                pos = self.get_position()
                if pos:
                    result = self.exchange.market_close(self.symbol, pos['size'])
                    return True, f"Closed {pos['side'].upper()}: {pos['size']:.4f} {self.symbol}"
                else:
                    return False, "No position to close"

            elif action == 'partial_close':
                # Close 50% of position for aggressive mode
                pos = self.get_position()
                if pos:
                    partial_size = pos['size'] / 2
                    if self.symbol in ['ETH', 'BTC']:
                        partial_size = round(partial_size, 3)
                    else:
                        partial_size = round(partial_size, 2)

                    result = self.exchange.market_close(self.symbol, partial_size)
                    self.partial_exit_done = True
                    return True, f"Partial close (50%): {partial_size:.4f} {self.symbol}"
                else:
                    return False, "No position to close"

            return False, "Unknown action"

        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # Monitor functions
    def read_indicators(self):
        """Read indicators from TradingView"""
        try:
            # Use the EXACT same detection method as wait_for_indicators
            # Look for MMA values with data-test-id-value-title attribute
            value_items = self.driver.find_elements(By.CSS_SELECTOR, "div[data-test-id-value-title*='MMA']")
            
            # Must have at least 10 MMA values to be considered valid (same as wait_for_indicators)
            if len(value_items) < 10:
                print(f"   ⚠️  Only found {len(value_items)} MMA values, need at least 10")
                return {}
            
            print(f"   🔍 Processing {len(value_items)} MMA values...")
            
            indicators = {}
            processed_count = 0
            skipped_count = 0
            
            for item in value_items:
                try:
                    title = item.get_attribute('data-test-id-value-title') or ''
                    # Only process EMAs from the ribbon (titles contain 'MMA')
                    if 'MMA' not in title.upper():
                        continue
                    
                    # Find corresponding numeric value element in the same legend row
                    value_elem = None
                    try:
                        # Try to find the value element within the same parent
                        value_elem = item.find_element(By.XPATH, ".//div[contains(@class,'valueValue')]")
                    except Exception:
                        try:
                            # Fallback: look for sibling element
                            value_elem = item.find_element(By.XPATH, "following-sibling::*[contains(@class,'valueValue')]")
                        except Exception:
                            # Last resort: look in parent row
                            try:
                                parent_row = item.find_element(By.XPATH, "./ancestor::div[contains(@class,'valueItem')][1]")
                                value_elem = parent_row.find_element(By.XPATH, ".//div[contains(@class,'valueValue')]")
                            except Exception:
                                pass
                    
                    if not value_elem:
                        print(f"   ⚠️  No value element found for {title}")
                        skipped_count += 1
                        continue
                        
                    style = value_elem.get_attribute('style') if value_elem else ''
                    value = value_elem.text.replace(',', '') if value_elem else ''
                    
                    if not value or value == '':
                        print(f"   ⚠️  Empty value for {title}")
                        skipped_count += 1
                        continue
                    
                    try:
                        price = float(value)
                    except:
                        print(f"   ⚠️  Invalid price '{value}' for {title}")
                        skipped_count += 1
                        price = None
                    
                    # Parse RGB and classify color with intensity
                    rgb_match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', style)
                    if rgb_match:
                        r, g, b = map(int, rgb_match.groups())

                        # Yellow detection (high red + high green)
                        if r > 150 and g > 150 and r + g > 300:
                            color = 'yellow'
                            intensity = 'normal'
                        # Green detection with intensity
                        elif g > 150 and g > r * 1.3:
                            # Dark green: high green value (200+) and low red/blue
                            if g >= 200 and r < 100 and b < 100:
                                color = 'green'
                                intensity = 'dark'
                            # Light/normal green
                            else:
                                color = 'green'
                                intensity = 'light' if g < 180 else 'normal'
                        # Red detection with intensity
                        elif r > 150 and r > g * 1.3:
                            # Dark red: high red value (200+) and low green/blue
                            if r >= 200 and g < 100 and b < 100:
                                color = 'red'
                                intensity = 'dark'
                            # Light/normal red
                            else:
                                color = 'red'
                                intensity = 'light' if r < 180 else 'normal'
                        # Gray detection (all RGB values similar and moderate)
                        elif 100 < r < 150 and 100 < g < 150 and 100 < b < 150 and abs(r-g) < 20 and abs(g-b) < 20:
                            color = 'gray'
                            intensity = 'normal'
                        else:
                            color = 'neutral'
                            intensity = 'normal'

                        indicators[title] = {'value': value, 'price': price, 'color': color, 'intensity': intensity}
                        processed_count += 1
                except Exception as e:
                    print(f"   ⚠️  Error processing {title}: {e}")
                    skipped_count += 1
                    continue
            
            print(f"   ✅ Successfully processed {processed_count} indicators, skipped {skipped_count}")
            return indicators
        except:
            return {}
    
    def analyze_ribbon(self, indicators):
        """Analyze ribbon state with dark color detection"""
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
            ema_info = {'name': name, 'price': data['price'], 'value': data['value'], 'intensity': data.get('intensity', 'normal')}

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

        if non_yellow_total == 0:
            return 'unknown', {
                'yellow': yellow_emas,
                'green': green_emas,
                'red': red_emas,
                'gray': gray_emas,
                'dark_green': dark_green_emas,
                'dark_red': dark_red_emas
            }, []

        # Use dynamic threshold based on scalping mode
        threshold = self.ribbon_threshold

        if len(green_emas) >= non_yellow_total * threshold:
            state = 'all_green'
        elif len(red_emas) >= non_yellow_total * threshold:
            state = 'all_red'
        else:
            state = 'mixed'

        ema_groups = {
            'yellow': yellow_emas,
            'green': green_emas,
            'red': red_emas,
            'gray': gray_emas,
            'dark_green': dark_green_emas,
            'dark_red': dark_red_emas
        }

        return state, ema_groups, mma_indicators

    def add_state_snapshot(self, state, ema_groups, current_price):
        """Add current state to history buffer"""
        green_emas = ema_groups.get('green', [])
        red_emas = ema_groups.get('red', [])
        gray_emas = ema_groups.get('gray', [])
        dark_green_emas = ema_groups.get('dark_green', [])
        dark_red_emas = ema_groups.get('dark_red', [])

        total_colored = len(green_emas) + len(red_emas)
        green_pct = len(green_emas) / total_colored if total_colored > 0 else 0
        red_pct = len(red_emas) / total_colored if total_colored > 0 else 0

        snapshot = {
            'timestamp': time.time(),
            'price': current_price,
            'ribbon_state': state,
            'green_count': len(green_emas),
            'red_count': len(red_emas),
            'gray_count': len(gray_emas),
            'dark_green_count': len(dark_green_emas),
            'dark_red_count': len(dark_red_emas),
            'green_pct': green_pct,
            'red_pct': red_pct
        }

        self.state_history.append(snapshot)

    def get_history_slice(self, num_checks):
        """Get last N checks from history"""
        if len(self.state_history) < num_checks:
            return list(self.state_history)
        return list(self.state_history)[-num_checks:]

    def detect_momentum_acceleration(self):
        """Detect if green% is accelerating (best entry signal)"""
        # Need at least 1 candle of data
        lookback = min(self.candle_checks, len(self.state_history))
        if lookback < self.candle_checks // 2:  # At least half a candle
            return False, 0

        recent = self.get_history_slice(lookback)

        # Calculate green% trend over the candle
        green_pcts = [s['green_pct'] for s in recent]

        # Check for consistent increase
        if len(green_pcts) < 3:
            return False, 0

        # Recent trend (last 1/3 of candle)
        third = lookback // 3
        early_avg = sum(green_pcts[:third]) / third if third > 0 else 0
        recent_avg = sum(green_pcts[-third:]) / third if third > 0 else 0

        acceleration = recent_avg - early_avg

        # Strong acceleration = 20%+ gain within one candle
        is_accelerating = acceleration > 0.20

        return is_accelerating, acceleration

    def detect_v_bottom_reversal(self):
        """Detect rapid reversal from red to green (V-bottom pattern)"""
        # Need at least 2 candles
        lookback = min(self.candle_checks * 2, len(self.state_history))
        if lookback < self.candle_checks:
            return False, ""

        recent = self.get_history_slice(lookback)

        # Get ribbon states over time
        states = [s['ribbon_state'] for s in recent]

        # Pattern: Was strongly red, now transitioning/green
        # Count red vs green states in first half vs second half
        half = len(states) // 2
        first_half_states = states[:half]
        second_half_states = states[half:]

        first_red_pct = first_half_states.count('all_red') / len(first_half_states) if first_half_states else 0
        second_green_pct = (second_half_states.count('all_green') + second_half_states.count('mixed')) / len(second_half_states) if second_half_states else 0

        # V-bottom: Was >60% red, now >60% green/mixed
        is_v_bottom = first_red_pct > 0.6 and second_green_pct > 0.6

        if is_v_bottom:
            # Check speed of reversal (faster = more explosive)
            dark_greens = [s['dark_green_count'] for s in recent[-self.candle_checks//3:]]
            avg_dark_green = sum(dark_greens) / len(dark_greens) if dark_greens else 0

            if avg_dark_green >= 2:
                return True, "explosive"
            else:
                return True, "normal"

        return False, ""

    def detect_failed_momentum(self):
        """Detect when dark colors are fading (failed breakout)"""
        # Need at least half a candle
        lookback = min(self.candle_checks // 2, len(self.state_history))
        if lookback < 10:  # At least 10 checks
            return False

        recent = self.get_history_slice(lookback)

        dark_green_counts = [s['dark_green_count'] for s in recent]

        # Check if dark greens were present but are now fading
        if len(dark_green_counts) < 3:
            return False

        # Was building, now declining
        early = dark_green_counts[:len(dark_green_counts)//2]
        late = dark_green_counts[len(dark_green_counts)//2:]

        early_avg = sum(early) / len(early) if early else 0
        late_avg = sum(late) / len(late) if late else 0

        # Failed if had 2+ dark greens but now fading
        is_failing = early_avg >= 2.0 and late_avg < early_avg * 0.6

        return is_failing

    def calculate_momentum_velocity(self):
        """Calculate speed of ribbon change (for entry timing)"""
        # Look at last half candle
        lookback = min(self.candle_checks // 2, len(self.state_history))
        if lookback < 5:
            return 0

        recent = self.get_history_slice(lookback)

        green_pcts = [s['green_pct'] for s in recent]

        if len(green_pcts) < 2:
            return 0

        # Velocity = change in green% over time
        velocity = (green_pcts[-1] - green_pcts[0]) / len(green_pcts)

        return velocity

    def show_runtime_menu(self):
        """Show runtime settings menu"""
        print("\n" + "="*80)
        print("╔" + "="*78 + "╗")
        print("║" + " "*25 + "RUNTIME SETTINGS MENU" + " "*32 + "║")
        print("╚" + "="*78 + "╝")
        
        while True:
            pos = self.get_position()
            
            print("\n📊 CURRENT SETTINGS:")
            print("─"*80)
            print(f"  1. Network: {'TESTNET 🧪' if self.use_testnet else 'MAINNET 💰'}")
            print(f"  2. Auto-Trading: {'✅ ENABLED' if self.auto_trade else '❌ DISABLED'}")
            print(f"  3. Position Size: {self.position_size_pct*100:.1f}% per trade")
            print(f"  4. Leverage: {self.leverage}x")
            print(f"  5. Take Profit: {self.take_profit_account_pct:.0f}% account")
            print(f"  6. Protection Trigger: {self.profit_trigger_pct:.2f}% price (~{self.profit_trigger_pct*self.leverage:.1f}% account)")
            print(f"  7. Protection Secure: {self.secure_profit_pct:.2f}% price (~{self.secure_profit_pct*self.leverage:.1f}% account)")
            
            if pos:
                print(f"\n⚠️  ACTIVE POSITION: {pos['side'].upper()} {pos['size']:.4f} {self.symbol}")
                print(f"   Entry: ${pos['entry_price']:.2f} | PnL: ${pos['unrealized_pnl']:+.2f}")
            
            print("\n" + "─"*80)
            print("  R. Resume Monitoring")
            print("  Q. Stop Bot")
            print("─"*80)
            
            choice = input("\nSelect option (1-7, R, Q): ").strip().upper()
            
            if choice == '1':
                # Switch network
                if pos:
                    print("\n⚠️  Cannot switch networks with an active position!")
                    print("   Close your position first, then switch networks.")
                    input("\nPress Enter to continue...")
                    print("\n" + "="*80)
                    continue
                
                new_network = 'mainnet' if self.use_testnet else 'testnet'
                
                if new_network == 'mainnet':
                    print("\n" + "⚠️ "*20)
                    print("WARNING: SWITCHING TO MAINNET WITH REAL MONEY!")
                    print("⚠️ "*20)
                    confirm = input("\nType 'SWITCH TO MAINNET' to confirm: ").strip()
                    if confirm != 'SWITCH TO MAINNET':
                        print("✓ Cancelled")
                        input("\nPress Enter to continue...")
                        print("\n" + "="*80)
                        continue
                
                self.use_testnet = not self.use_testnet
                print(f"\n✓ Switching to {new_network.upper()}...")
                self.reconnect_hyperliquid()
                input("\nPress Enter to continue...")
                clear_screen()
                
            elif choice == '2':
                # Toggle auto-trading
                self.auto_trade = not self.auto_trade
                status = "ENABLED ✅" if self.auto_trade else "DISABLED ❌"
                print(f"\n✓ Auto-Trading: {status}")
                input("\nPress Enter to continue...")
                clear_screen()
                
            elif choice == '3':
                # Change position size
                new_size = input(f"\nNew position size % (current: {self.position_size_pct*100:.1f}): ").strip()
                try:
                    size = float(new_size) / 100
                    if 0 < size <= 1:
                        self.position_size_pct = size
                        print(f"✓ Position size set to {size*100:.1f}%")
                    else:
                        print("⚠️  Invalid size (must be 1-100)")
                except:
                    print("⚠️  Invalid input")
                input("\nPress Enter to continue...")
                clear_screen()
                
            elif choice == '4':
                # Change leverage
                new_lev = input(f"\nNew leverage (current: {self.leverage}): ").strip()
                try:
                    lev = int(new_lev)
                    if 1 <= lev <= 50:
                        self.leverage = lev
                        self.take_profit_price_pct = self.take_profit_account_pct / self.leverage
                        print(f"✓ Leverage set to {lev}x")
                        print("✓ Reconnecting to apply new leverage...")
                        self.reconnect_hyperliquid()
                    else:
                        print("⚠️  Invalid leverage (must be 1-50)")
                except:
                    print("⚠️  Invalid input")
                input("\nPress Enter to continue...")
                clear_screen()
                
            elif choice == '5':
                # Change take profit
                new_tp = input(f"\nNew take profit % account (current: {self.take_profit_account_pct:.0f}): ").strip()
                try:
                    tp = float(new_tp)
                    if 0 < tp <= 200:
                        self.take_profit_account_pct = tp
                        self.take_profit_price_pct = tp / self.leverage
                        print(f"✓ Take profit set to {tp:.0f}% account ({tp/self.leverage:.2f}% price)")
                    else:
                        print("⚠️  Invalid TP (must be 1-200)")
                except:
                    print("⚠️  Invalid input")
                input("\nPress Enter to continue...")
                clear_screen()
                
            elif choice == '6':
                # Change protection trigger
                new_trigger = input(f"\nNew protection trigger % price (current: {self.profit_trigger_pct:.2f}): ").strip()
                try:
                    trigger = float(new_trigger)
                    if 0 < trigger <= 5:
                        self.profit_trigger_pct = trigger
                        print(f"✓ Protection trigger set to {trigger:.2f}% price (~{trigger*self.leverage:.1f}% account)")
                    else:
                        print("⚠️  Invalid value (must be 0.01-5)")
                except:
                    print("⚠️  Invalid input")
                input("\nPress Enter to continue...")
                clear_screen()
                
            elif choice == '7':
                # Change protection secure
                new_secure = input(f"\nNew protection secure % price (current: {self.secure_profit_pct:.2f}): ").strip()
                try:
                    secure = float(new_secure)
                    if 0 < secure <= self.profit_trigger_pct:
                        self.secure_profit_pct = secure
                        print(f"✓ Protection secure set to {secure:.2f}% price (~{secure*self.leverage:.1f}% account)")
                    else:
                        print(f"⚠️  Invalid value (must be less than trigger {self.profit_trigger_pct:.2f})")
                except:
                    print("⚠️  Invalid input")
                input("\nPress Enter to continue...")
                clear_screen()
                
            elif choice == 'R':
                # Resume
                print("\n✓ Resuming monitoring...")
                self.paused = False
                time.sleep(1)
                return True
                
            elif choice == 'Q':
                # Quit
                confirm = input("\n⚠️  Stop the bot? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y']:
                    return False
                clear_screen()
            
            else:
                print("\n⚠️  Invalid option")
                input("\nPress Enter to continue...")
                clear_screen()
    
    def get_current_price(self):
        """Get current price from TradingView price wrapper"""
        try:
            # Method 1: Read price from legend (MMA values) — use last MMA as close proxy
            try:
                last_mma = self.driver.find_elements(By.XPATH, "//span[contains(text(),'MMA')]/following::*[self::div or self::span][1]")
                if last_mma:
                    txt = last_mma[-1].text.replace(',', '').strip()
                    if re.match(r'^\d+\.?\d*$', txt):
                        p = float(txt)
                        if 100 < p < 1000000:
                            return p
            except Exception:
                pass

            # Method 2: TradingView price wrapper
            price_wrapper = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="priceWrapper"]')
            
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
            
            # Method 3: Specific class
            try:
                price_elem = self.driver.find_element(By.CLASS_NAME, 'priceWrapper-qWcO4bp9')
                text = price_elem.text.replace(',', '').strip()
                match = re.search(r'(\d{4,5}\.\d{1,2})', text)
                if match:
                    price = float(match.group(1))
                    if 1000 < price < 100000:
                        return price
            except:
                pass
            
            # Method 4: Fallback to Hyperliquid
            all_mids = self.info.all_mids()
            price = float(all_mids.get(self.symbol, 0))
            if price > 0:
                return price
            
        except:
            pass
        
        return None
    
    def display_dashboard(self, indicators, state, ema_groups, current_price, check_num):
        """Display live dashboard"""
        print("\n" + "="*80)  # Add separator instead of clearing screen

        # Unpack ema_groups
        yellow_emas = ema_groups.get('yellow', [])
        green_emas = ema_groups.get('green', [])
        red_emas = ema_groups.get('red', [])
        gray_emas = ema_groups.get('gray', [])
        dark_green_emas = ema_groups.get('dark_green', [])
        dark_red_emas = ema_groups.get('dark_red', [])

        timestamp = datetime.now().strftime('%H:%M:%S')

        # Header
        print("╔" + "="*78 + "╗")
        print("║" + " "*18 + "AUTO-TRADING SYSTEM (LIVE)" + " "*33 + "║")
        print("║" + f" {self.leverage}x Leverage | {self.position_size_pct*100:.0f}% Position | TP: {self.take_profit_account_pct:.0f}% ".center(78) + "║")
        print("╚" + "="*78 + "╝")

        # Status
        print(f"\n⏰ {timestamp} | Check #{check_num}")

        # Get position from Hyperliquid
        pos = self.get_position()
        account = self.get_account_info()

        # Current state
        print("\n" + "─"*80)
        if state:
            state_emoji = "🟢" if state == 'all_green' else "🔴" if state == 'all_red' else "⚪"
            print(f"💰 PRICE: ${current_price:.2f}" if current_price else "💰 PRICE: N/A", end="  |  ")
            print(f"{state_emoji} STATE: {state.upper().replace('_', ' ')}")
        else:
            print(f"💰 PRICE: ${current_price:.2f}" if current_price else "💰 PRICE: N/A", end="  |  ")
            print("⚪ STATE: NO INDICATORS FOUND")

        # Show dark EMAs count (for aggressive mode)
        if self.scalping_mode == 'aggressive_5m' and (dark_green_emas or dark_red_emas):
            print(f"💎 DARK EMAs: {len(dark_green_emas)} Green | {len(dark_red_emas)} Red")

        # Show last solid state
        if self.last_solid_state:
            solid_emoji = "🟢" if self.last_solid_state == 'all_green' else "🔴"
            print(f"{solid_emoji} LAST SOLID: {self.last_solid_state.upper().replace('_', ' ')}")
        
        # Position info
        if pos:
            side_emoji = "📈" if pos['side'] == 'long' else "📉"
            pnl_emoji = "🟢" if pos['unrealized_pnl'] > 0 else "🔴"
            pnl_pct = (pos['unrealized_pnl'] / pos['margin_used'] * 100) if pos['margin_used'] > 0 else 0
            
            # Calculate profit percentage from entry
            entry = pos['entry_price']
            if pos['side'] == 'long':
                entry_profit_pct = ((current_price - entry) / entry) * 100
            else:
                entry_profit_pct = ((entry - current_price) / entry) * 100
            
            print(f"{side_emoji} POSITION: {pos['side'].upper()} | {pos['size']:.4f} {self.symbol}")
            print(f"   Entry: ${pos['entry_price']:.2f} | {pnl_emoji} PnL: ${pos['unrealized_pnl']:+.2f} ({pnl_pct:+.2f}%)")
            
            # Show profit protection status
            if self.profit_secured:
                secure_price = entry * (1 + self.secure_profit_pct / 100) if pos['side'] == 'long' else entry * (1 - self.secure_profit_pct / 100)
                secure_account_pct = self.secure_profit_pct * self.leverage
                print(f"   🛡️ PROTECTION: ACTIVE | Stop @ ${secure_price:.2f} (+{self.secure_profit_pct:.2f}% price / ~{secure_account_pct:.1f}% account)")
            else:
                trigger_needed = self.profit_trigger_pct - entry_profit_pct
                trigger_account_pct = self.profit_trigger_pct * self.leverage
                if trigger_needed > 0:
                    print(f"   ⏳ Protection activates at +{self.profit_trigger_pct:.2f}% price (~{trigger_account_pct:.1f}% account) | Need +{trigger_needed:.2f}% more")
                else:
                    print(f"   ⚡ Protection ready to activate!")
            
            # Show take profit target
            if pos['side'] == 'long':
                tp_price = entry * (1 + self.take_profit_price_pct / 100)
                distance_to_tp = ((tp_price - current_price) / current_price) * 100
            else:
                tp_price = entry * (1 - self.take_profit_price_pct / 100)
                distance_to_tp = ((current_price - tp_price) / current_price) * 100
            
            print(f"   🎯 Take Profit: ${tp_price:.2f} ({self.take_profit_account_pct}% account) | {distance_to_tp:.2f}% away")
        else:
            print("📊 POSITION: NONE")
        
        print("─"*80)
        
        # Gray warning (appears prominently)
        if gray_emas and not pos:
            print("\n" + "⚠️ "*20)
            print("⚠️  GRAY EMAs DETECTED - RIBBON TRANSITIONING!")
            print("⚠️  Prepare for possible trade signal soon...")
            gray_count = len(gray_emas)
            print(f"⚠️  {gray_count} EMA{'s' if gray_count > 1 else ''} turning gray")
            print("⚠️ "*20)
        
        # Yellow EMAs info (for reference only, not used for exits)
        # if yellow_emas:
        #     yellow_prices = [e['price'] for e in yellow_emas if e['price']]
        #     if yellow_prices:
        #         print(f"\n🟡 YELLOW LEVELS: ", end="")
        #         print(" | ".join([f"${p:.2f}" for p in yellow_prices]))
        
        # EMA table (compact)
        print("\n" + "─"*80)
        mma_indicators = {k: v for k, v in indicators.items() if k.startswith('MMA')}
        
        def get_num(key):
            m = re.search(r'\d+', key)
            return int(m.group()) if m else 0
        
        sorted_mma = sorted(mma_indicators.items(), key=lambda x: get_num(x[0]))
        
        # Display in 4 columns
        for i in range(0, len(sorted_mma), 4):
            row_items = sorted_mma[i:i+4]
            
            for name, data in row_items:
                emoji = {'green': '🟢', 'red': '🔴', 'yellow': '🟡', 'gray': '⚪'}.get(data['color'], '⚫')
                print(f"{emoji} {name:>6}: {data['value']:<10}", end="  ")
            print()
        
        print("─"*80)
        
        # Summary
        total = len(mma_indicators)
        if total == 0:
            print(f"\n❌ NO INDICATORS FOUND!")
            print("   🔍 Please click 'Indicators' → 'Annii's Ribbon' to show EMA values")
            print("   📊 The bot needs to see MMA values like: MMA 8: 3896.50")
        else:
            print(f"\n📊 {total} EMAs | 🟢 {len(green_emas)} | 🔴 {len(red_emas)} | 🟡 {len(yellow_emas)} | ⚪ {len(gray_emas)}")
        
        # Warning message
        if self.last_warning:
            print(f"\n⚠️  {self.last_warning}")
        
        # Last signal
        if self.last_signal:
            print(f"\n⚡ LAST SIGNAL: {self.last_signal}")
        
        # Account info
        if account:
            available = account['account_value'] - account['margin_used']
            pnl_emoji = "🟢" if account['unrealized_pnl'] > 0 else "🔴" if account['unrealized_pnl'] < 0 else "⚪"
            print(f"\n💼 ACCOUNT: ${account['account_value']:,.2f} | Available: ${available:,.2f}")
            print(f"   {pnl_emoji} Total PnL: ${account['unrealized_pnl']:+,.2f}")
        
        # Trade count
        if self.trades:
            print(f"\n📈 TRADES TODAY: {len(self.trades)}")
        
        # Footer
        print("\n" + "─"*80)
        auto_status = "🤖 AUTO-TRADING: ACTIVE ✅" if self.auto_trade else "⚠️  AUTO-TRADING: DISABLED"
        print(f"{auto_status} | Network: {'TESTNET' if self.use_testnet else 'MAINNET'}")
        print(f"📁 Data Logging: {self.session_dir.name}")
        print("Press 'M' + Enter for menu | Ctrl+C to stop")
        print("─"*80)
    
    def check_signals(self, state, ema_groups, current_price):
        """Check for entry/exit signals and warnings with historical context"""
        signal = None
        action = None
        warning = None

        # Unpack ema_groups
        yellow_emas = ema_groups.get('yellow', [])
        green_emas = ema_groups.get('green', [])
        red_emas = ema_groups.get('red', [])
        gray_emas = ema_groups.get('gray', [])
        dark_green_emas = ema_groups.get('dark_green', [])
        dark_red_emas = ema_groups.get('dark_red', [])

        # Get current position
        pos = self.get_position()

        # PRIORITY 0: Failed momentum detection (AVOID ENTRY)
        if not pos and len(self.state_history) >= 10:
            is_failing = self.detect_failed_momentum()
            if is_failing:
                warning = "⚠️  Failed breakout detected - Dark EMAs fading, skipping entry"
                return None, None, warning

        # PRIORITY 1: V-Bottom Reversal + Acceleration (HIGHEST CONFIDENCE)
        if not pos and len(self.state_history) >= self.candle_checks:
            is_v_bottom, intensity = self.detect_v_bottom_reversal()
            is_accelerating, accel_value = self.detect_momentum_acceleration()

            if is_v_bottom and is_accelerating:
                dark_green_count = len(dark_green_emas)
                if intensity == "explosive":
                    signal = f"💥 EXPLOSIVE LONG @ ${current_price:.2f} (V-Bottom + {dark_green_count} Dark Green + {accel_value:.0%} accel)"
                    action = 'long'
                    self.profit_secured = False
                    return signal, action, warning
                elif dark_green_count >= 2:
                    signal = f"🚀 V-BOTTOM LONG @ ${current_price:.2f} (Reversal + {dark_green_count} Dark Green + {accel_value:.0%} accel)"
                    action = 'long'
                    self.profit_secured = False
                    return signal, action, warning

        # PRIORITY 2: Momentum Acceleration (Strong entry)
        if not pos and len(self.state_history) >= self.candle_checks // 2:
            is_accelerating, accel_value = self.detect_momentum_acceleration()
            dark_green_count = len(dark_green_emas)

            if is_accelerating and dark_green_count >= 3:
                signal = f"⚡ ACCELERATION LONG @ ${current_price:.2f} ({dark_green_count} Dark Green + {accel_value:.0%} momentum)"
                action = 'long'
                self.profit_secured = False
                return signal, action, warning

        # PRIORITY 3: Dark color + Gray ultra-early entry (AGGRESSIVE MODE ONLY)
        if self.allow_gray_entries and self.scalping_mode == 'aggressive_5m' and not pos:
            gray_count = len(gray_emas)
            dark_green_count = len(dark_green_emas)
            dark_red_count = len(dark_red_emas)

            # Check velocity to confirm momentum
            velocity = self.calculate_momentum_velocity() if len(self.state_history) >= 5 else 0

            # Ultra-early scalp: Dark green + gray transition + positive velocity
            if dark_green_count >= 2 and gray_count >= 2 and velocity > 0:
                signal = f"💎 ULTRA-EARLY LONG @ ${current_price:.2f} (💎{dark_green_count} Dark Green + ⚪{gray_count} Gray + ⬆️{velocity:.1%}/check)"
                action = 'long'
                self.profit_secured = False
                return signal, action, warning

            # Ultra-early scalp: Dark red + gray transition + negative velocity
            elif dark_red_count >= 2 and gray_count >= 2 and velocity < 0:
                signal = f"💎 ULTRA-EARLY SHORT @ ${current_price:.2f} (💎{dark_red_count} Dark Red + ⚪{gray_count} Gray + ⬇️{abs(velocity):.1%}/check)"
                action = 'short'
                self.profit_secured = False
                return signal, action, warning

        # PRIORITY 4: Gray warning and standard aggressive entry logic
        if gray_emas and not pos:
            gray_count = len(gray_emas)
            if gray_count >= 3:
                warning = f"⚠️  {gray_count} EMAs turning GRAY - Trade signal may be coming!"

                # AGGRESSIVE MODE: Enter during gray transition if majority leans one way
                if self.allow_gray_entries and self.scalping_mode == 'aggressive_5m':
                    total_non_yellow = len(green_emas) + len(red_emas)
                    if total_non_yellow > 0:
                        green_pct = len(green_emas) / total_non_yellow
                        red_pct = len(red_emas) / total_non_yellow

                        # Enter if 50%+ are leaning one direction (early entry)
                        if green_pct >= 0.50 and gray_count >= 3:
                            signal = f"⚡ EARLY LONG @ ${current_price:.2f} (Gray transition: {len(green_emas)}G + {gray_count} gray)"
                            action = 'long'
                            self.profit_secured = False
                        elif red_pct >= 0.50 and gray_count >= 3:
                            signal = f"⚡ EARLY SHORT @ ${current_price:.2f} (Gray transition: {len(red_emas)}R + {gray_count} gray)"
                            action = 'short'
                            self.profit_secured = False

        # PRIORITY 5: Standard entry - when ribbon becomes fully green or fully red
        # Track last solid state (all_green or all_red)
        if state in ['all_green', 'all_red'] and not pos and not signal:
            # We have a solid state now
            if self.last_solid_state and self.last_solid_state != state:
                # State changed from one solid state to another
                if self.last_solid_state == 'all_red' and state == 'all_green':
                    signal = f"🚀 LONG @ ${current_price:.2f} (Ribbon: ALL RED → ALL GREEN | {len(green_emas)}G/{len(red_emas)}R/{len(yellow_emas)}Y)"
                    action = 'long'
                    self.profit_secured = False  # Reset protection flag

                elif self.last_solid_state == 'all_green' and state == 'all_red':
                    signal = f"🚀 SHORT @ ${current_price:.2f} (Ribbon: ALL GREEN → ALL RED | {len(green_emas)}G/{len(red_emas)}R/{len(yellow_emas)}Y)"
                    action = 'short'
                    self.profit_secured = False  # Reset protection flag

            # Update last solid state
            self.last_solid_state = state
        
        # HARD STOP LOSS (Aggressive mode only) - checked first
        if pos and self.stop_loss_pct:
            entry = pos['entry_price']

            if pos['side'] == 'long':
                loss_pct = ((current_price - entry) / entry) * 100
                if loss_pct <= -self.stop_loss_pct:
                    account_loss = loss_pct * self.leverage
                    signal = f"❌ STOP LOSS @ ${current_price:.2f} ({loss_pct:.2f}% price / ~{account_loss:.1f}% account)"
                    action = 'close'
                    return signal, action, warning

            else:  # short
                loss_pct = ((entry - current_price) / entry) * 100
                if loss_pct <= -self.stop_loss_pct:
                    account_loss = loss_pct * self.leverage
                    signal = f"❌ STOP LOSS @ ${current_price:.2f} ({loss_pct:.2f}% price / ~{account_loss:.1f}% account)"
                    action = 'close'
                    return signal, action, warning

        # PARTIAL PROFIT TARGET (Aggressive mode - first target)
        if pos and self.use_partial_exits and not self.partial_exit_done:
            entry = pos['entry_price']

            if pos['side'] == 'long':
                profit_pct = ((current_price - entry) / entry) * 100
                take_profit_price = entry * (1 + self.take_profit_price_pct / 100)

                if current_price >= take_profit_price:
                    account_profit = profit_pct * self.leverage
                    signal = f"🎯 PARTIAL TP (50%) @ ${current_price:.2f} (+{profit_pct:.2f}% / ~{account_profit:.1f}% account)"
                    action = 'partial_close'
                    return signal, action, warning

            else:  # short
                profit_pct = ((entry - current_price) / entry) * 100
                take_profit_price = entry * (1 - self.take_profit_price_pct / 100)

                if current_price <= take_profit_price:
                    account_profit = profit_pct * self.leverage
                    signal = f"🎯 PARTIAL TP (50%) @ ${current_price:.2f} (+{profit_pct:.2f}% / ~{account_profit:.1f}% account)"
                    action = 'partial_close'
                    return signal, action, warning

        # FINAL PROFIT TARGET (Second target for partial exits or main target)
        if pos:
            entry = pos['entry_price']

            # Use second target if partial exits enabled and already took first profit
            if self.use_partial_exits and self.partial_exit_done and self.take_profit_price_pct_2:
                target_pct = self.take_profit_price_pct_2
                target_label = "FINAL"
            else:
                target_pct = self.take_profit_price_pct
                target_label = "TAKE PROFIT"

            if pos['side'] == 'long':
                profit_pct = ((current_price - entry) / entry) * 100
                take_profit_price = entry * (1 + target_pct / 100)

                if current_price >= take_profit_price:
                    account_profit = profit_pct * self.leverage
                    signal = f"🎯 {target_label} @ ${current_price:.2f} (+{profit_pct:.2f}% price / {account_profit:.1f}% account)"
                    action = 'close'
                    return signal, action, warning

            else:  # short
                profit_pct = ((entry - current_price) / entry) * 100
                take_profit_price = entry * (1 - target_pct / 100)

                if current_price <= take_profit_price:
                    account_profit = profit_pct * self.leverage
                    signal = f"🎯 {target_label} @ ${current_price:.2f} (+{profit_pct:.2f}% price / {account_profit:.1f}% account)"
                    action = 'close'
                    return signal, action, warning

        # Profit protection logic (breakeven stop) - for conservative mode or after partial exit
        if pos and not self.profit_secured:
            entry = pos['entry_price']
            profit_pct = 0

            if pos['side'] == 'long':
                profit_pct = ((current_price - entry) / entry) * 100
            else:  # short
                profit_pct = ((entry - current_price) / entry) * 100

            # Check if we've hit the profit trigger
            if profit_pct >= self.profit_trigger_pct:
                self.profit_secured = True
                account_profit = profit_pct * self.leverage
                warning = f"🛡️ PROFIT PROTECTION ACTIVATED at {profit_pct:.2f}% price move (~{account_profit:.1f}% account)!"

        # Check profit protection stop (only if activated)
        if pos and self.profit_secured:
            entry = pos['entry_price']

            if pos['side'] == 'long':
                secure_price = entry * (1 + self.secure_profit_pct / 100)
                if current_price <= secure_price:
                    profit_pct = ((current_price - entry) / entry) * 100
                    account_profit = profit_pct * self.leverage
                    signal = f"🛡️ PROFIT SECURED @ ${current_price:.2f} (+{profit_pct:.2f}% price / ~{account_profit:.1f}% account)"
                    action = 'close'

            else:  # short
                secure_price = entry * (1 - self.secure_profit_pct / 100)
                if current_price >= secure_price:
                    profit_pct = ((entry - current_price) / entry) * 100
                    account_profit = profit_pct * self.leverage
                    signal = f"🛡️ PROFIT SECURED @ ${current_price:.2f} (+{profit_pct:.2f}% price / ~{account_profit:.1f}% account)"
                    action = 'close'
        
        # Yellow cross exits (backup/optional - commented out, can re-enable if needed)
        # if pos and not signal:
        #     yellow_prices = [e['price'] for e in yellow_emas if e['price']]
        #     if yellow_prices:
        #         max_yellow = max(yellow_prices)
        #         min_yellow = min(yellow_prices)
        #         
        #         if pos['side'] == 'long' and current_price < min_yellow:
        #             signal = f"❌ EXIT LONG @ ${current_price:.2f} (crossed below yellow)"
        #             action = 'close'
        #             
        #         elif pos['side'] == 'short' and current_price > max_yellow:
        #             signal = f"❌ EXIT SHORT @ ${current_price:.2f} (crossed above yellow)"
        #             action = 'close'
        
        return signal, action, warning
    
    def monitor(self):
        """Main monitoring loop"""
        self.setup_browser()
        
        print("\n" + "="*80)
        print("🚀 Starting auto-trading system...")
        print("\n💡 TIP: Type 'M' and press Enter at any time to open settings menu")
        time.sleep(3)
        
        check_num = 0
        
        # Start input thread for menu access
        def check_input():
            while True:
                try:
                    user_input = input()
                    if user_input.upper() == 'M':
                        self.paused = True
                except:
                    pass
        
        input_thread = threading.Thread(target=check_input, daemon=True)
        input_thread.start()
        
        try:
            while True:
                # Check if paused for menu
                if self.paused:
                    should_continue = self.show_runtime_menu()
                    if not should_continue:
                        break
                    print("\n" + "="*80)
                    print("🚀 Resuming monitoring...")
                    time.sleep(2)
                
                check_num += 1
                
                # Read data
                indicators = self.read_indicators()
                
                if not indicators:
                    print("⚠️  No indicators found")
                    print("   🔍 Debug: Checking for MMA elements...")
                    try:
                        mma_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[data-test-id-value-title*='MMA']")
                        print(f"   📊 Found {len(mma_elements)} MMA elements")
                        if mma_elements:
                            titles = [elem.get_attribute('data-test-id-value-title') for elem in mma_elements[:5]]
                            print(f"   📋 Sample titles: {titles}")
                    except Exception as e:
                        print(f"   ❌ Error checking elements: {e}")
                    time.sleep(10)
                    continue
                
                # Analyze
                state, ema_groups, mma_indicators = self.analyze_ribbon(indicators)
                current_price = self.get_current_price()

                # Add to state history for temporal analysis
                self.add_state_snapshot(state, ema_groups, current_price)

                # Log data to CSV files (every 10 seconds)
                self.log_ema_data(indicators, current_price, state)
                self.log_trading_data(check_num, current_price, state, ema_groups)

                # Check for signals and warnings (now with historical context)
                signal, action, warning = self.check_signals(state, ema_groups, current_price)
                
                # Update warning
                if warning:
                    self.last_warning = warning
                else:
                    self.last_warning = None
                
                # Execute trade if signal (only on confirmation, not on gray warning)
                if signal and action:
                    self.last_signal = signal
                    
                    if self.auto_trade:
                        success, message = self.execute_trade(action, current_price)
                        
                        if success:
                            self.last_signal += f" ✅ {message}"
                            
                            # Reset profit protection when closing
                            if action == 'close':
                                self.profit_secured = False
                            
                            # Record trade
                            self.trades.append({
                                'time': datetime.now(),
                                'action': action,
                                'price': current_price,
                                'signal': signal
                            })
                        else:
                            self.last_signal += f" ❌ {message}"
                
                # Display
                self.display_dashboard(indicators, state, ema_groups, current_price, check_num)
                
                self.prev_state = state
                
                time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n" + "="*80)
            print("\n✓ System stopped by user")
            print(f"\nTrades executed: {len(self.trades)}")
            if self.trades:
                for i, trade in enumerate(self.trades, 1):
                    print(f"  {i}. {trade['time'].strftime('%H:%M:%S')} - {trade['action'].upper()} @ ${trade['price']:.2f}")
            
        finally:
            if self.driver:
                self.driver.quit()


def main():
    print("\n" + "="*80)
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "AUTO-TRADING SYSTEM SETUP" + " "*33 + "║")
    print("╚" + "="*78 + "╝")
    
    # Default settings option
    print("\n⚙️  CONFIGURATION OPTIONS")
    print("─"*40)
    print("🚀 Use default settings? (Recommended for beginners)")
    print("   • Conservative mode (15min)")
    print("   • 10% position size")
    print("   • 35% take profit")
    print("   • 15% stop loss")
    print("   • Auto-login enabled")
    
    use_defaults = input("\n👉 Use defaults? (Y/n) [default: Y]: ").strip().lower()
    
    if not use_defaults or use_defaults in ['y', 'yes', '']:
        # Use all defaults - skip all configuration
        print("\n✅ Using default settings!")
        print("   🎯 Mode: Conservative (15min)")
        print("   💰 Position: 10%")
        print("   📈 Take Profit: 35%")
        print("   📉 Stop Loss: 15%")
        print("   🔐 Auto-login: Enabled")
        
        # Set default values
        scalping_mode = "conservative_15m"
        position_size = 0.10
        take_profit_pct = 35.0
        stop_loss_pct = 15.0
        leverage = 25
        profit_trigger = 0.3
        secure_profit = 0.08
        auto_login = True
        
        # Load private key (still needed)
        private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')
        if private_key:
            print(f"\n🔑 Private Key: Loaded from .env file ✅")
        else:
            print("\n💡 TIP: Create a .env file with HYPERLIQUID_PRIVATE_KEY to skip this step")
            private_key = input("\n🔑 Hyperliquid Private Key: ").strip()
        
        # Testnet setting
        default_testnet = os.getenv('USE_TESTNET', 'true').lower() == 'true'
        use_testnet = default_testnet
        print(f"\n🌐 Using {'Testnet' if use_testnet else 'Mainnet'}")
        
        # Skip all other configuration
        print("\n" + "="*80)
        print("📊 TRADING CONFIGURATION SUMMARY:")
        print("="*80)
        print(f"🎯 Mode: {scalping_mode.replace('_', ' ').title()}")
        print(f"💰 Position Size: {position_size*100:.0f}%")
        print(f"📈 Take Profit: {take_profit_pct:.0f}%")
        print(f"📉 Stop Loss: {stop_loss_pct:.0f}%")
        print(f"⚡ Leverage: {leverage}x")
        print(f"🛡️  Profit Protection: {profit_trigger*leverage:.1f}% → {secure_profit*leverage:.1f}%")
        print(f"🌐 Network: {'Testnet' if use_testnet else 'Mainnet'}")
        print("="*80)
        
        # Start the bot with defaults
        system = AutoTradingSystem(
            private_key=private_key,
            use_testnet=use_testnet,
            scalping_mode=scalping_mode,
            position_size_pct=position_size,
            take_profit_pct=take_profit_pct,
            leverage=leverage,
            profit_trigger=profit_trigger,
            secure_profit=secure_profit
        )
        system.monitor()
        return
    
    # Get config (custom settings)
    print("\n📋 Custom Configuration:")
    print("─"*80)
    
    # Try to load private key from .env
    private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')
    
    if private_key:
        print(f"\n🔑 Private Key: Loaded from .env file ✅")
        print(f"   Address: {Account.from_key('0x' + private_key if not private_key.startswith('0x') else private_key).address[:10]}...")
    else:
        print("\n💡 TIP: Create a .env file with HYPERLIQUID_PRIVATE_KEY to skip this step")
        private_key = input("\n🔑 Hyperliquid Private Key: ").strip()
    
    # Load other settings from .env or use defaults/prompts
    default_testnet = os.getenv('USE_TESTNET', 'true').lower() == 'true'
    use_testnet_input = input(f"🌐 Use Testnet? (yes/no, default: {'yes' if default_testnet else 'no'}) [Press Enter for yes]: ").strip().lower()
    
    if use_testnet_input:
        use_testnet = use_testnet_input not in ['no', 'n']
    else:
        use_testnet = default_testnet
    
    if not use_testnet:
        print("\n" + "⚠️ "*20)
        print("WARNING: YOU ARE USING MAINNET WITH REAL MONEY!")
        print("⚠️ "*20)
        confirm = input("\nType 'I UNDERSTAND' to continue: ").strip()
        if confirm != 'I UNDERSTAND':
            print("\n✓ Cancelled - Use testnet first to practice!")
            return
    
    default_auto_trade = os.getenv('AUTO_TRADE', 'true').lower() == 'true'
    auto_trade_input = input(f"\n🤖 Enable Auto-Trading? (yes/no, default: {'yes' if default_auto_trade else 'no'}) [Press Enter for yes]: ").strip().lower()
    
    if auto_trade_input:
        auto_trade = auto_trade_input not in ['no', 'n']
    else:
        auto_trade = default_auto_trade
    
    if not auto_trade:
        print("\n⚠️  Auto-trading disabled - Monitor only mode")

    # Scalping mode configuration
    print("\n" + "─"*80)
    print("⚡ Scalping Mode:")
    print("  1. Conservative (15min) - Wait for full ribbon flip, larger TPs")
    print("  2. Aggressive (5min) - Faster entries, partial exits, tight stops")

    default_mode = os.getenv('SCALPING_MODE', 'conservative')
    mode_input = input(f"\nSelect mode (1=conservative, 2=aggressive, default: {'1' if default_mode=='conservative' else '2'}): ").strip()

    if mode_input == '2':
        scalping_mode = 'aggressive_5m'
    elif mode_input == '1':
        scalping_mode = 'conservative'
    else:
        scalping_mode = default_mode

    if scalping_mode == 'aggressive_5m':
        print("\n⚡ AGGRESSIVE 5MIN MODE SELECTED:")
        print("   • Enters at 60% ribbon alignment (vs 90%)")
        print("   • Early entries during gray transitions")
        print("   • TP1: 10% account (0.4% price) → Close 50%")
        print("   • TP2: 20% account (0.8% price) → Close remaining")
        print("   • Hard stop: -0.15% price (-3.75% account)")
        print("   • Profit protection: +0.12% → secure +0.05% minimum")

    # Position size configuration
    print("\n" + "─"*80)
    print("💰 Position Sizing:")
    
    default_position_size = float(os.getenv('POSITION_SIZE_PCT', '10'))
    position_size_input = input(f"Position size as % of account (default: {default_position_size:.0f}): ").strip()
    try:
        position_size_pct = float(position_size_input) / 100 if position_size_input else default_position_size / 100
        if position_size_pct <= 0 or position_size_pct > 1:
            print("⚠️  Invalid size, using default")
            position_size_pct = default_position_size / 100
    except:
        print("⚠️  Invalid input, using default")
        position_size_pct = default_position_size / 100
    
    # Leverage configuration
    default_leverage = int(os.getenv('LEVERAGE', '25'))
    leverage_input = input(f"Leverage (default: {default_leverage}): ").strip()
    try:
        leverage = int(leverage_input) if leverage_input else default_leverage
        if leverage < 1 or leverage > 50:
            print(f"⚠️  Invalid leverage, using default {default_leverage}x")
            leverage = default_leverage
    except:
        print(f"⚠️  Invalid input, using default {default_leverage}x")
        leverage = default_leverage
    
    # Take profit configuration
    print("\n" + "─"*80)
    print("🎯 Take Profit Settings:")
    
    default_take_profit = float(os.getenv('TAKE_PROFIT_PCT', '35'))
    tp_input = input(f"Take profit % (account profit, default: {default_take_profit:.0f}): ").strip()
    try:
        take_profit_pct = float(tp_input) if tp_input else default_take_profit
        if take_profit_pct <= 0 or take_profit_pct > 200:
            print(f"⚠️  Invalid TP, using default {default_take_profit:.0f}%")
            take_profit_pct = default_take_profit
    except:
        print(f"⚠️  Invalid input, using default {default_take_profit:.0f}%")
        take_profit_pct = default_take_profit
    
    # Profit protection configuration
    print("\n" + "─"*80)
    print("🛡️ Profit Protection:")
    print("(Leave blank to use defaults)")
    
    default_profit_trigger = float(os.getenv('PROFIT_TRIGGER_PCT', '0.3'))
    trigger_input = input(f"Activate protection at % price move (default: {default_profit_trigger} = {default_profit_trigger*leverage:.1f}% account): ").strip()
    try:
        profit_trigger = float(trigger_input) if trigger_input else default_profit_trigger
        if profit_trigger < 0 or profit_trigger > 5:
            print(f"⚠️  Invalid value, using default {default_profit_trigger}%")
            profit_trigger = default_profit_trigger
    except:
        print(f"⚠️  Invalid input, using default {default_profit_trigger}%")
        profit_trigger = default_profit_trigger
    
    default_secure_profit = float(os.getenv('SECURE_PROFIT_PCT', '0.08'))
    secure_input = input(f"Secure at least % price move (default: {default_secure_profit} = {default_secure_profit*leverage:.1f}% account): ").strip()
    try:
        secure_profit = float(secure_input) if secure_input else default_secure_profit
        if secure_profit < 0 or secure_profit > profit_trigger:
            print(f"⚠️  Invalid value, using default {default_secure_profit}%")
            secure_profit = default_secure_profit
    except:
        print(f"⚠️  Invalid input, using default {default_secure_profit}%")
        secure_profit = default_secure_profit
    
    # Summary
    print("\n" + "="*80)
    print("📊 TRADING CONFIGURATION SUMMARY:")
    print("="*80)
    print(f"  Network: {'TESTNET' if use_testnet else '⚠️  MAINNET ⚠️'}")
    print(f"  Auto-Trading: {'✅ ENABLED' if auto_trade else '❌ DISABLED (Monitor Only)'}")
    print(f"  Scalping Mode: {scalping_mode.upper()}")
    print(f"  Position Size: {position_size_pct*100:.1f}% of account per trade")
    print(f"  Leverage: {leverage}x")
    if scalping_mode == 'conservative':
        print(f"  Take Profit: {take_profit_pct:.1f}% account profit ({take_profit_pct/leverage:.2f}% price move)")
        print(f"  Protection Trigger: {profit_trigger:.2f}% price (~{profit_trigger*leverage:.1f}% account)")
        print(f"  Protection Secures: {secure_profit:.2f}% price (~{secure_profit*leverage:.1f}% account)")
    else:
        print(f"  TP1 (50%): 10% account (0.4% price) | TP2 (100%): 20% account (0.8% price)")
        print(f"  Hard Stop: -0.15% price (-3.75% account)")
        print(f"  Protection: +0.12% trigger → +0.05% secure")
    print("="*80)
    
    confirm = input("\n✅ Start bot with these settings? (yes/no) [Press Enter for yes]: ").strip().lower()
    if confirm in ['no', 'n']:
        print("\n✓ Cancelled")
        return
    
    print("\n" + "="*80)
    print("Starting system...")
    print("="*80 + "\n")
    
    # Create and run with custom settings
    system = AutoTradingSystem(
        private_key=private_key,
        use_testnet=use_testnet,
        auto_trade=auto_trade,
        position_size_pct=position_size_pct,
        leverage=leverage,
        take_profit_pct=take_profit_pct,
        profit_trigger=profit_trigger,
        secure_profit=secure_profit,
        scalping_mode=scalping_mode
    )
    system.monitor()


if __name__ == "__main__":
    main()