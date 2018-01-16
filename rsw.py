# -*- coding: utf-8 -*-
import cx_Oracle


def RSWconnection():
    return cx_Oracle.connect('krzemwo1/boFnMF8zAJIB2sx!@10.236.28.53:1521/RSW')


def getOrderId(con, msisdn, status):
    cur = con.cursor()
    cur.execute('select max(id_zamowienia) from rsw.rsw_zamowienia '
                'where dn_num = \'' + str(msisdn) + '\' and status = ' + str(status))
    row = cur.fetchone()
    cur.close()
    return row[0]


def setOrderStatus(con, orderId, status):
    cur = con.cursor()
    cur.execute('update rsw.rsw_zamowienia set status = ' + str(status) + ' where id_zamowienia = ' + str(orderId))
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount
