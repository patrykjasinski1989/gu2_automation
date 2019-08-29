"""This module contains various helper functions."""
import re

from db.nra import nra_connection, get_sim_status, set_sim_status_nra, set_sim_status_bscs, set_imsi_status_bscs
from db.otsa import check_sim
from remedy import add_work_info, reassign_incident, get_work_info


def process_sims(sims, otsa, inc):
    """This function changes SIM card statuses, if allowed and necessary.
    If the status is 'd', 'l', or 'E', then we change it to 'r' and close the ticket.
    If it's 'a' or 'B' or there is an open transaction with this card, we don't change the status.
    All other cases (less than 1%) must be handled manually."""
    all_resolved = True
    resolution = ''

    nra = nra_connection()
    for sim in sims:
        partial_resolution = ''
        result = check_sim(otsa, sim)
        result = [r for r in result if r['status'] not in ('3D', '3G')]
        if not result:
            wi_notes = ''
            sim_status = get_sim_status(nra, sim)
            if not sim_status:
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
            partial_resolution = 'Karta SIM {0} powiązana z nieanulowaną umową {1}. ' \
                                 'Brak możliwości odblokowania. ' \
                                 'Proszę o kontakt z dealer support lub z działem reklamacji.' \
                .format(sim, result[0]['trans_num'])
        if partial_resolution != '':
            resolution = resolution + '\r\n' + partial_resolution
    nra.close()

    return all_resolved, resolution


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


def extract_data_from_rsw_inc(inc):
    """Try to return if the ticket is about offer_availability, desired offer name, and the MSISDN number.
    This function is just a big fucking mess."""
    offer_availability_ = False
    msisdns = None
    msisdn_regex = re.compile(r'\d{3}[ -]?\d{3}[ -]?\d{3}')
    lines = inc['notes']
    for i, line in enumerate(lines):
        if 'Nazwa oferty' in line:
            offer_name = lines[i + 1].lower().strip()
        if ('Numer telefonu klienta Orange / MSISDN' in line or
            'Proszę podać numer MSISDN oraz numer koszyka, z którym jest problem:' in line) and i < len(lines) - 1:
            msisdns = msisdn_regex.findall(lines[i + 1])
        entitlement_keywords = ['uprawnienie', 'dodanie', 'podgranie', 'o migracj', 'podegranie', 'wgranie']
        for entitlement_keyword in entitlement_keywords:
            if entitlement_keyword in line.lower():
                offer_availability_ = True
                break
        prepaid_keywords = ['prepaid', 'pripeid']
        for prepaid_keyword in prepaid_keywords:
            if prepaid_keyword in line.lower():
                offer_name = 'migracja na prepaid'
    if msisdns:
        msisdns = [msisdn.translate(''.maketrans({'-': '', ' ': ''})) for msisdn in msisdns]
    return offer_availability_, msisdns, offer_name
