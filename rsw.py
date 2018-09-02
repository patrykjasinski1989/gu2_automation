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


def get_latest_order(con, msisdn):
    cur = con.cursor()
    cur.execute('select * from (select id_zamowienia, data_zamowienia, status, status_om, ilosc_prob '
                "from rsw.rsw_zamowienia where dn_num = '{}') where rownum = 1".format(msisdn))
    row = cur.fetchone()
    cur.close()
    if cur.rowcount == 1:
        dict_row = {'id_zamowienia': row[0], 'data_zamowienia': row[1],
                    'status': row[2], 'status_om': row[3], 'ilosc_prob': row[4]}
    else:
        dict_row = None
    return dict_row
