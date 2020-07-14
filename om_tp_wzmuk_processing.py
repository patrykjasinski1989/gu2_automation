"""This module handles OM TP WZMUK processing."""
import time
from datetime import datetime

from xlrd import open_workbook, cellname, xldate_as_tuple

import config
from helper_functions import get_ssh_connection


def get_users_data_from_xls(filename):
    """Return user data from xls file necessary to process the request."""
    book = open_workbook(filename)
    sheet = book.sheet_by_name('Lista osób')

    users = []
    for row in range(8, sheet.nrows):
        user = {}
        for col in range(sheet.ncols):
            if 'K' in cellname(row, col):
                user['login_ad'] = sheet.cell(row, col).value
            elif 'S' in cellname(row, col):
                user['typ_wniosku'] = sheet.cell(row, col).value
            elif 'T' in cellname(row, col):
                user['profil'] = sheet.cell(row, col).value
            elif 'V' in cellname(row, col):
                date_value = xldate_as_tuple(sheet.cell(row, col).value, book.datemode)[:3]
                user['data_waznosci_konta'] = datetime(*date_value)
            elif 'X' in cellname(row, col):
                user['przedluzenie_dostepu'] = sheet.cell(row, col).value
        users.append(user)
    return users


def disable_user(user):
    """Run shell script to disable account."""
    shell = get_ssh_connection(*config.EAI_IS.values())
    shell.send('sudo su - webmeth1' + '\r\n')
    shell.send('ssh 126.185.9.192' + '\r\n')
    shell.send('cd kk02/wzmuki' + '\r\n')
    shell.send(f'./wzmukiDIS_solo.sh {user}' + '\r\n')
    time.sleep(1)
