from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchWindowException, NoSuchElementException, InvalidArgumentException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from utils.database import Database
from time import sleep
import time
import math
import datetime
import argparse
import keyboard
from utils.db_to_excel import Converter

'''
░█──░█ █──█ █▀▀█ ▀▀█▀▀ █▀▀ █▀▀█ █▀▀█ █▀▀█ 　 ░█▀▀▀█ ░█▀▀▀█ ▀█▀ ░█▄─░█ ▀▀█▀▀ 
░█░█░█ █▀▀█ █▄▄█ ──█── ▀▀█ █▄▄█ █──█ █──█ 　 ░█──░█ ─▀▀▀▄▄ ░█─ ░█░█░█ ─░█── 
░█▄▀▄█ ▀──▀ ▀──▀ ──▀── ▀▀▀ ▀──▀ █▀▀▀ █▀▀▀ 　 ░█▄▄▄█ ░█▄▄▄█ ▄█▄ ░█──▀█ ─░█── 
░█▀▀█ ░█──░█ 　 ───░█ ─█▀▀█ ░█▀▀▀█ ░█▀▀█ ░█▀▀▀ ░█▀▀█ ─█▀▀█ ░█▄─░█ 
░█▀▀▄ ░█▄▄▄█ 　 ─▄─░█ ░█▄▄█ ─▀▀▀▄▄ ░█▄▄█ ░█▀▀▀ ░█▄▄▀ ░█▄▄█ ░█░█░█ 
░█▄▄█ ──░█── 　 ░█▄▄█ ░█─░█ ░█▄▄▄█ ░█─── ░█▄▄▄ ░█─░█ ░█─░█ ░█──▀█
'''

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

def find_user_chat(driver, user):
    """Search and goes to the user's chat"""
    try:
        # Search for the chat box
        search_box = driver.find_element(by=By.XPATH, value='//*[@id="side"]/div[1]/div/div[2]/div/div/div[1]/p')
        search_box.click()
        
        # Type the username into the search box
        actions = ActionChains(driver)
        actions.send_keys(user).perform()

        print(f'Trying to find: {user}')
        # Finds the first user in the search results
        user_element = driver.find_element(by=By.XPATH, value='//*[@id="pane-side"]/div[1]/div/div/div[2]/div/div')
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div[1]/div/div/div[2]/div/div'))
        )
        user_element.click()
        print('Found and clicked!')
        return True
    except NoSuchElementException:
        print(f'{user} is not found. Returning...(Maybe your contact is in the archive or not in your chat list. Check it)')
        return False
    except Exception as e:
        print(f"Error finding user {user}: {e}")
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
    print(f"Tracking {user}...")

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
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="side"]/div[1]/div/div[2]/div/div/div[1]/p'))
        )
        print("\nLoaded")
    except Exception as e:
        print(f"Error loading WhatsApp Web: {e}")
        print("Press F1 if stuck...")
        if keyboard.is_pressed('F1'):
            return

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

    #WebDriverWait(driver, 100).until(
         #   EC.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/div[3]/div/div[3]'))
        #)