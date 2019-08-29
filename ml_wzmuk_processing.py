"""This module handles ML WZMUK processing."""
import os

import cx_Oracle
from datetime import datetime
from xlrd import open_workbook, cellname, xldate_as_tuple

from db.ml import ml_prod_connection
from db.ml_sti import recertify_account, create_account, delete_account, ml_sti_connection
from remedy import get_incidents, get_work_info, close_incident


def ml_wzmuk_sti():
    """Process ML access requests for STI (test) environment."""
    process_ml_wzmuks(tier2='M55 ML_STI', ml_connection=ml_sti_connection, env_name='ML ŚTI')


def ml_wzmuk_prod():
    """Process ML access requests for PROD environment."""
    process_ml_wzmuks(tier2='M38 ML', ml_connection=ml_prod_connection, env_name='ML PROD')


def process_ml_wzmuks(tier2, ml_connection, env_name):
    """Process access requests for ML system. Depending on what's in the request it can:
    create a new account, delete an old one, or change permissions for an existing account."""
    incidents = get_incidents(
        'VC3_BSS_ML',
        '(185) E-WZMUK-konto w SI Nowe/Modyfikacja/Likwidacja',
        tier2,
        '40h'
    )
    try:
        ml_con = ml_connection()
    except cx_Oracle.DatabaseError:
        return

    for inc in incidents:
        work_info = get_work_info(inc)
        filename, contents = work_info[0]['attachment']

        xls_file = open(filename, 'wb')
        xls_file.write(contents)
        xls_file.close()
        users = get_users_data_from_xls(filename)
        os.remove(filename)

        resolution = ''
        for user in users:
            if user['typ_wniosku'] == 'Modyfikacja uprawnień':
                resolution += ml_modify_access(ml_con, user, env_name, inc)
            elif user['typ_wniosku'] == 'Nowe konto':
                resolution += ml_add_access(ml_con, user, env_name, inc)
            elif user['typ_wniosku'] == 'Likwidacja konta':
                resolution += ml_remove_access(ml_con, user, env_name, inc)

        if resolution:
            close_incident(inc, resolution.strip())
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))

    ml_con.close()


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
                profile = sheet.cell(row, col).value
                user['profil'] = map_profile_to_db(profile)
            elif 'U' in cellname(row, col):
                date_value = xldate_as_tuple(sheet.cell(row, col).value, book.datemode)[:3]
                user['data_waznosci_konta'] = datetime(*date_value)
            elif 'W' in cellname(row, col):
                user['przedluzenie_dostepu'] = sheet.cell(row, col).value
        users.append(user)
    return users


def map_profile_to_db(profile_name):
    """Return a proper DB profile name for a profile name taken from the access request."""
    profile_name_lower = profile_name.lower()
    db_profile = None
    if 'dealer' in profile_name_lower and 'support' in profile_name_lower:
        db_profile = 'DS_Orange_Love'
    elif 'read_only' in profile_name_lower and 'pickup' not in profile_name_lower:
        db_profile = 'Read_only'
    elif 'biznes' in profile_name_lower:
        db_profile = 'Biznes'
    elif 'ML_' in profile_name:
        db_profile = profile_name[3:]
    return db_profile


def ml_modify_access(ml_con, user, env_name, inc):
    """Modify user's access to ML."""
    resolution = ''
    rows_updated = recertify_account(
        ml_con, user['login_ad'], user['data_waznosci_konta'], user['profil'], inc['inc'])
    if rows_updated == 1:
        resolution += 'Przedłużono dostęp do {} dla konta AD {} do dnia {}.\n'. \
            format(env_name, user['login_ad'], user['data_waznosci_konta'])
    elif rows_updated == 0:
        rows_inserted = create_account(
            ml_con, user['login_ad'], user['data_waznosci_konta'], user['profil'], inc['inc'])
        if rows_inserted == 1:
            resolution += 'Utworzono dostęp do {} dla konta AD {} z profilem {} do dnia {}.\n'. \
                format(env_name, user['login_ad'], user['profil'], user['data_waznosci_konta'])
    return resolution


def ml_add_access(ml_con, user, env_name, inc):
    """Add access to ML for user."""
    resolution = ''
    try:
        rows_inserted = create_account(
            ml_con, user['login_ad'], user['data_waznosci_konta'], user['profil'], inc['inc'])
    except cx_Oracle.IntegrityError:
        rows_inserted = 0
    if rows_inserted == 1:
        resolution += 'Utworzono dostęp do {} dla konta AD {} z profilem {} do dnia {}.\n'. \
            format(env_name, user['login_ad'], user['profil'], user['data_waznosci_konta'])
    elif rows_inserted == 0:
        rows_updated = recertify_account(
            ml_con, user['login_ad'], user['data_waznosci_konta'], user['profil'], inc['inc'])
        if rows_updated == 1:
            resolution += 'Przedłużono dostęp do {} dla konta AD {} do dnia {}.\n'. \
                format(env_name, user['login_ad'], user['data_waznosci_konta'])


def ml_remove_access(ml_con, user, env_name, inc):
    """Remove access to ML from user."""
    resolution = ''
    rows_updated = delete_account(ml_con, user['login_ad'], inc)
    if rows_updated == 1:
        resolution += 'Usunięto dostęp do {} dla konta AD {}.\n'.format(env_name, user['login_ad'])
    elif rows_updated == 0:
        resolution += 'Brak dostępu do {} dla konta AD {}.\n'.format(env_name, user['login_ad'])
    return resolution
