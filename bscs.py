# -*- coding: utf-8 -*-
import cx_Oracle

import config


def BSCSconnection():
    return cx_Oracle.connect('{}/{}@{}'.format(config.bscs['user'], config.bscs['password'], config.bscs['server']))


def getCustomerId(con, custcode):
    cur = con.cursor()
    cur.execute('select aa.CUSTOMER_ID from ccontact_all bb, customer_all aa '
                'where aa.customer_id=bb.customer_id and aa.custcode = \'' + str(custcode) + '\'')
    customer_id = cur.fetchone()
    cur.close()
    return customer_id[0]


def setTransNo(con, custcode, transNo):
    cur = con.cursor()
    stmt = 'update ptk_otsa.ptk_otsa_resources set trans_no = ' + str(
        transNo) + ' where subtrans_no=0 and type=\'CUSTCODE_S\' ' \
                   'and value = \'' + str(custcode) + '\''
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


if __name__ == "__main__":
    bscs = BSCSconnection()
    print getCustomerId(bscs, '1.20894258')
    bscs.close()
