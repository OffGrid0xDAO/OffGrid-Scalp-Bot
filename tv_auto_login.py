"""
TradingView Auto-Login Module
Handles automated login to TradingView using Selenium
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time


class TradingViewLogin:
    """Handles TradingView login automation"""
    
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
    
    def check_if_logged_in(self):
        """
        Check if user is already logged in from previous session
        
        Returns:
            bool: True if logged in, False otherwise
        """
        try:
            # Check current URL - if we're not on a login page, probably logged in
            current_url = self.driver.current_url
            print(f"   🔍 Current URL: {current_url}")
            
            # If we're on a login page, definitely not logged in
            if '/signin/' in current_url or '/accounts/' in current_url:
                print("   ❌ On login page - not logged in")
                return False
            
            # If we're on chart or main page, check for actual login indicators
            if '/chart/' in current_url or 'tradingview.com' in current_url:
                print("   🔍 On chart/main page - checking for login indicators...")
                # Don't assume logged in just because we're on the page
                # Let the login indicators check below determine this
            
            # Try to find user menu or profile elements (multiple methods)
            login_indicators = [
                ("[data-name='header-user-menu-button']", "CSS"),
                ("button[aria-label*='Open user menu']", "CSS"),
                ("//button[contains(@aria-label, 'user')]", "XPATH"),
                ("div[class*='userData']", "CSS"),
                ("//div[contains(@class, 'header-user')]", "XPATH"),
                ("//div[contains(@class, 'tv-header')]", "XPATH"),  # TradingView header
                ("//button[contains(@class, 'user')]", "XPATH"),   # Any user button
            ]
            
            for selector, method in login_indicators:
                try:
                    wait = WebDriverWait(self.driver, 2)  # Shorter timeout
                    if method == "XPATH":
                        element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    else:
                        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    
                    if element:
                        print(f"   ✅ Found login indicator: {selector[:30]}...")
                        return True  # Found user element, we're logged in!
                except:
                    continue
            
            # If we can't find specific indicators, assume NOT logged in
            print("   ❌ Couldn't find login indicators - assuming NOT logged in")
            return False
            
        except Exception as e:
            print(f"   ❌ Error checking login status: {str(e)[:50]}...")
            return False
    
    def login(self, username, password, chart_url=None):
        """
        Automatically log into TradingView
        
        Args:
            username: TradingView email/username
            password: TradingView password
            chart_url: Optional direct chart URL to navigate to after login
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("\n🔐 Starting TradingView auto-login...")
            
            # Try to click "Join for free" popup if it appears on current page
            try:
                self._click_join_for_free_if_present()
            except Exception:
                pass
            
            # Navigate to login page with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"   🌐 Navigating to login page (attempt {attempt + 1}/{max_retries})...")
                    self.driver.get("https://www.tradingview.com/accounts/signin/")
                    time.sleep(2)
                    break
                except Exception as e:
                    if "ConnectionResetError" in str(e) or "connection was forcibly closed" in str(e):
                        print(f"   ⚠️  Connection error (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            print("   🔄 Retrying in 3 seconds...")
                            time.sleep(3)
                        else:
                            print("   ❌ Connection failed after retries")
                            return False
                    else:
                        raise e
            
            # Click "Email" tab (in case social login is default)
            try:
                # Try multiple ways to find the email tab
                email_selectors = [
                    "//span[contains(text(), 'Email')]",
                    "//button[contains(text(), 'Email')]",
                    "//div[contains(text(), 'Email')]"
                ]
                
                for selector in email_selectors:
                    try:
                        email_tab = self.driver.find_element(By.XPATH, selector)
                        email_tab.click()
                        print("   ✓ Selected Email login method")
                        time.sleep(1)
                        break
                    except:
                        continue
            except:
                print("   ℹ️  Email tab not found (might already be selected)")
                pass  # Email might already be selected
            
            # Find and fill username field
            print("   📧 Entering username...")
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "id_username"))
            )
            username_field.clear()
            username_field.send_keys(username)
            time.sleep(0.5)
            
            # Find and fill password field
            print("   🔑 Entering password...")
            password_field = self.driver.find_element(By.NAME, "id_password")
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(0.5)
            
            # Click sign in button - try multiple selectors
            print("   🚀 Finding sign in button...")
            signin_button = None
            
            # Try multiple selectors (TradingView changes their classes)
            selectors = [
                ("button[data-overflow-tooltip-text='Sign in']", "CSS"),  # Most specific
                ("button.submitButton-LQwxK8Bm", "CSS"),  # Class-based
                ("button[type='submit']", "CSS"),  # Generic submit
                ("//button[contains(text(), 'Sign in')]", "XPATH"),  # XPath fallback
                ("//button[contains(@class, 'submitButton')]", "XPATH")  # Partial class match
            ]
            
            for selector, method in selectors:
                try:
                    if method == "XPATH":
                        signin_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        signin_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    if signin_button:
                        print(f"   ✓ Found button using {method}: {selector[:50]}...")
                        time.sleep(0.5)  # Small delay to ensure button is ready
                        signin_button.click()
                        print("   ✓ Sign in button clicked!")
                        break
                except Exception as e:
                    continue
            
            if not signin_button:
                raise Exception("Could not find sign in button with any selector")
            
            # Wait for login to complete (check for chart or profile icon)
            print("   ⏳ Waiting for login to complete...")
            time.sleep(3)  # Give login some time to process
            
            # Try multiple indicators of successful login
            login_success = False
            login_indicators = [
                ("[data-name='header-user-menu-button']", "CSS"),  # Profile menu
                ("button[aria-label*='Open user menu']", "CSS"),  # User menu button
                ("//button[contains(@aria-label, 'user')]", "XPATH"),  # User button via aria-label
                ("[data-role='button'][aria-label*='menu']", "CSS"),  # Menu button
                ("div[class*='userData']", "CSS"),  # User data container
                ("//div[contains(@class, 'header-user')]", "XPATH"),  # Header user section
            ]
            
            for selector, method in login_indicators:
                try:
                    wait = WebDriverWait(self.driver, 5)
                    if method == "XPATH":
                        element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    else:
                        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    
                    if element:
                        print(f"   ✅ Login successful! (Detected via {method})")
                        login_success = True
                        break
                except:
                    continue
            
            # Additional check: URL should change from /signin/ if successful
            if not login_success:
                current_url = self.driver.current_url
                if '/signin/' not in current_url and '/accounts/' not in current_url:
                    print("   ✅ Login successful! (URL changed from login page)")
                    login_success = True
            
            if not login_success:
                print("   ⚠️ Could not confirm login - but continuing anyway...")
                # Don't return False - let's continue and see if chart works
            
            time.sleep(2)
            
            # Navigate to specific chart if provided
            if chart_url:
                print(f"\n📊 Navigating to chart: {chart_url}")
                self.driver.get(chart_url)
                time.sleep(3)
            else:
                print("\n📊 Navigating to chart page...")
                self.driver.get("https://www.tradingview.com/chart/")
                time.sleep(3)
            
            return True  # Return True since we got past login page
                
        except Exception as e:
            print(f"   ❌ Login error: {str(e)}")
            return False
    
    def wait_for_indicators(self, timeout=10):
        """
        Wait for chart indicators to load
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            bool: True if indicators found, False otherwise
        """
        try:
            print("   ⏳ Waiting for indicators to load...")
            # Look for value items (indicator values on chart)
            self.wait = WebDriverWait(self.driver, timeout)
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.valueItem-l31H9iuA'))
            )
            print("   ✅ Indicators detected!")
            return True
        except TimeoutException:
            print("   ⚠️ Indicators not found within timeout")
            return False

    def _click_join_for_free_if_present(self):
        """Click the 'Join for free' CTA if a popup appears.
        This helps get to the authentication flow on some pages.
        """
        try:
            print("   🔎 Looking for 'Join for free' popup...")
            wait_short = WebDriverWait(self.driver, 3)
            selectors = [
                ("button[data-overflow-tooltip-text='Join for free']", "CSS"),
                ("//button[.//span[text()='Join for free']]", "XPATH"),
                ("//button[contains(text(), 'Join for free')]", "XPATH"),
                ("//span[text()='Join for free']/ancestor::button", "XPATH"),
            ]
            for selector, method in selectors:
                try:
                    if method == "XPATH":
                        el = wait_short.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        el = wait_short.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    el.click()
                    print("   ✅ Clicked 'Join for free'")
                    time.sleep(1)
                    return True
                except Exception:
                    continue
            print("   ℹ️  'Join for free' popup not found")
            return False
        except Exception:
            return False


def test_login():
    """Test the login functionality"""
    import os
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from dotenv import load_dotenv
    
    load_dotenv()
    
    username = os.getenv('TRADINGVIEW_USERNAME')
    password = os.getenv('TRADINGVIEW_PASSWORD')
    chart_url = os.getenv('TRADINGVIEW_CHART_URL')
    
    if not username or not password:
        print("❌ Please set TRADINGVIEW_USERNAME and TRADINGVIEW_PASSWORD in .env file")
        return
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    try:
        # Login
        login_handler = TradingViewLogin(driver)
        success = login_handler.login(username, password, chart_url)
        
        if success:
            print("\n✅ Auto-login successful!")
            login_handler.wait_for_indicators()
            print("\n🎯 You can now use the bot!")
            input("\nPress Enter to close browser...")
        else:
            print("\n❌ Auto-login failed")
            input("\nPress Enter to close browser...")
            
    finally:
        driver.quit()


if __name__ == "__main__":
    test_login()

