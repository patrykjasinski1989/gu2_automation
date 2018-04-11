# -*- coding: utf-8 -*-
import cx_Oracle

import config


def bscs_connection():
    return cx_Oracle.connect('{}/{}@{}'.format(config.bscs['user'], config.bscs['password'], config.bscs['server']))


def get_customer_id(con, custcode):
    cur = con.cursor()
    cur.execute('select aa.CUSTOMER_ID from ccontact_all bb, customer_all aa '
                'where aa.customer_id=bb.customer_id and aa.custcode = \'' + str(custcode) + '\'')
    customer_id = cur.fetchone()
    cur.close()
    return customer_id[0]


def set_trans_no(con, custcode, trans_no):
    cur = con.cursor()
    stmt = 'update ptk_otsa.ptk_otsa_resources set trans_no = ' + str(
        trans_no) + ' where subtrans_no=0 and type=\'CUSTCODE_S\' ' \
                    'and value = \'' + str(custcode) + '\''
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


if __name__ == "__main__":
    bscs = bscs_connection()
    print get_customer_id(bscs, '1.20894258')
    bscs.close()
