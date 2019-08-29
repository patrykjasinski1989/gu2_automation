"""This module is used for getting data from OM PTK console."""

import requests
from requests.auth import HTTPBasicAuth

import config

SERVER = config.OM_PTK['server']
USER = config.OM_PTK['user']
PASSWORD = config.OM_PTK['password']


def get_orders(key):
    """Returns all orders for a given key in a human-friendly format."""
    session = requests.session()
    url = '{}/PtkOMConsole/requests/ordersByKey.dsp?key={}'.format(SERVER, key)
    response = session.get(url=url, auth=HTTPBasicAuth(USER, PASSWORD), timeout=3)
    lines = response.text.split('\n')

    _cnt = 0
    _values = []
    _orders = []
    for i, line in enumerate(lines):
        if '<td nowrap="nowrap" class="evenrowdata">' in line:
            if '</td>' in lines[i]:
                _values.append(line.split('>')[1].split('<')[0])
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
    """Returns all FRs for a given key in a human-friendly format."""
    session = requests.session()
    url = '{}/PtkOMConsole/requests/failedRequestsByKey.dsp?key={}'.format(SERVER, key)
    response = session.get(url=url, auth=HTTPBasicAuth(USER, PASSWORD), timeout=3)
    lines = response.text.split('\n')

    cnt = 0
    values = []
    failed_requests = []
    for i, line in enumerate(lines):
        if '<td nowrap="nowrap" class="evenrowdata">' in line:
            if '</td>' in line:
                values.append(line.split('>')[1].split('<')[0])
            elif len(lines[i + 1].split('>')) > 1:
                values.append(lines[i + 1].split('>')[1].split('<')[0])
            else:
                values.append(lines[i + 2].split('>')[1].split('<')[0])
            cnt += 1
        if cnt == 6:
            _failed_request = {'id': values[0], 'type': values[1], 'channel': values[2], 'date': values[3],
                               'error_code': values[4], 'order': values[5]}
            failed_requests.append(_failed_request)
            values = []
            cnt = 0

    return failed_requests


if __name__ == '__main__':
    FRS = get_failed_requests('514465271')
    for failed_request in FRS:
        print(failed_request)
