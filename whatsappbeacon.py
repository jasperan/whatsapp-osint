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
from utils.logs_manager import Logs
import os
import time
import math
import datetime
import argparse


'''
░█──░█ █──█ █▀▀█ ▀▀█▀▀ █▀▀ █▀▀█ █▀▀█ █▀▀█ 　 ░█▀▀▀█ ░█▀▀▀█ ▀█▀ ░█▄─░█ ▀▀█▀▀ 
░█░█░█ █▀▀█ █▄▄█ ──█── ▀▀█ █▄▄█ █──█ █──█ 　 ░█──░█ ─▀▀▀▄▄ ░█─ ░█░█░█ ─░█── 
░█▄▀▄█ ▀──▀ ▀──▀ ──▀── ▀▀▀ ▀──▀ █▀▀▀ █▀▀▀ 　 ░█▄▄▄█ ░█▄▄▄█ ▄█▄ ░█──▀█ ─░█── 
░█▀▀█ ░█──░█ 　 ───░█ ─█▀▀█ ░█▀▀▀█ ░█▀▀█ ░█▀▀▀ ░█▀▀█ ─█▀▀█ ░█▄─░█ 
░█▀▀▄ ░█▄▄▄█ 　 ─▄─░█ ░█▄▄█ ─▀▀▀▄▄ ░█▄▄█ ░█▀▀▀ ░█▄▄▀ ░█▄▄█ ░█░█░█ 
░█▄▄█ ──░█── 　 ░█▄▄█ ░█─░█ ░█▄▄▄█ ░█─── ░█▄▄▄ ░█─░█ ░█─░█ ░█──▀█
'''



def study_user(driver, user, language):
	# First, go to their chat
	try:
		#We instantiate our Logs class, save current date and create a text file for the user
		logs = Logs()
		logs_date = datetime.datetime.now().strftime('%Y-%m-%d')
		logs.create_log(user, logs_date)
		print('There has been created in the folder ./logs a text file to log every connection and disconnection of the user {}'.format(user))
		
		x_arg = '//span[contains(text(), \'{}\')]'.format(user)
		print('Trying to find: {}'.format(x_arg))
		element = driver.find_element(by=By.XPATH, value = x_arg)
		element.click()
		print('Found and clicked!')

	except NoSuchElementException:
		print('{} is not found. Returning...'.format(user))
		return

	x_arg = str()
	# Now, we continuously check for their online status:
	if language == 'en' or language == 'de' or language == 'pt':
		x_arg = '//span[@title=\'{}\']'.format('online')
	elif language == 'es':
		x_arg = '//span[@title=\'{}\']'.format('en línea')
	elif language == 'fr':
		x_arg = '//span[@title=\'{}\']'.format('en ligne')
	elif language == 'cat':
		x_arg = '//span[@title=\'{}\']'.format('en línia')

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
				logs.update_log(input, user, logs_date)	
				first_online = time.time()
				previous_state = 'ONLINE'	
			
		except NoSuchElementException:
			if previous_state == 'ONLINE':
			# calculate approximate real time of WhatsApp being online
				total_online_time = time.time() - first_online - 12 # approximately what it takes onPause to send signal
				if total_online_time < 0: # This means that the user was typing instead of going offline.
					continue # Skip the rest of this iteration. Do nothing.
				cumulative_session_time += total_online_time
				input = ('[{}][DISCONNECTED] {} was online for {} seconds. Session total: {} seconds'.format(
					datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
					user,
					math.floor(total_online_time),
					math.floor(cumulative_session_time)))
				print(input)
				logs.update_log(input, user, logs_date)	
				previous_state = 'OFFLINE'

		except NoSuchWindowException:
			print('ERROR: Your WhatsApp window has been minimized or closed, try running the code again, shutting down...')
			exit()

		time.sleep(1)



def whatsapp_login():
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
	parser = argparse.ArgumentParser()
	parser.add_argument('-u', '--username', help='Username to track', required=True)
	parser.add_argument('-l', '--language', help='Language to use', required=True, choices=['en', 'es', 'fr', 'pt', 'de', 'cat'])
	args = parser.parse_args()

	driver = whatsapp_login()
	study_user(driver, args.username, args.language)



if __name__ == '__main__':
	main()