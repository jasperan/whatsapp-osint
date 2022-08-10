import time
import datetime

class Logs():

    @staticmethod
    def create_log(username, logs_date):
        with open('logs/{} {}.txt'.format(logs_date, username), 'w') as f:
            f.write('Tracking to user {} has started at {}'.format(username, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'a'))

    @staticmethod
    def update_log(input, username, logs_date):
        with open('logs/{} {}.txt'.format(logs_date, username), 'a') as f:
            f.write(f'\n{input}')
            f.close()        