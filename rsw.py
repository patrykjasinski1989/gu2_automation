# -*- coding: utf-8 -*-
import cx_Oracle
import config

def RSWconnection():
    return cx_Oracle.connect('{}/{}@{}'.format(config.rsw['user'], config.rsw['password'], config.rsw['server']))


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
