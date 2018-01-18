# -*- coding: utf-8 -*-
from bscs import getCustomerId, BSCSconnection
from om import getOrders
from optipos import getCartStatus, OPTIconnection, setCartStatus
from otsa import searchMsisdn, updateTransaction, updateContract, fix90100, fixCSC185, searchCart, OTSAconnection, \
    fixPesel, fixCSC178, fixAAC
from remedy import reassignIncident, updateSummary


def processMsisdns(msisdns, inc):
    otsa = OTSAconnection()
    resolution = ''
    allResolved = True
    for msisdn in msisdns:
        contracts = searchMsisdn(otsa, msisdn)
        for contract in contracts:
            print contract
        contracts = [ contract for contract in contracts if (contract['status'] not in ['9', '3D', '3G']
                                or (contract['status'] == '3A' and contract['trans_type'] not in ['MNP1', 'PRPS']))]
        for contract in contracts:
            if contract['status'] == '2Y':
                partialResolution = process2Y(otsa, contract, inc)
            elif contract['status'] == '2B':
                partialResolution = process2B(otsa, contract, inc)
            elif contract['status'] == '3C':
                partialResolution = process3C(otsa, contract, inc)
            elif contract['status'] == '1F':
                partialResolution = process1F(otsa, contract, inc)
            elif contract['status'] =='1H':
                partialResolution = process1H(otsa, contract, inc)
            elif contract['status'] == '3A':
                partialResolution = process3A(otsa, contract, inc)
            elif contract['status'] == '1C':
                partialResolution = process1C(otsa, contract, inc)
            elif contract['status'] == '8B':
                partialResolution = process8B(otsa, contract, inc)
            else:
                partialResolution = ''

            if partialResolution == '':
                allResolved = False

            resolution = resolution + partialResolution + '\n'

    otsa.close()
    return resolution, allResolved


def process2Y(otsa, contract, inc):
    resolution = ''

    toCancel = False
    for line in inc['notes']:
        if 'anulowa' in line or 'ANULOWA' in line:
            toCancel = True

    if toCancel:
        updateTransaction(otsa, contract['trans_code'], '3D')
        updateContract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'
        return resolution

    if inc['summary'] == 'ponowione':
        resolution = 'Umowa ' + contract['trans_num'] + ' wstrzymana po stronie OM. ' \
                     'Jest to poprawny biznesowo status. Proszę anulować lub zatwierdzić. ' \
                     'W razie kłopotów proszę o kontakt z Dealer Support'
        return resolution

    orders = getOrders(contract['msisdn'])
    for order in orders:
        if order['status'] == 'HALTED' and order['id'] == contract['om_order_id']:
            updateTransaction(otsa, contract['trans_code'], '1B')
            resolution = 'Umowa ' + contract['trans_num'] + ' przekazana do realizacji.'
        elif order['status'] == 'COMPLETED' and order['id'] == contract['om_order_id']:
            updateTransaction(otsa, contract['trans_code'], '3A')
            updateContract(otsa, contract['trans_code'], '3A')
            resolution = 'Umowa ' + contract['trans_num'] +' zrealizowana.'
        elif order['status'] == 'CANCELLED' and order['id'] == contract['om_order_id']:
            updateTransaction(otsa, contract['trans_code'], '3D')
            updateContract(otsa, contract['trans_code'], '3D')
            resolution = 'Umowa ' + contract['trans_num'] +' anulowana.'
        else:
            resolution = ''

    return resolution


def process2B(otsa, contract, inc):
    if inc['summary'] == 'ponowione':
        resolution = 'Umowa ' + contract['trans_num'] + ' przekazana do realizacji.'
    else:
        reassignIncident(inc, 'OM')
        resolution = ''
    return resolution


def process3C(otsa, contract, inc):
    if contract['process_error'] == 103199:
        resolution = 'Tak wygląda proces sprzedażowy dla Magnumów. Jeśli nie było logistyki (w OM lub w kanale), ' \
                     'to zlecenie MV musi być zawieszone w OM (HALTED) i dopiero wtedy można złożyć zlecenie DATA.'
    elif contract['process_error'] == 90100:
        transactions = searchCart(otsa, contract['cart_code'])
        for t in transactions:
            fix90100(otsa, t['trans_code'])
        resolution = ''
    elif contract['process_error'] == 21220:
        updateTransaction(otsa, contract['trans_code'], '1C')
        resolution = 'Dokument został już zarejestrowany w CRM. Umowa w statusie do poprawienia. ' \
                     'W razie wątpliwości proszę o kontakt z Dealer Support.'
        return resolution
    elif contract['ncs_error_desc'] is not None and 'CSC.185' in contract['ncs_error_desc']:
        fixCSC185(otsa, contract['cart_code'])
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'CSC.178' in contract['ncs_error_desc']:
        fixCSC178(otsa, contract['cart_code'])
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'ACCOUNT ALREADY CREATED' in contract['ncs_error_desc']:
        bscs = BSCSconnection()
        customer_id = getCustomerId(bscs, contract['custcode'])
        bscs.close()
        fixAAC(otsa, contract['trans_code'],customer_id)
        resolution = ''
    elif contract['process_error'] == 102860:
        updateTransaction(otsa, contract['trans_code'], '1C')
        resolution = contract['ncs_error_desc'] + '\nUmowa w statusie do poprawy. ' \
                                                  'W razie wątpliwości proszę o kontakt z Dealer Support.'
        return resolution
    elif contract['ncs_error_desc'] is not None and 'na zleceniu nie odpowiada' in contract['ncs_error_desc']:
        reassignIncident(inc, 'OV')
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'Voucher' in contract['ncs_error_desc']:
        reassignIncident(inc, 'OV')
        resolution = ''
    else:
        resolution = ''
    updateTransaction(otsa, contract['trans_code'], '1B')
    updateSummary(inc, 'ponowione')
    return resolution


def process1F(otsa, contract, inc):
    if contract['cart_code'] != '':
        cart = searchCart(otsa, contract['cart_code'])
        hasCA = False
        for trans in cart:
            if trans['trans_type'] == 'CA':
                hasCA = True
        if hasCA:
            resolution = ''  # TODO
        else:
            resolution = process3C(otsa, contract, inc)
    else:
        resolution = process3C(otsa, contract, inc)
    return resolution


def process1H(otsa, contract, inc):
    if contract['cart_code'] != '':
        resolution = ''
        cart = searchCart(otsa, contract['cart_code'])
        for trans in cart:
            if inc['summary'] == 'ponowione' and trans['process_error'] is None:
                fixPesel(otsa, trans['trans_code'])
            if trans['trans_type'] == 'CA' and trans['status'] == '3C':
                resolution = process3C(otsa, trans, inc)
                updateSummary(inc, 'ponowione')
    else:
        resolution = process3C(otsa, contract, inc)
    return resolution


def process3A(otsa, contract, inc):
    resolution = ''
    if contract['status'] == '3A' and inc['summary'] == 'ponowione':
        resolution += 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.\n'
    for line in inc['notes']:
        if 'koszyk' in line:
            opti = OPTIconnection()
            if contract['cart_code'] is not None:
                cartStatus = getCartStatus(opti, contract['cart_code'])
                if cartStatus not in ['3A', '3D']:
                    setCartStatus(opti, contract['cart_code'], '3A')
                    resolution += 'Koszyk {} zamknięty.\n'.format(contract['cart_code'])
                    opti.close()
                    return resolution
    else:
        resolution = ''
    return resolution


def process1C(otsa, contract, inc):
    toCancel = False
    for line in inc['notes']:
        if 'anulowa' in line:
            toCancel = True

    if toCancel:
        updateTransaction(otsa, contract['trans_code'], '3D')
        updateContract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'
    else:
        resolution = ''

    return resolution

def process8B(otsa, contract, inc):
    process1C(otsa, contract, inc)
