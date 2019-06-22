# -*- coding: utf-8 -*-
import requests
from requests.auth import HTTPBasicAuth

import config

server = config.om['server']
user = config.om['user']
password = config.om['password']


def get_orders(key):
    s = requests.session()
    url = '{}/PtkOMConsole/requests/ordersByKey.dsp?key={}'.format(server, key)
    response = s.get(url=url, auth=HTTPBasicAuth(user, password), timeout=3)
    lines = response.text.split('\n')

    _cnt = 0
    _values = []
    _orders = []
    for i in range(len(lines)):
        if '<td nowrap="nowrap" class="evenrowdata">' in lines[i]:
            if '</td>' in lines[i]:
                _values.append(lines[i].split('>')[1].split('<')[0])
                _cnt += 1
            else:
                _values.append(lines[i + 1].split('>')[1].split('<')[0])
                _cnt += 1
        if _cnt == 6:
            _order = {'id': _values[0], 'type': _values[1], 'channel': _values[2], 'status': _values[3],
                      'order_date': _values[4], 'realization_date': _values[5]}
            _orders.append(_order)
            _values = []
            _cnt = 0

    return _orders


def get_failed_requests(key):
    s = requests.session()
    url = '{}/PtkOMConsole/requests/failedRequestsByKey.dsp?key={}'.format(server, key)
    response = s.get(url=url, auth=HTTPBasicAuth(user, password), timeout=3)
    lines = response.text.split('\n')

    cnt = 0
    values = []
    failed_requests = []
    for i in range(len(lines)):
        if '<td nowrap="nowrap" class="evenrowdata">' in lines[i]:
            if '</td>' in lines[i]:
                values.append(lines[i].split('>')[1].split('<')[0])
            elif len(lines[i + 1].split('>')) > 1:
                values.append(lines[i + 1].split('>')[1].split('<')[0])
            else:
                values.append(lines[i + 2].split('>')[1].split('<')[0])
            cnt += 1
        if cnt == 6:
            fr = {'id': values[0], 'type': values[1], 'channel': values[2], 'date': values[3],
                  'error_code': values[4], 'order': values[5]}
            failed_requests.append(fr)
            values = []
            cnt = 0

    return failed_requests


if __name__ == '__main__':
    frs = get_failed_requests('514465271')
    for fr in frs:
        print(fr)
