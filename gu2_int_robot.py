#!/usr/bin/env python3
import sys

from helper_functions import has_brm_error, get_tel_order_number, get_logs_for_order
from om_tp import get_order_data, get_order_info
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
                else:
                    order_data = get_order_data(get_order_info(tel_order_number))
                    ord_id = order_data['OM zamowienie (ORD_ID)']
                    print('{} {} {} {}'.format(inc['inc'], ord_id, tel_order_number, logs_string), file=sys.stderr)


if __name__ == '__main__':
    handle_brm_errors()
