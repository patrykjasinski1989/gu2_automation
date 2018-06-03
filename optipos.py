# -*- coding: utf-8 -*-
import cx_Oracle

import config


def opti_connection():
    return cx_Oracle.connect(user=config.opti['user'], password=config.opti['password'], dsn=config.opti['server'])


def get_cart_status(con, cart_id):
    cur = con.cursor()
    cur.execute('select cart_id, status from dicts.sm_cart where cart_id = {0}'.format(cart_id))
    customer_id = cur.fetchone()
    cur.close()
    return customer_id[1]


def set_cart_status(con, cart_id, status):
    cur = con.cursor()
    stmt = "update dicts.sm_cart set status = '{0}' where cart_id = '{1}'".format(status, cart_id)
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    return cur.rowcount


if __name__ == "__main__":
    opti = opti_connection()
    print(get_cart_status(opti, 6654712))
    set_cart_status(opti, 6654712, '3D')
    print(get_cart_status(opti, 6654712))
    set_cart_status(opti, 6654712, '3A')
    print(get_cart_status(opti, 6654712))
