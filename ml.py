# -*- coding: utf-8 -*-
import cx_Oracle

import config


def ml_connection():
    return cx_Oracle.connect(user=config.ml['user'], password=config.ml['password'], dsn=config.ml['server'])


def get_order_data(con, msisdn):
    cur = con.cursor()
    stmt = "select k.msisdn, k.idzleceniaom, z.id, z.status, z.datazmianystatusu " \
           "from ml.kontrakty k join ml.zlecenia z on z.id = k.idzlecenia " \
           "where k.msisdn = '{}' order by z.id desc".format(msisdn)
    cur.execute(stmt)
    row = cur.fetchone()
    if cur.rowcount == 1:
        result = {'msisdn': row[0], 'om_order_id': row[1], 'ml_id': row[2], 'status': row[3], 'last_status_change': row[4]}
    else:
        result = None
    cur.close()
    return result


if __name__ == '__main__':
    ml = ml_connection()
    order = get_order_data(ml, 798841486)
    ml.close()
    print(order)
