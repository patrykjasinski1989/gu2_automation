import paramiko
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

import config

SERVER = config.OM_TP['server']
USER = config.OM_TP['user']
PASSWORD = config.OM_TP['password']


def get_order_info(tel_id):
    url = '{}/BlsOmConsole/getOrderInfo.dsp?tel={}'.format(SERVER, tel_id)
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(config.EAI_IS['server'], username=config.EAI_IS['user'], password=config.EAI_IS['password'],
                       allow_agent=False)
    _, stdout, _ = ssh_client.exec_command('curl -k -u {}:{} {}'.format(USER, PASSWORD, url))
    stdout = ''.join(stdout.readlines())
    ssh_client.close()
    return BeautifulSoup(stdout, 'html.parser')


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
    order_info_ = get_order_info('TEL000128143169')

    order_data_ = get_order_data(order_info_)
    for key in order_data_:
        print('{}: {}'.format(key, order_data_[key]))

    process_errors_ = get_process_errors(order_info_)
    print('\nErrors: ')
    for process_error in sorted(process_errors_):
        print(process_error)
