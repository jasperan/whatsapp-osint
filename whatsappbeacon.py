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


def goto_user(driver, target):
	try:
		# x_arg = '//span[@title={}]'.format(target)
		x_arg = '//span[contains(text(), \'{}\')]'.format(target)
		print('Trying to find: {}'.format(x_arg))
		element = driver.find_element_by_xpath(x_arg)
		element.click()
		print('Found and clicked!')
	except NoSuchElementException:
		print('Element is not found. Returning...')
		return
		
'''
		input_box = browser.find_element_by_xpath('//*[@id="main"]/footer/div[1]/div[2]/div/div[2]')
		for ch in message:
			if ch == "\n":
				ActionChains(browser).key_down(Keys.SHIFT).key_down(Keys.ENTER).key_up(Keys.ENTER).key_up(Keys.SHIFT).key_up(Keys.BACKSPACE).perform()
			else:
				input_box.send_keys(ch)
		input_box.send_keys(Keys.ENTER)
		print("Message sent successfuly")
		time.sleep(1)
	except NoSuchElementException:
		return
'''

def study_user(driver, user):
	x_arg = '//span[contains(text(), \'{}\']'.format('online')
	x_arg_test = '//span[@title=\'{}\']'.format('online')
	print('Trying to find: {} in user {}'.format(x_arg_test, user))
	while True:
		try:
			element = driver.find_element_by_xpath(x_arg_test)
			print('Found element!')
		except NoSuchElementException:
			print('User is offline')
		time.sleep(3)


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
	user = 'Dani Oracle'

	print('Please, scan your QR code.')
	driver = whatsapp_login()
	goto_user(driver, user) # testing
	study_user(driver, user)
	inf_sleep()


if __name__ == '__main__':
	main()

