from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchWindowException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import InvalidArgumentException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from utils.database import Database
from time import sleep
import os
import time
import math
import datetime
import argparse
from db_to_excel import Converter
import threading



'''
░█──░█ █──█ █▀▀█ ▀▀█▀▀ █▀▀ █▀▀█ █▀▀█ █▀▀█ 　 ░█▀▀▀█ ░█▀▀▀█ ▀█▀ ░█▄─░█ ▀▀█▀▀ 
░█░█░█ █▀▀█ █▄▄█ ──█── ▀▀█ █▄▄█ █──█ █──█ 　 ░█──░█ ─▀▀▀▄▄ ░█─ ░█░█░█ ─░█── 
░█▄▀▄█ ▀──▀ ▀──▀ ──▀── ▀▀▀ ▀──▀ █▀▀▀ █▀▀▀ 　 ░█▄▄▄█ ░█▄▄▄█ ▄█▄ ░█──▀█ ─░█── 
░█▀▀█ ░█──░█ 　 ───░█ ─█▀▀█ ░█▀▀▀█ ░█▀▀█ ░█▀▀▀ ░█▀▀█ ─█▀▀█ ░█▄─░█ 
░█▀▀▄ ░█▄▄▄█ 　 ─▄─░█ ░█▄▄█ ─▀▀▀▄▄ ░█▄▄█ ░█▀▀▀ ░█▄▄▀ ░█▄▄█ ░█░█░█ 
░█▄▄█ ──░█── 　 ░█▄▄█ ░█─░█ ░█▄▄▄█ ░█─── ░█▄▄▄ ░█─░█ ░█─░█ ░█──▀█
'''

def remove_idle(driver):
    while True:
        time.sleep(10)
        try:
            smiley = driver.find_element(by=By.XPATH, value='//span[@data-testid="smiley"]')
            smiley.click()
        except NoSuchElementException:
            print('Error: could not find smiley element')



def study_user(driver, user, language, excel):
	"""
	Generates an excel file with user data and checks their online status.

	Parameters:
	driver (webdriver): Selenium webdriver instance.
	user (str): The name of the user to study.
	language (str): The language of the user's WhatsApp account.
	excel (bool): Whether or not to generate an excel file.

	Returns:
	None
	"""
	# Create Excel File
	if excel:
		excel = Converter()

		excel.db_to()
		excel.db_to_excel()
		print("\n Your Data Has Been Added to Excel File")
	else:
		pass

	# First, go to their chat
	try:
		#We instantiate our Logs class, save current date and create a text file for the user
		x_arg = '//span[contains(text(), \'{}\')]'.format(user)
		print('Trying to find: {}'.format(x_arg))
		element = driver.find_element(by=By.XPATH, value = x_arg)
		element.click()
		print('Found and clicked!')

	except NoSuchElementException:
		print('{} is not found. Returning...(Maybe your contact is in the archive. Check it)'.format(user))
		return

	x_arg = str()

	idle_thread = threading.Thread(target=remove_idle, args=(driver,), daemon=True)
	idle_thread.start()

	# Now, we continuously check for their online status:
	if language == 'en' or language == 'de' or language == 'pt':
		x_arg = '//span[@title=\'{}\']'.format('online')
	elif language == 'es':
		x_arg = '//span[@title=\'{}\']'.format('en línea')
	elif language == 'fr':
		x_arg = '//span[@title=\'{}\']'.format('en ligne')
	elif language == 'cat':
		x_arg = '//span[@title=\'{}\']'.format('en línia')
	elif language == 'tr':
		x_arg = '//span[@title=\'{}\']'.format('çevrimiçi')

	print('Trying to find: {} in user {}'.format(x_arg, user))
	
	previous_state = 'OFFLINE' # by default, we consider the user to be offline. The first time the user goes online,
	first_online = time.time()
	cumulative_session_time = 0
	# it will be printed.
	while True:
		try:
			element = driver.find_element(by=By.XPATH, value = x_arg)
			if previous_state == 'OFFLINE':
				input = ('[{}][ONLINE] {}'.format(
					datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
					user))

				print(input)
				date = datetime.datetime.now().strftime('%Y-%m-%d')	
				hour = datetime.datetime.now().strftime('%H')
				minute = datetime.datetime.now().strftime('%M')
				second = datetime.datetime.now().strftime('%S')
				type_connection = 'CONNECTION'
				
				Database.insert_connection_data(user, date, hour, minute, second, type_connection)	
				first_online = time.time()
				previous_state = 'ONLINE'	
			
		except NoSuchElementException:
			if previous_state == 'ONLINE':
			# calculate approximate real time of WhatsApp being online
				total_online_time = time.time() - first_online # approximately what it takes onPause to send signal
				if total_online_time < 0: # This means that the user was typing instead of going offline.
					continue # Skip the rest of this iteration. Do nothing.
				cumulative_session_time += total_online_time
				input = ('[{}][DISCONNECTED] {} was online for {} seconds. Session total: {} seconds'.format(
					datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
					user,
					math.floor(total_online_time),
					math.floor(cumulative_session_time)))
				print(input)
				date = datetime.datetime.now().strftime('%Y-%m-%d')	
				hour = datetime.datetime.now().strftime('%H')
				minute = datetime.datetime.now().strftime('%M')
				second = datetime.datetime.now().strftime('%S')
				type_connection = "DISCONNECTION"
				time_connected = total_online_time

				Database.insert_disconnection_data(user, date, hour, minute, second, type_connection,round(time_connected))
				previous_state = 'OFFLINE'

		except NoSuchWindowException:
			print('ERROR: Your WhatsApp window has been minimized or closed, try running the code again, shutting down...')
			exit()



def whatsapp_login():
	"""
	Logs into WhatsApp Web using Selenium and returns the driver object.

	Raises:
	- InvalidArgumentException: If a Selenium navigator is already running in the background.

	Returns:
	- driver: A webdriver object with WhatsApp Web open and the user logged in.
	"""
	try:
		print('In order to make this program to work, you will need to log-in once in WhatsApp. After that, your session will be saved until you revoke it.')
		options = webdriver.ChromeOptions()
		options.add_argument("user-data-dir=C:\\Path")
		options.add_experimental_option('excludeSwitches', ['enable-logging'])
		driver = webdriver.Chrome(options=options)
		driver.get('https://web.whatsapp.com')
		assert 'WhatsApp' in driver.title 
		input('Press any key when you are at the chat menu...')

		return driver

	except InvalidArgumentException:
		print('ERROR: You may already have a Selenium navegator running in the background, close the window and run the code again, shutting down...')
		exit()






def main():
	"""
	This function creates a table in the database and parses command line arguments.
	It then logs into WhatsApp and studies the specified user in the specified language.
	If the excel flag is set, it converts the database to an Excel file.

	Args:
	None

	Returns:
	None
	"""

	Database.create_table()

	parser = argparse.ArgumentParser()
	parser.add_argument('-u', '--username', help='Username to track', required=True)
	parser.add_argument('-l', '--language', help='Language to use', required=True, choices=['en', 'es', 'fr', 'pt', 'de', 'cat','tr'])
	parser.add_argument('-e','--excel',help="Db to Excel Converter",required=False,action='store_true')
	parser.add_argument('-s', '--split', help="change the prefix with which the spaces of the --username flag will be separated", required=False, default="-")

	args = parser.parse_args()

	user_name = " ".join(args.username.split(args.split))

	driver = whatsapp_login()
	
	study_user(driver, user_name, args.language,args.excel)



if __name__ == '__main__':
	main()
