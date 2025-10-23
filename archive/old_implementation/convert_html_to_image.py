#!/usr/bin/env python3
"""
Convert trading_analysis.html to PNG for Telegram
Uses selenium to capture the interactive chart as an image
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def convert_html_to_png(html_path, output_path='trading_data/trading_analysis.png', width=1920, height=1080):
    """
    Convert HTML file to PNG image
    
    Args:
        html_path: Path to HTML file
        output_path: Path to save PNG
        width: Screenshot width
        height: Screenshot height
        
    Returns:
        str: Path to PNG file if successful, None otherwise
    """
    
    if not os.path.exists(html_path):
        print(f"❌ HTML file not found: {html_path}")
        return None
    
    try:
        print(f"📸 Converting {html_path} to PNG...")
        
        # Setup Chrome in headless mode
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'--window-size={width},{height}')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Load HTML file
        abs_path = os.path.abspath(html_path)
        driver.get(f'file://{abs_path}')
        
        # Wait for plotly to render
        time.sleep(3)
        
        # Take screenshot
        driver.save_screenshot(output_path)
        driver.quit()
        
        if os.path.exists(output_path):
            file_size_kb = os.path.getsize(output_path) / 1024
            print(f"✅ Screenshot saved: {output_path} ({file_size_kb:.0f}KB)")
            return output_path
        else:
            print(f"❌ Screenshot failed: {output_path}")
            return None
            
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return None


if __name__ == '__main__':
    import sys
    
    html_file = sys.argv[1] if len(sys.argv) > 1 else 'trading_data/trading_analysis.html'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'trading_data/trading_analysis.png'
    
    result = convert_html_to_png(html_file, output_file)
    sys.exit(0 if result else 1)
