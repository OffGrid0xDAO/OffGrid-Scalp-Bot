#!/usr/bin/env python3
"""
Automated EMA Data Backfill
Uses automated mouse control to hover over chart bars and capture EMA values
Fully automated - no manual hovering required!
"""

import csv
import os
import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from dotenv import load_dotenv
import pyautogui

load_dotenv()


class AutoBackfiller:
    """Fully automated EMA data backfill with mouse control"""

    def __init__(self):
        self.tradingview_email = os.getenv('TRADINGVIEW_EMAIL')
        self.tradingview_password = os.getenv('TRADINGVIEW_PASSWORD')

        # Get chart URL from env or use default
        self.tradingview_chart_url = os.getenv('TRADINGVIEW_CHART_URL')
        if not self.tradingview_chart_url:
            # Try to get from CHART_URL or TRADINGVIEW_5MIN_URL
            self.tradingview_chart_url = os.getenv('CHART_URL') or os.getenv('TRADINGVIEW_5MIN_URL')

        if not self.tradingview_chart_url:
            print("\n⚠️  TRADINGVIEW_CHART_URL not found in .env")
            print("   Please enter your TradingView chart URL:")
            print("   (Example: https://www.tradingview.com/chart/xxxxx/)")
            self.tradingview_chart_url = input("\n   Chart URL: ").strip()

        # Enable fail-safe (move mouse to corner to abort)
        pyautogui.FAILSAFE = True

    def init_browser(self):
        """Initialize Chrome browser"""
        print("\n🌐 Initializing browser...")

        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')

        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        return driver

    def login_tradingview(self, driver):
        """Login to TradingView"""
        print("\n🔐 Logging into TradingView...")

        try:
            # Navigate directly to login page
            print("   🌐 Navigating to login page...")
            driver.get("https://www.tradingview.com/accounts/signin/")
            time.sleep(3)

            # Check if already logged in
            try:
                driver.find_element(By.CSS_SELECTOR, "[data-name='header-user-menu-button']")
                print("   ✅ Already logged in!")
                return
            except:
                pass  # Not logged in, continue

            # Click Email button
            print("   🔍 Looking for Email button...")
            email_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='Email'].emailButton-nKAw8Hvt"))
            )
            email_button.click()
            print("   📧 Email button clicked")
            time.sleep(2)

            # Enter email
            print("   📝 Entering email...")
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='id_username']"))
            )
            email_input.clear()
            email_input.send_keys(self.tradingview_email)
            time.sleep(1)

            # Enter password
            print("   🔑 Entering password...")
            password_input = driver.find_element(By.CSS_SELECTOR, "input[name='id_password']")
            password_input.clear()
            password_input.send_keys(self.tradingview_password)
            time.sleep(1)

            # Click Sign in button
            print("   🚀 Clicking Sign in...")
            selectors = [
                "button.submitButton-LQwxK8Bm",
                "button[data-overflow-tooltip-text='Sign in']",
                "button[type='submit']",
            ]

            for selector in selectors:
                try:
                    signin_button = driver.find_element(By.CSS_SELECTOR, selector)
                    signin_button.click()
                    print("   ✅ Sign in button clicked")
                    break
                except:
                    continue

            time.sleep(5)
            print("   ✅ Logged in successfully")

        except Exception as e:
            print(f"   ⚠️  Login failed: {e}")
            print(f"   💡 You may need to log in manually in the browser")
            input("\n   Press Enter after logging in manually...")
            return

    def load_chart(self, driver):
        """Load the chart with EMAs"""
        print(f"\n📈 Loading chart...")

        driver.get(self.tradingview_chart_url)
        time.sleep(10)  # Wait for chart to fully load

        print("   ✅ Chart loaded")

    def set_timeframe(self, driver, timeframe='1'):
        """
        Set chart timeframe
        timeframe: '1' for 1min, '3' for 3min, '5' for 5min
        """
        print(f"\n⏱️  Setting timeframe to {timeframe}min...")

        try:
            # Click on timeframe selector
            # This is tricky - may need to adjust selector based on TradingView UI
            # Alternative: Use keyboard shortcut

            # Press comma key multiple times to zoom to desired timeframe
            body = driver.find_element(By.TAG_NAME, 'body')

            # First, go to a known state (daily)
            body.send_keys('D')
            time.sleep(1)

            # Then navigate to 1min
            if timeframe == '1':
                body.send_keys('1')
            elif timeframe == '3':
                body.send_keys('3')
            elif timeframe == '5':
                body.send_keys('5')

            time.sleep(2)
            print(f"   ✅ Timeframe set to {timeframe}min")

        except Exception as e:
            print(f"   ⚠️  Could not set timeframe: {e}")
            print("   📝 You may need to set timeframe manually")

    def navigate_to_date(self, driver, target_date):
        """
        Navigate chart to specific date
        Uses Go To dialog (Alt+G)
        """
        print(f"\n📅 Navigating to {target_date}...")

        try:
            body = driver.find_element(By.TAG_NAME, 'body')

            # Open "Go to" dialog with Alt+G
            actions = ActionChains(driver)
            actions.key_down(Keys.ALT).send_keys('g').key_up(Keys.ALT).perform()
            time.sleep(1)

            # Type the date (format: YYYY-MM-DD HH:MM)
            date_str = target_date.strftime('%Y-%m-%d %H:%M')
            actions.send_keys(date_str).perform()
            time.sleep(0.5)

            # Press Enter
            actions.send_keys(Keys.RETURN).perform()
            time.sleep(2)

            print(f"   ✅ Navigated to {date_str}")

        except Exception as e:
            print(f"   ⚠️  Navigation failed: {e}")
            raise

    def get_chart_area(self, driver):
        """Find the chart area coordinates"""
        try:
            # Find the chart canvas element
            # TradingView uses canvas for the chart
            canvas = driver.find_element(By.CSS_SELECTOR, 'canvas')
            location = canvas.location
            size = canvas.size

            # Get chart boundaries
            chart_left = location['x']
            chart_top = location['y']
            chart_right = chart_left + size['width']
            chart_bottom = chart_top + size['height']

            # Chart area for candlesticks (exclude legends, etc.)
            # Usually the main chart is in the center-right area
            usable_left = chart_left + 100  # Skip Y-axis labels
            usable_right = chart_right - 50  # Skip right margin
            usable_top = chart_top + 50     # Skip top margin
            usable_bottom = chart_bottom - 100  # Skip X-axis and bottom info

            return {
                'left': usable_left,
                'right': usable_right,
                'top': usable_top,
                'bottom': usable_bottom,
                'width': usable_right - usable_left,
                'height': usable_bottom - usable_top,
                'center_y': (usable_top + usable_bottom) // 2
            }

        except Exception as e:
            print(f"⚠️  Could not find chart area: {e}")
            # Return default area (adjust based on your screen)
            return {
                'left': 200,
                'right': 1700,
                'top': 150,
                'bottom': 900,
                'width': 1500,
                'height': 750,
                'center_y': 525
            }

    def read_indicators(self, driver):
        """Read current EMA indicators"""
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

                    # Parse RGB
                    rgb_match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', style)
                    if rgb_match:
                        r, g, b = map(int, rgb_match.groups())

                        # Classify color
                        if r > 150 and g > 150 and r + g > 300:
                            color = 'yellow'
                            intensity = 'normal'
                        elif g > r * 1.3 and g > b * 1.3:
                            color = 'green'
                            intensity = 'light' if g >= 150 else 'dark'
                        elif r > g * 1.3 and r > b * 1.3:
                            color = 'red'
                            intensity = 'light' if r >= 150 else 'dark'
                        elif 100 < r < 150 and 100 < g < 150 and 100 < b < 150:
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

        except Exception as e:
            return {}

    def analyze_ribbon(self, indicators):
        """Analyze ribbon state"""
        mma_indicators = {k: v for k, v in indicators.items() if k.startswith('MMA')}

        if not mma_indicators:
            return 'unknown'

        green_count = sum(1 for v in mma_indicators.values() if v['color'] == 'green')
        red_count = sum(1 for v in mma_indicators.values() if v['color'] == 'red')
        total = len(mma_indicators)

        if green_count / total >= 0.92:
            return 'all_green'
        elif red_count / total >= 0.92:
            return 'all_red'
        elif green_count / total >= 0.75:
            return 'mixed_green'
        elif red_count / total >= 0.75:
            return 'mixed_red'
        else:
            return 'mixed'

    def automated_hover_capture(self, driver, start_time, end_time, timeframe_minutes=1):
        """
        Automatically hover over bars and capture data

        Args:
            driver: Selenium WebDriver
            start_time: datetime to start
            end_time: datetime to end
            timeframe_minutes: 1, 3, or 5 minute bars

        Returns:
            List of captured data
        """
        print(f"\n🤖 Starting automated capture...")
        print(f"   From: {start_time}")
        print(f"   To:   {end_time}")
        print(f"   Timeframe: {timeframe_minutes}min")

        # Calculate expected bars
        duration_minutes = (end_time - start_time).total_seconds() / 60
        expected_bars = int(duration_minutes / timeframe_minutes)
        print(f"   Expected bars: ~{expected_bars}")

        # Get chart area
        chart_area = self.get_chart_area(driver)
        print(f"\n📊 Chart area: {chart_area['width']}x{chart_area['height']}px")

        # Calculate pixels per bar (estimate)
        # TradingView typically shows ~100-200 bars on screen
        bars_on_screen = 150  # Approximate
        pixels_per_bar = chart_area['width'] / bars_on_screen

        print(f"   Estimated pixels per bar: {pixels_per_bar:.1f}px")
        print(f"   Will scan from left to right...")

        captured_data = []
        last_price = None

        # Start from left side of chart
        current_x = chart_area['left']
        y = chart_area['center_y']

        print(f"\n🖱️  Moving mouse to start position...")
        pyautogui.moveTo(current_x, y, duration=1)
        time.sleep(1)

        print(f"\n📸 Starting capture (press Ctrl+C to stop)...")
        print(f"   Tip: Mouse will move slowly across chart")
        print(f"   Move to top-left corner to abort (failsafe)\n")

        bar_count = 0

        try:
            while current_x < chart_area['right'] and bar_count < expected_bars:
                # Move mouse to current position
                pyautogui.moveTo(current_x, y, duration=0.05)
                time.sleep(0.1)  # Wait for tooltip to appear

                # Read indicators at this position
                indicators = self.read_indicators(driver)

                if indicators and 'MMA5' in indicators:
                    current_price = indicators['MMA5'].get('price')

                    # Only capture if price changed (new bar)
                    if current_price and current_price != last_price:
                        ribbon_state = self.analyze_ribbon(indicators)

                        # Build data row
                        row = {
                            'timestamp': datetime.now().isoformat(),  # Capture time
                            'price': current_price,
                            'ribbon_state': ribbon_state
                        }

                        # Add EMA values
                        for ema_num in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
                            key = f'MMA{ema_num}'
                            if key in indicators:
                                row[f'{key}_value'] = indicators[key].get('value', 'N/A')
                                row[f'{key}_color'] = indicators[key].get('color', 'unknown')
                                row[f'{key}_intensity'] = indicators[key].get('intensity', 'normal')
                            else:
                                row[f'{key}_value'] = 'N/A'
                                row[f'{key}_color'] = 'unknown'
                                row[f'{key}_intensity'] = 'normal'

                        captured_data.append(row)
                        last_price = current_price
                        bar_count += 1

                        # Progress indicator
                        progress = (bar_count / expected_bars) * 100 if expected_bars > 0 else 0
                        print(f"  ✅ Bar {bar_count}/{expected_bars} ({progress:.1f}%) | Price: {current_price} | {ribbon_state}")

                # Move to next position (small step to ensure we hit each bar)
                current_x += max(1, pixels_per_bar * 0.5)  # Move half a bar width at a time

        except KeyboardInterrupt:
            print(f"\n\n⏸️  Capture interrupted by user")
        except pyautogui.FailSafeException:
            print(f"\n\n🛑 Failsafe triggered - mouse moved to corner")
        except Exception as e:
            print(f"\n\n❌ Error during capture: {e}")

        print(f"\n📊 Capture complete!")
        print(f"   Total bars captured: {len(captured_data)}")
        print(f"   Expected: {expected_bars}")
        print(f"   Coverage: {(len(captured_data)/expected_bars)*100:.1f}%")

        return captured_data

    def save_data(self, data, output_file='trading_data/ema_backfill.csv'):
        """Save captured data to CSV"""
        if not data:
            print("\n⚠️  No data to save")
            return

        print(f"\n💾 Saving {len(data)} rows to {output_file}...")

        # Headers
        headers = ['timestamp', 'price', 'ribbon_state']
        for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
            headers.extend([
                f'MMA{ema}_value',
                f'MMA{ema}_color',
                f'MMA{ema}_intensity'
            ])

        # Write CSV
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        print(f"   ✅ Saved successfully")

    def run(self, start_time, end_time, timeframe_minutes=1):
        """
        Main execution

        Args:
            start_time: datetime object for start
            end_time: datetime object for end
            timeframe_minutes: 1, 3, or 5
        """
        print("="*80)
        print("AUTOMATED EMA BACKFILL")
        print("="*80)

        # Initialize browser
        driver = self.init_browser()

        try:
            # Login and load chart
            self.login_tradingview(driver)
            self.load_chart(driver)

            # Set timeframe
            self.set_timeframe(driver, str(timeframe_minutes))

            # Navigate to start date
            self.navigate_to_date(driver, start_time)

            # Wait for user to verify chart position
            print(f"\n⏸️  Chart is now at {start_time}")
            print(f"   Please verify:")
            print(f"   1. Chart shows correct date/time")
            print(f"   2. Timeframe is {timeframe_minutes}min")
            print(f"   3. Chart is zoomed appropriately")

            input("\nPress Enter to start automated capture...")

            # Automated hover capture
            data = self.automated_hover_capture(driver, start_time, end_time, timeframe_minutes)

            # Save data
            if data:
                self.save_data(data)
                print(f"\n✅ Backfill complete!")
                print(f"   Review: trading_data/ema_backfill.csv")
            else:
                print(f"\n⚠️  No data captured")

        finally:
            print("\n🔒 Closing browser...")
            driver.quit()


if __name__ == '__main__':
    import sys

    # Default: Fill from Oct 20 12:45 to now
    start_time = datetime(2025, 10, 20, 12, 45)
    end_time = datetime.now()

    # Allow command line override
    if len(sys.argv) > 1:
        # python3 auto_backfill_ema.py "2025-10-20 12:45" "2025-10-21 04:00"
        start_time = datetime.strptime(sys.argv[1], '%Y-%m-%d %H:%M')
        if len(sys.argv) > 2:
            end_time = datetime.strptime(sys.argv[2], '%Y-%m-%d %H:%M')

    print(f"\n🎯 Backfill Settings:")
    print(f"   Start: {start_time}")
    print(f"   End: {end_time}")
    print(f"   Duration: {(end_time - start_time).total_seconds() / 3600:.1f} hours")

    # Initialize and run
    backfiller = AutoBackfiller()
    backfiller.run(start_time, end_time, timeframe_minutes=1)
