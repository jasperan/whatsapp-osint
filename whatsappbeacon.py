#!/usr/local/anaconda3/bin/python3

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


def study_user(driver, user):
	# First, go to his/her chat
	try:
		# x_arg = '//span[@title={}]'.format(target)
		x_arg = '//span[contains(text(), \'{}\')]'.format(user)
		print('Trying to find: {}'.format(x_arg))
		element = driver.find_element_by_xpath(x_arg)
		element.click()
		print('Found and clicked!')
	except NoSuchElementException:
		print('{} is not found. Returning...'.format(user))
		return

	# Now, we continuously check for his/her online status:
	x_arg = '//span[@title=\'{}\']'.format('online')
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

		time.sleep(1)


def inf_sleep():
	while True:
		time.sleep(1)


def whatsapp_login():
    driver = webdriver.Chrome()
    # wait = WebDriverWait(browser, 600)
    driver.get('https://web.whatsapp.com')
    assert 'WhatsApp' in driver.title 
    driver.maximize_window()
    input('Scan the code and press any key...')
    print('QR scanned successfully!')
    return driver


def main():
	print('Logging in...')
	user = 'Guille Tocayo Oracle'

	print('Please, scan your QR code.')
	driver = whatsapp_login()
	study_user(driver, user)


if __name__ == '__main__':
	main()

