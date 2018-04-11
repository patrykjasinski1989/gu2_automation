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
                _values.append(lines[i+1].split('>')[1].split('<')[0])
                _cnt += 1
        if _cnt == 6:
            _order = {'id': _values[0], 'type': _values[1], 'channel': _values[2], 'status': _values[3],
                      'order_date': _values[4], 'realization_date': _values[5]}
            _orders.append(_order)
            _values = []
            _cnt = 0

    return _orders


if __name__ == '__main__':
    _msisdns = ['514791214',
                '515875042',
                '514708163',
                '789046027',
                '505544393',
                '797911014',
                '505660232',
                '503368023',
                '511283975',
                '690646670',
                '505868463',
                '518349027',
                '507926721',
                '798122974',
                '789114208',
                '517450088',
                '517743596',
                '797736502',
                '515169175',
                '515790718',
                '513376472',
                '500488148',
                '516687139',
                '797621740',
                '516398027',
                '511391532',
                '519451249',
                '518420505',
                '503482553',
                '503639746',
                '513790999',
                '512126169',
                '514475059',
                '789206537',
                '797437729',
                '517982243',
                '516914568',
                '515313111',
                '690425159',
                '504027899',
                '510740809',
                '505392976',
                '507250439',
                '517177653',
                '500321398',
                '518142036',
                '503402482',
                '789128598',
                '506958440',
                '690472869',
                '512703267',
                '515684287',
                '789131190',
                '517484199',
                '798852227',
                '517406651',
                '504736933',
                '798277872',
                '507964252',
                '516776728',
                '604620593',
                '518405117',
                '515302837',
                '501332190']
    print len(_msisdns)
    cnt = 0
    for msisdn in _msisdns:
        orders = get_orders(msisdn)
        for order in orders:
            if order['channel'] == 'OTSA' and order['status'] == 'COMPLETED':
                cnt = cnt + 1
    print cnt
