# -*- coding: utf-8 -*-
import cx_Oracle

import config


def ml_connection():
    return cx_Oracle.connect(user=config.ml['user'], password=config.ml['password'], dsn=config.ml['server'])


def get_order_data(con, channel_order_id):
    cur = con.cursor()
    stmt = "select k.msisdn, k.idzleceniaom, z.id, z.status, z.datazmianystatusu " \
           "from ml.kontrakty k join ml.zlecenia z on z.id = k.idzlecenia " \
           "where k.idzleceniawkanale = '{}'".format(channel_order_id)
    cur.execute(stmt)
    row = cur.fetchone()
    cur.close()
    return {'msisdn': row[0], 'om_order_id': row[1], 'ml_id': row[2], 'status': row[3], 'last_status_change': row[4]}
