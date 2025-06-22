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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="N8N Automation API", version="1.0.0")

# Pydantic models for request/response
class AutomationRequest(BaseModel):
    action: str = "login_and_navigate"

class AutomationResponse(BaseModel):
    success: bool
    message: str
    details: dict = {}

def setup_chrome_driver():
    """Setup Chrome driver with appropriate options"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        # Remove headless mode for debugging - add back if needed
        # chrome_options.add_argument("--headless")
        
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        logger.error(f"Error setting up Chrome driver: {str(e)}")
        return None

def login_to_n8n(driver):
    """Login to N8N platform"""
    try:
        # Navigate to the login page
        print("Navigating to N8N login page...")
        driver.get("https://n8n.realtyamp.ai/")
        
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
        traceback.print_exc()
        return False

def navigate_to_credentials_page(driver):
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

def handle_modal_and_extract_value(driver):
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
        driver = setup_chrome_driver()
        if not driver:
            return {"success": False, "message": "Failed to setup Chrome driver"}
        
        # Login to N8N
        if not login_to_n8n(driver):
            return {"success": False, "message": "Failed to login to N8N"}
        
        # Navigate to credentials page and click first card
        if not navigate_to_credentials_page(driver):
            return {"success": False, "message": "Failed to navigate to credentials page or click first card"}
        
        # Handle modal and extract value
        extracted_value = handle_modal_and_extract_value(driver)
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "N8N Automation API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "n8n-automation"}

# Direct execution for testing
if __name__ == "__main__":
    print("Running automation directly...")
    result = run_automation()
    print(f"Final result: {result}")