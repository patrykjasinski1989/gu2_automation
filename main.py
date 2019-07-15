# -*- coding: utf-8 -*-
import os
import re

import cx_Oracle
import paramiko
from datetime import datetime
from dateutil import parser
from xlrd import open_workbook, cellname, xldate_as_tuple

from eai import get_expiration_date, get_contract_data
from ml import ml_prod_connection
from ml_sti import ml_sti_connection, recertify_account, create_account, delete_account
from nra import get_sim_status, nra_connection, set_sim_status_nra, set_sim_status_bscs, set_imsi_status_bscs
from otsa import otsa_connection, check_sim, unlock_account
from otsa_processing import process_msisdns
from remedy import get_incidents, close_incident, is_empty, get_work_info, add_work_info, reassign_incident, \
    get_pending_incidents, assign_incident, get_all_incidents
from rsw import rsw_connection, get_latest_order, add_entitlement, get_offer_id_by_name


def process_transactions():

    incidents = get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'AKTYWACJA KLIENTA'
    )
    incidents += get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'MIGRACJA KLIENTA'
    )
    incidents += get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'SPRZEDAZ USLUG'
    )

    msisdn_regex = re.compile('\d{3}[ -]?\d{3}[ -]?\d{3}')
    trans_num_regex = re.compile('[A-Z0-9]{5,}?/?[0-9]{4}/[0-9]+')
    for inc in incidents:
        resolution = ''
        lines = inc['notes']
        all_resolved = True
        for i in range(len(lines)):
            if 'Proszę podać numer MSISDN' in lines[i] or 'Numer telefonu klienta Orange / MSISDN' in lines[i]:
                msisdns = msisdn_regex.findall(lines[i + 1])
                msisdns += msisdn_regex.findall(lines[i + 2])
                msisdns = [msisdn.translate(''.maketrans({'-': '', ' ': ''})) for msisdn in msisdns]
                trans_nums = trans_num_regex.findall(lines[i + 1])
                resolution, all_resolved = process_msisdns(msisdns, trans_nums, inc)
        if is_empty(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
        if resolution != '' and all_resolved:
            resolution = '\r\n'.join(list(set(resolution.split('\r\n')))).strip()
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))


def release_resources():
    incidents = get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '000_incydent/awaria/uszkodzenie',
        'OTSA',
        'UWOLNIENIE ZASOBOW'
    )

    otsa = otsa_connection()
    sim_regex = re.compile('[0-9]{19,20}')
    for inc in incidents:
        sims = []
        for line in inc['notes']:
            sims.extend(sim_regex.findall(line))

        all_resolved = True
        resolution = ''

        nra = nra_connection()
        for sim in sims:
            partial_resolution = ''
            result = check_sim(otsa, sim)
            result = [r for r in result if r['status'] not in ('3D', '3G')]
            if len(result) == 0:
                wi_notes = ''
                sim_status = get_sim_status(nra, sim)
                if len(sim_status) == 0:
                    partial_resolution = 'Brak karty SIM {0} w nRA. Proszę podać poprawny numer.'.format(sim)
                    resolution = partial_resolution + '\r\n'
                    continue
                if sim_status['status_nra'] == sim_status['status_bscs']:
                    if sim_status['status_nra'] in ('r', 'd', 'l', 'E') \
                            and sim_status['status_nra'] == sim_status['status_bscs']:
                        set_sim_status_nra(nra, sim, 'r')
                        set_sim_status_bscs(nra, sim, 'r')
                        set_imsi_status_bscs(nra, sim_status['imsi'], 'r')
                        partial_resolution = 'Karta SIM {0} uwolniona.'.format(sim)
                    elif sim_status['status_nra'] in ('a', 'B'):
                        partial_resolution = 'Karta SIM {0} aktywna. Brak możliwości odblokowania.'.format(sim)
                    else:
                        all_resolved = False
                        wi_notes += 'Karta SIM {} w statusie {}.\nW Optiposie brak powiązań.'.format(sim, sim_status)
                if wi_notes:
                    add_work_info(inc, 'VC_OPTIPOS', wi_notes)
                    reassign_incident(inc, 'NRA')
            else:
                partial_resolution = 'Karta SIM {0} powiązana z nieanulowaną umową {1}. Brak możliwości odblokowania. ' \
                                     'Proszę o kontakt z dealer support lub z działem reklamacji.' \
                    .format(sim, result[0]['trans_num'])
            if partial_resolution != '':
                resolution = resolution + '\r\n' + partial_resolution
        nra.close()

        if is_empty(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'

        if all_resolved and resolution != '':
            resolution = '\r\n'.join(list(set(resolution.split('\r\n')))).strip()
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution))
    otsa.close()


def problems_with_offer():
    incidents = get_incidents(
        'VC3_BSS_RSW',
        '(357) RSW / nBUK',
        '(357B) PROBLEMY Z OFERTĄ I TERMINALAMI',
        'Orange Mobile, B2C, B2B, Love'
    )

    for inc in incidents:
        msisdn = ''
        msisdn_in_next_line = False
        offer_name = ''
        for line in inc['notes']:
            if 'Numer telefonu klienta Orange / MSISDN' in line:
                msisdn_in_next_line = True
                continue
            if msisdn_in_next_line:
                msisdn = line.strip()
                msisdn_in_next_line = False
            if 'Proszę o dodanie oferty: ' in line:
                offer_name = line.split(': ')[1].split('.')[0]

        expiration_date = get_expiration_date(get_contract_data(msisdn))
        if expiration_date != '':
            dt = parser.parse(expiration_date)
        else:
            continue
        now = datetime.now()
        if (offer_name.lower() == 'plan komórkowy' or offer_name.lower() == 'internet mobilny') \
                and (dt - now).days > 120:
            resolution = 'Klient ma lojalkę do {0}. Zgodnie z konfiguracją marketingową oferta {1} ' \
                         'jest dostępna na 120 dni przed końcem lojalki, czyli klient tych wymagań nie spełnia. ' \
                         'Brak błędu aplikacji.'.format(expiration_date, offer_name)
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))


def unlock_accounts():
    incidents = get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '000_incydent/awaria/uszkodzenie',
        'OTSA/OPTIPOS',
        'ODBLOKOWANIE KONTA'
    )

    sd_tiers = ['OKI i SOHO - AKTYWACJA KONTA', '[DETAL PTK] KKB,ADT - AKTYWACJA KONTA',
                '[DETAL TP] DEALER SUPPORT - AKTYWACJA KONTA', 'ZŁD Aktywacja/Modyfikacja konta']
    for tier3 in sd_tiers:
        incidents += get_incidents(
            'VC3_BSS_OPTIPOS_MOBILE',
            '000_wniosek o dostęp/instalację/dostarczenie',
            'OTSA/OPTIPOS',
            tier3
        )

    otsa = otsa_connection()

    for inc in incidents:
        login = None
        # looking for login in incident description
        login_in_next_line = False
        for line in inc['notes']:
            if 'Podaj login OTSA' in line:
                login_in_next_line = True
                continue
            if login_in_next_line:
                login = line.strip().lower()
                break
        # login not found, looking in work info
        if not login:
            wi = get_work_info(inc)
            for entry in wi:
                notes = ' '.join(entry['notes']).lower().replace(':', ' ').split()
                if 'sd' in entry['summary'].lower() and 'zdjęcie' in notes:
                    for word in 'lub odbicie na sd'.split():
                        if word in notes:
                            notes.remove(word)
                    if 'konta' in notes and 'login' not in notes:
                        login = notes[notes.index('konta') + 1]
                    elif 'loginu' in notes:
                        login = notes[notes.index('loginu') + 1]
                    elif 'login' in notes:
                        login = notes[notes.index('login') + 1]
                    elif 'logowania' in notes:
                        login = notes[notes.index('logowania') + 1]
                    else:
                        login = notes[-1]
        # unlock account if login found
        if login:
            rows_updated = unlock_account(otsa, login)
            if rows_updated == 1:
                resolution = 'Konto o loginie {} jest aktywne. Nowe hasło to: centertel.'.format(login)
                close_incident(inc, resolution)
                print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))

    otsa.close()


def close_pending_rsw():
    incidents = get_pending_incidents(['VC3_BSS_RSW'])
    msisdn_regex = re.compile('\d{3}[ -]?\d{3}[ -]?\d{3}')
    rsw = rsw_connection()
    for inc in incidents:
        resolution = ''
        lines = inc['notes']
        msisdns = None
        last_order = None
        for i in range(len(lines)):
            if 'Numer telefonu klienta Orange / MSISDN' in lines[i] and i < len(lines) - 1:
                msisdns = msisdn_regex.findall(lines[i + 1])
        if msisdns:
            msisdns = [msisdn.translate(''.maketrans({'-': '', ' ': ''})) for msisdn in msisdns]
        if msisdns and len(msisdns) != 1:
            continue
        elif msisdns:
            msisdn = msisdns[0]
            last_order = get_latest_order(rsw, msisdn)
        if last_order and last_order['data_zamowienia'] > inc['reported_date'] and last_order['ilosc_prob'] == 0:
            if last_order['status'] == 16 and last_order['status_om'] == 4:
                resolution = 'Na podanym numerze {} jest już zrealizowane zamówienie {} z {}.'. \
                    format(msisdn, last_order['id_zamowienia'], last_order['data_zamowienia'])
            elif last_order['status'] in (2, 3):
                resolution = 'Na podanym numerze {} jest już zamówienie {} w trakcie realizacji w ML.'. \
                    format(msisdn, last_order['id_zamowienia'])
        if resolution:
            assign_incident(inc)
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))

    rsw.close()


def offer_entitlement():
    incidents = get_incidents(
        'VC3_BSS_RSW',
        '(357) RSW / nBUK',
        '(357B) PROBLEMY Z OFERTĄ I TERMINALAMI',
        'Orange Mobile, B2C, B2B, Love'
    )

    msisdn_regex = re.compile('\d{3}[ -]?\d{3}[ -]?\d{3}')
    rsw = rsw_connection()
    for inc in incidents:
        resolution = ''
        entitlement = False
        prepaid = False
        msisdns = None
        offer_name = None
        lines = inc['notes']
        for i in range(len(lines)):
            if 'Nazwa oferty' in lines[i]:
                offer_name = lines[i + 1].strip()
                offer_id = get_offer_id_by_name(rsw, offer_name)
            if ('Numer telefonu klienta Orange / MSISDN' in lines[i] or
                'Proszę podać numer MSISDN oraz numer koszyka z którym jest problem:' in lines[i]) \
                    and i < len(lines) - 1:
                msisdns = msisdn_regex.findall(lines[i + 1])
            if 'proszę o uprawnienie' in lines[i].lower() or 'proszę o dodanie' in lines[i].lower():
                entitlement = True
            if 'prepaid' in lines[i].lower():
                prepaid = True
        if msisdns:
            msisdns = [msisdn.translate(''.maketrans({'-': '', ' ': ''})) for msisdn in msisdns]
        if msisdns and len(msisdns) != 1:
            continue
        elif msisdns:
            msisdn = msisdns[0]
        if msisdns and entitlement:
            if offer_id:
                add_entitlement(rsw, msisdn, offer_id)
            elif prepaid:
                add_entitlement(rsw, msisdn, 3624)
            else:
                add_entitlement(rsw, msisdn)
            resolution = 'Numer {} uprawniony.'.format(msisdn)
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))
    rsw.close()


def map_profile_to_db(profile_name):
    profile_name_lower = profile_name.lower()
    db_profile = None
    if 'dealer' in profile_name_lower and 'support' in profile_name_lower:
        db_profile = 'DS_Orange_Love'
    elif 'read_only' in profile_name_lower and 'pickup' not in profile_name_lower:
        db_profile = 'Read_only'
    elif 'ML_' in profile_name:
        db_profile = profile_name[3:]
    return db_profile


def process_ml_wzmuks(tier2, ml_connection, env_name):
    incidents = get_incidents(
        'VC3_BSS_ML',
        '(185) E-WZMUK-konto w SI Nowe/Modyfikacja/Likwidacja',
        tier2,
        '40h'
    )

    ml = ml_connection()

    for inc in incidents:
        wi = get_work_info(inc)
        filename, contents = wi[0]['attachment']

        xls_file = open(filename, 'wb')
        xls_file.write(contents)
        xls_file.close()
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
        os.remove(filename)

        resolution = ''
        for user in users:
            if user['typ_wniosku'] == 'Modyfikacja uprawnień':
                rows_updated = recertify_account(
                    ml, user['login_ad'], user['data_waznosci_konta'], user['profil'], inc['inc'])
                if rows_updated == 1:
                    resolution += 'Przedłużono dostęp do {} dla konta AD {} do dnia {}.\n'. \
                        format(env_name, user['login_ad'], user['data_waznosci_konta'])
                elif rows_updated == 0:
                    rows_inserted = create_account(
                        ml, user['login_ad'], user['data_waznosci_konta'], user['profil'], inc['inc'])
                    if rows_inserted == 1:
                        resolution += 'Utworzono dostęp do {} dla konta AD {} z profilem {} do dnia {}.\n'. \
                            format(env_name, user['login_ad'], user['profil'], user['data_waznosci_konta'])

            elif user['typ_wniosku'] == 'Nowe konto':
                try:
                    rows_inserted = create_account(
                        ml, user['login_ad'], user['data_waznosci_konta'], user['profil'], inc['inc'])
                except cx_Oracle.IntegrityError:
                    rows_inserted = 0
                if rows_inserted == 1:
                    resolution += 'Utworzono dostęp do {} dla konta AD {} z profilem {} do dnia {}.\n'. \
                        format(env_name, user['login_ad'], user['profil'], user['data_waznosci_konta'])
                elif rows_inserted == 0:
                    rows_updated = recertify_account(
                        ml, user['login_ad'], user['data_waznosci_konta'], user['profil'], inc['inc'])
                    if rows_updated == 1:
                        resolution += 'Przedłużono dostęp do {} dla konta AD {} do dnia {}.\n'. \
                            format(env_name, user['login_ad'], user['data_waznosci_konta'])

            elif user['typ_wniosku'] == 'Likwidacja konta':
                rows_updated = delete_account(ml, user['login_ad'], inc)
                if rows_updated == 1:
                    resolution += 'Usunięto dostęp do {} dla konta AD {}.\n'.format(env_name, user['login_ad'])
                elif rows_updated == 0:
                    resolution += 'Brak dostępu do {} dla konta AD {}.\n'.format(env_name, user['login_ad'])

        if resolution:
            close_incident(inc, resolution.strip())
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))

    ml.close()


def ml_wzmuk_sti():
    process_ml_wzmuks(tier2='M55 ML_STI', ml_connection=ml_sti_connection, env_name='ML ŚTI')


def ml_wzmuk_prod():
    process_ml_wzmuks(tier2='M38 ML', ml_connection=ml_prod_connection, env_name='ML PROD')


def empty_rsw_inc():
    all_rsw_inc = get_all_incidents('VC3_BSS_RSW')
    for inc in all_rsw_inc:
        if is_empty(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))


if __name__ == '__main__':

    lock_file = 'lock'
    if os.path.exists(lock_file):
        print('Lock file exists. Remove it to run the program.')
        exit(666)
    try:
        unlock_accounts()
        process_transactions()
        release_resources()
        problems_with_offer()
        close_pending_rsw()
        offer_entitlement()
        empty_rsw_inc()
        ml_wzmuk_sti()
        ml_wzmuk_prod()
    except cx_Oracle.DatabaseError as e:
        print('Database error: {}.\nCreating lock file and exiting...'.format(e))
        open(lock_file, 'w+')
        exit(666)
    except paramiko.ssh_exception.AuthenticationException as e:
        print('SSH error: {}.\nCreating lock file and exiting...'.format(e))
        open(lock_file, 'w+')
        exit(666)
