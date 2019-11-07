"""This module is used to get data from EAI PTK.
So far only one service - gCD and one field that we're interested in - expirationDate"""

import requests

import config

EAI_PTK_SERVER = config.EAI['server']


def get_contract_data(msisdn):
    """Returns response from getContractData service for a given MSISDN number."""
    url = '{0}/invoke/ptk.adapter.rsw.billing/getContractData?msisdn={1}'.format(EAI_PTK_SERVER, msisdn)
    response = requests.get(url)
    return response.text.split('\n')


def get_expiration_date(contract_data):
    """Extracts expiration date from getContractData response."""
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
