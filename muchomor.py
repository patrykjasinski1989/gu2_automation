# -*- coding: utf-8 -*-
import requests
from requests.exceptions import ConnectTimeout

from rsw import RSWconnection, getOrderId, setOrderStatus
import config

def unlockImei(imei):
    proxies = config.muchomor['proxies']

    url = config.muchomor['url']
    s = requests.session()
    try:
        s.get(url=url+'pagIMEI.jsf', proxies=proxies, timeout=2)
        s.post(url=url+'j_security_check', proxies=proxies,
           data={'j_username': config.muchomor['user'], 'j_password': config.muchomor['password']})
        response = s.get(url=url+'pagIMEI.jsf', proxies=proxies)
        javaxFaces = response.text.split('id="javax.faces.ViewState" value="')[1].split('"')[0]
    except:
        return ''

    payload = {
        'j_id_jsp_625197284_1:j_id_jsp_625197284_5': imei,
        'j_id_jsp_625197284_1:findImei': 'Szukaj',
        'j_id_jsp_625197284_1_SUBMIT': '1',
        'javax.faces.ViewState': javaxFaces
    }

    payload2 = {
        'j_id_jsp_625197284_1:j_id_jsp_625197284_5': imei,
        'j_id_jsp_625197284_1:findImei': 'Szukaj',
        'j_id_jsp_625197284_1_SUBMIT': '1',
        'javax.faces.ViewState': javaxFaces,
        'salesPoint': '',
        'imei': imei,
        'promoCode': '',
        'personId': '',
        'j_id_jsp_625197284_1:_idcl': 'j_id_jsp_625197284_1:j_id_jsp_625197284_13'
    }

    response = s.post(url=url+'pagIMEI.jsf', proxies=proxies, data=payload)
    if 'messageForUser' in response.text:
        result = response.text.split('<span class="messageForUser">')[1].split('</span>')[0]
    else:
        return ''

    if result == 'Nie znaleziono terminala. Podaj poprawny IMEI.':
        resolution = 'Nie znaleziono terminala %s. Prosze podac poprawny IMEI.' % imei
    elif 'Nie mo&#380;na odblokowa&#263;,' in result:
        if 'RSW' in result:
            msisdn = response.text.split('<tr><td>'+imei+'</td><td>')[-1].split('</td>')[0]
            resolution = result + ', na numerze MSISDN: ' + msisdn + '.'
            if 'Reklamacja' in result:
                rsw = RSWconnection()
                order_id = getOrderId(rsw, msisdn, '5')
                setOrderStatus(rsw, order_id, '6')
                resolution = unlockImei(imei)
                setOrderStatus(rsw, order_id, '5')
                rsw.close()
    elif 'Mo&#380;na odblokowa&#263;,' in result:
        response = s.post(url=url+'pagIMEI.jsf', proxies=proxies, data=payload2)
        resolution = response.text.split('<span class="messageForUser">')[1].split('</span>')[0]
    elif 'Sprzedawca powinien ' in result:
        resolution = 'Terminal ' + imei +' aktywny w IFS. Proszę o kontakt z działem refundacji ' \
                   'lub z centralą agenta w przypadku salonów agencyjnych.'
    elif 'Terminal odblokowany' in result:
        resolution = 'Terminal ' + imei + ' odblokowany.'
    else:
        resolution = result

    return resolution

