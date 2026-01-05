import time
import math
import datetime
import logging
from pathlib import Path
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchWindowException, NoSuchElementException, InvalidArgumentException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

from .database import Database
from .db_to_excel import Converter
from .config import Config

logger = logging.getLogger(__name__)

# Dictionary for different languages
ONLINE_STATUS = {
    'en': 'online',
    'de': 'online',
    'pt': 'online',
    'es': 'en línea',
    'fr': 'en ligne',
    'it': 'in linea',
    'cat': 'en línia',
    'tr': 'çevrimiçi'
}

class WhatsAppBeacon:
    def __init__(self, config: Config):
        self.config = config
        self.db_path = Path(self.config.data_dir) / 'victims_logs.db'
        self.database = Database(db_path=str(self.db_path))
        self.driver = None

    def get_current_time_parts(self):
        """Retrieves formatted time"""
        now = datetime.datetime.now()
        return {
            'date': now.strftime('%Y-%m-%d'),
            'hour': now.strftime('%H'),
            'minute': now.strftime('%M'),
            'second': now.strftime('%S'),
            'formatted': now.strftime('%Y-%m-%d %H:%M:%S')
        }

    def check_online_status(self, xpath):
        """Verifies if the user is online"""
        try:
            self.driver.find_element(by=By.XPATH, value=xpath)
            return True
        except NoSuchElementException:
            return False

    def find_user_chat(self, user):
        """Search and goes to the user's chat"""
        try:
            # Search for the chat box
            search_box_xpath = '//*[@id="side"]/div[1]/div/div[2]/div/div/div[1]/p'
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, search_box_xpath))
            )
            search_box = self.driver.find_element(by=By.XPATH, value=search_box_xpath)
            search_box.click()

            # Type the username into the search box
            # Clear it first just in case
            search_box.clear()
            actions = ActionChains(self.driver)
            actions.send_keys(user).perform()

            logger.info(f'Trying to find: {user}')

            # Finds the first user in the search results
            result_xpath = '//*[@id="pane-side"]/div[1]/div/div/div[2]/div/div'
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, result_xpath))
            )
            user_element = self.driver.find_element(by=By.XPATH, value=result_xpath)
            user_element.click()
            logger.info('Found and clicked!')
            return True
        except Exception as e:
            logger.warning(f"{user} is not found. Error: {e}. (Maybe your contact is in the archive or not in your chat list.)")
            return False

    def setup_driver(self):
        """Sets up the Selenium driver."""
        logger.info("Setting up WebDriver...")
        options = webdriver.ChromeOptions()

        # Cross-platform user data directory
        user_data_dir = Path(self.config.data_dir) / "chrome_profile"
        options.add_argument(f"user-data-dir={user_data_dir.absolute()}")

        if self.config.headless:
            logger.info("Running in Headless mode.")
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        try:
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.critical(f"Failed to initialize Chrome Driver: {e}")
            sys.exit(1)

    def whatsapp_login(self):
        """Logs into Whatsapp Web."""
        try:
            logger.info('Opening WhatsApp Web...')
            self.driver.get('https://web.whatsapp.com')

            # Wait for load
            logger.info("Waiting for WhatsApp to load...")

            if self.config.headless:
                # In headless, we might need to take a screenshot if not logged in
                time.sleep(5) # Give it a moment to render QR or Main page
                try:
                    # Check if logged in (search box exists)
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="side"]/div[1]/div/div[2]/div/div/div[1]/p'))
                    )
                    logger.info("Logged in successfully (Headless).")
                except:
                    logger.warning("Not logged in. Taking screenshot of QR code...")
                    screenshot_path = Path("qrcode.png")
                    self.driver.save_screenshot(str(screenshot_path))
                    logger.warning(f"Screenshot saved to {screenshot_path.absolute()}. Please scan it or run in non-headless mode first to authenticate.")
                    # Wait for a while to allow scanning if the user opens the image
                    # But usually, they should run non-headless first.

                    # Try to wait for login for 60 seconds
                    try:
                        WebDriverWait(self.driver, 60).until(
                             EC.presence_of_element_located((By.XPATH, '//*[@id="side"]/div[1]/div/div[2]/div/div/div[1]/p'))
                        )
                        logger.info("Logged in successfully.")
                    except:
                        logger.error("Login timeout. Please run without headless mode to authenticate first.")
                        sys.exit(1)
            else:
                 WebDriverWait(self.driver, 120).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="side"]/div[1]/div/div[2]/div/div/div[1]/p'))
                )

            logger.info("WhatsApp Web Loaded")

        except InvalidArgumentException:
            logger.error('ERROR: You may already have a Selenium navigator running in the background. Close it and try again.')
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading WhatsApp Web: {e}")
            if not self.config.headless:
                logger.info("Press Ctrl+C to exit if stuck.")

    def run(self):
        """Main execution loop."""
        if self.config.excel:
            excel_converter = Converter(db_path=str(self.db_path))
            excel_converter.db_to_excel()

        language = self.config.language
        if language not in ONLINE_STATUS:
            logger.error(f"Error: Language '{language}' not supported. Supported languages: {list(ONLINE_STATUS.keys())}")
            return

        self.setup_driver()
        self.whatsapp_login()

        user = self.config.username
        if not self.find_user_chat(user):
            self.driver.quit()
            return

        user_id = self.database.get_or_create_user(user)
        xpath = f"//span[@title='{ONLINE_STATUS[language]}']"
        logger.info(f"Tracking {user}...")

        previous_state = 'OFFLINE'
        first_online = 0
        cumulative_session_time = 0
        current_session_id = None

        try:
            while True:
                is_online = self.check_online_status(xpath)
                time_parts = self.get_current_time_parts()

                if is_online and previous_state == 'OFFLINE':
                    logger.info(f"[ONLINE] {user}")
                    current_session_id = self.database.insert_session_start(user_id, time_parts)
                    first_online = time.time()
                    previous_state = 'ONLINE'

                elif not is_online and previous_state == 'ONLINE':
                    total_online_time = time.time() - first_online
                    if total_online_time >= 0 and current_session_id:
                        cumulative_session_time += total_online_time
                        logger.info(f"[DISCONNECTED] {user} was online for {math.floor(total_online_time)} seconds. Session total: {math.floor(cumulative_session_time)} seconds")
                        self.database.update_session_end(current_session_id, time_parts, str(round(total_online_time)))
                        previous_state = 'OFFLINE'
                        current_session_id = None

                # Small sleep to reduce CPU usage
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\nStopping tracker...")
        except NoSuchWindowException:
            logger.error('ERROR: Your WhatsApp window has been minimized or closed.')
        finally:
            if self.driver:
                self.driver.quit()
            logger.info("Exited.")
