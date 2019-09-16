#!/usr/bin/env python3
from helper_functions import has_brm_error, get_tel_order_number, get_logs_for_order
from remedy import get_all_incidents, get_work_info, has_exactly_one_entry, add_work_info, reassign_incident


def handle_brm_errors():
    incidents = get_all_incidents('VC3_BSS_OM_TP')
    for inc in incidents:
        work_info = get_work_info(inc)
        if has_exactly_one_entry(work_info) and has_brm_error(work_info):
            tel_order_number = get_tel_order_number(inc)
            if tel_order_number:
                logs = get_logs_for_order(tel_order_number)
                if logs:
                    add_work_info(inc, 'VC_OM', logs)
                    reassign_incident(inc, 'APLIKACJE_OBRM_DOSTAWCA')


if __name__ == '__main__':
    handle_brm_errors()
