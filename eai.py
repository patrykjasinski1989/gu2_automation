# -*- coding: utf-8 -*-
import requests

import config

server = config.eai['server']


def get_contract_data(msisdn):
    url = '{0}/invoke/ptk.adapter.rsw.billing/getContractData?msisdn={1}'.format(server, msisdn)
    response = requests.get(url)
    return response.text.split('\n')


def get_expiration_date(contract_data):
    expiration_date = ''
    expiration_date_in_next_line = False
    for line in contract_data:
        if 'expirationDate' in line:
            expiration_date_in_next_line = True
            continue
        if expiration_date_in_next_line:
            expiration_date = line.split('<TD>')[1].split('</TD>')[0]
            break
    return expiration_date


if __name__ == '__main__':
    print(get_expiration_date(get_contract_data('573010799')))
    print(get_expiration_date(get_contract_data('5730107999')))
    exit(666)
