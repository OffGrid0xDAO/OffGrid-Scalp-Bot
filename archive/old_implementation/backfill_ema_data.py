#!/usr/bin/env python3
"""
Backfill Missing EMA Data from TradingView
Uses browser automation to hover over historical bars and capture EMA states
"""

import csv
import os
import re
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class EMABackfiller:
    """Backfill missing EMA data from TradingView"""

    def __init__(self):
        self.tradingview_email = os.getenv('TRADINGVIEW_EMAIL')
        self.tradingview_password = os.getenv('TRADINGVIEW_PASSWORD')
        self.tradingview_chart_url = os.getenv('TRADINGVIEW_CHART_URL')

    def find_gaps(self, csv_file='trading_data/ema_data_5min.csv'):
        """Find gaps in existing data"""
        print(f"\n📊 Analyzing {csv_file} for gaps...")

        df = pd.read_csv(csv_file, on_bad_lines='skip')
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        gaps = []
        for i in range(1, len(df)):
            time_diff = (df.iloc[i]['timestamp'] - df.iloc[i-1]['timestamp']).total_seconds() / 60
            if time_diff > 15:  # Gap larger than 15 minutes
                gaps.append({
                    'start': df.iloc[i-1]['timestamp'],
                    'end': df.iloc[i]['timestamp'],
                    'duration_hours': time_diff / 60
                })

        if gaps:
            print(f"\n⚠️  Found {len(gaps)} gaps > 15 minutes:")
            for i, gap in enumerate(gaps, 1):
                print(f"\nGap #{i}:")
                print(f"  From: {gap['start']}")
                print(f"  To:   {gap['end']}")
                print(f"  Duration: {gap['duration_hours']:.1f} hours")
        else:
            print("\n✅ No significant gaps found!")

        return gaps

    def init_browser(self):
        """Initialize Chrome browser"""
        print("\n🌐 Initializing browser...")

        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        # Uncomment to run headless:
        # chrome_options.add_argument('--headless')

        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def login_tradingview(self, driver):
        """Login to TradingView"""
        print("\n🔐 Logging into TradingView...")

        driver.get("https://www.tradingview.com/")
        time.sleep(3)

        try:
            # Click user menu
            menu_button = driver.find_element(By.CSS_SELECTOR, "[data-name='header-user-menu-button']")
            menu_button.click()
            time.sleep(1)

            # Click Sign in
            signin_button = driver.find_element(By.CSS_SELECTOR, "[data-name='header-user-menu-sign-in']")
            signin_button.click()
            time.sleep(2)

            # Click Email button
            email_button = driver.find_element(By.CSS_SELECTOR, "[name='Email']")
            email_button.click()
            time.sleep(1)

            # Enter email
            email_input = driver.find_element(By.CSS_SELECTOR, "[name='id_username']")
            email_input.send_keys(self.tradingview_email)

            # Enter password
            password_input = driver.find_element(By.CSS_SELECTOR, "[name='id_password']")
            password_input.send_keys(self.tradingview_password)

            # Click Sign in
            signin_submit = driver.find_element(By.CSS_SELECTOR, "[type='submit']")
            signin_submit.click()

            print("   ✅ Logged in successfully")
            time.sleep(5)

        except Exception as e:
            print(f"   ⚠️  Login failed: {e}")
            raise

    def load_chart(self, driver):
        """Load the chart with EMAs"""
        print(f"\n📈 Loading chart: {self.tradingview_chart_url}")

        driver.get(self.tradingview_chart_url)
        time.sleep(10)  # Wait for chart to fully load

        print("   ✅ Chart loaded")

    def read_indicators(self, driver):
        """Read current EMA indicators from chart"""
        try:
            value_items = driver.find_elements(By.CSS_SELECTOR, 'div.valueItem-l31H9iuA')
            indicators = {}

            for item in value_items:
                try:
                    title = item.get_attribute('data-test-id-value-title')
                    if not title or not title.startswith('MMA'):
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
            print(f"⚠️  Error reading indicators: {e}")
            return {}

    def analyze_ribbon(self, indicators):
        """Analyze ribbon state from indicators"""
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

    def get_chart_timestamp(self, driver):
        """Try to read the timestamp from the chart tooltip"""
        try:
            # Look for date/time display elements
            time_elements = driver.find_elements(By.CSS_SELECTOR, 'div[class*="time"]')
            for elem in time_elements:
                text = elem.text
                # Try to parse various time formats
                # This is tricky - TradingView shows time in different formats
                # You may need to adjust this based on what you see
                if text:
                    return text
        except:
            pass
        return None

    def backfill_gap(self, driver, gap_start, gap_end, output_file='trading_data/ema_backfill.csv'):
        """
        Backfill a specific gap by hovering over bars

        NOTE: This is a semi-manual process. You need to:
        1. Navigate to the gap time period on the chart
        2. Set the chart to 1-minute or 3-minute timeframe
        3. This script will capture data as you hover

        Returns list of captured data points
        """
        print(f"\n🔍 Backfilling gap:")
        print(f"   From: {gap_start}")
        print(f"   To:   {gap_end}")
        print(f"\n⚠️  MANUAL STEPS REQUIRED:")
        print(f"   1. Navigate chart to {gap_start}")
        print(f"   2. Set timeframe to 1min or 3min")
        print(f"   3. Press Enter when ready to start capturing...")

        input("\nPress Enter to continue...")

        print("\n📸 Starting capture mode...")
        print("   Move mouse slowly over each bar from left to right")
        print("   Data will be captured automatically")
        print("   Press Ctrl+C to stop\n")

        captured_data = []
        last_price = None

        try:
            while True:
                # Read indicators at current cursor position
                indicators = self.read_indicators(driver)

                if indicators:
                    # Get current price
                    current_price = None
                    for key, val in indicators.items():
                        if val.get('price') and key == 'MMA5':  # Use MMA5 as price reference
                            current_price = val['price']
                            break

                    # Only capture if price changed (new bar)
                    if current_price and current_price != last_price:
                        ribbon_state = self.analyze_ribbon(indicators)

                        # Build data row
                        timestamp = datetime.now()  # Note: This is capture time, not bar time
                        row = {
                            'timestamp': timestamp.isoformat(),
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

                        print(f"✅ Captured: {current_price} | {ribbon_state} | Total: {len(captured_data)}")

                time.sleep(0.1)  # Small delay between checks

        except KeyboardInterrupt:
            print(f"\n\n📊 Capture stopped. Total bars captured: {len(captured_data)}")

        # Save captured data
        if captured_data:
            self.save_backfill_data(captured_data, output_file)

        return captured_data

    def save_backfill_data(self, data, output_file):
        """Save backfilled data to CSV"""
        if not data:
            print("No data to save")
            return

        print(f"\n💾 Saving {len(data)} rows to {output_file}...")

        # Create headers
        headers = ['timestamp', 'price', 'ribbon_state']
        for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
            headers.extend([
                f'MMA{ema}_value',
                f'MMA{ema}_color',
                f'MMA{ema}_intensity'
            ])

        # Write to CSV
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        print(f"   ✅ Saved to {output_file}")

    def run(self):
        """Main execution"""
        print("="*80)
        print("EMA DATA BACKFILLER")
        print("="*80)

        # Find gaps
        gaps = self.find_gaps()

        if not gaps:
            print("\n✅ No gaps to fill!")
            return

        # Initialize browser
        driver = self.init_browser()

        try:
            # Login and load chart
            self.login_tradingview(driver)
            self.load_chart(driver)

            # Backfill each gap
            for i, gap in enumerate(gaps, 1):
                print(f"\n{'='*80}")
                print(f"GAP {i}/{len(gaps)}")
                print(f"{'='*80}")

                self.backfill_gap(driver, gap['start'], gap['end'])

                if i < len(gaps):
                    cont = input("\nContinue to next gap? (y/n): ")
                    if cont.lower() != 'y':
                        break

        finally:
            print("\n🔒 Closing browser...")
            driver.quit()

        print("\n✅ Backfill complete!")
        print("\nNOTE: Review 'trading_data/ema_backfill.csv' and merge with main dataset")


if __name__ == '__main__':
    backfiller = EMABackfiller()
    backfiller.run()
