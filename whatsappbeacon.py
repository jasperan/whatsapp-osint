from http.client import CONTINUE
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
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



def on_press(key):
    print('{0} pressed'.format(
        key))



def study_user(driver, user, language):
	# First, go to their chat
	try:
		x_arg = '//span[contains(text(), \'{}\')]'.format(user)
		print('Trying to find: {}'.format(x_arg))
		element = driver.find_element_by_xpath(x_arg)
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
			element = driver.find_element_by_xpath(x_arg)
			if previous_state == 'OFFLINE':
				print('[{}][ONLINE] {}'.format(
					datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
					user))
				first_online = time.time()
				previous_state = 'ONLINE'	
			
		except NoSuchElementException:
			if previous_state == 'ONLINE':
			# calculate approximate real time of WhatsApp being online
				total_online_time = time.time() - first_online - 12 # approximately what it takes onPause to send signal
				if total_online_time < 0: # This means that the user was typing instead of going offline.
					continue # Skip the rest of this iteration. Do nothing.
				cumulative_session_time += total_online_time
				print('[{}][DISCONNECTED] {} was online for {} seconds. Session total: {} seconds'.format(
					datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
					user,
					math.floor(total_online_time),
					math.floor(cumulative_session_time)))
				previous_state = 'OFFLINE'

		leave_track = str(input('Type stop if you desire to change user to track or end program'))
		if leave_track == 'stop':
			
			username = menu()
			
			study_user(driver, username, language)

		time.sleep(1)


def menu():
	print_menu()
	option = int(input('Enter your choice: '))
	if option == 1:
		username = input('Introduce name of the user to track: ')
	elif option == 2:
		raise SystemExit(0)
	else:
		print('You have introduced a wrong option, try again')
		option = int(input('Enter your choice: '))

	return username

def print_menu():
	print('1. Change user to track')
	print('2. Exit program')	

def inf_sleep():
	while True:
		time.sleep(1)



def whatsapp_login():
	options = webdriver.ChromeOptions()
	options.add_experimental_option('excludeSwitches', ['enable-logging'])
	driver = webdriver.Chrome(options=options)
	driver.get('https://web.whatsapp.com')
	assert 'WhatsApp' in driver.title 
	input('Scan the code and press any key...')
	print('QR scanned successfully!')
	return driver



def main():
	username = "Gloglito"
	language = 'en'

	print('Logging in...')
	print('Please, scan your QR code.')
	driver = whatsapp_login()
	study_user(driver, username, language)



if __name__ == '__main__':
	main()