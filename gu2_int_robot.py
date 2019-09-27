#!/usr/bin/env python3
import sys
from time import sleep

from helper_functions import has_brm_error, get_tel_order_number, get_logs_for_order
from om_tp import get_order_info, get_process_errors
from remedy import get_all_incidents, get_work_info, has_exactly_one_entry, add_work_info, reassign_incident


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
                else:
                    process_errors = get_process_errors(get_order_info(tel_order_number))
                    error_id = ''
                    if process_errors and process_errors[0]:
                        error_id = process_errors[0][0]
                    print('{} {} {} {}'.format(inc['inc'], error_id, tel_order_number, logs_string), file=sys.stderr)


if __name__ == '__main__':
    handle_brm_errors()
