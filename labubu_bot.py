from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
import os
import time
import random
import platform
import requests
import logging
import json
import tempfile
import shutil

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    filename="labubu_bot.log",
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)

# Discord webhook for notifications
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# List of modern user agents
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
]

# List of product URLs to monitor
PRODUCTS = [
    "https://www.popmart.com/us/products/2155/THE-MONSTERS-Big-into-Energy-Series-Vinyl-Plush-Pendant-Blind-Box",
    "https://www.popmart.com/us/products/1372/THE-MONSTERS---Have-a-Seat-Vinyl-Plush-Blind-Box"
]

def get_random_user_agent():
    """Get a random user agent from the list of modern browsers."""
    return random.choice(USER_AGENTS)

def human_like_delay():
    """Add a random delay to simulate human behavior."""
    time.sleep(random.uniform(0.5, 1.5))

def get_chrome_profile_dir():
    """Return the default Chrome profile path for the current OS."""
    home = os.path.expanduser("~")
    system = platform.system()

    if system == "Darwin":
        return os.path.join(home, "Library/Application Support/Google/Chrome/Default")
    if system == "Windows":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return os.path.join(local_app_data, "Google", "Chrome", "User Data", "Default")
    return os.path.join(home, ".config", "google-chrome", "Default")

def play_sound_alert():
    """Play a sound alert when an item is added to cart."""
    try:
        if platform.system() == "Darwin":  # macOS
            os.system('afplay /System/Library/Sounds/Glass.aiff')
        elif platform.system() == "Windows":
            import winsound
            winsound.Beep(1000, 1000)
        else:  # Linux
            os.system('paplay /usr/share/sounds/freedesktop/stereo/complete.oga')
    except Exception as e:
        print(f"⚠️ Could not play sound alert: {str(e)}")

def send_discord_alert(message):
    """Send a notification to Discord webhook."""
    if not DISCORD_WEBHOOK:
        logging.warning("No Discord webhook configured")
        return
        
    data = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK, json=data)
        if response.status_code == 204:
            logging.info("Sent Discord alert: " + message)
            play_sound_alert()
        else:
            print(f"[⚠️] Discord alert failed with status {response.status_code}")
    except Exception as e:
        print(f"[❌] Error sending Discord alert: {e}")

def get_driver():
    """Setup and return a Chrome webdriver instance with anti-detection measures."""
    print("🔧 Setting up Chrome driver...")
    
    try:
        # Initialize Chrome options
        chrome_options = Options()
        
        # Get the user's Chrome profile directory
        chrome_profile = get_chrome_profile_dir()
        
        # Create a temporary directory for the profile copy
        temp_dir = tempfile.mkdtemp()
        print(f"📁 Creating temporary profile directory: {temp_dir}")
        
        # Copy the Chrome profile to the temporary directory
        try:
            shutil.copytree(chrome_profile, os.path.join(temp_dir, "Default"))
            print("✅ Successfully copied Chrome profile")
        except Exception as e:
            print(f"⚠️ Could not copy Chrome profile: {str(e)}")
            print("Using fresh profile instead...")
        
        # Configure Chrome options
        chrome_options.add_argument(f"user-data-dir={temp_dir}")
        chrome_options.add_argument(f"user-agent={get_random_user_agent()}")
        
        # Additional options for stability and stealth
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Performance optimizations
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Disable images for faster loading
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--disk-cache-size=1")  # Minimize disk cache
        chrome_options.add_argument("--media-cache-size=1")  # Minimize media cache
        chrome_options.add_argument("--disable-application-cache")  # Disable app cache
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Create the driver
        print("🚀 Creating Chrome driver...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Execute CDP commands to prevent detection
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        
        print("✅ Chrome driver created successfully")
        driver.set_page_load_timeout(10)  
        driver.implicitly_wait(3) 
        
        return driver
        
    except Exception as e:
        print(f"❌ Failed to create Chrome driver: {str(e)}")
        raise

def add_to_cart(driver, url):
    """Attempt to add a product to the cart using multiple click methods."""
    print("🔄 Starting add_to_cart process...")
    try:
        print(f"📄 Current page: {driver.title}")
        print(f"🔗 Current URL: {driver.current_url}")
        
        human_like_delay()
        
        # Look for the add to bag button using the most reliable selector
        print("🔍 Looking for ADD TO BAG button...")
        try:
            add_btn = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'ADD TO BAG')]"))
            )
            print("✅ Found ADD TO BAG button")
        except:
            print("❌ Could not find ADD TO BAG button")
            return False
        
        # Scroll the button into view with a random offset
        print("📜 Scrolling to button...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", add_btn)
        human_like_delay()
        
        click_success = False
        try:
            # Try JavaScript click first
            driver.execute_script("arguments[0].click();", add_btn)
            print("✅ Clicked button with JavaScript")
            click_success = True
        except Exception as e:
            print(f"⚠️ JavaScript click failed: {str(e)}")
            try:
                # Try regular click
                add_btn.click()
                print("✅ Clicked button normally")
                click_success = True
            except Exception as e:
                print(f"⚠️ Normal click failed: {str(e)}")
                try:
                    # Try ActionChains as last resort
                    ActionChains(driver).move_to_element(add_btn).click().perform()
                    print("✅ Clicked button with ActionChains")
                    click_success = True
                except Exception as e:
                    print(f"❌ All click methods failed: {str(e)}")
                    raise
        
        if click_success:
            print("✅ Successfully clicked ADD TO BAG button")
            play_sound_alert()
            send_discord_alert(f"🎉 Successfully clicked ADD TO BAG for: {url}")
            return True
        else:
            print("❌ Failed to click ADD TO BAG button")
            return False
            
    except Exception as e:
        print(f"❌ Error in add_to_cart: {str(e)}")
        return False

def check_product_availability(driver, url):
    """Check if a product is available without adding to cart."""
    try:
        print(f"🔍 Checking availability for: {url}")
        driver.get(url)
        
        # Wait for the page to load with reduced timeout
        WebDriverWait(driver, 5).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        # Look for the add to bag button
        try:
            add_btn = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.index_usBtn__2KlEx.index_red__kx6Ql.index_btnFull__F7k90"))
            )
            print(f"✅ Product is available: {url}")
            return True
        except:
            try:
                add_btn = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'ADD TO BAG')]"))
                )
                print(f"✅ Product is available: {url}")
                return True
            except:
                print(f"❌ Product is not available: {url}")
                return False
    except Exception as e:
        print(f"❌ Error checking availability: {str(e)}")
        return False

def run_bot_cycle():
    """Run one cycle of the bot, checking all products for availability."""
    driver = None
    try:
        print("\n🌐 Starting product checks...")
        
        try:
            driver = get_driver()
            print("✅ Created main browser window")
        except Exception as e:
            print(f"❌ Failed to create driver: {str(e)}")
            time.sleep(random.uniform(8, 12))
            return
        
        while True:  # Continuous checking loop
            # Check each product and add to cart if available
            for product_url in PRODUCTS:
                try:
                    print(f"\n🔍 Checking product: {product_url}")
                    
                    # Refresh the page
                    driver.get(product_url)
                    
                    # Wait for the page to load
                    WebDriverWait(driver, 5).until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )
                    
                    # Look for the add to bag button
                    try:
                        add_btn = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'ADD TO BAG')]"))
                        )
                        print(f"✅ Product is available: {product_url}")
                        
                        # Try to add to cart immediately
                        print(f"🛒 Attempting to add to cart: {product_url}")
                        result = add_to_cart(driver, product_url)
                        if result:
                            print(f"✅ Successfully added to cart: {product_url}")
                            # Continue to next product after a short delay
                            human_like_delay()
                            continue
                    except:
                        print(f"❌ Product is not available: {product_url}")
                        continue
                    
                    # Add small random delay between products
                    human_like_delay()
                    
                except Exception as e:
                    print(f"❌ Error checking product {product_url}: {str(e)}")
                    continue
            
            print("\n⏳ Completed checking all products, starting next cycle...")
            # Small delay between cycles
            time.sleep(random.uniform(1, 2))
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        time.sleep(random.uniform(.5, 1))

def run_bot():
    """Main function to run the bot continuously."""
    print("\n🤖 Starting bot...")
    print("🎯 Target products:")
    for i, product in enumerate(PRODUCTS, 1):
        print(f"{i}. {product}")
    print("⏰ TEST MODE: Running immediately")
    
    while True:
        run_bot_cycle()

if __name__ == "__main__":
    print("\n🚀 Starting Labubu Bot...")
    print("=" * 50)
    print("⚠️ IMPORTANT: Make sure you're logged into Pop Mart in your regular Chrome!")
    print("⏰ TEST MODE: Running immediately")
    print("=" * 50)
    
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot stopped due to error: {str(e)}")
    finally:
        print("\n✨ Bot session ended")
