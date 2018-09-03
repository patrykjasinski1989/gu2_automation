# -*- coding: utf-8 -*-
import os
import re

import cx_Oracle
from datetime import datetime
from dateutil import parser

from eai import get_expiration_date, get_contract_data
from muchomor import unlock_imei
from nra import get_sim_status, nra_connection, set_sim_status_nra, set_sim_status_bscs, set_imsi_status_bscs
from otsa import otsa_connection, check_sim, unlock_account
from otsa_processing import process_msisdns
from remedy import get_incidents, close_incident, is_empty, get_work_info, add_work_info, reassign_incident, \
    update_summary, get_pending_incidents, assign_incident
from rsw import rsw_connection, get_latest_order


def unlock_imeis():
    incidents = get_incidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'ODBLOKOWANIE IMEI'
    )

    imei_regex = re.compile('[a-zA-Z0-9]{9,15}')
    imeis = []

    for inc in incidents:
        lines = inc['notes']
        for i in range(len(lines)):
            if 'IMEI:' in lines[i]:
                imeis = imei_regex.findall(lines[i + 1])
                break
        resolution = ''
        if len(imeis) > 0:
            for imei in imeis:
                resolution += unlock_imei(imei.upper()) + '\n'
        if is_empty(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
        if resolution.strip() != '':
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))


def process_transactions():
    incidents = get_incidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'AKTYWACJA KLIENTA'
    )
    incidents += get_incidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'MIGRACJA KLIENTA'
    )
    incidents += get_incidents(
        'VC_BSS_MOBILE_OPTIPOS',
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
                msisdns = msisdn_regex.findall(lines[i+1])
                msisdns += msisdn_regex.findall(lines[i+2])
                msisdns = [msisdn.translate(''.maketrans({'-': '', ' ': ''})) for msisdn in msisdns]
                trans_nums = trans_num_regex.findall(lines[i + 1])
                resolution, all_resolved = process_msisdns(msisdns, trans_nums, inc)
        if is_empty(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
        if resolution != '' and all_resolved:
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))


def release_resources():
    incidents = get_incidents(
        'VC_BSS_MOBILE_OPTIPOS',
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
                partial_resolution = 'Karta SIM {0} powiązana z nieanulowaną umową {1}. Brak możliwości odblokowania.' \
                                     'Proszę o kontakt z dealer support lub z działem reklamacji' \
                    .format(sim, result[0]['trans_num'])
            if partial_resolution != '':
                resolution = resolution + '\r\n' + partial_resolution
        nra.close()

        if is_empty(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'

        if all_resolved and resolution != '':
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))
    otsa.close()


def problems_with_offer():
    incidents = get_incidents(
        'VC_BSS_MOBILE_RSW',
        '000_incydent/awaria/uszkodzenie',
        'RSW / nBUK',
        'PROBLEMY Z OFERTĄ I TERMINALAMI'
    )
    for inc in incidents:
        resolution = ''

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
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OTSA/OPTIPOS',
        'ODBLOKOWANIE KONTA'
    )
    sd_tiers = ['OKI i SOHO - AKTYWACJA KONTA', '[DETAL PTK] KKB,ADT - AKTYWACJA KONTA',
                '[DETAL TP] DEALER SUPPORT - AKTYWACJA KONTA']
    for tier3 in sd_tiers:
        incidents += get_incidents(
            'VC_BSS_MOBILE_OPTIPOS',
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
                notes = ' '.join(entry['notes']).lower().split()
                if 'SD' in entry['summary'] and 'zdjęcie' in notes:
                    for word in 'lub odbicie na sd'.split():
                        if word in notes:
                            notes.remove(word)
                    if 'konta' in notes:
                        login = notes[notes.index('konta') + 1]
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
    incidents = get_pending_incidents(['VC_BSS_MOBILE_RSW'])
    msisdn_regex = re.compile('\d{3}[ -]?\d{3}[ -]?\d{3}')
    rsw = rsw_connection()
    for inc in incidents:
        resolution = ''
        lines = inc['notes']
        for i in range(len(lines)):
            if 'Numer telefonu klienta Orange / MSISDN' in lines[i] and i < len(lines) - 1:
                msisdns = msisdn_regex.findall(lines[i+1])
        msisdns = [msisdn.translate(''.maketrans({'-': '', ' ': ''})) for msisdn in msisdns]
        if len(msisdns) != 1:
            continue
        else:
            msisdn = msisdns[0]
        last_order = get_latest_order(rsw, msisdn)
        if last_order and last_order['data_zamowienia'] > inc['reported_date'] and last_order['ilosc_prob'] == 0:
            if last_order['status'] == 16 and last_order['status_om'] == 4:
                resolution = 'Na podanym numerze {} jest już zrealizowane zamówienie {} z {}.'.\
                    format(msisdn, last_order['id_zamowienia'], last_order['data_zamowienia'])
            elif last_order['status'] in (2, 3):
                resolution = 'Na podanym numerze {} jest już zamówienie {} w trakcie realizacji w ML.'.\
                    format(msisdn, last_order['id_zamowienia'])
        if resolution:
            assign_incident(inc)
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))

    rsw.close()


def revert_inc_status():
    incidents = get_incidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'AKTYWACJA KLIENTA'
    )
    incidents += get_incidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'MIGRACJA KLIENTA'
    )
    incidents += get_incidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'SPRZEDAZ USLUG'
    )

    for inc in incidents:
        if 'ponowione3' in inc['summary']:
            update_summary(inc, 'ponowione2')


if __name__ == '__main__':

    lock_file = 'lock'
    if os.path.exists(lock_file):
        print('Lock file exists. Remove it to run the program.')
        exit(666)
    try:
        unlock_imeis()
        unlock_accounts()
        process_transactions()
        release_resources()
        problems_with_offer()
        close_pending_rsw()
    except cx_Oracle.DatabaseError as e:
        print('Database error: {}.\nCreating lock file and exiting...'.format(e))
        open(lock_file, 'w+')
        exit(666)
