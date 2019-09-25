"""This module handles processing OTSA transactions depending on their status."""
import paramiko

import config
from db.bscs import get_customer_id, bscs_connection, set_trans_no
from db.ml import get_order_data, ml_prod_connection
from db.optipos_ptk import get_cart_status, optipos_connection, set_cart_status
from db.otsa import search_msisdn, update_transaction, update_contract, fix_90100, fix_csc185, search_cart, \
    otsa_connection, fix_pesel, fix_csc178, fix_aac, fix_csc598, fix_csc598_cart, get_magnum_offers, \
    get_promotion_codes, search_trans_num
from om_ptk import get_orders
from remedy import reassign_incident, update_summary, add_work_info, get_work_info, is_work_info_empty


def process_msisdns(msisdns, trans_nums, inc):
    """Handle checking if all msisdns or trans_nums from the ticket have been resolved.
    Also collect work_info from all other methods in this module."""
    otsa = otsa_connection()
    resolution, work_info = '', ''
    all_resolved = True
    for id_ in msisdns + trans_nums:
        contracts = search_msisdn(otsa, id_)
        contracts += search_trans_num(otsa, id_)
        contracts = [contract for contract in contracts
                     if (contract['status'] not in ['9', '3D', '3G']
                         and contract['trans_type'] not in ['MNP1', 'PRPS', 'PPRPS'])]

        for contract in contracts:
            partial_resolution, partial_wi = process_contracts(otsa, contract, inc)
            if partial_resolution == '':
                all_resolved = False
            resolution = resolution + partial_resolution + '\n'
            work_info = work_info + partial_wi + '\n'

    if work_info.strip():
        add_work_info(inc, 'VC_OPTIPOS', work_info)

    otsa.close()
    return resolution, all_resolved


def process_contracts(otsa, contract, inc):
    """Send contract to be processed in an appropriate function, depending on its status."""
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
    return partial_resolution, partial_wi


def to_cancel(inc):
    """Check if the contract from the ticket should be cancelled."""
    cancel_phrases = ['proszę o anul', 'proszę anulować', 'prosze o anul', 'prośba o anul', 'anulowanie umowy',
                      'rezygn']
    for line in inc['notes']:
        line = line.lower()
        for phrase in cancel_phrases:
            if phrase in line:
                return True
    return False


def to_process(inc):
    """Check if the contract from the ticket should be completed."""
    process_phrases = ['proszę zatw', 'proszę o zatw', 'proszę przeproces', 'proszę o przeproces']
    for line in inc['notes']:
        line = line.lower()
        for phrase in process_phrases:
            if phrase in line:
                return True
    return False


def is_magnum(otsa, contract):
    """Check if the contract has one of promotions from the Magnum project."""
    magnum_offers = get_magnum_offers(otsa)
    promotion_codes = get_promotion_codes(otsa, contract['trans_code'])
    for code in promotion_codes:
        if code in magnum_offers:
            return True
    return False


def update_processing_status(inc):
    """Update status at most 3 times"""
    if 'ponowione' not in inc['summary']:
        update_summary(inc, 'ponowione')
    elif 'ponowione2' not in inc['summary']:
        update_summary(inc, 'ponowione2')
    else:
        update_summary(inc, 'ponowione3')


def process_2y(otsa, contract, inc):
    """Process transactions with '2Y' status."""
    resolution = ''

    if to_cancel(inc):
        update_transaction(otsa, contract['trans_code'], '3D')
        update_contract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'
        return resolution

    for line in inc['notes']:
        line = line.lower()
        if False:  # 'wstrzym' in line and 'po stronie om' in line and not is_magnum(otsa, contract):
            resolution = 'Umowa ' + contract['trans_num'] + \
                         ' wstrzymana po stronie OM. Jest to poprawny biznesowo status. ' \
                         'Proszę anulować lub zatwierdzić. W razie kłopotów proszę o kontakt z Dealer Support'
            return resolution

    if 'ponowione' in inc['summary']:
        resolution = 'Umowa {} wstrzymana po stronie OM. Jest to poprawny biznesowo status. ' \
                     'Proszę anulować lub zatwierdzić. W razie kłopotów proszę o kontakt z Dealer Support'. \
            format(contract['trans_num'])
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
    """Process transactions with '2B' status."""
    zld_remedy_url = 'https://itsmweb.corp.tepenet/arsys/forms/itsm.corp.tepenet/TP%3ASKR%3AUserPage/ORANGE_ZLD/'
    _ = otsa
    resolution, work_info = '', ''
    if to_cancel(inc):
        return resolution, work_info
    if 'ponowione' in inc['summary']:
        resolution = 'Umowa ' + contract['trans_num'] + ' przekazana do realizacji.'
    elif contract['process_error'] != -31000:
        work_info_ = get_work_info(inc)
        if not is_work_info_empty(work_info_):
            return '', ''

        if contract['trans_type'][0] == 'T':
            ml_con = ml_prod_connection()
            ml_order = get_order_data(ml_con, contract['msisdn'])
            if ml_order and ml_order['status'] != 'DELV':
                resolution = 'Zamówienie przetwarzane w ML. ' \
                             'Proszę swoje zgłoszenie przekierować na panel zarządzania łańcuchem dostaw: {}'. \
                    format(zld_remedy_url)
            ml_con.close()
        else:
            work_info += 'Umowa {} (ncs_trans_num: {}, om_order_id: {}) w trakcie realizacji. ' \
                         'Prośba o weryfikację w OM.' \
                .format(contract['trans_num'], contract['ncs_trans_num'], contract['om_order_id'])
            reassign_incident(inc, 'OM')
            resolution = ''
    return resolution, work_info


def process_3c(otsa, contract, inc):
    """Process transactions with '3C' status.
    Possibly the biggest fucking mess in this whole code."""
    if 'ponowione3' in inc['summary']:
        return send_error_to_ov(inc, contract)

    update_status, resolution = handle_process_errors(otsa, contract)
    if not resolution:
        update_status, resolution = handle_ncs_errors(otsa, contract, inc)

    if update_status:
        update_transaction(otsa, contract['trans_code'], '1B')
        update_processing_status(inc)
    return resolution


def send_error_to_ov(inc, contract):
    """Look for an error in applier logs an if there is one, send it to OV for further analysis."""
    grep_files = '/nas/logs/optpos/NodeManagerLogs/applier_*.log'
    grep_command = 'grep {} {} | grep INVOKE | tail -2 | grep -v ">0</errorCode>" | grep -v createInteraction'
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(config.OPTPOS_LOGS['server'],
                username=config.OPTPOS_LOGS['user'], password=config.OPTPOS_LOGS['password'])
    _, ssh_stdout, _ = ssh.exec_command(grep_command.format(contract['trans_code'], grep_files))
    logs = ssh_stdout.readlines()
    if len(logs) == 2:
        work_info = get_work_info(inc)
        if not is_work_info_empty(work_info):
            return ''
        work_info = 'Prośba o weryfikację: \r\n' + logs[0] + '\r\n' + logs[1]
        add_work_info(inc, 'VC_OPTIPOS', work_info)
        reassign_incident(inc, 'OV')
    return ''


def handle_process_errors(otsa, contract):
    """Handle process errors - artificially separated function part to slim down the process_3c() function."""
    update_status = False
    if contract['process_error'] == 103199:
        resolution = 'Druga noga zamówienia nie znajduje sie w statusie HALTED w OM co jest wymagane przy MAGNUM, ' \
                     'proszę ponownie wypisać całość. W razie wątpliwości proszę o kontakt z Dealer Support.\n'
    elif contract['process_error'] == 90100:
        if 'BSCS (47 - blad wewnetrzny systemu)' in contract['ncs_error_desc']:
            bscs = bscs_connection()
            set_trans_no(bscs, contract['custcode'], -1)
            bscs.close()
        else:
            transactions = search_cart(otsa, contract['cart_code'])
            for trans in transactions:
                fix_90100(otsa, trans['trans_code'])
        resolution = ''
        update_status = True
    elif contract['process_error'] == 21220:
        update_transaction(otsa, contract['trans_code'], '1C')
        resolution = 'Dokument został już zarejestrowany w CRM. Umowa w statusie do poprawienia. ' \
                     'W razie wątpliwości proszę o kontakt z Dealer Support.'
    elif contract['process_error'] == 200307:
        update_transaction(otsa, contract['trans_code'], '1C')
        resolution = 'Wybrano e-fakturę, a nie podano adresu email. ' \
                     'Proszę zmienić metodę wysyłki faktury lub uzupełnić adres mailowy. ' \
                     'Umowa w statusie do poprawienia. W razie wątpliwości proszę kontaktować się z Dealer Support.'
    elif contract['process_error'] == 102860:
        update_transaction(otsa, contract['trans_code'], '1C')
        resolution = contract['ncs_error_desc'] + '\nUmowa w statusie do poprawy. ' \
                                                  'W razie wątpliwości proszę o kontakt z Dealer Support.'
    else:
        resolution = ''
    return update_status, resolution


def handle_ncs_errors(otsa, contract, inc):
    """Handle NCS errors - another artificially separated function just to try and solve the process_3c mess."""
    update_status = True
    if contract['ncs_error_desc'] is not None and 'CSC.185' in contract['ncs_error_desc']:
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
        update_status = False
        resolution = 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.'
    elif contract['ncs_error_desc'] is not None and 'ACCOUNT ALREADY CREATED' in contract['ncs_error_desc']:
        bscs = bscs_connection()
        customer_id = get_customer_id(bscs, contract['custcode'])
        bscs.close()
        fix_aac(otsa, contract['trans_code'], customer_id)
        resolution = ''
    elif contract['ncs_error_desc'] is not None and ('na zleceniu nie odpowiada' in contract['ncs_error_desc']
                                                     or 'nie jest dostepny' in contract['ncs_error_desc']):
        work_info = get_work_info(inc)
        if not is_work_info_empty(work_info):
            return ''
        add_work_info(inc, 'VC_OPTIPOS', 'Prośba o weryfikację, MSISDN {}.'.format(contract['msisdn']))
        reassign_incident(inc, 'OV')
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'Voucher' in contract['ncs_error_desc']:
        work_info = get_work_info(inc)
        if not is_work_info_empty(work_info):
            return ''
        add_work_info(inc, 'VC_OPTIPOS', 'Prośba o zmianę statusu vouchera, MSISDN {}.'.format(contract['msisdn']))
        reassign_incident(inc, 'OV')
        resolution = ''
    else:
        resolution = ''
    return update_status, resolution


def process_1f(otsa, contract, inc):
    """Process transactions with '1F' status."""
    resolution = ''
    if contract['cart_code'] != '':
        cart = search_cart(otsa, contract['cart_code'])
        has_ca = False
        ca_trans = None
        for trans in cart:
            if trans['trans_type'] == 'CA':
                has_ca = True
                ca_trans = trans
        if has_ca:
            if ca_trans['status'] == '3A':
                resolution = ''
                for trans in [t for t in cart if t['trans_type'] != 'CA']:
                    if trans['status'] in ('1F', '3C'):
                        resolution += process_3c(otsa, trans, inc)
            else:
                pass
        else:
            resolution = process_3c(otsa, contract, inc)
    else:
        resolution = process_3c(otsa, contract, inc)
    return resolution


def process_1h(otsa, contract, inc):
    """Process transactions with '1H' status."""
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
    """Process transactions with '3A' status."""
    _ = otsa
    resolution = ''

    if is_contract_processed_recently(contract, inc) or \
            'Proszę o zmianę w systemie zgody na TAK' in ' '.join(inc['notes']):
        resolution += 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.'
        return resolution

    for line in inc['notes']:
        line = line.lower()
        if ('wstrzym' in line and 'po stronie om' in line) or (to_process(inc) and contract['trans_type'] != 'CA'):
            resolution += 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.'
            return resolution
        if 'koszyk' in line and 'zatwierd' in line and 'oraz numer koszyka' not in line:
            opti = optipos_connection()
            if contract['cart_code'] is not None:
                cart_status = get_cart_status(opti, contract['cart_code'])
                if cart_status not in ['3A', '3D']:
                    set_cart_status(opti, contract['cart_code'], '3A')
                    resolution += 'Koszyk {} zamknięty.'.format(contract['cart_code'])
                    opti.close()
                    return resolution
    return ''


def is_contract_processed_recently(contract, inc):
    """Check if the contract has been processed recently."""
    return contract['status'] == '3A' and contract['trans_num'] and \
           ('ponowione' in inc['summary'] or
            (contract['ncs_error_desc'] and 'Timeout' in contract['ncs_error_desc']) or
            (contract['process_error'] and contract['process_error'] == -31000))


def process_1c(otsa, contract, inc):
    """Process transactions with '1C' status."""
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
    """Process transactions with '8B' status."""
    return process_1c(otsa, contract, inc)


def process_1d(otsa, contract, inc):
    """Process transactions with '3D' status."""
    resolution = ''

    if to_cancel(inc):
        update_transaction(otsa, contract['trans_code'], '3D')
        update_contract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'

    return resolution
