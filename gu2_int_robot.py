#!/usr/bin/env python3
import os
import re
import sys
from time import sleep

from db.provik import get_latest_order, provik_connection, is_gbill_out_for_order, has_gpreprov, cancel_order, \
    has_pbi184471_error, is_geqret_processing, get_pgo_id, get_bpm_id, delete_process_timeout
from helper_functions import has_brm_error, get_tel_order_number, get_logs_for_order, resubmit_goal, \
    fine_flag_value_replace, update_cf_service, delete_cf_service, get_return_flag
from om_tp import get_order_info, get_process_errors, get_order_data, has_brm_process_error, is_ctx_session, \
    set_business_error
from om_tp_wzmuk_processing import get_users_data_from_xls, disable_user, new_ro_user
from otsa_processing import to_cancel
from remedy import get_all_incidents, get_work_info, has_exactly_one_entry, add_work_info, reassign_incident, \
    get_incidents, close_incident, is_work_info_empty, get_pending_incidents, assign_incident, update_summary


def handle_brm_errors():
    incidents = get_all_incidents('VC3_BSS_OM_TP')
    provik = provik_connection()

    for inc in incidents:
        work_info = get_work_info(inc)
        tel_order_number = get_tel_order_number(inc)
        order_info = get_order_info(tel_order_number)
        order_data = get_order_data(order_info)
        if 'OM zamowienie (ORD_ID)' in order_data:
            ord_id = order_data['OM zamowienie (ORD_ID)']

        if 'BRM3' in inc['summary']:
            if is_gbill_out_for_order(provik, ord_id):
                update_summary(inc, 'CRM')
                add_work_info(inc, 'OM_TP', 'Poprawione.')
                reassign_incident(inc, 'VC3_BSS_CRM_FIX')

        elif 'BRM2' in inc['summary']:
            if is_gbill_out_for_order(provik, ord_id):
                resolution = 'Zamówienie {} przekazane do realizacji.'.format(tel_order_number)
                close_incident(inc, resolution)

        elif 'BRM' in inc['summary'] or 'PK' in inc['summary']:
            promotion_regex = re.compile(r'pro[0-9]{14}')
            promotion_ids = []
            return_flag = get_return_flag(work_info)

            for entry in work_info[::-1]:
                notes = '\r\n'.join(entry['notes']).lower()
                summary = entry['summary'].lower()
                promotion_ids += promotion_regex.findall(notes)

                if 'crm' in summary and \
                        ('bez kary' in notes or 'bez naliczania kary' in notes or 'bez naliczenia kary' in notes):
                    if ord_id:
                        fine_flag_value_replace(ord_id, inc)
                        resubmit_successful = resubmit_goal(tel_order_number)
                        if resubmit_successful:
                            update_summary(inc, 'BRM3') if return_flag else update_summary(inc, 'BRM2')

                elif 'crm' in summary and ('promo' in notes or 'pro000' in notes) and \
                        ('bez' in notes or 'usunięcie' in notes or 'do usunięcia' in notes):
                    promotion_id = None
                    promotion_ids = list(set(promotion_ids))
                    if len(promotion_ids) == 1:
                        promotion_id = promotion_ids[0].upper()
                    if promotion_id:
                        update_cf_service(ord_id, promotion_id, inc)
                        resubmit_successful = resubmit_goal(tel_order_number)
                        if resubmit_successful:
                            update_summary(inc, 'BRM3') if return_flag else update_summary(inc, 'BRM2')

                elif 'crm' in summary and 'ins000' in notes and \
                        ('bez' in notes or 'usunięcie' in notes or 'do usunięcia' in notes):
                    ins_regex = re.compile(r'ins[0-9]{14}')
                    ins_ids = ins_regex.findall(notes)
                    ins_id = None
                    if len(ins_ids) == 1:
                        ins_id = ins_ids[0].upper()
                    if ins_id:
                        delete_cf_service(ord_id, ins_id, inc)
                        resubmit_successful = resubmit_goal(tel_order_number)
                        if resubmit_successful:
                            update_summary(inc, 'BRM3') if return_flag else update_summary(inc, 'BRM2')

        elif tel_order_number and (is_work_info_empty(work_info) or has_exactly_one_entry(work_info)):
            if to_cancel(inc) or 'pipi.sh error' in inc['summary']:
                continue
            process_errors = get_process_errors(order_info)
            if has_brm_process_error(process_errors) or has_brm_error(work_info):
                logs = get_logs_for_order(tel_order_number)
                logs_string = '\r\n'.join(logs)
                if len(logs) == 2:
                    update_summary(inc, 'BRM')
                    add_work_info(inc, 'OM_TP', logs_string)
                    reassign_incident(inc, 'APLIKACJE_OBRM_DOSTAWCA')
                    sleep(30)
                elif len(logs) == 1 and not is_gbill_out_for_order(provik, ord_id):
                    resubmit_successful = resubmit_goal(tel_order_number)
                    if resubmit_successful:
                        update_summary(inc, 'pipi.sh error')
                        print('{} Zamówienie {} ponowione w OM TP'.format(inc['inc'], tel_order_number),
                              file=sys.stderr)
                else:
                    process_errors = get_process_errors(get_order_info(tel_order_number))
                    error_id = ''
                    if process_errors and process_errors[0]:
                        error_id = process_errors[0][0]
                    print('{} {} {} {}'.format(inc['inc'], error_id, tel_order_number, logs_string), file=sys.stderr)

    provik.close()


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
    provik.close()


def om_tp_wzmuk():
    incidents = get_incidents(
        'VC3_BSS_OM_TP',
        '(185) E-WZMUK-konto w SI Nowe/Modyfikacja/Likwidacja',
        'O30 OMTP',
        '40h'
    )
    for inc in incidents:
        work_info = get_work_info(inc)
        filename, contents = work_info[0]['attachment']

        xls_file = open(filename, 'wb')
        xls_file.write(contents)
        xls_file.close()
        users = get_users_data_from_xls(filename)
        os.remove(filename)

        for user in users:
            if not user['login_ad']:
                continue

            if user['typ_wniosku'] == 'Nowe konto':
                if user['profil'] == 'konsola zamówień OM (odczyt)':
                    password = new_ro_user(user['login_ad'])
                    close_incident(inc, f'Konto założone, hasło to: {password}')
                else:
                    pass
            elif user['typ_wniosku'] == 'Modyfikacja uprawnień':
                pass
            elif user['typ_wniosku'] == 'Likwidacja konta':
                disable_user(user['login_ad'])
                close_incident(inc, 'Konto wyłączone.')


def cancel_om_orders():
    incidents = get_all_incidents('VC3_BSS_OM_TP')
    provik = provik_connection()
    for inc in incidents:
        work_info = get_work_info(inc)
        tel_order_number = get_tel_order_number(inc)
        order_info = get_order_info(tel_order_number)
        order_data = get_order_data(order_info)
        if 'OM zamowienie (ORD_ID)' in order_data:
            ord_id = order_data['OM zamowienie (ORD_ID)']

        if is_ctx_session(ord_id):
            continue

        for entry in work_info:
            notes = '\r\n'.join(entry['notes']).lower()
            summary = entry['summary'].lower()
            if 'crm' in summary and \
                    ('anulowanie z bazy' in notes or 'do anulowania z bazy' in notes) \
                    and not has_gpreprov(provik, ord_id):

                if is_geqret_processing(provik, ord_id):
                    pgo_ids = get_pgo_id(provik, ord_id, 'GEQRET')
                    for pgo_id in pgo_ids:
                        set_business_error(pgo_id)
                        bpm_id = get_bpm_id(provik, pgo_id)
                        delete_process_timeout(provik, bpm_id)

                pgo_id = get_pgo_id(provik, ord_id, 'GBILL')
                set_business_error(pgo_id)
                cancel_order(provik, ord_id)
                add_work_info(inc, 'OM_TP', 'Zamówienie anulowane.')
                reassign_incident(inc, 'VC3_BSS_CRM_FIX')
    provik.close()


def pbi184471():
    wi_notes = 'Błędna sekcja documents, brak określenia pola TYPE dla jednego z dokumentów. PBI000000184471'
    incidents = []
    incidents += get_incidents('VC3_BSS_OM_TP', '(001) CRM Fix')
    incidents += get_incidents('VC3_BSS_OM_TP', '(039) Obieg zleceń CRM-KSP')
    provik = provik_connection()
    for inc in incidents:
        work_info = get_work_info(inc)
        tel_order_number = get_tel_order_number(inc)
        if (is_work_info_empty(work_info) or has_exactly_one_entry(work_info))\
                and has_pbi184471_error(provik, tel_order_number):
            add_work_info(inc, 'OM_TP', wi_notes)
            reassign_incident(inc, 'APLIKACJE_DEVOPS_HYBRIS')
    provik.close()


if __name__ == '__main__':
    cancel_om_orders()
    om_tp_wzmuk()
    handle_brm_errors()
    close_pending_om_tp()
    pbi184471()
