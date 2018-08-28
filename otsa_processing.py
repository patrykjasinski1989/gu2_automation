# -*- coding: utf-8 -*-
import paramiko as paramiko

import config
from bscs import get_customer_id, bscs_connection, set_trans_no
from om import get_orders
from optipos import get_cart_status, opti_connection, set_cart_status
from otsa import search_msisdn, update_transaction, update_contract, fix_90100, fix_csc185, search_cart, \
    otsa_connection, fix_pesel, fix_csc178, fix_aac, fix_csc598, fix_csc598_cart, get_magnum_offers, \
    get_promotion_codes, search_trans_num
from remedy import reassign_incident, update_summary, add_work_info


def process_msisdns(msisdns, trans_nums, inc):
    otsa = otsa_connection()
    resolution = ''
    work_info = ''
    all_resolved = True
    for id in (msisdns + trans_nums):
        contracts = search_msisdn(otsa, id)
        contracts += search_trans_num(otsa, id)
        contracts = [contract for contract in contracts
                     if (contract['status'] not in ['9', '3D', '3G']
                         and contract['trans_type'] not in ['MNP1', 'PRPS', 'PPRPS'])]
        for contract in contracts:
            partial_wi = ''
            if contract['status'] == '2Y':
                partial_resolution = process_2y(otsa, contract, inc)
            elif contract['status'] == '2B':
                partial_resolution, partial_wi = process_2b(otsa, contract, inc)
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
            work_info = work_info + partial_wi + '\n'

    if work_info.strip():
        add_work_info(inc, 'VC_OPTIPOS', work_info)

    otsa.close()
    return resolution, all_resolved


def to_cancel(inc):
    for line in inc['notes']:
        line = line.lower()
        if 'proszę o anul' in line or 'proszę anulować' in line or 'prosze o anulo' in line or 'prośba o anul' in line \
                or 'anulowanie umowy' in line:
            return True
    return False


def to_process(inc):
    for line in inc['notes']:
        line = line.lower()
        if 'proszę zatw' in line or 'proszę o zatw' in line \
                or 'proszę przeproces' in line or 'proszę o przeproces' in line:
            return True
    return False


def is_magnum(otsa, contract):
    magnum_offers = get_magnum_offers(otsa)
    pc = get_promotion_codes(otsa, contract['trans_code'])
    for code in pc:
        if code in magnum_offers:
            return True
    return False


def update_processing_status(inc):
    if 'ponowione' not in inc['summary']:
        update_summary(inc, 'ponowione')
    elif 'ponowione2' not in inc['summary']:
        update_summary(inc, 'ponowione2')
    else:
        update_summary(inc, 'ponowione3')


def process_2y(otsa, contract, inc):
    resolution = ''

    if to_cancel(inc):
        update_transaction(otsa, contract['trans_code'], '3D')
        update_contract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'
        return resolution

    for line in inc['notes']:
        line = line.lower()
        if 'wstrzym' in line and 'po stronie om' in line and not is_magnum(otsa, contract):
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
    _ = otsa
    resolution, wi = '', ''
    if to_cancel(inc):
        return resolution, wi
    if 'ponowione' in inc['summary']:
        resolution = 'Umowa ' + contract['trans_num'] + ' przekazana do realizacji.'
    else:  # TODO Umowy TLS (trans_type like 'T%') do sprawdzenia w ML
        wi += 'Umowa {} (ncs_trans_num: {}, om_order_id: {}) w trakcie realizacji. Prośba o weryfikację w OM.'\
            .format(contract['trans_num'], contract['ncs_trans_num'], contract['om_order_id'])
        reassign_incident(inc, 'OM')
        resolution = ''
    return resolution, wi


def process_3c(otsa, contract, inc):
    if 'ponowione3' in inc['summary']:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(config.optpos_logs['server'],
                    username=config.optpos_logs['user'], password=config.optpos_logs['password'])
        _, ssh_stdout, _ = ssh.exec_command(
            'grep {} /nas/logs/optpos/NodeManagerLogs/applier_*.log | grep INVOKE | tail -2 | grep -v ">0</errorCode>" | grep -v createInteraction'
                .format(contract['trans_code']))
        logs = ssh_stdout.readlines()
        if len(logs) == 2:
            work_info = 'Prośba o weryfikację: \r\n' + logs[0] + logs[1]
            add_work_info(inc, 'VC_OPTIPOS', work_info)
            reassign_incident(inc, 'OV')
        return ''

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
    elif contract['process_error'] == 200307:
        update_transaction(otsa, contract['trans_code'], '1C')  # TODO update all transactions in cart, not only CA
        resolution = 'Wybrano efakturę, a nie podano adresu email. ' \
                     'Proszę zmienić metodę wysyłki faktury lub uzupełnić adres mailowy. ' \
                     'Umowa w statusie do poprawienia. W razie wątpliwości proszę kontaktować się z Dealer Support.'
        return resolution
    elif contract['ncs_error_desc'] is not None and 'CSC.185' in contract['ncs_error_desc']:
        fix_csc185(otsa, contract['cart_code'])
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'CSC.178' in contract['ncs_error_desc']:
        fix_csc178(otsa, contract['cart_code'])
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'CSC.59' in contract['ncs_error_desc']:  # CSC.598, CSC.597
        if not contract['cart_code']:
            fix_csc598(otsa, contract['trans_code'])
        else:
            cart = search_cart(otsa, contract['cart_code'])
            fix_csc598_cart(otsa, cart)
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'EDL.33' in contract['ncs_error_desc']:
        update_transaction(otsa, contract['trans_code'], '3A')
        update_contract(otsa, contract['trans_code'], '3A')
        resolution = 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.'
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
    elif contract['ncs_error_desc'] is not None and ('na zleceniu nie odpowiada' in contract['ncs_error_desc']
                                                     or 'nie jest dostepny' in contract['ncs_error_desc']):
        add_work_info(inc, 'VC_OPTIPOS', 'Prośba o weryfikację, MSISDN {}.'.format(contract['msisdn']))
        reassign_incident(inc, 'OV')
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'Voucher' in contract['ncs_error_desc']:
        add_work_info(inc, 'VC_OPTIPOS', 'Prośba o zmianę statusu vouchera, MSISDN {}.'.format(contract['msisdn']))
        reassign_incident(inc, 'OV')
        resolution = ''
    else:
        resolution = ''

    update_transaction(otsa, contract['trans_code'], '1B')
    update_processing_status(inc)
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
                pass  # TODO jak się trafi przypadek testowy...
        else:
            resolution = process_3c(otsa, contract, inc)
    else:
        resolution = process_3c(otsa, contract, inc)
    return resolution


def process_1h(otsa, contract, inc):
    if 'ponowione3' in inc['summary']:
        return ''

    if contract['cart_code'] != '':
        resolution = ''
        cart = search_cart(otsa, contract['cart_code'])
        ca_processed = False
        for trans in cart:
            if trans['trans_type'] == 'CA' and trans['status'] == '3A':
                ca_processed = True
        for trans in cart:
            if 'ponowione' in inc['summary'] and trans['process_error'] is None and trans['nation'] != 18:
                fix_pesel(otsa, trans['trans_code'])
            if trans['status'] == '3C' and trans['trans_type'] == 'CA':
                resolution = process_3c(otsa, trans, inc)
                update_processing_status(inc)
            elif trans['status'] == '3C' and ca_processed:
                resolution = process_3c(otsa, trans, inc)
                update_processing_status(inc)
    else:
        resolution = process_3c(otsa, contract, inc)
    return resolution


def process_3a(otsa, contract, inc):
    _ = otsa
    resolution = ''
    if contract['status'] == '3A' and contract['trans_num'] and \
            ('ponowione' in inc['summary'] or
             (contract['ncs_error_desc'] and 'Timeout' in contract['ncs_error_desc']) or
             (contract['process_error'] and contract['process_error'] == -31000)):
        resolution += 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.'
        return resolution
    for line in inc['notes']:
        line = line.lower()
        if ('wstrzym' in line and 'po stronie om' in line) \
                or to_process(inc) and contract['trans_type'] != 'CA':
            resolution += 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.'
            return resolution
        elif 'koszyk' in line and 'zatwierd' in line and 'oraz numer koszyka' not in line:
            opti = opti_connection()
            if contract['cart_code'] is not None:
                cart_status = get_cart_status(opti, contract['cart_code'])
                if cart_status not in ['3A', '3D']:
                    set_cart_status(opti, contract['cart_code'], '3A')
                    resolution += 'Koszyk {} zamknięty.'.format(contract['cart_code'])
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
    elif to_process(inc):
        return process_3c(otsa, contract, inc)
    else:
        resolution = ''

    return resolution


def process_8b(otsa, contract, inc):
    return process_1c(otsa, contract, inc)


def process_1d(otsa, contract, inc):
    resolution = ''

    if not to_cancel(inc):
        update_transaction(otsa, contract['trans_code'], '1B')
        update_processing_status(inc)
    else:
        update_transaction(otsa, contract['trans_code'], '3D')
        update_contract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'

    return resolution
