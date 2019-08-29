"""This module is used to interact with bscs database."""

import cx_Oracle

import config
from db.db_helpers import execute_dml


def bscs_connection():
    """Returns connection to prod bscs database."""
    return cx_Oracle.connect('{}/{}@{}'.format(config.BSCS['user'], config.BSCS['password'], config.BSCS['server']))


def get_customer_id(con, custcode):
    """Returns customer_id for a given custcode"""
    cur = con.cursor()
    cur.execute('select aa.CUSTOMER_ID from ccontact_all bb, customer_all aa '
                'where aa.customer_id=bb.customer_id and aa.custcode = \'' + str(custcode) + '\'')
    customer_id = cur.fetchone()
    cur.close()
    return customer_id[0]


def set_trans_no(con, custcode, trans_no):
    """Sets trans_no for a given custcode."""
    stmt = 'update ptk_otsa.ptk_otsa_resources set trans_no = ' + str(
        trans_no) + ' where subtrans_no=0 and type=\'CUSTCODE_S\' ' \
                    'and value = \'' + str(custcode) + '\''
    execute_dml(con, stmt)


if __name__ == '__main__':
    BSCS = bscs_connection()
    print(get_customer_id(BSCS, '1.20894258'))
    BSCS.close()
