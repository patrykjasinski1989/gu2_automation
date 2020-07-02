#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from time import sleep

from db.provik import get_latest_order, provik_connection
from helper_functions import has_brm_error, get_tel_order_number, get_logs_for_order, resubmit_goal
from ml_wzmuk_processing import get_users_data_from_xls
from om_tp import get_order_info, get_process_errors, get_order_data, has_brm_process_error
from remedy import get_all_incidents, get_work_info, has_exactly_one_entry, add_work_info, reassign_incident, \
    get_incidents, close_incident, is_work_info_empty, get_pending_incidents, assign_incident


def handle_brm_errors():
    incidents = get_all_incidents('VC3_BSS_OM_TP')
    for inc in incidents:
        work_info = get_work_info(inc)
        tel_order_number = get_tel_order_number(inc)
        if tel_order_number and (is_work_info_empty(work_info) or has_exactly_one_entry(work_info)):
            process_errors = get_process_errors(get_order_info(tel_order_number))
            if has_brm_process_error(process_errors) or has_brm_error(work_info):
                logs = get_logs_for_order(tel_order_number)
                logs_string = '\r\n'.join(logs)
                if len(logs) == 2:
                    add_work_info(inc, 'VC_OM', logs_string)
                    reassign_incident(inc, 'APLIKACJE_OBRM_DOSTAWCA')
                    sleep(30)
                elif len(logs) == 1:
                    resubmit_goal(tel_order_number)
                    print('{} Zamówienie {} ponowione w OM TP'.format(inc['inc'], tel_order_number), file=sys.stderr)
                else:
                    process_errors = get_process_errors(get_order_info(tel_order_number))
                    error_id = ''
                    if process_errors and process_errors[0]:
                        error_id = process_errors[0][0]
                    print('{} {} {} {}'.format(inc['inc'], error_id, tel_order_number, logs_string), file=sys.stderr)


def close_pending_om_tp():
    incidents = get_pending_incidents(['VC3_BSS_OM_TP'])
    provik = provik_connection()
    for inc in incidents:
        resolution = ''
        tel_order_number = get_tel_order_number(inc)
        if tel_order_number:
            order_data = get_order_data(get_order_info(tel_order_number))
            if 'Stan procesu' in order_data and order_data['Stan procesu'] == 'COMPLETED':
                resolution = 'Zamówienie {} skompletowane.'.format(tel_order_number)
            elif 'Stan procesu' not in order_data:
                latest_order = get_latest_order(provik, tel_order_number)
                if latest_order and latest_order['ord_state'] == 'COMPLETED':
                    resolution = 'Zamówienie {} skompletowane.'.format(tel_order_number)
        if resolution:
            assign_incident(inc)
            close_incident(inc, resolution)
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))
    provik.close()


def om_tp_wzmuk():
    incidents = get_incidents(
        'VC3_BSS_OM_TP',
        '',
        '',
        ''  # TODO uzupelnic nazwy kategorii
    )
    for inc in incidents:
        work_info = get_work_info(inc)
        filename, contents = work_info[0]['attachment']

        xls_file = open(filename, 'wb')
        xls_file.write(contents)
        xls_file.close()
        users = get_users_data_from_xls(filename)  # TODO mozliwe ze bedzie potrzebna lekka modyfikacja tej funkcji
        os.remove(filename)

        resolution = ''
        for user in users:
            if user['typ_wniosku'] == 'Nowe konto':
                resolution = None  # TODO napisac funkcje do zakladania kont (skrypt na 126.185.9.192)

        if resolution:
            close_incident(inc, resolution.strip())
            print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))


if __name__ == '__main__':
    close_pending_om_tp()
    handle_brm_errors()
