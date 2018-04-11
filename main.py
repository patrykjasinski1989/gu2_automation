# -*- coding: utf-8 -*-
import re

from datetime import datetime
from dateutil import parser

from eai import getExpirationDate, getContractData
from muchomor import unlockImei
from nra import getSimStatus, NRAconnection, setSimStatusNRA, setSimStatusBSCS, setIMSIStatusBSCS
from otsa import OTSAconnection, checkSIM, unlockAccount
from otsa_processing import processMsisdns
from remedy import getIncidents, closeIncident, emptyInc, getSchemas, getFields, reassignIncident


def unlockImeis():
    incidents = getIncidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'ODBLOKOWANIE IMEI'
        )

    imei_regex = re.compile('[a-zA-Z0-9]{9,15}')
    imeis = []

    for inc in incidents:
        lines = inc['notes']
        for i in range(len(lines)):
            if 'IMEI:' in lines[i]:
                imeis = imei_regex.findall(lines[i+1])
                break
        resolution = ''
        if len(imeis)>0:
            for imei in imeis:
                resolution += unlockImei(imei.upper()) + '\n'
        if emptyInc(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
        if resolution.strip() != '':
            closeIncident(inc, resolution)
        print '{}: {}'.format(inc['inc'], resolution.strip())


def activateCustomers():
    incidents = getIncidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'AKTYWACJA KLIENTA'
    )

    msisdn_regex = re.compile('[0-9]{9,9}')
    for inc in incidents:
        resolution = ''
        lines = inc['notes']
        allResolved = True
        for i in range(len(lines)):
            if 'Proszę podać numer MSISDN' in lines[i]:
                msisdns = msisdn_regex.findall(lines[i+1])
                resolution, allResolved = processMsisdns(msisdns, inc)
        if emptyInc(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
        if resolution != '' and allResolved:
            closeIncident(inc, resolution)
        print '{}: {}'.format(inc['inc'], resolution.strip())


def migrateCustomers():
    incidents = getIncidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'MIGRACJA KLIENTA'
    )

    msisdn_regex = re.compile('[0-9]{9,9}')
    for inc in incidents:
        resolution = ''
        lines = inc['notes']
        allResolved = True
        for i in range(len(lines)):
            if 'Proszę podać numer MSISDN' in lines[i]:
                msisdns = msisdn_regex.findall(lines[i+1])
                resolution, allResolved = processMsisdns(msisdns, inc)
        if emptyInc(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
        if resolution != '' and allResolved:
            closeIncident(inc, resolution)
        print '{}: {}'.format(inc['inc'], resolution.strip())


def saleOfServices():
    incidents = getIncidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OPTIPOS - OFERTA PTK',
        'SPRZEDAZ USLUG'
    )

    msisdn_regex = re.compile('[0-9]{9,9}')
    for inc in incidents:
        resolution = ''
        lines = inc['notes']
        allResolved = True
        for i in range(len(lines)):
            if 'Numer telefonu klienta Orange / MSISDN' in lines[i]:
                msisdns = msisdn_regex.findall(lines[i+1])
                resolution, allResolved = processMsisdns(msisdns, inc)
        if emptyInc(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'
        if resolution != '' and allResolved:
            closeIncident(inc, resolution)
        print '{}: {}'.format(inc['inc'], resolution.strip())


def releaseResources():
    incidents = getIncidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OTSA',
        'UWOLNIENIE ZASOBOW'
    )

    otsa = OTSAconnection()
    sim_regex = re.compile('[0-9]{19,20}')
    for inc in incidents:
        sims = []
        for line in inc['notes']:
            sims.extend(sim_regex.findall(line))

        allResolved = True
        resolution = ''

        nra = NRAconnection()
        for sim in sims:
            partialResolution = ''
            result = checkSIM(otsa, sim)
            result = [r for r in result if r['status'] not in ('3D', '3G')]
            if len(result) == 0:
                simStatus = getSimStatus(nra, sim)
                if len(simStatus) == 0:
                    partialResolution = 'Brak karty SIM {0} w nRA. Proszę podać poprawny numer.'.format(sim)
                    resolution = partialResolution + '\r\n'
                    continue
                if simStatus['status_nra'] == simStatus['status_bscs']:
                    if simStatus['status_nra'] in ('r', 'd', 'l', 'E') \
                    and simStatus['status_nra'] == simStatus['status_bscs']:
                        setSimStatusNRA(nra, sim, 'r')
                        setSimStatusBSCS(nra, sim, 'r')
                        setIMSIStatusBSCS(nra, simStatus['imsi'], 'r')
                        partialResolution = 'Karta SIM {0} uwolniona.'.format(sim)
                    elif simStatus['status_nra'] in ('a', 'B'):
                        partialResolution = 'Karta SIM {0} aktywna. Brak możliwości odblokowania.'.format(sim)
                    else:
                        allResolved = False
                        pass # simka w dziwnym statusie i na nra
            else:
                partialResolution = 'Karta SIM {0} powiązana z nieanulowaną umową {1}. Brak możliwości odblokowania.' \
                                    'Proszę o kontakt z dealer support lub z działem reklamacji'\
                    .format(sim, result[0]['trans_num'])
            if partialResolution != '':
                resolution = resolution + '\r\n' + partialResolution
        nra.close()

        if emptyInc(inc):
            resolution = 'Puste zgłoszenie, prawdopodobnie duplikat.'

        if allResolved and resolution != '':
            closeIncident(inc, resolution)

        print '{}: {}'.format(inc['inc'], resolution.strip())
    otsa.close()


def problemsWithOffer():
    incidents = getIncidents(
        'VC_BSS_MOBILE_RSW',
        '000_incydent/awaria/uszkodzenie',
        'RSW / nBUK',
        'PROBLEMY Z OFERTĄ I TERMINALAMI'
    )
    for inc in incidents:
        resolution = ''

        msisdn = ''
        msisdnInNextLine = False
        offerName = ''
        for line in inc['notes']:
            if 'Numer telefonu klienta Orange / MSISDN' in line:
                msisdnInNextLine = True
                continue
            if msisdnInNextLine:
                msisdn = line.strip()
                msisdnInNextLine = False
            if 'Proszę o dodanie oferty: ' in line:
                offerName = line.split(': ')[1].split('.')[0]

        expirationDate = getExpirationDate(getContractData(msisdn))
        if expirationDate != '':
            dt = parser.parse(expirationDate)
        else:
            continue
        now = datetime.now()
        if (offerName.lower() == 'plan komórkowy' or offerName.lower() == 'internet mobilny') and (dt - now).days > 120:
            resolution = 'Klient ma lojalkę do {0}. Zgodnie z konfiguracją marketingową oferta {1} ' \
                         'jest dostępna na 120 dni przed końcem lojalki, czyli klient tych wymagań nie spełnia. ' \
                         'Brak błędu aplikacji.'.format(expirationDate, offerName)
            closeIncident(inc, resolution)

        print '{}: {}'.format(inc['inc'], resolution.strip())


def unlockAccounts():
    incidents = getIncidents(
        'VC_BSS_MOBILE_OPTIPOS',
        '000_incydent/awaria/uszkodzenie',
        'OTSA/OPTIPOS',
        'ODBLOKOWANIE KONTA'
    )
    otsa = OTSAconnection()
    for inc in incidents:
        loginInNextLine = False
        for line in inc['notes']:
            if 'Podaj login OTSA' in line:
                loginInNextLine = True
                continue
            if loginInNextLine:
                login = line.strip().lower()
                break
        if login:
            rowsUpdated = unlockAccount(otsa, login)
        if rowsUpdated == 1:
            resolution = 'Konto o loginie {} jest aktywne. Nowe hasło to: centertel.'.format(login)
            closeIncident(inc, resolution)

        print '{}: {}'.format(inc['inc'], resolution.strip())


if __name__ == '__main__':

    print "ODBLOKOWANIE IMEI"
    unlockImeis()
    print "ODBLOKOWANIE KONTA"
    unlockAccounts()
    print "AKTYWACJA KLIENTA"
    activateCustomers()
    print "MIGRACJA KLIENTA"
    migrateCustomers()
    print "SPRZEDAZ USLUG"
    saleOfServices()
    print "UWOLNIENIE ZASOBÓW"
    releaseResources()
    print "PROBLEMY Z OFERTĄ"
    problemsWithOffer()
