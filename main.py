"""This is the script used to close the tickets. GU2 Sales Incidents for OPL to be exact.
Should be broken into smaller parts..."""
__author__ = "Patryk Jasiński <pjasinski@bluesoft.com>"

import os
import re

import cx_Oracle
import paramiko
from datetime import datetime
from dateutil import parser

from db.otsa import otsa_connection, unlock_account
from db.rsw import rsw_connection, get_latest_order, add_entitlement, get_offer_id_by_name
from eai_ptk import get_expiration_date, get_contract_data
from ml_wzmuk_processing import ml_wzmuk_sti, ml_wzmuk_prod
from otsa_processing import process_msisdns
from remedy import get_incidents, close_incident, is_empty, get_work_info, \
    get_pending_incidents, assign_incident, get_all_incidents
from sim_processing import process_sims


def process_transactions():
    """Process transactions on prod otsa database.
    Do so using rules that no one understands anymore (defined in otsa_processing.py)."""
    incidents = get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '(129) OPTIPOS Mobile',
        '(129B) AKTYWACJA KLIENTA',
        'login OTSA'
    )
    incidents += get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '(129) OPTIPOS Mobile',
        '(129D) MIGRACJA KLIENTA',
        'otsa sprzedaż'
    )
    incidents += get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '(129) OPTIPOS Mobile',
        '(129E) SPRZEDAZ USLUG',
        'otsa sprzedaż'
    )

    msisdn_regex = re.compile(r'\d{3}[ -]?\d{3}[ -]?\d{3}')
    trans_num_regex = re.compile('[A-Z0-9]{5,}?/?[0-9]{4}/[0-9]+')
    for inc in incidents:
        resolution = ''
        lines = inc['notes']
        all_resolved = True
        for i, line in enumerate(lines):
            if 'Proszę podać numer MSISDN' in line or 'Numer telefonu klienta Orange / MSISDN' in line:
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
    """Use to change SIM status to 'r' so the card can be used again in sales.
    Logic implemented in sim_processing.py"""
    incidents = get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '(129) OPTIPOS Mobile',
        '(129M) UWOLNIENIE ZASOBOW',
        'otsa sprzedaż'
    )

    otsa = otsa_connection()
    sim_regex = re.compile(r'[0-9]{19,20}')
    for inc in incidents:
        sims = []
        for line in inc['notes']:
            sims.extend(sim_regex.findall(line))

        all_resolved, resolution = process_sims(sims, otsa, inc)

        if is_empty(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'

        if all_resolved and resolution != '':
            resolution = '\r\n'.join(list(set(resolution.split('\r\n')))).strip()
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution))
    otsa.close()


def problems_with_offer():
    """Handle incidents from the 'problems with offer' category.
    It is most likely deprecated and removal of the whole function should be considered."""
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
            expiration_date = parser.parse(expiration_date)
        else:
            continue
        now = datetime.now()
        if (offer_name.lower() == 'plan komórkowy' or offer_name.lower() == 'internet mobilny') \
                and (expiration_date - now).days > 120:
            resolution = 'Klient ma lojalkę do {0}. Zgodnie z konfiguracją marketingową oferta {1} ' \
                         'jest dostępna na 120 dni przed końcem lojalki, czyli klient tych wymagań nie spełnia. ' \
                         'Brak błędu aplikacji.'.format(expiration_date, offer_name)
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))


def unlock_accounts():
    """Reset the password and unlock the account, if the login can be found in the ticket."""
    incidents = []
    incidents += get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '(129) OPTIPOS Mobile',
        '(129O) OTSA/OPTIPOS - odblokowanie konta',
        'ota login odblokowanie'
    )
    incidents += get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '(129) OPTIPOS Mobile',
        '(129RF) DEALER SUPPORT - AKTYWACJA KONTA',
        'otsa login dealersupport DS.'
    )

    sd_tiers = ['(129RI) OKI i SOHO - AKTYWACJA KONTA', '(129RA) KKB,ADT - AKTYWACJA KONTA',
                '(129RK) ZŁD Aktywacja/Modyfikacja konta']
    for tier2 in sd_tiers:
        incidents += get_incidents(
            'VC3_BSS_OPTIPOS_MOBILE',
            '(129) OPTIPOS Mobile',
            tier2,
            'otsa login'
        )

    otsa = otsa_connection()

    for inc in incidents:
        login = find_login(inc)
        if login:
            rows_updated = unlock_account(otsa, login)
            if rows_updated == 1:
                resolution = 'Konto o loginie {} jest aktywne. Nowe hasło to: centertel.'.format(login)
                close_incident(inc, resolution)
                print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))

    otsa.close()


def find_login(inc):
    """Return account name to unlock, if it can be found."""
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
        work_info = get_work_info(inc)
        for entry in work_info:
            notes = ' '.join(entry['notes']).lower().replace(':', ' ').split()
            if 'sd' in entry['summary'].lower() and 'zdjęcie' in notes:
                for word in 'lub odbicie na sd'.split():
                    if word in notes:
                        notes.remove(word)
                login_keywords = ['konta', 'login', 'loginu']
                for keyword in login_keywords:
                    if keyword in notes:
                        login = notes[notes.index(keyword) + 1]
    return login


def close_pending_rsw():
    """Use to close old pending tickets where there was some issue with placing an order.
    If there is a renewal order for the contract and the order date is later than the ticket creation date,
    we close the ticket as resolved."""
    incidents = get_pending_incidents(['VC3_BSS_RSW'])
    msisdn_regex = re.compile(r'\d{3}[ -]?\d{3}[ -]?\d{3}')
    rsw = rsw_connection()
    for inc in incidents:
        resolution = ''
        lines = inc['notes']
        msisdns = None
        last_order = None
        for i, line in enumerate(lines):
            if 'Numer telefonu klienta Orange / MSISDN' in line and i < len(lines) - 1:
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
    """Add an offer to the list of available ones in case of a contract renewal."""
    incidents = []
    incidents += get_incidents(
        'VC3_BSS_RSW',
        '(357) RSW / nBUK',
        '(357B) PROBLEMY Z OFERTĄ I TERMINALAMI',
        'Orange Mobile, B2C, B2B, Love'
    )
    incidents += get_incidents(
        'VC3_BSS_RSW',
        '(129) OPTIPOS Mobile',
        '(129C) OFERTA UTRZYMANIOWA',
        'otsa utrzymanie'
    )

    rsw = rsw_connection()
    for inc in incidents:
        entitlement, msisdns, offer_name = extract_data_from_rsw_inc(inc)
        if msisdns and len(msisdns) != 1:
            continue
        elif msisdns:
            msisdn = msisdns[0]
        if msisdns and entitlement:
            offer_id = get_offer_id_by_name(rsw, offer_name)
            if offer_id:
                add_entitlement(rsw, msisdn, offer_id)
            else:
                add_entitlement(rsw, msisdn)
            resolution = 'Numer {} uprawniony.'.format(msisdn)
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))
    rsw.close()


def extract_data_from_rsw_inc(inc):
    """Try to return if the ticket is about entitlement, desired offer name, and the MSISDN number.
    This function is just a big fucking mess."""
    entitlement = False
    msisdns = None
    msisdn_regex = re.compile(r'\d{3}[ -]?\d{3}[ -]?\d{3}')
    lines = inc['notes']
    for i, line in enumerate(lines):
        if 'Nazwa oferty' in line:
            offer_name = lines[i + 1].lower().strip()
        if ('Numer telefonu klienta Orange / MSISDN' in line or
            'Proszę podać numer MSISDN oraz numer koszyka, z którym jest problem:' in line) \
                and i < len(lines) - 1:
            msisdns = msisdn_regex.findall(lines[i + 1])
        entitlement_keywords = ['uprawnienie', 'dodanie', 'podgranie', 'o migracj', 'podegranie', 'wgranie']
        for entitlement_keyword in entitlement_keywords:
            if entitlement_keyword in line.lower():
                entitlement = True
                break
        prepaid_keywords = ['prepaid', 'pripeid']
        for prepaid_keyword in prepaid_keywords:
            if prepaid_keyword in line.lower():
                offer_name = 'migracja na prepaid'
    if msisdns:
        msisdns = [msisdn.translate(''.maketrans({'-': '', ' ': ''})) for msisdn in msisdns]
    return entitlement, msisdns, offer_name


def empty_rsw_inc():
    """Close tickets with no content."""
    all_rsw_inc = get_all_incidents('VC3_BSS_RSW')
    for inc in all_rsw_inc:
        if is_empty(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))


if __name__ == '__main__':

    LOCK_FILE = 'lock'
    if os.path.exists(LOCK_FILE):
        print('Lock file exists. Remove it to run the program.')
        exit(37)
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
    except cx_Oracle.DatabaseError as db_exception:
        print('Database error: {}.\nCreating lock file and exiting...'.format(db_exception))
        open(LOCK_FILE, 'w+')
        exit(37)
    except paramiko.ssh_exception.AuthenticationException as ssh_exception:
        print('SSH error: {}.\nCreating lock file and exiting...'.format(ssh_exception))
        open(LOCK_FILE, 'w+')
        exit(37)
