# -*- coding: utf-8 -*-
from bscs import get_customer_id, bscs_connection, set_trans_no
from om import get_orders
from optipos import get_cart_status, opti_connection, set_cart_status
from otsa import search_msisdn, update_transaction, update_contract, fix_90100, fix_csc185, search_cart, \
    otsa_connection, fix_pesel, fix_csc178, fix_aac, fix_csc598
from remedy import reassign_incident, update_summary


def process_msisdns(msisdns, inc):
    otsa = otsa_connection()
    resolution = ''
    all_resolved = True
    for msisdn in msisdns:
        contracts = search_msisdn(otsa, msisdn)
        for contract in contracts:
            print contract
        contracts = [contract for contract in contracts
                     if (contract['status'] not in ['9', '3D', '3G']
                         or (contract['status'] == '3A' and contract['trans_type'] not in ['MNP1', 'PRPS']))]
        for contract in contracts:
            if contract['status'] == '2Y':
                partial_resolution = process_2y(otsa, contract, inc)
            elif contract['status'] == '2B':
                partial_resolution = process_2b(otsa, contract, inc)
            elif contract['status'] == '3C':
                partial_resolution = process_3c(otsa, contract, inc)
            elif contract['status'] == '1F':
                partial_resolution = process_1f(otsa, contract, inc)
            elif contract['status'] == '1H':
                partial_resolution = process_1h(otsa, contract, inc)
            elif contract['status'] == '3A':
                partial_resolution = process_3a(otsa, contract, inc)
            elif contract['status'] == '1C':
                partial_resolution = process_1c(otsa, contract, inc)
            elif contract['status'] == '8B':
                partial_resolution = process_8b(otsa, contract, inc)
            elif contract['status'] == '1D':
                partial_resolution = process_1d(otsa, contract, inc)
            else:
                partial_resolution = ''

            if partial_resolution == '':
                all_resolved = False

            resolution = resolution + partial_resolution + '\n'

    otsa.close()
    return resolution, all_resolved


def to_cancel(inc):
    for line in inc['notes']:
        line = line.lower()
        if 'o anulowa' in line or 'proszę anulować' in line:
            return True
    return False


def process_2y(otsa, contract, inc):
    resolution = ''

    if to_cancel(inc):
        update_transaction(otsa, contract['trans_code'], '3D')
        update_contract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'
        return resolution

    for line in inc['notes']:
        line = line.lower()
        if 'wstrzym' in line and 'po stronie om' in line:
            resolution = 'Umowa ' + contract['trans_num'] + \
                         ' wstrzymana po stronie OM. Jest to poprawny biznesowo status. ' \
                         'Proszę anulować lub zatwierdzić. W razie kłopotów proszę o kontakt z Dealer Support'
            return resolution

    if 'ponowione' in inc['summary']:
        resolution = 'Umowa ' + contract['trans_num'] + ' wstrzymana po stronie OM. ' \
                     'Jest to poprawny biznesowo status. Proszę anulować lub zatwierdzić. ' \
                     'W razie kłopotów proszę o kontakt z Dealer Support'
        return resolution

    orders = get_orders(contract['msisdn'])
    for order in orders:
        if order['status'] == 'HALTED' and order['id'] == contract['om_order_id']:
            update_transaction(otsa, contract['trans_code'], '1B')
            resolution = 'Umowa ' + contract['trans_num'] + ' przekazana do realizacji.'
        elif order['status'] == 'COMPLETED' and order['id'] == contract['om_order_id']:
            update_transaction(otsa, contract['trans_code'], '3A')
            update_contract(otsa, contract['trans_code'], '3A')
            resolution = 'Umowa ' + contract['trans_num'] + ' zrealizowana.'
        elif order['status'] == 'CANCELLED' and order['id'] == contract['om_order_id']:
            update_transaction(otsa, contract['trans_code'], '3D')
            update_contract(otsa, contract['trans_code'], '3D')
            resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'
        else:
            resolution = ''

    return resolution


def process_2b(otsa, contract, inc):
    if 'ponowione' in inc['summary']:
        resolution = 'Umowa ' + contract['trans_num'] + ' przekazana do realizacji.'
    else:
        reassign_incident(inc, 'OM')
        resolution = ''
    return resolution


def process_3c(otsa, contract, inc):
    if contract['process_error'] == 103199:
        resolution = 'Tak wygląda proces sprzedażowy dla Magnumów. Jeśli nie było logistyki (w OM lub w kanale), ' \
                     'to zlecenie MV musi być zawieszone w OM (HALTED) i dopiero wtedy można złożyć zlecenie DATA.'
    elif contract['process_error'] == 90100:
        if 'BSCS (47 - blad wewnetrzny systemu)' in contract['ncs_error_desc']:
            bscs = bscs_connection()
            set_trans_no(bscs, contract['custcode'], -1)
            bscs.close()
        else:
            transactions = search_cart(otsa, contract['cart_code'])
            for t in transactions:
                fix_90100(otsa, t['trans_code'])
        resolution = ''
    elif contract['process_error'] == 21220:
        update_transaction(otsa, contract['trans_code'], '1C')
        resolution = 'Dokument został już zarejestrowany w CRM. Umowa w statusie do poprawienia. ' \
                     'W razie wątpliwości proszę o kontakt z Dealer Support.'
        return resolution
    elif contract['ncs_error_desc'] is not None and 'CSC.185' in contract['ncs_error_desc']:
        fix_csc185(otsa, contract['cart_code'])
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'CSC.178' in contract['ncs_error_desc']:
        fix_csc178(otsa, contract['cart_code'])
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'CSC.598' in contract['ncs_error_desc']:
        fix_csc598(otsa, contract['trans_code'])
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'EDL.33' in contract['ncs_error_desc']:
        update_transaction(otsa, contract['trans_code'], '3A')
        update_contract(otsa, contract['trans_code'], '3A')
        resolution = 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.\n'
        return resolution
    elif contract['ncs_error_desc'] is not None and 'ACCOUNT ALREADY CREATED' in contract['ncs_error_desc']:
        bscs = bscs_connection()
        customer_id = get_customer_id(bscs, contract['custcode'])
        bscs.close()
        fix_aac(otsa, contract['trans_code'], customer_id)
        resolution = ''
    elif contract['process_error'] == 102860:
        update_transaction(otsa, contract['trans_code'], '1C')
        resolution = contract['ncs_error_desc'] + '\nUmowa w statusie do poprawy. ' \
                                                  'W razie wątpliwości proszę o kontakt z Dealer Support.'
        return resolution
    elif contract['ncs_error_desc'] is not None and 'na zleceniu nie odpowiada' in contract['ncs_error_desc']:
        reassign_incident(inc, 'OV')
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'Voucher' in contract['ncs_error_desc']:
        reassign_incident(inc, 'OV')
        resolution = ''
    else:
        resolution = ''
    update_transaction(otsa, contract['trans_code'], '1B')
    update_summary(inc, 'ponowione')
    return resolution


def process_1f(otsa, contract, inc):
    resolution = ''
    if contract['cart_code'] != '':
        cart = search_cart(otsa, contract['cart_code'])
        has_ca = False
        ca = None
        for trans in cart:
            if trans['trans_type'] == 'CA':
                has_ca = True
                ca = trans
        if has_ca:
            if ca['status'] == '3A':
                resolution = ''
                for trans in [t for t in cart if t['trans_type'] != 'CA']:
                    if trans['status'] in ('1F', '3C'):
                        resolution += process_3c(otsa, trans, inc)
            else:
                pass  # TODO
        else:
            resolution = process_3c(otsa, contract, inc)
    else:
        resolution = process_3c(otsa, contract, inc)
    return resolution


def process_1h(otsa, contract, inc):
    if contract['cart_code'] != '':
        resolution = ''
        cart = search_cart(otsa, contract['cart_code'])
        for trans in cart:
            if 'ponowione' in inc['summary'] and trans['process_error'] is None:
                fix_pesel(otsa, trans['trans_code'])
            if trans['trans_type'] == 'CA' and trans['status'] == '3C':
                resolution = process_3c(otsa, trans, inc)
                update_summary(inc, 'ponowione')
    else:
        resolution = process_3c(otsa, contract, inc)
    return resolution


def process_3a(otsa, contract, inc):
    resolution = ''
    if contract['status'] == '3A' and \
            ('ponowione' in inc['summary'] or (contract['ncs_error_desc'] is not None
                                               and 'Timeout' in contract['ncs_error_desc'])) \
            and contract['trans_num'] is not None:
        resolution += 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.\n'
        return resolution
    for line in inc['notes']:
        line = line.lower()
        if 'wstrzym' in line and 'po stronie om' in line:
            resolution += 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.\n'
            return resolution
        if 'koszyk' in line and 'oraz numer koszyka' not in line:
            opti = opti_connection()
            if contract['cart_code'] is not None:
                cart_status = get_cart_status(opti, contract['cart_code'])
                if cart_status not in ['3A', '3D']:
                    set_cart_status(opti, contract['cart_code'], '3A')
                    resolution += 'Koszyk {} zamknięty.\n'.format(contract['cart_code'])
                    opti.close()
                    return resolution
    else:
        resolution = ''
    return resolution


def process_1c(otsa, contract, inc):
    if to_cancel(inc):
        update_transaction(otsa, contract['trans_code'], '3D')
        update_contract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'
    else:
        resolution = ''

    return resolution


def process_8b(otsa, contract, inc):
    return process_1c(otsa, contract, inc)


def process_1d(otsa, contract, inc):
    resolution = ''

    if not to_cancel(inc):
        update_transaction(otsa, contract['trans_code'], '1B')
        update_summary(inc, 'ponowione')
    else:
        update_transaction(otsa, contract['trans_code'], '3D')
        update_contract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'

    return resolution
