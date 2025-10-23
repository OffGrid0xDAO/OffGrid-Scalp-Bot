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
import numpy as np

# Import Claude trader
from claude_trader import ClaudeTrader

# Import Telegram notifier
from telegram_notifier import TelegramNotifier

# Import continuous learning module
from continuous_learning import ContinuousLearning

# Import EMA derivative analyzer
from ema_derivative_analyzer import EMADerivativeAnalyzer

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
                 position_size_pct=0.10, leverage=25, min_confidence=0.75,
                 timeframe_short=5, timeframe_long=15):
        """Initialize dual-timeframe bot"""
        self.private_key = private_key
        self.use_testnet = use_testnet
        self.auto_trade = auto_trade
        self.symbol = 'ETH'
        self.leverage = leverage
        self.position_size_pct = position_size_pct
        self.min_confidence = min_confidence

        # Timeframe configuration
        self.timeframe_short = timeframe_short  # e.g., 1, 3, 5
        self.timeframe_long = timeframe_long    # e.g., 3, 5, 15

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

        # Candle-based decision making (CRITICAL FIX for over-trading!)
        self.last_5min_candle = None
        self.last_15min_candle = None

        # Trade cooldown to prevent over-trading
        self.last_trade_time = None
        self.trade_cooldown = 1800  # 30 minutes between trades

        # Order tracking for TP/SL management
        self.active_tp_order = None  # Take profit order ID
        self.active_sl_order = None  # Stop loss order ID
        self.last_sl_price = None    # Track last stop loss price to avoid unnecessary updates

        # Position tracking for exchange-side closes
        self.last_position_side = None  # Track position direction
        self.last_position_entry = None  # Track entry price
        self.last_position_size = None   # Track position size

        # Commentary tracking
        self.last_commentary_time = None
        self.commentary_interval = 600  # 10 minutes in seconds
        self.last_commentary = None

        # API call optimization
        self.last_api_call_time = None
        self.min_api_call_interval = 60  # Minimum 60 seconds between Claude calls (no position)
        self.position_check_interval = 120  # Check less frequently when in position (2 minutes)
        self.last_check_state = {'5min': None, '15min': None}  # Track state changes
        self.api_calls_saved = 0  # Track how many calls we saved
        self.total_api_calls = 0  # Track total calls made

        # Ribbon transition tracking (for RuleBasedTrader freshness check)
        self.last_ribbon_state_5min = None
        self.last_ribbon_state_15min = None
        self.ribbon_transition_time_5min = None
        self.ribbon_transition_time_15min = None

        # Position management
        self.position_entry_time = None  # Track when we entered position

        # Continuous learning module
        self.learning = ContinuousLearning()
        self.last_learning_update = None
        self.learning_interval = 3600  # Run analysis every hour (in seconds)
        self.initial_training_done = False  # Track if initial training completed
        self.min_hold_time = 900  # Minimum 15 minutes (900 seconds) - backtest shows 15-20min optimal!
        self.yellow_ema_violation_count = 0  # Track consecutive yellow EMA violations
        self.yellow_ema_violations_needed = 3  # Need 3 consecutive violations to exit (30 seconds)

        # EMA Derivative analyzers (one for each timeframe)
        self.derivative_analyzer_5min = EMADerivativeAnalyzer(lookback_periods=10)
        self.derivative_analyzer_15min = EMADerivativeAnalyzer(lookback_periods=10)

        # Data logging
        self.setup_data_logging()

        # Initialize Claude trader
        try:
            self.claude = ClaudeTrader()
            print("✅ Claude AI trader initialized")
        except Exception as e:
            print(f"⚠️  Claude initialization failed: {e}")
            self.claude = None

        # Initialize Telegram notifier
        try:
            self.telegram = TelegramNotifier()
        except Exception as e:
            print(f"⚠️  Telegram initialization failed: {e}")
            self.telegram = None

        # Market analysis notifications
        self.market_analysis_interval = int(os.getenv('MARKET_ANALYSIS_INTERVAL', 30)) * 60  # Convert minutes to seconds
        self.last_market_analysis_time = None

        # Initialize Hyperliquid connection
        self.reconnect_hyperliquid()

    def setup_data_logging(self):
        """Setup CSV logging for both timeframes - continuous files"""
        self.data_dir = Path("trading_data")
        self.data_dir.mkdir(exist_ok=True)

        # Use continuous files (not per-session)
        # This allows historical data to accumulate across sessions
        self.ema_data_5min_file = self.data_dir / "ema_data_5min.csv"
        self.ema_data_15min_file = self.data_dir / "ema_data_15min.csv"
        self.trading_decisions_file = self.data_dir / "claude_decisions.csv"

        # Initialize CSV headers ONLY if files don't exist
        for file_path in [self.ema_data_5min_file, self.ema_data_15min_file]:
            if not file_path.exists():
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'price', 'ribbon_state'])
                print(f"📝 Created new data file: {file_path.name}")
            else:
                print(f"📂 Using existing data file: {file_path.name}")

        # Trading decisions CSV - ALWAYS verify/recreate header
        header_row = [
            'timestamp',
            'action_type',
            'direction',
            'entry_recommended',
            'confidence_score',
            'reasoning',
            'entry_price',
            'stop_loss',
            'take_profit',
            'yellow_ema_stop',
            'position_management',
            'exit_recommended',
            'outer_bands_spreading',
            'timeframe_alignment',
            'executed'
        ]

        # Check if file exists and has correct header
        needs_new_header = False
        if not self.trading_decisions_file.exists():
            needs_new_header = True
            print(f"📝 Creating new decisions file: {self.trading_decisions_file.name}")
        else:
            # Check if existing header matches
            try:
                with open(self.trading_decisions_file, 'r', newline='') as f:
                    reader = csv.reader(f)
                    existing_header = next(reader, None)
                    if existing_header != header_row:
                        # Backup old file and create new one
                        backup_file = self.data_dir / f"claude_decisions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        self.trading_decisions_file.rename(backup_file)
                        needs_new_header = True
                        print(f"📦 Old file backed up to: {backup_file.name}")
                        print(f"📝 Creating new decisions file with updated columns")
                    else:
                        print(f"📂 Using existing decisions file: {self.trading_decisions_file.name}")
            except Exception as e:
                print(f"⚠️  Error checking header: {e}")
                needs_new_header = True

        if needs_new_header:
            with open(self.trading_decisions_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header_row)
            print(f"✅ Header written to {self.trading_decisions_file.name}")

        print(f"📁 Data logging initialized: {self.data_dir}")

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
        print("\n🚀 Opening TradingView charts with Annii's Ribbon indicator...")
        print("   The indicator will be loaded automatically on both charts.")
        print("   Please wait while the browsers load...")
        print("="*80 + "\n")

        # Base chart URL with ETH/USD and the indicator already added
        # Format: chart URL + interval parameter + indicator
        base_chart_url = "https://www.tradingview.com/chart/gsKW80Wm/?symbol=BINANCE%3AETHUSD"
        indicator_script = "JvAOl84K-Ribbon-for-Scalping-5-to-15-min-timeframes"

        # Chart URLs with different timeframes (dynamic based on selection)
        chart_short_url = f"{base_chart_url}&interval={self.timeframe_short}"
        chart_long_url = f"{base_chart_url}&interval={self.timeframe_long}"

        # Setup short timeframe browser
        print(f"🔷 Opening Browser 1 ({self.timeframe_short}-minute chart)...")
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_argument('--window-position=0,0')
        chrome_options.add_argument('--window-size=960,1080')
        # Prevent browser from sleeping/throttling
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_experimental_option('prefs', {
            'profile.default_content_setting_values.automatic_downloads': 1,
        })

        self.driver_5min = webdriver.Chrome(options=chrome_options)
        self.driver_5min.get(chart_short_url)
        print(f"   ✅ {self.timeframe_short}-minute chart loaded with indicator")
        time.sleep(3)

        # Setup long timeframe browser
        print(f"🔶 Opening Browser 2 ({self.timeframe_long}-minute chart)...")
        chrome_options_15 = Options()
        chrome_options_15.add_argument('--no-sandbox')
        chrome_options_15.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options_15.add_argument('--window-position=960,0')
        chrome_options_15.add_argument('--window-size=960,1080')
        # Prevent browser from sleeping/throttling
        chrome_options_15.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options_15.add_argument('--disable-renderer-backgrounding')
        chrome_options_15.add_argument('--disable-background-timer-throttling')
        chrome_options_15.add_argument('--disable-ipc-flooding-protection')
        chrome_options_15.add_experimental_option('prefs', {
            'profile.default_content_setting_values.automatic_downloads': 1,
        })

        self.driver_15min = webdriver.Chrome(options=chrome_options_15)
        self.driver_15min.get(chart_long_url)
        print(f"   ✅ {self.timeframe_long}-minute chart loaded with indicator")
        time.sleep(3)

        print("\n" + "="*80)
        print("📊 BOTH CHARTS READY!")
        print("="*80)
        print("\n⚠️  IMPORTANT: Check that:")
        print("   1. Both charts show ETH/USD on Binance")
        print("   2. Annii's Ribbon indicator is visible with all EMAs")
        print(f"   3. Left browser = {self.timeframe_short}-minute timeframe")
        print(f"   4. Right browser = {self.timeframe_long}-minute timeframe")
        print("\n   If the indicator didn't load automatically, you may need to:")
        print("   - Log in to TradingView")
        print("   - Manually add the indicator from your favorites/library")
        print("="*80)

        input("\n👉 Press ENTER when both charts are ready and showing data: ")
        print("\n✅ Both browsers confirmed ready!")

    def keep_browser_awake(self, driver):
        """
        Keep the browser awake by interacting with the page
        This prevents Chrome from throttling or going idle

        Multiple techniques used:
        1. Execute JavaScript to keep JS engine active
        2. Micro-scroll to trigger rendering
        3. Query DOM to keep layout engine active
        4. Touch body element to simulate activity
        """
        try:
            # 1. Execute JavaScript to keep the page active
            driver.execute_script("return document.title;")

            # 2. Micro-scroll to trigger re-rendering (works even when minimized)
            driver.execute_script("window.scrollBy(0, 1); window.scrollBy(0, -1);")

            # 3. Query DOM to keep layout engine active
            driver.execute_script("return document.body.clientHeight;")

            # 4. Simulate mouse movement over body (keeps browser thinking user is active)
            driver.execute_script("""
                var event = new MouseEvent('mousemove', {
                    view: window,
                    bubbles: true,
                    cancelable: true
                });
                document.body.dispatchEvent(event);
            """)

            # 5. Refresh a timestamp in the page to prevent staleness detection
            driver.execute_script("window._lastActivity = Date.now();")

        except Exception as e:
            print(f"⚠️  Browser wake-up warning: {e}")

    def periodic_browser_keepalive(self):
        """
        Periodic keep-alive thread to prevent browsers from sleeping
        Runs every 15 seconds with aggressive anti-sleep measures

        This is SEPARATE from the read_indicators keep-alive to ensure
        browsers stay active even if reading fails
        """
        keepalive_interval = 15  # More frequent: every 15 seconds

        while self.running:
            try:
                time.sleep(keepalive_interval)

                # Wake up 5min browser with multiple techniques
                if self.driver_5min:
                    try:
                        # Execute multiple commands to keep all browser subsystems active
                        self.driver_5min.execute_script("console.log('keepalive-5min');")
                        self.driver_5min.execute_script("window.scrollBy(0, 2); window.scrollBy(0, -2);")
                        self.driver_5min.execute_script("document.body.clientHeight;")
                        # Keep WebDriver connection alive
                        self.driver_5min.title  # Simple property access
                    except Exception as e:
                        print(f"⚠️  5min browser keepalive failed: {e}")

                # Wake up 15min browser with multiple techniques
                if self.driver_15min:
                    try:
                        # Execute multiple commands to keep all browser subsystems active
                        self.driver_15min.execute_script("console.log('keepalive-15min');")
                        self.driver_15min.execute_script("window.scrollBy(0, 2); window.scrollBy(0, -2);")
                        self.driver_15min.execute_script("document.body.clientHeight;")
                        # Keep WebDriver connection alive
                        self.driver_15min.title  # Simple property access
                    except Exception as e:
                        print(f"⚠️  15min browser keepalive failed: {e}")

            except Exception as e:
                if self.running:
                    print(f"⚠️  Keepalive thread error: {e}")

    def read_indicators(self, driver):
        """Read indicators from TradingView"""
        try:
            # Wake up the browser before reading
            self.keep_browser_awake(driver)

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

                        # IMPROVED Color detection logic with better dark EMA distinction
                        # Yellow EMAs (support/resistance)
                        if r > 150 and g > 150 and r + g > 300:
                            color = 'yellow'
                            intensity = 'normal'

                        # Green EMAs - classify by intensity (only light or dark)
                        elif g > r * 1.3 and g > b * 1.3:  # Green dominant
                            color = 'green'
                            # LIGHT = bright/saturated (high G value) = STRONG momentum, full commitment
                            # DARK = dim/less saturated (low G value) = WEAK momentum, early transition
                            # Flow: all red → dark green (deciding) → light green (committed)
                            intensity = 'light' if g >= 150 else 'dark'

                        # Red EMAs - classify by intensity (only light or dark)
                        elif r > g * 1.3 and r > b * 1.3:  # Red dominant
                            color = 'red'
                            # LIGHT = bright/saturated (high R value) = STRONG momentum, full commitment
                            # DARK = dim/less saturated (low R value) = WEAK momentum, early transition
                            # Flow: all green → dark red (deciding) → light red (committed)
                            intensity = 'light' if r >= 150 else 'dark'

                        # Gray EMAs (neutral/dead)
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
                            'intensity': intensity,
                            'rgb': (r, g, b)  # Store raw RGB values for Claude
                        }
                    else:
                        # No RGB found - store with default values
                        indicators[title] = {
                            'value': value,
                            'price': price,
                            'color': 'unknown',
                            'intensity': 'normal',
                            'rgb': (0, 0, 0)  # Black/unknown
                        }
                except:
                    continue

            return indicators
        except Exception as e:
            print(f"⚠️  Error reading indicators: {e}")
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

        # Calculate totals for state detection
        # Include gray EMAs in total (they're neutral but still part of the ribbon)
        total_directional_emas = len(green_emas) + len(red_emas) + len(gray_emas)

        # IMPROVED STATE DETECTION:
        # - 85%+ = ALL_GREEN or ALL_RED (true alignment, ready to trade)
        # - 50-84% = MIXED_GREEN or MIXED_RED (predominant, but not confirmed)
        # - <50% = MIXED (no clear direction)
        # - Includes dark EMA analysis for momentum confirmation

        if total_directional_emas == 0:
            # No non-yellow EMAs to analyze
            state = 'unknown'
            entry_strength = 'none'
        elif len(green_emas) >= total_directional_emas * 0.85:  # 85%+ green
            state = 'all_green'
            # LIGHT EMAs = bright/saturated = STRONG momentum (fully committed)
            # DARK EMAs = dim/weak = EARLY transition (still deciding)
            light_green_count = len([ema for ema in green_emas if ema.get('intensity') == 'light'])
            if light_green_count >= 2:
                entry_strength = 'strong'  # Light green EMAs = full momentum! ✅
            else:
                entry_strength = 'building'  # Mostly dark = still deciding/building
        elif len(green_emas) >= total_directional_emas * 0.5:  # 50-84% green
            state = 'mixed_green'  # Predominant green, not confirmed yet
            entry_strength = 'building'  # Watching, not ready
        elif len(red_emas) >= total_directional_emas * 0.85:  # 85%+ red
            state = 'all_red'
            # LIGHT EMAs = bright/saturated = STRONG momentum (fully committed)
            # DARK EMAs = dim/weak = EARLY transition (still deciding)
            light_red_count = len([ema for ema in red_emas if ema.get('intensity') == 'light'])
            if light_red_count >= 2:
                entry_strength = 'strong'  # Light red EMAs = full momentum! ✅
            else:
                entry_strength = 'building'  # Mostly dark = still deciding/building
        elif len(red_emas) >= total_directional_emas * 0.5:  # 50-84% red
            state = 'mixed_red'  # Predominant red, not confirmed yet
            entry_strength = 'building'  # Watching, not ready
        else:
            # Too mixed, no clear direction
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

    def calculate_ema_derivatives(self, indicators, derivative_analyzer):
        """
        Calculate slope, acceleration, and inflection points for all EMAs

        Args:
            indicators: Dict of indicators from chart
            derivative_analyzer: EMADerivativeAnalyzer instance for this timeframe

        Returns:
            Dict with derivative data for each EMA and overall compression state
        """
        timestamp = datetime.now()
        derivatives = {}

        # Extract EMA periods from indicator names
        mma_indicators = {k: v for k, v in indicators.items() if k.startswith('MMA')}

        for name, data in mma_indicators.items():
            # Extract EMA period number
            match = re.search(r'\d+', name)
            if not match:
                continue

            ema_period = int(match.group())

            # Get EMA value
            try:
                ema_value = float(data.get('value', 0))
                if ema_value <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            # Add value to history
            derivative_analyzer.add_ema_value(ema_period, timestamp, ema_value)

            # Calculate derivatives
            derivative_info = derivative_analyzer.calculate_realtime_derivatives(ema_period)

            # Store in derivatives dict
            derivatives[f'MMA{ema_period}'] = derivative_info

        # Calculate compression state (how tight/wide are the EMAs)
        compression_info = self.calculate_compression_state(mma_indicators)
        derivatives['compression'] = compression_info

        # Detect if there are any significant inflection points (early warning signals)
        inflection_signals = self.detect_inflection_signals(derivatives)
        derivatives['inflection_signals'] = inflection_signals

        return derivatives

    def calculate_compression_state(self, mma_indicators):
        """
        Calculate how compressed/expanded the EMA ribbon is

        Returns:
            Dict with compression metrics
        """
        ema_values = []

        for name, data in mma_indicators.items():
            try:
                val = float(data.get('value', 0))
                if val > 0:
                    ema_values.append(val)
            except (ValueError, TypeError):
                continue

        if len(ema_values) < 2:
            return {
                'state': 'unknown',
                'value': 0.0,
                'spread_pct': 0.0
            }

        # Calculate compression as coefficient of variation (std / mean)
        mean_ema = np.mean(ema_values)
        std_ema = np.std(ema_values)

        compression = (std_ema / mean_ema) * 100 if mean_ema > 0 else 0

        # Calculate spread
        spread = max(ema_values) - min(ema_values)
        spread_pct = (spread / min(ema_values)) * 100 if min(ema_values) > 0 else 0

        # Classify compression state
        if compression < 0.1:
            state = 'highly_compressed'
        elif compression < 0.2:
            state = 'compressed'
        elif compression < 0.4:
            state = 'normal'
        elif compression < 0.8:
            state = 'expanding'
        else:
            state = 'highly_expanded'

        return {
            'state': state,
            'value': round(compression, 4),
            'spread_pct': round(spread_pct, 4)
        }

    def detect_inflection_signals(self, derivatives):
        """
        Detect significant inflection points across EMAs (early warning signals)

        Returns:
            Dict with inflection signal info
        """
        bullish_inflections = []
        bearish_inflections = []
        bullish_accelerations = []
        bearish_accelerations = []

        for ema_name, deriv_data in derivatives.items():
            if not isinstance(deriv_data, dict) or 'inflection_type' not in deriv_data:
                continue

            inflection_type = deriv_data['inflection_type']
            inflection_strength = deriv_data.get('inflection_strength', 0)

            if inflection_type == 'bullish_inflection':
                bullish_inflections.append({
                    'ema': ema_name,
                    'strength': inflection_strength
                })
            elif inflection_type == 'bearish_inflection':
                bearish_inflections.append({
                    'ema': ema_name,
                    'strength': inflection_strength
                })
            elif inflection_type == 'bullish_acceleration':
                bullish_accelerations.append({
                    'ema': ema_name,
                    'strength': inflection_strength
                })
            elif inflection_type == 'bearish_acceleration':
                bearish_accelerations.append({
                    'ema': ema_name,
                    'strength': inflection_strength
                })

        # Determine if there's a strong signal
        signal_type = 'none'
        signal_strength = 0

        if len(bullish_inflections) >= 2 or len(bullish_accelerations) >= 3:
            signal_type = 'bullish'
            signal_strength = len(bullish_inflections) + len(bullish_accelerations)
        elif len(bearish_inflections) >= 2 or len(bearish_accelerations) >= 3:
            signal_type = 'bearish'
            signal_strength = len(bearish_inflections) + len(bearish_accelerations)

        return {
            'type': signal_type,
            'strength': signal_strength,
            'bullish_inflections': len(bullish_inflections),
            'bearish_inflections': len(bearish_inflections),
            'bullish_accelerations': len(bullish_accelerations),
            'bearish_accelerations': len(bearish_accelerations)
        }

    def detect_fresh_transition(self):
        """
        Detect if we have a FRESH transition (state flip) on either timeframe.
        Returns: (has_transition, transition_info)
        """
        state_5min = self.data_5min['state']
        state_15min = self.data_15min['state']

        transition_5min = None
        transition_15min = None

        # Check 5min transition (track all directional states including mixed_green/mixed_red)
        if state_5min in ['all_green', 'all_red', 'mixed_green', 'mixed_red']:
            if self.last_solid_state_5min is None:
                # First time seeing a directional state - just record it, don't trade yet
                self.last_solid_state_5min = state_5min
            elif self.last_solid_state_5min != state_5min:
                # State changed! This is a transition
                transition_5min = f"{self.last_solid_state_5min} → {state_5min}"
                self.last_solid_state_5min = state_5min
                self.warmup_complete = True

        # Check 15min transition (track all directional states including mixed_green/mixed_red)
        if state_15min in ['all_green', 'all_red', 'mixed_green', 'mixed_red']:
            if self.last_solid_state_15min is None:
                # First time seeing a directional state - just record it, don't trade yet
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
        consecutive_failures = 0
        max_failures_before_refresh = 3

        while self.running:
            try:
                # Read indicators
                indicators = self.read_indicators(driver)

                if not indicators:
                    consecutive_failures += 1
                    print(f"⚠️  {timeframe}: No indicators read (attempt {consecutive_failures}/{max_failures_before_refresh})")

                    # REMOVED: Auto-refresh - it loses chart state and causes gaps
                    # Instead: Rely on aggressive keep-alive and error recovery
                    # If failures persist, it means there's a bigger issue that needs manual intervention

                    if consecutive_failures >= max_failures_before_refresh:
                        print(f"❌ {timeframe}: Persistent failures detected! Check browser window manually.")
                        print(f"   Tip: Ensure browser window is visible (not minimized) for best reliability")
                        # Don't refresh - keep trying with existing page

                    time.sleep(update_interval)
                    continue

                # Reset failure counter on success
                consecutive_failures = 0

                # Analyze ribbon
                state, ema_groups, mma_indicators = self.analyze_ribbon(indicators)

                # Get price
                current_price = self.get_current_price(driver)

                # Detect manipulation wicks (liquidity grabs)
                wick_signal = self.detect_manipulation_wick(indicators, current_price, state, data_store)

                # Calculate EMA derivatives (slope, acceleration, inflection)
                derivative_analyzer = self.derivative_analyzer_5min if timeframe == '5min' else self.derivative_analyzer_15min
                derivatives = self.calculate_ema_derivatives(indicators, derivative_analyzer)

                # Update data store
                data_store['indicators'] = indicators
                data_store['state'] = state
                data_store['ema_groups'] = ema_groups
                data_store['price'] = current_price
                data_store['last_update'] = datetime.now()
                data_store['wick_signal'] = wick_signal  # Add wick detection
                data_store['derivatives'] = derivatives  # Add derivative data

                # Add to history
                data_store['history'].append({
                    'timestamp': time.time(),
                    'price': current_price,
                    'state': state,
                    'ema_groups': ema_groups,
                    'wick_signal': wick_signal,
                    'derivatives': derivatives
                })

                # Log to CSV (now includes derivatives)
                self.log_ema_data(indicators, current_price, state, log_file, derivatives)

                print(f"✅ {timeframe} updated: {state.upper()} @ ${current_price:.2f}" if current_price else f"✅ {timeframe} updated: {state.upper()}")

            except Exception as e:
                print(f"⚠️  Error updating {timeframe}: {e}")

            time.sleep(update_interval)

    def detect_manipulation_wick(self, indicators, current_price, state, data_store):
        """
        Detect manipulation wicks (liquidity grabs) - Best scalping entry opportunities!

        When price wicks below all EMAs (LONG) or above all EMAs (SHORT), it's often
        a stop hunt followed by a strong reversal.

        Returns:
            Dict with wick signal info or None
        """
        if not current_price or current_price == 0:
            return None

        try:
            # Get all EMA values (exclude non-EMA indicators)
            ema_values = []
            for key, data in indicators.items():
                if key.startswith('MMA') and 'value' in data:
                    try:
                        val = float(data['value'])
                        if val > 0:
                            ema_values.append(val)
                    except:
                        continue

            if len(ema_values) < 8:  # Need sufficient EMAs
                return None

            # Find EMA ribbon boundaries
            highest_ema = max(ema_values)
            lowest_ema = min(ema_values)
            ema_spread = highest_ema - lowest_ema

            # Calculate wick deviation as % from ribbon edge
            wick_below = ((lowest_ema - current_price) / lowest_ema * 100) if current_price < lowest_ema else 0
            wick_above = ((current_price - highest_ema) / highest_ema * 100) if current_price > highest_ema else 0

            # BULLISH WICK SIGNAL: Price wicked below all EMAs (liquidity grab down)
            if wick_below >= 0.3 and wick_below <= 0.8 and 'red' in state.lower():
                # Check if price is recovering (need recent history)
                history = data_store.get('history', [])
                if len(history) >= 2:
                    prev_price = history[-1]['price'] if history[-1]['price'] else history[-2]['price']

                    # Price recovering back toward EMAs = reversal confirmation
                    if current_price > prev_price:
                        return {
                            'type': 'BULLISH_WICK',
                            'direction': 'LONG',
                            'wick_size_pct': round(wick_below, 3),
                            'lowest_ema': round(lowest_ema, 2),
                            'current_price': round(current_price, 2),
                            'confidence_boost': 20,  # +20% confidence for Claude
                            'description': f'Liquidity grab: Price wicked {wick_below:.2f}% below ribbon, now recovering'
                        }

            # BEARISH WICK SIGNAL: Price wicked above all EMAs (liquidity grab up)
            elif wick_above >= 0.3 and wick_above <= 0.8 and 'green' in state.lower():
                # Check if price is recovering
                history = data_store.get('history', [])
                if len(history) >= 2:
                    prev_price = history[-1]['price'] if history[-1]['price'] else history[-2]['price']

                    # Price recovering back toward EMAs = reversal confirmation
                    if current_price < prev_price:
                        return {
                            'type': 'BEARISH_WICK',
                            'direction': 'SHORT',
                            'wick_size_pct': round(wick_above, 3),
                            'highest_ema': round(highest_ema, 2),
                            'current_price': round(current_price, 2),
                            'confidence_boost': 20,  # +20% confidence for Claude
                            'description': f'Liquidity grab: Price wicked {wick_above:.2f}% above ribbon, now recovering'
                        }

            return None

        except Exception as e:
            print(f"⚠️  Error detecting wick: {e}")
            return None

    def should_check_for_new_candle(self):
        """
        CRITICAL FIX: Only make trading decisions on candle close!

        Problem: Bot was analyzing every 10-second update, causing 35 trades in 8 hours.
        Solution: Only ask Claude when a NEW CANDLE CLOSES (5min or 15min).

        Returns:
            bool: True if a new candle just closed
        """
        current_time = time.time()

        # Calculate current candle timestamps
        current_5min_candle = int(current_time / 300) * 300  # 5min = 300 seconds
        current_15min_candle = int(current_time / 900) * 900  # 15min = 900 seconds

        # Check if new candle closed
        new_5min = (current_5min_candle != self.last_5min_candle)
        new_15min = (current_15min_candle != self.last_15min_candle)

        # Update trackers
        if new_5min:
            self.last_5min_candle = current_5min_candle
            print(f"🕯️  {self.timeframe_short}min candle closed @ {datetime.fromtimestamp(current_5min_candle).strftime('%H:%M:%S')}")
        if new_15min:
            self.last_15min_candle = current_15min_candle
            print(f"🕯️  {self.timeframe_long}min candle closed @ {datetime.fromtimestamp(current_15min_candle).strftime('%H:%M:%S')}")

        return new_5min or new_15min

    def can_enter_new_trade(self):
        """
        Check if trade cooldown has expired.

        Problem: Bot was entering too many trades too quickly.
        Solution: Minimum 30 minutes between trades.

        Returns:
            bool: True if cooldown expired, False otherwise
        """
        if self.last_trade_time is None:
            return True

        time_since_last = time.time() - self.last_trade_time

        if time_since_last < self.trade_cooldown:
            remaining = (self.trade_cooldown - time_since_last) / 60
            # Don't print on every check, only occasionally
            if int(time_since_last) % 60 == 0:  # Every minute
                print(f"⏸️  Trade cooldown: {remaining:.1f} minutes remaining")
            return False

        return True

    def is_high_quality_setup(self, direction, confidence, data_5min, data_15min):
        """
        Filter for HIGH-QUALITY trade setups only.

        Problem: Bot was taking low-quality trades with poor win rate.
        Solution: Strict quality filters - only take the BEST setups.

        Criteria:
        1. High confidence (85%+ or 90%+ without wick)
        2. Timeframe alignment (both trending same direction)
        3. Wick signal preferred
        4. No conflicting signals

        Returns:
            tuple: (bool, str) - (is_quality, reason)
        """
        # Require high confidence
        if confidence < 0.85:
            return False, f"⛔ Confidence {confidence:.0%} < 85% minimum"

        # Check timeframe alignment
        state_5min = data_5min['state'].lower()
        state_15min = data_15min['state'].lower()

        if direction == 'LONG':
            # SCALPING FIX: Accept mixed_green states (not just all_green!)
            # This allows early entries on dark transitions and reversals
            is_bullish_5min = any(x in state_5min for x in ['all_green', 'mixed_green'])
            is_bullish_15min = any(x in state_15min for x in ['all_green', 'mixed_green', 'mixed'])

            # REJECT only if BOTH timeframes are clearly bearish
            is_bearish_5min = 'all_red' in state_5min
            is_bearish_15min = 'all_red' in state_15min

            if is_bearish_5min and is_bearish_15min:
                return False, "⛔ Both timeframes bearish (all_red)"

            # If neither timeframe shows bullish momentum, reject
            if not (is_bullish_5min or is_bullish_15min):
                return False, "⛔ No bullish momentum detected"

            # SPECIAL CASE: Early Reversal (PATH D/E)
            # If we have 15+ LIGHT green EMAs, this is a strong signal even if ribbon not fully green!
            ema_groups_5min = data_5min.get('ema_groups', {})
            green_emas = ema_groups_5min.get('green', [])
            light_green_count = len([e for e in green_emas if e.get('intensity') == 'light'])

            if light_green_count >= 15:
                return True, f"✅ STRONG EARLY REVERSAL: {light_green_count} LIGHT green EMAs (PATH D/E override)"

        elif direction == 'SHORT':
            # SCALPING FIX: Accept mixed_red states (not just all_red!)
            # This allows early entries on dark transitions and reversals
            is_bearish_5min = any(x in state_5min for x in ['all_red', 'mixed_red'])
            is_bearish_15min = any(x in state_15min for x in ['all_red', 'mixed_red', 'mixed'])

            # REJECT only if BOTH timeframes are clearly bullish
            is_bullish_5min = 'all_green' in state_5min
            is_bullish_15min = 'all_green' in state_15min

            if is_bullish_5min and is_bullish_15min:
                return False, "⛔ Both timeframes bullish (all_green)"

            # If neither timeframe shows bearish momentum, reject
            if not (is_bearish_5min or is_bearish_15min):
                return False, "⛔ No bearish momentum detected"

            # SPECIAL CASE: Early Reversal (PATH D/E)
            # If we have 15+ LIGHT red EMAs, this is a strong signal even if ribbon not fully red!
            ema_groups_5min = data_5min.get('ema_groups', {})
            red_emas = ema_groups_5min.get('red', [])
            light_red_count = len([e for e in red_emas if e.get('intensity') == 'light'])

            if light_red_count >= 15:
                return True, f"✅ STRONG EARLY REVERSAL: {light_red_count} LIGHT red EMAs (PATH D/E override)"

        # Check for wick signal (strongly preferred)
        wick_5min = data_5min.get('wick_signal')
        wick_15min = data_15min.get('wick_signal')
        has_wick = wick_5min or wick_15min

        # Without wick, require 90% confidence
        if not has_wick and confidence < 0.90:
            return False, f"⛔ No wick signal - need 90% confidence (have {confidence:.0%})"

        # All checks passed!
        wick_info = ""
        if has_wick:
            wick_type = wick_5min['type'] if wick_5min else wick_15min['type']
            wick_size = wick_5min['wick_size_pct'] if wick_5min else wick_15min['wick_size_pct']
            wick_info = f" + {wick_type} ({wick_size:.2f}% wick)"

        return True, f"✅ High-quality setup: {confidence:.0%} confidence{wick_info}"

    def log_ema_data(self, indicators, current_price, state, log_file, derivatives=None):
        """
        Log EMA data to CSV including derivatives (slope, acceleration, inflection)

        Args:
            indicators: EMA indicator data
            current_price: Current price
            state: Ribbon state
            log_file: CSV file path
            derivatives: Dict with derivative data for each EMA (optional)
        """
        try:
            timestamp = datetime.now().isoformat()
            mma_indicators = {k: v for k, v in indicators.items() if k.startswith('MMA')}

            def get_num(key):
                m = re.search(r'\d+', key)
                return int(m.group()) if m else 0

            sorted_mma = sorted(mma_indicators.items(), key=lambda x: get_num(x[0]))

            # Build row with basic data
            row = [timestamp, current_price, state]

            # Add compression data if available
            if derivatives and 'compression' in derivatives:
                comp = derivatives['compression']
                row.extend([
                    comp.get('state', 'unknown'),
                    comp.get('value', 0.0),
                    comp.get('spread_pct', 0.0)
                ])
            else:
                row.extend(['unknown', 0.0, 0.0])

            # Add inflection signal summary if available
            if derivatives and 'inflection_signals' in derivatives:
                signals = derivatives['inflection_signals']
                row.extend([
                    signals.get('type', 'none'),
                    signals.get('strength', 0),
                    signals.get('bullish_inflections', 0),
                    signals.get('bearish_inflections', 0),
                    signals.get('bullish_accelerations', 0),
                    signals.get('bearish_accelerations', 0)
                ])
            else:
                row.extend(['none', 0, 0, 0, 0, 0])

            # Add EMA data with derivatives
            for name, data in sorted_mma:
                ema_num = get_num(name)
                ema_key = f'MMA{ema_num}'

                # Basic EMA data
                row.extend([
                    data.get('value', 'N/A'),
                    data.get('color', 'unknown'),
                    data.get('intensity', 'normal')
                ])

                # Derivative data if available
                if derivatives and ema_key in derivatives:
                    deriv = derivatives[ema_key]
                    row.extend([
                        deriv.get('slope', 0.0),
                        deriv.get('slope_color', 'gray'),
                        deriv.get('acceleration', 0.0),
                        deriv.get('inflection_type', 'none'),
                        deriv.get('inflection_strength', 0.0)
                    ])
                else:
                    row.extend([0.0, 'gray', 0.0, 'none', 0.0])

            with open(log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)

            # Update headers if first data row
            with open(log_file, 'r') as f:
                lines = f.readlines()
                if len(lines) == 2:
                    header = [
                        'timestamp', 'price', 'ribbon_state',
                        'compression_state', 'compression_value', 'compression_spread_pct',
                        'inflection_signal_type', 'inflection_signal_strength',
                        'bullish_inflections', 'bearish_inflections',
                        'bullish_accelerations', 'bearish_accelerations'
                    ]

                    for name, _ in sorted_mma:
                        ema_num = get_num(name)
                        header.extend([
                            f'MMA{ema_num}_value',
                            f'MMA{ema_num}_color',
                            f'MMA{ema_num}_intensity',
                            f'MMA{ema_num}_slope',
                            f'MMA{ema_num}_slope_color',
                            f'MMA{ema_num}_acceleration',
                            f'MMA{ema_num}_inflection_type',
                            f'MMA{ema_num}_inflection_strength'
                        ])

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
                           reasoning, targets, executed, action_type='decision'):
        """
        Log Claude's trading decision to CSV with proper formatting

        Args:
            action_type: 'decision' for normal decisions, 'exit' for exit decisions
        """
        try:
            with open(self.trading_decisions_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)

                # Clean up reasoning for CSV (remove extra newlines but keep structure)
                cleaned_reasoning = reasoning.strip().replace('\n', ' | ')

                writer.writerow([
                    datetime.now().isoformat(),
                    action_type,
                    direction,
                    entry_recommended,
                    f"{confidence_score:.3f}",  # Format to 3 decimal places
                    cleaned_reasoning,  # FULL reasoning with | separators
                    f"{targets.get('entry_price', 0):.2f}",
                    f"{targets.get('stop_loss', 0):.2f}",
                    f"{targets.get('take_profit', 0):.2f}",
                    f"{targets.get('yellow_ema_stop', 0):.2f}",
                    targets.get('position_management', 'HOLD'),
                    targets.get('exit_recommended', 'NO'),
                    str(targets.get('outer_bands_spreading', False)),
                    targets.get('timeframe_alignment', 'UNKNOWN'),
                    str(executed)
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
                # LONG: TP above entry, SL BELOW entry
                tp_price = entry_price * 1.015  # 1.5% TP

                # Validate yellow EMA is below entry for LONG (proper stop direction)
                if yellow_ema_stop > 0 and yellow_ema_stop < entry_price:
                    sl_price = yellow_ema_stop  # Use yellow EMA if it's below entry
                else:
                    sl_price = entry_price * 0.995  # Fallback: 0.5% below entry
                    if yellow_ema_stop > entry_price:
                        print(f"⚠️  Yellow EMA ${yellow_ema_stop:.2f} is ABOVE entry ${entry_price:.2f} - using fallback SL")

                # Place TP (reduce-only sell limit)
                tp_result = self.exchange.order(self.symbol, False, size, tp_price, {"limit": {"tif": "Gtc"}}, reduce_only=True)

                # Place SL (reduce-only sell stop-market)
                sl_result = self.exchange.order(self.symbol, False, size, sl_price, {"trigger": {"triggerPx": sl_price, "isMarket": True, "tpsl": "sl"}}, reduce_only=True)

            else:  # short
                # SHORT: TP below entry, SL ABOVE entry
                tp_price = entry_price * 0.985  # 1.5% TP

                # Validate yellow EMA is above entry for SHORT (proper stop direction)
                if yellow_ema_stop > 0 and yellow_ema_stop > entry_price:
                    sl_price = yellow_ema_stop  # Use yellow EMA if it's above entry
                else:
                    sl_price = entry_price * 1.005  # Fallback: 0.5% above entry
                    if yellow_ema_stop < entry_price and yellow_ema_stop > 0:
                        print(f"⚠️  Yellow EMA ${yellow_ema_stop:.2f} is BELOW entry ${entry_price:.2f} - using fallback SL")

                # Place TP (reduce-only buy limit)
                tp_result = self.exchange.order(self.symbol, True, size, tp_price, {"limit": {"tif": "Gtc"}}, reduce_only=True)

                # Place SL (reduce-only buy stop-market)
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

    def check_yellow_ema_violation(self, position_side, current_price, yellow_ema_stop, ribbon_state):
        """
        Check if price is truly breaking through yellow EMA or just retesting support

        IMPROVED STRATEGY:
        - Requires MULTIPLE consecutive violations (not just one wick)
        - Checks if ribbon is still aligned (if yes, it's just a retest)
        - More lenient threshold (0.5% instead of 0.3%)
        - This prevents exits on healthy pullbacks/retests

        Args:
            position_side: 'long' or 'short'
            current_price: Current market price
            yellow_ema_stop: Yellow EMA level
            ribbon_state: Current ribbon state ('all_green', 'all_red', etc.)

        Returns:
            Tuple of (should_exit, reason)
        """
        if not yellow_ema_stop or yellow_ema_stop == 0:
            self.yellow_ema_violation_count = 0
            return False, "No yellow EMA level"

        # Calculate distance from yellow EMA
        distance_pct = abs((current_price - yellow_ema_stop) / yellow_ema_stop) * 100
        is_violating = False

        if position_side == 'long':
            # LONG: Check if price is BELOW yellow EMA
            if current_price < yellow_ema_stop:
                # More lenient threshold: 0.5% instead of 0.3%
                if distance_pct > 0.5:
                    is_violating = True

                    # Check if ribbon is still bullish - if yes, it's just a retest
                    if ribbon_state in ['all_green', 'mixed_green']:
                        self.yellow_ema_violation_count = 0  # Reset - ribbon still aligned
                        return False, f"Price below yellow but ribbon still GREEN/MIXED_GREEN - likely retest (${current_price:.2f} vs ${yellow_ema_stop:.2f})"

                    # Ribbon is not aligned, count this violation
                    self.yellow_ema_violation_count += 1
                else:
                    # Just touching, not violating
                    self.yellow_ema_violation_count = 0
                    return False, f"Yellow EMA touched but holding (only {distance_pct:.2f}% below)"
            else:
                # Price still above yellow EMA - all good
                self.yellow_ema_violation_count = 0
                return False, f"Price ${current_price:.2f} above yellow ${yellow_ema_stop:.2f}"

        else:  # short
            # SHORT: Check if price is ABOVE yellow EMA
            if current_price > yellow_ema_stop:
                # More lenient threshold: 0.5% instead of 0.3%
                if distance_pct > 0.5:
                    is_violating = True

                    # Check if ribbon is still bearish - if yes, it's just a retest
                    if ribbon_state in ['all_red', 'mixed_red']:
                        self.yellow_ema_violation_count = 0  # Reset - ribbon still aligned
                        return False, f"Price above yellow but ribbon still RED/MIXED_RED - likely retest (${current_price:.2f} vs ${yellow_ema_stop:.2f})"

                    # Ribbon is not aligned, count this violation
                    self.yellow_ema_violation_count += 1
                else:
                    # Just touching, not violating
                    self.yellow_ema_violation_count = 0
                    return False, f"Yellow EMA touched but holding (only {distance_pct:.2f}% above)"
            else:
                # Price still below yellow EMA - all good
                self.yellow_ema_violation_count = 0
                return False, f"Price ${current_price:.2f} below yellow ${yellow_ema_stop:.2f}"

        # Check if we have enough consecutive violations
        if is_violating:
            if self.yellow_ema_violation_count >= self.yellow_ema_violations_needed:
                # CONFIRMED violation - exit
                direction = "below" if position_side == 'long' else "above"
                return True, f"Yellow EMA BROKEN (confirmed {self.yellow_ema_violation_count}x): Price ${current_price:.2f} is {distance_pct:.2f}% {direction} yellow ${yellow_ema_stop:.2f}"
            else:
                # Still counting violations
                remaining = self.yellow_ema_violations_needed - self.yellow_ema_violation_count
                return False, f"Yellow EMA violation detected ({self.yellow_ema_violation_count}/{self.yellow_ema_violations_needed}) - need {remaining} more confirmations"

        return False, "No violation"

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

                # Get actual fill price from position (NOT pre-execution market price)
                pos = self.get_position()
                if pos and 'entry_price' in pos:
                    actual_entry_price = pos['entry_price']
                    print(f"📍 Entry: pre-exec ${price:.2f} → actual ${actual_entry_price:.2f} (slippage: ${actual_entry_price - price:.2f})")
                else:
                    actual_entry_price = price  # Fallback to market price if position not found
                    print(f"⚠️  Could not get actual entry price, using market price ${price:.2f}")

                # Place TP/SL orders using ACTUAL fill price
                tp_success, sl_success, tp_sl_msg = self.place_tp_sl_orders('long', actual_entry_price, yellow_ema_stop)
                return True, f"LONG opened: {size:.4f} {self.symbol} | {tp_sl_msg}"

            elif action == 'short':
                result = self.exchange.market_open(self.symbol, False, size, None, 0.01)
                time.sleep(0.5)  # Wait for position to open

                # Get actual fill price from position (NOT pre-execution market price)
                pos = self.get_position()
                if pos and 'entry_price' in pos:
                    actual_entry_price = pos['entry_price']
                    print(f"📍 Entry: pre-exec ${price:.2f} → actual ${actual_entry_price:.2f} (slippage: ${actual_entry_price - price:.2f})")
                else:
                    actual_entry_price = price  # Fallback to market price if position not found
                    print(f"⚠️  Could not get actual entry price, using market price ${price:.2f}")

                # Place TP/SL orders using ACTUAL fill price
                tp_success, sl_success, tp_sl_msg = self.place_tp_sl_orders('short', actual_entry_price, yellow_ema_stop)
                return True, f"SHORT opened: {size:.4f} {self.symbol} | {tp_sl_msg}"

            return False, "Unknown action"

        except Exception as e:
            return False, f"Error: {str(e)}"

    def send_market_analysis_notification(self, last_decision=None):
        """Send periodic market analysis to Telegram"""
        if not self.telegram or not self.telegram.enabled:
            return

        # Get current data
        current_price = self.data_5min.get('price', 0)

        # Get ribbon states
        timeframe_5min = self.data_5min.get('state', 'unknown')
        timeframe_15min = self.data_15min.get('state', 'unknown')

        # Get EMA groups for 5min
        ema_groups_5min = self.data_5min.get('ema_groups', {})
        green_emas_5min = ema_groups_5min.get('green', [])
        red_emas_5min = ema_groups_5min.get('red', [])
        yellow_emas_5min = ema_groups_5min.get('yellow', [])

        # Extract yellow EMA values (usually EMA40 and EMA100)
        yellow_ema_5min = yellow_emas_5min[0].get('price', 0) if yellow_emas_5min else 0

        # Get EMA counts for 5min with intensity
        # Count all intensities: light, dark, and normal
        tf_5min_light_green = len([e for e in green_emas_5min if e.get('intensity') == 'light'])
        tf_5min_dark_green = len([e for e in green_emas_5min if e.get('intensity') == 'dark'])
        tf_5min_normal_green = len([e for e in green_emas_5min if e.get('intensity') == 'normal'])
        tf_5min_light_red = len([e for e in red_emas_5min if e.get('intensity') == 'light'])
        tf_5min_dark_red = len([e for e in red_emas_5min if e.get('intensity') == 'dark'])
        tf_5min_normal_red = len([e for e in red_emas_5min if e.get('intensity') == 'normal'])

        # Get EMA groups for 15min
        ema_groups_15min = self.data_15min.get('ema_groups', {})
        green_emas_15min = ema_groups_15min.get('green', [])
        red_emas_15min = ema_groups_15min.get('red', [])
        yellow_emas_15min = ema_groups_15min.get('yellow', [])

        # Extract yellow EMA values (usually EMA40 and EMA100)
        yellow_ema_15min = yellow_emas_15min[0].get('price', 0) if yellow_emas_15min else 0

        # Get EMA counts for 15min with intensity
        tf_15min_light_green = len([e for e in green_emas_15min if e.get('intensity') == 'light'])
        tf_15min_dark_green = len([e for e in green_emas_15min if e.get('intensity') == 'dark'])
        tf_15min_normal_green = len([e for e in green_emas_15min if e.get('intensity') == 'normal'])
        tf_15min_light_red = len([e for e in red_emas_15min if e.get('intensity') == 'light'])
        tf_15min_dark_red = len([e for e in red_emas_15min if e.get('intensity') == 'dark'])
        tf_15min_normal_red = len([e for e in red_emas_15min if e.get('intensity') == 'normal'])

        # Combine dark + normal for display (anything that's not light = building)
        tf_5min_dark_green = tf_5min_dark_green + tf_5min_normal_green
        tf_5min_dark_red = tf_5min_dark_red + tf_5min_normal_red
        tf_15min_dark_green = tf_15min_dark_green + tf_15min_normal_green
        tf_15min_dark_red = tf_15min_dark_red + tf_15min_normal_red

        # Determine trade setup status
        trade_setup = "NEUTRAL"
        setup_confidence = 0.0
        claude_analysis = "Market monitoring in progress."

        if last_decision:
            direction = last_decision.get('direction', 'NEUTRAL')
            entry_recommended = last_decision.get('entry_recommended', False)
            confidence_score = last_decision.get('confidence_score', 0.0)
            reasoning = last_decision.get('reasoning', '')

            claude_analysis = reasoning

            # Determine setup status based on ribbon states and confidence
            if direction == 'LONG':
                if 'ALL_GREEN' in timeframe_5min.upper() and 'ALL_GREEN' in timeframe_15min.upper():
                    if entry_recommended and confidence_score >= self.min_confidence:
                        trade_setup = "LONG_READY"
                        setup_confidence = confidence_score
                    else:
                        trade_setup = "LONG_BUILDING"
                        setup_confidence = confidence_score
                elif 'GREEN' in timeframe_5min.upper() or 'GREEN' in timeframe_15min.upper():
                    trade_setup = "LONG_BUILDING"
                    setup_confidence = confidence_score
            elif direction == 'SHORT':
                if 'ALL_RED' in timeframe_5min.upper() and 'ALL_RED' in timeframe_15min.upper():
                    if entry_recommended and confidence_score >= self.min_confidence:
                        trade_setup = "SHORT_READY"
                        setup_confidence = confidence_score
                    else:
                        trade_setup = "SHORT_BUILDING"
                        setup_confidence = confidence_score
                elif 'RED' in timeframe_5min.upper() or 'RED' in timeframe_15min.upper():
                    trade_setup = "SHORT_BUILDING"
                    setup_confidence = confidence_score
            else:
                trade_setup = "NO_SETUP"

        # Send the analysis
        try:
            self.telegram.send_market_analysis(
                current_price=current_price,
                timeframe_5min=timeframe_5min,
                timeframe_15min=timeframe_15min,
                tf_5min_light_green=tf_5min_light_green,
                tf_5min_dark_green=tf_5min_dark_green,
                tf_5min_light_red=tf_5min_light_red,
                tf_5min_dark_red=tf_5min_dark_red,
                tf_15min_light_green=tf_15min_light_green,
                tf_15min_dark_green=tf_15min_dark_green,
                tf_15min_light_red=tf_15min_light_red,
                tf_15min_dark_red=tf_15min_dark_red,
                yellow_ema_5min=yellow_ema_5min,
                yellow_ema_15min=yellow_ema_15min,
                claude_analysis=claude_analysis,
                trade_setup=trade_setup,
                setup_confidence=setup_confidence
            )
            print("📱 Market analysis notification sent to Telegram")
        except Exception as e:
            print(f"⚠️  Market analysis send error: {e}")

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
        # Updated emojis for new states
        if state_5min == 'all_green':
            state_emoji_5min = "🟢"
        elif state_5min == 'mixed_green':
            state_emoji_5min = "🟢⚪"  # Green with white (building green)
        elif state_5min == 'all_red':
            state_emoji_5min = "🔴"
        elif state_5min == 'mixed_red':
            state_emoji_5min = "🔴⚪"  # Red with white (building red)
        else:
            state_emoji_5min = "⚪"

        print(f"\n🔷 {self.timeframe_short}-MINUTE:")
        print(f"   {state_emoji_5min} State: {state_5min.upper()}")
        print(f"   💰 Price: ${price_5min:.2f}" if price_5min else "   💰 Price: N/A")
        print(f"   🟢 {len(ema_5min.get('green', []))} | 🔴 {len(ema_5min.get('red', []))} | 🟡 {len(ema_5min.get('yellow', []))} | ⚪ {len(ema_5min.get('gray', []))}")

        # Show entry strength indicator
        entry_strength_5min = ema_5min.get('entry_strength', 'unknown')
        strength_emoji = "💪" if entry_strength_5min == 'strong' else "👀" if entry_strength_5min == 'building' else "⚠️"
        if entry_strength_5min in ['strong', 'building']:
            print(f"   {strength_emoji} Entry Strength: {entry_strength_5min.upper()}")

        # Show intensity breakdown (light = strong momentum, dark = early transition)
        green_emas = ema_5min.get('green', [])
        red_emas = ema_5min.get('red', [])

        if green_emas:
            light_green = len([e for e in green_emas if e.get('intensity') == 'light'])
            dark_green = len([e for e in green_emas if e.get('intensity') == 'dark'])
            if light_green > 0 or dark_green > 0:
                print(f"   💚 Green: {light_green} light (strong) | {dark_green} dark (early)")

        if red_emas:
            light_red = len([e for e in red_emas if e.get('intensity') == 'light'])
            dark_red = len([e for e in red_emas if e.get('intensity') == 'dark'])
            if light_red > 0 or dark_red > 0:
                print(f"   ❤️  Red: {light_red} light (strong) | {dark_red} dark (early)")

        # Show individual EMAs with details in columns
        indicators_5min = self.data_5min.get('indicators', {})
        mma_indicators_5min = {k: v for k, v in indicators_5min.items() if k.startswith('MMA')}
        if mma_indicators_5min:
            print(f"   📋 Individual EMAs:")
            # Sort by EMA number
            sorted_mma_5min = sorted(mma_indicators_5min.items(),
                                    key=lambda x: int(re.search(r'\d+', x[0]).group() if re.search(r'\d+', x[0]) else 0))

            # Display in 3 columns for better readability
            num_emas = len(sorted_mma_5min)
            for i in range(0, num_emas, 3):
                row = []
                for j in range(3):
                    if i + j < num_emas:
                        name, data = sorted_mma_5min[i + j]
                        color_emoji = "🟢" if data['color'] == 'green' else "🔴" if data['color'] == 'red' else "🟡" if data['color'] == 'yellow' else "⚪" if data['color'] == 'gray' else "⚫"
                        intensity = f"({data['intensity'][0]})" if data.get('intensity') != 'normal' else "   "
                        row.append(f"{color_emoji} {name}: ${data['value']:>8s} {intensity}")
                    else:
                        row.append("")

                # Print row with columns aligned
                if len(row) == 3:
                    print(f"      {row[0]:<30} {row[1]:<30} {row[2]:<30}")
                elif len(row) == 2:
                    print(f"      {row[0]:<30} {row[1]:<30}")
                elif len(row) == 1:
                    print(f"      {row[0]:<30}")

        # 15min
        state_15min = self.data_15min['state']
        price_15min = self.data_15min['price']
        ema_15min = self.data_15min['ema_groups']
        # Updated emojis for new states
        if state_15min == 'all_green':
            state_emoji_15min = "🟢"
        elif state_15min == 'mixed_green':
            state_emoji_15min = "🟢⚪"  # Green with white (building green)
        elif state_15min == 'all_red':
            state_emoji_15min = "🔴"
        elif state_15min == 'mixed_red':
            state_emoji_15min = "🔴⚪"  # Red with white (building red)
        else:
            state_emoji_15min = "⚪"

        print(f"\n🔶 {self.timeframe_long}-MINUTE:")
        print(f"   {state_emoji_15min} State: {state_15min.upper()}")
        print(f"   💰 Price: ${price_15min:.2f}" if price_15min else "   💰 Price: N/A")
        print(f"   🟢 {len(ema_15min.get('green', []))} | 🔴 {len(ema_15min.get('red', []))} | 🟡 {len(ema_15min.get('yellow', []))} | ⚪ {len(ema_15min.get('gray', []))}")

        # Show entry strength indicator
        entry_strength_15min = ema_15min.get('entry_strength', 'unknown')
        strength_emoji = "💪" if entry_strength_15min == 'strong' else "👀" if entry_strength_15min == 'building' else "⚠️"
        if entry_strength_15min in ['strong', 'building']:
            print(f"   {strength_emoji} Entry Strength: {entry_strength_15min.upper()}")

        # Show intensity breakdown (light = strong momentum, dark = early transition)
        green_emas_15min = ema_15min.get('green', [])
        red_emas_15min = ema_15min.get('red', [])

        if green_emas_15min:
            light_green_15 = len([e for e in green_emas_15min if e.get('intensity') == 'light'])
            dark_green_15 = len([e for e in green_emas_15min if e.get('intensity') == 'dark'])
            if light_green_15 > 0 or dark_green_15 > 0:
                print(f"   💚 Green: {light_green_15} light (strong) | {dark_green_15} dark (early)")

        if red_emas_15min:
            light_red_15 = len([e for e in red_emas_15min if e.get('intensity') == 'light'])
            dark_red_15 = len([e for e in red_emas_15min if e.get('intensity') == 'dark'])
            if light_red_15 > 0 or dark_red_15 > 0:
                print(f"   ❤️  Red: {light_red_15} light (strong) | {dark_red_15} dark (early)")

        # Show individual EMAs with details in columns
        indicators_15min = self.data_15min.get('indicators', {})
        mma_indicators_15min = {k: v for k, v in indicators_15min.items() if k.startswith('MMA')}
        if mma_indicators_15min:
            print(f"   📋 Individual EMAs:")
            # Sort by EMA number
            sorted_mma_15min = sorted(mma_indicators_15min.items(),
                                     key=lambda x: int(re.search(r'\d+', x[0]).group() if re.search(r'\d+', x[0]) else 0))

            # Display in 3 columns for better readability
            num_emas = len(sorted_mma_15min)
            for i in range(0, num_emas, 3):
                row = []
                for j in range(3):
                    if i + j < num_emas:
                        name, data = sorted_mma_15min[i + j]
                        color_emoji = "🟢" if data['color'] == 'green' else "🔴" if data['color'] == 'red' else "🟡" if data['color'] == 'yellow' else "⚪" if data['color'] == 'gray' else "⚫"
                        intensity = f"({data['intensity'][0]})" if data.get('intensity') != 'normal' else "   "
                        row.append(f"{color_emoji} {name}: ${data['value']:>8s} {intensity}")
                    else:
                        row.append("")

                # Print row with columns aligned
                if len(row) == 3:
                    print(f"      {row[0]:<30} {row[1]:<30} {row[2]:<30}")
                elif len(row) == 2:
                    print(f"      {row[0]:<30} {row[1]:<30}")
                elif len(row) == 1:
                    print(f"      {row[0]:<30}")

        # Warmup status
        if not self.warmup_complete:
            print("\n" + "🔄"*20)
            print("🔄 WARMUP MODE: Waiting for first state transition...")
            print(f"🔄 {self.timeframe_short}min last state: {self.last_solid_state_5min or 'Not yet recorded'}")
            print(f"🔄 {self.timeframe_long}min last state: {self.last_solid_state_15min or 'Not yet recorded'}")
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
        print(f"📁 Data Logging: {self.data_dir} (continuous files)")
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
        thread_keepalive = threading.Thread(target=self.periodic_browser_keepalive, daemon=True)

        thread_5min.start()
        thread_15min.start()
        thread_keepalive.start()

        print("✅ Data collection threads started")
        print("✅ Browser keep-alive thread started")
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

                # DETECT POSITION CLOSED BY EXCHANGE (TP/SL hit)
                # Track if we HAD a position but now we don't
                if self.position_entry_time and not pos:
                    # Position was closed by exchange (TP or SL hit)
                    exit_duration = time.time() - self.position_entry_time
                    current_price = self.data_5min['price']

                    # Calculate P&L if we have entry price
                    entry_price = self.last_position_entry or 0
                    position_side = self.last_position_side or "unknown"
                    position_size = self.last_position_size or 0

                    pnl_dollars = 0
                    pnl_pct = 0
                    if entry_price > 0:
                        if position_side == 'long':
                            pnl_dollars = (current_price - entry_price) * position_size
                            pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        elif position_side == 'short':
                            pnl_dollars = (entry_price - current_price) * position_size
                            pnl_pct = ((entry_price - current_price) / entry_price) * 100

                    # Determine which was hit
                    if pnl_pct > 1:
                        exit_reason = "🎯 Take Profit Hit"
                    elif pnl_pct < -0.5:
                        exit_reason = "🛑 Stop Loss Hit"
                    else:
                        exit_reason = "🎯 TP/SL triggered by exchange"

                    print(f"\n{'='*80}")
                    print(f"🎯 POSITION CLOSED BY EXCHANGE")
                    print(f"📊 {position_side.upper()} position @ ${entry_price:.2f} → ${current_price:.2f}")
                    print(f"⏱️  Position held for: {exit_duration:.0f} seconds ({exit_duration/60:.1f} minutes)")
                    print(f"💰 P&L: ${pnl_dollars:+.2f} ({pnl_pct:+.2f}%)")
                    print(f"🎯 Reason: {exit_reason}")
                    print(f"{'='*80}\n")

                    # Send Telegram notification for exchange exit
                    if self.telegram and self.telegram.enabled:
                        try:
                            self.telegram.send_exit(
                                direction=position_side.upper(),
                                entry_price=entry_price,
                                exit_price=current_price,
                                size=position_size,
                                pnl=pnl_dollars,
                                pnl_pct=pnl_pct,
                                hold_duration=exit_duration,
                                exit_reason=exit_reason,
                                reasoning=f"Position closed automatically by exchange. Entry: ${entry_price:.2f}, Exit: ${current_price:.2f}, P&L: ${pnl_dollars:+.2f} ({pnl_pct:+.2f}%)"
                            )
                        except Exception as e:
                            print(f"⚠️  Telegram exit notification error: {e}")

                    # Reset tracking
                    self.position_entry_time = None
                    self.yellow_ema_violation_count = 0
                    self.last_position_side = None
                    self.last_position_entry = None
                    self.last_position_size = None
                    self.last_signal = f"{exit_reason} @ ${current_price:.2f} | P&L: ${pnl_dollars:+.2f} ({pnl_pct:+.2f}%)"

                # Check if it's time to update learning insights
                current_time = time.time()

                # Run initial training immediately on first check (uses existing historical data)
                should_update_learning = False
                if not self.initial_training_done:
                    should_update_learning = True
                    self.initial_training_done = True
                # Then run hourly updates
                elif self.last_learning_update is None or (current_time - self.last_learning_update) >= self.learning_interval:
                    should_update_learning = True

                if should_update_learning:
                    print("\n" + "="*80)
                    print("🎓 CONTINUOUS LEARNING UPDATE")
                    print("="*80)
                    try:
                        # Run backtest analysis on recent 4 hours of data
                        analysis = self.learning.run_backtest_analysis(lookback_hours=4)

                        if analysis:
                            # Save insights to file for persistence
                            self.learning.save_insights_to_file()

                            # Print detailed training report
                            report = self.learning.get_training_report()
                            print(report)

                            # Send summary to Telegram
                            if self.telegram and self.telegram.enabled:
                                try:
                                    cycle = self.learning.history.get_latest_cycle()
                                    if cycle:
                                        message = f"🎓 <b>Learning Cycle #{cycle['cycle_number']}</b>\n\n"
                                        message += f"🎯 Scalper Score: {cycle['scalper_score']['total']:.1f}/100 - {cycle['scalper_score']['grade']}\n\n"
                                        message += f"📊 Win Rate: {cycle['metrics']['win_rate']:.1f}%\n"
                                        message += f"💰 R:R Ratio: {cycle['metrics']['risk_reward_ratio']:.2f}:1\n"
                                        message += f"⏱️ Optimal Hold: {cycle['metrics']['best_hold_duration']} min\n\n"
                                        message += f"<b>Top Tips:</b>\n"
                                        for tip in cycle['trading_tips'][:3]:  # Top 3 tips
                                            message += f"{tip}\n"

                                        self.telegram.send_message(message)
                                except Exception as e:
                                    print(f"⚠️  Telegram learning notification error: {e}")

                            print("✅ Learning insights updated and will be used in next Claude decision")

                        self.last_learning_update = current_time

                    except Exception as e:
                        print(f"⚠️  Learning update error: {e}")
                        import traceback
                        traceback.print_exc()

                    print("="*80 + "\n")

                # Track ribbon state transitions for RuleBasedTrader
                current_state_5min = self.data_5min.get('state', 'unknown')
                current_state_15min = self.data_15min.get('state', 'unknown')

                # Update transition times when state changes
                if current_state_5min != self.last_ribbon_state_5min:
                    self.ribbon_transition_time_5min = datetime.now()
                    self.last_ribbon_state_5min = current_state_5min
                    print(f"🔄 5min ribbon transition: → {current_state_5min}")

                if current_state_15min != self.last_ribbon_state_15min:
                    self.ribbon_transition_time_15min = datetime.now()
                    self.last_ribbon_state_15min = current_state_15min
                    print(f"🔄 15min ribbon transition: → {current_state_15min}")

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
                    # IN POSITION - Reduce API calls significantly
                    # Only check if:
                    # 1. Significant time passed (2+ minutes) OR
                    # 2. State deteriorated (ribbon changed to worse state)

                    position_side = pos['side']
                    time_in_position = time.time() - self.position_entry_time if self.position_entry_time else 999

                    # Check if ribbon state deteriorated
                    state_5min = self.data_5min['state']
                    state_15min = self.data_15min['state']

                    ribbon_deteriorated = False
                    if position_side == 'long':
                        # For LONG: deterioration = any RED appearing
                        if 'red' in state_5min.lower() or 'red' in state_15min.lower():
                            ribbon_deteriorated = True
                    else:  # short
                        # For SHORT: deterioration = any GREEN appearing
                        if 'green' in state_5min.lower() or 'green' in state_15min.lower():
                            ribbon_deteriorated = True

                    # Call Claude if:
                    # - Ribbon deteriorated (possible exit signal) OR
                    # - 2+ minutes passed since last check OR
                    # - Been in position >10 minutes (check more frequently near scalp window close)
                    if ribbon_deteriorated:
                        should_ask_claude = True
                        print("🔔 Ribbon deteriorating - checking exit conditions")
                    elif time_in_position > 600 and time_since_last_call >= 90:
                        # After 10min, check every 90 seconds (scalp window closing)
                        should_ask_claude = True
                    elif time_since_last_call >= self.position_check_interval:
                        # Otherwise check every 2 minutes
                        should_ask_claude = True

                elif should_check_entry:
                    # NO POSITION - Check frequently for entries (matching backtest behavior)

                    # Check trade cooldown
                    can_trade = self.can_enter_new_trade()

                    # FIXED: Check every 30 seconds (not just candle close)
                    # This matches backtest which checks every data point
                    # Only call if:
                    # 1. Trade cooldown expired AND
                    # 2. Enough time since last check (30 seconds)
                    if can_trade and time_since_last_call >= 30:
                        should_ask_claude = True
                        print("🔍 Checking for entry opportunity...")
                    elif not can_trade:
                        # Still in cooldown
                        pass  # Message already printed by can_enter_new_trade()

                # Update last check states
                self.last_check_state['5min'] = self.data_5min['state']
                self.last_check_state['15min'] = self.data_15min['state']

                # Track API call savings
                if not should_ask_claude:
                    self.api_calls_saved += 1

                # Make Claude decision if we have Claude and conditions met
                if self.claude and should_ask_claude:
                    self.last_api_call_time = current_time  # Update call time
                    self.total_api_calls += 1

                    # Print API usage stats every 10 calls
                    if self.total_api_calls % 10 == 0:
                        total_checks = self.total_api_calls + self.api_calls_saved
                        savings_pct = (self.api_calls_saved / total_checks * 100) if total_checks > 0 else 0
                        print(f"💰 API Stats: {self.total_api_calls} calls | {self.api_calls_saved} saved ({savings_pct:.1f}% reduction)")

                    try:
                        # Get latest learning insights to pass to Claude
                        learning_insights_text = self.learning.get_training_prompt_addition()

                        direction, entry_recommended, confidence_score, reasoning, targets = \
                            self.claude.make_trading_decision(
                                self.data_5min,
                                self.data_15min,
                                pos,
                                account,
                                learning_insights=learning_insights_text
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

                            # Check if minimum hold time has passed
                            time_in_position = 0
                            minimum_hold_met = True
                            if self.position_entry_time:
                                time_in_position = time.time() - self.position_entry_time
                                minimum_hold_met = time_in_position >= self.min_hold_time

                            # Check if we should exit
                            should_exit = False
                            exit_reason = ""
                            ignore_hold_time = False  # Flag for critical exits that bypass hold time

                            # Check yellow EMA violation (with confirmation, respects hold time)
                            ribbon_state_5min = self.data_5min.get('state', 'unknown')
                            yellow_violated, yellow_msg = self.check_yellow_ema_violation(
                                position_side, current_price, yellow_ema_stop, ribbon_state_5min
                            )

                            # Yellow EMA violation now requires:
                            # 1. Multiple confirmations (3 consecutive violations)
                            # 2. Minimum hold time to be met
                            # 3. Ribbon NOT still aligned (prevents exits on retests)
                            if yellow_violated and minimum_hold_met:
                                should_exit = True
                                exit_reason = yellow_msg
                                # NO LONGER bypasses hold time - violations must be confirmed over time

                            # Check other exit signals ONLY if minimum hold time has passed
                            if minimum_hold_met:
                                # Exit signal from Claude
                                if exit_recommended == 'YES':
                                    should_exit = True
                                    exit_reason = "Claude EXIT signal"

                                # Position management: EXIT_NOW
                                if targets.get('position_management') == 'EXIT_NOW':
                                    should_exit = True
                                    exit_reason = "Position management: EXIT_NOW"

                                # Reversal detection: opposite direction with high confidence
                                opposite_direction = 'SHORT' if position_side == 'long' else 'LONG'
                                if (direction == opposite_direction and
                                    entry_recommended == 'YES' and
                                    confidence_score >= self.min_confidence):
                                    should_exit = True
                                    exit_reason = f"Reversal to {direction}"
                            else:
                                # Still in minimum hold period
                                if time_in_position > 0:
                                    remaining = self.min_hold_time - time_in_position
                                    print(f"🔒 Position in hold period: {time_in_position:.0f}s elapsed, {remaining:.0f}s remaining")

                            # REMOVED: Outer bands spreading - too aggressive, causes premature exits
                            # if targets.get('outer_bands_spreading', False):
                            #     should_exit = True
                            #     exit_reason = "Outer bands spreading (pullback)"

                            # Apply hold time check unless it's a critical exit
                            if should_exit and not minimum_hold_met and not ignore_hold_time:
                                print(f"⏸️  Exit signal '{exit_reason}' blocked - minimum hold time not met ({time_in_position:.0f}s / {self.min_hold_time}s)")
                                should_exit = False

                            # Execute exit
                            if should_exit and self.auto_trade:
                                success, message = self.execute_trade('close', current_price)

                                if success:
                                    # Print full exit reasoning
                                    exit_duration = time.time() - self.position_entry_time if self.position_entry_time else 0
                                    print(f"\n{'='*80}")
                                    print(f"🚪 EXIT DECISION - {exit_reason}")
                                    print(f"⏱️  Position held for: {exit_duration:.0f} seconds ({exit_duration/60:.1f} minutes)")
                                    print(f"{'='*80}")
                                    print(f"📊 Claude's Full Reasoning:")
                                    print(reasoning)
                                    print(f"{'='*80}\n")

                                    # Reset entry time and violation counter after exit
                                    self.position_entry_time = None
                                    self.yellow_ema_violation_count = 0
                                    self.last_position_side = None
                                    self.last_position_entry = None
                                    self.last_position_size = None

                                    self.last_signal = f"🚪 EXIT {position_side.upper()} @ ${current_price:.2f} | {exit_reason} | {message}"
                                    executed = True
                                    self.trades.append({
                                        'time': datetime.now(),
                                        'action': f'exit_{position_side}',
                                        'price': current_price,
                                        'confidence': confidence_score,
                                        'reasoning': f"{exit_reason}: {reasoning}",
                                        'hold_duration_seconds': exit_duration
                                    })

                                    # Send Telegram notification for EXIT
                                    if self.telegram and self.telegram.enabled:
                                        try:
                                            self.telegram.send_exit(
                                                direction=position_side.upper(),
                                                entry_price=pos['entry_price'],
                                                exit_price=current_price,
                                                size=pos['size'],
                                                pnl=pos.get('unrealized_pnl', 0),
                                                pnl_pct=(pos.get('unrealized_pnl', 0) / pos.get('margin_used', 1) * 100) if pos.get('margin_used', 0) > 0 else 0,
                                                hold_duration=exit_duration,
                                                exit_reason=exit_reason,
                                                reasoning=reasoning
                                            )
                                            print("📱 Telegram exit notification sent")
                                        except Exception as telegram_error:
                                            print(f"⚠️  Telegram notification error: {telegram_error}")

                                    # After closing, check if we should immediately reverse
                                    if exit_reason.startswith("Reversal"):
                                        time.sleep(1)  # Brief pause
                                        reverse_action = opposite_direction.lower()
                                        # Pass yellow_ema_stop for the reverse entry
                                        success_reverse, message_reverse = self.execute_trade(reverse_action, current_price, yellow_ema_stop)

                                        if success_reverse:
                                            # Track new position entry time
                                            self.position_entry_time = time.time()
                                            self.yellow_ema_violation_count = 0  # Reset counter for new position
                                            print(f"⏱️  Reversed position opened at {datetime.now().strftime('%H:%M:%S')}")

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
                        elif self.claude.should_execute_trade(direction, entry_recommended, confidence_score, self.min_confidence, targets.get('timeframe_alignment', 'UNKNOWN')):

                            # QUALITY FILTER - Only take HIGH-QUALITY setups!
                            quality_ok, quality_reason = self.is_high_quality_setup(
                                direction, confidence_score, self.data_5min, self.data_15min
                            )

                            if not quality_ok:
                                # Setup rejected by quality filter
                                print(f"⏸️  Trade rejected: {quality_reason}")
                                self.last_signal = f"❌ Setup rejected: {quality_reason}"
                                # Don't execute trade, continue monitoring
                            else:
                                # Quality check passed - proceed with entry
                                print(quality_reason)  # Print the success message
                                action = direction.lower()
                                yellow_ema_stop = targets.get('yellow_ema_stop', 0)

                                if self.auto_trade:
                                    success, message = self.execute_trade(action, current_price, yellow_ema_stop)

                                    if success:
                                        # Track entry time for minimum hold period
                                        self.position_entry_time = time.time()
                                        self.last_trade_time = time.time()  # Update cooldown tracker
                                        self.yellow_ema_violation_count = 0  # Reset violation counter
                                        print(f"⏱️  Position opened at {datetime.now().strftime('%H:%M:%S')} - minimum hold: {self.min_hold_time/60:.0f}min | Cooldown: {self.trade_cooldown/60:.0f}min")

                                        # Get position details for tracking
                                        new_pos = self.get_position()
                                        if new_pos:
                                            self.last_position_side = new_pos['side']
                                            self.last_position_entry = new_pos['entry_price']
                                            self.last_position_size = new_pos['size']

                                        self.last_signal = f"✅ {direction} @ ${current_price:.2f} | {message} | Conf: {confidence_score:.0%}{transition_context}"
                                        executed = True

                                        self.trades.append({
                                            'time': datetime.now(),
                                            'action': action,
                                            'price': current_price,
                                            'confidence': confidence_score,
                                            'reasoning': reasoning
                                        })

                                        # Send Telegram notification for ENTRY
                                        if self.telegram and self.telegram.enabled:
                                            try:
                                                # Position size already retrieved above
                                                position_size = new_pos['size'] if new_pos else 0

                                                # Get EMA intensity counts for momentum display
                                                green_emas_5 = self.data_5min['ema_groups'].get('green', [])
                                                red_emas_5 = self.data_5min['ema_groups'].get('red', [])
                                                light_green = len([e for e in green_emas_5 if e.get('intensity') == 'light'])
                                                dark_green = len([e for e in green_emas_5 if e.get('intensity') == 'dark'])
                                                light_red = len([e for e in red_emas_5 if e.get('intensity') == 'light'])
                                                dark_red = len([e for e in red_emas_5 if e.get('intensity') == 'dark'])

                                                self.telegram.send_entry(
                                                    direction=direction,
                                                    price=current_price,
                                                    size=position_size,
                                                    confidence=confidence_score,
                                                    reasoning=reasoning,
                                                    entry_price=targets.get('entry_price', current_price),
                                                    stop_loss=targets.get('stop_loss', 0),
                                                    take_profit=targets.get('take_profit', 0),
                                                    yellow_ema_stop=yellow_ema_stop,
                                                    timeframe_5min=self.data_5min['state'],
                                                    timeframe_15min=self.data_15min['state'],
                                                    light_green=light_green,
                                                    dark_green=dark_green,
                                                    light_red=light_red,
                                                    dark_red=dark_red
                                                )
                                                print("📱 Telegram entry notification sent")
                                            except Exception as telegram_error:
                                                print(f"⚠️  Telegram notification error: {telegram_error}")
                                    else:
                                        self.last_signal = f"❌ {direction} @ ${current_price:.2f} | {message}"
                                else:
                                    self.last_signal = f"📊 SIGNAL: {direction} @ ${current_price:.2f} | Conf: {confidence_score:.0%} (Auto-trade OFF)"

                        # Log decision to CSV - mark as 'exit' if we have a position, 'decision' otherwise
                        action_type = 'exit' if pos else 'decision'
                        self.log_claude_decision(direction, entry_recommended, confidence_score,
                                               reasoning, targets, executed, action_type)

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

                # Periodic market analysis to Telegram
                if (self.telegram and self.telegram.enabled and
                    self.market_analysis_interval > 0 and
                    (self.last_market_analysis_time is None or
                     current_time_commentary - self.last_market_analysis_time >= self.market_analysis_interval)):
                    try:
                        self.send_market_analysis_notification(last_decision)
                        self.last_market_analysis_time = current_time_commentary
                    except Exception as e:
                        print(f"⚠️  Market analysis notification error: {e}")

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

    # Timeframe selection
    print("\n📊 SELECT TRADING STRATEGY:")
    print("  [1] 🐌 DAY TRADING (5min + 15min)")
    print("  [2] ⚡ SCALPING (1min + 3min) **RECOMMENDED**")

    while True:
        strategy_choice = input("\nEnter choice (1 or 2, default: 2): ").strip() or '2'
        if strategy_choice == '1':
            timeframe_short = 5
            timeframe_long = 15
            strategy_name = "DAY TRADING"
            break
        elif strategy_choice == '2':
            timeframe_short = 1
            timeframe_long = 3
            strategy_name = "SCALPING"
            break
        else:
            print("❌ Invalid choice. Please enter 1 or 2.")

    # Summary
    print("\n" + "="*80)
    print("📊 CONFIGURATION SUMMARY:")
    print("="*80)
    print(f"  Strategy: {strategy_name}")
    print(f"  Network: {'TESTNET' if use_testnet else '⚠️  MAINNET ⚠️'}")
    print(f"  Auto-Trading: {'✅ ENABLED' if auto_trade else '❌ DISABLED'}")
    print(f"  Position Size: {position_size_pct*100:.1f}%")
    print(f"  Leverage: {leverage}x")
    print(f"  Min Confidence: {min_confidence:.0%}")
    print(f"  Timeframes: {timeframe_short}min + {timeframe_long}min")
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
        timeframe_short=timeframe_short,
        timeframe_long=timeframe_long,
        min_confidence=min_confidence
    )
    bot.monitor()


if __name__ == "__main__":
    main()
