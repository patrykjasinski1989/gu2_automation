# -*- coding: utf-8 -*-
import cx_Oracle

import config


def rsw_connection():
    return cx_Oracle.connect('{}/{}@{}'.format(config.rsw['user'], config.rsw['password'], config.rsw['server']))


def get_order_id(con, msisdn, status):
    cur = con.cursor()
    cur.execute('select max(id_zamowienia) from rsw.rsw_zamowienia '
                'where dn_num = \'' + str(msisdn) + '\' and status = ' + str(status))
    row = cur.fetchone()
    cur.close()
    return row[0]


def set_order_status(con, order_id, status):
    cur = con.cursor()
    cur.execute('update rsw.rsw_zamowienia set status = ' + str(status) + ' where id_zamowienia = ' + str(order_id))
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount
