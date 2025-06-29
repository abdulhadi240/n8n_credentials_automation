from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import pyperclip  # For copying to clipboard


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="N8N OAuth Automation API", version="1.0.0")

class OAuthResponse(BaseModel):
    success: bool
    google_auth_url: str = None
    message: str
    error: str = None

class AuthStorage:
    google_auth_url: str = None


# Pydantic models for request/response
class AutomationRequest(BaseModel):
    action: str = "login_and_navigate"

class AutomationResponse(BaseModel):
    success: bool
    message: str
    details: dict = {}




def setup_driver():
    """Setup Chrome driver with options"""
    chrome_options = Options()
    # Uncomment the next line to run in headless mode
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def login_to_n8n(driver):
    """Login to N8N platform"""
    try:
        # Navigate to the login page
        print("Navigating to N8N login page...")
        driver.get("https://n8n.srv876975.hstgr.cloud/")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 15)
        
        # Find and fill email field
        print("Looking for email field...")
        email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[id='email']")))
        email_field.clear()
        email_field.send_keys("mike.jackson@realtyamp.ai")
        print("Email entered successfully")
        
        # Find and fill password field
        print("Looking for password field...")
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password'], input[id='password']")
        password_field.clear()
        password_field.send_keys("Legal%3490")
        print("Password entered successfully")
        
        # Find and click sign in button
        print("Looking for sign in button...")
        # Try multiple possible selectors for the sign in button
        sign_in_selectors = [
            "button[type='submit']",
            "button:contains('Sign in')",
            "input[type='submit']",
            "button:contains('Login')",
            ".btn-primary",
            "[data-test-id='sign-in-button']"
        ]
        
        sign_in_button = None
        for selector in sign_in_selectors:
            try:
                if ":contains(" in selector:
                    # Use XPath for text-based search
                    xpath_selector = f"//button[contains(text(), 'Sign in') or contains(text(), 'Login')]"
                    sign_in_button = driver.find_element(By.XPATH, xpath_selector)
                else:
                    sign_in_button = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except NoSuchElementException:
                continue
        
        if not sign_in_button:
            # Fallback: look for any button element
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                if any(word in button.text.lower() for word in ['sign', 'login', 'submit']):
                    sign_in_button = button
                    break
        
        if sign_in_button:
            driver.execute_script("arguments[0].click();", sign_in_button)
            print("Sign in button clicked")
        else:
            print("Could not find sign in button, trying form submission...")
            # Try submitting the form directly
            password_field.submit()
        
        # Wait for login to complete (10 seconds as requested)
        print("Waiting for login to complete...")
        time.sleep(10)
        
        # Check if login was successful by looking for common post-login elements
        try:
            # Wait for a common element that appears after login
            wait.until(EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='main-content']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".main-content")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav")),
                EC.url_contains("dashboard")
            ))
            print("Login successful!")
            return True
        except TimeoutException:
            print("Login may have failed or page is still loading...")
            return True  # Continue anyway
            
    except Exception as e:
        print(f"Error during login: {str(e)}")
        return False
    
def navigate_to_credentials_page_id(driver):
    """Navigate to the credentials creation page and click on the first credential card"""
    try:
        print("Navigating to credentials creation page...")
        driver.get("https://n8n.realtyamp.ai/projects/N5IZDJlcXNhJSNRP/credentials/create")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        print("Successfully navigated to credentials page")
        
        # Wait for 5 seconds as requested
        print("Waiting 5 seconds before clicking on first card...")
        time.sleep(5)
        
        # Try to find and click the first credential card
        print("Looking for the first credential card...")
        
        # Multiple selectors to find the first card
        card_selectors = [
            'div[data-test-id="resources-list-item"]',
            '.card._card_1vkmg_123._cardLink_14jai_123',
            '.card[data-test-id="resources-list-item"]',
            '.recycle-scroller-item .card'
        ]
        
        first_card = None
        for selector in card_selectors:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    first_card = cards[0]
                    print(f"Found first card using selector: {selector}")
                    break
            except NoSuchElementException:
                continue
        
        if first_card:
            # Scroll the card into view if needed
            driver.execute_script("arguments[0].scrollIntoView(true);", first_card)
            time.sleep(1)  # Short wait after scrolling
            
            # Try to click the card
            try:
                # First try regular click
                first_card.click()
                print("Successfully clicked the first credential card")
            except Exception as e:
                print(f"Regular click failed, trying JavaScript click: {e}")
                # Fallback to JavaScript click
                driver.execute_script("arguments[0].click();", first_card)
                print("Successfully clicked the first credential card using JavaScript")
            
            # Wait a moment for the page to respond
            time.sleep(2)
            return True
            
        else:
            print("Could not find any credential cards on the page")
            return False
            
    except Exception as e:
        print(f"Error navigating to credentials page or clicking card: {str(e)}")
        traceback.print_exc()
        return False

def handle_modal_and_extract_value_id(driver):
    """Handle the modal that opens after clicking the credential card, click Details, and extract the value"""
    try:
        print("Waiting for modal to appear...")
        wait = WebDriverWait(driver, 15)
        
        # Wait for modal to appear - try multiple possible modal selectors
        modal_selectors = [
            ".el-dialog",
            ".modal",
            ".dialog",
            "[role='dialog']",
            ".el-dialog__wrapper"
        ]
        
        modal = None
        for selector in modal_selectors:
            try:
                modal = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"Modal found using selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not modal:
            print("Modal not found, trying to proceed anyway...")
            time.sleep(3)  # Give some time for modal to appear
        
        # Look for and click the "Details" button/link
        print("Looking for Details button...")
        details_selectors = [
            "//button[contains(text(), 'Details')]",
            "//a[contains(text(), 'Details')]",
            "//span[contains(text(), 'Details')]",
            "//div[contains(text(), 'Details')]",
            "[data-test-id*='details']",
            ".details-button",
            ".details-link"
        ]
        
        details_element = None
        for selector in details_selectors:
            try:
                if selector.startswith("//"):
                    # XPath selector
                    details_element = driver.find_element(By.XPATH, selector)
                else:
                    # CSS selector
                    details_element = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"Details element found using selector: {selector}")
                break
            except NoSuchElementException:
                continue
        
        if details_element:
            # Scroll into view and click
            driver.execute_script("arguments[0].scrollIntoView(true);", details_element)
            time.sleep(1)
            
            try:
                details_element.click()
                print("Successfully clicked Details")
            except Exception as e:
                print(f"Regular click failed, trying JavaScript click: {e}")
                driver.execute_script("arguments[0].click();", details_element)
                print("Successfully clicked Details using JavaScript")
            
            # Wait for details section to load
            time.sleep(2)
        else:
            print("Details button not found, proceeding to look for value...")
        
        # Now look for the value in the specified div
        print("Looking for value in the specified div...")
        
        # Multiple strategies to find the value
        value_selectors = [
            'div.el-col.el-col-16 span.n8n-text',
            '.valueLabel span.n8n-text',
            'div[class*="valueLabel"] span',
            '.el-col-16 span.n8n-text',
            'span.n8n-text.compact.size-medium.regular'
        ]
        
        extracted_value = None
        for selector in value_selectors:
            try:
                value_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in value_elements:
                    text = element.text.strip()
                    # Look for a value that matches the pattern (alphanumeric string)
                    if text and len(text) > 10 and text.isalnum():
                        extracted_value = text
                        print(f"Found value using selector {selector}: {extracted_value}")
                        break
                if extracted_value:
                    break
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
                continue
        
        # If not found, try a more generic approach
        if not extracted_value:
            print("Trying generic approach to find the value...")
            try:
                # Look for any span with text that looks like an ID/token
                all_spans = driver.find_elements(By.TAG_NAME, "span")
                for span in all_spans:
                    text = span.text.strip()
                    if text and len(text) > 10 and len(text) < 50 and text.replace('_', '').replace('-', '').isalnum():
                        extracted_value = text
                        print(f"Found potential value: {extracted_value}")
                        break
            except Exception as e:
                print(f"Error in generic search: {e}")
        
        if extracted_value:
            # Copy to clipboard
            try:
                pyperclip.copy(extracted_value)
                print(f"Value copied to clipboard: {extracted_value}")
            except Exception as e:
                print(f"Could not copy to clipboard: {e}")
            
            return extracted_value
        else:
            print("Could not find the value in the modal")
            return None
            
    except Exception as e:
        print(f"Error handling modal and extracting value: {str(e)}")
        traceback.print_exc()
        return None

def run_automation():
    """Main automation function"""
    driver = None
    try:
        print("Starting N8N automation...")
        
        # Setup Chrome driver
        driver = setup_driver()
        if not driver:
            return {"success": False, "message": "Failed to setup Chrome driver"}
        
        # Login to N8N
        if not login_to_n8n(driver):
            return {"success": False, "message": "Failed to login to N8N"}
        
        # Navigate to credentials page and click first card
        if not navigate_to_credentials_page_id(driver):
            return {"success": False, "message": "Failed to navigate to credentials page or click first card"}
        
        # Handle modal and extract value
        extracted_value = handle_modal_and_extract_value_id(driver)
        if not extracted_value:
            return {"success": False, "message": "Failed to extract value from modal"}
        
        print("Automation completed successfully!")
        return {
            "success": True, 
            "message": "Successfully logged in, clicked first credential card, and extracted value",
            "current_url": driver.current_url,
            "extracted_value": extracted_value
        }
        
    except Exception as e:
        error_msg = f"Automation failed: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return {"success": False, "message": error_msg}
    
    finally:
        if driver:
            print("Closing browser...")
            time.sleep(5)  # Keep browser open for 5 seconds to see result
            driver.quit()


def navigate_to_credentials_page(driver):
    """Navigate to the credentials creation page"""
    try:
        print("Navigating to credentials creation page...")
        driver.get("https://n8n.realtyamp.ai/projects/N5IZDJlcXNhJSNRP/credentials/create")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        print("Successfully navigated to credentials page")
        return True
        
    except Exception as e:
        print(f"Error navigating to credentials page: {str(e)}")
        return False


def create_gmail_oauth_credential(driver):
    """Create Gmail OAuth2 API credential"""
    try:
        wait = WebDriverWait(driver, 15)
        
        # Look for the select dropdown element
        print("Looking for credential type select dropdown...")
        
        # Based on the HTML structure, find the select dropdown
        select_selectors = [
            "[data-test-id='new-credential-type-select']",
            ".n8n-select",
            ".el-select",
            ".select-trigger",
            "input[placeholder='Search for app...']"
        ]
        
        select_element = None
        for selector in select_selectors:
            try:
                select_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"Found select element with selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not select_element:
            print("Could not find select dropdown element")
            return False
        
        # Click on the select dropdown to open it
        print("Clicking on select dropdown...")
        driver.execute_script("arguments[0].click();", select_element)
        
        # Wait for dropdown to open
        time.sleep(2)
        
        # Now look for the search input that becomes active when dropdown is open
        try:
            search_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Search for app...']")))
            print("Found search input in opened dropdown")
            
            # Clear and enter the search term
            search_input.clear()
            search_input.send_keys("Gmail OAuth2 API")
            print("Entered 'Gmail OAuth2 API' in search field")
            
            # Step 1: Press Enter after typing
            from selenium.webdriver.common.keys import Keys
            search_input.send_keys(Keys.ENTER)
            print("Pressed Enter after typing Gmail OAuth2 API")
            
            # Wait 5 seconds
            print("Waiting 5 seconds...")
            time.sleep(5)
            
            # Step 2: Press Tab to navigate to the option
            search_input.send_keys(Keys.TAB)
            print("Pressed Tab to navigate to option")
            
            # Wait 5 seconds
            print("Waiting 5 seconds...")
            time.sleep(5)
            
            # Step 3: Press Enter to select the option
            # Get the currently focused element and press Enter
            active_element = driver.switch_to.active_element
            active_element.send_keys(Keys.ENTER)
            print("Pressed Enter to select the option")
            
            # Wait 5 seconds
            print("Waiting 5 seconds...")
            time.sleep(5)

            active_element = driver.switch_to.active_element
            active_element.send_keys(Keys.TAB)
            print("Pressed Tab to navigate to credential name field")
                
            # Wait 2 seconds
            print("Waiting 2 seconds...")
            time.sleep(2)
            
            # Step 5: Enter the credential name "Hadi Testing"
            active_element = driver.switch_to.active_element
            active_element.clear()  # Clear any existing text
            active_element.send_keys("Hadi Testing")
            print("Entered 'Hadi Testing' as credential name")
            
            # Wait 2 seconds
            print("Waiting 2 seconds...")
            time.sleep(2)
        
        except TimeoutException:
            print("Could not find search input after opening dropdown")
            return False
        
        # Look for and click Continue button with improved selectors and wait conditions
        print("Looking for Continue button...")
        
        # First, wait for the button to be present and enabled
        continue_button = None
        
        # Try the exact selector from your HTML first
        try:
            continue_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-id='new-credential-type-button']")))
            print("Found Continue button with data-test-id")
        except TimeoutException:
            print("Button with data-test-id not found, trying other selectors...")
            
            # Try alternative selectors
            continue_selectors = [
                "button[data-test-id='new-credential-type-button']",
                "[data-test-id='new-credential-type-button']",
                "//button[@data-test-id='new-credential-type-button']",
                "//button[contains(text(), 'Continue')]",
                "//button[contains(@class, 'primary') and contains(text(), 'Continue')]",
                "//button[contains(@class, 'button') and contains(text(), 'Continue')]",
                ".button.primary",
                "button.primary"
            ]
            
            for selector in continue_selectors:
                try:
                    if selector.startswith("//"):
                        continue_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        continue_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    print(f"Found Continue button with selector: {selector}")
                    break
                except TimeoutException:
                    continue
        
        if continue_button:
            # Scroll to the button to ensure it's visible
            driver.execute_script("arguments[0].scrollIntoView(true);", continue_button)
            time.sleep(1)
            
            # Try multiple click methods
            try:
                # Method 1: JavaScript click
                driver.execute_script("arguments[0].click();", continue_button)
                print("Clicked Continue button using JavaScript")
            except Exception as e:
                print(f"JavaScript click failed: {e}")
                try:
                    # Method 2: Regular click
                    continue_button.click()
                    print("Clicked Continue button using regular click")
                except Exception as e2:
                    print(f"Regular click failed: {e2}")
                    # Method 3: Action chains
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(driver)
                    actions.move_to_element(continue_button).click().perform()
                    print("Clicked Continue button using ActionChains")
            
            # Wait for page to process the click
            time.sleep(3)
            
            # Verify if the click was successful by checking if we moved to the next step
            try:
                # Look for elements that would indicate we're on the credential configuration page
                wait.until(EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='clientId']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='clientSecret']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".credential-form")),
                    EC.url_contains("credential")
                ))
                print("Successfully moved to credential configuration page!")
                
                # Fill in the credential details
                if fill_gmail_oauth_details(driver):
                    return True
                else:
                    return False
                    
            except TimeoutException:
                print("Continue button clicked but may not have navigated to next step")
                return False
                
        else:
            print("Could not find Continue button")
            # Debug: Print all available buttons
            buttons = driver.find_elements(By.TAG_NAME, "button")
            print(f"Available buttons: {[btn.text.strip() for btn in buttons if btn.text.strip()]}")
            
            # Debug: Print button attributes
            for i, btn in enumerate(buttons):
                if btn.text.strip():
                    print(f"Button {i}: text='{btn.text.strip()}', class='{btn.get_attribute('class')}', data-test-id='{btn.get_attribute('data-test-id')}'")
            
            return False
            
    except Exception as e:
        print(f"Error creating Gmail OAuth credential: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def copy_google_auth_url(driver):
    """Helper function to handle Google Auth URL copying"""
    try:
        # Store current window handle
        main_window = driver.current_window_handle
        
        # Wait for new window to open (up to 10 seconds)
        wait_time = 0
        max_wait = 10
        while wait_time < max_wait:
            all_windows = driver.window_handles
            if len(all_windows) > 1:
                break
            time.sleep(1)
            wait_time += 1
        
        if len(all_windows) <= 1:
            print("No new window detected after waiting")
            return None
            
        # Find the new window
        new_window = None
        for window in all_windows:
            if window != main_window:
                new_window = window
                break
        
        if new_window:
            # Switch to the new window
            driver.switch_to.window(new_window)
            print("Switched to Google Auth window")
            
            # Wait for the window to fully load
            time.sleep(3)
            
            # Get the URL
            auth_url = driver.current_url
            print(f"Google Auth URL: {auth_url}")
            
            # Try to copy to clipboard
            try:
                import pyperclip
                pyperclip.copy(auth_url)
                print("✓ URL copied to clipboard!")
            except ImportError:
                print("Note: Install pyperclip to auto-copy URL to clipboard")
            except Exception as e:
                print(f"Could not copy to clipboard: {e}")
            
            # Switch back to main window
            driver.switch_to.window(main_window)
            print("Switched back to main window")
            
            return auth_url
        else:
            print("Could not find new window handle")
            return None
            
    except Exception as e:
        print(f"Error handling Google Auth URL: {e}")
        return None


def create_gmail_oauth_credential(driver):
    """Create Gmail OAuth2 API credential"""
    try:
        wait = WebDriverWait(driver, 15)
        
        # Look for the select dropdown element
        print("Looking for credential type select dropdown...")
        
        # Based on the HTML structure, find the select dropdown
        select_selectors = [
            "[data-test-id='new-credential-type-select']",
            ".n8n-select",
            ".el-select",
            ".select-trigger",
            "input[placeholder='Search for app...']"
        ]
        
        select_element = None
        for selector in select_selectors:
            try:
                select_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"Found select element with selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not select_element:
            print("Could not find select dropdown element")
            return False
        
        # Click on the select dropdown to open it
        print("Clicking on select dropdown...")
        driver.execute_script("arguments[0].click();", select_element)
        
        # Wait for dropdown to open
        time.sleep(2)
        
        # Now look for the search input that becomes active when dropdown is open
        try:
            search_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Search for app...']")))
            print("Found search input in opened dropdown")
            
            # Clear and enter the search term
            search_input.clear()
            search_input.send_keys("Gmail OAuth2 API")
            print("Entered 'Gmail OAuth2 API' in search field")
            
            # Step 1: Press Enter after typing
            from selenium.webdriver.common.keys import Keys
            search_input.send_keys(Keys.ENTER)
            print("Pressed Enter after typing Gmail OAuth2 API")
            
            # Wait 5 seconds
            print("Waiting 5 seconds...")
            time.sleep(5)
            
            # Step 2: Press Tab to navigate to the option
            search_input.send_keys(Keys.TAB)
            print("Pressed Tab to navigate to option")
            
            # Wait 5 seconds
            print("Waiting 5 seconds...")
            time.sleep(5)
            
            # Step 3: Press Enter to select the option
            # Get the currently focused element and press Enter
            active_element = driver.switch_to.active_element
            active_element.send_keys(Keys.ENTER)
            print("Pressed Enter to select the option")
            
            # Wait 5 seconds for the credential modal to open
            print("Waiting 5 seconds for credential modal to open...")
            time.sleep(5)
            
        except TimeoutException:
            print("Could not find search input after opening dropdown")
            return False
        
        # After selecting Gmail OAuth2 API, the credential input modal should open directly
        # No "Continue" button - it goes straight to the credential form
        print("Gmail OAuth2 API selected, credential modal should be open now")
        
        # Check if we're now on the credential configuration page/modal
        try:
            # Look for elements that indicate we're in the credential input modal
            credential_indicators = [
                (By.CSS_SELECTOR, "input[data-test-id='parameter-input-field']"),
                (By.CSS_SELECTOR, "input[type='text'][data-test-id='parameter-input-field']"),
                (By.CSS_SELECTOR, "input[type='password'][data-test-id='parameter-input-field']"),
                (By.CSS_SELECTOR, "button[data-test-id='None']"),  # The Save button you showed
                (By.XPATH, "//button[contains(text(), 'Save')]")
            ]
            
            credential_form_found = False
            for indicator in credential_indicators:
                try:
                    wait_short = WebDriverWait(driver, 3)
                    wait_short.until(EC.presence_of_element_located(indicator))
                    print(f"Found credential form indicator: {indicator}")
                    credential_form_found = True
                    break
                except TimeoutException:
                    continue
            
            if credential_form_found:
                print("Successfully opened credential input modal!")
                
                # Fill in the credential details
                if fill_gmail_oauth_details(driver):
                    return True
                else:
                    return False
            else:
                print("Could not detect credential input modal")
                # Debug: Print current page elements
                print("Current page buttons:")
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for i, btn in enumerate(buttons):
                    if btn.text.strip():
                        print(f"  Button {i}: '{btn.text.strip()}' - class: '{btn.get_attribute('class')}' - data-test-id: '{btn.get_attribute('data-test-id')}'")
                
                print("Current page inputs:")
                inputs = driver.find_elements(By.TAG_NAME, "input")
                for i, inp in enumerate(inputs):
                    print(f"  Input {i}: type='{inp.get_attribute('type')}' - class: '{inp.get_attribute('class')}' - data-test-id: '{inp.get_attribute('data-test-id')}' - placeholder: '{inp.get_attribute('placeholder')}'")
                
                return False
                
        except Exception as e:
            print(f"Error checking for credential form: {e}")
            return False
            
    except Exception as e:
        print(f"Error creating Gmail OAuth credential: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def fill_gmail_oauth_details(driver):
    """Fill in the Gmail OAuth2 API credential details"""
    try:
        from selenium.webdriver.common.keys import Keys
        wait = WebDriverWait(driver, 15)
        
        # Credentials to fill
        client_id = "1027567267122-4tkgcc56vpmm9a1snvahlht36f60sa29.apps.googleusercontent.com"
        client_secret = "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"
        
        print("Filling Gmail OAuth2 credential details...")
        
        # Wait for the credential form to load
        time.sleep(3)
        
        # Method 1: Try to find inputs by data-test-id (most reliable)
        try:
            print("Method 1: Looking for inputs by data-test-id...")
            
            # Find all parameter input fields
            input_fields = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "input[data-test-id='parameter-input-field']")
            ))
            
            print(f"Found {len(input_fields)} parameter input fields")
            
            if len(input_fields) >= 2:
                # First field should be Client ID (text input)
                client_id_field = input_fields[0]
                if client_id_field.get_attribute('type') == 'text':
                    print("Found Client ID field (first text input)")
                    driver.execute_script("arguments[0].scrollIntoView(true);", client_id_field)
                    time.sleep(1)
                    client_id_field.clear()
                    client_id_field.send_keys(client_id)
                    print("Client ID entered successfully")
                
                # Second field should be Client Secret (password input)
                client_secret_field = input_fields[1]
                if client_secret_field.get_attribute('type') == 'password':
                    print("Found Client Secret field (password input)")
                    driver.execute_script("arguments[0].scrollIntoView(true);", client_secret_field)
                    time.sleep(1)
                    client_secret_field.clear()
                    client_secret_field.send_keys(client_secret)
                    print("Client Secret entered successfully")
                
        except TimeoutException:
            print("Method 1 failed, trying Method 2...")
            
            # Method 2: Try specific selectors based on the HTML you provided
            try:
                print("Method 2: Looking for specific input elements...")
                
                # Look for the text input (Client ID)
                client_id_field = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input[type='text'][data-test-id='parameter-input-field']")
                ))
                print("Found Client ID field")
                driver.execute_script("arguments[0].scrollIntoView(true);", client_id_field)
                time.sleep(1)
                client_id_field.clear()
                client_id_field.send_keys(client_id)
                print("Client ID entered successfully")
                
                # Look for the password input (Client Secret)
                client_secret_field = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input[type='password'][data-test-id='parameter-input-field']")
                ))
                print("Found Client Secret field")
                driver.execute_script("arguments[0].scrollIntoView(true);", client_secret_field)
                time.sleep(1)
                client_secret_field.clear()
                client_secret_field.send_keys(client_secret)
                print("Client Secret entered successfully")
                
            except TimeoutException:
                print("Method 2 failed, trying Method 3...")
                
                # Method 3: Tab navigation as fallback
                print("Method 3: Using Tab navigation...")
                
                # Click somewhere on the page to start tabbing
                body = driver.find_element(By.TAG_NAME, "body")
                body.click()
                
                # Tab to find the input fields
                active_element = driver.switch_to.active_element
                
                # Tab through elements to find the first input
                for i in range(15):  # Try up to 15 tabs
                    active_element.send_keys(Keys.TAB)
                    active_element = driver.switch_to.active_element
                    
                    if (active_element.tag_name == 'input' and 
                        active_element.get_attribute('data-test-id') == 'parameter-input-field' and
                        active_element.get_attribute('type') == 'text'):
                        print(f"Found Client ID field after {i+1} tabs")
                        active_element.clear()
                        active_element.send_keys(client_id)
                        print("Client ID entered successfully")
                        break
                
                # Tab once more to get to Client Secret field
                active_element.send_keys(Keys.TAB)
                active_element = driver.switch_to.active_element
                
                if (active_element.tag_name == 'input' and 
                    active_element.get_attribute('data-test-id') == 'parameter-input-field' and
                    active_element.get_attribute('type') == 'password'):
                    print("Found Client Secret field")
                    active_element.clear()
                    active_element.send_keys(client_secret)
                    print("Client Secret entered successfully")
        
        # Wait for fields to be processed and Google Auth button to appear
        print("Waiting for Google Auth button to appear...")
        time.sleep(5)  # Increased wait time
        
        # First, let's debug what's on the page
        print("Debugging: Current page elements...")
        try:
            # Print all buttons for debugging
            all_buttons = driver.find_elements(By.TAG_NAME, "button")
            print(f"Total buttons found: {len(all_buttons)}")
            for i, btn in enumerate(all_buttons):
                btn_text = btn.text.strip() if btn.text else ""
                btn_title = btn.get_attribute('title') if btn.get_attribute('title') else ""
                btn_class = btn.get_attribute('class') if btn.get_attribute('class') else ""
                btn_style = btn.get_attribute('style') if btn.get_attribute('style') else ""
                print(f"  Button {i}: text='{btn_text}' title='{btn_title}' class='{btn_class[:50]}...' style='{btn_style[:50]}...'")
        except Exception as debug_e:
            print(f"Debug error: {debug_e}")
        
        # UPDATED: Look for the "Sign in with Google" button with more comprehensive selectors
        print("Looking for 'Sign in with Google' button...")
        
        google_auth_selectors = [
            "._googleAuthBtn_1tor9_123",  # Exact class from your HTML
            "button[class*='_googleAuthBtn_']",  # Partial class match
            "button[title='Sign in with Google']",
            "button[class*='googleAuthBtn']",
            "button[style*='google-auth']",  # Based on the style attribute you showed
            "button[style*='google-auth-btn']",
            "//button[@title='Sign in with Google']",
            "//button[contains(@class, 'googleAuthBtn')]",
            "//button[contains(@class, '_googleAuthBtn_')]",
            "//button[contains(@style, 'google-auth')]"
        ]
        
        google_auth_button = None
        for i, selector in enumerate(google_auth_selectors):
            try:
                print(f"Trying selector {i+1}: {selector}")
                if selector.startswith("//"):
                    google_auth_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, selector)))
                else:
                    google_auth_button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"✓ Found Google Auth button with selector: {selector}")
                break
            except TimeoutException:
                print(f"✗ Selector failed: {selector}")
                continue
        
        # If standard selectors fail, try a more aggressive approach
        if not google_auth_button:
            print("Standard selectors failed, trying alternative approaches...")
            
            # Method 1: Look for any button with Google-related attributes
            try:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in all_buttons:
                    btn_title = btn.get_attribute('title') or ""
                    btn_class = btn.get_attribute('class') or ""
                    btn_style = btn.get_attribute('style') or ""
                    
                    if any(keyword in btn_title.lower() for keyword in ['google', 'sign in']) or \
                       any(keyword in btn_class.lower() for keyword in ['google', 'auth']) or \
                       any(keyword in btn_style.lower() for keyword in ['google-auth']):
                        google_auth_button = btn
                        print("Found Google Auth button using attribute search")
                        break
            except Exception as e:
                print(f"Alternative method 1 failed: {e}")
            
            # Method 2: If still not found, try looking for the button by its background image style
            if not google_auth_button:
                try:
                    # The button has specific Google auth background images
                    google_auth_button = driver.find_element(By.CSS_SELECTOR, "button[style*='google-auth-btn-normal']")
                    print("Found Google Auth button using background image style")
                except NoSuchElementException:
                    print("Could not find button using background image style")
            
            # Method 3: Tab through elements to find the button
            if not google_auth_button:
                print("Trying tab navigation to find Google Auth button...")
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                    body.click()
                    
                    for i in range(20):  # Try up to 20 tabs
                        active_element = driver.switch_to.active_element
                        active_element.send_keys(Keys.TAB)
                        active_element = driver.switch_to.active_element
                        
                        if active_element.tag_name == 'button':
                            btn_title = active_element.get_attribute('title') or ""
                            btn_class = active_element.get_attribute('class') or ""
                            
                            if 'google' in btn_title.lower() or 'google' in btn_class.lower():
                                google_auth_button = active_element
                                print(f"Found Google Auth button using tab navigation after {i+1} tabs")
                                break
                except Exception as e:
                    print(f"Tab navigation failed: {e}")
        
        if google_auth_button:
            print("Clicking 'Sign in with Google' button...")
            
            # Scroll to the button and ensure it's visible
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", google_auth_button)
            time.sleep(2)
            
            # Wait for any animations to complete
            time.sleep(1)
            
            # Try multiple click methods
            click_successful = False
            
            try:
                # Method 1: JavaScript click
                driver.execute_script("arguments[0].click();", google_auth_button)
                print("✓ Google Auth button clicked using JavaScript")
                click_successful = True
            except Exception as e:
                print(f"JavaScript click failed: {e}")
                
                try:
                    # Method 2: Regular click
                    google_auth_button.click()
                    print("✓ Google Auth button clicked using regular click")
                    click_successful = True
                except Exception as e2:
                    print(f"Regular click failed: {e2}")
                    
                    try:
                        # Method 3: Action chains
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_to_element(google_auth_button).click().perform()
                        print("✓ Google Auth button clicked using ActionChains")
                        click_successful = True
                    except Exception as e3:
                        print(f"ActionChains click failed: {e3}")
            
            if click_successful:
                # Wait and try to get auth URL
                time.sleep(3)
                auth_url = copy_google_auth_url(driver)
                if auth_url:
                    print("✓ Google Auth URL obtained successfully")
                    AuthStorage.google_auth_url = auth_url
                    return True
                else:
                    print("Button clicked, check for popup windows manually")
                    return True
        else:
            print("Could not find 'Sign in with Google' button")
            # Still try the Tab+Enter approach as fallback
            print("Trying Tab+Enter approach as fallback...")
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.click()
                active_element = driver.switch_to.active_element
                active_element.send_keys(Keys.TAB)
                time.sleep(1)
                active_element = driver.switch_to.active_element
                active_element.send_keys(Keys.ENTER)
                print("Pressed Tab+Enter as fallback")
                
                # Wait and try to get auth URL
                time.sleep(3)
                auth_url = copy_google_auth_url(driver)
                if auth_url:
                    print("✓ Google Auth URL obtained using Tab+Enter fallback")
                    AuthStorage.google_auth_url = auth_url
                    return True
                else:
                    print("Tab+Enter pressed, check for popup windows manually")
                    return True
            except Exception as e:
                print(f"Tab+Enter fallback failed: {e}")
            
            return False
        
    except Exception as e:
        print(f"Error filling Gmail OAuth details: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@app.get("/", response_model=OAuthResponse)
async def root():
    """Main automation function"""
    driver = None
    try:
        # Setup driver
        driver = setup_driver()
        print("Chrome driver initialized successfully")
        
        # Login to N8N
        if not login_to_n8n(driver):
            print("Login failed, exiting...")
            return OAuthResponse(success=False, message="Login to N8N failed")

        # Navigate to credentials page
        if not navigate_to_credentials_page(driver):
            print("Navigation to credentials page failed, exiting...")
            return OAuthResponse(success=False, message="Navigation failed")
        
        # Create Gmail OAuth2 credential
        if create_gmail_oauth_credential(driver):
            print("Gmail OAuth2 API credential creation process completed successfully!")
        else:
            print("Gmail OAuth2 API credential creation process failed")
            return OAuthResponse(success=False, message="Credential creation failed")
        
        # Keep browser open for a few seconds to see the result
        print("Keeping browser open for 5 seconds...")
        time.sleep(5)

        if AuthStorage.google_auth_url:
            return OAuthResponse(
                success=True,
                google_auth_url=AuthStorage.google_auth_url,
                message="OAuth URL retrieved successfully"
            )
        
        else:
            return OAuthResponse(success=False, message="OAuth URL not found")

    except Exception as e:
        return OAuthResponse(success=False, message="Unexpected error", error=str(e))
        
    finally:
        if driver:
            print("Closing browser...")
            driver.quit()


# Thread pool for running automation asynchronously
executor = ThreadPoolExecutor(max_workers=1)

@app.post("/run-automation", response_model=AutomationResponse)
async def run_automation_endpoint(request: AutomationRequest):
    """Run the N8N automation"""
    try:
        # Run automation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, run_automation)
        
        return AutomationResponse(
            success=result["success"],
            message=result["message"],
            details=result
        )
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


