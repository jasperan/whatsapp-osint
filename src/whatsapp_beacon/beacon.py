import time
import math
import datetime
import logging
from pathlib import Path
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchWindowException,
    NoSuchElementException,
    InvalidArgumentException,
    TimeoutException,
    WebDriverException,
)
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

# XPath candidates for detecting a successful WhatsApp Web login.
# Tried in order; the first match wins. Update here when WhatsApp changes their DOM.
_LOGIN_READY_XPATHS = [
    '//div[@data-testid="chat-list"]',
    '//div[@aria-label="Chat list"]',
    '//*[@id="side"]',
    '//div[@role="textbox"][@data-tab="3"]',
    '//div[@contenteditable="true"][@data-tab="3"]',
    '//input[@role="searchbox"]',
]

# XPath candidates for the search input box.
# WhatsApp Web uses either a Lexical rich-text editor (div[role="textbox"])
# or a native <input role="searchbox"> depending on the build.
_SEARCH_BOX_XPATHS = [
    # Lexical editor: role="textbox" with contenteditable, data-tab may be on same or parent element
    '//div[@role="textbox"][@data-tab="3"]',
    '//div[@contenteditable="true"][@data-tab="3"]',
    '//div[@data-tab="3"]//div[@role="textbox"]',
    '//div[@data-tab="3"]//div[@contenteditable="true"]',
    # Native input variant (newer WhatsApp builds)
    '//input[@role="searchbox"]',
    '//div[@data-tab="5"]//input[@type="text"]',
    # Broad fallbacks scoped to the side panel
    '//*[@id="side"]//div[@role="textbox"][@contenteditable="true"]',
    '//*[@id="side"]//input[@type="text"]',
]

# XPath candidates for the first result in the search pane.
_SEARCH_RESULT_XPATHS = [
    '//div[@data-testid="cell-frame-container"]',
    '//div[@role="listitem"]',
    '//*[@id="pane-side"]//div[@data-testid="cell-frame-container"]',
    '//*[@id="pane-side"]/div[1]/div/div/div[1]/div/div',
    '//*[@id="pane-side"]/div[1]/div/div/div[2]/div/div',
]


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

    def _find_first_present(self, xpaths, timeout=20):
        """
        Poll the page until one of the given XPaths is present.
        Returns the matching XPath string, or None if the timeout expires.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            for xpath in xpaths:
                try:
                    if self.driver.find_element(By.XPATH, xpath):
                        return xpath
                except (NoSuchElementException, WebDriverException):
                    pass
            time.sleep(0.5)
        return None

    def find_user_chat(self, user):
        """Search and goes to the user's chat"""
        try:
            search_xpath = self._find_first_present(_SEARCH_BOX_XPATHS, timeout=20)
            if not search_xpath:
                logger.warning(
                    "Could not locate the WhatsApp search box. "
                    "The DOM may have changed — check _SEARCH_BOX_XPATHS in beacon.py."
                )
                return False

            search_box = self.driver.find_element(By.XPATH, search_xpath)
            search_box.click()
            time.sleep(0.5)

            is_native_input = search_box.tag_name == 'input'
            if is_native_input:
                # Native <input> element: use clear() + send_keys()
                search_box.clear()
                search_box.send_keys(user)
            else:
                # Contenteditable div (Lexical editor): select-all, delete, type
                search_box.send_keys(Keys.CONTROL + 'a')
                search_box.send_keys(Keys.DELETE)
                time.sleep(0.2)
                ActionChains(self.driver).send_keys(user).perform()

            logger.info(f'Trying to find: {user}')
            time.sleep(1)  # allow search results to populate

            result_xpath = self._find_first_present(_SEARCH_RESULT_XPATHS, timeout=30)
            if not result_xpath:
                logger.warning(f"No search results appeared for '{user}'.")
                return False

            user_element = self.driver.find_element(By.XPATH, result_xpath)
            user_element.click()
            logger.info('Found and clicked!')
            return True
        except Exception as e:
            logger.warning(
                f"{user} is not found. Error: {e}. "
                "(Maybe your contact is in the archive or not in your chat list.)"
            )
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
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )

        # Stability flags (important on Linux/Docker and some Windows configs)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # Remove Selenium fingerprints that WhatsApp (and other sites) detect.
        # Without these, WhatsApp Web detects automation and closes the connection.
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            # Patch navigator.webdriver on every new document so it reads as undefined.
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
            )
        except Exception as e:
            logger.critical(f"Failed to initialize Chrome Driver: {e}")
            sys.exit(1)

    def whatsapp_login(self):
        """Logs into WhatsApp Web. Raises WebDriverException / TimeoutException on failure."""
        try:
            logger.info('Opening WhatsApp Web...')
            self.driver.get('https://web.whatsapp.com')
            logger.info("Waiting for WhatsApp to load...")

            if self.config.headless:
                time.sleep(5)  # let the page render before probing
                matched = self._find_first_present(_LOGIN_READY_XPATHS, timeout=15)
                if not matched:
                    logger.warning("Not logged in. Saving QR code screenshot to qrcode.png ...")
                    self.driver.save_screenshot("qrcode.png")
                    logger.warning(
                        "Scan qrcode.png with your phone, or run once without --headless to authenticate."
                    )
                    matched = self._find_first_present(_LOGIN_READY_XPATHS, timeout=60)
                    if not matched:
                        raise TimeoutException("Login timed out in headless mode.")
            else:
                matched = self._find_first_present(_LOGIN_READY_XPATHS, timeout=120)
                if not matched:
                    raise TimeoutException(
                        "WhatsApp Web did not finish loading within 120 seconds. "
                        "Check your internet connection or scan the QR code."
                    )

            logger.info("WhatsApp Web Loaded")

        except InvalidArgumentException:
            logger.error(
                "ERROR: A Selenium browser may already be running with the same profile. "
                "Close it and try again."
            )
            sys.exit(1)
        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Error loading WhatsApp Web: {e}")
            raise  # propagate so run() can clean up instead of stumbling forward

    def run(self):
        """Main execution loop."""
        if self.config.excel:
            excel_converter = Converter(db_path=str(self.db_path))
            excel_converter.db_to_excel()

        language = self.config.language
        if language not in ONLINE_STATUS:
            logger.error(
                f"Error: Language '{language}' not supported. "
                f"Supported languages: {list(ONLINE_STATUS.keys())}"
            )
            return

        self.setup_driver()

        try:
            self.whatsapp_login()
        except Exception:
            # whatsapp_login already logged the error
            if self.driver:
                self.driver.quit()
            return

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
                        logger.info(
                            f"[DISCONNECTED] {user} was online for {math.floor(total_online_time)} seconds. "
                            f"Session total: {math.floor(cumulative_session_time)} seconds"
                        )
                        self.database.update_session_end(
                            current_session_id, time_parts, str(round(total_online_time))
                        )
                        previous_state = 'OFFLINE'
                        current_session_id = None

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\nStopping tracker...")
        except NoSuchWindowException:
            logger.error('ERROR: Your WhatsApp window has been minimized or closed.')
        finally:
            if self.driver:
                self.driver.quit()
            logger.info("Exited.")
