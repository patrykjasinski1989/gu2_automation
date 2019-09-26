import requests
import urllib3
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

import config

SERVER = config.OM_TP['server']
USER = config.OM_TP['user']
PASSWORD = config.OM_TP['password']


def get_order_info(tel_id):
    session = requests.session()
    url = '{}/TpOrderManagementConsole/getOrderInfo.dsp?tel={}'.format(SERVER, tel_id)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = session.get(url=url, auth=HTTPBasicAuth(USER, PASSWORD), timeout=3, verify=False)
    return BeautifulSoup(response.content, 'html.parser')


def get_order_data(order_info):
    left_column = order_info.find_all('div', class_='leftColumn')
    right_column = order_info.find_all('div', class_='rightColumn')
    columns = zip(left_column, right_column)
    order_data = {}
    for left, right in columns:
        left = left.get_text().strip()
        right = right.get_text().strip()
        order_data[left] = right
    return order_data


def get_process_errors(order_info):
    errors = order_info.find_all('tr', class_='dark_row_red')
    process_errors = []
    for error in errors:
        process_errors.append(error.get_text().replace('\xa0', '').split('\n'))
    for element in process_errors:
        element.pop(0)
    return process_errors


if __name__ == '__main__':
    order_info_ = get_order_info('TEL000124646896')

    order_data_ = get_order_data(order_info_)
    for key in order_data_:
        print('{}: {}'.format(key, order_data_[key]))

    process_errors_ = get_process_errors(order_info_)
    print('\nErrors: ')
    for process_error in process_errors_:
        print(process_error)
