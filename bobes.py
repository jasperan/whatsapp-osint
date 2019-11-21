import time
import pyautogui


def modo_asqueroso():
	for i in range(50):
		pyautogui.press('tab')
	pyautogui.press('space')
	pyautogui.press('down')
	pyautogui.press('enter')

	for i in range(12):
		pyautogui.press('tab')
		time.sleep(1)
		pyautogui.press('space')
		time.sleep(1)
		for j in range(3):
			pyautogui.press('down')
			time.sleep(.25)
		pyautogui.press('enter')
	
	time.sleep(1)
	pyautogui.press('tab')
	time.sleep(1)
	pyautogui.press('enter')


def main():
	time.sleep(2)
	modo_asqueroso()
	time.sleep(3)


if __name__ == '__main__':
	main()

