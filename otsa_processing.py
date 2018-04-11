# -*- coding: utf-8 -*-
from bscs import getCustomerId, BSCSconnection, setTransNo
from om import getOrders
from optipos import getCartStatus, OPTIconnection, setCartStatus
from otsa import searchMsisdn, updateTransaction, updateContract, fix90100, fixCSC185, searchCart, OTSAconnection, \
    fixPesel, fixCSC178, fixAAC, fixCSC598
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
            elif contract['status'] == '1D':
                partialResolution = process1D(otsa, contract, inc)
            else:
                partialResolution = ''

            if partialResolution == '':
                allResolved = False

            resolution = resolution + partialResolution + '\n'

    otsa.close()
    return resolution, allResolved


def toCancel(inc):
    for line in inc['notes']:
        line = line.lower()
        if 'o anulowa' in line or 'proszę anulować' in line:
            return True
    return False


def process2Y(otsa, contract, inc):
    resolution = ''

    if toCancel(inc):
        updateTransaction(otsa, contract['trans_code'], '3D')
        updateContract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'
        return resolution

    for line in inc['notes']:
        line = line.lower()
        if 'wstrzym' in line and 'po stronie om' in line:
            resolution = 'Umowa ' + contract['trans_num'] + ' wstrzymana po stronie OM. ' \
                                                            'Jest to poprawny biznesowo status. Proszę anulować lub zatwierdzić. ' \
                                                            'W razie kłopotów proszę o kontakt z Dealer Support'
            return resolution

    if 'ponowione' in inc['summary']:
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
    if 'ponowione' in inc['summary']:
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
        if 'BSCS (47 - blad wewnetrzny systemu)' in contract['ncs_error_desc']:
            bscs = BSCSconnection()
            setTransNo(bscs, contract['custcode'], -1)
            bscs.close()
        else:
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
    elif contract['ncs_error_desc'] is not None and 'CSC.598' in contract['ncs_error_desc']:
        fixCSC598(otsa, contract['trans_code'])
        resolution = ''
    elif contract['ncs_error_desc'] is not None and 'EDL.33' in contract['ncs_error_desc']:
        updateTransaction(otsa, contract['trans_code'], '3A')
        updateContract(otsa, contract['trans_code'], '3A')
        resolution = 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.\n'
        return resolution
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
        CA = None
        for trans in cart:
            if trans['trans_type'] == 'CA':
                hasCA = True
                CA = trans
        if hasCA:
            if CA['status'] == '3A':
                resolution = ''
                for trans in [t for t in cart if t['trans_type'] != 'CA']:
                    if trans['status'] in ('1F', '3C'):
                        resolution += process3C(otsa, trans, inc)
            else:
                pass # TODO
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
            if 'ponowione' in inc['summary'] and trans['process_error'] is None:
                fixPesel(otsa, trans['trans_code'])
            if trans['trans_type'] == 'CA' and trans['status'] == '3C':
                resolution = process3C(otsa, trans, inc)
                updateSummary(inc, 'ponowione')
    else:
        resolution = process3C(otsa, contract, inc)
    return resolution


def process3A(otsa, contract, inc):
    resolution = ''
    if contract['status'] == '3A' and ('ponowione' in inc['summary'] or
                                           (contract['ncs_error_desc'] is not None and 'Timeout' in contract['ncs_error_desc']))\
            and contract['trans_num'] is not None:
        resolution += 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.\n'
        return resolution
    for line in inc['notes']:
        line = line.lower()
        if 'wstrzym' in line and 'po stronie om' in line:
            resolution += 'Umowa ' + str(contract['trans_num']) + ' zrealizowana.\n'
            return resolution
        if 'koszyk' in line and 'oraz numer koszyka' not in line:
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
    if toCancel(inc):
        updateTransaction(otsa, contract['trans_code'], '3D')
        updateContract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'
    else:
        resolution = ''

    return resolution


def process8B(otsa, contract, inc):
    return process1C(otsa, contract, inc)


def process1D(otsa, contract, inc):
    resolution = ''

    if not toCancel(inc):
        updateTransaction(otsa, contract['trans_code'], '1B')
        updateSummary(inc, 'ponowione')
    else:
        updateTransaction(otsa, contract['trans_code'], '3D')
        updateContract(otsa, contract['trans_code'], '3D')
        resolution = 'Umowa ' + contract['trans_num'] + ' anulowana.'

    return resolution
