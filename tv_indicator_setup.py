"""
TradingView Indicator Auto-Setup
Automatically adds Annii's Ribbon indicator to the chart
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)


class TradingViewIndicatorSetup:
    """Handles automatic setup of Annii's Ribbon indicator"""
    
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
    
    def setup_ribbon_indicator(self):
        """
        Automatically set up Annii's Ribbon indicator
        Returns True if successful, False otherwise
        """
        try:
            print("\n🔧 Setting up Annii's Ribbon indicator automatically...")
            print("   ⏱️  Timeout: 30 seconds max")
            
            # Step 0: Handle cookie consent banner first
            if not self._handle_cookie_banner():
                print("   ⚠️  Could not handle cookie banner - please accept cookies manually")
            
            # Step 1: Click on Indicators button (with timeout)
            if not self._click_indicators_button():
                print("   ⚠️  Auto-setup failed - please click 'Indicators' manually")
                return False
            
            # Step 2: Check if already in favorites
            if self._check_favorites():
                print("   ✅ Found in favorites - clicking it!")
                return self._click_favorite_ribbon()
            
            # Step 3: Search for "RIBBON FOR SCALPING"
            if not self._search_ribbon():
                print("   ⚠️  Search failed - please search manually")
                return False
            
            # Step 4: Click on first result
            if not self._click_first_result():
                print("   ⚠️  Could not click result - please click manually")
                return False
            
            # Step 5: Add to favorites
            if not self._add_to_favorites():
                print("   ⚠️  Could not add to favorites - not critical")
            
            print("   ✅ Annii's Ribbon indicator added successfully!")
            return True
            
        except Exception as e:
            print(f"   ❌ Error setting up indicator: {str(e)[:50]}...")
            return False
    
    def _handle_cookie_banner(self):
        """Handle cookie consent banner"""
        try:
            print("   🍪 Checking for cookie banner...")
            
            # Cookie banner selectors (exact selectors from TradingView)
            cookie_selectors = [
                "button.acceptAll-ICNSJWAI",  # Exact class from your HTML
                "button[data-overflow-tooltip-text='Accept all']",  # Data attribute
                "//button[contains(@class, 'acceptAll-ICNSJWAI')]",  # XPath version
                "//button[contains(text(), 'Accept all')]",  # Text content
                "//button[contains(text(), 'Accept')]",  # Partial text
                "button[class*='acceptAll']",  # Partial class match
                "button[class*='accept']"  # Generic accept
            ]
            
            short_wait = WebDriverWait(self.driver, 3)
            
            for selector in cookie_selectors:
                try:
                    if selector.startswith("//"):
                        element = short_wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        element = short_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                    print("   ✅ Found cookie banner - accepting...")
                    element.click()
                    time.sleep(1)
                    return True
                except TimeoutException:
                    continue
            
            print("   ℹ️  No cookie banner found")
            return True  # Not critical if no banner
            
        except Exception as e:
            print(f"   ⚠️  Cookie banner handling failed: {str(e)[:30]}...")
            return True  # Not critical
    
    def _click_indicators_button(self):
        """Click the Indicators button"""
        try:
            print("   🔍 Looking for Indicators button...")
            
            # Multiple selectors for the Indicators button
            indicators_selectors = [
                "#header-toolbar-indicators button[data-name='open-indicators-dialog']",
                "div#header-toolbar-indicators button[data-name='open-indicators-dialog']",
                "button[data-name='open-indicators-dialog']",
                "button[aria-label*='Indicators']",
                "//button[contains(@aria-label, 'Indicators')]",
                "//button[contains(text(), 'Indicators')]",
                "button[data-tooltip*='Indicators']"
            ]
            
            # Use shorter timeout for faster response
            short_wait = WebDriverWait(self.driver, 5)
            
            for selector in indicators_selectors:
                try:
                    if selector.startswith("//"):
                        element = short_wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    else:
                        element = short_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    
                    print(f"   ✅ Found Indicators button: {selector[:45]}...")
                    # Ensure visible and in view
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    except Exception:
                        pass
                    
                    try:
                        short_wait.until(EC.element_to_be_clickable((By.XPATH, selector)) if selector.startswith("//") else EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    except Exception:
                        pass
                    
                    try:
                        element.click()
                    except (ElementClickInterceptedException, StaleElementReferenceException, Exception):
                        # Fallback to JS click
                        try:
                            self.driver.execute_script("arguments[0].click();", element)
                        except Exception:
                            # Final fallback: use keyboard hotkey '/'
                            try:
                                ActionChains(self.driver).send_keys(Keys.SLASH).perform()
                            except Exception:
                                raise
                    time.sleep(1)
                    return True
                    
                except TimeoutException:
                    print(f"   ⚠️  Selector {selector[:20]}... not found, trying next...")
                    continue
            
            print("   ❌ Could not find Indicators button - trying manual approach")
            print("   🔧 Please click 'Indicators' button manually in the browser")
            return False
            
        except Exception as e:
            print(f"   ❌ Error clicking Indicators button: {str(e)[:50]}...")
            return False
    
    def _check_favorites(self):
        """Check if Ribbon is already in favorites"""
        try:
            print("   🔍 Checking favorites...")
            
            # Look for favorites section
            favorites_selectors = [
                "//div[contains(@class, 'favorites')]",
                "//div[contains(text(), 'Favorites')]",
                "//div[contains(@class, 'favorite')]"
            ]
            
            for selector in favorites_selectors:
                try:
                    favorites_section = self.driver.find_element(By.XPATH, selector)
                    if "ribbon" in favorites_section.text.lower() or "annii" in favorites_section.text.lower():
                        print("   ✅ Found Ribbon in favorites!")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"   ⚠️  Could not check favorites: {str(e)[:30]}...")
            return False
    
    def _search_ribbon(self):
        """Search for 'RIBBON FOR SCALPING'"""
        try:
            print("   🔍 Searching for 'RIBBON FOR SCALPING'...")
            
            # Find search input
            search_selectors = [
                "input[id='indicators-dialog-search-input']",
                "input[placeholder='Search']",
                "input[type='text']",
                "//input[@role='searchbox']"
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    if selector.startswith("//"):
                        search_input = self.driver.find_element(By.XPATH, selector)
                    else:
                        search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not search_input:
                print("   ❌ Could not find search input")
                return False
            
            # Clear and type search term
            search_input.clear()
            search_input.send_keys("RIBBON FOR SCALPING")
            time.sleep(2)
            
            print("   ✅ Search completed")
            return True
            
        except Exception as e:
            print(f"   ❌ Error searching: {str(e)[:50]}...")
            return False
    
    def _click_first_result(self):
        """Click on the first search result"""
        try:
            print("   🔍 Looking for first result...")
            
            # Wait for results to appear
            time.sleep(2)
            
            # Look for result items
            result_selectors = [
                "//div[contains(@class, 'result')]//button",
                "//div[contains(@class, 'item')]//button",
                "//button[contains(@class, 'result')]",
                "//div[contains(@class, 'search')]//button"
            ]
            
            for selector in result_selectors:
                try:
                    results = self.driver.find_elements(By.XPATH, selector)
                    if results:
                        print(f"   ✅ Found {len(results)} results, clicking first one")
                        results[0].click()
                        time.sleep(2)
                        return True
                except:
                    continue
            
            print("   ❌ Could not find search results")
            return False
            
        except Exception as e:
            print(f"   ❌ Error clicking result: {str(e)[:50]}...")
            return False
    
    def _add_to_favorites(self):
        """Add the indicator to favorites"""
        try:
            print("   ⭐ Adding to favorites...")
            
            # Look for favorite button
            favorite_selectors = [
                "span[aria-label='Add to favorites']",
                "//span[contains(@class, 'favorite')]",
                "//button[contains(@aria-label, 'favorite')]",
                "//span[contains(@class, 'favorite-_FRQhM5Y')]"
            ]
            
            for selector in favorite_selectors:
                try:
                    if selector.startswith("//"):
                        favorite_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        favorite_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    favorite_btn.click()
                    time.sleep(1)
                    print("   ✅ Added to favorites!")
                    return True
                except:
                    continue
            
            print("   ⚠️  Could not find favorite button (might already be favorited)")
            return True  # Not critical if we can't find it
            
        except Exception as e:
            print(f"   ⚠️  Error adding to favorites: {str(e)[:30]}...")
            return True  # Not critical
    
    def _click_favorite_ribbon(self):
        """Click on Ribbon from favorites"""
        try:
            print("   🔍 Looking for Ribbon in favorites...")
            
            # Look for Ribbon in favorites
            ribbon_selectors = [
                "//div[contains(text(), 'Ribbon')]",
                "//div[contains(text(), 'ANNII')]",
                "//button[contains(text(), 'Ribbon')]",
                "//div[contains(@class, 'favorite')]//div[contains(text(), 'Ribbon')]"
            ]
            
            for selector in ribbon_selectors:
                try:
                    ribbon_element = self.driver.find_element(By.XPATH, selector)
                    ribbon_element.click()
                    time.sleep(2)
                    print("   ✅ Clicked Ribbon from favorites!")
                    return True
                except:
                    continue
            
            print("   ❌ Could not find Ribbon in favorites")
            return False
            
        except Exception as e:
            print(f"   ❌ Error clicking favorite Ribbon: {str(e)[:50]}...")
            return False
    
    def wait_for_indicators(self, timeout=30):
        """
        Wait for indicators to appear in the values panel
        Returns True if indicators are found, False otherwise
        """
        try:
            print(f"   ⏳ Waiting for indicators to appear (timeout: {timeout}s)...")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                # If a Symbol Search popup is overlaying the chart, close it
                self._close_symbol_search_if_present()

                # STRICT CHECK: Look for specific MMA values with data-test-id-value-title
                try:
                    mma_values = self.driver.find_elements(By.CSS_SELECTOR, "div[data-test-id-value-title*='MMA']")
                    if len(mma_values) >= 10:  # Must have at least 10 MMA values
                        # Double-check by looking for specific MMA numbers
                        mma_titles = [elem.get_attribute('data-test-id-value-title') for elem in mma_values]
                        mma_numbers = [title for title in mma_titles if 'MMA' in title and any(char.isdigit() for char in title)]
                        
                        if len(mma_numbers) >= 10:
                            print(f"   ✅ Found {len(mma_numbers)} MMA indicators: {mma_numbers[:5]}...")
                            return True
                except Exception:
                    pass

                # FALLBACK: Check for "Annii's Ribbon" text
                try:
                    annis = self.driver.find_elements(By.XPATH, "//*[contains(text(), \"Annii's Ribbon\")]")
                    if annis:
                        print("   ✅ 'Annii's Ribbon' label found")
                        return True
                except Exception:
                    pass

                time.sleep(1)
            
            print("   ⚠️  Timeout waiting for indicators")
            return False
            
        except Exception as e:
            print(f"   ❌ Error waiting for indicators: {str(e)[:50]}...")
            return False

    def _close_symbol_search_if_present(self):
        """Close the 'Symbol Search' popup if it is visible."""
        try:
            selectors = [
                ("button[data-qa-id='close']", "CSS"),
                ("button.close-BZKENkhT", "CSS"),
                ("//button[@data-qa-id='close']", "XPATH"),
                ("//span[text()='Close menu']/ancestor::button", "XPATH"),
            ]
            for selector, method in selectors:
                try:
                    if method == "XPATH":
                        el = WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        el = WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    el.click()
                    print("   ✅ Closed 'Symbol Search' popup")
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False
