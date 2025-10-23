#!/usr/bin/env python3
"""
Simple EMA Backfill - Automatic Browser Mode
Script opens Chrome automatically and captures EMA data via mouse hovering
"""

import csv
import os
import re
import time
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pyautogui

# Load environment
load_dotenv()

# Enable fail-safe (move mouse to corner to abort)
pyautogui.FAILSAFE = True


class SimpleBackfiller:
    """Simple backfiller - you set up chart, script captures data"""

    def __init__(self):
        self.captured_data = []
        self.driver = None

    def init_browser(self):
        """
        Initialize Chrome browser automatically with remote debugging
        Returns driver instance
        """
        print("\n🌐 Initializing Chrome browser...")

        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("   ✅ Chrome browser opened!")
            return driver
        except Exception as e:
            print(f"   ❌ Failed to open Chrome: {e}")
            print("\n   💡 Make sure ChromeDriver is installed:")
            print("   brew install chromedriver")
            return None

    def connect_to_existing_chrome(self):
        """
        Connect to an already-open Chrome browser

        IMPORTANT: Start Chrome with remote debugging:

        On Mac:
        /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_dev"

        Then open TradingView in that Chrome window
        """
        print("\n🔌 Connecting to existing Chrome browser...")

        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("   ✅ Connected to Chrome!")
            return driver
        except Exception as e:
            print(f"   ❌ Could not connect: {e}")
            print("\n   💡 Make sure you started Chrome with:")
            print('   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_dev"')
            return None

    def read_indicators(self, driver):
        """Read current EMA indicators from TradingView"""
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

                    # Parse RGB color
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

    def extract_timestamp_from_tooltip(self, driver):
        """
        Extract timestamp from TradingView tooltip when hovering over a bar

        TradingView shows time in multiple places:
        1. Bottom axis label (appears on hover in black box)
        2. Legend area at top
        3. Crosshair tooltip
        """
        try:
            # Strategy 1: Look for axis label (black box on bottom axis)
            # These appear dynamically when hovering
            axis_selectors = [
                'div[class*="crosshair"]',
                'div[class*="price-axis"]',
                'div[class*="time-axis"]',
                'div[class*="pane-axis"]',
                'div[class*="axisHotspot"]',
            ]

            for selector in axis_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and ':' in text and len(text) < 30:  # Short time strings
                            # Check if it looks like a time (has numbers and colon)
                            if re.search(r'\d{1,2}:\d{2}', text):
                                return text
                except:
                    continue

            # Strategy 2: Check for visible tooltip/legend with time
            legend_selectors = [
                'div[class*="legend"]',
                'div[class*="pane-legend"]',
                'div[data-name="legend-source-item"]',
                'div[class*="sourceLabelContainer"]',
            ]

            for selector in legend_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text
                        if not text:
                            continue

                        # Look for date/time patterns
                        # Examples: "Oct 20, 12:45", "2025-10-20 12:45", "12:45"
                        if any(pattern in text for pattern in [':', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']):
                            # Filter out lines that are just EMA values (contain only numbers/commas)
                            if not re.match(r'^[\d,.\s]+$', text):
                                return text
                except:
                    continue

            # Strategy 3: Execute JavaScript to find any visible text with time format
            try:
                js_code = """
                let allElements = document.querySelectorAll('*');
                for (let elem of allElements) {
                    if (elem.offsetParent !== null) {  // Is visible
                        let text = elem.textContent || elem.innerText;
                        if (text && text.match(/\\d{1,2}:\\d{2}/) && text.length < 50) {
                            return text.trim();
                        }
                    }
                }
                return null;
                """
                result = driver.execute_script(js_code)
                if result:
                    return result
            except:
                pass

            return None

        except Exception as e:
            return None

    def debug_html_structure(self, driver):
        """
        Debug function to inspect HTML structure and find where timestamps are
        This will dump all potentially relevant elements
        """
        print("\n🔍 DEBUG: Inspecting HTML structure...")

        try:
            # Get all divs that might contain time/date info
            all_divs = driver.find_elements(By.CSS_SELECTOR, 'div')

            time_related = []
            for div in all_divs:
                # Check attributes
                class_name = div.get_attribute('class') or ''
                data_name = div.get_attribute('data-name') or ''
                text = div.text[:100] if div.text else ''  # First 100 chars

                # Look for time-related keywords
                if any(keyword in class_name.lower() for keyword in ['time', 'date', 'legend', 'tooltip', 'label', 'axis']):
                    time_related.append({
                        'class': class_name,
                        'data-name': data_name,
                        'text': text
                    })
                elif any(keyword in data_name.lower() for keyword in ['time', 'date', 'legend', 'tooltip', 'label']):
                    time_related.append({
                        'class': class_name,
                        'data-name': data_name,
                        'text': text
                    })
                elif text and any(pattern in text for pattern in [':', 'Oct', 'Nov', 'Dec', '2025', '2024']):
                    time_related.append({
                        'class': class_name,
                        'data-name': data_name,
                        'text': text
                    })

            print(f"\n   Found {len(time_related)} potentially time-related elements:")
            for i, elem in enumerate(time_related[:20]):  # Show first 20
                print(f"\n   Element #{i+1}:")
                print(f"      Class: {elem['class'][:80]}")
                print(f"      Data-name: {elem['data-name']}")
                print(f"      Text: {elem['text']}")

        except Exception as e:
            print(f"   ❌ Error during debug: {e}")

        print("\n")

    def analyze_ribbon(self, indicators):
        """Determine ribbon state from indicators"""
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

    def get_chart_bounds(self, driver):
        """Get chart area boundaries"""
        try:
            # Find canvas
            canvas = driver.find_element(By.CSS_SELECTOR, 'canvas')
            location = canvas.location
            size = canvas.size

            # Define usable area (exclude margins, axes, etc.)
            usable_left = location['x'] + 100
            usable_right = location['x'] + size['width'] - 50
            usable_top = location['y'] + 50
            usable_bottom = location['y'] + size['height'] - 100

            return {
                'left': usable_left,
                'right': usable_right,
                'top': usable_top,
                'bottom': usable_bottom,
                'width': usable_right - usable_left,
                'center_y': (usable_top + usable_bottom) // 2
            }
        except:
            # Default for 1920x1080 screen
            return {
                'left': 200,
                'right': 1700,
                'top': 150,
                'bottom': 900,
                'width': 1500,
                'center_y': 525
            }

    def automated_capture(self, driver, expected_bars=100):
        """
        Automatically hover over bars and capture data

        Args:
            driver: Selenium WebDriver connected to Chrome
            expected_bars: Approximate number of bars to capture
        """
        print(f"\n🤖 Starting automated capture...")
        print(f"   Expected bars: ~{expected_bars}")

        # Get chart boundaries
        chart = self.get_chart_bounds(driver)
        print(f"\n📊 Chart area: {chart['width']}px wide")

        # Calculate movement - use smaller steps for better accuracy
        # Assume ~60-100 bars visible on a typical 1-minute chart
        pixels_per_bar = chart['width'] / 80  # More conservative estimate
        step_size = max(2, pixels_per_bar * 0.3)  # Move 30% of a bar at a time (slower, more accurate)

        print(f"   Pixels per bar: ~{pixels_per_bar:.1f}px")
        print(f"   Step size: {step_size:.1f}px")

        print(f"\n🖱️  Starting scan from left to right...")
        print(f"   Move mouse to top-left corner to abort (failsafe)")
        print(f"   Press Ctrl+C to stop")
        print(f"\n   DEBUG MODE: Showing all reads (not just captures)\n")

        captured_count = 0
        last_price = None
        last_timestamp = None
        current_x = chart['left']
        read_count = 0

        try:
            while current_x < chart['right'] and captured_count < expected_bars:
                # Move mouse to position
                pyautogui.moveTo(current_x, chart['center_y'], duration=0.05)
                time.sleep(0.25)  # Longer wait for tooltip to appear

                # Read indicators
                indicators = self.read_indicators(driver)
                read_count += 1

                # Debug output every 10 reads
                if read_count % 10 == 0:
                    print(f"   📍 Read #{read_count}: x={current_x:.0f}px | Indicators found: {len(indicators)} | Has MMA5: {'MMA5' in indicators}")

                if indicators and 'MMA5' in indicators:
                    current_price = indicators['MMA5'].get('price')

                    # Try to get timestamp from chart tooltip
                    chart_timestamp = self.extract_timestamp_from_tooltip(driver)

                    # New bar detected
                    if current_price and current_price != last_price:
                        ribbon_state = self.analyze_ribbon(indicators)

                        # Use chart timestamp if available, otherwise use current time
                        timestamp = chart_timestamp if chart_timestamp else datetime.now().isoformat()

                        # Build data row
                        row = {
                            'timestamp': timestamp,
                            'price': current_price,
                            'ribbon_state': ribbon_state
                        }

                        # Add all EMAs
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

                        self.captured_data.append(row)
                        last_price = current_price
                        last_timestamp = timestamp
                        captured_count += 1

                        # Progress
                        progress = (captured_count / expected_bars) * 100 if expected_bars > 0 else 0
                        print(f"  ✅ Bar {captured_count}/{expected_bars} ({progress:.1f}%) | Price: {current_price} | {ribbon_state} | Time: {timestamp}")

                # Move to next position
                current_x += step_size

        except KeyboardInterrupt:
            print(f"\n\n⏸️  Stopped by user")
        except pyautogui.FailSafeException:
            print(f"\n\n🛑 Failsafe - mouse moved to corner")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n📊 Capture complete!")
        print(f"   Total reads: {read_count}")
        print(f"   Bars captured: {captured_count}")
        print(f"   Expected: {expected_bars}")
        print(f"   Capture rate: {(captured_count/read_count)*100:.1f}%" if read_count > 0 else "N/A")
        print(f"   Coverage: {(captured_count/expected_bars)*100:.1f}%" if expected_bars > 0 else "N/A")

        return self.captured_data

    def save_data(self, filename='trading_data/ema_backfill.csv'):
        """Save captured data to CSV"""
        if not self.captured_data:
            print("\n⚠️  No data to save")
            return

        print(f"\n💾 Saving {len(self.captured_data)} rows to {filename}...")

        # Headers
        headers = ['timestamp', 'price', 'ribbon_state']
        for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
            headers.extend([
                f'MMA{ema}_value',
                f'MMA{ema}_color',
                f'MMA{ema}_intensity'
            ])

        # Write CSV
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(self.captured_data)

        print(f"   ✅ Saved successfully")


def main():
    print("="*80)
    print("SIMPLE EMA BACKFILL - AUTOMATIC MODE")
    print("="*80)

    print("\n📋 SETUP:")
    print("   This script will:")
    print("   ✓ Automatically open Chrome browser")
    print("   ✓ You manually navigate to TradingView chart")
    print("   ✓ Script captures EMA data automatically")

    # Initialize
    backfiller = SimpleBackfiller()

    # Open Chrome automatically
    driver = backfiller.init_browser()
    if not driver:
        print("\n❌ Could not open Chrome browser.")
        return

    # Check if chart URL is in environment
    chart_url = os.getenv('TRADINGVIEW_CHART_URL') or os.getenv('CHART_URL') or os.getenv('TRADINGVIEW_5MIN_URL') or os.getenv('TRADINGVIEW_1MIN_URL')

    if chart_url:
        print(f"\n🔗 Opening TradingView chart from .env...")
        print(f"   URL: {chart_url[:60]}...")
        try:
            driver.get(chart_url)
            print("   ✅ Chart loaded!")
            print("\n📋 NEXT STEPS:")
            print("   1. In the Chrome window:")
            print("      - Log in to TradingView if prompted")
            print("      - Wait for chart to fully load with all EMAs")
            print("      - Set timeframe to 1-minute (if not already)")
            print("      - Navigate to the date you want to backfill (Oct 20, 12:45)")
            print("      - Zoom so you see ~80-100 bars on screen")
            print("   2. Come back here and press Enter")
        except Exception as e:
            print(f"   ⚠️  Could not load chart: {e}")
            print("\n📋 MANUAL SETUP:")
            print("   1. In the Chrome window that just opened:")
            print("      - Go to TradingView.com and log in")
            print("      - Open your chart with all EMAs visible")
            print("      - Set timeframe to 1-minute")
            print("      - Navigate to the date you want to backfill (Oct 20, 12:45)")
            print("      - Zoom so you see ~80-100 bars on screen")
            print("   2. Come back here and press Enter")
    else:
        print("\n💡 TIP: Add TRADINGVIEW_CHART_URL to .env for automatic chart loading")
        print("\n📋 NEXT STEPS:")
        print("   1. In the Chrome window that just opened:")
        print("      - Go to TradingView.com and log in")
        print("      - Open your chart with all EMAs visible")
        print("      - Set timeframe to 1-minute")
        print("      - Navigate to the date you want to backfill (Oct 20, 12:45)")
        print("      - Zoom so you see ~80-100 bars on screen")
        print("   2. Come back here and press Enter")

    input("\nPress Enter when your chart is ready...")

    # Verify chart is ready
    print("\n✅ Connected to Chrome!")
    print("\n🔍 Checking for TradingView indicators...")

    indicators = backfiller.read_indicators(driver)
    if not indicators:
        print("   ⚠️  No indicators found!")
        print("   Make sure TradingView chart is open with EMAs visible")
        return

    print(f"   ✅ Found {len(indicators)} indicators")

    # Ask if user wants to debug HTML first
    print("\n🔧 DEBUG MODE:")
    print("   Do you want to inspect HTML structure first?")
    print("   This will help find where TradingView stores timestamps")
    debug_mode = input("\n   Debug HTML first? (y/n, default n): ").strip().lower()

    if debug_mode == 'y':
        print("\n📍 Move your mouse over a bar on the chart...")
        input("   Press Enter when hovering over a bar: ")
        backfiller.debug_html_structure(driver)

        # Test timestamp extraction
        print("\n🧪 Testing timestamp extraction...")
        timestamp = backfiller.extract_timestamp_from_tooltip(driver)
        if timestamp:
            print(f"   ✅ Found timestamp: {timestamp}")
        else:
            print(f"   ⚠️  No timestamp found")

        cont = input("\n   Continue with capture? (y/n): ").strip().lower()
        if cont != 'y':
            print("\n   Exiting...")
            return

    # Get expected bars
    print("\n📊 How many bars do you want to capture?")
    print("   Examples:")
    print("   - 1 hour at 1min = 60 bars")
    print("   - 10 hours at 1min = 600 bars")
    print("   - 24 hours at 1min = 1440 bars")

    try:
        expected = int(input("\n   Expected bars (default 100): ") or "100")
    except:
        expected = 100

    # Get chart position
    chart = backfiller.get_chart_bounds(driver)
    print(f"\n📍 Chart detected:")
    print(f"   Left: {chart['left']}px")
    print(f"   Right: {chart['right']}px")
    print(f"   Center Y: {chart['center_y']}px")
    print(f"   Width: {chart['width']}px")

    # Test mouse movement
    print(f"\n🧪 Testing mouse movement...")
    print(f"   Watch your mouse - it should move to the chart!")
    time.sleep(2)

    # Move to start position
    pyautogui.moveTo(chart['left'], chart['center_y'], duration=1)
    print(f"   ✅ Mouse at start position")
    time.sleep(1)

    # Move to end position
    pyautogui.moveTo(chart['right'], chart['center_y'], duration=2)
    print(f"   ✅ Mouse at end position")
    time.sleep(1)

    # Return to start
    pyautogui.moveTo(chart['left'], chart['center_y'], duration=1)
    print(f"   ✅ Mouse back at start")

    # Start capture
    print(f"\n⚠️  READY TO CAPTURE {expected} BARS")
    print("   Make sure:")
    print("   ✓ Chart is at the start position")
    print("   ✓ Timeframe is 1-minute")
    print("   ✓ Chart shows ~100-150 bars")
    print("   ✓ Don't touch the mouse during capture")

    input("\nPress Enter to start automated capture...")

    # Capture
    data = backfiller.automated_capture(driver, expected_bars=expected)

    # Save
    if data:
        backfiller.save_data()
        print("\n✅ Backfill complete!")
        print("   Next step: python3 merge_backfill.py")
    else:
        print("\n⚠️  No data captured")


if __name__ == '__main__':
    main()
