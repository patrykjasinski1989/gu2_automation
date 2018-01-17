# -*- coding: utf-8 -*-
import requests


def getContractData(msisdn):
    url = 'http://eai2-vip.centertel.pl:4125/invoke/ptk.adapter.rsw.billing/getContractData?msisdn={}'.format(msisdn)
    response = requests.get(url)
    return response.text.split('\n')


def getExpirationDate(contractData):
    expirationDateInNextLine = False
    for line in contractData:
        if 'expirationDate' in line:
            expirationDateInNextLine = True
            continue
        if expirationDateInNextLine:
            expirationDate = line.split('<TD>')[1].split('</TD>')[0]
            break
    return expirationDate


if __name__ == '__main__':
    print getExpirationDate(getContractData('573010799'))
    exit(666)
