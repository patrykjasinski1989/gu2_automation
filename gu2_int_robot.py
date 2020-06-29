#!/usr/bin/env python3
import os
import re
import sys
from datetime import datetime
from time import sleep

from helper_functions import has_brm_error, get_tel_order_number, get_logs_for_order, resubmit_goal
from ml_wzmuk_processing import get_users_data_from_xls
from om_tp import get_order_info, get_process_errors, get_order_data
from remedy import get_all_incidents, get_work_info, has_exactly_one_entry, add_work_info, reassign_incident, \
    get_incidents, close_incident


def handle_brm_errors():
    incidents = get_all_incidents('VC3_BSS_OM_TP')
    for inc in incidents:
        work_info = get_work_info(inc)
        if has_exactly_one_entry(work_info) and has_brm_error(work_info):
            tel_order_number = get_tel_order_number(inc)
            if tel_order_number:
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
    handle_brm_errors()
