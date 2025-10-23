"""
Automated TradingView Login Script
Opens two Chrome browsers with different profiles and logs in automatically
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TradingViewAutoLogin:
    """Automates TradingView login for multiple browser instances"""
    
    def __init__(self):
        self.browsers = []
        
    def create_chrome_profile(self, profile_name):
        """Create Chrome options with a specific profile"""
        chrome_options = Options()
        
        # Use separate Chrome profiles
        user_data_dir = os.path.expanduser(f"~/Library/Application Support/Google/Chrome/TradingBot_{profile_name}")
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument(f"--profile-directory={profile_name}")
        
        # Useful options
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        return chrome_options
    
    def login_to_tradingview(self, driver, email, password, browser_num):
        """
        Login to TradingView with given credentials
        
        Args:
            driver: Selenium WebDriver instance
            email: TradingView email
            password: TradingView password
            browser_num: Browser number (for logging)
        """
        try:
            print(f"\n🌐 Browser {browser_num}: Opening TradingView...")
            driver.get("https://www.tradingview.com/accounts/signin/")
            
            # Wait for page to load
            time.sleep(2)
            
            # Click the Email button
            print(f"🔍 Browser {browser_num}: Looking for Email button...")
            email_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='Email'].emailButton-nKAw8Hvt"))
            )
            email_button.click()
            print(f"✅ Browser {browser_num}: Email button clicked")
            
            # Wait for email input to appear
            time.sleep(1)
            
            # Fill in username/email
            print(f"📧 Browser {browser_num}: Entering email...")
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "id_username"))
            )
            username_input.clear()
            username_input.send_keys(email)
            print(f"✅ Browser {browser_num}: Email entered")
            
            # Fill in password
            print(f"🔒 Browser {browser_num}: Entering password...")
            password_input = driver.find_element(By.ID, "id_password")
            password_input.clear()
            password_input.send_keys(password)
            print(f"✅ Browser {browser_num}: Password entered")
            
            # Submit the form
            print(f"🚀 Browser {browser_num}: Submitting login...")
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # Wait for redirect (login success)
            print(f"⏳ Browser {browser_num}: Waiting for login to complete...")
            time.sleep(5)
            
            # Check if we're on the main page
            if "tradingview.com/chart" in driver.current_url or "tradingview.com/" in driver.current_url:
                print(f"✅ Browser {browser_num}: Login successful!")
                return True
            else:
                print(f"⚠️  Browser {browser_num}: Login may have failed (check manually)")
                return False
                
        except Exception as e:
            print(f"❌ Browser {browser_num}: Login error - {e}")
            return False
    
    def open_browser(self, browser_num, email, password):
        """
        Open a browser and login to TradingView
        
        Args:
            browser_num: Browser number (1 or 2)
            email: TradingView email
            password: TradingView password
        """
        try:
            profile_name = f"Profile{browser_num}"
            chrome_options = self.create_chrome_profile(profile_name)
            
            print(f"\n{'='*70}")
            print(f"🚀 STARTING BROWSER {browser_num}")
            print(f"{'='*70}")
            
            # Create driver
            driver = webdriver.Chrome(options=chrome_options)
            self.browsers.append(driver)
            
            # Login
            success = self.login_to_tradingview(driver, email, password, browser_num)
            
            if success:
                print(f"\n✅ Browser {browser_num} ready!")
            else:
                print(f"\n⚠️  Browser {browser_num} may need manual intervention")
                
            return driver
            
        except Exception as e:
            print(f"❌ Failed to start browser {browser_num}: {e}")
            return None
    
    def start_both_browsers(self):
        """Start both browsers with different accounts"""
        print("\n" + "="*70)
        print("🤖 TRADINGVIEW AUTO-LOGIN")
        print("="*70)
        
        # Get credentials from .env
        email1 = os.getenv('TRADINGVIEW_EMAIL_1')
        password1 = os.getenv('TRADINGVIEW_PASSWORD_1')
        email2 = os.getenv('TRADINGVIEW_EMAIL_2')
        password2 = os.getenv('TRADINGVIEW_PASSWORD_2')
        
        # Validate credentials
        if not all([email1, password1, email2, password2]):
            print("\n❌ ERROR: Missing TradingView credentials in .env file!")
            print("\nPlease add to .env:")
            print("TRADINGVIEW_EMAIL_1=your_first_email@example.com")
            print("TRADINGVIEW_PASSWORD_1=your_first_password")
            print("TRADINGVIEW_EMAIL_2=your_second_email@example.com")
            print("TRADINGVIEW_PASSWORD_2=your_second_password")
            return False
        
        if email1 == "your_email_1@example.com" or email2 == "your_email_2@example.com":
            print("\n❌ ERROR: Please update .env with real TradingView credentials!")
            return False
        
        print(f"\n📧 Browser 1 will login with: {email1}")
        print(f"📧 Browser 2 will login with: {email2}")
        print("\n⏳ Starting browsers...\n")
        
        # Start browser 1
        driver1 = self.open_browser(1, email1, password1)
        time.sleep(2)
        
        # Start browser 2
        driver2 = self.open_browser(2, email2, password2)
        
        print("\n" + "="*70)
        print("✅ BOTH BROWSERS STARTED!")
        print("="*70)
        print("\n📌 What to do next:")
        print("   1. Check both browsers logged in successfully")
        print("   2. Navigate to your trading charts if needed")
        print("   3. Keep browsers open")
        print("   4. Start the trading bot: python3 main.py")
        print("\n⚠️  Keep this script running to keep browsers open!")
        print("   Press Ctrl+C when done to close browsers\n")
        
        return True
    
    def wait_until_stopped(self):
        """Keep browsers open until user stops the script"""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  Closing browsers...")
            self.close_all()
    
    def close_all(self):
        """Close all browser instances"""
        for i, browser in enumerate(self.browsers, 1):
            try:
                browser.quit()
                print(f"✅ Browser {i} closed")
            except:
                pass
        print("✅ All browsers closed")


def main():
    """Main function"""
    auto_login = TradingViewAutoLogin()
    
    if auto_login.start_both_browsers():
        auto_login.wait_until_stopped()
    else:
        print("\n❌ Failed to start browsers. Please check configuration.")


if __name__ == '__main__':
    main()
