# -*- coding: utf-8 -*-
import cx_Oracle

import config


def OPTIconnection():
    return cx_Oracle.connect('{}/{}@{}'.format(config.opti['user'], config.opti['password'], config.opti['server']))


def getCartStatus(con, cartId):
    cur = con.cursor()
    cur.execute('select cart_id, status from dicts.sm_cart where cart_id = {0}'.format(cartId))
    customer_id = cur.fetchone()
    cur.close()
    return customer_id[1]


def setCartStatus(con, cartId, status):
    cur = con.cursor()
    stmt = "update dicts.sm_cart set status = '{0}' where cart_id = '{1}'".format(status, cartId)
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    return cur.rowcount


if __name__ == "__main__":
    opti = OPTIconnection()
    print getCartStatus(opti, 6654712)
    setCartStatus(opti, 6654712, '3D')
    print getCartStatus(opti, 6654712)
    setCartStatus(opti, 6654712, '3A')
    print getCartStatus(opti, 6654712)
