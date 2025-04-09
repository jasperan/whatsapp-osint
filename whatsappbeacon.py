from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchWindowException, NoSuchElementException, InvalidArgumentException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from utils.database import Database
from time import sleep
import time
import math
import datetime
import argparse
import sqlite3
from typing import Dict, Optional
import threading
import keyboard
from utils.db_to_excel import Converter

# Dictionary for different languages
ONLINE_STATUS = {
    'en': 'online',
    'de': 'online', 
    'pt': 'online', 
    'es': 'en línea',
    'fr': 'en ligne', 
    'cat': 'en línia', 
    'tr': 'çevrimiçi'
}


def get_current_time_parts():
    """Retrieves formatted time"""
    now = datetime.datetime.now()
    return {
        'date': now.strftime('%Y-%m-%d'),
        'hour': now.strftime('%H'),
        'minute': now.strftime('%M'),
        'second': now.strftime('%S'),
        'formatted': now.strftime('%Y-%m-%d %H:%M:%S')
    }

def check_online_status(driver, xpath):
    """Verifies if the user is online"""
    try:
        driver.find_element(by=By.XPATH, value=xpath)
        return True
    except NoSuchElementException:
        return False

def remove_idle(driver):
    """Avoids session to end"""
    while True:
        sleep(10)
        try:
            driver.find_element(by=By.XPATH, value='//span[@data-testid="smiley"]').click()
        except NoSuchElementException:
            print('Error: could not find smiley element')

def find_user_chat(driver, user):
    """Search and goes to the user's chat"""
    try:
        driver.find_element(by=By.CSS_SELECTOR, value='span[data-testid="chat"]').click()
        actions = ActionChains(driver)
        actions.send_keys(user).perform()
        sleep(1)
        print(f'Trying to find: {user}')
        driver.find_element(by=By.CSS_SELECTOR, value=f"span[title='{user}']").click()
        print('Found and clicked!')
        return True
    except NoSuchElementException:
        print(f'{user} is not found. Returning...(Maybe your contact is in the archive. Check it)')
        return False

def study_user(driver, user, language, excel):
    """Tracks and stores users Whatsapp connections"""
    if excel:
        excel_converter = Converter()
        excel_converter.db_to()
        excel_converter.db_to_excel()
        print("\nYour Data Has Been Added to Excel File")

    if language not in ONLINE_STATUS:
        print(f"Error: Language '{language}' not supported. Supported languages: {list(ONLINE_STATUS.keys())}")
        return

    if not find_user_chat(driver, user):
        return

    user_id = Database.get_or_create_user(user)
    xpath = f"//span[@title='{ONLINE_STATUS[language]}']"
    idle_thread = threading.Thread(target=remove_idle, args=(driver,), daemon=True)
    idle_thread.start()

    previous_state = 'OFFLINE'
    first_online = 0
    cumulative_session_time = 0
    current_session_id = None

    while True:
        try:
            is_online = check_online_status(driver, xpath)
            time_parts = get_current_time_parts()

            if is_online and previous_state == 'OFFLINE':
                print(f"[{time_parts['formatted']}][ONLINE] {user}")
                current_session_id = Database.insert_session_start(user_id, time_parts)
                first_online = time.time()
                previous_state = 'ONLINE'

            elif not is_online and previous_state == 'ONLINE':
                total_online_time = time.time() - first_online
                if total_online_time >= 0 and current_session_id:
                    cumulative_session_time += total_online_time
                    print(f"[{time_parts['formatted']}][DISCONNECTED] {user} was online for {math.floor(total_online_time)} seconds. Session total: {math.floor(cumulative_session_time)} seconds")
                    Database.update_session_end(current_session_id, time_parts, str(round(total_online_time)))
                    previous_state = 'OFFLINE'
                    current_session_id = None

        except NoSuchWindowException:
            print('ERROR: Your WhatsApp window has been minimized or closed, try running the code again, shutting down...')
            return

def whatsapp_load(driver):
    """Waits until Whatsapp Web fully loads."""
    while True:
        try:
            driver.find_element(by=By.XPATH, value='//div[@data-testid="wa-web-loading-screen"]').click()
            print("\nLoaded")
            break
        except Exception as e:
            print(f"Loading. Press F1 if stuck in this step...: {e}", end="\r")
            if keyboard.is_pressed('F1'):
                break

def whatsapp_login():
    """Logs into Whatsapp Web and returns the driver"""
    try:
        print('In order to make this program work, you will need to log in once in WhatsApp. After that, your session will be saved until you revoke it.')
        options = webdriver.ChromeOptions()
        options.add_argument("user-data-dir=C:\\Path")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(options=options)
        driver.get('https://web.whatsapp.com')
        assert 'WhatsApp' in driver.title
        whatsapp_load(driver)
        return driver
    except InvalidArgumentException:
        print('ERROR: You may already have a Selenium navigator running in the background, close the window and run the code again, shutting down...')
        exit()

def main():
    """Main function that sets up and runs the program"""
    Database.create_tables()
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', help='Username to track', required=True)
    parser.add_argument('-l', '--language', help='Language to use', required=True)
    parser.add_argument('-e', '--excel', help="DB to Excel Converter", action='store_true')
    parser.add_argument('-s', '--split', help="Change the prefix with which the spaces of the --username flag will be separated", default="-")
    args = parser.parse_args()

    user_name = " ".join(args.username.split(args.split))
    driver = whatsapp_login()
    study_user(driver, user_name, args.language, args.excel)

if __name__ == '__main__':
    main()