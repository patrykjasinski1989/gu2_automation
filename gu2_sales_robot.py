#!/usr/env/bin python3
"""This is the script used to close the tickets. GU2 Sales Incidents for OPL to be exact.
Should be broken into smaller parts..."""
import config
from db.optipos_ptk import optipos_sti_connection, link_login_with_ifs
from ml_wzmuk_processing import ml_wzmuk_sti, ml_wzmuk_prod

__author__ = "Patryk Jasiński <pjasinski@bluesoft.com>"

import os
import re
from datetime import datetime

import cx_Oracle
import paramiko

from db.otsa import otsa_connection, unlock_account
from db.rsw import rsw_connection, get_latest_order, make_offer_available, get_offer_id_by_name
from helper_functions import process_sims, find_login, extract_data_from_rsw_inc
from otsa_processing import process_msisdns
from remedy import get_incidents, close_incident, is_empty, \
    get_pending_incidents, assign_incident, get_all_incidents, get_work_info, has_exactly_one_entry, add_work_info, \
    reassign_incident


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
    Logic implemented in helper_functions.py"""
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

    incidents += get_incidents(
        'VC3_BSS_OPTIPOS_MOBILE',
        '(129) OPTIPOS Mobile',
        '(129I) PROBLEM Z LOGOWANIEM',
        'login OTSA'
    )

    sd_tiers = ['(129RI) OKI i SOHO - AKTYWACJA KONTA', '(129RA) KKB,ADT - AKTYWACJA KONTA',
                '(129RK) ZŁD Aktywacja/Modyfikacja konta', '(129RH) OKB i TAM - AKTYWACJA KONTA']
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


def offer_availability():
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
        availability_inc, msisdns, offer_name = extract_data_from_rsw_inc(inc)
        if msisdns and len(msisdns) != 1:
            continue
        elif msisdns:
            msisdn = msisdns[0]
        if msisdns and availability_inc:
            offer_id = get_offer_id_by_name(rsw, offer_name)
            if offer_id:
                make_offer_available(rsw, msisdn, offer_id)
            else:
                make_offer_available(rsw, msisdn)
            resolution = 'Numer {} uprawniony.'.format(msisdn)
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))
    rsw.close()


def empty_inc():
    """Close tickets with no content."""
    all_inc = []
    all_inc += get_all_incidents('VC3_BSS_RSW')
    all_inc += get_all_incidents('VC3_BSS_OPTIPOS_MOBILE')
    for inc in all_inc:
        if is_empty(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))


def optipos_tp_errors():
    pesel_or_nip_regex = re.compile(r'\d{10,11}')
    incidents = get_all_incidents('VC3_BSS_OPTIPOS_FIX')
    for inc in incidents:
        if not has_exactly_one_entry(get_work_info(inc)):
            continue

        lines = inc['notes']
        pesel_or_nip_string = ''
        for i, line in enumerate(lines):
            if 'Proszę podać numer PESEL lub NIP klienta:' in line:
                pesel_or_nip_regex_search_result = pesel_or_nip_regex.findall(lines[i + 1])
                if not pesel_or_nip_regex_search_result:
                    continue
                pesel_or_nip_string = pesel_or_nip_regex_search_result[0].strip()
        if not pesel_or_nip_string:
            continue

        get_session_data_cmd = """ 
            ssh hooter "find /nas/logs/optineo -maxdepth 1 -name 'optineo_*.log*' -mtime -7 | 
            xargs grep {} | cut -d' ' -f1,2,4 | sed 's/:/\ /' | sort -k2 | tail -1" """.format(pesel_or_nip_string)
        get_logs_cmd = 'ssh hooter "fgrep {} {} | grep xml | tail -2"'

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(config.OPTPOS_LOGS['server'], username=config.OPTPOS_LOGS['user'],
                           password=config.OPTPOS_LOGS['password'], allow_agent=False)
        _, ssh_stdout, _ = ssh_client.exec_command(get_session_data_cmd.format(pesel_or_nip_string))
        session_data = ssh_stdout.readlines()
        if not session_data:
            continue

        session_data = session_data[0].strip().split(' ')
        file, session = session_data[0], session_data[3]
        _, ssh_stdout, _ = ssh_client.exec_command(get_logs_cmd.format(session, file))
        logs = ssh_stdout.readlines()

        input_, output = logs[0], logs[1]
        if 'INVALID' in output or 'PSCRM' in output:
            wi_notes = 'Prośba o weryfikację:\r\n\r\n{}\r\n{}\r\n'.format(input_, output)
            add_work_info(inc, 'VC_OPTIPOS', wi_notes)
            reassign_incident(inc, 'VC3_BSS_OV_TP')


def tester_accounts():
    incidents = get_incidents('VC3_BSS_OPTIPOS_MOBILE', '(129) OPTIPOS Mobile',
                              '(129S) TESTER - POWIĄZANIE IFS', 'otsa sprzedaż')
    optipot3 = optipos_sti_connection()
    for inc in incidents:
        login = None
        lines = inc['notes']
        for i, line in enumerate(lines):
            if 'Podaj login testera' in line:
                login = lines[i + 1].strip()
        if login:
            row_count = link_login_with_ifs(optipot3, login)
            if row_count == 1:
                resolution = 'Powiązano konto {} z IFS.'.format(login)
                close_incident(inc, resolution)
                print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))
    optipot3.close()


if __name__ == '__main__':

    LOCK_FILE = 'lock'
    if os.path.exists(LOCK_FILE):
        print('Lock file exists. Remove it to run the program.')
        exit(37)

    try:
        unlock_accounts()
        process_transactions()
        release_resources()
        close_pending_rsw()
        offer_availability()
        empty_inc()
        ml_wzmuk_sti()
        ml_wzmuk_prod()
        optipos_tp_errors()
        tester_accounts()

    except cx_Oracle.DatabaseError as db_exception:
        print('Database error: {}: {}.\nCreating lock file and exiting...'.
              format(db_exception.db_name.lower(), db_exception))
        open(LOCK_FILE, 'w+')
        exit(37)

    except paramiko.ssh_exception.AuthenticationException as ssh_exception:
        print('SSH error: {}.\nCreating lock file and exiting...'.format(ssh_exception))
        open(LOCK_FILE, 'w+')
        exit(37)
